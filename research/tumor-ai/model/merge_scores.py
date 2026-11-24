"""Join the parts of a split evaluate.py run (--part K/N) into one CSV and print the usual summary.

    python merge_scores.py ../results/anhui_parts/anhui_asls_v1_part*.csv --out ../results/anhui_asls_v1.csv
"""
import argparse
import csv
from pathlib import Path

from evaluate import summary


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("parts", nargs="+")
    ap.add_argument("--out", required=True)
    ap.add_argument("--expect", type=int, default=0, help="number of patients there should be (refuse if not)")
    a = ap.parse_args()
    if Path(a.out).exists():
        raise SystemExit(f"{a.out} already exists (results are never overwritten).")
    rows = [r for p in sorted(a.parts) for r in csv.DictReader(open(p))]
    pids = [r["patient"] for r in rows if r["model"] == rows[0]["model"]]
    assert len(pids) == len(set(pids)), "a patient appears in two parts"
    if a.expect:
        assert len(pids) == a.expect, f"{len(pids)} patients in the parts, expected {a.expect}"
    with open(a.out, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=rows[0].keys())
        w.writeheader()
        w.writerows(rows)
    for r in rows:
        r.update(dice=float(r["dice"]), hd95_mm=float(r["hd95_mm"]), vol_diff_pct=float(r["vol_diff_pct"]),
                 gtv_cc=float(r["gtv_cc"]), found=r["found"] == "True")
    print(f"{len(pids)} patients from {len(a.parts)} parts")
    summary(rows, a.out)


if __name__ == "__main__":
    main()
