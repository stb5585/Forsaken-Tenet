#!/usr/bin/env python3
"""Focused coverage for pygame combat-view helpers and overlays."""

from __future__ import annotations

import sys
from pathlib import Path
from types import SimpleNamespace

import pygame
import pytest

sys.path.insert(0, str(Path(__file__).parents[2]))

from src.core.combat import CombatEncounter, EnemyResolution
from src.ui_pygame.assets.enemy_combat_sprite_manager import EnemyCombatSpriteManager
from src.ui_pygame.gui import combat_view
from src.ui_pygame.gui.combat_view.animator import DEATH_ANIMATION_FRAMES
from src.ui_pygame.gui.status_icons import (
    STATUS_ICON_COLORS,
    combine_duplicate_status_icons,
    fit_status_icon_label,
    prioritize_status_icons,
    status_icon_color,
)
from tests.test_framework import TestGameState


@pytest.fixture(autouse=True)
def _init_pygame():
    if not pygame.get_init():
        pygame.init()
    if not pygame.font.get_init():
        pygame.font.init()
    yield


class DummyScreen:
    def __init__(self, size=(900, 600)):
        self._size = size
        self.blit_calls = []
        self.fill_calls = []

    def get_width(self):
        return self._size[0]

    def get_height(self):
        return self._size[1]

    def blit(self, surface, position, *args, **kwargs):
        self.blit_calls.append((surface, position, args, kwargs))

    def fill(self, color, rect=None):
        self.fill_calls.append((color, rect))

    def copy(self):
        return DummySurface(self._size)


class DummySurface:
    def __init__(self, size=(64, 64), text=None):
        self._size = size
        self.text = text
        self.alpha = None
        self.fill_calls = []
        self.blit_calls = []

    def get_size(self):
        return self._size

    def copy(self):
        return DummySurface(self._size, self.text)

    def get_width(self):
        return self._size[0]

    def get_height(self):
        return self._size[1]

    def set_alpha(self, value):
        self.alpha = value

    def fill(self, color):
        self.fill_calls.append(color)

    def blit(self, surface, position, *args, **kwargs):
        self.blit_calls.append((surface, position, args, kwargs))

    def get_rect(self, **kwargs):
        rect = pygame.Rect(0, 0, *self._size)
        for key, value in kwargs.items():
            setattr(rect, key, value)
        return rect

    def convert_alpha(self):
        return self


class RecordingFont:
    def __init__(self):
        self.render_calls = []
        self.color_calls = []

    def size(self, text):
        return (max(8, len(text) * 8), 20)

    def render(self, text, _antialias, _color):
        self.render_calls.append(text)
        self.color_calls.append((text, _color))
        return DummySurface((max(8, len(text) * 8), 20), text=text)


class DummyClock:
    def __init__(self, frame_ms=80):
        self.frame_ms = frame_ms
        self.ticks = []

    def tick(self, fps):
        self.ticks.append(fps)

    def get_time(self):
        return self.frame_ms


@pytest.mark.parametrize("size", [(1024, 720), (1024, 768)])
def test_two_enemy_cards_fit_supported_layout_and_expose_hitboxes(size):
    screen = pygame.Surface(size)
    view = combat_view.CombatView(screen, SimpleNamespace())
    player = TestGameState.create_player(name="Hero")
    first = TestGameState.create_player(name="Goblin")
    second = TestGameState.create_player(name="Goblin")
    encounter = CombatEncounter.from_enemies(
        [first, second],
        combatant_ids=("first", "second"),
    )

    view.render_encounter_in_dungeon(
        player,
        encounter,
        focus_target_id="second",
        details_by_id={"first": False, "second": False},
    )

    assert set(view._enemy_card_rects) == {"first", "second"}
    assert all(rect.bottom <= size[1] - 158 for rect in view._enemy_card_rects.values())
    assert view.enemy_card_at(view._enemy_card_rects["first"].center) == "first"
    assert encounter.members[0].display_label == "Goblin A"


def test_two_enemy_target_uses_arrow_without_selection_plate():
    screen = pygame.Surface((1024, 720))
    screen.fill((210, 160, 20))
    view = combat_view.CombatView(screen, SimpleNamespace())
    player = TestGameState.create_player(name="Hero")
    encounter = CombatEncounter.from_enemies(
        [
            TestGameState.create_player(name="Goblin"),
            TestGameState.create_player(name="Zombie"),
        ],
        combatant_ids=("first", "second"),
    )

    view.render_encounter_in_dungeon(
        player,
        encounter,
        focus_target_id="second",
        details_by_id={"first": True, "second": True},
    )

    second_lane = view._enemy_card_rects["second"]
    plate_sample = (second_lane.left + 10, second_lane.top + 5)
    assert screen.get_at(plate_sample)[:3] != (18, 18, 24)
    target_rect = view._enemy_target_rects["second"]
    marker_y = max(second_lane.top + 44, target_rect.top - 18)
    marker_sample = (target_rect.centerx, marker_y + 4)
    assert screen.get_at(marker_sample)[:3] == view.colors["turn_enemy_alt"]


def test_polymorph_animator_paces_within_its_randomized_span():
    animator = combat_view.SpriteAnimator()
    offsets = []
    for _ in range(220):
        animator.update()
        offsets.append(animator.confused_pace_offset())

    assert min(offsets) < 0 < max(offsets)
    assert max(abs(offset) for offset in offsets) <= animator.pace_span


def test_polymorphed_boss_uses_small_bunny_combat_box():
    view = combat_view.CombatView(pygame.Surface((1024, 720)), SimpleNamespace())
    enemy = SimpleNamespace(
        name="Minotaur",
        status_effects={"Polymorph": SimpleNamespace(active=True)},
    )

    assert view._is_boss_enemy(enemy)
    assert view._enemy_combat_sprite_size(enemy) == (107, 107)
    assert view._enemy_dungeon_combat_sprite_size(enemy) == (134, 134)


def test_resolved_enemy_lane_disappears_without_shifting_survivor():
    screen = pygame.Surface((1024, 720))
    view = combat_view.CombatView(screen, SimpleNamespace())
    player = TestGameState.create_player(name="Hero")
    encounter = CombatEncounter.from_enemies(
        [
            TestGameState.create_player(name="Goblin"),
            TestGameState.create_player(name="Zombie"),
        ],
        combatant_ids=("first", "second"),
    )
    details = {"first": True, "second": True}
    view.render_encounter_in_dungeon(
        player,
        encounter,
        focus_target_id="second",
        details_by_id=details,
    )
    survivor_x = view._enemy_card_rects["second"].x
    assert view._enemy_target_rects["second"].bottom == view._enemy_card_rects["second"].bottom - 8

    encounter.resolve_enemy("first", EnemyResolution.MERCY)
    view.render_encounter_in_dungeon(
        player,
        encounter,
        focus_target_id="second",
        details_by_id=details,
    )

    assert "first" not in view._enemy_card_rects
    assert "first" in view._enemy_target_rects
    first_animator = view._get_sprite_animator(encounter.members[0].enemy)
    assert first_animator.animation_type == "death"
    first_animator.update(DEATH_ANIMATION_FRAMES)
    view.render_encounter_in_dungeon(
        player,
        encounter,
        focus_target_id="second",
        details_by_id=details,
    )
    assert "first" not in view._enemy_target_rects
    assert view._enemy_card_rects["second"].x == survivor_x


def test_multi_enemy_sprite_sizes_preserve_relative_stature():
    view = _make_view()
    view._enemy_combat_sprite_scale = lambda enemy: enemy.presentation_scale
    available = (320, 380)
    dwarf = SimpleNamespace(presentation_scale=0.85)
    vampire = SimpleNamespace(presentation_scale=1.15)

    dwarf_size = view._enemy_encounter_sprite_size(dwarf, available)
    vampire_size = view._enemy_encounter_sprite_size(vampire, available)

    assert dwarf_size == view._enemy_dungeon_combat_sprite_size(dwarf)
    assert vampire_size == view._enemy_dungeon_combat_sprite_size(vampire)
    assert dwarf_size[1] < vampire_size[1]
    assert vampire_size[1] <= available[1]


def _make_view():
    screen = DummyScreen()
    presenter = SimpleNamespace()
    return combat_view.CombatView(screen, presenter)


def _effect(active=True, extra=0, source=""):
    return SimpleNamespace(active=active, extra=extra, source=source)


def _make_character():
    return SimpleNamespace(
        name="Hero",
        cls=SimpleNamespace(name="Warrior"),
        equipment={"Pendant": SimpleNamespace(mod="None")},
        sight=False,
        health=SimpleNamespace(current=40, max=50),
        mana=SimpleNamespace(current=10, max=15),
        encumbered=False,
        status_effects={"Berserk": _effect(), "Steal Success": _effect()},
        physical_effects={"Prone": _effect()},
        stat_effects={"Attack": _effect(extra=2), "Defense": _effect(extra=-1)},
        magic_effects={
            "Totem": _effect(),
            "Regen": _effect(),
            "Jump": _effect(),
            "Astral Shift": _effect(),
        },
        class_effects={"Power Chant": _effect()},
        maelstrom_hits=2,
        evasive_guard_stacks=2,
        spellbook={"Skills": {"Maelstrom Weapon": object(), "Evasive Guard": object()}},
    )


def test_sprite_animator_lifecycle_and_tint():
    animator = combat_view.SpriteAnimator()
    still_alive = animator.update(30)
    assert still_alive is None
    assert animator.frame in (0, 1)
    assert animator.bob_offset != 0 or animator.sway_offset != 0

    animator.trigger_damage()
    assert animator.damage_flash == 1.0

    animator.trigger_death()
    assert animator.animation_type == "death"
    animator.update(4)
    death_time = animator.animation_time
    animator.trigger_death()
    assert animator.animation_time == death_time
    animator.trigger_damage()
    assert animator.animation_type == "death"
    animator.update(DEATH_ANIMATION_FRAMES - death_time)
    assert animator.is_dead is True
    assert animator.death_progress == 1.0

    surface = DummySurface((20, 20))
    tinted = animator.apply_tint(surface, (255, 0, 0), 0.5)
    assert tinted is not surface
    assert tinted.blit_calls
    assert animator.apply_tint(surface, (255, 0, 0), 0) is surface


