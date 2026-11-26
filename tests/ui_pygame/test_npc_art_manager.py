#!/usr/bin/env python3
"""Coverage for NPC dialogue portrait asset resolution."""

from __future__ import annotations

import json

from PIL import Image

from src.ui_pygame.assets.npc_art_manager import NpcArtManager
from tools import build_npc_art_sheet

V1_NPC_KEYS = {
    "alchemist",
    "barkeep",
    "busboy",
    "drunkard",
    "griswold",
    "hooded_figure",
    "jeweler",
    "mara_vale",
    "nimue",
    "old_warehouse_guard",
    "priest",
    "seraphine_voss",
    "soldier",
    "waitress",
    "warp_point_scientist",
    "gray_broker",
}

V2_NPC_KEYS = {
    "acolyte",
    "reflection",
    "vesperion",
}

OPAQUE_BACKGROUND_REPLACEMENT_KEYS = {
    "gray_broker",
    "mara_vale",
    "seraphine_voss",
}


def _write_png(path):
    Image.new("RGBA", (32, 48), (180, 120, 80, 255)).save(path)


def _edge_transparency_ratio(alpha) -> float:
    width, height = alpha.size
    edge_values = []
    for x in range(width):
        edge_values.append(alpha.getpixel((x, 0)))
        edge_values.append(alpha.getpixel((x, height - 1)))
    for y in range(height):
        edge_values.append(alpha.getpixel((0, y)))
        edge_values.append(alpha.getpixel((width - 1, y)))
    return sum(value == 0 for value in edge_values) / len(edge_values)


def test_npc_art_manager_resolves_mapped_paths_and_aliases(tmp_path):
    art_root = tmp_path / "npc_art"
    art_root.mkdir()
    _write_png(art_root / "sergeant.png")
    _write_png(art_root / "hooded_figure.png")
    map_path = art_root / "npc_art_map.json"
    map_path.write_text(
        json.dumps({"Sergeant": "sergeant", "The Hooded Figure": "hooded_figure"}),
        encoding="utf-8",
    )
    facing_path = art_root / "npc_art_facing.json"
    facing_path.write_text(json.dumps({"sergeant": "right"}), encoding="utf-8")

    manager = NpcArtManager(
        art_root=art_root,
        art_map_path=map_path,
        facing_map_path=facing_path,
    )

    assert manager.get_image_path("Sergeant") == str(art_root / "sergeant.png")
    assert manager.get_image_path("The Hooded Figure") == str(art_root / "hooded_figure.png")
    assert manager.get_image_path("Hooded Figure") == str(art_root / "hooded_figure.png")
    assert manager.should_mirror("Sergeant", stage_side="right")
    assert not manager.should_mirror("Sergeant", stage_side="left")
    assert not manager.should_mirror("The Hooded Figure", stage_side="right")


def test_liora_faces_inward_on_either_side_of_dialogue_stage():
    manager = NpcArtManager()

    assert not manager.should_mirror("Liora", stage_side="left")
    assert manager.should_mirror("Liora", stage_side="right")


def test_npc_art_manager_tolerates_missing_map_and_missing_files(tmp_path):
    art_root = tmp_path / "npc_art"
    art_root.mkdir()

    missing_map = NpcArtManager(art_root=art_root, art_map_path=art_root / "missing.json")
    assert missing_map.get_image_path("Sergeant") == ""

    map_path = art_root / "npc_art_map.json"
    map_path.write_text(json.dumps({"Sergeant": "sergeant"}), encoding="utf-8")
    manager = NpcArtManager(art_root=art_root, art_map_path=map_path)
    assert manager.get_image_path("Sergeant") == ""

    _write_png(art_root / "sergeant.png")
    manager.clear_cache()
    assert manager.get_image_path("Sergeant") == str(art_root / "sergeant.png")


def test_default_npc_art_map_covers_v1_dialogue_npcs():
    art_root = build_npc_art_sheet.DEFAULT_ART_ROOT
    map_path = art_root / "npc_art_map.json"
    data = json.loads(map_path.read_text(encoding="utf-8"))
    manager = NpcArtManager(art_root=art_root, art_map_path=map_path)

    assert V1_NPC_KEYS.issubset(set(data.values()))
    assert manager.get_image_path("Old Warehouse Guard").endswith("old_warehouse_guard.png")
    assert manager.get_image_path("Warehouse Guard").endswith("old_warehouse_guard.png")
    assert manager.get_image_path("Warp Point Scientist").endswith("warp_point_scientist.png")
    assert manager.get_image_path("Staffed Warp Point Scientist").endswith(
        "warp_point_scientist.png"
    )
    assert manager.get_image_path("Mara Vale").endswith("mara_vale.png")
    assert manager.get_image_path("The Gray Broker").endswith("gray_broker.png")
    assert manager.get_image_path("Seraphine Voss").endswith("seraphine_voss.png")


