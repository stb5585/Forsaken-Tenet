"""Backend-independent dungeon rendering instructions."""

from dataclasses import dataclass

from .geometry import Quad


@dataclass(frozen=True)
class RenderCommand:
    """Describe one textured perspective surface for a renderer."""

    depth: int
    order: int
    panel_id: str
    texture_key: str
    quad: Quad
    darkness: float