def test_combat_log_filters_scrolls_and_status_helpers():
    view = _make_view()

    view.set_hidden_enemy_identities(["Invisible Stalker"])
    view.add_combat_message("Invisible Stalker attacks Hero.")
    assert view.combat_log == ["Unseen force attacks Hero."]
    view.combat_log.clear()

    view.add_combat_message(
        "Hero attacks!\nHero is affected by poison\nAlready stunned\nEnemy resists the spell\nNext line"
    )
    assert view.combat_log == ["Hero attacks!", "Next line"]

    view.combat_log = [f"Line {i}" for i in range(8)]
    view.log_scroll_offset = 3
    enemy = SimpleNamespace(name="Goblin")
    view._get_sprite_animator(enemy).trigger_death()
    view.scroll_log(-10)
    assert view.log_scroll_offset == 0
    view.scroll_log(99)
    assert view.log_scroll_offset == view._max_log_scroll()
    view.reset_combat_log()
    assert view.combat_log == []
    assert view.log_scroll_offset == 0
    assert view.sprite_animators == {}
    assert view._hidden_enemy_names == set()

    assert view._effect_label("Resist Fire") == "RF"
    assert view._effect_label("Resist Shadow") == "RSH"
    assert view._effect_label("Resist Holy") == "RHO"
    assert view._effect_label("Mystery") == "MYS"

    icons = view._collect_status_icons(_make_character())
    assert ("ATK2", True) in icons
    assert ("DEF", True) in icons
    assert ("BRK", False) in icons
    assert ("PRN", False) in icons
    assert ("REG", True) in icons
    assert ("AST", True) in icons
    assert ("MW2", True) in icons
    assert ("EG2", True) in icons
    assert icons.index(("PRN", False)) < icons.index(("REG", True))

    character = _make_character()
    character.magic_effects["Resist Shadow"] = _effect()
    character.magic_effects["Resist Holy"] = _effect()
    icons = view._collect_status_icons(character)
    assert ("RSH", True) in icons
    assert ("RHO", True) in icons

    character = _make_character()
    character.status_effects["Blind Rage"] = SimpleNamespace(active=True)
    assert ("BRG", False) in view._collect_status_icons(character)

    character = _make_character()
    character.status_effects.clear()
    character.physical_effects["Defend"] = _effect()
    icons = view._collect_status_icons(character)
    assert any(label.startswith("DEF") and positive is True for label, positive in icons)
    assert ("DEF", False) not in icons
    assert status_icon_color(True, "DEF") == STATUS_ICON_COLORS["positive"]
    assert status_icon_color(False, "DEF") == STATUS_ICON_COLORS["positive"]

    character = _make_character()
    character.magic_effects["Totem"].active = True
    icons = view._collect_status_icons(character)
    assert ("ATK2", True) in icons
    assert ("ATK", True) not in icons

    character = _make_character()
    character.magic_effects["DOT"] = _effect(source="Slot Machine")
    assert ("DOT", False) in view._collect_status_icons(character)

    character.magic_effects["DOT"].source = "Burn"
    assert ("BRN", False) in view._collect_status_icons(character)

    character.stat_effects["Magic"] = _effect(extra=0)
    assert ("MAG", True) not in view._collect_status_icons(character)
    assert ("MAG", False) not in view._collect_status_icons(character)


def test_combat_log_wraps_long_charge_messages(monkeypatch):
    view = _make_view()
    font = RecordingFont()

    monkeypatch.setattr(
        "src.ui_pygame.gui.combat_view.pygame.font.Font", lambda *_args, **_kwargs: font
    )
    monkeypatch.setattr(
        "src.ui_pygame.gui.combat_view.pygame.draw.rect", lambda *_args, **_kwargs: None
    )

    message = "Goblin is lowering their head and building momentum for a devastating charge that needs wrapping."
    view.add_combat_message(message)

    assert view.combat_log == ["Goblin is charging."]
    assert view._wrapped_combat_log_lines(view.combat_width - 30, font=font) == [
        "Goblin is charging."
    ]

    view._render_combat_log()

    assert font.render_calls == ["Goblin is charging."]
    assert all(font.size(text)[0] <= view.combat_width - 30 for text in font.render_calls)
    assert all(color == view.colors["telegraph"] for _text, color in font.color_calls)
    rendered_positions = [
        position
        for surface, position, _args, _kwargs in view.screen.blit_calls
        if getattr(surface, "text", None) in font.render_calls
    ]
    assert rendered_positions[0][0] == 20

    font.render_calls.clear()
    font.color_calls.clear()
    view.screen.blit_calls.clear()
    view.combat_log = ["Goblin is charging."]
    view._render_combat_log_overlay()
    overlay_width = int(view.screen_width * 0.65) - 30
    assert font.render_calls == ["Goblin is charging."]
    assert all(font.size(text)[0] <= overlay_width for text in font.render_calls)
    assert all(color == view.colors["telegraph"] for _text, color in font.color_calls)
    rendered_positions = [
        position
        for surface, position, _args, _kwargs in view.screen.blit_calls
        if getattr(surface, "text", None) in font.render_calls
    ]
    assert rendered_positions[0][0] == 20


def test_combat_log_wrapping_is_cached_until_messages_change(monkeypatch):
    view = _make_view()
    font = RecordingFont()
    wrap_calls = []
    original_wrap = view._wrap_log_line

    monkeypatch.setattr(
        "src.ui_pygame.gui.combat_view.pygame.font.Font", lambda *_args, **_kwargs: font
    )
    monkeypatch.setattr(
        "src.ui_pygame.gui.combat_view.pygame.draw.rect", lambda *_args, **_kwargs: None
    )

    def recording_wrap(*args, **kwargs):
        wrap_calls.append(args[0])
        return original_wrap(*args, **kwargs)

    monkeypatch.setattr(view, "_wrap_log_line", recording_wrap)

    view.add_combat_message("Hero attacks Goblin for 5 damage.")
    wrap_calls.clear()
    view._render_combat_log()
    view._render_combat_log()

    assert wrap_calls == ["Hero attacks Goblin for 5 damage."]

    view.add_combat_message("Goblin misses Hero.")
    wrap_calls.clear()
    view._render_combat_log()

    assert wrap_calls.count("Hero attacks Goblin for 5 damage.") == 1
    assert wrap_calls.count("Goblin misses Hero.") == 1


def test_combat_log_overlay_wraps_with_render_font(monkeypatch):
    view = _make_view()
    wide_font = RecordingFont()
    narrow_font = RecordingFont()

    wide_font.size = lambda text: (max(8, len(text) * 12), 20)
    narrow_font.size = lambda text: (max(8, len(text) * 5), 20)
    fonts = [wide_font]

    def font_factory(*_args, **_kwargs):
        if fonts:
            return fonts.pop(0)
        return narrow_font

    monkeypatch.setattr("src.ui_pygame.gui.combat_view.pygame.font.Font", font_factory)
    monkeypatch.setattr(
        "src.ui_pygame.gui.combat_view.pygame.draw.rect", lambda *_args, **_kwargs: None
    )

    view.combat_log = [
        "Kain is coiling their legs, preparing to leap into the air, gathering power for a devastating strike."
    ]

    view._render_combat_log_overlay()

    overlay_width = int(view.screen_width * 0.65) - 30
    assert len(wide_font.render_calls) > 1
    assert all(wide_font.size(text)[0] <= overlay_width for text in wide_font.render_calls)


def test_combat_log_color_categorizes_common_outcomes():
    view = _make_view()

    assert (
        view._combat_log_color("The bleed damages Kain for 37 health points.")
        == view.colors["log_damage"]
    )
    assert (
        view._combat_log_color("Red Dragon's health has regenerated by 20.")
        == view.colors["log_heal"]
    )
    assert view._combat_log_color("Red Dragon resists the spell.") == view.colors["log_muted"]
    assert view._combat_log_color("Goblin has been blinded.") == view.colors["log_damage"]
    assert view._combat_log_color("Goblin has been silenced.") == view.colors["log_damage"]
    assert view._combat_log_color("Kain attacks.") == view.colors["text"]
    assert view._combat_log_color("Kain attacks.", overlay=True) == (240, 240, 240)

    view._set_combat_log_actors(SimpleNamespace(name="Kain"), SimpleNamespace(name="Red Dragon"))
    assert view._combat_log_color("Kain attacks.") == view.colors["log_player"]
    assert view._combat_log_color("Red Dragon attacks.") == view.colors["log_enemy"]
    assert (
        view._combat_log_color("Red Dragon's health has regenerated by 20.")
        == view.colors["log_heal"]
    )

    view._set_combat_log_actors(
        SimpleNamespace(name="Kain", active_summon_name="Patagon"),
        SimpleNamespace(name="Red Dragon"),
    )
    assert view._combat_log_color("Patagon uses Throw Rock.") == view.colors["log_summon"]


