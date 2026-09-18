#!/usr/bin/env python3
"""Focused coverage for pygame game launcher helpers."""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from src.core import items
from src.core.classes import class_rings
from src.ui_pygame import game as pygame_game


def test_signal_handler_quits_and_exits(monkeypatch):
    quit_calls = []
    exit_codes = []
    monkeypatch.setattr("src.ui_pygame.game.pygame.quit", lambda: quit_calls.append(True))
    monkeypatch.setattr(
        "src.ui_pygame.game.sys.exit",
        lambda code=0: exit_codes.append(code) or (_ for _ in ()).throw(SystemExit(code)),
    )

    with pytest.raises(SystemExit):
        pygame_game.signal_handler(None, None)

    assert quit_calls == [True]
    assert exit_codes == [0]


def test_signal_handler_registration_is_explicit(monkeypatch):
    calls = []
    monkeypatch.setattr(pygame_game.signal, "signal", lambda *args: calls.append(args))

    pygame_game.install_signal_handlers()

    assert calls == [(pygame_game.signal.SIGINT, pygame_game.signal_handler)]


def test_main_returns_nonzero_for_fatal_startup_failure(monkeypatch, capsys):
    monkeypatch.setattr(pygame_game, "install_signal_handlers", lambda: None)
    monkeypatch.setattr(
        pygame_game,
        "PygameGame",
        lambda **_kwargs: (_ for _ in ()).throw(RuntimeError("startup exploded")),
    )
    monkeypatch.setattr(pygame_game.sys, "argv", ["game_pygame.py"])

    assert pygame_game.main() == 1
    assert "Fatal startup error: startup exploded" in capsys.readouterr().err


def test_cleanup_clears_background_provider_and_quits(monkeypatch):
    game = pygame_game.PygameGame.__new__(pygame_game.PygameGame)
    cleanup_calls = []
    provider_values = []
    quit_calls = []
    game.presenter = SimpleNamespace(
        cleanup=lambda: cleanup_calls.append(True),
        set_background_provider=lambda provider: provider_values.append(provider),
    )
    monkeypatch.setattr(pygame_game.pygame, "quit", lambda: quit_calls.append(True))

    game.cleanup()

    assert cleanup_calls == [True]
    assert provider_values == [None]
    assert quit_calls == [True]


def test_cleanup_clears_background_provider_when_presenter_cleanup_fails(monkeypatch):
    game = pygame_game.PygameGame.__new__(pygame_game.PygameGame)
    cleanup_calls = []
    provider_values = []
    quit_calls = []

    def fail_cleanup():
        cleanup_calls.append(True)
        raise RuntimeError("cleanup failed")

    game.presenter = SimpleNamespace(
        cleanup=fail_cleanup,
        set_background_provider=lambda provider: provider_values.append(provider),
    )
    monkeypatch.setattr(pygame_game.pygame, "quit", lambda: quit_calls.append(True))

    with pytest.raises(RuntimeError, match="cleanup failed"):
        game.cleanup()

    assert cleanup_calls == [True]
    assert provider_values == [None]
    assert quit_calls == [True]


def test_display_settings_uses_popup_and_applies_selected_native_mode(monkeypatch):
    """The display selector remains an in-style modal and applies immediately."""
    game = pygame_game.PygameGame.__new__(pygame_game.PygameGame)
    applied = []
    game.presenter = SimpleNamespace(
        apply_display_mode=lambda **kwargs: applied.append(kwargs),
    )
    game.fullscreen = False
    selections = iter([1, 4])
    popup_calls = []

    class FakeChoicePopup:
        def __init__(self, _presenter, title, options, header_message):
            popup_calls.append((title, tuple(options), header_message))

        def show(self):
            return next(selections)

    monkeypatch.setattr(pygame_game, "ChoicePopup", FakeChoicePopup)

    assert game.show_display_settings() is True
    assert applied == [{"fullscreen": False, "resolution": (1366, 768)}]
    assert game.fullscreen is False
    assert popup_calls[0][0] == "Display Settings"
    assert popup_calls[0][1][-1] == "Back"


def test_init_build_character_and_default_character(monkeypatch):
    class FakePresenter:
        def __init__(self):
            self.screen = SimpleNamespace()
            self.event_bus = "bus"
            self.height = 480
            self.width = 640
            self.debug_mode = False
            self.cleanup_called = False

        def cleanup(self):
            self.cleanup_called = True

    monkeypatch.setattr("src.ui_pygame.game.pygame.init", lambda: None)
    monkeypatch.setattr(pygame_game, "PygamePresenter", FakePresenter)
    monkeypatch.setattr(pygame_game.SaveManager, "list_saves", staticmethod(lambda: ["hero.save"]))
    game = pygame_game.PygameGame(debug_mode=True)

    assert game.load_files == ["hero.save"]
    assert game.event_bus == "bus"
    assert game.presenter.debug_mode is True

    class FakeRace:
        def __init__(self):
            self.name = "Human"
            self.strength = 1
            self.intel = 2
            self.wisdom = 3
            self.con = 4
            self.charisma = 5
            self.dex = 6
            self.base_attack = 7
            self.base_defense = 8
            self.base_magic = 9
            self.base_magic_def = 10
            self.resistance = {"Fire": 0.1}
            self.cls_res = {"Base": ["Warrior"]}

    class FakeClass:
        def __init__(self):
            self.name = "Warrior"
            self.str_plus = 10
            self.int_plus = 11
            self.wis_plus = 12
            self.con_plus = 13
            self.cha_plus = 14
            self.dex_plus = 15
            self.att_plus = 2
            self.def_plus = 3
            self.magic_plus = 4
            self.magic_def_plus = 5
            self.equipment = {"Weapon": "starter"}

    created = {}

    class FakePlayer:
        def __init__(
            self,
            location_x,
            location_y,
            location_z,
            level,
            health,
            mana,
            stats,
            combat,
            gold,
            resistance,
        ):
            created.update(
                location=(location_x, location_y, location_z),
                level=level,
                health=health,
                mana=mana,
                stats=stats,
                combat=combat,
                gold=gold,
                resistance=resistance,
            )
            self.location_x = location_x
            self.location_y = location_y
            self.location_z = location_z
            self.level = level
            self.health = health
            self.mana = mana
            self.stats = stats
            self.combat = combat
            self.gold = gold
            self.resistance = resistance
            self.spellbook = {"Spells": {}, "Skills": {}}
            self.storage = {}
            self.equipment = {}
            self.loaded_tiles = False

        def load_tiles(self):
            self.loaded_tiles = True

    class FakeSpell:
        def __init__(self):
            self.name = "Spark"

    monkeypatch.setattr("src.core.player.Player", FakePlayer)
    monkeypatch.setattr("src.core.abilities.spell_dict", {"Warrior": {"1": FakeSpell}})
    monkeypatch.setattr(pygame_game.items, "HealthPotion", lambda: "potion")

    game.races_dict = {"Human": FakeRace}
    game.classes_dict = {"Warrior": {"class": FakeClass}}
    player = game._build_player_character("Human", "Warrior", name="Ada")

    assert created["location"] == (5, 10, 0)
    assert player.name == "Ada"
    assert player.race.name == "Human"
    assert player.cls.name == "Warrior"
    assert player.portrait_variant == 0
    assert "Spark" not in player.spellbook["Spells"]
    assert player.spellbook["Skills"] == {}
    assert player.progression.unspent_points == 1
    assert player.progression.purchased_node_ids == set()
    assert player.storage["Health Potion"] == ["potion"] * 5
    assert player.loaded_tiles is True
    assert game.create_default_character(name="Bob").name == "Bob"


