"""Distribution configuration and clean-location startup smoke tests."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]


def test_runtime_resources_live_in_packaged_trees():
    assert (PROJECT_ROOT / "src/core/data/maps/map_level_1.json").is_file()
    assert (PROJECT_ROOT / "src/core/data/maps/dungeon_tiles.tsx").is_file()
    assert (PROJECT_ROOT / "src/ui_pygame/assets/backgrounds/main_menu.png").is_file()
    spec = (PROJECT_ROOT / "packaging/forsaken_tenet.spec").read_text(encoding="utf-8")
    assert 'collect_data_files("src.core.data"' in spec
    assert 'collect_data_files(\n        "src.ui_pygame.assets"' in spec
    assert "review_sheet.png" in spec


def test_headless_startup_from_clean_working_directory(tmp_path):
    environment = os.environ.copy()
    environment.update(
        {
            "SDL_AUDIODRIVER": "dummy",
            "SDL_VIDEODRIVER": "dummy",
            "FORSAKEN_TENET_DATA_DIR": str(tmp_path / "user-data"),
        }
    )

    result = subprocess.run(
        [sys.executable, str(PROJECT_ROOT / "game_pygame.py"), "--smoke-test"],
        cwd=tmp_path,
        env=environment,
        check=False,
        capture_output=True,
        text=True,
        timeout=30,
    )

    assert result.returncode == 0, result.stderr
    assert "Startup smoke test passed." in result.stdout
    assert (tmp_path / "user-data" / "saves").is_dir()


def test_runtime_art_staging_preserves_source_and_bundle_paths(tmp_path):
    from PIL import Image

    from tools.export_runtime_art import stage_runtime_art

    source = tmp_path / "example.png"
    with Image.new("RGBA", (512, 768), (24, 88, 120, 96)) as image:
        image.save(source)
    original = source.read_bytes()
    destination = "src/ui_pygame/assets/item_art/weapons/swords"

    staged = stage_runtime_art(source, destination, tmp_path / "stage")

    assert staged == tmp_path / "stage" / destination / source.name
    with Image.open(staged) as runtime:
        assert runtime.size == (341, 512)
        assert runtime.mode == "RGBA"
        assert runtime.getpixel((0, 0))[3] == 96
    assert source.read_bytes() == original
    assert stage_runtime_art(source, "src/ui_pygame/assets/backgrounds", tmp_path) == source
    assert stage_runtime_art(staged, destination, tmp_path / "second-stage") == staged


def test_runtime_dialogue_art_preserves_full_canvas(tmp_path):
    from PIL import Image

    from tools.export_runtime_art import stage_runtime_art

    source = tmp_path / "portrait.png"
    with Image.new("RGBA", (512, 1068)) as image:
        image.paste((90, 120, 140, 255), (100, 200, 400, 1000))
        image.save(source)

    staged = stage_runtime_art(source, "src/ui_pygame/assets/player_dialogue", tmp_path / "stage")

    with Image.open(staged) as runtime:
        assert runtime.size == (403, 840)
        assert runtime.getpixel((0, 0))[3] == 0
        assert runtime.getpixel((200, 400))[3] == 255