def test_turn_indicator_renders_player_and_enemy_states(monkeypatch):
    view = _make_view()
    player = SimpleNamespace(name="Hero")
    enemy = SimpleNamespace(
        name="Goblin With An Extremely Long Formal Dungeon Title And Several More Ceremonial Names"
    )
    player_token_calls = []
    token_calls = []
    companion_token_calls = []
    view.player_token_manager = SimpleNamespace(
        get_scaled_token=lambda target, size: player_token_calls.append((target.name, size))
        or DummySurface(size, text="player-token")
    )
    view.enemy_token_manager = SimpleNamespace(
        get_scaled_token=lambda target, size: token_calls.append((target.name, size))
        or DummySurface(size, text="enemy-token")
    )
    monkeypatch.setattr(
        "src.ui_pygame.gui.combat_view.overlay.get_companion_art_manager",
        lambda: SimpleNamespace(
            get_scaled_sprite=lambda target, size: companion_token_calls.append((target.name, size))
            or DummySurface(size, text="summon-token")
        ),
    )
    view._collect_status_icons = lambda _actor: []
    fonts = iter(
        [
            RecordingFont(),
            RecordingFont(),
            RecordingFont(),
            RecordingFont(),
            RecordingFont(),
            RecordingFont(),
            RecordingFont(),
            RecordingFont(),
        ]
    )
    rect_calls = []
    circle_calls = []

    monkeypatch.setattr(
        "src.ui_pygame.gui.combat_view.pygame.font.Font", lambda *_args, **_kwargs: next(fonts)
    )
    monkeypatch.setattr(
        "src.ui_pygame.gui.combat_view.pygame.draw.rect",
        lambda *_args, **_kwargs: rect_calls.append((_args, _kwargs)),
    )
    monkeypatch.setattr(
        "src.ui_pygame.gui.combat_view.pygame.draw.circle",
        lambda *_args, **_kwargs: circle_calls.append((_args, _kwargs)),
    )
    monkeypatch.setattr(
        "src.ui_pygame.gui.combat_view.pygame.Surface",
        lambda size, *_args, **_kwargs: DummySurface(size),
    )

    view._render_turn_indicator(player, enemy, current_turn="player")
    view._render_turn_indicator(player, enemy, current_turn="enemy", overlay=True)
    view._render_turn_indicator(
        player,
        enemy,
        current_turn="player",
        current_actor=SimpleNamespace(name="Patagon"),
    )
    view._render_turn_indicator(player, enemy, current_turn=None)

    rendered_text = [
        getattr(surface, "text", "")
        for surface, _pos, _args, _kwargs in view.screen.blit_calls
        if getattr(surface, "text", "")
    ]
    colors = [args[1] for args, _kwargs in rect_calls if len(args) > 1]

    assert "Your Turn" in rendered_text
    assert "Enemy Turn" in rendered_text
    assert "Patagon" in rendered_text
    assert "player-token" in rendered_text
    assert "enemy-token" in rendered_text
    assert "summon-token" in rendered_text
    enemy_label = next(text for text in rendered_text if text.startswith("Goblin"))
    assert enemy_label.endswith("...")
    assert RecordingFont().size(enemy_label)[0] <= int(view.screen_width * 0.65) - 30 - 86
    assert view.colors["turn_player"] in colors
    assert view.colors["turn_enemy"] in colors
    assert player_token_calls == [(player.name, (46, 46))]
    assert token_calls == [(enemy.name, (46, 46))]
    assert companion_token_calls == [("Patagon", (46, 46))]
    assert not circle_calls


def test_turn_indicator_skips_incapacitated_actor(monkeypatch):
    view = _make_view()
    player = SimpleNamespace(name="Hero", incapacitated=lambda: True)
    enemy = SimpleNamespace(name="Goblin", incapacitated=lambda: False)
    player_token_calls = []
    view.player_token_manager = SimpleNamespace(
        get_scaled_token=lambda target, size: player_token_calls.append((target.name, size))
    )
    monkeypatch.setattr(
        "src.ui_pygame.gui.combat_view.pygame.draw.rect", lambda *_args, **_kwargs: None
    )

    view._render_turn_indicator(player, enemy, current_turn="player")

    assert player_token_calls == []
    assert view.screen.blit_calls == []


def test_turn_indicator_conceals_invisible_enemy_without_sight(monkeypatch):
    view = _make_view()
    player = SimpleNamespace(
        name="Hero",
        cls=SimpleNamespace(name="Warrior"),
        equipment={},
        sight=False,
        incapacitated=lambda: False,
    )
    enemy = SimpleNamespace(
        name="Invisible Stalker",
        invisible=True,
        incapacitated=lambda: False,
    )
    token_calls = []
    view.enemy_token_manager = SimpleNamespace(
        get_scaled_token=lambda target, size: (
            token_calls.append((target.name, size)) or DummySurface(size, text="enemy-token")
        ),
    )
    fonts = iter([RecordingFont(), RecordingFont()])
    monkeypatch.setattr(
        "src.ui_pygame.gui.combat_view.pygame.font.Font",
        lambda *_args, **_kwargs: next(fonts),
    )
    monkeypatch.setattr(
        "src.ui_pygame.gui.combat_view.pygame.draw.rect",
        lambda *_args, **_kwargs: None,
    )
    monkeypatch.setattr(
        "src.ui_pygame.gui.combat_view.pygame.Surface",
        lambda size, *_args, **_kwargs: DummySurface(size),
    )

    view._render_turn_indicator(
        player,
        enemy,
        current_turn="enemy",
        overlay=True,
    )

    rendered_text = [
        getattr(surface, "text", "")
        for surface, _pos, _args, _kwargs in view.screen.blit_calls
        if getattr(surface, "text", "")
    ]
    assert "Unseen force" in rendered_text
    assert "Invisible Stalker" not in rendered_text
    assert token_calls == []