def test_debug_level_up_initialize_managers_and_update_bounties(monkeypatch):
    game = pygame_game.PygameGame.__new__(pygame_game.PygameGame)
    game.debug_mode = True
    game.presenter = SimpleNamespace(screen="screen")
    game.player_char = SimpleNamespace(
        level=SimpleNamespace(level=5, exp=10, exp_to_gain=20),
        max_level=lambda: False,
    )

    class FakeLevelUpScreen:
        def __init__(self, screen, presenter):
            self.screen = screen
            self.presenter = presenter

        def show_level_up(self, player_char, game_obj):
            calls.append((player_char, game_obj))

    calls = []
    monkeypatch.setattr("src.ui_pygame.gui.level_up.LevelUpScreen", FakeLevelUpScreen)
    game.debug_level_up()
    assert game.player_char.level.exp == 10
    assert game.player_char.level.exp_to_gain == 20
    assert calls == [(game.player_char, game)]

    game.player_char.max_level = lambda: True
    popup_calls = []

    class FakeConfirmationPopup:
        def __init__(self, presenter, message, show_buttons=True):
            popup_calls.append((presenter, message, show_buttons))

        def show(self, **kwargs):
            popup_calls.append(kwargs)

    monkeypatch.setattr(pygame_game, "ConfirmationPopup", FakeConfirmationPopup)
    game.debug_level_up()
    assert popup_calls == [
        (game.presenter, "Already at max level.", False),
        {"flush_events": True, "require_key_release": True},
    ]

    manager_calls = []
    monkeypatch.setattr(
        pygame_game,
        "ShopManager",
        lambda presenter, player: manager_calls.append(("shop", player)) or "shop",
    )
    monkeypatch.setattr(
        pygame_game,
        "ChurchManager",
        lambda presenter, player: manager_calls.append(("church", player)) or "church",
    )
    monkeypatch.setattr(
        pygame_game,
        "InnManager",
        lambda presenter, player: manager_calls.append(("inn", player)) or "inn",
    )
    monkeypatch.setattr(
        pygame_game,
        "BarracksManager",
        lambda presenter, player: manager_calls.append(("barracks", player)) or "barracks",
    )
    monkeypatch.setattr(
        pygame_game,
        "DungeonManager",
        lambda presenter, player, game_obj: manager_calls.append(("dungeon", player, game_obj))
        or "dungeon",
    )
    game.initialize_managers()
    assert game.shop_manager == "shop"
    assert game.dungeon_manager == "dungeon"

    class FakeBountyBoard:
        def __init__(self):
            self.bounties = [{"enemy": SimpleNamespace(name="Goblin"), "reward": 50}]

        def generate_bounties(self, game_obj):
            manager_calls.append(("bounties", game_obj))

    monkeypatch.setattr("src.core.town.BountyBoard", FakeBountyBoard)
    game.update_bounties()
    assert game.bounties["Goblin"]["reward"] == 50


def test_location_music_wrapper_is_defensive_and_routes_to_sound_manager():
    game = pygame_game.PygameGame.__new__(pygame_game.PygameGame)
    calls = []
    stop_calls = []
    game.presenter = SimpleNamespace(
        sound_manager=SimpleNamespace(
            play_location_music=lambda location, **kwargs: calls.append((location, kwargs))
            or "theme",
            stop_music=lambda **kwargs: stop_calls.append(kwargs),
        )
    )

    assert game._play_location_music("dungeon", boss=True) == "theme"
    assert calls == [("dungeon", {"boss": True, "final": False})]
    game._stop_music(fade_ms=125)
    assert stop_calls == [{"fade_ms": 125}]

    game.presenter.sound_manager.play_location_music = lambda *_args, **_kwargs: (
        _ for _ in ()
    ).throw(RuntimeError("audio"))
    assert game._play_location_music("town") is None
    game.presenter.sound_manager.stop_music = lambda *_args, **_kwargs: (_ for _ in ()).throw(
        RuntimeError("audio")
    )
    game._stop_music()

    game.presenter.sound_manager = None
    assert game._play_location_music("town") is None
    game._stop_music()


def test_top_level_flows_request_location_music(monkeypatch):
    game = pygame_game.PygameGame.__new__(pygame_game.PygameGame)
    music_calls = []
    game._play_location_music = (
        lambda location, **kwargs: music_calls.append((location, kwargs)) or location
    )
    game.presenter = SimpleNamespace(set_background_provider=lambda _provider: None)
    game.shop_manager = SimpleNamespace(
        visit_blacksmith=lambda: None,
        visit_alchemist=lambda: None,
        visit_jeweler=lambda: None,
        visit_magic_shop=lambda: None,
    )
    game.church_manager = SimpleNamespace(visit_church=lambda: None)
    game.barracks_manager = SimpleNamespace(visit_barracks=lambda: None)
    game.inn_manager = SimpleNamespace(visit_inn=lambda: None)
    game.dungeon_manager = SimpleNamespace(explore_dungeon=lambda: None)
    game.player_char = SimpleNamespace(quit=False, in_town=lambda: True)

    class FakeShopSelection:
        def __init__(self, _presenter):
            pass

        def navigate(self, options, **_kwargs):
            return len(options) - 1

    monkeypatch.setattr(pygame_game, "ShopSelectionScreen", FakeShopSelection)

    game.visit_shop()
    game.visit_church()
    game.visit_barracks()
    game.visit_inn()
    game.enter_dungeon()

    assert music_calls == [
        ("shop", {}),
        ("church", {}),
        ("town", {}),
        ("inn", {}),
        ("dungeon", {}),
        ("town", {}),
    ]


