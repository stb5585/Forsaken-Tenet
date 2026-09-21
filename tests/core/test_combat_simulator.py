#!/usr/bin/env python3
"""
Combat simulator tests (Focus Area 6.3).
"""

import random
import sys
from copy import deepcopy
from pathlib import Path
from types import SimpleNamespace

import pytest

sys.path.insert(0, str(Path(__file__).parents[2]))


def _make_stat(
    *,
    winner="Hero",
    loser="Goblin",
    winner_class="Warrior",
    loser_class="Rogue",
    turns=5,
    hp_remaining=40,
    hp_max=100,
    abilities=None,
    statuses=None,
    class_kit_events=None,
    action_economy_events=None,
):
    from src.core.analytics.combat_simulator import CombatStats

    return CombatStats(
        winner=winner,
        loser=loser,
        winner_class=winner_class,
        loser_class=loser_class,
        winner_level=10,
        loser_level=9,
        turns=turns,
        winner_hp_remaining=hp_remaining,
        winner_hp_max=hp_max,
        total_damage_dealt=25,
        total_damage_taken=10,
        abilities_used=abilities or {},
        status_effects_applied=statuses or {},
        class_kit_events=class_kit_events or {},
        action_economy_events=action_economy_events or {},
    )


def test_combat_level_handles_nested_plain_and_invalid_levels():
    from src.core.analytics.combat_simulator import _combat_level

    assert _combat_level(SimpleNamespace(level=SimpleNamespace(level=7))) == 7
    assert _combat_level(SimpleNamespace(level=5)) == 5
    assert _combat_level(SimpleNamespace(level="bad")) == 1
    assert _combat_level(object()) == 1


def test_combat_stats_properties_cover_zero_and_close_fights():
    zero_hp = _make_stat(hp_remaining=0, hp_max=0)
    close_fight = _make_stat(hp_remaining=20, hp_max=100)
    safe_win = _make_stat(hp_remaining=40, hp_max=100)

    assert zero_hp.hp_remaining_percent == 0.0
    assert zero_hp.was_close is True
    assert close_fight.was_close is True
    assert safe_win.was_close is False


def test_simulator_accepts_explicit_encounter_and_reports_roster_metrics():
    from src.core.analytics.combat_simulator import CombatSimulator
    from src.core.enemies import build_curated_encounter
    from tests.test_framework import TestGameState

    player = TestGameState.create_player(
        name="Warrior",
        class_name="Warrior",
        race_name="Human",
        level=10,
        health=(500, 500),
        mana=(200, 200),
    )
    stats = CombatSimulator().simulate_battle(
        player,
        encounter=build_curated_encounter("carrion_crawl"),
        max_turns=100,
        seed=1337,
    )

    assert stats.roster == ("Giant Hornet", "Battle Toad")
    assert stats.actor_turns >= stats.turns
    assert stats.rounds >= 1
    assert len(stats.timeline_trace) == stats.turns
    assert stats.readiness_is_monotonic is True
    assert stats.max_consecutive_actor_turns <= 2
    assert all(
        later.ready_at >= earlier.ready_at
        for earlier, later in zip(stats.timeline_trace, stats.timeline_trace[1:])
    )
    assert [entry.actor_turn_id for entry in stats.timeline_trace] == list(
        range(1, len(stats.timeline_trace) + 1)
    )
    assert "player" in stats.final_readiness
    assert len(stats.final_readiness) == 3
    assert len(stats.enemy_hp_remaining) == 2
    assert stats.player_hp_max == 500
    assert set(stats.damage_by_combatant).issubset({"Giant Hornet", "Battle Toad"})
    assert stats.consumables_used >= 0
    assert stats.reward_experience >= 0
    assert stats.reward_gold >= 0


