"""Deterministic one-roll weapon and spell contact resolution."""

from __future__ import annotations

import math
from dataclasses import dataclass, replace
from enum import Enum

from src.core.randomness import gameplay_random as random

from ..randomness import RandomSource


class ContactKind(str, Enum):
    WEAPON = "weapon"
    SPELL = "spell"


class ArmorGroup(str, Enum):
    NONE = "none"
    LIGHT = "light"
    MEDIUM = "medium"
    HEAVY = "heavy"


class FailureAttribution(str, Enum):
    MISS = "miss"
    DODGE = "dodge"


class ModifierClassification(str, Enum):
    FITTED_INPUT = "fitted_input"
    ACCURACY_MULTIPLIER = "accuracy_multiplier"
    ACCURACY_POINTS = "accuracy_points"
    DODGE_POINTS = "dodge_points"
    POST_CONTACT = "post_contact"
    NON_CONTACT = "non_contact"


@dataclass(frozen=True)
class ContactInputs:
    """Approved fitted axes and explicit modifiers for one contact attempt."""

    kind: ContactKind
    proficiency_difference: int = 0
    defender_speed: float = 14.0
    armor_group: ArmorGroup = ArmorGroup.NONE
    intelligence: float = 14.0
    wisdom: float = 14.0
    charisma_term: int = 0
    accuracy_multiplier: float = 1.0
    accuracy_points: float = 0.0
    dodge_points: float = 0.0
    always_hit: bool = False


@dataclass(frozen=True)
class ContactResult:
    """One contact probability, draw, and failure attribution."""

    hit: bool
    chance: float
    roll: float | None
    attribution: FailureAttribution | None = None
    always_hit: bool = False


CONTACT_MODIFIER_REGISTRY = {
    "weapon.proficiency_difference": ModifierClassification.FITTED_INPUT,
    "weapon.defender_speed": ModifierClassification.FITTED_INPUT,
    "weapon.armor_group": ModifierClassification.FITTED_INPUT,
    "third_eye_intelligence": ModifierClassification.FITTED_INPUT,
    "spell.intelligence": ModifierClassification.FITTED_INPUT,
    "spell.wisdom_charisma": ModifierClassification.FITTED_INPUT,
    "accuracy_ring": ModifierClassification.ACCURACY_MULTIPLIER,
    "blind": ModifierClassification.ACCURACY_MULTIPLIER,
    "flying": ModifierClassification.ACCURACY_MULTIPLIER,
    "disarm": ModifierClassification.ACCURACY_MULTIPLIER,
    "berserk": ModifierClassification.ACCURACY_MULTIPLIER,
    "blind_rage": ModifierClassification.ACCURACY_MULTIPLIER,
    "invisibility": ModifierClassification.ACCURACY_MULTIPLIER,
    "encumbrance": ModifierClassification.ACCURACY_MULTIPLIER,
    "weapon_focus": ModifierClassification.ACCURACY_POINTS,
    "promotion_difference": ModifierClassification.ACCURACY_POINTS,
    "healer_accuracy": ModifierClassification.ACCURACY_POINTS,
    "duelist_accuracy": ModifierClassification.ACCURACY_POINTS,
    "sword_and_board_accuracy": ModifierClassification.ACCURACY_POINTS,
    "commitment_accuracy": ModifierClassification.ACCURACY_POINTS,
    "melee_accuracy": ModifierClassification.ACCURACY_POINTS,
    "threaded_accuracy": ModifierClassification.ACCURACY_POINTS,
    "totem_surge_reliability": ModifierClassification.ACCURACY_POINTS,
    "ability_accuracy_modifier": ModifierClassification.ACCURACY_POINTS,
    "dodge_ring": ModifierClassification.DODGE_POINTS,
    "evasion_skill": ModifierClassification.DODGE_POINTS,
    "concealment": ModifierClassification.DODGE_POINTS,
    "magic_dodge": ModifierClassification.DODGE_POINTS,
    "spell_dodge_bonus": ModifierClassification.DODGE_POINTS,
    "quickstep": ModifierClassification.DODGE_POINTS,
    "live_and_learn": ModifierClassification.DODGE_POINTS,
    "case_prediction": ModifierClassification.DODGE_POINTS,
    "rope_a_dope": ModifierClassification.DODGE_POINTS,
    "seeker_templar": ModifierClassification.DODGE_POINTS,
    "arcane_trickster": ModifierClassification.DODGE_POINTS,
    "tricksters_gambit": ModifierClassification.DODGE_POINTS,
    "retribution": ModifierClassification.DODGE_POINTS,
    "counterattack_dodge": ModifierClassification.DODGE_POINTS,
    "hangover_dodge_multiplier": ModifierClassification.DODGE_POINTS,
    "encumbrance_dodge_multiplier": ModifierClassification.DODGE_POINTS,
    "parry": ModifierClassification.POST_CONTACT,
    "reflect": ModifierClassification.POST_CONTACT,
    "resistance": ModifierClassification.POST_CONTACT,
    "immunity": ModifierClassification.POST_CONTACT,
    "status_contest": ModifierClassification.POST_CONTACT,
    "critical": ModifierClassification.NON_CONTACT,
}


