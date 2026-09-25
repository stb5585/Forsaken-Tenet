#!/usr/bin/env python3
"""
Smoke tests for core dungeon navigation behavior.
"""

from types import SimpleNamespace

from src.core import enemies, map_tiles
from src.core.character import Combat, Level, Resource, Stats
from src.core.player import DIRECTIONS, Player
from src.core.player.exploration import TOWN_SAFE_ZONE_RADIUS, normalize_town_safe_zone


def _make_player():
    player = Player(
        5,
        10,
        1,
        level=Level(),
        health=Resource(20, 20),
        mana=Resource(10, 10),
        stats=Stats(10, 10, 10, 10, 10, 10),
        combat=Combat(attack=10, defense=10, magic=5, magic_def=5),
        gold=100,
        resistance={},
    )
    player.facing = "east"
    player.load_tiles()
    return player


def test_movement():
    player = _make_player()

    assert (player.location_x, player.location_y, player.location_z) == (5, 10, 1)
    assert player.facing == "east"
    assert len(player.world_dict) > 0

    current_tile = player.world_dict.get((player.location_x, player.location_y, player.location_z))
    assert current_tile is not None

    dx, dy = DIRECTIONS[player.facing]["move"]
    ahead_pos = (player.location_x + dx, player.location_y + dy, player.location_z)
    tile_ahead = player.world_dict.get(ahead_pos)
    assert tile_ahead is not None
    assert getattr(tile_ahead, "enter", True) is True

    old_pos = (player.location_x, player.location_y)
    player.location_x += dx
    player.location_y += dy
    new_pos = (player.location_x, player.location_y)
    new_tile = player.world_dict.get((player.location_x, player.location_y, player.location_z))

    assert new_pos != old_pos
    assert new_pos == ahead_pos[:2]
    assert new_tile is not None

    player.location_x, player.location_y = 5, 10
    movable_directions = []
    for direction in ["north", "east", "south", "west"]:
        ddx, ddy = DIRECTIONS[direction]["move"]
        tile = player.world_dict.get((5 + ddx, 10 + ddy, 1))
        if tile and getattr(tile, "enter", True):
            movable_directions.append(direction)

    assert "east" in movable_directions
    assert player.quit is False
    assert player.in_town() is False


def test_town_safe_zone_normalizes_only_nearby_level_zero_cave_path_twos():
    town_x, town_y, town_z = (5, 10, 0)
    inside = (town_x + TOWN_SAFE_ZONE_RADIUS, town_y, town_z)
    outside = (town_x + TOWN_SAFE_ZONE_RADIUS + 1, town_y, town_z)
    world = {
        inside: map_tiles.CavePath2(*inside),
        outside: map_tiles.CavePath2(*outside),
        (town_x, town_y + 1, town_z): map_tiles.CavePath0(town_x, town_y + 1, town_z),
        (town_x, town_y, 1): map_tiles.CavePath2(town_x, town_y, 1),
        (town_x + 1, town_y, town_z): map_tiles.StairsDown(town_x + 1, town_y, town_z),
    }

    assert normalize_town_safe_zone(world, map_tiles) == 1
    assert type(world[inside]) is map_tiles.CavePath0
    assert type(world[outside]) is map_tiles.CavePath2
    assert type(world[(town_x, town_y + 1, town_z)]) is map_tiles.CavePath0
    assert type(world[(town_x, town_y, 1)]) is map_tiles.CavePath2
    assert type(world[(town_x + 1, town_y, town_z)]) is map_tiles.StairsDown


def test_bone_pile_marks_minotaur_approach_tile():
    player = _make_player()

    assert isinstance(player.world_dict[(3, 2, 1)], map_tiles.MinotaurBossRoom)
    assert isinstance(player.world_dict[(3, 3, 1)], map_tiles.BonePileTile)


def test_decorative_dungeon_tiles_are_traversable_hooks():
    game = SimpleNamespace(player_char=SimpleNamespace(spellbook={"Skills": []}))
    for tile_class in (
        map_tiles.RubbleTile,
        map_tiles.RootGrowthTile,
        map_tiles.FungusPatchTile,
        map_tiles.CrystalClusterTile,
        map_tiles.BonePileTile,
        map_tiles.BrokenGearTile,
    ):
        tile = tile_class(1, 2, 3)

        assert tile.enter is True
        assert tile.special is False
        assert tile.enemy is None
        assert tile.description in tile.intro_text(game)


