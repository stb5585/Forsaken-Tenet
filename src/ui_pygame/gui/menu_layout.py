"""Shared responsive measurements for touch-friendly legacy Pygame menus."""

from __future__ import annotations


def menu_viewport_size(presenter) -> tuple[int, int]:
    """Return the active surface size, falling back to presenter dimensions."""
    get_size = getattr(getattr(presenter, "screen", None), "get_size", None)
    if callable(get_size):
        return get_size()
    return presenter.width, presenter.height


def menu_unit(presenter, reference_pixels: int, minimum: int = 1) -> int:
    """Return a native-pixel menu measurement from the display metrics."""
    metrics = getattr(presenter, "layout_metrics", None)
    if metrics is not None:
        return metrics.unit(reference_pixels, minimum=minimum)
    width, height = menu_viewport_size(presenter)
    return max(minimum, round(reference_pixels * min(width / 1024, height / 768)))


def touch_target_height(presenter) -> int:
    """Return the minimum practical menu-row height for mouse and touch input."""
    return menu_unit(presenter, 54, minimum=48)
