"""Regression coverage for main-story progression state."""

from __future__ import annotations

from src.core import main_story, opening_story
from src.core.player import LIMINAL_GAP_ENTRY_FACING, LIMINAL_GAP_ENTRY_POS, LIMINAL_GAP_LEVEL
from src.core.save_system import PlayerDataSerializer
from tests.test_framework import TestGameState


def test_new_players_initialize_main_story_defaults():
    player = TestGameState.create_player()

    assert player.ensure_main_story_state() == main_story.default_state()
    assert player.can_enter_true_final() is False


def test_opening_choices_normalize_only_documented_values():
    state = main_story.normalize_state(
        {
            "arrival_motive": "Knowledge",
            "arrival_aid": "FetchHelp",
            "triangulus_identity_answer": "Memory",
        }
    )

    assert state["arrival_motive"] == "Knowledge"
    assert state["arrival_aid"] == "FetchHelp"
    assert state["triangulus_identity_answer"] == "Memory"
    invalid = main_story.normalize_state(
        {
            "arrival_motive": "Power",
            "arrival_aid": "Ignore",
            "triangulus_identity_answer": "CorrectAnswer",
        }
    )
    assert invalid["arrival_motive"] is None
    assert invalid["arrival_aid"] is None
    assert invalid["triangulus_identity_answer"] is None


def test_legacy_player_save_skips_new_opening_scenes_with_unrecorded_choices():
    player = TestGameState.create_player()
    data = PlayerDataSerializer.serialize(player)
    data.pop("main_story")

    loaded = PlayerDataSerializer.deserialize(data, skip_tiles=True)

    state = loaded.ensure_main_story_state()
    assert state["arrival_scene_seen"] is True
    assert state["joffrey_tavern_scene_seen"] is True
    assert state["arrival_motive"] == opening_story.MIGRATED_CHOICE
    assert state["arrival_aid"] == opening_story.MIGRATED_CHOICE
    assert state["dungeon_entry_story_seen"] is True
    assert state["vesperion_false_final_triggered"] is False


def test_legacy_triangulus_save_backfills_threshold_without_replaying_it():
    player = TestGameState.create_player()
    raw_state = {
        key: value
        for key, value in main_story.default_state().items()
        if key not in opening_story.OPENING_STATE_DEFAULTS
    }
    state = main_story.normalize_state(raw_state)

    opening_story.migrate_loaded_state(
        state,
        raw_state,
        quest_dict={
            "Main": {
                "Uncertain Reports": {
                    "Stage": "report_first_relic",
                    "Completed": True,
                }
            }
        },
        special_inventory={"Triangulus": [object()]},
    )

    assert state["opening_ledger_seen"] is True
    assert state["opening_patrol_fate_seen"] is True
    assert state["acolyte_triangulus_fragment_seen"] is True
    assert state["triangulus_identity_answer"] == opening_story.MIGRATED_CHOICE


def test_existing_opening_save_backfills_dungeon_entry_transition_as_seen():
    raw_state = main_story.default_state()
    raw_state.pop("dungeon_entry_story_seen")
    state = main_story.normalize_state(raw_state)

    opening_story.migrate_loaded_state(
        state,
        raw_state,
        quest_dict={"Main": {}},
        special_inventory={},
    )

    assert state["dungeon_entry_story_seen"] is True
    assert state["first_descent_story_seen"] is False


