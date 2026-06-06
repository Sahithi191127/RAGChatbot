"""Phase 1: corpus configuration and citation allowlists."""

import pytest

from app.models import SectionTag
from config import (
    build_chunk_id,
    build_fund_management_chunk_id,
    clear_corpus_cache,
    get_corpus_config,
    get_groww_citation_allowlist,
    get_refusal_citation_allowlist,
    load_corpus_config,
    parse_chunk_id,
    resolve_scheme_from_text,
)
from config.loader import CorpusConfigError

GROWW_URLS = {
    "https://groww.in/mutual-funds/hdfc-mid-cap-fund-direct-growth",
    "https://groww.in/mutual-funds/hdfc-small-cap-fund-direct-growth",
    "https://groww.in/mutual-funds/hdfc-large-cap-fund-direct-growth",
    "https://groww.in/mutual-funds/hdfc-gold-etf-fund-of-fund-direct-plan-growth",
    "https://groww.in/mutual-funds/hdfc-defence-fund-direct-growth",
}

REFUSAL_URLS = {
    "https://www.amfiindia.com/investor/knowledge-center-info?faqs",
    "https://www.sebi.gov.in/sebiweb/home/HomePage.jsp?siteLanguage=en",
}


@pytest.fixture(autouse=True)
def _clear_config_cache() -> None:
    clear_corpus_cache()
    yield
    clear_corpus_cache()


def test_load_corpus_config_has_five_schemes() -> None:
    config = load_corpus_config()
    assert config.amc == "HDFC Mutual Fund"
    assert len(config.schemes) == 5
    assert len(config.sections) == 9
    assert SectionTag.FUND_MANAGEMENT in config.sections


def test_groww_citation_allowlist_exactly_five() -> None:
    allowlist = get_groww_citation_allowlist()
    assert len(allowlist) == 5
    assert allowlist == GROWW_URLS


def test_refusal_citation_allowlist_amfi_and_sebi() -> None:
    allowlist = get_refusal_citation_allowlist()
    assert len(allowlist) == 2
    assert allowlist == REFUSAL_URLS


def test_groww_and_refusal_allowlists_disjoint() -> None:
    groww = get_groww_citation_allowlist()
    refusal = get_refusal_citation_allowlist()
    assert groww.isdisjoint(refusal)


def test_resolve_scheme_by_alias() -> None:
    scheme = resolve_scheme_from_text("What is the exit load on defence fund?")
    assert scheme is not None
    assert scheme.slug == "hdfc-defence-fund-direct-growth"


def test_resolve_scheme_gold_etf_fof() -> None:
    scheme = resolve_scheme_from_text("Who manages gold etf fof?")
    assert scheme is not None
    assert scheme.slug == "hdfc-gold-etf-fund-of-fund-direct-plan-growth"


def test_build_chunk_id_format() -> None:
    chunk_id = build_chunk_id("hdfc-mid-cap-fund-direct-growth", SectionTag.EXPENSE_RATIO, 0)
    assert chunk_id == "hdfc-mid-cap-fund-direct-growth#expense_ratio#0"
    parsed = parse_chunk_id(chunk_id)
    assert parsed["slug"] == "hdfc-mid-cap-fund-direct-growth"
    assert parsed["section"] == "expense_ratio"


def test_build_fund_management_chunk_id() -> None:
    chunk_id = build_fund_management_chunk_id(
        "hdfc-defence-fund-direct-growth", "Priya Ranjan"
    )
    assert chunk_id == "hdfc-defence-fund-direct-growth#fund_management#priya-ranjan"


def test_cached_get_corpus_config() -> None:
    a = get_corpus_config()
    b = get_corpus_config()
    assert a is b


def test_invalid_corpus_file(tmp_path) -> None:
    bad = tmp_path / "bad.yaml"
    bad.write_text("schemes: []\nsections: []\n", encoding="utf-8")
    with pytest.raises(CorpusConfigError):
        load_corpus_config(bad)
