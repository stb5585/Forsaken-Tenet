"""Class-mechanic selections for pygame combat."""

from __future__ import annotations

import sys

import pygame

from src.core.classes import (
    ability_mechanics,
    astromancer,
    bard,
    demonologist,
    promotion_kits,
)
from src.ui_pygame.screen_runtime import get_events

from ..input_guards import release_guard_allows_input


class ClassMechanicSelectionMixin:
    """Select companion, repertoire, resolve, summon, rune, and contract actions."""

    def _select_companion_command(self, player_char, enemy):
        """Show Beast Master companion command selection and return command name."""
        commands = ability_mechanics.available_beast_companion_commands(player_char)
        if not commands:
            self.combat_view.add_combat_message("No companion commands available!")
            self._pause_with_events(500)
            return None

        selected = 0
        scroll_offset = 0
        input_armed = self._clear_pending_input()
        frame_player = self._selection_frame_player(player_char)
        while True:
            self._render_combat_frame(frame_player, enemy, [], -1)
            command_options = list(commands)
            descriptions = [
                getattr(player_char.spellbook["Skills"].get(name), "description", "")
                for name in commands
            ]
            self._render_described_selection_menu(
                "Command Companion",
                command_options,
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
                elif event.type == pygame.KEYDOWN:
                    if event.key in [pygame.K_ESCAPE, pygame.K_BACKSPACE]:
                        return None
                    elif event.key in [pygame.K_UP, pygame.K_w]:
                        selected = (selected - 1) % len(commands)
                    elif event.key in [pygame.K_DOWN, pygame.K_s]:
                        selected = (selected + 1) % len(commands)
                    elif event.key == pygame.K_PAGEUP:
                        selected = max(0, selected - 10)
                    elif event.key == pygame.K_PAGEDOWN:
                        selected = min(len(commands) - 1, selected + 10)
                    elif event.key in [pygame.K_RETURN, pygame.K_SPACE]:
                        return commands[selected]
                    scroll_offset = self._scroll_offset_for_selection(selected, scroll_offset)
                elif event.type in (pygame.MOUSEMOTION, pygame.MOUSEBUTTONDOWN):
                    selected, scroll_offset, confirmed = self._selection_menu_mouse_update(
                        event,
                        command_options,
                        selected,
                        scroll_offset,
                        input_armed,
                    )
                    if confirmed:
                        return commands[selected]

    def _select_repertoire_song(self, player_char, enemy):
        """Show mastered Troubadour songs and return the selected title."""
        songs = bard.mastered_repertoire_songs(player_char)
        if not songs:
            self.combat_view.add_combat_message("No mastered repertoire available!")
            self._pause_with_events(500)
            return None

        descriptions = [
            (f"{bard.REPERTOIRE_MP_COSTS[song]} MP - {bard.SONGS[song]['description']}")
            for song in songs
        ]
        selected = 0
        scroll_offset = 0
        input_armed = self._clear_pending_input()
        frame_player = self._selection_frame_player(player_char)
        while True:
            self._render_combat_frame(frame_player, enemy, [], -1)
            self._render_described_selection_menu(
                "Mastered Repertoire",
                songs,
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
                        selected = (selected - 1) % len(songs)
                    elif event.key in (pygame.K_DOWN, pygame.K_s):
                        selected = (selected + 1) % len(songs)
                    elif event.key in (pygame.K_RETURN, pygame.K_SPACE):
                        return songs[selected]
                    scroll_offset = self._scroll_offset_for_selection(
                        selected,
                        scroll_offset,
                    )
                elif event.type in (pygame.MOUSEMOTION, pygame.MOUSEBUTTONDOWN):
                    selected, scroll_offset, confirmed = self._selection_menu_mouse_update(
                        event,
                        songs,
                        selected,
                        scroll_offset,
                        input_armed,
                    )
                    if confirmed:
                        return songs[selected]

    def _select_resolve_ability(self, player_char, enemy, *, bursts=False):
        """Show a Resolve spend or full-bar burst selection menu."""
        skills = self._available_skill_names(player_char, enemy, resolve=True)
        burst_names = {entry["name"] for entry in promotion_kits.RESOLVE_SURGES}
        if bursts:
            skills = [name for name in skills if name in burst_names]
        else:
            skills = [name for name in skills if name not in burst_names]
        if not skills:
            label = "bursts" if bursts else "abilities"
            self.combat_view.add_combat_message(f"No Resolve {label} available!")
            self._pause_with_events(500)
            return None

        selected = 0
        scroll_offset = 0
        input_armed = self._clear_pending_input()
        frame_player = self._selection_frame_player(player_char)
        while True:
            self._render_combat_frame(frame_player, enemy, [], -1)
            resolve_options = []
            for skill_name in skills:
                skill = player_char.spellbook["Skills"][skill_name]
                display_name = self._canonical_resolve_skill_name(
                    getattr(skill, "name", skill_name)
                )
                resolve_options.append(
                    f"{display_name} ({self._resolve_skill_cost_label(skill, player_char)})"
                )
            descriptions = [
                getattr(player_char.spellbook["Skills"][skill_name], "description", "")
                for skill_name in skills
            ]
            self._render_described_selection_menu(
                "Select Resolve Burst" if bursts else "Select Resolve",
                resolve_options,
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
                elif event.type == pygame.KEYDOWN:
                    if event.key in [pygame.K_ESCAPE, pygame.K_BACKSPACE]:
                        return None
                    elif event.key in [pygame.K_UP, pygame.K_w]:
                        selected = (selected - 1) % len(skills)
                    elif event.key in [pygame.K_DOWN, pygame.K_s]:
                        selected = (selected + 1) % len(skills)
                    elif event.key == pygame.K_PAGEUP:
                        selected = max(0, selected - 10)
                    elif event.key == pygame.K_PAGEDOWN:
                        selected = min(len(skills) - 1, selected + 10)
                    elif event.key in [pygame.K_RETURN, pygame.K_SPACE]:
                        return skills[selected]
                    scroll_offset = self._scroll_offset_for_selection(selected, scroll_offset)
                elif event.type in (pygame.MOUSEMOTION, pygame.MOUSEBUTTONDOWN):
                    selected, scroll_offset, confirmed = self._selection_menu_mouse_update(
                        event,
                        resolve_options,
                        selected,
                        scroll_offset,
                        input_armed,
                    )
                    if confirmed:
                        return skills[selected]

    def _select_summon(self, player_char, enemy):
        """Show summon selection menu and return selected summon name."""
        summons = getattr(player_char, "summons", {}) or {}
        summon_names = [
            name for name, summon in summons.items() if self._living_summon_available(summon)
        ]

        if not summon_names:
            self.combat_view.add_combat_message("No summons available!")
            self._pause_with_events(500)
            return None

        selected = 0
        scroll_offset = 0
        input_armed = self._clear_pending_input()
        while True:
            self._render_combat_frame(player_char, enemy, [], -1)
            summon_options = []
            for summon_name in summon_names:
                summon = summons[summon_name]
                level = getattr(getattr(summon, "level", None), "level", None)
                suffix = f" (Lv {level})" if level is not None else ""
                summon_options.append(f"{summon_name}{suffix}")

            self._render_selection_menu("Select Summon", summon_options, selected, scroll_offset)
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
                        selected = (selected - 1) % len(summon_names)
                    elif event.key in [pygame.K_DOWN, pygame.K_s]:
                        selected = (selected + 1) % len(summon_names)
                    elif event.key == pygame.K_PAGEUP:
                        selected = max(0, selected - 10)
                    elif event.key == pygame.K_PAGEDOWN:
                        selected = min(len(summon_names) - 1, selected + 10)
                    elif event.key in [pygame.K_RETURN, pygame.K_SPACE]:
                        return summon_names[selected]
                    scroll_offset = self._scroll_offset_for_selection(selected, scroll_offset)
                elif event.type in (pygame.MOUSEMOTION, pygame.MOUSEBUTTONDOWN):
                    selected, scroll_offset, confirmed = self._selection_menu_mouse_update(
                        event,
                        summon_options,
                        selected,
                        scroll_offset,
                        input_armed,
                    )
                    if confirmed:
                        return summon_names[selected]

    @staticmethod
    def _living_summon_available(summon) -> bool:
        is_alive = getattr(summon, "is_alive", None)
        return bool(is_alive()) if callable(is_alive) else True

    def _select_runic_boost_spell(self, player_char, enemy):
        """Show Runic Boost spell selection and return selected spell name."""
        spells = astromancer.boostable_spells(player_char)
        if not spells:
            self.combat_view.add_combat_message("No rune-boostable spells are ready!")
            self._pause_with_events(500)
            return None

        selected = 0
        scroll_offset = 0
        input_armed = self._clear_pending_input()
        while True:
            self._render_combat_frame(player_char, enemy, [], -1)
            spell_options = []
            for spell_name in spells:
                spell = player_char.spellbook["Spells"][spell_name]
                sign = astromancer.sign_for_spell(spell) or "Rune"
                spell_options.append(f"{sign}: {spell_name} (MP: {spell.cost})")
            spell_descriptions = [
                getattr(player_char.spellbook["Spells"][spell_name], "description", "")
                for spell_name in spells
            ]

            self._render_described_selection_menu(
                "Runic Boost", spell_options, selected, scroll_offset, spell_descriptions
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
                        return None
                    elif event.key in [pygame.K_UP, pygame.K_w]:
                        selected = (selected - 1) % len(spells)
                    elif event.key in [pygame.K_DOWN, pygame.K_s]:
                        selected = (selected + 1) % len(spells)
                    elif event.key == pygame.K_PAGEUP:
                        selected = max(0, selected - 10)
                    elif event.key == pygame.K_PAGEDOWN:
                        selected = min(len(spells) - 1, selected + 10)
                    elif event.key in [pygame.K_RETURN, pygame.K_SPACE]:
                        return spells[selected]

                    max_visible = 3
                    if selected < scroll_offset:
                        scroll_offset = selected
                    elif selected >= scroll_offset + max_visible:
                        scroll_offset = selected - max_visible + 1
                elif event.type in (pygame.MOUSEMOTION, pygame.MOUSEBUTTONDOWN):
                    selected, scroll_offset, confirmed = self._selection_menu_mouse_update(
                        event,
                        spell_options,
                        selected,
                        scroll_offset,
                        input_armed,
                    )
                    if confirmed:
                        return spells[selected]

    def _select_steal_as_well_spell(self, player_char, enemy):
        """Show Steal As Well spell/scroll selection and return the selected name."""
        from src.core import items as core_items

        options = [
            name
            for name, spell in player_char.spellbook["Spells"].items()
            if spell.subtyp not in {"Support", "Movement"}
            and spell.cost <= player_char.mana.current
        ]
        options.extend(
            item_name
            for item_name, item_list in player_char.inventory.items()
            if item_list and isinstance(item_list[0], core_items.InscribedSpellScroll)
        )
        if not options:
            self.combat_view.add_combat_message("No spell theft options are ready!")
            self._pause_with_events(500)
            return None

        selected = 0
        scroll_offset = 0
        input_armed = self._clear_pending_input()
        while True:
            self._render_combat_frame(player_char, enemy, [], -1)
            descriptions = []
            for option in options:
                spell = player_char.spellbook["Spells"].get(option)
                if spell is not None:
                    descriptions.append(getattr(spell, "description", ""))
                    continue
                item_list = player_char.inventory.get(option, [])
                descriptions.append(getattr(item_list[0], "description", "") if item_list else "")
            self._render_described_selection_menu(
                "Steal As Well", options, selected, scroll_offset, descriptions
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
                        return None
                    elif event.key in [pygame.K_UP, pygame.K_w]:
                        selected = (selected - 1) % len(options)
                    elif event.key in [pygame.K_DOWN, pygame.K_s]:
                        selected = (selected + 1) % len(options)
                    elif event.key == pygame.K_PAGEUP:
                        selected = max(0, selected - 10)
                    elif event.key == pygame.K_PAGEDOWN:
                        selected = min(len(options) - 1, selected + 10)
                    elif event.key in [pygame.K_RETURN, pygame.K_SPACE]:
                        return options[selected]

                    max_visible = 3
                    if selected < scroll_offset:
                        scroll_offset = selected
                    elif selected >= scroll_offset + max_visible:
                        scroll_offset = selected - max_visible + 1
                elif event.type in (pygame.MOUSEMOTION, pygame.MOUSEBUTTONDOWN):
                    selected, scroll_offset, confirmed = self._selection_menu_mouse_update(
                        event,
                        options,
                        selected,
                        scroll_offset,
                        input_armed,
                    )
                    if confirmed:
                        return options[selected]

    def _select_contract_intent(self, player_char, enemy):
        """Choose and confirm a Demonologist contract intent."""
        intents = demonologist.available_intents(player_char)
        if not intents:
            self.combat_view.add_combat_message("No active fiend contract is bound.")
            self._pause_with_events(500)
            return None

        selected = 0
        scroll_offset = 0
        input_armed = self._clear_pending_input()

        def confirm_intent(intent):
            quote = demonologist.quote_contract(player_char, enemy, intent)
            if not quote.get("ok"):
                self.combat_view.add_combat_message(quote.get("reason", "The patron refuses."))
                self._pause_with_events(700)
                return None
            costs = quote["costs"]
            lines = [
                f"{quote['patron']} demands {costs['gold']} gold.",
                f"Misbehavior risk: {int(quote['misbehavior_chance'] * 100)}%",
            ]
            if costs.get("item"):
                lines.append("Additional demand: one potion.")
            permanent = costs.get("permanent")
            if permanent:
                lines.append(
                    f"Additional demand: permanent {permanent['amount']} {permanent['stat']}."
                )
            if not demonologist.can_pay_quote(player_char, quote):
                self.combat_view.add_combat_message("You cannot pay that price.")
                self._pause_with_events(700)
                return None
            if self.presenter.render_menu("\n".join(lines), ["Accept", "Refuse"]) == 0:
                return intent
            return None

        while True:
            self._render_combat_frame(player_char, enemy, [], -1)
            self._render_selection_menu("Ask Fiend", intents, selected, scroll_offset)
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
                        selected = (selected - 1) % len(intents)
                    elif event.key in [pygame.K_DOWN, pygame.K_s]:
                        selected = (selected + 1) % len(intents)
                    elif event.key in [pygame.K_RETURN, pygame.K_SPACE]:
                        return confirm_intent(intents[selected])

                    max_visible = 3
                    if selected < scroll_offset:
                        scroll_offset = selected
                    elif selected >= scroll_offset + max_visible:
                        scroll_offset = selected - max_visible + 1
                elif event.type in (pygame.MOUSEMOTION, pygame.MOUSEBUTTONDOWN):
                    selected, scroll_offset, confirmed = self._selection_menu_mouse_update(
                        event,
                        intents,
                        selected,
                        scroll_offset,
                        input_armed,
                    )
                    if confirmed:
                        return confirm_intent(intents[selected])
