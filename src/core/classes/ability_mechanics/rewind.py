"""Taming, battle snapshots, and rewind mechanics."""

from __future__ import annotations

from copy import deepcopy
from typing import Any

from src.core.randomness import gameplay_random as random

from .companions import (
    _tamed_enemy_class_key,
    _with_active_tamed_companion,
    normalize_tamed_companion,
    tamed_companion_base_snapshot,
    tamed_companion_evolution_for_bond,
    tamed_companion_species,
    tamed_special_from_enemy,
)
from .equipment import TAMED_COMPANION_ROSTER_LIMIT, TAMED_COMPANION_START_BOND


def attempt_tame(character: Any, target: Any, *, rng: Any = random) -> str:
    if target is None:
        return "There is no beast to tame.\n"
    if getattr(target, "enemy_typ", None) != "Animal":
        return f"{getattr(target, 'name', 'The target')} is not tamable.\n"
    if (
        getattr(target, "boss", False)
        or getattr(target, "boss_type", None)
        or getattr(target, "class_ring_trial_enemy", False)
    ):
        return f"{target.name} resists all attempts at taming.\n"
    current_state = normalize_tamed_companion(getattr(character, "tamed_companion", None))
    roster = list(current_state.get("companions", []))
    enemy_class = _tamed_enemy_class_key(target.__class__.__name__)
    existing_index = None
    for index, companion_state in enumerate(roster):
        if companion_state.get("enemy_class") == enemy_class:
            existing_index = index
            break
    if existing_index is None and len(roster) >= TAMED_COMPANION_ROSTER_LIMIT:
        return (
            f"{character.name} cannot keep another tamed companion.\n"
            f"Release one from the Companion & Hunt tab before taming {target.name}.\n"
        )
    hp_max = max(1, int(getattr(getattr(target, "health", None), "max", 1) or 1))
    hp_ratio = max(0.0, min(1.0, getattr(target.health, "current", hp_max) / hp_max))
    low_hp_bonus = 0.35 if hp_ratio <= 0.35 else 0.0
    chance = min(0.85, 0.15 + low_hp_bonus + (character.stats.charisma * 0.015))
    if rng.random() > chance:
        return f"{character.name} fails to tame {target.name}; it refuses the signal.\n"

    state = {
        "active": True,
        "enemy_class": enemy_class,
        "name": target.name,
        "custom_name": None,
        "level": max(1, int(getattr(getattr(target, "level", None), "level", 1) or 1)),
        "bond": TAMED_COMPANION_START_BOND,
        "species": tamed_companion_species(target),
        "evolution": tamed_companion_evolution_for_bond(TAMED_COMPANION_START_BOND, enemy_class),
        "special_ability": tamed_special_from_enemy(target),
        "pending_command": None,
        "base": tamed_companion_base_snapshot(target),
    }
    if existing_index is None:
        roster.append(state)
        active_index = len(roster) - 1
        lead = f"{character.name} tames {target.name}.\n"
    else:
        existing = dict(roster[existing_index])
        bond = max(
            int(existing.get("bond", 0) or 0),
            min(100, int(existing.get("bond", 0) or 0) + TAMED_COMPANION_START_BOND),
        )
        existing.update(state)
        existing["bond"] = bond
        existing["evolution"] = tamed_companion_evolution_for_bond(
            bond, enemy_class, existing["species"]
        )
        roster[existing_index] = existing
        active_index = existing_index
        lead = f"{character.name} strengthens their bond with {target.name}.\n"
    character.tamed_companion = _with_active_tamed_companion(roster, active_index)
    try:
        from ... import companions

        character.familiar = companions.tamed_companion_from_state(character.tamed_companion)
    except Exception:
        pass
    target.tamed_by_player = True
    target.no_victory_rewards = True
    target.health.current = 0
    special = character.tamed_companion["special_ability"]
    roster_count = len(character.tamed_companion.get("companions", []))
    return (
        lead + f"{target.name} begins watching for your signals with {special}.\n"
        f"Tamed companions held: {roster_count}/{TAMED_COMPANION_ROSTER_LIMIT}.\n"
    )


def capture_battle_snapshot(engine: Any) -> dict[str, Any]:
    def character_state(character: Any) -> dict[str, Any]:
        return {
            "health": getattr(character.health, "current", 0),
            "mana": getattr(character.mana, "current", 0),
            "status_effects": deepcopy(getattr(character, "status_effects", {})),
            "physical_effects": deepcopy(getattr(character, "physical_effects", {})),
            "stat_effects": deepcopy(getattr(character, "stat_effects", {})),
            "magic_effects": deepcopy(getattr(character, "magic_effects", {})),
            "flying": getattr(character, "flying", False),
            "invisible": getattr(character, "invisible", False),
            "tunnel": getattr(character, "tunnel", False),
        }

    members = {
        member.combatant_id: {
            "character": character_state(member.enemy),
            "resolution": member.resolution,
            "resolution_cause": member.resolution_cause,
        }
        for member in engine.encounter.members
    }
    cycle = getattr(engine, "_actor_cycle", None)
    summon = getattr(engine, "summon", None)
    from .. import promotion_kits

    promotion_state = promotion_kits.combat_state(engine.player)
    return {
        "player": character_state(engine.player),
        "enemy": character_state(engine.encounter.primary_enemy),
        "members": members,
        "resolution_ledger": deepcopy(engine.encounter.resolution_ledger),
        "attacker": engine._actor_id_for(engine.attacker),
        "defender": engine._actor_id_for(engine.defender),
        "summon_active": bool(getattr(engine, "summon_active", False)),
        "summon": summon,
        "summon_state": character_state(summon) if summon is not None else None,
        "focus_target_id": getattr(engine, "_focus_target_id", None),
        "cycle": (
            {
                "order": tuple(cycle.order),
                "cursor": cycle.cursor,
                "round_number": cycle.round_number,
                "total_started_actor_turns": cycle.total_started_actor_turns,
                "readiness": dict(cycle.readiness),
                "median_speed": cycle.median_speed,
                "current_time": cycle.current_time,
                "round_pending_actor_ids": set(cycle.round_pending_actor_ids),
                "consecutive_actor_id": cycle.consecutive_actor_id,
                "consecutive_normal_turns": cycle.consecutive_normal_turns,
                "immediate_actor_id": cycle._immediate_actor_id,
                "current_actor_turn_id": getattr(engine, "_current_actor_turn_id", 0),
            }
            if cycle
            else None
        ),
        "pending_actions": {
            key: dict(value) for key, value in getattr(engine, "pending_actions", {}).items()
        },
        "delayed_spells": [dict(entry) for entry in getattr(engine, "delayed_spells", [])],
        "foresight_threads": int(promotion_state.get("foresight_threads", 0) or 0),
        "threaded_cast_pending": bool(promotion_state.get("threaded_cast_pending", False)),
    }


