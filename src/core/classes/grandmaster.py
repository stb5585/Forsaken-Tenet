"""Grandmaster of Arms weapon discipline helpers."""

from __future__ import annotations

from copy import deepcopy
from typing import Any

from src.core.randomness import gameplay_random as random

from .base import Job

WEAPON_TYPES = (
    "Fist",
    "Dagger",
    "Sword",
    "Club",
    "Longsword",
    "Battle Axe",
    "Polearm",
    "Hammer",
)
ONE_HANDED_WEAPONS = {"Fist", "Dagger", "Sword", "Club"}
TWO_HANDED_WEAPONS = {"Longsword", "Battle Axe", "Polearm", "Hammer"}

MAX_RANK = 10
XP_THRESHOLDS = (24, 60, 114, 186, 285, 414, 576, 774, 1008, 1290)
HIT_XP = 1
VICTORY_XP = 3
ART_XP = 2

DISCIPLINE_XP_CHANCES = {
    "hit": 0.30,
    "crit": 0.55,
    "art": 0.75,
    "victory": 0.65,
}
DISCIPLINE_INT_CHANCE_PER_POINT = 0.02
DISCIPLINE_MIN_CHANCE = 0.05
DISCIPLINE_MAX_CHANCE = 0.95

BASE_ACCURACY_PER_RANK = 0.005
BASE_PROC_PER_RANK = 0.01

WEAPON_ARTS = {
    "Fist": "Iron Palm",
    "Dagger": "Hemorrhage",
    "Sword": "Riposte Line",
    "Club": "Low Sweep",
    "Longsword": "Guard Cleaver",
    "Battle Axe": "Reaver's Mark",
    "Polearm": "Brace",
    "Hammer": "Anvil Strike",
}
ART_WEAPON_TYPES = {art: weapon_type for weapon_type, art in WEAPON_ARTS.items()}
WEAPON_ART_UPGRADES = {f"{art_name} 2": art_name for art_name in WEAPON_ARTS.values()}
WEAPON_ART_MASTERIES = {f"{art_name} 3": f"{art_name} 2" for art_name in WEAPON_ARTS.values()}
ART_WEAPON_TYPES.update(
    {
        upgraded_name: ART_WEAPON_TYPES[base_name]
        for upgraded_name, base_name in WEAPON_ART_UPGRADES.items()
    }
)
ART_WEAPON_TYPES.update(
    {
        mastered_name: ART_WEAPON_TYPES[WEAPON_ART_UPGRADES[upgraded_name]]
        for mastered_name, upgraded_name in WEAPON_ART_MASTERIES.items()
    }
)
WEAPON_ART_LEVELS = {
    **{art_name: 1 for art_name in WEAPON_ARTS.values()},
    **{art_name: 2 for art_name in WEAPON_ART_UPGRADES},
    **{art_name: 3 for art_name in WEAPON_ART_MASTERIES},
}
ART_COSTS = {
    "Fist": 6,
    "Dagger": 7,
    "Sword": 7,
    "Club": 7,
    "Longsword": 9,
    "Battle Axe": 9,
    "Polearm": 8,
    "Hammer": 10,
}


class GrandmasterOfArms(Job):
    """
    Promotion: Warrior -> Weapon Master -> GrandMaster of Arms
    Additional Pros: Higher dexterity and constitution gain
    Additional Cons: Lower strength gain
    Special Mechanic: Weapon Specialty - mastered weapon disciplines reveal weapon arts
        and passive bonuses.
    """

    def __init__(self):
        super().__init__(
            name="Grandmaster of Arms",
            description="Grandmasters of Arms are the pinnacle of weapon expertise, "
            "perfecting their chosen weapon style and wielding an adaptable "
            "arsenal with unmatched skill.",
            str_plus=2,
            int_plus=1,
            wis_plus=0,
            con_plus=2,
            cha_plus=0,
            dex_plus=2,
            att_plus=5,
            def_plus=3,
            magic_plus=0,
            magic_def_plus=2,
            restrictions={
                "Weapon": [
                    "Fist",
                    "Dagger",
                    "Sword",
                    "Club",
                    "Longsword",
                    "Battle Axe",
                    "Polearm",
                    "Hammer",
                ],
                # Grandmasters retain an off-hand weapon only after choosing
                # the Weapon Master tree's Dual Wield style.
                "OffHand": [],
                "Armor": ["Light", "Medium"],
            },
            pro_level=3,
        )


