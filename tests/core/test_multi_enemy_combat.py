"""Focused contracts for headless two-enemy combat."""

from __future__ import annotations

import pytest

from src.core import abilities, items
from src.core.classes import ability_mechanics
from src.core.combat import CombatEncounter, EnemyResolution, TargetLossPolicy, TargetScope
from src.core.combat.battle_engine import (
    ActionIntent,
    ActionValidationCode,
    BattleEngine,
)
from src.core.combat.visibility import conceal, is_concealed, is_revealed_to
from src.core.events.event_bus import EventType, get_event_bus, reset_event_bus
from tests.test_framework import TestGameState


class _FirstRng:
    def choices(self, population, weights, k):
        del weights, k
        return [population[0]]

    def random(self):
        return 0.0


class _Tile:
    def __init__(self):
        self.enemy = "authored"
        self.defeated = False

    def available_actions(self, _player):
        return ["Attack", "Cast Spell", "Defend", "Flee"]

    def __str__(self):
        return "Pair Test Tile"


def _character(name: str, *, hp: int = 50, mana: int = 50):
    character = TestGameState.create_player(
        name=name,
        class_name="Warrior",
        race_name="Human",
        level=10,
        health=(hp, hp),
        mana=(mana, mana),
    )
    character.enemy_typ = "TestEnemy"
    character.experience = 100
    return character


def _engine():
    player = _character("Hero", hp=100, mana=100)
    enemies = [_character("Goblin"), _character("Goblin")]
    encounter = CombatEncounter.from_enemies(
        enemies,
        encounter_id="pair",
        combatant_ids=("enemy-a", "enemy-b"),
    )
    tile = _Tile()
    engine = BattleEngine(
        player,
        tile=tile,
        encounter=encounter,
        rng=_FirstRng(),
    )
    return engine, player, enemies, tile


def test_pair_cycle_is_fixed_and_emits_round_and_turn_identity():
    reset_event_bus()
    engine, player, enemies, _tile = _engine()

    first, defender = engine.start_battle()

    assert first is player
    assert defender is enemies[0]
    assert engine.fixed_turn_order == ("player", "enemy-a", "enemy-b")
    assert engine.current_actor_id == "player"
    assert engine.round_number == 1
    assert engine.total_started_actor_turns == 1
    start = get_event_bus().get_history(EventType.TURN_START)[-1]
    assert start.data["encounter_id"] == "pair"
    assert start.data["actor_id"] == "player"
    assert start.data["round"] == 1
    assert start.data["actor_turn_id"] == 1

    engine.post_turn()
    engine.swap_turns()
    assert engine.current_actor_id == "enemy-a"
    engine.post_turn()
    engine.swap_turns()
    assert engine.current_actor_id == "enemy-b"
    engine.post_turn()
    engine.swap_turns()
    assert engine.current_actor_id == "player"
    assert engine.round_number == 2
    assert engine.total_started_actor_turns == 4
    assert len(get_event_bus().get_history(EventType.ROUND_END)) == 1


def test_timeline_entries_preview_six_opportunities_without_advancing_combat():
    engine, _player, _enemies, _tile = _engine()
    engine.start_battle()
    actor_id = engine.current_actor_id
    ready_at = engine.current_readiness

    entries = engine.timeline_entries()

    assert len(entries) == 6
    assert entries[0].actor_id == actor_id
    assert entries[0].ready_at == ready_at
    assert [entry.ready_at for entry in entries] == sorted(entry.ready_at for entry in entries)
    assert engine.current_actor_id == actor_id
    assert engine.current_readiness == ready_at


def test_invalid_intents_do_not_commit_or_change_focus():
    engine, _player, enemies, _tile = _engine()
    engine.start_battle()
    hp_before = [enemy.health.current for enemy in enemies]

    missing = engine.execute_intent(ActionIntent("Attack"))
    unknown = engine.execute_intent(ActionIntent("Attack", target_ids=("not-in-this-fight",)))
    wrong_scope = engine.execute_intent(ActionIntent("Defend", target_ids=("enemy-a",)))

    assert missing.committed is False
    assert missing.validation_code == ActionValidationCode.MISSING_TARGET
    assert unknown.validation_code == ActionValidationCode.UNKNOWN_TARGET
    assert wrong_scope.validation_code == ActionValidationCode.WRONG_TARGET_SCOPE
    assert [enemy.health.current for enemy in enemies] == hp_before
    assert engine.focus_target_id == "enemy-a"
    actor_id = engine.current_actor_id
    turns = engine.logger.turn_counter
    engine.post_turn()
    engine.swap_turns()
    assert engine.current_actor_id == actor_id
    assert engine.logger.turn_counter == turns


