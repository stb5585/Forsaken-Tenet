"""Compatibility exports for Pygame dungeon geometry callers.

The geometry itself is renderer-neutral and lives in :mod:`src.ui_common.dungeon`.
"""

from src.ui_common.dungeon.geometry import (
    Quad,
    RectF,
    ZoneGeometry,
    build_depth_rect,
    build_next_depth_rect,
    build_zone_geometry,
)

__all__ = [
    "Quad",
    "RectF",
    "ZoneGeometry",
    "build_depth_rect",
    "build_next_depth_rect",
    "build_zone_geometry",
]
