"""
Live AI regression run — asks the running backend real questions about the
three demo patients and checks each answer for required facts and forbidden
claims. Not collected by pytest (it needs a running server and a real model).

    cd backend && source venv/bin/activate
    python tests/ai_regression.py                 # http://localhost:8000
    python tests/ai_regression.py -v              # also print every answer
    BASE_URL=http://localhost:8001 python tests/ai_regression.py

Run it after every change that can alter an AI answer, and before each rehearsal.
Signs its own token with the local SECRET_KEY, so no password is needed.
"""
import json
import os
import re
import sys
import urllib.request
from pathlib import Path

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))
from dotenv import load_dotenv
load_dotenv(ROOT / ".env")
from auth import create_token

BASE_URL = os.environ.get("BASE_URL", "http://localhost:8000")

# Claims the record contradicts, whichever patient is asked about.
CLAIMS_PRESENT = r"(metasta\w+|recurrence) (is|are|was|were|has been) (detected|present|noted|found|seen|identified)"
INVENTED_SEVERITY = r"\b(critical(ly)?|severe(ly)?)\b"
# Never acceptable in any answer: leaked reasoning tokens or recited prompt sections.
LEAKS = [r"<unused\d+>", r"===", r"\(901\) 555", r"poplar ave"]

# (patient, question, must contain [all], must not match [any regex])
CASES = [
    # P1002 — breast: CT says no distant metastasis; the only anemia CBC is the latest CBC.
    ("P1002", "What is concerning for this patient?", ["10.2"], [CLAIMS_PRESENT, INVENTED_SEVERITY, r"anc[^\n]*\blow\b"]),   # ANC 2.3 is in range
    ("P1002", "What changed since the last visit?", [], [r"no anemia", r"anemia (has |is )?(resolved|improved|normali[sz]ed)", CLAIMS_PRESENT]),
    ("P1002", "What is the CA 15-3 trend?", ["38", "22", "42.1"], []),
    ("P1002", "Is there any evidence of metastasis?", [r"\bno\b"], [CLAIMS_PRESENT]),
    ("P1002", "What medications is she on?", ["tamoxifen"], []),
    ("P1002", "Is the latest hemoglobin in range?", ["10.2", r"low|below"], []),
    ("P1002", "hi", [], [r"patricia", r"hgb|hemoglobin", r"ca 15-3"]),
    # P1004 — colorectal: CEA back in range; latest CBC shows neutropenia; no recurrence on CT.
    ("P1004", "What's concerning?", [r"0\.8|1\.8"], [CLAIMS_PRESENT, INVENTED_SEVERITY]),
    ("P1004", "What is the CEA trend?", ["8.2", "2.1", "74.4"], []),
    ("P1004", "Is there any recurrence?", [r"\bno\b"], [CLAIMS_PRESENT, r"colonoscopy", r"every \d+ months"]),   # neither is in the record
    ("P1004", "What changed since the last visit?", [], [r"neutropenia (has |is )?(resolved|recovered)", CLAIMS_PRESENT]),
    ("P1004", "Summarize the blood work.", ["1.8"], [INVENTED_SEVERITY, r"plt[^\n]*\blow\b"]),   # PLT 164 is in range
    # P1001 — lung: CEA down but still above range; brain MRI and abdominal CT clear.
    ("P1001", "What is the CEA trend?", ["12.5", "5.2", "58.4"], []),
    ("P1001", "Are there any brain metastases?", [r"\bno\b"], [CLAIMS_PRESENT]),
    ("P1001", "What's concerning?", [r"0\.9|2\.1"], [CLAIMS_PRESENT, INVENTED_SEVERITY]),
    ("P1001", "What is the current treatment?", ["pembrolizumab"], []),
    ("P1001", "What is neutropenia?", [], [r"james", r"mitchell"]),
    ("P1001", "What is the latest CEA value? Answer in one line.", ["5.2"], [r"low confidence"]),
]


def ask(token: str, patient_id: str, question: str) -> str:
    req = urllib.request.Request(
        f"{BASE_URL}/api/deep-query",
        data=json.dumps({"patient_id": patient_id, "question": question}).encode(),
        headers={"Content-Type": "application/json", "Authorization": f"Bearer {token}"},
    )
    with urllib.request.urlopen(req, timeout=300) as resp:
        return json.load(resp)["answer"]


def _asserted(pattern: str, text: str) -> bool:
    """True if the pattern appears without a negation earlier in the same sentence
    ("No intracranial metastases were detected" is a correct answer, not a claim)."""
    for m in re.finditer(pattern, text):
        sentence_start = max(text.rfind(c, 0, m.start()) for c in ".\n!?") + 1
        if not re.search(r"\b(no|not|without|negative)\b", text[sentence_start:m.start()]):
            return True
    return False


def check(answer: str, must: list, must_not: list) -> list:
    text = answer.lower()
    problems = [f"missing: {m}" for m in must if not re.search(m if "\\" in m or "|" in m else re.escape(m), text)]
    problems += [f"forbidden: {m}" for m in must_not if _asserted(m, text)]
    problems += [f"leak: {m}" for m in LEAKS if re.search(m, text)]
    return problems


def main() -> int:
    verbose = "-v" in sys.argv
    token = create_token("doctor", "PHYSICIAN")
    failed = 0
    for patient_id, question, must, must_not in CASES:
        try:
            answer = ask(token, patient_id, question)
            problems = check(answer, must, must_not)
        except Exception as e:  # server down, 500, timeout — a failed case, not a crash
            answer, problems = "", [f"request failed: {e}"]
        failed += bool(problems)
        print(f"{'FAIL' if problems else 'PASS'}  {patient_id}  {question}", flush=True)
        for p in problems:
            print(f"        {p}")
        if problems or verbose:
            print("        " + answer.replace("\n", "\n        ") + "\n")
    print(f"\n{len(CASES) - failed}/{len(CASES)} passed against {BASE_URL} "
          f"(model backend = whatever LLM_BACKEND that server was started with)")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
