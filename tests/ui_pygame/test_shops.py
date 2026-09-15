#!/usr/bin/env python3
"""Focused coverage for pygame shop-manager helper logic."""

from __future__ import annotations

from types import SimpleNamespace

from src.core import items
from src.core.classes import dragoon
from src.ui_pygame.gui import shops


class DummyFont:
    def render(self, text, _antialias, _color):
        return SimpleNamespace(get_width=lambda: len(text) * 8)

    def get_height(self):
        return 16


class DummyScreen:
    def blit(self, *_args, **_kwargs):
        return None

    def fill(self, *_args, **_kwargs):
        return None


def _make_presenter():
    return SimpleNamespace(
        screen=DummyScreen(),
        width=640,
        height=480,
        title_font=DummyFont(),
        large_font=DummyFont(),
        normal_font=DummyFont(),
        small_font=DummyFont(),
        show_message=lambda message: None,
    )


def _make_player(*, level=12, in_town=True, gold=500):
    inventory = {}
    calls = []

    def modify_inventory(item, num=1, subtract=False):
        calls.append((item.name, num, subtract))
        inventory = player.inventory
        if subtract:
            for _ in range(num):
                inventory[item.name].remove(item)
                if not inventory[item.name]:
                    del inventory[item.name]
            return
        inventory.setdefault(item.name, [])
        inventory[item.name].extend([item] * num)

    def equip_check(item, slot):
        if getattr(item, "typ", None) == "Weapon":
            if slot == "Weapon":
                return True
            return slot == "OffHand" and getattr(item, "off", False)
        if getattr(item, "typ", None) == "Accessory":
            return getattr(item, "subtyp", None) == slot
        return getattr(item, "typ", None) == slot

    equipment = {
        "Weapon": items.NoWeapon(),
        "OffHand": items.NoOffHand(),
        "Armor": items.NoArmor(),
        "Helmet": items.NoHelmet(),
        "Ring": items.NoRing(),
        "Pendant": items.NoPendant(),
    }

    def equip(slot, item):
        if not equip_check(item, slot):
            return False
        equipment[slot] = item
        modify_inventory(item, subtract=True)
        return True

    player = SimpleNamespace(
        gold=gold,
        inventory=inventory,
        special_inventory={},
        equipment=equipment,
        cls=SimpleNamespace(name="Tester", equip_check=equip_check),
        stats=SimpleNamespace(strength=10),
        level=SimpleNamespace(level=level),
        in_town=lambda: in_town,
        player_level=lambda: level,
        modify_inventory=modify_inventory,
        equip=equip,
        can_equip_item=lambda item, slot=None: equip_check(item, slot) if slot else bool(item),
        equip_diff=lambda item, slot, buy=False: "",
    )
    player.inventory_calls = calls
    return player


class FakePopup:
    responses = []
    messages = []
    calls = []

    def __init__(self, _presenter, message, show_buttons=True):
        self.message = message
        self.show_buttons = show_buttons
        FakePopup.messages.append((message, show_buttons))

    def show(self, background_draw_func=None, **kwargs):
        FakePopup.calls.append(kwargs)
        if background_draw_func:
            background_draw_func()
        if FakePopup.responses:
            return FakePopup.responses.pop(0)
        return None


class FakeQuantityPopup:
    responses = []
    created = []

    def __init__(self, _presenter, item_name, price, max_qty, action="buy", default_quantity=1):
        self.item_name = item_name
        self.price = price
        self.max_qty = max_qty
        self.action = action
        self.default_quantity = default_quantity
        FakeQuantityPopup.created.append((item_name, price, max_qty, action, default_quantity))

    def show(self, background_draw_func=None, **_kwargs):
        if background_draw_func:
            background_draw_func()
        return FakeQuantityPopup.responses.pop(0)


class FakeSelectionPopup:
    responses = []
    created = []

    def __init__(
        self, _presenter, _parent_screen, title="Select", header_message=None, options=None
    ):
        self.title = title
        self.header_message = header_message
        self.options = list(options or [])
        FakeSelectionPopup.created.append((title, header_message, tuple(self.options)))

    def show(self, _player_char, **_kwargs):
        if FakeSelectionPopup.responses:
            return ("selection", FakeSelectionPopup.responses.pop(0))
        return None


class FakeShopScreen:
    option_sequences = []
    item_sequences = []
    instances = []

    def __init__(
        self, _presenter, _player_char, shop_message, background_image="town.png", options_list=None
    ):
        self.shop_message = shop_message
        self.background_image = background_image
        self.location_portrait_name = None
        self.options = list(options_list or [])
        self.set_calls = []
        self.update_calls = []
        self.draw_calls = []
        self._navigate_options = list(
            FakeShopScreen.option_sequences.pop(0) if FakeShopScreen.option_sequences else []
        )
        self._navigate_items = list(
            FakeShopScreen.item_sequences.pop(0) if FakeShopScreen.item_sequences else []
        )
        FakeShopScreen.instances.append(self)

    def set_options(self, options):
        self.options = list(options)
        self.set_calls.append(list(options))

    def set_location_portrait(self, npc_name):
        self.location_portrait_name = npc_name

    def navigate_options(self):
        return self._navigate_options.pop(0) if self._navigate_options else None

    def update_item_list(self, itemdict, action):
        self.update_calls.append((itemdict, action))

    def navigate_items(self):
        return self._navigate_items.pop(0) if self._navigate_items else None

    def draw_all(self, do_flip=True):
        self.draw_calls.append(do_flip)

    def display_quest_text(self, text, **kwargs):
        self.last_quest_text = text
        self.last_quest_npc_name = kwargs.get("npc_name")


class FakeQuestManager:
    instances = []

    def __init__(self, _presenter, _player_char, quest_text_renderer, **_kwargs):
        self.quest_text_renderer = quest_text_renderer
        self.calls = []
        FakeQuestManager.instances.append(self)

    def check_and_offer(self, who):
        self.calls.append(who)


