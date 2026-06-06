"""Phase 9.3: scheduler smoke test (ingestion trigger, no fetch/embed in scheduler)."""

from __future__ import annotations

from datetime import datetime, timezone

import pytest

from pathlib import Path

from ingestion.models import IngestionRunResult
from scheduler.daily import trigger_ingestion


def _successful_run() -> IngestionRunResult:
    now = datetime.now(timezone.utc)
    return IngestionRunResult(
        success=True,
        started_at=now,
        finished_at=now,
        fetch_ok=5,
        fetch_total=5,
        schemes_parsed=5,
        chunk_count=49,
        chunks_by_scheme={"hdfc-mid-cap-fund-direct-growth": 10},
        chunks_by_section={"expense_ratio": 5},
    )


def test_scheduler_once_triggers_ingestion(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[dict] = []

    def fake_run(**kwargs):
        calls.append(kwargs)
        return _successful_run()

    monkeypatch.setattr("scheduler.daily._run_ingestion_callable", fake_run)
    result = trigger_ingestion(retry=False)
    assert result.success
    assert result.exit_code == 0
    assert len(calls) == 1


def test_chat_api_independent_of_scheduler() -> None:
    """Regression: app.main must not import scheduler or ingestion."""
    source = Path("app/main.py").read_text(encoding="utf-8")
    assert "scheduler" not in source
    assert "ingestion" not in source
