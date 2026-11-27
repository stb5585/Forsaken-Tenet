#!/usr/bin/env python3
"""Focused coverage for barracks manager helpers."""

from __future__ import annotations

from types import SimpleNamespace

import pygame

from src.core import items, main_story
from src.core.classes import class_rings, grandmaster
from src.ui_pygame.gui import barracks


class FakePopup:
    messages = []
    calls = []

    def __init__(self, _presenter, message, show_buttons=False, **_kwargs):
        self.message = message
        FakePopup.messages.append(message)

    def show(self, **_kwargs):
        FakePopup.calls.append(_kwargs)
        return True


class FakeQuantityPopup:
    responses = []
    created = []

    def __init__(
        self,
        _presenter,
        _name,
        unit_cost=0,
        max_quantity=1,
        action="store",
        default_quantity=0,
    ):
        self.max_quantity = max_quantity
        self.action = action
        self.default_quantity = default_quantity
        self.created.append((action, max_quantity, default_quantity))

    def show(self, **_kwargs):
        return FakeQuantityPopup.responses.pop(0)


def _make_presenter():
    pygame.font.init()
    return SimpleNamespace(
        screen=SimpleNamespace(copy=lambda: "screen-copy", blit=lambda *_a, **_k: None),
        width=900,
        height=700,
        title_font=pygame.font.Font(None, 30),
        large_font=pygame.font.Font(None, 26),
        normal_font=pygame.font.Font(None, 22),
        small_font=pygame.font.Font(None, 18),
        clock=SimpleNamespace(tick=lambda _fps: None),
        debug_mode=False,
    )


def _make_player():
    inventory_calls = []

    def modify_inventory(item, num=1, storage=False, subtract=False, rare=False):
        inventory_calls.append((item.name, num, storage, subtract, rare))

    return SimpleNamespace(
        cls=SimpleNamespace(name="Warrior"),
        equipment={"Ring": SimpleNamespace(name="No Ring")},
        inventory={},
        storage={},
        special_inventory={},
        modify_inventory=modify_inventory,
        inventory_calls=inventory_calls,
    )


def test_opening_ledgers_use_clean_barracks_background(monkeypatch):
    scenes = []

    class FakeStoryScene:
        def __init__(self, _presenter, title, **kwargs):
            self.title = title
            self.kwargs = kwargs
            self.beats = []
            scenes.append(self)

        def show_dialogue(self, beats, **_kwargs):
            self.beats.extend(beats)

        def choose(self, _prompt, _options, **_kwargs):
            return 0

    player = _make_player()
    player.main_story = main_story.default_state()
    manager = barracks.BarracksManager.__new__(barracks.BarracksManager)
    manager.presenter = _make_presenter()
    manager.player_char = player
    monkeypatch.setattr(barracks, "StorySceneScreen", FakeStoryScene)

    manager._review_opening_ledgers()

    assert scenes[0].title == "Barracks — Patrol Ledgers"
    assert scenes[0].kwargs["background_image"] == "barracks.jpg"
    assert player.main_story["opening_ledger_seen"] is True