class DummyItem:
    def __init__(
        self,
        name="Bronze Sword",
        *,
        typ="Weapon",
        subtyp="Sword",
        description="A simple sword for testing description wrapping.",
        value=40,
        rarity=0.8,
        damage=0,
        weight=0,
        armor=0,
        magic=0,
        magic_defense=0,
        restriction=None,
        ultimate=False,
    ):
        self.name = name
        self.typ = typ
        self.subtyp = subtyp
        self.description = description
        self.value = value
        self.rarity = rarity
        self.damage = damage
        self.weight = weight
        self.armor = armor
        self.magic = magic
        self.magic_defense = magic_defense
        self.restriction = [] if restriction is None else restriction
        self.ultimate = ultimate


def _manager(monkeypatch, *, level=12, in_town=True, gold=500):
    FakePopup.responses = []
    FakePopup.messages = []
    FakePopup.calls = []
    FakeQuantityPopup.responses = []
    FakeQuantityPopup.created = []
    FakeSelectionPopup.responses = []
    FakeSelectionPopup.created = []
    FakeShopScreen.option_sequences = []
    FakeShopScreen.item_sequences = []
    FakeShopScreen.instances = []
    FakeQuestManager.instances = []
    monkeypatch.setattr(
        "src.ui_pygame.gui.town_base.TownScreenBase._load_background",
        lambda self: setattr(self, "background", None),
    )
    return shops.ShopManager(
        _make_presenter(), _make_player(level=level, in_town=in_town, gold=gold)
    )


def test_visit_blacksmith_and_jeweler_closed_show_popup(monkeypatch):
    manager = _manager(monkeypatch, level=3)
    monkeypatch.setattr(shops, "ConfirmationPopup", FakePopup)

    manager.visit_blacksmith()
    manager.visit_jeweler()

    assert any(
        "blacksmith is currently closed" in message for message, _buttons in FakePopup.messages
    )
    assert any("jeweler is currently closed" in message for message, _buttons in FakePopup.messages)
    assert all(call.get("flush_events") for call in FakePopup.calls)


def test_visit_blacksmith_handles_unobtainium_buy_branch_and_leave(monkeypatch):
    manager = _manager(monkeypatch, level=12)
    manager.player_char.special_inventory["Unobtainium"] = [object()]
    shown_messages = []
    manager.presenter.show_message = lambda message: shown_messages.append(message)
    buy_calls = []

    FakeShopScreen.option_sequences = [["Buy", "Weapons", "Leave"]]
    FakeSelectionPopup.responses = ["Not Yet"]
    monkeypatch.setattr(shops, "ShopScreen", FakeShopScreen)
    monkeypatch.setattr(shops, "ConfirmationPopup", FakePopup)
    monkeypatch.setattr(shops, "SelectionPopup", FakeSelectionPopup)
    monkeypatch.setattr("src.ui_pygame.gui.quest_manager.QuestManager", FakeQuestManager)
    monkeypatch.setattr(manager, "buy_weapons", lambda: buy_calls.append("weapons"))

    manager.visit_blacksmith()

    assert any("Unobtainium" in message for message in shown_messages)
    assert any(
        "don't know how to forge a weapon your class can use" in message
        for message in shown_messages
    )
    assert buy_calls == ["weapons"]
    assert FakeShopScreen.instances[0].set_calls[:2] == [
        ["Buy", "Sell", "Quests", "Leave"],
        ["Weapons", "Shields", "Armor", "Helmets", "Back"],
    ]
    assert FakeShopScreen.instances[0].location_portrait_name == "Griswold"
    assert FakeShopScreen.instances[0].shop_message == "Griswold's Blacksmith"
    assert any(
        "Come back whenever you'd like." in message for message, _buttons in FakePopup.messages
    )


def test_visit_blacksmith_quest_renderer_uses_griswold_portrait(monkeypatch):
    manager = _manager(monkeypatch, level=12)

    FakeShopScreen.option_sequences = [["Quests", "Leave"]]
    monkeypatch.setattr(shops, "ShopScreen", FakeShopScreen)
    monkeypatch.setattr(shops, "ConfirmationPopup", FakePopup)
    monkeypatch.setattr("src.ui_pygame.gui.quest_manager.QuestManager", FakeQuestManager)

    manager.visit_blacksmith()
    FakeQuestManager.instances[0].quest_text_renderer("Griswold quest")

    assert FakeQuestManager.instances[0].calls == ["Griswold"]
    assert FakeShopScreen.instances[0].last_quest_npc_name == "Griswold"


def test_blacksmith_buy_submenu_keeps_griswold_portrait(monkeypatch):
    manager = _manager(monkeypatch, level=12)
    manager._active_shopkeeper_portrait = "Griswold"

    FakeShopScreen.option_sequences = [["Back"]]
    monkeypatch.setattr(shops, "ShopScreen", FakeShopScreen)

    manager.buy_weapons()

    assert FakeShopScreen.instances[0].shop_message == "Choose weapon type"
    assert FakeShopScreen.instances[0].location_portrait_name == "Griswold"


def test_blacksmith_two_handed_weapons_exclude_staves(monkeypatch):
    manager = _manager(monkeypatch, level=20)
    item_calls = []
    monkeypatch.setattr(shops, "ShopScreen", FakeShopScreen)
    monkeypatch.setattr(manager, "_has_available_items", lambda _item_list: True)
    monkeypatch.setattr(
        manager,
        "_buy_with_shop_screen",
        lambda itemdict, category_name, **_kwargs: item_calls.append((itemdict, category_name)),
    )

    FakeShopScreen.option_sequences = [["2-Handed"]]
    manager.buy_weapons()

    assert item_calls[-1][1] == "2-Handed Weapons"
    assert "Staff" not in item_calls[-1][0]