def test_seeded_simulation_is_repeatable_without_mutating_global_rng():
    from src.core.analytics.combat_simulator import CombatSimulator
    from src.core.enemies import Goblin
    from tests.test_framework import TestGameState

    player = TestGameState.create_player(
        class_name="Warrior", race_name="Human", health=(150, 150), mana=(50, 50)
    )
    enemy = Goblin()

    def simulate():
        return CombatSimulator().simulate_battle(
            deepcopy(player), deepcopy(enemy), max_turns=20, seed=99
        )

    state_before = random.getstate()
    first = simulate()
    state_after = random.getstate()
    second = simulate()

    assert state_after == state_before
    assert random.getstate() == state_before
    assert first.winner == second.winner
    assert first.turns == second.turns
    assert first.player_hp_remaining == second.player_hp_remaining
    assert first.total_damage_dealt == second.total_damage_dealt
    assert first.abilities_used == second.abilities_used


def test_simulator_rejects_seed_and_rng_together():
    from src.core.analytics.combat_simulator import CombatSimulator
    from src.core.enemies import Goblin
    from tests.test_framework import TestGameState

    player = TestGameState.create_player(class_name="Warrior", race_name="Human")
    with pytest.raises(ValueError, match="mutually exclusive"):
        CombatSimulator().simulate_battle(player, Goblin(), seed=1, rng=random.Random(1))


def test_balance_report_empty_results_return_zero_metrics():
    from src.core.analytics.combat_simulator import BalanceReport

    report = BalanceReport(total_battles=0, results=[])

    assert report.win_rates == {}
    assert report.average_turns == 0.0
    assert report.median_turns == 0.0
    assert report.close_fight_rate == 0.0
    assert report.stomp_rate == 0.0
    assert report.get_ability_usage() == {}
    assert report.get_status_effect_frequency() == {}
    assert report.get_class_kit_events() == {}
    assert report.get_action_economy_events() == {}
    assert report.identify_outliers() == {"overpowered": [], "underpowered": []}


def test_remaining_improvement_tuning_report_lists_deferred_measurement_targets():
    from src.core.analytics.combat_simulator import remaining_improvement_tuning_report

    report = remaining_improvement_tuning_report()

    assert set(report) == {
        "footpad",
        "ordinary_drops",
        "multi_strike_accuracy",
        "enfeeble",
        "poison_consistency",
    }
    assert report["footpad"]["status"] == "measure_before_tuning"
    assert "win_rate" in report["footpad"]["metrics"]
    assert report["ordinary_drops"]["excluded_drop_sources"] == ["quest", "special", "boss"]
    assert report["multi_strike_accuracy"]["candidate_change"] == "per_strike_accuracy_falloff"
    assert "land_rate" in report["enfeeble"]["metrics"]
    assert "tick_damage" in report["poison_consistency"]["metrics"]


def test_remaining_balance_baseline_wrapper_plans_canonical_targets(tmp_path):
    from tools.run_remaining_balance_baseline import (
        CANONICAL_BASELINE_COMMANDS,
        planned_baseline_payload,
        write_baseline_summary,
    )

    payload = planned_baseline_payload(
        output_dir=tmp_path,
        timestamp="20260701_120000",
        python_executable="./.venv/bin/python",
    )

    assert len(payload["commands"]) == len(CANONICAL_BASELINE_COMMANDS) == 4
    command_text = "\n".join(command["command"] for command in payload["commands"])
    assert "--tier base --level 10 --iters 30 --seed 1337" in command_text
    assert "--tier first --level 20 --iters 30 --seed 1337" in command_text
    assert "--tier second --level 30 --iters 30 --seed 1337" in command_text
    assert (
        "--races Human Elf Half Elf Half Giant Gnome Dwarf Half Orc --delta --baseline-race Human"
        in command_text
    )
    assert set(payload["remaining_tuning_targets"]) == {
        "footpad",
        "ordinary_drops",
        "multi_strike_accuracy",
        "enfeeble",
        "poison_consistency",
    }

    text_path, json_path = write_baseline_summary(
        output_dir=tmp_path,
        timestamp="20260701_120000",
        python_executable="./.venv/bin/python",
    )

    assert text_path.name == "remaining_balance_baseline_summary.txt"
    assert json_path.name == "remaining_balance_baseline_summary.json"
    assert "Deferred tuning targets" in text_path.read_text(encoding="utf-8")