def test_visit_barracks_routes_and_special_event(monkeypatch):
    FakePopup.messages = []
    FakePopup.calls = []
    player = _make_player()
    player.special_inventory = {"Brass Key": [SimpleNamespace(name="Brass Key")]}
    presenter = _make_presenter()
    monkeypatch.setattr(
        barracks.BarracksManager, "_load_background", lambda self: setattr(self, "background", None)
    )
    monkeypatch.setattr("src.ui_pygame.gui.barracks.ConfirmationPopup", FakePopup)
    monkeypatch.setattr(
        "src.ui_pygame.gui.barracks.get_special_events",
        lambda: {"Joffrey's Key": {"Text": ["Line one", "Line two"]}},
    )
    monkeypatch.setattr(barracks.items, "BrassKey", lambda: SimpleNamespace(name="Brass Key"))
    monkeypatch.setattr(
        barracks.items, "JoffreysLetter", lambda: SimpleNamespace(name="Joffrey's Letter")
    )
    monkeypatch.setattr(
        barracks.items, "GreatHealthPotion", lambda: SimpleNamespace(name="Great Health Potion")
    )

    manager = barracks.BarracksManager(presenter, player)
    storage_calls = []
    manager.manage_storage = lambda: storage_calls.append(True)

    class FakeQuestManager:
        def __init__(self, _presenter, _player, quest_text_renderer, **_kwargs):
            self.quest_text_renderer = quest_text_renderer

        def check_and_offer(self, giver):
            self.quest_text_renderer(f"{giver} quest")

    nav_values = iter([0, 1, 2])
    rendered = []
    portraits = []

    class FakeLocationMenuScreen:
        def __init__(self, _presenter, _title, **kwargs):
            self.options_list = []
            assert kwargs["background_image"] == "barracks.jpg"

        def draw_all(self):
            return None

        def set_location_portrait(self, npc_name):
            portraits.append(npc_name)

        def navigate(self, _options, reset_cursor=False, **_kwargs):
            return next(nav_values)

        def display_quest_text(self, text, **kwargs):
            rendered.append((text, kwargs.get("npc_name")))

    monkeypatch.setattr("src.ui_pygame.gui.barracks.LocationMenuScreen", FakeLocationMenuScreen)
    monkeypatch.setattr("src.ui_pygame.gui.quest_manager.QuestManager", FakeQuestManager)

    manager.visit_barracks()

    assert portraits == ["Caedmon Varr"]
    assert rendered == [("Sergeant quest", "Caedmon Varr")]
    assert storage_calls == [True]
    assert any("Joffrey's Letter" in message for message in FakePopup.messages)
    assert any(call.get("flush_events") for call in FakePopup.calls)
    assert all(call.get("background_draw_func") for call in FakePopup.calls)
    assert ("Brass Key", 1, False, True, True) in player.inventory_calls
    assert ("Joffrey's Letter", 1, False, False, True) in player.inventory_calls
    assert ("Great Health Potion", 5, False, False, False) in player.inventory_calls


def test_milestone_storage_rewards_are_deposited_once(monkeypatch):
    FakePopup.messages = []
    FakePopup.calls = []
    player = _make_player()
    player.quest_dict = {
        "Bounty": {},
        "Main": {
            "The Butcher": {"Turned In": True},
            "A Bad Dream": {"Turned In": False},
        },
        "Side": {
            "Rookie Mistake": {"Turned In": True},
        },
    }
    presenter = _make_presenter()
    monkeypatch.setattr(
        barracks.BarracksManager, "_load_background", lambda self: setattr(self, "background", None)
    )
    monkeypatch.setattr("src.ui_pygame.gui.barracks.ConfirmationPopup", FakePopup)
    manager = barracks.BarracksManager(presenter, player)

    granted = manager._grant_milestone_storage_rewards()
    second_granted = manager._grant_milestone_storage_rewards()

    assert granted == [
        "2x Health Potion",
        "1x Mana Potion",
        "3x Health Potion",
        "1x Mana Potion",
    ]
    assert second_granted == []
    assert player.quest_dict["Milestone Storage Rewards"] == {
        "Rookie Mistake": True,
        "The Butcher": True,
    }
    assert player.storage.keys() == {"Health Potion", "Mana Potion"}
    assert len(player.storage["Health Potion"]) == 5
    assert len(player.storage["Mana Potion"]) == 2
    assert player.inventory_calls == []
    assert any("milestone supplies" in message for message in FakePopup.messages)


def test_grandmaster_hall_requires_equipped_or_stored_class_ring(monkeypatch):
    player = _make_player()
    player.cls = SimpleNamespace(name="Grandmaster of Arms")
    player.inventory = {"Class Ring": [items.ClassRing()]}
    presenter = _make_presenter()
    monkeypatch.setattr(
        barracks.BarracksManager, "_load_background", lambda self: setattr(self, "background", None)
    )

    manager = barracks.BarracksManager(presenter, player)
    assert manager._grandmaster_hall_available() is False

    player.storage = {"Class Ring": [items.ClassRing()]}
    assert manager._grandmaster_hall_available() is True

    player.storage = {}
    player.equipment["Ring"] = items.ClassRing()
    assert manager._grandmaster_hall_available() is True


def test_grandmaster_hall_binds_after_successful_gauntlet(monkeypatch):
    FakePopup.messages = []
    player = _make_player()
    player.cls = SimpleNamespace(name="Grandmaster of Arms")
    player.equipment = {
        "Ring": items.ClassRing(),
        "Weapon": SimpleNamespace(subtyp="Sword"),
    }
    player.grandmaster_discipline = grandmaster.default_state()
    presenter = _make_presenter()
    monkeypatch.setattr(
        barracks.BarracksManager, "_load_background", lambda self: setattr(self, "background", None)
    )
    monkeypatch.setattr("src.ui_pygame.gui.barracks.ConfirmationPopup", FakePopup)

    manager = barracks.BarracksManager(presenter, player)
    monkeypatch.setattr(manager, "_choose_grandmaster_weapon", lambda rebind=False: "Sword")
    monkeypatch.setattr(
        manager, "_run_grandmaster_gauntlet", lambda weapon_type, rebind=False: True
    )

    assert manager.visit_grandmaster_secret_hall() is True
    assert player.grandmaster_discipline["activated"] is True
    assert player.grandmaster_discipline["bound_weapon"] == "Sword"
    assert player.equipment["Ring"].mod == "Sword Discipline x2"
    assert any("awakens to Sword Discipline" in message for message in FakePopup.messages)


