"""Off-hand crossbow firing, ammunition, and delayed-bolt mechanics."""

from __future__ import annotations

from typing import Any

from src.core.randomness import gameplay_random as random

from .. import items
from ..constants import ARMOR_SCALING_FACTOR

BOLT_ORDER = (
    "Wooden Bolts",
    "Metal Bolts",
    "Armor Piercing Bolts",
    "Magic Bolts",
    "Heat-Seeking Bolts",
    "Napalm Bolts",
    "Delayed Bolts",
)


def equipped_crossbow(character: Any) -> Any | None:
    """Return the equipped crossbow, if any."""
    offhand = getattr(character, "equipment", {}).get("OffHand")
    return offhand if getattr(offhand, "subtyp", None) == "Crossbow" else None


def _pack(character: Any, name: str) -> Any | None:
    stack = getattr(character, "inventory", {}).get(name, [])
    if not isinstance(stack, list):
        return None
    return next(
        (pack for pack in stack if int(getattr(pack, "charges", 0) or 0) > 0),
        None,
    )


def selected_bolts(character: Any) -> Any | None:
    """Resolve selected ammunition, falling back to the least costly available pack."""
    selected = str(getattr(character, "selected_crossbow_bolts", "") or "")
    pack = _pack(character, selected) if selected else None
    if pack is not None:
        return pack
    for name in BOLT_ORDER:
        pack = _pack(character, name)
        if pack is not None:
            character.selected_crossbow_bolts = name
            return pack
    return None


def _recover_bolt(character: Any, pack: Any, *, rng: Any) -> str:
    chance = float(getattr(pack, "recovery_chance", 0.0) or 0.0)
    try:
        from ..progression import has_talent

        if has_talent(character, "ranger.quick-reload"):
            chance += 0.20
    except (AttributeError, KeyError, TypeError):
        pass
    pack.charges = max(0, int(getattr(pack, "charges", 0) or 0) - 1)
    recovered = rng.random() < chance
    if recovered and pack.name == "Napalm Bolts":
        metal_pack = _pack(character, "Metal Bolts")
        if metal_pack is None:
            character.modify_inventory(items.MetalBolts(charges=1))
        else:
            metal_pack.charges += 1
    elif recovered:
        pack.charges += 1
    description = str(getattr(pack, "ammunition_description", "Crossbow ammunition."))
    pack.description = f"{description} Bolts remaining: {pack.charges}."
    if pack.charges <= 0:
        character.modify_inventory(pack, subtract=True)
        if getattr(character, "selected_crossbow_bolts", None) == pack.name:
            character.selected_crossbow_bolts = ""
    if not recovered:
        return ""
    if pack.name == "Napalm Bolts":
        return "The spent Napalm Bolt is recovered as a Metal Bolt.\n"
    return f"{character.name} recovers the {pack.name[:-1]}.\n"


def _heat_seeking_bonus(target: Any) -> float:
    enemy_type = str(getattr(target, "enemy_typ", "") or "")
    if enemy_type in {"Undead", "Slime"}:
        return 0.0
    if enemy_type == "Elemental":
        name = str(getattr(target, "name", "") or "").lower()
        resistances = getattr(target, "resistance", {})
        fire_resistance = float(resistances.get("Fire", 0) or 0)
        is_fire_elemental = "fire" in name or "flame" in name or fire_resistance >= 1.0
        if not is_fire_elemental:
            return 0.0
    return 0.20


def _physical_damage(attacker: Any, target: Any, raw: int, *, ignore_armor: bool) -> int:
    physical_resistance = float(target.check_mod("resist", enemy=attacker, typ="Physical"))
    armor = 0 if ignore_armor else max(0, int(target.check_mod("armor", enemy=attacker)))
    reduction = armor / (armor + ARMOR_SCALING_FACTOR)
    return max(1, int(raw * (1 - physical_resistance) * (1 - reduction)))


def _living_enemies(encounter: Any, primary: Any) -> list[Any]:
    if encounter is None:
        return [primary]
    enemies = [member.enemy for member in encounter.living_members]
    return enemies or [primary]


