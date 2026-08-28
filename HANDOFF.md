# Project Handoff — Integrated Patient Data Retrieval System

> Originally written 2026-07-27 at the end of V3. **Updated 2026-08-06** after
> V4 shipped and merged to `main`, the git branch history was cleaned up, the
> README was rewritten for a recruiter-facing audience, and a live bug-hunting
> session against the running `main` branch turned up several real, fixed (and
> some still-open) issues. §0 below is new — read it first, it's the most
> recent and most likely to matter for whatever you're picking up next.
>
> Purpose: let a fresh session (new Claude conversation, or you in a month) pick up
> this project with zero prior context. Covers everything — what this is, why it's
> built the way it is, what's done, what broke, what's still open, and exactly
> where to look for more detail on any of it.
>
> This is the top-level entry point. Other docs still exist and are still the
> source of truth for their specific topic — this file tells you which one to
> open next, and gives you enough summary to not need to open all of them just
> to get oriented.

---

## 0. What Happened Since the V3 Handoff (2026-07-27 → 2026-08-06)

Read this section first — everything below it (§1 onward) is the original
V3-era handoff and is still accurate for architecture/background, but doesn't
know about any of this yet.

### 0.1 V4 shipped and merged to `main`

`feature/v4-ai-capabilities` added three real capabilities on top of V3's
hardened base, then merged cleanly into `main` (zero conflicts, verified via
`git merge-tree` before merging). Full detail in `V4_PROGRESS.md` — condensed
here:

1. **Real RAG** — `backend/rag.py`, sentence-transformers + Chroma, one
   collection scoped per patient. Replaces the old "keyword-gated context
   injection" described in §3.5 below as the *fallback* path: keyword
   matching still runs first and wins when it hits (cheap, exact); RAG only
   kicks in when keyword matching finds nothing, closing the synonym gap
   ("blood cell count" now matches even though it's not a literal `wbc`
   keyword). Patient-ID filtering happens *inside* the Chroma query, not as a
   post-filter — deliberate, since trusting similarity alone to keep patients
   separate would be a real cross-patient PHI leak, not cosmetic. §3.5 below
   is now the "before" picture; this is the "after."
2. **MedGemma vision adapter** — local, Ollama-served vision model
   (`medgemma`) for image analysis in `/analyze-document`, alongside the
   existing Gemini vision path (Gemini still handles PDFs — Ollama vision
   models here take images only).
3. **Multi-agent orchestration** — `backend/multi_agent.py`, hand-rolled (not
   LangGraph — deferred). Compound questions naming 2+ specific departments
   get split into one specialist call per department plus a synthesis pass;
   single-department and overview questions still go through the original
   single-agent path unchanged.
4. A real bug fixed live during V4 testing: **concern-focused questions
   producing near-duplicate answers** — "what's concerning?" and "summarize
   status" both fell into the same "overview" bucket and fetched identical
   records, so a small local model produced near-identical prose for both.
   Fixed additively in `encoder.py` (`is_concern_focused_question()` /
   `build_concern_instruction()`) — every record still reaches the prompt
   unchanged, this only tells the model which flagged items to lead with when
   the question is specifically about problems, not a general summary.

Production deployment path (on-prem GPU serving, cloud BAA options) was
researched (`project_knowledge.md` §14–16) but not implemented — infra work,
intentionally out of scope for this demo.

### 0.2 Git history cleanup and the new branch workflow

The branch chain had grown to `main → v2-department-integration →
ai-capabilities-v2 → v3-security-ai-pipeline → v4-ai-capabilities`, stacked
and never merged. Resolved by:

- Verifying zero conflicts (`git merge-tree`) and fast-forward-merging V4 into
  `main`.
- Renaming every branch to a consistent `feature/v<N>-<name>` notation
  (content/hashes unchanged — `git branch -m` + push new name + delete old
  remote name is a pure relabel, not a rewrite).
- Stripping the `Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>`
  trailer from the 5 commits made during that session (`git filter-branch
  --msg-filter`, content unchanged) — 2 older pre-session commits and 8 more
  scattered across other branches (see §0.6) were **not** touched.

