"""Regression coverage for the expanded Warrior tree and enemy fleeing."""

from types import SimpleNamespace

import pytest

from src.core import abilities
from src.core.classes import warrior
from src.core.combat.action_queue import ActionPriority
from src.core.combat.battle_engine import BattleEngine
from src.core.combat.encounter import EnemyResolution
from src.core.enemies import Goblin
from src.core.progression import NodeState, available_nodes, initialize_progression
from tests.test_framework import TestGameState


class _Tile:
    def available_actions(self, _player):
        return ["Attack", "Defend", "Use Skill", "Flee"]

    def __str__(self):
        return "CavePath"


def test_commitment_closes_competing_promotions_and_stacks_on_one_target():
    player = TestGameState.create_player(class_name="Warrior", level=30)
    initialize_progression(player)
    player.spellbook["Skills"]["Commitment"] = abilities.Commitment()
    player.progression.purchased_node_ids.add("warrior.ability.commitment")
    statuses = {status.node.name: status.state for status in available_nodes(player)}

    assert statuses["Promote: Weapon Master"] == NodeState.CLOSED
    assert statuses["Promote: Lancer"] == NodeState.CLOSED
    assert statuses["Promote: Sentinel"] == NodeState.CLOSED
    assert statuses["Promote: Paladin"] != NodeState.CLOSED

    first = Goblin()
    second = Goblin()
    warrior.start_combat(player)
    assert warrior.record_attack(player, first) == 1
    assert warrior.record_attack(player, first) == 2
    assert warrior.commitment_accuracy_bonus(player) == 0.06
    assert warrior.record_attack(player, second) == 1
    warrior.begin_action(player)
    warrior.finish_action(player)
    assert warrior.commitment_accuracy_bonus(player) == 0.0


def test_improved_defend_and_upsurge_apply_their_defensive_bonuses():
    player = TestGameState.create_player(class_name="Warrior", level=20)
    player.spellbook["Skills"]["Improved Defend"] = abilities.ImprovedDefend()
    player.enter_defensive_stance(reduction=0.30)

    assert player.get_defensive_reduction() == pytest.approx(0.45)

    summon = TestGameState.create_player(name="Ally", class_name="Warrior", level=20)
    player.mana.current = player.mana.max
    result = abilities.Upsurge().use(
        player,
        battle_engine=SimpleNamespace(summon=summon),
    )

    assert player.temporary_health["amount"] == int(player.health.max * 0.15)
    assert summon.temporary_health["amount"] == int(summon.health.max * 0.15)
    assert "Ally gains" in result.message


def test_enemy_flee_is_recorded_without_ending_combat_as_player_flee():
    player = TestGameState.create_player(class_name="Warrior", level=30)
    enemy = Goblin()
    engine = BattleEngine(player, enemy, _Tile())
    engine.attacker = enemy
    engine.defender = player

    result = engine.execute_intent(engine.prepare_intent("Flee"))

    assert result.fled is False
    assert engine.flee is False
    assert engine.encounter.primary_member.resolution == EnemyResolution.ESCAPED
    assert "flees from battle" in result.message


def test_escaped_single_enemy_awards_no_victory_rewards(monkeypatch):
    player = TestGameState.create_player(class_name="Warrior", level=30)
    enemy = Goblin()
    tile = _Tile()
    tile.enemy = enemy
    engine = BattleEngine(player, enemy, tile)
    engine.attacker = enemy
    engine.defender = player
    monkeypatch.setattr(
        "src.core.classes.footpad.aggressive_pursuit",
        lambda _player, _enemy: (True, "Goblin flees from battle.\n"),
    )
    starting_experience = player.level.exp
    starting_gold = player.gold

    engine.execute_intent(engine.prepare_intent("Flee"))
    outcome = engine.end_battle()

    assert outcome.result == "victory"
    assert outcome.enemy_escaped is True
    assert "escaped the encounter" in outcome.message
    assert player.level.exp == starting_experience
    assert player.gold == starting_gold
    assert player.gameplay_stats["enemies_defeated"] == 0
    assert tile.enemy is None


def test_priority_enemy_ai_can_choose_flee_when_player_outclasses_it(monkeypatch):
    player = TestGameState.create_player(
        class_name="Grandmaster of Arms",
        level=30,
    )
    enemy = Goblin()
    enemy.action_stack = [{"ability": "Attack", "priority": ActionPriority.NORMAL}]
    monkeypatch.setattr("src.core.enemies.base.random.randint", lambda *_args: 1)
    monkeypatch.setattr(
        "src.core.enemies.base.random.choice",
        lambda choices: next(choice for choice in choices if choice[0] == "Flee"),
    )

    action, ability = enemy.options(player, [], _Tile())

    assert (action, ability) == ("Flee", None)


def test_enemy_smoke_screen_bypasses_aggressive_pursuit(monkeypatch):
    player = TestGameState.create_player(class_name="Warrior", level=30)
    player.spellbook["Skills"]["Aggressive Pursuit"] = abilities.AggressivePursuit()
    player.sight = False
    enemy = Goblin()
    enemy.spellbook["Skills"]["Smoke Screen"] = abilities.SmokeScreen()
    enemy.mana.current = enemy.mana.max
    engine = BattleEngine(player, enemy, _Tile())
    engine.attacker = enemy
    engine.defender = player
    monkeypatch.setattr(
        player,
        "weapon_damage",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(
            AssertionError("Aggressive Pursuit must not trigger for Smoke Screen")
        ),
    )

    result = engine.execute_intent(engine.prepare_intent("Use Skill", "Smoke Screen"))

    assert result.fled is False
    assert engine.encounter.primary_member.resolution == EnemyResolution.ESCAPED
    assert "cloud of smoke" in result.message