def default_state() -> dict[str, Any]:
    return {
        "activated": False,
        "bound_weapon": None,
        "disciplines": {weapon_type: {"xp": 0, "rank": 0} for weapon_type in WEAPON_TYPES},
    }


def rank_for_xp(xp: int) -> int:
    xp = max(0, int(xp or 0))
    rank = 0
    for threshold in XP_THRESHOLDS:
        if xp >= threshold:
            rank += 1
    return min(MAX_RANK, rank)


def normalize_state(state: Any) -> dict[str, Any]:
    normalized = default_state()
    if not isinstance(state, dict):
        return normalized

    normalized["activated"] = bool(state.get("activated", False))
    bound_weapon = state.get("bound_weapon")
    normalized["bound_weapon"] = bound_weapon if bound_weapon in WEAPON_TYPES else None

    disciplines = state.get("disciplines", {})
    if isinstance(disciplines, dict):
        for weapon_type in WEAPON_TYPES:
            entry = disciplines.get(weapon_type, {})
            try:
                xp = int(entry.get("xp", 0) or 0) if isinstance(entry, dict) else 0
            except (TypeError, ValueError):
                xp = 0
            normalized["disciplines"][weapon_type] = {
                "xp": max(0, xp),
                "rank": rank_for_xp(xp),
            }
    return normalized


def copy_state(state: Any) -> dict[str, Any]:
    return deepcopy(normalize_state(state))


def get_weapon_type(character: Any, slot: str = "Weapon") -> str | None:
    equipment = getattr(character, "equipment", {})
    item = equipment.get(slot) if isinstance(equipment, dict) else None
    weapon_type = getattr(item, "subtyp", None)
    return weapon_type if weapon_type in WEAPON_TYPES else None


def is_grandmaster(character: Any) -> bool:
    return getattr(getattr(character, "cls", None), "name", None) == "Grandmaster of Arms"


def is_weapon_discipline_class(character: Any) -> bool:
    return getattr(getattr(character, "cls", None), "name", None) in {
        "Weapon Master",
        "Berserker",
        "Grandmaster of Arms",
    }


def weapon_discipline_types(character: Any) -> tuple[str, ...]:
    """Return weapon disciplines visible to the current class."""
    if getattr(getattr(character, "cls", None), "name", None) == "Berserker":
        return tuple(
            weapon_type for weapon_type in WEAPON_TYPES if weapon_type in TWO_HANDED_WEAPONS
        )
    return WEAPON_TYPES


def has_equipped_class_ring(character: Any) -> bool:
    equipment = getattr(character, "equipment", {})
    ring = equipment.get("Ring") if isinstance(equipment, dict) else None
    return getattr(ring, "name", None) == "Class Ring"


def has_stored_class_ring(character: Any) -> bool:
    storage = getattr(character, "storage", {})
    if not isinstance(storage, dict):
        return False
    return any(
        getattr(item, "name", None) == "Class Ring" for item in storage.get("Class Ring", [])
    )


def ring_visible_for_sergeant(character: Any) -> bool:
    return has_equipped_class_ring(character) or has_stored_class_ring(character)


def discipline_rank(character: Any, weapon_type: str | None) -> int:
    if weapon_type not in WEAPON_TYPES:
        return 0
    state = normalize_state(getattr(character, "grandmaster_discipline", None))
    return int(state["disciplines"][weapon_type]["rank"])


def format_xp_value(value: float) -> str:
    value = max(0.0, float(value or 0))
    if value.is_integer():
        return str(int(value))
    return f"{value:.2f}".rstrip("0").rstrip(".")


def discipline_difficulty_factor(opponent: Any) -> float:
    if opponent is None:
        return 1.0
    level = getattr(opponent, "level", None)
    try:
        pro_level = float(getattr(level, "pro_level", 0) or 0)
    except (TypeError, ValueError):
        pro_level = 0.0
    return max(0.0, pro_level / 2.0)


