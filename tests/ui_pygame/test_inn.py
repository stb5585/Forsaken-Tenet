#!/usr/bin/env python3
"""Focused coverage for inn/tavern manager helpers."""

from __future__ import annotations

from types import SimpleNamespace

import pygame
import pytest

from src.core import main_story, opening_story
from src.ui_pygame.gui import inn


class FakePopup:
    messages = []
    show_kwargs = []

    def __init__(self, _presenter, message, show_buttons=False, **_kwargs):
        self.message = message
        self.show_buttons = show_buttons
        FakePopup.messages.append(message)

    def show(self, **kwargs):
        FakePopup.show_kwargs.append(kwargs)
        return True


def _make_player(*, level=10):
    return SimpleNamespace(
        quest_dict={"Main": {}, "Bounty": {}},
        kill_dict={},
        gold=10,
        familiar=None,
        summons={},
        player_level=lambda: level,
        level=SimpleNamespace(exp=0, exp_to_gain=10),
        max_level=lambda: False,
        modify_inventory=lambda _item: None,
        main_story=main_story.default_state(),
    )


@pytest.mark.parametrize("answer", [*opening_story.TRIANGULUS_IDENTITY_ANSWERS, "Unrecorded", None])
@pytest.mark.parametrize("choice", [0, 1, None])
def test_first_relic_aftermath_and_hooded_echo_are_one_time(monkeypatch, answer, choice):
    FakePopup.messages = []
    FakePopup.show_kwargs = []
    player = _make_player()
    player.quest_dict["Main"]["The Holy Relics"] = {"Completed": False}
    player.main_story["triangulus_identity_answer"] = answer
    presenter = _make_presenter()
    monkeypatch.setattr(
        inn.InnManager, "_load_background", lambda self: setattr(self, "background", None)
    )
    scenes = []

    class FakeStoryScene:
        def __init__(self, _presenter, title, **kwargs):
            self.title = title
            self.kwargs = kwargs
            self.beats = []
            scenes.append(self)

        def show_dialogue(self, beats):
            self.beats.extend(beats)

        def choose(self, _prompt, options, **kwargs):
            assert options == ["Who told you that?", "Keep walking"]
            assert kwargs["record_selection"] is False
            return choice

    monkeypatch.setattr("src.ui_pygame.gui.inn.StorySceneScreen", FakeStoryScene)
    monkeypatch.setattr(
        "src.ui_pygame.gui.inn.LevelUpScreen",
        lambda *_args, **_kwargs: SimpleNamespace(show_level_up=lambda *_a, **_k: None),
    )
    manager = inn.InnManager(presenter, player)

    manager._show_first_relic_aftermath()
    manager._show_first_relic_aftermath()
    assert manager._show_hooded_triangulus_response() is True
    assert manager._show_hooded_triangulus_response() is False

    assert player.main_story["first_relic_tavern_aftermath_seen"] is True
    assert player.main_story["hooded_figure_triangulus_response_seen"] is True
    assert [scene.title for scene in scenes] == [
        "The Thirsty Dog — After Triangulus",
        "Outside The Thirsty Dog",
    ]
    assert scenes[0].beats[0].speaker == "Narrator"
    assert scenes[0].kwargs["background_image"] == "tavern.jpg"
    assert "background_draw_func" not in scenes[0].kwargs
    assert any("clears an untouched cup" in beat.text for beat in scenes[0].beats)
    assert scenes[-1].beats[0].speaker == "Narrator"
    spoken = scenes[-1].beats
    expected = opening_story.TRIANGULUS_ANSWER_TEXT.get(answer)
    assert spoken[1].text == (
        f"“{expected}”" if expected else "You answered the question at the altar."
    )
    if choice == 0:
        assert spoken[2].portrait_name == inn.PLAYER_PORTRAIT_KEY
        assert spoken[-1].speaker == "Hooded Figure"
    else:
        assert len(spoken) == 2


def _make_presenter():
    pygame.font.init()
    return SimpleNamespace(
        screen=object(),
        width=900,
        height=700,
        title_font=pygame.font.Font(None, 30),
        large_font=pygame.font.Font(None, 26),
        normal_font=pygame.font.Font(None, 22),
        small_font=pygame.font.Font(None, 18),
        clock=SimpleNamespace(tick=lambda _fps: None),
        debug_mode=False,
    )


