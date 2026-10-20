"""
Reads DICOM and DICOM RT files and turns them into what the chart shows:
outlines as masks on the dose grid, dose-volume curves, dose metrics, plan
constraint checks (computed in code, never by the model), rendered CT slices
with outlines and dose, and a de-identified header summary for any DICOM file.

Works on any standard files, not only the synthetic ones made for the demo.
"""
import io
from functools import lru_cache
from pathlib import Path

import numpy as np
import pydicom
from PIL import Image, ImageDraw

# Example limits for the demo. A clinic's own protocol replaces these.
PROTOCOLS = {
    "lung": [
        ("PTV", "D95", ">=", 0.95, "rx", "Target coverage, D95"),
        ("Lungs-GTV", "V20", "<=", 35, "%", "Lungs minus GTV, V20 Gy"),
        ("Lungs-GTV", "mean", "<=", 20, "Gy", "Lungs minus GTV, mean dose"),
        ("Heart", "mean", "<=", 20, "Gy", "Heart, mean dose"),
        ("Esophagus", "mean", "<=", 34, "Gy", "Oesophagus, mean dose"),
        ("SpinalCord", "max", "<=", 50, "Gy", "Spinal cord, maximum dose"),
    ],
    "breast": [
        ("PTV_Breast_L", "D95", ">=", 0.95, "rx", "Target coverage, D95"),
        ("Heart", "mean", "<=", 4, "Gy", "Heart, mean dose"),
        ("Lung_L", "V20", "<=", 20, "%", "Left lung, V20 Gy"),
        ("Breast_R", "mean", "<=", 3, "Gy", "Right breast, mean dose"),
        ("SpinalCord", "max", "<=", 45, "Gy", "Spinal cord, maximum dose"),
    ],
}

# Header fields that identify a person (DICOM basic de-identification profile, abridged).
IDENTIFYING = [
    "PatientName", "PatientID", "PatientBirthDate", "PatientBirthTime", "OtherPatientIDs", "OtherPatientNames",
    "OtherPatientIDsSequence", "PatientAddress", "PatientTelephoneNumbers", "PatientMotherBirthName",
    "MedicalRecordLocator", "AccessionNumber", "InstitutionName", "InstitutionAddress", "ReferringPhysicianName",
    "PerformingPhysicianName", "OperatorsName", "PhysiciansOfRecord", "NameOfPhysiciansReadingStudy",
    "ReviewerName", "StudyID", "DeviceSerialNumber", "StationName",
]
WINDOWS = {"lung": (-600, 1500), "soft": (40, 400), "bone": (400, 1800)}

# Real files name structures many ways ("Spinal-Cord", "Lung-Left", "GTV-1").
# Map them to one vocabulary for the checks, and give each a clear display colour.
CANONICAL = [
    ("GTV", lambda n: n.lower().startswith("gtv")),
    ("PTV", lambda n: n.lower().startswith("ptv")),
    ("Lungs", lambda n: n.lower() in ("lungs", "lung", "lung_total", "lungs_total")),
    ("Lung_L", lambda n: n.lower().replace("-", "_") in ("lung_l", "lung_left", "left_lung")),
    ("Lung_R", lambda n: n.lower().replace("-", "_") in ("lung_r", "lung_right", "right_lung")),
    ("Heart", lambda n: n.lower() == "heart"),
    ("Esophagus", lambda n: n.lower() in ("esophagus", "oesophagus")),
    ("SpinalCord", lambda n: n.lower().replace("-", "").replace("_", "") in ("spinalcord", "cord")),
]
PALETTE = {"GTV": (220, 38, 38), "PTV": (249, 115, 22), "Lungs": (56, 189, 248), "Lung_L": (56, 189, 248),
           "Lung_R": (125, 211, 252), "Heart": (236, 72, 153), "Esophagus": (132, 204, 22), "SpinalCord": (234, 179, 8)}


def canonical(name: str) -> str | None:
    return next((c for c, test in CANONICAL if test(name)), None)


