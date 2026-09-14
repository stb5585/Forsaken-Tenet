#!/usr/bin/env python3
"""Catalog and legacy behavior coverage for enemy definitions."""

import inspect
import random
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

sys.path.insert(0, str(Path(__file__).parents[2]))

from src.core import abilities, enemies, items
from src.core.combat.battle_engine import BattleEngine
from src.core.enemies.catalog import (
    FUNHOUSE_ENEMY_SPECS,
    RANDOM_ENEMY_SPECS,
    resolve_enemy_specs,
)
from tests.test_framework import TestGameState


def _no_arg_enemy_classes():
    enemy_classes = []
    for name in dir(enemies):
        obj = getattr(enemies, name)
        if not inspect.isclass(obj):
            continue
        if not issubclass(obj, enemies.Enemy) or obj is enemies.Enemy:
            continue
        signature = inspect.signature(obj)
        required = [
            param
            for param in signature.parameters.values()
            if param.default is param.empty
            and param.kind in (param.POSITIONAL_ONLY, param.POSITIONAL_OR_KEYWORD)
        ]
        if not required:
            enemy_classes.append(obj)
    return sorted(enemy_classes, key=lambda cls: cls.__name__)


def _make_enemy(name="Scout"):
    return enemies.Enemy(name, 10, 10, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 10)


def test_no_arg_enemy_catalog_instantiates_and_renders_cleanly():
    discovered = _no_arg_enemy_classes()

    assert len(discovered) >= 100

    instantiated_names = []
    for enemy_cls in discovered:
        enemy = enemy_cls()
        instantiated_names.append(enemy.name)
        assert enemy.cls is enemy
        assert isinstance(enemy.experience, int)
        assert isinstance(enemy.enemy_typ, str)
        assert enemy.spellbook.keys() >= {"Spells", "Skills"}
        assert "Health:" in str(enemy)
        details = enemy.inspect()
        assert f"Name: {enemy.name}" in details
        assert "Type:" in details

    assert "Goblin" in instantiated_names
    assert "Hydra" in instantiated_names
    assert "Copycat" in instantiated_names


def test_random_enemy_and_funhouse_enemy_follow_expected_catalog_edges(monkeypatch):
    monkeypatch.delenv("DUNGEON_FORCE_ENEMY", raising=False)
    monkeypatch.setattr("src.core.enemies.random.choice", lambda seq: seq[0])
    assert isinstance(enemies.random_enemy("0"), enemies.GreenSlime)
    assert isinstance(enemies.random_enemy_catalog()["0"][0], enemies.GreenSlime)

    monkeypatch.setattr("src.core.enemies.random.choice", lambda seq: seq[-1])
    assert isinstance(enemies.random_enemy("999"), enemies.BrainGorger)
    assert isinstance(enemies.funhouse_enemy(), enemies.Copycat)
    assert isinstance(enemies.funhouse_enemy_catalog()[-1], enemies.Copycat)


def test_static_enemy_specs_resolve_to_the_compatibility_catalogs():
    expected_random = {
        level: tuple((display_name, class_name) for display_name, class_name in specs)
        for level, specs in RANDOM_ENEMY_SPECS.items()
    }
    resolved_random = {
        level: tuple((display_name, factory.__name__) for display_name, factory in specs)
        for level, specs in enemies._RANDOM_ENEMY_CATALOG.items()
    }
    resolved_funhouse = tuple(
        (display_name, factory.__name__)
        for display_name, factory in enemies._FUNHOUSE_ENEMY_CATALOG
    )

    assert resolved_random == expected_random
    assert resolved_funhouse == FUNHOUSE_ENEMY_SPECS


def test_enemy_spec_resolution_rejects_an_unknown_class():
    with pytest.raises(RuntimeError, match="MissingEnemy"):
        resolve_enemy_specs((("Missing", "MissingEnemy"),), {})


