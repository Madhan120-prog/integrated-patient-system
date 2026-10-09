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


def _readings(rec: dict):
    """Yield (key, value, display, low, high) for each numeric reading in a record.
    Structured `values` (one entry per analyte) are the source of truth. Free
    text is only trusted when it holds exactly one number — taking the first
    number misread "CA 15-3 ... (38 U/mL)" as 15 and compared different
    analytes of one panel ("Hgb 10.8" vs "WBC 1.8") as a single trend."""
    if rec.get("values"):
        for v in rec["values"]:
            yield v["analyte"], float(v["value"]), f'{v["value"]} {v["unit"]}', v.get("low"), v.get("high")
        return
    # ponytail: fallback still keys by test_name, so two analytes written as
    # single numbers under one panel name would be compared. Seed data carries
    # `values`; give real feeds structured analytes rather than widening this.
    name = str(rec.get("test_name", "")).strip()
    result = str(rec.get("result", ""))
    nums = _NUM_RE.findall(result.replace(",", ""))
    if name and len(nums) == 1:
        yield name, float(nums[0]), result, None, None


def _range_status(val: float, low, high):
    if low is None or high is None:
        return None
    return "LOW" if val < low else "HIGH" if val > high else "IN RANGE"


def _by_analyte(records: list) -> dict:
    by_key: dict = {}
    for rec in records:
        date_str = str(rec.get("test_date", "") or rec.get("date", ""))
        if not date_str:
            continue
        for key, val, raw, low, high in _readings(rec):
            by_key.setdefault(key, []).append({"val": val, "date": date_str, "raw": raw, "low": low, "high": high})
    for entries in by_key.values():
        entries.sort(key=lambda e: e["date"])
    return by_key


def detect_trends(records: list) -> dict:
    """
    Group readings by analyte, sort by date, return a trend entry for each
    analyte that has ≥2 numeric readings.

    Return shape per analyte:
      {trend: "↑"|"↓"|"→", first_val, last_val, pct_change, flag, dates, status}
    flag is the SIZE of the change, not clinical severity:
      "LARGE CHANGE" (≥50%) | "MODERATE CHANGE" (≥20%) | "SMALL CHANGE" (≥5%) | "STABLE"
    status is the latest reading against its reference range:
      "LOW" | "HIGH" | "IN RANGE" | None (no range on record)
    """
    trends = {}
    for name, entries in _by_analyte(records).items():
        if len(entries) < 2:
            continue
        first, last = entries[0], entries[-1]
        if first["val"] == 0:
            continue
        pct = round((last["val"] - first["val"]) / abs(first["val"]) * 100, 1)
        abs_pct = abs(pct)
        flag = ("LARGE CHANGE" if abs_pct >= 50 else "MODERATE CHANGE" if abs_pct >= 20
                else "SMALL CHANGE" if abs_pct >= 5 else "STABLE")
        trends[name] = {
            "trend": "↑" if pct > 0 else "↓" if pct < 0 else "→",
            "first_val": first["raw"],
            "last_val": last["raw"],
            "pct_change": pct,
            "flag": flag,
            "dates": [first["date"], last["date"]],
            "status": _range_status(last["val"], last["low"], last["high"]),
        }
    return trends


def summarize_latest(records: list) -> dict:
    """Deterministic 'where things stand' facts, so the LLM never has to infer
    recency or abnormality itself:
      latest:       one line per test — the most recent result on file
      out_of_range: analytes whose most recent reading is outside its range
    Both exist to stop two verified failures: claiming a finding had resolved
    when no later result existed, and inventing severity for a keyword hit."""
    latest_by_test: dict = {}
    for rec in records:
        name, date_str = rec.get("test_name"), str(rec.get("test_date", ""))
        if name and date_str and date_str >= latest_by_test.get(name, ("",))[0]:
            latest_by_test[name] = (date_str, str(rec.get("result", "")))
    out_of_range, latest_values = [], {}
    for name, entries in _by_analyte(records).items():
        last = entries[-1]
        status = _range_status(last["val"], last["low"], last["high"])
        if status:
            latest_values[name] = {"value": last["val"], "display": last["raw"], "status": status,
                                   "low": last["low"], "high": last["high"], "date": last["date"]}
        if status in ("LOW", "HIGH"):
            out_of_range.append(f'{name} {last["raw"]} {status} (range {last["low"]}–{last["high"]}) on {last["date"]}')
    return {
        "latest": [f"{n} — {d}: {r}" for n, (d, r) in sorted(latest_by_test.items())],
        "out_of_range": sorted(out_of_range),
        "latest_values": latest_values,   # for guardrails.check_ranges, not for the prompt
    }


