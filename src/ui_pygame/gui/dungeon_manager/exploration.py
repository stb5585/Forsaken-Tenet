"""Exploration behavior for the dungeon manager package."""

import sys
import traceback

import pygame

from src.core import map_tiles, quest_progress
from src.core.abilities import detects_encounter
from src.core.player import DIRECTIONS

from ..input_guards import (
    prepare_guarded_input,
    release_guard_allows_input,
    update_input_armed_from_event,
)


class DungeonExplorationMixin:
    def _get_tile_intro(self):
        """Get intro text for current tile and tile ahead."""
        messages = []

        # Check current tile (for stairs, shops, enemies you're standing on)
        current_tile = self.get_current_tile()
        if current_tile:
            intro_text = current_tile.intro_text(self.game).strip("\n")
            tile_type = type(current_tile).__name__

            if "StairsUp" in tile_type:
                messages.append("You see stairs leading upward.")
            elif "LadderUp" in tile_type:
                messages.append("A sturdy ladder leads upward.")
            elif "StairsDown" in tile_type:
                messages.append("You see stairs descending into darkness.")
            elif "LadderDown" in tile_type:
                messages.append("A sturdy ladder descends into darkness.")
            elif "SecretShop" in tile_type:
                messages.append("You've found a secret shop! (Press O to enter)")
            elif "UltimateArmorShop" in tile_type:
                messages.append("You've found a mysterious forge! (Press O to enter)")
            elif "WarpPoint" in tile_type:
                if getattr(self.player_char, "warp_point", False):
                    messages.append("A warp point shimmers before you! (Press O to use)")
                else:
                    messages.append("An inactive warp point hums faintly. (Press O to inspect)")
            elif "UndergroundSpring" in tile_type:
                messages.append("An underground spring bubbles nearby. (Press O to interact)")
            elif "AntiMagicSwitch" in tile_type:
                messages.append(
                    "A humming terminal waits here. The anti-magic field may be tied to it."
                )
            elif "UnobtainiumRoom" in tile_type:
                if not (hasattr(current_tile, "looted") and not current_tile.looted):
                    messages.append("You happen upon a strange metal! (Press O to take)")
            elif "DeadBody" in tile_type:
                messages.append("The body of a fallen soldier lies here.")
            elif "FinalBlocker" in tile_type:
                if not self.player_char.has_relics():
                    messages.append("An invisible force blocks your path northward.")
                else:
                    messages.append("The way to the final chamber has opened!")
            elif "FinalRoom" in tile_type:
                messages.append("The final chamber awaits. (Press O to proceed)")
            elif "LiminalGuide" in tile_type:
                messages.append("The Hooded Figure waits here. (Press O to speak)")
            elif "LiminalSeventhSeat" in tile_type:
                messages.append("The empty Seventh Seat waits here. (Press O to inspect)")
            elif "LiminalAcolyte" in tile_type:
                messages.append("The Acolyte kneels in silence. (Press O to speak)")
            elif "LiminalReflection" in tile_type:
                messages.append("A mirror-dark threshold waits here. (Press O to face it)")
            elif getattr(current_tile, "liminal_gate_event", None):
                guardian_name = getattr(current_tile, "guardian_name", "Guardian")
                messages.append(f"The gate of {guardian_name} is sealed. (Press O to inspect)")
            elif "LiminalExitBlocker" in tile_type:
                messages.append("A torn threshold refuses to open. (Press O to inspect)")
            elif "Boss" in tile_type or "Lair" in tile_type:
                if self._resolve_tile_enemy(current_tile):
                    messages.append("You sense a powerful presence nearby...")
                else:
                    if intro_text:
                        messages.append(intro_text)
            else:
                enemy = self._resolve_tile_enemy(current_tile)
                if enemy:
                    messages.append(f"A {enemy.name} blocks your path!")
            gathering_message = map_tiles.gathering_hint(
                self.player_char,
                current_tile,
                current_tile=True,
            )
            if gathering_message:
                messages.append(gathering_message)

        # Check tile ahead (for interactive objects like chests, doors, relics)
        direction = self.player_char.facing
        dx, dy = DIRECTIONS[direction]["move"]
        ahead_x = self.player_char.location_x + dx
        ahead_y = self.player_char.location_y + dy
        ahead_z = self.player_char.location_z

        ahead_tile = self.player_char.world_dict.get((ahead_x, ahead_y, ahead_z))
        if ahead_tile:
            tile_type = type(ahead_tile).__name__

            if "Chest" in tile_type:
                if hasattr(ahead_tile, "open") and ahead_tile.open:
                    messages.append("There's an open chest ahead.")
                elif hasattr(ahead_tile, "locked") and ahead_tile.locked:
                    messages.append("There's a locked chest ahead! (Press O to unlock)")
                else:
                    messages.append("There's a chest ahead! (Press O to open)")
            elif tile_type == "OreVaultDoor":
                # Hidden door: appears as wall unless detected or open
                # Show identification message once when the player has means to detect it
                is_open = getattr(ahead_tile, "open", False)
                is_detected = getattr(ahead_tile, "detected", False)
                has_cryptic_key = "Cryptic Key" in self.player_char.inventory
                has_keen_eye = "Keen Eye" in self.player_char.spellbook.get("Skills", [])

                if is_open:
                    messages.append("The secret vault door stands open ahead.")
                elif not is_detected and (has_cryptic_key or has_keen_eye):
                    # Mark as detected and inform the player
                    ahead_tile.detected = True
                    if has_cryptic_key:
                        messages.append(
                            "The Cryptic Key begins to glow; faint seams reveal a hidden door ahead!"
                        )
                    else:
                        messages.append(
                            f"{self.player_char.name}'s keen eye spots a hidden door ahead!"
                        )
                    # View changed (door will render as detected)
                    self._mark_view_dirty()
            elif "Door" in tile_type:
                if hasattr(ahead_tile, "open") and ahead_tile.open:
                    messages.append("An open doorway ahead.")
                elif hasattr(ahead_tile, "locked") and ahead_tile.locked:
                    messages.append("A locked door blocks your path. (Press O to unlock)")
                else:
                    messages.append("An open doorway ahead.")
            elif "Relic" in tile_type:
                if hasattr(ahead_tile, "read") and ahead_tile.read:
                    messages.append("An empty altar stands ahead.")
                else:
                    messages.append("A glowing relic rests on a altar ahead! (Press O to collect)")
            elif "Boulder" in tile_type:
                if hasattr(ahead_tile, "read") and ahead_tile.read:
                    messages.append("A broken boulder ahead.")
                else:
                    messages.append("An oddly placed boulder ahead. (Press O to examine)")
            elif "UnobtainiumRoom" in tile_type:
                is_looted = bool(getattr(ahead_tile, "visited", False))
                if is_looted:
                    messages.append("The ground ahead is already cleared.")
                else:
                    messages.append("You see Unobtainium on the ground ahead! (Press O to take)")
            elif "GoldenChaliceRoom" in tile_type:
                if map_tiles.chalice_altar_visible(self.player_char):
                    if getattr(ahead_tile, "read", False):
                        messages.append("An empty chalice pedestal stands ahead.")
                    else:
                        messages.append(
                            "A golden chalice rests on a pedestal ahead! (Press O to take)"
                        )
            gathering_message = map_tiles.gathering_hint(
                self.player_char,
                ahead_tile,
                current_tile=False,
            )
            if gathering_message:
                messages.append(gathering_message)

        return messages if messages else None

    def _check_tile_effects(self):
        """Check for tile effects like encounters, traps, etc."""
        current_tile = self.get_current_tile()
        if not current_tile:
            return

        location_message = quest_progress.record_location(
            self.player_char,
            (self.player_char.location_x, self.player_char.location_y, self.player_char.location_z),
        )
        if location_message:
            self.add_message(location_message.rstrip())

        # Golden Chalice quest progression hooks
        try:
            map_tiles.update_chalice_location(self.game)
            map_tiles.handle_chalice_adventurer(self.game)
        except Exception:
            pass

        # Check for stairs - automatically use them when stepping on them
        tile_type = type(current_tile).__name__
        if "StairsUp" in tile_type:
            self.use_stairs_up()
            return  # Don't check for other effects when using stairs
        elif "StairsDown" in tile_type:
            self.use_stairs_down()
            return  # Don't check for other effects when using stairs
        elif "FinalRoom" in tile_type:
            # Automatically trigger final room conversation when stepping on the tile
            self._interact_final_room(current_tile)
            return  # Don't check for other effects after final room interaction
        elif "AntiMagicSwitch" in tile_type:
            self._interact_anti_magic_switch(current_tile)

        current_enemy = self._resolve_tile_enemy(current_tile)
        is_boss_encounter = current_enemy is not None and (
            "Boss" in tile_type or "Lair" in tile_type
        )
        if is_boss_encounter and not getattr(current_tile, "read", False):
            self._show_boss_intro_dialogue(current_tile, current_enemy)

        # Display special event text BEFORE tile effects and combat
        if hasattr(current_tile, "special_text") and not is_boss_encounter:
            try:
                special = current_tile.special_text(self.game)
                special_text = str(special).strip() if special else ""
                if special_text:
                    from ..confirmation_popup import ConfirmationPopup

                    popup = ConfirmationPopup(
                        self.presenter,
                        special_text,
                        show_buttons=False,
                    )
                    popup.show(
                        background_draw_func=self._draw_cached_popup_background,
                        flush_events=True,
                        require_key_release=True,
                        min_display_ms=300,
                    )
            except Exception:
                pass

        # Apply tile-defined effects (original game behavior)
        # This enables effects like FirePath damage on entry.
        hp_before = getattr(self.player_char.health, "current", None)
        try:
            if "UndergroundSpring" not in tile_type:
                from ..confirmation_popup import ConfirmationPopup

                try:
                    current_tile.modify_player(self.game, popup_class=ConfirmationPopup)
                except TypeError:
                    current_tile.modify_player(self.game)
        except AttributeError:
            pass
        except Exception:
            pass
        else:
            hp_after = getattr(self.player_char.health, "current", None)
            self._sync_dungeon_music()
            if (
                "FirePath" in tile_type
                and hp_before is not None
                and hp_after is not None
                and hp_after < hp_before
            ):
                damage = hp_before - hp_after
                self.add_message(f"The heat sears you for {damage} damage!")
                # Brief red flash when the floor burns the player
                if hasattr(self.renderer, "trigger_damage_flash"):
                    self.renderer.trigger_damage_flash()
                self.ui_dirty = True
                self.view_dirty = True

        cambion_messages = map_tiles.pop_cambion_messages(self.player_char)
        for message in cambion_messages:
            self.add_message(message)
        if "Trap" in tile_type and cambion_messages:
            from ..confirmation_popup import ConfirmationPopup

            popup = ConfirmationPopup(
                self.presenter,
                "\n".join(cambion_messages),
                show_buttons=False,
            )
            popup.show(
                background_draw_func=self._draw_cached_popup_background,
                min_display_ms=300,
            )

        # Check if tile effect teleported player to town (e.g., "Bring Him Home" quest)
        if self.player_char.in_town():
            self.add_message("You've been teleported back to town!")
            try:
                from ..confirmation_popup import ConfirmationPopup

                popup = ConfirmationPopup(
                    self.presenter, "You've been teleported back to town!", show_buttons=False
                )
                popup.show(flush_events=True, require_key_release=True, min_display_ms=300)
            except Exception:
                pass
            self._show_town_entry_loading_screen()
            self.running = False  # Exit dungeon mode
            return

        # Check for enemy encounter after enter_combat has had a chance to spawn one
        if hasattr(current_tile, "enemy") and current_tile.enemy:
            enemy = self._resolve_tile_enemy(current_tile)

            if hasattr(enemy, "is_alive") and not enemy.is_alive():
                current_tile.enemy = None
                return
            if hasattr(enemy, "health") and getattr(enemy.health, "current", 1) <= 0:
                current_tile.enemy = None
                return

            if getattr(current_tile, "detectable_random_encounter", False) and detects_encounter(
                self.player_char, enemy
            ):
                from ..confirmation_popup import ConfirmationPopup

                fight = ConfirmationPopup(
                    self.presenter,
                    f"Detect {enemy.enemy_typ} reveals {enemy.name} ahead. Fight it?",
                ).show()
                if not fight:
                    current_tile.enemy = None
                    current_tile.detectable_random_encounter = False
                    self.player_char.state = "normal"
                    self.add_message(f"You avoid the {enemy.name}.")
                    return

            self.add_message(f"You've encountered a {enemy.name}!")

            # Set player state to fight BEFORE calling start_combat
            # This ensures available_actions returns combat actions
            self.player_char.state = "fight"

            # Update combat manager with current world state for rendering
            self.combat_manager.player_world_dict = self.player_char.world_dict

            # Initiate combat
            self._refresh_cached_frame()
            combat_won = self.combat_manager.start_combat(self.player_char, enemy, current_tile)

            if self.player_char.in_town():
                self._detach_dungeon_background_provider()
                self.player_char.state = "normal"
                self.running = False
                return

            if combat_won:
                # Enemy defeated - clear from tile
                current_tile.enemy = None
                current_tile.detectable_random_encounter = False
                self.add_message("You emerge victorious!")
                self._handle_defeated_jester_boss(current_tile)
                if "MerzhinBossRoom" in type(current_tile).__name__:
                    self.add_message("Merzhin falls and the Realm of Cambion collapses around you.")
                    self.player_char.exit_realm_of_cambion()
                    self._sync_dungeon_music()
                    self._mark_view_dirty()
            elif not self.player_char.is_alive():
                # Player died - return to town or exit funhouse
                if self.player_char.location_z == 7:
                    # In funhouse - exit instead of going to town
                    self.add_message("You were defeated... The funhouse spits you back out.")
                    self.player_char.exit_funhouse()
                    self._sync_dungeon_music()
                elif self.player_char.in_realm_of_cambion():
                    self.add_message(
                        "You were defeated... The Realm of Cambion hurls you back to the spring."
                    )
                    self.player_char.exit_realm_of_cambion()
                    self._sync_dungeon_music()
                    self._mark_view_dirty()
                else:
                    self.add_message("You were defeated...")
                    self._detach_dungeon_background_provider()
                    self._cached_view = None
                    self._cached_frame = None
                    self._mark_view_dirty()
                    death_message = self.player_char.death()
                    for line in str(death_message or "").splitlines():
                        if line.strip():
                            self.add_message(line.strip())
                self.player_char.state = "normal"
                # End dungeon exploration loop (return control to town menu)
                self.running = False
            else:
                # Player fled - enemy moves away/disappears
                current_tile.enemy = None
                self.add_message("You escaped from combat.")

        # Check for warning tiles (difficulty increase)
        if "WarningTile" in tile_type and not hasattr(current_tile, "_warning_shown"):
            self.add_message(
                "*** WARNING: Enemies beyond this point increase in difficulty. Plan accordingly. ***"
            )
            current_tile._warning_shown = True

    def explore_dungeon(self):
        """
        Main dungeon exploration loop.
        Returns when player exits dungeon (returns to town, quits, etc.)
        """
        # A prior death or dungeon exit may have left a cached frame from another location.
        self._cached_view = None
        self._cached_frame = None
        self._mark_view_dirty()
        self._sync_dungeon_music()

        # Always show a loading screen on entry. If we're in town coordinates, use a descending message.
        if hasattr(self.player_char, "in_town") and callable(self.player_char.in_town):
            msg = (
                "Descending further into the dungeon..."
                if self.player_char.in_town()
                else "Entering the dungeon..."
            )
        else:
            msg = "Entering the dungeon..."
        self._show_dungeon_loading_screen(msg, duration=1.25)
        self._suppress_navigation_input(ms=350)

        # Initial message
        current_tile = self.get_current_tile()
        if current_tile:
            current_tile.visited = True
            current_tile.adjacent_visited(self.player_char)

        self.add_message("You enter the dungeon...")
        self.add_message(f"Facing: {self.player_char.facing}")

        # Show controls
        if getattr(self.game, "debug_mode", False):
            self.add_message(
                "Controls: Arrows/WASD=Move/Turn, O=Interact, U=Stairs Up, J=Stairs Down, M=Map, ESC=Menu, L=Debug Level Up"
            )
        else:
            self.add_message(
                "Controls: Arrows/WASD=Move/Turn, O=Interact, U=Stairs Up, J=Stairs Down, M=Map, ESC=Menu"
            )

        clock = pygame.time.Clock()
        self.running = True

        # Initialize animation timer (torch flicker, subtle post-effects, etc.)
        self._next_anim_tick = pygame.time.get_ticks() + self._anim_interval_ms

        # Initialize cry timer for floor 2 quest
        self._last_cry_time = 0
        self._cry_interval = 8000  # Check every 8 seconds

        while self.running:
            if self.player_char.in_town():
                self.running = False
                break

            # Handle events
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.running = False
                    self.player_char.quit = True

                elif event.type == pygame.MOUSEWHEEL:
                    if event.y > 0:
                        self.scroll_message_log(-1)
                    elif event.y < 0:
                        self.scroll_message_log(1)

                elif event.type == pygame.MOUSEBUTTONDOWN and getattr(event, "button", None) == 1:
                    minimap_rect = getattr(self.hud, "last_minimap_rect", None)
                    if minimap_rect is not None and minimap_rect.collidepoint(
                        getattr(event, "pos", (-1, -1))
                    ):
                        self._show_enlarged_minimap()

                elif event.type == pygame.KEYDOWN:
                    self._handle_keypress(event.key)

                elif event.type == pygame.KEYUP:
                    self._release_navigation_input(event.key)

            if self.player_char.in_town():
                self.running = False
                break

            # Periodic animation refresh (even if the player doesn't move)
            now = pygame.time.get_ticks()
            if now >= self._next_anim_tick:
                self._mark_view_dirty()
                self._next_anim_tick = now + self._anim_interval_ms

            # Check for random cries on floor 2 during "Something to Cry About" quest
            if now >= self._last_cry_time + self._cry_interval:
                self._check_random_cry()
                self._last_cry_time = now

            # Keep UI refreshing while a damage flash is active so the fade animates
            if getattr(self.renderer, "_damage_flash_active", False):
                self.ui_dirty = True

            # Only redraw when something changed.
            if self.view_dirty or self.ui_dirty or self._cached_view is None:
                self._render()
                pygame.display.flip()

            # Keep event loop responsive; redraws are conditional.
            clock.tick(60)

        if self.player_char.in_town() or self.player_char.quit:
            self.reset_message_log()

        return not self.player_char.quit  # Return True if player didn't quit game

    def _handle_keypress(self, key):
        """Handle keyboard input for dungeon navigation."""
        if self._navigation_input_suppressed(key):
            return

        # Movement and turning
        if key in (pygame.K_w, pygame.K_UP):
            self.move_forward()

        elif key in (pygame.K_a, pygame.K_LEFT):
            self.turn_left()

        elif key in (pygame.K_d, pygame.K_RIGHT):
            self.turn_right()

        elif key in (pygame.K_s, pygame.K_DOWN):
            self.turn_around()

        # Stairs
        elif key == pygame.K_u:
            self.use_stairs_up()

        elif key == pygame.K_j:
            self.use_stairs_down()

        # Interact
        elif key == pygame.K_o:
            self.interact()

        elif key == pygame.K_PAGEUP:
            self.scroll_message_log(-1)

        elif key == pygame.K_PAGEDOWN:
            self.scroll_message_log(1)

        elif key == pygame.K_m:
            self._show_enlarged_minimap()

        # Character menu
        elif key == pygame.K_c:
            # Open character screen (same as town)
            while True:
                choice = self._get_character_screen().navigate(self.player_char)
                if choice == "Exit Menu" or choice is None:
                    break
                else:
                    # Placeholder until inventory/equipment/etc screens exist
                    self.presenter.show_message("This menu is not yet implemented in the dungeon.")

        # Debug level-up shortcut
        elif key == pygame.K_l and getattr(self.game, "debug_mode", False):
            self.game.debug_level_up()

        # Escape menu
        elif key == pygame.K_ESCAPE:
            self._show_menu()

    def _show_enlarged_minimap(self):
        """Show the enlarged minimap modal over the current dungeon view."""
        clock = pygame.time.Clock()
        panel_rect = self.hud.enlarged_map_rect()
        while True:
            self._render()
            panel_rect = self.hud.render_enlarged_minimap_modal(self.player_char)
            pygame.display.flip()

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.running = False
                    self.player_char.quit = True
                    return
                if event.type == pygame.KEYDOWN and event.key in (pygame.K_m, pygame.K_ESCAPE):
                    self.ui_dirty = True
                    return
                if event.type == pygame.MOUSEBUTTONDOWN and getattr(event, "button", None) == 1:
                    if not panel_rect.collidepoint(getattr(event, "pos", (-1, -1))):
                        self.ui_dirty = True
                        return
            clock.tick(30)

    def _show_menu(self):
        """Show in-dungeon menu."""
        menu_options = [
            "Resume Exploration",
            "Character Menu",
        ]
        if getattr(self.game, "debug_mode", False):
            menu_options.append("Save Game")
        menu_options.append("Quit Game (No Save)")

        choice = self._popup_menu(
            "Dungeon Menu",
            menu_options,
            flush_events=True,
            require_key_release=True,
        )

        # Handle None (menu closed without selection)
        if choice is None or choice == 0:  # Resume
            self.add_message("Resuming exploration...")
            return

        elif choice == 1:  # Character Menu
            while True:
                char_choice = self._get_character_screen().navigate(self.player_char)
                if char_choice == "Exit Menu" or char_choice is None:
                    break
                else:
                    self.presenter.show_message("This menu is not yet implemented in the dungeon.")

        elif menu_options[choice] == "Save Game":
            from ..confirmation_popup import ConfirmationPopup

            popup = ConfirmationPopup(self.presenter, "Save your progress?")
            if popup.show(
                background_draw_func=self._dungeon_dialog_background,
                flush_events=True,
                require_key_release=True,
            ):
                self.game.save_game()
                self.add_message("Game saved!")

        elif menu_options[choice] == "Quit Game (No Save)":
            from ..confirmation_popup import ConfirmationPopup

            popup = ConfirmationPopup(self.presenter, "Quit without saving? Progress will be lost.")
            if popup.show(
                background_draw_func=self._dungeon_dialog_background,
                flush_events=True,
                require_key_release=True,
            ):
                self.add_message("Exiting game...")
                self.running = False
                self.player_char.quit = True

    def _popup_menu(
        self,
        title: str,
        options: list[str],
        flush_events: bool = False,
        require_key_release: bool = False,
    ):
        """Lightweight modal popup menu drawn over the current view.

        Returns the selected index or None if canceled.
        """
        selected = 0
        clock = self.presenter.clock
        screen = self.presenter.screen

        # Snapshot current frame as background
        background = screen.copy()
        input_armed = prepare_guarded_input(
            flush_events=flush_events,
            require_key_release=require_key_release,
        )

        # Layout
        panel_width = self.presenter.width // 2
        panel_height = self.presenter.height // 2
        panel_x = (self.presenter.width - panel_width) // 2
        panel_y = (self.presenter.height - panel_height) // 2
        panel_rect = pygame.Rect(panel_x, panel_y, panel_width, panel_height)

        def draw():
            # Draw background dimmed
            screen.blit(background, (0, 0))
            overlay = pygame.Surface((self.presenter.width, self.presenter.height), pygame.SRCALPHA)
            overlay.fill((0, 0, 0, 180))
            screen.blit(overlay, (0, 0))

            # Panel
            pygame.draw.rect(screen, (20, 20, 30), panel_rect)
            pygame.draw.rect(screen, (200, 200, 200), panel_rect, 3)

            # Title
            title_surf = self.presenter.title_font.render(title, True, (218, 165, 32))
            title_rect = title_surf.get_rect(center=(panel_rect.centerx, panel_rect.top + 40))
            screen.blit(title_surf, title_rect)

            # Options
            y = title_rect.bottom + 20
            for idx, opt in enumerate(options):
                color = (218, 165, 32) if idx == selected else (255, 255, 255)
                surf = self.presenter.large_font.render(opt, True, color)
                rect = surf.get_rect(center=(panel_rect.centerx, y))
                screen.blit(surf, rect)
                y += 40

            # Instructions
            instr = "UP/DOWN: Navigate  ENTER: Select  ESC: Cancel"
            instr_surf = self.presenter.small_font.render(instr, True, (180, 180, 180))
            instr_rect = instr_surf.get_rect(center=(panel_rect.centerx, panel_rect.bottom - 30))
            screen.blit(instr_surf, instr_rect)

            pygame.display.flip()

        while True:
            draw()
            input_armed = release_guard_allows_input(require_key_release, input_armed)
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    pygame.quit()
                    sys.exit()
                input_armed = update_input_armed_from_event(event, require_key_release, input_armed)
                if event.type == pygame.KEYDOWN:
                    if not input_armed:
                        continue
                    if event.key in (pygame.K_UP, pygame.K_w):
                        selected = (selected - 1) % len(options)
                    elif event.key in (pygame.K_DOWN, pygame.K_s):
                        selected = (selected + 1) % len(options)
                    elif event.key in (pygame.K_RETURN, pygame.K_SPACE):
                        return selected
                    elif event.key == pygame.K_ESCAPE:
                        return None
            clock.tick(30)

    def _render(self):
        """Render the complete dungeon view."""
        # Ensure we have a cached view surface for the current resolution.
        screen = self.presenter.screen
        if self._cached_view is None or self._cached_view.get_size() != screen.get_size():
            self._cached_view = pygame.Surface(screen.get_size()).convert()
            self._mark_view_dirty()

        # --- 3D view (expensive) ---
        if self.view_dirty:
            screen.fill((0, 0, 0))
            try:
                self.renderer.render_dungeon_view(self.player_char, self.player_char.world_dict)

                # Cache the freshly-rendered 3D view *before* overlay UI is drawn.
                self._cached_view.blit(screen, (0, 0))
                self._render_error_logged = False
            except Exception as e:
                # Do not spam tracebacks every frame.
                if not self._render_error_logged:
                    print(f"Render error: {e}")
                    traceback.print_exc()
                    self._render_error_logged = True

                # Fall back to the last known-good view if available.
                screen.blit(self._cached_view, (0, 0))
        else:
            # Re-use the cached 3D view.
            screen.blit(self._cached_view, (0, 0))

        # --- UI overlays (cheap) ---
        try:
            self.renderer.render_message_area(
                self.messages,
                scroll_offset=self.message_scroll_offset,
                lines_per_page=self.message_lines_per_page,
            )
        except Exception as e:
            print(f"Message render error: {e}")

        try:
            self.hud.render_hud(self.player_char)
        except Exception as e:
            if not self._render_error_logged:
                print(f"HUD render error: {e}")
                traceback.print_exc()
                self._render_error_logged = True

        try:
            self.renderer.render_damage_flash()
        except Exception as e:
            if not self._render_error_logged:
                print(f"Damage flash render error: {e}")
                traceback.print_exc()
                self._render_error_logged = True

        self._cached_frame = screen.copy()

        # Clear dirty flags after a frame attempt.
        self.view_dirty = False
        self.ui_dirty = False
