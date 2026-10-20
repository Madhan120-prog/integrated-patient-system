"""
Synthetic DICOM for the radiation oncology demo: a planning CT series (a
mathematical phantom, not a real scan), an RT Structure Set with the outlines,
an RT Plan and an RT Dose grid, all in standard DICOM RT form so the same code
would read files exported by a real planning system.

Everything here is made up: names, IDs, dates and anatomy. Nothing is derived
from a real patient. Geometry is in the DICOM patient coordinate system
(millimetres; +x patient left, +y posterior, +z superior).
"""
import hashlib
from datetime import date

import numpy as np
from pydicom.dataset import Dataset, FileMetaDataset
from pydicom.sequence import Sequence
from pydicom.tag import Tag
from pydicom.uid import (CTImageStorage, ExplicitVRLittleEndian, RTDoseStorage, RTPlanStorage,
                         RTStructureSetStorage, generate_uid)

CT_SIZE, CT_SPACING = 256, 1.5          # 384 mm field of view
DOSE_SIZE, DOSE_SPACING = 128, 3.0
SLICES, SLICE_STEP, Z0 = 24, 5.0, -60.0
CT_ORIGIN = -(CT_SIZE - 1) * CT_SPACING / 2
DOSE_ORIGIN = -(DOSE_SIZE - 1) * DOSE_SPACING / 2
Z_POSITIONS = [Z0 + k * SLICE_STEP for k in range(SLICES)]
DOSE_SCALING = 1e-5                     # Gy per stored unit

# Shapes: ("ellipse", cx, cy, a, b, zmin, zmax) is an elliptic cylinder;
# ("ellipsoid", cx, cy, cz, a, b, c) and ("sphere", cx, cy, cz, r) are solids.
SITES = {
    "lung": {
        "label": "LUNG_R_60", "name": "Right lung and mediastinum, concurrent chemoradiation",
        "body": [("ellipse", 0, 0, 175, 125, -999, 999)],
        "rois": [
            ("GTV", "GTV", (255, 0, 0), [("sphere", -70, -30, 25, 18), ("sphere", -12, 35, 10, 12)]),
            ("PTV", "PTV", (255, 140, 0), [("sphere", -70, -30, 25, 25), ("sphere", -12, 35, 10, 19)]),
            ("Lungs", "ORGAN", (56, 189, 248), [("ellipse", -88, -5, 55, 82, -999, 999), ("ellipse", 88, -5, 55, 82, -999, 999)]),
            ("Heart", "ORGAN", (244, 114, 182), [("ellipse", 0, -35, 32, 36, -999, 0)]),
            ("Esophagus", "ORGAN", (163, 230, 53), [("ellipse", 10, 45, 8, 8, -999, 999)]),
            ("SpinalCord", "ORGAN", (250, 204, 21), [("ellipse", 0, 85, 7, 7, -999, 999)]),
        ],
        "hu": [("Lungs", -820), ("Heart", 45), ("Esophagus", 20), ("GTV", 35)],
        "beams": [("ARC1", 181, 179, "CW"), ("ARC2", 179, 181, "CC")], "technique": "VMAT", "energy": 6,
    },
    "breast": {
        "label": "BREAST_L_50", "name": "Left whole breast, tangential fields",
        "body": [("ellipse", 0, 0, 175, 115, -999, 999), ("ellipsoid", 85, -108, 0, 60, 42, 65),
                 ("ellipsoid", -85, -108, 0, 60, 42, 65)],
        "rois": [
            ("PTV_Breast_L", "PTV", (255, 140, 0), [("ellipsoid", 85, -110, 0, 54, 37, 59)]),
            ("Lung_L", "ORGAN", (56, 189, 248), [("ellipse", 85, 5, 55, 75, -999, 999)]),
            ("Lung_R", "ORGAN", (125, 211, 252), [("ellipse", -85, 5, 55, 75, -999, 999)]),
            ("Heart", "ORGAN", (244, 114, 182), [("ellipse", 0, -30, 28, 34, -999, 15)]),
            ("Breast_R", "ORGAN", (192, 132, 252), [("ellipsoid", -85, -110, 0, 54, 37, 59)]),
            ("SpinalCord", "ORGAN", (250, 204, 21), [("ellipse", 0, 80, 7, 7, -999, 999)]),
        ],
        "hu": [("Lung_L", -820), ("Lung_R", -820), ("Heart", 45), ("PTV_Breast_L", -40), ("Breast_R", -40)],
        "beams": [("MED_TAN", 300, 300, "NONE"), ("LAT_TAN", 120, 120, "NONE")], "technique": "3D conformal tangents", "energy": 6,
    },
}


