"""Regression coverage for virtual-readiness battle-log records."""

from __future__ import annotations

from src.core.combat.battle_engine import BattleEngine
from src.core.enemies import Goblin
from tests.test_framework import TestGameState


class _CombatTile:
    def available_actions(self, _player):
        return ["Defend"]


def test_battle_log_records_the_current_virtual_opportunity():
    player = TestGameState.create_player(name="Hero", class_name="Warrior", race_name="Human")
    enemy = Goblin()
    engine = BattleEngine(player, enemy, _CombatTile())

    engine.start_battle()
    ready_at = engine.current_readiness
    result = engine.execute_intent(engine.prepare_intent("Defend"))

    event = engine.logger.events[-1]
    assert result.committed is True
    assert engine.logger.metadata["timeline"] == {
        "scheduler": "virtual_readiness",
        "ready_at": ready_at,
        "round": engine.round_number,
        "actor_turn_id": engine.total_started_actor_turns,
    }
    assert event["opportunity_actor_id"] == engine.current_actor_id
    assert event["ready_at"] == ready_at
    assert event["round"] == engine.round_number
    assert event["actor_turn_id"] == engine.total_started_actor_turns
