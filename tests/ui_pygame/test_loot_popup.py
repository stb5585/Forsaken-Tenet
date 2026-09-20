#!/usr/bin/env python3
"""Focused coverage for pygame loot popup helpers."""

from __future__ import annotations

from types import SimpleNamespace

import pygame

from src.ui_pygame.gui import loot_popup


class RenderedText:
    def __init__(self, text):
        self.text = text

    def get_rect(self, **kwargs):
        rect = pygame.Rect(0, 0, max(8, len(self.text) * 8), 18)
        for key, value in kwargs.items():
            setattr(rect, key, value)
        return rect


class RecordingFont:
    def __init__(self):
        self.render_calls = []

    def render(self, text, _antialias, _color):
        self.render_calls.append(text)
        return RenderedText(text)


class RecordingScreen:
    def __init__(self, size=(640, 480)):
        self._size = size
        self.blit_calls = []
        self.fill_calls = []

    def get_width(self):
        return self._size[0]

    def get_height(self):
        return self._size[1]

    def blit(self, surface, position):
        self.blit_calls.append((surface, position))

    def fill(self, color):
        self.fill_calls.append(color)

    def copy(self):
        return "screen-copy"


class DummySurface:
    def __init__(self, size=(640, 480)):
        self.size = size
        self.fill_calls = []
        self.alpha = None

    def fill(self, color):
        self.fill_calls.append(color)

    def set_alpha(self, value):
        self.alpha = value


class DummyClock:
    def __init__(self):
        self.ticks = []

    def tick(self, fps):
        self.ticks.append(fps)


def _make_presenter():
    return SimpleNamespace(screen=RecordingScreen(), get_background_surface=lambda: "presenter-bg")


def _make_popup(monkeypatch):
    title_font = RecordingFont()
    item_font = RecordingFont()
    desc_font = RecordingFont()
    small_font = RecordingFont()
    fonts = iter([title_font, item_font, desc_font, small_font])
    flip_calls = []
    draw_calls = []
    clocks = []

    monkeypatch.setattr(
        "src.ui_pygame.gui.loot_popup.pygame.font.Font", lambda *_args, **_kwargs: next(fonts)
    )
    monkeypatch.setattr(
        "src.ui_pygame.gui.loot_popup.pygame.display.flip", lambda: flip_calls.append(True)
    )
    monkeypatch.setattr(
        "src.ui_pygame.gui.loot_popup.pygame.draw.rect",
        lambda *_args, **_kwargs: draw_calls.append((_args, _kwargs)),
    )
    monkeypatch.setattr(
        "src.ui_pygame.gui.loot_popup.pygame.Surface",
        lambda size, *_args, **_kwargs: DummySurface(size),
    )
    monkeypatch.setattr(
        "src.ui_pygame.gui.loot_popup.pygame.time.Clock",
        lambda: clocks.append(DummyClock()) or clocks[-1],
    )

    screen = RecordingScreen()
    popup = loot_popup.LootPopup(screen, _make_presenter())
    return SimpleNamespace(
        popup=popup,
        screen=screen,
        title_font=title_font,
        item_font=item_font,
        desc_font=desc_font,
        small_font=small_font,
        flip_calls=flip_calls,
        draw_calls=draw_calls,
        clocks=clocks,
    )


def test_show_loot_normalizes_items_and_uses_default_background(monkeypatch):
    bundle = _make_popup(monkeypatch)
    popup = bundle.popup

    item = SimpleNamespace(name="Potion")
    render_calls = []
    popup.max_animation_time = 1
    monkeypatch.setattr(popup, "_get_background_surface", lambda: "background")
    monkeypatch.setattr(
        popup,
        "_render_loot_popup",
        lambda items, chest_type: render_calls.append((items, chest_type, popup.animation_time)),
    )
    event_batches = iter(
        [
            [],
            [SimpleNamespace(type=pygame.KEYDOWN)],
        ]
    )
    monkeypatch.setattr(
        "src.ui_pygame.gui.loot_popup.pygame.event.get", lambda: next(event_batches, [])
    )

    popup.show_loot([None, item], chest_type="Relic Chest")
    assert render_calls[0][0] == [item]
    assert render_calls[0][1] == "Relic Chest"
    assert popup.animation_time == 1
    assert bundle.screen.blit_calls[0] == ("background", (0, 0))
    assert bundle.flip_calls
    assert bundle.clocks[0].ticks and bundle.clocks[0].ticks[-1] == 60

    empty_calls = []
    monkeypatch.setattr(
        popup,
        "_show_empty_chest",
        lambda chest_type, background_draw_func=None, **kwargs: empty_calls.append(
            (chest_type, background_draw_func, kwargs)
        )
        or "empty",
    )
    assert popup.show_loot(None, chest_type="Chest") == "empty"
    assert empty_calls[0][0] == "Chest"


