"""Tests for renderer-neutral dungeon presentation models."""

from src.ui_common.dungeon.geometry import RectF
from src.ui_common.dungeon.geometry import build_depth_rect
from src.ui_common.dungeon.geometry import build_next_depth_rect
from src.ui_common.dungeon.geometry import build_zone_geometry


def test_common_geometry_matches_the_existing_dungeon_projection() -> None:
    rect = build_depth_rect(1024, 600, 1)
    zone = build_zone_geometry(rect, build_next_depth_rect(rect), depth=1)

    assert rect == RectF(0, 0, 1024, 600)
    assert zone.center_floor.points[0][0] < rect.left
    assert zone.center_floor.points[1][0] > rect.right
