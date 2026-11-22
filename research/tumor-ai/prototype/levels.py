"""'Explain this result' at four levels (patient, physician, physicist, AI / technical). No language model.

Code measures the outline (where, how big, how sure) into a fact sheet; each level is a fixed sentence template
filled from that sheet, so the levels cannot disagree with each other or invent a number. check() verifies that.

    .venv/bin/python prototype/levels.py --self-check                 synthetic scan with a known answer
    .venv/bin/python prototype/levels.py --case prototype/cases/t1    the four texts for a finished case

Spec: private/TUMOR_XAI_LEVELS_SPEC.md. Words like 'upper part' are thirds of that lung's height, not lobes.
"""
import argparse
import json
import re
import time
from functools import lru_cache
from pathlib import Path

import numpy as np
import SimpleITK as sitk
from scipy import ndimage
from scipy.spatial import ConvexHull

import engine

# Final test, 60 locked patients, job 3609438 (EXPERIMENTS.md, "Final test (once)"): 25% ours + 75% nnU-Net.
REFERENCE = {"n": 60, "dice": 0.677, "found": 52, "hd95_mm": 6.9,
             "by_group": {"small": 0.581, "medium": 0.768, "large": 0.682}}
SIZE_GROUPS = [("small", 0, 20), ("medium", 20, 100), ("large", 100, float("inf"))]   # cc, as in model/evaluate.py
BAND = (0.3, 0.7)          # "uncertain band": inside the 30% outline but not the 70% one

TEMPLATES = {
    "patient": "The computer found an area in the {part} part of your {side} lung that looks like a tumour. "
               "It is about {longest_cm} cm across. Your doctor has checked this outline. "
               "Your care team will explain what it means for you and what happens next.",
    "patient_none": "The computer did not mark a tumour on this scan. "
                    "Your doctor reviews every scan and will talk with you about the results.",
    "physician": "AI draft outline (research use): {side} lung, {part} part, slices {slice_from}–{slice_to} "
                 "({slices} slices). Volume {volume_cc} cc, longest axial diameter {longest_mm} mm. "
                 "Mean AI confidence inside the outline {sure_pct}% at the {cut_pct}% cut-off.{vs} "
                 "Check the outline on every slice before clinical use.",
    "physician_vs": " Compared with the doctor's outline: overlap (Dice) {dice:.2f}, volume {vs_pct:+.1f}%.",
    "physician_none": "No AI outline at the {cut_pct}% cut-off. Review the scan as usual; "
                      "a lower cut-off may show a faint candidate.",
    "physicist": "GTV_AI_DRAFT at cut-off {cut_pct}%: {volume_cc} cc, extent {sx} × {sy} × {sz} mm "
                 "(side × front-back × up-down). {band}{vs} Exported as RTSTRUCT for review in the planning system.",
    "physicist_band": "{edge_pct}% of the outlined volume lies in the uncertain band ({lo}–{hi}% confidence), "
                      "mostly on slices {where}.",
    "physicist_band_none": "None of the outlined volume lies in the uncertain band ({lo}–{hi}% confidence).",
    "physicist_vs": " Overlap with the clinical GTV: Dice {dice:.2f}; volume {vs_pct:+.1f}% vs the clinical outline.",
    "physicist_none": "No GTV_AI_DRAFT at cut-off {cut_pct}%: no voxel passes it, so no contour would be exported.",
    "ai": "Model: {model}. On our {ref_n} locked test patients this recipe reached Dice {ref_dice} "
          "(found {ref_found}/{ref_n}); for {size_group} tumours Dice {ref_group}. This tumour is {size_group} "
          "({volume_cc} cc); mean confidence {sure_pct}%, {edge_pct}% of the outline uncertain. {fair}. "
          "Known weak spots: small tumours, and occasionally outlining a nearby structure instead of the tumour.",
    "ai_none": "Model: {model}. On our {ref_n} locked test patients this recipe reached Dice {ref_dice} "
               "(found {ref_found}/{ref_n}). Nothing passes the {cut_pct}% cut-off on this scan. {fair}. "
               "Known weak spots: small tumours, and occasionally outlining a nearby structure instead of the tumour.",
}
LEVELS = ["patient", "physician", "physicist", "ai"]
_NUMBER = re.compile(r"\d+(?:\.\d+)?")
_OUTLOOK = re.compile(r"\b(survival|life expectancy|months to live|terminal|incurable|cure[ds]?|prognosis|outlook)\b", re.I)


