# Project Plan — Integrated Patient Data Retrieval System

> Last updated: 2026-07-15

## Project Context

A cancer hospital in Memphis, US uses separate department software systems (Epic/Cerner
for treatment, GE PACS for radiology, MUSE for ECG, Sunquest/PathNet for lab work) —
each with its own database. No unified view exists across departments. This system acts
as an integration layer: one patient ID retrieves the full medical history across all 6
departments, powered by an AI clinical assistant that can reason across the combined data.

---

## Phase 1: Remove Emergent.sh Dependency (COMPLETED)

- [x] Backend: Replace `emergentintegrations` with direct Google Gemini API (`google-genai`)
- [x] Backend: Clean `requirements.txt`, add `.env.example`
- [x] Frontend: Strip all Emergent branding, PostHog analytics, rrweb session recording
- [x] Frontend: Self-host hospital logo, remove CDN dependency
- [x] Frontend: Delete Emergent webpack/babel plugins, simplify `craco.config.js`
- [x] Repo: Delete `.emergent/`, `.gitconfig`, `test_reports/`, clean `.gitignore`
- [x] Repo: Rewrite README with real setup steps
- [x] Verification: Login, search, patient records, analytics, Deep Search all working
- [x] Zero Emergent references remaining in codebase

---

## Phase 2: Realistic Oncology Patient Data (IMMEDIATE — do this now)

### Problem
- Patient names are inconsistent across department collections (Faker re-seeding bug)
- Medical images don't match test types (chest X-ray shows a leg)
- Every patient has random tests from every department — unrealistic
- Data has no medical logic (no coherent patient stories)

### Tasks

#### A. Design Patient Scenarios (oncology-focused)
- [x] Create 12 curated patient profiles with realistic demographics (Memphis addresses, real cancer conditions)
- [x] Each patient gets a medical "story" based on their cancer type — 9 scenario templates:
  lung cancer, breast cancer, colorectal cancer, prostate cancer, leukemia, lymphoma,
  brain tumor, routine screening, post-treatment follow-up
- [x] Not every patient has every test — only what makes medical sense (verified: leukemia
  patient has zero X-rays, heavy blood work; routine screening patient has minimal records)
- [x] Test results follow logical timelines (e.g. leukemia: WBC 45k with blasts → induction
  chemo → WBC normalizing → remission confirmed → maintenance therapy)

#### B. Source Correct Medical Images
- [x] Discovered: my first attempt at Wikimedia URLs was hallucinated (guessed file hash
  paths) — all 404'd. Fixed by writing `backend/data/resolve_images.py` which calls the
  real Wikimedia Commons Search + imageinfo API to resolve actual working thumbnail URLs
  per test type (brain MRI, chest X-ray, ECG tracing, CT scan, lab blood work, etc.)
- [x] Resolver found bad category matches too (search relevance issues, not broken links):
  a pelvic ultrasound mislabeled as "Abdominal MRI", a concrete-cracking photo matched for
  "Stress ECG" (matched on the word "stress"), 1912 textbook scans for Holter/Event
  monitors. Added a blacklist filter + manually re-sourced and hand-verified the 2 worst
  offenders via direct Commons API title lookups.
- [x] All 23 test-type categories populated, all 32 unique URLs verified HTTP 200
- [x] Re-seeded database with corrected `medical_images.json`
- [x] Verified in browser: Marcus Johnson's Brain MRI now renders a real brain scan image
  (naturalWidth 500, naturalHeight 784 — confirmed actually painted, not broken)

#### C. Rewrite the Seeder (`/api/init-data`)
- [x] Replaced random Faker generation with curated patient data (`backend/data/seed.py`)
- [x] Each patient defined as a complete scenario (profile + all their department records)
- [x] Fixed seed (`random.seed(42)`) for reproducibility of extra generated patients
- [x] Consistent names across all collections for same patient — verified zero mismatches
  across all 12 patients after re-seed
- [x] Scales via `--extra N` flag (tested: 12 curated + 50 extra = 62 patients cleanly)
- [x] Proper image URLs per test type (blood_profile category also fixed — 6 distinct
      real lab photos instead of 2 repeated ones)

#### D. Re-seed & Verify (COMPLETE)
- [x] Re-seeded with final corrected data + images
- [x] Verified in browser: patient search shows consistent data
- [x] Verified DocAssist AI gives coherent answers with new data
- [x] Verified evidence cards show correct images for their test type

---

## Phase 3: AI Assistant Improvements (COMPLETE)

### A. LLM Provider — DECIDED: keep Gemini
- [x] Gemini (`gemini-3-flash-preview`) already working, free tier, multimodal.
      No switch to OpenAI/open-source unless cost or quality actually breaks — not
      evaluating alternatives speculatively.

### B. Enhance DocAssist Features
- [x] Text Q&A — verified working end-to-end with Gemini
- [x] Voice output — initially fixed 3 bugs in the browser's SpeechSynthesis
      API (markdown read literally, no pauses, low-quality default voice), but
      on the user's actual machine the browser's TTS engine turned out to be
      permanently stuck (Chrome/macOS bug — speechSynthesis.speak() silently
      did nothing, no events fired at all, confirmed via direct console test
      that bypassed our code entirely). Root-caused by moving TTS server-side
      instead of patching around a browser bug: added `POST /api/tts` using
      `gTTS` (free, no API key) to generate real MP3 audio, frontend now
      fetches it and plays via a plain `<audio>` element instead of
      `speechSynthesis`. More reliable, works identically in every browser.
      Verified end-to-end: Audio instance played 24.384s / 24.384s to
      completion (checked via `currentTime === duration && ended === true`)
