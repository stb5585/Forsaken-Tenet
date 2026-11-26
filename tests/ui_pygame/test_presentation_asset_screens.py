#!/usr/bin/env python3
"""Focused coverage for presentation/asset gate pygame screens."""

from __future__ import annotations

from types import SimpleNamespace

import pygame
import pytest

from src.ui_pygame.gui import presentation_asset_screens


@pytest.fixture(autouse=True)
def _init_pygame():
    if not pygame.get_init():
        pygame.init()
    if not pygame.font.get_init():
        pygame.font.init()
    yield


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
    def __init__(self, height=22):
        self.render_calls = []
        self._height = height

    def render(self, text, _antialias, _color):
        self.render_calls.append(text)
        return DummySurface((max(8, len(str(text)) * 8), self._height), text=text)

    def size(self, text):
        return (max(8, len(str(text)) * 8), self._height)

    def get_height(self):
        return self._height


class RecordingScreen:
    def __init__(self, size=(900, 700)):
        self._size = size
        self.fill_calls = []
        self.blit_calls = []

    def fill(self, color):
        self.fill_calls.append(color)

    def blit(self, surface, position):
        self.blit_calls.append((surface, position))


def _make_presenter():
    return SimpleNamespace(
        screen=RecordingScreen(),
        width=900,
        height=700,
        title_font=RecordingFont(34),
        large_font=RecordingFont(28),
        normal_font=RecordingFont(22),
        small_font=RecordingFont(18),
        clock=SimpleNamespace(tick=lambda _fps: None),
    )


def _patch_drawing(monkeypatch):
    monkeypatch.setattr(
        "src.ui_pygame.gui.presentation_asset_screens.pygame.draw.rect", lambda *_a, **_k: None
    )
    monkeypatch.setattr(
        "src.ui_pygame.gui.presentation_asset_screens.pygame.draw.line", lambda *_a, **_k: None
    )
    monkeypatch.setattr(
        "src.ui_pygame.gui.presentation_asset_screens.pygame.display.flip", lambda: None
    )


def test_character_created_screen_draws_summary_and_accepts_keyboard(monkeypatch):
    _patch_drawing(monkeypatch)
    presenter = _make_presenter()
    portrait = pygame.Surface((225, 400), pygame.SRCALPHA)
    player = SimpleNamespace(
        name="Ada",
        race=SimpleNamespace(name="Elf"),
        sex="Female",
        cls=SimpleNamespace(name="Mage"),
        portrait_variant=2,
        health=SimpleNamespace(max=42),
        mana=SimpleNamespace(max=31),
        equipment={"OffHand": SimpleNamespace(typ="Armor")},
        check_mod=lambda mod: {
            "weapon": 14,
            "armor": 9,
            "magic": 18,
            "magic def": 11,
            "shield": 12,
            "speed": 7,
        }[mod],
        critical_chance=lambda _attack_type: 0.075,
    )
    manager = SimpleNamespace(get_portrait=lambda *args, **kwargs: portrait)
    screen = presentation_asset_screens.CharacterCreatedScreen(
        presenter, player, portrait_manager=manager
    )

    screen.draw()

    rendered = (
        presenter.title_font.render_calls
        + presenter.large_font.render_calls
        + presenter.normal_font.render_calls
        + presenter.small_font.render_calls
    )
    assert "Character Created" in rendered
    assert "Ada" in rendered
    assert "Elf" in rendered
    assert "Female" in rendered
    assert "Mage" in rendered
    assert "42" in rendered
    assert "31" in rendered
    assert "Combat Stats" in rendered
    assert "Attack" in rendered
    assert "Magic Defense" in rendered
    assert "14" in rendered
    assert "7.5%" in rendered
    assert "12%" in rendered
    assert all("Progression Point" not in text for text in rendered)

    event_batches = iter([[SimpleNamespace(type=pygame.KEYDOWN, key=pygame.K_RETURN)]])
    monkeypatch.setattr(
        "src.ui_pygame.gui.presentation_asset_screens.pygame.event.get",
        lambda: next(event_batches, []),
    )

    assert screen.show() is True


def test_character_created_screen_survives_portrait_fallback(monkeypatch):
    _patch_drawing(monkeypatch)
    presenter = _make_presenter()
    player = SimpleNamespace(
        name="Hero",
        race="Human",
        sex="Male",
        cls="Warrior",
        health=SimpleNamespace(max=20),
        mana=SimpleNamespace(max=10),
    )
    fallback = pygame.Surface((225, 400), pygame.SRCALPHA)
    manager = SimpleNamespace(
        get_portrait=lambda *args, **kwargs: (_ for _ in ()).throw(
            pygame.error("missing composed portrait")
        ),
        base_portrait=lambda *args, **kwargs: fallback,
    )
    screen = presentation_asset_screens.CharacterCreatedScreen(
        presenter, player, portrait_manager=manager
    )

    screen.draw()

    assert screen.portrait is fallback
    assert presenter.screen.blit_calls


