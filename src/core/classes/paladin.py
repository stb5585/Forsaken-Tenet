"""Paladin class definition."""

from __future__ import annotations

import copy
import math
import random
from typing import Any

from .base import Job


class Paladin(Job):
    """
    Promotion: Warrior -> Paladin -> Crusader
    Pros: Can cast healing spells; additional wisdom and charisma gain
    Cons: Cannot equip 2-handed weapons except hammers and cannot equip light armor; no dex
        and lower strength gain
    Special Mechanic: Oath Conviction - swear a path and build conviction through
        path-aligned combat actions.
    """

    def __init__(self):
        super().__init__(
            name="Paladin",
            description="The Paladin is a holy knight, crusading in the name of good and "
            "order. Gaining some healing and damage spells, paladins become a"
            " more balanced class and are ideal for players who always forget"
            " to restock health potions.",
            str_plus=1,
            int_plus=0,
            wis_plus=2,
            con_plus=2,
            cha_plus=1,
            dex_plus=0,
            att_plus=2,
            def_plus=2,
            magic_plus=2,
            magic_def_plus=2,
            restrictions={
                "Weapon": ["Sword", "Club", "Longsword", "Hammer"],
                "OffHand": ["Shield"],
                "Armor": ["Medium", "Heavy"],
            },
            pro_level=2,
        )


PATHS = ("Redemption", "Conquest", "Protection", "Retribution")

SKILL_NAMES = {
    "Redemption": "Redeem",
    "Conquest": "Challenge",
    "Protection": "Interpose",
    "Retribution": "Judgment Riposte",
}

SKILL_CLASS_NAMES = {
    "Redemption": "Redeem",
    "Conquest": "Challenge",
    "Protection": "Interpose",
    "Retribution": "JudgmentRiposte",
}

DESCRIPTIONS = {
    "Redemption": (
        "Redeem offers wounded foes a chance to yield. Mercy can still be "
        "rewarding, especially when your oath is burning bright, but it turns "
        "away from trophies and bloody renown."
    ),
    "Conquest": (
        "Challenge names a foe and presses the fight toward a decisive end. "
        "Victories against chosen or hunted enemies feed your commanding aura."
    ),
    "Protection": (
        "Interpose commits you to a guarded stand. Timely blocks turn defense "
        "into protective momentum for the battles ahead."
    ),
    "Retribution": (
        "Judgment Riposte waits for enemy aggression and answers it with holy "
        "reprisal. Clean vengeance can leave your aura burning brighter."
    ),
}

AURA_NAMES = {
    "Redemption": "Redemption Aura",
    "Conquest": "Conquest Aura",
    "Protection": "Protection Aura",
    "Retribution": "Retribution Aura",
}

MARK_NAMES = {
    "Redemption": "Mark of Perdition",
    "Conquest": "Mark of the Craven",
    "Protection": "Mark of Vulnerability",
    "Retribution": "Mark of Mercy",
}

SIGNATURE_DESCRIPTIONS = {
    "Redemption": (
        "Using Redeem on an eligible wounded foe grants 1 Conviction even if "
        "the foe refuses. A successful surrender grants 1 additional stack."
    ),
    "Conquest": (
        "Naming an eligible foe with Challenge grants 1 Conviction immediately. "
        "Defeating a challenged or bounty foe grants 1 additional stack."
    ),
    "Protection": (
        "Entering Interpose grants 1 Conviction immediately and prepares a "
        "two-turn guarded stance with +35 percentage points to block chance "
        "and mitigation. A guarded block grants 1 additional stack."
    ),
    "Retribution": (
        "Preparing Judgment Riposte grants 1 Conviction immediately. If its "
        "two-turn holy counter triggers, it grants 1 additional stack."
    ),
}

AURA_DESCRIPTIONS = {
    "Redemption": (
        "Successful mercy grants this Aura for three encounters: +20% "
        "redemption rewards, +10 percentage points to Redeem chance, and 25% "
        "fewer encounters."
    ),
    "Conquest": (
        "Defeating a challenged or bounty foe grants a three-encounter Aura, "
        "stacking to three: +5% damage and initiative per stack."
    ),
    "Protection": (
        "A successful block grants a two-turn Aura, stacking to five: "
        "+3 percentage points block chance and +5 mitigation per stack."
    ),
    "Retribution": (
        "A successful riposte grants a three-encounter Aura: +10% dodge and "
        "+15% critical damage. A killing riposte doubles its duration."
    ),
}

MARK_DESCRIPTIONS = {
    "Redemption": (
        "Killing instead of showing mercy applies this Mark for three "
        "encounters: -20% redemption rewards and 25% more encounters."
    ),
    "Conquest": (
        "Fleeing applies this Mark: -10% damage and loss of initiative until it is "
        "cleared by defeating a bounty foe."
    ),
    "Protection": (
        "Being incapacitated applies this Mark: +20% incoming physical damage " "until recovery."
    ),
    "Retribution": (
        "Being unable to answer with a weapon applies this Mark. At or below "
        "10% HP, incoming damage becomes lethal until a weapon is restored."
    ),
}


def vow_selection_summary(vow_path: Any) -> str:
    """Describe a vow's learned action, Aura, and Mark for confirmation UIs."""
    selected = normalize_path(vow_path)
    if not selected:
        return ""
    return " ".join(
        (
            DESCRIPTIONS[selected],
            f"Learned ability — {SKILL_NAMES[selected]}: " f"{SIGNATURE_DESCRIPTIONS[selected]}",
            f"{AURA_NAMES[selected]}: {AURA_DESCRIPTIONS[selected]}",
            f"{MARK_NAMES[selected]}: {MARK_DESCRIPTIONS[selected]}",
        )
    )


def default_state() -> dict[str, Any]:
    return {
        "path": None,
        "aura": {
            "name": None,
            "turns": 0,
            "encounters": 0,
            "stacks": 0,
            "doubled": False,
        },
        "mark": {
            "name": None,
            "turns": 0,
            "encounters": 0,
            "active": False,
            "data": {},
        },
        "challenge": {"target_id": None, "turns": 0},
        "interpose": {"turns": 0, "spent": False},
        "riposte": {"turns": 0, "spent": False},
    }


def normalize_path(vow_path: Any) -> str | None:
    if isinstance(vow_path, dict):
        vow_path = vow_path.get("path")
    if vow_path is None:
        return None
    text = str(vow_path).strip().lower()
    for candidate in PATHS:
        if text == candidate.lower():
            return candidate
    return None


