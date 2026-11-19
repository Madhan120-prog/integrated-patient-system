"""E10/E11 data, part 1: NSCLC Radiogenomics (TCIA, public, CC BY 3.0) -> the same NIfTI layout as Lung1.

    python prep/10_radiogenomics.py download data/radiogenomics/raw     # login node (needs internet), ~1 GB + CTs
    python prep/10_radiogenomics.py convert  data/radiogenomics/raw data/radiogenomics   # compute node

download: first the 144 tumour outlines (DICOM SEG, 0.9 GB), then ONLY the CT series each outline was drawn on
          (the collection holds 91 GB of CT, most of it not outlined). Already-downloaded series are skipped.
convert:  CT in HU, oriented like Lung1 (LPS), -> imagesTr/RG-<id>_0000.nii.gz; outline -> labelsTr/RG-<id>.nii.gz
          (1 = tumour); a QC picture per case; cases.csv with size, slice gap and any issue (issue = left out).
"""
import csv
import importlib.util
import sys
from pathlib import Path

import numpy as np
import pydicom
import SimpleITK as sitk

COLLECTION = "NSCLC Radiogenomics"
HERE = Path(__file__).resolve().parent
_spec = importlib.util.spec_from_file_location("convert", HERE / "02_convert.py")
convert = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(convert)                 # reuse read_ct and qc_picture


def download(raw: Path):
    from tcia_utils import nbia
    series = nbia.getSeries(collection=COLLECTION)
    segs = [s for s in series if s["Modality"] == "SEG"]
    print(f"{len(segs)} outlines ({sum(s['FileSize'] for s in segs) / 1e9:.1f} GB)")
    nbia.downloadSeries([s["SeriesInstanceUID"] for s in segs], path=str(raw / "seg"), input_type="list")
    wanted = set()
    for f in (raw / "seg").rglob("*.dcm"):
        d = pydicom.dcmread(f, stop_before_pixels=True)
        wanted.add(d.ReferencedSeriesSequence[0].SeriesInstanceUID)
    cts = [s for s in series if s["Modality"] == "CT" and s["SeriesInstanceUID"] in wanted]
    print(f"{len(cts)} CT series referenced by the outlines ({sum(s['FileSize'] for s in cts) / 1e9:.1f} GB)")
    nbia.downloadSeries([s["SeriesInstanceUID"] for s in cts], path=str(raw / "ct"), input_type="list")
    keys = ["PatientID", "Modality", "SeriesInstanceUID", "ImageCount", "FileSize", "DateReleased"]
    with open(raw / "series.csv", "w", newline="") as f:      # dataset version record
        w = csv.DictWriter(f, fieldnames=keys, extrasaction="ignore")
        w.writeheader()
        w.writerows(segs + cts)


def seg_mask(seg_path, ct: sitk.Image) -> np.ndarray:
    """DICOM SEG -> (z, y, x) uint8 on the CT grid. Each SEG frame is one slice plane; its position says which slice.
    All segments are merged (this collection has one: the primary tumour)."""
    ds = pydicom.dcmread(seg_path)
    frames = ds.pixel_array
    frames = frames[None] if frames.ndim == 2 else frames
    nx, ny, nz = ct.GetSize()
    d = np.array(ct.GetDirection()).reshape(3, 3)
    iop = np.array(ds.SharedFunctionalGroupsSequence[0].PlaneOrientationSequence[0].ImageOrientationPatient, float)
    if not np.allclose(iop, [*d[:, 0], *d[:, 1]], atol=1e-3):
        raise ValueError("outline is tilted differently from the CT")
    mask = np.zeros((nz, ny, nx), np.uint8)
    for frame, fg in zip(frames, ds.PerFrameFunctionalGroupsSequence):
        ipp = [float(v) for v in fg.PlanePositionSequence[0].ImagePositionPatient]
        i, j, k = (int(round(v)) for v in ct.TransformPhysicalPointToContinuousIndex(ipp))
        if not 0 <= k < nz:
            continue
        if frame.shape != (ny, nx) or (i, j) != (0, 0):
            raise ValueError(f"outline grid {frame.shape} at ({i},{j}) does not match the CT {ny}x{nx}")
        mask[k] |= (frame > 0).astype(np.uint8)
    return mask


