"""Sparse one-use traps for ordinary dungeon path tiles."""

from __future__ import annotations

from dataclasses import dataclass
from types import SimpleNamespace
from typing import Any

from src.core.randomness import gameplay_random as random

from .. import enemies
from ..classes import footpad
from ..constants import ARMOR_SCALING_FACTOR
from .rules import _queue_cambion_message, quest_biased_random_enemy

TRAP_CHANCE = 0.06
DEATHCAP_CHANCE = 0.015
TRAP_TYPES = ("Tripwire", "Magic Ward", "Alert", "Red Alert")
ELIGIBLE_PATH_TYPES = frozenset({"EmptyCavePath", "CavePath0", "CavePath1", "CavePath2"})
STANDARD_DUNGEON_DEPTHS = frozenset(range(0, 7))
MAGIC_WARD_SPELLS = (
    (0, "Firebolt", "Fire"),
    (0, "Tremor", "Earth"),
    (1, "Water Jet", "Water"),
    (1, "Gust", "Wind"),
    (2, "Ice", "Ice"),
    (2, "Lightning", "Electric"),
    (3, "Shadow Bolt", "Shadow"),
)


@dataclass(frozen=True)
class TrapFeedback:
    """Presentation-neutral damage feedback emitted by a resolved dungeon trap."""

    category: str
    damage: int
    trap_type: str
    source: str
    element: str | None = None


def pop_trap_feedback(player: Any) -> list[TrapFeedback]:
    """Return and clear transient damaging-trap feedback for a player."""
    queued = list(getattr(player, "_trap_feedback_queue", ()))
    player._trap_feedback_queue = []
    return queued


def _queue_trap_feedback(player: Any, feedback: TrapFeedback | None) -> None:
    if feedback is not None and feedback.damage > 0:
        queue = getattr(player, "_trap_feedback_queue", None)
        if queue is None:
            queue = []
            player._trap_feedback_queue = queue
        queue.append(feedback)


def find_trap_warning(tile: Any, player: Any, *, rng: Any = random) -> str:
    """Cancel the first detected trap entry and return its warning message."""
    if getattr(tile, "trap_type", None) not in TRAP_TYPES or getattr(tile, "trap_triggered", False):
        return ""
    if getattr(tile, "trap_warned", False):
        if footpad.has_skill(player, "Disarm Traps"):
            return disarm_tile_trap(tile, player, rng=rng)
        return ""
    if not footpad.has_skill(player, "Find Traps"):
        return ""
    dexterity = int(getattr(getattr(player, "stats", None), "dex", 10))
    depth = max(0, int(getattr(tile, "z", 0) or 0))
    chance = max(0.25, min(0.90, 0.45 + (0.025 * (dexterity - 10)) - (0.03 * depth)))
    from ..classes.thief import has_thief_talent

    if has_thief_talent(player, "thief.trap-lore"):
        chance = min(0.95, chance + 0.15)
    if rng.random() >= chance:
        return ""
    tile.trap_warned = True
    return f"{player.name} notices a hidden {tile.trap_type} ahead and stops before entering."


def disarm_tile_trap(tile: Any, player: Any, *, rng: Any = random) -> str:
    """Attempt to disarm a previously detected trap and stop movement."""
    trap_type = getattr(tile, "trap_type", None)
    if (
        trap_type not in TRAP_TYPES
        or getattr(tile, "trap_triggered", False)
        or not getattr(tile, "trap_warned", False)
        or not footpad.has_skill(player, "Disarm Traps")
    ):
        return ""
    from .. import items
    from ..classes.thief import has_thief_talent

    dexterity = int(getattr(getattr(player, "stats", None), "dex", 10))
    depth = max(0, int(getattr(tile, "z", 0) or 0))
    difficulty = {
        "Tripwire": 0.00,
        "Magic Ward": 0.08,
        "Alert": 0.05,
        "Red Alert": 0.15,
    }[trap_type]
    chance = 0.40 + (0.025 * (dexterity - 10)) - (0.035 * depth) - difficulty
    if items.has_lockpick_kit(player):
        chance += 0.10
    if footpad.has_skill(player, "Master Lockpick"):
        chance += 0.10
    if has_thief_talent(player, "rogue.sure-hands"):
        chance += 0.15
    cap = 0.95 if has_thief_talent(player, "rogue.impossible-job") else 0.90
    chance = max(0.15, min(cap, chance))
    if rng.random() < chance:
        tile.trap_triggered = True
        return f"{player.name} disarms the hidden {trap_type}."
    player._failed_disarm = True
    message = trigger_tile_trap(tile, player, rng=rng)
    player._failed_disarm = False
    return f"{player.name} fails to disarm the {trap_type}. {message}"