def test_main_story_round_trips_through_player_serializer():
    player = TestGameState.create_player()
    player.main_story["dungeon_entry_story_seen"] = True
    player.main_story["vesperion_false_final_triggered"] = True
    player.main_story["liminal_gap_entered"] = True
    player.main_story["voluntas_revealed"] = True
    player.main_story["seventh_seat_revealed"] = True
    player.main_story["acolyte_liminal_seen"] = True
    player.main_story["reflection_defeated"] = True
    player.main_story["returned_from_liminal_gap"] = True
    player.main_story["hooded_figure_witness_revealed"] = True
    player.main_story["hooded_figure_angelic_confirmed"] = True
    player.main_story["liminal_gap_guide_revealed"] = True
    player.main_story["liminal_gap_clues_reviewed"] = True
    player.main_story["reflection_attempts"] = 2
    player.main_story["reflection_failures"] = 1
    player.main_story["vesperion_true_final_defeated"] = True
    player.main_story["main_story_complete"] = True
    player.main_story["class_voluntas_affirmed"] = True
    player.main_story["class_voluntas_affirmed_class"] = "Wizard"
    player.main_story["class_voluntas_affirmed_ring_awakened"] = True
    player.main_story["class_voluntas_affirmed_archetype"] = "mystic"
    player.main_story["reflection_voluntas_answer"] = "Carry"
    player.main_story["hooded_figure_witness_farewell_seen"] = True
    player.main_story["class_voluntas_followup_seen"] = True
    player.main_story["class_voluntas_bridge_seen"] = True
    player.main_story["reflection_path_mirror_seen"] = True
    player.main_story["vesperion_choice_argument_seen"] = True
    player.main_story["guardian_trial_vignettes_seen"]["Triangulus"] = True
    player.main_story["guardian_trial_vignettes_seen"]["Luna"] = True
    player.main_story["liminal_trial_v2_reviewed"] = True
    player.main_story["guardian_trials_completed"]["Triangulus"] = True
    player.main_story["guardian_trials_started"]["Triangulus"] = True
    player.main_story["guardian_trial_choices"]["Triangulus"] = "Memory"
    player.main_story["voluntas_clues_found"]["Triangulus"] = True
    player.main_story["guardian_trials_completed"]["Quadrata"] = True
    player.main_story["guardian_trials_started"]["Quadrata"] = True
    player.main_story["guardian_trial_choices"]["Quadrata"] = "Rewrite"
    player.main_story["voluntas_clues_found"]["Quadrata"] = True
    player.main_story["guardian_trial_choices"]["Hexagonum"] = "not-a-valid-choice"
    player.liminal_gap_return = (7, 8, 6, "south")

    loaded = PlayerDataSerializer.deserialize(
        PlayerDataSerializer.serialize(player), skip_tiles=True
    )

    assert loaded.main_story["vesperion_false_final_triggered"] is True
    assert loaded.main_story["dungeon_entry_story_seen"] is True
    assert loaded.main_story["liminal_gap_entered"] is True
    assert loaded.main_story["voluntas_revealed"] is True
    assert loaded.main_story["seventh_seat_revealed"] is True
    assert loaded.main_story["acolyte_liminal_seen"] is True
    assert loaded.main_story["reflection_defeated"] is True
    assert loaded.main_story["returned_from_liminal_gap"] is True
    assert loaded.main_story["hooded_figure_witness_revealed"] is True
    assert loaded.main_story["hooded_figure_angelic_confirmed"] is True
    assert loaded.main_story["liminal_gap_guide_revealed"] is True
    assert loaded.main_story["liminal_gap_clues_reviewed"] is True
    assert loaded.main_story["reflection_attempts"] == 2
    assert loaded.main_story["reflection_failures"] == 1
    assert loaded.main_story["vesperion_true_final_defeated"] is True
    assert loaded.main_story["main_story_complete"] is True
    assert loaded.main_story["class_voluntas_affirmed"] is True
    assert loaded.main_story["class_voluntas_affirmed_class"] == "Wizard"
    assert loaded.main_story["class_voluntas_affirmed_ring_awakened"] is True
    assert loaded.main_story["class_voluntas_affirmed_archetype"] == "mystic"
    assert loaded.main_story["reflection_voluntas_answer"] == "Carry"
    assert loaded.main_story["hooded_figure_witness_farewell_seen"] is True
    assert loaded.main_story["class_voluntas_followup_seen"] is True
    assert loaded.main_story["class_voluntas_bridge_seen"] is True
    assert loaded.main_story["reflection_path_mirror_seen"] is True
    assert loaded.main_story["vesperion_choice_argument_seen"] is True
    assert loaded.main_story["guardian_trial_vignettes_seen"]["Triangulus"] is True
    assert loaded.main_story["guardian_trial_vignettes_seen"]["Luna"] is True
    assert loaded.main_story["guardian_trial_vignettes_seen"]["Quadrata"] is False
    assert loaded.main_story["liminal_trial_v2_reviewed"] is True
    assert loaded.main_story["guardian_trials_completed"]["Triangulus"] is True
    assert loaded.main_story["guardian_trials_completed"]["Quadrata"] is True
    assert loaded.main_story["guardian_trials_started"]["Triangulus"] is True
    assert loaded.main_story["guardian_trials_started"]["Quadrata"] is True
    assert loaded.main_story["guardian_trial_choices"]["Triangulus"] == "Memory"
    assert loaded.main_story["guardian_trial_choices"]["Quadrata"] == "Rewrite"
    assert loaded.main_story["guardian_trial_choices"]["Hexagonum"] is None
    assert loaded.main_story["voluntas_clues_found"]["Triangulus"] is True
    assert loaded.main_story["voluntas_clues_found"]["Quadrata"] is True
    assert loaded.main_story["true_final_unlocked"] is False
    assert loaded.liminal_gap_return == (7, 8, 6, "south")


