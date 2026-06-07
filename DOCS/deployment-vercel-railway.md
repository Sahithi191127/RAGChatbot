# Vercel + Railway deployment guide

Deploy **FundFacts Assistant** with:

| Service | Host | Role |
|---------|------|------|
| **Next.js UI** | [Vercel](https://vercel.com) | `frontend/` — chat UI |
| **FastAPI API** | [Railway](https://railway.app) | RAG backend + Chroma |
| **Ingestion** | GitHub Actions | Daily refresh (10 AM IST) |

Repo: https://github.com/Sahithi191127/RAGChatbot

---

## Architecture

```text
User → Vercel (Next.js) → Railway (FastAPI /api/chat) → Chroma + Groq
                              ↑
                    GitHub Actions (daily ingestion)
```

---

## Part 1 — Prepare the Chroma index (one-time, local)

The vector index is **not** in Git by default. Build it locally:

```powershell
cd RAGChatbot
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
$env:PYTHONPATH="."
python ingestion/run.py --use-cache
```

Verify:

```powershell
curl http://127.0.0.1:8000/health
# index_ready should be true after index exists
```

### Option A — Bake index into Railway image (simpler)

1. Edit `.gitignore` — allow the index:

   ```gitignore
   data/index/*
   !data/index/chroma/
   !data/index/metadata.json
   ```

2. Commit and push:

   ```powershell
   git add data/index/chroma data/index/metadata.json .gitignore
   git commit -m "Add Chroma index for Railway deploy"
   git push
   ```

### Option B — Railway volume (index survives redeploys without Git)

1. Railway → your service → **Volumes** → mount path: `/app/data/index`
2. Run ingestion once via Railway shell or upload index manually

---

## Part 2 — Deploy API on Railway

### 2.1 Create project

1. Go to [railway.app](https://railway.app) → **New Project**
2. **Deploy from GitHub repo** → select `Sahithi191127/RAGChatbot`
3. Railway detects `Dockerfile` + `railway.toml`

### 2.2 Environment variables

Railway → **Variables** tab:

| Variable | Value |
|----------|--------|
| `LLM_API_KEY` | Your Groq API key |
| `LLM_MODEL` | `llama-3.3-70b-versatile` |
| `LLM_BASE_URL` | `https://api.groq.com/openai/v1` |
| `USE_LLM_STUB` | `false` |
| `CHROMA_PATH` | `./data/index/chroma` |
| `EMBEDDING_MODEL` | `BAAI/bge-small-en-v1.5` |
| `EMBEDDING_PROVIDER` | `local` |
| `PYTHONPATH` | `.` |

Railway sets **`PORT`** automatically — the app reads it via `API_PORT` / `PORT`.

### 2.3 Deploy & verify

1. Wait for build (first deploy may take **10–20 min** — downloads embedding model).
2. **Settings → Networking → Generate domain** (e.g. `ragchatbot-api.up.railway.app`)
3. Test:

   ```text
   GET https://YOUR-RAILWAY-URL.up.railway.app/health
   ```

   Expect `"index_ready": true` and `"status": "ok"`.

4. Test chat:

   ```powershell
   Invoke-RestMethod -Uri "https://YOUR-RAILWAY-URL.up.railway.app/api/chat" `
     -Method POST -ContentType "application/json" `
     -Body '{"message":"What is the expense ratio of HDFC Mid Cap Fund Direct Growth?"}'
   ```

### 2.4 Railway tips

- **Memory:** use at least **2 GB RAM** (sentence-transformers + Chroma).
- **Health check:** `/health` (configured in `railway.toml`).
- **Logs:** Railway → **Deployments → View logs** if build OOMs.
- **Daily ingestion:** GitHub Actions → **Daily ingestion** (already in repo); artifacts do not update Railway automatically — re-deploy or use a volume + manual ingest for now.

---

## Part 3 — Deploy frontend on Vercel

### 3.1 Import project

1. Go to [vercel.com](https://vercel.com) → **Add New → Project**
2. Import `Sahithi191127/RAGChatbot`
3. **Root Directory:** `frontend` ← important
4. Framework: **Next.js** (auto-detected)

### 3.2 Environment variables

Vercel → **Settings → Environment Variables**:

| Variable | Value | Environments |
|----------|--------|--------------|
| `NEXT_PUBLIC_API_URL` | `https://YOUR-RAILWAY-URL.up.railway.app` | Production, Preview, Development |

No trailing slash. Example:

```text
NEXT_PUBLIC_API_URL=https://ragchatbot-api-production.up.railway.app
```

The browser calls Railway directly (CORS is enabled on the API).

### 3.3 Deploy

Click **Deploy**. Your app will be at:

```text
https://your-project.vercel.app
```

### 3.4 Smoke test

1. Open the Vercel URL
2. Click an example question (expense ratio, exit load, fund manager)
3. Confirm factual answer + Groww source link
4. Try “Should I invest?” → refusal + learn-more link

---

## Part 4 — Connect custom domains (optional)

| Service | Example |
|---------|---------|
| Vercel | `fundfacts.yourdomain.com` |
| Railway | `api.yourdomain.com` |

After adding a custom Railway domain, update `NEXT_PUBLIC_API_URL` on Vercel and redeploy.

---

## Part 5 — Environment summary

### Local dev

```powershell
# Terminal 1 — API
$env:PYTHONPATH="."
python -m app.main

# Terminal 2 — UI
cd frontend
# .env.local: API_URL=http://127.0.0.1:8000
npm run dev
```

### Production

| Where | Variable | Purpose |
|-------|----------|---------|
| Railway | `LLM_API_KEY`, `CHROMA_PATH`, … | Backend |
| Vercel | `NEXT_PUBLIC_API_URL` | Points UI to Railway |

---

## Troubleshooting

| Symptom | Fix |
|---------|-----|
| Vercel shows “Request failed” | Check `NEXT_PUBLIC_API_URL`; test Railway `/health` |
| `index_ready: false` on Railway | Index missing — Part 1 (commit index or volume) |
| Railway build timeout / OOM | Increase RAM; or set `USE_LLM_STUB=true` temporarily |
| CORS errors | API allows `*` origins; ensure HTTPS URL in `NEXT_PUBLIC_API_URL` |
| Slow first query | Cold start + embedding model load — normal |

---

## Related docs

- [deployment-plan.md](./deployment-plan.md) — Streamlit alternative
- [scheduler/README.md](../scheduler/README.md) — 10 AM IST cron
- [../frontend/README.md](../frontend/README.md) — local frontend setup