def test_visit_inn_and_patron_helpers(monkeypatch):
    FakePopup.messages = []
    FakePopup.show_kwargs = []
    player = _make_player(level=30)
    presenter = _make_presenter()
    monkeypatch.setattr(
        inn.InnManager, "_load_background", lambda self: setattr(self, "background", None)
    )
    monkeypatch.setattr("src.ui_pygame.gui.inn.ConfirmationPopup", FakePopup)
    monkeypatch.setattr(
        "src.ui_pygame.gui.inn.LevelUpScreen",
        lambda *_args, **_kwargs: SimpleNamespace(show_level_up=lambda *_a, **_k: None),
    )
    manager = inn.InnManager(presenter, player)

    calls = []
    manager.talk_to_patrons = lambda: calls.append("talk")
    manager.show_bounty_board = lambda: calls.append("bounty")

    selections = iter([0, 1, 2])
    location_portraits = []

    class FakeLocationMenuScreen:
        def __init__(self, _presenter, _title, **_kwargs):
            pass

        def set_location_portrait(self, npc_name):
            location_portraits.append(npc_name)

        def navigate(self, _options, reset_cursor=False, **_kwargs):
            return next(selections)

    monkeypatch.setattr("src.ui_pygame.gui.inn.LocationMenuScreen", FakeLocationMenuScreen)

    manager.visit_inn()

    assert calls == ["talk", "bounty"]
    assert location_portraits == []
    assert "Come back whenever you'd like." in FakePopup.messages
    assert FakePopup.show_kwargs[-1]["flush_events"] is True
    assert FakePopup.show_kwargs[-1]["require_key_release"] is True
    assert callable(FakePopup.show_kwargs[-1]["background_draw_func"])

    player.quest_dict["Main"] = {"A Bad Dream": {"Turned In": False}}
    assert manager._build_patron_list() == [
        "Oren",
        "Liora",
        "Pell",
        "Duty Soldier",
        "Hooded Figure",
        "Back",
    ]

    player.quest_dict["Main"] = {"A Bad Dream": {"Turned In": True}}
    assert "Tavin" in manager._build_patron_list()

    monkeypatch.setattr("src.ui_pygame.gui.inn.random.choice", lambda seq: seq[0])
    comment = manager._random_patron_comment("Drunkard")
    assert comment is not None


def test_talk_to_patrons_accepts_quest_or_shows_hint(monkeypatch):
    FakePopup.messages = []
    FakePopup.show_kwargs = []
    player = _make_player(level=12)
    presenter = _make_presenter()
    monkeypatch.setattr(
        inn.InnManager, "_load_background", lambda self: setattr(self, "background", None)
    )
    monkeypatch.setattr(
        "src.ui_pygame.gui.inn.LevelUpScreen",
        lambda *_args, **_kwargs: SimpleNamespace(show_level_up=lambda *_a, **_k: None),
    )
    manager = inn.InnManager(presenter, player)
    monkeypatch.setattr(manager, "_build_patron_list", lambda: ["Oren", "Back"])
    monkeypatch.setattr(manager, "_random_patron_comment", lambda patron: f"{patron} comment")

    rendered = []

    class FakeLocationMenuScreen:
        def __init__(self, _presenter, _title, **_kwargs):
            pass

        def set_option_portraits(self, _npc_names):
            return None

        def navigate(self, _options, reset_cursor=False, **_kwargs):
            if not rendered:
                return 0
            return 1

        def display_quest_text(self, text, **kwargs):
            rendered.append((text, kwargs.get("npc_name")))

    class FakeQuestManager:
        def __init__(self, _presenter, _player, quest_text_renderer, **_kwargs):
            self.quest_text_renderer = quest_text_renderer

        def check_and_offer(self, patron, show_help=False, suppress_no_quests_message=True):
            return False, False

        def get_random_help_hint(self, patron):
            return f"{patron} hint"

    monkeypatch.setattr("src.ui_pygame.gui.inn.LocationMenuScreen", FakeLocationMenuScreen)
    monkeypatch.setattr("src.ui_pygame.gui.quest_manager.QuestManager", FakeQuestManager)
    monkeypatch.setattr("src.ui_pygame.gui.inn.random.choice", lambda seq: seq[0])

    manager.talk_to_patrons()

    assert rendered == [("Barkeep hint", "Oren")]


