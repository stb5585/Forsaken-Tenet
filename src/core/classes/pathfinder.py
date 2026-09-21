"""Pathfinder class definition."""

from __future__ import annotations

from copy import deepcopy
from typing import Any

from src.core.randomness import gameplay_random as random

from .. import items
from .base import Job

ELEMENTAL_DAMAGE_TYPES = frozenset(
    {
        "Fire",
        "Water",
        "Earth",
        "Wind",
        "Ice",
        "Electric",
    }
)
UNNATURAL_ENEMY_TYPES = frozenset({"Slime", "Monster", "Undead", "Aberration"})
CREATURE_COMFORT_STEPS = 50


def has_skill(character: Any, name: str) -> bool:
    """Return whether a character knows a named Pathfinder-tree skill."""
    return name in getattr(character, "spellbook", {}).get("Skills", {})


def has_ranger_talent(character: Any, talent_key: str) -> bool:
    """Return whether a character purchased a Ranger tree talent."""
    try:
        from ..progression import has_talent

        return has_talent(character, talent_key)
    except (AttributeError, KeyError, TypeError):
        return False


def is_unnatural_enemy(enemy: Any | None) -> bool:
    """Return whether an enemy belongs to Ranger's unnatural quarry group."""
    return str(getattr(enemy, "enemy_typ", "") or "") in UNNATURAL_ENEMY_TYPES


def is_favored_enemy(character: Any, enemy: Any | None) -> bool:
    """Return whether an enemy matches the character's current quarry type."""
    if enemy is None or not has_skill(character, "Favored Enemy"):
        return False
    from . import ability_mechanics

    return str(getattr(enemy, "enemy_typ", "") or "") == ability_mechanics.favorite_enemy_type(
        character
    )


def wild_sense_report(character: Any, enemy: Any | None) -> str:
    """Describe a favored enemy with detail scaled by Tracking Mastery."""
    if enemy is None:
        return "Wild Sense needs a target.\n"
    if not is_favored_enemy(character, enemy):
        return f"{enemy.name} is not your favored enemy type.\n"
    from . import ability_mechanics

    detail = ability_mechanics.favored_enemy_practice_bonus(character)
    lines = [
        f"Wild Sense: {enemy.name} — {enemy.enemy_typ}.",
        f"Vitality: {enemy.health.current}/{enemy.health.max} HP.",
    ]
    combat = getattr(enemy, "combat", None)
    if detail >= 3 and combat is not None:
        lines.append(
            "Combat profile: "
            f"Attack {getattr(combat, 'attack', 0)}, "
            f"Defense {getattr(combat, 'defense', 0)}, "
            f"Magic {getattr(combat, 'magic', 0)}, Magic Defense "
            f"{getattr(combat, 'magic_def', 0)}."
        )
    if detail >= 5:
        resistances = [
            f"{name} {int(float(value) * 100):+d}%"
            for name, value in sorted((getattr(enemy, "resistance", {}) or {}).items())
            if float(value or 0)
        ]
        resistance_text = ", ".join(resistances) if resistances else "none observed"
        lines.append(f"Resistances: {resistance_text}.")
    if detail >= 7:
        known = []
        for book in (getattr(enemy, "spellbook", {}) or {}).values():
            if isinstance(book, dict):
                known.extend(str(name) for name in book)
        technique_text = ", ".join(sorted(known)) if known else "none"
        lines.append(f"Known techniques: {technique_text}.")
    return "\n".join(lines) + "\n"


