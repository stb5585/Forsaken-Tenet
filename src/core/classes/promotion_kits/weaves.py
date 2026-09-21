"""Knight Enchanter Foundation and Accent weave mechanics."""

from __future__ import annotations

from typing import Any

from src.core.randomness import gameplay_random as random

from .state import (
    _has_skill,
    _ring_awakened_equipped,
    class_name,
    combat_state,
)

WEAVE_SIGNATURES = ("Element", "Force", "Protection", "Conjuration")

_FOUNDATION_PREVIEWS = {
    "Element": "volatile damage",
    "Force": "defense break",
    "Protection": "temporary ward",
    "Conjuration": "duplicated edge",
}
_ACCENT_PREVIEWS = {
    "Element": "added power",
    "Force": "deeper break",
    "Protection": "returned ward",
    "Conjuration": "echoed effect",
}

_ELEMENTAL_TYPES = frozenset(
    {
        "Earth",
        "Electric",
        "Fire",
        "Ice",
        "Lightning",
        "Water",
        "Wind",
    }
)
_PROTECTION_TERMS = (
    "armor",
    "barrier",
    "heal",
    "protect",
    "reflect",
    "resist",
    "sanctuary",
    "shell",
    "shield",
    "ward",
)
_CONJURATION_TERMS = (
    "conjure",
    "decoy",
    "familiar",
    "mirror image",
    "summon",
    "teleport",
    "volitation",
)


def spell_weave_signature(ability: Any) -> str | None:
    """Classify a spell into one stable Knight Enchanter signature."""
    if str(getattr(ability, "typ", "") or "") != "Spell":
        return None
    subtype = str(getattr(ability, "subtyp", "") or "")
    school = str(getattr(ability, "school", "") or "")
    name = str(getattr(ability, "name", "") or "").lower()
    if subtype in _ELEMENTAL_TYPES or school in _ELEMENTAL_TYPES:
        return "Element"
    if (
        subtype in {"Heal", "Support"}
        or school in {"Abjuration", "Protection"}
        or any(term in name for term in _PROTECTION_TERMS)
    ):
        return "Protection"
    if (
        subtype in {"Illusion", "Movement", "Summon"}
        or school == "Conjuration"
        or any(term in name for term in _CONJURATION_TERMS)
    ):
        return "Conjuration"
    return "Force"


def record_spell_signature(character: Any, ability: Any) -> str:
    """Update a Knight Enchanter's two-slot weave after a combat cast."""
    if class_name(character) != "Knight Enchanter":
        return ""
    if not bool(getattr(character, "_active_combat", False)):
        return ""
    signature = spell_weave_signature(ability)
    if signature is None:
        return ""
    state = combat_state(character)
    foundation = state.get("weave_foundation")
    accent = state.get("weave_accent")
    if foundation not in WEAVE_SIGNATURES:
        state["weave_foundation"] = signature
        state["weave_accent"] = None
        return f"{character.name} sets a {signature} weave Foundation.\n"
    if signature == foundation or signature == accent:
        return f"{character.name} reinforces the {signature} weave signature.\n"
    state["weave_accent"] = signature
    return f"{character.name} sets {signature} as the weave Accent.\n"


def weave_pattern(character: Any) -> tuple[str | None, str | None]:
    """Return the currently valid Foundation and Accent."""
    state = combat_state(character)
    foundation = state.get("weave_foundation")
    accent = state.get("weave_accent")
    return (
        foundation if foundation in WEAVE_SIGNATURES else None,
        accent if accent in WEAVE_SIGNATURES else None,
    )


def weave_preview(character: Any) -> str:
    """Return a compact Enchanted Assault preview for combat presentation."""
    foundation, accent = weave_pattern(character)
    if not foundation:
        return "Cast a spell to set Foundation"
    preview = f"{foundation}: {_FOUNDATION_PREVIEWS[foundation]}"
    if accent:
        preview += f"; {accent}: {_ACCENT_PREVIEWS[accent]}"
    return preview


