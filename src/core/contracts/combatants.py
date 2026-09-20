"""Minimal runtime protocols shared by foundational combat contracts."""

from typing import Protocol


class CombatStats(Protocol):
    """Read-only combat statistics needed by scheduling contracts."""

    @property
    def dex(self) -> int:
        """Return the combatant's dexterity."""


class Combatant(Protocol):
    """Structural character surface used by dependency-free combat models."""

    @property
    def name(self) -> str:
        """Return the combatant's display name."""

    @property
    def stats(self) -> CombatStats:
        """Return the combatant's scheduling statistics."""