def test_bounty_accept_turn_in_and_view(monkeypatch):
    FakePopup.messages = []
    FakePopup.show_kwargs = []
    player = _make_player(level=20)
    presenter = _make_presenter()
    presenter.game = SimpleNamespace(
        bounties={
            "Goblin Hunt": {
                "enemy": SimpleNamespace(name="Goblin"),
                "num": 2,
                "gold": 50,
                "exp": 5,
                "reward": lambda: SimpleNamespace(name="Goblin Ear"),
            }
        }
    )
    added_items = []
    player.modify_inventory = lambda item: added_items.append(item.name)
    monkeypatch.setattr(
        inn.InnManager, "_load_background", lambda self: setattr(self, "background", None)
    )
    monkeypatch.setattr("src.ui_pygame.gui.inn.ConfirmationPopup", FakePopup)
    monkeypatch.setattr(
        "src.ui_pygame.gui.inn.LevelUpScreen",
        lambda *_args, **_kwargs: SimpleNamespace(show_level_up=lambda *_a, **_k: None),
    )
    manager = inn.InnManager(presenter, player)

    class FakeLocationMenuScreen:
        def __init__(self, _presenter, title, **_kwargs):
            self.title = title

        def set_location_portrait(self, _npc_name):
            return None

        def set_option_portraits(self, _npc_names):
            return None

        def navigate_with_content(self, items, **_kwargs):
            if self.title == "Accept Bounty":
                return 0
            if self.title == "Active Bounties":
                return 0
            if self.title == "Turn In Bounty":
                assert items == [("Goblin Hunt", 0), ("Back", 0)]
                return 0
            return None

    monkeypatch.setattr("src.ui_pygame.gui.inn.LocationMenuScreen", FakeLocationMenuScreen)

    manager.accept_bounty()
    assert "Goblin Hunt" in player.quest_dict["Bounty"]
    assert "Goblin Hunt" not in presenter.game.bounties
    assert any("Bounty Accepted: Goblin Hunt" in message for message in FakePopup.messages)
    assert all(kwargs["flush_events"] is True for kwargs in FakePopup.show_kwargs)
    assert all(kwargs["require_key_release"] is True for kwargs in FakePopup.show_kwargs)

    manager.accept_bounty()
    assert "No new bounties available at this time." in FakePopup.messages

    player.quest_dict["Bounty"]["Goblin Hunt"][2] = True
    presenter.game.bounties["Goblin Hunt"] = player.quest_dict["Bounty"]["Goblin Hunt"][0]
    player.level.exp_to_gain = 0
    level_up_calls = []
    manager.level_up = lambda: level_up_calls.append(True) or setattr(
        player.level, "exp_to_gain", "MAX"
    )
    manager.turn_in_bounty(["Goblin Hunt"])
    assert player.gold == 60
    assert player.level.exp == 5
    assert added_items == ["Goblin Ear"]
    assert level_up_calls == []
    assert "Goblin Hunt" not in player.quest_dict["Bounty"]
    assert "Goblin Hunt" not in presenter.game.bounties

    player.quest_dict["Bounty"] = {}
    manager.view_active_bounties()
    assert any("No active bounties." in message for message in FakePopup.messages)


