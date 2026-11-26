"""Tests for persistent Pygame player preferences."""

import json

import pytest

from src.ui_pygame import user_settings


def test_dialogue_speed_round_trip(tmp_path):
    path = tmp_path / "ui_settings.json"

    assert user_settings.load_dialogue_speed(path) == user_settings.DEFAULT_DIALOGUE_CPS

    user_settings.save_dialogue_speed(60, path)

    assert user_settings.load_dialogue_speed(path) == 60
    assert json.loads(path.read_text(encoding="utf-8")) == {"dialogue_characters_per_second": 60}


@pytest.mark.parametrize("content", ["not json", "[]", '{"dialogue_characters_per_second": 9}'])
def test_invalid_dialogue_speed_uses_default(tmp_path, content):
    path = tmp_path / "ui_settings.json"
    path.write_text(content, encoding="utf-8")

    assert user_settings.load_dialogue_speed(path) == user_settings.DEFAULT_DIALOGUE_CPS


def test_rejects_unsupported_dialogue_speed(tmp_path):
    with pytest.raises(ValueError, match="unsupported dialogue speed"):
        user_settings.save_dialogue_speed(9, tmp_path / "ui_settings.json")
