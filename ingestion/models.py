"""Ingestion pipeline data structures."""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

from app.models import ChunkRecord, SectionTag


class FetchMeta(BaseModel):
    slug: str
    scheme_name: str
    source_url: str
    fetch_timestamp: datetime
    content_type: Literal["html", "markdown"]
    content_path: str
    from_cache: bool = False
    fetch_error: str | None = None


class FetchResult(BaseModel):
    slug: str
    success: bool
    meta: FetchMeta | None = None
    error: str | None = None


class ManagerBlock(BaseModel):
    name: str
    tenure: str = ""
    education: str = ""
    experience: str = ""
    also_manages: list[str] = Field(default_factory=list)
    text: str = ""


class SectionContent(BaseModel):
    text: str = ""


class FundManagementSection(BaseModel):
    managers: list[ManagerBlock] = Field(default_factory=list)


class ParsedSchemeDocument(BaseModel):
    slug: str
    scheme_name: str
    source_url: str
    category: str
    fetch_timestamp: datetime
    parsed_at: datetime
    sections: dict[str, SectionContent | FundManagementSection]

    def section_text(self, tag: SectionTag) -> str:
        block = self.sections.get(tag.value)
        if block is None:
            return ""
        if isinstance(block, FundManagementSection):
            return "\n\n".join(m.text for m in block.managers if m.text)
        return block.text


class IngestionRunResult(BaseModel):
    """Structured status returned by ``ingestion/run.py`` for scheduler and tests."""

    success: bool
    started_at: datetime
    finished_at: datetime
    fetch_ok: int = 0
    fetch_total: int = 0
    schemes_parsed: int = 0
    chunk_count: int = 0
    chunks_by_scheme: dict[str, int] = Field(default_factory=dict)
    chunks_by_section: dict[str, int] = Field(default_factory=dict)
    errors: list[str] = Field(default_factory=list)
    metadata_index_path: str | None = None
    chroma_path: str | None = None


class MetadataIndex(BaseModel):
    """``data/index/metadata.json`` — scheme index for retrieval (Phase 4)."""

    built_at: datetime
    embedding_model: str
    embedding_provider: str
    chunk_count: int
    collection_name: str
    schemes: list[dict[str, str | list[str] | None]]