def test_random_enemy_instantiates_only_the_selected_catalog_entry(monkeypatch):
    calls = []

    def build_first():
        calls.append("first")
        return SimpleNamespace(name="First")

    def build_second():
        calls.append("second")
        return SimpleNamespace(name="Second")

    class LastChoiceRng:
        @staticmethod
        def choice(sequence):
            return sequence[-1]

        @staticmethod
        def random():
            return 1.0

    monkeypatch.delenv("DUNGEON_FORCE_ENEMY", raising=False)
    monkeypatch.setattr(
        enemies.encounters,
        "_RANDOM_ENEMY_CATALOG",
        {"0": (("First", build_first), ("Second", build_second))},
    )

    selected = enemies.random_enemy("0", rng=LastChoiceRng())

    assert selected.name == "Second"
    assert calls == ["second"]


def test_bestiary_practical_info_helpers_use_broad_labels():
    locations = enemies.bestiary_location_hints("Wyvern")
    assert locations == ["Dungeon Level 5", "Dungeon Level 6"]
    assert enemies.bestiary_location_hints("Mimic") == ["Chests", "Funhouse Mimic Chest"]
    assert enemies.bestiary_location_hints("Copycat") == ["Funhouse"]

    enemy = SimpleNamespace(
        inventory={
            "drops": [
                items.HealthPotion,
                items.DragonTear,
                items.BirdFat,
            ]
        }
    )

    assert enemies.bestiary_drop_hints(enemy) == [
        "Health Potion (Common)",
        "Dragon's Tear (Very Rare)",
    ]

    boss = SimpleNamespace(inventory={"drops": [items.HealthPotion, items.DragonTear]})
    assert enemies.bestiary_drop_hints(boss, boss=True) == [
        "Health Potion (Guaranteed)",
        "Dragon's Tear (Very Rare)",
    ]
    assert enemies.bestiary_uses_boss_drop_rules("Minotaur") is True
    assert enemies.bestiary_uses_boss_drop_rules("Goblin") is False


def test_random_enemy_debug_override_is_explicit_and_clearable(monkeypatch):
    monkeypatch.delenv("DUNGEON_FORCE_ENEMY", raising=False)
    monkeypatch.setattr("src.core.enemies.random.choice", lambda seq: seq[0])
    enemies.clear_random_enemy_override()

    try:
        enemies.set_random_enemy_override("Test")
        assert isinstance(enemies.random_enemy("0"), enemies.Test)

        enemies.set_random_enemy_override(enemies.Goblin)
        assert isinstance(enemies.random_enemy("0"), enemies.Goblin)

        enemies.set_random_enemy_override(lambda: enemies.Skeleton())
        assert isinstance(enemies.random_enemy("0"), enemies.Skeleton)

        enemies.clear_random_enemy_override()
        assert isinstance(enemies.random_enemy("0"), enemies.GreenSlime)
    finally:
        enemies.clear_random_enemy_override()


def test_random_enemy_debug_override_can_come_from_environment(monkeypatch):
    monkeypatch.setattr("src.core.enemies.random.choice", lambda seq: seq[0])
    enemies.clear_random_enemy_override()
    monkeypatch.setenv("DUNGEON_FORCE_ENEMY", "Test")

    try:
        assert isinstance(enemies.random_enemy("0"), enemies.Test)

        enemies.set_random_enemy_override(enemies.Goblin)
        assert isinstance(enemies.random_enemy("0"), enemies.Goblin)

        enemies.clear_random_enemy_override()
        monkeypatch.delenv("DUNGEON_FORCE_ENEMY", raising=False)
        assert isinstance(enemies.random_enemy("0"), enemies.GreenSlime)
    finally:
        enemies.clear_random_enemy_override()
        monkeypatch.delenv("DUNGEON_FORCE_ENEMY", raising=False)


