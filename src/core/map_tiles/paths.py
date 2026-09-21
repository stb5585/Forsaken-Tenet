"""Foundational dungeon paths, walls, and terrain tiles."""

from src.core.randomness import gameplay_random as random

from .. import enemies, items, thieves_guild
from ..combat import CombatEncounter
from .rules import (
    _CARDINAL_DIRECTIONS,
    JESTER_TOKENS_REQUIRED,
    REALM_OF_CAMBION_LEVEL,
    _apply_cambion_antimagic,
    check_fake_wall,
    jester_token_count,
    nature_communion_text,
    quest_biased_random_enemy,
    reveal_cambion_code_clue,
)


class MapTile:

    def __init__(self, x, y, z):
        self.x = x
        self.y = y
        self.z = z
        self.near = False
        self.visited = False  # tells whether the tile has been visited by player_char
        self.enter = True  # keeps player_char from entering walls
        self.special = False
        self.open = False

    def intro_text(self, game):
        intro_str = ""
        if items.can_detect_fake_walls(game.player_char):
            intro_str += check_fake_wall(self, game)
        return intro_str

    def modify_player(self, game):
        raise NotImplementedError()

    def available_actions(self, player_char):
        """Returns all the available actions in this room."""
        raise NotImplementedError()

    def adjacent_visited(self, player_char):
        """Changes visited parameter for 4 adjacent tiles"""
        # reveals 4 spaces in cardinal directions
        see = [True] * 4
        try:
            if "LockedDoor" in str(self):
                if (
                    not self.open
                    and self.blocked == "East"
                    and not player_char.world_dict[(self.x + 1, self.y, self.z)].near
                ):
                    see[0] = False
            player_char.world_dict[(self.x + 1, self.y, self.z)].near = see[0]
        except KeyError:
            pass
        try:
            if "LockedDoor" in str(self):
                if (
                    not self.open
                    and self.blocked == "West"
                    and not player_char.world_dict[(self.x - 1, self.y, self.z)].near
                ):
                    see[1] = False
            player_char.world_dict[(self.x - 1, self.y, self.z)].near = see[1]
        except KeyError:
            pass
        try:
            if "LockedDoor" in str(self) or "FinalBlocker" in str(self):
                if (
                    not self.open
                    and self.blocked == "North"
                    and not player_char.world_dict[(self.x, self.y - 1, self.z)].near
                ):
                    see[2] = False
            player_char.world_dict[(self.x, self.y - 1, self.z)].near = see[2]
        except KeyError:
            pass
        try:
            if "LockedDoor" in str(self):
                if (
                    not self.open
                    and self.blocked == "South"
                    and not player_char.world_dict[(self.x, self.y + 1, self.z)].near
                ):
                    see[3] = False
            player_char.world_dict[(self.x, self.y + 1, self.z)].near = see[3]
        except KeyError:
            pass


class StairsUp(MapTile):

    def intro_text(self, game):
        intro_str = super().intro_text(game)
        intro_str += (
            f"{game.player_char.name} sees a flight of stairs going up.\n" f"(Enter 'u' to use)\n"
        )
        return intro_str

    def modify_player(self, game):
        self.visited = True
        self.adjacent_visited(game.player_char)

    def available_actions(self, player_char):
        return []


class StairsDown(MapTile):

    def intro_text(self, game):
        intro_str = super().intro_text(game)
        intro_str += (
            f"{game.player_char.name} sees a flight of stairs going down.\n" f"(Enter 'j' to use)\n"
        )
        return intro_str

    def modify_player(self, game):
        self.visited = True
        self.adjacent_visited(game.player_char)

    def available_actions(self, player_char):
        return []


class LadderUp(MapTile):

    def intro_text(self, game):
        intro_str = super().intro_text(game)
        intro_str += (
            f"{game.player_char.name} sees a sturdy ladder leading up.\n" f"(Enter 'u' to use)\n"
        )
        return intro_str

    def modify_player(self, game):
        self.visited = True
        self.adjacent_visited(game.player_char)

    def available_actions(self, player_char):
        return []


