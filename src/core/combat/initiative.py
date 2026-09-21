"""
Shared combat utility functions used by Pygame and headless combat tools.

Centralises initiative determination and other combat-flow helpers so
that changes only need to be made once.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from src.core.randomness import gameplay_random as random

if TYPE_CHECKING:
    from src.core.character import Character


def determine_initiative(
    player: Character,
    enemy: Character,
) -> tuple[Character, Character]:
    """
    Determine who acts first in combat.

    Rules (in priority order):
      1. Encumbered player always loses initiative.
      2. Invisible player (enemy can't see) → player first.
         - Shadowcaster power-up activates on surprise.
      3. Invisible enemy (player can't see) → enemy first.
      4. Otherwise weighted random based on speed + luck.

    Returns:
        (first, second) - ordered pair of combatants.
    """
    # Dwarf Gluttony (out-of-combat hangover): can cause auto-loss of initiative
    # for a number of steps after using combat consumables.
    if getattr(player, "dwarf_hangover_steps", 0) > 0:
        first = enemy
    elif getattr(player, "encumbered", False):
        first = enemy
    elif player.invisible and not enemy.sight:
        # Shadowcaster surprise activation
        if player.cls.name == "Shadowcaster" and getattr(player, "power_up", False):
            player.class_effects["Power Up"].active = True
            player.class_effects["Power Up"].duration = 1
        first = player
    elif enemy.invisible and not player.sight:
        first = enemy
    else:
        p_chance = player.check_mod("speed", enemy=enemy) + player.check_mod(
            "luck", enemy=enemy, luck_factor=10
        )
        e_chance = enemy.check_mod("speed", enemy=player) + enemy.check_mod(
            "luck", enemy=player, luck_factor=10
        )
        total = p_chance + e_chance
        if total > 0:
            first = random.choices(
                [player, enemy],
                [p_chance / total, e_chance / total],
            )[0]
        else:
            # Fallback to raw dexterity comparison
            first = player if player.stats.dex >= enemy.stats.dex else enemy

    second = enemy if first == player else player
    return first, second