def distance_mm(mask: np.ndarray, spacing_zyx, limit: float = 120.0) -> np.ndarray:
    """Distance (mm) from every voxel to the nearest voxel of `mask`; `limit` beyond a
    box around it. Brute force over the mask's surface voxels, fine for tumour-sized masks."""
    out = np.full(mask.shape, limit, dtype=float)
    if not mask.any():
        return out
    sz, sy, sx = spacing_zyx
    inner = mask.copy()
    for axis in range(3):
        inner &= np.roll(mask, 1, axis) & np.roll(mask, -1, axis)
    surface = np.argwhere(mask & ~inner) * np.array([sz, sy, sx])
    lo = np.maximum(np.argwhere(mask).min(0) - np.ceil(limit / np.array([sz, sy, sx])).astype(int), 0)
    hi = np.minimum(np.argwhere(mask).max(0) + np.ceil(limit / np.array([sz, sy, sx])).astype(int) + 1, mask.shape)
    zz, yy, xx = np.meshgrid(*[np.arange(a, b) for a, b in zip(lo, hi)], indexing="ij")
    pts = np.stack([zz.ravel() * sz, yy.ravel() * sy, xx.ravel() * sx], axis=1)
    best = np.full(len(pts), np.inf)
    for i in range(0, len(pts), 4096):                # chunked both ways to keep memory small
        p = pts[i:i + 4096]
        for j in range(0, len(surface), 512):
            s = surface[j:j + 512]
            d2 = (p[:, None, 0] - s[None, :, 0]) ** 2 + (p[:, None, 1] - s[None, :, 1]) ** 2 + (p[:, None, 2] - s[None, :, 2]) ** 2
            best[i:i + 4096] = np.minimum(best[i:i + 4096], d2.min(1))
    best = np.sqrt(best)
    box = np.minimum(best, limit).reshape(zz.shape)
    box[mask[lo[0]:hi[0], lo[1]:hi[1], lo[2]:hi[2]]] = 0
    out[lo[0]:hi[0], lo[1]:hi[1], lo[2]:hi[2]] = box
    return out


def _text(value):
    return str(value) if value is not None else ""


def deidentify(ds) -> dict:
    """Clinical summary of a DICOM header plus the identifying fields that were hidden.
    Dates are reduced to the year."""
    hidden = [k for k in IDENTIFYING if k in ds and _text(ds.get(k)).strip()]
    year = lambda k: _text(ds.get(k))[:4]
    modality = _text(ds.get("Modality"))
    info = {
        "modality": modality,
        "body_part": _text(ds.get("BodyPartExamined")),
        "study": _text(ds.get("StudyDescription")),
        "series": _text(ds.get("SeriesDescription")),
        "year": year("StudyDate") or year("RTPlanDate") or year("StructureSetDate"),
        "manufacturer": _text(ds.get("Manufacturer")),
    }
    if "Rows" in ds:
        info["size"] = f"{ds.Rows} x {ds.Columns}"
    if "PixelSpacing" in ds:
        info["pixel_spacing_mm"] = [round(float(v), 3) for v in ds.PixelSpacing]
    if "SliceThickness" in ds:
        info["slice_thickness_mm"] = float(ds.SliceThickness)
    if modality == "RTPLAN":
        info.update(plan_summary(ds))
    elif modality == "RTSTRUCT":
        info["structures"] = [_text(r.ROIName) for r in ds.get("StructureSetROISequence", [])]
    elif modality == "RTDOSE":
        info["dose_units"] = _text(ds.get("DoseUnits"))
        info["frames"] = int(ds.get("NumberOfFrames", 1))
    return {"info": {k: v for k, v in info.items() if v not in ("", None, [])}, "hidden": hidden}


def plan_summary(plan) -> dict:
    rx = next((float(r.TargetPrescriptionDose) for r in plan.get("DoseReferenceSequence", []) if "TargetPrescriptionDose" in r), None)
    fg = plan.FractionGroupSequence[0] if plan.get("FractionGroupSequence") else None
    fractions = int(fg.NumberOfFractionsPlanned) if fg else None
    beams = []
    for b in plan.get("BeamSequence", []):
        cps = b.get("ControlPointSequence", [])
        start = cps[0] if cps else None
        beams.append({
            "name": _text(b.BeamName), "type": _text(b.get("BeamType")), "radiation": _text(b.get("RadiationType")),
            "energy_mv": float(start.NominalBeamEnergy) if start is not None and "NominalBeamEnergy" in start else None,
            "gantry": [float(c.GantryAngle) for c in cps if "GantryAngle" in c],
            "machine": _text(b.get("TreatmentMachineName")),
        })
    return {
        "label": _text(plan.get("RTPlanLabel")), "name": _text(plan.get("RTPlanName")),
        "date": _text(plan.get("RTPlanDate")), "approval": _text(plan.get("ApprovalStatus")),
        "intent": _text(plan.get("PlanIntent")), "prescription": _text(plan.get("PrescriptionDescription")),
        "rx_gy": rx, "fractions": fractions, "dose_per_fraction_gy": round(rx / fractions, 2) if rx and fractions else None,
        "beams": beams,
    }


