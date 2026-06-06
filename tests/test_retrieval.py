"""Phase 4: metadata-first hybrid retrieval tests."""

from __future__ import annotations

import pytest

from app.models import SectionTag
from app.retriever import (
    detect_section_intent,
    index_is_ready,
    resolve_scheme,
    retrieve,
)

MID_SLUG = "hdfc-mid-cap-fund-direct-growth"
DEFENCE_SLUG = "hdfc-defence-fund-direct-growth"
GOLD_SLUG = "hdfc-gold-etf-fund-of-fund-direct-plan-growth"


@pytest.fixture(scope="module")
def requires_index() -> None:
    if not index_is_ready():
        pytest.skip("Chroma index not built — run python ingestion/run.py first")


# --- Stage 1: scheme resolution (no index) ---


def test_resolve_mid_cap_alias() -> None:
    resolution = resolve_scheme("What is the expense ratio for HDFC mid cap?")
    assert resolution.slug == MID_SLUG
    assert not resolution.out_of_scope
    assert not resolution.scheme_ambiguous


def test_resolve_defence_alias() -> None:
    resolution = resolve_scheme("exit load on defence fund")
    assert resolution.slug == DEFENCE_SLUG


def test_resolve_gold_fof_alias() -> None:
    resolution = resolve_scheme("Who manages gold etf fof?")
    assert resolution.slug == GOLD_SLUG


def test_resolve_out_of_scope_sbi() -> None:
    resolution = resolve_scheme("SBI Mid Cap expense ratio")
    assert resolution.out_of_scope
    assert resolution.slug is None


def test_resolve_ambiguous_no_scheme() -> None:
    resolution = resolve_scheme("What is the expense ratio?")
    assert resolution.scheme_ambiguous
    assert resolution.slug is None


def test_resolve_hdfc_only_ambiguous() -> None:
    resolution = resolve_scheme("Tell me about HDFC fund")
    assert resolution.scheme_ambiguous


# --- Stage 2: section intent ---


def test_detect_expense_ratio() -> None:
    assert detect_section_intent("expense ratio of mid cap") == SectionTag.EXPENSE_RATIO


def test_detect_fund_management() -> None:
    assert detect_section_intent("Who manages HDFC Defence Fund?") == SectionTag.FUND_MANAGEMENT


def test_detect_exit_load() -> None:
    assert detect_section_intent("exit load on defence fund") == SectionTag.EXIT_LOAD


# --- Stage 3: end-to-end retrieval (requires Chroma) ---


def test_retrieve_expense_mid_cap(requires_index) -> None:
    result = retrieve("Expense ratio HDFC Mid Cap")
    assert not result.out_of_scope
    assert not result.scheme_ambiguous
    assert result.resolved_slug == MID_SLUG
    assert result.resolved_section == SectionTag.EXPENSE_RATIO
    assert len(result.chunks) >= 1
    chunk = result.chunks[0].chunk
    assert chunk.section == SectionTag.EXPENSE_RATIO
    assert "%" in chunk.text
    assert result.chunks[0].score == 1.0


def test_retrieve_defence_all_managers(requires_index) -> None:
    result = retrieve("Who manages HDFC Defence Fund?")
    assert result.resolved_slug == DEFENCE_SLUG
    assert result.resolved_section == SectionTag.FUND_MANAGEMENT
    assert len(result.chunks) == 3
    managers = {item.chunk.manager_name for item in result.chunks}
    assert "Priya Ranjan" in managers
    assert "Dhruv Muchhal" in managers
    assert "Rahul Baijal" in managers


def test_retrieve_gold_fof_managers(requires_index) -> None:
    result = retrieve("Who manages HDFC Gold ETF Fund of Fund?")
    assert result.resolved_slug == GOLD_SLUG
    assert len(result.chunks) >= 2
    assert all(item.chunk.section == SectionTag.FUND_MANAGEMENT for item in result.chunks)


def test_retrieve_sbi_out_of_scope(requires_index) -> None:
    result = retrieve("SBI Mid Cap expense ratio")
    assert result.out_of_scope
    assert result.chunks == []


def test_retrieve_no_scheme_ambiguous(requires_index) -> None:
    result = retrieve("What is the expense ratio?")
    assert result.scheme_ambiguous
    assert result.chunks == []


def test_retrieve_exit_load_defence(requires_index) -> None:
    result = retrieve("exit load on HDFC defence fund")
    assert result.resolved_slug == DEFENCE_SLUG
    assert result.resolved_section == SectionTag.EXIT_LOAD
    assert len(result.chunks) == 1
    assert "exit load" in result.chunks[0].chunk.text.lower()
