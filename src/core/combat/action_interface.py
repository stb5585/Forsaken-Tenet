"""UI-agnostic combat action, shortcut, and resource presentation helpers."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable

from ..abilities.presentation import ability_icon_key
from ..contracts import (
    ActionAvailability,
    ActionAvailabilityCode,
    ActionReference,
    ActionReferenceKind,
    CombatResourcePresentation,
    EnvironmentalEffectPresentation,
    TimelineEntry,
)

SHORTCUT_SLOT_COUNT = 6
SYSTEM_COMMANDS = (
    "Attack",
    "Defend",
    "Items",
    "All Actions",
    "Flee",
)


@dataclass(frozen=True)
class CombatActionPresentation:
    """A selectable combat action with its current engine-derived availability."""

    action_id: str
    display_name: str
    engine_action: str
    choice: str | None
    availability: ActionAvailability
    description: str = ""
    reference: ActionReference | None = None
    icon_key: str = "unknown"

    @property
    def enabled(self) -> bool:
        """Return whether this presentation entry may be committed."""
        return self.availability.available

    @property
    def display_label(self) -> str:
        """Return text-complete menu content without relying on color alone."""
        if self.enabled or not self.availability.reason:
            return self.display_name
        return f"{self.display_name} — {self.availability.reason}"


@dataclass(frozen=True)
class ShortcutSlotPresentation:
    """One persisted shortcut slot and its current resolved action, if any."""

    index: int
    reference: ActionReference | None
    action: CombatActionPresentation | None

    @property
    def display_label(self) -> str:
        """Return an accessible one-based shortcut label."""
        prefix = f"{self.index + 1}. "
        if self.action is not None:
            return prefix + self.action.display_label
        if self.reference is not None:
            return prefix + "Unavailable assignment"
        return prefix + "Empty"


@dataclass(frozen=True)
class CombatInterfaceSnapshot:
    """Read-only core state consumed by combat presentation layers."""

    shortcuts: tuple[ShortcutSlotPresentation, ...]
    all_actions: tuple[CombatActionPresentation, ...]
    resources: tuple[CombatResourcePresentation, ...]
    timeline: tuple[TimelineEntry, ...]
    environmental_effects: tuple[EnvironmentalEffectPresentation, ...] = ()


def _slug(value: object) -> str:
    """Return a stable display-only key without serializing legacy class names."""
    parts = "".join(character.lower() if character.isalnum() else " " for character in str(value))
    return "_".join(part for part in parts.split() if part)


def _active_abilities(player: Any) -> Iterable[tuple[str, str, Any]]:
    """Yield learned combat-active spellbook abilities in acquisition order."""
    spellbook = getattr(player, "spellbook", {}) or {}
    for book, engine_action in (("Spells", "Cast Spell"), ("Skills", "Use Skill")):
        for name, ability in (spellbook.get(book, {}) or {}).items():
            if getattr(ability, "passive", False) or getattr(ability, "exploration_cast", False):
                continue
            yield engine_action, str(name), ability


def action_reference_for_ability(ability: Any) -> ActionReference | None:
    """Return the persisted slug reference for a learned active ability."""
    from ..abilities.catalog import ensure_catalog_ability_identity

    ensure_catalog_ability_identity(ability)
    ability_id = getattr(ability, "ability_id", None)
    if not isinstance(ability_id, str) or not ability_id:
        return None
    return ActionReference(ActionReferenceKind.ABILITY, ability_id)


def _ability_availability(
    player: Any,
    ability: Any,
    *,
    engine: Any | None = None,
    engine_action: str = "",
    choice: str | None = None,
) -> ActionAvailability:
    """Return presentation availability without duplicating target legality in UI."""
    if getattr(ability, "passive", False):
        return ActionAvailability(
            ActionAvailabilityCode.CLASS_RESTRICTED, "Passive abilities are read-only."
        )
    resource_type = str(getattr(ability, "resource_type", "") or "")
    bypasses_magic_block = resource_type in {"Resolve", "Oath Conviction"}
    if getattr(player, "anti_magic_active", False) and not bypasses_magic_block:
        return ActionAvailability(
            ActionAvailabilityCode.BLOCKED_BY_STATUS,
            "Blocked by the anti-magic field.",
        )
    silence = (getattr(player, "status_effects", {}) or {}).get("Silence")
    cost = int(getattr(ability, "cost", 0) or 0)
    if getattr(silence, "active", False) and cost > 0 and not bypasses_magic_block:
        return ActionAvailability(ActionAvailabilityCode.BLOCKED_BY_STATUS, "Blocked by Silence.")
    mana = getattr(player, "mana", None)
    if mana is not None and cost > int(getattr(mana, "current", 0) or 0):
        return ActionAvailability(ActionAvailabilityCode.INSUFFICIENT_MP, "Not enough MP.")
    if getattr(ability, "weapon", False):
        is_disarmed = getattr(player, "is_disarmed", None)
        if callable(is_disarmed) and is_disarmed():
            return ActionAvailability(
                ActionAvailabilityCode.WRONG_EQUIPMENT, "Weapon is unavailable."
            )
    is_available = getattr(ability, "is_available", None)
    if callable(is_available):
        try:
            currently_available = bool(is_available(player, None))
        except TypeError:
            currently_available = bool(is_available(player))
        if not currently_available:
            if resource_type:
                return ActionAvailability(
                    ActionAvailabilityCode.INSUFFICIENT_CLASS_RESOURCE,
                    f"Requires {resource_type}.",
                )
            return ActionAvailability(
                ActionAvailabilityCode.CLASS_RESTRICTED, "Requirements not met."
            )
    target_scope = getattr(engine, "target_scope_for_action", None)
    encounter = getattr(engine, "encounter", None)
    if callable(target_scope) and encounter is not None:
        scope = target_scope(engine_action, choice)
        scope_name = str(getattr(scope, "value", scope))
        if scope_name == "single_opponent" and not getattr(encounter, "living_members", ()):
            return ActionAvailability(ActionAvailabilityCode.NO_LEGAL_TARGET, "No legal target.")
    return ActionAvailability()


def learned_action_presentations(
    player: Any,
    *,
    engine: Any | None = None,
) -> tuple[CombatActionPresentation, ...]:
    """List every learned active combat action, including unavailable entries."""
    entries: list[CombatActionPresentation] = []
    for engine_action, name, ability in _active_abilities(player):
        reference = action_reference_for_ability(ability)
        action_id = (
            reference.action_id if reference else f"runtime.{_slug(engine_action)}.{_slug(name)}"
        )
        category = "Spell" if engine_action == "Cast Spell" else "Skill"
        book = "Spells" if engine_action == "Cast Spell" else "Skills"
        cost = int(getattr(ability, "cost", 0) or 0)
        cost_text = f" ({cost} MP)" if cost else ""
        entries.append(
            CombatActionPresentation(
                action_id=action_id,
                display_name=f"{category}: {name}{cost_text}",
                engine_action=engine_action,
                choice=name,
                availability=_ability_availability(
                    player,
                    ability,
                    engine=engine,
                    engine_action=engine_action,
                    choice=name,
                ),
                description=str(getattr(ability, "description", "") or ""),
                reference=reference,
                icon_key=ability_icon_key(book, ability),
            )
        )
    return tuple(entries)


def normalize_shortcuts(player: Any) -> tuple[ActionReference | None, ...]:
    """Keep six persisted slots and auto-fill a new layout without overwriting edits."""
    raw = list(getattr(player, "action_bar_assignments", ()) or ())[:SHORTCUT_SLOT_COUNT]
    raw.extend([None] * (SHORTCUT_SLOT_COUNT - len(raw)))
    assignments: list[ActionReference | None] = [
        entry if isinstance(entry, ActionReference) else None for entry in raw
    ]
    if not bool(getattr(player, "action_bar_autofill_complete", False)):
        assigned = {entry for entry in assignments if entry is not None}
        candidates = [
            entry.reference
            for entry in learned_action_presentations(player)
            if entry.reference is not None and entry.reference not in assigned
        ]
        for index, assignment in enumerate(assignments):
            if assignment is None and candidates:
                assignments[index] = candidates.pop(0)
        player.action_bar_autofill_complete = True
    normalized = tuple(assignments)
    player.action_bar_assignments = normalized
    return normalized


def assign_shortcut(
    player: Any, slot_index: int, reference: ActionReference | None
) -> tuple[ActionReference | None, ...]:
    """Assign, clear, or rearrange one persisted shortcut without spending a turn."""
    if not 0 <= slot_index < SHORTCUT_SLOT_COUNT:
        raise IndexError("shortcut slot index must be between 0 and 5")
    assignments = list(normalize_shortcuts(player))
    assignments[slot_index] = reference
    player.action_bar_assignments = tuple(assignments)
    return player.action_bar_assignments


def shortcut_presentations(
    player: Any,
    *,
    engine: Any | None = None,
) -> tuple[ShortcutSlotPresentation, ...]:
    """Resolve six shortcut slots against the current learned-action catalog."""
    by_reference = {
        entry.reference: entry
        for entry in learned_action_presentations(player, engine=engine)
        if entry.reference is not None
    }

    def resolve(reference: ActionReference | None) -> CombatActionPresentation | None:
        if reference is None:
            return None
        if reference.kind is ActionReferenceKind.ABILITY:
            return by_reference.get(reference)
        inventory = getattr(player, "inventory", {}) or {}
        item_stack = inventory.get(reference.action_id, ())
        if not item_stack:
            return CombatActionPresentation(
                action_id=f"item.{_slug(reference.action_id)}",
                display_name=reference.action_id,
                engine_action="Use Item",
                choice=reference.action_id,
                availability=ActionAvailability(
                    ActionAvailabilityCode.MISSING_ITEM,
                    "Assigned item is unavailable.",
                ),
                reference=reference,
                icon_key="unknown",
            )
        return CombatActionPresentation(
            action_id=f"item.{_slug(reference.action_id)}",
            display_name=f"Item: {reference.action_id} ({len(item_stack)})",
            engine_action="Use Item",
            choice=reference.action_id,
            availability=ActionAvailability(),
            reference=reference,
            icon_key="unknown",
        )

    return tuple(
        ShortcutSlotPresentation(index, reference, resolve(reference))
        for index, reference in enumerate(normalize_shortcuts(player))
    )


def combat_resource_presentations(
    player: Any, target: Any | None = None
) -> tuple[CombatResourcePresentation, ...]:
    """Adapt class-kit resource providers into stable, text-complete HUD rows."""
    from ..classes import promotion_kits

    rows = promotion_kits.status_summary_rows(player, target)
    resources: list[CombatResourcePresentation] = []
    for priority, (label, state_text) in enumerate(rows):
        key = _slug(label)
        ready = any(token in state_text.lower() for token in ("ready", "full", "primed"))
        resources.append(
            CombatResourcePresentation(
                stable_key=f"class_resource.{key}",
                label=label,
                priority=priority,
                icon_key=f"resource.{key}",
                state_text=state_text,
                ready=ready,
            )
        )
    return tuple(resources)


def environmental_effect_presentations(player: Any) -> tuple[EnvironmentalEffectPresentation, ...]:
    """Return active world modifiers for every frontend without tile-type checks."""
    if not getattr(player, "anti_magic_active", False):
        return ()
    return (
        EnvironmentalEffectPresentation(
            stable_key="environment.anti_magic_field",
            label="Anti-Magic Field",
            detail="Spells and standard skills are suppressed.",
            icon_label="AM",
        ),
    )


def combat_interface_snapshot(engine: Any, player: Any) -> CombatInterfaceSnapshot:
    """Build the complete read-only combat interface state from engine-owned rules."""
    timeline_entries = getattr(engine, "timeline_entries", None)
    timeline = tuple(timeline_entries(6)) if callable(timeline_entries) else ()
    target = None
    focused_enemy = getattr(engine, "_focused_enemy", None)
    if callable(focused_enemy):
        target = focused_enemy()
    return CombatInterfaceSnapshot(
        shortcuts=shortcut_presentations(player, engine=engine),
        all_actions=learned_action_presentations(player, engine=engine),
        resources=combat_resource_presentations(player, target),
        timeline=timeline,
        environmental_effects=environmental_effect_presentations(player),
    )
