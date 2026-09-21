"""Virtual-readiness encounter actor scheduling."""

from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass, field
from statistics import median
from typing import TYPE_CHECKING, Any, Callable

from src.core.randomness import gameplay_random as random

if TYPE_CHECKING:
    from ..character import Character
    from .encounter import CombatEncounter


PLAYER_ACTOR_ID = "player"
STANDARD_ACTION_COST = 100.0
MIN_TEMPO = 0.75
MAX_TEMPO = 1.5


def initiative_rating(actor: Character, opponent: Character) -> float:
    """Return the retired fixed-order weighting for compatibility callers."""
    from ..classes import pathfinder

    chronology = float(pathfinder.chronology_initiative_bonus(actor))
    return max(
        0.0,
        float(actor.check_mod("speed", enemy=opponent))
        + float(actor.check_mod("luck", enemy=opponent, luck_factor=10))
        + chronology,
    )


def _uniform(rng: Any, lower: float, upper: float) -> float:
    """Draw a deterministic-compatible uniform value from the supplied RNG."""
    if hasattr(rng, "uniform"):
        return float(rng.uniform(lower, upper))
    return lower + (upper - lower) * float(rng.random())


def _effective_speed(actor: Character, opponent: Character) -> float:
    """Return the current effective Speed used by virtual readiness."""
    return max(0.0, float(actor.check_mod("speed", enemy=opponent)))


def _luck_head_start(actor: Character, opponent: Character) -> float:
    """Return the existing Luck contribution, bounded by the approved contract."""
    return min(
        10.0,
        max(0.0, float(actor.check_mod("luck", enemy=opponent, luck_factor=10))),
    )


def _player_has_surprise(player: Character, encounter: CombatEncounter) -> bool:
    """Return whether the existing surprise condition grants time-zero readiness."""
    living = encounter.living_members
    return bool(
        living
        and getattr(player, "invisible", False)
        and not any(getattr(member.enemy, "sight", False) for member in living)
    )


def build_actor_order(
    player: Character,
    encounter: CombatEncounter,
    *,
    rng: Any = random,
) -> tuple[str, ...]:
    """Return stable actor IDs for compatibility with legacy callers.

    Scheduling is now owned by :func:`build_readiness_cycle`; this function
    retains the old public import while no longer rolls a fixed turn order.
    """
    del player, rng
    return (PLAYER_ACTOR_ID, *(member.combatant_id for member in encounter.living_members))


def build_readiness_cycle(
    player: Character,
    encounter: CombatEncounter,
    *,
    rng: Any = random,
    force_player_last: bool = False,
) -> "ActorCycle":
    """Build a seeded virtual-readiness schedule for an encounter.

    Initial readiness uses approved jitter and the existing Luck contribution.
    The encounter-start median Speed is retained as the immutable tempo
    baseline; later actions use current effective Speed against that baseline.
    """
    living = encounter.living_members
    order = (PLAYER_ACTOR_ID, *(member.combatant_id for member in living))
    if not living:
        return ActorCycle(order, readiness={PLAYER_ACTOR_ID: 0.0}, median_speed=1.0)

    actors = {PLAYER_ACTOR_ID: player}
    actors.update({member.combatant_id: member.enemy for member in living})
    opponents = {
        PLAYER_ACTOR_ID: living[0].enemy,
        **{member.combatant_id: player for member in living},
    }
    initial = {
        actor_id: _uniform(rng, -10.0, 10.0) - _luck_head_start(actor, opponents[actor_id])
        for actor_id, actor in actors.items()
    }
    surprise = _player_has_surprise(player, encounter) and not force_player_last
    if surprise:
        initial[PLAYER_ACTOR_ID] = min(initial.values()) - 1.0
        if getattr(getattr(player, "cls", None), "name", None) == "Shadowcaster" and getattr(
            player, "power_up", False
        ):
            player.class_effects["Power Up"].active = True
            player.class_effects["Power Up"].duration = 1
    if force_player_last:
        initial[PLAYER_ACTOR_ID] = max(initial.values()) + 1.0

    earliest = min(initial.values())
    readiness = {actor_id: max(0.0, value - earliest) for actor_id, value in initial.items()}
    speeds = [_effective_speed(actor, opponents[actor_id]) for actor_id, actor in actors.items()]
    return ActorCycle(
        order,
        readiness=readiness,
        median_speed=max(1.0, float(median(speeds))),
    )


