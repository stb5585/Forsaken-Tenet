"""Lycan class definition and Moon Cycle helpers."""

from __future__ import annotations

from typing import Any

from src.core.randomness import gameplay_random as random

from .base import Job

MOON_PHASES = ("New", "Waxing", "Full", "Waning")
STEPS_PER_PHASE = 120


class Lycan(Job):
    """
    Promotion: Pathfinder -> Druid -> Lycan
    Additional Pros: Can unlock Dragon Essence; increased constitution gain
    Additional Cons: Lower intel gain
    Special Mechanic: Can shapeshift into alternative forms
    """

    def __init__(self):
        super().__init__(
            name="Lycan",
            description=(
                "Lycans coexist with a persistent Werewolf form whose Moon-driven stress "
                "becomes more controllable through successful play. Dragon Essence adds "
                "Winged Pounce without replacing the beast-self."
            ),
            str_plus=1,
            int_plus=0,
            wis_plus=1,
            con_plus=2,
            cha_plus=1,
            dex_plus=2,
            att_plus=3,
            def_plus=2,
            magic_plus=2,
            magic_def_plus=3,
            restrictions={
                "Weapon": ["Dagger", "Club", "Polearm", "Hammer", "Staff"],
                "OffHand": ["Tome"],
                "Armor": ["Cloth", "Light"],
            },
            pro_level=3,
        )


def default_state() -> dict[str, Any]:
    return {"moon_phase": "New", "moon_steps": 0, "frenzy_turns": 0}


def normalize_state(state: Any) -> dict[str, Any]:
    normalized = default_state()
    if isinstance(state, dict):
        phase = state.get("moon_phase", "New")
        normalized["moon_phase"] = phase if phase in MOON_PHASES else "New"
        for key in ("moon_steps", "frenzy_turns"):
            try:
                normalized[key] = max(0, int(state.get(key, 0) or 0))
            except (TypeError, ValueError):
                normalized[key] = 0
        if state.get("dragon_essence", False):
            normalized["dragon_essence"] = True
    return normalized


def ensure_state(character: Any) -> dict[str, Any]:
    state = normalize_state(getattr(character, "lycan_state", None))
    setattr(character, "lycan_state", state)
    return state


def record_steps(character: Any, steps: int = 1) -> dict[str, Any]:
    state = ensure_state(character)
    state["moon_steps"] += max(0, int(steps))
    while state["moon_steps"] >= STEPS_PER_PHASE:
        state["moon_steps"] -= STEPS_PER_PHASE
        index = (MOON_PHASES.index(state["moon_phase"]) + 1) % len(MOON_PHASES)
        state["moon_phase"] = MOON_PHASES[index]
    return state


def is_transformed(character: Any) -> bool:
    from . import transformation

    return transformation.is_transformed(character)


def phase_damage_bonus(character: Any) -> float:
    if not _is_lycan(character):
        return 0.0
    if not is_transformed(character):
        return 0.0
    phase = ensure_state(character)["moon_phase"]
    return {"New": 0.00, "Waxing": 0.05, "Full": 0.15, "Waning": 0.08}[phase]


def frenzy_damage_bonus(character: Any) -> float:
    state = ensure_state(character)
    if state["frenzy_turns"] <= 0:
        return 0.0
    bonus = 0.20
    try:
        from ..progression import has_talent

        if has_talent(character, "lycan.frenzied-force"):
            bonus += 0.10
    except (AttributeError, KeyError, TypeError):
        pass
    return bonus


def healing_multiplier(character: Any) -> float:
    state = ensure_state(character)
    if state["frenzy_turns"] <= 0:
        return 1.0
    from . import class_rings

    return class_rings.controlled_frenzy_healing_multiplier(character)


