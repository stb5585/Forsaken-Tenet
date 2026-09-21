"""Regression coverage for Berserker and Grandmaster authored trees."""

from __future__ import annotations

import pytest

from src.core import abilities, items
from src.core.classes import ability_mechanics, grandmaster
from src.core.combat import CombatEncounter
from src.core.combat.battle_engine import BattleEngine
from src.core.progression import (
    ABILITY_TREES,
    NodeKind,
    ensure_progression,
    purchase_node,
)
from src.core.save_system import PlayerDataSerializer
from tests.test_framework import TestGameState


class _CombatTile:
    def available_actions(self, _player):
        return ["Attack"]


def _player(class_name: str):
    player = TestGameState.create_player(
        class_name=class_name,
        race_name="Human",
        level=100,
        pro_level=3,
        stats={
            "strength": 30,
            "intel": 20,
            "wisdom": 15,
            "con": 25,
            "charisma": 12,
            "dex": 28,
        },
    )
    state = ensure_progression(player)
    state.level = 100
    state.unspent_points = 60
    return player


def test_berserker_tree_has_centered_development_and_heavy_weapon_arts():
    tree = ABILITY_TREES["Berserker"]
    by_name = {node.name: node for node in tree.nodes}
    expected_positions = {
        "Monkey Grip": (0, 1),
        "Momentum": (0, 2),
        "Tectonic Rift": (0, 4),
        "Monkey Grip 2": (0, 5),
        "Mortal Strike 2": (1, 1),
        "Boomerang Toss": (1, 2),
        "+30 Attack": (1, 3),
        "Thunderous Vault": (1, 4),
        "Triple Strike": (1, 5),
        "Frenzy": (2, 1),
        "Hemorrhage Thirst": (2, 3),
        "Fatality": (2, 4),
        "Composed Wrath": (2, 5),
        "Parry": (3, 1),
        "Pain Tolerance": (3, 2),
        "Final Assault": (3, 3),
        "Reckless Onslaught": (3, 4),
    }
    expected_levels = {
        "Momentum": 65,
        "Tectonic Rift": 75,
        "Monkey Grip 2": 80,
        "Boomerang Toss": 65,
        "Thunderous Vault": 75,
        "Triple Strike": 80,
        "Pain Tolerance": 65,
        "Final Assault": 70,
        "Hemorrhage Thirst": 70,
        "Fatality": 75,
        "Composed Wrath": 80,
        "Reckless Onslaught": 75,
    }

    assert "Bloodied Ferocity" not in by_name
    assert "Scarred Endurance" not in by_name
    for name, position in expected_positions.items():
        assert by_name[name].position == position
    assert "level_requirement" not in by_name["Frenzy"].payload
    assert "level_requirement" not in by_name["Parry"].payload
    assert by_name["Hemorrhage Thirst"].payload["ability_class"]().passive is True
    assert by_name["+30 Attack"].payload["amount"] == 30
    assert by_name["Reckless Onslaught"].prerequisites == (by_name["Final Assault"].id,)
    assert by_name["Monkey Grip 2"].prerequisites == (by_name["Tectonic Rift"].id,)
    assert by_name["Momentum"].prerequisites == (by_name["Monkey Grip"].id,)
    assert by_name["Tectonic Rift"].prerequisites == (by_name["Momentum"].id,)
    assert by_name["Fatality"].prerequisites == (by_name["Hemorrhage Thirst"].id,)
    assert by_name["Composed Wrath"].prerequisites == (by_name["Fatality"].id,)
    assert not hasattr(
        by_name["Reckless Onslaught"].payload["ability_class"],
        "replaces",
    )
    for name in ("Monkey Grip 2", "Triple Strike", "Composed Wrath", "Reckless Onslaught"):
        assert by_name[name].cost == 2
    for name, level in expected_levels.items():
        assert by_name[name].payload["level_requirement"] == level

    art_nodes = [node for node in tree.nodes if node.payload.get("weapon_specialization")]
    assert len(art_nodes) == 8
    assert {
        node.payload["weapon_specialization"][0] for node in art_nodes
    } == grandmaster.TWO_HANDED_WEAPONS
    assert all("level_requirement" not in node.payload for node in art_nodes)
    assert {node.position[0] for node in art_nodes} == {4, 5}
    assert {node.position[1] for node in art_nodes} == {2, 3, 4, 5}


