"""Native-resolution display configuration and responsive layout metrics.

The reference size is a layout vocabulary only. It is never used as an
intermediate render surface: Pygame draws directly to the active display.
"""

from __future__ import annotations

from dataclasses import dataclass

REFERENCE_SIZE = (1024, 768)


@dataclass(frozen=True)
class DisplayConfiguration:
    """The active native Pygame render target and its layout characteristics."""

    fullscreen: bool
    render_size: tuple[int, int]
    physical_viewport: tuple[int, int]
    aspect_ratio: float
    ui_scale: float
    layout_mode: str

    @classmethod
    def for_viewport(
        cls,
        *,
        fullscreen: bool,
        render_size: tuple[int, int],
        physical_viewport: tuple[int, int] | None = None,
    ) -> "DisplayConfiguration":
        """Build a configuration for a display that is rendered natively."""
        width, height = render_size
        if width <= 0 or height <= 0:
            raise ValueError("render_size must contain positive dimensions")
        viewport = physical_viewport or render_size
        aspect_ratio = width / height
        reference_width, reference_height = REFERENCE_SIZE
        ui_scale = min(width / reference_width, height / reference_height)
        if aspect_ratio <= 1.45:
            layout_mode = "desktop_4_3"
        elif aspect_ratio <= 1.9:
            layout_mode = "landscape"
        else:
            layout_mode = "extra_wide_landscape"
        return cls(
            fullscreen=fullscreen,
            render_size=render_size,
            physical_viewport=viewport,
            aspect_ratio=aspect_ratio,
            ui_scale=ui_scale,
            layout_mode=layout_mode,
        )


@dataclass(frozen=True)
class LayoutMetrics:
    """Convert reference layout units into native pixels for one viewport."""

    display: DisplayConfiguration

    def unit(self, reference_pixels: float, *, minimum: int = 1) -> int:
        """Return a scaled native-pixel layout measurement."""
        return max(minimum, round(reference_pixels * self.display.ui_scale))

    def font_size(self, reference_points: float, *, minimum: int = 10) -> int:
        """Return a native font size; text is rendered at this size directly."""
        return self.unit(reference_points, minimum=minimum)

    def stroke(self, reference_pixels: float = 1) -> int:
        """Return a visible native-pixel primitive stroke width."""
        return self.unit(reference_pixels)

    @property
    def dungeon_hud_fraction(self) -> float:
        """Reserve a compact right-side HUD on wider dungeon layouts."""
        if self.display.layout_mode == "extra_wide_landscape":
            return 0.28
        if self.display.layout_mode == "landscape":
            return 0.31
        return 0.35

    @property
    def dungeon_view_fraction(self) -> float:
        """Return the native viewport fraction used by first-person dungeon art."""
        return 1.0 - self.dungeon_hud_fraction

    def pointer_position(self, position: tuple[int, int]) -> tuple[int, int] | None:
        """Validate a native pointer position against the active render target."""
        x, y = position
        width, height = self.display.render_size
        if not 0 <= x < width or not 0 <= y < height:
            return None
        return x, y