# ── NER signal extractor ───────────────────────────────────────────────────────

_DRUG_LIST = [
    "cisplatin", "carboplatin", "oxaliplatin", "paclitaxel", "docetaxel",
    "gemcitabine", "capecitabine", "fluorouracil", "doxorubicin", "cyclophosphamide",
    "methotrexate", "vincristine", "etoposide", "irinotecan", "bevacizumab",
    "trastuzumab", "pembrolizumab", "nivolumab", "atezolizumab", "erlotinib",
    "gefitinib", "osimertinib", "imatinib", "dasatinib", "rituximab", "pemetrexed",
    "tamoxifen", "letrozole", "anastrozole", "prednisone", "dexamethasone",
    "5-fu", "leucovorin", "filgrastim",
]

_DIAGNOSIS_LIST = [
    "neutropenia", "anemia", "thrombocytopenia", "leukopenia", "lymphopenia",
    "pancytopenia", "sepsis", "infection", "pneumonia", "carcinoma", "adenocarcinoma",
    "lymphoma", "metastasis", "metastases", "metastatic", "recurrence", "remission",
    "hepatotoxicity", "nephrotoxicity", "neuropathy", "mucositis", "alopecia",
]

_DRUG_PATTERNS = [re.compile(r"\b" + d + r"\b") for d in _DRUG_LIST]
_DX_PATTERNS = [re.compile(r"\b" + dx + r"\b") for dx in _DIAGNOSIS_LIST]


# A finding only counts as present if no negation cue precedes it in the same
# clause. Without this, "No evidence of distant metastasis" was reported to the
# LLM as DETECTED CONDITIONS: metastasis — the opposite of the record.
_NEGATION_RE = re.compile(r"\b(?:no|not|without|negative for|free of|ruled out|absence of)\b")
_CLAUSE_SPLIT_RE = re.compile(r"[.;,\n—–]| - ")
_DX_ALIASES = {"metastases": "metastasis"}


def extract_ner_signals(records: list) -> dict:
    """
    Scan free-text result/notes/medication fields across all records.
    Returns {"drugs": [...], "diagnoses": [...], "ruled_out": [...]} — sorted,
    deduplicated. `diagnoses` are stated as present somewhere; `ruled_out` are
    only ever stated as absent.
    """
    fields = [
        " ".join([
            str(rec.get("result", "")),
            str(rec.get("notes", "")),
            str(rec.get("medication", "")),
            str(rec.get("medicines", "")),      # treatment records store drugs here
            str(rec.get("treatment_name", "")),  # drug names also appear in the treatment label itself
            str(rec.get("diagnosis", "")),
        ]).lower()
        for rec in records
    ]
    text = " ".join(fields)
    drugs = sorted({_DRUG_LIST[i] for i, p in enumerate(_DRUG_PATTERNS) if p.search(text)})

    present, negated = set(), set()
    for field in fields:
        for clause in _CLAUSE_SPLIT_RE.split(field):
            for i, p in enumerate(_DX_PATTERNS):
                m = p.search(clause)
                if m:
                    dx = _DX_ALIASES.get(_DIAGNOSIS_LIST[i], _DIAGNOSIS_LIST[i])
                    (negated if _NEGATION_RE.search(clause[:m.start()]) else present).add(dx)
    return {"drugs": drugs, "diagnoses": sorted(present), "ruled_out": sorted(negated - present)}


# ── Prompt block formatter ─────────────────────────────────────────────────────

_CONCERN_KEYWORDS = ["concerning", "concern", "abnormal", "critical", "worrisome", "red flag", "urgent"]


def is_concern_focused_question(question: str) -> bool:
    """Detects a question asking specifically about abnormal/concerning findings,
    as opposed to a general 'summarize everything' overview ask. Both currently
    fetch the same records — this only changes how the model is instructed to
    use them, never what data it sees (see build_concern_instruction)."""
    q = question.lower()
    return any(k in q for k in _CONCERN_KEYWORDS)


