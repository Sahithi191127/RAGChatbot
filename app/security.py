"""Input sanitization — reject PII before LLM / logging (Phase 7)."""

from __future__ import annotations

import re

# Indian PAN: 5 letters + 4 digits + 1 letter
_PAN_PATTERN = re.compile(r"\b[A-Z]{5}[0-9]{4}[A-Z]\b", re.IGNORECASE)

# Aadhaar: 12 digits, optional spaces/dashes
_AADHAAR_PATTERN = re.compile(r"\b(?:\d{4}[\s-]?){3}\d{4}\b")

_EMAIL_PATTERN = re.compile(
    r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b",
)

# Indian mobile: 10 digits, optional +91
_PHONE_PATTERN = re.compile(
    r"(?:\+91[\s-]?)?[6-9]\d{9}\b",
)

_OTP_PATTERN = re.compile(r"\b(?:otp|one[- ]time password)\b", re.IGNORECASE)

# Long digit sequences (possible account numbers)
_ACCOUNT_PATTERN = re.compile(r"\b\d{12,}\b")

PII_REASON = (
    "Messages must not contain personal identifiers (PAN, Aadhaar, email, phone, "
    "OTP, or account numbers). Ask factual questions about the five HDFC schemes only."
)


def contains_pii(text: str) -> bool:
    """Return True if text matches blocked PII patterns."""
    if _PAN_PATTERN.search(text):
        return True
    if _AADHAAR_PATTERN.search(text):
        return True
    if _EMAIL_PATTERN.search(text):
        return True
    if _PHONE_PATTERN.search(text):
        return True
    if _OTP_PATTERN.search(text):
        return True
    if _ACCOUNT_PATTERN.search(text):
        return True
    return False


def validate_message_length(text: str, *, max_length: int = 4000) -> None:
    if len(text) > max_length:
        raise ValueError(f"Message exceeds maximum length of {max_length} characters.")
