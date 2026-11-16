"""Prototype engine: a CT scan (DICOM) in, the AI's tumour outline out, as an RTSTRUCT a planning system opens.

    .venv/bin/python prototype/engine.py <DICOM folder or .zip> --out prototype/cases/<name>

Research draft only. Everything runs on this computer; nothing is sent anywhere.
Models are read from prototype/models/ (see prototype/README.md):
    nnunet/      a trained nnU-Net folder (plans.json, dataset.json, fold_<k>/checkpoint_final.pth)
    unet.pt      our U-Net (a best.pt from model/runs/)
    splits.json  optional: lets the page say whether this patient was used to train the model
With both models the outline is 25% ours + 75% nnU-Net, cut-off 0.3, most-confident piece (batch 6 winner).
If the upload holds the doctor's RTSTRUCT (GTV-1), the AI outline is compared with it.
"""
import argparse
import importlib.util
import json
import shutil
import sys
import time
import zipfile
from pathlib import Path

import numpy as np
import pydicom
import SimpleITK as sitk
import torch

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(ROOT / "model"))
from train import build, one_piece, predict_prob  # noqa: E402

_spec = importlib.util.spec_from_file_location("convert", ROOT / "prep" / "02_convert.py")
convert = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(convert)            # reuse read_ct, gtv_mask and qc_picture from data preparation

CUTS = [round(0.1 * i, 1) for i in range(1, 10)]   # "how sure must the AI be": 10% .. 90%
DEFAULT_CUT = 0.3
WEIGHT_OURS = 0.25


# ---------- 1. sort the upload ----------
def gather(src: Path, case: Path, log):
    """Find the CT series (the one with most slices) and the doctor's RTSTRUCT, copy them into the case folder."""
    files = []
    if src.is_file() and zipfile.is_zipfile(src):
        up = case / "upload"
        up.mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(src) as z:                 # members get numbered names: no path from the zip is used
            for i, m in enumerate(n for n in z.infolist() if not n.is_dir()):
                (up / f"{i:05d}").write_bytes(z.read(m))
        files = sorted(up.iterdir())
    else:
        files = [f for f in Path(src).rglob("*") if f.is_file()]
    series, rts = {}, []
    for f in files:
        try:
            d = pydicom.dcmread(f, stop_before_pixels=True)
        except Exception:
            continue
        if d.get("Modality") == "CT":
            series.setdefault(d.SeriesInstanceUID, []).append(f)
        elif d.get("Modality") == "RTSTRUCT":
            rts.append(f)
    if not series:
        raise ValueError("No CT slices found. Upload a zipped DICOM folder of one CT scan.")
    ct_files = max(series.values(), key=len)
    ct_dir = case / "ct"
    ct_dir.mkdir(parents=True, exist_ok=True)
    for i, f in enumerate(ct_files):
        shutil.copy(f, ct_dir / f"{i:04d}.dcm")
    log(f"Found a CT with {len(ct_files)} slices" + (f" (and {len(series) - 1} other series, ignored)" if len(series) > 1 else ""))
    doctor = None
    for f in rts:
        names = [r.ROIName.strip() for r in pydicom.dcmread(f).StructureSetROISequence]
        if any(convert.PRIMARY_GTV.match(n) for n in names):
            doctor = case / "doctor_rtstruct.dcm"
            shutil.copy(f, doctor)
            log("Found the doctor's outline (GTV-1): the AI will be compared with it")
            break
    else:
        log("No doctor's outline in the upload: the AI outline is shown on its own")
    shutil.rmtree(case / "upload", ignore_errors=True)  # the copies in ct/ are all we keep
    return ct_dir, doctor


def slice_order(ct_dir: Path):
    """For each slice in rt-utils' order, the matching slice index in SimpleITK's order (both sort by position,
    computed here so the RTSTRUCT lands on the right slices whatever the scan's direction)."""
    names = sitk.ImageSeriesReader.GetGDCMSeriesFileNames(str(ct_dir))
    pos = []
    for n in names:
        d = pydicom.dcmread(n, stop_before_pixels=True)
        o = np.array(d.ImageOrientationPatient, float)
        pos.append(float(np.dot(np.cross(o[:3], o[3:]), np.array(d.ImagePositionPatient, float))))
    return np.argsort(pos, kind="stable")


