"""Shared Pydantic models for API, ingestion, and vector store."""

from datetime import date, datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field, HttpUrl, field_validator


class SectionTag(str, Enum):
    """Logical section tags aligned with Groww page structure."""

    OVERVIEW = "overview"
    EXPENSE_RATIO = "expense_ratio"
    EXIT_LOAD = "exit_load"
    MINIMUM_INVESTMENT = "minimum_investment"
    BENCHMARK = "benchmark"
    TAX = "tax"
    FUND_MANAGEMENT = "fund_management"
    INVESTMENT_OBJECTIVE = "investment_objective"
    FUND_HOUSE = "fund_house"


class SchemeMetadata(BaseModel):
    """Per-scheme metadata index entry."""

    slug: str
    scheme_name: str
    category: str
    source_url: HttpUrl
    aliases: list[str] = Field(default_factory=list)
    last_fetched_at: date | None = None


class RefusalUrls(BaseModel):
    """Fixed AMFI/SEBI links for refusal responses."""

    amfi: HttpUrl
    sebi: HttpUrl


class CorpusConfig(BaseModel):
    """Loaded from config/corpus.yaml."""

    amc: str
    sections: list[SectionTag]
    refusal_urls: RefusalUrls
    disclaimer: str
    schemes: list[SchemeMetadata]

    @field_validator("sections", mode="before")
    @classmethod
    def coerce_sections(cls, value: list[str]) -> list[SectionTag]:
        return [SectionTag(v) if isinstance(v, str) else v for v in value]

    @field_validator("schemes")
    @classmethod
    def validate_scheme_count(cls, schemes: list[SchemeMetadata]) -> list[SchemeMetadata]:
        if len(schemes) != 5:
            raise ValueError(f"Corpus must contain exactly 5 schemes, got {len(schemes)}")
        slugs = [s.slug for s in schemes]
        if len(slugs) != len(set(slugs)):
            raise ValueError("Duplicate scheme slugs in corpus")
        urls = [str(s.source_url) for s in schemes]
        if len(urls) != len(set(urls)):
            raise ValueError("Duplicate source_url values in corpus")
        return schemes


class ChunkRecord(BaseModel):
    """Vector store document / processed chunk."""

    id: str
    text: str
    scheme_name: str
    source_url: HttpUrl
    section: SectionTag
    last_updated: date
    manager_name: str | None = None
    embedding: list[float] | None = None

    model_config = {"extra": "forbid"}


class ChatRequest(BaseModel):
    """POST /api/chat body."""

    message: str = Field(..., min_length=1)

    model_config = {"extra": "ignore"}

    @field_validator("message")
    @classmethod
    def strip_message(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("message must not be empty or whitespace only")
        return stripped


class SchemeListItem(BaseModel):
    """Scheme summary for ``GET /api/schemes``."""

    slug: str
    scheme_name: str
    category: str
    source_url: HttpUrl
    aliases: list[str] = Field(default_factory=list)


class ChatResponse(BaseModel):
    """Structured chat API response."""

    answer: str
    citation_url: HttpUrl | None = None
    last_updated: date
    is_refusal: bool
    disclaimer: str

    @field_validator("last_updated", mode="before")
    @classmethod
    def coerce_last_updated(cls, value: date | datetime | str) -> date:
        if isinstance(value, datetime):
            return value.date()
        if isinstance(value, str):
            return date.fromisoformat(value[:10])
        return value


class CorpusSummary(BaseModel):
    """Lightweight corpus info for health/debug endpoints."""

    amc: str
    scheme_count: int
    scheme_slugs: list[str]
    citation_allowlist_count: int
    refusal_allowlist_count: int


class ScoredChunk(BaseModel):
    """Retrieved chunk with similarity score (Phase 4)."""

    chunk: ChunkRecord
    score: float = Field(ge=0.0, le=1.0)


class RetrievalResult(BaseModel):
    """Output of ``app.retriever.retrieve``."""

    chunks: list[ScoredChunk] = Field(default_factory=list)
    resolved_slug: str | None = None
    resolved_section: SectionTag | None = None
    scheme_ambiguous: bool = False
    out_of_scope: bool = False
    insufficient_context: bool = False
    index_unavailable: bool = False


class ValidationResult(BaseModel):
    """Post-generation validation outcome (Phase 6)."""

    passed: bool
    should_refuse: bool = False
    issues: list[str] = Field(default_factory=list)
    suggested_citation_url: str | None = None
