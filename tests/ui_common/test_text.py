"""Tests for renderer-neutral text layout."""

from src.ui_common.text import wrap_text_to_width


def test_wrap_text_to_width_uses_caller_measurement() -> None:
    assert wrap_text_to_width("one two three", len, 7) == ["one two", "three"]


def test_wrap_text_to_width_preserves_empty_input() -> None:
    assert wrap_text_to_width("", len, 10) == [""]


def test_wrap_text_to_width_keeps_an_overwide_single_word() -> None:
    assert wrap_text_to_width("extraordinary", len, 5) == ["extraordinary"]