def test_giant_and_owlbear_are_midgame_catalog_enemies():
    catalog = enemies.random_enemy_catalog()

    assert not any(isinstance(enemy, enemies.Giant) for enemy in catalog["3"])
    assert any(isinstance(enemy, enemies.Giant) for enemy in catalog["4"])
    assert any(isinstance(enemy, enemies.Owlbear) for enemy in catalog["3"])
    assert any(isinstance(enemy, enemies.Owlbear) for enemy in catalog["4"])

    giant = enemies.Giant()
    assert giant.enemy_typ == "Humanoid"
    assert giant.level.pro_level == 4
    assert set(giant.spellbook["Skills"]) == {
        "Charge",
        "Mortal Strike",
        "Dishearten",
    }
    assert giant.inventory == {}
    assert [entry["ability"] for entry in giant.action_stack] == [
        "Attack",
        "Charge",
        "Mortal Strike",
        "Dishearten",
    ]

    owlbear = enemies.Owlbear()
    assert owlbear.enemy_typ == "Monster"
    assert owlbear.level.pro_level == 3
    assert set(owlbear.spellbook["Spells"]) == {"Shock", "Wind Speed", "Regen"}
    assert owlbear.inventory["Feather"] == [items.Feather]
    assert owlbear.inventory["Leather"] == [items.Leather]
    regen_entry = next(entry for entry in owlbear.action_stack if entry["ability"] == "Regen")
    assert regen_entry["priority_if"] == [
        {"condition": "self_hp_pct_lt", "value": 50, "priority": enemies.ActionPriority.HIGH},
        {"condition": "self_status", "value": "Regen", "priority": enemies.ActionPriority.LOW},
    ]


def test_new_holy_and_variance_enemies_have_authored_kits_and_resistances():
    catalog = enemies.random_enemy_catalog()

    assert any(isinstance(enemy, enemies.Acolyte) for enemy in catalog["2"])
    assert any(isinstance(enemy, enemies.WarTurtle) for enemy in catalog["3"])
    assert any(isinstance(enemy, enemies.WaywardPriest) for enemy in catalog["3"])
    assert any(isinstance(enemy, enemies.Unicorn) for enemy in catalog["5"])

    acolyte = enemies.Acolyte()
    assert set(acolyte.spellbook["Spells"]) == {"Holy", "Heal"}
    assert set(acolyte.spellbook["Skills"]) == {"Counterspell"}

    giant = enemies.Giant()
    assert giant.resistance["Holy"] == -0.50
    assert giant.resistance["Poison"] == 0.50

    unicorn = enemies.Unicorn()
    assert unicorn.resistance["Holy"] == 1.50
    assert unicorn.resistance["Shadow"] == -0.25
    assert unicorn.status_immunity == ["Poison"]
    assert {"Stomp", "Gore"} == set(unicorn.spellbook["Skills"])

    turtle = enemies.WarTurtle()
    assert turtle.resistance["Electric"] == -0.50
    abilities = set(turtle.spellbook["Spells"]) | set(turtle.spellbook["Skills"])
    assert {"Reflect", "Headbutt", "Retract"} == abilities

    priest = enemies.WaywardPriest()
    assert priest.resistance["Holy"] == 0.25
    assert priest.resistance["Shadow"] == -0.25
    assert "Dazed or Confused" in priest.spellbook["Skills"]


def test_reagent_drop_sources_are_themed():
    treant = enemies.Treant()
    green_slime = enemies.GreenSlime()
    red_slime = enemies.RedSlime()
    black_slime = enemies.BlackSlime()
    brown_slime = enemies.BrownSlime()
    night_hag = enemies.NightHag()

    assert treant.inventory["Acorn"] == [items.Acorn]
    assert treant.inventory["Vine Seed"] == [items.VineSeed]
    assert green_slime.inventory["Fungus Spore"] == [items.FungusSpore]
    assert red_slime.inventory["Fungus Spore"] == [items.FungusSpore]
    assert black_slime.inventory["Fungus Spore"] == [items.FungusSpore]
    assert brown_slime.inventory["Fungus Spore"] == [items.FungusSpore]
    assert night_hag.inventory["Hemlock Root"] == [items.HemlockRoot]


