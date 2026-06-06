# Phase 8 sign-off checklist

Primary UI: **Next.js** app in `frontend/` (FundFacts Assistant).  
Fallback UI: static `ui/` served at `/` when only the API runs.

## Exit criteria

| # | Criterion | Status | Notes |
|---|-----------|--------|-------|
| 1 | Welcome message with supported schemes | Done | `WelcomeMessage.tsx` |
| 2 | Three example questions (expense ratio, exit load, fund management) | Done | `EXAMPLE_QUESTIONS` in `frontend/src/lib/types.ts` |
| 3 | Disclaimer always visible | Done | Red footer bar (`DisclaimerFooter.tsx`); legacy `ui/` header banner |
| 4 | Chat calls `POST /api/chat` | Done | `frontend/src/lib/api.ts`, `ui/app.js` |
| 5 | Loading and error states | Done | “Thinking…” spinner; error bubbles |
| 6 | Factual answer: ≤3 sentences, one citation, last-updated footer | Done | Backend formatter; UI renders citation + date |
| 7 | Refusal shows educational link | Done | “Learn more” label when `is_refusal` + `citation_url` |
| 8 | No PII-specific input fields | Done | Generic text input + privacy notice only |

## Manual smoke test (run with backend on :8000, frontend on :3000)

```powershell
# Backend
$env:PYTHONPATH="."
.venv\Scripts\python -m app.main

# Frontend (separate terminal)
cd frontend
npm run dev
```

Click each example pill at http://localhost:3000 and confirm:

1. Expense ratio — Mid Cap → factual answer + Groww source link  
2. Exit load — Defence → factual answer + Groww source link  
3. Who manages — Small Cap → manager names from chunks + source link  

Advisory refusal smoke test:

```powershell
Invoke-RestMethod -Uri http://127.0.0.1:8000/api/chat -Method POST `
  -ContentType "application/json" `
  -Body '{"message":"Should I invest in HDFC Mid Cap?"}'
```

Expect `is_refusal: true` and AMFI/SEBI `citation_url`.

## Dev vs prod UI

| Mode | Command | URL |
|------|---------|-----|
| **Recommended (dev)** | `npm run dev` in `frontend/` | http://localhost:3000 |
| **API-only fallback** | `python -m app.main` | http://localhost:8000/ (static `ui/`) |
| **Prod (optional)** | `npm run build && npm start` in `frontend/` | Configure reverse proxy to API |

Phase 8 complete → proceed to **Phase 9** (manual QA matrix in `tests/MANUAL_QA.md`).