def test_show_loot_renders_until_acknowledged(monkeypatch):
    bundle = _make_popup(monkeypatch)
    popup = bundle.popup
    popup.max_animation_time = 0
    render_calls = []
    monkeypatch.setattr("src.ui_pygame.gui.input_guards.pygame.key.get_pressed", lambda: [])
    monkeypatch.setattr(
        popup, "_render_loot_popup", lambda items, chest_type: render_calls.append(chest_type)
    )
    event_batches = iter(
        [
            [SimpleNamespace(type=pygame.KEYDOWN)],
        ]
    )
    monkeypatch.setattr(
        "src.ui_pygame.gui.loot_popup.pygame.event.get", lambda: next(event_batches, [])
    )

    popup.show_loot(
        [SimpleNamespace(name="Potion")],
        flush_events=False,
        require_key_release=False,
    )

    assert render_calls == ["Chest"]


def test_show_empty_chest_and_background_helper(monkeypatch):
    bundle = _make_popup(monkeypatch)
    popup = bundle.popup

    render_calls = []
    monkeypatch.setattr(
        popup, "_render_empty_chest", lambda chest_type: render_calls.append(chest_type)
    )
    event_batches = iter(
        [
            [],
            [SimpleNamespace(type=pygame.MOUSEBUTTONDOWN)],
        ]
    )
    monkeypatch.setattr(
        "src.ui_pygame.gui.loot_popup.pygame.event.get", lambda: next(event_batches, [])
    )
    popup._show_empty_chest("Ancient Chest")
    assert render_calls == ["Ancient Chest", "Ancient Chest"]
    assert bundle.flip_calls
    assert bundle.clocks[0].ticks == [60, 60]

    popup.presenter = SimpleNamespace(get_background_surface=lambda: "bg")
    assert popup._get_background_surface() == "bg"
    popup.presenter = SimpleNamespace(
        get_background_surface=lambda: (_ for _ in ()).throw(RuntimeError("boom"))
    )
    assert popup._get_background_surface() == "screen-copy"


def test_empty_chest_can_wait_for_stale_input_release(monkeypatch):
    bundle = _make_popup(monkeypatch)
    popup = bundle.popup
    clears = []
    render_calls = []
    monkeypatch.setattr(
        "src.ui_pygame.gui.input_guards.pygame.event.clear", lambda: clears.append(True)
    )
    key_states = iter([[1], [1], [], []])
    monkeypatch.setattr("src.ui_pygame.gui.input_guards.pygame.event.pump", lambda: None)
    monkeypatch.setattr(
        "src.ui_pygame.gui.input_guards.pygame.key.get_pressed", lambda: next(key_states, [])
    )
    monkeypatch.setattr(
        popup, "_render_empty_chest", lambda chest_type: render_calls.append(chest_type)
    )
    event_batches = iter(
        [
            [SimpleNamespace(type=pygame.MOUSEBUTTONDOWN)],
            [SimpleNamespace(type=pygame.MOUSEBUTTONUP)],
            [SimpleNamespace(type=pygame.MOUSEBUTTONDOWN)],
        ]
    )
    monkeypatch.setattr(
        "src.ui_pygame.gui.loot_popup.pygame.event.get", lambda: next(event_batches, [])
    )

    popup._show_empty_chest("Chest", flush_events=True, require_key_release=True)

    assert clears == [True]
    assert render_calls == ["Chest", "Chest", "Chest"]


def test_render_loot_popup_item_empty_and_unlock_prompt_branches(monkeypatch):
    bundle = _make_popup(monkeypatch)
    popup = bundle.popup
    render_calls = []
    popup.item_render_manager = SimpleNamespace(
        get_scaled_render=lambda item, size: render_calls.append((getattr(item, "name", ""), size))
        or pygame.surface.Surface(size, pygame.SRCALPHA)
    )

    item = SimpleNamespace(
        name="Mythic Sword",
        rarity=0.05,
        description="Line one\nLine two\nLine three\nLine four",
        value=120,
        damage=9,
        armor=0,
        subtyp="Blade",
    )

    popup.animation_time = 5
    popup._render_loot_popup([item], "Treasure Chest")
    assert "Treasure Chest Opened!" not in bundle.title_font.render_calls

    popup.animation_time = popup.max_animation_time
    popup._render_loot_popup([item], "Treasure Chest")
    assert "Treasure Chest Opened!" in bundle.title_font.render_calls
    assert "Press any key to continue..." in bundle.small_font.render_calls
    popup._render_loot_popup([item], "Mimic Reward")
    assert "Mimic Reward" in bundle.title_font.render_calls
    assert "Mimic Reward Opened!" not in bundle.title_font.render_calls

    y = popup._render_item(item, 10, 20, 300)
    assert y > 20
    assert ("Mythic Sword", (82, 118)) in render_calls
    assert "Mythic Sword" in bundle.item_font.render_calls
    assert "Line one" in bundle.desc_font.render_calls
    assert "Line four" in bundle.desc_font.render_calls
    assert "Value: 120g | Damage: 9 | Armor: 0 | Type: Blade" in bundle.small_font.render_calls

    plain_item = SimpleNamespace(name="Stone")
    popup._render_item(plain_item, 10, 20, 300)
    assert "Stone" in bundle.item_font.render_calls

    popup._render_empty_chest("Chest")
    assert "Empty Chest" in bundle.title_font.render_calls
    assert "The chest contains nothing of value." in bundle.desc_font.render_calls

    popup._render_unlock_prompt("door", ["Use Old Key", "Cancel"], 1)
    assert "Locked!" in bundle.title_font.render_calls
    assert "This door is locked." in bundle.desc_font.render_calls
    assert "Use a Key to unlock it?" in bundle.desc_font.render_calls
    assert "Use Old Key" in bundle.item_font.render_calls
    assert "Arrow Keys: Navigate | Enter: Select | ESC: Cancel" in bundle.small_font.render_calls
    assert bundle.draw_calls

    assert popup._ease_out_back(1.0) == 1.0


