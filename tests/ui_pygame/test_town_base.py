#!/usr/bin/env python3
"""Coverage for shared town-screen pygame helpers."""

from __future__ import annotations

import os
from types import SimpleNamespace

import pygame

from src.ui_pygame.display_scaling import DisplayConfiguration, LayoutMetrics
from src.ui_pygame.gui import town_base

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")


class RecordingScreen:
    def __init__(self):
        self.fill_calls = []
        self.blit_calls = []

    def fill(self, color):
        self.fill_calls.append(color)

    def blit(self, surface, position):
        self.blit_calls.append((surface, position))


class RecordingTownScreen(town_base.TownScreenBase):
    def __init__(self, presenter):
        self.top_calls = 0
        self.options_calls = 0
        self.background_calls = 0
        super().__init__(presenter)

    def draw_background(self):
        self.background_calls += 1
        return super().draw_background()

    def draw_top(self):
        self.top_calls += 1

    def draw_options(self):
        self.options_calls += 1


def _make_presenter(*, debug_mode=False, screen=None):
    pygame.font.init()
    return SimpleNamespace(
        screen=screen or RecordingScreen(),
        width=640,
        height=480,
        title_font=pygame.font.Font(None, 32),
        large_font=pygame.font.Font(None, 24),
        normal_font=pygame.font.Font(None, 22),
        small_font=pygame.font.Font(None, 18),
        debug_mode=debug_mode,
        clock=SimpleNamespace(tick=lambda _fps: None),
    )


def test_load_background_does_not_upscale_low_resolution_art(monkeypatch):
    presenter = _make_presenter()
    source = pygame.Surface((200, 100))
    monkeypatch.setattr("src.ui_pygame.gui.town_base.os.path.exists", lambda _path: True)
    monkeypatch.setattr("src.ui_pygame.gui.town_base.pygame.image.load", lambda _path: source)

    base = town_base.TownScreenBase(presenter)

    assert base.background is source
    assert base._background_is_native_fallback is True


def test_load_background_caches_downscaled_larger_art(monkeypatch):
    presenter = _make_presenter()
    source = pygame.Surface((1280, 960))
    scaled_sizes = []
    monkeypatch.setattr("src.ui_pygame.gui.town_base.os.path.exists", lambda _path: True)
    monkeypatch.setattr("src.ui_pygame.gui.town_base.pygame.image.load", lambda _path: source)

    def fake_smoothscale(image, size):
        scaled_sizes.append((image.get_size(), size))
        return pygame.Surface(size)

    monkeypatch.setattr(
        "src.ui_pygame.gui.town_base.pygame.transform.smoothscale", fake_smoothscale
    )
    base = town_base.TownScreenBase(presenter)

    assert scaled_sizes == [((1280, 960), (640, 480))]
    assert base._background_is_native_fallback is False


def test_load_background_prefers_available_high_resolution_variant(monkeypatch):
    presenter = _make_presenter()
    presenter.layout_metrics = LayoutMetrics(
        DisplayConfiguration.for_viewport(fullscreen=True, render_size=(1920, 1080))
    )
    loaded_paths = []
    source = pygame.Surface((1920, 1080))

    monkeypatch.setattr(
        "src.ui_pygame.gui.town_base.os.path.exists", lambda path: str(path).endswith("town@2x.png")
    )
    monkeypatch.setattr(
        "src.ui_pygame.gui.town_base.pygame.image.load",
        lambda path: loaded_paths.append(str(path)) or source,
    )

    base = town_base.TownScreenBase(presenter)

    assert loaded_paths[-1].endswith("town@2x.png")
    assert base._background_is_native_fallback is False


def test_load_background_handles_missing_and_load_failures(monkeypatch, capsys):
    presenter = _make_presenter()

    monkeypatch.setattr("src.ui_pygame.gui.town_base.os.path.exists", lambda _path: False)
    missing = town_base.TownScreenBase(presenter)
    assert missing.background is None
    assert "Town background not found" in capsys.readouterr().out

    monkeypatch.setattr("src.ui_pygame.gui.town_base.os.path.exists", lambda _path: True)
    monkeypatch.setattr(
        "src.ui_pygame.gui.town_base.pygame.image.load",
        lambda _path: (_ for _ in ()).throw(RuntimeError("boom")),
    )
    failed = town_base.TownScreenBase(presenter)
    assert failed.background is None
    assert "Could not load town background" in capsys.readouterr().out