def test_balance_suite_dragoon_meta_loadout_uses_existing_power_up():
    from tools.run_balance_suite import _apply_meta_progression_loadouts

    player = SimpleNamespace(
        name="Tester",
        cls=SimpleNamespace(name="Dragoon"),
        spellbook={"Spells": {}, "Skills": {}},
        familiar=None,
        summons={},
        kill_dict={},
        power_up=False,
    )

    _apply_meta_progression_loadouts(player, 30)

    assert player.power_up is True
    assert "Draconic Onslaught" in player.spellbook["Skills"]


def test_balance_suite_meta_loadout_skips_missing_optional_power_up():
    from tools.run_balance_suite import _apply_meta_progression_loadouts

    player = SimpleNamespace(
        name="Tester",
        cls=SimpleNamespace(name="Astromancer"),
        spellbook={"Spells": {}, "Skills": {}},
        familiar=None,
        summons={},
        kill_dict={},
        power_up=False,
    )

    _apply_meta_progression_loadouts(player, 30)

    assert player.power_up is False
    assert player.spellbook["Skills"] == {}


def test_remaining_balance_baseline_dry_run_writes_result_paths(tmp_path):
    import json

    from tools.run_remaining_balance_baseline import run_baseline_bundle

    _text_path, json_path = run_baseline_bundle(
        output_dir=tmp_path,
        timestamp="20260701_121500",
        python_executable="./.venv/bin/python",
        dry_run=True,
    )

    payload = json.loads(json_path.read_text(encoding="utf-8"))
    assert [result["returncode"] for result in payload["results"]] == [0, 0, 0, 0]
    for result in payload["results"]:
        stdout_path = Path(result["stdout_path"])
        assert stdout_path.exists()
        assert stdout_path.read_text(encoding="utf-8").startswith("DRY RUN:")


def test_balance_report_aggregates_metrics_and_usage():
    from src.core.analytics.combat_simulator import BalanceReport

    results = [
        _make_stat(
            winner_class="Warrior",
            loser_class="Mage",
            turns=3,
            hp_remaining=20,
            hp_max=100,
            abilities={"Attack": 2, "Slash": 1},
            statuses={"Bleed": 1},
            class_kit_events={"meter_gain": 2, "meter_spend": 1},
            action_economy_events={"totem_output": 1},
        ),
        _make_stat(
            winner_class="Mage",
            loser_class="Warrior",
            turns=7,
            hp_remaining=95,
            hp_max=100,
            abilities={"Fireball": 3, "Attack": 1},
            statuses={"Burn": 2},
            class_kit_events={"preservation": 1},
            action_economy_events={"song_coda": 1},
        ),
        _make_stat(
            winner_class="Warrior",
            loser_class="Mage",
            turns=5,
            hp_remaining=92,
            hp_max=100,
            abilities={"Attack": 1},
            statuses={"Bleed": 2},
        ),
    ]

    report = BalanceReport(total_battles=3, results=results)

    assert report.win_rates == {"Warrior": 66.66666666666666, "Mage": 33.33333333333333}
    assert report.average_turns == 5
    assert report.median_turns == 5
    assert report.close_fight_rate == (1 / 3) * 100
    assert report.stomp_rate == (2 / 3) * 100
    assert report.get_ability_usage() == {"Attack": 4, "Slash": 1, "Fireball": 3}
    assert report.get_most_used_abilities(2) == [("Attack", 4), ("Fireball", 3)]
    assert report.get_status_effect_frequency() == {"Bleed": 3, "Burn": 2}
    assert report.get_class_kit_events() == {"meter_gain": 2, "meter_spend": 1, "preservation": 1}
    assert report.get_action_economy_events() == {"totem_output": 1, "song_coda": 1}


