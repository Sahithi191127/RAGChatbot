"""Filesystem paths for ingestion artifacts."""

from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "data"
RAW_DIR = DATA_DIR / "raw"
PROCESSED_DIR = DATA_DIR / "processed"
CACHE_DIR = DATA_DIR / "cache"
INDEX_DIR = DATA_DIR / "index"
CHROMA_STAGING_DIR = INDEX_DIR / "chroma_staging"
METADATA_INDEX_PATH = INDEX_DIR / "metadata.json"
COLLECTION_NAME = "hdfc_faq_corpus"


def chroma_path() -> Path:
    import os

    configured = os.getenv("CHROMA_PATH", "data/index/chroma")
    path = Path(configured)
    if not path.is_absolute():
        path = PROJECT_ROOT / path
    return path


def raw_html_path(slug: str) -> Path:
    return RAW_DIR / f"{slug}.html"


def raw_markdown_path(slug: str) -> Path:
    return RAW_DIR / f"{slug}.md"


def raw_meta_path(slug: str) -> Path:
    return RAW_DIR / f"{slug}.meta.json"


def cache_markdown_path(slug: str) -> Path:
    return CACHE_DIR / f"{slug}.md"


def processed_json_path(slug: str) -> Path:
    return PROCESSED_DIR / f"{slug}.json"


def processed_chunks_path(slug: str) -> Path:
    return PROCESSED_DIR / f"{slug}.chunks.json"


def ensure_ingestion_dirs() -> None:
    for directory in (RAW_DIR, PROCESSED_DIR, CACHE_DIR, INDEX_DIR):
        directory.mkdir(parents=True, exist_ok=True)
