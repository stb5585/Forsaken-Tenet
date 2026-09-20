# effects/base.py
from __future__ import annotations

from abc import ABC, abstractmethod

from ..combat.combat_result import CombatResult
from ..contracts.combatants import Combatant


class Effect(ABC):
    """Base class for all effects that can be applied in combat."""

    @abstractmethod
    def apply(self, actor: Combatant, target: Combatant, result: CombatResult) -> None:
        """Apply the effect to the target character."""
        pass
