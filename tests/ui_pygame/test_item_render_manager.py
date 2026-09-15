#!/usr/bin/env python3
"""Focused coverage for large item render loading."""

from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

import pygame

from src.core import items
from src.ui_pygame.assets.item_render_manager import ItemRenderManager


def _write_render_fixture(root: Path) -> None:
    root.mkdir(exist_ok=True)
    manifest = {
        "longsword": {"x": 0, "y": 0, "w": 80, "h": 140},
        "greatsword": {"x": 80, "y": 0, "w": 80, "h": 140},
        "warhammer": {"x": 160, "y": 0, "w": 80, "h": 140},
        "weapon": {"x": 0, "y": 140, "w": 80, "h": 140},
        "armor": {"x": 80, "y": 140, "w": 80, "h": 140},
        "helmet": {"x": 160, "y": 140, "w": 80, "h": 140},
        "generic_item": {"x": 160, "y": 140, "w": 80, "h": 140},
    }
    (root / "item_render_atlas.json").write_text(json.dumps(manifest), encoding="utf-8")
    (root / "item_render_map.json").write_text(
        json.dumps({"Claymore": "greatsword"}), encoding="utf-8"
    )
    (root / "item_icon_map.json").write_text(
        json.dumps({"Iron Sword": "sword", "War Hammer": "hammer"}), encoding="utf-8"
    )
    surface = pygame.Surface((240, 280), pygame.SRCALPHA)
    surface.fill((0, 0, 0, 0))
    surface.fill((255, 0, 0, 255), pygame.Rect(0, 0, 80, 140))
    surface.fill((0, 255, 0, 255), pygame.Rect(80, 0, 80, 140))
    surface.fill((0, 0, 255, 255), pygame.Rect(160, 0, 80, 140))
    surface.fill((255, 255, 0, 255), pygame.Rect(0, 140, 80, 140))
    surface.fill((255, 0, 255, 255), pygame.Rect(80, 140, 80, 140))
    surface.fill((0, 255, 255, 255), pygame.Rect(160, 140, 80, 140))
    pygame.image.save(surface, root / "item_render_atlas.png")


def test_item_render_manager_loads_manifest_and_exact_mapping(tmp_path):
    _write_render_fixture(tmp_path)

    manager = ItemRenderManager(
        render_root=tmp_path,
        icon_map_path=tmp_path / "item_icon_map.json",
        enhance_artwork=False,
    )

    assert manager.frames["longsword"].rect == pygame.Rect(0, 0, 80, 140)
    assert manager.get_render_key_for_item(SimpleNamespace(name="Claymore")) == "greatsword"
    assert manager.get_render_by_name("Claymore").get_at((1, 1)) == pygame.Color(0, 255, 0, 255)


def test_item_render_manager_uses_icon_map_conversion_and_category_fallbacks(tmp_path):
    _write_render_fixture(tmp_path)
    manager = ItemRenderManager(
        render_root=tmp_path,
        icon_map_path=tmp_path / "item_icon_map.json",
        enhance_artwork=False,
    )

    assert manager.get_render_key_for_item(SimpleNamespace(name="Iron Sword")) == "longsword"
    assert manager.get_render_key_for_item(SimpleNamespace(name="War Hammer")) == "warhammer"
    assert (
        manager.get_render_key_for_item(
            SimpleNamespace(name="Mystery Axe", typ="Weapon", subtyp="Unknown")
        )
        == "weapon"
    )
    assert (
        manager.get_render_key_for_item(
            SimpleNamespace(name="Mystery Plate", typ="Armor", subtyp="Unknown")
        )
        == "armor"
    )
    assert (
        manager.get_render_key_for_item(
            SimpleNamespace(name="Mystery Helm", typ="Helmet", subtyp="Heavy")
        )
        == "helmet"
    )
    assert (
        manager.get_render_key_for_item(SimpleNamespace(name="Mystery Thing", typ="", subtyp=""))
        == "generic_item"
    )
    assert "Mystery Thing" in manager.missing_mappings


def test_item_render_manager_prefers_individual_item_art_for_exact_mapping(tmp_path):
    _write_render_fixture(tmp_path)
    art_root = tmp_path / "item_art"
    art_root.mkdir()
    (tmp_path / "item_render_map.json").write_text(
        json.dumps({"Rapier": "rapier"}), encoding="utf-8"
    )
    art = pygame.Surface((20, 20), pygame.SRCALPHA)
    art.fill((12, 34, 210, 255))
    pygame.image.save(art, art_root / "rapier.png")
    manager = ItemRenderManager(
        render_root=tmp_path,
        item_art_root=art_root,
        icon_map_path=tmp_path / "item_icon_map.json",
        enhance_artwork=False,
    )

    render = manager.get_render_by_name("Rapier")

    assert manager.get_render_key_for_item(SimpleNamespace(name="Rapier")) == "rapier"
    assert render.get_size() == (20, 20)
    assert render.get_at((1, 1)) == pygame.Color(12, 34, 210, 255)


