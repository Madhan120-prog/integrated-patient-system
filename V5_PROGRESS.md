# V5 Progress Log — Chart Workspace, Trusted Brief, Referral Intake

> Branch: `feature/v5-new-version` (local, unpushed). `main` stays frozen as the
> deployed V4. Nothing merges into `main` without explicit written approval.
> Started 2026-10-08. This file is the running record: plan, checkpoints, test
> runs, fixes. Update it at every checkpoint.

## Core idea (must not change)

Federated department systems, each isolated behind its own gateway and reached
through the MPI, with AI capabilities layered on top. V5 adds use cases and a
better workspace on that base. It does not replace the gateways, the MPI, the
encoder-before-LLM rule, additive guardrails, or the audit log.

Rules for every stage:
- Additive changes first. Existing routes, record fields and pages keep working.
- Deterministic facts come from code; the LLM writes prose only.
- Each stage ends with a checkpoint: tests, verification run, fixes, then the next stage.
- No new dependency if an installed one covers it.

## Stages

| Stage | Scope | Status |
|---|---|---|
| 1. Data and trust | Structured lab values, oncology profile fields, encoder and negation fixes, confidence badge, vendor naming | Code done, automated checks pass; live AI run pending |
| 2. Chart workspace | New navigation (search in header, chart shell with tabs), pinned banner, lab flowsheet, timeline, loading and error states | Not started (mockups awaiting approval) |
| 3. Brief | One-click pre-visit brief from deterministic facts with per-line sources, print view, time-saved panel | Not started |
| 4. Referral intake | Upload a referral document, structured fields, missing-documents checklist, human confirmation | Not started |
| 5. Freeze and rehearse | Golden-path script, reset procedure, presentation mode, rehearsals | Not started |

Out of scope for now (planned later): trial matching, edit/approve workflow,
FHIR-shaped source view, role-specific views, dark mode, tablet layout,
retrieval upgrade, HL7/FHIR/DICOM interface layer.

## Findings from verifying the backlog against the code (2026-10-08)

1. `encoder.detect_trends` took the first number in the result text. A result
   like "CA 15-3 mildly elevated (38 U/mL)" was read as 15, giving 0.0% STABLE
   instead of -42.1%. Panel results ("Hgb 10.8" then "WBC 1.8" under one
   "Complete Blood Count") were compared as if they were one analyte. The old
   trend test used a hand-written fixture, so the suite passed anyway.
2. `encoder.extract_ner_signals` ignored negation. "No evidence of distant
   metastasis" produced `DETECTED CONDITIONS: metastasis`. Likely cause of the
   reported false metastasis claim (to confirm in the live AI run).
3. Trend flags named CRITICAL/HIGH described the size of a change, not clinical
   severity, and the concern prompt put them on equal footing with keyword hits.
4. The low-confidence badge fired on any answer under 80 words.
5. Lab results were free text only: no analyte, unit or reference range.
6. Profiles had no diagnosis, stage, performance status, allergies or regimen.
7. `/analyze-document` needs an existing patient and returns prose, so referral
   intake needs its own endpoint (it can reuse the vision call).
8. Audit `model_version` always records the Gemini model name, even on other
   backends. Not fixed yet.

## Stage 1 — Data and trust

### What changed
- `data/scenarios/*.json`: every lab record with numbers now carries `values`
  (`analyte, value, unit, low, high`). The `result` text is unchanged. The three
  demo scenarios (breast, colorectal, lung) carry fuller panels.
- `data/patients.json`: P1001, P1002, P1004 gain `mrn, diagnosis, stage,
  biomarkers, ecog, allergies, regimen`. Other patients are unchanged.
- `data/seed.py`, `data/lab_system.py`, `lab_gateway.py`: pass `values` through
  the lab store (`values_json` column) and the gateway. Old stores without the
  column still read correctly.
- `encoder.py`: trends are computed per analyte from `values`; free text is used
  only when it holds exactly one number. Each trend carries the latest value and
  an in-range/low/high status. Change-size labels replace CRITICAL/HIGH/WATCH.
  Negated findings are excluded from detected conditions and listed as ruled
  out. The prompt block lists the latest result on file per test.
- `guardrails.py`: answer length no longer triggers the low-confidence badge.
- Vendor naming in docs and docstrings made neutral and marked simulated.

### Checkpoint 1
- [x] Unit tests: see "Test runs" below.
- [x] Reseed local data (`clear-data`, then `init-data`).
- [x] Live AI regression run on the Gemini backend: 17/18.
- [x] Fix for the one failure, with tests.
- [ ] Re-run the failed question live once AI quota is available.

### Known limits
- Free-text fallback still groups by test name; two different analytes written
  as single numbers under one panel name would be compared. Seed data no longer
  relies on it.
- Reference ranges are generic adult ranges, not sex- or lab-specific.

## Test runs

