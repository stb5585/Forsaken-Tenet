"""Tests for the opt-in dungeon touch-playtest overlay."""

from types import SimpleNamespace

import pygame

from src.ui_common.input import UiCommand
from src.ui_pygame.gui.dungeon_playtest_controls import DungeonPlaytestControls


class DummyScreen:
    """Minimal screen surface used to calculate control layout."""

    def get_size(self) -> tuple[int, int]:
        return (1024, 768)


def _controls() -> DungeonPlaytestControls:
    return DungeonPlaytestControls(SimpleNamespace(screen=DummyScreen()))


def test_layout_keeps_controls_above_the_message_area_and_non_overlapping() -> None:
    buttons = DungeonPlaytestControls.button_layout(1024, 768, 665)

    assert {button.command for button in buttons} == {
        UiCommand.DUNGEON_MOVE_FORWARD,
        UiCommand.DUNGEON_TURN_LEFT,
        UiCommand.DUNGEON_TURN_RIGHT,
        UiCommand.DUNGEON_TURN_AROUND,
        UiCommand.DUNGEON_INTERACT,
        UiCommand.OPEN_MAP,
        UiCommand.OPEN_MENU,
        UiCommand.PAGE_PREVIOUS,
        UiCommand.PAGE_NEXT,
    }
    assert all(button.rect.bottom <= 668 for button in buttons)
    assert not any(
        first.rect.colliderect(second.rect)
        for index, first in enumerate(buttons)
        for second in buttons[index + 1 :]
    )


def test_control_hit_testing_supports_mouse_and_normalized_touch_coordinates() -> None:
    controls = _controls()
    forward = next(
        button
        for button in controls.button_layout(1024, 768, 665)
        if button.command is UiCommand.DUNGEON_MOVE_FORWARD
    )
    center = forward.rect.center

    assert controls.command_at(center) is UiCommand.DUNGEON_MOVE_FORWARD
    assert (
        controls.command_from_event(
            SimpleNamespace(type=pygame.MOUSEBUTTONDOWN, button=1, pos=center)
        )
        is UiCommand.DUNGEON_MOVE_FORWARD
    )
    assert (
        controls.command_from_event(
            SimpleNamespace(type=pygame.FINGERDOWN, x=center[0] / 1024, y=center[1] / 768)
        )
        is UiCommand.DUNGEON_MOVE_FORWARD
    )


def test_render_draws_visible_button_surface() -> None:
    pygame.font.init()
    screen = pygame.Surface((1024, 768), pygame.SRCALPHA)
    controls = DungeonPlaytestControls(SimpleNamespace(screen=screen))
    forward = next(
        button
        for button in controls.button_layout(1024, 768, 665)
        if button.command is UiCommand.DUNGEON_MOVE_FORWARD
    )

    controls.render()

    assert screen.get_at((forward.rect.left + 6, forward.rect.top + 6)).a > 0
