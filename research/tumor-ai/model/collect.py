"""One table of every run, read from the runs' own records (nothing is re-run, nothing in runs/ is changed).

    cd ~/tumor-ai/model && ../.venv/bin/python collect.py

Our runs:     runs/<name>/summary.json (older runs without one: best Dice from log.csv)
nnU-Net runs: ../runs/nnunet_full/*/<trainer>__<plans>__<config>/fold_<k>/validation/summary.json
Each row is compared with the baseline on the same fold: E3 (full_e3_fold<k>) for our runs,
nnU-Net 3d_fullres for nnU-Net runs. The table is rebuilt from the records every time and saved to
../results/all_runs.csv.
"""
import argparse
import csv
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent


def ours(runs):
    rows = []
    for run in sorted(p for p in runs.iterdir() if p.is_dir()):
        s = json.loads((run / "summary.json").read_text()) if (run / "summary.json").exists() else None
        if s and "rows" in s:                                   # prediction-only run: one row per variant
            on = " on TRAINING patients" if s.get("scored_on") == "train" else ""
            rows += [{"name": f"{run.name} [{r['variant']}]", "exp": s["exp"], "change": f"{s['change']} [{r['variant']}]{on}",
                      "model": s.get("model", "our U-Net"), "fold": s["fold"], "val_dice": r["val_dice"], "found": f"{r['found']}/{r['n_val']}",
                      "size_vs_doctor_pct": r["median_vol_diff_pct"], "job": s["job"], "finished": s["finished"]}
                     for r in s["rows"]]
        elif s:
            rows.append({"name": run.name, "exp": s["exp"], "change": s["change"], "model": "our U-Net", "fold": s["fold"],
                         "val_dice": s["best_val_dice"], "found": f"{s['found']}/{s['n_val']}", "size_vs_doctor_pct": "",
                         "job": s["job"], "finished": s["finished"]})
        elif (run / "log.csv").exists():                        # older runs (E3, E3-small) kept only log.csv
            dices = [float(r["val_dice"]) for r in csv.DictReader(open(run / "log.csv"))]
            started = (run / "settings.json").exists()
            rows.append({"name": run.name, "exp": "E3" if run.name.startswith("full_e3") else "",
                         "change": "unfinished: running, or crashed (see its log)" if started else "baseline (older run)",
                         "model": "our U-Net",
                         "fold": int(run.name[-1]) if run.name[-1].isdigit() else "", "val_dice": max(dices) if dices else "",
                         "found": "", "size_vs_doctor_pct": "", "job": "", "finished": ""})
    return rows


def nnunet(root):
    rows = []
    for f in sorted(root.glob("*/*/fold_*/validation/summary.json")):
        trainer, plans, config = f.parents[2].name.split("__")
        fold = int(f.parents[1].name.split("_")[1])
        first = trainer == "nnUNetTrainer_250epochs" and plans == "nnUNetPlans"   # E1 / E2 as first run
        name = f"nnunet_{config}" if first else f"nnunet_{config}_{trainer}_{plans}"
        rows.append({"name": f"{name}_fold{fold}", "exp": ("E1" if config == "3d_fullres" else "E2" if config == "2d" else "") if first else "B4 nnU-Net",
                     "change": f"{config} {trainer} {plans}", "model": "nnU-Net", "fold": fold,
                     "val_dice": round(json.loads(f.read_text())["foreground_mean"]["Dice"], 4),
                     "found": "", "size_vs_doctor_pct": "", "job": "", "finished": ""})
    return rows


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--runs", default=HERE / "runs", type=Path)
    ap.add_argument("--nnunet", default=HERE.parent / "runs" / "nnunet_full", type=Path)
    ap.add_argument("--out", default=HERE.parent / "results" / "all_runs.csv", type=Path)
    a = ap.parse_args()

    rows = ours(a.runs) + (nnunet(a.nnunet) if a.nnunet.exists() else [])
    base = {(r["model"], r["fold"]): r["val_dice"] for r in rows
            if r["name"] in [f"full_e3_fold{r['fold']}", f"nnunet_3d_fullres_fold{r['fold']}"]}
    for r in rows:
        b = base.get((r["model"], r["fold"]))
        r["vs_baseline"] = f"{r['val_dice'] - b:+.3f}" if b is not None and r["val_dice"] != "" else ""
    rows.sort(key=lambda r: (str(r["exp"]), r["name"]))

    a.out.parent.mkdir(parents=True, exist_ok=True)
    with open(a.out, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)
    print(f"{'experiment':<6} {'run':<36} {'fold':>4} {'val Dice':>8} {'vs base':>8} {'found':>6} {'size%':>6}  what changed")
    for r in rows:
        print(f"{r['exp']:<6} {r['name']:<36} {r['fold']:>4} {r['val_dice']:>8} {r['vs_baseline']:>8} {r['found']:>6} "
              f"{r['size_vs_doctor_pct']!s:>6}  {r['change']}")
    print(f"\n{len(rows)} runs -> {a.out}   (baseline: E3 for our U-Net, nnU-Net 3d_fullres for nnU-Net, same fold)")


if __name__ == "__main__":
    main()