def test_guardian_trial_definitions_validate_choices_and_completion():
    state = main_story.default_state()

    assert set(main_story.GUARDIAN_TRIAL_DEFINITIONS) == set(main_story.GUARDIAN_TRIALS)
    assert main_story.guardian_trial_definition("Triangulus")["kind"] == "combat"
    assert main_story.guardian_trial_definition("Infinitas")["kind"] == "combat"
    assert main_story.guardian_trial_question("Polaris") == "How do you follow guidance?"
    assert main_story.guardian_trial_event("Triangulus", "Memory") == "Triangulus Trial Memory"
    assert (
        main_story.guardian_trial_event("Infinitas", event="defeat_event")
        == "Infinitas Trial Defeat"
    )
    assert main_story.record_guardian_trial_completion(state, "Triangulus", "Memory") is True
    assert state["guardian_trials_started"]["Triangulus"] is True
    assert state["guardian_trials_completed"]["Triangulus"] is True
    assert state["guardian_trial_choices"]["Triangulus"] == "Memory"
    assert state["voluntas_clues_found"]["Triangulus"] is True
    assert main_story.record_guardian_trial_completion(state, "Triangulus", "Wrong") is False


def test_guardian_trial_vignettes_default_normalize_and_summarize():
    state = main_story.default_state()

    assert state["guardian_trial_vignettes_seen"] == {
        guardian: False for guardian in main_story.GUARDIAN_TRIALS
    }
    assert state["liminal_trial_v2_reviewed"] is False
    assert main_story.guardian_trial_vignette_seen(state, "Triangulus") is False
    assert main_story.guardian_trial_vignette_seen(state, "Voluntas") is False
    assert main_story.record_guardian_trial_vignette(state, "Voluntas") is False

    assert main_story.record_guardian_trial_vignette(state, "Triangulus") is True
    assert main_story.record_guardian_trial_vignette(state, "Triangulus") is False
    assert main_story.guardian_trial_vignette_seen(state, "Triangulus") is True
    assert main_story.completed_guardian_vignette_count(state) == 1

    state["guardian_trial_choices"]["Triangulus"] = "Memory"
    assert main_story.guardian_vignette_summary(state) == [
        "Triangulus (Memory): identity chosen through name, body, and memory.",
    ]

    normalized = main_story.normalize_state(
        {
            "guardian_trial_vignettes_seen": {
                "Triangulus": True,
                "Luna": 1,
                "NotAGuardian": True,
            },
            "guardian_trial_choices": {
                "Triangulus": "Name",
                "Luna": "Release",
                "Polaris": "NotAChoice",
            },
            "liminal_trial_v2_reviewed": True,
        }
    )

    assert normalized["guardian_trial_vignettes_seen"]["Triangulus"] is True
    assert normalized["guardian_trial_vignettes_seen"]["Luna"] is True
    assert normalized["guardian_trial_vignettes_seen"]["Quadrata"] is False
    assert normalized["guardian_trial_choices"]["Polaris"] is None
    assert normalized["liminal_trial_v2_reviewed"] is True
    assert main_story.completed_guardian_vignette_count(normalized) == 2
    assert main_story.guardian_vignette_summary(normalized) == [
        "Triangulus (Name): identity chosen through name, body, and memory.",
        "Luna (Release): love protects, releases, or shares without possession.",
    ]


