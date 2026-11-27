"""Regression coverage for split enemy modules and the public enemy façade."""

import inspect

from src.core import enemies
from src.core.enemies import base, early, endgame, midgame, registry

ENEMY_MODULES = (base, early, midgame, endgame)


def _module_enemy_classes(module):
    return {
        name: value
        for name, value in vars(module).items()
        if inspect.isclass(value)
        and issubclass(value, enemies.Enemy)
        and value.__module__ == module.__name__
    }


def test_enemies_facade_preserves_all_split_class_exports():
    direct_exports = {
        name: implementation
        for module in ENEMY_MODULES
        for name, implementation in _module_enemy_classes(module).items()
    }

    assert len(direct_exports) == 145
    for name, implementation in direct_exports.items():
        assert getattr(enemies, name) is implementation


def test_encounter_catalogs_reference_split_implementations():
    catalog_entries = [
        entry for floor_entries in enemies._RANDOM_ENEMY_CATALOG.values() for entry in floor_entries
    ]
    catalog_entries.extend(enemies._FUNHOUSE_ENEMY_CATALOG)

    assert catalog_entries
    for _display_name, enemy_class in catalog_entries:
        assert getattr(enemies, enemy_class.__name__) is enemy_class
        assert enemy_class.__module__.startswith("src.core.enemies.")


def test_registry_resolves_catalogs_without_the_package_facade():
    assert registry.ENEMY_NAMESPACE
    assert registry.RANDOM_ENEMY_CATALOG == enemies._RANDOM_ENEMY_CATALOG
    assert registry.FUNHOUSE_ENEMY_CATALOG == enemies._FUNHOUSE_ENEMY_CATALOG


def test_transform_targets_preserve_public_class_identity():
    transformations = (
        enemies.Barghest().transform,
        enemies.Quasit().transform,
        enemies.Vampire().transform,
        enemies.Wererat().transform,
    )

    for targets in transformations:
        assert targets
        for target_class in targets:
            assert getattr(enemies, target_class.__name__) is target_class
