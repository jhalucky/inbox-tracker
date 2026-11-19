from app.pipeline.rules_filter import should_skip
from app.providers.base import EmailInput


def _email(**kwargs: object) -> EmailInput:
    data = {"from": "Ada <ada@example.com>", "subject": "Hello", "body": "Hi", "headers": {}}
    data.update(kwargs)
    return EmailInput.model_validate(data)


def test_skip_list_unsubscribe() -> None:
    email = _email(headers={"List-Unsubscribe": "<mailto:unsub@example.com>"})
    assert should_skip(email) is True


def test_skip_precedence_bulk_list_junk() -> None:
    for value in ("bulk", "list", "junk", "Bulk"):
        assert should_skip(_email(headers={"Precedence": value})) is True


def test_skip_auto_submitted() -> None:
    assert should_skip(_email(headers={"Auto-Submitted": "auto-generated"})) is True
    assert should_skip(_email(headers={"Auto-Submitted": "no"})) is False


def test_skip_noreply_and_notification_senders() -> None:
    assert should_skip(_email(**{"from": "GitHub <noreply@github.com>"})) is True
    assert should_skip(_email(**{"from": "no-reply@example.com"})) is True
    assert should_skip(_email(**{"from": "notifications@stripe.com"})) is True


def test_skip_mailer_daemon() -> None:
    assert should_skip(_email(**{"from": "Mailer-Daemon <mailer-daemon@googlemail.com>"})) is True


def test_skip_calendar_invitation() -> None:
    by_header = _email(headers={"Content-Type": "text/calendar; method=REQUEST"})
    by_body = _email(body="BEGIN:VCALENDAR\nMETHOD:REQUEST\nEND:VCALENDAR")
    assert should_skip(by_header) is True
    assert should_skip(by_body) is True


def test_does_not_skip_normal_person() -> None:
    email = _email(**{"from": "Ada Lead <ada@newco.example>", "body": "Can we talk?"})
    assert should_skip(email) is False