def normalize_state(state: Any) -> dict[str, Any]:
    normalized = default_state()
    if isinstance(state, str):
        normalized["path"] = normalize_path(state)
        return normalized
    if not isinstance(state, dict):
        return normalized

    normalized["path"] = normalize_path(state.get("path"))
    for key in ("aura", "mark", "challenge", "interpose", "riposte"):
        incoming = state.get(key, {})
        if isinstance(incoming, dict):
            normalized[key].update(copy.deepcopy(incoming))

    aura = normalized["aura"]
    aura["name"] = str(aura["name"]) if aura.get("name") else None
    aura["turns"] = max(0, int(aura.get("turns", 0) or 0))
    aura["encounters"] = max(0, int(aura.get("encounters", 0) or 0))
    aura["stacks"] = max(0, int(aura.get("stacks", 0) or 0))
    aura["doubled"] = bool(aura.get("doubled", False))

    mark = normalized["mark"]
    mark["name"] = str(mark["name"]) if mark.get("name") else None
    mark["turns"] = max(0, int(mark.get("turns", 0) or 0))
    mark["encounters"] = max(0, int(mark.get("encounters", 0) or 0))
    mark["active"] = bool(mark.get("active", False))
    mark["data"] = mark.get("data") if isinstance(mark.get("data"), dict) else {}

    for key in ("challenge", "interpose", "riposte"):
        data = normalized[key]
        data["turns"] = max(0, int(data.get("turns", 0) or 0))
    normalized["interpose"]["spent"] = bool(normalized["interpose"].get("spent", False))
    normalized["riposte"]["spent"] = bool(normalized["riposte"].get("spent", False))
    return normalized


def ensure_state(character: Any) -> dict[str, Any]:
    state = normalize_state(getattr(character, "paladin_vow", None))
    setattr(character, "paladin_vow", state)
    if state["path"] is None:
        combat = getattr(character, "_promotion_kit_combat", None)
        if isinstance(combat, dict):
            combat["oath_conviction"] = 0
            combat["oath_judgment_counter"] = None
            combat["oath_protection_guard"] = None
            combat["oath_retribution_shelter"] = None
    return state


def path(character: Any) -> str | None:
    return ensure_state(character).get("path")


def is_paladin_lineage(character: Any) -> bool:
    return getattr(getattr(character, "cls", None), "name", None) in {"Paladin", "Crusader"}


def choose_vow(character: Any, vow_path: Any) -> tuple[bool, str]:
    state = ensure_state(character)
    selected = normalize_path(vow_path)
    if not selected:
        return False, "That vow path is not recognized.\n"
    existing = normalize_path(state.get("path"))
    if existing and existing != selected:
        return False, f"The Vow of {existing} is already sworn.\n"

    state["path"] = selected
    grant_signature_skill(character, selected)
    return True, f"You swear the Vow of {selected} and learn {SKILL_NAMES[selected]}.\n"


def grant_signature_skill(character: Any, vow_path: Any | None = None) -> bool:
    selected = normalize_path(vow_path) or path(character)
    if not selected:
        return False
    try:
        from src.core import abilities

        cls = getattr(abilities, SKILL_CLASS_NAMES[selected])
        skill = cls()
        character.spellbook.setdefault("Skills", {})[skill.name] = skill
        return True
    except Exception:
        return False


def has_affirmation(character: Any) -> bool:
    try:
        from . import class_rings

        return class_rings.is_awakened(
            character, "Crusader"
        ) and class_rings.has_equipped_class_ring(character)
    except Exception:
        return False


def aura_multiplier(character: Any) -> float:
    return 1.5 if has_affirmation(character) else 1.0


def mark_multiplier(character: Any) -> float:
    return 0.5 if has_affirmation(character) else 1.0


def adjusted_mark_duration(character: Any, base: int) -> int:
    return max(1, int(round(base * mark_multiplier(character))))


def clear_aura(character: Any) -> None:
    state = ensure_state(character)
    state["aura"] = default_state()["aura"]


def clear_mark(character: Any) -> None:
    state = ensure_state(character)
    state["mark"] = default_state()["mark"]


def trigger_aura(character: Any, vow_path: Any | None = None, doubled: bool = False) -> str:
    selected = normalize_path(vow_path) or path(character)
    if not selected:
        return ""
    state = ensure_state(character)
    aura = state["aura"]
    aura["name"] = AURA_NAMES[selected]
    aura["doubled"] = bool(doubled)
    if selected == "Protection":
        aura["turns"] = 2
        aura["encounters"] = 0
        aura["stacks"] = min(5, max(1, int(aura.get("stacks", 0) or 0) + 1))
    elif selected == "Conquest":
        aura["turns"] = 0
        aura["encounters"] = 3
        aura["stacks"] = min(3, max(1, int(aura.get("stacks", 0) or 0) + 1))
    elif selected == "Retribution":
        aura["turns"] = 0
        aura["encounters"] = 6 if doubled else 3
        aura["stacks"] = 1
    else:
        aura["turns"] = 0
        aura["encounters"] = 3
        aura["stacks"] = 1
    return f"{AURA_NAMES[selected]} answers your vow.\n"


def apply_mark(character: Any, vow_path: Any | None = None) -> str:
    selected = normalize_path(vow_path) or path(character)
    if not selected:
        return ""
    state = ensure_state(character)
    mark = state["mark"]
    mark["name"] = MARK_NAMES[selected]
    mark["active"] = True
    mark["data"] = {}
    if selected == "Redemption":
        mark["encounters"] = adjusted_mark_duration(character, 3)
        mark["turns"] = 0
    elif selected == "Protection":
        mark["encounters"] = 0
        mark["turns"] = 1
    else:
        mark["encounters"] = 0
        mark["turns"] = 0
    return f"{MARK_NAMES[selected]} settles on you.\n"


def tick_turn(character: Any) -> None:
    state = ensure_state(character)
    for key in ("challenge", "interpose", "riposte"):
        state[key]["turns"] = max(0, int(state[key].get("turns", 0) or 0) - 1)
        if not state[key]["turns"] and key in {"interpose", "riposte"}:
            state[key]["spent"] = False
    aura = state["aura"]
    if aura.get("turns"):
        aura["turns"] = max(0, int(aura.get("turns", 0) or 0) - 1)
        if aura["turns"] <= 0:
            clear_aura(character)
    mark = state["mark"]
    if mark.get("turns"):
        mark["turns"] = max(0, int(mark.get("turns", 0) or 0) - 1)
        if mark["turns"] <= 0:
            clear_mark(character)


