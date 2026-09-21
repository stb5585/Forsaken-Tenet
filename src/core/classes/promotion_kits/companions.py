"""Totem, summon, companion, song, and transformation progression."""

from __future__ import annotations

import math
from typing import Any

from src.core.randomness import gameplay_random as random

from .meters import _preserve_spent_meter, _spend_mp, cap_for, gain_meter
from .state import (
    ADVANCED_SONGS,
    SUMMON_NAMES,
    _clamp_int,
    _cleanse_one_hostile_status,
    _ring_awakened_equipped,
    class_name,
    combat_state,
    ensure_state,
)

XENID_CASTER_EFFECTS = {
    "Hodag": {"strength": 4, "melee": 0.10},
    "Caladrius": {"wisdom": 4, "healing": 0.12},
    "Patagon": {"strength": 3, "melee": 0.10},
    "Kobalos": {"dexterity": 3, "melee": 0.06},
    "Dilong": {"constitution": 3, "armor": 0.08},
    "Cacus": {"strength": 5, "melee": 0.15},
    "Agloolik": {"wisdom": 2, "magic_defense": 0.08},
    "Izulu": {"dexterity": 3, "magic": 0.06},
    "Hala": {"dexterity": 3, "melee": 0.06},
    "Lamashtu": {"charisma": 3, "magic": 0.10},
    "Seraphim": {"wisdom": 4, "healing": 0.12},
    "Bardi": {"intelligence": 4, "magic": 0.10},
    "Tiamat": {"constitution": 4, "armor": 0.08, "magic_defense": 0.08},
    "Zahhak": {"intelligence": 5, "magic": 0.12},
}
XENID_DEATH_CONDUIT_LOSS = 25
XENID_RAISE_CONDUIT_REFUND = 10
XENID_INVOCATIONS = {
    "Hodag": {"types": ("Physical",), "rider": "attack_up"},
    "Caladrius": {"types": ("Holy",), "rider": "heal_cleanse"},
    "Patagon": {"types": ("Physical", "Earth"), "rider": "attack_down"},
    "Dilong": {"types": ("Earth",), "rider": "defense_down"},
    "Agloolik": {"types": ("Ice",), "rider": "defense_up"},
    "Cacus": {"types": ("Fire",), "rider": "burn"},
    "Izulu": {"types": ("Electric",), "rider": "siphon"},
    "Hala": {"types": ("Wind",), "rider": "speed_up"},
    "Lamashtu": {"types": ("Shadow",), "rider": "curse"},
    "Seraphim": {"types": ("Holy",), "rider": "heal"},
    "Bardi": {"types": ("Shadow",), "rider": "blind"},
    "Kobalos": {"types": ("Physical", "Poison"), "rider": "dodge_up"},
    "Tiamat": {"types": ("Water",), "rider": "defense_pressure"},
    "Zahhak": {"types": ("Arcane",), "rider": "magic_defense_up"},
}


def xenid_caster_effects(character: Any) -> dict[str, float]:
    """Return cumulative caster bonuses produced by all chosen Xenid conduits."""
    if class_name(character) != "Thaumaturgist":
        return {}
    state = ensure_state(character)
    choices = getattr(character, "xenid_choices", {})
    if not isinstance(choices, dict):
        return {}
    mastery = False
    progression = getattr(character, "progression", None)
    if progression is not None:
        mastery = "thaumaturgist.talent.conduit-mastery" in getattr(
            progression, "purchased_node_ids", set()
        )
    mastery_scale = 1.5 if mastery else 1.0
    totals: dict[str, float] = {}
    for name in choices.values():
        conduit = int(state["summon_bonds"].get(name, 0) or 0)
        scale = conduit / 100 * mastery_scale
        for effect, maximum in XENID_CASTER_EFFECTS.get(name, {}).items():
            totals[effect] = totals.get(effect, 0.0) + float(maximum) * scale
    return totals


def xenid_caster_attribute_bonus(character: Any, stat_name: str) -> int:
    """Return the conduit-derived virtual primary-attribute bonus."""
    aliases = {
        "strength": "strength",
        "intel": "intelligence",
        "wisdom": "wisdom",
        "con": "constitution",
        "charisma": "charisma",
        "dex": "dexterity",
    }
    return int(xenid_caster_effects(character).get(aliases[stat_name], 0.0))


def xenid_caster_multiplier(character: Any, effect: str) -> float:
    """Return a conduit-derived multiplier for one combat result."""
    return 1.0 + xenid_caster_effects(character).get(effect, 0.0)


ASPECTS = ("Venom", "Stone", "Growth", "Storm")


def _aspect_counts(character: Any) -> dict[str, int]:
    state = combat_state(character)
    raw = state.setdefault("aspect_harmony", {})
    if isinstance(raw, set):
        raw = {str(name): 1 for name in raw if name in ASPECTS}
    elif not isinstance(raw, dict):
        raw = {}
    counts = {
        name: max(0, int(raw.get(name, 0) or 0))
        for name in ASPECTS
        if int(raw.get(name, 0) or 0) > 0
    }
    state["aspect_harmony"] = counts
    return counts


