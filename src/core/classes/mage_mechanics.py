"""Shared Mage specialization, enhancement, and transient-conjuration rules."""

from __future__ import annotations

import math
from typing import Any

from src.core.randomness import gameplay_random as random

ELEMENTAL_SCHOOLS = ("Fire", "Ice", "Electric", "Wind", "Water", "Earth")
ENHANCEMENT_BY_SCHOOL = {
    "Fire": "Fire Inside",
    "Ice": "Frozen Armor",
    "Electric": "Electrified",
    "Wind": "Wind Currents",
    "Water": "Refreshment",
    "Earth": "Terra Firma",
}
TRANSIENT_SUMMON_STEPS = 50
TORCHLIGHT_STEPS = 50
TORCHLIGHT_ENCOUNTER_MULTIPLIER = 0.50
ENHANCEMENT_PROC_CHANCE = 0.20
RANDOM_SCHOOL_RIDERS: dict[tuple[str, str], float] = {
    ("Electric", "Paralyzer"): 0.25,
    ("Wind", "Ejection Gale"): 0.25,
    ("Ice", "Subzero"): 0.25,
    ("Water", "Unrelenting Waves"): 0.35,
}

CALLING_ENEMY_TYPE_PREFERENCES = {
    "Animal": ("Animal",),
    "Humanoid": ("Humanoid",),
    "Monster": ("Monster",),
    "Spirit": ("Elemental", "Undead"),
    "Fiend": ("Fiend", "Fey"),
    "Celestial": ("Celestial", "Fey", "Humanoid"),
    "Dragon": ("Dragon",),
}


def has_skill(character: Any, name: str) -> bool:
    """Return whether the character learned a named Mage passive."""
    return name in getattr(character, "spellbook", {}).get("Skills", {})


def has_talent(character: Any, key: str) -> bool:
    """Return whether a named progression talent is owned."""
    try:
        from ..progression import has_talent as progression_has_talent

        return progression_has_talent(character, key)
    except Exception:
        return False


def enhance_blade_bonus(character: Any) -> int:
    """Return Tome-warrior bonus damage from current mana percentage."""
    if not has_skill(character, "Enhance Blade"):
        return 0
    weapon = getattr(character, "equipment", {}).get("Weapon")
    base_damage = max(0, int(getattr(weapon, "damage", 0) or 0))
    mana = getattr(character, "mana", None)
    maximum = max(1, int(getattr(mana, "max", 1) or 1))
    current = max(0, min(maximum, int(getattr(mana, "current", 0) or 0)))
    return int(base_damage * (current / maximum))


def enhance_armor_bonus(character: Any) -> int:
    """Return bonus physical armor from the character's missing mana."""
    if not has_skill(character, "Enhance Armor"):
        return 0
    armor = getattr(character, "equipment", {}).get("Armor")
    base_armor = max(0, int(getattr(armor, "armor", 0) or 0))
    mana = getattr(character, "mana", None)
    maximum = max(1, int(getattr(mana, "max", 1) or 1))
    current = max(0, min(maximum, int(getattr(mana, "current", 0) or 0)))
    return int(base_armor * (1.0 - (current / maximum)))


def specialization(character: Any) -> str | None:
    """Return the selected Sorcerer specialization, if any."""
    if has_skill(character, "Classical Force"):
        return "Elemental"
    if has_skill(character, "Arcane Tradition"):
        return "Arcane"
    return None


def school_from_ability(ability: Any) -> str | None:
    """Resolve elemental and Arcane schools without changing resistance types."""
    for candidate in (
        getattr(ability, "subtyp", None),
        getattr(ability, "school", None),
        getattr(ability, "damage_type", None),
    ):
        if str(candidate) in ELEMENTAL_SCHOOLS:
            return str(candidate)
        if str(candidate) == "Arcane":
            return "Arcane"
    if getattr(ability, "name", "") in {
        "Magic Missile",
        "Magic Missile II",
        "Magic Missile III",
        "Mana Rupture",
        "Gravitational Pull",
        "Polymorph",
        "Mana Shield",
        "Imbue Weapon",
    }:
        return "Arcane"
    return None