def advance_encounter(character: Any) -> None:
    state = ensure_state(character)
    aura = state["aura"]
    if aura.get("encounters"):
        aura["encounters"] = max(0, int(aura.get("encounters", 0) or 0) - 1)
        if aura["encounters"] <= 0:
            clear_aura(character)
    mark = state["mark"]
    if mark.get("encounters"):
        mark["encounters"] = max(0, int(mark.get("encounters", 0) or 0) - 1)
        if mark["encounters"] <= 0:
            clear_mark(character)


def aura_active(character: Any, aura_name: str) -> bool:
    aura = ensure_state(character)["aura"]
    if aura.get("name") != aura_name:
        return False
    return bool(aura.get("stacks", 0) or aura.get("turns", 0) or aura.get("encounters", 0))


def mark_active(character: Any, mark_name: str) -> bool:
    mark = ensure_state(character)["mark"]
    return bool(mark.get("active") and mark.get("name") == mark_name)


def redemption_reward_multiplier(character: Any) -> float:
    multiplier = 1.0
    if aura_active(character, "Redemption Aura"):
        multiplier += 0.20 * aura_multiplier(character)
    if mark_active(character, "Mark of Perdition"):
        multiplier -= 0.20 * mark_multiplier(character)
    return max(0.0, multiplier)


def encounter_rate_multiplier(character: Any) -> float:
    multiplier = 1.0
    if aura_active(character, "Redemption Aura"):
        multiplier -= 0.25 * aura_multiplier(character)
    if mark_active(character, "Mark of Perdition"):
        multiplier += 0.25 * mark_multiplier(character)
    return max(0.05, multiplier)


def conquest_damage_multiplier(character: Any, target: Any | None = None) -> float:
    state = ensure_state(character)
    multiplier = 1.0
    if aura_active(character, "Conquest Aura"):
        stacks = max(1, int(state["aura"].get("stacks", 1) or 1))
        multiplier += (0.05 * stacks) * aura_multiplier(character)
    if mark_active(character, "Mark of the Craven"):
        multiplier -= 0.10 * mark_multiplier(character)
    if target is not None and challenge_matches(character, target):
        multiplier += 0.15 * aura_multiplier(character)
    return max(0.0, multiplier)


def initiative_multiplier(character: Any) -> float:
    state = ensure_state(character)
    multiplier = 1.0
    if aura_active(character, "Conquest Aura"):
        stacks = max(1, int(state["aura"].get("stacks", 1) or 1))
        multiplier += (0.05 * stacks) * aura_multiplier(character)
    if mark_active(character, "Mark of the Craven"):
        multiplier -= 0.10 * mark_multiplier(character)
    return max(0.0, multiplier)


def protection_block_bonus(character: Any) -> float:
    state = ensure_state(character)
    bonus = 0.0
    if aura_active(character, "Protection Aura"):
        bonus += 0.03 * int(state["aura"].get("stacks", 1) or 1) * aura_multiplier(character)
    if state["interpose"].get("turns") and not state["interpose"].get("spent"):
        bonus += 0.35
    from . import promotion_kits

    guard = promotion_kits.combat_state(character).get("oath_protection_guard")
    if isinstance(guard, dict) and int(guard.get("turns", 0) or 0) > 0:
        bonus += float(guard.get("block_bonus", 0.0) or 0.0)
    return bonus


def protection_mitigation_bonus(character: Any) -> float:
    state = ensure_state(character)
    bonus = 0.0
    if aura_active(character, "Protection Aura"):
        bonus += 0.05 * int(state["aura"].get("stacks", 1) or 1) * aura_multiplier(character)
    if state["interpose"].get("turns") and not state["interpose"].get("spent"):
        bonus += 0.35
    from . import promotion_kits

    guard = promotion_kits.combat_state(character).get("oath_protection_guard")
    if isinstance(guard, dict) and int(guard.get("turns", 0) or 0) > 0:
        bonus += float(guard.get("mitigation_bonus", 0.0) or 0.0)
    return bonus


def incoming_damage_multiplier(character: Any, damage_type: str = "Physical") -> float:
    if damage_type in {"Physical", "Melee"} and mark_active(character, "Mark of Vulnerability"):
        return 1.0 + (0.20 * mark_multiplier(character))
    return 1.0


def retribution_dodge_bonus(character: Any) -> float:
    if aura_active(character, "Retribution Aura"):
        return 0.10 * aura_multiplier(character)
    return 0.0


def retribution_crit_damage_multiplier(character: Any) -> float:
    if aura_active(character, "Retribution Aura"):
        return 1.0 + (0.15 * aura_multiplier(character))
    return 1.0


def mercy_lethal_threshold(character: Any) -> float:
    return 0.05 if has_affirmation(character) else 0.10


def challenge_matches(character: Any, target: Any) -> bool:
    state = ensure_state(character)
    return int(state["challenge"].get("turns", 0) or 0) > 0 and state["challenge"].get(
        "target_id"
    ) == id(target)


def start_challenge(character: Any, target: Any) -> str:
    if path(character) != "Conquest":
        return "Only the Vow of Conquest can issue Challenge.\n"
    state = ensure_state(character)
    state["challenge"] = {"target_id": id(target), "turns": 3}
    from . import promotion_kits

    return (
        f"{target.name} is named your Challenged Foe for 3 turns.\n"
        + promotion_kits.conviction_action(character, "Challenge")
    )


def start_interpose(character: Any) -> str:
    if path(character) != "Protection":
        return "Only the Vow of Protection can Interpose.\n"
    state = ensure_state(character)
    state["interpose"] = {"turns": 2, "spent": False}
    from . import promotion_kits

    return (
        f"{character.name} enters a guarded stance for 2 turns.\n"
        + promotion_kits.conviction_action(character, "Interpose")
    )


def start_riposte(character: Any) -> str:
    if path(character) != "Retribution":
        return "Only the Vow of Retribution can prepare Judgment Riposte.\n"
    if weapon_missing(character):
        return apply_mark(character, "Retribution")
    state = ensure_state(character)
    state["riposte"] = {"turns": 2, "spent": False}
    from . import promotion_kits

    return (
        f"{character.name} prepares a retaliatory judgment for 2 turns.\n"
        + promotion_kits.conviction_action(character, "Judgment Riposte")
    )


def weapon_missing(character: Any) -> bool:
    weapon = getattr(character, "equipment", {}).get("Weapon")
    return (
        weapon is None
        or getattr(weapon, "subtyp", "None") == "None"
        or getattr(character, "is_disarmed", lambda: False)()
    )