| Date | What | Result |
|---|---|---|
| 2026-10-08 | Baseline `pytest tests` before any V5 change | 101 passed |
| 2026-10-08 | After encoder/guardrail change, before test updates | 96 passed, 5 failed: exactly the 5 tests asserting the old behaviour (CRITICAL/HIGH flag names x3, NER dict shape, short answer = low confidence). Updated to the new intended behaviour. |
| 2026-10-08 | Stage 1 complete: `pytest tests` incl. new `test_v5_stage1.py` (20 tests on real seed data) | 121 passed |
| 2026-10-08 | Local reseed (`clear-data`, `init-data`) on the V5 branch | 500 patients, 7,129 records indexed |
| 2026-10-08 | First live AI regression run (Gemini, `tests/ai_regression.py`) | 17/18 passed. All trust cases passed: no false metastasis or recurrence claim, no invented "critical", correct CA 15-3 and CEA trends, no "anemia resolved", greeting leaks nothing. 1 failure: "What is the latest CEA value?" answered "not documented". |
| 2026-10-08 | Fix for that failure: question routing matched no department for tumor-marker names, so no lab data reached the model. Routing moved to `match_departments()` with lab keywords and word-start matching. `pytest tests` | 130 passed. Live re-check of that one question pending (daily AI quota used up). |
| 2026-10-08 | Live AI regression on local `medgemma1.5:4b` (Ollama) | 15/18. All trust cases passed. 3 failures: (1) checker bug: "No intracranial metastases were detected" is a correct answer; (2) real: the model recited the prompt, including the patient profile with address and phone, after a general-knowledge answer; (3) one request timed out at 120 s. Also seen: the "Unverified claim" badge fired on a correctly sourced imaging answer. |
| 2026-10-08 | Fixes: prompt no longer carries address, phone, image URLs or repeated identifiers (profile now carries the oncology fields); recited prompt text is cut from answers; the unverified-claim badge now keys on whether any records were fetched; checker handles negated sentences; script timeout 300 s. 4 new tests. | `pytest tests`: 134 passed (run after the offloaded files were restored and disk space freed). Live re-run on the local model pending. |
| 2026-10-08 | Second live run on `medgemma1.5:4b`, answers read line by line | Script said 13/18, but reading the answers shows more: two in-range values called LOW (ANC 2.3, PLT 164); an invented colonoscopy date and surveillance schedule when no records were fetched; reasoning tokens (`<unused94>…`) leaked into two answers; one answer lost to over-aggressive echo cleanup; two HTTP 503 from Ollama; the dosage badge fired on lab units (g/dL). The trust cases from Stage 1 still held (no false metastasis or recurrence claim). |
| 2026-10-08 | Fixes: `guardrails.check_ranges` (deterministic check of low/high wording against the record's reference range, appended as a warning); reasoning tokens and recited prompt blocks removed without dropping the answer; general-knowledge questions get no patient data; a patient question that matches no department now gets the whole chart; dosage badge ignores lab units; Ollama timeout 240 s; regression checks tightened (leaks, invented findings, false LOW). `pytest tests` | 149 passed. Live re-run pending. |

## Blocker found at checkpoint 1
- Gemini key is free tier: 20 requests/day per model. One regression run or a
  short demo uses it up (the first run did). Needs a paid-tier key (owner decision) before the AI
  run can complete, and before any live demo.
- A quota error (HTTP 429 from the provider) surfaces as a generic 500 and
  "Sorry, I encountered an error". The same generic message appears when a
  non-physician account uses DocAssist (HTTP 403), which is how it was first seen. Stage 2 error states must show a clear
  "AI quota reached" message and keep the rest of the chart usable.

## Environment problem found 2026-10-08
The project lives in a folder that iCloud syncs, and the disk reached 96% full
after a model download. macOS offloaded about 8,700 files of `backend/venv`
and some source files to iCloud; reading them stalls for minutes. This looks
like a code hang but is not one. Until the folder is kept local (or moved out
of the synced folder) and disk space is freed, test runs and server starts
can stall without warning.

## Assessment of the local model (2026-10-08)
`medgemma1.5:4b` runs on the 16 GB development machine with no quota, which
makes it right for development and for the on-premises story. It is not
reliable enough for free-text answers in front of clinicians: it misreads
ranges, invents detail when given no data, and takes roughly 30 s or more per
answer. Consequence for the plan: deterministic output (flowsheet, brief built
from code) carries the demo; free-text Q&A needs either the hosted model on a
paid tier or the guardrails above plus a narrow, rehearsed question list.

## Open items noticed during Stage 1
- Demo timelines are dated 2025 and labs stop months before the last imaging,
  so "since last visit" will look stale. Decide in Stage 3 whether to shift
  registration dates or add recent results.
- The lung scenario pairs a stage III work-up with a regimen normally used for
  stage IV disease. Needs a clinical-coherence review before it is shown.
- Medication detection is a keyword list (now includes 5-FU, leucovorin,
  filgrastim). The brief must read medications from treatment records, not NER.
- Prompts still say "XYZ Hospital".
