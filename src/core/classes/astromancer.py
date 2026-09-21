"""Astromancer class definition and rune-state helpers."""

from __future__ import annotations

from typing import Any

from src.core.randomness import gameplay_random as random

from .base import Job

CONSTELLATIONS = ("Ember", "Tide", "Gale", "Stone")
RUNE_CAP = 3
BASE_RUNE_DROP_CHANCE = 0.25
ASTROMANCER_ACTIVE_SIGN_DROP_BONUS = 0.25
RUNIC_BOOST_FLOOR = 0.75
RING_ACTIVE_SIGN_BOOST_FLOOR = 1.0

SIGN_TO_ELEMENT = {
    "Ember": "Fire",
    "Tide": "Water",
    "Gale": "Wind",
    "Stone": "Earth",
}
ELEMENT_TO_SIGN = {element: sign for sign, element in SIGN_TO_ELEMENT.items()}
NATURAL_ELEMENTS = set(ELEMENT_TO_SIGN)
THREAD_ACTIONS = frozenset(
    {
        "Foretell",
        "Twist Fate",
        "Wormhole",
        "Rewind",
        "Runic Boost",
        "Astral Judgment",
    }
)
LEARNABLE_SPELL_RANKS = {
    "Aqualung": 1,
    "Hurricane": 1,
    "Mudslide": 1,
    "Blinding Fog": 1,
    "Stupefy": 1,
    "Tornado": 2,
    "Poison Breath": 2,
    "Earthquake": 2,
    "Tsunami": 2,
    "Petrify": 2,
    "Volcano": 2,
    "Photon Sphere": 3,
}


def default_state() -> dict[str, Any]:
    return {
        "active_constellation_index": 0,
        "runes": {sign: 0 for sign in CONSTELLATIONS},
    }


def normalize_state(state: Any) -> dict[str, Any]:
    normalized = default_state()
    if not isinstance(state, dict):
        return normalized

    try:
        normalized["active_constellation_index"] = int(
            state.get("active_constellation_index", 0) or 0
        ) % len(CONSTELLATIONS)
    except (TypeError, ValueError):
        normalized["active_constellation_index"] = 0

    incoming_runes = state.get("runes", {})
    if isinstance(incoming_runes, dict):
        for sign in CONSTELLATIONS:
            try:
                count = int(incoming_runes.get(sign, 0) or 0)
            except (TypeError, ValueError):
                count = 0
            normalized["runes"][sign] = max(0, min(RUNE_CAP, count))
    return normalized


def ensure_state(character: Any) -> dict[str, Any]:
    state = normalize_state(getattr(character, "astromancer_state", None))
    setattr(character, "astromancer_state", state)
    return state


def class_name(character: Any) -> str:
    return str(getattr(getattr(character, "cls", None), "name", "") or "")


def has_rune_system(character: Any) -> bool:
    return class_name(character) in {"Diviner", "Astromancer"}


def is_astromancer(character: Any) -> bool:
    return class_name(character) == "Astromancer"


def silent_lucidity_active(character: Any) -> bool:
    """Return whether the Astromancer may select a lucid spell while asleep."""
    return bool(
        is_astromancer(character)
        and "Silent Lucidity" in getattr(character, "spellbook", {}).get("Skills", {})
    )


def can_cast_while_asleep(character: Any, spell: Any) -> bool:
    """Limit Silent Lucidity to authored Time and Divination spells."""
    if not silent_lucidity_active(character):
        return False
    return str(getattr(spell, "subtyp", "") or "") in {"Time", "Divination"}


def active_constellation(character: Any) -> str:
    state = ensure_state(character)
    index = int(state.get("active_constellation_index", 0) or 0)
    return CONSTELLATIONS[index % len(CONSTELLATIONS)]


def advance_constellation(character: Any) -> str:
    state = ensure_state(character)
    index = int(state.get("active_constellation_index", 0) or 0) + 1
    state["active_constellation_index"] = index % len(CONSTELLATIONS)
    return active_constellation(character)


