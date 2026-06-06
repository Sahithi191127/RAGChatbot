"""Phase 5.2: refusal handler tests."""



from config.loader import get_corpus_config, get_refusal_citation_allowlist



from app.classifier import QueryLabel

from app.refusal import (

    build_refusal_response,

    build_unrelated_response,

    build_unsupported_scheme_response,

)

from app.formatter import enforce_max_sentences





def test_refusal_uses_allowlisted_citation() -> None:

    response = build_refusal_response(QueryLabel.ADVISORY)

    assert response.is_refusal is True

    assert str(response.citation_url) in get_refusal_citation_allowlist()





def test_refusal_unified_policy_message() -> None:

    for label in (QueryLabel.ADVISORY, QueryLabel.COMPARISON, QueryLabel.PERFORMANCE):

        response = build_refusal_response(label)

        assert "investment advice" in response.answer.lower()

        assert "comparisons" in response.answer.lower()





def test_refusal_disclaimer_from_config() -> None:

    config = get_corpus_config()

    response = build_refusal_response(QueryLabel.COMPARISON)

    assert response.disclaimer == config.disclaimer





def test_unsupported_scheme_lists_all_five() -> None:

    response = build_unsupported_scheme_response()

    assert response.is_refusal is True

    assert "Mid Cap" in response.answer

    assert "Defence" in response.answer

    assert "Please ask about one of these schemes" in response.answer





def test_unrelated_does_not_list_all_schemes() -> None:

    response = build_unrelated_response()

    assert response.is_refusal is True

    assert "I don't know that information" in response.answer

    assert "Examples:" in response.answer

    assert response.citation_url is None

    assert "Gold ETF" not in response.answer





def test_formatter_max_three_sentences() -> None:

    text = "One. Two. Three. Four. Five."

    assert enforce_max_sentences(text, 3) == "One. Two. Three."

