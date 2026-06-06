"""Chunk ID conventions for vector store documents.

Formats (see DOCS/implementationplan.md Phase 1):

- General section: ``{slug}#{section}#{index}``
  Example: ``hdfc-mid-cap-fund-direct-growth#expense_ratio#0``

- Fund management (one chunk per manager when possible):
  ``{slug}#fund_management#{manager-slug}``
  Example: ``hdfc-defence-fund-direct-growth#fund_management#priya-ranjan``
"""

import re

from app.models import SectionTag


def slugify_manager_name(name: str) -> str:
    """Convert manager display name to a stable slug segment."""
    slug = name.lower().strip()
    slug = re.sub(r"[^a-z0-9]+", "-", slug)
    return slug.strip("-")


def build_chunk_id(slug: str, section: SectionTag | str, index: int) -> str:
    """Build ID for a generic section chunk."""
    section_value = section.value if isinstance(section, SectionTag) else section
    return f"{slug}#{section_value}#{index}"


def build_fund_management_chunk_id(slug: str, manager_name: str) -> str:
    """Build ID for a fund_management chunk tied to one manager."""
    return f"{slug}#{SectionTag.FUND_MANAGEMENT.value}#{slugify_manager_name(manager_name)}"


def parse_chunk_id(chunk_id: str) -> dict[str, str]:
    """Parse chunk ID into slug, section, and third segment (index or manager slug)."""
    parts = chunk_id.split("#", 2)
    if len(parts) != 3:
        raise ValueError(f"Invalid chunk id format: {chunk_id}")
    return {"slug": parts[0], "section": parts[1], "segment": parts[2]}
