###########################################
"""Town manager"""

import random
import re

from . import enemies, items
from .data.data_loader import (
    get_patron_dialogues,
    get_quests,
    get_response_map,
    get_tavern_flavor_dialogues,
)

# Patron dialogue keyed by minimum total level (base + promotions)
# Loaded from external JSON file
PATRON_DIALOGUES = get_patron_dialogues()

# NPC responses to quest acceptance/rejection
# Loaded from external JSON file
RESPONSE_MAP = get_response_map()

# General tavern flavor comments used when no quests are available/active
# Loaded from external JSON file
TAVERN_FLAVOR_DIALOGUES = get_tavern_flavor_dialogues()


BOUNTY_RESTOCK_STEP_THRESHOLD = 200
BOUNTY_RESTOCK_ENEMY_THRESHOLD = 8
MAX_ACTIVE_BOUNTIES = 4

BOUNTY_BOARD_STATE_DEFAULTS = {
    "initialized": False,
    "last_restock_level": 0,
    "last_restock_steps": 0,
    "last_restock_enemies_defeated": 0,
}

RELIC_NAMES = ("Triangulus", "Quadrata", "Hexagonum", "Luna", "Polaris", "Infinitas")
MAJOR_BOSS_NAMES = (
    "Barghest",
    "Nightmare",
    "Iron Golem",
    "Domingo",
    "Jester",
    "Red Dragon",
    "Merzhin",
)


def default_bounty_board_state():
    """Return fresh bounty-board restock state for a player/save."""
    return dict(BOUNTY_BOARD_STATE_DEFAULTS)


def _nonnegative_int(value, fallback=0):
    try:
        return max(0, int(value))
    except (TypeError, ValueError):
        return fallback


def normalize_bounty_board_state(state=None):
    """Return a backward-compatible bounty-board restock state dictionary."""
    normalized = default_bounty_board_state()
    if isinstance(state, dict):
        normalized.update(state)

    normalized["initialized"] = bool(normalized.get("initialized", False))
    for key in (
        "last_restock_level",
        "last_restock_steps",
        "last_restock_enemies_defeated",
    ):
        normalized[key] = _nonnegative_int(
            normalized.get(key),
            BOUNTY_BOARD_STATE_DEFAULTS[key],
        )
    return normalized


def _player_level(player_char):
    if hasattr(player_char, "player_level"):
        try:
            return _nonnegative_int(player_char.player_level(), 1)
        except TypeError:
            pass
    level = getattr(player_char, "level", None)
    return _nonnegative_int(getattr(level, "level", 1), 1)


def _gameplay_stat(player_char, stat_name):
    stats = getattr(player_char, "gameplay_stats", {})
    if isinstance(stats, dict):
        return _nonnegative_int(stats.get(stat_name, 0))
    return 0


def ensure_bounty_board_state(player_char):
    """Attach normalized bounty-board restock state to the player."""
    state = normalize_bounty_board_state(getattr(player_char, "bounty_board_state", None))
    player_char.bounty_board_state = state
    return state


def active_bounty_count(player_char):
    quest_dict = getattr(player_char, "quest_dict", {})
    bounty_dict = quest_dict.get("Bounty", {}) if isinstance(quest_dict, dict) else {}
    return len(bounty_dict)


def _split_boss_room_name(class_name: str) -> str:
    base_name = class_name.removesuffix("BossRoom")
    return re.sub(r"(?<!^)(?=[A-Z])", " ", base_name).strip()


def already_defeated_enemy(player_char, enemy_name: str) -> bool:
    """Return whether saved progress already proves this enemy was defeated."""
    target_name = str(enemy_name or "").strip()
    if not target_name:
        return False

    kill_dict = getattr(player_char, "kill_dict", {}) or {}
    if isinstance(kill_dict, dict):
        for enemy_counts in kill_dict.values():
            if not isinstance(enemy_counts, dict):
                continue
            try:
                if int(enemy_counts.get(target_name, 0) or 0) > 0:
                    return True
            except (TypeError, ValueError):
                continue

    world_dict = getattr(player_char, "world_dict", {}) or {}
    if not isinstance(world_dict, dict):
        return False
    for tile in world_dict.values():
        if not getattr(tile, "defeated", False):
            continue
        tile_class_name = type(tile).__name__
        candidates = {tile_class_name, _split_boss_room_name(tile_class_name)}
        tile_enemy = getattr(tile, "enemy", None)
        if tile_enemy is not None:
            candidates.add(str(getattr(tile_enemy, "name", "") or ""))
            candidates.add(str(getattr(tile_enemy, "__name__", "") or ""))
        if target_name in candidates:
            return True
    return False