def add_aspect(character: Any, aspect: str, *, incoming: bool = False) -> str:
    if class_name(character) != "Archdruid":
        return ""
    if aspect not in ASPECTS:
        return ""
    state = combat_state(character)
    claim_key = "incoming_claims" if incoming else "action_claims"
    claims = state.setdefault(claim_key, set())
    if not isinstance(claims, set):
        claims = set(claims)
        state[claim_key] = claims
    claim = f"aspect:{aspect}"
    if claim in claims:
        return ""
    claims.add(claim)
    cap = cap_for(character, "aspect_harmony")
    aspects = _aspect_counts(character)
    total = sum(aspects.values())
    if total >= cap:
        return "Aspect Harmony is capped.\n"
    gain = 1
    current_round = int(state.get("action_round", 0) or 0)
    effect = getattr(character, "class_effects", {}).get("Power Up")
    ascendant = bool(
        getattr(character, "power_up", False)
        and "Primal Ascendance" in getattr(character, "spellbook", {}).get("Skills", {})
        and effect is not None
        and effect.active
    )
    if ascendant and state.get("aspect_gain_round") != current_round and total + gain < cap:
        gain += 1
        state["aspect_gain_round"] = current_round
    aspects[aspect] = aspects.get(aspect, 0) + gain
    order = state.setdefault("aspect_harmony_order", [])
    if not isinstance(order, list):
        order = list(order)
        state["aspect_harmony_order"] = order
    order.extend([aspect] * gain)
    suffix = f" (+{gain})" if gain > 1 else ""
    return f"{character.name} represents {aspect} Aspect Harmony{suffix}.\n"


def _surge_typed_damage(character: Any, target: Any, raw: int, damage_type: str) -> tuple[int, str]:
    if target is None or raw <= 0:
        return 0, ""
    hit, reduction, reduced = target.damage_reduction(raw, character, typ=damage_type)
    dealt = max(0, min(int(reduced or 0), int(target.health.current))) if hit else 0
    if dealt:
        target.health.current -= dealt
        character._emit_damage_event(
            target,
            dealt,
            damage_type=damage_type,
            source="promotion_kit_payoff",
            ability_name="Fourfold Surge",
        )
    return dealt, reduction


