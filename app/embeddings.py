"""Query embeddings for retrieval (Phase 4)."""

from __future__ import annotations

import os

from app.settings import get_settings

BGE_QUERY_PREFIX = "Represent this sentence for searching relevant passages: "


def format_query_for_embedding(query: str, *, model_name: str | None = None) -> str:
    """Apply model-specific query prefix (BGE retrieval instruction)."""
    name = (model_name or os.getenv("EMBEDDING_MODEL", get_settings().embedding_model)).lower()
    text = query.strip()
    if "bge" in name and not text.lower().startswith(BGE_QUERY_PREFIX.lower()[:20]):
        return f"{BGE_QUERY_PREFIX}{text}"
    return text


def embed_query(query: str) -> list[float]:
    """Embed a user query with the same model used at index time."""
    from ingestion.index import embed_texts

    prefixed = format_query_for_embedding(query)
    vectors = embed_texts([prefixed])
    return vectors[0]
