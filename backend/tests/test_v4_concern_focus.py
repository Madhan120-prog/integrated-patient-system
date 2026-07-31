"""
Tests for a V4 live-testing bug (2026-07-31): "what's concerning?" and
"summarize status" both fell under is_overview, fetched identical records,
and a small local model produced near-duplicate answers with nothing to
differentiate the two asks. Fix is additive only — no record is ever
filtered out of the prompt, this only changes the instruction the model
gets alongside the same data.

Run: pytest tests/test_v4_concern_focus.py -v
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from encoder import is_concern_focused_question, build_concern_instruction


# ── is_concern_focused_question ─────────────────────────────────────────────

def test_detects_concerning_findings_phrasing():
    assert is_concern_focused_question("What are the most concerning findings or abnormal results?") is True


def test_detects_critical_and_worrisome():
    assert is_concern_focused_question("Anything critical or worrisome here?") is True


def test_case_insensitive():
    assert is_concern_focused_question("ABNORMAL results?") is True


def test_plain_summary_question_is_not_concern_focused():
    assert is_concern_focused_question("Summarize this patient's overall status in a few bullet points.") is False


def test_plain_treatment_question_is_not_concern_focused():
    assert is_concern_focused_question("What is the current treatment plan?") is False


# ── build_concern_instruction ────────────────────────────────────────────────

def test_no_instruction_when_not_concern_focused():
    assert build_concern_instruction(False) == ""


def test_instruction_points_at_flagged_findings_not_a_filter():
    instruction = build_concern_instruction(True)
    assert "CRITICAL" in instruction
    assert "HIGH" in instruction
    assert "DETECTED CONDITIONS" in instruction
    # Must never claim to remove/hide data — additive only.
    assert "remove" not in instruction.lower()
    assert "exclude" not in instruction.lower()
