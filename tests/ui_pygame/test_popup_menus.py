#!/usr/bin/env python3
"""Focused coverage for reusable pygame popup menu helpers."""

from __future__ import annotations

from types import SimpleNamespace

import pygame
import pytest

from src.core import classes, items
from src.ui_pygame.gui import popup_menus


class RenderedText:
    def __init__(self, text):
        self.text = text
        self.width = max(8, len(text) * 8)
        self.height = 18

    def get_width(self):
        return self.width

    def get_height(self):
        return self.height

    def get_rect(self, **kwargs):
        rect = pygame.Rect(0, 0, self.width, self.height)
        for key, value in kwargs.items():
            setattr(rect, key, value)
        return rect


class RecordingFont:
    def __init__(self):
        self.render_calls = []
        self.color_calls = []

    def render(self, text, _antialias, _color):
        self.render_calls.append(text)
        self.color_calls.append((text, _color))
        return RenderedText(text)

    def size(self, text):
        return (max(8, len(text) * 8), 18)

    def get_height(self):
        return 18


class RecordingScreen:
    def __init__(self):
        self.blit_calls = []
        self.fill_calls = []
        self.size = (640, 480)

    def blit(self, surface, position):
        self.blit_calls.append((surface, position))

    def fill(self, color):
        self.fill_calls.append(color)

    def copy(self):
        return "screen-copy"

    def get_size(self):
        return self.size


class DummyItem:
    def __init__(
        self,
        name,
        *,
        typ="Weapon",
        subtyp="Sword",
        description="Useful description text for testing.",
        value=25,
        weight=2,
        qty=None,
        unequip=False,
        passive=False,
        cost=None,
    ):
        self.name = name
        self.typ = typ
        self.subtyp = subtyp
        self.description = description
        self.value = value
        self.weight = weight
        self.qty = qty
        self.unequip = unequip
        self.passive = passive
        if cost is not None:
            self.cost = cost

    def use(self, _player_char):
        return f"Used {self.name}"


class DemoPopup(popup_menus.BasePopupMenu):
    def build_items(self, _player_char):
        self.items = [{"is_header": True, "text": "Header"}, "Alpha", "Beta", "Gamma"]

    def draw_details_extra(self, player_char, item, x, y):
        self.screen.blit(self.normal_font.render(f"Extra:{item}", True, self.WHITE), (x, y))

    def on_select(self, player_char, item):
        return ("selected", item)


class StickyPopup(DemoPopup):
    def __init__(self, presenter, parent_screen, title="Sticky"):
        super().__init__(presenter, parent_screen, title=title)
        self.select_calls = []

    def on_select(self, player_char, item):
        self.select_calls.append(item)
        if len(self.select_calls) == 1:
            return None
        return ("selected", item)


class OverflowPopup(DemoPopup):
    def build_items(self, _player_char):
        self.items = [f"Entry {index}" for index in range(40)]


def _make_presenter():
    return SimpleNamespace(
        screen=RecordingScreen(),
        width=640,
        height=480,
        title_font=RecordingFont(),
        large_font=RecordingFont(),
        normal_font=RecordingFont(),
        small_font=RecordingFont(),
        clock=SimpleNamespace(tick=lambda _fps: None),
        set_background_provider=lambda provider: None,
        show_message=lambda message, **kwargs: None,
    )


def _make_parent():
    calls = []
    return SimpleNamespace(
        draw_all=lambda player_char, do_flip=False: calls.append((player_char, do_flip)),
        calls=calls,
    )


def _make_player():
    inventory = {
        "Weapons": [
            DummyItem("Bronze Sword"),
            DummyItem("Bronze Sword"),
            DummyItem("Apple", typ="Misc", subtyp="Health"),
        ],
        "Helmets": [DummyItem("Iron Helm", typ="Helmet", subtyp="Heavy")],
        "Accessories": [
            DummyItem("Silver Ring", typ="Accessory", subtyp="Ring"),
            DummyItem("Sun Pendant", typ="Accessory", subtyp="Pendant"),
        ],
    }
    equipment = {
        "Weapon": DummyItem("Starter Blade"),
        "Armor": DummyItem("Traveler Coat", typ="Armor", subtyp="Light"),
        "Helmet": DummyItem("No Helmet", typ="Helmet", subtyp="None", unequip=True),
        "OffHand": DummyItem("None", typ="OffHand", subtyp="Shield", unequip=True),
        "Ring": DummyItem("None", typ="Accessory", subtyp="Ring", unequip=True),
        "Pendant": DummyItem("None", typ="Accessory", subtyp="Pendant", unequip=True),
    }
    player = SimpleNamespace(
        inventory=inventory,
        equipment=equipment,
        quest_dict={},
        cls=SimpleNamespace(equip_check=lambda item, slot: True),
        level=SimpleNamespace(level=12),
        special_inventory={"Triangulus": [DummyItem("Triangulus", typ="Misc")]},
        spellbook={"Skills": {"Jump": None, "Totem": None}},
        equip_diff=lambda item, slot, buy=False: "Attack  +2\nDefense  -1",
    )
    return player


def _patch_visuals(monkeypatch):
    monkeypatch.setattr("src.ui_pygame.gui.popup_menus.pygame.display.flip", lambda: None)
    monkeypatch.setattr(
        "src.ui_pygame.gui.popup_menus.pygame.draw.rect", lambda *_args, **_kwargs: None
    )
    monkeypatch.setattr(
        "src.ui_pygame.gui.popup_menus.pygame.Surface",
        lambda size, *_args: SimpleNamespace(fill=lambda *_a, **_k: None),
    )


def test_base_popup_helpers_and_show_navigation(monkeypatch):
    _patch_visuals(monkeypatch)
    presenter = _make_presenter()
    presenter.width = 1024
    presenter.height = 768
    presenter.screen.size = (1024, 768)
    parent = _make_parent()
    popup = DemoPopup(presenter, parent, title="Test")
    player = _make_player()

    assert popup._truncate_text("very long title", 20).endswith("...")
    popup.items = ["A", "B", "C", "D"]
    popup.selected_index = 3
    popup.scroll_offset = 0
    popup._ensure_visible()
    assert popup.scroll_offset >= 0

    popup.items = []
    popup._ensure_visible()
    assert popup.selected_index == 0

    popup.build_items(player)
    popup.draw_background("bg")
    popup.draw_popup(player)
    popup.draw_list()
    popup.draw_details(player)
    popup._capture_menu_surface(player)
    assert parent.calls

    events = iter(
        [
            [SimpleNamespace(type=pygame.KEYDOWN, key=pygame.K_DOWN)],
            [SimpleNamespace(type=pygame.KEYDOWN, key=pygame.K_PAGEDOWN)],
            [SimpleNamespace(type=pygame.KEYDOWN, key=pygame.K_RETURN)],
        ]
    )
    monkeypatch.setattr("src.ui_pygame.gui.popup_menus.pygame.event.get", lambda: next(events, []))
    result = popup.show(player)
    assert result[0] == "selected"


def test_base_popup_supports_mouse_hover_click_and_wheel(monkeypatch):
    _patch_visuals(monkeypatch)
    presenter = _make_presenter()
    parent = _make_parent()
    popup = DemoPopup(presenter, parent, title="Test")
    player = _make_player()
    popup.build_items(player)
    rows = dict(popup.visible_row_rects())

    beta_pos = rows[2].center
    events = iter(
        [
            [SimpleNamespace(type=pygame.MOUSEMOTION, pos=beta_pos)],
            [SimpleNamespace(type=pygame.MOUSEBUTTONDOWN, button=1, pos=beta_pos)],
        ]
    )
    monkeypatch.setattr("src.ui_pygame.gui.popup_menus.pygame.event.get", lambda: next(events, []))

    assert popup.show(player) == ("selected", "Beta")

    popup = DemoPopup(presenter, parent, title="Test")
    popup.build_items(player)
    events = iter(
        [
            [SimpleNamespace(type=pygame.MOUSEWHEEL, y=-1)],
            [SimpleNamespace(type=pygame.KEYDOWN, key=pygame.K_RETURN)],
        ]
    )
    monkeypatch.setattr("src.ui_pygame.gui.popup_menus.pygame.event.get", lambda: next(events, []))

    assert popup.show(player) == ("selected", "Beta")


