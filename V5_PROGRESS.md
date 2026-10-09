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
| 1. Data and trust | Structured lab values, oncology profile fields, encoder and negation fixes, confidence badge, vendor naming | Done and committed (`55fe9f4`). Live AI re-run after the last fixes deferred until the model decision |
| 2. Chart workspace | New navigation (search in header, chart shell with tabs), pinned banner, lab flowsheet, timeline, loading and error states | Built; tests and build pass; visual click-through pending |
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

## Stage 2 — Chart workspace

### What changed
- `backend/chart.py` (new): builds the timeline, lab flowsheet and out-of-range
  list from gateway records. Pure functions; all numbers come from the encoder.
- `GET /api/chart?term=` (new): profile lookup by ID or name, then all six
  gateways in parallel, then `build_chart`. Any signed-in role may read it.
- Hosted-model quota errors now return HTTP 429 with a plain message instead of
  a generic 500.
- `frontend/src/pages/ChartPage.jsx` (new) at `/chart/:term`: pinned patient
  banner, section navigation (Summary, Timeline, Labs, Imaging, Treatment),
  lab flowsheet with L/H markers and reference ranges, timeline with a source
  system filter, loading skeleton, not-found and service-down states.
- `frontend/src/components/AskPanel.jsx` (new): DocAssist inside the chart,
  scoped to the open patient, with specific messages for a non-physician
  account, quota reached and service unavailable. Opening a chart spends no AI
  request.
- Header: patient search with native autocomplete on every signed-in page.
- Results page: "Open chart view" button. Existing pages are unchanged.

### Checkpoint 2
- [x] `pytest tests`: 155 passed (6 new chart tests on real seed data).
- [x] `CI=true npm run build`: compiled successfully.
- [x] Endpoint called in-process against the local database: P1002, a name
      search, a patient without oncology fields, 404 for no match, 401 without a token.
- [x] Browser check (2026-10-08): signed in as the physician account; header
      search by name opened the chart; banner, Summary and Labs flowsheet render
      for P1002 and P1004. Found and fixed: ECOG 0 showed as "Not recorded".
- [x] The main search page now opens the chart instead of the old results page
      (the old page still exists at `/results`). Build re-run: compiled.
- [ ] Owner click-through of all five sections for the three demo patients.
- Noted: the welcome and search pages still have the V4 look, which is why the
  change was not obvious at first. Restyling them is not yet scheduled.
- [ ] Decide whether sign-in should land on search-then-chart instead of the welcome page.

### Stage 2 redesign after owner review (2026-10-08)
Feedback: the first chart was text-heavy and hard to navigate; the old
two-page flow felt clearer; more charts, boxes and visuals wanted.
Decisions (asked as multiple choice): keep the section tabs and put visuals in
each; clean style with colour for meaning; build all four visuals; DocAssist in
a drawer opened by a button; Summary is a dashboard; findings computed in code
with AI only on request; sign-in lands on a clean search screen; report images
as thumbnails that enlarge.

Built:
- `chart.py`: `build_findings` (out of range with trend, tumor-marker trend,
  treatment modified, current therapy, latest imaging, stated absent) and
  `build_treatments` (category, status, modified flag). No model involved.
- `components/ChartVisuals.jsx` (new): stat boxes, finding cards, lab trend
  charts with a shaded reference range on a shared date axis, all-systems lane
  timeline with selectable points, treatment course steps.
- `ChartPage.jsx` rewritten: dashboard Summary, Labs (small-multiple charts +
  flowsheet), Imaging (thumbnail gallery with enlarge dialog), Treatment,
  Timeline; DocAssist drawer; "Explain with AI" asks one fixed summary question.
- Colours: a colour-blind-safe categorical set (validated with a script) for
  source systems and treatment types; one colour for "outside range" with an
  L/H letter, so low and high are not ranked against each other.
- `SearchPage.jsx`: a rewrite was rejected by the owner the same day and
  reverted. The page is the V4 version again, with one line changed so a search
  opens the chart. Sign-in goes to this page; the welcome page still exists at
  `/welcome`. Rule going forward: existing V4 pages keep their look unless the
  owner asks for a change.

Checks: `pytest tests` 159 passed (4 new for findings/treatments);
`CI=true npm run build` compiled; browser check of Summary stat boxes, tumor
marker chart, Labs charts and flowsheet, Imaging gallery, Timeline lanes and
the search screen for P1004. Not yet seen in the browser: key findings,
treatment course steps and treatment lines on the marker chart (the running
backend predates them and needs a restart), and the DocAssist drawer in use.

### Second visual pass after owner review (2026-10-08, evening)
Feedback: wanted richer, more colourful screens with varied components; text
in the patient header was cut short; no long dashes anywhere; a distinctive
DocAssist entry point; clean at 100% browser zoom. Reference designs supplied
(medical dashboard shots) were reviewed for patterns only: soft tinted
background, raised rounded cards, coloured icon tiles, pill navigation.

Built:
- Patient header is now a gradient card with initials, full-text field tiles
  that wrap (nothing truncated) and an ECOG 0 to 4 scale. The old sticky banner
  is gone; the section navigation and DocAssist card stay in view instead.
- Stat tiles with coloured icon squares; key findings as flip cards (finding
  on the front, its basis on the back); "Latest lab values" range gauges;
  gradient-filled trend charts; treatment course as icon steps on a line;
  raised record cards with a colour bar per source system.
