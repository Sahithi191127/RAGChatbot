"""Refusal responses for non-factual queries (Phase 5.2)."""



from __future__ import annotations



from datetime import date



from app.classifier import QueryLabel

from app.models import ChatResponse

from config.loader import get_corpus_config



REFUSAL_CITATION_PREFERENCE = "amfi"  # or "sebi"



_POLICY_REFUSAL_MESSAGE = (

    "I can only provide factual information about the supported mutual fund schemes "

    "and cannot provide investment advice, recommendations, comparisons, or return predictions."

)





def _refusal_citation_url() -> str:

    config = get_corpus_config()

    if REFUSAL_CITATION_PREFERENCE == "sebi":

        return str(config.refusal_urls.sebi)

    return str(config.refusal_urls.amfi)





def _supported_scheme_bullets() -> str:

    config = get_corpus_config()

    lines = [f"* {scheme.scheme_name}" for scheme in config.schemes]

    return "\n".join(lines)





def refusal_message(label: QueryLabel) -> str:

    if label in (QueryLabel.ADVISORY, QueryLabel.COMPARISON, QueryLabel.PERFORMANCE):

        return _POLICY_REFUSAL_MESSAGE

    return _POLICY_REFUSAL_MESSAGE





def build_refusal_response(label: QueryLabel) -> ChatResponse:

    """Build a refusal ``ChatResponse`` with AMFI/SEBI educational link."""

    config = get_corpus_config()

    return ChatResponse(

        answer=refusal_message(label),

        citation_url=_refusal_citation_url(),

        last_updated=date.today(),

        is_refusal=True,

        disclaimer=config.disclaimer,

    )





def build_unsupported_scheme_response() -> ChatResponse:

    """List supported schemes when the question is about an unsupported mutual fund."""

    config = get_corpus_config()

    answer = (

        "I only have information for the following five HDFC mutual fund schemes:\n\n"

        f"{_supported_scheme_bullets()}\n\n"

        "Please ask about one of these schemes."

    )

    return ChatResponse(

        answer=answer,

        citation_url=_refusal_citation_url(),

        last_updated=date.today(),

        is_refusal=True,

        disclaimer=config.disclaimer,

    )





def build_unrelated_response() -> ChatResponse:

    """Short refusal for queries unrelated to the mutual fund corpus."""

    config = get_corpus_config()

    answer = (

        "I don't know that information.\n\n"

        "I can only answer factual questions about five supported HDFC mutual fund schemes.\n\n"

        "Examples:\n\n"

        "* What is the expense ratio of HDFC Mid Cap Fund Direct Growth?\n"

        "* Who manages HDFC Defence Fund Direct Growth?\n"

        "* What is the exit load on HDFC Small Cap Fund Direct Growth?\n\n"

        "Facts-only. No investment advice."

    )

    return ChatResponse(

        answer=answer,

        citation_url=None,

        last_updated=date.today(),

        is_refusal=True,

        disclaimer=config.disclaimer,

    )





def build_scheme_ambiguous_response() -> ChatResponse:

    """Ask the user to name one supported scheme (MF-related but no scheme resolved)."""

    config = get_corpus_config()

    answer = (

        "Please name one of the five supported HDFC schemes so I can answer with facts "

        "from its Groww page.\n\n"

        f"{_supported_scheme_bullets()}"

    )

    return ChatResponse(

        answer=answer,

        citation_url=_refusal_citation_url(),

        last_updated=date.today(),

        is_refusal=True,

        disclaimer=config.disclaimer,

    )





def build_out_of_scope_response(*, scheme_ambiguous: bool = False) -> ChatResponse:

    """Backward-compatible alias for ambiguous scheme vs unsupported scheme routing."""

    if scheme_ambiguous:

        return build_scheme_ambiguous_response()

    return build_unsupported_scheme_response()





def build_insufficient_context_response(source_url: str | None = None) -> ChatResponse:

    config = get_corpus_config()

    answer = (

        "I could not find enough information in the retrieved scheme content to answer precisely. "

        "Please check the scheme page for the latest published details."

    )

    citation = source_url or _refusal_citation_url()

    return ChatResponse(

        answer=answer,

        citation_url=citation,

        last_updated=date.today(),

        is_refusal=False,

        disclaimer=config.disclaimer,

    )

