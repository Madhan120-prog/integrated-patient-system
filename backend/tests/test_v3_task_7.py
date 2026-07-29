"""
Tests for V3 task 7: Guardrails layer.

Run: pytest tests/test_v3_task_7.py -v
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from guardrails import check_confidence, check_drug_dosage, check_citations, check_diagnosis, apply_guardrails


# ── Confidence gate ────────────────────────────────────────────────────────────

def test_hedge_phrase_triggers_warning():
    r = check_confidence("I'm not sure about the patient's current status.")
    assert "Low confidence" in r


def test_short_response_triggers_warning():
    r = check_confidence("WBC is normal.")
    assert "Low confidence" in r


def test_long_confident_response_unchanged():
    text = " ".join(["WBC count is within normal limits."] * 20)  # 120 words > threshold
    r = check_confidence(text)
    assert "Low confidence" not in r


def test_uncertain_phrase_case_insensitive():
    r = check_confidence("It May Be related to the current treatment protocol.")
    assert "Low confidence" in r


# ── Drug dosage flag ───────────────────────────────────────────────────────────

def test_dosage_mg_triggers_warning():
    r = check_drug_dosage("Administer Cisplatin 75mg/m² on day 1.")
    assert "Drug dosage mentioned" in r


def test_dosage_g_triggers_warning():
    r = check_drug_dosage("Give 1.5 g IV over 30 minutes.")
    assert "Drug dosage mentioned" in r


def test_no_dosage_unchanged():
    r = check_drug_dosage("Patient is currently on Cisplatin chemotherapy.")
    assert "Drug dosage mentioned" not in r


def test_dosage_mcg_triggers_warning():
    r = check_drug_dosage("Prescribed 250mcg twice daily.")
    assert "Drug dosage mentioned" in r


# ── Citation check ─────────────────────────────────────────────────────────────

def test_citation_no_trends_triggers_warning():
    r = check_citations("WBC was 3.2 g/dL on 2026-01-15.", trends_available=False)
    assert "Unverified claim" in r


def test_citation_with_trends_no_warning():
    r = check_citations("WBC was 3.2 g/dL on 2026-01-15.", trends_available=True)
    assert "Unverified claim" not in r


def test_no_specific_values_no_warning():
    r = check_citations("The patient appears to be improving.", trends_available=False)
    assert "Unverified claim" not in r


# ── Diagnosis check ────────────────────────────────────────────────────────────

def test_most_likely_diagnosis_triggers_warning():
    r = check_diagnosis("Based on the available records, Breast Cancer is the most likely diagnosis.")
    assert "Diagnostic language detected" in r


def test_the_diagnosis_is_triggers_warning():
    r = check_diagnosis("The diagnosis is stage II adenocarcinoma.")
    assert "Diagnostic language detected" in r


def test_patient_has_x_triggers_warning():
    r = check_diagnosis("Patient has neutropenia based on the WBC trend.")
    assert "Diagnostic language detected" in r


def test_passive_summary_no_warning():
    """Citing an already-recorded diagnosis is not the LLM diagnosing."""
    r = check_diagnosis("Existing diagnosis on file: hormone receptor-positive breast cancer.")
    assert "Diagnostic language detected" not in r


def test_is_likely_phrasing_triggers_warning():
    """Live-testing regression: 'Breast cancer is likely' evaded the original
    regex, which only matched 'most likely diagnosis is X' / 'the diagnosis is X'."""
    r = check_diagnosis("Based on her age and hormone therapy response, breast cancer is likely.")
    assert "Diagnostic language detected" in r


def test_likely_represents_phrasing_triggers_warning():
    r = check_diagnosis("This finding likely represents disease recurrence.")
    assert "Diagnostic language detected" in r


# ── apply_guardrails (full pipeline) ──────────────────────────────────────────

def test_multiple_warnings_can_stack():
    """A short hedging response with a dosage should get both warnings."""
    r = apply_guardrails("It may be 75mg.", trends_available=True)
    assert "Low confidence" in r
    assert "Drug dosage mentioned" in r


def test_clean_response_unchanged():
    """A normal confident response with no dosage and trend data should pass through."""
    text = " ".join(["CEA trending down from 12.5 to 5.2 ng/mL over 3 months."] * 10)  # 130 words > threshold
    r = apply_guardrails(text, trends_available=True)
    assert "Low confidence" not in r
    assert "Unverified claim" not in r