def test_grandmaster_tree_has_three_rank_gated_art_levels_and_floating_talents():
    tree = ABILITY_TREES["Grandmaster of Arms"]
    by_name = {node.name: node for node in tree.nodes}
    art_nodes = [node for node in tree.nodes if node.payload.get("weapon_specialization")]

    assert len(art_nodes) == 24
    assert {node.payload["weapon_specialization"][1] for node in art_nodes} == {
        1,
        5,
        10,
    }
    assert all("level_requirement" not in node.payload for node in art_nodes)
    for base_name in grandmaster.WEAPON_ARTS.values():
        assert by_name[f"{base_name} 2"].prerequisites == (by_name[base_name].id,)
        assert by_name[f"{base_name} 3"].prerequisites == (by_name[f"{base_name} 2"].id,)
        assert by_name[f"{base_name} 3"].payload["ability_class"].replaces == f"{base_name} 2"

    perfect_form = by_name["Perfect Form"]
    adaptive_arsenal = by_name["Adaptive Arsenal"]
    double_strike = by_name["Double Strike"]
    weapon_swap = by_name["Weapon Swap"]
    assert perfect_form.kind == NodeKind.TALENT
    assert adaptive_arsenal.kind == NodeKind.TALENT
    assert perfect_form.prerequisites == (weapon_swap.id,)
    assert adaptive_arsenal.prerequisites == (weapon_swap.id,)
    assert perfect_form.payload["level_requirement"] == 75
    assert adaptive_arsenal.payload["level_requirement"] == 75
    assert weapon_swap.payload["level_requirement"] == 70
    assert "level_requirement" not in double_strike.payload
    assert double_strike.payload["owned_if_known"] is True
    assert perfect_form.cost == 2
    assert adaptive_arsenal.cost == 2
    assert double_strike.position == (4, 1)
    assert weapon_swap.position == (4, 3)
    assert perfect_form.position == (3, 4)
    assert adaptive_arsenal.position == (5, 4)
    assert by_name["Dual Wield Excellence"].position == (4, 2)
    assert by_name["Dual Wield Mastery"].position == (4, 5)


def test_frenzy_forces_three_turn_berserk_and_adds_critical_chance():
    player = _player("Berserker")
    player.equipment["Weapon"] = items.Bastard()
    before = player.critical_chance("Weapon")

    result = abilities.Frenzy().use(player)

    berserk = player.status_effects["Berserk"]
    assert result.message
    assert berserk.active is True
    assert berserk.duration == 3
    assert berserk.source == "Frenzy"
    assert player.critical_chance("Weapon") == pytest.approx(before + 0.15)


def test_composed_wrath_restores_action_choice_during_frenzy():
    player = _player("Berserker")
    enemy = _player("Grandmaster of Arms")
    engine = BattleEngine(player, enemy, _CombatTile())
    engine.attacker = player
    abilities.Frenzy().use(player)

    forced = engine.get_forced_action()
    assert forced is not None and forced.intent is not None
    assert forced.intent.action_id == "system.attack"

    player.spellbook["Skills"]["Composed Wrath"] = abilities.ComposedWrath()

    assert engine.get_forced_action() is None


def test_fatality_forces_a_surviving_target_to_counterattack(monkeypatch):
    player = _player("Berserker")
    target = _player("Grandmaster of Arms")
    player.equipment["Weapon"] = items.Bastard()
    target.equipment["Weapon"] = items.Bastard()
    player.mana.current = 100
    counterattacks = []

    def fatality_strike(defender, **_kwargs):
        defender.health.current -= 20
        return "Fatality strike.\n", True, 1

    def counterattack(defender, **kwargs):
        counterattacks.append(kwargs)
        defender.health.current -= 10
        return "Counterattack.\n", True, 1

    monkeypatch.setattr(player, "weapon_damage", fatality_strike)
    monkeypatch.setattr(target, "weapon_damage", counterattack)
    before_health = player.health.current

    result = abilities.Fatality().use(player, target)

    assert result.damage == 20
    assert player.health.current == before_health - 10
    assert player._last_attack_parried is True
    assert len(counterattacks) == 1
    assert "parries" in result.message