def _uid(*parts) -> str:
    return generate_uid(entropy_srcs=[str(p) for p in parts])


def _grid(size, spacing, origin):
    axis = origin + np.arange(size) * spacing
    return np.meshgrid(axis, axis)          # X varies along columns, Y along rows


def shape_mask(shape, X, Y, z):
    kind = shape[0]
    if kind == "ellipse":
        _, cx, cy, a, b, zmin, zmax = shape
        if not zmin <= z <= zmax:
            return np.zeros_like(X, dtype=bool)
        return ((X - cx) / a) ** 2 + ((Y - cy) / b) ** 2 <= 1
    if kind == "sphere":
        _, cx, cy, cz, r = shape
        return (X - cx) ** 2 + (Y - cy) ** 2 + (z - cz) ** 2 <= r ** 2
    _, cx, cy, cz, a, b, c = shape
    return ((X - cx) / a) ** 2 + ((Y - cy) / b) ** 2 + ((z - cz) / c) ** 2 <= 1


def shape_outline(shape, z, points=60):
    """Closed polygon (N x 2, mm) where the shape crosses plane z, or None."""
    kind = shape[0]
    if kind == "ellipse":
        _, cx, cy, a, b, zmin, zmax = shape
        if not zmin <= z <= zmax:
            return None
    elif kind == "sphere":
        _, cx, cy, cz, r = shape
        if abs(z - cz) >= r:
            return None
        a = b = float(np.sqrt(r ** 2 - (z - cz) ** 2))
    else:
        _, cx, cy, cz, a0, b0, c = shape
        f = 1 - ((z - cz) / c) ** 2
        if f <= 0:
            return None
        a, b = a0 * np.sqrt(f), b0 * np.sqrt(f)
    if a < 1.5 or b < 1.5:
        return None
    t = np.linspace(0, 2 * np.pi, points, endpoint=False)
    return np.stack([cx + a * np.cos(t), cy + b * np.sin(t)], axis=1)


def _signed_distance(shapes, X, Y, z):
    """Approximate distance (mm) to the nearest shape surface; negative inside."""
    best = np.full(X.shape, np.inf)
    for s in shapes:
        if s[0] == "sphere":
            _, cx, cy, cz, r = s
            d = np.sqrt((X - cx) ** 2 + (Y - cy) ** 2 + (z - cz) ** 2) - r
        else:
            _, cx, cy, cz, a, b, c = s
            q = np.sqrt(((X - cx) / a) ** 2 + ((Y - cy) / b) ** 2 + ((z - cz) / c) ** 2)
            d = (q - 1) * min(a, b)
        best = np.minimum(best, d)
    return best


def _body(site, X, Y, z):
    m = np.zeros_like(X, dtype=bool)
    for s in SITES[site]["body"]:
        m |= shape_mask(s, X, Y, z)
    return m


def dose_grid(site, rx_gy, seed):
    """Plan dose (Gy) on the dose grid, shape (slices, rows, cols)."""
    rng = np.random.default_rng(seed)
    X, Y = _grid(DOSE_SIZE, DOSE_SPACING, DOSE_ORIGIN)
    ptv = next(r for r in SITES[site]["rois"] if r[1] == "PTV")[3]
    out = np.zeros((SLICES, DOSE_SIZE, DOSE_SIZE))
    for k, z in enumerate(Z_POSITIONS):
        # Full dose covers the target plus a few millimetres, as in a real plan; then it falls off.
        if site == "lung":
            d = _signed_distance(ptv, X, Y, z) - 4
            iso = np.sqrt((X + 45) ** 2 + (Y + 5) ** 2 + (z - 18) ** 2)
            outside = 0.62 * np.exp(-d / 12) + 0.38 * np.exp(-d / 50) + 0.08 * np.exp(-iso / 110)
        else:
            d = _signed_distance(ptv, X, Y, z) - 3
            outside = 0.9 * np.exp(-d / 12) + 0.05 * np.exp(-d / 60)
        rel = np.where(d <= 0, 1.0 + 0.012 * rng.standard_normal(X.shape), np.minimum(outside, 1.0))
        out[k] = rx_gy * rel * _body(site, X, Y, z)
    return np.clip(out, 0, None)


