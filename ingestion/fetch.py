"""Fetch Groww scheme pages or load cached markdown snapshots."""

from __future__ import annotations

import json
import logging
import os
import shutil
from datetime import datetime, timezone

import httpx

from app.models import SchemeMetadata
from config.loader import get_corpus_config
from ingestion.models import FetchMeta, FetchResult
from ingestion.paths import (
    PROJECT_ROOT,
    cache_markdown_path,
    ensure_ingestion_dirs,
    raw_html_path,
    raw_markdown_path,
    raw_meta_path,
)

logger = logging.getLogger(__name__)

DEFAULT_USER_AGENT = (
    "Mozilla/5.0 (compatible; HDFC-FAQ-Bot/0.1; +https://github.com/local/RAGChatbot)"
)
FETCH_TIMEOUT_SECONDS = float(os.getenv("FETCH_TIMEOUT_SECONDS", "30"))


def _use_cache() -> bool:
    return os.getenv("USE_CACHE", "false").lower() in ("1", "true", "yes")


def _write_meta(meta: FetchMeta) -> None:
    raw_meta_path(meta.slug).write_text(
        meta.model_dump_json(indent=2),
        encoding="utf-8",
    )


def _load_cached_markdown(scheme: SchemeMetadata) -> FetchResult | None:
    """Copy cached markdown into data/raw when USE_CACHE is enabled."""
    cache_path = cache_markdown_path(scheme.slug)
    if not cache_path.is_file():
        logger.warning("Cache miss for %s: %s", scheme.slug, cache_path)
        return None

    ensure_ingestion_dirs()
    destination = raw_markdown_path(scheme.slug)
    shutil.copy2(cache_path, destination)
    fetched_at = datetime.fromtimestamp(cache_path.stat().st_mtime, tz=timezone.utc)

    meta = FetchMeta(
        slug=scheme.slug,
        scheme_name=scheme.scheme_name,
        source_url=str(scheme.source_url),
        fetch_timestamp=fetched_at,
        content_type="markdown",
        content_path=str(destination.relative_to(PROJECT_ROOT)).replace("\\", "/"),
        from_cache=True,
    )
    _write_meta(meta)
    logger.info("Loaded cached markdown for %s from %s", scheme.slug, cache_path)
    return FetchResult(slug=scheme.slug, success=True, meta=meta)


def fetch_scheme(
    scheme: SchemeMetadata,
    *,
    client: httpx.Client | None = None,
    use_cache: bool | None = None,
) -> FetchResult:
    """
    Fetch one scheme page and store under ``data/raw/``.

    When ``use_cache`` is True, reads ``data/cache/{slug}.md`` instead of HTTP.
    """
    use_cache_mode = _use_cache() if use_cache is None else use_cache
    if use_cache_mode:
        cached = _load_cached_markdown(scheme)
        if cached is not None:
            return cached
        logger.warning(
            "USE_CACHE=true but no cache file for %s; falling back to HTTP",
            scheme.slug,
        )

    ensure_ingestion_dirs()
    url = str(scheme.source_url)
    owns_client = client is None
    http = client or httpx.Client(
        timeout=FETCH_TIMEOUT_SECONDS,
        headers={"User-Agent": DEFAULT_USER_AGENT},
        follow_redirects=True,
    )

    try:
        response = http.get(url)
        response.raise_for_status()
        html_path = raw_html_path(scheme.slug)
        html_path.write_text(response.text, encoding="utf-8")
        fetched_at = datetime.now(timezone.utc)
        meta = FetchMeta(
            slug=scheme.slug,
            scheme_name=scheme.scheme_name,
            source_url=url,
            fetch_timestamp=fetched_at,
            content_type="html",
            content_path=str(html_path.relative_to(PROJECT_ROOT)).replace("\\", "/"),
            from_cache=False,
        )
        _write_meta(meta)
        logger.info("Fetched %s (%d bytes)", scheme.slug, len(response.text))
        return FetchResult(slug=scheme.slug, success=True, meta=meta)
    except httpx.HTTPError as exc:
        logger.error("Fetch failed for %s: %s", scheme.slug, exc)
        return FetchResult(slug=scheme.slug, success=False, error=str(exc))
    finally:
        if owns_client:
            http.close()


def fetch_all_schemes(*, use_cache: bool | None = None) -> list[FetchResult]:
    """
    Fetch all corpus schemes. Continues on per-URL failure.

    Raises ``RuntimeError`` if every fetch fails.
    """
    config = get_corpus_config()
    results: list[FetchResult] = []
    with httpx.Client(
        timeout=FETCH_TIMEOUT_SECONDS,
        headers={"User-Agent": DEFAULT_USER_AGENT},
        follow_redirects=True,
    ) as client:
        for scheme in config.schemes:
            results.append(fetch_scheme(scheme, client=client, use_cache=use_cache))

    successes = [r for r in results if r.success]
    if not successes:
        failed = ", ".join(r.slug for r in results)
        raise RuntimeError(f"All fetches failed: {failed}")
    if len(successes) < len(results):
        failed = [r for r in results if not r.success]
        logger.warning(
            "Partial fetch: %d/%d succeeded; failed: %s",
            len(successes),
            len(results),
            [f.slug for f in failed],
        )
    return results


def load_fetch_meta(slug: str) -> FetchMeta:
    path = raw_meta_path(slug)
    if not path.is_file():
        raise FileNotFoundError(f"No fetch metadata for slug={slug}: {path}")
    return FetchMeta.model_validate_json(path.read_text(encoding="utf-8"))


def read_raw_content(slug: str) -> tuple[str, FetchMeta]:
    """Return raw page content and metadata for a slug."""
    meta = load_fetch_meta(slug)
    if meta.content_type == "markdown":
        path = raw_markdown_path(slug)
    else:
        path = raw_html_path(slug)
    if not path.is_file():
        raise FileNotFoundError(f"Raw content missing for {slug}: {path}")
    return path.read_text(encoding="utf-8", errors="replace"), meta
