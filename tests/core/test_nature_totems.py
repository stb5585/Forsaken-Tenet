"""Coverage for Shaman/Soulcatcher nature Totem mechanics."""

from __future__ import annotations

from types import SimpleNamespace

from src.core import abilities, items, map_tiles
from src.core.classes import class_rings, nature_totems, promotion_kits
from src.core.combat.battle_engine import BattleEngine
from src.core.combat.combat_result import CombatResult
from src.core.effects.skills import ElementalStrikeEffect
from src.core.save_system import PlayerDataSerializer
from tests.test_framework import TestGameState


class DummyCombatTile:
    def available_actions(self, _player):
        return ["Attack", "Cast Spell", "Use Skill", "Flee"]


class DummyRng:
    def __init__(self, value):
        self.value = value

    def random(self):
        return self.value


class PulseSpell:
    def __init__(self, name, subtyp, damage=20):
        self.name = name
        self.subtyp = subtyp
        self.cost = 99
        self.damage = damage
        self.cast_count = 0

    def cast(self, caster, target=None, **_kwargs):
        self.cast_count += 1
        amount = int(self.damage * nature_totems.spell_output_multiplier(caster, self))
        if target is not None:
            target.health.current -= amount
        self.result = CombatResult(
            action=self.name,
            actor=caster,
            target=target,
            hit=amount > 0,
            damage=amount,
        )
        return f"{self.name} hits for {amount}.\n"


def _active_totem(player, aspect):
    player.magic_effects["Totem"].active = True
    player.magic_effects["Totem"].duration = 5
    player.magic_effects["Totem"].extra = {
        "aspect": aspect,
        "secondary": "water_ward" if aspect == "Water" else "elemental",
    }


def test_elemental_communion_unlocks_only_for_shaman_and_does_not_duplicate():
    shaman = TestGameState.create_player(class_name="Shaman", race_name="Human")
    unlocked, message = nature_totems.unlock_communion(shaman, "Earth")

    assert unlocked is True
    assert "Earthquake" in shaman.spellbook["Spells"]
    assert "learns Earthquake" in message

    unlocked_again, repeat_message = nature_totems.unlock_communion(shaman, "Earth")
    assert unlocked_again is False
    assert "already bound" in repeat_message

    warrior = TestGameState.create_player(class_name="Warrior", race_name="Human")
    unlocked_warrior, warrior_message = nature_totems.unlock_communion(warrior, "Earth")
    assert unlocked_warrior is False
    assert "does not answer" in warrior_message
    assert "Earthquake" not in warrior.spellbook["Spells"]


def test_load_tiles_places_floor_three_strange_draft_and_unlocks_wind():
    shaman = TestGameState.create_player(class_name="Shaman", race_name="Human")
    shaman.load_tiles()

    tile = shaman.world_dict[nature_totems.WIND_COMMUNION_POS]

    assert isinstance(tile, map_tiles.StrangeDraftTile)
    message = tile.special_text(SimpleNamespace(player_char=shaman))
    assert "learns Tornado" in message
    assert "Tornado" in shaman.spellbook["Spells"]

    warrior = TestGameState.create_player(class_name="Warrior", race_name="Human")
    assert tile.special_text(SimpleNamespace(player_char=warrior)) == ""


def test_communion_spell_round_trips_through_save_serializer():
    shaman = TestGameState.create_player(class_name="Shaman", race_name="Human")
    nature_totems.unlock_communion(shaman, "Water")

    data = PlayerDataSerializer.serialize(shaman)
    restored = PlayerDataSerializer.deserialize(data, skip_tiles=True)

    assert "Tsunami" in restored.spellbook["Spells"]


def test_totem_pulse_uses_highest_unlocked_spell_half_potency_and_no_mana():
    player = TestGameState.create_player(class_name="Shaman", race_name="Human", mana=(100, 100))
    enemy = TestGameState.create_player(class_name="Warrior", race_name="Human", health=(100, 100))
    player.spellbook["Spells"]["Scorch"] = PulseSpell("Scorch", "Fire", damage=10)
    player.spellbook["Spells"]["Fireball"] = PulseSpell("Fireball", "Fire", damage=40)
    _active_totem(player, "Fire")

    message = nature_totems.resolve_totem_pulse(player, enemy, rng=DummyRng(0.0))

    assert "Fire Totem pulses with Fireball" in message
    assert enemy.health.current == 80
    assert player.mana.current == 100
    assert player.spellbook["Spells"]["Scorch"].cast_count == 0
    assert player.spellbook["Spells"]["Fireball"].cast_count == 1
    assert promotion_kits.totem_resonance(player) == 1


