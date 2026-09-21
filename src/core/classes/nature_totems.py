"""Shaman and Soulcatcher nature Totem helpers."""

from __future__ import annotations

from typing import Any

from src.core.randomness import gameplay_random as random

ELIGIBLE_CLASSES = {"Shaman", "Soulcatcher"}
ELEMENTAL_ASPECTS = ("Earth", "Water", "Fire", "Wind")
COMMUNION_SPELLS = {
    "Water": "Tsunami",
    "Earth": "Earthquake",
    "Fire": "Fireball",
    "Wind": "Tornado",
}
ASPECT_SPELL_ORDER = {
    "Earth": ("Tremor", "Mudslide", "Earthquake"),
    "Water": ("Water Jet", "Hydration", "Tsunami"),
    "Fire": ("Scorch", "Firebolt", "Fireball", "Firestorm"),
    "Wind": ("Gust", "Hurricane", "Tornado"),
    "Soul": ("Soul Drain",),
}
SPELL_TO_ASPECT = {
    "Tremor": "Earth",
    "Mudslide": "Earth",
    "Earthquake": "Earth",
    "Water Jet": "Water",
    "Hydration": "Water",
    "Tsunami": "Water",
    "Scorch": "Fire",
    "Firebolt": "Fire",
    "Fireball": "Fire",
    "Firestorm": "Fire",
    "Gust": "Wind",
    "Hurricane": "Wind",
    "Tornado": "Wind",
    "Soul Drain": "Soul",
}
BASE_PULSE_CHANCE = 0.35
STAFF_PULSE_BONUS = 0.15
TOTEM_PULSE_POTENCY = 0.50
STAFF_MATCHING_CAST_MULTIPLIER = 1.20
WATER_WARD_MAGIC_DEFENSE_BONUS = 0.20
WATER_WARD_ABSORB_FRACTION = 0.25
WIND_COMMUNION_POS = (5, 5, 3)


def has_nature_talent(character: Any, talent_key: str) -> bool:
    """Return whether a Shaman-line progression talent is owned."""
    try:
        from ..progression import has_talent

        return has_talent(character, talent_key)
    except (AttributeError, KeyError, TypeError, ValueError):
        return False


def _dread_key(target: Any) -> str:
    return str(getattr(target, "combatant_id", None) or id(target))


def dread_stacks(character: Any, target: Any) -> int:
    """Return combat-only Bad Omens dread on one enemy."""
    from . import promotion_kits

    dread = promotion_kits.combat_state(character).setdefault("omen_dread", {})
    return max(0, int(dread.get(_dread_key(target), 0) or 0))


def add_dread(character: Any, target: Any, reason: str) -> str:
    """Add one dread and realize the omen at three stacks."""
    if target is None or not getattr(target, "is_alive", lambda: False)():
        return ""
    from . import promotion_kits

    dread = promotion_kits.combat_state(character).setdefault("omen_dread", {})
    key = _dread_key(target)
    stacks = min(3, max(0, int(dread.get(key, 0) or 0)) + 1)
    dread[key] = stacks
    message = f"{target.name} gains dread from {reason} ({stacks}/3).\n"
    if stacks < 3:
        return message
    dread[key] = 0
    if target.has_status_protection("Stun"):
        return message + f"{target.name} resists the omen.\n"
    stun = target.status_effects["Stun"]
    stun.active = True
    duration = 3 if has_nature_talent(character, "shaman.inevitable-omen") else 2
    stun.duration = max(int(stun.duration or 0), duration)
    stun.source = "Bad Omens"
    return message + f"The omen comes true: {target.name} is Stunned for {duration} turns.\n"


def record_enemy_miss(character: Any, enemy: Any, result: Any) -> str:
    """Turn a hostile miss into Bad Omens dread."""
    if not has_nature_talent(character, "shaman.bad-omens"):
        return ""
    portions = getattr(result, "results", None)
    if not isinstance(portions, list):
        portions = [result]
    if not portions or not any(getattr(portion, "hit", None) is False for portion in portions):
        return ""
    return add_dread(character, enemy, "a failed attack")