class _BiasRng:
    def __init__(self, roll):
        self.roll = roll
        self.choice_names = []

    def random(self):
        return self.roll

    def choice(self, values):
        self.choice_names.append([enemy.name for enemy in values])
        return values[0]


def test_random_encounter_bias_can_choose_active_quest_target():
    player = SimpleNamespace(
        quest_dict={
            "Main": {},
            "Side": {"Rat Trouble": {"Type": "Defeat", "What": "Giant Rat", "Completed": False}},
            "Bounty": {},
        },
        stats=SimpleNamespace(charisma=10),
        check_mod=lambda *_args, **_kwargs: 5,
    )
    rng = _BiasRng(0.0)

    enemy = map_tiles.quest_biased_random_enemy(player, "0", rng=rng)

    assert enemy.name == "Giant Rat"
    assert rng.choice_names == [["Giant Rat"]]


def test_random_encounter_bias_is_soft_and_floor_limited():
    player = SimpleNamespace(
        quest_dict={
            "Main": {"Late Threat": {"Type": "Defeat", "What": "Lich", "Completed": False}},
            "Side": {"Rat Trouble": {"Type": "Defeat", "What": "Giant Rat", "Completed": False}},
            "Bounty": {"Goblin": [{"num": 2}, 0, False]},
        },
        stats=SimpleNamespace(charisma=10),
        check_mod=lambda *_args, **_kwargs: 5,
    )
    rng = _BiasRng(0.99)

    enemy = map_tiles.quest_biased_random_enemy(player, "0", rng=rng)

    assert enemy.name == "Green Slime"
    assert "Giant Rat" in rng.choice_names[0]
    assert "Goblin" in rng.choice_names[0]
    assert "Lich" not in rng.choice_names[0]


def test_random_encounter_bias_includes_enemy_drop_collection_quests():
    player = SimpleNamespace(
        quest_dict={
            "Main": {},
            "Side": {
                "Rat Trap": {"Type": "Collect", "What": "RatTail", "Completed": False},
                "Ticket to Ride": {"Type": "Collect", "What": "TicketPiece", "Completed": False},
            },
            "Bounty": {},
        },
        stats=SimpleNamespace(charisma=10),
        check_mod=lambda *_args, **_kwargs: 5,
    )

    targets = map_tiles.active_random_encounter_quest_targets(player)

    assert "Giant Rat" in targets
    assert "Wererat" in targets
    assert "TicketPiece" not in targets


def test_random_encounter_bias_ignores_completed_and_turned_in_targets():
    player = SimpleNamespace(
        quest_dict={
            "Main": {
                "Done": {"Type": "Defeat", "What": "Giant Rat", "Completed": True},
                "Turned": {"Type": "Defeat", "What": "Goblin", "Turned In": True},
            },
            "Side": {
                "Collected": {"Type": "Collect", "What": "RatTail", "Completed": True},
                "Turned Collect": {"Type": "Collect", "What": "RatTail", "Turned In": True},
            },
            "Bounty": {
                "Bandit": [{"num": 1}, 1, True],
                "Skeleton": [{"num": 1}, 0, False],
            },
        },
        stats=SimpleNamespace(charisma=10),
        check_mod=lambda *_args, **_kwargs: 5,
    )

    targets = map_tiles.active_random_encounter_quest_targets(player)

    assert targets == {"Skeleton"}


def test_random_encounter_bias_chance_is_softened_and_capped():
    player = SimpleNamespace(
        quest_dict={"Main": {}, "Side": {}, "Bounty": {}},
        stats=SimpleNamespace(charisma=999),
        check_mod=lambda *_args, **_kwargs: 999,
    )

    assert map_tiles.random_encounter_quest_bias_chance(player) == 0.15


def test_random_enemy_override_bypasses_encounter_bias():
    player = SimpleNamespace(
        quest_dict={"Main": {}, "Side": {"Rat Trouble": {"Type": "Defeat", "What": "Giant Rat"}}},
        stats=SimpleNamespace(charisma=99),
        check_mod=lambda *_args, **_kwargs: 99,
    )
    try:
        enemies.set_random_enemy_override(enemies.Test)
        enemy = map_tiles.quest_biased_random_enemy(player, "0", rng=_BiasRng(0.0))
    finally:
        enemies.clear_random_enemy_override()

    assert enemy.name == "Test"