def ranger_weapon_damage_multiplier(character: Any, enemy: Any | None) -> float:
    """Return Hunt and two-handed multipliers for a weapon or crossbow hit."""
    if not is_favored_enemy(character, enemy):
        return 1.0
    multiplier = 1.0
    if has_ranger_talent(character, "ranger.quarrys-bane"):
        multiplier *= 1.10
    weapon = getattr(character, "equipment", {}).get("Weapon")
    if (
        has_ranger_talent(character, "beast-master.heavy-hunter")
        and int(getattr(weapon, "handed", 1) or 1) == 2
    ):
        multiplier *= 1.15
    if has_ranger_talent(character, "beast-master.coordinated-assault"):
        from . import ability_mechanics

        if ability_mechanics.has_living_tamed_companion(character):
            multiplier *= 1.10
    from . import ability_mechanics

    if (
        has_ranger_talent(character, "ranger.apex-hunter")
        and ability_mechanics.favored_enemy_rank(
            ability_mechanics.favored_enemy_state(character).get("practice", 0)
        )
        == "Mastered Trail"
    ):
        multiplier *= 1.10
    return multiplier


def ranger_damage_reduction(
    defender: Any,
    attacker: Any | None,
    damage: int,
    *,
    physical: bool,
) -> tuple[int, str]:
    """Apply Ranger defensive talents, including per-action Combo Breaker stacks."""
    if damage <= 0:
        return damage, ""
    multiplier = 1.0
    labels = []
    if has_ranger_talent(defender, "beast-master.trail-guard") and is_favored_enemy(
        defender,
        attacker,
    ):
        multiplier *= 0.90
        labels.append("Trail Guard")
    if physical and has_ranger_talent(defender, "ranger.braced-grip"):
        weapon = getattr(defender, "equipment", {}).get("Weapon")
        if int(getattr(weapon, "handed", 1) or 1) == 2:
            multiplier *= 0.92
            labels.append("Braced Grip")
    if has_ranger_talent(defender, "ranger.companion-cover"):
        from . import ability_mechanics

        if ability_mechanics.has_living_tamed_companion(defender):
            multiplier *= 0.92
            labels.append("Companion Cover")
    hit_index = int(getattr(defender, "_ranger_incoming_hit_count", 0) or 0)
    if has_ranger_talent(defender, "ranger.combo-breaker"):
        combo_reduction = min(0.32, 0.08 * hit_index)
        if combo_reduction:
            multiplier *= 1.0 - combo_reduction
            labels.append(f"Combo Breaker {int(combo_reduction * 100)}%")
    defender._ranger_incoming_hit_count = hit_index + 1
    reduced_damage = max(0, int(damage * multiplier))
    reduced = damage - reduced_damage
    if reduced <= 0 or not labels:
        return reduced_damage, ""
    label_text = ", ".join(labels)
    return reduced_damage, (f"{defender.name}'s {label_text} reduces damage by {reduced}.\n")


def ability_damage_types(ability: Any) -> frozenset[str]:
    """Return every declared damage/school type attached to an ability."""
    types = {str(value) for value in getattr(ability, "damage_types", ()) if value}
    for attribute in ("damage_type", "subtyp", "school"):
        value = str(getattr(ability, attribute, "") or "")
        if value:
            types.add(value)
    return frozenset(types)


def is_elemental_ability(ability: Any) -> bool:
    """Return whether an ability qualifies as an offensive elemental spell."""
    return bool(ability_damage_types(ability) & ELEMENTAL_DAMAGE_TYPES)


def start_combat(character: Any) -> None:
    """Reset encounter-local Pathfinder mechanics."""
    character._conversion_critical_bonus = 0.0
    character._intensify_element = None
    character._primal_trance_active = False
    character._primal_trance_multiplier = 1.0
    character._control_z_snapshot = None
    character._incoming_action_snapshot = None
    character._ranger_incoming_hit_count = 0


def spell_output_multiplier(character: Any, ability: Any) -> float:
    """Resolve Fundamental Harmony, Intensify Elements, and Primal Trance."""
    multiplier = 1.0
    types = ability_damage_types(ability)
    if has_skill(character, "Fundamental Harmony") and types & ELEMENTAL_DAMAGE_TYPES:
        multiplier *= 1.20
    intensified = getattr(character, "_intensify_element", None)
    if intensified and intensified in types:
        multiplier *= 1.35
        character._intensify_element = None
    multiplier *= max(1.0, float(getattr(character, "_primal_trance_multiplier", 1.0)))
    return multiplier