# ---------- geometry ----------
def lungs(arr: np.ndarray, img: sitk.Image):
    """Both lungs: air (HU < -400) inside the body. Air touching the image's side edges is outside the body; the
    (up to) two largest remaining pieces are the lungs, split at their middle. Every 2nd pixel in-plane, for speed.
    Returns the midline column and each lung's physical z range, or None when no lung is found."""
    a = arr[:, ::2, ::2] < -400
    lab, n = ndimage.label(a)
    if not n:
        return None
    size = np.bincount(lab.ravel())
    size[0] = 0
    edge = np.unique(np.concatenate([lab[:, 0, :].ravel(), lab[:, -1, :].ravel(), lab[:, :, 0].ravel(), lab[:, :, -1].ravel()]))
    size[edge] = 0
    order = np.argsort(size)[::-1][:2]
    keep = [int(l) for l in order if size[l] and size[l] >= 0.1 * size[order[0]]]
    if not keep:
        return None
    z, _, x = np.nonzero(np.isin(lab, keep))
    x = x * 2
    mid = (x.min() + x.max()) / 2
    yc = arr.shape[1] / 2
    left_high = phys(img, mid + 1, yc, 0)[0] > phys(img, mid, yc, 0)[0]          # DICOM LPS: +x = patient's left
    out = {"mid_col": float(mid)}
    for side, sel in (("left", x >= mid if left_high else x < mid), ("right", x < mid if left_high else x >= mid)):
        zs = z[sel]
        if len(zs):
            pz = [phys(img, mid, yc, zs.min())[2], phys(img, mid, yc, zs.max())[2]]
            out[side] = [min(pz), max(pz)]
    return out


def phys(img, x, y, z):
    return img.TransformContinuousIndexToPhysicalPoint((float(x), float(y), float(z)))


def longest_axial(m: np.ndarray, sx: float, sy: float):
    """RECIST-style: longest distance across the outline on the slice where it is largest (pixel edges, mm)."""
    k = int(m.sum(axis=(1, 2)).argmax())
    y, x = np.nonzero(m[k])
    pts = np.concatenate([np.stack([x + dx, y + dy], 1) for dx in (0, 1) for dy in (0, 1)]).astype(float) * [sx, sy]
    if len(pts) > 4:
        try:
            pts = pts[ConvexHull(pts).vertices]
        except Exception:                            # a line of pixels: all points are on the hull anyway
            pass
    d = np.sqrt(((pts[:, None] - pts[None]) ** 2).sum(-1))
    return float(d.max()), k


def describe(m: np.ndarray, lo, img: sitk.Image, lung):
    """Where and how big one outline is. m is the outline inside its box, lo the box start (z, y, x)."""
    sx, sy, sz = img.GetSpacing()
    if not m.any():
        return {"found": False}
    z, y, x = np.nonzero(m)
    longest, kz = longest_axial(m, sx, sy)
    c = phys(img, x.mean() + lo[2], y.mean() + lo[1], z.mean() + lo[0])
    f = {"found": True, "volume_cc": round(float(m.sum() * sx * sy * sz / 1000), 1), "longest_mm": round(longest),
         "longest_cm": round(longest / 10, 1),
         "size_mm": [round(float((x.max() - x.min() + 1) * sx)), round(float((y.max() - y.min() + 1) * sy)),
                     round(float((z.max() - z.min() + 1) * sz))],
         "slice_from": int(z.min() + lo[0] + 1), "slice_to": int(z.max() + lo[0] + 1),
         "slices": int(len(np.unique(z))), "largest_slice": int(kz + lo[0] + 1), "side": None, "part": None}
    if lung:
        midx = phys(img, lung["mid_col"], y.mean() + lo[1], z.mean() + lo[0])[0]
        f["side"] = "left" if c[0] > midx else "right"
        zr = lung.get(f["side"])
        if zr and zr[1] > zr[0]:
            t = (c[2] - zr[0]) / (zr[1] - zr[0])        # 0 = bottom (feet) of that lung, 1 = top
            f["part"] = "upper" if t > 2 / 3 else "lower" if t < 1 / 3 else "middle"
    return f