def weave_release_available(character: Any) -> bool:
    """Return whether an active weave can consume at least one Blade Charge."""
    from .meters import _normalized_blade_charge

    charge = _normalized_blade_charge(combat_state(character).get("blade_charge"))
    foundation, _accent = weave_pattern(character)
    return class_name(character) == "Knight Enchanter" and bool(charge and foundation)


def _finish_pattern(character: Any) -> str:
    """Clear a spent pattern, applying the awakened ring's Accent memory."""
    state = combat_state(character)
    accent = state.get("weave_accent")
    if accent in WEAVE_SIGNATURES and _ring_awakened_equipped(character, "Knight Enchanter"):
        state["weave_foundation"] = accent
        state["weave_accent"] = None
        return f"Arcane Duel preserves {accent} as the next Foundation.\n"
    state["weave_foundation"] = None
    state["weave_accent"] = None
    return ""


def _consume_weave(character: Any) -> tuple[dict[str, int] | None, str | None, str | None, str]:
    """Consume the current charges and pattern for an active release."""
    from .meters import _normalized_blade_charge

    state = combat_state(character)
    charge = _normalized_blade_charge(state.get("blade_charge"))
    foundation, accent = weave_pattern(character)
    if not charge or not foundation:
        return None, None, None, ""
    state["blade_charge"] = None
    return charge, foundation, accent, _finish_pattern(character)


def _release_multiplier(character: Any, *, consume: bool = True) -> float:
    """Return the Defensive Release multiplier and optionally spend it."""
    state = combat_state(character)
    stacks = max(0, min(3, int(state.get("defensive_release", 0) or 0)))
    if consume and stacks:
        state["defensive_release"] = 0
    return 1.0 + (0.25 * stacks)


def defensive_release(character: Any) -> str:
    """Replace Defend with one stack of release preparation."""
    state = combat_state(character)
    stacks = min(3, int(state.get("defensive_release", 0) or 0) + 1)
    state["defensive_release"] = stacks
    return (
        f"{character.name} braces the Weave ({stacks}/3); the next release "
        f"is increased by {stacks * 25}%.\n"
    )


def begin_multi_hit_weave(character: Any, strikes: int) -> bool:
    """Prepare Quick Recharge tracking for one multi-hit weapon action."""
    state = combat_state(character)
    state.pop("quick_recharge", None)
    if (
        class_name(character) != "Knight Enchanter"
        or strikes < 2
        or not _has_skill(character, "Quick Recharge")
    ):
        return False
    state["quick_recharge"] = {"release": None}
    return True


def end_multi_hit_weave(character: Any) -> None:
    """Discard the action-scoped Quick Recharge snapshot."""
    combat_state(character).pop("quick_recharge", None)


def _remember_multi_hit_release(character: Any, payload: dict[str, Any]) -> None:
    """Store the first release so later hits can repeat it."""
    context = combat_state(character).get("quick_recharge")
    if isinstance(context, dict) and context.get("release") is None:
        context["release"] = payload


def _preserve_resonant_charge(
    character: Any,
    charge: dict[str, int],
    foundation: str,
) -> str:
    """Preserve one spent pool entry through Resonant Strike."""
    if not _has_skill(character, "Resonant Strike"):
        return ""
    preferred = "Elemental" if foundation == "Element" else "Arcane"
    alternate = "Arcane" if preferred == "Elemental" else "Elemental"
    preserved = preferred if charge.get(preferred, 0) else alternate
    if not charge.get(preserved, 0):
        return ""
    combat_state(character)["blade_charge"] = {
        "Arcane": int(preserved == "Arcane"),
        "Elemental": int(preserved == "Elemental"),
    }
    return f"Resonant Strike preserves one {preserved} blade charge.\n"


