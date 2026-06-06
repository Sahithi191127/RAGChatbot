"""Post-parse cleaning for all schemes (markdown and HTML sources)."""

from __future__ import annotations

import re

from app.models import SectionTag
from ingestion.models import FundManagementSection, ManagerBlock, ParsedSchemeDocument, SectionContent

_FOOTER_PATTERNS = (
    "Vaishnavi Tech Park",
    "© 2016",
    "Share Market",
    "Bug Bounty",
    "Terms and Conditions",
    "Privacy Policy",
    "Download the App",
    "Show More",
    "NSEBSEMCX",
    "Mutual Funds :",
    "Stocks :",
    "Invest in Stocks",
    "GROWW",
)

_NOISE_LINE_PATTERNS = (
    r"^\|",
    r"^Monthly investment",
    r"^Monthly SIP",
    r"^Rating$",
    r"^##### Expense ratio$",
    r"^### Minimum investments",
    r"^### Return calculator",
    r"^See All$",
    r"^View details$",
    r"^Check past data$",
)


def _drop_footer_lines(text: str) -> str:
    lines = []
    for line in text.splitlines():
        if any(marker in line for marker in _FOOTER_PATTERNS):
            continue
        lines.append(line)
    return "\n".join(lines).strip()


def _drop_noise_lines(text: str) -> str:
    lines = []
    for line in text.splitlines():
        if any(re.match(pat, line.strip()) for pat in _NOISE_LINE_PATTERNS):
            continue
        lines.append(line)
    return "\n".join(lines).strip()


def clean_expense_ratio(text: str, overview_text: str = "") -> str:
    text = _drop_noise_lines(text)
    ratio_match = re.search(r"(\d+(?:\.\d+)?%)", text)
    if ratio_match and "Expense ratio" not in text.splitlines()[0]:
        prefix = f"Expense ratio: {ratio_match.group(1)}"
        rest = re.sub(r"^\d+(?:\.\d+)?%\s*", "", text).strip()
        return f"{prefix}\n\n{rest}".strip() if rest else prefix
    if not text.strip() and overview_text:
        match = re.search(r"Expense ratio[:\s]*(\d+(?:\.\d+)?%)", overview_text, re.I)
        if match:
            return f"Expense ratio: {match.group(1)}"
    return text


def clean_minimum_investment(text: str) -> str:
    lines = []
    capture = False
    for line in text.splitlines():
        if "Minimum investment" in line or line.startswith("Min. for"):
            capture = True
        if capture:
            if line.startswith("##### ") or line.startswith("### Exit"):
                break
            lines.append(line)
    return _drop_noise_lines("\n".join(lines))


def clean_overview(text: str, scheme_name: str) -> str:
    text = _drop_footer_lines(text)
    lines = []
    for line in text.splitlines():
        if line.startswith("|"):
            continue
        if line in ("1M", "6M", "1Y", "3Y", "5Y", "All"):
            continue
        if re.match(r"^\+?-?\d+\.?\d*%", line.strip()):
            continue
        lines.append(line)
    cleaned = "\n".join(lines).strip()
    if scheme_name.lower() not in cleaned.lower():
        cleaned = f"# {scheme_name}\n\n{cleaned}".strip()
    return cleaned


def _manager_display_text(manager: ManagerBlock) -> str:
    parts = [f"{manager.name} — Fund Manager, {manager.tenure}".strip(", ")]
    if manager.education:
        parts.append(f"Education: {manager.education}")
    if manager.experience:
        parts.append(f"Experience: {manager.experience}")
    return "\n".join(parts)


def clean_fund_management(section: FundManagementSection) -> FundManagementSection:
    cleaned_managers: list[ManagerBlock] = []
    for manager in section.managers:
        if not manager.name.strip():
            continue
        text = _manager_display_text(manager)
        cleaned_managers.append(
            manager.model_copy(
                update={
                    "also_manages": [],
                    "text": text,
                }
            )
        )
    return FundManagementSection(managers=cleaned_managers)


def clean_parsed_document(document: ParsedSchemeDocument) -> ParsedSchemeDocument:
    """Apply corpus-wide cleaning rules to a parsed scheme document."""
    overview_raw = ""
    if SectionTag.OVERVIEW.value in document.sections:
        block = document.sections[SectionTag.OVERVIEW.value]
        if isinstance(block, SectionContent):
            overview_raw = block.text

    new_sections: dict = {}
    for key, block in document.sections.items():
        if key == SectionTag.OVERVIEW.value and isinstance(block, SectionContent):
            new_sections[key] = SectionContent(
                text=clean_overview(block.text, document.scheme_name)
            )
        elif key == SectionTag.EXPENSE_RATIO.value and isinstance(block, SectionContent):
            new_sections[key] = SectionContent(
                text=clean_expense_ratio(block.text, overview_raw)
            )
        elif key == SectionTag.MINIMUM_INVESTMENT.value and isinstance(block, SectionContent):
            new_sections[key] = SectionContent(text=clean_minimum_investment(block.text))
        elif key == SectionTag.FUND_MANAGEMENT.value and isinstance(block, FundManagementSection):
            new_sections[key] = clean_fund_management(block)
        elif key == SectionTag.FUND_HOUSE.value and isinstance(block, SectionContent):
            new_sections[key] = SectionContent(text=_drop_footer_lines(block.text))
        elif key == SectionTag.BENCHMARK.value and isinstance(block, SectionContent):
            new_sections[key] = SectionContent(text=_drop_noise_lines(block.text))
        elif isinstance(block, SectionContent):
            new_sections[key] = SectionContent(text=_drop_noise_lines(_drop_footer_lines(block.text)))
        else:
            new_sections[key] = block

    return document.model_copy(update={"sections": new_sections})
