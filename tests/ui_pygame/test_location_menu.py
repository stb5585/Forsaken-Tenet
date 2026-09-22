#!/usr/bin/env python3
"""Focused coverage for generic location-menu helpers."""

from __future__ import annotations

from types import SimpleNamespace

import pygame
import pytest

from src.ui_pygame.display_scaling import DisplayConfiguration, LayoutMetrics
from src.ui_pygame.gui import location_menu


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
    def __init__(self, size=(900, 700)):
        self._size = size
        self.blit_calls = []
        self.fill_calls = []

    def blit(self, surface, position):
        self.blit_calls.append((surface, position))

    def fill(self, color):
        self.fill_calls.append(color)

    def copy(self):
        return "screen-copy"


def _make_presenter(size=(900, 700)):
    metrics = LayoutMetrics(DisplayConfiguration.for_viewport(fullscreen=False, render_size=size))
    return SimpleNamespace(
        screen=RecordingScreen(size),
        width=size[0],
        height=size[1],
        title_font=RecordingFont(32),
        large_font=RecordingFont(28),
        normal_font=RecordingFont(22),
        small_font=RecordingFont(18),
        clock=SimpleNamespace(tick=lambda _fps: None),
        debug_mode=True,
        layout_metrics=metrics,
    )


def _scripted_events(batches):
    iterator = iter(batches)

    def next_batch():
        try:
            return next(iterator)
        except StopIteration as error:
            raise AssertionError("scripted event queue exhausted") from error

    return next_batch


def test_location_menu_draw_helpers(monkeypatch):
    presenter = _make_presenter()
    screen = location_menu.LocationMenuScreen(presenter, "Church")
    screen.options_list = ["Heal", "Bless", "Leave"]
    screen.current_option = 1

    panel_calls = []
    monkeypatch.setattr(
        screen,
        "draw_semi_transparent_panel",
        lambda rect, alpha=180: panel_calls.append((rect, alpha)),
    )
    draw_rect_calls = []
    monkeypatch.setattr(
        "src.ui_pygame.gui.location_menu.pygame.draw.rect",
        lambda *_args, **_kwargs: draw_rect_calls.append((_args, _kwargs)),
    )
    flip_calls = []
    monkeypatch.setattr(
        "src.ui_pygame.gui.location_menu.pygame.display.flip", lambda: flip_calls.append(True)
    )

    screen.draw_top()
    assert "Church" in presenter.large_font.render_calls

    screen.draw_options()
    assert "Heal" in presenter.normal_font.render_calls
    assert "Bless" in presenter.normal_font.render_calls

    screen.draw_content("Welcome to town\nThis is a wrapped paragraph.")
    assert "Welcome to town" in presenter.large_font.render_calls

    items_data = [(0, "Potion", 2, False), (1, "Elixir", 1, True)]
    screen.draw_content(items_data=items_data)
    assert any(
        surface.text == ">"
        for surface, _pos in presenter.screen.blit_calls
        if hasattr(surface, "text")
    )

    screen.draw_options_instructions()
    assert "[Use arrows to select]" in presenter.normal_font.render_calls

    monkeypatch.setattr(screen, "draw_background", lambda: panel_calls.append(("background", None)))
    monkeypatch.setattr(screen, "draw_top", lambda: panel_calls.append(("top", None)))
    monkeypatch.setattr(screen, "draw_options", lambda: panel_calls.append(("options", None)))
    monkeypatch.setattr(
        screen,
        "draw_content",
        lambda *args, **kwargs: panel_calls.append(
            ("content", kwargs.get("items_data", args[0] if args else None))
        ),
    )
    screen.draw_all()
    assert ("background", None) in panel_calls
    assert flip_calls
    assert draw_rect_calls


