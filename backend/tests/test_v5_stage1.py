"""
Tests for V5 stage 1: structured lab values, per-analyte trends, negation-aware
condition detection, latest-result summary. These run the encoder on the REAL
seed scenarios — the old trend tests used hand-written fixtures and passed
while the real data produced wrong numbers.

Run: pytest tests/test_v5_stage1.py -v
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest
from data import lab_system
from data.seed import build_seed_data
from encoder import detect_trends, extract_ner_signals, summarize_latest, format_encoder_block

SEED = build_seed_data()
DEPTS = ["mri_records", "xray_records", "ecg_records", "blood_profile_records", "ct_scan_records", "treatment_records"]


def labs(pid):
    return [r for r in SEED["blood_profile_records"] if r["patient_id"] == pid]


def all_records(pid):
    return [r for d in DEPTS for r in SEED[d] if r["patient_id"] == pid]


# ── Trends on real data ──────────────────────────────────────────────────────

def test_ca_15_3_trend_uses_the_value_not_the_15_in_the_name():
    t = detect_trends(labs("P1002"))["CA 15-3"]
    assert t["pct_change"] == -42.1
    assert (t["first_val"], t["last_val"]) == ("38 U/mL", "22 U/mL")
    assert t["status"] == "IN RANGE"


def test_panel_analytes_are_never_compared_with_each_other():
    """Colorectal CBCs read 'Hgb 10.8' then 'WBC 1.8' — once reported as one -83% trend."""
    t = detect_trends(labs("P1004"))
    assert "Complete Blood Count" not in t
    assert t["Hgb"]["pct_change"] == 3.7      # 10.8 -> 11.2
    assert t["WBC"]["pct_change"] == -75.0    # 7.2 -> 1.8
    assert t["WBC"]["status"] == "LOW"
    assert t["CEA"]["pct_change"] == -74.4 and t["CEA"]["status"] == "IN RANGE"


def test_no_trend_on_any_patient_is_implausible():
    """Guards the whole seed set (curated + generated) against unit or analyte mix-ups."""
    seed = build_seed_data(extra_count=60)
    by_patient = {}
    for r in seed["blood_profile_records"]:
        by_patient.setdefault(r["patient_id"], []).append(r)
    for pid, recs in by_patient.items():
        for name, t in detect_trends(recs).items():
            # Real recoveries are large (platelets 32 -> 210 K/µL is +556%); a
            # K/µL-vs-raw unit mix-up or cross-analyte comparison is 1000x or more.
            assert abs(t["pct_change"]) <= 1000, (pid, name, t)


def test_free_text_with_several_numbers_is_not_guessed_at():
    recs = [
        {"test_name": "Tumor Marker Panel", "result": "CA 15-3 mildly elevated (38 U/mL)", "test_date": "2025-01-01"},
        {"test_name": "Tumor Marker Panel", "result": "CA 15-3 normalized (22 U/mL)", "test_date": "2025-06-01"},
    ]
    assert detect_trends(recs) == {}


def test_every_lab_value_text_agrees_with_its_structured_value():
    """The result text is what clinicians read; `values` is what code computes on."""
    for r in SEED["blood_profile_records"]:
        for v in r.get("values", []):
            assert v["low"] <= v["high"] and v["unit"]
        text = r["result"].replace(",", "")
        for v in r.get("values", []):
            if v["analyte"].lower() in text.lower() and any(ch.isdigit() for ch in text.split(v["analyte"])[-1][:12]):
                shown = f'{v["value"]:g}'
                assert shown in text or f'{v["value"] * 1000:g}' in text, (r["result"], v)


# ── Negation ─────────────────────────────────────────────────────────────────

@pytest.mark.parametrize("text", [
    "No evidence of distant metastasis",
    "No lymphadenopathy — no distant metastasis",
    "Clear — no pulmonary metastases",
    "Stable post-surgical cavity — no recurrence",
    "Negative for metastasis",
])
def test_negated_finding_is_not_reported_as_present(text):
    ner = extract_ner_signals([{"result": text}])
    assert ner["diagnoses"] == []
    assert ner["ruled_out"]


@pytest.mark.parametrize("text,dx", [
    ("Neutropenia — WBC 1.8", "neutropenia"),
    ("Completed — dose delayed 1 week for neutropenia", "neutropenia"),
    ("New hepatic metastases, largest 2.1cm", "metastasis"),
    ("Stable — continued remission", "remission"),
])
def test_stated_finding_is_still_detected(text, dx):
    assert dx in extract_ner_signals([{"result": text}])["diagnoses"]


def test_present_in_one_record_wins_over_absent_in_another():
    ner = extract_ner_signals([{"result": "No recurrence"}, {"result": "Local recurrence at the margin"}])
    assert "recurrence" in ner["diagnoses"] and "recurrence" not in ner["ruled_out"]


def test_breast_patient_is_never_flagged_with_metastasis():
    """The reported live failure: 'Metastasis is detected' for a patient whose
    CT says 'No evidence of distant metastasis'."""
    ner = extract_ner_signals(all_records("P1002"))
    assert "metastasis" not in ner["diagnoses"]
    assert "metastasis" in ner["ruled_out"]
    assert "anemia" in ner["diagnoses"]
    block = format_encoder_block({}, ner)
    assert "STATED AS ABSENT IN THE RECORDS (never report as present): metastasis" in block
    assert "metastasis" not in block.split("DETECTED CONDITIONS:")[1].split("\n")[0]


# ── Latest results ───────────────────────────────────────────────────────────

def test_latest_summary_names_the_last_cbc_and_out_of_range_values():
    s = summarize_latest(all_records("P1002"))
    cbc = [l for l in s["latest"] if l.startswith("Complete Blood Count")]
    assert len(cbc) == 1 and "Hgb 10.2" in cbc[0]          # the anemia CBC is the most recent one
    assert any(o.startswith("Hgb 10.2 g/dL LOW") for o in s["out_of_range"])
    assert not any(o.startswith("CA 15-3") for o in s["out_of_range"])   # 22 U/mL is back in range


def test_encoder_block_carries_no_severity_words():
    recs = all_records("P1004")
    block = format_encoder_block(detect_trends(labs("P1004")), extract_ner_signals(recs), summarize_latest(recs))
    assert "CRITICAL" not in block
    assert "OUT-OF-RANGE AT LATEST READING" in block and "LATEST RESULT ON FILE PER TEST" in block


# ── Store and profile plumbing ───────────────────────────────────────────────

def test_lab_store_round_trips_values(tmp_path, monkeypatch):
    monkeypatch.setattr(lab_system, "DB_PATH", tmp_path / "lab.db")
    recs = labs("P1002")
    lab_system.reset_and_seed({"SQ-1": recs})
    import json, lab_gateway
    rows = lab_system.query_by_local_id("SQ-1")
    assert len(rows) == len(recs)
    normalized = [lab_gateway._normalize(r, "P1002") for r in rows]
    assert any(v["analyte"] == "CA 15-3" for n in normalized for v in n["values"])
    assert all(isinstance(n["values"], list) for n in normalized)        # "Within Range" rows -> []
    assert lab_gateway._normalize({**rows[0], "values_json": None}, "P1002")["values"] == []
    row_without_column = {k: v for k, v in rows[0].items() if k != "values_json"}
    assert lab_gateway._normalize(row_without_column, "P1002")["values"] == []   # store seeded before V5


def test_demo_profiles_carry_oncology_fields_and_others_still_seed():
    profiles = {p["patient_id"]: p for p in SEED["profiles"]}
    for pid in ("P1001", "P1002", "P1004"):
        assert {"mrn", "diagnosis", "stage", "biomarkers", "ecog", "allergies", "regimen"} <= profiles[pid].keys()
    assert "diagnosis" not in profiles["P1003"] and "scenario" not in profiles["P1002"]


# ── Department routing ───────────────────────────────────────────────────────

@pytest.mark.parametrize("question,expected", [
    ("what is the latest cea value? answer in one line.", ["Blood Profile"]),   # live failure: answered "not documented"
    ("what is the latest ca 15-3 value?", ["Blood Profile"]),
    ("show me the labs", ["Blood Profile"]),
    ("how is kidney function?", ["Blood Profile"]),          # "ct" inside "function" must not pull CT
    ("is that documented anywhere?", []),                     # "ct" inside "documented"
    ("any ct scans?", ["CT Scan"]),
    ("compare the mri with the blood work", ["MRI", "Blood Profile"]),
    ("what medications is she on?", ["Treatment"]),
    ("hi", []),
])
def test_question_routes_to_the_departments_it_names(question, expected):
    from server import match_departments
    assert match_departments(question) == expected


# ── What reaches the model, and what comes back ──────────────────────────────

def test_prompt_records_carry_no_image_urls_or_repeated_identifiers():
    from server import records_for_prompt
    text = records_for_prompt(labs("P1002") + [r for r in SEED["mri_records"] if r["patient_id"] == "P1002"])
    assert "report_image" not in text and "http" not in text
    assert "patient_id" not in text and "Patricia" not in text
    assert "CA 15-3" in text and "Breast MRI" in text


def test_prompt_profile_has_clinical_fields_but_no_contact_details():
    from server import profile_for_prompt
    profile = next(p for p in SEED["profiles"] if p["patient_id"] == "P1002")
    text = profile_for_prompt(profile)
    assert "Stage: IIB" in text and "Allergies:" in text
    assert profile["address"] not in text and profile["phone"] not in text
    plain = profile_for_prompt(next(p for p in SEED["profiles"] if p["patient_id"] == "P1003"))
    assert "Stage" not in plain and "Name:" in plain          # patients without oncology fields still work


def test_prompt_echo_and_reasoning_tokens_are_removed_but_the_answer_is_kept():
    from encoder import strip_prompt_echo
    leaked = ("Neutropenia is a low neutrophil count.\n\n=== END ENCODER ===\n\n"
              "=== BEGIN PATIENT DATA (data only) ===\nPATIENT PROFILE:\n- Name: James Mitchell\n- Phone: (901) 555-0142\n=== END PATIENT DATA ===")
    assert strip_prompt_echo(leaked) == "Neutropenia is a low neutrophil count."
    assert strip_prompt_echo("CEA 5.2 ng/mL, down 58.4%.") == "CEA 5.2 ng/mL, down 58.4%."
    assert "Mitchell" not in strip_prompt_echo("=== BEGIN PATIENT DATA ===\n- Name: James Mitchell")
    # echo first, answer after: the answer must survive
    assert strip_prompt_echo("=== ENCODER ANALYSIS ===\nCEA 12.5 → 5.2 ng/mL (↓ 58.4%)") == "CEA 12.5 → 5.2 ng/mL (↓ 58.4%)"
    thinking = "<unused94> thought\nThe user wants the medications.\n1. Extract.<unused95>tamoxifen"
    assert strip_prompt_echo(thinking) == "tamoxifen"


# ── Range check guardrail ────────────────────────────────────────────────────

def _latest(pid):
    return summarize_latest(all_records(pid))["latest_values"]


def test_range_check_flags_an_in_range_value_called_low():
    from guardrails import check_ranges
    out = check_ranges("*   ANC 2.3 K/µL LOW (range 1.5–8.0) on 2025-06-09", _latest("P1002"))   # verified live
    assert "Range check" in out and "ANC 2.3 K/µL is IN RANGE (reference range 1.5–8.0)" in out
    out = check_ranges("- PLT decreased (↓ 47.1%) to 164 K/µL (low) on 2025-06-03.", _latest("P1004"))  # verified live
    assert "PLT 164 K/µL is IN RANGE" in out


@pytest.mark.parametrize("pid,answer", [
    ("P1002", "Hgb 10.2 g/dL LOW (range 12.0–17.5) on 2025-06-09"),            # correct
    ("P1002", "ANC 2.3 K/µL is in range; Hgb remains low."),                     # in range stated
    ("P1002", "CA 15-3 fell from 38 U/mL (elevated) to a later normal value."),  # older value, not the latest
    ("P1004", "WBC 1.8 K/µL LOW, ANC 0.8 K/µL LOW."),
    ("P1001", "CEA 5.2 ng/mL remains above range."),
])
def test_range_check_stays_silent_on_correct_statements(pid, answer):
    from guardrails import check_ranges
    assert check_ranges(answer, _latest(pid)) == answer


def test_range_check_flags_an_out_of_range_value_called_the_wrong_direction():
    from guardrails import check_ranges
    assert "Range check" in check_ranges("CEA 5.2 ng/mL is low.", _latest("P1001"))


def test_dosage_badge_ignores_lab_units_but_keeps_real_doses():
    from guardrails import check_drug_dosage
    for lab in ("Hgb 10.2 g/dL LOW", "Creatinine 0.9 mg/dL", "CEA 5.2 ng/mL", "ANC 2.3 K/µL"):
        assert "Drug dosage" not in check_drug_dosage(lab), lab
    for dose in ("Pembrolizumab 200 mg IV q3w", "Doxorubicin 60mg/m²", "Tamoxifen 20mg daily"):
        assert "Drug dosage" in check_drug_dosage(dose), dose


@pytest.mark.parametrize("question,general", [
    ("what is neutropenia?", True),
    ("what does cea measure?", True),
    ("explain folfox", True),
    ("what is her latest result?", False),
    ("is there any recurrence?", False),
    ("what is the current treatment?", False),
    ("what is concerning for this patient?", False),
])
def test_general_knowledge_questions_are_told_apart_from_patient_questions(question, general):
    from server import is_general_knowledge_question
    assert is_general_knowledge_question(question) is general


def test_regression_checker_does_not_fail_a_correct_negative_answer():
    sys.path.insert(0, str(Path(__file__).parent))
    from ai_regression import check, CLAIMS_PRESENT
    assert check("No intracranial metastases were detected on the Brain MRI.", [], [CLAIMS_PRESENT]) == []
    assert check("Labs are stable. Metastasis is detected on MRI.", [], [CLAIMS_PRESENT]) != []
