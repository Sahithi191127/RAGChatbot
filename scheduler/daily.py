"""
Daily scheduler — triggers ``ingestion/run.py`` only (Phase 3).

The scheduler does not fetch, parse, chunk, or embed. The chat API never imports
this module; ingestion runs offline and swaps the index when complete.
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

from ingestion.models import IngestionRunResult
from ingestion.paths import PROJECT_ROOT
from scheduler.models import SchedulerJobResult, TriggerMode

logger = logging.getLogger(__name__)


def _retry_enabled() -> bool:
    return os.getenv("SCHEDULER_RETRY_ON_FAILURE", "true").lower() in ("1", "true", "yes")


def _schedule_hour_utc() -> int:
    raw = os.getenv("SCHEDULE_HOUR_UTC", "2")
    hour = int(raw)
    if not 0 <= hour <= 23:
        raise ValueError(f"SCHEDULE_HOUR_UTC must be 0-23, got {hour}")
    return hour


def _schedule_cron() -> str | None:
    value = os.getenv("INGESTION_SCHEDULE_CRON", "").strip()
    return value or None


def _log_path() -> Path | None:
    raw = os.getenv("SCHEDULER_LOG_PATH", "").strip()
    if not raw:
        return None
    path = Path(raw)
    if not path.is_absolute():
        path = PROJECT_ROOT / path
    return path


def format_job_log_line(result: SchedulerJobResult) -> str:
    """Single-line status for stdout or log file."""
    ingestion = result.ingestion
    payload = {
        "event": "scheduler_job",
        "status": "OK" if result.success else "FAILED",
        "exit_code": result.exit_code,
        "attempt_count": result.attempt_count,
        "trigger_mode": result.trigger_mode,
        "duration_s": round(result.duration_seconds, 2),
        "started_at": result.started_at.isoformat(),
        "finished_at": result.finished_at.isoformat(),
    }
    if ingestion is not None:
        payload.update(
            {
                "chunks": ingestion.chunk_count,
                "schemes_parsed": ingestion.schemes_parsed,
                "fetch_ok": ingestion.fetch_ok,
                "fetch_total": ingestion.fetch_total,
            }
        )
    if result.errors:
        payload["errors"] = result.errors
    return json.dumps(payload, ensure_ascii=False)


def append_job_log(result: SchedulerJobResult) -> None:
    line = format_job_log_line(result)
    logger.info("%s", line)
    log_path = _log_path()
    if log_path is None:
        return
    log_path.parent.mkdir(parents=True, exist_ok=True)
    with log_path.open("a", encoding="utf-8") as handle:
        handle.write(line + "\n")


def _run_ingestion_callable(
    *,
    use_cache: bool | None,
    skip_fetch: bool,
    skip_index: bool,
) -> IngestionRunResult:
    from ingestion.run import run_ingestion

    return run_ingestion(
        use_cache=use_cache,
        skip_fetch=skip_fetch,
        skip_index=skip_index,
    )


def _run_ingestion_subprocess(
    *,
    use_cache: bool,
    skip_fetch: bool,
    skip_index: bool,
) -> tuple[int, IngestionRunResult | None]:
    """Invoke ``ingestion/run.py`` in a child process; returns exit code."""
    script = PROJECT_ROOT / "ingestion" / "run.py"
    cmd = [sys.executable, str(script)]
    if use_cache:
        cmd.append("--use-cache")
    if skip_fetch:
        cmd.append("--skip-fetch")
    if skip_index:
        cmd.append("--skip-index")

    env = os.environ.copy()
    env.setdefault("PYTHONPATH", str(PROJECT_ROOT))

    completed = subprocess.run(
        cmd,
        cwd=str(PROJECT_ROOT),
        env=env,
        capture_output=False,
    )
    return completed.returncode, None


def trigger_ingestion(
    *,
    use_subprocess: bool = False,
    use_cache: bool | None = None,
    skip_fetch: bool = False,
    skip_index: bool = False,
    retry: bool | None = None,
) -> SchedulerJobResult:
    """
    Trigger one ingestion job (callable or subprocess).

    On failure, retries once when ``retry`` is True (default from env).
    """
    if retry is None:
        retry = _retry_enabled()

    trigger_mode: TriggerMode = "subprocess" if use_subprocess else "callable"
    started = datetime.now(timezone.utc)
    errors: list[str] = []
    ingestion: IngestionRunResult | None = None
    exit_code = 1
    attempt_count = 0
    max_attempts = 2 if retry else 1

    for attempt in range(1, max_attempts + 1):
        attempt_count = attempt
        errors.clear()
        try:
            if use_subprocess:
                use_cache_flag = use_cache if use_cache is not None else False
                exit_code, ingestion = _run_ingestion_subprocess(
                    use_cache=use_cache_flag,
                    skip_fetch=skip_fetch,
                    skip_index=skip_index,
                )
            else:
                ingestion = _run_ingestion_callable(
                    use_cache=use_cache,
                    skip_fetch=skip_fetch,
                    skip_index=skip_index,
                )
                exit_code = 0 if ingestion.success else 1
                if ingestion.errors:
                    errors.extend(ingestion.errors)
        except Exception as exc:
            logger.exception("Ingestion trigger failed on attempt %s", attempt)
            exit_code = 1
            errors.append(str(exc))

        if exit_code == 0:
            break
        if attempt < max_attempts:
            logger.warning("Ingestion failed (exit %s); retrying once", exit_code)

    finished = datetime.now(timezone.utc)
    success = exit_code == 0

    result = SchedulerJobResult(
        success=success,
        exit_code=exit_code,
        started_at=started,
        finished_at=finished,
        attempt_count=attempt_count,
        trigger_mode=trigger_mode,
        ingestion=ingestion,
        errors=errors,
    )
    append_job_log(result)
    return result


def _build_apscheduler_trigger():
    from apscheduler.triggers.cron import CronTrigger

    cron_expr = _schedule_cron()
    if cron_expr:
        parts = cron_expr.split()
        if len(parts) == 5:
            return CronTrigger(
                minute=parts[0],
                hour=parts[1],
                day=parts[2],
                month=parts[3],
                day_of_week=parts[4],
                timezone="UTC",
            )
        raise ValueError(
            f"INGESTION_SCHEDULE_CRON must be 5 fields (min hour day month dow), got: {cron_expr}"
        )

    hour = _schedule_hour_utc()
    return CronTrigger(hour=hour, minute=0, timezone="UTC")


def run_daemon(
    *,
    use_subprocess: bool = False,
    use_cache: bool | None = None,
) -> None:
    """Run APScheduler blocking loop (dev / single-process deployment)."""
    from apscheduler.schedulers.blocking import BlockingScheduler

    scheduler = BlockingScheduler(timezone="UTC")
    trigger = _build_apscheduler_trigger()

    def job() -> None:
        trigger_ingestion(use_subprocess=use_subprocess, use_cache=use_cache)

    scheduler.add_job(job, trigger=trigger, id="daily_ingestion", replace_existing=True)
    cron_expr = _schedule_cron()
    schedule_desc = cron_expr if cron_expr else f"daily at {_schedule_hour_utc():02d}:00 UTC"
    logger.info("Scheduler started — ingestion %s (APScheduler)", schedule_desc)
    scheduler.start()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Trigger ingestion on a schedule or once (does not serve chat API)",
    )
    parser.add_argument(
        "--once",
        action="store_true",
        help="Run a single ingestion job and exit (manual / cron wrapper)",
    )
    parser.add_argument(
        "--subprocess",
        action="store_true",
        help="Run ingestion/run.py in a child process instead of in-process call",
    )
    parser.add_argument(
        "--use-cache",
        action="store_true",
        help="Pass USE_CACHE=true behavior to ingestion (markdown from data/cache/)",
    )
    parser.add_argument("--skip-fetch", action="store_true", help="Forward to ingestion")
    parser.add_argument("--skip-index", action="store_true", help="Forward to ingestion")
    parser.add_argument(
        "--no-retry",
        action="store_true",
        help="Disable single retry on failure",
    )
    args = parser.parse_args(argv)

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )

    use_cache = True if args.use_cache else None
    if args.use_cache:
        os.environ["USE_CACHE"] = "true"

    if args.once:
        result = trigger_ingestion(
            use_subprocess=args.subprocess,
            use_cache=use_cache,
            skip_fetch=args.skip_fetch,
            skip_index=args.skip_index,
            retry=not args.no_retry,
        )
        print(
            f"Scheduler {'succeeded' if result.success else 'failed'}: "
            f"exit_code={result.exit_code} attempts={result.attempt_count} "
            f"duration={result.duration_seconds:.1f}s"
        )
        if result.ingestion:
            ing = result.ingestion
            print(
                f"  ingestion: chunks={ing.chunk_count} schemes={ing.schemes_parsed} "
                f"fetch={ing.fetch_ok}/{ing.fetch_total}"
            )
        return result.exit_code

    run_daemon(use_subprocess=args.subprocess, use_cache=use_cache)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
