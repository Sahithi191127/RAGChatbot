"""LLM answer generation via Groq OpenAI-compatible API (Phase 6)."""

from __future__ import annotations

import logging
import re
from typing import Any

from app.models import ScoredChunk, SectionTag
from app.settings import get_settings
from app.stub_generator import generate_from_chunks

logger = logging.getLogger(__name__)

MAX_CHUNKS_IN_PROMPT = 5
MAX_TOKENS = 256

SYSTEM_PROMPT = """You are a facts-only mutual fund FAQ assistant for five HDFC schemes on Groww.

Rules:
- Answer ONLY using the provided context chunks. If context is insufficient, say so briefly.
- Maximum 3 short sentences. No bullet lists.
- Do NOT give investment advice, buy/sell/hold recommendations, or opinions.
- Do NOT compare funds or predict returns.
- Do NOT invent numbers, manager names, or URLs not present in the context.
- Do NOT include URLs in your answer (citation is added separately).
- Use plain English."""

GROQ_DEFAULT_BASE_URL = "https://api.groq.com/openai/v1"


def use_stub_generation() -> bool:
    settings = get_settings()
    return settings.use_llm_stub or not settings.llm_api_key.strip()


def _build_context_block(chunks: list[ScoredChunk]) -> str:
    lines: list[str] = []
    for index, item in enumerate(chunks[:MAX_CHUNKS_IN_PROMPT], start=1):
        chunk = item.chunk
        lines.append(f"[Chunk {index}]")
        lines.append(f"Scheme: {chunk.scheme_name}")
        lines.append(f"Section: {chunk.section.value}")
        lines.append(f"Source: {chunk.source_url}")
        lines.append(f"Last updated: {chunk.last_updated.isoformat()}")
        if chunk.manager_name:
            lines.append(f"Manager: {chunk.manager_name}")
        lines.append(chunk.text)
        lines.append("")
    return "\n".join(lines).strip()


def _create_llm_client() -> Any:
    from openai import OpenAI

    settings = get_settings()
    base_url = settings.llm_base_url.strip() or GROQ_DEFAULT_BASE_URL
    return OpenAI(api_key=settings.llm_api_key, base_url=base_url)


def generate_answer(
    query: str,
    chunks: list[ScoredChunk],
    *,
    client: Any | None = None,
    feedback: str | None = None,
) -> str:
    """
    Generate a draft answer from retrieved chunks.

    Uses Groq when ``LLM_API_KEY`` is set and ``USE_LLM_STUB`` is false; otherwise stub.
    """
    if use_stub_generation():
        return generate_from_chunks(query, chunks)

    if not chunks:
        return "I could not find this information in the retrieved scheme content."

    context = _build_context_block(chunks)
    user_parts = [
        f"Context:\n{context}",
        f"\nUser question: {query}",
        "\nWrite a factual answer in at most 3 sentences using only the context above.",
    ]
    if feedback:
        user_parts.append(f"\nPrevious answer failed validation: {feedback}")
        user_parts.append("Regenerate a corrected answer.")
    user_message = "".join(user_parts)

    try:
        llm_client = client or _create_llm_client()
    except ModuleNotFoundError:
        logger.warning("openai package not installed; falling back to stub generation")
        return generate_from_chunks(query, chunks)

    settings = get_settings()

    try:
        response = llm_client.chat.completions.create(
            model=settings.llm_model,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_message},
            ],
            temperature=0.0,
            max_tokens=MAX_TOKENS,
        )
    except Exception as exc:
        logger.exception("Groq LLM call failed: %s", exc)
        return generate_from_chunks(query, chunks)

    content = response.choices[0].message.content
    if not content or not content.strip():
        return generate_from_chunks(query, chunks)

    return _strip_urls(content.strip())


def _strip_urls(text: str) -> str:
    return re.sub(r"https?://\S+", "", text).strip()


def link_only_fallback(chunks: list[ScoredChunk]) -> str:
    """Fallback when validation fails after retry (GEN-10)."""
    if not chunks:
        return (
            "I could not verify a fully grounded answer from the retrieved content. "
            "Please refer to the official scheme documentation."
        )
    scheme = chunks[0].chunk.scheme_name
    return (
        f"I could not verify a fully grounded answer for {scheme}. "
        "Please see the linked Groww scheme page for the published facts."
    )
