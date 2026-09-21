"""Canonical identities for authored quests."""

from __future__ import annotations

from ..data.data_loader import load_json_data
from ..identity import canonical_slug


def _authored_quest_names() -> set[str]:
    names: set[str] = set()
    document = load_json_data("quests.json")
    for giver_data in document.values():
        if not isinstance(giver_data, dict):
            continue
        for category in ("Main", "Side"):
            levels = giver_data.get(category, {})
            if not isinstance(levels, dict):
                continue
            for quests in levels.values():
                if isinstance(quests, dict):
                    names.update(str(name) for name in quests)
    return names


QUEST_NAMES_BY_ID = {canonical_slug(name): name for name in _authored_quest_names()}
QUEST_IDS_BY_NAME = {name: quest_id for quest_id, name in QUEST_NAMES_BY_ID.items()}

if len(QUEST_NAMES_BY_ID) != len(QUEST_IDS_BY_NAME):
    raise ValueError("authored quest names do not have unique canonical IDs")
