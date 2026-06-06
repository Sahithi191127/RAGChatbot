"""Section-first chunking for parsed scheme documents (Phase 2.3)."""

from __future__ import annotations

import json
import logging
from collections import Counter
from app.models import ChunkRecord, SectionTag
from config.chunk_ids import build_chunk_id, build_fund_management_chunk_id
from config.loader import get_corpus_config
from ingestion.models import FundManagementSection, ParsedSchemeDocument, SectionContent
from ingestion.parse import load_processed_document
from ingestion.paths import ensure_ingestion_dirs, processed_chunks_path

logger = logging.getLogger(__name__)

# ~400 tokens at ~4 chars/token; overlap ~50 tokens
MAX_CHUNK_CHARS = 1600
OVERLAP_CHARS = 200


def estimate_tokens(text: str) -> int:
    return max(1, len(text) // 4)


def format_chunk_text(
    *,
    scheme_name: str,
    section: SectionTag,
    source_url: str,
    body: str,
    manager_name: str | None = None,
) -> str:
    lines = [
        f"Scheme: {scheme_name}",
        f"Section: {section.value}",
        f"Source: {source_url}",
    ]
    if manager_name:
        lines.append(f"Manager: {manager_name}")
    lines.append("")
    lines.append(body.strip())
    return "\n".join(lines)


def split_text_within_section(
    text: str,
    *,
    max_chars: int = MAX_CHUNK_CHARS,
    overlap_chars: int = OVERLAP_CHARS,
) -> list[str]:
    """Split long section text; overlap stays inside the same section only."""
    text = text.strip()
    if not text:
        return []
    if len(text) <= max_chars:
        return [text]

    parts: list[str] = []
    start = 0
    while start < len(text):
        end = min(start + max_chars, len(text))
        if end < len(text):
            window = text[start:end]
            break_at = window.rfind("\n\n")
            if break_at < max_chars // 2:
                break_at = window.rfind(". ")
            if break_at < max_chars // 2:
                break_at = window.rfind(" ")
            if break_at > 0:
                end = start + break_at + 1

        piece = text[start:end].strip()
        if piece:
            parts.append(piece)
        if end >= len(text):
            break
        start = max(end - overlap_chars, start + 1)

    return parts


def chunk_document(document: ParsedSchemeDocument) -> list[ChunkRecord]:
    """Build ``ChunkRecord`` list from one parsed scheme document."""
    last_updated = document.fetch_timestamp.date()
    source_url = document.source_url
    chunks: list[ChunkRecord] = []

    for section_tag in SectionTag:
        block = document.sections.get(section_tag.value)
        if block is None:
            continue

        if section_tag == SectionTag.FUND_MANAGEMENT:
            if not isinstance(block, FundManagementSection):
                continue
            for manager in block.managers:
                body = manager.text.strip()
                if not body:
                    continue
                chunk_id = build_fund_management_chunk_id(document.slug, manager.name)
                chunks.append(
                    ChunkRecord(
                        id=chunk_id,
                        text=format_chunk_text(
                            scheme_name=document.scheme_name,
                            section=section_tag,
                            source_url=source_url,
                            body=body,
                            manager_name=manager.name,
                        ),
                        scheme_name=document.scheme_name,
                        source_url=source_url,  # type: ignore[arg-type]
                        section=section_tag,
                        last_updated=last_updated,
                        manager_name=manager.name,
                    )
                )
            continue

        if not isinstance(block, SectionContent):
            continue
        body = block.text.strip()
        if not body:
            continue

        for index, part in enumerate(
            split_text_within_section(body, max_chars=MAX_CHUNK_CHARS, overlap_chars=OVERLAP_CHARS)
        ):
            chunks.append(
                ChunkRecord(
                    id=build_chunk_id(document.slug, section_tag, index),
                    text=format_chunk_text(
                        scheme_name=document.scheme_name,
                        section=section_tag,
                        source_url=source_url,
                        body=part,
                    ),
                    scheme_name=document.scheme_name,
                    source_url=source_url,  # type: ignore[arg-type]
                    section=section_tag,
                    last_updated=last_updated,
                )
            )

    return chunks


def chunk_scheme(slug: str, *, write: bool = True) -> list[ChunkRecord]:
    document = load_processed_document(slug)
    chunks = chunk_document(document)
    if write:
        ensure_ingestion_dirs()
        path = processed_chunks_path(slug)
        payload = [c.model_dump(mode="json") for c in chunks]
        path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        logger.info("Wrote %s chunks to %s", len(chunks), path)
    return chunks


def chunk_all_schemes(*, write: bool = True) -> list[ChunkRecord]:
    config = get_corpus_config()
    all_chunks: list[ChunkRecord] = []
    for scheme in config.schemes:
        try:
            all_chunks.extend(chunk_scheme(scheme.slug, write=write))
        except FileNotFoundError:
            logger.warning("Skipping chunk for %s (not parsed)", scheme.slug)
    return all_chunks


def summarize_chunks(chunks: list[ChunkRecord]) -> tuple[dict[str, int], dict[str, int]]:
    by_scheme: Counter[str] = Counter()
    by_section: Counter[str] = Counter()
    for chunk in chunks:
        slug = chunk.id.split("#", 1)[0]
        by_scheme[slug] += 1
        by_section[chunk.section.value] += 1
    return dict(by_scheme), dict(by_section)