def test_base_popup_scrollbar_click_repositions_an_overflowing_list(monkeypatch):
    _patch_visuals(monkeypatch)
    presenter = _make_presenter()
    popup = OverflowPopup(presenter, _make_parent(), title="Overflow")
    popup.build_items(_make_player())
    scrollbar = popup.scrollbar_rects()

    assert scrollbar is not None
    track, _thumb = scrollbar
    assert popup._scroll_to_pointer((track.centerx, track.bottom - 1)) is True
    assert popup.scroll_offset == len(popup.items) - popup.visible_row_count()


def test_specials_popup_casts_exploration_spells_with_confirmation(monkeypatch):
    presenter = _make_presenter()
    parent = _make_parent()
    player = _make_player()
    player.name = "Hero"
    player.mana = SimpleNamespace(current=20)
    cast_calls = []
    spell = SimpleNamespace(
        name="Resist Shadow",
        description="Ward against shadow.",
        cost=15,
        exploration_cast=True,
        cast_out=lambda caster: (
            cast_calls.append(caster)
            or setattr(caster.mana, "current", caster.mana.current - 15)
            or "Shadow ward applied."
        ),
    )
    popup = popup_menus.SimpleListPopupMenu(
        presenter,
        parent,
        "Special Abilities",
        lambda _player: [spell],
    )
    popup._capture_menu_surface = lambda _player: "menu-background"
    confirmations = []

    class FakeConfirmation:
        def __init__(self, _presenter, message, show_buttons=True):
            confirmations.append((message, show_buttons))

        def show(self, **kwargs):
            kwargs["background_draw_func"]()
            return True

    monkeypatch.setattr(popup_menus.mechanics, "ConfirmationPopup", FakeConfirmation)

    assert (
        popup.on_select(
            player,
            {"is_header": False, "text": spell.name, "value": spell},
        )
        is None
    )
    assert cast_calls == [player]
    assert player.mana.current == 5
    assert confirmations == [
        ("Cast Resist Shadow?", True),
        ("Shadow ward applied.", False),
    ]


def test_base_popup_ignores_header_click_and_keeps_open_on_none(monkeypatch):
    _patch_visuals(monkeypatch)
    presenter = _make_presenter()
    parent = _make_parent()
    player = _make_player()

    popup = DemoPopup(presenter, parent, title="Test")
    popup.build_items(player)
    rows = dict(popup.visible_row_rects())
    header_pos = rows[0].center
    gamma_pos = rows[3].center
    events = iter(
        [
            [SimpleNamespace(type=pygame.MOUSEBUTTONDOWN, button=1, pos=header_pos)],
            [SimpleNamespace(type=pygame.MOUSEBUTTONDOWN, button=1, pos=gamma_pos)],
        ]
    )
    monkeypatch.setattr("src.ui_pygame.gui.popup_menus.pygame.event.get", lambda: next(events, []))

    assert popup.show(player) == ("selected", "Gamma")

    popup = StickyPopup(presenter, parent, title="Sticky")
    popup.build_items(player)
    rows = dict(popup.visible_row_rects())
    alpha_pos = rows[1].center
    beta_pos = rows[2].center
    parent.calls.clear()
    events = iter(
        [
            [SimpleNamespace(type=pygame.MOUSEBUTTONDOWN, button=1, pos=alpha_pos)],
            [SimpleNamespace(type=pygame.MOUSEBUTTONDOWN, button=1, pos=beta_pos)],
        ]
    )
    monkeypatch.setattr("src.ui_pygame.gui.popup_menus.pygame.event.get", lambda: next(events, []))

    assert popup.show(player) == ("selected", "Beta")
    assert popup.select_calls == ["Alpha", "Beta"]
    assert len(parent.calls) >= 2


def test_selection_popup_preserves_header_line_breaks(monkeypatch):
    _patch_visuals(monkeypatch)
    presenter = _make_presenter()
    popup = popup_menus.SelectionPopup(
        presenter,
        _make_parent(),
        header_message="Purchased 1x Cloak. Equip now?\n\nEquip Now:\nArmor: replaces Tunic",
        options=["Equip Now", "Cancel"],
    )
    popup.items = ["Equip Now", "Cancel"]
    popup.selected_index = 0

    popup.draw_details(_make_player())

    rendered = presenter.normal_font.render_calls
    assert "Purchased 1x Cloak. Equip" in rendered
    assert "now?" in rendered
    assert "Equip Now:" in rendered
    assert "Armor: replaces Tunic" in rendered
    assert "Equip now? Equip Now:" not in rendered


def test_bestiary_popup_uses_kill_dict_and_sight_for_details(monkeypatch):
    presenter = _make_presenter()
    parent = _make_parent()
    popup = popup_menus.BestiaryPopupMenu(presenter, parent)
    player = SimpleNamespace(
        kill_dict={"Regular": {"Goblin": 2, "No Count": 0}},
        bestiary={},
        cls=SimpleNamespace(name="Warrior"),
        equipment={"Pendant": SimpleNamespace(mod="")},
        sight=False,
    )
    draw_calls = []
    monkeypatch.setattr(
        popup,
        "_draw_enemy_sprite",
        lambda _enemy, _rect, enemy_name=None: draw_calls.append(enemy_name),
    )

    popup.build_items(player)

    assert [popup.item_display_text(item) for item in popup.items] == ["Goblin x2"]
    assert "enemy" not in popup.items[0]

    player.kill_dict = {"Regular": {"Zombie": 1}, "Aberration": {"Aberration": 1}}
    popup.build_items(player)
    assert [popup.item_display_text(item) for item in popup.items] == ["Aberration x1", "Zombie x1"]

    player.kill_dict = {"Regular": {"Goblin": 2, "No Count": 0}}
    popup.build_items(player)

    popup.draw_details(player)
    assert "Goblin" in presenter.large_font.render_calls
    assert draw_calls == ["Goblin"]
    assert "Name: Goblin" in presenter.normal_font.render_calls
    assert "Status: Defeated" in presenter.normal_font.render_calls
    assert "Type: Regular" in presenter.normal_font.render_calls
    assert "Seen: 2" in presenter.normal_font.render_calls
    assert "Defeated: 2" in presenter.normal_font.render_calls
    assert "Locations" in presenter.normal_font.render_calls
    assert "Early Dungeon" in presenter.small_font.render_calls
    assert "Possible Drops" in presenter.normal_font.render_calls
    assert "Details unknown." in presenter.normal_font.render_calls

    presenter.normal_font.render_calls.clear()
    presenter.small_font.render_calls.clear()
    player.sight = True
    popup.draw_details(player)

    assert "Details unknown." in presenter.normal_font.render_calls
    assert not any(text.startswith("HP:") for text in presenter.normal_font.render_calls)
    assert not any(text.startswith("Attack:") for text in presenter.normal_font.render_calls)
    assert not any(text.startswith("Experience:") for text in presenter.normal_font.render_calls)

    presenter.normal_font.render_calls.clear()
    player.bestiary = {
        "Goblin": {
            "name": "Goblin",
            "type": "Regular",
            "seen_count": 1,
            "details_unlocked": True,
            "difficulty_level": 1,
            "resistances": {"Fire": 0.25, "Holy": -0.1},
            "known_abilities": ["Hex"],
            "features": ["Sight"],
            "immunities": ["Death"],
        }
    }
    popup.draw_details(player)

    assert "Status: Detailed" in presenter.normal_font.render_calls
    assert "Pro/Difficulty Level: 1" in presenter.normal_font.render_calls
    assert "Resistances" in presenter.normal_font.render_calls
    assert "Fire +25%" in presenter.small_font.render_calls
    assert "Holy -10%" in presenter.small_font.render_calls
    assert "Known Abilities: Hex" in presenter.normal_font.render_calls
    assert "Immunities: Death" in presenter.normal_font.render_calls
    assert "Features: Sight" in presenter.normal_font.render_calls
    assert not any(text.startswith("HP:") for text in presenter.normal_font.render_calls)


