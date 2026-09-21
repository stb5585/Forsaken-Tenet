#!/usr/bin/env python3
"""Coverage for tiny core helper modules with minimal existing surface."""

import sys
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).parents[2]))

from src.core.character import Character, Combat, Resource, Stats
from src.core.combat.combat_result import CombatResult
from src.core.effects.damage import DamageEffect
from src.core.effects.healing import HealEffect, RegenEffect
from src.core.effects.status import StatusEffect


def _character(
    name: str,
    *,
    hp: int = 50,
    max_hp: int = 50,
    strength: int = 0,
    wisdom: int = 0,
) -> Character:
    return Character(
        name=name,
        health=Resource(max=max_hp, current=hp),
        mana=Resource(max=20, current=20),
        stats=Stats(strength=strength, wisdom=wisdom),
        combat=Combat(),
    )


def test_damage_effect_applies_scaled_damage_to_legacy_hp_targets():
    actor = SimpleNamespace(strength=6)
    target = SimpleNamespace(hp=50)
    result = CombatResult(action="Attack", actor=actor, target=target, hit=True, crit=1)

    effect = DamageEffect(base_damage=10, scaling=0.5)
    effect.apply(actor, target, result)

    assert target.hp == 37
    assert result.damage == 13


def test_damage_effect_uses_character_stats_and_health_resource():
    actor = _character("Hero", strength=6)
    target = _character("Slime", hp=50, max_hp=50)
    result = CombatResult(action="Attack", actor=actor, target=target, hit=True, crit=1)

    effect = DamageEffect(base_damage=10, scaling=0.5)
    effect.apply(actor, target, result)

    assert target.health.current == 37
    assert result.damage == 13
    assert result.extra["last_damage"] == 13


def test_damage_effect_clamps_current_health_at_zero():
    actor = _character("Hero", strength=100)
    target = _character("Slime", hp=5, max_hp=50)
    result = CombatResult(action="Attack", actor=actor, target=target, hit=True, crit=1)

    effect = DamageEffect(base_damage=10, scaling=1.0)
    effect.apply(actor, target, result)

    assert target.health.current == 0
    assert result.damage == 110


def test_heal_effect_caps_target_healing_and_sets_result():
    user = SimpleNamespace(stats=SimpleNamespace(wisdom=8))
    target = SimpleNamespace(health=SimpleNamespace(current=12, max=20))
    result = CombatResult(action="Heal", actor=user, target=target, hit=True, crit=1)

    effect = HealEffect(base_healing=5, scaling=0.5)
    effect.apply(user, target, result)

    assert target.health.current == 20
    assert result.healing == 8


def test_heal_effect_uses_character_healing_multiplier():
    user = _character("Priest", wisdom=10)
    target = _character("Ally", hp=20, max_hp=100)
    target.status_effects["Poison"].active = True
    result = CombatResult(action="Heal", actor=user, target=target, hit=True, crit=1)

    effect = HealEffect(base_healing=10, scaling=1.0)
    effect.apply(user, target, result)

    assert target.health.current == 34
    assert result.healing == 14


def test_regen_effect_applies_magic_status_payload():
    user = SimpleNamespace(stats=SimpleNamespace(wisdom=10))
    target = SimpleNamespace(
        magic_effects={"Regen": SimpleNamespace(active=False, duration=0, extra=0)}
    )
    result = CombatResult(action="Regen", actor=user, target=target, hit=True, crit=1)

    effect = RegenEffect(base_healing=4, duration=3, scaling=0.5)
    effect.apply(user, target, result)

    regen = target.magic_effects["Regen"]
    assert regen.active is True
    assert regen.duration == 3
    assert regen.extra == 9
    assert result.effects_applied["Magic"] == ["Regen"]


def test_status_effect_activates_known_status_and_records_extra():
    actor = SimpleNamespace(name="Caster")
    target = SimpleNamespace(status_effects={"Stun": SimpleNamespace(active=False, duration=0)})
    result = CombatResult(action="Status", actor=actor, target=target, hit=True, crit=1)

    effect = StatusEffect(name="Stun", duration=2)
    effect.apply(actor, target, result)

    assert target.status_effects["Stun"].active is True
    assert target.status_effects["Stun"].duration == 2
    assert result.effects_applied["Status"] == ["Stun"]
    assert result.extra["status_effect"] == "Stun"
