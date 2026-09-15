"""Lifecycle behavior for the combat manager package."""

from __future__ import annotations

import sys
from typing import TYPE_CHECKING

import pygame

from src.core import enemies
from src.core.character import Character
from src.core.classes import ability_mechanics, promotion_kits
from src.core.combat import ActionIntent, CombatEncounter, TargetScope
from src.core.combat.action_interface import (
    SYSTEM_COMMANDS,
    CombatActionPresentation,
    combat_interface_snapshot,
)
from src.core.combat.battle_engine import BattleEngine
from src.core.player import Player
from src.ui_pygame.gui.enemy_presentation import (
    is_invisible_target,
    player_has_sight,
)

from ..input_guards import release_guard_allows_input
from ..mouse_helpers import hit_index, is_left_click, mouse_position
from .constants import (
    _DISPLAY_TO_ENGINE,
    COMBAT_START_TRANSITION_FRAMES,
    POST_TURN_DELAY_FRAMES,
    VESPERION_FALSE_FINAL_ENEMY_TURNS,
)

if TYPE_CHECKING:
    from src.core.map_tiles import MapTile


class CombatLifecycleMixin:
    def _focused_combat_enemy(self, fallback):
        """Return engine focus while retaining compatibility with test adapters."""
        focused = getattr(self.engine, "_focused_enemy", None)
        if callable(focused):
            return focused()
        encounter = getattr(self.engine, "encounter", None)
        if encounter is not None:
            try:
                return encounter.member_by_id(self.engine.focus_target_id).enemy
            except (AttributeError, KeyError, ValueError):
                pass
        return fallback

    def _current_enemy_actor(self, fallback):
        """Return the scheduled hostile actor or a singleton fallback."""
        actor = getattr(self.engine, "attacker", None)
        if actor is not None and actor is not getattr(self.engine, "player", None):
            return actor
        return fallback

    def start_combat(
        self,
        player_char: Player,
        enemy: Character | None = None,
        tile: MapTile | None = None,
        *,
        encounter: CombatEncounter | None = None,
    ) -> bool:
        """
        Initiate combat between player and enemy.

        Args:
            player_char: The player character
            enemy: The enemy to fight
            tile: The map tile where combat is occurring

        Returns:
            bool: True if player won, False if player fled/died
        """
        if tile is None:
            raise ValueError("CombatManager requires a combat tile.")
        runtime_encounter = getattr(
            enemy,
            "_runtime_combat_encounter",
            None,
        )
        if encounter is None and isinstance(runtime_encounter, CombatEncounter):
            encounter = runtime_encounter
            enemy = None
        if (enemy is None) == (encounter is None):
            raise ValueError("Supply exactly one of enemy or encounter.")
        if encounter is None:
            assert enemy is not None
            encounter = CombatEncounter.singleton(enemy)
        primary_enemy = encounter.primary_enemy

        # Store tile for loot drops
        self.current_tile = tile

        # Ensure dungeon background has a valid world dict for rendering
        if not self.player_world_dict and hasattr(player_char, "world_dict"):
            self.player_world_dict = player_char.world_dict

        # Create the core engine (handles initiative, actions, bookkeeping)
        self.engine = BattleEngine(
            player=player_char,
            tile=tile,
            game=self.game,
            logger=self.logger,
            encounter=encounter,
        )

        # Build display-friendly action list from the engine's available actions
        self.available_actions = self._build_display_actions()

        # Initialize combat state
        self.running = True
        self._last_combat_timeline = ()
        self._debug_auto_kill_hint_shown = False
        self.combat_view.reset_combat_log()
        has_sight = player_has_sight(player_char)
        hidden_names = [
            member.enemy.name
            for member in encounter.members
            if is_invisible_target(member.enemy) and not has_sight
        ]
        identity_setter = getattr(
            self.combat_view,
            "set_hidden_enemy_identities",
            None,
        )
        if callable(identity_setter):
            identity_setter(hidden_names)
        labels = ", ".join(member.display_label for member in encounter.members)
        self.combat_view.add_combat_message(f"Combat started with {labels}!")
        if getattr(player_char, "anti_magic_active", False):
            self.combat_view.add_combat_message(
                "An anti-magic field suppresses spells and standard skills in this encounter."
            )
        self._combat_background = self._capture_background()
        for member in encounter.members:
            self._prepare_enemy_combat_assets(member.enemy)

        # Show initial combat screen with brief transition delay (with animation updates)
        init_clock = pygame.time.Clock()
        for _ in range(COMBAT_START_TRANSITION_FRAMES):
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    pygame.quit()
                    sys.exit(0)
                self._handle_combat_log_scroll_event(event)
            self._render_combat_frame(
                self._selection_frame_player(player_char),
                primary_enemy,
                [],
                -1,
            )
            pygame.display.flip()
            init_clock.tick(60)

        # Determine who goes first (engine handles initiative)
        first, _ = self.engine.start_battle()
        if player_char.encumbered:
            self.combat_view.add_combat_message("You are ENCUMBERED! Enemy strikes first!")

        if first == player_char:
            self.combat_view.add_combat_message(f"{player_char.name} has the initiative!")
        else:
            self.combat_view.add_combat_message(f"{first.name} has the initiative!")
        if getattr(player_char, "anti_magic_active", False):
            self._show_anti_magic_warning()

        clock = pygame.time.Clock()
        fled = False
        singleton = len(encounter.members) == 1
        vesperion_false_final = singleton and self._is_vesperion_false_final_combat(
            player_char, primary_enemy
        )
        vesperion_enemy_turns = 0

        # Main combat loop
        while self.running and self.engine.battle_continues() and not player_char.in_town():
            if self.engine.is_player_turn():
                action_result = self._player_turn(
                    player_char,
                    self._focused_combat_enemy(primary_enemy),
                )
                if action_result == "flee":
                    fled = True
                    break
                elif not action_result:  # Closed combat
                    fled = True
                    break

                # Check if enemy died from special effects (e.g., self-healing that prevents death)
                if singleton and not primary_enemy.is_alive():
                    if vesperion_false_final:
                        return self._handle_vesperion_false_final(
                            player_char,
                            primary_enemy,
                        )
                    if not getattr(primary_enemy, "tamed_by_player", False):
                        self.combat_view.enemy_dies(primary_enemy)
                    break

                if vesperion_false_final and self._vesperion_false_final_hp_threshold_met(
                    primary_enemy
                ):
                    return self._handle_vesperion_false_final(
                        player_char,
                        primary_enemy,
                    )

                # Check for Mad Waitress form change (below 10% health)
                if singleton:
                    self._check_enemy_form_change(player_char, primary_enemy)
            else:
                current_enemy = self._current_enemy_actor(primary_enemy)
                # Double-check enemy is still alive before their turn
                if not current_enemy.is_alive():
                    self.combat_view.enemy_dies(current_enemy)
                    continue

                enemy_result = self._enemy_turn(player_char, current_enemy)
                if enemy_result == "flee":
                    fled = True
                    break

                if vesperion_false_final:
                    vesperion_enemy_turns += 1
                    if (
                        not player_char.is_alive()
                        or vesperion_enemy_turns >= VESPERION_FALSE_FINAL_ENEMY_TURNS
                        or self._vesperion_false_final_hp_threshold_met(primary_enemy)
                    ):
                        return self._handle_vesperion_false_final(
                            player_char,
                            primary_enemy,
                        )

                # Check if player died
                if not player_char.is_alive():
                    break

                # Prevent Mad Waitress from dying before her forced transition
                if singleton:
                    self._preserve_waitress_for_transition(primary_enemy)
                    self._check_enemy_form_change(player_char, primary_enemy)

                # Check if enemy died (e.g., from self-damaging skills like Widow's Wail)
                if singleton and not primary_enemy.is_alive():
                    if vesperion_false_final:
                        return self._handle_vesperion_false_final(
                            player_char,
                            primary_enemy,
                        )
                    self.combat_view.enemy_dies(primary_enemy)
                    break

            # Advance turn: post-turn processing + swap
            self._post_turn_processing(
                player_char,
                getattr(self.engine, "defender", primary_enemy),
            )
            if vesperion_false_final and (
                not player_char.is_alive()
                or not primary_enemy.is_alive()
                or self._vesperion_false_final_hp_threshold_met(primary_enemy)
            ):
                return self._handle_vesperion_false_final(
                    player_char,
                    primary_enemy,
                )
            self.engine.swap_turns()
            self._refresh_combat_background(
                player_char,
                self._focused_combat_enemy(primary_enemy),
            )

            # Refresh available actions for next turn
            self.available_actions = self._build_display_actions()

            # Small delay between turns (with animation updates)
            for _ in range(POST_TURN_DELAY_FRAMES):
                for event in pygame.event.get():
                    if event.type == pygame.QUIT:
                        pygame.quit()
                        sys.exit(0)
                    self._handle_combat_log_scroll_event(event)
                self._render_combat_frame(
                    player_char,
                    self._focused_combat_enemy(primary_enemy),
                    [],
                    -1,
                )
                pygame.display.flip()
                clock.tick(60)

        # Combat ended - show result
        return self._handle_combat_end(player_char, primary_enemy, fled)

    def _show_anti_magic_warning(self) -> None:
        """Present one blocking warning after combat art is ready, before turns begin."""
        from ..confirmation_popup import ConfirmationPopup

        popup = ConfirmationPopup(
            self.presenter,
            "ANTI-MAGIC FIELD ACTIVE\n\n"
            "Spells and standard skills are suppressed in this encounter.\n\n"
            "The field remains marked above the combat controls.",
            show_buttons=False,
        )
        popup.show(flush_events=True, require_key_release=True)

    def _prepare_enemy_combat_assets(self, enemy: Character) -> None:
        """Warm the current enemy's combat sprites before the first combat frame."""
        prepare = getattr(self.combat_view, "prepare_enemy_assets", None)
        if callable(prepare):
            try:
                prepare(enemy)
            except Exception:
                pass

    def _build_display_actions(self) -> list[str]:
        """Build the pygame display-friendly action list from the engine's available actions."""
        raw_actions = self.engine.available_actions
        action_names = []
        for action in raw_actions:
            if isinstance(action, dict):
                action_name = action.get("name", str(action))
            else:
                action_name = str(action)
            # Rename for display
            action_name = (
                action_name.replace("Cast Spell", "Spells")
                .replace("Use Skill", "Skills")
                .replace("Use Item", "Items")
            )
            action_names.append(action_name)

        is_player_turn = getattr(self.engine, "is_player_turn", None)
        if callable(is_player_turn) and is_player_turn():
            return self._build_foundational_display_actions(action_names)

        # Deduplicate while preserving order
        deduped = []
        seen = set()
        for name in action_names:
            normalized = name.strip()
            if not normalized or normalized in seen:
                continue
            seen.add(normalized)
            deduped.append(normalized)

        # Add Defend if not already present
        if "Defend" not in deduped and "Attack" in deduped:
            deduped.insert(1, "Defend")

        actor = getattr(self.engine, "attacker", None) or getattr(self.engine, "player", None)

        target = getattr(self.engine, "defender", None)
        if actor is not None:
            resolve_names = self._available_skill_names(actor, target, resolve=True)
            surge_names = {entry["name"] for entry in promotion_kits.RESOLVE_SURGES}
            has_resolve = any(
                name != "Hold the Line" and name not in surge_names for name in resolve_names
            )
            has_bursts = any(name in surge_names for name in resolve_names)
            has_standard_skills = bool(self._available_skill_names(actor, target, resolve=False))
            if has_resolve and "Resolve" not in deduped:
                skill_index = (
                    deduped.index("Skills")
                    if "Skills" in deduped
                    else deduped.index("Items") if "Items" in deduped else len(deduped)
                )
                deduped.insert(skill_index, "Resolve")
            if has_bursts and "Bursts" not in deduped:
                skill_index = (
                    deduped.index("Skills")
                    if "Skills" in deduped
                    else deduped.index("Items") if "Items" in deduped else len(deduped)
                )
                deduped.insert(skill_index, "Bursts")
            if (has_resolve or has_bursts) and not has_standard_skills and "Skills" in deduped:
                deduped.remove("Skills")

        if actor is not None and "Defend" in deduped:
            skills = getattr(actor, "spellbook", {}).get("Skills", {})
            defensive_release = skills.get("Defensive Release")
            hold_the_line = skills.get("Hold the Line")
            class_name = getattr(getattr(actor, "cls", None), "name", "")
            if class_name == "Knight Enchanter" and defensive_release is not None:
                defend_index = deduped.index("Defend")
                deduped[defend_index] = "Defensive Release"
            elif class_name in {"Sentinel", "Stalwart Defender"} and hold_the_line is not None:
                defend_index = deduped.index("Defend")
                deduped.pop(defend_index)
                if self._skill_available_for_selection(
                    actor,
                    hold_the_line,
                    target,
                ):
                    deduped.insert(defend_index, "Hold the Line")

        # Add Pickup Weapon if the active actor is disarmed
        is_disarmed = getattr(actor, "is_disarmed", None)
        if (
            actor is not None
            and callable(is_disarmed)
            and is_disarmed()
            and "Pickup Weapon" not in deduped
        ):
            idx = 2 if "Defend" in deduped else 1
            deduped.insert(idx, "Pickup Weapon")

        return deduped

    def _build_foundational_display_actions(self, action_names: list[str]) -> list[str]:
        """Project core shortcuts and fixed commands without changing combat rules."""
        snapshot = combat_interface_snapshot(self.engine, self.engine.player)
        self._display_action_presentations: dict[str, CombatActionPresentation] = {}
        labels: list[str] = []
        for slot in snapshot.shortcuts:
            label = slot.display_label
            labels.append(label)
            if slot.action is not None:
                self._display_action_presentations[label] = slot.action

        available = set(action_names)
        for command in SYSTEM_COMMANDS:
            if command == "All Actions" or command in available:
                labels.append(command)
            else:
                labels.append(f"{command} — Not available this turn.")

        fixed_or_catalog = {*SYSTEM_COMMANDS, "Spells", "Skills"}
        labels.extend(name for name in action_names if name not in fixed_or_catalog)
        return labels

    def _refresh_display_actions(self) -> None:
        """Refresh the visible combat action list when turn-start effects change availability."""
        try:
            self.available_actions = self._build_display_actions()
        except AttributeError:
            return

    def _post_turn_processing(self, player_char: Player, enemy: Character) -> None:
        """Handle engine post-turn + display any messages."""
        visual_before = (getattr(enemy, "name", None), getattr(enemy, "picture", None))
        post = self.engine.post_turn()
        self._announce_new_resolutions(post)
        visual_after = (getattr(enemy, "name", None), getattr(enemy, "picture", None))
        added_message = False
        for msg in post.messages:
            if msg:
                for line in msg.strip().split("\n"):
                    if line.strip():
                        self.combat_view.add_combat_message(line)
                        added_message = True
        if added_message:
            self._flush_result_frame(player_char, enemy)
        if visual_after != visual_before:
            self._play_enemy_visual_transition(player_char, enemy, visual_before, visual_after)

    def _announce_new_resolutions(self, result) -> None:
        """Log and animate each terminal member attached to one engine result."""
        encounter = getattr(self.engine, "encounter", None)
        if encounter is None:
            return
        labels = {
            "defeated": "defeated",
            "mercy": "spared",
            "tamed": "tamed",
            "ejected": "ejected",
            "escaped": "escaped",
        }
        for record in getattr(result, "new_resolutions", ()):
            try:
                member = encounter.member_by_id(record.combatant_id)
            except KeyError:
                continue
            resolution = labels.get(record.resolution.value, record.resolution.value)
            self.combat_view.add_combat_message(f"{member.display_label} {resolution}.")
            self.combat_view.enemy_dies(member.enemy)

    def _flush_result_frame(self, player_char, enemy) -> None:
        """Draw result log text before any impact animation or turn transition starts."""
        self._render_combat_frame(player_char, enemy, [], -1)
        pygame.display.flip()
        try:
            pygame.event.pump()
        except pygame.error:
            pass
        pygame.time.Clock().tick(60)

    def _play_enemy_visual_transition(
        self,
        player_char: Player,
        enemy: Character,
        visual_before: tuple[object, object],
        visual_after: tuple[object, object],
    ) -> None:
        """Briefly alternate old/new enemy visuals when a form changes."""
        before_picture = visual_before[1]
        after_picture = visual_after[1]
        if not before_picture or not after_picture or before_picture == after_picture:
            self.combat_view.reload_enemy_sprite(enemy)
            return

        original_offset = getattr(self.combat_view, "enemy_visual_offset", (0, 0))
        frames = [
            (before_picture, -8),
            (after_picture, 8),
            (before_picture, -6),
            (after_picture, 6),
            (before_picture, -3),
            (after_picture, 0),
        ]
        clock = pygame.time.Clock()
        try:
            for picture, offset_x in frames:
                enemy.picture = picture
                self.combat_view.reload_enemy_sprite(enemy)
                self.combat_view.enemy_visual_offset = (offset_x, 0)
                for _ in range(5):
                    for event in pygame.event.get():
                        if event.type == pygame.QUIT:
                            pygame.quit()
                            sys.exit(0)
                        self._handle_combat_log_scroll_event(event)
                    self._render_combat_frame(player_char, enemy, [], -1)
                    pygame.display.flip()
                    clock.tick(60)
        finally:
            enemy.picture = after_picture
            self.combat_view.enemy_visual_offset = original_offset
            self.combat_view.reload_enemy_sprite(enemy)

    def _player_turn(self, player_char, enemy):
        """
        Handle player's turn with action selection.

        Returns:
            str/bool: "flee" if fled, False if cancelled, True if action taken
        """
        if self._debug_mode_enabled() and not self._debug_auto_kill_hint_shown:
            self.combat_view.add_combat_message("Debug: Press K to defeat the focused enemy.")
            self._debug_auto_kill_hint_shown = True

        # Pre-turn: process status effects and check if player can act
        pre = self.engine.pre_turn()
        if pre.effects_text:
            for line in pre.effects_text.strip().split("\n"):
                if line.strip():
                    self.combat_view.add_combat_message(line)
            self._flush_result_frame(player_char, enemy)

        # If the player died from effects (poison, DOT, bleed), end turn immediately
        if pre.died_from_effects:
            return True

        if not pre.can_act:
            self.combat_view.add_combat_message(pre.inactive_reason.strip())
            self._flush_result_frame(player_char, enemy)
            return True  # Turn skipped

        self._refresh_display_actions()

        # Check for forced actions (berserk, charging, jump)
        forced = self.engine.get_forced_action()
        if forced:
            if forced.action == "Cancelled":
                for line in forced.cancel_message.strip().split("\n"):
                    if line.strip():
                        self.combat_view.add_combat_message(line)
                self._flush_result_frame(player_char, enemy)
                return True

            if forced.action == "Attack":
                actor_name = getattr(
                    getattr(self.engine, "attacker", None), "name", player_char.name
                )
                self.combat_view.add_combat_message(
                    f"{actor_name} is BERSERKED and attacks wildly!"
                )

            # Execute the forced action via engine
            enemy_hp_before = enemy.health.current
            result = self.engine.execute_action(forced.action, choice=forced.choice)
            self._announce_new_resolutions(result)

            for line in result.message.strip().split("\n"):
                if line.strip():
                    self.combat_view.add_combat_message(line)

            self._flush_result_frame(player_char, enemy)

            # Damage flash for attack/skill hits
            damage_to_enemy = max(0, enemy_hp_before - enemy.health.current)
            if damage_to_enemy > 0:
                self.combat_view.enemy_take_damage(enemy)
                floating_damage = self._recorded_floating_damage(
                    result,
                    damage_to_enemy,
                )
                self._show_combat_damage_effect(
                    "enemy",
                    forced.action,
                    forced.choice,
                    result.message,
                    floating_damage,
                )
                self._flush_result_frame(player_char, enemy)

            self._preserve_waitress_for_transition(enemy)

            if result.fled:
                return "flee"
            return True

        # Get available actions
        actions = self.available_actions
        shortcut_count = 6 if len(actions) > 6 else 0
        selected_action = shortcut_count if len(actions) > shortcut_count else -1
        input_armed = self._clear_pending_input()

        action_taken = False

        while not action_taken:
            # Render combat scene
            self._render_combat_frame(player_char, enemy, actions, selected_action)

            # Handle input
            input_armed = release_guard_allows_input(True, input_armed)
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    pygame.quit()
                    sys.exit(0)

                input_armed = self._arm_guarded_input(event, input_armed)
                if event.type == pygame.KEYDOWN and not input_armed:
                    continue

                if self._handle_combat_log_scroll_event(event):
                    continue

                controller_key = self._controller_key(event)
                if event.type == pygame.KEYDOWN or controller_key is not None:
                    key = event.key if event.type == pygame.KEYDOWN else controller_key

                    if key == pygame.K_q:
                        self.engine.cycle_focus(-1)
                        enemy = self.engine._focused_enemy()
                    elif key == pygame.K_e:
                        self.engine.cycle_focus(1)
                        enemy = self.engine._focused_enemy()
                    elif key == pygame.K_k and self._debug_mode_enabled():
                        action_result = self._execute_action("Auto Kill", player_char, enemy)
                        if action_result is not None:
                            action_taken = True
                    elif key == pygame.K_UP or key == pygame.K_w:
                        continue
                    elif key == pygame.K_DOWN or key == pygame.K_s:
                        continue
                    elif key == pygame.K_LEFT or key == pygame.K_a:
                        if selected_action > shortcut_count:
                            selected_action -= 1
                    elif key == pygame.K_RIGHT or key == pygame.K_d:
                        if shortcut_count <= selected_action < len(actions) - 1:
                            selected_action += 1
                    elif key == pygame.K_y:
                        action_result = self._execute_action("All Actions", player_char, enemy)
                        if action_result == "flee":
                            return "flee"
                        elif action_result is not None:
                            action_taken = True
                    elif key == pygame.K_x:
                        self._show_combat_resource_details(player_char)
                    elif key == pygame.K_RETURN or key == pygame.K_SPACE:
                        if selected_action < shortcut_count:
                            continue
                        action_result = self._execute_action(
                            actions[selected_action], player_char, enemy
                        )
                        if action_result == "flee":
                            return "flee"
                        elif action_result == "continue_turn":
                            self._refresh_display_actions()
                            actions = self.available_actions
                            selected_action = 0
                            input_armed = self._clear_pending_input()
                            break
                        elif action_result is not None:
                            action_taken = True
                    elif key in [
                        pygame.K_1,
                        pygame.K_2,
                        pygame.K_3,
                        pygame.K_4,
                        pygame.K_5,
                        pygame.K_6,
                    ]:
                        # Number keys for quick selection
                        num = key - pygame.K_1
                        if num < len(actions):
                            action_result = self._execute_action(actions[num], player_char, enemy)
                            if action_result == "flee":
                                return "flee"
                            elif action_result == "continue_turn":
                                self._refresh_display_actions()
                                actions = self.available_actions
                                selected_action = 0
                                input_armed = self._clear_pending_input()
                                break
                            elif action_result is not None:
                                action_taken = True
                elif event.type in (
                    pygame.MOUSEMOTION,
                    pygame.MOUSEBUTTONDOWN,
                    pygame.FINGERDOWN,
                    pygame.FINGERUP,
                ):
                    position = mouse_position(event)
                    finger_event = event.type in (pygame.FINGERDOWN, pygame.FINGERUP)
                    if finger_event:
                        position = (
                            int(getattr(event, "x", 0.0) * self.screen.get_width()),
                            int(getattr(event, "y", 0.0) * self.screen.get_height()),
                        )
                    activated = is_left_click(event) or event.type == pygame.FINGERUP
                    if activated and input_armed:
                        focus_control_at = getattr(self.combat_view, "enemy_focus_control_at", None)
                        direction = (
                            focus_control_at(position) if callable(focus_control_at) else None
                        )
                        if direction is not None:
                            self.engine.cycle_focus(direction)
                            enemy = self.engine._focused_enemy()
                            continue
                        card_at = getattr(self.combat_view, "enemy_card_at", None)
                        target_id = card_at(position) if callable(card_at) else None
                        if target_id is not None:
                            try:
                                self.engine.set_focus_target(target_id)
                                enemy = self.engine._focused_enemy()
                            except (KeyError, ValueError):
                                pass
                            continue
                    hovered = hit_index(self._combat_action_rects(actions), position)
                    if hovered is None:
                        continue
                    if hovered >= shortcut_count:
                        selected_action = hovered
                    if not activated or not input_armed:
                        continue
                    action_result = self._execute_action(
                        actions[hovered],
                        player_char,
                        enemy,
                    )
                    if action_result == "flee":
                        return "flee"
                    elif action_result == "continue_turn":
                        self._refresh_display_actions()
                        actions = self.available_actions
                        selected_action = 0
                        input_armed = self._clear_pending_input()
                        break
                    elif action_result is not None:
                        action_taken = True

            pygame.display.flip()

        # Companion / familiar turn
        companion_msg = self.engine.companion_turn()
        if companion_msg:
            for line in companion_msg.strip().split("\n"):
                if line.strip():
                    self.combat_view.add_combat_message(line)

        return True

    def _check_enemy_form_change(self, player_char, enemy):
        """
        Check if Mad Waitress should change form/state when health drops below 10%.
        When the transition happens, she becomes sane, changes sprite back to waitress.png,
        and attacks herself once before dying.
        """
        # Only applies to Mad Waitress (NightHag2)
        if not isinstance(enemy, enemies.NightHag2):
            return

        # Check if already transitioned
        if getattr(enemy, "_form_changed", False):
            return

        # Check health threshold (below 10%)
        health_pct = enemy.health.current / enemy.health.max
        if health_pct >= 0.1:
            return

        # Perform transition
        enemy._form_changed = True

        # Collect transition messages to display in popup
        transition_messages = [
            "The Mad Waitress momentarily comes to her senses...",
            "This visible form change reveals the waitress beneath the hag's shape.",
            "Her eyes clear. She sees what she has become.",
            "",
            "Recognizing the horror of her actions,",
            "she takes her own life, finally finding peace with Joffrey...",
        ]

        # Change name and sprite back to normal Waitress
        enemy.name = "Waitress"
        self.combat_view.reload_enemy_sprite(enemy)

        # Waitress takes her own life - deal lethal damage
        damage = enemy.health.current
        enemy.health.current = 0

        # Show popup with the wail/transition narrative
        from ..confirmation_popup import ConfirmationPopup

        popup_text = "\n".join(transition_messages)
        popup = ConfirmationPopup(self.presenter, popup_text, show_buttons=False)
        popup.show(flush_events=True, require_key_release=True)

        # Show combat log messages for the self-attack
        self.combat_view.add_combat_message(
            "The Mad Waitress visibly changes form without changing her true identity."
        )
        self.combat_view.add_combat_message(f"{enemy.name} turns her weapon on herself in despair!")
        self.combat_view.add_combat_message(f"{enemy.name} takes {damage} damage from the attack!")

        # Enemy is now dead
        self.combat_view.enemy_dies(enemy)

    def _preserve_waitress_for_transition(self, enemy) -> None:
        """Prevent killing the Mad Waitress before her transition triggers."""
        if not isinstance(enemy, enemies.NightHag2):
            return
        if getattr(enemy, "_form_changed", False):
            return
        if enemy.health.current <= 0:
            enemy.health.current = 1

    def _select_all_action(self, player_char, enemy) -> CombatActionPresentation | None:
        """Select any learned active action while retaining unavailable explanations."""
        entries = combat_interface_snapshot(self.engine, player_char).all_actions
        if not entries:
            self.combat_view.add_combat_message("No active learned actions.")
            return None
        selected = 0
        scroll_offset = 0
        input_armed = self._clear_pending_input()
        frame_player = self._selection_frame_player(player_char)
        while True:
            self._render_combat_frame(frame_player, enemy, [], -1)
            options = [entry.display_label for entry in entries]
            descriptions = [entry.description for entry in entries]
            self._render_described_selection_menu(
                "All Actions",
                options,
                selected,
                scroll_offset,
                descriptions,
            )
            pygame.display.flip()
            input_armed = release_guard_allows_input(True, input_armed)
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    pygame.quit()
                    sys.exit(0)
                input_armed = self._arm_guarded_input(event, input_armed)
                if event.type == pygame.KEYDOWN and not input_armed:
                    continue
                controller_key = self._controller_key(event)
                if event.type == pygame.KEYDOWN or controller_key is not None:
                    key = event.key if event.type == pygame.KEYDOWN else controller_key
                    if key in (pygame.K_ESCAPE, pygame.K_BACKSPACE):
                        return None
                    if key in (pygame.K_UP, pygame.K_w):
                        selected = (selected - 1) % len(entries)
                    elif key in (pygame.K_DOWN, pygame.K_s):
                        selected = (selected + 1) % len(entries)
                    elif key == pygame.K_PAGEUP:
                        selected = max(0, selected - 10)
                    elif key == pygame.K_PAGEDOWN:
                        selected = min(len(entries) - 1, selected + 10)
                    elif key in (pygame.K_RETURN, pygame.K_SPACE):
                        return entries[selected]
                    scroll_offset = self._scroll_offset_for_selection(selected, scroll_offset)
                elif event.type in (pygame.MOUSEMOTION, pygame.MOUSEBUTTONDOWN):
                    selected, scroll_offset, confirmed = self._selection_menu_mouse_update(
                        event,
                        options,
                        selected,
                        scroll_offset,
                        input_armed,
                    )
                    if confirmed:
                        return entries[selected]
            clock = getattr(self.presenter, "clock", None)
            if clock is not None:
                clock.tick(60)

    def _execute_action(self, action, player_char, enemy):
        """Execute a player action by delegating to the engine."""
        actor = getattr(self.engine, "attacker", None) or player_char
        if isinstance(action, str):
            slot_number, separator, slot_label = action.partition(". ")
            if (
                separator
                and slot_number.isdigit()
                and slot_label in {"Empty", "Unavailable assignment"}
            ):
                return None
        if isinstance(action, str) and action.endswith(" — Not available this turn."):
            self.combat_view.add_combat_message("That system command is not available this turn.")
            return None
        presentation = (
            action
            if isinstance(action, CombatActionPresentation)
            else getattr(self, "_display_action_presentations", {}).get(action)
        )
        direct_choice = None
        if presentation is not None:
            if not presentation.enabled:
                self.combat_view.add_combat_message(
                    presentation.availability.reason or "That action is unavailable."
                )
                return None
            action = presentation.engine_action
            direct_choice = presentation.choice
        if action == "All Actions":
            selected = self._select_all_action(player_char, enemy)
            return (
                self._execute_action(selected, player_char, enemy) if selected is not None else None
            )
        if action == "Auto Kill":
            if not self._debug_mode_enabled():
                self.combat_view.add_combat_message("Auto Kill is only available in debug mode.")
                return None
            enemy_hp_before = enemy.health.current
            enemy.health.current = 0
            damage_to_enemy = max(0, enemy_hp_before - enemy.health.current)
            self.combat_view.add_combat_message(f"Debug: {enemy.name} defeated.")
            self.combat_view.enemy_take_damage(enemy)
            self._show_combat_damage_effect("enemy", "Attack", None, "", damage_to_enemy)
            return "action_taken"

        # Map display name back to engine name
        engine_action = _DISPLAY_TO_ENGINE.get(action, action)
        support_mode = action == "Support"

        # Sub-menu actions need a selection UI first
        choice = direct_choice

        if support_mode:
            support = self._select_summoner_support_action(player_char, enemy)
            if not support:
                return None
            action, engine_action, choice = support
            actor = player_char

        if action == "Items" and choice is None:
            selected_item = self._select_item(actor, enemy, support_only=support_mode)
            if not selected_item:
                return None  # Cancelled
            choice = selected_item.name

        elif action == "Spells":
            if actor.abilities_suppressed():
                reason = (
                    "the anti-magic field"
                    if getattr(actor, "anti_magic_active", False)
                    else "silence"
                )
                self.combat_view.add_combat_message(
                    f"{actor.name} cannot cast spells because of {reason}!"
                )
                return None
            selected_spell = self._select_spell(actor, enemy)
            if not selected_spell:
                return None
            spell = actor.spellbook.get("Spells", {}).get(selected_spell)
            calling_category = getattr(spell, "category", "")
            class_name = str(getattr(getattr(actor, "cls", None), "name", ""))
            if (
                calling_category
                and class_name == "Thaumaturgist"
                and not self._choose_calling_xenid(
                    actor,
                    enemy,
                    calling_category,
                )
            ):
                return None
            choice = selected_spell

        elif action == "Runic Boost":
            if player_char.abilities_suppressed():
                reason = (
                    "the anti-magic field"
                    if getattr(player_char, "anti_magic_active", False)
                    else "silence"
                )
                self.combat_view.add_combat_message(
                    f"{player_char.name} cannot cast spells because of {reason}!"
                )
                return None
            selected_spell = self._select_runic_boost_spell(player_char, enemy)
            if not selected_spell:
                return None
            choice = selected_spell

        elif action == "Steal As Well":
            selected_spell = self._select_steal_as_well_spell(player_char, enemy)
            if not selected_spell:
                return None
            choice = selected_spell

        elif action == "Companion":
            if player_char.abilities_suppressed():
                reason = (
                    "the anti-magic field"
                    if getattr(player_char, "anti_magic_active", False)
                    else "silence"
                )
                self.combat_view.add_combat_message(
                    f"{player_char.name} cannot command their companion because of {reason}!"
                )
                return None
            selected_command = self._select_companion_command(player_char, enemy)
            if not selected_command:
                return None
            choice = selected_command

        elif action == "Repertoire":
            selected_song = self._select_repertoire_song(player_char, enemy)
            if not selected_song:
                return None
            choice = selected_song

        elif action == "Skills":
            allowed_skill_names = None
            if support_mode and self.engine is not None:
                allowed_skill_names = self.engine.summoner_support_skill_names()
            if allowed_skill_names is None:
                selected_skill = self._select_skill(actor, enemy)
            else:
                selected_skill = self._select_skill(actor, enemy, allowed_names=allowed_skill_names)
            if not selected_skill:
                return None
            choice = selected_skill
            if selected_skill == "Weapon Swap":
                skill_obj = actor.spellbook.get("Skills", {}).get(selected_skill)
                selected_weapon = self._select_combat_weapon(actor, enemy, skill_obj)
                if selected_weapon is None:
                    return None
                skill_obj.selected_weapon = selected_weapon
            if selected_skill == "Call Contract":
                intent = self._select_contract_intent(player_char, enemy)
                if not intent:
                    return None
                skill_obj = actor.spellbook.get("Skills", {}).get("Call Contract")
                if skill_obj:
                    skill_obj.pending_intent = intent

        elif action == "Resolve":
            selected_skill = self._select_resolve_ability(actor, enemy)
            if not selected_skill:
                return None
            choice = selected_skill

        elif action == "Bursts":
            selected_skill = self._select_resolve_ability(
                actor,
                enemy,
                bursts=True,
            )
            if not selected_skill:
                return None
            choice = selected_skill

        elif action == "Summon":
            if player_char.abilities_suppressed():
                reason = (
                    "the anti-magic field"
                    if getattr(player_char, "anti_magic_active", False)
                    else "silence"
                )
                self.combat_view.add_combat_message(
                    f"{player_char.name} cannot summon because of {reason}!"
                )
                return None
            selected_summon = self._select_summon(player_char, enemy)
            if not selected_summon:
                return None
            choice = selected_summon

        elif action == "Transform":
            forms = tuple(getattr(player_char, "available_transform_forms", lambda: ())())
            if len(forms) > 1:
                choice = self._select_transform_form(player_char, enemy, forms)
                if not choice:
                    return None
            elif forms:
                choice = forms[0]

        elif action == "Pickup Weapon":
            is_disarmed = getattr(actor, "is_disarmed", None)
            if not callable(is_disarmed) or not is_disarmed():
                self.combat_view.add_combat_message("Not disarmed!")
                return None

        if choice is not None:
            self._render_combat_frame(self._selection_frame_player(player_char), enemy, [], -1)
            pygame.display.flip()

        # Record HP before execution for damage flash
        enemy_hp_before = enemy.health.current
        encounter = getattr(self.engine, "encounter", None)
        enemy_hp_by_id = (
            {member.combatant_id: member.enemy.health.current for member in encounter.members}
            if encounter is not None
            else {}
        )
        player_hp_before = player_char.health.current
        actor_hp_before = getattr(getattr(actor, "health", None), "current", 0)
        enemy_name_before = enemy.name

        # Delegate to engine (handles attack rolls, spell casts, skill use, etc.)
        slot_cb = None
        if action in {"Skills", "Resolve", "Bursts"} and choice:
            skill_obj = actor.spellbook.get("Skills", {}).get(choice)
            if skill_obj and skill_obj.name == "Slot Machine":

                def slot_cb(_u, _t):
                    return self._show_slot_machine_reveal(actor, enemy)

        if support_mode:
            result = self.engine.execute_summoner_support_action(
                engine_action, choice=choice, slot_machine_callback=slot_cb
            )
        elif encounter is not None and hasattr(
            self.engine,
            "target_scope_for_action",
        ):
            scope = self.engine.target_scope_for_action(engine_action, choice)
            target_ids = (self.engine.focus_target_id,) if scope == TargetScope.SINGLE_ENEMY else ()
            result = self.engine.execute_intent(
                ActionIntent(action_id=engine_action, choice=choice, target_ids=target_ids),
                slot_machine_callback=slot_cb,
            )
        else:
            result = self.engine.execute_action(
                engine_action,
                choice=choice,
                slot_machine_callback=slot_cb,
            )
        self._announce_new_resolutions(result)

        damage_to_enemy = max(0, enemy_hp_before - enemy.health.current)
        favored_msg = ability_mechanics.consume_favored_enemy_bonus_message(player_char)
        if damage_to_enemy > 0:
            for line in favored_msg.strip().split("\n"):
                if line.strip():
                    self.combat_view.add_combat_message(line)

        # Display result messages
        for line in result.message.strip().split("\n"):
            if line.strip():
                self.combat_view.add_combat_message(line)

        action_fled = result.fled or bool(getattr(self.engine, "flee", False))
        if engine_action == "Use Skill" and choice == "Smoke Screen" and action_fled:
            self._play_smoke_screen_visual(player_char, enemy, "player")
        else:
            self._flush_result_frame(player_char, enemy)

        # Show damage flash for enemy damage
        showed_damage_effect = False
        tamed_result = bool(getattr(enemy, "tamed_by_player", False))
        damaged_members = []
        for member in encounter.members if encounter is not None else ():
            before = enemy_hp_by_id.get(
                member.combatant_id,
                member.enemy.health.current,
            )
            damage = max(0, before - member.enemy.health.current)
            if damage > 0 and not getattr(member.enemy, "tamed_by_player", False):
                damaged_members.append((member, damage))
        if damaged_members:
            for member, damage in damaged_members:
                self.combat_view.enemy_take_damage(member.enemy)
                floating_damage = self._recorded_floating_damage(
                    result,
                    damage,
                    target_id=member.combatant_id,
                )
                self._show_combat_damage_effect(
                    member.combatant_id,
                    action,
                    choice,
                    result.message,
                    floating_damage,
                )
            showed_damage_effect = True
        elif damage_to_enemy > 0 and not tamed_result:
            self.combat_view.enemy_take_damage(enemy)
            floating_damage = self._recorded_floating_damage(
                result,
                damage_to_enemy,
            )
            self._show_combat_damage_effect(
                "enemy",
                action,
                choice,
                result.message,
                floating_damage,
            )
            showed_damage_effect = True
        else:
            if not tamed_result:
                self._show_combat_heal_text("enemy", max(0, enemy.health.current - enemy_hp_before))

        # Show damage flash for player damage (from reflected/self-damage skills)
        active_hp_after = getattr(getattr(actor, "health", None), "current", actor_hp_before)
        damage_to_player = max(0, player_hp_before - player_char.health.current)
        if actor is not player_char:
            damage_to_player = max(0, actor_hp_before - active_hp_after)
        if damage_to_player > 0:
            self._show_combat_damage_effect(
                "player", action, choice, result.message, damage_to_player
            )
            showed_damage_effect = True
        else:
            heal_amount = max(0, player_char.health.current - player_hp_before)
            if actor is not player_char:
                heal_amount = max(0, active_hp_after - actor_hp_before)
            self._show_combat_heal_text("player", heal_amount)

        if showed_damage_effect:
            self._flush_result_frame(player_char, enemy)

        # Check if enemy shapeshifted (name changed)
        if enemy.name != enemy_name_before:
            self.combat_view.reload_enemy_sprite(enemy)

        self._preserve_waitress_for_transition(enemy)

        if action_fled:
            return "flee"
        if getattr(result, "summon_started", False):
            self._refresh_display_actions()
            return "continue_turn"
        return "action_taken"
