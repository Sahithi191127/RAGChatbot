"""Phase 3: scheduler triggers ingestion only."""

from __future__ import annotations

import ast
import json
from datetime import datetime, timezone
from pathlib import Path

import pytest

from ingestion.models import IngestionRunResult
from scheduler.daily import (
    format_job_log_line,
    trigger_ingestion,
)
from scheduler.models import SchedulerJobResult


def _fake_ingestion_result(*, success: bool = True) -> IngestionRunResult:
    now = datetime.now(timezone.utc)
    return IngestionRunResult(
        success=success,
        started_at=now,
        finished_at=now,
        fetch_ok=5,
        fetch_total=5,
        schemes_parsed=5,
        chunk_count=49,
        chunks_by_scheme={"hdfc-mid-cap-fund-direct-growth": 10},
        chunks_by_section={"expense_ratio": 5},
    )


def test_scheduler_module_has_no_fetch_or_embed_logic() -> None:
    source = (Path("scheduler") / "daily.py").read_text(encoding="utf-8")
    tree = ast.parse(source)
    names = {
        node.id
        for node in ast.walk(tree)
        if isinstance(node, ast.Name)
    }
    assert "BeautifulSoup" not in names
    assert "chromadb" not in names
    assert "SentenceTransformer" not in names
    assert "fetch_all_schemes" not in names
    assert "parse_all_schemes" not in names
    assert "chunk_all_schemes" not in names
    assert "index_chunks" not in names


def test_app_main_does_not_import_scheduler_or_ingestion() -> None:
    source = Path("app/main.py").read_text(encoding="utf-8")
    assert "scheduler" not in source
    assert "ingestion" not in source


def test_trigger_ingestion_success(monkeypatch) -> None:
    monkeypatch.setattr(
        "scheduler.daily._run_ingestion_callable",
        lambda **kwargs: _fake_ingestion_result(success=True),
    )
    result = trigger_ingestion(retry=False)
    assert result.success
    assert result.exit_code == 0
    assert result.trigger_mode == "callable"
    assert result.attempt_count == 1
    assert result.ingestion is not None
    assert result.ingestion.chunk_count == 49


def test_trigger_ingestion_retries_once(monkeypatch) -> None:
    outcomes = [_fake_ingestion_result(success=False), _fake_ingestion_result(success=True)]

    def side_effect(**kwargs):
        return outcomes.pop(0)

    monkeypatch.setattr("scheduler.daily._run_ingestion_callable", side_effect)

    result = trigger_ingestion(retry=True)
    assert result.success
    assert result.attempt_count == 2


def test_trigger_ingestion_fails_after_retry(monkeypatch) -> None:
    monkeypatch.setattr(
        "scheduler.daily._run_ingestion_callable",
        lambda **kwargs: _fake_ingestion_result(success=False),
    )
    result = trigger_ingestion(retry=True)
    assert not result.success
    assert result.exit_code == 1
    assert result.attempt_count == 2


def test_format_job_log_line_json() -> None:
    now = datetime.now(timezone.utc)
    job = SchedulerJobResult(
        success=True,
        exit_code=0,
        started_at=now,
        finished_at=now,
        ingestion=_fake_ingestion_result(),
    )
    line = format_job_log_line(job)
    payload = json.loads(line)
    assert payload["event"] == "scheduler_job"
    assert payload["status"] == "OK"
    assert payload["chunks"] == 49


def test_schedule_hour_validation(monkeypatch) -> None:
    monkeypatch.setenv("SCHEDULE_HOUR_UTC", "25")
    from scheduler.daily import _schedule_hour_utc

    with pytest.raises(ValueError):
        _schedule_hour_utc()


def test_cli_once_invokes_trigger(monkeypatch) -> None:
    captured: list[bool] = []

    def fake_trigger(**kwargs):
        captured.append(kwargs.get("retry", True))
        return SchedulerJobResult(
            success=True,
            exit_code=0,
            started_at=datetime.now(timezone.utc),
            finished_at=datetime.now(timezone.utc),
            ingestion=_fake_ingestion_result(),
        )

    monkeypatch.setattr("scheduler.daily.trigger_ingestion", fake_trigger)
    from scheduler.daily import main

    assert main(["--once", "--no-retry"]) == 0
    assert captured == [False]
