"""Persistent curse and fracture mechanics shared by combat and exploration."""

from __future__ import annotations

from typing import Any

from src.core.randomness import gameplay_random as random

CURSE_NAMES = (
    "Umbra",
    "Frailty",
    "Swarms",
    "Hemorrhaging",
    "Elijah",
    "Dysarthria",
    "Demon Eyes",
    "Polydipsia",
)
FRACTURE_EXCLUDED = ("slime", "elemental", "construct", "apparition", "spirit")


def ensure_curses(character: Any) -> dict[str, dict[str, Any]]:
    """Return a normalized persistent curse mapping for a character."""
    raw = getattr(character, "persistent_curses", None)
    afflictions = raw if isinstance(raw, dict) else {}
    for name in CURSE_NAMES:
        value = afflictions.get(name)
        if value is True:
            afflictions[name] = {"active": True, "turns": 0}
        elif not isinstance(value, dict):
            afflictions[name] = {"active": False, "turns": 0}
        else:
            value["active"] = bool(value.get("active", False))
            value["turns"] = max(0, int(value.get("turns", 0) or 0))
    character.persistent_curses = afflictions
    return afflictions


def has_curse(character: Any, name: str) -> bool:
    """Return whether ``name`` is an active persistent curse."""
    return bool(ensure_curses(character).get(name, {}).get("active", False))


def apply_curse(
    character: Any,
    name: str,
    *,
    source: str = "Unknown",
    caster: Any | None = None,
) -> str:
    """Apply a curse that remains until cured or the victim dies."""
    if name not in CURSE_NAMES:
        raise ValueError(f"Unknown curse: {name}")
    entry = ensure_curses(character)[name]
    entry.update({"active": True, "turns": 0, "source": source})
    if caster is not None:
        casters = getattr(character, "_persistent_curse_casters", None)
        if not isinstance(casters, dict):
            casters = {}
            character._persistent_curse_casters = casters
        casters[name] = caster
    return f"{character.name} is afflicted by Curse of {name}.\n"


def cure_curses(character: Any) -> str:
    """Remove every persistent curse and return a display message."""
    removed = [name for name in CURSE_NAMES if has_curse(character, name)]
    for name in removed:
        ensure_curses(character)[name] = {"active": False, "turns": 0}
    casters = getattr(character, "_persistent_curse_casters", None)
    if isinstance(casters, dict):
        for name in removed:
            casters.pop(name, None)
    if not removed:
        return f"{character.name} has no curses to expel.\n"
    return f"The curses afflicting {character.name} are expelled.\n"


def strength_multiplier(character: Any) -> float:
    """Return the Curse of Frailty multiplier for strength-based rules."""
    if not has_curse(character, "Frailty"):
        return 1.0
    return 0.50 if curse_is_empowered(character, "Frailty") else 0.65


def spell_delay(character: Any) -> int:
    """Return extra casting turns imposed by Curse of Dysarthria."""
    if not has_curse(character, "Dysarthria"):
        return 0
    return 2 if curse_is_empowered(character, "Dysarthria") else 1


def shadow_resistance_penalty(character: Any) -> float:
    """Return the resistance penalty caused by Curse of Umbra."""
    if not has_curse(character, "Umbra"):
        return 0.0
    return -0.50 if curse_is_empowered(character, "Umbra") else -0.35


def fire_resistance_penalty(character: Any) -> float:
    """Return the Fire penalty added to Umbra by Flammable Affliction."""
    if not has_curse(character, "Umbra"):
        return 0.0
    caster = curse_caster(character, "Umbra")
    if "Flammable Affliction" not in getattr(caster, "spellbook", {}).get("Skills", {}):
        return 0.0
    return -0.50 if curse_is_empowered(character, "Umbra") else -0.35


def curse_caster(character: Any, name: str) -> Any | None:
    """Return the transient caster associated with a persistent curse."""
    casters = getattr(character, "_persistent_curse_casters", {})
    return casters.get(name) if isinstance(casters, dict) else None


def curse_is_empowered(character: Any, name: str) -> bool:
    """Return whether Monkey's Paw empowers the named curse."""
    caster = curse_caster(character, name)
    return "Monkey's Paw" in getattr(caster, "spellbook", {}).get("Skills", {})


def hemorrhaging_tick(character: Any) -> str:
    """Deal periodic bleeding damage from Hemorrhaging Curse."""
    if not has_curse(character, "Hemorrhaging") or not character.is_alive():
        return ""
    fraction = 0.06 if curse_is_empowered(character, "Hemorrhaging") else 0.04
    damage = min(character.health.current, max(1, int(character.health.max * fraction)))
    character.health.current = max(0, character.health.current - damage)
    return f"{character.name}'s open wounds bleed for {damage} damage.\n"


def can_fracture(character: Any) -> bool:
    """Return whether a creature has a skeleton or breakable exoskeleton."""
    identity = " ".join(
        str(value or "")
        for value in (
            getattr(character, "name", ""),
            getattr(character, "enemy_typ", ""),
            character.__class__.__name__,
        )
    ).lower()
    return not any(term in identity for term in FRACTURE_EXCLUDED)


def apply_fracture(character: Any, *, rng: Any = random) -> str:
    """Fracture a random bone, with repeated skull fractures being fatal."""
    if not can_fracture(character):
        return f"{character.name} has no anatomy that can be fractured.\n"
    identity = f"{getattr(character, 'enemy_typ', '')} {character.__class__.__name__}".lower()
    insect = any(term in identity for term in ("insect", "arachnid", "scarab", "spider"))
    bones = ["Arm", "Leg", "Exoskeleton" if insect else "Ribs", "Skull"]
    bone = rng.choice(bones)
    state = getattr(character, "fractures", None)
    if not isinstance(state, dict):
        state = {}
        character.fractures = state
    state[bone] = int(state.get(bone, 0) or 0) + 1
    effect = character.status_effects.get("Fractured")
    if effect is not None:
        effect.active = True
        effect.duration = -1
        effect.extra = bone
    if bone == "Skull" and state[bone] > 1:
        character.health.current = 0
        return f"{character.name}'s skull fractures again, killing them.\n"
    return f"{character.name} suffers a fractured {bone.lower()}.\n"


