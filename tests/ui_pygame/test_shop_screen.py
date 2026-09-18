#!/usr/bin/env python3
"""Focused coverage for reusable pygame shop-screen helpers."""

from __future__ import annotations

from types import SimpleNamespace

import pygame

from src.core import items
from src.ui_pygame.gui import shop_screen


class RenderedText:
    def __init__(self, text):
        self.text = text

    def get_width(self):
        return max(8, len(self.text) * 8)

    def get_height(self):
        return 18

    def get_rect(self, **kwargs):
        rect = SimpleNamespace(x=0, y=0, width=self.get_width(), height=self.get_height())
        if "centerx" in kwargs:
            rect.centerx = kwargs["centerx"]
        if "centery" in kwargs:
            rect.centery = kwargs["centery"]
        if "bottom" in kwargs:
            rect.bottom = kwargs["bottom"]
        return rect


class RecordingFont:
    def __init__(self):
        self.render_calls = []

    def render(self, text, _antialias, _color):
        self.render_calls.append(text)
        return RenderedText(text)

    def get_height(self):
        return 18

    def size(self, text):
        return (max(8, len(text) * 8), 18)


class RecordingScreen:
    def __init__(self):
        self.blit_calls = []
        self.fill_calls = []

    def blit(self, surface, position):
        self.blit_calls.append((surface, position))

    def fill(self, color):
        self.fill_calls.append(color)


class DummyItem:
    def __init__(
        self,
        name,
        *,
        typ="Weapon",
        subtyp="Sword",
        value=100,
        rarity=0.9,
        description="Useful equipment for testing.",
        restriction=None,
    ):
        self.name = name
        self.typ = typ
        self.subtyp = subtyp
        self.value = value
        self.rarity = rarity
        self.description = description
        self.restriction = [] if restriction is None else restriction


def _item_factory(name, **kwargs):
    class Factory:
        def __call__(self):
            return DummyItem(name, **kwargs)

    return Factory()


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
    )


def _make_player(*, in_town=True, level=12, gold=250):
    equip_calls = []

    player = SimpleNamespace(
        gold=gold,
        inventory={"Owned Sword": [DummyItem("Owned Sword")]},
        cls=SimpleNamespace(
            name="Knight",
            equip_check=lambda _item, _slot: True,
        ),
        in_town=lambda: in_town,
        player_level=lambda: level,
        shop_price_scale=lambda: 1.2,
        shop_sell_price_multiplier=lambda: 0.5,
        equip_diff=lambda _item, _slot, buy=False: equip_calls.append((_slot, buy))
        or "Attack  +5\nArmor  -2\nLuck  0",
    )
    player.equip_calls = equip_calls
    return player


def _make_shop(monkeypatch, *, in_town=True, level=12, background_image="town.png"):
    monkeypatch.setattr(
        shop_screen.ShopScreen, "_load_background", lambda self: setattr(self, "background", None)
    )
    return shop_screen.ShopScreen(
        _make_presenter(),
        _make_player(in_town=in_town, level=level),
        "Shop Test",
        background_image=background_image,
    )


def test_load_background_keeps_low_resolution_image_native_and_constructor_sets_rects(monkeypatch):
    presenter = _make_presenter()
    source = SimpleNamespace(get_size=lambda: (200, 100))

    monkeypatch.setattr("os.path.exists", lambda _path: True)
    monkeypatch.setattr("src.ui_pygame.gui.shop_screen.pygame.image.load", lambda _path: source)

    screen = shop_screen.ShopScreen(
        presenter, _make_player(), "Welcome", background_image="dungeon.png"
    )

    assert screen.background is source
    assert screen._background_is_native_fallback is True
    assert screen.options_list == ["Buy", "Sell", "Quests", "Leave"]
    assert screen.top_rect.size == (640, 40)
    assert screen.options_rect.size == (213, 120)
    assert screen.list_rect.width == 426
    assert screen.gold_rect.height == 40

    screen.set_options(["One", "Two"], reset_cursor=False)
    assert screen.options_list == ["One", "Two"]


