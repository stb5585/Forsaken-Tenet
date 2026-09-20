#!/usr/bin/env python3
"""Focused coverage for the load-game screen helpers."""

from __future__ import annotations

from types import SimpleNamespace

import pygame

from src.ui_pygame.gui import load_game


class DummySurface:
    def __init__(self, size=(64, 24), text=None):
        self._size = size
        self.text = text

    def get_width(self):
        return self._size[0]

    def get_height(self):
        return self._size[1]

    def get_size(self):
        return self._size

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
    def __init__(self, size=(800, 600)):
        self._size = size
        self.blit_calls = []
        self.fill_calls = []

    def fill(self, color):
        self.fill_calls.append(color)

    def blit(self, surface, position):
        self.blit_calls.append((surface, position))

    def copy(self):
        return DummySurface(self._size, text="screen-copy")


def _make_presenter():
    return SimpleNamespace(
        screen=RecordingScreen(),
        width=800,
        height=600,
        title_font=RecordingFont(),
        normal_font=RecordingFont(),
        small_font=RecordingFont(),
        clock=SimpleNamespace(tick=lambda _fps: None),
    )


def _valid_save_metadata(filename, *, empty=False):
    return {
        "filename": filename,
        "valid": True,
        "extension_matches_expected": True,
        "is_file": True,
        "empty": empty,
    }


def test_load_game_draw_helpers_and_data_loading(monkeypatch):
    presenter = _make_presenter()
    portrait_calls = []

    class FakePortraitManager:
        def get_portrait(self, *args, **kwargs):
            portrait_calls.append((args, kwargs))
            return DummySurface((90, 160), text="portrait")

    monkeypatch.setattr(load_game, "PortraitManager", FakePortraitManager)
    monkeypatch.setattr(
        load_game.pygame.transform,
        "smoothscale",
        lambda surface, size: DummySurface(size, text="scaled-portrait"),
    )
    screen = load_game.LoadGameScreen(presenter)

    draw_calls = []
    monkeypatch.setattr(
        "src.ui_pygame.gui.load_game.pygame.draw.rect",
        lambda *_args, **_kwargs: draw_calls.append((_args, _kwargs)),
    )
    flip_calls = []
    monkeypatch.setattr(
        "src.ui_pygame.gui.load_game.pygame.display.flip", lambda: flip_calls.append(True)
    )

    player_a = SimpleNamespace(
        name="hero",
        race=SimpleNamespace(name="Human"),
        sex="Female",
        cls=SimpleNamespace(name="Warrior"),
        level=SimpleNamespace(level=5, exp=123),
        gold=77,
        stats=SimpleNamespace(strength=10, intel=9, wisdom=8, con=11, charisma=7, dex=6),
        portrait_variant=3,
    )
    player_b = None

    def fake_load_player(path):
        if path == "a.save":
            return player_a
        if path == "b.save":
            return player_b
        raise RuntimeError("broken")

    def fake_describe_save_file(filename):
        metadata = _valid_save_metadata(filename, empty=filename == "empty.save")
        if filename == "../bad.save":
            metadata["valid"] = False
            metadata["is_file"] = False
        return metadata

    monkeypatch.setattr(
        load_game.SaveManager, "describe_save_file", staticmethod(fake_describe_save_file)
    )
    monkeypatch.setattr(load_game.SaveManager, "load_player", staticmethod(fake_load_player))
    screen.load_save_files(["a.save", "b.save", "c.save"])

    assert screen.save_data[0]["name"] == "Hero"
    assert screen.save_data[0]["loadable"] is True
    assert screen.save_data[0]["sex"] == "Female"
    assert screen.save_data[0]["portrait_variant"] == 3
    assert screen.save_data[0]["stats"]["STR"] == 10
    assert screen.save_data[1]["name"] == "Corrupted save"
    assert screen.save_data[1]["loadable"] is False
    assert screen.save_data[2]["name"] == "Error loading"
    assert screen.save_data[2]["loadable"] is False

    screen.draw_header()
    assert "Choose the character to load" in presenter.normal_font.render_calls

    screen.current_selection = 0
    screen.draw_char_info()
    assert portrait_calls[-1][0][:2] == ("Human", "Female")
    assert portrait_calls[-1][1]["variant"] == 3
    assert any(
        getattr(surface, "text", None) == "scaled-portrait"
        for surface, _pos in presenter.screen.blit_calls
    )
    assert "Level: 5" in presenter.small_font.render_calls
    assert "Race: Human" in presenter.small_font.render_calls
    assert "Sex: Female" in presenter.small_font.render_calls
    assert "Class: Warrior" in presenter.small_font.render_calls
    assert "Experience: 123" in presenter.small_font.render_calls
    assert "Gold: 77" in presenter.small_font.render_calls
    assert "Stats:" in presenter.small_font.render_calls
    assert "STR: 10" in presenter.small_font.render_calls

    screen.draw_file_list()
    assert "Save Files" in presenter.small_font.render_calls
    assert "Hero (Lvl 5)" in presenter.small_font.render_calls
    assert "DEL/BACKSPACE: Delete selected save" in presenter.small_font.render_calls

    screen.load_save_files(["empty.save", "../bad.save"])
    assert screen.save_data[0]["name"] == "Corrupted save"
    assert screen.save_data[0]["loadable"] is False
    assert screen.save_data[1]["name"] == "Invalid save"
    assert screen.save_data[1]["loadable"] is False

    screen.save_data = []
    screen.draw_file_list()
    assert "No save files found" in presenter.normal_font.render_calls

    screen.save_data = [
        {"name": "Hero", "level": 5, "race": "Human", "class": "Warrior", "file": "a.save"}
    ]
    screen.current_selection = 0
    screen.draw_all()
    assert presenter.screen.fill_calls
    assert flip_calls
    assert draw_calls