def spin_constellation(character: Any, rng: Any = random) -> str:
    state = ensure_state(character)
    current = int(state.get("active_constellation_index", 0) or 0)
    choices = [idx for idx in range(len(CONSTELLATIONS)) if idx != current]
    state["active_constellation_index"] = int(rng.choice(choices))
    return active_constellation(character)


def rune_grid_lines(character: Any) -> list[str]:
    state = ensure_state(character)
    runes = state["runes"]
    lines = []
    for sign in CONSTELLATIONS:
        filled = int(runes.get(sign, 0) or 0)
        cells = "".join("*" if idx < filled else "." for idx in range(RUNE_CAP))
        lines.append(f"{sign}: {cells}")
    return lines


def rune_status_summary(character: Any) -> str:
    return " | ".join(rune_grid_lines(character))


def sign_for_spell(spell: Any) -> str | None:
    return ELEMENT_TO_SIGN.get(str(getattr(spell, "subtyp", "") or ""))


def boostable_spells(character: Any) -> list[str]:
    if not has_rune_system(character):
        return []
    state = ensure_state(character)
    spells = getattr(character, "spellbook", {}).get("Spells", {})
    names = []
    for name, spell in spells.items():
        if getattr(spell, "passive", False):
            continue
        sign = sign_for_spell(spell)
        if not sign:
            continue
        if int(state["runes"].get(sign, 0) or 0) <= 0:
            continue
        if int(getattr(spell, "cost", 0) or 0) > int(getattr(character.mana, "current", 0) or 0):
            continue
        names.append(name)
    return names


def has_awakened_equipped_class_ring(character: Any) -> bool:
    try:
        from . import class_rings

        return bool(
            class_rings.is_awakened(character, "Astromancer")
            and class_rings.has_equipped_class_ring(character)
        )
    except Exception:
        return False


def runic_boost_floor(character: Any, sign: str | None) -> float:
    if (
        is_astromancer(character)
        and sign == active_constellation(character)
        and has_awakened_equipped_class_ring(character)
    ):
        return RING_ACTIVE_SIGN_BOOST_FLOOR
    return RUNIC_BOOST_FLOOR


def consume_rune(character: Any, sign: str) -> bool:
    state = ensure_state(character)
    count = int(state["runes"].get(sign, 0) or 0)
    if count <= 0:
        return False
    state["runes"][sign] = count - 1
    return True


def add_rune(character: Any, sign: str, amount: int = 1) -> bool:
    if sign not in CONSTELLATIONS:
        return False
    state = ensure_state(character)
    before = int(state["runes"].get(sign, 0) or 0)
    after = max(0, min(RUNE_CAP, before + int(amount)))
    state["runes"][sign] = after
    return after > before


def rune_drop_chance(character: Any, target: Any, spell: Any) -> tuple[str | None, float]:
    sign = sign_for_spell(spell)
    if not sign:
        return None, 0.0
    chance = BASE_RUNE_DROP_CHANCE
    try:
        from ..progression import has_talent

        if has_talent(character, "diviner.open-sigils"):
            chance += 0.10
        if sign == active_constellation(character) and has_talent(
            character, "astromancer.celestial-runes"
        ):
            chance += 0.15
    except (AttributeError, KeyError, TypeError):
        pass
    if is_astromancer(character) and sign == active_constellation(character):
        chance += ASTROMANCER_ACTIVE_SIGN_DROP_BONUS
    element = SIGN_TO_ELEMENT[sign]
    resistance = 0.0
    try:
        resistance = float(getattr(target, "resistance", {}).get(element, 0.0) or 0.0)
    except (TypeError, ValueError):
        resistance = 0.0
    if resistance >= 0:
        chance *= max(0.0, 1.0 - resistance)
    else:
        chance *= 1.0 + abs(resistance)
    return sign, max(0.0, min(1.0, chance))