def test_visit_magic_shop_handles_buy_sell_and_leave(monkeypatch):
    manager = _manager(monkeypatch, level=12)
    calls = []
    monkeypatch.setattr(shops, "ShopScreen", FakeShopScreen)
    monkeypatch.setattr(shops, "ConfirmationPopup", FakePopup)
    monkeypatch.setattr(manager, "buy_magic_shop_goods", lambda: calls.append("buy"))
    monkeypatch.setattr(manager, "sell_items", lambda: calls.append("sell"))

    FakeShopScreen.option_sequences = [["Buy", "Sell", "Leave"]]
    manager.visit_magic_shop()

    assert calls == ["buy", "sell"]
    assert FakeShopScreen.instances[0].set_calls[0] == ["Buy", "Sell", "Quests", "Leave"]
    assert FakeShopScreen.instances[0].shop_message == shops.ShopManager.MAGIC_SHOP_MESSAGE
    assert FakeShopScreen.instances[0].location_portrait_name == "Seraphine Voss"


def test_magic_shop_is_closed_until_level_three(monkeypatch):
    manager = _manager(monkeypatch, level=2)
    monkeypatch.setattr(shops, "ShopScreen", FakeShopScreen)
    monkeypatch.setattr(shops, "ConfirmationPopup", FakePopup)
    FakePopup.messages = []
    instance_count = len(FakeShopScreen.instances)

    manager.visit_magic_shop()

    assert len(FakeShopScreen.instances) == instance_count
    assert "The Magic Shop is currently closed." in FakePopup.messages[-1][0]
    assert "level" not in FakePopup.messages[-1][0].lower()


def test_visit_blacksmith_crafts_master_monk_ultimate_staff(monkeypatch):
    from src.core.classes.master_monk import MasterMonk

    manager = _manager(monkeypatch, level=30)
    manager.player_char.cls = MasterMonk()
    manager.player_char.special_inventory["Unobtainium"] = [object()]
    shown_messages = []
    manager.presenter.show_message = lambda message: shown_messages.append(message)

    FakeShopScreen.option_sequences = [["Leave"]]
    FakeSelectionPopup.responses = ["Staff"]
    monkeypatch.setattr(shops, "ShopScreen", FakeShopScreen)
    monkeypatch.setattr(shops, "ConfirmationPopup", FakePopup)
    monkeypatch.setattr(shops, "SelectionPopup", FakeSelectionPopup)
    monkeypatch.setattr("src.ui_pygame.gui.quest_manager.QuestManager", FakeQuestManager)

    manager.visit_blacksmith()

    assert "Unobtainium" not in manager.player_char.special_inventory
    assert "Ruyi Jingu Bang" in manager.player_char.inventory
    assert any("mighty Ruyi Jingu Bang" in message for message in shown_messages)
    assert FakeSelectionPopup.created[-1][2] == ("Fist", "Staff", "Not Yet")


def test_visit_alchemist_and_jeweler_cover_quest_and_sell_paths(monkeypatch):
    manager = _manager(monkeypatch, level=15)
    sell_calls = []

    FakeShopScreen.option_sequences = [["Quests", "Sell", "Leave"], ["Quests", "Leave"]]
    monkeypatch.setattr(shops, "ShopScreen", FakeShopScreen)
    monkeypatch.setattr(shops, "ConfirmationPopup", FakePopup)
    monkeypatch.setattr("src.ui_pygame.gui.quest_manager.QuestManager", FakeQuestManager)
    monkeypatch.setattr(manager, "sell_items", lambda: sell_calls.append("sold"))

    manager.visit_alchemist()
    manager.visit_jeweler()

    assert FakeQuestManager.instances[0].calls == ["Alchemist"]
    assert FakeQuestManager.instances[1].calls == ["Jeweler"]
    assert FakeShopScreen.instances[0].location_portrait_name == "Alchemist"
    assert FakeShopScreen.instances[1].location_portrait_name == "Jeweler"
    FakeQuestManager.instances[0].quest_text_renderer("Alchemist quest")
    FakeQuestManager.instances[1].quest_text_renderer("Jeweler quest")
    assert FakeShopScreen.instances[0].last_quest_npc_name == "Alchemist"
    assert FakeShopScreen.instances[1].last_quest_npc_name == "Jeweler"
    assert sell_calls == ["sold"]
    assert any(
        "Good luck on your adventures!" in message for message, _buttons in FakePopup.messages
    )
    assert any("May fortune favor you!" in message for message, _buttons in FakePopup.messages)


def test_alchemist_and_jeweler_buy_open_tabbed_browsers(monkeypatch):
    manager = _manager(monkeypatch, level=15)
    buy_calls = []

    FakeShopScreen.option_sequences = [["Buy", "Leave"], ["Buy", "Leave"]]
    monkeypatch.setattr(shops, "ShopScreen", FakeShopScreen)
    monkeypatch.setattr(shops, "ConfirmationPopup", FakePopup)
    monkeypatch.setattr("src.ui_pygame.gui.quest_manager.QuestManager", FakeQuestManager)
    monkeypatch.setattr(manager, "buy_alchemist_goods", lambda: buy_calls.append("alchemist"))
    monkeypatch.setattr(manager, "buy_jewelry", lambda: buy_calls.append("jewelry"))

    manager.visit_alchemist()
    manager.visit_jeweler()

    assert buy_calls == ["alchemist", "jewelry"]
    assert FakeShopScreen.instances[0].set_calls == [["Buy", "Sell", "Quests", "Leave"]]
    assert FakeShopScreen.instances[1].set_calls == [["Buy", "Sell", "Quests", "Leave"]]