def test_fatality_heals_fifteen_percent_max_health_on_a_kill(monkeypatch):
    player = _player("Berserker")
    target = _player("Grandmaster of Arms")
    player.equipment["Weapon"] = items.Bastard()
    player.mana.current = 100
    player.health.max = 200
    player.health.current = 100
    target.health.current = 20

    def fatality_strike(defender, **_kwargs):
        defender.health.current -= 40
        return "Fatality strike.\n", True, 1

    monkeypatch.setattr(player, "weapon_damage", fatality_strike)

    result = abilities.Fatality().use(player, target)

    assert target.is_alive() is False
    assert result.damage == 20
    assert player.health.current == 130
    assert "recovers 30 health" in result.message


def test_tectonic_rift_hits_all_enemies_but_only_prones_grounded_targets():
    player = _player("Berserker")
    grounded = _player("Grandmaster of Arms")
    flying = _player("Grandmaster of Arms")
    flying.flying = True
    player.equipment["Weapon"] = items.Bastard()
    player.equipment["OffHand"] = items.Bastard()
    player.mana.current = 100
    encounter = CombatEncounter.from_enemies([grounded, flying])
    engine = BattleEngine(player, encounter=encounter, tile=_CombatTile())
    engine.attacker = player
    engine.defender = grounded
    ability = abilities.TectonicRift()
    targets = [(member.combatant_id, member.enemy) for member in encounter.members]

    result = ability.use_group(player, targets, battle_engine=engine)

    assert len(result.results) == 2
    assert grounded.physical_effects["Prone"].active is True
    assert flying.physical_effects["Prone"].active is False
    assert grounded.health.current < grounded.health.max
    assert flying.health.current < flying.health.max
    assert player.mana.current == 100 - ability.cost


def test_thunderous_vault_strikes_twice_and_shocks_the_enemy_group(monkeypatch):
    player = _player("Berserker")
    primary = _player("Grandmaster of Arms")
    secondary = _player("Grandmaster of Arms")
    player.equipment["Weapon"] = items.Bastard()
    player.equipment["OffHand"] = items.Bastard()
    player.mana.current = 100
    encounter = CombatEncounter.from_enemies([primary, secondary])
    BattleEngine(player, encounter=encounter, tile=_CombatTile())
    attack_slots = []

    def attack(defender, **kwargs):
        attack_slots.append(kwargs["attack_slots"])
        defender.health.current -= 10
        return "Vault strike.\n", True, 1

    monkeypatch.setattr(player, "weapon_damage", attack)
    monkeypatch.setattr("src.core.abilities.skills.random.random", lambda: 0.0)
    ability = abilities.ThunderousVault()

    result = ability.use(player, primary)

    assert attack_slots == [("Weapon",), ("OffHand",)]
    assert primary.health.current < primary.health.max - 20
    assert secondary.health.current < secondary.health.max
    assert primary.status_effects["Stun"].active is True
    assert secondary.status_effects["Stun"].active is True
    assert player.mana.current == 100 - ability.cost
    assert result.damage > 20


def test_weapon_swap_equips_the_selected_carried_weapon():
    player = _player("Grandmaster of Arms")
    player.equipment["Weapon"] = items.Bastard()
    replacement = items.Mace()
    player.inventory[replacement.name] = [replacement]

    message = abilities.WeaponSwap().use(player, weapon=replacement)

    assert player.equipment["Weapon"] is replacement
    assert "Bastard Sword" in player.inventory
    assert "swaps Bastard Sword for Mace" in message


def test_reckless_onslaught_stacks_tradeoff_and_prones_user_when_parried(
    monkeypatch,
):
    player = _player("Berserker")
    target = _player("Grandmaster of Arms")
    player.equipment["Weapon"] = items.Bastard()
    player.mana.current = 100
    damage_modifiers = []

    def attack(defender, **kwargs):
        damage_modifiers.append(kwargs["dmg_mod"])
        player._last_attack_parried = len(damage_modifiers) == 1
        defender.health.current -= 20
        return "Onslaught attack.\n", True, 1

    monkeypatch.setattr(player, "weapon_damage", attack)
    ability = abilities.RecklessOnslaught()

    first = ability.use(player, target)
    first_message = first.message
    first_damage = first.damage
    second = ability.use(player, target)

    assert damage_modifiers == [2.0, 2.0]
    assert first_damage == 20
    assert second.damage == 20
    assert player.stat_effects["Attack"].extra == 10
    assert player.stat_effects["Defense"].extra == -10
    assert player.stat_effects["Attack"].duration == 3
    assert player.stat_effects["Defense"].duration == 3
    assert player.physical_effects["Prone"].active is True
    assert player.physical_effects["Prone"].duration == 2
    assert "knocked prone" in first_message


