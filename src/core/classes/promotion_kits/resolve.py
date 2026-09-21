"""Sentinel and Stalwart Defender Resolve mechanics."""

from __future__ import annotations

from typing import Any

from src.core.randomness import gameplay_random as random

from .state import _claim_action, _class_ring_data, class_name, combat_state

RESOLVE_SPEND_ABILITIES: tuple[dict[str, Any], ...] = (
    {
        "name": "Hold the Line",
        "role": "Stance",
        "cost": 0,
        "description": "Enter a shield stance that improves block and mitigation.",
    },
    {
        "name": "Brace Wall",
        "role": "Stance",
        "cost": 15,
        "description": "Refresh Hold the Line and raise Defense for the next exchange.",
    },
    {
        "name": "Spell Block",
        "role": "Anti-magic",
        "cost": 25,
        "description": "Prepare your shield to block a projectile spell.",
    },
    {
        "name": "Bulwark Guard",
        "role": "Barrier",
        "cost": 25,
        "description": "Create a powerful barrier for one turn.",
    },
    {
        "name": "Purge Weakness",
        "role": "Cleanse",
        "cost": 40,
        "description": "Remove negative effects and gain two turns of immunity.",
    },
    {
        "name": "Repercussion",
        "role": "Assault",
        "cost": 30,
        "description": "Release a powerful blast wave against all enemies.",
    },
    {
        "name": "Boast",
        "role": "Support",
        "cost": 20,
        "description": "Gain temporary health and increased Resolve generation.",
    },
    {
        "name": "Focused Assault",
        "role": "Assault",
        "cost": 15,
        "description": "Improve accuracy and critical damage for three turns.",
    },
)

RESOLVE_SURGES: tuple[dict[str, Any], ...] = (
    {
        "name": "Citadel Aegis",
        "role": "Barrier Surge",
        "mastery_key": "citadel_aegis",
        "required_uses": 4,
        "description": "Empty full Resolve into a fortress barrier and defensive stance.",
    },
    {
        "name": "Ironwall Revenge",
        "role": "Counter Burst",
        "mastery_key": "ironwall_revenge",
        "required_uses": 4,
        "description": "Empty full Resolve into a three-hit counterattack.",
    },
    {
        "name": "Last Bastion",
        "role": "Survival Surge",
        "mastery_key": "last_bastion",
        "required_uses": 4,
        "description": "Empty full Resolve to recover and rebuild your guard.",
    },
    {
        "name": "Stronghold",
        "role": "Defense Burst",
        "mastery_key": "stronghold",
        "required_uses": 4,
        "description": "Reduce melee damage and improve block amount by 30%.",
    },
)

GET_EVEN_DISCOUNT = 10
GENERATOR_SHIELD_GAIN = 5
TOWER_OFFENSE_DAMAGE_DIVISOR = 5
TOWER_OFFENSE_GAIN_CAP = 20


def resolve_cap(character: Any) -> int:
    return 100 if class_name(character) == "Stalwart Defender" else 50


def _normalize_resolve_data(data: dict[str, Any]) -> None:
    data["guard_meter"] = max(0, int(data.get("guard_meter", 0) or 0))
    mastery = data.get("resolve_mastery", {})
    keys = tuple(entry["mastery_key"] for entry in RESOLVE_SURGES)
    if not isinstance(mastery, dict):
        data["resolve_mastery"] = {key: 0 for key in keys}
        return
    normalized_mastery = {}
    for key in keys:
        try:
            progress = int(mastery.get(key, 0) or 0)
        except (TypeError, ValueError):
            progress = 0
        normalized_mastery[key] = max(0, min(4, progress))
    data["resolve_mastery"] = normalized_mastery


def _has_shield(character: Any) -> bool:
    return getattr(character.equipment.get("OffHand"), "subtyp", None) == "Shield"


def _require_resolve_training(character: Any, ability_name: str) -> str:
    if class_name(character) not in {"Sentinel", "Stalwart Defender"}:
        return f"{ability_name} belongs to the shield defender track.\n"
    return ""


def _require_shield(character: Any, ability_name: str) -> str:
    if not _has_shield(character):
        return f"{ability_name} requires a shield.\n"
    return ""


