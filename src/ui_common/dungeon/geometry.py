"""Geometry used to project the dungeon scene in any front end."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class RectF:
    """An immutable floating-point rectangle."""

    x: float
    y: float
    w: float
    h: float

    @property
    def left(self) -> float:
        return self.x

    @property
    def top(self) -> float:
        return self.y

    @property
    def right(self) -> float:
        return self.x + self.w

    @property
    def bottom(self) -> float:
        return self.y + self.h

    def to_int_tuple(self) -> tuple[int, int, int, int]:
        return (round(self.x), round(self.y), round(self.w), round(self.h))


@dataclass(frozen=True)
class Quad:
    """A four-point polygon used by perspective rendering."""

    points: tuple[
        tuple[float, float], tuple[float, float], tuple[float, float], tuple[float, float]
    ]

    @classmethod
    def from_rect(cls, rect: RectF) -> Quad:
        return cls(
            (
                (rect.left, rect.top),
                (rect.right, rect.top),
                (rect.right, rect.bottom),
                (rect.left, rect.bottom),
            )
        )

    def as_int_points(self) -> list[tuple[int, int]]:
        return [(round(x), round(y)) for x, y in self.points]

    def bounding_rect(self) -> RectF:
        xs = [x for x, _ in self.points]
        ys = [y for _, y in self.points]
        return RectF(min(xs), min(ys), max(xs) - min(xs), max(ys) - min(ys))


@dataclass(frozen=True)
class ZoneGeometry:
    """The perspective surfaces for one visible dungeon depth."""

    depth: int
    rect: RectF
    next_rect: RectF
    center_floor: Quad
    center_floor_left: Quad
    center_floor_right: Quad
    left_floor_open: Quad
    right_floor_open: Quad
    center_ceiling: Quad
    center_ceiling_left: Quad
    center_ceiling_right: Quad
    left_ceiling_open: Quad
    right_ceiling_open: Quad
    left_wall: Quad
    right_wall: Quad
    back_wall_rect: RectF
    left_side_blocker_rect: RectF
    right_side_blocker_rect: RectF


def build_depth_rect(view_w: int, view_h: int, depth: int) -> RectF:
    """Return the nested depth rectangle for the given screen size."""
    if depth < 1:
        raise ValueError("depth must be >= 1")

    divisor = 2 ** (depth - 1)
    width = view_w // divisor
    height = view_h // divisor
    return RectF((view_w - width) // 2, (view_h - height) // 2, width, height)


def build_next_depth_rect(rect: RectF) -> RectF:
    """Return the centered next depth rectangle nested within the current one."""
    width = int(rect.w) // 2
    height = int(rect.h) // 2
    x = int(rect.x) + (int(rect.w) - width) // 2
    y = int(rect.y) + (int(rect.h) - height) // 2
    return RectF(x, y, width, height)


def build_zone_geometry(rect: RectF, next_rect: RectF, depth: int = 0) -> ZoneGeometry:
    """Build the fixed quads used to render one depth layer."""
    x, y, w, h = int(rect.x), int(rect.y), int(rect.w), int(rect.h)
    nx, ny, nw, nh = int(next_rect.x), int(next_rect.y), int(next_rect.w), int(next_rect.h)

    left_w = w // 4
    center_w = w // 2
    right_w = w - left_w - center_w
    next_left_w = nw // 4
    next_center_w = nw // 2
    top_h = h // 4
    center_h = h // 2

    front_center_left = x + left_w
    front_center_mid = x + left_w + (center_w // 2)
    front_center_right = x + left_w + center_w
    back_center_left = nx + next_left_w
    back_center_mid = nx + next_left_w + (next_center_w // 2)
    back_center_right = nx + next_left_w + next_center_w

    front_overscan = max(1, depth) * w
    back_overscan = max(1, depth) * nw
    front_overscan_left = x - front_overscan
    front_overscan_right = x + w + front_overscan
    back_overscan_left = nx - back_overscan
    back_overscan_right = nx + nw + back_overscan

    center_floor = Quad(
        (
            (front_overscan_left, y + h),
            (front_overscan_right, y + h),
            (back_overscan_right, ny + nh),
            (back_overscan_left, ny + nh),
        )
    )
    center_floor_left = Quad(
        (
            (front_center_left, y + h),
            (front_center_mid, y + h),
            (back_center_mid, ny + nh),
            (back_center_left, ny + nh),
        )
    )
    center_floor_right = Quad(
        (
            (front_center_mid, y + h),
            (front_center_right, y + h),
            (back_center_right, ny + nh),
            (back_center_mid, ny + nh),
        )
    )
    left_floor_open = Quad(
        (
            (x, y + h),
            (front_center_left, y + h),
            (back_center_left, ny + nh),
            (nx, ny + nh),
        )
    )
    right_floor_open = Quad(
        (
            (front_center_right, y + h),
            (x + w, y + h),
            (nx + nw, ny + nh),
            (back_center_right, ny + nh),
        )
    )
    center_ceiling = Quad(
        (
            (front_overscan_left, y),
            (front_overscan_right, y),
            (back_overscan_right, ny),
            (back_overscan_left, ny),
        )
    )
    center_ceiling_left = Quad(
        (
            (front_center_left, y),
            (front_center_mid, y),
            (back_center_mid, ny),
            (back_center_left, ny),
        )
    )
    center_ceiling_right = Quad(
        (
            (front_center_mid, y),
            (front_center_right, y),
            (back_center_right, ny),
            (back_center_mid, ny),
        )
    )
    left_ceiling_open = Quad(((x, y), (front_center_left, y), (back_center_left, ny), (nx, ny)))
    right_ceiling_open = Quad(
        ((front_center_right, y), (x + w, y), (nx + nw, ny), (back_center_right, ny))
    )
    left_wall = Quad(
        (
            (x, y),
            (front_center_left, y + top_h),
            (front_center_left, y + top_h + center_h),
            (x, y + h),
        )
    )
    right_wall = Quad(
        (
            (front_center_right, y + top_h),
            (x + w, y),
            (x + w, y + h),
            (front_center_right, y + top_h + center_h),
        )
    )

    return ZoneGeometry(
        depth=depth,
        rect=rect,
        next_rect=next_rect,
        center_floor=center_floor,
        center_floor_left=center_floor_left,
        center_floor_right=center_floor_right,
        left_floor_open=left_floor_open,
        right_floor_open=right_floor_open,
        center_ceiling=center_ceiling,
        center_ceiling_left=center_ceiling_left,
        center_ceiling_right=center_ceiling_right,
        left_ceiling_open=left_ceiling_open,
        right_ceiling_open=right_ceiling_open,
        left_wall=left_wall,
        right_wall=right_wall,
        back_wall_rect=next_rect,
        left_side_blocker_rect=RectF(x - left_w, y + top_h, left_w * 2, center_h),
        right_side_blocker_rect=RectF(x + left_w + center_w, y + top_h, right_w * 2, center_h),
    )