def test_concealed_enemy_rejects_direct_player_intent_but_not_area_targeting():
    engine, _player, enemies, _tile = _engine()
    engine.start_battle()
    conceal(enemies[1])

    result = engine.execute_intent(ActionIntent("Attack", target_ids=("enemy-b",)))

    assert result.committed is False
    assert result.validation_code is ActionValidationCode.CONCEALED_TARGET


def test_hostile_action_breaks_player_concealment_on_commit(monkeypatch):
    engine, player, enemies, _tile = _engine()
    engine.start_battle()
    conceal(player)
    monkeypatch.setattr(
        player,
        "weapon_damage",
        lambda target, **_kwargs: ("Hit.\n", True, 0),
    )

    result = engine.execute_intent(ActionIntent("Attack", target_ids=("enemy-a",)))

    assert result.committed is True
    assert is_concealed(player) is False


def test_enemy_automatically_detects_a_concealed_player_before_acting():
    engine, player, _enemies, _tile = _engine()
    engine.start_battle()
    conceal(player)
    engine.post_turn()
    engine.swap_turns()

    invalid = engine.execute_intent(ActionIntent("Attack"))
    pre_turn = engine.pre_turn()
    engine.attacker.options = lambda _target, _actions, _tile: ("Attack", None)
    action, choice = engine.get_enemy_action()

    assert invalid.committed is False
    assert invalid.validation_code is ActionValidationCode.CONCEALED_TARGET
    assert "detects 1 concealed opponent" in pre_turn.effects_text
    assert (action, choice) != ("Detect", None)
    assert is_revealed_to(engine.attacker, player) is True


def test_enemy_area_action_records_the_player_side_as_its_structured_target():
    reset_event_bus()
    engine, player, enemies, _tile = _engine()
    enemies[0].spellbook["Spells"]["Earthquake"] = abilities.Earthquake()
    engine.start_battle()
    engine.post_turn()
    engine.swap_turns()

    result = engine.execute_intent(ActionIntent("Cast Spell", "Earthquake"))

    assert result.committed is True
    assert result.combat_results.target_scope is TargetScope.ALL_ENEMIES
    assert result.combat_results.target_ids == ("player",)
    assert result.combat_results.results[0].target is player
    assert result.combat_results.results[0].target_id == "player"
    event = get_event_bus().get_history(EventType.ACTION_RESULT)[-1]
    assert event.data["target_id"] == "player"
    assert event.data["target_scope"] == TargetScope.ALL_ENEMIES.value


def test_pending_retarget_action_uses_a_visible_focus_after_target_loss():
    engine, player, enemies, _tile = _engine()
    engine.start_battle()
    calls = []

    class _RetargetingCharge:
        name = "Retargeting Charge"
        cost = 0
        passive = False
        target_scope = TargetScope.SINGLE_ENEMY
        target_loss_policy = TargetLossPolicy.RETARGET_FOCUS

        @staticmethod
        def use(_user, target=None):
            calls.append(target)
            return "Retargeted hit.\n"

    charge = _RetargetingCharge()
    player.spellbook["Skills"][charge.name] = charge
    conceal(enemies[0])
    engine.pending_actions["player"] = {
        "action": "Use Skill",
        "choice": charge.name,
        "ability": charge,
        "target_id": "enemy-a",
        "policy": TargetLossPolicy.RETARGET_FOCUS,
    }

    result = engine.execute_intent(engine.prepare_intent("Use Skill", charge.name))

    assert result.committed is True
    assert calls == [enemies[1]]
    assert engine.focus_target_id == "enemy-b"


def test_focus_controls_cycle_living_members_without_consuming_turn():
    engine, _player, enemies, _tile = _engine()
    engine.start_battle()
    actor_id = engine.current_actor_id
    actor_turns = engine.total_started_actor_turns

    assert engine.cycle_focus(1) == "enemy-b"
    assert engine.defender is enemies[1]
    assert engine.cycle_focus(-1) == "enemy-a"
    enemies[0].health.current = 0
    engine._record_final_enemy_resolutions()

    assert engine.cycle_focus(1) == "enemy-b"
    assert engine.current_actor_id == actor_id
    assert engine.total_started_actor_turns == actor_turns
    with pytest.raises(ValueError, match="not a living target"):
        engine.set_focus_target("enemy-a")
    with pytest.raises(KeyError):
        engine.set_focus_target("foreign")