def _file(ds, sop_class, sop_uid):
    meta = FileMetaDataset()
    meta.MediaStorageSOPClassUID = sop_class
    meta.MediaStorageSOPInstanceUID = sop_uid
    meta.TransferSyntaxUID = ExplicitVRLittleEndian
    ds.file_meta = meta
    ds.SOPClassUID, ds.SOPInstanceUID = sop_class, sop_uid
    return ds


def _patient(ds, case, local_id):
    # Made-up identity, present on purpose so the de-identification step has something to hide.
    family, given = case["name"].split(" ", 1)[1].upper(), case["name"].split(" ", 1)[0].upper()
    ds.PatientName = f"{family}^{given}"
    ds.PatientID = local_id
    ds.PatientBirthDate = f"{case['birth_year']}0101"
    ds.PatientSex = case["sex"]
    ds.InstitutionName = "Demo Cancer Center (synthetic)"
    ds.ReferringPhysicianName = case["physician"].replace("Dr. ", "").upper()
    ds.AccessionNumber = hashlib.sha1(local_id.encode()).hexdigest()[:10].upper()


def build_case(case: dict) -> dict:
    """All DICOM objects for one patient's radiation course."""
    site, spec = case["site"], SITES[case["site"]]
    pid = case["patient_id"]
    study_uid, series_uid, frame_uid = _uid(pid, "study"), _uid(pid, "ct"), _uid(pid, "for")
    ct_date = case["ct_date"].replace("-", "")
    plan_date = case["plan_date"].replace("-", "")
    rng = np.random.default_rng(int(hashlib.sha1(pid.encode()).hexdigest()[:8], 16))
    X, Y = _grid(CT_SIZE, CT_SPACING, CT_ORIGIN)

    ct = []
    for k, z in enumerate(Z_POSITIONS):
        body = _body(site, X, Y, z)
        hu = np.full(X.shape, -1000.0)
        hu[body] = 30
        inner = np.zeros_like(body)
        for s in spec["body"]:                                    # the outline shrunk by 12 mm
            shrunk = (s[0], *s[1:3], s[3] - 12, s[4] - 12, *s[5:]) if s[0] == "ellipse" else (s[0], *s[1:4], s[4] - 12, s[5] - 12, s[6] - 12)
            inner |= shape_mask(shrunk, X, Y, z)
        hu[body & ~inner] = -90                                   # subcutaneous fat
        cord_x = 0
        cord_y = 85 if site == "lung" else 80
        hu[shape_mask(("ellipse", cord_x, cord_y, 18, 18, -999, 999), X, Y, z)] = 650   # vertebra
        for roi_name, value in spec["hu"]:
            shapes = next(r[3] for r in spec["rois"] if r[0] == roi_name)
            for s in shapes:
                hu[shape_mask(s, X, Y, z)] = value
        hu[shape_mask(("ellipse", cord_x, cord_y, 7, 7, -999, 999), X, Y, z)] = 35          # cord inside canal
        hu = hu + 10 * rng.standard_normal(hu.shape) * body
        ds = Dataset()
        _file(ds, CTImageStorage, _uid(pid, "ct", k))
        _patient(ds, case, case["pacs_local_id"])
        ds.Modality, ds.BodyPartExamined = "CT", "CHEST"
        ds.StudyInstanceUID, ds.SeriesInstanceUID, ds.FrameOfReferenceUID = study_uid, series_uid, frame_uid
        ds.StudyDate = ds.SeriesDate = ds.ContentDate = ct_date
        ds.StudyDescription = "CT simulation for radiotherapy planning"
        ds.SeriesDescription = "Planning CT, 5 mm (synthetic phantom)"
        ds.Manufacturer, ds.ManufacturerModelName = "Synthetic phantom", "Demo generator"
        ds.SeriesNumber, ds.InstanceNumber = 1, k + 1
        ds.ImagePositionPatient = [CT_ORIGIN, CT_ORIGIN, z]
        ds.ImageOrientationPatient = [1, 0, 0, 0, 1, 0]
        ds.SliceThickness, ds.SliceLocation = SLICE_STEP, z
        ds.PixelSpacing = [CT_SPACING, CT_SPACING]
        ds.Rows = ds.Columns = CT_SIZE
        ds.SamplesPerPixel, ds.PhotometricInterpretation = 1, "MONOCHROME2"
        ds.BitsAllocated, ds.BitsStored, ds.HighBit, ds.PixelRepresentation = 16, 16, 15, 0
        ds.RescaleIntercept, ds.RescaleSlope, ds.RescaleType = -1024, 1, "HU"
        ds.WindowCenter, ds.WindowWidth = 40, 400
        ds.PixelData = np.clip(hu + 1024, 0, 4095).astype(np.uint16).tobytes()
        ct.append(ds)

    struct = Dataset()
    _file(struct, RTStructureSetStorage, _uid(pid, "rtstruct"))
    _patient(struct, case, case["ro_local_id"])
    struct.Modality = "RTSTRUCT"
    struct.StudyInstanceUID, struct.SeriesInstanceUID = study_uid, _uid(pid, "rtstruct-series")
    struct.StructureSetLabel, struct.StructureSetName = spec["label"], "Planning structures"
    struct.StructureSetDate = plan_date
    contour_refs = Sequence([Dataset() for _ in ct])
    for ref, img in zip(contour_refs, ct):
        ref.ReferencedSOPClassUID, ref.ReferencedSOPInstanceUID = CTImageStorage, img.SOPInstanceUID
    series_ref = Dataset()
    series_ref.SeriesInstanceUID, series_ref.ContourImageSequence = series_uid, contour_refs
    study_ref = Dataset()
    study_ref.ReferencedSOPClassUID = "1.2.840.10008.3.1.2.3.2"
    study_ref.ReferencedSOPInstanceUID, study_ref.RTReferencedSeriesSequence = study_uid, Sequence([series_ref])
    frame_ref = Dataset()
    frame_ref.FrameOfReferenceUID, frame_ref.RTReferencedStudySequence = frame_uid, Sequence([study_ref])
    struct.ReferencedFrameOfReferenceSequence = Sequence([frame_ref])
    roi_seq, contour_seq, obs_seq = Sequence(), Sequence(), Sequence()
    for n, (roi_name, kind, color, shapes) in enumerate([("BODY", "EXTERNAL", (120, 120, 120), spec["body"])] + spec["rois"], start=1):
        roi = Dataset()
        roi.ROINumber, roi.ROIName, roi.ReferencedFrameOfReferenceUID = n, roi_name, frame_uid
        roi.ROIGenerationAlgorithm = "MANUAL"
        roi_seq.append(roi)
        rc = Dataset()
        rc.ReferencedROINumber, rc.ROIDisplayColor = n, list(color)
        contours = Sequence()
        for k, z in enumerate(Z_POSITIONS):
            for s in shapes:
                poly = shape_outline(s, z)
                if poly is None:
                    continue
                c = Dataset()
                img_ref = Dataset()
                img_ref.ReferencedSOPClassUID, img_ref.ReferencedSOPInstanceUID = CTImageStorage, ct[k].SOPInstanceUID
                c.ContourImageSequence = Sequence([img_ref])
                c.ContourGeometricType, c.NumberOfContourPoints = "CLOSED_PLANAR", len(poly)
                c.ContourData = [round(float(v), 2) for xy in poly for v in (xy[0], xy[1], z)]
                contours.append(c)
        rc.ContourSequence = contours
        contour_seq.append(rc)
        obs = Dataset()
        obs.ObservationNumber, obs.ReferencedROINumber, obs.RTROIInterpretedType = n, n, kind
        obs.ROIInterpreter = ""
        obs_seq.append(obs)
    struct.StructureSetROISequence, struct.ROIContourSequence, struct.RTROIObservationsSequence = roi_seq, contour_seq, obs_seq

    plan = Dataset()
    _file(plan, RTPlanStorage, _uid(pid, "rtplan"))
    _patient(plan, case, case["ro_local_id"])
    plan.Modality = "RTPLAN"
    plan.StudyInstanceUID, plan.SeriesInstanceUID, plan.FrameOfReferenceUID = study_uid, _uid(pid, "rtplan-series"), frame_uid
    plan.RTPlanLabel, plan.RTPlanName, plan.RTPlanDate = spec["label"], spec["name"], plan_date
    plan.RTPlanDescription = site
    plan.RTPlanGeometry, plan.PlanIntent = "PATIENT", "CURATIVE"
    plan.ApprovalStatus, plan.ReviewDate, plan.ReviewerName = "APPROVED", plan_date, case["physician"].replace("Dr. ", "").upper()
    plan.PrescriptionDescription = f"{case['dose']:g} Gy in {case['fractions']} fractions to {spec['rois'][1][0] if site == 'lung' else spec['rois'][0][0]}"
    target = Dataset()
    target.DoseReferenceNumber, target.DoseReferenceStructureType, target.DoseReferenceType = 1, "VOLUME", "TARGET"
    target.TargetPrescriptionDose = case["dose"]
    plan.DoseReferenceSequence = Sequence([target])
    beams, refs = Sequence(), Sequence()
    meterset = round(case["dose"] / case["fractions"] * 130, 1)
    for n, (beam_name, g0, g1, rot) in enumerate(spec["beams"], start=1):
        b = Dataset()
        b.BeamNumber, b.BeamName, b.BeamType = n, beam_name, "DYNAMIC" if rot != "NONE" else "STATIC"
        b.RadiationType, b.TreatmentMachineName, b.TreatmentDeliveryType = "PHOTON", "LINAC_1", "TREATMENT"
        b.NumberOfControlPoints = 2
        cps = Sequence()
        for i, angle in enumerate((g0, g1)):
            cp = Dataset()
            cp.ControlPointIndex, cp.GantryAngle = i, angle
            if i == 0:
                cp.NominalBeamEnergy, cp.GantryRotationDirection = spec["energy"], rot
            cps.append(cp)
        b.ControlPointSequence = cps
        beams.append(b)
        r = Dataset()
        r.ReferencedBeamNumber, r.BeamMeterset = n, meterset / len(spec["beams"])
        refs.append(r)
    plan.BeamSequence = beams
    fg = Dataset()
    fg.FractionGroupNumber, fg.NumberOfFractionsPlanned, fg.NumberOfBeams = 1, case["fractions"], len(spec["beams"])
    fg.ReferencedBeamSequence = refs
    plan.FractionGroupSequence = Sequence([fg])

    grid = dose_grid(site, case["dose"], seed=len(pid))
    dose = Dataset()
    _file(dose, RTDoseStorage, _uid(pid, "rtdose"))
    _patient(dose, case, case["ro_local_id"])
    dose.Modality = "RTDOSE"
    dose.StudyInstanceUID, dose.SeriesInstanceUID, dose.FrameOfReferenceUID = study_uid, _uid(pid, "rtdose-series"), frame_uid
    dose.DoseUnits, dose.DoseType, dose.DoseSummationType = "GY", "PHYSICAL", "PLAN"
    dose.DoseGridScaling = DOSE_SCALING
    plan_ref = Dataset()
    plan_ref.ReferencedSOPClassUID, plan_ref.ReferencedSOPInstanceUID = RTPlanStorage, plan.SOPInstanceUID
    dose.ReferencedRTPlanSequence = Sequence([plan_ref])
    dose.ImagePositionPatient = [DOSE_ORIGIN, DOSE_ORIGIN, Z_POSITIONS[0]]
    dose.ImageOrientationPatient = [1, 0, 0, 0, 1, 0]
    dose.PixelSpacing = [DOSE_SPACING, DOSE_SPACING]
    dose.Rows = dose.Columns = DOSE_SIZE
    dose.NumberOfFrames = SLICES
    dose.GridFrameOffsetVector = [z - Z_POSITIONS[0] for z in Z_POSITIONS]
    dose.FrameIncrementPointer = Tag(0x3004, 0x000C)
    dose.SamplesPerPixel, dose.PhotometricInterpretation = 1, "MONOCHROME2"
    dose.BitsAllocated, dose.BitsStored, dose.HighBit, dose.PixelRepresentation = 32, 32, 31, 0
    dose.PixelData = np.round(grid / DOSE_SCALING).astype(np.uint32).tobytes()
    return {"ct": ct, "struct": struct, "plan": plan, "dose": dose}