def test_visit_jeweler_crafts_draconite_pendant(monkeypatch):
    manager = _manager(monkeypatch, level=15)
    player = manager.player_char
    player.dragoon_dragon_quest = dragoon.default_state()
    player.dragoon_dragon_quest["draconite_claimed"] = True
    player.special_inventory["Draconite"] = [items.Draconite()]
    messages = []
    manager.presenter.show_message = messages.append

    FakeShopScreen.instances = []
    FakeShopScreen.option_sequences = [["Craft Draconite Pendant", "Leave"]]
    monkeypatch.setattr(shops, "ShopScreen", FakeShopScreen)
    monkeypatch.setattr(shops, "ConfirmationPopup", FakePopup)
    monkeypatch.setattr("src.ui_pygame.gui.quest_manager.QuestManager", FakeQuestManager)

    manager.visit_jeweler()

    assert "Draconite" not in player.special_inventory
    assert "Draconite Pendant" in player.special_inventory
    assert player.dragoon_dragon_quest["pendant_crafted"] is True
    assert any("Draconite Pendant" in message for message in messages)
    assert FakeShopScreen.instances[0].set_calls[0] == [
        "Buy",
        "Sell",
        "Quests",
        "Craft Draconite Pendant",
        "Leave",
    ]


def test_buy_helpers_route_to_expected_equipment_methods(monkeypatch):
    manager = _manager(monkeypatch, level=20)
    item_calls = []

    monkeypatch.setattr(
        manager,
        "buy_equipment",
        lambda item_list, category_name, background_image="town.png": item_calls.append(
            (item_list, category_name, background_image)
        ),
    )
    monkeypatch.setattr(
        manager,
        "_buy_with_shop_screen",
        lambda itemdict, category_name, background_image="town.png", **_kwargs: item_calls.append(
            (itemdict, category_name, background_image)
        ),
    )

    FakeShopScreen.option_sequences = [["1-Handed"]]
    monkeypatch.setattr(shops, "ShopScreen", FakeShopScreen)
    monkeypatch.setattr(manager, "_has_available_items", lambda _item_list: True)

    manager.buy_weapons()
    manager.buy_armor()
    manager.buy_helmets()
    manager.buy_shields()
    manager.buy_rings()
    manager.buy_pendants()
    manager.buy_jewelry()
    manager.buy_scrolls(background_image="dungeon.png")
    manager.buy_misc()
    manager.buy_potions(background_image="dungeon.png")
    manager.buy_alchemist_goods()
    manager.buy_thieves_guild_goods()
    manager.buy_magic_shop_goods()

    assert item_calls[0][1] == "1-Handed Weapons"
    assert set(item_calls[0][0]) >= {"Fist", "Dagger", "Sword"}
    assert item_calls[1][1] == "Armor"
    assert set(item_calls[1][0]) >= {"Cloth", "Light", "Medium", "Heavy"}
    assert item_calls[2][1] == "Helmets"
    assert set(item_calls[2][0]) >= {"Cloth", "Light", "Medium", "Heavy"}
    assert item_calls[3][1] == "Shield"
    assert item_calls[4][1] == "Ring"
    assert item_calls[5][1] == "Pendant"
    assert item_calls[6][1] == "Jewelry"
    assert set(item_calls[6][0]) == {"Rings", "Pendants"}
    assert item_calls[7][1] == "Scroll"
    assert item_calls[7][2] == "dungeon.png"
    assert item_calls[8][1] == "Misc"
    assert item_calls[9][1] == "Potions"
    assert item_calls[9][2] == "dungeon.png"
    assert item_calls[10][1] == "Alchemist Goods"
    assert "Health Potions" in item_calls[10][0]
    assert "Mana Potions" in item_calls[10][0]
    assert "Scrolls" not in item_calls[10][0]
    assert item_calls[11][1] == "Thieves Guild Goods"
    assert set(item_calls[11][0]) == {
        "Tools",
        "Toxins",
        "Ammunition",
        "Crossbows",
        "Crossbow Bolts",
    }
    assert items.Key in item_calls[11][0]["Tools"]
    assert items.BlankScroll in item_calls[11][0]["Tools"]
    assert items.LockpickKit in item_calls[11][0]["Tools"]
    assert items.SmokeBomb in item_calls[11][0]["Tools"]
    assert items.WoodenBolts not in item_calls[11][0]["Tools"]
    assert items.Oculus not in item_calls[11][0]["Tools"]
    assert items.FireScroll not in item_calls[11][0]["Tools"]
    assert item_calls[11][0]["Toxins"] == [items.MildToxin]
    assert item_calls[11][0]["Ammunition"] == [items.ThrowingDaggers]
    assert items.HandCrossbow in item_calls[11][0]["Crossbows"]
    assert items.GoldenClaw in item_calls[11][0]["Crossbows"]
    assert items.WoodenBolts in item_calls[11][0]["Crossbow Bolts"]
    assert item_calls[12][1] == "Magic Shop Goods"
    assert "Spell Scrolls" in item_calls[12][0]
    assert "Staves" in item_calls[12][0]
    assert "Tomes" in item_calls[12][0]
    assert "Rods" in item_calls[12][0]
    assert "Musical Instruments" in item_calls[12][0]
    assert "Magic Items" in item_calls[12][0]
    assert items.BlankScroll not in item_calls[12][0]["Spell Scrolls"]
    assert items.Oculus in item_calls[12][0]["Magic Items"]
    assert items.CenserOfChokingAsh in item_calls[12][0]["Magic Items"]