def test_berserker_duel_requires_visible_dormant_class_ring(monkeypatch):
    player = _make_player()
    player.cls = SimpleNamespace(name="Berserker")
    player.class_ring_awakening = class_rings.default_state()
    player.inventory = {"Class Ring": [items.ClassRing()]}
    presenter = _make_presenter()
    monkeypatch.setattr(
        barracks.BarracksManager, "_load_background", lambda self: setattr(self, "background", None)
    )

    manager = barracks.BarracksManager(presenter, player)
    assert manager._berserker_duel_available() is False

    player.storage = {"Class Ring": [items.ClassRing()]}
    assert manager._berserker_duel_available() is True

    player.storage = {}
    player.equipment["Ring"] = items.ClassRing()
    assert manager._berserker_duel_available() is True

    player.class_ring_awakening["awakened"]["Berserker"] = True
    assert manager._berserker_duel_available() is False


def test_berserker_duel_awakes_ring_after_successful_bout(monkeypatch):
    FakePopup.messages = []
    player = _make_player()
    player.cls = SimpleNamespace(name="Berserker")
    player.class_ring_awakening = class_rings.default_state()
    player.equipment["Ring"] = items.ClassRing()
    player.awaken_class_ring = lambda class_name=None, **kwargs: class_rings.activate(
        player, class_name, **kwargs
    )
    presenter = _make_presenter()
    monkeypatch.setattr(
        barracks.BarracksManager, "_load_background", lambda self: setattr(self, "background", None)
    )
    monkeypatch.setattr("src.ui_pygame.gui.barracks.ConfirmationPopup", FakePopup)

    manager = barracks.BarracksManager(presenter, player)
    monkeypatch.setattr(manager, "_run_berserker_duel", lambda: True)

    assert manager.visit_berserker_no_healing_duel() is True
    assert player.class_ring_awakening["awakened"]["Berserker"] is True
    assert player.equipment["Ring"].mod == "Bloodied Crits"
    assert any("No Healing Duel" in message for message in FakePopup.messages)


def test_legacy_barracks_trials_require_visible_dormant_class_ring(monkeypatch):
    player = _make_player()
    player.cls = SimpleNamespace(name="Dragoon")
    player.class_ring_awakening = class_rings.default_state()
    player.inventory = {"Class Ring": [items.ClassRing()]}
    presenter = _make_presenter()
    monkeypatch.setattr(
        barracks.BarracksManager, "_load_background", lambda self: setattr(self, "background", None)
    )

    manager = barracks.BarracksManager(presenter, player)
    assert manager._legacy_barracks_trial_label() == "Guard The Fall"
    assert manager._legacy_barracks_trial_available() is False

    player.storage = {"Class Ring": [items.ClassRing()]}
    assert manager._legacy_barracks_trial_available() is True

    player.storage = {}
    player.equipment["Ring"] = items.ClassRing()
    assert manager._legacy_barracks_trial_available() is True

    player.class_ring_awakening["awakened"]["Dragoon"] = True
    assert manager._legacy_barracks_trial_available() is False


def test_dragoon_and_stalwart_trials_awaken_ring_after_success(monkeypatch):
    FakePopup.messages = []
    presenter = _make_presenter()
    monkeypatch.setattr(
        barracks.BarracksManager, "_load_background", lambda self: setattr(self, "background", None)
    )
    monkeypatch.setattr("src.ui_pygame.gui.barracks.ConfirmationPopup", FakePopup)

    for class_name, expected_mod, expected_label in (
        ("Dragoon", "Aerial Supremacy", "Guard The Fall"),
        ("Stalwart Defender", "Guard Meter", "Siege Trial"),
    ):
        player = _make_player()
        player.cls = SimpleNamespace(name=class_name)
        player.class_ring_awakening = class_rings.default_state()
        player.equipment["Ring"] = items.ClassRing()
        player.awaken_class_ring = (
            lambda class_name=None, _player=player, **kwargs: class_rings.activate(
                _player,
                class_name,
                **kwargs,
            )
        )
        manager = barracks.BarracksManager(presenter, player)
        monkeypatch.setattr(manager, "_run_legacy_barracks_trial", lambda: True)

        assert manager.visit_legacy_barracks_class_ring_trial() is True
        assert player.class_ring_awakening["awakened"][class_name] is True
        assert player.equipment["Ring"].mod == expected_mod
        assert any(expected_label in message for message in FakePopup.messages)


