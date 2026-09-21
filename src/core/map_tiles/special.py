"""Interactive and Realm of Cambion map tiles."""

from src.core.randomness import gameplay_random as random

from .. import items
from ..classes import dragoon, footpad
from .paths import EmptyCavePath, SpecialTile
from .rules import (
    CAMBION_ALARM_ENEMY,
    CAMBION_PORTAL_FLAVOR,
    CAMBION_PORTAL_MAP,
    CAMBION_ROTATOR_FLAVOR,
    CAMBION_SWITCH_CODE,
    CHALICE_QUEST_NAME,
    _apply_cambion_antimagic,
    _ensure_cambion_state,
    _ensure_chalice_progress,
    _enterable_adjacent_positions,
    _queue_cambion_message,
    cambion_anti_magic_active,
    disable_cambion_anti_magic,
    nature_communion_text,
    return_to_underground_spring,
    reveal_cambion_code_clue,
    sync_chalice_map_description,
)


class UndergroundSpring(SpecialTile):
    """
    Drinking from the spring unlocks the sword Excaliper 2:B19
    Fuath remains the unique boss of the spring and is not a Xenid choice.
    Retrieve Excaliper item to summon Maid of the Spring, Nimue (quest giver)
    Special interaction (maybe reward?) if you craft Excalibur and return
    """

    def __init__(self, x, y, z):
        super().__init__(x, y, z)
        self.drink = False
        self.nimue = False
        self.enemy = None
        self.defeated = False

    def special_text(self, game):
        pass

    def available_actions(self, player_char):
        if player_char.state == "fight":
            action_list = ["Attack", "Use Item"]
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


class Boulder(SpecialTile):

    def __init__(self, x, y, z):
        super().__init__(x, y, z)
        self.enter = False

    def intro_text(self, game):
        intro_str = super().intro_text(game)
        if not self.read:
            intro_str += "You see a boulder that seems very out of place.\n"
        else:
            intro_str += "There's that boulder where you found that sword...and broke it.\n"
        return intro_str

    def modify_player(self, game):
        pass

    def special_text(self, game):
        earth_message = nature_communion_text(game.player_char, "Earth")
        if game.player_char.world_dict[(4, 9, 3)].drink and not self.read:
            game.special_event("Boulder")
            game.player_char.modify_inventory(items.Excaliper(), rare=True)
            self.read = True

        quest_data = game.player_char.quest_dict.get("Side", {}).get(CHALICE_QUEST_NAME)
        progress = _ensure_chalice_progress(quest_data)
        if progress and progress.get("Hooded") and not progress.get("Map"):
            if self.read:
                game.special_event("Chalice Map")
                game.player_char.modify_inventory(items.ChaliceMap(), rare=True, quest=True)
                progress["Map"] = True
                sync_chalice_map_description(game.player_char)
                quest_data["Help Text"] = (
                    "Bring the map to the Sergeant at the barracks for help deciphering it."
                )
        return earth_message


class Portal(EmptyCavePath):
    """
    Returns player from the Realm of Cambion to the Underground Spring
    """

    def __init__(self, x, y, z):
        super().__init__(x, y, z)

    def intro_text(self, game):
        intro_str = super().intro_text(game)
        intro_str += (
            "A shimmering portal flickers here, reflecting impossible corridors in its surface.\n"
        )
        return intro_str

    def modify_player(self, game):
        self.visited = True
        player_char = game.player_char
        self.adjacent_visited(player_char)
        reveal_cambion_code_clue(player_char, (self.x, self.y, self.z))
        pos = (self.x, self.y, self.z)
        if pos in CAMBION_PORTAL_MAP:
            destination = CAMBION_PORTAL_MAP[pos]
            player_char.previous_location = pos
            player_char.location_x, player_char.location_y, player_char.location_z = destination
            destination_tile = player_char.world_dict.get(destination)
            if destination_tile:
                destination_tile.visited = True
                destination_tile.adjacent_visited(player_char)
            _queue_cambion_message(
                player_char,
                CAMBION_PORTAL_FLAVOR.get(
                    pos,
                    "Space folds in on itself and spits you out elsewhere in the realm.",
                ),
            )
            return
        return_to_underground_spring(player_char)