def assign_dungeon_traps(world_dict: dict, *, rng: Any | None = None) -> int:
    """Randomly arm a stable, sparse set of ordinary cave-path tiles."""
    rng = rng or random.Random(0xD06E0)
    assigned = 0
    for tile in world_dict.values():
        if (
            type(tile).__name__ not in ELIGIBLE_PATH_TYPES
            or int(getattr(tile, "z", -1)) not in STANDARD_DUNGEON_DEPTHS
        ):
            continue
        tile.trap_type = None
        tile.trap_triggered = False
        tile.trap_warned = False
        tile.deathcap_available = rng.random() < DEATHCAP_CHANCE
        tile.deathcap_gathered = False
        if rng.random() >= TRAP_CHANCE:
            continue
        tile.trap_type = rng.choices(
            TRAP_TYPES,
            weights=(0.35, 0.30, 0.25, 0.10),
            k=1,
        )[0]
        assigned += 1
    return assigned


def _avoidance_severity(player: Any, *, rng: Any) -> tuple[float, str]:
    """Return the fraction of a trap effect remaining after Avoid Traps."""
    severity, message = footpad.trap_severity_multiplier(player, rng=rng)
    try:
        from ..classes.thief import has_thief_talent

        if getattr(player, "_failed_disarm", False) and has_thief_talent(
            player, "rogue.impossible-job"
        ):
            severity = min(severity, 0.5)
            message = message or "Impossible Job halves the failed disarm's effect."
    except (AttributeError, KeyError, TypeError, ValueError):
        pass
    return severity, message


def _tripwire(
    tile: Any, player: Any, severity: float, *, rng: Any
) -> tuple[str, TrapFeedback | None]:
    depth = max(0, int(tile.z))
    raw_damage = rng.randint(8 + (depth * 6), 14 + (depth * 8))
    armor = max(0, int(player.check_mod("armor")))
    damage = int(raw_damage * (1 - (armor / (armor + ARMOR_SCALING_FACTOR))))
    damage = max(1, int(damage * severity)) if severity else 0
    if damage:
        damage = min(damage, max(0, int(player.health.current) - 1))
        player.health.current -= damage
        return (
            f"A hidden tripwire launches an arrow, dealing {damage} Physical damage.",
            TrapFeedback("physical", damage, "Tripwire", "arrow"),
        )
    return "A hidden tripwire snaps, but its arrow misses harmlessly.", None


def _magic_ward(
    tile: Any, player: Any, severity: float, *, rng: Any
) -> tuple[str, TrapFeedback | None]:
    depth = max(0, int(tile.z))
    available = [entry for entry in MAGIC_WARD_SPELLS if entry[0] <= depth]
    _minimum_depth, spell_name, damage_type = rng.choice(available)
    raw_damage = rng.randint(10 + (depth * 7), 16 + (depth * 10))
    raw_damage = max(0, int(raw_damage * severity))
    source = SimpleNamespace(name="Magic Ward")
    _hit, reduction_message, damage = player.damage_reduction(
        raw_damage,
        source,
        typ=damage_type,
    )
    damage = min(max(0, int(damage)), max(0, int(player.health.current) - 1))
    player.health.current -= damage
    message = f"A Magic Ward casts {spell_name}, dealing {damage} {damage_type} damage."
    if reduction_message:
        message += f" {reduction_message.strip()}"
    feedback = (
        TrapFeedback("magical", damage, "Magic Ward", spell_name, damage_type)
        if damage > 0
        else None
    )
    return message, feedback


def _alert(tile: Any, player: Any, severity: float, *, red: bool, rng: Any) -> str:
    if severity <= 0:
        return "The alarm mechanism clicks, but you disable it before it sounds."
    local_depth = max(0, int(tile.z))
    encounter_depth = local_depth + int(red and severity >= 1.0)
    if red:
        tile.enemy = enemies.random_enemy(str(encounter_depth), rng=rng)
    else:
        tile.enemy = quest_biased_random_enemy(player, str(encounter_depth), rng=rng)
    player.state = "fight"
    tile.trap_forced_initiative = bool(red or severity >= 1.0)
    if red and severity < 1.0:
        return "You partially disable a Red Alert; it summons a local enemy, but still gives it initiative."
    label = "Red Alert" if red else "Alert"
    difficulty = "a stronger enemy" if red else "a local enemy"
    return f"A hidden {label} sounds, drawing {difficulty}; it has the initiative."


def trigger_tile_trap(tile: Any, player: Any, *, rng: Any = random) -> str:
    """Trigger and disarm a tile's trap, returning its exploration message."""
    trap_type = getattr(tile, "trap_type", None)
    if trap_type not in TRAP_TYPES or getattr(tile, "trap_triggered", False):
        return ""
    tile.trap_triggered = True
    severity, avoidance_message = _avoidance_severity(player, rng=rng)
    if trap_type == "Tripwire":
        message, feedback = _tripwire(tile, player, severity, rng=rng)
    elif trap_type == "Magic Ward":
        message, feedback = _magic_ward(tile, player, severity, rng=rng)
    elif trap_type == "Alert":
        message = _alert(tile, player, severity, red=False, rng=rng)
        feedback = None
    else:
        message = _alert(tile, player, severity, red=True, rng=rng)
        feedback = None
    if avoidance_message:
        message = f"{avoidance_message} {message}"
    _queue_cambion_message(player, message)
    _queue_trap_feedback(player, feedback)
    return message