def test_flying_enemy_renders_higher_than_grounded(monkeypatch):
    view = _make_view()
    enemy = SimpleNamespace(
        name="Bat", health=SimpleNamespace(current=10, max=10), flying=False, tunnel=False
    )
    animator = SimpleNamespace(
        damage_flash=0,
        animation_type=None,
        death_progress=0,
        bob_offset=0,
        sway_offset=0,
        apply_tint=lambda surface, _color, _alpha: surface,
    )
    monkeypatch.setattr(view, "_get_sprite_animator", lambda _enemy: animator)
    monkeypatch.setattr(view, "_enemy_combat_sprite_size", lambda _enemy: (64, 64))
    monkeypatch.setattr(
        view,
        "_enemy_sprite_surface",
        lambda *_args, **_kwargs: DummySurface((64, 64), text="enemy"),
    )
    monkeypatch.setattr(view, "_draw_mirror_images", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(
        "src.ui_pygame.gui.combat_view.pygame.draw.rect", lambda *_args, **_kwargs: None
    )

    view._render_enemy(enemy)
    grounded_center_y = view._last_enemy_target_rect.centery
    enemy.flying = True
    view._render_enemy(enemy)
    flying_center_y = view._last_enemy_target_rect.centery

    assert flying_center_y < grounded_center_y


def test_render_combat_does_not_default_to_player_turn(monkeypatch):
    view = _make_view()
    player = _make_character()
    enemy = SimpleNamespace(name="Goblin")
    recorded_turns = []

    monkeypatch.setattr(view, "update_animations", lambda: None)
    monkeypatch.setattr(view.screen, "fill", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(view, "_render_enemy", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(view, "_render_enemy_info_panel", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(
        view,
        "_render_turn_indicator",
        lambda *_args, **kwargs: recorded_turns.append(kwargs.get("current_turn")),
    )
    monkeypatch.setattr(view, "_render_telegraph_banner", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(view, "_render_player_status", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(view, "_render_action_menu", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(view, "_render_combat_log", lambda *_args, **_kwargs: None)

    view.render_combat(player, enemy, actions=[])

    assert recorded_turns == [None]


def test_action_menu_overlay_fits_many_actions_without_overflow(monkeypatch):
    view = _make_view()
    action_font = RecordingFont()

    monkeypatch.setattr(
        "src.ui_pygame.gui.combat_view.pygame.font.Font", lambda *_args, **_kwargs: action_font
    )
    monkeypatch.setattr(
        "src.ui_pygame.gui.combat_view.pygame.Surface",
        lambda size, *_args, **_kwargs: DummySurface(size),
    )
    monkeypatch.setattr(
        "src.ui_pygame.gui.combat_view.pygame.draw.rect", lambda *_args, **_kwargs: None
    )

    actions = [
        "Attack",
        "Defend",
        "Pickup Weapon",
        "Spells",
        "Skills",
        "Items",
        "Auto Kill",
        "Extremely Long Debug Combat Action That Must Fit",
    ]
    view._render_action_menu_overlay(actions, selected_action=7)

    menu_top = view.screen_height - 174
    action_blits = [
        (surface.text, position)
        for surface, position, _args, _kwargs in view.screen.blit_calls
        if getattr(surface, "text", "") in action_font.render_calls
    ]
    assert len(action_blits) == len(actions)
    assert all(
        menu_top <= position[1] < view.screen_height - 10 for _text, position in action_blits
    )
    fitted_long = next(text for text in action_font.render_calls if text.startswith("Extremely"))
    assert fitted_long.endswith("...")
    _actions_per_row, _row_count, _start_y_offset, _row_height, cell_width = (
        view._action_grid_layout(
            int(view.screen_width * 0.65),
            174,
            len(actions),
        )
    )
    assert action_font.size(fitted_long)[0] <= cell_width - 22


def test_telegraph_banner_uses_latest_matching_log_line(monkeypatch):
    view = _make_view()
    fonts = [
        RecordingFont(),
        RecordingFont(),
        RecordingFont(),
        RecordingFont(),
        RecordingFont(),
        RecordingFont(),
    ]
    rect_calls = []

    monkeypatch.setattr(
        "src.ui_pygame.gui.combat_view.pygame.font.Font",
        lambda *_args, **_kwargs: fonts.pop(0) if fonts else RecordingFont(),
    )
    monkeypatch.setattr(
        "src.ui_pygame.gui.combat_view.pygame.draw.rect",
        lambda *_args, **_kwargs: rect_calls.append((_args, _kwargs)),
    )
    monkeypatch.setattr(
        "src.ui_pygame.gui.combat_view.pygame.draw.circle", lambda *_args, **_kwargs: None
    )
    monkeypatch.setattr(
        "src.ui_pygame.gui.combat_view.pygame.Surface",
        lambda size, *_args, **_kwargs: DummySurface(size),
    )

    view.add_combat_message("Goblin attacks.")
    view.add_combat_message("Goblin is lowering their head and building momentum!")

    view._render_telegraph_banner(overlay=False)
    view._render_telegraph_banner(overlay=True)

    rendered_text = [
        getattr(surface, "text", "")
        for surface, _pos, _args, _kwargs in view.screen.blit_calls
        if getattr(surface, "text", "")
    ]

    assert "Incoming" in rendered_text
    assert "Goblin is charging." in rendered_text
    assert any(args[1] == view.colors["telegraph"] for args, _kwargs in rect_calls if len(args) > 1)


def test_telegraph_banner_ignores_player_telegraphs_when_enemy_context(monkeypatch):
    view = _make_view()
    font = RecordingFont()
    enemy = SimpleNamespace(name="Red Dragon")

    monkeypatch.setattr(
        "src.ui_pygame.gui.combat_view.pygame.font.Font", lambda *_args, **_kwargs: font
    )
    monkeypatch.setattr(
        "src.ui_pygame.gui.combat_view.pygame.draw.rect", lambda *_args, **_kwargs: None
    )
    monkeypatch.setattr(
        "src.ui_pygame.gui.combat_view.pygame.draw.circle", lambda *_args, **_kwargs: None
    )
    monkeypatch.setattr(
        "src.ui_pygame.gui.combat_view.pygame.Surface",
        lambda size, *_args, **_kwargs: DummySurface(size),
    )

    view.add_combat_message("Kain is coiling their legs, preparing to leap into the air!")
    view._render_telegraph_banner(enemy=enemy, overlay=True)
    assert "Incoming" not in font.render_calls

    view.add_combat_message("Red Dragon is inhaling deeply, flames flickering in its throat!")
    view._render_telegraph_banner(enemy=enemy, overlay=True)
    assert "Incoming" in font.render_calls


def test_telegraph_banner_uses_full_unwrapped_latest_message(monkeypatch):
    view = _make_view()
    long_message = (
        "Hydra is gathering enough stormlight for an extremely long telegraph message "
        "that wraps inside the combat log but should stay whole for banner truncation."
    )
    view.add_combat_message(long_message)

    assert view.combat_log == ["Hydra is charging."]
    assert view._latest_telegraph_line() == "Hydra is charging."
    view.reset_combat_log()
    assert view._latest_telegraph_line() is None


def test_telegraph_banner_clears_after_non_telegraph_message(monkeypatch):
    view = _make_view()
    view.add_combat_message("Hydra is gathering enough stormlight to strike next turn.")
    assert view._latest_telegraph_line() is not None

    view.add_combat_message("Hydra unleashes the storm!")

    assert view._latest_telegraph_line() is None
    assert any("unleashes" in line for line in view.combat_log)


def test_class_kit_log_filter_keeps_required_failure_messages():
    view = _make_view()

    view.add_combat_message("Goblin is immune to poison.")
    assert "Goblin is immune to poison." not in view.combat_log

    view.add_combat_message("Death Mark is immune to execution and downgrades to pressure.")
    view.add_combat_message("Threaded Cast is immune to the negated rider.")
    view.add_combat_message("Class Ring resists the failed payoff and Ring Preserve remains ready.")
    view.add_combat_message("Spellbind fails because the blade charge was lost.")
    view.add_combat_message("Summon Bond: Patagon bond holds steady after a low-XP victory.")
    view.add_combat_message("Scavenger's Eye spots ordinary loot: Iron Dagger.")

    assert "Death Mark is immune to execution and downgrades to pressure." in view.combat_log
    assert "Threaded Cast is immune to the negated rider." in view.combat_log
    assert (
        "Class Ring resists the failed payoff and Ring Preserve remains ready." in view.combat_log
    )
    assert "Spellbind fails because the blade charge was lost." in view.combat_log
    assert "Summon Bond: Patagon bond holds steady after a low-XP victory." in view.combat_log
    assert "Scavenger's Eye spots ordinary loot: Iron Dagger." in view.combat_log


def test_sight_rules():
    view = _make_view()

    player = _make_character()
    assert view._has_sight(player) is False
    player.cls.name = "Seeker"
    assert view._has_sight(player) is True
    player.cls.name = "Warrior"
    player.equipment["Pendant"].mod = "Vision"
    assert view._has_sight(player) is True
    player.equipment["Pendant"].mod = "None"
    player.sight = True
    assert view._has_sight(player) is True


def test_render_helpers_cover_icons_player_status_and_logs(monkeypatch):
    view = _make_view()
    font_small = RecordingFont()
    font_medium = RecordingFont()
    font_large = RecordingFont()
    all_fonts = [
        font_small,
        font_medium,
        font_large,
        RecordingFont(),
        RecordingFont(),
        RecordingFont(),
        RecordingFont(),
        RecordingFont(),
        RecordingFont(),
        RecordingFont(),
    ]
    fonts = list(all_fonts)

    monkeypatch.setattr(
        "src.ui_pygame.gui.combat_view.pygame.font.Font",
        lambda *_args, **_kwargs: fonts.pop(0) if fonts else RecordingFont(),
    )
    rect_calls = []
    monkeypatch.setattr(
        "src.ui_pygame.gui.combat_view.pygame.draw.rect",
        lambda *_args, **_kwargs: rect_calls.append((_args, _kwargs)),
    )

    view._render_status_icons([("ATK", True), ("PSN", False), ("REG", True)], 10, 20, max_width=90)
    assert "ATK" in font_small.render_calls
    assert "PSN" in font_small.render_calls

    player = _make_character()
    player.encumbered = True
    view._render_player_status(player)
    combined = font_medium.render_calls + font_large.render_calls
    assert any(text.startswith("HP:") for text in combined)
    assert any("ENCUMBERED" in text for text in combined)

    rune_player = _make_character()
    rune_player.cls.name = "Astromancer"
    rune_player.astromancer_state = {
        "active_constellation_index": 0,
        "runes": {"Ember": 2, "Tide": 0, "Gale": 1, "Stone": 0},
    }
    view._render_player_status(rune_player)
    rune_calls = [text for font in all_fonts for text in font.render_calls]
    assert "Sign: Ember" in rune_calls
    assert "Ember: **." in rune_calls

    view.combat_log = ["Line one", "Line two\nLine three"]
    view._render_combat_log()
    assert any(
        "Line one" in call[0].text for call in view.screen.blit_calls if hasattr(call[0], "text")
    )

    view.combat_log = [f"Msg {i}" for i in range(9)]
    view.log_scroll_offset = 2
    fonts = [RecordingFont(), RecordingFont(), RecordingFont()]
    monkeypatch.setattr(
        "src.ui_pygame.gui.combat_view.pygame.font.Font",
        lambda *_args, **_kwargs: fonts.pop(0) if fonts else RecordingFont(),
    )
    view._render_combat_log_overlay()

    fonts = [RecordingFont(), RecordingFont()]
    monkeypatch.setattr(
        "src.ui_pygame.gui.combat_view.pygame.font.Font",
        lambda *_args, **_kwargs: fonts.pop(0) if fonts else RecordingFont(),
    )
    monkeypatch.setattr(
        "src.ui_pygame.gui.combat_view.pygame.Surface",
        lambda size, *_args, **_kwargs: DummySurface(size),
    )
    view._render_action_menu_overlay(["Attack", "Skills", "Items"], 1)
    assert rect_calls


def test_status_icons_compact_overflow_and_telegraph_log_color(monkeypatch):
    view = _make_view()
    font = RecordingFont()
    rect_calls = []

    monkeypatch.setattr(
        "src.ui_pygame.gui.combat_view.pygame.font.Font", lambda *_args, **_kwargs: font
    )
    monkeypatch.setattr(
        "src.ui_pygame.gui.combat_view.pygame.draw.rect",
        lambda *_args, **_kwargs: rect_calls.append((_args, _kwargs)),
    )
    monkeypatch.setattr(
        "src.ui_pygame.gui.combat_view.pygame.Surface",
        lambda size, *_args, **_kwargs: DummySurface(size),
    )

    icons = [(f"E{i}", i % 2 == 0) for i in range(6)]
    view._render_status_icons(icons, 10, 20, max_width=90, max_rows=2)

    assert font.render_calls == ["E0", "E1", "E2", "+3"]
    assert view.status_colors["overflow"] in [
        args[1] for args, _kwargs in rect_calls if len(args) > 1
    ]

    normal_line = "Hero attacks."
    telegraph_line = "Goblin is charging."
    font.render_calls.clear()
    font.color_calls.clear()
    view.combat_log = [telegraph_line, normal_line]
    view.log_scroll_offset = 0

    view._render_combat_log()
    assert (telegraph_line, view.colors["telegraph"]) in font.color_calls
    assert (normal_line, view.colors["text"]) in font.color_calls

    font.color_calls.clear()
    view._render_combat_log_overlay()
    assert (telegraph_line, view.colors["telegraph"]) in font.color_calls
    assert (normal_line, (240, 240, 240)) in font.color_calls


def test_status_art_icons_render_without_badge_background(monkeypatch):
    view = _make_view()
    font = RecordingFont()
    rect_calls = []
    icon_surface = DummySurface((14, 14), text="stun-icon")
    icon_sizes = []

    monkeypatch.setattr(
        "src.ui_pygame.gui.combat_view.pygame.font.Font", lambda *_args, **_kwargs: font
    )
    monkeypatch.setattr(
        "src.ui_pygame.gui.combat_view.pygame.draw.rect",
        lambda *_args, **_kwargs: rect_calls.append((_args, _kwargs)),
    )
    monkeypatch.setattr(
        "src.ui_pygame.gui.combat_view.status.load_status_icon_surface",
        lambda _label, size, _is_positive=None: icon_sizes.append(size) or icon_surface,
    )

    view._render_status_icons([("STN", False)], 10, 20, max_width=90)

    assert not rect_calls
    assert font.render_calls == []
    assert icon_sizes == [(24, 24)]
    assert any(surface is icon_surface for surface, _pos, _args, _kwargs in view.screen.blit_calls)


def test_counted_art_status_icons_render_badge_over_icon(monkeypatch):
    view = _make_view()
    font = RecordingFont()
    icon_surface = DummySurface((14, 14), text="maelstrom-icon")
    circle_calls = []

    monkeypatch.setattr(
        "src.ui_pygame.gui.combat_view.pygame.font.Font", lambda *_args, **_kwargs: font
    )
    monkeypatch.setattr(
        "src.ui_pygame.gui.combat_view.pygame.draw.circle",
        lambda *_args, **_kwargs: circle_calls.append((_args, _kwargs)),
    )
    monkeypatch.setattr(
        "src.ui_pygame.gui.combat_view.status.load_status_icon_surface",
        lambda _label, _size, _is_positive=None: icon_surface,
    )

    view._render_status_icons([("MW5", True)], 10, 20, max_width=90)

    blitted_text = [
        getattr(surface, "text", "") for surface, _pos, _args, _kwargs in view.screen.blit_calls
    ]
    assert "maelstrom-icon" in blitted_text
    assert "5" in blitted_text
    assert circle_calls


def test_enemy_detail_visibility_hides_bosses_and_shows_non_boss_mana(monkeypatch):
    view = _make_view()
    player = _make_character()
    player.equipment["Pendant"].mod = "Vision"
    boss = SimpleNamespace(name="Jester", boss=True)
    enemy = SimpleNamespace(
        name="Bandit",
        health=SimpleNamespace(current=8, max=10),
        mana=SimpleNamespace(current=7, max=16),
        flying=False,
        tunnel=False,
        magic_effects={},
        class_effects={},
    )
    font = RecordingFont()

    assert view._enemy_details_visible(player, boss) is False
    assert view._enemy_details_visible(player, enemy) is True

    monkeypatch.setattr(
        "src.ui_pygame.gui.combat_view.pygame.font.Font", lambda *_args, **_kwargs: font
    )
    monkeypatch.setattr(
        "src.ui_pygame.gui.combat_view.pygame.draw.rect", lambda *_args, **_kwargs: None
    )
    monkeypatch.setattr(
        "src.ui_pygame.gui.combat_view.pygame.draw.circle", lambda *_args, **_kwargs: None
    )
    monkeypatch.setattr(
        view,
        "_enemy_sprite_surface",
        lambda *_args, **_kwargs: DummySurface((80, 80), text="enemy"),
    )
    monkeypatch.setattr(view, "_enemy_combat_sprite_size", lambda _enemy: (80, 80))

    view._render_enemy(enemy, has_sight=True)

    assert "HP 8/10" in font.render_calls
    assert "MP 7/16" in font.render_calls


def test_combat_log_color_classifies_item_special_effect_messages():
    view = _make_view()
    view._set_combat_log_actors(
        SimpleNamespace(name="Hero"),
        SimpleNamespace(name="Bandit"),
    )

    assert (
        view._combat_log_color("Hero's Robes of Merlin restore 4 mana.") == view.colors["log_heal"]
    )
    assert (
        view._combat_log_color("Bandit's Klivanion shocks Hero for 3 lightning damage.")
        == view.colors["log_damage"]
    )
    assert view._combat_log_color("Hero is stunned by the Klivanion.") == view.colors["log_damage"]
    assert view._combat_log_color("Bandit resists the poison.") == view.colors["log_muted"]
    assert view._combat_log_color("Hero's shield hums with power.") == view.colors["log_player"]
    assert view._combat_log_color("Bandit's armor gleams.") == view.colors["log_enemy"]


def test_status_icon_priority_keeps_urgent_effects_visible_before_overflow(monkeypatch):
    view = _make_view()
    font = RecordingFont()
    rect_calls = []

    monkeypatch.setattr(
        "src.ui_pygame.gui.combat_view.pygame.font.Font", lambda *_args, **_kwargs: font
    )
    monkeypatch.setattr(
        "src.ui_pygame.gui.combat_view.pygame.draw.rect",
        lambda *_args, **_kwargs: rect_calls.append((_args, _kwargs)),
    )

    icons = prioritize_status_icons(
        [
            ("ATK", True),
            ("REG", True),
            ("PSN", False),
            ("STN", False),
            ("MSH", True),
            ("PRN", False),
        ]
    )

    assert icons[:3] == [("STN", False), ("PRN", False), ("PSN", False)]

    view._render_status_icons(icons, 10, 20, max_width=90, max_rows=2)
    assert font.render_calls == ["STN", "PRN", "PSN", "+3"]
    colors = [args[1] for args, _kwargs in rect_calls if len(args) > 1]
    assert view.status_colors["urgent_negative"] in colors


def test_status_icon_priority_uses_counts_as_stable_tie_breaker():
    icons = prioritize_status_icons(
        combine_duplicate_status_icons(
            [
                ("BLE", False),
                ("PSN", False),
                ("PSN", False),
                ("PSN", False),
                ("PSN", False),
                ("WND", False),
                ("WND", False),
                ("WND", False),
                ("STN", False),
                ("ATK", True),
                ("MSH", True),
            ]
        )
    )

    assert icons == [
        ("STN", False),
        ("PSN4", False),
        ("WND3", False),
        ("BLE", False),
        ("MSH", True),
        ("ATK", True),
    ]


def test_status_icon_label_fitting_handles_zero_width_pills():
    font = RecordingFont()

    assert fit_status_icon_label(font, "BRG", 0) == "."
    assert fit_status_icon_label(font, "+12", -1) == "+"
    assert fit_status_icon_label(font, "BRG", 999) == "BRG"


def test_enemy_info_panel_renders_combat_sprite(monkeypatch):
    view = _make_view()
    calls = []
    fonts = iter([RecordingFont(), RecordingFont()])
    enemy = SimpleNamespace(
        name="Goblin Raider",
        enemy_typ="Humanoid",
        health=SimpleNamespace(current=15, max=20),
        resistance={"Fire": -0.25, "Poison": 0.5},
        status_effects={},
        physical_effects={},
        stat_effects={},
        magic_effects={},
        class_effects={},
    )
    view.enemy_combat_sprite_manager = SimpleNamespace(
        get_scaled_sprite=lambda target, size: calls.append((target.name, size))
        or DummySurface(size, text="enemy-combat-sprite"),
        fallback_surface=lambda: DummySurface((256, 320), text="fallback-sprite"),
    )

    monkeypatch.setattr(
        "src.ui_pygame.gui.combat_view.pygame.font.Font", lambda *_args, **_kwargs: next(fonts)
    )
    monkeypatch.setattr(
        "src.ui_pygame.gui.combat_view.pygame.draw.rect", lambda *_args, **_kwargs: None
    )

    view._render_enemy_info_panel(enemy, has_sight=True, overlay=True)

    assert calls and calls[0][0] == "Goblin Raider"
    assert any(
        getattr(surface, "text", "") == "enemy-combat-sprite"
        for surface, _pos, _args, _kwargs in view.screen.blit_calls
    )
    rendered_text = [
        getattr(surface, "text", "")
        for surface, _pos, _args, _kwargs in view.screen.blit_calls
        if getattr(surface, "text", "")
    ]
    assert "Goblin Raider" in rendered_text
    assert "HP 15 / 20" in rendered_text
    assert "Type Humanoid" in rendered_text
    assert any(text.startswith("Weak Fire") for text in rendered_text)
    assert any(text.startswith("Resist Poison") for text in rendered_text)


def test_quasit_combat_sprite_mapping_loads_remade_asset():
    from tools.build_enemy_combat_sprites import mapped_sprite_keys

    manager = EnemyCombatSpriteManager()

    assert manager.get_sprite_key_for_enemy("Quasit") == "quasit"
    assert "quasit" in mapped_sprite_keys(manager.sprite_root)
    sprite = manager.get_sprite_by_name("Quasit")
    width, height = sprite.get_size()
    assert width > 0
    assert height > 0


def test_enemy_info_panel_adds_invisible_notes_and_preserves_sight_gate(monkeypatch):
    view = _make_view()
    calls = []
    fonts = iter([RecordingFont(), RecordingFont(), RecordingFont(), RecordingFont()])
    enemy = SimpleNamespace(
        name="Invisible Stalker",
        enemy_typ="Elemental",
        invisible=True,
        health=SimpleNamespace(current=12, max=24),
        resistance={"Fire": -0.25},
        status_effects={},
        physical_effects={},
        stat_effects={},
        magic_effects={},
        class_effects={},
    )
    view.enemy_combat_sprite_manager = SimpleNamespace(
        get_scaled_sprite=lambda target, size: calls.append((target.name, size))
        or DummySurface(size, text="enemy-combat-sprite"),
        fallback_surface=lambda: DummySurface((256, 320), text="fallback-sprite"),
    )

    monkeypatch.setattr(
        "src.ui_pygame.gui.combat_view.pygame.font.Font", lambda *_args, **_kwargs: next(fonts)
    )
    monkeypatch.setattr(
        "src.ui_pygame.gui.combat_view.pygame.draw.rect", lambda *_args, **_kwargs: None
    )

    view._render_enemy_info_panel(enemy, has_sight=False, overlay=True)

    rendered_text = [
        getattr(surface, "text", "")
        for surface, _pos, _args, _kwargs in view.screen.blit_calls
        if getattr(surface, "text", "")
    ]
    assert "Unseen force" in rendered_text
    assert "Invisible Stalker" not in rendered_text
    assert any(text.startswith("Invisible: details hidden") for text in rendered_text)
    assert "HP 12 / 24" not in rendered_text
    assert not any(text.startswith("Weak Fire") for text in rendered_text)
    assert calls == []

    view.screen.blit_calls.clear()
    view._render_enemy_info_panel(enemy, has_sight=True, overlay=True)

    rendered_text = [
        getattr(surface, "text", "")
        for surface, _pos, _args, _kwargs in view.screen.blit_calls
        if getattr(surface, "text", "")
    ]
    assert any(text.startswith("Sight reveals this invisible") for text in rendered_text)
    assert "HP 12 / 24" in rendered_text
    assert any(text.startswith("Weak Fire") for text in rendered_text)
    assert calls and calls[0][0] == "Invisible Stalker"


def test_invisible_stalker_dungeon_combat_does_not_draw_fallback_without_sight(monkeypatch):
    view = _make_view()
    calls = []
    circle_calls = []
    fonts = iter([RecordingFont(), RecordingFont()])
    player = _make_character()
    player.sight = False
    player.equipment["Pendant"].mod = "None"
    enemy = SimpleNamespace(
        name="Invisible Stalker",
        health=SimpleNamespace(current=12, max=24),
        status_effects={},
        physical_effects={},
        stat_effects={},
        magic_effects={},
        class_effects={},
    )
    view.enemy_combat_sprite_manager = SimpleNamespace(
        get_sprite_key_for_enemy=lambda target: calls.append(target.name) or "invisible_stalker",
        get_scaled_sprite_by_key=lambda _key, size: DummySurface(size, text="enemy-combat-sprite"),
    )

    monkeypatch.setattr(
        "src.ui_pygame.gui.combat_view.pygame.font.Font", lambda *_args, **_kwargs: next(fonts)
    )
    monkeypatch.setattr(
        "src.ui_pygame.gui.combat_view.pygame.draw.circle",
        lambda *args, **kwargs: circle_calls.append((args, kwargs)),
    )

    view.render_enemy_in_dungeon(player, enemy)

    assert calls == []
    assert circle_calls == []
    assert not any(
        getattr(surface, "text", "") == "enemy-combat-sprite"
        for surface, *_rest in view.screen.blit_calls
    )
    assert not any(
        getattr(surface, "text", "") == "Invisible Stalker"
        for surface, *_rest in view.screen.blit_calls
    )


def test_collect_status_icons_includes_vision_and_weapon_art_states():
    view = _make_view()
    character = _make_character()
    character.sight = True
    character._reavers_mark = {"turns": 2, "bonus": 0.1}
    character._brace_art = {"turns": 1}
    character._riposte_line = {"turns": 1}

    icons = view._collect_status_icons(character)

    assert ("VIS", True) in icons
    assert ("RMK", False) in icons
    assert ("BRC", True) in icons
    assert ("RIP", True) in icons


def test_collect_status_icons_marks_player_charge_in_progress():
    view = _make_view()
    character = _make_character()
    character.spellbook["Skills"]["Charge"] = SimpleNamespace(charging=True)

    assert ("CHG", True) in view._collect_status_icons(character)

    character.spellbook["Skills"]["Charge"].charging = False
    character.class_effects["Jump"] = _effect(active=True)
    assert ("CHG", True) in view._collect_status_icons(character)


def test_construct_bleed_uses_oil_leak_presentation_without_changing_effect():
    view = _make_view()
    construct = _make_character()
    construct.name = "Cyborg"
    construct.enemy_typ = "Construct"
    construct.physical_effects["Bleed"] = _effect()
    construct.physical_effects["Bleed"].active = True
    construct.physical_effects["Bleed"].duration = 2
    construct.physical_effects["Bleed"].extra = 6

    biological = _make_character()
    biological.name = "Bandit"
    biological.enemy_typ = "Humanoid"
    biological.physical_effects["Bleed"] = _effect()
    biological.physical_effects["Bleed"].active = True

    assert construct.physical_effects["Bleed"].active is True
    assert ("OIL", False) in view._collect_status_icons(construct)
    assert ("RND", False) in view._collect_status_icons(biological)

    view._set_combat_log_actors(SimpleNamespace(name="Hero"), construct)
    view.add_combat_message("Cyborg bleeds for 4 health points.")
    assert view.combat_log[-1] == "Cyborg leaks oil for 4 health points."

    view._set_combat_log_actors(SimpleNamespace(name="Hero"), biological)
    view.add_combat_message("Bandit bleeds for 4 health points.")
    assert view.combat_log[-1] == "Bandit bleeds for 4 health points."


def test_damage_flash_enemy_render_and_combat_render_paths(monkeypatch):
    view = _make_view()
    player = _make_character()
    enemy = SimpleNamespace(
        name="Goblin", health=SimpleNamespace(current=10, max=20), flying=False, tunnel=False
    )
    enemy.status_effects = {}
    enemy.physical_effects = {}
    enemy.stat_effects = {}
    enemy.magic_effects = {}
    enemy.class_effects = {}

    monkeypatch.setattr(
        "src.ui_pygame.gui.combat_view.pygame.Surface",
        lambda size, *_args, **_kwargs: DummySurface(size),
    )
    monkeypatch.setattr("src.ui_pygame.gui.combat_view.pygame.display.flip", lambda: None)
    monkeypatch.setattr(
        "src.ui_pygame.gui.combat_view.pygame.event.get",
        lambda: [
            pygame.event.Event(pygame.KEYDOWN, key=pygame.K_PAGEUP),
            pygame.event.Event(pygame.QUIT),
        ],
    )
    quit_calls = []
    monkeypatch.setattr(
        "src.ui_pygame.gui.combat_view.pygame.quit", lambda: quit_calls.append(True)
    )
    monkeypatch.setattr(
        "src.ui_pygame.gui.combat_view.sys.exit",
        lambda _code=0: (_ for _ in ()).throw(SystemExit()),
    )
    monkeypatch.setattr(
        "src.ui_pygame.gui.combat_view.pygame.time.Clock", lambda: DummyClock(frame_ms=80)
    )

    with pytest.raises(SystemExit):
        view.show_damage_flash(
            True,
            event_handler=lambda event: (
                view.scroll_log(-1) if event.type == pygame.KEYDOWN else None
            ),
        )
    assert quit_calls

    fonts = iter(
        [RecordingFont(), RecordingFont(), RecordingFont(), RecordingFont(), RecordingFont()]
    )
    monkeypatch.setattr(
        "src.ui_pygame.gui.combat_view.pygame.font.Font", lambda *_args, **_kwargs: next(fonts)
    )
    monkeypatch.setattr(
        "src.ui_pygame.gui.combat_view.pygame.draw.circle", lambda *_args, **_kwargs: None
    )
    monkeypatch.setattr(
        "src.ui_pygame.gui.combat_view.pygame.draw.rect", lambda *_args, **_kwargs: None
    )
    monkeypatch.setattr(
        "src.ui_pygame.gui.combat_view.pygame.transform.scale",
        lambda surface, size: DummySurface(size),
    )
    view._render_enemy(enemy, has_sight=True)

    enemy.tunnel = True
    view._render_enemy(enemy, has_sight=True)

    enemy.tunnel = False
    view._has_sight = lambda _player: True
    view._render_enemy = lambda _enemy, _has_sight=True: view.screen.blit(
        DummySurface((10, 10), text="enemy"), (0, 0)
    )
    view._render_enemy_info_panel = lambda *_args, **_kwargs: view.screen.blit(
        DummySurface((10, 10), text="enemy-info"), (0, 0)
    )
    view._render_player_status = lambda _player: view.screen.blit(
        DummySurface((10, 10), text="player"), (0, 0)
    )
    view._render_action_menu = lambda actions, selected: view.screen.blit(
        DummySurface((10, 10), text=f"menu:{selected}"), (0, 0)
    )
    view._render_combat_log = lambda: view.screen.blit(DummySurface((10, 10), text="log"), (0, 0))
    view.render_combat(player, enemy, ["Attack", "Defend"], selected_action=1)
    assert any(
        getattr(surface, "text", "") == "menu:1"
        for surface, _pos, _args, _kwargs in view.screen.blit_calls
    )


def test_impact_effects_use_target_rects_and_expire(monkeypatch):
    view = _make_view()
    line_calls = []
    circle_calls = []
    blit_count = len(view.screen.blit_calls)

    monkeypatch.setattr(
        "src.ui_pygame.gui.combat_view.pygame.Surface",
        lambda size, *_args, **_kwargs: DummySurface(size),
    )
    monkeypatch.setattr(
        "src.ui_pygame.gui.combat_view.pygame.draw.line",
        lambda *_args, **_kwargs: line_calls.append((_args, _kwargs)),
    )
    monkeypatch.setattr(
        "src.ui_pygame.gui.combat_view.pygame.draw.circle",
        lambda *_args, **_kwargs: circle_calls.append((_args, _kwargs)),
    )
    ticks = iter([1000, 1000, 1120, 1700])
    monkeypatch.setattr(
        "src.ui_pygame.gui.combat_view.pygame.time.get_ticks", lambda: next(ticks, 1700)
    )

    view._last_enemy_target_rect = pygame.Rect(100, 120, 80, 100)
    view.trigger_impact_effect("enemy", "spell", "Fire")
    view._render_active_impact_effects()

    assert view._active_impact_effects
    assert line_calls
    assert circle_calls
    assert len(view.screen.blit_calls) > blit_count

    view._prune_impact_effects()
    assert view._active_impact_effects == []


def test_specialized_impact_effects_draw_reflect_status_and_elemental_strike(monkeypatch):
    view = _make_view()
    line_calls = []
    circle_calls = []
    ellipse_calls = []
    blit_count = len(view.screen.blit_calls)

    monkeypatch.setattr(
        "src.ui_pygame.gui.combat_view.pygame.Surface",
        lambda size, *_args, **_kwargs: DummySurface(size),
    )
    monkeypatch.setattr(
        "src.ui_pygame.gui.combat_view.pygame.draw.line",
        lambda *_args, **_kwargs: line_calls.append((_args, _kwargs)),
    )
    monkeypatch.setattr(
        "src.ui_pygame.gui.combat_view.pygame.draw.circle",
        lambda *_args, **_kwargs: circle_calls.append((_args, _kwargs)),
    )
    monkeypatch.setattr(
        "src.ui_pygame.gui.combat_view.pygame.draw.ellipse",
        lambda *_args, **_kwargs: ellipse_calls.append((_args, _kwargs)),
    )
    monkeypatch.setattr("src.ui_pygame.gui.combat_view.pygame.time.get_ticks", lambda: 1000)

    view._last_enemy_target_rect = pygame.Rect(100, 120, 80, 100)
    view.trigger_impact_effect("enemy", "reflect", "Holy")
    view.trigger_impact_effect("enemy", "status")
    view.trigger_impact_effect("enemy", "elemental_strike", "Fire")
    view._render_active_impact_effects()

    assert ellipse_calls
    assert circle_calls
    assert line_calls
    assert len(view.screen.blit_calls) > blit_count


def test_ability_status_visuals_draw_shield_and_rising_smoke_without_duplicate_overlay(monkeypatch):
    view = _make_view()
    rect_calls = []
    ellipse_calls = []
    circle_calls = []
    blit_count = len(view.screen.blit_calls)
    character = SimpleNamespace(
        magic_effects={
            "Duplicates": SimpleNamespace(active=True, duration=2),
            "Mana Shield": SimpleNamespace(active=True),
            "Smoke Screen": SimpleNamespace(active=True),
        }
    )

    monkeypatch.setattr(
        "src.ui_pygame.gui.combat_view.pygame.Surface",
        lambda size, *_args, **_kwargs: DummySurface(size),
    )
    monkeypatch.setattr(
        "src.ui_pygame.gui.combat_view.pygame.draw.rect",
        lambda *_args, **_kwargs: rect_calls.append((_args, _kwargs)),
    )
    monkeypatch.setattr(
        "src.ui_pygame.gui.combat_view.pygame.draw.ellipse",
        lambda *_args, **_kwargs: ellipse_calls.append((_args, _kwargs)),
    )
    monkeypatch.setattr(
        "src.ui_pygame.gui.combat_view.pygame.draw.circle",
        lambda *_args, **_kwargs: circle_calls.append((_args, _kwargs)),
    )
    monkeypatch.setattr("src.ui_pygame.gui.combat_view.pygame.time.get_ticks", lambda: 1000)

    view._last_player_target_rect = pygame.Rect(30, 320, 220, 110)
    view._render_ability_status_visuals(character, "player")

    shield_blits = [
        (surface, position)
        for surface, position, _args, _kwargs in view.screen.blit_calls[blit_count:]
        if position == (10, 170)
    ]
    assert any(
        surface.get_width() >= view.combat_width - 24
        and surface.get_height() <= view.combat_height - 320
        for surface, _position in shield_blits
    )
    assert ellipse_calls
    assert circle_calls
    assert len(view.screen.blit_calls) > blit_count

    smoke_only = SimpleNamespace(magic_effects={})
    circle_calls.clear()
    view.trigger_smoke_screen_visual("enemy")
    view._last_enemy_target_rect = pygame.Rect(200, 160, 120, 160)
    view._render_ability_status_visuals(smoke_only, "enemy", include_duplicates=False)
    assert circle_calls


def test_ability_status_visuals_do_not_draw_active_totem_marker(monkeypatch):
    view = _make_view()
    rect_calls = []
    ellipse_calls = []
    circle_calls = []
    character = SimpleNamespace(
        magic_effects={
            "Totem": SimpleNamespace(
                active=True,
                extra={"aspect": "Fire", "attack_bonus": 0.25, "secondary": "elemental"},
            ),
        }
    )

    monkeypatch.setattr(
        "src.ui_pygame.gui.combat_view.pygame.draw.rect",
        lambda *_args, **_kwargs: rect_calls.append((_args, _kwargs)),
    )
    monkeypatch.setattr(
        "src.ui_pygame.gui.combat_view.pygame.draw.ellipse",
        lambda *_args, **_kwargs: ellipse_calls.append((_args, _kwargs)),
    )
    monkeypatch.setattr(
        "src.ui_pygame.gui.combat_view.pygame.draw.circle",
        lambda *_args, **_kwargs: circle_calls.append((_args, _kwargs)),
    )
    monkeypatch.setattr("src.ui_pygame.gui.combat_view.pygame.time.get_ticks", lambda: 1000)

    view._last_enemy_target_rect = pygame.Rect(200, 160, 120, 160)
    view._render_ability_status_visuals(character, "enemy", include_duplicates=False)

    assert not rect_calls
    assert not ellipse_calls
    assert not circle_calls


def test_combat_feedback_text_recoil_and_low_health_vignette(monkeypatch):
    view = _make_view()
    enemy = SimpleNamespace(name="Goblin")
    player = SimpleNamespace(health=SimpleNamespace(current=8, max=50))
    rect_calls = []
    ellipse_calls = []

    monkeypatch.setattr(
        "src.ui_pygame.gui.combat_view.pygame.Surface",
        lambda size, *_args, **_kwargs: DummySurface(size),
    )
    monkeypatch.setattr(
        "src.ui_pygame.gui.combat_view.pygame.font.Font", lambda *_args, **_kwargs: RecordingFont()
    )
    monkeypatch.setattr(
        "src.ui_pygame.gui.combat_view.pygame.draw.rect",
        lambda *_args, **_kwargs: rect_calls.append((_args, _kwargs)),
    )
    monkeypatch.setattr(
        "src.ui_pygame.gui.combat_view.pygame.draw.ellipse",
        lambda *_args, **_kwargs: ellipse_calls.append((_args, _kwargs)),
    )
    ticks = iter([1000, 1010, 1000, 1240, 1900])
    monkeypatch.setattr(
        "src.ui_pygame.gui.combat_view.pygame.time.get_ticks", lambda: next(ticks, 1900)
    )

    view.enemy_take_damage(enemy)
    assert view._enemy_recoil_offset() != 0

    view._last_enemy_target_rect = pygame.Rect(100, 120, 80, 100)
    view.trigger_floating_text("enemy", "-12", (235, 120, 105))
    view._render_floating_texts()
    assert any(
        getattr(surface, "text", "") == "-12"
        for surface, _pos, _args, _kwargs in view.screen.blit_calls
    )

    view.trigger_floating_text("enemy", "-8", (235, 120, 105))
    view._active_float_texts[-1].start_ms = 0
    view._prune_float_texts()
    assert view._active_float_texts == []

    view._render_player_danger_vignette(player)
    assert ellipse_calls


def test_center_combat_enemy_uses_combat_sprite_manager_not_combat_artwork(monkeypatch):
    view = _make_view()
    calls = []
    enemy = SimpleNamespace(
        name="Goblin",
        health=SimpleNamespace(current=8, max=12),
        flying=False,
        tunnel=False,
    )
    view.enemy_combat_sprite_manager = SimpleNamespace(
        get_sprite_key_for_enemy=lambda _enemy: "goblin",
        get_scaled_sprite_by_key=lambda key, size: calls.append((key, size))
        or DummySurface(size, text="combat-sprite"),
    )

    monkeypatch.setattr(
        "src.ui_pygame.gui.combat_view.pygame.font.Font", lambda *_args, **_kwargs: RecordingFont()
    )
    monkeypatch.setattr(
        "src.ui_pygame.gui.combat_view.pygame.draw.rect", lambda *_args, **_kwargs: None
    )
    monkeypatch.setattr(
        "src.ui_pygame.gui.combat_view.pygame.draw.circle", lambda *_args, **_kwargs: None
    )

    view._render_enemy(enemy, has_sight=True)

    assert calls == [("goblin", (256, 256))]
    assert any(
        getattr(surface, "text", "") == "combat-sprite"
        for surface, _pos, _args, _kwargs in view.screen.blit_calls
    )


def test_prepare_enemy_assets_warms_combat_and_dungeon_sizes():
    view = _make_view()
    calls = []
    enemy = SimpleNamespace(name="Goblin")
    view.enemy_combat_sprite_manager = SimpleNamespace(
        get_sprite_key_for_enemy=lambda _enemy: "goblin",
        get_combat_scale_for_enemy=lambda _enemy: 1.0,
        get_scaled_sprite_by_key=lambda key, size: calls.append((key, size)) or DummySurface(size),
    )

    view.prepare_enemy_assets(enemy)

    assert calls == [("goblin", (256, 256)), ("goblin", (320, 320))]


def test_center_combat_enemy_draws_active_mirror_images(monkeypatch):
    view = _make_view()
    enemy = SimpleNamespace(
        name="Illusionist",
        health=SimpleNamespace(current=8, max=12),
        flying=False,
        tunnel=False,
        magic_effects={
            "Duplicates": SimpleNamespace(active=True, duration=3),
        },
    )
    view.enemy_combat_sprite_manager = SimpleNamespace(
        get_sprite_key_for_enemy=lambda _enemy: "illusionist",
        get_combat_scale_for_enemy=lambda _enemy: 1.0,
        get_scaled_sprite_by_key=lambda key, size: DummySurface(size, text="mirror-combat-sprite"),
    )

    monkeypatch.setattr(
        "src.ui_pygame.gui.combat_view.pygame.font.Font", lambda *_args, **_kwargs: RecordingFont()
    )
    monkeypatch.setattr(
        "src.ui_pygame.gui.combat_view.pygame.draw.rect", lambda *_args, **_kwargs: None
    )
    monkeypatch.setattr("src.ui_pygame.gui.combat_view.pygame.time.get_ticks", lambda: 0)

    view._render_enemy(enemy, has_sight=True)

    sprite_blits = [
        surface
        for surface, _pos, _args, _kwargs in view.screen.blit_calls
        if getattr(surface, "text", "") == "mirror-combat-sprite"
    ]
    assert len(sprite_blits) == 4
    assert [surface.alpha for surface in sprite_blits[:3]] == [118, 104, 90]
    assert sprite_blits[-1].alpha is None


def test_stale_mirror_image_effect_does_not_render_duplicates():
    view = _make_view()
    effect = SimpleNamespace(active=True, duration=0)
    enemy = SimpleNamespace(magic_effects={"Duplicates": effect})

    assert view._active_duplicate_count(enemy) == 0
    assert effect.active is False
    assert effect.duration == 0


def test_center_combat_enemy_fades_while_smoke_screen_active(monkeypatch):
    view = _make_view()
    enemy = SimpleNamespace(
        name="Bandit",
        health=SimpleNamespace(current=8, max=12),
        flying=False,
        tunnel=False,
        magic_effects={
            "Smoke Screen": SimpleNamespace(active=True),
        },
    )
    view.enemy_combat_sprite_manager = SimpleNamespace(
        get_sprite_key_for_enemy=lambda _enemy: "bandit",
        get_combat_scale_for_enemy=lambda _enemy: 1.0,
        get_scaled_sprite_by_key=lambda key, size: DummySurface(size, text="smoke-combat-sprite"),
    )

    monkeypatch.setattr(
        "src.ui_pygame.gui.combat_view.pygame.font.Font", lambda *_args, **_kwargs: RecordingFont()
    )
    monkeypatch.setattr(
        "src.ui_pygame.gui.combat_view.pygame.draw.rect", lambda *_args, **_kwargs: None
    )
    monkeypatch.setattr(
        "src.ui_pygame.gui.combat_view.pygame.draw.ellipse", lambda *_args, **_kwargs: None
    )
    monkeypatch.setattr(
        "src.ui_pygame.gui.combat_view.pygame.draw.circle", lambda *_args, **_kwargs: None
    )
    monkeypatch.setattr("src.ui_pygame.gui.combat_view.pygame.time.get_ticks", lambda: 0)

    view._render_enemy(enemy, has_sight=True)

    sprite_blits = [
        surface
        for surface, _pos, _args, _kwargs in view.screen.blit_calls
        if getattr(surface, "text", "") == "smoke-combat-sprite"
    ]
    assert sprite_blits
    assert sprite_blits[-1].alpha == 77


def test_enemy_hidden_for_flee_skips_sprite_until_log_reset(monkeypatch):
    view = _make_view()
    sprite_calls = []
    enemy = SimpleNamespace(
        name="Bandit",
        health=SimpleNamespace(current=8, max=12),
        flying=False,
        tunnel=False,
        status_effects={},
        physical_effects={},
        stat_effects={},
        magic_effects={},
        class_effects={},
    )
    view.enemy_combat_sprite_manager = SimpleNamespace(
        get_sprite_key_for_enemy=lambda _enemy: "bandit",
        get_combat_scale_for_enemy=lambda _enemy: 1.0,
        get_scaled_sprite_by_key=lambda key, size: sprite_calls.append(("main", key, size))
        or DummySurface(size, text="hidden-bandit"),
        get_scaled_sprite=lambda _enemy, size: sprite_calls.append(("panel", size))
        or DummySurface(size, text="hidden-bandit-panel"),
    )

    monkeypatch.setattr(
        "src.ui_pygame.gui.combat_view.pygame.font.Font", lambda *_args, **_kwargs: RecordingFont()
    )
    monkeypatch.setattr(
        "src.ui_pygame.gui.combat_view.pygame.draw.rect", lambda *_args, **_kwargs: None
    )
    view.hide_enemy_for_flee()
    view._render_enemy(enemy, has_sight=True)
    view._render_enemy_info_panel(enemy, has_sight=True, overlay=True)

    assert not any(
        getattr(surface, "text", "") in {"hidden-bandit", "hidden-bandit-panel"}
        for surface, _pos, _args, _kwargs in view.screen.blit_calls
    )
    assert sprite_calls == []

    view.reset_combat_log()
    view._render_enemy(enemy, has_sight=True)
    view._render_enemy_info_panel(enemy, has_sight=True, overlay=True)

    assert any(
        getattr(surface, "text", "") == "hidden-bandit"
        for surface, _pos, _args, _kwargs in view.screen.blit_calls
    )
    assert any(call[0] == "panel" for call in sprite_calls)


def test_center_combat_boss_uses_mapped_scale_sprite_box(monkeypatch):
    view = _make_view()
    calls = []
    enemy = SimpleNamespace(
        name="Minotaur",
        health=SimpleNamespace(current=80, max=120),
        flying=False,
        tunnel=False,
    )
    view.enemy_combat_sprite_manager = SimpleNamespace(
        get_sprite_key_for_enemy=lambda _enemy: "minotaur",
        get_combat_scale_for_enemy=lambda _enemy: 1.4,
        get_scaled_sprite_by_key=lambda key, size: calls.append((key, size))
        or DummySurface(size, text="boss-combat-sprite"),
    )

    monkeypatch.setattr(
        "src.ui_pygame.gui.combat_view.pygame.font.Font", lambda *_args, **_kwargs: RecordingFont()
    )
    monkeypatch.setattr(
        "src.ui_pygame.gui.combat_view.pygame.draw.rect", lambda *_args, **_kwargs: None
    )

    view._render_enemy(enemy, has_sight=True)

    assert calls == [("minotaur", (840, 840))]
    assert any(
        getattr(surface, "text", "") == "boss-combat-sprite"
        for surface, _pos, _args, _kwargs in view.screen.blit_calls
    )


def test_center_combat_non_boss_can_use_mapped_scale_sprite_box(monkeypatch):
    view = _make_view()
    calls = []
    enemy = SimpleNamespace(
        name="Ogre",
        health=SimpleNamespace(current=60, max=80),
        flying=False,
        tunnel=False,
    )
    view.enemy_combat_sprite_manager = SimpleNamespace(
        get_sprite_key_for_enemy=lambda _enemy: "ogre",
        get_combat_scale_for_enemy=lambda _enemy: 1.2,
        get_scaled_sprite_by_key=lambda key, size: calls.append((key, size))
        or DummySurface(size, text="scaled-ogre"),
    )

    monkeypatch.setattr(
        "src.ui_pygame.gui.combat_view.pygame.font.Font", lambda *_args, **_kwargs: RecordingFont()
    )
    monkeypatch.setattr(
        "src.ui_pygame.gui.combat_view.pygame.draw.rect", lambda *_args, **_kwargs: None
    )

    view._render_enemy(enemy, has_sight=True)

    assert calls == [("ogre", (307, 307))]


def test_render_enemy_in_dungeon_uses_combat_sprite_manager_not_combat_artwork(monkeypatch):
    view = _make_view()
    player = _make_character()
    calls = []
    enemy = SimpleNamespace(
        name="Giant Rat",
        picture="giantrat.txt",
        health=SimpleNamespace(current=8, max=12),
        flying=False,
        tunnel=False,
        status_effects={},
        physical_effects={},
        stat_effects={},
        magic_effects={},
        class_effects={},
    )
    view.enemy_combat_sprite_manager = SimpleNamespace(
        get_sprite_key_for_enemy=lambda _enemy: "giant_rat",
        get_combat_scale_for_enemy=lambda _enemy: 1.25,
        get_scaled_sprite_by_key=lambda key, size: calls.append((key, size))
        or DummySurface(size, text="dungeon-combat-sprite"),
    )

    monkeypatch.setattr(
        "src.ui_pygame.gui.combat_view.pygame.font.Font", lambda *_args, **_kwargs: RecordingFont()
    )
    monkeypatch.setattr(
        "src.ui_pygame.gui.combat_view.pygame.draw.rect", lambda *_args, **_kwargs: None
    )
    monkeypatch.setattr(
        "src.ui_pygame.gui.combat_view.pygame.draw.circle", lambda *_args, **_kwargs: None
    )

    view.render_enemy_in_dungeon(player, enemy)

    assert calls == [("giant_rat", (400, 400))]
    assert any(
        getattr(surface, "text", "") == "dungeon-combat-sprite"
        for surface, _pos, _args, _kwargs in view.screen.blit_calls
    )


def test_generic_combat_sprite_key_renders_manager_fallback(monkeypatch):
    view = _make_view()
    calls = []
    enemy = SimpleNamespace(
        name="Alligator",
        picture="alligator.txt",
        health=SimpleNamespace(current=8, max=12),
        flying=False,
        tunnel=False,
    )
    view.enemy_combat_sprite_manager = SimpleNamespace(
        get_sprite_key_for_enemy=lambda _enemy: "generic_enemy",
        get_scaled_sprite_by_key=lambda key, size: calls.append((key, size))
        or DummySurface(size, text="generic-combat-sprite"),
    )

    monkeypatch.setattr(
        "src.ui_pygame.gui.combat_view.pygame.font.Font", lambda *_args, **_kwargs: RecordingFont()
    )
    monkeypatch.setattr(
        "src.ui_pygame.gui.combat_view.pygame.draw.rect", lambda *_args, **_kwargs: None
    )
    monkeypatch.setattr(
        "src.ui_pygame.gui.combat_view.pygame.draw.circle", lambda *_args, **_kwargs: None
    )

    view._render_enemy(enemy, has_sight=True)

    assert calls == [("generic_enemy", (256, 256))]
    assert any(
        getattr(surface, "text", "") == "generic-combat-sprite"
        for surface, _pos, _args, _kwargs in view.screen.blit_calls
    )
