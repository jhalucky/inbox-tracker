from __future__ import annotations

import json
import logging
import re
from collections.abc import Callable

from pydantic import ValidationError

from app.providers.base import Classification, TokenUsage

logger = logging.getLogger(__name__)

CompleteFn = Callable[[], tuple[str, TokenUsage]]

_FENCE_RE = re.compile(r"^```(?:json)?\s*|\s*```$", re.IGNORECASE)


def strip_code_fences(text: str) -> str:
    text = text.strip()
    if text.startswith("```"):
        text = _FENCE_RE.sub("", text).strip()
    return text


def extract_json_object(text: str) -> str:
    text = strip_code_fences(text)
    start = text.find("{")
    end = text.rfind("}")
    if start != -1 and end != -1 and end > start:
        return text[start : end + 1]
    return text


def parse_classification(text: str) -> Classification | None:
    try:
        data = json.loads(extract_json_object(text))
        if not isinstance(data, dict):
            return None
        data.pop("prompt_tokens", None)
        data.pop("completion_tokens", None)
        data.pop("adjusted_urgency", None)
        return Classification.model_validate(data)
    except (json.JSONDecodeError, ValidationError, TypeError, ValueError):
        return None


def fallback_classification(usage: TokenUsage) -> Classification:
    return Classification(
        needs_reply=None,
        urgency=1,
        category="other",
        deadline=None,
        reason="model returned invalid JSON",
        summary="",
        prompt_tokens=usage.prompt_tokens,
        completion_tokens=usage.completion_tokens,
    )


def classify_with_json_retry(complete: CompleteFn) -> Classification:
    usage = TokenUsage()
    for attempt in range(2):
        raw, call_usage = complete()
        usage.prompt_tokens += call_usage.prompt_tokens
        usage.completion_tokens += call_usage.completion_tokens
        parsed = parse_classification(raw)
        if parsed is not None:
            parsed.prompt_tokens = usage.prompt_tokens
            parsed.completion_tokens = usage.completion_tokens
            return parsed
        if attempt == 0:
            logger.warning("LLM returned invalid JSON; retrying")
        else:
            logger.warning("LLM returned invalid JSON; falling back to needs_reply=null")
    return fallback_classification(usage)
