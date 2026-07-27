"""
Tests for V3 task 6: Encoder layer (trend detector + NER signals).

Run: pytest tests/test_v3_task_6.py -v
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from encoder import detect_trends, extract_ner_signals, format_encoder_block


# ── Trend detector ─────────────────────────────────────────────────────────────

def test_trend_falling_critical():
    records = [
        {"test_name": "WBC", "result": "45000 /µL", "test_date": "2026-01-01"},
        {"test_name": "WBC", "result": "3200 /µL",  "test_date": "2026-03-01"},
    ]
    t = detect_trends(records)
    assert "WBC" in t
    assert t["WBC"]["trend"] == "↓"
    assert t["WBC"]["flag"] == "CRITICAL"
    assert t["WBC"]["pct_change"] < -50


def test_trend_rising_high():
    records = [
        {"test_name": "CEA", "result": "2.5 ng/mL", "test_date": "2026-01-01"},
        {"test_name": "CEA", "result": "5.2 ng/mL", "test_date": "2026-04-01"},
    ]
    t = detect_trends(records)
    assert t["CEA"]["trend"] == "↑"
    assert t["CEA"]["flag"] in ("HIGH", "CRITICAL")


def test_trend_stable():
    records = [
        {"test_name": "Hemoglobin", "result": "13.2 g/dL", "test_date": "2026-01-01"},
        {"test_name": "Hemoglobin", "result": "13.5 g/dL", "test_date": "2026-03-01"},
    ]
    t = detect_trends(records)
    assert t["Hemoglobin"]["flag"] == "STABLE"


def test_single_reading_excluded():
    """Only one data point — no trend possible, should not appear in output."""
    records = [{"test_name": "Platelets", "result": "150000", "test_date": "2026-01-01"}]
    t = detect_trends(records)
    assert "Platelets" not in t


def test_trend_sorted_by_date():
    """Records may arrive out of order; trend should still be first→last by date."""
    records = [
        {"test_name": "RBC", "result": "5.0 M/µL",  "test_date": "2026-03-01"},
        {"test_name": "RBC", "result": "3.0 M/µL",  "test_date": "2026-01-01"},
    ]
    t = detect_trends(records)
    assert t["RBC"]["first_val"] == "3.0 M/µL"
    assert t["RBC"]["last_val"]  == "5.0 M/µL"
    assert t["RBC"]["trend"] == "↑"


# ── NER signal extractor ───────────────────────────────────────────────────────

def test_ner_detects_drug():
    records = [{"result": "Patient is on Cisplatin 75mg/m² q3w"}]
    signals = extract_ner_signals(records)
    assert "cisplatin" in signals["drugs"]


def test_ner_detects_diagnosis():
    records = [{"result": "Grade 3 neutropenia observed"}]
    signals = extract_ner_signals(records)
    assert "neutropenia" in signals["diagnoses"]


def test_ner_detects_drug_in_medicines_field():
    """Treatment records store drug names under 'medicines', not 'medication' —
    real bug found in live testing where Paclitaxel was omitted from a drug list."""
    records = [{
        "treatment_name": "Chemotherapy — Paclitaxel Cycle 1",
        "result": "Completed",
        "medicines": "Paclitaxel 80mg/m² weekly, Diphenhydramine 50mg",
    }]
    signals = extract_ner_signals(records)
    assert "paclitaxel" in signals["drugs"]


def test_ner_case_insensitive():
    records = [{"medication": "PACLITAXEL 175mg", "result": "Metastatic adenocarcinoma"}]
    signals = extract_ner_signals(records)
    assert "paclitaxel" in signals["drugs"]
    assert "adenocarcinoma" in signals["diagnoses"]


def test_ner_empty_records():
    signals = extract_ner_signals([])
    assert signals == {"drugs": [], "diagnoses": []}


# ── Prompt block formatter ─────────────────────────────────────────────────────

def test_format_block_has_critical_flag():
    trends = {"WBC": {"trend": "↓", "first_val": "45000", "last_val": "3200",
                      "pct_change": -92.9, "flag": "CRITICAL", "dates": ["2026-01", "2026-03"]}}
    ner = {"drugs": ["cisplatin"], "diagnoses": ["neutropenia"]}
    block = format_encoder_block(trends, ner)
    assert "CRITICAL" in block
    assert "WBC" in block
    assert "cisplatin" in block
    assert "neutropenia" in block


def test_format_block_empty_trends_message():
    block = format_encoder_block({}, {"drugs": [], "diagnoses": []})
    assert "insufficient data" in block