def sword_and_board_active(character: Any) -> bool:
    """Return whether the Crusader's one-handed shield style is active."""
    skills = getattr(character, "spellbook", {}).get("Skills", {})
    weapon = getattr(character, "equipment", {}).get("Weapon")
    offhand = getattr(character, "equipment", {}).get("OffHand")
    return bool(
        "Sword & Board" in skills
        and int(getattr(weapon, "handed", 0) or 0) == 1
        and getattr(offhand, "subtyp", None) == "Shield"
    )


def sword_and_board_accuracy_bonus(character: Any) -> float:
    """Return the accuracy bonus for the active Sword & Board style."""
    return 0.10 if sword_and_board_active(character) else 0.0


def sword_and_board_damage_multiplier(character: Any) -> float:
    """Return the weapon-damage multiplier for the active shield style."""
    return 1.10 if sword_and_board_active(character) else 1.0


def _wicked_target(target: Any) -> bool:
    return getattr(target, "enemy_typ", None) in {"Fiend", "Undead"}


def condemnation(
    character: Any,
    target: Any | None,
    *,
    rng: Any | None = None,
) -> str:
    """Strike with weapon and Holy damage, possibly condemning a wicked foe."""
    if target is None:
        return "There is no foe to condemn.\n"
    if weapon_missing(character):
        return "Condemnation requires a weapon.\n"
    cost = 10
    if character.mana.current < cost:
        return f"{character.name} does not have enough mana for Condemnation.\n"
    character.mana.current -= cost
    message, hit, _crit = character.weapon_damage(
        target,
        dmg_mod=1.0,
        use_offhand=False,
        attack_slots=("Weapon",),
    )
    if not hit:
        return message

    magic = max(1, int(character.check_mod("magic", enemy=target)))
    magic_defense = max(
        0,
        int(target.check_mod("magic def", enemy=character)),
    )
    resistance = float(target.check_mod("resist", enemy=character, typ="Holy"))
    holy_damage = max(
        1,
        int(
            magic
            * 0.50
            * holy_damage_multiplier(character)
            * max(0.0, 1.0 - resistance)
            * (100 / (100 + magic_defense))
        ),
    )
    target.health.current -= holy_damage
    message += f"Condemnation burns {target.name} for {holy_damage} Holy damage.\n"

    skills = getattr(character, "spellbook", {}).get("Skills", {})
    if "Beyond Reproach" in skills and _wicked_target(target) and target.is_alive():
        generator = rng or random
        stats = int(character.stats.wisdom) + int(character.stats.charisma)
        mark_chance = max(0.25, min(0.75, 0.35 + ((stats - 20) / 200)))
        if generator.random() < mark_chance:
            setattr(target, "condemned_by_crusader", True)
            message += (
                f"{target.name} is marked by Condemnation; a successful "
                "Repel the Wicked will disintegrate it.\n"
            )
    return message


def holy_damage_multiplier(character: Any) -> float:
    """Return the Crusader's outgoing Holy-damage multiplier."""
    skills = getattr(character, "spellbook", {}).get("Skills", {})
    multiplier = 1.5 if "Sanctification" in skills else 1.0
    if penalization_active(character):
        multiplier *= 1.25
    return multiplier


def _undead_enemy_present(character: Any) -> bool:
    encounter = getattr(character, "_combat_encounter", None)
    return any(
        getattr(member.enemy, "enemy_typ", None) == "Undead"
        for member in getattr(encounter, "living_members", ())
    )


def undead_hunter_speed_multiplier(character: Any) -> float:
    """Return Undead Hunter's dynamic Speed and initiative multiplier."""
    skills = getattr(character, "spellbook", {}).get("Skills", {})
    if "Undead Hunter" not in skills or not _undead_enemy_present(character):
        return 1.0
    return 1.20


def undead_hunter_critical_bonus(character: Any) -> float:
    """Return Undead Hunter's critical chance against an undead encounter."""
    return 0.10 if undead_hunter_speed_multiplier(character) > 1.0 else 0.0


def trigger_penalization(character: Any) -> str:
    """Activate Penalization's combat-long wrath after Mortal Strike hits."""
    skills = getattr(character, "spellbook", {}).get("Skills", {})
    if "Penalization" not in skills:
        return ""
    from . import promotion_kits

    state = promotion_kits.combat_state(character)
    if state.get("crusader_wrath"):
        return ""
    state["crusader_wrath"] = True
    return (
        f"Penalization fills {character.name} with wrath, increasing critical "
        "strike chance and Holy damage.\n"
    )


def penalization_active(character: Any) -> bool:
    """Return whether Penalization's wrath is active this combat."""
    from . import promotion_kits

    return bool(promotion_kits.combat_state(character).get("crusader_wrath"))


def penalization_critical_bonus(character: Any) -> float:
    """Return the critical chance granted by Penalization's wrath."""
    return 0.15 if penalization_active(character) else 0.0


def radiant_healing_damage(
    character: Any,
    amount_healed: int,
    *,
    source: str,
) -> str:
    """Damage one living hostile after a successful combat healing spell."""
    if amount_healed <= 0 or not getattr(character, "_active_combat", False):
        return ""
    skills = getattr(character, "spellbook", {}).get("Skills", {})
    if "Radiant Healing" not in skills:
        return ""
    spell = getattr(character, "spellbook", {}).get("Spells", {}).get(source)
    if spell is None or getattr(spell, "subtyp", None) != "Heal":
        return ""
    encounter = getattr(character, "_combat_encounter", None)
    living = tuple(getattr(encounter, "living_members", ()))
    if not living:
        return ""
    target = living[0].enemy
    raw_damage = max(1, int(amount_healed * 0.10))
    hit, defense_message, damage = target.damage_reduction(
        raw_damage,
        character,
        typ="Holy",
    )
    if not hit or damage <= 0:
        return defense_message
    damage = min(int(target.health.current), int(damage))
    target.health.current -= damage
    try:
        character._emit_damage_event(
            target,
            damage,
            damage_type="Holy",
            source="Radiant Healing",
        )
    except Exception:
        pass
    return defense_message + f"Radiant Healing strikes {target.name} for {damage} Holy damage.\n"


def _shield_equipped(character: Any) -> bool:
    shield = getattr(character, "equipment", {}).get("OffHand")
    return str(getattr(shield, "subtyp", "") or "") == "Shield"


