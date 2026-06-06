"""Format factual answers into ``ChatResponse`` (Phase 5.3)."""

from __future__ import annotations

import re
from datetime import date

from app.models import ChatResponse, ScoredChunk
from config.loader import get_corpus_config


def _split_sentences(text: str) -> list[str]:
    parts = re.split(r"(?<=[.!?])\s+", text.strip())
    return [part.strip() for part in parts if part.strip()]


def enforce_max_sentences(text: str, max_sentences: int = 3) -> str:
    sentences = _split_sentences(text)
    if not sentences:
        return text.strip()
    return " ".join(sentences[:max_sentences])


def _extract_body(chunk_text: str) -> str:
    """Return chunk body after the metadata header block."""
    parts = chunk_text.split("\n\n", 1)
    if len(parts) == 2:
        return parts[1].strip()
    return chunk_text.strip()


def _max_last_updated(chunks: list[ScoredChunk]) -> date:
    if not chunks:
        return date.today()
    return max(item.chunk.last_updated for item in chunks)


def _primary_citation_url(chunks: list[ScoredChunk]) -> str:
    if not chunks:
        config = get_corpus_config()
        return str(config.schemes[0].source_url)
    return str(chunks[0].chunk.source_url)


def format_factual_answer(
    draft_answer: str,
    chunks: list[ScoredChunk],
    *,
    citation_url: str | None = None,
) -> ChatResponse:
    """
    Build ``ChatResponse`` for a factual path.

    Enforces ≤3 sentences, one citation URL, disclaimer, and ``last_updated`` from chunks.
    """
    config = get_corpus_config()
    answer = enforce_max_sentences(draft_answer, max_sentences=3)
    last_updated = _max_last_updated(chunks)
    citation = citation_url or _primary_citation_url(chunks)
    return ChatResponse(
        answer=answer,
        citation_url=citation,
        last_updated=last_updated,
        is_refusal=False,
        disclaimer=config.disclaimer,
    )


def format_answer_with_footer(draft_answer: str, chunks: list[ScoredChunk]) -> ChatResponse:
    """Same as ``format_factual_answer``; footer date is exposed via ``last_updated`` field."""
    return format_factual_answer(draft_answer, chunks)