@pytest.mark.parametrize("size", ((900, 700), (1080, 1920)))
def test_bounty_rows_use_shared_measured_rects_at_supported_viewports(monkeypatch, size):
    presenter = _make_presenter(size)
    screen = location_menu.LocationMenuScreen(presenter, "Accept Bounty")
    screen.options_list = ["Green Slime", "Scarecrow", "Bandit", "Back"]
    screen.current_option = 1
    monkeypatch.setattr(screen, "draw_semi_transparent_panel", lambda *_args, **_kwargs: None)
    draw_calls = []
    monkeypatch.setattr(
        "src.ui_pygame.gui.location_menu.pygame.draw.rect",
        lambda _surface, _color, rect, *_args, **_kwargs: draw_calls.append(rect.copy()),
    )

    option_rect = screen.option_rects()[1]
    assert option_rect.height >= presenter.normal_font.get_height() + (
        presenter.layout_metrics.unit(6) * 2
    )
    screen.draw_options()
    assert option_rect in draw_calls

    item_rect = dict(screen.content_row_rects(3))[0]
    assert item_rect.height >= presenter.large_font.get_height() + (
        presenter.layout_metrics.unit(4) * 2
    )
    assert screen._content_rect().contains(item_rect)

    screen.draw_content(
        items_data=[
            (0, "Green Slime", 0, False),
            (1, "Scarecrow", 0, True),
            (2, "Bandit", 0, False),
        ]
    )
    selected_row = dict(screen.content_row_rects(3))[1]
    assert selected_row in draw_calls


def test_bounty_content_navigation_uses_responsive_rows_and_scrolls(monkeypatch):
    presenter = _make_presenter((1080, 1920))
    screen = location_menu.LocationMenuScreen(presenter, "Accept Bounty")
    items = [(f"Bounty {index}", 0) for index in range(60)]
    monkeypatch.setattr(screen, "draw_background", lambda: None)
    monkeypatch.setattr(screen, "draw_top", lambda: None)
    monkeypatch.setattr(screen, "draw_options_instructions", lambda: None)
    monkeypatch.setattr(screen, "draw_npc_portrait", lambda **_kwargs: None)
    monkeypatch.setattr(screen, "draw_content", lambda **_kwargs: None)
    monkeypatch.setattr("src.ui_pygame.gui.location_menu.pygame.display.flip", lambda: None)

    monkeypatch.setattr(
        "src.ui_pygame.gui.location_menu.pygame.event.get",
        _scripted_events(
            [
                [SimpleNamespace(type=pygame.KEYDOWN, key=pygame.K_DOWN)],
                [SimpleNamespace(type=pygame.KEYDOWN, key=pygame.K_RETURN)],
            ]
        ),
    )
    assert screen.navigate_with_content(items) == 1

    screen.current_option = 0
    screen.scroll_offset = 0
    row_rect = dict(screen.content_row_rects(len(items)))[3]
    monkeypatch.setattr(
        "src.ui_pygame.gui.location_menu.pygame.event.get",
        _scripted_events(
            [[SimpleNamespace(type=pygame.MOUSEBUTTONDOWN, button=1, pos=row_rect.center)]]
        ),
    )
    assert screen.navigate_with_content(items) == 3

    screen.current_option = 0
    screen.scroll_offset = 0
    monkeypatch.setattr(
        "src.ui_pygame.gui.location_menu.pygame.event.get",
        _scripted_events(
            [
                [SimpleNamespace(type=pygame.KEYDOWN, key=pygame.K_UP)],
                [SimpleNamespace(type=pygame.KEYDOWN, key=pygame.K_RETURN)],
            ]
        ),
    )
    assert screen.navigate_with_content(items) == len(items) - 1
    assert screen.scroll_offset > 0


def test_location_menu_draws_static_and_option_portraits(monkeypatch):
    presenter = _make_presenter()
    screen = location_menu.LocationMenuScreen(presenter, "Patrons")
    screen.options_list = ["Barkeep", "Waitress", "Back"]
    drawn_portraits = []

    monkeypatch.setattr(screen, "draw_background", lambda: None)
    monkeypatch.setattr(screen, "draw_top", lambda: None)
    monkeypatch.setattr(screen, "draw_options", lambda: None)
    monkeypatch.setattr(screen, "draw_content", lambda *args, **kwargs: None)
    monkeypatch.setattr(
        screen, "draw_npc_portrait", lambda **kwargs: drawn_portraits.append(kwargs.get("npc_name"))
    )
    monkeypatch.setattr("src.ui_pygame.gui.location_menu.pygame.display.flip", lambda: None)

    screen.set_location_portrait("Priest")
    screen.draw_all()
    assert drawn_portraits[-1] == "Priest"

    screen.set_option_portraits(["Barkeep", "Waitress", None])
    screen.current_option = 1
    screen.draw_all()
    assert drawn_portraits[-1] == "Waitress"

    screen.current_option = 2
    screen.draw_all()
    assert drawn_portraits[-1] is None