def test_default_npc_art_map_covers_v2_story_npcs():
    art_root = build_npc_art_sheet.DEFAULT_ART_ROOT
    map_path = art_root / "npc_art_map.json"
    data = json.loads(map_path.read_text(encoding="utf-8"))
    manager = NpcArtManager(art_root=art_root, art_map_path=map_path)

    assert V2_NPC_KEYS.issubset(set(data.values()))
    assert manager.get_image_path("The Acolyte").endswith("acolyte.png")
    assert manager.get_image_path("Acolyte").endswith("acolyte.png")
    assert manager.get_image_path("Reflection").endswith("reflection.png")
    assert manager.get_image_path("Reflection Psychopomp").endswith("reflection.png")
    assert manager.get_image_path("Vesperion").endswith("vesperion.png")


def test_default_npc_art_map_covers_opening_story_aliases():
    art_root = build_npc_art_sheet.DEFAULT_ART_ROOT
    map_path = art_root / "npc_art_map.json"
    manager = NpcArtManager(art_root=art_root, art_map_path=map_path)

    expected = {
        "Caedmon": "caedmon_varr.png",
        "Edrin": "edrin_shaw.png",
        "Joffrey": "joffrey.png",
        "Liora": "waitress.png",
        "Oren": "barkeep.png",
        "Pell": "drunkard.png",
        "Tavin": "busboy.png",
        "Excited Patron": "excited_patron.png",
        "Uneasy Patron": "uneasy_patron.png",
        "Angry Patron": "angry_patron.png",
        "Sergeant": "caedmon_varr.png",
        "Timmy": "timmy.png",
        "Timmy's Mother": "timmy_mother.png",
        "Timmy's Father": "timmy_father.png",
    }
    for character, filename in expected.items():
        assert manager.get_image_path(character).endswith(filename)


def test_default_npc_portraits_use_transparent_cutout_assets():
    art_root = build_npc_art_sheet.DEFAULT_ART_ROOT
    map_path = art_root / "npc_art_map.json"
    data = json.loads(map_path.read_text(encoding="utf-8"))

    for key in set(data.values()):
        path = art_root / f"{key}.png"
        assert path.exists(), key
        with Image.open(path) as image:
            assert image.mode == "RGBA", key
            assert image.size == (512, 768), key
            alpha = image.getchannel("A")
            assert alpha.getbbox() != (0, 0, image.width, image.height), key
            assert _edge_transparency_ratio(alpha) >= 0.5, key

            if key in OPAQUE_BACKGROUND_REPLACEMENT_KEYS:
                corners = [
                    alpha.getpixel((0, 0)),
                    alpha.getpixel((image.width - 1, 0)),
                    alpha.getpixel((0, image.height - 1)),
                    alpha.getpixel((image.width - 1, image.height - 1)),
                ]
                assert corners == [0, 0, 0, 0], key


def test_npc_art_manager_ignores_archived_art_subfolders(tmp_path):
    art_root = tmp_path / "npc_art"
    archive_root = art_root / "old_files"
    archive_root.mkdir(parents=True)
    _write_png(art_root / "sergeant.png")
    _write_png(archive_root / "sergeant_original.png")
    map_path = art_root / "npc_art_map.json"
    map_path.write_text(json.dumps({"Sergeant": "sergeant"}), encoding="utf-8")

    manager = NpcArtManager(art_root=art_root, art_map_path=map_path)

    assert "sergeant_original" not in manager.available_keys
    assert manager.get_image_path("Sergeant") == str(art_root / "sergeant.png")


def test_build_npc_art_review_sheet_smoke(tmp_path):
    art_root = tmp_path / "npc_art"
    art_root.mkdir()
    map_path = art_root / "npc_art_map.json"
    map_path.write_text(json.dumps({"Sergeant": "sergeant", "Priest": "priest"}), encoding="utf-8")
    _write_png(art_root / "sergeant.png")
    _write_png(art_root / "priest.png")
    output = tmp_path / "review.png"

    build_npc_art_sheet.draw_review_sheet(art_root, output, columns=2)

    assert output.exists()
    with Image.open(output) as sheet:
        assert sheet.size[0] > 0
        assert sheet.size[1] > 0