def test_item_render_manager_loads_nested_individual_item_art(tmp_path):
    _write_render_fixture(tmp_path)
    art_root = tmp_path / "item_art"
    nested_root = art_root / "weapons" / "swords"
    nested_root.mkdir(parents=True)
    (tmp_path / "item_render_map.json").write_text(
        json.dumps({"Excalibur": "weapons/swords/excalibur"}),
        encoding="utf-8",
    )
    art = pygame.Surface((18, 22), pygame.SRCALPHA)
    art.fill((220, 210, 44, 255))
    pygame.image.save(art, nested_root / "excalibur.png")
    manager = ItemRenderManager(
        render_root=tmp_path,
        item_art_root=art_root,
        icon_map_path=tmp_path / "item_icon_map.json",
        enhance_artwork=False,
    )

    render = manager.get_render_by_name("Excalibur")

    assert (
        manager.get_render_key_for_item(SimpleNamespace(name="Excalibur"))
        == "weapons/swords/excalibur"
    )
    assert manager.art_path_for_key("weapons/swords/excalibur") == nested_root / "excalibur.png"
    assert render.get_size() == (18, 22)
    assert render.get_at((1, 1)) == pygame.Color(220, 210, 44, 255)


def test_item_render_manager_missing_frame_and_cache_reuse(tmp_path):
    _write_render_fixture(tmp_path)
    manager = ItemRenderManager(
        render_root=tmp_path,
        icon_map_path=tmp_path / "item_icon_map.json",
        enhance_artwork=False,
    )

    generic = manager.get_render_by_key("does_not_exist")
    again = manager.get_render_by_key("does_not_exist")

    assert generic.get_at((1, 1)) == pygame.Color(0, 255, 255, 255)
    assert again is generic


def test_item_render_manager_scaled_render_preserves_aspect_and_caches(tmp_path):
    _write_render_fixture(tmp_path)
    manager = ItemRenderManager(
        render_root=tmp_path,
        icon_map_path=tmp_path / "item_icon_map.json",
        enhance_artwork=False,
    )

    scaled = manager.get_scaled_render_by_key("longsword", (100, 100))
    cached = manager.get_scaled_render_by_key("longsword", (100, 100))

    assert scaled is cached
    assert scaled.get_size() == (100, 100)
    assert scaled.get_at((1, 50)).a == 0
    assert scaled.get_at((50, 50)).a > 0


def test_item_render_manager_missing_atlas_returns_fallback(tmp_path):
    root = tmp_path / "missing"
    root.mkdir()
    (root / "item_render_atlas.json").write_text(
        json.dumps({"generic_item": {"x": 0, "y": 0, "w": 80, "h": 140}}),
        encoding="utf-8",
    )
    (root / "item_render_map.json").write_text("{}", encoding="utf-8")
    (root / "item_icon_map.json").write_text("{}", encoding="utf-8")
    manager = ItemRenderManager(
        render_root=root,
        icon_map_path=root / "item_icon_map.json",
        enhance_artwork=False,
    )

    assert manager.get_render_by_key("generic_item").get_size() == (160, 280)


def test_item_render_manager_enhances_cached_display_art(tmp_path):
    _write_render_fixture(tmp_path)
    manager = ItemRenderManager(render_root=tmp_path, icon_map_path=tmp_path / "item_icon_map.json")

    render = manager.get_render_by_key("longsword")
    cached = manager.get_render_by_key("longsword")

    assert cached is render
    assert render.get_at((1, 1)).r == 255
    assert render.get_at((1, 1)).a == 255


def test_item_render_manager_contrast_lift_preserves_alpha():
    source = pygame.Surface((2, 1), pygame.SRCALPHA)
    source.set_at((0, 0), pygame.Color(40, 35, 30, 255))
    source.set_at((1, 0), pygame.Color(20, 20, 20, 0))

    enhanced = ItemRenderManager.enhance_display_contrast(source)

    assert enhanced.get_at((0, 0)).r > source.get_at((0, 0)).r
    assert enhanced.get_at((1, 0)).a == 0


def test_default_item_render_map_covers_instantiable_catalog_items():
    manager = ItemRenderManager()
    item_names = set()
    for value in vars(items).values():
        if not isinstance(value, type) or not issubclass(value, items.Item) or value is items.Item:
            continue
        try:
            item_names.add(value().name)
        except Exception:
            continue

    missing = sorted(item_names - set(manager.render_map))

    assert missing == []


