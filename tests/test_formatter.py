"""Phase 9.1: response formatter tests."""

from __future__ import annotations

from datetime import date

import pytest

from app.formatter import (
    _split_sentences,
    enforce_max_sentences,
    format_factual_answer,
)
from app.models import ChunkRecord, ScoredChunk, SectionTag
from config.loader import get_corpus_config, get_groww_citation_allowlist

MID_URL = "https://groww.in/mutual-funds/hdfc-mid-cap-fund-direct-growth"


def _chunk(section: SectionTag, text: str) -> ScoredChunk:
    return ScoredChunk(
        chunk=ChunkRecord(
            id=f"hdfc-mid-cap-fund-direct-growth#{section.value}#0",
            text=text,
            scheme_name="HDFC Mid Cap Fund Direct Growth",
            source_url=MID_URL,
            section=section,
            last_updated=date(2026, 6, 2),
        ),
        score=1.0,
    )


def test_enforce_max_three_sentences() -> None:
    text = "One. Two. Three. Four. Five."
    assert enforce_max_sentences(text, 3) == "One. Two. Three."


def test_enforce_max_sentences_preserves_decimal_percentages() -> None:
    text = "The expense ratio is 0.73%. It is listed on Groww. Updated today."
    result = enforce_max_sentences(text, 3)
    assert "0.73%" in result
    assert len(_split_sentences(result)) <= 3


def test_format_factual_answer_uses_chunk_citation() -> None:
    chunks = [
        _chunk(
            SectionTag.EXPENSE_RATIO,
            "Scheme: HDFC Mid Cap\nSection: expense_ratio\n\nExpense ratio: 0.73%",
        )
    ]
    response = format_factual_answer("The expense ratio is 0.73%.", chunks)
    assert str(response.citation_url) in get_groww_citation_allowlist()
    assert response.last_updated == date(2026, 6, 2)
    assert response.is_refusal is False
    assert response.disclaimer == get_corpus_config().disclaimer


def test_format_factual_answer_respects_sentence_cap() -> None:
    chunks = [_chunk(SectionTag.OVERVIEW, "Overview text.")]
    draft = "First. Second. Third. Fourth."
    response = format_factual_answer(draft, chunks)
    assert len(_split_sentences(response.answer)) <= 3
