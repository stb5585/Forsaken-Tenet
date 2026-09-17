"""Compatibility exports for Pygame dungeon geometry callers.

The geometry itself is renderer-neutral and lives in :mod:`src.ui_common.dungeon`.
"""

from src.ui_common.dungeon.geometry import Quad
from src.ui_common.dungeon.geometry import RectF
from src.ui_common.dungeon.geometry import ZoneGeometry
from src.ui_common.dungeon.geometry import build_depth_rect
from src.ui_common.dungeon.geometry import build_next_depth_rect
from src.ui_common.dungeon.geometry import build_zone_geometry

__all__ = [
    "Quad",
    "RectF",
    "ZoneGeometry",
    "build_depth_rect",
    "build_next_depth_rect",
    "build_zone_geometry",
]
