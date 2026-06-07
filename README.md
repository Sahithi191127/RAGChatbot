# Mutual Fund FAQ Assistant

Facts-only RAG chatbot for **five HDFC Mutual Fund schemes** on Groww. No investment advice; every factual answer includes a single source link and a last-updated footer.

## Documentation

| Document | Description |
|----------|-------------|
| [DOCS/ProblemStatement.md](DOCS/ProblemStatement.md) | Scope, corpus, success criteria |
| [DOCS/architecture.md](DOCS/architecture.md) | System design and components |
| [DOCS/implementationplan.md](DOCS/implementationplan.md) | Phase-wise build plan |
| [DOCS/deployment-plan.md](DOCS/deployment-plan.md) | Streamlit Community Cloud deployment |
| [DOCS/deployment-vercel-railway.md](DOCS/deployment-vercel-railway.md) | **Vercel (UI) + Railway (API)** |
| [DOCS/edgecase.md](DOCS/edgecase.md) | Edge cases and test catalog |

## Requirements

- Python **3.10+**
- pip

## Setup

```bash
cd RAGChatbot
python -m venv .venv

# Windows
.venv\Scripts\activate

# macOS / Linux
# source .venv/bin/activate

pip install -r requirements.txt
cp .env.example .env
# Edit .env when adding LLM keys (Phase 6+)
```

## Run API (Phase 7)

```bash
python -m app.main
```

Server: [http://127.0.0.1:8000](http://127.0.0.1:8000)

## Frontend (Next.js — Phase 8)

React chat UI matching the **FundFacts Assistant** design. Runs on port **3000** and proxies `/api/*` to the FastAPI backend.

```powershell
# Terminal 1 — backend
$env:PYTHONPATH="."
.venv\Scripts\python -m app.main

# Terminal 2 — frontend
cd frontend
copy .env.local.example .env.local
npm install
npm run dev
```

Open [http://localhost:3000](http://localhost:3000). See [frontend/README.md](frontend/README.md) and [tests/PHASE8_SIGNOFF.md](tests/PHASE8_SIGNOFF.md) for UI sign-off.

The legacy static UI in `ui/` is still served at `/` when only the API is running.

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/health` | GET | Liveness + `index_ready` |
| `/api/schemes` | GET | List five HDFC schemes |
| `/api/chat` | POST | Chat body `{ "message": "..." }` |
| `/docs` | GET | OpenAPI UI |

```bash
curl -X POST http://127.0.0.1:8000/api/chat ^
  -H "Content-Type: application/json" ^
  -d "{\"message\": \"What is the expense ratio of HDFC Mid Cap Fund Direct Growth?\"}"
```

## Ingestion (Phase 2 — full pipeline)

```bash
# Full pipeline: fetch → parse → chunk → embed → index
set USE_CACHE=true
python ingestion/run.py --use-cache

# Or live Groww fetch (requires network):
python ingestion/run.py

# Parse/chunk/index only (reuse data/raw + processed):
python ingestion/run.py --skip-fetch
```

Outputs:

| Path | Content |
|------|---------|
| `data/raw/` | Fetched HTML or markdown + `.meta.json` |
| `data/processed/{slug}.json` | Parsed sections |
| `data/processed/{slug}.chunks.json` | Chunk records (optional artifact) |
| `data/index/chroma/` | ChromaDB vector store |
| `data/index/metadata.json` | Scheme metadata + `last_fetched_at` |

Embedding defaults: `EMBEDDING_PROVIDER=local`, `EMBEDDING_MODEL=BAAI/bge-small-en-v1.5` (see `.env.example`).

## Scheduler (Phase 3)

Triggers ingestion on a schedule; does not serve chat traffic. See [scheduler/README.md](scheduler/README.md).

**Daily 10:00 AM IST:** set `INGESTION_SCHEDULE_CRON=30 4 * * *` in `.env` (04:30 UTC), then run the daemon below.

```bash
# One-shot (manual or cron wrapper)
set PYTHONPATH=.
python scheduler/daily.py --once

# Dev daemon (APScheduler — uses INGESTION_SCHEDULE_CRON or SCHEDULE_HOUR_UTC from .env)
python scheduler/daily.py
```

The API (`python -m app.main`) does not import the scheduler. During ingestion, chat continues using the previous index until the new Chroma build is swapped in.

## Retrieval (Phase 4)

Metadata-first hybrid search over `data/index/chroma/` (scheme + section rules, then slug-scoped semantic fallback).

```python
from app.retriever import retrieve
result = retrieve("Expense ratio HDFC Mid Cap")
# result.chunks[0].chunk.section, result.resolved_slug, flags
```

Requires a built index (`python ingestion/run.py`). See [DOCS/implementationplan.md](DOCS/implementationplan.md) Phase 4.

## Application layer (Phase 5)

```python
from app.rag import chat
response = chat("Expense ratio HDFC Mid Cap")
# response.answer, response.citation_url, response.is_refusal
```

Classifier → retriever (factual only) → Groq LLM (or stub) → validator → formatter. Refusals skip retrieval.

## Generation (Phase 6 — Groq)

Set in `.env`:

```env
LLM_PROVIDER=groq
LLM_API_KEY=your_groq_api_key
LLM_MODEL=llama-3.3-70b-versatile
LLM_BASE_URL=https://api.groq.com/openai/v1
```

Without `LLM_API_KEY` (or with `USE_LLM_STUB=true`), answers use the rule-based stub from Phase 5.

## Tests

```bash
pytest
```

Phase 9 acceptance matrix: [tests/MANUAL_QA.md](tests/MANUAL_QA.md) (163 automated tests, including parametrized coverage for all five schemes). CI: `.github/workflows/ci.yml`.

## Corpus config (Phase 1)

- Schemes and URLs: [`config/corpus.yaml`](config/corpus.yaml)
- Load in code: `from config import get_corpus_config, get_groww_citation_allowlist`
- Models: [`app/models.py`](app/models.py) (`SchemeMetadata`, `ChunkRecord`, `ChatRequest`, `ChatResponse`)

## Project layout

```
RAGChatbot/
├── app/           # FastAPI application + shared models
├── config/        # corpus.yaml, loader.py, chunk_ids.py
├── ingestion/     # offline pipeline (Phase 2+)
├── scheduler/     # triggers ingestion (Phase 3+)
├── ui/            # legacy static chat UI (optional)
├── frontend/      # Next.js React chat UI (Phase 8)
├── data/          # raw, processed, index
├── tests/
└── DOCS/
```

## Corpus (phase 1 scope)

HDFC schemes on Groww: Mid Cap, Small Cap, Large Cap, Gold ETF FoF, Defence — see [ProblemStatement.md](DOCS/ProblemStatement.md).

## Disclaimer

Facts-only. No investment advice.