def slice_gaps(ct_dir: Path):
    pos = []
    for f in Path(ct_dir).glob("*.dcm"):
        d = pydicom.dcmread(f, stop_before_pixels=True)
        o = np.array(d.ImageOrientationPatient, float)
        pos.append(float(np.dot(np.cross(o[:3], o[3:]), np.array(d.ImagePositionPatient, float))))
    return np.diff(np.sort(pos))


def to_lps(img: sitk.Image) -> sitk.Image:
    """Same axis order and direction as Lung1 (identity direction), so the models see the body the same way."""
    return sitk.DICOMOrient(img, "LPS")


def convert_all(raw: Path, out: Path, prefix="RG"):
    ds_dir = out / "nnunet"
    for d in (ds_dir / "imagesTr", ds_dir / "labelsTr", out / "qc"):
        d.mkdir(parents=True, exist_ok=True)
    ct_dirs = {}
    for f in (raw / "ct").rglob("*.dcm"):
        ct_dirs.setdefault(pydicom.dcmread(f, stop_before_pixels=True).SeriesInstanceUID, f.parent)
    cases = []
    for seg in sorted((raw / "seg").rglob("*.dcm")):
        h = pydicom.dcmread(seg, stop_before_pixels=True)
        pid, uid = f"{prefix}-{h.PatientID}", h.ReferencedSeriesSequence[0].SeriesInstanceUID
        row = {"patient": pid, "gtv_cc": "", "tumour_slices": "", "slice_mm": "", "pixel_mm": "", "issues": ""}
        try:
            if uid not in ct_dirs:
                raise ValueError("its CT was not downloaded")
            gaps = slice_gaps(ct_dirs[uid])
            if gaps.max() - gaps.min() > 0.1:
                raise ValueError(f"uneven slice gaps {gaps.min():.1f}-{gaps.max():.1f} mm")
            ct = convert.read_ct(str(ct_dirs[uid]))
            mask = seg_mask(seg, ct)
            if not mask.any():
                raise ValueError("empty outline")
            label = sitk.GetImageFromArray(mask)
            label.CopyInformation(ct)
            ct, label = to_lps(ct), to_lps(label)
            sitk.WriteImage(sitk.Cast(ct, sitk.sitkInt16), str(ds_dir / "imagesTr" / f"{pid}_0000.nii.gz"))
            sitk.WriteImage(label, str(ds_dir / "labelsTr" / f"{pid}.nii.gz"))
            arr, m = sitk.GetArrayFromImage(ct), sitk.GetArrayFromImage(label)
            convert.qc_picture(arr, m, out / "qc" / f"{pid}.png")
            sp = ct.GetSpacing()
            row.update(gtv_cc=round(float(m.sum() * np.prod(sp) / 1000), 1), tumour_slices=int((m.sum(axis=(1, 2)) > 0).sum()),
                       slice_mm=round(sp[2], 2), pixel_mm=round(sp[0], 3))
            if sp[2] < 2:
                row["note"] = "thin slices"
        except Exception as e:                    # one bad case must not stop the rest; it is listed with its reason
            row["issues"] = str(e)
        cases.append(row)
        print(pid, row["issues"] or f"{row['gtv_cc']} cc, slices {row['slice_mm']} mm", flush=True)
    write_cases(out / "cases.csv", cases)
    ok = [c for c in cases if not c["issues"]]
    print(f"\n{len(ok)} of {len(cases)} usable -> {ds_dir}; {sum(c.get('note') == 'thin slices' for c in ok)} with thin slices")


def write_cases(path, cases):
    keys = list(dict.fromkeys(k for c in cases for k in c))
    with open(path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=keys)
        w.writeheader()
        w.writerows(cases)


if __name__ == "__main__":
    cmd, *args = sys.argv[1:]
    download(Path(args[0])) if cmd == "download" else convert_all(Path(args[0]), Path(args[1]))
