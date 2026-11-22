"""Outside data, part 4: Anhui Chest Hospital ASLS26 / ESLS26 (Science Data Bank, CC0, doi 10.57760/sciencedb.29318)
-> the same NIfTI layout as Lung1, for testing (and later training, v2).

    python prep/13_anhui.py unzip   ~/Downloads/ASLS26.zip data/anhui/raw            # zipped DICOM + label NIfTI
    python prep/13_anhui.py convert data/anhui/raw/ASLS26 data/anhui ASLS             # compute node

Download the zips yourself in a browser (the site marks them "not for bots"), then copy them to BigBlue.
Each patient folder: <id>/<StudyUID>/<SeriesUID>/*.dcm and <id>_segmentation/<id>-label.nii.gz (1 = tumour).
ASLS26 masks are radiotherapy GTVs (2+ oncologists, consensus); ESLS26 masks are diagnostic outlines (radiologists).

The authors 'inverted the third row' of the orientation when they made their own NIfTI files, so the mask is not
trusted blindly: it is placed on the CT by its header when the headers agree, else by index or head-feet flipped,
whichever looks like a lung tumour (solid inside, more air around); unclear cases are left out with the reason.
Also recorded: how many separate pieces the mask has (lymph nodes inside the "GTVs" would show as extra pieces).
"""
import json
import sys
import zipfile
from pathlib import Path

import numpy as np
import SimpleITK as sitk
from scipy import ndimage

sys.path.insert(0, str(Path(__file__).resolve().parent))
rg = __import__("10_radiogenomics")                 # reuse read_ct, qc_picture, to_lps, write_cases


def unzip(zip_path: Path, raw: Path):
    raw.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(zip_path) as z:            # zipfile drops absolute paths and '..' parts
        z.extractall(raw)
    print("unzipped to", raw)


def same_grid(a: sitk.Image, b: sitk.Image, tol=1e-2):
    return (a.GetSize() == b.GetSize() and np.allclose(a.GetSpacing(), b.GetSpacing(), atol=tol)
            and np.allclose(a.GetOrigin(), b.GetOrigin(), atol=0.5) and np.allclose(a.GetDirection(), b.GetDirection(), atol=tol))


def solid(ct_arr, m):
    """How much the mask looks like a lung tumour: share of tissue (HU > -500) inside the mask minus the share in a
    thin ring around it (in-plane). On the tumour: solid inside, lung air around (high). Misplaced onto liver or heart:
    solid inside and around (near 0). Misplaced into the lung: air inside (negative)."""
    if not m.any():
        return 0.0
    ring = ndimage.binary_dilation(m > 0, structure=np.array([[[0, 0, 0], [0, 0, 0], [0, 0, 0]], [[0, 1, 0], [1, 1, 1], [0, 1, 0]],
                                                              [[0, 0, 0], [0, 0, 0], [0, 0, 0]]], bool), iterations=4) & (m == 0)
    tissue = ct_arr > -500
    return float(tissue[m > 0].mean() - tissue[ring].mean())


def place(ct: sitk.Image, lab: sitk.Image):
    """The mask as an array on the CT's grid, and how it was placed (header / index / zflip)."""
    ct_arr = sitk.GetArrayFromImage(ct)
    lab_arr = (sitk.GetArrayFromImage(lab) > 0).astype(np.uint8)
    if same_grid(ct, lab):
        return lab_arr, "header", solid(ct_arr, lab_arr)
    if lab.GetSize() != ct.GetSize():
        raise ValueError(f"mask size {lab.GetSize()} differs from the CT {ct.GetSize()}")
    flip = lab_arr[::-1].copy()
    s_idx, s_flip = solid(ct_arr, lab_arr), solid(ct_arr, flip)
    best, other, how = (lab_arr, flip, "index") if s_idx >= s_flip else (flip, lab_arr, "zflip")
    s_best, s_other = max(s_idx, s_flip), min(s_idx, s_flip)
    if s_best < 0.15 or s_best - s_other < 0.1:
        raise ValueError(f"alignment unclear (tumour-likeness: as stored {s_idx:.2f}, head-feet flipped {s_flip:.2f})")
    return best, how, s_best


