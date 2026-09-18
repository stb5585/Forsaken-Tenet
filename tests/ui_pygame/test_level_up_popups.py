#!/usr/bin/env python3
"""Focused coverage for level-up popup helpers."""

from __future__ import annotations

from types import SimpleNamespace

import pygame

from src.ui_pygame.gui import level_up_popup, stat_selection_popup


class DummySurface:
    def __init__(self, size=(64, 24), text=None):
        self._size = size
        self.text = text
        self.alpha = None
        self.fill_calls = []

    def set_alpha(self, value):
        self.alpha = value

    def fill(self, color):
        self.fill_calls.append(color)

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


class RecordingScreen:
    def __init__(self, size=(640, 480)):
        self._size = size
        self.blit_calls = []
        self.fill_calls = []

    def blit(self, surface, position):
        self.blit_calls.append((surface, position))

    def fill(self, color):
        self.fill_calls.append(color)

    def copy(self):
        return "screen-copy"


def _make_presenter():
    return SimpleNamespace(
        screen=RecordingScreen(),
        width=640,
        height=480,
        title_font=RecordingFont(),
        header_font=RecordingFont(),
        normal_font=RecordingFont(),
        small_font=RecordingFont(),
        clock=SimpleNamespace(tick=lambda _fps: None),
        get_background_surface=lambda: "presenter-bg",
    )


def test_level_up_popup_prepares_draws_and_shows(monkeypatch):
    presenter = _make_presenter()
    level_info = {
        "new_level": 9,
        "health_gain": 5,
        "mana_gain": 4,
        "attack_gain": 2,
        "defense_gain": 0,
        "magic_gain": 3,
        "magic_def_gain": 1,
        "new_abilities": ["Spell: Nova"],
        "spell_upgrades": ["Spark upgraded to Spark II"],
        "skill_upgrades": ["Slash goes up a level"],
    }
    popup = level_up_popup.LevelUpPopup(presenter, level_info)

    assert ("header", "You are now level 9!") in popup.content_lines
    assert ("gain", "Attack: +2") in popup.content_lines
    assert ("gain", "Defense: +0") not in popup.content_lines
    assert ("subheader", "New Abilities:") in popup.content_lines
    assert ("ability", "Spell: Nova") in popup.content_lines
    assert ("subheader", "Upgrades:") in popup.content_lines

    draw_calls = []
    monkeypatch.setattr(
        "src.ui_pygame.gui.level_up_popup.pygame.Surface",
        lambda size, *_args, **_kwargs: DummySurface(size),
    )
    monkeypatch.setattr(
        "src.ui_pygame.gui.level_up_popup.pygame.draw.rect",
        lambda *_args, **_kwargs: draw_calls.append((_args, _kwargs)),
    )
    popup.draw_popup()
    assert "LEVEL UP!" in presenter.title_font.render_calls
    assert "Click or press any key to continue..." in presenter.small_font.render_calls
    assert draw_calls

    presenter.get_background_surface = lambda: "bg-surface"
    assert popup._get_background_surface() == "bg-surface"
    presenter.get_background_surface = lambda: None
    assert popup._get_background_surface() == "screen-copy"
    presenter.get_background_surface = lambda: presenter.screen
    assert popup._get_background_surface() == "screen-copy"
    presenter.get_background_surface = lambda: (_ for _ in ()).throw(RuntimeError("boom"))
    assert popup._get_background_surface() == "screen-copy"

    monkeypatch.setattr("src.ui_pygame.gui.level_up_popup.pygame.display.flip", lambda: None)
    event_batches = iter(
        [
            [],
            [SimpleNamespace(type=pygame.KEYDOWN)],
        ]
    )
    monkeypatch.setattr(
        "src.ui_pygame.gui.level_up_popup.pygame.event.get", lambda: next(event_batches, [])
    )
    bg_calls = []
    popup.show(background_draw_func=lambda: bg_calls.append(True))
    assert bg_calls

    popup = level_up_popup.LevelUpPopup(presenter, level_info)
    event_batches = iter([[SimpleNamespace(type=pygame.MOUSEBUTTONDOWN, button=1, pos=(1, 1))]])
    monkeypatch.setattr(
        "src.ui_pygame.gui.level_up_popup.pygame.event.get", lambda: next(event_batches, [])
    )
    popup.show(background_draw_func=lambda: bg_calls.append(True))

    presenter.get_background_surface = lambda: "bg-default"
    popup = level_up_popup.LevelUpPopup(presenter, level_info)
    event_batches = iter(
        [
            [SimpleNamespace(type=pygame.QUIT)],
        ]
    )
    monkeypatch.setattr(
        "src.ui_pygame.gui.level_up_popup.pygame.event.get", lambda: next(event_batches, [])
    )
    popup.show()
    assert ("bg-default", (0, 0)) in presenter.screen.blit_calls

    popup = level_up_popup.LevelUpPopup(presenter, level_info)
    clear_calls = []
    key_states = iter([[1], []])
    event_batches = iter(
        [
            [SimpleNamespace(type=pygame.KEYDOWN)],
            [SimpleNamespace(type=pygame.KEYDOWN)],
        ]
    )
    monkeypatch.setattr(
        "src.ui_pygame.gui.input_guards.pygame.event.clear", lambda: clear_calls.append(True)
    )
    monkeypatch.setattr(
        "src.ui_pygame.gui.input_guards.pygame.key.get_pressed", lambda: next(key_states, [])
    )
    monkeypatch.setattr(
        "src.ui_pygame.gui.level_up_popup.pygame.event.get", lambda: next(event_batches, [])
    )
    popup.show(flush_events=True, require_key_release=True)
    assert clear_calls == [True]


