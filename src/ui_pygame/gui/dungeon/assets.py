from __future__ import annotations

import json
import os
import re
from collections import OrderedDict
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

import pygame

from src.paths import MAP_FILES_DIR, PROJECT_ROOT, PYGAME_ASSETS_DIR

from .geometry import Quad
from .projector import ProjectedSurface, project_texture_to_quad

TEXTURE_MANIFEST_NAME = "dungeon_texture_manifest.json"

DEFAULT_TEXTURE_PATHS = {
    "wall": "walls/brick.png",
    "wall_funhouse": "walls/funhouse.png",
    "wall_funhouse_boundary": "walls/funhouse_boundary.png",
    "door_closed": "walls/closed_door.png",
    "door_open": "walls/opened_door.png",
    "floor": "floors/dirt.png",
    "floor_fire": "floors/firepath.png",
    "floor_spring": "floors/underground_spring.png",
    "floor_funhouse": "floors/funhouse.png",
    "floor_pit": "floors/dirt_pit.png",
    "ceiling": "ceilings/stone.png",
    "ceiling_funhouse": "ceilings/funhouse.png",
    "ceiling_pit": "ceilings/stone_pit.png",
    "ceiling_void": "__generated__/ceiling_void.png",
}

TEXTURE_PATHS = dict(DEFAULT_TEXTURE_PATHS)

DEFAULT_SPECIAL_TEXTURE_PATHS = {
    "stairs_up": "special_tiles/stairs_up.png",
    "stairs_down": "special_tiles/stairs_down.png",
    "ladder_up": "special_tiles/ladder_up.png",
    "ladder_down": "special_tiles/ladder_down.png",
    "chest_locked": "special_tiles/closed_locked_chest.png",
    "chest_closed": "special_tiles/closed_unlocked_chest.png",
    "chest_open": "special_tiles/opened_chest.png",
    "portal": "special_tiles/portal.png",
    "teleporter": "special_tiles/teleporter.png",
    "warp_point_active": "special_tiles/warp_point_active.png",
    "warp_point_inactive": "special_tiles/warp_point_inactive.png",
    "boulder": "special_tiles/boulder.png",
    "boulder_sword": "special_tiles/boulder_sword.png",
    "dead_body": "special_tiles/dead_body.png",
    "dead_soldier_item": str(
        PYGAME_ASSETS_DIR / "item_art" / "special" / "quest" / "dead_soldier.png"
    ),
    "burial_site": "special_tiles/burial_site.png",
    "blood_floor_overlay": "special_tiles/blood_floor_overlay.png",
    "blood_wall_overlay": "special_tiles/blood_wall_overlay.png",
    "blood_ceiling_overlay": "special_tiles/blood_ceiling_overlay.png",
    "empty_altar": "special_tiles/empty_altar.png",
    "luna_altar": "special_tiles/luna_altar.png",
    "polaris_altar": "special_tiles/polaris_altar.png",
    "triangulus_altar": "special_tiles/triangulus_altar.png",
    "quadrata_altar": "special_tiles/quadrata_altar.png",
    "hexagonum_altar": "special_tiles/hexagonum_altar.png",
    "infinitas_altar": "special_tiles/infinitas_altar.png",
    "golden_chalice_altar": "special_tiles/golden_chalice_altar.png",
    "empty_golden_chalice_altar": "special_tiles/empty_golden_chalice_altar.png",
    "secret_shop": "special_tiles/secret_shop.png",
    "unobtainium": "special_tiles/unobtainium.png",
    "rotator": str(MAP_FILES_DIR / "tileset" / "rotator.png"),
}

GATHERING_FLOOR_OVERLAYS = {
    "floor_gathering_acorn": "root_growth_sparse",
    "floor_gathering_vine_seed": "root_growth",
    "floor_gathering_fungus_spore": "fungus_patch_sparse",
    "floor_gathering_hemlock_root": "root_growth_dense",
    "floor_gathering_deathcap_mushroom": "fungus_patch_dense",
}

SPECIAL_TEXTURE_PATHS = dict(DEFAULT_SPECIAL_TEXTURE_PATHS)

FALLBACK_COLORS = {
    "wall": (90, 90, 104),
    "wall_funhouse": (54, 40, 70),
    "wall_funhouse_boundary": (46, 42, 64),
    "door_closed": (90, 60, 30),
    "door_open": (120, 90, 60),
    "floor": (128, 118, 92),
    "floor_fire": (164, 84, 40),
    "floor_spring": (70, 120, 150),
    "floor_funhouse": (148, 148, 148),
    "floor_pit": (92, 76, 60),
    "ceiling": (70, 68, 76),
    "ceiling_funhouse": (44, 36, 58),
    "ceiling_pit": (52, 52, 58),
    "ceiling_void": (4, 5, 7),
}

SPECIAL_FALLBACK_COLORS = {
    "stairs_up": (100, 140, 200),
    "stairs_down": (200, 120, 80),
    "ladder_up": (140, 110, 70),
    "ladder_down": (120, 90, 60),
    "chest_locked": (120, 96, 70),
    "chest_closed": (139, 90, 43),
    "chest_open": (170, 120, 55),
    "portal": (120, 80, 180),
    "teleporter": (110, 150, 210),
    "warp_point_active": (110, 190, 230),
    "warp_point_inactive": (96, 110, 124),
    "boulder": (110, 110, 120),
    "boulder_sword": (120, 120, 130),
    "dead_body": (120, 88, 70),
    "dead_soldier_item": (118, 82, 68),
    "burial_site": (110, 100, 92),
    "blood_floor_overlay": (110, 18, 22),
    "blood_wall_overlay": (100, 16, 20),
    "blood_ceiling_overlay": (90, 14, 18),
    "empty_altar": (120, 120, 140),
    "luna_altar": (160, 160, 180),
    "polaris_altar": (120, 150, 190),
    "triangulus_altar": (160, 120, 190),
    "quadrata_altar": (190, 160, 120),
    "hexagonum_altar": (160, 130, 100),
    "infinitas_altar": (120, 140, 120),
    "golden_chalice_altar": (180, 160, 90),
    "empty_golden_chalice_altar": (140, 130, 95),
    "secret_shop": (120, 80, 60),
    "unobtainium": (110, 180, 190),
    "rotator": (150, 118, 78),
    "rubble": (102, 96, 88),
    "fungus_patch": (88, 116, 82),
    "crystal_cluster": (92, 148, 176),
    "bone_pile": (164, 150, 126),
    "broken_gear": (126, 104, 86),
    "torch_lit": (198, 122, 54),
    "sconce_unlit": (92, 82, 72),
    "sconce_broken": (70, 66, 62),
}

