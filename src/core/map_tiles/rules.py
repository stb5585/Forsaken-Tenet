###########################################
"""map manager"""

from functools import lru_cache
from textwrap import wrap

from src.core.randomness import gameplay_random as random

from .. import enemies
from ..player import DIRECTIONS, REALM_OF_CAMBION_LEVEL

# Feature flag: Set to True to use enhanced combat with action queue
USE_ENHANCED_COMBAT = True


# functions
def check_fake_wall(tile, game):
    for dx, dy in [(1, 0), (-1, 0), (0, 1), (0, -1)]:
        try:
            wall = game.player_char.world_dict[(tile.x + dx, tile.y + dy, tile.z)]
            detectable = getattr(wall, "detectable_for", None)
            if callable(detectable) and not detectable(game.player_char):
                continue
            if "FakeWall" in str(wall) and not wall.visited:
                return "Something seems off but you aren't quite sure what...\n"
        except KeyError:
            continue
    return ""


def ordinary_chest_mimic_chance(player_char, *, locked: int = 0, plus: int = 0) -> float:
    """Return the non-funhouse chest mimic chance for the current player."""
    level_fn = getattr(player_char, "player_level", None)
    try:
        player_level = int(
            level_fn()
            if callable(level_fn)
            else getattr(getattr(player_char, "level", None), "level", 1)
        )
    except (TypeError, ValueError):
        player_level = 1
    if player_level < 5:
        return 0.0
    luck_mod = 0
    try:
        luck_mod = int(player_char.check_mod("luck", luck_factor=3))
    except Exception:
        luck_mod = 0
    chance = (
        0.12
        + (0.05 * int(bool(locked)))
        + (0.03 * int(bool(plus)))
        - min(0.07, max(0, luck_mod) * 0.01)
    )
    return max(0.05, min(0.25, chance))


def ordinary_chest_spawns_mimic(
    player_char, *, locked: int = 0, plus: int = 0, roll: float | None = None
) -> bool:
    """Return whether a non-funhouse chest becomes a mimic."""
    chance = ordinary_chest_mimic_chance(player_char, locked=locked, plus=plus)
    if chance <= 0:
        return False
    return (random.random() if roll is None else float(roll)) < chance


def assign_dungeon_chest_mimics(world_dict: dict, player_char, *, rng=None) -> int:
    """Assign stable Mimic outcomes to ordinary chests in a generated dungeon."""
    source = rng if rng is not None else random
    assigned = 0
    for _position, tile in sorted(world_dict.items()):
        if type(tile).__name__ == "FunhouseMimicChest" or not hasattr(tile, "mimic_outcome"):
            continue
        if getattr(tile, "mimic_outcome", None) is not None:
            continue
        locked = int(bool(getattr(tile, "locked", False)))
        plus = int(type(tile).__name__.endswith("2"))
        tile.mimic_outcome = ordinary_chest_spawns_mimic(
            player_char,
            locked=locked,
            plus=plus,
            roll=source.random(),
        )
        assigned += 1
    return assigned


