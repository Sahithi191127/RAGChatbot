"""Load and validate corpus configuration from YAML."""

from functools import lru_cache
from pathlib import Path

import yaml

from app.models import CorpusConfig, CorpusSummary, SchemeMetadata, SectionTag

_DEFAULT_CORPUS_PATH = Path(__file__).resolve().parent / "corpus.yaml"
_EXPECTED_SCHEME_COUNT = 5


class CorpusConfigError(Exception):
    """Raised when corpus.yaml fails validation."""


def _corpus_path(path: Path | None) -> Path:
    return path if path is not None else _DEFAULT_CORPUS_PATH


def load_corpus_config(path: Path | None = None) -> CorpusConfig:
    """Load corpus.yaml and return a validated CorpusConfig."""
    corpus_path = _corpus_path(path)
    if not corpus_path.is_file():
        raise CorpusConfigError(f"Corpus file not found: {corpus_path}")

    with corpus_path.open(encoding="utf-8") as handle:
        raw = yaml.safe_load(handle)

    if not isinstance(raw, dict):
        raise CorpusConfigError("corpus.yaml must be a mapping")

    try:
        return CorpusConfig.model_validate(raw)
    except Exception as exc:
        raise CorpusConfigError(f"Invalid corpus configuration: {exc}") from exc


@lru_cache
def get_corpus_config() -> CorpusConfig:
    """Cached corpus config for runtime use."""
    return load_corpus_config()


def get_groww_citation_allowlist(path: Path | None = None) -> frozenset[str]:
    """URLs allowed for factual answer citations (five Groww scheme pages)."""
    config = load_corpus_config(path) if path else get_corpus_config()
    return frozenset(str(scheme.source_url) for scheme in config.schemes)


def get_refusal_citation_allowlist(path: Path | None = None) -> frozenset[str]:
    """URLs allowed for refusal / educational citations (AMFI, SEBI)."""
    config = load_corpus_config(path) if path else get_corpus_config()
    return frozenset(
        {
            str(config.refusal_urls.amfi),
            str(config.refusal_urls.sebi),
        }
    )


def get_all_citation_allowlist(path: Path | None = None) -> frozenset[str]:
    """Union of Groww factual URLs and refusal URLs."""
    return get_groww_citation_allowlist(path) | get_refusal_citation_allowlist(path)


def is_groww_citation(url: str, path: Path | None = None) -> bool:
    return url in get_groww_citation_allowlist(path)


def is_refusal_citation(url: str, path: Path | None = None) -> bool:
    return url in get_refusal_citation_allowlist(path)


def get_scheme_by_slug(slug: str, path: Path | None = None) -> SchemeMetadata | None:
    config = load_corpus_config(path) if path else get_corpus_config()
    for scheme in config.schemes:
        if scheme.slug == slug:
            return scheme
    return None


def resolve_scheme_from_text(text: str, path: Path | None = None) -> SchemeMetadata | None:
    """Best-effort scheme resolution from user query (delegates to Phase 4 retriever)."""
    del path  # corpus path override not applied in retriever yet
    from app.retriever import resolve_scheme

    resolution = resolve_scheme(text)
    if resolution.out_of_scope or resolution.scheme_ambiguous:
        return None
    return resolution.scheme


def get_corpus_summary(path: Path | None = None) -> CorpusSummary:
    config = load_corpus_config(path) if path else get_corpus_config()
    return CorpusSummary(
        amc=config.amc,
        scheme_count=len(config.schemes),
        scheme_slugs=[s.slug for s in config.schemes],
        citation_allowlist_count=len(get_groww_citation_allowlist(path)),
        refusal_allowlist_count=len(get_refusal_citation_allowlist(path)),
    )


def clear_corpus_cache() -> None:
    """Clear cached config (for tests)."""
    get_corpus_config.cache_clear()