def spell_potency_multiplier(character: Any, ability: Any) -> float:
    """Apply specialization and advanced off-school potency reductions."""
    chosen = specialization(character)
    school = school_from_ability(ability)
    if chosen == "Elemental" and school == "Arcane":
        return 0.50 if has_skill(character, "Classical Enrichment") else 0.75
    if chosen == "Arcane" and school in ELEMENTAL_SCHOOLS:
        return 0.50 if has_skill(character, "Arcane Ritual") else 0.75
    return 1.0


def arcane_potency_multiplier(character: Any) -> float:
    """Return Arcane barrier/enhancement potency after specialization."""
    if specialization(character) != "Elemental":
        return 1.0
    return 0.50 if has_skill(character, "Classical Enrichment") else 0.75


def spell_mana_cost(character: Any, ability: Any) -> int:
    """Return the effective mana cost after Arcane specialization passives."""
    cost = max(0, int(getattr(ability, "cost", 0) or 0))
    if has_skill(character, "Force Multiplier") and _is_magic_missile(ability):
        cost = math.ceil(cost * 1.25)
    if int(getattr(character, "mystical_vitality_turns", 0) or 0) > 0:
        cost = math.ceil(cost * 0.75)
    return cost


def spell_damage_multiplier(
    character: Any,
    ability: Any,
    target: Any | None = None,
) -> float:
    """Return authored Mage-talent damage scaling for a spell."""
    multiplier = 1.0
    try:
        from . import astromancer

        multiplier *= 1.0 + astromancer.threaded_bonus(character, "output")
    except Exception:
        pass
    if str(getattr(ability, "name", "")).startswith("Shadow Bolt") and has_talent(
        character, "mage.forbidden-studies"
    ):
        multiplier *= 1.20
    if (
        str(getattr(ability, "name", "")).startswith("Shadow Bolt")
        and has_skill(character, "Impending Demise")
        and target is not None
    ):
        doom = getattr(target, "status_effects", {}).get("Doom")
        turns = int(getattr(doom, "duration", 0) or 0)
        if getattr(doom, "active", False) and turns > 0:
            multiplier *= 1 + (0.50 / turns)
    if str(getattr(ability, "name", "")) == "Terrify" and has_skill(
        character,
        "Night Terror",
    ):
        sleeping = getattr(target, "status_effects", {}).get("Sleep") if target else None
        multiplier *= 1.50 if getattr(sleeping, "active", False) else 1.25
    if (
        school_from_ability(ability) == "Shadow"
        and int(getattr(character, "warlock_eclipse_turns", 0) or 0) > 0
    ):
        multiplier *= 1.15
    if has_skill(character, "Force Multiplier") and _is_magic_missile(ability):
        multiplier *= 1.25
    if has_skill(character, "Arcane Empowerment"):
        stacks = min(5, max(0, int(_combat_state(character).get("arcane_empowerment", 0))))
        multiplier *= 1 + (stacks * 0.05)
    if (
        school_from_ability(ability) == "Electric"
        and has_skill(character, "Divine Wind")
        and target is not None
        and getattr(target.physical_effects.get("Prone"), "source", "") == "Divine Wind"
    ):
        multiplier *= 2.0
    return multiplier


def consume_shadow_overheal_bonus(character: Any, ability: Any) -> int:
    """Consume Resource Abuse's stored overheal on a damaging Shadow spell."""
    if school_from_ability(ability) != "Shadow":
        return 0
    bonus = max(0, int(getattr(character, "resource_abuse_shadow_bonus", 0) or 0))
    character.resource_abuse_shadow_bonus = 0
    return bonus