CHALICE_QUEST_NAME = "The Holy Grail of Quests"
CHALICE_PROGRESS_KEY = "Chalice Progress"
CHALICE_ADVENTURER_POS = (12, 14, 3)
CHALICE_LOCATION_POS = (2, 17, 6)
UNDERGROUND_SPRING_POS = (4, 9, 3)
WIND_COMMUNION_POS = (5, 5, 3)
REALM_OF_CAMBION_ENTRY_POS = (1, 28, REALM_OF_CAMBION_LEVEL)
CAMBION_SWITCH_CODE = "2749"
CAMBION_SWITCH_POS = (12, 28, REALM_OF_CAMBION_LEVEL)
CAMBION_ALARM_ENEMY = enemies.Warforged
CAMBION_CODE_CLUES = {
    (1, 1, REALM_OF_CAMBION_LEVEL): "A sigil burned into the stone shows the first digit: 2.",
    (23, 9, REALM_OF_CAMBION_LEVEL): "A charred warning plate hisses. The second digit is 7.",
    (
        20,
        20,
        REALM_OF_CAMBION_LEVEL,
    ): "A rotating ring clicks into place and reveals the third digit: 4.",
    (25, 28, REALM_OF_CAMBION_LEVEL): "An etched rune near the terminal reveals the last digit: 9.",
}
CAMBION_PORTAL_PAIRS = [
    ((1, 1, REALM_OF_CAMBION_LEVEL), (28, 28, REALM_OF_CAMBION_LEVEL)),
    ((9, 1, REALM_OF_CAMBION_LEVEL), (28, 20, REALM_OF_CAMBION_LEVEL)),
    ((11, 1, REALM_OF_CAMBION_LEVEL), (1, 22, REALM_OF_CAMBION_LEVEL)),
    ((17, 1, REALM_OF_CAMBION_LEVEL), (5, 28, REALM_OF_CAMBION_LEVEL)),
    ((28, 1, REALM_OF_CAMBION_LEVEL), (8, 3, REALM_OF_CAMBION_LEVEL)),
    ((1, 4, REALM_OF_CAMBION_LEVEL), (16, 4, REALM_OF_CAMBION_LEVEL)),
    ((24, 6, REALM_OF_CAMBION_LEVEL), (22, 10, REALM_OF_CAMBION_LEVEL)),
    ((4, 11, REALM_OF_CAMBION_LEVEL), (17, 13, REALM_OF_CAMBION_LEVEL)),
    ((20, 13, REALM_OF_CAMBION_LEVEL), (23, 13, REALM_OF_CAMBION_LEVEL)),
    ((28, 15, REALM_OF_CAMBION_LEVEL), (22, 17, REALM_OF_CAMBION_LEVEL)),
    ((6, 18, REALM_OF_CAMBION_LEVEL), (12, 24, REALM_OF_CAMBION_LEVEL)),
]
CHALICE_MAP_BLANK_DESC = "A weathered map whose ink appears almost completely faded."
CHALICE_MAP_METHOD_DESC = (
    "A weathered map with barely visible marks. The hidden adventurer showed you a trick to reveal it—"
    "inspect it closely."
)
CHALICE_MAP_REVEALED_DESC = (
    "The hidden ink has surfaced. The map marks a sealed altar on the sixth floor."
)
CHALICE_MAP_REVEALED_ASCII = (
    "Map Fragment\n"
    "+------------------+\n"
    "| Floor 6          |\n"
    "|                  |\n"
    "|  x=2, y=17   X   |\n"
    "|              altar|\n"
    "+------------------+"
)


def _ensure_chalice_progress(quest_data: dict | None) -> dict | None:
    if not quest_data:
        return None
    progress = quest_data.setdefault(CHALICE_PROGRESS_KEY, {})
    for key in ("Hooded", "Map", "Sergeant", "Adventurer", "Revealed", "Spawned"):
        progress.setdefault(key, False)
    return progress


def get_chalice_progress(player_char):
    quest_dict = getattr(player_char, "quest_dict", {})
    quest_data = quest_dict.get("Side", {}).get(CHALICE_QUEST_NAME)
    return _ensure_chalice_progress(quest_data)


def chalice_altar_visible(player_char) -> bool:
    """Return whether the Golden Chalice altar should be visible to the player."""
    quest_dict = getattr(player_char, "quest_dict", {})
    quest_data = quest_dict.get("Side", {}).get(CHALICE_QUEST_NAME)
    progress = _ensure_chalice_progress(quest_data)
    return bool(progress and (progress.get("Revealed") or quest_data.get("Completed")))


def _set_chalice_map_description(player_char, text: str):
    map_items = player_char.special_inventory.get("Chalice Map", [])
    if not map_items:
        return
    wrapped = "\n".join(wrap(text, 35, break_on_hyphens=False))
    for map_item in map_items:
        map_item.description = wrapped


def sync_chalice_map_description(player_char):
    """Keep Chalice Map description aligned with quest progression."""
    quest_data = player_char.quest_dict.get("Side", {}).get(CHALICE_QUEST_NAME)
    progress = _ensure_chalice_progress(quest_data)
    if not progress or "Chalice Map" not in player_char.special_inventory:
        return

    if progress.get("Revealed") or (quest_data and quest_data.get("Completed")):
        _set_chalice_map_description(player_char, CHALICE_MAP_REVEALED_DESC)
    elif progress.get("Adventurer"):
        _set_chalice_map_description(player_char, CHALICE_MAP_METHOD_DESC)
    else:
        _set_chalice_map_description(player_char, CHALICE_MAP_BLANK_DESC)