def test_magic_shop_uses_town_rarity_filter_and_includes_diviner_starter_rods(monkeypatch):
    manager = _manager(monkeypatch, level=1)
    manager.player_char.cls.name = "Diviner"
    captured = []
    monkeypatch.setattr(
        manager,
        "_buy_with_shop_screen",
        lambda itemdict, category_name, background_image="town.png", **kwargs: captured.append(
            (itemdict, category_name, background_image, kwargs)
        ),
    )

    manager.buy_magic_shop_goods()

    itemdict, category_name, _background, kwargs = captured[-1]
    assert category_name == "Magic Shop Goods"
    assert "Rods" in itemdict
    assert shops.items_module.WillowDiviningRod in itemdict["Rods"]
    assert shops.items_module.DowsingRod in itemdict["Rods"]
    assert "ignore_rarity_filter" not in kwargs


def test_buy_helpers_return_early_for_back_and_unavailable_items(monkeypatch):
    manager = _manager(monkeypatch, level=20)
    monkeypatch.setattr(shops, "ShopScreen", FakeShopScreen)
    monkeypatch.setattr(
        manager,
        "buy_equipment",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(AssertionError("should not buy")),
    )

    FakeShopScreen.option_sequences = [[None]]
    manager.buy_weapons()

    FakeShopScreen.option_sequences = [[]]
    monkeypatch.setattr(manager, "_has_available_items", lambda _item_list: False)
    manager.buy_armor()

    assert FakeShopScreen.instances[-1].set_calls == [["1-Handed", "2-Handed", "Back"]]


def test_buy_with_shop_screen_covers_cancel_insufficient_gold_and_purchase(monkeypatch):
    manager = _manager(monkeypatch, gold=120)
    item = DummyItem(name="Potion", typ="Potion", subtyp="Potion", value=10)
    itemdict = {"Potions": [item]}
    messages = []
    manager.presenter.show_message = lambda message: messages.append(message)

    FakeShopScreen.item_sequences = [
        [
            ("Potion", item, 30, 0),
            ("Potion", item, 100, 0),
            ("Potion", item, 10, 0),
            None,
        ]
    ]
    FakeQuantityPopup.responses = [0, 2, 2]
    FakePopup.responses = [None]

    monkeypatch.setattr(shops, "ShopScreen", FakeShopScreen)
    monkeypatch.setattr("src.ui_pygame.gui.confirmation_popup.QuantityPopup", FakeQuantityPopup)
    monkeypatch.setattr(shops, "ConfirmationPopup", FakePopup)

    manager._buy_with_shop_screen(itemdict, "Potions")

    assert messages == ["Not enough gold! Need 200g"]
    assert manager.player_char.gold == 100
    assert manager.player_char.inventory_calls == [("Potion", 2, False)]
    assert FakeShopScreen.instances[0].update_calls == [(itemdict, "Buy"), (itemdict, "Buy")]
    assert any("Purchased 2x Potion!" in message for message, _buttons in FakePopup.messages)
    assert not any(message.startswith("Buy 2x Potion") for message, _buttons in FakePopup.messages)
    assert any(call.get("flush_events") for call in FakePopup.calls)


def test_buy_with_shop_screen_equips_purchased_weapon_to_chosen_slot(monkeypatch):
    manager = _manager(monkeypatch, gold=120)
    item = items.Rapier()
    itemdict = {"Swords": [items.Rapier]}
    manager.player_char.equipment["OffHand"] = items.Buckler()
    manager.player_char.equip_diff = lambda _item, slot, buy=False: (
        "Attack  +5\nDefense  -2" if slot == "OffHand" and buy else ""
    )

    FakeShopScreen.item_sequences = [[("Rapier", item, 10, 0), None]]
    FakeQuantityPopup.responses = [1]
    FakePopup.responses = [True]
    FakeSelectionPopup.responses = ["OffHand"]

    monkeypatch.setattr(shops, "ShopScreen", FakeShopScreen)
    monkeypatch.setattr("src.ui_pygame.gui.confirmation_popup.QuantityPopup", FakeQuantityPopup)
    monkeypatch.setattr(shops, "ConfirmationPopup", FakePopup)
    monkeypatch.setattr(shops, "SelectionPopup", FakeSelectionPopup)

    manager._buy_with_shop_screen(itemdict, "Weapons")

    assert manager.player_char.gold == 110
    assert manager.player_char.equipment["OffHand"].name == "Rapier"
    assert "Rapier" not in manager.player_char.inventory
    assert FakeSelectionPopup.created[-1][2] == ("Main Hand", "OffHand", "Cancel")
    header = FakeSelectionPopup.created[-1][1]
    assert "Purchased 1x Rapier. Equip now?" in header
    assert "Cancel keeps the purchased item in inventory." in header
    assert "Main Hand: replaces empty" in header
    assert "no stat change" in header
    assert "OffHand: replaces Buckler" in header
    assert "Attack  +5" in header
    assert "Defense  -2" in header
    assert "Dual Wield: buy 2 copies to equip both hands." in header
    assert any("Equipped Rapier to OffHand." in message for message, _buttons in FakePopup.messages)


def test_alchemist_and_secret_consumables_include_status_items(monkeypatch):
    manager = _manager(monkeypatch, level=30, gold=120)
    captured = []
    manager._buy_with_shop_screen = lambda itemdict, category_name, **kwargs: captured.append(
        (category_name, itemdict, kwargs)
    )

    manager.buy_potions()
    manager.buy_alchemist_goods()
    manager.buy_thieves_guild_goods()
    manager.buy_magic_shop_goods()
    manager._buy_secret_consumables(SimpleNamespace())

    assert captured[0][1]["Status Items"] == items.items_dict["Potion"]["Status"]
    assert "Health Potions" in captured[0][1]
    assert "Mana Potions" in captured[0][1]
    assert captured[1][1]["Status Items"] == items.items_dict["Potion"]["Status"]
    assert "Health Potions" in captured[1][1]
    assert "Mana Potions" in captured[1][1]
    assert "Scrolls" not in captured[1][1]
    assert set(captured[2][1]) == {"Tools", "Toxins", "Ammunition", "Crossbows", "Crossbow Bolts"}
    assert items.BlankScroll in captured[2][1]["Tools"]
    assert items.LockpickKit in captured[2][1]["Tools"]
    assert items.FireScroll not in captured[2][1]["Tools"]
    assert "Spell Scrolls" in captured[3][1]
    assert items.FireScroll in captured[3][1]["Spell Scrolls"]
    assert items.BlankScroll not in captured[3][1]["Spell Scrolls"]
    assert captured[4][1]["Status Items"] == items.items_dict["Potion"]["Status"]