def test_new_game_uses_guarded_race_and_class_selection(monkeypatch):
    game = pygame_game.PygameGame.__new__(pygame_game.PygameGame)
    route_kwargs = []
    game.presenter = SimpleNamespace(
        show_message=lambda _message: None,
        get_text_input=lambda _prompt: "Ada",
    )

    class FakeRace:
        name = "Human"

    class FakeClass:
        name = "Warrior"

    class FakeRaceScreen:
        def __init__(self, _presenter):
            pass

        def navigate(self, races_dict, **kwargs):
            route_kwargs.append(("race", kwargs))
            return "Human"

    class FakeClassScreen:
        def __init__(self, _presenter):
            pass

        def navigate(self, race_name, race, classes_dict, **kwargs):
            route_kwargs.append(("class", kwargs))
            return "Warrior"

    class FakeNamingScreen:
        def __init__(self, _presenter, race_name, class_name):
            route_kwargs.append(("naming_init", {"race": race_name, "class": class_name}))
            self.sex = "Female"
            self.selected_portrait_variant = 4

        def navigate(self, **kwargs):
            route_kwargs.append(("naming", kwargs))
            return "Ada"

    class FakePopup:
        def __init__(self, *_args, **_kwargs):
            pass

        def show(self, **_kwargs):
            return True

    class FakeCreatedScreen:
        def __init__(self, _presenter, player_char):
            route_kwargs.append(("created_init", {"name": player_char.name}))

        def show(self, **kwargs):
            route_kwargs.append(("created", kwargs))
            return True

    game.races_dict = {"Human": FakeRace}
    game.classes_dict = {"Warrior": {"class": FakeClass}}
    game._build_player_character = (
        lambda race_name, class_name, name, sex, portrait_variant=0: SimpleNamespace(
            race_name=race_name,
            class_name=class_name,
            name=name,
            sex=sex,
            portrait_variant=portrait_variant,
            health=SimpleNamespace(max=20),
            mana=SimpleNamespace(max=10),
        )
    )
    game.initialize_managers = lambda: None
    monkeypatch.setattr(pygame_game, "RaceSelectionScreen", FakeRaceScreen)
    monkeypatch.setattr(pygame_game, "ClassSelectionScreen", FakeClassScreen)
    monkeypatch.setattr(pygame_game, "CharacterNamingScreen", FakeNamingScreen)
    monkeypatch.setattr(pygame_game, "ConfirmationPopup", FakePopup)
    monkeypatch.setattr(pygame_game, "CharacterCreatedScreen", FakeCreatedScreen)

    player = game.new_game()

    assert player.name == "Ada"
    assert player.sex == "Female"
    assert player.portrait_variant == 4
    assert route_kwargs == [
        ("race", {"flush_events": True, "require_key_release": True}),
        ("class", {"flush_events": True, "require_key_release": True}),
        ("naming_init", {"race": "Human", "class": "Warrior"}),
        ("naming", {"default": "Hero", "flush_events": True, "require_key_release": True}),
        ("created_init", {"name": "Ada"}),
        ("created", {"flush_events": True, "require_key_release": True}),
    ]


