"""Shared title-backdrop treatment for the new-character flow."""

from __future__ import annotations

from collections.abc import Callable

import pygame

BackgroundDrawFunc = Callable[[], object]


def draw_creation_background(
    screen: pygame.Surface,
    size: tuple[int, int],
    background_draw_func: BackgroundDrawFunc | None,
    *,
    fallback_color: tuple[int, int, int] = (0, 0, 0),
) -> None:
    """Draw the title backdrop beneath a restrained readability veil."""
    if background_draw_func is None:
        screen.fill(fallback_color)
        return
    background_draw_func()
    veil = pygame.Surface(size, pygame.SRCALPHA)
    veil.fill((0, 0, 0, 42))
    screen.blit(veil, (0, 0))


def draw_creation_panel(
    screen: pygame.Surface,
    rect: pygame.Rect,
    border_color: tuple[int, int, int],
    background_draw_func: BackgroundDrawFunc | None,
    *,
    fill_color: tuple[int, int, int] = (0, 0, 0),
    alpha: int = 150,
) -> None:
    """Draw an opaque fallback or translucent panel over the title art."""
    if background_draw_func is None:
        pygame.draw.rect(screen, fill_color, rect)
    else:
        panel = pygame.Surface(rect.size, pygame.SRCALPHA)
        panel.fill((*fill_color, alpha))
        screen.blit(panel, rect.topleft)
    pygame.draw.rect(screen, border_color, rect, 2)
