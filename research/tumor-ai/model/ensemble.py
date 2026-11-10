"""6.3: average our U-Net's tumour probability with nnU-Net's, on one fold's VALIDATION patients, and score every mix.

    ../.venv/bin/python ensemble.py --data ../data/full/nnunet/Dataset001_LungGTV --splits ../data/full/splits.json \\
        --fold 0 --ours b5_long_fold0 --nnunet ../data/full/prob_nnunet_resencL/val_fold0 --name b6_avg_resencL_fold0

combined = w * ours + (1 - w) * nnU-Net (several --nnunet folders are averaged first), for w in --weights.
w = 0 is nnU-Net alone, w = 1 is our U-Net alone, so the table always holds both single models too.
Writes runs/<name>/settings.json + summary.json in the same shape as a prediction-only run, so collect.py lists it.
Refuses a --name that already exists. Test patients are never touched here.
"""
import argparse
import json
import os
import time
from pathlib import Path

import numpy as np
import torch

from train import HERE, build, code_fingerprint, dice, load, new_run_dir, one_piece, predict_prob, write_json


def nnunet_prob(folders, pid):
    """nnU-Net's saved tumour probability (class 1), averaged over the given prediction folders."""
    return np.mean([np.load(Path(f) / f"{pid}.npz")["probabilities"][1].astype(np.float32) for f in folders], axis=0)


def mask(prob, cutoff, how):
    return (prob > cutoff).astype(np.uint8) if how == "all" else one_piece(prob, cutoff, how)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", required=True)
    ap.add_argument("--splits", required=True)
    ap.add_argument("--fold", type=int, required=True)
    ap.add_argument("--ours", required=True, help="our finished run for this fold (its best.pt)")
    ap.add_argument("--nnunet", nargs="+", required=True, help="folder(s) of nnU-Net .npz probabilities for this fold's val patients")
    ap.add_argument("--weights", type=float, nargs="+", default=[0, 0.25, 0.4, 0.5, 0.6, 0.75, 1])
    ap.add_argument("--cutoffs", type=float, nargs="+", default=[0.3, 0.4, 0.5])
    ap.add_argument("--pieces", nargs="+", choices=["all", "largest", "confident"], default=["all", "largest", "confident"])
    ap.add_argument("--name", required=True)
    a = ap.parse_args()

    run = new_run_dir(a.name)
    device = "cuda" if torch.cuda.is_available() else "mps" if torch.backends.mps.is_available() else "cpu"
    ck = torch.load(HERE / "runs" / a.ours / "best.pt", map_location=device)
    assert ck["args"]["fold"] == a.fold, f"{a.ours} was trained for fold {ck['args']['fold']}, not {a.fold}"
    net = build(ck["args"]).to(device).eval()
    net.load_state_dict(ck["model"])
    record = {"name": a.name, "exp": "B6.3 average", "model": "average",
              "change": f"w x {a.ours} + (1 - w) x nnU-Net {', '.join(Path(f).parent.name for f in a.nnunet)}",
              "job": os.environ.get("SLURM_JOB_ID"), "started": time.strftime("%Y-%m-%d %H:%M:%S"),
              "code": code_fingerprint(), "fold": a.fold, "scored_on": "val", "args": vars(a)}
    write_json(run / "settings.json", record)

    key = lambda w, c, h: f"w{w}_{c}_{h}"
    per = {key(w, c, h): {} for w in a.weights for c in a.cutoffs for h in a.pieces}
    for pid in json.load(open(a.splits))["folds"][a.fold]["val"]:
        img, lab = load(Path(a.data), pid)
        ours = predict_prob(net, img, ck["args"]["patch"], device, ck.get("norm"), gauss=True)
        nn = nnunet_prob(a.nnunet, pid)
        assert ours.shape == nn.shape == lab.shape, f"{pid}: shapes differ {ours.shape} {nn.shape} {lab.shape}"
        for w in a.weights:
            prob = w * ours + (1 - w) * nn
            for c in a.cutoffs:
                for h in a.pieces:
                    m = mask(prob, c, h)
                    per[key(w, c, h)][pid] = {"dice": round(float(dice(m, lab)), 4),
                                             "vol_diff_pct": round(100 * (int(m.sum()) - int(lab.sum())) / int(lab.sum()), 1)}
        c, h = a.cutoffs[-1], a.pieces[0]
        print(pid, *[f"w{w}: {per[key(w, c, h)][pid]['dice']}" for w in a.weights], f"(cut-off {c}, {h})", flush=True)

    rows = [{"variant": k, "val_dice": round(float(np.mean([r["dice"] for r in d.values()])), 4),
             "found": sum(r["dice"] > 0.1 for r in d.values()), "n_val": len(d),
             "median_vol_diff_pct": float(np.median([r["vol_diff_pct"] for r in d.values()]))} for k, d in per.items()]
    for r in sorted(rows, key=lambda r: -r["val_dice"])[:8]:
        print(f"{r['variant']:<22} val Dice {r['val_dice']:.3f}  found {r['found']}/{r['n_val']}")
    write_json(run / "summary.json", {**record, "rows": rows, "per_patient": per, "finished": time.strftime("%Y-%m-%d %H:%M:%S")})


if __name__ == "__main__":
    main()
