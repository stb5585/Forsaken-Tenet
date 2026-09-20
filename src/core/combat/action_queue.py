"""
Action Queue System for Combat

This module implements a priority-based action queue for turn-based combat.
It allows for:
- Speed-based turn order
- Delayed actions (charge-up abilities)
- Stacked enemy AI behavior
- Simultaneous action resolution
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable

from ..contracts.combatants import Combatant


class ActionPriority(Enum):
    """Priority levels for action execution."""

    IMMEDIATE = 0  # Counter-attacks, automatic responses
    HIGH = 1  # Fast actions, quick strikes
    NORMAL = 2  # Standard attacks and abilities
    LOW = 3  # Slow/charging abilities
    DELAYED = 4  # Actions that occur later (e.g., after X turns)
    LOW_HP_ONLY = 50  # AI-only: selectable only when the actor is below an HP threshold
    SKIP = 99  # AI-only: do not select/schedule this action


class ActionType(Enum):
    """Types of actions that can be queued."""

    ATTACK = "attack"
    SKILL = "skill"
    SPELL = "spell"
    ITEM = "item"
    DEFEND = "defend"
    FLEE = "flee"
    SPECIAL = "special"
    STATUS_TICK = "status_tick"


@dataclass
class ScheduledAction:
    """
    Represents a single action scheduled in the combat queue.

    Attributes:
        actor: The character performing the action
        action_type: What kind of action this is
        target: The target of the action (None for self-target or AOE)
        priority: When this action should execute relative to others
        delay: Number of turns before this action executes (0 = this turn)
        callback: The function to execute when this action resolves
        params: Additional parameters to pass to the callback
        speed_modifier: Adjustment to base speed for this specific action
        metadata: Additional data for logging/analytics
    """

    actor: Combatant
    action_type: ActionType
    target: Combatant | None
    priority: ActionPriority
    callback: Callable[..., Any]
    delay: int = 0
    params: dict[str, Any] = field(default_factory=dict)
    speed_modifier: float = 1.0
    metadata: dict[str, Any] = field(default_factory=dict)

    def __lt__(self, other: ScheduledAction) -> bool:
        """
        Compare actions for sorting in the queue.
        Lower priority value = executes first.
        If same priority, higher speed executes first.
        """
        if self.priority.value != other.priority.value:
            return self.priority.value < other.priority.value

        # Calculate effective speed
        actor_speed = self.actor.stats.dex * self.speed_modifier
        other_speed = other.actor.stats.dex * other.speed_modifier

        return actor_speed > other_speed

    def is_ready(self) -> bool:
        """Check if this action is ready to execute (delay has elapsed)."""
        return self.delay <= 0

    def tick(self) -> None:
        """Decrement the delay counter."""
        if self.delay > 0:
            self.delay -= 1


class ActionQueue:
    """
    Manages the queue of actions in combat.

    This implements a priority queue where actions are sorted by:
    1. Priority level
    2. Actor speed (within same priority)
    """

    def __init__(self):
        self.queue: list[ScheduledAction] = []
        self.history: list[ScheduledAction] = []
        self.current_round: int = 0

    def schedule(
        self,
        actor: Combatant,
        action_type: ActionType,
        callback: Callable[..., Any],
        target: Combatant | None = None,
        priority: ActionPriority = ActionPriority.NORMAL,
        delay: int = 0,
        speed_modifier: float = 1.0,
        **params,
    ) -> ScheduledAction:
        """
        Add an action to the queue.

        Args:
            actor: The character performing the action
            action_type: Type of action being performed
            callback: Function to call when action executes
            target: Target of the action (optional)
            priority: Priority level for execution order
            delay: Turns to wait before executing (0 = immediate)
            speed_modifier: Multiplier for actor's speed (e.g., 1.5 for fast attack)
            **params: Additional parameters for the callback

        Returns:
            The scheduled action object
        """
        normalized_delay = max(0, delay)
        action = ScheduledAction(
            actor=actor,
            action_type=action_type,
            target=target,
            priority=priority,
            callback=callback,
            delay=normalized_delay,
            speed_modifier=speed_modifier,
            params=params,
            metadata={
                "scheduled_round": self.current_round,
                "scheduled_at": self.current_round,
            },
        )

        self.queue.append(action)
        self._sort_queue()
        return action

    def _sort_queue(self) -> None:
        """Sort the queue by priority and speed."""
        self.queue.sort()

    def get_next_action(self) -> ScheduledAction | None:
        """
        Get the next ready action from the queue.

        Returns:
            The next action to execute, or None if no actions are ready
        """
        # Tick down all delays
        for action in self.queue:
            action.tick()

        # Find first ready action
        for i, action in enumerate(self.queue):
            if action.is_ready():
                return self.queue.pop(i)

        return None

    def resolve_next(self) -> Any:
        """
        Execute the next action in the queue.

        Returns:
            The result of the action's callback
        """
        action = self.get_next_action()
        if action is None:
            return None

        # Execute the action
        action.metadata["executed_round"] = self.current_round
        result = action.callback(actor=action.actor, target=action.target, **action.params)

        # Store in history for analytics
        self.history.append(action)

        return result

    def has_ready_actions(self) -> bool:
        """Check if there are any actions ready to execute."""
        return any(action.is_ready() for action in self.queue)

    def clear(self) -> None:
        """Clear all queued actions."""
        self.queue.clear()

    def next_round(self) -> None:
        """Advance to the next round."""
        self.current_round += 1

    def get_actions_for(self, actor: Combatant) -> list[ScheduledAction]:
        """Get all queued actions for a specific actor."""
        return [action for action in self.queue if action.actor == actor]

    def cancel_actions_for(self, actor: Combatant) -> int:
        """
        Cancel all queued actions for a specific actor.
        Useful for stun, death, etc.

        Returns:
            Number of actions cancelled
        """
        original_count = len(self.queue)
        self.queue = [action for action in self.queue if action.actor != actor]
        return original_count - len(self.queue)


class TurnManager:
    """
    Manages turn order and round progression in combat.

    This works alongside ActionQueue to handle:
    - Initiative determination
    - Round-based effects
    - Turn cycling
    """

    def __init__(self, participants: list[Combatant]):
        self.participants = participants
        self.action_queue = ActionQueue()
        self.turn_order: list[Combatant] = []
        self.current_turn_index: int = 0

    def determine_turn_order(self) -> list[Combatant]:
        """
        Determine the turn order for this round based on speed.

        Returns:
            List of characters in order from fastest to slowest
        """
        # Sort by dexterity + random factor for variety
        import random

        turn_order = sorted(
            self.participants, key=lambda char: char.stats.dex + random.randint(-5, 5), reverse=True
        )

        self.turn_order = turn_order
        self.current_turn_index = 0
        return turn_order

    def get_current_actor(self) -> Combatant | None:
        """Get the character whose turn it is."""
        if not self.turn_order or self.current_turn_index >= len(self.turn_order):
            return None
        return self.turn_order[self.current_turn_index]

    def next_turn(self) -> Combatant | None:
        """
        Advance to the next character's turn.

        Returns:
            The next character to act, or None if round is complete
        """
        self.current_turn_index += 1

        if self.current_turn_index >= len(self.turn_order):
            # Round is complete
            return None

        return self.get_current_actor()

    def start_new_round(self) -> None:
        """Start a new combat round."""
        self.action_queue.next_round()
        self.determine_turn_order()

    def is_round_complete(self) -> bool:
        """Check if all participants have taken their turn this round."""
        return self.current_turn_index >= len(self.turn_order)


# Example usage and integration helpers
def create_attack_action(
    actor: Combatant, target: Combatant, attack_callback: Callable[..., Any], fast: bool = False
) -> ScheduledAction:
    """
    Helper to create a standard attack action.

    Args:
        actor: The attacking character
        target: The target being attacked
        attack_callback: Function that performs the attack
        fast: If True, uses HIGH priority (quick attack)

    Returns:
        The scheduled action
    """
    priority = ActionPriority.HIGH if fast else ActionPriority.NORMAL

    return ScheduledAction(
        actor=actor,
        action_type=ActionType.ATTACK,
        target=target,
        priority=priority,
        callback=attack_callback,
        speed_modifier=1.5 if fast else 1.0,
        metadata={"helper": "attack", "fast": fast},
    )


def create_spell_action(
    actor: Combatant,
    target: Combatant,
    spell_callback: Callable[..., Any],
    cast_time: int = 0,
) -> ScheduledAction:
    """
    Helper to create a spell casting action.

    Args:
        actor: The caster
        target: The spell target
        spell_callback: Function that casts the spell
        cast_time: Number of turns required to cast (0 = instant)

    Returns:
        The scheduled action
    """
    normalized_cast_time = max(0, cast_time)
    priority = ActionPriority.DELAYED if normalized_cast_time > 0 else ActionPriority.NORMAL

    return ScheduledAction(
        actor=actor,
        action_type=ActionType.SPELL,
        target=target,
        priority=priority,
        callback=spell_callback,
        delay=normalized_cast_time,
        speed_modifier=0.8,  # Spells are generally slower
        metadata={"helper": "spell", "cast_time": normalized_cast_time},
    )