_WEAPON_COEFFICIENTS = (
    2.196017117580274,
    1.0826241866516044,
    -1.1779354313213697,
    -0.5635489834499144,
    0.35108418067201397,
    0.00627346460331834,
    -0.017602861712730133,
    0.02510273086731499,
    0.050559870108057306,
    -0.02483345821977801,
    -0.03151720006974427,
    -0.052912455191929844,
    0.08089948276048431,
    0.030750816112461176,
)
_SPELL_COEFFICIENTS = (
    2.083496322599882,
    0.08929383062312002,
    -0.07708612665683551,
    -0.06706465941156274,
    0.15574292349193025,
    0.05429918945446811,
    -0.058232975985693214,
    -0.13168434804004975,
    -0.035455780259402485,
    -0.02159167222110652,
)


def armor_group_for_subtype(subtype: object) -> ArmorGroup:
    """Map legacy armor subtype values to fitted avoidance groups."""
    value = str(subtype or "None")
    if value in {"Natural", "Cloth", "None"}:
        return ArmorGroup.NONE
    try:
        return ArmorGroup(value.lower())
    except ValueError:
        return ArmorGroup.NONE


def _sigmoid(value: float) -> float:
    return 1.0 / (1.0 + math.exp(-max(-60.0, min(60.0, value))))


def _weapon_features(inputs: ContactInputs) -> tuple[float, ...]:
    proficiency = max(-2, min(2, inputs.proficiency_difference)) / 2.0
    speed = (max(0.0, inputs.defender_speed) - 14.0) / 8.0
    flags = tuple(
        float(inputs.armor_group.value == group) for group in ("light", "medium", "heavy")
    )
    return (
        1.0,
        proficiency,
        speed,
        proficiency * speed,
        speed * speed,
        *flags,
        *(flag * speed for flag in flags),
        *(flag * speed * speed for flag in flags),
    )


def _spell_features(inputs: ContactInputs) -> tuple[float, ...]:
    intelligence = (max(0.0, inputs.intelligence) - 14.0) / 8.0
    wisdom = (max(0.0, inputs.wisdom) - 14.0) / 8.0
    charisma = max(-5, min(5, inputs.charisma_term)) / 5.0
    return (
        1.0,
        intelligence,
        wisdom,
        charisma,
        intelligence * wisdom,
        intelligence * charisma,
        wisdom * charisma,
        intelligence * intelligence,
        wisdom * wisdom,
        charisma * charisma,
    )


def fitted_baseline(inputs: ContactInputs) -> float:
    """Return the unmodified fitted chance for approved input axes."""
    features, coefficients = (
        (_weapon_features(inputs), _WEAPON_COEFFICIENTS)
        if inputs.kind is ContactKind.WEAPON
        else (_spell_features(inputs), _SPELL_COEFFICIENTS)
    )
    return _sigmoid(
        sum(coefficient * feature for coefficient, feature in zip(coefficients, features))
    )


def contact_chance(inputs: ContactInputs) -> float:
    """Apply multiplicative accuracy, additive points, then dodge points."""
    accurate = (fitted_baseline(inputs) * inputs.accuracy_multiplier) + inputs.accuracy_points
    return max(0.0, min(1.0, accurate * (1.0 - max(0.0, min(1.0, inputs.dodge_points)))))


def _no_evasion_inputs(inputs: ContactInputs) -> ContactInputs:
    if inputs.kind is ContactKind.WEAPON:
        return replace(inputs, defender_speed=0.0, armor_group=ArmorGroup.NONE, dodge_points=0.0)
    return replace(inputs, wisdom=0.0, charisma_term=-5, dodge_points=0.0)


def resolve_contact(inputs: ContactInputs, *, rng: RandomSource = random) -> ContactResult:
    """Resolve exactly one contact draw with deterministic miss/dodge attribution."""
    if inputs.always_hit:
        return ContactResult(hit=True, chance=1.0, roll=None, always_hit=True)
    chance = contact_chance(inputs)
    roll = rng.random()
    if roll < chance:
        return ContactResult(hit=True, chance=chance, roll=roll)
    attribution = (
        FailureAttribution.DODGE
        if roll < contact_chance(_no_evasion_inputs(inputs))
        else FailureAttribution.MISS
    )
    return ContactResult(hit=False, chance=chance, roll=roll, attribution=attribution)