def sync_rookie_body_drop_marker(player_char):
    """Reflect Rookie Mistake dropped-body quest state onto the loaded tile."""
    quest = getattr(player_char, "quest_dict", {}).get("Side", {}).get("Rookie Mistake")
    world_dict = getattr(player_char, "world_dict", {})
    for tile in world_dict.values():
        if getattr(tile, "dropped_rookie_body", False):
            tile.dropped_rookie_body = False
    dropped_at = quest.get("Body Dropped At") if quest else None
    if not dropped_at or "Dead Soldier" in getattr(player_char, "special_inventory", {}):
        return
    tile = world_dict.get(tuple(dropped_at))
    if tile is not None:
        tile.dropped_rookie_body = True
        tile.read = False


def rookie_body_visible_for_player(player_char, tile) -> bool:
    """Return whether the Rookie Mistake body marker should be visible."""
    if tile is None:
        return False
    if bool(getattr(tile, "read", False)):
        return False

    quest = getattr(player_char, "quest_dict", {}).get("Side", {}).get("Rookie Mistake")
    if not quest:
        return False

    if bool(getattr(tile, "dropped_rookie_body", False)):
        dropped_at = quest.get("Body Dropped At")
        tile_pos = [getattr(tile, "x", None), getattr(tile, "y", None), getattr(tile, "z", None)]
        return (
            bool(dropped_at)
            and list(dropped_at) == tile_pos
            and "Dead Soldier" not in getattr(player_char, "special_inventory", {})
        )

    if not bool(getattr(tile, "rookie_body_marker", False)):
        return False
    return not quest.get("Completed") and not quest.get("Body Dropped At")


def reveal_chalice_map_on_inspect(player_char, item) -> bool:
    """Reveal Chalice location when an instructed player inspects the map."""
    if not item or getattr(item, "name", "") != "Chalice Map":
        return False

    quest_data = player_char.quest_dict.get("Side", {}).get(CHALICE_QUEST_NAME)
    progress = _ensure_chalice_progress(quest_data)
    if not progress:
        return False

    revealed_now = False
    if progress.get("Adventurer") and not progress.get("Revealed"):
        progress["Revealed"] = True
        if quest_data is not None:
            quest_data["Help Text"] = (
                "The map reveals the altar at 6:2,17. Seek the Golden Chalice there."
            )
        revealed_now = True

    sync_chalice_map_description(player_char)
    return revealed_now


def nature_communion_text(player_char, aspect: str) -> str:
    from ..classes import nature_totems

    _unlocked, message = nature_totems.unlock_communion(player_char, aspect)
    return message


def chalice_map_preview_text(player_char) -> str:
    quest_data = player_char.quest_dict.get("Side", {}).get(CHALICE_QUEST_NAME)
    progress = _ensure_chalice_progress(quest_data)
    if not progress:
        return ""
    if not progress.get("Adventurer"):
        return "The map is too faded to decipher."
    if not progress.get("Revealed"):
        return "Most of the ink is still hidden. Inspect the map carefully to reveal the altar location."
    return CHALICE_MAP_REVEALED_ASCII


def _replace_tile(world_dict, pos, new_tile):
    old_tile = world_dict.get(pos)
    if old_tile:
        for attr in ("visited", "near", "open", "read", "blocked", "enter", "defeated"):
            if hasattr(old_tile, attr) and hasattr(new_tile, attr):
                setattr(new_tile, attr, getattr(old_tile, attr))
    world_dict[pos] = new_tile


CAMBION_PORTAL_MAP = {}
for left, right in CAMBION_PORTAL_PAIRS:
    CAMBION_PORTAL_MAP[left] = right
    CAMBION_PORTAL_MAP[right] = left