def test_aspect_evolution_strengthens_soul_surge_without_becoming_lethal():
    player = TestGameState.create_player(
        class_name="Soulcatcher",
        race_name="Human",
        mana=(100, 100),
    )
    enemy = TestGameState.create_player(
        class_name="Warrior",
        race_name="Human",
        health=(100, 100),
    )
    player.equipment["Ring"] = items.ClassRing()
    class_rings.ensure_state(player)["awakened"]["Soulcatcher"] = True
    player.equipment["Ring"].class_mod(player)
    for enemy_type in ("Animal", "Fiend", "Undead"):
        class_rings.record_soul_harvest(player, enemy_type)
    player.spellbook["Spells"]["Soul Drain"] = abilities.SoulDrain()
    _active_totem(player, "Soul")
    player.magic_effects["Totem"].extra["resonance"] = 4

    message = promotion_kits.totem_surge(player, enemy)

    assert "spends 4 Totem Resonance" in message
    assert 1 <= enemy.health.current < 95
    assert promotion_kits.totem_resonance(player) == 0


def test_staff_increases_totem_pulse_chance_but_not_potency():
    player = TestGameState.create_player(
        class_name="Shaman",
        race_name="Human",
        equipment={"Weapon": "Mithrilshod Staff"},
    )
    enemy = TestGameState.create_player(class_name="Warrior", race_name="Human", health=(100, 100))
    player.spellbook["Spells"]["Tornado"] = PulseSpell("Tornado", "Wind", damage=40)
    _active_totem(player, "Wind")

    message = nature_totems.resolve_totem_pulse(player, enemy, rng=DummyRng(0.40))

    assert "Wind Totem pulses with Tornado" in message
    assert enemy.health.current == 80


def test_matching_staff_and_totem_amplify_player_cast_spell_only():
    player = TestGameState.create_player(
        class_name="Shaman",
        race_name="Human",
        equipment={"Weapon": "Mithrilshod Staff"},
    )
    spell = PulseSpell("Tornado", "Wind", damage=50)
    player.spellbook["Spells"]["Tornado"] = spell
    enemy = TestGameState.create_player(class_name="Warrior", race_name="Human", health=(100, 100))
    _active_totem(player, "Wind")

    message = spell.cast(player, target=enemy)

    assert "hits for 60" in message
    assert enemy.health.current == 40


def test_elemental_strike_forces_active_totem_aspect():
    player = TestGameState.create_player(class_name="Shaman", race_name="Human")
    enemy = TestGameState.create_player(class_name="Warrior", race_name="Human", health=(100, 100))
    fireball = PulseSpell("Fireball", "Fire", damage=20)
    water = PulseSpell("Water Jet", "Water", damage=20)
    player.spellbook["Spells"]["Fireball"] = fireball
    player.spellbook["Spells"]["Water Jet"] = water
    _active_totem(player, "Fire")
    result = CombatResult(action="Elemental Strike", actor=player, target=enemy)
    result.hit = True

    ElementalStrikeEffect().apply(player, enemy, result)

    assert fireball.cast_count == 1
    assert water.cast_count == 0


def test_water_totem_magic_defense_and_spell_absorption():
    player = TestGameState.create_player(class_name="Shaman", race_name="Human", health=(100, 50))
    base_magic_def = player.check_mod("magic def")
    _active_totem(player, "Water")

    assert player.check_mod("magic def") == int(base_magic_def * 1.20)

    damage, message = nature_totems.water_ward_absorb(player, 40)
    assert damage == 30
    assert player.health.current == 60
    assert "absorbs 10 spell damage" in message


def test_soul_drain_is_nonlethal_and_soul_totem_pulse_is_half_strength():
    player = TestGameState.create_player(
        class_name="Soulcatcher",
        race_name="Human",
        spells=["Soul Drain"],
        mana=(100, 100),
    )
    enemy = TestGameState.create_player(class_name="Warrior", race_name="Human", health=(100, 100))

    message = abilities.SoulDrain().cast(player, target=enemy)
    assert "drains 10 hit points" in str(message)
    assert enemy.health.current == 90

    enemy.health.current = 5
    abilities.SoulDrain().cast(player, target=enemy)
    assert enemy.health.current == 4

    enemy.health.current = 100
    _active_totem(player, "Soul")
    pulse = nature_totems.resolve_totem_pulse(player, enemy, rng=DummyRng(0.0))
    assert "Soul Totem pulses with Soul Drain" in pulse
    assert enemy.health.current == 95


def test_battle_engine_post_turn_runs_player_totem_pulse():
    player = TestGameState.create_player(class_name="Shaman", race_name="Human")
    enemy = TestGameState.create_player(class_name="Warrior", race_name="Human", health=(100, 100))
    player.spellbook["Spells"]["Tsunami"] = PulseSpell("Tsunami", "Water", damage=40)
    _active_totem(player, "Water")
    engine = BattleEngine(player, enemy, DummyCombatTile())
    engine.attacker = player
    engine.defender = enemy

    from src.core.classes import nature_totems as nature_module

    original = nature_module.random.random
    nature_module.random.random = lambda: 0.0
    try:
        result = engine.post_turn()
    finally:
        nature_module.random.random = original

    assert any("Water Totem pulses with Tsunami" in message for message in result.messages)
    assert enemy.health.current == 80