@lru_cache(maxsize=8)
def _read(path: str, mtime: float):
    return pydicom.dcmread(path)


def read(path: str):
    return _read(path, Path(path).stat().st_mtime)


def rois(struct) -> dict:
    """ROI name -> {color, type, contours: {z: [polygons as N x 2 arrays (mm)]}}."""
    kinds = {int(o.ReferencedROINumber): _text(o.get("RTROIInterpretedType")) for o in struct.get("RTROIObservationsSequence", [])}
    names = {int(r.ROINumber): _text(r.ROIName) for r in struct.StructureSetROISequence}
    out = {}
    for rc in struct.ROIContourSequence:
        n = int(rc.ReferencedROINumber)
        contours = {}
        for c in rc.get("ContourSequence", []):
            pts = np.array(c.ContourData, dtype=float).reshape(-1, 3)
            contours.setdefault(round(float(pts[0, 2]), 2), []).append(pts[:, :2])
        canon = canonical(names[n])
        color = PALETTE.get(canon) or [int(v) for v in rc.get("ROIDisplayColor", [200, 200, 200])]
        out[names[n]] = {"color": list(color), "type": kinds.get(n, "") or ("GTV" if canon == "GTV" else ""),
                         "contours": contours, "canonical": canon}
    return out


def dose_array(dose):
    grid = dose.pixel_array.astype(float) * float(dose.DoseGridScaling)
    if grid.ndim == 2:
        grid = grid[None]
    origin = [float(v) for v in dose.ImagePositionPatient]
    spacing = [float(v) for v in dose.PixelSpacing]          # row spacing (y), column spacing (x)
    zs = [origin[2] + float(o) for o in dose.GridFrameOffsetVector]
    return grid, origin, spacing, zs


def rasterize(polys, origin, spacing, shape) -> np.ndarray:
    img = Image.new("L", (shape[1], shape[0]), 0)
    draw = ImageDraw.Draw(img)
    for p in polys:
        cols = (p[:, 0] - origin[0]) / spacing[1]
        rows = (p[:, 1] - origin[1]) / spacing[0]
        draw.polygon(list(zip(cols.tolist(), rows.tolist())), fill=1)
    return np.asarray(img, dtype=bool)


def masks(struct, dose) -> dict:
    grid, origin, spacing, zs = dose_array(dose)
    out = {}
    for name, roi in rois(struct).items():
        m = np.zeros(grid.shape, dtype=bool)
        for k, z in enumerate(zs):
            polys = [p for cz, ps in roi["contours"].items() if abs(cz - z) < 0.5 * (zs[1] - zs[0] if len(zs) > 1 else 1) for p in ps]
            if polys:
                m[k] = rasterize(polys, origin, spacing, grid.shape[1:])
        out[name] = m
    return add_derived(out, rois(struct), spacing_zyx=((zs[1] - zs[0]) if len(zs) > 1 else 3.0, spacing[0], spacing[1]))


PTV_MARGIN_MM = 7.0


def add_derived(masks_by_name: dict, roi_info: dict, spacing_zyx) -> dict:
    """Canonical names for the checks (GTV, PTV, Lungs, ...), built from whatever the file calls them.
    A PTV missing from the file is derived as the GTV plus a margin, and marked as derived."""
    out = dict(masks_by_name)
    by_canon = {}
    for name, info in roi_info.items():
        if info.get("canonical") and name in out:
            by_canon.setdefault(info["canonical"], []).append(out[name])
    for canon, ms in by_canon.items():
        if canon not in out:
            out[canon] = np.logical_or.reduce(ms)
    if "Lungs" not in out and ("Lung_L" in out or "Lung_R" in out):
        out["Lungs"] = out.get("Lung_L", False) | out.get("Lung_R", False)
    if "PTV" not in out and "GTV" in out:
        out["PTV (GTV + 7 mm, derived)"] = distance_mm(out["GTV"], spacing_zyx, limit=PTV_MARGIN_MM + 1) <= PTV_MARGIN_MM
        out["PTV"] = out["PTV (GTV + 7 mm, derived)"]
    if "Lungs" in out and "GTV" in out:
        out["Lungs-GTV"] = out["Lungs"] & ~out["GTV"]
    return out


