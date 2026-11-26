"""Chest, door, quest, and event-room tiles."""

from .. import enemies, items, opening_story, quest_progress
from .bosses import BossRoom
from .paths import CavePath, MapTile, SpecialTile, Wall
from .rules import chalice_altar_visible, relic_discovery_text


class ChestRoom(MapTile):
    def __init__(self, x, y, z):
        super().__init__(x, y, z)
        self.open = False
        self.locked = False
        self.loot = None
        # Assigned from the dungeon seed after all tiles are loaded.  ``None``
        # distinguishes legacy/unassigned state from a chest known to be safe.
        self.mimic_outcome: bool | None = None
        self.enter = False
        self.generate_loot()  # Generate loot when chest is created

    def available_actions(self, player_char):
        raise NotImplementedError

    def modify_player(self, game):
        self.visited = True
        self.adjacent_visited(game.player_char)
        self.generate_loot()

    def generate_loot(self):
        """Generate random loot for the chest if not already generated."""
        if self.loot is None:
            bonus = int("Locked" in str(self)) + int("Room2" in str(self))
            self.loot = items.random_item(self.z + bonus)


class UnlockedChestRoom(ChestRoom):

    def __init__(self, x, y, z):
        super().__init__(x, y, z)
        self.locked = False

    def intro_text(self, game):
        intro_str = super().intro_text(game)
        if not self.open:
            intro_str += f"{game.player_char.name} finds a chest. (Enter 'o' to open)\n"
        else:
            intro_str += "This room has an open chest.\n"
        return intro_str

    def available_actions(self, player_char):
        if not self.open:
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
        return []


class UnlockedChestRoom2(UnlockedChestRoom):

    def __init__(self, x, y, z):
        super().__init__(x, y, z)


class LockedChestRoom(ChestRoom):

    def __init__(self, x, y, z):
        super().__init__(x, y, z)
        self.locked = True

    def intro_text(self, game):
        intro_str = super().intro_text(game)
        if not self.open:
            if self.locked:
                intro_str += f"{game.player_char.name} finds a chest!!... but it is locked.\n"
            else:
                intro_str += f"{game.player_char.name} finds a chest. (Enter 'o' to open)\n"
        else:
            intro_str += "This room has an open chest.\n"
        return intro_str

    def available_actions(self, player_char):
        if not self.open:
            if self.locked:
                return []
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
        return []

    def modify_player(self, game):
        """Apply automatic locked-chest effects when the tile is entered."""
        self.visited = True
        self.adjacent_visited(game.player_char)
        self.generate_loot()
        if self.locked:
            # UI hook: prompt player to unlock chest (Master Key, lockpick, or Key)
            # UI hook: show unlock success/failure messages
            if "Master Key" in game.player_char.special_inventory:
                self.locked = False
            elif any(
                [
                    "Lockpick" in game.player_char.spellbook["Skills"],
                    "Master Lockpick" in game.player_char.spellbook["Skills"],
                ]
            ) and items.has_lockpick_kit(game.player_char):
                self.locked = False
                items.use_lockpick_kit(
                    game.player_char,
                    master="Master Lockpick" in game.player_char.spellbook["Skills"],
                )


class LockedChestRoom2(LockedChestRoom):

    def __init__(self, x, y, z):
        super().__init__(x, y, z)
        self.locked = True


class LockedDoor(MapTile):

    def __init__(self, x, y, z):
        super().__init__(x, y, z)
        self.open = False
        self.locked = True
        self.blocked = None

    def intro_text(self, game):
        intro_str = super().intro_text(game)
        if not self.open:
            if self.locked:
                intro_str += (
                    f"{game.player_char.name} finds a locked door.\n"
                    f"If only you could find the key...\n"
                )
            else:
                intro_str += "There is an unlocked door.\n" "(Enter 'o' to open)\n"
        else:
            intro_str += "There is an open door.\n"
        return intro_str

    def modify_player(self, game):
        """Apply automatic locked-door effects when the tile is entered."""
        self.visited = True
        self.which_blocked(game)
        self.adjacent_visited(game.player_char)
        # If door is already open, no need to unlock it
        if self.open:
            return
        if self.locked:
            # UI hook: prompt player to unlock door (Master Key, lockpick, or Old Key)
            # UI hook: show unlock success/failure messages
            if "Master Key" in game.player_char.special_inventory:
                self.locked = False
            elif "Master Lockpick" in game.player_char.spellbook[
                "Skills"
            ] and items.has_lockpick_kit(game.player_char):
                self.locked = False
                items.use_lockpick_kit(game.player_char, master=True)

    def available_actions(self, player_char):
        if not self.open:
            if self.locked:
                return []
            return []
        return []

    def which_blocked(self, game):
        if self.x == game.player_char.previous_location[0] + 1:
            self.blocked = "East"
        if self.x == game.player_char.previous_location[0] - 1:
            self.blocked = "West"
        if self.y == game.player_char.previous_location[1] - 1:
            self.blocked = "North"
        if self.y == game.player_char.previous_location[1] + 1:
            self.blocked = "South"