def discipline_xp_chance(character: Any, opponent: Any = None, *, reason: str = "hit") -> float:
    difficulty = discipline_difficulty_factor(opponent)
    if difficulty <= 0:
        return 0.0
    base_chance = DISCIPLINE_XP_CHANCES.get(reason, DISCIPLINE_XP_CHANCES["hit"])
    stats = getattr(character, "stats", None)
    try:
        intel = int(getattr(stats, "intel", 10) or 10)
    except (TypeError, ValueError):
        intel = 10
    chance = (base_chance + ((intel - 10) * DISCIPLINE_INT_CHANCE_PER_POINT)) * difficulty
    return max(DISCIPLINE_MIN_CHANCE, min(DISCIPLINE_MAX_CHANCE, chance))


def add_discipline_xp(character: Any, weapon_type: str | None, amount: int) -> tuple[int, int]:
    if weapon_type not in WEAPON_TYPES or amount <= 0 or not is_weapon_discipline_class(character):
        return 0, 0
    state = normalize_state(getattr(character, "grandmaster_discipline", None))
    entry = state["disciplines"][weapon_type]
    before = int(entry["rank"])
    entry["xp"] = max(0, int(entry["xp"]) + int(amount))
    entry["rank"] = rank_for_xp(entry["xp"])
    setattr(character, "grandmaster_discipline", state)
    sync_weapon_art_skills(character)
    return before, int(entry["rank"])


def roll_discipline_xp(
    character: Any,
    weapon_type: str | None,
    amount: int,
    opponent: Any = None,
    *,
    reason: str = "hit",
    rng=random,
) -> tuple[int, int, int]:
    if weapon_type not in WEAPON_TYPES or amount <= 0 or not is_weapon_discipline_class(character):
        return 0, 0, 0
    chance = discipline_xp_chance(character, opponent, reason=reason)
    if chance <= 0 or rng.random() >= chance:
        current_rank = discipline_rank(character, weapon_type)
        return current_rank, current_rank, 0
    before, after = add_discipline_xp(character, weapon_type, int(amount))
    return before, after, int(amount)


def xp_label(character: Any, weapon_type: str | None) -> str:
    if weapon_type not in WEAPON_TYPES:
        return "0/0 XP"
    state = normalize_state(getattr(character, "grandmaster_discipline", None))
    entry = state["disciplines"][weapon_type]
    xp = max(0, int(entry.get("xp", 0) or 0))
    rank = max(0, int(entry.get("rank", 0) or 0))
    if rank >= MAX_RANK:
        return "MAX"
    return f"{format_xp_value(xp)}/{XP_THRESHOLDS[rank]} XP"


def discipline_xp_text(
    character: Any,
    weapon_type: str | None,
    amount: int,
    before_rank: int,
    after_rank: int,
) -> str:
    if weapon_type not in WEAPON_TYPES or amount <= 0:
        return ""
    text = f"{weapon_type} Discipline +{format_xp_value(amount)} XP.\n"
    if after_rank > before_rank:
        text += f"{weapon_type} Discipline reached rank {after_rank}.\n"
        art_name = WEAPON_ARTS.get(weapon_type)
        if art_name and before_rank < 1 <= after_rank:
            text += f"{art_name} is now available in the Weapon Master ability tree.\n"
        if art_name and before_rank < 5 <= after_rank:
            text += f"{art_name} 2 is now available in the Weapon Master ability tree.\n"
        if art_name and before_rank < 10 <= after_rank:
            text += f"{art_name} 3 is now available in the Grandmaster of Arms " "ability tree.\n"
    return text


def bind_weapon(character: Any, weapon_type: str) -> bool:
    if weapon_type not in WEAPON_TYPES:
        return False
    state = normalize_state(getattr(character, "grandmaster_discipline", None))
    state["activated"] = True
    state["bound_weapon"] = weapon_type
    setattr(character, "grandmaster_discipline", state)
    return True


def bound_multiplier(character: Any, weapon_type: str | None) -> int:
    state = normalize_state(getattr(character, "grandmaster_discipline", None))
    if (
        weapon_type in WEAPON_TYPES
        and state["activated"]
        and state["bound_weapon"] == weapon_type
        and has_equipped_class_ring(character)
    ):
        return 2
    return 1


def accuracy_bonus(character: Any, weapon_type: str | None) -> float:
    if not is_weapon_discipline_class(character):
        return 0.0
    rank = discipline_rank(character, weapon_type)
    return rank * BASE_ACCURACY_PER_RANK * bound_multiplier(character, weapon_type)