def maybe_trigger_frenzy(
    character: Any,
    *,
    reason: str,
    rng: Any = random,
) -> tuple[bool, str]:
    if not _is_lycan(character):
        return False, ""
    state = ensure_state(character)
    if state["frenzy_turns"] > 0:
        return False, ""
    phase = state["moon_phase"]
    base_chance = {"New": 0.05, "Waxing": 0.12, "Full": 0.25, "Waning": 0.16}[phase]
    if reason == "low_hp":
        base_chance += 0.10
    elif reason in {"kill", "extended"}:
        base_chance += 0.05
    from . import class_rings, promotion_kits, transformation

    control = promotion_kits.lycan_control_state(character)
    rank = str(control.get("rank", "Feral") or "Feral")
    rank_multiplier = {
        "Feral": 1.00,
        "Muzzled": 0.80,
        "Restive": 0.60,
        "Tethered": 0.40,
        "Tame": 0.20,
    }.get(rank, 1.00)
    base_chance *= rank_multiplier
    combat = promotion_kits.combat_state(character)
    if combat.pop("center_beast_ready", False):
        base_chance *= 0.50
    try:
        from ..progression import has_talent

        if has_talent(character, "lycan.measured-breath"):
            base_chance *= 0.85
    except (AttributeError, KeyError, TypeError):
        pass
    base_chance *= class_rings.controlled_frenzy_penalty_multiplier(character)
    if rng.random() >= base_chance:
        if rank == "Restive":
            promotion_kits.record_lycan_stress(character, "resist")
        return False, ""
    duration = {"New": 1, "Waxing": 2, "Full": 4, "Waning": 3}[phase]
    duration -= {"Feral": 0, "Muzzled": 0, "Restive": 1, "Tethered": 2, "Tame": 3}.get(rank, 0)
    if class_rings.controlled_frenzy_penalty_multiplier(character) < 1.0:
        duration -= 1
    duration = max(1, duration)
    message = ""
    if not is_transformed(character):
        message += transformation.apply_form(character, "Werewolf", force=True) + "\n"
    state["frenzy_turns"] = duration
    promotion_kits.combat_state(character)["lycan_stressed"] = True
    message += f"The {phase} Moon locks {character.name} into a frenzy for {duration} turns.\n"
    return True, message


def tick_frenzy(character: Any) -> str:
    state = ensure_state(character)
    if state["frenzy_turns"] <= 0:
        return ""
    state["frenzy_turns"] -= 1
    if state["frenzy_turns"] <= 0:
        return f"{character.name}'s frenzy loosens.\n"
    return ""


def _is_lycan(character: Any) -> bool:
    from . import transformation

    return transformation.permanent_class_name(character) == "Lycan"


def start_combat(character: Any) -> str:
    """Initialize Lycan stress triggers and check the Full Moon once."""
    if not _is_lycan(character):
        return ""
    from . import promotion_kits

    state = promotion_kits.combat_state(character)
    state["lycan_low_hp_checked"] = False
    state["lycan_transformed_turns"] = 0
    state["lycan_stressed"] = False
    state["lycan_success_keys"] = set()
    if ensure_state(character)["moon_phase"] == "Full":
        return maybe_trigger_frenzy(character, reason="combat_start")[1]
    return ""


def record_player_turn(character: Any) -> str:
    """Check low-health and extended-form stress at authored turn thresholds."""
    if not _is_lycan(character):
        return ""
    from . import promotion_kits

    combat = promotion_kits.combat_state(character)
    message = ""
    if (
        not combat.get("lycan_low_hp_checked")
        and character.health.max > 0
        and character.health.current / character.health.max < 0.25
    ):
        combat["lycan_low_hp_checked"] = True
        message += maybe_trigger_frenzy(character, reason="low_hp")[1]
    if is_transformed(character):
        turns = int(combat.get("lycan_transformed_turns", 0) or 0) + 1
        combat["lycan_transformed_turns"] = turns
        if turns == 5 or (turns > 5 and (turns - 5) % 3 == 0):
            message += maybe_trigger_frenzy(character, reason="extended")[1]
    return message


def record_transformed_kill(character: Any) -> str:
    """Resolve the once-per-killing-action transformed stress check."""
    if not _is_lycan(character) or not is_transformed(character):
        return ""
    return maybe_trigger_frenzy(character, reason="kill")[1]
