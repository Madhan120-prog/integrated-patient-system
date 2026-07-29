"""
Deterministic pre-processing layer between raw patient records and the LLM.
Computes lab trends arithmetically and extracts structured drug/diagnosis signals
via regex — so the LLM cites Python-computed facts rather than deriving them
from raw text (where it could hallucinate numbers).

No ML required. No external dependencies beyond stdlib.
"""
import re
from typing import Optional

# ── Trend detector ─────────────────────────────────────────────────────────────

_NUM_RE = re.compile(r"[-+]?\d+(?:\.\d+)?")


def _parse_numeric(value: str) -> Optional[float]:
    """Extract first number from a result string like '12.5 g/dL' or '8,500/µL'."""
    m = _NUM_RE.search(value.replace(",", ""))
    return float(m.group()) if m else None


def detect_trends(records: list) -> dict:
    """
    Group records by test_name, sort by date, return a trend entry for each
    test that has ≥2 numeric readings.

    Return shape per test:
      {trend: "↑"|"↓"|"→", first_val, last_val, pct_change, flag, dates}
    flag: "CRITICAL" (≥50%) | "HIGH" (≥20%) | "WATCH" (≥5%) | "STABLE"
    """
    by_test: dict = {}
    for rec in records:
        name = str(rec.get("test_name", "")).strip()
        result_str = str(rec.get("result", ""))
        date_str = str(rec.get("test_date", "") or rec.get("date", ""))
        val = _parse_numeric(result_str)
        if name and val is not None and date_str:
            by_test.setdefault(name, []).append({"val": val, "date": date_str, "raw": result_str})

    trends = {}
    for name, entries in by_test.items():
        if len(entries) < 2:
            continue
        entries.sort(key=lambda e: e["date"])
        first, last = entries[0], entries[-1]
        if first["val"] == 0:
            continue
        pct = round((last["val"] - first["val"]) / abs(first["val"]) * 100, 1)
        abs_pct = abs(pct)
        flag = "CRITICAL" if abs_pct >= 50 else "HIGH" if abs_pct >= 20 else "WATCH" if abs_pct >= 5 else "STABLE"
        trends[name] = {
            "trend": "↑" if pct > 0 else "↓" if pct < 0 else "→",
            "first_val": first["raw"],
            "last_val": last["raw"],
            "pct_change": pct,
            "flag": flag,
            "dates": [first["date"], last["date"]],
        }
    return trends


# ── NER signal extractor ───────────────────────────────────────────────────────

_DRUG_LIST = [
    "cisplatin", "carboplatin", "oxaliplatin", "paclitaxel", "docetaxel",
    "gemcitabine", "capecitabine", "fluorouracil", "doxorubicin", "cyclophosphamide",
    "methotrexate", "vincristine", "etoposide", "irinotecan", "bevacizumab",
    "trastuzumab", "pembrolizumab", "nivolumab", "atezolizumab", "erlotinib",
    "gefitinib", "osimertinib", "imatinib", "dasatinib", "rituximab", "pemetrexed",
    "tamoxifen", "letrozole", "anastrozole", "prednisone", "dexamethasone",
]

_DIAGNOSIS_LIST = [
    "neutropenia", "anemia", "thrombocytopenia", "leukopenia", "lymphopenia",
    "pancytopenia", "sepsis", "infection", "pneumonia", "carcinoma", "adenocarcinoma",
    "lymphoma", "metastasis", "metastatic", "recurrence", "remission",
    "hepatotoxicity", "nephrotoxicity", "neuropathy", "mucositis", "alopecia",
]

_DRUG_PATTERNS = [re.compile(r"\b" + d + r"\b") for d in _DRUG_LIST]
_DX_PATTERNS = [re.compile(r"\b" + dx + r"\b") for dx in _DIAGNOSIS_LIST]


def extract_ner_signals(records: list) -> dict:
    """
    Scan free-text result/notes/medication fields across all records.
    Returns {"drugs": [...], "diagnoses": [...]} — sorted, deduplicated.
    """
    text = " ".join(
        " ".join([
            str(rec.get("result", "")),
            str(rec.get("notes", "")),
            str(rec.get("medication", "")),
            str(rec.get("medicines", "")),      # treatment records store drugs here
            str(rec.get("treatment_name", "")),  # drug names also appear in the treatment label itself
            str(rec.get("diagnosis", "")),
        ])
        for rec in records
    ).lower()

    drugs = sorted({_DRUG_LIST[i] for i, p in enumerate(_DRUG_PATTERNS) if p.search(text)})
    diagnoses = sorted({_DIAGNOSIS_LIST[i] for i, p in enumerate(_DX_PATTERNS) if p.search(text)})
    return {"drugs": drugs, "diagnoses": diagnoses}