def test_buy_with_shop_screen_applies_active_price_multiplier(monkeypatch):
    manager = _manager(monkeypatch, gold=120)
    itemdict = {"Scrolls": [items.BlankScroll]}
    manager._active_price_multiplier = 0.75

    monkeypatch.setattr(shops, "ShopScreen", FakeShopScreen)

    FakeShopScreen.item_sequences = [[None]]
    manager._buy_with_shop_screen(itemdict, "Thieves Guild Goods")

    screen = FakeShopScreen.instances[-1]
    assert screen.price_multiplier == 0.75


def test_shop_item_info_separates_main_hand_and_offhand_comparisons(monkeypatch):
    manager = _manager(monkeypatch, gold=120)
    manager.player_char.equipment["Weapon"] = items.Dirk()
    manager.player_char.equipment["OffHand"] = items.Buckler()
    manager.player_char.equip_diff = lambda _item, slot, buy=False: (
        "Attack          10 -> 12" if slot == "Weapon" else "Block Chance     20% -> 0%"
    )

    weapon_info = manager._format_item_info(items.Rapier())
    shield_info = manager._format_item_info(items.Aspis())

    assert "=== Hand Comparison ===" in weapon_info
    assert "Main Hand:" in weapon_info
    assert "OffHand:" in weapon_info
    assert "replaces Dirk" in weapon_info
    assert "replaces Buckler" in weapon_info
    assert "Main Hand:" in shield_info
    assert "not usable in this slot" in shield_info
    assert "OffHand:" in shield_info


def test_buy_with_shop_screen_can_dual_wield_multi_quantity_purchase(monkeypatch):
    manager = _manager(monkeypatch, gold=120)
    item = items.Dirk()
    itemdict = {"Daggers": [items.Dirk]}

    FakeShopScreen.item_sequences = [[("Dirk", item, 10, 0), None]]
    FakeQuantityPopup.responses = [3]
    FakePopup.responses = [True]
    FakeSelectionPopup.responses = ["Dual Wield"]

    monkeypatch.setattr(shops, "ShopScreen", FakeShopScreen)
    monkeypatch.setattr("src.ui_pygame.gui.confirmation_popup.QuantityPopup", FakeQuantityPopup)
    monkeypatch.setattr(shops, "ConfirmationPopup", FakePopup)
    monkeypatch.setattr(shops, "SelectionPopup", FakeSelectionPopup)

    manager._buy_with_shop_screen(itemdict, "Weapons")

    assert manager.player_char.gold == 90
    assert manager.player_char.equipment["Weapon"].name == "Dirk"
    assert manager.player_char.equipment["OffHand"].name == "Dirk"
    assert len(manager.player_char.inventory["Dirk"]) == 1
    assert FakeSelectionPopup.created[-1][2] == ("Main Hand", "OffHand", "Dual Wield", "Cancel")
    header = FakeSelectionPopup.created[-1][1]
    assert "Purchased 3x Dirk. Equip now?" in header
    assert "Cancel keeps every purchased item in inventory." in header
    assert "Dual Wield:" in header
    assert "uses 2 purchased copies" in header
    assert "Main Hand: replaces empty" in header
    assert "OffHand: replaces empty" in header
    assert any(
        "Equipped Dirk to Main Hand and OffHand." in message
        for message, _buttons in FakePopup.messages
    )


def test_buy_with_shop_screen_cancel_equip_keeps_purchase_in_inventory(monkeypatch):
    manager = _manager(monkeypatch, gold=120)
    item = items.Rapier()
    itemdict = {"Swords": [items.Rapier]}

    FakeShopScreen.item_sequences = [[("Rapier", item, 10, 0), None]]
    FakeQuantityPopup.responses = [1]
    FakePopup.responses = [True]
    FakeSelectionPopup.responses = ["Cancel"]

    monkeypatch.setattr(shops, "ShopScreen", FakeShopScreen)
    monkeypatch.setattr("src.ui_pygame.gui.confirmation_popup.QuantityPopup", FakeQuantityPopup)
    monkeypatch.setattr(shops, "ConfirmationPopup", FakePopup)
    monkeypatch.setattr(shops, "SelectionPopup", FakeSelectionPopup)

    manager._buy_with_shop_screen(itemdict, "Weapons")

    assert manager.player_char.gold == 110
    assert manager.player_char.equipment["Weapon"].name == "Bare Hands"
    assert manager.player_char.equipment["OffHand"].name == "No OffHand"
    assert len(manager.player_char.inventory["Rapier"]) == 1
    assert not any("Equipped Rapier" in message for message, _buttons in FakePopup.messages)