def test_update_item_list_builds_buy_and_sell_lists_with_filters(monkeypatch):
    screen = _make_shop(monkeypatch, in_town=True, level=12)
    screen.current_item = 3
    screen.scroll_offset = 2
    screen.buy_or_sell = "Buy"

    itemdict = {
        "Weapons": [
            _item_factory("Knight Sword", typ="Weapon", value=100, rarity=0.9),
            _item_factory("Ninja Blade", typ="Weapon", rarity=0.9, restriction=["Ninja"]),
            _item_factory("Old Key", typ="Misc", subtyp="Key", rarity=0.9),
            _item_factory("Ultra Rare", typ="Weapon", rarity=0.1),
        ]
    }
    screen.player_char.inventory["Knight Sword"] = [
        DummyItem("Knight Sword"),
        DummyItem("Knight Sword"),
    ]

    screen.update_item_list(itemdict, "Buy")

    assert [(name, cost, owned) for name, _item, cost, owned in screen.item_list] == [
        ("Knight Sword", 120, 2),
        ("Go Back", 0, 0),
    ]
    assert screen.current_item == 0
    assert screen.scroll_offset == 0

    sell_item = DummyItem("Sell Sword", typ="Weapon", value=50)
    screen.current_item = 1
    screen.scroll_offset = 1
    screen.update_item_list({"Sell Sword": [sell_item, sell_item]}, "Sell")
    assert screen.item_list == [("Sell Sword", sell_item, 12, 2), ("Go Back", None, 0, 0)]

    screen.current_item = 5
    screen.scroll_offset = 3
    screen.update_item_list({"Sell Sword": [sell_item]}, "Sell")
    assert screen.current_item == 0
    assert screen.scroll_offset == 0


def test_level_one_diviner_magic_shop_rods_use_town_rarity_filter(monkeypatch):
    screen = _make_shop(monkeypatch, in_town=True, level=1)
    screen.player_char.cls.name = "Diviner"

    screen.update_item_list({"Rods": items.items_dict["OffHand"]["Rod"]}, "Buy")

    names = [name for name, _item, _cost, _owned in screen.item_list]
    assert "Willow Divining Rod" not in names
    assert "Copper Ley Rod" not in names
    assert "Moonlit Hazel Rod" not in names
    assert "Dowsing Rod" not in names
    assert names == []


def test_update_item_list_keeps_preserved_selection_visible_after_shrink(monkeypatch):
    screen = _make_shop(monkeypatch)
    screen.buy_or_sell = "Sell"
    screen.current_item = 20
    screen.scroll_offset = 20

    itemdict = {f"Item {i}": [DummyItem(f"Item {i}")] for i in range(10)}
    screen.update_item_list(itemdict, "Sell")

    assert screen.current_item == 9
    assert screen.scroll_offset == 0

    screen.item_list = [(f"Item {i}", DummyItem(f"Item {i}"), 10, 0) for i in range(45)]
    screen.current_item = 44
    screen.scroll_offset = 99
    screen._keep_current_item_visible()

    assert screen.scroll_offset == 26


def test_shop_screen_draws_main_menu_shopkeeper_portrait(monkeypatch):
    screen = _make_shop(monkeypatch)
    drawn = []
    monkeypatch.setattr(screen, "draw_npc_portrait", lambda **kwargs: drawn.append(kwargs))
    monkeypatch.setattr(
        "src.ui_pygame.gui.shop_screen.pygame.draw.rect", lambda *_args, **_kwargs: None
    )

    screen.set_location_portrait("Griswold")
    screen.draw_shop_list()

    assert drawn[-1]["npc_name"] == "Griswold"
    assert drawn[-1]["rect"].left == screen.list_rect.left
    assert drawn[-1]["rect"].top == screen.list_rect.top
    assert drawn[-1]["rect"].width == screen.width // 3

    screen.update_item_list(
        {"Weapons": [_item_factory("Knight Sword", typ="Weapon", value=100, rarity=0.9)]}, "Buy"
    )
    drawn.clear()
    screen.draw_shop_list()
    assert drawn == []


def test_build_buy_list_secret_shop_filters_to_mid_rarity_band(monkeypatch):
    screen = _make_shop(monkeypatch, in_town=False, level=20, background_image="dungeon.png")
    itemdict = {
        "Misc": [
            _item_factory("Too Common", typ="Misc", rarity=0.8),
            _item_factory("Too Rare", typ="Misc", rarity=0.1),
            _item_factory("Secret Stock", typ="Misc", rarity=0.3, value=70),
        ]
    }

    screen.update_item_list(itemdict, "Buy")

    assert [(name, cost) for name, _item, cost, _owned in screen.item_list] == [
        ("Secret Stock", 84),
        ("Go Back", 0),
    ]