def test_bounty_accept_starts_at_zero_despite_prior_defeats(monkeypatch):
    FakePopup.messages = []
    FakePopup.show_kwargs = []
    player = _make_player(level=20)
    player.kill_dict = {"Fiend": {"Barghest": 3}}
    presenter = _make_presenter()
    presenter.game = SimpleNamespace(
        bounties={
            "Barghest Hunt": {
                "enemy": SimpleNamespace(name="Barghest"),
                "num": 3,
                "gold": 75,
                "exp": 9,
            }
        }
    )
    monkeypatch.setattr(
        inn.InnManager, "_load_background", lambda self: setattr(self, "background", None)
    )
    monkeypatch.setattr("src.ui_pygame.gui.inn.ConfirmationPopup", FakePopup)
    monkeypatch.setattr(
        "src.ui_pygame.gui.inn.LevelUpScreen",
        lambda *_args, **_kwargs: SimpleNamespace(show_level_up=lambda *_a, **_k: None),
    )
    manager = inn.InnManager(presenter, player)

    class FakeLocationMenuScreen:
        def __init__(self, _presenter, title, **_kwargs):
            self.title = title

        def set_location_portrait(self, _npc_name):
            return None

        def set_option_portraits(self, _npc_names):
            return None

        def navigate_with_content(self, items, **_kwargs):
            if self.title == "Accept Bounty":
                return 0
            return None

    monkeypatch.setattr("src.ui_pygame.gui.inn.LocationMenuScreen", FakeLocationMenuScreen)

    manager.accept_bounty()

    assert player.quest_dict["Bounty"]["Barghest Hunt"][1:] == [0, False]
    assert "Barghest Hunt" not in presenter.game.bounties
    assert all("Prior defeats counted" not in message for message in FakePopup.messages)


def test_empty_bounty_popup_uses_bounty_board_background(monkeypatch):
    FakePopup.messages = []
    FakePopup.show_kwargs = []
    player = _make_player(level=20)
    presenter = _make_presenter()
    presenter.game = SimpleNamespace(bounties={})
    monkeypatch.setattr(
        inn.InnManager, "_load_background", lambda self: setattr(self, "background", None)
    )
    monkeypatch.setattr("src.ui_pygame.gui.inn.ConfirmationPopup", FakePopup)
    monkeypatch.setattr(
        "src.ui_pygame.gui.inn.LevelUpScreen",
        lambda *_args, **_kwargs: SimpleNamespace(show_level_up=lambda *_a, **_k: None),
    )
    manager = inn.InnManager(presenter, player)
    drawn_frames = []
    board_calls = 0

    class FakeLocationMenuScreen:
        def __init__(self, _presenter, title, **_kwargs):
            self.title = title

        def navigate(self, options, reset_cursor=False, **_kwargs):
            nonlocal board_calls
            if self.title == "Bounty Board":
                board_calls += 1
                return (
                    options.index("Accept Bounty") if board_calls == 1 else options.index("Leave")
                )
            return None

        def draw_frame(self, *, do_flip=False):
            drawn_frames.append((self.title, do_flip))

    monkeypatch.setattr("src.ui_pygame.gui.inn.LocationMenuScreen", FakeLocationMenuScreen)

    manager.show_bounty_board()

    assert "No new bounties available at this time." in FakePopup.messages
    background_draw = FakePopup.show_kwargs[-1]["background_draw_func"]
    background_draw()
    assert drawn_frames == [("Bounty Board", False)]


