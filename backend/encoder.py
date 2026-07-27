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
