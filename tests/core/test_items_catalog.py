#!/usr/bin/env python3
"""Broad catalog coverage for item definitions and helper utilities."""

import inspect
import sys
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).parents[2]))

from src.core import items
from src.core.character import armor_resistance_modifier
from src.core.combat.combat_result import CombatResult
from src.core.effects.common import StatusApplyEffect
from tests.test_framework import TestGameState

_BASE_ITEM_CLASSES = {
    items.Item,
    items.Weapon,
    items.Armor,
    items.Helmet,
    items.OffHand,
    items.Accessory,
    items.Potion,
    items.Misc,
}


def _no_arg_item_classes():
    discovered = []
    for name in dir(items):
        obj = getattr(items, name)
        if not inspect.isclass(obj):
            continue
        if not issubclass(obj, items.Item) or obj in _BASE_ITEM_CLASSES:
            continue
        signature = inspect.signature(obj)
        required = [
            param
            for param in signature.parameters.values()
            if param.default is param.empty
            and param.kind in (param.POSITIONAL_ONLY, param.POSITIONAL_OR_KEYWORD)
        ]
        if not required:
            discovered.append(obj)
    return sorted(discovered, key=lambda cls: cls.__name__)


def test_no_arg_item_catalog_instantiates_and_renders_cleanly():
    discovered = _no_arg_item_classes()

    assert len(discovered) >= 300

    seen_types = set()
    saw_summon_misc = False
    for item_cls in discovered:
        item = item_cls()
        seen_types.add(item.typ)
        assert item.name
        assert isinstance(item.description, str)
        assert item.subtyp is not None

        rendered = str(item)
        assert item.name in rendered

        if isinstance(item, items.Weapon):
            assert "Damage:" in rendered
            assert "Critical Chance:" in rendered
            if item.subtyp == "Fist":
                assert item.disarm is False
        elif isinstance(item, items.Armor):
            assert "Armor:" in rendered
        elif isinstance(item, items.OffHand):
            if item.subtyp == "Shield":
                assert "Block:" in rendered
            elif item.subtyp == "Crossbow":
                assert "Damage:" in rendered
            else:
                assert "Spell Damage Mod:" in rendered
        elif isinstance(item, items.Accessory):
            assert "Mod:" in rendered
        elif isinstance(item, items.Potion):
            assert "Weight:" in rendered
            assert item.weight == 0.1
        else:
            assert "Sub-type:" in rendered
            if "Summon" in item.subtyp:
                assert "Sub-type: Special" in rendered
                saw_summon_misc = True

    assert {"Weapon", "Armor", "Helmet", "OffHand", "Accessory", "Potion", "Misc"} <= seen_types
    assert saw_summon_misc is True


def test_reality_fragment_is_an_extremely_rare_miracle_reagent():
    fragment = items.RealityFragment()

    assert fragment.typ == "Misc"
    assert fragment.subtyp == "Reagent"
    assert fragment.rarity == 0.01
    assert items.RealityFragment in items.items_dict["Misc"]["Reagents"]
    assert items.RealityFragment in items.catalog._build_rarity_table()["8"]


def test_helmet_catalog_matches_equipment_table():
    helmet_names = {
        subtyp: [helmet_cls().name for helmet_cls in helmet_classes]
        for subtyp, helmet_classes in items.items_dict["Helmet"].items()
    }

    assert helmet_names["Cloth"] == [
        "Cloth Cap",
        "Jaapi",
        "Turban",
        "Witch Hat",
        "Enchanted Hood",
        "Mitre Hat",
        "Circlet",
        "Cohuleen Druith",
        "Ariadne's Diadem",
    ]
    assert helmet_names["Light"] == [
        "Leather Cap",
        "Pith Helmet",
        "War Mask",
        "Arming Cap",
        "Katapu",
        "Sōmen",
        "Demon Cowl",
    ]
    assert helmet_names["Medium"] == [
        "Scale Helm",
        "Chain Coif",
        "Kulah Khud",
        "Cervelliere",
        "Tolga",
        "Tarnhelm",
        "Helm of Rostam",
    ]
    assert helmet_names["Heavy"] == [
        "Iron Helm",
        "Kettle Helm",
        "Barbute",
        "Great Helm",
        "Plate Helm",
        "Close Helm",
        "Kabuto",
    ]

    mitre = items.MitreHat()
    circlet = items.Circlet()
    assert mitre.restriction == ["Priest", "Archbishop", "Diviner", "Astromancer"]
    assert circlet.restricted_against == ["Priest", "Archbishop", "Diviner", "Astromancer"]
    assert items.CohuleenDruith().resist_mod == 0.5
    assert items.DemonCowl().element == "Death"
    assert items.VisoredSallet().name == "Visored Sallet"
    assert items.Tolga().armor == 10
    assert items.Tarnhelm().armor == 13
    assert items.HelmOfRostam().armor == 19


