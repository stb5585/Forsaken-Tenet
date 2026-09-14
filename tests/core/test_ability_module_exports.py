"""Regression coverage for split ability modules and the public façade."""

import inspect

from src.core import abilities
from src.core.combat.action_interface import action_reference_for_ability
from src.core.save_system.item_serialization import AbilitySerializer
from src.core.abilities import (
    bard,
    base,
    cleric,
    enemy,
    healer_promotions,
    inquisitor,
    mage,
    pathfinder,
    powerups,
    promotions,
    shaman,
    skills,
    spell_stealer,
    spell_types,
    spells,
    thief,
    utility,
)

ABILITY_MODULES = (
    base,
    bard,
    cleric,
    healer_promotions,
    inquisitor,
    skills,
    promotions,
    utility,
    powerups,
    mage,
    enemy,
    spell_types,
    spells,
    pathfinder,
    shaman,
    spell_stealer,
    thief,
)


def _module_ability_classes(module):
    return {
        name: value
        for name, value in vars(module).items()
        if inspect.isclass(value) and value.__module__ == module.__name__
    }


def _progression_abilities():
    for progression in (abilities.skill_dict, abilities.spell_dict):
        for levels in progression.values():
            for entry in levels.values():
                yield from abilities.ability_classes_for(entry)


def test_abilities_facade_preserves_all_split_class_exports():
    direct_exports = {
        name: implementation
        for module in ABILITY_MODULES
        for name, implementation in _module_ability_classes(module).items()
    }

    assert len(direct_exports) == 623
    for name, implementation in direct_exports.items():
        assert getattr(abilities, name) is implementation


def test_progression_catalogs_reference_split_implementations():
    progression_abilities = list(_progression_abilities())

    assert progression_abilities
    for ability_class in progression_abilities:
        assert getattr(abilities, ability_class.__name__) is ability_class
        assert ability_class.__module__.startswith("src.core.abilities.")


def test_legacy_alias_and_yaml_directory_remain_available():
    assert abilities.SongInspiration is abilities.MelodyInspiration
    assert abilities._YAML_DIR.is_dir()


def test_every_learnable_active_ability_has_a_stable_shortcut_and_save_identity():
    """Prevent catalog additions from silently becoming unassignable actions."""
    active_abilities = []
    for ability_class in _progression_abilities():
        ability = ability_class()
        if getattr(ability, "passive", False) or getattr(ability, "exploration_cast", False):
            continue
        active_abilities.append(ability)

    references = [action_reference_for_ability(ability) for ability in active_abilities]
    serialized = [AbilitySerializer.serialize(ability) for ability in active_abilities]

    assert all(reference is not None for reference in references)
    assert all(reference.action_id == saved for reference, saved in zip(references, serialized))
    assert all(AbilitySerializer.deserialize(ability_id) is not None for ability_id in serialized)