def test_buy_list_uses_subtype_tabs_and_preserves_active_tab(monkeypatch):
    screen = _make_shop(monkeypatch, in_town=True, level=20)
    itemdict = {
        "Swords": [_item_factory("Training Sword", typ="Weapon", subtyp="Sword", rarity=0.9)],
        "Axes": [_item_factory("Hand Axe", typ="Weapon", subtyp="Axe", rarity=0.9)],
        "Unavailable": [_item_factory("Hidden Blade", typ="Weapon", subtyp="Dagger", rarity=0.1)],
    }

    screen.update_item_list(itemdict, "Buy")

    assert screen.tab_labels == ["Swords", "Axes"]
    assert screen.active_tab_index == 0
    assert screen.item_list[0][0] == "Training Sword"

    screen.switch_item_tab(1)

    assert screen.active_tab_index == 1
    assert screen.item_list[0][0] == "Hand Axe"

    screen.current_item = 1
    screen.update_item_list(itemdict, "Buy")

    assert screen.tab_labels == ["Swords", "Axes"]
    assert screen.active_tab_index == 1
    assert screen.item_list[0][0] == "Hand Axe"


def test_draw_helpers_render_empty_lists_descriptions_gold_and_all(monkeypatch):
    screen = _make_shop(monkeypatch)
    monkeypatch.setattr(
        "src.ui_pygame.gui.shop_screen.pygame.draw.rect", lambda *_args, **_kwargs: None
    )
    flip_calls = []
    monkeypatch.setattr(
        "src.ui_pygame.gui.shop_screen.pygame.display.flip", lambda: flip_calls.append(True)
    )
    render_calls = []
    screen.item_render_manager = SimpleNamespace(
        get_scaled_render=lambda item, size: render_calls.append((getattr(item, "name", ""), size))
        or pygame.surface.Surface(size, pygame.SRCALPHA)
    )

    screen.buy_or_sell = "Buy"
    screen.draw_shop_list()
    assert "No items available" in screen.normal_font.render_calls

    sword = DummyItem(
        "Steel Sword",
        typ="Weapon",
        subtyp="Sword",
        description="A sword with a wrapped description.",
    )
    screen.item_list = [("Steel Sword", sword, 100, 1)]
    screen.buy_or_sell = "Buy"
    screen.draw_options()
    screen.draw_item_desc()
    screen.draw_gold()

    screen.item_list = [(f"Item {i}", DummyItem(f"Item {i}"), 10, 0) for i in range(25)]
    screen.scroll_offset = 2
    screen.draw_shop_list()

    called = []
    screen.draw_background = lambda: called.append("background")
    screen.draw_top = lambda: called.append("top")
    screen.draw_options = lambda: called.append("options")
    screen.draw_item_desc = lambda: called.append("desc")
    screen.draw_shop_list = lambda: called.append("list")
    screen.draw_mod = lambda: called.append("mod")
    screen.draw_gold = lambda: called.append("gold")
    screen.draw_all(do_flip=False)
    screen.draw_all(do_flip=True)

    assert "wrapped description" in "".join(screen.normal_font.render_calls)
    assert render_calls == [("Steel Sword", (185, 92))]
    assert "250G" in screen.normal_font.render_calls
    assert "3-21 / 25" in screen.small_font.render_calls
    assert called == [
        "background",
        "top",
        "options",
        "list",
        "desc",
        "mod",
        "gold",
        "background",
        "top",
        "options",
        "list",
        "desc",
        "mod",
        "gold",
    ]
    assert flip_calls == [True]


