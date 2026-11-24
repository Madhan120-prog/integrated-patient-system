"""v2 data: E10's training set + most of Anhui ASLS26, with a NEW locked test slice cut from Anhui first.

    python prep/14_v2.py data/full data/anhui          # on BigBlue, from ~/tumor-ai, after anhui_prep

1. Anhui's usable patients are split by tumour size (sorted, groups of 10, 3 of each group drawn with seed 42):
   30% = v2's LOCKED TEST (used once, by jobs/v2_test.sbatch), 70% = training.
2. Training labels: Lung1 GTVs are the primary tumour only, so an Anhui mask with more than one piece (likely lymph
   nodes) keeps only its largest piece for TRAINING (data/anhui/labels_primary/). Test labels stay as the hospital drew them.
3. E10's folds are kept exactly; Anhui training patients join the TRAINING side of every fold. Validation stays the same
   Lung1 patients, so v2's fold scores compare 1:1 with v1 (b4_resenc) and E10. Lung1 test and outside A stay out.
Writes:
  data/full/nnunet/Dataset003_LungV2/{imagesTr,labelsTr}   links (no copies) + dataset.json
  data/full/splits_v2.json, data/full/splits_final_v2.json  (nnU-Net's shape, copied in after nnU-Net's preparation)
  data/anhui/splits_v2.json {"test": [...], "train": [...]}, data/anhui/v2_test/imagesTr (links, for prediction)
Refuses to run if splits_v2.json exists: splits are made once and never changed.
"""
import csv
import json
import random
import sys
from pathlib import Path

import numpy as np
import SimpleITK as sitk
from scipy import ndimage

sys.path.insert(0, str(Path(__file__).resolve().parent))
cb = __import__("12_combine")                        # reuse link()

SEED, TEST_SHARE, GROUP = 42, 0.3, 10


def lock_test(cases):
    """Size-balanced draw: sort by tumour size, then TEST_SHARE of each group of GROUP neighbours."""
    rng = random.Random(SEED)
    ordered = sorted(cases, key=lambda c: (float(c["gtv_cc"]), c["patient"]))
    test = []
    for i in range(0, len(ordered), GROUP):
        g = [c["patient"] for c in ordered[i:i + GROUP]]
        test += rng.sample(g, round(TEST_SHARE * len(g)))
    return sorted(test), sorted(c["patient"] for c in cases if c["patient"] not in test)


def primary_label(src: Path, dst: Path):
    """The mask's largest 3D piece only (written once)."""
    if dst.exists():
        return
    im = sitk.ReadImage(str(src))
    lab, n = ndimage.label(sitk.GetArrayFromImage(im) > 0)
    keep = (lab == 1 + np.argmax(np.bincount(lab.ravel())[1:])).astype(np.uint8)
    out = sitk.GetImageFromArray(keep)
    out.CopyInformation(im)
    dst.parent.mkdir(parents=True, exist_ok=True)
    sitk.WriteImage(out, str(dst))


def main(full, anhui):
    full, anhui = Path(full), Path(anhui)
    out_splits = full / "splits_v2.json"
    if out_splits.exists():
        sys.exit(f"{out_splits} exists: splits are made once and never changed")
    e10 = json.load(open(full / "splits_multi.json"))
    cases = [r for r in csv.DictReader(open(anhui / "cases.csv")) if not r["issues"]]
    assert sorted(c["patient"] for c in cases) == sorted(json.load(open(anhui / "splits_asls.json"))["test"])
    test, train = lock_test(cases)
    multi = {c["patient"] for c in cases if int(c["pieces"]) > 1}

    src2 = full / "nnunet" / "Dataset002_LungMulti"
    ds = full / "nnunet" / "Dataset003_LungV2"
    old = sorted(p.name[:-len("_0000.nii.gz")] for p in (src2 / "imagesTr").glob("*_0000.nii.gz"))
    for pid in old:
        cb.link(src2 / "imagesTr" / f"{pid}_0000.nii.gz", ds / "imagesTr" / f"{pid}_0000.nii.gz")
        cb.link(src2 / "labelsTr" / f"{pid}.nii.gz", ds / "labelsTr" / f"{pid}.nii.gz")
    a_img, a_lab = anhui / "nnunet" / "imagesTr", anhui / "nnunet" / "labelsTr"
    for pid in train:
        cb.link(a_img / f"{pid}_0000.nii.gz", ds / "imagesTr" / f"{pid}_0000.nii.gz")
        lab = a_lab / f"{pid}.nii.gz"
        if pid in multi:
            primary_label(lab, anhui / "labels_primary" / f"{pid}.nii.gz")
            lab = anhui / "labels_primary" / f"{pid}.nii.gz"
        cb.link(lab, ds / "labelsTr" / f"{pid}.nii.gz")
    for pid in test:
        cb.link(a_img / f"{pid}_0000.nii.gz", anhui / "v2_test" / "imagesTr" / f"{pid}_0000.nii.gz")
    json.dump({"channel_names": {"0": "CT"}, "labels": {"background": 0, "tumour": 1},
               "numTraining": len(old) + len(train), "file_ending": ".nii.gz"}, open(ds / "dataset.json", "w"), indent=2)

    folds = [{"train": sorted(f["train"] + train), "val": f["val"]} for f in e10["folds"]]
    locked = set(e10["test"]) | set(e10["outside_test"]) | set(test)
    for f in folds:                                    # the rules, checked rather than trusted
        assert not set(f["train"]) & set(f["val"]), "patient in both train and val"
        assert not set(f["train"]) & locked, "a test patient leaked into training"
        assert all(p.startswith("LUNG1-") for p in f["val"]), "validation must stay Lung1 only"
    assert not set(test) & set(train) and len(test) + len(train) == len(cases)
    json.dump({"seed": SEED, "test": e10["test"], "outside_test": e10["outside_test"], "anhui_test": test,
               "extra_train": sorted(e10["extra_train"] + train), "anhui_largest_piece_only": sorted(multi & set(train)),
               "folds": folds}, open(out_splits, "w"), indent=2)
    json.dump(folds, open(full / "splits_final_v2.json", "w"), indent=2)
    json.dump({"seed": SEED, "test": test, "train": train}, open(anhui / "splits_v2.json", "w"), indent=2)
    print(f"Dataset003: {len(old)} E10 cases + {len(train)} Anhui = {len(old) + len(train)}; "
          f"Anhui locked test (v2): {len(test)}; multi-piece training masks cut to the largest piece: {len(multi & set(train))}")


if __name__ == "__main__":
    main(*sys.argv[1:3])
