"""
Test suite for weapon and armor special effects after CombatResultGroup refactor.
Tests:
1. Life steal (VampireBite)
2. Instant death (Ninjato)
3. Stun effects (Mjolnir, Onikiri)
4. Leer/Gaze petrification
"""

import os
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[2]))

import pytest

from src.core import items
from src.core.character import Character, Combat, Level, Resource, Stats
from src.core.combat.combat_result import CombatResult, CombatResultGroup


def create_test_character(name="TestChar", level_num=10):
    """Create a simple test character using proper Character initialization."""
    stats = Stats(strength=20, intel=20, wisdom=20, con=20, charisma=10, dex=20)
    combat = Combat(attack=15, defense=10, magic=15, magic_def=10)
    health = Resource(current=100, max=100)
    mana = Resource(current=50, max=50)

    char = Character(name=name, health=health, mana=mana, stats=stats, combat=combat)
    char.level = Level(level=level_num, pro_level=level_num, exp=0)
    char.resistance = {}  # Simple dict for resistance

    # Initialize equipment with basic items
    char.equipment = {
        "Weapon": items.NoWeapon(),
        "OffHand": items.NoOffHand(),
        "Armor": items.NoArmor(),
        "Ring": items.NoRing(),
        "Pendant": items.NoPendant(),
    }

    # Initialize status effects using StatusEffect dataclass
    from src.core.character import StatusEffect

    char.status_effects = {
        "Stun": StatusEffect(),
        "Sleep": StatusEffect(),
        "Poison": StatusEffect(),
        "Blind": StatusEffect(),
        "Berserk": StatusEffect(),
    }
    char.status_immunity = []

    # Initialize magic/physical effects dicts
    char.magic_effects = {
        "Mana Shield": StatusEffect(),
        "Ice Block": StatusEffect(),
        "Duplicates": StatusEffect(),
    }
    char.physical_effects = {"Disarm": StatusEffect()}
    char.class_effects = {"Power Up": StatusEffect()}

    # Other combat attributes
    char.invisible = False
    char.flying = False
    char.tunnel = False

    # Initialize spellbook
    char.spellbook = {"Skills": [], "Spells": []}

    # Add cls mock for class checks
    class MockClass:
        name = "Warrior"

    char.cls = MockClass()
    char.power_up = False

    return char


def test_vampire_bite_life_steal(monkeypatch):
    """Test that VampireBite drains health on critical hits."""
    attacker = create_test_character("Vampire", level_num=10)
    defender = create_test_character("Victim", level_num=5)

    # Equip VampireBite
    attacker.equipment["Weapon"] = items.VampireBite()

    # Set attacker to low health
    attacker.health.current = 50
    initial_health = attacker.health.current

    # Create a combat result with damage
    result = CombatResult(
        action="Weapon",
        actor=attacker,
        target=defender,
        hit=True,
        crit=2.0,  # Critical hit
        damage=20,
    )
    results = CombatResultGroup()
    results.add(result)

    monkeypatch.setattr(random, "random", lambda: 0.0)

    # Call special_effect
    attacker.equipment["Weapon"].special_effect(results)

    assert results.results[-1].extra["Drain"] is True
    assert attacker.health.current == initial_health + 20


@pytest.mark.parametrize("bite_cls", [items.Bite, items.Bite2])
def test_bite_disease_reports_constitution_loss_in_combat(monkeypatch, bite_cls):
    """A successful Bite disease proc must surface its permanent CON penalty."""
    attacker = create_test_character("Biter")
    defender = create_test_character("Victim")
    attacker.equipment["Weapon"] = bite_cls()
    starting_con = defender.stats.con

    monkeypatch.setattr(random, "random", lambda: 0.0)
    monkeypatch.setattr(random, "randint", lambda _low, _high: 0)

    message = attacker._apply_equipment_effects(defender, "Weapon", damage=10, crit=1)

    assert defender.stats.con == starting_con - 1
    assert "contracts a disease" in message
    assert "constitution is reduced by 1" in message.lower()


def test_demon_claw_reports_doom_message():
    """Demon Claw should surface the Doom message when its special applies."""
    from src.core.character import StatusEffect

    attacker = create_test_character("Demon", level_num=20)
    defender = create_test_character("Victim", level_num=5)
    attacker.stats.charisma = 200
    defender.stats.wisdom = 1
    defender.status_effects["Doom"] = StatusEffect()

    result = CombatResult(
        action="Weapon",
        actor=attacker,
        target=defender,
        hit=True,
        crit=2.0,
        damage=20,
    )
    results = CombatResultGroup()
    results.add(result)

    items.DemonClaw().special_effect(results)

    assert defender.status_effects["Doom"].active is True
    assert "timer has been placed" in results.results[0].message.lower()


