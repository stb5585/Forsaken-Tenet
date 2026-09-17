"""Presentation commands independent of any input device or frontend."""

from enum import StrEnum


class UiCommand(StrEnum):
    """Named presentation actions shared by frontends and input adapters."""

    NAVIGATE_UP = "navigate_up"
    NAVIGATE_DOWN = "navigate_down"
    CONFIRM = "confirm"
    CANCEL = "cancel"
    PAGE_PREVIOUS = "page_previous"
    PAGE_NEXT = "page_next"
    DUNGEON_MOVE_FORWARD = "dungeon_move_forward"
    DUNGEON_TURN_LEFT = "dungeon_turn_left"
    DUNGEON_TURN_RIGHT = "dungeon_turn_right"
    DUNGEON_TURN_AROUND = "dungeon_turn_around"
    DUNGEON_USE_STAIRS_UP = "dungeon_use_stairs_up"
    DUNGEON_USE_STAIRS_DOWN = "dungeon_use_stairs_down"
    DUNGEON_INTERACT = "dungeon_interact"
    OPEN_MAP = "open_map"
    OPEN_CHARACTER = "open_character"
    OPEN_MENU = "open_menu"
    DEBUG_LEVEL_UP = "debug_level_up"