def _inventory_has_named_item(inventory: object, item_name: str) -> bool:
    if not isinstance(inventory, dict):
        return False
    if item_name in inventory:
        return True
    for key, value in inventory.items():
        if str(key) == item_name:
            return True
        entries = value if isinstance(value, (list, tuple, set)) else (value,)
        for entry in entries:
            if getattr(entry, "name", None) == item_name:
                return True
    return False


def _collected_relic_names(player_char) -> list[str]:
    inventory = getattr(player_char, "special_inventory", {})
    return [name for name in RELIC_NAMES if _inventory_has_named_item(inventory, name)]


def _quest_entry(player_char, category: str, quest_name: str) -> dict | None:
    quests = getattr(player_char, "quest_dict", {}).get(category, {})
    quest = quests.get(quest_name) if isinstance(quests, dict) else None
    return quest if isinstance(quest, dict) else None


def _active_quest(player_char, category: str, quest_name: str) -> bool:
    quest = _quest_entry(player_char, category, quest_name)
    return bool(quest and not quest.get("Completed") and not quest.get("Turned In"))


def _completed_unturned_quest(player_char, category: str, quest_name: str) -> bool:
    quest = _quest_entry(player_char, category, quest_name)
    return bool(quest and quest.get("Completed") and not quest.get("Turned In"))


def _defeated_boss_names(player_char) -> list[str]:
    return [name for name in MAJOR_BOSS_NAMES if already_defeated_enemy(player_char, name)]


def _relic_progress_hints(relic_names: list[str], speaker: str) -> list[str]:
    count = len(relic_names)
    if count <= 0:
        return []
    if speaker == "Sergeant":
        if count >= len(RELIC_NAMES):
            return [
                "All six relics are accounted for. Do not let victory make you casual; whatever waits below will know you carry them."
            ]
        return [
            f"You have {count} of the six relics. Keep them together; every guardian report says the dark below reacts when they gather."
        ]
    if speaker == "Soldier":
        if count >= len(RELIC_NAMES):
            return [
                "Every relic report on the board is marked recovered, but the old hands look more afraid than relieved."
            ]
        return [
            f"The relic board has {count} bright pin{'s' if count != 1 else ''} now. The map room gets colder each time we add one."
        ]
    if speaker == "Hooded Figure":
        if count >= len(RELIC_NAMES):
            return [
                "Six holy shapes, one closing circle. The last door will not mistake you for unchosen."
            ]
        return ["The relics do not merely wait to be found. They listen for each other."]
    if speaker == "Barkeep":
        if count >= len(RELIC_NAMES):
            return [
                "Six relics on one road. I would offer a toast, but the room has learned not to celebrate too early."
            ]
        return [
            "Word is another relic came home with you. The mugs rattled on the shelf before anyone said your name."
        ]
    if speaker == "Busboy":
        return [
            "People keep asking which relic you found next. I keep telling them the order matters less than getting you back alive."
        ]
    if speaker == "Waitress":
        return [
            "When you carry relic-light, even the quiet patrons notice. Please do not let it make you careless."
        ]
    if speaker == "Drunkard":
        return [
            "Relics, guardians, old songs... (hic) every shiny thing down there has teeth in the story somewhere."
        ]
    return []