def proc_chance(character: Any, weapon_type: str | None) -> float:
    if not is_weapon_discipline_class(character):
        return 0.0
    rank = discipline_rank(character, weapon_type)
    return rank * BASE_PROC_PER_RANK * bound_multiplier(character, weapon_type)


def _has_skill(character: Any, skill_name: str) -> bool:
    skills = getattr(character, "spellbook", {}).get("Skills", {})
    return isinstance(skills, dict) and skill_name in skills


def two_handed_accuracy_bonus(character: Any, slot: str) -> float:
    """Return the passive accuracy bonus for a two-handed weapon attack."""
    weapon_type = get_weapon_type(character, slot)
    if weapon_type in TWO_HANDED_WEAPONS and _has_skill(character, "Two-Handed Weapon Proficiency"):
        return 0.10
    return 0.0


def two_handed_damage_multiplier(character: Any, slot: str) -> float:
    """Return the passive damage multiplier for a two-handed weapon attack."""
    weapon_type = get_weapon_type(character, slot)
    if weapon_type in TWO_HANDED_WEAPONS and _has_skill(character, "Two-Handed Weapon Proficiency"):
        return 1.10
    return 1.0


def brutish_critical_multiplier(
    character: Any,
    weapon_type: str | None,
    multiplier: float,
) -> float:
    """Increase critical bonus damage by five percent per discipline rank."""
    if multiplier <= 1 or not _has_skill(character, "Brutish Strength"):
        return multiplier
    rank = discipline_rank(character, weapon_type)
    return 1 + ((multiplier - 1) * (1 + (0.05 * rank)))


def _has_talent(character: Any, talent_key: str) -> bool:
    try:
        from ..progression import has_talent

        return has_talent(character, talent_key)
    except (ImportError, AttributeError):
        return False


def perfect_form_accuracy_bonus(
    character: Any,
    weapon_type: str | None,
) -> float:
    """Grant 0.5 percent hit chance per equipped discipline rank."""
    if not _has_talent(character, "grandmaster.perfect-form"):
        return 0.0
    return discipline_rank(character, weapon_type) * 0.005


def perfect_form_damage_multiplier(
    character: Any,
    weapon_type: str | None,
) -> float:
    """Grant one percent weapon damage per equipped discipline rank."""
    if not _has_talent(character, "grandmaster.perfect-form"):
        return 1.0
    return 1.0 + (discipline_rank(character, weapon_type) * 0.01)


def adaptive_arsenal_parry_bonus(character: Any) -> float:
    """Grant 0.5 percent parry chance per main-hand discipline rank."""
    if not _has_talent(character, "grandmaster.adaptive-arsenal"):
        return 0.0
    return discipline_rank(character, get_weapon_type(character)) * 0.005


def adaptive_arsenal_counter_crit_chance(character: Any) -> float:
    """Grant one percent counterattack critical chance per discipline rank."""
    if not _has_talent(character, "grandmaster.adaptive-arsenal"):
        return 0.0
    return discipline_rank(character, get_weapon_type(character)) * 0.01


def should_proc(character: Any, weapon_type: str | None) -> bool:
    chance = proc_chance(character, weapon_type)
    return chance > 0 and random.random() < chance


def art_rank(character: Any, art_name: str) -> int:
    return discipline_rank(character, ART_WEAPON_TYPES.get(art_name))


def art_unlocked(character: Any, art_name: str) -> bool:
    required_rank = {
        1: 1,
        2: 5,
        3: 10,
    }.get(WEAPON_ART_LEVELS.get(art_name, 1), 1)
    return art_rank(character, art_name) >= required_rank


def perfect_bound_art(character: Any, weapon_type: str | None) -> bool:
    state = normalize_state(getattr(character, "grandmaster_discipline", None))
    return bool(
        is_grandmaster(character)
        and weapon_type in WEAPON_TYPES
        and state["activated"]
        and state["bound_weapon"] == weapon_type
        and has_equipped_class_ring(character)
    )