class LadderDown(MapTile):

    def intro_text(self, game):
        intro_str = super().intro_text(game)
        intro_str += (
            f"{game.player_char.name} sees a sturdy ladder leading down.\n" f"(Enter 'j' to use)\n"
        )
        return intro_str

    def modify_player(self, game):
        self.visited = True
        self.adjacent_visited(game.player_char)

    def available_actions(self, player_char):
        return []


class SpecialTile(MapTile):

    def __init__(self, x, y, z):
        super().__init__(x, y, z)
        self.special = True
        self.read = False

    def modify_player(self, game):
        self.visited = True
        self.adjacent_visited(game.player_char)

    def special_text(self, game):
        raise NotImplementedError

    def available_actions(self, player_char):
        return []


class Wall(MapTile):

    def __init__(self, x, y, z):
        super().__init__(x, y, z)
        self.enter = False

    def modify_player(self, game):
        self.visited = True
        self.adjacent_visited(game.player_char)

    def available_actions(self, player_char):
        """Returns all the available actions in this room."""
        return []


class FakeWall(Wall):

    def __init__(self, x, y, z):
        super().__init__(x, y, z)
        self.enter = True

    def available_actions(self, player_char):
        return []


class ThievesGuildTrialFakeWall(FakeWall):
    """False wall that only opens once the Thieves Guild initiation is active."""

    def __init__(self, x, y, z):
        super().__init__(x, y, z)
        self.enter = False

    def detectable_for(self, player_char):
        state = thieves_guild.ensure_state(player_char)
        return bool(state.get("trial_started") and state.get("trial_branch"))

    def sync_for_player(self, player_char):
        self.enter = self.detectable_for(player_char)

    def available_actions(self, player_char):
        self.sync_for_player(player_char)
        if not self.enter:
            return []
        return super().available_actions(player_char)

    def intro_text(self, game):
        self.sync_for_player(game.player_char)
        if not self.enter:
            return ""
        return super().intro_text(game)

    def modify_player(self, game):
        self.sync_for_player(game.player_char)
        if not self.enter:
            return
        super().modify_player(game)