def test_balance_report_exports_payload_json_and_file(tmp_path):
    import json

    from src.core.analytics.combat_simulator import BalanceReport, TimelineTurnDiagnostic

    stat = _make_stat(
        winner_class="Warrior",
        loser_class="Mage",
        turns=4,
        abilities={"Attack": 2},
        statuses={"Blind": 1},
        class_kit_events={"payoff": 1},
        action_economy_events={"companion_output": 1},
    )
    stat.timeline_trace = (
        TimelineTurnDiagnostic(
            actor_id="player",
            ready_at=0.0,
            round_number=1,
            actor_turn_id=1,
            can_act=True,
            action="player=Attack",
            committed=True,
        ),
    )
    stat.final_readiness = {"player": 100.0, "enemy:0": 50.0}
    stat.max_consecutive_actor_turns = 1

    report = BalanceReport(
        total_battles=1,
        results=[stat],
    )

    payload = report.export_payload()
    assert payload["total_battles"] == 1
    assert payload["ability_usage"] == {"Attack": 2}
    assert payload["status_effect_frequency"] == {"Blind": 1}
    assert payload["class_kit_events"] == {"payoff": 1}
    assert payload["action_economy_events"] == {"companion_output": 1}
    assert payload["timeline_diagnostics"] == {
        "traced_actor_turns": 1,
        "readiness_monotonic_battles": 1,
        "max_consecutive_actor_turns": 1,
    }
    assert payload["results"][0]["winner_class"] == "Warrior"
    assert payload["results"][0]["class_kit_events"] == {"payoff": 1}
    assert payload["results"][0]["timeline_trace"] == [
        {
            "actor_id": "player",
            "ready_at": 0.0,
            "round_number": 1,
            "actor_turn_id": 1,
            "can_act": True,
            "action": "player=Attack",
            "committed": True,
            "forced": False,
        }
    ]

    json_payload = json.loads(report.export_json())
    assert json_payload["win_rates"] == {"Warrior": 100.0}

    output_path = report.export_json_file(tmp_path / "reports" / "balance.json")
    saved_payload = json.loads(output_path.read_text(encoding="utf-8"))
    assert saved_payload["median_turns"] == 4


def test_balance_report_summary_payload_is_compact_and_limited():
    from src.core.analytics.combat_simulator import BalanceReport

    report = BalanceReport(
        total_battles=2,
        results=[
            _make_stat(
                winner_class="Warrior",
                loser_class="Mage",
                turns=4,
                abilities={"Attack": 2, "Slash": 1},
                statuses={"Bleed": 3},
                class_kit_events={"meter_gain": 1},
                action_economy_events={"totem_output": 2},
            ),
            _make_stat(
                winner_class="Mage",
                loser_class="Warrior",
                turns=6,
                abilities={"Fireball": 4, "Attack": 1},
                statuses={"Burn": 2, "Bleed": 1},
                class_kit_events={"meter_gain": 2, "preservation": 1},
                action_economy_events={"summon_output": 1},
            ),
        ],
    )

    payload = report.summary_payload(ability_limit=2, status_limit=1)

    assert "results" not in payload
    assert "ability_usage" not in payload
    assert "status_effect_frequency" not in payload
    assert payload["total_battles"] == 2
    assert payload["win_rates"] == {"Warrior": 50.0, "Mage": 50.0}
    assert payload["most_used_abilities"] == [("Fireball", 4), ("Attack", 3)]
    assert payload["most_common_status_effects"] == [("Bleed", 4)]
    assert payload["class_kit_events"] == {"meter_gain": 3, "preservation": 1}
    assert payload["action_economy_events"] == {"totem_output": 2, "summon_output": 1}
    empty_payload = report.summary_payload(ability_limit=-1, status_limit=-1)
    assert empty_payload["most_used_abilities"] == []
    assert empty_payload["most_common_status_effects"] == []


