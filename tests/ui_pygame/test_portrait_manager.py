#!/usr/bin/env python3
"""Focused coverage for portrait sheet loading and composition."""

from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

import pygame

from src.ui_pygame.assets.portrait_manager import PortraitManager


def _surface(size=(10, 10), color=(0, 0, 0, 255)):
    surface = pygame.Surface(size, pygame.SRCALPHA)
    surface.fill(color)
    return surface


def _write_sheet_mapping(root: Path, *, frames: dict | None = None) -> Path:
    mapping_json = root / "portrait_atlas_mapping.json"
    default_frames = frames or {
        "male_1": {"x": 0, "y": 0, "w": 10, "h": 10},
        "male_2": {"x": 10, "y": 0, "w": 10, "h": 10},
        "female_1": {"x": 0, "y": 10, "w": 10, "h": 10},
        "female_2": {"x": 10, "y": 10, "w": 10, "h": 10},
    }
    mapping_json.write_text(
        json.dumps(
            {
                "universal_frames": default_frames,
                "sheets": {
                    "human": {
                        "image": "human_base_portraits.png",
                        "frames": {
                            "human_male_1": default_frames["male_1"],
                            "human_male_2": default_frames["male_2"],
                            "human_female_1": default_frames["female_1"],
                            "human_female_2": default_frames["female_2"],
                        },
                    },
                    "half_orc": {
                        "image": "half_orc_base_portraits.png",
                        "uses": "universal_frames",
                    },
                },
            }
        ),
        encoding="utf-8",
    )
    (root / "human_base_portraits.png").touch()
    (root / "half_orc_base_portraits.png").touch()
    return mapping_json


def test_portrait_sheet_mapping_json_loading(tmp_path):
    mapping_json = _write_sheet_mapping(tmp_path)

    manager = PortraitManager(portrait_root=tmp_path, atlas_json=mapping_json)

    assert manager.atlas_image_path == tmp_path / "human_base_portraits.png"
    assert manager.sheet_image_paths["human"] == tmp_path / "human_base_portraits.png"
    assert manager.sheet_image_paths["half_orc"] == tmp_path / "half_orc_base_portraits.png"
    assert manager.frames["human_male"].rect == pygame.Rect(0, 0, 10, 10)
    assert manager.frames["human_male_2"].rect == pygame.Rect(10, 0, 10, 10)
    assert manager.frames["half_orc_female_2"].race == "half_orc"
    assert manager.variant_count() == 2


def test_portrait_sheet_mapping_uses_per_race_variant_columns(tmp_path):
    mapping_json = _write_sheet_mapping(tmp_path)
    human_sheet = _surface((20, 20), (0, 0, 0, 0))
    human_sheet.fill((255, 0, 0, 255), pygame.Rect(0, 0, 10, 10))
    human_sheet.fill((0, 255, 0, 255), pygame.Rect(10, 0, 10, 10))
    human_sheet.fill((255, 255, 0, 255), pygame.Rect(10, 10, 10, 10))
    orc_sheet = _surface((20, 20), (0, 0, 255, 255))
    surfaces = {
        "human_base_portraits.png": human_sheet,
        "half_orc_base_portraits.png": orc_sheet,
    }

    manager = PortraitManager(portrait_root=tmp_path, atlas_json=mapping_json)
    manager.load_image = lambda path: surfaces[path.name]

    male_1 = manager.base_portrait("Human", "Male", variant=0)
    male_2 = manager.base_portrait("Human", "Male", variant=1)
    female_2 = manager.base_portrait("Human", "Female", variant=1)
    half_orc = manager.base_portrait("Half Orc", "Female", variant=1)

    assert male_1.get_at((1, 1)) == pygame.Color(255, 0, 0, 255)
    assert male_2.get_at((1, 1)) == pygame.Color(0, 255, 0, 255)
    assert female_2.get_at((1, 1)) == pygame.Color(255, 255, 0, 255)
    assert half_orc.get_at((1, 1)) == pygame.Color(0, 0, 255, 255)


def test_portrait_mapping_excludes_internal_separator_lines():
    manager = PortraitManager()

    def bright_separator_pixels(surface, side: str) -> int:
        width, height = surface.get_size()
        if side == "left":
            pixels = [surface.get_at((0, y)) for y in range(height)]
        elif side == "right":
            pixels = [surface.get_at((width - 1, y)) for y in range(height)]
        else:
            raise AssertionError(side)
        return sum(
            1
            for pixel in pixels
            if min(pixel.r, pixel.g, pixel.b) > 190
            and max(pixel.r, pixel.g, pixel.b) - min(pixel.r, pixel.g, pixel.b) < 45
        )

    for race in ("Human", "Elf", "Half Elf", "Half Giant", "Gnome", "Dwarf", "Half Orc"):
        for gender in ("Male", "Female"):
            for variant in range(manager.variant_count()):
                portrait = manager.base_portrait(race, gender, variant=variant)
                _width, height = portrait.get_size()
                assert bright_separator_pixels(portrait, "left") < height * 0.25
                assert bright_separator_pixels(portrait, "right") < height * 0.25


def test_portrait_mapping_keeps_variant_sizes_stable():
    manager = PortraitManager()
    sizes = {
        manager.base_portrait(race, gender, variant=variant).get_size()
        for race in ("Human", "Elf", "Half Elf", "Half Giant", "Gnome", "Dwarf", "Half Orc")
        for gender in ("Male", "Female")
        for variant in range(manager.variant_count())
    }

    assert sizes == {(269, 560)}