DEFAULT_ASSETS_BASE = PYGAME_ASSETS_DIR
DEFAULT_TILESET_BASE = DEFAULT_ASSETS_BASE / "dungeon_tiles"


@dataclass(frozen=True)
class SurfacePanelPlan:
    """Describe the logical surface tiles that make up one projected panel.

    The plan is renderer-facing instead of map-facing: it describes the
    tile-sized texture segments that are composed before perspective projection
    or, when the renderer chooses geometry-aware slot drawing, the logical slot
    ids that can be mapped to individual projected sub-quads.

    Slot ids use a semantic
    `<family>:<panel-kind>:<side?>:d<depth>:<slot-name>` format.
    Examples:
    - `floor:center:d2:col3`
    - `ceiling:center:d2:col1`
    - `wall:right:d1:near`
    - `wall:back:d2:tile`
    - `floor:corridor_outer:right:d2:tile`

    Reading the designation:
        - `floor`, `ceiling`, or `wall` = surface family
        - `center`, `right`, `back`, or `corridor_outer` = projected panel kind
        - `left` or `right` = side, when applicable
        - `d2` = scene depth
        - trailing segment like `col3`, `near`, `far`, or `tile` = logical slot id

    Current implementation scope:
        - `center_floor` and `center_ceiling` expose `colN` slots
        - `corridor_outer_floor` and `corridor_outer_ceiling` expose a single `tile` slot
        - `back_wall` and `left/right_blocker` expose a single `tile` slot
        - `left_wall`, `right_wall`, and `corridor_outer_wall` expose `near` / `far`
          slots so wall overrides can target a depth segment instead of an entire wall
    """

    slot_ids: tuple[str, ...]
    slot_texture_keys: tuple[str, ...]
    slot_spans: tuple[tuple[float, float], ...] | None = None
    x_phase: float = 0.0
    row_phase: int = 0
    axis: str = "horizontal"