def test_reckless_onslaught_purchase_preserves_final_assault():
    player = _player("Berserker")

    for node_id in (
        "berserker.ability.parry",
        "berserker.ability.pain-tolerance",
        "berserker.ability.final-assault",
        "berserker.ability.reckless-onslaught",
    ):
        assert purchase_node(player, node_id).success
    assert "Final Assault" in player.spellbook["Skills"]
    assert "Reckless Onslaught" in player.spellbook["Skills"]

    restored = PlayerDataSerializer.deserialize(
        PlayerDataSerializer.serialize(player),
        skip_tiles=True,
    )
    assert "Final Assault" in restored.spellbook["Skills"]
    assert "Reckless Onslaught" in restored.spellbook["Skills"]


def test_parry_outcome_is_exposed_to_reckless_onslaught(monkeypatch):
    attacker = _player("Berserker")
    defender = _player("Grandmaster of Arms")
    defender.spellbook["Skills"]["Parry"] = abilities.Parry()
    attacker._last_attack_parried = False
    monkeypatch.setattr(
        "src.core.character.offense.random.random",
        lambda: 0.0,
    )
    monkeypatch.setattr(
        defender,
        "weapon_damage",
        lambda *_args, **_kwargs: ("Counterattack.\n", True, 1),
    )

    remaining, message, parried, aborted = attacker._apply_parry(defender, damage=10)

    assert aborted is False
    assert parried is True
    assert remaining < 10
    assert attacker._last_attack_parried is True
    assert "parries" in message


def test_pain_tolerance_reduces_bleed_effects_and_doubles_bandage_healing(
    monkeypatch,
):
    player = _player("Berserker")
    assert ability_mechanics.pain_tolerance_bleed_multiplier(player) == 1.0
    assert ability_mechanics.bandage_healing_multiplier(player) == 1.0
    player.spellbook["Skills"]["Pain Tolerance"] = abilities.PainTolerance()
    assert ability_mechanics.pain_tolerance_bleed_multiplier(player) == 0.50
    assert ability_mechanics.bandage_healing_multiplier(player) == 2.0

    bandage = items.Bandage()
    player.inventory["Bandage"] = [bandage]
    player.health.max = 200
    player.health.current = 100
    bleed = player.physical_effects["Bleed"]
    bleed.active = True
    bleed.duration = 2
    bleed.extra = 10
    monkeypatch.setattr(
        "src.core.items.consumables.random.randint",
        lambda _low, high: high,
    )

    bandage.use(player)

    assert player.health.current == 140
    assert bleed.active is False


def test_hemorrhage_thirst_heals_bleed_and_crashes_after_three_turns():
    player = _player("Berserker")
    enemy = _player("Grandmaster of Arms")
    player.health.current = 100
    player.spellbook["Skills"]["Hemorrhage Thirst"] = abilities.HemorrhageThirst()
    bleed = enemy.physical_effects["Bleed"]
    bleed.active = True
    bleed.duration = 4
    bleed.extra = 20
    enemy.stats.con = 0
    engine = BattleEngine(player, enemy, _CombatTile())
    engine.attacker = enemy
    engine.defender = player

    results = [engine.pre_turn() for _turn in range(3)]

    assert player.health.current == 145
    assert all("restores 15 health" in result.effects_text for result in results)
    assert player.status_effects["Sleep"].active is True
    assert player.status_effects["Sleep"].duration == 2
    assert player.status_effects["Sleep"].source == "Hemorrhage Thirst"
    assert player._hemorrhage_thirst_streak == 0
    assert "unconscious for two turns" in results[-1].effects_text


