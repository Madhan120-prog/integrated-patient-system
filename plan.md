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
- [ ] Create 10-12 curated patient profiles with realistic demographics
- [ ] Each patient gets a medical "story" based on their cancer type:
  - Lung cancer patient → Chest X-Ray, Chest CT, Blood (tumor markers), ECG (pre-chemo), Chemo treatment
  - Breast cancer patient → MRI, Blood work, Surgery + Chemo treatment
  - Leukemia patient → Blood panels (CBC, WBC), CT Scan, Chemo/Immunotherapy
  - Routine screening patient → just Blood Profile + one X-Ray, all normal
  - Post-treatment follow-up → MRI (monitoring), Blood work, check-up visits
- [ ] Not every patient has every test — only what makes medical sense
- [ ] Test results should follow logical timelines (abnormal finding → more tests → treatment → follow-up)

#### B. Source Correct Medical Images
- [ ] Find properly labeled open medical images per test type:
  - Chest X-Ray → actual chest radiograph
  - Brain MRI → actual brain MRI scan
  - ECG → actual ECG waveform
  - Blood report → lab report format
  - CT Scan → actual CT image
- [ ] Sources: NIH Open-i, Radiopaedia (CC-licensed), or correctly categorized stock photos
- [ ] Map each image URL to the specific test type it belongs to

#### C. Rewrite the Seeder (`/api/init-data`)
- [ ] Replace random Faker generation with curated patient data
- [ ] Each patient defined as a complete scenario (profile + all their department records)
- [ ] Fixed seed for any remaining random elements (dates, doctor names)
- [ ] Consistent names across all collections for same patient
- [ ] Proper image URLs per test type

#### D. Re-seed & Verify
- [ ] Run updated `/api/init-data` once
- [ ] Verify in browser: patient search shows consistent data
- [ ] Verify DocAssist AI gives coherent answers with new data
- [ ] Check all evidence cards show correct images for their test type

---

## Phase 3: AI Assistant Improvements (NEXT — after data fix)

### A. Choose LLM Provider
- [ ] Evaluate options: Gemini (current) vs OpenAI vs Open Source (Llama/Mistral)
- [ ] Consider: cost, quality, latency, privacy, multimodal support
- [ ] Decide and implement

### B. Enhance DocAssist Features
- [ ] Test and fix voice input/output (Web Speech API)
- [ ] Test and fix document analysis (image/PDF upload)
- [ ] Improve AI responses with better system prompts (oncology-aware)
- [ ] Better error handling and user feedback when AI is unavailable

### C. Smart Context (send only relevant data)
- [ ] Instead of sending ALL 6 collections to the LLM, detect which departments
      are relevant to the question and only send those
- [ ] Reduces token usage and improves response quality

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
