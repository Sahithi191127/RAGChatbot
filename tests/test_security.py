"""Phase 7: PII and message length guards."""

import pytest

from app.security import contains_pii, validate_message_length


def test_detects_pan() -> None:
    assert contains_pii("My PAN is ABCDE1234F and expense ratio?")


def test_detects_email() -> None:
    assert contains_pii("Contact me at user@example.com about mid cap")


def test_detects_phone() -> None:
    assert contains_pii("Call me on 9876543210 for NAV")


def test_factual_query_clean() -> None:
    assert not contains_pii("What is the expense ratio of HDFC Mid Cap Fund Direct Growth?")


def test_message_length_limit() -> None:
    with pytest.raises(ValueError):
        validate_message_length("x" * 5000, max_length=4000)
