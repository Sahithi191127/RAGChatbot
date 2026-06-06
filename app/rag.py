"""RAG orchestrator: classify → retrieve → generate → validate → format."""

from __future__ import annotations

import logging
from collections.abc import Callable

from app.classifier import ClassificationResult, QueryLabel, classify_query
from app.formatter import format_factual_answer
from app.generator import generate_answer, link_only_fallback, use_stub_generation
from app.models import ChatResponse, RetrievalResult, ScoredChunk, ValidationResult
from app.refusal import (
    build_insufficient_context_response,
    build_refusal_response,
    build_scheme_ambiguous_response,
    build_unrelated_response,
    build_unsupported_scheme_response,
)
from app.retriever import retrieve
from app.stub_generator import generate_from_chunks
from app.validator import sanitize_draft, validate_draft

logger = logging.getLogger(__name__)

_REFUSAL_LABELS = frozenset(
    {QueryLabel.ADVISORY, QueryLabel.COMPARISON, QueryLabel.PERFORMANCE}
)

MAX_GENERATION_ATTEMPTS = 2


def _labels_requiring_refusal(label: QueryLabel) -> bool:
    return label in _REFUSAL_LABELS


def _call_generate(
    message: str,
    chunks: list[ScoredChunk],
    *,
    generate_fn: Callable[[str, list[ScoredChunk]], str] | None,
    feedback: str | None,
) -> str:
    if generate_fn is not None:
        return generate_fn(message, chunks)
    return generate_answer(message, chunks, feedback=feedback)


def _generate_with_validation(
    message: str,
    chunks: list[ScoredChunk],
    *,
    generate_fn: Callable[[str, list[ScoredChunk]], str] | None = None,
    validate_fn: Callable[[str, list[ScoredChunk]], ValidationResult] | None = None,
) -> ChatResponse:
    validator = validate_fn or validate_draft
    feedback: str | None = None

    for attempt in range(MAX_GENERATION_ATTEMPTS):
        draft = _call_generate(
            message, chunks, generate_fn=generate_fn, feedback=feedback
        )
        clean = sanitize_draft(draft)
        validation = validator(clean, chunks)

        if validation.should_refuse:
            logger.info("draft_refused label=advisory issues=%s", validation.issues)
            return build_refusal_response(QueryLabel.ADVISORY)

        if validation.passed:
            return format_factual_answer(
                clean,
                chunks,
                citation_url=validation.suggested_citation_url,
            )

        feedback = "; ".join(validation.issues)
        logger.warning("validation_failed attempt=%s issues=%s", attempt + 1, feedback)

    if use_stub_generation():
        clean = sanitize_draft(generate_from_chunks(message, chunks))
        validation = validator(clean, chunks)
        return format_factual_answer(
            clean,
            chunks,
            citation_url=validation.suggested_citation_url,
        )

    clean = sanitize_draft(link_only_fallback(chunks))
    validation = validator(clean, chunks)
    return format_factual_answer(
        clean,
        chunks,
        citation_url=validation.suggested_citation_url,
    )


def chat(
    message: str,
    *,
    retrieve_fn: Callable[[str], RetrievalResult] | None = None,
    generate_fn: Callable[[str, list[ScoredChunk]], str] | None = None,
    validate_fn: Callable[[str, list[ScoredChunk]], ValidationResult] | None = None,
) -> ChatResponse:
    """
    Process one user message and return a structured ``ChatResponse``.

    Optional hooks support tests (Phase 5–6).
    """
    classification = classify_query(message)
    logger.info("query_class=%s reason=%s", classification.label.value, classification.reason)

    if _labels_requiring_refusal(classification.label):
        return build_refusal_response(classification.label)

    if classification.label == QueryLabel.UNSUPPORTED_SCHEME:
        return build_unsupported_scheme_response()

    if classification.label == QueryLabel.UNRELATED:
        return build_unrelated_response()

    retriever = retrieve_fn or retrieve
    retrieval = retriever(message)

    if retrieval.out_of_scope:
        return build_unsupported_scheme_response()

    if retrieval.scheme_ambiguous:
        return build_scheme_ambiguous_response()

    if retrieval.index_unavailable:
        return build_insufficient_context_response()

    if retrieval.insufficient_context or not retrieval.chunks:
        citation = None
        if retrieval.resolved_slug:
            from config.loader import get_scheme_by_slug

            scheme = get_scheme_by_slug(retrieval.resolved_slug)
            if scheme:
                citation = str(scheme.source_url)
        return build_insufficient_context_response(citation)

    return _generate_with_validation(
        message,
        retrieval.chunks,
        generate_fn=generate_fn,
        validate_fn=validate_fn,
    )


def classify_only(message: str) -> ClassificationResult:
    """Expose classification without retrieval (tests / logging)."""
    return classify_query(message)