# ── Prompt block formatter ─────────────────────────────────────────────────────

def format_encoder_block(trends: dict, ner: dict) -> str:
    """Render encoder output as a structured text block for the LLM prompt."""
    lines = ["=== ENCODER ANALYSIS (Python-computed — cite these as facts, not estimates) ==="]

    if trends:
        lines.append("\nLAB TRENDS:")
        for name, t in sorted(trends.items(), key=lambda x: -abs(x[1]["pct_change"])):
            lines.append(
                f"  [{t['flag']}] {name}: {t['first_val']} → {t['last_val']} "
                f"({t['trend']} {abs(t['pct_change'])}%) "
                f"[{t['dates'][0]} → {t['dates'][1]}]"
            )
    else:
        lines.append("\nLAB TRENDS: insufficient data (need ≥2 readings of the same test)")

    drugs = ner.get("drugs", [])
    diagnoses = ner.get("diagnoses", [])
    if drugs:
        lines.append(f"\nDETECTED MEDICATIONS: {', '.join(drugs)}")
    if diagnoses:
        lines.append(f"\nDETECTED CONDITIONS: {', '.join(diagnoses)}")

    lines.append("\n=== END ENCODER ===")
    return "\n".join(lines)


# ── Tool-calling interface ─────────────────────────────────────────────────────
# A lightweight, provider-agnostic tool protocol: the LLM emits one TOOL_CALL
# line to request a deterministic fact instead of restating it from memory.
# Works identically across Gemini/Ollama/Azure — no backend-specific function-
# calling API needed, which matters most for the local model: small models
# restate structured numbers unreliably (verified in live testing — a 38→22
# U/mL trend was reported back as "0.0% change"). Routing it through a tool
# call means the number the doctor sees is the exact string Python computed.

TOOL_INSTRUCTIONS = """
You have two tools for exact data instead of estimating from memory:
- get_lab_trend("test name") — returns the precise computed trend for a lab test
- get_medications() — returns the exact list of medications on record

If answering requires a specific trend or medication list, respond with EXACTLY
one line and nothing else:
TOOL_CALL: get_lab_trend("test name")
or
TOOL_CALL: get_medications()

Otherwise answer normally without calling a tool.
"""

_TOOL_CALL_RE = re.compile(r'TOOL_CALL:\s*(get_lab_trend|get_medications)\((?:"([^"]*)")?\)')


def parse_tool_call(response: str):
    """Return (tool_name, arg) if the response requests a tool, else None."""
    m = _TOOL_CALL_RE.search(response)
    if not m:
        return None
    return m.group(1), m.group(2)


def execute_tool(tool_name: str, arg: str, trends: dict, ner: dict) -> str:
    """Run a tool against this request's already-computed encoder output."""
    if tool_name == "get_lab_trend":
        if not arg:
            return "No test name provided."
        # Doctors ask by the clinical name ("CA 15-3"), but trends are keyed by
        # the panel name ("Tumor Marker Panel") — the clinical name only shows
        # up in the raw result text, so match against both.
        arg_lower = arg.lower()
        match = next(
            (name for name, t in trends.items()
             if arg_lower in name.lower()
             or arg_lower in t["first_val"].lower()
             or arg_lower in t["last_val"].lower()),
            None,
        )
        if not match:
            return f"No trend data available for '{arg}' — fewer than 2 readings on record."
        t = trends[match]
        return (f"{match}: {t['first_val']} → {t['last_val']} "
                f"({t['trend']} {abs(t['pct_change'])}%) [{t['dates'][0]} → {t['dates'][1]}] "
                f"— flag: {t['flag']}")
    if tool_name == "get_medications":
        drugs = ner.get("drugs", [])
        return ", ".join(drugs) if drugs else "No medications detected in records."
    return f"Unknown tool: {tool_name}"


# Defensive cleanup — live testing showed the 3B model echoing the tool-call
# syntax back into its own final answer (e.g. "TOOL_CALL: get_medications()\nShe
# is on...") instead of treating it as backend-only. Strip any residual
# TOOL_CALL lines or bare function-call tokens before the doctor ever sees them.
_TOOL_ARTIFACT_RE = re.compile(
    r'TOOL_CALL:\s*(?:get_lab_trend|get_medications)\([^)]*\)\s*\n?'
    r'|\b(?:get_lab_trend|get_medications)\([^)]*\)'
)


def strip_tool_artifacts(text: str) -> str:
    cleaned = _TOOL_ARTIFACT_RE.sub('', text)
    return re.sub(r'\n{3,}', '\n\n', cleaned).strip()