# ---------- 2. the models ----------
class Models:
    def __init__(self, folder: Path = HERE / "models", device=None, mirror=False):
        self.device = device or ("cuda" if torch.cuda.is_available() else "mps" if torch.backends.mps.is_available() else "cpu")
        self.unet = self.nn = None
        self.folds, self.used_folds = [], set()
        if (folder / "unet.pt").exists():
            ck = torch.load(folder / "unet.pt", map_location="cpu", weights_only=False)
            net = build(ck["args"])
            net.load_state_dict(ck["model"])
            self.unet = (net.to(self.device).eval(), ck)
            self.used_folds.add(ck["args"]["fold"])
        nn_dir = folder / "nnunet"
        if (nn_dir / "plans.json").exists():
            from nnunetv2.inference.predict_from_raw_data import nnUNetPredictor
            self.folds = sorted(int(p.name[5:]) for p in nn_dir.glob("fold_*") if (p / "checkpoint_final.pth").exists())
            if not self.folds:
                raise SystemExit(f"{nn_dir} has no fold_<k>/checkpoint_final.pth (see prototype/README.md)")
            p = nnUNetPredictor(tile_step_size=0.5, use_gaussian=True, use_mirroring=mirror,
                                perform_everything_on_device=self.device == "cuda", device=torch.device(self.device),
                                allow_tqdm=False)
            p.initialize_from_trained_model_folder(str(nn_dir), use_folds=tuple(self.folds), checkpoint_name="checkpoint_final.pth")
            self.nn = p
            self.used_folds.update(self.folds)
        if not (self.unet or self.nn):
            raise SystemExit(f"No model in {folder}: add nnunet/ and/or unet.pt (see prototype/README.md)")
        splits = folder / "splits.json"
        self.splits = json.loads(splits.read_text()) if splits.exists() else None

    def describe(self):
        parts = []
        if self.nn:
            parts.append(f"nnU-Net ({Path(self.nn.plans_manager.plans_name).name}, fold{'s' if len(self.folds) > 1 else ''} "
                         f"{', '.join(map(str, self.folds))})")
        if self.unet:
            parts.append(f"our U-Net ({self.unet[1]['args'].get('name', 'unet')})")
        mix = f" averaged {int(WEIGHT_OURS * 100)}% ours / {100 - int(WEIGHT_OURS * 100)}% nnU-Net" if self.nn and self.unet else ""
        return " + ".join(parts) + mix + f", on {self.device}"

    def patient_role(self, pid):
        """Was this patient used to train the models? Decides whether the score is a fair check."""
        if not self.splits:
            return "unknown", "Can't tell whether this patient was used in training (no splits.json next to the models)."
        if pid in self.splits["test"]:
            return "test", "Locked test patient: kept for the one final test. Its score counts as that test."
        if any(pid in self.splits["folds"][k]["train"] for k in self.used_folds):
            return "trained", "This patient was used to TRAIN the model, so the score looks better than it really is."
        if any(pid in f["val"] for f in self.splits["folds"]):
            return "fair", "Not used to train this model: a fair check."
        return "outside", "Not in our dataset: a fair, outside check."

    @torch.inference_mode()
    def probability(self, ct: sitk.Image, log):
        img = sitk.GetArrayFromImage(ct)
        probs = []
        if self.nn:
            t = time.time()
            log(f"nnU-Net is reading the scan ({len(self.folds)} fold{'s' if len(self.folds) > 1 else ''})")
            _, p = self.nn.predict_single_npy_array(img.astype(np.float32)[None], {"spacing": list(ct.GetSpacing())[::-1]},
                                                    None, None, True)
            assert p[1].shape == img.shape, f"nnU-Net returned {p[1].shape}, scan is {img.shape}"
            probs.append((1 - WEIGHT_OURS if self.unet else 1.0, p[1].astype(np.float32)))
            log(f"nnU-Net done in {time.time() - t:.0f} s")
        if self.unet:
            t = time.time()
            net, ck = self.unet
            log("Our U-Net is reading the scan")
            p = predict_prob(net, img.astype(np.int16), ck["args"]["patch"], self.device, ck.get("norm"), gauss=True)
            probs.append((WEIGHT_OURS if self.nn else 1.0, p))
            log(f"Our U-Net done in {time.time() - t:.0f} s")
        return sum(w * p for w, p in probs)


