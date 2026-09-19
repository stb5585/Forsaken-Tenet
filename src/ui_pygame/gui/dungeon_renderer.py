from __future__ import annotations

from time import perf_counter

from .dungeon.assets import TextureLibrary
from .dungeon.overlays import OverlayRenderer
from .dungeon.performance import DungeonPerformanceDiagnostics
from .dungeon.renderer import SceneRenderer


class DungeonRenderer:
    """Facade for the modular dungeon renderer implementation."""

    def __init__(self, presenter, *, performance_diagnostics: bool = False):
        self.presenter = presenter
        self.screen = presenter.screen
        self.width = presenter.width
        self.height = presenter.height
        self.performance_diagnostics = DungeonPerformanceDiagnostics(performance_diagnostics)

        self.textures = TextureLibrary()
        self.scene_renderer = SceneRenderer(presenter, self.textures)
        self.scene_renderer.enable_wall_overlays = True
        self.overlays = OverlayRenderer(presenter)

    def _refresh_screen_refs(self) -> None:
        self.screen = self.presenter.screen
        self.width, self.height = self.screen.get_size()

    def render_dungeon_view(self, player_char, world_dict):
        self._refresh_screen_refs()
        started = perf_counter()
        self.scene_renderer.render(player_char, world_dict)
        self.performance_diagnostics.record("scene", perf_counter() - started)
        self.performance_diagnostics.record_projection_activity(
            *self.textures.consume_projected_cache_activity()
        )
        started = perf_counter()
        self.overlays.render_vignette()
        self.overlays.render_low_health_vignette(player_char)
        self.performance_diagnostics.record("scene-overlay", perf_counter() - started)

    def render_message_area(self, messages, scroll_offset=0, lines_per_page=4):
        self._refresh_screen_refs()
        self.overlays.render_message_area(
            messages, scroll_offset=scroll_offset, lines_per_page=lines_per_page
        )

    def trigger_damage_flash(self, duration_ms=700, alpha=255, color=(255, 32, 16)):
        self.overlays.trigger_damage_flash(duration_ms=duration_ms, alpha=alpha, color=color)

    def render_damage_flash(self):
        self._refresh_screen_refs()
        self.overlays.render_damage_flash()

    def record_ui_and_present(self, ui_elapsed_seconds: float, flip_elapsed_seconds: float) -> None:
        """Record overlay/HUD and display-present timing for the exploration loop."""
        self.performance_diagnostics.record("hud-overlay", ui_elapsed_seconds)
        self.performance_diagnostics.record("display-flip", flip_elapsed_seconds)
        self.performance_diagnostics.report_if_due()