def test_enemy_options_short_circuit_for_berserk_turtle_and_ice_block():
    target = TestGameState.create_player(class_name="Warrior", race_name="Human", level=1)

    berserk_enemy = _make_enemy()
    berserk_enemy.status_effects["Berserk"].active = True
    assert berserk_enemy.options(target, [], None) == ("Attack", None)

    turtle_enemy = _make_enemy()
    turtle_enemy.turtle = True
    assert turtle_enemy.options(target, [], None) == ("Nothing", None)

    ice_block_enemy = _make_enemy()
    ice_block_enemy.magic_effects["Ice Block"].active = True
    assert ice_block_enemy.options(target, [], None) == ("Nothing", None)


def test_enemy_options_continue_charging_skill_before_selecting_new_action():
    target = TestGameState.create_player(class_name="Warrior", race_name="Human", level=10)
    dragon = enemies.RedDragon()
    dragon.spellbook["Skills"]["Dragon Breath (Fire)"].charging = True

    assert dragon.options(target, [], None) == ("Use Skill", "Dragon Breath (Fire)")


def test_flame_wisp_has_elemental_healing_weaknesses_and_poison_immunity():
    enemy = enemies.FlameWisp()

    assert enemy.resistance["Fire"] > 1
    assert enemy.resistance["Ice"] < 0
    assert enemy.resistance["Water"] < 0
    assert enemy.resistance["Poison"] == 1
    assert "Poison" in enemy.status_immunity


def test_red_dragon_breath_is_centerpiece_not_constant_spell_pressure():
    dragon = enemies.RedDragon()
    breath = dragon.spellbook["Skills"]["Dragon Breath (Fire)"]
    ability_priorities = {entry["ability"]: entry["priority"] for entry in dragon.action_stack}

    assert breath.get_charge_time() == 2
    assert breath._effects[0].multiplier > 2.0
    assert dragon.combat.attack < 135
    assert dragon.combat.magic < 115
    assert ability_priorities["Volcano"] == enemies.ActionPriority.LOW
    assert ability_priorities["Photon Sphere"] == enemies.ActionPriority.LOW
    assert ability_priorities["Regen"] == enemies.ActionPriority.LOW_HP_ONLY
    assert ability_priorities["Doublecast"] == enemies.ActionPriority.NORMAL


def test_low_hp_only_priority_skips_until_threshold(monkeypatch):
    target = TestGameState.create_player(class_name="Warrior", race_name="Human", level=1)
    healer = _make_enemy(name="Test Healer")
    healer.spellbook["Spells"]["Regen"] = abilities.Regen()
    healer.action_stack = [
        {"ability": "Attack", "priority": enemies.ActionPriority.NORMAL},
        {"ability": "Regen", "priority": enemies.ActionPriority.LOW_HP_ONLY, "hp_threshold": 0.5},
    ]
    monkeypatch.setattr("src.core.enemies.random.choice", lambda seq: seq[-1])

    healer.health.current = healer.health.max
    assert healer.options(target, [], None) == ("Attack", None)

    healer.health.current = 4
    assert healer.options(target, [], None) == ("Cast Spell", "Regen")


def test_full_health_enemy_skips_heal_and_deprioritizes_regen(monkeypatch):
    target = TestGameState.create_player(class_name="Warrior", race_name="Human", level=1)
    healer = _make_enemy(name="Test Healer")
    healer.spellbook["Spells"] = {
        "Heal": abilities.Heal(),
        "Regen": abilities.Regen(),
    }
    healer.action_stack = [
        {"ability": "Attack", "priority": enemies.ActionPriority.NORMAL},
        {"ability": "Heal", "priority": enemies.ActionPriority.HIGH},
        {"ability": "Regen", "priority": enemies.ActionPriority.HIGH},
    ]
    monkeypatch.setattr("src.core.enemies.random.choice", lambda seq: seq[-1])

    assert healer.options(target, [], None) == ("Cast Spell", "Regen")
    assert healer.get_last_action_metadata()["priority"] == enemies.ActionPriority.LOW

    healer.health.current -= 1
    assert healer.options(target, [], None) == ("Cast Spell", "Regen")
    assert healer.get_last_action_metadata()["priority"] == enemies.ActionPriority.HIGH