# ---------- 3. outlines at every sureness level ----------
def outlines(prob):
    """One uint16 per voxel, bit i set when the voxel is in the outline at CUTS[i] (most-confident piece),
    kept only inside the box around everything above the lowest cut-off. Returns (bits, box start)."""
    zs, ys, xs = np.nonzero(prob > CUTS[0])
    if not len(zs):
        return np.zeros((0, 0, 0), np.uint16), [0, 0, 0]
    lo = [int(zs.min()), int(ys.min()), int(xs.min())]
    hi = [int(zs.max()) + 1, int(ys.max()) + 1, int(xs.max()) + 1]
    crop = prob[lo[0]:hi[0], lo[1]:hi[1], lo[2]:hi[2]]
    bits = np.zeros(crop.shape, np.uint16)
    for i, c in enumerate(CUTS):
        bits |= one_piece(crop, c, "confident").astype(np.uint16) << i
    z, y, x = np.nonzero(bits)                       # shrink to the outlines themselves (stray specks are dropped)
    return np.ascontiguousarray(bits[z.min():z.max() + 1, y.min():y.max() + 1, x.min():x.max() + 1]), \
        [lo[0] + int(z.min()), lo[1] + int(y.min()), lo[2] + int(x.min())]


def full_mask(bits, lo, shape, cut):
    m = np.zeros(shape, np.uint8)
    if bits.size:
        i = CUTS.index(cut)
        m[lo[0]:lo[0] + bits.shape[0], lo[1]:lo[1] + bits.shape[1], lo[2]:lo[2] + bits.shape[2]] = (bits >> i) & 1
    return m


def measure(bits, lo, i, prob, doctor, spacing):
    """Size, sureness and overlap with the doctor for the outline at CUTS[i], counted inside the outline's box only."""
    sx, sy, sz = spacing
    box = tuple(slice(l, l + n) for l, n in zip(lo, bits.shape))
    m = (bits >> i) & 1
    dsum = int(doctor.sum()) if doctor is not None else 0
    inter = int((m & doctor[box]).sum()) if doctor is not None and bits.size else 0
    r = {"found": bool(m.any()), "cc": 0, "size_mm": [0, 0, 0], "slices": 0, "sure": 0, "dice": None}
    if doctor is not None:
        r["dice"] = round(2 * inter / (int(m.sum()) + dsum), 3) if int(m.sum()) + dsum else 1.0
        r["vs_doctor_pct"] = round(100 * (int(m.sum()) - dsum) / max(dsum, 1), 1)
    if not r["found"]:
        return r
    z, y, x = np.nonzero(m)
    r.update(cc=round(float(m.sum() * sx * sy * sz / 1000), 1),
             size_mm=[round(float((x.max() - x.min() + 1) * sx)), round(float((y.max() - y.min() + 1) * sy)),
                      round(float((z.max() - z.min() + 1) * sz))],
             slices=int(len(np.unique(z))), sure=round(float(prob[box][m > 0].mean()), 3))
    return r


def write_rtstruct(case: Path, cut: float):
    """The AI outline at one cut-off as an RTSTRUCT tied to this CT (rt-utils), named as a research draft."""
    from rt_utils import RTStructBuilder
    s = json.loads((case / "summary.json").read_text())
    r = np.load(case / "result.npz")
    m = full_mask(r["bits"], list(r["lo"]), tuple(s["shape"]), cut)
    rt = RTStructBuilder.create_new(dicom_series_path=str(case / "ct"))
    rt.add_roi(mask=m[slice_order(case / "ct")].transpose(1, 2, 0).astype(bool), color=[255, 176, 0],
               name="GTV_AI_DRAFT", description=f"AI research draft, cut-off {cut}. Not for treatment without review.")
    out = case / "out" / f"AI_outline_{s['patient']}_cut{int(cut * 100)}.dcm"
    out.parent.mkdir(exist_ok=True)
    rt.save(str(out))
    return out


def write_mask(case: Path, cut: float):
    s = json.loads((case / "summary.json").read_text())
    r = np.load(case / "result.npz")
    ct = convert.read_ct(str(case / "ct"))
    img = sitk.GetImageFromArray(full_mask(r["bits"], list(r["lo"]), tuple(s["shape"]), cut))
    img.CopyInformation(ct)
    out = case / "out" / f"AI_mask_{s['patient']}_cut{int(cut * 100)}.nii.gz"
    out.parent.mkdir(exist_ok=True)
    sitk.WriteImage(img, str(out))
    return out