@dataclass
class ActorCycle:
    """Mutable virtual-time scheduler over stable encounter actor IDs."""

    order: tuple[str, ...]
    cursor: int = 0
    round_number: int = 1
    total_started_actor_turns: int = 0
    readiness: dict[str, float] = field(default_factory=dict)
    median_speed: float = 1.0
    current_time: float = 0.0
    round_pending_actor_ids: set[str] = field(default_factory=set)
    consecutive_actor_id: str | None = None
    consecutive_normal_turns: int = 0
    _immediate_actor_id: str | None = None

    def __post_init__(self) -> None:
        if not self.order:
            raise ValueError("Actor cycle requires at least one actor.")
        self.readiness = {
            actor_id: max(0.0, float(self.readiness.get(actor_id, 0.0))) for actor_id in self.order
        }
        self.median_speed = max(1.0, float(self.median_speed))
        self.cursor = min(
            range(len(self.order)),
            key=lambda index: (self.readiness[self.order[index]], index),
        )
        self.current_time = self.readiness[self.current_actor_id]
        if not self.round_pending_actor_ids:
            self.round_pending_actor_ids = set(self.order)

    @property
    def current_actor_id(self) -> str:
        """Return the actor currently granted the next opportunity."""
        return self.order[self.cursor]

    @property
    def current_ready_at(self) -> float:
        """Return the virtual time of the current actor opportunity."""
        return self.current_time

    def start_current_turn(self) -> int:
        """Record the start of the current actor's normal opportunity."""
        self.total_started_actor_turns += 1
        self.round_pending_actor_ids.discard(self.current_actor_id)
        if self.consecutive_actor_id == self.current_actor_id:
            self.consecutive_normal_turns += 1
        else:
            self.consecutive_actor_id = self.current_actor_id
            self.consecutive_normal_turns = 1
        return self.total_started_actor_turns

    def add_actor(self, actor_id: str) -> None:
        """Schedule a reinforcement immediately, starting its round next cycle."""
        if actor_id in self.order:
            return
        self.order = (*self.order, actor_id)
        self.readiness[actor_id] = self.current_time

    def schedule_immediate(self, actor_id: str) -> None:
        """Grant an approved forced immediate opportunity without adding an actor."""
        if actor_id not in self.order:
            return
        self.readiness[actor_id] = min(self.readiness[actor_id], self.current_time)
        self._immediate_actor_id = actor_id

    def preview(
        self,
        valid_actor_ids: set[str],
        readiness_cost_for_actor: Callable[[str], float],
        limit: int,
    ) -> tuple[tuple[str, float], ...]:
        """Predict normal opportunities without mutating the live scheduler."""
        if limit <= 0:
            return ()
        scheduler = deepcopy(self)
        valid = set(valid_actor_ids).intersection(scheduler.order)
        opportunities: list[tuple[str, float]] = []
        while valid and len(opportunities) < limit:
            actor_id = scheduler.current_actor_id
            opportunities.append((actor_id, scheduler.current_ready_at))
            if len(opportunities) == limit:
                break
            scheduler.advance(
                valid,
                readiness_cost=readiness_cost_for_actor(actor_id),
            )
            scheduler.start_current_turn()
        return tuple(opportunities)

    def advance(
        self,
        valid_actor_ids: set[str],
        *,
        readiness_cost: float = STANDARD_ACTION_COST,
    ) -> tuple[bool, str]:
        """Consume the current opportunity and select the next valid actor."""
        valid = set(valid_actor_ids).intersection(self.order)
        if not valid:
            raise RuntimeError("Actor cycle has no valid actors.")

        current = self.current_actor_id
        self.readiness[current] = self.current_time + max(0.0, float(readiness_cost))
        self.round_pending_actor_ids.intersection_update(valid)
        wrapped = False
        if not self.round_pending_actor_ids:
            self.round_number += 1
            self.round_pending_actor_ids = set(valid)
            wrapped = True

        candidate = self._select_next_actor(valid)
        self.cursor = self.order.index(candidate)
        self.current_time = max(self.current_time, self.readiness[candidate])
        return wrapped, candidate

    def _select_next_actor(self, valid_actor_ids: set[str]) -> str:
        """Choose the earliest ready actor while enforcing the two-turn cap."""
        if self._immediate_actor_id in valid_actor_ids:
            candidate = self._immediate_actor_id
            self._immediate_actor_id = None
            return candidate

        candidates = sorted(
            valid_actor_ids,
            key=lambda actor_id: (self.readiness[actor_id], self.order.index(actor_id)),
        )
        candidate = candidates[0]
        if (
            candidate == self.consecutive_actor_id
            and self.consecutive_normal_turns >= 2
            and len(candidates) > 1
        ):
            candidate = candidates[1]
        return candidate