def _cancel_charged_action(target: Any, battle_engine: Any | None) -> str:
    """Cancel a target's live charge state in both ability and engine state."""
    interrupted = ""
    charging_entry = getattr(battle_engine, "charging_ability", None)
    if charging_entry and charging_entry[0] is target:
        skill = charging_entry[2]
        cancel = getattr(skill, "cancel_charge", None)
        interrupted = (
            cancel(target)
            if callable(cancel)
            else f"{target.name}'s {getattr(skill, 'name', 'charge')} was interrupted!\n"
        )
        battle_engine.charging_ability = None
        actor_id = battle_engine._actor_id_for(target)
        battle_engine.pending_actions.pop(actor_id, None)
        return interrupted
    for skill in getattr(target, "spellbook", {}).get("Skills", {}).values():
        if not getattr(skill, "charging", False):
            continue
        cancel = getattr(skill, "cancel_charge", None)
        interrupted = (
            cancel(target)
            if callable(cancel)
            else f"{target.name}'s {getattr(skill, 'name', 'charge')} was interrupted!\n"
        )
        if battle_engine is not None:
            actor_id = battle_engine._actor_id_for(target)
            battle_engine.pending_actions.pop(actor_id, None)
        break
    return interrupted


def censure(
    character: Any,
    target: Any | None,
    *,
    battle_engine: Any | None = None,
    rng: Any | None = None,
) -> str:
    """Attack and attempt to interrupt an enemy's charged ability."""
    if target is None:
        return "There is no foe to censure.\n"
    if not _shield_equipped(character):
        return "Censure requires an equipped shield.\n"
    character.mana.current -= 12
    message, hit, _crit = character.weapon_damage(
        target,
        dmg_mod=1.0,
        use_offhand=False,
        attack_slots=("Weapon",),
    )
    if not hit or not target.is_alive():
        return message
    charging = bool(
        getattr(battle_engine, "charging_ability", None)
        and battle_engine.charging_ability[0] is target
    ) or any(
        getattr(skill, "charging", False)
        for skill in getattr(target, "spellbook", {}).get("Skills", {}).values()
    )
    if not charging:
        return message + f"{target.name} has no charged ability to interrupt.\n"
    generator = rng or random
    chance = max(
        0.25,
        min(
            0.90,
            0.50 + (int(character.stats.strength) - int(target.stats.con)) * 0.02,
        ),
    )
    if generator.random() < chance:
        return message + _cancel_charged_action(target, battle_engine)
    return message + f"{target.name} maintains the charged ability.\n"


def _shield_ricochet_damage(character: Any, target: Any) -> tuple[int, str]:
    """Apply one shield impact through physical defenses."""
    raw_damage = max(1, int(character.check_mod("attack", enemy=target) * 0.8))
    hit, message, damage = target.handle_defenses(
        character,
        raw_damage,
        False,
        typ="Physical",
    )
    if not hit:
        return 0, message
    hit, reduction_message, damage = target.damage_reduction(
        damage,
        character,
        typ="Physical",
    )
    message += reduction_message
    if not hit:
        return 0, message
    damage, ward_message = target._apply_temporary_health(target, damage)
    message += ward_message
    target.health.current = max(0, target.health.current - damage)
    return damage, message


def shield_ricochet(
    character: Any,
    targets: list[tuple[str, Any]],
    *,
    battle_engine: Any,
    rng: Any | None = None,
):
    """Damage every living enemy and independently roll a one-turn stun."""
    from ..combat.combat_result import CombatResult, CombatResultGroup
    from ..combat.targeting import TargetScope

    group = CombatResultGroup(
        action="Shield Ricochet",
        actor_id=battle_engine.current_actor_id,
        target_scope=TargetScope.ALL_ENEMIES,
        target_ids=tuple(target_id for target_id, _target in targets),
    )
    if not _shield_equipped(character):
        group.add(
            CombatResult(
                action="Shield Ricochet",
                actor=character,
                actor_id=battle_engine.current_actor_id,
                message="Shield Ricochet requires an equipped shield.\n",
            )
        )
        return group
    character.mana.current -= 16
    generator = rng or random
    for target_id, target in targets:
        damage, defense_message = _shield_ricochet_damage(character, target)
        stun_chance = max(
            0.10,
            min(
                0.75,
                0.35 + (int(character.stats.strength) - int(target.stats.con)) * 0.015,
            ),
        )
        stunned = damage > 0 and generator.random() < stun_chance
        if stunned:
            target.status_effects["Stun"].active = True
            target.status_effects["Stun"].duration = max(
                1,
                int(target.status_effects["Stun"].duration or 0),
            )
        message = defense_message
        message += f"The shield ricochets into {target.name} for {damage} damage.\n"
        if stunned:
            message += f"{target.name} is stunned for 1 turn.\n"
        try:
            from . import promotion_kits

            message += promotion_kits.generator_shield_after_ricochet(
                character,
                hit=damage > 0,
                stunned=stunned,
            )
        except (AttributeError, KeyError, TypeError, ValueError):
            pass
        group.add(
            CombatResult(
                action="Shield Ricochet",
                actor=character,
                target=target,
                actor_id=battle_engine.current_actor_id,
                target_id=target_id,
                hit=damage > 0,
                damage=damage,
                effects_applied={
                    "Status": ["Stun"] if stunned else [],
                    "Physical": [],
                    "Stat": [],
                    "Magic": [],
                    "Class": [],
                },
                message=message,
            )
        )
    return group


def prayer_of_faith(
    character: Any,
    targets: list[tuple[str, Any]],
    *,
    battle_engine: Any,
    rng: Any | None = None,
):
    """Resolve one of Prayer of Faith's three equally likely miracles."""
    from ..combat.combat_result import CombatResult, CombatResultGroup
    from ..combat.targeting import TargetScope

    group = CombatResultGroup(
        action="Prayer of Faith",
        actor_id=battle_engine.current_actor_id,
        target_scope=TargetScope.ALL_ENEMIES,
        target_ids=tuple(target_id for target_id, _target in targets),
    )
    if character.health.current * 10 >= character.health.max:
        group.add(
            CombatResult(
                action="Prayer of Faith",
                actor=character,
                actor_id=battle_engine.current_actor_id,
                message="Prayer of Faith requires health below 10%.\n",
            )
        )
        return group
    character.mana.current -= 20
    generator = rng or random
    outcome = generator.choice(("heal", "barrier", "judgment"))
    if outcome == "heal":
        healing = max(0, character.health.max - character.health.current)
        character.health.current = character.health.max
        group.add(
            CombatResult(
                action="Prayer of Faith",
                actor=character,
                target=character,
                actor_id=battle_engine.current_actor_id,
                target_id="player",
                healing=healing,
                message=f"Faith restores {character.name} to full health ({healing} HP).\n",
            )
        )
    elif outcome == "barrier":
        character.temporary_health = {
            "amount": 1,
            "turns": 2,
            "source": "Prayer of Faith barrier",
            "blocks_all_damage": True,
        }
        group.add(
            CombatResult(
                action="Prayer of Faith",
                actor=character,
                target=character,
                actor_id=battle_engine.current_actor_id,
                target_id="player",
                message=(f"A Prayer of Faith barrier surrounds {character.name} for 2 turns.\n"),
            )
        )
    else:
        for target_id, target in targets:
            raw_damage = max(
                1,
                int(character.check_mod("magic", enemy=target) * 3),
            )
            _hit, message, damage = target.damage_reduction(
                raw_damage,
                character,
                typ="Holy",
            )
            target.health.current = max(0, target.health.current - damage)
            message += f"Faith judges {target.name} for {damage} Holy damage.\n"
            group.add(
                CombatResult(
                    action="Prayer of Faith",
                    actor=character,
                    target=target,
                    actor_id=battle_engine.current_actor_id,
                    target_id=target_id,
                    hit=damage > 0,
                    damage=damage,
                    message=message,
                )
            )
    return group


