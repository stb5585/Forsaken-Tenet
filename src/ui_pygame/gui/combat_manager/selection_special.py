"""Special-form and support selections for pygame combat."""

from __future__ import annotations

import sys

import pygame

from src.core.classes import (
    ability_mechanics,
)
from src.ui_pygame.screen_runtime import get_events

from ..character_naming import CompanionNamingScreen
from ..input_guards import release_guard_allows_input
from .constants import _DISPLAY_TO_ENGINE


class SpecialSelectionMixin:
    """Select permanent callings, forms, support actions, and totems."""

    def _choose_calling_xenid(self, player_char, enemy, category):
        """Make the permanent paired choice required by a Calling spell."""
        from src.core import companions

        existing = companions.chosen_xenid(player_char, category)
        if existing:
            return existing
        options = list(companions.XENID_PAIRS.get(category, ()))
        if not options:
            return None
        selected = 0
        input_armed = self._clear_pending_input()
        frame_player = self._selection_frame_player(player_char)
        descriptions = [
            (
                f"Permanently bind {name} to Conjure {category}. "
                f"The other {category.lower()} Xenid will become unavailable."
            )
            for name in options
        ]
        while True:
            self._render_combat_frame(frame_player, enemy, [], -1)
            self._render_described_selection_menu(
                f"Choose {category} Xenid",
                options,
                selected,
                0,
                descriptions,
            )
            pygame.display.flip()
            input_armed = release_guard_allows_input(True, input_armed)
            for event in get_events():
                if event.type == pygame.QUIT:
                    pygame.quit()
                    sys.exit(0)
                input_armed = self._arm_guarded_input(event, input_armed)
                if event.type == pygame.KEYDOWN and not input_armed:
                    continue
                if event.type == pygame.KEYDOWN:
                    if event.key in (pygame.K_ESCAPE, pygame.K_BACKSPACE):
                        return None
                    if event.key in (pygame.K_UP, pygame.K_w, pygame.K_LEFT, pygame.K_a):
                        selected = (selected - 1) % len(options)
                    elif event.key in (
                        pygame.K_DOWN,
                        pygame.K_s,
                        pygame.K_RIGHT,
                        pygame.K_d,
                    ):
                        selected = (selected + 1) % len(options)
                    elif event.key in (pygame.K_RETURN, pygame.K_SPACE):
                        chosen = options[selected]
                        success, message = companions.choose_xenid(
                            player_char,
                            category,
                            chosen,
                        )
                        self.combat_view.add_combat_message(message)
                        return chosen if success else None
                elif event.type in (pygame.MOUSEMOTION, pygame.MOUSEBUTTONDOWN):
                    selected, _offset, confirmed = self._selection_menu_mouse_update(
                        event,
                        options,
                        selected,
                        0,
                        input_armed,
                    )
                    if confirmed:
                        chosen = options[selected]
                        success, message = companions.choose_xenid(
                            player_char,
                            category,
                            chosen,
                        )
                        self.combat_view.add_combat_message(message)
                        return chosen if success else None

    def _select_transform_form(self, player_char, enemy, forms):
        """Prompt for one of the Druid's unlocked combat forms."""
        descriptions = {
            "Panther": "A fast predator suited to accurate physical attacks.",
            "Direbear": "A durable bruiser with greater health and raw strength.",
        }
        selected = 0
        input_armed = self._clear_pending_input()
        frame_player = self._selection_frame_player(player_char)
        options = list(forms)
        while True:
            self._render_combat_frame(frame_player, enemy, [], -1)
            self._render_described_selection_menu(
                "Choose Form",
                options,
                selected,
                0,
                [descriptions.get(form, "") for form in options],
            )
            pygame.display.flip()

            input_armed = release_guard_allows_input(True, input_armed)
            for event in get_events():
                if event.type == pygame.QUIT:
                    pygame.quit()
                    sys.exit(0)
                input_armed = self._arm_guarded_input(event, input_armed)
                if event.type == pygame.KEYDOWN and not input_armed:
                    continue
                if event.type == pygame.KEYDOWN:
                    if event.key in (pygame.K_ESCAPE, pygame.K_BACKSPACE):
                        return None
                    if event.key in (pygame.K_UP, pygame.K_w, pygame.K_LEFT, pygame.K_a):
                        selected = (selected - 1) % len(options)
                    elif event.key in (
                        pygame.K_DOWN,
                        pygame.K_s,
                        pygame.K_RIGHT,
                        pygame.K_d,
                    ):
                        selected = (selected + 1) % len(options)
                    elif event.key in (pygame.K_RETURN, pygame.K_SPACE):
                        return options[selected]
                elif event.type in (pygame.MOUSEMOTION, pygame.MOUSEBUTTONDOWN):
                    selected, _offset, confirmed = self._selection_menu_mouse_update(
                        event,
                        options,
                        selected,
                        0,
                        input_armed,
                    )
                    if confirmed:
                        return options[selected]

    def _prompt_for_tamed_companion_name(self, player_char, enemy, background_surface=None) -> None:
        """Ask for an optional nickname after a successful tame."""
        state = ability_mechanics.normalize_tamed_companion(
            getattr(player_char, "tamed_companion", None)
        )
        companion_name = str(state.get("name") or getattr(enemy, "name", "Companion"))
        screen = CompanionNamingScreen(
            self.presenter,
            companion_name,
            species=str(state.get("species") or ""),
            form=str(state.get("evolution") or ""),
            special=str(state.get("special_ability") or ""),
        )
        nickname = screen.navigate(
            default="",
            flush_events=True,
            require_key_release=True,
            background_surface=background_surface,
        )
        nickname = str(nickname or "").strip()
        if not nickname:
            return
        ability_mechanics.rename_tamed_companion(player_char, nickname)
        display_name = ability_mechanics.tamed_companion_display_name(
            getattr(player_char, "tamed_companion", None)
        )
        original_name = getattr(enemy, "name", "companion")
        if display_name and display_name != original_name:
            self.combat_view.add_combat_message(f"{original_name} answers to {display_name}.")

    def _select_summoner_support_action(self, player_char, enemy):
        """Show the active-summon support menu and return display/action/choice seeds."""
        if self.engine is None:
            return None
        raw_actions = self.engine.summoner_support_actions()
        if not raw_actions:
            self.combat_view.add_combat_message("No summon support actions are available.")
            self._pause_with_events(500)
            return None
        display_actions = [
            str(action).replace("Use Skill", "Skills").replace("Use Item", "Items")
            for action in raw_actions
        ]
        selected = 0
        input_armed = self._clear_pending_input()
        while True:
            self._render_combat_frame(player_char, enemy, [], -1)
            self._render_selection_menu("Xenid Support", display_actions, selected)
            pygame.display.flip()

            input_armed = release_guard_allows_input(True, input_armed)
            for event in get_events():
                if event.type == pygame.QUIT:
                    pygame.quit()
                    sys.exit(0)
                input_armed = self._arm_guarded_input(event, input_armed)
                if event.type == pygame.KEYDOWN and not input_armed:
                    continue
                elif event.type == pygame.KEYDOWN:
                    if event.key in [pygame.K_ESCAPE, pygame.K_BACKSPACE]:
                        return None
                    elif event.key in [pygame.K_UP, pygame.K_w]:
                        selected = (selected - 1) % len(display_actions)
                    elif event.key in [pygame.K_DOWN, pygame.K_s]:
                        selected = (selected + 1) % len(display_actions)
                    elif event.key in [pygame.K_RETURN, pygame.K_SPACE]:
                        display = display_actions[selected]
                        return display, _DISPLAY_TO_ENGINE.get(display, display), None
                elif event.type in (pygame.MOUSEMOTION, pygame.MOUSEBUTTONDOWN):
                    selected, _scroll_offset, confirmed = self._selection_menu_mouse_update(
                        event,
                        display_actions,
                        selected,
                        0,
                        input_armed,
                    )
                    if confirmed:
                        display = display_actions[selected]
                        return display, _DISPLAY_TO_ENGINE.get(display, display), None

    def _select_totem_aspect(self, player_char, enemy, totem_skill):
        """Show Totem aspect selection menu and return aspect name."""
        if not totem_skill or not hasattr(totem_skill, "get_unlocked_aspects"):
            return None

        aspects = totem_skill.get_unlocked_aspects(player_char)
        if not aspects:
            self.combat_view.add_combat_message("No Totem aspects unlocked!")
            self._pause_with_events(500)
            return None

        selected = 0
        active = getattr(totem_skill, "active_aspect", "")
        input_armed = self._clear_pending_input()
        while True:
            self._render_combat_frame(player_char, enemy, [], -1)
            options = []
            for aspect in aspects:
                suffix = " (Active)" if aspect == active else ""
                options.append(f"{aspect}{suffix}")

            self._render_selection_menu("Select Totem Aspect", options, selected)
            pygame.display.flip()

            input_armed = release_guard_allows_input(True, input_armed)
            for event in get_events():
                if event.type == pygame.QUIT:
                    pygame.quit()
                    sys.exit(0)
                input_armed = self._arm_guarded_input(event, input_armed)
                if event.type == pygame.KEYDOWN and not input_armed:
                    continue
                elif event.type == pygame.KEYDOWN:
                    if event.key in [pygame.K_ESCAPE, pygame.K_BACKSPACE]:
                        return None
                    elif event.key in [pygame.K_UP, pygame.K_w]:
                        selected = (selected - 1) % len(aspects)
                    elif event.key in [pygame.K_DOWN, pygame.K_s]:
                        selected = (selected + 1) % len(aspects)
                    elif event.key in [pygame.K_RETURN, pygame.K_SPACE]:
                        return aspects[selected]
                elif event.type in (pygame.MOUSEMOTION, pygame.MOUSEBUTTONDOWN):
                    selected, _scroll_offset, confirmed = self._selection_menu_mouse_update(
                        event,
                        options,
                        selected,
                        0,
                        input_armed,
                    )
                    if confirmed:
                        return aspects[selected]