def test_bestiary_popup_merges_seen_defeated_and_detailed_entries(monkeypatch):
    presenter = _make_presenter()
    parent = _make_parent()
    popup = popup_menus.BestiaryPopupMenu(presenter, parent)
    player = SimpleNamespace(
        kill_dict={"Regular": {"Goblin": 1}},
        bestiary={
            "Specter": {
                "name": "Specter",
                "type": "Undead",
                "seen_count": 2,
                "details_unlocked": False,
            },
            "Wraith": {
                "name": "Wraith",
                "type": "Undead",
                "seen_count": 1,
                "details_unlocked": True,
                "difficulty_level": 5,
                "resistances": {},
                "known_abilities": ["Soul Drain"],
                "features": [],
                "immunities": [],
            },
        },
    )
    monkeypatch.setattr(popup, "_draw_enemy_sprite", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(popup_menus.pygame.draw, "rect", lambda *_args, **_kwargs: None)

    popup.build_items(player)

    assert [popup.item_display_text(item) for item in popup.items] == [
        "Goblin x1",
        "Specter Seen",
        "Wraith Seen",
    ]
    assert popup.summary_text == "Seen: 3 | Defeated: 1 | Detailed: 1"
    popup.draw_popup(player)
    assert "Seen: 3 | Defeated: 1 | Detailed: 1" in presenter.small_font.render_calls

    popup.selected_index = 1
    popup.draw_details(player)
    assert "Name: Specter" in presenter.normal_font.render_calls
    assert "Status: Seen" in presenter.normal_font.render_calls
    assert "Seen: 2" in presenter.normal_font.render_calls
    assert "Defeated: 0" in presenter.normal_font.render_calls
    assert "Details unknown." in presenter.normal_font.render_calls
    assert "Locations" not in presenter.normal_font.render_calls
    assert "Possible Drops" not in presenter.normal_font.render_calls


def test_bestiary_popup_defeated_entries_show_locations_and_drops(monkeypatch):
    presenter = _make_presenter()
    parent = _make_parent()
    popup = popup_menus.BestiaryPopupMenu(presenter, parent)
    player = SimpleNamespace(
        kill_dict={"Slime": {"Green Slime": 1}},
        bestiary={},
    )
    monkeypatch.setattr(popup, "_draw_enemy_sprite", lambda *_args, **_kwargs: None)
    location_calls = []
    drop_calls = []
    monkeypatch.setattr(
        popup_menus.enemies,
        "bestiary_location_hints",
        lambda enemy_name: location_calls.append(enemy_name) or ["Early Dungeon"],
    )
    monkeypatch.setattr(
        popup_menus.enemies,
        "bestiary_drop_hints",
        lambda enemy, boss=False: drop_calls.append((getattr(enemy, "name", None), boss))
        or ["Key (Common)"],
    )

    popup.build_items(player)
    popup.draw_details(player)
    popup.draw_details(player)

    assert "Status: Defeated" in presenter.normal_font.render_calls
    assert "Locations" in presenter.normal_font.render_calls
    assert "Early Dungeon" in presenter.small_font.render_calls
    assert "Possible Drops" in presenter.normal_font.render_calls
    assert "Key (Common)" in presenter.small_font.render_calls
    assert "Details unknown." in presenter.normal_font.render_calls
    assert location_calls == ["Green Slime"]
    assert drop_calls == [("Green Slime", False)]


def test_bestiary_popup_undetailed_boss_does_not_suggest_vision(monkeypatch):
    presenter = _make_presenter()
    parent = _make_parent()
    popup = popup_menus.BestiaryPopupMenu(presenter, parent)
    player = SimpleNamespace(
        kill_dict={"Dragon": {"Red Dragon": 1}},
        bestiary={},
    )
    monkeypatch.setattr(popup, "_draw_enemy_sprite", lambda *_args, **_kwargs: None)

    popup.build_items(player)
    popup.draw_details(player)

    assert "Details unknown." in presenter.normal_font.render_calls
    assert "Boss details cannot be revealed" in presenter.small_font.render_calls
    assert "with Vision." in presenter.small_font.render_calls
    assert (
        "Use Vision while fighting this enemy to reveal bestiary details."
        not in presenter.small_font.render_calls
    )


def test_bestiary_popup_detailed_defeated_entries_keep_mechanics_with_practical_info(monkeypatch):
    presenter = _make_presenter()
    parent = _make_parent()
    popup = popup_menus.BestiaryPopupMenu(presenter, parent)
    player = SimpleNamespace(
        kill_dict={"Dragon": {"Red Dragon": 1}},
        bestiary={
            "Red Dragon": {
                "name": "Red Dragon",
                "type": "Dragon",
                "seen_count": 1,
                "details_unlocked": True,
                "difficulty_level": 8,
                "resistances": {"Fire": 0.25},
                "known_abilities": ["Breathe Fire"],
                "features": [],
                "immunities": ["Death"],
            },
        },
    )
    monkeypatch.setattr(popup, "_draw_enemy_sprite", lambda *_args, **_kwargs: None)

    popup.build_items(player)
    popup.draw_details(player)

    assert "Status: Detailed" in presenter.normal_font.render_calls
    assert "Locations" in presenter.normal_font.render_calls
    assert "Red Dragon Boss Room" in presenter.small_font.render_calls
    assert "Possible Drops" in presenter.normal_font.render_calls
    assert "Dragon's Tear (Very Rare)" in presenter.small_font.render_calls
    assert "Pro/Difficulty Level: 8" in presenter.normal_font.render_calls
    assert "Resistances" in presenter.normal_font.render_calls
    assert "Known Abilities: Breathe Fire" in presenter.normal_font.render_calls


def test_bestiary_popup_resolves_mimic_details_and_art_lazily(monkeypatch):
    presenter = _make_presenter()
    parent = _make_parent()
    popup = popup_menus.BestiaryPopupMenu(presenter, parent)
    player = SimpleNamespace(
        kill_dict={"Aberration": {"Mimic": 1}},
        bestiary={
            "Mimic": {
                "name": "Mimic",
                "type": "Aberration",
                "seen_count": 1,
                "details_unlocked": True,
                "difficulty_level": 2,
                "resistances": {},
                "known_abilities": [],
                "features": ["Boss"],
            }
        },
        cls=SimpleNamespace(name="Seeker"),
        equipment={"Pendant": SimpleNamespace(mod="")},
        sight=False,
    )
    draw_calls = []
    monkeypatch.setattr(
        popup,
        "_draw_enemy_sprite",
        lambda enemy, _rect, enemy_name=None: draw_calls.append(
            (getattr(enemy, "name", None), enemy_name)
        ),
    )

    popup.build_items(player)

    assert [popup.item_display_text(item) for item in popup.items] == ["Mimic x1"]
    assert "enemy" not in popup.items[0]

    popup.draw_details(player)

    assert draw_calls == [("Mimic", "Mimic")]
    assert "Resistances" in presenter.normal_font.render_calls
    assert "None" in presenter.small_font.render_calls
    assert "Known Abilities: None observed" in presenter.normal_font.render_calls
    assert not any(text.startswith("HP:") for text in presenter.normal_font.render_calls)


def test_base_popup_quick_scrolls_when_arrow_key_is_held(monkeypatch):
    presenter = _make_presenter()
    parent = _make_parent()
    popup = DemoPopup(presenter, parent, title="Test")
    popup.items = ["Alpha", "Beta", "Gamma", "Delta"]
    popup.selected_index = 0
    popup.quick_scroll_delay = 2

    class PressedKeys:
        def __getitem__(self, key):
            return key == pygame.K_DOWN

    pressed = PressedKeys()
    monkeypatch.setattr("src.ui_pygame.gui.popup_menus.pygame.key.get_pressed", lambda: pressed)

    popup._handle_held_scroll()
    assert popup.selected_index == 0

    popup._handle_held_scroll()
    assert popup.selected_index == 1


def test_equipment_popup_wraps_long_plain_descriptions(monkeypatch):
    presenter = _make_presenter()
    parent = _make_parent()
    player = _make_player()
    player.equipment["Pendant"] = DummyItem(
        "Wind Amulet",
        typ="Accessory",
        subtyp="Pendant",
        description="A long wind-blessed amulet description that should move onto additional lines instead of running off the details panel.",
    )
    popup = popup_menus.EquipmentPopupMenu(presenter, parent)
    popup.build_items(player)
    popup.selected_index = 5
    monkeypatch.setattr(
        "src.ui_pygame.gui.popup_menus.pygame.draw.rect", lambda *_args, **_kwargs: None
    )

    popup.draw_details(player)

    assert "Description:" in presenter.normal_font.render_calls
    assert not any(
        call.startswith("Description: A long wind-blessed amulet description")
        for call in presenter.normal_font.render_calls
    )
    assert not any(call.startswith("Slot:") for call in presenter.normal_font.render_calls)
    assert not any(call.startswith("Value:") for call in presenter.normal_font.render_calls)


def test_base_popup_can_wait_for_key_release_before_accepting_input(monkeypatch):
    _patch_visuals(monkeypatch)
    presenter = _make_presenter()
    parent = _make_parent()
    popup = DemoPopup(presenter, parent, title="Test")
    player = _make_player()

    events = iter(
        [
            [SimpleNamespace(type=pygame.KEYDOWN, key=pygame.K_RETURN)],
            [SimpleNamespace(type=pygame.KEYUP, key=pygame.K_RETURN)],
            [SimpleNamespace(type=pygame.KEYDOWN, key=pygame.K_RETURN)],
        ]
    )
    monkeypatch.setattr("src.ui_pygame.gui.popup_menus.pygame.event.get", lambda: next(events, []))
    monkeypatch.setattr("src.ui_pygame.gui.input_guards.pygame.key.get_pressed", lambda: [1])

    result = popup.show(player, require_key_release=True)

    assert result == ("selected", "Alpha")


def test_base_popup_accepts_fresh_key_without_keyup(monkeypatch):
    _patch_visuals(monkeypatch)
    presenter = _make_presenter()
    parent = _make_parent()
    popup = DemoPopup(presenter, parent, title="Test")
    player = _make_player()

    events = iter(
        [
            [SimpleNamespace(type=pygame.KEYDOWN, key=pygame.K_RETURN)],
        ]
    )
    clear_calls = []
    monkeypatch.setattr("src.ui_pygame.gui.popup_menus.pygame.event.get", lambda: next(events, []))
    monkeypatch.setattr(
        "src.ui_pygame.gui.popup_menus.pygame.event.clear", lambda: clear_calls.append(True)
    )
    monkeypatch.setattr("src.ui_pygame.gui.input_guards.pygame.key.get_pressed", lambda: [])

    result = popup.show(player, flush_events=True, require_key_release=True)

    assert result == ("selected", "Alpha")
    assert clear_calls == [True]


def test_base_popup_restores_background_provider_on_error(monkeypatch):
    _patch_visuals(monkeypatch)
    providers = []
    presenter = _make_presenter()
    presenter._background_provider = "previous-provider"
    presenter.set_background_provider = lambda provider: providers.append(provider) or setattr(
        presenter,
        "_background_provider",
        provider,
    )
    parent = _make_parent()

    class ExplodingPopup(DemoPopup):
        def draw_list(self):
            raise RuntimeError("boom")

    popup = ExplodingPopup(presenter, parent, title="Test")

    with pytest.raises(RuntimeError, match="boom"):
        popup.show(_make_player())

    assert providers[-1] == "previous-provider"
    assert presenter._background_provider == "previous-provider"


def test_inventory_popup_build_sort_cycle_and_item_actions(monkeypatch):
    _patch_visuals(monkeypatch)
    presenter = _make_presenter()
    parent = _make_parent()
    player = _make_player()
    popup = popup_menus.InventoryPopupMenu(presenter, parent)

    popup.build_items(player)
    assert popup.title.startswith("Inventory [Name]")
    assert popup.item_display_text(("Weapons", DummyItem("Potion", qty=3), 1)) == "Potion x3"
    assert popup._is_combat_usable(DummyItem("Potion", typ="Misc", subtyp="Health")) is True
    assert (
        popup._is_combat_usable(DummyItem("Sanctuary Scroll", typ="Misc", subtyp="Scroll")) is False
    )

    popup.handle_key_down(player, SimpleNamespace(key=pygame.K_s))
    assert popup.title.startswith("Inventory [Type]")
    assert player.inventory_sort_mode == "Type"

    notices = []

    class FakePopup:
        def __init__(self, _presenter, message, show_buttons=True):
            notices.append((message, show_buttons))

        def show(self, **kwargs):
            assert kwargs["flush_events"] is True
            assert kwargs["require_key_release"] is True
            kwargs["background_draw_func"]()
            return True

    monkeypatch.setattr(popup_menus.inventory, "ConfirmationPopup", FakePopup)
    no_equip_player = _make_player()
    no_equip_player.cls = SimpleNamespace(equip_check=lambda item, slot: False)
    popup._equip_item(
        no_equip_player, DummyItem("Forbidden"), "Weapons", background_surface="inventory-bg"
    )
    assert notices == [("You cannot equip Forbidden.", False)]

    player.equipment["Weapon"] = DummyItem("No Weapon", unequip=True)
    popup._equip_item(player, player.inventory["Weapons"][0], "Weapons")
    assert player.equipment["Weapon"].name == "Bronze Sword"

    confirm_calls = []

    class FakeConfirm:
        def __init__(self, *_args, **_kwargs):
            pass

        def show(self, **_kwargs):
            confirm_calls.append(_kwargs)
            return True

    monkeypatch.setattr(popup_menus.inventory, "ConfirmationPopup", FakeConfirm)
    popup._use_item(player, player.inventory["Weapons"][0], "Weapons", background_surface="bg")
    assert "Weapons" in player.inventory
    popup._drop_item(player, player.inventory["Weapons"][0], "Weapons", background_surface="bg")
    assert any(call.get("flush_events") for call in confirm_calls)


def test_inventory_popup_draw_list_renders_item_icons(monkeypatch):
    _patch_visuals(monkeypatch)
    presenter = _make_presenter()
    parent = _make_parent()
    player = _make_player()
    popup = popup_menus.InventoryPopupMenu(presenter, parent)
    popup.build_items(player)
    popup.item_render_manager = SimpleNamespace(
        get_scaled_render=lambda _item, size: pygame.surface.Surface(size, pygame.SRCALPHA)
    )
    icon_calls = []
    popup.icon_manager = SimpleNamespace(
        get_icon=lambda item, **_kwargs: icon_calls.append(getattr(item, "name", ""))
        or pygame.surface.Surface((32, 32), pygame.SRCALPHA)
    )

    popup.draw_list()

    assert icon_calls
    assert any(
        name in icon_calls for name in {"Bronze Sword", "Apple", "Silver Ring", "Sun Pendant"}
    )
    assert presenter.screen.blit_calls


def test_inventory_and_equipment_details_render_large_item_art(monkeypatch):
    _patch_visuals(monkeypatch)
    presenter = _make_presenter()
    presenter.width = 1024
    presenter.height = 768
    presenter.screen.size = (1024, 768)
    parent = _make_parent()
    player = _make_player()
    render_calls = []
    fake_render_manager = SimpleNamespace(
        get_scaled_render=lambda item, size: render_calls.append((getattr(item, "name", ""), size))
        or pygame.surface.Surface(size, pygame.SRCALPHA)
    )

    inventory = popup_menus.InventoryPopupMenu(presenter, parent)
    inventory.build_items(player)
    inventory.item_render_manager = fake_render_manager
    inventory.draw_details(player)

    equipment = popup_menus.EquipmentPopupMenu(presenter, parent)
    equipment.build_items(player)
    equipment.item_render_manager = fake_render_manager
    equipment.draw_details(player)

    assert any(
        name in {"Bronze Sword", "Apple", "Silver Ring", "Sun Pendant"}
        for name, _size in render_calls
    )
    assert ("Starter Blade", (142, 114)) in render_calls


def test_inventory_details_center_name_and_hide_category(monkeypatch):
    _patch_visuals(monkeypatch)
    presenter = _make_presenter()
    presenter.width = 1024
    presenter.height = 768
    presenter.screen.size = (1024, 768)
    parent = _make_parent()
    player = _make_player()
    popup = popup_menus.InventoryPopupMenu(presenter, parent)
    popup.build_items(player)
    popup.selected_index = next(
        index
        for index, (_category, obj, _count) in enumerate(popup.items)
        if getattr(obj, "name", "") == "Bronze Sword"
    )
    popup.item_render_manager = SimpleNamespace(
        get_scaled_render=lambda _item, size: pygame.surface.Surface(size, pygame.SRCALPHA)
    )

    popup.draw_details(player)

    assert not any(call.startswith("Category:") for call in presenter.normal_font.render_calls)
    assert "Sub-type: Sword" in presenter.normal_font.render_calls
    assert "Description:" in presenter.normal_font.render_calls
    assert not any(
        call.startswith("Description:") and call != "Description:"
        for call in presenter.normal_font.render_calls
    )
    name_blits = [
        position
        for surface, position in presenter.screen.blit_calls
        if getattr(surface, "text", None) == "Bronze Sword"
    ]
    assert name_blits
    expected_x = popup.details_rect.centerx - (len("Bronze Sword") * 8) // 2
    assert name_blits[-1][0] == expected_x


def test_popup_visible_row_count_reserves_bottom_padding(monkeypatch):
    _patch_visuals(monkeypatch)
    popup = DemoPopup(_make_presenter(), _make_parent())
    popup.items = [f"Item {index}" for index in range(30)]

    assert popup.list_vertical_padding() == 16
    assert popup.visible_row_count() == max(1, (popup.list_rect.height - 32) // popup.line_height)


def test_base_popup_skips_icons_for_plain_labels(monkeypatch):
    _patch_visuals(monkeypatch)
    presenter = _make_presenter()
    parent = _make_parent()
    popup = popup_menus.BasePopupMenu(presenter, parent, title="Labels")
    popup.items = [
        {"is_header": False, "text": "Bounty", "value": "Bounty"},
        ("[Main] First Quest", "Main", "First Quest", {}),
        "Side",
    ]
    popup.icon_manager = SimpleNamespace(
        get_icon=lambda _item, **_kwargs: pytest.fail("plain labels should not request icons")
    )

    popup.draw_list()
    popup.draw_details(_make_player())


def test_simple_list_draw_list_only_icons_item_objects(monkeypatch):
    _patch_visuals(monkeypatch)
    presenter = _make_presenter()
    parent = _make_parent()
    player = _make_player()
    popup = popup_menus.SimpleListPopupMenu(
        presenter,
        parent,
        "Simple",
        lambda _player: [
            "--- Header ---",
            DummyItem("Lore Entry", typ="Misc"),
            SimpleNamespace(name="Shield Slam", description="Ability text."),
            "Plain",
        ],
    )
    popup.build_items(player)
    icon_calls = []
    popup.icon_manager = SimpleNamespace(
        get_icon=lambda item, **_kwargs: icon_calls.append(getattr(item, "name", str(item)))
        or pygame.surface.Surface((32, 32), pygame.SRCALPHA)
    )

    popup.draw_list()

    assert icon_calls == ["Lore Entry"]


def test_simple_list_key_item_details_use_large_art_layout(monkeypatch):
    _patch_visuals(monkeypatch)
    presenter = _make_presenter()
    parent = _make_parent()
    player = _make_player()
    popup = popup_menus.SimpleListPopupMenu(
        presenter,
        parent,
        "Key Items",
        lambda _player: [
            DummyItem(
                "Ancient Key",
                typ="Misc",
                subtyp="Key",
                description="Opens a sealed vault.",
                value=0,
                weight=0,
            )
        ],
    )
    popup.build_items(player)
    render_calls = []
    popup.item_render_manager = SimpleNamespace(
        get_scaled_render=lambda item, size: render_calls.append((getattr(item, "name", ""), size))
        or pygame.surface.Surface(size, pygame.SRCALPHA)
    )

    popup.draw_details(player)

    assert render_calls and render_calls[0][0] == "Ancient Key"
    assert "Ancient Key" in presenter.large_font.render_calls
    assert "Description:" in presenter.normal_font.render_calls
    assert "Value: 0G" not in presenter.normal_font.render_calls
    assert "Weight: 0" not in presenter.normal_font.render_calls


def test_simple_list_ability_card_renders_multiple_modifications_separately(monkeypatch):
    _patch_visuals(monkeypatch)
    presenter = _make_presenter()
    ability = SimpleNamespace(
        name="Firebolt",
        description="A mote of fire propelled at the foe.",
        subtyp="Fire",
        cost=2,
        passive=False,
        presentation_modifications=(
            SimpleNamespace(name="Fire Inside", description="Grants a critical charge."),
            SimpleNamespace(name="Focused Flame", description="Improves focused casting."),
        ),
    )
    popup = popup_menus.SimpleListPopupMenu(
        presenter,
        _make_parent(),
        "Special Abilities",
        lambda _player: [ability],
    )
    popup.build_items(_make_player())

    popup.draw_details(_make_player())

    rendered = presenter.normal_font.render_calls
    assert "Modifications" in rendered
    assert any(text.startswith("Fire Inside:") for text in rendered)
    assert any(text.startswith("Focused Flame:") for text in rendered)
    assert all("Fire Inside" not in text for text in rendered[:1])


def test_simple_list_relic_key_item_details_use_relic_sprite(monkeypatch):
    _patch_visuals(monkeypatch)
    presenter = _make_presenter()
    parent = _make_parent()
    player = _make_player()
    popup = popup_menus.SimpleListPopupMenu(
        presenter,
        parent,
        "Key Items",
        lambda _player: [DummyItem("Triangulus", typ="Misc", subtyp="Special", value=0, weight=0)],
    )
    popup.build_items(player)
    popup.item_render_manager = SimpleNamespace(
        get_scaled_render=lambda _item, _size: pytest.fail(
            "relic sprites should bypass the item render atlas"
        )
    )
    relic_surface = pygame.surface.Surface((32, 32), pygame.SRCALPHA)
    monkeypatch.setattr(
        "src.ui_pygame.gui.popup_menus.pygame.image.load", lambda _path: relic_surface
    )

    popup.draw_details(player)

    assert "Triangulus" in presenter.large_font.render_calls
    assert presenter.screen.blit_calls


def test_inventory_popup_on_select_uses_nested_selection_popup(monkeypatch):
    _patch_visuals(monkeypatch)
    presenter = _make_presenter()
    parent = _make_parent()
    player = _make_player()
    popup = popup_menus.InventoryPopupMenu(presenter, parent)
    popup.build_items(player)
    popup.item_render_manager = SimpleNamespace(
        get_scaled_render=lambda _item, size: pygame.surface.Surface(size, pygame.SRCALPHA)
    )

    actions = iter(
        [
            ("selection", "Equip"),
            ("selection", "Use"),
            ("selection", "Drop"),
            ("selection", "Cancel"),
        ]
    )

    class FakeSelectionPopup:
        def __init__(self, *_args, **_kwargs):
            self.draw_background = lambda surf: None

        def show(self, _player_char, **_kwargs):
            assert _kwargs["flush_events"] is True
            assert _kwargs["require_key_release"] is True
            return next(actions)

    monkeypatch.setattr(popup_menus.inventory, "SelectionPopup", FakeSelectionPopup)
    monkeypatch.setattr(popup, "_equip_item", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(popup, "_use_item", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(popup, "_drop_item", lambda *_args, **_kwargs: None)
    popup.on_select(player, popup.items[0])


def test_inventory_popup_restores_nested_action_background_on_error(monkeypatch):
    _patch_visuals(monkeypatch)
    presenter = _make_presenter()
    parent = _make_parent()
    player = _make_player()
    popup = popup_menus.InventoryPopupMenu(presenter, parent)
    popup.build_items(player)
    popup.item_render_manager = SimpleNamespace(
        get_scaled_render=lambda _item, size: pygame.surface.Surface(size, pygame.SRCALPHA)
    )

    class ExplodingSelectionPopup:
        def __init__(self, *_args, **_kwargs):
            self.draw_background = lambda surf: "original"

        def show(self, _player_char, **_kwargs):
            raise RuntimeError("nested boom")

    action_popup_ref = {}

    def fake_selection_popup(*args, **kwargs):
        action_popup = ExplodingSelectionPopup(*args, **kwargs)
        action_popup_ref["popup"] = action_popup
        return action_popup

    monkeypatch.setattr(popup_menus.inventory, "SelectionPopup", fake_selection_popup)

    with pytest.raises(RuntimeError, match="nested boom"):
        popup.on_select(player, popup.items[0])

    assert action_popup_ref["popup"].draw_background("bg") == "original"


def test_equipment_popup_build_details_and_selection_flows(monkeypatch):
    _patch_visuals(monkeypatch)
    presenter = _make_presenter()
    parent = _make_parent()
    player = _make_player()
    popup = popup_menus.EquipmentPopupMenu(presenter, parent)
    popup.item_render_manager = SimpleNamespace(
        get_scaled_render=lambda _item, size: pygame.surface.Surface(size, pygame.SRCALPHA)
    )

    popup.build_items(player)
    assert popup.item_display_text(
        ("Weapon", DummyItem("Very Long Equipment Name That Truncates"))
    ).startswith("Weapon:")
    popup.draw_details(player)

    equippable = popup._get_equippable_items_for_slot(player, "Ring")
    assert any(item.name == "Silver Ring" for item in equippable)
    helmet_options = popup._get_equippable_items_for_slot(player, "Helmet")
    assert any(item.name == "Iron Helm" for item in helmet_options)

    new_ring = DummyItem("Ruby Ring", typ="Accessory", subtyp="Ring")
    player.inventory.setdefault("Ruby Ring", []).append(new_ring)
    popup._equip_from_inventory(player, "Ring", new_ring)
    assert player.equipment["Ring"].name == "Ruby Ring"

    new_helmet = DummyItem("Leather Cap", typ="Helmet", subtyp="Light")
    player.inventory.setdefault("Leather Cap", []).append(new_helmet)
    popup._equip_from_inventory(player, "Helmet", new_helmet)
    assert player.equipment["Helmet"].name == "Leather Cap"

    popup._unequip_item(player, "Ring", player.equipment["Ring"])
    assert player.equipment["Ring"].name == "No Ring"
    popup._unequip_item(player, "Helmet", player.equipment["Helmet"])
    assert player.equipment["Helmet"].name == "No Helmet"

    class FakeEquipPopup:
        def __init__(self, *_args, **_kwargs):
            self.draw_background = lambda surf: None

        def show(self, _player_char, **_kwargs):
            assert _kwargs["flush_events"] is True
            assert _kwargs["require_key_release"] is True
            return ("selection", "Cancel")

    flips = []
    monkeypatch.setattr(pygame.display, "flip", lambda: flips.append("flip"))
    monkeypatch.setattr(popup_menus.equipment, "EquipmentSelectionPopup", FakeEquipPopup)
    assert popup.on_select(player, popup.items[0]) is None
    assert flips == []


def test_equipment_popup_uses_player_equip_logic_for_two_handed_weapons(monkeypatch):
    _patch_visuals(monkeypatch)
    presenter = _make_presenter()
    parent = _make_parent()
    player = _make_player()
    popup = popup_menus.EquipmentPopupMenu(presenter, parent)

    two_hander = SimpleNamespace(name="Great Pike", typ="Weapon", subtyp="Polearm", handed=2)
    player.inventory.setdefault("Weapons", []).append(two_hander)
    player.equipment["OffHand"] = DummyItem(
        "Kite Shield", typ="OffHand", subtyp="Shield", unequip=False
    )
    calls = []

    def fake_equip(slot, item):
        calls.append((slot, item.name))
        if slot == "Weapon" and getattr(item, "handed", 1) == 2:
            player.equipment["OffHand"] = DummyItem(
                "None", typ="OffHand", subtyp="Shield", unequip=True
            )
        player.equipment[slot] = item
        if item in player.inventory["Weapons"]:
            player.inventory["Weapons"].remove(item)
        return True

    player.equip = fake_equip

    popup._equip_from_inventory(player, "Weapon", two_hander)

    assert calls == [("Weapon", "Great Pike")]
    assert player.equipment["Weapon"].name == "Great Pike"
    assert player.equipment["OffHand"].name == "None"


def test_equipment_selection_popup_right_aligns_values_and_shows_handedness(monkeypatch):
    _patch_visuals(monkeypatch)
    presenter = _make_presenter()
    parent = _make_parent()
    player = _make_player()
    two_hander = DummyItem("Bastard Sword", typ="Weapon", subtyp="Longsword")
    two_hander.handed = 2
    player.inventory = {"Weapons": [two_hander]}
    player.equip_diff = lambda _item, _slot, buy=False: "\n".join(
        [
            f"{'Attack':16}  {'36 -> 40':>6}",
            f"{'Armor':16}  {'12 -> 8':>6}",
            f"{'Buffs':16}  {'Magic Dodge':>6}",
        ]
    )
    popup = popup_menus.EquipmentSelectionPopup(
        presenter,
        parent,
        title="Weapon Slot",
        options=["Bastard Sword"],
        slot="Weapon",
        current_item=player.equipment["Weapon"],
        player_char=player,
    )
    render_calls = []
    popup.item_render_manager = SimpleNamespace(
        get_scaled_render=lambda item, size: render_calls.append((getattr(item, "name", ""), size))
        or pygame.surface.Surface(size, pygame.SRCALPHA)
    )

    popup.build_items(player)
    popup.draw_details(player)

    assert render_calls == [("Bastard Sword", (88, 92))]
    rendered = presenter.large_font.render_calls + presenter.normal_font.render_calls
    assert "Bastard Sword (2H)" in rendered
    assert (
        popup._equipment_display_name(DummyItem("Dirk", typ="Weapon", subtyp="Dagger"))
        == "Dirk (1H)"
    )
    assert "Hands" not in rendered
    assert "Two-handed" not in rendered
    assert "Attack" in rendered
    assert "36 -> 40" in rendered
    assert "Armor" in rendered
    assert "12 -> 8" in rendered
    assert "Buffs" in rendered
    assert "Magic Dodge" in rendered

    positions = {
        surface.text: position[0]
        for surface, position in presenter.screen.blit_calls
        if getattr(surface, "text", None) in {"Attack", "36 -> 40"}
    }
    assert positions["36 -> 40"] > positions["Attack"]

    colors = dict(presenter.normal_font.color_calls)
    assert colors["Attack"] == popup.GREEN
    assert colors["36 -> 40"] == popup.GREEN
    assert colors["Armor"] == popup.RED
    assert colors["12 -> 8"] == popup.RED
    assert colors["Buffs"] == popup.LIGHT_GRAY
    assert colors["Magic Dodge"] == popup.LIGHT_GRAY
    assert popup._diff_value_direction("10/5 -> 20") == 1
    assert popup._diff_value_direction("20 -> 10/5") == -1
    assert popup._diff_value_direction("+25% -> +75%") == 1
    assert popup._diff_value_direction("Magic Dodge") == 0


def test_equipment_popup_offhand_includes_allowed_weapons(monkeypatch):
    _patch_visuals(monkeypatch)
    presenter = _make_presenter()
    parent = _make_parent()
    player = _make_player()
    popup = popup_menus.EquipmentPopupMenu(presenter, parent)

    fist = DummyItem("Indra's Fist", typ="Weapon", subtyp="Fist")
    sword = DummyItem("Offhand Sword", typ="Weapon", subtyp="Sword")
    shield = DummyItem("Buckler", typ="OffHand", subtyp="Shield")
    player.inventory.setdefault("Weapons", []).extend([fist, sword])
    player.inventory.setdefault("Shields", []).append(shield)
    player.cls = SimpleNamespace(
        equip_check=lambda item, slot: slot == "OffHand" and item.subtyp in {"Fist", "Shield"}
    )

    equippable = popup._get_equippable_items_for_slot(player, "OffHand")

    assert any(item.name == "Indra's Fist" for item in equippable)
    assert any(item.name == "Buckler" for item in equippable)
    assert all(item.name != "Offhand Sword" for item in equippable)


def test_equipment_popup_weapon_slot_excludes_class_restricted_weapons(monkeypatch):
    _patch_visuals(monkeypatch)
    presenter = _make_presenter()
    parent = _make_parent()
    player = _make_player()
    popup = popup_menus.EquipmentPopupMenu(presenter, parent)

    player.cls = classes.Healer()
    staff = items.Quarterstaff()
    sledgehammer = items.Sledgehammer()
    player.inventory = {"Weapons": [staff, sledgehammer]}

    equippable = popup._get_equippable_items_for_slot(player, "Weapon")

    assert any(item.name == "Quarterstaff" for item in equippable)
    assert all(item.name != "Sledgehammer" for item in equippable)


def test_quest_popup_build_and_details_cover_main_side_and_bounty(monkeypatch):
    _patch_visuals(monkeypatch)
    presenter = _make_presenter()
    parent = _make_parent()
    player = _make_player()
    player.quest_dict = {
        "Main": {
            "Main Quest": {
                "Type": "Defeat",
                "What": "Dragon",
                "Completed": False,
                "Turned In": False,
                "Experience": 100,
                "Help Text": "The dragon has returned to the mountain pass.",
            },
            "Turned Quest": {
                "Type": "Locate",
                "What": "Tower",
                "Completed": True,
                "Turned In": True,
            },
        },
        "Side": {
            "Relic Hunt": {
                "Type": "Collect",
                "What": "Relics",
                "Total": 6,
                "Completed": True,
                "Turned In": False,
                "Reward": ["Gold"],
                "Reward Number": 50,
            },
        },
        "Bounty": {
            "Goblin Hunt": [
                {"enemy": SimpleNamespace(name="Goblin"), "num": 3, "gold": 40, "exp": 20},
                1,
                False,
            ],
        },
    }
    popup = popup_menus.QuestPopupMenu(presenter, parent)
    popup.build_items(player)
    assert any(isinstance(item, dict) and item.get("is_header") for item in popup.items)
    popup.icon_manager = SimpleNamespace(
        get_icon=lambda _item, **_kwargs: pytest.fail("quest labels should not request icons")
    )
    popup.draw_list()
    popup.draw_details(player)
    assert "Description:" in presenter.normal_font.render_calls
    assert any("dragon has returned" in call for call in presenter.normal_font.render_calls)
    assert "Defeated: 0/1" in presenter.normal_font.render_calls
    assert popup.on_select(player, popup.items[0]) is None


def test_quest_popup_draws_reward_icons(monkeypatch):
    _patch_visuals(monkeypatch)
    presenter = _make_presenter()
    parent = _make_parent()
    player = _make_player()
    player.quest_dict = {
        "Side": {
            "Reward Quest": {
                "Type": "Collect",
                "What": "Relics",
                "Total": 1,
                "Completed": False,
                "Turned In": False,
                "Reward": ["Gold"],
                "Reward Number": 50,
            }
        }
    }
    popup = popup_menus.QuestPopupMenu(presenter, parent)
    popup.build_items(player)
    icon_calls = []
    popup.icon_manager = SimpleNamespace(
        get_icon=lambda item, **_kwargs: icon_calls.append(getattr(item, "name", item))
        or pygame.surface.Surface((32, 32), pygame.SRCALPHA)
    )

    popup.draw_details(player)

    assert icon_calls == ["Gold"]
    assert "50 Gold" in presenter.normal_font.render_calls


def test_turned_in_collection_quest_retains_completed_progress(monkeypatch):
    _patch_visuals(monkeypatch)
    presenter = _make_presenter()
    parent = _make_parent()
    player = _make_player()
    player.inventory = {}
    player.special_inventory = {}
    player.quest_dict = {
        "Side": {
            "Rat Trap": {
                "Type": "Collect",
                "What": "RatTail",
                "Total": 6,
                "Completed": True,
                "Turned In": True,
            }
        }
    }
    popup = popup_menus.QuestPopupMenu(presenter, parent)
    popup.build_items(player)
    popup.selected_index = next(
        index for index, item in enumerate(popup.items) if isinstance(item, tuple)
    )

    popup.draw_details(player)

    assert "Collected: 6/6" in presenter.normal_font.render_calls
    assert "Collected: 0/6" not in presenter.normal_font.render_calls


def test_quest_popup_draws_bounty_rewards_like_regular_rewards(monkeypatch):
    _patch_visuals(monkeypatch)
    presenter = _make_presenter()
    parent = _make_parent()
    player = _make_player()
    player.quest_dict = {
        "Bounty": {
            "Goblin Hunt": [
                {
                    "enemy": SimpleNamespace(name="Goblin"),
                    "num": 3,
                    "gold": 40,
                    "exp": 20,
                    "reward": lambda: DummyItem("Goblin Charm", typ="Misc"),
                },
                1,
                False,
            ],
        },
    }
    popup = popup_menus.QuestPopupMenu(presenter, parent)
    popup.build_items(player)
    icon_calls = []
    popup.icon_manager = SimpleNamespace(
        get_icon=lambda item, **_kwargs: icon_calls.append(getattr(item, "name", item))
        or pygame.surface.Surface((32, 32), pygame.SRCALPHA)
    )

    popup.draw_details(player)

    assert "Rewards:" in presenter.normal_font.render_calls
    assert "40 Gold" in presenter.normal_font.render_calls
    assert "20 Experience" in presenter.normal_font.render_calls
    assert "Goblin Charm" in presenter.normal_font.render_calls
    assert "+ Item Reward" not in presenter.normal_font.render_calls
    assert "Reward: 40 Gold" not in presenter.normal_font.render_calls
    assert "Experience: 20" not in presenter.normal_font.render_calls
    assert icon_calls == ["Gold", "Goblin Charm"]


def test_simple_list_jumpmods_totems_and_selection_popups(monkeypatch):
    _patch_visuals(monkeypatch)
    presenter = _make_presenter()
    parent = _make_parent()
    player = _make_player()

    simple = popup_menus.SimpleListPopupMenu(
        presenter,
        parent,
        "Simple",
        lambda _player: [
            "--- Header ---",
            DummyItem("Lore Entry", description="Story text"),
            "Plain",
        ],
    )
    simple.build_items(player)
    simple.draw_details(player)

    messages = []
    presenter.show_message = lambda message, **kwargs: messages.append((message, kwargs))
    monkeypatch.setattr(
        popup_menus.map_tiles, "reveal_chalice_map_on_inspect", lambda _player, _value: None
    )
    monkeypatch.setattr(
        popup_menus.map_tiles,
        "get_chalice_progress",
        lambda _player: {"Revealed": True, "Adventurer": False},
    )
    chalice_item = {
        "is_header": False,
        "text": "Chalice Map",
        "value": SimpleNamespace(name="Chalice Map"),
    }
    assert simple.on_select(player, chalice_item) is None
    assert messages[0][1]["image_path"].endswith("key_items/chalice_map.png")

    jump_skill = SimpleNamespace(
        modifications={"Crit": True, "Quake": False},
        unlock_requirements={"Crit": {"type": "lancer_level", "requirement": 5}},
        get_active_count=lambda: 1,
        get_max_active_modifications=lambda _player: 2,
        get_unlocked_modifications=lambda: ["Crit", "Quake"],
        set_modification=lambda name, value, _player: (True, ""),
    )
    player.spellbook["Skills"]["Jump"] = jump_skill
    jump_popup = popup_menus.JumpModsPopupMenu(presenter, parent)
    jump_popup.build_items(player)
    jump_popup.draw_details(player)
    assert jump_popup.on_select(player, jump_popup.items[1]) is None

    totem_skill = SimpleNamespace(
        active_aspect="Bear",
        aspects={"Bear": {"cost": 4, "description": "Tank stance"}},
        get_unlocked_aspects=lambda _player: ["Bear"],
        set_active_aspect=lambda aspect: (True, ""),
    )
    player.spellbook["Skills"]["Totem"] = totem_skill
    player.spellbook["Skills"]["Spirit Animal"] = SimpleNamespace(
        name="Spirit Animal",
        ANIMALS=("Bear", "Wolf"),
    )
    totem_popup = popup_menus.TotemAspectsPopupMenu(presenter, parent)
    totem_popup.build_items(player)
    totem_popup.draw_details(player)
    assert totem_popup.on_select(player, totem_popup.items[1]) is None
    wolf = next(item for item in totem_popup.items if item.get("value") == "Wolf")
    assert totem_popup.on_select(player, wolf) is None
    assert player.spirit_animal == "Wolf"

    composed = []
    player.cls = SimpleNamespace(name="Bard")
    player.equipment["OffHand"] = SimpleNamespace(
        name="Lute",
        subtyp="Musical Instrument",
    )
    monkeypatch.setattr(
        popup_menus.mechanics.bard,
        "compose_sheet_music",
        lambda _player, song: (True, composed.append(song) or "Composed.\n"),
    )
    composition_popup = popup_menus.CompositionPopupMenu(presenter, parent)
    composition_popup.build_items(player)
    battle_hymn = next(item for item in composition_popup.items if item["value"] == "Battle Hymn")
    assert battle_hymn["available"] is True
    assert composition_popup.on_select(player, battle_hymn) is None
    assert composed == ["Battle Hymn"]

    selection = popup_menus.SelectionPopup(
        presenter, parent, title="Pick", header_message="Choose wisely", options=["A", "B"]
    )
    selection.build_items(player)
    selection.draw_details(player)
    assert selection.on_select(player, "A") == ("selection", "A")

    equip_sel = popup_menus.EquipmentSelectionPopup(
        presenter,
        parent,
        title="Equip",
        header_message="Pick gear",
        options=["Unequip", "Cancel"],
        slot="Weapon",
        current_item=DummyItem("Sword"),
        player_char=player,
    )
    equip_sel.build_items(player)
    equip_sel.draw_details(player)


def test_second_popup_menus_pass_covers_remaining_helper_branches(monkeypatch):
    _patch_visuals(monkeypatch)
    presenter = _make_presenter()
    parent = _make_parent()
    player = _make_player()

    # Base popup hook defaults
    base = popup_menus.BasePopupMenu(presenter, parent, title="Base")
    assert base.help_footer().startswith("Arrows:")
    assert base.handle_key_down(player, SimpleNamespace(key=pygame.K_a)) is False
    assert base.on_select(player, "item") == ("selected", "item")

    # Inventory sorting and non-success tuple handling
    inv = popup_menus.InventoryPopupMenu(presenter, parent)
    inv.sort_mode_idx = inv.sort_modes.index("Quantity")
    inv.build_items(player)
    assert inv.items[0][2] >= inv.items[-1][2]
    assert parent._inventory_sort_mode == "Quantity"
    assert player.inventory_sort_mode == "Quantity"
    reopened_inv = popup_menus.InventoryPopupMenu(presenter, parent)
    assert reopened_inv._current_mode() == "Quantity"
    player.inventory_sort_mode = "Combat"
    reopened_inv.build_items(player)
    assert reopened_inv._current_mode() == "Combat"
    inv.sort_mode_idx = inv.sort_modes.index("Combat")
    inv.build_items(player)
    assert inv.items[0][1].name == "Apple"

    confirm_calls = []

    class FalseConfirm:
        def __init__(self, *_args, **_kwargs):
            pass

        def show(self, **_kwargs):
            confirm_calls.append(_kwargs)
            return False

    monkeypatch.setattr(popup_menus.inventory, "ConfirmationPopup", FalseConfirm)
    before = list(player.inventory["Weapons"])
    inv._drop_item(player, player.inventory["Weapons"][0], "Weapons", background_surface="bg")
    assert player.inventory["Weapons"] == before
    assert confirm_calls and confirm_calls[0]["flush_events"] is True

    # Equipment popup empty and select-unequip path
    eq = popup_menus.EquipmentPopupMenu(presenter, parent)
    eq.item_render_manager = SimpleNamespace(
        get_scaled_render=lambda _item, size: pygame.surface.Surface(size, pygame.SRCALPHA)
    )
    empty_player = _make_player()
    empty_player.equipment["Weapon"] = None
    eq.build_items(empty_player)
    eq.draw_details(empty_player)

    actions = iter([("selection", "Unequip")])

    class UnequipPopup:
        def __init__(self, *_args, **_kwargs):
            self.draw_background = lambda surf: None

        def show(self, _player_char, **_kwargs):
            assert _kwargs["flush_events"] is True
            assert _kwargs["require_key_release"] is True
            return next(actions)

    real_equipment_selection_popup = popup_menus.EquipmentSelectionPopup
    monkeypatch.setattr(popup_menus.equipment, "EquipmentSelectionPopup", UnequipPopup)
    monkeypatch.setattr(
        eq, "_unequip_item", lambda *_args, **_kwargs: setattr(eq, "_unequipped", True)
    )
    eq.build_items(player)
    eq.on_select(player, eq.items[0])
    assert getattr(eq, "_unequipped", False) is True

    # Quest details with callable rewards and no-quest fallback
    quest_popup = popup_menus.QuestPopupMenu(presenter, parent)
    player.quest_dict = {}
    quest_popup.build_items(player)
    quest_popup.draw_details(player)

    player.quest_dict = {
        "Side": {
            "Collector": {
                "Type": "Collect",
                "What": lambda: DummyItem("Moon Pearl", typ="Misc"),
                "Total": 2,
                "Completed": False,
                "Turned In": False,
                "Reward": [lambda: DummyItem("Shard", typ="Misc")],
            }
        }
    }
    player.special_inventory["Moon Pearl"] = [DummyItem("Moon Pearl", typ="Misc")]
    quest_popup.build_items(player)
    quest_popup.draw_details(player)

    # Simple list fallback/alternate chalice messages
    simple = popup_menus.SimpleListPopupMenu(
        presenter,
        parent,
        "Simple",
        lambda _player: [
            DummyItem("Passive Aura", typ="Skill", description="", passive=True, cost=4)
        ],
    )
    simple.build_items(player)
    simple.draw_details(player)

    messages = []
    presenter.show_message = lambda message, **kwargs: messages.append(message)
    monkeypatch.setattr(
        popup_menus.map_tiles, "reveal_chalice_map_on_inspect", lambda _player, _value: None
    )
    monkeypatch.setattr(
        popup_menus.map_tiles,
        "get_chalice_progress",
        lambda _player: {"Revealed": False, "Adventurer": True},
    )
    simple.on_select(
        player,
        {"is_header": False, "text": "Chalice Map", "value": SimpleNamespace(name="Chalice Map")},
    )
    monkeypatch.setattr(
        popup_menus.map_tiles,
        "get_chalice_progress",
        lambda _player: {"Revealed": False, "Adventurer": False},
    )
    simple.on_select(
        player,
        {"is_header": False, "text": "Chalice Map", "value": SimpleNamespace(name="Chalice Map")},
    )
    assert len(messages) == 2

    # Jump/Totem not learned or unsuccessful selection
    player.spellbook["Skills"] = {}
    jump_popup = popup_menus.JumpModsPopupMenu(presenter, parent)
    jump_popup.build_items(player)
    jump_popup.draw_details(player)
    assert jump_popup.on_select(player, jump_popup.items[0]) is None

    totem_popup = popup_menus.TotemAspectsPopupMenu(presenter, parent)
    totem_popup.build_items(player)
    totem_popup.draw_details(player)
    assert totem_popup.on_select(player, totem_popup.items[0]) is None

    fail_jump = SimpleNamespace(
        modifications={"Crit": False},
        get_unlocked_modifications=lambda: ["Crit"],
        set_modification=lambda name, value, _player: (False, "blocked"),
    )
    player.spellbook["Skills"]["Jump"] = fail_jump
    jump_popup.build_items(player)
    assert jump_popup.on_select(player, jump_popup.items[1]) is None

    fail_totem = SimpleNamespace(
        active_aspect="",
        aspects={"Wolf": {"description": "Speed up"}},
        get_unlocked_aspects=lambda _player: ["Wolf"],
        set_active_aspect=lambda aspect: (False, "blocked"),
    )
    player.spellbook["Skills"]["Totem"] = fail_totem
    totem_popup.build_items(player)
    assert totem_popup.on_select(player, totem_popup.items[1]) is None

    # Selection popup header wrapping and equipment selection diff branches
    selection = popup_menus.SelectionPopup(
        presenter,
        parent,
        title="Pick",
        header_message="A very long header message that should wrap across multiple lines in the details panel.",
        options=["A"],
    )
    selection.build_items(player)
    selection.draw_details(player)

    player.inventory["Weapons"] = [DummyItem("Steel Sword")]
    monkeypatch.setattr(
        popup_menus.equipment, "EquipmentSelectionPopup", real_equipment_selection_popup
    )
    equip_sel = popup_menus.EquipmentSelectionPopup(
        presenter,
        parent,
        title="Equip",
        header_message="Choose replacement",
        options=["Steel Sword", "Unequip", "Cancel"],
        slot="Weapon",
        current_item=DummyItem("Starter Blade"),
        player_char=player,
    )
    equip_sel.item_render_manager = SimpleNamespace(
        get_scaled_render=lambda _item, _size: RenderedText("equipment-art")
    )
    equip_sel.build_items(player)
    equip_sel.draw_details(player)
    equip_sel.selected_index = 1
    equip_sel.draw_details(player)
    equip_sel.selected_index = 2
    equip_sel.draw_details(player)