# ---------- the fact sheet ----------
def size_group(cc):
    return next(g for g, a, b in SIZE_GROUPS if a <= cc < b)


def facts_from(img, arr, bits, lo, cut, row, model, role_text, lung="auto"):
    """Facts for the AI outline at `cut`. bits/lo as engine.outlines(); row = engine.measure() at that cut."""
    if lung == "auto":
        lung = lungs(arr, img)
    i = engine.CUTS.index(cut)
    m = ((bits >> i) & 1).astype(np.uint8) if bits.size else np.zeros((0, 0, 0), np.uint8)
    f = {"cut": cut, "cut_pct": round(cut * 100), "model": model, "fair_check": role_text,
         **describe(m, lo, img, lung)}
    if not f["found"]:
        return f
    lo_b, hi_b = engine.CUTS.index(BAND[0]), engine.CUTS.index(BAND[1])
    band = (((bits >> lo_b) & 1) == 1) & (((bits >> hi_b) & 1) == 0) & (m == 1)
    per_slice = band.sum(axis=(1, 2))
    f.update(volume_cc=row["cc"], sure_pct=round(row["sure"] * 100), size_mm=row["size_mm"],
             size_group=size_group(row["cc"]), edge_uncertain_pct=round(100 * band.sum() / m.sum()),
             uncertain_slices=sorted(int(k + lo[0] + 1) for k in np.argsort(per_slice)[::-1][:3] if per_slice[k]))
    if row.get("dice") is not None:
        f["vs_doctor"] = {"dice": round(row["dice"], 2), "volume_pct": row["vs_doctor_pct"]}
    return f


@lru_cache(maxsize=8)
def _case_geometry(case: str):
    img = engine.convert.read_ct(str(Path(case) / "ct"))
    arr = sitk.GetArrayFromImage(img).astype(np.int16)
    return img, arr, lungs(arr, img)


def facts(case_dir, cut):
    """Facts for a finished review-desk case (prototype/cases/<id>)."""
    case = Path(case_dir)
    s = json.loads((case / "summary.json").read_text())
    r = np.load(case / "result.npz")
    img, arr, lung = _case_geometry(str(case.resolve()))
    row = next(p for p in s["per_cut"] if p["cut"] == cut)
    f = facts_from(img, arr, r["bits"], list(r["lo"]), cut, row, s["models"], s["role_text"], lung)
    f["patient"] = s["patient"]
    return f


def doctor_facts(case_dir):
    """The same measurements on the doctor's outline (for comparing what each reader would be told)."""
    case = Path(case_dir)
    s = json.loads((case / "summary.json").read_text())
    if not s["has_doctor"] or not s["doctor_shape"][0]:
        return None
    img, _, lung = _case_geometry(str(case.resolve()))
    d = np.fromfile(case / "doctor.bin", np.uint8).reshape(s["doctor_shape"])
    return describe(d, s["doctor_lo"], img, lung)


# ---------- the four texts ----------
def _list(nums):
    nums = [str(n) for n in nums]
    return nums[0] if len(nums) == 1 else ", ".join(nums[:-1]) + " and " + nums[-1]


