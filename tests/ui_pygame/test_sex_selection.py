#!/usr/bin/env python3
"""Focused coverage for the character sex selection screen."""

from __future__ import annotations

from types import SimpleNamespace

import pygame
import pytest

from src.ui_pygame.gui import sex_selection


class DummySurface:
    def __init__(self, size=(64, 24), text=None):
        self._size = size
        self.text = text

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
    def __init__(self, height=24):
        self.render_calls = []
        self._height = height

    def render(self, text, _antialias, _color):
        self.render_calls.append(text)
        return DummySurface((max(8, len(text) * 8), self._height), text=text)

    def get_height(self):
        return self._height


class RecordingScreen:
    def __init__(self):
        self.blit_calls = []
        self.fill_calls = []

    def blit(self, surface, position):
        self.blit_calls.append((surface, position))

    def fill(self, color):
        self.fill_calls.append(color)


def _make_presenter():
    return SimpleNamespace(
        screen=RecordingScreen(),
        width=900,
        height=700,
        title_font=RecordingFont(30),
        normal_font=RecordingFont(22),
        small_font=RecordingFont(18),
        clock=SimpleNamespace(tick=lambda _fps: None),
    )


def test_sex_selection_draws_options(monkeypatch):
    presenter = _make_presenter()
    screen = sex_selection.SexSelectionScreen(presenter)
    draw_calls = []
    monkeypatch.setattr(
        "src.ui_pygame.gui.sex_selection.pygame.draw.rect",
        lambda *_args, **_kwargs: draw_calls.append((_args, _kwargs)),
    )

    screen.draw()

    assert "Select the sex for your character" in presenter.normal_font.render_calls
    assert "Description" in presenter.normal_font.render_calls
    assert {"Male", "Female"}.issubset(set(presenter.normal_font.render_calls))
    assert "Male" in presenter.title_font.render_calls
    assert draw_calls


def test_sex_selection_options_expand_to_native_touch_targets():
    presenter = _make_presenter()
    presenter.width, presenter.height = (1920, 1080)
    screen = sex_selection.SexSelectionScreen(presenter)

    assert all(rect.height >= 72 for rect in screen.option_rects())


def test_sex_selection_navigation_and_cancel(monkeypatch):
    presenter = _make_presenter()
    screen = sex_selection.SexSelectionScreen(presenter)
    monkeypatch.setattr(screen, "draw", lambda *_args, **_kwargs: None)
    monkeypatch.setattr("src.ui_pygame.gui.sex_selection.pygame.display.flip", lambda: None)
    monkeypatch.setattr("src.ui_pygame.gui.input_guards.pygame.key.get_pressed", lambda: [])

    event_batches = iter(
        [
            [SimpleNamespace(type=pygame.KEYDOWN, key=pygame.K_DOWN)],
            [SimpleNamespace(type=pygame.KEYDOWN, key=pygame.K_SPACE)],
        ]
    )
    monkeypatch.setattr(
        "src.ui_pygame.gui.sex_selection.pygame.event.get", lambda: next(event_batches, [])
    )
    assert screen.navigate() == "Female"

    event_batches = iter([[SimpleNamespace(type=pygame.KEYDOWN, key=pygame.K_ESCAPE)]])
    monkeypatch.setattr(
        "src.ui_pygame.gui.sex_selection.pygame.event.get", lambda: next(event_batches, [])
    )
    assert screen.navigate() is None

    click_pos = screen.option_rects()[1].center
    event_batches = iter([[SimpleNamespace(type=pygame.MOUSEBUTTONDOWN, button=1, pos=click_pos)]])
    monkeypatch.setattr(
        "src.ui_pygame.gui.sex_selection.pygame.event.get", lambda: next(event_batches, [])
    )
    assert screen.navigate() == "Female"


def test_sex_selection_quit_exits(monkeypatch):
    presenter = _make_presenter()
    screen = sex_selection.SexSelectionScreen(presenter)
    quit_calls = []
    monkeypatch.setattr(screen, "draw", lambda *_args, **_kwargs: None)
    monkeypatch.setattr("src.ui_pygame.gui.sex_selection.pygame.display.flip", lambda: None)
    monkeypatch.setattr(
        "src.ui_pygame.gui.sex_selection.pygame.quit", lambda: quit_calls.append(True)
    )
    monkeypatch.setattr("sys.exit", lambda: (_ for _ in ()).throw(SystemExit()))
    monkeypatch.setattr(
        "src.ui_pygame.gui.sex_selection.pygame.event.get",
        lambda: [SimpleNamespace(type=pygame.QUIT)],
    )

    with pytest.raises(SystemExit):
        screen.navigate()
    assert quit_calls
