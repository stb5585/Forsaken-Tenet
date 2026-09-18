"""Tests for the opt-in dungeon touch-playtest overlay."""

from types import SimpleNamespace

import pygame

from src.ui_common.input import UiCommand
from src.ui_pygame.display_scaling import DisplayConfiguration, LayoutMetrics
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
        UiCommand.OPEN_MENU,
    }
    assert all(button.rect.bottom <= 668 for button in buttons)
    assert not any(
        first.rect.colliderect(second.rect)
        for index, first in enumerate(buttons)
        for second in buttons[index + 1 :]
    )
    labels = {button.command: button.label for button in buttons}
    assert labels[UiCommand.DUNGEON_TURN_LEFT] == ""
    assert labels[UiCommand.DUNGEON_MOVE_FORWARD] == ""
    assert labels[UiCommand.DUNGEON_TURN_RIGHT] == ""
    assert labels[UiCommand.DUNGEON_TURN_AROUND] == ""
    assert labels[UiCommand.OPEN_MENU] == "MENU"

    buttons_by_command = {button.command: button for button in buttons}
    assert buttons_by_command[UiCommand.DUNGEON_MOVE_FORWARD].rect.centerx == (
        buttons_by_command[UiCommand.DUNGEON_TURN_AROUND].rect.centerx
    )
    assert buttons_by_command[UiCommand.DUNGEON_TURN_LEFT].rect.top == (
        buttons_by_command[UiCommand.DUNGEON_TURN_AROUND].rect.top
    )
    assert buttons_by_command[UiCommand.DUNGEON_TURN_RIGHT].rect.top == (
        buttons_by_command[UiCommand.DUNGEON_TURN_AROUND].rect.top
    )


def test_control_hit_testing_supports_native_touch_and_mouse_event_shapes() -> None:
    controls = _controls()
    forward = next(
        button
        for button in controls.button_layout(1024, 768, 665)
        if button.command is UiCommand.DUNGEON_MOVE_FORWARD
    )
    center = forward.rect.center

    assert controls.command_at(center) is UiCommand.DUNGEON_MOVE_FORWARD
    mouse_event = SimpleNamespace(type=pygame.MOUSEBUTTONDOWN, button=1, pos=center)
    mouse_event_without_pos = SimpleNamespace(
        type=pygame.MOUSEBUTTONDOWN, button=1, x=center[0], y=center[1], touch=True
    )
    native_touch_event = SimpleNamespace(
        type=pygame.FINGERDOWN,
        x=center[0] / 1024,
        y=center[1] / 768,
        finger_id=4,
        touch_id=1,
    )

    for event in (mouse_event, mouse_event_without_pos, native_touch_event):
        assert _controls().command_from_event(event, now_ms=100) is UiCommand.DUNGEON_MOVE_FORWARD


def test_control_press_deduplicates_native_touch_then_mouse_emulation() -> None:
    controls = _controls()
    center = next(
        button.rect.center
        for button in controls.button_layout(1024, 768, 665)
        if button.command is UiCommand.DUNGEON_MOVE_FORWARD
    )

    assert (
        controls.command_from_event(
            SimpleNamespace(type=pygame.FINGERDOWN, x=center[0] / 1024, y=center[1] / 768),
            now_ms=100,
        )
        is UiCommand.DUNGEON_MOVE_FORWARD
    )
    assert (
        controls.command_from_event(
            SimpleNamespace(type=pygame.MOUSEBUTTONDOWN, button=1, pos=center), now_ms=110
        )
        is None
    )


def test_control_press_deduplicates_mouse_emulation_then_native_touch() -> None:
    controls = _controls()
    center = next(
        button.rect.center
        for button in controls.button_layout(1024, 768, 665)
        if button.command is UiCommand.DUNGEON_MOVE_FORWARD
    )

    assert (
        controls.command_from_event(
            SimpleNamespace(type=pygame.MOUSEBUTTONDOWN, button=1, pos=center), now_ms=100
        )
        is UiCommand.DUNGEON_MOVE_FORWARD
    )
    assert (
        controls.command_from_event(
            SimpleNamespace(type=pygame.FINGERDOWN, x=center[0] / 1024, y=center[1] / 768),
            now_ms=110,
        )
        is None
    )


def test_control_press_debounces_repeated_mouse_clicks() -> None:
    controls = _controls()
    center = next(
        button.rect.center
        for button in controls.button_layout(1024, 768, 665)
        if button.command is UiCommand.DUNGEON_TURN_LEFT
    )
    mouse_event = SimpleNamespace(type=pygame.MOUSEBUTTONDOWN, button=1, pos=center)

    assert controls.command_from_event(mouse_event, now_ms=100) is UiCommand.DUNGEON_TURN_LEFT
    assert controls.command_from_event(mouse_event, now_ms=200) is None
    assert controls.command_from_event(mouse_event, now_ms=400) is UiCommand.DUNGEON_TURN_LEFT


def test_control_press_does_not_suppress_distinct_mouse_click() -> None:
    controls = _controls()
    forward = next(
        button.rect.center
        for button in controls.button_layout(1024, 768, 665)
        if button.command is UiCommand.DUNGEON_MOVE_FORWARD
    )
    turn_left = next(
        button.rect.center
        for button in controls.button_layout(1024, 768, 665)
        if button.command is UiCommand.DUNGEON_TURN_LEFT
    )

    assert (
        controls.command_from_event(
            SimpleNamespace(type=pygame.FINGERDOWN, x=forward[0] / 1024, y=forward[1] / 768),
            now_ms=100,
        )
        is UiCommand.DUNGEON_MOVE_FORWARD
    )
    assert (
        controls.command_from_event(
            SimpleNamespace(type=pygame.MOUSEBUTTONDOWN, button=1, pos=turn_left), now_ms=110
        )
        is UiCommand.DUNGEON_TURN_LEFT
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


def test_native_1080p_layout_scales_targets_and_mouse_hit_testing() -> None:
    pygame.font.init()
    screen = pygame.Surface((1920, 1080), pygame.SRCALPHA)
    metrics = LayoutMetrics(
        DisplayConfiguration.for_viewport(fullscreen=True, render_size=screen.get_size())
    )
    controls = DungeonPlaytestControls(SimpleNamespace(screen=screen, layout_metrics=metrics))
    forward = next(
        button for button in controls._buttons() if button.command is UiCommand.DUNGEON_MOVE_FORWARD
    )

    assert forward.rect.width > 108
    assert (
        controls.command_from_event(
            SimpleNamespace(type=pygame.MOUSEBUTTONDOWN, button=1, pos=forward.rect.center),
            now_ms=100,
        )
        is UiCommand.DUNGEON_MOVE_FORWARD
    )
