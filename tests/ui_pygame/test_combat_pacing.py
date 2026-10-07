"""Combat pacing constants preserve readable intrinsic animations."""

from src.ui_pygame.gui.combat_manager.constants import (
    COMBAT_START_TRANSITION_FRAMES,
    DEFEAT_PAUSE_MS,
    ENEMY_PRE_ACTION_HOLD_FRAMES,
    ENEMY_RESULT_HOLD_FRAMES,
    FLEE_PAUSE_MS,
    POST_TURN_DELAY_FRAMES,
)
from src.ui_pygame.gui.combat_manager.outcomes import POST_DEATH_PAUSE_MS
from src.ui_pygame.gui.combat_view.animator import DEATH_ANIMATION_FRAMES


def test_noninteractive_combat_waits_are_reduced():
    assert COMBAT_START_TRANSITION_FRAMES == 12
    assert ENEMY_PRE_ACTION_HOLD_FRAMES == 6
    assert ENEMY_RESULT_HOLD_FRAMES == 10
    assert POST_TURN_DELAY_FRAMES == 1
    assert DEFEAT_PAUSE_MS == 250
    assert FLEE_PAUSE_MS == 200
    assert POST_DEATH_PAUSE_MS == 40
    assert DEATH_ANIMATION_FRAMES == 18
