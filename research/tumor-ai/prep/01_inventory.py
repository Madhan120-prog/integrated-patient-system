"""Step 1: data check. One row per patient, so we know what we have before trusting it.

Reads only DICOM headers (no pixels), so it is fast. Works on any folder layout:
files are grouped by what their headers say, not by folder names.

    python prep/01_inventory.py <dicom_root> data/inventory.csv
"""
import csv
import re
import sys
from collections import defaultdict
from pathlib import Path

import numpy as np
import pydicom

# The primary tumour is "GTV-1" in NSCLC-Radiomics; "gtv-2", "gtv-3" are extra lesions (usually lymph nodes).
PRIMARY_GTV = re.compile(r"^gtv[-_ ]?1$", re.I)
ANY_GTV = re.compile(r"^gtv", re.I)


def scan(root: Path):
    """Group every DICOM file by patient -> CT series, and patient -> RTSTRUCT."""
    ct = defaultdict(lambda: defaultdict(list))
    rts = defaultdict(list)
    for f in root.rglob("*.dcm"):
        ds = pydicom.dcmread(f, stop_before_pixels=True)
        if ds.Modality == "CT":
            ct[ds.PatientID][ds.SeriesInstanceUID].append((f, ds))
        elif ds.Modality == "RTSTRUCT":
            rts[ds.PatientID].append((f, ds))
    return ct, rts


def referenced_series(rt) -> str | None:
    """The CT series the outlines were drawn on."""
    try:
        return (rt.ReferencedFrameOfReferenceSequence[0].RTReferencedStudySequence[0]
                .RTReferencedSeriesSequence[0].SeriesInstanceUID)
    except (AttributeError, IndexError):
        return None


def describe(patient, series, rt_list):
    issues = []
    rt_path, rt = rt_list[0] if rt_list else (None, None)
    if not rt_list:
        issues.append("no RTSTRUCT")
    elif len(rt_list) > 1:
        issues.append(f"{len(rt_list)} RTSTRUCTs, using first")

    uid = referenced_series(rt) if rt else None
    if uid not in series:
        uid = max(series, key=lambda u: len(series[u]))   # fall back to the largest series
        if rt:
            issues.append("RTSTRUCT points to a CT series we don't have")
    if len(series) > 1:
        issues.append(f"{len(series)} CT series")

    slices = series[uid]
    first = slices[0][1]
    z = np.sort([float(ds.ImagePositionPatient[2]) for _, ds in slices])
    steps = np.diff(z)
    step = float(np.median(steps)) if len(steps) else 0.0
    if len(steps) and np.any(np.abs(steps - step) > 0.1):
        issues.append(f"uneven slice spacing ({steps.min():.2f}-{steps.max():.2f} mm), possible missing slices")
    if [round(float(v), 3) for v in first.ImageOrientationPatient] != [1, 0, 0, 0, 1, 0]:
        issues.append("non-standard orientation")

    rois = [r.ROIName for r in rt.StructureSetROISequence] if rt else []
    has_primary = any(PRIMARY_GTV.match(n.strip()) for n in rois)
    if rt and not has_primary:
        issues.append("no primary GTV")

    return {
        "patient": patient,
        "n_slices": len(slices),
        "slice_step_mm": round(step, 2),
        "pixel_mm": round(float(first.PixelSpacing[0]), 3),
        "rows": first.Rows, "cols": first.Columns,
        "manufacturer": str(first.get("Manufacturer", "")).strip(),
        "kernel": str(first.get("ConvolutionKernel", "")),
        "kvp": first.get("KVP", ""),
        "contrast": str(first.get("ContrastBolusAgent", "")).strip(),
        "has_primary_gtv": has_primary,
        "n_gtv": sum(bool(ANY_GTV.match(n.strip())) for n in rois),
        "roi_names": "|".join(rois),
        "ct_dir": str(slices[0][0].parent),
        "rtstruct": str(rt_path or ""),
        "issues": "; ".join(issues),
    }


def main(root, out):
    ct, rts = scan(Path(root))
    rows = [describe(p, ct[p], rts.get(p, [])) for p in sorted(ct)]
    Path(out).parent.mkdir(parents=True, exist_ok=True)
    with open(out, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=rows[0].keys())
        w.writeheader()
        w.writerows(rows)
    usable = sum(r["has_primary_gtv"] and not r["issues"] for r in rows)
    print(f"{len(rows)} patients, {usable} with no issues -> {out}")
    for r in rows:
        if r["issues"]:
            print(f"  {r['patient']}: {r['issues']}")


if __name__ == "__main__":
    main(*sys.argv[1:3])
