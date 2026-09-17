"""Regression coverage for creature detection and weapon-hand rules."""

from pathlib import Path
from types import SimpleNamespace

import pytest
import yaml

from src.core import abilities, enemies, items
from src.core.classes import ability_mechanics
from src.core.data.ability_loader import AbilityFactory
from src.core.events import EventBus, EventType
from tests.test_framework import TestGameState

DETECT_CLASSES = (
    abilities.DetectSlime,
    abilities.DetectAnimal,
    abilities.DetectHumanoid,
    abilities.DetectFey,
    abilities.DetectFiend,
    abilities.DetectUndead,
    abilities.DetectElemental,
    abilities.DetectDragon,
    abilities.DetectMonster,
    abilities.DetectAberration,
    abilities.DetectConstruct,
)


def _player(class_name="Grandmaster of Arms"):
    return TestGameState.create_player(class_name=class_name, level=80)


def test_all_standard_enemy_families_have_timed_exclusive_detect_spells():
    player = _player("Paladin")
    player.mana.current = 100

    assert {ability().enemy_type for ability in DETECT_CLASSES} == {
        "Slime",
        "Animal",
        "Humanoid",
        "Fey",
        "Fiend",
        "Undead",
        "Elemental",
        "Dragon",
        "Monster",
        "Aberration",
        "Construct",
    }
    abilities.DetectUndead().cast_out(player)
    abilities.DetectFiend().cast_out(player)

    assert player.detect_enemy_type == "Fiend"
    assert player.detect_enemy_steps == 50
    fiend = SimpleNamespace(enemy_typ="Fiend")
    undead = SimpleNamespace(enemy_typ="Undead")
    assert abilities.detects_encounter(player, fiend, roll=0.0) is True
    assert abilities.detects_encounter(player, undead, roll=0.0) is False
    abilities.tick_detection(player, 50)
    assert player.detect_enemy_type is None


def test_yaml_weapon_skills_default_to_main_hand_with_explicit_dual_exceptions():
    ability_dir = Path("src/core/data/abilities")
    exceptions = {"Sneak Attack"}
    for path in ability_dir.glob("*.yaml"):
        raw = yaml.safe_load(path.read_text(encoding="utf-8"))
        if raw.get("type", "Skill") != "Skill" or not raw.get("weapon", False):
            continue
        ability = AbilityFactory.create_from_yaml(path, combat_ready=True)
        assert ability._use_offhand is (ability.name in exceptions), path.name


def test_flurry_uses_main_hand_and_loses_accuracy_until_first_miss(monkeypatch):
    player = _player()
    target = enemies.Goblin()
    calls = []
    hits = iter((True, True, False, True))

    def weapon_damage(_target, **kwargs):
        calls.append(kwargs)
        return "strike\n", next(hits), 1

    monkeypatch.setattr(player, "weapon_damage", weapon_damage)
    result = abilities.FlurryBlades().use(player, target)

    assert result.hit is True
    assert len(calls) == 3
    assert [call["accuracy_modifier"] for call in calls] == pytest.approx([0.0, -0.08, -0.16])
    assert all(call["use_offhand"] is False for call in calls)


def test_dual_wield_penalties_are_removed_by_excellence_then_mastery():
    player = _player()
    player.equipment["Weapon"] = items.Rapier()
    player.equipment["OffHand"] = items.Dirk()
    player.spellbook["Skills"]["Dual Wield"] = abilities.DualWield()

    assert ability_mechanics.dual_wield_accuracy_modifier(player, "Weapon") == -0.15
    assert ability_mechanics.dual_wield_accuracy_modifier(player, "OffHand") == -0.15
    player.spellbook["Skills"]["Dual Wield Excellence"] = abilities.DualWieldExcellence()
    assert ability_mechanics.dual_wield_accuracy_modifier(player, "Weapon") == 0.0
    assert ability_mechanics.dual_wield_accuracy_modifier(player, "OffHand") == -0.15
    player.spellbook["Skills"]["Dual Wield Mastery"] = abilities.DualWieldMastery()
    assert ability_mechanics.dual_wield_accuracy_modifier(player, "OffHand") == 0.0


def test_parry_is_blocked_by_shields_and_riposte_is_a_separate_skill(monkeypatch):
    attacker = enemies.Goblin()
    defender = _player("Knight Enchanter")
    defender.spellbook["Skills"]["Parry"] = abilities.Parry()
    event_bus = EventBus()
    event_bus.enable()
    events = []
    event_bus.subscribe(EventType.BLOCK, events.append)
    monkeypatch.setattr("src.core.character.offense.get_event_bus", lambda: event_bus)
    rolls = iter((0.0, 0.5, 0.9))
    monkeypatch.setattr("src.core.character.offense.random.random", lambda: next(rolls))
    monkeypatch.setattr("src.core.character.offense.random.uniform", lambda *_args: 0.5)

    defender.equipment["OffHand"] = items.KiteShield()
    assert attacker._apply_parry(defender, 20) == (20, "", False, False)

    defender.equipment["OffHand"] = items.NoOffHand()
    defender.equipment["Weapon"] = items.Dirk()
    remaining, message, parried, aborted = attacker._apply_parry(defender, 20)
    assert (remaining, parried, aborted) == (10, True, False)
    assert "ripostes" not in message
    assert len(events) == 1
    assert events[0].data["reaction"] == "parry"
    assert events[0].data["parry_style"] == "blade"
    assert events[0].data["parry_weapon_type"] == "Dagger"


def test_monocane_has_five_casting_uses_before_removal():
    player = _player("Footpad")
    player.modify_inventory(items.Monocane())

    for uses_left in range(4, -1, -1):
        used, _message = items.use_reusable_tool(player, "Monocane")
        assert used is True
        if uses_left:
            assert player.inventory["Monocane"][0].charges == uses_left
    assert not player.inventory.get("Monocane")