def repel_the_wicked(
    character: Any,
    target: Any | None,
    *,
    rng: Any | None = None,
) -> str:
    """Attempt to drive a fiend or undead foe from the current combat."""
    if target is None:
        return "There is no foe to repel.\n"
    cost = 12
    if character.mana.current < cost:
        return f"{character.name} does not have enough mana to cast " "Repel the Wicked.\n"
    character.mana.current -= cost
    if not _wicked_target(target):
        return "Repel the Wicked affects only fiends and undead.\n"
    if mercy_immune(target):
        return f"{target.name} resists banishment.\n"

    generator = rng or random
    stats = int(character.stats.wisdom) + int(character.stats.charisma)
    target_wisdom = int(getattr(getattr(target, "stats", None), "wisdom", 10) or 10)
    success_chance = max(
        0.10,
        min(0.85, 0.35 + ((stats - (target_wisdom * 2)) / 100)),
    )
    if generator.random() >= success_chance:
        return f"{target.name} stands firm against Repel the Wicked.\n"

    target.health.current = 0
    if bool(getattr(target, "condemned_by_crusader", False)):
        setattr(target, "paladin_disintegrated", True)
        return f"Repel the Wicked ignites Condemnation and disintegrates " f"{target.name}.\n"
    setattr(target, "paladin_repelled", True)
    return f"{target.name} flees from the sacred force.\n"


def clear_condemnation(target: Any) -> None:
    """Clear the combat-only Condemnation mark."""
    if hasattr(target, "condemned_by_crusader"):
        setattr(target, "condemned_by_crusader", False)


def block_succeeded(character: Any) -> str:
    state = ensure_state(character)
    guarded = bool(state["interpose"].get("turns") and not state["interpose"].get("spent"))
    if state["interpose"].get("turns") and not state["interpose"].get("spent"):
        state["interpose"]["spent"] = True
    if path(character) == "Protection":
        msg = trigger_aura(character, "Protection")
        if guarded:
            from . import promotion_kits

            msg += promotion_kits.conviction_action(
                character,
                "successful guarded block",
                clean=True,
            )
        return msg
    return ""


def redeem_chance(character: Any, target: Any) -> float:
    if target is None or mercy_immune(target):
        return 0.0
    hp_max = max(1, int(getattr(getattr(target, "health", None), "max", 1) or 1))
    missing_ratio = max(
        0.0, min(1.0, (hp_max - getattr(target.health, "current", hp_max)) / hp_max)
    )
    stats_bonus = (
        int(getattr(character.stats, "charisma", 0)) + int(getattr(character.stats, "wisdom", 0))
    ) / 300.0
    chance = 0.10 + stats_bonus + (missing_ratio * 0.45)
    if aura_active(character, "Redemption Aura"):
        chance += 0.10 * aura_multiplier(character)
    return max(0.10, min(0.90, chance))


def mercy_immune(target: Any) -> bool:
    if bool(getattr(target, "mercy_immune", False)):
        return True
    if "Boss" in str(getattr(target, "__class__", type(target)).__name__):
        return True
    if bool(getattr(target, "class_ring_trial", False)):
        return True
    return bool(getattr(target, "is_boss", False))


def attempt_redeem(character: Any, target: Any, rng: Any | None = None) -> str:
    if path(character) != "Redemption":
        return "Only the Vow of Redemption can use Redeem.\n"
    if mercy_immune(target):
        return f"{target.name} refuses mercy.\n"
    from . import promotion_kits

    message = promotion_kits.conviction_action(character, "Redeem")
    rng = rng or random
    chance = redeem_chance(character, target)
    if rng.random() <= chance:
        target.health.current = 0
        setattr(target, "paladin_mercy_victory", True)
        message += promotion_kits.conviction_action(
            character,
            "successful Redeem",
            clean=True,
        )
        return message + trigger_aura(character, "Redemption") + f"{target.name} yields to mercy.\n"
    return message + f"{target.name} rejects mercy.\n"


def on_enemy_defeated(
    character: Any, enemy: Any, bounty_target: bool = False, mercy: bool = False
) -> str:
    if mercy:
        return ""
    selected = path(character)
    if selected == "Redemption":
        clear_aura(character)
        return apply_mark(character, "Redemption")
    if selected == "Conquest" and (challenge_matches(character, enemy) or bounty_target):
        ensure_state(character)["challenge"] = {"target_id": None, "turns": 0}
        if bounty_target and mark_active(character, "Mark of the Craven"):
            clear_mark(character)
        from . import promotion_kits

        return trigger_aura(character, "Conquest") + promotion_kits.conviction_action(
            character,
            "defeated challenged foe",
            clean=True,
        )
    return ""


def on_flee(character: Any, success: bool) -> str:
    if success and path(character) == "Conquest":
        return apply_mark(character, "Conquest")
    return ""


def on_incapacitated(character: Any) -> str:
    if path(character) == "Protection":
        return apply_mark(character, "Protection")
    return ""


def clear_transient_marks(character: Any) -> None:
    state = ensure_state(character)
    mark = state["mark"]
    if (
        mark.get("name") == "Mark of Vulnerability"
        and not getattr(character, "incapacitated", lambda: False)()
    ):
        clear_mark(character)
    if mark.get("name") == "Mark of Mercy" and not weapon_missing(character):
        clear_mark(character)


def pending_riposte(character: Any) -> bool:
    state = ensure_state(character)
    return bool(state["riposte"].get("turns") and not state["riposte"].get("spent"))