# ---------- 4. the whole case ----------
def run(src: Path, case: Path, models: Models, log=print):
    t0 = time.time()
    case.mkdir(parents=True, exist_ok=True)
    ct_dir, doctor_rt = gather(Path(src), case, log)
    ct = convert.read_ct(str(ct_dir))
    first = pydicom.dcmread(sorted(ct_dir.iterdir())[0], stop_before_pixels=True)
    pid = str(first.get("PatientID", "unknown"))
    img = sitk.GetArrayFromImage(ct).astype(np.int16)
    log(f"Patient {pid}: {img.shape[0]} slices of {img.shape[2]} x {img.shape[1]} pixels, "
        f"{ct.GetSpacing()[0]:.2f} mm pixels, {ct.GetSpacing()[2]:.1f} mm apart")
    doctor = None
    if doctor_rt:
        try:
            doctor = convert.gtv_mask(str(doctor_rt), ct)
        except Exception as e:                       # a broken outline must not stop the AI
            log(f"Could not read the doctor's outline ({e}); carrying on without it")
    role, role_text = models.patient_role(pid)
    log(f"Models: {models.describe()}")
    prob = models.probability(ct, log)
    log("Drawing the outline at every sureness level (10% .. 90%)")
    bits, lo = outlines(prob)
    per_cut = [{"cut": c, **measure(bits, lo, i, prob, doctor, ct.GetSpacing())} for i, c in enumerate(CUTS)]

    img.tofile(case / "ct.bin")                      # raw slices for the review page
    np.savez_compressed(case / "result.npz", bits=bits, lo=np.array(lo))
    bits.tofile(case / "ai.bin")
    dlo, dshape = [0, 0, 0], [0, 0, 0]
    if doctor is not None and doctor.any():
        z, y, x = np.nonzero(doctor)
        dlo = [int(z.min()), int(y.min()), int(x.min())]
        d = doctor[dlo[0]:z.max() + 1, dlo[1]:y.max() + 1, dlo[2]:x.max() + 1]
        dshape = list(d.shape)
        np.ascontiguousarray(d).tofile(case / "doctor.bin")
    summary = {"patient": pid, "study_date": str(first.get("StudyDate", "")), "shape": list(img.shape),
               "spacing": list(ct.GetSpacing()), "models": models.describe(), "role": role, "role_text": role_text,
               "has_doctor": doctor is not None, "ai_lo": lo, "ai_shape": list(bits.shape), "doctor_lo": dlo,
               "doctor_shape": dshape, "cuts": CUTS, "default_cut": DEFAULT_CUT, "per_cut": per_cut,
               "seconds": round(time.time() - t0), "finished": time.strftime("%Y-%m-%d %H:%M:%S")}
    (case / "summary.json").write_text(json.dumps(summary, indent=2))
    convert.qc_picture(img, full_mask(bits, lo, img.shape, DEFAULT_CUT) if bits.size else np.zeros_like(img, np.uint8),
                       case / "overview.png")
    d = next(p for p in per_cut if p["cut"] == DEFAULT_CUT)
    log(f"Done in {summary['seconds']} s: " + (f"tumour {d['cc']} cc on {d['slices']} slices" if d["found"] else "no tumour found")
        + (f", overlap with the doctor {d['dice']:.2f}" if d["dice"] is not None else ""))
    return summary


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("src", help="DICOM folder or .zip of one CT (optionally with the doctor's RTSTRUCT)")
    ap.add_argument("--out", required=True, help="case folder to create")
    ap.add_argument("--cut", type=float, default=DEFAULT_CUT, choices=CUTS)
    ap.add_argument("--models", default=HERE / "models", type=Path)
    ap.add_argument("--mirror", action="store_true", help="nnU-Net test-time mirroring: as scored, ~8x slower")
    a = ap.parse_args()
    out = Path(a.out)
    if out.exists() and any(out.iterdir()):
        sys.exit(f"{out} already exists; choose a new --out")
    run(Path(a.src), out, Models(a.models, mirror=a.mirror))
    print("RTSTRUCT:", write_rtstruct(out, a.cut))
    print("mask:    ", write_mask(out, a.cut))
    print("picture: ", out / "overview.png")


if __name__ == "__main__":
    main()