def maybe_award_rune(
    character: Any, target: Any, spell: Any, rng: Any = random
) -> tuple[bool, str | None, float]:
    if not has_rune_system(character):
        return False, None, 0.0
    sign, chance = rune_drop_chance(character, target, spell)
    if not sign or chance <= 0:
        return False, sign, chance
    if rng.random() < chance:
        return add_rune(character, sign), sign, chance
    return False, sign, chance


def constellation_bonus(character: Any, damage_type: str | None = None) -> float:
    if not has_awakened_equipped_class_ring(character):
        return 0.0
    current = active_constellation(character)
    element = SIGN_TO_ELEMENT.get(current)
    if damage_type is None or damage_type == element:
        return 0.15
    return 0.05


def spell_learning_rank(character: Any) -> int:
    """Return the maximum witnessed-spell rank the character may learn."""
    skill = getattr(character, "spellbook", {}).get("Skills", {}).get("Learn Spell")
    if skill is None or class_name(character) not in {"Diviner", "Astromancer"}:
        return 0
    if (
        skill.__class__.__name__ == "LearnSpell2"
        or "rank 2" in str(getattr(skill, "description", "")).lower()
    ):
        return 2
    return 1


def spell_resolution_succeeded(result: Any, spell: Any) -> bool:
    """Return whether a witnessed spell resolved without miss or full negation."""
    recorded = result if hasattr(result, "hit") else getattr(spell, "result", None)
    if recorded is not None:
        if getattr(recorded, "hit", None) is False or bool(getattr(recorded, "dodge", False)):
            return False
        extra = getattr(recorded, "extra", {}) or {}
        if extra.get("no_effect_reason") or extra.get("duplicate_intercepted"):
            return False
    message = str(result or "").lower()
    blocked = (
        "has no effect",
        "no effect",
        "there is no ",
        "no spell is ",
        "not enough mana",
        "cannot ",
        "collapses without",
        "misses ",
        "dodged",
        "mirror image",
        "immune",
        "fumbles",
    )
    return not any(fragment in message for fragment in blocked)


def learn_witnessed_spell(character: Any, spell: Any, result: Any) -> str:
    """Permanently learn one successfully witnessed, explicitly ranked spell."""
    maximum_rank = spell_learning_rank(character)
    name = str(getattr(spell, "name", "") or "")
    authored_rank = getattr(spell, "rank", None)
    rank = LEARNABLE_SPELL_RANKS.get(name)
    if (
        maximum_rank <= 0
        or rank is None
        or authored_rank != rank
        or rank > maximum_rank
        or name in getattr(character, "spellbook", {}).get("Spells", {})
        or not spell_resolution_succeeded(result, spell)
    ):
        return ""
    from .. import abilities

    class_key = str(getattr(spell, "_class_name", spell.__class__.__name__) or "")
    constructor = getattr(abilities, class_key, None)
    if not callable(constructor):
        return ""
    learned = constructor()
    character.spellbook.setdefault("Spells", {})[learned.name] = learned
    return f"{character.name} learns {learned.name} by witnessing its pattern.\n"


def record_thread_action(character: Any, action_name: str, *, successful: bool) -> str:
    """Award one Foresight Thread for an authored successful action."""
    if not successful or action_name not in THREAD_ACTIONS or not is_astromancer(character):
        return ""
    from . import promotion_kits

    state = promotion_kits.combat_state(character)
    if action_name == "Rewind":
        if state.get("rewind_thread_granted"):
            return ""
        state["rewind_thread_granted"] = True
    token = int(state.get("action_token", 0) or 0)
    marker = (token, action_name)
    if state.get("foresight_thread_action") == marker:
        return ""
    state["foresight_thread_action"] = marker
    amount = 1
    try:
        from ..progression import has_talent

        if has_talent(character, "astromancer.thread-spinner") and not state.get(
            "thread_spinner_used"
        ):
            amount += 1
            state["thread_spinner_used"] = True
    except (AttributeError, KeyError, TypeError):
        pass
    return promotion_kits.gain_meter(
        character,
        "foresight_threads",
        amount,
        action_name,
    )