def test_reagents_are_visible_misc_items():
    reagent_names = [
        items.Acorn().name,
        items.VineSeed().name,
        items.FungusSpore().name,
        items.HemlockRoot().name,
    ]

    assert reagent_names == ["Acorn", "Vine Seed", "Fungus Spore", "Hemlock Root"]
    for reagent in (items.Acorn(), items.VineSeed(), items.FungusSpore(), items.HemlockRoot()):
        assert reagent.typ == "Misc"
        assert reagent.subtyp == "Reagent"
        assert reagent.rarity == 0.5
        assert "Sub-type: Reagent" in str(reagent)


def test_helm_of_rostam_blocks_berserk_and_stun_without_invisibility():
    actor = TestGameState.create_player(name="Caster", class_name="Sorcerer", race_name="Human")
    target = TestGameState.create_player(name="Defender", class_name="Warrior", race_name="Human")
    target.equipment["Helmet"] = items.HelmOfRostam()

    assert target.invisible is False
    assert target.has_status_protection("Berserk") is True
    assert target.has_status_protection("Stun") is True
    assert target.has_status_protection("Sleep") is False
    assert target.apply_stun(2, source="test", applier=actor) is False

    result = CombatResult(action="Berserk Test", actor=actor, target=target)
    StatusApplyEffect("Berserk", duration=2).apply(actor, target, result)

    assert target.status_effects["Berserk"].active is False
    assert result.extra["status_immune"] == "Berserk"


def test_item_metadata_lines_include_elements_and_resistance_mods():
    assert "Element: Electric" in items.item_metadata_lines(items.IndrasFist())
    assert "Resistance: Fire +25%" in items.item_metadata_lines(items.Svalinn())
    assert "Resistance: Fire +25%, Water +25%" in items.item_metadata_lines(items.Palangina())
    assert "Resistance: Fire +50%" in items.item_metadata_lines(items.FireChain())
    assert "Immunity: Electric" in items.item_metadata_lines(items.ElectricAmulet())


def test_palangina_grants_fire_and_water_resistance_only():
    palangina = items.Palangina()

    assert armor_resistance_modifier(palangina, "Fire") == 0.25
    assert armor_resistance_modifier(palangina, "Water") == 0.25
    assert armor_resistance_modifier(palangina, "Ice") == 0.0


def test_resistance_item_descriptions_leave_numeric_effects_to_metadata_lines():
    resistance_items = [
        items.CohuleenDruith(),
        items.DemonCowl(),
        items.Svalinn(),
        items.FireChain(),
        items.IceChain(),
        items.ElectricChain(),
        items.WaterChain(),
        items.EarthChain(),
        items.WindChain(),
        items.ElementalChain(),
        items.Palangina(),
        items.FireAmulet(),
        items.IceAmulet(),
        items.ElectricAmulet(),
        items.WaterAmulet(),
        items.EarthAmulet(),
        items.WindAmulet(),
        items.ElementalAmulet(),
    ]

    for item in resistance_items:
        description = item.description.lower()
        assert "resistance" not in description
        assert "immunity" not in description
        assert "immune" not in description
        assert " by 50%" not in description
        assert " by 100%" not in description
        assert " by 25%" not in description


