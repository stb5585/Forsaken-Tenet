"""Shared item icon atlas loading for the Pygame UI."""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pygame

from src.paths import PYGAME_ASSETS_DIR

logger = logging.getLogger(__name__)

ICON_ROOT = PYGAME_ASSETS_DIR / "item_icons"


@dataclass(frozen=True)
class IconFrame:
    """Atlas frame metadata for one reusable icon archetype."""

    atlas: str
    key: str
    rect: pygame.Rect


class IconManager:
    """Load reusable icon atlases and resolve item objects to archetype icons."""

    ITEM_TYPES = {"Weapon", "Armor", "Helmet", "OffHand", "Accessory", "Potion", "Misc"}
    NON_ITEM_TYPES = {"Skill", "Spell", "Ability"}

    ATLAS_FILES = (
        ("equipment_icons", "equipment_icons.png", "equipment_icons.json"),
        ("consumable_icons", "consumable_icons.png", "consumable_icons.json"),
        ("utility_icons", "utility_icons.png", "utility_icons.json"),
    )

    CATEGORY_FALLBACKS = {
        "Weapon": "weapon",
        "Armor": "armor",
        "Helmet": "helmet",
        "OffHand": "offhand",
        "Accessory": "accessory",
        "Potion": "consumable",
        "Misc": "generic_item",
    }

    SLOT_FALLBACKS = {
        "Weapon": "weapon",
        "Armor": "armor",
        "Helmet": "helmet",
        "OffHand": "offhand",
        "Ring": "ring",
        "Pendant": "pendant",
    }

    def __init__(
        self,
        icon_root: Path | None = None,
        *,
        mapping_path: Path | None = None,
    ) -> None:
        self.icon_root = Path(icon_root or ICON_ROOT)
        self.mapping_path = Path(mapping_path or self.icon_root / "item_icon_map.json")
        self.frames: dict[str, IconFrame] = {}
        self.atlas_paths: dict[str, Path] = {}
        self.item_map: dict[str, str] = {}
        self._atlas_cache: dict[str, pygame.Surface] = {}
        self._icon_cache: dict[str, pygame.Surface] = {}
        self._fallback_surface: pygame.Surface | None = None
        self.load_manifests()
        self.load_item_map()

    @staticmethod
    def item_name(item: Any) -> str:
        if isinstance(item, str):
            return item
        return str(getattr(item, "name", item) or "")

    def load_manifests(self) -> None:
        for atlas_key, image_name, manifest_name in self.ATLAS_FILES:
            image_path = self.icon_root / image_name
            manifest_path = self.icon_root / manifest_name
            if not manifest_path.exists():
                logger.warning("Icon manifest missing: %s", manifest_path)
                continue
            try:
                data = json.loads(manifest_path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError) as exc:
                logger.warning("Could not load icon manifest %s: %s", manifest_path, exc)
                continue

            self.atlas_paths[atlas_key] = image_path
            for key, entry in data.items():
                try:
                    rect = pygame.Rect(
                        int(entry["x"]), int(entry["y"]), int(entry["w"]), int(entry["h"])
                    )
                except (KeyError, TypeError, ValueError) as exc:
                    logger.warning(
                        "Skipping invalid icon frame %s in %s: %s", key, manifest_path, exc
                    )
                    continue
                self.frames[str(key)] = IconFrame(atlas=atlas_key, key=str(key), rect=rect)

    def load_item_map(self) -> None:
        if not self.mapping_path.exists():
            logger.warning("Item icon map missing: %s", self.mapping_path)
            return
        try:
            data = json.loads(self.mapping_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            logger.warning("Could not load item icon map %s: %s", self.mapping_path, exc)
            return
        self.item_map = {str(name): str(archetype) for name, archetype in data.items()}

    def atlas_surface(self, atlas_key: str) -> pygame.Surface | None:
        cached = self._atlas_cache.get(atlas_key)
        if cached is not None:
            return cached
        path = self.atlas_paths.get(atlas_key)
        if path is None or not path.exists():
            logger.warning("Icon atlas image missing: %s", path)
            return None
        try:
            surface = pygame.image.load(str(path))
        except (pygame.error, OSError) as exc:
            logger.warning("Could not load icon atlas %s: %s", path, exc)
            return None
        try:
            surface = surface.convert_alpha()
        except pygame.error:
            surface = surface.copy()
        self._atlas_cache[atlas_key] = surface
        return surface

    def get_icon_by_key(self, archetype: str) -> pygame.Surface:
        key = str(archetype or "generic_item")
        cached = self._icon_cache.get(key)
        if cached is not None:
            return cached

        frame = self.frames.get(key) or self.frames.get("generic_item")
        if frame is None:
            logger.warning("Icon frame missing for %s and generic_item", key)
            return self.fallback_surface()

        atlas = self.atlas_surface(frame.atlas)
        if atlas is None:
            return self.fallback_surface()

        try:
            icon = atlas.subsurface(frame.rect).copy()
        except ValueError as exc:
            logger.warning("Icon frame out of bounds for %s: %s", key, exc)
            return self.fallback_surface()
        self._icon_cache[key] = icon
        return icon

    def get_icon(self, item: Any, *, slot: str | None = None) -> pygame.Surface:
        return self.get_icon_by_key(self.icon_key_for_item(item, slot=slot))

    def icon_key_for_item(self, item: Any, *, slot: str | None = None) -> str:
        name = self.item_name(item)
        if name in self.item_map:
            return self.item_map[name]

        typ = str(getattr(item, "typ", "") or "")
        if typ in self.NON_ITEM_TYPES:
            return "generic_item"

        subtyp = str(getattr(item, "subtyp", "") or "")
        if typ == "Misc" and subtyp == "Scroll" and name.startswith("Stolen "):
            return "scroll"

        if name:
            logger.warning("Item icon mapping missing for %s", name)
        inferred = self.infer_icon_key(item)
        if inferred:
            return inferred

        if typ in self.CATEGORY_FALLBACKS:
            return self.CATEGORY_FALLBACKS[typ]
        if slot in self.SLOT_FALLBACKS:
            return self.SLOT_FALLBACKS[slot]
        return "generic_item"

    def infer_icon_key(self, item: Any) -> str | None:
        typ = str(getattr(item, "typ", "") or "")
        subtyp = str(getattr(item, "subtyp", "") or "")
        if typ == "Weapon":
            name = self.item_name(item)
            if (
                name
                in {
                    "Brass Knuckles",
                    "Cestus",
                    "Battle Gauntlet",
                    "Bagh Nahk",
                    "Indra's Fist",
                    "God's Hand",
                }
                or subtyp == "Fist"
            ):
                return "fist_weapon"
            if subtyp in {"Club", "Hammer"}:
                return "hammer"
            if subtyp == "Natural":
                return "claw"
            if subtyp == "Longsword":
                return "longsword"
            if subtyp in {"Sword", "Ninja Blade"}:
                return "sword"
            if subtyp == "Battle Axe":
                return "axe"
            if subtyp == "Polearm":
                return "spear"
            if subtyp == "Dagger":
                return "dagger"
            if subtyp == "Staff":
                return "staff"
            return "weapon"
        if typ == "Armor":
            return {
                "Cloth": "robe",
                "Light": "light_armor",
                "Medium": "medium_armor",
                "Heavy": "heavy_armor",
            }.get(subtyp, "armor")
        if typ == "Helmet":
            return "helmet"
        if typ == "OffHand":
            return {
                "Shield": "shield",
                "Tome": "tome",
                "Rod": "focus",
            }.get(subtyp, "offhand")
        if typ == "Accessory":
            return {"Ring": "ring", "Pendant": "pendant"}.get(subtyp, "accessory")
        if typ == "Potion":
            return {
                "Health": "health_potion",
                "Mana": "mana_potion",
                "Elixir": "health_potion",
                "Status": "antidote",
            }.get(subtyp, "consumable")
        if typ == "Misc":
            if subtyp == "Key":
                return "key"
            if subtyp == "Scroll":
                return "scroll"
            if subtyp == "Quest":
                return "quest_item"
            if subtyp in {"Special", "Ability"}:
                return "gem"
            if "Summon" in subtyp:
                return "quest_item"
            return "crafting_material"
        return None

    def fallback_surface(self) -> pygame.Surface:
        if self._fallback_surface is not None:
            return self._fallback_surface
        surface = pygame.Surface((32, 32), pygame.SRCALPHA)
        surface.fill((24, 24, 28, 255))
        pygame.draw.rect(surface, (200, 200, 200), surface.get_rect(), 1)
        pygame.draw.line(surface, (218, 165, 32), (8, 16), (24, 16), 2)
        pygame.draw.line(surface, (218, 165, 32), (16, 8), (16, 24), 2)
        self._fallback_surface = surface
        return surface

    def clear_cache(self) -> None:
        self._atlas_cache.clear()
        self._icon_cache.clear()
        self._fallback_surface = None
