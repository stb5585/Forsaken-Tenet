"""Promotion-kit action and combat event dispatch.

This module translates combat events into specialized class-kit behavior. It
may depend on individual kits; the generic ``meters`` module must not.
"""

from __future__ import annotations

from typing import Any

from src.core.randomness import gameplay_random as random

from .meters import (
    _apply_breakdown_stack,
    _blade_charge_type,
    _claim_action,
    _clear_breakdown_stacks,
    _consume_consecrated_conduit,
    _is_hierophant_staff_hit,
    _normalized_blade_charge,
    _power_up_active,
    _release_blade_charge_damage,
    _resolve_stolen_charge_payoff,
    _store_blade_charge,
    finish_stolen_charge_payoff,
    gain_bloodied_momentum,
    gain_meter,
    record_devotion_source,
    record_prayer_source,
)
from .state import (
    _has_skill,
    _is_weapon_hit,
    _message,
    class_name,
    combat_state,
)


def finish_action(character: Any, *, defender_survived: bool) -> str:
    from .aerial import finish_aerial_follow_through

    state = combat_state(character)
    pending = state.get("pending_devotion_gains")
    choice = str(state.get("action_choice") or state.get("action_name") or "")
    state["defer_devotion_until_survival"] = False
    state["pending_devotion_gains"] = []
    state["pending_hierophant_devotion_token"] = None
    msg = finish_aerial_follow_through(character)
    msg += finish_stolen_charge_payoff(character)
    if (
        choice == "Defend"
        and getattr(
            getattr(character, "equipment", {}).get("OffHand"),
            "subtyp",
            None,
        )
        == "Shield"
    ):
        msg += record_devotion_source(
            character,
            "shielded Defend",
            holy_or_shield=True,
        )
    if choice == "Great Gospel" and _power_up_active(character, "Great Gospel"):
        from .tracks import great_gospel_prayer

        msg += great_gospel_prayer(character)
    if (
        choice == "Defend"
        and class_name(character) in {"Priest", "Archbishop"}
        and _has_skill(character, "Defensive Regen")
    ):
        state["defensive_regen_prayer_armed"] = True
    if isinstance(pending, list):
        for entry in pending:
            if entry.get("require_survivor") and not defender_survived:
                continue
            msg += gain_meter(
                character,
                "devotion",
                int(entry.get("amount", 0) or 0),
                str(entry.get("reason") or ""),
            )
    state["consecrated_conduit_action"] = None
    return msg


PRAYER_SUPPORT_ABILITIES = frozenset(
    {
        "Bless",
        "Cleanse",
        "Dispel",
        "Mana Shield",
        "Mana Shield 2",
        "Prayer of Faith",
        "Regen",
        "Regen2",
        "Regen3",
        "Resurrection",
        "Shell",
        "Silence",
    }
)
STORM_UTILITY_ABILITIES = frozenset({"Ball Lightning", "Windswept"})
STONE_UTILITY_ABILITIES = frozenset({"Nature Shield", "Stone Skin"})


def record_action_resolution(character: Any, result: Any | None) -> str:
    """Translate a structured action result into authored meter outcomes."""
    if result is None:
        return ""
    portions = getattr(result, "results", None)
    if not isinstance(portions, list):
        portions = [result]
    choice = str(combat_state(character).get("action_choice") or "")
    successful = False
    applied = False
    for portion in portions:
        damage = max(0, int(getattr(portion, "damage", 0) or 0))
        healing = max(0, int(getattr(portion, "healing", 0) or 0))
        effects = getattr(portion, "effects_applied", {}) or {}
        changed = (
            any(bool(values) for values in effects.values()) if isinstance(effects, dict) else False
        )
        successful = successful or damage > 0 or healing > 0 or bool(getattr(portion, "hit", False))
        applied = applied or changed
    msg = _resolve_stolen_charge_payoff(character, portions)
    if choice in PRAYER_SUPPORT_ABILITIES and (successful or applied):
        msg += record_prayer_source(character, choice, divine_support=True)
    if choice == "Turn Undead" and successful:
        msg += record_devotion_source(
            character,
            "Turn Undead",
            hostile=True,
            holy_or_shield=True,
        )
    if class_name(character) == "Archdruid" and (successful or applied):
        from .companions import add_aspect

        if choice in STORM_UTILITY_ABILITIES:
            msg += add_aspect(character, "Storm")
        if choice in STONE_UTILITY_ABILITIES:
            msg += add_aspect(character, "Stone")
        if choice == "Tree of Life":
            msg += add_aspect(character, "Growth")
    if class_name(character) in {"Shaman", "Soulcatcher"} and (successful or applied):
        from .. import nature_totems
        from .companions import gain_totem_resonance

        if (
            choice != "Totem Surge"
            and nature_totems.spell_aspect(choice) == nature_totems.active_totem_aspect(character)
            and _claim_action(character, "totem_resonance")
        ):
            msg += gain_totem_resonance(character, "matching cast")
            if (
                nature_totems.has_nature_talent(character, "soulcatcher.ancestral-current")
                and random.random() < 0.25
            ):
                msg += gain_totem_resonance(character, "Ancestral Current")
    return msg