def resolve_riposte(character: Any, target: Any) -> str:
    state = ensure_state(character)
    if not pending_riposte(character):
        return ""
    state["riposte"]["spent"] = True
    if weapon_missing(character):
        state["riposte"]["turns"] = 0
        return apply_mark(character, "Retribution")
    damage = max(1, int(character.check_mod("weapon", enemy=target) * 0.75))
    damage += max(1, int(character.check_mod("heal", enemy=target) * 0.25))
    target.health.current -= damage
    message = (
        f"{character.name}'s Judgment Riposte strikes {target.name} for {damage} Holy damage.\n"
    )
    if getattr(target.health, "current", 1) <= 0:
        message += trigger_aura(character, "Retribution", doubled=True)
    from . import promotion_kits

    message += promotion_kits.conviction_action(
        character,
        "triggered Judgment Riposte",
        clean=True,
    )
    ensure_state(character)["riposte"] = {"turns": 0, "spent": True}
    return message


def _has_talent(character: Any, talent_key: str) -> bool:
    try:
        from ..progression import has_talent

        return has_talent(character, talent_key)
    except Exception:
        return False


def _valid_oath_weapon(character: Any, *, require_shield: bool = False) -> str:
    if weapon_missing(character):
        return "A class-legal main-hand weapon is required.\n"
    weapon = character.equipment.get("Weapon")
    allowed = set(getattr(character.cls, "restrictions", {}).get("Weapon", ()))
    if allowed and getattr(weapon, "subtyp", None) not in allowed:
        return "A class-legal main-hand weapon is required.\n"
    if (
        require_shield
        and getattr(
            character.equipment.get("OffHand"),
            "subtyp",
            None,
        )
        != "Shield"
    ):
        return "The Vow of Protection requires a shield for Oath's Judgment.\n"
    return ""


def _spend_oath_conviction(character: Any, action_name: str) -> tuple[int, str]:
    from . import promotion_kits

    state = promotion_kits.combat_state(character)
    stacks = max(0, int(state.get("oath_conviction", 0) or 0))
    if stacks <= 0:
        return 0, f"{action_name} requires Oath Conviction.\n"
    spent = promotion_kits.spend_meter(character, "oath_conviction")
    return (
        spent,
        f"{character.name} spends {spent} Oath Conviction on {action_name}.\n",
    )


def _preserve_conviction(character: Any, spent: int, applied: bool) -> str:
    if not applied or spent <= 0 or not has_affirmation(character):
        return ""
    from . import promotion_kits

    state = promotion_kits.combat_state(character)
    marker = "Crusader:oath_conviction"
    if marker in state["ring_preserved"]:
        return ""
    state["ring_preserved"].add(marker)
    state["oath_conviction"] = max(
        1,
        int(state.get("oath_conviction", 0) or 0),
    )
    return "Vow Affirmation preserves 1 Oath Conviction.\n"


def _apply_oath_barrier(
    character: Any,
    amount: int,
    duration: int,
) -> None:
    barrier = character.magic_effects["Nature Shield"]
    barrier.active = True
    barrier.duration = max(int(barrier.duration or 0), duration)
    barrier.extra = max(int(barrier.extra or 0), max(1, int(amount)))


_OATH_JUDGMENT_DESCRIPTIONS = {
    "Redemption": (
        "0.9x Holy weapon strike; +3 accuracy per stack and heal 5% maximum " "HP per stack on hit."
    ),
    "Conquest": ("1.0x plus 0.15x weapon damage per stack and +5 accuracy per stack."),
    "Protection": ("Shield-required 0.75x strike; lower Attack and gain a barrier on hit."),
    "Retribution": ("1.0x Holy strike; prepare a 0.25x-per-stack Holy counter on hit."),
}

_OATH_SHELTER_DESCRIPTIONS = {
    "Redemption": ("Heal 10% maximum HP per stack and cleanse Poison at two stacks."),
    "Conquest": "Gain 3 Attack and Speed per stack for two turns.",
    "Protection": ("Gain 15 barrier and 5 points of block chance and mitigation per stack."),
    "Retribution": (
        "Reduce the next damaging hit by 8% per stack and return the prevented "
        "amount as Holy damage."
    ),
}


def oath_technique_description(character: Any, action_name: str) -> str:
    """Describe an oath spender using the current vow and Conviction state."""
    selected = path(character)
    if selected is None:
        return "No vow sworn. Requires at least 1 Conviction and spends all stacks."
    from . import promotion_kits

    conviction = int(promotion_kits.combat_state(character).get("oath_conviction", 0) or 0)
    descriptions = (
        _OATH_JUDGMENT_DESCRIPTIONS
        if action_name == "Oath's Judgment"
        else _OATH_SHELTER_DESCRIPTIONS
    )
    return (
        f"Vow of {selected}; requires at least 1 Conviction and spends all "
        f"{conviction} stored stack(s). {descriptions[selected]}"
    )


def oaths_judgment(character: Any, target: Any | None) -> str:
    """Spend Conviction on a vow-specific weapon judgment."""
    selected = path(character)
    if selected is None:
        return "A Paladin vow must be sworn before using Oath's Judgment.\n"
    if target is None:
        return "There is no target for Oath's Judgment.\n"
    validation = _valid_oath_weapon(
        character,
        require_shield=selected == "Protection",
    )
    if validation:
        return validation
    spent, message = _spend_oath_conviction(character, "Oath's Judgment")
    if spent <= 0:
        return message

    advanced = _has_talent(character, "crusader.righteous-advance")
    potency = 1.25 if advanced else 1.0
    direct_bonus = 0.10 if advanced else 0.0
    accuracy = 0.03 * spent
    damage_mod = 1.0 + direct_bonus
    if selected == "Redemption":
        damage_mod = 0.90 + direct_bonus
    elif selected == "Conquest":
        damage_mod = 1.0 + direct_bonus + (0.15 * potency * spent)
        accuracy = 0.05 * spent
    elif selected == "Protection":
        damage_mod = 0.75 + direct_bonus

    before = max(0, int(getattr(target.health, "current", 0) or 0))
    attack_message, hit, _crit = character.weapon_damage(
        target,
        dmg_mod=damage_mod,
        use_offhand=False,
        attack_slots=("Weapon",),
        accuracy_modifier=accuracy,
        damage_type_override="Holy",
    )
    message += attack_message
    actual_damage = max(
        0,
        before - max(0, int(getattr(target.health, "current", 0) or 0)),
    )
    applied = bool(hit)

    if hit and selected == "Redemption":
        healing = max(
            1,
            math.ceil(character.health.max * 0.05 * potency * spent),
        )
        healing = min(
            healing,
            max(0, character.health.max - character.health.current),
        )
        character.health.current += healing
        if healing > 0:
            message += f"Redemption restores {healing} HP through Oath's Judgment.\n"
    elif hit and selected == "Protection":
        penalty = max(1, math.ceil(2 * potency * spent))
        attack = target.stat_effects["Attack"]
        attack.active = True
        attack.duration = max(int(attack.duration or 0), 2)
        attack.extra = min(int(attack.extra or 0), -penalty)
        barrier = max(1, math.ceil(10 * potency * spent))
        _apply_oath_barrier(character, barrier, 2)
        message += (
            f"Protection lowers enemy Attack by {penalty} and grants a "
            f"{barrier}-point barrier.\n"
        )
    elif hit and selected == "Retribution":
        from . import promotion_kits

        counter_mod = 0.25 * potency * spent
        promotion_kits.combat_state(character)["oath_judgment_counter"] = {
            "turns": 2,
            "damage_mod": counter_mod,
        }
        message += (
            "Retribution prepares a Holy counter against the next incoming " "weapon attack.\n"
        )
    elif hit and selected == "Conquest":
        message += f"Conquest drives the judgment for {actual_damage} weapon damage.\n"

    if not hit:
        message += "Oath's Judgment misses, but its Conviction is spent.\n"
    message += _preserve_conviction(character, spent, applied)
    return message