def fire_crossbow(
    attacker: Any,
    target: Any,
    *,
    encounter: Any = None,
    rng: Any | None = None,
    shot_limit: int | None = None,
    damage_multiplier: float = 1.0,
    napalm_splash: bool = True,
) -> tuple[str, bool, list[int]]:
    """Fire an equipped crossbow after a basic attack."""
    crossbow = equipped_crossbow(attacker)
    if crossbow is None or target is None or not target.is_alive():
        return "", False, []
    generator = rng or random
    messages: list[str] = []
    damages: list[int] = []
    any_hit = False
    shots = int(getattr(crossbow, "shots_per_attack", 1) or 1)
    if shot_limit is not None:
        shots = min(shots, max(0, int(shot_limit)))
    for _shot in range(shots):
        pack = selected_bolts(attacker)
        if pack is None:
            messages.append(f"{crossbow.name} has no crossbow bolts to fire.\n")
            break
        accuracy_bonus = 0.0
        try:
            from ..progression import has_talent

            if has_talent(attacker, "ranger.crossbow-training"):
                accuracy_bonus += 0.10
        except (AttributeError, KeyError, TypeError):
            pass
        if pack.name == "Heat-Seeking Bolts":
            accuracy_bonus += _heat_seeking_bonus(target)
        contact = attacker.resolve_contact(
            target,
            typ="weapon",
            accuracy_points=accuracy_bonus,
            rng=generator,
        )
        if not contact.hit:
            messages.append(f"{attacker.name} fires {crossbow.name} but misses {target.name}.\n")
            messages.append(_recover_bolt(attacker, pack, rng=generator))
            continue
        any_hit = True
        shot_damage_multiplier = damage_multiplier
        try:
            from . import pathfinder

            shot_damage_multiplier *= pathfinder.ranger_weapon_damage_multiplier(
                attacker,
                target,
            )
        except (AttributeError, KeyError, TypeError):
            pass
        raw = max(
            1,
            int(
                (crossbow.damage + attacker.combat.attack + attacker.stats.dex // 2)
                * shot_damage_multiplier
            ),
        )
        if pack.name == "Delayed Bolts":
            payload = getattr(target, "_delayed_crossbow_bolts", [])
            payload.append({"turns": 1, "damage": int(raw * 2.5), "source": attacker.name})
            target._delayed_crossbow_bolts = payload
            messages.append(f"A Delayed Bolt attaches to {target.name}.\n")
        else:
            damage = _physical_damage(
                attacker,
                target,
                raw,
                ignore_armor=pack.name == "Armor Piercing Bolts",
            )
            target.health.current -= damage
            damages.append(damage)
            messages.append(f"{crossbow.name} hits {target.name} for {damage} damage.\n")
            if pack.name == "Magic Bolts" and crossbow.name == "Magic Crossbow":
                _hit, reduction_message, arcane_damage = target.damage_reduction(
                    max(1, raw // 2), attacker, typ="Arcane"
                )
                target.health.current -= arcane_damage
                damages.append(arcane_damage)
                messages.append(f"Arcane energy deals {arcane_damage} additional damage.\n")
                if reduction_message:
                    messages.append(reduction_message)
            if pack.name == "Napalm Bolts":
                napalm_targets = _living_enemies(encounter, target) if napalm_splash else [target]
                for enemy in napalm_targets:
                    if not enemy.is_alive():
                        continue
                    _hit, _reduction_message, fire_damage = enemy.damage_reduction(
                        max(1, raw // 2), attacker, typ="Fire"
                    )
                    enemy.health.current -= fire_damage
                    if enemy is target:
                        damages.append(fire_damage)
                    messages.append(f"Napalm burns {enemy.name} for {fire_damage} Fire damage.\n")
        messages.append(_recover_bolt(attacker, pack, rng=generator))
        if not target.is_alive():
            break
    return "".join(messages), any_hit, damages


def tick_delayed_bolts(character: Any) -> str:
    """Advance and detonate crossbow bolts attached to a combatant."""
    payload = list(getattr(character, "_delayed_crossbow_bolts", []) or [])
    if not payload:
        return ""
    remaining = []
    messages = []
    for bolt in payload:
        bolt["turns"] = int(bolt.get("turns", 0) or 0) - 1
        if bolt["turns"] > 0:
            remaining.append(bolt)
            continue
        damage = max(1, int(bolt.get("damage", 1) or 1))
        character.health.current -= damage
        messages.append(f"A Delayed Bolt explodes for {damage} damage to {character.name}.\n")
    character._delayed_crossbow_bolts = remaining
    return "".join(messages)
