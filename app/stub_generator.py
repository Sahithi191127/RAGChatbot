"""Stub answer generator from retrieved chunks (Phase 5 — replaced in Phase 6)."""

from __future__ import annotations

import re

from app.models import ScoredChunk, SectionTag


def _extract_body(chunk_text: str) -> str:
    parts = chunk_text.split("\n\n", 1)
    if len(parts) == 2:
        return parts[1].strip()
    return chunk_text.strip()


def _first_percent(text: str) -> str | None:
    match = re.search(r"(\d+(?:\.\d+)?%)", text)
    return match.group(1) if match else None


def generate_from_chunks(query: str, chunks: list[ScoredChunk]) -> str:
    """
    Produce a short factual draft from retrieved chunks (no LLM).

    Phase 6 replaces this with ``app/generator.py``.
    """
    del query  # section intent already applied in retrieval
    if not chunks:
        return "I could not find this information in the retrieved scheme content."

    top = chunks[0].chunk
    scheme = top.scheme_name

    if all(item.chunk.section == SectionTag.FUND_MANAGEMENT for item in chunks):
        names: list[str] = []
        for item in chunks:
            if item.chunk.manager_name and item.chunk.manager_name not in names:
                names.append(item.chunk.manager_name)
        if names:
            joined = ", ".join(names[:-1]) + f", and {names[-1]}" if len(names) > 1 else names[0]
            return (
                f"{scheme} is managed by {joined} according to the fund management section "
                "on the scheme page."
            )

    body = _extract_body(top.text)
    section = top.section.value.replace("_", " ")

    if top.section == SectionTag.EXPENSE_RATIO:
        ratio = _first_percent(body)
        if ratio:
            return f"The expense ratio for {scheme} is {ratio} as listed on the Groww scheme page."

    if top.section == SectionTag.EXIT_LOAD:
        return f"For {scheme}, the exit load stated on the scheme page is: {body}"

    if top.section == SectionTag.MINIMUM_INVESTMENT:
        return f"Minimum investment details for {scheme} on the scheme page: {body}"

    if top.section == SectionTag.BENCHMARK:
        return f"The benchmark for {scheme} is described on the scheme page as: {body}"

    if top.section == SectionTag.TAX:
        return f"Tax implications stated on the scheme page for {scheme}: {body}"

    return f"From the {section} section for {scheme}: {body}"
