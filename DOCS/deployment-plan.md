# Deployment Plan: RAGChatbot on Streamlit Community Cloud

This document describes how to deploy the **HDFC Mutual Fund FAQ Assistant** on [Streamlit Community Cloud](https://streamlit.io/cloud). The local project uses **FastAPI + Next.js**; Streamlit Cloud runs a **single Python app**, so deployment uses a thin Streamlit UI that calls the existing RAG pipeline in-process (`app.rag.chat`).

---

## 1. Deployment target vs local stack

| Local (dev) | Streamlit Cloud (prod) |
|-------------|-------------------------|
| FastAPI `app/main.py` on :8000 | Not deployed (logic reused in-process) |
| Next.js `frontend/` on :3000 | Replaced by `streamlit_app.py` |
| Chroma at `data/index/chroma/` | Same path; must be present at runtime |
| Scheduler `scheduler/daily.py` | Use **GitHub Actions** cron (see §7) |
| `.env` | Streamlit **Secrets** (`secrets.toml`) |

**Why Streamlit:** free hosting, simple Python-only deploy, built-in secrets UI, no separate frontend server.

**Trade-offs:** no Next.js UI on Cloud; cold starts can be slow (embedding model + Chroma load); Community Cloud has resource limits; daily ingestion is not run inside Streamlit.

---

## 2. Prerequisites

- GitHub repo: [https://github.com/Sahithi191127/RAGChatbot](https://github.com/Sahithi191127/RAGChatbot)
- Streamlit Community Cloud account (sign in with GitHub)
- Groq API key (`LLM_API_KEY`) for live answers, or `USE_LLM_STUB=true` for demo-only
- **Pre-built Chroma index** available at deploy time (see §4)

---

## 3. Files to add (before first Streamlit deploy)

Create these at the repo root:

### 3.1 `streamlit_app.py`

Minimal chat UI that reuses the existing RAG stack:

```python
"""Streamlit deployment entrypoint — calls app.rag.chat in-process."""

import streamlit as st
from app.rag import chat
from config.loader import get_corpus_config

st.set_page_config(page_title="FundFacts Assistant", page_icon="📊", layout="centered")

config = get_corpus_config()

st.title("FundFacts Assistant")
st.caption("Facts-only FAQ for five HDFC schemes on Groww. No investment advice.")

with st.expander("Supported schemes", expanded=False):
    for scheme in config.schemes:
        st.markdown(f"- {scheme.scheme_name}")

examples = [
    "What is the expense ratio of HDFC Mid Cap Fund Direct Growth?",
    "What is the exit load on HDFC Defence Fund Direct Growth?",
    "Who manages HDFC Small Cap Fund Direct Growth?",
]
cols = st.columns(1)
for q in examples:
    if st.button(q, key=q):
        st.session_state["pending"] = q

if "messages" not in st.session_state:
    st.session_state.messages = []

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])
        if msg.get("citation"):
            st.markdown(f"[Source]({msg['citation']})")
        if msg.get("last_updated"):
            st.caption(f"Last updated from sources: {msg['last_updated']}")

prompt = st.session_state.pop("pending", None) or st.chat_input(
    "Ask a factual question about one of the supported schemes…"
)

if prompt:
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("assistant"):
        with st.spinner("Thinking…"):
            response = chat(prompt)
        st.markdown(response.answer)
        if response.citation_url:
            label = "Learn more" if response.is_refusal else "Source"
            st.markdown(f"[{label}]({response.citation_url})")
        st.caption(f"Last updated from sources: {response.last_updated}")
    st.session_state.messages.append(
        {
            "role": "assistant",
            "content": response.answer,
            "citation": str(response.citation_url) if response.citation_url else None,
            "last_updated": str(response.last_updated),
        }
    )
    st.rerun()

st.warning("Do not enter PAN, Aadhaar, email, phone, or account numbers.", icon="⚠️")
st.error("DISCLAIMER: Facts-only. No investment advice.", icon="ℹ️")
```

### 3.2 `.streamlit/config.toml`

```toml
[server]
headless = true
enableCORS = false
enableXsrfProtection = true

[browser]
gatherUsageStats = false
```

### 3.3 `requirements.txt`

Ensure the repo root `requirements.txt` includes Streamlit:

```text
streamlit>=1.28.0
```

(Other deps are already listed: `fastapi`, `chromadb`, `sentence-transformers`, `openai`, etc.)

### 3.4 Optional `packages.txt` (system deps)

Usually not required. Add only if Chroma or torch fails on Cloud:

```text
# leave empty unless build logs show missing OS libraries
```

---

## 4. Vector index strategy (critical)

`.gitignore` excludes `data/index/`. Streamlit Cloud **needs** a Chroma index at runtime. Choose one:

| Option | Pros | Cons |
|--------|------|------|
| **A. Commit index (small ~49 chunks)** | Simplest deploy | Increases repo size; remove `data/index/` from `.gitignore` for `chroma/` only |
| **B. Git LFS for `data/index/chroma/`** | Keeps repo lean | LFS setup + quota |
| **C. Build on deploy** | Fresh index | Slow cold start; Groww fetch may fail or timeout on Cloud |
| **D. Download artifact in `streamlit_app.py` startup** | Flexible | Needs hosted URL (S3/GitHub Release) |

**Recommended for first deploy:** **Option A** — after `python ingestion/run.py --skip-fetch`, temporarily allow-list and commit:

```gitignore
# In .gitignore, replace data/index/ block with:
data/index/*
!data/index/chroma/
!data/index/metadata.json
```

Re-run ingestion locally, commit `data/index/chroma/` + `metadata.json`, then deploy.

Verify locally:

```powershell
$env:PYTHONPATH="."
streamlit run streamlit_app.py
```

---

## 5. Streamlit secrets

In Streamlit Cloud → **App settings → Secrets**, paste (TOML):

```toml
LLM_PROVIDER = "groq"
LLM_API_KEY = "your_groq_api_key_here"
LLM_MODEL = "llama-3.3-70b-versatile"
LLM_BASE_URL = "https://api.groq.com/openai/v1"
USE_LLM_STUB = "false"

CHROMA_PATH = "./data/index/chroma"
EMBEDDING_PROVIDER = "local"
EMBEDDING_MODEL = "BAAI/bge-small-en-v1.5"

# Optional: demo without Groq
# USE_LLM_STUB = "true"
# LLM_API_KEY = ""
```

Never commit real keys. `.env` stays local only.

---

## 6. Deploy steps (Streamlit Community Cloud)

1. Push code to `main` on GitHub (including `streamlit_app.py`, index if using Option A).
2. Go to [share.streamlit.io](https://share.streamlit.io) → **Create app**.
3. Select repository: `Sahithi191127/RAGChatbot`.
4. **Branch:** `main`
5. **Main file path:** `streamlit_app.py`
6. **App URL:** e.g. `ragchatbot-fundfacts` → `https://ragchatbot-fundfacts.streamlit.app`
7. Add **Secrets** (§5) → **Deploy**.
8. First boot may take **5–15 minutes** (sentence-transformers download + model load).
9. Smoke-test the three example questions from the problem statement.

### Post-deploy checks

| Check | Expected |
|-------|----------|
| Expense ratio — Mid Cap | Factual answer + Groww link |
| Should I invest? | Refusal + AMFI/SEBI link |
| SBI Mid Cap | Unsupported scheme list |
| Health | App loads without 500 errors |

---

## 7. Scheduler on Streamlit Cloud

Streamlit Cloud **cannot** run `scheduler/daily.py` as a daemon. Use **GitHub Actions** instead.

Example `.github/workflows/ingestion-daily.yml`:

```yaml
name: Daily ingestion

on:
  schedule:
    - cron: "30 4 * * *"   # 10:00 AM IST = 04:30 UTC
  workflow_dispatch:

jobs:
  ingest:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"
      - run: pip install -r requirements.txt
      - run: python ingestion/run.py --use-cache
        env:
          PYTHONPATH: .
          USE_CACHE: "true"
      # Optional: commit updated index back to repo (requires bot token)
```

For a class/demo project, **manual** `python ingestion/run.py` locally + push updated index is enough.

---

## 8. Environment variables mapping

| Local `.env` | Streamlit Secrets |
|--------------|-------------------|
| `LLM_API_KEY` | `LLM_API_KEY` |
| `USE_LLM_STUB` | `USE_LLM_STUB` |
| `CHROMA_PATH` | `CHROMA_PATH` |
| `EMBEDDING_MODEL` | `EMBEDDING_MODEL` |
| `INGESTION_SCHEDULE_CRON` | N/A (use GitHub Actions) |
| `API_PORT` | N/A (no FastAPI on Cloud) |

---

## 9. Limitations on Streamlit Community Cloud

- **Memory:** large embedding models may OOM on free tier; consider smaller model or stub mode for demos.
- **Cold start:** first query slow after idle sleep.
- **No Next.js UI:** Streamlit styling only (or keep Next.js on Vercel pointing to a separate API host).
- **Rate limits:** Groq + Streamlit Cloud shared limits; no built-in per-IP rate limit from `app/rate_limit.py` unless wrapped manually.
- **PII guard:** wire `app/security.py` checks in `streamlit_app.py` before calling `chat()`.
- **One process:** concurrent users share one instance; not ideal for high traffic.

---

## 10. Alternative: hybrid deploy

If you want to keep the **Next.js FundFacts UI**:

| Component | Host |
|-----------|------|
| FastAPI + Chroma | Railway / Render / Fly.io |
| Next.js `frontend/` | Vercel |
| Ingestion | GitHub Actions cron |

Streamlit is best for a **single-app demo**; hybrid is better for production-like UX.

---

## 11. Rollback

1. Streamlit Cloud → **Manage app → Reboot** or redeploy previous Git commit.
2. Pin app to a known-good Git tag: `v1.0.0-phase9`.
3. Set `USE_LLM_STUB=true` in Secrets if Groq is down (degraded but functional).

---

## 12. Checklist before go-live

- [ ] `streamlit_app.py` added and tested locally
- [ ] Chroma index available on Cloud (§4)
- [ ] Secrets configured (no keys in Git)
- [ ] `requirements.txt` includes `streamlit`
- [ ] Example questions pass smoke test
- [ ] Disclaimer visible in UI
- [ ] GitHub repo pushed to `main`

---

## Related docs

- [implementationplan.md](./implementationplan.md) — Phase 10 deploy/docs
- [architecture.md](./architecture.md) — system layers
- [../scheduler/README.md](../scheduler/README.md) — 10:00 AM IST cron (`30 4 * * *`)
- [../tests/MANUAL_QA.md](../tests/MANUAL_QA.md) — QA matrix
