"""Tests for Pygame-to-command translation."""

from types import SimpleNamespace

import pygame

from src.ui_common.input import UiCommand
from src.ui_pygame.input_adapter import dungeon_command_for_key, dungeon_command_from_event


def test_dungeon_command_for_key_preserves_existing_navigation_bindings() -> None:
    assert dungeon_command_for_key(pygame.K_w) is UiCommand.DUNGEON_MOVE_FORWARD
    assert dungeon_command_for_key(pygame.K_LEFT) is UiCommand.DUNGEON_TURN_LEFT
    assert dungeon_command_for_key(pygame.K_o) is UiCommand.DUNGEON_INTERACT
    assert dungeon_command_for_key(pygame.K_ESCAPE) is UiCommand.OPEN_MENU


def test_dungeon_command_from_event_ignores_non_keydown_events() -> None:
    assert dungeon_command_from_event(SimpleNamespace(type=pygame.KEYUP, key=pygame.K_w)) is None
    assert dungeon_command_from_event(SimpleNamespace(type=pygame.MOUSEBUTTONDOWN)) is None


def test_dungeon_debug_command_is_available_only_in_debug_mode() -> None:
    assert dungeon_command_for_key(pygame.K_l) is None
    assert dungeon_command_for_key(pygame.K_l, debug_mode=True) is UiCommand.DEBUG_LEVEL_UP
