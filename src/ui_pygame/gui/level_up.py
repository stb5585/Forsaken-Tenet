"""Pygame level-up presentation backed by the shared progression service."""

import pygame

from src.ui_pygame.screen_runtime import get_events

from .level_up_popup import LevelUpPopup


class LevelUpScreen:
    """Display canonical level-up results in a popup."""

    def __init__(self, screen, presenter):
        self.screen = screen
        self.presenter = presenter
        self._popup_background = None

    def show_level_up(self, player_char, game):
        """Display the result of the player's most recent level increase.

        Args:
            player_char: Player whose progression result should be displayed.
            game: Retained for compatibility with existing callers.

        Returns:
            A dictionary of level and stat gains rendered by the popup.
        """
        level_info = self._calculate_level_up(player_char)
        self._popup_background = self._get_background_surface()

        popup = LevelUpPopup(self.presenter, level_info)
        popup.show(
            background_draw_func=self._draw_popup_background,
            flush_events=True,
            require_key_release=True,
        )

        return level_info

    def _calculate_level_up(self, player_char):
        """Return display data from the canonical progression service."""
        from src.core.progression import (
            award_experience,
            cumulative_experience_for_level,
            ensure_progression,
        )

        result = getattr(player_char, "_pending_level_up_result", None)
        if result is not None:
            player_char._pending_level_up_result = None
        else:
            state = ensure_progression(player_char)
            if state.level >= 100:
                growth = ()
                points_awarded = 0
                attribute_points_awarded = 0
            else:
                target_xp = cumulative_experience_for_level(state.level + 1)
                result = award_experience(
                    player_char,
                    max(0, target_xp - state.total_xp),
                )

        if result is not None:
            growth = result.growth
            points_awarded = result.points_awarded
            attribute_points_awarded = result.attribute_points_awarded

        point_messages = []
        if points_awarded:
            point_messages.append(
                f"+{points_awarded} progression point" f"{'s' if points_awarded != 1 else ''}"
            )
        if attribute_points_awarded:
            point_messages.append(
                f"+{attribute_points_awarded} attribute point"
                f"{'s' if attribute_points_awarded != 1 else ''}"
            )

        return {
            "new_level": player_char.level.level,
            "health_gain": sum(item.health for item in growth),
            "mana_gain": sum(item.mana for item in growth),
            "attack_gain": sum(item.attack for item in growth),
            "defense_gain": sum(item.defense for item in growth),
            "magic_gain": sum(item.magic for item in growth),
            "magic_def_gain": sum(item.magic_defense for item in growth),
            "new_abilities": point_messages,
            "spell_upgrades": [],
            "skill_upgrades": [],
        }

    def _get_background_surface(self):
        if hasattr(self.presenter, "get_background_surface"):
            try:
                surface = self.presenter.get_background_surface()
                if surface is not None:
                    return surface.copy()
            except Exception:
                pass
        return self.screen.copy()

    def _draw_popup_background(self):
        if self._popup_background is None:
            self._popup_background = self._get_background_surface()
        self.screen.blit(self._popup_background, (0, 0))

    def _wait_for_continue(self):
        """Wait for the player to press a key or close the window."""
        waiting = True
        while waiting:
            for event in get_events():
                if event.type in (pygame.QUIT, pygame.KEYDOWN):
                    waiting = False