def build_concern_instruction(is_concern_focused: bool) -> str:
    """Live-testing bug (2026-07-31): 'what's concerning?' and 'summarize
    status' both fell under the same is_overview bucket, got identical
    records, and a small local model produced near-duplicate answers because
    nothing told it these two asks are different. Fix is additive, not a
    filter — every record still reaches the prompt unchanged; this just
    points the model at the flagged findings that already exist in the
    encoder block instead of leaving it to guess what counts as notable."""
    if not is_concern_focused:
        return ""
    return (
        "\nThe doctor is asking specifically about concerning or abnormal "
        "findings, not a general summary. Lead with only the values listed under "
        "OUT-OF-RANGE AT LATEST READING and the items under DETECTED CONDITIONS "
        "in the encoder analysis above. Trend labels describe the size of a "
        "change, not severity, and a listed condition carries no severity at "
        "all: do not add labels such as CRITICAL or severe that the records do "
        "not state. Do not restate routine or normal results, and say so "
        "explicitly if nothing is flagged as abnormal.\n"
    )


def format_encoder_block(trends: dict, ner: dict, latest: Optional[dict] = None) -> str:
    """Render encoder output as a structured text block for the LLM prompt."""
    lines = ["=== ENCODER ANALYSIS (Python-computed — cite these as facts, not estimates) ==="]

    if trends:
        lines.append("\nLAB TRENDS (first → latest reading; label = size of change, not severity):")
        for name, t in sorted(trends.items(), key=lambda x: -abs(x[1]["pct_change"])):
            status = f" — latest {t['status']}" if t.get("status") else ""
            lines.append(
                f"  [{t['flag']}] {name}: {t['first_val']} → {t['last_val']} "
                f"({t['trend']} {abs(t['pct_change'])}%) "
                f"[{t['dates'][0]} → {t['dates'][1]}]{status}"
            )
    else:
        lines.append("\nLAB TRENDS: insufficient data (need ≥2 readings of the same test)")

    if latest:
        if latest.get("out_of_range"):
            lines.append("\nOUT-OF-RANGE AT LATEST READING:")
            lines.extend(f"  {item}" for item in latest["out_of_range"])
        if latest.get("latest"):
            lines.append("\nLATEST RESULT ON FILE PER TEST (no later result exists — never imply one does):")
            lines.extend(f"  {item}" for item in latest["latest"])

    drugs = ner.get("drugs", [])
    diagnoses = ner.get("diagnoses", [])
    ruled_out = ner.get("ruled_out", [])
    if drugs:
        lines.append(f"\nDETECTED MEDICATIONS: {', '.join(drugs)}")
    if diagnoses:
        lines.append(f"\nDETECTED CONDITIONS: {', '.join(diagnoses)}")
    if ruled_out:
        lines.append(f"\nSTATED AS ABSENT IN THE RECORDS (never report as present): {', '.join(ruled_out)}")

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
                f"— {t['flag']}" + (f", latest {t['status']}" if t.get("status") else ""))
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


# Small local models sometimes recite the prompt around their answer (verified
# live: a general question came back with the patient data block appended) or
# leak their reasoning between reserved tokens (MedGemma 1.5: <unused94>thought
# ... <unused95>). Neither is part of the answer. The patient data block and
# the "===" section markers are removed; anything else the model wrote stays.
_THINKING_RE = re.compile(r"<unused94>.*?<unused95>", re.DOTALL)
_DATA_BLOCK_RE = re.compile(r"=== BEGIN PATIENT DATA.*?(?:=== END PATIENT DATA ===|\Z)", re.DOTALL)
_MARKER_LINE_RE = re.compile(r"^\s*===.*$", re.MULTILINE)


def strip_prompt_echo(text: str) -> str:
    cleaned = _THINKING_RE.sub("", text)
    cleaned = _MARKER_LINE_RE.sub("", _DATA_BLOCK_RE.sub("", cleaned))
    cleaned = re.sub(r"\n{3,}", "\n\n", cleaned).strip()
    return cleaned or "No answer was generated. Please rephrase the question."