def record_spell_damage_hit(
    character: Any,
    target: Any | None = None,
    metadata: dict[str, Any] | None = None,
) -> None:
    """Resolve Mage passives that react to individual spell-damage hits."""
    if metadata is None and isinstance(target, dict):
        metadata = target
        target = None
    if not isinstance(metadata, dict):
        return
    ability_name = str(metadata.get("ability_name") or "")
    state = _combat_state(character)
    if ability_name == "Kinetic Explosion" and has_skill(
        character,
        "Arcane Empowerment",
    ):
        state["arcane_empowerment"] = min(
            5,
            int(state.get("arcane_empowerment", 0) or 0) + 1,
        )
    if (
        ability_name in {"Magic Missile", "Magic Missile II", "Magic Missile III"}
        and has_skill(character, "Fragmentation")
        and random.random() < 0.35
    ):
        state["arcane_crystal_shards"] = min(
            24,
            int(state.get("arcane_crystal_shards", 0) or 0) + 1,
        )
        state["new_arcane_crystal_shards"] = int(state.get("new_arcane_crystal_shards", 0) or 0) + 1
    if (
        str(metadata.get("damage_type") or "") == "Electric"
        and bool(metadata.get("is_critical"))
        and has_skill(character, "Electrical Burns")
        and target is not None
    ):
        _apply_burning(target, max(1, int(getattr(character.stats, "intel", 1) // 3)))


def incoming_damage_multiplier(character: Any) -> float:
    """Split damage with an active Mirror Image when Illusory Link is known."""
    duplicates = getattr(character, "magic_effects", {}).get("Duplicates")
    if (
        has_skill(character, "Illusory Link")
        and duplicates is not None
        and bool(getattr(duplicates, "active", False))
    ):
        return 0.50
    return 1.0


def arcane_critical_multiplier(
    character: Any,
    multiplier: float,
    ability: Any | None = None,
) -> float:
    """Increase only Magic Missile projectile critical bonus damage by 20%."""
    try:
        from ..progression import has_talent

        if (
            multiplier > 1
            and _is_magic_missile(ability)
            and has_talent(character, "mage.arcane-fundamentals")
        ):
            return 1 + ((multiplier - 1) * 1.20)
    except Exception:
        pass
    return multiplier


def _combat_state(character: Any) -> dict[str, Any]:
    state = getattr(character, "mage_enhancement_state", None)
    if not isinstance(state, dict):
        state = {}
        setattr(character, "mage_enhancement_state", state)
    return state


def start_combat(character: Any) -> None:
    """Clear transient Mage effects before a new combat begins."""
    _combat_state(character).clear()
    character.mage_refueling = False
    character.mage_refueling_streak = 0


def _random_school_rider_triggers(
    character: Any,
    school: str,
    passive_name: str,
    *,
    rng: Any,
) -> bool:
    """Resolve one registered random rider and its hidden Wizard streak."""
    base_chance = RANDOM_SCHOOL_RIDERS.get((school, passive_name))
    if base_chance is None or not has_skill(character, passive_name):
        return False
    from . import class_rings, promotion_kits

    streak_active = (
        getattr(getattr(character, "cls", None), "name", "") == "Wizard"
        and class_rings.is_awakened(character, "Wizard")
        and class_rings.has_equipped_class_ring(character)
    )
    if streak_active:
        if not promotion_kits._claim_action(
            character,
            f"wizard_school_rider:{school}",
        ):
            return False
        bonus = class_rings.wizard_rider_chance_bonus(character, school)
        triggered = bonus >= 1.0 or rng.random() < min(1.0, base_chance + bonus)
        class_rings.record_wizard_rider(character, school, triggered)
        return triggered
    return rng.random() < base_chance


def process_cast(
    character: Any,
    ability: Any,
    target: Any | None = None,
    *,
    rng: Any = random,
) -> str:
    """Attempt the learned matching Enhancement after a successful spell cast."""
    from . import promotion_kits

    message = promotion_kits.record_spell_signature(character, ability)
    try:
        from . import demonologist

        message += demonologist.process_spell_cast(character, ability, target, rng=rng)
    except Exception:
        pass
    school = school_from_ability(ability)
    message += _apply_sorcerer_modifier(character, ability, target, school, rng=rng)
    message += _apply_wizard_modifier(character, ability, target, school, rng=rng)
    message += _resolve_arcane_battlefield_effects(character, ability)
    passive = ENHANCEMENT_BY_SCHOOL.get(str(school))
    if passive is None or not has_skill(character, passive):
        return message
    chance = ENHANCEMENT_PROC_CHANCE
    if specialization(character) == "Arcane":
        chance *= 0.50
    if rng.random() >= chance:
        return message

    state = _combat_state(character)
    if school == "Fire":
        state["fire_inside"] = 3
        return message + f"{character.name}'s Fire Inside primes the next attack.\n"
    if school == "Ice":
        state["frozen_armor"] = 1
        character.stat_effects["Defense"].active = True
        character.stat_effects["Defense"].duration = max(
            character.stat_effects["Defense"].duration, 1
        )
        character.stat_effects["Defense"].extra = max(character.stat_effects["Defense"].extra, 10)
        return message + f"Frozen Armor protects {character.name} for one turn.\n"
    if school == "Electric":
        state["electrified"] = 3
        return message + f"{character.name} becomes Electrified for three turns.\n"
    if school == "Wind":
        state["wind_currents"] = 3
        character.stat_effects["Speed"].active = True
        character.stat_effects["Speed"].duration = max(character.stat_effects["Speed"].duration, 3)
        character.stat_effects["Speed"].extra = max(character.stat_effects["Speed"].extra, 3)
        return message + f"Wind Currents quicken {character.name} for three turns.\n"
    if school == "Water":
        hp = max(1, int(character.health.max * 0.05))
        mp = max(1, int(character.mana.max * 0.05))
        hp = min(hp, character.health.max - character.health.current)
        mp = min(mp, character.mana.max - character.mana.current)
        character.health.current += max(0, hp)
        character.mana.current += max(0, mp)
        return message + f"Refreshment restores {hp} HP and {mp} MP to {character.name}.\n"
    if school == "Earth":
        state["terra_firma"] = 3
        return message + f"Terra Firma empowers {character.name}'s melee attacks.\n"
    return message


def tick_combat_state(character: Any, *, end: bool = False) -> str:
    """Advance or clear temporary Mage enhancement state."""
    state = _combat_state(character)
    if end:
        duplicates = getattr(character, "magic_effects", {}).get("Duplicates")
        if (
            has_skill(character, "Multiplicity")
            and duplicates is not None
            and bool(getattr(duplicates, "active", False))
        ):
            count = max(0, int(getattr(duplicates, "duration", 0) or 0))
            healing = min(
                character.health.max - character.health.current,
                int(character.health.max * 0.05 * count),
            )
            character.health.current += max(0, healing)
        state.clear()
        character.mage_refueling = False
        character.mage_refueling_streak = 0
        return ""
    message = ""
    if bool(getattr(character, "mage_refueling", False)):
        maximum = max(0, int(getattr(character.mana, "max", 0) or 0))
        streak = max(0, int(getattr(character, "mage_refueling_streak", 0) or 0)) + 1
        character.mage_refueling_streak = streak
        restored = min(
            maximum - int(getattr(character.mana, "current", 0) or 0),
            max(1, int(maximum * 0.10 * (2 ** (streak - 1)))),
        )
        character.mana.current += max(0, restored)
        message += f"{character.name} refuels {max(0, restored)} MP.\n"
    for key in tuple(state):
        if key in {"arcane_empowerment", "school_mastery_buffs"}:
            continue
        state[key] = max(0, int(state[key] or 0) - 1)
        if state[key] <= 0:
            del state[key]
    return message


def save_roll_multiplier(character: Any) -> float:
    """Return the defensive-save multiplier for prone or Refueling characters."""
    prone = getattr(character, "physical_effects", {}).get("Prone")
    return (
        0.5
        if (
            bool(getattr(character, "mage_refueling", False))
            or bool(getattr(prone, "active", False))
        )
        else 1.0
    )


def _apply_sorcerer_modifier(
    character: Any,
    ability: Any,
    target: Any | None,
    school: str | None,
    *,
    rng: Any,
) -> str:
    """Apply a learned Sorcerer school rider after a damaging spell hit."""
    if target is None or school not in ELEMENTAL_SCHOOLS:
        return ""
    result = getattr(ability, "result", None)
    damage = max(0, int(getattr(result, "damage", 0) or 0))
    if damage <= 0:
        return ""
    if hasattr(target, "is_alive") and not target.is_alive():
        return ""
    if school == "Fire" and has_skill(character, "Combustion"):
        effect = target.magic_effects["DOT"]
        effect.active = True
        effect.duration = max(int(effect.duration or 0), 2)
        effect.extra = max(int(effect.extra or 0), max(1, damage // 4))
        effect.source = "Burn"
        return f"Combustion sets {target.name} ablaze.\n"
    if school == "Ice" and has_skill(character, "Snowpiercer"):
        extra = max(1, damage // 4)
        target.health.current -= extra
        return f"Snowpiercer deals {extra} additional cold damage to {target.name}.\n"
    if school == "Electric" and _random_school_rider_triggers(
        character,
        school,
        "Paralyzer",
        rng=rng,
    ):
        if target.apply_stun(
            1,
            source="Paralyzer",
            applier=character,
        ):
            return f"Paralyzer stuns {target.name}.\n"
        return ""
    if school == "Wind" and has_skill(character, "Ejection Gale"):
        if not _random_school_rider_triggers(
            character,
            school,
            "Ejection Gale",
            rng=rng,
        ):
            return ""
        target.health.current = 0
        target.windswept_ejected = True
        return f"Ejection Gale sweeps {target.name} out of combat.\n"
    if school == "Water" and has_skill(character, "Aspirate"):
        effect = target.magic_effects["DOT"]
        effect.active = True
        effect.duration = max(int(effect.duration or 0), 2)
        effect.extra = max(int(effect.extra or 0), max(1, damage // 5))
        effect.source = "Drowning"
        target.apply_stun(1, source="Aspirate", applier=character)
        return f"Aspirate leaves {target.name} drowning and unable to act.\n"
    if school == "Earth" and has_skill(character, "Unsteady Ground"):
        effect = target.physical_effects["Prone"]
        effect.active = True
        effect.duration = max(int(effect.duration or 0), 1)
        effect.source = "Unsteady Ground"
        return f"Unsteady Ground knocks {target.name} prone.\n"
    return ""


def _is_magic_missile(ability: Any) -> bool:
    return str(getattr(ability, "name", "")) in {
        "Magic Missile",
        "Magic Missile II",
        "Magic Missile III",
    }


def _apply_burning(target: Any, damage: int, *, source: str = "Burn") -> None:
    effect = target.magic_effects["DOT"]
    effect.active = True
    effect.duration = max(int(effect.duration or 0), 3)
    effect.extra = max(int(effect.extra or 0), max(1, int(damage)))
    effect.source = source


def _encounter_targets(character: Any) -> list[Any]:
    encounter = getattr(character, "_combat_encounter", None)
    return [
        member.enemy
        for member in getattr(encounter, "living_members", ())
        if getattr(member, "enemy", None) is not None
    ]


def _apply_wizard_modifier(
    character: Any,
    ability: Any,
    target: Any | None,
    school: str | None,
    *,
    rng: Any,
) -> str:
    """Apply visible Wizard riders and their intentionally undisclosed interactions."""
    if target is None or school not in ELEMENTAL_SCHOOLS:
        return ""
    result = getattr(ability, "result", None)
    damage = max(0, int(getattr(result, "damage", 0) or 0))
    if damage <= 0:
        return ""
    message = ""
    if school == "Fire" and has_skill(character, "Inferno"):
        _apply_burning(target, max(1, damage // 4), source="Inferno")
        state = _combat_state(character)
        state["burning_environment"] = True
        others = [enemy for enemy in _encounter_targets(character) if enemy is not target]
        if others:
            _apply_burning(others[0], max(1, damage // 6), source="Inferno")
        message += "Inferno spreads the flames across the battlefield.\n"
    elif school == "Ice" and _random_school_rider_triggers(
        character,
        school,
        "Subzero",
        rng=rng,
    ):
        target.mage_frozen = 2
        target.mage_brittle = True
        target.apply_stun(2, source="Subzero", applier=character)
        message += f"{target.name} is frozen solid.\n"
    elif school == "Electric" and has_skill(character, "Electrical Burns"):
        if getattr(target.magic_effects.get("DOT"), "source", "") == "Drowning" and has_skill(
            character, "Aspirate"
        ):
            target.health.current = 0
            message += f"The charge courses through {target.name}'s drowning body.\n"
    elif school == "Wind" and has_skill(character, "Divine Wind"):
        target.flying = not bool(getattr(target, "flying", False))
        prone = target.physical_effects["Prone"]
        prone.active = True
        prone.duration = max(int(prone.duration or 0), 2)
        prone.source = "Divine Wind"
        message += f"Fujin leaves {target.name} prone.\n"
    elif school == "Water" and has_skill(character, "Unrelenting Waves"):
        if _random_school_rider_triggers(
            character,
            school,
            "Unrelenting Waves",
            rng=rng,
        ):
            target.mage_unrelenting_waves = 2
            effect = target.magic_effects["DOT"]
            effect.active = True
            effect.duration = max(int(effect.duration or 0), 2)
            effect.extra = max(int(effect.extra or 0), max(1, damage // 5))
            effect.source = "Unrelenting Waves"
            message += f"Unrelenting Waves continue around {target.name}.\n"
    elif school == "Earth" and has_skill(character, "Aftershock"):
        reverberating_targets = _encounter_targets(character) or [target]
        for enemy in reverberating_targets:
            enemy.mage_aftershock = 2
            effect = enemy.magic_effects["DOT"]
            effect.active = True
            effect.duration = max(int(effect.duration or 0), 3)
            effect.extra = max(int(effect.extra or 0), max(1, damage // 5))
            effect.source = "Aftershock"
        message += "The ground continues to reverberate.\n"

    # These cross-school reactions are deliberately absent from descriptions.
    if (
        school == "Wind"
        and getattr(target, "windswept_ejected", False)
        and has_skill(
            character,
            "Inferno",
        )
    ):
        extra = max(1, damage)
        target.health.current -= extra
        message += f"A vortex of flame tears through {target.name} for {extra} damage.\n"
    if (
        school == "Earth"
        and getattr(target, "mage_frozen", 0)
        and has_skill(
            character,
            "Subzero",
        )
    ):
        target.health.current = 0
        message += f"{target.name} shatters.\n"
    if (
        school == "Ice"
        and getattr(target, "mage_unrelenting_waves", 0)
        and has_skill(character, "Snowpiercer")
    ):
        target.mage_frozen = 2
        target.mage_brittle = True
        target.apply_stun(2, source="Flash Frozen", applier=character)
        message += f"{target.name} flash-freezes and becomes brittle.\n"
    if (
        school == "Fire"
        and getattr(target, "mage_aftershock", 0)
        and has_skill(character, "Combustion")
    ):
        _apply_burning(target, max(1, damage // 2), source="Molten Ground")
        message += f"The ground beneath {target.name} turns to molten lava.\n"
    return message


def _resolve_arcane_battlefield_effects(character: Any, ability: Any) -> str:
    state = _combat_state(character)
    message = ""
    new_shards = int(state.pop("new_arcane_crystal_shards", 0) or 0)
    if new_shards:
        noun = "shard" if new_shards == 1 else "shards"
        message += f"{new_shards} Arcane crystal {noun} scatter across the battlefield.\n"
    if str(getattr(ability, "name", "")) == "Kinetic Explosion" and has_skill(
        character, "Detonation Cascade"
    ):
        shards = int(state.pop("arcane_crystal_shards", 0) or 0)
        targets = _encounter_targets(character)
        if targets:
            pull_damage = max(
                1,
                int(character.check_mod("magic", enemy=targets[0]) * 0.08),
            )
            for enemy in targets:
                enemy.health.current -= pull_damage * 3
            message += (
                "The collapsing blast drags every enemy through three waves "
                "of force at its center.\n"
            )
        if shards and targets:
            damage = max(1, int(character.check_mod("magic", enemy=targets[0]) * 0.15))
            for index in range(shards):
                target = targets[index % len(targets)]
                if target.is_alive():
                    target.health.current -= damage
                    if has_skill(character, "Arcane Empowerment"):
                        state["arcane_empowerment"] = min(
                            5,
                            int(state.get("arcane_empowerment", 0) or 0) + 1,
                        )
            message += (
                f"Detonation Cascade ignites {shards} crystal shards into "
                f"smaller Kinetic Explosions.\n"
            )
    return message


def resolve_mana_rupture(
    character: Any,
    target: Any,
    *,
    battle_engine: Any | None = None,
) -> str:
    """Consume Arcane resources attached to Mana Rupture's learned modifiers."""
    del battle_engine
    state = _combat_state(character)
    message = ""
    if has_skill(character, "Mana Leak"):
        stacks = min(5, max(0, int(state.pop("arcane_empowerment", 0) or 0)))
        if stacks:
            depleted = min(
                int(target.mana.current),
                max(1, int(target.mana.max * 0.10 * stacks)),
            )
            target.mana.current -= depleted
            message += f"Mana Leak drains {depleted} MP from {target.name}.\n"
    if has_skill(character, "Mana Splinters"):
        shards = max(0, int(state.pop("arcane_crystal_shards", 0) or 0))
        targets = _encounter_targets(character)
        if shards and targets:
            damage = max(1, int(character.stats.intel * 0.10))
            for enemy in targets:
                enemy.health.current -= damage * shards
            restored = min(
                character.mana.max - character.mana.current,
                damage * shards,
            )
            character.mana.current += max(0, restored)
            message += (
                f"Mana Splinters shatters {shards} shards for {damage * shards} "
                f"damage to every enemy and restores {max(0, restored)} MP.\n"
            )
    return message


def melee_accuracy_bonus(character: Any) -> float:
    return 0.10 if _combat_state(character).get("wind_currents", 0) else 0.0


def melee_damage_multiplier(character: Any) -> float:
    return 1.50 if _combat_state(character).get("terra_firma", 0) else 1.0


def fire_inside_critical_bonus(character: Any) -> float:
    return 0.25 if _combat_state(character).get("fire_inside", 0) else 0.0


def consume_fire_inside(character: Any) -> None:
    _combat_state(character).pop("fire_inside", None)


def ice_resistance_bonus(character: Any, damage_type: str | None) -> float:
    if damage_type == "Ice" and _combat_state(character).get("frozen_armor", 0):
        return 0.25
    return 0.0


def electrified_retaliation(attacker: Any, defender: Any, damage: int) -> str:
    """Return one INT-scaled jolt after a successful incoming melee hit."""
    if damage <= 0 or not _combat_state(defender).get("electrified", 0):
        return ""
    jolt = max(1, int(getattr(defender.stats, "intel", 1) * 0.50))
    attacker.health.current -= jolt
    return f"{defender.name}'s Electrified ward jolts {attacker.name} for {jolt} damage.\n"


def set_transient_companion(
    character: Any,
    *,
    name: str,
    kind: str,
    source: str,
    damage: int | None = None,
) -> dict[str, Any]:
    """Replace the single transient companion and start its step duration."""
    level = max(1, int(getattr(getattr(character, "level", None), "level", 1)))
    binding = has_talent(character, "mage.binding-circle")
    base_damage = damage if damage is not None else max(2, level + character.stats.intel // 2)
    duration = TRANSIENT_SUMMON_STEPS
    if kind == "undead" and has_talent(character, "mage.forbidden-studies"):
        duration = int(duration * 1.50)
    state = {
        "name": str(name),
        "kind": str(kind),
        "source": str(source),
        "steps_remaining": duration,
        "damage": max(1, int(base_damage * (1.10 if binding else 1.0))),
    }
    character.transient_companion = state
    return state


def local_enemy_for_calling(
    character: Any,
    category: str,
    *,
    rng: Any = random,
) -> Any | None:
    """Choose a standard enemy of the requested kind nearest the current floor."""
    from .. import enemies
    from ..enemies.catalog import RANDOM_ENEMY_SPECS

    preferred_types = CALLING_ENEMY_TYPE_PREFERENCES.get(str(category), ())
    if not preferred_types:
        return None
    current_floor = max(0, int(getattr(character, "location_z", 0) or 0))
    floor_numbers = sorted(int(floor) for floor in RANDOM_ENEMY_SPECS)
    for enemy_type in preferred_types:
        nearest_distance: int | None = None
        nearest_factories: list[Any] = []
        for floor in floor_numbers:
            distance = abs(floor - current_floor)
            if nearest_distance is not None and distance > nearest_distance:
                continue
            for _name, factory in enemies.random_enemy_candidates(str(floor)):
                candidate = factory()
                if str(getattr(candidate, "enemy_typ", "")) != enemy_type:
                    continue
                if nearest_distance is None or distance < nearest_distance:
                    nearest_distance = distance
                    nearest_factories = [factory]
                elif distance == nearest_distance:
                    nearest_factories.append(factory)
        if nearest_factories:
            return rng.choice(nearest_factories)()
    return None


def conjure_standard_companion(
    character: Any,
    category: str,
    *,
    source: str,
    rng: Any = random,
) -> dict[str, Any] | None:
    """Replace the transient companion with a location-aware ordinary enemy."""
    enemy = local_enemy_for_calling(character, category, rng=rng)
    if enemy is None:
        return None
    damage = max(
        2,
        int(getattr(getattr(enemy, "combat", None), "attack", 0) or 0)
        + int(getattr(getattr(enemy, "stats", None), "strength", 0) or 0) // 2,
    )
    state = set_transient_companion(
        character,
        name=str(getattr(enemy, "name", category)),
        kind=str(category).lower(),
        source=source,
        damage=damage,
    )
    state["enemy_type"] = str(getattr(enemy, "enemy_typ", category))
    return state


def activate_torchlight(character: Any) -> None:
    """Start or refresh Torchlight's encounter-suppression duration."""
    character.torchlight_steps = TORCHLIGHT_STEPS


def torchlight_encounter_multiplier(character: Any) -> float:
    """Return the active Torchlight multiplier for random encounters."""
    if int(getattr(character, "torchlight_steps", 0) or 0) > 0:
        return TORCHLIGHT_ENCOUNTER_MULTIPLIER
    return 1.0


def tick_exploration(character: Any, steps: int) -> None:
    """Advance Mage transient summons, Torchlight, and conjuration cooldowns."""
    step_count = max(0, int(steps or 0))
    companion = getattr(character, "transient_companion", None)
    if isinstance(companion, dict):
        companion["steps_remaining"] = max(
            0, int(companion.get("steps_remaining", 0) or 0) - step_count
        )
        if companion["steps_remaining"] <= 0:
            character.transient_companion = None
    cooldown = max(0, int(getattr(character, "conjure_potion_cooldown", 0) or 0))
    character.conjure_potion_cooldown = max(0, cooldown - step_count)
    elixir_cooldown = max(
        0,
        int(getattr(character, "conjure_elixir_cooldown", 0) or 0),
    )
    character.conjure_elixir_cooldown = max(0, elixir_cooldown - step_count)
    torchlight_steps = max(
        0,
        int(getattr(character, "torchlight_steps", 0) or 0),
    )
    character.torchlight_steps = max(0, torchlight_steps - step_count)


def transient_companion_action(character: Any, enemies: list[Any], *, rng: Any = random) -> str:
    """Resolve the companion's independent random follow-up action."""
    companion = getattr(character, "transient_companion", None)
    living = [enemy for enemy in enemies if getattr(enemy, "is_alive", lambda: False)()]
    if not isinstance(companion, dict) or not living:
        return ""
    target = rng.choice(living)
    spread = rng.uniform(0.80, 1.20)
    damage = max(1, int(int(companion.get("damage", 1) or 1) * spread))
    target.health.current -= damage
    return (
        f"{companion['name']} acts independently and strikes {target.name} "
        f"for {damage} damage.\n"
    )


def permanent_summon_multipliers(character: Any) -> tuple[float, float]:
    """Return health and damage multipliers from Mage/Thaumaturgist mechanics."""
    state = getattr(character, "progression", None)
    purchased = getattr(state, "purchased_node_ids", set()) or set()
    health = 1.10 if has_talent(character, "mage.binding-circle") else 1.0
    damage = 1.10 if has_talent(character, "mage.binding-circle") else 1.0
    conduit_ranks = sum(
        node_id.startswith("summoner.talent.summoner-conduit-mastery") for node_id in purchased
    )
    ward_ranks = sum(
        node_id.startswith("summoner.talent.summoner-true-name-ward") for node_id in purchased
    )
    return health * (1 + 0.05 * ward_ranks), damage * (1 + 0.05 * conduit_ranks)


def record_last_enemy(character: Any, enemy: Any, *, boss: bool = False) -> None:
    """Remember the most recently defeated non-boss enemy for Enliven Dead."""
    if boss:
        return
    character.last_defeated_enemy = {
        "name": str(getattr(enemy, "name", "Unknown Enemy")),
        "enemy_type": str(getattr(enemy, "enemy_typ", "Monster")),
        "level": max(1, int(getattr(getattr(enemy, "level", None), "level", 1))),
    }