def metrics(dose_values: np.ndarray, voxel_cc: float) -> dict:
    if dose_values.size == 0:
        return {}
    return {
        "volume_cc": round(dose_values.size * voxel_cc, 1),
        "mean": round(float(dose_values.mean()), 2),
        "max": round(float(dose_values.max()), 2),
        "D95": round(float(np.percentile(dose_values, 5)), 2),
        "V20": round(float((dose_values >= 20).mean() * 100), 1),
        "V5": round(float((dose_values >= 5).mean() * 100), 1),
    }


def dvh_curve(dose_values: np.ndarray, top: float, step: float = 0.5) -> list[list[float]]:
    """Cumulative dose-volume histogram: [dose Gy, % of volume receiving at least that dose]."""
    edges = np.arange(0, top + step, step)
    if dose_values.size == 0:
        return []
    sorted_vals = np.sort(dose_values)
    at_least = 1 - np.searchsorted(sorted_vals, edges, side="left") / sorted_vals.size
    return [[round(float(d), 1), round(float(v) * 100, 2)] for d, v in zip(edges, at_least)]


def check_constraints(site: str, stats: dict, rx: float) -> list[dict]:
    out = []
    for roi, metric, op, limit, unit, label in PROTOCOLS.get(site, []):
        if roi not in stats or metric not in stats[roi]:
            continue
        value = stats[roi][metric]
        limit_value = limit * rx if unit == "rx" else limit
        ok = value >= limit_value if op == ">=" else value <= limit_value
        out.append({
            "label": label, "structure": roi, "metric": metric,
            "limit": f"{'≥' if op == '>=' else '≤'} {limit_value:g} {'Gy' if unit in ('rx', 'Gy') else '%'}",
            "value": value, "unit": "%" if unit == "%" else "Gy", "ok": bool(ok), "op": op, "limit_value": round(limit_value, 2),
        })
    return out


def analyse(files: dict, delivery: list[dict]) -> dict:
    """Everything the Radiation section shows, from one patient's plan, structures and dose."""
    plan, struct, dose = read(files["RTPLAN"]), read(files["RTSTRUCT"]), read(files["RTDOSE"])
    summary = plan_summary(plan)
    site = _text(plan.get("RTPlanDescription")) or "lung"
    grid, _, spacing, zs = dose_array(dose)
    voxel_cc = spacing[0] * spacing[1] * (zs[1] - zs[0] if len(zs) > 1 else 1) / 1000
    roi_info = rois(struct)
    stats, curves = {}, {}
    top = float(np.ceil(grid.max() / 5) * 5)
    derived_ptv = None
    for name, m in masks(struct, dose).items():
        if name.upper() in ("BODY", "EXTERNAL") or not np.any(m):
            continue
        vals = grid[m]
        stats[name] = metrics(vals, voxel_cc)
        if name in roi_info or name.endswith("derived)"):
            curves[name] = dvh_curve(vals, top)
        if name.endswith("derived)"):
            derived_ptv = name
    rx = summary["rx_gy"] or float(grid.max())
    delivered = [d for d in delivery if d.get("status") == "Delivered"]
    target = next((n for n, r in roi_info.items() if r["type"] == "PTV"), None) or next((n for n, r in roi_info.items() if r.get("canonical") == "GTV"), None)
    areas = {}
    if target:     # the plane where the target is largest: the slice the viewer opens on
        for z, polys in roi_info[target]["contours"].items():
            areas[z] = sum(abs(np.dot(p[:, 0], np.roll(p[:, 1], 1)) - np.dot(p[:, 1], np.roll(p[:, 0], 1))) / 2 for p in polys)
    structures = [{"name": n, "color": r["color"], "type": r["type"], **({"volume_cc": stats[n]["volume_cc"]} if n in stats else {})}
                  for n, r in roi_info.items() if n.upper() not in ("BODY", "EXTERNAL")]
    if derived_ptv:
        structures.insert(1, {"name": derived_ptv, "color": list(PALETTE["PTV"]), "type": "PTV", "derived": True,
                              "volume_cc": stats[derived_ptv]["volume_cc"]})
    illustrative = "illustrative" in _text(plan.get("RTPlanName")).lower()
    return {
        "site": site,
        "illustrative": illustrative,
        "dose_note": "Illustrative dose computed for this demo on the real anatomy; the public dataset includes no clinical plan." if illustrative else None,
        "target_z": max(areas, key=areas.get) if areas else None,
        "plan": summary,
        "structures": structures,
        "dvh": curves,
        "stats": stats,
        "constraints": check_constraints(site, stats, rx),
        "delivery": {"planned": summary["fractions"], "delivered": len(delivered), "fractions": delivery,
                     "breaks": treatment_breaks([d["date"] for d in delivered]),
                     "dose_delivered_gy": round(sum(float(d.get("dose_gy", 0)) for d in delivered), 1),
                     "first": delivery[0]["date"] if delivery else None, "last": delivered[-1]["date"] if delivered else None},
    }


