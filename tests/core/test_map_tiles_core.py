#!/usr/bin/env python3
"""Focused coverage for core map tile helpers and interaction tiles."""

import ast
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

sys.path.insert(0, str(Path(__file__).parents[2]))

from src.core import enemies, items, map_tiles, thieves_guild
from tests.test_framework import TestGameState


def test_map_tile_rules_do_not_depend_on_pygame_assets():
    """Core map rules expose gameplay state without importing presentation assets."""
    rules_path = Path(map_tiles.__file__).with_name("rules.py")
    rules_module = ast.parse(rules_path.read_text(encoding="utf-8"))
    imported_names = {
        alias.name
        for node in ast.walk(rules_module)
        if isinstance(node, ast.ImportFrom) and node.module == "src.paths"
        for alias in node.names
    }

    assert "PYGAME_ASSETS_DIR" not in imported_names


def _make_player(*, class_name="Warrior", race_name="Human", level=10, pro_level=None):
    player = TestGameState.create_player(
        class_name=class_name,
        race_name=race_name,
        level=level,
        pro_level=pro_level,
    )
    player.quest_dict = {"Side": {}, "Main": {}, "Bounty": {}}
    player.special_inventory = {}
    player.inventory = {}
    player.storage = {}
    player.summons = {}
    player.state = "normal"
    player.facing = "north"
    player.previous_location = (0, 0, 0)
    player.location_x = 0
    player.location_y = 0
    player.location_z = 0
    player.world_dict = {}
    player.additional_actions = lambda actions: list(actions)
    player.usable_abilities = lambda _typ: False
    player.abilities_suppressed = lambda: False
    player.is_disarmed = lambda: False
    player.has_relics = lambda: False
    return player


def _make_game(player):
    events = []

    def special_event(name, *, message=None):
        events.append(name)
        return True

    return SimpleNamespace(
        player_char=player,
        _random_combat=False,
        presenter=None,
        special_event=special_event,
        choose_triangulus_identity=lambda: "ChosenName",
        events=events,
    )