def test_main_menu_load_game_show_intro_warp_point_save_and_character_info(monkeypatch):
    game = pygame_game.PygameGame.__new__(pygame_game.PygameGame)
    popup_messages = []
    popup_kwargs = []
    popup_show_calls = []
    presenter_messages = []
    progress_calls = []

    def show_progress_popup(**kwargs):
        progress_calls.append(kwargs)
        work = kwargs.get("work")
        return work() if work else None

    presenter = SimpleNamespace(
        show_message=lambda message, title="": presenter_messages.append((title, message)),
        show_progress_popup=show_progress_popup,
        cleanup=lambda: cleanup_calls.append(True),
        set_background_provider=lambda provider: background_provider_calls.append(provider),
    )
    cleanup_calls = []
    background_provider_calls = []
    game.presenter = presenter
    game.running = True
    game.debug_mode = True
    game._random_combat = True
    game.load_files = ["save1"]
    game.player_char = None
    game.initialize_managers = lambda: init_calls.append(True)
    save_list = ["save1"]
    monkeypatch.setattr(
        pygame_game.SaveManager, "list_saves", staticmethod(lambda: list(save_list))
    )
    stop_calls = []
    music_calls = []
    game._stop_music = lambda **kwargs: stop_calls.append(kwargs)
    game._play_location_music = (
        lambda location, **kwargs: music_calls.append((location, kwargs)) or location
    )
    init_calls = []

    class FakePopup:
        def __init__(self, presenter_obj, message, show_buttons=False, **_kwargs):
            popup_messages.append(message)
            self.message = message

        def show(self, **kwargs):
            popup_kwargs.append(kwargs)
            popup_show_calls.append((self.message, kwargs))
            return True

    class FakeMenu:
        def __init__(self, presenter_obj):
            self.presenter_obj = presenter_obj

        def navigate(self, options, **kwargs):
            menu_calls.append(tuple(options))
            popup_kwargs.append(kwargs)
            return menu_choices.pop(0)

    menu_calls = []
    menu_choices = [2, 3]
    monkeypatch.setattr(pygame_game, "confirm_yes_no", lambda presenter_obj, message: False)
    monkeypatch.setattr(pygame_game, "ConfirmationPopup", FakePopup)
    monkeypatch.setattr(pygame_game, "MainMenuScreen", FakeMenu)
    game.new_game = lambda: None
    game.load_game = lambda: None
    game.show_display_settings = lambda: False
    game.run = lambda: run_calls.append(True)
    run_calls = []
    game.main_menu()
    assert game._random_combat is True
    assert any("Random encounters enabled" in msg for msg in popup_messages)
    assert popup_kwargs[-1]["flush_events"] is True
    assert popup_kwargs[-1]["require_key_release"] is True
    assert any("Settings" in opts for opts in menu_calls)
    assert game.running is False
    assert stop_calls == [{"fade_ms": 250}]
    assert music_calls == [("menu", {})]

    presenter_messages.clear()
    game.load_files = []
    save_list.clear()
    assert pygame_game.PygameGame.load_game(game) is None
    assert presenter_messages[-1][1] == "No saved games found!"
    assert game.load_files == []

    class FakeLoadScreen:
        def __init__(self, presenter_obj):
            self.presenter_obj = presenter_obj

        def navigate(self, save_files, **kwargs):
            popup_kwargs.append(kwargs)
            return navigate_results.pop(0)

    navigate_results = ["save1", "save2"]
    monkeypatch.setattr(pygame_game, "LoadGameScreen", FakeLoadScreen)
    monkeypatch.setattr(
        pygame_game.SaveManager, "load_player", staticmethod(lambda filename: load_results.pop(0))
    )
    load_results = [
        SimpleNamespace(in_town=lambda: True, quit=True),
        None,
    ]
    save_list[:] = ["save1"]
    game.load_files = []
    loaded = pygame_game.PygameGame.load_game(game)
    assert loaded.quit is False
    assert loaded._suppress_heal_message is True
    assert game.load_files == ["save1"]
    assert popup_kwargs[-1]["flush_events"] is True
    assert popup_kwargs[-1]["require_key_release"] is True
    assert progress_calls
    assert init_calls
    assert pygame_game.PygameGame.load_game(game) is None
    assert presenter_messages[-1][1] == "Failed to load character!"

    story_calls = []

    class FakeStorySequence:
        def __init__(self, presenter_obj, pages, title=""):
            story_calls.append(("init", tuple(pages), title))

        def show(self, **kwargs):
            story_calls.append(("show", kwargs))
            return True

    monkeypatch.setattr(pygame_game, "StoryCardSequence", FakeStorySequence)
    presenter_messages.clear()
    game.show_intro()
    assert len(presenter_messages) == 0
    assert story_calls[0][0] == "init"
    intro_pages = story_calls[0][1]
    assert len(intro_pages) == 6
    assert story_calls[0][2] == "The Story Begins"
    intro_text = "\n".join(intro_pages)
    for expected in ("Silvana", "relics", "guardians", "Step below"):
        assert expected in intro_text
    for spoiler in ("Vesperion", "Voluntas", "busboy", "Hooded Figure", "true final"):
        assert spoiler not in intro_text
    assert story_calls[1] == ("show", {"flush_events": True, "require_key_release": True})

    confirm_results = iter([True, False])
    popup_kwargs.clear()

    class FakePopup2:
        def __init__(self, presenter_obj, message, show_buttons=False, **_kwargs):
            popup_messages.append(message)
            self.message = message
            self._show_buttons = show_buttons

        def show(self, **kwargs):
            popup_kwargs.append(kwargs)
            if "Do you want to warp down to level 5?" in self.message:
                return next(confirm_results)
            return True

    monkeypatch.setattr(pygame_game, "ConfirmationPopup", FakePopup2)
    game.player_char = SimpleNamespace(
        name="Hero",
        world_dict={
            (3, 0, 5): SimpleNamespace(visited=False, warped=False),
            (2, 0, 5): SimpleNamespace(near=False),
            (4, 0, 5): SimpleNamespace(near=False),
            (3, -1, 5): SimpleNamespace(near=False),
            (3, 1, 5): SimpleNamespace(near=False),
        },
        location_x=0,
        location_y=0,
        location_z=0,
        facing="north",
        quit=False,
    )
    assert game.use_warp_point(background_draw_func=lambda: None) == "dungeon"
    assert any("Two field scientists" in message for message in popup_messages)
    assert any("throw their levers" in message for message in popup_messages)
    assert popup_kwargs[0]["flush_events"] is True
    assert popup_kwargs[0]["require_key_release"] is True
    assert callable(popup_kwargs[0]["background_draw_func"])
    assert game.player_char.location_x == 3 and game.player_char.location_z == 5
    assert game.player_char.world_dict[(3, 0, 5)].visited is True
    assert game.player_char.world_dict[(3, 0, 5)].warped is True
    assert game.player_char.world_dict[(2, 0, 5)].near is True
    assert game.use_warp_point(background_draw_func=lambda: None) is None

    render_menu_calls = []
    game.presenter = SimpleNamespace(
        render_menu=lambda prompt, options, **kwargs: render_menu_calls.append(
            (prompt, tuple(options), kwargs)
        )
        or 0,
        show_message=lambda message, title="": presenter_messages.append((title, message)),
        cleanup=lambda: cleanup_calls.append(True),
        set_background_provider=lambda provider: background_provider_calls.append(provider),
    )
    game.player_char = SimpleNamespace(
        name="Hero",
        world_dict={(3, 0, 5): SimpleNamespace(visited=False, warped=False)},
        location_x=0,
        location_y=0,
        location_z=0,
        facing="north",
        quit=False,
    )
    assert game.use_warp_point(background_draw_func=lambda: None) == "dungeon"
    assert render_menu_calls
    assert "Two field scientists" in render_menu_calls[0][0]
    assert render_menu_calls[0][1] == ("Yes", "No")
    assert render_menu_calls[0][2]["split_layout"] is True

    monkeypatch.setattr(
        pygame_game.SaveManager,
        "save_player",
        staticmethod(lambda player, filename: save_results.pop(0)),
    )
    monkeypatch.setattr(
        pygame_game.SaveManager, "list_saves", staticmethod(lambda: ["hero.save", "mage.save"])
    )
    save_results = [True, False]
    game.player_char = SimpleNamespace(name="Hero")
    game.save_game()
    assert game.load_files == ["hero.save", "mage.save"]
    assert "Game saved successfully!" in presenter_messages[-1][1]
    game.save_game()
    assert presenter_messages[-1][1] == "Save failed. Please try again."

    class FakeStandardCharacterScreen:
        def __init__(self, presenter_obj):
            self.presenter_obj = presenter_obj

        def navigate(self, player):
            return nav_results.pop(0)

    nav_results = ["Exit Menu"]
    monkeypatch.setattr(pygame_game, "ModernCharacterScreen", FakeStandardCharacterScreen)
    game.player_char = SimpleNamespace(quit=False)
    game.show_character_info()
    assert game.player_char.quit is False

    game.cleanup()
    assert cleanup_calls == [True]


def test_main_menu_stops_music_after_returning_from_gameplay(monkeypatch):
    game = pygame_game.PygameGame.__new__(pygame_game.PygameGame)
    game.presenter = SimpleNamespace()
    game.running = True
    game.debug_mode = False
    game.load_files = []
    game.player_char = None
    stop_calls = []
    music_calls = []
    run_calls = []
    game._stop_music = lambda **kwargs: stop_calls.append(kwargs)
    game._play_location_music = (
        lambda location, **kwargs: music_calls.append((location, kwargs)) or location
    )
    game.new_game = lambda: SimpleNamespace(name="Hero")
    game.run = lambda: run_calls.append(True)
    monkeypatch.setattr(pygame_game.SaveManager, "list_saves", staticmethod(lambda: []))

    class FakeMenu:
        def __init__(self, _presenter):
            pass

        def navigate(self, _options, **_kwargs):
            return menu_choices.pop(0)

    menu_choices = [0, 2]
    monkeypatch.setattr(pygame_game, "MainMenuScreen", FakeMenu)

    game.main_menu()

    assert run_calls == [True]
    assert stop_calls == [{"fade_ms": 250}, {"fade_ms": 250}]
    assert music_calls == [("menu", {})]


