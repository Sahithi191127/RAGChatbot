# FundFacts Assistant — Frontend

Next.js (React) chat UI for the HDFC Mutual Fund FAQ RAG backend.

## Prerequisites

- Node.js 20+
- FastAPI backend running (see project root `README.md`)

## Setup

```powershell
cd frontend
copy .env.local.example .env.local
npm install
```

Edit `.env.local` if your API runs on a port other than `8000` (e.g. `8001`).

## Development

Start the backend first:

```powershell
cd ..
$env:PYTHONPATH="."
.venv\Scripts\python -m app.main
```

Then start the frontend:

```powershell
cd frontend
npm run dev
```

Open [http://localhost:3000](http://localhost:3000). API requests to `/api/*` are proxied to the FastAPI server via `next.config.ts` rewrites.

## Production build

```powershell
npm run build
npm start
```

Set `API_URL` to your deployed FastAPI origin when building/running, or set `NEXT_PUBLIC_API_URL` if the browser should call the API directly (requires CORS on the backend — already enabled).

## Features

- Dark-themed **FundFacts Assistant** layout matching the design spec
- Welcome card with supported schemes and clickable example questions
- User/assistant chat bubbles with source links and last-updated footer
- PII privacy notice and facts-only disclaimer bar