**Standing rules that came out of this, apply to every future session:**
- **Every commit goes out under the user's own git identity** (`Madhan Kumar
  Tammineni <madhant120@gmail.com>`) — never a Claude co-author trailer,
  regardless of how much of the diff Claude authored. Confirmed explicitly:
  *"remember every time, do it from my git account not from claude."*
- **Version branches (`feature/v1-...` through `feature/v4-...`) are
  permanent historical records — never delete them**, even after merging to
  `main`. Explicit user correction: *"why deleting the version branches, i
  dont want them delete because i wanna see what work i have done, so they
  would be like records, right?"*
- **New workflow going forward:** every new feature branches from current
  `main`, gets merged back when done, old branches stay frozen forever as
  records. Consistent naming: `feature/v<N>-<short-name>`.
- Current branches (as of 2026-08-06): `feature/v1-deep-search`,
  `feature/v1-demo-data-with-APIKEY`, `feature/v2-department-integration`,
  `feature/v2-ai-capabilities`, `feature/v3-security-ai-pipeline`,
  `feature/v4-ai-capabilities`, `main` (all merged into main, all preserved).
  A `wip/deep-search-alt-flow` branch also exists on the remote, untouched.
- A separate worktree (`integrated-patient-system-v3/`, checked out on
  `feature/v3-security-ai-pipeline`) still exists on disk alongside the main
  working directory — it's a legitimate leftover from V3 testing, not a
  conflict. **The actual running backend/frontend (ports 8000/3000) run from
  the main working directory (`integrated-patient-system/`), not the
  worktree** — verified via `lsof` + checking each process's cwd. If a
  terminal's shell prompt shows the `-v3` worktree path, that only means the
  shell's `cwd` is there, not that any running server is.

### 0.3 README.md — full recruiter-facing rewrite

`README.md` was completely rewritten: no hospital naming anywhere (title,
badges, architecture diagram, tech table), Mermaid diagrams for the
"why this exists" pitch and the full architecture, a "See it in action" table
with 3 real screenshots (`docs/screenshots/`) captured live via a Playwright
script (login → dashboard → patient search → DocAssist chat, driven against
the actual running app, not mocked), an honest "Built the hard way — real
bugs, found live and fixed" section drawn from the real V3/V4 bug list, an
explicit "Security & compliance posture" section that states the BAA gap
plainly rather than glossing over it, and a "what's actually left before this
could touch real patients" section. Merged cleanly with one manual
GitHub-side title edit the user made concurrently (`2f1206d`) — resolved in
favor of the full rewrite's title.

**Also discovered and fixed while taking screenshots:** the live app itself
still said "XYZ Hospital" in three places despite the README no longer naming
a hospital — `frontend/src/components/Header.jsx`, `frontend/src/pages/LoginPage.jsx`,
and `frontend/public/index.html` (page title + meta description). All three
changed to generic "Patient Records System" branding. Screenshots were
recaptured after this fix.

### 0.4 Live bug-hunting session against running `main` (2026-08-06)

The user ran the app in their own terminal (standing preference — see §16)
and reported issues found by actually using it. Findings, in the order they
came up:

**Fixed — pie chart label overlap.** `/analytics?patient_id=P1004`'s
"Treatment Progress" donut chart showed overlapping/garbled text
("Completed: 100%" colliding with "In Progress: 0%"). Root cause:
Recharts renders a label for every slice regardless of size, and a 0%-value
slice has zero angular width, so its label point coincides exactly with the
100% slice's boundary. Fixed in
`frontend/src/pages/AnalyticsPageWithCharts.jsx` (the `label={...}` prop on
the `<Pie>`) by suppressing the label when `percent === 0`. Verified live in
the browser — clean single label, no collision.

**Investigated, not reproduced — MRI department page stuck loading.**
User reported `/department/mri` hanging indefinitely on "Loading profile
records...". Direct backend curl (with a valid JWT) returned 200 OK in
0.097s with a valid 196KB payload; a live browser reproduction (fresh login →
direct navigation to `/department/mri`) loaded successfully (547 records,
fully populated table). Leading theory, not confirmed: a transient hiccup
from `uvicorn --reload` cycling mid-request during one of this session's many
backend restarts — no code change made, since the bug didn't reproduce and
the frontend fetch logic (`DepartmentView.jsx`) already clears its loading
state in a `finally` block regardless of success/failure. **If this recurs,
it needs a fresh live repro, not a code fix from this description alone.**

**Answered directly (not a bug):** *"What model are we using?"* — Ollama,
locally: `llama3.2` for text, `medgemma` for vision (`LLM_BACKEND=ollama` in
`backend/.env`). Verified `ollama serve` was actually running (not just
configured) via `ps aux` + `curl localhost:11434/api/tags` — it had been up
since Friday 1PM as a long-lived background process with both models already
pulled, so nothing needed to be started for it to work. *"How does RAG work
now?"* — see §0.1 item 1 above (real Chroma-backed RAG, V4's addition,
replacing the old keyword-only approach).

**Found and fixed — proactive-check race condition mislabeled as a bad AI
answer.** User reported: typing "Hi" as the first message to DocAssist
produced a "CRITICAL — Anemia" clinical dump instead of a greeting reply.
Root cause, confirmed by reproducing live and inspecting both network
requests: `DeepSearchModal.jsx`'s `runProactiveCheck()` (a real, intentional
feature — silently asks "what's concerning?" the moment a consultation
starts, so abnormal findings surface without the doctor asking) races against
whatever the doctor types first. The backend's greeting detection
(`is_greeting_message()` in `server.py`) was working correctly the whole
time — its actual reply to "Hi" was a plain, data-free "Everything's going
well here." / "How's your shift going so far?" — it just landed in the chat
log *after* the unlabeled proactive alert, visually reading as if "Hi" had
triggered the clinical dump. **Fix:** tagged the proactive message with
`proactive: true` and render a `⚡ Automatic check — not a reply to your
message` label above it (`DeepSearchModal.jsx`, both the `runProactiveCheck`
message-push and the message-rendering JSX). Verified live — the label now
appears correctly regardless of race timing, and "Hi" gets its own correct,
clearly separate reply.

**Deep-dive analysis of a real DocAssist conversation (patient P1002,
Patricia Williams) — one bug found and fixed above, two more identified,
not yet fixed:**
1. *(the proactive-check race, fixed above)*
2. **Still open — a genuine hallucination.** Asked "what changed since last
   visit," the model said "her latest CBC result shows no anemia," directly
   reversing the actual timeline (verified against real data via the API:
   the *only* anemia-related CBC on file is the most recent one, `2025-06-09,
   Hgb 10.2`; there is no later CBC). This told a doctor a finding had
   resolved when the record shows no such thing. **Not fixed** — needs a
   real fix in how "what changed" / comparison-style answers are generated,
   likely in `multi_agent.py` or the relevant prompt-construction code in
   `server.py`.
3. **Still open — misleading "CRITICAL" label.** The same conversation
   labeled a finding explicitly described as "mild" (`Hgb 10.2`) as
   "CRITICAL." Root cause identified precisely: `encoder.py`'s `CRITICAL`
   flag (line ~51) is a *numeric trend magnitude* indicator (≥50% change
   between two readings) — nothing to do with clinical severity — but there
   was only one numeric CBC reading for this patient, so no trend could be
   computed. "Anemia" only reached the model via free-text keyword
   extraction into `DETECTED CONDITIONS` (`extract_ner_signals()`), which
   carries zero severity metadata. The prompt instruction in
   `build_concern_instruction()` (`encoder.py` ~132-134) tells the model to
   "lead with items flagged CRITICAL or HIGH... or listed under DETECTED
   CONDITIONS" — phrasing that puts an unranked keyword list on equal footing
   with a real computed severity flag, so the model invents its own
   "CRITICAL" header for something its own bullet calls "mild." **Not
   fixed** — needs `build_concern_instruction()` reworded so DETECTED
   CONDITIONS items are never implied to carry CRITICAL/HIGH severity.
4. **Still open — guardrail miscalibration.** The "⚠ Low confidence" badge
   fires on any response under 80 words (`guardrails.py`, `_SHORT_RESPONSE_WORDS
   = 80`), independent of actual correctness or grounding — this is the same
   issue flagged in the original V3 handoff §8.6 ("alert fatigue"), confirmed
   still present and reproduced live: it fired on a correct, concise,
   explicitly bullet-point-requested answer just as readily as on a vague
   one. **Not fixed** — length is the wrong proxy; needs either a higher
   threshold, a different signal entirely, or removal of brevity as a trigger.
5. **Flagged, not yet investigated at all.** The same proactive-check
   feature (once fixed to be correctly labeled, see above) produced, on a
   separate run: *"Metastasis is detected, as indicated by post-surgical
   findings from MRI records."* The actual MRI record for this patient says
   "Post-surgical — clean margins, **no residual tumor**" — the opposite
   claim. This is a false-positive hallucination in a proactive safety
   feature, which is a worse place for a hallucination to live than in a
   direct Q&A the doctor can push back on. **Not investigated — highest
   priority open item, see §0.5.**

### 0.5 GitHub Contributors graph — investigated, deliberately left alone

User asked to make the repo's GitHub "Contributors" list show only themselves
and Claude (currently shows 4: `emergent-agent-e1`, `Madhan120-prog`/Madhan,
`claude`, `maparna16`). Investigated properly rather than guessed:

- `git log --all --format='%an <%ae>'` shows **93 commits** authored by
  `emergent-agent-e1 <github@emergent.sh>` (almost certainly an earlier
  AI app-builder tool used before this project moved to Claude Code), **42**
  by Madhan, **1** by `maparna16 <makkenaaparna99@gmail.com>` (confirmed by
  the user to also be them, a different account/machine), **1** by
  `Madhan120-prog` (same person, GitHub-web-UI commit), and **8** commits
  elsewhere in history still carrying a `Co-Authored-By: Claude Sonnet 5`
  trailer (outside the range cleaned in §0.2) — that trailer is why `claude`
  shows up at all.
- GitHub's Contributors graph is computed from the **default branch's**
  commit history, live — there's no per-contributor "hide" setting.
  Reattributing either unwanted identity requires an actual history rewrite
  (changing that commit's author and force-pushing everything downstream).
- Checked the actual blast radius before proposing anything: both
  `emergent-agent-e1`'s commits and `maparna16`'s single commit sit very
  early in shared history and are reachable from **every** branch
  (v1 through v4) — reattributing either would cascade through 80+ downstream
  commits and require rewriting/force-pushing every branch, not a contained
  change.
- **Decision: left as-is, nothing rewritten.** A lower-blast-radius
  alternative was discussed and explicitly **not** pursued — squashing just
  `main`'s history into a handful of milestone commits (backed up under
  `archive/main-full-history` first) while leaving v1-v4 branches completely
  untouched. Talked through honestly and rejected for real reasons: a
  thin/squashed main can look *more* suspicious to a technical reviewer than
  reassuring, it doesn't survive real scrutiny since the full history is
  still one click away on the archive branch, it hurts the GitHub profile
  activity heatmap, and it complicates merging future work back into main
  (orphan history, no shared ancestor with the version branches). **If this
  comes up again, that reasoning is the reason it wasn't done — don't
  re-propose it without something changing.**

### 0.6 Open items carried forward from this session (priority order)

1. **Metastasis false-positive hallucination** (§0.4 item 5) — not yet
   investigated. Highest priority: a proactive, unprompted safety feature
   asserting a serious finding the record contradicts is worse than a
   regular wrong answer.
2. **"What changed" temporal-reversal hallucination** (§0.4 item 2) — needs a
   real fix, not just a flag.
3. **CRITICAL-label conflation with DETECTED CONDITIONS** (§0.4 item 3) —
   concrete, localized fix identified in `encoder.py`, not yet applied.
4. **80-word confidence-badge miscalibration** (§0.4 item 4 / original §8.6)
   — long-standing, still open, needs a real signal to replace word-count.
5. **V5 planning** — user wants to build V5 (including UI work) with
   accumulating sub-features (5.1, 5.2, ...) and **no merge to `main` until
   rigorous testing and satisfaction**. Chosen approach: a **completely
   separate, disposable repo** for V5 experimentation (not a branch in this
   repo) — reasoning: fully reconcilable back into this repo later, or fully
   discardable if unsatisfied, without the branch-juggling confusion this
   session spent a lot of time untangling. **Not started yet** — no repo
   created, no code written.
6. Everything in the original §10 (below) that's still unaddressed: VLM/vision
   in-app end-to-end retest, structured JSON output, prompt-injection
   sanitization for record free-text, Azure path untested.

---

---

## 1. What This Project Is

A cancer hospital in Memphis, US ("West Cancer Center" in the demo branding) runs
six separate department systems that don't share data: an EMR for treatment
(like Epic/Cerner), a radiology PACS for imaging (like GE PACS), an ECG system
(like MUSE), and a lab system (like Sunquest/PathNet). This project simulates
that reality and builds an integration layer on top of it:

- **One patient ID retrieves the full medical history across all 6 departments**,
  even though each department genuinely doesn't know the others exist.
- **DocAssist** — an AI clinical assistant that reasons across the combined data,
  answers natural-language questions, flags abnormalities, and shows its sources.
- **V3 (current branch)** adds the security/compliance layer a real hospital would
  require before this could touch a real patient: auth, audit logging, a
  swappable/local LLM backend, deterministic fact-checking, and safety guardrails.

This is a portfolio/learning project, not a deployed clinical system. Nothing
here should be mistaken for HIPAA-certified or production-ready — see §7 for
exactly what gap exists between "this demo" and "a real compliant system."

---

## 2. Tech Stack

| Layer | Technology |
|---|---|
| Backend | FastAPI + Motor (async MongoDB driver) |
| Frontend | React (CRA/craco) + Tailwind + shadcn/ui + Recharts |
| Central DB | MongoDB 7.0 — holds only `profiles` + `mpi` collections |
| Dept systems | SQLite, JSON files, dbm, shelve, CSV, JSON (was pickle) — one per department, deliberately different tech per department |
| LLM (cloud) | Google Gemini `gemini-3-flash-preview` |
| LLM (local) | Ollama — tested with `llama3.2` (3B) |
| LLM (enterprise, unused) | Azure OpenAI — coded, never tested (no key configured) |
| Voice output | gTTS (server-side MP3 generation, no browser TTS dependency) |
| Auth | JWT (`python-jose`), `OAuth2PasswordBearer` |

---

## 3. Architecture

### 3.1 The federated pattern (the core idea of this whole project)

```
Doctor enters patient ID
        ↓
   MPI (MongoDB "mpi" collection)
   maps canonical patient_id → each vendor's own local ID
        ↓