def test_draw_all_accepts_popup_parent_screen_call_signature(monkeypatch):
    screen = _make_shop(monkeypatch)
    flip_calls = []
    monkeypatch.setattr(
        "src.ui_pygame.gui.shop_screen.pygame.display.flip", lambda: flip_calls.append(True)
    )
    called = []
    screen.draw_background = lambda: called.append("background")
    screen.draw_top = lambda: called.append("top")
    screen.draw_options = lambda: called.append("options")
    screen.draw_item_desc = lambda: called.append("desc")
    screen.draw_shop_list = lambda: called.append("list")
    screen.draw_mod = lambda: called.append("mod")
    screen.draw_gold = lambda: called.append("gold")

    replacement_player = _make_player(gold=999)
    screen.draw_all(replacement_player, do_flip=False)
    screen.draw_all(False)

    assert screen.player_char is replacement_player
    assert called == [
        "background",
        "top",
        "options",
        "list",
        "background",
        "top",
        "options",
        "list",
    ]
    assert flip_calls == []

    called.clear()
    screen.buy_or_sell = "Buy"
    screen.draw_all(False)
    assert called == ["background", "top", "options", "list", "desc", "mod", "gold"]
    assert flip_calls == []


def test_shop_screen_quest_text_uses_blocking_town_dialogue(monkeypatch):
    screen = _make_shop(monkeypatch)
    calls = []
    monkeypatch.setattr(
        shop_screen.TownScreenBase,
        "display_quest_text",
        lambda _self, text, **kwargs: calls.append((text, kwargs)),
    )

    screen.display_quest_text("A quiet answer in the ledger.", title="Mara Vale")

    assert calls == [
        (
            "====== Mara Vale ======\nA quiet answer in the ledger.",
            {"npc_name": "Mara Vale"},
        )
    ]


def test_shop_screen_quest_text_accepts_npc_name_keyword(monkeypatch):
    screen = _make_shop(monkeypatch)
    calls = []
    monkeypatch.setattr(
        shop_screen.TownScreenBase,
        "display_quest_text",
        lambda _self, text, **kwargs: calls.append((text, kwargs)),
    )

    screen.display_quest_text("A new commission awaits.", npc_name="Griswold")

    assert calls == [("A new commission awaits.", {"npc_name": "Griswold"})]


def test_draw_item_desc_includes_element_and_resistance_metadata(monkeypatch):
    screen = _make_shop(monkeypatch)
    monkeypatch.setattr(
        "src.ui_pygame.gui.shop_screen.pygame.draw.rect", lambda *_args, **_kwargs: None
    )

    indras_fist = items.IndrasFist()
    screen.item_list = [("Indra's Fist", indras_fist, 100, 0)]
    screen.current_item = 0
    screen.draw_item_desc()
    assert "Element: Electric" in screen.normal_font.render_calls

    screen.normal_font.render_calls.clear()
    svalinn = items.Svalinn()
    screen.item_list = [("Svalinn", svalinn, 100, 0)]
    screen.draw_item_desc()
    assert "Resistance: Fire +25%" in screen.normal_font.render_calls


def test_draw_mod_uses_cache_and_handles_cant_equip_and_errors(monkeypatch):
    screen = _make_shop(monkeypatch)
    monkeypatch.setattr(
        "src.ui_pygame.gui.shop_screen.pygame.draw.rect", lambda *_args, **_kwargs: None
    )

    item = DummyItem("Silver Ring", typ="Accessory", subtyp="Ring")
    screen.item_list = [("Silver Ring", item, 75, 0)]
    screen.current_item = 0

    screen.draw_mod()
    screen.draw_mod()
    assert screen.player_char.equip_calls == [("Ring", True)]
    assert "Equipment Modifications" in screen.normal_font.render_calls
    assert "Attack" in screen.normal_font.render_calls

    screen.player_char.cls.equip_check = lambda _item, _slot: False
    screen.cached_item_index = -1
    screen.draw_mod()
    assert "Can't Equip" in screen.normal_font.render_calls

    screen.player_char.cls = SimpleNamespace(
        equip_check=lambda _item, _slot: (_ for _ in ()).throw(AttributeError("boom"))
    )
    screen.draw_mod()