def explain(f):
    t, out = TEMPLATES, {"facts": f}
    fair = (f.get("fair_check") or "").strip().rstrip(".")
    ref = {"ref_n": REFERENCE["n"], "ref_dice": REFERENCE["dice"], "ref_found": REFERENCE["found"]}
    if not f["found"]:
        out["patient"] = t["patient_none"]
        out["physician"] = t["physician_none"].format(**f)
        out["physicist"] = t["physicist_none"].format(**f)
        out["ai"] = t["ai_none"].format(**f, **ref, fair=fair)
        return out
    side, part = f["side"] or "(side not determined)", f["part"] or "(part not determined)"
    vs = f.get("vs_doctor")
    lo, hi = round(BAND[0] * 100), round(BAND[1] * 100)
    band = (t["physicist_band"].format(edge_pct=f["edge_uncertain_pct"], lo=lo, hi=hi, where=_list(f["uncertain_slices"]))
            if f["uncertain_slices"] else t["physicist_band_none"].format(lo=lo, hi=hi))
    out["patient"] = t["patient"].format(part=part, side=side, longest_cm=f["longest_cm"])
    out["physician"] = t["physician"].format(**{**f, "side": side, "part": part},
                                             vs=t["physician_vs"].format(dice=vs["dice"], vs_pct=vs["volume_pct"]) if vs else "")
    sx, sy, sz = f["size_mm"]
    out["physicist"] = t["physicist"].format(cut_pct=f["cut_pct"], volume_cc=f["volume_cc"], sx=sx, sy=sy, sz=sz, band=band,
                                             vs=t["physicist_vs"].format(dice=vs["dice"], vs_pct=vs["volume_pct"]) if vs else "")
    out["ai"] = t["ai"].format(**f, **ref, fair=fair, ref_group=REFERENCE["by_group"][f["size_group"]],
                               edge_pct=f["edge_uncertain_pct"])
    return out


# ---------- the guard ----------
def _numbers(v):
    if isinstance(v, dict):
        return [n for x in v.values() for n in _numbers(x)]
    if isinstance(v, (list, tuple)):
        return [n for x in v for n in _numbers(x)]
    if isinstance(v, bool) or v is None:
        return []
    if isinstance(v, (int, float)):
        return [abs(float(v))]
    return [float(n) for n in _NUMBER.findall(str(v))]


def check(level, text, f):
    """Notes for anything a reader should verify. Never changes the text."""
    allowed = set(_numbers(f)) | set(_numbers(REFERENCE)) | {round(b * 100) for b in BAND}
    unknown = sorted({n for n in _NUMBER.findall(text) if not any(abs(float(n) - a) < 1e-6 for a in allowed)}, key=float)
    notes = []
    if unknown:
        notes.append(f"Number{'s' if len(unknown) > 1 else ''} not in the fact sheet: {', '.join(unknown)}.")
    if level == "patient":
        if "%" in text or re.search(r"\bdice\b", text, re.I):
            notes.append("Patient text uses a percentage or a technical score.")
        if _OUTLOOK.search(text):
            notes.append("Mentions outlook. The care team should discuss this with the patient directly.")
    return notes


def fk_grade(text):
    """Flesch-Kincaid grade. Syllables: groups of vowels, a final silent 'e' dropped, at least 1; a number = 1 word."""
    sents = max(1, len(re.findall(r"[.!?](?:\s|$)", text)))
    words = re.findall(r"[A-Za-z]+(?:'[a-z]+)?|\d+(?:\.\d+)?", text)
    if not words:
        return 0.0

    def syl(w):
        if w[0].isdigit():
            return 1
        w = w.lower()
        n = len(re.findall(r"[aeiouy]+", w))
        if w.endswith("e") and not w.endswith(("le", "ee")) and n > 1:
            n -= 1
        return max(1, n)
    return round(0.39 * len(words) / sents + 11.8 * sum(map(syl, words)) / len(words) - 15.59, 1)


def build(case_dir, cut):
    """Facts + the four texts + check notes + timing, for the server and the download."""
    t = time.perf_counter()
    f = facts(case_dir, cut)
    out = explain(f)
    out["notes"] = {k: check(k, out[k], f) for k in LEVELS}
    out["ms"] = round(1000 * (time.perf_counter() - t), 1)
    return out