def store_rewind_snapshot(engine: Any) -> None:
    if getattr(engine, "attacker", None) == getattr(engine, "player", None):
        engine.player._rewind_snapshot = capture_battle_snapshot(engine)


def restore_battle_snapshot(engine: Any, snapshot: dict[str, Any]) -> str:
    if not snapshot:
        return "No foretelling has been prepared.\n"

    def restore(character: Any, state: dict[str, Any]) -> None:
        character.health.current = state["health"]
        character.mana.current = state["mana"]
        character.status_effects = deepcopy(state["status_effects"])
        character.physical_effects = deepcopy(state["physical_effects"])
        character.stat_effects = deepcopy(state["stat_effects"])
        character.magic_effects = deepcopy(state["magic_effects"])
        character.flying = state["flying"]
        character.invisible = state["invisible"]
        character.tunnel = state["tunnel"]

    restore(engine.player, snapshot["player"])
    member_states = snapshot.get("members")
    if member_states:
        for member in engine.encounter.members:
            state = member_states[member.combatant_id]
            restore(member.enemy, state["character"])
            member.resolution = state["resolution"]
            member.resolution_cause = state["resolution_cause"]
        engine.encounter._resolution_ledger = list(deepcopy(snapshot.get("resolution_ledger", ())))
    else:
        restore(engine.encounter.primary_enemy, snapshot["enemy"])
    engine.summon_active = bool(snapshot.get("summon_active", False))
    engine.summon = snapshot.get("summon")
    if engine.summon is not None and snapshot.get("summon_state"):
        restore(engine.summon, snapshot["summon_state"])
    cycle_state = snapshot.get("cycle")
    if cycle_state and getattr(engine, "_actor_cycle", None):
        engine._actor_cycle.order = tuple(cycle_state["order"])
        engine._actor_cycle.cursor = cycle_state["cursor"]
        engine._actor_cycle.round_number = cycle_state["round_number"]
        engine._actor_cycle.total_started_actor_turns = cycle_state["total_started_actor_turns"]
        engine._actor_cycle.readiness = dict(cycle_state.get("readiness", {}))
        engine._actor_cycle.median_speed = float(cycle_state.get("median_speed", 1.0))
        engine._actor_cycle.current_time = float(cycle_state.get("current_time", 0.0))
        engine._actor_cycle.round_pending_actor_ids = set(
            cycle_state.get("round_pending_actor_ids", ())
        )
        engine._actor_cycle.consecutive_actor_id = cycle_state.get("consecutive_actor_id")
        engine._actor_cycle.consecutive_normal_turns = int(
            cycle_state.get("consecutive_normal_turns", 0)
        )
        engine._actor_cycle._immediate_actor_id = cycle_state.get("immediate_actor_id")
        engine._current_actor_turn_id = cycle_state["current_actor_turn_id"]
    engine._focus_target_id = snapshot.get(
        "focus_target_id",
        engine.encounter.primary_member.combatant_id,
    )
    engine.pending_actions = {
        key: dict(value) for key, value in snapshot.get("pending_actions", {}).items()
    }
    engine.delayed_spells = [dict(entry) for entry in snapshot.get("delayed_spells", [])]
    engine._forced_cancellation = None
    engine._forced_cancellation_actor_id = None
    engine._forced_cancellation_turn_id = 0
    engine._reaction_executions = set()
    from .. import promotion_kits

    promotion_state = promotion_kits.combat_state(engine.player)
    promotion_state["foresight_threads"] = max(
        0,
        int(snapshot.get("foresight_threads", 0) or 0),
    )
    promotion_state["threaded_cast_pending"] = bool(snapshot.get("threaded_cast_pending", False))
    if getattr(engine.player, "_threaded_cast_context", None):
        promotion_state["foresight_threads"] = 0
        promotion_state["threaded_cast_pending"] = False
    if getattr(engine, "_actor_cycle", None):
        engine._sync_actor_aliases()
    else:
        attacker_id = snapshot.get("attacker")
        engine.attacker = (
            engine.player if attacker_id == "player" else engine.encounter.primary_enemy
        )
        defender_id = snapshot.get("defender")
        engine.defender = (
            engine.player if defender_id == "player" else engine.encounter.primary_enemy
        )
    engine.player._foretell_snapshot = None
    return "Time folds back to the foretold moment.\n"


def restore_rewind_snapshot(engine: Any) -> str:
    snapshot = getattr(engine.player, "_rewind_snapshot", None)
    if not snapshot:
        return "No previous choice point can be rewound.\n"
    message = restore_battle_snapshot(engine, snapshot)
    engine.player._rewind_snapshot = None
    return message.replace("foretold moment", "previous choice point")
