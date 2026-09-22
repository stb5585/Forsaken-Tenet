"""Regression coverage for sparse ordinary-path dungeon traps."""

import random
from types import SimpleNamespace

from src.core import abilities, enemies, map_tiles
from src.core.combat.battle_engine import BattleEngine
from src.core.save_system import TileStateSerializer
from tests.test_framework import TestGameState


class _PlacementRng:
    def random(self):
        return 0.0

    def choices(self, population, **_kwargs):
        return [population[0]]


class _TripwireRng:
    def randint(self, low, _high):
        return low

    def random(self):
        return 1.0


class _GatheringRng:
    def __init__(self):
        self.choice_calls = []

    def random(self):
        return 0.0

    def choices(self, population, **kwargs):
        self.choice_calls.append((tuple(population), tuple(kwargs["weights"])))
        return [population[0]]


def _player(class_name="Warrior"):
    player = TestGameState.create_player(class_name=class_name, level=30)
    player.quest_dict = {"Main": {}, "Side": {}, "Bounty": {}}
    player.state = "normal"
    return player


def test_traps_are_only_assigned_to_exact_ordinary_path_types():
    ordinary = [
        map_tiles.EmptyCavePath(0, 0, 0),
        map_tiles.CavePath0(1, 0, 0),
        map_tiles.CavePath1(2, 0, 1),
        map_tiles.CavePath2(3, 0, 2),
    ]
    excluded = [
        map_tiles.BossPath(4, 0, 2),
        map_tiles.FirePath(5, 0, 2),
        map_tiles.RubbleTile(6, 0, 2),
        map_tiles.StairsDown(7, 0, 2),
    ]
    world = {(tile.x, tile.y, tile.z): tile for tile in (*ordinary, *excluded)}

    count = map_tiles.assign_dungeon_traps(world, rng=_PlacementRng())

    assert count == 4
    assert all(tile.trap_type == "Tripwire" for tile in ordinary)
    assert all(not hasattr(tile, "trap_type") or tile.trap_type is None for tile in excluded)


def test_gathering_nodes_are_depth_weighted_and_exclude_non_path_tiles():
    early = map_tiles.EmptyCavePath(0, 0, 1)
    middle = map_tiles.CavePath0(1, 0, 3)
    deep = map_tiles.CavePath1(2, 0, 5)
    excluded = map_tiles.RubbleTile(3, 0, 3)
    world = {(tile.x, tile.y, tile.z): tile for tile in (early, middle, deep, excluded)}
    rng = _GatheringRng()

    count = map_tiles.assign_dungeon_gathering_nodes(world, rng=rng)

    assert count == 3
    assert [tile.gathering_resource for tile in (early, middle, deep)] == [
        "acorn",
        "vine_seed",
        "fungus_spore",
    ]
    assert rng.choice_calls == [
        (("acorn", "vine_seed", "fungus_spore"), (40, 35, 25)),
        (("vine_seed", "fungus_spore", "hemlock_root", "deathcap_mushroom"), (20, 30, 35, 15)),
        (("fungus_spore", "hemlock_root", "deathcap_mushroom"), (20, 35, 45)),
    ]
    assert excluded.gathering_available is False
    assert map_tiles.GATHERING_NODE_CHANCE == 0.03


def test_gathering_knowledge_and_harvest_follow_specialist_rules():
    druid = _player("Druid")
    assassin = _player("Assassin")
    warrior = _player("Warrior")
    nature_tile = map_tiles.EmptyCavePath(1, 2, 1)
    nature_tile.gathering_resource = "acorn"
    nature_tile.gathering_available = True
    deathcap_tile = map_tiles.EmptyCavePath(2, 2, 4)
    deathcap_tile.gathering_resource = "deathcap_mushroom"
    deathcap_tile.gathering_available = True

    assert map_tiles.can_identify_gathering_node(druid, nature_tile)
    assert not map_tiles.can_identify_gathering_node(assassin, nature_tile)
    assert map_tiles.can_identify_gathering_node(assassin, deathcap_tile)
    assert not map_tiles.can_identify_gathering_node(warrior, deathcap_tile)
    assert "Acorn" in map_tiles.gathering_hint(druid, nature_tile, current_tile=True)
    assert "unfamiliar growth" in map_tiles.gathering_hint(warrior, nature_tile, current_tile=False)

    item = map_tiles.harvest_gathering_node(druid, nature_tile)
    assert item.name == "Acorn"
    assert nature_tile.gathering_harvested is True
    assert nature_tile.gathering_available is False
    assert map_tiles.harvest_gathering_node(warrior, deathcap_tile) is None
    assert deathcap_tile.gathering_available is True


def test_tripwire_scales_with_depth_uses_defense_and_only_triggers_once():
    player = _player()
    tile = map_tiles.EmptyCavePath(1, 1, 3)
    tile.trap_type = "Tripwire"
    initial_health = player.health.current

    message = map_tiles.trigger_tile_trap(tile, player, rng=_TripwireRng())
    health_after_first = player.health.current
    second_message = map_tiles.trigger_tile_trap(tile, player, rng=_TripwireRng())

    assert "arrow" in message
    assert health_after_first < initial_health
    assert second_message == ""
    assert player.health.current == health_after_first
    feedback = map_tiles.pop_trap_feedback(player)
    assert len(feedback) == 1
    assert feedback[0].category == "physical"
    assert feedback[0].source == "arrow"
    assert feedback[0].damage > 0
    assert map_tiles.pop_trap_feedback(player) == []