def oaths_shelter(character: Any) -> str:
    """Spend Conviction on vow-specific self-protection."""
    selected = path(character)
    if selected is None:
        return "A Paladin vow must be sworn before using Oath's Shelter.\n"
    spent, message = _spend_oath_conviction(character, "Oath's Shelter")
    if spent <= 0:
        return message

    advanced = _has_talent(character, "crusader.consecrated-bulwark")
    potency = 1.25 if advanced else 1.0
    duration = 3 if advanced else 2
    applied = False
    if selected == "Redemption":
        healing = max(
            1,
            math.ceil(character.health.max * 0.10 * potency * spent),
        )
        healing = min(
            healing,
            max(0, character.health.max - character.health.current),
        )
        character.health.current += healing
        cleansed = False
        poison = character.status_effects.get("Poison")
        if spent >= 2 and poison is not None and poison.active:
            poison.active = False
            poison.duration = 0
            cleansed = True
        applied = healing > 0 or cleansed
        message += f"Redemption restores {healing} HP."
        if cleansed:
            message += " Poison is cleansed."
        message += "\n"
    elif selected == "Conquest":
        bonus = max(1, math.ceil(3 * potency * spent))
        for name in ("Attack", "Speed"):
            effect = character.stat_effects[name]
            effect.active = True
            effect.duration = max(int(effect.duration or 0), duration)
            effect.extra = max(int(effect.extra or 0), bonus)
        applied = True
        message += f"Conquest raises Attack and Speed by {bonus} for {duration} " "turns.\n"
    elif selected == "Protection":
        from . import promotion_kits

        barrier = max(1, math.ceil(15 * potency * spent))
        _apply_oath_barrier(character, barrier, duration)
        bonus = 0.05 * potency * spent
        promotion_kits.combat_state(character)["oath_protection_guard"] = {
            "turns": duration,
            "block_bonus": bonus,
            "mitigation_bonus": bonus,
        }
        applied = True
        message += (
            f"Protection grants a {barrier}-point barrier and "
            f"{round(bonus * 100)} percentage points of block and mitigation "
            f"for {duration} turns.\n"
        )
    else:
        from . import promotion_kits

        reduction = min(0.75, 0.08 * potency * spent)
        promotion_kits.combat_state(character)["oath_retribution_shelter"] = {
            "turns": duration,
            "reduction": reduction,
        }
        applied = True
        message += (
            f"Retribution prepares to turn {round(reduction * 100)}% of the "
            f"next damaging hit back on its attacker within {duration} turns.\n"
        )

    message += _preserve_conviction(character, spent, applied)
    return message


def resolve_oath_judgment_counter(
    defender: Any,
    attacker: Any,
) -> str:
    """Resolve and consume the Retribution form of Oath's Judgment."""
    try:
        from . import promotion_kits

        state = promotion_kits.combat_state(defender)
        counter = state.get("oath_judgment_counter")
        if not isinstance(counter, dict) or int(counter.get("turns", 0) or 0) <= 0:
            return ""
        from ..combat.reactions import execute_reaction

        def resolve() -> str:
            state["oath_judgment_counter"] = None
            if weapon_missing(defender):
                return "Oath's Judgment cannot answer while its user is disarmed.\n"
            message, _hit, _crit = defender.weapon_damage(
                attacker,
                dmg_mod=float(counter.get("damage_mod", 0.25) or 0.25),
                use_offhand=False,
                attack_slots=("Weapon",),
                damage_type_override="Holy",
            )
            return "Oath's Judgment answers with a Holy counter.\n" + message

        return execute_reaction("oaths_judgment", defender, resolve) or ""
    except Exception:
        return ""


def oath_shelter_damage_reduction(
    defender: Any,
    attacker: Any,
    damage: int,
) -> tuple[int, str]:
    """Consume Retribution Shelter and return prevented damage as Holy."""
    if damage <= 0:
        return damage, ""
    try:
        from . import promotion_kits

        state = promotion_kits.combat_state(defender)
        shelter = state.get("oath_retribution_shelter")
        if not isinstance(shelter, dict) or int(shelter.get("turns", 0) or 0) <= 0:
            return damage, ""
        state["oath_retribution_shelter"] = None
        prevented = max(
            1,
            int(damage * float(shelter.get("reduction", 0.08) or 0.08)),
        )
        prevented = min(damage, prevented)
        attacker.health.current = max(0, attacker.health.current - prevented)
        try:
            defender._emit_damage_event(
                attacker,
                prevented,
                damage_type="Holy",
                source="Oath's Shelter",
            )
        except Exception:
            pass
        return (
            damage - prevented,
            (
                f"Oath's Shelter prevents {prevented} damage and returns it "
                f"to {attacker.name} as Holy damage.\n"
            ),
        )
    except Exception:
        return damage, ""


def mercy_lethal_message(character: Any, incoming_damage: int) -> str:
    if incoming_damage <= 0 or not mark_active(character, "Mark of Mercy"):
        return ""
    hp_max = max(1, int(getattr(character.health, "max", 1) or 1))
    if character.health.current / hp_max <= mercy_lethal_threshold(character):
        character.health.current = 0
        return f"{MARK_NAMES['Retribution']} turns mercy into a fatal opening.\n"
    return ""