def test_buy_with_shop_screen_preflight_failure_keeps_purchase_in_inventory(monkeypatch):
    manager = _manager(monkeypatch, gold=120)
    item = items.Rapier()
    itemdict = {"Swords": [items.Rapier]}
    manager.player_char.equipment["OffHand"] = items.Buckler()
    manager._can_equip_purchase_slot = lambda _item, slot: slot != "OffHand"

    FakeShopScreen.item_sequences = [[("Rapier", item, 10, 0), None]]
    FakeQuantityPopup.responses = [1]
    FakePopup.responses = [True]
    FakeSelectionPopup.responses = ["OffHand"]

    monkeypatch.setattr(shops, "ShopScreen", FakeShopScreen)
    monkeypatch.setattr("src.ui_pygame.gui.confirmation_popup.QuantityPopup", FakeQuantityPopup)
    monkeypatch.setattr(shops, "ConfirmationPopup", FakePopup)
    monkeypatch.setattr(shops, "SelectionPopup", FakeSelectionPopup)

    manager._buy_with_shop_screen(itemdict, "Weapons")

    assert manager.player_char.gold == 110
    assert manager.player_char.equipment["Weapon"].name == "Bare Hands"
    assert manager.player_char.equipment["OffHand"].name == "Buckler"
    assert len(manager.player_char.inventory["Rapier"]) == 1
    assert any(
        "Could not equip Rapier. It remains in inventory." in message
        for message, _buttons in FakePopup.messages
    )


def test_buy_with_shop_screen_mid_action_failure_restores_inventory_and_equipment(monkeypatch):
    manager = _manager(monkeypatch, gold=120)
    item = items.Dirk()
    itemdict = {"Daggers": [items.Dirk]}
    equip_calls = []

    def flaky_equip(slot, purchased_item):
        equip_calls.append(slot)
        manager.player_char.equipment[slot] = purchased_item
        manager.player_char.modify_inventory(purchased_item, subtract=True)
        return slot != "OffHand"

    manager.player_char.equip = flaky_equip

    FakeShopScreen.item_sequences = [[("Dirk", item, 10, 0), None]]
    FakeQuantityPopup.responses = [2]
    FakePopup.responses = [True]
    FakeSelectionPopup.responses = ["Dual Wield"]

    monkeypatch.setattr(shops, "ShopScreen", FakeShopScreen)
    monkeypatch.setattr("src.ui_pygame.gui.confirmation_popup.QuantityPopup", FakeQuantityPopup)
    monkeypatch.setattr(shops, "ConfirmationPopup", FakePopup)
    monkeypatch.setattr(shops, "SelectionPopup", FakeSelectionPopup)

    manager._buy_with_shop_screen(itemdict, "Weapons")

    assert equip_calls == ["Weapon", "OffHand"]
    assert manager.player_char.gold == 100
    assert manager.player_char.equipment["Weapon"].name == "Bare Hands"
    assert manager.player_char.equipment["OffHand"].name == "No OffHand"
    assert len(manager.player_char.inventory["Dirk"]) == 2
    assert any(
        "Could not equip Dirk. It remains in inventory." in message
        for message, _buttons in FakePopup.messages
    )


def test_format_item_info_and_item_availability_helpers(monkeypatch):
    manager = _manager(monkeypatch, level=12, in_town=True)
    current = DummyItem(name="Old Sword", typ="Weapon", subtyp="Sword")
    manager.player_char.equipment = {
        "Weapon": current,
        "Ring": DummyItem(name="None", typ="Accessory", subtyp="Ring"),
    }
    manager.player_char.equip_diff = (
        lambda _item, _slot, buy=False: "Attack  +5\nDefense  -2\nSpeed  0"
    )

    info = manager._format_item_info(
        DummyItem(
            name="New Sword",
            typ="Weapon",
            subtyp="Sword",
            description="A very long description that should wrap neatly in the info panel for testing.",
            value=75,
            damage=12,
            weight=3,
        )
    )
    assert "Type: Weapon" in info
    assert "Subtype: Sword" in info
    assert "Theme Name: Mighty New Sword" in info
    assert "Damage: 12" in info
    assert "Value: 75g" in info
    assert "=== Hand Comparison ===" in info
    assert "Main Hand:" in info
    assert "replaces Old Sword" in info
    assert "Attack  +5" in info
    assert "Defense  -2" in info
    assert "OffHand:" in info
    assert "not usable in this slot" in info

    manager.player_char.equipment = {"Ring": DummyItem(name="None", typ="Accessory", subtyp="Ring")}
    ring_info = manager._format_item_info(
        DummyItem(name="Silver Band", typ="Accessory", subtyp="Ring", value=40)
    )
    assert "(No Ring currently equipped)" in ring_info

    electric_info = manager._format_item_info(
        DummyItem(name="Storm Fist", typ="Weapon", subtyp="Fist", value=40, damage=10)
    )
    assert "Element: Electric" not in electric_info
    elemental_item = DummyItem(name="Storm Fist", typ="Weapon", subtyp="Fist", value=40, damage=10)
    elemental_item.element = "Electric"
    assert "Element: Electric" in manager._format_item_info(elemental_item)

    class AvailableItem:
        def __call__(self):
            return DummyItem(name="Available", rarity=0.9)

    class RestrictedByLevel:
        def __call__(self):
            return DummyItem(name="Late", rarity=0.9, restriction=[20])

    class RestrictedByClass:
        def __call__(self):
            return DummyItem(name="ClassLock", rarity=0.9, restriction=["Ninja"])

    class LowRarity:
        def __call__(self):
            return DummyItem(name="Rare", rarity=0.1)

    assert manager._has_available_items([AvailableItem()]) is True
    assert (
        manager._has_available_items([RestrictedByLevel(), RestrictedByClass(), LowRarity()])
        is False
    )


