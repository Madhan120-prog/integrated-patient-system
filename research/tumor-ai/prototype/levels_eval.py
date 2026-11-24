"""Numbers for the paper: the four-level explanations on a whole patient set (spec section 6).

For every patient: the recipe's probability -> outlines at all cut-offs (as the review desk) -> facts -> four texts.
Then: (1) check() notes per level, (2) the facts the reader is told vs the same facts measured on the doctor's
outline (side, part, volume, longest diameter), (3) Flesch-Kincaid grade per level, (4) time to build the texts.

    # fold-0 validation patients, fold-0 models (fair: never trained on)
    python prototype/levels_eval.py --set fold0 --data <Dataset001> --splits <splits.json> --runs <model/runs> \
        --ours b3_long_fold0 --nnunet-prob <prob_nnunet_resencL/val_fold0> <prob_nnunet_1000ep/val_fold0> --out <csv>
    # the 60 locked test patients, final models (the test is already spent: describing it is allowed, choosing is not)
    python prototype/levels_eval.py --set test ... --ours b3_long_fold0 b5_long_fold1 ... --nnunet-prob <.../test> ...

Nothing here changes the models or chooses a setting. See jobs/levels_eval.sbatch.
"""
import argparse
import csv
import json
import sys
import time
from pathlib import Path

import numpy as np
import SimpleITK as sitk
import torch

import engine
import levels
from engine import ROOT

sys.path.insert(0, str(ROOT / "model"))
from ensemble import nnunet_prob  # noqa: E402
from train import build, predict_prob  # noqa: E402

ROLE = {"fold0": "Not used to train this model: a fair check",
        "test": "Locked test patient: not used to train or choose the model",
        "outside": "Outside hospital: never used to train or choose the model"}


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--set", choices=["fold0", "test", "outside"], required=True, help="outside = the 'test' list of an outside splits file")
    ap.add_argument("--data", required=True, help="nnU-Net dataset folder with imagesTr/ and labelsTr/")
    ap.add_argument("--splits", required=True)
    ap.add_argument("--runs", default=str(ROOT / "model" / "runs"), help="folder holding our U-Net runs")
    ap.add_argument("--ours", nargs="*", default=[])
    ap.add_argument("--nnunet-prob", nargs="*", default=[])
    ap.add_argument("--weight", type=float, default=engine.WEIGHT_OURS)
    ap.add_argument("--cut", type=float, default=engine.DEFAULT_CUT)
    ap.add_argument("--model-text", default="25% our U-Net + 75% nnU-Net (ResEnc L 250 ep + nnU-Net 1000 ep)")
    ap.add_argument("--limit", type=int, default=0, help="first N patients only (a quick try)")
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    if Path(a.out).exists():
        raise SystemExit(f"{a.out} already exists (results are never overwritten). Use a new --out.")
    if not (a.ours or a.nnunet_prob):
        raise SystemExit("give --ours and/or --nnunet-prob")

    s = json.load(open(a.splits))
    pids = s["folds"][0]["val"] if a.set == "fold0" else s["test"]
    pids = pids[:a.limit] if a.limit else pids
    device = "cuda" if torch.cuda.is_available() else "mps" if torch.backends.mps.is_available() else "cpu"
    nets = []
    for name in a.ours:
        ck = torch.load(Path(a.runs) / name / "best.pt", map_location=device, weights_only=False)
        if a.set == "fold0":
            assert ck["args"]["fold"] == 0, f"{name} is a fold-{ck['args']['fold']} model: not fair on fold-0 patients"
        net = build(ck["args"]).to(device)
        net.load_state_dict(ck["model"])
        nets.append((net.eval(), ck["args"]["patch"], ck.get("norm")))
    data = Path(a.data)
    w = a.weight if nets and a.nnunet_prob else (1.0 if nets else 0.0)
    rows = []
    for pid in pids:
        img = sitk.ReadImage(str(data / "imagesTr" / f"{pid}_0000.nii.gz"))
        arr = sitk.GetArrayFromImage(img).astype(np.int16)
        gt = sitk.GetArrayFromImage(sitk.ReadImage(str(data / "labelsTr" / f"{pid}.nii.gz"))).astype(np.uint8)
        prob = 0
        if nets:
            with torch.inference_mode():
                prob = w * np.mean([predict_prob(n, arr, p, device, nm, True) for n, p, nm in nets], axis=0)
        if a.nnunet_prob:
            nn = nnunet_prob(a.nnunet_prob, pid)
            assert nn.shape == gt.shape, f"{pid}: nnU-Net {nn.shape} vs scan {gt.shape}"
            prob = prob + (1 - w) * nn
        bits, lo = engine.outlines(prob)
        row = engine.measure(bits, lo, engine.CUTS.index(a.cut), prob, gt, img.GetSpacing())

        t0 = time.perf_counter()
        lung = levels.lungs(arr, img)
        f = levels.facts_from(img, arr, bits, lo, a.cut, row, a.model_text, ROLE[a.set], lung)
        t1 = time.perf_counter()
        out = levels.explain(f)
        notes = {k: levels.check(k, out[k], f) for k in levels.LEVELS}
        t2 = time.perf_counter()
        d = levels.describe(gt, [0, 0, 0], img, lung)

        r = {"set": a.set, "patient": pid, "ai_found": f["found"], "doc_found": d["found"], "dice": row["dice"]}
        if f["found"]:   # what the physician / physicist levels say about certainty (paper: does it warn when wrong?)
            r.update(sure_pct=f.get("sure_pct"), edge_uncertain_pct=f.get("edge_uncertain_pct"),
                     size_group=f.get("size_group"))
        if f["found"] and d["found"]:
            r.update(ai_side=f["side"], doc_side=d["side"], same_side=f["side"] == d["side"],
                     ai_part=f["part"], doc_part=d["part"], same_part=f["part"] == d["part"],
                     ai_cc=f["volume_cc"], doc_cc=d["volume_cc"], vol_err_cc=round(f["volume_cc"] - d["volume_cc"], 1),
                     vol_err_pct=round(100 * (f["volume_cc"] - d["volume_cc"]) / max(d["volume_cc"], 0.1), 1),
                     ai_longest_mm=f["longest_mm"], doc_longest_mm=d["longest_mm"],
                     longest_err_mm=f["longest_mm"] - d["longest_mm"])
        for k in levels.LEVELS:
            r[f"grade_{k}"] = levels.fk_grade(out[k])
            r[f"notes_{k}"] = " | ".join(notes[k])
        r.update(ms_facts=round(1000 * (t1 - t0), 1), ms_texts=round(1000 * (t2 - t1), 2))
        rows.append(r)
        print(pid, f"{f.get('side')}/{f.get('part')} vs doctor {d.get('side')}/{d.get('part')}",
              f"{f.get('volume_cc')} vs {d.get('volume_cc')} cc", "notes:" if any(notes.values()) else "clean",
              *[n for v in notes.values() for n in v], flush=True)

    Path(a.out).parent.mkdir(parents=True, exist_ok=True)
    keys = list(dict.fromkeys(k for r in rows for k in r))
    with open(a.out, "w", newline="") as fh:
        wr = csv.DictWriter(fh, fieldnames=keys)
        wr.writeheader()
        wr.writerows(rows)
    summary(rows, a.set)
    print(f"\nper-patient rows -> {a.out}")


