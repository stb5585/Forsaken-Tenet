"""Opt-in on-screen controls for touch and remote dungeon playtesting."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import pygame

from src.ui_common.input import UiCommand

_MESSAGE_AREA_HEIGHT = 100
_PRESS_DEBOUNCE_MS = 250
_DUPLICATE_PRESS_DISTANCE_PX = 8


@dataclass(frozen=True)
class PlaytestControlButton:
    """One visible dungeon command target."""

    command: UiCommand
    label: str
    rect: pygame.Rect
    accent_color: tuple[int, int, int]


class DungeonPlaytestControls:
    """Render and hit-test touch targets over the dungeon exploration view."""

    def __init__(self, presenter: Any, *, input_diagnostics: bool = False):
        self.presenter = presenter
        self.input_diagnostics = input_diagnostics
        self._last_press: tuple[str, tuple[int, int], int] | None = None

    @staticmethod
    def button_layout(
        width: int, height: int, hud_x: int, *, metrics=None
    ) -> tuple[PlaytestControlButton, ...]:
        """Build non-overlapping control targets above the dungeon message area."""
        unit = metrics.unit if metrics is not None else round
        message_height = unit(_MESSAGE_AREA_HEIGHT)
        button_size = max(unit(56), min(unit(108), (height - message_height) // 6))
        gap = max(unit(8), button_size // 7)
        margin = max(unit(12), button_size // 4)
        content_bottom = height - message_height - margin
        # Resemble physical cursor keys: up in the middle, then left/down/right
        # below it.  The menu remains reachable at the upper-left of the view.
        top_row_y = content_bottom - (button_size * 2) - gap
        bottom_row_y = content_bottom - button_size
        left_x = margin
        center_x = left_x + button_size + gap
        right_x = center_x + button_size + gap

        use_size = int(button_size * 1.35)
        use_x = hud_x - margin - use_size
        use_y = content_bottom - use_size

        return (
            PlaytestControlButton(
                UiCommand.OPEN_MENU,
                "MENU",
                pygame.Rect(margin, margin, button_size, button_size),
                (145, 93, 91),
            ),
            PlaytestControlButton(
                UiCommand.DUNGEON_MOVE_FORWARD,
                "",
                pygame.Rect(center_x, top_row_y, button_size, button_size),
                (77, 156, 102),
            ),
            PlaytestControlButton(
                UiCommand.DUNGEON_TURN_LEFT,
                "",
                pygame.Rect(left_x, bottom_row_y, button_size, button_size),
                (72, 134, 190),
            ),
            PlaytestControlButton(
                UiCommand.DUNGEON_TURN_AROUND,
                "",
                pygame.Rect(center_x, bottom_row_y, button_size, button_size),
                (72, 134, 190),
            ),
            PlaytestControlButton(
                UiCommand.DUNGEON_TURN_RIGHT,
                "",
                pygame.Rect(right_x, bottom_row_y, button_size, button_size),
                (72, 134, 190),
            ),
            PlaytestControlButton(
                UiCommand.DUNGEON_INTERACT,
                "USE",
                pygame.Rect(use_x, use_y, use_size, use_size),
                (185, 143, 53),
            ),
        )

    def _buttons(self) -> tuple[PlaytestControlButton, ...]:
        screen = self.presenter.screen
        width, height = screen.get_size()
        metrics = getattr(self.presenter, "layout_metrics", None)
        hud_fraction = metrics.dungeon_hud_fraction if metrics is not None else 0.35
        hud_x = width - int(width * hud_fraction)
        return self.button_layout(width, height, hud_x, metrics=metrics)

    def command_at(self, position: tuple[int, int]) -> UiCommand | None:
        """Return the command whose visible target contains a screen position."""
        for button in self._buttons():
            if button.rect.collidepoint(position):
                return button.command
        return None

    def command_from_event(self, event: Any, *, now_ms: int | None = None) -> UiCommand | None:
        """Normalize native and mouse-emulated touch presses into a control command.

        Native ``FINGERDOWN`` coordinates are normalized by SDL. Mouse presses,
        including touch presses emulated by SDL or Moonlight, use window pixels.
        Same-location presses are debounced to avoid click-through or duplicate
        actions caused by a single physical press.
        """
        press = self._press_from_event(event)
        if press is None:
            return None

        source, position = press
        self._diagnose_press(event, source, position)
        command = self.command_at(position)
        if command is None:
            return None

        press_time = pygame.time.get_ticks() if now_ms is None else now_ms
        if self._is_duplicate_press(source, position, press_time):
            return None
        self._last_press = (source, position, press_time)
        return command

    def _press_from_event(self, event: Any) -> tuple[str, tuple[int, int]] | None:
        """Extract a screen-space press position from supported Pygame events."""
        event_type = getattr(event, "type", None)
        if event_type == pygame.FINGERDOWN:
            width, height = self.presenter.screen.get_size()
            return (
                "finger",
                (
                    round(float(getattr(event, "x", -1.0)) * width),
                    round(float(getattr(event, "y", -1.0)) * height),
                ),
            )
        if event_type == pygame.MOUSEBUTTONDOWN and getattr(event, "button", None) == 1:
            position = getattr(event, "pos", None)
            pointer_position = getattr(self.presenter, "pointer_position", None)
            if callable(pointer_position):
                position = pointer_position(event)
            if position is None:
                position = (getattr(event, "x", -1), getattr(event, "y", -1))
            return "mouse", (round(float(position[0])), round(float(position[1])))
        return None

    def _is_duplicate_press(self, source: str, position: tuple[int, int], now_ms: int) -> bool:
        """Return whether a recent same-location physical press was already handled."""
        if self._last_press is None:
            return False
        _last_source, last_position, last_time = self._last_press
        if now_ms - last_time > _PRESS_DEBOUNCE_MS:
            return False
        return (
            abs(position[0] - last_position[0]) <= _DUPLICATE_PRESS_DISTANCE_PX
            and abs(position[1] - last_position[1]) <= _DUPLICATE_PRESS_DISTANCE_PX
        )

    def _diagnose_press(self, event: Any, source: str, position: tuple[int, int]) -> None:
        """Print concise, opt-in event data for local touchscreen investigation."""
        if not self.input_diagnostics:
            return
        fields = {
            name: getattr(event, name)
            for name in ("pos", "x", "y", "button", "touch", "finger_id", "touch_id")
            if hasattr(event, name)
        }
        print(
            "Dungeon playtest input: "
            f"type={pygame.event.event_name(getattr(event, 'type', pygame.NOEVENT))} "
            f"source={source} screen_position={position} fields={fields}"
        )

    def render(self) -> None:
        """Draw translucent, touch-sized controls over the current dungeon frame."""
        screen = self.presenter.screen
        metrics = getattr(self.presenter, "layout_metrics", None)
        font_size = metrics.font_size(24) if metrics is not None else 24
        font = pygame.font.Font(None, font_size)
        for button in self._buttons():
            button_surface = pygame.Surface(button.rect.size, pygame.SRCALPHA)
            button_surface.fill((*button.accent_color, 185))
            screen.blit(button_surface, button.rect)
            border_width = metrics.stroke(2) if metrics is not None else 2
            border_radius = metrics.unit(8) if metrics is not None else 8
            pygame.draw.rect(
                screen, (225, 225, 225), button.rect, border_width, border_radius=border_radius
            )
            if button.command in {
                UiCommand.DUNGEON_TURN_LEFT,
                UiCommand.DUNGEON_MOVE_FORWARD,
                UiCommand.DUNGEON_TURN_RIGHT,
                UiCommand.DUNGEON_TURN_AROUND,
            }:
                self._draw_direction_arrow(screen, button)
            else:
                label = font.render(button.label, True, (255, 255, 255))
                screen.blit(label, label.get_rect(center=button.rect.center))

    @staticmethod
    def _draw_direction_arrow(screen: pygame.Surface, button: PlaytestControlButton) -> None:
        """Draw a font-independent directional arrow for a navigation target."""
        direction = {
            UiCommand.DUNGEON_TURN_LEFT: (-1, 0),
            UiCommand.DUNGEON_MOVE_FORWARD: (0, -1),
            UiCommand.DUNGEON_TURN_RIGHT: (1, 0),
            UiCommand.DUNGEON_TURN_AROUND: (0, 1),
        }[button.command]
        dx, dy = direction
        center_x, center_y = button.rect.center
        shaft_length = max(14, min(button.rect.width, button.rect.height) // 3)
        head_size = max(9, shaft_length // 2)
        start = (center_x - dx * shaft_length // 2, center_y - dy * shaft_length // 2)
        end = (center_x + dx * shaft_length // 2, center_y + dy * shaft_length // 2)
        perpendicular = (-dy, dx)
        head = [
            end,
            (
                end[0] - dx * head_size + perpendicular[0] * head_size,
                end[1] - dy * head_size + perpendicular[1] * head_size,
            ),
            (
                end[0] - dx * head_size - perpendicular[0] * head_size,
                end[1] - dy * head_size - perpendicular[1] * head_size,
            ),
        ]
        pygame.draw.line(screen, (255, 255, 255), start, end, width=5)
        pygame.draw.polygon(screen, (255, 255, 255), head)