def test_navigation_helpers_support_selection_wrapping_and_scroll(monkeypatch):
    screen = _make_shop(monkeypatch)
    monkeypatch.setattr(screen, "draw_all", lambda do_flip=True: None)

    monkeypatch.setattr("src.ui_pygame.gui.shop_screen.pygame.event.clear", lambda: None)
    monkeypatch.setattr("src.ui_pygame.gui.input_guards.pygame.key.get_pressed", lambda: [])
    option_events = iter(
        [
            [SimpleNamespace(type=pygame.KEYDOWN, key=pygame.K_DOWN)],
            [SimpleNamespace(type=pygame.KEYDOWN, key=pygame.K_RETURN)],
        ]
    )
    monkeypatch.setattr(
        "src.ui_pygame.gui.shop_screen.pygame.event.get", lambda: next(option_events, [])
    )
    assert screen.navigate_options(flush_events=False, require_key_release=False) == "Sell"

    screen.item_list = [(f"Item {i}", DummyItem(f"Item {i}"), 10, 0) for i in range(25)]
    screen.current_item = 18
    screen.scroll_offset = 0
    item_events = iter(
        [
            [SimpleNamespace(type=pygame.KEYDOWN, key=pygame.K_DOWN)],
            [SimpleNamespace(type=pygame.KEYDOWN, key=pygame.K_DOWN)],
            [SimpleNamespace(type=pygame.KEYDOWN, key=pygame.K_RETURN)],
        ]
    )
    monkeypatch.setattr(
        "src.ui_pygame.gui.shop_screen.pygame.event.get", lambda: next(item_events, [])
    )
    choice = screen.navigate_items()

    assert choice[0] == "Item 20"
    assert screen.current_item == 20
    assert screen.scroll_offset == 2

    screen.item_list = []
    assert screen.navigate_items() is None


def test_shop_option_navigation_supports_mouse_hover_and_click(monkeypatch):
    screen = _make_shop(monkeypatch)
    monkeypatch.setattr(screen, "draw_all", lambda do_flip=True: None)
    monkeypatch.setattr("src.ui_pygame.gui.input_guards.pygame.key.get_pressed", lambda: [])

    click_pos = screen.option_rects()[1].center
    option_events = iter(
        [
            [SimpleNamespace(type=pygame.MOUSEMOTION, pos=click_pos)],
            [SimpleNamespace(type=pygame.MOUSEBUTTONDOWN, button=1, pos=click_pos)],
        ]
    )
    monkeypatch.setattr(
        "src.ui_pygame.gui.shop_screen.pygame.event.get", lambda: next(option_events, [])
    )

    assert screen.navigate_options(flush_events=True, require_key_release=True) == "Sell"
    assert screen.current_option == 1


def test_shop_item_navigation_supports_mouse_rows_wheel_and_tabs(monkeypatch):
    screen = _make_shop(monkeypatch)
    monkeypatch.setattr(screen, "draw_all", lambda do_flip=True: None)
    monkeypatch.setattr("src.ui_pygame.gui.input_guards.pygame.key.get_pressed", lambda: [])
    screen.item_list = [(f"Item {i}", DummyItem(f"Item {i}"), 10, 0) for i in range(25)]

    wheel_events = iter(
        [
            [SimpleNamespace(type=pygame.MOUSEWHEEL, y=-1)],
            [SimpleNamespace(type=pygame.KEYDOWN, key=pygame.K_RETURN)],
        ]
    )
    monkeypatch.setattr(
        "src.ui_pygame.gui.shop_screen.pygame.event.get", lambda: next(wheel_events, [])
    )

    choice = screen.navigate_items(flush_events=True, require_key_release=True)

    assert choice[0] == "Item 1"
    assert screen.current_item == 1

    click_pos = screen.item_row_rects()[3][1].center
    row_events = iter(
        [
            [SimpleNamespace(type=pygame.MOUSEMOTION, pos=click_pos)],
            [SimpleNamespace(type=pygame.MOUSEBUTTONDOWN, button=1, pos=click_pos)],
        ]
    )
    monkeypatch.setattr(
        "src.ui_pygame.gui.shop_screen.pygame.event.get", lambda: next(row_events, [])
    )

    choice = screen.navigate_items(flush_events=True, require_key_release=True)

    assert choice[0] == "Item 3"
    assert screen.current_item == 3

    screen.update_item_list(
        {
            "Swords": [_item_factory("Training Sword", typ="Weapon", subtyp="Sword")],
            "Axes": [_item_factory("Hand Axe", typ="Weapon", subtyp="Axe")],
        },
        "Buy",
    )
    tab_pos = screen.item_tab_rects()[1].center
    item_pos = screen.item_row_rects()[0][1].center
    tab_events = iter(
        [
            [SimpleNamespace(type=pygame.MOUSEBUTTONDOWN, button=1, pos=tab_pos)],
            [SimpleNamespace(type=pygame.MOUSEBUTTONDOWN, button=1, pos=item_pos)],
        ]
    )
    monkeypatch.setattr(
        "src.ui_pygame.gui.shop_screen.pygame.event.get", lambda: next(tab_events, [])
    )

    choice = screen.navigate_items(flush_events=True, require_key_release=True)

    assert choice[0] == "Hand Axe"
    assert screen.active_tab_index == 1


