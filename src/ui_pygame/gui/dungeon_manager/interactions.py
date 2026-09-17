"""Interactions behavior for the dungeon manager package."""

import random

import pygame

from src.core import (
    enemies,
    items,
    map_tiles,
)
from src.core.player import DIRECTIONS
from src.paths import PYGAME_ASSETS_DIR

from .core import get_npc_art_manager, get_special_events
from .helpers import relic_discovery_text


class DungeonInteractionMixin:
    def interact(self):
        """Interact with the tile ahead (or current tile for some types)."""
        # For interactive objects like chests/doors/relics, check tile ahead
        # For things you stand on (stairs, shops), check current tile

        self._mark_view_dirty()

        # First check tile ahead
        direction = self.player_char.facing
        dx, dy = DIRECTIONS[direction]["move"]
        ahead_x = self.player_char.location_x + dx
        ahead_y = self.player_char.location_y + dy
        ahead_z = self.player_char.location_z

        ahead_tile = self.player_char.world_dict.get((ahead_x, ahead_y, ahead_z))

        if ahead_tile:
            tile_type = type(ahead_tile).__name__

            # Interact with tile ahead for these types
            if "Chest" in tile_type:
                self._interact_chest(ahead_tile, tile_type)
                return
            elif "Door" in tile_type:
                # Special check for OreVaultDoor - only allow interaction if detected or open
                if tile_type == "OreVaultDoor":
                    has_cryptic_key = "Cryptic Key" in self.player_char.inventory
                    has_keen_eye = "Keen Eye" in self.player_char.spellbook.get("Skills", [])
                    is_open = getattr(ahead_tile, "open", False)
                    if not (has_cryptic_key or has_keen_eye or is_open):
                        # Door not detected - treat like a wall
                        self.add_message("There's nothing to interact with here.")
                        return
                self._interact_door(ahead_tile)
                return
            elif "Relic" in tile_type:
                self._interact_relic(ahead_tile)
                return
            elif "Boulder" in tile_type:
                self._interact_boulder(ahead_tile)
                return
            elif "UnobtainiumRoom" in tile_type:
                self._interact_unobtainium_room(ahead_tile)
                return
            elif "GoldenChaliceRoom" in tile_type:
                self._interact_golden_chalice_room(ahead_tile)
                return

        # Check current tile for things you stand on
        current_tile = self.get_current_tile()
        if not current_tile:
            self.add_message("There's nothing to interact with here.")
            return

        tile_type = type(current_tile).__name__

        # Check for adjacent SecretShop tiles (since SecretShop is non-enterable)
        adjacent_secret_shop = None
        if "SecretShop" not in tile_type:
            # Check all adjacent tiles for secret shops
            dx, dy = DIRECTIONS[self.player_char.facing]["move"]
            adjacent_pos = (
                self.player_char.location_x + dx,
                self.player_char.location_y + dy,
                self.player_char.location_z,
            )
            adjacent_tile = self.player_char.world_dict.get(adjacent_pos)
            if adjacent_tile and "SecretShop" in type(adjacent_tile).__name__:
                adjacent_secret_shop = adjacent_tile

        if "SecretShop" in tile_type or adjacent_secret_shop:
            # Show special message on first discovery
            shop_tile = current_tile if "SecretShop" in tile_type else adjacent_secret_shop
            if not hasattr(shop_tile, "read") or not shop_tile.read:
                self.presenter.show_message(
                    "You've discovered a secret shop!\n\n"
                    "A mysterious merchant appears from the shadows...\n\n"
                    '"Welcome, traveler. I have rare goods for sale."',
                    image_path=str(
                        PYGAME_ASSETS_DIR / "dungeon_tiles" / "special_tiles" / "secret_shop.png"
                    ),
                )
                shop_tile.read = True

            self.add_message("Entering secret shop...")
            self.shop_manager.visit_secret_shop()
        elif "UltimateArmorShop" in tile_type:
            self.add_message("Approaching the forge...")
            self.ultimate_armor_shop.visit_shop(self.player_char, current_tile)
        elif "WarpPoint" in tile_type:
            self._handle_warp_point(current_tile)
        elif "UndergroundSpring" in tile_type:
            self._interact_underground_spring(current_tile)
        elif "AntiMagicSwitch" in tile_type:
            self._interact_anti_magic_switch(current_tile)
        elif "UnobtainiumRoom" in tile_type:
            self._interact_unobtainium_room(current_tile)
        elif "DeadBody" in tile_type:
            self._interact_dead_body(current_tile)
        elif "FinalRoom" in tile_type:
            self._interact_final_room(current_tile)
        elif "LiminalGuide" in tile_type:
            self._interact_liminal_guide(current_tile)
        elif "LiminalSeventhSeat" in tile_type:
            self._interact_liminal_seventh_seat(current_tile)
        elif "LiminalAcolyte" in tile_type:
            self._interact_liminal_acolyte(current_tile)
        elif "LiminalReflection" in tile_type:
            self._interact_liminal_reflection(current_tile)
        elif getattr(current_tile, "liminal_gate_event", None):
            self._interact_liminal_guardian_gate(current_tile)
        elif "LiminalExitBlocker" in tile_type:
            self._interact_liminal_exit_blocker(current_tile)
        elif "IncubusLair" in tile_type:
            self._interact_incubus_lair(current_tile)
        elif "GoldenChaliceRoom" in tile_type:
            self._interact_golden_chalice_room(current_tile)
        elif map_tiles.definition_for_tile(current_tile) is not None:
            self._interact_gathering_node(current_tile)
        else:
            self.add_message("There's nothing to interact with here.")

    def _interact_gathering_node(self, tile) -> None:
        """Harvest a recognized resource node through the standard loot presentation."""
        if not map_tiles.can_identify_gathering_node(self.player_char, tile):
            self.add_message(
                "You lack the knowledge to identify or harvest this unfamiliar growth."
            )
            return
        item = map_tiles.harvest_gathering_node(self.player_char, tile)
        if item is None:
            self.add_message("This resource has already been harvested.")
            return
        self._mark_view_dirty()
        self._refresh_cached_frame()
        self.loot_popup.show_loot(
            item,
            "Foraged Resource",
            background_draw_func=self._draw_cached_popup_background,
            flush_events=True,
            require_key_release=True,
        )
        self.add_message(f"Gathered {item.name}.")

    def _interact_chest(self, chest_tile, tile_type):
        """Handle chest interaction."""
        # Check if already opened
        if hasattr(chest_tile, "open") and chest_tile.open:
            self.add_message("This chest has already been opened.")
            return

        # Check if locked
        if hasattr(chest_tile, "locked") and chest_tile.locked:
            # Try to unlock
            if "Master Key" in self.player_char.special_inventory:
                chest_tile.locked = False
                self.add_message("You unlock the chest with the Master Key!")
            elif "Lockpick" in self.player_char.spellbook.get(
                "Skills", []
            ) and items.has_lockpick_kit(self.player_char):
                chest_tile.locked = False
                self.add_message("You skillfully pick the lock!")
                _used, kit_message = items.use_lockpick_kit(self.player_char)
                self.add_message(kit_message)
            elif "Key" in self.player_char.inventory:
                # Ask if they want to use a key with visual popup
                self._refresh_cached_frame()
                use_key = self.loot_popup.show_unlock_prompt(
                    "chest",
                    background_draw_func=self._draw_cached_popup_background,
                    flush_events=True,
                    require_key_release=True,
                )
                if use_key:
                    chest_tile.locked = False
                    self.player_char.modify_inventory(
                        self.player_char.inventory["Key"][0], subtract=True
                    )
                    self.add_message("You unlock the chest with a Key!")
                else:
                    self.add_message("The chest remains locked.")
                    return
            else:
                self.add_message(
                    "The chest is locked! You need a Key or Lockpick Kit with the Lockpick skill."
                )
                return

        # Check for Mimic (FunhouseMimicChest always spawns one; other chests have random chance)
        locked = int("Locked" in tile_type)
        plus = int("ChestRoom2" in tile_type)
        is_funhouse_mimic = "FunhouseMimicChest" in tile_type
        mimic_outcome = getattr(chest_tile, "mimic_outcome", None)
        if not is_funhouse_mimic and mimic_outcome is None:
            # Compatibility for hand-built tiles and pre-persistence saves.
            mimic_outcome = map_tiles.ordinary_chest_spawns_mimic(
                self.player_char, locked=locked, plus=plus
            )
            chest_tile.mimic_outcome = mimic_outcome
        if is_funhouse_mimic or mimic_outcome:
            from src.core import enemies

            # For funhouse mimic chest, spawn level 4 mimic; for other chests use normal scaling
            mimic_level = 4 if is_funhouse_mimic else (self.player_char.location_z + locked + plus)
            enemy = enemies.Mimic(mimic_level, player_level=self.player_char.player_level())
            enemy.anti_magic_active = self.player_char.anti_magic_active
            chest_tile.enemy = enemy
            self.add_message("There is a Mimic in the chest!")
            # Start combat with the Mimic
            self.player_char.state = "fight"
            self._refresh_cached_frame()
            victory = self.combat_manager.start_combat(self.player_char, enemy, chest_tile)
            if not getattr(enemy, "is_alive", lambda: True)():
                chest_tile.enemy = None
            if not victory or not self.player_char.is_alive():
                return  # Player fled or died, don't open chest

        # Open the chest
        chest_tile.open = True

        # Generate loot if not already generated
        if not hasattr(chest_tile, "loot") or chest_tile.loot is None:
            chest_tile.generate_loot()

        # Show loot with visual popup
        if chest_tile.loot:
            loot_item = chest_tile.loot()
            # Show the loot popup first
            chest_name = "Locked Chest" if "Locked" in tile_type else "Chest"
            self._refresh_cached_frame()
            self.loot_popup.show_loot(
                loot_item,
                chest_name,
                background_draw_func=self._draw_cached_popup_background,
                flush_events=True,
                require_key_release=True,
            )
            # Then add to inventory
            self.player_char.modify_inventory(loot_item)
            self.add_message(f"Obtained {loot_item.name}!")

            # Funhouse Mimic Chest also drops a Jester Token
            if is_funhouse_mimic:
                from src.core import items as items_module

                token = items_module.JesterToken()
                self._refresh_cached_frame()
                self.loot_popup.show_loot(
                    token,
                    "Mimic Reward",
                    background_draw_func=self._draw_cached_popup_background,
                    flush_events=True,
                    require_key_release=True,
                )
                self.player_char.modify_inventory(token, rare=True)
                self.add_message(f"A shimmering {token.name} manifests as the Mimic dissolves!")
        else:
            self._refresh_cached_frame()
            self.loot_popup.show_loot(
                [],
                "Empty Chest",
                background_draw_func=self._draw_cached_popup_background,
                flush_events=True,
                require_key_release=True,
            )

    def _interact_door(self, door_tile):
        """Handle door interaction."""
        if not hasattr(door_tile, "locked"):
            self.add_message("This door cannot be interacted with.")
            return

        if not door_tile.locked:
            self.add_message("The door is already unlocked.")
            return

        # Special handling for OreVaultDoor
        door_type = type(door_tile).__name__
        if door_type == "OreVaultDoor":
            # Try to unlock with Cryptic Key first
            if "Cryptic Key" in self.player_char.inventory:
                door_tile.locked = False
                door_tile.open = True
                door_tile.enter = True
                door_tile.detected = True
                self.player_char.modify_inventory(
                    self.player_char.inventory["Cryptic Key"][0], subtract=True
                )
                self.add_message("The Cryptic Key turns smoothly in the hidden lock.")
                self.add_message("The door swings open, revealing the vault beyond!")
                self._play_sfx("open_door")
                self._mark_view_dirty()
                return
            # Master Key works if player has Keen Eye
            elif "Master Key" in self.player_char.special_inventory:
                if "Keen Eye" in self.player_char.spellbook.get("Skills", []):
                    door_tile.locked = False
                    door_tile.open = True
                    door_tile.enter = True
                    door_tile.detected = True
                    self.add_message("You unlock and open the hidden door with the Master Key!")
                    self._play_sfx("open_door")
                    self._mark_view_dirty()
                    return
            # Master Lockpick works if player has Keen Eye
            elif "Master Lockpick" in self.player_char.spellbook.get(
                "Skills", []
            ) and items.has_lockpick_kit(self.player_char):
                if "Keen Eye" in self.player_char.spellbook.get("Skills", []):
                    door_tile.locked = False
                    door_tile.open = True
                    door_tile.enter = True
                    door_tile.detected = True
                    _used, kit_message = items.use_lockpick_kit(self.player_char, master=True)
                    self.add_message("You skillfully pick the hidden door's lock!")
                    self.add_message(kit_message)
                    self._play_sfx("open_door")
                    self._mark_view_dirty()
                    return
            # If we get here, they can't unlock it
            self.add_message(
                "You sense something is hidden here, but you lack the means to open it."
            )
            return

        # Regular door handling
        # Try to unlock
        if "Master Key" in self.player_char.special_inventory:
            door_tile.locked = False
            door_tile.open = True
            door_tile.blocked = None
            self.add_message("You unlock and open the door with the Master Key!")
            self._play_sfx("open_door")
        elif "Master Lockpick" in self.player_char.spellbook.get(
            "Skills", []
        ) and items.has_lockpick_kit(self.player_char):
            door_tile.locked = False
            door_tile.open = True
            door_tile.blocked = None
            _used, kit_message = items.use_lockpick_kit(self.player_char, master=True)
            self.add_message("You skillfully pick the lock and open the door!")
            self.add_message(kit_message)
            self._play_sfx("open_door")
        elif "Old Key" in self.player_char.inventory:
            self._refresh_cached_frame()
            use_key = self.loot_popup.show_unlock_prompt(
                "door",
                background_draw_func=self._draw_cached_popup_background,
                flush_events=True,
                require_key_release=True,
            )
            if use_key:
                door_tile.locked = False
                door_tile.open = True
                door_tile.blocked = None
                self.player_char.modify_inventory(
                    self.player_char.inventory["Old Key"][0], subtract=True
                )
                self.add_message("You unlock and open the door with an Old Key!")
                self._play_sfx("open_door")
            else:
                self.add_message("The door remains locked.")
        else:
            self.add_message(
                "The door is locked! You need an Old Key or Lockpick Kit with the Master Lockpick skill."
            )

    def _interact_relic(self, relic_tile):
        """Handle relic room interaction."""
        if hasattr(relic_tile, "read") and relic_tile.read:
            self.add_message("You already collected the relic from this room.")
            return

        # Get the appropriate relic for this level
        z = self.player_char.location_z
        relics = [
            items.Relic1(),
            items.Relic2(),
            items.Relic3(),
            items.Relic4(),
            items.Relic5(),
            items.Relic6(),
        ]

        if 1 <= z <= 6:
            relic = relics[z - 1]
            discovery_message = relic_discovery_text(relic)
            popup_shown = False
            try:
                if self.game is not None:
                    self.game.special_event("Relic Room", message=discovery_message)
                    popup_shown = True
            except Exception:
                pass
            if not popup_shown:
                self.add_message(discovery_message)
            self.player_char.modify_inventory(relic, rare=True, quest=True)
            relic_tile.read = True

            # Restore HP and MP
            self.player_char.health.current = self.player_char.health.max
            self.player_char.mana.current = self.player_char.mana.max
            quest_message = self.player_char.quests()
            if quest_message:
                for line in quest_message.strip().splitlines():
                    self.add_message(line)
            self.add_message("Your health and mana have been fully restored!")
        else:
            self.add_message("The pedestal is empty.")

    def _handle_warp_point(self, warp_tile):
        """Handle warp point interaction - return to town."""
        if not getattr(self.player_char, "warp_point", False):
            self.add_message("The warp point is inactive. It looks like it requires authorization.")
            return

        choice = self._show_dungeon_choice(
            "You've found a warp point!\n\nDo you want to return to town?",
            ["Yes", "No"],
        )

        if choice == 0:  # Yes
            self.add_message("Warping to town...")
            self._show_town_entry_loading_screen()

            # Move player to town using proper method
            self.player_char.to_town()

            # Exit dungeon exploration - return to town menu
            self.running = False
        else:
            self.add_message("You remain in the dungeon.")
            warp_tile.warped = False

    def _interact_boulder(self, boulder_tile):
        """Handle boulder interaction - can find Excaliper sword."""
        communion = map_tiles.nature_communion_text(self.player_char, "Earth")
        if communion:
            self.add_message(communion.strip())

        progress = map_tiles.get_chalice_progress(self.player_char)
        map_ready = bool(progress and progress.get("Hooded") and not progress.get("Map"))
        has_excaliper = "Excaliper" in self.player_char.special_inventory

        # Backfill old saves/states where Excaliper was already obtained but tile wasn't marked read.
        if has_excaliper and hasattr(boulder_tile, "read") and not boulder_tile.read:
            boulder_tile.read = True

        if hasattr(boulder_tile, "read") and boulder_tile.read and not map_ready:
            self.add_message("Just a broken boulder where you found that sword.")
            return

        # Check if player has drunk from the spring
        spring_tile = self.player_char.world_dict.get((4, 9, 3))
        if spring_tile and hasattr(spring_tile, "drink") and spring_tile.drink:
            if not getattr(boulder_tile, "read", False):
                self.game.special_event("Boulder")
                self.add_message("You find a magnificent sword embedded in the boulder!")
                self.add_message("You obtained: Excaliper!")
                self.player_char.modify_inventory(items.Excaliper(), rare=True)
                boulder_tile.read = True
        else:
            self.add_message("An oddly placed boulder. Nothing seems special about it.")

        if map_ready and getattr(boulder_tile, "read", False):
            self.game.special_event("Chalice Map")
            self.add_message("You find a weathered map tucked inside a crevice.")
            self.player_char.modify_inventory(items.ChaliceMap(), rare=True, quest=True)
            progress["Map"] = True
            map_tiles.sync_chalice_map_description(self.player_char)
            chalice_quest = self.player_char.quest_dict["Side"]["The Holy Grail of Quests"]
            chalice_quest["Help Text"] = (
                "Bring the map to the Sergeant at the barracks for help deciphering it."
            )

    def _interact_underground_spring(self, spring_tile):
        """Handle underground spring interaction."""
        from ..confirmation_popup import ConfirmationPopup

        nimue_image_path = get_npc_art_manager().get_image_path("Nimue")
        popup = ConfirmationPopup(
            self.presenter,
            "You see a refreshing underground spring.\n\nDo you want to drink from it?",
            show_buttons=True,
        )
        if not popup.show(
            background_draw_func=self._dungeon_dialog_background,
            flush_events=True,
            require_key_release=True,
            min_display_ms=300,
        ):
            return
        self._play_sfx("underground_spring")
        communion = map_tiles.nature_communion_text(self.player_char, "Water")
        if communion:
            self.add_message(communion.strip())

        # Check for Naivete quest
        if "Naivete" in self.player_char.quest_dict.get("Side", {}):
            if not self.player_char.quest_dict["Side"]["Naivete"]["Completed"]:
                self.add_message("You fill the vial with spring water.")
                self.player_char.modify_inventory(items.EmptyVial(), subtract=True, rare=True)
                self.player_char.modify_inventory(items.SpringWater(), rare=True)
                self.player_char.quest_dict["Side"]["Naivete"]["Completed"] = True
                self.add_message("Quest completed: Naivete")
                popup = ConfirmationPopup(
                    self.presenter,
                    "You fill the empty vial with Spring Water.\n\nItem received: Spring Water",
                    show_buttons=False,
                )
                popup.show(
                    background_draw_func=self._dungeon_dialog_background,
                    flush_events=True,
                    require_key_release=True,
                    min_display_ms=300,
                )

        # Random encounter with Fuath
        if self.player_char.level.pro_level > 1 and not random.randint(0, 1):
            if not hasattr(spring_tile, "defeated") or not spring_tile.defeated:
                self.add_message("A Fuath emerges from the spring!")

                enemy = enemies.Fuath()

                # Start combat
                self._refresh_cached_frame()
                self.combat_manager.start_combat(self.player_char, enemy, spring_tile)

                spring_tile.defeated = True

        # Drink from spring
        if not hasattr(spring_tile, "drink"):
            spring_tile.drink = False

        if not spring_tile.drink:
            self.add_message("You drink from the spring... nothing seems to have changed.")
            spring_tile.drink = True

        # Check for Excaliper quest
        if not hasattr(spring_tile, "nimue"):
            spring_tile.nimue = False

        if not spring_tile.nimue and "Excaliper" in self.player_char.special_inventory:
            # Play Nimue materialization animation before showing event text
            self._animate_nimue_materialization()

            self._show_special_event_dialogue("Nimue", title="Nimue", image_path=nimue_image_path)
            self.player_char.modify_inventory(items.Excaliper(), subtract=True, rare=True)
            spring_tile.nimue = True
            # Track this as first meeting - don't offer quests yet
            if not hasattr(spring_tile, "nimue_met_before"):
                spring_tile.nimue_met_before = False

        # Offer Nimue quests only on subsequent visits after first meeting
        if spring_tile.nimue:
            if not hasattr(spring_tile, "nimue_met_before"):
                spring_tile.nimue_met_before = True

            # Check if this is a return visit (not the first meeting)
            if hasattr(spring_tile, "nimue_met_before") and spring_tile.nimue_met_before:
                from ..confirmation_popup import ConfirmationPopup
                from ..quest_manager import QuestManager

                qm = QuestManager(
                    self.presenter,
                    self.player_char,
                    quest_text_renderer=lambda text: self._show_dungeon_dialogue(
                        text,
                        title="Nimue",
                        image_path=nimue_image_path,
                    ),
                    quest_choice_renderer=lambda prompt, options: self._show_dungeon_choice(
                        prompt,
                        options,
                        image_path=nimue_image_path,
                    ),
                    renderer_preserve_formatting=True,
                )
                did_action, showed_message = qm.check_and_offer(
                    "Nimue",
                    show_help=False,
                    suppress_no_quests_message=True,
                )

                if not did_action and not showed_message:
                    hint = qm.get_random_help_hint("Nimue")
                    if hint:
                        self.add_message(hint)

            # Mark that we've met Nimue before for next visit
            spring_tile.nimue_met_before = True

        # Check for Excalibur upgrade
        if spring_tile.nimue:
            if "Excalibur" in self.player_char.inventory:
                self.add_message("The Lady of the Lake appears and upgrades your Excalibur!")
                self.player_char.modify_inventory(items.Excalibur2())
                self.player_char.modify_inventory(items.Excalibur(), subtract=True)
            elif "Excalibur" == self.player_char.equipment.get("Weapon").name:
                self.add_message("The Lady of the Lake appears and upgrades your Excalibur!")
                self.player_char.equipment["Weapon"] = items.Excalibur2()

        wizard_folly = self.player_char.quest_dict.get("Side", {}).get("The Wizard's Folly")
        if wizard_folly and not wizard_folly.get("Completed") and not wizard_folly.get("Turned In"):
            realm_popup = ConfirmationPopup(
                self.presenter,
                "Nimue parts the spring and reveals a hidden way.\n\nEnter the Realm of Cambion?",
                show_buttons=True,
            )
            if realm_popup.show(
                background_draw_func=self._dungeon_dialog_background,
                flush_events=True,
                require_key_release=True,
                min_display_ms=300,
            ):
                map_tiles.enter_realm_of_cambion(self.player_char)
                self._sync_dungeon_music()
                self._mark_view_dirty()
                self.add_message("The spring pulls you into the Realm of Cambion.")

    def _interact_anti_magic_switch(self, switch_tile):
        """Handle the Cambion anti-magic terminal."""
        from ..confirmation_popup import CodeEntryPopup

        if getattr(switch_tile, "has_kaelenon_branch", lambda _game: False)(self.game):
            switch_tile.resolve_kaelenon_branch(self.game)
            for message in map_tiles.pop_cambion_messages(self.player_char):
                self.add_message(message)
            return

        popup = CodeEntryPopup(
            self.presenter,
            "Anti-Magic Terminal",
            "Enter the 4-digit override code",
        )
        code = popup.show(
            background_draw_func=self._dungeon_dialog_background,
            flush_events=True,
            require_key_release=True,
        )
        if code is None:
            self.add_message("You step away from the terminal.")
            return

        switch_tile.attempt_disable(self.game, code)
        for message in map_tiles.pop_cambion_messages(self.player_char):
            self.add_message(message)

    def _interact_unobtainium_room(self, unobtainium_tile):
        """Handle Unobtainium room interaction."""
        if hasattr(unobtainium_tile, "visited") and unobtainium_tile.visited:
            self.add_message("The ground here is already cleared.")
            return

        self.game.special_event("Unobtainium")
        self.add_message("You spot Unobtainium on the ground and pick it up!")
        self.player_char.modify_inventory(items.Unobtainium(), rare=True, quest=True)
        unobtainium_tile.visited = True

    def _interact_dead_body(self, body_tile):
        """Handle dead body interaction."""
        # Check for quest item pickup
        if "A Bad Dream" in self.player_char.quest_dict.get("Main", {}):
            if not hasattr(body_tile, "read") or not body_tile.read:
                self.game.special_event("Dead Body")
                self.add_message("You found a Lucky Locket on the body!")
                self.player_char.modify_inventory(items.LuckyLocket(), rare=True, quest=True)
                self.player_char.quest_dict["Main"]["A Bad Dream"]["Completed"] = True
                body_tile.read = True
                self.add_message("Quest completed: A Bad Dream")
                return

        # Trigger Waitress encounter if "A Bad Dream" has been turned in
        if "A Bad Dream" in self.player_char.quest_dict.get("Main", {}):
            if self.player_char.quest_dict["Main"]["A Bad Dream"].get("Turned In"):
                if not self.player_char.quest_dict["Main"]["A Bad Dream"].get(
                    "Waitress Defeated", False
                ):
                    self.game.special_event("Waitress")
                    self._play_sfx("waitress_wail")
                    self._show_special_event_dialogue(
                        "Waitress",
                        title="Waitress",
                        image_path=self._enemy_combat_sprite_image_path("mad_waitress.png"),
                    )
                    self.add_message("The Waitress appears, overcome with grief and rage!")

                    enemy = enemies.NightHag2()

                    # Start combat
                    self._refresh_cached_frame()
                    combat_won = self.combat_manager.start_combat(
                        self.player_char, enemy, body_tile
                    )

                    if combat_won:
                        # Mark the encounter as complete
                        self.player_char.quest_dict["Main"]["A Bad Dream"][
                            "Waitress Defeated"
                        ] = True
                    return

        # Check for Something to Cry About quest
        if "Something to Cry About" in self.player_char.quest_dict.get("Side", {}):
            if not self.player_char.quest_dict["Side"]["Something to Cry About"]["Completed"]:
                self.add_message("A Night Hag appears to protect the body!")

                enemy = enemies.NightHag2()

                # Start combat
                self._refresh_cached_frame()
                combat_won = self.combat_manager.start_combat(self.player_char, enemy, body_tile)

    def _interact_final_room(self, final_room_tile):
        """Handle final room interaction - ask if player wants to fight final boss."""
        ensure_story = getattr(self.player_char, "ensure_main_story_state", None)
        story_state = (
            ensure_story()
            if callable(ensure_story)
            else getattr(self.player_char, "main_story", {})
        )
        if isinstance(story_state, dict) and story_state.get("main_story_complete"):
            self._show_special_event_dialogue(
                "The Forsaken Tenet Ending", title="The Forsaken Tenet"
            )
            self.add_message("The Forsaken Tenet is already remembered.")
            self._mark_view_dirty()
            return
        if (
            isinstance(story_state, dict)
            and story_state.get("vesperion_false_final_triggered")
            and not story_state.get("true_final_unlocked")
        ):
            self._show_special_event_dialogue("Liminal Gap Blocker", title="Voluntas")
            self.add_message("Voluntas remains unresolved. The final chamber will not open yet.")
            self._mark_view_dirty()
            return
        true_final = isinstance(story_state, dict) and story_state.get("true_final_unlocked")

        choice = self.presenter.render_menu(
            "You stand before the final chamber.\n\n"
            "Vesperion awaits within.\n\n"
            "Do you wish to enter and face your destiny?",
            ["Yes, I'm ready", "No, not yet"],
        )

        if choice == 0:  # Yes
            self.add_message("You step forward into the final chamber...")
            return_location = (
                self.player_char.location_x,
                self.player_char.location_y,
                self.player_char.location_z,
                self.player_char.facing,
            )
            # Move player north into the final boss room (2 tiles north)
            self.player_char.location_y -= 2
            self._mark_view_dirty()

            # Reveal the surrounding room tiles
            final_room_tile.adjacent_visited(self.player_char)

            # Show Vesperion's dialogue
            special_event_dict = get_special_events()
            event_name = (
                "True Final Prelude"
                if true_final and "True Final Prelude" in special_event_dict
                else "Final Boss"
            )
            if event_name in special_event_dict:
                self._show_special_event_dialogue(event_name, title="Vesperion")
            if true_final:
                self._show_vesperion_choice_argument_if_ready(story_state)

            # Clear event queue to remove any lingering keypresses from dialogs
            pygame.event.clear()

            # Spawn and initiate combat with Vesperion
            vesperion = enemies.Vesperion()
            self.player_char.state = "fight"

            # Update combat manager with current world state
            self.combat_manager.player_world_dict = self.player_char.world_dict

            # Start combat
            self._refresh_cached_frame()
            combat_won = self.combat_manager.start_combat(
                self.player_char, vesperion, final_room_tile
            )

            story_state = (
                ensure_story()
                if callable(ensure_story)
                else getattr(self.player_char, "main_story", {})
            )
            if isinstance(story_state, dict) and story_state.get("pending_liminal_gap_entry"):
                self._enter_liminal_gap_stub(return_location, vesperion)
                return

            if combat_won:
                if true_final:
                    self._complete_true_final_sequence()
                else:
                    self.add_message("You have defeated Vesperion! The dungeon fades away...")
                    self.player_char.quit = True
                    self.running = False
            elif not self.player_char.is_alive():
                self.add_message("You were defeated... The world fades to black.")
                self._detach_dungeon_background_provider()
                try:
                    self.player_char.to_town()
                except Exception:
                    (
                        self.player_char.location_x,
                        self.player_char.location_y,
                        self.player_char.location_z,
                    ) = (5, 10, 0)
                self.player_char.state = "normal"
                self.running = False
            else:
                self.add_message("You escaped from combat.")
        else:
            # Move player back south (1 tile)
            self.add_message("You step back to prepare yourself...")
            self.player_char.location_y += 1
            self._mark_view_dirty()

    def _complete_true_final_sequence(self):
        """Play the completed main-story ending after true-final Vesperion victory."""
        story_state = self.player_char.ensure_main_story_state()
        story_state["vesperion_true_final_defeated"] = True
        story_state["main_story_complete"] = True
        self._show_special_event_dialogue("Vesperion True Final Victory", title="Vesperion")
        self._show_special_event_dialogue("The Forsaken Tenet Ending", title="The Forsaken Tenet")
        self._show_special_event_dialogue("The Thirsty Dog Epilogue", title="The Thirsty Dog")
        self.add_message("Vesperion is defeated. Voluntas endures, and the main story is complete.")
        self.player_char.quit = True
        self.player_char.state = "normal"
        self.running = False
        self._mark_view_dirty()
