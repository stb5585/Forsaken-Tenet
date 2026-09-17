"""Opt-in on-screen controls for touch and remote dungeon playtesting."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import pygame

from src.ui_common.input import UiCommand

_MESSAGE_AREA_HEIGHT = 100


@dataclass(frozen=True)
class PlaytestControlButton:
    """One visible dungeon command target."""

    command: UiCommand
    label: str
    rect: pygame.Rect
    accent_color: tuple[int, int, int]


class DungeonPlaytestControls:
    """Render and hit-test touch targets over the dungeon exploration view."""

    def __init__(self, presenter: Any):
        self.presenter = presenter

    @staticmethod
    def button_layout(width: int, height: int, hud_x: int) -> tuple[PlaytestControlButton, ...]:
        """Build non-overlapping control targets above the dungeon message area."""
        button_size = max(56, min(84, (height - _MESSAGE_AREA_HEIGHT) // 7))
        gap = max(8, button_size // 7)
        margin = max(12, button_size // 4)
        content_bottom = height - _MESSAGE_AREA_HEIGHT - margin
        top_row_y = content_bottom - (button_size * 2) - gap
        bottom_row_y = content_bottom - button_size
        left_x = margin
        center_x = left_x + button_size + gap
        right_x = center_x + button_size + gap

        use_size = int(button_size * 1.35)
        use_x = hud_x - margin - use_size
        use_y = content_bottom - use_size
        log_height = max(38, button_size // 2)
        log_y = margin

        return (
            PlaytestControlButton(
                UiCommand.DUNGEON_TURN_LEFT,
                "TURN L",
                pygame.Rect(left_x, top_row_y, button_size, button_size),
                (72, 134, 190),
            ),
            PlaytestControlButton(
                UiCommand.DUNGEON_MOVE_FORWARD,
                "FWD",
                pygame.Rect(center_x, top_row_y, button_size, button_size),
                (77, 156, 102),
            ),
            PlaytestControlButton(
                UiCommand.DUNGEON_TURN_RIGHT,
                "TURN R",
                pygame.Rect(right_x, top_row_y, button_size, button_size),
                (72, 134, 190),
            ),
            PlaytestControlButton(
                UiCommand.OPEN_MAP,
                "MAP",
                pygame.Rect(left_x, bottom_row_y, button_size, button_size),
                (120, 104, 175),
            ),
            PlaytestControlButton(
                UiCommand.DUNGEON_TURN_AROUND,
                "TURN 180",
                pygame.Rect(center_x, bottom_row_y, button_size, button_size),
                (72, 134, 190),
            ),
            PlaytestControlButton(
                UiCommand.OPEN_MENU,
                "MENU",
                pygame.Rect(right_x, bottom_row_y, button_size, button_size),
                (145, 93, 91),
            ),
            PlaytestControlButton(
                UiCommand.DUNGEON_INTERACT,
                "USE",
                pygame.Rect(use_x, use_y, use_size, use_size),
                (185, 143, 53),
            ),
            PlaytestControlButton(
                UiCommand.PAGE_PREVIOUS,
                "LOG +",
                pygame.Rect(use_x, log_y, use_size, log_height),
                (93, 103, 119),
            ),
            PlaytestControlButton(
                UiCommand.PAGE_NEXT,
                "LOG -",
                pygame.Rect(use_x, log_y + log_height + gap, use_size, log_height),
                (93, 103, 119),
            ),
        )

    def _buttons(self) -> tuple[PlaytestControlButton, ...]:
        screen = self.presenter.screen
        width, height = screen.get_size()
        return self.button_layout(width, height, int(width * 0.65))

    def command_at(self, position: tuple[int, int]) -> UiCommand | None:
        """Return the command whose visible target contains a screen position."""
        for button in self._buttons():
            if button.rect.collidepoint(position):
                return button.command
        return None

    def command_from_event(self, event: Any) -> UiCommand | None:
        """Normalize mouse and touch presses into an on-screen control command."""
        if event.type == pygame.MOUSEBUTTONDOWN and getattr(event, "button", None) == 1:
            return self.command_at(getattr(event, "pos", (-1, -1)))
        if event.type == pygame.FINGERDOWN:
            width, height = self.presenter.screen.get_size()
            position = (
                round(getattr(event, "x", -1.0) * width),
                round(getattr(event, "y", -1.0) * height),
            )
            return self.command_at(position)
        return None

    def render(self) -> None:
        """Draw translucent, touch-sized controls over the current dungeon frame."""
        screen = self.presenter.screen
        font = pygame.font.Font(None, max(16, min(24, screen.get_height() // 32)))
        for button in self._buttons():
            button_surface = pygame.Surface(button.rect.size, pygame.SRCALPHA)
            button_surface.fill((*button.accent_color, 185))
            screen.blit(button_surface, button.rect)
            pygame.draw.rect(screen, (225, 225, 225), button.rect, 2, border_radius=8)
            label = font.render(button.label, True, (255, 255, 255))
            screen.blit(label, label.get_rect(center=button.rect.center))
