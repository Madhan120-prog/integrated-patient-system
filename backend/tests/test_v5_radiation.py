"""V5: picture archive and radiation oncology systems, synthetic DICOM RT, plan review maths."""
import asyncio
from datetime import date, datetime

import numpy as np
import pydicom
import pytest

import radiation
from data import dicom_synth, pacs_system, radiation_system
from data.seed import build_seed_data

TODAY = datetime(2026, 10, 8)
SEED = build_seed_data(today=TODAY)
# The phantom path everywhere in these tests; the public-data path has its own test below.
PHANTOM_CASES = [{k: v for k, v in c.items() if k != "public_source"} for c in SEED["radiation_cases"]]
CASES = {c["patient_id"]: c for c in PHANTOM_CASES}


@pytest.fixture(scope="module")
def stores(tmp_path_factory):
    root = tmp_path_factory.mktemp("rt")
    old = pacs_system.DB_PATH, radiation_system.DB_PATH
    pacs_system.DB_PATH, radiation_system.DB_PATH = root / "pacs_store", root / "radiation_store"
    dicom_synth.write_cases(PHANTOM_CASES)
    yield root
    pacs_system.DB_PATH, radiation_system.DB_PATH = old


def course(pid):
    mpi = next(m for m in SEED["mpi"] if m["patient_id"] == pid)
    return radiation_system.course_files(mpi["ro_local_id"]), radiation_system.delivery(mpi["ro_local_id"]), mpi


# ── Seeding ──────────────────────────────────────────────────────────────────

def test_two_courses_are_seeded_and_every_patient_has_ids_in_both_new_systems():
    assert {c["patient_id"]: c["site"] for c in SEED["radiation_cases"]} == {"P1001": "lung", "P1002": "breast"}
    assert all(m["pacs_local_id"].startswith("PACS-") and m["ro_local_id"].startswith("RO-") for m in SEED["mpi"])
    assert all("radiation" not in p for p in SEED["profiles"])            # the flag stays out of the profile


def test_fractions_end_on_the_radiation_record_and_skip_weekends():
    for pid, case in CASES.items():
        rt = next(r for r in SEED["treatment_records"] if r["patient_id"] == pid and r["treatment_name"].startswith("Radiation"))
        assert case["fraction_dates"][-1] == rt["treatment_date"]
        assert len(case["fraction_dates"]) == case["fractions"]
        assert all(date.fromisoformat(d).weekday() < 5 for d in case["fraction_dates"])
        assert case["ct_date"] < case["plan_date"] < case["fraction_dates"][0]
    assert CASES["P1001"]["physician"] == "Dr. Okafor" and CASES["P1002"]["physician"] == "Dr. Patel"


# ── Files round-trip as standard DICOM ───────────────────────────────────────

def test_files_are_standard_dicom_reached_by_each_systems_own_id(stores):
    files, delivery, mpi = course("P1001")
    modalities = {k: pydicom.dcmread(v).Modality for k, v in files.items()}
    assert modalities == {"RTSTRUCT": "RTSTRUCT", "RTPLAN": "RTPLAN", "RTDOSE": "RTDOSE"}
    series = pacs_system.list_series(mpi["pacs_local_id"])
    assert len(series) == 1 and series[0]["modality"] == "CT" and len(series[0]["files"]) == dicom_synth.SLICES
    ct = pydicom.dcmread(series[0]["files"][0])
    assert ct.FrameOfReferenceUID == pydicom.dcmread(files["RTDOSE"]).FrameOfReferenceUID
    assert ct.PatientID == mpi["pacs_local_id"] and pydicom.dcmread(files["RTPLAN"]).PatientID == mpi["ro_local_id"]
    assert len(delivery) == 30 and all(d["status"] == "Delivered" for d in delivery)
    assert radiation_system.course_files("RO-unknown") is None and pacs_system.list_series("PACS-unknown") == []


# ── Plan review ──────────────────────────────────────────────────────────────

