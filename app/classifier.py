"""Rule-based query classification (Phase 5.1)."""



from __future__ import annotations



import re

from enum import Enum



from pydantic import BaseModel



from app.retriever import OTHER_AMC_MARKERS, resolve_scheme





class QueryLabel(str, Enum):

    FACTUAL = "factual"

    ADVISORY = "advisory"

    COMPARISON = "comparison"

    PERFORMANCE = "performance"

    UNSUPPORTED_SCHEME = "unsupported_scheme"

    UNRELATED = "unrelated"





class ClassificationResult(BaseModel):

    label: QueryLabel

    reason: str | None = None





# Phrases that must not trigger advisory "invest" heuristics (CLS-21)

_SAFE_PHRASES = (

    "investment objective",

    "minimum investment",

    "min investment",

    "min sip",

    "minimum sip",

)



_ADVISORY_PATTERNS = (

    r"should\s+i\s+invest",

    r"shuld\s+i\s+invest",

    r"should\s+we\s+invest",

    r"is\s+it\s+a\s+good\s+fund",

    r"is\s+this\s+a\s+good\s+fund",

    r"good\s+enough\s+to\s+buy",

    r"worth\s+investing",

    r"recommend(?:ed|ation)?",

    r"should\s+i\s+buy",

    r"should\s+i\s+sell",

    r"should\s+i\s+hold",

    r"\bbuy\s+this\s+fund\b",

    r"\bsell\s+this\s+fund\b",

    r"personal(?:ized)?\s+tax\s+advice",

    r"how\s+much\s+tax\s+will\s+i\s+pay",

    r"\bsuitability\b",

    r"\branking\b",

    r"which\s+fund\s+will\s+give",

    r"highest\s+returns?",

    r"best\s+fund\s+to\s+invest",

)



_COMPARISON_PATTERNS = (

    r"which\s+(?:fund\s+)?is\s+better",

    r"which\s+is\s+better",

    r"which\s+one\s+is\s+better",

    r"\bvs\.?\b",

    r"\bversus\b",

    r"\bcompare\b",

    r"better\s+than",

    r"or\s+small\s+cap.*large\s+cap",

    r"mid\s+cap.*small\s+cap",

)



_PERFORMANCE_PATTERNS = (

    r"what\s+(?:will|would)\s+(?:be\s+)?my\s+returns",

    r"what\s+returns\s+will\s+i",

    r"expected\s+returns",

    r"future\s+returns",

    r"predict(?:ed)?\s+returns",

    r"past\s+performance",

    r"compare\s+.*returns",

    r"\b\d+y\s+returns?\b",

    r"annualised\s+return",

    r"annualized\s+return",

    r"\bcagr\b",

    r"how\s+much\s+will\s+i\s+make",

    r"will\s+i\s+get\s+.*%",

)



_NON_CORPUS_SCHEME_MARKERS = (

    "flexi cap",

    "flexicap",

    "elss",

    "hybrid fund",

    "balanced advantage",

    "corporate bond fund",

    "income fund",

    "short term fund",

)



_MF_CONTEXT_KEYWORDS = (

    "mutual fund",

    "expense ratio",

    "exit load",

    "fund manager",

    "investment objective",

    "minimum investment",

    "min sip",

    "benchmark",

    "nav ",

    " aum",

    "fund house",

    "riskometer",

    "direct growth",

    "direct plan",

    "groww",

    "large cap",

    "small cap",

    "mid cap",

    "defence fund",

    "gold etf",

    "redemption charge",

    "tax implication",

    "portfolio manager",

    "scheme page",

    "sip amount",

    "lumpsum",

)



_UNRELATED_PATTERNS = (

    r"what\s+is\s+my\s+name",

    r"who\s+am\s+i",

    r"prime\s+minister",

    r"world\s+cup",

    r"write\s+(?:me\s+)?(?:a\s+)?poem",

    r"write\s+(?:me\s+)?(?:a\s+)?joke",

    r"tell\s+me\s+a\s+joke",

    r"who\s+won\b",

    r"what\s+is\s+the\s+weather",

    r"weather\s+today",

)





def _normalize(text: str) -> str:

    return re.sub(r"\s+", " ", text.lower().strip())





def _strip_safe_phrases(normalized: str) -> str:

    cleaned = normalized

    for phrase in _SAFE_PHRASES:

        cleaned = cleaned.replace(phrase, " ")

    return cleaned





def _matches_any(patterns: tuple[str, ...], text: str) -> bool:

    return any(re.search(pattern, text) for pattern in patterns)





def _mentions_non_corpus_scheme(normalized: str) -> bool:

    if "hdfc" not in normalized:

        return False

    return any(marker in normalized for marker in _NON_CORPUS_SCHEME_MARKERS)





def _mentions_other_amc_without_hdfc(normalized: str) -> bool:

    if "hdfc" in normalized:

        return False

    return any(marker in normalized for marker in OTHER_AMC_MARKERS)





def _has_mutual_fund_context(normalized: str) -> bool:

    if "hdfc" in normalized:

        return True

    if _mentions_other_amc_without_hdfc(normalized):

        return True

    if any(keyword in normalized for keyword in _MF_CONTEXT_KEYWORDS):

        return True

    if re.search(r"\b(?:mutual\s+)?fund\b", normalized):

        return True

    return False





def _is_unrelated(normalized: str) -> bool:

    if _matches_any(_UNRELATED_PATTERNS, normalized):

        return True

    return not _has_mutual_fund_context(normalized)





def _mentions_two_corpus_schemes(normalized: str) -> bool:

    """Detect cross-scheme comparison within the five-scheme corpus."""

    from config.loader import get_corpus_config



    hits = 0

    for scheme in get_corpus_config().schemes:

        if scheme.scheme_name.lower() in normalized:

            hits += 1

            continue

        for alias in scheme.aliases:

            if alias.lower() in normalized:

                hits += 1

                break

    return hits >= 2





def _is_unsupported_mutual_fund(normalized: str) -> bool:

    if _mentions_other_amc_without_hdfc(normalized):

        return True

    if _mentions_non_corpus_scheme(normalized):

        return True

    resolution = resolve_scheme(normalized)

    return resolution.out_of_scope





def classify_query(message: str) -> ClassificationResult:

    """

    Classify a user message before retrieval.



    Order: advisory → performance → comparison → unsupported MF → unrelated → factual.

    """

    normalized = _normalize(message)

    if not normalized:

        return ClassificationResult(label=QueryLabel.UNRELATED, reason="empty")



    advisory_text = _strip_safe_phrases(normalized)

    if _matches_any(_ADVISORY_PATTERNS, advisory_text):

        return ClassificationResult(label=QueryLabel.ADVISORY, reason="advisory_phrase")



    if _matches_any(_PERFORMANCE_PATTERNS, normalized):

        return ClassificationResult(label=QueryLabel.PERFORMANCE, reason="performance_intent")



    if _matches_any(_COMPARISON_PATTERNS, normalized) or _mentions_two_corpus_schemes(

        normalized

    ):

        return ClassificationResult(label=QueryLabel.COMPARISON, reason="comparison_intent")



    if _is_unsupported_mutual_fund(normalized):

        reason = "other_amc"

        if _mentions_non_corpus_scheme(normalized):

            reason = "non_corpus_scheme"

        return ClassificationResult(label=QueryLabel.UNSUPPORTED_SCHEME, reason=reason)



    if _is_unrelated(normalized):

        return ClassificationResult(label=QueryLabel.UNRELATED, reason="unrelated_topic")



    return ClassificationResult(label=QueryLabel.FACTUAL)