def test_avoid_traps_halves_a_failed_tripwire_avoidance():
    baseline = _player("Footpad")
    protected = _player("Footpad")
    protected.spellbook["Skills"]["Avoid Traps"] = abilities.AvoidTraps()
    baseline_tile = map_tiles.EmptyCavePath(1, 1, 2)
    protected_tile = map_tiles.EmptyCavePath(2, 1, 2)
    baseline_tile.trap_type = protected_tile.trap_type = "Tripwire"

    map_tiles.trigger_tile_trap(baseline_tile, baseline, rng=_TripwireRng())
    message = map_tiles.trigger_tile_trap(protected_tile, protected, rng=_TripwireRng())

    baseline_damage = baseline.health.max - baseline.health.current
    protected_damage = protected.health.max - protected.health.current
    assert protected_damage <= baseline_damage // 2
    assert "halves" in message


def test_magic_ward_uses_an_offensive_spell_and_magic_defense(monkeypatch):
    player = _player()
    tile = map_tiles.EmptyCavePath(1, 1, 3)
    tile.trap_type = "Magic Ward"
    monkeypatch.setattr(
        player, "damage_reduction", lambda damage, _source, typ: (True, "warded", damage // 2)
    )
    rng = SimpleNamespace(
        random=lambda: 1.0,
        choice=lambda entries: entries[-1],
        randint=lambda low, _high: low,
    )

    message = map_tiles.trigger_tile_trap(tile, player, rng=rng)

    assert "Magic Ward casts Shadow Bolt" in message
    assert "Shadow damage" in message
    assert "warded" in message
    feedback = map_tiles.pop_trap_feedback(player)
    assert len(feedback) == 1
    assert feedback[0].category == "magical"
    assert feedback[0].element == "Shadow"


def test_alert_forces_enemy_initiative(monkeypatch):
    player = _player()
    tile = map_tiles.EmptyCavePath(1, 1, 1)
    tile.trap_type = "Alert"
    enemy = enemies.Goblin()
    monkeypatch.setattr(
        "src.core.map_tiles.traps.quest_biased_random_enemy",
        lambda *_args, **_kwargs: enemy,
    )

    message = map_tiles.trigger_tile_trap(tile, player, rng=random.Random(1))
    engine = BattleEngine(player, enemy=enemy, tile=tile, rng=random.Random(2))
    first, _second = engine.start_battle()

    assert "has the initiative" in message
    assert first is enemy
    assert tile.trap_forced_initiative is False
    assert map_tiles.pop_trap_feedback(player) == []


def test_red_alert_uses_the_next_depth_enemy_pool(monkeypatch):
    player = _player()
    tile = map_tiles.EmptyCavePath(1, 1, 2)
    tile.trap_type = "Red Alert"
    requested = []
    enemy = enemies.Goblin()

    def fake_random_enemy(level, **_kwargs):
        requested.append(level)
        return enemy

    monkeypatch.setattr("src.core.map_tiles.traps.enemies.random_enemy", fake_random_enemy)
    message = map_tiles.trigger_tile_trap(tile, player, rng=random.Random(1))

    assert requested == ["3"]
    assert tile.enemy is enemy
    assert "stronger enemy" in message


def test_trap_type_and_triggered_state_round_trip_through_saves():
    tile = map_tiles.EmptyCavePath(1, 2, 3)
    tile.trap_type = "Magic Ward"
    tile.trap_triggered = True
    tile.gathering_resource = "hemlock_root"
    tile.gathering_available = False
    tile.gathering_harvested = True
    payload = TileStateSerializer.serialize_tile_state({(1, 2, 3): tile})
    restored = map_tiles.EmptyCavePath(1, 2, 3)

    TileStateSerializer.restore_tile_state({(1, 2, 3): restored}, payload)

    assert restored.trap_type == "Magic Ward"
    assert restored.trap_triggered is True
    assert restored.gathering_resource == "hemlock_root"
    assert restored.gathering_available is False
    assert restored.gathering_harvested is True


def test_chest_mimic_outcome_round_trips_through_saves():
    chest = map_tiles.UnlockedChestRoom(1, 2, 3)
    chest.mimic_outcome = True
    payload = TileStateSerializer.serialize_tile_state({(1, 2, 3): chest})
    restored = map_tiles.UnlockedChestRoom(1, 2, 3)

    TileStateSerializer.restore_tile_state({(1, 2, 3): restored}, payload)

    assert restored.mimic_outcome is True


def test_ordinary_chest_mimics_are_seed_assigned_and_exclude_funhouse_chests():
    player = _player()
    ordinary = map_tiles.UnlockedChestRoom(1, 2, 3)
    locked = map_tiles.LockedChestRoom2(2, 2, 3)
    funhouse = map_tiles.FunhouseMimicChest(3, 2, 7)
    world = {(tile.x, tile.y, tile.z): tile for tile in (ordinary, locked, funhouse)}

    count = map_tiles.assign_dungeon_chest_mimics(world, player, rng=_PlacementRng())

    assert count == 2
    assert ordinary.mimic_outcome is True
    assert locked.mimic_outcome is True
    assert funhouse.mimic_outcome is None


def test_legacy_deathcap_state_restores_as_a_gathering_node():
    restored = map_tiles.EmptyCavePath(1, 2, 3)
    TileStateSerializer.restore_tile_state(
        {(1, 2, 3): restored},
        {"(1, 2, 3)": {"deathcap_available": True, "deathcap_gathered": False}},
    )

    assert restored.gathering_resource == "deathcap_mushroom"
    assert restored.gathering_available is True
    assert restored.gathering_harvested is False
