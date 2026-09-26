# Deploying this app

The frontend and backend deploy to different kinds of hosts, because they
need different things. This is a one-time setup — after this, new pushes
to `main` redeploy automatically on both.

## Why not one host for everything

The backend isn't a stateless API — it deliberately runs each department
on a different real storage technology (SQLite, JSON, dbm, shelve) to
simulate genuinely fragmented hospital systems, and it can optionally run
a local LLM (Ollama) that needs a persistent process and disk space.
Serverless platforms (Vercel included) give each request a fresh,
ephemeral filesystem and no long-running processes — that breaks both of
those things. The frontend has no such requirement, so it can go
anywhere static, including Vercel.

**Frontend → Vercel. Backend → Render. Database → MongoDB Atlas.**

## 1. MongoDB Atlas (free tier)

1. Create a free cluster at [mongodb.com/atlas](https://www.mongodb.com/atlas).
2. Create a database user and allow network access from anywhere (0.0.0.0/0) — simplest for a demo; tighten later if needed.
3. Copy the connection string — you'll set it as `MONGO_URL` on Render.

## 2. Backend on Render

1. Push this repo to GitHub (already done if you're reading this from the repo).
2. In Render, create a new **Blueprint** and point it at this repo — it will read `backend/render.yaml` automatically.
3. Set the environment variables Render prompts for (marked `sync: false` in the blueprint, so Render won't guess them):
   - `MONGO_URL` — your Atlas connection string
   - `GEMINI_API_KEY` — from [aistudio.google.com/apikey](https://aistudio.google.com/apikey)
   - `SECRET_KEY` — generate with `python3 -c "import secrets; print(secrets.token_hex(32))"`
   - `CORS_ORIGINS` — leave blank for now; come back and set it once you have the Vercel URL (step 3)
4. Deploy. Note the resulting URL (something like `https://integrated-patient-system-backend.onrender.com`).
5. Seed the database once, the same way you would locally: `curl -X POST "https://<your-render-url>/api/init-data?reset=true"`.

**Known tradeoff:** Render's free tier doesn't persist disk across restarts/redeploys unless you add a paid persistent disk. That means the six department stores reset to freshly-seeded demo data on every redeploy — fine for a pilot/demo, not something to build on for real data yet.

## 3. Frontend on Vercel

1. Import this repo into Vercel.
2. Set the project's **Root Directory** to `frontend` (Vercel asks for this on import).
3. Add one environment variable: `REACT_APP_BACKEND_URL` = your Render backend URL from step 2 (no trailing slash).
4. Deploy. Vercel gives you a `https://your-app.vercel.app` URL.

## 4. Close the loop

Go back to Render and set `CORS_ORIGINS` to your Vercel URL (e.g.
`https://your-app.vercel.app`) instead of leaving it blank, then redeploy
the backend so it only accepts requests from your actual frontend.

## What this doesn't cover

- The local model path (`LLM_BACKEND=ollama`) only works on your own
  machine or a real VM with persistent disk — not on Render's standard
  web service. Use `LLM_BACKEND=gemini` for the hosted version.
- This is a demo/pilot deployment, not a HIPAA-ready one — see
  [`project_knowledge.md`](./project_knowledge.md) for what's still
  needed before this could touch real patient data.