def sync_weapon_art_skills(character: Any) -> list[str]:
    """Remove legacy auto-granted arts; tree purchases now own acquisition."""
    if not is_weapon_discipline_class(character):
        return []
    spellbook = getattr(character, "spellbook", None)
    if not isinstance(spellbook, dict):
        return []
    skills = spellbook.setdefault("Skills", {})
    if not isinstance(skills, dict):
        return []
    purchased = getattr(getattr(character, "progression", None), "purchased_node_ids", set())
    for art_name in (
        *WEAPON_ARTS.values(),
        *WEAPON_ART_UPGRADES,
        *WEAPON_ART_MASTERIES,
    ):
        node_suffix = ".ability." + art_name.lower().replace("'", "").replace(" ", "-")
        if not any(node_id.endswith(node_suffix) for node_id in purchased):
            skills.pop(art_name, None)
    return []


def _matching_weapon_equipped(character: Any, weapon_type: str) -> bool:
    return (
        get_weapon_type(character, "Weapon") == weapon_type
        or get_weapon_type(character, "OffHand") == weapon_type
    )


def matching_weapon_for_art_equipped(character: Any, art_name: str) -> bool:
    """Return whether a known weapon art has its matching weapon equipped."""
    weapon_type = ART_WEAPON_TYPES.get(art_name)
    return weapon_type is not None and _matching_weapon_equipped(character, weapon_type)


def _set_status(effect: Any, *, duration: int, extra: int) -> None:
    effect.active = True
    effect.duration = max(int(getattr(effect, "duration", 0) or 0), duration)
    effect.extra = extra


def perform_weapon_art(character: Any, target: Any, art_name: str) -> str:
    weapon_type = ART_WEAPON_TYPES.get(art_name)
    rank = discipline_rank(character, weapon_type)
    art_level = WEAPON_ART_LEVELS.get(art_name, 1)
    required_rank = {1: 1, 2: 5, 3: 10}[art_level]
    if weapon_type not in WEAPON_TYPES or rank < required_rank:
        if weapon_type in WEAPON_TYPES and art_level > 1:
            return f"{art_name} requires {weapon_type} specialization level " f"{required_rank}.\n"
        return f"{character.name} has not learned {art_name}.\n"
    if not _matching_weapon_equipped(character, weapon_type):
        return f"{art_name} requires an equipped {weapon_type}.\n"
    cost = ART_COSTS[weapon_type] + (2 * (art_level - 1))
    if getattr(character.mana, "current", 0) < cost:
        return f"{character.name} does not have enough mana to use {art_name}.\n"

    from . import berserker

    momentum, momentum_msg = berserker.prepare_heavy_art_payoff(
        character,
        art_name,
    )
    character.mana.current -= cost

    mastered = rank >= 10
    improved = rank >= 5
    perfect = perfect_bound_art(character, weapon_type)
    msg, hit, crit = character.weapon_damage(
        target,
        dmg_mod=_art_damage_mod(weapon_type, rank, perfect)
        + (0.15 * (art_level - 1))
        + momentum.damage_bonus,
        crit=2 if (weapon_type in {"Sword", "Battle Axe"} and mastered) else 1,
        ignore=weapon_type in {"Longsword", "Hammer"} and improved,
        cover=False,
        use_offhand=False,
        accuracy_modifier=momentum.accuracy_bonus,
    )
    msg = momentum_msg + msg
    if not hit:
        return msg + berserker.resolve_heavy_art_payoff(
            character,
            momentum,
            hit=False,
        )

    msg += _apply_art_effect(
        character,
        target,
        weapon_type,
        rank,
        crit,
        perfect,
        momentum=momentum,
    )
    msg += berserker.resolve_heavy_art_payoff(
        character,
        momentum,
        hit=True,
    )
    if hasattr(character, "record_grandmaster_weapon_art"):
        before, after, amount = character.record_grandmaster_weapon_art(weapon_type, target)
        msg += discipline_xp_text(character, weapon_type, amount, before, after)
    return msg


def _art_damage_mod(weapon_type: str, rank: int, perfect: bool) -> float:
    base = {
        "Fist": 0.90,
        "Dagger": 0.85,
        "Sword": 0.95,
        "Club": 0.85,
        "Longsword": 1.05,
        "Battle Axe": 1.00,
        "Polearm": 0.75,
        "Hammer": 1.10,
    }.get(weapon_type, 1.0)
    if rank >= 5:
        base += 0.05
    if rank >= 10:
        base += 0.05
    if perfect:
        base += 0.05
    return base


