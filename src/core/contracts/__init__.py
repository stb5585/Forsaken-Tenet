"""Typed foundational gameplay contracts without runtime dependencies."""

from .abilities import (
    AbilityActivation,
    AbilityDefinition,
    AbilityForm,
    AbilityMethod,
    AbilityOrigin,
    AbilityTaxonomy,
    PrimaryIntent,
)
from .actions import (
    ActionAvailability,
    ActionAvailabilityCode,
    ActionDefinition,
    ActionReference,
    ActionReferenceKind,
)
from .combatants import Combatant, CombatStats
from .presentation import (
    CombatResourcePresentation,
    EnvironmentalEffectPresentation,
    TimelineEntry,
    VisibilityState,
)
from .targeting import TargetingPolicy, TargetLossPolicy, TargetScope

__all__ = [
    "AbilityActivation",
    "AbilityDefinition",
    "AbilityForm",
    "AbilityMethod",
    "AbilityOrigin",
    "AbilityTaxonomy",
    "ActionAvailability",
    "ActionAvailabilityCode",
    "ActionDefinition",
    "ActionReference",
    "ActionReferenceKind",
    "CombatResourcePresentation",
    "Combatant",
    "CombatStats",
    "EnvironmentalEffectPresentation",
    "PrimaryIntent",
    "TargetingPolicy",
    "TargetLossPolicy",
    "TargetScope",
    "TimelineEntry",
    "VisibilityState",
]
