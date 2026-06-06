"""Phase 1: Pydantic model validation."""

from datetime import date

import pytest
from pydantic import ValidationError

from app.models import ChatRequest, ChatResponse, ChunkRecord, SectionTag


def test_chat_request_strips_and_validates() -> None:
    req = ChatRequest(message="  What is the expense ratio?  ")
    assert req.message == "What is the expense ratio?"


def test_chat_request_rejects_empty() -> None:
    with pytest.raises(ValidationError):
        ChatRequest(message="   ")


def test_chat_response_factual_shape() -> None:
    resp = ChatResponse(
        answer="The expense ratio is 0.73%.",
        citation_url="https://groww.in/mutual-funds/hdfc-mid-cap-fund-direct-growth",
        last_updated="2026-06-01",
        is_refusal=False,
        disclaimer="Facts-only. No investment advice.",
    )
    assert resp.last_updated == date(2026, 6, 1)


def test_chunk_record_minimal() -> None:
    record = ChunkRecord(
        id="hdfc-mid-cap-fund-direct-growth#expense_ratio#0",
        text="Expense ratio: 0.73%",
        scheme_name="HDFC Mid Cap Fund Direct Growth",
        source_url="https://groww.in/mutual-funds/hdfc-mid-cap-fund-direct-growth",
        section=SectionTag.EXPENSE_RATIO,
        last_updated=date(2026, 6, 1),
    )
    assert record.manager_name is None