def record_elemental_spell_damage(character: Any, damage_type: str) -> None:
    """Prime Conversion after the character deals elemental spell damage."""
    if has_skill(character, "Conversion") and damage_type in ELEMENTAL_DAMAGE_TYPES:
        character._conversion_critical_bonus = 0.50


def consume_conversion(character: Any) -> float:
    """Consume Conversion's bonus on the next melee attack."""
    bonus = max(0.0, float(getattr(character, "_conversion_critical_bonus", 0.0)))
    character._conversion_critical_bonus = 0.0
    return bonus


def record_elemental_damage_taken(character: Any, damage_type: str) -> None:
    """Remember incoming elemental damage for Intensify Elements."""
    if has_skill(character, "Intensify Elements") and damage_type in ELEMENTAL_DAMAGE_TYPES:
        character._intensify_element = damage_type


def chronology_initiative_bonus(character: Any) -> int:
    """Return the standard Intelligence modifier for Chronology."""
    if not has_skill(character, "Chronology"):
        return 0
    return (int(getattr(character.stats, "intel", 10)) - 10) // 2


def melee_damage_multiplier(character: Any) -> float:
    """Return Razor Talons' outgoing melee damage multiplier."""
    return 1.10 if has_skill(character, "Razor Talons") else 1.0


def enhance_melee_bleed(character: Any, target: Any) -> None:
    """Increase an active Bleed newly caused by a Razor Talons melee ability."""
    if not has_skill(character, "Razor Talons"):
        return
    bleed = getattr(target, "physical_effects", {}).get("Bleed")
    if bleed is not None and bleed.active:
        bleed.extra = max(1, int(float(bleed.extra or 0) * 1.25))


def counterattack_dodge_bonus(character: Any) -> float:
    """Return Cautious Assault's dodge bonus against counterattacks."""
    return 0.20 if has_skill(character, "Cautious Assault") else 0.0


def bounce_back_bonus(character: Any) -> int:
    """Return the extra Prone-duration recovery supplied by Bounce Back."""
    return 1 if has_skill(character, "Bounce Back") else 0


def spell_damage(
    caster: Any,
    target: Any,
    ability: Any,
    *,
    damage_type: str,
    damage_modifier: float,
    rng: Any | None = None,
) -> tuple[str, int]:
    """Resolve a Pathfinder spell through magic defense and typed resistance."""
    generator = rng or random
    if target.magic_effects["Ice Block"].active or target.tunnel:
        return "The spell has no effect.\n", 0
    contact = caster.resolve_contact(target, typ="magic", rng=generator)
    if not contact.hit:
        if contact.attribution is not None and contact.attribution.value == "dodge":
            return f"{target.name} dodges the spell.\n", 0
        return f"{caster.name}'s spell misses {target.name}.\n", 0
    raw = max(1, int(caster.check_mod("magic", enemy=target) * damage_modifier))
    hit, message, damage = target.damage_reduction(raw, caster, typ=damage_type)
    if not hit:
        return message, 0
    damage = max(0, int(damage * spell_output_multiplier(caster, ability)))
    target.health.current -= damage
    caster._emit_damage_event(
        target,
        damage,
        damage_type=damage_type,
        source="spell",
        attack_source="spell",
        ability_name=ability.name,
    )
    return (
        message + f"{caster.name} deals {damage} {damage_type} damage to {target.name}.\n",
        damage,
    )


def suppress_shapeshifting(target: Any) -> str:
    """Restore a shifted enemy snapshot and prevent further shifts this combat."""
    target.shapeshift_suppressed = True
    snapshot = getattr(target, "_shapeshift_original_state", None)
    if not isinstance(snapshot, dict):
        return f"{target.name} cannot shapeshift for the rest of combat.\n"
    shifted_name = target.name
    for attribute, value in snapshot.items():
        setattr(target, attribute, value)
    target.shapeshift_suppressed = True
    shifted = target.status_effects.get("Shapeshifted")
    if shifted is not None:
        shifted.active = False
        shifted.duration = 0
    return f"Moonlight forces {shifted_name} back into its original form as {target.name}.\n"