class Rotator(EmptyCavePath):
    """
    Spins the player around and pushes them into one of the adjacent enterable spaces
    """

    def __init__(self, x, y, z):
        super().__init__(x, y, z)

    def intro_text(self, game):
        intro_str = super().intro_text(game)
        intro_str += (
            "The floor hums beneath your feet, as if some hidden mechanism is waiting to trigger.\n"
        )
        return intro_str

    def modify_player(self, game):
        self.visited = True
        player_char = game.player_char
        previous = getattr(player_char, "previous_location", None)
        reveal_cambion_code_clue(player_char, (self.x, self.y, self.z))

        options = _enterable_adjacent_positions(player_char.world_dict, self.x, self.y, self.z)
        if not options:
            self.adjacent_visited(player_char)
            return

        filtered = [entry for entry in options if entry[1] != previous]
        if filtered:
            options = filtered

        direction, destination = random.choice(options)
        player_char.previous_location = (self.x, self.y, self.z)
        player_char.facing = direction
        player_char.location_x, player_char.location_y, player_char.location_z = destination

        destination_tile = player_char.world_dict.get(destination)
        if destination_tile:
            destination_tile.visited = True
            destination_tile.adjacent_visited(player_char)
        _queue_cambion_message(
            player_char, "The room spins violently and throws you down a different passage."
        )
        _queue_cambion_message(
            player_char, CAMBION_ROTATOR_FLAVOR[cambion_anti_magic_active(player_char)]
        )


class Trap(EmptyCavePath):
    """ """

    def __init__(self, x, y, z):
        super().__init__(x, y, z)

    def intro_text(self, game):
        return super().intro_text(game)

    def modify_player(self, game):
        super().modify_player(game)
        player_char = game.player_char
        reveal_cambion_code_clue(player_char, (self.x, self.y, self.z))
        damage = min(player_char.health.current - 1, random.randint(10, 28))
        damage, avoidance_message = footpad.trap_damage(player_char, damage)
        if damage > 0:
            player_char.health.current -= damage
            _queue_cambion_message(
                player_char, f"A hidden trap snaps shut, dealing {damage} damage!"
            )
        if avoidance_message:
            _queue_cambion_message(player_char, avoidance_message)


class AntiMagicSwitch(EmptyCavePath):
    """ """

    def __init__(self, x, y, z):
        super().__init__(x, y, z)
        self.enemy = None

    def intro_text(self, game):
        intro_str = super().intro_text(game)
        if cambion_anti_magic_active(game.player_char):
            intro_str += "A humming terminal pulses here, bound to the realm's anti-magic field.\n"
        else:
            intro_str += "The terminal sits dark and silent. The anti-magic field is down.\n"
        return intro_str

    def modify_player(self, game):
        self.visited = True
        self.adjacent_visited(game.player_char)

    def has_kaelenon_branch(self, game):
        return dragoon.has_pending_terminal_branch(game.player_char)

    def resolve_kaelenon_branch(self, game):
        message = dragoon.resolve_terminal_branch(game.player_char)
        if message:
            _queue_cambion_message(game.player_char, message)
            return True
        return False

    def attempt_disable(self, game, code: str | None):
        player_char = game.player_char
        if self.resolve_kaelenon_branch(game):
            return True
        state = _ensure_cambion_state(player_char)
        if not state["anti_magic_active"]:
            _queue_cambion_message(
                player_char,
                "The terminal displays: SHIELD OFFLINE. The realm feels less certain without its hum.",
            )
            return True

        if str(code).strip() == CAMBION_SWITCH_CODE:
            disable_cambion_anti_magic(player_char)
            _queue_cambion_message(
                player_char,
                "The terminal accepts the code. The anti-magic field collapses, and distant portals flare in reply.",
            )
            return True

        state["alarm_count"] += 1
        self.enemy = CAMBION_ALARM_ENEMY()
        _apply_cambion_antimagic(self, player_char, self.enemy)
        player_char.state = "fight"
        _queue_cambion_message(
            player_char, "The terminal flashes red. An alarm sounds and a guardian attacks!"
        )
        return False