def _boss_progress_hints(defeated: list[str], speaker: str) -> list[str]:
    if not defeated:
        return []

    defeated_set = set(defeated)
    hints: list[str] = []
    if speaker == "Sergeant":
        if "Barghest" in defeated_set:
            hints.append(
                "The Barghest report is closed. That means the first relic guardian was real, and so is everything after it."
            )
        if "Iron Golem" in defeated_set:
            hints.append(
                "With the Iron Golem down, deeper patrol markers are back on the table. Do not confuse access with safety."
            )
        if "Domingo" in defeated_set:
            hints.append(
                "The scientists say the warp route is stable after Domingo. I say stable does not mean friendly."
            )
        if "Jester" in defeated_set:
            hints.append(
                "The Jester file is sealed, but nobody here laughs at sealed files anymore."
            )
        if "Merzhin" in defeated_set:
            hints.append(
                "Cambion stopped moving on our maps after Merzhin fell. I do not trust a quiet map, but I will take it."
            )
    elif speaker == "Soldier":
        if "Nightmare" in defeated_set:
            hints.append(
                "The Nightmare patrol notes ended in ash. Yours is the first report that came back with a pulse."
            )
        if "Iron Golem" in defeated_set:
            hints.append(
                "Engineers are measuring the cracks left by the Iron Golem. They keep finding the same shape under different stones."
            )
        if "Jester" in defeated_set:
            hints.append(
                "After the Jester fell, we stopped finding playing cards under the barracks doors. I still check."
            )
        if "Merzhin" in defeated_set:
            hints.append(
                "The Realm of Cambion no longer shifts our patrol markers, but everyone still walks the corridors twice."
            )
    elif speaker == "Barkeep":
        if "Jester" in defeated_set:
            hints.append(
                "The first quiet night after the Jester died felt worse than the jokes. Quiet gives people room to count losses."
            )
        if "Merzhin" in defeated_set:
            hints.append(
                "When word came from Cambion, nobody cheered right away. They waited to see whether the walls agreed."
            )
    elif speaker == "Busboy":
        if "Iron Golem" in defeated_set:
            hints.append(
                "A guard said the Iron Golem left footprints like wells. I am pretending that was an exaggeration."
            )
        if "Merzhin" in defeated_set:
            hints.append(
                "The portal-room crowd drinks more water since Merzhin fell. Nobody says why."
            )
    elif speaker == "Waitress":
        if "Nightmare" in defeated_set:
            hints.append(
                "Someone said the Nightmare is gone. I hope that means fewer people wake screaming above the tavern."
            )
        if "Jester" in defeated_set:
            hints.append(
                "The Jester being gone should feel cleaner than it does. Grief has strange manners."
            )
    elif speaker == "Drunkard":
        if "Domingo" in defeated_set:
            hints.append(
                "Big magic egg thing gone, then? Good. Never trusted eggs with job titles. (hic)"
            )
        if "Merzhin" in defeated_set:
            hints.append(
                "If a realm can lie, can it apologize? No? Then I am still mad at it. (hic)"
            )
    elif speaker == "Hooded Figure":
        if "Red Dragon" in defeated_set:
            hints.append(
                "Dragonfire reveals what ordinary flame only burns away. You have been clarified."
            )
        if "Merzhin" in defeated_set:
            hints.append(
                "Merzhin mistook illusion for authorship. The difference matters more than he survived knowing."
            )
    return hints


def _quest_state_hints(player_char, speaker: str) -> list[str]:
    hints: list[str] = []
    if speaker == "Sergeant":
        if _completed_unturned_quest(player_char, "Side", "The Holy Grail of Quests"):
            hints.append(
                "The Chalice is found. Report to Nimue and do not waste the one advantage that realm has not learned to counterfeit."
            )
        if _active_quest(player_char, "Side", "The Wizard's Folly"):
            hints.append(
                "If Nimue opens Cambion for you, mark every portal and trust no straight corridor just because it looks honest."
            )
    elif speaker == "Soldier":
        if _active_quest(player_char, "Side", "The Wizard's Folly"):
            hints.append(
                "Cambion reports disagree on every route except one point: Merzhin wants you second-guessing before the first turn."
            )
    elif speaker == "Hooded Figure":
        if _active_quest(player_char, "Side", "The Wizard's Folly"):
            hints.append(
                "A false path is still a path. The question is who benefits when you believe it is the only one."
            )
    return hints