def test_enemy_options_cover_pickup_surface_and_flee_legacy_paths(monkeypatch):
    low_level_target = TestGameState.create_player(class_name="Warrior", race_name="Human", level=1)
    weapon = items.Weapon("Test Sword", "", 0, 0.0, 1, 1, "1-Handed", "Sword", False, True)

    pickup_enemy = _make_enemy(name="Test")
    pickup_enemy.tunnel = True
    pickup_enemy.equipment["Weapon"] = weapon
    pickup_enemy.physical_effects["Disarm"].active = True
    monkeypatch.setattr(random, "choice", lambda seq: seq[0])
    assert pickup_enemy.options(low_level_target, [], None) == ("Pickup Weapon", None)

    surface_enemy = _make_enemy(name="Test")
    surface_enemy.tunnel = True
    surface_enemy.equipment["Weapon"] = weapon
    monkeypatch.setattr(random, "choice", lambda seq: seq[0])
    assert surface_enemy.options(low_level_target, [], None) == ("Surface", None)

    flee_enemy = _make_enemy(name="Scout")
    flee_target = TestGameState.create_player(class_name="Sorcerer", race_name="Human", level=10)
    monkeypatch.setattr("src.core.enemies.random.randint", lambda low, high: 1)
    monkeypatch.setattr(random, "choice", lambda seq: seq[-1])
    assert flee_enemy.options(flee_target, [], None) == ("Flee", None)


def test_required_argument_enemy_constructors_render_expected_state():
    mimic = enemies.Mimic(z=1, player_level=25)
    assert mimic.name == "Mimic"
    assert mimic.level.pro_level == 3
    assert mimic.sight is True
    assert "Name: Mimic" in mimic.inspect()

    minion = enemies.FunhouseMinion(
        name="Practice Dummy",
        health_range=(10, 10),
        mana_range=(5, 5),
        stat_range=(3, 3),
        combat_range=(4, 4),
        exp_range=(7, 7),
    )
    assert minion.name == "Practice Dummy"
    assert minion.level.pro_level == 4
    assert any(entry["ability"] == "Attack" for entry in minion.action_stack)


@pytest.mark.parametrize(
    "enemy_cls",
    [
        enemies.Zombie,
        enemies.Quasit,
        enemies.GiantScorpion,
        enemies.InvisibleStalker,
        enemies.DrowAssassin,
    ],
)
def test_non_druid_enemies_use_piercing_strike_instead_of_poison_strike(enemy_cls):
    """Enemy-only kits must not retain the Druid Poison Strike spell."""
    enemy = enemy_cls()

    assert "Poison Strike" not in enemy.spellbook["Spells"]
    assert "Poison Strike" not in enemy.spellbook["Skills"]
    assert "Piercing Strike" in enemy.spellbook["Skills"]
    assert any(entry["ability"] == "Piercing Strike" for entry in enemy.action_stack)


def test_jester_verdant_form_uses_piercing_strike_instead_of_poison_strike():
    jester = enemies.Jester()
    jester._apply_jester_form("verdant", track_cooldown=False)

    assert "Poison Strike" not in jester.spellbook["Spells"]
    assert "Poison Strike" not in jester.spellbook["Skills"]
    assert "Piercing Strike" in jester.spellbook["Skills"]
    assert any(entry["ability"] == "Piercing Strike" for entry in jester.action_stack)


@pytest.mark.parametrize(
    "enemy_cls",
    [
        enemies.Minotaur,
        enemies.Jester,
        enemies.Incubus,
        enemies.Circe,
        enemies.Merzhin,
    ],
)
def test_bosses_and_minibosses_are_immune_to_disarm(enemy_cls):
    enemy = enemy_cls()

    assert "Disarm" in enemy.status_immunity
    assert enemy.can_be_disarmed() is False


