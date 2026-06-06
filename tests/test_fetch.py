"""Phase 2.1: ingestion fetch tests."""

from pathlib import Path
from unittest.mock import MagicMock

import httpx
import pytest

from config.loader import clear_corpus_cache
from ingestion.fetch import fetch_all_schemes, fetch_scheme, load_fetch_meta
from ingestion.paths import CACHE_DIR, RAW_DIR, cache_markdown_path, raw_markdown_path

FIXTURE_MD = (
    Path(__file__).parent / "fixtures" / "hdfc-mid-cap-fund-direct-growth.md"
)
SLUG = "hdfc-mid-cap-fund-direct-growth"


@pytest.fixture(autouse=True)
def _clear_cache() -> None:
    clear_corpus_cache()
    yield
    clear_corpus_cache()


@pytest.fixture
def scheme():
    from config.loader import get_scheme_by_slug

    found = get_scheme_by_slug(SLUG)
    assert found is not None
    return found


def test_fetch_from_cache(monkeypatch, scheme, tmp_path) -> None:
    monkeypatch.setenv("USE_CACHE", "true")
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    cache_path = cache_markdown_path(SLUG)
    cache_path.write_text(FIXTURE_MD.read_text(encoding="utf-8"), encoding="utf-8")

    result = fetch_scheme(scheme, use_cache=True)
    assert result.success is True
    assert result.meta is not None
    assert result.meta.from_cache is True
    assert result.meta.content_type == "markdown"
    assert raw_markdown_path(SLUG).is_file()

    meta = load_fetch_meta(SLUG)
    assert meta.slug == SLUG


def test_fetch_http_success(monkeypatch, scheme) -> None:
    monkeypatch.setenv("USE_CACHE", "false")

    response = httpx.Response(
        200,
        text="<html><body><h1>HDFC Mid Cap Fund Direct Growth</h1></body></html>",
        request=httpx.Request("GET", str(scheme.source_url)),
    )
    client = MagicMock()
    client.get.return_value = response

    result = fetch_scheme(scheme, client=client, use_cache=False)
    assert result.success is True
    assert result.meta is not None
    assert result.meta.content_type == "html"
    client.get.assert_called_once()


def test_fetch_http_failure_continues(monkeypatch, scheme) -> None:
    monkeypatch.setenv("USE_CACHE", "false")

    client = MagicMock()
    client.get.side_effect = httpx.TimeoutException("timeout")

    result = fetch_scheme(scheme, client=client, use_cache=False)
    assert result.success is False
    assert result.error is not None


def test_fetch_all_raises_when_all_fail(monkeypatch) -> None:
    from ingestion.models import FetchResult

    def _always_fail(scheme, **kwargs):
        return FetchResult(slug=scheme.slug, success=False, error="down")

    monkeypatch.setattr("ingestion.fetch.fetch_scheme", _always_fail)
    with pytest.raises(RuntimeError, match="All fetches failed"):
        fetch_all_schemes(use_cache=False)
