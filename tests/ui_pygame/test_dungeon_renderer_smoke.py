from __future__ import annotations

import json
import os
from dataclasses import dataclass
from types import SimpleNamespace

import pygame
import pytest

from src.core import map_tiles
from src.ui_pygame.gui.dungeon.assets import TEXTURE_PATHS, TextureLibrary
from src.ui_pygame.gui.dungeon.geometry import (
    Quad,
    build_depth_rect,
    build_next_depth_rect,
    build_zone_geometry,
)
from src.ui_pygame.gui.dungeon.projector import project_texture_to_quad
from src.ui_pygame.gui.dungeon.renderer import SceneRenderer
from src.ui_pygame.gui.dungeon.scene import extract_visible_scene
from src.ui_pygame.gui.dungeon_renderer import DungeonRenderer

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")


class OpenTile:
    enter = True


class WallTile:
    enter = False


class FakeWall:
    enter = True

    def __init__(self, visited=True):
        self.visited = visited


class ThievesGuildTrialFakeWall(FakeWall):
    pass


class LockedDoor:
    enter = False
    open = False


class OpenDoor:
    enter = True
    open = True


class OreVaultDoor:
    enter = False
    open = False

    def __init__(self, detected=False, open=False):
        self.detected = detected
        self.open = open
        self.enter = open


class ChestRoom:
    enter = True
    locked = False
    open = False


class LadderUp:
    enter = True


class StairsUp:
    enter = True


class LadderDown:
    enter = True


class StairsDown:
    enter = True


class UndergroundSpring:
    enter = True


class BonePileTile:
    enter = True


class FirePath:
    enter = True


class FunhousePath:
    enter = True


class FunhouseWall:
    enter = False


class FunhouseBoundaryWall:
    enter = False


class MirrorWall:
    enter = False


class RubbleTile:
    enter = True


class RootGrowthTile:
    enter = True


class FungusPatchTile:
    enter = True


class CrystalClusterTile:
    enter = True


class Portal:
    enter = True


class Boulder:
    enter = True

    def __init__(self, read=False):
        self.read = read


class DeadBody:
    enter = True

    def __init__(self, read=False):
        self.read = read


class RookieCavePath:
    enter = True
    rookie_body_marker = True

    def __init__(self, read=False):
        self.read = read


class RelicRoom:
    enter = False

    def __init__(self, read=False):
        self.read = read


class GoldenChaliceRoom:
    enter = False

    def __init__(self, read=False):
        self.read = read


class UnobtainiumRoom:
    enter = True

    def __init__(self, visited=False):
        self.visited = visited


class SecretShop:
    enter = False


class WarpPoint:
    enter = True


class Rotator:
    enter = True


class FunhouseTeleporter:
    enter = True

    def __init__(self, active=True):
        self.active = active


class BossRoom:
    enter = True

    def __init__(self, enemy=None, defeated=False):
        self.enemy = enemy
        self.defeated = defeated


class JesterBossRoom(BossRoom):
    pass


class DummyEnemy:
    def __init__(self, name="Minotaur"):
        self.name = name

    def is_alive(self):
        return True


@dataclass
class DummyPlayer:
    location_x: int = 0
    location_y: int = 0
    location_z: int = 1
    facing: str = "east"
    warp_point: bool = False


@dataclass
class DummyPresenter:
    width: int
    height: int
    screen: pygame.Surface


def _build_scene_commands(scene_renderer: SceneRenderer, player, world):
    view_w, view_h = scene_renderer._get_viewport_size()
    scene = extract_visible_scene(player, world, max_depth=3)
    zones = {
        depth: build_zone_geometry(
            build_depth_rect(view_w, view_h, depth),
            build_next_depth_rect(build_depth_rect(view_w, view_h, depth)),
            depth=depth,
        )
        for depth in (1, 2, 3)
    }
    return scene_renderer._build_render_commands(scene, zones), zones


def _render_side_forward_tile_case(tile, side: str, side_depth: int):
    pygame.init()
    screen = pygame.display.set_mode((640, 480))
    presenter = DummyPresenter(width=640, height=480, screen=screen)
    scene_renderer = SceneRenderer(presenter, TextureLibrary())
    player = DummyPlayer()

    side_y = -1 if side == "left" else 1
    world = {
        (0, 0, 1): OpenTile(),
        (1, 0, 1): OpenTile(),
        (2, 0, 1): OpenTile(),
        (3, 0, 1): OpenTile(),
        (0, side_y, 1): OpenTile(),
        (1, side_y, 1): OpenTile(),
        (2, side_y, 1): OpenTile(),
        (3, side_y, 1): OpenTile(),
    }
    world[(side_depth, side_y, 1)] = tile

    projected_calls = []
    rendered_tiles = []
    original_get_projected_surface = scene_renderer.textures.get_projected_surface
    original_render_special_tile = scene_renderer._render_special_tile

    def recording_get_projected_surface(panel_id, texture_key, quad, darkness, view_size):
        projected_calls.append((panel_id, texture_key))
        return original_get_projected_surface(panel_id, texture_key, quad, darkness, view_size)

    def recording_render_special_tile(tile, rect, darkness, depth, side=None, lateral_view=False):
        rendered_tiles.append((type(tile).__name__ if tile else None, depth, side, lateral_view))
        return original_render_special_tile(
            tile,
            rect,
            darkness,
            depth,
            side=side,
            lateral_view=lateral_view,
        )

    scene_renderer.textures.get_projected_surface = recording_get_projected_surface
    scene_renderer._render_special_tile = recording_render_special_tile

    try:
        scene_renderer.render(player, world)
        return (
            projected_calls,
            rendered_tiles,
            scene_renderer.textures.get_surface_slot_overrides(),
        )
    finally:
        pygame.quit()


def test_dungeon_renderer_smoke():
    pygame.init()
    screen = pygame.display.set_mode((640, 480))
    presenter = DummyPresenter(width=640, height=480, screen=screen)
    renderer = DungeonRenderer(presenter)
    player = DummyPlayer()
    world = {
        (0, 0, 1): OpenTile(),
        (1, 0, 1): OpenTile(),
        (2, 0, 1): OpenTile(),
        (3, 0, 1): WallTile(),
        (0, -1, 1): OpenTile(),
        (1, -1, 1): WallTile(),
        (0, 1, 1): OpenTile(),
        (1, 1, 1): OpenTile(),
    }

    renderer.render_dungeon_view(player, world)
    renderer.render_message_area(["Line 1", "Line 2"], scroll_offset=0, lines_per_page=2)
    renderer.trigger_damage_flash(duration_ms=100, alpha=128)
    renderer.render_damage_flash()

    pygame.quit()


def test_dungeon_renderer_special_tiles_smoke():
    pygame.init()
    screen = pygame.display.set_mode((640, 480))
    presenter = DummyPresenter(width=640, height=480, screen=screen)
    renderer = DungeonRenderer(presenter)
    player = DummyPlayer()
    world = {
        (0, 0, 1): OpenTile(),
        (1, 0, 1): ChestRoom(),
        (2, 0, 1): LockedDoor(),
        (3, 0, 1): StairsDown(),
        (0, -1, 1): OpenTile(),
        (0, 1, 1): OpenTile(),
        (1, -1, 1): OpenTile(),
        (1, 1, 1): OpenTile(),
        (2, -1, 1): OpenTile(),
        (2, 1, 1): OpenTile(),
        (3, -1, 1): OpenTile(),
        (3, 1, 1): OpenTile(),
    }

    world[(0, 0, 1)] = LadderUp()
    renderer.render_dungeon_view(player, world)

    pixel_data = pygame.image.tostring(screen, "RGBA")
    assert any(channel != 0 for channel in pixel_data)

    pygame.quit()


def test_dungeon_renderer_applies_soft_vignette_to_viewport():
    pygame.init()
    screen = pygame.display.set_mode((640, 480))
    presenter = DummyPresenter(width=640, height=480, screen=screen)
    renderer = DungeonRenderer(presenter)
    screen.fill((220, 220, 220))

    renderer.overlays.render_vignette()

    left_corner = screen.get_at((2, 2))
    center = screen.get_at((150, 150))
    divider = screen.get_at((int(640 * 0.65) - 1, 150))
    right_hud = screen.get_at((500, 150))

    assert left_corner.r < center.r
    assert left_corner.g < center.g
    assert left_corner.b < center.b
    assert divider.r < center.r
    assert right_hud.r == 220 and right_hud.g == 220 and right_hud.b == 220

    pygame.quit()


def test_dungeon_renderer_reuses_vignette_surfaces_for_unchanged_viewport():
    pygame.init()
    screen = pygame.display.set_mode((640, 480))
    presenter = DummyPresenter(width=640, height=480, screen=screen)
    renderer = DungeonRenderer(presenter)

    renderer.overlays.render_vignette()
    cached_vignette = renderer.overlays._vignette_cache[(416, 480)]
    renderer.overlays.render_vignette()

    assert renderer.overlays._vignette_cache[(416, 480)] is cached_vignette
    pygame.quit()


def test_dungeon_renderer_applies_low_health_vignette_only_when_critical():
    pygame.init()
    screen = pygame.display.set_mode((640, 480))
    presenter = DummyPresenter(width=640, height=480, screen=screen)
    renderer = DungeonRenderer(presenter)
    player = SimpleNamespace(health=SimpleNamespace(current=25, max=100))
    screen.fill((220, 220, 220))

    renderer.overlays.render_low_health_vignette(player)

    left_corner = screen.get_at((2, 2))
    center = screen.get_at((150, 150))
    right_hud = screen.get_at((500, 150))

    assert left_corner.g < center.g
    assert left_corner.b < center.b
    assert right_hud.r == 220 and right_hud.g == 220 and right_hud.b == 220

    screen.fill((220, 220, 220))
    player.health.current = 26
    renderer.overlays.render_low_health_vignette(player)

    assert screen.get_at((2, 2)).r == 220
    assert screen.get_at((2, 2)).g == 220
    assert screen.get_at((2, 2)).b == 220

    pygame.quit()


def test_dungeon_renderer_render_view_invokes_low_health_overlay(monkeypatch):
    pygame.init()
    screen = pygame.display.set_mode((640, 480))
    presenter = DummyPresenter(width=640, height=480, screen=screen)
    renderer = DungeonRenderer(presenter)
    player = SimpleNamespace(health=SimpleNamespace(current=5, max=20))
    calls = []

    monkeypatch.setattr(
        renderer.scene_renderer,
        "render",
        lambda player_char, world_dict: calls.append(("scene", player_char, world_dict)),
    )
    monkeypatch.setattr(renderer.overlays, "render_vignette", lambda: calls.append(("vignette",)))
    monkeypatch.setattr(
        renderer.overlays,
        "render_low_health_vignette",
        lambda player_char: calls.append(("low-health", player_char)),
    )

    renderer.render_dungeon_view(player, {"world": True})

    assert calls == [
        ("scene", player, {"world": True}),
        ("vignette",),
        ("low-health", player),
    ]
    pygame.quit()


def test_texture_library_does_not_tile_ladder_pit_panels():
    pygame.init()
    textures = TextureLibrary()

    ceiling = textures.get_texture("ceiling_pit")
    floor = textures.get_texture("floor_pit")

    assert textures.get_ceiling_key(LadderUp()) == "ceiling_pit"
    assert textures.get_panel_texture("d2:center_ceiling", "ceiling_pit").get_size() == (
        ceiling.get_width() * 5,
        ceiling.get_height(),
    )
    assert textures.get_panel_texture("d2:center_floor", "floor_pit").get_size() == (
        floor.get_width() * 5,
        floor.get_height(),
    )
    assert (
        textures.get_panel_texture("d2:right_corridor_outer_ceiling", "ceiling_pit").get_size()
        == ceiling.get_size()
    )
    assert (
        textures.get_panel_texture("d2:right_corridor_outer_floor", "floor_pit").get_size()
        == floor.get_size()
    )

    pygame.quit()


def test_texture_library_resolves_repo_assets_when_cwd_changes(tmp_path, monkeypatch):
    pygame.init()
    monkeypatch.chdir(tmp_path)

    textures = TextureLibrary()

    assert textures.get_texture("wall").get_width() > 0
    assert textures.get_special_texture("stairs_down") is not None
    assert textures.get_enemy_texture("Minotaur", size=32) is not None

    pygame.quit()


