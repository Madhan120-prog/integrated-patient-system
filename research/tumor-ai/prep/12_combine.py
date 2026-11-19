"""E10/E11 data, part 3: one combined training set, with every split rule kept.

    python prep/12_combine.py data/full data/radiogenomics data/msd_lung

1. Repeats: an MSD lung case that is the same scan as a Radiogenomics case (same size, same spacing, nearly the same
   HU values) is dropped, so no patient can sit on both the training and the test side.
2. Radiogenomics is split by tumour size into half A = OUTSIDE TEST (locked, used once, E11) and half B = training.
3. Lung1 keeps its 5 folds and its 60 test patients exactly. Radiogenomics B + MSD join the TRAINING side of every fold;
   validation stays Lung1 only, so scores compare 1:1 with everything before.
Writes:
  data/full/nnunet/Dataset002_LungMulti/{imagesTr,labelsTr}  links to the files (no copies) + dataset.json
  data/full/splits_multi.json        same shape as splits.json, plus "outside_test" (A) and "extra_train"
  data/full/splits_final_multi.json  the same folds in nnU-Net's shape (copied in after nnU-Net's preparation)
  data/full/outside_A/{imagesTr,labelsTr}  links to the outside-test cases, for prediction and scoring
Refuses to run if splits_multi.json exists: splits are made once and never changed.
"""
import csv
import json
import random
import sys
from pathlib import Path

import numpy as np
import SimpleITK as sitk

SEED = 42


def usable(out: Path):
    return [r for r in csv.DictReader(open(out / "cases.csv")) if not r["issues"]]


def fingerprint(path):
    im = sitk.ReadImage(str(path))
    return im.GetSize(), np.round(im.GetSpacing(), 2), sitk.GetArrayFromImage(im)[::4, ::8, ::8].astype(np.float32)


def repeats(msd_dir: Path, rg_dir: Path, msd_ids, rg_ids):
    """MSD cases that are the same scan as a Radiogenomics case."""
    rg = {p: fingerprint(rg_dir / "nnunet" / "imagesTr" / f"{p}_0000.nii.gz") for p in rg_ids}
    found = {}
    for m in msd_ids:
        size, sp, a = fingerprint(msd_dir / "nnunet" / "imagesTr" / f"{m}_0000.nii.gz")
        for p, (s2, sp2, b) in rg.items():
            if size == s2 and np.allclose(sp, sp2, atol=0.02) and np.abs(a - b).mean() < 5:
                found[m] = p
                break
    return found


def halves(cases):
    """Size-balanced halves: sort by tumour size, then one of each neighbouring pair to each half."""
    rng = random.Random(SEED)
    ordered = sorted(cases, key=lambda c: float(c["gtv_cc"]))
    a, b = [], []
    for i in range(0, len(ordered), 2):
        pair = [c["patient"] for c in ordered[i:i + 2]]
        rng.shuffle(pair)
        a.append(pair[0])
        b += pair[1:]
    return sorted(a), sorted(b)


def link(src: Path, dst: Path):
    dst.parent.mkdir(parents=True, exist_ok=True)
    if not dst.exists():
        dst.symlink_to(src.resolve())


def main(full, rg_dir, msd_dir):
    full, rg_dir, msd_dir = Path(full), Path(rg_dir), Path(msd_dir)
    out_splits = full / "splits_multi.json"
    if out_splits.exists():
        sys.exit(f"{out_splits} exists: splits are made once and never changed")
    lung1 = json.load(open(full / "splits.json"))
    rg_cases, msd_cases = usable(rg_dir), usable(msd_dir)
    dup = repeats(msd_dir, rg_dir, [c["patient"] for c in msd_cases], [c["patient"] for c in rg_cases])
    for m, p in dup.items():
        print(f"repeat: {m} is the same scan as {p}; {m} dropped")
    msd_ids = sorted(c["patient"] for c in msd_cases if c["patient"] not in dup)
    outside, rg_train = halves(rg_cases)
    extra = sorted(rg_train + msd_ids)

    lung1_ids = sorted({p for f in lung1["folds"] for p in f["train"] + f["val"]})   # Lung1 test stays OUT
    src1 = full / "nnunet" / "Dataset001_LungGTV"
    ds = full / "nnunet" / "Dataset002_LungMulti"
    for pid in lung1_ids:
        link(src1 / "imagesTr" / f"{pid}_0000.nii.gz", ds / "imagesTr" / f"{pid}_0000.nii.gz")
        link(src1 / "labelsTr" / f"{pid}.nii.gz", ds / "labelsTr" / f"{pid}.nii.gz")
    for pid in extra:
        src = (rg_dir if pid.startswith("RG-") else msd_dir) / "nnunet"
        link(src / "imagesTr" / f"{pid}_0000.nii.gz", ds / "imagesTr" / f"{pid}_0000.nii.gz")
        link(src / "labelsTr" / f"{pid}.nii.gz", ds / "labelsTr" / f"{pid}.nii.gz")
    for pid in outside:
        link(rg_dir / "nnunet" / "imagesTr" / f"{pid}_0000.nii.gz", full / "outside_A" / "imagesTr" / f"{pid}_0000.nii.gz")
        link(rg_dir / "nnunet" / "labelsTr" / f"{pid}.nii.gz", full / "outside_A" / "labelsTr" / f"{pid}.nii.gz")
    json.dump({"channel_names": {"0": "CT"}, "labels": {"background": 0, "tumour": 1},
               "numTraining": len(lung1_ids) + len(extra), "file_ending": ".nii.gz"}, open(ds / "dataset.json", "w"), indent=2)

    folds = [{"train": sorted(f["train"] + extra), "val": f["val"]} for f in lung1["folds"]]
    test, held = set(lung1["test"]), set(outside)
    for f in folds:                                    # the rules, checked rather than trusted
        assert not set(f["train"]) & set(f["val"]), "patient in both train and val"
        assert not set(f["train"]) & (test | held), "a test patient leaked into training"
        assert all(p.startswith("LUNG1-") for p in f["val"]), "validation must stay Lung1 only"
    assert not held & set(extra) and not set(dup) & set(extra)
    json.dump({"seed": SEED, "test": lung1["test"], "outside_test": outside, "extra_train": extra,
               "repeats_dropped": dup, "folds": folds}, open(out_splits, "w"), indent=2)
    json.dump(folds, open(full / "splits_final_multi.json", "w"), indent=2)
    print(f"\nDataset002: {len(lung1_ids)} Lung1 + {len(rg_train)} Radiogenomics B + {len(msd_ids)} MSD = "
          f"{len(lung1_ids) + len(extra)} cases; outside test A: {len(outside)}; Lung1 test untouched: {len(test)}")


if __name__ == "__main__":
    main(*sys.argv[1:4])
