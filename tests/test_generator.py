"""Phase 6: generator tests (mocked Groq client)."""

from datetime import date
from unittest.mock import MagicMock

import pytest

from app.generator import generate_answer, use_stub_generation
from app.models import ChunkRecord, ScoredChunk, SectionTag
from app.settings import get_settings

MID_URL = "https://groww.in/mutual-funds/hdfc-mid-cap-fund-direct-growth"


def _chunk() -> ScoredChunk:
    return ScoredChunk(
        chunk=ChunkRecord(
            id="hdfc-mid-cap-fund-direct-growth#expense_ratio#0",
            text="Scheme: HDFC Mid Cap Fund Direct Growth\nSection: expense_ratio\n\nExpense ratio: 0.73%",
            scheme_name="HDFC Mid Cap Fund Direct Growth",
            source_url=MID_URL,
            section=SectionTag.EXPENSE_RATIO,
            last_updated=date(2026, 6, 2),
        ),
        score=1.0,
    )


def test_use_stub_when_no_api_key(monkeypatch) -> None:
    monkeypatch.setenv("LLM_API_KEY", "")
    monkeypatch.setenv("USE_LLM_STUB", "false")
    get_settings.cache_clear()
    assert use_stub_generation() is True
    get_settings.cache_clear()


def test_generate_uses_groq_client(monkeypatch) -> None:
    monkeypatch.setenv("LLM_API_KEY", "test-key")
    monkeypatch.setenv("USE_LLM_STUB", "false")
    monkeypatch.setenv("LLM_BASE_URL", "https://api.groq.com/openai/v1")
    monkeypatch.setenv("LLM_MODEL", "llama-3.3-70b-versatile")
    get_settings.cache_clear()

    mock_client = MagicMock()
    mock_choice = MagicMock()
    mock_choice.message.content = "The expense ratio is 0.73% as stated in the context."
    mock_client.chat.completions.create.return_value = MagicMock(choices=[mock_choice])

    answer = generate_answer("Expense ratio?", [_chunk()], client=mock_client)
    assert "0.73%" in answer
    mock_client.chat.completions.create.assert_called_once()
    call_kwargs = mock_client.chat.completions.create.call_args.kwargs
    assert call_kwargs["model"] == "llama-3.3-70b-versatile"
    get_settings.cache_clear()


def test_generate_falls_back_on_api_error(monkeypatch) -> None:
    monkeypatch.setenv("LLM_API_KEY", "test-key")
    monkeypatch.setenv("USE_LLM_STUB", "false")
    get_settings.cache_clear()

    mock_client = MagicMock()
    mock_client.chat.completions.create.side_effect = RuntimeError("api down")

    answer = generate_answer("Expense ratio HDFC Mid Cap", [_chunk()], client=mock_client)
    assert "0.73%" in answer
    get_settings.cache_clear()
