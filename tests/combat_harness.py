"""
BattleEngine test harness.

Provides a deterministic, lightweight driver for exercising core combat
flow without UI dependencies. Intended for unit/integration tests.
"""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from typing import Callable, Deque, Iterable, Literal

from src.core.combat.battle_engine import ActionResult, BattleEngine, PostTurnResult, PreTurnResult
from src.core.events.event_bus import (
    EventBus,
    EventType,
    create_combat_event,
    get_event_bus,
    reset_event_bus,
)


@dataclass
class TurnOutcome:
    """Snapshot of a single BattleEngine turn."""

    attacker: str
    defender: str
    action: str
    choice: str | None
    pre: PreTurnResult
    result: ActionResult
    companion_message: str
    post: PostTurnResult


class MockTile:
    """Minimal tile stub for BattleEngine tests."""

    def __init__(self, enemy=None, actions: Iterable[str] | None = None, boss: bool = False):
        self.enemy = enemy
        self.defeated = False
        self._actions = (
            list(actions) if actions else ["Attack", "Cast Spell", "Use Skill", "Use Item", "Flee"]
        )
        self._boss = boss

    def available_actions(self, _player):
        return list(self._actions)

    def __str__(self) -> str:
        return "BossTile" if self._boss else "TestTile"


class NullBattleLogger:
    """
    No-op logger for tests.

    BattleEngine logs on every action; using a null logger avoids test
    brittleness due to metadata assumptions (enemy_typ, mana.max, etc.).
    """

    def start_battle(self, *args, **kwargs) -> None:
        return None

    def log_event(self, *args, **kwargs) -> None:
        return None

    def next_turn(self) -> None:
        return None

    def end_battle(self, *args, **kwargs) -> None:
        return None


