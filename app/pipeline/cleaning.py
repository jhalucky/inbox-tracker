from __future__ import annotations

import re

MAX_BODY_CHARS = 2000

_QUOTE_LINE_RE = re.compile(r"^\s*>")
_CHAIN_RE = re.compile(
    r"\n(?:"
    r"On .{0,200} wrote:\s*$"
    r"|-{2,}\s*Original Message\s*-{2,}"
    r"|_{5,}"
    r"|Begin forwarded message:?\s*$"
    r"|From:\s+.+\n(?:Sent|Date):"
    r")",
    re.IGNORECASE | re.MULTILINE,
)


def clean_body(body: str, max_chars: int = MAX_BODY_CHARS) -> str:
    if not body:
        return ""
    text = body.replace("\r\n", "\n").replace("\r", "\n")
    match = _CHAIN_RE.search("\n" + text)
    if match:
        text = text[: max(match.start() - 1, 0)]

    lines = [line for line in text.split("\n") if not _QUOTE_LINE_RE.match(line)]
    cleaned = re.sub(r"\n{3,}", "\n\n", "\n".join(lines)).strip()
    return cleaned[:max_chars]
