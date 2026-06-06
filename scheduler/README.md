# Scheduler component (Phase 3)

Triggers `ingestion/run.py` on a schedule. **Does not** fetch, parse, chunk, or embed.

The FastAPI chat API (`app/main.py`) does not import this package. Ingestion runs offline; the API keeps serving the previous Chroma index until the ingestion job finishes and swaps `data/index/chroma/`.

## Daily at 10:00 AM IST (recommended)

India Standard Time (IST) is **UTC+5:30**, so **10:00 AM IST = 04:30 AM UTC**.

Add to `.env` (see `.env.example`):

```env
INGESTION_SCHEDULE_CRON=30 4 * * *
SCHEDULER_LOG_PATH=./data/logs/scheduler.log
```

Then run the APScheduler daemon:

```bash
# Linux / macOS
export PYTHONPATH=.
python scheduler/daily.py
```

```powershell
# Windows
$env:PYTHONPATH="."
python scheduler/daily.py
```

When `INGESTION_SCHEDULE_CRON` is set, it overrides `SCHEDULE_HOUR_UTC`. Cron fields are **minute hour day month day-of-week**, interpreted in **UTC**.

| Local time | UTC cron (`INGESTION_SCHEDULE_CRON`) |
|------------|--------------------------------------|
| 10:00 AM IST | `30 4 * * *` |
| 07:30 AM IST | `0 2 * * *` (same as `SCHEDULE_HOUR_UTC=2`) |

## Manual run (testing)

```bash
# From project root (set PYTHONPATH on Windows if needed)
set PYTHONPATH=.
python scheduler/daily.py --once

# Re-index only (no HTTP fetch)
python scheduler/daily.py --once --skip-fetch

# Child process isolation (same as cron wrapper)
python scheduler/daily.py --once --subprocess
```

## Dev: APScheduler daemon

```bash
# Default: daily at SCHEDULE_HOUR_UTC (default 02:00 UTC = 07:30 IST)
python scheduler/daily.py

# Or full cron expression (5 fields, UTC) — e.g. 10:00 AM IST
set INGESTION_SCHEDULE_CRON=30 4 * * *
python scheduler/daily.py
```

## Production options

### Linux: system cron (10:00 AM IST = 04:30 UTC)

```cron
# /etc/cron.d/hdfc-faq-ingestion
30 4 * * * cd /path/to/RAGChatbot && PYTHONPATH=. /path/to/.venv/bin/python scheduler/daily.py --once --subprocess >> /var/log/hdfc-faq-scheduler.log 2>&1
```

### Windows: Task Scheduler (10:00 AM local)

Run daily at **10:00 AM** in Task Scheduler (use your machine’s IST timezone):

```powershell
cd C:\path\to\RAGChatbot
$env:PYTHONPATH="."
.venv\Scripts\python scheduler/daily.py --once --subprocess
```

No cron env vars needed when the OS scheduler fires at local 10:00 AM.

## Environment

| Variable | Default | Purpose |
|----------|---------|---------|
| `SCHEDULE_HOUR_UTC` | `2` | Daily run hour (UTC) when cron expr not set (07:30 IST) |
| `INGESTION_SCHEDULE_CRON` | (empty) | 5-field cron override for APScheduler (**UTC**). Use `30 4 * * *` for 10:00 AM IST |
| `SCHEDULER_RETRY_ON_FAILURE` | `true` | Retry ingestion once on failure |
| `SCHEDULER_LOG_PATH` | (empty) | Append JSON job lines to this file |
| `USE_CACHE` | `false` | Forwarded when using `--use-cache` |

## Log format

Each job writes one JSON line to stdout (and optionally `SCHEDULER_LOG_PATH`):

```json
{"event": "scheduler_job", "status": "OK", "exit_code": 0, "chunks": 49, ...}
```