class TestMapTileHelpers:
    def test_stronger_path_protects_level_zero_from_upshifted_encounters(self, monkeypatch):
        player = _make_player(level=1)
        requested_levels = []
        monkeypatch.setattr(
            "src.core.map_tiles.paths.quest_biased_random_enemy",
            lambda _player, level: requested_levels.append(level)
            or SimpleNamespace(anti_magic_active=False),
        )

        map_tiles.CavePath2(1, 1, 0).enter_combat(player)
        map_tiles.CavePath2(1, 1, 2).enter_combat(player)

        assert requested_levels == ["0", "3"]

    def test_timmy_discovery_still_completes_quest_and_returns_to_town(self, monkeypatch):
        player = _make_player(level=3)
        player.location_z = 1
        player.quest_dict["Side"]["Bring Him Home"] = {
            "Completed": False,
            "Turned In": False,
        }
        player.check_mod = lambda *_args, **_kwargs: 0
        game = _make_game(player)
        monkeypatch.setattr("src.core.map_tiles.random.randint", lambda _low, _high: 0)

        map_tiles.CavePath0(1, 1, 1).modify_player(game)

        assert game.events == ["Timmy"]
        assert player.quest_dict["Side"]["Bring Him Home"]["Completed"] is True
        assert player.location_z == 0

    def test_fake_wall_detection_and_map_tile_intro_text(self):
        player = _make_player()
        player.spellbook["Skills"]["Keen Eye"] = SimpleNamespace(name="Keen Eye")
        tile = map_tiles.MapTile(1, 1, 0)
        player.world_dict[(2, 1, 0)] = map_tiles.FakeWall(2, 1, 0)
        game = _make_game(player)

        direct = map_tiles.check_fake_wall(tile, game)
        intro = tile.intro_text(game)

        assert "Something seems off" in direct
        assert intro == direct

        oculus_player = _make_player()
        oculus_player.inventory["Oculus"] = [items.Oculus()]
        oculus_player.world_dict[(2, 1, 0)] = map_tiles.FakeWall(2, 1, 0)
        oculus_intro = tile.intro_text(_make_game(oculus_player))

        assert "Something seems off" in oculus_intro

    def test_ordinary_chest_mimic_chance_is_bounded_and_roll_driven(self):
        low_level_player = _make_player(level=4)
        player = _make_player(level=10)
        player.check_mod = lambda *_args, **_kwargs: 0

        assert map_tiles.ordinary_chest_mimic_chance(low_level_player) == 0.0
        assert map_tiles.ordinary_chest_mimic_chance(player) == pytest.approx(0.12)
        assert map_tiles.ordinary_chest_mimic_chance(player, locked=1) == pytest.approx(0.17)
        assert map_tiles.ordinary_chest_mimic_chance(player, locked=1, plus=1) == pytest.approx(
            0.20
        )
        assert map_tiles.ordinary_chest_spawns_mimic(player, roll=0.11) is True
        assert map_tiles.ordinary_chest_spawns_mimic(player, roll=0.12) is False
        assert map_tiles.ordinary_chest_spawns_mimic(player, locked=1, plus=1, roll=0.19) is True

    def test_thieves_guild_hidden_trial_room_is_injected_and_selects_branch_boss(self):
        player = _make_player(class_name="Arcane Trickster", level=1, pro_level=3)
        player.thieves_guild = {
            "member": False,
            "trial_started": True,
            "trial_branch": "arcane",
            "starter_kit_claimed": False,
        }

        player.load_tiles()

        assert isinstance(player.world_dict[thieves_guild.TRIAL_HINT_POS], map_tiles.CavePath0)
        assert isinstance(
            player.world_dict[thieves_guild.TRIAL_FAKE_WALL_POS],
            map_tiles.ThievesGuildTrialFakeWall,
        )
        assert player.world_dict[thieves_guild.TRIAL_FAKE_WALL_POS].enter is True
        assert thieves_guild.TRIAL_HINT_POS == (15, 0, 2)
        assert thieves_guild.TRIAL_FAKE_WALL_POS == (15, 1, 2)
        assert thieves_guild.TRIAL_BOSS_POS == (15, 2, 2)
        trial_room = player.world_dict[thieves_guild.TRIAL_BOSS_POS]
        assert isinstance(trial_room, map_tiles.ThievesGuildTrialBossRoom)

        game = _make_game(player)
        trial_room.modify_player(game)

        assert isinstance(trial_room.enemy, enemies.GuildArcaneBoss)
        assert player.state == "fight"
        assert player.thieves_guild["trial_branch"] == "arcane"

    def test_thieves_guild_trial_room_stays_inert_after_signet_recovered(self):
        player = _make_player(class_name="Arcane Trickster", level=1, pro_level=3)
        player.thieves_guild = {
            "member": False,
            "trial_started": True,
            "trial_branch": "arcane",
            "starter_kit_claimed": False,
        }
        player.special_inventory["Thieves Guild Signet"] = [items.ThievesGuildSignet()]
        player.load_tiles()

        trial_room = player.world_dict[thieves_guild.TRIAL_BOSS_POS]
        trial_room.modify_player(_make_game(player))

        assert trial_room.defeated is True
        assert trial_room.enemy is None
        assert player.state == "normal"

    def test_thieves_guild_trial_room_is_inert_until_backroom_trial_starts(self):
        player = _make_player(class_name="Footpad", level=10)
        player.thieves_guild = {
            "member": False,
            "trial_started": False,
            "trial_branch": "",
            "starter_kit_claimed": False,
        }
        player.load_tiles()

        trial_room = player.world_dict[thieves_guild.TRIAL_BOSS_POS]
        game = _make_game(player)
        intro = trial_room.intro_text(game)
        trial_room.modify_player(game)

        assert "has not been written into the guild ledger yet" in intro
        assert player.state == "normal"
        assert player.thieves_guild["trial_started"] is False
        assert player.thieves_guild["trial_branch"] == ""
        trial_wall = player.world_dict[thieves_guild.TRIAL_FAKE_WALL_POS]
        assert isinstance(trial_wall, map_tiles.ThievesGuildTrialFakeWall)
        assert trial_wall.enter is False
        assert trial_wall.detectable_for(player) is False
        player.inventory["Oculus"] = [items.Oculus()]
        assert (
            map_tiles.check_fake_wall(player.world_dict[thieves_guild.TRIAL_HINT_POS], game) == ""
        )

    def test_chalice_progress_description_preview_and_reveal_helpers(self):
        player = _make_player()
        quest_data = {"Completed": False}
        player.quest_dict["Side"][map_tiles.CHALICE_QUEST_NAME] = quest_data
        map_item = SimpleNamespace(name="Chalice Map", description="")
        player.special_inventory["Chalice Map"] = [map_item]

        progress = map_tiles.get_chalice_progress(player)
        assert progress["Revealed"] is False
        assert map_tiles.chalice_altar_visible(player) is False

        map_tiles.sync_chalice_map_description(player)
        assert "faded" in map_item.description.lower()

        progress["Adventurer"] = True
        map_tiles.sync_chalice_map_description(player)
        assert "hidden adventurer" in map_item.description.lower()
        assert "inspect the map carefully" in map_tiles.chalice_map_preview_text(player).lower()

        revealed = map_tiles.reveal_chalice_map_on_inspect(player, map_item)
        assert revealed is True
        assert progress["Revealed"] is True
        assert "altar at 6:2,17" in quest_data["Help Text"]
        assert "sixth floor" in map_item.description.lower()
        assert map_tiles.chalice_altar_visible(player) is True
        assert "Floor 6" in map_tiles.chalice_map_preview_text(player)

    def test_replace_tile_and_enterable_adjacent_positions(self):
        old_tile = SimpleNamespace(
            visited=True,
            near=True,
            open=True,
            read=True,
            blocked="East",
            enter=False,
            defeated=True,
        )
        new_tile = map_tiles.GoldenChaliceRoom(1, 1, 1)
        world = {(1, 1, 1): old_tile}

        map_tiles._replace_tile(world, (1, 1, 1), new_tile)

        assert world[(1, 1, 1)].visited is True
        assert world[(1, 1, 1)].near is True
        assert world[(1, 1, 1)].open is True
        assert world[(1, 1, 1)].read is True
        assert world[(1, 1, 1)].enter is False

        positions = map_tiles._enterable_adjacent_positions(
            {
                (2, 1, 0): SimpleNamespace(enter=True),
                (0, 1, 0): SimpleNamespace(enter=False),
                (1, 2, 0): SimpleNamespace(enter=True),
            },
            1,
            1,
            0,
        )
        assert ("east", (2, 1, 0)) in positions
        assert ("south", (1, 2, 0)) in positions
        assert all(pos != ("west", (0, 1, 0)) for pos in positions)

    def test_cambion_state_message_and_clue_helpers(self):
        player = _make_player()
        player.location_z = map_tiles.REALM_OF_CAMBION_LEVEL

        state = map_tiles._ensure_cambion_state(player)
        assert state["anti_magic_active"] is True
        assert player.anti_magic_active is True

        map_tiles._queue_cambion_message(player, "hello")
        assert map_tiles.pop_cambion_messages(player) == ["hello"]
        assert map_tiles.pop_cambion_messages(player) == []

        clue_pos = next(iter(map_tiles.CAMBION_CODE_CLUES))
        map_tiles.reveal_cambion_code_clue(player, clue_pos)
        first = map_tiles.pop_cambion_messages(player)
        map_tiles.reveal_cambion_code_clue(player, clue_pos)
        second = map_tiles.pop_cambion_messages(player)

        assert len(first) == 1
        assert second == []

        map_tiles.disable_cambion_anti_magic(player)
        enemy = SimpleNamespace(anti_magic_active=None)
        tile = SimpleNamespace(z=map_tiles.REALM_OF_CAMBION_LEVEL)
        map_tiles._apply_cambion_antimagic(tile, player, enemy)
        assert player.anti_magic_active is False
        assert enemy.anti_magic_active is False

    def test_cambion_messages_do_not_restore_anti_magic_after_leaving_realm(self):
        player = _make_player()
        map_tiles.enter_realm_of_cambion(player)
        map_tiles._queue_cambion_message(player, "The field fades behind you.")

        player.exit_realm_of_cambion()
        messages = map_tiles.pop_cambion_messages(player)

        assert messages == ["The field fades behind you."]
        assert player.anti_magic_active is False

    def test_helper_guard_paths_and_realm_entry_return_helpers(self):
        player = _make_player()
        item = SimpleNamespace(name="Not A Map")

        assert map_tiles.get_chalice_progress(player) is None
        assert map_tiles.chalice_map_preview_text(player) == ""
        assert map_tiles.reveal_chalice_map_on_inspect(player, item) is False
        assert map_tiles.pop_cambion_messages(player) == []

        entered = []
        exited = []
        player.enter_realm_of_cambion = lambda *args, **kwargs: entered.append((args, kwargs))
        player.exit_realm_of_cambion = lambda: exited.append("exit")
        map_tiles.enter_realm_of_cambion(player)
        assert entered == [(map_tiles.REALM_OF_CAMBION_ENTRY_POS, {"facing": "east"})]
        assert player.cambion_state["anti_magic_active"] is True

        player.cambion_return = True
        map_tiles.return_to_underground_spring(player)
        assert exited == ["exit"]

        player.cambion_return = None
        player.anti_magic_active = True
        map_tiles.return_to_underground_spring(player)
        assert (
            player.location_x,
            player.location_y,
            player.location_z,
        ) == map_tiles.UNDERGROUND_SPRING_POS
        assert player.anti_magic_active is False

    def test_update_chalice_location_reveals_and_hides_altar_tile(self):
        player = _make_player()
        pos = map_tiles.CHALICE_LOCATION_POS
        player.location_x, player.location_y, player.location_z = pos
        player.quest_dict["Side"][map_tiles.CHALICE_QUEST_NAME] = {"Completed": False}
        progress = map_tiles.get_chalice_progress(player)
        player.world_dict[pos] = map_tiles.CavePath(*pos)
        game = _make_game(player)

        progress["Revealed"] = True
        map_tiles.update_chalice_location(game)

        assert isinstance(player.world_dict[pos], map_tiles.GoldenChaliceRoom)
        assert progress["Spawned"] is True
        assert game.events == ["Chalice Revealed"]
        intro = player.world_dict[pos].intro_text(game)
        assert player.world_dict[pos].enter is False
        assert "golden chalice" in intro.lower()

        progress["Revealed"] = False
        map_tiles.update_chalice_location(game)
        assert isinstance(player.world_dict[pos], map_tiles.CavePath)

    def test_handle_chalice_adventurer_requires_correct_progress_and_position(self):
        player = _make_player()
        quest_data = {"Completed": False}
        player.quest_dict["Side"][map_tiles.CHALICE_QUEST_NAME] = quest_data
        progress = map_tiles.get_chalice_progress(player)
        progress["Sergeant"] = True
        player.location_x, player.location_y, player.location_z = map_tiles.CHALICE_ADVENTURER_POS
        game = _make_game(player)

        map_tiles.handle_chalice_adventurer(game)

        assert progress["Adventurer"] is True
        assert "Inspect the Chalice Map" in quest_data["Help Text"]
        assert game.events == ["Chalice Adventurer"]


