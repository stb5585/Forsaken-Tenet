"""Navigation behavior for the dungeon manager package."""

import random

import pygame

from src.core import map_tiles
from src.core.classes import class_rings, promotion_kits
from src.core.player import DIRECTIONS


class DungeonNavigationMixin:
    def _sync_realm_scoped_effects(self) -> None:
        """Clear effects that cannot persist after leaving their special realm."""
        if self.player_char.location_z != map_tiles.REALM_OF_CAMBION_LEVEL:
            self.player_char.anti_magic_active = False

    def _check_hidden_cache(self) -> None:
        """Award the equipped Seeker ring cache once a floor is well mapped."""
        level = int(self.player_char.location_z)
        progress = promotion_kits.level_mapping_progress(self.player_char, level)
        message = class_rings.award_hidden_cache(self.player_char, level, progress)
        if message:
            self.add_message(message)

    def move_forward(self):
        """Move one tile forward if the path is clear."""
        dx, dy = DIRECTIONS[self.player_char.facing]["move"]
        ahead_pos = (
            self.player_char.location_x + dx,
            self.player_char.location_y + dy,
            self.player_char.location_z,
        )

        tile_ahead = self.player_char.world_dict.get(ahead_pos)
        if tile_ahead is None:
            self.add_message("You can't move that way.")
            return False

        tile_type = type(tile_ahead).__name__
        sync_tile = getattr(tile_ahead, "sync_for_player", None)
        if callable(sync_tile):
            sync_tile(self.player_char)

        # Impassable tiles (walls, undetected hidden doors, etc.)
        if not getattr(tile_ahead, "enter", True):
            if tile_type == "OreVaultDoor" and getattr(tile_ahead, "locked", False):
                self.add_message("A solid wall blocks your path.")
            else:
                self.add_message("You can't move that way.")
            return False

        # Closed or locked doors block movement
        if "Door" in tile_type:
            if hasattr(tile_ahead, "open") and tile_ahead.open:
                pass
            elif getattr(tile_ahead, "locked", False):
                self.add_message("A locked door blocks your path. (Press O to unlock)")
                return False
            elif hasattr(tile_ahead, "open") and not tile_ahead.open:
                self.add_message("A closed door blocks your path. (Press O to open)")
                return False

        # Final blocker requires relics
        if "FinalBlocker" in tile_type and not self.player_char.has_relics():
            blocked_dir = getattr(tile_ahead, "blocked", None)
            if blocked_dir and blocked_dir.lower() == self.player_char.facing:
                self.add_message("An invisible force prevents you from moving forward!")
                return False

        current_tile = self.get_current_tile()
        if (
            current_tile
            and map_tiles.jester_force_field_blocks(
                current_tile, self.player_char, self.player_char.facing
            )
        ) or map_tiles.jester_force_field_blocks_entry(tile_ahead, self.player_char):
            self._show_special_event_dialogue(
                map_tiles.JESTER_FORCE_FIELD_EVENT,
                title="Jester",
                image_path=self._enemy_combat_sprite_image_path("jester.png"),
            )
            self.add_message("A crackling force field prevents you from moving forward!")
            return False

        trap_warning = map_tiles.find_trap_warning(tile_ahead, self.player_char, rng=random)
        if trap_warning:
            self.add_message(trap_warning)
            return False

        # Record previous position for tiles that inspect it (doors, blockers, etc.)
        self.player_char.previous_location = (
            self.player_char.location_x,
            self.player_char.location_y,
            self.player_char.location_z,
        )

        # Move the player
        self.player_char.location_x += dx
        self.player_char.location_y += dy
        self._sync_realm_scoped_effects()
        if hasattr(self.player_char, "record_step"):
            self.player_char.record_step()

        # The view definitely changed.
        self._mark_view_dirty()

        # Update tile visited status
        new_tile = self.get_current_tile()
        if new_tile:
            new_tile.visited = True
            new_tile.adjacent_visited(self.player_char)
            self._check_hidden_cache()

        # Debug: log tile type and FirePath state on each step
        try:
            tname = type(new_tile).__name__ if new_tile else "None"
            if new_tile and ("FirePath" in tname):
                self.player_char.check_mod("resist", typ="Fire")
        except Exception:
            pass

        # Get tile intro text
        intro_messages = self._get_tile_intro()
        if intro_messages:
            for message in intro_messages:
                self.add_message(message)

        # Check for random encounters or tile effects
        self._check_tile_effects()

        return True

    def turn_left(self):
        """Turn player 90 degrees counterclockwise."""
        directions = ["north", "east", "south", "west"]
        current_idx = directions.index(self.player_char.facing)
        self.player_char.facing = directions[(current_idx - 1) % 4]
        self.add_message(f"You turn to face {self.player_char.facing}.")
        self._mark_view_dirty()
        # Emit any context intro messages for the new facing (e.g., hidden door detection)
        intro_messages = self._get_tile_intro()
        if intro_messages:
            for message in intro_messages:
                self.add_message(message)

    def turn_right(self):
        """Turn player 90 degrees clockwise."""
        directions = ["north", "east", "south", "west"]
        current_idx = directions.index(self.player_char.facing)
        self.player_char.facing = directions[(current_idx + 1) % 4]
        self.add_message(f"You turn to face {self.player_char.facing}.")
        self._mark_view_dirty()
        # Emit any context intro messages for the new facing (e.g., hidden door detection)
        intro_messages = self._get_tile_intro()
        if intro_messages:
            for message in intro_messages:
                self.add_message(message)

    def turn_around(self):
        """Turn player 180 degrees."""
        directions = ["north", "east", "south", "west"]
        current_idx = directions.index(self.player_char.facing)
        self.player_char.facing = directions[(current_idx + 2) % 4]
        self.add_message(f"You turn around to face {self.player_char.facing}.")
        self._mark_view_dirty()
        # Emit any context intro messages for the new facing (e.g., hidden door detection)
        intro_messages = self._get_tile_intro()
        if intro_messages:
            for message in intro_messages:
                self.add_message(message)

    def use_stairs_up(self):
        """Use stairs to go up a level."""
        current_tile = self.get_current_tile()
        tile_type = type(current_tile).__name__

        if "StairsUp" not in tile_type and "LadderUp" not in tile_type:
            self.add_message("There are no stairs here!")
            return False

        target_level = self.player_char.location_z - 1
        loading_text = (
            "Returning to town..." if target_level <= 0 else f"Ascending to level {target_level}..."
        )
        self._show_dungeon_loading_screen(loading_text)

        self.player_char.location_z = target_level
        self._sync_realm_scoped_effects()
        self._sync_dungeon_music()
        if hasattr(self.player_char, "record_stairs_used"):
            self.player_char.record_stairs_used()
        if "StairsUp" in tile_type:
            self._move_to_adjacent_from_stairs()
        self._mark_view_dirty()
        self._suppress_navigation_input()
        self.add_message("You climb the stairs upward...")

        # Check if returned to town
        if self.player_char.in_town():
            self.add_message("You emerge back in town!")
            self.running = False  # Exit dungeon mode
            return True
        else:
            self.add_message(f"Now on dungeon level {self.player_char.location_z}")

        return True

    def use_stairs_down(self):
        """Use stairs to go down a level."""
        current_tile = self.get_current_tile()
        tile_type = type(current_tile).__name__

        if "StairsDown" not in tile_type and "LadderDown" not in tile_type:
            self.add_message("There are no stairs here!")
            return False

        target_level = self.player_char.location_z + 1
        self._show_dungeon_loading_screen(f"Descending to level {target_level}...")

        self.player_char.location_z = target_level
        self._sync_realm_scoped_effects()
        self._sync_dungeon_music()
        if hasattr(self.player_char, "record_stairs_used"):
            self.player_char.record_stairs_used()
        if "StairsDown" in tile_type:
            self._move_to_adjacent_from_stairs()
        self._mark_view_dirty()
        self._suppress_navigation_input()
        self.add_message("You descend the stairs deeper into the dungeon...")
        self.add_message(f"Now on dungeon level {self.player_char.location_z}")
        self._check_hidden_cache()

        return True

    def _suppress_navigation_input(self, ms: int = 250) -> None:
        """Discard buffered movement and block held keys until release."""
        self._navigation_input_suppressed_until = pygame.time.get_ticks() + ms
        navigation_keys = self._navigation_keys()
        try:
            pressed = pygame.key.get_pressed()
            self._navigation_keys_awaiting_release.update(
                key for key in navigation_keys if pressed[key]
            )
        except (IndexError, pygame.error):
            pass
        try:
            pygame.event.clear((pygame.KEYDOWN, pygame.KEYUP))
        except pygame.error:
            pass

    @staticmethod
    def _navigation_keys() -> set[int]:
        """Return keys that can change dungeon position or facing."""
        return {
            pygame.K_w,
            pygame.K_UP,
            pygame.K_a,
            pygame.K_LEFT,
            pygame.K_d,
            pygame.K_RIGHT,
            pygame.K_s,
            pygame.K_DOWN,
            pygame.K_u,
            pygame.K_j,
        }

    def _release_navigation_input(self, key: int) -> None:
        """Re-arm a transition-held navigation key after its key-up event."""
        self._navigation_keys_awaiting_release.discard(key)

    def _navigation_input_suppressed(self, key) -> bool:
        if key in self._navigation_keys_awaiting_release:
            return True
        return (
            key in self._navigation_keys()
            and pygame.time.get_ticks() < self._navigation_input_suppressed_until
        )

    def _is_walkable_spawn_tile(self, tile):
        """Check if tile can be used as a post-stairs spawn location."""
        if tile is None:
            return False

        tile_type = type(tile).__name__

        # Do not spawn directly onto stair tiles
        if any(name in tile_type for name in ("StairsUp", "StairsDown")):
            return False

        if not getattr(tile, "enter", True):
            return False

        if "Door" in tile_type:
            if getattr(tile, "locked", False):
                return False
            if hasattr(tile, "open") and not tile.open:
                return False

        return True

    def _move_to_adjacent_from_stairs(self):
        """After changing floor, move player from stairs tile to a valid adjacent tile."""
        x = self.player_char.location_x
        y = self.player_char.location_y
        z = self.player_char.location_z

        walkable_neighbors = []
        for direction in ("north", "east", "south", "west"):
            dx, dy = DIRECTIONS[direction]["move"]
            pos = (x + dx, y + dy, z)
            candidate_tile = self.player_char.world_dict.get(pos)
            if self._is_walkable_spawn_tile(candidate_tile):
                walkable_neighbors.append((direction, dx, dy, candidate_tile))

        # Most stair endpoints have exactly one enterable adjacent tile.
        if len(walkable_neighbors) == 1:
            _, dx, dy, candidate_tile = walkable_neighbors[0]
            self.player_char.location_x = x + dx
            self.player_char.location_y = y + dy
            candidate_tile.visited = True
            candidate_tile.adjacent_visited(self.player_char)
            return

        facing = self.player_char.facing
        right_turn = {"north": "east", "east": "south", "south": "west", "west": "north"}
        left_turn = {"north": "west", "west": "south", "south": "east", "east": "north"}
        back_turn = {"north": "south", "south": "north", "east": "west", "west": "east"}

        candidate_order = [facing, right_turn[facing], left_turn[facing], back_turn[facing]]

        for direction in candidate_order:
            dx, dy = DIRECTIONS[direction]["move"]
            pos = (x + dx, y + dy, z)
            candidate_tile = self.player_char.world_dict.get(pos)
            if self._is_walkable_spawn_tile(candidate_tile):
                self.player_char.location_x = x + dx
                self.player_char.location_y = y + dy

                # Mark destination tile as visited for consistency with normal movement
                candidate_tile.visited = True
                candidate_tile.adjacent_visited(self.player_char)
                return
