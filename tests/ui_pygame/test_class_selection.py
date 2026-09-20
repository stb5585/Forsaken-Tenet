#!/usr/bin/env python3
"""Focused coverage for the pygame class selection screen."""

from __future__ import annotations

from types import SimpleNamespace

import pygame
import pytest

from src.ui_pygame.gui import class_selection


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
    def __init__(self, height=20):
        self.render_calls = []
        self._height = height

    def render(self, text, _aa, _color):
        self.render_calls.append(text)
        return DummySurface((max(8, len(text) * 8), self._height), text=text)

    def size(self, text):
        return (max(8, len(text) * 8), self._height)


class RecordingScreen:
    def __init__(self):
        self.fill_calls = []
        self.blit_calls = []

    def fill(self, color):
        self.fill_calls.append(color)

    def blit(self, surface, pos):
        self.blit_calls.append((surface, pos))


def _make_presenter():
    return SimpleNamespace(
        screen=RecordingScreen(),
        width=1000,
        height=800,
        title_font=RecordingFont(30),
        normal_font=RecordingFont(22),
        small_font=RecordingFont(18),
        clock=SimpleNamespace(tick=lambda _fps: None),
    )


class WarriorClass:
    def __init__(self):
        self.description = "A front-line fighter.\nStrong and direct."
        self.str_plus = 3
        self.int_plus = 0
        self.wis_plus = 1
        self.con_plus = 2
        self.cha_plus = -1
        self.dex_plus = 1
        self.att_plus = 4
        self.def_plus = 3
        self.magic_plus = 0
        self.magic_def_plus = 1
        self.restrictions = {"Weapon": ["Sword", "Axe"], "Armor": ["Heavy"]}


class MageClass:
    def __init__(self):
        self.description = "A scholar of arcane arts."
        self.str_plus = 0
        self.int_plus = 4
        self.wis_plus = 3
        self.con_plus = 0
        self.cha_plus = 1
        self.dex_plus = 1
        self.att_plus = 0
        self.def_plus = 0
        self.magic_plus = 5
        self.magic_def_plus = 4
        self.restrictions = {"Weapon": ["Staff"]}


def _make_race():
    return SimpleNamespace(
        strength=11,
        intel=12,
        wisdom=13,
        con=14,
        charisma=15,
        dex=16,
        base_attack=2,
        base_defense=3,
        base_magic=4,
        base_magic_def=5,
        cls_res={"Base": ["Warrior", "Mage"], "First": ["Paladin", "Warlock", "Conjurer"]},
    )


def test_class_selection_draw_and_set_classes(monkeypatch):
    presenter = _make_presenter()
    screen = class_selection.ClassSelectionScreen(presenter)
    draw_rect_calls = []
    flip_calls = []
    monkeypatch.setattr(
        "src.ui_pygame.gui.class_selection.pygame.draw.rect",
        lambda *_a, **_k: draw_rect_calls.append(True),
    )
    monkeypatch.setattr(
        "src.ui_pygame.gui.class_selection.pygame.display.flip", lambda: flip_calls.append(True)
    )

    screen.set_classes(
        "Elf",
        _make_race(),
        {
            "Warrior": {"class": WarriorClass},
            "Mage": {"class": MageClass},
            "Healer": {"class": None},
        },
    )

    assert screen.available_classes == ["Warrior", "Mage"]
    assert screen.class_data["Warrior"]["stats"]["strength"]["base"] == 14
    assert screen.class_data["Warrior"]["promotions"] == ["Paladin"]
    assert screen.class_data["Mage"]["promotions"] == ["Warlock", "Conjurer"]

    screen.draw_header()
    screen.draw_class_details()
    screen.draw_class_list()
    screen.draw_all()

    assert presenter.normal_font.render_calls
    assert "Select the class for your Elf character" in presenter.normal_font.render_calls
    assert "Starting Stats" in presenter.small_font.render_calls
    assert "Equipment Restrictions" in presenter.small_font.render_calls
    assert "Available Promotions" in presenter.small_font.render_calls
    assert draw_rect_calls
    assert flip_calls

    screen.available_classes = []
    screen.draw_class_list()
    assert "No classes available" in presenter.normal_font.render_calls


