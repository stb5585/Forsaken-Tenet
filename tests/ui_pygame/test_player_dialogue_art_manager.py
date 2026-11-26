"""Coverage for appearance-matched full-body player dialogue art."""

import json
from pathlib import Path

import pygame

from src.ui_pygame.assets.player_dialogue_art_manager import PlayerDialogueArtManager
from src.ui_pygame.assets.portrait_manager import PortraitManager

EXPECTED_APPEARANCE_IDS = {
    f"{race}_{sex}_{variant}"
    for race in ("human", "elf", "half_elf", "half_giant", "gnome", "dwarf", "half_orc")
    for sex in ("male", "female")
    for variant in range(1, 6)
}


def test_dialogue_art_uses_face_portrait_appearance_id(tmp_path: Path):
    mapping_path = tmp_path / "dialogue_art_map.json"
    mapping_path.write_text(
        json.dumps(
            {
                "assets": {"human_male_5": "hero.png"},
                "facing": {"human_male_5": "right"},
            }
        ),
        encoding="utf-8",
    )
    surface = pygame.Surface((32, 64), pygame.SRCALPHA)
    surface.fill((20, 40, 60, 255))
    pygame.image.save(surface, tmp_path / "hero.png")
    manager = PlayerDialogueArtManager(tmp_path, mapping_path=mapping_path)

    assert PortraitManager.appearance_id("Human", "Male", 4) == "human_male_5"
    assert manager.appearance_id("Human", "Male", 4) == "human_male_5"
    assert manager.image_path("Human", "Male", 4) == tmp_path / "hero.png"
    assert manager.get_portrait("Human", "Male", variant=4).get_size() == (32, 64)
    assert manager.should_mirror("Human", "Male", variant=4, stage_side="right")
    assert not manager.should_mirror("Human", "Male", variant=4, stage_side="left")


def test_unpopulated_dialogue_appearance_has_no_face_or_generic_fallback(tmp_path: Path):
    mapping_path = tmp_path / "dialogue_art_map.json"
    mapping_path.write_text(json.dumps({"assets": {}}), encoding="utf-8")
    manager = PlayerDialogueArtManager(tmp_path, mapping_path=mapping_path)

    assert manager.image_path("Elf", "Female", 2) is None
    assert manager.get_portrait("Elf", "Female", variant=2) is None
    assert not manager.should_mirror("Elf", "Female", variant=2, stage_side="right")


def test_committed_dialogue_assets_cover_every_playable_appearance():
    manager = PlayerDialogueArtManager()

    assert set(manager.assets) == EXPECTED_APPEARANCE_IDS
    assert set(manager.facing) == EXPECTED_APPEARANCE_IDS
    for appearance_id, filename in manager.assets.items():
        path = manager.art_root / filename
        assert path.is_file(), appearance_id
        surface = pygame.image.load(path)
        assert surface.get_size() == (512, 1068), appearance_id
        assert surface.get_masks()[3] != 0, appearance_id
        assert surface.get_at((0, 0)).a == 0, appearance_id
        assert surface.get_bounding_rect(min_alpha=1).height > 1000, appearance_id
