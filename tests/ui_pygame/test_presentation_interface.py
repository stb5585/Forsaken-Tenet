"""Coverage for the supported Pygame presentation interface."""

from __future__ import annotations

import pytest

from src.ui_pygame.presentation.interface import GamePresenter


def test_game_presenter_remains_abstract():
    """The interface cannot be constructed without a concrete frontend."""
    with pytest.raises(TypeError):
        GamePresenter()