CAMBION_PORTAL_FLAVOR = {
    (
        1,
        1,
        REALM_OF_CAMBION_LEVEL,
    ): "The portal exhales cold mist, carrying the echo of a voice counting backward.",
    (
        9,
        1,
        REALM_OF_CAMBION_LEVEL,
    ): "For an instant, the corridor beyond the portal appears upside down.",
    (
        11,
        1,
        REALM_OF_CAMBION_LEVEL,
    ): "The portal flashes with the silhouette of a tower that is not on any map.",
    (17, 1, REALM_OF_CAMBION_LEVEL): "The portal smells sharply of rain on hot stone.",
    (
        28,
        1,
        REALM_OF_CAMBION_LEVEL,
    ): "A ribbon of green light coils around your wrist before snapping back into the portal.",
    (1, 4, REALM_OF_CAMBION_LEVEL): "The portal surface ripples like water disturbed from below.",
    (
        24,
        6,
        REALM_OF_CAMBION_LEVEL,
    ): "Something laughs from the other side, then abruptly forgets the joke.",
    (4, 11, REALM_OF_CAMBION_LEVEL): "The portal reflects you a heartbeat too late.",
    (20, 13, REALM_OF_CAMBION_LEVEL): "The portal's edge briefly hardens into black glass.",
    (28, 15, REALM_OF_CAMBION_LEVEL): "A pressure behind your eyes fades as the portal takes hold.",
    (6, 18, REALM_OF_CAMBION_LEVEL): "The portal opens with the sound of pages tearing.",
}
for left, right in CAMBION_PORTAL_PAIRS:
    CAMBION_PORTAL_FLAVOR.setdefault(right, CAMBION_PORTAL_FLAVOR[left])

CAMBION_ROTATOR_FLAVOR = {
    True: "The anti-magic field hums through the mechanism as the room rights itself.",
    False: "With the anti-magic field silent, the mechanism wobbles before throwing you onward.",
}

RELIC_DISCOVERY_TEXT = {
    "Triangulus": (
        "Triangulus rises from the altar, its three points bright with mind, body, and spirit. "
        "The room steadies as if an old oath has remembered its shape."
    ),
    "Quadrata": (
        "Quadrata settles into your hands, steady as a vow carved into stone. "
        "For one breath, the dungeon's shifting dark feels measured and contained."
    ),
    "Hexagonum": (
        "Hexagonum hums with living geometry, every edge answering roots, bone, and deep earth. "
        "Something patient beneath the floor recognizes you."
    ),
    "Luna": (
        "Luna glows with pale warmth, a quiet reminder that love is a choice renewed. "
        "The altar light softens, but the silence around it does not."
    ),
    "Polaris": (
        "Polaris catches a fixed northern light, pointing onward through the dark. "
        "The way ahead is no safer, only harder to lose."
    ),
    "Infinitas": (
        "Infinitas turns without beginning or end, holding the shape of endurance. "
        "The circle closes in your palm, and still the road continues."
    ),
}


def relic_discovery_text(relic) -> str:
    name = getattr(relic, "name", "Unknown Relic")
    return RELIC_DISCOVERY_TEXT.get(name, f"You found a relic: {name}!")


@lru_cache(maxsize=None)
def _enemy_names_for_collection_item(item_key: str) -> frozenset[str]:
    """Return random-encounter enemies that can drop the quest collection item."""
    if not isinstance(item_key, str) or not item_key.strip():
        return frozenset()
    item_key = item_key.strip()
    targets: set[str] = set()
    for catalog in enemies.random_enemy_catalog().values():
        for enemy in catalog:
            inventory = getattr(enemy, "inventory", {}) or {}
            for drop_entries in inventory.values():
                for drop_entry in drop_entries:
                    item_cls = drop_entry if isinstance(drop_entry, type) else type(drop_entry)
                    if getattr(item_cls, "__name__", "") == item_key:
                        enemy_name = getattr(enemy, "name", "").strip()
                        if enemy_name:
                            targets.add(enemy_name)
    return frozenset(targets)


