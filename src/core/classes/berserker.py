"""Berserker class definition and Battle Scars helpers."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from src.core.randomness import gameplay_random as random

from .base import Job

SCAR_CAP = 20
SCAR_CHANCE = 0.10
LOW_HP_THRESHOLD = 0.10
BLOODIED_DAMAGE_THRESHOLD = 0.25
MOMENTUM_ACCURACY_PER_STACK = 0.03
MOMENTUM_DAMAGE_PER_STACK = 0.05
MOMENTUM_RIDER_PER_STACK = 0.02
RING_MOMENTUM_RIDER_PER_STACK = 0.03
HEAVY_ARTS = frozenset(
    {
        "Guard Cleaver",
        "Reaver's Mark",
        "Brace",
        "Anvil Strike",
    }
)


@dataclass(frozen=True)
class BloodiedMomentumPayoff:
    """Bonuses captured when a validated Berserker payoff spends Momentum."""

    stacks: int = 0
    accuracy_bonus: float = 0.0
    damage_bonus: float = 0.0
    rider_per_stack: float = MOMENTUM_RIDER_PER_STACK
    crush_bonus: int = 0


class Berserker(Job):
    """
    Promotion: Warrior -> Weapon Master -> Berserker
    Additional Pros: Can dual wield 2-handed weapons; additional charisma gain
    Additional Cons: Can only equip light armor
    Special Mechanic: Battle Scars - surviving combat with less than 10% health gives
        a chance of earning a permanent scar.
    """

    def __init__(self):
        super().__init__(
            name="Berserker",
            description="Berserkers are combat masters, driven by pure rage and "
            "vengeance. Their strength is so great, they gain the "
            "ability to dual wield two-handed weapons. Their further "
            "reliance on maneuverability limits the type of armor to light "
            "armor.",
            str_plus=3,
            int_plus=0,
            wis_plus=0,
            con_plus=1,
            cha_plus=1,
            dex_plus=2,
            att_plus=5,
            def_plus=2,
            magic_plus=0,
            magic_def_plus=3,
            restrictions={
                "Weapon": ["Longsword", "Battle Axe", "Polearm", "Hammer"],
                "OffHand": ["Longsword", "Battle Axe", "Polearm", "Hammer"],
                "Armor": ["Light"],
            },
            pro_level=3,
        )


def data(character: Any) -> dict[str, Any]:
    from . import class_rings

    state = class_rings.ensure_state(character)
    berserker = state["data"].setdefault("Berserker", {})
    berserker.setdefault("no_healing_duel_complete", False)
    berserker["battle_scars"] = max(
        0,
        min(SCAR_CAP, int(berserker.get("battle_scars", 0) or 0)),
    )
    berserker["battle_scar_hp_bonus"] = max(
        0,
        int(berserker.get("battle_scar_hp_bonus", 0) or 0),
    )
    return berserker


def scar_count(character: Any) -> int:
    return int(data(character).get("battle_scars", 0) or 0)


def bloodied_weapon_bonus(character: Any) -> float:
    if getattr(getattr(character, "cls", None), "name", "") != "Berserker":
        return 0.0
    hp_max = max(1, int(getattr(getattr(character, "health", None), "max", 1) or 1))
    if getattr(character.health, "current", hp_max) / hp_max >= BLOODIED_DAMAGE_THRESHOLD:
        return 0.0
    return scar_count(character) * 0.005


def _base_art_name(art_name: str) -> str:
    return art_name[:-2] if art_name.endswith((" 2", " 3")) else art_name


def _ring_reliability_active(character: Any) -> bool:
    from . import class_rings

    hp_max = max(1, int(getattr(character.health, "max", 1) or 1))
    return bool(
        character.health.current / hp_max < BLOODIED_DAMAGE_THRESHOLD
        and class_rings.is_awakened(character, "Berserker")
        and class_rings.has_equipped_class_ring(character)
    )


def prepare_heavy_art_payoff(
    character: Any,
    art_name: str,
) -> tuple[BloodiedMomentumPayoff, str]:
    """Spend Momentum for a validated heavy weapon art."""
    if (
        getattr(getattr(character, "cls", None), "name", "") != "Berserker"
        or _base_art_name(art_name) not in HEAVY_ARTS
    ):
        return BloodiedMomentumPayoff(), ""

    from . import promotion_kits

    stacks = promotion_kits.spend_meter(character, "bloodied_momentum")
    if stacks <= 0:
        return BloodiedMomentumPayoff(), ""
    state = promotion_kits.combat_state(character)
    state["bloodied_payoff_action_token"] = int(state.get("action_token", 0) or 0)
    ring_boost = _ring_reliability_active(character)
    payoff = BloodiedMomentumPayoff(
        stacks=stacks,
        accuracy_bonus=MOMENTUM_ACCURACY_PER_STACK * stacks,
        damage_bonus=MOMENTUM_DAMAGE_PER_STACK * stacks,
        rider_per_stack=(RING_MOMENTUM_RIDER_PER_STACK if ring_boost else MOMENTUM_RIDER_PER_STACK),
        crush_bonus=stacks + int(ring_boost),
    )
    return (
        payoff,
        f"{character.name} spends {stacks} Bloodied Momentum on {art_name}.\n",
    )


def resolve_heavy_art_payoff(
    character: Any,
    payoff: BloodiedMomentumPayoff,
    *,
    hit: bool,
) -> str:
    """Apply the once-per-combat preservation appropriate to an art result."""
    if payoff.stacks <= 0:
        return ""

    from . import class_rings, promotion_kits

    state = promotion_kits.combat_state(character)
    state["bloodied_payoff_action_token"] = None
    if hit:
        if scar_count(character) < 10 or state.get("battle_scar_momentum_preserved"):
            return ""
        state["battle_scar_momentum_preserved"] = True
        state["bloodied_momentum"] = max(
            1,
            int(state.get("bloodied_momentum", 0) or 0),
        )
        return "Battle Scars preserve 1 Bloodied Momentum after the clean payoff.\n"

    hp_max = max(1, int(getattr(character.health, "max", 1) or 1))
    ring_ready = bool(
        character.health.current / hp_max < 0.50
        and class_rings.is_awakened(character, "Berserker")
        and class_rings.has_equipped_class_ring(character)
    )
    if not ring_ready or state.get("bloodied_ring_miss_preserved"):
        return "Bloodied Momentum is spent despite the miss.\n"
    state["bloodied_ring_miss_preserved"] = True
    state["bloodied_momentum"] = max(
        1,
        int(state.get("bloodied_momentum", 0) or 0),
    )
    return "Bloodied Crits preserves 1 Bloodied Momentum after the missed payoff.\n"


def prepare_final_assault_payoff(character: Any) -> tuple[BloodiedMomentumPayoff, str]:
    """Spend Momentum to reinforce a triggered Final Assault counter."""
    from . import promotion_kits

    if getattr(getattr(character, "cls", None), "name", "") != "Berserker":
        return BloodiedMomentumPayoff(), ""
    stacks = promotion_kits.spend_meter(character, "bloodied_momentum")
    if stacks <= 0:
        return BloodiedMomentumPayoff(), ""
    return (
        BloodiedMomentumPayoff(
            stacks=stacks,
            accuracy_bonus=MOMENTUM_ACCURACY_PER_STACK * stacks,
            damage_bonus=MOMENTUM_DAMAGE_PER_STACK * stacks,
        ),
        f"{character.name} spends {stacks} Bloodied Momentum on Final Assault.\n",
    )


def scar_qualification_threshold(character: Any) -> float:
    """Return the low-health victory threshold for earning another scar."""
    return 0.15 if scar_count(character) >= SCAR_CAP else LOW_HP_THRESHOLD


def record_battle_scar(character: Any, *, rng: Any = random) -> tuple[bool, str]:
    """Roll for a Battle Scar after a qualifying non-trial victory."""
    if getattr(getattr(character, "cls", None), "name", "") != "Berserker":
        return False, ""
    hp = getattr(character, "health", None)
    hp_max = max(1, int(getattr(hp, "max", 1) or 1))
    threshold = scar_qualification_threshold(character)
    if getattr(hp, "current", hp_max) / hp_max > threshold:
        return False, ""

    berserker = data(character)
    if int(berserker.get("battle_scars", 0) or 0) >= SCAR_CAP:
        return False, (
            f"{character.name}'s Battle Scars hold steady at the "
            f"{int(threshold * 100)}% victory threshold.\n"
        )
    if rng.random() >= SCAR_CHANCE:
        return False, ""

    berserker["battle_scars"] = int(berserker.get("battle_scars", 0) or 0) + 1
    hp_bonus = max(1, int(hp_max * 0.01))
    berserker["battle_scar_hp_bonus"] = (
        int(berserker.get("battle_scar_hp_bonus", 0) or 0) + hp_bonus
    )
    character.health.max += hp_bonus
    character.health.current = min(character.health.max, character.health.current + hp_bonus)
    stability = " at the 15% scar-stability threshold" if threshold > LOW_HP_THRESHOLD else ""
    return True, (
        f"{character.name} earns a Battle Scar{stability}. " f"Max HP rises by {hp_bonus}.\n"
    )