def _resolve_data(character: Any) -> dict[str, Any]:
    data = _class_ring_data(character, "Stalwart Defender")
    _normalize_resolve_data(data)
    data["guard_meter"] = min(resolve_cap(character), int(data.get("guard_meter", 0) or 0))
    return data


def record_resolve_mastery(
    character: Any,
    mastery_key: str,
    reason: str,
    *,
    action_deduplicated: bool = False,
) -> str:
    """Record one successful use toward an associated Resolve Surge."""
    if class_name(character) not in {"Sentinel", "Stalwart Defender"}:
        return ""
    entries = {entry["mastery_key"]: entry for entry in RESOLVE_SURGES}
    entry = entries.get(mastery_key)
    if entry is None:
        return ""
    if action_deduplicated and not _claim_action(
        character,
        f"resolve_mastery:{mastery_key}",
    ):
        return ""
    data = _resolve_data(character)
    mastery = data["resolve_mastery"]
    required = int(entry["required_uses"])
    before = int(mastery.get(mastery_key, 0) or 0)
    mastery[mastery_key] = min(required, before + 1)
    if mastery[mastery_key] == before:
        return ""
    progress = mastery[mastery_key]
    message = f"{character.name}'s defensive mastery deepens.\n"
    if progress == required:
        if class_name(character) == "Stalwart Defender":
            message += f"{character.name} discovers the {entry['name']} Resolve Surge!\n"
        else:
            message += (
                f"{character.name} discovers {entry['name']}; the technique awaits "
                "their final defender training.\n"
            )
    return message


def resolve_surge_unlocked(character: Any, surge_name: str) -> bool:
    if class_name(character) != "Stalwart Defender":
        return False
    data = _resolve_data(character)
    for entry in RESOLVE_SURGES:
        if entry["name"] == surge_name:
            progress = int(data["resolve_mastery"].get(entry["mastery_key"], 0) or 0)
            return progress >= int(entry["required_uses"])
    return False


def current_resolve(character: Any) -> int:
    data = _resolve_data(character)
    return int(data.get("guard_meter", 0) or 0)


def resolve_is_full(character: Any) -> bool:
    return current_resolve(character) >= resolve_cap(character)


def resolve_surge_available(character: Any, surge_name: str) -> bool:
    return resolve_surge_unlocked(character, surge_name) and resolve_is_full(character)


def resolve_surge_rows(character: Any) -> list[dict[str, Any]]:
    data = _resolve_data(character)
    full = int(data.get("guard_meter", 0) or 0) >= resolve_cap(character)
    rows: list[dict[str, Any]] = []
    for entry in RESOLVE_SURGES:
        progress = int(data["resolve_mastery"].get(entry["mastery_key"], 0) or 0)
        required = int(entry["required_uses"])
        learned = progress >= required
        unlocked = class_name(character) == "Stalwart Defender" and learned
        rows.append(
            {
                **entry,
                "progress": progress,
                "required": required,
                "learned": learned,
                "unlocked": unlocked,
                "available": unlocked and full,
            }
        )
    return rows


def resolve_spend_rows(character: Any) -> list[dict[str, Any]]:
    learned = set(getattr(character, "spellbook", {}).get("Skills", {}) or {})
    return [{**entry, "unlocked": entry["name"] in learned} for entry in RESOLVE_SPEND_ABILITIES]


def _spend_resolve(
    character: Any,
    cost: int,
    ability_name: str,
) -> tuple[bool, str, dict[str, Any]]:
    data = _resolve_data(character)
    resolve = int(data.get("guard_meter", 0) or 0)
    state = combat_state(character)
    spent = effective_resolve_cost(character, cost)
    if resolve < spent:
        return False, f"{ability_name} requires {spent} Resolve.\n", data
    data["guard_meter"] = resolve - spent
    discount_used = cost - spent
    if discount_used:
        state["get_even_discount"] = 0
    message = (
        f"Get Even reduces {ability_name}'s Resolve cost by {discount_used}.\n"
        if discount_used
        else ""
    )
    message += f"{character.name} spends {spent} Resolve on {ability_name}.\n"
    return True, message, data