def test_ninjato_instant_death(monkeypatch):
    """Test that Ninjato can instant kill on critical hits."""
    attacker = create_test_character("Ninja", level_num=20)
    defender = create_test_character("Victim", level_num=5)

    # Equip Ninjato
    attacker.equipment["Weapon"] = items.Ninjato()
    attacker.stats.strength = 50
    attacker.stats.luck = 50

    # Create a combat result with critical hit
    result = CombatResult(
        action="Weapon",
        actor=attacker,
        target=defender,
        hit=True,
        crit=2.0,  # Critical hit
        damage=40,
    )
    results = CombatResultGroup()
    results.add(result)

    rolls = iter([100, 0])
    monkeypatch.setattr(random, "randint", lambda _a, _b: next(rolls))

    # Call special_effect
    attacker.equipment["Weapon"].special_effect(results)

    assert results.results[-1].extra["Instant Death"] is True


def test_gaze_petrification(monkeypatch):
    """Test that Gaze (Leer) attack properly sets up petrification."""
    attacker = create_test_character("Gorgon", level_num=10)
    defender = create_test_character("Victim", level_num=5)

    # Equip Gaze weapon
    attacker.equipment["Weapon"] = items.Gaze()

    # Create a combat result
    result = CombatResult(
        action="Leer", actor=attacker, target=defender, hit=True, crit=1, damage=0
    )
    results = CombatResultGroup()
    results.add(result)

    petrify_calls = []

    class FakePetrify:
        def cast(self, actor, target, special=False):
            petrify_calls.append((actor, target, special))
            return ""

    monkeypatch.setattr("src.core.items.weapons.abilities.Petrify", lambda: FakePetrify())

    attacker.equipment["Weapon"].special_effect(results)

    assert results.results[-1].extra["leers"] is True
    assert petrify_calls == [(attacker, defender, True)]


def test_mjolnir_stun(monkeypatch):
    """Test that Mjolnir stuns on critical hits."""
    attacker = create_test_character("Thor", level_num=15)
    defender = create_test_character("Victim", level_num=10)

    # Equip Mjolnir
    attacker.equipment["Weapon"] = items.Mjolnir()
    attacker.stats.strength = 40

    # Defender should not be immune to stun
    defender.status_immunity = []

    # Create a combat result with critical hit
    result = CombatResult(
        action="Weapon",
        actor=attacker,
        target=defender,
        hit=True,
        crit=2.0,  # Critical hit (float, not list)
        damage=35,
    )
    results = CombatResultGroup()
    results.add(result)

    monkeypatch.setattr(random, "randint", lambda _a, _b: _b)
    monkeypatch.setattr(defender, "stun_contest_success", lambda *_args, **_kwargs: True)

    # Call special_effect
    attacker.equipment["Weapon"].special_effect(results)

    assert results.results[-1].target.status_effects["Stun"].active is True
    assert results.results[-1].target.status_effects["Stun"].duration == 4
    assert "Stun" in results.results[-1].effects_applied["Status"]


def test_armor_special_effect():
    """Test that armor special effects can be called."""
    attacker = create_test_character("Attacker", level_num=10)
    defender = create_test_character("Defender", level_num=10)

    # Equip basic armor
    defender.equipment["Armor"] = items.NoArmor()

    # Create a combat result
    result = CombatResult(
        action="Weapon", actor=attacker, target=defender, hit=True, crit=1.5, damage=25
    )
    results = CombatResultGroup()
    results.add(result)

    returned = defender.equipment["Armor"].special_effect(results)

    assert returned is None
    assert results.results[-1].damage == 25
    assert results.results[-1].effects_applied == {
        "Status": [],
        "Physical": [],
        "Stat": [],
        "Magic": [],
        "Class": [],
    }


def _armor_hit_result(attacker, defender, damage=40):
    result = CombatResult(
        action="Weapon",
        actor=attacker,
        target=defender,
        hit=True,
        crit=1.0,
        damage=damage,
        healing=0,
    )
    results = CombatResultGroup()
    results.add(result)
    return results