def polydipsia_tick(character: Any, *, rng: Any = random) -> str:
    """Advance Curse of Polydipsia by one combat or exploration turn."""
    entry = ensure_curses(character)["Polydipsia"]
    if not entry["active"] or not getattr(character, "is_alive", lambda: True)():
        return ""
    if int(entry.pop("held_turns", 0) or 0) > 0:
        return f"A sip of water holds {character.name}'s thirst at bay.\n"
    entry["turns"] += 1
    turn = entry["turns"]
    if turn >= 41:
        character.health.current = 0
        return f"{character.name} dies as unquenchable thirst consumes them.\n"
    if turn >= 31:
        if rng.random() < min(0.75, 0.15 + ((turn - 31) * 0.06)):
            character.health.current = 0
            return f"{character.name}'s organs fail from the curse.\n"
        character.status_effects["Stun"].active = True
        character.status_effects["Stun"].duration = 1
        return f"{character.name} is incapacitated by failing organs.\n"
    if turn >= 21:
        damage = max(1, int(character.health.max * 0.10))
        character.health.current = max(0, character.health.current - damage)
        return f"{character.name} harms themself in a thirsty delirium for {damage} damage.\n"
    if turn >= 11:
        character.status_effects["Berserk"].active = True
        character.status_effects["Berserk"].duration = max(
            1, character.status_effects["Berserk"].duration
        )
        return f"{character.name} loses control to a thirsty rage.\n"
    if rng.random() < 0.25:
        character.status_effects["Fear"].active = True
        character.status_effects["Fear"].duration = 1
        return f"Whispering voices fill {character.name} with fear.\n"
    return f"{character.name}'s unnatural thirst worsens.\n"


def swarms_tick(character: Any, *, rng: Any = random) -> str:
    """Deal repeated mosquito damage and occasionally spread nearby afflictions."""
    if not has_curse(character, "Swarms") or not character.is_alive():
        return ""
    caster = getattr(character, "_curse_swarms_caster", None)
    hits = rng.randint(4, 8)
    per_hit = max(1, int(getattr(getattr(caster, "stats", None), "intel", 10) / 20))
    spread_chance = 0.30 if curse_is_empowered(character, "Swarms") else 0.20
    if curse_is_empowered(character, "Swarms"):
        per_hit = max(1, int(per_hit * 1.50))
    damage = min(character.health.current, hits * per_hit)
    character.health.current = max(0, character.health.current - damage)
    message = f"Mosquitoes bite {character.name} {hits} times for {damage} damage.\n"

    encounter = getattr(caster, "_combat_encounter", None)
    source_member = next(
        (member for member in getattr(encounter, "members", ()) if member.enemy is character),
        None,
    )
    if source_member is None:
        return message
    adjacent = [
        member.enemy
        for member in getattr(encounter, "living_members", ())
        if abs(int(member.slot) - int(source_member.slot)) == 1
    ]
    if not adjacent:
        return message
    nearby = rng.choice(adjacent)

    dot = getattr(character, "magic_effects", {}).get("DOT")
    nearby_dot = getattr(nearby, "magic_effects", {}).get("DOT")
    if (
        rng.random() < spread_chance
        and dot is not None
        and dot.active
        and str(getattr(dot, "source", "")).lower().startswith("corruption")
        and nearby_dot is not None
        and not nearby_dot.active
    ):
        nearby_dot.active = True
        nearby_dot.duration = max(1, int(dot.duration or 1))
        nearby_dot.extra = max(1, int(dot.extra or 1))
        nearby_dot.source = "Corruption"
        payload = getattr(character, "_corruption_payload", None)
        if isinstance(payload, dict):
            nearby._corruption_payload = dict(payload)
        message += f"The swarm spreads Corruption to {nearby.name}.\n"

    negative_statuses = ("Poison", "Blind", "Silence", "Sleep", "Fear", "Stun", "Doom")
    active_statuses = [
        name
        for name in negative_statuses
        if getattr(getattr(character, "status_effects", {}).get(name), "active", False)
    ]
    if active_statuses and rng.random() < spread_chance:
        name = rng.choice(active_statuses)
        source = character.status_effects[name]
        target = nearby.status_effects.get(name)
        if target is not None:
            target.active = True
            target.duration = max(1, int(source.duration or 1))
            target.extra = source.extra
            message += f"The swarm spreads {name} to {nearby.name}.\n"

    spreadable = [
        name
        for name in CURSE_NAMES
        if name != "Swarms" and has_curse(character, name) and not has_curse(nearby, name)
    ]
    if spreadable and rng.random() < spread_chance:
        name = rng.choice(spreadable)
        apply_curse(
            nearby,
            name,
            source="Curse of Swarms",
            caster=curse_caster(character, name),
        )
        message += f"The swarm spreads Curse of {name} to {nearby.name}.\n"
    return message


def drink(character: Any) -> str:
    """Heal five percent and postpone Polydipsia for one turn."""
    healed = max(1, int(character.health.max * 0.05))
    before = character.health.current
    character.health.current = min(character.health.max, before + healed)
    entry = ensure_curses(character)["Polydipsia"]
    if entry["active"]:
        entry["held_turns"] = 1
    return (
        f"{character.name} drinks deeply and recovers {character.health.current - before} health.\n"
    )
