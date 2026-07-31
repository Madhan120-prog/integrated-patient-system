"""
V4 multi-agent orchestration — hand-rolled (plain Python), not a framework.

LangGraph/CrewAI were considered and deferred to a future version — this
project's whole philosophy is "understand what's happening under the hood,"
and at this scale a framework adds a dependency without adding capability.
Revisit if/when the orchestration graph gets complex enough that hand-rolled
routing becomes the harder-to-read option.

Only triggers for genuinely compound questions — the keyword classifier in
server.py matching 2+ specific departments in one question (e.g. "how's her
WBC and what did the MRI show?"). Single-department and overview questions
keep using the existing one-call path; splitting those into "specialists"
would add latency for no benefit — a single department or a "summarize
everything" ask is already well served by one broad prompt.

Design: one focused specialist call per matched department (narrow context,
narrow instructions) -> one synthesizer call that merges the specialists'
answers into the same chart-note style the rest of the app uses. This
mirrors the "explicit roles + shared-state handoff" pattern from real
multi-agent clinical-AI literature (project_knowledge.md SS11) rather than
inventing a bespoke taxonomy.
"""
from typing import Awaitable, Callable

GenerateFn = Callable[[str, str], Awaitable[str]]


def should_use_multi_agent(keyword_matched: list, is_overview: bool) -> bool:
    """2+ specific departments named in one question -> compound ask, worth
    splitting. Overview questions already get a single broad synthesis and
    work fine as one call; multi-agent would just slow those down."""
    return len(keyword_matched) >= 2 and not is_overview


SPECIALIST_SYSTEM_PROMPT = """You are a {department} specialist supporting a clinical AI assistant.
The doctor's question may ask about things outside {department} too — that's
expected, another specialist is handling those parts. Only answer the part of
the question that {department} records can actually answer. Do not mention,
guess at, or comment on any other department's data at all, even to say it's
missing or unavailable — simply omit it, as if that part of the question
wasn't asked. Be concise: 2-4 sentences or short bullets, doctor-facing
shorthand (WBC, Hgb, etc. — don't spell these out). If nothing in these
{department} records is relevant, say so in one line."""

SYNTHESIZER_SYSTEM_PROMPT = """You are DocAssist, a clinical AI assistant. You've received a separate
specialist answer for each department relevant to the doctor's question.
Combine them into ONE coherent chart-note style answer:
- Lead with the most clinically significant finding across all specialists,
  flagged with a warning symbol if abnormal or concerning
- Keep each department's contribution short — synthesize, don't just
  concatenate the specialist text verbatim
- Do not introduce any fact that isn't present in the specialist answers
- End with one relevant follow-up question only if it adds value"""


async def run_specialist(department: str, records_text: str, question: str,
                          encoder_block: str, generate_fn: GenerateFn) -> str:
    system_message = SPECIALIST_SYSTEM_PROMPT.format(department=department)
    prompt = f"""Doctor's question: {question}

{encoder_block}

{department} records:
{records_text}"""
    return await generate_fn(prompt, system_message)


async def run_multi_agent(question: str, matched_departments: list,
                           records_text_by_dept: dict, encoder_block_by_dept: dict,
                           generate_fn: GenerateFn) -> tuple[str, dict]:
    """Runs one specialist per matched department, then synthesizes.

    `encoder_block_by_dept` must be scoped per department, not one shared
    block — live-testing bug found 2026-07-31: passing the same global
    encoder block (computed over every fetched department) to every
    specialist let a small local model (llama3.2) treat another
    department's facts as its own — the MRI specialist started inventing
    WBC readings because a lab-derived "neutropenia" fact was sitting in
    its prompt. Each specialist must only ever see facts computed from its
    own department's records.

    Returns (final_answer, specialist_answers). `final_answer` always ends
    with a deterministic, verbatim-per-department breakdown — a second
    live-testing bug found the same day: the synthesis call sometimes
    dropped one specialist's finding entirely (small-model unreliability,
    the same failure mode documented in V3_PROGRESS.md steps 9/9b/9c).
    Rather than trust the model to include every department, the raw
    specialist answers are always appended by construction, so nothing can
    be silently lost — the synthesis call only has to provide the leading
    summary, not guarantee completeness.
    """
    specialist_answers = {}
    for dept in matched_departments:
        specialist_answers[dept] = await run_specialist(
            dept, records_text_by_dept.get(dept, "No records."), question,
            encoder_block_by_dept.get(dept, ""), generate_fn,
        )

    combined = "\n\n".join(f"[{d} specialist]: {a}" for d, a in specialist_answers.items())
    synth_prompt = f"""Doctor's question: {question}

Specialist answers:
{combined}"""
    summary = await generate_fn(synth_prompt, SYNTHESIZER_SYSTEM_PROMPT)

    breakdown = "\n".join(f"- **{d}**: {a}" for d, a in specialist_answers.items())
    final_answer = f"{summary}\n\n---\n*By department:*\n{breakdown}"
    return final_answer, specialist_answers
