"""Structured extraction from live Groww HTML pages."""

from __future__ import annotations

import re
from datetime import datetime, timezone

from bs4 import BeautifulSoup

from app.models import SchemeMetadata, SectionTag
from ingestion.models import (
    FundManagementSection,
    ManagerBlock,
    ParsedSchemeDocument,
    SectionContent,
)
from ingestion.text_utils import normalize_lines, parse_manager_blocks


def _strings(soup: BeautifulSoup) -> list[str]:
    return [s.strip() for s in soup.stripped_strings if s and s.strip()]


def _value_after_label(strings: list[str], label: str, max_lookahead: int = 4) -> str:
    for index, value in enumerate(strings):
        if value == label or value.startswith(label):
            for candidate in strings[index + 1 : index + 1 + max_lookahead]:
                if candidate != label and len(candidate) < 120:
                    return candidate
    return ""


def _first_match(strings: list[str], pattern: str) -> str:
    regex = re.compile(pattern, re.IGNORECASE)
    for value in strings:
        if regex.search(value):
            return value
    return ""


def _extract_overview_html(soup: BeautifulSoup, scheme: SchemeMetadata) -> str:
    parts: list[str] = [f"# {scheme.scheme_name}"]
    strings = _strings(soup)

    h1 = soup.find("h1")
    if h1:
        parent = h1.find_parent("div")
        if parent:
            local = [
                s.strip()
                for s in parent.get_text("\n", strip=True).split("\n")
                if s.strip()
            ][:12]
            for line in local:
                if line == scheme.scheme_name:
                    continue
                if line in ("1M", "6M", "1Y", "3Y", "5Y", "All"):
                    continue
                if re.match(r"^\+?-?\d+\.?\d*%", line):
                    continue
                if any(x in line for x in ("Vaishnavi", "©", "Stocks")):
                    break
                parts.append(line)

    nav = _first_match(strings, r"NAV:\s*")
    if nav:
        parts.append(nav)
    sip = _value_after_label(strings, "Min. for SIP")
    if sip:
        parts.append(f"Min. for SIP: ₹{sip}" if not sip.startswith("₹") else f"Min. for SIP: {sip}")
    aum = _value_after_label(strings, "Fund size (AUM)")
    if not aum:
        aum = _value_after_label(strings, "Fund size")
    if aum:
        parts.append(f"Fund size (AUM): {aum}")
    ratio = _value_after_label(strings, "Expense ratio")
    if ratio:
        parts.append(f"Expense ratio: {ratio}")

    return "\n".join(dict.fromkeys(parts))


def _extract_fund_management_html(soup: BeautifulSoup) -> FundManagementSection:
    heading = soup.find("h3", class_=re.compile("fundManagement_heading"))
    if not heading:
        return FundManagementSection(managers=[])

    container = heading.find_parent("div", class_=re.compile("fundManagement_container"))
    if not container:
        container = heading.parent
    lines = normalize_lines(container.get_text("\n", strip=True))
    managers = parse_manager_blocks(lines)
    return FundManagementSection(managers=managers)


def _extract_investment_objective_html(soup: BeautifulSoup) -> str:
    block = soup.find(class_=re.compile("investmentObjective_readMoreSection"))
    if block:
        title = block.find(class_=re.compile("investmentObjective_readMoreTitle"))
        body = block.find(class_=re.compile("bodyLarge"))
        if title and body:
            return f"{title.get_text(strip=True)}\n\n{body.get_text(strip=True)}"
    return ""


def _extract_benchmark_html(soup: BeautifulSoup) -> str:
    row = soup.find(class_=re.compile("investmentObjective_benchmarkRow"))
    if row:
        spans = [s.get_text(strip=True) for s in row.find_all("span")]
        if len(spans) >= 2:
            return f"Fund benchmark: {spans[-1]}"
    value = _value_after_label(_strings(soup), "Fund benchmark")
    return f"Fund benchmark: {value}" if value else ""


def _extract_fund_house_html(soup: BeautifulSoup) -> str:
    heading = soup.find(string=re.compile(r"^Fund house$", re.I))
    if not heading:
        return ""
    parent = heading.find_parent("div")
    if not parent:
        return ""
    lines = []
    for line in parent.get_text("\n", strip=True).split("\n"):
        if any(x in line for x in ("Home", "Vaishnavi", "©", "Mutual Funds :")):
            break
        if line.strip():
            lines.append(line.strip())
    return "\n".join(lines[:20])


def _extract_minimum_investment_html(soup: BeautifulSoup) -> str:
    strings = _strings(soup)
    parts = []
    for label in ("Min. for 1st investment", "Min. for 2nd investment", "Min. for SIP"):
        value = _value_after_label(strings, label)
        if value:
            parts.append(f"{label}: ₹{value}" if not value.startswith("₹") else f"{label}: {value}")
    return "\n".join(parts)


def parse_groww_html(
    html: str,
    scheme: SchemeMetadata,
    fetch_timestamp: datetime,
) -> ParsedSchemeDocument:
    """Build a parsed document from Groww scheme page HTML."""
    soup = BeautifulSoup(html, "html.parser")

    strings = _strings(soup)
    overview = _extract_overview_html(soup, scheme)
    expense_ratio_val = _value_after_label(strings, "Expense ratio")
    expense_text = (
        f"Expense ratio: {expense_ratio_val}"
        if expense_ratio_val
        else _first_match(strings, r"expense ratio")
    )

    exit_load = _first_match(strings, r"Exit load of .*redeemed within")
    tax = _first_match(strings, r"If you redeem within")

    sections: dict[str, SectionContent | FundManagementSection] = {
        SectionTag.OVERVIEW.value: SectionContent(text=overview),
        SectionTag.EXPENSE_RATIO.value: SectionContent(text=expense_text),
        SectionTag.EXIT_LOAD.value: SectionContent(text=exit_load),
        SectionTag.MINIMUM_INVESTMENT.value: SectionContent(
            text=_extract_minimum_investment_html(soup)
        ),
        SectionTag.BENCHMARK.value: SectionContent(text=_extract_benchmark_html(soup)),
        SectionTag.TAX.value: SectionContent(text=tax),
        SectionTag.FUND_MANAGEMENT.value: _extract_fund_management_html(soup),
        SectionTag.INVESTMENT_OBJECTIVE.value: SectionContent(
            text=_extract_investment_objective_html(soup)
        ),
        SectionTag.FUND_HOUSE.value: SectionContent(text=_extract_fund_house_html(soup)),
    }

    return ParsedSchemeDocument(
        slug=scheme.slug,
        scheme_name=scheme.scheme_name,
        source_url=str(scheme.source_url),
        category=scheme.category,
        fetch_timestamp=fetch_timestamp,
        parsed_at=datetime.now(timezone.utc),
        sections=sections,
    )