def passive_rating_bonus(character: Any, rating: str) -> int:
    """Return authored Soulcatcher bonuses from Totem and harvest mastery."""
    if getattr(getattr(character, "cls", None), "name", None) != "Soulcatcher":
        return 0
    bonus = 0
    if active_totem_aspect(character):
        if rating == "weapon" and has_nature_talent(character, "soulcatcher.spirit-warrior"):
            bonus += 10
        if (
            rating == "magic def"
            and active_totem_aspect(character) == "Soul"
            and has_nature_talent(character, "soulcatcher.death-ward")
        ):
            bonus += 15
    try:
        from . import class_rings

        count = len(
            class_rings.ensure_state(character)["data"]["Soulcatcher"].get(
                "harvested_types",
                [],
            )
        )
    except (AttributeError, KeyError, TypeError):
        count = 0
    if (
        rating == "magic"
        and count >= 3
        and has_nature_talent(character, "soulcatcher.varied-harvest")
    ):
        bonus += 10
    if (
        rating == "armor"
        and count >= 5
        and has_nature_talent(character, "soulcatcher.essence-shell")
    ):
        bonus += 10
    if count >= 7 and has_nature_talent(character, "soulcatcher.perfect-vessel"):
        if rating in {"weapon", "magic def"}:
            bonus += 10
    return bonus


def is_nature_totem_class(character: Any) -> bool:
    return getattr(getattr(character, "cls", None), "name", None) in ELIGIBLE_CLASSES


def has_staff_equipped(character: Any) -> bool:
    weapon = getattr(character, "equipment", {}).get("Weapon")
    return getattr(weapon, "subtyp", None) == "Staff"


def active_totem_aspect(character: Any) -> str | None:
    effect = getattr(character, "magic_effects", {}).get("Totem")
    if not effect or not getattr(effect, "active", False):
        return None
    extra = getattr(effect, "extra", None)
    if not isinstance(extra, dict):
        return None
    aspect = extra.get("aspect")
    return str(aspect) if aspect else None


def spell_aspect(spell_or_name: Any) -> str | None:
    name = spell_or_name if isinstance(spell_or_name, str) else getattr(spell_or_name, "name", "")
    return SPELL_TO_ASPECT.get(str(name))


def spell_output_multiplier(character: Any, spell_or_name: Any) -> float:
    multiplier = 1.0
    if hasattr(character, "_totem_pulse_potency"):
        try:
            multiplier = max(0.0, float(getattr(character, "_totem_pulse_potency", 1.0)))
            multiplier *= max(0.0, float(getattr(character, "_totem_surge_output", 1.0)))
            if active_totem_aspect(character) == "Soul":
                from . import class_rings

                multiplier *= 1.0 + class_rings.soul_aspect_bonus(character)
            return multiplier
        except (TypeError, ValueError):
            return multiplier

    aspect = spell_aspect(spell_or_name)
    if aspect and has_staff_equipped(character) and active_totem_aspect(character) == aspect:
        multiplier *= STAFF_MATCHING_CAST_MULTIPLIER
    if aspect and active_totem_aspect(character) == aspect:
        try:
            from . import promotion_kits

            multiplier *= 1.0 + (promotion_kits.totem_resonance(character) * 0.03)
        except Exception:
            pass
    return multiplier


def highest_unlocked_spell_name(character: Any, aspect: str) -> str | None:
    spells = getattr(character, "spellbook", {}).get("Spells", {})
    for name in reversed(ASPECT_SPELL_ORDER.get(aspect, ())):
        if name in spells:
            return name
    return None


def totem_pulse_chance(character: Any) -> float:
    chance = BASE_PULSE_CHANCE
    if has_staff_equipped(character):
        chance += STAFF_PULSE_BONUS
    if has_nature_talent(character, "shaman.steady-pulse"):
        chance += 0.10
    try:
        from . import promotion_kits

        chance += promotion_kits.totem_resonance(character) * 0.05
    except Exception:
        pass
    return min(1.0, chance)


