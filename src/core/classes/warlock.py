"""Warlock class definition."""

from __future__ import annotations

from typing import Any

from src.core.randomness import gameplay_random as random

from .base import Job


class Warlock(Job):
    """
    Promotion: Mage -> Warlock -> Shadowcaster
                               |
                               -> Demonologist
    Pros: Higher charisma and constitution gain; access to additional skills; gains access to shadow spells and familiar
    Cons: Lower intelligence gain and limited access to higher-level tree spells
    Special Mechanic: Gains familiar that sometimes acts in or out of combat
    """

    def __init__(self):
        super().__init__(
            name="Warlock",
            description="The Warlock specializes in the dark arts while retaining earlier "
            "Mage training. This focus unlocks powerful "
            "abilities, including the ability to summon a familiar to aid "
            "them.",
            str_plus=0,
            int_plus=2,
            wis_plus=1,
            con_plus=1,
            cha_plus=2,
            dex_plus=0,
            att_plus=1,
            def_plus=1,
            magic_plus=4,
            magic_def_plus=2,
            restrictions={
                "Weapon": ["Dagger", "Staff"],
                "OffHand": ["Tome"],
                "Armor": ["Cloth"],
            },
            pro_level=2,
        )


def mark_corruption(
    caster: Any,
    target: Any,
    *,
    rank: int = 1,
    contracts: int = 0,
) -> None:
    """Attach transient propagation data to a Corruption DOT target."""
    dot = getattr(target, "magic_effects", {}).get("DOT")
    if dot is None or not dot.active:
        return
    contract_count = max(0, int(contracts or 0)) if rank >= 2 else 0
    target._corruption_payload = {
        "caster": caster,
        "rank": max(1, int(rank or 1)),
        "contracts": contract_count,
        "jump_chance": min(0.60, 0.25 + (contract_count * 0.05)),
        "duration": max(1, int(dot.duration or 0)),
        "damage": max(1, int(dot.extra or 0)),
    }


def spread_corruption(target: Any, *, rng: Any = random) -> str:
    """Try to move a ticking Corruption effect to an adjacent enemy slot."""
    payload = getattr(target, "_corruption_payload", None)
    if not isinstance(payload, dict):
        return ""
    if rng.random() >= float(payload.get("jump_chance", 0.25) or 0.25):
        return ""
    caster = payload.get("caster")
    encounter = getattr(caster, "_combat_encounter", None)
    living_members = list(getattr(encounter, "living_members", ()))
    source_member = next(
        (member for member in getattr(encounter, "members", ()) if member.enemy is target),
        None,
    )
    if source_member is None:
        return ""
    adjacent = [
        member
        for member in living_members
        if abs(int(member.slot) - int(source_member.slot)) == 1
        and not member.enemy.magic_effects["DOT"].active
    ]
    if not adjacent:
        return ""
    infected = rng.choice(adjacent).enemy
    dot = infected.magic_effects["DOT"]
    dot.active = True
    dot.duration = max(1, int(payload.get("duration", 1) or 1))
    dot.extra = max(1, int(payload.get("damage", 1) or 1))
    dot.source = "Corruption"
    infected._corruption_payload = dict(payload)
    try:
        caster._emit_status_event(
            infected,
            "DOT",
            applied=True,
            duration=dot.duration,
            source="Corruption",
        )
    except Exception:
        pass
    return f"Corruption jumps from {target.name} to {infected.name}.\n"