def effective_resolve_cost(character: Any, cost: int) -> int:
    """Return an ordinary Resolve action's cost after a primed discount."""
    discount = max(
        0,
        int(combat_state(character).get("get_even_discount", 0) or 0),
    )
    return max(0, int(cost) - discount)


def build_resolve(character: Any, amount: int, reason: str = "") -> str:
    if class_name(character) not in {"Sentinel", "Stalwart Defender"}:
        return ""
    cap = resolve_cap(character)
    data = _resolve_data(character)
    before = int(data.get("guard_meter", 0) or 0)
    gain = max(0, int(amount))
    if int(combat_state(character).get("boast_turns", 0) or 0) > 0:
        gain = max(1, int(round(gain * 1.5)))
    try:
        from ...progression import has_talent

        if has_talent(character, "stalwart.unbroken-wall") and getattr(
            character.class_effects.get("Last Stand"), "active", False
        ):
            gain = max(1, int(round(gain * 1.5)))
    except Exception:
        pass
    data["guard_meter"] = min(cap, before + gain)
    if data["guard_meter"] == before:
        return "Resolve is capped.\n"
    gained = data["guard_meter"] - before
    msg = (
        f"{character.name} gains {gained} Resolve from {reason} "
        f"({data['guard_meter']}/{cap}).\n"
    )
    return msg