def test_stat_selection_popup_draws_and_selects(monkeypatch):
    presenter = _make_presenter()
    options = [("Strength", 10), ("Dexterity", 8), ("Wisdom", 11)]
    popup = stat_selection_popup.StatSelectionPopup(presenter, options)

    draw_calls = []
    monkeypatch.setattr(
        "src.ui_pygame.gui.stat_selection_popup.pygame.Surface",
        lambda size, *_args, **_kwargs: DummySurface(size),
    )
    monkeypatch.setattr(
        "src.ui_pygame.gui.stat_selection_popup.pygame.draw.rect",
        lambda *_args, **_kwargs: draw_calls.append((_args, _kwargs)),
    )
    popup.draw_popup()
    assert "Choose Stat to Increase" in presenter.title_font.render_calls
    assert "Strength: 10 -> 11" in presenter.normal_font.render_calls
    assert "Up/Down or W/S to select | Enter to confirm" in presenter.small_font.render_calls
    assert draw_calls

    presenter.get_background_surface = lambda: "bg-surface"
    assert popup._get_background_surface() == "bg-surface"
    presenter.get_background_surface = lambda: None
    assert popup._get_background_surface() == "screen-copy"
    presenter.get_background_surface = lambda: presenter.screen
    assert popup._get_background_surface() == "screen-copy"
    presenter.get_background_surface = lambda: (_ for _ in ()).throw(RuntimeError("boom"))
    assert popup._get_background_surface() == "screen-copy"

    monkeypatch.setattr("src.ui_pygame.gui.stat_selection_popup.pygame.display.flip", lambda: None)
    event_batches = iter(
        [
            [SimpleNamespace(type=pygame.KEYDOWN, key=pygame.K_DOWN)],
            [SimpleNamespace(type=pygame.KEYDOWN, key=pygame.K_RETURN)],
        ]
    )
    monkeypatch.setattr(
        "src.ui_pygame.gui.stat_selection_popup.pygame.event.get", lambda: next(event_batches, [])
    )
    assert popup.show(background_draw_func=lambda: presenter.screen.fill((1, 2, 3))) == "Dexterity"

    popup = stat_selection_popup.StatSelectionPopup(presenter, options)
    event_batches = iter(
        [
            [SimpleNamespace(type=pygame.KEYDOWN, key=pygame.K_UP)],
            [SimpleNamespace(type=pygame.KEYDOWN, key=pygame.K_SPACE)],
        ]
    )
    monkeypatch.setattr(
        "src.ui_pygame.gui.stat_selection_popup.pygame.event.get", lambda: next(event_batches, [])
    )
    assert popup.show() == "Wisdom"

    popup = stat_selection_popup.StatSelectionPopup(presenter, options)
    clear_calls = []
    key_states = iter([[1], []])
    event_batches = iter(
        [
            [SimpleNamespace(type=pygame.KEYDOWN, key=pygame.K_RETURN)],
            [SimpleNamespace(type=pygame.KEYDOWN, key=pygame.K_RETURN)],
        ]
    )
    monkeypatch.setattr(
        "src.ui_pygame.gui.input_guards.pygame.event.clear", lambda: clear_calls.append(True)
    )
    monkeypatch.setattr(
        "src.ui_pygame.gui.input_guards.pygame.key.get_pressed", lambda: next(key_states, [])
    )
    monkeypatch.setattr(
        "src.ui_pygame.gui.stat_selection_popup.pygame.event.get", lambda: next(event_batches, [])
    )
    assert popup.show(flush_events=True, require_key_release=True) == "Strength"
    assert clear_calls == [True]

    popup = stat_selection_popup.StatSelectionPopup(presenter, options)
    monkeypatch.setattr("src.ui_pygame.gui.input_guards.pygame.key.get_pressed", lambda: [])
    event_batches = iter(
        [
            [SimpleNamespace(type=pygame.KEYDOWN, key=pygame.K_RETURN)],
        ]
    )
    monkeypatch.setattr(
        "src.ui_pygame.gui.stat_selection_popup.pygame.event.get", lambda: next(event_batches, [])
    )
    assert popup.show(flush_events=True, require_key_release=True) == "Strength"

    popup = stat_selection_popup.StatSelectionPopup(presenter, options)
    click_pos = popup.option_rects()[2].center
    event_batches = iter(
        [
            [SimpleNamespace(type=pygame.MOUSEMOTION, pos=click_pos)],
            [SimpleNamespace(type=pygame.MOUSEBUTTONDOWN, button=1, pos=click_pos)],
        ]
    )
    monkeypatch.setattr(
        "src.ui_pygame.gui.stat_selection_popup.pygame.event.get", lambda: next(event_batches, [])
    )
    assert popup.show() == "Wisdom"

    popup = stat_selection_popup.StatSelectionPopup(presenter, options)
    event_batches = iter(
        [
            [SimpleNamespace(type=pygame.QUIT)],
        ]
    )
    monkeypatch.setattr(
        "src.ui_pygame.gui.stat_selection_popup.pygame.event.get", lambda: next(event_batches, [])
    )
    assert popup.show() is None
