#!/usr/bin/env python3
"""Focused coverage for the ultimate armor shop flow."""

from __future__ import annotations

from types import SimpleNamespace

import pygame

from src.ui_pygame.gui import ultimate_armor


class DummySurface:
    def __init__(self, size=(64, 24), text=None):
        self._size = size
        self.text = text

    def get_rect(self, **kwargs):
        rect = pygame.Rect(0, 0, *self._size)
        for key, value in kwargs.items():
            setattr(rect, key, value)
        return rect


class RecordingFont:
    def __init__(self):
        self.render_calls = []

    def render(self, text, _antialias, _color):
        self.render_calls.append(text)
        return DummySurface((max(8, len(text) * 8), 24), text=text)


class RecordingScreen:
    def __init__(self, size=(640, 480)):
        self._size = size
        self.blit_calls = []
        self.fill_calls = []

    def get_width(self):
        return self._size[0]

    def get_height(self):
        return self._size[1]

    def fill(self, color):
        self.fill_calls.append(color)

    def blit(self, surface, position):
        self.blit_calls.append((surface, position))


def _make_presenter():
    return SimpleNamespace(
        screen=RecordingScreen(),
        messages=[],
        menu_results=[],
        show_message=lambda message, title="": presenter.messages.append((title, message)),
        render_menu=lambda title, options: presenter.menu_results.pop(0),
    )


presenter = None


def _make_player():
    player = SimpleNamespace(
        quest_dict={"Side": {"He Ain't Heavy": {"Completed": False}}},
        inventory_added=[],
    )
    player.modify_inventory = lambda item: player.inventory_added.append(item)
    return player


def test_visit_shop_handles_quest_looted_leave_and_confirm(monkeypatch):
    global presenter
    presenter = _make_presenter()
    shop = ultimate_armor.UltimateArmorShop(presenter)
    player = _make_player()
    tile = SimpleNamespace(looted=False)

    crafted = []
    monkeypatch.setattr(shop, "_show_crafting_animation", lambda: crafted.append(True))

    class MerlinRobe:
        def __init__(self):
            self.name = "Merlin Robe"
            self.description = "Legendary cloth armor"

    class DragonHide:
        def __init__(self):
            self.name = "Dragon Hide"
            self.description = "Legendary light armor"

    class Klivanion:
        def __init__(self):
            self.name = "Klivanion"
            self.description = "Legendary medium armor"

    class Genji:
        def __init__(self):
            self.name = "Genji"
            self.description = "Legendary heavy armor"

    monkeypatch.setattr(ultimate_armor.items, "MerlinRobe", MerlinRobe)
    monkeypatch.setattr(ultimate_armor.items, "DragonHide", DragonHide)
    monkeypatch.setattr(ultimate_armor.items, "Klivanion", Klivanion)
    monkeypatch.setattr(ultimate_armor.items, "Genji", Genji)

    presenter.menu_results = [0, 0]
    shop.visit_shop(player, tile)
    assert player.quest_dict["Side"]["He Ain't Heavy"]["Completed"] is True
    assert crafted == [True]
    assert tile.looted is True
    assert player.inventory_added and player.inventory_added[0].name == "Merlin Robe"
    assert any(title == "Cloth Armor" for title, _message in presenter.messages)
    assert any("legendary armor" in message.lower() for _title, message in presenter.messages)

    presenter.messages.clear()
    shop.visit_shop(player, tile)
    assert presenter.messages[0][0] == "The Forge Master"
    assert "Please, defeat him before it's too late" in presenter.messages[0][1]

    presenter.messages.clear()
    tile.looted = False
    presenter.menu_results = [4]
    shop.visit_shop(player, tile)
    assert any(
        "Come back when you have made your decision." in message
        for _title, message in presenter.messages
    )

    presenter.messages.clear()
    presenter.menu_results = [2, 1]
    shop.visit_shop(player, tile)
    assert any(title == "Medium Armor" for title, _message in presenter.messages)
    assert not any(item.name == "Klivanion" for item in player.inventory_added[1:])


def test_crafting_animation_renders_until_time_expires(monkeypatch):
    global presenter
    presenter = _make_presenter()
    shop = ultimate_armor.UltimateArmorShop(presenter)

    fonts = [RecordingFont(), RecordingFont()]
    monkeypatch.setattr(
        "src.ui_pygame.gui.ultimate_armor.pygame.font.Font",
        lambda *_args, **_kwargs: fonts.pop(0) if fonts else RecordingFont(),
    )
    monkeypatch.setattr("src.ui_pygame.gui.ultimate_armor.pygame.display.flip", lambda: None)
    monkeypatch.setattr("src.ui_pygame.gui.ultimate_armor.pygame.event.get", lambda: [])
    monkeypatch.setattr(
        "src.ui_pygame.gui.ultimate_armor.pygame.time.Clock",
        lambda: SimpleNamespace(tick=lambda _fps: None),
    )

    values = [0.0, 0.1, 0.2, 0.4, 0.8, 1.2, 1.8, 2.4, 3.1]
    state = {"index": 0}

    def fake_time():
        idx = state["index"]
        if idx < len(values) - 1:
            state["index"] += 1
        return values[min(idx, len(values) - 1)]

    monkeypatch.setattr("src.ui_pygame.gui.ultimate_armor.time.time", fake_time)

    shop._show_crafting_animation()
    assert presenter.screen.fill_calls
    assert presenter.screen.blit_calls