def test_item_navigation_supports_page_home_and_end_keys(monkeypatch):
    screen = _make_shop(monkeypatch)
    monkeypatch.setattr(screen, "draw_all", lambda do_flip=True: None)
    monkeypatch.setattr("src.ui_pygame.gui.input_guards.pygame.key.get_pressed", lambda: [])
    screen.item_list = [(f"Item {i}", DummyItem(f"Item {i}"), 10, 0) for i in range(45)]

    item_events = iter(
        [
            [SimpleNamespace(type=pygame.KEYDOWN, key=pygame.K_PAGEDOWN)],
            [SimpleNamespace(type=pygame.KEYDOWN, key=pygame.K_PAGEDOWN)],
            [SimpleNamespace(type=pygame.KEYDOWN, key=pygame.K_PAGEUP)],
            [SimpleNamespace(type=pygame.KEYDOWN, key=pygame.K_END)],
            [SimpleNamespace(type=pygame.KEYDOWN, key=pygame.K_HOME)],
            [SimpleNamespace(type=pygame.KEYDOWN, key=pygame.K_RETURN)],
        ]
    )
    monkeypatch.setattr(
        "src.ui_pygame.gui.shop_screen.pygame.event.get", lambda: next(item_events, [])
    )

    choice = screen.navigate_items(flush_events=True, require_key_release=True)

    assert choice[0] == "Item 0"
    assert screen.current_item == 0
    assert screen.scroll_offset == 0


def test_item_navigation_switches_buy_tabs_with_left_right(monkeypatch):
    screen = _make_shop(monkeypatch)
    monkeypatch.setattr(screen, "draw_all", lambda do_flip=True: None)
    monkeypatch.setattr("src.ui_pygame.gui.input_guards.pygame.key.get_pressed", lambda: [])
    screen.update_item_list(
        {
            "Swords": [_item_factory("Training Sword", typ="Weapon", subtyp="Sword")],
            "Axes": [_item_factory("Hand Axe", typ="Weapon", subtyp="Axe")],
        },
        "Buy",
    )

    item_events = iter(
        [
            [SimpleNamespace(type=pygame.KEYDOWN, key=pygame.K_RIGHT)],
            [SimpleNamespace(type=pygame.KEYDOWN, key=pygame.K_RETURN)],
        ]
    )
    monkeypatch.setattr(
        "src.ui_pygame.gui.shop_screen.pygame.event.get", lambda: next(item_events, [])
    )

    choice = screen.navigate_items(flush_events=True, require_key_release=True)

    assert choice[0] == "Hand Axe"
    assert screen.active_tab_index == 1


def test_navigation_helpers_can_opt_out_of_stale_input_guard(monkeypatch):
    screen = _make_shop(monkeypatch)
    monkeypatch.setattr(screen, "draw_all", lambda do_flip=True: None)

    clear_calls = []
    monkeypatch.setattr(
        "src.ui_pygame.gui.shop_screen.pygame.event.clear", lambda: clear_calls.append(True)
    )
    option_events = iter([[SimpleNamespace(type=pygame.KEYDOWN, key=pygame.K_RETURN)]])
    monkeypatch.setattr(
        "src.ui_pygame.gui.shop_screen.pygame.event.get", lambda: next(option_events, [])
    )

    assert screen.navigate_options(flush_events=False, require_key_release=False) == "Buy"
    assert clear_calls == []


def test_navigation_guard_accepts_fresh_key_without_keyup(monkeypatch):
    screen = _make_shop(monkeypatch)
    monkeypatch.setattr(screen, "draw_all", lambda do_flip=True: None)
    monkeypatch.setattr("src.ui_pygame.gui.input_guards.pygame.key.get_pressed", lambda: [])
    monkeypatch.setattr(
        "src.ui_pygame.gui.shop_screen.pygame.event.get",
        lambda: [SimpleNamespace(type=pygame.KEYDOWN, key=pygame.K_RETURN)],
    )

    assert screen.navigate_options(flush_events=True, require_key_release=True) == "Buy"