def _adjacent_targets(character: Any, target: Any) -> list[Any]:
    """Return living hostile slots adjacent to the primary release target."""
    if not _has_skill(character, "Cleaving Edge"):
        return []
    encounter = getattr(character, "_combat_encounter", None)
    members = list(getattr(encounter, "living_members", ()) or ())
    primary = next((member for member in members if member.enemy is target), None)
    if primary is None:
        return []
    return [
        member.enemy
        for member in members
        if member is not primary and abs(member.slot - primary.slot) == 1
    ]


def _refresh_negative_effects(target: Any) -> int:
    """Refresh active finite negative effects to a three-turn floor."""
    refreshed = 0
    negative_statuses = {
        "Berserk",
        "Blind",
        "Blind Rage",
        "Doom",
        "Hangover",
        "Poison",
        "Polymorph",
        "Silence",
        "Sleep",
        "Stun",
    }
    negative_physical = {"Bleed", "Cripple", "Disarm", "Maim", "Prone"}
    for collection_name, names in (
        ("status_effects", negative_statuses),
        ("physical_effects", negative_physical),
    ):
        effects = getattr(target, collection_name, {})
        for name in names:
            effect = effects.get(name)
            duration = int(getattr(effect, "duration", 0) or 0)
            if effect is not None and effect.active and duration > 0:
                effect.duration = max(3, duration)
                refreshed += 1
    dot = getattr(target, "magic_effects", {}).get("DOT")
    if dot is not None and dot.active and int(dot.duration or 0) > 0:
        dot.duration = max(3, int(dot.duration or 0))
        refreshed += 1
    for effect in getattr(target, "stat_effects", {}).values():
        if (
            getattr(effect, "active", False)
            and int(getattr(effect, "duration", 0) or 0) > 0
            and int(getattr(effect, "extra", 0) or 0) < 0
        ):
            effect.duration = max(3, int(effect.duration or 0))
            refreshed += 1
    return refreshed


def _maybe_refresh_debuffs(character: Any, target: Any) -> str:
    if not _has_skill(character, "Re-debuff") or target is None:
        return ""
    refreshed = _refresh_negative_effects(target)
    return (
        f"Re-debuff refreshes {refreshed} negative effect(s) on {target.name}.\n"
        if refreshed
        else ""
    )


def _schedule_echo(character: Any, payload: dict[str, Any]) -> str:
    """Roll Echoing Blade and save a combat-only release snapshot."""
    if not _has_skill(character, "Echoing Blade") or random.random() >= 0.25:
        return ""
    combat_state(character)["echoing_weave"] = payload
    return "Echoing Blade will repeat the release next turn.\n"


def _apply_stat_effect(
    character: Any,
    rating: str,
    amount: int,
    duration: int,
    *,
    source: str,
) -> None:
    effect = getattr(character, "stat_effects", {}).get(rating)
    if effect is None or amount == 0:
        return
    effect.active = True
    effect.duration = max(int(getattr(effect, "duration", 0) or 0), duration)
    current = int(getattr(effect, "extra", 0) or 0)
    effect.extra = min(current, amount) if amount < 0 else max(current, amount)
    effect.source = source


def _grant_temporary_ward(character: Any, amount: int, turns: int) -> int:
    amount = max(0, int(amount or 0))
    if amount <= 0:
        return 0
    existing = getattr(character, "temporary_health", None)
    if isinstance(existing, dict):
        existing["amount"] = max(0, int(existing.get("amount", 0) or 0)) + amount
        existing["turns"] = max(int(existing.get("turns", 0) or 0), turns)
        existing["source"] = "layered ward"
    else:
        character.temporary_health = {
            "amount": amount,
            "turns": turns,
            "source": "enchantment ward",
        }
    return amount


def _apply_non_elemental_damage(actor: Any, target: Any, raw_damage: int) -> int:
    if target is None or raw_damage <= 0:
        return 0
    resistance = float(target.check_mod("resist", enemy=actor, typ="Non-elemental"))
    damage = int(raw_damage * (1.0 - resistance))
    if damage >= 0:
        target.health.current = max(0, int(target.health.current) - damage)
    else:
        target.health.current = min(
            int(target.health.max),
            int(target.health.current) + abs(damage),
        )
    return damage