def test_explicit_target_updates_focus_without_enemy_compatibility_bridge(monkeypatch):
    engine, player, enemies, _tile = _engine()
    engine.start_battle()
    seen = []

    def weapon_damage(target, **_kwargs):
        seen.append(target)
        target.health.current -= 7
        return "Hit.\n", True, 7

    monkeypatch.setattr(player, "weapon_damage", weapon_damage)
    result = engine.execute_intent(ActionIntent("Attack", target_ids=("enemy-b",)))

    assert result.committed is True
    assert result.combat_results.target_scope == TargetScope.SINGLE_ENEMY
    assert result.combat_results.target_ids == ("enemy-b",)
    assert result.combat_results.results[0].target_id == "enemy-b"
    assert enemies[1].health.current == 43
    assert engine.focus_target_id == "enemy-b"
    assert seen == [enemies[1]]
    assert not hasattr(engine, "enemy")


def test_lethal_single_target_intent_records_resolution_before_return(monkeypatch):
    engine, player, enemies, _tile = _engine()
    engine.start_battle()

    def lethal_weapon_damage(target, **_kwargs):
        damage = target.health.current
        target.health.current = 0
        return "Lethal hit.\n", True, damage

    monkeypatch.setattr(player, "weapon_damage", lethal_weapon_damage)

    result = engine.execute_intent(ActionIntent("Attack", target_ids=("enemy-a",)))

    assert result.new_resolutions == (engine.encounter.resolution_ledger[0],)
    assert result.new_resolutions[0].combatant_id == "enemy-a"
    assert result.new_resolutions[0].resolution == EnemyResolution.DEFEATED
    assert engine.encounter.member_by_id("enemy-a").resolution == (EnemyResolution.DEFEATED)
    assert engine.focus_target_id == "enemy-b"
    assert enemies[0].health.current == 0


def test_single_target_resurrection_precedes_terminal_resolution(monkeypatch):
    engine, player, enemies, _tile = _engine()
    engine.start_battle()

    def resurrect(caster):
        caster.health.current = 1
        return f"{caster.name} rises again.\n"

    enemies[0].spellbook["Spells"]["Resurrection"] = type(
        "_Resurrection",
        (),
        {"cast": staticmethod(resurrect)},
    )()

    def lethal_weapon_damage(target, **_kwargs):
        damage = target.health.current
        target.health.current = 0
        return "Lethal hit.\n", True, damage

    monkeypatch.setattr(player, "weapon_damage", lethal_weapon_damage)

    result = engine.execute_intent(ActionIntent("Attack", target_ids=("enemy-a",)))

    assert "Goblin rises again" in result.message
    assert result.new_resolutions == ()
    assert engine.encounter.resolution_ledger == ()
    assert enemies[0].health.current == 1


def test_dead_enemy_is_skipped_without_changing_fixed_order():
    engine, _player, enemies, _tile = _engine()
    engine.start_battle()
    enemies[0].health.current = 0
    engine._record_final_enemy_resolutions()

    engine.post_turn()
    engine.swap_turns()

    assert engine.fixed_turn_order == ("player", "enemy-a", "enemy-b")
    assert engine.current_actor_id == "enemy-b"


def test_earthquake_resolves_each_enemy_for_one_mana_cost():
    engine, player, enemies, _tile = _engine()
    player.spellbook["Spells"]["Earthquake"] = abilities.Earthquake()
    for enemy in enemies:
        enemy.status_effects["Sleep"].active = True
    engine.start_battle()

    result = engine.execute_intent(ActionIntent("Cast Spell", "Earthquake"))

    assert player.mana.current == 74
    assert result.combat_results.target_scope == TargetScope.ALL_ENEMIES
    assert [portion.target_id for portion in result.combat_results.results] == [
        "enemy-a",
        "enemy-b",
    ]
    assert all(portion.damage > 0 for portion in result.combat_results.results)
    assert all(enemy.health.current < enemy.health.max for enemy in enemies)


def test_area_outcomes_redact_concealed_enemy_identity_but_keep_the_lane():
    reset_event_bus()
    engine, player, enemies, _tile = _engine()
    player.spellbook["Spells"]["Earthquake"] = abilities.Earthquake()
    conceal(enemies[1])
    engine.start_battle()

    result = engine.execute_intent(ActionIntent("Cast Spell", "Earthquake"))
    concealed_portion = result.combat_results.results[1]

    assert concealed_portion.target is None
    assert concealed_portion.target_id == "enemy-b"
    assert concealed_portion.extra["identity_redacted"] is True
    assert concealed_portion.extra["target_label"] == "a concealed opponent"
    assert enemies[1].name not in result.message
    serialized = result.combat_results.summary_dict()
    assert serialized["target_ids"] == ["enemy-a", "enemy-b"]
    assert serialized["results"][1]["target"] is None
    event = get_event_bus().get_history(EventType.ACTION_RESULT)[1]
    assert event.target is None
    assert event.result is concealed_portion


