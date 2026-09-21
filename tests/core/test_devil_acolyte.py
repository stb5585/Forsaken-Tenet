#!/usr/bin/env python3
"""Tests for the Devil's Cambion Acolyte companion support logic."""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parents[2]))


def _make_player():
    from tests.test_framework import TestGameState

    return TestGameState.create_player(
        name="Hero",
        class_name="Warrior",
        race_name="Human",
        level=50,
        health=(999, 999),
        mana=(999, 999),
    )


def test_devil_familiar_turn_invokes_acolyte_support():
    from src.core.enemies import Devil

    devil = Devil()
    player = _make_player()

    # Ensure Shell is not already active.
    devil.stat_effects["Magic Defense"].active = False
    devil.stat_effects["Magic Defense"].duration = 0

    msg = devil.familiar_turn(player)
    assert msg
    assert "Cambion Acolyte" in msg
    assert devil.stat_effects["Magic Defense"].active is True


def test_acolyte_prefers_regen_when_shell_already_active_and_boss_low():
    from src.core.enemies import Devil

    devil = Devil()
    player = _make_player()

    # Pretend Shell already active.
    devil.stat_effects["Magic Defense"].active = True
    devil.stat_effects["Magic Defense"].duration = 5

    # Low HP to trigger Regen.
    devil.health.current = int(devil.health.max * 0.5)
    devil.magic_effects["Regen"].active = False
    devil.magic_effects["Regen"].duration = 0

    msg = devil.familiar_turn(player)
    assert msg
    assert "casts Regen" in msg
    assert devil.magic_effects["Regen"].active is True


def test_acolyte_no_crash_when_no_mana():
    from src.core.enemies import Devil

    devil = Devil()
    player = _make_player()

    devil.acolyte.mana.current = 0

    msg = devil.familiar_turn(player)
    assert msg == ""


def test_devil_can_cast_regen_with_magic_bonus_active():
    """The final boss's heal modifier must not reference an uninitialized value."""
    from src.core.enemies import Devil

    devil = Devil()
    devil.health.current = int(devil.health.max * 0.5)
    devil.stat_effects["Magic"].active = True
    devil.stat_effects["Magic"].extra = 12

    result = devil.spellbook["Spells"]["Regen"].cast(devil)

    assert result is not None
    assert devil.magic_effects["Regen"].active is True


def test_devil_unknown_resistance_defaults_to_neutral():
    """Unexpected damage labels must remain neutral instead of crashing combat."""
    from src.core.enemies import Devil

    assert Devil().check_mod("resist", typ="Non-elemental") == 0


@pytest.mark.parametrize("physical_resistance", [-0.4, 0.0, 0.75])
def test_ultimate_physical_damage_ignores_enemy_resistance(physical_resistance):
    """Ultimate Physical hits do not create resistance or vulnerability."""
    from src.core.enemies import Devil

    devil = Devil()
    devil.resistance["Physical"] = physical_resistance

    assert devil.check_mod("resist", typ="Physical") == pytest.approx(physical_resistance)
    assert devil.check_mod("resist", typ="Physical", ultimate=True) == 0.0
