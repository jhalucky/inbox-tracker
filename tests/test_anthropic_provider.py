import json

from app.providers.anthropic_provider import AnthropicProvider
from app.providers.base import EmailInput

VALID = json.dumps(
    {
        "needs_reply": True,
        "urgency": 3,
        "category": "client",
        "deadline": None,
        "reason": "Asked to reschedule.",
        "summary": "Client wants to move a call.",
    }
)


class _TextBlock:
    type = "text"

    def __init__(self, text: str) -> None:
        self.text = text


class _Usage:
    input_tokens = 9
    output_tokens = 6


class _Message:
    def __init__(self, text: str) -> None:
        self.content = [_TextBlock(text)]
        self.usage = _Usage()


class _Messages:
    def __init__(self, text: str) -> None:
        self.text = text
        self.kwargs: dict | None = None

    def create(self, **kwargs: object) -> _Message:
        self.kwargs = kwargs
        return _Message(self.text)


class _FakeAnthropic:
    def __init__(self, text: str) -> None:
        self.messages = _Messages(text)


def test_anthropic_uses_model_and_usage() -> None:
    client = _FakeAnthropic(VALID)
    provider = AnthropicProvider(
        api_key="secret-key",
        model="claude-haiku-4-5",
        client=client,  # type: ignore[arg-type]
        backoff_seconds=0,
    )
    result = provider.classify(
        EmailInput(sender="chen@client.example", subject="Reschedule?", body="Can we move?")
    )
    assert client.messages.kwargs is not None
    assert client.messages.kwargs["model"] == "claude-haiku-4-5"
    assert client.messages.kwargs["max_tokens"] == 300
    assert client.messages.kwargs["extra_body"] == {"temperature": 0}
    assert result.needs_reply is True
    assert result.prompt_tokens == 9
    assert result.completion_tokens == 6
    assert result.reason == "Asked to reschedule."