def test_balance_report_identifies_manual_outliers_and_summary_mentions_sections(monkeypatch):
    from src.core.analytics.combat_simulator import BalanceReport

    report = BalanceReport(total_battles=4, results=[_make_stat()])
    report._win_rates = {
        "Champion": 90.0,
        "Balanced": 50.0,
        "Struggler": 10.0,
    }
    report.results = [
        _make_stat(winner_class="Champion", loser_class="Balanced", abilities={"Meteor": 4}),
        _make_stat(winner_class="Balanced", loser_class="Struggler", abilities={"Slash": 2}),
    ]

    outliers = report.identify_outliers(threshold=0.5)
    monkeypatch.setattr(
        report,
        "identify_outliers",
        lambda threshold=2.0: {
            "overpowered": [("Champion", 90.0, 1.0)],
            "underpowered": [("Struggler", 10.0, -1.0)],
        },
    )
    summary = report.generate_summary()

    assert outliers["overpowered"][0][0] == "Champion"
    assert outliers["underpowered"][0][0] == "Struggler"
    assert "COMBAT BALANCE REPORT" in summary
    assert "Overpowered Classes" in summary
    assert "Underpowered Classes" in summary
    assert "Most Used Abilities" in summary


def test_combat_simulator_runs_single_battle():
    from src.core.analytics.combat_simulator import CombatSimulator
    from src.core.enemies import Goblin
    from tests.test_framework import TestGameState

    player = TestGameState.create_player(
        name="Hero",
        class_name="Warrior",
        race_name="Human",
        level=8,
        health=(120, 120),
        mana=(30, 30),
    )
    enemy = Goblin()

    sim = CombatSimulator()
    stats = sim.simulate_battle(player, enemy, max_turns=50, seed=123)

    assert stats.turns > 0
    assert stats.winner in [player.name, enemy.name, "draw"]
    assert isinstance(stats.abilities_used, dict)
    assert isinstance(stats.status_effects_applied, dict)


def test_combat_simulator_can_return_draw_when_no_turns_are_run():
    from src.core.analytics.combat_simulator import CombatSimulator
    from src.core.enemies import Goblin
    from tests.test_framework import TestGameState

    player = TestGameState.create_player(
        name="Hero",
        class_name="Warrior",
        race_name="Human",
        level=8,
        health=(120, 120),
        mana=(30, 30),
    )
    enemy = Goblin()

    sim = CombatSimulator()
    stats = sim.simulate_battle(player, enemy, max_turns=0, seed=123)

    assert stats.winner == "draw"
    assert stats.loser == "draw"
    assert stats.turns == 0


def test_combat_simulator_run_simulations_with_factories():
    from src.core.analytics.combat_simulator import CombatSimulator
    from src.core.enemies import Goblin
    from tests.test_framework import TestGameState

    def make_player():
        return TestGameState.create_player(
            name="Hero",
            class_name="Warrior",
            race_name="Human",
            level=8,
            health=(120, 120),
            mana=(30, 30),
        )

    def make_enemy():
        return Goblin()

    sim = CombatSimulator()
    report = sim.run_simulations(make_player, make_enemy, iterations=10, seed=999)

    assert report.total_battles == 10
    assert len(report.results) == 10


def test_run_simulations_seeds_each_iteration_and_extends_results(monkeypatch):
    from src.core.analytics.combat_simulator import CombatSimulator

    sim = CombatSimulator()
    calls = []

    def fake_simulate_battle(char1, char2, rng=None):
        sample = rng.random()
        calls.append((char1["id"], char2["id"], sample))
        return _make_stat(winner=f"Hero-{sample}", loser="Enemy")

    monkeypatch.setattr(sim, "simulate_battle", fake_simulate_battle)

    counter = {"value": 0}

    def make_player():
        counter["value"] += 1
        return {"id": f"player-{counter['value']}"}

    def make_enemy():
        counter["value"] += 1
        return {"id": f"enemy-{counter['value']}"}

    report = sim.run_simulations(make_player, make_enemy, iterations=3, seed=50)

    assert [sample for _char1, _char2, sample in calls] == [
        random.Random(seed).random() for seed in (50, 51, 52)
    ]
    assert report.total_battles == 3
    assert len(report.results) == 3
    assert len(sim.results) == 3
