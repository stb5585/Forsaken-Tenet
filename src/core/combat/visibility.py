"""Core concealment, reveal, and Detect rules for combat."""

from __future__ import annotations

from typing import Any

from src.core.randomness import gameplay_random as random


def is_concealed(combatant: Any) -> bool:
    """Return whether a combatant currently hides its identity from opponents."""
    return bool(getattr(combatant, "_combat_concealed", False))


def is_revealed_to(observer: Any, combatant: Any) -> bool:
    """Return whether Sight or a recorded observation reveals a combatant."""
    if not is_concealed(combatant):
        return True
    if bool(getattr(observer, "sight", False)):
        return True
    observers = getattr(combatant, "_combat_revealed_to", set())
    return id(observer) in observers


def reveal_to(observer: Any, combatant: Any) -> None:
    """Record an observation that lasts until concealment is reapplied."""
    observers = set(getattr(combatant, "_combat_revealed_to", set()))
    observers.add(id(observer))
    combatant._combat_revealed_to = observers


def conceal(combatant: Any) -> None:
    """Apply concealment and clear prior per-observer observations."""
    combatant._combat_concealed = True
    combatant._combat_revealed_to = set()


def break_concealment(combatant: Any) -> None:
    """Remove concealment after a committed hostile direct action."""
    combatant._combat_concealed = False
    combatant._combat_revealed_to = set()


def detect_chance(observer: Any, combatant: Any, bonus: float = 0.0) -> float:
    """Return the approved bounded chance to reveal one concealed opponent."""
    wisdom = int(getattr(getattr(observer, "stats", None), "wisdom", 10) or 10)
    concealment = float(getattr(combatant, "_concealment_bonus", 0.0) or 0.0)
    return max(0.25, min(0.90, 0.50 + (0.025 * (wisdom - 10)) + bonus - concealment))


def detect(observer: Any, combatant: Any, *, rng: Any = random, bonus: float = 0.0) -> bool:
    """Attempt to reveal one concealed opponent without changing concealment."""
    if is_revealed_to(observer, combatant):
        return True
    if rng.random() < detect_chance(observer, combatant, bonus):
        reveal_to(observer, combatant)
        return True
    return False