def test_main_menu_refreshes_save_files_before_rendering_options(monkeypatch):
    game = pygame_game.PygameGame.__new__(pygame_game.PygameGame)
    game.presenter = SimpleNamespace()
    game.running = True
    game.debug_mode = False
    game.load_files = []
    game.player_char = None
    game._stop_music = lambda **_kwargs: None
    game._play_location_music = lambda *_args, **_kwargs: None
    game.new_game = lambda: None
    game.load_game = lambda: load_calls.append(True)
    game.run = lambda: None
    load_calls = []
    menu_calls = []
    monkeypatch.setattr(pygame_game.SaveManager, "list_saves", staticmethod(lambda: ["fresh.save"]))

    class FakeMenu:
        def __init__(self, _presenter):
            pass

        def navigate(self, options, **_kwargs):
            menu_calls.append(tuple(options))
            return menu_choices.pop(0)

    menu_choices = [1, 3]
    monkeypatch.setattr(pygame_game, "MainMenuScreen", FakeMenu)

    game.main_menu()

    assert menu_calls[0] == ("New Game", "Load Game", "Settings", "Exit")
    assert load_calls == [True]
    assert game.load_files == ["fresh.save"]


def test_gameplay_statistics_popup_and_town_menu_entry(monkeypatch):
    game = pygame_game.PygameGame.__new__(pygame_game.PygameGame)
    game.presenter = SimpleNamespace()
    game.player_char = SimpleNamespace(
        name="Hero",
        level=SimpleNamespace(level=6),
        gameplay_stats={
            "steps_taken": "12",
            "stairs_used": 3,
            "enemies_defeated": 4,
            "deaths": 1,
            "flees": 2,
            "highest_level_reached": 5,
            "highest_damage_dealt": 99,
            "highest_damage_taken": 42,
        },
        town_heal=lambda: None,
        _suppress_heal_message=True,
        special_inventory={},
        quest_dict={"Side": {}},
        warp_point=False,
        quit=False,
    )

    popup_messages = []
    popup_kwargs = []

    class FakePopup:
        def __init__(self, _presenter, message, show_buttons=False, **_kwargs):
            popup_messages.append((message, show_buttons))

        def show(self, **kwargs):
            popup_kwargs.append(kwargs)
            return True

    monkeypatch.setattr(pygame_game, "ConfirmationPopup", FakePopup)

    formatted = pygame_game.PygameGame.format_gameplay_statistics(game.player_char)
    assert "Exploration" in formatted
    assert "Combat" in formatted
    assert "Records" in formatted
    assert "Steps Taken: 12" in formatted
    assert "Encounters Survived: 5" in formatted
    assert "Combat Outcomes: 7" in formatted
    assert "Combat Survival Rate: 71%" in formatted
    assert "Exploration Actions: 15" in formatted
    assert "Total Activity: 22" in formatted
    assert "Highest Level Reached: 6" in formatted

    broken_stats_player = SimpleNamespace(
        level=SimpleNamespace(level="bad"),
        gameplay_stats={
            "steps_taken": object(),
            "enemies_defeated": 1,
            "flees": 0,
            "deaths": 5,
            "highest_damage_taken": None,
        },
    )
    broken_formatted = pygame_game.PygameGame.format_gameplay_statistics(broken_stats_player)
    assert "Steps Taken: 0" in broken_formatted
    assert "Encounters Survived: 0" in broken_formatted
    assert "Combat Outcomes: 6" in broken_formatted
    assert "Combat Survival Rate: 0%" in broken_formatted
    assert "Exploration Actions: 0" in broken_formatted
    assert "Total Activity: 6" in broken_formatted
    assert "Highest Level Reached: 1" in broken_formatted

    game.show_gameplay_statistics(background_draw_func=lambda: None)
    assert "Adventure Statistics" in popup_messages[-1][0]
    assert popup_messages[-1][1] is False
    assert popup_kwargs[-1]["flush_events"] is True
    assert popup_kwargs[-1]["require_key_release"] is True

    options_seen = []

    class FakeTownMenu:
        def __init__(self, _presenter):
            self.calls = 0

        def draw_background(self):
            return None

        def draw_menu_panel(self, _options):
            return None

        def navigate(self, options, **kwargs):
            options_seen.append(tuple(options))
            popup_kwargs.append(kwargs)
            self.calls += 1
            if self.calls == 1:
                return options.index("Statistics")
            return len(options) - 1

    stats_calls = []
    monkeypatch.setattr(pygame_game, "TownMenuScreen", FakeTownMenu)
    game.show_gameplay_statistics = lambda background_draw_func=None: stats_calls.append(
        background_draw_func
    )

    assert game.town_menu() == "quit"
    assert stats_calls
    assert any("Statistics" in options for options in options_seen)
    assert any("Settings" in options for options in options_seen)
    assert all("Progression" not in options for options in options_seen)
    assert all("Explore Town" not in options for options in options_seen)
    assert popup_kwargs[-1]["flush_events"] is True
    assert popup_kwargs[-1]["require_key_release"] is True


def test_old_warehouse_footpad_ring_jobs_require_visible_dormant_ring(monkeypatch):
    game = pygame_game.PygameGame.__new__(pygame_game.PygameGame)
    shown_messages = []
    game.presenter = SimpleNamespace(
        show_message=lambda message, **kwargs: shown_messages.append((message, kwargs)),
    )
    game.player_char = SimpleNamespace(
        cls=SimpleNamespace(name="Rogue"),
        class_ring_awakening=class_rings.default_state(),
        inventory={"Class Ring": [items.ClassRing()]},
        storage={},
        equipment={},
    )
    popup_messages = []

    class FakePopup:
        def __init__(self, _presenter, message, show_buttons=False, **_kwargs):
            popup_messages.append(message)

        def show(self, **_kwargs):
            return True

    monkeypatch.setattr(pygame_game, "ConfirmationPopup", FakePopup)
    monkeypatch.setattr(
        pygame_game,
        "get_npc_art_manager",
        lambda: SimpleNamespace(
            get_image_path=lambda name: f"npc:{name}" if name == "Old Warehouse Guard" else ""
        ),
    )

    assert game._footpad_class_ring_rite_label() == "Loaded Game"
    assert game._footpad_class_ring_rite_available() is False
    assert game.visit_old_warehouse() is False
    assert popup_messages == []
    assert (
        shown_messages[-1][0]
        == 'A warehouse guard steps into your path.\n\n"Authorized personnel only. Please leave."'
    )
    assert shown_messages[-1][1]["title"] == "Old Warehouse Guard"
    assert shown_messages[-1][1]["image_path"] == "npc:Old Warehouse Guard"
    assert shown_messages[-1][1]["split_layout"] is True

    game.player_char.storage = {"Class Ring": [items.ClassRing()]}
    assert game._footpad_class_ring_rite_available() is True

    game.player_char.storage = {}
    game.player_char.equipment["Ring"] = items.ClassRing()
    assert game._footpad_class_ring_rite_available() is True

    game.player_char.class_ring_awakening["awakened"]["Rogue"] = True
    assert game._footpad_class_ring_rite_available() is False