def record_damage_event(
    actor: Any,
    target: Any,
    amount: int,
    damage_type: str,
    *,
    metadata: dict[str, Any] | None = None,
) -> None:
    from .companions import add_aspect

    if not amount or amount <= 0:
        return
    try:
        from .. import mage_mechanics

        spell_metadata = dict(metadata or {})
        spell_metadata["damage_type"] = damage_type
        mage_mechanics.record_spell_damage_hit(actor, target, spell_metadata)
    except Exception:
        pass
    cls = class_name(actor)
    damage_type = str(damage_type or "Physical")
    weapon_hit = _is_weapon_hit(metadata)
    resource_payoff = str((metadata or {}).get("source") or "") == "promotion_kit_payoff"
    from .aerial import record_aerial_weapon_damage

    record_aerial_weapon_damage(actor, target, amount, metadata)
    if isinstance(metadata, dict):
        critical_hit = bool(metadata.get("is_critical"))
        if not critical_hit:
            try:
                critical_hit = float(metadata.get("crit", 1) or 1) > 1
            except (TypeError, ValueError):
                critical_hit = False
    else:
        critical_hit = False
    if critical_hit and _is_weapon_hit(metadata):
        from .aerial import critical_vigor

        _message(actor, critical_vigor(actor))
    if critical_hit and cls in {"Shaman", "Soulcatcher"} and target is not None:
        from .. import nature_totems

        if nature_totems.has_nature_talent(actor, "shaman.bad-omens"):
            _message(actor, nature_totems.add_dread(actor, target, "a critical hit"))
            if nature_totems.has_nature_talent(actor, "soulcatcher.haunting-blows"):
                _message(actor, nature_totems.add_dread(actor, target, "Haunting Blows"))
    if cls == "Soulcatcher" and str((metadata or {}).get("ability_name") or "") == "Soul Drain":
        from .. import nature_totems

        if nature_totems.has_nature_talent(actor, "soulcatcher.gentle-reaping"):
            healing = min(
                max(0, int(actor.health.max) - int(actor.health.current)),
                max(1, int(amount * 0.25)),
            )
            actor.health.current += healing
            if healing:
                _message(actor, f"Gentle Reaping restores {healing} health.\n")

    spell_hit = bool(
        not weapon_hit
        and isinstance(metadata, dict)
        and (metadata.get("ability_name") or metadata.get("source") == "spell")
    )
    if cls in {"Spellblade", "Knight Enchanter"} and spell_hit:
        if cls == "Knight Enchanter":
            from .weaves import resolve_spellbind

            _message(actor, resolve_spellbind(actor, target, amount))
        _store_blade_charge(
            actor,
            charge_type=_blade_charge_type(damage_type),
        )
    if (
        spell_hit
        and target is not None
        and class_name(target) in {"Spellblade", "Knight Enchanter"}
        and _has_skill(target, "Counter Charge")
    ):
        source_state = combat_state(actor)
        source_token = int(source_state.get("action_token", 0) or 0)
        marker = (id(actor), source_token) if source_token > 0 else None
        target_state = combat_state(target)
        if marker is None or target_state.get("counter_charge_action_token") != marker:
            _store_blade_charge(
                target,
                charge_type=_blade_charge_type(damage_type),
                deduplicate=False,
            )
            target_state["counter_charge_action_token"] = marker
            _message(target, f"{target.name}'s Counter Charge answers the spell.\n")

    if (
        cls == "Berserker"
        and weapon_hit
        and not getattr(actor, "_final_assault_countering", False)
        and combat_state(actor).get("bloodied_payoff_action_token")
        != int(combat_state(actor).get("action_token", 0) or 0)
    ):
        _message(actor, gain_bloodied_momentum(actor, "bloodied weapon hit"))

    if not resource_payoff and cls in {"Thief", "Rogue"} and weapon_hit:
        from .tracks import RISKY_LUCK_ACTIONS, record_luck_roll

        choice = str(combat_state(actor).get("action_choice") or "")
        if choice not in RISKY_LUCK_ACTIONS:
            reason = "critical attack" if critical_hit else "attack"
            _message(actor, record_luck_roll(actor, True, reason))

    if not resource_payoff and cls in {"Cleric", "Templar"} and damage_type == "Holy":
        _message(
            actor,
            record_devotion_source(
                actor,
                "Holy pressure",
                hostile=True,
                holy_or_shield=True,
            ),
        )
    if (
        not resource_payoff
        and cls in {"Cleric", "Templar"}
        and str((metadata or {}).get("ability_name") or "") == "Shield Slam"
    ):
        _message(
            actor,
            record_devotion_source(
                actor,
                "Shield Slam",
                hostile=True,
                holy_or_shield=True,
            ),
        )
    if cls == "Hierophant" and not resource_payoff:
        staff_hit = _is_hierophant_staff_hit(actor, metadata)
        turn_undead = (
            str((metadata or {}).get("ability_name") or "").lower().startswith("turn undead")
        )
        if damage_type == "Holy" or staff_hit or turn_undead:
            reason = "staff conduit" if staff_hit else "holy action"
            _message(
                actor,
                record_devotion_source(
                    actor,
                    reason,
                    hostile=True,
                    holy_or_shield=True,
                ),
            )
        _consume_consecrated_conduit(actor, target, amount, damage_type, metadata)

    if not resource_payoff and cls in {"Priest", "Archbishop"} and damage_type == "Holy":
        _message(actor, record_prayer_source(actor, "Holy spell"))

    if cls in {"Monk", "Master Monk"} and weapon_hit:
        from .tracks import record_ki_martial_hit

        _message(actor, record_ki_martial_hit(actor, metadata))

    if cls == "Archdruid" and not resource_payoff:
        if damage_type in {"Poison"}:
            _message(actor, add_aspect(actor, "Venom"))
        if damage_type in {"Electric", "Wind"}:
            _message(actor, add_aspect(actor, "Storm"))
        if damage_type in {"Earth", "Physical"} and not weapon_hit:
            _message(actor, add_aspect(actor, "Stone"))

    if cls in {"Shaman", "Soulcatcher"} and not hasattr(actor, "_totem_pulse_potency"):
        from .. import nature_totems
        from .companions import gain_totem_resonance

        ability_name = str((metadata or {}).get("ability_name") or "")
        if nature_totems.spell_aspect(ability_name) == nature_totems.active_totem_aspect(
            actor
        ) and _claim_action(actor, "totem_resonance"):
            _message(actor, gain_totem_resonance(actor, "matching cast"))

    if weapon_hit:
        _apply_breakdown_stack(actor, target)
        _consume_weapon_payoffs(actor, target, amount, damage_type)
    elif spell_hit:
        _clear_breakdown_stacks(actor, target)
    if target is not None and not target.is_alive():
        from .tracks import clear_death_marks

        clear_death_marks(actor, target)