- [x] Fixed: frontend had a hardcoded regex gatekeeper blocking "hi", "hello",
      "ok", "test" etc as "meaningless input" before reaching the LLM at all —
      deleted it, moved the judgment call to Gemini via a system prompt rule
      ("if greeted, respond naturally then offer help"). Verified: "Hi" now
      gets a real greeting response instead of a rejection message
- [x] Fixed: voice output showed a false "failed" toast on normal utterance
      interruption (Chrome fires 'canceled'/'interrupted' error whenever a new
      utterance replaces one still speaking — expected, not a real failure).
      Now only surfaces genuine errors to the user
- [x] Document analysis — tested with a real chest X-ray via the exact API the
      frontend calls (multipart upload). Gemini correctly identified it as a
      "Chest Radiograph, PA view" and gave a real structured radiological read
      (trachea, cardiac silhouette, lung fields, pleural spaces, bones) tied to
      the patient's age/context — confirmed genuine multimodal image analysis,
      not just text-based guessing
- [x] Voice input (mic) — code-reviewed: uses standard SpeechRecognition API,
      correctly handles the "permission denied" case, transcribes into the
      input field. Automated browser can't provide real microphone audio to
      fully confirm — user should test by clicking the mic and speaking
- [x] Oncology-aware + doctor-friendly system prompt rewrite: leads with the
      answer (no "Based on the records..." preamble), flags abnormal findings
      first, uses real clinical shorthand (WBC, Hgb, Tx, CBC, NSR, f/u — not
      spelled out), bullets over paragraphs, bold only on abnormal values, ends
      with one relevant follow-up question. Verified: leukemia patient query
      now reads like an actual chart note instead of a chatbot essay
- [ ] Error handling / user feedback when AI unavailable
- [x] Conversation memory — already implemented (last 6 turns prepended to
      each prompt), verified working, no rebuild needed
- [x] Interactive UI — added 4 quick-action buttons (Summarize, Flag concerns,
      Latest labs, Treatment plan) that fire a canned question directly, no
      typing needed. Verified in browser: "Flag concerns" correctly triggered
      the ⚠ WBC 45,000 / 60% blasts flagged response
- [x] Conversational scope fix — greetings/general questions were dumping full
      patient records (both in the answer text AND as evidence cards). Fixed
      two places: (1) system prompt now explicitly separates greeting/general/
      patient-specific question types, (2) evidence-card logic no longer
      defaults to "attach everything" when no department keyword matches —
      only does that for genuine overview requests (summarize, status, etc).
      Verified: "Hi" → 0 evidence, clean short reply. "What is neutropenia?"
      → general answer, 0 evidence. "Summarize" → 6 evidence cards as expected
- [x] Clean markdown rendering — AI answers showed literal `**asterisks**` in
      the UI since the chat bubble just printed raw text. Wrote a small (~20
      line) renderer for bold/bullets/headers instead of adding a markdown
      library dependency for 3 patterns. Verified in browser: bold, bullets
      render properly now, no stray symbols
- [x] Voice control redesigned — replaced the "🔊 Voice On" text button with a
      Siri-style orb: gentle teal breathing pulse when idle, animated color
      swirl + expanding sonar rings while speaking, flat gray when muted. No
      text label — state conveyed visually + via title/aria-label tooltip

### C. Smart Context (send only relevant data) — COMPLETE
- [x] Moved keyword-matching before the Gemini call instead of after (it existed
      already but only for evidence-card selection). Now the same match also
      decides which department collections get queried from MongoDB and
      included in the prompt — skips both the DB round-trip and the tokens for
      irrelevant departments.
- [x] Greetings/general questions → zero departments fetched, zero patient data
      in the prompt at all (not just an empty evidence array — the LLM
      literally never sees the records). Overview questions (summarize, status)
      still fetch everything, same as before.
- [x] Verified: "Hi" → 0 evidence, 0 matched_departments, clean short answer.
      Single-department test (WBC question) hit Gemini's daily free-tier quota
      (20 req/day, exhausted from testing) before returning, but confirmed the
      code path runs cleanly through to a real Gemini API call with no errors.

### D. Error Handling — COMPLETE
- [x] Distinguished Gemini's transient 503 "high demand" overload (seen
      repeatedly during testing) from other failures. Added `generate_content_with_retry()`
      — one automatic retry on `ServerError`, then a clear 503 with an
      actionable message ("AI is temporarily overloaded, try again in a
      moment") instead of a generic 500. Wired into both `/deep-query` and
      `/analyze-document`. Frontend now shows this message distinctly from
      other errors.

---

## Phase 4: Cloud Deployment (LATER — for demo/showcase)

- [ ] MongoDB Atlas (free tier) — replace local Homebrew MongoDB
- [ ] Backend on Railway / Render / Fly.io
- [ ] Frontend on Vercel / Netlify
- [ ] Update hospital name and branding
- [ ] Custom domain, HTTPS, production CORS

---

## Phase 5: Security & Hardening (FUTURE)

- [ ] JWT authentication (replace hardcoded demo credentials)
- [ ] Rate limiting on AI endpoints
- [ ] Prompt injection defense
- [ ] HIPAA considerations (Vertex AI or on-premise LLM)
- [ ] Audit logging for AI queries
- [ ] MongoDB authentication

---

## Notes
- **Hospital concept**: Cancer hospital in Memphis, US (name TBD — currently "XYZ Hospital")
- **Branch**: `chore/remove-emergent-dependency`
- **LLM**: Gemini 3 Flash Preview (free tier — older models deprecated for this API key)
- **Database**: MongoDB 7.0 via Homebrew (6 collections simulating 6 department databases)
- **Real-world dept software**: Epic/Cerner (EMR), GE PACS (radiology), MUSE (ECG), Sunquest (lab)
- **Stack**: FastAPI + Motor (backend), React + CRA/craco + Tailwind/shadcn (frontend)