def test_default_item_render_map_uses_dedicated_art_for_new_tools_and_signet():
    manager = ItemRenderManager(enhance_artwork=False)
    expected = {
        items.LockpickKit().name: "tools/lockpick_kit",
        items.SmokeBomb().name: "tools/smoke_bomb",
        items.WaterBladder().name: "tools/water_bladder",
        items.Oculus().name: "magic_tools/oculus",
        items.ThievesGuildSignet().name: "accessories/rings/thieves_guild_signet",
    }

    for item_name, render_key in expected.items():
        path = manager.art_path_for_key(render_key)
        surface = pygame.image.load(str(path))
        width, height = surface.get_size()

        assert manager.get_render_key_for_item(item_name) == render_key
        assert path.exists()
        assert surface.get_at((0, 0)).a == 0
        assert surface.get_at((width - 1, 0)).a == 0
        assert surface.get_at((0, height - 1)).a == 0
        assert surface.get_at((width - 1, height - 1)).a == 0
        assert pygame.mask.from_surface(surface, 8).count() > 1000


def test_default_item_render_map_uses_dedicated_art_for_recent_combat_items():
    manager = ItemRenderManager(enhance_artwork=False)
    expected = {
        items.HandCrossbow().name: "offhand/crossbows/hand_crossbow",
        items.LightCrossbow().name: "offhand/crossbows/light_crossbow",
        items.HeavyCrossbow().name: "offhand/crossbows/heavy_crossbow",
        items.PistolCrossbow().name: "offhand/crossbows/pistol_crossbow",
        items.RepeatingCrossbow().name: "offhand/crossbows/repeating_crossbow",
        items.MagicCrossbow().name: "offhand/crossbows/magic_crossbow",
        items.GoldenClaw().name: "offhand/crossbows/golden_claw",
        items.WoodenBolts().name: "ammunition/crossbow_bolts/wooden_bolts",
        items.MetalBolts().name: "ammunition/crossbow_bolts/metal_bolts",
        items.ArmorPiercingBolts().name: ("ammunition/crossbow_bolts/armor_piercing_bolts"),
        items.MagicBolts().name: "ammunition/crossbow_bolts/magic_bolts",
        items.HeatSeekingBolts().name: ("ammunition/crossbow_bolts/heat_seeking_bolts"),
        items.NapalmBolts().name: "ammunition/crossbow_bolts/napalm_bolts",
        items.DelayedBolts().name: "ammunition/crossbow_bolts/delayed_bolts",
        items.ThrowingDaggers().name: "ammunition/throwing_daggers",
        items.MildToxin().name: "consumables/toxins/mild_toxin",
        items.Neurotoxin().name: "consumables/toxins/neurotoxin",
        items.Hemotoxin().name: "consumables/toxins/hemotoxin",
        items.Amatoxin().name: "consumables/toxins/amatoxin",
        items.Myotoxin().name: "consumables/toxins/myotoxin",
        items.Necrotoxin().name: "consumables/toxins/necrotoxin",
        items.SnakeVenom().name: "materials/reagents/snake_venom",
        items.ScorpionVenom().name: "materials/reagents/scorpion_venom",
        items.ViperVenom().name: "materials/reagents/viper_venom",
        items.LizardVenom().name: "materials/reagents/lizard_venom",
        items.ShadowVenom().name: "materials/reagents/shadow_venom",
        items.DeathcapMushroom().name: "materials/reagents/deathcap_mushroom",
    }

    assert len(expected) == 27
    for item_name, render_key in expected.items():
        path = manager.art_path_for_key(render_key)
        assert path.exists()
        surface = pygame.image.load(str(path))
        width, height = surface.get_size()

        assert manager.get_render_key_for_item(item_name) == render_key
        assert surface.get_at((0, 0)).a == 0
        assert surface.get_at((width - 1, 0)).a == 0
        assert surface.get_at((0, height - 1)).a == 0
        assert surface.get_at((width - 1, height - 1)).a == 0
        assert pygame.mask.from_surface(surface, 8).count() > 1000


def test_default_item_render_map_uses_individual_art_for_diviner_rods():
    manager = ItemRenderManager(enhance_artwork=False)
    expected = {
        items.WillowDiviningRod().name: "offhand/rods/willow_divining_rod",
        items.CopperLeyRod().name: "offhand/rods/copper_ley_rod",
        items.MoonlitHazelRod().name: "offhand/rods/moonlit_hazel_rod",
    }

    assert len(set(expected.values())) == len(expected)
    for item_name, render_key in expected.items():
        path = manager.art_path_for_key(render_key)
        assert manager.get_render_key_for_item(item_name) == render_key
        assert path.exists()


def test_default_item_render_map_uses_individual_art_for_helmet_catalog():
    manager = ItemRenderManager()
    generic_keys = {"helmet", "armor", "generic_item"}

    missing = []
    for helmet_classes in items.items_dict["Helmet"].values():
        for helmet_cls in helmet_classes:
            helmet = helmet_cls()
            render_key = manager.get_render_key_for_item(helmet)
            art_path = manager.art_path_for_key(render_key)
            if render_key in generic_keys or not art_path.exists():
                missing.append((helmet.name, render_key))

    assert missing == []


