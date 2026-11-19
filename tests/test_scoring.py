import pytest

from app.pipeline.scoring import apply_sender_weight


def test_weight_raises_then_caps_at_five() -> None:
    assert apply_sender_weight(5, 1.2) == 5.0
    assert apply_sender_weight(4, 1.2) == pytest.approx(4.8)


def test_weight_lowers_score() -> None:
    assert apply_sender_weight(3, 0.7) == pytest.approx(2.1)


def test_default_weight_unchanged() -> None:
    assert apply_sender_weight(4, 1.0) == 4.0