class OreVaultDoor(Wall):
    """
    Hidden door that blocks access to the Unobtainium vault.
    Appears as a regular wall unless the player has Keen Eye skill or the Cryptic Key.
    Can only be unlocked with the Cryptic Key, Master Key, or Master Lockpick.
    """

    def __init__(self, x, y, z):
        super().__init__(x, y, z)
        self.open = False
        self.locked = True
        self.blocked = None
        self.enter = False  # Starts as impassable wall
        self.detected = False  # Track if player has detected the hidden door

    def intro_text(self, game):
        intro_str = ""
        # Call grandparent MapTile intro_text for Keen Eye check
        intro_str += MapTile.intro_text(self, game)

        # Door is open - can pass through
        if self.open:
            intro_str += "The secret vault door stands open.\n"
            return intro_str

        # Check if player can perceive the hidden door
        has_keen_eye = "Keen Eye" in game.player_char.spellbook["Skills"]
        has_cryptic_key = "Cryptic Key" in game.player_char.inventory

        # Only reveal and mark as detected if player has the means to see it
        if has_cryptic_key:
            # Key glows in presence of the door
            self.detected = True
            intro_str += "The Cryptic Key in your possession begins to glow warmly.\n"
            intro_str += "You notice faint seams in the wall... a hidden door!\n"
        elif has_keen_eye:
            # Keen perception reveals the door
            self.detected = True
            intro_str += (
                f"{game.player_char.name}'s keen eye spots something unusual in the wall.\n"
            )
            intro_str += "The stone here doesn't quite match... it's a hidden door!\n"
        else:
            # Reset detected status if player no longer has the means to see it
            self.detected = False
        # Otherwise appears as a normal wall (no text)

        return intro_str

    def modify_player(self, game):
        """Update discovery and traversal state for the hidden vault door."""
        self.visited = True
        self.which_blocked(game)
        self.adjacent_visited(game.player_char)

        # If door hasn't been detected, treat it like a wall - no interaction
        has_cryptic_key = "Cryptic Key" in game.player_char.inventory
        has_keen_eye = "Keen Eye" in game.player_char.spellbook["Skills"]

        if not (has_cryptic_key or has_keen_eye or self.open):
            # Door is not detected and not open - act like a wall, do nothing
            return

        # If door is already open, allow passage
        if self.open:
            self.enter = True
            return

    def available_actions(self, player_char):
        # If open, allow normal movement
        if self.open:
            return []
        # If closed, acts like a wall (blocks movement)
        return []

    def which_blocked(self, game):
        if self.x == game.player_char.previous_location[0] + 1:
            self.blocked = "East"
        if self.x == game.player_char.previous_location[0] - 1:
            self.blocked = "West"
        if self.y == game.player_char.previous_location[1] - 1:
            self.blocked = "North"
        if self.y == game.player_char.previous_location[1] + 1:
            self.blocked = "South"


class WarningTile(CavePath):

    def __init__(self, x, y, z):
        super().__init__(x, y, z)
        self.warning = False

    def intro_text(self, game):
        intro_str = super().intro_text(game)
        if not self.warning:
            intro_str += "Enemies beyond this point increase in difficulty.\n" "Plan accordingly.\n"
        return intro_str

    def modify_player(self, game):
        self.visited = True
        self.adjacent_visited(game.player_char)
        self.warning = True

    def enter_combat(self, player_char):
        # If locked, check for ways to unlock
        if self.locked:
            # UI hook: prompt player to unlock chest (Master Key, lockpick, or Key)
            # UI hook: show unlock success/failure messages
            pass


