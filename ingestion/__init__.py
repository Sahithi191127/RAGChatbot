"""Offline ingestion pipeline (fetch, parse, chunk, index)."""

from ingestion.fetch import fetch_all_schemes, fetch_scheme, load_fetch_meta, read_raw_content

__all__ = [
    "fetch_all_schemes",
    "fetch_scheme",
    "load_fetch_meta",
    "read_raw_content",
]


def __getattr__(name: str):
    if name in ("load_processed_document", "parse_all_schemes", "parse_scheme"):
        from ingestion import parse as parse_mod

        return getattr(parse_mod, name)
    if name in ("chunk_all_schemes", "chunk_document", "chunk_scheme"):
        from ingestion import chunk as chunk_mod

        return getattr(chunk_mod, name)
    if name in ("index_chunks", "load_metadata_index"):
        from ingestion import index as index_mod

        return getattr(index_mod, name)
    if name == "run_ingestion":
        from ingestion.run import run_ingestion

        return run_ingestion
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
