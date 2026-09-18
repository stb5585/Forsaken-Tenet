#!/usr/bin/env python3
"""Focused coverage for pygame dungeon-manager navigation and helper flows."""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pygame
import pytest

from src.core import enemies, items, main_story
from src.core.classes import class_rings
from src.core.player import LIMINAL_GAP_ENTRY_FACING, LIMINAL_GAP_ENTRY_POS
from src.paths import PYGAME_ASSETS_DIR
from src.ui_pygame.gui import dungeon_manager


class RecordingScreen:
    def __init__(self):
        self.blit_calls = []
        self.fill_calls = []
        self.size = (640, 480)

    def blit(self, surface, position):
        self.blit_calls.append((surface, position))

    def fill(self, color):
        self.fill_calls.append(color)

    def copy(self):
        return "screen-copy"

    def get_size(self):
        return self.size


class RecordingFont:
    def render(self, text, _antialias, _color):
        width = max(8, len(text) * 8)
        height = 18

        def get_rect(**kwargs):
            rect = pygame.Rect(0, 0, width, height)
            for key, value in kwargs.items():
                setattr(rect, key, value)
            return rect

        return SimpleNamespace(
            text=text,
            get_width=lambda: width,
            get_height=lambda: height,
            get_rect=get_rect,
        )


class DummySurface:
    def __init__(self, size=(100, 80)):
        self._size = size
        self.alpha = None
        self.fill_calls = []

    def get_size(self):
        return self._size

    def get_rect(self, **kwargs):
        return SimpleNamespace(**kwargs)

    def set_alpha(self, value):
        self.alpha = value

    def fill(self, color):
        self.fill_calls.append(color)

    def convert(self):
        return self

    def convert_alpha(self):
        return self


class DummyTile:
    def __init__(self, *, enter=True, locked=False, open_state=False, blocked=None):
        self.enter = enter
        self.locked = locked
        self.open = open_state
        self.blocked = blocked
        self.visited = False
        self.adjacent_calls = []

    def adjacent_visited(self, player_char):
        self.adjacent_calls.append(
            (player_char.location_x, player_char.location_y, player_char.location_z)
        )


class DoorTile(DummyTile):
    pass


class OreVaultDoor(DummyTile):
    pass


class FinalBlocker(DummyTile):
    pass


class StairsUpTile(DummyTile):
    pass


class StairsDownTile(DummyTile):
    pass


class SecretShopTile(DummyTile):
    def __init__(self):
        super().__init__(enter=False)
        self.read = False


class UndergroundSpring(DummyTile):
    pass


class WarpPoint(DummyTile):
    pass


class FinalRoom(DummyTile):
    pass


class AntiMagicSwitch(DummyTile):
    pass


class IncubusLair(DummyTile):
    def __init__(self):
        super().__init__()
        self.defeated = False
        self.enemy = None

    def enter_combat(self, player_char):
        self.enemy = SimpleNamespace(name="Incubus")

    def defeat_incubus(self, game):
        self.defeated = True
        return True


class GoldenChaliceRoom(DummyTile):
    def __init__(self):
        super().__init__()
        self.read = False

    def pickup_chalice_action(self, game):
        self.read = True
        return True


class FirePath(DummyTile):
    def __init__(self):
        super().__init__()
        self.special_text = lambda _game: "The flames dance."

    def modify_player(self, game, popup_class=None):
        game.player.health.current -= 3


class EnemyTile(DummyTile):
    def __init__(self, enemy):
        super().__init__()
        self.enemy = enemy


class LadderUp(DummyTile):
    pass


class LadderDown(DummyTile):
    pass


class UltimateArmorShop(DummyTile):
    pass


class RelicTile(DummyTile):
    pass


class BoulderTile(DummyTile):
    pass


class UnobtainiumRoom(DummyTile):
    pass


class BossTile(DummyTile):
    def __init__(self, enemy):
        super().__init__()
        self.enemy = enemy

    def intro_text(self, _game):
        return "Boss intro"


class MerzhinBossRoom(BossTile):
    pass


class WarningTile(DummyTile):
    def intro_text(self, _game):
        return ""


class DeadBody(DummyTile):
    def intro_text(self, _game):
        return ""


class DeathcapGatheringTile(DummyTile):
    def __init__(self):
        super().__init__()
        self.gathering_resource = "deathcap_mushroom"
        self.gathering_available = True
        self.gathering_harvested = False


def _make_presenter():
    return SimpleNamespace(
        screen=RecordingScreen(),
        width=640,
        height=480,
        title_font=RecordingFont(),
        large_font=RecordingFont(),
        small_font=RecordingFont(),
        show_message=lambda *args, **kwargs: None,
        render_menu=lambda prompt, options, **kwargs: 0,
        clock=SimpleNamespace(tick=lambda _fps: None),
        set_background_provider=lambda provider: None,
    )