def test_thieves_guild_backroom_ring_jobs_awaken_mods(monkeypatch):
    popup_messages = []
    popup_kwargs = []

    class FakePopup:
        def __init__(self, _presenter, message, show_buttons=False, **_kwargs):
            popup_messages.append(message)

        def show(self, **kwargs):
            popup_kwargs.append(kwargs)
            return True

    monkeypatch.setattr(pygame_game, "ConfirmationPopup", FakePopup)

    for class_name, expected_mod, expected_label in (
        ("Rogue", "Loaded Dice", "Loaded Game"),
        ("Seeker", "Hidden Cache", "Cartographer's Proof"),
        ("Ninja", "No-Trace Opener", "No-Trace Contract"),
        ("Arcane Trickster", "Arcane Larceny", "Impossible Theft"),
    ):
        game = pygame_game.PygameGame.__new__(pygame_game.PygameGame)
        game.presenter = SimpleNamespace()
        player = SimpleNamespace(
            cls=SimpleNamespace(name=class_name),
            class_ring_awakening=class_rings.default_state(),
            storage={},
            equipment={"Ring": items.ClassRing()},
        )
        player.awaken_class_ring = (
            lambda class_name=None, _player=player, **kwargs: class_rings.activate(
                _player,
                class_name,
                **kwargs,
            )
        )
        game.player_char = player

        assert game._run_footpad_class_ring_rite(background_draw_func=lambda: None) is True
        assert player.class_ring_awakening["awakened"][class_name] is True
        assert player.equipment["Ring"].mod == expected_mod
        assert any(expected_label in message for message in popup_messages)

    assert all(call.get("flush_events") for call in popup_kwargs)
    assert all(call.get("require_key_release") for call in popup_kwargs)


def test_thieves_guild_backroom_guidance_for_members(monkeypatch):
    shown_messages = []
    menu_calls = []
    monkeypatch.setattr(
        pygame_game,
        "get_npc_art_manager",
        lambda: SimpleNamespace(
            get_image_path=lambda name: f"npc:{name}" if name == "The Gray Broker" else ""
        ),
    )

    game = pygame_game.PygameGame.__new__(pygame_game.PygameGame)
    game.presenter = SimpleNamespace(
        render_menu=lambda prompt, options, **kwargs: menu_calls.append(
            (prompt, tuple(options), kwargs)
        )
        or 0,
        show_message=lambda message, **kwargs: shown_messages.append((message, kwargs)),
    )
    game.player_char = SimpleNamespace(
        cls=SimpleNamespace(name="Spell Stealer"),
        level=SimpleNamespace(level=1, pro_level=2),
        thieves_guild={
            "member": True,
            "trial_started": True,
            "trial_branch": "arcane",
            "starter_kit_claimed": True,
        },
        class_ring_awakening=class_rings.default_state(),
        equipment={},
        storage={},
    )

    game._visit_thieves_guild_backroom(background_draw_func=lambda: None)
    assert menu_calls[-1][0] == "Thieves Guild Backroom"
    assert menu_calls[-1][1] == ("Class Guide", "Leave")
    assert "combat Spells menu" in shown_messages[-1][0]
    assert "commits that magic to an Arcane payoff" in shown_messages[-1][0]
    assert shown_messages[-1][1]["title"] == "The Gray Broker"
    assert shown_messages[-1][1]["image_path"] == "npc:The Gray Broker"


def test_thieves_guild_membership_turn_in_grants_discount_state_and_kit(monkeypatch):
    shown_messages = []
    inventory_calls = []
    monkeypatch.setattr(
        pygame_game,
        "get_npc_art_manager",
        lambda: SimpleNamespace(get_image_path=lambda name: f"npc:{name}"),
    )

    game = pygame_game.PygameGame.__new__(pygame_game.PygameGame)
    game.presenter = SimpleNamespace(
        show_message=lambda message, **kwargs: shown_messages.append((message, kwargs)),
    )
    game.player_char = SimpleNamespace(
        cls=SimpleNamespace(name="Arcane Trickster"),
        thieves_guild={
            "member": False,
            "trial_started": True,
            "trial_branch": "arcane",
            "starter_kit_claimed": False,
        },
        special_inventory={"Thieves Guild Signet": [items.ThievesGuildSignet()]},
        inventory={},
        modify_inventory=lambda item, num=1, subtract=False, rare=False: inventory_calls.append(
            (item.name, num, subtract, rare)
        ),
    )

    game._offer_thieves_guild_membership(background_draw_func=lambda: None)

    assert game.player_char.thieves_guild["member"] is True
    assert game.player_char.thieves_guild["starter_kit_claimed"] is True
    assert ("Thieves Guild Signet", 1, True, True) in inventory_calls
    assert ("Key", 2, False, False) in inventory_calls
    assert ("Blank Scroll", 2, False, False) in inventory_calls
    assert "25% lower" in shown_messages[-1][0]


def test_thieves_guild_membership_starts_branch_trial_for_promoted_footpad(monkeypatch):
    shown_messages = []
    monkeypatch.setattr(
        pygame_game,
        "get_npc_art_manager",
        lambda: SimpleNamespace(get_image_path=lambda name: f"npc:{name}"),
    )
    game = pygame_game.PygameGame.__new__(pygame_game.PygameGame)
    game.presenter = SimpleNamespace(
        show_message=lambda message, **kwargs: shown_messages.append((message, kwargs)),
    )
    game.player_char = SimpleNamespace(
        cls=SimpleNamespace(name="Ninja"),
        thieves_guild={},
        special_inventory={},
    )

    game._offer_thieves_guild_membership(background_draw_func=lambda: None)

    assert game.player_char.thieves_guild["trial_started"] is True
    assert game.player_char.thieves_guild["trial_branch"] == "contract"
    assert "Silent Contract Trial" in shown_messages[-1][0]
    assert "false face" in shown_messages[-1][0]
    assert "narrow northward approach" in shown_messages[-1][0]
    assert "15,0,2" not in shown_messages[-1][0]
    assert "17,16,2" not in shown_messages[-1][0]


