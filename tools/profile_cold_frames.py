"""Measure first-use rendering work at common dungeon and UI transitions."""

from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from collections.abc import Callable
from contextlib import ExitStack
from statistics import median
from time import perf_counter
from unittest.mock import patch

import pygame

from src.core import enemies, map_tiles
from src.core.player import DIRECTIONS
from src.ui_pygame.assets.enemy_combat_sprite_manager import get_enemy_combat_sprite_manager
from src.ui_pygame.assets.item_render_manager import get_item_render_manager
from src.ui_pygame.assets.npc_art_manager import get_npc_art_manager
from src.ui_pygame.gui.combat_view import CombatView
from src.ui_pygame.gui.dungeon import assets
from src.ui_pygame.gui.dungeon_renderer import DungeonRenderer
from src.ui_pygame.gui.shop_screen import ShopScreen
from src.ui_pygame.gui.story_scene import StoryBeat, StorySceneScreen
from src.ui_pygame.presentation.pygame_presenter import PygamePresenter
from tests.test_framework import TestGameState


class TransitionSamples:
    """Collect wall times and work performed inside each transition."""

    def __init__(self) -> None:
        self.results = defaultdict(list)
        self.calls: Counter[str] = Counter()
        self.work_ms: Counter[str] = Counter()

    def timed(self, name, operation):
        def measure(*args, **kwargs):
            started = perf_counter()
            try:
                return operation(*args, **kwargs)
            finally:
                self.calls[name] += 1
                self.work_ms[name] += (perf_counter() - started) * 1000

        return measure

    def sample(self, name: str, draw: Callable):
        self.calls.clear()
        self.work_ms.clear()
        started = perf_counter()
        value = draw()
        self.results[name].append(
            ((perf_counter() - started) * 1000, self.calls.copy(), self.work_ms.copy())
        )
        return value

    def report(self) -> None:
        print("phase                       median / max ms | median calls and time")
        for name, rows in self.results.items():
            elapsed = [row[0] for row in rows]
            parts = [
                f"{key}={median(row[1][key] for row in rows):g}/"
                f"{median(row[2][key] for row in rows):.1f}ms"
                for key in ("image", "scale", "project")
                if any(row[1][key] for row in rows)
            ]
            print(
                f"{name:27} {median(elapsed):6.1f} / {max(elapsed):6.1f} | {' '.join(parts) or '—'}"
            )


def find_door_view(world):
    """Pick a stable camera position facing an authored locked door."""
    for (x, y, z), tile in sorted(world.items(), key=lambda entry: (entry[0][2], entry[0])):
        if not isinstance(tile, map_tiles.LockedDoor):
            continue
        for facing, direction in DIRECTIONS.items():
            dx, dy = direction["move"]
            position = (x - dx, y - dy, z)
            if isinstance(world.get(position), map_tiles.CavePath):
                return position, facing, tile
    raise RuntimeError("No authored locked door with an adjacent cave path")


def run_session(presenter, samples: TransitionSamples) -> None:
    """Replay dungeon, combat, shop and dialogue draws with fresh relevant caches."""
    enemy_art = get_enemy_combat_sprite_manager()
    get_npc_art_manager().clear_cache()
    get_item_render_manager().clear_cache()
    enemy_art.clear_cache()
    player = TestGameState.create_player()
    player.load_tiles()
    world = player.world_dict
    position, facing, door = find_door_view(world)
    # Normal floor-one spawn used by the town descent.
    player.location_x, player.location_y, player.location_z = (5, 10, 1)
    player.facing = "east"
    renderer = samples.sample("dungeon setup", lambda: DungeonRenderer(presenter))

    def dungeon():
        renderer.render_dungeon_view(player, world)

    samples.sample("dungeon entrance draw", dungeon)
    samples.sample("entrance repeat", dungeon)
    player.location_x, player.location_y, player.location_z = position
    player.facing = facing
    samples.sample("door approach draw", dungeon)
    samples.sample("door approach repeat", dungeon)
    player.turn_left()
    samples.sample("first turn draw", dungeon)
    samples.sample("turned repeat", dungeon)
    player.facing = facing
    door.open = True
    door.locked = False
    samples.sample("opened door draw", dungeon)
    samples.sample("open door repeat", dungeon)

    view = CombatView(presenter.screen, presenter)
    enemy = enemies.Barghest()
    samples.sample("combat art preparation", lambda: view.prepare_enemy_assets(enemy))

    def combat():
        dungeon()
        view.render_enemy_in_dungeon(player, enemy, show_enemy_details=True)

    samples.sample("first combat draw", combat)
    samples.sample("combat repeat", combat)

    shop = samples.sample("shop setup", lambda: ShopScreen(presenter, player, "Shop"))

    def shop_draw():
        shop.draw_selected_item_art(shop.options_rect, "Bastard Sword")

    samples.sample("first item draw", shop_draw)
    samples.sample("item repeat", shop_draw)

    scene = samples.sample(
        "dialogue setup",
        lambda: StorySceneScreen(
            presenter,
            "The Thirsty Dog",
            participants=("Oren", "Liora", "Pell"),
            background_image="tavern.jpg",
            player_char=player,
        ),
    )
    beat = StoryBeat("Oren", "Have a seat.")
    samples.sample("first dialogue draw", lambda: scene.draw_frame(beat, do_flip=False))
    samples.sample("dialogue repeat", lambda: scene.draw_frame(beat, do_flip=False))


def main() -> None:
    """Run a fixed transition sequence at both supported comparison sizes."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repeats", type=int, default=5)
    args = parser.parse_args()
    if args.repeats < 1:
        parser.error("--repeats must be at least 1")

    presenter = PygamePresenter(1024, 768)
    try:
        for width, height in ((1024, 768), (1920, 1080)):
            presenter.apply_display_mode(fullscreen=False, resolution=(width, height))
            samples = TransitionSamples()
            with ExitStack() as stack:
                for module, attribute, name in (
                    (pygame.image, "load", "image"),
                    (pygame.transform, "smoothscale", "scale"),
                    (assets, "project_texture_to_quad", "project"),
                ):
                    stack.enter_context(
                        patch.object(
                            module, attribute, samples.timed(name, getattr(module, attribute))
                        )
                    )
                for _ in range(args.repeats):
                    run_session(presenter, samples)
            print(f"\n{width}×{height}, {args.repeats} sessions")
            samples.report()
    finally:
        pygame.quit()


if __name__ == "__main__":
    main()