def test_plan_analysis_reads_prescription_and_passes_the_example_constraints(stores):
    for pid, (rx, n) in {"P1001": (60, 30), "P1002": (50, 25)}.items():
        files, delivery, _ = course(pid)
        a = radiation.analyse(files, delivery)
        assert a["plan"]["rx_gy"] == rx and a["plan"]["fractions"] == n and a["plan"]["approval"] == "APPROVED"
        assert a["constraints"] and all(c["ok"] for c in a["constraints"]), a["constraints"]
        assert a["delivery"]["delivered"] == n and a["delivery"]["dose_delivered_gy"] == pytest.approx(rx)
        target = next(s["name"] for s in a["structures"] if s["type"] == "PTV")
        assert a["stats"][target]["D95"] >= 0.95 * rx
        for curve in a["dvh"].values():                                    # cumulative: starts at 100%, never rises
            vols = [v for _, v in curve]
            assert vols[0] == pytest.approx(100) and all(b <= a_ + 1e-9 for a_, b in zip(vols, vols[1:]))


def test_dose_metrics_on_a_known_answer():
    vals = np.array([10.0] * 50 + [30.0] * 50)
    m = radiation.metrics(vals, voxel_cc=0.5)
    assert m == {"volume_cc": 50.0, "mean": 20.0, "max": 30.0, "D95": 10.0, "V20": 50.0, "V5": 100.0}
    curve = dict((d, v) for d, v in radiation.dvh_curve(vals, top=40, step=10))
    assert curve == {0.0: 100.0, 10.0: 100.0, 20.0: 50.0, 30.0: 50.0, 40.0: 0.0}


def test_outline_rasterizes_to_the_right_area():
    square = np.array([[0, 0], [30, 0], [30, 30], [0, 30]], dtype=float)
    m = radiation.rasterize([square], origin=[0, 0, 0], spacing=[3, 3], shape=(20, 20))
    assert 100 <= m.sum() <= 121                                          # 10 x 10 cells, edges included


def test_constraints_flag_when_a_limit_is_missed():
    stats = {"PTV": {"D95": 55.0}, "Heart": {"mean": 25.0}, "Lungs-GTV": {"V20": 10.0, "mean": 8.0}}
    checks = {c["structure"] + c["metric"]: c["ok"] for c in radiation.check_constraints("lung", stats, rx=60)}
    assert checks == {"PTVD95": False, "Heartmean": False, "Lungs-GTVV20": True, "Lungs-GTVmean": True}


# ── De-identification ────────────────────────────────────────────────────────

def test_identifying_header_fields_are_hidden_and_dates_cut_to_the_year(stores):
    files, _, mpi = course("P1001")
    ct = pydicom.dcmread(pacs_system.list_series(mpi["pacs_local_id"])[0]["files"][0])
    out = radiation.deidentify(ct)
    assert {"PatientName", "PatientID", "PatientBirthDate", "AccessionNumber", "InstitutionName"} <= set(out["hidden"])
    text = str(out["info"])
    assert "MITCHELL" not in text and mpi["pacs_local_id"] not in text and out["info"]["year"] == CASES["P1001"]["ct_date"][:4]
    plan = radiation.deidentify(pydicom.dcmread(files["RTPLAN"]))
    assert plan["info"]["rx_gy"] == 60 and plan["info"]["fractions"] == 30 and "ReviewerName" in plan["hidden"]


# ── Gateways and rendering ───────────────────────────────────────────────────

class _MPI:
    def __init__(self, rows):
        self.rows = rows

    async def find_one(self, query, projection=None):
        return next((r for r in self.rows if r["patient_id"] == query["patient_id"]), None)


class _DB:
    def __init__(self, rows):
        self.mpi = _MPI(rows)


def test_gateways_reach_each_system_through_the_mpi(stores):
    import pacs_gateway
    import radiation_gateway
    db = _DB(SEED["mpi"])
    got = asyncio.run(radiation_gateway.get_course(db, "P1002"))
    assert got and set(got["files"]) == {"RTSTRUCT", "RTPLAN", "RTDOSE"} and len(got["delivery"]) == 25
    assert len(asyncio.run(pacs_gateway.get_series(db, "P1001"))) == 1
    assert asyncio.run(radiation_gateway.get_course(db, "P1004")) is None      # no course for this patient
    assert asyncio.run(pacs_gateway.get_series(_DB([{"patient_id": "X"}]), "X")) == []   # old MPI row without the id