def test_default_item_render_map_uses_individual_art_for_potion_families():
    manager = ItemRenderManager()
    generic_keys = {"consumable", "antidote", "generic_item"}

    missing = []
    for potion_subtyp, potion_classes in items.items_dict["Potion"].items():
        if potion_subtyp == "Status":
            continue
        for potion_cls in potion_classes:
            potion = potion_cls()
            render_key = manager.get_render_key_for_item(potion)
            art_path = manager.art_path_for_key(render_key)
            if render_key in generic_keys or not art_path.exists():
                missing.append((potion.name, render_key))

    assert missing == []


def test_default_item_render_map_uses_individual_art_for_status_item_family():
    manager = ItemRenderManager()
    generic_keys = {"consumable", "generic_item"}

    missing = []
    for potion_cls in [*items.items_dict["Potion"]["Status"], items.Remedy]:
        potion = potion_cls()
        render_key = manager.get_render_key_for_item(potion)
        art_path = manager.art_path_for_key(render_key)
        if render_key in generic_keys or not art_path.exists():
            missing.append((potion.name, render_key))

    assert missing == []


def test_default_item_render_map_uses_individual_art_for_unique_and_special_items():
    manager = ItemRenderManager()
    item_classes = [
        items.Excalibur,
        items.Excalibur2,
        items.Mjolnir,
        items.Necronomicon,
        items.VisionPendant,
        items.DragonStaff,
        items.Gungnir,
        items.Svalinn,
        items.MedusaShield,
        items.RibbonPendant,
        items.Jarnbjorn,
        items.Carnwennan,
        items.GodsHand,
        items.IndrasFist,
        items.Skullcrusher,
        items.PrincessGuard,
        items.VulcansHammer,
        items.EarthHammer,
        items.Magus,
        items.CodexEternity,
        items.CompendiumAncients,
        items.DragonRouge,
        items.ClassRing,
        items.ForceRing,
        items.MagicPendant,
        items.InvisibilityPendant,
        items.LevitationPendant,
        items.GorgonPendant,
        items.GarfunkelPendant,
        items.DharmaPendant,
        items.ElementalChain,
        items.FireAmulet,
        items.IceAmulet,
        items.ElectricAmulet,
        items.WaterAmulet,
        items.EarthAmulet,
        items.WindAmulet,
        items.ElementalAmulet,
        items.Unobtainium,
        items.DeadSoldier,
        items.Relic1,
        items.Relic2,
        items.Relic3,
        items.Relic4,
        items.Relic5,
        items.Relic6,
    ]

    missing = []
    for item_cls in item_classes:
        item = item_cls()
        render_key = manager.get_render_key_for_item(item)
        art_path = manager.art_path_for_key(render_key)
        if not art_path.exists():
            missing.append((item.name, render_key))

    assert missing == []


def test_default_item_render_map_uses_individual_art_for_scroll_catalog():
    manager = ItemRenderManager()
    generic_keys = {"scroll", "generic_item"}

    missing = []
    for scroll_cls in items.items_dict["Misc"]["Scroll"]:
        scroll = scroll_cls()
        render_key = manager.get_render_key_for_item(scroll)
        art_path = manager.art_path_for_key(render_key)
        if render_key in generic_keys or not art_path.exists():
            missing.append((scroll.name, render_key))

    assert missing == []


def test_default_item_render_map_uses_individual_art_for_material_and_key_families():
    manager = ItemRenderManager()
    generic_keys = {"crafting_material", "quest_item", "gem", "generic_item"}
    item_classes = [
        items.RatTail,
        items.MysteryMeat,
        items.Leather,
        items.Feather,
        items.SnakeSkin,
        items.ScrapMetal,
        items.CursedHops,
        items.BirdFat,
        items.ElementalMote,
        items.PowerCore,
        items.Phylactery,
        items.Key,
        items.OldKey,
        items.MasterKey,
        items.CrypticKey,
        items.BrassKey,
        items.BlacksmithsHammer,
        items.JesterToken,
        items.TicketPiece,
        items.LuckyLocket,
        items.Joker,
        items.ChaliceMap,
        items.JoffreysLetter,
        items.EmptyVial,
        items.SpringWater,
        items.DragonTear,
        items.ChiryuKoma,
        items.Excaliper,
        items.GoldenChalice,
    ]

    missing = []
    for item_cls in item_classes:
        item = item_cls()
        render_key = manager.get_render_key_for_item(item)
        art_path = manager.art_path_for_key(render_key)
        if render_key in generic_keys or not art_path.exists():
            missing.append((item.name, render_key))

    assert missing == []