def test_sight_preserves_concealed_area_target_identity():
    engine, player, enemies, _tile = _engine()
    player.spellbook["Spells"]["Earthquake"] = abilities.Earthquake()
    player.sight = True
    conceal(enemies[1])
    engine.start_battle()

    result = engine.execute_intent(ActionIntent("Cast Spell", "Earthquake"))
    concealed_portion = result.combat_results.results[1]

    assert concealed_portion.target is enemies[1]
    assert "identity_redacted" not in concealed_portion.extra


def test_shield_ricochet_resolves_as_an_all_enemy_skill(monkeypatch):
    engine, player, enemies, _tile = _engine()
    player.cls.name = "Crusader"
    player.equipment["OffHand"] = items.KiteShield()
    player.spellbook["Skills"]["Shield Ricochet"] = abilities.ShieldRicochet()
    for enemy in enemies:
        monkeypatch.setattr(
            enemy,
            "handle_defenses",
            lambda _attacker, damage, _cover=False, typ="Physical": (
                True,
                "",
                damage,
            ),
        )
        monkeypatch.setattr(
            enemy,
            "damage_reduction",
            lambda damage, _attacker, typ="Physical": (True, "", damage),
        )
    engine.start_battle()

    result = engine.execute_intent(ActionIntent("Use Skill", "Shield Ricochet"))

    assert player.mana.current == 84
    assert result.combat_results.target_scope == TargetScope.ALL_ENEMIES
    assert [portion.target_id for portion in result.combat_results.results] == [
        "enemy-a",
        "enemy-b",
    ]
    assert all(portion.damage > 0 for portion in result.combat_results.results)


def test_earthquake_includes_flying_enemy_as_explicit_no_effect():
    engine, player, enemies, _tile = _engine()
    player.spellbook["Spells"]["Earthquake"] = abilities.Earthquake()
    enemies[1].flying = True
    engine.start_battle()

    result = engine.execute_intent(ActionIntent("Cast Spell", "Earthquake"))
    flying = result.combat_results.results[1]

    assert flying.target_id == "enemy-b"
    assert flying.hit is False
    assert flying.extra["no_effect_reason"] == "flying"
    assert enemies[1].health.current == enemies[1].health.max
    assert not enemies[1].physical_effects["Prone"].active


def test_hallowed_ground_has_enemy_portions_and_tagged_self_portion():
    engine, player, enemies, _tile = _engine()
    player.spellbook["Spells"]["Hallowed Ground"] = abilities.HallowedGround()
    engine.start_battle()

    result = engine.execute_intent(ActionIntent("Cast Spell", "Hallowed Ground"))

    portions = result.combat_results.results
    assert [portion.target_id for portion in portions] == [
        "enemy-a",
        "enemy-b",
        "player",
    ]
    assert portions[-1].extra["self_result"] is True
    assert all(enemy.magic_effects["Hallowed Ground"].active for enemy in enemies)
    assert player.magic_effects["Hallowed Ground"].active


def test_locked_charge_fizzles_without_refund_when_target_is_gone():
    engine, player, enemies, _tile = _engine()
    player.spellbook["Skills"]["Charge"] = abilities.Charge()
    engine.start_battle()

    started = engine.execute_intent(ActionIntent("Use Skill", "Charge", ("enemy-a",)))
    mana_after_commit = player.mana.current
    enemies[0].health.current = 0
    engine._record_final_enemy_resolutions()
    engine.post_turn()
    engine.swap_turns()
    while engine.attacker is not player:
        engine.swap_turns()
    released = engine.execute_intent(engine.prepare_intent("Use Skill", "Charge"))

    assert "building momentum" in started.message
    assert "fizzles" in released.message
    assert player.mana.current == mana_after_commit
    assert "player" not in engine.pending_actions


