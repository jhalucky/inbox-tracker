import json
from pathlib import Path

import pytest

from app.config import Settings
from app.pipeline.classifier import classify_one, format_report, main, run
from app.pipeline.scoring import apply_sender_weight
from app.providers.base import Classification, EmailInput
from app.providers.factory import LLMConfigError, get_llm_provider
from tests.fakes import FakeProvider

FIXTURE = Path(__file__).parent / "fixtures" / "sample_emails.json"


def test_run_skips_rules_and_calls_provider_only_for_the_rest() -> None:
    emails = json.loads(FIXTURE.read_text())
    provider = FakeProvider()
    report = run(emails, provider)

    assert report.skipped_count == 5
    assert len(provider.calls) == 5
    for email in provider.calls:
        assert "SECRET_BODY_MARKER_QUOTE" not in email.body
        assert len(email.body) <= 2000


def test_metrics_precision_recall_and_wrong_list() -> None:
    emails = [
        {"from": "a@x.com", "subject": "A", "body": "Please reply?", "label": True, "headers": {}},
        {"from": "b@x.com", "subject": "B", "body": "Please reply?", "label": False, "headers": {}},
        {"from": "c@x.com", "subject": "C", "body": "FYI only", "label": True, "headers": {}},
        {"from": "d@x.com", "subject": "D", "body": "FYI only", "label": False, "headers": {}},
    ]
    provider = FakeProvider()
    report = run(emails, provider)
    acc = report.accuracy()
    assert acc is not None
    ratio, correct, total = acc
    assert total == 4
    assert correct == 2
    assert ratio == 0.5
    precision, recall = report.precision_recall()
    assert precision == 0.5
    assert recall == 0.5
    wrong_subjects = {item.subject for item in report.wrong()}
    assert wrong_subjects == {"B", "C"}


def test_limit_and_cost_and_no_bodies_in_output() -> None:
    emails = json.loads(FIXTURE.read_text())
    provider = FakeProvider()
    report = run(emails, provider, limit=3)
    assert len(report.items) == 3

    settings = Settings(
        _env_file=None,
        llm_price_input_per_m=1.0,
        llm_price_output_per_m=2.0,
    )
    text = format_report(report, settings)
    assert "skipped by rules" in text
    assert "SECRET_BODY_MARKER" not in text
    assert "estimated cost: $" in text
    assert report.prompt_tokens == 10 * len(provider.calls)
    assert "tokens:" in text


def test_cli_main_with_fake_provider(monkeypatch, capsys, tmp_path: Path) -> None:
    source = json.loads(FIXTURE.read_text())
    path = tmp_path / "emails.json"
    path.write_text(json.dumps(source), encoding="utf-8")

    fake = FakeProvider(
        {
            "Pricing for a 10-seat plan?": Classification(
                needs_reply=True,
                urgency=4,
                category="lead",
                deadline=None,
                reason="Asked for pricing.",
                summary="Lead wants pricing.",
                prompt_tokens=8,
                completion_tokens=3,
            )
        }
    )
    monkeypatch.setattr("app.pipeline.classifier.get_llm_provider", lambda: fake)
    exit_code = main([str(path), "--limit", "2"])
    assert exit_code == 0
    out = capsys.readouterr().out
    assert "Pricing for a 10-seat plan?" in out
    assert "SECRET_BODY_MARKER" not in out
    assert "skipped:" in out
    assert "accuracy:" in out


def test_missing_llm_model_error() -> None:
    settings = Settings(_env_file=None, llm_model=None, llm_provider="openai_compatible")
    with pytest.raises(LLMConfigError, match="LLM_MODEL"):
        get_llm_provider(settings)


def test_cli_prints_missing_model_without_traceback(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    def _raise() -> None:
        raise LLMConfigError("LLM_MODEL is not set. Set it in .env.")

    monkeypatch.setattr("app.pipeline.classifier.get_llm_provider", _raise)
    code = main([str(FIXTURE), "--limit", "1"])
    captured = capsys.readouterr()
    assert code == 2
    assert "LLM_MODEL" in captured.err
    assert "Traceback" not in captured.err
    assert "SECRET_BODY_MARKER" not in captured.out
    assert "SECRET_BODY_MARKER" not in captured.err


def test_classify_one_applies_sender_weight() -> None:
    provider = FakeProvider()
    email = EmailInput(sender="a@b.com", subject="Q", body="Please reply?")
    skipped, result = classify_one(email, provider, importance_weight=1.2)
    assert skipped is False
    assert result is not None
    assert result.adjusted_urgency == apply_sender_weight(result.urgency, 1.2)
