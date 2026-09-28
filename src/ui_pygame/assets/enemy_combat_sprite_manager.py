"""Transparent enemy combat sprite loading for battlefield presentation."""

from __future__ import annotations

import json
import logging
import re
from pathlib import Path
from typing import Any

import pygame

from src.paths import PYGAME_ASSETS_DIR

logger = logging.getLogger(__name__)

ENEMY_COMBAT_SPRITE_ROOT = PYGAME_ASSETS_DIR / "enemy_combat_sprites"
POLYMORPH_SPRITE_SCALE = 0.42
_SHARED_ENEMY_COMBAT_SPRITE_MANAGER: EnemyCombatSpriteManager | None = None


class EnemyCombatSpriteManager:
    """Resolve enemies to transparent full-body combat sprites."""

    CATEGORY_FALLBACKS = {
        "Animal": "wolf",
        "Slime": "slime",
        "Humanoid": "bandit",
        "Fey": "wraith",
        "Fiend": "demon",
        "Undead": "zombie",
        "Elemental": "earth_elemental",
        "Dragon": "dragon",
        "Monster": "boss",
        "Aberration": "boss",
        "Construct": "dark_knight",
        "Misc": "generic_enemy",
    }

    BOSS_NAMES = {
        "Barghest",
        "Beholder",
        "Behemoth",
        "Cerberus",
        "Chimera",
        "Circe",
        "Cockatrice",
        "Domingo",
        "Fuath",
        "Golem",
        "Incubus",
        "Jester",
        "Merzhin",
        "Minotaur",
        "Nightmare",
        "Red Dragon",
        "The Devil",
        "Wendigo",
    }

    NAME_HINTS = (
        ("goblin", "goblin"),
        ("kobold", "kobold"),
        ("skeleton warrior", "skeleton_warrior"),
        ("skeleton", "skeleton"),
        ("zombie", "zombie"),
        ("lich", "lich"),
        ("wraith", "wraith"),
        ("ghost", "ghost"),
        ("dire wolf", "dire_wolf"),
        ("direwolf", "dire_wolf"),
        ("wolf", "wolf"),
        ("bear", "bear"),
        ("boar", "boar"),
        ("rat", "giant_rat"),
        ("giant spider", "giant_spider"),
        ("spider", "spider"),
        ("scorpion", "scorpion"),
        ("slime", "slime"),
        ("ooze", "ooze"),
        ("bat", "bat"),
        ("harpy", "harpy"),
        ("gargoyle", "gargoyle"),
        ("fire", "fire_elemental"),
        ("water", "water_elemental"),
        ("earth", "earth_elemental"),
        ("wind", "air_elemental"),
        ("storm", "air_elemental"),
        ("shadow", "shadow_elemental"),
        ("demon", "demon"),
        ("devil", "devil"),
        ("dragon", "dragon"),
        ("wyrm", "wyrm"),
        ("wyvern", "wyvern"),
        ("orc", "orc"),
        ("bandit", "bandit"),
        ("cultist", "cultist"),
        ("disciple", "disciple"),
        ("dark knight", "dark_knight"),
    )

    def __init__(
        self,
        *,
        sprite_root: Path | None = None,
        sprite_map_path: Path | None = None,
        scale_map_path: Path | None = None,
        dungeon_scale_map_path: Path | None = None,
    ) -> None:
        self.sprite_root = Path(sprite_root or ENEMY_COMBAT_SPRITE_ROOT)
        self.sprite_map_path = Path(
            sprite_map_path or self.sprite_root / "enemy_combat_sprite_map.json"
        )
        self.scale_map_path = Path(
            scale_map_path or self.sprite_root / "enemy_combat_sprite_scale.json"
        )
        self.dungeon_scale_map_path = Path(
            dungeon_scale_map_path or self.sprite_root / "enemy_dungeon_sprite_scale.json"
        )
        self.available_keys: set[str] = {
            path.stem
            for path in self.sprite_root.glob("*.png")
            if path.is_file() and not path.stem.endswith("_review_sheet")
        }
        self.sprite_map: dict[str, str] = {}
        self.combat_scale_map: dict[str, float] = {}
        self.dungeon_scale_map: dict[str, float] = {}
        self._sprite_cache: dict[str, pygame.Surface] = {}
        self._scaled_cache: dict[tuple[str, tuple[int, int]], pygame.Surface] = {}
        self._fallback_surface: pygame.Surface | None = None
        self.load_map()
        self.load_scale_map()
        self.load_dungeon_scale_map()

    def load_map(self) -> None:
        if not self.sprite_map_path.exists():
            return
        try:
            data = json.loads(self.sprite_map_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            logger.warning(
                "Could not load enemy combat sprite map %s: %s", self.sprite_map_path, exc
            )
            return
        self.sprite_map = {str(name): str(key) for name, key in data.items()}

    def load_scale_map(self) -> None:
        if not self.scale_map_path.exists():
            return
        try:
            data = json.loads(self.scale_map_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            logger.warning(
                "Could not load enemy combat sprite scale map %s: %s", self.scale_map_path, exc
            )
            return
        if not isinstance(data, dict):
            logger.warning(
                "Enemy combat sprite scale map must be an object: %s", self.scale_map_path
            )
            return

        scales: dict[str, float] = {}
        for name, value in data.items():
            try:
                scale = float(value)
            except (TypeError, ValueError):
                logger.warning("Ignoring invalid enemy combat sprite scale for %s: %r", name, value)
                continue
            scales[str(name)] = self._valid_combat_scale(scale)
        self.combat_scale_map = scales

    def load_dungeon_scale_map(self) -> None:
        self.dungeon_scale_map = self._load_scale_map_file(
            self.dungeon_scale_map_path,
            "enemy dungeon sprite scale map",
        )

    def _load_scale_map_file(self, path: Path, label: str) -> dict[str, float]:
        if not path.exists():
            return {}
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            logger.warning("Could not load %s %s: %s", label, path, exc)
            return {}
        if not isinstance(data, dict):
            logger.warning("%s must be an object: %s", label, path)
            return {}

        scales: dict[str, float] = {}
        for name, value in data.items():
            try:
                scale = float(value)
            except (TypeError, ValueError):
                logger.warning("Ignoring invalid %s for %s: %r", label, name, value)
                continue
            scales[str(name)] = self._valid_combat_scale(scale)
        return scales

    def get_combat_scale_for_enemy(self, enemy: Any) -> float:
        """Return an optional per-enemy combat sprite scale multiplier."""
        return self._scale_for_enemy(enemy, self.combat_scale_map)

    def get_dungeon_scale_for_enemy(self, enemy: Any) -> float:
        """Return an optional per-enemy dungeon/navigation sprite scale multiplier."""
        return self._scale_for_enemy(enemy, self.dungeon_scale_map)

    def _scale_for_enemy(self, enemy: Any, scale_map: dict[str, float]) -> float:
        polymorph = getattr(enemy, "status_effects", {}).get("Polymorph")
        if polymorph is not None and getattr(polymorph, "active", False):
            return POLYMORPH_SPRITE_SCALE
        name = self.enemy_name(enemy)
        if name in scale_map:
            return scale_map[name]

        sprite_key = self.get_sprite_key_for_enemy(enemy)
        if sprite_key in scale_map:
            return scale_map[sprite_key]

        if self._is_boss(enemy) and "boss" in scale_map:
            return scale_map["boss"]
        return 1.0

    def get_sprite(self, enemy: Any) -> pygame.Surface:
        return self.get_sprite_by_key(self.get_sprite_key_for_enemy(enemy))

    def get_sprite_by_name(self, enemy_name: str) -> pygame.Surface:
        return self.get_sprite_by_key(self.get_sprite_key_for_enemy(enemy_name))

    def get_sprite_by_key(self, sprite_key: str) -> pygame.Surface:
        key = self._valid_key(sprite_key)
        cached = self._sprite_cache.get(key)
        if cached is not None:
            return cached

        path = self.sprite_root / f"{key}.png"
        if not path.exists():
            logger.warning("Enemy combat sprite missing for %s: %s", key, path)
            return self.fallback_surface()

        try:
            surface = pygame.image.load(str(path))
        except (pygame.error, OSError) as exc:
            logger.warning("Could not load enemy combat sprite %s: %s", path, exc)
            return self.fallback_surface()

        try:
            surface = surface.convert_alpha()
        except pygame.error:
            surface = surface.copy()

        self._sprite_cache[key] = surface
        return surface

    def get_scaled_sprite(self, enemy: Any, target_size: tuple[int, int]) -> pygame.Surface:
        return self.get_scaled_sprite_by_key(self.get_sprite_key_for_enemy(enemy), target_size)

    def get_scaled_sprite_by_name(
        self, enemy_name: str, target_size: tuple[int, int]
    ) -> pygame.Surface:
        return self.get_scaled_sprite_by_key(self.get_sprite_key_for_enemy(enemy_name), target_size)

    def get_scaled_sprite_by_key(
        self, sprite_key: str, target_size: tuple[int, int]
    ) -> pygame.Surface:
        key = self._valid_key(sprite_key)
        target = (max(1, int(target_size[0])), max(1, int(target_size[1])))
        cache_key = (key, target)
        cached = self._scaled_cache.get(cache_key)
        if cached is not None:
            return cached

        sprite = self.get_sprite_by_key(key)
        source_w, source_h = sprite.get_size()
        scale = min(target[0] / source_w, target[1] / source_h)
        fitted_size = (max(1, int(source_w * scale)), max(1, int(source_h * scale)))
        fitted = pygame.transform.smoothscale(sprite, fitted_size)
        surface = pygame.Surface(target, pygame.SRCALPHA)
        surface.blit(fitted, ((target[0] - fitted_size[0]) // 2, (target[1] - fitted_size[1]) // 2))
        self._scaled_cache[cache_key] = surface
        return surface

    def get_sprite_key_for_enemy(self, enemy: Any) -> str:
        polymorph = getattr(enemy, "status_effects", {}).get("Polymorph")
        if (
            polymorph is not None
            and getattr(polymorph, "active", False)
            and "polymorph_bunny" in self.available_keys
        ):
            return "polymorph_bunny"
        name = self.enemy_name(enemy)
        picture_key = self._picture_key(enemy)
        if picture_key and picture_key in self.available_keys:
            return picture_key

        enemy_class = self._attribute_key(enemy, "enemy_class")
        if enemy_class:
            if enemy_class in self.sprite_map:
                return self._valid_key(self.sprite_map[enemy_class])
            class_key = self.normalize_key(re.sub(r"(?<!^)(?=[A-Z])", " ", enemy_class))
            if class_key in self.available_keys:
                return class_key

        if name in self.sprite_map:
            return self._valid_key(self.sprite_map[name], prefer_boss=self._is_boss(enemy))

        if self.sprite_map:
            normalized_name = self.normalize_key(name)
            if normalized_name in self.available_keys:
                return normalized_name

            class_name = enemy.__name__ if isinstance(enemy, type) else type(enemy).__name__
            class_key = self.normalize_key(class_name)
            if class_key in self.available_keys:
                return class_key

            archetype = self._attribute_key(
                enemy, "combat_sprite_archetype", "render_archetype", "archetype"
            )
            if archetype:
                return self._valid_key(archetype, prefer_boss=self._is_boss(enemy))

            hinted = self._hint_key(name) or self._hint_key(class_name)
            if hinted:
                return self._valid_key(hinted, prefer_boss=self._is_boss(enemy))

            category = self._attribute_key(enemy, "enemy_typ", "category", "typ")
            if category in self.CATEGORY_FALLBACKS:
                return self._valid_key(
                    self.CATEGORY_FALLBACKS[category], prefer_boss=self._is_boss(enemy)
                )

            if self._is_boss(enemy):
                return self._valid_key("boss")
            return self._valid_key("generic_enemy")

        return self._valid_key("boss" if self._is_boss(enemy) else "generic_enemy")

    def _valid_key(self, key: str, *, prefer_boss: bool = False) -> str:
        if key in self.available_keys:
            return key
        if prefer_boss and "boss" in self.available_keys:
            return "boss"
        if "generic_enemy" in self.available_keys:
            return "generic_enemy"
        return str(key or "generic_enemy")

    @staticmethod
    def _valid_combat_scale(scale: float) -> float:
        return max(0.25, min(2.5, scale))

    @staticmethod
    def enemy_name(enemy: Any) -> str:
        if isinstance(enemy, str):
            return enemy
        return str(getattr(enemy, "name", enemy) or "")

    @staticmethod
    def normalize_key(value: Any) -> str:
        text = str(value or "").strip().lower()
        return "_".join("".join(ch if ch.isalnum() else " " for ch in text).split())

    def _hint_key(self, value: str) -> str | None:
        normalized = value.replace("_", " ").lower()
        for needle, key in self.NAME_HINTS:
            if needle in normalized:
                return key
        return None

    @staticmethod
    def _attribute_key(enemy: Any, *names: str) -> str:
        if isinstance(enemy, str):
            return ""
        for name in names:
            value = getattr(enemy, name, "")
            if value:
                return str(value)
        return ""

    @classmethod
    def _picture_key(cls, enemy: Any) -> str:
        if isinstance(enemy, str):
            return ""
        picture = getattr(enemy, "picture", "")
        if not isinstance(picture, str) or not picture.lower().endswith(".png"):
            return ""
        return cls.normalize_key(Path(picture).stem)

    def _is_boss(self, enemy: Any) -> bool:
        name = self.enemy_name(enemy)
        if bool(getattr(enemy, "boss", False) or getattr(enemy, "is_boss", False)):
            return True
        return name in self.BOSS_NAMES

    def fallback_surface(self) -> pygame.Surface:
        if self._fallback_surface is not None:
            return self._fallback_surface
        surface = pygame.Surface((384, 384), pygame.SRCALPHA)
        pygame.draw.ellipse(surface, (34, 31, 36, 235), pygame.Rect(128, 84, 128, 216))
        pygame.draw.polygon(
            surface, (74, 63, 50, 245), [(152, 138), (232, 138), (250, 270), (134, 270)]
        )
        pygame.draw.circle(surface, (210, 172, 88, 255), (168, 154), 7)
        pygame.draw.circle(surface, (210, 172, 88, 255), (216, 154), 7)
        self._fallback_surface = surface
        return surface

    def clear_cache(self) -> None:
        self._sprite_cache.clear()
        self._scaled_cache.clear()
        self._fallback_surface = None


def get_enemy_combat_sprite_manager() -> EnemyCombatSpriteManager:
    """Return the shared runtime enemy combat sprite manager."""
    global _SHARED_ENEMY_COMBAT_SPRITE_MANAGER
    if _SHARED_ENEMY_COMBAT_SPRITE_MANAGER is None:
        _SHARED_ENEMY_COMBAT_SPRITE_MANAGER = EnemyCombatSpriteManager()
    return _SHARED_ENEMY_COMBAT_SPRITE_MANAGER