def test_hooded_figure_angelic_confirmation_gate():
    state = main_story.default_state()

    assert main_story.should_confirm_hooded_figure_angelic(state) is False
    state["reflection_defeated"] = True
    state["hooded_figure_witness_revealed"] = True
    assert main_story.should_confirm_hooded_figure_angelic(state) is True
    state["hooded_figure_angelic_confirmed"] = True
    assert main_story.should_confirm_hooded_figure_angelic(state) is False


def test_class_voluntas_affirmation_defaults_normalize_and_record_once():
    state = main_story.default_state()

    assert state["class_voluntas_affirmed"] is False
    assert state["class_voluntas_affirmed_class"] is None
    assert state["class_voluntas_affirmed_ring_awakened"] is False
    assert state["class_voluntas_affirmed_archetype"] is None
    assert main_story.record_class_voluntas_affirmation(state, "", True) is False

    assert main_story.record_class_voluntas_affirmation(state, "Wizard", True) is True
    assert state["class_voluntas_affirmed"] is True
    assert state["class_voluntas_affirmed_class"] == "Wizard"
    assert state["class_voluntas_affirmed_ring_awakened"] is True
    assert state["class_voluntas_affirmed_archetype"] == "mystic"
    assert main_story.record_class_voluntas_affirmation(state, "Berserker", False) is False
    assert state["class_voluntas_affirmed_class"] == "Wizard"

    normalized = main_story.normalize_state(
        {
            "class_voluntas_affirmed": True,
            "class_voluntas_affirmed_class": "  Knight Enchanter  ",
            "class_voluntas_affirmed_ring_awakened": True,
            "class_voluntas_affirmed_archetype": "hybrid",
            "reflection_voluntas_answer": "ChooseAgain",
            "hooded_figure_witness_farewell_seen": True,
        }
    )

    assert normalized["class_voluntas_affirmed"] is True
    assert normalized["class_voluntas_affirmed_class"] == "Knight Enchanter"
    assert normalized["class_voluntas_affirmed_ring_awakened"] is True
    assert normalized["class_voluntas_affirmed_archetype"] == "hybrid"
    assert normalized["reflection_voluntas_answer"] == "ChooseAgain"
    assert normalized["hooded_figure_witness_farewell_seen"] is True

    invalid = main_story.normalize_state(
        {
            "class_voluntas_affirmed_archetype": "not-real",
            "reflection_voluntas_answer": "RewriteSelf",
        }
    )

    assert invalid["class_voluntas_affirmed_archetype"] is None
    assert invalid["reflection_voluntas_answer"] is None

    old_affirmed = main_story.normalize_state(
        {
            "class_voluntas_affirmed": True,
            "class_voluntas_affirmed_class": "Soulcatcher",
        }
    )

    assert old_affirmed["class_voluntas_affirmed_archetype"] == "shadow"


