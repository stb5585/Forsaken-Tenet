"""Bestiary location and loot presentation helpers."""

from __future__ import annotations

from itertools import chain

from .base import Enemy
from .catalog import (
    BOSS_DROP_ENEMY_NAMES,
    FIXED_LOCATION_HINTS,
    FUNHOUSE_ENEMY_SPECS,
    RANDOM_ENEMY_SPECS,
)


def bestiary_location_hints(enemy_name: str) -> list[str]:
    """Return coarse location hints for a bestiary entry."""
    clean_name = str(enemy_name or "").strip()
    if not clean_name:
        return []

    locations: set[str] = set()
    for level, catalog in RANDOM_ENEMY_SPECS.items():
        label = "Early Dungeon" if str(level) == "0" else f"Dungeon Level {level}"
        if any(enemy_name == clean_name for enemy_name, _class_name in catalog):
            locations.add(label)

    if any(enemy_name == clean_name for enemy_name, _class_name in FUNHOUSE_ENEMY_SPECS):
        locations.add("Funhouse")

    locations.update(FIXED_LOCATION_HINTS.get(clean_name, ()))
    return sorted(locations)


def bestiary_uses_boss_drop_rules(enemy_name: str) -> bool:
    """Return whether the named enemy normally uses boss-room loot rules."""
    return str(enemy_name or "").strip() in BOSS_DROP_ENEMY_NAMES


def _item_from_drop_entry(drop_entry) -> object | None:
    try:
        return drop_entry()
    except TypeError:
        return drop_entry
    except Exception:
        return None


def _bestiary_rarity_label(rarity: float) -> str:
    try:
        value = float(rarity)
    except (TypeError, ValueError):
        return "Unknown"
    if value >= 0.75:
        return "Common"
    if value >= 0.4:
        return "Uncommon"
    if value >= 0.1:
        return "Rare"
    return "Very Rare"


def bestiary_drop_hints(enemy: Enemy | None, *, boss: bool = False) -> list[str]:
    """Return possible drop rows using broad rarity labels, not exact odds."""
    if enemy is None:
        return []
    rows: list[str] = []
    seen: set[str] = set()
    inventory = getattr(enemy, "inventory", {}) or {}
    for drop_entry in chain.from_iterable(inventory.values()):
        item = _item_from_drop_entry(drop_entry)
        if item is None:
            continue
        if str(getattr(item, "subtyp", "") or "") == "Quest":
            continue
        name = str(getattr(item, "name", "") or "").strip()
        if not name or name in seen:
            continue
        seen.add(name)
        if boss and str(getattr(item, "subtyp", "") or "") not in {"Special", "Quest", "Ability"}:
            label = "Guaranteed"
        else:
            label = _bestiary_rarity_label(getattr(item, "rarity", None))
        rows.append(f"{name} ({label})")
    return rows