def test_location_menu_navigation_and_item_navigation(monkeypatch):
    presenter = _make_presenter()
    screen = location_menu.LocationMenuScreen(presenter, "Inn")
    monkeypatch.setattr(screen, "draw_all", lambda: None)
    monkeypatch.setattr(screen, "draw_background", lambda: None)
    monkeypatch.setattr(screen, "draw_top", lambda: None)
    monkeypatch.setattr(screen, "draw_options", lambda: None)
    monkeypatch.setattr(screen, "draw_options_instructions", lambda: None)
    monkeypatch.setattr(screen, "draw_content", lambda *args, **kwargs: None)
    monkeypatch.setattr("src.ui_pygame.gui.location_menu.pygame.display.flip", lambda: None)

    event_batches = iter(
        [
            [SimpleNamespace(type=pygame.KEYDOWN, key=pygame.K_DOWN)],
            [SimpleNamespace(type=pygame.KEYDOWN, key=pygame.K_RETURN)],
        ]
    )
    monkeypatch.setattr(
        "src.ui_pygame.gui.location_menu.pygame.event.get", _scripted_events(event_batches)
    )
    assert screen.navigate(["Rest", "Leave"]) == 1

    screen.current_option = 1
    event_batches = iter(
        [
            [SimpleNamespace(type=pygame.KEYDOWN, key=pygame.K_ESCAPE)],
        ]
    )
    monkeypatch.setattr(
        "src.ui_pygame.gui.location_menu.pygame.event.get", lambda: next(event_batches, [])
    )
    assert screen.navigate(["Rest", "Leave"], reset_cursor=False) is None
    assert screen.current_option == 1

    screen.current_option = 4
    event_batches = iter(
        [
            [SimpleNamespace(type=pygame.KEYDOWN, key=pygame.K_ESCAPE)],
        ]
    )
    monkeypatch.setattr(
        "src.ui_pygame.gui.location_menu.pygame.event.get", lambda: next(event_batches, [])
    )
    assert screen.navigate(["Only"], reset_cursor=False) is None
    assert screen.current_option == 0

    screen.current_option = 1
    event_batches = iter(
        [
            [SimpleNamespace(type=pygame.KEYDOWN, key=pygame.K_ESCAPE)],
        ]
    )
    monkeypatch.setattr(
        "src.ui_pygame.gui.location_menu.pygame.event.get", lambda: next(event_batches, [])
    )
    assert screen.navigate(["Rest", "Leave"], reset_cursor=True) is None
    assert screen.current_option == 0

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
            [SimpleNamespace(type=pygame.KEYDOWN, key=pygame.K_DOWN)],
            [SimpleNamespace(type=pygame.KEYDOWN, key=pygame.K_RETURN)],
        ]
    )
    monkeypatch.setattr(
        "src.ui_pygame.gui.location_menu.pygame.event.get", lambda: next(event_batches, [])
    )
    monkeypatch.setattr(
        "src.ui_pygame.gui.location_menu.pygame.event.clear", lambda: clear_calls.append(True)
    )
    assert screen.navigate(["Rest", "Leave"], flush_events=True, require_key_release=True) == 1
    assert clear_calls == [True]

    screen.current_option = 0
    monkeypatch.setattr("src.ui_pygame.gui.input_guards.pygame.key.get_pressed", lambda: [])
    event_batches = iter([[SimpleNamespace(type=pygame.KEYDOWN, key=pygame.K_RETURN)]])
    monkeypatch.setattr(
        "src.ui_pygame.gui.location_menu.pygame.event.get", lambda: next(event_batches, [])
    )
    assert screen.navigate(["Rest", "Leave"], flush_events=True, require_key_release=True) == 0

    screen.options_list = ["Rest", "Leave"]
    click_pos = screen.option_rects()[1].center
    event_batches = iter([[SimpleNamespace(type=pygame.MOUSEBUTTONDOWN, button=1, pos=click_pos)]])
    monkeypatch.setattr(
        "src.ui_pygame.gui.location_menu.pygame.event.get", lambda: next(event_batches, [])
    )
    assert screen.navigate(["Rest", "Leave"]) == 1

    event_batches = iter(
        [
            [SimpleNamespace(type=pygame.KEYDOWN, key=pygame.K_SPACE)],
        ]
    )
    monkeypatch.setattr(
        "src.ui_pygame.gui.location_menu.pygame.event.get", lambda: next(event_batches, [])
    )
    screen.display_items_list([("Potion", 2)])

    event_batches = iter(
        [
            [SimpleNamespace(type=pygame.MOUSEBUTTONDOWN, button=1, pos=(450, 250))],
        ]
    )
    monkeypatch.setattr(
        "src.ui_pygame.gui.location_menu.pygame.event.get", lambda: next(event_batches, [])
    )
    screen.display_items_list([("Potion", 2)])

    items = [(f"Item {idx}", idx + 1) for idx in range(25)]
    screen.current_option = 0
    screen.scroll_offset = 0
    event_batches = iter(
        [
            [SimpleNamespace(type=pygame.KEYDOWN, key=pygame.K_DOWN)],
            [SimpleNamespace(type=pygame.KEYDOWN, key=pygame.K_RETURN)],
        ]
    )
    monkeypatch.setattr(
        "src.ui_pygame.gui.location_menu.pygame.event.get", lambda: next(event_batches, [])
    )
    assert screen.navigate_with_content(items) == 1

    screen.current_option = 0
    event_batches = iter(
        [
            [SimpleNamespace(type=pygame.KEYDOWN, key=pygame.K_UP)],
            [SimpleNamespace(type=pygame.KEYDOWN, key=pygame.K_RETURN)],
        ]
    )
    monkeypatch.setattr(
        "src.ui_pygame.gui.location_menu.pygame.event.get", lambda: next(event_batches, [])
    )
    assert screen.navigate_with_content(items) == len(items) - 1
    assert screen.scroll_offset > 0

    screen.current_option = 0
    screen.scroll_offset = 0
    row_pos = dict(screen.content_row_rects(len(items)))[2].center
    event_batches = iter(
        [
            [SimpleNamespace(type=pygame.MOUSEMOTION, pos=row_pos)],
            [SimpleNamespace(type=pygame.MOUSEBUTTONDOWN, button=1, pos=row_pos)],
        ]
    )
    monkeypatch.setattr(
        "src.ui_pygame.gui.location_menu.pygame.event.get", lambda: next(event_batches, [])
    )
    assert screen.navigate_with_content(items) == 2

    screen.current_option = 0
    screen.scroll_offset = 0
    event_batches = iter(
        [
            [SimpleNamespace(type=pygame.MOUSEWHEEL, y=-1)],
            [SimpleNamespace(type=pygame.KEYDOWN, key=pygame.K_RETURN)],
        ]
    )
    monkeypatch.setattr(
        "src.ui_pygame.gui.location_menu.pygame.event.get", lambda: next(event_batches, [])
    )
    assert screen.navigate_with_content(items) == 1

    screen.current_option = 0
    screen.scroll_offset = 0
    clear_calls.clear()
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
        "src.ui_pygame.gui.location_menu.pygame.event.get", lambda: next(event_batches, [])
    )
    assert screen.navigate_with_content(items, flush_events=True, require_key_release=True) == 1
    assert clear_calls == [True]

    screen.current_option = 0
    monkeypatch.setattr("src.ui_pygame.gui.input_guards.pygame.key.get_pressed", lambda: [])
    event_batches = iter([[SimpleNamespace(type=pygame.KEYDOWN, key=pygame.K_RETURN)]])
    monkeypatch.setattr(
        "src.ui_pygame.gui.location_menu.pygame.event.get", lambda: next(event_batches, [])
    )
    assert screen.navigate_with_content(items, flush_events=True, require_key_release=True) == 0


def test_location_menu_quit_event_raises(monkeypatch):
    presenter = _make_presenter()
    screen = location_menu.LocationMenuScreen(presenter, "Shop")
    monkeypatch.setattr(screen, "draw_all", lambda: None)
    quit_calls = []
    monkeypatch.setattr(
        "src.ui_pygame.gui.location_menu.pygame.quit", lambda: quit_calls.append(True)
    )
    monkeypatch.setattr("sys.exit", lambda: (_ for _ in ()).throw(SystemExit()))
    monkeypatch.setattr(
        "src.ui_pygame.gui.location_menu.pygame.event.get",
        lambda: [SimpleNamespace(type=pygame.QUIT)],
    )

    with pytest.raises(SystemExit):
        screen.navigate(["A", "B"])
    assert quit_calls