def test_class_voluntas_archetypes_reflection_answer_and_witness_farewell_gate():
    assert main_story.class_voluntas_archetype("Berserker") == "martial"
    assert main_story.class_voluntas_archetype("Grandmaster of Arms") == "martial"
    assert main_story.class_voluntas_archetype("Wizard") == "mystic"
    assert main_story.class_voluntas_archetype("Archdruid") == "mystic"
    assert main_story.class_voluntas_archetype("Knight Enchanter") == "hybrid"
    assert main_story.class_voluntas_archetype("Beast Master") == "companion"
    assert main_story.class_voluntas_archetype("Soulcatcher") == "shadow"
    assert main_story.class_voluntas_archetype("Demonologist") == "shadow"
    assert main_story.class_voluntas_archetype("Chronomancer") == "wanderer"

    state = main_story.default_state()

    assert main_story.record_reflection_voluntas_answer(state, "RewriteSelf") is False
    assert main_story.record_reflection_voluntas_answer(state, "Claim") is True
    assert state["reflection_voluntas_answer"] == "Claim"
    assert main_story.record_reflection_voluntas_answer(state, "Carry") is False
    assert state["reflection_voluntas_answer"] == "Claim"

    farewell_state = main_story.default_state()
    assert main_story.should_show_hooded_witness_farewell(farewell_state) is False
    farewell_state["reflection_defeated"] = True
    assert main_story.should_show_hooded_witness_farewell(farewell_state) is True
    farewell_state["hooded_figure_witness_farewell_seen"] = True
    assert main_story.should_show_hooded_witness_farewell(farewell_state) is False
    farewell_state["hooded_figure_witness_farewell_seen"] = False
    farewell_state["returned_from_liminal_gap"] = True
    assert main_story.should_show_hooded_witness_farewell(farewell_state) is False


def test_narrative_system_v3_flags_helpers_and_path_summary():
    state = main_story.default_state()

    assert state["class_voluntas_followup_seen"] is False
    assert state["class_voluntas_bridge_seen"] is False
    assert state["reflection_path_mirror_seen"] is False
    assert state["vesperion_choice_argument_seen"] is False
    assert main_story.should_show_class_voluntas_followup(state) is False
    assert main_story.record_class_voluntas_followup(state) is False
    assert main_story.should_show_class_voluntas_bridge(state) is False
    assert main_story.record_class_voluntas_bridge(state) is False

    main_story.record_class_voluntas_affirmation(state, "Wizard", True)
    assert main_story.should_show_class_voluntas_followup(state) is True
    assert main_story.should_show_class_voluntas_bridge(state) is False
    assert main_story.record_class_voluntas_followup(state) is True
    assert main_story.record_class_voluntas_followup(state) is False
    assert main_story.should_show_class_voluntas_bridge(state) is True
    assert main_story.class_voluntas_bridge_event_key("Wizard") == "Class Voluntas Bridge Wizard"
    assert (
        main_story.class_voluntas_bridge_event_key("  Grandmaster of Arms  ")
        == "Class Voluntas Bridge Grandmaster of Arms"
    )
    assert (
        main_story.class_voluntas_bridge_event_key("Chronomancer")
        == "Class Voluntas Bridge Wanderer"
    )
    assert main_story.record_class_voluntas_bridge(state) is True
    assert main_story.record_class_voluntas_bridge(state) is False

    assert main_story.should_show_reflection_path_mirror(state) is False
    state["voluntas_revealed"] = True
    state["acolyte_liminal_seen"] = True
    assert main_story.should_show_reflection_path_mirror(state) is True
    assert main_story.record_reflection_path_mirror(state) is True
    assert main_story.record_reflection_path_mirror(state) is False
    state["reflection_defeated"] = True
    assert main_story.should_show_reflection_path_mirror(state) is False

    assert main_story.should_show_vesperion_choice_argument(state) is False
    state["true_final_unlocked"] = True
    assert main_story.should_show_vesperion_choice_argument(state) is True
    assert main_story.record_vesperion_choice_argument(state) is True
    assert main_story.record_vesperion_choice_argument(state) is False
    state["main_story_complete"] = True
    assert main_story.should_show_vesperion_choice_argument(state) is False

    state["reflection_voluntas_answer"] = "Carry"
    state["guardian_trials_completed"]["Triangulus"] = True
    state["voluntas_clues_found"]["Triangulus"] = True
    state["guardian_trial_choices"]["Triangulus"] = "Memory"
    state["guardian_trial_vignettes_seen"]["Triangulus"] = True

    assert main_story.voluntas_path_summary(state) == [
        "Class path: Wizard (mystic, awakened ring).",
        "Reflection answer: carried the untaken paths without surrendering the chosen one.",
        "Triangulus (Memory): selfhood is chosen, not assigned.",
        "Guardian trial depths witnessed: 1/6.",
    ]

    blank_summary = main_story.voluntas_path_summary(main_story.default_state())
    assert blank_summary == [
        "Class path: no Class Ring affirmation recorded.",
        "Reflection answer: not yet recorded.",
        "Guardian clues: none awakened.",
        "Guardian trial depths witnessed: 0/6.",
    ]