class CavePath(MapTile):

    def __init__(self, x, y, z):
        super().__init__(x, y, z)
        self.enemy = None
        self.trap_type = None
        self.trap_triggered = False
        self.trap_warned = False
        self.trap_forced_initiative = False
        self.gathering_resource = None
        self.gathering_available = False
        self.gathering_harvested = False

    def modify_player(self, game):
        self.visited = True
        self.adjacent_visited(game.player_char)
        from .traps import trigger_tile_trap

        trigger_tile_trap(self, game.player_char)
        if self.z == REALM_OF_CAMBION_LEVEL:
            reveal_cambion_code_clue(game.player_char, (self.x, self.y, self.z))
        class_name = getattr(getattr(game.player_char, "cls", None), "name", "")
        familiar = getattr(game.player_char, "familiar", None)
        if class_name in ["Warlock", "Shadowcaster", "Demonologist"] and familiar is not None:
            if familiar.race == "Jinkin" and familiar.level.pro_level == 3:
                if not random.randint(
                    0, int(20 - game.player_char.check_mod("luck", luck_factor=10))
                ):
                    bonus = int("Master Locator" in game.player_char.spellbook.get("Skills", {}))
                    rand_item = items.random_item(self.z + bonus)()
                    game.player_char.modify_inventory(rand_item, 1)
        # Scale random encounter rate down if player greatly outlevels the area
        try:
            if hasattr(game.player_char, "player_level") and callable(
                game.player_char.player_level
            ):
                player_level = game.player_char.player_level()
            else:
                player_level = game.player_char.level.level
        except Exception:
            player_level = 1

        expected_level = max(1, (self.z + 1) * 10)
        level_diff = max(0, player_level - expected_level)

        extra_roll = min(10, level_diff // 5)

        encounter_roll_max = 4 + extra_roll
        try:
            from ..classes import bard, footpad, mage_mechanics, paladin

            multiplier = (
                paladin.encounter_rate_multiplier(game.player_char)
                * bard.encounter_rate_multiplier(game.player_char)
                * footpad.encounter_rate_multiplier(game.player_char)
                * mage_mechanics.torchlight_encounter_multiplier(game.player_char)
            )
            encounter_slots = max(1, int(round((encounter_roll_max + 1) / multiplier)))
            encounter_roll_max = max(0, encounter_slots - 1)
        except Exception:
            pass

        if all(
            [not random.randint(0, encounter_roll_max), self.enemy is None, game._random_combat]
        ):
            self.enter_combat(game.player_char)
            try:
                from ..classes import pathfinder

                if pathfinder.animal_avoids_encounter(
                    game.player_char,
                    self.enemy,
                ):
                    self.enemy = None
                    game.player_char.state = "normal"
            except Exception:
                pass
            self.detectable_random_encounter = self.enemy is not None

    def available_actions(self, player_char):
        if player_char.state == "fight":
            action_list = ["Attack", "Use Item", "Flee"]
            if not player_char.abilities_suppressed():
                if player_char.usable_abilities("Spells"):
                    action_list.insert(1, "Cast Spell")
                if player_char.usable_abilities("Skills"):
                    action_list.insert(1, "Use Skill")
            action_list.insert(1, "Defend")
            if player_char.is_disarmed():
                action_list.insert(2, "Pickup Weapon")
            action_list = player_char.additional_actions(action_list)
            return action_list
        return []

    def enter_combat(self, player_char):
        raise NotImplementedError


class EmptyCavePath(CavePath):
    """
    Cave Path with no random enemies
    """

    def modify_player(self, game):
        return super().modify_player(game)

    def enter_combat(self, player_char):
        pass


class DecorativeCavePath(EmptyCavePath):
    """Traversable visual hook for future dungeon interaction systems."""

    description = ""

    def intro_text(self, game):
        intro_str = super().intro_text(game)
        if self.description:
            intro_str += f"{self.description}\n"
        return intro_str


class RubbleTile(DecorativeCavePath):
    description = "Loose rubble and crumbling stone choke the edges of this passage."


class RootGrowthTile(DecorativeCavePath):
    description = "Pale roots and clinging lichen thread through the old stone."


class FungusPatchTile(DecorativeCavePath):
    description = "A damp patch of fungus gives off a faint bitter smell."


class CrystalClusterTile(DecorativeCavePath):
    description = "A cluster of crystals catches the dungeon gloom with a quiet inner shine."


class BonePileTile(DecorativeCavePath):
    description = "Bones, sinew, and scraps of fur have gathered in the dust."


class BrokenGearTile(DecorativeCavePath):
    description = "Broken equipment lies scattered here, too ruined to use for now."


class StrangeDraftTile(EmptyCavePath):
    """Floor 3 wind communion hallway for Shaman/Soulcatcher."""

    def intro_text(self, game):
        intro_str = super().intro_text(game)
        intro_str += "A strange draft threads through this passage without any visible source.\n"
        return intro_str

    def special_text(self, game):
        from ..classes import nature_totems

        if not nature_totems.is_nature_totem_class(game.player_char):
            return ""
        return nature_communion_text(game.player_char, "Wind")


class CavePath0(CavePath):

    def modify_player(self, game, popup_class=None):
        super().modify_player(game)
        if "Bring Him Home" in game.player_char.quest_dict["Side"]:
            if not game.player_char.quest_dict["Side"]["Bring Him Home"]["Completed"]:
                if not random.randint(0, 20 - game.player_char.check_mod("luck", luck_factor=10)):
                    game.special_event("Timmy")
                    game.player_char.quest_dict["Side"]["Bring Him Home"]["Completed"] = True
                    game.player_char.to_town()
        if "Ticket to Ride" in game.player_char.quest_dict["Side"]:
            if not game.player_char.quest_dict["Side"]["Ticket to Ride"]["Completed"]:
                if not random.randint(0, 20 - game.player_char.check_mod("luck", luck_factor=5)):
                    quest_message = "You find a piece of the raffle ticket.\n"
                    game.player_char.modify_inventory(items.TicketPiece(), rare=True)
                    quest_message += game.player_char.quests(item=items.TicketPiece())
                    if popup_class and game.presenter is not None:
                        # Pygame version - show quest notification as a popup
                        dungeon_bg = game.presenter.screen.copy()
                        popup = popup_class(game.presenter, quest_message, show_buttons=False)
                        popup.show(
                            background_draw_func=lambda: game.presenter.screen.blit(
                                dungeon_bg, (0, 0)
                            ),
                            flush_events=True,
                            require_key_release=True,
                            min_display_ms=300,
                        )

    def enter_combat(self, player_char):
        self.enemy = quest_biased_random_enemy(player_char, "0")
        _apply_cambion_antimagic(self, player_char, self.enemy)
        player_char.state = "fight"


class CavePath1(CavePath):

    @property
    def rookie_body_marker(self):
        return (self.x, self.y, self.z) == (8, 8, 1)

    def _dropped_rookie_body_here(self, player_char):
        rookie_quest = player_char.quest_dict.get("Side", {}).get("Rookie Mistake")
        if not rookie_quest:
            return False
        dropped_at = rookie_quest.get("Body Dropped At")
        return (
            list(dropped_at or []) == [self.x, self.y, self.z]
            and "Dead Soldier" not in player_char.special_inventory
        )

    def _should_trigger_rookie_event(self, player_char):
        rookie_quest = player_char.quest_dict.get("Side", {}).get("Rookie Mistake")
        return bool(
            self.rookie_body_marker
            and rookie_quest
            and not rookie_quest.get("Completed")
            and not rookie_quest.get("Body Dropped At")
        )

    def modify_player(self, game, popup_class=None):
        if self._dropped_rookie_body_here(game.player_char):
            self.visited = True
            self.adjacent_visited(game.player_char)
            rookie_item = items.DeadSoldier()
            game.player_char.modify_inventory(rookie_item, rare=True)
            rookie_quest = game.player_char.quest_dict["Side"]["Rookie Mistake"]
            rookie_quest["Completed"] = True
            rookie_quest.pop("Body Dropped At", None)
            self.dropped_rookie_body = False
            self.read = True
            return
        if self._should_trigger_rookie_event(game.player_char):
            self.visited = True
            self.adjacent_visited(game.player_char)
            game.special_event("Rookie")
            rookie_item = items.DeadSoldier()
            game.player_char.modify_inventory(rookie_item, rare=True)
            quest_message = "You found the rookie! He's dead...\n"
            game.player_char.quest_dict["Side"]["Rookie Mistake"]["Completed"] = True
            quest_message += "You have completed the quest Rookie Mistake.\n"
            self.read = True
            self._enter_rookie_combat(game.player_char)
            return
        super().modify_player(game)

    def _enter_rookie_combat(self, player_char):
        zombies = [enemies.Zombie(), enemies.Zombie()]
        encounter = CombatEncounter.from_enemies(zombies)
        self.enemy = encounter.primary_enemy
        self.enemy._runtime_combat_encounter = encounter
        for zombie in zombies:
            _apply_cambion_antimagic(self, player_char, zombie)
        player_char.state = "fight"

    def enter_combat(self, player_char):
        self.enemy = quest_biased_random_enemy(player_char, str(self.z))
        _apply_cambion_antimagic(self, player_char, self.enemy)
        player_char.state = "fight"


class CavePath2(CavePath):

    def enter_combat(self, player_char):
        self.enemy = quest_biased_random_enemy(player_char, str(self.z + 1))
        _apply_cambion_antimagic(self, player_char, self.enemy)
        player_char.state = "fight"


class FunhouseEmptyPath(EmptyCavePath):

    def __init__(self, x, y, z):
        super().__init__(x, y, z)
        self.read = False

    def _boss_direction(self, player_char):
        for (dx, dy), direction in _CARDINAL_DIRECTIONS.items():
            tile = player_char.world_dict.get((self.x + dx, self.y + dy, self.z))
            if tile is None:
                continue
            if type(tile).__name__ != "JesterBossRoom":
                continue
            if getattr(tile, "defeated", False):
                return None
            return direction
        return None

    def intro_text(self, game):
        intro_str = super().intro_text(game)
        blocked = self._boss_direction(game.player_char)
        if blocked and jester_token_count(game.player_char) < JESTER_TOKENS_REQUIRED:
            intro_str += "A shimmering force field seals off the Jester's sanctum.\n"
        elif blocked:
            intro_str += "The force field flickers and fades before you.\n"
        return intro_str

    def available_actions(self, player_char):
        blocked = self._boss_direction(player_char)
        if blocked and jester_token_count(player_char) < JESTER_TOKENS_REQUIRED:
            return []
        return super().available_actions(player_char)

    def special_text(self, game):
        blocked = self._boss_direction(game.player_char)
        if not blocked:
            return None
        token_count = jester_token_count(game.player_char)
        if token_count < JESTER_TOKENS_REQUIRED:
            self.read = False
            return "A crackling force field bars the way to the Jester."
        if not self.read:
            self.read = True
            return "Your Jester Tokens resonate and the force field drops."
        return None


class FunhousePath(CavePath):

    def __init__(self, x, y, z):
        super().__init__(x, y, z)

    def enter_combat(self, player_char):
        self.enemy = enemies.funhouse_enemy()
        player_char.state = "fight"


class FunhouseWall(FakeWall):
    """A deceptive wall tile that disorients the player when entered."""

    def __init__(self, x, y, z):
        super().__init__(x, y, z)
        self.blocked = None

    def intro_text(self, game):
        intro_str = super().intro_text(game)
        intro_str += (
            f"{game.player_char.name} sees only endless reflections and twisted corridors.\n"
        )
        intro_str += "Which way is forward?\n"
        return intro_str

    def modify_player(self, game):
        self.visited = True
        self.adjacent_visited(game.player_char)
        # Disorient the player: reverse their facing direction
        reverse_map = {"north": "south", "south": "north", "east": "west", "west": "east"}
        original_facing = game.player_char.facing
        game.player_char.facing = reverse_map.get(original_facing, original_facing)

    def available_actions(self, player_char):
        return []


class FunhouseBoundaryWall(Wall):
    """An impassable exterior wall for funhouse map boundaries."""

    pass


class BossPath(CavePath):

    def enter_combat(self, player_char):
        self.enemy = random.choice(
            [enemies.Minotaur(), enemies.Barghest(), enemies.Pseudodragon(), enemies.Nightmare()]
        )
        player_char.state = "fight"


class SandwormLair(EmptyCavePath):

    def modify_player(self, game):
        super().modify_player(game)


class FirePath(EmptyCavePath):

    def enter_combat(self, player_char):
        """Begin the FirePath-exclusive Flame Wisp encounter."""
        self.enemy = enemies.FlameWisp()
        player_char.state = "fight"

    def modify_player(self, game):
        super().modify_player(game)
        if not game.player_char.flying:
            resist = game.player_char.check_mod("resist", typ="Fire")
            health_10per = max(0, int(game.player_char.health.max * 0.1 * (1 - resist)))
            damage = random.randint(health_10per // 2, health_10per)
            game.player_char.health.current -= damage


class FirePathSpecial(FirePath):
    """A fire path containing a nature-communion interaction."""

    def special_text(self, game):
        return nature_communion_text(game.player_char, "Fire")

    def modify_player(self, game):
        super().modify_player(game)
