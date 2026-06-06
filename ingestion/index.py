"""Embed chunks and upsert into ChromaDB with blue-green swap (Phase 2.4)."""

from __future__ import annotations

import gc
import logging
import os
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable

import chromadb

from app.models import ChunkRecord
from config.loader import get_corpus_config
from ingestion.models import MetadataIndex
from ingestion.parse import load_processed_document
from ingestion.paths import (
    CHROMA_STAGING_DIR,
    COLLECTION_NAME,
    METADATA_INDEX_PATH,
    chroma_path,
    ensure_ingestion_dirs,
)

logger = logging.getLogger(__name__)

_embedder_cache: object | None = None


def _embedding_provider() -> str:
    return os.getenv("EMBEDDING_PROVIDER", "local").lower()


def _embedding_model_name() -> str:
    return os.getenv("EMBEDDING_MODEL", "BAAI/bge-small-en-v1.5")


def _get_embedder():
    global _embedder_cache
    if _embedder_cache is None:
        from sentence_transformers import SentenceTransformer

        _embedder_cache = SentenceTransformer(_embedding_model_name())
    return _embedder_cache


def embed_texts(
    texts: list[str],
    *,
    embed_fn: Callable[[list[str]], list[list[float]]] | None = None,
) -> list[list[float]]:
    """Embed document texts for indexing (passage / document encoding)."""
    if not texts:
        return []
    if embed_fn is not None:
        return embed_fn(texts)

    provider = _embedding_provider()
    if provider == "local":
        model = _get_embedder()
        model_name = _embedding_model_name().lower()
        inputs = texts
        if "bge" in model_name:
            inputs = texts
        vectors = model.encode(inputs, normalize_embeddings=True, show_progress_bar=False)
        return [v.tolist() for v in vectors]

    if provider == "openai":
        from openai import OpenAI

        client = OpenAI(api_key=os.getenv("LLM_API_KEY"))
        model = _embedding_model_name()
        response = client.embeddings.create(input=texts, model=model)
        return [item.embedding for item in response.data]

    raise ValueError(f"Unsupported EMBEDDING_PROVIDER: {provider}")


def _chunk_to_chroma_metadata(chunk: ChunkRecord) -> dict[str, str]:
    return {
        "slug": chunk.id.split("#", 1)[0],
        "section": chunk.section.value,
        "scheme_name": chunk.scheme_name,
        "source_url": str(chunk.source_url),
        "last_updated": chunk.last_updated.isoformat(),
        "manager_name": chunk.manager_name or "",
    }


def build_chroma_collection(
    chunks: list[ChunkRecord],
    persist_path: Path,
    *,
    embed_fn: Callable[[list[str]], list[list[float]]] | None = None,
) -> int:
    """Build a Chroma collection at ``persist_path``; returns document count."""
    if persist_path.exists():
        shutil.rmtree(persist_path, ignore_errors=True)
    persist_path.mkdir(parents=True, exist_ok=True)

    client = chromadb.PersistentClient(path=str(persist_path))
    collection = client.get_or_create_collection(
        name=COLLECTION_NAME,
        metadata={"hnsw:space": "cosine"},
    )

    if not chunks:
        count = collection.count()
        del collection
        del client
        gc.collect()
        return count

    texts = [c.text for c in chunks]
    embeddings = embed_texts(texts, embed_fn=embed_fn)
    collection.upsert(
        ids=[c.id for c in chunks],
        documents=texts,
        embeddings=embeddings,
        metadatas=[_chunk_to_chroma_metadata(c) for c in chunks],
    )
    count = collection.count()
    del collection
    del client
    gc.collect()
    logger.info("Upserted %s chunks into %s", len(chunks), persist_path)
    return count


def swap_chroma_index(staging_path: Path, production_path: Path) -> None:
    """Replace production Chroma directory with a successfully built staging directory."""
    ensure_ingestion_dirs()
    if staging_path.resolve() == production_path.resolve():
        return

    if not staging_path.is_dir():
        raise FileNotFoundError(f"Staging Chroma path missing: {staging_path}")

    backup_path = production_path.parent / f"{production_path.name}_old"
    if backup_path.exists():
        shutil.rmtree(backup_path, ignore_errors=True)
    if production_path.exists():
        shutil.rmtree(production_path, ignore_errors=True)

    shutil.copytree(staging_path, production_path)
    shutil.rmtree(staging_path, ignore_errors=True)
    gc.collect()


def build_metadata_index(chunks: list[ChunkRecord]) -> MetadataIndex:
    config = get_corpus_config()
    schemes_out: list[dict[str, str | list[str] | None]] = []

    for scheme in config.schemes:
        last_fetched: str | None = None
        try:
            doc = load_processed_document(scheme.slug)
            last_fetched = doc.fetch_timestamp.date().isoformat()
        except FileNotFoundError:
            pass

        schemes_out.append(
            {
                "slug": scheme.slug,
                "scheme_name": scheme.scheme_name,
                "category": scheme.category,
                "source_url": str(scheme.source_url),
                "aliases": scheme.aliases,
                "last_fetched_at": last_fetched,
            }
        )

    return MetadataIndex(
        built_at=datetime.now(timezone.utc),
        embedding_model=_embedding_model_name(),
        embedding_provider=_embedding_provider(),
        chunk_count=len(chunks),
        collection_name=COLLECTION_NAME,
        schemes=schemes_out,
    )


def write_metadata_index(index: MetadataIndex) -> Path:
    ensure_ingestion_dirs()
    METADATA_INDEX_PATH.write_text(
        index.model_dump_json(indent=2),
        encoding="utf-8",
    )
    logger.info("Wrote metadata index: %s", METADATA_INDEX_PATH)
    return METADATA_INDEX_PATH


def index_chunks(
    chunks: list[ChunkRecord],
    *,
    embed_fn: Callable[[list[str]], list[list[float]]] | None = None,
) -> tuple[Path, Path]:
    """Build staging Chroma index, swap to production, write metadata.json."""
    ensure_ingestion_dirs()
    staging = CHROMA_STAGING_DIR
    production = chroma_path()

    build_chroma_collection(chunks, staging, embed_fn=embed_fn)
    swap_chroma_index(staging, production)

    meta = build_metadata_index(chunks)
    meta_path = write_metadata_index(meta)
    return production, meta_path


def load_metadata_index() -> MetadataIndex:
    if not METADATA_INDEX_PATH.is_file():
        raise FileNotFoundError(f"Metadata index not found: {METADATA_INDEX_PATH}")
    return MetadataIndex.model_validate_json(
        METADATA_INDEX_PATH.read_text(encoding="utf-8")
    )
