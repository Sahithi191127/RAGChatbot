"""Phase 2.4: Chroma index and metadata tests (mocked embeddings)."""

from pathlib import Path

import pytest

from ingestion.chunk import chunk_document
from ingestion.index import (
    build_chroma_collection,
    build_metadata_index,
    index_chunks,
    load_metadata_index,
    swap_chroma_index,
)
from ingestion.parse import load_processed_document

MID_SLUG = "hdfc-mid-cap-fund-direct-growth"


def _fake_embed(texts: list[str]) -> list[list[float]]:
    return [[0.1, 0.2, 0.3] for _ in texts]


@pytest.fixture
def mid_cap_chunks():
    path = Path(f"data/processed/{MID_SLUG}.json")
    if not path.is_file():
        pytest.skip("processed document missing")
    return chunk_document(load_processed_document(MID_SLUG))


def test_build_chroma_collection(tmp_path: Path, mid_cap_chunks) -> None:
    staging = tmp_path / "chroma_staging"
    count = build_chroma_collection(
        mid_cap_chunks,
        staging,
        embed_fn=_fake_embed,
    )
    assert count == len(mid_cap_chunks)


def test_swap_chroma_index(tmp_path: Path, mid_cap_chunks) -> None:
    staging = tmp_path / "staging"
    production = tmp_path / "production"
    build_chroma_collection(mid_cap_chunks[:3], staging, embed_fn=_fake_embed)
    swap_chroma_index(staging, production)
    assert production.is_dir()
    assert any(production.iterdir())


def test_metadata_index_written(tmp_path: Path, mid_cap_chunks, monkeypatch) -> None:
    monkeypatch.setattr("ingestion.index.CHROMA_STAGING_DIR", tmp_path / "staging")
    monkeypatch.setattr("ingestion.index.chroma_path", lambda: tmp_path / "chroma")
    monkeypatch.setattr("ingestion.index.METADATA_INDEX_PATH", tmp_path / "metadata.json")

    chroma, meta_path = index_chunks(mid_cap_chunks, embed_fn=_fake_embed)
    assert chroma.is_dir()
    assert meta_path.is_file()

    meta = load_metadata_index()
    assert meta.chunk_count == len(mid_cap_chunks)
    assert meta.collection_name == "hdfc_faq_corpus"
    assert len(meta.schemes) == 5


def test_metadata_index_has_last_fetched(mid_cap_chunks) -> None:
    meta = build_metadata_index(mid_cap_chunks)
    slugs_with_dates = [
        s["slug"] for s in meta.schemes if s.get("last_fetched_at")
    ]
    assert len(slugs_with_dates) >= 1
