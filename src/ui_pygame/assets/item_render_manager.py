"""Large item artwork loading for selected-item presentation panels."""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
import pygame

from src.paths import PYGAME_ASSETS_DIR
from src.ui_pygame.assets.icon_manager import IconManager
from src.ui_pygame.assets.scaled_surface_cache import ScaledSurfaceCache

logger = logging.getLogger(__name__)

ITEM_RENDER_ROOT = PYGAME_ASSETS_DIR
ITEM_ART_ROOT = PYGAME_ASSETS_DIR / "item_art"
ICON_MAP_PATH = PYGAME_ASSETS_DIR / "item_icons" / "item_icon_map.json"
_SHARED_ITEM_RENDER_MANAGER: ItemRenderManager | None = None


@dataclass(frozen=True)
class ItemRenderFrame:
    """Optional legacy atlas frame metadata for one large item render."""

    key: str
    rect: pygame.Rect


class ItemRenderManager:
    """Resolve item objects or names to large painterly item artwork."""

    ICON_TO_RENDER = {
        "sword": "longsword",
        "longsword": "greatsword",
        "hammer": "warhammer",
        "tome": "spellbook",
        "spellbook": "spellbook",
        "wand": "focus",
    }

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
        render_root: Path | None = None,
        *,
        atlas_json: Path | None = None,
        atlas_image: Path | None = None,
        render_map_path: Path | None = None,
        item_art_root: Path | None = None,
        icon_map_path: Path | None = None,
        enhance_artwork: bool = True,
    ) -> None:
        self.render_root = Path(render_root or ITEM_RENDER_ROOT)
        self.item_art_root = Path(item_art_root or ITEM_ART_ROOT)
        self.atlas_json_path = Path(atlas_json or self.render_root / "item_render_atlas.json")
        self.atlas_image_path = Path(atlas_image or self.render_root / "item_render_atlas.png")
        self.render_map_path = Path(render_map_path or self.render_root / "item_render_map.json")
        self.icon_map_path = Path(icon_map_path or ICON_MAP_PATH)
        self.enhance_artwork = enhance_artwork
        self.frames: dict[str, ItemRenderFrame] = {}
        self.render_map: dict[str, str] = {}
        self.icon_map: dict[str, str] = {}
        self.missing_mappings: set[str] = set()
        self._atlas_surface: pygame.Surface | None = None
        self._render_cache: dict[str, pygame.Surface] = {}
        self._scaled_cache = ScaledSurfaceCache[tuple[str, tuple[int, int]]](24 * 1024**2)
        self._fallback_surface: pygame.Surface | None = None
        self._icon_manager = IconManager()
        self.load_manifest()
        self.load_maps()

    @staticmethod
    def item_name(item: Any) -> str:
        if isinstance(item, str):
            return item
        return str(getattr(item, "name", item) or "")

    @classmethod
    def render_key_from_icon_key(cls, icon_key: str) -> str:
        return cls.ICON_TO_RENDER.get(str(icon_key or ""), str(icon_key or "generic_item"))

    def load_manifest(self) -> None:
        if not self.atlas_json_path.exists():
            logger.debug("Optional item render atlas JSON missing: %s", self.atlas_json_path)
            return
        try:
            data = json.loads(self.atlas_json_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            logger.warning(
                "Could not load item render atlas JSON %s: %s", self.atlas_json_path, exc
            )
            return

        for key, entry in data.items():
            try:
                rect = pygame.Rect(
                    int(entry["x"]), int(entry["y"]), int(entry["w"]), int(entry["h"])
                )
            except (KeyError, TypeError, ValueError) as exc:
                logger.warning("Skipping invalid item render frame %s: %s", key, exc)
                continue
            self.frames[str(key)] = ItemRenderFrame(key=str(key), rect=rect)

    def load_maps(self) -> None:
        self.render_map = self._load_string_map(self.render_map_path, "item render map")
        self.icon_map = self._load_string_map(self.icon_map_path, "item icon map")

    @staticmethod
    def _load_string_map(path: Path, label: str) -> dict[str, str]:
        if not path.exists():
            logger.warning("%s missing: %s", label.capitalize(), path)
            return {}
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            logger.warning("Could not load %s %s: %s", label, path, exc)
            return {}
        return {str(name): str(key) for name, key in data.items()}

    def atlas_surface(self) -> pygame.Surface | None:
        if self._atlas_surface is not None:
            return self._atlas_surface
        if not self.atlas_image_path.exists():
            logger.debug("Optional item render atlas image missing: %s", self.atlas_image_path)
            return None
        try:
            surface = pygame.image.load(str(self.atlas_image_path))
        except (pygame.error, OSError) as exc:
            logger.warning("Could not load item render atlas %s: %s", self.atlas_image_path, exc)
            return None
        try:
            surface = surface.convert_alpha()
        except pygame.error:
            surface = surface.copy()
        self._atlas_surface = surface
        return surface

    def get_render(self, item: Any) -> pygame.Surface:
        return self.get_render_by_key(self.get_render_key_for_item(item))

    def get_render_by_name(self, item_name: str) -> pygame.Surface:
        return self.get_render_by_key(self.get_render_key_for_item(item_name))

    def get_render_by_key(self, render_key: str) -> pygame.Surface:
        key = str(render_key or "generic_item")
        cached = self._render_cache.get(key)
        if cached is not None:
            return cached

        individual = self._load_individual_art(key)
        if individual is not None:
            self._render_cache[key] = individual
            return individual

        frame = self.frames.get(key) or self.frames.get("generic_item")
        if frame is None:
            logger.debug("Item render frame missing for %s and generic_item", key)
            return self.fallback_surface()

        atlas = self.atlas_surface()
        if atlas is None:
            return self.fallback_surface()

        try:
            render = atlas.subsurface(frame.rect).copy()
        except ValueError as exc:
            logger.warning("Item render frame out of bounds for %s: %s", key, exc)
            return self.fallback_surface()
        render = self.trim_transparent_padding(render)
        if self.enhance_artwork:
            render = self.enhance_display_contrast(render)
        self._render_cache[key] = render
        return render

    def _load_individual_art(self, key: str) -> pygame.Surface | None:
        path = self.art_path_for_key(key)
        if not path.exists():
            return None
        try:
            surface = pygame.image.load(str(path))
        except (pygame.error, OSError) as exc:
            logger.warning("Could not load item art %s: %s", path, exc)
            return None
        try:
            surface = surface.convert_alpha()
        except pygame.error:
            surface = surface.copy()
        surface = self.trim_transparent_padding(surface)
        if self.enhance_artwork:
            surface = self.enhance_display_contrast(surface)
        return surface

    @staticmethod
    def trim_transparent_padding(
        surface: pygame.Surface, *, alpha_threshold: int = 8, padding: int = 6
    ) -> pygame.Surface:
        mask = pygame.mask.from_surface(surface, alpha_threshold)
        rects = mask.get_bounding_rects()
        if not rects:
            return surface
        bounds = rects[0].copy()
        for rect in rects[1:]:
            bounds.union_ip(rect)
        bounds.inflate_ip(padding * 2, padding * 2)
        bounds = bounds.clip(surface.get_rect())
        if bounds.size == surface.get_size():
            return surface
        return surface.subsurface(bounds).copy()

    @staticmethod
    def enhance_display_contrast(surface: pygame.Surface) -> pygame.Surface:
        """Lift cached render contrast while preserving transparent pixels."""
        enhanced = surface.copy()
        rgb = pygame.surfarray.pixels3d(enhanced)
        alpha = pygame.surfarray.pixels_alpha(enhanced)
        visible = alpha > 8
        if np.any(visible):
            adjusted = ((rgb.astype(np.float32) - 18.0) * 1.45) + 24.0
            rgb[visible] = np.clip(adjusted[visible], 0, 255).astype(np.uint8)
        del rgb
        del alpha
        return enhanced

    def get_scaled_render_by_key(
        self, render_key: str, target_size: tuple[int, int]
    ) -> pygame.Surface:
        key = str(render_key or "generic_item")
        target = (max(1, int(target_size[0])), max(1, int(target_size[1])))
        cache_key = (key, target)
        cached = self._scaled_cache.get(cache_key)
        if cached is not None:
            return cached

        render = self.get_render_by_key(key)
        source_w, source_h = render.get_size()
        scale = min(target[0] / source_w, target[1] / source_h)
        fitted_size = (max(1, int(source_w * scale)), max(1, int(source_h * scale)))
        fitted = pygame.transform.smoothscale(render, fitted_size)
        surface = pygame.Surface(target, pygame.SRCALPHA)
        surface.blit(fitted, ((target[0] - fitted_size[0]) // 2, (target[1] - fitted_size[1]) // 2))
        self._scaled_cache[cache_key] = surface
        return surface

    def get_scaled_render(self, item: Any, target_size: tuple[int, int]) -> pygame.Surface:
        return self.get_scaled_render_by_key(self.get_render_key_for_item(item), target_size)

    def get_render_key_for_item(self, item: Any, *, slot: str | None = None) -> str:
        name = self.item_name(item)
        if name in self.render_map:
            return self._valid_key(self.render_map[name])
        if name in self.icon_map:
            return self._valid_key(self.render_key_from_icon_key(self.icon_map[name]))

        if name:
            logger.debug("Item render mapping missing for %s", name)
            self.missing_mappings.add(name)

        inferred_icon = self._icon_manager.infer_icon_key(item)
        if inferred_icon:
            return self._valid_key(self.render_key_from_icon_key(inferred_icon))

        typ = str(getattr(item, "typ", "") or "")
        if typ in self.CATEGORY_FALLBACKS:
            return self._valid_key(self.CATEGORY_FALLBACKS[typ])
        if slot in self.SLOT_FALLBACKS:
            return self._valid_key(self.SLOT_FALLBACKS[slot])
        return "generic_item"

    def _valid_key(self, key: str) -> str:
        if key in self.frames or self.art_path_for_key(key).exists():
            return key
        return "generic_item"

    def art_path_for_key(self, key: str) -> Path:
        """Return the PNG path for an item-art render key."""
        return self.item_art_root / f"{key}.png"

    def fallback_surface(self) -> pygame.Surface:
        if self._fallback_surface is not None:
            return self._fallback_surface
        surface = pygame.Surface((160, 280), pygame.SRCALPHA)
        surface.fill((14, 12, 12, 255))
        pygame.draw.rect(surface, (108, 86, 54), surface.get_rect(), 2)
        pygame.draw.rect(surface, (42, 34, 28), pygame.Rect(36, 72, 88, 136), border_radius=8)
        pygame.draw.line(surface, (190, 151, 74), (60, 140), (100, 140), 5)
        pygame.draw.line(surface, (190, 151, 74), (80, 120), (80, 160), 5)
        self._fallback_surface = surface
        return surface

    def scaled_cache_stats(self) -> dict[str, int]:
        """Report scaled artwork cache usage and activity."""
        return self._scaled_cache.stats()

    def clear_cache(self) -> None:
        self._atlas_surface = None
        self._render_cache.clear()
        self._scaled_cache.clear()
        self._fallback_surface = None


def get_item_render_manager() -> ItemRenderManager:
    """Return the shared runtime item render manager."""
    global _SHARED_ITEM_RENDER_MANAGER
    if _SHARED_ITEM_RENDER_MANAGER is None:
        _SHARED_ITEM_RENDER_MANAGER = ItemRenderManager()
    return _SHARED_ITEM_RENDER_MANAGER
