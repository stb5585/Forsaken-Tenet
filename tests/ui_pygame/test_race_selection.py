#!/usr/bin/env python3
"""Focused coverage for the pygame race-selection screen."""

from __future__ import annotations

from types import SimpleNamespace

import pygame
import pytest

from src.ui_pygame.gui import race_selection


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


class ElfRace:
    def __init__(self):
        self.description = "Graceful and wise.\nKeen senses help in battle."
        self.strength = 8
        self.intel = 14
        self.wisdom = 13
        self.con = 9
        self.charisma = 12
        self.dex = 15
        self.base_attack = 2
        self.base_defense = 3
        self.base_magic = 5
        self.base_magic_def = 4
        self.resistance = {"Fire": 0.1, "Ice": 0.2, "Holy": 0.15}
        self.cls_res = {"Base": ["Mage", "Pathfinder"]}
        self.virtue = SimpleNamespace(name="Grace", description="Moves lightly through the world.")
        self.sin = SimpleNamespace(name="Pride", description="Can become too certain of success.")


class HumanRace:
    def __init__(self):
        self.description = "Adaptable and bold."
        self.strength = 10
        self.intel = 10
        self.wisdom = 10
        self.con = 10
        self.charisma = 10
        self.dex = 10
        self.base_attack = 1
        self.base_defense = 1
        self.base_magic = 1
        self.base_magic_def = 1
        self.resistance = {}
        self.cls_res = {"Base": ["Warrior"]}


def test_race_selection_draw_and_set_races(monkeypatch):
    presenter = _make_presenter()
    screen = race_selection.RaceSelectionScreen(presenter)
    draw_rect_calls = []
    flip_calls = []
    monkeypatch.setattr(
        "src.ui_pygame.gui.race_selection.pygame.draw.rect",
        lambda *_a, **_k: draw_rect_calls.append(True),
    )
    monkeypatch.setattr(
        "src.ui_pygame.gui.race_selection.pygame.display.flip", lambda: flip_calls.append(True)
    )

    screen.set_races({"Elf": ElfRace, "Human": HumanRace})

    assert screen.races == ["Elf", "Human"]
    assert screen.race_data["Elf"]["stats"]["mana"] == 28
    assert screen.race_data["Elf"]["resistance"]["fire"] == 10.0
    assert screen.race_data["Elf"]["available_classes"] == ["Mage", "Pathfinder"]
    assert screen.race_data["Elf"]["virtue"]["name"] == "Grace"
    assert screen.race_data["Elf"]["sin"]["name"] == "Pride"

    screen.draw_header()
    screen.draw_race_details()
    screen.draw_race_list()
    screen.draw_all()

    assert "Select the race for your character" in presenter.normal_font.render_calls
    assert "Base Stats" in presenter.small_font.render_calls
    assert "Resistances" in presenter.small_font.render_calls
    assert "Available Base Classes" in presenter.small_font.render_calls
    assert "Virtue / Sin" in presenter.small_font.render_calls
    assert draw_rect_calls
    assert flip_calls

    screen.races = []
    screen.draw_race_list()
    assert "No races available" in presenter.normal_font.render_calls


def test_race_selection_options_expand_to_native_touch_targets():
    presenter = _make_presenter()
    presenter.width, presenter.height = (1920, 1080)
    screen = race_selection.RaceSelectionScreen(presenter)

    assert all(rect.height >= 72 for rect in screen.option_rects(["Elf", "Human"]))


def test_race_selection_navigation_and_quit(monkeypatch):
    presenter = _make_presenter()
    screen = race_selection.RaceSelectionScreen(presenter)
    monkeypatch.setattr(screen, "draw_all", lambda: None)

    races = {"Elf": ElfRace, "Human": HumanRace}

    event_batches = iter(
        [
            [SimpleNamespace(type=pygame.KEYDOWN, key=pygame.K_DOWN)],
            [SimpleNamespace(type=pygame.KEYDOWN, key=pygame.K_SPACE)],
        ]
    )
    monkeypatch.setattr(
        "src.ui_pygame.gui.race_selection.pygame.event.get", lambda: next(event_batches, [])
    )
    assert screen.navigate(races) == "Human"

    event_batches = iter(
        [
            [SimpleNamespace(type=pygame.KEYDOWN, key=pygame.K_ESCAPE)],
        ]
    )
    monkeypatch.setattr(
        "src.ui_pygame.gui.race_selection.pygame.event.get", lambda: next(event_batches, [])
    )
    assert screen.navigate(races) is None

    clear_calls = []
    pressed_states = iter([[1], [1], [], []])
    monkeypatch.setattr(
        "src.ui_pygame.gui.input_guards.pygame.key.get_pressed", lambda: next(pressed_states, [])
    )
    event_batches = iter(
        [
            [SimpleNamespace(type=pygame.KEYDOWN, key=pygame.K_SPACE)],
            [SimpleNamespace(type=pygame.KEYUP, key=pygame.K_SPACE)],
            [SimpleNamespace(type=pygame.KEYDOWN, key=pygame.K_DOWN)],
            [SimpleNamespace(type=pygame.KEYDOWN, key=pygame.K_SPACE)],
        ]
    )
    monkeypatch.setattr(
        "src.ui_pygame.gui.race_selection.pygame.event.get", lambda: next(event_batches, [])
    )
    monkeypatch.setattr(
        "src.ui_pygame.gui.race_selection.pygame.event.clear", lambda: clear_calls.append(True)
    )
    assert screen.navigate(races, flush_events=True, require_key_release=True) == "Human"
    assert clear_calls == [True]

    screen.current_selection = 0
    monkeypatch.setattr("src.ui_pygame.gui.input_guards.pygame.key.get_pressed", lambda: [])
    event_batches = iter([[SimpleNamespace(type=pygame.KEYDOWN, key=pygame.K_SPACE)]])
    monkeypatch.setattr(
        "src.ui_pygame.gui.race_selection.pygame.event.get", lambda: next(event_batches, [])
    )
    assert screen.navigate(races, flush_events=True, require_key_release=True) == "Elf"

    screen.set_races(races)
    click_pos = screen.option_rects()[1].center
    event_batches = iter([[SimpleNamespace(type=pygame.MOUSEBUTTONDOWN, button=1, pos=click_pos)]])
    monkeypatch.setattr(
        "src.ui_pygame.gui.race_selection.pygame.event.get", lambda: next(event_batches, [])
    )
    assert screen.navigate(races) == "Human"

    monkeypatch.setattr(screen, "set_races", lambda *_args: setattr(screen, "races", []))
    assert screen.navigate(races) is None

    quit_calls = []
    monkeypatch.setattr(screen, "set_races", lambda *_args: setattr(screen, "races", ["Elf"]))
    monkeypatch.setattr(
        "src.ui_pygame.gui.race_selection.pygame.quit", lambda: quit_calls.append(True)
    )
    monkeypatch.setattr("sys.exit", lambda: (_ for _ in ()).throw(SystemExit()))
    monkeypatch.setattr(
        "src.ui_pygame.gui.race_selection.pygame.event.get",
        lambda: [SimpleNamespace(type=pygame.QUIT)],
    )

    with pytest.raises(SystemExit):
        screen.navigate(races)
    assert quit_calls
