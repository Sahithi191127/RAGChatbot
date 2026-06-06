"""Scheduler component — triggers ingestion (Phase 3)."""

from scheduler.daily import trigger_ingestion
from scheduler.models import SchedulerJobResult

__all__ = ["SchedulerJobResult", "trigger_ingestion"]