def test_main_story_helpers_gate_voluntas_and_true_final():
    state = main_story.default_state()

    assert main_story.all_guardian_trials_completed(state) is False
    assert main_story.all_voluntas_clues_found(state) is False
    assert main_story.can_reveal_voluntas(state) is False
    assert main_story.can_unlock_true_final(state) is False

    for guardian in main_story.GUARDIAN_TRIALS:
        state["guardian_trials_completed"][guardian] = True
        state["voluntas_clues_found"][guardian] = True

    assert main_story.all_guardian_trials_completed(state) is True
    assert main_story.all_voluntas_clues_found(state) is True
    assert main_story.can_reveal_voluntas(state) is True
    assert main_story.can_unlock_true_final(state) is False

    state["voluntas_revealed"] = True
    state["reflection_defeated"] = True

    assert main_story.can_unlock_true_final(state) is True


def test_main_story_guardian_progress_summaries_include_choices():
    state = main_story.default_state()
    state["guardian_trials_completed"]["Triangulus"] = True
    state["voluntas_clues_found"]["Triangulus"] = True
    state["guardian_trial_choices"]["Triangulus"] = "Memory"
    state["guardian_trials_completed"]["Luna"] = True
    state["voluntas_clues_found"]["Luna"] = True
    state["guardian_trial_choices"]["Luna"] = "Release"

    summaries = main_story.guardian_clue_summary(state)

    assert main_story.completed_guardian_count(state) == 2
    assert summaries == [
        "Triangulus (Memory): selfhood is chosen, not assigned.",
        "Luna (Release): love without freedom becomes possession or obligation.",
    ]


def test_liminal_gap_stub_enters_real_hub_restores_resources_and_clears_effects():
    player = TestGameState.create_player(health=(101, 0), mana=(51, 0))
    player.location_x, player.location_y, player.location_z, player.facing = (10, 2, 4, "north")
    player.state = "fight"
    player.main_story["pending_liminal_gap_entry"] = True
    effect_calls = []
    player.effects = lambda end=False: effect_calls.append(end)

    player.enter_liminal_gap_stub((7, 8, 9, "south"))

    assert (player.location_x, player.location_y, player.location_z) == LIMINAL_GAP_ENTRY_POS
    assert player.facing == LIMINAL_GAP_ENTRY_FACING
    assert player.in_liminal_gap() is True
    assert player.liminal_gap_return == (7, 8, 9, "south")
    assert player.health.current == 50
    assert player.mana.current == 25
    assert player.state == "normal"
    assert effect_calls == [True]
    assert player.main_story["vesperion_false_final_triggered"] is True
    assert player.main_story["pending_liminal_gap_entry"] is False
    assert player.main_story["liminal_gap_entered"] is True


def test_liminal_gap_map_loads_with_hub_tiles():
    player = TestGameState.create_player()
    player.load_tiles()

    tile_names = {
        type(tile).__name__
        for (x, y, z), tile in player.world_dict.items()
        if z == LIMINAL_GAP_LEVEL
    }

    assert "LiminalGuide" in tile_names
    assert "LiminalExitBlocker" in tile_names
    assert "LiminalSeventhSeat" in tile_names
    assert "LiminalAcolyte" in tile_names
    assert "LiminalReflection" in tile_names
    assert {
        "TriangulusGate",
        "QuadrataGate",
        "HexagonumGate",
        "LunaGate",
        "PolarisGate",
        "InfinitasGate",
    }.issubset(tile_names)