def test_load_game_lists_incompatible_save_with_schema_explanation(monkeypatch):
    presenter = _make_presenter()
    screen = load_game.LoadGameScreen(presenter)
    load_calls = []
    monkeypatch.setattr(
        load_game.SaveManager,
        "describe_save_file",
        staticmethod(
            lambda filename: {
                **_valid_save_metadata(filename),
                "loadable": False,
                "compatibility_status": "pre_foundation",
                "status_message": "Start a new game after the foundational update.",
            }
        ),
    )
    monkeypatch.setattr(
        load_game.SaveManager,
        "load_player",
        staticmethod(lambda filename: load_calls.append(filename)),
    )

    screen.load_save_files(["legacy.save"])

    assert load_calls == []
    assert screen.save_data == [
        {
            "name": "Incompatible save",
            "race": "?",
            "sex": "?",
            "class": "?",
            "level": "?",
            "file": "legacy.save",
            "loadable": False,
            "status_message": "Start a new game after the foundational update.",
        }
    ]


def test_load_game_navigation_selects_and_cancels(monkeypatch):
    presenter = _make_presenter()
    screen = load_game.LoadGameScreen(presenter)
    screen.save_data = [
        {"name": "Hero", "level": 5, "file": "a.save"},
        {"name": "Mage", "level": 3, "file": "b.save"},
    ]
    screen.save_files = ["a.save", "b.save"]
    monkeypatch.setattr(screen, "load_save_files", lambda _save_files: None)
    monkeypatch.setattr(screen, "draw_all", lambda: None)

    event_batches = iter(
        [
            [SimpleNamespace(type=pygame.KEYDOWN, key=pygame.K_DOWN)],
            [SimpleNamespace(type=pygame.KEYDOWN, key=pygame.K_RETURN)],
        ]
    )
    monkeypatch.setattr(
        "src.ui_pygame.gui.load_game.pygame.event.get", lambda: next(event_batches, [])
    )
    assert screen.navigate(["a.save", "b.save"]) == "b.save"

    screen.current_selection = 0
    event_batches = iter(
        [
            [SimpleNamespace(type=pygame.KEYDOWN, key=pygame.K_ESCAPE)],
        ]
    )
    monkeypatch.setattr(
        "src.ui_pygame.gui.load_game.pygame.event.get", lambda: next(event_batches, [])
    )
    assert screen.navigate(["a.save", "b.save"]) is None

    clear_calls = []
    pressed_states = iter([[], []])
    monkeypatch.setattr(
        "src.ui_pygame.gui.input_guards.pygame.key.get_pressed", lambda: next(pressed_states, [])
    )
    event_batches = iter(
        [
            [SimpleNamespace(type=pygame.KEYDOWN, key=pygame.K_DOWN)],
            [SimpleNamespace(type=pygame.KEYDOWN, key=pygame.K_RETURN)],
        ]
    )
    monkeypatch.setattr(
        "src.ui_pygame.gui.load_game.pygame.event.get", lambda: next(event_batches, [])
    )
    monkeypatch.setattr(
        "src.ui_pygame.gui.load_game.pygame.event.clear", lambda: clear_calls.append(True)
    )
    assert (
        screen.navigate(["a.save", "b.save"], flush_events=True, require_key_release=True)
        == "b.save"
    )
    assert clear_calls == [True]

    screen.current_selection = 0
    monkeypatch.setattr("src.ui_pygame.gui.input_guards.pygame.key.get_pressed", lambda: [])
    event_batches = iter([[SimpleNamespace(type=pygame.KEYDOWN, key=pygame.K_RETURN)]])
    monkeypatch.setattr(
        "src.ui_pygame.gui.load_game.pygame.event.get", lambda: next(event_batches, [])
    )
    assert (
        screen.navigate(["a.save", "b.save"], flush_events=True, require_key_release=True)
        == "a.save"
    )

    screen.current_selection = 0
    click_pos = screen.save_row_rects()[1].center
    event_batches = iter(
        [
            [SimpleNamespace(type=pygame.MOUSEMOTION, pos=click_pos)],
            [SimpleNamespace(type=pygame.MOUSEBUTTONDOWN, button=1, pos=click_pos)],
        ]
    )
    monkeypatch.setattr(
        "src.ui_pygame.gui.load_game.pygame.event.get", lambda: next(event_batches, [])
    )
    assert screen.navigate(["a.save", "b.save"]) == "b.save"