def test_draw_background_and_panel_helpers(monkeypatch):
    screen = RecordingScreen()
    presenter = _make_presenter(screen=screen)
    monkeypatch.setattr("src.ui_pygame.gui.town_base.os.path.exists", lambda _path: False)
    base = town_base.TownScreenBase(presenter)

    base.draw_background()
    assert screen.fill_calls == [town_base.TownColors.BLACK]

    base.background = pygame.Surface((100, 80))
    base.draw_background()
    _surface, rect = screen.blit_calls[-1]
    assert rect.center == (presenter.width // 2, presenter.height // 2)

    panel = base.draw_semi_transparent_panel(pygame.Rect(10, 20, 30, 40), alpha=123)
    assert panel.get_size() == (30, 40)
    assert screen.blit_calls[-1][1] == (10, 20)


def test_town_colors_provide_light_gray_for_character_screen_hint_text():
    assert town_base.TownColors.LIGHT_GRAY == (192, 192, 192)


def test_wrap_text_to_pixel_width_allows_narrow_text_to_use_full_line():
    pygame.font.init()
    font = pygame.font.Font(None, 24)
    line = " ".join(["iiiiiiiiii"] * 8)

    assert len(line) > 50
    assert town_base.wrap_text_to_pixel_width(line, font, font.size(line)[0]) == [line]


def test_display_quest_text_debug_mode_renders_full_text_and_exits(monkeypatch):
    pygame.init()
    pygame.display.set_mode((1, 1))
    presenter = _make_presenter(debug_mode=True, screen=pygame.Surface((640, 480), pygame.SRCALPHA))
    monkeypatch.setattr("src.ui_pygame.gui.town_base.os.path.exists", lambda _path: False)
    base = RecordingTownScreen(presenter)

    events = [SimpleNamespace(type=pygame.KEYDOWN)]
    monkeypatch.setattr("src.ui_pygame.gui.town_base.pygame.event.get", lambda: list(events))
    monkeypatch.setattr("src.ui_pygame.gui.town_base.pygame.display.flip", lambda: None)

    base.display_quest_text("====== Quest ======\nLine one\n\nLine two")

    assert base.background_calls == 1
    assert base.top_calls == 1
    assert base.options_calls == 1
    pygame.quit()


def test_display_quest_text_debug_mode_draws_npc_portrait(monkeypatch):
    pygame.init()
    pygame.display.set_mode((1, 1))
    presenter = _make_presenter(debug_mode=True, screen=pygame.Surface((640, 480), pygame.SRCALPHA))
    monkeypatch.setattr("src.ui_pygame.gui.town_base.os.path.exists", lambda _path: False)
    base = RecordingTownScreen(presenter)

    loaded_paths = []
    panel_rects = []
    scaled_sizes = []
    portrait = pygame.Surface((512, 768), pygame.SRCALPHA)

    def fake_load(path):
        loaded_paths.append(path)
        return portrait

    def fake_smoothscale(surface, size):
        scaled_sizes.append((surface.get_size(), size))
        return pygame.Surface(size, pygame.SRCALPHA)

    events = [SimpleNamespace(type=pygame.KEYDOWN)]
    monkeypatch.setattr("src.ui_pygame.gui.town_base.pygame.image.load", fake_load)
    monkeypatch.setattr(
        "src.ui_pygame.gui.town_base.pygame.transform.smoothscale", fake_smoothscale
    )
    monkeypatch.setattr("src.ui_pygame.gui.town_base.pygame.event.get", lambda: list(events))
    monkeypatch.setattr("src.ui_pygame.gui.town_base.pygame.display.flip", lambda: None)
    monkeypatch.setattr(
        base, "draw_semi_transparent_panel", lambda rect, alpha=180: panel_rects.append(rect)
    )

    base.display_quest_text("====== Sergeant ======\nLine one", image_path="sergeant.png")

    assert loaded_paths == ["sergeant.png"]
    assert base.dialogue_portrait_rect() in panel_rects
    assert base.dialogue_portrait_rect().left == 0
    assert base.dialogue_portrait_rect().top == presenter.height // 12 + presenter.height // 4
    assert scaled_sizes
    assert scaled_sizes[-1][0] == (512, 768)
    assert scaled_sizes[-1][1][0] <= base.dialogue_portrait_rect().width
    assert scaled_sizes[-1][1][1] <= base.dialogue_portrait_rect().height
    pygame.quit()


def test_display_quest_text_debug_mode_exits_on_left_click(monkeypatch):
    pygame.init()
    pygame.display.set_mode((1, 1))
    presenter = _make_presenter(debug_mode=True, screen=pygame.Surface((640, 480), pygame.SRCALPHA))
    monkeypatch.setattr("src.ui_pygame.gui.town_base.os.path.exists", lambda _path: False)
    base = RecordingTownScreen(presenter)

    events = [SimpleNamespace(type=pygame.MOUSEBUTTONDOWN, button=1, pos=(320, 240))]
    monkeypatch.setattr("src.ui_pygame.gui.town_base.pygame.event.get", lambda: list(events))
    monkeypatch.setattr("src.ui_pygame.gui.town_base.pygame.display.flip", lambda: None)

    base.display_quest_text("====== Quest ======\nLine one\n\nLine two")

    assert base.background_calls == 1
    assert base.top_calls == 1
    assert base.options_calls == 1
    pygame.quit()


def test_display_quest_text_non_debug_supports_skip_and_advance(monkeypatch):
    pygame.init()
    pygame.display.set_mode((1, 1))
    presenter = _make_presenter(
        debug_mode=False, screen=pygame.Surface((640, 480), pygame.SRCALPHA)
    )
    monkeypatch.setattr("src.ui_pygame.gui.town_base.os.path.exists", lambda _path: False)
    base = RecordingTownScreen(presenter)

    key_events = iter(
        [
            [SimpleNamespace(type=pygame.KEYDOWN, key=pygame.K_SPACE)],
            [SimpleNamespace(type=pygame.KEYDOWN, key=pygame.K_RETURN)],
        ]
    )

    def fake_get():
        try:
            return next(key_events)
        except StopIteration:
            return []

    clear_calls = []
    tick_calls = []
    presenter.clock = SimpleNamespace(tick=lambda fps: tick_calls.append(fps))
    monkeypatch.setattr("src.ui_pygame.gui.town_base.pygame.event.get", fake_get)
    monkeypatch.setattr(
        "src.ui_pygame.gui.town_base.pygame.event.clear",
        lambda event_type=None: clear_calls.append(event_type),
    )
    monkeypatch.setattr("src.ui_pygame.gui.town_base.pygame.display.flip", lambda: None)
    monkeypatch.setattr("time.sleep", lambda _value: None)

    base.display_quest_text("====== Quest ======\nSkip me quickly\n\nThen show this too")

    assert clear_calls == [pygame.KEYDOWN]
    assert base.background_calls >= 2
    assert base.top_calls >= 2
    assert base.options_calls >= 2
    assert tick_calls == []
    pygame.quit()


def test_display_quest_text_non_debug_keeps_full_text_width_with_portrait(monkeypatch):
    pygame.init()
    pygame.display.set_mode((1, 1))
    presenter = _make_presenter(
        debug_mode=False, screen=pygame.Surface((640, 480), pygame.SRCALPHA)
    )
    monkeypatch.setattr("src.ui_pygame.gui.town_base.os.path.exists", lambda _path: False)
    base = RecordingTownScreen(presenter)

    portrait = pygame.Surface((512, 768), pygame.SRCALPHA)
    monkeypatch.setattr("src.ui_pygame.gui.town_base.pygame.image.load", lambda _path: portrait)
    monkeypatch.setattr(
        "src.ui_pygame.gui.town_base.pygame.transform.smoothscale",
        lambda _surface, size: pygame.Surface(size, pygame.SRCALPHA),
    )

    wrap_widths = []

    def fake_wrap(raw_line, font, max_width):
        wrap_widths.append(max_width)
        return ["wrapped"]

    monkeypatch.setattr(town_base, "wrap_text_to_pixel_width", fake_wrap)
    monkeypatch.setattr(
        "src.ui_pygame.gui.town_base.pygame.event.clear", lambda event_type=None: None
    )
    monkeypatch.setattr("src.ui_pygame.gui.town_base.pygame.display.flip", lambda: None)
    monkeypatch.setattr("time.sleep", lambda _value: None)

    def show_dialogue(*, image_path=""):
        key_events = iter(
            [
                [SimpleNamespace(type=pygame.KEYDOWN, key=pygame.K_SPACE)],
                [SimpleNamespace(type=pygame.KEYDOWN, key=pygame.K_RETURN)],
            ]
        )
        monkeypatch.setattr(
            "src.ui_pygame.gui.town_base.pygame.event.get", lambda: next(key_events, [])
        )
        base.display_quest_text(
            "====== Sergeant ======\nThis is a longer portrait dialogue line.",
            image_path=image_path,
        )

    show_dialogue()
    no_portrait_width = wrap_widths[-1]
    show_dialogue(image_path="sergeant.png")

    assert wrap_widths
    assert wrap_widths[-1] == no_portrait_width
    pygame.quit()


def test_display_quest_text_non_debug_supports_mouse_skip_and_advance(monkeypatch):
    pygame.init()
    pygame.display.set_mode((1, 1))
    presenter = _make_presenter(
        debug_mode=False, screen=pygame.Surface((640, 480), pygame.SRCALPHA)
    )
    monkeypatch.setattr("src.ui_pygame.gui.town_base.os.path.exists", lambda _path: False)
    base = RecordingTownScreen(presenter)

    mouse_events = iter(
        [
            [SimpleNamespace(type=pygame.MOUSEBUTTONDOWN, button=1, pos=(320, 240))],
            [SimpleNamespace(type=pygame.MOUSEBUTTONDOWN, button=1, pos=(320, 240))],
        ]
    )

    def fake_get():
        try:
            return next(mouse_events)
        except StopIteration:
            return []

    clear_calls = []
    tick_calls = []
    presenter.clock = SimpleNamespace(tick=lambda fps: tick_calls.append(fps))
    monkeypatch.setattr("src.ui_pygame.gui.town_base.pygame.event.get", fake_get)
    monkeypatch.setattr(
        "src.ui_pygame.gui.town_base.pygame.event.clear",
        lambda event_type=None: clear_calls.append(event_type),
    )
    monkeypatch.setattr("src.ui_pygame.gui.town_base.pygame.display.flip", lambda: None)
    monkeypatch.setattr("time.sleep", lambda _value: None)

    base.display_quest_text("====== Quest ======\nClick me quickly")

    assert clear_calls == [pygame.KEYDOWN]
    assert base.background_calls >= 2
    assert base.top_calls >= 2
    assert base.options_calls >= 2
    assert tick_calls == []
    pygame.quit()