- DocAssist: animated gradient orb mark, a dark promo card in the sidebar, a
  floating button on narrow screens, and a drawer with a gradient header,
  suggestion cards, chat bubbles and a typing indicator.
- `chart.py` `_plain()`: long dashes in displayed record text become a colon
  ("Stable: no new lesions"). Stored records and the old pages are unchanged.
  DocAssist answers shown in the drawer are tidied the same way.
- Layout tuned at a 1024 px wide viewport (the owner's screen at 100% zoom).
- Styles added to `index.css` (orb, flip, raised card, reduced-motion rules).
  No new dependency.

Checks: `pytest tests` 160 passed; `CI=true npm run build` compiled; browser
check at 1024 px of the header, tiles, flip card, marker chart, gauges,
treatment records and the DocAssist drawer for P1001. Long dashes still show
until the backend is restarted with the new code.

### Visits, medications and recent dates (2026-10-08, late)
Owner asked for an appointments view (who the patient saw and when, the
signed-in doctor's own consultations, upcoming appointments) and prescribed
medications. Decisions by multiple choice: all visits with a "My consultations"
toggle; upcoming shown as an estimate from the regimen (the owner chose this
over a new scheduling system; I advised against it, so it is labelled plainly
as an estimate, never as a booked appointment); shift demo timelines to end
near today; leave the header search as is.

Built:
- `data/seed.py`: curated patients' registration dates are moved at seed time
  so each scenario's last record falls 6 days before the seed date (same
  spacing). Generated patients are untouched. Demo patients carry
  `primary_oncologist` ("Dr. Smith", the demo physician account), used as the
  doctor on their treatment records.
- `chart.py`: `build_visits` (records grouped by date with the doctors
  involved), `build_medications` (current from treatment in progress; history
  per drug with last dose, last date, times given), `estimate_upcoming` (next
  doses from a "q3w"-style interval on the treatment in progress; returns a
  note and no dates when there is no interval or no active treatment).
- Chart page: Medications and Visits sections; the patient header collapses to
  the identity row on sections other than Summary.
- Header dropdown separator changed from a long dash to a middle dot.

Checks: `pytest tests` 166 passed (6 new); `CI=true npm run build` compiled;
browser check that the two new sections render. They show empty until the
backend is restarted and local data reseeded (dates and doctor changed).

### One-page chart and resizable assistant (2026-10-09)
Owner preferred the old results page's "everything in one place" with the new
visuals, and wanted the DocAssist drawer to enlarge leftwards.
- Chart sections are stacked on one scrolling page. The left menu scrolls to a
  section and highlights the one in view (IntersectionObserver). Panels that
  would repeat on the same page were removed (lab reports and treatment record
  lists; the treatment course and systems timeline now appear once each).
- DocAssist drawer: drag its left edge, use the widen button, or the arrow keys
  on the handle. Width is kept between 380 px and 1100 px.
- "Next expected doses" shows its start date in a readable form.
- Five richness ideas recorded as stories N-3 to N-7 in the private backlog.

Checks: `pytest tests` 166 passed; `CI=true npm run build` compiled; browser
check at 1024 px: menu click scrolled to Visits and highlighted it, visits and
dose estimates showed live data after the owner's reseed, the drawer widened
to 60% and dragged to 794 px.

### Department names on the chart (2026-10-09)
The chart's source tags used system names (LIS, RIS/PACS, EMR) while the search
page uses department names. Owner chose department names everywhere: tags and
timeline lanes now read MRI Scan, X-Ray, CT Scan, ECG, Blood Test, Treatment
(six lanes, six colours), and "simulated" is stated once per panel instead of
on every tag. `pytest tests` 166 passed; build compiled. Also fixed: long
treatment names overflowing their cards; a clear message when a thumbnail
fails to load.

Review of the one-page chart at 1024 px (owner felt "something is off"):
the page is about 14 screens tall; the patient header fills most of the first
screen; trend charts have only two or three points each so they read as
straight lines; the same lab numbers appear three times (gauges, charts,
flowsheet); flip cards hide their content behind a click. Options put to the
owner; nothing changed yet.

### Five fixes after the page review (2026-10-09)
Owner approved all five options from the review.
- A. Richer lab data: the breast, colorectal and lung scenarios gained
  intermediate blood counts (before each chemotherapy cycle) and tumor-marker
  readings. Only readings between each analyte's existing first and latest
  value were added, so what is out of range today, every trend percentage and
  the AI regression expectations are unchanged. Counts now dip before the
  cycles that were reduced or delayed.
- B. Compact patient header: one card with wrapping fact chips. The first
  findings now sit on the first screen.
- C. Labs de-duplicated: the grid of small charts is replaced by one "Trend
  explorer" (pick an analyte, shown against treatment events); the flowsheet
  gained a sparkline per row. Gauges stay in Summary.
- D. Key findings show title and basis together; the flip interaction and its
  CSS were removed.
- E. Vitals (with body surface area computed by the Mosteller formula), care
  team and a problem list (profile diagnosis plus conditions the records state
  as present). Demo patients only; other patients simply do not show the panel.

Checks: `pytest tests` 167 passed (1 new, 2 updated for the extra readings);
`CI=true npm run build` compiled; browser check at 1024 px of the compact
header, findings, trend explorer and flowsheet sparklines for P1004. Page
height went from about 14 screens to under 13 before the new data. The richer
curves, vitals and care team need a backend restart and local reseed to show.

### Not in this stage
Documents and Brief sections (Stage 3), print view, role-specific views, dark mode.

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
