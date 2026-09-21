"""Player exploration, navigation, travel, and death behavior."""

import numpy

from src.core.randomness import gameplay_random as random
from src.paths import MAP_FILES_DIR

from .. import thieves_guild
from ..constants import TOWN_LOCATION
from .config import (
    DIRECTIONS,
    LIMINAL_GAP_ENTRY_FACING,
    LIMINAL_GAP_ENTRY_POS,
    LIMINAL_GAP_LEVEL,
    REALM_OF_CAMBION_LEVEL,
)
from .maps import _load_text_map, _load_tiled_map


class PlayerExplorationMixin:
    def minimap(self):
        """
        Function that allows the player_char to view the current dungeon level in terminal
        20 x 20 grid
        """

        def is_direction_visible_from_current(direction: str) -> bool:
            current_tile = self.world_dict.get((self.location_x, self.location_y, self.location_z))
            if not current_tile:
                return True

            blocked = getattr(current_tile, "blocked", None)
            if blocked and blocked.lower() == direction:
                if hasattr(current_tile, "open") and getattr(current_tile, "open", False):
                    return True
                return False

            return True

        visible_adjacent = set()
        adjacent_dirs = {
            "north": (0, -1),
            "south": (0, 1),
            "east": (1, 0),
            "west": (-1, 0),
        }
        for direction, (dx, dy) in adjacent_dirs.items():
            if not is_direction_visible_from_current(direction):
                continue
            pos = (self.location_x + dx, self.location_y + dy, self.location_z)
            if pos in self.world_dict:
                visible_adjacent.add((pos[0], pos[1]))

        map_size = (20, 20)
        map_array = numpy.zeros(map_size).astype(str)
        for tile in self.world_dict:
            if self.location_z == tile[2]:
                tile_x, tile_y = tile[1], tile[0]
                if (
                    self.world_dict[tile].near
                    or self.cls.name == "Seeker"
                    or (tile[0], tile[1]) in visible_adjacent
                ):
                    if "Stairs" in str(self.world_dict[tile]) or "Ladder" in str(
                        self.world_dict[tile]
                    ):
                        map_array[tile_x][tile_y] = "\u25e3"
                    elif "Door" in str(self.world_dict[tile]):
                        # Special handling for OreVaultDoor - only show as door if detected or open
                        if "OreVaultDoor" in str(self.world_dict[tile]):
                            if self.world_dict[tile].open:
                                map_array[tile_x][tile_y] = "."
                            elif (
                                hasattr(self.world_dict[tile], "detected")
                                and self.world_dict[tile].detected
                            ):
                                map_array[tile_x][tile_y] = "\u2593"
                            else:
                                # Show as wall if not detected
                                map_array[tile_x][tile_y] = "#"
                        else:
                            map_array[tile_x][tile_y] = (
                                "\u2593" if not self.world_dict[tile].open else "."
                            )
                    elif "Wall" in str(self.world_dict[tile]):
                        if (
                            "FakeWall" in str(self.world_dict[tile])
                            and self.world_dict[tile].visited
                        ):
                            map_array[tile_x][tile_y] = ":"
                        else:
                            map_array[tile_x][tile_y] = "#"
                    elif "Chest" in str(self.world_dict[tile]):
                        map_array[tile_x][tile_y] = (
                            "\u25a1" if self.world_dict[tile].open else "\u25a0"
                        )
                    elif "Relic" in str(self.world_dict[tile]):
                        map_array[tile_x][tile_y] = (
                            "\u25cb" if self.world_dict[tile].read else "\u25c9"
                        )
                    elif "BossRoom" in str(self.world_dict[tile]):
                        map_array[tile_x][tile_y] = (
                            "\u2620" if not self.world_dict[tile].defeated else "."
                        )
                    elif "SecretShop" in str(self.world_dict[tile]):
                        map_array[tile_x][tile_y] = "\u2302"
                    elif "WarpPoint" in str(self.world_dict[tile]):
                        map_array[tile_x][tile_y] = "\u25c9"
                    else:
                        map_array[tile_x][tile_y] = "."
        map_array[self.location_y][self.location_x] = DIRECTIONS[self.facing]["char"]
        map_array[map_array == "0.0"] = " "
        map_array = numpy.insert(map_array, 0, numpy.zeros(map_array.shape[1]), 0)
        map_array[map_array == "0.0"] = "#"
        map_array = numpy.vstack([map_array, numpy.zeros(map_array.shape[1])])
        map_array[map_array == "0.0"] = "#"
        map_array = numpy.insert(map_array, 0, numpy.zeros(map_array.shape[0]), 1)
        map_array[map_array == "0.0"] = "#"
        map_array = numpy.append(map_array, numpy.zeros(map_array.shape[0]).reshape(-1, 1), 1)
        map_array[map_array == "0.0"] = "#"
        map_str = map_str = "\n".join(" ".join(row) for row in map_array)
        return map_str

    def load_tiles(self):
        """Parses a file that describes the world space into the _world object"""
        from .. import map_tiles

        world_dict = {}
        map_dir = MAP_FILES_DIR
        files_by_level = {}
        for map_file in map_dir.glob("map_level_*.json"):
            try:
                z = int(map_file.stem.split("_")[-1])
            except ValueError:
                continue
            files_by_level[z] = map_file

        # Optional side-area map: funhouse challenge level (level 4 boss area).
        funhouse_path = map_dir / "map_funhouse.json"
        if funhouse_path.exists() and 7 not in files_by_level:
            files_by_level[7] = funhouse_path

        cambion_path = map_dir / "map_realm_cambion.json"
        if cambion_path.exists() and REALM_OF_CAMBION_LEVEL not in files_by_level:
            files_by_level[REALM_OF_CAMBION_LEVEL] = cambion_path

        liminal_path = map_dir / "map_liminal_gap.txt"
        if liminal_path.exists() and LIMINAL_GAP_LEVEL not in files_by_level:
            files_by_level[LIMINAL_GAP_LEVEL] = liminal_path

        for z, map_file in sorted(files_by_level.items()):
            if map_file.suffix == ".json":
                world_dict.update(_load_tiled_map(map_file, z, map_tiles))
                continue
            world_dict.update(_load_text_map(map_file, z, map_tiles))

        map_tiles.assign_dungeon_traps(
            world_dict,
            rng=random.Random(int(getattr(self, "dungeon_trap_seed", 0) or 0)),
        )
        map_tiles.assign_dungeon_gathering_nodes(
            world_dict,
            rng=random.Random(int(getattr(self, "dungeon_trap_seed", 0) or 0) ^ 0x6A7E1),
        )
        map_tiles.assign_dungeon_chest_mimics(
            world_dict,
            self,
            rng=random.Random(int(getattr(self, "dungeon_trap_seed", 0) or 0) ^ 0xC4E57),
        )

        wind_pos = getattr(map_tiles, "WIND_COMMUNION_POS", None)
        if wind_pos and wind_pos in world_dict:
            world_dict[wind_pos] = map_tiles.StrangeDraftTile(*wind_pos)

        if thieves_guild.TRIAL_ENTRY_POS in world_dict:
            world_dict[thieves_guild.TRIAL_ENTRY_POS] = map_tiles.CavePath0(
                *thieves_guild.TRIAL_ENTRY_POS
            )
        if thieves_guild.TRIAL_FAKE_WALL_POS in world_dict:
            guild_wall = map_tiles.ThievesGuildTrialFakeWall(*thieves_guild.TRIAL_FAKE_WALL_POS)
            guild_wall.sync_for_player(self)
            world_dict[thieves_guild.TRIAL_FAKE_WALL_POS] = guild_wall
        if thieves_guild.TRIAL_BOSS_POS in world_dict:
            world_dict[thieves_guild.TRIAL_BOSS_POS] = map_tiles.ThievesGuildTrialBossRoom(
                *thieves_guild.TRIAL_BOSS_POS
            )

        self.world_dict = world_dict
        map_tiles.sync_rookie_body_drop_marker(self)

    def additional_actions(self, action_list):
        """
        Controls the listed options during combat
        """
        if getattr(self, "_transformed", False):
            action_list.insert(1, "Dismiss Form")
        elif self.available_transform_forms():
            action_list.insert(1, "Transform")
        if self.is_disarmed() and "Pickup Weapon" not in action_list:
            action_list.insert(1, "Pickup Weapon")
        if (
            getattr(getattr(self, "cls", None), "name", "") == "Thaumaturgist"
            and any(x.is_alive() for x in self.summons.values())
            and not self.abilities_suppressed()
        ):
            action_list.insert(1, "Summon")
        if "Steal As Well" in self.spellbook["Skills"] and not self.abilities_suppressed():
            action_list.insert(1, "Steal As Well")
        # Note: Totem was previously duplicated here for Shaman/Soulcatcher
        # It's already accessible via the Skills submenu, so no need for separate action
        return action_list

    def has_relics(self):
        relics = ["Triangulus", "Quadrata", "Hexagonum", "Luna", "Polaris", "Infinitas"]
        return all(item in self.special_inventory for item in relics)

    def level_exp(self):
        """
        total experience required to level up for current level; different from exp_to_gain
        """
        from ..progression import experience_for_level

        return experience_for_level(self.level.level)

    def player_level(self):
        """
        total player level (cumulative across all promotions)
        Base class: levels 1-30
        First promotion: levels 31-60 (reset to 1, gain 30 more)
        Second promotion: levels 61-110 (reset to 1, gain 50 more)
        """
        return self.level.level

    def max_level(self):
        return self.level.level >= 100

    def in_town(self):
        return (self.location_x, self.location_y, self.location_z) == TOWN_LOCATION

    def to_town(self):
        self.location_x, self.location_y, self.location_z = TOWN_LOCATION

    def exit_funhouse(self):
        """Exit the funhouse and return to the saved location."""
        if hasattr(self, "funhouse_return") and self.funhouse_return:
            self.location_x, self.location_y, self.location_z, self.facing = self.funhouse_return
            self.funhouse_return = None
        else:
            # Fallback: return to town if no saved location
            self.to_town()

    def enter_realm_of_cambion(self, x, y, z, facing="east"):
        """Enter the Realm of Cambion from the current location."""
        self.cambion_return = (
            self.location_x,
            self.location_y,
            self.location_z,
            self.facing,
        )
        self.location_x = x
        self.location_y = y
        self.location_z = z
        self.facing = facing
        self.anti_magic_active = True

    def exit_realm_of_cambion(self):
        """Exit the Realm of Cambion and return to the saved location."""
        if hasattr(self, "cambion_return") and self.cambion_return:
            self.location_x, self.location_y, self.location_z, self.facing = self.cambion_return
            self.cambion_return = None
        self.anti_magic_active = False

    def in_realm_of_cambion(self):
        return self.location_z == REALM_OF_CAMBION_LEVEL

    def in_liminal_gap(self):
        return self.location_z == LIMINAL_GAP_LEVEL

    def enter_liminal_gap(self, return_location=None):
        """Enter the Liminal Gap hub after Vesperion's false-final transition."""
        story_state = self.ensure_main_story_state()
        story_state["vesperion_false_final_triggered"] = True
        story_state["pending_liminal_gap_entry"] = False
        story_state["liminal_gap_entered"] = True

        if return_location and len(return_location) >= 4:
            self.liminal_gap_return = tuple(return_location[:4])

        self.location_x, self.location_y, self.location_z = LIMINAL_GAP_ENTRY_POS
        self.facing = LIMINAL_GAP_ENTRY_FACING
        self.state = "normal"
        self.effects(end=True)
        self.health.current = max(1, self.health.max // 2)
        self.mana.current = max(0, self.mana.max // 2)

    def enter_liminal_gap_stub(self, return_location):
        """Compatibility wrapper for the old non-map Liminal stub."""
        self.enter_liminal_gap(return_location)

    def return_from_liminal_gap(self):
        """Return from the Liminal Gap after the true-final path unlocks."""
        story_state = self.ensure_main_story_state()
        if not story_state.get("true_final_unlocked"):
            return False
        if hasattr(self, "liminal_gap_return") and self.liminal_gap_return:
            self.location_x, self.location_y, self.location_z, self.facing = self.liminal_gap_return
            self.liminal_gap_return = None
            story_state["returned_from_liminal_gap"] = True
            self.state = "normal"
            return True
        return False

    def town_heal(self):
        self.state = "normal"
        self.health.current = self.health.max
        self.mana.current = self.mana.max
        for summon in self.summons.values():
            summon.health.current = summon.health.max
            summon.mana.current = summon.mana.max

    def usable_item(self, item):
        if self.in_town():
            cat_list = ["Stat"]
        else:
            cat_list = ["Health", "Mana", "Elixir", "Stat"]
        if item.subtyp in cat_list or item.name == "Sanctuary Scroll":
            return True
        return False

    def usable_abilities(self, typ):
        if self.abilities_suppressed():
            return False
        for ability in self.spellbook[typ].values():
            if not ability.passive and ability.cost <= self.mana.current:
                if any(
                    [
                        ability.name == "Shield Slam"
                        and self.equipment["OffHand"].subtyp != "Shield",
                        ability.name == "Mortal Strike" and self.equipment["Weapon"].handed == 1,
                    ]
                ):
                    continue
                return True
        # should only reach if not enough mana to cast spells; lasts for 4 turns
        if self.cls.name == "Wizard" and self.power_up and typ == "Spells":
            self.class_effects["Power Up"].active = True
            self.class_effects["Power Up"].duration = 4
            return True
        return False

    def max_weight(self):
        from .. import persistent_afflictions as afflictions

        return (
            int(self.stats.strength * afflictions.strength_multiplier(self))
            * 10
            * self.level.pro_level
        )

    def current_weight(self):
        weight = 0
        for item in self.equipment.values():
            weight += item.weight
        for item in self.inventory.values():
            weight += item[0].weight * len(item)
        for item in self.special_inventory.values():
            weight += item[0].weight * len(item)
        return round(weight, 1)

    def move(self, dx, dy):
        """Moves the character by dx, dy if the target tile allows entry."""
        self.previous_location = (self.location_x, self.location_y, self.location_z)
        new_x, new_y = self.location_x + dx, self.location_y + dy
        try:
            from .. import map_tiles

            current_tile = self.world_dict.get((self.location_x, self.location_y, self.location_z))
            if current_tile and map_tiles.jester_force_field_blocks(
                current_tile, self, self.facing
            ):
                return False
        except Exception:
            pass

        target_tile = self.world_dict.get((new_x, new_y, self.location_z), {})
        try:
            from ..map_tiles import find_trap_warning

            if find_trap_warning(target_tile, self):
                return False
        except Exception:
            pass
        can_enter_wall = (
            getattr(self, "enter_wall", False)
            and "Wall" in target_tile.__class__.__name__
            and "Boundary" not in target_tile.__class__.__name__
        )
        if getattr(target_tile, "enter", False) or can_enter_wall:
            self.location_x, self.location_y = new_x, new_y
            self.record_step()
            if getattr(self, "dwarf_hangover_steps", 0) > 0:
                self.dwarf_hangover_steps = max(0, int(self.dwarf_hangover_steps) - 1)
            return True
        return False

    def move_forward(self, game):
        """Moves the character in the direction they are facing."""
        try:
            from .. import map_tiles

            current_tile = self.world_dict.get((self.location_x, self.location_y, self.location_z))
            if current_tile and map_tiles.jester_force_field_blocks(
                current_tile, self, self.facing
            ):
                if game is not None and hasattr(game, "special_event"):
                    game.special_event(map_tiles.JESTER_FORCE_FIELD_EVENT)
                return False
        except Exception:
            pass
        dx, dy = DIRECTIONS[self.facing]["move"]
        return self.move(dx, dy)

    def turn(self, direction):
        """Turns the character left, right, or around (180 degrees)."""
        directions = ["north", "east", "south", "west"]
        current_idx = directions.index(self.facing)

        if direction == "right":
            new_idx = (current_idx + 1) % 4
        elif direction == "left":
            new_idx = (current_idx - 1) % 4
        elif direction == "around":
            new_idx = (current_idx + 2) % 4  # Move 2 steps forward in the list (180-degree turn)
        else:
            raise ValueError(f"Invalid turn direction: {direction}")

        self.facing = directions[new_idx]

    def turn_left(self):
        self.turn("left")

    def turn_right(self):
        self.turn("right")

    def turn_around(self):
        self.turn("around")

    def stairs(self, dz):
        """Moves the character up or down a floor."""
        self.previous_location = (self.location_x, self.location_y, self.location_z)
        self.location_z += dz
        self.record_stairs_used()
        if getattr(self, "dwarf_hangover_steps", 0) > 0:
            self.dwarf_hangover_steps = max(0, int(self.dwarf_hangover_steps) - 1)

    def stairs_up(self):
        self.stairs(dz=-1)

    def stairs_down(self):
        self.stairs(dz=1)

    def change_location(self, x, y, z):
        self.location_x = x
        self.location_y = y
        self.location_z = z

    def death(self):
        """Resolve death penalties, return the result message, and move the player to town."""
        from ..classes import promotion_kits

        promotion_kits.clear_combat_state(self)
        self.record_death()
        death_message = ""
        stat_list = ["strength", "intelligence", "wisdom", "constitution", "charisma", "dexterity"]
        form_snapshot = getattr(self, "_normal_form_snapshot", None)
        normal_stats = form_snapshot["stats"] if isinstance(form_snapshot, dict) else self.stats
        if self.level.level > 9 or self.level.pro_level > 1:
            cost = self.level.level * self.level.pro_level * 100 * self.location_z
            cost = random.randint(cost // 2, cost)
            cost = min(cost, self.gold)
            death_message += f"Resurrection costs you {cost} gold.\n"
            self.gold -= cost
            if not random.randint(0, normal_stats.charisma):
                death_message += "Complications occurred during your resurrection.\n"
                stat_index = random.randint(0, 5)
                stat_name = stat_list[stat_index]
                stat_attr = {
                    "strength": "strength",
                    "intelligence": "intel",
                    "wisdom": "wisdom",
                    "constitution": "con",
                    "charisma": "charisma",
                    "dexterity": "dex",
                }[stat_name]
                setattr(normal_stats, stat_attr, getattr(normal_stats, stat_attr) - 1)
                if normal_stats is not self.stats:
                    setattr(self.stats, stat_attr, getattr(self.stats, stat_attr) - 1)
                death_message += f"You have lost 1 {stat_name}.\n"
        self.state = "normal"
        self.effects(end=True)
        death_message += self._drop_rookie_body_on_death()
        self.to_town()
        death_message += "You wake up in town.\n"
        self.last_death_message = death_message
        return death_message

    def _drop_rookie_body_on_death(self):
        """Leave the Rookie Mistake body where the player fell."""
        quest = self.quest_dict.get("Side", {}).get("Rookie Mistake")
        if not quest or "Dead Soldier" not in self.special_inventory:
            return ""

        self.special_inventory.pop("Dead Soldier", None)
        quest["Completed"] = False
        dropped_at = [self.location_x, self.location_y, self.location_z]
        quest["Body Dropped At"] = dropped_at
        try:
            tile = self.world_dict.get(tuple(dropped_at))
            if tile is not None:
                setattr(tile, "dropped_rookie_body", True)
                setattr(tile, "read", False)
        except Exception:
            pass
        return "The rookie's body slips from your grasp and remains where you fell.\n"
