"""Resolve transparent player dialogue art from character-creation appearance IDs."""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

import pygame

from src.paths import PYGAME_ASSETS_DIR

from .portrait_manager import PortraitManager

logger = logging.getLogger(__name__)

PLAYER_DIALOGUE_ART_ROOT = PYGAME_ASSETS_DIR / "player_dialogue"
PLAYER_DIALOGUE_ART_MAP = PLAYER_DIALOGUE_ART_ROOT / "dialogue_art_map.json"


class PlayerDialogueArtManager:
    """Load full-body player cutouts without falling back to face portraits."""

    def __init__(
        self,
        art_root: Path | None = None,
        *,
        mapping_path: Path | None = None,
    ) -> None:
        self.art_root = Path(art_root or PLAYER_DIALOGUE_ART_ROOT)
        self.mapping_path = Path(mapping_path or self.art_root / "dialogue_art_map.json")
        self.assets, self.facing = self._load_mapping()
        self._surface_cache: dict[str, pygame.Surface | None] = {}

    def _load_mapping(self) -> tuple[dict[str, str], dict[str, str]]:
        """Return validated appearance-to-filename mappings."""
        try:
            data = json.loads(self.mapping_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as error:
            logger.warning(
                "Could not load player dialogue art map %s: %s", self.mapping_path, error
            )
            return {}, {}
        assets = data.get("assets")
        if not isinstance(assets, dict):
            logger.warning("Player dialogue art map has no assets object: %s", self.mapping_path)
            return {}, {}
        validated_assets = {
            appearance_id: filename
            for appearance_id, filename in assets.items()
            if isinstance(appearance_id, str)
            and appearance_id
            and isinstance(filename, str)
            and filename
        }
        facing = data.get("facing")
        validated_facing = (
            {
                appearance_id: direction
                for appearance_id, direction in facing.items()
                if appearance_id in validated_assets and direction in {"left", "right", "front"}
            }
            if isinstance(facing, dict)
            else {}
        )
        return validated_assets, validated_facing

    @staticmethod
    def appearance_id(race: Any, gender: Any, variant: Any = None) -> str:
        """Return the same canonical ID used by the face portrait atlas."""
        return PortraitManager.appearance_id(race, gender, variant)

    def image_path(self, race: Any, gender: Any, variant: Any = None) -> Path | None:
        """Return mapped dialogue art for an appearance, if populated."""
        filename = self.assets.get(self.appearance_id(race, gender, variant))
        if filename is None:
            return None
        path = self.art_root / filename
        return path if path.is_file() else None

    def should_mirror(
        self,
        race: Any,
        gender: Any,
        *,
        variant: Any = None,
        stage_side: str,
    ) -> bool:
        """Return whether the cutout faces outward from its current stage side."""
        direction = self.facing.get(self.appearance_id(race, gender, variant), "front")
        return direction == stage_side and direction in {"left", "right"}

    def get_portrait(
        self,
        race: Any,
        gender: Any,
        *,
        variant: Any = None,
    ) -> pygame.Surface | None:
        """Return a transparent full-body cutout, or None for an unpopulated appearance."""
        appearance_id = self.appearance_id(race, gender, variant)
        if appearance_id in self._surface_cache:
            return self._surface_cache[appearance_id]
        path = self.image_path(race, gender, variant)
        if path is None:
            self._surface_cache[appearance_id] = None
            return None
        try:
            surface = pygame.image.load(str(path))
        except (OSError, pygame.error) as error:
            logger.warning("Could not load player dialogue art %s: %s", path, error)
            self._surface_cache[appearance_id] = None
            return None
        try:
            surface = surface.convert_alpha()
        except pygame.error:
            surface = surface.copy()
        self._surface_cache[appearance_id] = surface
        return surface