def fraction_dates(end: date, count: int) -> list[str]:
    """Weekday treatment dates ending on `end`."""
    days, d = [], end
    while len(days) < count:
        if d.weekday() < 5:
            days.append(d.isoformat())
        d = date.fromordinal(d.toordinal() - 1)
    return sorted(days)


def build_public_case(case: dict, folder) -> dict:
    """A course built on real public data: the CT series and the structure set are the
    published, de-identified files (copied, with this archive's own local id); the plan and
    the dose are illustrative, computed here on that real anatomy and labelled as such."""
    import glob
    import pydicom
    import radiation
    folder = str(folder)
    ct = sorted((pydicom.dcmread(f) for f in glob.glob(folder + "/CT/*.dcm")), key=lambda d: float(d.ImagePositionPatient[2]))
    struct = pydicom.dcmread(glob.glob(folder + "/RTSTRUCT/*.dcm")[0])
    for k, ds in enumerate(ct):
        ds.PatientID = case["pacs_local_id"]
        ds.SeriesDescription = "Planning CT (public NSCLC-Radiomics data, TCIA)"
        ds.InstanceNumber = k + 1
    struct.PatientID = case["ro_local_id"]
    pid, study_uid, frame_uid = case["patient_id"], ct[0].StudyInstanceUID, ct[0].FrameOfReferenceUID
    plan_date = case["plan_date"].replace("-", "")

    # dose grid: 4 mm in-plane over the CT field of view, one frame per CT slice
    zs = [float(d.ImagePositionPatient[2]) for d in ct]
    ct_origin = [float(v) for v in ct[0].ImagePositionPatient]
    ct_sp = [float(v) for v in ct[0].PixelSpacing]
    fov = ct[0].Columns * ct_sp[1]
    step = 4.0
    n = int(np.ceil(fov / step))
    d_origin = [ct_origin[0] - ct_sp[1] / 2 + step / 2, ct_origin[1] - ct_sp[0] / 2 + step / 2]
    rows = d_origin[1] + np.arange(n) * step
    cols = d_origin[0] + np.arange(n) * step
    roi = radiation.rois(struct)
    gtv = np.zeros((len(zs), n, n), dtype=bool)
    body = np.zeros_like(gtv)
    ci = np.clip(np.round((cols - ct_origin[0]) / ct_sp[1]).astype(int), 0, ct[0].Columns - 1)
    ri = np.clip(np.round((rows - ct_origin[1]) / ct_sp[0]).astype(int), 0, ct[0].Rows - 1)
    for k, (z, ds) in enumerate(zip(zs, ct)):
        hu = ds.pixel_array.astype(float) * float(ds.get("RescaleSlope", 1)) + float(ds.get("RescaleIntercept", 0))
        tissue = hu[np.ix_(ri, ci)] > -400
        # the patient outline: fill between the outermost tissue on each row and column, so lungs count as inside
        cols_any, rows_any = tissue.any(0), tissue.any(1)
        filled_rows = np.zeros_like(tissue)
        for r in np.where(rows_any)[0]:
            hit = np.where(tissue[r])[0]
            filled_rows[r, hit[0]:hit[-1] + 1] = True
        filled_cols = np.zeros_like(tissue)
        for c in np.where(cols_any)[0]:
            hit = np.where(tissue[:, c])[0]
            filled_cols[hit[0]:hit[-1] + 1, c] = True
        body[k] = filled_rows & filled_cols
        polys = [p for name, r in roi.items() if r["canonical"] == "GTV" for cz, ps in r["contours"].items() if abs(cz - z) < 0.5 for p in ps]
        if polys:
            gtv[k] = radiation.rasterize(polys, [d_origin[0], d_origin[1]], [step, step], (n, n))
    slice_step = abs(zs[1] - zs[0]) if len(zs) > 1 else 3.0
    d_gtv = radiation.distance_mm(gtv, (slice_step, step, step), limit=150)
    d = d_gtv - radiation.PTV_MARGIN_MM - 4          # full dose to the PTV plus 4 mm
    centre = np.argwhere(gtv).mean(0) * np.array([slice_step, step, step]) if gtv.any() else np.zeros(3)
    zz, yy, xx = np.meshgrid(np.arange(len(zs)) * slice_step, np.arange(n) * step, np.arange(n) * step, indexing="ij")
    iso = np.sqrt((zz - centre[0]) ** 2 + (yy - centre[1]) ** 2 + (xx - centre[2]) ** 2)
    rng = np.random.default_rng(len(pid))
    outside = 0.62 * np.exp(-d / 12) + 0.38 * np.exp(-d / 50) + 0.08 * np.exp(-iso / 110)
    grid = case["dose"] * np.where(d <= 0, 1.0 + 0.012 * rng.standard_normal(d.shape), np.minimum(outside, 1.0)) * body
    # spare the spinal cord as a plan would: cap the dose close to it, rising back to full 2 cm away
    cord = np.zeros_like(gtv)
    for k, z in enumerate(zs):
        polys = [p for name, r in roi.items() if r["canonical"] == "SpinalCord" for cz, ps in r["contours"].items() if abs(cz - z) < 0.5 for p in ps]
        if polys:
            cord[k] = radiation.rasterize(polys, [d_origin[0], d_origin[1]], [step, step], (n, n))
    if cord.any():
        d_cord = radiation.distance_mm(cord, (slice_step, step, step), limit=25)
        cap = case["dose"] * (0.62 + 0.38 * np.clip(d_cord / 20, 0, 1))
        grid = np.where(gtv, grid, np.minimum(grid, cap))
    grid = np.clip(grid, 0, None)

    spec = SITES["lung"]
    synthetic = build_plan_and_dose({**case, "study_uid": study_uid, "frame_uid": frame_uid, "plan_date": plan_date,
                                     "label": "LUNG_R_60_ILLUS", "name": "Right lung, illustrative plan on public CT",
                                     "target": "PTV (GTV + 7 mm)"}, spec, grid,
                                    origin=[d_origin[0], d_origin[1], zs[0]], spacing=step, zs=zs)
    return {"ct": ct, "struct": struct, **synthetic}