def treatment_breaks(dates: list[str]) -> list[dict]:
    """Gaps of two or more working days between consecutive treatment days."""
    import numpy as _np
    out = []
    for a, b in zip(dates, dates[1:]):
        missed = int(_np.busday_count(a, b)) - 1
        if missed >= 2:
            out.append({"after": a, "resumed": b, "working_days_missed": missed})
    return out


def _colormap(rel: np.ndarray) -> np.ndarray:
    """Relative dose 0..1.1 -> RGB, blue through red."""
    stops = np.array([0.2, 0.5, 0.8, 0.95, 1.05])
    colors = np.array([[37, 99, 235], [6, 182, 212], [34, 197, 94], [250, 204, 21], [239, 68, 68]], dtype=float)
    out = np.zeros(rel.shape + (3,))
    for ch in range(3):
        out[..., ch] = np.interp(rel, stops, colors[:, ch])
    return out


def render_slice(ct_files: list[str], files: dict | None, index: int, window: str = "soft",
                 show_contours: bool = True, show_dose: bool = True, size: int = 512) -> bytes:
    """One CT slice as a PNG, with the outlines and the dose colour wash on top."""
    ct = read(ct_files[index])
    hu = ct.pixel_array.astype(float) * float(ct.get("RescaleSlope", 1)) + float(ct.get("RescaleIntercept", 0))
    center, width = WINDOWS.get(window, WINDOWS["soft"])
    gray = np.clip((hu - (center - width / 2)) / width, 0, 1) * 255
    rgb = np.stack([gray] * 3, axis=-1)
    z = float(ct.ImagePositionPatient[2])
    ct_origin = [float(v) for v in ct.ImagePositionPatient]
    ct_spacing = [float(v) for v in ct.PixelSpacing]
    if files and show_dose:
        plan, dose = read(files["RTPLAN"]), read(files["RTDOSE"])
        grid, d_origin, d_spacing, zs = dose_array(dose)
        k = int(np.argmin([abs(v - z) for v in zs]))
        rx = plan_summary(plan)["rx_gy"] or float(grid.max())
        # sample the dose grid at every CT pixel centre (both share the patient coordinate system)
        cols = (ct_origin[0] + np.arange(hu.shape[1]) * ct_spacing[1] - d_origin[0]) / d_spacing[1]
        rows = (ct_origin[1] + np.arange(hu.shape[0]) * ct_spacing[0] - d_origin[1]) / d_spacing[0]
        # bilinear between the four nearest dose points, so the wash stays smooth when zoomed in
        c = np.clip(cols, 0, grid.shape[2] - 1)
        r = np.clip(rows, 0, grid.shape[1] - 1)
        c0, r0 = np.floor(c).astype(int), np.floor(r).astype(int)
        c1, r1 = np.minimum(c0 + 1, grid.shape[2] - 1), np.minimum(r0 + 1, grid.shape[1] - 1)
        fc, fr = (c - c0)[None, :], (r - r0)[:, None]
        g = grid[k]
        top = g[np.ix_(r0, c0)] * (1 - fc) + g[np.ix_(r0, c1)] * fc
        bottom = g[np.ix_(r1, c0)] * (1 - fc) + g[np.ix_(r1, c1)] * fc
        inside = ((cols >= -0.5) & (cols <= grid.shape[2] - 0.5))[None, :] & ((rows >= -0.5) & (rows <= grid.shape[1] - 0.5))[:, None]
        rel = np.where(inside, (top * (1 - fr) + bottom * fr) / rx, 0.0)
        alpha = np.clip((rel - 0.2) / 0.8, 0, 1)[..., None] * 0.5
        alpha[rel < 0.2] = 0
        rgb = rgb * (1 - alpha) + _colormap(rel) * alpha
    img = Image.fromarray(rgb.astype(np.uint8), "RGB").resize((size, size), Image.BILINEAR)
    if files and show_contours:
        draw = ImageDraw.Draw(img)
        f = size / hu.shape[1]
        for name, roi in rois(read(files["RTSTRUCT"])).items():
            if name.upper() in ("BODY", "EXTERNAL"):
                continue
            for cz, polys in roi["contours"].items():
                if abs(cz - z) > 0.5:
                    continue
                for p in polys:
                    cols = (p[:, 0] - ct_origin[0]) / ct_spacing[1] * f
                    rows = (p[:, 1] - ct_origin[1]) / ct_spacing[0] * f
                    pts = list(zip(cols.tolist(), rows.tolist()))
                    draw.line(pts + pts[:1], fill=tuple(roi["color"]), width=2)
    buf = io.BytesIO()
    img.save(buf, "PNG", optimize=True)
    return buf.getvalue()


