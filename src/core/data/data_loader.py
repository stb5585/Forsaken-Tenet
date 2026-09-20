"""
Data loader utility for loading JSON game data files.
"""

from __future__ import annotations

import json
from copy import deepcopy
from typing import TYPE_CHECKING

from src.paths import CORE_DATA_DIR

if TYPE_CHECKING:
    from typing import Any


CONTENT_DIR = CORE_DATA_DIR / "content"
# Cache for loaded data to avoid repeated file reads
_data_cache: dict[str, Any] = {}


def load_json_data(filename: str, cache: bool = True) -> dict[str, Any]:
    """
    Load JSON data from the data directory.

    Args:
        filename: Name of the JSON file (e.g., 'special_events.json')
        cache: Whether to cache the loaded data (default: True)
    dict
    Returns:
        Dictionary containing the loaded JSON data

    Raises:
        FileNotFoundError: If the JSON file doesn't exist
        json.JSONDecodeError: If the JSON file is invalid
    """
    if cache and filename in _data_cache:
        return _data_cache[filename]

    # Get the data directory path (relative to this file)
    file_path = CONTENT_DIR / filename

    if not file_path.exists():
        raise FileNotFoundError(f"Data file not found: {file_path}")

    with open(file_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    if cache:
        _data_cache[filename] = data

    return data


def get_special_events() -> dict[str, Any]:
    """
    Load and return the special events dictionary.

    Returns:
        Dictionary containing all special event data
    """
    return load_json_data("special_events.json")


def get_intro_story() -> list[str]:
    """
    Load and return the shared new-game intro story pages.

    Returns:
        Ordered story pages for UI-specific intro presentation
    """
    intro_data = get_special_events().get("Intro", {})
    pages = intro_data.get("Text", [])
    if not isinstance(pages, list):
        return []
    return [str(page) for page in pages]


def get_quests() -> dict[str, Any]:
    """
    Load and return the quests dictionary with resolved item references.

    Returns:
        Dictionary containing all quest data with item references resolved
    """
    from .. import items  # Import here to avoid circular imports

    # Item mapping: string name -> item class
    item_map = {
        # Potions
        "HealthPotion": items.HealthPotion,
        "GreatHealthPotion": items.GreatHealthPotion,
        "SuperHealthPotion": items.SuperHealthPotion,
        "MasterHealthPotion": items.MasterHealthPotion,
        "ManaPotion": items.ManaPotion,
        "GreatManaPotion": items.GreatManaPotion,
        "SuperManaPotion": items.SuperManaPotion,
        "MasterManaPotion": items.MasterManaPotion,
        "Elixir": items.Elixir,
        "HPPotion": items.HPPotion,
        "MPPotion": items.MPPotion,
        "StrengthPotion": items.StrengthPotion,
        "IntelPotion": items.IntelPotion,
        "WisdomPotion": items.WisdomPotion,
        "ConPotion": items.ConPotion,
        "CharismaPotion": items.CharismaPotion,
        "DexterityPotion": items.DexterityPotion,
        "AardBeing": items.AardBeing,
        "Antidote": items.Antidote,
        "Remedy": items.Remedy,
        "Megalixir": items.Megalixir,
        # Accessories
        "EvasionRing": items.EvasionRing,
        "PowerRing": items.PowerRing,
        "ClassRing": items.ClassRing,
        "GorgonPendant": items.GorgonPendant,
        "ElementalChain": items.ElementalChain,
        "FireAmulet": items.FireAmulet,
        "IceAmulet": items.IceAmulet,
        "ElectricAmulet": items.ElectricAmulet,
        "WaterAmulet": items.WaterAmulet,
        "EarthAmulet": items.EarthAmulet,
        "WindAmulet": items.WindAmulet,
        # Keys and Miscellaneous
        "OldKey": items.OldKey,
        "CrypticKey": items.CrypticKey,
        "UltimaScepter": items.UltimaScepter,
        # Unique Items
        "MedusaShield": items.MedusaShield,
        "Magus": items.Magus,
        "RainbowRod": items.RainbowRod,
        # Special items (resolved as strings, not classes)
        "Gold": "Gold",
        "Power Up": "Power Up",
        "Warp Point": "Warp Point",
        "Izulu": "Izulu",
        "Spell Upgrade": "Spell Upgrade",
    }

    # Reward resolution replaces JSON strings with runtime classes. Keep the
    # cached raw document immutable so other callers cannot observe compiled
    # quest state or mutate future reads through the shared cache.
    quests_data = deepcopy(load_json_data("quests.json"))

    # Resolve reward strings to item classes
    def resolve_rewards(reward_list):
        """Convert string reward identifiers to item classes."""
        resolved = []
        for reward_str in reward_list:
            if reward_str in item_map:
                resolved.append(item_map[reward_str])
            else:
                # Log warning but continue - might be a special string
                resolved.append(reward_str)
        return resolved

    # Recursively traverse quest structure and resolve rewards
    def process_quests(quests_dict):
        for quest_types in quests_dict.values():
            for quest_levels in quest_types.values():
                for quest_dict_inner in quest_levels.values():
                    for quest_data in quest_dict_inner.values():
                        if "Reward" in quest_data:
                            quest_data["Reward"] = resolve_rewards(quest_data["Reward"])
        return quests_dict

    return process_quests(quests_data)


def get_patron_dialogues() -> dict[str, Any]:
    """
    Load and return the patron dialogues dictionary.

    Returns:
        Dictionary with NPC names mapping to level-keyed (int) dialogue lists
    """
    dialogues_data = load_json_data("dialogues.json")
    patron_dialogues = dialogues_data["patron_dialogues"]

    # Convert string keys to integers for level comparison
    converted = {}
    for npc_name, levels_dict in patron_dialogues.items():
        converted[npc_name] = {int(level): dialogues for level, dialogues in levels_dict.items()}

    return converted


def get_response_map() -> dict[str, Any]:
    """
    Load and return the NPC response map for quest acceptance/rejection.

    Returns:
        Dictionary with NPC names mapping to [accept_response, reject_response]
    """
    dialogues_data = load_json_data("dialogues.json")
    return dialogues_data["response_map"]


def get_tavern_flavor_dialogues() -> list[str]:
    """
    Load and return the tavern flavor dialogue lines.

    Returns:
        List of ambient dialogue strings
    """
    dialogues_data = load_json_data("dialogues.json")
    return dialogues_data["tavern_flavor_dialogues"]


def clear_cache():
    """Clear the data cache. Useful for testing or reloading data."""
    _data_cache.clear()
