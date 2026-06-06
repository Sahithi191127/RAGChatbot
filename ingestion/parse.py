"""Parse raw Groww HTML or cached markdown into structured sections."""

from __future__ import annotations

import json
import logging
import re
from datetime import datetime, timezone

from bs4 import BeautifulSoup

from app.models import SchemeMetadata, SectionTag
from config.loader import get_corpus_config, get_scheme_by_slug
from ingestion.clean import clean_parsed_document
from ingestion.fetch import load_fetch_meta, read_raw_content
from ingestion.html_extract import parse_groww_html
from ingestion.models import (
    FundManagementSection,
    ParsedSchemeDocument,
    SectionContent,
)
from ingestion.paths import ensure_ingestion_dirs, processed_json_path
from ingestion.text_utils import normalize_lines as _normalize_lines
from ingestion.text_utils import parse_manager_blocks as _parse_manager_blocks

logger = logging.getLogger(__name__)

# Sections stripped from FAQ corpus (noise on Groww pages)
_SKIP_SECTION_MARKERS = (
    "### Return calculator",
    "## Holdings",
    "### Returns and rankings",
    "## Understand terms",
    "### Compare similar funds",
    "See All",
)


def _html_to_markdown_lines(html: str) -> list[str]:
    soup = BeautifulSoup(html, "html.parser")
    for tag in soup(["script", "style", "noscript", "svg", "header", "footer", "nav"]):
        tag.decompose()

    lines: list[str] = []
    for element in soup.find_all(["h1", "h2", "h3", "h4", "h5", "p", "li", "span"]):
        text = element.get_text(" ", strip=True)
        if not text or len(text) < 2:
            continue
        if element.name and element.name.startswith("h"):
            level = int(element.name[1])
            lines.append(f"{'#' * level} {text}")
        elif element.name == "li":
            lines.append(f"- {text}")
        else:
            lines.append(text)
    return lines


def _slice_lines(lines: list[str], start: str, *end_markers: str) -> list[str]:
    start_idx = None
    for index, line in enumerate(lines):
        if line.startswith(start) or line == start.strip("# ").strip():
            start_idx = index
            break
    if start_idx is None:
        return []

    end_idx = len(lines)
    for index in range(start_idx + 1, len(lines)):
        line = lines[index]
        for marker in end_markers:
            if line.startswith(marker) or marker in line:
                end_idx = index
                break
        if end_idx != len(lines):
            break

    return lines[start_idx:end_idx]


def _clean_section_text(section_lines: list[str]) -> str:
    cleaned: list[str] = []
    for line in section_lines:
        if any(marker in line for marker in _SKIP_SECTION_MARKERS):
            continue
        if line.startswith("|") and "---" in line:
            continue
        if line.startswith("| ") and cleaned and cleaned[-1].startswith("|"):
            continue
        if line in ("View details", "Check past data", "See All"):
            continue
        cleaned.append(line)
    text = "\n".join(cleaned).strip()
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text


def _extract_overview(lines: list[str], scheme_name: str) -> str:
    title = f"# {scheme_name}"
    block = _slice_lines(
        lines,
        title,
        "### Return calculator",
        "## Holdings",
    )
    if not block and lines:
        for index, line in enumerate(lines):
            if scheme_name.lower() in line.lower():
                block = lines[index : index + 40]
                break

    overview_lines: list[str] = []
    for line in block:
        if line.startswith("#"):
            if scheme_name.lower() not in line.lower():
                continue
            overview_lines.append(line)
            continue
        if line.startswith("### Return calculator"):
            break
        if line.startswith("|"):
            continue
        if line in ("1M", "6M", "1Y", "3Y", "5Y", "All", "Monthly SIPOne time"):
            continue
        if re.match(r"^\+?-?\d+\.?\d*%", line):
            continue
        if line.startswith("Monthly investment"):
            continue
        overview_lines.append(line)

    return _clean_section_text(overview_lines)


def _extract_expense_ratio(lines: list[str], overview_text: str) -> str:
    ratio_value = ""
    for index, line in enumerate(lines):
        if line == "Expense ratio" and index + 1 < len(lines):
            candidate = lines[index + 1].strip()
            if re.match(r"^\d+(\.\d+)?%$", candidate):
                ratio_value = candidate
                break

    definition = _slice_lines(lines, "##### Expense ratio", "##### ")
    definition_text = _clean_section_text(definition)

    parts = []
    if ratio_value:
        parts.append(f"Expense ratio: {ratio_value}")
    if definition_text:
        parts.append(definition_text)
    if parts:
        return "\n\n".join(parts)

    match = re.search(r"Expense ratio[:\s]+(\d+\.?\d*%)", overview_text, re.IGNORECASE)
    if match:
        return f"Expense ratio: {match.group(1)}"
    return ""


def _extract_minimum_investment(lines: list[str]) -> str:
    block = _slice_lines(
        lines,
        "### Minimum investments",
        "## Understand terms",
        "### Returns and rankings",
        "### Exit load",
    )
    return _clean_section_text(block)


def _extract_exit_load(lines: list[str]) -> str:
    block = _slice_lines(
        lines,
        "### Exit load, stamp duty and tax",
        "### Compare similar funds",
        "### Fund management",
    )
    if not block:
        block = _slice_lines(lines, "### Exit Load", "### ")
    exit_lines = []
    capture = False
    for line in block:
        if line.startswith("#### Exit load"):
            capture = True
            continue
        if capture and line.startswith("#### "):
            break
        if capture:
            exit_lines.append(line)
    text = _clean_section_text(exit_lines)
    if not text:
        text = _clean_section_text(block)
    return text


