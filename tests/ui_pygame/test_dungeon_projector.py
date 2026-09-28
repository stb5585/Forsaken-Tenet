from __future__ import annotations

import os

import pygame

from src.ui_pygame.gui.dungeon.geometry import (
    Quad,
    build_depth_rect,
    build_next_depth_rect,
    build_zone_geometry,
)
from src.ui_pygame.gui.dungeon.projector import project_texture_to_quad

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")


def _make_texture() -> pygame.Surface:
    texture = pygame.Surface((128, 128), pygame.SRCALPHA)
    texture.fill((160, 160, 160, 255))
    pygame.draw.rect(texture, (40, 40, 40), (0, 0, 64, 64))
    pygame.draw.rect(texture, (220, 220, 220), (64, 0, 64, 64))
    pygame.draw.rect(texture, (220, 220, 220), (0, 64, 64, 64))
    pygame.draw.rect(texture, (40, 40, 40), (64, 64, 64, 64))
    return texture


def test_project_texture_to_core_panels():
    pygame.init()
    pygame.display.set_mode((1, 1))
    texture = _make_texture()

    for size in [(1024, 600), (1280, 720)]:
        rect = build_depth_rect(size[0], size[1], 1)
        next_rect = build_next_depth_rect(rect)
        zone = build_zone_geometry(rect, next_rect, depth=1)
        for quad in (
            zone.center_floor,
            zone.left_floor_open,
            zone.right_floor_open,
            zone.left_wall,
            zone.right_wall,
        ):
            projected = project_texture_to_quad(texture, quad, darkness=0.2)
            assert projected.surface.get_width() > 0
            assert projected.surface.get_height() > 0
            assert projected.surface.get_bounding_rect().width > 0

    pygame.quit()


def test_project_texture_to_extrapolated_depth3_slot_quad():
    pygame.init()
    pygame.display.set_mode((1, 1))
    texture = _make_texture()

    quad = Quad(
        (
            (-249.4285714286, 288.0),
            (-83.2857142857, 288.0),
            (207.7142857143, 336.0),
            (290.5714285714, 336.0),
        )
    )

    projected = project_texture_to_quad(texture, quad, darkness=0.0)

    assert projected.surface.get_width() > 0
    assert projected.surface.get_height() > 0

    pygame.quit()
