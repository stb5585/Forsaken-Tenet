"""Item, spell, skill, and weapon selections for pygame combat."""

from __future__ import annotations

import sys

import pygame

from src.core.classes import (
    paladin,
    promotion_kits,
)
from src.core.combat.battle_engine import STOLEN_SCROLL_CHOICE_PREFIX
from src.ui_pygame.screen_runtime import get_events

from ..input_guards import release_guard_allows_input


class AbilitySelectionMixin:
    """Select inventory items and directly activated combat abilities."""

    def _select_item(self, player_char, enemy, *, support_only=False):
        """Show item selection menu and return selected item."""
        items = []
        for item_name, item_list in player_char.inventory.items():
            if item_list and self._combat_item_is_usable(item_list[0], support_only=support_only):
                items.append((item_name, item_list[0], len(item_list)))

        if not items:
            self.combat_view.add_combat_message("No usable items!")
            self._pause_with_events(500)
            return None

        selected = 0
        scroll_offset = 0
        input_armed = self._clear_pending_input()
        frame_player = self._selection_frame_player(player_char)
        while True:
            self._render_combat_frame(frame_player, enemy, [], -1)
            item_options = [f"{name} ({count})" for name, _, count in items]
            item_descriptions = [getattr(item, "description", "") for _, item, _ in items]
            self._render_described_selection_menu(
                "Select Item",
                item_options,
                selected,
                scroll_offset,
                item_descriptions,
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
                elif event.type == pygame.KEYDOWN:
                    if event.key in [pygame.K_ESCAPE, pygame.K_BACKSPACE]:
                        return None  # Cancel
                    elif event.key in [pygame.K_UP, pygame.K_w]:
                        selected = (selected - 1) % len(items)
                    elif event.key in [pygame.K_DOWN, pygame.K_s]:
                        selected = (selected + 1) % len(items)
                    elif event.key == pygame.K_PAGEUP:
                        selected = max(0, selected - 10)
                    elif event.key == pygame.K_PAGEDOWN:
                        selected = min(len(items) - 1, selected + 10)
                    elif event.key in [pygame.K_RETURN, pygame.K_SPACE]:
                        return items[selected][1]
                    scroll_offset = self._scroll_offset_for_selection(selected, scroll_offset)
                elif event.type == pygame.MOUSEWHEEL:
                    selected = max(0, min(len(items) - 1, selected - getattr(event, "y", 0)))
                    scroll_offset = self._scroll_offset_for_selection(selected, scroll_offset)
                elif self._selection_menu_back_clicked(event, input_armed):
                    return None
                elif event.type in (pygame.MOUSEMOTION, pygame.MOUSEBUTTONDOWN):
                    selected, scroll_offset, confirmed = self._selection_menu_mouse_update(
                        event,
                        item_options,
                        selected,
                        scroll_offset,
                        input_armed,
                    )
                    if confirmed:
                        return items[selected][1]
            clock = getattr(self.presenter, "clock", None)
            if clock is not None:
                clock.tick(60)

    @staticmethod
    def _combat_item_is_usable(item, *, support_only=False) -> bool:
        """Return whether an inventory item belongs in the combat item picker."""
        subtyp = getattr(item, "subtyp", "")
        if subtyp in {"Health", "Mana", "Elixir", "Status"}:
            return True
        if support_only:
            return False
        if subtyp == "Scroll":
            return hasattr(item, "spell")
        return False

    def _select_spell(self, player_char, enemy):
        """Show spell selection menu and return selected spell name."""
        from src.core import items as core_items
        from src.core.abilities.descriptions import described_selection_text

        spell_entries = [
            (
                name,
                f"{name} (MP: {getattr(spell, 'cost', 0)})",
                described_selection_text(player_char, spell),
            )
            for name, spell in player_char.spellbook["Spells"].items()
            if not getattr(spell, "passive", False)
            and not getattr(spell, "exploration_cast", False)
            and (getattr(spell, "subtyp", None) != "Movement" or name == "Volitation")
        ]
        scroll_entries = [
            (
                f"{STOLEN_SCROLL_CHOICE_PREFIX}{item_name}",
                f"{item_name} (Scroll)",
                getattr(item_list[0], "description", ""),
            )
            for item_name, item_list in player_char.inventory.items()
            if item_list and isinstance(item_list[0], core_items.InscribedSpellScroll)
        ]
        entries = spell_entries + scroll_entries

        if not entries:
            self.combat_view.add_combat_message("No spells learned!")
            self._pause_with_events(500)
            return None

        selected = 0
        scroll_offset = 0
        input_armed = self._clear_pending_input()
        frame_player = self._selection_frame_player(player_char)
        while True:
            self._render_combat_frame(frame_player, enemy, [], -1)
            spell_options = [label for _choice, label, _description in entries]
            spell_descriptions = [description for _choice, _label, description in entries]

            self._render_described_selection_menu(
                "Select Spell", spell_options, selected, scroll_offset, spell_descriptions
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
                elif event.type == pygame.KEYDOWN:
                    if event.key in [pygame.K_ESCAPE, pygame.K_BACKSPACE]:
                        return None  # Cancel
                    elif event.key in [pygame.K_UP, pygame.K_w]:
                        selected = (selected - 1) % len(entries)
                    elif event.key in [pygame.K_DOWN, pygame.K_s]:
                        selected = (selected + 1) % len(entries)
                    elif event.key == pygame.K_PAGEUP:
                        selected = max(0, selected - 10)
                    elif event.key == pygame.K_PAGEDOWN:
                        selected = min(len(entries) - 1, selected + 10)
                    elif event.key in [pygame.K_RETURN, pygame.K_SPACE]:
                        return entries[selected][0]
                    scroll_offset = self._scroll_offset_for_selection(selected, scroll_offset)
                elif self._selection_menu_back_clicked(event, input_armed):
                    return None
                elif event.type in (pygame.MOUSEMOTION, pygame.MOUSEBUTTONDOWN):
                    selected, scroll_offset, confirmed = self._selection_menu_mouse_update(
                        event,
                        spell_options,
                        selected,
                        scroll_offset,
                        input_armed,
                    )
                    if confirmed:
                        return entries[selected][0]

    def _select_skill(self, player_char, enemy, *, allowed_names=None):
        """Show skill selection menu and return selected skill name."""
        from src.core.abilities.descriptions import described_selection_text

        # Filter out passive and currently unusable equipment-dependent skills.
        skills = self._available_skill_names(
            player_char, enemy, allowed_names=allowed_names, resolve=False
        )

        if not skills:
            self.combat_view.add_combat_message("No skills learned!")
            self._pause_with_events(500)
            return None

        selected = 0
        scroll_offset = 0
        input_armed = self._clear_pending_input()
        frame_player = self._selection_frame_player(player_char)
        while True:
            # Render combat with skill menu overlay
            self._render_combat_frame(frame_player, enemy, [], -1)
            skill_options = []
            for skill_name in skills:
                skill = player_char.spellbook["Skills"][skill_name]
                cost = skill.cost
                if getattr(skill, "resource_type", None) == "Oath Conviction":
                    conviction = int(
                        promotion_kits.combat_state(player_char).get(
                            "oath_conviction",
                            0,
                        )
                        or 0
                    )
                    skill_options.append(f"{skill_name} (Conviction: all {conviction})")
                else:
                    skill_options.append(f"{skill_name} (MP: {cost})")
            skill_descriptions = []
            for skill_name in skills:
                skill = player_char.spellbook["Skills"][skill_name]
                if getattr(skill, "resource_type", None) == "Oath Conviction":
                    skill_descriptions.append(
                        paladin.oath_technique_description(
                            player_char,
                            skill_name,
                        )
                    )
                else:
                    skill_descriptions.append(described_selection_text(player_char, skill))

            self._render_described_selection_menu(
                "Select Skill", skill_options, selected, scroll_offset, skill_descriptions
            )
            pygame.display.flip()

            # Handle input
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
                        return None  # Cancel
                    elif event.key in [pygame.K_UP, pygame.K_w]:
                        selected = (selected - 1) % len(skills)
                    elif event.key in [pygame.K_DOWN, pygame.K_s]:
                        selected = (selected + 1) % len(skills)
                    elif event.key == pygame.K_PAGEUP:
                        selected = max(0, selected - 10)
                    elif event.key == pygame.K_PAGEDOWN:
                        selected = min(len(skills) - 1, selected + 10)
                    elif event.key in [pygame.K_RETURN, pygame.K_SPACE]:
                        return skills[selected]  # Return skill name

                    # Update scroll to keep selection visible
                    max_visible = 3
                    if selected < scroll_offset:
                        scroll_offset = selected
                    elif selected >= scroll_offset + max_visible:
                        scroll_offset = selected - max_visible + 1
                elif self._selection_menu_back_clicked(event, input_armed):
                    return None
                elif event.type in (pygame.MOUSEMOTION, pygame.MOUSEBUTTONDOWN):
                    selected, scroll_offset, confirmed = self._selection_menu_mouse_update(
                        event,
                        skill_options,
                        selected,
                        scroll_offset,
                        input_armed,
                    )
                    if confirmed:
                        return skills[selected]

    def _select_combat_weapon(self, player_char, enemy, skill):
        """Choose the carried weapon that Weapon Swap should equip."""
        weapons = skill.available_weapons(player_char)
        if not weapons:
            return None

        selected = 0
        scroll_offset = 0
        input_armed = self._clear_pending_input()
        frame_player = self._selection_frame_player(player_char)
        while True:
            self._render_combat_frame(frame_player, enemy, [], -1)
            options = [weapon.name for weapon in weapons]
            descriptions = [getattr(weapon, "description", "") for weapon in weapons]
            self._render_described_selection_menu(
                "Select Weapon",
                options,
                selected,
                scroll_offset,
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
                    if event.key in (pygame.K_UP, pygame.K_w):
                        selected = (selected - 1) % len(weapons)
                    elif event.key in (pygame.K_DOWN, pygame.K_s):
                        selected = (selected + 1) % len(weapons)
                    elif event.key == pygame.K_PAGEUP:
                        selected = max(0, selected - 10)
                    elif event.key == pygame.K_PAGEDOWN:
                        selected = min(len(weapons) - 1, selected + 10)
                    elif event.key in (pygame.K_RETURN, pygame.K_SPACE):
                        return weapons[selected]
                    scroll_offset = self._scroll_offset_for_selection(
                        selected,
                        scroll_offset,
                    )
                elif self._selection_menu_back_clicked(event, input_armed):
                    return None
                elif event.type in (pygame.MOUSEMOTION, pygame.MOUSEBUTTONDOWN):
                    selected, scroll_offset, confirmed = self._selection_menu_mouse_update(
                        event,
                        options,
                        selected,
                        scroll_offset,
                        input_armed,
                    )
                    if confirmed:
                        return weapons[selected]