def record_damage_taken(defender: Any, amount: int, damage_type: str) -> None:
    from .companions import add_aspect
    from .resolve import build_resolve
    from .tracks import cheat_death

    if not amount or amount <= 0:
        return
    cls = class_name(defender)
    if cls == "Master Monk":
        from .tracks import break_rope_a_dope

        _message(defender, break_rope_a_dope(defender))
    if cls == "Berserker":
        state = combat_state(defender)
        if int(getattr(getattr(defender, "health", None), "current", 0) or 0) <= 0:
            state["bloodied_momentum"] = 0
            state["bloodied_bonus_round"] = None
            state["bloodied_payoff_action_token"] = None
            state["battle_scar_momentum_preserved"] = False
            state["bloodied_ring_miss_preserved"] = False
        else:
            _message(
                defender,
                gain_bloodied_momentum(
                    defender,
                    "bloodied incoming damage",
                    incoming=True,
                ),
            )
    if cls in {"Sentinel", "Stalwart Defender"} and damage_type in {"Physical", "Melee"}:
        _message(
            defender,
            build_resolve(
                defender,
                max(1, amount // 5),
                "mitigated pressure",
            ),
        )
    if (
        cls == "Archdruid"
        and damage_type == "Physical"
        and int(getattr(getattr(defender, "health", None), "current", 0) or 0) > 0
    ):
        _message(defender, add_aspect(defender, "Stone", incoming=True))
    if cls == "Rogue" and int(getattr(getattr(defender, "health", None), "current", 1) or 0) <= 0:
        _message(defender, cheat_death(defender))
    if (
        cls in {"Lancer", "Dragoon"}
        and int(getattr(getattr(defender, "health", None), "current", 1) or 0) <= 0
    ):
        from .aerial import try_dragon_soul

        _message(defender, try_dragon_soul(defender))
    if (
        cls in {"Lancer", "Dragoon"}
        and int(getattr(getattr(defender, "health", None), "current", 1) or 0) <= 0
    ):
        state = combat_state(defender)
        state["aerial_tempo"] = 0
        state["pending_aerial_follow_through"] = None
        from .. import class_rings

        class_rings.reset_combat_flags(defender)
    if (
        cls in {"Paladin", "Crusader"}
        and int(getattr(getattr(defender, "health", None), "current", 1) or 0) <= 0
    ):
        state = combat_state(defender)
        state["oath_conviction"] = 0
        state["oath_judgment_counter"] = None
        state["oath_protection_guard"] = None
        state["oath_retribution_shelter"] = None


def record_healing_done(
    actor: Any,
    amount: int,
    *,
    source: str = "Unknown",
    target: Any | None = None,
) -> str:
    from ..cleric import has_cleric_talent
    from .companions import add_aspect

    if not amount or amount <= 0:
        return ""
    cls = class_name(actor)
    recipient = target or actor
    threshold = max(5, int((max(1, recipient.health.max) * 0.05) + 0.999))
    meaningful = amount >= threshold
    msg = ""
    passive = str(source).lower().startswith(("regen", "water totem"))
    if meaningful and cls in {"Cleric", "Templar", "Hierophant"}:
        msg += record_devotion_source(actor, "meaningful healing")
    if (
        meaningful
        and not passive
        and cls == "Hierophant"
        and has_cleric_talent(actor, "hierophant.merciful-ward")
    ):
        ward = recipient.magic_effects["Nature Shield"]
        ward.active = True
        ward.duration = max(int(ward.duration or 0), 2)
        ward.extra = max(
            int(ward.extra or 0),
            max(6, int(getattr(actor.stats, "wisdom", 0) or 0) // 4),
        )
        msg += f"Merciful Ward shelters {recipient.name}.\n"
    if meaningful and cls in {"Priest", "Archbishop"} and not passive:
        msg += record_prayer_source(actor, "meaningful healing", divine_support=True)
    if cls in {"Monk", "Master Monk"} and _has_skill(actor, "Chi Heal"):
        state = combat_state(actor)
        token = int(state.get("action_token", 0) or 0)
        if state.get("action_choice") == "Chi Heal" and state.get("ki_action_token") != token:
            state["ki_action_token"] = token
            msg += gain_meter(actor, "ki", 1, "Chi Heal")
    if cls == "Archdruid" and meaningful:
        msg += add_aspect(actor, "Growth")
    if cls in {"Shaman", "Soulcatcher"} and not hasattr(actor, "_totem_pulse_potency"):
        from .. import nature_totems
        from .companions import gain_totem_resonance

        if nature_totems.spell_aspect(source) == nature_totems.active_totem_aspect(
            actor
        ) and _claim_action(actor, "totem_resonance"):
            msg += gain_totem_resonance(actor, "matching cast")
    return msg


def _consume_weapon_payoffs(actor: Any, target: Any, amount: int, damage_type: str) -> None:
    state = combat_state(actor)
    cls = class_name(actor)
    extra = 0
    lines: list[str] = []

    charge = _normalized_blade_charge(state.get("blade_charge"))
    quick_recharge = ""
    if cls == "Knight Enchanter":
        from .weaves import resolve_quick_recharge_hit

        quick_recharge = resolve_quick_recharge_hit(actor, target, amount)
        lines.append(quick_recharge)
    if not quick_recharge and cls in {"Spellblade", "Knight Enchanter"} and charge:
        lines.append(_release_blade_charge_damage(actor, target, amount, charge))
        state["blade_charge"] = None
        if cls == "Knight Enchanter":
            from .weaves import resolve_enchanted_assault

            lines.append(resolve_enchanted_assault(actor, target, amount, charge))

    if extra > 0 and target is not None:
        target.health.current = max(0, target.health.current - extra)
    for line in lines:
        _message(actor, line)
