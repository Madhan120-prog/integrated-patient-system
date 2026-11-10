"""6.4 / E8: MedSAM2 outlines the tumour from a box hint, on one fold's VALIDATION patients (or the test, once).

    ../.venv-medsam2/bin/python medsam_box.py --data ../data/full/nnunet/Dataset001_LungGTV --splits ../data/full/splits.json \\
        --fold 0 --box doctor --name b6_medsam_doctor_fold0
    ... --box ours --ours b5_long_fold0 --name b6_medsam_ours_fold0

--box doctor  (a) best case: box around the doctor's outline on the slice where the tumour is largest.
--box ours    (b) real case: same, but from our U-Net's outline (it never sees the doctor's); no outline -> no box -> a miss.
MedSAM2 only gets the plain CT and the box; the doctor's outline is used for the box in (a) and for scoring.
It follows the tumour up and down from the box slice (MedSAM2's 3D CT recipe, medsam2_infer_3D_CT.py), keeps the
largest piece, and is scored like every other run. Writes runs/<name>/ (refuses an existing name).
"""
import argparse
import json
import os
import time
from pathlib import Path

import numpy as np
import torch
from PIL import Image

from train import HERE, HU_MAX, HU_MIN, build, code_fingerprint, dice, largest_piece, load, new_run_dir, one_piece, \
    predict_prob, write_json


def box_on_largest_slice(mask, margin):
    """(slice, [x0, y0, x1, y1]): the slice where the outline is largest and the box around it, `margin` pixels wider."""
    z = int(np.argmax(mask.reshape(mask.shape[0], -1).sum(1)))
    ys, xs = np.nonzero(mask[z])
    h, w = mask.shape[1:]
    return z, np.array([max(0, xs.min() - margin), max(0, ys.min() - margin),
                        min(w - 1, xs.max() + margin), min(h - 1, ys.max() + margin)])


def coverage(lab, box):
    """Share of the doctor's tumour that falls inside the box's left-right / front-back range (any slice)."""
    x0, y0, x1, y1 = box
    _, ys, xs = np.nonzero(lab)
    return float(((xs >= x0) & (xs <= x1) & (ys >= y0) & (ys <= y1)).mean())


def to_frames(img, size=512):
    """CT in HU -> MedSAM2 input: window, 0-255, grey to RGB, resize, ImageNet normalisation (its CT recipe)."""
    v = np.uint8((np.clip(img, HU_MIN, HU_MAX) - HU_MIN) / (HU_MAX - HU_MIN) * 255)
    frames = np.stack([np.array(Image.fromarray(s).convert("RGB").resize((size, size))).transpose(2, 0, 1) for s in v])
    x = torch.from_numpy(frames / 255.0).float().cuda()
    mean = torch.tensor((0.485, 0.456, 0.406)).view(3, 1, 1).cuda()
    std = torch.tensor((0.229, 0.224, 0.225)).view(3, 1, 1).cuda()
    return (x - mean) / std


@torch.inference_mode()
def medsam_outline(predictor, img, z, box):
    seg = np.zeros(img.shape, np.uint8)
    frames = to_frames(img)
    with torch.autocast("cuda", dtype=torch.bfloat16):
        for reverse in (False, True):                       # follow the tumour up, then down, from the box slice
            state = predictor.init_state(frames, img.shape[1], img.shape[2])
            predictor.add_new_points_or_box(inference_state=state, frame_idx=z, obj_id=1, box=box)
            for f, _, logits in predictor.propagate_in_video(state, reverse=reverse):
                seg[f, (logits[0] > 0.0).cpu().numpy()[0]] = 1
            predictor.reset_state(state)
    return largest_piece(seg) if seg.any() else seg


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", required=True)
    ap.add_argument("--splits", required=True)
    ap.add_argument("--fold", type=int, default=0)
    ap.add_argument("--on", choices=["val", "test"], default="val", help="test: only once, for the final comparison")
    ap.add_argument("--box", choices=["doctor", "ours"], required=True)
    ap.add_argument("--ours", default=None, help="--box ours: our finished run for this fold")
    ap.add_argument("--ours-setting", nargs=3, default=["gauss", "0.3", "confident"],
                    help="--box ours: how our outline is made (b5 best on validation: gauss 0.3 confident)")
    ap.add_argument("--margin", type=int, default=5, help="box margin in pixels")
    ap.add_argument("--checkpoint", default="../MedSAM2/checkpoints/MedSAM2_latest.pt")
    ap.add_argument("--cfg", default="configs/sam2.1_hiera_t512.yaml")
    ap.add_argument("--name", required=True)
    a = ap.parse_args()
    assert a.box == "doctor" or a.ours, "--box ours needs --ours <run>"

    from sam2.build_sam import build_sam2_video_predictor_npz   # only in the MedSAM2 environment
    run = new_run_dir(a.name)
    s = json.load(open(a.splits))
    ids = s["test"] if a.on == "test" else s["folds"][a.fold]["val"]
    record = {"name": a.name, "exp": "B6.4 / E8 MedSAM2", "model": "MedSAM2",
              "change": f"box from {'the doctor' if a.box == 'doctor' else a.ours}, margin {a.margin} px, {Path(a.checkpoint).name}",
              "job": os.environ.get("SLURM_JOB_ID"), "started": time.strftime("%Y-%m-%d %H:%M:%S"), "code": code_fingerprint(),
              "fold": a.fold, "scored_on": a.on, "args": vars(a)}
    write_json(run / "settings.json", record)

    torch.manual_seed(2024)
    predictor = build_sam2_video_predictor_npz(a.cfg, a.checkpoint)
    net = None
    if a.box == "ours":
        ck = torch.load(HERE / "runs" / a.ours / "best.pt", map_location="cuda")
        net = build(ck["args"]).cuda().eval()
        net.load_state_dict(ck["model"])

    per = {}
    for pid in ids:
        img, lab = load(Path(a.data), pid)
        if net is None:
            guide = lab
        else:
            g, c, h = a.ours_setting
            guide = one_piece(predict_prob(net, img, ck["args"]["patch"], "cuda", ck.get("norm"), g == "gauss"), float(c), h)
        if guide.any():
            z, box = box_on_largest_slice(guide, a.margin)
            m, cov = medsam_outline(predictor, img, z, box), coverage(lab, box)
        else:                                                # our model found nothing: no box, a miss
            m, cov = np.zeros_like(lab), 0.0
        per[pid] = {"dice": round(float(dice(m, lab)), 4), "box_covers": round(cov, 3),
                    "vol_diff_pct": round(100 * (int(m.sum()) - int(lab.sum())) / int(lab.sum()), 1)}
        print(pid, per[pid], flush=True)

    d = per.values()
    rows = [{"variant": f"box_{a.box}", "val_dice": round(float(np.mean([r["dice"] for r in d])), 4),
             "found": sum(r["dice"] > 0.1 for r in d), "n_val": len(per),
             "median_vol_diff_pct": float(np.median([r["vol_diff_pct"] for r in d])),
             "mean_box_covers": round(float(np.mean([r["box_covers"] for r in d])), 3)}]
    print(rows[0])
    write_json(run / "summary.json", {**record, "rows": rows, "per_patient": per, "finished": time.strftime("%Y-%m-%d %H:%M:%S")})


if __name__ == "__main__":
    main()