# ---------- self-check ----------
def _synthetic(flip=False):
    """A water body with two air 'lungs' and a sphere tumour in the upper part of the patient's right lung.
    Identity direction (LPS): a higher column is further to the patient's LEFT, so the right lung is at low columns.
    flip=True mirrors the x axis in the image header only: then the same pixels are on the patient's left."""
    Z, Y, X, sp = 120, 160, 160, (1.0, 1.0, 1.5)
    arr = np.full((Z, Y, X), -1000, np.int16)
    arr[:, 20:140, 15:145] = 30                          # body
    arr[10:110, 40:120, 25:75] = -850                    # lung at low columns
    arr[10:110, 40:120, 85:135] = -850                   # lung at high columns
    zz, yy, xx = np.meshgrid(np.arange(Z) * sp[2], np.arange(Y) * sp[1], np.arange(X) * sp[0], indexing="ij")
    c, r = (50.0, 80.0, 90 * 1.5), 12.0                  # (x, y, z) mm: low-column lung, z near its top (slices 10-110)
    dist = np.sqrt((xx - c[0]) ** 2 + (yy - c[1]) ** 2 + (zz - c[2]) ** 2)
    arr[dist <= r] = 40
    img = sitk.GetImageFromArray(arr)
    img.SetSpacing(sp)
    if flip:
        img.SetDirection((-1, 0, 0, 0, 1, 0, 0, 0, 1))
    prob = np.clip(0.5 - (dist - r) / 6, 0, 1).astype(np.float32)   # 0.5 exactly at the sphere's surface
    return img, arr, prob, (dist <= r).astype(np.uint8), r


def self_check():
    for flip, want in ((False, "right"), (True, "left")):
        img, arr, prob, truth, r = _synthetic(flip)
        bits, lo = engine.outlines(prob)
        i = engine.CUTS.index(0.5)
        row = engine.measure(bits, lo, i, prob, truth, img.GetSpacing())
        f = facts_from(img, arr, bits, lo, 0.5, {**row, "cut": 0.5}, "synthetic model", "Synthetic scan.")
        vol, diam = 4 / 3 * np.pi * r ** 3 / 1000, 2 * r
        assert f["side"] == want and f["part"] == "upper", (flip, f["side"], f["part"])
        assert abs(f["volume_cc"] - vol) / vol < 0.05, (f["volume_cc"], vol)
        assert abs(f["longest_mm"] - diam) / diam < 0.05, (f["longest_mm"], diam)
        d = describe(truth, [0, 0, 0], img, lungs(arr, img))        # the true sphere, whole scan
        assert d["side"] == want and d["part"] == "upper"
        out = explain(f)
        for k in LEVELS:
            assert out[k].strip(), k
            assert not check(k, out[k], f), (k, check(k, out[k], f), out[k])
        assert "%" not in out["patient"]
        none = explain({**f, "found": False})
        assert all(none[k] and not check(k, none[k], f) for k in LEVELS)
        print(f"{'mirrored' if flip else 'normal'} header: {f['side']} lung, {f['part']} part, {f['volume_cc']} cc "
              f"(true {vol:.1f}), {f['longest_mm']} mm across (true {diam:.0f}); checks clean")
    bad = explain(f)["ai"].replace(str(REFERENCE["dice"]), "0.912")
    assert check("ai", bad, f), "check() must flag a number that is not in the fact sheet"
    assert check("patient", "Your survival is 80%.", f), "check() must flag outlook words and % in patient text"
    print("self-check passed")


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--self-check", action="store_true")
    ap.add_argument("--case", help="a finished case folder: print its four texts")
    ap.add_argument("--cut", type=float, default=engine.DEFAULT_CUT)
    a = ap.parse_args()
    if a.self_check:
        self_check()
    if a.case:
        out = build(a.case, a.cut)
        for k in LEVELS:
            print(f"\n[{k}] (grade {fk_grade(out[k])})\n{out[k]}" + "".join(f"\n  ! {n}" for n in out["notes"][k]))
        d = doctor_facts(a.case)
        if d:
            print(f"\ndoctor's outline: {d['side']} lung, {d['part']} part, {d['volume_cc']} cc, {d['longest_mm']} mm across")
        print(f"\nbuilt in {out['ms']} ms")