def _postgame_town_hints(player_char, speaker: str) -> list[str]:
    """Return non-mutating tavern fallout after the main story is complete."""
    main_story = getattr(player_char, "main_story", {})
    if not isinstance(main_story, dict) or not main_story.get("main_story_complete"):
        return []

    dialogue = {
        "Barkeep": [
            "You came back, and the work still needs doing. That is the strange mercy of ordinary days.",
            "The room is quieter without the busboy. We keep his place clear, though nobody remembers deciding to.",
        ],
        "Waitress": [
            "Joffrey should have lived to hear the ending. Some victories leave the chairs just as empty.",
            "People keep asking whether it is over. I tell them grief does not obey quest logs.",
        ],
        "Soldier": [
            "The patrol roster calls this peace. We still count everyone twice before closing the gate.",
            "You saved what could be saved. The rest of us have to learn how to live inside that answer.",
        ],
    }
    return dialogue.get(speaker, [])


def get_reactive_town_hints(player_char, speaker: str) -> list[str]:
    """Return repeatable town hints based on existing story and progression state."""
    hints = _postgame_town_hints(player_char, speaker)
    hints.extend(get_holy_grail_rotation_hints(player_char, speaker))
    hints.extend(_relic_progress_hints(_collected_relic_names(player_char), speaker))
    hints.extend(_boss_progress_hints(_defeated_boss_names(player_char), speaker))
    hints.extend(_quest_state_hints(player_char, speaker))
    return [hint for hint in hints if isinstance(hint, str) and hint.strip()]


def mark_bounty_board_restock(player_char):
    """Record the progress point used for the next intermittent restock."""
    player_char.bounty_board_state = {
        "initialized": True,
        "last_restock_level": _player_level(player_char),
        "last_restock_steps": _gameplay_stat(player_char, "steps_taken"),
        "last_restock_enemies_defeated": _gameplay_stat(
            player_char,
            "enemies_defeated",
        ),
    }
    return player_char.bounty_board_state


def should_restock_bounty_board(game, *, available_count=None):
    """Return whether the bounty board should refill at the current progress point."""
    player_char = game.player_char
    state = ensure_bounty_board_state(player_char)
    if available_count is None:
        available_count = len(getattr(game, "bounties", {}) or {})
    if active_bounty_count(player_char) >= MAX_ACTIVE_BOUNTIES or available_count > 0:
        return False
    if not state["initialized"]:
        return True

    current_level = _player_level(player_char)
    current_steps = _gameplay_stat(player_char, "steps_taken")
    current_defeats = _gameplay_stat(player_char, "enemies_defeated")

    return (
        current_level > state["last_restock_level"]
        or current_steps - state["last_restock_steps"] >= BOUNTY_RESTOCK_STEP_THRESHOLD
        or current_defeats - state["last_restock_enemies_defeated"]
        >= BOUNTY_RESTOCK_ENEMY_THRESHOLD
    )


