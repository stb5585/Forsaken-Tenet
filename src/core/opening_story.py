"""Rules and persistent state transitions for Silvana's opening story slice."""

from __future__ import annotations

from copy import deepcopy

ARRIVAL_MOTIVES = ("Fortune", "Service", "Knowledge", "Reinvention")
ARRIVAL_AID_CHOICES = ("ClearSpace", "SteadySurvivor", "RememberAccount", "FetchHelp")
TRIANGULUS_IDENTITY_ANSWERS = ("ChosenName", "Deeds", "Memory", "NextChoice")
MIGRATED_CHOICE = "Unrecorded"

OPENING_STATE_DEFAULTS: dict[str, object] = {
    "arrival_scene_seen": False,
    "arrival_motive": None,
    "arrival_aid": None,
    "hooded_figure_observed": False,
    "opening_ledger_seen": False,
    "dungeon_entry_story_seen": False,
    "first_descent_story_seen": False,
    "joffrey_tavern_scene_seen": False,
    "joffrey_patrol_briefing_seen": False,
    "joffrey_route_review_seen": False,
    "opening_patrol_fate_seen": False,
    "acolyte_triangulus_fragment_seen": False,
    "triangulus_identity_answer": None,
    "first_relic_tavern_aftermath_seen": False,
    "hooded_figure_triangulus_response_seen": False,
}

FIRST_DESCENT_POSITION = (3, 0, 1)
FIRST_DUNGEON_ENTRY_TEXT = (
    "The opened stair lies below the last town lantern. Behind you, Silvana keeps its fires "
    "lit. Ahead, the steps vanish into the dark.\n\n"
    "You begin the descent. Return with answers, if the dark allows it."
)
FIRST_DESCENT_TEXT = (
    "The worked stone nearest Silvana bears recent tool marks and drainage cuts. "
    "Beneath them, an older arch continues into masonry no town ledger claims."
)

PATROL_FATE_TEXT = (
    "Beneath fallen stone lies Tomas Reed, identified by his patrol clasp. Mira Venn is "
    "not here. Her chalk route marks continue beyond Tomas, cross the threshold, and end "
    "without a body or a clear return path.\n\n"
    "A weathered note waits beside the threshold:\n\n"
    '"I wrote my name beside every turn so the dark could not take it. At the seventh mark, '
    "the letters were mine but the hand was not. A name is proof only while someone still "
    'chooses to answer to it."'
)


def normalize_opening_fields(state: dict[str, object]) -> None:
    """Normalize opening fields in an already-created main-story state."""
    for key, default in OPENING_STATE_DEFAULTS.items():
        if key in {"arrival_motive", "arrival_aid", "triangulus_identity_answer"}:
            continue
        state[key] = bool(state.get(key, default))

    state["arrival_motive"] = _choice_or_none(state.get("arrival_motive"), ARRIVAL_MOTIVES)
    state["arrival_aid"] = _choice_or_none(state.get("arrival_aid"), ARRIVAL_AID_CHOICES)
    state["triangulus_identity_answer"] = _choice_or_none(
        state.get("triangulus_identity_answer"), TRIANGULUS_IDENTITY_ANSWERS
    )


def _choice_or_none(value: object, allowed: tuple[str, ...]) -> str | None:
    if value in (*allowed, MIGRATED_CHOICE):
        return str(value)
    return None


def record_arrival(state: dict[str, object], motive: str, aid: str) -> bool:
    """Record the two opening choices once both values are valid."""
    if motive not in ARRIVAL_MOTIVES or aid not in ARRIVAL_AID_CHOICES:
        return False
    state["arrival_motive"] = motive
    state["arrival_aid"] = aid
    state["arrival_scene_seen"] = True
    state["joffrey_tavern_scene_seen"] = True
    state["hooded_figure_observed"] = True
    return True


def record_ledger_review(state: dict[str, object]) -> None:
    """Mark all three opening patrol-ledger entries as reviewed."""
    state["opening_ledger_seen"] = True
    state["joffrey_patrol_briefing_seen"] = True


def record_first_descent(state: dict[str, object], position: tuple[int, int, int]) -> str:
    """Return the one-time layered-construction observation at the first descent."""
    if tuple(position) != FIRST_DESCENT_POSITION or state.get("first_descent_story_seen"):
        return ""
    state["first_descent_story_seen"] = True
    return FIRST_DESCENT_TEXT


def record_dungeon_entry_story(state: dict[str, object]) -> bool:
    """Mark the one-time illustrated transition into the dungeon."""
    if state.get("dungeon_entry_story_seen"):
        return False
    state["dungeon_entry_story_seen"] = True
    return True


def should_show_route_review(state: dict[str, object]) -> bool:
    """Return whether the first post-ledger route review is ready."""
    return bool(
        state.get("opening_ledger_seen")
        and state.get("first_descent_story_seen")
        and not state.get("joffrey_route_review_seen")
    )


def record_triangulus_threshold(state: dict[str, object]) -> bool:
    """Record Tomas's fate and the anonymous threshold fragment once."""
    if state.get("opening_patrol_fate_seen") and state.get("acolyte_triangulus_fragment_seen"):
        return False
    state["opening_patrol_fate_seen"] = True
    state["acolyte_triangulus_fragment_seen"] = True
    return True


def record_triangulus_answer(state: dict[str, object], answer: str) -> bool:
    """Persist one valid, mechanically neutral Triangulus identity answer."""
    if answer not in TRIANGULUS_IDENTITY_ANSWERS:
        return False
    state["triangulus_identity_answer"] = answer
    return True


def migrate_loaded_state(
    state: dict[str, object], raw_state: object, *, quest_dict: object, special_inventory: object
) -> None:
    """Backfill opening state for saves created before this slice existed."""
    saved = raw_state if isinstance(raw_state, dict) else {}
    if any(key in saved for key in OPENING_STATE_DEFAULTS):
        if "dungeon_entry_story_seen" not in saved:
            state["dungeon_entry_story_seen"] = True
        return

    state.update(
        {
            "arrival_scene_seen": True,
            "arrival_motive": MIGRATED_CHOICE,
            "arrival_aid": MIGRATED_CHOICE,
            "hooded_figure_observed": True,
            "joffrey_tavern_scene_seen": True,
            "dungeon_entry_story_seen": True,
        }
    )
    quests = quest_dict if isinstance(quest_dict, dict) else {}
    main_quests = quests.get("Main", {}) if isinstance(quests.get("Main", {}), dict) else {}
    uncertain = main_quests.get("Uncertain Reports")
    holy = main_quests.get("The Holy Relics")
    inventory = special_inventory if isinstance(special_inventory, dict) else {}

    if isinstance(uncertain, dict) or isinstance(holy, dict):
        record_ledger_review(state)
        state["joffrey_route_review_seen"] = True
    if isinstance(uncertain, dict) and uncertain.get("Stage") == "report_first_relic":
        record_triangulus_threshold(state)
        state["triangulus_identity_answer"] = MIGRATED_CHOICE
    if "Triangulus" in inventory:
        record_triangulus_threshold(state)
        state["triangulus_identity_answer"] = MIGRATED_CHOICE
    if isinstance(holy, dict):
        state["joffrey_patrol_briefing_seen"] = True
        state["joffrey_route_review_seen"] = True
        state["first_relic_tavern_aftermath_seen"] = True


def copied_defaults() -> dict[str, object]:
    """Return independent opening defaults for composition into main-story state."""
    return deepcopy(OPENING_STATE_DEFAULTS)