def test_bounty_board_can_abandon_active_bounty(monkeypatch):
    FakePopup.messages = []
    FakePopup.show_kwargs = []
    player = _make_player(level=20)
    player.quest_dict["Bounty"] = {
        "Rat Hunt": [
            {"enemy": SimpleNamespace(name="Giant Rat"), "num": 3, "gold": 40, "exp": 4},
            1,
            False,
        ]
    }
    presenter = _make_presenter()
    presenter.game = SimpleNamespace(bounties={"Fresh Bounty": {"num": 1}})
    monkeypatch.setattr(
        inn.InnManager, "_load_background", lambda self: setattr(self, "background", None)
    )
    monkeypatch.setattr("src.ui_pygame.gui.inn.ConfirmationPopup", FakePopup)
    monkeypatch.setattr(
        "src.ui_pygame.gui.inn.LevelUpScreen",
        lambda *_args, **_kwargs: SimpleNamespace(show_level_up=lambda *_a, **_k: None),
    )
    manager = inn.InnManager(presenter, player)
    board_options = []
    board_calls = 0
    drawn_frames = []

    class FakeLocationMenuScreen:
        def __init__(self, _presenter, title, **_kwargs):
            self.title = title

        def set_location_portrait(self, _npc_name):
            return None

        def set_option_portraits(self, _npc_names):
            return None

        def navigate(self, options, reset_cursor=False, **_kwargs):
            nonlocal board_calls
            if self.title == "Bounty Board":
                board_options.append(list(options))
                board_calls += 1
                return (
                    options.index("Abandon Bounty") if board_calls == 1 else options.index("Leave")
                )
            if self.title == "Abandon Bounty":
                return 0
            return None

        def navigate_with_content(self, options, **_kwargs):
            if self.title == "Abandon Bounty":
                assert options == [("Rat Hunt", 0), ("Back", 0)]
                return 0
            return None

        def draw_content_selection_frame(self, options, *, do_flip=False):
            drawn_frames.append((self.title, list(options), do_flip))

    monkeypatch.setattr("src.ui_pygame.gui.inn.LocationMenuScreen", FakeLocationMenuScreen)

    manager.show_bounty_board()

    assert "Abandon Bounty" in board_options[0]
    assert "Rat Hunt" not in player.quest_dict["Bounty"]
    assert presenter.game.bounties == {"Fresh Bounty": {"num": 1}}
    assert any("abandon the Rat Hunt bounty" in message for message in FakePopup.messages)
    assert "Abandoned bounty: Rat Hunt" in FakePopup.messages
    confirmation_background = next(
        kwargs["background_draw_func"]
        for message, kwargs in zip(FakePopup.messages, FakePopup.show_kwargs)
        if message.startswith("Are you sure you want to abandon")
    )
    confirmation_background()
    assert drawn_frames[-1] == ("Abandon Bounty", [("Rat Hunt", 0), ("Back", 0)], False)


def test_abandon_bounty_reopens_selection_after_cancel(monkeypatch):
    player = _make_player(level=20)
    player.quest_dict["Bounty"] = {
        "Rat Hunt": [
            {"enemy": SimpleNamespace(name="Giant Rat"), "num": 3, "gold": 40, "exp": 4},
            1,
            False,
        ]
    }
    presenter = _make_presenter()
    monkeypatch.setattr(
        inn.InnManager, "_load_background", lambda self: setattr(self, "background", None)
    )
    manager = inn.InnManager(presenter, player)
    calls = []

    class CancelPopup:
        def __init__(self, *_args, **_kwargs):
            pass

        def show(self, **_kwargs):
            return False

    class FakeLocationMenuScreen:
        def __init__(self, _presenter, _title, **_kwargs):
            pass

        def navigate_with_content(self, options, **_kwargs):
            calls.append(list(options))
            return 0 if len(calls) == 1 else options.index(("Back", 0))

        def draw_content_selection_frame(self, _options, *, do_flip=False):
            assert not do_flip

    monkeypatch.setattr("src.ui_pygame.gui.inn.ConfirmationPopup", CancelPopup)
    monkeypatch.setattr("src.ui_pygame.gui.inn.LocationMenuScreen", FakeLocationMenuScreen)

    manager.abandon_bounty()

    assert calls == [[("Rat Hunt", 0), ("Back", 0)], [("Rat Hunt", 0), ("Back", 0)]]
    assert "Rat Hunt" in player.quest_dict["Bounty"]


def test_accept_bounty_stays_open_until_no_bounties_remain(monkeypatch):
    FakePopup.messages = []
    FakePopup.show_kwargs = []
    player = _make_player(level=20)
    presenter = _make_presenter()
    presenter.game = SimpleNamespace(
        bounties={
            "Goblin Hunt": {
                "enemy": SimpleNamespace(name="Goblin"),
                "num": 2,
                "gold": 50,
                "exp": 5,
            },
            "Rat Hunt": {"enemy": SimpleNamespace(name="Rat"), "num": 3, "gold": 40, "exp": 4},
        }
    )
    monkeypatch.setattr(
        inn.InnManager, "_load_background", lambda self: setattr(self, "background", None)
    )
    monkeypatch.setattr("src.ui_pygame.gui.inn.ConfirmationPopup", FakePopup)
    monkeypatch.setattr(
        "src.ui_pygame.gui.inn.LevelUpScreen",
        lambda *_args, **_kwargs: SimpleNamespace(show_level_up=lambda *_a, **_k: None),
    )
    manager = inn.InnManager(presenter, player)
    menu_titles = []

    class FakeLocationMenuScreen:
        def __init__(self, _presenter, title, **_kwargs):
            self.title = title

        def set_location_portrait(self, _npc_name):
            return None

        def set_option_portraits(self, _npc_names):
            return None

        def navigate_with_content(self, items, **_kwargs):
            menu_titles.append((self.title, tuple(name for name, _value in items)))
            return 0

    monkeypatch.setattr("src.ui_pygame.gui.inn.LocationMenuScreen", FakeLocationMenuScreen)

    manager.accept_bounty()

    assert set(player.quest_dict["Bounty"]) == {"Goblin Hunt", "Rat Hunt"}
    assert presenter.game.bounties == {}
    assert menu_titles == [
        ("Accept Bounty", ("Goblin Hunt", "Rat Hunt", "Back")),
        ("Accept Bounty", ("Rat Hunt", "Back")),
    ]
    assert any(
        "No new bounties available at this time." in message for message in FakePopup.messages
    )


