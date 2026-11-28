"""Profile scaled art through repeated shop, combat, and dialogue draws."""

from statistics import median, quantiles
from time import perf_counter
from unittest.mock import patch

import pygame

from src.ui_pygame.assets.enemy_combat_sprite_manager import get_enemy_combat_sprite_manager
from src.ui_pygame.assets.item_render_manager import get_item_render_manager
from src.ui_pygame.gui.combat_view import CombatView
from src.ui_pygame.gui.shop_screen import ShopScreen
from src.ui_pygame.gui.story_scene import StoryBeat, StorySceneScreen
from src.ui_pygame.presentation.pygame_presenter import PygamePresenter
from tests.test_framework import TestGameState


def cache_stats(cache):
    if hasattr(cache, "stats"):
        return cache.stats()
    return {
        "entries": len(cache),
        "bytes": sum(s.get_pitch() * s.get_height() for s in cache.values()),
    }


def main() -> None:
    """Draw an art-heavy session and report cache counts by resolution."""
    presenter = PygamePresenter(1024, 768)
    player = TestGameState.create_player()
    item_art = get_item_render_manager()
    enemy_art = get_enemy_combat_sprite_manager()
    item_names_by_key = {key: name for name, key in item_art.render_map.items()}
    item_names = [item_names_by_key[key] for key in sorted(item_names_by_key)[::4][:32]]
    enemy_names = sorted(enemy_art.available_keys)[::5][:24]
    print(f"{len(item_names)} shop items, {len(enemy_names)} enemy sprites")
    scale = pygame.transform.smoothscale

    def run(entries, draw):
        times = []
        scales = 0

        def count(surface, size):
            nonlocal scales
            scales += 1
            return scale(surface, size)

        with patch.object(pygame.transform, "smoothscale", count):
            for entry in entries:
                start = perf_counter()
                draw(entry)
                times.append((perf_counter() - start) * 1000)
        return (
            f"scales={scales} median_ms={median(times):.2f} p95_ms={quantiles(times, n=20)[18]:.2f}"
        )

    for mode in [(1024, 768), (1280, 720), (1920, 1080), (1024, 768)]:
        presenter.apply_display_mode(fullscreen=False, resolution=mode)
        shop = ShopScreen(presenter, player, "Shop")
        view = CombatView(presenter.screen, presenter)
        print(mode, shop.options_rect.size)

        # Use the same item pane and combat sprite dimensions as the live UI.
        def shop_draw(key):
            shop.draw_selected_item_art(shop.options_rect, key)

        print(
            "items",
            run(item_names + item_names[-8:] * 3, shop_draw),
            cache_stats(item_art._scaled_cache),
        )

        def combat_draw(key):
            size = view._enemy_dungeon_combat_sprite_size(key)
            presenter.screen.blit(enemy_art.get_scaled_sprite_by_key(key, size), (0, 0))

        print(
            "enemies",
            run(enemy_names + enemy_names[-5:] * 4, combat_draw),
            cache_stats(enemy_art._scaled_cache),
        )
        scene = StorySceneScreen(
            presenter,
            "Dialogue",
            participants=("Oren", "Liora", "Pell"),
            background_image="tavern.jpg",
            player_char=player,
        )
        beats = [StoryBeat(name, "The lantern's still lit.") for name in ("Oren", "Liora", "Pell")]
        print(
            "dialogue",
            run(beats * 12, lambda b: scene.draw_frame(b, do_flip=False)),
            cache_stats(getattr(scene, "_scaled_portraits", {})),
        )
    pygame.quit()


if __name__ == "__main__":
    main()
