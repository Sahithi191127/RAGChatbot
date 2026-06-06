"""Post-generation validation for LLM drafts (Phase 6)."""

from __future__ import annotations

import re

from app.formatter import _split_sentences, enforce_max_sentences
from app.models import ScoredChunk, SectionTag, ValidationResult
from config.loader import get_groww_citation_allowlist

_ADVISORY_IN_DRAFT = (
    r"\bi recommend\b",
    r"\byou should buy\b",
    r"\byou should sell\b",
    r"\bbuy this fund\b",
    r"\bsell this fund\b",
    r"\bbetter investment\b",
    r"\bgood time to invest\b",
)

_PERFORMANCE_IN_DRAFT = (
    r"\+\d+(?:\.\d+)?%",
    r"\b\d+(?:\.\d+)?%\s+returns?\b",
    r"\b\d+y\s+return",
    r"\bwill return\b",
    r"\bexpected return\b",
    r"\bcagr\b",
)

_URL_PATTERN = re.compile(r"https?://[^\s\])>]+")


def _combined_context(chunks: list[ScoredChunk]) -> str:
    return "\n".join(item.chunk.text.lower() for item in chunks)


def _sentence_count(text: str) -> int:
    return len(_split_sentences(text))


def _extract_percentages(text: str) -> set[str]:
    return set(re.findall(r"\d+(?:\.\d+)?%", text))


def _allowed_manager_names(chunks: list[ScoredChunk]) -> set[str]:
    names: set[str] = set()
    for item in chunks:
        if item.chunk.manager_name:
            names.add(item.chunk.manager_name.lower())
    return names


def _draft_mentions_unknown_manager(draft: str, chunks: list[ScoredChunk]) -> bool:
    fm_chunks = [item for item in chunks if item.chunk.section == SectionTag.FUND_MANAGEMENT]
    if not fm_chunks:
        return False
    allowed = _allowed_manager_names(chunks)
    if not allowed:
        return False
    draft_lower = draft.lower()
    if any(name in draft_lower for name in allowed):
        return False
    if "manager" in draft_lower or "managed by" in draft_lower:
        return True
    return False


def _draft_has_ungrounded_performance(draft: str, context: str) -> bool:
    draft_lower = draft.lower()
    for pattern in _PERFORMANCE_IN_DRAFT:
        for match in re.finditer(pattern, draft_lower):
            snippet = match.group(0)
            if snippet not in context:
                return True
    return False


def validate_draft(draft: str, chunks: list[ScoredChunk]) -> ValidationResult:
    """
    Validate an LLM draft before formatting.

    Returns ``should_refuse`` for advisory/comparison language in the draft.
    """
    issues: list[str] = []
    if not draft.strip():
        return ValidationResult(passed=False, issues=["empty_draft"])

    draft_clean = draft.strip()
    draft_lower = draft_clean.lower()
    context = _combined_context(chunks)

    for pattern in _ADVISORY_IN_DRAFT:
        if re.search(pattern, draft_lower):
            return ValidationResult(
                passed=False,
                should_refuse=True,
                issues=["advisory_language_in_draft"],
            )

    if _sentence_count(draft_clean) > 3:
        issues.append("too_many_sentences")

    for url in _URL_PATTERN.findall(draft_clean):
        if url not in get_groww_citation_allowlist():
            issues.append(f"invalid_citation_url:{url}")

    for pct in _extract_percentages(draft_clean):
        if pct not in context and pct.lower() not in context:
            issues.append(f"ungrounded_percentage:{pct}")

    if _draft_has_ungrounded_performance(draft_clean, context):
        issues.append("ungrounded_performance")

    if _draft_mentions_unknown_manager(draft_clean, chunks):
        issues.append("ungrounded_manager")

    suggested_citation = str(chunks[0].chunk.source_url) if chunks else None

    if issues:
        return ValidationResult(
            passed=False,
            issues=issues,
            suggested_citation_url=suggested_citation,
        )

    return ValidationResult(
        passed=True,
        suggested_citation_url=suggested_citation,
    )


def sanitize_draft(draft: str) -> str:
    """Strip URLs and enforce sentence cap before formatting."""
    text = _URL_PATTERN.sub("", draft)
    return enforce_max_sentences(text.strip(), max_sentences=3)
