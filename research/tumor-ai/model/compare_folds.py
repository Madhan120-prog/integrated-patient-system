"""Compare two nnU-Net trainings on the SAME validation patients (all 5 folds pooled), per patient, with a
95% range from resampling patients (bootstrap). This is the v2 switching rule's first half (plan.md):
v2 must be better beyond the 95% range, and not worse on small tumours (< 20 cc).

    python compare_folds.py runs/nnunet_full/Dataset001_LungGTV/<trainer> runs/nnunet_full/Dataset003_LungV2/<trainer>
"""
import json
import sys
from pathlib import Path

import numpy as np
import SimpleITK as sitk


def per_patient(train_dir):
    out = {}
    for k in range(5):
        s = json.load(open(Path(train_dir) / f"fold_{k}" / "validation" / "summary.json"))
        for c in s["metric_per_case"]:
            out[Path(c["reference_file"]).name] = (c["metrics"]["1"]["Dice"], c["reference_file"])
    return out


def main(old_dir, new_dir):
    old, new = per_patient(old_dir), per_patient(new_dir)
    assert set(old) == set(new), f"different validation patients: {len(set(old) ^ set(new))} differ"
    pids = sorted(old)
    a = np.array([old[p][0] for p in pids])
    b = np.array([new[p][0] for p in pids])
    cc = []
    for p in pids:
        im = sitk.ReadImage(old[p][1])
        cc.append((sitk.GetArrayViewFromImage(im) > 0).sum() * np.prod(im.GetSpacing()) / 1000)
    cc = np.array(cc)
    rng = np.random.default_rng(42)
    for name, m in [("all", np.ones(len(pids), bool)), ("small <20 cc", cc < 20)]:
        d = b[m] - a[m]
        boot = [d[rng.integers(0, len(d), len(d))].mean() for _ in range(10000)]
        lo, hi = np.percentile(boot, [2.5, 97.5])
        print(f"{name:13} n={m.sum():3}  old {a[m].mean():.3f}  new {b[m].mean():.3f}  "
              f"difference {d.mean():+.3f} (95% range {lo:+.3f} to {hi:+.3f})  new better/worse on {(d > 0).sum()}/{(d < 0).sum()}")


if __name__ == "__main__":
    main(*sys.argv[1:3])
