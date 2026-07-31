"""
Tests for V4 task 3: hand-rolled multi-agent orchestration (multi_agent.py).

Run: pytest tests/test_v4_multi_agent.py -v
"""
import sys
import asyncio
from pathlib import Path
from unittest.mock import AsyncMock

sys.path.insert(0, str(Path(__file__).parent.parent))

from multi_agent import should_use_multi_agent, run_specialist, run_multi_agent


def run(coro):
    return asyncio.run(coro)


# ── should_use_multi_agent ──────────────────────────────────────────────────

def test_two_departments_triggers_multi_agent():
    assert should_use_multi_agent(["MRI", "Blood Profile"], is_overview=False) is True


def test_single_department_stays_single_agent():
    assert should_use_multi_agent(["Blood Profile"], is_overview=False) is False


def test_no_departments_stays_single_agent():
    assert should_use_multi_agent([], is_overview=False) is False


def test_overview_question_stays_single_agent_even_with_matches():
    """Overview questions ('summarize everything') already get one well-scoped
    broad prompt — multi-agent would only add latency, not accuracy, here."""
    assert should_use_multi_agent(["MRI", "Blood Profile"], is_overview=True) is False


# ── run_specialist ───────────────────────────────────────────────────────────

def test_specialist_gets_department_scoped_prompt_and_system_message():
    mock_generate = AsyncMock(return_value="WBC is stable across both results.")
    result = run(run_specialist(
        "Blood Profile", "[{\"result\": \"WBC 6.2\"}]", "how's her WBC and the MRI?",
        "TREND SIGNALS: none", mock_generate,
    ))
    assert result == "WBC is stable across both results."
    prompt_arg, system_arg = mock_generate.call_args[0]
    assert "Blood Profile specialist" in system_arg
    assert "Blood Profile records" in prompt_arg
    assert "WBC 6.2" in prompt_arg
    assert "how's her WBC and the MRI?" in prompt_arg


# ── run_multi_agent ──────────────────────────────────────────────────────────

def test_runs_one_specialist_per_department_plus_one_synthesis_call():
    mock_generate = AsyncMock(side_effect=[
        "MRI specialist answer.",
        "Blood profile specialist answer.",
        "Synthesized final answer.",
    ])
    final_answer, specialist_answers = run(run_multi_agent(
        "how's her WBC and what did the MRI show?",
        ["MRI", "Blood Profile"],
        {"MRI": "mri records text", "Blood Profile": "blood records text"},
        {"MRI": "", "Blood Profile": "TREND SIGNALS: none"},
        mock_generate,
    ))
    assert mock_generate.call_count == 3
    assert specialist_answers == {
        "MRI": "MRI specialist answer.",
        "Blood Profile": "Blood profile specialist answer.",
    }
    # Synthesis text leads, but see the completeness test below for the real guarantee.
    assert "Synthesized final answer." in final_answer


def test_synthesis_prompt_includes_every_specialist_answer():
    mock_generate = AsyncMock(side_effect=["MRI says X.", "Labs say Y.", "final"])
    run(run_multi_agent(
        "q", ["MRI", "Blood Profile"],
        {"MRI": "x", "Blood Profile": "y"},
        {"MRI": "", "Blood Profile": ""},
        mock_generate,
    ))
    synth_prompt_arg, synth_system_arg = mock_generate.call_args_list[2][0]
    assert "MRI says X." in synth_prompt_arg
    assert "Labs say Y." in synth_prompt_arg
    assert "DocAssist" in synth_system_arg


def test_missing_department_records_default_to_no_records_message():
    mock_generate = AsyncMock(side_effect=["specialist answer", "final"])
    run(run_multi_agent("q", ["MRI"], {}, {}, mock_generate))
    prompt_arg, _ = mock_generate.call_args_list[0][0]
    assert "No records." in prompt_arg


def test_missing_department_encoder_block_defaults_to_empty_not_shared():
    """Regression test for the 2026-07-31 cross-contamination bug: a specialist
    with no entry in encoder_block_by_dept must get an empty block, never a
    KeyError, and never another department's block."""
    mock_generate = AsyncMock(side_effect=["specialist answer", "final"])
    run(run_multi_agent("q", ["MRI"], {"MRI": "x"}, {}, mock_generate))
    prompt_arg, _ = mock_generate.call_args_list[0][0]
    assert "neutropenia" not in prompt_arg


def test_each_specialist_only_sees_its_own_encoder_block():
    """Regression test for the 2026-07-31 live-testing bug: llama3.2 invented
    a WBC reading in the MRI specialist's answer because the (blood-derived)
    global encoder block was shared across every specialist. Each specialist's
    prompt must only ever contain its own department's encoder facts."""
    mock_generate = AsyncMock(side_effect=["mri answer", "blood answer", "final"])
    run(run_multi_agent(
        "q", ["MRI", "Blood Profile"],
        {"MRI": "mri records", "Blood Profile": "blood records"},
        {"MRI": "", "Blood Profile": "DETECTED CONDITIONS: neutropenia"},
        mock_generate,
    ))
    mri_prompt_arg, _ = mock_generate.call_args_list[0][0]
    blood_prompt_arg, _ = mock_generate.call_args_list[1][0]
    assert "neutropenia" not in mri_prompt_arg
    assert "neutropenia" in blood_prompt_arg


def test_final_answer_always_includes_every_specialist_verbatim():
    """Regression test for the 2026-07-31 live-testing bug: the synthesis
    call sometimes silently dropped one specialist's finding (small-model
    unreliability, same failure mode as V3_PROGRESS.md steps 9/9b/9c).
    The final answer must deterministically include every specialist's exact
    text, regardless of what the synthesizer chose to summarize."""
    mock_generate = AsyncMock(side_effect=[
        "No intracranial metastases, brain MRI is clear.",
        "WBC 2.1, neutropenia present.",
        "The patient has neutropenia.",  # synthesizer drops the MRI finding
    ])
    final_answer, _ = run(run_multi_agent(
        "q", ["MRI", "Blood Profile"],
        {"MRI": "x", "Blood Profile": "y"},
        {"MRI": "", "Blood Profile": ""},
        mock_generate,
    ))
    assert "No intracranial metastases, brain MRI is clear." in final_answer
    assert "WBC 2.1, neutropenia present." in final_answer
