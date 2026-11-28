"""Stage display-sized PNGs for the desktop distribution."""

from pathlib import Path

from PIL import Image

RUNTIME_ART_BOUNDS = {
    "item_art": (640, 512),
    "enemy_combat_sprites": (768, 900),
    "player_dialogue": (512, 840),
}


def stage_runtime_art(source: Path, destination: str, stage_root: Path) -> Path:
    """Return the staged PNG when the bundled art exceeds its display bounds."""
    if source.suffix.lower() != ".png":
        return source

    asset_group = Path(destination).name
    # Item artwork uses nested category directories in the bundle.
    if "item_art" in Path(destination).parts:
        asset_group = "item_art"
    bounds = RUNTIME_ART_BOUNDS.get(asset_group)
    if bounds is None:
        return source
    if asset_group == "enemy_combat_sprites" and source.name == "vesperion.png":
        bounds = (1024, 1280)

    with Image.open(source) as image:
        if image.width <= bounds[0] and image.height <= bounds[1]:
            return source
        runtime_image = image.convert("RGBA")
        runtime_image.thumbnail(bounds, Image.Resampling.LANCZOS)
        staged = stage_root / destination / source.name
        staged.parent.mkdir(parents=True, exist_ok=True)
        runtime_image.save(staged, optimize=True)
    return staged
