"""Runtime resolution coverage for foundational combat annotations."""

from typing import get_type_hints

from src.core.combat.action_queue import ScheduledAction
from src.core.combat.combat_result import CombatResult
from src.core.effects.base import Effect
from src.core.events.event_bus import CombatEvent


def test_foundational_combat_annotations_resolve_at_runtime():
    """Public combat contracts must support runtime annotation inspection."""
    for contract in (CombatEvent, CombatResult, ScheduledAction, Effect.apply):
        assert get_type_hints(contract)