def test_stair_special_tile_sprites_are_opaque_and_directionally_distinct():
    pygame.init()
    textures = TextureLibrary()

    stairs_up = textures.get_special_texture("stairs_up")
    stairs_down = textures.get_special_texture("stairs_down")

    def alpha_stats(surface):
        width, height = surface.get_size()
        alphas = [surface.get_at((x, y)).a for y in range(height) for x in range(width)]
        coverage = sum(alpha > 128 for alpha in alphas) / len(alphas)
        top = min(y for y in range(height) for x in range(width) if surface.get_at((x, y)).a > 128)
        return coverage, top

    def opaque_row_width(surface, row):
        opaque_columns = [x for x in range(surface.get_width()) if surface.get_at((x, row)).a > 128]
        if not opaque_columns:
            return 0
        return max(opaque_columns) - min(opaque_columns) + 1

    def opaque_luminance(surface):
        colors = [
            surface.get_at((x, y))
            for y in range(surface.get_height())
            for x in range(surface.get_width())
            if surface.get_at((x, y)).a > 128
        ]
        return sum(
            (0.2126 * color.r) + (0.7152 * color.g) + (0.0722 * color.b) for color in colors
        ) / len(colors)

    def opaque_rgb_mean(surface):
        colors = [
            surface.get_at((x, y))
            for y in range(surface.get_height())
            for x in range(surface.get_width())
            if surface.get_at((x, y)).a > 128
        ]
        return tuple(
            sum(getattr(color, channel) for color in colors) / len(colors)
            for channel in ("r", "g", "b")
        )

    up_coverage, up_top = alpha_stats(stairs_up)
    down_coverage, down_top = alpha_stats(stairs_down)
    up_bounds = stairs_up.get_bounding_rect(min_alpha=128)
    up_mean_r, _up_mean_g, up_mean_b = opaque_rgb_mean(stairs_up)
    down_mean_r, _down_mean_g, down_mean_b = opaque_rgb_mean(stairs_down)
    up_top_pixel = stairs_up.get_at((stairs_up.get_width() // 2, 0))
    down_bounds = stairs_down.get_bounding_rect(min_alpha=128)
    down_far_width = opaque_row_width(
        stairs_down,
        down_bounds.y + int(down_bounds.height * 0.18),
    )
    down_near_width = opaque_row_width(
        stairs_down,
        down_bounds.bottom - int(down_bounds.height * 0.12),
    )

    assert up_coverage > 0.35
    assert 110 <= up_bounds.y <= 135
    assert up_bounds.height >= 360
    assert opaque_luminance(stairs_up) <= 76
    assert up_mean_b <= up_mean_r + 14
    assert abs(up_mean_r - down_mean_r) <= 22
    assert abs(up_mean_b - down_mean_b) <= 22
    assert up_top_pixel.a == 0
    assert down_coverage > 0.20
    assert down_top > up_top + 60
    assert down_bounds.height <= 200
    assert down_near_width > down_far_width * 1.55

    pygame.quit()


def test_texture_library_loads_dungeon_texture_manifest():
    pygame.init()
    textures = TextureLibrary()

    assert "floor_crystal" in textures.texture_paths
    assert "crystal_cluster" in textures.special_texture_paths
    assert "warp_point_active" in textures.special_texture_paths
    assert "warp_point_inactive" in textures.special_texture_paths
    assert textures.get_texture("floor_crystal").get_size() == (512, 512)
    assert textures.get_texture("door_open").get_at((256, 330)).a == 0
    assert textures.get_texture("door_open").get_at((256, 490)).a == 0
    assert max(textures.get_special_texture("crystal_cluster", size=64).get_size()) == 64
    assert textures.get_special_texture("dead_soldier_item") is not None
    assert textures.get_special_texture("warp_point_active") is not None
    assert textures.get_special_texture("warp_point_inactive") is not None

    pygame.quit()


def test_texture_library_records_manifest_asset_fallbacks(tmp_path):
    pygame.init()
    tileset = tmp_path / "tiles"
    tileset.mkdir()
    (tileset / "dungeon_texture_manifest.json").write_text(
        json.dumps(
            {
                "textures": {"floor_test": "floors/missing_test.png"},
                "special_textures": {"prop_test": "special_tiles/missing_prop.png"},
            }
        ),
        encoding="utf-8",
    )

    textures = TextureLibrary(tileset_base=tileset)
    assert textures.get_texture("floor_test").get_size() == (128, 128)
    assert textures.get_special_texture("prop_test", size=24) is not None

    fallbacks = textures.get_asset_fallbacks()
    assert fallbacks["texture:floor_test"].endswith("floors/missing_test.png")
    assert fallbacks["special:prop_test"].endswith("special_tiles/missing_prop.png")

    pygame.quit()


def test_texture_library_routes_decorative_tile_keys():
    pygame.init()
    textures = TextureLibrary()

    assert textures.get_floor_key(RootGrowthTile()) == "floor_roots"
    assert textures.get_floor_key(FungusPatchTile()) == "floor_fungus"
    assert textures.get_floor_key(CrystalClusterTile()) == "floor_crystal"
    assert textures.get_floor_key(RubbleTile()) == "floor_debris"
    assert textures.get_floor_key(FunhousePath()) == "floor_funhouse"
    assert textures.get_wall_key(FunhouseWall()) == "wall_funhouse"
    assert textures.get_wall_key(FunhouseBoundaryWall()) == "wall_funhouse_boundary"
    assert textures.get_wall_key(MirrorWall()) == "wall_funhouse"
    assert textures.get_ceiling_key(FunhousePath()) == "ceiling_funhouse"
    assert textures.get_ceiling_key(FungusPatchTile()) == "ceiling_fungus"
    assert textures.get_ceiling_key(CrystalClusterTile()) == "ceiling_crystal"
    assert SceneRenderer._get_decorative_floor_sprite_key("RubbleTile") == "rubble"
    assert SceneRenderer._get_decorative_floor_sprite_key("RootGrowthTile") == "root_growth"

    pygame.quit()


def test_wall_overlay_key_is_stable_for_same_map_tile_at_different_depths():
    class WallWithPosition:
        x = 3
        y = 5
        z = 2
        enter = False

    tile = WallWithPosition()

    assert SceneRenderer._get_wall_overlay_key(
        tile, depth=1
    ) == SceneRenderer._get_wall_overlay_key(tile, depth=3)


def test_wall_overlay_key_hides_sconces_on_fake_walls():
    assert SceneRenderer._get_wall_overlay_key(FakeWall(visited=False), depth=1) is None
    assert SceneRenderer._get_wall_overlay_key(FakeWall(visited=True), depth=3) is None
    assert (
        SceneRenderer._get_wall_overlay_key(ThievesGuildTrialFakeWall(visited=False), depth=2)
        is None
    )
    assert SceneRenderer._get_wall_overlay_key(StairsUp(), depth=1) is None


@pytest.mark.parametrize(
    ("level", "sprite_key"),
    (
        (1, "triangulus_altar"),
        (2, "quadrata_altar"),
        (3, "hexagonum_altar"),
        (4, "luna_altar"),
        (5, "polaris_altar"),
        (6, "infinitas_altar"),
    ),
)
def test_relic_altar_sprite_follows_relic_floor_order(level, sprite_key):
    renderer = object.__new__(SceneRenderer)
    renderer.player_char = SimpleNamespace(location_z=level)

    assert renderer._get_relic_altar_sprite_key(RelicRoom(read=False)) == sprite_key
    assert renderer._get_relic_altar_sprite_key(RelicRoom(read=True)) == "empty_altar"


def test_wall_overlays_stop_behind_foreground_stairs():
    pygame.init()
    screen = pygame.Surface((640, 480))
    presenter = DummyPresenter(width=640, height=480, screen=screen)
    scene_renderer = SceneRenderer(presenter, TextureLibrary())
    zones = {
        depth: build_zone_geometry(
            build_depth_rect(416, 480, depth),
            build_next_depth_rect(build_depth_rect(416, 480, depth)),
            depth=depth,
        )
        for depth in (1, 2)
    }
    scene = SimpleNamespace(
        depths=(
            SimpleNamespace(
                depth=1,
                center=StairsUp(),
                left=OpenTile(),
                right=OpenTile(),
            ),
            SimpleNamespace(
                depth=2,
                center=WallTile(),
                left=WallTile(),
                right=WallTile(),
            ),
        )
    )
    calls = []
    scene_renderer._render_wall_overlay_for_tile = lambda *args, **kwargs: calls.append(
        (args, kwargs)
    )

    scene_renderer._render_wall_overlays(scene, zones)

    assert calls == []
    pygame.quit()


def test_wall_overlays_stop_at_blocking_center_wall():
    pygame.init()
    screen = pygame.Surface((640, 480))
    presenter = DummyPresenter(width=640, height=480, screen=screen)
    scene_renderer = SceneRenderer(presenter, TextureLibrary())
    zones = {
        depth: build_zone_geometry(
            build_depth_rect(416, 480, depth),
            build_next_depth_rect(build_depth_rect(416, 480, depth)),
            depth=depth,
        )
        for depth in (1, 2)
    }
    near_center = WallTile()
    scene = SimpleNamespace(
        depths=(
            SimpleNamespace(
                depth=1,
                center=near_center,
                left=WallTile(),
                right=WallTile(),
            ),
            SimpleNamespace(
                depth=2,
                center=WallTile(),
                left=WallTile(),
                right=WallTile(),
            ),
        )
    )
    calls = []
    scene_renderer._render_wall_overlay_for_tile = (
        lambda tile, rect, darkness, depth, side=None: calls.append(
            (tile, rect, darkness, depth, side)
        )
    )

    scene_renderer._render_wall_overlays(scene, zones)

    assert len(calls) == 1
    assert calls[0][0] is near_center
    assert calls[0][3:] == (1, None)

    pygame.quit()


def test_rookie_body_sprite_respects_player_quest_gate():
    pygame.init()
    screen = pygame.display.set_mode((640, 480))
    presenter = DummyPresenter(width=640, height=480, screen=screen)
    scene_renderer = SceneRenderer(presenter, TextureLibrary())
    tile = RookieCavePath(read=False)
    rect = pygame.Rect(120, 120, 120, 120)
    calls = []
    scene_renderer._render_floor_sprite = lambda *args, **kwargs: calls.append((args, kwargs))

    scene_renderer.player_char = DummyPlayer()
    scene_renderer.player_char.quest_dict = {"Side": {}, "Main": {}, "Bounty": {}}
    scene_renderer.player_char.special_inventory = {}
    scene_renderer._render_special_tile(tile, rect, darkness=0.0, depth=1)
    assert calls == []

    scene_renderer.player_char.quest_dict["Side"]["Rookie Mistake"] = {"Completed": False}
    scene_renderer._render_special_tile(tile, rect, darkness=0.0, depth=1)
    assert calls and calls[-1][0][0] == "dead_soldier_item"

    pygame.quit()


def test_gathering_tiles_use_resource_specific_projected_floor_textures():
    pygame.init()
    screen = pygame.display.set_mode((640, 480))
    presenter = DummyPresenter(width=640, height=480, screen=screen)
    scene_renderer = SceneRenderer(presenter, TextureLibrary())
    tile = OpenTile()
    tile.gathering_resource = "deathcap_mushroom"
    tile.gathering_available = True
    tile.gathering_harvested = False
    assert scene_renderer.textures.get_floor_key(tile) == "floor_gathering_deathcap_mushroom"

    tile.gathering_resource = "acorn"
    assert scene_renderer.textures.get_floor_key(tile) == "floor_gathering_acorn"

    tile.gathering_harvested = True
    assert scene_renderer.textures.get_floor_key(tile) == "floor"

    pygame.quit()


def test_blood_overlay_keys_and_render_hooks():
    pygame.init()
    screen = pygame.display.set_mode((640, 480))
    presenter = DummyPresenter(width=640, height=480, screen=screen)
    scene_renderer = SceneRenderer(presenter, TextureLibrary())
    keys = []

    def fake_special_texture(key, max_size=None):
        keys.append((key, max_size))
        return pygame.Surface((20, 20), pygame.SRCALPHA)

    scene_renderer.textures.get_special_texture = fake_special_texture
    floor_tile = SimpleNamespace(blood_overlays={"floor", "ceiling"})
    wall_tile = SimpleNamespace(blood_wall_overlay=True, x=1, y=1, z=1)

    scene_renderer._render_surface_blood_overlay(
        floor_tile,
        pygame.Rect(100, 220, 140, 80),
        darkness=0.0,
        depth=1,
        surface="floor",
    )
    scene_renderer._render_surface_blood_overlay(
        floor_tile,
        pygame.Rect(100, 80, 140, 60),
        darkness=0.0,
        depth=1,
        surface="ceiling",
    )
    scene_renderer._render_wall_overlay_for_tile(
        wall_tile,
        pygame.Rect(260, 120, 160, 160),
        darkness=0.0,
        depth=1,
    )

    assert ("blood_floor_overlay", 34) in keys
    assert ("blood_ceiling_overlay", 20) in keys
    assert any(key == "blood_wall_overlay" for key, _size in keys)

    pygame.quit()


def test_texture_library_brightens_funhouse_floor_texture():
    pygame.init()
    base = pygame.Surface((2, 2), pygame.SRCALPHA)
    base.fill((42, 34, 26, 180))

    brightened = TextureLibrary._brighten_funhouse_floor_texture(base)

    assert brightened.get_at((0, 0)).r > base.get_at((0, 0)).r
    assert brightened.get_at((0, 0)).g > base.get_at((0, 0)).g
    assert brightened.get_at((0, 0)).b > base.get_at((0, 0)).b
    assert brightened.get_at((0, 0)).a == base.get_at((0, 0)).a

    pygame.quit()


def test_wall_overlays_are_opt_in(monkeypatch):
    pygame.init()
    screen = pygame.Surface((640, 480))
    presenter = DummyPresenter(width=640, height=480, screen=screen)

    monkeypatch.delenv("DUNGEON_RENDERER_ENABLE_WALL_OVERLAYS", raising=False)
    assert SceneRenderer(presenter, TextureLibrary()).enable_wall_overlays is False

    monkeypatch.setenv("DUNGEON_RENDERER_ENABLE_WALL_OVERLAYS", "1")
    assert SceneRenderer(presenter, TextureLibrary()).enable_wall_overlays is True

    pygame.quit()


def test_dungeon_renderer_enables_wall_overlays_for_gameplay(monkeypatch):
    pygame.init()
    screen = pygame.Surface((640, 480))
    presenter = DummyPresenter(width=640, height=480, screen=screen)

    monkeypatch.delenv("DUNGEON_RENDERER_ENABLE_WALL_OVERLAYS", raising=False)
    renderer = DungeonRenderer(presenter)

    assert renderer.scene_renderer.enable_wall_overlays is True

    pygame.quit()


def test_texture_library_records_missing_asset_fallbacks(tmp_path):
    pygame.init()
    textures = TextureLibrary(tileset_base=tmp_path / "missing_tiles")

    assert textures.get_diagnostics() == {
        "loaded": False,
        "fallback_counts": {},
        "fallback_keys": {},
        "fallback_total": 0,
        "projected_cache": {"size": 0, "limit": 512, "remaining": 512, "full": False},
        "surface_slot_overrides": {
            "manual_count": 0,
            "scene_count": 0,
            "total_count": 0,
            "has_overrides": False,
            "revision": 0,
        },
        "surface_slot_revision": 0,
    }

    wall = textures.get_texture("wall")
    special = textures.get_special_texture("stairs_down", size=24)
    enemy = textures.get_enemy_texture("Missing Enemy", size=24)
    fallbacks = textures.get_asset_fallbacks()
    expected_texture_fallbacks = len(
        [path for path in TEXTURE_PATHS.values() if not path.startswith("__generated__/")]
    )

    assert wall.get_size() == (128, 128)
    assert special is not None
    assert max(special.get_size()) == 24
    assert enemy is not None
    assert fallbacks["texture:wall"].endswith("walls/brick.png")
    assert fallbacks["special:stairs_down"].endswith("special_tiles/stairs_down.png")
    assert fallbacks["enemy:Missing Enemy"].endswith("enemy_combat_sprites/generic_enemy.png")
    assert textures.get_asset_fallback_counts() == {
        "texture": expected_texture_fallbacks,
        "special": 1,
        "enemy": 1,
    }
    fallback_keys = textures.get_asset_fallback_keys_by_category()
    assert fallback_keys["enemy"] == ["Missing Enemy"]
    assert fallback_keys["special"] == ["stairs_down"]
    assert "wall" in fallback_keys["texture"]

    fallbacks.clear()
    assert "texture:wall" in textures.get_asset_fallbacks()
    counts = textures.get_asset_fallback_counts()
    counts["texture"] = 0
    assert textures.get_asset_fallback_counts()["texture"] == expected_texture_fallbacks
    assert textures.get_diagnostics() == {
        "loaded": True,
        "fallback_counts": {
            "texture": expected_texture_fallbacks,
            "special": 1,
            "enemy": 1,
        },
        "fallback_keys": fallback_keys,
        "fallback_total": expected_texture_fallbacks + 2,
        "projected_cache": {"size": 0, "limit": 512, "remaining": 512, "full": False},
        "surface_slot_overrides": {
            "manual_count": 0,
            "scene_count": 0,
            "total_count": 0,
            "has_overrides": False,
            "revision": 0,
        },
        "surface_slot_revision": 0,
    }

    pygame.quit()


def test_texture_library_limits_projected_surface_cache():
    pygame.init()
    pygame.display.set_mode((1, 1))
    textures = TextureLibrary(projected_cache_limit=2)
    quad = Quad(((0.0, 0.0), (64.0, 0.0), (64.0, 64.0), (0.0, 64.0)))

    assert textures.get_projected_cache_stats() == {
        "size": 0,
        "limit": 2,
        "remaining": 2,
        "full": False,
    }

    for width in (128, 129, 130):
        textures.get_projected_surface(
            panel_id="d1:center_floor",
            texture_key="floor",
            quad=quad,
            darkness=0.0,
            view_size=(width, 128),
        )

    assert len(textures._projected_cache) == 2
    assert textures.get_projected_cache_stats() == {
        "size": 2,
        "limit": 2,
        "remaining": 0,
        "full": True,
    }
    assert textures.get_diagnostics()["projected_cache"] == {
        "size": 2,
        "limit": 2,
        "remaining": 0,
        "full": True,
    }
    assert all(cache_key[0] != (128, 128) for cache_key in textures._projected_cache)

    pygame.quit()


def test_texture_library_describes_floor_slot_ids():
    textures = TextureLibrary()

    assert textures.describe_floor_slot_ids("d2:center_floor") == (
        "floor:visible:d2:xm2",
        "floor:visible:d2:xm1",
        "floor:visible:d2:x0",
        "floor:visible:d2:xp1",
        "floor:visible:d2:xp2",
    )
    assert textures.describe_floor_slot_ids("d3:center_floor") == (
        "floor:visible:d3:xm4",
        "floor:visible:d3:xm3",
        "floor:visible:d3:xm2",
        "floor:visible:d3:xm1",
        "floor:visible:d3:x0",
        "floor:visible:d3:xp1",
        "floor:visible:d3:xp2",
        "floor:visible:d3:xp3",
        "floor:visible:d3:xp4",
    )
    assert textures.describe_floor_slot_ids("d2:right_corridor_outer_floor") == (
        "floor:corridor_outer:right:d2:tile",
    )
    assert textures.describe_floor_slot_ids("d2:left_corridor_outer_floor") == (
        "floor:corridor_outer:left:d2:tile",
    )
    assert textures.describe_floor_slot_ids("d3:right_corridor_outer_floor") == (
        "floor:corridor_outer:right:d3:tile",
    )
    assert textures.describe_floor_slot_ids("d3:left_corridor_outer_floor") == (
        "floor:corridor_outer:left:d3:tile",
    )


def test_texture_library_describes_depth3_center_slot_spans():
    textures = TextureLibrary()

    assert textures.describe_surface_slot_spans("d3:center_floor", texture_key="floor") == (
        (-1.0 / 7.0, 0.0),
        (0.0, 1.0 / 7.0),
        (1.0 / 7.0, 2.0 / 7.0),
        (2.0 / 7.0, 3.0 / 7.0),
        (3.0 / 7.0, 4.0 / 7.0),
        (4.0 / 7.0, 5.0 / 7.0),
        (5.0 / 7.0, 6.0 / 7.0),
        (6.0 / 7.0, 1.0),
        (1.0, 8.0 / 7.0),
    )
    assert textures.describe_surface_slot_spans("d3:center_ceiling", texture_key="ceiling") == (
        (-1.0 / 7.0, 0.0),
        (0.0, 1.0 / 7.0),
        (1.0 / 7.0, 2.0 / 7.0),
        (2.0 / 7.0, 3.0 / 7.0),
        (3.0 / 7.0, 4.0 / 7.0),
        (4.0 / 7.0, 5.0 / 7.0),
        (5.0 / 7.0, 6.0 / 7.0),
        (6.0 / 7.0, 1.0),
        (1.0, 8.0 / 7.0),
    )


def test_scene_renderer_preserves_overscan_for_depth3_slot_slices():
    quad = Quad(
        (
            (-249.0, 288.0),
            (913.0, 288.0),
            (581.0, 336.0),
            (83.0, 336.0),
        )
    )

    left_slot = SceneRenderer._slice_quad_horizontal_region(quad, -1.0 / 7.0, 0.0)
    right_slot = SceneRenderer._slice_quad_horizontal_region(quad, 1.0, 8.0 / 7.0)

    assert left_slot.points[0][0] < quad.points[0][0]
    assert left_slot.points[3][0] < quad.points[3][0]
    assert right_slot.points[1][0] > quad.points[1][0]
    assert right_slot.points[2][0] > quad.points[2][0]


def test_texture_library_describes_ceiling_and_wall_slot_ids():
    textures = TextureLibrary()

    assert textures.describe_ceiling_slot_ids("d2:center_ceiling") == (
        "ceiling:visible:d2:xm2",
        "ceiling:visible:d2:xm1",
        "ceiling:visible:d2:x0",
        "ceiling:visible:d2:xp1",
        "ceiling:visible:d2:xp2",
    )
    assert textures.describe_ceiling_slot_ids("d3:center_ceiling") == (
        "ceiling:visible:d3:xm4",
        "ceiling:visible:d3:xm3",
        "ceiling:visible:d3:xm2",
        "ceiling:visible:d3:xm1",
        "ceiling:visible:d3:x0",
        "ceiling:visible:d3:xp1",
        "ceiling:visible:d3:xp2",
        "ceiling:visible:d3:xp3",
        "ceiling:visible:d3:xp4",
    )
    assert textures.describe_ceiling_slot_ids("d2:right_corridor_outer_ceiling") == (
        "ceiling:corridor_outer:right:d2:tile",
    )
    assert textures.describe_ceiling_slot_ids("d2:left_corridor_outer_ceiling") == (
        "ceiling:corridor_outer:left:d2:tile",
    )
    assert textures.describe_ceiling_slot_ids("d3:right_corridor_outer_ceiling") == (
        "ceiling:corridor_outer:right:d3:tile",
    )
    assert textures.describe_ceiling_slot_ids("d3:left_corridor_outer_ceiling") == (
        "ceiling:corridor_outer:left:d3:tile",
    )
    assert textures.describe_wall_slot_ids("d1:back_wall") == ("wall:visible:d1:center",)
    assert textures.describe_wall_slot_ids("d1:right_wall") == (
        "wall:visible:d1:right:right:near",
        "wall:visible:d1:right:right:far",
    )
    assert textures.describe_wall_slot_ids("d2:right_corridor_outer_wall") == (
        "wall:visible:d2:corridor_outer:right:near",
        "wall:visible:d2:corridor_outer:right:far",
    )
    assert textures.describe_wall_slot_ids("d2:left_corridor_outer_wall") == (
        "wall:visible:d2:corridor_outer:left:near",
        "wall:visible:d2:corridor_outer:left:far",
    )


def test_texture_library_loads_migrated_special_and_enemy_sprites():
    pygame.init()
    textures = TextureLibrary()

    for key in (
        "portal",
        "boulder",
        "boulder_sword",
        "dead_body",
        "burial_site",
        "empty_altar",
        "luna_altar",
        "golden_chalice_altar",
        "secret_shop",
        "unobtainium",
        "rotator",
    ):
        assert textures.get_special_texture(key) is not None

    assert "special:rotator" not in textures.get_asset_fallbacks()
    assert textures.get_enemy_texture("Minotaur") is not None

    pygame.quit()


def test_texture_library_can_override_individual_floor_slots():
    pygame.init()
    textures = TextureLibrary()

    assert textures.has_any_surface_slot_overrides() is False

    baseline = textures.get_panel_texture("d2:right_corridor_outer_floor", "floor")
    textures.set_floor_slot_override("floor:corridor_outer:right:d2:tile", "floor_pit")
    assert textures.has_any_surface_slot_overrides() is True
    overridden = textures.get_panel_texture("d2:right_corridor_outer_floor", "floor")

    assert overridden.get_size() == baseline.get_size()
    assert pygame.image.tostring(overridden, "RGBA") != pygame.image.tostring(baseline, "RGBA")

    textures.clear_floor_slot_overrides()
    assert textures.has_any_surface_slot_overrides() is False
    restored = textures.get_panel_texture("d2:right_corridor_outer_floor", "floor")
    assert restored.get_size() == baseline.get_size()

    pygame.quit()


def test_texture_library_can_override_individual_ceiling_and_wall_slots():
    pygame.init()
    textures = TextureLibrary()

    baseline_ceiling = textures.get_panel_texture("d2:center_ceiling", "ceiling")
    textures.set_ceiling_slot_override("ceiling:visible:d2:xp1", "ceiling_pit")
    overridden_ceiling = textures.get_panel_texture("d2:center_ceiling", "ceiling")
    assert pygame.image.tostring(overridden_ceiling, "RGBA") != pygame.image.tostring(
        baseline_ceiling, "RGBA"
    )

    textures.clear_surface_slot_overrides()

    baseline_wall = textures.get_panel_texture("d1:right_wall", "wall")
    textures.set_wall_slot_override("wall:visible:d1:right:right:near", "floor_funhouse")
    overridden_wall = textures.get_panel_texture("d1:right_wall", "wall")
    assert pygame.image.tostring(overridden_wall, "RGBA") != pygame.image.tostring(
        baseline_wall, "RGBA"
    )

    textures.clear_surface_slot_overrides()
    pygame.quit()


def test_texture_library_reports_scene_surface_slot_overrides():
    textures = TextureLibrary()
    assert textures.has_any_surface_slot_overrides() is False
    assert textures.get_surface_slot_override_diagnostics() == {
        "manual_count": 0,
        "scene_count": 0,
        "total_count": 0,
        "has_overrides": False,
        "revision": 0,
    }

    textures.set_scene_surface_slot_overrides({"wall:visible:d1:center": "door_closed"})
    assert textures.has_any_surface_slot_overrides() is True
    assert textures.get_surface_slot_overrides() == {"wall:visible:d1:center": "door_closed"}
    assert textures.get_surface_slot_override_diagnostics() == {
        "manual_count": 0,
        "scene_count": 1,
        "total_count": 1,
        "has_overrides": True,
        "revision": 1,
    }

    textures.set_wall_slot_override("wall:visible:d1:center", "door_open")
    assert textures.get_surface_slot_override_diagnostics() == {
        "manual_count": 1,
        "scene_count": 1,
        "total_count": 1,
        "has_overrides": True,
        "revision": 2,
    }
    assert textures.get_diagnostics()["surface_slot_overrides"]["manual_count"] == 1

    textures.clear_scene_surface_slot_overrides()
    assert textures.get_surface_slot_override_diagnostics() == {
        "manual_count": 1,
        "scene_count": 0,
        "total_count": 1,
        "has_overrides": True,
        "revision": 3,
    }
    textures.clear_surface_slot_overrides()
    assert textures.has_any_surface_slot_overrides() is False


def test_texture_library_describes_panel_surface_slot_overrides():
    textures = TextureLibrary()
    textures.set_scene_surface_slot_overrides(
        {
            "floor:corridor_outer:right:d2:tile": "floor_pit",
            "ceiling:visible:d2:x0": "ceiling_pit",
            "wall:visible:d1:center": "door_closed",
        }
    )
    textures.set_wall_slot_override("wall:visible:d1:center", "door_open")

    assert textures.describe_panel_surface_slot_overrides(
        "d2:right_corridor_outer_floor",
        "floor",
    ) == {"floor:corridor_outer:right:d2:tile": "floor_pit"}
    assert textures.describe_panel_surface_slot_overrides("d2:center_ceiling", "ceiling") == {
        "ceiling:visible:d2:x0": "ceiling_pit",
    }
    assert textures.describe_panel_surface_slot_overrides("d1:back_wall", "wall") == {
        "wall:visible:d1:center": "door_open",
    }
    assert textures.describe_panel_surface_slot_overrides("unknown_panel", "floor") == {}

    textures.clear_scene_surface_slot_overrides()
    assert textures.describe_panel_surface_slot_overrides("d2:center_ceiling", "ceiling") == {}


def test_texture_library_describes_panel_surface_slot_state():
    textures = TextureLibrary()
    textures.set_scene_surface_slot_overrides(
        {
            "floor:visible:d2:x0": "floor_pit",
            "floor:visible:d2:xp1": "floor_pit",
        }
    )
    textures.set_floor_slot_override("floor:visible:d2:xp1", "floor_fire")

    state = textures.describe_panel_surface_slot_state("d2:center_floor", "floor")

    assert state[2] == {
        "slot_id": "floor:visible:d2:x0",
        "default_texture_key": "floor",
        "texture_key": "floor_pit",
        "overridden": True,
        "override_source": "scene",
    }
    assert state[3] == {
        "slot_id": "floor:visible:d2:xp1",
        "default_texture_key": "floor",
        "texture_key": "floor_fire",
        "overridden": True,
        "override_source": "manual",
    }
    assert state[0]["texture_key"] == "floor"
    assert state[0]["overridden"] is False
    assert state[0]["override_source"] == "none"
    assert textures.describe_panel_surface_slot_state("unknown_panel", "floor") == ()


def test_texture_library_summarizes_panel_surface_slot_state_sources():
    textures = TextureLibrary()
    textures.set_scene_surface_slot_overrides(
        {
            "floor:corridor_outer:right:d2:tile": "floor_pit",
            "floor:corridor_outer:left:d2:tile": "floor_pit",
        }
    )
    textures.set_floor_slot_override("floor:corridor_outer:right:d2:tile", "floor_fire")

    assert textures.summarize_panel_surface_slot_state(
        "d2:right_corridor_outer_floor",
        "floor",
    ) == {
        "panel_id": "d2:right_corridor_outer_floor",
        "texture_key": "floor",
        "slot_count": 1,
        "overridden_count": 1,
        "default_count": 0,
        "scene_override_count": 0,
        "manual_override_count": 1,
        "has_overrides": True,
    }
    assert (
        textures.summarize_panel_surface_slot_state(
            "d2:left_corridor_outer_floor",
            "floor",
        )["scene_override_count"]
        == 1
    )
    assert textures.summarize_panel_surface_slot_state("unknown_panel", "floor") == {
        "panel_id": "unknown_panel",
        "texture_key": "floor",
        "slot_count": 0,
        "overridden_count": 0,
        "default_count": 0,
        "scene_override_count": 0,
        "manual_override_count": 0,
        "has_overrides": False,
    }


def test_texture_library_ignores_invalid_surface_slot_overrides():
    pygame.init()
    textures = TextureLibrary()
    baseline_floor = textures.get_panel_texture("d2:right_corridor_outer_floor", "floor")
    baseline_ceiling = textures.get_panel_texture("d2:center_ceiling", "ceiling")
    baseline_wall = textures.get_panel_texture("d1:right_wall", "wall")

    textures.set_surface_slot_overrides(
        {
            "floor:corridor_outer:right:d2:tile": "floor_pit",
            "ceiling:visible:d2:xp1": "missing_texture",
            "wall:visible:d1:right:right:near": "floor_funhouse",
            "enemy:visible:d1:center": "wall",
        }
    )
    overrides = textures.get_surface_slot_overrides()

    assert overrides == {
        "floor:corridor_outer:right:d2:tile": "floor_pit",
        "wall:visible:d1:right:right:near": "floor_funhouse",
    }
    assert textures.has_floor_slot_override("d2:right_corridor_outer_floor") is True
    assert textures.has_ceiling_slot_override("d2:center_ceiling") is False
    assert textures.has_wall_slot_override("d1:right_wall") is True
    assert pygame.image.tostring(
        textures.get_panel_texture("d2:right_corridor_outer_floor", "floor"),
        "RGBA",
    ) != pygame.image.tostring(baseline_floor, "RGBA")
    assert pygame.image.tostring(
        textures.get_panel_texture("d2:center_ceiling", "ceiling"),
        "RGBA",
    ) == pygame.image.tostring(baseline_ceiling, "RGBA")
    assert pygame.image.tostring(
        textures.get_panel_texture("d1:right_wall", "wall"),
        "RGBA",
    ) != pygame.image.tostring(baseline_wall, "RGBA")

    textures.clear_surface_slot_overrides()
    textures.set_scene_surface_slot_overrides(
        {
            "wall:visible:d1:center": "not_a_texture",
            "ceiling:visible:d2:x0": "ceiling_pit",
        }
    )

    assert textures.get_surface_slot_overrides() == {"ceiling:visible:d2:x0": "ceiling_pit"}

    pygame.quit()


def test_scene_renderer_can_disable_darkness_via_env():
    pygame.init()
    screen = pygame.display.set_mode((640, 480))
    presenter = DummyPresenter(width=640, height=480, screen=screen)
    player = DummyPlayer()
    world = {(0, 0, 1): OpenTile()}
    previous = os.environ.get("DUNGEON_RENDERER_DISABLE_DARKNESS")
    os.environ["DUNGEON_RENDERER_DISABLE_DARKNESS"] = "1"

    try:
        scene_renderer = SceneRenderer(presenter, TextureLibrary())
        commands, _ = _build_scene_commands(scene_renderer, player, world)

        assert scene_renderer._get_layer_darkness(1) == 0.0
        assert scene_renderer._get_layer_darkness(2) == 0.0
        assert scene_renderer._get_layer_darkness(3) == 0.0
        assert all(command.darkness == 0.0 for command in commands)
    finally:
        if previous is None:
            os.environ.pop("DUNGEON_RENDERER_DISABLE_DARKNESS", None)
        else:
            os.environ["DUNGEON_RENDERER_DISABLE_DARKNESS"] = previous

    pygame.quit()


def test_scene_renderer_adds_endcaps_for_center_wall_with_blocked_side_corridors():
    pygame.init()
    screen = pygame.display.set_mode((640, 480))
    presenter = DummyPresenter(width=640, height=480, screen=screen)
    scene_renderer = SceneRenderer(presenter, TextureLibrary())
    player = DummyPlayer()
    world = {
        (0, 0, 1): OpenTile(),
        (1, 0, 1): OpenTile(),
        (1, -1, 1): OpenTile(),
        (1, 1, 1): OpenTile(),
        (2, 0, 1): WallTile(),
        (2, -1, 1): WallTile(),
        (2, 1, 1): WallTile(),
        (2, -2, 1): WallTile(),
        (2, 2, 1): WallTile(),
    }

    commands, _ = _build_scene_commands(scene_renderer, player, world)

    assert any(command.panel_id == "d2:left_back_wall_endcap" for command in commands)
    assert any(command.panel_id == "d2:right_back_wall_endcap" for command in commands)

    pygame.quit()


def test_scene_renderer_adds_endcap_for_open_center_side_blocker_with_outer_wall():
    pygame.init()
    screen = pygame.display.set_mode((640, 480))
    presenter = DummyPresenter(width=640, height=480, screen=screen)
    scene_renderer = SceneRenderer(presenter, TextureLibrary())
    player = DummyPlayer()
    world = {
        (0, 0, 1): OpenTile(),
        (1, 0, 1): OpenTile(),
        (2, 0, 1): OpenTile(),
        (0, -1, 1): WallTile(),
        (1, -1, 1): WallTile(),
        (2, -1, 1): WallTile(),
        (0, 1, 1): OpenTile(),
        (1, 1, 1): OpenTile(),
        (2, 1, 1): WallTile(),
        (2, 2, 1): WallTile(),
    }

    commands, _ = _build_scene_commands(scene_renderer, player, world)

    assert any(command.panel_id == "d2:right_blocker" for command in commands)
    assert any(command.panel_id == "d2:right_back_wall_endcap" for command in commands)

    pygame.quit()


def test_scene_renderer_renders_side_corridor_outer_wall_in_side_wall_layer():
    pygame.init()
    screen = pygame.display.set_mode((640, 480))
    presenter = DummyPresenter(width=640, height=480, screen=screen)
    scene_renderer = SceneRenderer(presenter, TextureLibrary())
    player = DummyPlayer()
    world = {
        (0, 0, 1): OpenTile(),
        (1, 0, 1): WallTile(),
        (0, 1, 1): OpenTile(),
        (1, 1, 1): OpenTile(),
        (1, 2, 1): WallTile(),
    }

    commands, _ = _build_scene_commands(scene_renderer, player, world)

    corridor_wall = next(
        command for command in commands if command.panel_id == "d2:right_corridor_outer_wall"
    )
    assert corridor_wall.order == 3

    pygame.quit()


def test_scene_renderer_preserves_side_opening_depth_after_center_wall():
    pygame.init()
    screen = pygame.display.set_mode((640, 480))
    presenter = DummyPresenter(width=640, height=480, screen=screen)
    scene_renderer = SceneRenderer(presenter, TextureLibrary())
    player = DummyPlayer()
    world = {
        (0, 0, 1): OpenTile(),
        (1, 0, 1): WallTile(),
        (2, 0, 1): OpenTile(),
        (3, 0, 1): OpenTile(),
        (0, 1, 1): OpenTile(),
        (1, 1, 1): OpenTile(),
        (1, 2, 1): WallTile(),
    }

    commands, _ = _build_scene_commands(scene_renderer, player, world)
    panel_ids = {command.panel_id for command in commands}

    assert "d1:back_wall" in panel_ids
    assert "d2:right_corridor_outer_wall" in panel_ids
    assert any(panel_id.startswith("d2:center_floor") for panel_id in panel_ids)
    assert any(panel_id.startswith("d2:center_ceiling") for panel_id in panel_ids)

    pygame.quit()


def test_scene_renderer_keeps_left_depth3_outer_corridor_wall_continuation():
    pygame.init()
    screen = pygame.display.set_mode((640, 480))
    presenter = DummyPresenter(width=640, height=480, screen=screen)
    scene_renderer = SceneRenderer(presenter, TextureLibrary())
    player = DummyPlayer()
    world = {
        (0, 0, 1): OpenTile(),
        (1, 0, 1): OpenTile(),
        (2, 0, 1): OpenTile(),
        (0, -1, 1): OpenTile(),
        (1, -1, 1): OpenTile(),
        (2, -1, 1): OpenTile(),
        (1, -2, 1): WallTile(),
        (2, -2, 1): WallTile(),
        (0, 1, 1): WallTile(),
    }

    commands, _ = _build_scene_commands(scene_renderer, player, world)

    assert any(command.panel_id == "d2:left_corridor_outer_wall" for command in commands)
    depth3_wall = next(
        command for command in commands if command.panel_id == "d3:left_corridor_outer_wall"
    )
    assert depth3_wall.texture_key == "wall"
    assert depth3_wall.order == 3
    assert not any(command.panel_id == "d3:right_corridor_outer_wall" for command in commands)

    pygame.quit()


def test_scene_renderer_keeps_outer_side_corridor_door_state_on_outer_wall():
    pygame.init()
    screen = pygame.display.set_mode((640, 480))
    presenter = DummyPresenter(width=640, height=480, screen=screen)
    scene_renderer = SceneRenderer(presenter, TextureLibrary())
    player = DummyPlayer()
    world = {
        (0, 0, 1): OpenTile(),
        (1, 0, 1): OpenTile(),
        (0, 1, 1): OpenTile(),
        (1, 1, 1): OpenTile(),
        (1, 2, 1): LockedDoor(),
    }

    calls = []
    original_get_projected_surface = scene_renderer.textures.get_projected_surface

    def recording_get_projected_surface(panel_id, texture_key, quad, darkness, view_size):
        calls.append((panel_id, texture_key))
        return original_get_projected_surface(panel_id, texture_key, quad, darkness, view_size)

    scene_renderer.textures.get_projected_surface = recording_get_projected_surface

    scene_renderer.render(player, world)

    assert ("d2:right_corridor_outer_wall", "door_closed") in calls
    assert ("d2:right_corridor_outer_wall", "wall") not in calls

    pygame.quit()


def test_scene_renderer_keeps_outer_side_corridor_open_door_state_on_outer_wall():
    pygame.init()
    screen = pygame.display.set_mode((640, 480))
    presenter = DummyPresenter(width=640, height=480, screen=screen)
    scene_renderer = SceneRenderer(presenter, TextureLibrary())
    player = DummyPlayer()
    world = {
        (0, 0, 1): OpenTile(),
        (1, 0, 1): OpenTile(),
        (0, 1, 1): OpenTile(),
        (1, 1, 1): OpenTile(),
        (1, 2, 1): OpenDoor(),
    }

    calls = []
    original_get_projected_surface = scene_renderer.textures.get_projected_surface

    def recording_get_projected_surface(panel_id, texture_key, quad, darkness, view_size):
        calls.append((panel_id, texture_key))
        return original_get_projected_surface(panel_id, texture_key, quad, darkness, view_size)

    scene_renderer.textures.get_projected_surface = recording_get_projected_surface

    scene_renderer.render(player, world)

    assert ("d2:right_corridor_outer_wall", "door_open") in calls
    assert ("d2:right_corridor_outer_wall", "wall") not in calls

    pygame.quit()


def test_scene_renderer_keeps_left_outer_side_corridor_door_states_on_outer_wall():
    pygame.init()
    screen = pygame.display.set_mode((640, 480))
    presenter = DummyPresenter(width=640, height=480, screen=screen)
    scene_renderer = SceneRenderer(presenter, TextureLibrary())
    player = DummyPlayer()
    world = {
        (0, 0, 1): OpenTile(),
        (1, 0, 1): OpenTile(),
        (0, -1, 1): OpenTile(),
        (1, -1, 1): OpenTile(),
        (1, -2, 1): LockedDoor(),
        (0, 1, 1): OpenTile(),
        (1, 1, 1): OpenTile(),
    }

    calls = []
    original_get_projected_surface = scene_renderer.textures.get_projected_surface

    def recording_get_projected_surface(panel_id, texture_key, quad, darkness, view_size):
        calls.append((panel_id, texture_key))
        return original_get_projected_surface(panel_id, texture_key, quad, darkness, view_size)

    scene_renderer.textures.get_projected_surface = recording_get_projected_surface
    scene_renderer.render(player, world)

    assert ("d2:left_corridor_outer_wall", "door_closed") in calls
    assert ("d2:left_corridor_outer_wall", "wall") not in calls

    calls.clear()
    world[(1, -2, 1)] = OpenDoor()
    scene_renderer.render(player, world)

    assert ("d2:left_corridor_outer_wall", "door_open") in calls
    assert ("d2:left_corridor_outer_wall", "wall") not in calls

    pygame.quit()


def test_scene_renderer_adds_three_depth3_endcaps_per_side_for_full_back_wall():
    pygame.init()
    screen = pygame.display.set_mode((640, 480))
    presenter = DummyPresenter(width=640, height=480, screen=screen)
    scene_renderer = SceneRenderer(presenter, TextureLibrary())
    player = DummyPlayer()
    world = {
        (0, 0, 1): OpenTile(),
        (1, 0, 1): OpenTile(),
        (2, 0, 1): OpenTile(),
        (2, -1, 1): OpenTile(),
        (2, 1, 1): OpenTile(),
        (3, 0, 1): WallTile(),
        (3, -1, 1): WallTile(),
        (3, 1, 1): WallTile(),
        (2, -2, 1): WallTile(),
        (2, 2, 1): WallTile(),
        (3, -2, 1): WallTile(),
        (3, 2, 1): WallTile(),
    }

    commands, _ = _build_scene_commands(scene_renderer, player, world)

    assert any(command.panel_id == "d3:left_back_wall_endcap" for command in commands)
    assert any(command.panel_id == "d3:left_back_wall_endcap1" for command in commands)
    assert any(command.panel_id == "d3:left_back_wall_endcap2" for command in commands)
    assert any(command.panel_id == "d3:right_back_wall_endcap" for command in commands)
    assert any(command.panel_id == "d3:right_back_wall_endcap1" for command in commands)
    assert any(command.panel_id == "d3:right_back_wall_endcap2" for command in commands)

    pygame.quit()


def test_scene_renderer_skips_special_tiles_hidden_behind_center_wall():
    pygame.init()
    screen = pygame.display.set_mode((640, 480))
    presenter = DummyPresenter(width=640, height=480, screen=screen)
    scene_renderer = SceneRenderer(presenter, TextureLibrary())
    player = DummyPlayer()
    world = {
        (0, 0, 1): OpenTile(),
        (1, 0, 1): WallTile(),
        (2, 0, 1): ChestRoom(),
        (0, -1, 1): OpenTile(),
        (0, 1, 1): OpenTile(),
        (1, -1, 1): OpenTile(),
        (1, 1, 1): OpenTile(),
        (2, -1, 1): OpenTile(),
        (2, 1, 1): OpenTile(),
    }

    rendered_tiles = []
    original_render_special_tile = scene_renderer._render_special_tile

    def recording_render_special_tile(tile, rect, darkness, depth, side=None, lateral_view=False):
        rendered_tiles.append((type(tile).__name__ if tile else None, depth, side, lateral_view))
        return original_render_special_tile(
            tile,
            rect,
            darkness,
            depth,
            side=side,
            lateral_view=lateral_view,
        )

    scene_renderer._render_special_tile = recording_render_special_tile

    scene_renderer.render(player, world)

    assert ("WallTile", 1, None, False) in rendered_tiles
    assert ("ChestRoom", 2, None, False) not in rendered_tiles

    pygame.quit()


def test_scene_renderer_renders_side_special_tiles_in_opening():
    pygame.init()
    screen = pygame.display.set_mode((640, 480))
    presenter = DummyPresenter(width=640, height=480, screen=screen)
    scene_renderer = SceneRenderer(presenter, TextureLibrary())
    player = DummyPlayer()
    world = {
        (0, 0, 1): OpenTile(),
        (1, 0, 1): WallTile(),
        (0, -1, 1): OpenTile(),
        (1, -1, 1): ChestRoom(),
        (0, 1, 1): OpenTile(),
        (1, 1, 1): OpenTile(),
    }

    rendered_tiles = []
    original_render_special_tile = scene_renderer._render_special_tile

    def recording_render_special_tile(tile, rect, darkness, depth, side=None, lateral_view=False):
        rendered_tiles.append((type(tile).__name__ if tile else None, depth, side, lateral_view))
        return original_render_special_tile(
            tile,
            rect,
            darkness,
            depth,
            side=side,
            lateral_view=lateral_view,
        )

    scene_renderer._render_special_tile = recording_render_special_tile

    scene_renderer.render(player, world)

    assert ("ChestRoom", 2, "left", True) in rendered_tiles

    pygame.quit()


def test_scene_renderer_renders_decorative_props_in_side_opening():
    pygame.init()
    screen = pygame.display.set_mode((640, 480))
    presenter = DummyPresenter(width=640, height=480, screen=screen)
    scene_renderer = SceneRenderer(presenter, TextureLibrary())
    player = DummyPlayer()
    world = {
        (0, 0, 1): OpenTile(),
        (1, 0, 1): WallTile(),
        (0, -1, 1): OpenTile(),
        (1, -1, 1): CrystalClusterTile(),
        (0, 1, 1): OpenTile(),
        (1, 1, 1): OpenTile(),
    }

    rendered_tiles = []
    original_render_special_tile = scene_renderer._render_special_tile

    def recording_render_special_tile(tile, rect, darkness, depth, side=None, lateral_view=False):
        rendered_tiles.append((type(tile).__name__ if tile else None, depth, side, lateral_view))
        return original_render_special_tile(
            tile,
            rect,
            darkness,
            depth,
            side=side,
            lateral_view=lateral_view,
        )

    scene_renderer._render_special_tile = recording_render_special_tile

    scene_renderer.render(player, world)

    assert ("CrystalClusterTile", 2, "left", True) in rendered_tiles

    pygame.quit()


def test_scene_renderer_advances_side_floor_sprite_depth_when_next_zone_is_visible():
    pygame.init()
    screen = pygame.display.set_mode((640, 480))
    presenter = DummyPresenter(width=640, height=480, screen=screen)
    scene_renderer = SceneRenderer(presenter, TextureLibrary())
    player = DummyPlayer()
    world = {
        (0, 0, 1): OpenTile(),
        (1, 0, 1): WallTile(),
        (0, -1, 1): OpenTile(),
        (1, -1, 1): ChestRoom(),
        (0, 1, 1): OpenTile(),
        (1, 1, 1): OpenTile(),
        (2, 0, 1): OpenTile(),
        (2, -1, 1): OpenTile(),
        (2, 1, 1): OpenTile(),
    }

    rendered_tiles = []
    original_render_special_tile = scene_renderer._render_special_tile

    def recording_render_special_tile(tile, rect, darkness, depth, side=None, lateral_view=False):
        rendered_tiles.append((type(tile).__name__ if tile else None, depth, side, lateral_view))
        return original_render_special_tile(
            tile,
            rect,
            darkness,
            depth,
            side=side,
            lateral_view=lateral_view,
        )

    scene_renderer._render_special_tile = recording_render_special_tile

    scene_renderer.render(player, world)

    assert ("ChestRoom", 2, "left", True) in rendered_tiles

    pygame.quit()


def test_scene_renderer_renders_side_door_in_opening():
    pygame.init()
    screen = pygame.display.set_mode((640, 480))
    presenter = DummyPresenter(width=640, height=480, screen=screen)
    scene_renderer = SceneRenderer(presenter, TextureLibrary())
    player = DummyPlayer()
    world = {
        (0, 0, 1): OpenTile(),
        (1, 0, 1): WallTile(),
        (0, -1, 1): OpenTile(),
        (1, -1, 1): LockedDoor(),
        (0, 1, 1): OpenTile(),
        (1, 1, 1): OpenTile(),
    }

    calls = []
    original_get_projected_surface = scene_renderer.textures.get_projected_surface

    def recording_get_projected_surface(panel_id, texture_key, quad, darkness, view_size):
        calls.append((panel_id, texture_key))
        return original_get_projected_surface(panel_id, texture_key, quad, darkness, view_size)

    scene_renderer.textures.get_projected_surface = recording_get_projected_surface

    scene_renderer.render(player, world)

    assert ("d1:left_blocker_slot0", "door_closed") in calls
    assert ("d1:left_blocker", "wall") not in calls

    pygame.quit()


def test_scene_renderer_hides_side_doors_behind_center_wall():
    pygame.init()
    screen = pygame.display.set_mode((640, 480))
    presenter = DummyPresenter(width=640, height=480, screen=screen)
    scene_renderer = SceneRenderer(presenter, TextureLibrary())
    player = DummyPlayer()
    world = {
        (0, 0, 1): OpenTile(),
        (1, 0, 1): WallTile(),
        (0, -1, 1): OpenTile(),
        (0, 1, 1): OpenTile(),
        (1, -1, 1): LockedDoor(),
        (1, 1, 1): LockedDoor(),
    }

    calls = []
    original_get_projected_surface = scene_renderer.textures.get_projected_surface

    def recording_get_projected_surface(panel_id, texture_key, quad, darkness, view_size):
        calls.append((panel_id, texture_key))
        return original_get_projected_surface(panel_id, texture_key, quad, darkness, view_size)

    scene_renderer.textures.get_projected_surface = recording_get_projected_surface

    scene_renderer.render(player, world)

    assert ("d1:left_blocker_slot0", "door_closed") not in calls
    assert ("d1:right_blocker_slot0", "door_closed") not in calls

    pygame.quit()


def test_scene_renderer_keeps_single_side_door_and_other_side_special_behind_center_wall():
    pygame.init()
    screen = pygame.display.set_mode((640, 480))
    presenter = DummyPresenter(width=640, height=480, screen=screen)
    scene_renderer = SceneRenderer(presenter, TextureLibrary())
    player = DummyPlayer()
    world = {
        (0, 0, 1): OpenTile(),
        (1, 0, 1): WallTile(),
        (0, -1, 1): OpenTile(),
        (0, 1, 1): OpenTile(),
        (1, -1, 1): LockedDoor(),
        (1, 1, 1): ChestRoom(),
    }

    projected_calls = []
    original_get_projected_surface = scene_renderer.textures.get_projected_surface

    def recording_get_projected_surface(panel_id, texture_key, quad, darkness, view_size):
        projected_calls.append((panel_id, texture_key))
        return original_get_projected_surface(panel_id, texture_key, quad, darkness, view_size)

    rendered_tiles = []
    original_render_special_tile = scene_renderer._render_special_tile

    def recording_render_special_tile(tile, rect, darkness, depth, side=None, lateral_view=False):
        rendered_tiles.append((type(tile).__name__ if tile else None, depth, side, lateral_view))
        return original_render_special_tile(
            tile,
            rect,
            darkness,
            depth,
            side=side,
            lateral_view=lateral_view,
        )

    scene_renderer.textures.get_projected_surface = recording_get_projected_surface
    scene_renderer._render_special_tile = recording_render_special_tile

    scene_renderer.render(player, world)

    assert ("d1:left_blocker_slot0", "door_closed") in projected_calls
    assert ("ChestRoom", 2, "right", True) in rendered_tiles

    pygame.quit()


def test_scene_renderer_hides_only_deeper_side_specials_after_depth2_center_wall():
    pygame.init()
    screen = pygame.display.set_mode((640, 480))
    presenter = DummyPresenter(width=640, height=480, screen=screen)
    scene_renderer = SceneRenderer(presenter, TextureLibrary())
    player = DummyPlayer()
    world = {
        (0, 0, 1): OpenTile(),
        (1, 0, 1): OpenTile(),
        (2, 0, 1): WallTile(),
        (1, -1, 1): OpenTile(),
        (1, 1, 1): OpenTile(),
        (2, -1, 1): LockedDoor(),
        (2, 1, 1): OpenTile(),
        (3, -1, 1): LockedDoor(),
        (3, 1, 1): LockedDoor(),
    }

    calls = []
    original_get_projected_surface = scene_renderer.textures.get_projected_surface

    def recording_get_projected_surface(panel_id, texture_key, quad, darkness, view_size):
        calls.append((panel_id, texture_key))
        return original_get_projected_surface(panel_id, texture_key, quad, darkness, view_size)

    scene_renderer.textures.get_projected_surface = recording_get_projected_surface

    scene_renderer.render(player, world)

    assert ("d2:left_blocker_slot0", "door_closed") in calls
    assert calls.count(("d2:left_blocker_slot0", "door_closed")) == 1
    assert ("d2:right_blocker_slot0", "door_closed") not in calls

    pygame.quit()


def test_scene_renderer_keeps_both_depth2_side_doors_when_center_wall_is_deeper():
    pygame.init()
    screen = pygame.display.set_mode((640, 480))
    presenter = DummyPresenter(width=640, height=480, screen=screen)
    scene_renderer = SceneRenderer(presenter, TextureLibrary())
    player = DummyPlayer()
    world = {
        (0, 0, 1): OpenTile(),
        (1, 0, 1): OpenTile(),
        (2, 0, 1): WallTile(),
        (0, -1, 1): WallTile(),
        (0, 1, 1): WallTile(),
        (1, -1, 1): OpenTile(),
        (1, 1, 1): OpenTile(),
        (2, -1, 1): LockedDoor(),
        (2, 1, 1): LockedDoor(),
    }

    calls = []
    original_get_projected_surface = scene_renderer.textures.get_projected_surface

    def recording_get_projected_surface(panel_id, texture_key, quad, darkness, view_size):
        calls.append((panel_id, texture_key))
        return original_get_projected_surface(panel_id, texture_key, quad, darkness, view_size)

    scene_renderer.textures.get_projected_surface = recording_get_projected_surface

    scene_renderer.render(player, world)

    assert ("d2:left_blocker_slot0", "door_closed") in calls
    assert ("d2:right_blocker_slot0", "door_closed") in calls

    pygame.quit()


def test_scene_renderer_renders_funhouse_wall_with_funhouse_wall_texture():
    pygame.init()
    screen = pygame.display.set_mode((640, 480))
    presenter = DummyPresenter(width=640, height=480, screen=screen)
    scene_renderer = SceneRenderer(presenter, TextureLibrary())
    player = DummyPlayer()
    world = {
        (0, 0, 1): FunhousePath(),
        (1, 0, 1): FunhouseWall(),
        (0, -1, 1): FunhousePath(),
        (0, 1, 1): FunhousePath(),
        (1, -1, 1): FunhousePath(),
        (1, 1, 1): FunhousePath(),
    }

    calls = []
    original_get_projected_surface = scene_renderer.textures.get_projected_surface

    def recording_get_projected_surface(panel_id, texture_key, quad, darkness, view_size):
        calls.append((panel_id, texture_key))
        return original_get_projected_surface(panel_id, texture_key, quad, darkness, view_size)

    scene_renderer.textures.get_projected_surface = recording_get_projected_surface

    scene_renderer.render(player, world)

    assert ("d1:back_wall", "wall_funhouse") in calls

    pygame.quit()


def test_scene_renderer_renders_automatic_funhouse_boundary_wall_with_funhouse_texture():
    pygame.init()
    screen = pygame.display.set_mode((640, 480))
    presenter = DummyPresenter(width=640, height=480, screen=screen)
    scene_renderer = SceneRenderer(presenter, TextureLibrary())
    player = DummyPlayer()
    world = {
        (0, 0, 1): FunhousePath(),
        (1, 0, 1): FunhousePath(),
    }

    calls = []
    original_get_projected_surface = scene_renderer.textures.get_projected_surface

    def recording_get_projected_surface(panel_id, texture_key, quad, darkness, view_size):
        calls.append((panel_id, texture_key))
        return original_get_projected_surface(panel_id, texture_key, quad, darkness, view_size)

    scene_renderer.textures.get_projected_surface = recording_get_projected_surface

    scene_renderer.render(player, world)

    assert ("d1:left_wall", "wall_funhouse_boundary") in calls
    assert ("d1:right_wall", "wall_funhouse_boundary") in calls
    assert ("d2:left_wall", "wall_funhouse_boundary") in calls
    assert ("d2:right_wall", "wall_funhouse_boundary") in calls
    assert ("d3:left_wall", "wall_funhouse_boundary") in calls
    assert ("d3:right_wall", "wall_funhouse_boundary") in calls

    pygame.quit()


def test_scene_renderer_renders_funhouse_boundary_endcaps_without_stone_fallback():
    pygame.init()
    screen = pygame.display.set_mode((640, 480))
    presenter = DummyPresenter(width=640, height=480, screen=screen)
    scene_renderer = SceneRenderer(presenter, TextureLibrary())
    player = DummyPlayer()
    world = {
        (0, 0, 1): FunhousePath(),
        (1, 0, 1): FunhousePath(),
        (0, 1, 1): FunhousePath(),
    }

    calls = []
    original_get_projected_surface = scene_renderer.textures.get_projected_surface

    def recording_get_projected_surface(panel_id, texture_key, quad, darkness, view_size):
        calls.append((panel_id, texture_key))
        return original_get_projected_surface(panel_id, texture_key, quad, darkness, view_size)

    scene_renderer.textures.get_projected_surface = recording_get_projected_surface

    scene_renderer.render(player, world)

    assert ("d1:right_blocker", "wall_funhouse_boundary") in calls
    assert ("d1:right_back_wall_endcap", "wall_funhouse_boundary") in calls
    assert ("d1:right_back_wall_endcap", "wall") not in calls

    pygame.quit()


def test_scene_renderer_does_not_render_current_tile_door():
    pygame.init()
    screen = pygame.display.set_mode((640, 480))
    presenter = DummyPresenter(width=640, height=480, screen=screen)
    scene_renderer = SceneRenderer(presenter, TextureLibrary())
    player = DummyPlayer()
    world = {
        (0, 0, 1): OpenDoor(),
        (1, 0, 1): OpenTile(),
        (2, 0, 1): LockedDoor(),
        (0, -1, 1): OpenTile(),
        (0, 1, 1): OpenTile(),
        (1, -1, 1): OpenTile(),
        (1, 1, 1): OpenTile(),
        (2, -1, 1): OpenTile(),
        (2, 1, 1): OpenTile(),
    }

    calls = []
    original_get_projected_surface = scene_renderer.textures.get_projected_surface

    def recording_get_projected_surface(panel_id, texture_key, quad, darkness, view_size):
        calls.append((panel_id, texture_key))
        return original_get_projected_surface(panel_id, texture_key, quad, darkness, view_size)

    scene_renderer.textures.get_projected_surface = recording_get_projected_surface

    scene_renderer.render(player, world)

    assert ("d2:back_wall_slot0", "door_closed") in calls
    assert ("d1:back_wall_slot0", "door_open") not in calls

    pygame.quit()


def test_scene_renderer_renders_detected_ore_vault_door_as_closed_door():
    pygame.init()
    screen = pygame.display.set_mode((640, 480))
    presenter = DummyPresenter(width=640, height=480, screen=screen)
    scene_renderer = SceneRenderer(presenter, TextureLibrary())
    player = DummyPlayer()
    world = {
        (0, 0, 1): OpenTile(),
        (1, 0, 1): OreVaultDoor(detected=True),
        (0, -1, 1): OpenTile(),
        (0, 1, 1): OpenTile(),
    }

    calls = []
    original_get_projected_surface = scene_renderer.textures.get_projected_surface

    def recording_get_projected_surface(panel_id, texture_key, quad, darkness, view_size):
        calls.append((panel_id, texture_key))
        return original_get_projected_surface(panel_id, texture_key, quad, darkness, view_size)

    scene_renderer.textures.get_projected_surface = recording_get_projected_surface

    scene_renderer.render(player, world)

    assert ("d1:back_wall_slot0", "door_closed") in calls
    assert ("d1:back_wall", "wall") not in calls

    pygame.quit()


def test_scene_renderer_keeps_hidden_ore_vault_door_as_wall():
    pygame.init()
    screen = pygame.display.set_mode((640, 480))
    presenter = DummyPresenter(width=640, height=480, screen=screen)
    scene_renderer = SceneRenderer(presenter, TextureLibrary())
    player = DummyPlayer()
    world = {
        (0, 0, 1): OpenTile(),
        (1, 0, 1): OreVaultDoor(detected=False),
        (0, -1, 1): OpenTile(),
        (0, 1, 1): OpenTile(),
    }

    calls = []
    original_get_projected_surface = scene_renderer.textures.get_projected_surface

    def recording_get_projected_surface(panel_id, texture_key, quad, darkness, view_size):
        calls.append((panel_id, texture_key))
        return original_get_projected_surface(panel_id, texture_key, quad, darkness, view_size)

    scene_renderer.textures.get_projected_surface = recording_get_projected_surface

    scene_renderer.render(player, world)

    assert ("d1:back_wall", "wall") in calls
    assert ("d1:back_wall_slot0", "door_closed") not in calls

    pygame.quit()


def test_scene_renderer_keeps_hidden_fake_wall_as_wall_without_marker():
    pygame.init()
    screen = pygame.display.set_mode((640, 480))
    presenter = DummyPresenter(width=640, height=480, screen=screen)
    scene_renderer = SceneRenderer(presenter, TextureLibrary())
    player = DummyPlayer()
    world = {
        (0, 0, 1): OpenTile(),
        (1, 0, 1): FakeWall(visited=False),
        (0, -1, 1): OpenTile(),
        (0, 1, 1): OpenTile(),
    }

    projected_calls = []
    special_calls = []
    original_get_projected_surface = scene_renderer.textures.get_projected_surface
    original_get_special_texture = scene_renderer.textures.get_special_texture

    def recording_get_projected_surface(panel_id, texture_key, quad, darkness, view_size):
        projected_calls.append((panel_id, texture_key))
        return original_get_projected_surface(panel_id, texture_key, quad, darkness, view_size)

    def recording_get_special_texture(texture_key, size=None):
        special_calls.append((texture_key, size))
        return original_get_special_texture(texture_key, size)

    scene_renderer.textures.get_projected_surface = recording_get_projected_surface
    scene_renderer.textures.get_special_texture = recording_get_special_texture

    scene_renderer.render(player, world)

    assert ("d1:back_wall", "wall") in projected_calls
    assert special_calls == []

    pygame.quit()


def test_scene_renderer_keeps_hidden_fake_wall_subclass_as_wall_without_marker():
    pygame.init()
    screen = pygame.display.set_mode((640, 480))
    presenter = DummyPresenter(width=640, height=480, screen=screen)
    scene_renderer = SceneRenderer(presenter, TextureLibrary())
    player = DummyPlayer()
    world = {
        (0, 0, 1): OpenTile(),
        (1, 0, 1): ThievesGuildTrialFakeWall(visited=False),
        (0, -1, 1): OpenTile(),
        (0, 1, 1): OpenTile(),
    }

    projected_calls = []
    special_calls = []
    original_get_projected_surface = scene_renderer.textures.get_projected_surface
    original_get_special_texture = scene_renderer.textures.get_special_texture

    def recording_get_projected_surface(panel_id, texture_key, quad, darkness, view_size):
        projected_calls.append((panel_id, texture_key))
        return original_get_projected_surface(panel_id, texture_key, quad, darkness, view_size)

    def recording_get_special_texture(texture_key, size=None):
        special_calls.append((texture_key, size))
        return original_get_special_texture(texture_key, size)

    scene_renderer.textures.get_projected_surface = recording_get_projected_surface
    scene_renderer.textures.get_special_texture = recording_get_special_texture

    scene_renderer.render(player, world)

    assert ("d1:back_wall", "wall") in projected_calls
    assert special_calls == []

    pygame.quit()


def test_scene_renderer_marks_revealed_fake_wall_as_translucent_wall_panel():
    pygame.init()
    screen = pygame.display.set_mode((640, 480))
    presenter = DummyPresenter(width=640, height=480, screen=screen)
    scene_renderer = SceneRenderer(presenter, TextureLibrary())
    player = DummyPlayer()
    world = {
        (0, 0, 1): OpenTile(),
        (1, 0, 1): FakeWall(visited=True),
        (2, 0, 1): WallTile(),
        (0, -1, 1): OpenTile(),
        (0, 1, 1): OpenTile(),
        (1, -1, 1): OpenTile(),
        (1, 1, 1): OpenTile(),
    }

    projected_calls = []
    special_calls = []
    translucent_wall_calls = []
    original_get_projected_surface = scene_renderer.textures.get_projected_surface
    original_get_special_texture = scene_renderer.textures.get_special_texture
    original_render_translucent_fake_wall_panel = scene_renderer._render_translucent_fake_wall_panel

    def recording_get_projected_surface(panel_id, texture_key, quad, darkness, view_size):
        projected_calls.append((panel_id, texture_key))
        return original_get_projected_surface(panel_id, texture_key, quad, darkness, view_size)

    def recording_get_special_texture(texture_key, size=None):
        special_calls.append((texture_key, size))
        return original_get_special_texture(texture_key, size)

    def recording_render_translucent_fake_wall_panel(
        tile, rect, darkness, depth, side=None, lateral_view=False
    ):
        translucent_wall_calls.append((depth, side, lateral_view))
        return original_render_translucent_fake_wall_panel(
            tile,
            rect,
            darkness,
            depth,
            side=side,
            lateral_view=lateral_view,
        )

    scene_renderer.textures.get_projected_surface = recording_get_projected_surface
    scene_renderer.textures.get_special_texture = recording_get_special_texture
    scene_renderer._render_translucent_fake_wall_panel = (
        recording_render_translucent_fake_wall_panel
    )

    scene_renderer.render(player, world)

    assert ("d1:back_wall", "wall") not in projected_calls
    assert translucent_wall_calls == [(1, None, False)]
    assert special_calls == []

    pygame.quit()


def test_scene_renderer_marks_revealed_side_fake_wall_as_translucent_wall_panel():
    pygame.init()
    screen = pygame.display.set_mode((640, 480))
    presenter = DummyPresenter(width=640, height=480, screen=screen)
    scene_renderer = SceneRenderer(presenter, TextureLibrary())
    player = DummyPlayer()
    world = {
        (0, 0, 1): OpenTile(),
        (1, 0, 1): OpenTile(),
        (2, 0, 1): OpenTile(),
        (0, -1, 1): OpenTile(),
        (1, -1, 1): FakeWall(visited=True),
    }

    special_calls = []
    translucent_wall_calls = []
    original_get_special_texture = scene_renderer.textures.get_special_texture
    original_render_translucent_fake_wall_panel = scene_renderer._render_translucent_fake_wall_panel

    def recording_get_special_texture(texture_key, size=None):
        special_calls.append((texture_key, size))
        return original_get_special_texture(texture_key, size)

    def recording_render_translucent_fake_wall_panel(
        tile, rect, darkness, depth, side=None, lateral_view=False
    ):
        translucent_wall_calls.append((depth, side, lateral_view))
        return original_render_translucent_fake_wall_panel(
            tile,
            rect,
            darkness,
            depth,
            side=side,
            lateral_view=lateral_view,
        )

    scene_renderer.textures.get_special_texture = recording_get_special_texture
    scene_renderer._render_translucent_fake_wall_panel = (
        recording_render_translucent_fake_wall_panel
    )

    scene_renderer.render(player, world)

    assert (1, "left", True) in translucent_wall_calls
    assert special_calls == []

    pygame.quit()


def test_scene_renderer_treats_open_ore_vault_door_as_open_passage():
    pygame.init()
    screen = pygame.display.set_mode((640, 480))
    presenter = DummyPresenter(width=640, height=480, screen=screen)
    scene_renderer = SceneRenderer(presenter, TextureLibrary())
    player = DummyPlayer()
    world = {
        (0, 0, 1): OpenTile(),
        (1, 0, 1): OreVaultDoor(detected=True, open=True),
        (2, 0, 1): OpenTile(),
        (0, -1, 1): OpenTile(),
        (0, 1, 1): OpenTile(),
        (1, -1, 1): OpenTile(),
        (1, 1, 1): OpenTile(),
    }

    calls = []
    original_get_projected_surface = scene_renderer.textures.get_projected_surface

    def recording_get_projected_surface(panel_id, texture_key, quad, darkness, view_size):
        calls.append((panel_id, texture_key))
        return original_get_projected_surface(panel_id, texture_key, quad, darkness, view_size)

    scene_renderer.textures.get_projected_surface = recording_get_projected_surface

    scene_renderer.render(player, world)

    assert ("d1:back_wall_slot0", "door_open") not in calls
    assert ("d1:back_wall", "wall") not in calls
    assert any(panel_id == "d2:center_floor" for panel_id, _texture in calls)

    pygame.quit()


def test_scene_renderer_renders_detected_side_ore_vault_door_in_opening():
    pygame.init()
    screen = pygame.display.set_mode((640, 480))
    presenter = DummyPresenter(width=640, height=480, screen=screen)
    scene_renderer = SceneRenderer(presenter, TextureLibrary())
    player = DummyPlayer()
    world = {
        (0, 0, 1): OpenTile(),
        (1, 0, 1): WallTile(),
        (0, -1, 1): OpenTile(),
        (1, -1, 1): OreVaultDoor(detected=True),
        (0, 1, 1): OpenTile(),
        (1, 1, 1): OpenTile(),
    }

    calls = []
    original_get_projected_surface = scene_renderer.textures.get_projected_surface

    def recording_get_projected_surface(panel_id, texture_key, quad, darkness, view_size):
        calls.append((panel_id, texture_key))
        return original_get_projected_surface(panel_id, texture_key, quad, darkness, view_size)

    scene_renderer.textures.get_projected_surface = recording_get_projected_surface

    scene_renderer.render(player, world)

    assert ("d1:left_blocker_slot0", "door_closed") in calls
    assert ("d1:left_blocker", "wall") not in calls

    pygame.quit()


def test_scene_renderer_keeps_hidden_side_ore_vault_door_as_wall():
    pygame.init()
    screen = pygame.display.set_mode((640, 480))
    presenter = DummyPresenter(width=640, height=480, screen=screen)
    scene_renderer = SceneRenderer(presenter, TextureLibrary())
    player = DummyPlayer()
    world = {
        (0, 0, 1): OpenTile(),
        (1, 0, 1): WallTile(),
        (0, -1, 1): OpenTile(),
        (1, -1, 1): OreVaultDoor(detected=False),
        (0, 1, 1): OpenTile(),
        (1, 1, 1): OpenTile(),
    }

    calls = []
    original_get_projected_surface = scene_renderer.textures.get_projected_surface

    def recording_get_projected_surface(panel_id, texture_key, quad, darkness, view_size):
        calls.append((panel_id, texture_key))
        return original_get_projected_surface(panel_id, texture_key, quad, darkness, view_size)

    scene_renderer.textures.get_projected_surface = recording_get_projected_surface

    scene_renderer.render(player, world)

    assert ("d1:left_blocker", "wall") in calls
    assert ("d1:left_blocker_slot0", "door_closed") not in calls

    pygame.quit()


def test_scene_renderer_renders_center_special_tiles_back_to_front():
    pygame.init()
    screen = pygame.display.set_mode((640, 480))
    presenter = DummyPresenter(width=640, height=480, screen=screen)
    scene_renderer = SceneRenderer(presenter, TextureLibrary())
    player = DummyPlayer()
    world = {
        (0, 0, 1): OpenTile(),
        (1, 0, 1): LadderUp(),
        (2, 0, 1): LockedDoor(),
        (0, -1, 1): OpenTile(),
        (0, 1, 1): OpenTile(),
        (1, -1, 1): OpenTile(),
        (1, 1, 1): OpenTile(),
        (2, -1, 1): OpenTile(),
        (2, 1, 1): OpenTile(),
    }

    rendered_tiles = []
    original_render_special_tile = scene_renderer._render_special_tile

    def recording_render_special_tile(tile, rect, darkness, depth, side=None, lateral_view=False):
        rendered_tiles.append((type(tile).__name__ if tile else None, depth, side, lateral_view))
        return original_render_special_tile(
            tile,
            rect,
            darkness,
            depth,
            side=side,
            lateral_view=lateral_view,
        )

    scene_renderer._render_special_tile = recording_render_special_tile

    scene_renderer.render(player, world)

    center_draws = [
        entry for entry in rendered_tiles if entry[2] is None and not entry[3] and entry[1] > 0
    ]
    assert center_draws[:2] == [("LockedDoor", 2, None, False), ("LadderUp", 1, None, False)]

    pygame.quit()


def test_scene_renderer_builds_skewed_lateral_floor_sprite_quads():
    rect = pygame.Rect(100, 200, 80, 60)

    left_quad = SceneRenderer._get_lateral_floor_sprite_quad(rect, "left")
    right_quad = SceneRenderer._get_lateral_floor_sprite_quad(rect, "right")

    assert left_quad.points[0][1] == left_quad.points[1][1]
    assert left_quad.points[0][0] > rect.left
    assert left_quad.points[2][0] == rect.right

    assert right_quad.points[0][1] == right_quad.points[1][1]
    assert right_quad.points[1][0] < rect.right
    assert right_quad.points[3][0] == rect.left


def test_scene_renderer_scales_ladder_down_as_pit_floor_sprite():
    assert SceneRenderer._get_floor_sprite_ratio(
        1, "ladder_down"
    ) > SceneRenderer._get_floor_sprite_ratio(2, "ladder_down")
    assert SceneRenderer._get_floor_sprite_ratio(
        1, "ladder_down"
    ) > SceneRenderer._get_floor_sprite_ratio(1, "chest")
    assert SceneRenderer._get_floor_sprite_ratio(
        1, "dead_soldier_item"
    ) < SceneRenderer._get_floor_sprite_ratio(1, "dead_body")
    assert SceneRenderer._get_floor_sprite_ratio(
        1, "dead_body"
    ) < SceneRenderer._get_floor_sprite_ratio(1, "boulder")


def test_scene_renderer_places_dead_body_lower_than_default_floor_anchor(monkeypatch):
    class RecordingScreen:
        def __init__(self):
            self.blit_calls = []

        def blit(self, surface, position):
            self.blit_calls.append((surface, position))

    screen = RecordingScreen()
    presenter = DummyPresenter(width=640, height=480, screen=screen)
    scene_renderer = SceneRenderer(presenter, TextureLibrary())
    sprite = pygame.Surface((54, 54), pygame.SRCALPHA)
    sprite.fill((120, 60, 40, 255))

    monkeypatch.setattr(
        scene_renderer.textures, "get_special_texture", lambda _key, _size=None: sprite
    )
    monkeypatch.setattr(
        scene_renderer, "_apply_darkness_to_surface", lambda surface, _darkness: surface
    )

    rect = pygame.Rect(0, 0, 100, 100)
    scene_renderer._render_floor_sprite("dead_body", rect, darkness=0.0, depth=1, kind="dead_body")

    assert screen.blit_calls
    assert screen.blit_calls[-1][1][1] > rect.bottom - sprite.get_height()


def test_scene_renderer_sizes_stairs_down_from_floor_width(monkeypatch):
    pygame.init()
    screen = pygame.display.set_mode((640, 480))
    presenter = DummyPresenter(width=640, height=480, screen=screen)
    scene_renderer = SceneRenderer(presenter, TextureLibrary())
    requested_sizes = []
    sprite = pygame.Surface((80, 40), pygame.SRCALPHA)
    sprite.fill((200, 140, 40, 255))

    def fake_get_special_texture(_texture_key, size=None):
        requested_sizes.append(size)
        return sprite

    monkeypatch.setattr(scene_renderer.textures, "get_special_texture", fake_get_special_texture)
    scene_renderer._render_floor_sprite(
        "stairs_down",
        pygame.Rect(100, 120, 220, 80),
        darkness=0,
        depth=1,
        kind="stairs_down",
    )

    assert requested_sizes == [252]

    pygame.quit()


def test_scene_renderer_scales_bone_pile_larger_than_other_decorative_props(monkeypatch):
    pygame.init()
    screen = pygame.display.set_mode((640, 480))
    presenter = DummyPresenter(width=640, height=480, screen=screen)
    scene_renderer = SceneRenderer(presenter, TextureLibrary())
    requested_sizes = []
    sprite = pygame.Surface((32, 32), pygame.SRCALPHA)
    sprite.fill((164, 150, 126, 255))

    def fake_get_special_texture(texture_key, size=None):
        requested_sizes.append((texture_key, size))
        return sprite

    monkeypatch.setattr(scene_renderer.textures, "get_special_texture", fake_get_special_texture)

    rect = pygame.Rect(100, 120, 180, 100)
    scene_renderer._render_floor_sprite(
        "bone_pile", rect, darkness=0, depth=1, kind="decorative_prop"
    )
    scene_renderer._render_floor_sprite("rubble", rect, darkness=0, depth=1, kind="decorative_prop")

    assert requested_sizes == [("bone_pile", 96), ("rubble", 62)]

    pygame.quit()


def test_scene_renderer_places_center_ladder_down_on_next_floor_slot():
    pygame.init()
    screen = pygame.display.set_mode((640, 480))
    presenter = DummyPresenter(width=640, height=480, screen=screen)
    scene_renderer = SceneRenderer(presenter, TextureLibrary())
    player = DummyPlayer()
    world = {
        (0, 0, 1): OpenTile(),
        (1, 0, 1): LadderDown(),
        (2, 0, 1): OpenTile(),
        (0, -1, 1): WallTile(),
        (0, 1, 1): WallTile(),
        (1, -1, 1): WallTile(),
        (1, 1, 1): WallTile(),
    }

    rendered = []

    def recording_render_special_tile(tile, rect, darkness, depth, side=None, lateral_view=False):
        if isinstance(tile, LadderDown):
            rendered.append((rect.copy(), depth, side, lateral_view))

    scene_renderer._render_special_tile = recording_render_special_tile
    scene_renderer.render(player, world)

    view_w, view_h = scene_renderer._get_viewport_size()
    depth2_zone = build_zone_geometry(
        build_depth_rect(view_w, view_h, 2),
        build_next_depth_rect(build_depth_rect(view_w, view_h, 2)),
        depth=2,
    )
    expected_bounds = scene_renderer._get_center_floor_slot_quad(
        depth2_zone, 2, "x0"
    ).bounding_rect()

    assert rendered
    rect, depth, side, lateral_view = rendered[0]
    assert depth == 2
    assert side is None
    assert lateral_view is False
    assert abs(rect.y - round(expected_bounds.y)) <= 1
    assert abs(rect.bottom - round(expected_bounds.y + expected_bounds.h)) <= 1

    pygame.quit()


def test_scene_renderer_projects_gathering_node_as_part_of_its_floor_tile():
    pygame.init()
    screen = pygame.display.set_mode((640, 480))
    presenter = DummyPresenter(width=640, height=480, screen=screen)
    scene_renderer = SceneRenderer(presenter, TextureLibrary())
    player = DummyPlayer()
    gathering_tile = OpenTile()
    gathering_tile.gathering_resource = "fungus_spore"
    gathering_tile.gathering_available = True
    gathering_tile.gathering_harvested = False
    world = {
        (0, 0, 1): gathering_tile,
        (1, 0, 1): OpenTile(),
        (2, 0, 1): OpenTile(),
        (0, -1, 1): WallTile(),
        (0, 1, 1): WallTile(),
        (1, -1, 1): WallTile(),
        (1, 1, 1): WallTile(),
    }

    commands, _ = _build_scene_commands(scene_renderer, player, world)
    current_floor = next(command for command in commands if command.panel_id == "d1:center_floor")
    assert current_floor.texture_key == "floor_gathering_fungus_spore"

    pygame.quit()


def test_scene_renderer_stretches_current_stairs_up_to_back_wall_top():
    pygame.init()
    screen = pygame.display.set_mode((640, 480))
    presenter = DummyPresenter(width=640, height=480, screen=screen)
    textures = TextureLibrary()
    scene_renderer = SceneRenderer(presenter, textures)
    player = DummyPlayer()
    world = {
        (0, 0, 1): StairsUp(),
        (1, 0, 1): OpenTile(),
        (2, 0, 1): OpenTile(),
        (0, -1, 1): WallTile(),
        (0, 1, 1): WallTile(),
        (1, -1, 1): WallTile(),
        (1, 1, 1): WallTile(),
    }

    rendered = []

    def recording_render_special_tile(tile, rect, darkness, depth, side=None, lateral_view=False):
        if isinstance(tile, StairsUp):
            rendered.append((rect.copy(), depth, side, lateral_view))

    scene_renderer._render_special_tile = recording_render_special_tile
    scene_renderer.render(player, world)

    view_w, view_h = scene_renderer._get_viewport_size()
    zones = {
        depth: build_zone_geometry(
            build_depth_rect(view_w, view_h, depth),
            build_next_depth_rect(build_depth_rect(view_w, view_h, depth)),
            depth=depth,
        )
        for depth in (1, 2, 3)
    }
    ceiling_bounds = zones[2].center_ceiling.bounding_rect()
    expected_visible_top = ceiling_bounds.top + (ceiling_bounds.h * 0.4)
    expected_visible_bottom = zones[2].center_floor.bounding_rect().bottom
    back_wall_rect = zones[2].back_wall_rect

    sprite = textures.get_special_texture("stairs_up")
    source_bounds = sprite.get_bounding_rect(min_alpha=128)

    assert rendered
    rect, depth, side, lateral_view = rendered[0]
    visible_top = rect.y + (source_bounds.top / sprite.get_height() * rect.height)
    visible_bottom = rect.y + (source_bounds.bottom / sprite.get_height() * rect.height)
    assert depth == 0
    assert side is None
    assert lateral_view is False
    assert rect.width >= round(back_wall_rect.w * 1.85)
    assert abs(rect.centerx - (back_wall_rect.x + back_wall_rect.w / 2)) <= 1
    assert rect.height > back_wall_rect.h
    assert abs(visible_top - expected_visible_top) <= 1
    assert abs(visible_bottom - expected_visible_bottom) <= 1

    pygame.quit()


def test_scene_renderer_applies_stairs_up_ascend_gradient():
    pygame.init()
    sprite = pygame.Surface((8, 8), pygame.SRCALPHA)
    sprite.fill((200, 200, 200, 255))

    shaded = SceneRenderer._apply_stairs_up_ascend_gradient(sprite)

    top = shaded.get_at((4, 0))
    bottom = shaded.get_at((4, 7))

    assert top.r < bottom.r
    assert top.g < bottom.g
    assert top.b < bottom.b
    assert top.a == 255
    assert top.r < 50
    assert bottom.r >= 198
    assert bottom.a == 255

    pygame.quit()


def test_scene_renderer_uses_ceiling_void_for_current_stairs_up_opening():
    pygame.init()
    screen = pygame.display.set_mode((640, 480))
    presenter = DummyPresenter(width=640, height=480, screen=screen)
    scene_renderer = SceneRenderer(presenter, TextureLibrary())
    player = DummyPlayer()
    world = {
        (0, 0, 1): StairsUp(),
        (1, 0, 1): OpenTile(),
        (2, 0, 1): OpenTile(),
        (0, -1, 1): WallTile(),
        (0, 1, 1): WallTile(),
        (1, -1, 1): WallTile(),
        (1, 1, 1): WallTile(),
    }

    scene_renderer.render(player, world)

    assert scene_renderer.textures.get_surface_slot_overrides() == {
        "ceiling:visible:d1:x0": "ceiling_void",
    }
    assert scene_renderer.textures.get_texture("ceiling_void").get_at((0, 0)) == pygame.Color(
        4, 5, 7, 255
    )

    pygame.quit()


def test_scene_renderer_uses_ceiling_void_for_center_stairs_up_opening():
    pygame.init()
    screen = pygame.display.set_mode((640, 480))
    presenter = DummyPresenter(width=640, height=480, screen=screen)
    scene_renderer = SceneRenderer(presenter, TextureLibrary())
    player = DummyPlayer()
    world = {
        (0, 0, 1): OpenTile(),
        (1, 0, 1): StairsUp(),
        (2, 0, 1): OpenTile(),
        (0, -1, 1): WallTile(),
        (0, 1, 1): WallTile(),
        (1, -1, 1): WallTile(),
        (1, 1, 1): WallTile(),
    }

    scene_renderer.render(player, world)

    assert scene_renderer.textures.get_surface_slot_overrides() == {
        "ceiling:visible:d2:x0": "ceiling_void",
    }

    pygame.quit()


def test_scene_renderer_stairs_up_ceiling_void_replaces_center_ceiling_slot():
    pygame.init()
    screen = pygame.display.set_mode((640, 480))
    presenter = DummyPresenter(width=640, height=480, screen=screen)
    scene_renderer = SceneRenderer(presenter, TextureLibrary())
    view_w, view_h = scene_renderer._get_viewport_size()
    zones = {
        depth: build_zone_geometry(
            build_depth_rect(view_w, view_h, depth),
            build_next_depth_rect(build_depth_rect(view_w, view_h, depth)),
            depth=depth,
        )
        for depth in (1, 2, 3)
    }
    scene_renderer.textures.set_scene_surface_slot_overrides(
        {
            "ceiling:visible:d2:x0": "ceiling_void",
        }
    )

    slot_state = scene_renderer.textures.describe_panel_surface_slot_state(
        "d2:center_ceiling", "ceiling"
    )
    center_slots = [slot for slot in slot_state if slot["slot_id"] == "ceiling:visible:d2:x0"]
    assert center_slots
    assert center_slots[0]["texture_key"] == "ceiling_void"
    assert (
        zones[2].center_ceiling.bounding_rect().top < zones[2].center_ceiling.bounding_rect().bottom
    )

    pygame.quit()


def test_scene_renderer_places_center_decorative_prop_on_next_floor_slot():
    pygame.init()
    screen = pygame.display.set_mode((640, 480))
    presenter = DummyPresenter(width=640, height=480, screen=screen)
    scene_renderer = SceneRenderer(presenter, TextureLibrary())
    player = DummyPlayer()
    world = {
        (0, 0, 1): OpenTile(),
        (1, 0, 1): BonePileTile(),
        (2, 0, 1): OpenTile(),
        (0, -1, 1): WallTile(),
        (0, 1, 1): WallTile(),
        (1, -1, 1): WallTile(),
        (1, 1, 1): WallTile(),
    }

    rendered = []

    def recording_render_special_tile(tile, rect, darkness, depth, side=None, lateral_view=False):
        if isinstance(tile, BonePileTile):
            rendered.append((rect.copy(), depth, side, lateral_view))

    scene_renderer._render_special_tile = recording_render_special_tile
    scene_renderer.render(player, world)

    view_w, view_h = scene_renderer._get_viewport_size()
    depth2_zone = build_zone_geometry(
        build_depth_rect(view_w, view_h, 2),
        build_next_depth_rect(build_depth_rect(view_w, view_h, 2)),
        depth=2,
    )
    expected_bounds = scene_renderer._get_center_floor_slot_quad(
        depth2_zone, 2, "x0"
    ).bounding_rect()

    assert rendered
    rect, depth, side, lateral_view = rendered[0]
    assert depth == 2
    assert side is None
    assert lateral_view is False
    assert abs(rect.y - round(expected_bounds.y)) <= 1
    assert abs(rect.bottom - round(expected_bounds.y + expected_bounds.h)) <= 1

    pygame.quit()


def test_project_texture_to_quad_preserves_transparent_sprite_background():
    pygame.init()
    texture = pygame.Surface((32, 32), pygame.SRCALPHA)
    texture.fill((0, 0, 0, 0))
    pygame.draw.circle(texture, (255, 200, 50, 255), (16, 16), 8)

    projected = project_texture_to_quad(
        texture,
        Quad(((2, 2), (28, 4), (30, 30), (0, 28))),
    )

    assert projected.surface.get_at((0, 0)).a == 0

    pygame.quit()


def test_trim_transparent_sprite_removes_empty_padding():
    pygame.init()
    texture = pygame.Surface((40, 20), pygame.SRCALPHA)
    texture.fill((0, 0, 0, 0))
    pygame.draw.rect(texture, (255, 255, 255, 255), pygame.Rect(10, 3, 18, 14))

    trimmed = SceneRenderer._trim_transparent_sprite(texture)

    assert trimmed.get_size() == (18, 14)

    pygame.quit()


def test_lateral_door_sprite_rect_biases_toward_outer_wall():
    rect = pygame.Rect(249, 336, 41, 96)

    left_rect = SceneRenderer._get_lateral_door_sprite_rect(rect, "left")
    right_rect = SceneRenderer._get_lateral_door_sprite_rect(rect, "right")

    assert left_rect.left < rect.left
    assert left_rect.width > rect.width
    assert right_rect.right > rect.right
    assert right_rect.width > rect.width


def test_lateral_stairs_sprite_rect_uses_extra_overscan():
    rect = pygame.Rect(415, 192, 83, 384)

    right_rect = SceneRenderer._get_lateral_stairs_sprite_rect(rect, "right")
    left_rect = SceneRenderer._get_lateral_stairs_sprite_rect(rect, "left")
    generic_right = SceneRenderer._get_special_sprite_rect(rect, side="right", lateral_view=True)

    assert right_rect.width > generic_right.width
    assert right_rect.left == rect.left
    assert left_rect.right == rect.right


def test_side_floor_special_clip_rect_keeps_chest_behind_blocking_corner():
    rect = pygame.Rect(100, 200, 80, 60)
    pygame.init()
    screen = pygame.display.set_mode((640, 480))
    presenter = DummyPresenter(width=640, height=480, screen=screen)
    scene_renderer = SceneRenderer(presenter, TextureLibrary())
    player = DummyPlayer()
    world = {
        (0, 0, 1): OpenTile(),
        (1, 0, 1): OpenTile(),
        (0, -1, 1): WallTile(),
        (0, 1, 1): OpenTile(),
        (1, 1, 1): ChestRoom(),
        (2, 1, 1): WallTile(),
    }

    _, zones = _build_scene_commands(scene_renderer, player, world)
    left_render = scene_renderer._get_side_special_render_rect(
        rect,
        ChestRoom(),
        "left",
        center_tile=OpenTile(),
        zone=zones[1],
        next_zone=zones[2],
        depth=1,
    )
    right_render = scene_renderer._get_side_special_render_rect(
        rect,
        ChestRoom(),
        "right",
        center_tile=OpenTile(),
        zone=zones[1],
        next_zone=zones[2],
        depth=1,
    )
    walled_render = scene_renderer._get_side_special_render_rect(
        rect, ChestRoom(), "left", center_tile=WallTile()
    )
    left_clip = SceneRenderer._get_side_special_clip_rect(
        rect, Boulder(), "left", center_tile=WallTile()
    )
    right_clip = SceneRenderer._get_side_special_clip_rect(
        rect, Boulder(), "right", center_tile=WallTile()
    )
    portal_clip = SceneRenderer._get_side_special_clip_rect(
        rect, Portal(), "left", center_tile=WallTile()
    )
    chest_clip = SceneRenderer._get_side_special_clip_rect(
        rect, ChestRoom(), "left", center_tile=WallTile()
    )
    boss_clip = SceneRenderer._get_side_special_clip_rect(
        rect, BossRoom(), "left", center_tile=WallTile()
    )
    unclipped_boulder = SceneRenderer._get_side_special_clip_rect(
        rect, Boulder(), "left", center_tile=OpenTile()
    )

    assert left_render.w > rect.width
    assert right_render.w > rect.width
    assert left_render.h == rect.height
    assert right_render.h == rect.height

    assert walled_render == rect

    assert left_clip.width > rect.width
    assert left_clip.left == rect.left
    assert left_clip.right > rect.right

    assert right_clip.width > rect.width
    assert right_clip.right == rect.right
    assert right_clip.left < rect.left

    assert portal_clip == rect
    assert chest_clip == rect
    assert boss_clip == rect
    assert unclipped_boulder is None

    pygame.quit()


def test_lateral_chest_floor_sprite_stays_upright_without_projection(monkeypatch):
    pygame.init()
    screen = pygame.display.set_mode((640, 480))
    presenter = DummyPresenter(width=640, height=480, screen=screen)
    scene_renderer = SceneRenderer(presenter, TextureLibrary())
    sprite = pygame.Surface((24, 24), pygame.SRCALPHA)
    sprite.fill((200, 140, 40, 255))

    monkeypatch.setattr(
        scene_renderer.textures, "get_special_texture", lambda *_args, **_kwargs: sprite
    )

    def fail_project(*_args, **_kwargs):
        raise AssertionError("side-view chests should not be perspective-projected")

    monkeypatch.setattr("src.ui_pygame.gui.dungeon.renderer.project_texture_to_quad", fail_project)

    scene_renderer._render_floor_sprite(
        "chest_closed",
        pygame.Rect(100, 120, 80, 70),
        darkness=0,
        depth=2,
        kind="chest",
        side="left",
        lateral_view=True,
    )

    pygame.quit()


def test_lateral_decorative_floor_sprite_stays_upright_without_projection(monkeypatch):
    pygame.init()
    screen = pygame.display.set_mode((640, 480))
    presenter = DummyPresenter(width=640, height=480, screen=screen)
    scene_renderer = SceneRenderer(presenter, TextureLibrary())
    sprite = pygame.Surface((24, 24), pygame.SRCALPHA)
    sprite.fill((164, 150, 126, 255))

    monkeypatch.setattr(
        scene_renderer.textures, "get_special_texture", lambda *_args, **_kwargs: sprite
    )

    def fail_project(*_args, **_kwargs):
        raise AssertionError("side-view decorative floor props should not be perspective-projected")

    monkeypatch.setattr("src.ui_pygame.gui.dungeon.renderer.project_texture_to_quad", fail_project)

    scene_renderer._render_floor_sprite(
        "bone_pile",
        pygame.Rect(100, 120, 80, 70),
        darkness=0,
        depth=2,
        kind="decorative_prop",
        side="left",
        lateral_view=True,
    )

    pygame.quit()


def test_depth2_side_floor_special_geometry_stays_in_outer_lanes():
    pygame.init()
    screen = pygame.display.set_mode((640, 480))
    presenter = DummyPresenter(width=640, height=480, screen=screen)
    scene_renderer = SceneRenderer(presenter, TextureLibrary())
    player = DummyPlayer()
    world = {
        (0, 0, 1): OpenTile(),
        (1, 0, 1): OpenTile(),
        (2, 0, 1): OpenTile(),
        (3, 0, 1): OpenTile(),
        (1, -1, 1): OpenTile(),
        (1, 1, 1): OpenTile(),
        (2, -1, 1): ChestRoom(),
        (2, 1, 1): ChestRoom(),
    }

    _, zones = _build_scene_commands(scene_renderer, player, world)
    view_w, _view_h = scene_renderer._get_viewport_size()

    left_opening = scene_renderer._get_side_opening_rect(zones[2], "left")
    right_opening = scene_renderer._get_side_opening_rect(zones[2], "right")
    left_rect = scene_renderer._get_side_special_render_rect(
        left_opening,
        ChestRoom(),
        "left",
        center_tile=OpenTile(),
        zone=zones[2],
        next_zone=zones[3],
        depth=2,
    )
    right_rect = scene_renderer._get_side_special_render_rect(
        right_opening,
        ChestRoom(),
        "right",
        center_tile=OpenTile(),
        zone=zones[2],
        next_zone=zones[3],
        depth=2,
    )
    left_floor, right_floor = (
        scene_renderer._get_side_special_surface_geometry(zones[2], zones[3], "left", 2)[0],
        scene_renderer._get_side_special_surface_geometry(zones[2], zones[3], "right", 2)[0],
    )

    assert scene_renderer._get_side_special_surface_geometry(zones[2], zones[3], "left", 2)[2] == 3
    assert scene_renderer._get_side_special_surface_geometry(zones[2], zones[3], "right", 2)[2] == 3
    assert round(left_rect.x) == round(left_floor.bounding_rect().x)
    assert round(right_rect.x) == round(right_floor.bounding_rect().x)
    assert round(left_rect.w) == round(right_rect.w)
    assert left_rect.x + left_rect.w < view_w / 2
    assert right_rect.x > view_w / 2

    pygame.quit()


def test_scene_renderer_places_depth2_side_floor_sprites_at_depth3_edges():
    pygame.init()
    screen = pygame.display.set_mode((640, 480))
    presenter = DummyPresenter(width=640, height=480, screen=screen)
    scene_renderer = SceneRenderer(presenter, TextureLibrary())
    player = DummyPlayer()
    world = {
        (0, 0, 1): OpenTile(),
        (1, 0, 1): OpenTile(),
        (2, 0, 1): OpenTile(),
        (3, 0, 1): OpenTile(),
        (1, -1, 1): OpenTile(),
        (1, 1, 1): OpenTile(),
        (2, -1, 1): ChestRoom(),
        (2, 1, 1): ChestRoom(),
    }
    view_w, _view_h = scene_renderer._get_viewport_size()
    rendered_tiles = []
    original_render_special_tile = scene_renderer._render_special_tile

    def recording_render_special_tile(tile, rect, darkness, depth, side=None, lateral_view=False):
        rendered_tiles.append(
            (type(tile).__name__ if tile else None, rect, depth, side, lateral_view)
        )
        return original_render_special_tile(
            tile,
            rect,
            darkness,
            depth,
            side=side,
            lateral_view=lateral_view,
        )

    scene_renderer._render_special_tile = recording_render_special_tile

    scene_renderer.render(player, world)

    left_chest = next(
        item for item in rendered_tiles if item[0] == "ChestRoom" and item[3] == "left"
    )
    right_chest = next(
        item for item in rendered_tiles if item[0] == "ChestRoom" and item[3] == "right"
    )

    assert left_chest[2:] == (3, "left", True)
    assert right_chest[2:] == (3, "right", True)
    assert left_chest[1].right < view_w / 2
    assert right_chest[1].left > view_w / 2

    pygame.quit()


def test_scene_renderer_routes_left_side_floor_special_to_outer_depth3_floor():
    pygame.init()
    screen = pygame.display.set_mode((640, 480))
    presenter = DummyPresenter(width=640, height=480, screen=screen)
    scene_renderer = SceneRenderer(presenter, TextureLibrary())
    player = DummyPlayer()
    world = {
        (0, 0, 1): OpenTile(),
        (1, 0, 1): OpenTile(),
        (2, 0, 1): OpenTile(),
        (3, 0, 1): OpenTile(),
        (1, -1, 1): OpenTile(),
        (2, -1, 1): FirePath(),
        (1, 1, 1): OpenTile(),
    }

    calls = []
    original_get_projected_surface = scene_renderer.textures.get_projected_surface

    def recording_get_projected_surface(panel_id, texture_key, quad, darkness, view_size):
        calls.append((panel_id, texture_key, quad.bounding_rect()))
        return original_get_projected_surface(panel_id, texture_key, quad, darkness, view_size)

    scene_renderer.textures.get_projected_surface = recording_get_projected_surface

    scene_renderer.render(player, world)

    left_floor = next(
        item
        for item in calls
        if item[0] == "d3:left_corridor_outer_floor" and item[1] == "floor_fire"
    )
    assert left_floor[2].right < scene_renderer._get_viewport_size()[0] / 2
    assert not any(
        panel_id == "d3:right_corridor_outer_floor" for panel_id, _texture, _rect in calls
    )

    pygame.quit()


def test_scene_renderer_routes_right_side_floor_special_to_outer_depth3_floor():
    pygame.init()
    screen = pygame.display.set_mode((640, 480))
    presenter = DummyPresenter(width=640, height=480, screen=screen)
    scene_renderer = SceneRenderer(presenter, TextureLibrary())
    player = DummyPlayer()
    world = {
        (0, 0, 1): OpenTile(),
        (1, 0, 1): OpenTile(),
        (2, 0, 1): OpenTile(),
        (3, 0, 1): OpenTile(),
        (1, 1, 1): OpenTile(),
        (2, 1, 1): FirePath(),
        (1, -1, 1): OpenTile(),
    }

    calls = []
    original_get_projected_surface = scene_renderer.textures.get_projected_surface

    def recording_get_projected_surface(panel_id, texture_key, quad, darkness, view_size):
        calls.append((panel_id, texture_key, quad.bounding_rect()))
        return original_get_projected_surface(panel_id, texture_key, quad, darkness, view_size)

    scene_renderer.textures.get_projected_surface = recording_get_projected_surface

    scene_renderer.render(player, world)

    right_floor = next(
        item
        for item in calls
        if item[0] == "d3:right_corridor_outer_floor" and item[1] == "floor_fire"
    )
    assert right_floor[2].left > scene_renderer._get_viewport_size()[0] / 2
    assert not any(
        panel_id == "d3:left_corridor_outer_floor" for panel_id, _texture, _rect in calls
    )

    pygame.quit()


def test_texture_library_floor_slot_override_changes_projected_corridor_floor_surface():
    pygame.init()
    screen = pygame.display.set_mode((640, 480))
    presenter = DummyPresenter(width=640, height=480, screen=screen)
    scene_renderer = SceneRenderer(presenter, TextureLibrary())
    player = DummyPlayer()
    world = {
        (0, 0, 1): OpenTile(),
        (1, 0, 1): WallTile(),
        (0, -1, 1): WallTile(),
        (1, -1, 1): WallTile(),
        (0, 1, 1): OpenTile(),
        (1, 1, 1): OpenTile(),
    }

    _, zones = _build_scene_commands(scene_renderer, player, world)
    corridor_quad = scene_renderer._push_outer_floor_quad(
        zones[2].center_floor_right,
        "right",
        float(zones[1].rect.w) * 0.25,
        float(zones[1].rect.w) * 0.5,
    )

    baseline = scene_renderer.textures.get_projected_surface(
        panel_id="d2:right_corridor_outer_floor",
        texture_key="floor",
        quad=corridor_quad,
        darkness=0.0,
        view_size=scene_renderer._get_viewport_size(),
    )

    scene_renderer.textures.set_floor_slot_override(
        "floor:corridor_outer:right:d2:tile", "floor_pit"
    )
    overridden = scene_renderer.textures.get_projected_surface(
        panel_id="d2:right_corridor_outer_floor",
        texture_key="floor",
        quad=corridor_quad,
        darkness=0.0,
        view_size=scene_renderer._get_viewport_size(),
    )

    assert pygame.image.tostring(overridden.surface, "RGBA") != pygame.image.tostring(
        baseline.surface, "RGBA"
    )

    scene_renderer.textures.clear_floor_slot_overrides()

    pygame.quit()


def test_scene_renderer_routes_side_ladder_floor_through_center_floor_slot_override():
    pygame.init()
    screen = pygame.display.set_mode((640, 480))
    presenter = DummyPresenter(width=640, height=480, screen=screen)
    scene_renderer = SceneRenderer(presenter, TextureLibrary())
    player = DummyPlayer()
    world = {
        (0, 0, 1): OpenTile(),
        (1, 0, 1): WallTile(),
        (0, -1, 1): WallTile(),
        (1, -1, 1): WallTile(),
        (0, 1, 1): OpenTile(),
        (1, 1, 1): LadderDown(),
    }

    calls = []
    original_get_projected_surface = scene_renderer.textures.get_projected_surface

    def recording_get_projected_surface(panel_id, texture_key, quad, darkness, view_size):
        calls.append((panel_id, texture_key))
        return original_get_projected_surface(panel_id, texture_key, quad, darkness, view_size)

    scene_renderer.textures.get_projected_surface = recording_get_projected_surface

    scene_renderer.render(player, world)

    assert ("d2:center_floor", "floor") not in calls
    assert ("d2:center_floor_slot3", "floor_pit") in calls
    assert ("d1:right_opening_special_floor", "floor_pit") not in calls
    assert scene_renderer.textures.get_floor_slot_overrides() == {
        "floor:visible:d2:xp1": "floor_pit",
    }

    pygame.quit()


def test_scene_renderer_keeps_side_ladder_down_surface_only_at_all_visible_depths():
    for side in ("left", "right"):
        for side_depth in (1, 2, 3):
            calls, rendered_tiles, overrides = _render_side_forward_tile_case(
                LadderDown(), side, side_depth
            )
            assert ("LadderDown", side_depth, side, True) not in rendered_tiles

            if side_depth == 3:
                assert not any(texture_key == "floor_pit" for _panel_id, texture_key in calls)
                assert overrides == {}
                continue

            surface_depth = side_depth + 1
            slot_suffix = "xm1" if side == "left" else "xp1"
            assert overrides == {
                f"floor:visible:d{surface_depth}:{slot_suffix}": "floor_pit",
            }
            assert any(
                panel_id.startswith(f"d{surface_depth}:center_floor_slot")
                and texture_key == "floor_pit"
                for panel_id, texture_key in calls
            )


def test_scene_renderer_localizes_current_underground_spring_floor_to_center_slot():
    pygame.init()
    screen = pygame.display.set_mode((640, 480))
    presenter = DummyPresenter(width=640, height=480, screen=screen)
    scene_renderer = SceneRenderer(presenter, TextureLibrary())
    player = DummyPlayer()
    world = {
        (0, 0, 1): UndergroundSpring(),
        (1, 0, 1): WallTile(),
        (0, -1, 1): OpenTile(),
        (0, 1, 1): OpenTile(),
    }

    calls = []
    original_get_projected_surface = scene_renderer.textures.get_projected_surface

    def recording_get_projected_surface(panel_id, texture_key, quad, darkness, view_size):
        calls.append((panel_id, texture_key))
        return original_get_projected_surface(panel_id, texture_key, quad, darkness, view_size)

    scene_renderer.textures.get_projected_surface = recording_get_projected_surface

    scene_renderer.render(player, world)

    assert ("d1:center_floor", "floor") not in calls
    assert ("d1:center_floor_slot1", "floor_spring") in calls
    assert scene_renderer.textures.get_floor_slot_overrides() == {
        "floor:visible:d1:x0": "floor_spring",
    }

    pygame.quit()


def test_scene_renderer_maps_adjacent_side_spring_to_left_visible_floor_slot():
    pygame.init()
    screen = pygame.display.set_mode((640, 480))
    presenter = DummyPresenter(width=640, height=480, screen=screen)
    scene_renderer = SceneRenderer(presenter, TextureLibrary())
    player = DummyPlayer(location_x=4, location_y=8, facing="west")
    world = {
        (4, 8, 1): OpenTile(),
        (3, 8, 1): WallTile(),
        (4, 9, 1): UndergroundSpring(),
        (4, 7, 1): OpenTile(),
        (3, 9, 1): WallTile(),
        (3, 7, 1): LockedDoor(),
    }

    calls = []
    original_get_projected_surface = scene_renderer.textures.get_projected_surface

    def recording_get_projected_surface(panel_id, texture_key, quad, darkness, view_size):
        calls.append((panel_id, texture_key))
        return original_get_projected_surface(panel_id, texture_key, quad, darkness, view_size)

    scene_renderer.textures.get_projected_surface = recording_get_projected_surface

    scene_renderer.render(player, world)

    assert ("d1:center_floor", "floor") not in calls
    assert ("d1:center_floor_slot0", "floor_spring") in calls
    assert (
        scene_renderer.textures.get_floor_slot_overrides()["floor:visible:d1:xm1"] == "floor_spring"
    )

    pygame.quit()


def test_scene_renderer_hides_side_ladder_beyond_max_visible_depth():
    pygame.init()
    screen = pygame.display.set_mode((640, 480))
    presenter = DummyPresenter(width=640, height=480, screen=screen)
    scene_renderer = SceneRenderer(presenter, TextureLibrary())
    player = DummyPlayer()
    world = {
        (0, 0, 1): OpenTile(),
        (1, 0, 1): OpenTile(),
        (2, 0, 1): OpenTile(),
        (3, 0, 1): OpenTile(),
        (0, -1, 1): WallTile(),
        (1, -1, 1): WallTile(),
        (2, -1, 1): WallTile(),
        (3, -1, 1): WallTile(),
        (0, 1, 1): WallTile(),
        (1, 1, 1): WallTile(),
        (2, 1, 1): OpenTile(),
        (3, 1, 1): LadderDown(),
    }

    calls = []
    rendered_tiles = []
    original_get_projected_surface = scene_renderer.textures.get_projected_surface
    original_render_special_tile = scene_renderer._render_special_tile

    def recording_get_projected_surface(panel_id, texture_key, quad, darkness, view_size):
        calls.append((panel_id, texture_key))
        return original_get_projected_surface(panel_id, texture_key, quad, darkness, view_size)

    def recording_render_special_tile(tile, rect, darkness, depth, side=None, lateral_view=False):
        rendered_tiles.append((type(tile).__name__ if tile else None, depth, side, lateral_view))
        return original_render_special_tile(
            tile,
            rect,
            darkness,
            depth,
            side=side,
            lateral_view=lateral_view,
        )

    scene_renderer.textures.get_projected_surface = recording_get_projected_surface
    scene_renderer._render_special_tile = recording_render_special_tile

    scene_renderer.render(player, world)

    assert ("d3:center_floor", "floor") not in calls
    assert any(panel_id.startswith("d3:center_floor_slot") for panel_id, _ in calls)
    assert not any(
        panel_id.startswith("d3:center_floor_slot") and texture_key == "floor_pit"
        for panel_id, texture_key in calls
    )
    assert ("LadderDown", 3, "right", True) not in rendered_tiles
    assert scene_renderer.textures.get_floor_slot_overrides() == {}

    pygame.quit()


def test_scene_renderer_routes_far_right_floor_special_to_outer_depth3_slot():
    pygame.init()
    screen = pygame.display.set_mode((640, 480))
    presenter = DummyPresenter(width=640, height=480, screen=screen)
    scene_renderer = SceneRenderer(presenter, TextureLibrary())
    player = DummyPlayer()
    world = {
        (0, 0, 1): OpenTile(),
        (1, 0, 1): BossRoom(enemy=DummyEnemy("Cockatrice"), defeated=True),
        (2, 0, 1): OpenTile(),
        (3, 0, 1): None,
        (0, -1, 1): WallTile(),
        (0, 1, 1): WallTile(),
        (0, -2, 1): WallTile(),
        (0, 2, 1): ChestRoom(),
        (1, -1, 1): ChestRoom(),
        (1, 1, 1): ChestRoom(),
        (1, -2, 1): WallTile(),
        (1, 2, 1): WallTile(),
        (2, -1, 1): WallTile(),
        (2, 1, 1): LadderDown(),
        (2, -2, 1): WallTile(),
        (2, 2, 1): LockedDoor(),
    }

    calls = []
    original_get_projected_surface = scene_renderer.textures.get_projected_surface

    def recording_get_projected_surface(panel_id, texture_key, quad, darkness, view_size):
        calls.append((panel_id, texture_key))
        return original_get_projected_surface(panel_id, texture_key, quad, darkness, view_size)

    scene_renderer.textures.get_projected_surface = recording_get_projected_surface

    scene_renderer.render(player, world)

    assert ("d3:center_floor", "floor") not in calls
    assert any(panel_id.startswith("d3:center_floor_slot") for panel_id, _ in calls)
    assert ("d3:center_floor_slot5", "floor_pit") in calls
    assert scene_renderer.textures.get_floor_slot_overrides()["floor:visible:d3:xp1"] == "floor_pit"

    pygame.quit()


def test_scene_renderer_renders_depth3_center_ceiling_through_slot_commands_without_overrides():
    pygame.init()
    screen = pygame.display.set_mode((640, 480))
    presenter = DummyPresenter(width=640, height=480, screen=screen)
    scene_renderer = SceneRenderer(presenter, TextureLibrary())
    player = DummyPlayer()
    world = {
        (0, 0, 1): OpenTile(),
        (1, 0, 1): OpenTile(),
        (2, 0, 1): OpenTile(),
        (0, -1, 1): OpenTile(),
        (0, 1, 1): OpenTile(),
        (1, -1, 1): OpenTile(),
        (1, 1, 1): OpenTile(),
        (2, -1, 1): OpenTile(),
        (2, 1, 1): OpenTile(),
    }

    calls = []
    original_get_projected_surface = scene_renderer.textures.get_projected_surface

    def recording_get_projected_surface(panel_id, texture_key, quad, darkness, view_size):
        calls.append((panel_id, texture_key))
        return original_get_projected_surface(panel_id, texture_key, quad, darkness, view_size)

    scene_renderer.textures.get_projected_surface = recording_get_projected_surface

    scene_renderer.render(player, world)

    assert ("d3:center_ceiling", "ceiling") not in calls
    assert any(panel_id.startswith("d3:center_ceiling_slot") for panel_id, _ in calls)
    assert ("d3:center_ceiling_slot0", "ceiling") in calls
    assert ("d3:center_ceiling_slot8", "ceiling") in calls

    pygame.quit()


def test_scene_renderer_renders_migrated_special_tile_sprites():
    pygame.init()
    screen = pygame.display.set_mode((640, 480))
    presenter = DummyPresenter(width=640, height=480, screen=screen)
    scene_renderer = SceneRenderer(presenter, TextureLibrary())
    scene_renderer.player_char = DummyPlayer(location_z=3)
    scene_renderer.player_char.quest_dict = {
        "Side": {
            "Rookie Mistake": {"Completed": False},
            "The Holy Grail of Quests": {
                "Completed": False,
                "Chalice Progress": {"Revealed": True},
            },
        }
    }
    scene_renderer.player_char.special_inventory = {}
    rect = pygame.Rect(120, 120, 160, 160)

    special_calls = []
    enemy_calls = []
    original_get_special_texture = scene_renderer.textures.get_special_texture
    original_get_enemy_texture = scene_renderer.textures.get_enemy_texture

    def recording_get_special_texture(texture_key, size=None):
        special_calls.append((texture_key, size))
        return original_get_special_texture(texture_key, size)

    def recording_get_enemy_texture(enemy_name, size=None):
        enemy_calls.append((enemy_name, size))
        return original_get_enemy_texture(enemy_name, size)

    scene_renderer.textures.get_special_texture = recording_get_special_texture
    scene_renderer.textures.get_enemy_texture = recording_get_enemy_texture

    tiles = (
        Portal(),
        Boulder(read=False),
        Boulder(read=True),
        DeadBody(read=False),
        DeadBody(read=True),
        RookieCavePath(read=False),
        RelicRoom(read=False),
        RelicRoom(read=True),
        GoldenChaliceRoom(read=False),
        GoldenChaliceRoom(read=True),
        UnobtainiumRoom(visited=False),
        SecretShop(),
        WarpPoint(),
        Rotator(),
        StairsDown(),
        BossRoom(enemy=DummyEnemy("Minotaur")),
        BossRoom(enemy=DummyEnemy("Jester")),
    )

    for tile in tiles:
        scene_renderer._render_special_tile(tile, rect, darkness=0.0, depth=1)

    assert SceneRenderer._is_floor_sprite_tile(RookieCavePath(read=False)) is True
    assert SceneRenderer._is_floor_sprite_tile(RookieCavePath(read=True)) is False
    assert ("portal", None) in special_calls
    assert ("boulder_sword", 112) in special_calls
    assert ("boulder", 112) in special_calls
    assert ("dead_body", 86) in special_calls
    assert ("burial_site", 86) in special_calls
    assert ("dead_soldier_item", 67) in special_calls
    assert ("hexagonum_altar", 96) in special_calls
    assert ("empty_altar", 96) in special_calls
    assert ("golden_chalice_altar", 96) in special_calls
    assert ("empty_golden_chalice_altar", 96) in special_calls
    assert ("unobtainium", 72) in special_calls
    assert ("secret_shop", None) in special_calls
    assert ("warp_point_inactive", 172) in special_calls
    assert ("rotator", 89) in special_calls
    assert ("stairs_down", 184) in special_calls
    assert ("stairs_down", None) not in special_calls
    assert ("Minotaur", 160) in enemy_calls
    assert ("Jester", 104) in enemy_calls

    pygame.quit()


def test_scene_renderer_skips_funhouse_teleporter_sprite():
    pygame.init()
    screen = pygame.display.set_mode((640, 480))
    presenter = DummyPresenter(width=640, height=480, screen=screen)
    scene_renderer = SceneRenderer(presenter, TextureLibrary())
    rect = pygame.Rect(120, 120, 160, 160)

    special_calls = []
    original_get_special_texture = scene_renderer.textures.get_special_texture

    def recording_get_special_texture(texture_key, size=None):
        special_calls.append((texture_key, size))
        return original_get_special_texture(texture_key, size)

    scene_renderer.textures.get_special_texture = recording_get_special_texture

    before = pygame.image.tostring(screen, "RGBA")
    for tile in (FunhouseTeleporter(active=True), FunhouseTeleporter(active=False)):
        scene_renderer._render_special_tile(
            tile,
            rect,
            darkness=0.0,
            depth=1,
        )
        after = pygame.image.tostring(screen, "RGBA")
        assert not any(texture_key == "funhouse_teleporter" for texture_key, _size in special_calls)
        assert before == after

    pygame.quit()


def test_scene_renderer_renders_defeated_boss_replacement_visual():
    pygame.init()
    screen = pygame.display.set_mode((640, 480))
    presenter = DummyPresenter(width=640, height=480, screen=screen)
    scene_renderer = SceneRenderer(presenter, TextureLibrary())
    rect = pygame.Rect(120, 120, 160, 160)

    special_calls = []
    enemy_calls = []
    original_get_special_texture = scene_renderer.textures.get_special_texture
    original_get_enemy_texture = scene_renderer.textures.get_enemy_texture

    def recording_get_special_texture(texture_key, size=None):
        special_calls.append((texture_key, size))
        return original_get_special_texture(texture_key, size)

    def recording_get_enemy_texture(enemy_name, size=None):
        enemy_calls.append((enemy_name, size))
        return original_get_enemy_texture(enemy_name, size)

    scene_renderer.textures.get_special_texture = recording_get_special_texture
    scene_renderer.textures.get_enemy_texture = recording_get_enemy_texture

    before = pygame.image.tostring(screen, "RGBA")
    scene_renderer._render_special_tile(
        BossRoom(enemy=DummyEnemy("Minotaur"), defeated=True),
        rect,
        darkness=0.0,
        depth=1,
    )
    after = pygame.image.tostring(screen, "RGBA")

    assert ("burial_site", 112) in special_calls
    assert enemy_calls == []
    assert before != after

    pygame.quit()


def test_scene_renderer_draws_jester_force_field_at_all_visible_depths_until_tokens_collected():
    pygame.init()
    try:
        for jester_depth in (1, 2, 3):
            screen = pygame.display.set_mode((640, 480))
            presenter = DummyPresenter(width=640, height=480, screen=screen)
            scene_renderer = SceneRenderer(presenter, TextureLibrary())
            player = DummyPlayer(facing="east")
            world = {
                (0, 0, 1): OpenTile(),
                **{(depth, 0, 1): OpenTile() for depth in range(1, jester_depth)},
                (jester_depth, 0, 1): JesterBossRoom(enemy=DummyEnemy("Jester")),
            }

            calls = []
            boss_calls = []
            render_order = []

            def recording_render_force_field(rect, darkness, depth, *, body=True, arcs=True):
                if body:
                    render_order.append("force_field_body")
                if arcs:
                    render_order.append("force_field_arcs")
                calls.append((rect.copy(), darkness, depth, body, arcs))

            def recording_render_boss_enemy(
                tile, rect, darkness, depth, side=None, lateral_view=False
            ):
                render_order.append("boss")
                boss_calls.append((tile, rect.copy(), darkness, depth, side, lateral_view))

            scene_renderer._render_jester_force_field = recording_render_force_field
            scene_renderer._render_boss_enemy = recording_render_boss_enemy

            scene_renderer.render(player, world)

            view_w, view_h = scene_renderer._get_viewport_size()
            depth_rect = build_depth_rect(view_w, view_h, jester_depth)
            expected_zone = build_zone_geometry(
                depth_rect,
                build_next_depth_rect(depth_rect),
                depth=jester_depth,
            )
            expected_rect = pygame.Rect(expected_zone.back_wall_rect.to_int_tuple())

            assert len(calls) == 1
            assert calls[0][0] == expected_rect
            assert calls[0][2] == jester_depth
            assert calls[0][3:] == (True, True)
            assert len(boss_calls) == 1
            assert render_order == ["boss", "force_field_body", "force_field_arcs"]

            calls.clear()
            boss_calls.clear()
            render_order.clear()
            player.special_inventory = {
                "Jester Token": [
                    SimpleNamespace(name="Jester Token")
                    for _ in range(map_tiles.JESTER_TOKENS_REQUIRED)
                ],
            }

            scene_renderer.render(player, world)

            assert calls == []
            assert len(boss_calls) == 1
            assert render_order == ["boss"]
    finally:
        pygame.quit()


def test_scene_renderer_draws_side_jester_force_field_in_front_of_side_boss():
    pygame.init()
    screen = pygame.display.set_mode((640, 480))
    presenter = DummyPresenter(width=640, height=480, screen=screen)
    scene_renderer = SceneRenderer(presenter, TextureLibrary())
    player = DummyPlayer(facing="east")
    world = {
        (0, 0, 1): OpenTile(),
        (1, 0, 1): WallTile(),
        (0, -1, 1): OpenTile(),
        (1, -1, 1): JesterBossRoom(enemy=DummyEnemy("Jester")),
    }

    calls = []
    boss_calls = []
    render_order = []
    boss_clips = []

    def recording_render_force_field(rect, darkness, depth, *, body=True, arcs=True):
        if body:
            render_order.append("force_field_body")
        if arcs:
            render_order.append("force_field_arcs")
        calls.append((rect.copy(), darkness, depth, body, arcs))

    def recording_render_boss_enemy(tile, rect, darkness, depth, side=None, lateral_view=False):
        render_order.append("boss")
        boss_clips.append(screen.get_clip().copy())
        boss_calls.append((tile, rect.copy(), darkness, depth, side, lateral_view))

    scene_renderer._render_jester_force_field = recording_render_force_field
    scene_renderer._render_boss_enemy = recording_render_boss_enemy

    scene_renderer.render(player, world)
    view_w, view_h = scene_renderer._get_viewport_size()
    depth1_zone = build_zone_geometry(
        build_depth_rect(view_w, view_h, 1),
        build_next_depth_rect(build_depth_rect(view_w, view_h, 1)),
        depth=1,
    )
    expected_clip = SceneRenderer._get_side_opening_rect(depth1_zone, "left")

    assert len(boss_calls) == 1
    assert boss_calls[0][3:] == (1, "left", True)
    assert boss_clips == [expected_clip]
    assert len(calls) == 1
    assert calls[0][2:] == (1, True, True)
    assert render_order == ["boss", "force_field_body", "force_field_arcs"]

    pygame.quit()


def test_scene_renderer_sizes_side_jester_from_opening_height():
    pygame.init()
    screen = pygame.display.set_mode((640, 480))
    presenter = DummyPresenter(width=640, height=480, screen=screen)
    scene_renderer = SceneRenderer(presenter, TextureLibrary())
    rect = pygame.Rect(0, 120, 64, 240)
    texture_calls = []

    def recording_get_enemy_texture(enemy_name, size=None):
        texture_calls.append((enemy_name, size))
        return pygame.Surface((size, size), pygame.SRCALPHA)

    scene_renderer.textures.get_enemy_texture = recording_get_enemy_texture

    scene_renderer._render_boss_enemy(
        JesterBossRoom(enemy=DummyEnemy("Jester")),
        rect,
        darkness=0.0,
        depth=1,
        side="left",
        lateral_view=True,
    )

    assert texture_calls == [("Jester", 156)]

    pygame.quit()


def test_scene_renderer_jester_force_field_draws_overlay_pixels():
    pygame.init()
    screen = pygame.display.set_mode((640, 480))
    presenter = DummyPresenter(width=640, height=480, screen=screen)
    scene_renderer = SceneRenderer(presenter, TextureLibrary())

    before = pygame.image.tostring(screen, "RGBA")
    scene_renderer._render_jester_force_field(
        pygame.Rect(120, 120, 160, 160),
        darkness=0.0,
        depth=1,
    )
    after = pygame.image.tostring(screen, "RGBA")

    assert before != after
    assert any(
        screen.get_at((x, y)).g > 90 and screen.get_at((x, y)).b > 100
        for x in range(120, 280)
        for y in range(120, 280)
    )

    pygame.quit()


def test_scene_renderer_jester_force_field_remains_visible_with_darkness():
    pygame.init()
    screen = pygame.display.set_mode((640, 480))
    presenter = DummyPresenter(width=640, height=480, screen=screen)
    scene_renderer = SceneRenderer(presenter, TextureLibrary())

    before = pygame.image.tostring(screen, "RGBA")
    scene_renderer._render_jester_force_field(
        pygame.Rect(120, 120, 160, 160),
        darkness=0.65,
        depth=3,
    )
    after = pygame.image.tostring(screen, "RGBA")

    assert before != after
    assert any(
        screen.get_at((x, y)).g > 110 and screen.get_at((x, y)).b > 115
        for x in range(120, 280)
        for y in range(120, 280)
    )

    pygame.quit()


def test_scene_renderer_caches_jester_force_field_body_surface():
    pygame.init()
    screen = pygame.display.set_mode((640, 480))
    presenter = DummyPresenter(width=640, height=480, screen=screen)
    scene_renderer = SceneRenderer(presenter, TextureLibrary())
    rect = pygame.Rect(120, 120, 160, 160)

    scene_renderer._render_jester_force_field(rect, darkness=0.65, depth=3, arcs=False)
    cache_size_after_first_render = len(scene_renderer._jester_force_field_body_cache)
    scene_renderer._render_jester_force_field(rect, darkness=0.65, depth=3, arcs=False)

    assert cache_size_after_first_render == 1
    assert len(scene_renderer._jester_force_field_body_cache) == 1

    pygame.quit()


def test_scene_renderer_prewarms_jester_force_field_body_cache_for_area():
    pygame.init()
    screen = pygame.display.set_mode((640, 480))
    presenter = DummyPresenter(width=640, height=480, screen=screen)
    scene_renderer = SceneRenderer(presenter, TextureLibrary())
    player = DummyPlayer(facing="east")
    world = {
        (0, 0, 1): OpenTile(),
        (1, 0, 1): OpenTile(),
        (8, 8, 1): JesterBossRoom(enemy=DummyEnemy("Jester")),
    }

    scene_renderer.render(player, world)

    assert len(scene_renderer._jester_force_field_body_cache) > 1

    pygame.quit()


def test_scene_renderer_renders_active_warp_point_with_active_sprite():
    pygame.init()
    screen = pygame.display.set_mode((640, 480))
    presenter = DummyPresenter(width=640, height=480, screen=screen)
    scene_renderer = SceneRenderer(presenter, TextureLibrary())
    scene_renderer.player_char = DummyPlayer(warp_point=True)
    rect = pygame.Rect(120, 120, 160, 160)

    before = pygame.image.tostring(screen, "RGBA")
    scene_renderer._render_special_tile(WarpPoint(), rect, darkness=0.0, depth=1)
    after = pygame.image.tostring(screen, "RGBA")

    assert before != after

    pygame.quit()


def test_scene_renderer_uses_warp_point_state_assets_and_teleporter_fallback():
    pygame.init()
    screen = pygame.display.set_mode((640, 480))
    presenter = DummyPresenter(width=640, height=480, screen=screen)
    scene_renderer = SceneRenderer(presenter, TextureLibrary())

    scene_renderer.player_char = DummyPlayer(warp_point=True)
    assert scene_renderer._warp_point_sprite_key() == "warp_point_active"

    scene_renderer.player_char = DummyPlayer(warp_point=False)
    assert scene_renderer._warp_point_sprite_key() == "warp_point_inactive"

    scene_renderer.player_char = DummyPlayer(warp_point=True)
    scene_renderer.textures.special_texture_paths.pop("warp_point_active", None)
    assert scene_renderer._warp_point_sprite_key() == "teleporter"

    pygame.quit()


def test_warp_point_art_review_sheet_builder_smoke(tmp_path):
    from tools.build_warp_point_art_sheet import DEFAULT_SPECIAL_ROOT, draw_review_sheet

    output = tmp_path / "warp_point_sheet.png"

    draw_review_sheet(DEFAULT_SPECIAL_ROOT, output)

    assert output.exists()
    assert output.stat().st_size > 0


def test_scene_renderer_centers_warp_point_effects_on_sprite():
    pygame.init()
    screen = pygame.display.set_mode((640, 480))
    presenter = DummyPresenter(width=640, height=480, screen=screen)
    scene_renderer = SceneRenderer(presenter, TextureLibrary())

    rect = pygame.Rect(200, 300, 180, 96)
    effect_rect = scene_renderer._get_warp_point_effect_rect(rect)

    assert effect_rect.centerx == rect.centerx
    assert effect_rect.centery < rect.bottom
    assert effect_rect.centery > rect.y
    assert effect_rect.width > round(rect.width * 0.35)

    pygame.quit()


def test_scene_renderer_scales_warp_point_down_with_distance():
    pygame.init()
    screen = pygame.display.set_mode((640, 480))
    presenter = DummyPresenter(width=640, height=480, screen=screen)
    scene_renderer = SceneRenderer(presenter, TextureLibrary())
    scene_renderer.player_char = DummyPlayer(warp_point=True)
    rect = pygame.Rect(120, 120, 160, 160)

    special_calls = []
    original_get_special_texture = scene_renderer.textures.get_special_texture

    def recording_get_special_texture(texture_key, size=None):
        special_calls.append((texture_key, size))
        return original_get_special_texture(texture_key, size)

    scene_renderer.textures.get_special_texture = recording_get_special_texture

    scene_renderer._render_special_tile(WarpPoint(), rect, darkness=0.0, depth=1)
    scene_renderer._render_special_tile(WarpPoint(), rect, darkness=0.0, depth=2)

    warp_sizes = [size for texture_key, size in special_calls if texture_key == "warp_point_active"]
    assert warp_sizes[0] > warp_sizes[1]

    pygame.quit()


def test_scene_renderer_renders_current_tile_warp_point_on_front_floor_band():
    pygame.init()
    screen = pygame.display.set_mode((640, 480))
    presenter = DummyPresenter(width=640, height=480, screen=screen)
    scene_renderer = SceneRenderer(presenter, TextureLibrary())
    scene_renderer.player_char = DummyPlayer(location_z=1, warp_point=True)
    world = {
        (0, 0, 1): WarpPoint(),
        (1, 0, 1): OpenTile(),
        (2, 0, 1): OpenTile(),
        (0, -1, 1): OpenTile(),
        (0, 1, 1): OpenTile(),
        (1, -1, 1): OpenTile(),
        (1, 1, 1): OpenTile(),
        (2, -1, 1): OpenTile(),
        (2, 1, 1): OpenTile(),
    }

    teleporter_rect = None
    original_render_center_floor_warp_point = scene_renderer._render_center_floor_warp_point

    def recording_render_center_floor_warp_point(quad, darkness, depth):
        nonlocal teleporter_rect
        sprite = scene_renderer._trim_transparent_sprite(
            scene_renderer.textures.get_special_texture(scene_renderer._warp_point_sprite_key())
        )
        teleporter_rect = scene_renderer._get_center_floor_warp_point_rect(quad, sprite)
        return original_render_center_floor_warp_point(quad, darkness, depth)

    scene_renderer._render_center_floor_warp_point = recording_render_center_floor_warp_point

    try:
        player = DummyPlayer(location_z=1, warp_point=True)
        scene_renderer.render(player, world)
    finally:
        scene_renderer._render_center_floor_warp_point = original_render_center_floor_warp_point

    assert teleporter_rect is not None

    view_w, view_h = scene_renderer._get_viewport_size()
    zone = build_zone_geometry(
        build_depth_rect(view_w, view_h, 1),
        build_next_depth_rect(build_depth_rect(view_w, view_h, 1)),
        depth=1,
    )
    slot_quad = scene_renderer._get_center_floor_slot_quad(zone, depth=1, slot_suffix="x0")
    sprite = scene_renderer._trim_transparent_sprite(
        scene_renderer.textures.get_special_texture(scene_renderer._warp_point_sprite_key())
    )
    expected_rect = scene_renderer._get_center_floor_warp_point_rect(slot_quad, sprite)
    assert teleporter_rect == expected_rect

    slot_bounds = slot_quad.bounding_rect()
    assert teleporter_rect.width == round(slot_bounds.w * 0.66)
    assert teleporter_rect.height == round(slot_bounds.h)
    assert teleporter_rect.centerx == round(slot_bounds.x + (slot_bounds.w / 2.0))
    assert teleporter_rect.bottom == round(slot_bounds.y + slot_bounds.h)

    pygame.quit()


def test_scene_renderer_does_not_route_warp_point_to_floor_texture_override():
    pygame.init()
    screen = pygame.display.set_mode((640, 480))
    presenter = DummyPresenter(width=640, height=480, screen=screen)
    scene_renderer = SceneRenderer(presenter, TextureLibrary())
    player = DummyPlayer()
    world = {
        (0, 0, 1): OpenTile(),
        (1, 0, 1): WarpPoint(),
        (2, 0, 1): OpenTile(),
        (0, -1, 1): OpenTile(),
        (0, 1, 1): OpenTile(),
        (1, -1, 1): OpenTile(),
        (1, 1, 1): OpenTile(),
        (2, -1, 1): OpenTile(),
        (2, 1, 1): OpenTile(),
    }

    commands, _ = _build_scene_commands(scene_renderer, player, world)

    assert not any(command.texture_key == "floor_teleporter" for command in commands)

    pygame.quit()


def test_scene_renderer_renders_secret_shop_overlay_in_center_view():
    pygame.init()
    screen = pygame.display.set_mode((640, 480))
    presenter = DummyPresenter(width=640, height=480, screen=screen)
    scene_renderer = SceneRenderer(presenter, TextureLibrary())
    player = DummyPlayer()
    world = {
        (0, 0, 1): OpenTile(),
        (1, 0, 1): SecretShop(),
        (0, -1, 1): OpenTile(),
        (0, 1, 1): OpenTile(),
    }

    calls = []
    original_get_special_texture = scene_renderer.textures.get_special_texture

    def recording_get_special_texture(texture_key, size=None):
        calls.append((texture_key, size))
        return original_get_special_texture(texture_key, size)

    scene_renderer.textures.get_special_texture = recording_get_special_texture

    scene_renderer.render(player, world)

    assert ("secret_shop", None) in calls

    pygame.quit()


def test_scene_renderer_treats_secret_shop_like_center_floor_overlay_for_structure():
    pygame.init()
    screen = pygame.display.set_mode((640, 480))
    presenter = DummyPresenter(width=640, height=480, screen=screen)
    scene_renderer = SceneRenderer(presenter, TextureLibrary())
    player = DummyPlayer()
    world = {
        (0, 0, 1): OpenTile(),
        (1, 0, 1): SecretShop(),
        (2, 0, 1): WallTile(),
        (0, -1, 1): OpenTile(),
        (0, 1, 1): WallTile(),
        (1, -1, 1): OpenTile(),
        (1, 1, 1): WallTile(),
        (2, -1, 1): OpenTile(),
        (2, 1, 1): WallTile(),
    }

    commands, _ = _build_scene_commands(scene_renderer, player, world)

    assert not any(command.panel_id == "d1:back_wall" for command in commands)
    assert any(command.panel_id == "d2:back_wall" for command in commands)

    rendered_tiles = []
    original_render_special_tile = scene_renderer._render_special_tile

    def recording_render_special_tile(tile, rect, darkness, depth, side=None, lateral_view=False):
        rendered_tiles.append((type(tile).__name__ if tile else None, depth, side, lateral_view))
        return original_render_special_tile(
            tile,
            rect,
            darkness,
            depth,
            side=side,
            lateral_view=lateral_view,
        )

    scene_renderer._render_special_tile = recording_render_special_tile

    scene_renderer.render(player, world)

    assert ("SecretShop", 1, None, False) in rendered_tiles

    pygame.quit()


def test_scene_renderer_routes_side_ladder_ceiling_through_center_ceiling_slot_override():
    pygame.init()
    screen = pygame.display.set_mode((640, 480))
    presenter = DummyPresenter(width=640, height=480, screen=screen)
    scene_renderer = SceneRenderer(presenter, TextureLibrary())
    player = DummyPlayer()
    world = {
        (0, 0, 1): OpenTile(),
        (1, 0, 1): WallTile(),
        (0, -1, 1): WallTile(),
        (1, -1, 1): WallTile(),
        (0, 1, 1): OpenTile(),
        (1, 1, 1): LadderUp(),
    }

    calls = []
    original_get_projected_surface = scene_renderer.textures.get_projected_surface

    def recording_get_projected_surface(panel_id, texture_key, quad, darkness, view_size):
        calls.append((panel_id, texture_key))
        return original_get_projected_surface(panel_id, texture_key, quad, darkness, view_size)

    scene_renderer.textures.get_projected_surface = recording_get_projected_surface

    scene_renderer.render(player, world)

    assert ("d2:center_ceiling_slot3", "ceiling_pit") in calls
    assert ("d2:center_ceiling", "ceiling") not in calls
    assert not any(panel_id == "d1:right_opening_special_ceiling" for panel_id, _ in calls)
    assert scene_renderer.textures.get_surface_slot_overrides() == {
        "ceiling:visible:d2:xp1": "ceiling_pit",
    }

    pygame.quit()


def test_scene_renderer_routes_left_side_ladder_ceiling_through_center_ceiling_slot_override():
    pygame.init()
    screen = pygame.display.set_mode((640, 480))
    presenter = DummyPresenter(width=640, height=480, screen=screen)
    scene_renderer = SceneRenderer(presenter, TextureLibrary())
    player = DummyPlayer()
    world = {
        (0, 0, 1): OpenTile(),
        (1, 0, 1): WallTile(),
        (0, 1, 1): WallTile(),
        (1, 1, 1): WallTile(),
        (0, -1, 1): OpenTile(),
        (1, -1, 1): LadderUp(),
    }

    calls = []
    original_get_projected_surface = scene_renderer.textures.get_projected_surface

    def recording_get_projected_surface(panel_id, texture_key, quad, darkness, view_size):
        calls.append((panel_id, texture_key))
        return original_get_projected_surface(panel_id, texture_key, quad, darkness, view_size)

    scene_renderer.textures.get_projected_surface = recording_get_projected_surface

    scene_renderer.render(player, world)

    assert ("d2:center_ceiling_slot1", "ceiling_pit") in calls
    assert ("d2:center_ceiling", "ceiling") not in calls
    assert not any(panel_id == "d1:left_opening_special_ceiling" for panel_id, _ in calls)
    assert scene_renderer.textures.get_surface_slot_overrides() == {
        "ceiling:visible:d2:xm1": "ceiling_pit",
    }

    pygame.quit()


def test_scene_renderer_keeps_side_ladder_up_surface_only_at_all_visible_depths():
    for side in ("left", "right"):
        for side_depth in (1, 2, 3):
            calls, rendered_tiles, overrides = _render_side_forward_tile_case(
                LadderUp(), side, side_depth
            )
            assert ("LadderUp", side_depth, side, True) not in rendered_tiles

            if side_depth == 3:
                assert not any(texture_key == "ceiling_pit" for _panel_id, texture_key in calls)
                assert overrides == {}
                continue

            surface_depth = side_depth + 1
            slot_suffix = "xm1" if side == "left" else "xp1"
            assert overrides == {
                f"ceiling:visible:d{surface_depth}:{slot_suffix}": "ceiling_pit",
            }
            assert any(
                panel_id.startswith(f"d{surface_depth}:center_ceiling_slot")
                and texture_key == "ceiling_pit"
                for panel_id, texture_key in calls
            )


def test_scene_renderer_routes_side_wall_through_wall_slot_commands():
    pygame.init()
    screen = pygame.display.set_mode((640, 480))
    presenter = DummyPresenter(width=640, height=480, screen=screen)
    scene_renderer = SceneRenderer(presenter, TextureLibrary())
    scene_renderer.textures.set_wall_slot_override(
        "wall:visible:d1:right:right:near", "floor_funhouse"
    )
    player = DummyPlayer()
    world = {
        (0, 0, 1): OpenTile(),
        (1, 0, 1): OpenTile(),
        (0, -1, 1): OpenTile(),
        (1, -1, 1): OpenTile(),
        (0, 1, 1): WallTile(),
        (1, 1, 1): WallTile(),
    }

    calls = []
    original_get_projected_surface = scene_renderer.textures.get_projected_surface

    def recording_get_projected_surface(panel_id, texture_key, quad, darkness, view_size):
        calls.append((panel_id, texture_key))
        return original_get_projected_surface(panel_id, texture_key, quad, darkness, view_size)

    scene_renderer.textures.get_projected_surface = recording_get_projected_surface

    scene_renderer.render(player, world)

    assert ("d1:right_wall_slot0", "floor_funhouse") in calls
    assert ("d1:right_wall_slot1", "wall") in calls
    assert ("d1:right_wall", "wall") not in calls

    pygame.quit()


def test_scene_renderer_renders_adjacent_side_wall_door_through_wall_slots():
    pygame.init()
    screen = pygame.display.set_mode((640, 480))
    presenter = DummyPresenter(width=640, height=480, screen=screen)
    scene_renderer = SceneRenderer(presenter, TextureLibrary())
    player = DummyPlayer()
    world = {
        (0, 0, 1): OpenTile(),
        (1, 0, 1): OpenTile(),
        (0, -1, 1): OpenTile(),
        (1, -1, 1): OpenTile(),
        (0, 1, 1): LockedDoor(),
        (1, 1, 1): WallTile(),
    }

    calls = []
    original_get_projected_surface = scene_renderer.textures.get_projected_surface

    def recording_get_projected_surface(panel_id, texture_key, quad, darkness, view_size):
        calls.append((panel_id, texture_key))
        return original_get_projected_surface(panel_id, texture_key, quad, darkness, view_size)

    scene_renderer.textures.get_projected_surface = recording_get_projected_surface

    scene_renderer.render(player, world)

    assert ("d1:right_wall", "door_closed") in calls
    assert ("d1:right_wall_slot0", "door_closed") not in calls
    assert ("d1:right_wall_slot1", "door_closed") not in calls

    pygame.quit()


def test_scene_renderer_open_adjacent_side_wall_door_keeps_side_blocker_visible():
    pygame.init()
    screen = pygame.display.set_mode((640, 480))
    presenter = DummyPresenter(width=640, height=480, screen=screen)
    scene_renderer = SceneRenderer(presenter, TextureLibrary())
    player = DummyPlayer()
    world = {
        (0, 0, 1): OpenTile(),
        (1, 0, 1): OpenTile(),
        (0, -1, 1): OpenTile(),
        (1, -1, 1): OpenTile(),
        (0, 1, 1): OpenDoor(),
        (1, 1, 1): WallTile(),
    }

    calls = []
    original_get_projected_surface = scene_renderer.textures.get_projected_surface

    def recording_get_projected_surface(panel_id, texture_key, quad, darkness, view_size):
        calls.append((panel_id, texture_key))
        return original_get_projected_surface(panel_id, texture_key, quad, darkness, view_size)

    scene_renderer.textures.get_projected_surface = recording_get_projected_surface

    scene_renderer.render(player, world)

    assert ("d1:right_wall", "door_open") in calls
    assert ("d1:right_blocker", "wall") in calls

    pygame.quit()