class BattleEngineHarness:
    """
    Deterministic driver for BattleEngine turns.

    Usage:
        harness = BattleEngineHarness(player, enemy, player_actions=[("Attack", None)])
        harness.start()
        outcome = harness.run_turn()
    """

    def __init__(
        self,
        player,
        enemy,
        tile: MockTile | None = None,
        player_actions: Iterable[tuple[str, str | None]] | None = None,
        enemy_actions: Iterable[tuple[str, str | None]] | None = None,
        *,
        force_initiative: Literal["player", "enemy"] | None = "player",
        rng_seed: int | None = None,
        isolate_events: bool = True,
        collect_events: bool = False,
        logger=None,
        player_policy: Callable[[BattleEngine], tuple[str, str | None]] | None = None,
        enemy_policy: Callable[[BattleEngine], tuple[str, str | None]] | None = None,
        assert_invariants: bool = False,
    ):
        self.player_actions: Deque[tuple[str, str | None]] = deque(player_actions or [])
        self.enemy_actions: Deque[tuple[str, str | None]] = deque(enemy_actions or [])

        self._force_initiative = force_initiative
        self._assert_invariants = assert_invariants
        self._player_policy = player_policy
        self._enemy_policy = enemy_policy

        if rng_seed is not None:
            import random

            random.seed(rng_seed)

        if isolate_events:
            reset_event_bus()

        self.event_bus: EventBus = get_event_bus()
        self.collected_events = []
        self._event_collector = None
        if collect_events:

            def _collect(event) -> None:
                self.collected_events.append(event)

            self._event_collector = _collect
            for event_type in EventType:
                self.event_bus.subscribe(event_type, _collect)

        self.tile = tile or MockTile(enemy=enemy)
        self.engine = BattleEngine(
            player=player,
            enemy=enemy,
            tile=self.tile,
            logger=logger if logger is not None else NullBattleLogger(),
        )

        self._wrap_enemy_options(enemy)

    def _wrap_enemy_options(self, enemy) -> None:
        if not hasattr(enemy, "options"):
            return

        def _options(_player, _actions, _tile):
            if self._enemy_policy is not None:
                return self._enemy_policy(self.engine)
            if self.enemy_actions:
                return self.enemy_actions.popleft()
            return "Attack", None

        enemy.options = _options

    def start(self):
        if self._force_initiative is None:
            return self.engine.start_battle()

        enemy = self.engine.encounter.primary_enemy
        if self._force_initiative == "player":
            first, second = self.engine.player, enemy
        else:
            first, second = enemy, self.engine.player

        self.engine.attacker, self.engine.defender = first, second

        # Mirror BattleEngine.start_battle side-effects without relying on RNG.
        self.engine._event_bus.emit(
            create_combat_event(
                EventType.COMBAT_START,
                actor=self.engine.player,
                target=enemy,
                initiative=self.engine.attacker == self.engine.player,
                boss=self.engine.boss,
            )
        )
        try:
            self.engine.logger.start_battle(
                self.engine.player,
                enemy,
                initiative=self.engine.attacker == self.engine.player,
                boss=self.engine.boss,
            )
        except Exception:
            pass

        return self.engine.attacker, self.engine.defender

    def clear_events(self) -> None:
        self.event_bus.clear_history()
        self.collected_events.clear()

    def stop_collecting_events(self) -> None:
        """Unsubscribe the harness event collector (only when collect_events=True)."""
        if self._event_collector is None:
            return
        for event_type in EventType:
            self.event_bus.unsubscribe(event_type, self._event_collector)
        self._event_collector = None

    def _next_player_action(self) -> tuple[str, str | None]:
        if self._player_policy is not None:
            return self._player_policy(self.engine)
        if self.player_actions:
            return self.player_actions.popleft()
        return "Attack", None

    def _check_invariants(self) -> None:
        if not self._assert_invariants:
            return

        for ch in [
            self.engine.player,
            *[member.enemy for member in self.engine.encounter.members],
            self.engine.summon,
        ]:
            if ch is None:
                continue
            if ch.health.max < 0 or ch.mana.max < 0:
                raise AssertionError("Negative resource max detected.")
            if not (0 <= ch.health.current <= ch.health.max):
                raise AssertionError("Health out of bounds.")
            if not (0 <= ch.mana.current <= ch.mana.max):
                raise AssertionError("Mana out of bounds.")

    def run_turn(self) -> TurnOutcome:
        acting_name = getattr(self.engine.attacker, "name", "")
        defending_name = getattr(self.engine.defender, "name", "")
        pre = self.engine.pre_turn()

        if not pre.can_act:
            # Still advance the turn even if attacker is incapacitated.
            result = ActionResult(message=pre.inactive_reason or pre.effects_text)
            companion_message = self.engine.companion_turn()
            post = self.engine.post_turn()
            self.engine.swap_turns()
            self._check_invariants()
            return TurnOutcome(
                attacker=acting_name,
                defender=defending_name,
                action="Nothing",
                choice=None,
                pre=pre,
                result=result,
                companion_message=companion_message,
                post=post,
            )

        forced = self.engine.get_forced_action()
        if forced:
            if forced.cancelled:
                action, choice = "Cancelled", None
                intent = self.engine.prepare_intent(action, choice)
            else:
                assert forced.intent is not None
                intent = forced.intent
                action, choice = intent.engine_action, intent.choice
        elif self.engine.is_player_turn():
            action, choice = self._next_player_action()
            intent = self.engine.prepare_intent(action, choice)
        else:
            action, choice = self.engine.get_enemy_action()
            intent = self.engine.prepare_intent(action, choice)

        result = self.engine.execute_intent(intent)
        companion_message = self.engine.companion_turn()
        post = self.engine.post_turn()
        self.engine.swap_turns()
        self._check_invariants()
        return TurnOutcome(
            attacker=acting_name,
            defender=defending_name,
            action=action,
            choice=choice,
            pre=pre,
            result=result,
            companion_message=companion_message,
            post=post,
        )

    def run_turns(self, count: int) -> list[TurnOutcome]:
        outcomes = []
        for _ in range(count):
            outcomes.append(self.run_turn())
            if not self.engine.battle_continues():
                break
        return outcomes

    def run_battle(self, max_turns: int = 50) -> list[TurnOutcome]:
        outcomes = []
        turns = 0
        while self.engine.battle_continues() and turns < max_turns:
            outcomes.append(self.run_turn())
            turns += 1
        return outcomes

    def end_battle(self):
        return self.engine.end_battle()