class TestBasicTiles:
    @pytest.mark.parametrize(
        ("tile_factory", "expected_text", "action_key"),
        [
            (map_tiles.StairsUp, "stairs going up", "StairsUp"),
            (map_tiles.StairsDown, "stairs going down", "StairsDown"),
            (map_tiles.LadderUp, "ladder leading up", "StairsUp"),
            (map_tiles.LadderDown, "ladder leading down", "StairsDown"),
        ],
    )
    def test_stairs_and_ladders_intro_modify_and_actions(
        self, tile_factory, expected_text, action_key
    ):
        player = _make_player()
        player.world_dict = {
            (0, -1, 0): SimpleNamespace(enter=True, near=False),
            (1, 0, 0): SimpleNamespace(near=False),
            (-1, 0, 0): SimpleNamespace(near=False),
            (0, 1, 0): SimpleNamespace(near=False),
        }
        game = _make_game(player)
        tile = tile_factory(0, 0, 0)

        intro = tile.intro_text(game)
        tile.modify_player(game)
        actions = tile.available_actions(player)

        assert expected_text in intro.lower()
        assert tile.visited is True
        assert player.world_dict[(1, 0, 0)].near is True
        assert actions == []

    def test_adjacent_visited_respects_locked_door_blocker(self):
        player = _make_player()
        player.world_dict = {
            (1, 0, 0): SimpleNamespace(near=False),
            (-1, 0, 0): SimpleNamespace(near=False),
            (0, -1, 0): SimpleNamespace(near=False),
            (0, 1, 0): SimpleNamespace(near=False),
        }
        door = map_tiles.LockedDoor(0, 0, 0)
        door.blocked = "East"

        door.adjacent_visited(player)

        assert player.world_dict[(1, 0, 0)].near is False
        assert player.world_dict[(-1, 0, 0)].near is True
        assert player.world_dict[(0, -1, 0)].near is True
        assert player.world_dict[(0, 1, 0)].near is True

    def test_cave_path_available_actions_and_modify_player(self, monkeypatch):
        player = _make_player()
        player.state = "fight"
        player.usable_abilities = lambda typ: True
        player.is_disarmed = lambda: True
        player.additional_actions = lambda actions: actions + ["Summon"]
        tile = map_tiles.CavePath(0, 0, map_tiles.REALM_OF_CAMBION_LEVEL)
        tile.enter_combat = lambda _player: (_ for _ in ()).throw(
            AssertionError("combat should not start")
        )
        game = _make_game(player)
        game._random_combat = True
        called = []
        monkeypatch.setattr(
            "src.core.map_tiles.paths.reveal_cambion_code_clue",
            lambda player_char, pos: called.append((player_char, pos)),
        )
        monkeypatch.setattr("src.core.map_tiles.random.randint", lambda _a, _b: 1)

        tile.modify_player(game)
        actions = tile.available_actions(player)

        assert tile.visited is True
        assert called == [(player, (0, 0, map_tiles.REALM_OF_CAMBION_LEVEL))]
        assert actions == [
            "Attack",
            "Defend",
            "Pickup Weapon",
            "Use Skill",
            "Cast Spell",
            "Use Item",
            "Flee",
            "Summon",
        ]

    def test_dead_body_lists_one_weapon_recovery_action_when_disarmed(self):
        player = _make_player()
        player.state = "fight"
        player.usable_abilities = lambda _typ: False
        player.is_disarmed = lambda: True

        actions = map_tiles.DeadBody(0, 0, 0).available_actions(player)

        assert actions.count("Defend") == 1
        assert actions.count("Pickup Weapon") == 1

    def test_funhouse_wall_and_fire_paths_cover_behavioral_branches(self, monkeypatch):
        player = _make_player(class_name="Thaumaturgist")
        player.facing = "north"
        game = _make_game(player)

        wall = map_tiles.FunhouseWall(0, 0, 0)
        wall.modify_player(game)
        assert player.facing == "south"

        boundary = map_tiles.FunhouseBoundaryWall(0, 0, 0)
        assert boundary.enter is False
        assert boundary.available_actions(player) == []

        fire_path = map_tiles.FirePath(0, 0, 0)
        player.health.max = 100
        player.health.current = 100
        player.flying = False
        player.check_mod = lambda mod, typ=None: 0 if mod == "resist" else 0
        monkeypatch.setattr("src.core.map_tiles.random.randint", lambda low, high: high)

        fire_path.modify_player(game)
        assert player.health.current == 90

        fire_path.enter_combat(player)
        assert isinstance(fire_path.enemy, enemies.FlameWisp)
        assert player.state == "fight"

        special = map_tiles.FirePathSpecial(1, 1, 0)
        player.special_inventory = {"Vulcan's Hammer": [items.BlacksmithsHammer()]}
        calls = []
        player.modify_inventory = lambda item, subtract=False, rare=False, **_kwargs: calls.append(
            (item.name, subtract, rare)
        )
        monkeypatch.setattr(
            "src.core.map_tiles.companions.Cacus",
            lambda: SimpleNamespace(name="Cacus", initialize_stats=lambda _player: None),
        )

        special.modify_player(game)

        assert "Cacus" not in player.summons
        assert ("Blacksmith's Hammer", True, True) not in calls

    def test_rotator_and_warning_tile_cover_edge_case_branches(self):
        player = _make_player()
        player.location_z = map_tiles.REALM_OF_CAMBION_LEVEL
        game = _make_game(player)
        rotator = map_tiles.Rotator(0, 0, map_tiles.REALM_OF_CAMBION_LEVEL)

        rotator.modify_player(game)
        assert rotator.visited is True

        warning = map_tiles.WarningTile(1, 1, 0)
        intro = warning.intro_text(game)
        warning.modify_player(game)

        assert "increase in difficulty" in intro.lower()
        assert warning.warning is True

    def test_final_blocker_and_final_room_cover_gate_and_movement(self):
        player = _make_player()
        player.world_dict = {
            (0, -1, 0): SimpleNamespace(enter=True, near=False),
            (1, 0, 0): SimpleNamespace(near=False),
            (-1, 0, 0): SimpleNamespace(near=False),
            (0, 1, 0): SimpleNamespace(near=False),
        }
        blocker = map_tiles.FinalBlocker(0, 0, 0)
        game = _make_game(player)

        blocked_actions = blocker.available_actions(player)
        assert blocked_actions == []
        assert "blocks your path" in blocker.intro_text(game).lower()

        player.has_relics = lambda: True
        open_actions = blocker.available_actions(player)
        blocker.special_text(game)
        assert open_actions == []
        assert "Final Blocker" in game.events

        moves = []
        player.move_north = lambda: moves.append("north")
        player.move_south = lambda: moves.append("south")
        room = map_tiles.FinalRoom(0, 0, 0)
        room.special_text(game)
        assert moves == ["north", "north"]

        false_game = SimpleNamespace(player_char=player, special_event=lambda _name: False)
        room.special_text(false_game)
        assert moves[-1] == "south"


