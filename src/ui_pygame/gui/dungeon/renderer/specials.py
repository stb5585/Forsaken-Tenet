"""Specials behavior for the renderer package."""

from __future__ import annotations

import math
import random

import pygame

from src.core import map_tiles, quest_progress
from src.ui_pygame.assets.enemy_combat_sprite_manager import get_enemy_combat_sprite_manager

from ..geometry import Quad
from ..projector import project_texture_to_quad
from ..scene import is_fake_wall, is_wall


class RendererSpecialTileMixin:
    def _render_special_tiles(self, scene, zones) -> None:
        visible_center_depths = []
        center_path_open = True
        max_visible_depth = scene.depths[-1].depth if scene.depths else 0
        for visible_depth in scene.depths:
            if not center_path_open:
                break

            self._render_side_special_tiles(
                visible_depth,
                zones[visible_depth.depth],
                zones.get(visible_depth.depth + 1),
            )

            visible_center_depths.append(visible_depth)

            if is_wall(visible_depth.center):
                center_path_open = False

        for visible_depth in reversed(visible_center_depths):
            if (
                visible_depth.depth == max_visible_depth
                and not is_wall(visible_depth.center)
                and "BossRoom" not in type(visible_depth.center).__name__
            ):
                continue
            rect = pygame.Rect(zones[visible_depth.depth].back_wall_rect.to_int_tuple())
            render_depth = visible_depth.depth
            center_type = (
                type(visible_depth.center).__name__ if visible_depth.center is not None else ""
            )
            if visible_depth.center is not None and "StairsUp" in center_type:
                rect = self._get_center_stairs_up_render_rect(zones, visible_depth.depth + 1)
            if visible_depth.center is not None and (
                "LadderDown" in center_type
                or "StairsDown" in center_type
                or self._get_decorative_floor_sprite_key(center_type) is not None
            ):
                floor_depth = visible_depth.depth + 1
                floor_zone = zones.get(floor_depth)
                if floor_zone is None:
                    continue
                floor_quad = self._get_center_floor_slot_quad(
                    zone=floor_zone,
                    depth=floor_depth,
                    slot_suffix="x0",
                )
                floor_bounds = floor_quad.bounding_rect()
                rect = pygame.Rect(
                    round(floor_bounds.x),
                    round(floor_bounds.y),
                    max(1, round(floor_bounds.w)),
                    max(1, round(floor_bounds.h)),
                )
                render_depth = floor_depth
            if (
                visible_depth.center is not None
                and "WarpPoint" in type(visible_depth.center).__name__
            ):
                continue
            self._render_special_tile(
                visible_depth.center,
                rect,
                darkness=self._get_layer_darkness(visible_depth.depth),
                depth=render_depth,
            )

        self._render_center_floor_special_tiles(scene, zones)

        current_depth = scene.depths[0] if scene.depths else None
        if current_depth is None:
            return

        current_tile = current_depth.source_tile
        if current_tile is not None and "WarpPoint" in type(current_tile).__name__:
            return

        current_rect = pygame.Rect(zones[1].back_wall_rect.to_int_tuple())
        if current_tile is not None and "StairsUp" in type(current_tile).__name__:
            current_rect = self._get_center_stairs_up_render_rect(zones, 2)
        self._render_special_tile(
            current_tile,
            current_rect,
            darkness=self._get_layer_darkness(1),
            depth=0,
        )

    def _render_center_floor_special_tiles(self, scene, zones) -> None:
        for visible_depth in scene.depths:
            tile = visible_depth.source_tile
            if tile is None:
                continue

            tile_type = type(tile).__name__
            is_warp_point = "WarpPoint" in tile_type
            is_current_down_ladder = visible_depth.depth == 1 and "LadderDown" in tile_type
            if not is_warp_point and not is_current_down_ladder:
                continue

            quad = self._get_center_floor_slot_quad(
                zone=zones[visible_depth.depth],
                depth=visible_depth.depth,
                slot_suffix="x0",
            )
            darkness = self._get_layer_darkness(visible_depth.depth)
            if is_warp_point:
                self._render_center_floor_warp_point(
                    quad,
                    darkness=darkness,
                    depth=visible_depth.depth,
                )
                continue

            bounds = quad.bounding_rect()
            self._render_special_tile(
                tile,
                pygame.Rect(
                    round(bounds.x),
                    round(bounds.y),
                    max(1, round(bounds.w)),
                    max(1, round(bounds.h)),
                ),
                darkness=darkness,
                depth=visible_depth.depth,
            )

    def _render_jester_force_fields(
        self, scene, zones, *, body: bool = True, arcs: bool = True
    ) -> None:
        for visible_depth in scene.depths:
            tile = visible_depth.center
            zone = zones.get(visible_depth.depth)
            if zone is None:
                continue

            if map_tiles.jester_force_field_blocks_entry(tile, self.player_char):
                self._render_jester_force_field(
                    pygame.Rect(zone.back_wall_rect.to_int_tuple()),
                    darkness=self._get_layer_darkness(visible_depth.depth),
                    depth=visible_depth.depth,
                    body=body,
                    arcs=arcs,
                )

            self._render_side_jester_force_field(
                visible_depth.left_forward,
                visible_depth.left,
                visible_depth.center,
                zone,
                zones.get(visible_depth.depth + 1),
                visible_depth.depth,
                "left",
                body=body,
                arcs=arcs,
            )
            self._render_side_jester_force_field(
                visible_depth.right_forward,
                visible_depth.right,
                visible_depth.center,
                zone,
                zones.get(visible_depth.depth + 1),
                visible_depth.depth,
                "right",
                body=body,
                arcs=arcs,
            )

    def _render_side_jester_force_field(
        self,
        tile,
        opening_tile,
        center_tile,
        zone,
        next_zone,
        depth: int,
        side: str,
        *,
        body: bool = True,
        arcs: bool = True,
    ) -> None:
        if not map_tiles.jester_force_field_blocks_entry(tile, self.player_char):
            return
        if self._opening_tile_blocks_view(opening_tile):
            return

        opening_rect = self._get_side_opening_rect(zone, side)
        render_rect = self._get_side_special_render_rect(
            opening_rect,
            tile,
            side,
            center_tile=center_tile,
            zone=zone,
            next_zone=next_zone,
            depth=depth,
        )
        if not isinstance(render_rect, pygame.Rect):
            render_rect = pygame.Rect(
                round(render_rect.x),
                round(render_rect.y),
                max(1, round(render_rect.w)),
                max(1, round(render_rect.h)),
            )

        previous_clip = self.screen.get_clip()
        try:
            clip_rect = self._get_side_special_clip_rect(
                opening_rect, tile, side, center_tile=center_tile
            )
            if clip_rect is not None:
                self.screen.set_clip(clip_rect)
            self._render_jester_force_field(
                render_rect,
                darkness=self._get_layer_darkness(depth),
                depth=depth,
                body=body,
                arcs=arcs,
            )
        finally:
            self.screen.set_clip(previous_clip)

    def _render_side_special_tiles(self, visible_depth, zone, next_zone=None) -> None:
        if next_zone is None:
            return

        if self._should_hide_side_doors_behind_center_wall(visible_depth):
            return

        darkness = self._get_layer_darkness(visible_depth.depth)
        left_rect = self._get_side_opening_rect(zone, "left")
        right_rect = self._get_side_opening_rect(zone, "right")
        self._render_side_special_tile(
            visible_depth.left_forward,
            left_rect,
            darkness=darkness,
            depth=visible_depth.depth,
            side="left",
            opening_tile=visible_depth.left,
            center_tile=visible_depth.center,
            zone=zone,
            next_zone=next_zone,
        )
        self._render_side_special_tile(
            visible_depth.right_forward,
            right_rect,
            darkness=darkness,
            depth=visible_depth.depth,
            side="right",
            opening_tile=visible_depth.right,
            center_tile=visible_depth.center,
            zone=zone,
            next_zone=next_zone,
        )

    def _get_side_special_surface_geometry(
        self, zone, next_zone, side: str, depth: int
    ) -> tuple[Quad, Quad, int]:
        if next_zone is None:
            if side == "left":
                return zone.left_floor_open, zone.left_ceiling_open, depth
            return zone.right_floor_open, zone.right_ceiling_open, depth

        base_offset = float(zone.rect.w) * 0.25
        edge_offset = float(zone.rect.w) * 0.5

        if side == "left":
            return (
                self._slice_quad_horizontal_region(
                    self._push_outer_floor_quad(
                        next_zone.center_floor_left, side, base_offset, edge_offset
                    ),
                    0.25,
                    0.75,
                ),
                self._slice_quad_horizontal_region(
                    self._push_outer_ceiling_quad(
                        next_zone.center_ceiling_left, side, base_offset, edge_offset
                    ),
                    0.25,
                    0.75,
                ),
                depth + 1,
            )

        return (
            self._slice_quad_horizontal_region(
                self._push_outer_floor_quad(
                    next_zone.center_floor_right, side, base_offset, edge_offset
                ),
                0.25,
                0.75,
            ),
            self._slice_quad_horizontal_region(
                self._push_outer_ceiling_quad(
                    next_zone.center_ceiling_right, side, base_offset, edge_offset
                ),
                0.25,
                0.75,
            ),
            depth + 1,
        )

    def _get_visible_side_special_floor_geometry(
        self, zone, side: str, depth: int, next_zone=None
    ) -> tuple[Quad, int, str]:
        base_quad = zone.left_floor_open if side == "left" else zone.right_floor_open
        if side == "left":
            sliced = self._slice_quad_region(base_quad, 0.10, 0.38, 0.45, 0.85)
        else:
            sliced = self._slice_quad_region(base_quad, 0.62, 0.90, 0.45, 0.85)
        return sliced, depth, f"d{depth}:{side}_opening_special_floor"

    def _get_visible_side_special_ceiling_geometry(
        self, zone, side: str, depth: int, next_zone=None
    ) -> tuple[Quad, int, str]:
        base_quad = zone.left_ceiling_open if side == "left" else zone.right_ceiling_open
        if side == "left":
            sliced = self._slice_quad_region(base_quad, 0.10, 0.42, 0.15, 0.70)
        else:
            sliced = self._slice_quad_region(base_quad, 0.58, 0.90, 0.15, 0.70)
        return sliced, depth, f"d{depth}:{side}_opening_special_ceiling"

    def _render_side_special_tile(
        self,
        tile,
        rect: pygame.Rect,
        darkness: float,
        depth: int,
        side: str,
        opening_tile=None,
        center_tile=None,
        zone=None,
        next_zone=None,
    ) -> None:
        if (
            self._opening_tile_blocks_view(opening_tile)
            or tile is None
            or (is_wall(tile) and not self._is_door_tile(tile))
        ):
            return
        if self._is_door_tile(tile):
            return
        if self._is_side_surface_only_ladder(tile):
            return

        render_depth = depth
        if (
            zone is not None
            and next_zone is not None
            and self._is_floor_sprite_tile(tile, getattr(self, "player_char", None))
            and not is_fake_wall(tile)
            and "BossRoom" not in type(tile).__name__
        ):
            render_depth = depth + 1

        render_rect = self._get_side_special_render_rect(
            rect,
            tile,
            side,
            center_tile=center_tile,
            zone=zone,
            next_zone=next_zone,
            depth=depth,
        )
        if not isinstance(render_rect, pygame.Rect):
            render_rect = pygame.Rect(
                round(render_rect.x),
                round(render_rect.y),
                max(1, round(render_rect.w)),
                max(1, round(render_rect.h)),
            )
        clip_rect = self._get_side_special_clip_rect(rect, tile, side, center_tile=center_tile)
        previous_clip = self.screen.get_clip()
        try:
            if clip_rect is not None:
                self.screen.set_clip(clip_rect)
            self._render_special_tile(
                tile,
                render_rect,
                darkness=darkness,
                depth=render_depth,
                side=side,
                lateral_view=True,
            )
        finally:
            self.screen.set_clip(previous_clip)

    def _precache_jester_force_field_bodies(self, world_dict, zones) -> None:
        sealed_jester_tiles = [
            tile
            for tile in world_dict.values()
            if map_tiles.jester_force_field_blocks_entry(tile, self.player_char)
        ]
        if not sealed_jester_tiles:
            return

        sample_tile = sealed_jester_tiles[0]
        for depth, zone in zones.items():
            darkness = self._get_layer_darkness(depth)
            alpha = self._get_jester_force_field_alpha(darkness, depth)
            self._precache_jester_force_field_body_for_rect(
                pygame.Rect(zone.back_wall_rect.to_int_tuple()),
                alpha,
            )
            for side in ("left", "right"):
                opening_rect = self._get_side_opening_rect(zone, side)
                render_rect = self._get_side_special_render_rect(
                    opening_rect,
                    sample_tile,
                    side,
                    center_tile=None,
                    zone=zone,
                    next_zone=zones.get(depth + 1),
                    depth=depth,
                )
                if not isinstance(render_rect, pygame.Rect):
                    render_rect = pygame.Rect(
                        round(render_rect.x),
                        round(render_rect.y),
                        max(1, round(render_rect.w)),
                        max(1, round(render_rect.h)),
                    )
                self._precache_jester_force_field_body_for_rect(render_rect, alpha)
                if zones.get(depth + 1) is None:
                    continue
                surface_rect = self._get_side_special_render_rect(
                    opening_rect,
                    sample_tile,
                    side,
                    center_tile=sample_tile,
                    zone=zone,
                    next_zone=zones.get(depth + 1),
                    depth=depth,
                )
                if not isinstance(surface_rect, pygame.Rect):
                    surface_rect = pygame.Rect(
                        round(surface_rect.x),
                        round(surface_rect.y),
                        max(1, round(surface_rect.w)),
                        max(1, round(surface_rect.h)),
                    )
                self._precache_jester_force_field_body_for_rect(surface_rect, alpha)

    def _precache_jester_force_field_body_for_rect(self, rect: pygame.Rect, alpha: int) -> None:
        field_rect = self._get_jester_force_field_rect(rect)
        if field_rect.width > 0 and field_rect.height > 0:
            self._get_jester_force_field_body(field_rect.size, alpha)

    def _render_special_tile(
        self,
        tile,
        rect: pygame.Rect,
        darkness: float,
        depth: int,
        side: str | None = None,
        lateral_view: bool = False,
    ) -> None:
        if tile is None:
            return

        tile_type = type(tile).__name__

        if depth <= 0 and "Door" in tile_type:
            return

        if tile_type == "OreVaultDoor":
            return

        if "Door" in tile_type:
            return

        if depth <= 0 and "WarpPoint" not in tile_type:
            return

        gathering_definition = map_tiles.definition_for_tile(tile)
        if gathering_definition is not None:
            # Gathering assets are projected as part of their floor tile. This
            # keeps them grounded in perspective, including beneath the player.
            return

        site = quest_progress.joffrey_site(getattr(self, "player_char", None), tile)
        if site:
            self._render_floor_sprite(
                site,
                rect,
                darkness=darkness,
                depth=depth,
                kind="dead_body",
                side=side,
                lateral_view=lateral_view,
            )
            return

        decorative_sprite_key = self._get_decorative_floor_sprite_key(tile_type)
        if decorative_sprite_key is not None:
            self._render_floor_sprite(
                decorative_sprite_key,
                rect,
                darkness=darkness,
                depth=depth,
                kind="decorative_prop",
                side=side,
                lateral_view=lateral_view,
            )
            return

        if "Chest" in tile_type:
            if getattr(tile, "opened", False) or getattr(tile, "open", False):
                sprite_key = "chest_open"
            elif getattr(tile, "locked", False):
                sprite_key = "chest_locked"
            else:
                sprite_key = "chest_closed"
            self._render_floor_sprite(
                sprite_key,
                rect,
                darkness=darkness,
                depth=depth,
                kind="chest",
                side=side,
                lateral_view=lateral_view,
            )
            return

        if "StairsUp" in tile_type:
            self._render_special_sprite(
                "stairs_up", rect, darkness=darkness, side=side, lateral_view=lateral_view
            )
            return

        if "StairsDown" in tile_type:
            self._render_floor_sprite(
                "stairs_down",
                rect,
                darkness=darkness,
                depth=depth,
                kind="stairs_down",
                side=side,
                lateral_view=lateral_view,
            )
            return

        if "LadderUp" in tile_type:
            self._render_floor_sprite(
                "ladder_up",
                rect,
                darkness=darkness,
                depth=depth,
                kind="ladder_up",
                side=side,
                lateral_view=lateral_view,
            )
            return

        if "LadderDown" in tile_type:
            self._render_floor_sprite(
                "ladder_down",
                rect,
                darkness=darkness,
                depth=depth,
                kind="ladder_down",
                side=side,
                lateral_view=lateral_view,
            )
            return

        if "Portal" in tile_type:
            self._render_special_sprite(
                "portal", rect, darkness=darkness, side=side, lateral_view=lateral_view
            )
            return

        if "WarpPoint" in tile_type:
            self._render_floor_sprite(
                self._warp_point_sprite_key(),
                rect,
                darkness=darkness,
                depth=depth,
                kind="warp_point",
                side=side,
                lateral_view=lateral_view,
            )
            if bool(getattr(self.player_char, "warp_point", False)):
                self._render_warp_point_sparks(
                    rect,
                    darkness=darkness,
                    depth=depth,
                    side=side,
                    lateral_view=lateral_view,
                )
            return

        if "Rotator" in tile_type:
            self._render_floor_sprite(
                "rotator",
                rect,
                darkness=darkness,
                depth=depth,
                kind="rotator",
                side=side,
                lateral_view=lateral_view,
            )
            return

        if "FunhouseTeleporter" in tile_type:
            return

        if is_fake_wall(tile) and bool(getattr(tile, "visited", False)):
            self._render_translucent_fake_wall_panel(
                tile,
                rect,
                darkness=darkness,
                depth=depth,
                side=side,
                lateral_view=lateral_view,
            )
            return

        if "Boulder" in tile_type:
            sprite_key = "boulder" if bool(getattr(tile, "read", False)) else "boulder_sword"
            self._render_floor_sprite(
                sprite_key,
                rect,
                darkness=darkness,
                depth=depth,
                kind="boulder",
                side=side,
                lateral_view=lateral_view,
            )
            return

        if bool(getattr(tile, "rookie_body_marker", False)) or bool(
            getattr(tile, "dropped_rookie_body", False)
        ):
            player_char = getattr(self, "player_char", None)
            visible = (
                not bool(getattr(tile, "read", False))
                if player_char is None
                else map_tiles.rookie_body_visible_for_player(player_char, tile)
            )
            if not visible:
                return
            self._render_floor_sprite(
                "dead_soldier_item",
                rect,
                darkness=darkness,
                depth=depth,
                kind="dead_soldier_item",
                side=side,
                lateral_view=lateral_view,
            )
            return

        if "DeadBody" in tile_type:
            sprite_key = "burial_site" if bool(getattr(tile, "read", False)) else "dead_body"
            self._render_floor_sprite(
                sprite_key,
                rect,
                darkness=darkness,
                depth=depth,
                kind="dead_body",
                side=side,
                lateral_view=lateral_view,
            )
            return

        if "RelicRoom" in tile_type:
            sprite_key = self._get_relic_altar_sprite_key(tile)
            self._render_floor_sprite(
                sprite_key,
                rect,
                darkness=darkness,
                depth=depth,
                kind="altar",
                side=side,
                lateral_view=lateral_view,
            )
            return

        if "GoldenChaliceRoom" in tile_type:
            if hasattr(
                getattr(self, "player_char", None), "quest_dict"
            ) and not map_tiles.chalice_altar_visible(self.player_char):
                return
            sprite_key = (
                "empty_golden_chalice_altar"
                if bool(getattr(tile, "read", False))
                else "golden_chalice_altar"
            )
            self._render_floor_sprite(
                sprite_key,
                rect,
                darkness=darkness,
                depth=depth,
                kind="altar",
                side=side,
                lateral_view=lateral_view,
            )
            return

        if "UnobtainiumRoom" in tile_type and not bool(getattr(tile, "visited", False)):
            self._render_floor_sprite(
                "unobtainium",
                rect,
                darkness=darkness,
                depth=depth,
                kind="unobtainium",
                side=side,
                lateral_view=lateral_view,
            )
            return

        if "SecretShop" in tile_type:
            self._render_special_sprite(
                "secret_shop", rect, darkness=darkness, side=side, lateral_view=lateral_view
            )
            return

        if "BossRoom" in tile_type:
            self._render_boss_enemy(
                tile, rect, darkness=darkness, depth=depth, side=side, lateral_view=lateral_view
            )
            return

    def _render_translucent_fake_wall_panel(
        self,
        tile,
        rect: pygame.Rect,
        darkness: float,
        depth: int,
        side: str | None = None,
        lateral_view: bool = False,
    ) -> None:
        darkness_factor = 1.0 - max(0.0, min(1.0, darkness))
        if darkness_factor <= 0.0:
            return

        wall_texture = self.textures.get_texture(self.textures.get_wall_key(tile))
        target_rect = rect
        if lateral_view and side is not None:
            target_rect = self._get_special_sprite_rect(rect, side=side, lateral_view=True)

        scaled = pygame.transform.smoothscale(wall_texture, target_rect.size)
        shaded = self._apply_darkness_to_surface(scaled, darkness)
        shaded.set_alpha(max(36, min(118, round(104 * darkness_factor))))
        self.screen.blit(shaded, target_rect.topleft)

    def _render_special_sprite(
        self,
        texture_key: str,
        rect: pygame.Rect,
        darkness: float,
        side: str | None = None,
        lateral_view: bool = False,
    ) -> None:
        sprite = self.textures.get_special_texture(texture_key)
        if sprite is None:
            return

        if lateral_view and texture_key.startswith("door_") and side is not None:
            target_rect = self._get_lateral_door_sprite_rect(rect, side)
        else:
            if lateral_view and texture_key.startswith("door_"):
                sprite = self._trim_transparent_sprite(sprite)
            target_rect = self._get_special_sprite_rect(
                rect,
                side=side,
                lateral_view=lateral_view,
                texture_key=texture_key,
            )
        scaled = pygame.transform.smoothscale(sprite, target_rect.size)
        if texture_key == "stairs_up":
            scaled = self._apply_stairs_up_ascend_gradient(scaled)
        shaded = self._apply_darkness_to_surface(scaled, darkness)
        self.screen.blit(shaded, target_rect.topleft)

    def _render_floor_sprite(
        self,
        texture_key: str,
        rect: pygame.Rect,
        darkness: float,
        depth: int,
        kind: str,
        side: str | None = None,
        lateral_view: bool = False,
    ) -> None:
        size_ratio = self._get_floor_sprite_ratio(depth, kind)
        size_ratio *= self._get_floor_sprite_texture_scale(texture_key)
        if lateral_view:
            size_ratio *= 0.9
        sprite_basis = rect.width if kind == "stairs_down" else rect.height
        sprite_size = max(8, int(sprite_basis * size_ratio))
        sprite = self.textures.get_special_texture(texture_key, sprite_size)
        if sprite is None:
            return

        sprite_rect = sprite.get_rect()
        sprite_rect.midbottom = self._get_floor_sprite_anchor(
            rect, side=side, lateral_view=lateral_view
        )

        if kind == "ladder_up":
            sprite_rect.y = rect.y + (rect.height - sprite_rect.height) // 2
        elif kind == "stairs_down":
            sprite_rect.midbottom = (
                rect.centerx,
                round(rect.y + (rect.height * (0.90 if lateral_view else 0.96))),
            )
        elif kind == "ladder_down" and not lateral_view:
            sprite_rect.midbottom = (
                rect.centerx,
                round(rect.y + (rect.height * 0.55)),
            )
        elif kind == "dead_body":
            anchor_x, _anchor_y = self._get_floor_sprite_anchor(
                rect, side=side, lateral_view=lateral_view
            )
            sprite_rect.midbottom = (
                anchor_x,
                round(rect.y + (rect.height * (1.06 if lateral_view else 1.08))),
            )

        if lateral_view and side is not None:
            if kind in {"chest", "decorative_prop"}:
                shaded = self._apply_darkness_to_surface(sprite, darkness)
                self.screen.blit(shaded, sprite_rect.topleft)
            else:
                quad = self._get_lateral_floor_sprite_quad(sprite_rect, side)
                projected = project_texture_to_quad(sprite, quad, darkness=darkness)
                self.screen.blit(projected.surface, projected.topleft)
            return

        shaded = self._apply_darkness_to_surface(sprite, darkness)
        self.screen.blit(shaded, sprite_rect.topleft)

    def _render_boss_enemy(
        self,
        tile,
        rect: pygame.Rect,
        darkness: float,
        depth: int,
        side: str | None = None,
        lateral_view: bool = False,
    ) -> None:
        if bool(getattr(tile, "defeated", False)):
            self._render_floor_sprite(
                "burial_site",
                rect,
                darkness=darkness,
                depth=depth,
                kind="defeated_boss",
                side=side,
                lateral_view=lateral_view,
            )
            return

        enemy = getattr(tile, "enemy", None)
        if enemy is None:
            return

        if callable(enemy):
            try:
                enemy = enemy()
            except Exception:
                return

        enemy_name = getattr(enemy, "name", None)
        if not enemy_name:
            return

        if hasattr(enemy, "is_alive") and not enemy.is_alive():
            return

        size_ratio = {0: 2.0, 1: 1.0, 2: 0.8, 3: 0.65}.get(depth, 0.65)
        size_ratio *= get_enemy_combat_sprite_manager().get_dungeon_scale_for_enemy(enemy)
        sprite_basis = min(rect.width, rect.height)
        if lateral_view and side is not None:
            sprite_basis = rect.height
        sprite_size = max(8, int(sprite_basis * size_ratio))
        sprite = self.textures.get_enemy_texture(enemy_name, sprite_size)

        if sprite is None:
            fallback = pygame.Surface((sprite_size, sprite_size), pygame.SRCALPHA)
            fallback.fill((200, 50, 50, 255))
            sprite = fallback

        sprite_rect = sprite.get_rect()
        sprite_rect.midbottom = self._get_floor_sprite_anchor(
            rect, side=side, lateral_view=lateral_view
        )

        if lateral_view and side is not None:
            quad = self._get_lateral_floor_sprite_quad(sprite_rect, side)
            projected = project_texture_to_quad(sprite, quad, darkness=darkness)
            self.screen.blit(projected.surface, projected.topleft)
            return

        shaded = self._apply_darkness_to_surface(sprite, darkness)
        self.screen.blit(shaded, sprite_rect.topleft)

    def _render_jester_force_field(
        self,
        rect: pygame.Rect,
        darkness: float,
        depth: int,
        *,
        body: bool = True,
        arcs: bool = True,
    ) -> None:
        darkness_factor = max(0.0, 1.0 - min(1.0, darkness))
        if darkness_factor <= 0.0:
            return

        field_rect = self._get_jester_force_field_rect(rect)
        if field_rect.width <= 0 or field_rect.height <= 0:
            return

        alpha = self._get_jester_force_field_alpha(darkness, depth)
        overlay = pygame.Surface(field_rect.size, pygame.SRCALPHA)

        border_color = (124, 176, 236, max(54, alpha - 14))
        (92, 224, 246, max(48, alpha - 28))
        glow_color = (40, 184, 230, max(42, alpha // 2))
        hot_color = (96, 230, 255, max(90, min(178, alpha + 34)))
        core_color = (244, 254, 255, max(150, min(232, alpha + 82)))

        if body:
            overlay.blit(self._get_jester_force_field_body(field_rect.size, alpha), (0, 0))
            overlay_rect = overlay.get_rect()
            pygame.draw.rect(overlay, border_color, overlay_rect, width=1, border_radius=2)

        if arcs:
            self._force_field_seed_counter += 1
            rng = random.Random(
                (pygame.time.get_ticks() * 1009) + (self._force_field_seed_counter * 9173) + depth
            )
            outer_glow = pygame.Surface(overlay.get_size(), pygame.SRCALPHA)
            inner_glow = pygame.Surface(overlay.get_size(), pygame.SRCALPHA)
            for start_ratio in (0.20, 0.48, 0.76):
                start_x = round(field_rect.width * start_ratio) + rng.randint(-3, 3)
                end_x = start_x + rng.randint(-6, 6)
                start = (max(2, min(field_rect.width - 3, start_x)), 0)
                end = (max(2, min(field_rect.width - 3, end_x)), field_rect.height)
                displacement = max(8.0, field_rect.width * 0.20)
                points = self._build_midpoint_lightning_points(
                    start, end, displacement, rng, iterations=6
                )
                self._draw_layered_lightning(
                    overlay,
                    points,
                    glow_color,
                    hot_color,
                    core_color,
                    outer_glow=outer_glow,
                    inner_glow=inner_glow,
                )

                for branch_start in points[2:-2:4]:
                    branch_direction = -1 if rng.random() < 0.5 else 1
                    branch_end = (
                        max(
                            2,
                            min(
                                field_rect.width - 3,
                                branch_start[0] + branch_direction * rng.randint(8, 20),
                            ),
                        ),
                        max(2, min(field_rect.height - 3, branch_start[1] + rng.randint(-6, 10))),
                    )
                    branch_points = self._build_midpoint_lightning_points(
                        branch_start,
                        branch_end,
                        max(4.0, field_rect.width * 0.06),
                        rng,
                        iterations=4,
                    )
                    self._draw_layered_lightning(
                        overlay,
                        branch_points,
                        glow_color,
                        hot_color,
                        core_color,
                        outer_glow=outer_glow,
                        inner_glow=inner_glow,
                    )

            overlay.blit(outer_glow, (0, 0), special_flags=pygame.BLEND_RGBA_ADD)
            overlay.blit(inner_glow, (0, 0), special_flags=pygame.BLEND_RGBA_ADD)

        self.screen.blit(overlay, field_rect.topleft)

    @staticmethod
    def _get_jester_force_field_rect(rect: pygame.Rect) -> pygame.Rect:
        inset_x = max(1, round(rect.width * 0.01))
        inset_y = max(1, round(rect.height * 0.01))
        return rect.inflate(-inset_x * 2, -inset_y * 2)

    @staticmethod
    def _get_jester_force_field_alpha(darkness: float, depth: int) -> int:
        darkness_factor = max(0.0, 1.0 - min(1.0, darkness))
        field_visibility = 0.62 + (darkness_factor * 0.38)
        return max(72, min(142, round((132 - (depth * 8)) * field_visibility)))

    def _get_jester_force_field_body(self, size: tuple[int, int], alpha: int) -> pygame.Surface:
        cache_key = (size[0], size[1], alpha)
        cached = self._jester_force_field_body_cache.get(cache_key)
        if cached is not None:
            return cached

        if len(self._jester_force_field_body_cache) > 12:
            self._jester_force_field_body_cache.clear()

        width, height = size
        if width <= 0 or height <= 0:
            return pygame.Surface(size, pygame.SRCALPHA)

        surface = pygame.Surface(size, pygame.SRCALPHA)
        surface.fill((14, 18, 58, min(160, round(alpha * 0.38))))

        center_x = width / 2
        center_y = height / 2
        max_radius = max(width, height) * 0.62
        for layer in range(9, 0, -1):
            ratio = layer / 9
            radius_x = max(1, round(max_radius * ratio))
            radius_y = max(1, round(max_radius * ratio))
            center_light = 1.0 - ratio
            color = (
                round(30 + (44 * center_light)),
                round(70 + (104 * center_light)),
                round(118 + (118 * center_light)),
                max(8, round(alpha * (0.07 + (0.09 * center_light)))),
            )
            pygame.draw.ellipse(
                surface,
                color,
                pygame.Rect(
                    round(center_x - radius_x),
                    round(center_y - radius_y),
                    radius_x * 2,
                    radius_y * 2,
                ),
            )

        self._jester_force_field_body_cache[cache_key] = surface
        return surface

    @staticmethod
    def _build_midpoint_lightning_points(
        start: tuple[int, int],
        end: tuple[int, int],
        displacement: float,
        rng: random.Random,
        *,
        iterations: int,
    ) -> list[tuple[int, int]]:
        points = [(float(start[0]), float(start[1])), (float(end[0]), float(end[1]))]
        current_displacement = displacement

        for _ in range(iterations):
            next_points = [points[0]]
            for point_a, point_b in zip(points, points[1:]):
                mid_x = (point_a[0] + point_b[0]) / 2.0
                mid_y = (point_a[1] + point_b[1]) / 2.0
                dx = point_b[0] - point_a[0]
                dy = point_b[1] - point_a[1]
                length = math.hypot(dx, dy)
                if length == 0:
                    next_points.append(point_b)
                    continue

                normal_x = -dy / length
                normal_y = dx / length
                offset = rng.uniform(-current_displacement, current_displacement)
                mid_x += normal_x * offset
                mid_y += normal_y * offset
                next_points.append((mid_x, mid_y))
                next_points.append(point_b)
            points = next_points
            current_displacement *= 0.5

        return [(round(x), round(y)) for x, y in points]

    @staticmethod
    def _draw_layered_lightning(
        surface: pygame.Surface,
        points: list[tuple[int, int]],
        glow_color: tuple[int, int, int, int],
        hot_color: tuple[int, int, int, int],
        core_color: tuple[int, int, int, int],
        outer_glow: pygame.Surface | None = None,
        inner_glow: pygame.Surface | None = None,
    ) -> None:
        if len(points) < 2:
            return

        blit_glow = outer_glow is None or inner_glow is None
        if outer_glow is None:
            outer_glow = pygame.Surface(surface.get_size(), pygame.SRCALPHA)
        if inner_glow is None:
            inner_glow = pygame.Surface(surface.get_size(), pygame.SRCALPHA)

        pygame.draw.lines(outer_glow, glow_color, False, points, 8)
        pygame.draw.lines(inner_glow, hot_color, False, points, 4)
        if blit_glow:
            surface.blit(outer_glow, (0, 0), special_flags=pygame.BLEND_RGBA_ADD)
            surface.blit(inner_glow, (0, 0), special_flags=pygame.BLEND_RGBA_ADD)

        pygame.draw.lines(surface, core_color, False, points, 1)

    @staticmethod
    def _is_floor_sprite_tile(tile, player_char=None) -> bool:
        if tile is None:
            return False
        if quest_progress.joffrey_site(player_char, tile):
            return True
        if map_tiles.definition_for_tile(tile) is not None:
            return True
        if bool(getattr(tile, "rookie_body_marker", False)) or bool(
            getattr(tile, "dropped_rookie_body", False)
        ):
            if player_char is None:
                return not bool(getattr(tile, "read", False))
            return map_tiles.rookie_body_visible_for_player(player_char, tile)

        tile_type = type(tile).__name__
        return any(
            name in tile_type
            for name in (
                "Chest",
                "Boulder",
                "DeadBody",
                "RelicRoom",
                "GoldenChaliceRoom",
                "UnobtainiumRoom",
                "BossRoom",
                "RubbleTile",
                "RootGrowthTile",
                "FungusPatchTile",
                "CrystalClusterTile",
                "BonePileTile",
                "BrokenGearTile",
            )
        )