def summary(rows, name):
    n = len(rows)
    both = [r for r in rows if r["ai_found"] and r["doc_found"]]
    clean = {k: sum(not r[f"notes_{k}"] for r in rows) for k in levels.LEVELS}
    print(f"\n=== XAI levels, {name}: {n} patients, AI found {sum(r['ai_found'] for r in rows)}, compared on {len(both)}")
    print("1. texts with no unsupported number / flag: " + ", ".join(f"{k} {clean[k]}/{n}" for k in levels.LEVELS)
          + f"  (all {sum(clean.values())}/{4 * n})")
    if both:
        part_known = [r for r in both if r["ai_part"] and r["doc_part"]]
        print(f"2. same side as the doctor's outline {100 * np.mean([r['same_side'] for r in both]):.0f}%, "
              f"same part {100 * np.mean([r['same_part'] for r in part_known]):.0f}% (of {len(part_known)}); "
              f"volume error median {np.median([abs(r['vol_err_cc']) for r in both]):.1f} cc "
              f"({np.median([abs(r['vol_err_pct']) for r in both]):.0f}%); "
              f"longest diameter error median {np.median([abs(r['longest_err_mm']) for r in both]):.0f} mm")
    print("3. reading grade (Flesch-Kincaid, mean): " + ", ".join(
        f"{k} {np.mean([r[f'grade_{k}'] for r in rows]):.1f}" for k in levels.LEVELS))
    print(f"4. time: facts {np.median([r['ms_facts'] for r in rows]):.0f} ms, four texts + checks "
          f"{np.median([r['ms_texts'] for r in rows]):.2f} ms (medians)")


if __name__ == "__main__":
    main()