def _apply_art_effect(
    character: Any,
    target: Any,
    weapon_type: str,
    rank: int,
    crit: int,
    perfect: bool,
    *,
    momentum: Any | None = None,
) -> str:
    improved = rank >= 5
    mastered = rank >= 10
    momentum_stacks = max(0, int(getattr(momentum, "stacks", 0) or 0))
    crush_bonus = max(0, int(getattr(momentum, "crush_bonus", 0) or 0))
    rider_bonus = momentum_stacks * max(
        0.0,
        float(getattr(momentum, "rider_per_stack", 0.0) or 0.0),
    )
    msg = ""
    if weapon_type == "Fist":
        penalty = -3 - (2 if improved else 0) - (1 if perfect else 0)
        _set_status(target.stat_effects["Attack"], duration=3, extra=penalty)
        msg += f"{target.name}'s attack is disrupted by Iron Palm.\n"
        if improved and random.random() < (0.20 + (0.10 if mastered else 0.0)):
            if target.apply_stun(1, source="Iron Palm", applier=character):
                msg += f"{target.name} reels from the palm strike.\n"
        if mastered:
            _set_status(
                character.stat_effects["Defense"], duration=2, extra=4 + (2 if perfect else 0)
            )
            msg += f"{character.name}'s stance hardens after Iron Palm.\n"
    elif weapon_type == "Dagger":
        bleed = max(2, character.stats.dex // 5) + (2 if improved else 0) + (2 if mastered else 0)
        if target.physical_effects["Bleed"].active and improved:
            bleed += max(1, int(target.physical_effects["Bleed"].extra or 0) // 2)
        _set_status(
            target.physical_effects["Bleed"],
            duration=3 + int(mastered),
            extra=bleed + (1 if perfect else 0),
        )
        msg += f"Hemorrhage opens a bleeding wound on {target.name}.\n"
        if mastered and not target.is_alive():
            refund = max(1, ART_COSTS["Dagger"] // 2)
            character.mana.current = min(character.mana.max, character.mana.current + refund)
            msg += f"{character.name} recovers {refund} mana from the finishing cut.\n"
    elif weapon_type == "Sword":
        character._riposte_line = {
            "turns": 2,
            "multiplier": 0.45 + (0.15 if improved else 0.0) + (0.10 if perfect else 0.0),
            "crit": 2 if mastered else 1,
        }
        msg += f"{character.name} settles into a riposte line.\n"
    elif weapon_type == "Club":
        speed = -3 - (2 if improved else 0) - (1 if perfect else 0)
        _set_status(target.stat_effects["Speed"], duration=3, extra=speed)
        prone_chance = 0.25 + (0.20 if improved else 0.0) + (0.10 if mastered else 0.0)
        if random.random() < prone_chance and not getattr(target, "flying", False):
            target.physical_effects["Prone"].active = True
            target.physical_effects["Prone"].duration = max(
                1 + int(mastered), target.physical_effects["Prone"].duration
            )
            msg += f"{target.name} is swept low and knocked prone.\n"
        else:
            msg += f"Low Sweep slows {target.name}'s footing.\n"
    elif weapon_type == "Longsword":
        defense = -5 - (3 if improved else 0) - (2 if perfect else 0) - crush_bonus
        _set_status(target.stat_effects["Defense"], duration=3 + int(mastered), extra=defense)
        msg += f"Guard Cleaver breaks {target.name}'s guard.\n"
    elif weapon_type == "Battle Axe":
        target._reavers_mark = {
            "turns": 3 + int(mastered),
            "bonus": (
                0.10 + (0.05 if improved else 0.0) + (0.05 if perfect else 0.0) + rider_bonus
            ),
        }
        msg += f"{target.name} is marked by Reaver's Mark.\n"
        if improved:
            _set_status(target.stat_effects["Defense"], duration=2, extra=-3)
        if mastered and not target.is_alive():
            _set_status(
                character.stat_effects["Attack"], duration=2, extra=5 + (2 if perfect else 0)
            )
            msg += f"{character.name} surges after reaving the marked foe.\n"
    elif weapon_type == "Polearm":
        character._brace_art = {
            "turns": 2,
            "reduction": (
                0.20
                + (0.10 if improved else 0.0)
                + (0.10 if mastered else 0.0)
                + (0.05 if perfect else 0.0)
                + rider_bonus
            ),
            "counter": 0.45 + (0.10 if improved else 0.0) + rider_bonus,
        }
        _set_status(character.stat_effects["Defense"], duration=2, extra=3 + (2 if mastered else 0))
        msg += f"{character.name} braces behind the polearm.\n"
    elif weapon_type == "Hammer":
        defense = -6 - (3 if improved else 0) - (2 if perfect else 0) - crush_bonus
        _set_status(target.stat_effects["Defense"], duration=3, extra=defense)
        if mastered:
            target._guard_suppressed = 2
        msg += f"Anvil Strike crushes {target.name}'s defenses.\n"
    if momentum_stacks and weapon_type in TWO_HANDED_WEAPONS:
        msg += (
            f"Bloodied Momentum mutates the art with {momentum_stacks} stack(s) "
            "of added pressure.\n"
        )
    return msg


def _stack_entry(target: Any, key: str) -> dict[str, int]:
    stacks = getattr(target, "grandmaster_technique_stacks", None)
    if not isinstance(stacks, dict):
        stacks = {}
        setattr(target, "grandmaster_technique_stacks", stacks)
    entry = stacks.setdefault(key, {"stacks": 0, "duration": 0})
    entry["stacks"] = min(3, int(entry.get("stacks", 0) or 0) + 1)
    entry["duration"] = 3
    return entry


def apply_weapon_technique(attacker: Any, defender: Any, weapon_type: str | None) -> str:
    if weapon_type not in WEAPON_TYPES or not should_proc(attacker, weapon_type):
        return ""

    if weapon_type == "Fist":
        entry = _stack_entry(defender, "Fist Stagger")
        effect = defender.stat_effects["Attack"]
        effect.active = True
        effect.duration = 3
        effect.extra = -2 * entry["stacks"]
        return f"{attacker.name}'s fist technique staggers {defender.name}.\n"

    if weapon_type == "Dagger":
        entry = _stack_entry(defender, "Dagger Expose")
        effect = defender.physical_effects["Bleed"]
        effect.active = True
        effect.duration = 3
        effect.extra = max(
            int(effect.extra or 0), max(1, attacker.stats.dex // 4) * entry["stacks"]
        )
        return f"{attacker.name}'s dagger exposes {defender.name}'s guard.\n"

    if weapon_type == "Sword":
        entry = _stack_entry(attacker, "Sword Precision")
        return f"{attacker.name}'s sword form sharpens into precision ({entry['stacks']}).\n"

    if weapon_type == "Club":
        entry = _stack_entry(defender, "Club Daze")
        effect = defender.stat_effects["Speed"]
        effect.active = True
        effect.duration = 3
        effect.extra = -2 * entry["stacks"]
        return f"{attacker.name}'s club strike dazes {defender.name}.\n"

    if weapon_type == "Longsword":
        effect = defender.stat_effects["Defense"]
        effect.active = True
        effect.duration = 3
        effect.extra = min(int(effect.extra or 0), -5)
        return f"{attacker.name}'s longsword breaks {defender.name}'s guard.\n"

    if weapon_type == "Battle Axe":
        effect = defender.physical_effects["Bleed"]
        effect.active = True
        effect.duration = 3
        effect.extra = max(int(effect.extra or 0), max(2, attacker.stats.strength // 3))
        return f"{attacker.name}'s axe rends {defender.name}.\n"

    if weapon_type == "Polearm":
        if getattr(defender, "flying", False):
            return f"{defender.name} stays beyond the trip.\n"
        effect = defender.physical_effects["Prone"]
        effect.active = True
        effect.duration = max(2, int(effect.duration or 0))
        return f"{attacker.name}'s polearm trips {defender.name}.\n"

    if weapon_type == "Hammer":
        effect = defender.stat_effects["Defense"]
        effect.active = True
        effect.duration = 3
        effect.extra = min(int(effect.extra or 0), -8)
        return f"{attacker.name}'s hammer sunders {defender.name}'s defenses.\n"

    return ""


def tick_technique_stacks(character: Any) -> list[str]:
    stacks = getattr(character, "grandmaster_technique_stacks", None)
    if not isinstance(stacks, dict) or not stacks:
        return []
    expired = []
    for key, entry in list(stacks.items()):
        entry["duration"] = int(entry.get("duration", 0) or 0) - 1
        if entry["duration"] <= 0:
            expired.append(key)
            del stacks[key]
    return expired
