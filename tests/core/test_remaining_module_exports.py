"""Compatibility coverage for the remaining split core modules."""

import inspect

from src.core import character, map_tiles
from src.core.classes import promotion_kits
from src.core.data import data_driven_abilities

MAP_TILE_MODULES = (
    map_tiles.rules,
    map_tiles.paths,
    map_tiles.special,
    map_tiles.bosses,
    map_tiles.rooms,
    map_tiles.endgame,
)
DATA_DRIVEN_MODULES = (
    data_driven_abilities.base,
    data_driven_abilities.skills,
    data_driven_abilities.spells,
    data_driven_abilities.special,
    data_driven_abilities.missile,
    data_driven_abilities.jump,
    data_driven_abilities.movement,
)
CHARACTER_BEHAVIOR_MODULES = (
    character.events,
    character.status,
    character.offense,
    character.defense,
    character.utility,
)
PROMOTION_KIT_MODULES = (
    promotion_kits.state,
    promotion_kits.lifecycle,
    promotion_kits.meters,
    promotion_kits.events,
    promotion_kits.resolve,
    promotion_kits.tracks,
    promotion_kits.companions,
    promotion_kits.presentation,
)


def _owned_classes(module):
    return {
        name: value
        for name, value in vars(module).items()
        if inspect.isclass(value) and value.__module__ == module.__name__
    }


def _owned_functions(module):
    return {
        name: value
        for name, value in vars(module).items()
        if inspect.isfunction(value) and value.__module__ == module.__name__
    }


def test_map_tile_facade_preserves_all_split_classes():
    exports = {
        name: implementation
        for module in MAP_TILE_MODULES
        for name, implementation in _owned_classes(module).items()
    }

    assert len(exports) == 85
    for name, implementation in exports.items():
        assert getattr(map_tiles, name) is implementation


def test_data_driven_facade_preserves_all_split_classes():
    exports = {
        name: implementation
        for module in DATA_DRIVEN_MODULES
        for name, implementation in _owned_classes(module).items()
    }

    assert len(exports) == 12
    for name, implementation in exports.items():
        assert getattr(data_driven_abilities, name) is implementation


def test_character_composes_every_split_behavior_method():
    methods = {
        name: implementation
        for module in CHARACTER_BEHAVIOR_MODULES
        for mixin in _owned_classes(module).values()
        for name, implementation in vars(mixin).items()
        if inspect.isfunction(implementation)
    }

    # _emit_parry_event is part of the split offense contract as well.
    assert len(methods) == 57
    for name, implementation in methods.items():
        assert getattr(character.Character, name) is implementation


def test_promotion_kit_facade_preserves_all_split_functions():
    exports = {
        name: implementation
        for module in PROMOTION_KIT_MODULES
        for name, implementation in _owned_functions(module).items()
    }

    assert len(exports) == 237
    for name, implementation in exports.items():
        assert getattr(promotion_kits, name) is implementation
