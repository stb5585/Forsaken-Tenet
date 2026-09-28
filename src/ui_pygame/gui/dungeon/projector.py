from __future__ import annotations

from dataclasses import dataclass
from math import ceil, floor

import numpy as np
import pygame
from PIL import Image, ImageChops, ImageDraw

from .geometry import Quad


@dataclass(frozen=True)
class ProjectedSurface:
    surface: pygame.Surface
    topleft: tuple[int, int]


def _get_perspective_coeffs(
    source_points: list[tuple[float, float]],
    target_points: list[tuple[float, float]],
) -> tuple[float, ...]:
    matrix = []
    for source, target in zip(source_points, target_points):
        matrix.append(
            [target[0], target[1], 1, 0, 0, 0, -source[0] * target[0], -source[0] * target[1]]
        )
        matrix.append(
            [0, 0, 0, target[0], target[1], 1, -source[1] * target[0], -source[1] * target[1]]
        )

    a_rows = []
    b_rows = []
    for index, row in enumerate(matrix):
        a_rows.append(row)
        b_rows.append(source_points[index // 2][index % 2])

    a = np.array(a_rows, dtype=float)
    b = np.array(b_rows, dtype=float).reshape(8)
    result = np.linalg.solve(a, b)
    return tuple(float(value) for value in result)


def project_texture_to_quad(
    texture: pygame.Surface,
    quad: Quad,
    darkness: float = 0.0,
) -> ProjectedSurface:
    """Project a texture into a local bounding-box surface that contains the quad."""
    points = list(quad.points)
    xs = [x for x, _ in points]
    ys = [y for _, y in points]
    min_x = floor(min(xs))
    min_y = floor(min(ys))
    max_x = ceil(max(xs))
    max_y = ceil(max(ys))
    out_w = max(1, max_x - min_x)
    out_h = max(1, max_y - min_y)

    local_points = [(x - min_x, y - min_y) for x, y in points]

    texture_string = pygame.image.tostring(texture, "RGBA")
    pil_image = Image.frombytes("RGBA", texture.get_size(), texture_string)
    source_points = [
        (0, 0),
        (texture.get_width(), 0),
        (texture.get_width(), texture.get_height()),
        (0, texture.get_height()),
    ]
    try:
        coeffs = _get_perspective_coeffs(source_points, local_points)
    except np.linalg.LinAlgError:
        # Rounded screen-space quads can become numerically singular at extreme
        # slot widths. Returning a transparent surface avoids aborting the frame.
        return ProjectedSurface(
            surface=pygame.Surface((out_w, out_h), pygame.SRCALPHA), topleft=(min_x, min_y)
        )

    transformed = pil_image.transform(
        (out_w, out_h),
        Image.PERSPECTIVE,
        coeffs,
        Image.BICUBIC,
        fillcolor=(0, 0, 0, 0),
    )

    mask = Image.new("L", (out_w, out_h), 0)
    mask_draw = ImageDraw.Draw(mask)
    mask_draw.polygon(local_points, fill=255)
    alpha = ImageChops.multiply(transformed.getchannel("A"), mask)
    transformed.putalpha(alpha)

    surface = pygame.image.fromstring(transformed.tobytes(), transformed.size, transformed.mode)
    if darkness > 0:
        factor = int(255 * max(0.0, 1.0 - min(1.0, darkness)))
        surface.fill((factor, factor, factor, 255), special_flags=pygame.BLEND_RGBA_MULT)

    return ProjectedSurface(surface=surface, topleft=(min_x, min_y))