def test_rewind_restores_roster_ledger_cycle_focus_and_pending_actions():
    engine, player, enemies, _tile = _engine()
    player.spellbook["Skills"]["Charge"] = abilities.Charge()
    engine.start_battle()
    engine.execute_intent(ActionIntent("Use Skill", "Charge", ("enemy-b",)))
    snapshot = ability_mechanics.capture_battle_snapshot(engine)

    enemies[0].health.current = 0
    engine._record_final_enemy_resolutions()
    engine._focus_target_id = "enemy-a"
    engine.swap_turns()
    ability_mechanics.restore_battle_snapshot(engine, snapshot)

    assert enemies[0].is_alive()
    assert engine.encounter.resolution_ledger == ()
    assert engine.current_actor_id == "player"
    assert engine.focus_target_id == "enemy-b"
    assert engine.pending_actions["player"]["target_id"] == "enemy-b"


def test_multi_victory_settles_rewards_once_without_mutating_tile():
    engine, player, enemies, tile = _engine()
    engine.start_battle()
    for enemy in enemies:
        enemy.health.current = 0
    engine._record_final_enemy_resolutions()
    experience_before = player.level.exp

    outcome = engine.end_battle()

    assert outcome.result == "victory"
    assert outcome.rewards_settled is True
    assert outcome.total_experience == 220
    assert len(outcome.member_settlements) == 2
    assert player.level.exp > experience_before
    assert tile.enemy == "authored"
    assert tile.defeated is False
    exp_after = player.level.exp

    repeated = engine.end_battle()

    assert repeated is outcome
    assert player.level.exp == exp_after


def test_multi_flee_discards_partial_resolution_ledger():
    engine, _player, enemies, tile = _engine()
    engine.start_battle()
    enemies[0].health.current = 0
    engine._record_final_enemy_resolutions()
    engine.flee = True

    outcome = engine.end_battle()

    assert outcome.result == "flee"
    assert outcome.rewards_settled is True
    assert outcome.member_settlements == ()
    assert engine.encounter.resolution_ledger == ()
    assert all(member.resolution is None for member in engine.encounter.members)
    assert all(enemy.health.current == enemy.health.max for enemy in enemies)
    assert tile.enemy == "authored"


def test_mixed_mercy_and_ejection_settle_only_approved_rewards():
    engine, player, enemies, _tile = _engine()
    engine.start_battle()
    for enemy in enemies:
        enemy.health.current = 0
        enemy.gold = 40
        enemy.inventory = {}
    engine.encounter.resolve_enemy(
        "enemy-a",
        EnemyResolution.MERCY,
        cause="test_mercy",
    )
    engine.encounter.resolve_enemy(
        "enemy-b",
        EnemyResolution.EJECTED,
        cause="test_ejection",
    )

    outcome = engine.end_battle()

    mercy, ejection = outcome.member_settlements
    assert mercy.resolution == EnemyResolution.MERCY
    assert mercy.experience == 110
    assert mercy.gold == 40
    assert mercy.kill_credit is False
    assert ejection.resolution == EnemyResolution.EJECTED
    assert ejection.experience == 55
    assert ejection.gold == 0
    assert ejection.loot_eligible is False
    assert outcome.total_experience == 165
    assert outcome.total_gold == 40
    assert outcome.resolution_counts == (
        (EnemyResolution.MERCY, 1),
        (EnemyResolution.EJECTED, 1),
    )
    assert player.kill_dict.get("TestEnemy", {}) == {}


def test_post_turn_reports_each_new_resolution_once():
    engine, _player, enemies, _tile = _engine()
    engine.start_battle()
    enemies[0].health.current = 0

    first = engine.post_turn()
    second = engine.post_turn()

    assert [(record.combatant_id, record.resolution) for record in first.new_resolutions] == [
        ("enemy-a", EnemyResolution.DEFEATED)
    ]
    assert second.new_resolutions == ()


def test_multi_settlement_aggregates_normal_and_special_loot():
    engine, player, enemies, _tile = _engine()
    engine.start_battle()

    def award_test_loot(enemy, _tile):
        player.gold += enemy.gold
        player.modify_inventory(items.HealthPotion())
        player.modify_inventory(items.JesterToken(), rare=True)
        return f"{enemy.name} dropped test loot.\n"

    player.loot = award_test_loot
    for enemy in enemies:
        enemy.health.current = 0
        enemy.gold = 7
        enemy.inventory = {}
    engine._record_final_enemy_resolutions()

    outcome = engine.end_battle()

    assert outcome.total_gold == 14
    assert {
        (award.item_name, award.quantity, award.destination) for award in outcome.loot_awards
    } == {
        ("Health Potion", 2, "normal"),
        ("Jester Token", 2, "special"),
    }
    assert all(len(settlement.loot_awards) == 2 for settlement in outcome.member_settlements)
