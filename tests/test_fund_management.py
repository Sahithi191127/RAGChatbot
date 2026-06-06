"""Phase 9.1: fund management retrieval tests."""

from __future__ import annotations

import pytest

from app.models import SectionTag
from app.retriever import index_is_ready, retrieve

DEFENCE_SLUG = "hdfc-defence-fund-direct-growth"
GOLD_SLUG = "hdfc-gold-etf-fund-of-fund-direct-plan-growth"
SMALL_SLUG = "hdfc-small-cap-fund-direct-growth"


@pytest.fixture(scope="module")
def requires_index() -> None:
    if not index_is_ready():
        pytest.skip("Chroma index not built — run python ingestion/run.py first")


def test_defence_fund_all_three_managers(requires_index) -> None:
    result = retrieve("Who manages HDFC Defence Fund Direct Growth?")
    assert result.resolved_slug == DEFENCE_SLUG
    assert result.resolved_section == SectionTag.FUND_MANAGEMENT
    assert len(result.chunks) == 3
    managers = {item.chunk.manager_name for item in result.chunks}
    assert managers == {"Priya Ranjan", "Dhruv Muchhal", "Rahul Baijal"}


def test_gold_etf_fof_multiple_managers(requires_index) -> None:
    result = retrieve("Who manages HDFC Gold ETF Fund of Fund Direct Plan Growth?")
    assert result.resolved_slug == GOLD_SLUG
    assert len(result.chunks) >= 2
    assert all(item.chunk.section == SectionTag.FUND_MANAGEMENT for item in result.chunks)
    assert all(item.chunk.manager_name for item in result.chunks)


def test_small_cap_fund_manager(requires_index) -> None:
    result = retrieve("Who manages HDFC Small Cap Fund Direct Growth?")
    assert result.resolved_slug == SMALL_SLUG
    assert result.resolved_section == SectionTag.FUND_MANAGEMENT
    assert len(result.chunks) >= 1
    names = {item.chunk.manager_name for item in result.chunks}
    assert any(name for name in names)