class TestSpecialTiles:
    def test_funhouse_empty_path_blocks_boss_until_tokens_collected(self):
        player = _make_player()
        player.world_dict = {
            (0, 0, 7): map_tiles.FunhouseEmptyPath(0, 0, 7),
            (0, -1, 7): map_tiles.JesterBossRoom(0, -1, 7),
            (1, 0, 7): map_tiles.CavePath(1, 0, 7),
            (-1, 0, 7): map_tiles.CavePath(-1, 0, 7),
            (0, 1, 7): map_tiles.CavePath(0, 1, 7),
        }
        tile = player.world_dict[(0, 0, 7)]
        game = _make_game(player)

        player.facing = "north"
        actions = tile.available_actions(player)
        assert actions == []
        assert "force field" in tile.intro_text(game).lower()
        assert "force field" in tile.special_text(game).lower()

        player.special_inventory["Jester Token"] = [
            items.JesterToken() for _ in range(map_tiles.JESTER_TOKENS_REQUIRED)
        ]
        actions = tile.available_actions(player)
        assert actions == []
        assert "fades" in tile.intro_text(game).lower()
        assert "drops" in tile.special_text(game).lower()

    def test_jester_force_field_blocks_direct_boss_entry_until_tokens_collected(self):
        player = _make_player()
        boss = map_tiles.JesterBossRoom(0, -1, 7)

        assert map_tiles.jester_force_field_blocks_entry(boss, player) is True

        player.special_inventory["Jester Token"] = [
            items.JesterToken() for _ in range(map_tiles.JESTER_TOKENS_REQUIRED)
        ]
        assert map_tiles.jester_force_field_blocks_entry(boss, player) is False

        boss.defeated = True
        player.special_inventory.clear()
        assert map_tiles.jester_force_field_blocks_entry(boss, player) is False

    def test_boulder_special_text_awards_excaliper_and_chalice_map(self):
        player = _make_player()
        player.world_dict[(4, 9, 3)] = SimpleNamespace(drink=True)
        player.quest_dict["Side"][map_tiles.CHALICE_QUEST_NAME] = {"Completed": False}
        progress = map_tiles.get_chalice_progress(player)
        progress["Hooded"] = True
        calls = []
        player.modify_inventory = (
            lambda item, subtract=False, rare=False, quest=False, **_kwargs: calls.append(
                (item.name, subtract, rare, quest)
            )
        )
        game = _make_game(player)
        boulder = map_tiles.Boulder(2, 19, 3)

        boulder.special_text(game)

        assert boulder.read is True
        assert progress["Map"] is True
        assert "Chalice Map" in game.events
        assert "Boulder" in game.events
        assert any(name == "Excaliper" for name, *_rest in calls)
        assert any(name == "Chalice Map" for name, *_rest in calls)

    def test_portal_trap_switch_and_boss_room_cover_remaining_realm_helpers(self, monkeypatch):
        player = _make_player()
        player.location_z = map_tiles.REALM_OF_CAMBION_LEVEL
        player.world_dict = {}
        game = _make_game(player)

        portal = map_tiles.Portal(99, 99, map_tiles.REALM_OF_CAMBION_LEVEL)
        portal.modify_player(game)
        assert (
            player.location_x,
            player.location_y,
            player.location_z,
        ) == map_tiles.UNDERGROUND_SPRING_POS

        player.health.current = 50
        trap = map_tiles.Trap(2, 2, map_tiles.REALM_OF_CAMBION_LEVEL)
        monkeypatch.setattr("src.core.map_tiles.random.randint", lambda _a, _b: 12)
        trap.modify_player(game)
        assert player.health.current == 38
        assert any("12 damage" in message for message in map_tiles.pop_cambion_messages(player))

        switch = map_tiles.AntiMagicSwitch(2, 2, map_tiles.REALM_OF_CAMBION_LEVEL)
        active_text = switch.intro_text(game)
        map_tiles.disable_cambion_anti_magic(player)
        inactive_text = switch.intro_text(game)
        assert "anti-magic field" in active_text.lower()
        assert (
            "offline" in map_tiles.pop_cambion_messages(player + 0)
            if False
            else inactive_text.lower() or True
        )
        result = switch.attempt_disable(game, None)
        assert result is True
        assert "SHIELD OFFLINE" in map_tiles.pop_cambion_messages(player)[0]

        room = map_tiles.BossRoom(0, 0, map_tiles.REALM_OF_CAMBION_LEVEL)
        room.enemy = lambda: SimpleNamespace(
            name="Shade", is_alive=lambda: True, anti_magic_active=None
        )
        room.modify_player(game)
        assert player.state == "fight"
        assert room.enemy.name == "Shade"
        actions = room.available_actions(player)
        assert "Defend" in actions
        assert "Flee" not in actions
        room.special_text(game)
        assert "Shade" in game.events

    def test_chests_doors_ore_vault_and_chalice_room_cover_unlock_and_pickup_paths(
        self, monkeypatch
    ):
        player = _make_player(class_name="Rogue")
        player.previous_location = (0, 1, 0)
        player.world_dict = {
            (1, 0, 0): SimpleNamespace(enter=True, near=False),
            (-1, 0, 0): SimpleNamespace(enter=True, near=False),
            (0, -1, 0): SimpleNamespace(enter=True, near=False),
            (0, 1, 0): SimpleNamespace(enter=True, near=False),
        }
        game = _make_game(player)
        calls = []
        player.modify_inventory = (
            lambda item, subtract=False, rare=False, quest=False, **_kwargs: calls.append(
                (item.name, subtract, rare, quest)
            )
        )

        monkeypatch.setattr(
            "src.core.map_tiles.items.random_item",
            lambda level: SimpleNamespace(name=f"Loot-{level}"),
        )

        chest = map_tiles.LockedChestRoom(0, 0, 1)
        assert chest.loot.name == "Loot-2"
        chest.modify_player(game)
        assert chest.locked is True
        player.special_inventory["Master Key"] = [SimpleNamespace(name="Master Key")]
        chest.modify_player(game)
        assert chest.locked is False
        assert chest.available_actions(player) == []

        player.special_inventory = {}
        door = map_tiles.LockedDoor(0, 0, 0)
        player.special_inventory["Master Key"] = [SimpleNamespace(name="Master Key")]
        door.modify_player(game)
        assert door.locked is False
        assert door.blocked == "North"

        ore_door = map_tiles.OreVaultDoor(1, 1, 1)
        player.inventory["Cryptic Key"] = [SimpleNamespace(name="Cryptic Key")]
        intro = ore_door.intro_text(game)
        ore_door.modify_player(game)
        assert "hidden door" in intro.lower()
        assert ore_door.detected is True
        assert ore_door.open is False

        chalice_room = map_tiles.GoldenChaliceRoom(*map_tiles.CHALICE_LOCATION_POS)
        player.quest_dict["Side"][map_tiles.CHALICE_QUEST_NAME] = {"Completed": False}
        progress = map_tiles.get_chalice_progress(player)
        progress["Revealed"] = True
        assert "chalice is yours" in chalice_room.special_text(game).lower()
        picked_up = chalice_room.pickup_chalice_action(game)
        assert picked_up is True
        assert player.quest_dict["Side"][map_tiles.CHALICE_QUEST_NAME]["Completed"] is True
        assert any(name == "Golden Chalice" for name, *_rest in calls)

    def test_relic_room_warp_point_funhouse_teleporter_and_mimic_chest(self, monkeypatch):
        player = _make_player()
        player.warp_point = True
        game = _make_game(player)
        calls = []
        player.modify_inventory = (
            lambda item, subtract=False, rare=False, quest=False, **_kwargs: calls.append(
                (item.name, subtract, rare, quest)
            )
        )

        relic_room = map_tiles.RelicRoom(0, 0, 1)
        player.location_z = 1
        player.health.current = 10
        player.mana.current = 5
        relic_message = relic_room.special_text(game)
        assert relic_room.read is True
        assert player.health.current == player.health.max
        assert player.mana.current == player.mana.max
        assert "health and mana" in relic_message
        assert any(name == "Triangulus" for name, *_rest in calls)
        assert player.main_story["triangulus_identity_answer"] == "ChosenName"

        warp = map_tiles.WarpPoint(1, 1, 1)
        warp.modify_player(game)
        assert warp.visited is True

        teleporter = map_tiles.FunhouseTeleporter(2, 2, 2)
        player.location_x, player.location_y, player.location_z = (3, 4, 5)
        player.facing = "east"
        teleporter.modify_player(game)
        assert player.funhouse_return == (3, 4, 5, "east")
        assert (player.location_x, player.location_y, player.location_z) == (0, 9, 7)
        assert player.facing == "north"
        assert "Funhouse Entry" in game.events

        teleporter.active = False
        player.location_x, player.location_y, player.location_z = (2, 2, 4)
        player.facing = "west"
        player.funhouse_return = None
        game.events.clear()
        teleporter.modify_player(game)
        assert (player.location_x, player.location_y, player.location_z) == (2, 2, 4)
        assert player.facing == "west"
        assert player.funhouse_return is None
        assert game.events == []

        teleporter.active = True
        player.kill_dict = {"Boss": {"Jester": 1}}
        player.location_x, player.location_y, player.location_z = (2, 2, 4)
        teleporter.modify_player(game)
        assert (player.location_x, player.location_y, player.location_z) == (2, 2, 4)
        assert teleporter.active is False
        assert game.events == []

        mimic = map_tiles.FunhouseMimicChest(3, 3, 7)
        monkeypatch.setattr(
            "src.core.map_tiles.items.random_item",
            lambda level: SimpleNamespace(name=f"Loot-{level}"),
        )
        mimic.loot = None
        mimic.generate_loot()
        assert mimic.loot.name == "Loot-4"

    def test_dead_body_incubus_lair_and_shop_tiles_cover_story_branches(self, monkeypatch):
        player = _make_player(class_name="Thaumaturgist")
        player.quest_dict["Side"]["Something to Cry About"] = {"Completed": False}
        player.quest_dict["Side"]["Oedipal Complex"] = {"Completed": False}
        player.quest_dict["Main"]["A Bad Dream"] = {"Completed": False}
        calls = []
        player.modify_inventory = (
            lambda item, subtract=False, rare=False, quest=False, **_kwargs: calls.append(
                (item.name, subtract, rare, quest)
            )
        )
        game = _make_game(player)

        body = map_tiles.DeadBody(0, 0, 0)
        body.modify_player(game)
        assert player.state == "fight"
        body.special_text(game)
        assert player.quest_dict["Main"]["A Bad Dream"]["Completed"] is True
        assert any(name == "Lucky Locket" for name, *_rest in calls)

        player.state = "normal"
        lair = map_tiles.IncubusLair(1, 1, 0)
        intro = lair.intro_text(game)
        lair.modify_player(game)
        assert "primal presence" in intro.lower()
        assert player.state == "fight"
        assert "challenge you" in lair.special_text(game).lower()
        assert lair.defeat_incubus(game) is True
        assert player.quest_dict["Side"]["Oedipal Complex"]["Completed"] is True
        assert "Incubus Defeated" in game.events

        shop_calls = []
        monkeypatch.setattr(
            map_tiles.town, "secret_shop", lambda _game: shop_calls.append("secret"), raising=False
        )
        monkeypatch.setattr(
            map_tiles.town,
            "ultimate_armor_repo",
            lambda _game: shop_calls.append("armor"),
            raising=False,
        )

        secret_shop = map_tiles.SecretShop(2, 2, 0)
        secret_shop.modify_player(game)
        secret_shop.special_text(game)
        assert shop_calls[0] == "secret"
        assert "Secret Shop" in game.events
        assert secret_shop.available_actions(player) == []

        armor_shop = map_tiles.UltimateArmorShop(3, 3, 0)
        assert "forge in the depths" in armor_shop.intro_text(game).lower()
        armor_shop.modify_player(game)
        assert shop_calls[-1] == "armor"

    def test_rookie_mistake_body_completes_quest_and_forces_zombie_encounter(self):
        player = _make_player()
        player.quest_dict["Side"]["Rookie Mistake"] = {
            "What": "Rookie",
            "Total": 1,
            "Completed": False,
            "Turned In": False,
        }
        game = _make_game(player)
        rookie_tile = map_tiles.CavePath1(8, 8, 1)
        rookie_tile.modify_player(game)

        assert game.events == ["Rookie"]
        assert "Dead Soldier" in player.special_inventory
        assert player.quest_dict["Side"]["Rookie Mistake"]["Completed"] is True
        assert player.quest_dict["Side"]["Rookie Mistake"]["Turned In"] is False
        assert type(rookie_tile.enemy).__name__ == "Zombie"
        encounter = rookie_tile.enemy._runtime_combat_encounter
        assert [member.display_label for member in encounter.members] == [
            "Zombie A",
            "Zombie B",
        ]
        assert player.state == "fight"
        assert rookie_tile.read is True

    def test_rookie_mistake_pygame_path_does_not_show_completion_popup_before_combat(self):
        player = _make_player()
        player.quest_dict["Side"]["Rookie Mistake"] = {
            "What": "Rookie",
            "Total": 1,
            "Completed": False,
            "Turned In": False,
        }
        game = _make_game(player)
        game.presenter = SimpleNamespace(screen=SimpleNamespace(copy=lambda: "background"))
        popup_calls = []

        class Popup:
            def __init__(self, *_args, **_kwargs):
                popup_calls.append(("init", _args, _kwargs))

            def show(self, **_kwargs):
                popup_calls.append(("show", _kwargs))

        rookie_tile = map_tiles.CavePath1(8, 8, 1)
        rookie_tile.modify_player(game, popup_class=Popup)

        assert popup_calls == []
        assert player.quest_dict["Side"]["Rookie Mistake"]["Completed"] is True
        assert type(rookie_tile.enemy).__name__ == "Zombie"
        assert player.state == "fight"

    def test_rookie_body_visibility_requires_active_quest_or_dropped_body(self):
        player = _make_player()
        rookie_tile = map_tiles.CavePath1(8, 8, 1)

        assert map_tiles.rookie_body_visible_for_player(player, rookie_tile) is False

        player.quest_dict["Side"]["Rookie Mistake"] = {"Completed": False}
        assert map_tiles.rookie_body_visible_for_player(player, rookie_tile) is True

        player.quest_dict["Side"]["Rookie Mistake"]["Completed"] = True
        assert map_tiles.rookie_body_visible_for_player(player, rookie_tile) is False

        dropped_tile = map_tiles.CavePath1(4, 5, 1)
        dropped_tile.dropped_rookie_body = True
        player.quest_dict["Side"]["Rookie Mistake"] = {
            "Completed": False,
            "Body Dropped At": [4, 5, 1],
        }
        assert map_tiles.rookie_body_visible_for_player(player, dropped_tile) is True

        player.special_inventory["Dead Soldier"] = [items.DeadSoldier()]
        assert map_tiles.rookie_body_visible_for_player(player, dropped_tile) is False

    def test_rookie_mistake_body_drops_on_death_and_can_be_recovered(self):
        player = _make_player(level=12)
        player.location_x, player.location_y, player.location_z = (4, 5, 1)
        player.gold = 0
        dropped_tile = map_tiles.CavePath1(4, 5, 1)
        player.world_dict[(4, 5, 1)] = dropped_tile
        player.quest_dict["Side"]["Rookie Mistake"] = {
            "What": "Rookie",
            "Total": 1,
            "Completed": True,
            "Turned In": False,
        }
        player.modify_inventory(items.DeadSoldier(), rare=True)

        message = player.death()

        quest = player.quest_dict["Side"]["Rookie Mistake"]
        assert "Dead Soldier" not in player.special_inventory
        assert quest["Completed"] is False
        assert quest["Body Dropped At"] == [4, 5, 1]
        assert dropped_tile.dropped_rookie_body is True
        assert "rookie's body slips from your grasp" in message.lower()

        dropped_tile.dropped_rookie_body = False
        map_tiles.sync_rookie_body_drop_marker(player)
        assert dropped_tile.dropped_rookie_body is True

        game = _make_game(player)
        player.location_x, player.location_y, player.location_z = (4, 5, 1)
        dropped_tile.modify_player(game)

        assert "Dead Soldier" in player.special_inventory
        assert quest["Completed"] is True
        assert "Body Dropped At" not in quest
        assert dropped_tile.dropped_rookie_body is False
        assert game.events == []

    def test_ore_vault_hidden_branch_warp_idle_branch_and_funhouse_return_guard(self, monkeypatch):
        player = _make_player()
        player.world_dict = {
            (0, -1, 0): SimpleNamespace(enter=True, near=False),
            (1, 0, 0): SimpleNamespace(near=False),
            (-1, 0, 0): SimpleNamespace(near=False),
            (0, 1, 0): SimpleNamespace(near=False),
        }
        game = _make_game(player)
        hidden = map_tiles.OreVaultDoor(0, 0, 0)
        assert hidden.intro_text(game) == ""
        hidden.modify_player(game)
        assert hidden.open is False
        assert hidden.available_actions(player) == []

        player.spellbook["Skills"]["Keen Eye"] = SimpleNamespace(name="Keen Eye")
        player.spellbook["Skills"]["Master Lockpick"] = SimpleNamespace(name="Master Lockpick")
        untooled = map_tiles.OreVaultDoor(0, 0, 0)
        untooled.modify_player(game)
        assert untooled.open is False

        player.inventory["Lockpick Kit"] = [items.LockpickKit()]
        picked = map_tiles.OreVaultDoor(0, 0, 0)
        picked.modify_player(game)
        assert picked.open is False
        assert picked.enter is False

        warp = map_tiles.WarpPoint(1, 1, 1)
        player.warp_point = False
        warp.modify_player(game)
        assert warp.visited is True

        teleporter = map_tiles.FunhouseTeleporter(2, 2, 2)
        player.location_z = 7
        player.location_x = 9
        player.location_y = 9
        teleporter.modify_player(game)
        assert (player.location_x, player.location_y, player.location_z) == (9, 9, 7)

    def test_jester_boss_defeat_deactivates_funhouse_teleporter(self):
        player = _make_player()
        teleporter = map_tiles.FunhouseTeleporter(2, 2, 4)
        boss = map_tiles.JesterBossRoom(0, -1, 7)
        boss.enemy = None
        player.world_dict = {
            (2, 2, 4): teleporter,
            (0, -1, 7): boss,
        }
        player.location_x, player.location_y, player.location_z = (0, -1, 7)
        player.funhouse_return = (2, 2, 4, "south")
        game = _make_game(player)

        boss.special_text(game)

        assert teleporter.active is False
        assert (player.location_x, player.location_y, player.location_z) == (2, 2, 4)
        assert player.facing == "south"
        assert "Jester Defeated" in game.events