def test_show_unlock_prompt_navigation_and_exit_paths(monkeypatch):
    bundle = _make_popup(monkeypatch)
    popup = bundle.popup

    render_calls = []
    monkeypatch.setattr(
        popup,
        "_render_unlock_prompt",
        lambda locked_type, options, selected: render_calls.append(
            (locked_type, tuple(options), selected)
        ),
    )
    monkeypatch.setattr(popup, "_get_background_surface", lambda: "background")

    event_batches = iter(
        [
            [SimpleNamespace(type=pygame.KEYDOWN, key=pygame.K_DOWN)],
            [SimpleNamespace(type=pygame.KEYDOWN, key=pygame.K_UP)],
            [SimpleNamespace(type=pygame.KEYDOWN, key=pygame.K_RETURN)],
        ]
    )
    monkeypatch.setattr(
        "src.ui_pygame.gui.loot_popup.pygame.event.get", lambda: next(event_batches, [])
    )
    assert popup.show_unlock_prompt("door") is True
    assert render_calls[0][1] == ("Use Old Key", "Cancel")
    assert bundle.screen.blit_calls[0] == ("background", (0, 0))

    event_batches = iter(
        [
            [SimpleNamespace(type=pygame.KEYDOWN, key=pygame.K_ESCAPE)],
        ]
    )
    monkeypatch.setattr(
        "src.ui_pygame.gui.loot_popup.pygame.event.get", lambda: next(event_batches, [])
    )
    assert (
        popup.show_unlock_prompt(
            "chest", background_draw_func=lambda: bundle.screen.fill((1, 2, 3))
        )
        is False
    )

    event_batches = iter(
        [
            [SimpleNamespace(type=pygame.QUIT)],
        ]
    )
    monkeypatch.setattr(
        "src.ui_pygame.gui.loot_popup.pygame.event.get", lambda: next(event_batches, [])
    )
    assert popup.show_unlock_prompt("chest") is False


def test_show_unlock_prompt_can_wait_for_stale_input_release(monkeypatch):
    bundle = _make_popup(monkeypatch)
    popup = bundle.popup
    clears = []
    render_calls = []
    monkeypatch.setattr(
        "src.ui_pygame.gui.input_guards.pygame.event.clear", lambda: clears.append(True)
    )
    key_states = iter([[1], [1], [], []])
    monkeypatch.setattr("src.ui_pygame.gui.input_guards.pygame.event.pump", lambda: None)
    monkeypatch.setattr(
        "src.ui_pygame.gui.input_guards.pygame.key.get_pressed", lambda: next(key_states, [])
    )
    monkeypatch.setattr(
        popup,
        "_render_unlock_prompt",
        lambda locked_type, options, selected: render_calls.append((locked_type, selected)),
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
        "src.ui_pygame.gui.loot_popup.pygame.event.get", lambda: next(event_batches, [])
    )

    assert popup.show_unlock_prompt("chest", flush_events=True, require_key_release=True) is False
    assert clears == [True]
    assert render_calls == [("chest", 0), ("chest", 0), ("chest", 1)]

    monkeypatch.setattr("src.ui_pygame.gui.input_guards.pygame.key.get_pressed", lambda: [])
    event_batches = iter([[SimpleNamespace(type=pygame.KEYDOWN, key=pygame.K_RETURN)]])
    monkeypatch.setattr(
        "src.ui_pygame.gui.loot_popup.pygame.event.get", lambda: next(event_batches, [])
    )
    assert popup.show_unlock_prompt("door", flush_events=True, require_key_release=True) is True
