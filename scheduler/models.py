"""Scheduler job status models (Phase 3)."""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

from ingestion.models import IngestionRunResult

TriggerMode = Literal["callable", "subprocess"]


class SchedulerJobResult(BaseModel):
    """Result of a scheduler-triggered ingestion job."""

    success: bool
    exit_code: int
    started_at: datetime
    finished_at: datetime
    attempt_count: int = 1
    trigger_mode: TriggerMode = "callable"
    ingestion: IngestionRunResult | None = None
    errors: list[str] = Field(default_factory=list)

    @property
    def duration_seconds(self) -> float:
        return (self.finished_at - self.started_at).total_seconds()