def test_story_card_sequence_advances_with_keyboard_mouse_and_can_skip(monkeypatch):
    _patch_drawing(monkeypatch)
    presenter = _make_presenter()
    sequence = presentation_asset_screens.StoryCardSequence(
        presenter,
        ["First page of the story.", "Second page of the story."],
        title="The Story Begins",
    )

    event_batches = iter(
        [
            [SimpleNamespace(type=pygame.KEYDOWN, key=pygame.K_SPACE)],
            [SimpleNamespace(type=pygame.KEYDOWN, key=pygame.K_SPACE)],
            [SimpleNamespace(type=pygame.MOUSEBUTTONDOWN, button=1, pos=(40, 40))],
            [SimpleNamespace(type=pygame.MOUSEBUTTONDOWN, button=1, pos=(450, 620))],
        ]
    )
    monkeypatch.setattr(
        "src.ui_pygame.gui.presentation_asset_screens.pygame.event.get",
        lambda: next(event_batches, []),
    )

    assert sequence.show() is True
    assert sequence.page_index == 1
    assert "The Story Begins" not in presenter.title_font.render_calls
    assert "1/2" not in presenter.small_font.render_calls
    assert "2/2" not in presenter.small_font.render_calls
    assert "Click to reveal this passage" not in presenter.small_font.render_calls
    assert "Click to continue" not in presenter.small_font.render_calls
    assert "First page of the story." in presenter.large_font.render_calls
    assert "Second page of the story." in presenter.large_font.render_calls

    skip_sequence = presentation_asset_screens.StoryCardSequence(
        presenter, ["Only page"], title="Skip Me"
    )
    event_batches = iter([[SimpleNamespace(type=pygame.KEYDOWN, key=pygame.K_ESCAPE)]])
    monkeypatch.setattr(
        "src.ui_pygame.gui.presentation_asset_screens.pygame.event.get",
        lambda: next(event_batches, []),
    )

    assert skip_sequence.show() is False


def test_story_card_sequence_uses_configured_reveal_speed():
    presenter = _make_presenter()
    presenter.story_dialogue_cps = 12
    sequence = presentation_asset_screens.StoryCardSequence(
        presenter,
        ["A passage revealed one character at a time."],
    )
    sequence._page_started_ms = 1000

    assert sequence._visible_character_count(1500) == 6
    sequence._page_complete = True
    assert sequence._visible_character_count(1500) == len(
        sequence._wrapped_story_text(sequence.pages[0])
    )


def test_story_card_sequence_wraps_complete_words_before_revealing():
    presenter = _make_presenter()
    presenter.width = 180
    presenter.screen = RecordingScreen((180, 700))
    sequence = presentation_asset_screens.StoryCardSequence(
        presenter,
        ["Alpha beta gamma"],
    )

    wrapped = sequence._wrapped_story_text(sequence.pages[0])

    assert wrapped == "Alpha beta\ngamma"
    assert wrapped[:12].splitlines() == ["Alpha beta", "g"]


def test_story_card_sequence_fades_each_card_in_and_out(monkeypatch):
    _patch_drawing(monkeypatch)
    presenter = _make_presenter()
    sequence = presentation_asset_screens.StoryCardSequence(
        presenter,
        ["First page.", "Second page."],
    )
    fades = []
    monkeypatch.setattr(
        sequence,
        "_fade_in",
        lambda duration: fades.append(("in", sequence.page_index, duration)),
    )
    monkeypatch.setattr(
        sequence,
        "_fade_out",
        lambda duration: fades.append(("out", sequence.page_index, duration)),
    )
    event_batches = iter(
        [
            [SimpleNamespace(type=pygame.KEYDOWN, key=pygame.K_SPACE)],
            [SimpleNamespace(type=pygame.KEYDOWN, key=pygame.K_SPACE)],
            [SimpleNamespace(type=pygame.KEYDOWN, key=pygame.K_SPACE)],
            [SimpleNamespace(type=pygame.KEYDOWN, key=pygame.K_SPACE)],
        ]
    )
    monkeypatch.setattr(
        "src.ui_pygame.gui.presentation_asset_screens.pygame.event.get",
        lambda: next(event_batches, []),
    )

    assert sequence.show(fade_in_ms=300) is True
    assert fades == [
        ("in", 0, 300),
        ("out", 0, 300),
        ("in", 1, 300),
        ("out", 1, 300),
    ]


def test_fade_to_black_rejects_negative_durations():
    presenter = _make_presenter()

    with pytest.raises(ValueError, match="durations"):
        presentation_asset_screens.fade_to_black(presenter, duration_ms=-1)


def test_intro_story_images_are_complete_landscape_set():
    paths = presentation_asset_screens.INTRO_STORY_IMAGE_PATHS

    assert len(paths) == 6
    for path in paths:
        assert path.exists()
        assert pygame.image.load(str(path)).get_size() == (1280, 720)

    assert presentation_asset_screens.DUNGEON_ENTRY_IMAGE_PATHS[0].exists()
    assert pygame.image.load(
        str(presentation_asset_screens.DUNGEON_ENTRY_IMAGE_PATHS[0])
    ).get_size() == (1280, 720)