def test_ultimate_armor_special_effects_cover_magic_fire_lightning_and_recovery(monkeypatch):
    attacker = create_test_character("Attacker", level_num=10)
    defender = create_test_character("Defender", level_num=10)

    defender.mana.current = 10
    defender.equipment["Armor"] = items.MerlinRobe()
    msg = attacker._apply_equipment_effects(defender, "Weapon", 40, 1)
    assert defender.mana.current == 20
    assert "restore 10 mana" in msg

    defender.mana.current = 10
    results = _armor_hit_result(attacker, defender, damage=40)
    items.MerlinRobe().special_effect(results)
    assert defender.mana.current == 20
    assert results[-1].extra["Mana Restored"] == 10
    assert "restore 10 mana" in results[-1].message

    attacker.health.current = 100
    results = _armor_hit_result(attacker, defender, damage=40)
    items.DragonHide().special_effect(results)
    assert attacker.health.current == 90
    assert results[-1].extra["Dragon Hide Damage"] == 10
    assert "Fire" in results[-1].effects_applied["Magic"]

    attacker.health.current = 100
    monkeypatch.setattr(random, "random", lambda: 0.0)
    results = _armor_hit_result(attacker, defender, damage=40)
    items.Klivanion().special_effect(results)
    assert attacker.health.current == 94
    assert results[-1].extra["Klivanion Shock Damage"] == 6
    assert attacker.status_effects["Stun"].active is True
    assert "Stun" in results[-1].effects_applied["Status"]

    defender.health.current = 60
    results = _armor_hit_result(attacker, defender, damage=40)
    items.Genji().special_effect(results)
    assert defender.health.current == 68
    assert results[-1].healing == 8
    assert results[-1].extra["Genji Damage Recovered"] == 8


def test_elemental_armor_metadata_contributes_character_resistance():
    defender = create_test_character("Defender", level_num=10)
    defender.resistance["Fire"] = 0.1
    defender.equipment["Armor"] = items.DragonHide()

    assert defender.check_mod("resist", typ="Fire") == pytest.approx(0.35)
    assert defender.check_mod("resist", typ="Ice") == pytest.approx(0)


def test_ruyi_jingu_bang_is_master_monk_chi_conduit(monkeypatch):
    """Ruyi Jingu Bang is the Master Monk ultimate staff and can build Ki."""
    from src.core.classes import promotion_kits

    attacker = create_test_character("Monk", level_num=30)
    defender = create_test_character("Target", level_num=30)
    attacker.cls = type("MockClass", (), {"name": "Master Monk"})()
    attacker.equipment["Weapon"] = items.RuyiJinguBang()
    promotion_kits.start_combat(attacker)

    result = CombatResult(
        action="Weapon",
        actor=attacker,
        target=defender,
        hit=True,
        crit=1,
        damage=20,
    )
    results = CombatResultGroup()
    results.add(result)
    monkeypatch.setattr(random, "random", lambda: 0.0)

    attacker.equipment["Weapon"].special_effect(results)

    assert promotion_kits.combat_state(attacker)["ki"] == 1
    assert "Ruyi Jingu Bang" in results[-1].message


def test_ultimate_staff_selection_is_class_specific():
    from src.core.classes.archbishop import Archbishop
    from src.core.classes.master_monk import MasterMonk
    from src.core.classes.wizard import Wizard

    archbishop = type("Player", (), {"cls": Archbishop()})()
    master_monk = type("Player", (), {"cls": MasterMonk()})()
    wizard = type("Player", (), {"cls": Wizard()})()

    assert dict(items.ultimate_weapon_options_for(archbishop))["Staff"] is items.PrincessGuard
    assert dict(items.ultimate_weapon_options_for(master_monk))["Staff"] is items.RuyiJinguBang
    assert dict(items.ultimate_weapon_options_for(wizard))["Staff"] is items.DragonStaff


def main():
    """Run all tests."""
    print("=" * 70)
    print("WEAPON SPECIAL EFFECTS TEST SUITE")
    print("=" * 70)

    tests = [
        test_vampire_bite_life_steal,
        test_ninjato_instant_death,
        test_gaze_petrification,
        test_mjolnir_stun,
        test_armor_special_effect,
    ]

    passed = 0
    failed = 0

    for test in tests:
        try:
            test()
            passed += 1
        except AssertionError:
            failed += 1
        except Exception as e:
            print(f"\n✗ Test {test.__name__} failed with error: {e}")
            import traceback

            traceback.print_exc()
            failed += 1

    print("\n" + "=" * 70)
    print(f"RESULTS: {passed} passed, {failed} failed")
    print("=" * 70)

    return failed == 0


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