def build_plan_and_dose(case, spec, grid, origin, spacing, zs):
    pid = case["patient_id"]
    plan = Dataset()
    _file(plan, RTPlanStorage, _uid(pid, "rtplan"))
    _patient(plan, case, case["ro_local_id"])
    plan.Modality = "RTPLAN"
    plan.StudyInstanceUID, plan.SeriesInstanceUID, plan.FrameOfReferenceUID = case["study_uid"], _uid(pid, "rtplan-series"), case["frame_uid"]
    plan.RTPlanLabel, plan.RTPlanName, plan.RTPlanDate = case["label"], case["name"], case["plan_date"]
    plan.RTPlanDescription = case["site"]
    plan.RTPlanGeometry, plan.PlanIntent = "PATIENT", "CURATIVE"
    plan.ApprovalStatus, plan.ReviewDate, plan.ReviewerName = "APPROVED", case["plan_date"], case["physician"].replace("Dr. ", "").upper()
    plan.PrescriptionDescription = f"{case['dose']:g} Gy in {case['fractions']} fractions to {case['target']}"
    target = Dataset()
    target.DoseReferenceNumber, target.DoseReferenceStructureType, target.DoseReferenceType = 1, "VOLUME", "TARGET"
    target.TargetPrescriptionDose = case["dose"]
    plan.DoseReferenceSequence = Sequence([target])
    beams, refs = Sequence(), Sequence()
    for n, (beam_name, g0, g1, rot) in enumerate(spec["beams"], start=1):
        b = Dataset()
        b.BeamNumber, b.BeamName, b.BeamType = n, beam_name, "DYNAMIC" if rot != "NONE" else "STATIC"
        b.RadiationType, b.TreatmentMachineName, b.TreatmentDeliveryType = "PHOTON", "LINAC_1", "TREATMENT"
        b.NumberOfControlPoints = 2
        cps = Sequence()
        for i, angle in enumerate((g0, g1)):
            cp = Dataset()
            cp.ControlPointIndex, cp.GantryAngle = i, angle
            if i == 0:
                cp.NominalBeamEnergy, cp.GantryRotationDirection = spec["energy"], rot
            cps.append(cp)
        b.ControlPointSequence = cps
        beams.append(b)
        r = Dataset()
        r.ReferencedBeamNumber, r.BeamMeterset = n, round(case["dose"] / case["fractions"] * 130 / len(spec["beams"]), 1)
        refs.append(r)
    plan.BeamSequence = beams
    fg = Dataset()
    fg.FractionGroupNumber, fg.NumberOfFractionsPlanned, fg.NumberOfBeams = 1, case["fractions"], len(spec["beams"])
    fg.ReferencedBeamSequence = refs
    plan.FractionGroupSequence = Sequence([fg])

    dose = Dataset()
    _file(dose, RTDoseStorage, _uid(pid, "rtdose"))
    _patient(dose, case, case["ro_local_id"])
    dose.Modality = "RTDOSE"
    dose.StudyInstanceUID, dose.SeriesInstanceUID, dose.FrameOfReferenceUID = case["study_uid"], _uid(pid, "rtdose-series"), case["frame_uid"]
    dose.DoseUnits, dose.DoseType, dose.DoseSummationType = "GY", "PHYSICAL", "PLAN"
    dose.DoseComment = "Illustrative dose for a demo, not a clinical plan"
    dose.DoseGridScaling = DOSE_SCALING
    plan_ref = Dataset()
    plan_ref.ReferencedSOPClassUID, plan_ref.ReferencedSOPInstanceUID = RTPlanStorage, plan.SOPInstanceUID
    dose.ReferencedRTPlanSequence = Sequence([plan_ref])
    dose.ImagePositionPatient = origin
    dose.ImageOrientationPatient = [1, 0, 0, 0, 1, 0]
    dose.PixelSpacing = [spacing, spacing]
    dose.Rows, dose.Columns = grid.shape[1], grid.shape[2]
    dose.NumberOfFrames = grid.shape[0]
    dose.GridFrameOffsetVector = [z - zs[0] for z in zs]
    dose.FrameIncrementPointer = Tag(0x3004, 0x000C)
    dose.SamplesPerPixel, dose.PhotometricInterpretation = 1, "MONOCHROME2"
    dose.BitsAllocated, dose.BitsStored, dose.HighBit, dose.PixelRepresentation = 32, 32, 31, 0
    dose.PixelData = np.round(grid / DOSE_SCALING).astype(np.uint32).tobytes()
    return {"plan": plan, "dose": dose}


def write_cases(cases: list[dict]) -> int:
    """Seed the picture archive and the radiation oncology system with every course."""
    from data import pacs_system, radiation_system
    pacs_system.clear()
    radiation_system.clear()
    for case in cases:
        source = case.get("public_source")
        objs = build_public_case(case, source) if source else build_case(case)
        pacs_system.store_series(case["pacs_local_id"], objs["ct"])
        per = round(case["dose"] / case["fractions"], 2)
        radiation_system.store_course(case["ro_local_id"], objs["struct"], objs["plan"], objs["dose"],
                                      [{"fraction": n + 1, "date": d, "dose_gy": per, "status": "Delivered"}
                                       for n, d in enumerate(case["fraction_dates"])])
    return len(cases)