def test_load_game_scrolls_visible_save_window(monkeypatch):
    presenter = _make_presenter()
    screen = load_game.LoadGameScreen(presenter)
    screen.save_data = [
        {"name": f"Hero {index}", "level": index, "file": f"{index}.save"} for index in range(14)
    ]
    screen.save_files = [entry["file"] for entry in screen.save_data]
    monkeypatch.setattr(screen, "load_save_files", lambda _save_files: None)
    monkeypatch.setattr(screen, "draw_all", lambda: None)

    event_batches = iter(
        [[SimpleNamespace(type=pygame.KEYDOWN, key=pygame.K_DOWN)] for _index in range(11)]
        + [[SimpleNamespace(type=pygame.KEYDOWN, key=pygame.K_RETURN)]]
    )
    monkeypatch.setattr(
        "src.ui_pygame.gui.load_game.pygame.event.get", lambda: next(event_batches, [])
    )

    assert screen.navigate(screen.save_files) == "11.save"
    assert screen.current_selection == 11
    assert screen.scroll_offset == 11 - screen.max_visible_saves() + 1
    assert screen.visible_save_data()[0]["file"] == f"{screen.scroll_offset}.save"

    click_pos = screen.save_row_rects()[3].center
    event_batches = iter(
        [
            [SimpleNamespace(type=pygame.MOUSEBUTTONDOWN, button=1, pos=click_pos)],
        ]
    )
    monkeypatch.setattr(
        "src.ui_pygame.gui.load_game.pygame.event.get", lambda: next(event_batches, [])
    )

    assert screen.navigate(screen.save_files) == f"{screen.scroll_offset + 3}.save"


def test_load_game_rows_use_touch_target_height(monkeypatch):
    presenter = _make_presenter()
    presenter.width, presenter.height = (1920, 1080)
    screen = load_game.LoadGameScreen(presenter)
    screen.save_data = [{"name": "Hero", "level": 1, "file": "hero.save"}]

    assert screen.save_row_rects()[0].height >= 70
    assert screen.max_visible_saves() <= 10