def fourfold_surge(character: Any, target: Any | None) -> str:
    if class_name(character) != "Archdruid":
        return "Fourfold Surge requires Archdruid training.\n"
    state = combat_state(character)
    aspects = _aspect_counts(character)
    distinct = len(aspects)
    total = sum(aspects.values())
    if distinct < 2:
        return "Fourfold Surge requires at least two represented aspects.\n"
    if not _spend_mp(character, 14):
        return "Not enough MP for Fourfold Surge.\n"
    spent = dict(aspects)
    state["aspect_harmony"] = {}
    order = list(state.get("aspect_harmony_order", []))
    state["aspect_harmony_order"] = []
    msg = f"{character.name} spends {', '.join(sorted(spent))} Aspect Harmony on Fourfold Surge.\n"
    power = 1.15 if distinct == 4 else 1.0
    effect = getattr(character, "class_effects", {}).get("Power Up")
    if (
        getattr(character, "power_up", False)
        and "Primal Ascendance" in getattr(character, "spellbook", {}).get("Skills", {})
        and effect is not None
        and effect.active
    ):
        power *= 1.20
    clean = False
    offensive = [name for name in ("Venom", "Storm") if name in spent]
    if target is not None and offensive:
        budget = max(
            1, int(character.check_mod("magic", enemy=target) * (0.35 + 0.15 * total) * power)
        )
        portions = [budget // len(offensive)] * len(offensive)
        portions[0] += budget - sum(portions)
        for name, raw in zip(offensive, portions):
            damage_type = "Poison" if name == "Venom" else "Electric"
            immune = float(getattr(target, "resistance", {}).get(damage_type, 0.0) or 0.0) >= 1.0
            if name == "Venom" and immune:
                damage_type = "Nature"
                raw = max(1, raw // 2)
            dealt, reduction = _surge_typed_damage(character, target, raw, damage_type)
            msg += reduction
            msg += f"{name} deals {dealt} {damage_type} damage.\n"
            clean = clean or dealt > 0
            boss = bool(getattr(target, "boss", False) or getattr(target, "is_boss", False))
            if (
                name == "Venom"
                and dealt > 0
                and not immune
                and not boss
                and not target.has_status_protection("Poison")
            ):
                poison = target.status_effects["Poison"]
                poison.active = True
                poison.duration = max(poison.duration, 2)
                poison.extra = max(int(poison.extra or 0), max(1, dealt // 6))
                msg += f"Venom poisons {target.name} for two turns.\n"
            if name == "Storm" and dealt > 0 and not boss:
                speed = target.stat_effects["Speed"]
                speed.active = True
                speed.duration = max(speed.duration, 2)
                speed.extra = min(int(speed.extra or 0), -3 * spent["Storm"])
                msg += f"Storm slows {target.name}.\n"
    if "Growth" in spent:
        growth_power = power
        tree = getattr(character, "magic_effects", {}).get("Tree of Life")
        if tree is not None and tree.active:
            growth_power *= 1.25
        heal = min(
            character.health.max - character.health.current, int((10 + 5 * total) * growth_power)
        )
        character.health.current += heal
        msg += f"Growth restores {heal} HP.\n"
        clean = clean or heal > 0
        if distinct >= 3:
            cleansed = _cleanse_one_hostile_status(character)
            if cleansed:
                clean = True
                msg += f"Growth cleanses {cleansed}.\n"
    if "Stone" in spent:
        character.stat_effects["Defense"].active = True
        character.stat_effects["Defense"].duration = 2
        character.stat_effects["Defense"].extra = max(
            int(character.stat_effects["Defense"].extra or 0), int(5 * total * power)
        )
        ward = character.magic_effects["Nature Shield"]
        ward.active = True
        ward.duration = max(ward.duration, 2)
        ward.extra = max(int(ward.extra or 0), int(6 * spent["Stone"] * power))
        clean = True
        msg += "Stone hardens the caster's defense.\n"
    preservation_key = "Archdruid:aspect_harmony"
    preserved_flags = state.setdefault("ring_preserved", set())
    if (
        clean
        and _ring_awakened_equipped(character, "Archdruid")
        and preservation_key not in preserved_flags
    ):
        preserved = next((name for name in reversed(order) if name in spent), sorted(spent)[0])
        state["aspect_harmony"] = {preserved: 1}
        state["aspect_harmony_order"] = [preserved]
        preserved_flags.add(preservation_key)
        msg += f"Harmony Bonus preserves {preserved} Aspect Harmony.\n"
    return msg


def totem_resonance(character: Any) -> int:
    effect = getattr(character, "magic_effects", {}).get("Totem")
    if not effect or not effect.active or not isinstance(effect.extra, dict):
        return 0
    return max(0, int(effect.extra.get("resonance", 0) or 0))


def gain_totem_resonance(character: Any, reason: str) -> str:
    effect = getattr(character, "magic_effects", {}).get("Totem")
    if not effect or not effect.active or not isinstance(effect.extra, dict):
        return ""
    cap = cap_for(character, "totem_resonance")
    before = totem_resonance(character)
    effect.extra["resonance"] = min(cap, before + 1)
    if effect.extra["resonance"] == before:
        return "Totem Resonance is capped.\n"
    return f"{character.name}'s Totem gains Resonance from {reason} ({effect.extra['resonance']}/{cap}).\n"


def totem_surge(character: Any, target: Any | None) -> str:
    from .. import nature_totems

    aspect = nature_totems.active_totem_aspect(character)
    stacks = totem_resonance(character)
    if not aspect:
        return "Totem Surge requires an active Totem.\n"
    if stacks <= 0:
        return "Totem Surge requires Totem Resonance.\n"
    spell_name = nature_totems.highest_unlocked_spell_name(character, aspect)
    if not spell_name:
        return "No known spell matches the active Totem.\n"
    if target is None:
        return "Totem Surge needs a target.\n"
    if not _spend_mp(character, 10):
        return "Not enough MP for Totem Surge.\n"
    spell = character.spellbook.get("Spells", {}).get(spell_name)
    if not spell:
        return "No known spell matches the active Totem.\n"
    effect = character.magic_effects["Totem"]
    preserve = (
        nature_totems.has_nature_talent(character, "soulcatcher.resonant-return")
        and random.random() < 0.25
    )
    effect.extra["resonance"] = 1 if preserve else 0
    potency = nature_totems.TOTEM_PULSE_POTENCY
    if nature_totems.has_nature_talent(character, "soulcatcher.perfect-surge"):
        potency += 0.10
    sentinel, prior = nature_totems._set_temp_attr(character, "_totem_pulse_potency", potency)
    output_sentinel, output_prior = nature_totems._set_temp_attr(
        character,
        "_totem_surge_output",
        1.10 if _ring_awakened_equipped(character, "Soulcatcher") else 1.0,
    )
    reliability_sentinel, reliability_prior = nature_totems._set_temp_attr(
        character,
        "_totem_surge_reliability",
        0.10 if _ring_awakened_equipped(character, "Soulcatcher") else 0.0,
    )
    try:
        msg = f"{character.name} spends {stacks} Totem Resonance to force {spell_name}.\n"
        if preserve:
            msg += "Resonant Return preserves 1 Totem Resonance.\n"
        msg += str(spell.cast(character, target=target, special=True))
    finally:
        nature_totems._restore_temp_attr(character, "_totem_pulse_potency", sentinel, prior)
        nature_totems._restore_temp_attr(
            character, "_totem_surge_output", output_sentinel, output_prior
        )
        nature_totems._restore_temp_attr(
            character,
            "_totem_surge_reliability",
            reliability_sentinel,
            reliability_prior,
        )
    return msg


def gain_summon_bond_for_active(character: Any, amount: int, reason: str) -> str:
    summon = getattr(character, "active_summon_name", None)
    if not summon:
        return ""
    return gain_summon_bond(character, str(summon), amount, reason)


def record_xenid_death(character: Any, summon_name: str) -> str:
    """Apply one conduit penalty and remember the fallen active Xenid."""
    if class_name(character) != "Thaumaturgist" or summon_name not in SUMMON_NAMES:
        return ""
    combat = combat_state(character)
    if combat.get("fallen_xenid") == summon_name:
        return ""
    message = clear_conduit_command(character, "falls")
    state = ensure_state(character)
    before = int(state["summon_bonds"].get(summon_name, 0) or 0)
    after = max(0, before - XENID_DEATH_CONDUIT_LOSS)
    loss = before - after
    state["summon_bonds"][summon_name] = after
    combat["fallen_xenid"] = summon_name
    combat["fallen_xenid_conduit_loss"] = loss
    from ... import companions

    companions.sync_xenid_conduit(character, summon_name, after)
    message += (
        f"{summon_name}'s death weakens its conduit by {loss} " f"({after}/100).\n"
        if loss
        else f"{summon_name}'s conduit cannot weaken any further.\n"
    )
    return message


def raise_fallen_xenid(
    character: Any,
    battle_engine: Any | None,
    *,
    health_fraction: float = 0.25,
) -> tuple[bool, str]:
    """Raise only the Xenid that fell while active in the current combat."""
    if class_name(character) != "Thaumaturgist":
        return False, "Raise Summon requires Thaumaturgist training.\n"
    if battle_engine is None or not bool(getattr(character, "_active_combat", False)):
        return False, "Raise Summon can only be used during combat.\n"
    combat = combat_state(character)
    summon_name = str(combat.get("fallen_xenid", "") or "")
    summons = getattr(character, "summons", {}) or {}
    summon = summons.get(summon_name)
    if summon is None or summon.health.current > 0:
        return False, "No fallen active Xenid can be raised.\n"

    state = ensure_state(character)
    loss = max(0, int(combat.get("fallen_xenid_conduit_loss", 0) or 0))
    refund = min(XENID_RAISE_CONDUIT_REFUND, loss)
    conduit = int(state["summon_bonds"].get(summon_name, 0) or 0)
    conduit = min(100, conduit + refund)
    state["summon_bonds"][summon_name] = conduit
    from ... import companions

    companions.sync_xenid_conduit(character, summon_name, conduit)
    summon.health.current = max(
        1,
        int(summon.health.max * max(0.01, float(health_fraction))),
    )
    battle_engine.summon = summon
    battle_engine.summon_active = True
    character.active_summon_name = summon_name
    combat["fallen_xenid"] = None
    combat["fallen_xenid_conduit_loss"] = 0
    battle_engine.available_actions = battle_engine._available_actions()
    return True, (
        f"{summon_name} returns with {summon.health.current} HP. The rite "
        f"restores {refund} of the lost conduit ({conduit}/100).\n"
    )


def summon_level_span_xp(summon: Any) -> int:
    level = getattr(summon, "level", None)
    try:
        creature_level = max(1, int(getattr(level, "level", 1) or 1))
    except (TypeError, ValueError):
        creature_level = 1
    try:
        pro_level = max(1, int(getattr(level, "pro_level", 1) or 1))
    except (TypeError, ValueError):
        pro_level = 1
    try:
        exp_scale = max(1, int(getattr(summon, "exp_scale", 1000) or 1000))
    except (TypeError, ValueError):
        exp_scale = 1000
    return max(1, pro_level * exp_scale * creature_level)


def summon_bond_gain_for_victory(
    character: Any,
    exp_gain: int,
    *,
    guaranteed: bool = False,
    multiplier: int = 1,
) -> int:
    summon_name = getattr(character, "active_summon_name", None)
    try:
        exp_gain = max(0, int(exp_gain))
    except (TypeError, ValueError):
        exp_gain = 0
    if exp_gain <= 0:
        setattr(
            character,
            "_active_summon_bond_note",
            f"{summon_name or 'Summon'} bond sees no eligible XP.",
        )
        return 0
    global_level = getattr(
        getattr(character, "progression", None),
        "level",
        getattr(getattr(character, "level", None), "level", 1),
    )
    level_span = max(50, int(global_level or 1) * 20)
    ratio = max(0.0, float(exp_gain) / float(level_span))
    chance = min(1.0, ratio)
    if chance < 1.0 and not guaranteed and random.random() >= chance:
        setattr(
            character,
            "_active_summon_bond_note",
            f"{summon_name or 'Summon'} conduit holds steady after a low-XP victory.",
        )
        return 0
    gain = max(1, min(5, int(math.ceil(ratio * 5))))
    try:
        multiplier = max(1, int(multiplier))
    except (TypeError, ValueError):
        multiplier = 1
    setattr(character, "_active_summon_bond_note", "")
    return min(10, gain * multiplier)


def gain_summon_bond(character: Any, summon_name: str, amount: int, reason: str) -> str:
    if class_name(character) != "Thaumaturgist" or summon_name not in SUMMON_NAMES:
        return ""
    state = ensure_state(character)
    before = int(state["summon_bonds"].get(summon_name, 0) or 0)
    after = min(100, before + max(0, int(amount)))
    state["summon_bonds"][summon_name] = after
    from ... import companions

    companions.sync_xenid_conduit(character, summon_name, after)
    sync_xenid_invocations(character)
    if after == before:
        note = str(getattr(character, "_active_summon_bond_note", "") or "")
        return f"Xenid Conduit: {note}\n" if note else ""
    return f"{summon_name}'s conduit grows by {after - before} from {reason} " f"({after}/100).\n"


def sync_xenid_invocations(character: Any) -> None:
    """Grant borrowed invocation skills for conduits that reached trust."""
    if class_name(character) != "Thaumaturgist":
        return
    from ... import abilities

    skills = getattr(character, "spellbook", {}).setdefault("Skills", {})
    bonds = ensure_state(character)["summon_bonds"]
    for summon_name, bond in bonds.items():
        if int(bond or 0) < 50:
            continue
        ability_type = getattr(abilities, f"Invoke{summon_name}", None)
        if ability_type is None:
            continue
        invocation = ability_type()
        skills.setdefault(invocation.name, invocation)


def summon_bond_multiplier(character: Any, summon_name: str) -> float:
    bond = int(ensure_state(character)["summon_bonds"].get(summon_name, 0) or 0)
    return 1.0 + 0.25 * bond / 100


def _apply_temporary_stat(
    character: Any,
    stat_name: str,
    amount: int,
    *,
    duration: int = 2,
) -> None:
    effect = getattr(character, "stat_effects", {}).get(stat_name)
    if effect is None:
        return
    effect.active = True
    effect.duration = max(duration, int(getattr(effect, "duration", 0) or 0))
    current = int(getattr(effect, "extra", 0) or 0)
    effect.extra = amount if abs(amount) > abs(current) else current


def _resolve_invocation_damage(
    character: Any,
    target: Any,
    raw_damage: int,
    damage_types: tuple[str, ...],
) -> tuple[int, str]:
    total = 0
    messages = ""
    shares = [raw_damage // len(damage_types)] * len(damage_types)
    shares[0] += raw_damage - sum(shares)
    for damage_type, share in zip(damage_types, shares):
        hit, defense_message, defended = target.handle_defenses(
            character,
            max(1, share),
            typ=damage_type,
        )
        messages += defense_message
        if not hit or defended <= 0:
            continue
        hit, reduction_message, final_damage = target.damage_reduction(
            defended,
            character,
            typ=damage_type,
        )
        messages += reduction_message
        if not hit or final_damage <= 0:
            continue
        applied = min(int(target.health.current), max(0, int(final_damage)))
        target.health.current = max(0, int(target.health.current) - applied)
        total += applied
        if applied:
            character._emit_damage_event(
                target,
                applied,
                damage_type,
                source="Xenid invocation",
                attack_source="skill",
                ability_name="Invoke Xenid",
            )
    return total, messages


def _apply_xenid_signature_rider(
    actor: Any,
    target: Any | None,
    summon_name: str,
    damage: int,
    *,
    lesser: bool = False,
) -> str:
    definition = XENID_INVOCATIONS.get(summon_name, {})
    rider = definition.get("rider")
    scale = 0.5 if lesser else 1.0
    label = "True Name" if lesser else f"Invoke {summon_name}"
    if rider == "attack_up":
        amount = max(1, int(actor.stats.strength * 0.15 * scale))
        _apply_temporary_stat(actor, "Attack", amount)
        return f"{label} briefly strengthens {actor.name}'s Attack.\n"
    if rider in {"heal", "heal_cleanse"}:
        healing = min(
            max(0, int(actor.health.max) - int(actor.health.current)),
            max(1, int(actor.health.max * 0.05 * scale)),
        )
        actor.health.current += healing
        message = f"{label} restores {healing} HP to {actor.name}.\n" if healing else ""
        if rider == "heal_cleanse":
            cleansed = _cleanse_one_hostile_status(actor)
            if cleansed:
                message += f"{label} cleanses {cleansed}.\n"
        return message
    if rider == "attack_down" and target is not None and damage > 0:
        amount = -max(1, int(target.stats.strength * 0.10 * scale))
        _apply_temporary_stat(target, "Attack", amount)
        return f"{label} briefly suppresses {target.name}'s Attack.\n"
    if rider in {"defense_down", "defense_pressure"} and target is not None and damage > 0:
        amount = -max(1, int(target.stats.con * 0.10 * scale))
        _apply_temporary_stat(target, "Defense", amount)
        return f"{label} briefly erodes {target.name}'s Defense.\n"
    if rider == "defense_up":
        amount = max(1, int(actor.stats.con * 0.10 * scale))
        _apply_temporary_stat(actor, "Defense", amount)
        return f"{label} briefly strengthens {actor.name}'s Defense.\n"
    if rider == "burn" and target is not None and damage > 0:
        dot = getattr(target, "magic_effects", {}).get("DOT")
        if dot is not None:
            dot.active = True
            dot.duration = max(2, int(getattr(dot, "duration", 0) or 0))
            pressure = max(1, int(damage * 0.10 * scale))
            dot.extra = max(int(getattr(dot, "extra", 0) or 0), pressure)
            dot.source = "Burn"
            return f"{label} leaves burning pressure on {target.name}.\n"
    if rider == "siphon" and damage > 0:
        healing = min(
            max(0, int(actor.health.max) - int(actor.health.current)),
            max(1, int(damage * 0.20 * scale)),
        )
        actor.health.current += healing
        return f"{label} siphons {healing} HP to {actor.name}.\n" if healing else ""
    if rider in {"speed_up", "dodge_up"}:
        amount = max(1, int(actor.stats.dex * 0.10 * scale))
        _apply_temporary_stat(actor, "Speed", amount)
        support = "evasion" if rider == "dodge_up" else "Speed"
        return f"{label} briefly improves {actor.name}'s {support}.\n"
    if rider == "curse" and target is not None and damage > 0:
        if random.random() < (0.15 if lesser else 0.30):
            from ... import persistent_afflictions as afflictions

            return afflictions.apply_curse(
                target,
                "Umbra",
                source=label,
                caster=actor,
            )
    if rider == "blind" and target is not None and damage > 0:
        if random.random() < (0.15 if lesser else 0.30):
            blind = getattr(target, "status_effects", {}).get("Blind")
            if blind is not None:
                blind.active = True
                blind.duration = max(2, int(getattr(blind, "duration", 0) or 0))
                blind.source = label
                return f"{label} blinds {target.name}.\n"
    if rider == "magic_defense_up":
        amount = max(1, int(actor.stats.wisdom * 0.10 * scale))
        _apply_temporary_stat(actor, "Magic Defense", amount)
        return f"{label} briefly strengthens {actor.name}'s Magic Defense.\n"
    return ""


def invoke_summon(character: Any, target: Any | None, summon_name: str) -> str:
    if class_name(character) != "Thaumaturgist":
        return "Only a Thaumaturgist can borrow a Xenid invocation.\n"
    bond = int(ensure_state(character)["summon_bonds"].get(summon_name, 0) or 0)
    if bond < 50:
        return f"{summon_name} has not entrusted this invocation yet.\n"
    if target is None:
        return "There is no invocation target.\n"
    if not _spend_mp(character, 12):
        return "Not enough MP for the invocation.\n"
    definition = XENID_INVOCATIONS.get(summon_name)
    if definition is None:
        return f"Invoke {summon_name} has no bound Xenid signature.\n"
    raw_damage = max(1, int(character.check_mod("magic", enemy=target) * 0.55))
    damage_types = tuple(definition["types"])
    damage, defense_message = _resolve_invocation_damage(
        character,
        target,
        raw_damage,
        damage_types,
    )
    type_text = "/".join(damage_types)
    message = defense_message
    message += (
        f"{character.name} invokes {summon_name}: {type_text} pressure deals " f"{damage} damage.\n"
    )
    message += _apply_xenid_signature_rider(
        character,
        target,
        summon_name,
        damage,
    )
    return message


def conduit_command(character: Any) -> str:
    if class_name(character) != "Thaumaturgist":
        return "Conduit Command requires Thaumaturgist training.\n"
    summon_name = str(getattr(character, "active_summon_name", "") or "")
    summon = getattr(character, "summons", {}).get(summon_name)
    if summon is None or not summon.is_alive() or summon_name not in SUMMON_NAMES:
        return "Conduit Command requires an active living Xenid.\n"
    if not _spend_mp(character, 10):
        return "Not enough MP for Conduit Command.\n"
    combat_state(character)["conduit_command"] = {"summon_name": summon_name}
    return f"{character.name} empowers the active Xenid's next action with Conduit Command.\n"


def begin_conduit_payoff(
    character: Any,
    summon: Any,
    action: str,
    target: Any | None,
) -> dict[str, Any] | None:
    """Consume a primed command and snapshot its committed Xenid action."""
    if action in {"Recall", "Support", "Nothing", "Cancelled"}:
        return None
    state = combat_state(character)
    command = state.get("conduit_command")
    if not isinstance(command, dict):
        return None
    summon_name = str(getattr(summon, "name", "") or "")
    if command.get("summon_name") != summon_name:
        return None
    state["conduit_command"] = False
    bond = int(ensure_state(character)["summon_bonds"].get(summon_name, 0) or 0)
    return {
        "consumed": True,
        "summon_name": summon_name,
        "target_health": int(target.health.current) if target is not None else None,
        "summon_health": int(summon.health.current),
        "owner_health": int(character.health.current),
        "true_name": bond >= 100 and _ring_awakened_equipped(character, "Thaumaturgist"),
    }


def finish_conduit_payoff(
    character: Any,
    summon: Any,
    target: Any | None,
    payoff: dict[str, Any] | None,
    combat_result: Any | None = None,
) -> str:
    """Apply command output and the optional True Name signature rider."""
    if not isinstance(payoff, dict) or not payoff.get("consumed"):
        return ""
    damage = 0
    damage_bonus = 0
    target_before = payoff.get("target_health")
    if target is not None and target_before is not None:
        damage = max(0, int(target_before) - int(target.health.current))
        if damage > 0 and target.is_alive():
            requested = max(1, int(damage * 0.25))
            damage_bonus = min(int(target.health.current), requested)
            target.health.current -= damage_bonus
    healing_bonus = 0
    healed_targets = []
    for recipient, before_key in (
        (summon, "summon_health"),
        (character, "owner_health"),
    ):
        before = int(payoff.get(before_key, recipient.health.current) or 0)
        healing = max(0, int(recipient.health.current) - before)
        if healing <= 0:
            continue
        bonus = min(
            max(0, int(recipient.health.max) - int(recipient.health.current)),
            max(1, int(healing * 0.25)),
        )
        if bonus:
            recipient.health.current += bonus
            healing_bonus += bonus
            healed_targets.append(recipient.name)
    if combat_result is not None:
        if damage_bonus:
            prior_damage = max(
                0,
                int(getattr(combat_result, "damage", 0) or 0),
            )
            combat_result.damage = prior_damage + damage_bonus
        if healing_bonus:
            prior_healing = max(
                0,
                int(getattr(combat_result, "healing", 0) or 0),
            )
            combat_result.healing = prior_healing + healing_bonus
        extra = getattr(combat_result, "extra", None)
        if isinstance(extra, dict):
            extra["conduit_command"] = {
                "consumed": True,
                "damage_bonus": damage_bonus,
                "healing_bonus": healing_bonus,
                "true_name": bool(payoff.get("true_name")),
            }
    message = "Conduit Command is consumed by the Xenid action.\n"
    if damage_bonus:
        message += f"Conduit Command adds {damage_bonus} damage.\n"
    if healing_bonus:
        message += (
            f"Conduit Command restores {healing_bonus} additional HP to "
            f"{', '.join(healed_targets)}.\n"
        )
    if payoff.get("true_name"):
        rider = _apply_xenid_signature_rider(
            summon,
            target,
            str(payoff.get("summon_name") or ""),
            damage + damage_bonus,
            lesser=True,
        )
        if rider:
            message += f"True Name answers the command.\n{rider}"
    else:
        rider = ""
    payoff.update(
        {
            "damage_bonus": damage_bonus,
            "healing_bonus": healing_bonus,
            "signature_rider": rider,
            "cleanup_reason": "next Xenid action",
        }
    )
    return message


def clear_conduit_command(character: Any, reason: str) -> str:
    """Expire an unspent Conduit Command for a lifecycle reason."""
    state = combat_state(character)
    if not state.get("conduit_command"):
        return ""
    state["conduit_command"] = False
    return f"Conduit Command expires when the Xenid {reason}.\n"


def companion_bond_rank(bond: int) -> str:
    if bond >= 100:
        return "True Bond"
    if bond >= 75:
        return "Packmate"
    if bond >= 50:
        return "Battle-Trained"
    if bond >= 25:
        return "Trusted"
    return "New Bond"


def companion_bond_gain_roll(current_bond: int, amount: int, *, rng: Any = random) -> int:
    """Return inverse-scaled tamed companion bond gain for this opportunity."""
    current = _clamp_int(current_bond, 0, 100)
    base = max(0, int(amount or 0))
    if base <= 0 or current >= 100:
        return 0
    chance = max(0.15, 1.0 - (current / 110.0))
    if rng.random() >= chance:
        return 0
    scale = max(0.25, 1.0 - (current / 125.0))
    return max(1, min(base, int(round(base * scale))))


def gain_companion_bond(
    character: Any, amount: int, reason: str, *, rng: Any = random, announce: bool = True
) -> str:
    if class_name(character) not in {"Ranger", "Beast Master"}:
        return ""
    state = getattr(character, "tamed_companion", None)
    if not isinstance(state, dict) or not state.get("active"):
        return ""
    before = _clamp_int(state.get("bond", 0), 0, 100)
    gain = companion_bond_gain_roll(before, amount, rng=rng)
    if gain <= 0:
        return ""
    after = min(100, before + gain)
    state["bond"] = after
    if after == before:
        return ""
    evolution_msg = ""
    try:
        from .. import ability_mechanics

        enemy_class = state.get("enemy_class")
        species = state.get("species")
        before_evolution = ability_mechanics.tamed_companion_evolution_for_bond(
            before, enemy_class, species
        )
        after_evolution = ability_mechanics.tamed_companion_evolution_for_bond(
            after, enemy_class, species
        )
        state["evolution"] = after_evolution
        roster = state.get("companions", [])
        active_index = state.get("active_index")
        if (
            isinstance(roster, list)
            and isinstance(active_index, int)
            and 0 <= active_index < len(roster)
        ):
            roster[active_index]["bond"] = after
            roster[active_index]["evolution"] = after_evolution
            roster[active_index]["active"] = True
        familiar = getattr(character, "familiar", None)
        if familiar is not None and getattr(familiar, "spec", "") == "Tamed":
            familiar.bond = after
            familiar.evolution = after_evolution
        if after_evolution != before_evolution:
            evolution_msg = f"{state.get('name') or 'Companion'} evolves into {after_evolution}.\n"
    except Exception:
        pass
    bond_msg = f"{state.get('name') or 'Companion'} bond increased.\n" if announce else ""
    return f"{bond_msg}{evolution_msg}"


def companion_bond_multiplier(character: Any) -> float:
    from ...progression import has_talent

    state = getattr(character, "tamed_companion", {}) or {}
    bond = _clamp_int(state.get("bond", 0), 0, 100)
    coefficient = 0.15
    if has_talent(character, "ranger.companion-bond"):
        coefficient += 0.05
    if has_talent(character, "beast-master.bonded-bulwark"):
        coefficient += 0.10
    if has_talent(character, "beast-master.true-bond"):
        coefficient += 0.10
    return 1.0 + (coefficient * (bond / 100))


def record_song_turn(character: Any, song: str) -> str:
    if class_name(character) not in {"Bard", "Troubadour"}:
        return ""
    from ...progression import has_talent

    state = combat_state(character)
    amount = 1
    if has_talent(character, "bard.rising-cadence") and int(state.get("crescendo", 0) or 0) == 0:
        amount += 1
    if has_talent(character, "troubadour.rolling-crescendo"):
        amount += 1
    msg = gain_meter(character, "crescendo", amount, f"Song of {song}")
    if class_name(character) == "Troubadour":
        msg += gain_bard_practice(character, song, 1, "performed turn")
        if has_talent(character, "troubadour.practiced-ear"):
            msg += gain_bard_practice(character, song, 1, "Practiced Ear")
    return msg


def clear_crescendo(character: Any, reason: str = "") -> str:
    if class_name(character) not in {"Bard", "Troubadour"}:
        return ""
    state = combat_state(character)
    if int(state.get("crescendo", 0) or 0) <= 0:
        return ""
    state["crescendo"] = 0
    suffix = f" from {reason}" if reason else ""
    return f"Crescendo clears{suffix}.\n"


def gain_bard_practice(character: Any, song: str, amount: int, reason: str) -> str:
    if class_name(character) != "Troubadour" or song not in ADVANCED_SONGS:
        return ""
    entry = ensure_state(character)["bard_repertoire"][song]
    before_xp = int(entry.get("practice_xp", 0) or 0)
    before_known = bool(entry.get("known", False))
    entry["practice_xp"] = min(999, before_xp + max(0, int(amount)))
    msg = ""
    if entry["practice_xp"] > before_xp:
        msg += f"{song} gains {entry['practice_xp'] - before_xp} practice XP from {reason} ({entry['practice_xp']}/18).\n"
    if (
        not before_known
        and entry["practice_xp"] >= 18
        and int(entry.get("clean_finishes", 0) or 0) >= 3
    ):
        entry["known"] = True
        msg += f"{character.name} masters {song} as permanent repertoire.\n"
    return msg


def complete_song(character: Any, song: str) -> str:
    if class_name(character) not in {"Bard", "Troubadour"}:
        return ""
    from ...progression import has_talent

    msg = ""
    if class_name(character) == "Troubadour" and song in ADVANCED_SONGS:
        entry = ensure_state(character)["bard_repertoire"][song]
        entry["clean_finishes"] = min(999, int(entry.get("clean_finishes", 0) or 0) + 1)
        msg += f"{song} records a clean finish ({entry['clean_finishes']}/3).\n"
        completion_xp = 5 if has_talent(character, "troubadour.flawless-form") else 3
        msg += gain_bard_practice(character, song, completion_xp, "natural completion")

    state = combat_state(character)
    spent = int(state.get("crescendo", 0) or 0)
    if spent <= 0:
        return msg
    state["crescendo"] = 0
    effective_spent = spent
    if has_talent(character, "bard.coda-craft"):
        effective_spent += 1
    if has_talent(character, "troubadour.masterful-finale"):
        effective_spent += 1
    msg += f"{character.name} spends {spent} Crescendo on a {song} coda.\n"
    if song == "Valor":
        if has_talent(character, "troubadour.heroic-finale"):
            effective_spent += 1
        for stat_name in ("Attack", "Magic"):
            effect = character.stat_effects[stat_name]
            effect.active = True
            effect.duration = max(effect.duration, 2)
            effect.extra = max(int(effect.extra or 0), effective_spent * 2)
        msg += "The Valor coda primes the next offensive phrase.\n"
    elif song == "Shelter":
        if has_talent(character, "troubadour.guardian-finale"):
            effective_spent += 1
        effect = character.magic_effects["Nature Shield"]
        effect.active = True
        effect.duration = max(effect.duration, 2)
        effect.extra = max(int(effect.extra or 0), effective_spent * 10)
        msg += "The Shelter coda leaves a brief ward.\n"
    elif song == "Renewal":
        if has_talent(character, "troubadour.reviving-finale"):
            effective_spent += 1
        hp = min(character.health.max - character.health.current, max(1, effective_spent * 8))
        mp = min(character.mana.max - character.mana.current, max(1, effective_spent * 4))
        character.health.current += hp
        character.mana.current += mp
        cleanse_at = 2 if has_talent(character, "troubadour.reviving-finale") else 3
        if spent >= cleanse_at and character.status_effects["Poison"].active:
            character.status_effects["Poison"].active = False
            msg += "The Renewal coda cleanses poison.\n"
        msg += f"The Renewal coda restores {hp} HP and {mp} MP.\n"
    elif song == "Battle Hymn":
        berserk = character.status_effects["Berserk"]
        berserk.active = True
        bonus = 1 if has_talent(character, "troubadour.riotous-finale") else 0
        berserk.duration = max(berserk.duration, 1 + effective_spent // 2 + bonus)
        msg += "The Battle Hymn coda keeps one controlled offensive beat.\n"
    elif song == "Ode to the Ramparts":
        effect = character.magic_effects["Nature Shield"]
        effect.active = True
        effect.duration = max(effect.duration, 2)
        effect.extra = max(int(effect.extra or 0), effective_spent * 12)
        msg += "The Ramparts coda hardens into a small barrier.\n"
    elif song == "Chorus Time":
        state["chorus_time_coda"] = effective_spent
        msg += "The Chorus Time coda readies one final reduced tempo check.\n"
    else:
        msg += "The final refrain lingers as a conservative coda.\n"
    return _preserve_spent_meter(character, "crescendo", "Troubadour", "Encore", msg)


def beast_command(character: Any, command: str) -> str:
    from .. import ability_mechanics

    if class_name(character) != "Beast Master":
        return f"{command} requires Beast Master training.\n"
    if command not in ability_mechanics.BEAST_COMPANION_COMMANDS:
        return f"{command} is not a known companion command.\n"
    if not ability_mechanics.has_living_tamed_companion(character):
        return f"{command} requires a living tamed companion.\n"
    if command not in ability_mechanics.available_beast_companion_commands(character):
        return f"{character.name} has not learned {command}.\n"
    combat_state(character)["pending_companion_command"] = command
    return f"{character.name} orders their companion: {command}.\n"


def favorite_enemy_type(character: Any) -> str | None:
    try:
        from .. import ability_mechanics

        return ability_mechanics.favorite_enemy_type(character)
    except Exception:
        return None


def lycan_control_state(character: Any) -> dict[str, Any]:
    return ensure_state(character)["lycan_control"]


def record_lycan_stress(character: Any, reason: str, *, survived: bool = True) -> str:
    if class_name(character) != "Lycan":
        return ""
    control = lycan_control_state(character)
    control["stress_events"] += 1
    if survived:
        progress = control["rank_progress"]
        progress[reason] = int(progress.get(reason, 0) or 0) + 1
        _maybe_advance_lycan_rank(control)
    return f"Lycan control records {reason} stress at rank {control['rank']}.\n"


def _maybe_advance_lycan_rank(control: dict[str, Any]) -> None:
    rank = control["rank"]
    progress = control["rank_progress"]
    gates = {
        "Feral": ("survive", "Muzzled", 3),
        "Muzzled": ("dismiss", "Restive", 3),
        "Restive": ("resist", "Tethered", 3),
        "Tethered": ("safe_dismiss", "Tame", 3),
    }
    gate = gates.get(rank)
    if gate and int(progress.get(gate[0], 0) or 0) >= gate[2]:
        control["rank"] = gate[1]


def unlock_dragon_essence(character: Any) -> str:
    if class_name(character) != "Lycan":
        return ""
    lycan_control_state(character)["dragon_essence"] = True
    return "Dragon Essence settles into the Werewolf form.\n"


def winged_pounce(character: Any, target: Any | None) -> str:
    from .. import lycan

    if class_name(character) != "Lycan":
        return "Winged Pounce requires Lycan training.\n"
    if "Winged Pounce" not in character.spellbook.get("Skills", {}):
        return "Winged Pounce has not been learned.\n"
    if not lycan.is_transformed(character) or getattr(character.cls, "name", "") != "Werewolf":
        return "Winged Pounce requires the Werewolf form.\n"
    if not lycan_control_state(character).get("dragon_essence"):
        return "Winged Pounce requires Dragon Essence.\n"
    if target is None:
        return "There is no target for Winged Pounce.\n"
    if int(character.mana.current) < 12:
        return "Not enough mana for Winged Pounce.\n"
    character.mana.current -= 12
    msg, _hit, _crit = character.weapon_damage(target, dmg_mod=1.35, use_offhand=False)
    state = combat_state(character)
    state["winged_pounce_previous_flying"] = bool(character.flying)
    state["winged_pounce_flight"] = 1
    character.flying = True
    return f"{character.name} launches a Winged Pounce.\n{msg}"


PRESERVATION_METERS = {
    "Crusader": ("oath_conviction",),
    "Rogue": ("fortune", "misfortune"),
    "Ninja": ("death_marks",),
    "Arcane Trickster": ("stolen_charge",),
    "Templar": ("devotion",),
    "Hierophant": ("devotion",),
    "Archbishop": ("prayer",),
    "Archdruid": ("aspect_harmony",),
    "Troubadour": ("crescendo",),
}
