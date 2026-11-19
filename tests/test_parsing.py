import logging

from app.providers.base import TokenUsage
from app.providers.parsing import (
    classify_with_json_retry,
    parse_classification,
    strip_code_fences,
)

VALID = """
{
  "needs_reply": true,
  "urgency": 4,
  "category": "lead",
  "deadline": "Friday",
  "reason": "Sender asked for pricing.",
  "summary": "Lead wants 10-seat pricing."
}
"""


def test_strip_code_fences() -> None:
    fenced = "```json\n{\"needs_reply\": true}\n```"
    assert strip_code_fences(fenced) == '{"needs_reply": true}'


def test_parse_fenced_json() -> None:
    parsed = parse_classification(f"```json{VALID}```")
    assert parsed is not None
    assert parsed.needs_reply is True
    assert parsed.urgency == 4
    assert parsed.category == "lead"


def test_parse_invalid_returns_none() -> None:
    assert parse_classification("not json") is None
    assert parse_classification('{"needs_reply": true}') is None


def test_retry_then_success() -> None:
    calls = {"n": 0}

    def complete() -> tuple[str, TokenUsage]:
        calls["n"] += 1
        usage = TokenUsage(prompt_tokens=3, completion_tokens=2)
        if calls["n"] == 1:
            return "not json", usage
        return VALID, usage

    result = classify_with_json_retry(complete)
    assert calls["n"] == 2
    assert result.needs_reply is True
    assert result.prompt_tokens == 6
    assert result.completion_tokens == 4


def test_fallback_needs_reply_null(caplog) -> None:
    caplog.set_level(logging.WARNING)

    def complete() -> tuple[str, TokenUsage]:
        return "<<<broken>>>", TokenUsage(prompt_tokens=1, completion_tokens=1)

    result = classify_with_json_retry(complete)
    assert result.needs_reply is None
    assert result.category == "other"
    assert "falling back to needs_reply=null" in caplog.text
    assert "<<<broken>>>" not in caplog.text