def test_load_game_navigation_deletes_selected_save(monkeypatch):
    presenter = _make_presenter()
    screen = load_game.LoadGameScreen(presenter)
    monkeypatch.setattr(screen, "draw_all", lambda: None)
    monkeypatch.setattr(
        load_game.SaveManager,
        "describe_save_file",
        staticmethod(_valid_save_metadata),
    )
    monkeypatch.setattr(
        load_game.SaveManager,
        "load_player",
        staticmethod(
            lambda filename: SimpleNamespace(
                name=filename.removesuffix(".save"),
                race=SimpleNamespace(name="Human"),
                cls=SimpleNamespace(name="Warrior"),
                level=SimpleNamespace(level=1, exp=0),
                gold=0,
            )
        ),
    )

    deleted = []
    monkeypatch.setattr(
        load_game.SaveManager,
        "delete_save",
        staticmethod(lambda filename: deleted.append(filename) or True),
    )

    popup_messages = []

    class FakePopup:
        def __init__(self, _presenter, message, show_buttons=True):
            popup_messages.append((message, show_buttons))

        def show(self, **kwargs):
            assert kwargs["flush_events"] is True
            assert kwargs["require_key_release"] is True
            kwargs["background_draw_func"]()
            return True

    monkeypatch.setattr(load_game, "ConfirmationPopup", FakePopup)
    monkeypatch.setattr("src.ui_pygame.gui.input_guards.pygame.key.get_pressed", lambda: [])
    event_batches = iter(
        [
            [SimpleNamespace(type=pygame.KEYDOWN, key=pygame.K_DELETE)],
            [SimpleNamespace(type=pygame.KEYDOWN, key=pygame.K_RETURN)],
        ]
    )
    monkeypatch.setattr(
        "src.ui_pygame.gui.load_game.pygame.event.get", lambda: next(event_batches, [])
    )

    assert (
        screen.navigate(["a.save", "b.save"], flush_events=True, require_key_release=True)
        == "b.save"
    )
    assert deleted == ["a.save"]
    assert popup_messages == [("Delete a.save? This cannot be undone.", True)]


def test_load_game_navigation_warns_for_unloadable_save_without_returning(monkeypatch):
    presenter = _make_presenter()
    screen = load_game.LoadGameScreen(presenter)
    monkeypatch.setattr(screen, "draw_all", lambda: None)
    monkeypatch.setattr(
        load_game.SaveManager,
        "describe_save_file",
        staticmethod(
            lambda filename: _valid_save_metadata(filename, empty=filename == "empty.save")
        ),
    )
    monkeypatch.setattr(
        load_game.SaveManager,
        "load_player",
        staticmethod(
            lambda filename: (
                SimpleNamespace(
                    name="hero",
                    race=SimpleNamespace(name="Human"),
                    cls=SimpleNamespace(name="Warrior"),
                    level=SimpleNamespace(level=1, exp=0),
                    gold=0,
                )
                if filename == "hero.save"
                else None
            )
        ),
    )

    popup_messages = []

    class FakePopup:
        def __init__(self, _presenter, message, show_buttons=True):
            popup_messages.append((message, show_buttons))

        def show(self, **kwargs):
            assert kwargs["flush_events"] is True
            assert kwargs["require_key_release"] is True
            kwargs["background_draw_func"]()
            return True

    monkeypatch.setattr(load_game, "ConfirmationPopup", FakePopup)
    monkeypatch.setattr("src.ui_pygame.gui.input_guards.pygame.key.get_pressed", lambda: [])
    event_batches = iter(
        [
            [SimpleNamespace(type=pygame.KEYDOWN, key=pygame.K_RETURN)],
            [SimpleNamespace(type=pygame.KEYDOWN, key=pygame.K_DOWN)],
            [SimpleNamespace(type=pygame.KEYDOWN, key=pygame.K_RETURN)],
        ]
    )
    monkeypatch.setattr(
        "src.ui_pygame.gui.load_game.pygame.event.get", lambda: next(event_batches, [])
    )

    assert (
        screen.navigate(["empty.save", "hero.save"], flush_events=True, require_key_release=True)
        == "hero.save"
    )
    assert popup_messages == [
        ("empty.save cannot be loaded.\n\nUse DEL/BACKSPACE to delete it.", False)
    ]
