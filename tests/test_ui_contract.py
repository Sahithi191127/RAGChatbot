"""Phase 9: UI contract tests (static checks for Phase 8 deliverables)."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
FRONTEND = ROOT / "frontend" / "src"
UI = ROOT / "ui"


def test_nextjs_disclaimer_footer_present() -> None:
    footer = (FRONTEND / "components" / "DisclaimerFooter.tsx").read_text(encoding="utf-8")
    assert "Facts-only" in footer
    assert "No investment advice" in footer


def test_nextjs_example_questions_cover_phase8_requirements() -> None:
    types_file = (FRONTEND / "lib" / "types.ts").read_text(encoding="utf-8")
    assert "expense ratio" in types_file.lower()
    assert "exit load" in types_file.lower()
    assert "Who manages" in types_file


def test_nextjs_privacy_notice_in_input() -> None:
    chat_input = (FRONTEND / "components" / "ChatInput.tsx").read_text(encoding="utf-8")
    assert "PAN" in chat_input
    assert "Aadhaar" in chat_input


def test_nextjs_learn_more_for_refusals() -> None:
    chat_message = (FRONTEND / "components" / "ChatMessage.tsx").read_text(encoding="utf-8")
    assert "Learn more" in chat_message


def test_legacy_ui_has_disclaimer_and_examples() -> None:
    html = (UI / "index.html").read_text(encoding="utf-8")
    assert "Facts-only" in html
    assert "expense ratio" in html.lower()
    assert "exit load" in html.lower()
    assert "Who manages" in html