def find_case(folder: Path):
    labels = sorted(folder.rglob("*-label.nii.gz"))
    dcm_dirs = sorted({f.parent for f in folder.rglob("*.dcm")}, key=lambda d: -len(list(d.glob("*.dcm"))))
    if not labels:
        raise ValueError("no -label.nii.gz")
    if not dcm_dirs:
        raise ValueError("no DICOM slices")
    return dcm_dirs[0], labels[0]


def convert_all(raw: Path, out: Path, prefix: str):
    ds_dir = out / "nnunet"
    for d in (ds_dir / "imagesTr", ds_dir / "labelsTr", out / "qc"):
        d.mkdir(parents=True, exist_ok=True)
    cases = []
    for folder in sorted(p for p in raw.iterdir() if p.is_dir() and not p.name.endswith("_segmentation")):
        pid = f"{prefix}-{folder.name.split('-')[-1]}"
        row = {"patient": pid, "source_id": folder.name, "gtv_cc": "", "tumour_slices": "", "slice_mm": "", "pixel_mm": "",
               "align": "", "tumour_likeness": "", "pieces": "", "largest_piece_pct": "", "issues": ""}
        try:
            dcm_dir, label_f = find_case(folder)    # both subfolders sit inside the patient folder (paper, Fig. 3)
            gaps = rg.slice_gaps(dcm_dir)
            if gaps.max() - gaps.min() > 0.1:
                raise ValueError(f"uneven slice gaps {gaps.min():.1f}-{gaps.max():.1f} mm")
            ct = rg.convert.read_ct(str(dcm_dir))
            m, how, frac = place(ct, sitk.ReadImage(str(label_f)))
            if not m.any():
                raise ValueError("empty outline")
            lab, n = ndimage.label(m)
            sizes = np.bincount(lab.ravel())[1:]
            label = sitk.GetImageFromArray(m)
            label.CopyInformation(ct)
            ct, label = rg.to_lps(ct), rg.to_lps(label)
            sitk.WriteImage(sitk.Cast(ct, sitk.sitkInt16), str(ds_dir / "imagesTr" / f"{pid}_0000.nii.gz"))
            sitk.WriteImage(label, str(ds_dir / "labelsTr" / f"{pid}.nii.gz"))
            arr, mm = sitk.GetArrayFromImage(ct), sitk.GetArrayFromImage(label)
            rg.convert.qc_picture(arr, mm, out / "qc" / f"{pid}.png")
            sp = ct.GetSpacing()
            row.update(gtv_cc=round(float(mm.sum() * np.prod(sp) / 1000), 1), tumour_slices=int((mm.sum(axis=(1, 2)) > 0).sum()),
                       slice_mm=round(sp[2], 2), pixel_mm=round(sp[0], 3), align=how, tumour_likeness=round(frac, 2),
                       pieces=int(n), largest_piece_pct=round(100 * sizes.max() / sizes.sum()))
            if sp[2] < 2:
                row["note"] = "thin slices"
        except Exception as e:                      # one bad case must not stop the rest; it is listed with its reason
            row["issues"] = str(e)
        cases.append(row)
        print(pid, row["issues"] or f"{row['gtv_cc']} cc, {row['pieces']} piece(s), placed by {row['align']}, "
              f"slices {row['slice_mm']} mm", flush=True)
    rg.write_cases(out / "cases.csv", cases)
    ok = [c["patient"] for c in cases if not c["issues"]]
    json.dump({"source": "Anhui Chest Hospital, Science Data Bank doi 10.57760/sciencedb.29318 (CC0)",
               "test": ok}, open(out / f"splits_{prefix.lower()}.json", "w"), indent=2)
    multi = sum(1 for c in cases if not c["issues"] and c["pieces"] > 1)
    print(f"\n{len(ok)} of {len(cases)} usable -> {ds_dir}; {multi} with more than one piece; "
          f"placed: " + ", ".join(f"{k} {sum(c['align'] == k for c in cases)}" for k in ("header", "index", "zflip")))


if __name__ == "__main__":
    cmd, *args = sys.argv[1:]
    unzip(Path(args[0]), Path(args[1])) if cmd == "unzip" else convert_all(Path(args[0]), Path(args[1]), args[2])
