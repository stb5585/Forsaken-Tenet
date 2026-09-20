#!/usr/bin/env python3
"""Coverage for shared story content loaded from core data."""

from copy import deepcopy

from src.core import main_story
from src.core.data.data_loader import (
    clear_cache,
    get_intro_story,
    get_quests,
    get_special_events,
    load_json_data,
)


def test_new_game_intro_story_content_is_shared_and_spoiler_safe():
    clear_cache()

    pages = get_intro_story()
    intro_text = "\n".join(pages)

    assert len(pages) == 6
    for expected in ("Silvana", "relics", "guardians", "Step below"):
        assert expected in intro_text
    for spoiler in ("Vesperion", "Voluntas", "busboy", "Hooded Figure", "true final"):
        assert spoiler not in intro_text


def test_quest_resolution_does_not_mutate_cached_raw_json():
    """Compiling quest rewards must not leak runtime classes into the JSON cache."""
    clear_cache()
    raw_quests = load_json_data("quests.json")
    original = deepcopy(raw_quests)

    get_quests()

    assert load_json_data("quests.json") == original


def test_story_polish_content_keys_are_present_and_spoiler_scoped():
    clear_cache()

    events = get_special_events()
    required_keys = (
        "Triangulus Trial Defeat",
        "Infinitas Trial Defeat",
        "Reflection Prelude Martial",
        "Reflection Prelude Mystic",
        "Reflection Prelude Hybrid",
        "Reflection Victory Martial",
        "Reflection Victory Mystic",
        "Reflection Victory Hybrid",
        "Reflection Defeat Martial",
        "Reflection Defeat Mystic",
        "Reflection Defeat Hybrid",
        "Hooded Figure Angelic Confirmation",
        "Class Voluntas Affirmation",
        "Class Voluntas Dormant Ring",
        "Class Voluntas Awakened Ring",
        "Class Voluntas Reflection Echo",
        "Class Voluntas Archetype Martial",
        "Class Voluntas Archetype Mystic",
        "Class Voluntas Archetype Hybrid",
        "Class Voluntas Archetype Companion",
        "Class Voluntas Archetype Shadow",
        "Class Voluntas Archetype Wanderer",
        "Class Voluntas Followup",
        "Class Voluntas Followup Martial",
        "Class Voluntas Followup Mystic",
        "Class Voluntas Followup Hybrid",
        "Class Voluntas Followup Companion",
        "Class Voluntas Followup Shadow",
        "Class Voluntas Followup Wanderer",
        "Class Voluntas Bridge",
        "Class Voluntas Bridge Wanderer",
        "Reflection Voluntas Choice Claim",
        "Reflection Voluntas Choice Carry",
        "Reflection Voluntas Choice Choose Again",
        "Reflection Voluntas Retry",
        "Reflection Voluntas Victory Echo",
        "Reflection Path Mirror",
        "Reflection Path Victory Echo",
        "Hooded Figure Witness Farewell",
        "Vesperion Choice Argument",
        "Vesperion Tragedy Reframing",
        "Vesperion True Final Victory",
    )
    for key in required_keys:
        assert events.get(key, {}).get("Text"), key
    for class_name in main_story.CLASS_VOLUNTAS_BRIDGE_CLASSES:
        key = main_story.class_voluntas_bridge_event_key(class_name)
        assert events.get(key, {}).get("Text"), key

    for guardian, choices in main_story.GUARDIAN_TRIAL_CHOICES.items():
        assert events.get(f"{guardian} Trial V2 Threshold", {}).get("Text"), guardian
        for choice in choices:
            key = f"{guardian} Trial V2 {choice}"
            assert events.get(key, {}).get("Text"), key
    assert events.get("Liminal Trial V2 Review", {}).get("Text")

    early_tragedy_text = "\n".join(
        line
        for key in ("Dead Body", "Waitress", "Joffrey's Key", "Busboy")
        for line in events[key]["Text"]
    )
    for spoiler in ("Vesperion", "Voluntas", "true final"):
        assert spoiler not in early_tragedy_text
    assert "grief" in early_tragedy_text
    assert "Joffrey" in early_tragedy_text

    endgame_tragedy_text = "\n".join(events["Vesperion Tragedy Reframing"]["Text"])
    assert "Vesperion" in endgame_tragedy_text
    assert "Joffrey" in endgame_tragedy_text
    assert "Waitress" in endgame_tragedy_text

    ending_text = "\n".join(
        line
        for key in (
            "Vesperion True Final Victory",
            "The Forsaken Tenet Ending",
            "The Thirsty Dog Epilogue",
        )
        for line in events[key]["Text"]
    )
    assert "The final chamber does not crown you" in ending_text
    assert "ordinary work" in ending_text


def test_red_dragon_continuity_copy_separates_route_meanings():
    clear_cache()

    events = get_special_events()
    red_dragon_text = "\n".join(events["Red Dragon"]["Text"])
    zahhak_text = "\n".join(events["Zahhak"]["Text"])
    dracarys = get_quests()["Hooded Figure"]["Main"]["60"]["Dracarys"]
    dracarys_text = "\n".join(dracarys[field] for field in ("Start Text", "End Text", "Help Text"))

    assert "Whatever truths the dragon carries" in red_dragon_text
    assert "not Kaelenon's restored self" in zahhak_text
    assert "draconic spirit" in zahhak_text
    assert "progression victory is complete for every hero" in dracarys_text
    for legacy_final_boss_framing in ("ultimate challenge...me", "futility", "my wrath"):
        assert legacy_final_boss_framing not in dracarys_text