def test_thieves_guild_backroom_denial_keeps_requirements_private(monkeypatch):
    shown_messages = []
    monkeypatch.setattr(
        pygame_game,
        "get_npc_art_manager",
        lambda: SimpleNamespace(get_image_path=lambda name: f"npc:{name}"),
    )
    game = pygame_game.PygameGame.__new__(pygame_game.PygameGame)
    game.presenter = SimpleNamespace(
        show_message=lambda message, **kwargs: shown_messages.append((message, kwargs)),
    )
    game.player_char = SimpleNamespace(
        cls=SimpleNamespace(name="Warrior"),
        thieves_guild={},
        special_inventory={},
    )

    game._offer_thieves_guild_membership(background_draw_func=lambda: None)

    assert "The wares are for all but the backroom is for a select few." in shown_messages[-1][0]
    assert "Footpad" not in shown_messages[-1][0]
    assert shown_messages[-1][1]["title"] == "Mara Vale"


def test_thieves_guild_backroom_denial_from_shop_uses_shop_note(monkeypatch):
    notes = []
    shown_messages = []

    class FakeShopScreen:
        def __init__(self, *_args, **_kwargs):
            self.choices = iter(["Ask About Backroom", "Leave"])

        def set_location_portrait(self, _npc_name):
            pass

        def set_options(self, _options):
            pass

        def draw_all(self, do_flip=True):
            pass

        def navigate_options(self):
            return next(self.choices)

        def display_quest_text(self, text, *, title=""):
            notes.append((text, title))

    class FakePopup:
        def __init__(self, *_args, **_kwargs):
            pass

        def show(self, **_kwargs):
            pass

    game = pygame_game.PygameGame.__new__(pygame_game.PygameGame)
    game.presenter = SimpleNamespace(
        show_message=lambda message, **kwargs: shown_messages.append((message, kwargs))
    )
    game.player_char = SimpleNamespace(
        cls=SimpleNamespace(name="Warrior"),
        player_level=lambda: 10,
        thieves_guild={},
        special_inventory={},
    )
    game._play_location_music = lambda *_args, **_kwargs: None
    game.shop_manager = SimpleNamespace(
        _active_shopkeeper_portrait=None,
        _active_price_multiplier=1.0,
        buy_thieves_guild_goods=lambda: None,
        sell_items=lambda: None,
    )

    monkeypatch.setattr(pygame_game, "ShopScreen", FakeShopScreen)
    monkeypatch.setattr(pygame_game, "ConfirmationPopup", FakePopup)

    game.visit_thieves_guild()

    assert notes == [
        (
            "Mara Vale keeps the public ledger open and the backroom door shut.\n\n"
            '"The wares are for all but the backroom is for a select few."',
            "Mara Vale",
        )
    ]
    assert shown_messages == []


def test_town_menu_keeps_thieves_guild_under_shops_after_level_10(monkeypatch):
    game = pygame_game.PygameGame.__new__(pygame_game.PygameGame)
    game.presenter = SimpleNamespace()
    game.player_char = SimpleNamespace(
        name="Shade",
        cls=SimpleNamespace(name="Ninja"),
        class_ring_awakening=class_rings.default_state(),
        equipment={"Ring": items.ClassRing()},
        storage={},
        level=SimpleNamespace(level=10, pro_level=1),
        player_level=lambda: 10,
        town_heal=lambda: None,
        _suppress_heal_message=True,
        special_inventory={},
        quest_dict={"Side": {}},
        warp_point=True,
        quit=False,
    )
    options_seen = []

    class FakeTownMenu:
        def __init__(self, _presenter):
            self.calls = 0

        def draw_background(self):
            return None

        def draw_menu_panel(self, _options):
            return None

        def navigate(self, options, **_kwargs):
            options_seen.append(tuple(options))
            self.calls += 1
            return len(options) - 1

    class FakePopup:
        def __init__(self, *_args, **_kwargs):
            pass

        def show(self, **_kwargs):
            return True

    monkeypatch.setattr(pygame_game, "TownMenuScreen", FakeTownMenu)
    monkeypatch.setattr(pygame_game, "ConfirmationPopup", FakePopup)

    assert game.town_menu() == "quit"
    assert any("Warp Point" in options for options in options_seen)
    assert all("Thieves Guild" not in options for options in options_seen)
    assert all("Old Warehouse" not in options for options in options_seen)


def test_town_menu_keeps_base_footpad_thieves_guild_under_shops(monkeypatch):
    game = pygame_game.PygameGame.__new__(pygame_game.PygameGame)
    game.presenter = SimpleNamespace()
    game.player_char = SimpleNamespace(
        name="Shade",
        cls=SimpleNamespace(name="Footpad"),
        level=SimpleNamespace(level=10, pro_level=1),
        player_level=lambda: 10,
        class_ring_awakening=class_rings.default_state(),
        equipment={},
        storage={},
        town_heal=lambda: None,
        _suppress_heal_message=True,
        special_inventory={},
        quest_dict={"Side": {}},
        warp_point=True,
        quit=False,
    )
    options_seen = []

    class FakeTownMenu:
        def __init__(self, _presenter):
            pass

        def draw_background(self):
            return None

        def draw_menu_panel(self, _options):
            return None

        def navigate(self, options, **_kwargs):
            options_seen.append(tuple(options))
            return len(options) - 1

    class FakePopup:
        def __init__(self, *_args, **_kwargs):
            pass

        def show(self, **_kwargs):
            return True

    monkeypatch.setattr(pygame_game, "TownMenuScreen", FakeTownMenu)
    monkeypatch.setattr(pygame_game, "ConfirmationPopup", FakePopup)

    assert game.town_menu() == "quit"
    assert any("Warp Point" in options for options in options_seen)
    assert all("Thieves Guild" not in options for options in options_seen)
    assert all("Old Warehouse" not in options for options in options_seen)


def test_visit_shop_lists_magic_shop_and_thieves_guild_from_start(monkeypatch):
    game = pygame_game.PygameGame.__new__(pygame_game.PygameGame)
    calls = []
    options_seen = []
    game.presenter = SimpleNamespace()
    game.player_char = SimpleNamespace(player_level=lambda: 1)
    game._play_location_music = lambda location, **_kwargs: calls.append(("music", location))
    game.shop_manager = SimpleNamespace(
        visit_blacksmith=lambda: calls.append("blacksmith"),
        visit_alchemist=lambda: calls.append("alchemist"),
        visit_jeweler=lambda: calls.append("jeweler"),
        visit_magic_shop=lambda: calls.append("magic"),
    )
    game.visit_thieves_guild = lambda: calls.append("guild")

    class FakeShopSelection:
        def __init__(self, _presenter):
            self.calls = 0

        def navigate(self, options, **_kwargs):
            options_seen.append(tuple(options))
            self.calls += 1
            if self.calls == 1:
                return options.index("Thieves Guild")
            return len(options) - 1

    monkeypatch.setattr(pygame_game, "ShopSelectionScreen", FakeShopSelection)

    game.visit_shop()

    assert options_seen[0] == (
        "Blacksmith",
        "Alchemist",
        "Jeweler",
        "Magic Shop",
        "Thieves Guild",
        "Go Back",
    )
    assert calls == [("music", "shop"), "guild"]