┌──────────────────────────────────────────────────────┐
│  Labs        │ SQLite       │ Sunquest simulation     │
│  MRI         │ JSON files   │ RIS simulation          │
│  X-Ray       │ dbm          │ PACS key-value          │
│  CT Scan     │ shelve       │ Object store simulation │
│  ECG         │ CSV          │ MUSE flat-file          │
│  Treatment   │ JSON (was pickle) │ Epic simulation    │
└──────────────────────────────────────────────────────┘
        ↓
   Normalized records → LLM (Gemini/Ollama/Azure) → DocAssist answer
```

**The rule that makes this real integration work, not a toy:** `server.py` never
queries a department's storage directly. Every read goes through that
department's **gateway module** (`lab_gateway.py`, `mri_gateway.py`, etc.), which
does: MPI lookup → translate to that vendor's local ID → query the vendor
system → normalize the result into a shared record shape. No vendor system
knows any other vendor system exists, and none of them know the canonical
`patient_id` — only the MPI does.

**Why deliberately different storage tech per department** (not 6× the same
database): real hospital vendors genuinely use incompatible technology, and
the normalization step — mapping 6 different field-naming/storage conventions
into one shared shape — is where real integration engineering work actually
lives. See `V2_PROGRESS.md` §"Are these all real databases?" for a detailed
breakdown of which of the 6 are genuine database engines (SQLite, dbm, shelve)
vs. file-drop-style exports (JSON, CSV) — both patterns exist in real hospitals.

### 3.2 Gateway contract

Every gateway exports the same two functions:

```python
def get_records_for_patient(db, patient_id: str) -> list[dict]:
    # MPI lookup via db (Motor/MongoDB) → query vendor system → normalize

