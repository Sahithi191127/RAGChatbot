"""FastAPI entrypoint — Mutual Fund FAQ Assistant (Phase 7)."""

from __future__ import annotations

import logging

from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app import __version__
from app.models import ChatRequest, ChatResponse, SchemeListItem
from app.rate_limit import RateLimitMiddleware
from app.rag import chat, classify_only
from app.retriever import detect_section_intent, index_is_ready, resolve_scheme
from app.security import PII_REASON, contains_pii, validate_message_length
from app.settings import get_settings
from config.loader import get_corpus_config, get_corpus_summary

logger = logging.getLogger(__name__)

app = FastAPI(
    title="Mutual Fund FAQ Assistant",
    description="Facts-only RAG assistant for five HDFC schemes on Groww.",
    version=__version__,
)

settings = get_settings()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(
    RateLimitMiddleware,
    limit=settings.rate_limit_per_minute,
    window_seconds=60,
)


def _guard_message(message: str) -> str:
    """PII and length checks before RAG (message is not logged)."""
    try:
        validate_message_length(message, max_length=settings.max_message_length)
    except ValueError as exc:
        raise HTTPException(status_code=413, detail=str(exc)) from exc
    if contains_pii(message):
        raise HTTPException(status_code=400, detail=PII_REASON)
    return message


@app.get("/health")
def health() -> dict:
    """Liveness check for deployment and local development."""
    corpus = get_corpus_summary()
    return {
        "status": "ok",
        "version": __version__,
        "service": "mutual-fund-faq-assistant",
        "chroma_path": settings.chroma_path,
        "index_ready": index_is_ready(),
        "corpus": corpus.model_dump(),
    }


@app.get("/api/schemes", response_model=list[SchemeListItem])
def list_schemes() -> list[SchemeListItem]:
    """List the five supported HDFC schemes (for UI)."""
    config = get_corpus_config()
    return [
        SchemeListItem(
            slug=scheme.slug,
            scheme_name=scheme.scheme_name,
            category=scheme.category,
            source_url=scheme.source_url,
            aliases=scheme.aliases,
        )
        for scheme in config.schemes
    ]


@app.post("/api/chat", response_model=ChatResponse)
def api_chat(body: ChatRequest, request: Request) -> ChatResponse:
    """
    Stateless chat: classify → retrieve → generate → validate → format.

    Offline index only; no corpus refresh from this endpoint.
    """
    message = _guard_message(body.message)

    classification = classify_only(message)
    scheme_resolution = resolve_scheme(message)
    section = detect_section_intent(message)

    response = chat(message)

    logger.info(
        "chat_completed query_class=%s resolved_slug=%s section=%s is_refusal=%s client=%s",
        classification.label.value,
        scheme_resolution.slug,
        section.value if section else None,
        response.is_refusal,
        request.client.host if request.client else "unknown",
    )

    return response


UI_DIR = Path(__file__).resolve().parent.parent / "ui"
if UI_DIR.is_dir():

    @app.get("/", include_in_schema=False)
    def serve_chat_ui() -> FileResponse:
        return FileResponse(UI_DIR / "index.html")

    app.mount("/static", StaticFiles(directory=UI_DIR), name="ui-static")


def run() -> None:
    """Run uvicorn when invoked as ``python -m app.main``."""
    import uvicorn

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    uvicorn.run(
        "app.main:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=False,
    )


if __name__ == "__main__":
    run()
