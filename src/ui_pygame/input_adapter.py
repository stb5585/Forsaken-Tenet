"""Translate Pygame input events into platform-neutral presentation commands."""

from __future__ import annotations

from typing import Any

import pygame

from src.ui_common.input import UiCommand

_DUNGEON_KEY_COMMANDS: dict[int, UiCommand] = {
    pygame.K_w: UiCommand.DUNGEON_MOVE_FORWARD,
    pygame.K_UP: UiCommand.DUNGEON_MOVE_FORWARD,
    pygame.K_a: UiCommand.DUNGEON_TURN_LEFT,
    pygame.K_LEFT: UiCommand.DUNGEON_TURN_LEFT,
    pygame.K_d: UiCommand.DUNGEON_TURN_RIGHT,
    pygame.K_RIGHT: UiCommand.DUNGEON_TURN_RIGHT,
    pygame.K_s: UiCommand.DUNGEON_TURN_AROUND,
    pygame.K_DOWN: UiCommand.DUNGEON_TURN_AROUND,
    pygame.K_u: UiCommand.DUNGEON_USE_STAIRS_UP,
    pygame.K_j: UiCommand.DUNGEON_USE_STAIRS_DOWN,
    pygame.K_o: UiCommand.DUNGEON_INTERACT,
    pygame.K_PAGEUP: UiCommand.PAGE_PREVIOUS,
    pygame.K_PAGEDOWN: UiCommand.PAGE_NEXT,
    pygame.K_m: UiCommand.OPEN_MAP,
    pygame.K_c: UiCommand.OPEN_CHARACTER,
    pygame.K_ESCAPE: UiCommand.OPEN_MENU,
}


def dungeon_command_for_key(key: int, *, debug_mode: bool = False) -> UiCommand | None:
    """Return the dungeon command bound to a Pygame key, if any.

    Debug-only shortcuts are intentionally excluded unless debug mode is active.
    """
    if debug_mode and key == pygame.K_l:
        return UiCommand.DEBUG_LEVEL_UP
    return _DUNGEON_KEY_COMMANDS.get(key)


def dungeon_command_from_event(event: Any, *, debug_mode: bool = False) -> UiCommand | None:
    """Return a dungeon command for a Pygame key-down event, if one is bound."""
    if getattr(event, "type", None) != pygame.KEYDOWN:
        return None
    return dungeon_command_for_key(getattr(event, "key", None), debug_mode=debug_mode)