class TextureLibrary:
    """Load dungeon textures and cache projected panels."""

    def __init__(
        self,
        tileset_base: str | os.PathLike[str] | None = None,
        projected_cache_limit: int = 512,
    ):
        if tileset_base:
            self.tileset_base = Path(tileset_base).expanduser().resolve()
        else:
            self.tileset_base = DEFAULT_TILESET_BASE
        self.assets_base = self.tileset_base.parent
        self.texture_paths = dict(DEFAULT_TEXTURE_PATHS)
        self.special_texture_paths = dict(DEFAULT_SPECIAL_TEXTURE_PATHS)
        self._loaded = False
        self._textures: dict[str, pygame.Surface] = {}
        self._projected_cache: OrderedDict[tuple, ProjectedSurface] = OrderedDict()
        self._projected_cache_limit = max(1, int(projected_cache_limit))
        self._projected_cache_hits = 0
        self._projected_cache_misses = 0
        self._panel_texture_cache: dict[tuple, pygame.Surface] = {}
        self._special_base_textures: dict[str, pygame.Surface] = {}
        self._special_scaled_cache: dict[tuple[str, int], pygame.Surface] = {}
        self._enemy_base_textures: dict[str, pygame.Surface | None] = {}
        self._enemy_scaled_cache: dict[tuple[str, int], pygame.Surface] = {}
        self._manual_surface_slot_overrides: dict[str, str] = {}
        self._scene_surface_slot_overrides: dict[str, str] = {}
        self._asset_fallbacks: dict[str, str] = {}
        self._surface_slot_revision = 0
        self._load_manifest()

    def _load_manifest(self) -> None:
        manifest_path = self.tileset_base / TEXTURE_MANIFEST_NAME
        if not manifest_path.exists():
            return

        try:
            data = json.loads(manifest_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            self._record_asset_fallback("manifest", "dungeon_textures", manifest_path)
            return

        textures = data.get("textures", {})
        if isinstance(textures, dict):
            for texture_key, rel_path in textures.items():
                if isinstance(texture_key, str) and isinstance(rel_path, str):
                    self.texture_paths[texture_key] = rel_path

        special_textures = data.get("special_textures", {})
        if isinstance(special_textures, dict):
            for texture_key, rel_path in special_textures.items():
                if isinstance(texture_key, str) and isinstance(rel_path, str):
                    self.special_texture_paths[texture_key] = rel_path

    def get_asset_fallbacks(self) -> dict[str, str]:
        """Return missing or failed asset paths that are using fallback behavior."""
        return dict(self._asset_fallbacks)

    def get_asset_fallback_counts(self) -> dict[str, int]:
        """Return fallback counts grouped by asset category for diagnostics."""
        counts: dict[str, int] = {}
        for fallback_key in self._asset_fallbacks:
            category, _separator, _texture_key = fallback_key.partition(":")
            counts[category] = counts.get(category, 0) + 1
        return counts

    def get_asset_fallback_keys_by_category(self) -> dict[str, list[str]]:
        """Return fallback texture keys grouped by asset category."""
        grouped: dict[str, list[str]] = {}
        for fallback_key in self._asset_fallbacks:
            category, _separator, texture_key = fallback_key.partition(":")
            grouped.setdefault(category, []).append(texture_key)
        return {
            category: sorted(texture_keys) for category, texture_keys in sorted(grouped.items())
        }

    def get_projected_cache_stats(self) -> dict[str, int]:
        """Return projected-surface cache stats for renderer diagnostics."""
        size = len(self._projected_cache)
        return {
            "size": size,
            "limit": self._projected_cache_limit,
            "remaining": max(0, self._projected_cache_limit - size),
            "full": size >= self._projected_cache_limit,
        }

    def consume_projected_cache_activity(self) -> tuple[int, int]:
        """Return and reset projected-surface cache hits and misses."""
        activity = (self._projected_cache_hits, self._projected_cache_misses)
        self._projected_cache_hits = 0
        self._projected_cache_misses = 0
        return activity

    def get_diagnostics(self) -> dict[str, int | bool | dict[str, int]]:
        """Return compact texture-library state for renderer/debug checks."""
        fallback_counts = self.get_asset_fallback_counts()
        return {
            "loaded": self._loaded,
            "fallback_counts": fallback_counts,
            "fallback_keys": self.get_asset_fallback_keys_by_category(),
            "fallback_total": sum(fallback_counts.values()),
            "projected_cache": self.get_projected_cache_stats(),
            "surface_slot_overrides": self.get_surface_slot_override_diagnostics(),
            "surface_slot_revision": self._surface_slot_revision,
        }

    def _record_asset_fallback(
        self, category: str, texture_key: str, path: str | os.PathLike[str]
    ) -> None:
        self._asset_fallbacks[f"{category}:{texture_key}"] = str(path)

    def ensure_loaded(self) -> None:
        if self._loaded:
            return

        for texture_key, rel_path in self.texture_paths.items():
            if texture_key == "ceiling_void":
                void = pygame.Surface((128, 128), pygame.SRCALPHA)
                void.fill((*FALLBACK_COLORS["ceiling_void"], 255))
                self._textures[texture_key] = self._prepare_texture(texture_key, void)
                continue

            full_path = self.tileset_base / rel_path
            if os.path.exists(full_path):
                self._textures[texture_key] = self._prepare_texture(
                    texture_key,
                    self._load_image_surface(full_path),
                )
            else:
                self._record_asset_fallback("texture", texture_key, full_path)
                fallback = pygame.Surface((128, 128), pygame.SRCALPHA)
                fallback.fill((*FALLBACK_COLORS.get(texture_key, FALLBACK_COLORS["wall"]), 255))
                self._textures[texture_key] = self._prepare_texture(texture_key, fallback)

        self._build_gathering_floor_textures()
        self._loaded = True

    def _build_gathering_floor_textures(self) -> None:
        """Composite transparent gathering art over the normal dungeon floor.

        The dedicated floor images are intentionally not used here: they are
        dark, opaque texture variants and obscure the tile beneath a node.
        Compositing the supplied transparent overlays keeps a node legible
        while letting perspective projection anchor it to the floor.
        """
        base_floor = self._textures.get("floor")
        if base_floor is None:
            return
        for texture_key, overlay_key in GATHERING_FLOOR_OVERLAYS.items():
            rel_path = self.special_texture_paths.get(overlay_key)
            if rel_path is None:
                self._textures[texture_key] = base_floor
                continue
            full_path = self._resolve_asset_path(rel_path)
            if not os.path.exists(full_path):
                self._record_asset_fallback("special", overlay_key, full_path)
                self._textures[texture_key] = base_floor
                continue
            overlay = self._load_image_surface(full_path)
            overlay = pygame.transform.smoothscale(overlay, base_floor.get_size())
            composite = base_floor.copy()
            composite.blit(overlay, (0, 0))
            self._textures[texture_key] = composite

    @staticmethod
    def _load_image_surface(path: str | os.PathLike[str]) -> pygame.Surface:
        surface = pygame.image.load(str(path))
        if pygame.display.get_surface() is not None:
            return surface.convert_alpha()
        return surface.copy()

    @classmethod
    def _prepare_texture(cls, texture_key: str, surface: pygame.Surface) -> pygame.Surface:
        if texture_key == "floor_funhouse":
            return cls._brighten_funhouse_floor_texture(surface)
        return surface

    @staticmethod
    def _brighten_funhouse_floor_texture(surface: pygame.Surface) -> pygame.Surface:
        brightened = surface.copy()
        brightened.fill((72, 58, 88, 0), special_flags=pygame.BLEND_RGB_ADD)
        return brightened

    def get_texture(self, texture_key: str) -> pygame.Surface:
        self.ensure_loaded()
        return self._textures[texture_key]

    def get_special_texture(
        self, texture_key: str, size: int | None = None
    ) -> pygame.Surface | None:
        self.ensure_loaded()
        if texture_key not in self.special_texture_paths:
            return None

        base = self._special_base_textures.get(texture_key)
        if base is None:
            rel_path = self.special_texture_paths[texture_key]
            full_path = self._resolve_asset_path(rel_path)
            if os.path.exists(full_path):
                try:
                    base = self._load_image_surface(full_path)
                except pygame.error:
                    self._record_asset_fallback("special", texture_key, full_path)
                    base = None
            else:
                self._record_asset_fallback("special", texture_key, full_path)
            if base is None:
                fallback = pygame.Surface((128, 128), pygame.SRCALPHA)
                fallback.fill(
                    (
                        *SPECIAL_FALLBACK_COLORS.get(
                            texture_key, SPECIAL_FALLBACK_COLORS["empty_altar"]
                        ),
                        255,
                    )
                )
                base = fallback
            self._special_base_textures[texture_key] = base

        if size is None:
            return base

        cache_key = (texture_key, size)
        scaled = self._special_scaled_cache.get(cache_key)
        if scaled is None:
            trimmed = self._trim_transparent_surface(base)
            scaled = self._scale_surface_to_fit(trimmed, size)
            self._special_scaled_cache[cache_key] = scaled
        return scaled

    @staticmethod
    def _trim_transparent_surface(surface: pygame.Surface) -> pygame.Surface:
        bounds = surface.get_bounding_rect(min_alpha=1)
        if bounds.width <= 0 or bounds.height <= 0:
            return surface
        if bounds.size == surface.get_size():
            return surface
        return surface.subsurface(bounds).copy()

    @staticmethod
    def _scale_surface_to_fit(surface: pygame.Surface, size: int) -> pygame.Surface:
        width, height = surface.get_size()
        if width <= 0 or height <= 0:
            return surface

        longest_edge = max(width, height)
        if longest_edge <= 0:
            return surface

        scale = size / float(longest_edge)
        target_size = (
            max(1, round(width * scale)),
            max(1, round(height * scale)),
        )
        if target_size == surface.get_size():
            return surface
        return pygame.transform.smoothscale(surface, target_size)

    def get_enemy_texture(self, enemy_name: str, size: int | None = None) -> pygame.Surface | None:
        self.ensure_loaded()
        cache_name = enemy_name.strip()
        if not cache_name:
            return None

        base = self._enemy_base_textures.get(cache_name)
        if cache_name not in self._enemy_base_textures:
            try:
                from src.ui_pygame.assets.enemy_combat_sprite_manager import (
                    get_enemy_combat_sprite_manager,
                )

                sprite_manager = get_enemy_combat_sprite_manager()
                sprite_key = sprite_manager.get_sprite_key_for_enemy(cache_name)
                if sprite_key == "generic_enemy" and cache_name != "Generic Enemy":
                    self._record_asset_fallback(
                        "enemy", cache_name, "enemy_combat_sprites/generic_enemy.png"
                    )
                base = sprite_manager.get_sprite_by_key(sprite_key).copy()
            except (pygame.error, OSError, ValueError) as exc:
                self._record_asset_fallback("enemy", cache_name, f"enemy_combat_sprites: {exc}")
                base = None
            self._enemy_base_textures[cache_name] = base

        if base is None:
            return None

        if size is None:
            return base

        cache_key = (cache_name, size)
        scaled = self._enemy_scaled_cache.get(cache_key)
        if scaled is None:
            scaled = self._scale_surface_to_fit(base, size)
            self._enemy_scaled_cache[cache_key] = scaled
        return scaled

    def _resolve_asset_path(self, rel_path: str) -> Path:
        path = Path(rel_path)
        if path.is_absolute():
            return path
        if rel_path.startswith("src/"):
            return PROJECT_ROOT / path
        if rel_path.startswith("map_files/"):
            return MAP_FILES_DIR / Path(*path.parts[1:])
        if rel_path.startswith("sprites/"):
            return self.assets_base / path
        return self.tileset_base / path

    def describe_surface_slot_ids(
        self, panel_id: str, texture_key: str | None = None
    ) -> tuple[str, ...]:
        plan = self._get_surface_panel_plan(panel_id, texture_key=texture_key)
        return () if plan is None else plan.slot_ids

    def describe_surface_slot_spans(
        self,
        panel_id: str,
        texture_key: str | None = None,
    ) -> tuple[tuple[float, float], ...]:
        plan = self._get_surface_panel_plan(panel_id, texture_key=texture_key)
        return () if plan is None else self._get_plan_slot_spans(plan)

    def describe_floor_slot_ids(self, panel_id: str) -> tuple[str, ...]:
        return self.describe_surface_slot_ids(panel_id, texture_key="floor")

    def describe_ceiling_slot_ids(self, panel_id: str) -> tuple[str, ...]:
        return self.describe_surface_slot_ids(panel_id, texture_key="ceiling")

    def describe_wall_slot_ids(self, panel_id: str) -> tuple[str, ...]:
        return self.describe_surface_slot_ids(panel_id, texture_key="wall")

    def has_surface_slot_override(self, panel_id: str, texture_key: str | None = None) -> bool:
        plan = self._get_surface_panel_plan(panel_id, texture_key=texture_key)
        return False if plan is None else self._panel_has_surface_slot_overrides(plan)

    def has_floor_slot_override(self, panel_id: str) -> bool:
        return self.has_surface_slot_override(panel_id, texture_key="floor")

    def has_ceiling_slot_override(self, panel_id: str) -> bool:
        return self.has_surface_slot_override(panel_id, texture_key="ceiling")

    def has_wall_slot_override(self, panel_id: str) -> bool:
        return self.has_surface_slot_override(panel_id, texture_key="wall")

    def get_surface_slot_overrides(self) -> dict[str, str]:
        overrides = dict(self._scene_surface_slot_overrides)
        overrides.update(self._manual_surface_slot_overrides)
        return overrides

    def get_surface_slot_override_diagnostics(self) -> dict[str, int | bool]:
        """Return compact manual/scene surface-slot override state."""
        return {
            "manual_count": len(self._manual_surface_slot_overrides),
            "scene_count": len(self._scene_surface_slot_overrides),
            "total_count": len(self.get_surface_slot_overrides()),
            "has_overrides": self.has_any_surface_slot_overrides(),
            "revision": self._surface_slot_revision,
        }

    def describe_panel_surface_slot_overrides(
        self,
        panel_id: str,
        texture_key: str | None = None,
    ) -> dict[str, str]:
        """Return active slot overrides that affect one projected panel."""
        plan = self._get_surface_panel_plan(panel_id, texture_key=texture_key)
        if plan is None:
            return {}
        overrides = self.get_surface_slot_overrides()
        return {slot_id: overrides[slot_id] for slot_id in plan.slot_ids if slot_id in overrides}

    def describe_panel_surface_slot_state(
        self,
        panel_id: str,
        texture_key: str | None = None,
    ) -> tuple[dict[str, str | bool], ...]:
        """Return default/effective texture keys and override sources for one panel."""
        plan = self._get_surface_panel_plan(panel_id, texture_key=texture_key)
        if plan is None:
            return ()

        def get_override_source(slot_id: str) -> str:
            if slot_id in self._manual_surface_slot_overrides:
                return "manual"
            if slot_id in self._scene_surface_slot_overrides:
                return "scene"
            return "none"

        return tuple(
            {
                "slot_id": slot_id,
                "default_texture_key": default_texture_key,
                "texture_key": self._manual_surface_slot_overrides.get(
                    slot_id,
                    self._scene_surface_slot_overrides.get(slot_id, default_texture_key),
                ),
                "overridden": get_override_source(slot_id) != "none",
                "override_source": get_override_source(slot_id),
            }
            for slot_id, default_texture_key in zip(plan.slot_ids, plan.slot_texture_keys)
        )

    def summarize_panel_surface_slot_state(
        self,
        panel_id: str,
        texture_key: str | None = None,
    ) -> dict[str, object]:
        """Return compact source counts for one panel's surface slots."""
        state = self.describe_panel_surface_slot_state(panel_id, texture_key=texture_key)
        source_counts = {"none": 0, "scene": 0, "manual": 0}
        for slot in state:
            source = str(slot.get("override_source", "none"))
            source_counts[source] = source_counts.get(source, 0) + 1

        return {
            "panel_id": panel_id,
            "texture_key": texture_key,
            "slot_count": len(state),
            "overridden_count": sum(1 for slot in state if slot.get("overridden")),
            "default_count": source_counts.get("none", 0),
            "scene_override_count": source_counts.get("scene", 0),
            "manual_override_count": source_counts.get("manual", 0),
            "has_overrides": any(slot.get("overridden") for slot in state),
        }

    def has_any_surface_slot_overrides(self) -> bool:
        """Return whether manual or scene-driven surface slot overrides are active."""
        return bool(self._manual_surface_slot_overrides or self._scene_surface_slot_overrides)

    def get_floor_slot_overrides(self) -> dict[str, str]:
        return self.get_surface_slot_overrides()

    def set_surface_slot_override(self, slot_id: str, texture_key: str) -> None:
        if not self._is_valid_surface_slot_override(slot_id, texture_key):
            return
        self._manual_surface_slot_overrides[slot_id] = texture_key
        self._bump_surface_slot_revision()

    def set_floor_slot_override(self, slot_id: str, texture_key: str) -> None:
        self.set_surface_slot_override(slot_id, texture_key)

    def set_ceiling_slot_override(self, slot_id: str, texture_key: str) -> None:
        self.set_surface_slot_override(slot_id, texture_key)

    def set_wall_slot_override(self, slot_id: str, texture_key: str) -> None:
        self.set_surface_slot_override(slot_id, texture_key)

    def set_surface_slot_overrides(self, overrides: dict[str, str]) -> None:
        filtered = self._filter_surface_slot_overrides(overrides)
        if filtered == self._manual_surface_slot_overrides:
            return
        self._manual_surface_slot_overrides = filtered
        self._bump_surface_slot_revision()

    def set_scene_surface_slot_overrides(self, overrides: dict[str, str]) -> None:
        filtered = self._filter_surface_slot_overrides(overrides)
        if filtered == self._scene_surface_slot_overrides:
            return
        self._scene_surface_slot_overrides = filtered
        self._bump_surface_slot_revision()

    def set_floor_slot_overrides(self, overrides: dict[str, str]) -> None:
        self.set_surface_slot_overrides(overrides)

    def clear_surface_slot_override(self, slot_id: str) -> None:
        if slot_id in self._manual_surface_slot_overrides:
            del self._manual_surface_slot_overrides[slot_id]
            self._bump_surface_slot_revision()

    def clear_floor_slot_override(self, slot_id: str) -> None:
        self.clear_surface_slot_override(slot_id)

    def clear_surface_slot_overrides(self) -> None:
        if self._manual_surface_slot_overrides:
            self._manual_surface_slot_overrides.clear()
            self._bump_surface_slot_revision()

    def clear_scene_surface_slot_overrides(self) -> None:
        if self._scene_surface_slot_overrides:
            self._scene_surface_slot_overrides.clear()
            self._bump_surface_slot_revision()

    def clear_floor_slot_overrides(self) -> None:
        self.clear_surface_slot_overrides()

    def _bump_surface_slot_revision(self) -> None:
        self._surface_slot_revision += 1
        self._panel_texture_cache.clear()

    def _is_valid_surface_slot_override(self, slot_id: object, texture_key: object) -> bool:
        return (
            isinstance(slot_id, str)
            and slot_id.startswith(("floor:", "ceiling:", "wall:"))
            and isinstance(texture_key, str)
            and texture_key in self.texture_paths
        )

    def _filter_surface_slot_overrides(self, overrides: dict[str, str]) -> dict[str, str]:
        return {
            slot_id: texture_key
            for slot_id, texture_key in overrides.items()
            if self._is_valid_surface_slot_override(slot_id, texture_key)
        }

    def _get_surface_panel_override_signature(self, panel_id: str, texture_key: str):
        plan = self._get_surface_panel_plan(panel_id, texture_key)
        if plan is None or not self._panel_has_surface_slot_overrides(plan):
            return None
        overrides = self.get_surface_slot_overrides()
        return tuple(
            (slot_id, overrides.get(slot_id, default_texture_key))
            for slot_id, default_texture_key in zip(plan.slot_ids, plan.slot_texture_keys)
        )

    def get_panel_texture(self, panel_id: str, texture_key: str) -> pygame.Surface:
        texture = self.get_texture(texture_key)
        surface_plan = self._get_surface_panel_plan(panel_id, texture_key)
        if surface_plan is not None and self._panel_has_surface_slot_overrides(surface_plan):
            cache_key = (
                panel_id,
                texture_key,
                self._get_surface_panel_override_signature(panel_id, texture_key),
            )
            cached = self._panel_texture_cache.get(cache_key)
            if cached is not None:
                return cached
            built = self._build_surface_panel_texture(surface_plan)
            self._panel_texture_cache[cache_key] = built
            return built

        if panel_id.endswith("center_floor") or panel_id.endswith("center_ceiling"):
            depth_match = re.match(r"d(\d+):", panel_id)
            depth = int(depth_match.group(1)) if depth_match else 1
            if texture_key == "ceiling_pit":
                columns = len(self._get_center_ceiling_slot_ids(depth))
                return self._build_center_special_band_texture(
                    base_texture=self.get_texture("ceiling"),
                    special_texture=texture,
                    columns=columns,
                )
            if texture_key == "floor_pit":
                columns = len(self._get_center_floor_slot_ids(depth))
                return self._build_center_special_band_texture(
                    base_texture=self.get_texture("floor"),
                    special_texture=texture,
                    columns=columns,
                )
            columns = (
                len(self._get_center_floor_slot_ids(depth))
                if panel_id.endswith("center_floor")
                else len(self._get_center_ceiling_slot_ids(depth))
            )
            return self._build_tiled_band_texture(
                texture,
                columns=columns,
                x_phase=0.0,
                row_phase=(depth - 1) % 2,
            )
        if panel_id.endswith("corridor_outer_floor") or panel_id.endswith("corridor_outer_ceiling"):
            return texture
        return texture

    def _get_surface_panel_plan(
        self, panel_id: str, texture_key: str | None = None
    ) -> SurfacePanelPlan | None:
        depth = self._get_panel_depth(panel_id)
        texture_key = texture_key or self._get_default_texture_key(panel_id)
        if texture_key is None:
            return None

        if panel_id.endswith("center_floor"):
            slot_ids = self._get_center_floor_slot_ids(depth)
            base_texture_key = "floor" if texture_key == "floor_pit" else texture_key
            slot_texture_keys = [base_texture_key] * len(slot_ids)
            if texture_key == "floor_pit":
                slot_texture_keys[len(slot_ids) // 2] = "floor_pit"
            return SurfacePanelPlan(
                slot_ids=slot_ids,
                slot_texture_keys=tuple(slot_texture_keys),
                slot_spans=self._get_center_depth_slot_spans(depth),
                x_phase=0.0,
                row_phase=(depth - 1) % 2,
            )

        if panel_id.endswith("center_ceiling"):
            slot_ids = self._get_center_ceiling_slot_ids(depth)
            base_texture_key = "ceiling" if texture_key == "ceiling_pit" else texture_key
            slot_texture_keys = [base_texture_key] * len(slot_ids)
            if texture_key == "ceiling_pit":
                slot_texture_keys[len(slot_ids) // 2] = "ceiling_pit"
            return SurfacePanelPlan(
                slot_ids=slot_ids,
                slot_texture_keys=tuple(slot_texture_keys),
                slot_spans=self._get_center_depth_slot_spans(depth),
                x_phase=0.0,
                row_phase=(depth - 1) % 2,
            )

        if panel_id.endswith("corridor_outer_floor"):
            side = "left" if ":left_" in panel_id else "right"
            return SurfacePanelPlan(
                slot_ids=(f"floor:corridor_outer:{side}:d{depth}:tile",),
                slot_texture_keys=(texture_key,),
            )

        if panel_id.endswith("corridor_outer_ceiling"):
            side = "left" if ":left_" in panel_id else "right"
            return SurfacePanelPlan(
                slot_ids=(f"ceiling:corridor_outer:{side}:d{depth}:tile",),
                slot_texture_keys=(texture_key,),
            )

        if panel_id.endswith(":back_wall"):
            return SurfacePanelPlan(
                slot_ids=(f"wall:visible:d{depth}:center",),
                slot_texture_keys=(texture_key,),
            )

        if panel_id.endswith(":left_blocker") or panel_id.endswith(":right_blocker"):
            side = "left" if ":left_" in panel_id else "right"
            return SurfacePanelPlan(
                slot_ids=(f"wall:visible:d{depth}:{side}_blocker",),
                slot_texture_keys=(texture_key,),
            )

        if (
            panel_id.endswith(":left_wall")
            or panel_id.endswith(":right_wall")
            or panel_id.endswith("corridor_outer_wall")
        ):
            side = "left" if ":left_" in panel_id else "right"
            panel_kind = "corridor_outer" if panel_id.endswith("corridor_outer_wall") else side
            return SurfacePanelPlan(
                slot_ids=(
                    f"wall:visible:d{depth}:{panel_kind}:{side}:near",
                    f"wall:visible:d{depth}:{panel_kind}:{side}:far",
                ),
                slot_texture_keys=(texture_key, texture_key),
            )

        return None

    @staticmethod
    def _get_default_texture_key(panel_id: str) -> str | None:
        if "floor" in panel_id:
            return "floor"
        if "ceiling" in panel_id:
            return "ceiling"
        if "wall" in panel_id:
            return "wall"
        return None

    @staticmethod
    def _get_panel_depth(panel_id: str) -> int:
        depth_match = re.match(r"d(\d+):", panel_id)
        return int(depth_match.group(1)) if depth_match else 1

    @staticmethod
    @lru_cache(maxsize=None)
    def _get_center_floor_slot_ids(depth: int) -> tuple[str, ...]:
        if depth <= 1:
            radius = 1
        elif depth == 2:
            radius = 2
        else:
            radius = 4

        slot_ids: list[str] = []
        for offset in range(-radius, radius + 1):
            if offset < 0:
                suffix = f"xm{abs(offset)}"
            elif offset > 0:
                suffix = f"xp{offset}"
            else:
                suffix = "x0"
            slot_ids.append(f"floor:visible:d{depth}:{suffix}")
        return tuple(slot_ids)

    @staticmethod
    @lru_cache(maxsize=None)
    def _get_center_ceiling_slot_ids(depth: int) -> tuple[str, ...]:
        if depth <= 1:
            radius = 1
        elif depth == 2:
            radius = 2
        else:
            radius = 4

        slot_ids: list[str] = []
        for offset in range(-radius, radius + 1):
            if offset < 0:
                suffix = f"xm{abs(offset)}"
            elif offset > 0:
                suffix = f"xp{offset}"
            else:
                suffix = "x0"
            slot_ids.append(f"ceiling:visible:d{depth}:{suffix}")
        return tuple(slot_ids)

    @staticmethod
    @lru_cache(maxsize=None)
    def _get_center_depth_slot_spans(depth: int) -> tuple[tuple[float, float], ...]:
        if depth == 3:
            boundaries = (
                -1.0 / 7.0,
                0.0,
                1.0 / 7.0,
                2.0 / 7.0,
                3.0 / 7.0,
                4.0 / 7.0,
                5.0 / 7.0,
                6.0 / 7.0,
                1.0,
                8.0 / 7.0,
            )
        elif depth == 2:
            boundaries = (0.0, 0.2, 0.4, 0.6, 0.8, 1.0)
        else:
            boundaries = (0.0, 1.0 / 3.0, 2.0 / 3.0, 1.0)
        return tuple(
            (boundaries[index], boundaries[index + 1]) for index in range(len(boundaries) - 1)
        )

    @staticmethod
    def _get_plan_slot_spans(plan: SurfacePanelPlan) -> tuple[tuple[float, float], ...]:
        if plan.slot_spans is not None:
            return plan.slot_spans
        slot_count = len(plan.slot_ids)
        if slot_count == 0:
            return ()
        return tuple((index / slot_count, (index + 1) / slot_count) for index in range(slot_count))

    def _panel_has_surface_slot_overrides(self, plan: SurfacePanelPlan) -> bool:
        overrides = self.get_surface_slot_overrides()
        return any(slot_id in overrides for slot_id in plan.slot_ids)

    def _build_surface_panel_texture(self, plan: SurfacePanelPlan) -> pygame.Surface:
        overrides = self.get_surface_slot_overrides()
        slot_textures = [
            self.get_texture(overrides.get(slot_id, texture_key))
            for slot_id, texture_key in zip(plan.slot_ids, plan.slot_texture_keys)
        ]

        if len(slot_textures) == 1:
            return slot_textures[0]

        tile_w, tile_h = slot_textures[0].get_size()
        slot_count = len(slot_textures)
        slot_spans = self._get_plan_slot_spans(plan)
        if plan.axis == "vertical":
            band = pygame.Surface((tile_w, tile_h), pygame.SRCALPHA)
            for texture, (start_ratio, end_ratio) in zip(slot_textures, slot_spans):
                top = round(start_ratio * tile_h)
                bottom = round(end_ratio * tile_h)
                segment_height = max(1, bottom - top)
                segment = pygame.transform.smoothscale(texture, (tile_w, segment_height))
                band.blit(segment, (0, top))
            return band

        band = pygame.Surface((tile_w * slot_count, tile_h), pygame.SRCALPHA)
        if plan.slot_spans is not None:
            for texture, (start_ratio, end_ratio) in zip(slot_textures, slot_spans):
                left = round(start_ratio * band.get_width())
                right = round(end_ratio * band.get_width())
                segment_width = max(1, right - left)
                segment = pygame.transform.smoothscale(texture, (segment_width, tile_h))
                band.blit(segment, (left, 0))
            return band

        offset = round((plan.x_phase + (plan.row_phase % 2)) * (tile_w / 2))
        if offset == 0:
            for index, texture in enumerate(slot_textures):
                band.blit(texture, (index * tile_w, 0))
            return band

        extended = pygame.Surface((tile_w * (slot_count + 2), tile_h), pygame.SRCALPHA)
        for index in range(slot_count + 2):
            slot_index = (index - 1) % slot_count
            extended.blit(slot_textures[slot_index], (index * tile_w, 0))

        band.blit(extended, (-tile_w + offset, 0))
        return band

    @staticmethod
    def _is_floor_overlay_tile(tile) -> bool:
        tile_type = type(tile).__name__ if tile else ""
        return any(
            name in tile_type
            for name in (
                "Chest",
                "Relic",
                "Boulder",
                "GoldenChaliceRoom",
                "SecretShop",
                "BossRoom",
                "Boss",
                "Lair",
            )
        )

    def _texture_or_default(self, texture_key: str, default_key: str) -> str:
        return texture_key if texture_key in self.texture_paths else default_key

    def get_floor_key(self, tile, fallback_tile=None) -> str:
        if self._is_floor_overlay_tile(tile) and fallback_tile is not None:
            return self.get_floor_key(fallback_tile)

        gathering_resource = getattr(tile, "gathering_resource", None)
        if (
            gathering_resource
            and getattr(tile, "gathering_available", False)
            and not getattr(tile, "gathering_harvested", False)
        ):
            gathering_floor_keys = {
                "acorn": "floor_gathering_acorn",
                "vine_seed": "floor_gathering_vine_seed",
                "fungus_spore": "floor_gathering_fungus_spore",
                "hemlock_root": "floor_gathering_hemlock_root",
                "deathcap_mushroom": "floor_gathering_deathcap_mushroom",
            }
            floor_key = gathering_floor_keys.get(gathering_resource)
            if floor_key is not None:
                return floor_key

        tile_type = type(tile).__name__ if tile else ""
        if "Funhouse" in tile_type:
            return "floor_funhouse"
        if "FirePath" in tile_type:
            return "floor_fire"
        if "UndergroundSpring" in tile_type:
            return "floor_spring"
        if "LadderDown" in tile_type:
            return "floor_pit"
        if "RootGrowthTile" in tile_type:
            return self._texture_or_default("floor_roots", "floor")
        if "FungusPatchTile" in tile_type:
            return self._texture_or_default("floor_fungus", "floor")
        if "CrystalClusterTile" in tile_type:
            return self._texture_or_default("floor_crystal", "floor")
        if any(name in tile_type for name in ("RubbleTile", "BonePileTile", "BrokenGearTile")):
            return self._texture_or_default("floor_debris", "floor")
        return "floor"

    def get_wall_key(self, tile) -> str:
        tile_type = type(tile).__name__ if tile else ""
        if tile_type == "FunhouseBoundaryWall":
            return self._texture_or_default("wall_funhouse_boundary", "wall_funhouse")
        if tile_type in ("FunhouseWall", "MirrorWall"):
            return self._texture_or_default("wall_funhouse", "wall")
        return "wall"

    def get_ceiling_key(self, tile) -> str:
        tile_type = type(tile).__name__ if tile else ""
        if "Funhouse" in tile_type:
            return self._texture_or_default("ceiling_funhouse", "ceiling")
        if "LadderUp" in tile_type:
            return "ceiling_pit"
        if "FungusPatchTile" in tile_type:
            return self._texture_or_default("ceiling_fungus", "ceiling")
        if "CrystalClusterTile" in tile_type:
            return self._texture_or_default("ceiling_crystal", "ceiling")
        return "ceiling"

    def get_projected_surface(
        self,
        panel_id: str,
        texture_key: str,
        quad: Quad,
        darkness: float,
        view_size: tuple[int, int],
    ) -> ProjectedSurface:
        self.ensure_loaded()

        quad_key = tuple((round(x, 3), round(y, 3)) for x, y in quad.points)
        cache_key = (
            view_size,
            panel_id,
            texture_key,
            self._get_surface_panel_override_signature(panel_id, texture_key),
            round(darkness, 3),
            quad_key,
        )
        projected = self._projected_cache.get(cache_key)
        if projected is not None:
            self._projected_cache_hits += 1
            self._projected_cache.move_to_end(cache_key)
            return projected

        self._projected_cache_misses += 1

        projected = project_texture_to_quad(
            self.get_panel_texture(panel_id, texture_key),
            quad,
            darkness=0.0,
            output_size=view_size,
        )
        surface = self._shade_projected_surface(projected.surface, panel_id, darkness)
        projected = ProjectedSurface(surface=surface, topleft=projected.topleft)
        self._projected_cache[cache_key] = projected
        self._trim_projected_cache()
        return projected

    def _trim_projected_cache(self) -> None:
        while len(self._projected_cache) > self._projected_cache_limit:
            self._projected_cache.popitem(last=False)

    def _shade_projected_surface(
        self, surface: pygame.Surface, panel_id: str, base_darkness: float
    ) -> pygame.Surface:
        depth_match = re.match(r"d(\d+):", panel_id)
        layer = int(depth_match.group(1)) if depth_match else 1
        target_darkness = min(1.0, base_darkness + 0.4) if layer < 3 else base_darkness

        if (
            panel_id.endswith("center_floor")
            or ":center_floor_slot" in panel_id
            or panel_id.endswith("corridor_outer_floor")
        ):
            return self._apply_vertical_gradient(
                surface, base_darkness, target_darkness, near_at_top=False
            )
        if (
            panel_id.endswith("center_ceiling")
            or ":center_ceiling_slot" in panel_id
            or panel_id.endswith("corridor_outer_ceiling")
        ):
            shaded = self._apply_vertical_gradient(
                surface, base_darkness, target_darkness, near_at_top=True
            )
            return self._apply_uniform_darkness(shaded, 0.30)
        if panel_id.endswith("left_wall") or ":left_wall_slot" in panel_id:
            shaded = self._apply_horizontal_gradient(
                surface, base_darkness, target_darkness, near_at_left=True
            )
            return self._apply_uniform_darkness(shaded, 0.20)
        if panel_id.endswith("right_wall") or ":right_wall_slot" in panel_id:
            shaded = self._apply_horizontal_gradient(
                surface, base_darkness, target_darkness, near_at_left=False
            )
            return self._apply_uniform_darkness(shaded, 0.20)
        if panel_id.endswith("corridor_outer_wall") or "corridor_outer_wall_slot" in panel_id:
            side = "left" if ":left_" in panel_id else "right"
            shaded = self._apply_horizontal_gradient(
                surface,
                base_darkness,
                target_darkness,
                near_at_left=(side == "left"),
            )
            return self._apply_uniform_darkness(shaded, 0.20)

        return self._apply_uniform_darkness(surface, base_darkness)

    @staticmethod
    def _apply_uniform_darkness(surface: pygame.Surface, darkness: float) -> pygame.Surface:
        darkness = max(0.0, min(1.0, darkness))
        if darkness <= 0.0:
            return surface
        shaded = surface.copy()
        factor = int(255 * (1.0 - darkness))
        shaded.fill((factor, factor, factor, 255), special_flags=pygame.BLEND_RGBA_MULT)
        return shaded

    @classmethod
    def _apply_vertical_gradient(
        cls,
        surface: pygame.Surface,
        base_darkness: float,
        target_darkness: float,
        near_at_top: bool,
    ) -> pygame.Surface:
        width, height = surface.get_size()
        if width <= 0 or height <= 0:
            return surface
        shaded = surface.copy()
        gradient = pygame.Surface((width, height), pygame.SRCALPHA)

        for y in range(height):
            position = y / max(1, height - 1)
            ratio = position if near_at_top else (1.0 - position)
            darkness = min(1.0, base_darkness + (ratio * (target_darkness - base_darkness)))
            factor = int(255 * max(0.0, 1.0 - darkness))
            pygame.draw.line(gradient, (factor, factor, factor, 255), (0, y), (width, y))

        shaded.blit(gradient, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)
        return shaded

    @classmethod
    def _apply_horizontal_gradient(
        cls,
        surface: pygame.Surface,
        base_darkness: float,
        target_darkness: float,
        near_at_left: bool,
    ) -> pygame.Surface:
        width, height = surface.get_size()
        if width <= 0 or height <= 0:
            return surface
        shaded = surface.copy()
        gradient = pygame.Surface((width, height), pygame.SRCALPHA)

        for x in range(width):
            position = x / max(1, width - 1)
            ratio = position if near_at_left else (1.0 - position)
            darkness = min(1.0, base_darkness + (ratio * (target_darkness - base_darkness)))
            factor = int(255 * max(0.0, 1.0 - darkness))
            pygame.draw.line(gradient, (factor, factor, factor, 255), (x, 0), (x, height))

        shaded.blit(gradient, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)
        return shaded

    @staticmethod
    def _build_tiled_band_texture(
        texture: pygame.Surface,
        columns: int,
        x_phase: float = 0.0,
        row_phase: int = 0,
    ) -> pygame.Surface:
        tile_w, tile_h = texture.get_size()
        band = pygame.Surface((tile_w * columns, tile_h), pygame.SRCALPHA)

        # Phase the horizontal band so the front-most visible strip can show
        # partial side tiles around a full center tile without changing quad geometry.
        offset = round((x_phase + (row_phase % 2)) * (tile_w / 2))
        for index in range(columns + 2):
            band.blit(texture, (index * tile_w - offset, 0))
        return band

    @staticmethod
    def _build_center_special_band_texture(
        base_texture: pygame.Surface,
        special_texture: pygame.Surface,
        columns: int,
    ) -> pygame.Surface:
        tile_w, tile_h = base_texture.get_size()
        band = pygame.Surface((tile_w * columns, tile_h), pygame.SRCALPHA)

        for index in range(columns):
            band.blit(base_texture, (index * tile_w, 0))

        center_index = columns // 2
        band.blit(special_texture, (center_index * tile_w, 0))
        return band
