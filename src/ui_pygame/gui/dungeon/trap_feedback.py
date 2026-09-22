"""Small cached dungeon-viewport effects for damaging traps."""

from __future__ import annotations

from collections import deque

import pygame


class TrapImpactRenderer:
    """Animate trap hits directly over the cached dungeon scene."""

    DURATION_MS = 420

    def __init__(self, presenter):
        self.presenter = presenter
        self._pending = deque()
        self._active = None
        self._started_at = 0
        self._font_cache: dict[int, pygame.font.Font] = {}

    @property
    def active(self) -> bool:
        return self._active is not None or bool(self._pending)

    def queue(self, feedback) -> None:
        """Queue one structured core feedback payload; no Pygame type crosses core."""
        self._pending.append(feedback)

    @staticmethod
    def sound_name(feedback) -> str:
        if feedback.category == "physical":
            return "hit"
        element = (feedback.element or "").lower()
        if element == "fire":
            return "spell_fire"
        if element in {"ice", "water"}:
            return "spell_ice"
        if element == "electric":
            return "spell_lightning"
        return "spell_cast"

    def render(self) -> bool:
        """Draw the current effect and return whether another frame is needed."""
        now = pygame.time.get_ticks()
        if self._active is None and self._pending:
            self._active = self._pending.popleft()
            self._started_at = now
        if self._active is None:
            return False
        elapsed = now - self._started_at
        if elapsed >= self.DURATION_MS:
            self._active = None
            return bool(self._pending)

        screen = self.presenter.screen
        width, height = screen.get_size()
        metrics = self.presenter.layout_metrics
        viewport_width = int(width * metrics.dungeon_view_fraction)
        center = (viewport_width // 2, int(height * 0.54))
        progress = elapsed / self.DURATION_MS
        alpha = max(40, int(255 * (1.0 - progress)))
        size = metrics.unit(28) + int(metrics.unit(32) * progress)
        if self._active.category == "physical":
            start = (center[0] - int(size * 2.2), center[1] - int(size * 0.7))
            pygame.draw.line(screen, (245, 220, 145), start, center, metrics.stroke(3))
            pygame.draw.line(
                screen,
                (255, 100, 80),
                (center[0] - size, center[1] + size),
                (center[0] + size, center[1] - size),
                metrics.stroke(3),
            )
        else:
            color = {
                "Fire": (255, 110, 55),
                "Ice": (110, 210, 255),
                "Electric": (240, 230, 90),
            }.get(
                self._active.element,
                (180, 110, 255),
            )
            pygame.draw.circle(screen, color, center, size, metrics.stroke(3))
            pygame.draw.circle(screen, (*color, alpha), center, max(1, size // 3))
        font_size = metrics.font_size(30)
        font = self._font_cache.setdefault(font_size, pygame.font.Font(None, font_size))
        text = font.render(f"-{self._active.damage}", True, (255, 105, 90))
        screen.blit(text, text.get_rect(center=(center[0], center[1] - size - text.get_height())))
        return True
