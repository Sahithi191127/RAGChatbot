"""Phase 2.5: ingestion pipeline entrypoint tests."""

from pathlib import Path

import pytest

from ingestion.run import run_ingestion

PROCESSED = Path("data/processed")


@pytest.fixture(scope="module")
def ensure_processed() -> None:
    if not PROCESSED.exists() or len(list(PROCESSED.glob("*.json"))) < 5:
        pytest.skip("need processed scheme JSON files")


def test_run_ingestion_skip_fetch_and_index(ensure_processed) -> None:
    result = run_ingestion(skip_fetch=True, skip_index=True)
    assert result.schemes_parsed == 5
    assert result.chunk_count >= 40
    by_section = result.chunks_by_section
    assert len(result.chunks_by_scheme) == 5
    assert by_section.get("expense_ratio", 0) >= 4
    assert by_section.get("exit_load", 0) >= 4
    assert by_section.get("fund_management", 0) >= 9


def test_run_ingestion_with_mock_index(ensure_processed, monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr("ingestion.index.CHROMA_STAGING_DIR", tmp_path / "staging")
    monkeypatch.setattr("ingestion.index.chroma_path", lambda: tmp_path / "chroma")
    monkeypatch.setattr("ingestion.index.METADATA_INDEX_PATH", tmp_path / "metadata.json")
    monkeypatch.setattr(
        "ingestion.index.embed_texts",
        lambda texts, embed_fn=None: [[0.0, 0.1, 0.2] for _ in texts],
    )

    result = run_ingestion(skip_fetch=True, skip_index=False)
    assert result.success
    assert result.chunk_count >= 40
    assert result.metadata_index_path is not None
