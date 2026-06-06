"""
Metadata-first hybrid retrieval (Phase 4).

Stage 1: scheme resolution (rules)
Stage 2: section intent (keyword rules)
Stage 3: Chroma metadata get, then slug-scoped semantic fallback
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from datetime import date
from functools import lru_cache
from typing import Any

import chromadb

from app.embeddings import embed_query
from app.models import ChunkRecord, RetrievalResult, ScoredChunk, SchemeMetadata, SectionTag
from app.settings import get_settings
from config.loader import get_corpus_config
from config.chunk_ids import slugify_manager_name
from ingestion.index import load_metadata_index
from ingestion.paths import COLLECTION_NAME, chroma_path

logger = logging.getLogger(__name__)

TOP_K = 5
FM_MAX_CHUNKS = 5
MIN_SIMILARITY = 0.35
SECTION_SCORE_BOOST = 1.2
SCHEME_SCORE_MARGIN = 10

OTHER_AMC_MARKERS = (
    "sbi",
    "axis mutual",
    "axis fund",
    "icici",
    "nippon",
    "bandhan",
    "kotak",
    "uti mutual",
    "franklin",
    "mirae",
    "parag parikh",
    "motilal",
    "dsp mutual",
    "aditya birla",
)

SECTION_KEYWORDS: list[tuple[SectionTag, tuple[str, ...]]] = [
    (
        SectionTag.FUND_MANAGEMENT,
        (
            "fund manager",
            "fund managers",
            "who manages",
            "who manage",
            "portfolio manager",
            "managed by",
            "manager's education",
            "manager education",
            "manager experience",
            "tenure of",
            "since when",
        ),
    ),
    (SectionTag.EXPENSE_RATIO, ("expense ratio", "ter", "total expense ratio")),
    (SectionTag.EXIT_LOAD, ("exit load", "redemption charge", "exit fee")),
    (
        SectionTag.MINIMUM_INVESTMENT,
        (
            "minimum investment",
            "min investment",
            "min sip",
            "minimum sip",
            "min lumpsum",
            "first investment",
            "second investment",
        ),
    ),
    (SectionTag.BENCHMARK, ("benchmark", "benchmark index", "tracks")),
    (SectionTag.TAX, ("tax implication", "stcg", "ltcg", "capital gains tax", "taxed")),
    (SectionTag.INVESTMENT_OBJECTIVE, ("investment objective", "objective of")),
    (SectionTag.FUND_HOUSE, ("fund house", "amc name", "asset management company")),
    (
        SectionTag.OVERVIEW,
        ("nav", "aum", "fund size", "riskometer", "category", "rating"),
    ),
]


@dataclass
class SchemeResolution:
    slug: str | None = None
    scheme: SchemeMetadata | None = None
    scheme_ambiguous: bool = False
    out_of_scope: bool = False


@lru_cache
def _get_chroma_collection() -> chromadb.Collection:
    settings = get_settings()
    path = chroma_path()
    if not path.is_dir():
        raise FileNotFoundError(f"Chroma path not found: {path}")
    client = chromadb.PersistentClient(path=str(path))
    return client.get_collection(name=COLLECTION_NAME)


def clear_retriever_cache() -> None:
    """Clear cached Chroma client (for tests)."""
    _get_chroma_collection.cache_clear()


def _normalize_query(query: str) -> str:
    return re.sub(r"\s+", " ", query.lower().strip())


def _mentions_other_amc_without_hdfc(normalized: str) -> bool:
    if "hdfc" in normalized:
        return False
    return any(marker in normalized for marker in OTHER_AMC_MARKERS)


def _score_scheme(scheme: SchemeMetadata, normalized: str) -> int:
    score = 0
    slug_spaced = scheme.slug.replace("-", " ")
    if scheme.slug in normalized or slug_spaced in normalized:
        score = max(score, 100)
    name = scheme.scheme_name.lower()
    if name in normalized:
        score = max(score, 80)
    for alias in sorted(scheme.aliases, key=len, reverse=True):
        alias_lower = alias.lower()
        if alias_lower in normalized:
            score = max(score, 60 + len(alias_lower))
    return score


def resolve_scheme(query: str) -> SchemeResolution:
    """Stage 1: resolve one of five corpus schemes or set flags."""
    normalized = _normalize_query(query)
    if _mentions_other_amc_without_hdfc(normalized):
        return SchemeResolution(out_of_scope=True)

    config = get_corpus_config()
    scored: list[tuple[SchemeMetadata, int]] = []
    for scheme in config.schemes:
        value = _score_scheme(scheme, normalized)
        if value > 0:
            scored.append((scheme, value))

    if not scored:
        return SchemeResolution(scheme_ambiguous=True)

    scored.sort(key=lambda item: item[1], reverse=True)
    top_scheme, top_score = scored[0]
    if len(scored) > 1 and scored[1][1] >= top_score - SCHEME_SCORE_MARGIN:
        return SchemeResolution(scheme_ambiguous=True)

    return SchemeResolution(slug=top_scheme.slug, scheme=top_scheme)


def detect_section_intent(query: str) -> SectionTag | None:
    """Stage 2: keyword-based section detection (specific rules first)."""
    normalized = _normalize_query(query)
    for section, keywords in SECTION_KEYWORDS:
        for keyword in keywords:
            if keyword in normalized:
                return section
    return None


def _metadata_where(slug: str, section: str | None = None) -> dict[str, Any]:
    if section is None:
        return {"slug": slug}
    return {"$and": [{"slug": slug}, {"section": section}]}


def _distance_to_score(distance: float) -> float:
    return max(0.0, min(1.0, 1.0 - distance))


def _row_to_chunk_record(
    chunk_id: str,
    document: str | None,
    metadata: dict[str, str],
) -> ChunkRecord:
    manager = metadata.get("manager_name") or None
    if manager == "":
        manager = None
    return ChunkRecord(
        id=chunk_id,
        text=document or "",
        scheme_name=metadata["scheme_name"],
        source_url=metadata["source_url"],
        section=SectionTag(metadata["section"]),
        last_updated=date.fromisoformat(metadata["last_updated"][:10]),
        manager_name=manager,
    )


def _get_by_metadata(slug: str, section: str | None = None) -> list[ScoredChunk]:
    collection = _get_chroma_collection()
    result = collection.get(where=_metadata_where(slug, section), include=["documents", "metadatas"])
    scored: list[ScoredChunk] = []
    ids = result.get("ids") or []
    documents = result.get("documents") or []
    metadatas = result.get("metadatas") or []
    for chunk_id, document, metadata in zip(ids, documents, metadatas, strict=True):
        chunk = _row_to_chunk_record(chunk_id, document, metadata)
        scored.append(ScoredChunk(chunk=chunk, score=1.0))
    return scored


def _query_semantic(
    query: str,
    slug: str,
    *,
    k: int = TOP_K,
    boost_section: SectionTag | None = None,
) -> list[ScoredChunk]:
    collection = _get_chroma_collection()
    embedding = embed_query(query)
    result = collection.query(
        query_embeddings=[embedding],
        n_results=k,
        where={"slug": slug},
        include=["documents", "metadatas", "distances"],
    )
    scored: list[ScoredChunk] = []
    ids = (result.get("ids") or [[]])[0]
    documents = (result.get("documents") or [[]])[0]
    metadatas = (result.get("metadatas") or [[]])[0]
    distances = (result.get("distances") or [[]])[0]
    for chunk_id, document, metadata, distance in zip(
        ids, documents, metadatas, distances, strict=True
    ):
        chunk = _row_to_chunk_record(chunk_id, document, metadata)
        score = _distance_to_score(float(distance))
        if boost_section and chunk.section == boost_section:
            score = min(1.0, score * SECTION_SCORE_BOOST)
        scored.append(ScoredChunk(chunk=chunk, score=score))
    scored.sort(key=lambda item: item.score, reverse=True)
    return scored


def _filter_manager_chunks(chunks: list[ScoredChunk], query: str) -> list[ScoredChunk]:
    normalized = _normalize_query(query)
    named = [
        item
        for item in chunks
        if item.chunk.manager_name and item.chunk.manager_name.lower() in normalized
    ]
    if named:
        return named[:FM_MAX_CHUNKS]
    slug_matches = []
    for item in chunks:
        if not item.chunk.manager_name:
            continue
        if slugify_manager_name(item.chunk.manager_name) in normalized.replace(" ", "-"):
            slug_matches.append(item)
    if slug_matches:
        return slug_matches[:FM_MAX_CHUNKS]
    return chunks[:FM_MAX_CHUNKS]


def retrieve(query: str) -> RetrievalResult:
    """
    Retrieve chunks for a factual user query.

    Returns empty ``chunks`` with flags when scheme is ambiguous, out of corpus,
    index is missing, or similarity is below threshold.
    """
    scheme_resolution = resolve_scheme(query)
    if scheme_resolution.out_of_scope:
        return RetrievalResult(out_of_scope=True)
    if scheme_resolution.scheme_ambiguous or scheme_resolution.slug is None:
        return RetrievalResult(scheme_ambiguous=True)

    slug = scheme_resolution.slug
    section = detect_section_intent(query)

    try:
        if section == SectionTag.FUND_MANAGEMENT:
            chunks = _get_by_metadata(slug, SectionTag.FUND_MANAGEMENT.value)
            chunks = _filter_manager_chunks(chunks, query)
            return RetrievalResult(
                chunks=chunks,
                resolved_slug=slug,
                resolved_section=section,
            )

        if section is not None:
            chunks = _get_by_metadata(slug, section.value)
            if chunks:
                return RetrievalResult(
                    chunks=chunks,
                    resolved_slug=slug,
                    resolved_section=section,
                )

        chunks = _query_semantic(query, slug, k=TOP_K, boost_section=section)
        if not chunks or chunks[0].score < MIN_SIMILARITY:
            return RetrievalResult(
                chunks=[],
                resolved_slug=slug,
                resolved_section=section,
                insufficient_context=True,
            )
        return RetrievalResult(
            chunks=chunks,
            resolved_slug=slug,
            resolved_section=section,
        )
    except FileNotFoundError as exc:
        logger.error("Retrieval index unavailable: %s", exc)
        return RetrievalResult(index_unavailable=True)
    except Exception as exc:
        logger.exception("Retrieval failed")
        return RetrievalResult(insufficient_context=True, resolved_slug=slug, resolved_section=section)


def index_chunk_count() -> int:
    """Return number of documents in the Chroma collection (health/debug)."""
    return _get_chroma_collection().count()


def index_is_ready() -> bool:
    try:
        return index_chunk_count() > 0
    except Exception:
        return False