def test_hemorrhage_thirst_has_no_effect_before_purchase_and_survives_save():
    player = _player("Berserker")
    player.health.current = 100

    assert ability_mechanics.trigger_hemorrhage_thirst(player, 20) == ""
    assert player.health.current == 100
    for node_id in (
        "berserker.ability.frenzy",
        "berserker.ability.hemorrhage-thirst",
    ):
        assert purchase_node(player, node_id).success

    restored = PlayerDataSerializer.deserialize(
        PlayerDataSerializer.serialize(player),
        skip_tiles=True,
    )
    assert "Hemorrhage Thirst" in restored.spellbook["Skills"]
    ability_mechanics.trigger_hemorrhage_thirst(restored, 20)
    assert restored.health.current == 120
    ability_mechanics.trigger_hemorrhage_thirst(restored, 0)
    assert restored._hemorrhage_thirst_streak == 0
    ability_mechanics.trigger_hemorrhage_thirst(restored, 10)
    ability_mechanics.trigger_hemorrhage_thirst(restored, 10)
    assert restored._hemorrhage_thirst_streak == 2
    assert restored.status_effects["Sleep"].active is False


def test_boomerang_toss_turns_devastating_throw_into_returning_multi_hit(
    monkeypatch,
):
    player = _player("Berserker")
    target = _player("Grandmaster of Arms")
    player.equipment["Weapon"] = items.Bastard()
    player.spellbook["Skills"]["Boomerang Toss"] = abilities.BoomerangToss()
    calls = []

    def attack(defender, **kwargs):
        calls.append(kwargs)
        defender.health.current -= 10
        return "Boomerang hit.\n", True, 1

    monkeypatch.setattr(player, "weapon_damage", attack)
    result = abilities.DevastatingThrow().use(player, target)

    assert len(calls) == 3
    assert result.damage == 30
    assert player.physical_effects["Disarm"].active is False
    assert "returns to hand" in result.message


def test_grandmaster_mastery_talents_scale_with_equipped_discipline():
    player = _player("Grandmaster of Arms")
    player.equipment["Weapon"] = items.Bastard()
    grandmaster.add_discipline_xp(
        player,
        "Longsword",
        grandmaster.XP_THRESHOLDS[-1],
    )

    assert grandmaster.perfect_form_accuracy_bonus(player, "Longsword") == 0.0
    assert grandmaster.perfect_form_damage_multiplier(player, "Longsword") == 1.0
    assert grandmaster.adaptive_arsenal_parry_bonus(player) == 0.0
    assert grandmaster.adaptive_arsenal_counter_crit_chance(player) == 0.0

    assert purchase_node(
        player,
        "grandmaster-of-arms.ability.double-strike",
    ).success
    assert purchase_node(
        player,
        "grandmaster-of-arms.ability.dual-wield-excellence",
    ).success
    assert purchase_node(
        player,
        "grandmaster-of-arms.ability.weapon-swap",
    ).success
    assert purchase_node(
        player,
        "grandmaster-of-arms.talent.perfect-form",
    ).success
    assert purchase_node(
        player,
        "grandmaster-of-arms.talent.adaptive-arsenal",
    ).success

    assert grandmaster.perfect_form_accuracy_bonus(
        player,
        "Longsword",
    ) == pytest.approx(0.05)
    assert grandmaster.perfect_form_damage_multiplier(
        player,
        "Longsword",
    ) == pytest.approx(1.10)
    assert grandmaster.adaptive_arsenal_parry_bonus(player) == pytest.approx(
        0.05,
    )
    assert grandmaster.adaptive_arsenal_counter_crit_chance(
        player,
    ) == pytest.approx(0.10)

    restored = PlayerDataSerializer.deserialize(
        PlayerDataSerializer.serialize(player),
        skip_tiles=True,
    )
    assert grandmaster.perfect_form_damage_multiplier(
        restored,
        "Longsword",
    ) == pytest.approx(1.10)
    assert grandmaster.adaptive_arsenal_parry_bonus(restored) == pytest.approx(
        0.05,
    )


def test_grandmaster_rank_ten_art_replaces_level_two_and_survives_sync():
    player = _player("Grandmaster of Arms")
    grandmaster.add_discipline_xp(
        player,
        "Fist",
        grandmaster.XP_THRESHOLDS[-1],
    )
    for node_id in (
        "grandmaster-of-arms.ability.iron-palm",
        "grandmaster-of-arms.ability.iron-palm-2",
        "grandmaster-of-arms.ability.iron-palm-3",
    ):
        assert purchase_node(player, node_id).success

    assert "Iron Palm" not in player.spellbook["Skills"]
    assert "Iron Palm 2" not in player.spellbook["Skills"]
    assert "Iron Palm 3" in player.spellbook["Skills"]
    grandmaster.sync_weapon_art_skills(player)
    assert "Iron Palm 3" in player.spellbook["Skills"]