def active_random_encounter_quest_targets(player_char) -> set[str]:
    """Return active quest enemy names that random encounters may softly favor."""
    targets: set[str] = set()
    quest_dict = getattr(player_char, "quest_dict", {}) or {}

    for category in ("Main", "Side"):
        quests = quest_dict.get(category, {}) or {}
        for quest_data in quests.values():
            if not isinstance(quest_data, dict):
                continue
            if quest_data.get("Completed") or quest_data.get("Turned In"):
                continue
            quest_type = quest_data.get("Type")
            target = quest_data.get("What")
            if quest_type == "Defeat" and isinstance(target, str) and target.strip():
                targets.add(target.strip())
            elif quest_type == "Collect":
                targets.update(_enemy_names_for_collection_item(target))

    for enemy_name, bounty_data in (quest_dict.get("Bounty", {}) or {}).items():
        try:
            completed = bool(bounty_data[2])
        except (IndexError, TypeError):
            completed = False
        if not completed and str(enemy_name).strip():
            targets.add(str(enemy_name).strip())

    return targets


def random_encounter_quest_bias_chance(player_char) -> float:
    """Return a small luck/charisma-based quest-target encounter bias chance."""
    try:
        luck_mod = max(0, int(player_char.check_mod("luck", luck_factor=10)))
    except Exception:
        luck_mod = 0

    stats = getattr(player_char, "stats", None)
    try:
        charisma = max(0, int(getattr(stats, "charisma", 0)))
    except (TypeError, ValueError):
        charisma = 0

    return min(0.15, 0.05 + (luck_mod * 0.005) + (charisma * 0.0025))


def quest_biased_random_enemy(player_char, level: str, rng=random):
    """Return a random enemy with a soft active-quest target nudge."""
    from ..classes import bard

    try:
        shifted_level = str(max(0, int(level) + bard.enemy_difficulty_shift(player_char)))
    except (TypeError, ValueError):
        shifted_level = level
    preferred_targets = active_random_encounter_quest_targets(player_char)
    return enemies.random_enemy(
        shifted_level,
        preferred_names=preferred_targets,
        preferred_chance=random_encounter_quest_bias_chance(player_char),
        rng=rng,
        allow_curated_encounter=True,
        # A live quest keeps its encounter source singleton, even when its
        # random-selection bias did not win this particular roll.
        allow_pilot3_rollout=not preferred_targets,
    )


def _enterable_adjacent_positions(
    world_dict, x: int, y: int, z: int
) -> list[tuple[str, tuple[int, int, int]]]:
    positions = []
    for direction, data in DIRECTIONS.items():
        dx, dy = data["move"]
        pos = (x + dx, y + dy, z)
        tile = world_dict.get(pos)
        if tile and getattr(tile, "enter", False):
            positions.append((direction, pos))
    return positions


def _ensure_cambion_state(player_char) -> dict:
    state = getattr(player_char, "cambion_state", None)
    if not isinstance(state, dict):
        state = {}
        player_char.cambion_state = state
    state.setdefault("anti_magic_active", True)
    state.setdefault("alarm_count", 0)
    state.setdefault("clues_found", {})
    state.setdefault("messages", [])
    player_char.anti_magic_active = bool(state["anti_magic_active"])
    return state


def _queue_cambion_message(player_char, message: str):
    state = _ensure_cambion_state(player_char)
    state["messages"].append(message)


def pop_cambion_messages(player_char) -> list[str]:
    if getattr(player_char, "location_z", None) != REALM_OF_CAMBION_LEVEL:
        state = getattr(player_char, "cambion_state", None)
        if not isinstance(state, dict):
            return []
    else:
        state = _ensure_cambion_state(player_char)
    messages = list(state.get("messages", []))
    state["messages"] = []
    return messages


def cambion_anti_magic_active(player_char) -> bool:
    return bool(_ensure_cambion_state(player_char).get("anti_magic_active", True))


def disable_cambion_anti_magic(player_char):
    state = _ensure_cambion_state(player_char)
    state["anti_magic_active"] = False
    player_char.anti_magic_active = False


def reveal_cambion_code_clue(player_char, pos):
    if pos not in CAMBION_CODE_CLUES:
        return
    state = _ensure_cambion_state(player_char)
    key = f"{pos[0]},{pos[1]},{pos[2]}"
    if state["clues_found"].get(key):
        return
    state["clues_found"][key] = True
    _queue_cambion_message(player_char, CAMBION_CODE_CLUES[pos])