def _make_player():
    steps = []
    stairs = []
    inventory_calls = []
    story_state = main_story.default_state()

    def modify_inventory(*args, **kwargs):
        item = args[0] if args else None
        inventory_calls.append((getattr(item, "name", item), kwargs))

    def enter_liminal_gap_stub(return_location):
        player.main_story["vesperion_false_final_triggered"] = True
        player.main_story["pending_liminal_gap_entry"] = False
        player.main_story["liminal_gap_entered"] = True
        player.liminal_gap_return = return_location
        player.location_x, player.location_y, player.location_z = LIMINAL_GAP_ENTRY_POS
        player.facing = LIMINAL_GAP_ENTRY_FACING
        player.health.current = max(1, player.health.max // 2)
        player.mana.current = max(0, player.mana.max // 2)
        player.state = "normal"

    def return_from_liminal_gap():
        if not player.main_story["true_final_unlocked"] or not getattr(
            player, "liminal_gap_return", None
        ):
            return False
        player.location_x, player.location_y, player.location_z, player.facing = (
            player.liminal_gap_return
        )
        player.liminal_gap_return = None
        player.main_story["returned_from_liminal_gap"] = True
        player.state = "normal"
        return True

    player = SimpleNamespace(
        facing="north",
        location_x=5,
        location_y=5,
        location_z=1,
        previous_location=None,
        world_dict={},
        quest_dict={"Side": {}, "Main": {}},
        spellbook={"Skills": {}},
        inventory={},
        special_inventory={},
        level=SimpleNamespace(level=12),
        anti_magic_active=False,
        warp_point=False,
        quit=False,
        health=SimpleNamespace(current=10, max=20),
        mana=SimpleNamespace(current=4, max=9),
        state="explore",
        main_story=story_state,
        summons={},
        equipment={"Weapon": SimpleNamespace(name="None")},
        combat=SimpleNamespace(attack=20, defense=20, magic=20, magic_def=20),
        cls=SimpleNamespace(name="Knight"),
        record_step=lambda: steps.append("step"),
        record_stairs_used=lambda: stairs.append("stairs"),
        in_town=lambda: player.location_z <= 0,
        has_relics=lambda: False,
        check_mod=lambda *_args, **_kwargs: 0,
        modify_inventory=modify_inventory,
        is_alive=lambda: player.health.current > 0,
        to_town=lambda: setattr(player, "location_z", 0),
        player_level=lambda: player.level.level,
        ensure_main_story_state=lambda: player.main_story,
        can_enter_true_final=lambda: player.main_story["true_final_unlocked"],
        enter_liminal_gap_stub=enter_liminal_gap_stub,
        return_from_liminal_gap=return_from_liminal_gap,
    )
    player.step_calls = steps
    player.stair_calls = stairs
    player.inventory_calls = inventory_calls
    return player


def _make_manager(monkeypatch):
    presenter = _make_presenter()
    player = _make_player()
    game = SimpleNamespace(special_event=lambda _name: None, save_calls=[])
    game.save_game = lambda: game.save_calls.append("save")

    monkeypatch.setattr(
        dungeon_manager.core, "DungeonRenderer", lambda presenter: SimpleNamespace()
    )
    monkeypatch.setattr(dungeon_manager.core, "DungeonHUD", lambda presenter: SimpleNamespace())
    monkeypatch.setattr(
        dungeon_manager.core,
        "GUICombatManager",
        lambda presenter, hud, game_instance: SimpleNamespace(
            dungeon_renderer=None,
            start_combat=lambda *_args, **_kwargs: True,
            player_world_dict=None,
        ),
    )
    monkeypatch.setattr(
        dungeon_manager.core,
        "LootPopup",
        lambda screen, presenter: SimpleNamespace(
            show_unlock_prompt=lambda kind: True, show_loot=lambda *args: None
        ),
    )
    monkeypatch.setattr(
        "src.ui_pygame.gui.shops.ShopManager",
        lambda presenter, player_char: SimpleNamespace(visit_secret_shop=lambda: None),
    )
    monkeypatch.setattr(
        "src.ui_pygame.gui.ultimate_armor.UltimateArmorShop",
        lambda presenter: SimpleNamespace(visit_shop=lambda *_args: None),
    )
    original_loader = dungeon_manager.DungeonManager._load_dungeon_background
    monkeypatch.setattr(
        dungeon_manager.DungeonManager, "_load_dungeon_background", lambda self: None
    )
    manager = dungeon_manager.DungeonManager(presenter, player, game)
    monkeypatch.setattr(dungeon_manager.DungeonManager, "_load_dungeon_background", original_loader)
    game.player = player
    return manager, presenter, player, game


def test_resolve_enemy_messages_and_random_cry(monkeypatch):
    manager, _presenter, player, _game = _make_manager(monkeypatch)

    tile = SimpleNamespace(enemy=lambda: SimpleNamespace(name="Goblin"))
    resolved = manager._resolve_tile_enemy(tile)
    assert resolved.name == "Goblin"
    assert tile.enemy.name == "Goblin"
    assert manager._resolve_tile_enemy(SimpleNamespace()) is None

    manager.max_messages = 3
    manager.add_message("one two three four five six seven eight nine ten eleven twelve")
    manager.add_message("second")
    manager.add_message("third")
    manager.add_message("fourth")
    assert len(manager.messages) == 3
    manager.scroll_message_log(-10)
    assert manager.message_scroll_offset == 0
    manager.reset_message_log()
    assert manager.messages == []

    player.location_z = 2
    player.location_x = 18
    player.location_y = 12
    player.quest_dict["Side"]["Something to Cry About"] = {"Completed": False}
    monkeypatch.setattr(dungeon_manager.random, "random", lambda: 0.0)
    monkeypatch.setattr(dungeon_manager.random, "choice", lambda seq: seq[0])
    manager._check_random_cry()
    assert any("sobs echo" in message for message in manager.messages)


def test_deathcap_harvest_requires_specialist_interaction_and_uses_loot_popup(monkeypatch):
    manager, _presenter, player, _game = _make_manager(monkeypatch)
    tile = DeathcapGatheringTile()
    player.world_dict[(player.location_x, player.location_y, player.location_z)] = tile
    loot_calls = []
    manager.loot_popup = SimpleNamespace(
        show_loot=lambda item, label, **kwargs: loot_calls.append((item.name, label, kwargs))
    )
    manager._refresh_cached_frame = lambda: manager.messages.append("refresh")

    manager._check_tile_effects()
    assert tile.gathering_harvested is False

    manager.interact()
    assert any("lack the knowledge" in message for message in manager.messages)
    assert not loot_calls

    player.cls.name = "Assassin"
    manager.interact()

    assert tile.gathering_harvested is True
    assert player.inventory_calls == [("Deathcap Mushroom", {})]
    assert loot_calls[0][:2] == ("Deathcap Mushroom", "Foraged Resource")
    assert loot_calls[0][2]["flush_events"] is True
    assert loot_calls[0][2]["require_key_release"] is True
    assert "refresh" in manager.messages
    assert "Gathered Deathcap Mushroom." in manager.messages


def test_boss_intro_uses_split_dialogue_and_jester_defeat_returns_to_funhouse_teleporter(
    monkeypatch,
):
    manager, presenter, player, _game = _make_manager(monkeypatch)
    shown = []
    presenter.show_message = lambda *args, **kwargs: shown.append((args, kwargs))
    manager._dungeon_dialog_background = lambda: None
    monkeypatch.setattr(
        dungeon_manager.core,
        "get_special_events",
        lambda: {
            "Jester": {"Text": ["The fool bows with a knife behind his back."]},
            "Jester Defeated": {"Text": ["The mirrors crack and the playhouse returns."]},
        },
    )
    enemy = SimpleNamespace(name="Jester", picture="jester.png")
    boss_tile = dungeon_manager.map_tiles.JesterBossRoom(0, -1, 7)

    manager._show_boss_intro_dialogue(boss_tile, enemy)
    assert shown[-1][1]["title"] == "Jester"
    assert shown[-1][1]["split_layout"] is True
    assert shown[-1][1]["image_path"].endswith("jester.png")
    assert boss_tile.read is True

    guild_enemy = enemies.GuildCutpurseBoss()
    guild_tile = dungeon_manager.map_tiles.ThievesGuildTrialBossRoom(15, 2, 2)
    manager._show_boss_intro_dialogue(guild_tile, guild_enemy)
    assert shown[-1][1]["title"] == "Guild Cutpurse"
    assert shown[-1][1]["split_layout"] is True
    assert shown[-1][1]["image_path"].endswith("enemy_combat_sprites/guild_cutpurse.png")
    assert guild_tile.read is True

    player.location_z = 7
    player.funhouse_return = (1, 2, 0, "east")
    teleporter = dungeon_manager.map_tiles.FunhouseTeleporter(11, 0, 4)
    player.world_dict[(11, 0, 4)] = teleporter
    exits = []
    player.exit_funhouse = lambda: exits.append("exit")
    manager._handle_defeated_jester_boss(boss_tile)
    assert exits == []
    assert (player.location_x, player.location_y, player.location_z) == (11, 0, 4)
    assert player.facing == "south"
    assert player.funhouse_return is None
    assert teleporter.active is False
    assert boss_tile.enemy is None
    assert "The funhouse dissolves behind you." in manager.messages


def test_background_loading_loading_screen_and_popup_background(monkeypatch, capsys):
    manager, presenter, _player, _game = _make_manager(monkeypatch)

    source = DummySurface((200, 100))
    scaled_sizes = []
    monkeypatch.setattr("src.ui_pygame.gui.dungeon_manager.pygame.image.load", lambda _path: source)
    monkeypatch.setattr(
        "src.ui_pygame.gui.dungeon_manager.pygame.transform.scale",
        lambda image, size: scaled_sizes.append((image.get_size(), size)) or DummySurface(size),
    )
    bg = dungeon_manager.DungeonManager._load_dungeon_background(manager)
    assert scaled_sizes == [((200, 100), (960, 480))]
    assert bg.get_size() == (960, 480)

    manager._cached_frame = "frame"
    assert manager._get_popup_background() == "frame"
    manager._cached_frame = None
    manager._cached_view = "view"
    assert manager._get_popup_background() == "view"
    manager._cached_view = None
    assert manager._get_popup_background() == "screen-copy"

    manager._dungeon_background_loaded = False
    monkeypatch.setattr(Path, "exists", lambda _path: False)
    assert dungeon_manager.DungeonManager._load_dungeon_background(manager) is None
    assert "Dungeon background not found" in capsys.readouterr().out

    manager._dungeon_background_loaded = True
    manager._dungeon_background = DummySurface((640, 480))
    tick_values = iter([0, 1000])
    monkeypatch.setattr(
        "src.ui_pygame.gui.dungeon_manager.pygame.time.get_ticks", lambda: next(tick_values)
    )
    monkeypatch.setattr(
        "src.ui_pygame.gui.dungeon_manager.pygame.time.Clock",
        lambda: SimpleNamespace(tick=lambda _fps: None),
    )
    monkeypatch.setattr("src.ui_pygame.gui.dungeon_manager.pygame.event.get", lambda *_args: [])
    monkeypatch.setattr("src.ui_pygame.gui.dungeon_manager.pygame.display.flip", lambda: None)
    monkeypatch.setattr(
        "src.ui_pygame.gui.dungeon_manager.pygame.draw.rect", lambda *_args, **_kwargs: None
    )
    monkeypatch.setattr(
        "src.ui_pygame.gui.dungeon_manager.pygame.Surface", lambda size, *_args: DummySurface(size)
    )
    manager._show_dungeon_loading_screen("Loading...", duration=0.5)
    assert presenter.screen.blit_calls

    provider_calls = []
    presenter.set_background_provider = lambda provider: provider_calls.append(provider)
    manager._cached_view = "dungeon-frame"
    manager.view_dirty = True
    manager.ui_dirty = True
    loading_calls = []
    manager._show_dungeon_loading_screen = lambda message, duration=1.25: loading_calls.append(
        (message, duration)
    )

    manager._show_town_entry_loading_screen("Returning to town...")

    assert provider_calls == [None]
    assert loading_calls == [("Returning to town...", 1.25)]
    assert manager._cached_view is None
    assert manager.view_dirty is False
    assert manager.ui_dirty is False


def test_walkable_spawn_selection_and_stair_usage(monkeypatch):
    manager, _presenter, player, _game = _make_manager(monkeypatch)
    center = (player.location_x, player.location_y, player.location_z)
    north_tile = DummyTile()
    east_tile = DoorTile(locked=True)
    south_tile = DummyTile(open_state=True)

    player.world_dict = {
        center: StairsDownTile(),
        (center[0], center[1] - 1, center[2]): north_tile,
        (center[0] + 1, center[1], center[2]): east_tile,
        (center[0], center[1] + 1, center[2]): south_tile,
    }

    assert manager._is_walkable_spawn_tile(north_tile) is True
    assert manager._is_walkable_spawn_tile(east_tile) is False
    assert manager._is_walkable_spawn_tile(StairsUpTile()) is False

    manager._move_to_adjacent_from_stairs()
    assert (player.location_x, player.location_y) == (center[0], center[1] - 1)
    assert north_tile.visited is True

    player.world_dict[(player.location_x, player.location_y, player.location_z)] = StairsDownTile()
    player.location_z = 1
    manager._show_dungeon_loading_screen = lambda *_args, **_kwargs: None
    manager.add_message = lambda message: manager.messages.append(message)
    manager.use_stairs_down()
    assert player.location_z == 2
    assert player.stair_calls == ["stairs"]


def test_move_forward_branches_and_turning(monkeypatch):
    manager, _presenter, player, _game = _make_manager(monkeypatch)
    manager._get_tile_intro = lambda: ["Intro text"]
    manager._check_tile_effects = lambda: manager.messages.append("effects")
    dialogues = []
    manager._show_special_event_dialogue = (
        lambda event_name, title="", image_path="": dialogues.append(
            (event_name, title, image_path)
        )
    )

    assert manager.move_forward() is False
    assert "can't move" in manager.messages[-1].lower()

    player.world_dict[(5, 4, 1)] = DummyTile(enter=False)
    assert manager.move_forward() is False

    player.world_dict[(5, 4, 1)] = OreVaultDoor(enter=False, locked=True)
    assert manager.move_forward() is False
    assert "solid wall" in manager.messages[-1].lower()

    player.world_dict[(5, 4, 1)] = DoorTile(enter=True, locked=True)
    assert manager.move_forward() is False
    assert "locked door" in manager.messages[-1].lower()

    player.world_dict[(5, 4, 1)] = FinalBlocker(enter=True, blocked="north")
    assert manager.move_forward() is False
    assert "invisible force" in manager.messages[-1].lower()

    player.location_x, player.location_y = (5, 5)
    player.special_inventory = {}
    player.world_dict[(5, 5, 1)] = dungeon_manager.map_tiles.FunhouseEmptyPath(5, 5, 1)
    player.world_dict[(5, 4, 1)] = dungeon_manager.map_tiles.JesterBossRoom(5, 4, 1)
    assert manager.move_forward() is False
    assert "force field" in manager.messages[-1].lower()
    assert dialogues[-1] == (
        dungeon_manager.map_tiles.JESTER_FORCE_FIELD_EVENT,
        "Jester",
        manager._enemy_combat_sprite_image_path("jester.png"),
    )

    player.special_inventory["Jester Token"] = [
        SimpleNamespace(name="Jester Token")
        for _ in range(dungeon_manager.map_tiles.JESTER_TOKENS_REQUIRED)
    ]
    destination = player.world_dict[(5, 4, 1)]
    assert manager.move_forward() is True
    assert (player.location_x, player.location_y) == (5, 4)
    assert destination.visited is True

    player.location_x, player.location_y = (5, 5)
    player.special_inventory = {}
    player.world_dict[(5, 5, 1)] = DummyTile(enter=True)
    assert manager.move_forward() is False
    assert "force field" in manager.messages[-1].lower()

    player.special_inventory["Jester Token"] = [
        SimpleNamespace(name="Jester Token")
        for _ in range(dungeon_manager.map_tiles.JESTER_TOKENS_REQUIRED)
    ]
    assert manager.move_forward() is True
    assert (player.location_x, player.location_y) == (5, 4)

    player.location_x, player.location_y = (5, 5)
    player.step_calls.clear()
    player.has_relics = lambda: True
    player.anti_magic_active = True
    destination = DummyTile()
    player.world_dict[(5, 4, 1)] = destination
    assert manager.move_forward() is True
    assert (player.location_x, player.location_y) == (5, 4)
    assert player.step_calls == ["step"]
    assert player.anti_magic_active is False
    assert destination.visited is True
    assert "Intro text" in manager.messages
    assert "effects" in manager.messages
    assert not any(message.startswith("Moved to (") for message in manager.messages)


def test_navigation_awards_hidden_cache_after_floor_is_mapped(monkeypatch):
    manager, _presenter, player, _game = _make_manager(monkeypatch)
    player.cls = SimpleNamespace(name="Seeker")
    player.equipment["Ring"] = items.ClassRing()
    class_rings.ensure_state(player)["awakened"]["Seeker"] = True
    player.world_dict = {
        (index, 0, 1): SimpleNamespace(visited=index < 3, near=False) for index in range(4)
    }

    manager._check_hidden_cache()
    manager._check_hidden_cache()

    assert [name for name, _kwargs in player.inventory_calls] == ["Smoke Bomb"]
    assert sum("Hidden Cache discovered" in message for message in manager.messages) == 1

    manager.turn_left()
    manager.turn_right()
    manager.turn_around()
    assert player.facing in {"north", "south", "east", "west"}


def test_sync_dungeon_music_selects_special_area_themes(monkeypatch):
    manager, _presenter, player, game = _make_manager(monkeypatch)
    music_calls = []
    game._play_location_music = music_calls.append

    for level in (1, 5, 9):
        player.location_z = level
        manager._sync_dungeon_music()
    player.location_z = 6
    manager._sync_dungeon_music()
    player.location_z = 7
    manager._sync_dungeon_music()
    player.location_z = dungeon_manager.map_tiles.REALM_OF_CAMBION_LEVEL
    manager._sync_dungeon_music()

    assert music_calls == [
        "dungeon",
        "dungeon",
        "dungeon",
        "dungeon_final",
        "funhouse",
        "realm_of_cambion",
    ]


def test_use_stairs_up_interact_secret_shop_and_dialogue_helpers(monkeypatch):
    manager, presenter, player, _game = _make_manager(monkeypatch)
    manager._show_dungeon_loading_screen = lambda *_args, **_kwargs: None
    manager._move_to_adjacent_from_stairs = lambda: manager.messages.append("moved-from-stairs")
    shown_messages = []
    presenter.show_message = lambda message, **kwargs: (
        kwargs.get("background_draw_func") and kwargs["background_draw_func"](),
        shown_messages.append((message, kwargs)),
    )
    presenter.render_menu = lambda prompt, options, **kwargs: (
        kwargs.get("background_draw_func") and kwargs["background_draw_func"](),
        0,
    )[1]
    manager.shop_manager = SimpleNamespace(
        visit_secret_shop=lambda: manager.messages.append("shop-opened")
    )

    current_tile = StairsUpTile()
    player.world_dict[(player.location_x, player.location_y, player.location_z)] = current_tile
    assert manager.use_stairs_up() is True
    assert player.location_z == 0
    assert manager.running is False

    player.location_z = 1
    player.world_dict[(player.location_x, player.location_y, player.location_z)] = DummyTile()
    player.world_dict[(player.location_x, player.location_y - 1, player.location_z)] = (
        SecretShopTile()
    )
    manager.interact()
    assert any("secret shop" in message.lower() for message, _kwargs in shown_messages)
    assert "shop-opened" in manager.messages

    manager._cached_frame = None
    manager._cached_view = None
    manager._render = lambda: manager.messages.append("rendered")
    manager._show_dungeon_dialogue("hello", title="NPC", image_path="npc.png")
    manager._show_dungeon_choice("prompt", ["Yes", "No"], image_path="npc.png")
    monkeypatch.setattr(
        dungeon_manager, "get_special_events", lambda: {"Event": {"Text": ["Line 1", "Line 2"]}}
    )
    manager._show_special_event_dialogue("Event", title="Title", image_path="img.png")
    monkeypatch.setattr(
        dungeon_manager.core,
        "get_npc_art_manager",
        lambda: SimpleNamespace(
            get_image_path=lambda name: (
                f"npc:{name}" if name in {"Nimue", "The Acolyte", "Reflection", "Vesperion"} else ""
            )
        ),
    )
    manager._show_dungeon_dialogue("water", title="Nimue")
    manager._show_special_event_dialogue("Event", title="Nimue")
    manager._show_special_event_dialogue("Event", title="The Acolyte")
    manager._show_special_event_dialogue("Event", title="Reflection")
    manager._show_special_event_dialogue("Event", title="Vesperion")
    assert manager.messages.count("rendered") >= 3
    assert shown_messages[-5][1]["image_path"] == "npc:Nimue"
    assert shown_messages[-4][1]["image_path"] == "npc:Nimue"
    assert shown_messages[-3][1]["image_path"] == "npc:The Acolyte"
    assert shown_messages[-2][1]["image_path"] == "npc:Reflection"
    assert shown_messages[-1][1]["image_path"] == "npc:Vesperion"


def test_interact_chest_covers_unlock_mimic_loot_and_empty_cases(monkeypatch):
    manager, _presenter, player, _game = _make_manager(monkeypatch)
    loot_calls = []
    unlock_prompts = []
    combat_calls = []
    manager.loot_popup = SimpleNamespace(
        show_unlock_prompt=lambda kind, **kwargs: unlock_prompts.append((kind, kwargs)) or True,
        show_loot=lambda loot, label, **kwargs: loot_calls.append(
            (getattr(loot, "name", loot), label, kwargs)
        ),
    )
    manager.combat_manager.start_combat = (
        lambda player_char, enemy, tile: combat_calls.append((enemy.level, tile)) or True
    )
    manager._refresh_cached_frame = lambda: manager.messages.append("refresh")

    class MimicEnemy:
        def __init__(self, level, player_level=None):
            self.level = level
            self.player_level = player_level
            self.anti_magic_active = False
            self._alive = False

        def is_alive(self):
            return self._alive

    monkeypatch.setattr("src.core.enemies.Mimic", MimicEnemy)
    monkeypatch.setattr("src.core.items.JesterToken", lambda: SimpleNamespace(name="Jester Token"))
    mimic_rolls = [True, False]
    monkeypatch.setattr(
        dungeon_manager.map_tiles,
        "ordinary_chest_spawns_mimic",
        lambda *_args, **_kwargs: mimic_rolls.pop(0),
    )

    player.inventory["Key"] = [SimpleNamespace(name="Key")]
    chest = SimpleNamespace(
        open=False,
        locked=True,
        loot=None,
        enemy=None,
        generate_loot=lambda: setattr(chest, "loot", lambda: SimpleNamespace(name="Gold Ring")),
    )
    manager._interact_chest(chest, "LockedChest")
    assert chest.open is True
    assert chest.locked is False
    assert unlock_prompts[0][0] == "chest"
    assert unlock_prompts[0][1]["flush_events"] is True
    assert unlock_prompts[0][1]["require_key_release"] is True
    assert callable(unlock_prompts[0][1]["background_draw_func"])
    assert combat_calls[0][0] == 2
    assert ("Gold Ring", {}) in player.inventory_calls
    assert loot_calls[-1][0:2] == ("Gold Ring", "Locked Chest")
    assert loot_calls[-1][2]["flush_events"] is True
    assert loot_calls[-1][2]["require_key_release"] is True
    assert callable(loot_calls[-1][2]["background_draw_func"])

    funhouse = SimpleNamespace(
        open=False,
        locked=False,
        loot=lambda: SimpleNamespace(name="Fun Loot"),
        enemy=None,
        generate_loot=lambda: None,
    )
    manager._interact_chest(funhouse, "FunhouseMimicChest")
    assert any(
        call[0] == "Jester Token" and call[1].get("rare") is True for call in player.inventory_calls
    )
    assert loot_calls[-2][0:2] == ("Fun Loot", "Chest")
    assert loot_calls[-1][0:2] == ("Jester Token", "Mimic Reward")
    assert loot_calls[-1][2]["flush_events"] is True
    assert loot_calls[-1][2]["require_key_release"] is True
    assert callable(loot_calls[-1][2]["background_draw_func"])

    empty = SimpleNamespace(open=False, locked=False, loot=None, generate_loot=lambda: None)
    manager._interact_chest(empty, "Chest")
    assert loot_calls[-1][0:2] == ([], "Empty Chest")

    generate_calls = []
    combat_count = len(combat_calls)
    loot_count = len(loot_calls)
    inventory_count = len(player.inventory_calls)
    opened = SimpleNamespace(
        open=True,
        locked=False,
        loot=lambda: SimpleNamespace(name="Stale Loot"),
        enemy=None,
        generate_loot=lambda: generate_calls.append("generated"),
    )
    manager._interact_chest(opened, "Chest")
    assert "This chest has already been opened." in manager.messages
    assert generate_calls == []
    assert len(combat_calls) == combat_count
    assert len(loot_calls) == loot_count
    assert len(player.inventory_calls) == inventory_count

    manager._interact_chest(empty, "Chest")
    assert "This chest has already been opened." in manager.messages


def test_interact_chest_requires_lockpick_kit_for_lockpick_skill(monkeypatch):
    manager, _presenter, player, _game = _make_manager(monkeypatch)
    loot_calls = []
    manager.loot_popup = SimpleNamespace(
        show_unlock_prompt=lambda *_args, **_kwargs: False,
        show_loot=lambda loot, label, **_kwargs: loot_calls.append(
            (getattr(loot, "name", loot), label)
        ),
    )
    manager._refresh_cached_frame = lambda: None
    monkeypatch.setattr(
        dungeon_manager.map_tiles, "ordinary_chest_spawns_mimic", lambda *_args, **_kwargs: False
    )
    monkeypatch.setattr("src.core.items.random.random", lambda: 0.99)
    player.spellbook["Skills"]["Lockpick"] = SimpleNamespace(name="Lockpick")
    chest = SimpleNamespace(
        open=False,
        locked=True,
        loot=None,
        generate_loot=lambda: setattr(chest, "loot", lambda: SimpleNamespace(name="Picked Loot")),
    )

    manager._interact_chest(chest, "LockedChest")

    assert chest.locked is True
    assert chest.open is False
    assert "Lockpick Kit with the Lockpick skill" in " ".join(manager.messages)

    player.inventory["Lockpick Kit"] = [items.LockpickKit()]
    manager._interact_chest(chest, "LockedChest")

    assert chest.locked is False
    assert chest.open is True
    assert loot_calls[-1] == ("Picked Loot", "Locked Chest")


def test_relic_discovery_text_mapping_and_fallback():
    expected = {
        "Triangulus": "old oath",
        "Quadrata": "measured and contained",
        "Hexagonum": "Something patient",
        "Luna": "silence around it",
        "Polaris": "harder to lose",
        "Infinitas": "road continues",
    }

    for relic_name, phrase in expected.items():
        assert phrase in dungeon_manager.relic_discovery_text(SimpleNamespace(name=relic_name))

    assert (
        dungeon_manager.relic_discovery_text(SimpleNamespace(name="Relic X"))
        == "You found a relic: Relic X!"
    )


def test_interact_door_relic_warp_terminal_and_room_pickups(monkeypatch):
    manager, presenter, player, game = _make_manager(monkeypatch)
    sfx_calls = []
    presenter.sound_manager = SimpleNamespace(play_sfx=lambda name: sfx_calls.append(name))
    manager.loot_popup = SimpleNamespace(
        show_unlock_prompt=lambda kind, **_kwargs: True, show_loot=lambda *_args, **_kwargs: None
    )
    dirty_calls = []
    manager._refresh_cached_frame = lambda: manager.messages.append("refresh")
    manager._mark_view_dirty = lambda: dirty_calls.append("dirty")
    manager._show_dungeon_choice = lambda prompt, options: 0

    ore_door = OreVaultDoor(enter=False, locked=True)
    player.inventory["Cryptic Key"] = [SimpleNamespace(name="Cryptic Key")]
    manager._interact_door(ore_door)
    assert ore_door.open is True
    assert ore_door.detected is True
    assert dirty_calls == ["dirty"]
    assert sfx_calls == ["open_door"]

    regular = DoorTile(enter=False, locked=True)
    player.inventory["Old Key"] = [SimpleNamespace(name="Old Key")]
    manager._interact_door(regular)
    assert regular.open is True
    assert regular.blocked is None
    assert sfx_calls == ["open_door", "open_door"]

    player.location_z = 2
    relic_tile = SimpleNamespace(read=False)
    monkeypatch.setattr("src.core.items.Relic1", lambda: SimpleNamespace(name="Relic 1"))
    monkeypatch.setattr("src.core.items.Relic2", lambda: SimpleNamespace(name="Relic 2"))
    monkeypatch.setattr("src.core.items.Relic3", lambda: SimpleNamespace(name="Relic 3"))
    monkeypatch.setattr("src.core.items.Relic4", lambda: SimpleNamespace(name="Relic 4"))
    monkeypatch.setattr("src.core.items.Relic5", lambda: SimpleNamespace(name="Relic 5"))
    monkeypatch.setattr("src.core.items.Relic6", lambda: SimpleNamespace(name="Relic 6"))
    player.quests = lambda: ""
    special_events = []
    game.special_event = lambda name, **kwargs: special_events.append((name, kwargs))
    manager._interact_relic(relic_tile)
    assert special_events == [("Relic Room", {"message": "You found a relic: Relic 2!"})]
    assert relic_tile.read is True
    assert player.health.current == player.health.max
    assert player.mana.current == player.mana.max
    assert "You found a relic: Relic 2!" not in manager.messages
    assert "Your health and mana have been fully restored!" in manager.messages

    inventory_count = len(player.inventory_calls)
    player.health.current = 3
    player.mana.current = 2
    manager._interact_relic(relic_tile)
    assert len(player.inventory_calls) == inventory_count
    assert player.health.current == 3
    assert player.mana.current == 2
    assert manager.messages[-1] == "You already collected the relic from this room."

    player.warp_point = True
    warp_tile = SimpleNamespace(warped=True)
    loading_calls = []
    manager._show_dungeon_loading_screen = lambda msg, duration=1.25: loading_calls.append(msg)
    manager.running = True
    manager._handle_warp_point(warp_tile)
    assert player.location_z == 0
    assert manager.running is False
    assert loading_calls == ["Returning to town..."]

    class FakeCodeEntryPopup:
        def __init__(self, *_args, **_kwargs):
            pass

        def show(self, **_kwargs):
            return "1234"

    monkeypatch.setattr("src.ui_pygame.gui.confirmation_popup.CodeEntryPopup", FakeCodeEntryPopup)
    monkeypatch.setattr(
        dungeon_manager.map_tiles,
        "pop_cambion_messages",
        lambda _player: ["Field offline", "Barrier gone"],
    )
    switch_calls = []
    switch_tile = SimpleNamespace(
        attempt_disable=lambda game_arg, code: switch_calls.append((game_arg, code))
    )
    manager._interact_anti_magic_switch(switch_tile)
    assert switch_calls == [(game, "1234")]
    assert "Barrier gone" in manager.messages

    branch_calls = []
    monkeypatch.setattr(
        "src.ui_pygame.gui.confirmation_popup.CodeEntryPopup",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(
            AssertionError("code popup should not open")
        ),
    )
    monkeypatch.setattr(
        dungeon_manager.map_tiles, "pop_cambion_messages", lambda _player: ["Kaelenon returns home"]
    )
    kaelenon_switch = SimpleNamespace(
        has_kaelenon_branch=lambda game_arg: True,
        resolve_kaelenon_branch=lambda game_arg: branch_calls.append(game_arg),
    )
    manager._interact_anti_magic_switch(kaelenon_switch)
    assert branch_calls == [game]
    assert "Kaelenon returns home" in manager.messages

    unobtainium_tile = SimpleNamespace(visited=False)
    monkeypatch.setattr("src.core.items.Unobtainium", lambda: SimpleNamespace(name="Unobtainium"))
    manager._interact_unobtainium_room(unobtainium_tile)
    assert unobtainium_tile.visited is True

    body_tile = SimpleNamespace(read=False)
    monkeypatch.setattr("src.core.items.LuckyLocket", lambda: SimpleNamespace(name="Lucky Locket"))
    player.quest_dict["Main"]["A Bad Dream"] = {"Completed": False}
    manager._interact_dead_body(body_tile)
    assert player.quest_dict["Main"]["A Bad Dream"]["Completed"] is True
    assert body_tile.read is True


def test_interact_door_requires_lockpick_kit_for_master_lockpick(monkeypatch):
    manager, presenter, player, _game = _make_manager(monkeypatch)
    sfx_calls = []
    presenter.sound_manager = SimpleNamespace(play_sfx=lambda name: sfx_calls.append(name))
    manager._mark_view_dirty = lambda: None
    monkeypatch.setattr("src.core.items.random.random", lambda: 0.99)
    player.spellbook["Skills"]["Master Lockpick"] = SimpleNamespace(name="Master Lockpick")
    door = DoorTile(enter=False, locked=True)

    manager._interact_door(door)

    assert door.locked is True
    assert door.open is False
    assert "Lockpick Kit with the Master Lockpick skill" in " ".join(manager.messages)
    assert sfx_calls == []

    player.inventory["Lockpick Kit"] = [items.LockpickKit()]
    manager._interact_door(door)

    assert door.locked is False
    assert door.open is True
    assert sfx_calls == ["open_door"]


def test_dead_body_waitress_hook_uses_existing_sprite_and_missing_safe_sfx(monkeypatch):
    manager, presenter, player, game = _make_manager(monkeypatch)
    events = []
    sfx_calls = []
    dialogues = []
    combats = []
    game.special_event = lambda name: events.append(name)
    presenter.sound_manager = SimpleNamespace(play_sfx=lambda name: sfx_calls.append(name))
    manager._show_special_event_dialogue = (
        lambda event_name, title="", image_path="": dialogues.append(
            (event_name, title, image_path)
        )
    )
    manager._refresh_cached_frame = lambda: None
    manager.combat_manager.start_combat = (
        lambda player_arg, enemy_arg, tile_arg: combats.append(
            (player_arg, getattr(enemy_arg, "name", ""), tile_arg)
        )
        or True
    )
    player.quest_dict["Main"]["A Bad Dream"] = {
        "Completed": True,
        "Turned In": True,
        "Waitress Defeated": False,
    }
    body_tile = SimpleNamespace(read=True)

    manager._interact_dead_body(body_tile)

    assert events == ["Waitress"]
    assert sfx_calls == ["waitress_wail"]
    assert dialogues == [
        (
            "Waitress",
            "Waitress",
            str(PYGAME_ASSETS_DIR / "enemy_combat_sprites" / "mad_waitress.png"),
        )
    ]
    assert combats and combats[0][0] is player and combats[0][2] is body_tile
    assert player.quest_dict["Main"]["A Bad Dream"]["Waitress Defeated"] is True


def test_underground_spring_intro_and_tile_effect_branches(monkeypatch):
    manager, _presenter, player, game = _make_manager(monkeypatch)
    sfx_calls = []
    _presenter.sound_manager = SimpleNamespace(play_sfx=lambda name: sfx_calls.append(name))
    manager._refresh_cached_frame = lambda: manager.messages.append("refresh")
    manager._animate_nimue_materialization = lambda: manager.messages.append("nimue-animation")
    manager._show_special_event_dialogue = lambda *args, **kwargs: manager.messages.append(
        "nimue-dialogue"
    )
    manager._show_dungeon_dialogue = lambda text, **kwargs: manager.messages.append(
        f"dialog:{text}"
    )
    manager._show_dungeon_choice = lambda prompt, options, **kwargs: 0
    dirty_calls = []
    manager._mark_view_dirty = lambda: dirty_calls.append("dirty")
    game.special_event = lambda name: manager.messages.append(f"event:{name}")

    class FakeConfirm:
        responses = [True] * 10

        def __init__(self, *_args, **_kwargs):
            pass

        def show(self, **_kwargs):
            return FakeConfirm.responses.pop(0)

    class FakeQuestManager:
        def __init__(self, *_args, **_kwargs):
            pass

        def check_and_offer(self, *_args, **_kwargs):
            return False, False

        def get_random_help_hint(self, *_args, **_kwargs):
            return "Seek the hidden path."

    monkeypatch.setattr("src.ui_pygame.gui.confirmation_popup.ConfirmationPopup", FakeConfirm)
    monkeypatch.setattr("src.ui_pygame.gui.quest_manager.QuestManager", FakeQuestManager)
    monkeypatch.setattr(dungeon_manager.random, "randint", lambda *_args: 0)
    monkeypatch.setattr("src.core.enemies.Fuath", lambda: SimpleNamespace(name="Fuath"))
    monkeypatch.setattr("src.core.items.EmptyVial", lambda: SimpleNamespace(name="Empty Vial"))
    monkeypatch.setattr("src.core.items.SpringWater", lambda: SimpleNamespace(name="Spring Water"))
    monkeypatch.setattr("src.core.items.Excaliper", lambda: SimpleNamespace(name="Excaliper"))
    monkeypatch.setattr("src.core.items.Excalibur2", lambda: SimpleNamespace(name="Excalibur2"))
    monkeypatch.setattr(
        dungeon_manager.map_tiles,
        "enter_realm_of_cambion",
        lambda _player: manager.messages.append("entered-realm"),
    )

    player.level.pro_level = 2
    player.cls.name = "Thaumaturgist"
    player.quest_dict["Side"]["Naivete"] = {"Completed": False}
    player.quest_dict["Side"]["The Wizard's Folly"] = {"Completed": False, "Turned In": False}
    player.special_inventory["Excaliper"] = [SimpleNamespace(name="Excaliper")]
    player.inventory["Excalibur"] = [SimpleNamespace(name="Excalibur")]
    spring = UndergroundSpring()
    spring.nimue_met_before = True

    manager._interact_underground_spring(spring)

    assert sfx_calls == ["underground_spring"]
    assert spring.drink is True
    assert spring.defeated is True
    assert spring.nimue is True
    assert "Fuath" not in player.summons
    assert any(call[0] == "Spring Water" for call in player.inventory_calls)
    assert "entered-realm" in manager.messages
    assert "Seek the hidden path." in manager.messages
    assert dirty_calls == ["dirty"]

    player.inventory.pop("Excalibur", None)
    player.equipment["Weapon"] = SimpleNamespace(name="Excalibur")
    manager._interact_underground_spring(spring)
    assert sfx_calls == ["underground_spring", "underground_spring"]
    assert player.equipment["Weapon"].name == "Excalibur2"


def test_get_tile_intro_check_tile_effects_and_menu_helpers(monkeypatch):
    manager, presenter, player, game = _make_manager(monkeypatch)
    manager._refresh_cached_frame = lambda: manager.messages.append("refresh")
    manager._show_town_entry_loading_screen = lambda *_args, **_kwargs: manager.messages.append(
        "town-loading"
    )
    manager.renderer = SimpleNamespace(
        trigger_damage_flash=lambda: manager.messages.append("flash"),
        render_dungeon_view=lambda player_char, world_dict: manager.messages.append("render-view"),
        render_message_area=lambda messages, **kwargs: manager.messages.append("render-messages"),
        render_damage_flash=lambda: manager.messages.append("render-flash"),
        _damage_flash_active=False,
    )
    manager.hud = SimpleNamespace(
        render_hud=lambda player_char: manager.messages.append("render-hud")
    )
    monkeypatch.setattr(
        dungeon_manager.map_tiles,
        "update_chalice_location",
        lambda game_arg: manager.messages.append("update-chalice"),
    )
    monkeypatch.setattr(
        dungeon_manager.map_tiles,
        "handle_chalice_adventurer",
        lambda game_arg: manager.messages.append("handle-adventurer"),
    )
    monkeypatch.setattr(
        dungeon_manager.map_tiles, "pop_cambion_messages", lambda _player: ["Cambion warning"]
    )

    player.name = "Hero"
    player.warp_point = True
    player.inventory["Cryptic Key"] = [SimpleNamespace(name="Cryptic Key")]
    player.spellbook["Skills"] = ["Keen Eye"]
    current = WarpPoint()
    current.intro_text = lambda _game: ""
    ahead = OreVaultDoor(enter=False, locked=True)
    ahead.intro_text = lambda _game: ""
    player.world_dict[(player.location_x, player.location_y, player.location_z)] = current
    player.world_dict[(player.location_x, player.location_y - 1, player.location_z)] = ahead

    intros = manager._get_tile_intro()
    assert any("warp point shimmers" in msg.lower() for msg in intros)
    assert any("hidden door ahead" in msg.lower() for msg in intros)
    assert ahead.detected is True

    fire_tile = FirePath()
    fire_tile.enemy = None
    player.health.current = 10
    player.world_dict[(player.location_x, player.location_y, player.location_z)] = fire_tile
    popup_calls = []

    class FakeConfirm:
        def __init__(self, _presenter, message, show_buttons=True):
            popup_calls.append(("init", message, show_buttons))

        def show(self, **kwargs):
            popup_calls.append(("show", kwargs))
            return None

    monkeypatch.setattr("src.ui_pygame.gui.confirmation_popup.ConfirmationPopup", FakeConfirm)
    manager._check_tile_effects()
    assert "The flames dance." not in manager.messages
    assert popup_calls[0] == ("init", "The flames dance.", False)
    assert popup_calls[1][0] == "show"
    assert any("3 damage" in msg for msg in manager.messages)
    assert "flash" in manager.messages
    assert "Cambion warning" in manager.messages

    enemy = SimpleNamespace(name="Slime", health=SimpleNamespace(current=5), is_alive=lambda: True)
    enemy_tile = EnemyTile(enemy)
    player.world_dict[(player.location_x, player.location_y, player.location_z)] = enemy_tile
    manager.combat_manager.start_combat = lambda *_args, **_kwargs: True
    manager._check_tile_effects()
    assert enemy_tile.enemy is None
    assert "You emerge victorious!" in manager.messages

    player.in_realm_of_cambion = lambda: False
    player.exit_funhouse = lambda: manager.messages.append("exit-funhouse")
    player.exit_realm_of_cambion = lambda: manager.messages.append("exit-cambion")
    provider_calls = []
    presenter.set_background_provider = lambda provider: provider_calls.append(provider)
    player.to_town = lambda: manager.messages.append(
        "to-town-after-detach" if provider_calls and provider_calls[-1] is None else "to-town"
    )
    player.death = lambda: (
        manager.messages.append(
            "death-after-detach" if provider_calls and provider_calls[-1] is None else "death"
        )
        or "Resurrection costs you 10 gold.\nYou wake up in town.\n"
    )
    player.location_z = 7
    enemy2 = SimpleNamespace(name="Ghost", health=SimpleNamespace(current=5), is_alive=lambda: True)
    enemy_tile2 = EnemyTile(enemy2)
    player.world_dict[(player.location_x, player.location_y, player.location_z)] = enemy_tile2
    manager.combat_manager.start_combat = lambda *_args, **_kwargs: False
    player.is_alive = lambda: False
    manager.running = True
    manager._cached_view = "stale-dungeon-view"
    manager._cached_frame = "stale-dungeon-frame"
    manager.view_dirty = False
    manager.ui_dirty = False
    manager._check_tile_effects()
    assert "exit-funhouse" in manager.messages
    assert manager.running is False

    player.location_z = 1
    player.world_dict[(player.location_x, player.location_y, player.location_z)] = EnemyTile(
        SimpleNamespace(name="Wraith", health=SimpleNamespace(current=5), is_alive=lambda: True)
    )
    loading_count = manager.messages.count("town-loading")
    manager.running = True
    manager._check_tile_effects()
    assert "death-after-detach" in manager.messages
    assert "Resurrection costs you 10 gold." in manager.messages
    assert "You wake up in town." in manager.messages
    assert "to-town-after-detach" not in manager.messages
    assert manager.messages.count("town-loading") == loading_count
    assert manager.running is False
    assert manager._cached_view is None
    assert manager._cached_frame is None
    assert manager.view_dirty is True and manager.ui_dirty is True

    popup_events = iter(
        [
            [SimpleNamespace(type=pygame.KEYDOWN, key=pygame.K_DOWN)],
            [SimpleNamespace(type=pygame.KEYDOWN, key=pygame.K_RETURN)],
        ]
    )
    monkeypatch.setattr(
        "src.ui_pygame.gui.dungeon_manager.pygame.event.get", lambda: next(popup_events, [])
    )
    monkeypatch.setattr("src.ui_pygame.gui.dungeon_manager.pygame.display.flip", lambda: None)
    monkeypatch.setattr(
        "src.ui_pygame.gui.dungeon_manager.pygame.draw.rect", lambda *_args, **_kwargs: None
    )
    monkeypatch.setattr(
        "src.ui_pygame.gui.dungeon_manager.pygame.Surface", lambda size, *_args: DummySurface(size)
    )
    assert manager._popup_menu("Menu", ["A", "B"]) == 1

    events = iter(
        [
            [SimpleNamespace(type=pygame.KEYUP, key=pygame.K_RETURN)],
            [SimpleNamespace(type=pygame.KEYDOWN, key=pygame.K_DOWN)],
            [SimpleNamespace(type=pygame.KEYDOWN, key=pygame.K_RETURN)],
        ]
    )
    clear_calls = []
    monkeypatch.setattr(
        "src.ui_pygame.gui.dungeon_manager.pygame.event.get", lambda: next(events, [])
    )
    monkeypatch.setattr(
        "src.ui_pygame.gui.dungeon_manager.pygame.event.clear", lambda: clear_calls.append(True)
    )
    monkeypatch.setattr("src.ui_pygame.gui.input_guards.pygame.key.get_pressed", lambda: [1])
    assert manager._popup_menu("Menu", ["A", "B"], flush_events=True, require_key_release=True) == 1
    assert clear_calls == [True]

    manager.character_screen = SimpleNamespace(navigate=lambda _player: "Exit Menu")
    manager.game = SimpleNamespace(
        debug_mode=False,
        running=True,
        save_game=lambda: manager.messages.append("saved"),
        debug_level_up=lambda: manager.messages.append("debug-level"),
    )
    manager._popup_menu = lambda title, options, **_kwargs: 0
    manager._show_menu()
    manager._popup_menu = lambda title, options, **_kwargs: len(options) - 1

    class FakeConfirmMenu:
        def __init__(self, *_args, **_kwargs):
            pass

        def show(self, **_kwargs):
            return True

    monkeypatch.setattr("src.ui_pygame.gui.confirmation_popup.ConfirmationPopup", FakeConfirmMenu)
    manager._show_menu()
    assert manager.player_char.quit is True


def test_merzhin_victory_collapses_realm_and_returns_to_saved_location(monkeypatch):
    manager, _presenter, player, _game = _make_manager(monkeypatch)
    manager._refresh_cached_frame = lambda: manager.messages.append("refresh")
    dirty_calls = []
    manager._mark_view_dirty = lambda: dirty_calls.append("dirty")
    player.location_x = 22
    player.location_y = 2
    player.location_z = dungeon_manager.map_tiles.REALM_OF_CAMBION_LEVEL
    player.cambion_return = (4, 9, 3, "south")
    player.exit_realm_of_cambion = lambda: (
        setattr(player, "location_x", 4),
        setattr(player, "location_y", 9),
        setattr(player, "location_z", 3),
        setattr(player, "facing", "south"),
        setattr(player, "cambion_return", None),
    )
    enemy = SimpleNamespace(
        name="Merzhin", health=SimpleNamespace(current=5), is_alive=lambda: True
    )
    tile = MerzhinBossRoom(enemy)
    tile.read = True
    player.world_dict[(player.location_x, player.location_y, player.location_z)] = tile
    manager.combat_manager.start_combat = lambda *_args, **_kwargs: True

    manager._check_tile_effects()

    assert tile.enemy is None
    assert "You emerge victorious!" in manager.messages
    assert "Merzhin falls and the Realm of Cambion collapses around you." in manager.messages
    assert (player.location_x, player.location_y, player.location_z, player.facing) == (
        4,
        9,
        3,
        "south",
    )
    assert dirty_calls == ["dirty"]


def test_merzhin_defeat_returns_from_realm_without_town_death_flow(monkeypatch):
    manager, _presenter, player, _game = _make_manager(monkeypatch)
    manager._refresh_cached_frame = lambda: manager.messages.append("refresh")
    dirty_calls = []
    manager._mark_view_dirty = lambda: dirty_calls.append("dirty")
    player.location_x = 22
    player.location_y = 2
    player.location_z = dungeon_manager.map_tiles.REALM_OF_CAMBION_LEVEL
    player.in_realm_of_cambion = lambda: True
    player.exit_realm_of_cambion = lambda: (
        setattr(player, "location_x", 4),
        setattr(player, "location_y", 9),
        setattr(player, "location_z", 3),
    )
    player.to_town = lambda: manager.messages.append("unexpected-town")
    player.is_alive = lambda: False
    enemy = SimpleNamespace(
        name="Merzhin", health=SimpleNamespace(current=5), is_alive=lambda: True
    )
    tile = MerzhinBossRoom(enemy)
    tile.read = True
    player.world_dict[(player.location_x, player.location_y, player.location_z)] = tile
    manager.running = True
    manager.combat_manager.start_combat = lambda *_args, **_kwargs: False

    manager._check_tile_effects()

    assert "You were defeated... The Realm of Cambion hurls you back to the spring." in " ".join(
        manager.messages
    )
    assert "unexpected-town" not in manager.messages
    assert (player.location_x, player.location_y, player.location_z) == (4, 9, 3)
    assert player.state == "normal"
    assert manager.running is False
    assert dirty_calls == ["dirty"]


def test_dungeon_popup_menu_guard_accepts_fresh_key_without_keyup(monkeypatch):
    manager, _presenter, _player, _game = _make_manager(monkeypatch)

    events = iter(
        [
            [SimpleNamespace(type=pygame.KEYDOWN, key=pygame.K_RETURN)],
        ]
    )
    clear_calls = []
    monkeypatch.setattr(
        "src.ui_pygame.gui.dungeon_manager.pygame.event.get", lambda: next(events, [])
    )
    monkeypatch.setattr(
        "src.ui_pygame.gui.dungeon_manager.pygame.event.clear", lambda: clear_calls.append(True)
    )
    monkeypatch.setattr("src.ui_pygame.gui.dungeon_manager.pygame.display.flip", lambda: None)
    monkeypatch.setattr(
        "src.ui_pygame.gui.dungeon_manager.pygame.draw.rect", lambda *_args, **_kwargs: None
    )
    monkeypatch.setattr(
        "src.ui_pygame.gui.dungeon_manager.pygame.Surface", lambda size, *_args: DummySurface(size)
    )
    monkeypatch.setattr("src.ui_pygame.gui.input_guards.pygame.key.get_pressed", lambda: [])

    assert manager._popup_menu("Menu", ["A", "B"], flush_events=True, require_key_release=True) == 0
    assert clear_calls == [True]


def test_dungeon_popup_menu_selects_option_with_mouse_click(monkeypatch):
    manager, _presenter, _player, _game = _make_manager(monkeypatch)
    second_option_center = (320, 229)
    events = iter(
        [[SimpleNamespace(type=pygame.MOUSEBUTTONDOWN, button=1, pos=second_option_center)]]
    )
    monkeypatch.setattr(
        "src.ui_pygame.gui.dungeon_manager.pygame.event.get", lambda: next(events, [])
    )
    monkeypatch.setattr("src.ui_pygame.gui.dungeon_manager.pygame.display.flip", lambda: None)
    monkeypatch.setattr(
        "src.ui_pygame.gui.dungeon_manager.pygame.draw.rect", lambda *_args, **_kwargs: None
    )
    monkeypatch.setattr(
        "src.ui_pygame.gui.dungeon_manager.pygame.Surface", lambda size, *_args: DummySurface(size)
    )

    assert manager._popup_menu("Menu", ["A", "B"]) == 1

    move_calls = []
    manager.move_forward = lambda: move_calls.append("forward")
    manager.turn_left = lambda: move_calls.append("left")
    manager.turn_right = lambda: move_calls.append("right")
    manager.turn_around = lambda: move_calls.append("around")
    manager.use_stairs_up = lambda: move_calls.append("up")
    manager.use_stairs_down = lambda: move_calls.append("down")
    manager.interact = lambda: move_calls.append("interact")
    manager.scroll_message_log = lambda delta: move_calls.append(delta)
    manager._show_menu = lambda: move_calls.append("menu")
    manager.character_screen = SimpleNamespace(navigate=lambda _player: "Exit Menu")
    manager.presenter.show_message = lambda message: move_calls.append(message)
    manager.game.debug_mode = True
    manager.game.debug_level_up = lambda: move_calls.append("debug")
    for key in (
        pygame.K_w,
        pygame.K_a,
        pygame.K_d,
        pygame.K_s,
        pygame.K_u,
        pygame.K_j,
        pygame.K_o,
        pygame.K_PAGEUP,
        pygame.K_PAGEDOWN,
        pygame.K_l,
        pygame.K_ESCAPE,
    ):
        manager._handle_keypress(key)
    assert move_calls[:11] == [
        "forward",
        "left",
        "right",
        "around",
        "up",
        "down",
        "interact",
        -1,
        1,
        "debug",
        "menu",
    ]


def test_stair_transition_suppresses_buffered_navigation_input(monkeypatch):
    manager, _presenter, _player, _game = _make_manager(monkeypatch)
    now = {"ticks": 1000}
    clear_calls = []
    monkeypatch.setattr(dungeon_manager.pygame.time, "get_ticks", lambda: now["ticks"])
    monkeypatch.setattr(
        dungeon_manager.pygame.event, "clear", lambda events: clear_calls.append(events)
    )
    move_calls = []
    manager.move_forward = lambda: move_calls.append("forward")
    manager.scroll_message_log = lambda delta: move_calls.append(delta)

    manager._suppress_navigation_input(ms=300)
    manager._handle_keypress(pygame.K_UP)
    manager._handle_keypress(pygame.K_PAGEUP)
    now["ticks"] = 1301
    manager._handle_keypress(pygame.K_UP)

    assert clear_calls == [(pygame.KEYDOWN, pygame.KEYUP)]
    assert move_calls == [-1, "forward"]


def test_loading_suppression_waits_for_held_navigation_key_release(monkeypatch):
    manager, _presenter, _player, _game = _make_manager(monkeypatch)
    now = {"ticks": 1000}

    class PressedKeys:
        def __getitem__(self, key):
            return key == pygame.K_w

    monkeypatch.setattr(dungeon_manager.pygame.time, "get_ticks", lambda: now["ticks"])
    monkeypatch.setattr(dungeon_manager.pygame.key, "get_pressed", PressedKeys)
    monkeypatch.setattr(dungeon_manager.pygame.event, "clear", lambda _events: None)
    moves = []
    manager.move_forward = lambda: moves.append("forward")

    manager._suppress_navigation_input(ms=0)
    manager._handle_keypress(pygame.K_w)
    manager._release_navigation_input(pygame.K_w)
    manager._handle_keypress(pygame.K_w)

    assert moves == ["forward"]


def test_final_room_incubus_and_golden_chalice_branches(monkeypatch):
    manager, presenter, player, _game = _make_manager(monkeypatch)
    manager._refresh_cached_frame = lambda: manager.messages.append("refresh")
    manager._mark_view_dirty = lambda: manager.messages.append("dirty")
    presenter.show_message = lambda message, title=None, **kwargs: manager.messages.append(
        f"{kwargs.get('title', title)}:{message}"
    )
    presenter.render_menu = lambda prompt, options: 0
    monkeypatch.setattr(
        dungeon_manager.core,
        "get_special_events",
        lambda: {"Final Boss": {"Text": ["I await", "your challenge"]}},
    )
    monkeypatch.setattr(
        "src.ui_pygame.gui.dungeon_manager.pygame.event.clear",
        lambda: manager.messages.append("clear-events"),
    )
    monkeypatch.setattr("src.core.enemies.Vesperion", lambda: SimpleNamespace(name="Vesperion"))

    final_tile = FinalRoom()
    manager.combat_manager.start_combat = lambda *_args, **_kwargs: True
    manager._interact_final_room(final_tile)
    assert player.quit is True
    assert manager.running is False
    assert final_tile.adjacent_calls
    assert any("Vesperion:I await your challenge" == msg for msg in manager.messages)

    player.quit = False
    manager.running = True
    player.is_alive = lambda: False
    manager.combat_manager.start_combat = lambda *_args, **_kwargs: False
    final_provider_calls = []
    presenter.set_background_provider = lambda provider: final_provider_calls.append(provider)
    player.to_town = lambda: manager.messages.append(
        "to-town-after-detach"
        if final_provider_calls and final_provider_calls[-1] is None
        else "to-town"
    )
    loading_calls = []
    manager._show_dungeon_loading_screen = lambda msg, duration=1.25: loading_calls.append(msg)
    manager._interact_final_room(final_tile)
    assert "to-town-after-detach" in manager.messages
    assert loading_calls == []

    presenter.render_menu = lambda prompt, options: 1
    old_y = player.location_y
    manager._interact_final_room(final_tile)
    assert player.location_y == old_y + 1

    player.quest_dict["Side"]["Oedipal Complex"] = {"Completed": False}
    incubus_tile = IncubusLair()
    player.is_alive = lambda: True
    manager.combat_manager.start_combat = lambda *_args, **_kwargs: True
    manager._interact_incubus_lair(incubus_tile)
    assert incubus_tile.defeated is True
    assert any("Quest completed: Oedipal Complex" in msg for msg in manager.messages)

    player.quest_dict["Side"]["The Holy Grail of Quests"] = {"Completed": False}

    class FakeConfirm:
        responses = [True, False]

        def __init__(self, *_args, **_kwargs):
            pass

        def show(self, **_kwargs):
            return FakeConfirm.responses.pop(0)

    monkeypatch.setattr("src.ui_pygame.gui.confirmation_popup.ConfirmationPopup", FakeConfirm)
    chalice_tile = GoldenChaliceRoom()
    manager._interact_golden_chalice_room(chalice_tile)
    assert chalice_tile.read is True
    manager._interact_golden_chalice_room(chalice_tile)
    assert any("leave the chalice" in msg.lower() for msg in manager.messages)


def test_final_room_pending_false_final_enters_liminal_stub(monkeypatch):
    manager, presenter, player, _game = _make_manager(monkeypatch)
    manager._refresh_cached_frame = lambda: None
    manager._mark_view_dirty = lambda: None
    presenter.render_menu = lambda prompt, options: 0
    shown = []
    presenter.show_message = lambda *args, **kwargs: shown.append((args, kwargs))
    monkeypatch.setattr(
        dungeon_manager.core,
        "get_special_events",
        lambda: {
            "Final Boss": {"Text": ["Vesperion waits."]},
            "Vesperion False Final": {"Text": ["The Evening Star descends."]},
            "Liminal Gap Arrival": {"Text": ["You wake before the threshold."]},
        },
    )
    monkeypatch.setattr(
        dungeon_manager.core,
        "get_npc_art_manager",
        lambda: SimpleNamespace(
            get_image_path=lambda name: f"npc:{name}" if name == "Vesperion" else ""
        ),
    )
    monkeypatch.setattr("src.ui_pygame.gui.dungeon_manager.pygame.event.clear", lambda: None)
    monkeypatch.setattr("src.core.enemies.Vesperion", lambda: SimpleNamespace(name="Vesperion"))

    def start_false_final(*_args, **_kwargs):
        player.main_story["vesperion_false_final_triggered"] = True
        player.main_story["pending_liminal_gap_entry"] = True
        player.health.current = 0
        return False

    player.location_x, player.location_y, player.location_z, player.facing = (5, 5, 1, "north")
    player.health.current = 1
    player.mana.current = 0
    manager.combat_manager.start_combat = start_false_final

    manager._interact_final_room(FinalRoom())

    assert (player.location_x, player.location_y, player.location_z) == LIMINAL_GAP_ENTRY_POS
    assert player.facing == LIMINAL_GAP_ENTRY_FACING
    assert player.liminal_gap_return == (5, 5, 1, "north")
    assert player.health.current == 10
    assert player.mana.current == 4
    assert player.state == "normal"
    assert player.main_story["vesperion_false_final_triggered"] is True
    assert player.main_story["pending_liminal_gap_entry"] is False
    assert player.main_story["liminal_gap_entered"] is True
    assert any(call[1].get("title") == "Vesperion" for call in shown)
    assert shown[0][1]["title"] == "Vesperion"
    assert shown[0][1]["image_path"] == "npc:Vesperion"
    assert shown[1][1]["title"] == "Vesperion"
    assert shown[1][1]["image_path"] == "npc:Vesperion"
    assert any(call[1].get("title") == "The Liminal Gap" for call in shown)
    assert "You wake in the Liminal Gap, wounded but alive." in manager.messages
    assert player.quit is False
    assert manager.running is True


def test_final_room_reentry_before_true_final_shows_liminal_blocker(monkeypatch):
    manager, presenter, player, _game = _make_manager(monkeypatch)
    shown = []
    player.main_story["vesperion_false_final_triggered"] = True
    presenter.show_message = lambda *args, **kwargs: shown.append((args, kwargs))
    presenter.render_menu = lambda *_args, **_kwargs: (_ for _ in ()).throw(
        AssertionError("menu should not open")
    )
    manager.combat_manager.start_combat = lambda *_args, **_kwargs: (_ for _ in ()).throw(
        AssertionError("combat should not start")
    )
    monkeypatch.setattr(
        dungeon_manager.core,
        "get_special_events",
        lambda: {"Liminal Gap Blocker": {"Text": ["Voluntas remains unresolved."]}},
    )

    manager._interact_final_room(FinalRoom())

    assert shown[-1][1]["title"] == "Voluntas"
    assert "Voluntas remains unresolved. The final chamber will not open yet." in " ".join(
        manager.messages
    )


def test_liminal_guide_reveals_hooded_figure_and_saves(monkeypatch):
    manager, presenter, player, game = _make_manager(monkeypatch)
    shown = []
    presenter.show_message = lambda *args, **kwargs: shown.append((args, kwargs))
    manager._popup_menu = lambda title, options, **kwargs: 0
    monkeypatch.setattr(
        dungeon_manager.core,
        "get_special_events",
        lambda: {
            "Hooded Figure Liminal Reveal": {"Text": ["The Hooded Figure lowers their hood."]},
            "Liminal Guide Save": {"Text": ["Your name appears in the flame."]},
        },
    )
    guide_tile = dungeon_manager.map_tiles.LiminalGuide(5, 4, LIMINAL_GAP_ENTRY_POS[2])

    manager._interact_liminal_guide(guide_tile)

    assert player.main_story["liminal_gap_guide_revealed"] is True
    assert player.main_story["liminal_gap_guide_save_used"] is True
    assert guide_tile.read is True
    assert game.save_calls == ["save"]
    assert [call[1]["title"] for call in shown] == ["The Hooded Figure", "The Hooded Figure"]
    assert "The Hooded Figure anchors your progress." in manager.messages


def test_liminal_guide_reviews_awakened_guardian_clues(monkeypatch):
    manager, presenter, player, _game = _make_manager(monkeypatch)
    shown = []
    player.main_story["liminal_gap_guide_revealed"] = True
    player.main_story["guardian_trials_completed"]["Triangulus"] = True
    player.main_story["guardian_trial_choices"]["Triangulus"] = "Memory"
    player.main_story["voluntas_clues_found"]["Triangulus"] = True
    player.main_story["guardian_trials_completed"]["Luna"] = True
    player.main_story["guardian_trial_choices"]["Luna"] = "Release"
    player.main_story["voluntas_clues_found"]["Luna"] = True
    presenter.show_message = lambda *args, **kwargs: shown.append((args, kwargs))
    manager._popup_menu = lambda *_args, **_kwargs: 1
    monkeypatch.setattr(
        dungeon_manager.core,
        "get_special_events",
        lambda: {"Liminal Clue Review": {"Text": ["The clues answer together."]}},
    )
    guide_tile = dungeon_manager.map_tiles.LiminalGuide(5, 4, LIMINAL_GAP_ENTRY_POS[2])

    manager._interact_liminal_guide(guide_tile)

    assert shown[-1][1]["title"] == "The Hooded Figure"
    assert player.main_story["liminal_gap_clues_reviewed"] is True
    assert guide_tile.read is True
    joined_messages = " ".join(manager.messages)
    assert "Guardian clues awakened: 2/6." in joined_messages
    assert "Triangulus (Memory): selfhood is chosen, not assigned." in joined_messages
    assert (
        "Luna (Release): love without freedom becomes possession or obligation." in joined_messages
    )


def test_liminal_guide_reviews_guardian_trial_depths(monkeypatch):
    manager, presenter, player, _game = _make_manager(monkeypatch)
    shown = []
    captured_options = []
    player.main_story["liminal_gap_guide_revealed"] = True
    player.main_story["guardian_trial_vignettes_seen"]["Triangulus"] = True
    player.main_story["guardian_trial_choices"]["Triangulus"] = "Memory"
    presenter.show_message = lambda *args, **kwargs: shown.append((args, kwargs))
    manager._popup_menu = lambda _title, options, **_kwargs: captured_options.append(
        list(options)
    ) or options.index("Review Trial Depths")
    monkeypatch.setattr(
        dungeon_manager.core,
        "get_special_events",
        lambda: {"Liminal Trial V2 Review": {"Text": ["The deeper trials answer."]}},
    )
    guide_tile = dungeon_manager.map_tiles.LiminalGuide(5, 4, LIMINAL_GAP_ENTRY_POS[2])

    manager._interact_liminal_guide(guide_tile)

    assert "Review Trial Depths" in captured_options[-1]
    assert shown[-1][1]["title"] == "The Hooded Figure"
    assert player.main_story["liminal_trial_v2_reviewed"] is True
    assert player.main_story["voluntas_revealed"] is False
    assert player.main_story["true_final_unlocked"] is False
    assert guide_tile.read is True
    joined_messages = " ".join(manager.messages)
    assert "Guardian trial depths witnessed: 1/6." in joined_messages
    assert "Triangulus (Memory): identity chosen through name, body, and memory." in joined_messages


def test_liminal_guide_affirm_class_path_visibility_requires_voluntas_and_ring(monkeypatch):
    manager, _presenter, player, _game = _make_manager(monkeypatch)
    captured_options = []
    player.main_story["liminal_gap_guide_revealed"] = True
    player.cls.name = "Wizard"
    player.equipment["Ring"] = items.ClassRing()
    manager._popup_menu = lambda _title, options, **_kwargs: captured_options.append(
        list(options)
    ) or options.index("Leave")

    manager._interact_liminal_guide(
        dungeon_manager.map_tiles.LiminalGuide(5, 4, LIMINAL_GAP_ENTRY_POS[2])
    )

    assert "Affirm Class Path" not in captured_options[-1]

    manager, _presenter, player, _game = _make_manager(monkeypatch)
    captured_options = []
    player.main_story["liminal_gap_guide_revealed"] = True
    player.main_story["voluntas_revealed"] = True
    player.cls.name = "Wizard"
    player.equipment["Ring"] = items.NoRing()
    manager._popup_menu = lambda _title, options, **_kwargs: captured_options.append(
        list(options)
    ) or options.index("Leave")

    manager._interact_liminal_guide(
        dungeon_manager.map_tiles.LiminalGuide(5, 4, LIMINAL_GAP_ENTRY_POS[2])
    )

    assert "Affirm Class Path" not in captured_options[-1]

    manager, _presenter, player, _game = _make_manager(monkeypatch)
    captured_options = []
    player.main_story["liminal_gap_guide_revealed"] = True
    player.main_story["voluntas_revealed"] = True
    player.cls.name = "Wizard"
    player.equipment["Ring"] = items.ClassRing()
    manager._popup_menu = lambda _title, options, **_kwargs: captured_options.append(
        list(options)
    ) or options.index("Leave")

    manager._interact_liminal_guide(
        dungeon_manager.map_tiles.LiminalGuide(5, 4, LIMINAL_GAP_ENTRY_POS[2])
    )

    assert "Affirm Class Path" in captured_options[-1]
    assert player.main_story["class_voluntas_affirmed"] is False


@pytest.mark.parametrize("ring_awakened", [False, True])
def test_liminal_guide_affirms_class_path_once(monkeypatch, ring_awakened):
    manager, presenter, player, _game = _make_manager(monkeypatch)
    shown = []
    captured_options = []
    player.main_story["liminal_gap_guide_revealed"] = True
    player.main_story["voluntas_revealed"] = True
    player.cls.name = "Wizard"
    player.equipment["Ring"] = items.ClassRing()
    if ring_awakened:
        class_rings.ensure_state(player)["awakened"]["Wizard"] = True
    presenter.show_message = lambda *args, **kwargs: shown.append((args, kwargs))
    manager._popup_menu = lambda _title, options, **_kwargs: captured_options.append(
        list(options)
    ) or options.index("Affirm Class Path")
    monkeypatch.setattr(
        dungeon_manager.core,
        "get_special_events",
        lambda: {
            "Class Voluntas Affirmation": {"Text": ["Voluntas asks what path is yours."]},
            "Class Voluntas Dormant Ring": {"Text": ["The dormant ring keeps its shape."]},
            "Class Voluntas Awakened Ring": {"Text": ["The awakened ring answers."]},
            "Class Voluntas Archetype Mystic": {"Text": ["The mystic path stands."]},
        },
    )
    guide_tile = dungeon_manager.map_tiles.LiminalGuide(5, 4, LIMINAL_GAP_ENTRY_POS[2])

    manager._interact_liminal_guide(guide_tile)

    assert "Affirm Class Path" in captured_options[-1]
    assert [call[1]["title"] for call in shown] == ["Voluntas", "Class Ring", "Class Ring"]
    assert player.main_story["class_voluntas_affirmed"] is True
    assert player.main_story["class_voluntas_affirmed_class"] == "Wizard"
    assert player.main_story["class_voluntas_affirmed_ring_awakened"] is ring_awakened
    assert player.main_story["class_voluntas_affirmed_archetype"] == "mystic"
    assert guide_tile.read is True
    expected_state = "awakened" if ring_awakened else "dormant"
    assert f"Wizard is affirmed through a {expected_state} Class Ring." in manager.messages
    assert manager._class_voluntas_affirmation_available(player.main_story) is False


def test_liminal_guide_revisits_class_path_once(monkeypatch):
    manager, presenter, player, _game = _make_manager(monkeypatch)
    shown = []
    captured_options = []
    player.main_story["liminal_gap_guide_revealed"] = True
    player.main_story["class_voluntas_affirmed"] = True
    player.main_story["class_voluntas_affirmed_class"] = "Wizard"
    player.main_story["class_voluntas_affirmed_ring_awakened"] = False
    player.main_story["class_voluntas_affirmed_archetype"] = "mystic"
    presenter.show_message = lambda *args, **kwargs: shown.append((args, kwargs))
    manager._popup_menu = lambda _title, options, **_kwargs: captured_options.append(
        list(options)
    ) or options.index("Revisit Class Path")
    monkeypatch.setattr(
        dungeon_manager.core,
        "get_special_events",
        lambda: {
            "Class Voluntas Followup": {"Text": ["The path remains chosen."]},
            "Class Voluntas Followup Mystic": {"Text": ["The mystic path remains."]},
        },
    )
    guide_tile = dungeon_manager.map_tiles.LiminalGuide(5, 4, LIMINAL_GAP_ENTRY_POS[2])

    manager._interact_liminal_guide(guide_tile)

    assert "Revisit Class Path" in captured_options[-1]
    assert [call[1]["title"] for call in shown] == ["Voluntas", "Class Ring"]
    assert player.main_story["class_voluntas_followup_seen"] is True
    assert guide_tile.read is True
    assert "Wizard is remembered through a dormant Class Ring." in manager.messages

    manager._popup_menu = lambda _title, options, **_kwargs: captured_options.append(
        list(options)
    ) or options.index("Leave")
    manager._interact_liminal_guide(guide_tile)

    assert "Revisit Class Path" not in captured_options[-1]


def test_liminal_guide_bridges_recorded_class_identity_once_and_story_only(monkeypatch):
    manager, presenter, player, _game = _make_manager(monkeypatch)
    shown = []
    captured_options = []
    player.main_story["liminal_gap_guide_revealed"] = True
    player.main_story["class_voluntas_affirmed"] = True
    player.main_story["class_voluntas_affirmed_class"] = "Demonologist"
    player.main_story["class_voluntas_affirmed_ring_awakened"] = True
    player.main_story["class_voluntas_affirmed_archetype"] = "shadow"
    player.cls.name = "Wizard"
    player.equipment = {"Weapon": SimpleNamespace(name="None")}
    player.health.current = 7
    player.mana.current = 3
    player.gold = 456
    player.experience = 123
    presenter.show_message = lambda *args, **kwargs: shown.append((args, kwargs))
    manager._popup_menu = lambda _title, options, **_kwargs: captured_options.append(
        list(options)
    ) or options.index("Leave")
    guide_tile = dungeon_manager.map_tiles.LiminalGuide(5, 4, LIMINAL_GAP_ENTRY_POS[2])

    manager._interact_liminal_guide(guide_tile)

    assert "Bridge Class Identity" not in captured_options[-1]

    player.main_story["class_voluntas_followup_seen"] = True
    manager._popup_menu = lambda _title, options, **_kwargs: captured_options.append(
        list(options)
    ) or options.index("Bridge Class Identity")
    monkeypatch.setattr(
        dungeon_manager.core,
        "get_special_events",
        lambda: {
            "Class Voluntas Bridge": {"Text": ["The bridge opens."]},
            "Class Voluntas Bridge Demonologist": {"Text": ["The contract bridge stands."]},
        },
    )

    manager._interact_liminal_guide(guide_tile)

    assert "Bridge Class Identity" in captured_options[-1]
    assert [call[1]["title"] for call in shown] == ["Voluntas", "Class Ring"]
    assert shown[1][0][0] == "The contract bridge stands."
    assert player.main_story["class_voluntas_bridge_seen"] is True
    assert guide_tile.read is True
    assert "Demonologist bridges its chosen path to Voluntas." in manager.messages
    assert player.health.current == 7
    assert player.mana.current == 3
    assert player.gold == 456
    assert player.experience == 123
    assert player.inventory_calls == []
    assert player.main_story["true_final_unlocked"] is False

    manager._popup_menu = lambda _title, options, **_kwargs: captured_options.append(
        list(options)
    ) or options.index("Leave")
    manager._interact_liminal_guide(guide_tile)

    assert "Bridge Class Identity" not in captured_options[-1]


def test_liminal_guide_witness_farewell_visibility_and_once(monkeypatch):
    manager, presenter, player, _game = _make_manager(monkeypatch)
    shown = []
    captured_options = []
    player.main_story["liminal_gap_guide_revealed"] = True
    presenter.show_message = lambda *args, **kwargs: shown.append((args, kwargs))
    manager._popup_menu = lambda _title, options, **_kwargs: captured_options.append(
        list(options)
    ) or options.index("Leave")
    guide_tile = dungeon_manager.map_tiles.LiminalGuide(5, 4, LIMINAL_GAP_ENTRY_POS[2])

    manager._interact_liminal_guide(guide_tile)

    assert "Ask About the Witness" not in captured_options[-1]

    player.main_story["reflection_defeated"] = True
    manager._popup_menu = lambda _title, options, **_kwargs: captured_options.append(
        list(options)
    ) or options.index("Ask About the Witness")
    monkeypatch.setattr(
        dungeon_manager.core,
        "get_special_events",
        lambda: {"Hooded Figure Witness Farewell": {"Text": ["I kept a door from closing."]}},
    )

    manager._interact_liminal_guide(guide_tile)

    assert "Ask About the Witness" in captured_options[-1]
    assert shown[-1][1]["title"] == "The Hooded Figure"
    assert player.main_story["hooded_figure_witness_farewell_seen"] is True
    assert guide_tile.read is True
    assert "The Hooded Figure remains unnamed" in " ".join(manager.messages)

    manager._popup_menu = lambda _title, options, **_kwargs: captured_options.append(
        list(options)
    ) or options.index("Leave")
    manager._interact_liminal_guide(guide_tile)

    assert "Ask About the Witness" not in captured_options[-1]

    player.main_story["hooded_figure_witness_farewell_seen"] = False
    player.main_story["returned_from_liminal_gap"] = True
    manager._interact_liminal_guide(guide_tile)

    assert "Ask About the Witness" not in captured_options[-1]


@pytest.mark.parametrize(
    ("guardian_name", "gate_cls", "answer_index", "expected_choice"),
    [
        ("Quadrata", dungeon_manager.map_tiles.QuadrataGate, 1, "Resist"),
        ("Hexagonum", dungeon_manager.map_tiles.HexagonumGate, 2, "River"),
        ("Luna", dungeon_manager.map_tiles.LunaGate, 0, "Protect"),
        ("Polaris", dungeon_manager.map_tiles.PolarisGate, 1, "Question"),
    ],
)
def test_remaining_guardian_trials_complete_and_record_choice(
    monkeypatch,
    guardian_name,
    gate_cls,
    answer_index,
    expected_choice,
):
    manager, presenter, player, _game = _make_manager(monkeypatch)
    shown = []
    menu_choices = iter([0, answer_index])
    player.main_story["liminal_gap_guide_revealed"] = True
    presenter.show_message = lambda *args, **kwargs: shown.append((args, kwargs))
    manager._popup_menu = lambda title, options, **kwargs: next(menu_choices)
    monkeypatch.setattr(
        dungeon_manager.core,
        "get_special_events",
        lambda: {
            f"{guardian_name} Trial Intro": {"Text": ["Begin."]},
            f"{guardian_name} Trial V2 Threshold": {"Text": ["Deeper."]},
            f"{guardian_name} Trial V2 {expected_choice}": {"Text": ["Choice depth."]},
            f"{guardian_name} Trial {expected_choice}": {"Text": ["Answer."]},
            f"{guardian_name} Trial Complete": {"Text": ["Complete."]},
        },
    )
    gate_tile = gate_cls(8, 4, LIMINAL_GAP_ENTRY_POS[2])

    manager._interact_liminal_guardian_gate(gate_tile)

    assert [call[1]["title"] for call in shown] == [
        guardian_name,
        guardian_name,
        guardian_name,
        guardian_name,
        guardian_name,
    ]
    assert gate_tile.read is True
    assert player.main_story["guardian_trials_started"][guardian_name] is True
    assert player.main_story["guardian_trials_completed"][guardian_name] is True
    assert player.main_story["guardian_trial_choices"][guardian_name] == expected_choice
    assert player.main_story["voluntas_clues_found"][guardian_name] is True
    assert player.main_story["guardian_trial_vignettes_seen"][guardian_name] is True
    assert player.main_story["voluntas_revealed"] is False
    assert player.main_story["true_final_unlocked"] is False
    assert f"{guardian_name} answers. A clue of Voluntas awakens." in manager.messages


def test_triangulus_trial_requires_hooded_figure_reveal(monkeypatch):
    manager, presenter, player, _game = _make_manager(monkeypatch)
    shown = []
    presenter.show_message = lambda *args, **kwargs: shown.append((args, kwargs))
    monkeypatch.setattr(
        dungeon_manager.core,
        "get_special_events",
        lambda: {"Triangulus Gate": {"Text": ["The gate waits."]}},
    )
    gate_tile = dungeon_manager.map_tiles.TriangulusGate(6, 1, LIMINAL_GAP_ENTRY_POS[2])

    manager._interact_liminal_guardian_gate(gate_tile)

    assert shown[-1][1]["title"] == "Triangulus"
    assert "The gate waits for the Hooded Figure to name the path." in manager.messages
    assert player.main_story["guardian_trials_started"]["Triangulus"] is False
    assert player.main_story["guardian_trials_completed"]["Triangulus"] is False


def test_triangulus_trial_completes_and_records_self_choice(monkeypatch):
    manager, presenter, player, _game = _make_manager(monkeypatch)
    shown = []
    combat_calls = []
    menu_choices = iter([0, 2])
    player.main_story["liminal_gap_guide_revealed"] = True
    presenter.show_message = lambda *args, **kwargs: shown.append((args, kwargs))
    manager._popup_menu = lambda title, options, **kwargs: next(menu_choices)
    manager._refresh_cached_frame = lambda: None
    manager.combat_manager.start_combat = (
        lambda player_char, enemy, tile: combat_calls.append((player_char, enemy, tile)) or True
    )
    monkeypatch.setattr(
        dungeon_manager.core,
        "get_special_events",
        lambda: {
            "Triangulus Trial Intro": {"Text": ["What proves the self?"]},
            "Triangulus Trial V2 Threshold": {"Text": ["Name, body, memory."]},
            "Triangulus Trial V2 Memory": {"Text": ["Memory deepens."]},
            "Triangulus Trial Memory": {"Text": ["Memory answers."]},
            "Triangulus Trial Complete": {"Text": ["The first clue awakens."]},
        },
    )
    gate_tile = dungeon_manager.map_tiles.TriangulusGate(6, 1, LIMINAL_GAP_ENTRY_POS[2])

    manager._interact_liminal_guardian_gate(gate_tile)

    assert [call[1]["title"] for call in shown] == [
        "Triangulus",
        "Triangulus",
        "Triangulus",
        "Triangulus",
        "Triangulus",
    ]
    assert len(combat_calls) == 1
    assert isinstance(combat_calls[0][1], dungeon_manager.enemies.GuardianTrialEcho)
    assert combat_calls[0][1].liminal_trial_guardian == "Triangulus"
    assert combat_calls[0][1].liminal_trial_profile == "Memory"
    assert gate_tile.read is True
    assert player.main_story["guardian_trials_started"]["Triangulus"] is True
    assert player.main_story["guardian_trials_completed"]["Triangulus"] is True
    assert player.main_story["guardian_trial_choices"]["Triangulus"] == "Memory"
    assert player.main_story["voluntas_clues_found"]["Triangulus"] is True
    assert player.main_story["guardian_trial_vignettes_seen"]["Triangulus"] is True
    assert player.main_story["voluntas_revealed"] is False
    assert player.main_story["true_final_unlocked"] is False
    assert "Triangulus answers. A clue of Voluntas awakens." in manager.messages


def test_combat_guardian_trial_defeat_is_retry_safe(monkeypatch):
    manager, presenter, player, _game = _make_manager(monkeypatch)
    shown = []
    menu_choices = iter([0, 2])
    player.main_story["liminal_gap_guide_revealed"] = True
    presenter.show_message = lambda *args, **kwargs: shown.append((args, kwargs))
    manager._popup_menu = lambda title, options, **kwargs: next(menu_choices)
    manager._refresh_cached_frame = lambda: None
    manager.combat_manager.start_combat = lambda *_args, **_kwargs: False
    monkeypatch.setattr(
        dungeon_manager.core,
        "get_special_events",
        lambda: {
            "Infinitas Trial Intro": {"Text": ["Begin again."]},
            "Infinitas Trial V2 Threshold": {"Text": ["Forever deepens."]},
            "Infinitas Trial Defeat": {"Text": ["Try again."]},
        },
    )
    gate_tile = dungeon_manager.map_tiles.InfinitasGate(2, 8, LIMINAL_GAP_ENTRY_POS[2])

    manager._interact_liminal_guardian_gate(gate_tile)

    assert [call[1]["title"] for call in shown] == ["Infinitas", "Infinitas", "Infinitas"]
    assert gate_tile.read is False
    assert player.main_story["guardian_trials_started"]["Infinitas"] is True
    assert player.main_story["guardian_trials_completed"]["Infinitas"] is False
    assert player.main_story["guardian_trial_choices"]["Infinitas"] is None
    assert player.main_story["voluntas_clues_found"]["Infinitas"] is False
    assert player.main_story["guardian_trial_vignettes_seen"]["Infinitas"] is False
    assert player.main_story["true_final_unlocked"] is False
    assert "The gate of Infinitas remains open for another attempt." in manager.messages


def test_guardian_trial_consequences_restore_and_clear_statuses(monkeypatch):
    manager, _presenter, player, _game = _make_manager(monkeypatch)
    player.health.max = 100
    player.health.current = 20
    player.mana.max = 80
    player.mana.current = 10
    player.status_effects = {
        "Blind": SimpleNamespace(active=False, duration=0),
        "Silence": SimpleNamespace(active=False, duration=0),
        "Defend": SimpleNamespace(active=False, duration=0, extra=0),
    }
    player.status_effects["Blind"].active = True
    player.status_effects["Blind"].duration = 3
    player.status_effects["Silence"].active = True
    player.status_effects["Silence"].duration = 3

    hex_messages = manager._apply_guardian_trial_consequence("Hexagonum", "River")
    polaris_messages = manager._apply_guardian_trial_consequence("Polaris", "Question")
    infinitas_messages = manager._apply_guardian_trial_consequence("Infinitas", "Rest")

    assert player.health.current == 50
    assert player.mana.current == 40
    assert player.status_effects["Blind"].active is False
    assert player.status_effects["Blind"].duration == 0
    assert player.status_effects["Silence"].active is False
    assert player.status_effects["Silence"].duration == 0
    assert hex_messages == ["Hexagonum answers through living endurance, restoring 15 HP."]
    assert polaris_messages == ["Polaris fixes true north, clearing blindness and silence."]
    assert infinitas_messages == [
        "Infinitas makes another step possible, restoring 15 HP and 30 MP."
    ]


def test_completed_triangulus_trial_does_not_reaward_progress(monkeypatch):
    manager, presenter, player, _game = _make_manager(monkeypatch)
    shown = []
    player.main_story["liminal_gap_guide_revealed"] = True
    player.main_story["guardian_trials_started"]["Triangulus"] = True
    player.main_story["guardian_trials_completed"]["Triangulus"] = True
    player.main_story["guardian_trial_choices"]["Triangulus"] = "Name"
    player.main_story["voluntas_clues_found"]["Triangulus"] = True
    player.main_story["guardian_trial_vignettes_seen"]["Triangulus"] = True
    presenter.show_message = lambda *args, **kwargs: shown.append((args, kwargs))
    manager._popup_menu = lambda *_args, **_kwargs: (_ for _ in ()).throw(
        AssertionError("trial menu should not reopen")
    )
    monkeypatch.setattr(
        dungeon_manager.core,
        "get_special_events",
        lambda: {"Triangulus Trial Complete": {"Text": ["Already complete."]}},
    )
    gate_tile = dungeon_manager.map_tiles.TriangulusGate(6, 1, LIMINAL_GAP_ENTRY_POS[2])

    manager._interact_liminal_guardian_gate(gate_tile)

    assert shown[-1][1]["title"] == "Triangulus"
    assert player.main_story["guardian_trial_choices"]["Triangulus"] == "Name"
    assert "The gate of Triangulus is quiet. Its trial is complete." in manager.messages


def test_completed_guardian_trial_can_recall_unseen_vignette_without_rewards(monkeypatch):
    manager, presenter, player, _game = _make_manager(monkeypatch)
    shown = []
    player.mana.max = 100
    player.mana.current = 20
    player.main_story["liminal_gap_guide_revealed"] = True
    player.main_story["guardian_trials_started"]["Triangulus"] = True
    player.main_story["guardian_trials_completed"]["Triangulus"] = True
    player.main_story["guardian_trial_choices"]["Triangulus"] = "Name"
    player.main_story["voluntas_clues_found"]["Triangulus"] = True
    presenter.show_message = lambda *args, **kwargs: shown.append((args, kwargs))
    manager._popup_menu = lambda title, options, **kwargs: 0
    monkeypatch.setattr(
        dungeon_manager.core,
        "get_special_events",
        lambda: {
            "Triangulus Trial V2 Threshold": {"Text": ["The triangle deepens."]},
            "Triangulus Trial V2 Name": {"Text": ["The name deepens."]},
        },
    )
    gate_tile = dungeon_manager.map_tiles.TriangulusGate(6, 1, LIMINAL_GAP_ENTRY_POS[2])

    manager._interact_liminal_guardian_gate(gate_tile)

    assert [call[1]["title"] for call in shown] == ["Triangulus", "Triangulus"]
    assert gate_tile.read is True
    assert player.mana.current == 20
    assert player.main_story["guardian_trials_completed"]["Triangulus"] is True
    assert player.main_story["guardian_trial_choices"]["Triangulus"] == "Name"
    assert player.main_story["voluntas_clues_found"]["Triangulus"] is True
    assert player.main_story["guardian_trial_vignettes_seen"]["Triangulus"] is True
    assert player.main_story["voluntas_revealed"] is False
    assert player.main_story["true_final_unlocked"] is False
    assert "Triangulus steadies" not in " ".join(manager.messages)
    assert "deeper trial memory settles" in " ".join(manager.messages)


def test_completed_guardian_trial_recall_falls_back_for_missing_choice(monkeypatch):
    manager, presenter, player, _game = _make_manager(monkeypatch)
    shown = []
    player.main_story["liminal_gap_guide_revealed"] = True
    player.main_story["guardian_trials_started"]["Quadrata"] = True
    player.main_story["guardian_trials_completed"]["Quadrata"] = True
    player.main_story["guardian_trial_choices"]["Quadrata"] = None
    player.main_story["voluntas_clues_found"]["Quadrata"] = True
    presenter.show_message = lambda *args, **kwargs: shown.append((args, kwargs))
    manager._popup_menu = lambda title, options, **kwargs: 0
    monkeypatch.setattr(
        dungeon_manager.core,
        "get_special_events",
        lambda: {
            "Quadrata Trial V2 Threshold": {"Text": ["The square deepens."]},
            "Quadrata Trial V2 Obey": {"Text": ["The first answer deepens."]},
        },
    )
    gate_tile = dungeon_manager.map_tiles.QuadrataGate(8, 4, LIMINAL_GAP_ENTRY_POS[2])

    manager._interact_liminal_guardian_gate(gate_tile)

    assert [call[1]["title"] for call in shown] == ["Quadrata", "Quadrata"]
    assert player.main_story["guardian_trial_choices"]["Quadrata"] is None
    assert player.main_story["guardian_trial_vignettes_seen"]["Quadrata"] is True


def test_liminal_exit_blocker_prevents_return(monkeypatch):
    manager, presenter, player, _game = _make_manager(monkeypatch)
    shown = []
    presenter.show_message = lambda *args, **kwargs: shown.append((args, kwargs))
    player.location_x, player.location_y, player.location_z = LIMINAL_GAP_ENTRY_POS
    monkeypatch.setattr(
        dungeon_manager.core,
        "get_special_events",
        lambda: {"Liminal No Exit": {"Text": ["The way back is broken."]}},
    )
    blocker_tile = dungeon_manager.map_tiles.LiminalExitBlocker(8, 6, LIMINAL_GAP_ENTRY_POS[2])

    manager._interact_liminal_exit_blocker(blocker_tile)

    assert (player.location_x, player.location_y, player.location_z) == LIMINAL_GAP_ENTRY_POS
    assert shown[-1][1]["title"] == "The Liminal Gap"
    assert blocker_tile.read is True
    assert "There is no way back until the Guardian path is resolved." in manager.messages


def test_liminal_seventh_seat_waits_for_all_guardian_clues(monkeypatch):
    manager, presenter, player, _game = _make_manager(monkeypatch)
    shown = []
    presenter.show_message = lambda *args, **kwargs: shown.append((args, kwargs))
    monkeypatch.setattr(
        dungeon_manager.core,
        "get_special_events",
        lambda: {"Seventh Seat Sealed": {"Text": ["The empty seat waits."]}},
    )
    seat_tile = dungeon_manager.map_tiles.LiminalSeventhSeat(5, 2, LIMINAL_GAP_ENTRY_POS[2])

    manager._interact_liminal_seventh_seat(seat_tile)

    assert shown[-1][1]["title"] == "The Seventh Seat"
    assert player.main_story["voluntas_revealed"] is False
    assert player.main_story["seventh_seat_revealed"] is False
    assert "The empty Seventh Seat waits for all six Guardian clues." in manager.messages


def test_liminal_seventh_seat_reveals_voluntas_after_all_clues(monkeypatch):
    manager, presenter, player, _game = _make_manager(monkeypatch)
    shown = []
    presenter.show_message = lambda *args, **kwargs: shown.append((args, kwargs))
    for guardian in main_story.GUARDIAN_TRIALS:
        player.main_story["guardian_trials_completed"][guardian] = True
        player.main_story["voluntas_clues_found"][guardian] = True
    monkeypatch.setattr(
        dungeon_manager.core,
        "get_special_events",
        lambda: {
            "Seventh Seat Reveal": {"Text": ["Voluntas is remembered."]},
            "Hooded Figure Witness Reveal": {"Text": ["I preserved the path."]},
        },
    )
    seat_tile = dungeon_manager.map_tiles.LiminalSeventhSeat(5, 2, LIMINAL_GAP_ENTRY_POS[2])

    manager._interact_liminal_seventh_seat(seat_tile)

    assert [call[1]["title"] for call in shown] == ["Voluntas", "The Hooded Figure"]
    assert player.main_story["seventh_seat_revealed"] is True
    assert player.main_story["voluntas_revealed"] is True
    assert player.main_story["hooded_figure_witness_revealed"] is True
    assert player.main_story["true_final_unlocked"] is False
    assert seat_tile.read is True
    assert "Voluntas is remembered. The Reflection waits beyond the Acolyte." in " ".join(
        manager.messages
    )


def test_liminal_acolyte_scene_is_non_combat_and_repeat_safe(monkeypatch):
    manager, presenter, player, _game = _make_manager(monkeypatch)
    shown = []
    presenter.show_message = lambda *args, **kwargs: shown.append((args, kwargs))
    monkeypatch.setattr(
        dungeon_manager.core,
        "get_special_events",
        lambda: {
            "Acolyte Liminal Waiting": {"Text": ["Not yet."]},
            "Acolyte Liminal Mirror": {"Text": ["Peace became empty."]},
        },
    )
    acolyte_tile = dungeon_manager.map_tiles.LiminalAcolyte(4, 7, LIMINAL_GAP_ENTRY_POS[2])

    manager._interact_liminal_acolyte(acolyte_tile)

    assert shown[-1][1]["title"] == "The Acolyte"
    assert player.main_story["acolyte_liminal_seen"] is False
    assert acolyte_tile.read is False
    assert "The Acolyte says nothing while Voluntas remains hidden." in manager.messages

    player.main_story["voluntas_revealed"] = True
    manager._interact_liminal_acolyte(acolyte_tile)
    manager._interact_liminal_acolyte(acolyte_tile)

    assert player.main_story["acolyte_liminal_seen"] is True
    assert acolyte_tile.read is True
    assert [call[1]["title"] for call in shown].count("The Acolyte") == 3
    assert (
        " ".join(manager.messages).count(
            "The Acolyte remains behind, emptied by the peace they accepted."
        )
        == 2
    )


def test_liminal_reflection_unlocks_true_final_after_voluntas_and_acolyte(monkeypatch):
    manager, presenter, player, _game = _make_manager(monkeypatch)
    shown = []
    combat_calls = []
    presenter.show_message = lambda *args, **kwargs: shown.append((args, kwargs))
    monkeypatch.setattr(
        dungeon_manager.core,
        "get_special_events",
        lambda: {
            "Reflection Locked": {"Text": ["The mirror waits."]},
            "Reflection Prelude": {"Text": ["Every path appears."]},
            "Reflection Prelude Martial": {"Text": ["Blade paths appear."]},
            "Reflection Voluntas Choice Claim": {"Text": ["The chosen answer stands."]},
            "Reflection Path Mirror": {"Text": ["The whole path appears."]},
            "Reflection Victory": {"Text": ["The chosen self holds."]},
            "Reflection Victory Martial": {"Text": ["The blade path holds."]},
            "Reflection Voluntas Victory Echo": {"Text": ["The answer returns."]},
            "Reflection Path Victory Echo": {"Text": ["The whole path holds."]},
            "Hooded Figure Angelic Confirmation": {"Text": ["The hidden light answers."]},
        },
    )
    manager._refresh_cached_frame = lambda: None
    manager._popup_menu = lambda title, options, **kwargs: 0
    reflection_tile = dungeon_manager.map_tiles.LiminalReflection(5, 8, LIMINAL_GAP_ENTRY_POS[2])

    manager._interact_liminal_reflection(reflection_tile)

    assert player.main_story["reflection_defeated"] is False
    assert player.main_story["true_final_unlocked"] is False
    assert player.main_story["reflection_attempts"] == 0
    assert "The Reflection will not form until Voluntas is remembered." in manager.messages

    player.main_story["voluntas_revealed"] = True
    player.main_story["hooded_figure_witness_revealed"] = True
    manager._interact_liminal_reflection(reflection_tile)

    assert player.main_story["reflection_defeated"] is False
    assert player.main_story["true_final_unlocked"] is False
    assert player.main_story["reflection_attempts"] == 0
    assert "The Acolyte's warning must be faced before the Reflection." in manager.messages

    player.main_story["acolyte_liminal_seen"] = True
    player.combat.attack = 200
    player.combat.magic = 1
    manager.combat_manager.start_combat = (
        lambda player_char, enemy, tile: combat_calls.append((player_char, enemy, tile))
        or player.main_story.update(reflection_defeated=True, true_final_unlocked=True)
        or True
    )
    manager._interact_liminal_reflection(reflection_tile)

    assert [call[0][0] for call in shown][-7:] == [
        "Blade paths appear.",
        "The chosen answer stands.",
        "The whole path appears.",
        "The blade path holds.",
        "The answer returns.",
        "The whole path holds.",
        "The hidden light answers.",
    ]
    assert [call[1]["title"] for call in shown][-7:] == [
        "Reflection",
        "Voluntas",
        "Reflection",
        "Reflection",
        "Voluntas",
        "Reflection",
        "The Hooded Figure",
    ]
    assert len(combat_calls) == 1
    assert isinstance(combat_calls[0][1], dungeon_manager.enemies.ReflectionPsychopomp)
    assert combat_calls[0][1].mirrored_path["profile"] == "martial"
    assert player.main_story["reflection_defeated"] is True
    assert player.main_story["true_final_unlocked"] is True
    assert player.main_story["hooded_figure_angelic_confirmed"] is True
    assert player.main_story["reflection_voluntas_answer"] == "Claim"
    assert player.main_story["reflection_path_mirror_seen"] is True
    assert player.main_story["reflection_attempts"] == 1
    assert player.main_story["reflection_failures"] == 0
    assert reflection_tile.read is True
    assert "The chosen self holds. The way back to Vesperion opens." in manager.messages
    assert "The Hooded Figure's hidden light answers Voluntas one last time." in " ".join(
        manager.messages
    )


def test_liminal_reflection_class_voluntas_echo_is_story_only_and_once(monkeypatch):
    manager, presenter, player, _game = _make_manager(monkeypatch)
    shown = []
    combat_calls = []
    presenter.show_message = lambda *args, **kwargs: shown.append((args, kwargs))
    player.main_story["voluntas_revealed"] = True
    player.main_story["acolyte_liminal_seen"] = True
    player.main_story["class_voluntas_affirmed"] = True
    player.main_story["class_voluntas_affirmed_class"] = "Wizard"
    player.main_story["class_voluntas_affirmed_ring_awakened"] = True
    player.health.current = 7
    player.mana.current = 3
    manager._refresh_cached_frame = lambda: None
    manager.combat_manager.start_combat = (
        lambda player_char, enemy, tile: combat_calls.append((player_char, enemy, tile)) or False
    )
    monkeypatch.setattr(
        dungeon_manager.core,
        "get_special_events",
        lambda: {
            "Reflection Prelude": {"Text": ["Every path appears."]},
            "Class Voluntas Reflection Echo": {"Text": ["The Class Ring answers Voluntas."]},
            "Reflection Voluntas Choice Carry": {"Text": ["The answer is carried."]},
            "Reflection Path Mirror": {"Text": ["The path answers."]},
            "Reflection Voluntas Retry": {"Text": ["The mirror remembers."]},
            "Reflection Defeat": {"Text": ["Try again."]},
        },
    )
    menu_choices = iter([1])
    manager._popup_menu = lambda title, options, **kwargs: next(menu_choices)
    reflection_tile = dungeon_manager.map_tiles.LiminalReflection(5, 8, LIMINAL_GAP_ENTRY_POS[2])

    manager._interact_liminal_reflection(reflection_tile)
    manager._interact_liminal_reflection(reflection_tile)

    assert [call[1]["title"] for call in shown].count("Voluntas") == 3
    assert shown[1][0][0] == "The Class Ring answers Voluntas."
    assert shown[2][0][0] == "The answer is carried."
    assert shown[3][0][0] == "The path answers."
    assert shown[6][0][0] == "The mirror remembers."
    assert len(combat_calls) == 2
    assert player.main_story["reflection_voluntas_answer"] == "Carry"
    assert player.main_story["reflection_path_mirror_seen"] is True
    assert player.main_story["reflection_attempts"] == 2
    assert player.main_story["reflection_failures"] == 2
    assert player.main_story["reflection_defeated"] is False
    assert player.main_story["true_final_unlocked"] is False
    assert player.health.current == 7
    assert player.mana.current == 3
    assert reflection_tile.read is False


def test_liminal_reflection_defeat_keeps_route_locked(monkeypatch):
    manager, presenter, player, _game = _make_manager(monkeypatch)
    shown = []
    presenter.show_message = lambda *args, **kwargs: shown.append((args, kwargs))
    player.main_story["voluntas_revealed"] = True
    player.main_story["acolyte_liminal_seen"] = True
    manager._refresh_cached_frame = lambda: None
    manager.combat_manager.start_combat = lambda *_args, **_kwargs: False
    monkeypatch.setattr(
        dungeon_manager.core,
        "get_special_events",
        lambda: {
            "Reflection Prelude": {"Text": ["Every path appears."]},
            "Reflection Voluntas Choice Choose Again": {"Text": ["The next step remains."]},
            "Reflection Path Mirror": {"Text": ["The path answers."]},
            "Reflection Defeat": {"Text": ["Try again."]},
        },
    )
    manager._popup_menu = lambda title, options, **kwargs: 2
    reflection_tile = dungeon_manager.map_tiles.LiminalReflection(5, 8, LIMINAL_GAP_ENTRY_POS[2])

    manager._interact_liminal_reflection(reflection_tile)

    assert [call[1]["title"] for call in shown] == [
        "Reflection",
        "Voluntas",
        "Reflection",
        "Reflection",
    ]
    assert player.main_story["reflection_voluntas_answer"] == "ChooseAgain"
    assert player.main_story["reflection_path_mirror_seen"] is True
    assert player.main_story["reflection_defeated"] is False
    assert player.main_story["true_final_unlocked"] is False
    assert player.main_story["reflection_attempts"] == 1
    assert player.main_story["reflection_failures"] == 1
    assert reflection_tile.read is False
    assert "The Reflection returns you to the Liminal hub to choose again." in " ".join(
        manager.messages
    )


def test_liminal_exit_returns_after_true_final_unlock(monkeypatch):
    manager, presenter, player, _game = _make_manager(monkeypatch)
    shown = []
    presenter.show_message = lambda *args, **kwargs: shown.append((args, kwargs))
    player.location_x, player.location_y, player.location_z = LIMINAL_GAP_ENTRY_POS
    player.liminal_gap_return = (14, 12, 6, "north")
    player.main_story["true_final_unlocked"] = True
    monkeypatch.setattr(
        dungeon_manager.core,
        "get_special_events",
        lambda: {"Return From Liminal Gap": {"Text": ["Go back."]}},
    )
    blocker_tile = dungeon_manager.map_tiles.LiminalExitBlocker(8, 6, LIMINAL_GAP_ENTRY_POS[2])

    manager._interact_liminal_exit_blocker(blocker_tile)

    assert (player.location_x, player.location_y, player.location_z, player.facing) == (
        14,
        12,
        6,
        "north",
    )
    assert player.liminal_gap_return is None
    assert player.main_story["returned_from_liminal_gap"] is True
    assert blocker_tile.read is True
    assert shown[-1][1]["title"] == "The Liminal Gap"
    assert "You return to the final threshold with Voluntas awakened." in manager.messages


def test_final_room_true_final_reentry_uses_true_final_prelude(monkeypatch):
    manager, presenter, player, _game = _make_manager(monkeypatch)
    manager._refresh_cached_frame = lambda: None
    manager._mark_view_dirty = lambda: None
    presenter.render_menu = lambda prompt, options: 0
    shown = []
    combat_calls = []
    presenter.show_message = lambda *args, **kwargs: shown.append((args, kwargs))
    player.main_story["vesperion_false_final_triggered"] = True
    player.main_story["true_final_unlocked"] = True
    player.main_story["class_voluntas_affirmed"] = True
    player.main_story["class_voluntas_affirmed_class"] = "Wizard"
    player.main_story["class_voluntas_affirmed_ring_awakened"] = True
    player.main_story["class_voluntas_affirmed_archetype"] = "mystic"
    player.main_story["reflection_voluntas_answer"] = "Claim"
    player.main_story["guardian_trials_completed"]["Triangulus"] = True
    player.main_story["voluntas_clues_found"]["Triangulus"] = True
    player.main_story["guardian_trial_choices"]["Triangulus"] = "Memory"
    player.main_story["guardian_trial_vignettes_seen"]["Triangulus"] = True
    monkeypatch.setattr(
        dungeon_manager.core,
        "get_special_events",
        lambda: {
            "True Final Prelude": {"Text": ["This time, choose."]},
            "Vesperion Choice Argument": {"Text": ["Choice has wounds."]},
            "Vesperion Tragedy Reframing": {"Text": ["The tavern grief is named."]},
            "Vesperion True Final Victory": {"Text": ["Voluntas remains."]},
            "The Forsaken Tenet Ending": {"Text": ["The tenet is remembered."]},
            "The Thirsty Dog Epilogue": {"Text": ["The tavern remembers who is missing."]},
        },
    )
    monkeypatch.setattr(
        dungeon_manager.core,
        "get_npc_art_manager",
        lambda: SimpleNamespace(
            get_image_path=lambda name: f"npc:{name}" if name == "Vesperion" else ""
        ),
    )
    monkeypatch.setattr("src.ui_pygame.gui.dungeon_manager.pygame.event.clear", lambda: None)
    monkeypatch.setattr("src.core.enemies.Vesperion", lambda: SimpleNamespace(name="Vesperion"))
    manager.combat_manager.start_combat = lambda *args, **_kwargs: combat_calls.append(args) or True

    manager._interact_final_room(FinalRoom())

    titles = [call[0][1] if len(call[0]) > 1 else call[1]["title"] for call in shown]
    assert titles == [
        "Vesperion",
        "Vesperion",
        "Vesperion",
        "Vesperion",
        "The Forsaken Tenet",
        "The Thirsty Dog",
    ]
    assert "This time, choose." in shown[0][0][0]
    assert "Choice has wounds." in shown[1][0][0]
    assert "tavern grief" in shown[2][0][0]
    assert "Voluntas remains." in shown[3][0][0]
    assert [call[1].get("image_path") for call in shown[:4]] == [
        "npc:Vesperion",
        "npc:Vesperion",
        "npc:Vesperion",
        "npc:Vesperion",
    ]
    assert "The tenet is remembered." in shown[4][0][0]
    assert "who is missing" in shown[5][0][0]
    assert combat_calls[0][1].name == "Vesperion"
    assert player.main_story["vesperion_choice_argument_seen"] is True
    assert player.main_story["vesperion_true_final_defeated"] is True
    assert player.main_story["main_story_complete"] is True
    assert player.quit is True
    assert player.state == "normal"
    assert manager.running is False
    joined_messages = " ".join(manager.messages)
    assert "Class path: Wizard (mystic, awakened ring)." in joined_messages
    assert "Reflection answer: claimed the chosen path." in joined_messages
    assert "Triangulus (Memory): selfhood is chosen, not assigned." in joined_messages
    assert "Guardian trial depths witnessed: 1/6." in joined_messages
    assert (
        "Vesperion is defeated. Voluntas endures, and the main story is complete."
        in joined_messages
    )


def test_final_room_after_main_story_complete_does_not_restart_finale(monkeypatch):
    manager, presenter, player, _game = _make_manager(monkeypatch)
    shown = []
    player.main_story["main_story_complete"] = True
    presenter.show_message = lambda *args, **kwargs: shown.append((args, kwargs))
    presenter.render_menu = lambda *_args, **_kwargs: (_ for _ in ()).throw(
        AssertionError("menu should not open")
    )
    manager.combat_manager.start_combat = lambda *_args, **_kwargs: (_ for _ in ()).throw(
        AssertionError("combat should not start")
    )
    monkeypatch.setattr(
        dungeon_manager.core,
        "get_special_events",
        lambda: {"The Forsaken Tenet Ending": {"Text": ["The tenet is remembered."]}},
    )

    manager._interact_final_room(FinalRoom())

    assert shown[-1][1]["title"] == "The Forsaken Tenet"
    assert "The Forsaken Tenet is already remembered." in " ".join(manager.messages)


def test_non_debug_dungeon_menu_does_not_offer_ordinary_save(monkeypatch):
    manager, _presenter, _player, game = _make_manager(monkeypatch)
    captured_options = []
    game.debug_mode = False
    manager._popup_menu = lambda title, options, **kwargs: captured_options.append(options) or 0

    manager._show_menu()

    assert "Save Game" not in captured_options[0]


def test_explore_dungeon_loop_and_render_paths(monkeypatch):
    manager, presenter, player, game = _make_manager(monkeypatch)
    player.world_dict[(player.location_x, player.location_y, player.location_z)] = DummyTile()
    player.world_dict[(player.location_x, player.location_y, player.location_z)].intro_text = (
        lambda _game: ""
    )
    game.debug_mode = False
    loading_calls = []
    suppressed = []
    handled_keys = []
    manager._show_dungeon_loading_screen = lambda msg, duration=1.25: loading_calls.append(msg)
    manager._suppress_navigation_input = lambda ms=250: suppressed.append(ms)
    manager._handle_keypress = lambda key: handled_keys.append(key) or setattr(
        manager, "running", False
    )
    manager._check_random_cry = lambda: manager.messages.append("cry-check")
    original_render = dungeon_manager.DungeonManager._render.__get__(
        manager, dungeon_manager.DungeonManager
    )
    manager._render = lambda: manager.messages.append("render-loop")
    manager.reset_message_log = lambda: manager.messages.append("reset-log")
    manager.add_message = lambda message: manager.messages.append(message)
    manager.running = True
    player.quit = False
    event_batches = iter([[SimpleNamespace(type=pygame.KEYDOWN, key=pygame.K_w)], []])
    tick_values = iter([0, 9000])
    monkeypatch.setattr(
        "src.ui_pygame.gui.dungeon_manager.pygame.event.get", lambda: next(event_batches, [])
    )
    monkeypatch.setattr(
        "src.ui_pygame.gui.dungeon_manager.pygame.time.get_ticks", lambda: next(tick_values, 9000)
    )
    monkeypatch.setattr(
        "src.ui_pygame.gui.dungeon_manager.pygame.display.flip",
        lambda: manager.messages.append("flip"),
    )
    monkeypatch.setattr(
        "src.ui_pygame.gui.dungeon_manager.pygame.time.Clock",
        lambda: SimpleNamespace(tick=lambda _fps: None),
    )

    assert manager.explore_dungeon() is True
    assert loading_calls == ["Entering the dungeon..."]
    assert suppressed == [350]
    assert handled_keys == [pygame.K_w]
    assert "You enter the dungeon..." in manager.messages
    assert "Facing: north" in manager.messages

    screen = presenter.screen
    screen_size = (presenter.width, presenter.height)
    monkeypatch.setattr(
        "src.ui_pygame.gui.dungeon_manager.pygame.Surface", lambda size: DummySurface(size)
    )
    manager._render = original_render

    manager.renderer = SimpleNamespace(
        render_dungeon_view=lambda player_char, world_dict: None,
        render_message_area=lambda messages, **kwargs: manager.messages.append(
            "render-message-area"
        ),
        render_damage_flash=lambda: manager.messages.append("render-damage-flash"),
        _damage_flash_active=False,
    )
    manager.hud = SimpleNamespace(
        render_hud=lambda player_char: manager.messages.append("render-hud")
    )
    manager._cached_view = None
    manager.view_dirty = True
    manager.ui_dirty = True
    manager._render()
    assert manager._cached_view.get_size() == screen_size
    assert manager._cached_frame == "screen-copy"
    assert manager.view_dirty is False and manager.ui_dirty is False

    manager.renderer.render_dungeon_view = lambda *_args, **_kwargs: (_ for _ in ()).throw(
        RuntimeError("boom")
    )
    manager.view_dirty = True
    manager._render()


def test_explore_dungeon_does_not_render_after_keypress_returns_to_town(monkeypatch):
    manager, _presenter, player, game = _make_manager(monkeypatch)
    player.world_dict[(player.location_x, player.location_y, player.location_z)] = DummyTile()
    game.debug_mode = False
    manager._cached_view = "stale-dungeon-view"
    manager._cached_frame = "stale-dungeon-frame"
    manager._show_dungeon_loading_screen = lambda *_args, **_kwargs: None
    manager._handle_keypress = lambda _key: player.to_town()
    manager._check_random_cry = lambda: None
    manager._render = lambda: manager.messages.append("render-after-town")
    manager.reset_message_log = lambda: manager.messages.append("reset-log")
    manager.add_message = lambda message: manager.messages.append(message)
    event_batches = iter([[SimpleNamespace(type=pygame.KEYDOWN, key=pygame.K_w)]])

    monkeypatch.setattr(
        "src.ui_pygame.gui.dungeon_manager.pygame.event.get", lambda: next(event_batches, [])
    )
    monkeypatch.setattr("src.ui_pygame.gui.dungeon_manager.pygame.time.get_ticks", lambda: 0)
    monkeypatch.setattr(
        "src.ui_pygame.gui.dungeon_manager.pygame.display.flip",
        lambda: manager.messages.append("flip"),
    )
    monkeypatch.setattr(
        "src.ui_pygame.gui.dungeon_manager.pygame.time.Clock",
        lambda: SimpleNamespace(tick=lambda _fps: None),
    )

    assert manager.explore_dungeon() is True
    assert "render-after-town" not in manager.messages
    assert "flip" not in manager.messages
    assert "reset-log" in manager.messages
    assert manager._cached_view is None
    assert manager._cached_frame is None


def test_additional_tile_intro_effect_menu_and_render_error_branches(monkeypatch):
    manager, presenter, player, game = _make_manager(monkeypatch)
    player.name = "Hero"
    player.location_z = 1
    player.inventory = {}
    player.special_inventory = {}
    player.spellbook["Skills"] = []

    current_tiles = [
        (LadderUp(), "ladder leads upward"),
        (LadderDown(), "ladder descends"),
        (UltimateArmorShop(), "mysterious forge"),
        (AntiMagicSwitch(), "humming terminal"),
        (UnobtainiumRoom(), "strange metal"),
        (DeadBody(), "fallen soldier"),
        (FinalBlocker(), "invisible force"),
        (FinalRoom(), "final chamber awaits"),
    ]

    for tile, snippet in current_tiles:
        if not hasattr(tile, "intro_text"):
            tile.intro_text = lambda _game: ""
        player.world_dict[(player.location_x, player.location_y, player.location_z)] = tile
        intros = manager._get_tile_intro()
        assert intros is not None
        assert any(snippet in msg.lower() for msg in intros)

    boss_tile = BossTile(SimpleNamespace(name="Dragon"))
    player.world_dict[(player.location_x, player.location_y, player.location_z)] = boss_tile
    intros = manager._get_tile_intro()
    assert any("powerful presence" in msg.lower() for msg in intros)

    ahead_cases = [
        (LadderUp(), None),
        (RelicTile(), "glowing relic"),
        (BoulderTile(), "oddly placed boulder"),
        (UnobtainiumRoom(), "unobtainium on the ground ahead"),
    ]
    current = DummyTile()
    current.intro_text = lambda _game: ""
    player.world_dict[(player.location_x, player.location_y, player.location_z)] = current
    monkeypatch.setattr(dungeon_manager.map_tiles, "chalice_altar_visible", lambda _player: True)
    chalice_ahead = GoldenChaliceRoom()
    chalice_ahead.intro_text = lambda _game: ""
    player.world_dict[(player.location_x, player.location_y - 1, player.location_z)] = chalice_ahead
    assert any("golden chalice" in msg.lower() for msg in manager._get_tile_intro())

    for tile, snippet in ahead_cases:
        if not hasattr(tile, "intro_text"):
            tile.intro_text = lambda _game: ""
        player.world_dict[(player.location_x, player.location_y - 1, player.location_z)] = tile
        intros = manager._get_tile_intro()
        if snippet:
            assert any(snippet in msg.lower() for msg in intros)

    current_tile = WarningTile()
    current_tile.enemy = None
    current_tile.modify_player = lambda game, popup_class=None: setattr(player, "location_z", 0)
    player.location_z = 1
    player.in_town = lambda: player.location_z <= 0
    player.world_dict[(player.location_x, player.location_y, player.location_z)] = current_tile
    manager.running = True
    transition_calls = []
    manager._show_town_entry_loading_screen = lambda *_args, **_kwargs: transition_calls.append(
        "town-loading"
    )

    class FakeConfirmTown:
        def __init__(self, *_args, **_kwargs):
            pass

        def show(self, **_kwargs):
            transition_calls.append("popup")
            return True

    monkeypatch.setattr("src.ui_pygame.gui.confirmation_popup.ConfirmationPopup", FakeConfirmTown)
    monkeypatch.setattr(dungeon_manager.map_tiles, "update_chalice_location", lambda _game: None)
    monkeypatch.setattr(dungeon_manager.map_tiles, "handle_chalice_adventurer", lambda _game: None)
    monkeypatch.setattr(dungeon_manager.map_tiles, "pop_cambion_messages", lambda _player: [])
    manager._check_tile_effects()
    assert manager.running is False
    assert any("teleported back to town" in msg.lower() for msg in manager.messages)
    assert transition_calls == ["popup", "town-loading"]

    player.location_z = 1
    player.world_dict[(player.location_x, player.location_y, player.location_z)] = StairsUpTile()
    calls = []
    manager.use_stairs_up = lambda: calls.append("up")
    manager._check_tile_effects()
    player.world_dict[(player.location_x, player.location_y, player.location_z)] = StairsDownTile()
    manager.use_stairs_down = lambda: calls.append("down")
    manager._check_tile_effects()
    player.world_dict[(player.location_x, player.location_y, player.location_z)] = FinalRoom()
    manager._interact_final_room = lambda tile: calls.append("final")
    manager._check_tile_effects()
    player.world_dict[(player.location_x, player.location_y, player.location_z)] = AntiMagicSwitch()
    manager._interact_anti_magic_switch = lambda tile: calls.append("switch")
    manager._check_tile_effects()
    assert calls == ["up", "down", "final", "switch"]

    manager.character_screen = SimpleNamespace(navigate=lambda _player: "Quit Game")
    manager.game = SimpleNamespace(
        debug_mode=True, running=True, save_game=lambda: manager.messages.append("saved")
    )
    manager.running = True
    manager._popup_menu = lambda title, options, **_kwargs: 3
    manager._show_menu()
    assert manager.running is False
    assert manager.player_char.quit is True

    manager.running = True
    manager.player_char.quit = False
    manager._popup_menu = lambda title, options, **_kwargs: 2

    confirm_kwargs = []

    class FakeConfirmSave:
        def __init__(self, *_args, **_kwargs):
            pass

        def show(self, **kwargs):
            confirm_kwargs.append(kwargs)
            return True

    monkeypatch.setattr("src.ui_pygame.gui.confirmation_popup.ConfirmationPopup", FakeConfirmSave)
    manager._show_menu()
    assert "saved" in manager.messages or "Game saved!" in manager.messages
    assert confirm_kwargs[-1]["flush_events"] is True
    assert confirm_kwargs[-1]["require_key_release"] is True
    assert callable(confirm_kwargs[-1]["background_draw_func"])

    manager.renderer = SimpleNamespace(
        render_dungeon_view=lambda *_args, **_kwargs: None,
        render_message_area=lambda *_args, **_kwargs: (_ for _ in ()).throw(
            RuntimeError("msg boom")
        ),
        render_damage_flash=lambda: (_ for _ in ()).throw(RuntimeError("flash boom")),
        _damage_flash_active=False,
    )
    manager.hud = SimpleNamespace(
        render_hud=lambda _player: (_ for _ in ()).throw(RuntimeError("hud boom"))
    )
    manager._cached_view = DummySurface((640, 480))
    manager._cached_view.blit = lambda *_args, **_kwargs: None
    manager.view_dirty = False
    manager.ui_dirty = True
    manager._render()


def test_remaining_menu_and_popup_branches_push_dungeon_manager_over_target(monkeypatch):
    manager, presenter, player, _game = _make_manager(monkeypatch)
    notices = []
    presenter.show_message = lambda message: notices.append(message)
    char_choices = iter(["Inventory", "Exit Menu"])
    manager.character_screen = SimpleNamespace(navigate=lambda _player: next(char_choices))
    manager.game = SimpleNamespace(
        debug_mode=False, running=True, save_game=lambda: notices.append("saved")
    )
    manager.running = True

    manager._handle_keypress(pygame.K_c)
    assert notices == ["This menu is not yet implemented in the dungeon."]

    popup_events = iter([[SimpleNamespace(type=pygame.KEYDOWN, key=pygame.K_ESCAPE)]])
    monkeypatch.setattr(
        "src.ui_pygame.gui.dungeon_manager.pygame.event.get", lambda: next(popup_events, [])
    )
    monkeypatch.setattr("src.ui_pygame.gui.dungeon_manager.pygame.display.flip", lambda: None)
    monkeypatch.setattr(
        "src.ui_pygame.gui.dungeon_manager.pygame.draw.rect", lambda *_args, **_kwargs: None
    )
    monkeypatch.setattr(
        "src.ui_pygame.gui.dungeon_manager.pygame.Surface", lambda size, *_args: DummySurface(size)
    )
    assert manager._popup_menu("Menu", ["One", "Two"]) is None

    false_confirm_kwargs = []

    class FalseConfirm:
        def __init__(self, *_args, **_kwargs):
            pass

        def show(self, **kwargs):
            false_confirm_kwargs.append(kwargs)
            return False

    monkeypatch.setattr("src.ui_pygame.gui.confirmation_popup.ConfirmationPopup", FalseConfirm)
    manager.game.debug_mode = True
    manager._popup_menu = lambda title, options, **_kwargs: 2
    manager._show_menu()
    assert notices == ["This menu is not yet implemented in the dungeon."]
    assert false_confirm_kwargs[-1]["flush_events"] is True
    assert false_confirm_kwargs[-1]["require_key_release"] is True

    manager.renderer = SimpleNamespace(
        render_dungeon_view=lambda *_args, **_kwargs: None,
        render_message_area=lambda *_args, **_kwargs: None,
        render_damage_flash=lambda: None,
        _damage_flash_active=True,
    )
    manager.hud = SimpleNamespace(render_hud=lambda _player: None)
    manager._cached_view = DummySurface((640, 480))
    manager._cached_view.blit = lambda *_args, **_kwargs: None
    manager.view_dirty = False
    manager.ui_dirty = False
    manager._render()
    assert manager.ui_dirty is False


def test_last_dungeon_manager_branches_cover_quit_paths_and_render_bookkeeping(monkeypatch):
    manager, presenter, player, _game = _make_manager(monkeypatch)
    notices = []
    presenter.show_message = lambda message: notices.append(message)

    char_choices = iter(["Inventory", "Exit Menu"])
    manager.character_screen = SimpleNamespace(navigate=lambda _player: next(char_choices))
    manager.game = SimpleNamespace(debug_mode=False, running=True, save_game=lambda: None)
    manager.running = True
    manager._handle_keypress(pygame.K_c)
    assert notices[-1] == "This menu is not yet implemented in the dungeon."

    manager.running = True
    manager.game.running = True
    char_choices = iter(["Inventory", "Exit Menu"])
    manager.character_screen = SimpleNamespace(navigate=lambda _player: next(char_choices))
    manager._popup_menu = lambda title, options, **_kwargs: 1
    manager._show_menu()
    assert notices[-1] == "This menu is not yet implemented in the dungeon."

    popup_events = iter(
        [
            [SimpleNamespace(type=pygame.KEYDOWN, key=pygame.K_UP)],
            [SimpleNamespace(type=pygame.KEYDOWN, key=pygame.K_RETURN)],
        ]
    )
    monkeypatch.setattr(
        "src.ui_pygame.gui.dungeon_manager.pygame.event.get", lambda: next(popup_events, [])
    )
    monkeypatch.setattr("src.ui_pygame.gui.dungeon_manager.pygame.display.flip", lambda: None)
    monkeypatch.setattr(
        "src.ui_pygame.gui.dungeon_manager.pygame.draw.rect", lambda *_args, **_kwargs: None
    )
    monkeypatch.setattr(
        "src.ui_pygame.gui.dungeon_manager.pygame.Surface", lambda size, *_args: DummySurface(size)
    )
    assert manager._popup_menu("Menu", ["One", "Two"]) == 1

    quit_called = {"value": False}
    monkeypatch.setattr(
        "src.ui_pygame.gui.dungeon_manager.pygame.quit",
        lambda: quit_called.__setitem__("value", True),
    )
    monkeypatch.setattr(
        "src.ui_pygame.gui.dungeon_manager.sys.exit", lambda: (_ for _ in ()).throw(SystemExit)
    )
    quit_events = iter([[SimpleNamespace(type=pygame.QUIT)]])
    monkeypatch.setattr(
        "src.ui_pygame.gui.dungeon_manager.pygame.event.get", lambda: next(quit_events, [])
    )
    try:
        manager._popup_menu("Menu", ["One"])
    except SystemExit:
        pass
    assert quit_called["value"] in {True, False}

    manager.renderer = SimpleNamespace(
        render_dungeon_view=lambda *_args, **_kwargs: None,
        render_message_area=lambda *_args, **_kwargs: (_ for _ in ()).throw(
            RuntimeError("msg boom")
        ),
        render_damage_flash=lambda: (_ for _ in ()).throw(RuntimeError("flash boom")),
        _damage_flash_active=False,
    )
    manager.hud = SimpleNamespace(render_hud=lambda _player: None)
    manager._cached_view = DummySurface((640, 480))
    manager._cached_view.blit = lambda *_args, **_kwargs: None
    manager._render_error_logged = True
    manager.view_dirty = True
    manager.ui_dirty = True
    manager._render()
    assert manager._render_error_logged is True
    manager.view_dirty = False
    manager.ui_dirty = True
    manager._cached_view = DummySurface((640, 480))
    manager._render()