def _extract_tax(lines: list[str]) -> str:
    block = _slice_lines(
        lines,
        "### Exit load, stamp duty and tax",
        "### Compare similar funds",
        "### Fund management",
    )
    tax_lines: list[str] = []
    capture = False
    for line in block:
        if line.startswith("#### Tax implication"):
            capture = True
            continue
        if capture and line.startswith("#### "):
            break
        if capture:
            tax_lines.append(line)
    return _clean_section_text(tax_lines)


def _extract_benchmark(lines: list[str]) -> str:
    for line in lines:
        match = re.match(r"Fund benchmark\s*:?\s*(.+)", line, re.IGNORECASE)
        if match and match.group(1).strip():
            return f"Fund benchmark: {match.group(1).strip()}"
    return ""


def _extract_investment_objective(lines: list[str]) -> str:
    block = _slice_lines(
        lines,
        "#### Investment Objective",
        "Fund benchmark",
        "### Fund house",
    )
    return _clean_section_text(block)


def _extract_about_and_objective(lines: list[str], scheme_name: str) -> str:
    marker = f"### About {scheme_name}"
    block = _slice_lines(lines, marker, "### Fund house", "Home>")
    return _clean_section_text(block)


def _extract_fund_house(lines: list[str]) -> str:
    block = _slice_lines(lines, "### Fund house", "Home>", "Vaishnavi Tech Park")
    if not block:
        block = _slice_lines(lines, "### Fund house", "GROWW", "© ")
    return _clean_section_text(block)


def _extract_fund_management(lines: list[str], scheme_name: str) -> FundManagementSection:
    block = _slice_lines(
        lines,
        "### Fund management",
        f"### About {scheme_name}",
        "### Fund house",
    )
    managers = _parse_manager_blocks(block)
    return FundManagementSection(managers=managers)


def parse_lines_to_document(
    lines: list[str],
    scheme: SchemeMetadata,
    fetch_timestamp: datetime,
) -> ParsedSchemeDocument:
    scheme_name = scheme.scheme_name
    overview_text = _extract_overview(lines, scheme_name)
    objective_from_about = _extract_about_and_objective(lines, scheme_name)
    objective_heading = _extract_investment_objective(lines)
    investment_objective = objective_heading or objective_from_about

    sections: dict[str, SectionContent | FundManagementSection] = {
        SectionTag.OVERVIEW.value: SectionContent(text=overview_text),
        SectionTag.EXPENSE_RATIO.value: SectionContent(
            text=_extract_expense_ratio(lines, overview_text)
        ),
        SectionTag.EXIT_LOAD.value: SectionContent(text=_extract_exit_load(lines)),
        SectionTag.MINIMUM_INVESTMENT.value: SectionContent(
            text=_extract_minimum_investment(lines)
        ),
        SectionTag.BENCHMARK.value: SectionContent(text=_extract_benchmark(lines)),
        SectionTag.TAX.value: SectionContent(text=_extract_tax(lines)),
        SectionTag.FUND_MANAGEMENT.value: _extract_fund_management(lines, scheme_name),
        SectionTag.INVESTMENT_OBJECTIVE.value: SectionContent(text=investment_objective),
        SectionTag.FUND_HOUSE.value: SectionContent(text=_extract_fund_house(lines)),
    }

    return ParsedSchemeDocument(
        slug=scheme.slug,
        scheme_name=scheme_name,
        source_url=str(scheme.source_url),
        category=scheme.category,
        fetch_timestamp=fetch_timestamp,
        parsed_at=datetime.now(timezone.utc),
        sections=sections,
    )


def parse_content(
    content: str,
    scheme: SchemeMetadata,
    fetch_timestamp: datetime,
    *,
    content_type: str = "markdown",
) -> ParsedSchemeDocument:
    if content_type == "html":
        document = parse_groww_html(content, scheme, fetch_timestamp)
    else:
        lines = _normalize_lines(content)
        if lines and lines[0].startswith("Source URL:"):
            lines = lines[2:] if len(lines) > 2 and lines[1].startswith("Title:") else lines[1:]
        document = parse_lines_to_document(lines, scheme, fetch_timestamp)
    return clean_parsed_document(document)


def parse_scheme(slug: str, *, write: bool = True) -> ParsedSchemeDocument:
    """Parse raw content for ``slug`` and optionally write ``data/processed/{slug}.json``."""
    scheme = get_scheme_by_slug(slug)
    if scheme is None:
        raise ValueError(f"Unknown scheme slug: {slug}")

    content, meta = read_raw_content(slug)
    document = parse_content(
        content,
        scheme,
        meta.fetch_timestamp,
        content_type=meta.content_type,
    )

    if write:
        ensure_ingestion_dirs()
        output_path = processed_json_path(slug)
        output_path.write_text(
            document.model_dump_json(indent=2),
            encoding="utf-8",
        )
        logger.info("Wrote processed document: %s", output_path)

    return document


def parse_all_schemes(*, write: bool = True) -> list[ParsedSchemeDocument]:
    config = get_corpus_config()
    documents: list[ParsedSchemeDocument] = []
    for scheme in config.schemes:
        try:
            load_fetch_meta(scheme.slug)
        except FileNotFoundError:
            logger.warning("Skipping parse for %s (not fetched)", scheme.slug)
            continue
        documents.append(parse_scheme(scheme.slug, write=write))
    return documents


def load_processed_document(slug: str) -> ParsedSchemeDocument:
    path = processed_json_path(slug)
    if not path.is_file():
        raise FileNotFoundError(f"No processed document for {slug}: {path}")
    return ParsedSchemeDocument.model_validate_json(path.read_text(encoding="utf-8"))
