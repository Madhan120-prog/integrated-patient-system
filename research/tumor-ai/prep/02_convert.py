"""Step 2: turn each patient's DICOM into two files a model can read, in nnU-Net's layout.

    imagesTr/LUNG1-001_0000.nii.gz   the CT, one 3D file, values in Hounsfield units
    labelsTr/LUNG1-001.nii.gz        the mask, 1 = primary tumour (GTV-1), 0 = everything else

Also writes one check picture per patient (data/qc/) and cases.csv with tumour size.

    python prep/02_convert.py data/inventory.csv data
"""
import csv
import json
import re
import sys
from pathlib import Path

import numpy as np
import pydicom
import SimpleITK as sitk
from PIL import Image, ImageDraw

PRIMARY_GTV = re.compile(r"^gtv[-_ ]?1$", re.I)
DATASET = "Dataset001_LungGTV"


def read_ct(ct_dir: str) -> sitk.Image:
    """Read a DICOM series in slice order. SimpleITK applies RescaleSlope/Intercept, so values are HU."""
    reader = sitk.ImageSeriesReader()
    reader.SetFileNames(reader.GetGDCMSeriesFileNames(ct_dir))
    return reader.Execute()


def gtv_mask(rtstruct: str, ct: sitk.Image) -> np.ndarray:
    """Rasterise the GTV-1 outline onto the CT grid. Returns a (z, y, x) uint8 array."""
    rt = pydicom.dcmread(rtstruct)
    number = next(r.ROINumber for r in rt.StructureSetROISequence if PRIMARY_GTV.match(r.ROIName.strip()))
    contours = next(c for c in rt.ROIContourSequence if c.ReferencedROINumber == number).ContourSequence
    nx, ny, nz = ct.GetSize()
    mask = np.zeros((nz, ny, nx), np.uint8)
    for c in contours:
        pts = np.asarray(c.ContourData, float).reshape(-1, 3)
        if len(pts) < 3:      # single points are markers, not areas
            continue
        idx = [ct.TransformPhysicalPointToContinuousIndex(p.tolist()) for p in pts]
        k = int(round(idx[0][2]))
        if not 0 <= k < nz:
            continue
        layer = Image.new("1", (nx, ny))
        ImageDraw.Draw(layer).polygon([(i, j) for i, j, _ in idx], fill=1)
        mask[k] ^= np.array(layer, np.uint8)   # XOR, so a contour inside another becomes a hole
    return mask


def qc_picture(ct: np.ndarray, mask: np.ndarray, path: Path):
    """CT slice where the tumour is largest, lung window, tumour in red."""
    k = int(mask.sum(axis=(1, 2)).argmax())
    lo, hi = -1350, 150   # lung window: level -600, width 1500
    grey = (np.clip((ct[k] - lo) / (hi - lo), 0, 1) * 255).astype(np.uint8)
    rgb = np.stack([grey] * 3, -1)
    rgb[mask[k] > 0] = (0.5 * rgb[mask[k] > 0] + [127, 0, 0]).astype(np.uint8)
    Image.fromarray(rgb).save(path)


def main(inventory, out):
    out = Path(out)
    ds_dir = out / "nnunet" / DATASET
    for sub in ("imagesTr", "labelsTr"):
        (ds_dir / sub).mkdir(parents=True, exist_ok=True)
    (out / "qc").mkdir(parents=True, exist_ok=True)

    cases = []
    for row in csv.DictReader(open(inventory)):
        if row["has_primary_gtv"] != "True" or row["issues"]:
            print(f"skip {row['patient']}: {row['issues'] or 'no primary GTV'}")
            continue
        pid = row["patient"]
        ct = read_ct(row["ct_dir"])
        mask = gtv_mask(row["rtstruct"], ct)
        label = sitk.GetImageFromArray(mask)
        label.CopyInformation(ct)   # same position, spacing and direction as the CT
        sitk.WriteImage(ct, str(ds_dir / "imagesTr" / f"{pid}_0000.nii.gz"))
        sitk.WriteImage(label, str(ds_dir / "labelsTr" / f"{pid}.nii.gz"))
        qc_picture(sitk.GetArrayFromImage(ct), mask, out / "qc" / f"{pid}.png")

        voxel_cc = np.prod(ct.GetSpacing()) / 1000
        cases.append({"patient": pid, "gtv_cc": round(float(mask.sum() * voxel_cc), 1),
                      "tumour_slices": int((mask.sum(axis=(1, 2)) > 0).sum()),
                      "manufacturer": row["manufacturer"]})
        print(f"{pid}: GTV {cases[-1]['gtv_cc']} cc on {cases[-1]['tumour_slices']} slices")

    json.dump({"channel_names": {"0": "CT"}, "labels": {"background": 0, "tumour": 1},
               "numTraining": len(cases), "file_ending": ".nii.gz"},
              open(ds_dir / "dataset.json", "w"), indent=2)
    with open(out / "cases.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=cases[0].keys())
        w.writeheader()
        w.writerows(cases)


if __name__ == "__main__":
    main(*sys.argv[1:3])
