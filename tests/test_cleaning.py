from app.pipeline.cleaning import MAX_BODY_CHARS, clean_body


def test_strips_quoted_reply_lines() -> None:
    body = "Please send dates.\n\n> Earlier I said hello\n> more quoted text\n"
    cleaned = clean_body(body)
    assert "Please send dates." in cleaned
    assert "quoted text" not in cleaned
    assert "Earlier I said" not in cleaned


def test_cuts_on_wrote_chain() -> None:
    body = (
        "Can we meet tomorrow?\n\n"
        "On Mon, Jan 1, 2024 at 9:00 AM Bob wrote:\n"
        "Hello from the past\n"
    )
    cleaned = clean_body(body)
    assert "Can we meet tomorrow?" in cleaned
    assert "Bob wrote" not in cleaned
    assert "Hello from the past" not in cleaned


def test_cuts_original_message_separator() -> None:
    body = "New ask here.\n\n-----Original Message-----\nFrom: old\nOld body"
    cleaned = clean_body(body)
    assert "New ask here." in cleaned
    assert "Old body" not in cleaned


def test_caps_length_at_2000() -> None:
    cleaned = clean_body("a" * 5000)
    assert len(cleaned) == MAX_BODY_CHARS
