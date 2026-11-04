"""Final test: score our U-Net and nnU-Net on the locked test patients, which no model has seen.

Our U-Net: the 5 fold models' tumour probabilities are averaged (nnU-Net does the same with its folds).
Both models then keep only the largest tumour piece, so they are compared the same way.

    python evaluate.py --data ../data/full/nnunet/Dataset001_LungGTV --splits ../data/full/splits.json \
        --ours full_e3_fold0 full_e3_fold1 full_e3_fold2 full_e3_fold3 full_e3_fold4 \
        --nnunet-pred ../data/full/pred_nnunet --out ../results/test_scores.csv
"""
import argparse
import csv
import json
from pathlib import Path

import numpy as np
import SimpleITK as sitk
import torch
from scipy import ndimage

from train import build, largest_piece, predict_prob

SIZE_GROUPS = [("small", 0, 20), ("medium", 20, 100), ("large", 100, float("inf"))]   # tumour volume, cc


def read(path):
    im = sitk.ReadImage(str(path))
    return sitk.GetArrayFromImage(im), np.array(im.GetSpacing()[::-1])   # (z, y, x) and mm per voxel


def hd95(pred, gt, spacing):
    """95th-percentile distance between the two outlines' surfaces, in mm (ignores the worst 5%)."""
    if not pred.any() or not gt.any():
        return float("nan")
    sp, sg = pred ^ ndimage.binary_erosion(pred), gt ^ ndimage.binary_erosion(gt)
    to_gt = ndimage.distance_transform_edt(~sg, sampling=spacing)[sp]
    to_pred = ndimage.distance_transform_edt(~sp, sampling=spacing)[sg]
    return float(np.percentile(np.concatenate([to_gt, to_pred]), 95))


def scores(pred, gt, spacing):
    pred, gt = pred.astype(bool), gt.astype(bool)
    voxel_cc = np.prod(spacing) / 1000
    dice = 2 * (pred & gt).sum() / (pred.sum() + gt.sum()) if pred.sum() + gt.sum() else 1.0
    return {"dice": round(float(dice), 3), "hd95_mm": round(hd95(pred, gt, spacing), 1),
            "vol_diff_pct": round(100 * (pred.sum() - gt.sum()) / gt.sum(), 1),
            "found": bool(dice > 0.1), "gtv_cc": round(float(gt.sum() * voxel_cc), 1)}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", required=True)
    ap.add_argument("--splits", required=True)
    ap.add_argument("--ours", nargs="*", default=[], help="run names under runs/, one per fold")
    ap.add_argument("--nnunet-pred", default=None, help="folder of nnUNetv2_predict outputs for the test patients")
    ap.add_argument("--out", required=True)
    ap.add_argument("--cutoff", type=float, default=0.5, help="our U-Net: tumour cut-off (choose it on validation, never on test)")
    ap.add_argument("--gauss", action="store_true", help="our U-Net: centre-weighted blocks")
    a = ap.parse_args()
    if Path(a.out).exists():
        raise SystemExit(f"{a.out} already exists (results are never overwritten). Use a new --out.")

    device = "cuda" if torch.cuda.is_available() else "mps" if torch.backends.mps.is_available() else "cpu"
    data = Path(a.data)
    nets = []
    for name in a.ours:
        ck = torch.load(Path("runs") / name / "best.pt", map_location=device)
        net = build(ck["args"]).to(device)
        net.load_state_dict(ck["model"])
        nets.append((net.eval(), ck["args"]["patch"], ck.get("norm")))

    rows = []
    for pid in json.load(open(a.splits))["test"]:
        img, spacing = read(data / "imagesTr" / f"{pid}_0000.nii.gz")
        gt, _ = read(data / "labelsTr" / f"{pid}.nii.gz")
        if nets:
            prob = np.mean([predict_prob(n, img.astype(np.int16), p, device, nm, a.gauss) for n, p, nm in nets], axis=0)
            rows.append({"patient": pid, "model": "our U-Net", **scores(largest_piece(prob > a.cutoff), gt, spacing)})
        if a.nnunet_pred:
            pred, _ = read(Path(a.nnunet_pred) / f"{pid}.nii.gz")
            rows.append({"patient": pid, "model": "nnU-Net", **scores(largest_piece(pred > 0), gt, spacing)})
        print(pid, *[f"{r['model']}: {r['dice']}" for r in rows if r["patient"] == pid], flush=True)

    Path(a.out).parent.mkdir(parents=True, exist_ok=True)
    with open(a.out, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=rows[0].keys())
        w.writeheader()
        w.writerows(rows)

    print(f"\n{'model':<10} {'group':<7} {'n':>3} {'Dice':>6} {'HD95 mm':>8} {'vol diff %':>10} {'found':>6}")
    for model in dict.fromkeys(r["model"] for r in rows):
        for group, lo, hi in [("all", 0, float("inf"))] + SIZE_GROUPS:
            g = [r for r in rows if r["model"] == model and lo <= r["gtv_cc"] < hi]
            if g:
                print(f"{model:<10} {group:<7} {len(g):>3} {np.mean([r['dice'] for r in g]):>6.3f} "
                      f"{np.nanmedian([r['hd95_mm'] for r in g]):>8.1f} {np.median([r['vol_diff_pct'] for r in g]):>10.1f} "
                      f"{sum(r['found'] for r in g):>3}/{len(g)}")
    print(f"\nper-patient scores -> {a.out}  (HD95 and volume difference are medians)")


if __name__ == "__main__":
    main()
