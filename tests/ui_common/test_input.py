"""Tests for platform-neutral presentation commands."""

from src.ui_common.input import UiCommand


def test_ui_commands_have_stable_serializable_values() -> None:
    assert UiCommand.DUNGEON_MOVE_FORWARD == "dungeon_move_forward"
    assert UiCommand.OPEN_MENU == "open_menu"
