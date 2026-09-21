"""Regression coverage for the effect owner modules and package exports."""

from src.core import effects
from src.core.effects import common, enemy, skills, special, summon

EFFECT_MODULES = (common, enemy, skills, special, summon)


def test_package_exports_resolve_to_the_split_implementations():
    for module in EFFECT_MODULES:
        for name, implementation in vars(module).items():
            if name.endswith("Effect") and name != "Effect":
                assert getattr(effects, name) is implementation
