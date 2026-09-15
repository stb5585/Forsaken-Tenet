"""Characterization coverage for the first relic boss's level-15 tuning."""

from src.core.enemies import Barghest


def test_barghest_uses_level_fifteen_baseline_stats():
    """Keep Barghest's speed and damage inputs within its intended encounter band."""
    barghest = Barghest()

    assert barghest.stats.dex == 12
    assert barghest.stats.strength == 22
    assert barghest.combat.attack == 34
    assert barghest.combat.defense == 30
    assert barghest.health.max == 153
    assert {form.__name__ for form in barghest.transform} == {"Barghest", "Goblin2", "Direwolf2"}