def test_slice_renders_as_png_with_and_without_overlays(stores):
    files, _, mpi = course("P1001")
    ct_files = pacs_system.list_series(mpi["pacs_local_id"])[0]["files"]
    full = radiation.render_slice(ct_files, files, 17, "lung")
    bare = radiation.render_slice(ct_files, files, 17, "lung", show_contours=False, show_dose=False)
    assert full[:8] == b"\x89PNG\r\n\x1a\n" and bare[:8] == b"\x89PNG\r\n\x1a\n" and full != bare
    picture = radiation.render_any(pydicom.dcmread(ct_files[0]))
    assert picture[:4] == b"\x89PNG" and radiation.render_any(pydicom.dcmread(files["RTPLAN"])) is None


def test_treatment_breaks_count_missed_working_days():
    days = ["2026-03-02", "2026-03-03", "2026-03-04", "2026-03-10", "2026-03-11"]     # Thu, Fri, Mon missed
    assert radiation.treatment_breaks(days) == [{"after": "2026-03-04", "resumed": "2026-03-10", "working_days_missed": 3}]
    assert radiation.treatment_breaks(["2026-03-06", "2026-03-09"]) == []              # a weekend is not a break


@pytest.mark.skipif(not (__import__("pathlib").Path(__file__).parent.parent / "data/public_dicom/NSCLC-Radiomics/LUNG1-005/RTSTRUCT").exists(),
                    reason="public NSCLC-Radiomics files not downloaded")
def test_course_on_real_public_ct_derives_the_ptv_and_labels_the_dose(tmp_path):
    import pathlib
    case = dict(next(c for c in SEED["radiation_cases"] if c["patient_id"] == "P1001"))
    case["public_source"] = str(pathlib.Path(__file__).parent.parent / "data/public_dicom/NSCLC-Radiomics/LUNG1-005")
    old = pacs_system.DB_PATH, radiation_system.DB_PATH
    pacs_system.DB_PATH, radiation_system.DB_PATH = tmp_path / "p", tmp_path / "r"
    try:
        dicom_synth.write_cases([case])
        a = radiation.analyse(radiation_system.course_files(case["ro_local_id"]), radiation_system.delivery(case["ro_local_id"]))
        series = pacs_system.list_series(case["pacs_local_id"])[0]
        assert len(series["files"]) > 50 and series["zs"] == sorted(series["zs"])          # real series, in slice order
        names = {s["name"] for s in a["structures"]}
        assert {"GTV-1", "Lung-Left", "Lung-Right", "Spinal-Cord", "PTV (GTV + 7 mm, derived)"} <= names
        assert a["illustrative"] and "no clinical plan" in a["dose_note"]
        assert a["stats"]["PTV"]["D95"] >= 57 and all(c["ok"] for c in a["constraints"]), a["constraints"]
    finally:
        pacs_system.DB_PATH, radiation_system.DB_PATH = old


def test_dropped_dicom_is_summarised_and_burned_in_text_is_never_analyzed(stores):
    files, _, mpi = course("P1001")
    ct = pydicom.dcmread(pacs_system.list_series(mpi["pacs_local_id"])[0]["files"][0])
    d = radiation.describe_upload(ct)
    assert d["summary"].startswith("CT image") and d["can_analyze"] and d["preview"][:4] == b"\x89PNG"
    assert "PatientName" in d["hidden"] and "MITCHELL" not in str(d["info"]) + d["summary"]
    plan = radiation.describe_upload(pydicom.dcmread(files["RTPLAN"]))
    assert "60 Gy in 30 fractions" in plan["summary"] and not plan["can_analyze"]          # no pixels: summary only
    assert "outlines" in radiation.describe_upload(pydicom.dcmread(files["RTSTRUCT"]))["summary"]
    ct.BurnedInAnnotation = "YES"
    assert radiation.describe_upload(ct)["burned_in"] and not radiation.describe_upload(ct)["can_analyze"]
    ct.BurnedInAnnotation, ct.Modality = "", "US"                                          # ultrasound: assume text unless told otherwise
    assert not radiation.describe_upload(ct)["can_analyze"]
