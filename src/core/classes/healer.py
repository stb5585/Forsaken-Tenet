"""Healer class definition."""

from __future__ import annotations

from src.core.randomness import gameplay_random as random

from .. import items
from .base import Job


def has_skill(character, name: str) -> bool:
    """Return whether a character knows a named Healer-tree skill."""
    return name in getattr(character, "spellbook", {}).get("Skills", {})


def start_combat(character) -> None:
    """Reset encounter-local Healer mechanics."""
    character._beginners_luck_active = False
    character._delayed_reaction_damage = []
    character._meditation_state = None


def luck_bonus(character, luck_factor: int) -> int:
    """Return Beginner's Luck's extra Charisma contribution."""
    if not getattr(character, "_beginners_luck_active", False):
        return 0
    return max(1, int(character.stats.charisma) // max(1, int(luck_factor)))


def accuracy_bonus(character, weapon_type: str | None = None) -> float:
    """Return Zen Accuracy and Staff Proficiency's combined hit bonus."""
    bonus = 0.05 if has_skill(character, "Zen Accuracy") else 0.0
    if weapon_type == "Staff" and has_skill(character, "Staff Proficiency"):
        bonus += 0.10
    if weapon_type in {"None", "Fist"} and has_skill(character, "Unarmed Proficiency"):
        bonus += 0.10
    return bonus


def staff_damage_multiplier(character, weapon_type: str | None) -> float:
    """Return Staff Proficiency's weapon damage multiplier."""
    if weapon_type == "Staff" and has_skill(character, "Staff Proficiency"):
        return 1.10
    if weapon_type in {"None", "Fist"} and has_skill(character, "Unarmed Proficiency"):
        return 1.10
    return 1.0


def apply_safeguarding(caster, target, source: str) -> None:
    """Arm Safeguarding after a direct Heal-family spell."""
    if has_skill(caster, "Safeguarding") and not source.lower().startswith("regen"):
        target._safeguarding_reduction = 0.25


def reduce_incoming_damage(
    character,
    damage: int,
    *,
    melee: bool,
    rng=None,
) -> tuple[int, str]:
    """Apply Meditation, Safeguarding, and Tutelary to incoming damage."""
    damage = max(0, int(damage))
    state = getattr(character, "_meditation_state", None)
    if isinstance(state, dict) and int(state.get("turns", 0) or 0) > 0 and damage:
        state["stored"] = int(state.get("stored", 0) or 0) + damage
        return 0, f"{character.name}'s meditation stores {damage} damage.\n"
    message = ""
    try:
        from ..progression import has_talent

        weapon = getattr(character, "equipment", {}).get("Weapon")
        armor = getattr(character, "equipment", {}).get("Armor")
        if (
            damage
            and has_talent(character, "master-monk.empty-fortress")
            and getattr(weapon, "subtyp", "None") in {"None", "Fist"}
            and int(getattr(armor, "armor", 0) or 0) == 0
        ):
            prevented = max(1, int(damage * 0.10))
            damage -= prevented
            message += f"Empty Fortress prevents {prevented} damage.\n"
    except (AttributeError, KeyError, TypeError, ValueError):
        pass
    if melee and damage and float(getattr(character, "_safeguarding_reduction", 0) or 0):
        reduction = min(0.75, float(character._safeguarding_reduction))
        reduced = max(1, int(damage * reduction))
        damage -= reduced
        character._safeguarding_reduction = 0.0
        message += f"Safeguarding reduces the melee damage by {reduced}.\n"
    generator = rng or random
    if (
        damage
        and int(getattr(character, "_tutelary_turns", 0) or 0) > 0
        and generator.random() < 0.25
    ):
        reduced = max(1, damage // 2)
        damage -= reduced
        message += f"{character.name}'s tutelary spirit prevents {reduced} damage.\n"
    return damage, message


def delay_critical_damage(character, damage: int, *, rng=None) -> tuple[int, str]:
    """Possibly defer a critical hit into three end-of-turn installments."""
    if not has_skill(character, "Delayed Reaction") or damage <= 0:
        return damage, ""
    generator = rng or random
    if generator.random() >= 0.25:
        return damage, ""
    base, remainder = divmod(int(damage), 3)
    installments = [base + (1 if index < remainder else 0) for index in range(3)]
    queue = getattr(character, "_delayed_reaction_damage", [])
    queue.extend(amount for amount in installments if amount > 0)
    character._delayed_reaction_damage = queue
    return 0, f"{character.name}'s Delayed Reaction spreads the critical damage over time.\n"


def meditation_release(character) -> int:
    """Consume and return Meditation's doubled stored-damage release."""
    state = getattr(character, "_meditation_state", None)
    if not isinstance(state, dict) or not state.get("ready"):
        return 0
    bonus = max(0, int(state.get("stored", 0) or 0) * 2)
    character._meditation_state = None
    return bonus


def flash_blindness(character, enemies, *, rng=None) -> str:
    """Chance for a Holy cast to blind every nearby enemy."""
    if not has_skill(character, "Flash Blindness"):
        return ""
    generator = rng or random
    if generator.random() >= 0.25:
        return ""
    affected = 0
    for enemy in enemies:
        if enemy.has_status_protection("Blind"):
            continue
        blind = enemy.status_effects["Blind"]
        blind.active = True
        blind.duration = max(2, int(blind.duration or 0))
        blind.source = "Flash Blindness"
        affected += 1
    return f"Flash Blindness blinds {affected} nearby enemy(s).\n" if affected else ""


def tick_combat_state(character, *, end: bool = False) -> str:
    """Advance temporary Healer-tree effects for one character turn."""
    message = ""
    mental_shard = getattr(character, "_mental_shard", None)
    if isinstance(mental_shard, dict):
        mental_shard["turns"] = 0 if end else int(mental_shard.get("turns", 0)) - 1
        if mental_shard["turns"] <= 0:
            character.stats.intel += int(mental_shard.get("amount", 0) or 0)
            character._mental_shard = None
            message += f"{character.name}'s Intelligence recovers.\n"
    if end:
        for attribute in (
            "_beginners_luck_active",
            "_courage_turns",
            "_tutelary_turns",
            "_vision_turns",
            "_delayed_reaction_damage",
            "_meditation_state",
            "_safeguarding_reduction",
        ):
            if hasattr(character, attribute):
                delattr(character, attribute)
        return message
    for attribute in ("_courage_turns", "_tutelary_turns", "_vision_turns"):
        turns = max(0, int(getattr(character, attribute, 0) or 0) - 1)
        setattr(character, attribute, turns)
    if int(getattr(character, "_vision_turns", 0) or 0) <= 0 and not int(
        getattr(character, "_vision_steps", 0) or 0
    ):
        character.sight = False
    state = getattr(character, "_meditation_state", None)
    if isinstance(state, dict) and not state.get("ready"):
        state["turns"] = max(0, int(state.get("turns", 0) or 0) - 1)
        if state["turns"] == 0:
            state["ready"] = True
            message += f"{character.name}'s meditation is ready to be released.\n"
    queue = getattr(character, "_delayed_reaction_damage", [])
    if queue:
        damage = max(0, int(queue.pop(0)))
        character.health.current -= damage
        message += f"Delayed Reaction deals {damage} damage to {character.name}.\n"
    return message


def tick_exploration(character, steps: int) -> None:
    """Advance Vision's exploration duration."""
    remaining = max(0, int(getattr(character, "_vision_steps", 0) or 0) - steps)
    character._vision_steps = remaining
    if remaining == 0 and int(getattr(character, "_vision_turns", 0) or 0) <= 0:
        character.sight = False


class Healer(Job):
    """
    Promotion: Healer -> Cleric -> Templar
                      |
                      -> Priest -> Archbishop
                      |
                      -> Monk   -> Master Monk
                      |
                      -> Bard   -> Troubadour

    """

    def __init__(self):
        super().__init__(
            name="Healer",
            description="Healers primary role in battle is to preserve the party with "
            "healing and protective spells. Well, how does that work when "
            "they are alone? Pretty much the same way!",
            str_plus=0,
            int_plus=1,
            wis_plus=2,
            con_plus=1,
            cha_plus=1,
            dex_plus=0,
            att_plus=1,
            def_plus=1,
            magic_plus=2,
            magic_def_plus=2,
            equipment={
                "Weapon": items.Quarterstaff(),
                "OffHand": items.NoOffHand(),
                "Armor": items.PaddedArmor(),
            },
            restrictions={
                "Weapon": ["Club", "Staff"],
                "OffHand": ["Shield", "Tome"],
                "Armor": ["Cloth", "Light"],
            },
            pro_level=1,
        )