def test_class_selection_options_expand_to_native_touch_targets():
    presenter = _make_presenter()
    presenter.width, presenter.height = (1920, 1080)
    screen = class_selection.ClassSelectionScreen(presenter)

    assert all(rect.height >= 72 for rect in screen.option_rects(["Warrior", "Mage"]))


def test_class_selection_navigation_and_quit(monkeypatch):
    presenter = _make_presenter()
    screen = class_selection.ClassSelectionScreen(presenter)
    monkeypatch.setattr(screen, "draw_all", lambda: None)

    race = _make_race()
    classes = {"Warrior": {"class": WarriorClass}, "Mage": {"class": MageClass}}

    event_batches = iter(
        [
            [SimpleNamespace(type=pygame.KEYDOWN, key=pygame.K_DOWN)],
            [SimpleNamespace(type=pygame.KEYDOWN, key=pygame.K_RETURN)],
        ]
    )
    monkeypatch.setattr(
        "src.ui_pygame.gui.class_selection.pygame.event.get", lambda: next(event_batches, [])
    )
    assert screen.navigate("Elf", race, classes) == "Mage"

    event_batches = iter(
        [
            [SimpleNamespace(type=pygame.KEYDOWN, key=pygame.K_ESCAPE)],
        ]
    )
    monkeypatch.setattr(
        "src.ui_pygame.gui.class_selection.pygame.event.get", lambda: next(event_batches, [])
    )
    assert screen.navigate("Elf", race, classes) is None

    clear_calls = []
    pressed_states = iter([[1], [1], [], []])
    monkeypatch.setattr(
        "src.ui_pygame.gui.input_guards.pygame.key.get_pressed", lambda: next(pressed_states, [])
    )
    event_batches = iter(
        [
            [SimpleNamespace(type=pygame.KEYDOWN, key=pygame.K_RETURN)],
            [SimpleNamespace(type=pygame.KEYUP, key=pygame.K_RETURN)],
            [SimpleNamespace(type=pygame.KEYDOWN, key=pygame.K_DOWN)],
            [SimpleNamespace(type=pygame.KEYDOWN, key=pygame.K_RETURN)],
        ]
    )
    monkeypatch.setattr(
        "src.ui_pygame.gui.class_selection.pygame.event.get", lambda: next(event_batches, [])
    )
    monkeypatch.setattr(
        "src.ui_pygame.gui.class_selection.pygame.event.clear", lambda: clear_calls.append(True)
    )
    assert (
        screen.navigate("Elf", race, classes, flush_events=True, require_key_release=True) == "Mage"
    )
    assert clear_calls == [True]

    screen.current_selection = 0
    monkeypatch.setattr("src.ui_pygame.gui.input_guards.pygame.key.get_pressed", lambda: [])
    event_batches = iter([[SimpleNamespace(type=pygame.KEYDOWN, key=pygame.K_RETURN)]])
    monkeypatch.setattr(
        "src.ui_pygame.gui.class_selection.pygame.event.get", lambda: next(event_batches, [])
    )
    assert (
        screen.navigate("Elf", race, classes, flush_events=True, require_key_release=True)
        == "Warrior"
    )

    screen.set_classes("Elf", race, classes)
    click_pos = screen.option_rects()[1].center
    event_batches = iter([[SimpleNamespace(type=pygame.MOUSEBUTTONDOWN, button=1, pos=click_pos)]])
    monkeypatch.setattr(
        "src.ui_pygame.gui.class_selection.pygame.event.get", lambda: next(event_batches, [])
    )
    assert screen.navigate("Elf", race, classes) == "Mage"

    monkeypatch.setattr(
        screen, "set_classes", lambda *_args: setattr(screen, "available_classes", [])
    )
    assert screen.navigate("Elf", race, classes) is None

    quit_calls = []
    monkeypatch.setattr(
        screen, "set_classes", lambda *_args: setattr(screen, "available_classes", ["Warrior"])
    )
    monkeypatch.setattr(
        "src.ui_pygame.gui.class_selection.pygame.quit", lambda: quit_calls.append(True)
    )
    monkeypatch.setattr("sys.exit", lambda: (_ for _ in ()).throw(SystemExit()))
    monkeypatch.setattr(
        "src.ui_pygame.gui.class_selection.pygame.event.get",
        lambda: [SimpleNamespace(type=pygame.QUIT)],
    )

    with pytest.raises(SystemExit):
        screen.navigate("Elf", race, classes)
    assert quit_calls