class UnobtainiumRoom(SpecialTile):

    def intro_text(self, game):
        intro_str = super().intro_text(game)
        return intro_str

    def modify_player(self, game):
        # Reveal nearby tiles but leave the ore to be looted manually
        self.adjacent_visited(game.player_char)

    def special_text(self, game):
        if not self.read:
            game.special_event("Unobtainium")
            self.read = True


class RelicRoom(SpecialTile):

    def __init__(self, x, y, z):
        super().__init__(x, y, z)
        self.enter = False

    def intro_text(self, game):
        intro_str = super().intro_text(game)
        intro_str += "An empty altar stands in the center of the room.\n"
        return intro_str

    def modify_player(self, game):
        self.adjacent_visited(game.player_char)
        self.visited = True

    def special_text(self, game):
        if not self.read:
            floor = game.player_char.location_z
            answer = None
            story = game.player_char.ensure_main_story_state()
            if floor == 1:
                if not story.get("opening_patrol_fate_seen"):
                    show_threshold = getattr(game, "show_triangulus_threshold", None)
                    if callable(show_threshold):
                        show_threshold()
                    else:
                        game.special_event(
                            "Triangulus Threshold", message=opening_story.PATROL_FATE_TEXT
                        )
                choose_answer = getattr(game, "choose_triangulus_identity", None)
                if not callable(choose_answer):
                    return "The relic waits for an answer you have not yet given.\n"
                answer = choose_answer()
                if answer is None:
                    return "You leave Triangulus undisturbed.\n"
            relic = quest_progress.relic_for_floor(floor)
            if relic is None:
                return "The pedestal is empty.\n"
            discovery_message = relic_discovery_text(relic)
            show_discovery = getattr(game, "show_relic_discovery", None)
            if callable(show_discovery):
                show_discovery(discovery_message)
            else:
                game.special_event("Relic Room", message=discovery_message)
            result = quest_progress.collect_relic(game.player_char, floor, triangulus_answer=answer)
            if not result.collected:
                return "The pedestal is empty.\n"
            self.read = True
            return f"{result.quest_message}Your health and mana have been restored to full!\n"
        return ""


class IncubusLair(BossRoom):
    """Encounter with the Incubus (father of Merzhin) - required for Oedipal Complex quest."""

    def __init__(self, x, y, z):
        super().__init__(x, y, z)
        self.enemy = enemies.Incubus
        self.defeated = False

    def intro_text(self, game):
        intro_str = super().intro_text(game)
        # Check if quest is active
        if "Oedipal Complex" in game.player_char.quest_dict.get("Side", {}):
            if not game.player_char.quest_dict["Side"]["Oedipal Complex"]["Completed"]:
                intro_str += "A deep, primal presence emanates from the shadows. Eyes glow red in the darkness.\n"
            else:
                intro_str += "The faint charred remains of a demonic entity scatter the floor.\n"
        else:
            intro_str += "The air here feels heavy and oppressive.\n"
        return intro_str

    def modify_player(self, game):
        self.adjacent_visited(game.player_char)
        self.visited = True
        quest_data = game.player_char.quest_dict.get("Side", {}).get("Oedipal Complex")
        if not quest_data:
            return
        if quest_data.get("Completed") or self.defeated:
            return
        if game.player_char.state == "fight":
            return

        # Spawn and enter combat only when the quest is active/incomplete.
        self.generate_enemy()
        if self.enemy and self.enemy.is_alive():
            self.enter_combat(game.player_char)

    def special_text(self, game):
        # Only trigger if quest is active and not yet completed
        if "Oedipal Complex" in game.player_char.quest_dict.get("Side", {}):
            if not game.player_char.quest_dict["Side"]["Oedipal Complex"]["Completed"]:
                if not self.defeated:
                    return "The Incubus emerges from the shadows to challenge you!"
        return ""

    def enter_combat(self, player_char):
        player_char.state = "fight"

    def defeat_incubus(self, game):
        """Complete the Oedipal Complex quest when Incubus is defeated."""
        if "Oedipal Complex" in game.player_char.quest_dict.get("Side", {}):
            if not game.player_char.quest_dict["Side"]["Oedipal Complex"]["Completed"]:
                game.player_char.quest_dict["Side"]["Oedipal Complex"]["Completed"] = True
                game.special_event("Incubus Defeated")
                self.defeated = True
                self.enter = False
                return True
        return False

    def available_actions(self, player_char):
        if player_char.state == "fight":
            action_list = ["Attack", "Use Item"]
            if not player_char.abilities_suppressed():
                if player_char.usable_abilities("Spells"):
                    action_list.insert(1, "Cast Spell")
                if player_char.usable_abilities("Skills"):
                    action_list.insert(1, "Use Skill")
            action_list = player_char.additional_actions(action_list)
            return action_list
        return []


