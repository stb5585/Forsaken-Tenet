"""Outcomes behavior for the combat manager package."""

from __future__ import annotations

import sys

import pygame

from ..combat_view.animator import DEATH_ANIMATION_FRAMES
from ..enemy_presentation import is_invisible_target, player_has_sight
from .constants import (
    DEFEAT_PAUSE_MS,
    ENEMY_PRE_ACTION_HOLD_FRAMES,
    ENEMY_RESULT_HOLD_FRAMES,
    FLEE_PAUSE_MS,
)
from .helpers import _player_facing_victory_line

POST_DEATH_PAUSE_MS = 75


class CombatOutcomeMixin:
    def _enemy_turn(self, player_char, enemy):
        """Handle enemy's turn (automated), delegating logic to the engine."""
        # Pre-turn: process status effects and check activity
        pre = self.engine.pre_turn()
        if pre.effects_text:
            for line in pre.effects_text.strip().split("\n"):
                if line.strip():
                    self.combat_view.add_combat_message(line)
            self._flush_result_frame(player_char, enemy)

        # If the enemy died from its own effects (poison, DOT, bleed), end turn
        if pre.died_from_effects:
            return None

        if not pre.can_act:
            self.combat_view.add_combat_message(pre.inactive_reason.strip())
            self._flush_result_frame(player_char, enemy)
            return None  # Skip turn

        # Render current state and pause before enemy acts (with animation updates)
        enemy_clock = pygame.time.Clock()
        for _ in range(ENEMY_PRE_ACTION_HOLD_FRAMES):
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    pygame.quit()
                    sys.exit(0)
                self._handle_combat_log_scroll_event(event)
            self._flush_result_frame(player_char, enemy)
            enemy_clock.tick(60)

        self._apply_vesperion_phase_pressure(player_char, enemy)
        if not player_char.is_alive():
            return None

        # Check for forced actions (charging skills, jump)
        forced = self.engine.get_forced_action()
        if forced:
            if forced.action == "Cancelled":
                for line in forced.cancel_message.strip().split("\n"):
                    if line.strip():
                        self.combat_view.add_combat_message(line)
                self._flush_result_frame(player_char, enemy)
                return None

            enemy_name_before = enemy.name
            enemy_hp_before = enemy.health.current
            player_hp_before = player_char.health.current
            player_stun_before = bool(player_char.status_effects["Stun"].active)

            result = self.engine.execute_action(forced.action, choice=forced.choice)
            self._announce_new_resolutions(result)
            self._record_bestiary_ability_if_visible(
                player_char, enemy, forced.choice or forced.action
            )
            for line in result.message.strip().split("\n"):
                if line.strip():
                    self.combat_view.add_combat_message(line)
            self._add_new_player_stun_message(player_char, player_stun_before, result.message)

            self._flush_result_frame(player_char, enemy)

            # Check if enemy shapeshifted
            if enemy.name != enemy_name_before:
                self.combat_view.reload_enemy_sprite(enemy)

            damage_to_player = max(0, player_hp_before - player_char.health.current)
            if damage_to_player > 0:
                self._show_combat_damage_effect(
                    "player", forced.action, forced.choice, result.message, damage_to_player
                )
                self._flush_result_frame(player_char, enemy)
            else:
                self._show_combat_heal_text(
                    "player", max(0, player_char.health.current - player_hp_before)
                )
            self._show_combat_heal_text("enemy", max(0, enemy.health.current - enemy_hp_before))

            if result.fled:
                return "flee"
            return None

        def is_shapeshift_action(action_name, choice_name, skill_obj=None):
            return action_name == "Use Skill" and (
                choice_name == "Shapeshift" or getattr(skill_obj, "name", "") == "Shapeshift"
            )

        def execute_enemy_action(action_name, choice_name, *, pause_after=True):
            if action_name == "Nothing":
                self.combat_view.add_combat_message(f"{enemy.name} does nothing.")
                return None, False

            # Record state before execution
            player_hp_before = player_char.health.current
            player_stun_before = bool(player_char.status_effects["Stun"].active)
            enemy_name_before = enemy.name
            enemy_hp_before = enemy.health.current

            # Delegate to engine (handles Smoke Screen flee, Slot Machine, Doublecast, Jump, etc.)
            slot_cb = None
            skill_obj = None
            if action_name == "Use Skill" and choice_name:
                skill_obj = enemy.spellbook.get("Skills", {}).get(choice_name)
                if skill_obj and skill_obj.name == "Slot Machine":

                    def slot_cb(_u, _t):
                        return self._show_slot_machine_reveal(player_char, enemy)

            result = self.engine.execute_action(
                action_name, choice=choice_name, slot_machine_callback=slot_cb
            )
            self._announce_new_resolutions(result)
            self._record_bestiary_ability_if_visible(player_char, enemy, choice_name or action_name)
            is_smoke_screen = action_name == "Use Skill" and (
                choice_name == "Smoke Screen" or getattr(skill_obj, "name", "") == "Smoke Screen"
            )
            action_fled = result.fled or bool(getattr(self.engine, "flee", False))
            if action_fled and is_smoke_screen:
                self.combat_view.hide_enemy_for_flee()

            # Display messages
            for line in result.message.strip().split("\n"):
                if line.strip():
                    self.combat_view.add_combat_message(line)
            self._add_new_player_stun_message(player_char, player_stun_before, result.message)

            if is_smoke_screen and action_fled:
                self._play_smoke_screen_visual(player_char, enemy, "enemy")
            else:
                self._flush_result_frame(player_char, enemy)

            # Check if enemy shapeshifted (name changed)
            shapeshifted = is_shapeshift_action(action_name, choice_name, skill_obj)
            if enemy.name != enemy_name_before:
                self.combat_view.reload_enemy_sprite(enemy)

            # Show damage flash if player took damage
            damage_to_player = max(0, player_hp_before - player_char.health.current)
            if damage_to_player > 0:
                self._show_combat_damage_effect(
                    "player", action_name, choice_name, result.message, damage_to_player
                )
                self._flush_result_frame(player_char, enemy)
            else:
                self._show_combat_heal_text(
                    "player", max(0, player_char.health.current - player_hp_before)
                )
            self._show_combat_heal_text("enemy", max(0, enemy.health.current - enemy_hp_before))

            if action_fled:
                return "flee", shapeshifted

            if pause_after:
                # Render updated state and show result (with animation updates)
                result_clock = pygame.time.Clock()
                for _ in range(ENEMY_RESULT_HOLD_FRAMES):
                    for event in pygame.event.get():
                        if event.type == pygame.QUIT:
                            pygame.quit()
                            sys.exit(0)
                        self._handle_combat_log_scroll_event(event)
                    self._render_combat_frame(player_char, enemy, [], -1)
                    pygame.display.flip()
                    result_clock.tick(60)

            return None, shapeshifted

        # Enemy AI chooses action
        action, choice = self.engine.get_enemy_action()
        skill_obj = (
            enemy.spellbook.get("Skills", {}).get(choice)
            if action == "Use Skill" and choice
            else None
        )
        result_status, shapeshifted = execute_enemy_action(
            action,
            choice,
            pause_after=not is_shapeshift_action(action, choice, skill_obj),
        )
        if result_status:
            return result_status

        if shapeshifted and player_char.is_alive():
            follow_action, follow_choice = self.engine.get_enemy_action()
            follow_skill = (
                enemy.spellbook.get("Skills", {}).get(follow_choice)
                if follow_action == "Use Skill" and follow_choice
                else None
            )
            if is_shapeshift_action(follow_action, follow_choice, follow_skill):
                follow_action, follow_choice = "Attack", None
            result_status, _follow_shapeshifted = execute_enemy_action(follow_action, follow_choice)
            if result_status:
                return result_status

        return None

    def _add_new_player_stun_message(
        self, player_char, was_stunned: bool, result_message: str
    ) -> None:
        """Ensure newly-applied player stun is visible even when an effect omits text."""
        stun = getattr(player_char, "status_effects", {}).get("Stun")
        is_stunned = bool(getattr(stun, "active", False))
        if is_stunned and not was_stunned and "stun" not in (result_message or "").lower():
            self.combat_view.add_combat_message(f"{player_char.name} is stunned and cannot act.")

    def _render_combat_frame(self, player_char, enemy, actions, selected_action):
        """Render a single frame of combat."""
        refresh_layout = getattr(self.combat_view, "refresh_layout", None)
        if callable(refresh_layout):
            refresh_layout()
        if not hasattr(player_char, "level_exp"):
            player_char = self._selection_frame_player(player_char)

        from src.core.combat.action_interface import combat_interface_snapshot

        interface_snapshot = (
            combat_interface_snapshot(self.engine, player_char) if self.engine is not None else None
        )
        timeline_entries = self._timeline_entries_for_frame(
            interface_snapshot.timeline if interface_snapshot is not None else ()
        )

        # Clear screen
        self.screen.fill((0, 0, 0))

        # Render the dungeon view as background (same as exploration)
        # This is passed from dungeon_manager
        if self.dungeon_renderer and self.player_world_dict:
            try:
                self.dungeon_renderer.render_dungeon_view(player_char, self.player_world_dict)
            except Exception:
                # Fallback to black screen if dungeon rendering fails
                self.screen.fill((0, 0, 0))

        current_turn = None
        current_actor = None
        if self.engine is not None and getattr(self.engine, "attacker", None) is not None:
            current_actor = self.engine.attacker
            current_turn = "player" if self.engine.is_player_turn() else "enemy"
        encounter = getattr(self.engine, "encounter", None)
        if encounter is not None:
            has_sight = player_has_sight(player_char)
            identity_setter = getattr(
                self.combat_view,
                "set_hidden_enemy_identities",
                None,
            )
            if callable(identity_setter):
                identity_setter(
                    member.enemy.name
                    for member in encounter.members
                    if is_invisible_target(member.enemy) and not has_sight
                )
            focus_id = self.engine.focus_target_id
            focused_member = encounter.member_by_id(focus_id)
            enemy = focused_member.enemy
            details_by_id = {
                member.combatant_id: self.engine.show_enemy_details(member.enemy)
                for member in encounter.members
            }
            show_enemy_details = details_by_id[focus_id]
            for member in encounter.members:
                if details_by_id[member.combatant_id] and hasattr(
                    player_char, "record_bestiary_enemy"
                ):
                    player_char.record_bestiary_enemy(
                        member.enemy,
                        getattr(member.enemy, "enemy_typ", None),
                    )
        else:
            focus_id = ""
            details_by_id = {}
            show_enemy_details = None
            if self.engine is not None and hasattr(self.engine, "show_enemy_details"):
                show_enemy_details = self.engine.show_enemy_details()
            if show_enemy_details and hasattr(player_char, "record_bestiary_enemy"):
                player_char.record_bestiary_enemy(
                    enemy,
                    getattr(enemy, "enemy_typ", None),
                )

        # Render enemy in the dungeon (in front of player)
        if encounter is not None:
            self.combat_view.render_encounter_in_dungeon(
                player_char,
                encounter,
                focus_target_id=focus_id,
                details_by_id=details_by_id,
            )
        else:
            self.combat_view.render_enemy_in_dungeon(
                player_char,
                enemy,
                show_enemy_details=show_enemy_details,
            )

        # Render combat HUD overlay (action menu and combat log)
        self.combat_view.render_combat_overlay(
            player_char,
            enemy,
            actions,
            selected_action,
            current_turn=current_turn,
            show_enemy_details=show_enemy_details,
            current_actor=current_actor,
            timeline_entries=timeline_entries,
            interface_snapshot=interface_snapshot,
            engine=self.engine,
        )

        # Render HUD (right 1/3) with combat mode indicator
        active_summon = None
        if self.engine is not None and getattr(self.engine, "summon_active", False):
            summon = getattr(self.engine, "summon", None)
            is_alive = getattr(summon, "is_alive", None)
            if summon is not None and (bool(is_alive()) if callable(is_alive) else True):
                active_summon = summon
        self.hud.render_hud(
            player_char,
            combat_mode=True,
            enemy=enemy,
            active_summon=active_summon,
            combat_resources=interface_snapshot.resources if interface_snapshot is not None else (),
        )

    def _timeline_entries_for_frame(self, fresh_entries):
        """Keep defeated actor badges until their matching sprite fade completes."""
        fresh_entries = tuple(fresh_entries)
        previous_entries = tuple(getattr(self, "_last_combat_timeline", ()))
        is_fading = getattr(self.combat_view, "death_animation_in_progress", None)
        if not previous_entries or not callable(is_fading) or not is_fading():
            self._last_combat_timeline = fresh_entries
            return fresh_entries

        visible_actor_ids = {entry.actor_id for entry in fresh_entries}
        entries = list(fresh_entries)
        for old_index, entry in enumerate(previous_entries):
            if entry.actor_id not in visible_actor_ids:
                entries.insert(min(old_index, len(entries)), entry)
        merged = tuple(entries[:6])
        self._last_combat_timeline = merged
        return merged

    def _record_bestiary_ability_if_visible(self, player_char, enemy, ability_name) -> None:
        if self.engine is None or not hasattr(self.engine, "show_enemy_details"):
            return
        if not self.engine.show_enemy_details():
            return
        if hasattr(player_char, "record_bestiary_ability"):
            player_char.record_bestiary_ability(enemy, ability_name)

    def _refresh_combat_background(self, player_char, enemy):
        """Render and cache the latest combat frame for popups/overlays."""
        self._render_combat_frame(player_char, enemy, [], -1)
        pygame.display.flip()
        self._combat_background = self.screen.copy()

    def _handle_combat_end(self, player_char, enemy, fled):
        """Handle end of combat using the engine for bookkeeping."""

        def _show_end_popup(
            message_text: str, *, background=None, refresh_background: bool = True
        ) -> None:
            if refresh_background:
                self._refresh_combat_background(player_char, enemy)
            background = background or self._combat_background or self._capture_background()

            def draw_background():
                return self.screen.blit(background, (0, 0))

            from ..confirmation_popup import ConfirmationPopup

            popup = ConfirmationPopup(self.presenter, message_text, show_buttons=False)
            popup.show(
                background_draw_func=draw_background,
                flush_events=True,
                require_key_release=True,
            )

        # Handle Sanctuary (player got teleported to town during combat)
        if player_char.in_town():
            player_char.effects(end=True)
            self.logger.end_battle(result="Escaped", winner=None, boss=False)
            self._persist_debug_battle_log("escaped")
            self.combat_view.reset_combat_log()
            self._combat_background = None
            return False

        # Sync engine flee state (in case player fled via UI flow)
        if fled:
            self.engine.flee = True

        if self._is_reflection_psychopomp_combat(enemy):
            if fled:
                self.combat_view.add_combat_message("You step back from the Reflection.")
                self.combat_view.reset_combat_log()
                self._combat_background = None
                player_char.state = "normal"
                return False
            return self._handle_reflection_psychopomp_end(player_char, enemy)

        if self._is_guardian_trial_echo_combat(enemy):
            if fled:
                guardian_name = getattr(enemy, "liminal_trial_guardian", "the trial")
                self.combat_view.add_combat_message(f"You step back from {guardian_name}.")
                self.combat_view.reset_combat_log()
                self._combat_background = None
                player_char.state = "normal"
                return False
            return self._handle_guardian_trial_echo_end(player_char, enemy)

        if (
            self._is_vesperion_true_final_combat(player_char, enemy)
            and not fled
            and player_char.is_alive()
            and not enemy.is_alive()
        ):
            return self._handle_vesperion_true_final_victory(player_char, enemy)

        encounter = getattr(self.engine, "encounter", None)
        bounty_before = self._bounty_progress_snapshot(player_char, encounter, enemy)
        tamed_members = (
            [
                member
                for member in encounter.members
                if getattr(member.enemy, "tamed_by_player", False)
            ]
            if encounter is not None
            else []
        )
        if encounter is None and getattr(enemy, "tamed_by_player", False):
            tamed_members = [type("_TamedMember", (), {"enemy": enemy})()]
        tamed_victory = (
            bool(tamed_members)
            and len(encounter.members if encounter is not None else [enemy]) == 1
        )
        repelled_victory = bool(getattr(enemy, "paladin_repelled", False))

        # Finish the battlefield presentation before rewards can mutate the HUD.
        pre_outcome_background = self.screen.copy()
        death_in_progress = getattr(self.combat_view, "death_animation_in_progress", None)
        expected_victory = (
            not fled
            and player_char.is_alive()
            and (
                not enemy.is_alive()
                or tamed_victory
                or repelled_victory
                or (callable(death_in_progress) and death_in_progress())
            )
        )
        if expected_victory:
            if not tamed_victory and not repelled_victory:
                clock = pygame.time.Clock()
                for _ in range(DEATH_ANIMATION_FRAMES):
                    self._render_combat_frame(player_char, enemy, [], -1)
                    pygame.display.flip()
                    clock.tick(60)
                    for event in pygame.event.get():
                        if event.type == pygame.QUIT:
                            pygame.quit()
                            sys.exit(0)
                        self._handle_combat_log_scroll_event(event)
                self._pause_with_events(POST_DEATH_PAUSE_MS)
            else:
                self._refresh_combat_background(player_char, enemy)
            pre_outcome_background = self.screen.copy()
            self._combat_background = pre_outcome_background

        # Let the engine handle all bookkeeping (exp, loot, quests, kill tracking, etc.)
        outcome = self.engine.end_battle()
        self._persist_debug_battle_log(outcome.result)

        if outcome.result == "defeat":
            self._pause_with_events(DEFEAT_PAUSE_MS)
            death_summary = str(getattr(player_char, "last_death_message", "") or "").strip()
            defeat_message = "You have been defeated!"
            if death_summary:
                defeat_message = f"{defeat_message}\n\n{death_summary}"

            _show_end_popup(
                defeat_message,
                background=pre_outcome_background,
                refresh_background=False,
            )
            self.combat_view.reset_combat_log()
            self._combat_background = None
            return False

        elif outcome.result == "victory":
            # Build end messages from outcome
            if encounter is not None and len(encounter.members) > 1:
                end_messages = ["Victory! Encounter complete!"]
            elif tamed_victory:
                end_messages = [f"{enemy.name} tamed!"]
            elif repelled_victory or getattr(outcome, "enemy_escaped", False):
                end_messages = [f"{enemy.name} fled from battle!"]
            else:
                end_messages = [f"Victory! {enemy.name} defeated!"]
            if encounter is not None and len(encounter.members) > 1:
                count_labels = {
                    "defeated": "defeated",
                    "mercy": "spared",
                    "tamed": "tamed",
                    "ejected": "ejected",
                    "escaped": "escaped",
                }
                counts = ", ".join(
                    f"{count} {count_labels[resolution.value]}"
                    for resolution, count in outcome.resolution_counts
                )
                if counts:
                    end_messages.append(counts)
                end_messages.append(f"Total XP: {outcome.total_experience}")
                end_messages.append(f"Total gold: {outcome.total_gold}")
                if outcome.loot_awards:
                    loot = ", ".join(
                        (
                            f"{award.item_name} x{award.quantity}"
                            if award.quantity != 1
                            else award.item_name
                        )
                        for award in outcome.loot_awards
                    )
                    end_messages.append(f"Acquired: {loot}")
                for notice in outcome.notices:
                    end_messages.append(
                        _player_facing_victory_line(
                            notice,
                            debug_mode=self._debug_mode_enabled(),
                        )
                    )
            else:
                for line in outcome.message.strip().split("\n"):
                    if line.strip():
                        end_messages.append(
                            _player_facing_victory_line(
                                line,
                                debug_mode=self._debug_mode_enabled(),
                            )
                        )

            if outcome.level_up:
                end_messages.append("\nLEVEL UP!")

            end_messages.extend(self._bounty_progress_lines(player_char, bounty_before))

            _show_end_popup(
                "\n".join(end_messages),
                background=pre_outcome_background,
                refresh_background=False,
            )
            if tamed_members:
                self._prompt_for_tamed_companion_name(
                    player_char,
                    tamed_members[-1].enemy,
                    self._combat_background,
                )

            if outcome.level_up:
                self.level_up_screen.show_level_up(player_char, self.game)

            self.combat_view.reset_combat_log()
            self._combat_background = None
            self._last_combat_timeline = ()
            return True

        elif outcome.result == "flee":
            self._render_combat_frame(player_char, enemy, [], -1)
            pygame.display.flip()
            self._pause_with_events(FLEE_PAUSE_MS)

            _show_end_popup("You fled from combat!")
            self.combat_view.reset_combat_log()
            self._combat_background = None
            return False

        # Fallback
        self.combat_view.reset_combat_log()
        self._combat_background = None
        return True

    @staticmethod
    def _bounty_progress_snapshot(player_char, encounter, enemy) -> dict[str, tuple[int, int]]:
        """Capture active bounty counts for members that can resolve this encounter."""
        bounties = getattr(player_char, "quest_dict", {}).get("Bounty", {})
        if not isinstance(bounties, dict):
            return {}
        enemies = [enemy]
        if encounter is not None:
            enemies = [member.enemy for member in getattr(encounter, "members", ())]
        snapshot = {}
        for member_enemy in enemies:
            entry = bounties.get(getattr(member_enemy, "name", ""))
            if isinstance(entry, list) and len(entry) >= 3 and isinstance(entry[0], dict):
                snapshot[member_enemy.name] = (int(entry[1]), int(entry[0].get("num", 1)))
        return snapshot

    @staticmethod
    def _bounty_progress_lines(player_char, before: dict[str, tuple[int, int]]) -> list[str]:
        """Format bounty changes caused by a completed encounter for the victory popup."""
        bounties = getattr(player_char, "quest_dict", {}).get("Bounty", {})
        lines = []
        for name, (old_count, total) in before.items():
            entry = bounties.get(name) if isinstance(bounties, dict) else None
            if not isinstance(entry, list) or len(entry) < 3:
                continue
            new_count = int(entry[1])
            if new_count == old_count:
                continue
            suffix = " — Ready to turn in!" if bool(entry[2]) else ""
            lines.append(f"Bounty: {name} {new_count}/{total}{suffix}")
        return lines

    def _pause_with_events(self, duration_ms: int) -> None:
        """Pause briefly while pumping events to avoid unresponsive window."""
        pause_clock = pygame.time.Clock()
        elapsed = 0
        while elapsed < duration_ms:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    pygame.quit()
                    sys.exit(0)
                self._handle_combat_log_scroll_event(event)
            pause_clock.tick(60)
            elapsed += pause_clock.get_time()