def test_manage_storage_store_and_retrieve(monkeypatch):
    FakePopup.messages = []
    FakePopup.calls = []
    FakeQuantityPopup.responses = [2, 1]
    FakeQuantityPopup.created = []
    player = _make_player()
    player.inventory = {
        "Potion": [
            SimpleNamespace(name="Potion"),
            SimpleNamespace(name="Potion"),
            SimpleNamespace(name="Potion"),
        ]
    }
    player.storage = {"Elixir": [SimpleNamespace(name="Elixir"), SimpleNamespace(name="Elixir")]}
    presenter = _make_presenter()
    monkeypatch.setattr(
        barracks.BarracksManager, "_load_background", lambda self: setattr(self, "background", None)
    )
    monkeypatch.setattr("src.ui_pygame.gui.barracks.ConfirmationPopup", FakePopup)
    monkeypatch.setattr("src.ui_pygame.gui.confirmation_popup.QuantityPopup", FakeQuantityPopup)
    manager = barracks.BarracksManager(presenter, player)

    nav_values = iter([0, 1, 2, None])
    content_values = iter([0, 1, 0, 1])

    class FakeLocationMenuScreen:
        def __init__(self, _presenter, _title):
            pass

        def set_location_portrait(self, _npc_name):
            return None

        def navigate(self, _options, reset_cursor=False, **_kwargs):
            return next(nav_values)

        def navigate_with_content(self, _items, **_kwargs):
            return next(content_values)

    monkeypatch.setattr("src.ui_pygame.gui.barracks.LocationMenuScreen", FakeLocationMenuScreen)

    store_calls = []
    retrieve_calls = []
    original_store = manager.store_items
    original_retrieve = manager.retrieve_items
    manager.store_items = lambda: store_calls.append(True) or original_store()
    manager.retrieve_items = lambda: retrieve_calls.append(True) or original_retrieve()

    manager.manage_storage()

    assert store_calls == [True]
    assert retrieve_calls == [True]
    assert ("Potion", 2, True, True, False) in player.inventory_calls
    assert ("Elixir", 1, True, False, False) in player.inventory_calls
    assert any("Stored 2x Potion" in message for message in FakePopup.messages)
    assert any("Retrieved 1x Elixir" in message for message in FakePopup.messages)
    assert ("retrieve", 2, 2) in FakeQuantityPopup.created
    assert any(call.get("flush_events") for call in FakePopup.calls)


def test_store_and_retrieve_empty_states(monkeypatch):
    FakePopup.messages = []
    FakePopup.calls = []
    player = _make_player()
    presenter = _make_presenter()
    monkeypatch.setattr(
        barracks.BarracksManager, "_load_background", lambda self: setattr(self, "background", None)
    )
    monkeypatch.setattr("src.ui_pygame.gui.barracks.ConfirmationPopup", FakePopup)
    manager = barracks.BarracksManager(presenter, player)

    manager.store_items()
    manager.retrieve_items()

    assert "You have no items to store." in FakePopup.messages
    assert "Your storage is empty." in FakePopup.messages
    assert any(call.get("flush_events") for call in FakePopup.calls)


def test_relic_reports_remember_the_order_and_deliver_once(monkeypatch):
    scenes = []

    class Scene:
        def __init__(self, presenter, title, **kwargs):
            scenes.append(title)

        def show_dialogue(self, beats):
            assert beats

        def choose(self, prompt, answers, **kwargs):
            return 2

    monkeypatch.setattr(barracks, "StorySceneScreen", Scene)
    manager = object.__new__(barracks.BarracksManager)
    manager.presenter = object()
    manager.player_char = SimpleNamespace(special_inventory={"Quadrata": [], "Hexagonum": []})
    story = barracks.main_story.default_state()
    for _ in range(4):
        manager._review_relic_routes(story)
        story = barracks.main_story.normalize_state(story)
    assert story["route_order"] == "SignOut"
    assert len(scenes) == len(set(scenes)) == 3
