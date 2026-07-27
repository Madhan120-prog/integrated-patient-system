"""
Guardrails layer — additive safety checks applied to every LLM response
before it reaches the frontend. Never modifies or removes content; only
appends structured warnings where applicable.
"""
import re

# ── Confidence gate ────────────────────────────────────────────────────────────

_HEDGE_PHRASES = [
    "i'm not sure", "i am not sure", "not certain", "unclear",
    "it may be", "it might be", "it could be", "possibly",
    "i cannot determine", "i can't determine", "cannot confirm",
    "insufficient information", "not enough information",
    "i don't have enough", "i do not have enough",
]

_CONFIDENCE_WARNING = (
    "\n\n⚠ **Low confidence** — response is uncertain or lacks sufficient data. "
    "Verify against current clinical guidelines before acting."
)

_SHORT_RESPONSE_WORDS = 80


def check_confidence(response: str) -> str:
    lower = response.lower()
    word_count = len(response.split())
    has_hedge = any(phrase in lower for phrase in _HEDGE_PHRASES)
    is_short = word_count < _SHORT_RESPONSE_WORDS
    if has_hedge or is_short:
        return response + _CONFIDENCE_WARNING
    return response


# ── Drug dosage flag ───────────────────────────────────────────────────────────

# Matches: "75mg", "200 mg", "1.5 g", "75 mg/m²", "500mg/day", "2.5mcg"
_DOSAGE_RE = re.compile(
    r"\b\d+(?:\.\d+)?\s*(?:mg|g|mcg|µg|ug|ml|mL|mmol|units?)(?:/(?:m²|m2|kg|day|hr|hour|dose))?\b",
    re.IGNORECASE,
)

_DOSAGE_WARNING = (
    "\n\n⚠ **Drug dosage mentioned** — always confirm against current formulary "
    "and patient weight/BSA before prescribing or administering."
)


def check_drug_dosage(response: str) -> str:
    if _DOSAGE_RE.search(response):
        return response + _DOSAGE_WARNING
    return response


# ── Citation check ─────────────────────────────────────────────────────────────

# Phrases that suggest the LLM is making a claim about a specific lab value or date
_CLAIM_RE = re.compile(
    r"\b(\d{4}-\d{2}-\d{2}|\d+(?:\.\d+)?\s*(?:g/dL|mg/dL|mmol/L|/µL|U/L|ng/mL|%|IU/L))\b",
    re.IGNORECASE,
)

_CITATION_WARNING = (
    "\n\n⚠ **Unverified claim** — specific values cited but no source records "
    "were available to the encoder. Cross-check against the patient's raw records."
)


def check_citations(response: str, trends_available: bool) -> str:
    """Flag if the response cites specific values but encoder had no trend data."""
    if not trends_available and _CLAIM_RE.search(response):
        return response + _CITATION_WARNING
    return response


# ── Apply all guardrails in sequence ──────────────────────────────────────────

def apply_guardrails(response: str, trends_available: bool) -> str:
    """Run all three checks in order. Each may append a warning."""
    response = check_confidence(response)
    response = check_drug_dosage(response)
    response = check_citations(response, trends_available)
    return response
