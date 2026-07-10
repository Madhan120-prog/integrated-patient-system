# XYZ Hospital — Integrated Patient Data Retrieval System

A full-stack tool for hospital staff to search for a patient and view their
complete medical record — MRI, X-Ray, ECG, Blood Profile, CT Scan, and
Treatment history — in one place, plus an AI clinical assistant ("Deep
Search") that answers natural-language questions (by voice or text) about a
patient's records and can analyze uploaded medical documents/images.

## Stack

- **Backend**: FastAPI + Motor (async MongoDB driver)
- **Frontend**: React (CRA/craco) + Tailwind + shadcn/ui + Recharts
- **Database**: MongoDB
- **LLM**: Google Gemini (`gemini-2.5-flash`) for the Deep Search assistant and
  document analysis

## Local setup

### 1. MongoDB

```bash
docker compose up -d mongo
```

### 2. Backend

```bash
cd backend
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # then fill in GEMINI_API_KEY (free key: https://aistudio.google.com/apikey)
uvicorn server:app --reload
```

On first run, seed sample data:

```bash
curl -X POST http://localhost:8000/api/init-data
```

### 3. Frontend

```bash
cd frontend
npm install
npm start
```

Default login: `doctor` / `doctor123` (see `backend/server.py` for other seeded accounts).

## Features

- Staff login
- Patient search by ID or name
- Department-wise medical records, sorted chronologically
- Department-wide record browsing
- Per-patient analytics dashboard (visit breakdowns, treatment progress)
- Deep Search: voice-enabled AI clinical assistant that answers questions
  about a patient's full record and can analyze uploaded medical
  images/PDFs
