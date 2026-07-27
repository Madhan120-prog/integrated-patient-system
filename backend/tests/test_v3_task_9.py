"""
Tests for V3 task 9: provider-agnostic tool-calling protocol.

Run: pytest tests/test_v3_task_9.py -v
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from encoder import parse_tool_call, execute_tool


# ── parse_tool_call ────────────────────────────────────────────────────────────

def test_parses_lab_trend_call():
    result = parse_tool_call('TOOL_CALL: get_lab_trend("CA 15-3")')
    assert result == ("get_lab_trend", "CA 15-3")


def test_parses_medications_call():
    result = parse_tool_call("TOOL_CALL: get_medications()")
    assert result == ("get_medications", None)


def test_no_tool_call_returns_none():
    result = parse_tool_call("WBC is stable, no concerns at this time.")
    assert result is None


def test_tool_call_embedded_in_extra_text_still_parses():
    """Small models don't always follow 'exactly one line' — should still parse."""
    result = parse_tool_call('Let me check.\nTOOL_CALL: get_lab_trend("WBC")\nThanks.')
    assert result == ("get_lab_trend", "WBC")


# ── execute_tool ───────────────────────────────────────────────────────────────

_SAMPLE_TRENDS = {
    "Tumor Marker Panel": {
        "trend": "↓",
        "first_val": "CA 15-3 mildly elevated (38 U/mL)",
        "last_val": "CA 15-3 normalized (22 U/mL)",
        "pct_change": -42.1, "flag": "HIGH", "dates": ["2025-02-10", "2025-09-01"],
    }
}
_SAMPLE_NER = {"drugs": ["paclitaxel", "tamoxifen"], "diagnoses": ["neutropenia"]}


def test_get_lab_trend_matches_by_clinical_name_not_just_panel_name():
    """Doctors ask by the lab name ('CA 15-3'), which only appears in the raw
    result text, not the panel key ('Tumor Marker Panel') — this is the exact
    mismatch that made the earlier live test return '0.0% change' instead of -42%."""
    result = execute_tool("get_lab_trend", "CA 15-3", _SAMPLE_TRENDS, _SAMPLE_NER)
    assert "42.1%" in result
    assert "↓" in result


def test_get_lab_trend_case_insensitive_partial_match():
    result = execute_tool("get_lab_trend", "tumor marker", _SAMPLE_TRENDS, _SAMPLE_NER)
    assert "38 U/mL" in result


def test_get_lab_trend_no_match_says_so():
    result = execute_tool("get_lab_trend", "Hemoglobin", _SAMPLE_TRENDS, _SAMPLE_NER)
    assert "No trend data available" in result


def test_get_medications_returns_full_list():
    result = execute_tool("get_medications", None, _SAMPLE_TRENDS, _SAMPLE_NER)
    assert "paclitaxel" in result
    assert "tamoxifen" in result


def test_get_medications_empty_says_so():
    result = execute_tool("get_medications", None, {}, {"drugs": [], "diagnoses": []})
    assert "No medications detected" in result
