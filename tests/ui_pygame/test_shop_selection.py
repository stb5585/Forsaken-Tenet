#!/usr/bin/env python3
"""Focused coverage for the shop-selection screen."""

from __future__ import annotations

from types import SimpleNamespace

import pygame
import pytest

from src.ui_pygame.gui import shop_selection


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
        large_font=RecordingFont(26),
        normal_font=RecordingFont(22),
        small_font=RecordingFont(18),
        clock=SimpleNamespace(tick=lambda _fps: None),
    )


def test_shop_selection_draw_menu_panel(monkeypatch):
    presenter = _make_presenter()
    screen = shop_selection.ShopSelectionScreen(presenter)
    screen.current_selection = 1

    panel_calls = []
    draw_rect_calls = []
    monkeypatch.setattr(
        screen,
        "draw_semi_transparent_panel",
        lambda rect, alpha=180: panel_calls.append((rect, alpha)),
    )
    monkeypatch.setattr(
        "src.ui_pygame.gui.shop_selection.pygame.draw.rect",
        lambda *_args, **_kwargs: draw_rect_calls.append((_args, _kwargs)),
    )

    screen.draw_menu_panel(["Blacksmith", "Jeweler", "Leave"])

    assert panel_calls
    assert "Select a Shop" in presenter.title_font.render_calls
    assert "Blacksmith" in presenter.normal_font.render_calls
    assert "Jeweler" in presenter.normal_font.render_calls
    assert "UP/DOWN: Navigate" in presenter.small_font.render_calls
    assert "ENTER: Select" in presenter.small_font.render_calls
    assert "ESC: Back" in presenter.small_font.render_calls
    assert draw_rect_calls


def test_shop_selection_options_expand_to_native_touch_targets():
    presenter = _make_presenter()
    presenter.width, presenter.height = (1920, 1080)
    screen = shop_selection.ShopSelectionScreen(presenter)

    assert all(rect.height >= 72 for rect in screen.option_rects(["Blacksmith", "Jeweler"]))


def test_shop_selection_navigate_selects_wraps_and_cancels(monkeypatch):
    presenter = _make_presenter()
    screen = shop_selection.ShopSelectionScreen(presenter)
    monkeypatch.setattr(screen, "draw_background", lambda: None)
    monkeypatch.setattr(screen, "draw_menu_panel", lambda _options: None)
    monkeypatch.setattr("src.ui_pygame.gui.shop_selection.pygame.display.flip", lambda: None)

    event_batches = iter(
        [
            [SimpleNamespace(type=pygame.KEYDOWN, key=pygame.K_DOWN)],
            [SimpleNamespace(type=pygame.KEYDOWN, key=pygame.K_RETURN)],
        ]
    )
    monkeypatch.setattr(
        "src.ui_pygame.gui.shop_selection.pygame.event.get", lambda: next(event_batches, [])
    )
    assert screen.navigate(["Blacksmith", "Jeweler", "Leave"]) == 1

    screen.current_selection = 0
    event_batches = iter(
        [
            [SimpleNamespace(type=pygame.KEYDOWN, key=pygame.K_UP)],
            [SimpleNamespace(type=pygame.KEYDOWN, key=pygame.K_SPACE)],
        ]
    )
    monkeypatch.setattr(
        "src.ui_pygame.gui.shop_selection.pygame.event.get", lambda: next(event_batches, [])
    )
    assert screen.navigate(["Blacksmith", "Jeweler", "Leave"]) == 2

    event_batches = iter(
        [
            [SimpleNamespace(type=pygame.KEYDOWN, key=pygame.K_ESCAPE)],
        ]
    )
    monkeypatch.setattr(
        "src.ui_pygame.gui.shop_selection.pygame.event.get", lambda: next(event_batches, [])
    )
    assert screen.navigate(["Blacksmith", "Jeweler", "Leave"]) is None

    screen.current_selection = 0
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
        "src.ui_pygame.gui.shop_selection.pygame.event.get", lambda: next(event_batches, [])
    )
    monkeypatch.setattr(
        "src.ui_pygame.gui.shop_selection.pygame.event.clear", lambda: clear_calls.append(True)
    )
    assert (
        screen.navigate(
            ["Blacksmith", "Jeweler", "Leave"], flush_events=True, require_key_release=True
        )
        == 1
    )
    assert clear_calls == [True]

    screen.current_selection = 0
    monkeypatch.setattr("src.ui_pygame.gui.input_guards.pygame.key.get_pressed", lambda: [])
    event_batches = iter([[SimpleNamespace(type=pygame.KEYDOWN, key=pygame.K_RETURN)]])
    monkeypatch.setattr(
        "src.ui_pygame.gui.shop_selection.pygame.event.get", lambda: next(event_batches, [])
    )
    assert (
        screen.navigate(
            ["Blacksmith", "Jeweler", "Leave"], flush_events=True, require_key_release=True
        )
        == 0
    )

    click_pos = screen.option_rects(["Blacksmith", "Jeweler", "Leave"])[1].center
    event_batches = iter([[SimpleNamespace(type=pygame.MOUSEBUTTONDOWN, button=1, pos=click_pos)]])
    monkeypatch.setattr(
        "src.ui_pygame.gui.shop_selection.pygame.event.get", lambda: next(event_batches, [])
    )
    assert screen.navigate(["Blacksmith", "Jeweler", "Leave"]) == 1


def test_shop_selection_quit_event_raises(monkeypatch):
    presenter = _make_presenter()
    screen = shop_selection.ShopSelectionScreen(presenter)
    monkeypatch.setattr(screen, "draw_background", lambda: None)
    monkeypatch.setattr(screen, "draw_menu_panel", lambda _options: None)
    monkeypatch.setattr("src.ui_pygame.gui.shop_selection.pygame.display.flip", lambda: None)

    quit_calls = []
    monkeypatch.setattr(
        "src.ui_pygame.gui.shop_selection.pygame.quit", lambda: quit_calls.append(True)
    )
    monkeypatch.setattr("sys.exit", lambda: (_ for _ in ()).throw(SystemExit()))
    monkeypatch.setattr(
        "src.ui_pygame.gui.shop_selection.pygame.event.get",
        lambda: [SimpleNamespace(type=pygame.QUIT)],
    )

    with pytest.raises(SystemExit):
        screen.navigate(["Blacksmith"])
    assert quit_calls
