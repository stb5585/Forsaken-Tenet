"""Core behavior for the renderer package."""

from __future__ import annotations

import os

import pygame

from ..assets import TextureLibrary
from ..geometry import (
    Quad,
    build_depth_rect,
    build_next_depth_rect,
    build_zone_geometry,
)
from ..scene import extract_visible_scene, is_wall
from .models import RenderCommand


class RendererCoreMixin:
    def __init__(self, presenter, textures: TextureLibrary, debug_geometry: bool = False):
        self.presenter = presenter
        self.textures = textures
        self.debug_geometry = debug_geometry or os.getenv("DUNGEON_RENDERER_DEBUG_GEOMETRY") == "1"
        self.disable_darkness = os.getenv("DUNGEON_RENDERER_DISABLE_DARKNESS") == "1"
        self.debug_scene = os.getenv("DUNGEON_RENDERER_DEBUG_SCENE") == "1"
        self.debug_commands = os.getenv("DUNGEON_RENDERER_DEBUG_COMMANDS") == "1"
        self.debug_surface_slots = os.getenv("DUNGEON_RENDERER_DEBUG_SURFACE_SLOTS") == "1"
        self.enable_wall_overlays = os.getenv("DUNGEON_RENDERER_ENABLE_WALL_OVERLAYS") == "1"
        self._force_field_seed_counter = 0
        self._jester_force_field_body_cache: dict[tuple[int, int, int], pygame.Surface] = {}
        self._last_debug_snapshot: str | None = None

    @property
    def screen(self) -> pygame.Surface:
        return self.presenter.screen

    def _get_viewport_size(self) -> tuple[int, int]:
        screen_w, screen_h = self.screen.get_size()
        metrics = getattr(self.presenter, "layout_metrics", None)
        view_fraction = metrics.dungeon_view_fraction if metrics is not None else 0.65
        return int(screen_w * view_fraction), screen_h

    def render(self, player_char, world_dict) -> None:
        self.textures.ensure_loaded()
        self.player_char = player_char
        screen = self.screen
        view_w, view_h = self._get_viewport_size()
        screen.fill((0, 0, 0), pygame.Rect(0, 0, view_w, view_h))

        scene = extract_visible_scene(player_char, world_dict, max_depth=3)
        self._configure_surface_slot_overrides(scene)
        zones = {
            depth: build_zone_geometry(
                build_depth_rect(view_w, view_h, depth),
                build_next_depth_rect(build_depth_rect(view_w, view_h, depth)),
                depth=depth,
            )
            for depth in (1, 2, 3)
        }
        self._precache_jester_force_field_bodies(world_dict, zones)

        commands = self._build_render_commands(scene, zones)
        self._emit_debug_snapshot(scene, commands)
        for command in sorted(commands, key=lambda item: (-item.depth, item.order)):
            projected = self.textures.get_projected_surface(
                panel_id=command.panel_id,
                texture_key=command.texture_key,
                quad=command.quad,
                darkness=command.darkness,
                view_size=(view_w, view_h),
            )
            screen.blit(projected.surface, projected.topleft)

        self._render_special_tiles(scene, zones)
        self._render_jester_force_fields(scene, zones)
        if self.enable_wall_overlays:
            self._render_wall_overlays(scene, zones)

        if self.debug_geometry:
            self._render_debug_overlay(zones, scene)

    def _configure_surface_slot_overrides(self, scene) -> None:
        desired_overrides: dict[str, str] = {}
        max_visible_depth = scene.depths[-1].depth if scene.depths else 0
        last_floor_theme_tile = self._find_initial_floor_theme_tile(scene)

        for visible_depth in scene.depths:
            center_floor_key = self._get_center_floor_texture_key(
                depth=visible_depth.depth,
                source_tile=visible_depth.source_tile,
                fallback_tile=last_floor_theme_tile,
            )
            center_ceiling_key = self.textures.get_ceiling_key(visible_depth.source_tile)
            self._collect_visible_floor_slot_overrides(
                visible_depth=visible_depth,
                base_texture_key=center_floor_key,
                overrides=desired_overrides,
            )
            self._collect_center_wall_slot_override(
                depth=visible_depth.depth,
                center_tile=visible_depth.center,
                overrides=desired_overrides,
            )
            side_doors_hidden_by_center_wall = self._should_hide_side_doors_behind_center_wall(
                visible_depth
            )

            self._collect_visible_ceiling_slot_overrides(
                visible_depth=visible_depth,
                base_texture_key=center_ceiling_key,
                overrides=desired_overrides,
            )
            self._collect_stairs_up_ceiling_void_override(
                visible_depth=visible_depth,
                max_visible_depth=max_visible_depth,
                overrides=desired_overrides,
            )
            if not side_doors_hidden_by_center_wall:
                self._collect_side_wall_slot_override(
                    depth=visible_depth.depth,
                    side="left",
                    opening_tile=visible_depth.left,
                    forward_tile=visible_depth.left_forward,
                    overrides=desired_overrides,
                )
                self._collect_side_wall_slot_override(
                    depth=visible_depth.depth,
                    side="right",
                    opening_tile=visible_depth.right,
                    forward_tile=visible_depth.right_forward,
                    overrides=desired_overrides,
                )

            if self._should_advance_floor_theme(visible_depth.depth, visible_depth.source_tile):
                last_floor_theme_tile = visible_depth.source_tile

        self.textures.set_scene_surface_slot_overrides(desired_overrides)

    def _collect_stairs_up_ceiling_void_override(
        self,
        visible_depth,
        max_visible_depth: int,
        overrides: dict[str, str],
    ) -> None:
        if (
            visible_depth.depth == 1
            and visible_depth.source_tile is not None
            and "StairsUp" in type(visible_depth.source_tile).__name__
        ):
            self._set_center_ceiling_void_override(
                visible_depth.depth, max_visible_depth, overrides
            )

        if visible_depth.center is not None and "StairsUp" in type(visible_depth.center).__name__:
            self._set_center_ceiling_void_override(
                visible_depth.depth + 1, max_visible_depth, overrides
            )

    @staticmethod
    def _set_center_ceiling_void_override(
        depth: int,
        max_visible_depth: int,
        overrides: dict[str, str],
    ) -> None:
        if depth < 1 or depth > max_visible_depth:
            return
        overrides[f"ceiling:visible:d{depth}:x0"] = "ceiling_void"

    def _collect_center_wall_slot_override(
        self,
        depth: int,
        center_tile,
        overrides: dict[str, str],
    ) -> None:
        if not self._is_door_tile(center_tile):
            return

        panel_id = f"d{depth}:back_wall"
        slot_ids = self.textures.describe_wall_slot_ids(panel_id)
        if not slot_ids:
            return

        overrides[slot_ids[0]] = (
            "door_open" if getattr(center_tile, "open", False) else "door_closed"
        )

    def _collect_visible_floor_slot_overrides(
        self,
        visible_depth,
        base_texture_key: str,
        overrides: dict[str, str],
    ) -> None:
        panel_id = f"d{visible_depth.depth}:center_floor"
        slot_ids = self.textures.describe_floor_slot_ids(panel_id)
        row_tiles = self._get_visible_floor_row_tiles(visible_depth)

        for slot_id, tile in zip(slot_ids, row_tiles):
            texture_key = self._get_visible_floor_texture_key(
                tile=tile,
                base_texture_key=base_texture_key,
            )
            if texture_key != base_texture_key:
                overrides[slot_id] = texture_key

    def _get_visible_floor_row_tiles(self, visible_depth) -> tuple[object | None, ...]:
        depth = visible_depth.depth
        if depth == 1:
            return (
                visible_depth.left,
                visible_depth.source_tile,
                visible_depth.right,
            )
        if depth == 2:
            return (
                visible_depth.left_branch,
                visible_depth.left,
                visible_depth.source_tile,
                visible_depth.right,
                visible_depth.right_branch,
            )
        return (
            None,
            None,
            visible_depth.left_branch,
            visible_depth.left,
            visible_depth.source_tile,
            visible_depth.right,
            visible_depth.right_branch,
            None,
            None,
        )

    def _get_visible_floor_texture_key(self, tile, base_texture_key: str) -> str:
        if tile is None or is_wall(tile) or self.textures._is_floor_overlay_tile(tile):
            return base_texture_key
        return self.textures.get_floor_key(tile)

    def _collect_visible_ceiling_slot_overrides(
        self,
        visible_depth,
        base_texture_key: str,
        overrides: dict[str, str],
    ) -> None:
        panel_id = f"d{visible_depth.depth}:center_ceiling"
        slot_ids = self.textures.describe_ceiling_slot_ids(panel_id)
        row_tiles = self._get_visible_ceiling_row_tiles(visible_depth)

        for slot_id, tile in zip(slot_ids, row_tiles):
            texture_key = self._get_visible_ceiling_texture_key(
                tile=tile,
                base_texture_key=base_texture_key,
            )
            if texture_key != base_texture_key:
                overrides[slot_id] = texture_key

    def _get_visible_ceiling_row_tiles(self, visible_depth) -> tuple[object | None, ...]:
        depth = visible_depth.depth
        if depth == 1:
            return (
                visible_depth.left,
                visible_depth.source_tile,
                visible_depth.right,
            )
        if depth == 2:
            return (
                visible_depth.left_branch,
                visible_depth.left,
                visible_depth.source_tile,
                visible_depth.right,
                visible_depth.right_branch,
            )
        return (
            None,
            None,
            visible_depth.left_branch,
            visible_depth.left,
            visible_depth.source_tile,
            visible_depth.right,
            visible_depth.right_branch,
            None,
            None,
        )

    def _get_visible_ceiling_texture_key(self, tile, base_texture_key: str) -> str:
        if tile is None or is_wall(tile) or self.textures._is_floor_overlay_tile(tile):
            return base_texture_key
        return self.textures.get_ceiling_key(tile)

    def _collect_side_wall_slot_override(
        self,
        depth: int,
        side: str,
        opening_tile,
        forward_tile,
        overrides: dict[str, str],
    ) -> None:
        if (
            self._opening_tile_blocks_view(opening_tile)
            or forward_tile is None
            or not self._is_door_tile(forward_tile)
        ):
            return

        panel_id = f"d{depth}:{side}_blocker"
        slot_ids = self.textures.describe_wall_slot_ids(panel_id)
        if not slot_ids:
            return

        overrides[slot_ids[0]] = (
            "door_open" if getattr(forward_tile, "open", False) else "door_closed"
        )

    def _build_render_commands(self, scene, zones) -> list[RenderCommand]:
        commands: list[RenderCommand] = []
        last_floor_theme_tile = self._find_initial_floor_theme_tile(scene)

        for visible_depth in scene.depths:
            depth = visible_depth.depth
            zone = zones[depth]
            darkness = self._get_layer_darkness(depth)

            center_floor_key = self._get_center_floor_texture_key(
                depth=depth,
                source_tile=visible_depth.source_tile,
                fallback_tile=last_floor_theme_tile,
            )
            center_ceiling_key = self.textures.get_ceiling_key(visible_depth.source_tile)

            if self._should_advance_floor_theme(depth, visible_depth.source_tile):
                last_floor_theme_tile = visible_depth.source_tile

            commands.extend(
                self._build_center_ceiling_commands(
                    depth=depth,
                    zone=zone,
                    texture_key=center_ceiling_key,
                    darkness=darkness,
                )
            )
            commands.extend(
                self._build_center_floor_commands(
                    depth=depth,
                    zone=zone,
                    texture_key=center_floor_key,
                    darkness=darkness,
                )
            )

            if is_wall(visible_depth.center):
                commands.extend(
                    self._build_wall_panel_commands(
                        depth=depth,
                        order=2,
                        panel_id=f"d{depth}:back_wall",
                        texture_key=self.textures.get_wall_key(visible_depth.center),
                        quad=Quad.from_rect(zone.back_wall_rect),
                        darkness=darkness,
                    )
                )
                commands.extend(
                    self._build_center_wall_endcap_commands(
                        depth=depth,
                        zone=zone,
                        left_tile=visible_depth.left,
                        right_tile=visible_depth.right,
                        left_forward_tile=visible_depth.left_forward,
                        right_forward_tile=visible_depth.right_forward,
                        left_outer_tile=visible_depth.left_forward_outer,
                        right_outer_tile=visible_depth.right_forward_outer,
                        darkness=darkness,
                    )
                )

            commands.extend(
                self._build_side_commands(
                    depth,
                    zone,
                    "left",
                    visible_depth.left,
                    visible_depth.left_branch,
                    visible_depth.left_forward,
                    darkness,
                    outer_wall_tile=visible_depth.left_forward_outer,
                    next_zone=zones.get(depth + 1),
                    center_blocked=is_wall(visible_depth.center),
                )
            )
            commands.extend(
                self._build_side_special_surface_commands(
                    visible_depth=visible_depth,
                    zone=zone,
                    next_zone=zones.get(depth + 1),
                    side="left",
                    darkness=darkness,
                )
            )
            commands.extend(
                self._build_side_commands(
                    depth,
                    zone,
                    "right",
                    visible_depth.right,
                    visible_depth.right_branch,
                    visible_depth.right_forward,
                    darkness,
                    outer_wall_tile=visible_depth.right_forward_outer,
                    next_zone=zones.get(depth + 1),
                    center_blocked=is_wall(visible_depth.center),
                )
            )
            commands.extend(
                self._build_side_special_surface_commands(
                    visible_depth=visible_depth,
                    zone=zone,
                    next_zone=zones.get(depth + 1),
                    side="right",
                    darkness=darkness,
                )
            )

        return commands

    def _get_center_floor_texture_key(self, depth: int, source_tile, fallback_tile) -> str:
        if self._is_localized_current_floor_tile(depth, source_tile):
            if fallback_tile is not None:
                return self.textures.get_floor_key(fallback_tile)
            return "floor"
        return self.textures.get_floor_key(source_tile, fallback_tile=fallback_tile)

    def _should_advance_floor_theme(self, depth: int, source_tile) -> bool:
        if source_tile is None:
            return False
        if self.textures._is_floor_overlay_tile(source_tile):
            return False
        if self._is_localized_current_floor_tile(depth, source_tile):
            return False
        return True