def _apply_assault_pattern(
    actor: Any,
    target: Any,
    trigger_damage: int,
    count: int,
    foundation: str,
    accent: str | None,
    multiplier: float,
    *,
    grant_self_benefits: bool = True,
) -> str:
    """Apply one Enchanted Assault pattern to one target."""
    raw_damage = 0
    ward = 0
    effects: list[str] = []

    if foundation == "Element":
        raw_damage += int(trigger_damage * 0.06 * multiplier) * count
        effects.append("Element adds volatile power")
    elif foundation == "Force":
        amount = max(1, int(4 * count * multiplier))
        _apply_stat_effect(target, "Defense", -amount, 2, source="Force Foundation")
        effects.append(f"Force lowers Defense by {amount}")
    elif foundation == "Protection":
        if grant_self_benefits:
            ward += int(actor.health.max * 0.05 * multiplier) * count
            effects.append("Protection raises a ward")
    elif foundation == "Conjuration":
        raw_damage += int(trigger_damage * 0.04 * multiplier) * count
        effects.append("Conjuration duplicates the enchanted edge")

    if accent == "Element":
        raw_damage += int(trigger_damage * 0.03 * multiplier) * count
        effects.append("Element Accent adds volatile power")
    elif accent == "Force":
        amount = max(1, int(2 * count * multiplier))
        _apply_stat_effect(target, "Defense", -amount, 2, source="Force Accent")
        effects.append(f"Force Accent lowers Defense by {amount}")
    elif accent == "Protection":
        if grant_self_benefits:
            ward += int(actor.health.max * 0.03 * multiplier) * count
            effects.append("Protection Accent returns a ward")
    elif accent == "Conjuration":
        raw_damage += (
            max(1, raw_damage // 2)
            if raw_damage
            else int(trigger_damage * 0.03 * multiplier) * count
        )
        effects.append("Conjuration Accent echoes the release")

    damage = _apply_non_elemental_damage(actor, target, raw_damage)
    granted = _grant_temporary_ward(actor, ward, 2)
    summary = "; ".join(effects) or "the pattern releases"
    message = f"Enchanted Assault affects {target.name}: {summary}."
    if damage:
        message += f" It deals {damage} non-elemental weave damage."
    if granted:
        message += f" It grants {granted} temporary HP."
    message += "\n"
    message += _maybe_refresh_debuffs(actor, target)
    return message


def resolve_enchanted_assault(
    actor: Any,
    target: Any,
    trigger_damage: int,
    charge: dict[str, int],
) -> str:
    """Spend the current pattern through the ordinary charged weapon hit."""
    foundation, accent = weave_pattern(actor)
    if class_name(actor) != "Knight Enchanter" or not foundation:
        return ""
    count = max(1, int(charge.get("count", 1) or 1))
    multiplier = _release_multiplier(actor)
    _remember_multi_hit_release(
        actor,
        {
            "charge": dict(charge),
            "count": count,
            "foundation": foundation,
            "accent": accent,
            "multiplier": multiplier,
        },
    )
    offensive_pattern = foundation != "Protection" or accent not in {None, "Protection"}
    targets = [
        target,
        *(_adjacent_targets(actor, target) if offensive_pattern else []),
    ]
    pattern = foundation + (f" > {accent}" if accent else "")
    messages = [f"{actor.name} releases Enchanted Assault ({pattern}).\n"]
    if len(targets) > 1:
        from .meters import _release_blade_charge_damage

        for adjacent in targets[1:]:
            if adjacent is not None and adjacent.is_alive():
                messages.append(
                    _release_blade_charge_damage(
                        actor,
                        adjacent,
                        trigger_damage,
                        charge,
                    )
                )
    messages.extend(
        _apply_assault_pattern(
            actor,
            affected,
            trigger_damage,
            count,
            foundation,
            accent,
            multiplier,
            grant_self_benefits=index == 0,
        )
        for index, affected in enumerate(targets)
        if affected is not None and affected.is_alive()
    )
    memory = _finish_pattern(actor)
    messages.append(memory)
    messages.append(_preserve_resonant_charge(actor, charge, foundation))
    messages.append(
        _schedule_echo(
            actor,
            {
                "kind": "assault",
                "targets": targets,
                "trigger_damage": trigger_damage,
                "count": count,
                "charge": charge,
                "foundation": foundation,
                "accent": accent,
                "multiplier": multiplier,
            },
        )
    )
    return "".join(messages)


def resolve_quick_recharge_hit(
    actor: Any,
    target: Any,
    trigger_damage: int,
) -> str:
    """Repeat a stored Enchanted Assault on a later multi-hit strike."""
    context = combat_state(actor).get("quick_recharge")
    if not isinstance(context, dict):
        return ""
    payload = context.get("release")
    if not isinstance(payload, dict):
        return ""

    from .meters import _release_blade_charge_damage

    charge = payload.get("charge", {})
    foundation = str(payload.get("foundation") or "Force")
    accent = payload.get("accent")
    count = max(1, int(payload.get("count", 1) or 1))
    multiplier = max(1.0, float(payload.get("multiplier", 1.0) or 1.0))
    offensive_pattern = foundation != "Protection" or accent not in {None, "Protection"}
    targets = [
        target,
        *(_adjacent_targets(actor, target) if offensive_pattern else []),
    ]
    messages = ["Quick Recharge repeats the Weave Release on this hit.\n"]
    for index, affected in enumerate(targets):
        if affected is None or not affected.is_alive():
            continue
        messages.append(
            _release_blade_charge_damage(
                actor,
                affected,
                trigger_damage,
                charge,
            )
        )
        messages.append(
            _apply_assault_pattern(
                actor,
                affected,
                trigger_damage,
                count,
                foundation,
                accent,
                multiplier,
                grant_self_benefits=index == 0,
            )
        )
    return "".join(messages)


def aegis_weave(character: Any) -> str:
    """Consume a weave to create a pattern-shaped defensive ward."""
    charge, foundation, accent, memory = _consume_weave(character)
    if not charge or not foundation:
        return "Aegis Weave requires a Foundation and at least one Blade Charge.\n"
    count = charge["count"]
    multiplier = _release_multiplier(character)
    turns = 3
    ward = int(character.health.max * 0.08 * multiplier) * count
    stat_bonuses: list[tuple[str, int]] = []
    if foundation == "Element":
        stat_bonuses.append(("Attack", max(1, int(3 * count * multiplier))))
    elif foundation == "Force":
        stat_bonuses.append(
            (
                "Magic Defense",
                max(1, int(4 * count * multiplier)),
            )
        )
    elif foundation == "Protection":
        ward = int(ward * 1.50)
    elif foundation == "Conjuration":
        turns += 1

    if accent == "Element":
        stat_bonuses.append(("Attack", max(1, int(2 * count * multiplier))))
    elif accent == "Force":
        stat_bonuses.append(("Defense", max(1, int(3 * count * multiplier))))
    elif accent == "Protection":
        ward = int(ward * 1.25)
    elif accent == "Conjuration":
        turns += 1

    for rating, bonus in stat_bonuses:
        _apply_stat_effect(
            character,
            rating,
            bonus,
            turns,
            source="Aegis Weave",
        )
    granted = _grant_temporary_ward(character, ward, turns)
    pattern = foundation + (f" > {accent}" if accent else "")
    message = (
        f"{character.name} releases Aegis Weave ({pattern}), gaining "
        f"{granted} temporary HP for {turns} turns.\n{memory}"
    )
    message += _preserve_resonant_charge(character, charge, foundation)
    message += _schedule_echo(
        character,
        {
            "kind": "aegis",
            "count": count,
            "foundation": foundation,
            "accent": accent,
            "multiplier": multiplier,
            "ward": ward,
            "turns": turns,
            "stat_bonuses": stat_bonuses,
        },
    )
    return message


def spellbind(character: Any) -> str:
    """Consume a weave to empower the next damaging spell hit."""
    charge, foundation, accent, memory = _consume_weave(character)
    if not charge or not foundation:
        return "Spellbind requires a Foundation and at least one Blade Charge.\n"
    combat_state(character)["spellbind"] = {
        "charge": charge,
        "count": charge["count"],
        "foundation": foundation,
        "accent": accent,
        "multiplier": _release_multiplier(character),
        "turns": 3,
    }
    pattern = foundation + (f" > {accent}" if accent else "")
    return (
        f"{character.name} binds {pattern} into the next damaging spell.\n"
        f"{memory}{_preserve_resonant_charge(character, charge, foundation)}"
    )


def resolve_spellbind(actor: Any, target: Any, trigger_damage: int) -> str:
    """Resolve and clear Spellbind on the next positive-damage spell event."""
    state = combat_state(actor)
    pending = state.get("spellbind")
    if class_name(actor) != "Knight Enchanter" or not isinstance(pending, dict):
        return ""
    state["spellbind"] = None
    count = max(1, int(pending.get("count", 1) or 1))
    multiplier = max(1.0, float(pending.get("multiplier", 1.0) or 1.0))
    foundation = str(pending.get("foundation") or "Force")
    accent = pending.get("accent")
    raw_damage = int(trigger_damage * 0.08 * multiplier) * count
    healing = 0
    restored = 0
    ward = 0
    if foundation == "Element":
        raw_damage += int(trigger_damage * 0.04) * count
    elif foundation == "Protection":
        healing = min(
            int(actor.health.max - actor.health.current),
            int(actor.health.max * 0.04) * count,
        )
        actor.health.current += max(0, healing)
    elif foundation == "Conjuration":
        restored = min(
            int(actor.mana.max - actor.mana.current),
            4 * count,
        )
        actor.mana.current += max(0, restored)

    if accent == "Element":
        raw_damage += int(trigger_damage * 0.02) * count
    elif accent == "Protection":
        ward = int(actor.health.max * 0.03) * count
        _grant_temporary_ward(actor, ward, 2)
    elif accent == "Conjuration":
        raw_damage += raw_damage // 2

    targets = [target, *_adjacent_targets(actor, target)]
    messages = []
    for affected in targets:
        if affected is None or not affected.is_alive():
            continue
        if foundation == "Force":
            _apply_stat_effect(
                affected,
                "Magic Defense",
                -max(1, int(4 * count * multiplier)),
                2,
                source="Spellbind",
            )
        if accent == "Force":
            _apply_stat_effect(
                affected,
                "Magic Defense",
                -max(1, int(2 * count * multiplier)),
                2,
                source="Spellbind",
            )
        damage = _apply_non_elemental_damage(actor, affected, raw_damage)
        messages.append(
            f"Spellbind releases {foundation}"
            f"{f' > {accent}' if accent else ''} on {affected.name} for "
            f"{damage} non-elemental bonus damage.\n"
        )
        messages.append(_maybe_refresh_debuffs(actor, affected))
    pattern = foundation + (f" > {accent}" if accent else "")
    del pattern
    messages.append(
        _schedule_echo(
            actor,
            {
                "kind": "spellbind",
                "targets": targets,
                "raw_damage": raw_damage,
                "foundation": foundation,
                "accent": accent,
                "count": count,
                "multiplier": multiplier,
                "healing": healing,
                "mana": restored,
                "ward": ward,
            },
        )
    )
    return "".join(messages)


def resolve_echoing_blade(character: Any) -> str:
    """Repeat an Echoing Blade snapshot at the next start of turn."""
    state = combat_state(character)
    payload = state.get("echoing_weave")
    if not isinstance(payload, dict):
        return ""
    state["echoing_weave"] = None
    kind = payload.get("kind")
    messages = [f"{character.name}'s Echoing Blade repeats the last release.\n"]
    if kind == "assault":
        from .meters import _release_blade_charge_damage

        for index, target in enumerate(payload.get("targets", ())):
            if target is not None and target.is_alive():
                messages.append(
                    _release_blade_charge_damage(
                        character,
                        target,
                        int(payload.get("trigger_damage", 0) or 0),
                        payload.get("charge", {}),
                    )
                )
                messages.append(
                    _apply_assault_pattern(
                        character,
                        target,
                        int(payload.get("trigger_damage", 0) or 0),
                        int(payload.get("count", 1) or 1),
                        str(payload.get("foundation") or "Force"),
                        payload.get("accent"),
                        float(payload.get("multiplier", 1.0) or 1.0),
                        grant_self_benefits=index == 0,
                    )
                )
    elif kind == "aegis":
        turns = int(payload.get("turns", 3) or 3)
        for rating, bonus in payload.get("stat_bonuses", ()):
            _apply_stat_effect(
                character,
                str(rating),
                int(bonus),
                turns,
                source="Echoing Blade",
            )
        ward = _grant_temporary_ward(
            character,
            int(payload.get("ward", 0) or 0),
            turns,
        )
        messages.append(f"The echoed Aegis grants {ward} temporary HP.\n")
    elif kind == "spellbind":
        count = int(payload.get("count", 1) or 1)
        multiplier = float(payload.get("multiplier", 1.0) or 1.0)
        foundation = str(payload.get("foundation") or "Force")
        accent = payload.get("accent")
        healing = min(
            max(0, int(character.health.max - character.health.current)),
            int(payload.get("healing", 0) or 0),
        )
        restored = min(
            max(0, int(character.mana.max - character.mana.current)),
            int(payload.get("mana", 0) or 0),
        )
        character.health.current += healing
        character.mana.current += restored
        ward = _grant_temporary_ward(
            character,
            int(payload.get("ward", 0) or 0),
            2,
        )
        if healing or restored or ward:
            messages.append(
                f"Echoing Spellbind restores {healing} HP and {restored} MP "
                f"and grants {ward} temporary HP.\n"
            )
        for target in payload.get("targets", ()):
            if target is None or not target.is_alive():
                continue
            if foundation == "Force":
                _apply_stat_effect(
                    target,
                    "Magic Defense",
                    -max(1, int(4 * count * multiplier)),
                    2,
                    source="Echoing Blade",
                )
            if accent == "Force":
                _apply_stat_effect(
                    target,
                    "Magic Defense",
                    -max(1, int(2 * count * multiplier)),
                    2,
                    source="Echoing Blade",
                )
            damage = _apply_non_elemental_damage(
                character,
                target,
                int(payload.get("raw_damage", 0) or 0),
            )
            messages.append(f"Echoing Spellbind deals {damage} damage to {target.name}.\n")
            messages.append(_maybe_refresh_debuffs(character, target))
    return "".join(messages)


def weave_reservoir_regeneration(character: Any) -> str:
    """Restore HP and MP while both typed charge pools are full."""
    from .meters import _blade_charge_capacity, _normalized_blade_charge

    if not _has_skill(character, "Weave Reservoir"):
        return ""
    charge = _normalized_blade_charge(combat_state(character).get("blade_charge"))
    capacity = _blade_charge_capacity(character)
    if not charge or any(charge[kind] < capacity for kind in ("Arcane", "Elemental")):
        return ""
    hp_missing = max(0, int(character.health.max - character.health.current))
    mp_missing = max(0, int(character.mana.max - character.mana.current))
    hp = min(hp_missing, max(1, int(character.health.max * 0.03)))
    mp = min(mp_missing, max(1, int(character.mana.max * 0.03)))
    character.health.current += hp
    character.mana.current += mp
    if not hp and not mp:
        return ""
    return f"Weave Reservoir restores {hp} HP and {mp} MP.\n"