def render_any(ds, size: int = 512) -> bytes | None:
    """Picture for an uploaded DICOM image (first frame), windowed for viewing. None if it has no pixels."""
    if "PixelData" not in ds:
        return None
    arr = ds.pixel_array.astype(float)
    if arr.ndim == 3 and arr.shape[-1] not in (3, 4):
        arr = arr[0]
    if arr.ndim == 2:
        arr = arr * float(ds.get("RescaleSlope", 1)) + float(ds.get("RescaleIntercept", 0))
        center, width = ds.get("WindowCenter"), ds.get("WindowWidth")
        if center is not None and width is not None:
            center = float(center[0] if hasattr(center, "__len__") and not isinstance(center, str) else center)
            width = float(width[0] if hasattr(width, "__len__") and not isinstance(width, str) else width)
            lo, hi = center - width / 2, center + width / 2
        else:
            lo, hi = np.percentile(arr, [1, 99])
        gray = np.clip((arr - lo) / max(hi - lo, 1e-6), 0, 1) * 255
        if _text(ds.get("PhotometricInterpretation")) == "MONOCHROME1":
            gray = 255 - gray
        img = Image.fromarray(gray.astype(np.uint8), "L")
    else:
        img = Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8))
    img.thumbnail((size, size))
    buf = io.BytesIO()
    img.convert("RGB").save(buf, "PNG", optimize=True)
    return buf.getvalue()


def for_prompt(a: dict) -> str:
    """The plan review as plain lines for DocAssist. Every number here was computed in code."""
    p, d = a["plan"], a["delivery"]
    beams = ", ".join(f"{b['name']} ({b['type'].lower()}, {b['energy_mv']:g} MV)" for b in p["beams"] if b.get("energy_mv"))
    lines = [
        f"Plan: {p['label']}, {p['name']}. Status: {p['approval'].lower()}. Intent: {p['intent'].lower()}.",
        f"Prescription: {p['prescription']} ({p['dose_per_fraction_gy']} Gy per fraction). Beams: {beams}.",
        f"Delivery: {d['delivered']} of {d['planned']} fractions delivered, {d['dose_delivered_gy']} Gy, from {d['first']} to {d['last']}.",
        "Constraint checks (example limits; the clinic's own protocol applies):",
    ]
    lines += [f"- {c['label']}: {c['value']} {c['unit']} (limit {c['limit']}) {'met' if c['ok'] else 'NOT MET, needs review'}" for c in a["constraints"]]
    shown = {s["name"] for s in a["structures"]}
    lines.append("Structure doses: " + "; ".join(f"{n} mean {s['mean']} Gy, max {s['max']} Gy" for n, s in a["stats"].items() if n in shown))
    if a.get("dose_note"):
        lines.append("Note: " + a["dose_note"])
    return "\n".join(lines)
