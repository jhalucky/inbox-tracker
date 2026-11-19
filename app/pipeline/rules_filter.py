from __future__ import annotations

import re

from app.providers.base import EmailInput

_NO_REPLY_LOCAL = re.compile(
    r"^(?:no[\._-]?reply|do[\._-]?not[\._-]?reply|notifications?|mailer-daemon|postmaster|bounce)"
    r"|[\._-](?:no[\._-]?reply)$",
    re.IGNORECASE,
)
_MAILER_DAEMON_RE = re.compile(r"mailer-daemon", re.IGNORECASE)


def _headers(email: EmailInput) -> dict[str, str]:
    return {key.lower(): value for key, value in email.headers.items()}


def _address(sender: str) -> str:
    match = re.search(r"<([^>]+)>", sender)
    return (match.group(1) if match else sender).strip().lower()


def _is_noreply_or_notification(sender: str) -> bool:
    if _MAILER_DAEMON_RE.search(sender):
        return True
    addr = _address(sender)
    local = addr.split("@", 1)[0]
    return bool(_NO_REPLY_LOCAL.search(local))


def _is_calendar(email: EmailInput, headers: dict[str, str]) -> bool:
    content_type = headers.get("content-type", "").lower()
    if "text/calendar" in content_type or "method=request" in content_type:
        return True
    return "BEGIN:VCALENDAR" in email.body[:500].upper()


def should_skip(email: EmailInput) -> bool:
    headers = _headers(email)
    if headers.get("list-unsubscribe"):
        return True

    precedence = headers.get("precedence", "").lower()
    if precedence in {"bulk", "list", "junk"}:
        return True

    auto_submitted = headers.get("auto-submitted", "").strip().lower()
    if auto_submitted and auto_submitted != "no":
        return True

    if _is_noreply_or_notification(email.sender):
        return True
    if _is_calendar(email, headers):
        return True
    return False