def ensnare_with_vine(caster: Any, target: Any) -> str:
    """Attach a three-attempt Thorny Vine escape state."""
    target._thorny_vine = {
        "caster": caster,
        "turns": 3,
        "difficulty": max(8, int(caster.stats.wisdom)),
        "damage": max(1, int(caster.check_mod("magic", enemy=target) * 0.35)),
    }
    return f"A thorny vine coils around {target.name}.\n"


def tick_thorny_vine(character: Any, *, rng: Any | None = None) -> str:
    """Attempt to escape Thorny Vine, dealing Nature damage on failure."""
    state = getattr(character, "_thorny_vine", None)
    if not isinstance(state, dict):
        return ""
    generator = rng or random
    strength = int(getattr(character.stats, "strength", 1))
    if generator.randint(1, 20) + ((strength - 10) // 2) >= int(state["difficulty"]):
        character._thorny_vine = None
        return f"{character.name} tears free of the thorny vine.\n"
    damage = max(1, int(state["damage"]))
    caster = state.get("caster")
    _hit, reduction, damage = character.damage_reduction(damage, caster, typ="Nature")
    character.health.current -= damage
    if caster is not None:
        caster._emit_damage_event(
            character,
            damage,
            damage_type="Nature",
            source="Thorny Vine",
            ability_name="Thorny Vine",
        )
    state["turns"] = int(state["turns"]) - 1
    if state["turns"] <= 0:
        character._thorny_vine = None
    return reduction + f"The vine's thorns deal {damage} Nature damage to {character.name}.\n"


def poison_strike(
    caster: Any,
    target: Any,
    ability: Any,
    *,
    rng: Any | None = None,
) -> tuple[str, int]:
    """Resolve Poison Strike's main-hand bite and secondary poison damage."""
    generator = rng or random
    contact = caster.resolve_contact(target, typ="weapon", rng=generator)
    if not contact.hit:
        return f"{caster.name}'s transformed fangs miss {target.name}.\n", 0
    bite_message, _hit, _crit = caster.weapon_damage(
        target,
        dmg_mod=0.85,
        hit=True,
        use_offhand=False,
    )
    bite = int(getattr(caster, "_last_weapon_primary_damage", 0) or 0)
    poison_raw = max(1, int(caster.check_mod("magic", enemy=target) * 0.40))
    _hit, poison_message, poison = target.damage_reduction(
        poison_raw,
        caster,
        typ="Poison",
    )
    poison = max(0, int(poison * spell_output_multiplier(caster, ability)))
    target.health.current -= poison
    caster._emit_damage_event(
        target,
        poison,
        damage_type="Poison",
        source="spell",
        attack_source="spell",
        ability_name="Poison Strike",
    )
    status = target.status_effects["Poison"]
    if not target.has_status_protection("Poison"):
        status.active = True
        status.duration = max(3, int(status.duration or 0))
        status.extra = max(int(status.extra or 0), max(1, poison // 3))
        status.source = "Poison Strike"
    message = f"{caster.name} grows giant fangs and bites.\n" + bite_message + poison_message
    message += f"The bite deals {poison} additional poison damage.\n"
    return message, bite + poison


def spirit_strike(caster: Any, target: Any) -> tuple[str, int]:
    """Resolve a main-hand attack plus Wisdom-difference spirit damage."""
    message, hit, crit = caster.weapon_damage(target, use_offhand=False)
    damage = int(getattr(caster, "_last_weapon_primary_damage", 0) or 0)
    if not hit:
        return message, damage
    difference = int(caster.stats.wisdom) - int(target.stats.wisdom)
    if difference <= 0:
        return message, damage
    spirit = max(1, int(difference * (1.0 if crit > 1 else 0.75)))
    _hit, reduction, spirit = target.damage_reduction(spirit, caster, typ="Nature")
    target.health.current -= spirit
    caster._emit_damage_event(
        target,
        spirit,
        damage_type="Nature",
        source="skill",
        ability_name="Spirit Strike",
    )
    return message + reduction + f"Spirit Strike adds {spirit} Nature damage.\n", damage + spirit


def call_animal(character: Any, cost: int, *, rng: Any | None = None) -> str:
    """Create a location-aware transient animal companion."""
    if character.mana.current < cost:
        return f"{character.name} does not have enough mana.\n"
    from . import mage_mechanics

    companion = mage_mechanics.conjure_standard_companion(
        character,
        "Animal",
        source="Call Animal",
        rng=rng or random,
    )
    if companion is None:
        return "No local animal answers the call.\n"
    character.mana.current -= cost
    return (
        f"A {companion['name']} answers {character.name}'s call for "
        f"{companion['steps_remaining']} steps.\n"
    )


def activate_creature_comforts(character: Any, cost: int) -> str:
    """Start Creature Comforts' animal-encounter pacification duration."""
    if character.mana.current < cost:
        return f"{character.name} does not have enough mana.\n"
    character.mana.current -= cost
    character.creature_comfort_steps = CREATURE_COMFORT_STEPS
    return f"Nearby animals are pacified for {CREATURE_COMFORT_STEPS} steps.\n"


def animal_avoids_encounter(
    character: Any,
    enemy: Any,
    *,
    rng: Any | None = None,
) -> bool:
    """Return whether an Animal encounter declines to attack."""
    if int(getattr(character, "creature_comfort_steps", 0) or 0) <= 0:
        return False
    if str(getattr(enemy, "enemy_typ", "")) != "Animal":
        return False
    return (rng or random).random() < 0.75


def pacify_combat_animals(character: Any, battle_engine: Any, cost: int) -> str:
    """Attempt to peacefully remove ordinary Animal enemies from combat."""
    if character.mana.current < cost:
        return f"{character.name} does not have enough mana.\n"
    character.mana.current -= cost
    pacified = 0
    for member in list(battle_engine.encounter.living_members):
        enemy = member.enemy
        if str(getattr(enemy, "enemy_typ", "")) != "Animal":
            continue
        if getattr(enemy, "boss", False) or getattr(enemy, "boss_type", None):
            continue
        enemy.no_victory_rewards = True
        enemy.health.current = 0
        pacified += 1
    return f"Creature Comforts persuades {pacified} animal(s) to leave combat.\n"


def activate_superstitious_barrier(
    character: Any,
    status_name: str,
    duration: int,
    *,
    rng: Any | None = None,
) -> str:
    """Possibly create a barrier when a negative status is applied."""
    if not has_skill(character, "Very Superstitious"):
        return ""
    if status_name in {"Defend", "Peaceful"} or (rng or random).random() >= 0.35:
        return ""
    amount = max(1, int(character.health.max * 0.15))
    character._superstitious_barrier = {
        "amount": amount,
        "status": status_name,
        "turns": max(1, int(duration or 1)),
    }
    return f"Very Superstitious raises a {amount}-point damage barrier.\n"


def absorb_superstitious_barrier(character: Any, damage: int) -> tuple[int, str]:
    """Absorb incoming damage with an active superstition barrier."""
    barrier = getattr(character, "_superstitious_barrier", None)
    if not isinstance(barrier, dict) or damage <= 0:
        return damage, ""
    absorbed = min(int(damage), max(0, int(barrier.get("amount", 0) or 0)))
    barrier["amount"] = int(barrier.get("amount", 0) or 0) - absorbed
    if barrier["amount"] <= 0:
        character._superstitious_barrier = None
    return damage - absorbed, f"The superstitious barrier absorbs {absorbed} damage.\n"


def begin_primal_trance(character: Any) -> None:
    """Apply Primal Trance's prone treatment without blocking its forced cast."""
    character._primal_trance_active = True
    character._primal_trance_multiplier = 1.0
    prone = character.physical_effects["Prone"]
    prone.active = True
    prone.duration = -1
    prone.source = "Primal Trance"


def end_primal_trance(character: Any) -> None:
    """Clear Primal Trance's temporary prone state and multiplier."""
    character._primal_trance_active = False
    character._primal_trance_multiplier = 1.0
    prone = character.physical_effects["Prone"]
    if prone.source == "Primal Trance":
        prone.active = False
        prone.duration = 0
        prone.source = ""


def primal_trance_cast(
    character: Any,
    target: Any,
    rank: int,
    *,
    rng: Any | None = None,
) -> str:
    """Cast one random learned elemental offensive spell without paying mana."""
    spells = [
        spell
        for spell in getattr(character, "spellbook", {}).get("Spells", {}).values()
        if is_elemental_ability(spell)
        and getattr(spell, "subtyp", "") not in {"Heal", "Support", "Status"}
        and callable(getattr(spell, "cast", None))
    ]
    if not spells:
        return "No learned offensive elemental spell answers the trance.\n"
    character._primal_trance_multiplier = 1.0 + (max(1, rank) - 1) * 0.25
    spell = (rng or random).choice(spells)
    result = spell.cast(character, target, special=True)
    return f"Primal Trance invokes {spell.name} at rank {rank}.\n{result}"


def geomancy_combat(character: Any, target: Any) -> str:
    """Report whether the target matters to an active quest or bounty."""
    if target is None:
        return "The earth senses no enemy to interpret.\n"
    from ..map_tiles.rules import active_random_encounter_quest_targets

    useful = target.name in active_random_encounter_quest_targets(character)
    return (
        f"The earth confirms that {target.name} carries useful quest or bounty information.\n"
        if useful
        else f"The earth senses no current quest or bounty value in {target.name}.\n"
    )


def geomancy_exploration(character: Any) -> str:
    """Point toward the nearest unfinished or unexplored useful map tile."""
    world = getattr(character, "world_dict", {}) or {}
    origin = (
        int(getattr(character, "location_x", 0)),
        int(getattr(character, "location_y", 0)),
        int(getattr(character, "location_z", 0)),
    )
    candidates = []
    for position, tile in world.items():
        if len(position) != 3 or position[2] != origin[2] or position == origin:
            continue
        unfinished = any(
            [
                hasattr(tile, "enemy") and getattr(tile, "enemy", None) is not None,
                hasattr(tile, "open") and not getattr(tile, "open", False),
                hasattr(tile, "read") and not getattr(tile, "read", False),
                hasattr(tile, "defeated") and not getattr(tile, "defeated", False),
                not getattr(tile, "visited", False),
            ]
        )
        if unfinished and getattr(tile, "enter", True):
            distance = abs(position[0] - origin[0]) + abs(position[1] - origin[1])
            candidates.append((distance, position))
    if not candidates:
        return "The ground reveals no useful location on this floor.\n"
    _distance, destination = min(candidates)
    dx = destination[0] - origin[0]
    dy = destination[1] - origin[1]
    direction = (
        "east"
        if abs(dx) >= abs(dy) and dx > 0
        else "west" if abs(dx) >= abs(dy) else "south" if dy > 0 else "north"
    )
    character._geomancy_target = destination
    return f"Lines of earthen light point {direction} toward a useful location.\n"


def record_incoming_action_start(character: Any) -> None:
    """Snapshot player state immediately before an enemy action."""
    character._ranger_incoming_hit_count = 0
    character._incoming_action_snapshot = {
        "health": int(character.health.current),
        "mana": int(character.mana.current),
        "status_effects": deepcopy(character.status_effects),
        "physical_effects": deepcopy(character.physical_effects),
        "stat_effects": deepcopy(character.stat_effects),
        "magic_effects": deepcopy(character.magic_effects),
    }


def record_incoming_action_end(character: Any, health_before: int) -> None:
    """Retain the pre-action snapshot only when the action caused damage."""
    snapshot = getattr(character, "_incoming_action_snapshot", None)
    if isinstance(snapshot, dict) and int(character.health.current) < int(health_before):
        character._control_z_snapshot = snapshot
    character._incoming_action_snapshot = None
    character._ranger_incoming_hit_count = 0


def control_z(character: Any) -> str:
    """Restore state from immediately before the most recent damaging action."""
    snapshot = getattr(character, "_control_z_snapshot", None)
    if not isinstance(snapshot, dict):
        return "There is no damaging action for Control Z to undo.\n"
    character.health.current = snapshot["health"]
    character.mana.current = snapshot["mana"]
    character.status_effects = deepcopy(snapshot["status_effects"])
    character.physical_effects = deepcopy(snapshot["physical_effects"])
    character.stat_effects = deepcopy(snapshot["stat_effects"])
    character.magic_effects = deepcopy(snapshot["magic_effects"])
    character._control_z_snapshot = None
    return "Time rewinds the last damaging action against you.\n"


def tick_exploration(character: Any, steps: int) -> None:
    """Advance Pathfinder exploration-duration effects."""
    remaining = max(
        0,
        int(getattr(character, "creature_comfort_steps", 0) or 0) - max(0, int(steps)),
    )
    character.creature_comfort_steps = remaining


def tick_combat_state(character: Any, *, end: bool = False) -> str:
    """Advance or clear encounter-local Pathfinder effects."""
    message = ""
    if end:
        end_primal_trance(character)
        for attribute in (
            "_conversion_critical_bonus",
            "_intensify_element",
            "_control_z_snapshot",
            "_incoming_action_snapshot",
            "_thorny_vine",
            "_superstitious_barrier",
        ):
            if hasattr(character, attribute):
                delattr(character, attribute)
        return message
    message += tick_thorny_vine(character)
    barrier = getattr(character, "_superstitious_barrier", None)
    if isinstance(barrier, dict):
        status_name = str(barrier.get("status", ""))
        status = character.status_effects.get(status_name)
        physical = character.physical_effects.get(status_name)
        active = bool(
            (status is not None and status.active) or (physical is not None and physical.active)
        )
        barrier["turns"] = max(0, int(barrier.get("turns", 0) or 0) - 1)
        if not active or barrier["turns"] <= 0:
            character._superstitious_barrier = None
            message += f"{character.name}'s superstitious barrier fades.\n"
    return message


class Pathfinder(Job):
    """
    Promotion: Pathfinder -> Druid   -> Lycan
                          |          |
                          |          -> Archdruid
                          |
                          -> Diviner -> Astromancer
                          |
                          -> Shaman  -> Soulcatcher
                          |
                          -> Ranger  -> Beast Master
    """

    def __init__(self):
        super().__init__(
            name="Pathfinder",
            description="In philosophy, naturalism is the belief that only natural laws"
            " and forces operate in the universe. A pathfinder embraces "
            "this idea by being attuned to one or more of the various "
            "aspects of nature, mainly the 4 classical elements: Earth, "
            "Wind, Water, and Fire.",
            str_plus=0,
            int_plus=1,
            wis_plus=1,
            con_plus=1,
            cha_plus=1,
            dex_plus=1,
            att_plus=1,
            def_plus=1,
            magic_plus=2,
            magic_def_plus=2,
            equipment={
                "Weapon": items.Dirk(),
                "OffHand": items.Buckler(),
                "Armor": items.HideArmor(),
            },
            restrictions={
                "Weapon": ["Dagger", "Club", "Polearm", "Hammer", "Staff"],
                "OffHand": ["Shield", "Tome"],
                "Armor": ["Cloth", "Light", "Medium"],
            },
            pro_level=1,
        )