def test_thieves_guild_shop_is_closed_before_level_10(monkeypatch):
    popup_messages = []
    popup_calls = []

    class FakePopup:
        def __init__(self, _presenter, message, show_buttons=False, **_kwargs):
            popup_messages.append((message, show_buttons))

        def show(self, **kwargs):
            popup_calls.append(kwargs)

    game = pygame_game.PygameGame.__new__(pygame_game.PygameGame)
    game.presenter = SimpleNamespace()
    game.player_char = SimpleNamespace(player_level=lambda: 9)
    game._play_location_music = lambda *_args, **_kwargs: (_ for _ in ()).throw(
        AssertionError("should not open")
    )
    monkeypatch.setattr(pygame_game, "ConfirmationPopup", FakePopup)

    game.visit_thieves_guild()

    assert "closed for now" in popup_messages[-1][0]
    assert popup_messages[-1][1] is False
    assert popup_calls[-1]["flush_events"] is True


def test_special_event_message_override_uses_popup_text(monkeypatch):
    game = pygame_game.PygameGame.__new__(pygame_game.PygameGame)
    game.presenter = SimpleNamespace()
    game.player_char = SimpleNamespace(location_z=0)
    game.dungeon_manager = None
    popup_messages = []
    popup_kwargs = []

    class FakePopup:
        def __init__(self, _presenter, message, show_buttons=False, **kwargs):
            popup_messages.append((message, show_buttons, kwargs))

        def show(self, **kwargs):
            popup_kwargs.append(kwargs)

    monkeypatch.setattr(pygame_game, "ConfirmationPopup", FakePopup)
    monkeypatch.setattr(
        pygame_game,
        "get_special_events",
        lambda: {"Relic Room": {"Text": ["Generic relic text."]}},
    )

    game.special_event("Relic Room", message="Triangulus rises from the altar.")

    assert popup_messages[0][0] == "Triangulus rises from the altar."
    assert popup_messages[0][1] is False
    assert popup_messages[0][2]["slow_print"] is True
    assert popup_kwargs[0]["flush_events"] is True


def test_town_menu_silently_drops_off_rookie_body_without_extra_popup(monkeypatch):
    game = pygame_game.PygameGame.__new__(pygame_game.PygameGame)
    game.presenter = SimpleNamespace()
    game.player_char = SimpleNamespace(
        town_heal=lambda: None,
        _suppress_heal_message=True,
        special_inventory={"Dead Soldier": [SimpleNamespace(name="Dead Soldier")]},
        quest_dict={"Side": {"Rookie Mistake": {"Completed": True, "Turned In": False}}},
        warp_point=False,
        quit=False,
    )
    removed_items = []

    def modify_inventory(item, subtract=False, rare=False, **_kwargs):
        removed_items.append((item.name, subtract, rare))
        game.player_char.special_inventory[item.name].pop(0)
        if not game.player_char.special_inventory[item.name]:
            del game.player_char.special_inventory[item.name]

    game.player_char.modify_inventory = modify_inventory
    popup_messages = []

    class FakePopup:
        def __init__(self, _presenter, message, show_buttons=False, **_kwargs):
            popup_messages.append(message)

        def show(self, **_kwargs):
            return True

    class FakeTownMenu:
        def __init__(self, _presenter):
            pass

        def draw_background(self):
            return None

        def draw_menu_panel(self, _options):
            return None

        def navigate(self, options, **_kwargs):
            return len(options) - 1

    monkeypatch.setattr(pygame_game, "ConfirmationPopup", FakePopup)
    monkeypatch.setattr(pygame_game, "TownMenuScreen", FakeTownMenu)

    assert game.town_menu() == "quit"
    assert removed_items == [("Dead Soldier", True, True)]
    assert "Dead Soldier" not in game.player_char.special_inventory
    assert game.player_char.quest_dict["Side"]["Rookie Mistake"]["Completed"] is True
    assert "You have completed the quest Rookie Mistake." not in popup_messages


def test_explore_town_prototype_routes_existing_location_actions(monkeypatch):
    game = pygame_game.PygameGame.__new__(pygame_game.PygameGame)
    calls = []
    game.presenter = SimpleNamespace()
    game.player_char = SimpleNamespace(location_x=5, location_y=10, location_z=0, facing="north")
    game._play_location_music = lambda location, **_kwargs: calls.append(("music", location))
    game.visit_barracks = lambda: calls.append("barracks")
    game.visit_shop = lambda: calls.append("shops")
    game.visit_inn = lambda: calls.append("inn")
    game.visit_church = lambda: calls.append("church")
    game.visit_old_warehouse = lambda **_kwargs: calls.append("warehouse")
    game.use_warp_point = lambda **_kwargs: calls.append("warp") or None

    class FakeTownNavigation:
        def __init__(self, _presenter):
            self.actions = iter(
                [
                    "Barracks",
                    "Shops",
                    "The Thirsty Dog Tavern",
                    "Church of Elysia",
                    "Old Warehouse",
                    "Warp Point",
                    "Enter Dungeon",
                ]
            )

        def draw(self):
            return None

        def navigate(self, **_kwargs):
            return next(self.actions)

    monkeypatch.setattr(pygame_game, "TownNavigationScreen", FakeTownNavigation)

    assert game.explore_town_prototype() == "dungeon"
    assert calls == [
        ("music", "town"),
        "barracks",
        "shops",
        "inn",
        "church",
        "warehouse",
        "warp",
    ]
    assert (
        game.player_char.location_x,
        game.player_char.location_y,
        game.player_char.location_z,
        game.player_char.facing,
    ) == (5, 10, 1, "east")


def test_main_can_launch_direct_town_navigation(monkeypatch):
    calls = []

    class FakeGame:
        def __init__(self, debug_mode=False):
            calls.append(("init", debug_mode))
            self.player_char = None

        def create_default_character(self, name="Hero"):
            calls.append(("default", name))
            return SimpleNamespace(name=name)

        def initialize_managers(self):
            calls.append("managers")

        def explore_town_prototype(self):
            calls.append("town")
            return "dungeon"

        def enter_dungeon(self):
            calls.append("dungeon")

        def cleanup(self):
            calls.append("cleanup")

    monkeypatch.setattr(pygame_game, "PygameGame", FakeGame)
    monkeypatch.setattr(
        pygame_game.sys,
        "argv",
        ["game_pygame.py", "--town-navigation", "--preview-name", "Town Tester"],
    )

    pygame_game.main()

    assert calls == [
        ("init", False),
        ("default", "Town Tester"),
        "managers",
        "town",
        "dungeon",
        "cleanup",
    ]
