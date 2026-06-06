"""Ingestion pipeline entrypoint: fetch → parse → chunk → embed → index (Phase 2.5)."""

from __future__ import annotations

import argparse
import logging
import sys
from datetime import datetime, timezone

from ingestion.chunk import chunk_all_schemes, summarize_chunks
from ingestion.fetch import fetch_all_schemes
from ingestion.index import index_chunks
from ingestion.models import IngestionRunResult
from ingestion.parse import parse_all_schemes
from ingestion.paths import chroma_path

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


def run_ingestion(
    *,
    use_cache: bool | None = None,
    skip_fetch: bool = False,
    skip_index: bool = False,
) -> IngestionRunResult:
    started = datetime.now(timezone.utc)
    errors: list[str] = []

    if not skip_fetch:
        fetch_results = fetch_all_schemes(use_cache=use_cache)
        fetch_ok = sum(1 for r in fetch_results if r.success)
        fetch_total = len(fetch_results)
        for result in fetch_results:
            if not result.success:
                logger.warning("Fetch failed for %s: %s", result.slug, result.error)
        if fetch_ok == 0:
            finished = datetime.now(timezone.utc)
            return IngestionRunResult(
                success=False,
                started_at=started,
                finished_at=finished,
                fetch_ok=0,
                fetch_total=fetch_total,
                errors=errors or ["All fetches failed"],
            )
    else:
        fetch_ok = 0
        fetch_total = 0

    documents = parse_all_schemes(write=True)
    schemes_parsed = len(documents)

    chunks = chunk_all_schemes(write=True)
    by_scheme, by_section = summarize_chunks(chunks)

    meta_path = None
    chroma = None
    if not skip_index:
        try:
            chroma, meta_path = index_chunks(chunks)
        except Exception as exc:
            logger.exception("Indexing failed")
            errors.append(f"index: {exc}")

    finished = datetime.now(timezone.utc)
    success = (
        (skip_fetch or fetch_ok > 0)
        and schemes_parsed > 0
        and len(chunks) > 0
        and (skip_index or meta_path is not None)
        and not errors
    )

    result = IngestionRunResult(
        success=success,
        started_at=started,
        finished_at=finished,
        fetch_ok=fetch_ok if not skip_fetch else fetch_total,
        fetch_total=fetch_total if not skip_fetch else schemes_parsed,
        schemes_parsed=schemes_parsed,
        chunk_count=len(chunks),
        chunks_by_scheme=by_scheme,
        chunks_by_section=by_section,
        errors=errors,
        metadata_index_path=str(meta_path) if meta_path else None,
        chroma_path=str(chroma) if chroma else str(chroma_path()),
    )

    duration = (finished - started).total_seconds()
    logger.info(
        "Ingestion %s in %.1fs — parsed=%s chunks=%s fetch=%s/%s",
        "OK" if success else "FAILED",
        duration,
        schemes_parsed,
        len(chunks),
        result.fetch_ok,
        result.fetch_total,
    )
    for slug, count in sorted(by_scheme.items()):
        logger.info("  chunks[%s]=%s", slug, count)
    for section, count in sorted(by_section.items()):
        logger.info("  section[%s]=%s", section, count)

    return result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run full HDFC FAQ ingestion pipeline")
    parser.add_argument(
        "--use-cache",
        action="store_true",
        help="Read markdown from data/cache/ when available",
    )
    parser.add_argument("--skip-fetch", action="store_true", help="Parse/chunk/index only")
    parser.add_argument("--skip-index", action="store_true", help="Fetch/parse/chunk only")
    args = parser.parse_args(argv)

    result = run_ingestion(
        use_cache=args.use_cache or None,
        skip_fetch=args.skip_fetch,
        skip_index=args.skip_index,
    )

    print(
        f"Ingestion {'succeeded' if result.success else 'failed'}: "
        f"chunks={result.chunk_count} schemes={result.schemes_parsed} "
        f"duration={(result.finished_at - result.started_at).total_seconds():.1f}s"
    )
    if result.errors:
        for err in result.errors:
            print(f"  error: {err}", file=sys.stderr)

    return 0 if result.success else 1


if __name__ == "__main__":
    raise SystemExit(main())
