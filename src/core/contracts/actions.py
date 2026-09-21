"""Stable action identity, assignment, and availability contracts."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Mapping

from .abilities import AbilityActivation
from .targeting import TargetingPolicy


class ActionReferenceKind(str, Enum):
    """Persisted namespaces for assignable actions."""

    ABILITY = "ability"
    ITEM = "item"


@dataclass(frozen=True)
class ActionReference:
    """Stable persisted reference to an ability slug or item token."""

    kind: ActionReferenceKind
    action_id: str

    def __post_init__(self) -> None:
        if not self.action_id or self.action_id.strip() != self.action_id:
            raise ValueError("action_id must be a non-empty normalized identifier")

    def to_dict(self) -> dict[str, str]:
        """Return the canonical save representation."""
        return {"kind": self.kind.value, "action_id": self.action_id}

    @classmethod
    def from_dict(cls, payload: Mapping[str, object]) -> ActionReference:
        """Parse the canonical save representation."""
        raw_kind = payload.get("kind")
        raw_action_id = payload.get("action_id")
        if not isinstance(raw_kind, str) or not isinstance(raw_action_id, str):
            raise ValueError("action reference kind and action_id must be strings")
        return cls(
            kind=ActionReferenceKind(raw_kind),
            action_id=raw_action_id,
        )


class ActionAvailabilityCode(str, Enum):
    """Machine-readable reason an action cannot currently be committed."""

    AVAILABLE = "available"
    INSUFFICIENT_MP = "insufficient_mp"
    BLOCKED_BY_STATUS = "blocked_by_status"
    WRONG_EQUIPMENT = "wrong_equipment"
    NO_LEGAL_TARGET = "no_legal_target"
    MISSING_ITEM = "missing_item"
    INSUFFICIENT_ITEM_COUNT = "insufficient_item_count"
    INSUFFICIENT_CLASS_RESOURCE = "insufficient_class_resource"
    CLASS_RESTRICTED = "class_restricted"


@dataclass(frozen=True)
class ActionAvailability:
    """Current availability and an optional player-facing explanation."""

    code: ActionAvailabilityCode = ActionAvailabilityCode.AVAILABLE
    reason: str = ""

    @property
    def available(self) -> bool:
        """Return whether the action may currently be committed."""
        return self.code is ActionAvailabilityCode.AVAILABLE


@dataclass(frozen=True)
class ActionDefinition:
    """Stable executable action metadata independent of frontend layout."""

    action_id: str
    display_name: str
    activation: AbilityActivation
    targeting: TargetingPolicy
    system_command: bool = False

    def __post_init__(self) -> None:
        if not self.action_id or self.action_id.strip() != self.action_id:
            raise ValueError("action_id must be a non-empty normalized identifier")
        if not self.display_name:
            raise ValueError("display_name must not be empty")