def test_base_item_classes_and_helper_utilities(monkeypatch):
    base_item = items.Item("Summon Sigil", "A helper token.", 5, 0.25, "Summon - Test")
    assert base_item.use(None) == ""
    assert base_item.special_effect(None) is None
    assert "Sub-type: Special" in str(base_item)

    fist_weapon = items.Weapon(
        "Fist Wrap", "Simple wraps.", 10, 0.5, 2, 0.1, 1, "Fist", False, True
    )
    sword_weapon = items.Weapon(
        "Training Sword", "A blunt sword.", 10, 0.5, 3, 0.2, 1, "Sword", False, True
    )
    armor = items.Armor("Padded Coat", "Simple protection.", 10, 0.5, 2, "Cloth", False)
    helmet = items.Helmet("Padded Cap", "Simple head protection.", 10, 0.5, 1, "Cloth", False)
    shield = items.OffHand("Practice Shield", "A round shield.", 10, 0.5, 0.25, "Shield", False)
    tome = items.OffHand("Study Tome", "A magical primer.", 10, 0.5, 3, "Book", False)
    accessory = items.Accessory("Charm Ring", "A simple charm.", 10, 0.5, "+1 Luck", "Ring", False)
    potion = items.Potion("Test Potion", "A minor tonic.", 10, 0.5, "Potion")
    misc = items.Misc("Quest Scrap", "A tiny scrap.", 0, 1.0, "Quest")
    sheet_music = items.SheetMusic("Song Sheet", "Sheet music.", 0, 0.5, "Special")
    blank_scroll = items.BlankScroll("Blank Scroll", "A writable scroll.", 0, 0.5, "Special")
    guild_signet = items.ThievesGuildSignet()
    lockpick_kit = items.LockpickKit()
    smoke_bomb = items.SmokeBomb()
    oculus = items.Oculus()
    censer = items.CenserOfChokingAsh()
    stolen_scroll = items.InscribedSpellScroll("MagicMissile", charges=2)

    assert fist_weapon.disarm is False
    assert sword_weapon.disarm is True
    assert fist_weapon.special_effect(None) is None
    assert armor.special_effect(None) is None
    assert helmet.typ == "Helmet"
    assert "Damage:" in str(fist_weapon)
    assert "Armor:" in str(armor)
    assert "Armor:" in str(helmet)
    assert "Block:" in str(shield)
    assert "Spell Damage Mod:" in str(tome)
    assert "Mod:" in str(accessory)
    assert "Weight:" in str(potion)
    assert "Sub-type: Quest" in str(misc)
    assert sheet_music.typ == "Misc"
    assert blank_scroll.typ == "Misc"
    assert guild_signet.name == "Thieves Guild Signet"
    assert guild_signet.subtyp == "Special"
    assert lockpick_kit.name == "Lockpick Kit"
    assert lockpick_kit.subtyp == "Tool"
    assert lockpick_kit.charges == 3
    assert "Durability: 3" in lockpick_kit.description
    assert items.LockpickKit in items.items_dict["Misc"]["Tool"]
    assert smoke_bomb.name == "Smoke Bomb"
    assert smoke_bomb.subtyp == "Tool"
    assert items.SmokeBomb in items.items_dict["Misc"]["Tool"]
    assert oculus.name == "Oculus"
    assert oculus.subtyp == "Magic Tool"
    assert items.Oculus in items.items_dict["Misc"]["Magic Tool"]
    assert censer.name == "Censer of Choking Ash"
    assert censer.value == 5000
    assert censer.subtyp == "Magic Tool"
    assert items.CenserOfChokingAsh in items.items_dict["Misc"]["Magic Tool"]
    assert items.has_lockpick_kit(SimpleNamespace(inventory={})) is False
    assert (
        items.has_lockpick_kit(SimpleNamespace(inventory={"Lockpick Kit": [lockpick_kit]})) is True
    )
    assert items.has_smoke_bomb(SimpleNamespace(inventory={"Smoke Bomb": [smoke_bomb]})) is True
    assert items.has_oculus(SimpleNamespace(inventory={"Oculus": [oculus]})) is True
    assert (
        items.can_detect_fake_walls(
            SimpleNamespace(inventory={"Oculus": [oculus]}, spellbook={"Skills": {}})
        )
        is True
    )
    assert (
        items.can_detect_fake_walls(
            SimpleNamespace(inventory={}, spellbook={"Skills": {"Keen Eye": object()}})
        )
        is True
    )

    utility_player = TestGameState.create_player(stats={"dex": 18})
    utility_player.inventory = {"Lockpick Kit": [lockpick_kit], "Smoke Bomb": [smoke_bomb]}
    normal_break_chance = items.lockpick_break_chance(utility_player)
    master_break_chance = items.lockpick_break_chance(utility_player, master=True)
    assert master_break_chance < normal_break_chance
    used, kit_message = items.use_lockpick_kit(utility_player, roll=0.99)
    assert used is True
    assert "Durability: 2" in kit_message
    assert utility_player.inventory["Lockpick Kit"][0].charges == 2
    used, kit_message = items.use_lockpick_kit(utility_player, master=True, roll=0.0)
    assert used is True
    assert kit_message == "The Lockpick Kit breaks."
    assert "Lockpick Kit" not in utility_player.inventory
    consumed, smoke_message = items.consume_smoke_bomb(utility_player)
    assert consumed is True
    assert smoke_message == "A Smoke Bomb bursts open.\n"
    assert "Smoke Bomb" not in utility_player.inventory
    assert stolen_scroll.name == "Stolen Magic Missile Scroll"
    assert stolen_scroll.charges == 2
    assert "\n" not in stolen_scroll.description
    assert "Charges: 2" in stolen_scroll.description

    monkeypatch.setattr(items.catalog, "_rarity_table_cache", None)
    monkeypatch.setattr("src.core.items.random.choice", lambda seq: seq[0])
    rarity_table = items._build_rarity_table()
    assert items._build_rarity_table() is rarity_table
    assert all(str(index) in rarity_table for index in range(1, 9))

    low_bucket_pick = items.random_item(0)
    high_bucket_pick = items.random_item(99)
    assert low_bucket_pick is rarity_table["1"][0]
    assert high_bucket_pick is rarity_table["8"][0]

    assert items.stat_theme_for_item(items.PowerRing()) == "strength"
    assert items.stat_theme_for_item(items.RubyLocket()) == "wisdom"
    assert items.stat_theme_for_item(items.Rapier()) == "strength"
    assert items.stat_theme_for_item(items.FireChain()) == "resistance"
    assert items.stat_theme_for_item(items.IronHelm()) == "constitution"
    assert items.stat_themed_item_name(items.PowerRing()) == "Mighty Power Ring"
    assert (
        items.stat_themed_item_name(items.Item("Pebble", "A pebble.", 0, 1.0, "Misc")) == "Pebble"
    )

    assert isinstance(items.remove_equipment("Weapon"), items.NoWeapon)
    assert isinstance(items.remove_equipment("OffHand"), items.NoOffHand)
    assert isinstance(items.remove_equipment("Armor"), items.NoArmor)
    assert isinstance(items.remove_equipment("Helmet"), items.NoHelmet)
    assert isinstance(items.remove_equipment("Ring"), items.NoRing)
    assert isinstance(items.remove_equipment("Pendant"), items.NoPendant)

    assert items.equipment_slots_for_item(items.Rapier()) == ["Weapon", "OffHand"]
    assert items.equipment_slots_for_item(items.Claymore()) == ["Weapon"]
    assert items.equipment_slots_for_item(items.Buckler()) == ["OffHand"]
    assert items.equipment_slots_for_item(items.LeatherArmor()) == ["Armor"]
    assert items.equipment_slots_for_item(items.IronHelm()) == ["Helmet"]
    assert items.equipment_slots_for_item(items.PowerRing()) == ["Ring"]
    assert items.equipment_slots_for_item(items.VisionPendant()) == ["Pendant"]
    assert items.equipment_slots_for_item(items.HealthPotion()) == []