def tower_offense_after_shield_slam(character: Any, damage: int) -> str:
    """Generate damage-scaled Resolve after Shield Slam deals damage."""
    if damage <= 0 or "Tower Offense" not in getattr(character, "spellbook", {}).get("Skills", {}):
        return ""
    gain = min(
        TOWER_OFFENSE_GAIN_CAP,
        max(1, int(damage) // TOWER_OFFENSE_DAMAGE_DIVISOR),
    )
    return build_resolve(character, gain, "Tower Offense")


def prepare_get_even(character: Any) -> str:
    """Prime the next ordinary Resolve action after Retaliate connects."""
    if "Get Even" not in getattr(character, "spellbook", {}).get("Skills", {}):
        return ""
    combat_state(character)["get_even_discount"] = GET_EVEN_DISCOUNT
    return f"{character.name}'s Get Even primes a Resolve discount.\n"


def generator_shield_after_ricochet(
    character: Any,
    *,
    hit: bool,
    stunned: bool,
) -> str:
    """Generate Resolve for one Shield Ricochet impact."""
    if not hit or "Generator Shield" not in getattr(character, "spellbook", {}).get("Skills", {}):
        return ""
    gain = GENERATOR_SHIELD_GAIN * (2 if stunned else 1)
    return build_resolve(character, gain, "Generator Shield")


def battle_determination_after_cry(character: Any) -> str:
    """Generate Resolve when a trained Stalwart Defender uses Battle Cry."""
    if "Battle Determination" not in getattr(character, "spellbook", {}).get("Skills", {}):
        return ""
    return build_resolve(character, 20, "Battle Determination")


def hold_the_line_active(character: Any) -> bool:
    """Return whether Hold the Line still has an active turn window."""
    return int(combat_state(character).get("hold_the_line", 0) or 0) > 0


def hold_the_line(character: Any, *, as_defend: bool = False) -> str:
    training = _require_resolve_training(character, "Hold the Line")
    if training:
        return training
    shield = _require_shield(character, "Hold the Line")
    if shield:
        return shield
    if hold_the_line_active(character):
        return "Hold the Line is already active.\n"
    combat_state(character)["hold_the_line"] = 3
    reduction = float(getattr(character, "defensive_stance_reduction", 0.5))
    try:
        from ...progression import has_talent

        if has_talent(character, "sentinel.resolute-guard"):
            reduction += 0.05
    except Exception:
        pass
    character.enter_defensive_stance(
        duration=3,
        reduction=min(0.75, reduction),
        source="Hold the Line",
    )
    msg = f"{character.name} holds the line behind their shield.\n"
    msg += build_resolve(character, 5, "Hold the Line")
    msg += record_resolve_mastery(
        character,
        "citadel_aegis",
        "Hold the Line",
        action_deduplicated=True,
    )
    if as_defend:
        msg += record_resolve_mastery(
            character,
            "stronghold",
            "Defend",
            action_deduplicated=True,
        )
    return msg


def brace_wall(character: Any) -> str:
    training = _require_resolve_training(character, "Brace Wall")
    if training:
        return training
    shield = _require_shield(character, "Brace Wall")
    if shield:
        return shield
    ok, msg, _data = _spend_resolve(character, 15, "Brace Wall")
    if not ok:
        return msg
    state = combat_state(character)
    state["hold_the_line"] = max(int(state.get("hold_the_line", 0) or 0), 3)
    character.enter_defensive_stance(duration=3)
    defense = character.stat_effects["Defense"]
    defense.active = True
    defense.duration = max(int(defense.duration or 0), 2)
    defense.extra = max(int(defense.extra or 0), 3)
    msg += f"{character.name} braces the wall.\n"
    msg += record_resolve_mastery(
        character,
        "citadel_aegis",
        "Brace Wall",
        action_deduplicated=True,
    )
    return msg


def prepare_spell_block(character: Any) -> str:
    """Prepare one projectile-spell block for the next two turns."""
    training = _require_resolve_training(character, "Spell Block")
    if training:
        return training
    shield = _require_shield(character, "Spell Block")
    if shield:
        return shield
    ok, message, _data = _spend_resolve(character, 25, "Spell Block")
    if not ok:
        return message
    state = combat_state(character)
    state["spell_block_turns"] = 2
    state["spell_block_skip_tick"] = True
    return message + f"{character.name} prepares to block a projectile spell.\n"


def bulwark_guard(character: Any) -> str:
    """Spend Resolve on a one-turn barrier."""
    training = _require_resolve_training(character, "Bulwark Guard")
    if training:
        return training
    shield = _require_shield(character, "Bulwark Guard")
    if shield:
        return shield
    ok, message, _data = _spend_resolve(character, 25, "Bulwark Guard")
    if not ok:
        return message
    barrier = max(25, int(character.health.max * 0.20))
    character.temporary_health = {
        "amount": barrier,
        "turns": 1,
        "source": "Bulwark Guard",
    }
    message += f"{character.name} raises a {barrier}-point Bulwark Guard for one turn.\n"
    message += record_resolve_mastery(
        character,
        "citadel_aegis",
        "Bulwark Guard",
        action_deduplicated=True,
    )
    return message


def purge_weakness(character: Any) -> str:
    """Clear negative effects and grant a two-turn immunity window."""
    ok, message, _data = _spend_resolve(character, 40, "Purge Weakness")
    if not ok:
        return message
    negative_physical = {"Bleed", "Cripple", "Disarm", "Maim", "Prone"}
    negative_magic = {"DOT"}
    removed = 0
    for collection_name in (
        "status_effects",
        "physical_effects",
        "magic_effects",
        "stat_effects",
    ):
        for name, effect in getattr(character, collection_name, {}).items():
            if not getattr(effect, "active", False):
                continue
            if collection_name == "physical_effects" and name not in negative_physical:
                continue
            if collection_name == "magic_effects" and name not in negative_magic:
                continue
            if collection_name == "stat_effects" and float(getattr(effect, "extra", 0) or 0) >= 0:
                continue
            if collection_name == "status_effects" and name in {"Berserk", "Peaceful"}:
                continue
            effect.active = False
            effect.duration = 0
            effect.extra = 0
            removed += 1
    combat_state(character)["purge_immunity_turns"] = 2
    message += (
        f"{character.name} purges {removed} negative effect"
        f"{'s' if removed != 1 else ''} and becomes immune for two turns.\n"
    )
    message += record_resolve_mastery(
        character,
        "last_bastion",
        "Purge Weakness",
        action_deduplicated=True,
    )
    return message


def boast(character: Any) -> str:
    """Create temporary HP and improve Resolve generation for three turns."""
    ok, message, _data = _spend_resolve(character, 20, "Boast")
    if not ok:
        return message
    amount = max(1, int(character.health.max * 0.15))
    character.temporary_health = {
        "amount": amount,
        "turns": 4,
        "source": "Boast",
    }
    state = combat_state(character)
    state["boast_turns"] = 3
    state["boast_starting_pool"] = amount
    message += f"{character.name}'s Boast grants {amount} temporary health for three turns.\n"
    message += record_resolve_mastery(
        character,
        "last_bastion",
        "Boast",
        action_deduplicated=True,
    )
    return message


def focused_assault(character: Any) -> str:
    """Improve weapon accuracy and critical damage for three turns."""
    ok, message, _data = _spend_resolve(character, 15, "Focused Assault")
    if not ok:
        return message
    combat_state(character)["focused_assault_turns"] = 3
    message += f"{character.name} focuses their assault for three turns.\n"
    message += record_resolve_mastery(
        character,
        "ironwall_revenge",
        "Focused Assault",
        action_deduplicated=True,
    )
    return message


def focused_assault_accuracy(character: Any) -> float:
    """Return the active Focused Assault weapon-accuracy bonus."""
    return 0.15 if int(combat_state(character).get("focused_assault_turns", 0) or 0) else 0.0


def focused_assault_critical_multiplier(character: Any, multiplier: float) -> float:
    """Increase only the bonus portion of critical weapon damage."""
    if multiplier <= 1 or not int(combat_state(character).get("focused_assault_turns", 0) or 0):
        return multiplier
    return 1 + ((multiplier - 1) * 1.30)


def shield_riposte_after_full_block(defender: Any, attacker: Any) -> str:
    """Attempt the passive Shield Riposte knockdown after a complete block."""
    if "Shield Riposte" not in getattr(defender, "spellbook", {}).get("Skills", {}):
        return ""
    chance = min(
        0.85,
        0.35 + (int(defender.stats.strength) - int(attacker.stats.con)) * 0.02,
    )
    if random.random() >= max(0.10, chance):
        return f"{defender.name}'s Shield Riposte fails to unbalance {attacker.name}.\n"
    prone = attacker.physical_effects["Prone"]
    prone.active = True
    prone.duration = max(1, int(prone.duration or 0))
    return f"{defender.name}'s Shield Riposte knocks {attacker.name} prone.\n"


def stronghold_melee_reduction(
    character: Any,
    damage: int,
    attacker: Any | None = None,
) -> tuple[int, str]:
    """Reduce melee damage and apply Iron Maiden while Stronghold is active."""
    if not int(combat_state(character).get("stronghold_turns", 0) or 0):
        return damage, ""
    reduced = max(1, int(damage * 0.30)) if damage > 0 else 0
    message = (
        f"{character.name}'s Stronghold reduces melee damage by {reduced}.\n" if reduced else ""
    )
    if (
        attacker is not None
        and reduced > 0
        and "Iron Maiden" in getattr(character, "spellbook", {}).get("Skills", {})
    ):
        retaliation = max(1, reduced // 2)
        attacker.health.current = max(0, int(attacker.health.current) - retaliation)
        character._emit_damage_event(
            attacker,
            retaliation,
            damage_type="Reflected",
            ability_name="Iron Maiden",
            source="reflected",
        )
        message += f"Iron Maiden deals {retaliation} damage to {attacker.name}.\n"
    return max(0, damage - reduced), message


def repercussion(
    character: Any,
    targets: list[tuple[str, Any]],
    *,
    battle_engine: Any,
    rng: Any = None,
):
    """Spend Resolve to damage every enemy with a physical blast wave."""
    from ...combat.combat_result import CombatResult, CombatResultGroup
    from ...combat.targeting import TargetScope

    group = CombatResultGroup(
        action="Repercussion",
        actor_id=battle_engine.current_actor_id,
        target_scope=TargetScope.ALL_ENEMIES,
        target_ids=tuple(target_id for target_id, _target in targets),
    )
    if not targets:
        group.add(
            CombatResult(
                action="Repercussion",
                actor=character,
                message="There are no targets for Repercussion.\n",
            )
        )
        return group
    ok, message, _data = _spend_resolve(character, 30, "Repercussion")
    if not ok:
        group.add(CombatResult(action="Repercussion", actor=character, message=message))
        return group
    message += record_resolve_mastery(
        character,
        "ironwall_revenge",
        "Repercussion",
        action_deduplicated=True,
    )
    try:
        from ...progression import has_talent

        punishing = has_talent(character, "stalwart.punishing-guard")
    except Exception:
        punishing = False
    generator = rng or random
    multiplier = 1.25 if punishing else 1.0
    for index, (target_id, target) in enumerate(targets):
        raw = max(1, int(character.check_mod("attack", enemy=target) * multiplier))
        _hit, defense_message, damage = target.damage_reduction(
            raw,
            character,
            typ="Physical",
        )
        damage, ward_message = target._apply_temporary_health(target, damage)
        target.health.current = max(0, int(target.health.current) - damage)
        prone = bool(punishing and damage > 0 and generator.random() < 0.35)
        if prone:
            effect = target.physical_effects["Prone"]
            effect.active = True
            effect.duration = max(1, int(effect.duration or 0))
        hit_message = (message if index == 0 else "") + defense_message + ward_message
        hit_message += f"Repercussion hits {target.name} for {damage} damage.\n"
        if prone:
            hit_message += f"{target.name} is knocked prone.\n"
        character._emit_damage_event(
            target,
            damage,
            damage_type="Physical",
            ability_name="Repercussion",
            attack_source="special_attack",
            source="ability",
        )
        group.add(
            CombatResult(
                action="Repercussion",
                actor=character,
                target=target,
                actor_id=battle_engine.current_actor_id,
                target_id=target_id,
                hit=damage > 0,
                damage=damage,
                message=hit_message,
            )
        )
    return group


def deflect_spell(character: Any) -> str:
    training = _require_resolve_training(character, "Deflect Spell")
    if training:
        return training
    shield = _require_shield(character, "Deflect Spell")
    if shield:
        return shield
    ok, msg, _data = _spend_resolve(character, 20, "Deflect Spell")
    if not ok:
        return msg
    effect = character.stat_effects["Magic Defense"]
    effect.active = True
    effect.duration = max(int(effect.duration or 0), 3)
    effect.extra = max(int(effect.extra or 0), 6)
    combat_state(character)["deflect_spell"] = 2
    return msg + f"{character.name} prepares to deflect hostile magic.\n"


def spell_reflection_compatible(spell: Any) -> bool:
    """Return whether a hostile, targeted spell may consume the preparation."""
    if spell is None:
        return True
    if bool(getattr(spell, "unreflectable", False)):
        return False
    if getattr(spell, "reflectable", True) is False:
        return False
    if bool(getattr(spell, "area", False) or getattr(spell, "area_effect", False)):
        return False
    target_mode = str(
        getattr(spell, "target_mode", getattr(spell, "target_type", "target")) or "target"
    ).lower()
    if target_mode in {"all", "all_enemies", "area", "aoe", "self"}:
        return False
    return str(getattr(spell, "subtyp", "") or "") not in {
        "Healing",
        "Movement",
        "Support",
    }


def spell_block_ready(character: Any) -> bool:
    """Return whether a prepared projectile block can trigger."""
    return bool(
        _has_shield(character) and int(combat_state(character).get("spell_block_turns", 0) or 0) > 0
    )


def apply_spell_block(
    character: Any,
    caster: Any,
    damage: int,
    *,
    spell: Any = None,
) -> tuple[int, str]:
    """Apply Spell Block and Citadel Aegis to post-mitigation spell damage."""
    damage = max(0, int(damage or 0))
    message = ""
    state = combat_state(character)
    citadel = state.get("citadel_aegis")
    if isinstance(citadel, dict) and damage > 0:
        absorbed = max(1, int(damage * 0.50))
        damage -= absorbed
        citadel["absorbed"] = int(citadel.get("absorbed", 0) or 0) + absorbed
        message += f"{character.name}'s Citadel Aegis absorbs {absorbed} magic damage.\n"
    if not spell_block_ready(character) or not spell_reflection_compatible(spell):
        return damage, message
    state["spell_block_turns"] = 0
    state["spell_block_skip_tick"] = False
    shield_strength = max(1, int(character.check_mod("shield")))
    spell_strength = max(1, int(getattr(spell, "cost", 0) or 0) * 2)
    block_ratio = min(0.90, shield_strength / (shield_strength + spell_strength))
    blocked = min(damage, max(1, int(damage * block_ratio))) if damage else 0
    damage -= blocked
    try:
        from ...progression import has_talent

        shielding_ward = has_talent(character, "sentinel.shielding-ward")
    except Exception:
        shielding_ward = False
    if shielding_ward:
        reduced = damage // 2
        damage -= reduced
        blocked += reduced
    message += f"{character.name}'s Spell Block stops {blocked} damage.\n"
    message += record_resolve_mastery(
        character,
        "stronghold",
        "Spell Block",
    )
    skills = getattr(character, "spellbook", {}).get("Skills", {})
    if "Spell Reflection" in skills and blocked > 0:
        chance = min(
            0.75,
            0.15 + shield_strength / 100 + int(character.stats.dex) / 200,
        )
        if random.random() < chance:
            reflected = blocked
            caster.health.current = max(0, int(caster.health.current) - reflected)
            character._emit_damage_event(
                caster,
                reflected,
                damage_type="Reflected",
                ability_name="Spell Reflection",
                source="reflected",
            )
            message += f"Spell Reflection returns {reflected} damage to {caster.name}.\n"
            try:
                from ...progression import has_talent

                if has_talent(character, "stalwart.mirror-bastion"):
                    effect = character.stat_effects["Magic Defense"]
                    effect.active = True
                    effect.duration = max(2, int(effect.duration or 0))
                    effect.extra = max(50, int(effect.extra or 0))
                    message += "Mirror Bastion raises Magic Defense by 50.\n"
            except Exception:
                pass
    return damage, message


def tick_resolve_effects(character: Any) -> str:
    """Advance temporary Resolve stances and return expiry messages."""
    state = combat_state(character)
    message = ""
    for key, label in (
        ("spell_block_turns", "Spell Block"),
        ("focused_assault_turns", "Focused Assault"),
        ("purge_immunity_turns", "Purge Weakness immunity"),
        ("stronghold_turns", "Stronghold"),
    ):
        turns = int(state.get(key, 0) or 0)
        if turns <= 0:
            continue
        skip_key = key.replace("_turns", "_skip_tick")
        if state.pop(skip_key, False):
            continue
        state[key] = turns - 1
        if state[key] <= 0:
            message += f"{character.name}'s {label} expires.\n"
    boast_turns = int(state.get("boast_turns", 0) or 0)
    if boast_turns > 0:
        state["boast_turns"] = boast_turns - 1
        if state["boast_turns"] <= 0:
            pool = getattr(character, "temporary_health", None)
            remaining = (
                max(0, int(pool.get("amount", 0) or 0))
                if isinstance(pool, dict) and pool.get("source") == "Boast"
                else 0
            )
            if isinstance(pool, dict) and pool.get("source") == "Boast":
                character.temporary_health = None
            try:
                from ...progression import has_talent

                braggadocious = has_talent(character, "sentinel.braggadocious")
            except Exception:
                braggadocious = False
            if braggadocious and remaining > 0:
                starting = max(1, int(state.get("boast_starting_pool", 1) or 1))
                refund = max(1, int(20 * remaining / starting))
                message += build_resolve(character, refund, "Braggadocious")
            message += f"{character.name}'s Boast expires.\n"
    citadel = state.get("citadel_aegis")
    if isinstance(citadel, dict):
        if citadel.pop("skip_tick", False):
            return message
        citadel["turns"] = max(0, int(citadel.get("turns", 0) or 0) - 1)
        if citadel["turns"] <= 0:
            state["citadel_aegis"] = None
            absorbed = max(0, int(citadel.get("absorbed", 0) or 0))
            targets = [target for target in citadel.get("targets", ()) if target.is_alive()]
            try:
                from ...progression import has_talent

                fortified = has_talent(character, "stalwart.fortified-citadel")
            except Exception:
                fortified = False
            if fortified and absorbed and targets:
                per_target, remainder = divmod(absorbed, len(targets))
                dealt = 0
                for index, target in enumerate(targets):
                    damage = per_target + (1 if index < remainder else 0)
                    if damage <= 0:
                        continue
                    target.health.current = max(0, int(target.health.current) - damage)
                    character._emit_damage_event(
                        target,
                        damage,
                        damage_type="Non-elemental",
                        ability_name="Fortified Citadel",
                        source="field",
                    )
                    dealt += damage
                message += (
                    f"Fortified Citadel releases {dealt} absorbed damage "
                    f"across {len(targets)} enemies.\n"
                )
    return message


def _use_resolve_surge(
    character: Any,
    surge_name: str,
    target: Any | None = None,
    *,
    battle_engine: Any | None = None,
) -> str:
    if class_name(character) != "Stalwart Defender":
        return f"{surge_name} requires Stalwart Defender training.\n"
    shield = _require_shield(character, surge_name)
    if shield:
        return shield
    if not resolve_surge_unlocked(character, surge_name):
        return f"{surge_name} is still locked behind Resolve mastery.\n"
    if surge_name == "Ironwall Revenge" and target is None:
        return "There is no target for Ironwall Revenge.\n"
    data = _resolve_data(character)
    cap = resolve_cap(character)
    if int(data.get("guard_meter", 0) or 0) < cap:
        return f"{surge_name} requires a full Resolve bar.\n"
    data["guard_meter"] = 0

    if surge_name == "Citadel Aegis":
        duration = 3
        targets = ()
        if battle_engine is not None:
            targets = tuple(member.enemy for member in battle_engine.encounter.living_members)
        combat_state(character)["citadel_aegis"] = {
            "turns": duration,
            "absorbed": 0,
            "targets": targets,
            "skip_tick": True,
        }
        character.enter_defensive_stance(duration=duration)
        return (
            f"{character.name} unleashes Citadel Aegis, absorbing half of "
            "incoming magic damage for three turns.\n"
        )

    if surge_name == "Ironwall Revenge":
        damage_mod = 1.35
        skills = getattr(character, "spellbook", {}).get("Skills", {})
        crushing = "Crushing Vengeance" in skills
        if crushing:
            damage_mod = 1.60
        attacks = 4 if "Double Payback" in skills else 3
        messages = [f"{character.name} unleashes Ironwall Revenge in {attacks} strikes.\n"]
        for _index in range(attacks):
            attack_message, hit, _crit = character.weapon_damage(
                target,
                dmg_mod=damage_mod,
                use_offhand=False,
            )
            messages.append(attack_message)
            if crushing and hit:
                for name in ("Attack", "Speed"):
                    effect = target.stat_effects[name]
                    effect.active = True
                    effect.duration = max(int(effect.duration or 0), 2)
                    effect.extra = min(int(effect.extra or 0), -3)
        if crushing:
            messages.append(
                "Crushing Vengeance empowers every strike and debilitates the target.\n"
            )
        return "".join(messages)

    if surge_name == "Last Bastion":
        heal_ratio = 0.30
        barrier = cap // 2
        duration = 2
        try:
            from ...progression import has_talent

            if has_talent(character, "stalwart.final-redoubt"):
                heal_ratio = 0.40
                barrier = 75
                duration = 3
        except Exception:
            pass
        heal = max(1, int(character.health.max * heal_ratio))
        character.health.current = min(character.health.max, character.health.current + heal)
        effect = character.magic_effects["Nature Shield"]
        effect.active = True
        effect.duration = max(int(effect.duration or 0), duration)
        effect.extra = max(int(effect.extra or 0), barrier)
        character.enter_defensive_stance(duration=duration)
        return (
            f"{character.name} unleashes Last Bastion, emptying Resolve to "
            f"recover {heal} health and reset their guard.\n"
        )

    if surge_name == "Stronghold":
        state = combat_state(character)
        state["stronghold_turns"] = 3
        state["stronghold_skip_tick"] = True
        return (
            f"{character.name} becomes a Stronghold for three turns, reducing "
            "melee damage and increasing block amount by 30%.\n"
        )

    return f"{surge_name} is not a recognized Resolve Surge.\n"


def citadel_aegis(character: Any, *, battle_engine: Any | None = None) -> str:
    return _use_resolve_surge(
        character,
        "Citadel Aegis",
        battle_engine=battle_engine,
    )


def ironwall_reprisal(character: Any, target: Any | None) -> str:
    return _use_resolve_surge(character, "Ironwall Revenge", target)


def last_bastion(character: Any) -> str:
    return _use_resolve_surge(character, "Last Bastion")


def stronghold(character: Any) -> str:
    return _use_resolve_surge(character, "Stronghold")