def test_enemy_legacy_options_can_select_spell_and_skill(monkeypatch):
    target = TestGameState.create_player(class_name="Warrior", race_name="Human", level=1)

    spell_enemy = _make_enemy(name="Test")
    spell_enemy.spellbook["Spells"]["Regen"] = abilities.Regen()
    monkeypatch.setattr(random, "choice", lambda seq: seq[-1])
    assert spell_enemy.options(target, [], None) == ("Cast Spell", "Regen")

    skill_enemy = _make_enemy(name="Test")
    skill_enemy.spellbook["Skills"]["Disarm"] = abilities.Disarm()
    monkeypatch.setattr(random, "choice", lambda seq: seq[-1])
    assert skill_enemy.options(target, [], None) == ("Use Skill", "Disarm")


def test_enemy_disarm_priority_skips_an_already_disarmed_target(monkeypatch):
    target = TestGameState.create_player(class_name="Warrior", race_name="Human", level=1)
    target.physical_effects["Disarm"].active = True
    enemy = _make_enemy(name="Test Disarmer")
    enemy.spellbook["Skills"]["Disarm"] = abilities.Disarm()
    enemy.action_stack = [
        {"ability": "Attack", "priority": enemies.ActionPriority.NORMAL},
        {"ability": "Disarm", "priority": enemies.ActionPriority.HIGH},
    ]
    monkeypatch.setattr("src.core.enemies.random.choice", lambda choices: choices[-1])

    assert enemy.options(target, [], None) == ("Attack", None)


def test_enemy_can_choose_and_use_combat_consumable_from_inventory(monkeypatch):
    target = TestGameState.create_player(class_name="Warrior", race_name="Human", level=1)
    potion_enemy = _make_enemy(name="Potion Goblin")
    potion_enemy.health.current = 5
    potion_enemy.state = "fight"
    potion_enemy.inventory["Health Potion"] = [items.HealthPotion]

    monkeypatch.setattr(random, "choice", lambda seq: seq[-1])
    assert potion_enemy.options(target, [], None) == ("Use Item", "Health Potion")

    engine = BattleEngine(
        target,
        potion_enemy,
        SimpleNamespace(available_actions=lambda _player: []),
    )
    engine.attacker = potion_enemy
    engine.defender = target
    monkeypatch.setattr("src.core.items.random.randint", lambda _low, high: high)

    message = engine._execute_item("Health Potion")

    assert "healed" in message
    assert potion_enemy.health.current > 5
    assert "Health Potion" not in potion_enemy.inventory


def test_enemy_can_choose_elixir_for_health_or_mana_recovery(monkeypatch):
    target = TestGameState.create_player(class_name="Warrior", race_name="Human", level=1)
    elixir_enemy = _make_enemy(name="Potion Goblin")
    elixir_enemy.health.current = elixir_enemy.health.max
    elixir_enemy.mana.current = 1
    elixir_enemy.inventory["Elixir"] = [items.Elixir]

    monkeypatch.setattr(random, "choice", lambda seq: seq[-1])

    assert elixir_enemy.options(target, [], None) == ("Use Item", "Elixir")


def test_enemy_priority_stack_can_request_specific_consumable(monkeypatch):
    target = TestGameState.create_player(class_name="Warrior", race_name="Human", level=1)
    potion_enemy = _make_enemy(name="Potion Goblin")
    potion_enemy.health.current = 5
    potion_enemy.inventory["Health Potion"] = [items.HealthPotion]
    potion_enemy.action_stack = [
        {"ability": "Use Item:Health Potion", "priority": enemies.ActionPriority.HIGH},
    ]

    monkeypatch.setattr(random, "choice", lambda seq: seq[0])

    assert potion_enemy.options(target, [], None) == ("Use Item", "Health Potion")
