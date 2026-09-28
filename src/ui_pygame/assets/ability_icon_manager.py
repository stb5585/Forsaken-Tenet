"""Cached ability-icon atlas loading for Pygame progression views."""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from pathlib import Path

import pygame

from src.paths import PYGAME_ASSETS_DIR

logger = logging.getLogger(__name__)

ABILITY_ICON_ROOT = PYGAME_ASSETS_DIR / "ability_icons"
ABILITY_ICON_ATLAS = ABILITY_ICON_ROOT / "ability_icons.png"
ABILITY_ICON_MANIFEST = ABILITY_ICON_ROOT / "ability_icons.json"


@dataclass(frozen=True)
class AbilityIconFrame:
    """Atlas rectangle for one semantic ability category."""

    key: str
    rect: pygame.Rect


class AbilityIconManager:
    """Resolve semantic progression icon keys to cached surfaces."""

    def __init__(
        self,
        atlas_path: Path | None = None,
        manifest_path: Path | None = None,
    ) -> None:
        self.atlas_path = Path(atlas_path or ABILITY_ICON_ATLAS)
        self.manifest_path = Path(manifest_path or ABILITY_ICON_MANIFEST)
        self.frames: dict[str, AbilityIconFrame] = {}
        self._atlas: pygame.Surface | None = None
        self._icons: dict[str, pygame.Surface] = {}
        self._scaled_icons: dict[tuple[str, tuple[int, int]], pygame.Surface] = {}
        self._fallback: pygame.Surface | None = None
        self._load_manifest()

    def _load_manifest(self) -> None:
        try:
            data = json.loads(self.manifest_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            logger.warning("Could not load ability icon manifest %s: %s", self.manifest_path, exc)
            return
        for key, entry in data.items():
            try:
                rect = pygame.Rect(
                    int(entry["x"]),
                    int(entry["y"]),
                    int(entry["w"]),
                    int(entry["h"]),
                )
            except (KeyError, TypeError, ValueError) as exc:
                logger.warning("Skipping invalid ability icon frame %s: %s", key, exc)
                continue
            self.frames[str(key)] = AbilityIconFrame(str(key), rect)

    def _atlas_surface(self) -> pygame.Surface | None:
        if self._atlas is not None:
            return self._atlas
        try:
            atlas = pygame.image.load(str(self.atlas_path))
        except (OSError, pygame.error) as exc:
            logger.warning("Could not load ability icon atlas %s: %s", self.atlas_path, exc)
            return None
        try:
            atlas = atlas.convert_alpha()
        except pygame.error:
            atlas = atlas.copy()
        self._atlas = atlas
        return atlas

    def get_icon(self, icon_key: str) -> pygame.Surface:
        """Return a native 32×32 icon or a safe fallback surface."""
        if icon_key == "unknown":
            return self.unknown_surface()
        cached = self._icons.get(icon_key)
        if cached is not None:
            return cached
        frame = self.frames.get(icon_key)
        atlas = self._atlas_surface()
        if frame is None or atlas is None:
            logger.warning("Ability icon is unavailable: %s", icon_key)
            return self.fallback_surface()
        try:
            icon = atlas.subsurface(frame.rect).copy()
        except ValueError as exc:
            logger.warning("Ability icon frame is out of bounds for %s: %s", icon_key, exc)
            return self.fallback_surface()
        self._icons[icon_key] = icon
        return icon

    def get_scaled_icon(self, icon_key: str, size: tuple[int, int]) -> pygame.Surface:
        """Return a cached icon scaled for a stable render slot size."""
        target = (max(1, int(size[0])), max(1, int(size[1])))
        cache_key = (icon_key, target)
        cached = self._scaled_icons.get(cache_key)
        if cached is None:
            cached = pygame.transform.smoothscale(self.get_icon(icon_key), target)
            self._scaled_icons[cache_key] = cached
        return cached

    def fallback_surface(self) -> pygame.Surface:
        """Return a deterministic missing-icon marker."""
        if self._fallback is None:
            surface = pygame.Surface((32, 32), pygame.SRCALPHA)
            surface.fill((28, 24, 34, 235))
            pygame.draw.rect(surface, (218, 165, 32), surface.get_rect(), 2)
            pygame.draw.line(surface, (218, 165, 32), (8, 8), (24, 24), 3)
            pygame.draw.line(surface, (218, 165, 32), (24, 8), (8, 24), 3)
            self._fallback = surface
        return self._fallback

    def unknown_surface(self) -> pygame.Surface:
        """Return a question-mark icon for unrevealed progression rewards."""
        cached = self._icons.get("unknown")
        if cached is not None:
            return cached
        surface = pygame.Surface((32, 32), pygame.SRCALPHA)
        surface.fill((28, 24, 34, 235))
        pygame.draw.rect(surface, (218, 165, 32), surface.get_rect(), 2)
        color = (244, 191, 42)
        pygame.draw.arc(surface, color, pygame.Rect(9, 6, 14, 13), 0, 3.4, 3)
        pygame.draw.line(surface, color, (16, 17), (16, 22), 3)
        pygame.draw.circle(surface, color, (16, 26), 2)
        self._icons["unknown"] = surface
        return surface


_ABILITY_ICON_MANAGER: AbilityIconManager | None = None


def get_ability_icon_manager() -> AbilityIconManager:
    """Return the process-wide ability icon manager."""
    global _ABILITY_ICON_MANAGER
    if _ABILITY_ICON_MANAGER is None:
        _ABILITY_ICON_MANAGER = AbilityIconManager()
    return _ABILITY_ICON_MANAGER