def _apply_cambion_antimagic(tile, player_char, enemy=None):
    if tile.z != REALM_OF_CAMBION_LEVEL:
        return
    active = cambion_anti_magic_active(player_char)
    player_char.anti_magic_active = active
    if enemy is not None:
        enemy.anti_magic_active = active


def enter_realm_of_cambion(player_char):
    player_char.enter_realm_of_cambion(*REALM_OF_CAMBION_ENTRY_POS, facing="east")
    player_char.cambion_state = {
        "anti_magic_active": True,
        "alarm_count": 0,
        "clues_found": {},
        "messages": [],
    }
    player_char.anti_magic_active = True


def return_to_underground_spring(player_char):
    if hasattr(player_char, "cambion_return") and player_char.cambion_return:
        player_char.exit_realm_of_cambion()
        return
    player_char.location_x, player_char.location_y, player_char.location_z = UNDERGROUND_SPRING_POS
    player_char.facing = "east"
    player_char.anti_magic_active = False


JESTER_TOKEN_NAME = "Jester Token"
JESTER_TOKENS_REQUIRED = 4
JESTER_FORCE_FIELD_EVENT = "Jester Force Field"
_CARDINAL_DIRECTIONS = {
    (1, 0): "East",
    (-1, 0): "West",
    (0, -1): "North",
    (0, 1): "South",
}


def jester_token_count(player_char) -> int:
    """Count Jester Tokens across both inventories for backward compatibility."""
    count = 0
    for inventory_name in ("special_inventory", "inventory"):
        inventory = getattr(player_char, inventory_name, {})
        for item_list in inventory.values():
            count += sum(
                1 for item in item_list if getattr(item, "name", None) == JESTER_TOKEN_NAME
            )
    return count


def jester_force_field_blocks(tile, player_char, facing: str) -> bool:
    """Return True when a funhouse force field should block forward movement."""
    if type(tile).__name__ != "FunhouseEmptyPath":
        return False
    blocked = tile._boss_direction(player_char)
    if not blocked:
        return False
    if blocked.lower() != facing:
        return False
    return jester_token_count(player_char) < JESTER_TOKENS_REQUIRED


def jester_force_field_blocks_entry(tile, player_char) -> bool:
    """Return True when direct entry into the Jester boss room is still sealed."""
    if type(tile).__name__ != "JesterBossRoom":
        return False
    if getattr(tile, "defeated", False):
        return False
    return jester_token_count(player_char) < JESTER_TOKENS_REQUIRED


def deactivate_funhouse_teleporters(player_char) -> None:
    """Turn off all funhouse entry teleporters after the Jester is defeated."""
    for tile in getattr(player_char, "world_dict", {}).values():
        if type(tile).__name__ == "FunhouseTeleporter" and hasattr(tile, "active"):
            tile.active = False


def jester_defeated(player_char) -> bool:
    """Return True when player/world state says the Jester has been cleared."""
    for name_counts in getattr(player_char, "kill_dict", {}).values():
        if name_counts.get("Jester", 0):
            return True
    return any(
        type(tile).__name__ == "JesterBossRoom" and getattr(tile, "defeated", False)
        for tile in getattr(player_char, "world_dict", {}).values()
    )


def handle_chalice_adventurer(game):
    """Trigger the hidden adventurer clue for the Golden Chalice quest."""
    player_char = game.player_char
    quest_data = player_char.quest_dict.get("Side", {}).get(CHALICE_QUEST_NAME)
    progress = _ensure_chalice_progress(quest_data)
    if not progress:
        return
    if progress.get("Adventurer"):
        return
    if (
        player_char.location_x,
        player_char.location_y,
        player_char.location_z,
    ) != CHALICE_ADVENTURER_POS:
        return
    if not progress.get("Sergeant"):
        return
    progress["Adventurer"] = True
    quest_data["Help Text"] = "Inspect the Chalice Map to reveal where the hidden altar lies."
    sync_chalice_map_description(player_char)
    game.special_event("Chalice Adventurer")
