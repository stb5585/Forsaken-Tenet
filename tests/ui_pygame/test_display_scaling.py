"""Tests for native-resolution display configuration and layout metrics."""

import pytest

from src.ui_pygame.display_scaling import DisplayConfiguration, LayoutMetrics


def test_landscape_configuration_uses_native_render_resolution() -> None:
    display = DisplayConfiguration.for_viewport(
        fullscreen=True, render_size=(1366, 768), physical_viewport=(1366, 768)
    )

    assert display.render_size == (1366, 768)
    assert display.physical_viewport == (1366, 768)
    assert display.ui_scale == 1
    assert display.layout_mode == "landscape"


def test_1080p_metrics_scale_native_fonts_primitives_and_pointer_targets() -> None:
    display = DisplayConfiguration.for_viewport(fullscreen=True, render_size=(1920, 1080))
    metrics = LayoutMetrics(display)

    assert display.ui_scale == pytest.approx(1080 / 768)
    assert metrics.font_size(24) == 34
    assert metrics.unit(56) == 79
    assert metrics.dungeon_hud_fraction == 0.31
    assert metrics.pointer_position((1919, 1079)) == (1919, 1079)
    assert metrics.pointer_position((1920, 100)) is None


def test_extra_wide_layout_reserves_more_native_space_for_dungeon_view() -> None:
    metrics = LayoutMetrics(
        DisplayConfiguration.for_viewport(fullscreen=True, render_size=(2340, 1080))
    )

    assert metrics.display.layout_mode == "extra_wide_landscape"
    assert metrics.dungeon_hud_fraction == 0.28
    assert metrics.dungeon_view_fraction == 0.72
