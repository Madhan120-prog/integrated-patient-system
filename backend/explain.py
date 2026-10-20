"""V5: one finding explained at four levels (patient, physician, lab scientist, drug developer).

Every level is written from the same fact sheet, built in code from the patient's
records, so the levels cannot contradict each other. After the model writes, every
number in every level is checked against the fact sheet. If the model fails or its
output cannot be read, a saved, pre-checked version is used instead.
"""
import json
import re
from pathlib import Path

SAVED_DIR = Path(__file__).parent / "data" / "explanations"

LEVELS = [
    ("patient", "Patient", "the patient and family"),
    ("physician", "Physician", "the treating physician"),
    ("lab", "Lab scientist", "a pathologist or biochemist"),
    ("drug", "Drug developer", "a drug developer or molecular scientist"),
]

# Facts the four levels need. A patient without them gets no graded explanation.
REQUIRED = ("diagnosis", "stage", "grade", "pathology", "molecular")

_NUMBER = re.compile(r"\d+(?:\.\d+)?")
_OUTLOOK = re.compile(r"\b(survival|life expectancy|months to live|terminal|incurable|cure[ds]?)\b", re.IGNORECASE)


def available(profile: dict | None) -> bool:
    return bool(profile) and all(profile.get(k) for k in REQUIRED)


def build_facts(profile: dict, records: dict) -> list[dict]:
    """The fact sheet: each fact with the system it came from. records maps a
    department name (as the gateways use it) to that department's records."""
    facts = [
        {"label": "Diagnosis", "value": profile["diagnosis"], "source": "Diagnosis on record"},
        {"label": "Stage", "value": profile["stage"], "source": "Diagnosis on record"},
        {"label": "Grade", "value": profile["grade"], "source": "Pathology report"},
        {"label": "Pathology", "value": profile["pathology"], "source": "Pathology report"},
        {"label": "Molecular tests", "value": profile["molecular"], "source": "Molecular pathology report"},
    ]
    for dept, label in (("CT Scan", "CT"), ("MRI", "MRI")):
        for r in sorted(records.get(dept, []), key=lambda r: r.get("test_date", "")):
            facts.append({"label": f"{r['test_name']} ({r.get('test_date', '')})", "value": r["result"], "source": f"{label} system"})
    cea = [(r.get("test_date", ""), v) for r in records.get("Blood Profile", []) for v in r.get("values", []) if v.get("analyte") == "CEA"]
    if cea:
        cea.sort()
        unit, high = cea[0][1].get("unit", ""), cea[0][1].get("high")
        trend = " → ".join(f"{v['value']:g}" for _, v in cea)
        facts.append({"label": "CEA (tumour marker)", "value": f"{trend} {unit}, reference 0 to {high}", "source": "Blood test system"})
    treatments = sorted(records.get("Treatment", []), key=lambda r: r.get("treatment_date", ""))
    chemo = [t for t in treatments if t["treatment_name"].lower().startswith("chemotherapy")]
    if chemo:
        facts.append({"label": "Chemotherapy", "value": f"{len(chemo)} cycles of {chemo[0]['treatment_name'].split('—')[-1].split(' Cycle')[0].strip()}",
                      "source": "Treatment system"})
    for t in treatments:
        if not t["treatment_name"].lower().startswith("chemotherapy"):
            facts.append({"label": t["treatment_name"], "value": t["result"], "source": "Treatment system"})
    if profile.get("regimen"):
        facts.append({"label": "Current regimen", "value": profile["regimen"], "source": "Diagnosis on record"})
    return facts


def prompt(facts: list[dict]) -> str:
    sheet = "\n".join(f"- {f['label']}: {f['value']}" for f in facts)
    return f"""Facts about one patient's tumour, taken from their records:
{sheet}

Explain this one finding at four levels. Use only the facts above for anything about this patient.
Each level is 3 to 5 short sentences. Do not invent numbers, dates or results.

1. "patient": speak to the patient directly as "you". Plain, everyday words, no jargon. Explain what grade 3 means simply.
   Do not discuss survival, life expectancy or cure. End by saying the care team will explain what it means for them.
2. "physician": for the treating physician. Histology, grade, TNM stage, size and spread, biomarkers, treatment so far
   and response, the CEA trend, current therapy.
3. "lab": for a pathologist or biochemist. Morphology and grade, immunohistochemistry, Ki-67, the PD-L1 assay result,
   the sequencing results, and CEA as a serum marker against its reference range.
4. "drug": for a drug developer. Start with one sentence that begins "Patient-specific:" listing this tumour's molecular
   findings. Then general mechanism background (the mutated pathway, how the current therapy in "Current regimen" acts,
   which drug classes target these alterations), with each such sentence starting "Background:". Only state
   well-established science; if you are not sure of something, leave it out.

Reply with JSON only, exactly like this: {{"patient": "...", "physician": "...", "lab": "...", "drug": "..."}}"""


SYSTEM = ("You explain medical findings for different readers. You are precise, you never add facts that are not given, "
          "and you do not diagnose or recommend treatment beyond what the record states.")


def parse(text: str) -> dict | None:
    """The four texts from the model's reply, or None if it cannot be read."""
    match = re.search(r"\{.*\}", text or "", re.DOTALL)
    if not match:
        return None
    try:
        data = json.loads(match.group(0))
    except json.JSONDecodeError:
        return None
    if not all(isinstance(data.get(k), str) and data[k].strip() for k, _, _ in LEVELS):
        return None
    return {k: data[k].strip() for k, _, _ in LEVELS}


def check(level: str, text: str, facts: list[dict]) -> list[str]:
    """Visible notes for anything the reader should verify. Never changes the text."""
    allowed = set(_NUMBER.findall(" ".join(f["value"] + " " + f["label"] for f in facts)))
    notes = []
    unknown = sorted({n for n in _NUMBER.findall(text) if n not in allowed}, key=float)
    if unknown:
        notes.append(f"Contains {'numbers' if len(unknown) > 1 else 'a number'} not in the record ({', '.join(unknown)}). Check before using.")
    if level == "patient" and _OUTLOOK.search(text):
        notes.append("Mentions outlook. The care team should discuss this with the patient directly.")
    return notes


def saved(patient_id: str) -> dict | None:
    path = SAVED_DIR / f"{patient_id}.json"
    return json.loads(path.read_text()) if path.exists() else None


def assemble(texts: dict, facts: list[dict], source: str) -> dict:
    return {
        "levels": [{"id": k, "label": label, "audience": audience, "text": texts[k], "notes": check(k, texts[k], facts)}
                   for k, label, audience in LEVELS],
        "facts": facts,
        "source": source,
    }