def get_all_records(db) -> list[dict]:
    # department-wide view; reverse-maps every vendor local ID back to
    # canonical patient_id via the MPI
```

Every record has at minimum: `patient_id, name, test_name, test_date, result,
doctor, report_image`. Treatment records use a different shape —
`treatment_name, treatment_date, medicines` — no `test_name`/`report_image`.
**This shape difference is exactly what caused a real bug in V3, see §8.4.**

### 3.3 MPI (Master Patient Index)

MongoDB collection `mpi`, one document per patient:
```json
{
  "patient_id": "P1001",
  "sunquest_lab_id": "SQ-90000",
  "ris_mri_id": "RIS-100000",
  "xray_local_id": "XR-200000",
  "ct_local_id": "CT-300000",
  "ecg_local_id": "ECG-400000",
  "treatment_local_id": "TX-500000"
}
```
This is the industry-standard pattern real EHR integrations use (Epic has one;
IHE PIX/PDQ is the standard protocol for it). It's exact 1:1 matching here — no
fuzzy/probabilistic patient matching, explicitly out of scope.

### 3.4 Smart context routing (token/cost efficiency)

Before any department is queried, a keyword classifier runs against the
doctor's **new question only** (never conversation history — see §8.2 for why
that separation matters). Overview keywords (`summarize`, `status`, `trend`,
etc.) fetch all 6 departments. Single-topic keywords (`mri`, `wbc`, `blood`)
fetch only the matching department. Greetings and general medical-knowledge
questions fetch **zero** departments — the LLM never even sees patient data for
those, by design (though see §8.2 for where this broke in practice).

### 3.5 What "RAG" means in this project (important — it's not what the name usually implies)

This system does **keyword-gated context injection**, not vector/embedding RAG:
1. Classify question → pick departments (keyword match, no embeddings)
2. Fetch raw records from those departments
3. Serialize to text, inject into the prompt
4. LLM answers using both its own training knowledge and the injected text

No embeddings, no vector DB, no chunk-level retrieval. Works when questions
have clear keywords; fails silently on medical synonyms ("blood cell count"
won't match the `wbc` keyword). See `project_knowledge.md` §3 for the true-RAG
upgrade path (SentenceTransformer + Chroma, CPU-only, no hosted service needed)
if this ever needs to scale past a demo.

---

## 4. Repository Structure

```
integrated-patient-system/
├── README.md                    # Quick-start setup guide
├── RULES.md                     # Standing conventions — read before writing code
├── plan.md                      # Full project roadmap, phase by phase
├── project_knowledge.md         # Security/compliance/architecture deep-dive (pre-V3)
├── V2_PROGRESS.md               # Federated-architecture build log (department isolation)
├── V3_PROGRESS.md               # Security/AI-pipeline build log — THE most detailed V3 doc
├── HANDOFF.md                   # This file
├── docker-compose.yml           # Optional Mongo-via-Docker
│
├── backend/
│   ├── server.py                 # All API routes + prompt construction + LLM call
│   ├── auth.py                   # JWT create/verify, RBAC dependencies, USERS dict
│   ├── encoder.py                # Deterministic trend detection + NER + tool-calling protocol + concern-focus instruction (V4)
│   ├── guardrails.py              # 4 additive safety checks on every LLM response
│   ├── rag.py                     # V4 — sentence-transformers + Chroma, per-patient-scoped semantic search (fallback when keyword routing finds nothing)
│   ├── multi_agent.py             # V4 — one specialist call per department + synthesis, for compound multi-department questions
│   ├── lab_gateway.py            # Labs: MPI lookup → SQLite
│   ├── mri_gateway.py            # MRI: MPI lookup → JSON files
│   ├── xray_gateway.py           # X-Ray: MPI lookup → dbm
│   ├── ct_gateway.py             # CT Scan: MPI lookup → shelve
│   ├── ecg_gateway.py            # ECG: MPI lookup → CSV
│   ├── treatment_gateway.py      # Treatment: MPI lookup → JSON (was pickle)
│   ├── requirements.txt
│   ├── .env                      # NOT committed — Gemini key, SECRET_KEY, LLM_BACKEND
│   ├── .env.example              # Template — copy this to .env
│   ├── README.md                 # Backend architecture reference (partially stale — see §11)
│   ├── data/
│   │   ├── seed.py               # Generates all 6 vendor stores + MPI + profiles
│   │   ├── lab_system.py         # SQLite vendor (sunquest.db)
│   │   ├── mri_system.py         # JSON file vendor (mri_store/)
│   │   ├── xray_system.py        # dbm.dumb vendor (xray_store)
│   │   ├── ct_system.py          # shelve vendor (ct_store)
│   │   ├── ecg_system.py         # CSV vendor (ecg_store.csv)
│   │   ├── treatment_system.py   # JSON vendor (treatment_store.json) — was pickle, V3 fix
│   │   ├── patients.json         # 12 curated oncology patient profiles
│   │   ├── scenarios/*.json      # Per-cancer-type medical timelines (9 templates)
│   │   └── medical_images.json   # Verified real image URLs by test type
│   ├── uploads/                  # Runtime uploads for /analyze-document
│   └── tests/
│       ├── test_v3_tasks_1_to_3.py   # pickle→JSON, JWT/RBAC, audit log (7 tests)
│       ├── test_v3_tasks_4_5.py      # LLM_BACKEND routing, Ollama adapter (5 tests)
│       ├── test_v3_task_6.py         # Encoder: trends + NER (13 tests)
│       ├── test_v3_task_7.py         # Guardrails: all 4 checks (14 tests)
│       └── test_v3_task_9.py         # Tool-calling protocol (11 tests)
│           # 50 tests total, all passing as of this doc
│
├── frontend/
│   ├── src/
│   │   ├── App.js                # Axios auth header setup, 401 interceptor, routes
│   │   ├── pages/
│   │   │   ├── LoginPage.jsx      # Stores JWT on login
│   │   │   ├── SearchPage.jsx     # Patient search by ID/name
│   │   │   ├── ResultsPage.jsx / ResultsPageDepartments.jsx
│   │   │   ├── DepartmentView.jsx # Single-department record listing
│   │   │   ├── AnalyticsPage.jsx / AnalyticsPageWithCharts.jsx
│   │   │   └── WelcomePage.jsx
│   │   ├── components/
│   │   │   ├── Header.jsx         # Logout clears JWT
│   │   │   ├── ProtectedRoute.jsx # Route guard, redirects if no token
│   │   │   ├── DeepSearchModal.jsx # The DocAssist chat UI
│   │   │   └── ui/                # shadcn/ui component library (unmodified)
│   │   └── hooks/, lib/
│   └── .env                       # REACT_APP_BACKEND_URL
│
└── tests/                        # Older pre-V3 integration test (test_docassist_api.py)
```

---

## 5. Branch History — How We Got Here

**Updated 2026-08-06 — this section described a mid-flight state; it's since
been resolved. See §0.2 for the full story.** As of now: `feature/v4-ai-capabilities`
has been merged into `main` (zero conflicts), every branch has been renamed to
a consistent `feature/v<N>-<name>` notation, and `main` is the actively
maintained trunk going forward. Nothing was deleted — every version branch
below still exists, frozen, as a historical record:

```
main  ← now includes everything through V4, actively maintained trunk
  ├── feature/v1-deep-search              ← preserved record, not deleted
  ├── feature/v1-demo-data-with-APIKEY    ← preserved record, not deleted
  ├── feature/v2-department-integration   ← V2: 6-dept federated architecture
  ├── feature/v2-ai-capabilities          ← DocAssist AI improvements
  ├── feature/v3-security-ai-pipeline     ← V3: security + AI pipeline
  └── feature/v4-ai-capabilities          ← V4: RAG + multi-agent + vision (merged to main)
```

Each branch is **independently runnable/demoable** — you can check out any of
them and the app works end-to-end at that stage of maturity. This was a
deliberate choice so progress could be shown incrementally. **New workflow
going forward:** branch from `main` for new work, merge back to `main` when
done, never delete the old branch.

### Commit timeline (chronological, oldest → newest)

1. `497f097` — Baseline: backend + frontend running locally with auth and search
2. `a51eeb7` → `d8f58bb` — Removed Emergent.sh dependency, migrated to Gemini, added curated oncology patient data (12 scenarios)
3. `7e2a7f9` — DocAssist improvements: server-side voice (gTTS), doctor-friendly tone, smart context routing
4. `23f39e8` → `5178663` — **V2**: scaled to 500 patients, piloted federated architecture on labs (SQLite), then MRI (JSON files), then isolated the remaining 4 departments (dbm, shelve, CSV, pickle)
5. `16ad438` → `4766767` — Documented storage tech honesty (real DBs vs file dumps), added proactive flagging + trend callouts + evidence cards
6. `fa90cdd` — Added `project_knowledge.md` (security/compliance/architecture research)
7. `21359b2` — V3 design locked, documented before implementation
8. `1e8d181` → `efa77ab` — **V3 tasks 1–9** (full breakdown in §8 below)

Full detail on any phase: `plan.md` (roadmap with checkboxes), `V2_PROGRESS.md`
(federated architecture build log), `V3_PROGRESS.md` (security/AI pipeline
build log — the single most detailed doc in this repo).

---

## 6. V2 Recap — Federated Department Isolation

**Why it exists:** the pre-V2 system was one shared MongoDB with 6 collections
— unrealistic. Real hospital departments run on different vendors' systems and
never query each other's databases directly.

**What changed:** each of the 6 departments became a fully isolated simulated
vendor system on its own storage technology (see §3.1 table), reachable only
through the MPI + a gateway module. Verified end-to-end after full 500-patient
reseed: zero orphaned records in any department, all search/analytics/AI-chat
paths working through the gateway layer.

**A real bug caught here** (documented in `V2_PROGRESS.md`): `ct_system.py`'s
existence check guessed `shelve`'s output file extension, but `shelve` on this
machine writes a single extensionless file — the check silently failed and
`query_all()` always returned empty even though seeding worked. Fixed by using
`glob.glob(path + "*")` instead of guessing extensions. Caught because every
vendor module gets an isolated offline correctness check before being wired
into the live app.

---

## 7. V3 — Security, AI Pipeline & Local Model

Full task-by-task detail lives in `V3_PROGRESS.md` — this section is the
condensed version plus what happened in **live testing today** that
`V3_PROGRESS.md` also now documents but is worth calling out clearly here.

### 7.1 Why V3 exists

V2 proved the federated architecture works. It had zero security: any process
on the network could call `/deep-query` with any patient ID, nothing was
logged, every query sent PHI to Google's Gemini API with no BAA, the system
was locked to one LLM vendor, and the LLM could hallucinate with nothing
catching it.

### 7.2 The 9 V3 tasks, in build order

| # | Task | What it does |
|---|---|---|
| 1 | Pickle → JSON | `treatment_system.py` — eliminated arbitrary-code-execution risk from deserializing untrusted pickle data |
| 2 | JWT auth + RBAC | 3 roles: `PHYSICIAN` (full access), `NURSE` (read-only, no AI), `ADMIN` (user mgmt only, no patient data) |
| 3 | Audit log | MongoDB `audit_log`, append-only, one entry per AI query — HIPAA §164.312(b) |
| 4 | `LLM_BACKEND` routing | env var switches between `gemini`/`ollama`/`azure`, one `generate_response()` interface for all three |
| 5 | Ollama local path | HTTP call to `localhost:11434/api/chat`, OpenAI-compatible schema — PHI never leaves the machine |
| 6 | Encoder layer | Pure-Python lab trend detector + regex-based drug/diagnosis NER — deterministic, not an LLM task |
| 7 | Guardrails | 4 additive checks appended to every LLM response (see §7.4) |
| 8 | Rate limiting | 60/min per-user (JWT-keyed, not IP) on `/deep-query` and `/analyze-document` |
| 9 | Tool-calling protocol | Provider-agnostic `TOOL_CALL:` text protocol so the LLM requests exact encoder facts instead of restating them from memory — added after live testing exposed hallucination (§8) |

### 7.3 Auth model

```python
USERS = {
    "doctor": {"password": "doctor123", "role": "PHYSICIAN"},
    "nurse":  {"password": "nurse123",  "role": "NURSE"},
    "admin":  {"password": "admin123",  "role": "ADMIN"},
}
```
JWT signed with `SECRET_KEY` (`.env`), 8-hour expiry. `/deep-query` and
`/analyze-document` require `PHYSICIAN`. `/init-data` and `/clear-data` require
`ADMIN`. Every other route requires any valid token (`get_current_user`).

**Why JWT over sessions:** stateless — no session table, no server-side state
to replicate. Token is self-contained `{user_id, role, exp}`, signature
verified in O(1), no DB lookup per request.

### 7.4 The 4 guardrails (`guardrails.py`)

All are **additive only** — they append a warning, never remove or alter the
LLM's actual answer:

1. **Confidence gate** — fires if response is under 80 words OR contains one of
   14 hedge phrases ("I'm not sure", "unclear", "it may be", etc.)
2. **Drug dosage flag** — fires on any dosage pattern (`75mg`, `1.5 g`, `80mg/m²`, etc.)
3. **Citation check** — fires if the response cites a specific lab value/date but
   the encoder had no trend data available to cross-reference
4. **Diagnosis check** *(added in live-testing fixup, §8.1)* — fires on active
   diagnostic language ("most likely diagnosis is X", "the diagnosis is X") —
   does NOT fire on passive citation of an already-recorded diagnosis

### 7.5 The encoder layer (`encoder.py`)

**Trend detector** — groups records by `test_name`, sorts by date, computes
direction (↑/↓/→) and % change between first and last reading. Flags:
`CRITICAL` (≥50% change) / `HIGH` (≥20%) / `WATCH` (≥5%) / `STABLE`. Skips
tests with only 1 reading (no trend possible). Pure arithmetic, zero ML.

**NER extractor** — regex-based, word-boundary matched, case-insensitive.
Scans `result`, `notes`, `medication`, `medicines`, `treatment_name`,
`diagnosis` fields (the last two added after the live-test bug, §8.4) against
a curated list of 31 oncology drugs and 20 diagnosis terms.

**Why deterministic, not LLM-based:** LLMs hallucinate numbers. A trend Python
computes is provably correct. Originally the plan was "inject this as text
context and trust the LLM to cite it faithfully" — live testing proved that
assumption wrong (§8.3), which is why task 9 (tool-calling) exists.

### 7.6 Tool-calling protocol (task 9 — the newest piece)

Instead of trusting the LLM to restate encoder-computed facts from memory, the
system prompt gives it two callable tools:
- `get_lab_trend("test name")` — returns the exact Python-computed trend string
- `get_medications()` — returns the exact NER-detected drug list

The LLM signals a request with a plain-text marker:
```
TOOL_CALL: get_lab_trend("CA 15-3")
```
The backend parses this (`parse_tool_call()`), executes the lookup against
that request's already-computed `trends`/`ner` dicts (`execute_tool()`), and
makes **one** follow-up call with the exact result appended, asking for a
final answer. No loop — capped at one round-trip.

**Why a text protocol instead of each provider's native function-calling API**
(Gemini's `FunctionDeclaration`, Ollama's `tools` field, OpenAI's tool-calling
schema): a plain-text protocol works identically across all three backends
without betting on SDK-specific function-calling shapes staying stable, and
critically — it works even for a 3B local model whose native tool-calling
reliability is itself questionable. Falls back cleanly: if the model never
emits a `TOOL_CALL:` line, behavior is unchanged from before this feature
existed (verified — it's additive, not a required path).

**Important nuance discovered while building this:** `get_lab_trend()` must
match against both the trend's dict key (`"Tumor Marker Panel"`) AND its raw
value text (`"CA 15-3 mildly elevated (38 U/mL)"`) — because doctors ask by
the clinical shorthand ("CA 15-3"), which never appears in the generic panel
name, only in the raw result string. This was caught writing the test suite,
not in live testing — see `test_get_lab_trend_matches_by_clinical_name_not_just_panel_name`.

### 7.7 Why rate limiting was removed, then re-added at a different number

First implementation: 10/min. User pushed back — a doctor shouldn't get a 429
mid-shift for asking questions. Initial response was to drop rate limiting
entirely. **On reflection/debate, the better answer was: keep it, but at
60/min, not 10.** Reasoning: JWT auth + RBAC + audit log protect against
*unauthenticated* abuse, but do nothing to slow down a *stolen token* scraping
PHI at high volume before the audit log is even reviewed. 60/min (1 request
per second) is invisible to any real clinician's typing/reading pace but stops
automated scraping. Rate limit key is the JWT token prefix, not IP — IP limits
are trivially bypassed with a VPN. This back-and-forth is preserved in commit
history (`4235957` drop → `ef62695` re-add at 60/min) as a real example of
revising a decision after being challenged on it, not just complying with the
first pushback.

---

## 8. Live-Test Findings (2026-07-27) — Real Bugs Found, Fixed, NOT Yet Re-Verified Live

This is the most important section for whoever picks this up next. A live
testing session against `llama3.2:3B` on Ollama surfaced genuine failures.
**All fixes below are unit-tested (50/50 passing) but have NOT been re-run
against the live chat UI with the same failing scenarios yet.** That
re-verification is the explicit next task — see §10.

### 8.1 CRITICAL — model diagnosed a patient despite an explicit rule not to

System prompt states: *"Never make diagnoses - only summarize and analyze
existing data."* When asked to diagnose, the live model answered: *"Based on
the available records, Breast Cancer is the most likely diagnosis."* None of
the 3 existing guardrails caught this — they check confidence/dosage/citation,
nothing checked for diagnostic language.

**Fix:** added guardrail #4 (`check_diagnosis`, §7.4). **Not yet re-tested
live** — only unit-tested against synthetic strings.

### 8.2 Scope leakage — "hi" and general questions dumped full patient data

System prompt explicitly separates greeting/general-knowledge/patient-specific
question types (§3.4). Live test: `"hi"` got a full anemia/treatment/profile
dump instead of one short sentence. `"what is neutropenia?"` (meant to be
general knowledge) returned patient-specific WBC values instead. This is both
a correctness bug and a HIPAA minimum-necessary-rule concern (PHI surfacing
when not needed).

**Status: NOT fixed.** This is a prompt-following failure by the small local
model, not a pipeline bug — no code change addresses it directly yet. Options
considered but not implemented: shrinking the system prompt for the Ollama
path specifically (small models follow fewer, blunter rules better), or a
post-hoc classifier that strips patient data from responses to greetings
before they're returned. **This is an open item, not resolved — see §10.**

### 8.3 Encoder trend math not faithfully relayed by the LLM

Encoder correctly computed a CA 15-3 trend (38→22 U/mL, verified by unit
tests). The LLM's prose restatement said `(→ 0.0%)` — a fabricated number, not
what the encoder computed. This is exactly what task 9 (tool-calling, §7.6)
was built to fix — by having the LLM request the fact via `TOOL_CALL:` instead
of restating it from memory, the number returned is byte-for-byte what Python
computed. **Fix implemented, not yet re-tested live against the original
failing question.**

### 8.4 Medications list omitted a real drug (Paclitaxel) — real encoder bug

Traced to root cause: treatment records store drug names under `medicines` and
`treatment_name` fields (confirmed by inspecting `data/scenarios/breast_cancer.json`
directly), but `extract_ner_signals()` only scanned `result`/`notes`/`medication`/
`diagnosis`. Paclitaxel simply never got scanned. **Fixed** — added `medicines`
and `treatment_name` to the scan list, with a regression test
(`test_ner_detects_drug_in_medicines_field`) using the exact real record shape
that caused the bug.

### 8.5 Self-contradiction across conversation turns

Turn 1 stated a specific chemo dosage (`Paclitaxel 80mg/m²`). A later turn in
the *same conversation* claimed "no chemo dosage information available."
Similarly, WBC was reported as two different values (`3.4` then `4.1 ×10^9/L`)
in consecutive turns for the same patient. **Status: NOT fixed.** Root cause is
the 3B model's general reliability, not a specific extractable bug — the
tool-calling protocol (§7.6) reduces the *numeric hallucination* variant of
this (since a tool call returns a fixed string), but doesn't fully solve
cross-turn narrative consistency. Worth watching whether task 9 incidentally
improves this before building anything more targeted at it.

### 8.6 Alert fatigue — confidence guardrail fired on almost every response

With the 3B local model, "Low confidence" appeared on nearly every single
turn. A warning that never turns off stops meaning anything to the doctor
reading it. **Status: NOT fixed** — the 80-word threshold may need to be
model-aware (smaller local models naturally produce shorter answers than
Gemini) or the hedge-phrase list may be too broad. Open item, see §10.

### 8.7 Ollama context window was silently capped

Discovered while diagnosing the above: Ollama defaults `num_ctx` to a
VRAM-based heuristic (was landing at 4096) regardless of what the model was
actually trained on (llama3.2 supports 131K). Prompts here run ~3000 tokens,
leaving very little headroom for the model to reason with. **Fixed** — forced
`"options": {"num_ctx": 8192}` in the Ollama request payload (`server.py`,
`_ollama_generate()`). This is a request-parameter fix, not a model or encoder
change — no fine-tuning, no retraining involved.

---

## 9. Root Cause Behind Most of §8: Model Size, Not Architecture

The pipeline itself (auth → encoder → LLM → guardrails → audit) is working as
designed. The bottleneck is `llama3.2:3B` — a 3-billion-parameter model is too
small to reliably: follow a system prompt with ~10 distinct behavioral rules,
maintain numeric consistency across conversation turns, or faithfully quote
structured data instead of paraphrasing it. This is a known, general
limitation of small local models, not specific to this codebase.

**What would actually move the needle, ranked by leverage:**
1. Tool-calling (§7.6) — done, addresses the highest-value case (numeric hallucination)
2. A larger local model (`llama3.1:8b`) — real latency/hardware tradeoff, not yet tried
3. A shorter, blunter system prompt specifically for the Ollama path — not yet tried
4. `meditron` (medical-trained 4GB Ollama model) — won't fix instruction-following
   or scope/consistency issues (those are model-*size* problems, not
   domain-*knowledge* problems), but likely improves raw clinical answer quality

---

## 10. Explicit Next Steps (in priority order)

1. **Live re-verification (do this FIRST, before anything else).** Re-run the
   exact scenarios that failed in the transcript from today against Ollama
   with the fixes now in place:
   - Ask it to diagnose a patient → confirm the new diagnosis guardrail fires
   - Ask the CA 15-3 trend question → confirm it now emits `TOOL_CALL:` and
     the final number matches the encoder's computed -42.1%, not "0.0%"
   - Ask "what medications is she on?" → confirm Paclitaxel now appears
   - Say "hi" → check whether §8.2 (scope leakage) still happens (it's not
     fixed yet — confirm it's still broken, don't assume otherwise)
   - Ask the same lab value question twice in one conversation → check for
     the §8.5 self-contradiction

2. **Decide on §8.2 and §8.6** (scope leakage, alert fatigue) — both are open,
   unfixed, and need either a prompt-engineering pass or a different guardrail
   design. Not yet started.

3. **VLM/vision support for the local path** — `/analyze-document` (X-ray/PDF
   analysis) is currently Gemini-only; `llama3.2` is text-only. Would need
   `llama3.2-vision` or `llava` via Ollama (general vision, not radiology-
   trained) or `MedGemma` (medical-trained VLM, requires manual HuggingFace→
   GGUF conversion, no Ollama registry entry). Not started — discussed only.

4. **Structured JSON output (bigger architectural idea, not started)** — have
   the LLM output a schema-validated JSON object (`{labs: [...], medications:
   [...], next_step: "..."}`) with numeric fields cross-checked
   programmatically against encoder output, and let the frontend render facts
   from a fixed template instead of trusting LLM prose for everything. This is
   the more thorough fix for hallucination — tool-calling (§7.6) is a lighter
   version of the same idea, shipped first because it was implementable
   without touching the frontend.

5. **RAG over medical literature** (not just patient records) — ground general
   medical-knowledge answers (like "what is neutropenia?") against a real
   corpus (WHO/NCCN guidelines) instead of the model's frozen training data.
   Not started, discussed only.

6. **Prompt injection defense** — patient record free-text fields are not
   currently sanitized before being injected into the prompt. A malformed or
   adversarial note could contain injection-shaped text. Not started,
   discussed only — mentioned in `project_knowledge.md` §5 as a "medium"
   severity item since before V3 began.

7. **Task 8 leftover: Azure path is untested** — coded (`_azure_generate()`
   exists, routes correctly) but no `AZURE_OPENAI_ENDPOINT`/`KEY` has ever been
   configured, so it's never actually been exercised end-to-end.

---

## 11. Known Stale Documentation

`backend/README.md`'s "V3 Additions" section is out of date — it still lists
3 guardrails (not 4), says "10/min" rate limiting (actual: 60/min), and
doesn't mention the encoder's tool-calling protocol (task 9) at all. Not fixed
as part of this handoff — flagging so whoever picks this up doesn't trust it
over `V3_PROGRESS.md`, which is current.

---

## 12. How to Run This Project

### First-time setup

```bash
# 1. MongoDB
brew services start mongodb-community

# 2. Backend
cd backend
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

Edit `backend/.env` — required keys:
```
MONGO_URL=mongodb://localhost:27017
DB_NAME=integrated_patient_system
GEMINI_API_KEY=<get a free key at https://aistudio.google.com/apikey>
SECRET_KEY=<run: python3 -c "import secrets; print(secrets.token_hex(32))">
LLM_BACKEND=gemini          # or: ollama | azure
OLLAMA_MODEL=llama3.2       # only relevant if LLM_BACKEND=ollama
```

```bash
# 3. Start the backend
uvicorn server:app --reload --port 8000
```

```bash
# 4. Frontend (separate terminal)
cd frontend
npm install
npm start
```

Frontend needs `frontend/.env` with `REACT_APP_BACKEND_URL=http://localhost:8000`.

### Seeding data (first run, or after a full reset)

Requires an admin JWT (init-data is `ADMIN`-only since V3):
```bash
TOKEN=$(curl -s -X POST http://localhost:8000/api/login \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"admin123"}' | python3 -c "import sys,json; print(json.load(sys.stdin)['token'])")

curl -s -X POST http://localhost:8000/api/clear-data -H "Authorization: Bearer $TOKEN"
curl -s -X POST http://localhost:8000/api/init-data -H "Authorization: Bearer $TOKEN"
```
**Important:** `/init-data` silently no-ops if MongoDB already has profiles —
even if the file-based vendor stores (SQLite/JSON/dbm/shelve/CSV) are empty.
Always `clear-data` first if you suspect partial/corrupted seed state (this
exact scenario happened once this session — see git history around
`156f113`).

### Login credentials

| Role | Username | Password |
|---|---|---|
| Physician | `doctor` | `doctor123` |
| Nurse | `nurse` | `nurse123` |
| Admin | `admin` | `admin123` |

### Running the local model (Ollama)

```bash
brew install ollama
ollama pull llama3.2
ollama serve          # leave running in its own terminal
```
Then set `LLM_BACKEND=ollama` in `backend/.env` and **restart uvicorn** — env
vars are read once at process start, a running server won't pick up `.env`
changes without a restart.

**Verifying you're actually hitting Ollama, not silently still on Gemini:**
watch the `ollama serve` terminal — every `/deep-query` should produce a
`POST /api/chat` log line there in real time. If nothing appears while you get
an answer, the backend didn't actually restart with the new `.env`.

---

## 13. Testing

```bash
cd backend
source venv/bin/activate    # or: ./venv/bin/python -m pytest ...
pytest tests/ -v
```

50 tests, all passing as of this doc. Broken down:
- `test_v3_tasks_1_to_3.py` — 7 tests (pickle→JSON, JWT/RBAC, audit log)
- `test_v3_tasks_4_5.py` — 5 tests (LLM_BACKEND routing, Ollama adapter)
- `test_v3_task_6.py` — 13 tests (trend detector, NER, including the medicines-field regression test)
- `test_v3_task_7.py` — 14 tests (all 4 guardrails)
- `test_v3_task_9.py` — 11 tests (tool-call parsing, execution, clinical-name matching)

**What's NOT covered by automated tests:** anything requiring a live LLM call
(the actual quality/consistency of Gemini or Ollama responses), the full
`/deep-query` HTTP flow end-to-end, rate limiting under real load, and — most
importantly right now — whether today's fixes actually resolve the specific
failures found in live testing (§8). Unit tests confirm the *logic* is
correct in isolation; they don't confirm the live model actually uses it
correctly in conversation. That gap is §10 item #1.

**Common gotcha:** running `pytest` with the wrong Python environment.
`(base)` conda Python does NOT have this project's dependencies
(`google-genai`, `python-jose`, etc.) — always confirm `(venv)` appears in
your shell prompt, or explicitly run `./venv/bin/python -m pytest tests/ -v`.
This tripped up testing multiple times this session.

---

## 14. Design Decisions & Rationale (the "why," not just the "what")

| Decision | Why |
|---|---|
| JWT over server-side sessions | Stateless, no session table, O(1) verification |
| Pickle → JSON | Pickle deserialization of untrusted data executes arbitrary code — not theoretical, a real RCE vector |
| Rate limit at 60/min, not 10 | 10 was reflexively too aggressive for a clinical tool; 60 (1/sec) is invisible to real usage but stops automated token-abuse scraping |
| Rate limit keyed on JWT, not IP | IP limits are trivially bypassed with a VPN |
| Guardrails are additive-only | Never strip or alter the LLM's actual answer — doctor sees the original plus warnings, not a filtered version. Trust requires transparency, not silent correction |
| Encoder is deterministic (no ML) | LLMs hallucinate numbers; Python arithmetic on structured data is provably correct |
| Tool-calling as a text protocol, not native APIs | Provider-agnostic — works identically on Gemini/Ollama/Azure without betting on 3 different SDKs' function-calling shapes; also more robust for a 3B model with weak native tool support |
| 6 different storage technologies for 6 departments | Mirrors real hospital vendor heterogeneity; the normalization work in each gateway is where real integration engineering time actually goes |
| Smart context ignores conversation history for department routing | Prevents an old turn's keyword ("WBC" 3 questions ago) from silently narrowing which departments get fetched for an unrelated new question |
| Never run backend/frontend from Claude's end (working agreement, not architecture) | User runs and confirms locally; Claude only runs commands directly if the user says they can't diagnose an issue themselves |

---

## 15. Glossary (for orientation, not exhaustive — see `project_knowledge.md` §6 for the full compliance glossary)

- **MPI** — Master Patient Index. Maps one canonical patient ID to every department's own local ID.
- **PHI** — Protected Health Information (any data that identifies a patient + relates to their health).
- **ePHI** — PHI in electronic form.
- **BAA** — Business Associate Agreement. Required before a vendor (e.g. Google, for Gemini) can legally process PHI on a covered entity's behalf. **This project's biggest unresolved compliance gap**: consumer Gemini API has no BAA path; only Vertex AI does.
- **HIPAA §164.312(b)** — the specific rule mandating audit controls on ePHI access (why `audit_log` exists).
- **Minimum Necessary Rule** — only access/use the PHI minimally necessary for the task at hand (why smart context routing exists, and why §8.2's scope leakage is a compliance concern, not just a UX bug).
- **RBAC** — Role-Based Access Control (`PHYSICIAN`/`NURSE`/`ADMIN` here).
- **FHIR** — the modern standard for health data exchange (REST/JSON). Real Epic/Cerner systems expose FHIR APIs; this project's "Treatment" records loosely resemble a simplified FHIR shape.

---

## 16. Working Agreements (carry these into any new session)

- Commits go out under **Madhan Kumar Tammineni**'s identity — no Claude co-author trailer. Explicit, repeated standing instruction — see §0.2.
- **Never delete a version branch** (`feature/v1-...` through current). They're
  permanent historical records, full stop — see §0.2.
- New branches always start from current `main`, get merged back into `main`
  when done, never deleted afterward. Naming: `feature/v<N>-<short-name>`.
- `backend/.env` is never committed (contains the Gemini API key + JWT secret).
- `.claude/` is gitignored — never commit it.
- New commits, not amends, unless explicitly asked.
- **Never start/run the backend or frontend servers directly** — hand over the
  exact command and let the user run + confirm in their own terminal.
  Exception: if the user says they can't tell what's wrong or can't resolve it
  themselves, then run/investigate directly to diagnose (this is how §0.4's
  bugs got root-caused — direct curl + live browser reproduction, not guessing
  from code alone).
- Keep `plan.md` updated whenever work changes or progresses (standing preference).
- Ponytail mode active — lean/minimal code by default, no unrequested scaffolding or abstractions.
- Before proposing any git history rewrite (filter-branch, squash, force-push):
  check the actual blast radius first (which branches contain the commit,
  how many downstream commits shift) — assumptions about "low risk" have been
  wrong before (see §0.5, the maparna16 commit turned out to touch every
  branch, not just one).
