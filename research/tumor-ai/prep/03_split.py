"""Step 3: split by PATIENT (never by slice), balanced by tumour size.

- test: ~15% locked away, used once at the very end.
- folds: the rest in 5 groups; each model trains on 4 and is checked on the 5th, 5 times.
Written in nnU-Net's splits_final.json shape so every model uses the exact same split.

    python prep/03_split.py data/cases.csv data/splits.json
"""
import csv
import json
import random
import sys

SEED, TEST_FRACTION, FOLDS = 42, 0.15, 5


def split(cases, seed=SEED):
    rng = random.Random(seed)
    # Sort by tumour size, then deal patients out in groups so every part gets small and large tumours.
    ordered = sorted(cases, key=lambda c: float(c["gtv_cc"]))
    every = max(1, round(1 / TEST_FRACTION))
    test, rest = [], []
    for start in range(0, len(ordered), every):
        group = [c["patient"] for c in ordered[start:start + every]]
        rng.shuffle(group)
        test.append(group[0])
        rest += group[1:]
    folds = [[] for _ in range(FOLDS)]
    for i, pid in enumerate(rest):   # rest is still roughly size-ordered, so round-robin balances size
        folds[i % FOLDS].append(pid)
    cv = [{"train": sorted(p for j, f in enumerate(folds) if j != k for p in f), "val": sorted(folds[k])}
          for k in range(FOLDS)]
    return sorted(test), cv


def check(test, cv, all_ids):
    for f in cv:
        assert not set(f["train"]) & set(f["val"]), "patient in both train and val"
        assert not (set(f["train"]) | set(f["val"])) & set(test), "test patient leaked into training"
        assert set(f["train"]) | set(f["val"]) | set(test) == set(all_ids), "patient lost"


if __name__ == "__main__":
    cases = list(csv.DictReader(open(sys.argv[1])))
    test, cv = split(cases)
    check(test, cv, [c["patient"] for c in cases])
    json.dump({"seed": SEED, "test": test, "folds": cv}, open(sys.argv[2], "w"), indent=2)
    print(f"{len(cases)} patients: {len(test)} test, {len(cases) - len(test)} in {FOLDS} folds -> {sys.argv[2]}")
