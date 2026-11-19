"""E10 data, part 2: Medical Segmentation Decathlon Task06 Lung (public, CC BY-SA 4.0) -> the same layout as Lung1.

    python prep/11_msd_lung.py download data/msd_lung/raw                  # login node, one 9.2 GB archive
    python prep/11_msd_lung.py convert  data/msd_lung/raw data/msd_lung    # compute node

The archive is NIfTI already. convert: orient like Lung1 (LPS), keep HU as whole numbers, label 1 = tumour,
-> imagesTr/MSD-lung_XXX_0000.nii.gz + labelsTr/MSD-lung_XXX.nii.gz, a QC picture each, cases.csv.
Only the 63 training cases have outlines (imagesTs has none) so only those are used.
MSD's lung cases may be patients also in NSCLC Radiogenomics: prep/12_combine.py finds and drops such repeats.
"""
import sys
import tarfile
import urllib.request
from pathlib import Path

import numpy as np
import SimpleITK as sitk

URL = "https://msd-for-monai.s3-us-west-2.amazonaws.com/Task06_Lung.tar"   # the copy MONAI downloads from

sys.path.insert(0, str(Path(__file__).resolve().parent))
rg = __import__("10_radiogenomics")                 # reuse to_lps, write_cases and qc_picture


def download(raw: Path):
    raw.mkdir(parents=True, exist_ok=True)
    tar = raw / "Task06_Lung.tar"
    if not tar.exists():
        print("downloading", URL)
        urllib.request.urlretrieve(URL, tar.with_suffix(".part"))
        tar.with_suffix(".part").rename(tar)
    if not (raw / "Task06_Lung").exists():
        with tarfile.open(tar) as t:
            t.extractall(raw, filter="data")       # "data" filter: no paths outside raw/
    print("ready:", raw / "Task06_Lung")


def convert_all(raw: Path, out: Path):
    src, ds_dir = raw / "Task06_Lung", out / "nnunet"
    for d in (ds_dir / "imagesTr", ds_dir / "labelsTr", out / "qc"):
        d.mkdir(parents=True, exist_ok=True)
    cases = []
    for img_f in sorted(p for p in (src / "imagesTr").glob("lung_*.nii.gz")):   # skips macOS "._" copies
        pid = "MSD-" + img_f.name.replace(".nii.gz", "")
        row = {"patient": pid, "gtv_cc": "", "tumour_slices": "", "slice_mm": "", "pixel_mm": "", "issues": ""}
        try:
            ct = rg.to_lps(sitk.ReadImage(str(img_f)))
            lab = rg.to_lps(sitk.ReadImage(str(src / "labelsTr" / img_f.name)))
            arr = sitk.GetArrayFromImage(ct)
            if arr.min() > -500:
                raise ValueError(f"values do not look like HU (lowest {arr.min()})")
            m = (sitk.GetArrayFromImage(lab) > 0).astype(np.uint8)
            if not m.any():
                raise ValueError("empty outline")
            label = sitk.GetImageFromArray(m)
            label.CopyInformation(ct)
            ct16 = sitk.Cast(sitk.Round(ct) if ct.GetPixelID() in (sitk.sitkFloat32, sitk.sitkFloat64) else ct, sitk.sitkInt16)
            sitk.WriteImage(ct16, str(ds_dir / "imagesTr" / f"{pid}_0000.nii.gz"))
            sitk.WriteImage(label, str(ds_dir / "labelsTr" / f"{pid}.nii.gz"))
            rg.convert.qc_picture(sitk.GetArrayFromImage(ct16), m, out / "qc" / f"{pid}.png")
            sp = ct.GetSpacing()
            row.update(gtv_cc=round(float(m.sum() * np.prod(sp) / 1000), 1), tumour_slices=int((m.sum(axis=(1, 2)) > 0).sum()),
                       slice_mm=round(sp[2], 2), pixel_mm=round(sp[0], 3))
            if sp[2] < 2:
                row["note"] = "thin slices"
        except Exception as e:
            row["issues"] = str(e)
        cases.append(row)
        print(pid, row["issues"] or f"{row['gtv_cc']} cc, slices {row['slice_mm']} mm", flush=True)
    rg.write_cases(out / "cases.csv", cases)
    ok = [c for c in cases if not c["issues"]]
    print(f"\n{len(ok)} of {len(cases)} usable -> {ds_dir}; {sum(c.get('note') == 'thin slices' for c in ok)} with thin slices")


if __name__ == "__main__":
    cmd, *args = sys.argv[1:]
    download(Path(args[0])) if cmd == "download" else convert_all(Path(args[0]), Path(args[1]))