def test_portrait_key_normalization_variants():
    assert PortraitManager.normalize_key("Half Orc") == "half_orc"
    assert PortraitManager.normalize_key("half_orc") == "half_orc"
    assert PortraitManager.normalize_key("Half Giant") == "half_giant"
    assert PortraitManager.normalize_key("Male") == "male"
    assert PortraitManager.normalize_key("female") == "female"
    assert (
        PortraitManager.entry_key(SimpleNamespace(name="Half Orc"), "Female") == "half_orc_female"
    )
    assert PortraitManager.appearance_id("Human", "Male", 4) == "human_male_5"


def test_base_portrait_lookup_uses_selected_sheet_variant(tmp_path):
    mapping_json = _write_sheet_mapping(tmp_path)
    human_sheet = _surface((20, 20), (20, 20, 20, 255))
    human_sheet.fill((80, 80, 80, 255), pygame.Rect(10, 0, 10, 10))

    manager = PortraitManager(portrait_root=tmp_path, atlas_json=mapping_json)
    manager.load_image = lambda _path: human_sheet

    base = manager.base_portrait("Human", "Male", variant=0)
    variant = manager.base_portrait("Human", "Male", variant=1)
    wrapped = manager.base_portrait("Human", "Male", variant=3)

    assert base.get_at((1, 1)) == pygame.Color(20, 20, 20, 255)
    assert variant.get_at((1, 1)) == pygame.Color(80, 80, 80, 255)
    assert wrapped is variant


def test_portrait_frame_scales_when_sheet_is_narrower_than_json_bounds(tmp_path):
    frames = {
        "male_1": {"x": 0, "y": 0, "w": 10, "h": 10},
        "male_2": {"x": 90, "y": 0, "w": 20, "h": 10},
        "female_1": {"x": 0, "y": 10, "w": 10, "h": 10},
        "female_2": {"x": 90, "y": 10, "w": 20, "h": 10},
    }
    mapping_json = _write_sheet_mapping(tmp_path, frames=frames)
    manager = PortraitManager(portrait_root=tmp_path, atlas_json=mapping_json)
    atlas = _surface((100, 20), (0, 0, 0, 0))
    atlas.fill((200, 60, 40, 255), pygame.Rect(82, 0, 18, 10))
    manager.load_image = lambda _path: atlas

    portrait = manager.base_portrait("Human", "Male", variant=1)

    assert portrait.get_size() == (18, 10)
    assert portrait.get_at((1, 1)) == pygame.Color(200, 60, 40, 255)


def test_missing_portrait_returns_placeholder_and_logs_warning(tmp_path, caplog):
    manager = PortraitManager(portrait_root=tmp_path, atlas_json=tmp_path / "missing.json")

    with caplog.at_level("WARNING"):
        portrait = manager.get_portrait("Unknown Race", "Unknown Gender")

    assert portrait.get_size() == (225, 400)
    assert "Portrait missing" in caplog.text


def test_missing_overlay_is_recorded_and_skipped(tmp_path):
    mapping_json = _write_sheet_mapping(tmp_path)
    manager = PortraitManager(portrait_root=tmp_path, atlas_json=mapping_json)
    manager.load_image = lambda _path: _surface((20, 20), (10, 20, 30, 255))

    portrait = manager.get_portrait("Human", "Male", class_name="Warrior")

    assert portrait.get_size() == (10, 10)
    assert manager.missing_overlays
    assert manager.missing_overlays[-1].name == "warrior.png"


def test_portrait_composition_order_and_cache_reuse(tmp_path):
    mapping_json = _write_sheet_mapping(tmp_path)
    manager = PortraitManager(portrait_root=tmp_path, atlas_json=mapping_json)
    manager.load_image = lambda _path: _surface((20, 20), (10, 10, 10, 255))
    order = []
    colors = {
        "warrior.png": (20, 20, 20, 255),
        "paladin.png": (30, 30, 30, 255),
        "crusader.png": (40, 40, 40, 255),
        "blessed.png": (50, 50, 50, 255),
    }

    def load_overlay(path):
        order.append(path.name)
        return _surface((10, 10), colors[path.name])

    manager.load_overlay = load_overlay

    portrait = manager.get_portrait(
        "Human",
        "Male",
        class_name="Warrior",
        first_promotion="Paladin",
        second_promotion="Crusader",
        effects=("Blessed",),
    )
    cached = manager.get_portrait(
        "Human",
        "Male",
        class_name="Warrior",
        first_promotion="Paladin",
        second_promotion="Crusader",
        effects=("Blessed",),
    )

    assert order == ["warrior.png", "paladin.png", "crusader.png", "blessed.png"]
    assert portrait.get_at((1, 1)) == pygame.Color(50, 50, 50, 255)
    assert cached is portrait


def test_portrait_cache_distinguishes_promotion_and_effects(tmp_path):
    mapping_json = _write_sheet_mapping(tmp_path)
    manager = PortraitManager(portrait_root=tmp_path, atlas_json=mapping_json)
    manager.load_image = lambda _path: _surface((20, 20), (10, 10, 10, 255))
    manager.load_overlay = lambda _path: None

    base = manager.get_portrait("Human", "Male", first_promotion="Paladin")
    promoted = manager.get_portrait("Human", "Male", first_promotion="Crusader")
    affected = manager.get_portrait(
        "Human", "Male", first_promotion="Paladin", effects=("Blessed",)
    )
    variant = manager.get_portrait("Human", "Male", first_promotion="Paladin", variant=1)

    assert promoted is not base
    assert affected is not base
    assert variant is not base
