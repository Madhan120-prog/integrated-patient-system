# Project Rules

Conventions for this repo. Check before adding code, deps, or data.

## Code
- No new dependency if stdlib/an installed package already covers it.
- No abstraction for one use case (no interface with one implementation, no config for a value that never changes).
- Fix root cause, not symptom — grep all callers before patching a shared function.
- Shortest diff that's correct. Boring over clever.

## Data
- Never call `/api/init-data` twice without clearing collections first (Faker/seed re-runs create duplicate profiles with mismatched names across collections — this bit us once already).
- Patient data lives in `backend/data/` — `patients.json` (profiles) + `scenarios/*.json` (medical timelines) + `medical_images.json` (image URLs by test type). Edit these, not hardcoded values in `server.py`.
- Every patient scenario must be medically coherent: results follow a timeline, only relevant departments have records (a leukemia patient doesn't need an X-Ray).
- Image URLs: verify with `curl -o /dev/null -w "%{http_code}"` before trusting them — Wikimedia URLs are easy to hallucinate wrong, and API search matches loosely (a "stress" query once returned a photo of cracked concrete).
- Scaling patient count: use `build_seed_data(extra_count=N)` in `backend/data/seed.py`, not manual JSON edits.

## AI / LLM
- Model: `gemini-3-flash-preview` (`backend/server.py` `GEMINI_MODEL` constant). Older Gemini models (2.0, 2.5) are deprecated/quota-blocked for this API key — check `client.models.list()` before assuming a model name works.
- `report_image` URLs are never sent to the LLM — only structured text (test results, dates, doctors, medicines). Image accuracy has zero effect on AI answer quality.
- Don't send all 6 department collections to every query — filter to relevant ones once "smart context" ships (Phase 3C).

## Git
- Commits go out under the user's own identity (Madhan Kumar Tammineni / Madhan120-prog) — no Claude co-author trailer.
- `.claude/` is gitignored — never commit it.
- New commits, not amends, unless explicitly asked.

## Environment
- MongoDB: local via Homebrew (`brew services start mongodb-community@7.0`), not Docker.
- Backend: `cd backend && source venv/bin/activate && uvicorn server:app --reload --port 8000`
- Frontend: `cd frontend && npm start` (needs `frontend/.env` with `REACT_APP_BACKEND_URL=http://localhost:8000` — CRA won't pick up new env vars without a restart).
- Ponytail plugin is active — lean/minimal code by default, no unrequested scaffolding.
- **Never start/run backend or frontend servers from Claude's end.** Make the code change, then hand the user the exact command(s) to run and ask them to confirm the result. Exception: if the user says they can't tell what's wrong or can't resolve it themselves, Claude may run it directly to diagnose.
