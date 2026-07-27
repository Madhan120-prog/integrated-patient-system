# West Cancer Center — Integrated Patient Data Retrieval System

A full-stack clinical tool that federates data from six isolated hospital department systems into a single unified view, with an AI clinical assistant (DocAssist) that reasons across all departments, flags abnormalities proactively, and supports voice interaction.

## Architecture Overview

Six departments each run their own separate vendor system — no shared database. A Master Patient Index (MPI) connects them.

```
Doctor enters patient ID
        ↓
   MPI (MongoDB)
   maps patient_id → local vendor IDs
        ↓
┌──────────────────────────────────────────────────────┐
│  Labs        │ SQLite       │ Sunquest simulation     │
│  MRI         │ JSON files   │ RIS simulation          │
│  X-Ray       │ dbm          │ PACS key-value          │
│  CT Scan     │ shelve       │ Object store simulation │
│  ECG         │ CSV          │ MUSE flat-file          │
│  Treatment   │ Pickle blob  │ Epic simulation         │
└──────────────────────────────────────────────────────┘
        ↓
   Normalized records → Gemini → DocAssist answer
```

Each department is a separate "vendor system" — only its gateway module knows how to talk to it. The backend never queries vendor systems directly.

## Stack

| Layer | Technology |
|---|---|
| Backend | FastAPI + Motor (async MongoDB) |
| Frontend | React (CRA/craco) + Tailwind + shadcn/ui + Recharts |
| Central DB | MongoDB 7.0 (MPI + patient index) |
| Dept systems | SQLite, JSON files, dbm, shelve, CSV, pickle (one per dept) |
| LLM | Google Gemini `gemini-3-flash-preview` |
| Voice output | gTTS (server-side MP3, no browser TTS dependency) |

## Features

- Staff login
- Patient search by ID or name (500 realistic oncology patients)
- Department-wise medical records across all 6 systems, sorted chronologically
- Department-wide record browsing
- Per-patient analytics dashboard
- **DocAssist** — AI clinical assistant:
  - Answers natural-language questions across all 6 departments
  - Smart context routing (only fetches departments relevant to the question)
  - Proactive abnormality flagging on patient load (silent unless findings exist)
  - Trend callouts on consecutive results (e.g. CEA 12.5 → 5.2 ng/mL)
  - "What changed?" quick action comparing current vs previous records
  - Collapsible evidence cards (shows exactly which records the AI used)
  - Conversation history (last 6 turns sent with each query)
  - Voice output via gTTS
  - Format override — "give me a paragraph" actually works
  - Disclaimer on every response

## Local Setup

### 1. MongoDB

```bash
brew services start mongodb-community
```

Or via Docker:
```bash
docker compose up -d mongo
```

### 2. Backend

```bash
cd backend
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # fill in GEMINI_API_KEY — free key: https://aistudio.google.com/apikey
uvicorn server:app --reload
```

### 3. Seed data (first run only)

```bash
# Reset MPI + all 6 vendor systems and seed 500 patients
curl -X POST "http://localhost:8000/api/init-data?reset=true"
```

> Seeding takes ~30–60 seconds for 500 patients across 6 vendor stores.
> Run once. Do not run again unless you want a fresh dataset.

### 4. Frontend

```bash
cd frontend
npm install
npm start
```

Open `http://localhost:3000`. Default login: `doctor` / `doctor123`

## Branch Structure

```
main                          ← stable, production-ready
  └── feature/department-integration-v2   ← federated 6-dept architecture
        └── feature/ai-capabilities-v2   ← DocAssist AI improvements (this branch)
```

Merge order when ready: `ai-capabilities-v2` → `department-integration-v2` → `main`

## What's NOT Committed (intentionally)

Vendor data stores are generated locally and gitignored:

```
backend/data/sunquest.db       ← Labs (SQLite)
backend/data/mri_store/        ← MRI (JSON files)
backend/data/xray_store*       ← X-Ray (dbm)
backend/data/ct_store*         ← CT Scan (shelve)
backend/data/ecg_store.csv     ← ECG (CSV)
backend/data/treatment_store.pkl ← Treatment (pickle)
backend/.env                   ← Gemini API key
```

Run `init-data` to regenerate them on any fresh clone.

## Next: V3 Security + AI Pipeline

See [`project_knowledge.md`](./project_knowledge.md) for the full V3 design — JWT auth, audit logging, local model support (Ollama + Meditron3), encoder-layer trend detection, guardrails, and HIPAA cloud deployment options.