def _set_temp_attr(character: Any, attr: str, value: Any):
    sentinel = object()
    prior = getattr(character, attr, sentinel)
    setattr(character, attr, value)
    return sentinel, prior


def _restore_temp_attr(character: Any, attr: str, sentinel: object, prior: Any) -> None:
    if prior is sentinel:
        try:
            delattr(character, attr)
        except AttributeError:
            pass
    else:
        setattr(character, attr, prior)


def resolve_totem_pulse(character: Any, target: Any, rng: Any = random) -> str:
    if not (
        is_nature_totem_class(character) and target and getattr(target, "is_alive", lambda: False)()
    ):
        return ""
    aspect = active_totem_aspect(character)
    if not aspect:
        return ""
    spell_name = highest_unlocked_spell_name(character, aspect)
    if not spell_name:
        return ""
    if rng.random() >= totem_pulse_chance(character):
        return ""

    spell = character.spellbook.get("Spells", {}).get(spell_name)
    if not spell:
        return ""

    potency = TOTEM_PULSE_POTENCY
    if has_nature_talent(character, "shaman.echoing-totem"):
        potency += 0.10
    if has_nature_talent(character, "soulcatcher.soul-amplifier") and aspect == "Soul":
        potency += 0.10
    sentinel, prior = _set_temp_attr(character, "_totem_pulse_potency", potency)
    try:
        message = f"{character.name}'s {aspect} Totem pulses with {spell_name}.\n"
        resolved = spell.cast(character, target=target, special=True)
        message += str(resolved)
        result = resolved if hasattr(resolved, "damage") else getattr(spell, "result", None)
        successful = bool(
            max(0, int(getattr(result, "damage", 0) or 0))
            or max(0, int(getattr(result, "healing", 0) or 0))
            or getattr(result, "hit", False)
            or any(
                bool(values) for values in (getattr(result, "effects_applied", {}) or {}).values()
            )
        )
        try:
            from . import promotion_kits

            if successful:
                message += promotion_kits.gain_totem_resonance(character, "successful pulse")
        except Exception:
            pass
    finally:
        _restore_temp_attr(character, "_totem_pulse_potency", sentinel, prior)
    return message


def communion_spell_name(aspect: str) -> str | None:
    return COMMUNION_SPELLS.get(aspect)


def unlock_communion(character: Any, aspect: str) -> tuple[bool, str]:
    spell_name = communion_spell_name(aspect)
    if not spell_name:
        return False, ""
    if not is_nature_totem_class(character):
        return False, f"A {aspect.lower()} presence stirs here, but it does not answer your path.\n"

    spells = character.spellbook.setdefault("Spells", {})
    if spell_name in spells:
        return False, f"The {aspect.lower()} presence is already bound to your Totem.\n"

    from src.core import abilities

    spell_cls = getattr(abilities, spell_name.replace(" ", ""), None)
    if spell_cls is None:
        return False, ""
    spells[spell_name] = spell_cls()
    return True, f"{character.name} communes with {aspect.lower()} and learns {spell_name}.\n"


def water_ward_absorb(defender: Any, damage: int) -> tuple[int, str]:
    if damage <= 0 or active_totem_aspect(defender) != "Water":
        return damage, ""
    fraction = WATER_WARD_ABSORB_FRACTION
    if has_nature_talent(defender, "shaman.deep-water"):
        fraction += 0.10
    absorbed = int(damage * fraction)
    if absorbed <= 0:
        return damage, ""
    defender.health.current = min(defender.health.max, defender.health.current + absorbed)
    try:
        defender._emit_healing_event(absorbed, source="Water Totem")
    except Exception:
        pass
    return damage - absorbed, (
        f"{defender.name}'s water totem absorbs {absorbed} spell damage "
        f"and restores {absorbed} health.\n"
    )