def test_joffrey_leaves_once_after_route_review_and_hexagonum(monkeypatch):
    from src.core import quest_progress

    manager = object.__new__(inn.InnManager)
    manager.player_char = player = _make_player(level=45)
    manager.presenter = object()
    scenes = []

    class Scene:
        def __init__(self, _presenter, title, **_kwargs):
            scenes.append(title)

        def show_dialogue(self, beats):
            assert {"Liora", "Joffrey", "Tavin"} <= {beat.speaker for beat in beats}

    monkeypatch.setattr(inn, "StorySceneScreen", Scene)
    player.main_story.update(
        hexagonum_report_seen=True,
        joffrey_tavern_scene_seen=True,
        joffrey_patrol_briefing_seen=True,
    )
    manager._show_joffrey_departure()
    assert not scenes
    assert not quest_progress.can_offer_authored_quest(player, "A Bad Dream")
    player.main_story["joffrey_route_review_seen"] = True
    manager._show_joffrey_departure()
    manager._show_joffrey_departure()
    assert len(scenes) == 1
    assert quest_progress.can_offer_authored_quest(player, "A Bad Dream")
    assert "Joffrey" not in manager._build_patron_list()
    assert "Duty Soldier" in manager._build_patron_list()


def test_late_act_two_scenes_remember_choices_across_visits(monkeypatch):
    manager = object.__new__(inn.InnManager)
    manager.player_char = player = _make_player(level=65)
    manager.presenter = object()
    player.main_story.update(joffrey_found=True, liora_reply="map")
    player.special_inventory = dict.fromkeys(("Joffrey's Letter", "Polaris", "Infinitas"))
    titles = []

    class Scene:
        def __init__(self, _presenter, title, **kwargs):
            titles.append(title)

        def show_dialogue(self, beats):
            assert beats

        def choose(self, prompt, options, **kwargs):
            return 1

    monkeypatch.setattr(inn, "StorySceneScreen", Scene)
    for _ in range(4):
        manager._show_late_relic_scene()
        main_story.ensure_state(player)
    assert len(titles) == 3
    assert player.main_story["liora_letter_read"]
    assert player.main_story["polaris_advice"] == "refuse"
    assert player.main_story["infinitas_return"] == "help"


def test_closing_wage_book_preserves_the_missing_patrons_quest_access(monkeypatch):
    manager = object.__new__(inn.InnManager)
    manager.presenter = object()
    player = manager.player_char = _make_player(level=65)
    player.main_story.update(infinitas_return="help", joffrey_found=True)
    player.quest_dict["Main"]["A Bad Dream"] = {"Turned In": True}
    scenes = []
    monkeypatch.setattr(
        inn,
        "StorySceneScreen",
        lambda *args, **kwargs: SimpleNamespace(show_dialogue=scenes.append),
    )
    manager._show_late_relic_scene()
    assert not scenes
    player.quest_dict["Main"]["The Holy Relics"] = {"Turned In": True}
    manager._show_late_relic_scene()
    manager._show_late_relic_scene()
    assert len(scenes) == 1
    options = manager._build_patron_list()
    assert "Liora" in options and "Tavin" not in options
    assert manager.PATRON_ROLES["Tavin’s notes"] == "Busboy"
    assert "Tavin’s notes" in options
