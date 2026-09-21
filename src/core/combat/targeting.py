"""Targeting contracts shared by abilities and the battle engine."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from ..contracts.targeting import (
    TargetingPolicy,
)
from ..contracts.targeting import TargetLossPolicy as CanonicalTargetLossPolicy
from ..contracts.targeting import TargetScope as CanonicalTargetScope

_ACTION_IDS = {
    "Attack": "system.attack",
    "Defend": "system.defend",
    "Flee": "system.flee",
    "Nothing": "system.wait",
    "Cancel Charge": "system.cancel_charge",
    "Pickup Weapon": "system.pickup_weapon",
    "Cast Spell": "ability.cast",
    "Use Skill": "ability.use",
    "Use Item": "item.use",
    "Summon": "companion.summon",
    "Recall": "companion.recall",
    "Support": "companion.support",
    "Companion": "companion.command",
    "Repertoire": "class.repertoire",
    "Totem": "class.totem",
    "Transform": "class.transform",
    "Untransform": "class.untransform",
    "Dismiss Form": "class.dismiss_form",
    "Runic Boost": "class.runic_boost",
    "Tame": "class.tame",
    "Steal As Well": "class.steal_as_well",
}
_ENGINE_ACTIONS = {action_id: command for command, action_id in _ACTION_IDS.items()}


class TargetScope(str, Enum):
    """Canonical set of combat action target shapes."""

    NONE = "none"
    SELF = "self"
    SINGLE_ENEMY = "single_enemy"
    ALL_ENEMIES = "all_enemies"


class TargetLossPolicy(str, Enum):
    """How a committed action behaves when its original target is lost."""

    LOCKED = "locked"
    RETARGET_FOCUS = "retarget_focus"
    SNAPSHOT_ROSTER = "snapshot_roster"


class ActionValidationCode(str, Enum):
    """Machine-readable reason an action intent was rejected."""

    MISSING_TARGET = "missing_target"
    UNKNOWN_TARGET = "unknown_target"
    UNAVAILABLE_TARGET = "dead_or_resolved_target"
    WRONG_TARGET_COUNT = "wrong_target_count"
    WRONG_TARGET_SCOPE = "wrong_target_scope"
    ENEMY_AREA_UNSUPPORTED = "enemy_area_unsupported"
    CONCEALED_TARGET = "concealed_target"
    CHARGE_NOT_READY = "charge_not_ready"
    CHARGE_PENDING = "charge_pending"
    NO_CHARGE_TO_CANCEL = "no_charge_to_cancel"
    FORCED_ACTION_REQUIRED = "forced_action_required"


@dataclass(frozen=True)
class ActionIntent:
    """Immutable ID-based action request; the engine owns the actor."""

    action_id: str
    choice: str | None = None
    target_ids: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not self.action_id:
            raise ValueError("action_id must not be empty")
        object.__setattr__(self, "action_id", _ACTION_IDS.get(self.action_id, self.action_id))
        object.__setattr__(self, "target_ids", tuple(self.target_ids))

    @property
    def engine_action(self) -> str:
        """Return the internal dispatcher command for this canonical ID."""
        return _ENGINE_ACTIONS.get(self.action_id, self.action_id)


def canonical_targeting_policy(
    scope: TargetScope,
    loss_policy: TargetLossPolicy,
    *,
    hostile: bool = False,
) -> TargetingPolicy:
    """Adapt enemy-named runtime targeting values to canonical actor-relative values."""
    canonical_scope = {
        TargetScope.NONE: CanonicalTargetScope.NONE,
        TargetScope.SELF: CanonicalTargetScope.SELF,
        TargetScope.SINGLE_ENEMY: CanonicalTargetScope.SINGLE_OPPONENT,
        TargetScope.ALL_ENEMIES: CanonicalTargetScope.ALL_OPPONENTS,
    }[scope]
    canonical_loss_policy = CanonicalTargetLossPolicy(loss_policy.value)
    return TargetingPolicy(canonical_scope, canonical_loss_policy, hostile=hostile)


def legacy_target_scope(scope: CanonicalTargetScope) -> TargetScope:
    """Adapt a canonical actor-relative scope for unmigrated runtime callers."""
    return {
        CanonicalTargetScope.NONE: TargetScope.NONE,
        CanonicalTargetScope.SELF: TargetScope.SELF,
        CanonicalTargetScope.SINGLE_OPPONENT: TargetScope.SINGLE_ENEMY,
        CanonicalTargetScope.ALL_OPPONENTS: TargetScope.ALL_ENEMIES,
    }[scope]
