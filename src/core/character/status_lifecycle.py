"""Lifecycle helpers for character status effects."""

from __future__ import annotations

from typing import Any, cast


def effect_maps(character: Any) -> tuple[Any, ...]:
    """Return every effect map whose entries are cleared at combat end."""
    return (
        character.status_effects,
        character.physical_effects,
        character.stat_effects,
        character.magic_effects,
        character.class_effects,
    )


def clear_effect(character: Any, effect_name: str, *, source: str = "Duration Expired") -> None:
    """Clear one effect and publish its expiry when it was active."""
    effect_map = character.effect_handler(effect=effect_name)
    effect = effect_map[effect_name]
    if effect.active:
        character._emit_status_event(character, effect_name, applied=False, source=source)
    effect.active = False
    effect.duration = 0
    effect.extra = 0
    effect.source = ""
    if effect_name == "DOT":
        character._corruption_payload = None


def _clear_all_effects(character: Any) -> None:
    """Clear every combat-scoped effect while emitting removal events."""
    for effect_map in effect_maps(character):
        for effect_name, effect in effect_map.items():
            if effect.active:
                character._emit_status_event(
                    character,
                    effect_name,
                    applied=False,
                    source="Combat End",
                )
            effect.active = False
            effect.duration = 0
            effect.extra = 0
            effect.source = ""


def _cancel_charging_skills(character: Any) -> None:
    """Cancel every charging skill, preserving each skill's cleanup contract."""
    for skill_group in getattr(character, "spellbook", {}).values():
        for skill in getattr(skill_group, "values", lambda: [])():
            if not getattr(skill, "charging", False):
                continue
            cancel_charge = getattr(skill, "cancel_charge", None)
            if callable(cancel_charge):
                cancel_charge(character)
                continue
            skill.charging = False
            if hasattr(skill, "charge_turns"):
                skill.charge_turns = 0
            if hasattr(skill, "charge_target"):
                skill.charge_target = None


def end_combat(character: Any) -> None:
    """Clear encounter-local hooks, effects, and transient character state."""
    from ..classes import ability_mechanics, healer, mage_mechanics, pathfinder, promotion_kits

    pathfinder.tick_combat_state(character, end=True)
    healer.tick_combat_state(character, end=True)
    mage_mechanics.tick_combat_state(character, end=True)
    _clear_all_effects(character)
    _cancel_charging_skills(character)
    character.grandmaster_technique_stacks = {}
    character._hemorrhage_thirst_streak = 0
    character._corruption_payload = None
    character.temporary_health = None
    character.fractures = {}
    for attribute in (
        "soul_bound_to",
        "soul_siphon",
        "shadow_curtain_turns",
        "shade_of_ahool_turns",
        "warlock_eclipse_turns",
        "mystical_vitality_turns",
        "demon_grease_turns",
        "soul_vessel_turns",
        "temporary_undead_allies",
        "haunted_turns",
        "_temporary_stasis_turns",
        "_soul_binding_caster",
    ):
        if hasattr(character, attribute):
            delattr(character, attribute)
    promotion_kits.clear_combat_state(character)
    ability_mechanics.sync_exploration_flags(character)


def tick_start_of_turn_hooks(character: Any) -> str:
    """Advance promotion and class-specific combat state in established order."""
    from ..classes import healer, mage_mechanics, pathfinder, promotion_kits

    return (
        cast(str, promotion_kits.tick_combat_state(character))
        + cast(str, mage_mechanics.tick_combat_state(character))
        + cast(str, healer.tick_combat_state(character))
        + cast(str, pathfinder.tick_combat_state(character))
    )


def prone_recovery_bonus(character: Any) -> int:
    """Return Pathfinder's additional Prone recovery without a compatibility fallback."""
    from ..classes import pathfinder

    return cast(int, pathfinder.bounce_back_bonus(character))


def tick_persistent_afflictions(character: Any) -> str:
    """Advance every persistent affliction in its defined order."""
    from .. import persistent_afflictions as afflictions

    return (
        cast(str, afflictions.hemorrhaging_tick(character))
        + cast(str, afflictions.swarms_tick(character))
        + cast(str, afflictions.polydipsia_tick(character))
    )


def record_defensive_regen(character: Any, healing: int) -> str:
    """Record the promotion-state consequence of a Defend healing tick."""
    from ..classes import promotion_kits

    return cast(str, promotion_kits.record_defensive_regen(character, healing))


def tick_magical_invigoration(character: Any) -> None:
    """Advance separately timed Magical Invigoration stacks."""
    from ..classes import promotion_kits

    promotion_kits.tick_magical_invigoration(character)


def record_magical_invigoration_tick(character: Any) -> str:
    """Record the promotion-state consequence of a Regen tick."""
    from ..classes import promotion_kits

    return cast(str, promotion_kits.record_magical_invigoration_tick(character))