def begin_threaded_spell(character: Any, spell: Any) -> tuple[int, str]:
    """Spend a prepared Threaded Cast and install its one-cast context."""
    if not is_astromancer(character):
        return 0, ""
    from . import promotion_kits

    state = promotion_kits.combat_state(character)
    if not state.get("threaded_cast_pending"):
        return 0, ""
    spent = promotion_kits.spend_meter(character, "foresight_threads")
    state["threaded_cast_pending"] = False
    if spent <= 0:
        return 0, ""
    active_sign = sign_for_spell(spell) == active_constellation(character)
    ring_bonus = 1 if active_sign and has_awakened_equipped_class_ring(character) else 0
    character._threaded_cast_context = {
        "threads": spent,
        "accuracy": (0.05 * spent) + (0.05 * ring_bonus),
        "status": (0.05 * spent) + (0.05 * ring_bonus),
        "output": (0.06 * spent) + (0.05 * ring_bonus),
        "ring": bool(ring_bonus),
    }
    message = f"{character.name} spends {spent} Foresight Thread(s) on {spell.name}.\n"
    if ring_bonus:
        message += "Constellation Cycle strengthens the active-sign thread.\n"
    return spent, message


def clear_threaded_spell(character: Any) -> None:
    """Remove the ephemeral context installed for one marked cast."""
    if hasattr(character, "_threaded_cast_context"):
        delattr(character, "_threaded_cast_context")


def threaded_bonus(character: Any, key: str) -> float:
    """Return one numeric bonus from the active Threaded Cast context."""
    context = getattr(character, "_threaded_cast_context", {})
    try:
        return max(0.0, float(context.get(key, 0.0) or 0.0))
    except (AttributeError, TypeError, ValueError):
        return 0.0


def tephra_splash(character: Any, primary_target: Any, encounter: Any) -> str:
    """Scatter Volcano debris onto every other living hostile."""
    if not is_astromancer(character) or "Tephra" not in getattr(character, "spellbook", {}).get(
        "Skills", {}
    ):
        return ""
    messages = []
    raw = max(1, int(character.check_mod("magic") * 0.35))
    for member in getattr(encounter, "living_members", ()):
        target = member.enemy
        if target is primary_target:
            continue
        hit, reduction, damage = target.damage_reduction(raw, character, typ="Fire")
        dealt = min(max(0, int(damage or 0)), int(target.health.current)) if hit else 0
        if dealt:
            target.health.current -= dealt
            character._emit_damage_event(
                target,
                dealt,
                damage_type="Fire",
                source="Tephra",
                ability_name="Volcano",
            )
        messages.append(reduction)
        messages.append(f"Tephra strikes {target.name} for {dealt} Fire damage.\n")
    return "".join(messages)


class Astromancer(Job):
    """
    Promotion: Pathfinder -> Diviner -> Astromancer
    Additional Pros: can learn rank 2 enemy specials when cast against; increased intel gain
    Additional Cons: None
    Special Mechanic: Runic Alterations - defeating enemies with elemental spells gives chance
        to drop runes
    """

    def __init__(self):
        super().__init__(
            name="Astromancer",
            description="Classified among the forbidden arts, astromancers study the celestial "
            "forces that govern magic, destiny, and the hidden threads of fate. Through careful "
            "observation they learn rank-one and rank-two hostile spells that resolve while "
            "they are present. Authored divination and time actions build Foresight Threads; "
            "those who master the stars spend them to bend "
            "probability itself, turning fortune against their enemies and ensuring destiny "
            "unfolds according to their design.",
            str_plus=0,
            int_plus=3,
            wis_plus=2,
            con_plus=1,
            cha_plus=1,
            dex_plus=0,
            att_plus=1,
            def_plus=1,
            magic_plus=4,
            magic_def_plus=4,
            restrictions={
                "Weapon": ["Dagger", "Staff"],
                "OffHand": ["Rod"],
                "Armor": ["Cloth"],
            },
            pro_level=3,
        )