# classes
class BountyBoard:
    MAX_ENEMY_ROLL_ATTEMPTS = 25

    def __init__(self):
        self.bounties = []

    def _existing_target_names(self, game):
        return set(game.player_char.quest_dict.get("Bounty", {})) | set(self.bounty_options())

    def _catalog_bounty_enemy(self, level, existing_names):
        catalog = enemies.random_enemy_candidates(level)
        candidates = [entry for entry in catalog if entry[0] not in existing_names]
        if not candidates:
            candidates = list(catalog)
        _name, enemy_factory = random.choice(candidates)
        return enemy_factory()

    def create_bounty(self, game):
        bounty = {"reward": None}
        level = str(min(6, game.player_char.player_level() // 10))
        existing_names = self._existing_target_names(game)
        enemy = None
        for _attempt in range(self.MAX_ENEMY_ROLL_ATTEMPTS):
            candidate = enemies.random_enemy(level)
            if candidate.name not in existing_names:
                enemy = candidate
                break
        if enemy is None:
            enemy = self._catalog_bounty_enemy(level, existing_names)
        bounty["enemy"] = enemy
        bounty["num"] = random.randint(3, 8)
        bounty["exp"] = random.randint(
            enemy.experience * bounty["num"] // 2,
            enemy.experience * bounty["num"],
        )
        bounty["gold"] = (
            random.randint(25 * bounty["num"], 50 * bounty["num"]) * game.player_char.player_level()
        )
        if random.randint(0, game.player_char.check_mod("luck", luck_factor=10)):
            global_level = game.player_char.player_level()
            item_band = min(8, 1 + ((global_level - 1) // 15))
            item_level = min(8, item_band + random.randint(0, item_band))
            bounty["reward"] = items.random_item(item_level)
        return bounty

    def generate_bounties(self, game):
        available_count = len(getattr(game, "bounties", {}) or {})
        active_count = active_bounty_count(game.player_char)
        if active_count >= MAX_ACTIVE_BOUNTIES or available_count > 0:
            state = ensure_bounty_board_state(game.player_char)
            if not state["initialized"]:
                mark_bounty_board_restock(game.player_char)
            return False
        if not should_restock_bounty_board(game, available_count=available_count):
            return False
        capacity = MAX_ACTIVE_BOUNTIES - active_count
        num = min(capacity, random.randint(1, MAX_ACTIVE_BOUNTIES))
        for _ in range(num):
            bounty = self.create_bounty(game)
            self.bounties.append(bounty)
        if self.bounties:
            mark_bounty_board_restock(game.player_char)
            return True
        return False

    def bounty_options(self):
        options = []
        for bounty in self.bounties:
            if "name" in bounty:
                options.append(bounty["name"])
                continue
            enemy = bounty.get("enemy")
            enemy_name = getattr(enemy, "name", None)
            if enemy_name:
                options.append(enemy_name)
        return options

    def accept_quest(self, quest):
        quest_idx = self.bounties.index(quest)
        self.bounties.pop(quest_idx)


# quest dict - loaded from external JSON file
# Using lazy loading to defer resolution of item classes until needed
_quest_dict_cache = None


def get_quest_dict():
    """Lazy load quests from JSON data file."""
    global _quest_dict_cache
    if _quest_dict_cache is None:
        _quest_dict_cache = get_quests()
    return _quest_dict_cache


def get_holy_grail_rotation_hints(player_char, speaker: str) -> list[str]:
    """Return repeatable Holy Grail progression hints for non-quest-giver dialogue rotation."""
    quest_data = player_char.quest_dict.get("Side", {}).get("The Holy Grail of Quests")
    if not quest_data or quest_data.get("Completed") or quest_data.get("Turned In"):
        return []

    progress = quest_data.setdefault("Chalice Progress", {})
    for key in ("Hooded", "Map", "Sergeant", "Adventurer", "Revealed", "Spawned"):
        progress.setdefault(key, False)

    hints: list[str] = []
    if speaker == "Hooded Figure" and progress.get("Hooded") and not progress.get("Map"):
        hints.append(
            "The Hooded Figure murmurs that a map to the Golden Chalice was last seen with an adventurer carrying an ugly sword."
        )
        hints.append("Revisit the boulder where you found Excaliper; the map may be hidden there.")

    if speaker == "Sergeant" and (
        progress.get("Map") or "Chalice Map" in player_char.special_inventory
    ):
        if not progress.get("Adventurer"):
            hints.append(
                "The Sergeant studies your map and mutters, 'There's a hidden route somewhere on the third floor. Find the adventurer there.'"
            )
            hints.append(
                "Search the third floor for a secret path; an adventurer there can help you decipher the map."
            )
        elif not progress.get("Revealed"):
            hints.append(
                "The Sergeant says the hidden adventurer's trick should make the ink emerge if you inspect the Chalice Map carefully."
            )
            hints.append(
                "Inspect the Chalice Map from your Key Items to reveal the hidden altar location."
            )
        else:
            hints.append(
                "The Sergeant nods. 'The map marks somewhere on the sixth floor. Go claim the Golden Chalice.'"
            )

    return hints


# For backward compatibility, create module-level variable
quest_dict = get_quest_dict()

# Note: The quest_dict has been moved to src/data/content/quests.json
# This module uses get_quests() from data_loader to load it with resolved item references