def test_sell_items_covers_empty_inventory_unsellable_cancel_and_confirm(monkeypatch):
    manager = _manager(monkeypatch, gold=50)
    monkeypatch.setattr(shops, "ConfirmationPopup", FakePopup)
    monkeypatch.setattr(shops, "ShopScreen", FakeShopScreen)
    monkeypatch.setattr("src.ui_pygame.gui.confirmation_popup.QuantityPopup", FakeQuantityPopup)

    manager.sell_items()
    assert any("nothing to sell" in message.lower() for message, _buttons in FakePopup.messages)

    manager.player_char.inventory = {"Legendary": [DummyItem(name="Legendary", ultimate=True)]}
    manager.sell_items(background_image="dungeon.png")
    assert any("no items to sell" in message.lower() for message, _buttons in FakePopup.messages)

    sell_item = DummyItem(name="Herb", typ="Potion", subtyp="Potion", value=10)
    manager.player_char.inventory = {"Herb": [sell_item, sell_item]}
    FakeShopScreen.item_sequences = [[("Herb", sell_item, 5, 2), ("Herb", sell_item, 5, 2), None]]
    FakeQuantityPopup.responses = [0, 2]
    FakePopup.responses = [True, None]

    manager.sell_items(background_image="dungeon.png")

    assert manager.player_char.gold == 60
    assert manager.player_char.inventory_calls[-1] == ("Herb", 2, True)
    assert any("Sold 2x Herb for 10g!" in message for message, _buttons in FakePopup.messages)
    assert any(call.get("flush_events") for call in FakePopup.calls)


def test_secret_shop_branches_delegate_to_expected_helpers(monkeypatch):
    manager = _manager(monkeypatch, level=20)
    calls = []

    monkeypatch.setattr(shops, "ShopScreen", FakeShopScreen)
    monkeypatch.setattr(shops, "ConfirmationPopup", FakePopup)
    monkeypatch.setattr(
        manager,
        "_buy_secret_weapons",
        lambda screen: calls.append(("weapons", screen.shop_message)),
    )
    monkeypatch.setattr(
        manager,
        "_buy_secret_offhand",
        lambda screen: calls.append(("offhand", screen.shop_message)),
    )
    monkeypatch.setattr(
        manager, "_buy_secret_armor", lambda screen: calls.append(("armor", screen.shop_message))
    )
    monkeypatch.setattr(
        manager,
        "_buy_secret_accessories",
        lambda screen: calls.append(("accessories", screen.shop_message)),
    )
    monkeypatch.setattr(
        manager,
        "_buy_secret_consumables",
        lambda screen: calls.append(("consumables", screen.shop_message)),
    )
    monkeypatch.setattr(
        manager,
        "sell_items",
        lambda background_image="town.png": calls.append(("sell", background_image)),
    )

    FakeShopScreen.option_sequences = [
        [
            "Buy",
            "Weapons",
            "Buy",
            "Shields & Tomes",
            "Buy",
            "Armor",
            "Buy",
            "Accessories",
            "Buy",
            "Potions & Scrolls",
            "Sell",
            "Leave",
        ]
    ]

    manager.visit_secret_shop()

    assert calls == [
        ("weapons", "Secret Shop - Rare Goods for Sale"),
        ("offhand", "Secret Shop - Rare Goods for Sale"),
        ("armor", "Secret Shop - Rare Goods for Sale"),
        ("accessories", "Secret Shop - Rare Goods for Sale"),
        ("consumables", "Secret Shop - Rare Goods for Sale"),
        ("sell", "dungeon.png"),
    ]
    assert any("Come back anytime!" in message for message, _buttons in FakePopup.messages)
    assert any(call.get("flush_events") for call in FakePopup.calls)


def test_secret_shop_submenus_and_misc_helpers(monkeypatch):
    manager = _manager(monkeypatch, level=20)
    delegated = []
    monkeypatch.setattr(shops, "ShopScreen", FakeShopScreen)
    monkeypatch.setattr(manager, "_has_available_items", lambda _item_list: True)
    monkeypatch.setattr(
        manager,
        "_buy_with_shop_screen",
        lambda itemdict, category_name, background_image="town.png": delegated.append(
            (category_name, background_image, itemdict)
        ),
    )

    FakeShopScreen.option_sequences = [["2-Handed"]]
    manager._buy_secret_weapons(FakeShopScreen(_make_presenter(), manager.player_char, "msg"))
    manager._buy_secret_offhand(FakeShopScreen(_make_presenter(), manager.player_char, "msg"))
    manager._buy_secret_armor(FakeShopScreen(_make_presenter(), manager.player_char, "msg"))
    manager._buy_secret_helmets(FakeShopScreen(_make_presenter(), manager.player_char, "msg"))
    manager._buy_secret_accessories(FakeShopScreen(_make_presenter(), manager.player_char, "msg"))
    manager._buy_secret_consumables(FakeShopScreen(_make_presenter(), manager.player_char, "msg"))
    manager._buy_secret_stat_potions()
    manager._buy_secret_keys()

    assert (
        "2-Handed Weapons",
        "dungeon.png",
        manager._available_item_groups(shops.items_module.items_dict["Weapon"]["2-Handed"]),
    ) in delegated
    assert (
        "Off-Hand",
        "dungeon.png",
        {
            "Shields": shops.items_module.items_dict["OffHand"]["Shield"],
            "Tomes": shops.items_module.items_dict["OffHand"]["Tome"],
            "Rods": shops.items_module.items_dict["OffHand"]["Rod"],
        },
    ) in delegated
    assert ("Armor", "dungeon.png", shops.items_module.items_dict["Armor"]) in delegated
    assert ("Helmets", "dungeon.png", shops.items_module.items_dict["Helmet"]) in delegated
    assert (
        "Accessories",
        "dungeon.png",
        {
            "Rings": shops.items_module.items_dict["Accessory"]["Ring"],
            "Pendants": shops.items_module.items_dict["Accessory"]["Pendant"],
        },
    ) in delegated
    assert any(
        category == "Consumables" and background == "dungeon.png"
        for category, background, _itemdict in delegated
    )
    assert (
        "Stat Potions",
        "dungeon.png",
        {"Stat Potions": shops.items_module.items_dict["Potion"]["Stat"]},
    ) in delegated
    assert (
        "Keys",
        "dungeon.png",
        {"Keys": shops.items_module.items_dict["Misc"]["Key"]},
    ) in delegated