class GoldenChaliceRoom(SpecialTile):
    """Location of the Golden Chalice - required for The Holy Grail of Quests."""

    def __init__(self, x, y, z):
        super().__init__(x, y, z)
        # Hidden altar locations behave like an ordinary floor tile until revealed.
        self.enter = True

    @staticmethod
    def _altar_visible_for(player_char) -> bool:
        return chalice_altar_visible(player_char)

    def intro_text(self, game):
        self.enter = not self._altar_visible_for(game.player_char)
        intro_str = super().intro_text(game)
        if "The Holy Grail of Quests" in game.player_char.quest_dict.get("Side", {}):
            if not game.player_char.quest_dict["Side"]["The Holy Grail of Quests"]["Completed"]:
                intro_str += "A golden chalice filled with a mysterious liquid sits on a pedestal, glowing faintly.\n"
            else:
                intro_str += "An empty pedestal stands where the chalice once rested.\n"
        else:
            intro_str += "A golden chalice sits on a pedestal, but something feels... forbidden about disturbing it.\n"
        return intro_str

    def modify_player(self, game):
        self.enter = not self._altar_visible_for(game.player_char)
        self.adjacent_visited(game.player_char)
        self.visited = True

    def special_text(self, game):
        self.enter = not self._altar_visible_for(game.player_char)
        # Only allow pickup if quest is active
        if "The Holy Grail of Quests" in game.player_char.quest_dict.get("Side", {}):
            if not game.player_char.quest_dict["Side"]["The Holy Grail of Quests"]["Completed"]:
                return "The chalice is yours to take!"
            return ""
        return "An invisible force prevents you from taking the chalice."

    def pickup_chalice_action(self, game):
        """Actually pick up the chalice when player confirms."""
        self.enter = not self._altar_visible_for(game.player_char)
        if "The Holy Grail of Quests" in game.player_char.quest_dict.get("Side", {}):
            if not game.player_char.quest_dict["Side"]["The Holy Grail of Quests"]["Completed"]:
                game.special_event("Golden Chalice")
                game.player_char.modify_inventory(items.GoldenChalice(), rare=True, quest=True)
                game.player_char.quest_dict["Side"]["The Holy Grail of Quests"]["Completed"] = True
                self.read = True
                self.enter = False
                return True
        return False


class DeadBody(SpecialTile):

    def __init__(self, x, y, z):
        super().__init__(x, y, z)
        self.enemy = None
        self.defeated = False

    def intro_text(self, game):
        intro_str = super().intro_text(game)
        if not self.read:
            intro_str += "The body of a soldier lies in a heap on the floor.\n"
        else:
            if "Something to Cry About" in game.player_char.quest_dict["Side"]:
                if game.player_char.quest_dict["Side"]["Something to Cry About"]["Completed"]:
                    intro_str += "The two lovers have been reunited. May they rest in peace.\n"
            else:
                intro_str += (
                    "'Here lies Joffrey, survived by his one true love.\n"
                    "May he be a reminder of the horrors of combat.\n"
                )
        return intro_str

    def modify_player(self, game):
        self.adjacent_visited(game.player_char)
        self.visited = True
        if "Something to Cry About" in game.player_char.quest_dict["Side"] and not self.defeated:
            if not game.player_char.quest_dict["Side"]["Something to Cry About"]["Completed"]:
                game.special_event("Waitress")
                self.enter_combat(game.player_char)

    def special_text(self, game):
        if "A Bad Dream" in game.player_char.quest_dict["Main"]:
            if not self.read:
                game.special_event("Dead Body")
                game.player_char.modify_inventory(items.LuckyLocket(), rare=True, quest=True)
                game.player_char.quest_dict["Main"]["A Bad Dream"]["Completed"] = True
                self.read = True

    def enter_combat(self, player_char):
        self.enemy = enemies.NightHag2()
        player_char.state = "fight"

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
