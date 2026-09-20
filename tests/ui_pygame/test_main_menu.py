#!/usr/bin/env python3
"""Focused coverage for the main menu screen helpers."""

from __future__ import annotations

from types import SimpleNamespace

import pygame
import pytest

from src.ui_pygame.gui import main_menu


class DummySurface:
    def __init__(self, size=(64, 24), text=None):
        self._size = size
        self.text = text

    def get_size(self):
        return self._size

    def get_width(self):
        return self._size[0]

    def get_height(self):
        return self._size[1]

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
        return DummySurface((max(8, len(text) * 8), 20), text=text)

    def size(self, text):
        return (max(8, len(text) * 8), 20)


class RecordingScreen:
    def __init__(self):
        self.blit_calls = []
        self.fill_calls = []

    def fill(self, color):
        self.fill_calls.append(color)

    def blit(self, surface, position):
        self.blit_calls.append((surface, position))


def _make_presenter():
    return SimpleNamespace(
        screen=RecordingScreen(),
        width=900,
        height=700,
        title_font=RecordingFont(),
        normal_font=RecordingFont(),
        small_font=RecordingFont(),
        clock=SimpleNamespace(tick=lambda _fps: None),
    )


def test_main_menu_draw_and_navigation(monkeypatch):
    presenter = _make_presenter()
    background = DummySurface((1536, 1024), text="background")
    scaled_background = DummySurface((1050, 700), text="scaled")
    monkeypatch.setattr(
        "src.ui_pygame.gui.main_menu.pygame.image.load", lambda *_args, **_kwargs: background
    )
    monkeypatch.setattr(
        "src.ui_pygame.gui.main_menu.pygame.transform.smoothscale",
        lambda _surface, _size: scaled_background,
    )
    screen = main_menu.MainMenuScreen(presenter)

    draw_calls = []
    monkeypatch.setattr(
        "src.ui_pygame.gui.main_menu.pygame.draw.rect",
        lambda *_args, **_kwargs: draw_calls.append((_args, _kwargs)),
    )
    flip_calls = []
    monkeypatch.setattr(
        "src.ui_pygame.gui.main_menu.pygame.display.flip", lambda: flip_calls.append(True)
    )

    screen.options = ["New Game", "Load Game", "Quit"]
    screen.current_option = 1
    screen.draw_background()
    assert presenter.screen.blit_calls[-1][0] is scaled_background

    screen.draw_title()
    assert "The Forsaken Tenet" not in presenter.title_font.render_calls

    screen.draw_menu()
    assert "New Game" in presenter.normal_font.render_calls
    assert "Load Game" in presenter.normal_font.render_calls
    assert draw_calls

    screen.draw()
    assert flip_calls

    event_batches = iter(
        [
            [SimpleNamespace(type=pygame.KEYDOWN, key=pygame.K_DOWN)],
            [SimpleNamespace(type=pygame.KEYDOWN, key=pygame.K_RETURN)],
        ]
    )
    monkeypatch.setattr(
        "src.ui_pygame.gui.main_menu.pygame.event.get", lambda: next(event_batches, [])
    )
    assert screen.navigate(["New Game", "Load Game", "Quit"]) == 2

    screen.current_option = 0
    event_batches = iter(
        [
            [SimpleNamespace(type=pygame.KEYDOWN, key=pygame.K_ESCAPE)],
        ]
    )
    monkeypatch.setattr(
        "src.ui_pygame.gui.main_menu.pygame.event.get", lambda: next(event_batches, [])
    )
    assert screen.navigate(["New Game", "Load Game", "Quit"]) is None

    screen.current_option = 0
    clear_calls = []
    pressed_states = iter([[1], [1], [], []])
    monkeypatch.setattr(
        "src.ui_pygame.gui.input_guards.pygame.key.get_pressed", lambda: next(pressed_states, [])
    )
    event_batches = iter(
        [
            [SimpleNamespace(type=pygame.KEYDOWN, key=pygame.K_RETURN)],
            [SimpleNamespace(type=pygame.KEYUP, key=pygame.K_RETURN)],
            [SimpleNamespace(type=pygame.KEYDOWN, key=pygame.K_RETURN)],
        ]
    )
    monkeypatch.setattr(
        "src.ui_pygame.gui.main_menu.pygame.event.get", lambda: next(event_batches, [])
    )
    monkeypatch.setattr(
        "src.ui_pygame.gui.main_menu.pygame.event.clear", lambda: clear_calls.append(True)
    )
    assert (
        screen.navigate(
            ["New Game", "Load Game", "Quit"], flush_events=True, require_key_release=True
        )
        == 0
    )

    screen.current_option = 0
    screen.options = ["New Game", "Load Game", "Quit"]
    click_pos = screen.option_rects(screen.options)[1].center
    event_batches = iter([[SimpleNamespace(type=pygame.MOUSEBUTTONDOWN, button=1, pos=click_pos)]])
    monkeypatch.setattr(
        "src.ui_pygame.gui.main_menu.pygame.event.get", lambda: next(event_batches, [])
    )
    assert screen.navigate(["New Game", "Load Game", "Quit"]) == 1
    assert clear_calls == [True]

    screen.current_option = 0
    monkeypatch.setattr("src.ui_pygame.gui.input_guards.pygame.key.get_pressed", lambda: [])
    event_batches = iter([[SimpleNamespace(type=pygame.KEYDOWN, key=pygame.K_RETURN)]])
    monkeypatch.setattr(
        "src.ui_pygame.gui.main_menu.pygame.event.get", lambda: next(event_batches, [])
    )
    assert (
        screen.navigate(
            ["New Game", "Load Game", "Quit"], flush_events=True, require_key_release=True
        )
        == 0
    )


def test_main_menu_options_expand_to_native_touch_targets(monkeypatch):
    presenter = _make_presenter()
    presenter.width, presenter.height = (1920, 1080)
    monkeypatch.setattr(
        "src.ui_pygame.gui.main_menu.pygame.image.load",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(FileNotFoundError()),
    )
    screen = main_menu.MainMenuScreen(presenter)
    screen.options = ["New Game", "Load Game", "Quit"]

    assert all(rect.height >= 72 for rect in screen.option_rects())


def test_main_menu_quit_event_raises_system_exit(monkeypatch):
    presenter = _make_presenter()
    monkeypatch.setattr(
        "src.ui_pygame.gui.main_menu.pygame.image.load",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(FileNotFoundError()),
    )
    screen = main_menu.MainMenuScreen(presenter)
    monkeypatch.setattr(screen, "draw", lambda: None)

    quit_calls = []
    monkeypatch.setattr("src.ui_pygame.gui.main_menu.pygame.quit", lambda: quit_calls.append(True))
    monkeypatch.setattr("sys.exit", lambda: (_ for _ in ()).throw(SystemExit()))
    monkeypatch.setattr(
        "src.ui_pygame.gui.main_menu.pygame.event.get",
        lambda: [SimpleNamespace(type=pygame.QUIT)],
    )

    with pytest.raises(SystemExit):
        screen.navigate(["Play"])
    assert quit_calls


def test_main_menu_falls_back_to_text_title_when_background_missing(monkeypatch):
    presenter = _make_presenter()
    monkeypatch.setattr(
        "src.ui_pygame.gui.main_menu.pygame.image.load",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(FileNotFoundError()),
    )
    screen = main_menu.MainMenuScreen(presenter)

    screen.draw_background()
    screen.draw_title()

    assert presenter.screen.fill_calls == [screen.BLACK]
    assert "The Forsaken Tenet" in presenter.title_font.render_calls
