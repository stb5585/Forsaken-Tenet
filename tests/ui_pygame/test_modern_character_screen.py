#!/usr/bin/env python3
"""Focused coverage for the standard pygame character menu."""

from __future__ import annotations

import typing
from types import SimpleNamespace

import pygame

from src.core import abilities, companions, items
from src.core.classes import (
    ability_mechanics,
    archdruid,
    astromancer,
    bard,
    class_rings,
    demonologist,
    grandmaster,
    promotion_kits,
    wizard,
)
from src.core.progression import ProgressionState
from src.ui_pygame import game as pygame_game
from src.ui_pygame.gui.dungeon_manager import DungeonManager
from src.ui_pygame.gui.modern_character_screen import (
    RESISTANCE_ORDER,
    ClassCompanionDetailsPopup,
    ModernCharacterScreen,
)


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

    def size(self, text):
        return (max(8, len(text) * 8), self._height)


class RecordingScreen:
    def __init__(self, size=(1000, 720)):
        self._size = size
        self.blit_calls = []
        self.fill_calls = []

    def blit(self, surface, position):
        self.blit_calls.append((surface, position))

    def fill(self, color):
        self.fill_calls.append(color)

    def get_width(self):
        return self._size[0]

    def get_height(self):
        return self._size[1]

    def copy(self):
        return "screen-copy"


def _make_presenter():
    return SimpleNamespace(
        screen=RecordingScreen(),
        width=1000,
        height=720,
        title_font=RecordingFont(34),
        large_font=RecordingFont(28),
        normal_font=RecordingFont(22),
        small_font=RecordingFont(18),
        clock=SimpleNamespace(tick=lambda _fps: None),
        debug_mode=True,
    )


def _effect(active=True, duration=2, extra=0):
    return SimpleNamespace(active=active, duration=duration, extra=extra)


class FakeJumpSkill:
    def __init__(self):
        self.name = "Jump"
        self.modifications = {"Crit": True, "Recover": False, "Skyfall": True}

    def get_active_count(self):
        return 2

    def get_max_active_modifications(self, _player):
        return 3

    def get_unlocked_modifications(self):
        return ["Crit", "Recover", "Skyfall"]

    def set_modification(self, mod_name, active, _player):
        self.modifications[mod_name] = active
        return True, ""


class FakeTotemSkill:
    name = "Totem"
    active_aspect = "Fire"
    aspects = {
        "Fire": {"cost": 6, "description": "Calls a flame totem."},
        "Water": {"cost": 6, "description": "Calls a water totem."},
        "Soul": {"cost": 10, "description": "Calls a soul totem."},
    }

    def get_unlocked_aspects(self, _player):
        return ["Fire", "Water", "Soul"]

    def set_active_aspect(self, aspect):
        self.active_aspect = aspect
        return True, ""


def _make_player():
    player = SimpleNamespace(
        name="Longnamed Hero of the Northern Gate",
        race=SimpleNamespace(name="Human"),
        sex="Female",
        cls=SimpleNamespace(name="Warrior"),
        level=SimpleNamespace(level=7, pro_level=1, exp=1250, exp_to_gain=50),
        progression=ProgressionState(level=7, total_xp=1250, unspent_points=6),
        gold=321,
        location_z=0,
        health=SimpleNamespace(current=45, max=60),
        mana=SimpleNamespace(current=12, max=20),
        stats=SimpleNamespace(strength=14, intel=11, wisdom=10, con=13, charisma=9, dex=8),
        combat=SimpleNamespace(attack=10, defense=8, magic=3, magic_def=4),
        resistance={
            "Fire": -0.15,
            "Ice": -0.15,
            "Water": -0.15,
            "Poison": 0.2,
            "Physical": 0.1,
        },
        equipment={
            "Weapon": SimpleNamespace(
                name="Sword",
                typ="Weapon",
                subtyp="Sword",
                damage=12,
                crit_chance=0.15,
                weight=4,
                description="Reliable steel.",
            ),
            "Armor": SimpleNamespace(name="Mail", typ="Armor", subtyp="Medium", armor=8, weight=12),
            "Helmet": SimpleNamespace(
                name="Iron Helm", typ="Helmet", subtyp="Heavy", armor=4, weight=6
            ),
            "OffHand": None,
            "Ring": SimpleNamespace(
                name="Ruby Ring", typ="Accessory", subtyp="Ring", mod="Block", weight=0.1
            ),
            "Pendant": SimpleNamespace(
                name="Pendant of Sight", typ="Accessory", subtyp="Pendant", mod="Vision", weight=0.2
            ),
        },
        buffs=[SimpleNamespace(name="Might"), SimpleNamespace(name="Might")],
        stat_effects={"Attack": _effect(True, 3, 4), "Speed": _effect(False)},
        magic_effects={"Regen": _effect(True, 2, 5)},
        class_effects={"Power Up": _effect(False)},
        status_effects={"Poison": _effect(True, 4, 2)},
        physical_effects={"Bleed": _effect(False)},
        spellbook={"Spells": {}, "Skills": {}},
        special_inventory={},
        kill_dict={"Regular": {"Goblin": 2}},
        sight=True,
    )
    player.current_weight = lambda: 19
    player.max_weight = lambda: 140
    player.level_exp = lambda: 300
    player.critical_chance = lambda _slot: 0.125

    def check_mod(mod, typ=None):
        if mod == "resist":
            value = player.resistance.get(typ, 0)
            pendant = player.equipment.get("Pendant")
            pendant_mod = str(getattr(pendant, "mod", "") or "")
            if pendant_mod.split("-")[-1] in {typ, "Elemental"} and typ in {
                "Fire",
                "Ice",
                "Electric",
                "Water",
                "Earth",
                "Wind",
            }:
                value += 1 if "Immune" in pendant_mod else 0.5
            return value
        return {
            "weapon": 18,
            "offhand": 8,
            "armor": 22,
            "shield": 15,
            "magic def": 7,
            "magic": 9,
            "speed": 8,
        }.get(mod, 0)

    player.check_mod = check_mod
    player.in_town = lambda: True
    return player


def _stub_character_screen_drawing(monkeypatch, screen):
    monkeypatch.setattr(
        screen,
        "draw_semi_transparent_panel",
        lambda rect, alpha=180: DummySurface((rect.width, rect.height)),
    )
    monkeypatch.setattr(
        "src.ui_pygame.gui.modern_character_screen.pygame.draw.rect", lambda *_args, **_kwargs: None
    )
    monkeypatch.setattr(
        "src.ui_pygame.gui.modern_character_screen.pygame.draw.line", lambda *_args, **_kwargs: None
    )


def _rendered_text(presenter):
    return set(
        presenter.large_font.render_calls
        + presenter.normal_font.render_calls
        + presenter.small_font.render_calls
    )


def test_companion_popup_annotations_resolve_at_runtime():
    hints = typing.get_type_hints(ClassCompanionDetailsPopup.__init__)

    assert hints["parent_screen"].__name__ == "ModernCharacterScreenProtocol"


def test_modern_character_tabs_are_generic_and_switchable():
    screen = ModernCharacterScreen(_make_presenter())
    player = _make_player()

    assert [tab.label for tab in screen.tabs] == [
        "Character",
        "Class",
        "Equipment",
        "Progression",
    ]
    assert [tab.label for tab in screen.visible_tabs(player)] == [
        "Character",
        "Equipment",
        "Progression",
    ]
    assert screen.active_tab.key == "character"
    assert abs((screen.character_panel_rect.width * 2) - (screen.combat_panel_rect.width * 3)) <= 3

    screen.move_tab(1, player)
    assert screen.active_tab.key == "equipment"

    screen.move_tab(1, player)
    assert screen.active_tab.key == "progression"
    assert screen.equipment_selector_active is False

    screen.move_tab(1, player)
    assert screen.active_tab.key == "character"

    player.cls = SimpleNamespace(name="Weapon Master")
    assert [tab.label for tab in screen.visible_tabs(player)] == [
        "Character",
        "Equipment",
        "Weapon Discipline",
        "Progression",
    ]
    screen.move_tab(1, player)
    assert screen.active_tab.key == "equipment"


def test_progression_tab_draws_tree_inside_character_menu(monkeypatch):
    presenter = _make_presenter()
    screen = ModernCharacterScreen(presenter)
    player = _make_player()
    screen.select_tab("progression")
    monkeypatch.setattr(
        screen.progression_view,
        "draw_semi_transparent_panel",
        lambda *_args, **_kwargs: None,
    )
    monkeypatch.setattr(
        "src.ui_pygame.gui.progression_screen.pygame.draw.rect",
        lambda *_args, **_kwargs: None,
    )
    monkeypatch.setattr(
        "src.ui_pygame.gui.progression_screen.pygame.draw.line",
        lambda *_args, **_kwargs: None,
    )
    monkeypatch.setattr(
        "src.ui_pygame.gui.progression_screen.pygame.draw.lines",
        lambda *_args, **_kwargs: None,
    )

    screen.draw_all(player, do_flip=False)

    rendered = set(presenter.normal_font.render_calls + presenter.small_font.render_calls)
    assert not any(text.startswith("Progression  |  Level") for text in rendered)
    assert "Available Progression Points: 6" in rendered
    assert "Warrior Ability Tree" not in rendered
    assert "P: Navigate tree" in rendered
    assert not any("Tree Navigation" in text for text in presenter.large_font.render_calls)


def test_modern_character_summary_helpers_cover_xp_equipment_resistances_and_effects():
    screen = ModernCharacterScreen(_make_presenter())
    player = _make_player()

    assert screen.xp_progress(player) == 250 / 300
    assert screen.xp_label(player) == "250/300 XP (50 next)"

    player.level.exp_to_gain = "MAX"
    assert screen.xp_progress(player) == 1.0
    assert screen.xp_label(player) == "1250 XP / MAX level"
    player.level.exp_to_gain = 50

    summary = dict(screen.build_character_summary(player))
    assert summary["Race"] == "Human"
    assert summary["Class"] == "Warrior"
    assert "Active Buffs" not in summary
    player.magic_effects["Resist Fire"] = _effect()
    player.magic_effects["Resist Holy"] = _effect()
    summary = dict(screen.build_character_summary(player))
    assert summary["Active Buffs"] == "Resist Fire, Resist Holy"
    assert dict(screen.build_portrait_details(player)) == {"Gold": "321G", "Location": "Town"}
    player.location_z = 3
    assert screen.location_label(player) == "Dungeon Level 3"
    player.location_z = 0
    assert screen.portrait_filename(player) == "human_base_portraits.png"

    player.race = SimpleNamespace(name="Half Elf")
    player.sex = "Male"
    assert screen.portrait_filename(player) == "half_elf_base_portraits.png"
    player.race = SimpleNamespace(name="Human")
    player.sex = "Female"

    combat = dict(screen.build_combat_stats(player))
    assert combat["HP"] == "45/60"
    assert combat["Attack"] == "18"
    assert combat["Magic Defense"] == "7"

    assert combat["Critical"] == "12.5%"
    assert combat["Weight"] == "19/140"

    player.equipment["OffHand"] = SimpleNamespace(name="Dagger", typ="Weapon", subtyp="Dagger")
    combat = dict(screen.build_combat_stats(player))
    assert combat["Attack"] == "18/8"
    player.equipment["OffHand"] = None

    slots = screen.build_equipment_slots(player)
    assert [slot.slot for slot in slots] == [
        "Weapon",
        "Armor",
        "Helmet",
        "OffHand",
        "Ring",
        "Pendant",
    ]
    helmet = next(slot for slot in slots if slot.slot == "Helmet")
    assert helmet.implemented is True
    assert helmet.item_name == "Iron Helm"
    assert helmet.details == ("Type: Heavy", "Base Armor: 4")
    weapon = next(slot for slot in slots if slot.slot == "Weapon")
    assert weapon.item_name == "Sword (1H)"
    assert weapon.details == ("Type: Sword", "Base Damage: 12", "Crit: 15%")
    armor = next(slot for slot in slots if slot.slot == "Armor")
    assert armor.details == ("Type: Medium", "Base Armor: 8")
    ring = next(slot for slot in slots if slot.slot == "Ring")
    assert ring.details == ()
    assert ring.buffs == ("Block",)
    pendant = next(slot for slot in slots if slot.slot == "Pendant")
    assert pendant.details == ()
    assert pendant.buffs == ("Vision",)
    assert pendant.icon_item is player.equipment["Pendant"]
    assert weapon.icon_item is player.equipment["Weapon"]

    player.equipment["Ring"] = SimpleNamespace(
        name="Weightless Ring", typ="Accessory", subtyp="Ring", mod="Dodge", weight=0
    )
    weightless_ring = next(
        slot for slot in screen.build_equipment_slots(player) if slot.slot == "Ring"
    )
    assert weightless_ring.details == ()
    assert weightless_ring.buffs == ("Dodge",)
    player.equipment["Ring"] = SimpleNamespace(
        name="Ruby Ring", typ="Accessory", subtyp="Ring", mod="Block", weight=0.1
    )

    player.equipment["OffHand"] = SimpleNamespace(
        name="Aspis", typ="OffHand", subtyp="Shield", mod=0.1, weight=10
    )
    shield = next(slot for slot in screen.build_equipment_slots(player) if slot.slot == "OffHand")
    assert shield.details == ("Type: Shield", "Block: 10%")
    assert shield.buffs == ()

    player.equipment["OffHand"] = SimpleNamespace(
        name="Apprentice Tome",
        typ="OffHand",
        subtyp="Tome",
        mod=12,
        weight=2,
    )
    tome = next(slot for slot in screen.build_equipment_slots(player) if slot.slot == "OffHand")
    assert tome.details == ("Type: Tome", "Spell Mod: 12")
    assert tome.buffs == ()

    player.equipment["OffHand"] = SimpleNamespace(
        name="Svalinn", typ="OffHand", subtyp="Shield", mod=0.35, weight=18
    )
    svalinn = next(slot for slot in screen.build_equipment_slots(player) if slot.slot == "OffHand")
    assert svalinn.details == ("Type: Shield", "Block: 35%")
    assert svalinn.buffs == ("+25% Fire Resistance",)
    player.equipment["OffHand"] = None

    player.equipment["Pendant"] = SimpleNamespace(
        name="Fire Chain",
        typ="Accessory",
        subtyp="Pendant",
        mod="Resist-Fire",
        weight=0.2,
    )
    fire_chain = next(
        slot for slot in screen.build_equipment_slots(player) if slot.slot == "Pendant"
    )
    assert fire_chain.buffs == ("+50% Fire Resistance",)

    player.equipment["Armor"] = SimpleNamespace(
        name="Resist Armor",
        typ="Armor",
        subtyp="Plate",
        armor=12,
        resistances={"Fire": 0.25, "Water": 0.25},
        weight=18,
    )
    resist_armor = next(
        slot for slot in screen.build_equipment_slots(player) if slot.slot == "Armor"
    )
    assert "+25% Fire Resistance" in resist_armor.buffs
    assert "+25% Water Resistance" in resist_armor.buffs

    player.equipment["Weapon"] = SimpleNamespace(
        name="Claymore",
        typ="Weapon",
        subtyp="Longsword",
        handed=2,
        damage=28,
        crit_chance=0.15,
        weight=12,
    )
    player.equipment["OffHand"] = SimpleNamespace(name="No OffHand", typ="OffHand", subtyp="None")
    player.cls = SimpleNamespace(name="Warrior", equip_check=lambda _item, slot: slot != "OffHand")
    two_handed_slots = screen.build_equipment_slots(player)
    occupied_offhand = next(slot for slot in two_handed_slots if slot.slot == "OffHand")
    assert occupied_offhand.item_name == "Claymore (2H)"
    assert occupied_offhand.icon_item is player.equipment["Weapon"]
    assert occupied_offhand.details == ("Type: Longsword", "Base Damage: 28", "Crit: 15%")

    player.cls = SimpleNamespace(
        name="Berserker", equip_check=lambda _item, slot: slot == "OffHand"
    )
    berserker_offhand = next(
        slot for slot in screen.build_equipment_slots(player) if slot.slot == "OffHand"
    )
    assert berserker_offhand.item_name == "(empty)"

    player.cls = SimpleNamespace(name="Lancer", equip_check=lambda _item, _slot: False)
    player.equipment["Weapon"].subtyp = "Polearm"
    lancer_offhand = next(
        slot for slot in screen.build_equipment_slots(player) if slot.slot == "OffHand"
    )
    assert lancer_offhand.item_name == "(empty)"

    player.cls = SimpleNamespace(name="Hierophant", equip_check=lambda _item, _slot: False)
    player.spellbook = {"Skills": {"Staff Conduit": object()}}
    player.equipment["Weapon"].subtyp = "Staff"
    hierophant_offhand = next(
        slot for slot in screen.build_equipment_slots(player) if slot.slot == "OffHand"
    )
    assert hierophant_offhand.item_name == "(empty)"

    player.equipment["Weapon"] = SimpleNamespace(
        name="Sword", typ="Weapon", subtyp="Sword", damage=12, crit_chance=0.15, weight=4
    )
    player.equipment["OffHand"] = None
    player.equipment["Pendant"] = SimpleNamespace(
        name="Pendant of Sight", typ="Accessory", subtyp="Pendant", mod="Vision", weight=0.2
    )
    player.cls = SimpleNamespace(name="Warrior", equip_check=lambda _item, _slot: True)

    grouped_resistances = screen.group_resistances(player)
    assert [entry.name for entry in grouped_resistances["weaknesses"]] == ["Fire", "Ice", "Water"]
    assert [entry.name for entry in grouped_resistances["resistances"]] == ["Poison", "Physical"]

    player.equipment["Pendant"] = SimpleNamespace(
        name="Fire Chain", typ="Accessory", subtyp="Pendant", mod="Resist-Fire", weight=0.2
    )
    grouped_resistances = screen.group_resistances(player)
    assert "Fire" not in [entry.name for entry in grouped_resistances["weaknesses"]]
    assert "Fire" in [entry.name for entry in grouped_resistances["resistances"]]
    player.equipment["Pendant"] = SimpleNamespace(
        name="Pendant of Sight", typ="Accessory", subtyp="Pendant", mod="Vision", weight=0.2
    )

    equipment_buffs = screen.collect_equipment_buffs(player)
    assert [(buff.name, buff.source) for buff in equipment_buffs] == [
        ("Block", "Ring: Ruby Ring"),
        ("Vision", "Pendant: Pendant of Sight"),
    ]

    assert screen.selected_equipment_slot(player) == "Weapon"
    screen.move_equipment_selector(player, "right")
    assert screen.selected_equipment_slot(player) == "Armor"
    screen.move_equipment_selector(player, "right")
    assert screen.selected_equipment_slot(player) == "OffHand"


def test_portrait_details_draws_long_location_without_truncating(monkeypatch):
    screen = ModernCharacterScreen(_make_presenter())
    drawn = []
    monkeypatch.setattr(
        screen,
        "_draw_text",
        lambda text, font, _color, _x, y, _max_width=None: drawn.append(
            (text, y, font.get_height())
        ),
    )

    detail_rect = pygame.Rect(0, 0, 120, 80)
    screen._draw_portrait_details(
        [("Location", "Realm of Cambion")],
        detail_rect,
        0,
    )

    assert "Realm of Cambion" in [text for text, _y, _height in drawn]
    assert not any(str(text).endswith("...") for text, _y, _height in drawn)
    assert all(y + height <= detail_rect.bottom for _text, y, height in drawn)


def test_portrait_details_compact_rows_stay_inside_short_detail_box(monkeypatch):
    screen = ModernCharacterScreen(_make_presenter())
    drawn = []
    monkeypatch.setattr(
        screen,
        "_draw_text",
        lambda text, font, _color, _x, y, _max_width=None: drawn.append(
            (text, y, font.get_height())
        ),
    )

    detail_rect = pygame.Rect(0, 0, 210, 46)
    screen._draw_portrait_details(
        [("Gold", "71789G"), ("Location", "Dungeon Level 1")],
        detail_rect,
        0,
    )

    assert "Location" in [text for text, _y, _height in drawn]
    assert "Dungeon Level 1" in [text for text, _y, _height in drawn]
    assert all(y + height <= detail_rect.bottom for _text, y, height in drawn)


def test_character_panel_reserves_portrait_detail_rows_after_large_portrait(monkeypatch):
    presenter = _make_presenter()
    screen = ModernCharacterScreen(presenter)
    player = _make_player()
    player.location_z = 7
    player.gold = 71789
    monkeypatch.setattr(
        screen,
        "draw_semi_transparent_panel",
        lambda rect, alpha=180: DummySurface((rect.width, rect.height)),
    )
    monkeypatch.setattr(
        "src.ui_pygame.gui.modern_character_screen.pygame.draw.rect", lambda *_args, **_kwargs: None
    )
    monkeypatch.setattr(
        "src.ui_pygame.gui.modern_character_screen.pygame.draw.line", lambda *_args, **_kwargs: None
    )
    screen.load_portrait = lambda _player: pygame.Surface((225, 400), pygame.SRCALPHA)

    screen.draw_character_panel(player)

    detail_texts = {"Gold", "71789G", "Location", "Dungeon Level 7"}
    detail_blits = [
        (getattr(surface, "text", None), position)
        for surface, position in presenter.screen.blit_calls
        if getattr(surface, "text", None) in detail_texts
    ]
    assert {text for text, _position in detail_blits} == detail_texts
    panel_bottom = screen.character_panel_rect.bottom
    for text, (_x, y) in detail_blits:
        assert y + presenter.small_font.get_height() <= panel_bottom, text


def test_modern_character_companion_display_prefers_familiar_then_living_summon():
    screen = ModernCharacterScreen(_make_presenter())
    player = _make_player()

    assert screen.active_companion_for_display(player) is None

    familiar = SimpleNamespace(
        name="Aster", race="Fairy", level=SimpleNamespace(level=4), is_alive=lambda: True
    )
    player.familiar = familiar
    player.summons = {"Fuath": SimpleNamespace(name="Fuath", is_alive=lambda: True)}
    assert screen.active_companion_for_display(player) == ("Familiar", familiar)
    assert ("Level", "4") in screen.companion_summary_rows("Familiar", familiar)

    player.familiar = None
    spent = SimpleNamespace(name="Spent", is_alive=lambda: False)
    living = SimpleNamespace(
        name="Fuath", race="Spirit", level=SimpleNamespace(pro_level=2), is_alive=lambda: True
    )
    player.summons = {"Spent": spent, "Fuath": living}
    assert screen.active_companion_for_display(player) == ("Xenid", living)
    assert ("Type", "Spirit") in screen.companion_summary_rows("Summon", living)

    patagon = SimpleNamespace(
        name="Patagon", cls=None, level=SimpleNamespace(level=1), is_alive=lambda: True
    )
    assert ("Type", "Summon") in screen.companion_summary_rows("Summon", patagon)

    player.summons = {"Spent": spent}
    assert screen.active_companion_for_display(player) is None


def test_modern_character_class_tab_lists_companions_without_art(monkeypatch):
    presenter = _make_presenter()
    screen = ModernCharacterScreen(presenter)
    player = _make_player()
    companion = SimpleNamespace(
        name="Patagon",
        cls=None,
        health=SimpleNamespace(current=40, max=50),
        mana=SimpleNamespace(current=5, max=10),
        combat=SimpleNamespace(attack=14, defense=8, magic=0, magic_def=3),
        level=SimpleNamespace(level=1),
        is_alive=lambda: True,
    )
    player.cls = SimpleNamespace(
        name="Thaumaturgist", description="Calls Xenids from distant realms."
    )
    player.summons = {"Patagon": companion}
    calls = []
    screen.companion_art_manager = SimpleNamespace(
        get_scaled_sprite=lambda entity, size: calls.append((entity, size)) or DummySurface(size)
    )

    monkeypatch.setattr(
        screen,
        "draw_semi_transparent_panel",
        lambda rect, alpha=180: DummySurface((rect.width, rect.height)),
    )
    monkeypatch.setattr(
        "src.ui_pygame.gui.modern_character_screen.pygame.draw.rect", lambda *_args, **_kwargs: None
    )
    monkeypatch.setattr(
        "src.ui_pygame.gui.modern_character_screen.pygame.draw.line", lambda *_args, **_kwargs: None
    )

    screen.draw_class_tab(player)

    assert calls == []
    rendered_text = set(presenter.small_font.render_calls + presenter.normal_font.render_calls)
    assert {"Xenids", "Patagon", "Type", "Xenid", "HP", "40/50"}.issubset(rendered_text)
    assert "Companions & Summons" not in rendered_text


def test_modern_character_warlock_class_tab_uses_familiar_label(monkeypatch):
    presenter = _make_presenter()
    screen = ModernCharacterScreen(presenter)
    player = _make_player()
    familiar = SimpleNamespace(
        name="Aster",
        cls="Familiar",
        health=SimpleNamespace(current=24, max=30),
        mana=SimpleNamespace(current=18, max=20),
        combat=SimpleNamespace(attack=4, defense=6, magic=12, magic_def=10),
        level=SimpleNamespace(level=4),
        is_alive=lambda: True,
    )
    player.cls = SimpleNamespace(name="Warlock", description="Binds familiar aid.")
    player.familiar = familiar
    player.summons = {}

    monkeypatch.setattr(
        screen,
        "draw_semi_transparent_panel",
        lambda rect, alpha=180: DummySurface((rect.width, rect.height)),
    )
    monkeypatch.setattr(
        "src.ui_pygame.gui.modern_character_screen.pygame.draw.rect", lambda *_args, **_kwargs: None
    )
    monkeypatch.setattr(
        "src.ui_pygame.gui.modern_character_screen.pygame.draw.line", lambda *_args, **_kwargs: None
    )

    screen.draw_class_tab(player)

    rendered_text = set(presenter.small_font.render_calls + presenter.normal_font.render_calls)
    assert {"Familiar", "Aster", "C: Select familiar"}.issubset(rendered_text)
    assert "Companion" not in rendered_text
    assert "C: Select summon" not in rendered_text


def test_modern_character_ranger_companion_tab_shows_bond_form_and_special(monkeypatch):
    presenter = _make_presenter()
    screen = ModernCharacterScreen(presenter)
    player = _make_player()
    companion = SimpleNamespace(
        name="Giant Rat",
        species="Rat",
        spec="Tamed",
        evolution="Tunnel Rat",
        special_ability="Pounce",
        bond=25,
        health=SimpleNamespace(current=20, max=20),
        mana=SimpleNamespace(current=1, max=1),
        combat=SimpleNamespace(attack=4, defense=5, magic=1, magic_def=3),
        level=SimpleNamespace(level=1),
        is_alive=lambda: True,
    )
    player.cls = SimpleNamespace(name="Ranger", description="Tames companions.")
    player.familiar = companion
    player.kill_dict = {"Animal": {"Giant Rat": 8}}
    player.tamed_companion = {
        "active": True,
        "enemy_class": "GiantRat",
        "name": "Giant Rat",
        "species": "Rat",
        "bond": 25,
        "evolution": "Tunnel Rat",
        "special_ability": "Pounce",
        "active_index": 0,
        "companions": [
            {
                "active": True,
                "enemy_class": "GiantRat",
                "name": "Giant Rat",
                "species": "Rat",
                "bond": 25,
                "evolution": "Tunnel Rat",
                "special_ability": "Pounce",
            },
            {
                "active": False,
                "enemy_class": "Direwolf",
                "name": "Direwolf",
                "species": "Direwolf",
                "bond": 5,
                "evolution": "Wolf Pup",
                "special_ability": "Pounce",
            },
        ],
    }
    screen.companion_art_manager = SimpleNamespace(
        get_scaled_sprite=lambda _entity, size: DummySurface(size)
    )

    _stub_character_screen_drawing(monkeypatch, screen)

    screen.draw_class_tab(player)

    entries = screen.class_companion_entries(player)
    assert [(kind, entry.name) for kind, entry in entries] == [("Companion", "Giant Rat")]
    active_slot = screen.class_companion_tile_rects(entries)[0]
    assert active_slot.height == screen._class_companion_large_slot_rect().height
    assert active_slot.height > 100

    rendered_text = _rendered_text(presenter)
    assert {
        "Companion",
        "Giant Rat",
        "Favored Enemy",
        "None",
        "Tracking Mastery",
        "No marked quarry",
        "0/100 Use Favored Enemy in combat",
        "Type",
        "Form",
        "Tunnel Rat",
        "Special",
        "Pounce",
        "Bond",
        "25/100",
    }.issubset(rendered_text)
    assert {"Held", "2/6", "Held Companion"}.isdisjoint(rendered_text)
    assert {"Level", "HP", "MP", "Attack", "Defense", "Magic", "XP", "0/0 XP"}.isdisjoint(
        rendered_text
    )
    assert ("Level", "1") not in screen.companion_summary_rows("Companion", player.familiar)
    detail_rows = screen.companion_detail_rows("Companion", player.familiar)
    assert all(
        label not in {"HP", "MP", "Attack", "Defense", "Magic", "Magic Defense"}
        for label, _value in detail_rows
    )


def test_modern_character_ranger_without_companion_shows_one_large_empty_slot(monkeypatch):
    presenter = _make_presenter()
    screen = ModernCharacterScreen(presenter)
    player = _make_player()
    player.cls = SimpleNamespace(name="Ranger", description="Tames companions.")
    player.familiar = None
    player.tamed_companion = None
    player.kill_dict = {"Animal": {"Giant Rat": 12}, "Undead": {"Skeleton": 5}}

    _stub_character_screen_drawing(monkeypatch, screen)

    screen.draw_class_tab(player)

    rendered_text = _rendered_text(presenter)
    assert {
        "Favored Enemy",
        "None",
        "Tracking Mastery",
        "No marked quarry",
        "0/100 Use Favored Enemy in combat",
        "Companion",
        "No Active Companion",
        "Tame a wounded Animal to form a bond.",
    }.issubset(rendered_text)
    empty_slot = screen._class_companion_large_slot_rect()
    assert empty_slot.height > 100
    assert {
        "Held",
        "0/6",
        "Companion Stable",
        "Tame a wounded Animal to fill a slot.",
        "Empty Slot 1",
        "Empty Slot 6",
        "Available",
    }.isdisjoint(rendered_text)


def test_modern_character_ranger_companion_tab_shows_marked_quarry_mastery(monkeypatch):
    presenter = _make_presenter()
    screen = ModernCharacterScreen(presenter)
    player = _make_player()
    player.cls = SimpleNamespace(name="Ranger", description="Tames companions.")
    player.familiar = None
    player.tamed_companion = None
    player.promotion_kit_state = promotion_kits.default_state()
    player.promotion_kit_state["favored_enemy"] = {"type": "Undead", "practice": 16, "switches": 1}

    _stub_character_screen_drawing(monkeypatch, screen)

    screen.draw_class_tab(player)

    rendered_text = _rendered_text(presenter)
    assert {
        "Favored Enemy",
        "Undead",
        "Tracking Mastery",
        "16/100 Known Trail - 16 practice",
        "Quarry changes: 1",
    }.issubset(rendered_text)
    assert "Undead +4 Known Trail" not in rendered_text


def test_modern_character_ranger_companion_tab_releases_active_companion(monkeypatch):
    presenter = _make_presenter()
    screen = ModernCharacterScreen(presenter)
    player = _make_player()
    player.cls = SimpleNamespace(name="Ranger", description="Tames companions.")
    player.tamed_companion = {
        "active": True,
        "enemy_class": "GiantRat",
        "name": "Giant Rat",
        "species": "Rat",
        "bond": 25,
        "evolution": "Tunnel Rat",
        "special_ability": "Pounce",
        "active_index": 0,
        "companions": [
            {
                "active": True,
                "enemy_class": "GiantRat",
                "name": "Giant Rat",
                "species": "Rat",
                "bond": 25,
                "evolution": "Tunnel Rat",
                "special_ability": "Pounce",
            },
            {
                "active": False,
                "enemy_class": "Direwolf",
                "name": "Direwolf",
                "species": "Direwolf",
                "bond": 5,
                "evolution": "Wolf Pup",
                "special_ability": "Pounce",
            },
        ],
    }
    player.tamed_companion = ability_mechanics.normalize_tamed_companion(player.tamed_companion)
    player.familiar = companions.tamed_companion_from_state(player.tamed_companion)

    popup_messages = []

    class FakePopup:
        def __init__(self, _presenter, message, show_buttons=True):
            popup_messages.append((message, show_buttons))

        def show(self, **kwargs):
            popup_messages.append(("shown", kwargs))
            return True

    monkeypatch.setattr(
        "src.ui_pygame.gui.modern_character_screen.layout.ConfirmationPopup", FakePopup
    )
    screen.selected_class_companion_index = 0
    screen._release_selected_tamed_companion(player)
    assert popup_messages[0] == ("Release Giant Rat?", True)
    assert popup_messages[1][1].get("flush_events") is True
    assert len(player.tamed_companion["companions"]) == 1
    assert player.tamed_companion["enemy_class"] == "Direwolf"

    player.tamed_companion = ability_mechanics.normalize_tamed_companion(
        {
            "active": True,
            "enemy_class": "GiantRat",
            "name": "Giant Rat",
            "species": "Rat",
            "bond": 25,
            "companions": [
                {
                    "active": True,
                    "enemy_class": "GiantRat",
                    "name": "Giant Rat",
                    "species": "Rat",
                    "bond": 25,
                }
            ],
        }
    )
    screen.selected_class_companion_index = 0
    popup_messages.clear()

    class CancelPopup(FakePopup):
        def show(self, **kwargs):
            popup_messages.append(("shown", kwargs))
            return False

    monkeypatch.setattr(
        "src.ui_pygame.gui.modern_character_screen.layout.ConfirmationPopup", CancelPopup
    )
    screen._release_selected_tamed_companion(player)
    assert len(player.tamed_companion["companions"]) == 1


def test_modern_character_ranger_tamed_roster_rebuilds_random_animals_stably():
    presenter = _make_presenter()
    screen = ModernCharacterScreen(presenter)
    player = _make_player()
    player.cls = SimpleNamespace(name="Ranger", description="Tames companions.")
    player.tamed_companion = {
        "active": True,
        "enemy_class": "GiantHornet",
        "name": "Giant Hornet",
        "species": "Hornet",
        "bond": 25,
        "evolution": "Amber Hornet",
        "special_ability": "Wingbeat",
        "active_index": 0,
        "companions": [
            {
                "active": True,
                "enemy_class": "GiantHornet",
                "name": "Giant Hornet",
                "species": "Hornet",
                "bond": 25,
                "evolution": "Amber Hornet",
                "special_ability": "Wingbeat",
            },
        ],
    }

    first = screen.class_companion_entries(player)[0][1]
    second = screen.class_companion_entries(player)[0][1]

    assert first.health.max == second.health.max
    assert first.mana.max == second.mana.max
    assert first.combat.attack == second.combat.attack


def test_modern_character_oath_conviction_tab_shows_vow_details(monkeypatch):
    presenter = _make_presenter()
    screen = ModernCharacterScreen(presenter)
    player = _make_player()
    player.cls = SimpleNamespace(name="Paladin", description="Holy knight.")
    player.paladin_vow = {"path": "Redemption"}
    promotion_kits.combat_state(player)["oath_conviction"] = 1

    monkeypatch.setattr(
        screen,
        "draw_semi_transparent_panel",
        lambda rect, alpha=180: DummySurface((rect.width, rect.height)),
    )
    monkeypatch.setattr(
        "src.ui_pygame.gui.modern_character_screen.pygame.draw.rect", lambda *_args, **_kwargs: None
    )
    monkeypatch.setattr(
        "src.ui_pygame.gui.modern_character_screen.pygame.draw.line", lambda *_args, **_kwargs: None
    )

    screen.select_tab("class")
    screen.draw_class_tab(player)

    rendered_text = set(
        presenter.large_font.render_calls
        + presenter.normal_font.render_calls
        + presenter.small_font.render_calls
    )
    assert {
        "Oath Conviction",
        "Conviction 1/2",
        "Vow",
        "Redemption",
        "Signature",
        "Redeem",
        "Aura",
        "Redemption Aura",
        "Mark",
        "Mark of Perdition",
        "Oath Rhythm",
        "Build",
        "Spend",
        "Risk",
    }.issubset(rendered_text)
    assert "Paladin" not in rendered_text
    assert not any(
        "class ring" in str(text).lower() or "ring identity" in str(text).lower()
        for text in rendered_text
    )


def test_modern_character_aerial_tempo_tab_owns_jump_mods(monkeypatch):
    presenter = _make_presenter()
    screen = ModernCharacterScreen(presenter)
    player = _make_player()
    player.cls = SimpleNamespace(name="Lancer", description="Leaps into danger.")
    player.spellbook["Skills"]["Jump"] = FakeJumpSkill()
    promotion_kits.combat_state(player)["aerial_tempo"] = 1

    monkeypatch.setattr(
        screen,
        "draw_semi_transparent_panel",
        lambda rect, alpha=180: DummySurface((rect.width, rect.height)),
    )
    monkeypatch.setattr(
        "src.ui_pygame.gui.modern_character_screen.pygame.draw.rect", lambda *_args, **_kwargs: None
    )
    monkeypatch.setattr(
        "src.ui_pygame.gui.modern_character_screen.pygame.draw.line", lambda *_args, **_kwargs: None
    )

    screen.select_tab("class")
    screen.draw_class_tab(player)

    rendered_text = set(
        presenter.large_font.render_calls
        + presenter.normal_font.render_calls
        + presenter.small_font.render_calls
    )
    assert {
        "Aerial Tempo",
        "Aerial Tempo: 1/2",
        "Jump Modifications (2/3 active)",
        "UP/DOWN: Select  ENTER: Toggle",
        "[X]",
        "Crit",
        "Recover",
        "Skyfall",
        "Status: Active",
        "Initial modification",
    }.issubset(rendered_text)
    assert screen.jump_mod_row_rects()
    assert len(screen.jump_mod_row_rects()) == 3
    assert "Lancer" not in rendered_text
    assert any("Build with clean Jump landings" in str(text) for text in rendered_text)
    assert "Ring Identity" not in rendered_text
    assert not any(
        "class ring" in str(text).lower() or "ring identity" in str(text).lower()
        for text in rendered_text
    )


def test_aerial_tempo_tab_fits_every_jump_mod_without_scrolling(monkeypatch):
    presenter = _make_presenter()
    screen = ModernCharacterScreen(presenter)
    player = _make_player()
    player.cls = SimpleNamespace(name="Dragoon", description="Rules the sky.")
    jump_skill = FakeJumpSkill()
    mod_names = (
        "Crit",
        "Thrust",
        "Defend",
        "Rend",
        "Quake",
        "Acrobat",
        "Dragon's Fury",
        "Soaring Strike",
        "Quick Dive",
        "Retribution",
        "Unstoppable",
        "Recover",
        "Skyfall",
    )
    jump_skill.modifications = {name: False for name in mod_names}
    jump_skill.get_unlocked_modifications = lambda: list(mod_names)
    player.spellbook["Skills"]["Jump"] = jump_skill
    drawn_rects = []

    monkeypatch.setattr(
        screen,
        "draw_semi_transparent_panel",
        lambda rect, alpha=180: DummySurface((rect.width, rect.height)),
    )
    monkeypatch.setattr(
        "src.ui_pygame.gui.modern_character_screen.pygame.draw.rect",
        lambda _surface, _color, rect, *_args, **_kwargs: (
            drawn_rects.append(rect.copy()) if isinstance(rect, pygame.Rect) else None
        ),
    )
    monkeypatch.setattr(
        "src.ui_pygame.gui.modern_character_screen.pygame.draw.line",
        lambda *_args, **_kwargs: None,
    )

    screen.select_tab("class")
    screen.draw_class_tab(player)

    row_rects = screen.jump_mod_row_rects()
    assert len(row_rects) == len(mod_names)
    assert len({rect.left for rect in row_rects}) == 2
    assert max(rect.bottom for rect in row_rects) <= screen.details_rect.bottom
    assert any(rect.height == 190 for rect in drawn_rects)


def test_modern_character_resolve_tab_shows_meter_progression(monkeypatch):
    presenter = _make_presenter()
    screen = ModernCharacterScreen(presenter)
    player = _make_player()
    player.cls = SimpleNamespace(name="Sentinel", description="Holds the line.")
    player.spellbook["Skills"] = {
        "Hold the Line": abilities.HoldTheLine(),
        "Brace Wall": abilities.BraceWall(),
        "Spell Block": abilities.SpellBlock(),
        "Bulwark Guard": abilities.BulwarkGuard(),
        "Purge Weakness": abilities.PurgeWeakness(),
        "Repercussion": abilities.Repercussion(),
        "Boast": abilities.Boast(),
        "Focused Assault": abilities.FocusedAssault(),
    }
    class_rings.ensure_state(player)["data"]["Stalwart Defender"]["guard_meter"] = 25
    promotion_kits.combat_state(player)["hold_the_line"] = 1
    rect_calls = []

    monkeypatch.setattr(
        screen,
        "draw_semi_transparent_panel",
        lambda rect, alpha=180: DummySurface((rect.width, rect.height)),
    )
    monkeypatch.setattr(
        "src.ui_pygame.gui.modern_character_screen.pygame.draw.rect",
        lambda _surface, color, rect, *_args, **_kwargs: (
            rect_calls.append((color, rect.copy())) if isinstance(rect, pygame.Rect) else None
        ),
    )
    monkeypatch.setattr(
        "src.ui_pygame.gui.modern_character_screen.pygame.draw.line", lambda *_args, **_kwargs: None
    )

    screen.select_tab("class")
    screen.draw_class_tab(player)

    rendered_text = set(
        presenter.large_font.render_calls
        + presenter.normal_font.render_calls
        + presenter.small_font.render_calls
    )
    assert {
        "25/50",
        "Resolve Spends",
        "Hold the Line",
        "Brace Wall",
        "Spell Block",
        "Bulwark Guard",
        "Purge Weakness",
        "Repercussion",
        "Boast",
        "Focused Assault",
    }.issubset(rendered_text)
    assert "Resolve" not in presenter.large_font.render_calls
    assert "Resolve Bursts" not in rendered_text
    assert "Defensive Mastery" in rendered_text
    assert "Unknown Burst" not in rendered_text
    assert not {
        "Citadel Aegis",
        "Ironwall Revenge",
        "Last Bastion",
        "Stronghold",
    }.intersection(rendered_text)
    assert not any("/4" in str(text) for text in rendered_text)
    assert "Resolve 25/50" not in rendered_text
    meter_rects = [rect for _color, rect in rect_calls if rect.height == 28]
    assert meter_rects
    assert abs(meter_rects[0].centerx - screen.details_rect.centerx) <= 1
    assert any(color == screen.colors.RED and rect.height == 28 for color, rect in rect_calls)
    assert "Sentinel" not in rendered_text
    assert "Resolve Flow" not in rendered_text
    assert "Guard Stance" not in rendered_text
    assert "Build" not in rendered_text
    assert not any(
        "class ring" in str(text).lower() or "ring identity" in str(text).lower()
        for text in rendered_text
    )


def test_modern_character_resolve_tab_shows_stalwart_surges(monkeypatch):
    presenter = _make_presenter()
    screen = ModernCharacterScreen(presenter)
    player = _make_player()
    player.cls = SimpleNamespace(name="Stalwart Defender", description="Holds the line.")
    player.spellbook["Skills"] = {
        "Hold the Line": abilities.HoldTheLine(),
        "Brace Wall": abilities.BraceWall(),
        "Spell Block": abilities.SpellBlock(),
        "Bulwark Guard": abilities.BulwarkGuard(),
        "Purge Weakness": abilities.PurgeWeakness(),
        "Repercussion": abilities.Repercussion(),
        "Boast": abilities.Boast(),
        "Focused Assault": abilities.FocusedAssault(),
        "Citadel Aegis": abilities.CitadelAegis(),
        "Ironwall Revenge": abilities.IronwallReprisal(),
        "Last Bastion": abilities.LastBastionSurge(),
        "Stronghold": abilities.Stronghold(),
    }
    data = class_rings.ensure_state(player)["data"]["Stalwart Defender"]
    data["guard_meter"] = 100
    data["resolve_mastery"].update({key: 4 for key in data["resolve_mastery"]})

    monkeypatch.setattr(
        screen,
        "draw_semi_transparent_panel",
        lambda rect, alpha=180: DummySurface((rect.width, rect.height)),
    )
    monkeypatch.setattr(
        "src.ui_pygame.gui.modern_character_screen.pygame.draw.rect", lambda *_args, **_kwargs: None
    )
    monkeypatch.setattr(
        "src.ui_pygame.gui.modern_character_screen.pygame.draw.line", lambda *_args, **_kwargs: None
    )

    screen.select_tab("class")
    screen.draw_class_tab(player)

    rendered_text = set(
        presenter.large_font.render_calls
        + presenter.normal_font.render_calls
        + presenter.small_font.render_calls
    )
    assert {
        "100/100",
        "Resolve Spends",
        "Resolve Bursts",
        "Citadel Aegis",
        "Ironwall Revenge",
        "Last Bastion",
        "Stronghold",
    }.issubset(rendered_text)
    assert "Resolve" not in presenter.large_font.render_calls
    assert "???" not in rendered_text
    assert any("Full bar" in str(text) for text in rendered_text)
    assert not any(
        "class ring" in str(text).lower() or "ring identity" in str(text).lower()
        for text in rendered_text
    )


def test_modern_character_class_tab_shows_weapon_discipline_for_weapon_master(monkeypatch):
    presenter = _make_presenter()
    screen = ModernCharacterScreen(presenter)
    player = _make_player()
    player.cls = SimpleNamespace(
        name="Weapon Master", description="Builds mastery through repeated weapon use."
    )
    player.equipment["Weapon"] = SimpleNamespace(name="Broadaxe", typ="Weapon", subtyp="Battle Axe")
    player.equipment["OffHand"] = SimpleNamespace(name="No OffHand", typ="OffHand", subtyp="None")
    player.grandmaster_discipline = grandmaster.default_state()
    battle_axe_xp = grandmaster.XP_THRESHOLDS[0] + 1
    player.grandmaster_discipline["disciplines"]["Battle Axe"]["xp"] = battle_axe_xp
    player.grandmaster_discipline["disciplines"]["Battle Axe"]["rank"] = grandmaster.rank_for_xp(
        battle_axe_xp
    )
    render_calls = []
    screen.item_render_manager = SimpleNamespace(
        get_scaled_render=lambda item, size: render_calls.append((getattr(item, "name", ""), size))
        or DummySurface(size)
    )

    monkeypatch.setattr(
        screen,
        "draw_semi_transparent_panel",
        lambda rect, alpha=180: DummySurface((rect.width, rect.height)),
    )
    monkeypatch.setattr(
        "src.ui_pygame.gui.modern_character_screen.pygame.draw.rect", lambda *_args, **_kwargs: None
    )
    monkeypatch.setattr(
        "src.ui_pygame.gui.modern_character_screen.pygame.draw.line", lambda *_args, **_kwargs: None
    )

    screen.draw_class_tab(player)

    assert screen.class_summary_rows(player) == []

    rendered_text = set(
        presenter.large_font.render_calls
        + presenter.small_font.render_calls
        + presenter.normal_font.render_calls
    )
    assert {
        "Weapon Discipline",
        "Battle Axe",
        "Rank 1",
        f"{battle_axe_xp}/{grandmaster.XP_THRESHOLDS[1]} XP",
    }.issubset(rendered_text)
    assert "Reaver's Mark" not in rendered_text
    assert "Companions & Summons" not in rendered_text
    assert "Weapon Master" not in rendered_text
    assert "Promotion Tier" not in rendered_text
    assert "Equipped Discipline" not in rendered_text
    assert "Highest Discipline" not in rendered_text
    assert any(name == "Broadaxe" for name, _size in render_calls)
    assert screen.weapon_discipline_detail_text(player, "Battle Axe").splitlines()[:6] == [
        "Battle Axe Discipline",
        f"Rank 1 - {battle_axe_xp}/{grandmaster.XP_THRESHOLDS[1]} XP",
        "Equipped now: Yes",
        "",
        "Weapon Art: Reaver's Mark",
        "Required weapon: Battle Axe",
    ]


def test_modern_character_weapon_discipline_popup_uses_selected_row(monkeypatch):
    presenter = _make_presenter()
    screen = ModernCharacterScreen(presenter)
    player = _make_player()
    player.cls = SimpleNamespace(
        name="Weapon Master", description="Builds mastery through repeated weapon use."
    )
    player.equipment["Weapon"] = SimpleNamespace(name="Framea", typ="Weapon", subtyp="Polearm")
    player.grandmaster_discipline = grandmaster.default_state()
    screen.selected_weapon_discipline_index = grandmaster.WEAPON_TYPES.index("Polearm")
    popup_messages = []
    popup_kwargs = []

    class FakePopup:
        def __init__(self, _presenter, message, show_buttons=False, **_kwargs):
            popup_messages.append((message, show_buttons))

        def show(self, **kwargs):
            popup_kwargs.append(kwargs)

    monkeypatch.setattr(
        "src.ui_pygame.gui.modern_character_screen.layout.ConfirmationPopup", FakePopup
    )

    screen._open_weapon_discipline_popup(player)

    assert "Polearm Discipline" in popup_messages[0][0]
    assert "Weapon Art: Brace" in popup_messages[0][0]
    assert "Required weapon: Polearm" in popup_messages[0][0]
    assert popup_messages[0][1] is False
    assert popup_kwargs[0]["flush_events"] is True


def test_berserker_weapon_discipline_tab_hides_one_handed_entries():
    presenter = _make_presenter()
    screen = ModernCharacterScreen(presenter)
    player = _make_player()
    player.cls = SimpleNamespace(name="Berserker")
    player.grandmaster_discipline = grandmaster.default_state()

    rows = screen.weapon_discipline_rows(player)

    assert [weapon_type for weapon_type, _progress in rows] == [
        "Longsword",
        "Battle Axe",
        "Polearm",
        "Hammer",
    ]


def test_modern_character_school_affinity_tab_shows_affinity_grid(monkeypatch):
    presenter = _make_presenter()
    screen = ModernCharacterScreen(presenter)
    player = _make_player()
    player.cls = SimpleNamespace(name="Wizard", description="Arcane scholar.")
    player.wizard_affinity = wizard.default_affinity()
    player.wizard_affinity["Fire"] = 82
    player.wizard_affinity["Ice"] = 50
    player.wizard_affinity_version = 2
    player.spellbook["Spells"] = {
        "Fireball": SimpleNamespace(name="Fireball"),
        "Ice Lance": SimpleNamespace(name="Ice Lance"),
    }
    icon_keys = []
    icon_manager = SimpleNamespace(
        get_icon=lambda key: (icon_keys.append(key) or DummySurface((32, 32), text=f"icon:{key}")),
    )
    monkeypatch.setattr(
        "src.ui_pygame.gui.modern_character_screen.mechanics.get_ability_icon_manager",
        lambda: icon_manager,
    )
    _stub_character_screen_drawing(monkeypatch, screen)

    screen.select_tab("class")
    screen.draw_class_tab(player)

    rendered_text = _rendered_text(presenter)
    assert {"School Affinity", "82/100"}.issubset(rendered_text)
    assert "Fire" not in rendered_text
    assert "Wizard Ring" not in rendered_text
    assert {"Fireball", "Ice Lance"}.isdisjoint(rendered_text)
    assert {
        "Affinity Cap 100",
        "Sorcerer Upgrade",
        "Wizard Upgrade",
        "Opposite Drift",
        "Ring Acceleration",
        "Affinity Notes",
        "Specialization",
    }.isdisjoint(rendered_text)
    assert "Promotion Tier" not in rendered_text
    radar_surfaces = [
        surface
        for surface, _position in presenter.screen.blit_calls
        if isinstance(surface, pygame.Surface)
    ]
    assert radar_surfaces
    assert radar_surfaces[0].get_width() > screen.details_rect.width // 2
    assert icon_keys == [
        "spell_fire",
        "spell_water",
        "spell_earth",
        "spell_ice",
        "spell_lightning",
        "spell_wind",
    ]


def test_modern_character_school_affinity_tab_hides_wizard_details_for_sorcerer(monkeypatch):
    presenter = _make_presenter()
    screen = ModernCharacterScreen(presenter)
    player = _make_player()
    player.cls = SimpleNamespace(name="Sorcerer", description="Elemental scholar.")
    player.wizard_affinity = wizard.default_affinity()
    player.wizard_affinity["Fire"] = 12
    player.wizard_affinity_version = 2
    player.spellbook["Spells"] = {"Firebolt": SimpleNamespace(name="Firebolt")}
    _stub_character_screen_drawing(monkeypatch, screen)

    screen.select_tab("class")
    screen.draw_class_tab(player)

    rendered_text = _rendered_text(presenter)
    assert {"School Affinity", "12/50"}.issubset(rendered_text)
    assert "Fire" not in rendered_text
    assert "Firebolt" not in rendered_text
    assert {"Affinity Cap 50", "Wizard Ring", "Not visible", "Specialization"}.isdisjoint(
        rendered_text
    )


def test_modern_character_contracts_tab_shows_patron_state(monkeypatch):
    presenter = _make_presenter()
    screen = ModernCharacterScreen(presenter)
    player = _make_player()
    player.cls = SimpleNamespace(name="Demonologist", description="Bargains with patrons.")
    player.demonologist_contracts = demonologist.default_state()
    player.demonologist_contracts.update(
        {
            "crypt_unlocked": True,
            "unlocked_contracts": ["Imp", "Quasit"],
            "active_patron": "Imp",
            "corruption": 55,
            "imprisoned_familiar": {"name": "Aster", "spec": "Arcane"},
            "contract_history": [{"patron": "Imp", "intent": "Harm", "gold": 160}],
        }
    )
    player.demonologist_contracts["patron_moods"]["Imp"] = 30
    _stub_character_screen_drawing(monkeypatch, screen)

    screen.select_tab("class")
    screen.draw_class_tab(player)

    rendered_text = _rendered_text(presenter)
    assert {
        "Contracts",
        "Bargain Taint",
        "55/100 Tier 2",
        "Active Patron",
        "Imp",
        "Recent Contracts",
        "Imp - Harm",
        "Echo",
    }.issubset(rendered_text)
    assert {"Available Intents", "Withheld Intents", "Cost 160"}.isdisjoint(rendered_text)
    assert "Promotion Tier" not in rendered_text


def test_modern_character_runes_tab_shows_constellation_and_boosts(monkeypatch):
    presenter = _make_presenter()
    screen = ModernCharacterScreen(presenter)
    player = _make_player()
    player.cls = SimpleNamespace(name="Astromancer", description="Reads signs.")
    player.astromancer_state = astromancer.default_state()
    player.astromancer_state["runes"]["Ember"] = 2
    player.astromancer_state["active_constellation_index"] = 0
    player.spellbook["Spells"] = {
        "Firebolt": SimpleNamespace(name="Firebolt", subtyp="Fire", passive=False, cost=1)
    }
    _stub_character_screen_drawing(monkeypatch, screen)

    screen.select_tab("class")
    screen.draw_class_tab(player)

    rendered_text = _rendered_text(presenter)
    assert {
        "Runes",
        "Active Constellation: Ember",
        "Ember",
        "2/3 Fire active",
        "Boostable Spells",
        "Firebolt",
    }.issubset(rendered_text)
    assert {
        "Runic Boost Floor",
        "Active Ring Floor",
        "Rune Source",
        "75%",
        "Rune Notes",
    }.isdisjoint(rendered_text)
    assert "Promotion Tier" not in rendered_text


def test_modern_character_runes_tab_hides_astromancer_details_for_diviner(monkeypatch):
    presenter = _make_presenter()
    screen = ModernCharacterScreen(presenter)
    player = _make_player()
    player.cls = SimpleNamespace(name="Diviner", description="Reads runes.")
    player.astromancer_state = astromancer.default_state()
    player.astromancer_state["runes"]["Tide"] = 1
    player.spellbook["Spells"] = {
        "Water Jet": SimpleNamespace(name="Water Jet", subtyp="Water", passive=False, cost=1)
    }
    _stub_character_screen_drawing(monkeypatch, screen)

    screen.select_tab("class")
    screen.draw_class_tab(player)

    rendered_text = _rendered_text(presenter)
    assert {"Runes", "Tide", "1/3 Water", "Boostable Spells", "Water Jet"}.issubset(rendered_text)
    assert {"Active Constellation: Ember", "Ring", "Not visible"}.isdisjoint(rendered_text)


def test_modern_character_totems_tab_shows_review_and_selector(monkeypatch):
    presenter = _make_presenter()
    screen = ModernCharacterScreen(presenter)
    player = _make_player()
    player.cls = SimpleNamespace(name="Soulcatcher", description="Binds nature.")
    player.spellbook["Skills"]["Totem"] = FakeTotemSkill()
    player.spellbook["Spells"] = {
        "Fireball": SimpleNamespace(name="Fireball"),
        "Tsunami": SimpleNamespace(name="Tsunami"),
        "Soul Drain": SimpleNamespace(name="Soul Drain"),
    }
    player.magic_effects["Totem"] = _effect(True, 3, {"aspect": "Fire", "resonance": 2})
    promotion_kits.combat_state(player)["totem_resonance"] = 2
    _stub_character_screen_drawing(monkeypatch, screen)

    screen.select_tab("class")
    screen.draw_class_tab(player)

    rendered_text = _rendered_text(presenter)
    assert {
        "Totems",
        "Totem Resonance",
        "2/3 Pulse strength",
        "Active Aspect",
        "Fire",
        "Unlocked Aspects",
        "Fire, Water, Soul",
        "Staff Bond",
        "Unfocused",
        "Select",
        "C/Enter: Totem Aspects",
        "Communions",
        "Soul",
        "Unlocked - Soul Drain",
    }.issubset(rendered_text)
    assert {"Pulse Chance", "Staff Bonus", "+20% matching cast"}.isdisjoint(rendered_text)
    assert "Promotion Tier" not in rendered_text

    opened = []

    class FakePopup:
        def __init__(self, _presenter, _screen, title="Totem Aspects"):
            opened.append(title)

        def show(self, **kwargs):
            opened.append(kwargs["player_char"].cls.name)

    import src.ui_pygame.gui.modern_character_screen as modern_module

    monkeypatch.setattr(modern_module.mechanics, "TotemAspectsPopupMenu", FakePopup)
    screen._open_totem_aspects_popup(player)
    assert opened == ["Totem Aspects", "Soulcatcher"]


def test_modern_character_totems_tab_c_opens_existing_aspect_popup(monkeypatch):
    presenter = _make_presenter()
    screen = ModernCharacterScreen(presenter)
    player = _make_player()
    player.cls = SimpleNamespace(name="Shaman", description="Binds nature.")
    player.spellbook["Skills"]["Totem"] = FakeTotemSkill()
    screen.select_tab("class")
    opened = []

    class FakePopup:
        def __init__(self, _presenter, _screen, title="Totem Aspects"):
            opened.append(title)

        def show(self, **kwargs):
            opened.append(kwargs["player_char"].cls.name)

    import src.ui_pygame.gui.modern_character_screen as modern_module

    monkeypatch.setattr(modern_module.mechanics, "TotemAspectsPopupMenu", FakePopup)
    monkeypatch.setattr(screen, "draw_all", lambda *_args, **_kwargs: None)
    monkeypatch.setattr("src.ui_pygame.gui.input_guards.pygame.key.get_pressed", lambda: [])
    event_batches = iter(
        [
            [pygame.event.Event(pygame.KEYDOWN, key=pygame.K_c)],
            [pygame.event.Event(pygame.KEYDOWN, key=pygame.K_ESCAPE)],
        ]
    )
    monkeypatch.setattr(
        "src.ui_pygame.gui.modern_character_screen.pygame.event.get",
        lambda: next(event_batches, []),
    )

    assert screen.navigate(player) == "Exit Menu"
    assert opened == ["Totem Aspects", "Shaman"]
    assert screen.class_companion_selector_active is False


def test_modern_character_totems_tab_hides_soulcatcher_soul_for_shaman(monkeypatch):
    presenter = _make_presenter()
    screen = ModernCharacterScreen(presenter)
    player = _make_player()
    player.cls = SimpleNamespace(name="Shaman", description="Binds nature.")
    player.spellbook["Skills"]["Totem"] = FakeTotemSkill()
    player.spellbook["Spells"] = {"Soul Drain": SimpleNamespace(name="Soul Drain")}
    _stub_character_screen_drawing(monkeypatch, screen)

    screen.select_tab("class")
    screen.draw_class_tab(player)

    rendered_text = _rendered_text(presenter)
    assert {"Totems", "Unlocked Aspects", "Fire, Water"}.issubset(rendered_text)
    assert {"Soul", "Unlocked - Soul Drain"}.isdisjoint(rendered_text)


def test_modern_character_case_journal_tab_shows_progress_and_wayfinding(monkeypatch):
    presenter = _make_presenter()
    screen = ModernCharacterScreen(presenter)
    player = _make_player()
    player.cls = SimpleNamespace(name="Seeker", description="Follows evidence.")
    player.promotion_kit_state = promotion_kits.default_state()
    player.promotion_kit_state["case_journal"] = {"Fiend": 80, "Beast": 25}
    promotion_kits.combat_state(player)["revelation"] = {"target": 2}
    _stub_character_screen_drawing(monkeypatch, screen)

    screen.select_tab("class")
    screen.draw_class_tab(player)

    rendered_text = _rendered_text(presenter)
    assert {
        "Case Journal",
        "Best Case",
        "Fiend",
        "Best Rank",
        "Pattern Lock",
        "Revelation",
        "Target-specific in combat",
        "Wayfinding",
        "Contextual",
        "Studied Enemy Types",
    }.issubset(rendered_text)
    assert "5%" not in rendered_text
    assert "Promotion Tier" not in rendered_text


def test_modern_character_case_journal_tab_hides_seeker_tools_for_inquisitor(monkeypatch):
    presenter = _make_presenter()
    screen = ModernCharacterScreen(presenter)
    player = _make_player()
    player.cls = SimpleNamespace(name="Inquisitor", description="Studies enemies.")
    player.promotion_kit_state = promotion_kits.default_state()
    player.promotion_kit_state["case_journal"] = {"Beast": 25}
    _stub_character_screen_drawing(monkeypatch, screen)

    screen.select_tab("class")
    screen.draw_class_tab(player)

    rendered_text = _rendered_text(presenter)
    assert {"Case Journal", "Best Case", "Beast", "Known Tells", "Studied Enemy Types"}.issubset(
        rendered_text
    )
    assert {"Wayfinding", "Hidden Cache", "Not visible"}.isdisjoint(rendered_text)


def test_modern_character_crescendo_tab_shows_song_and_repertoire(monkeypatch):
    presenter = _make_presenter()
    screen = ModernCharacterScreen(presenter)
    player = _make_player()
    player.cls = SimpleNamespace(name="Troubadour", description="Masters songs.")
    player.bard_song = {"active": "Valor", "turns": 2, "encore": "Shelter"}
    player.bard_exploration_song = {"active": "Gold Trigger", "steps": 40, "effect": "loot_rate_up"}
    player.promotion_kit_state = promotion_kits.default_state()
    player.promotion_kit_state["bard_repertoire"]["Battle Hymn"] = {
        "known": True,
        "practice_xp": 18,
        "clean_finishes": 3,
    }
    player.promotion_kit_state["bard_repertoire"]["Chorus Time"] = {
        "known": False,
        "practice_xp": 9,
        "clean_finishes": 1,
    }
    promotion_kits.combat_state(player)["crescendo"] = 3
    _stub_character_screen_drawing(monkeypatch, screen)

    screen.select_tab("class")
    screen.draw_class_tab(player)

    rendered_text = _rendered_text(presenter)
    assert {
        "Crescendo",
        "3/3 Coda",
        "Combat Song",
        "Valor",
        "Exploration Song",
        "Gold Trigger",
        "Encore",
        "Shelter",
        "Advanced Repertoire",
        "Battle Hymn",
        "Mastered - Complete",
    }.issubset(rendered_text)
    assert {"Exploration Effect", "loot_rate_up", "Mastered - 18/18 XP - 3/3 clean"}.isdisjoint(
        rendered_text
    )
    assert "Promotion Tier" not in rendered_text


def test_modern_character_crescendo_tab_hides_troubadour_repertoire_for_bard(monkeypatch):
    presenter = _make_presenter()
    screen = ModernCharacterScreen(presenter)
    player = _make_player()
    player.cls = SimpleNamespace(name="Bard", description="Performs songs.")
    player.equipment["OffHand"] = items.Lute()
    player.bard_song = {"active": "Valor", "turns": 1, "encore": None}
    promotion_kits.combat_state(player)["crescendo"] = 1
    _stub_character_screen_drawing(monkeypatch, screen)

    screen.select_tab("class")
    screen.draw_class_tab(player)

    rendered_text = _rendered_text(presenter)
    assert {
        "Crescendo",
        "1/3 Coda",
        "Combat Song",
        "Valor",
        "Composition",
        "Instrument Match",
        "Battle Hymn",
        "C/Enter: choose song",
    }.issubset(rendered_text)
    assert {"Encore", "Mastered", "Advanced Repertoire", "Not visible"}.isdisjoint(rendered_text)


def test_modern_character_crescendo_tab_opens_inherent_composition(monkeypatch):
    presenter = _make_presenter()
    screen = ModernCharacterScreen(presenter)
    player = _make_player()
    player.cls = SimpleNamespace(name="Bard", description="Performs songs.")
    opened = []

    class FakePopup:
        def __init__(self, _presenter, _screen, title="Compose Song"):
            opened.append(title)

        def show(self, **kwargs):
            opened.append(kwargs["player_char"].cls.name)

    import src.ui_pygame.gui.modern_character_screen as modern_module

    monkeypatch.setattr(modern_module.mechanics, "CompositionPopupMenu", FakePopup)
    screen._open_composition_popup(player)

    assert opened == ["Compose Song", "Bard"]


def test_modern_character_forms_tab_shows_lycan_control(monkeypatch):
    presenter = _make_presenter()
    screen = ModernCharacterScreen(presenter)
    player = _make_player()
    player.cls = SimpleNamespace(name="Lycan", description="Changes shape.")
    player.transform_type = SimpleNamespace(name="Lycan")
    player.lycan_state = {
        "moon_phase": "Full",
        "moon_steps": 60,
        "frenzy_turns": 2,
        "dragon_essence": True,
    }
    player.promotion_kit_state = promotion_kits.default_state()
    player.promotion_kit_state["lycan_control"] = {
        "rank": "Tethered",
        "stress_events": 7,
        "dragon_essence": True,
        "rank_progress": {"full_moon": 2},
    }
    _stub_character_screen_drawing(monkeypatch, screen)

    screen.select_tab("class")
    screen.draw_class_tab(player)

    rendered_text = _rendered_text(presenter)
    assert {
        "Forms",
        "Current Form",
        "Humanoid",
        "Stored Form",
        "Lycan",
        "Moon Cycle",
        "60/120 Full",
        "Frenzy Lock",
        "2 turn(s)",
        "Control Rank",
        "Tethered",
        "Dragon Essence",
        "Yes",
    }.issubset(rendered_text)
    assert "Full_Moon Gate" not in rendered_text
    assert "Promotion Tier" not in rendered_text


def test_modern_character_forms_tab_hides_lycan_details_for_druid(monkeypatch):
    presenter = _make_presenter()
    screen = ModernCharacterScreen(presenter)
    player = _make_player()
    player.cls = SimpleNamespace(name="Druid", description="Changes shape.")
    player.transform_type = SimpleNamespace(name="Druid")
    _stub_character_screen_drawing(monkeypatch, screen)

    screen.select_tab("class")
    screen.draw_class_tab(player)

    rendered_text = _rendered_text(presenter)
    assert {"Forms", "Current Form", "Humanoid", "Stored Form", "Druid"}.issubset(rendered_text)
    assert {
        "Ring",
        "Moon Cycle",
        "Frenzy Lock",
        "Control Rank",
        "Dragon Essence",
        "Lycan only",
        "Not visible",
    }.isdisjoint(rendered_text)


def test_modern_character_aspects_tab_shows_attunement_and_harmony(monkeypatch):
    presenter = _make_presenter()
    screen = ModernCharacterScreen(presenter)
    player = _make_player()
    player.cls = SimpleNamespace(name="Archdruid", description="Balances nature.")
    player.archdruid_attunement = archdruid.default_state()
    player.archdruid_attunement["grove_unlocked"] = True
    player.archdruid_attunement["attunement"]["Venom"] = 75
    player.archdruid_attunement["aspects"]["Venom"] = True
    player.archdruid_attunement["catalysts"]["Venom"] = True
    player.archdruid_attunement["progress"]["Storm"]["storm_damage_dealt"] = 42
    promotion_kits.combat_state(player)["aspect_harmony"] = {"Venom", "Storm"}
    _stub_character_screen_drawing(monkeypatch, screen)

    screen.select_tab("class")
    screen.draw_class_tab(player)

    rendered_text = _rendered_text(presenter)
    assert {
        "Aspects",
        "Venom",
        "75/100 Awake, catalyst",
        "Grove",
        "Unlocked",
        "Aspect Harmony",
        "Storm, Venom",
        "Fourfold Surge",
        "Ready",
        "Catalyst Progress",
        "Stirring",
    }.issubset(rendered_text)
    assert {"Harmony Bonus", "storm_damage_dealt 42"}.isdisjoint(rendered_text)
    assert "Promotion Tier" not in rendered_text


def test_modern_character_class_mechanic_tabs_include_pathfinder_branches():
    presenter = _make_presenter()
    screen = ModernCharacterScreen(presenter)
    player = _make_player()

    for class_name, expected_tabs in (
        ("Druid", ["Character", "Equipment", "Forms"]),
        ("Lycan", ["Character", "Equipment", "Forms"]),
        ("Archdruid", ["Character", "Equipment", "Aspects"]),
        ("Diviner", ["Character", "Equipment", "Runes"]),
        ("Shaman", ["Character", "Equipment", "Totems"]),
        ("Ranger", ["Character", "Equipment", "Companion & Hunt"]),
    ):
        player.cls = SimpleNamespace(name=class_name)
        player.summons = {}
        player.familiar = None
        assert [tab.label for tab in screen.visible_tabs(player)] == [
            *expected_tabs,
            "Progression",
        ]


def test_modern_character_class_mechanic_tabs_include_warrior_branches():
    presenter = _make_presenter()
    screen = ModernCharacterScreen(presenter)
    player = _make_player()

    for class_name, expected_tabs in (
        ("Paladin", ["Character", "Equipment", "Oath Conviction"]),
        ("Crusader", ["Character", "Equipment", "Oath Conviction"]),
        ("Lancer", ["Character", "Equipment", "Aerial Tempo"]),
        ("Dragoon", ["Character", "Equipment", "Aerial Tempo"]),
        ("Sentinel", ["Character", "Equipment", "Resolve"]),
        ("Stalwart Defender", ["Character", "Equipment", "Resolve"]),
    ):
        player.cls = SimpleNamespace(name=class_name)
        player.summons = {}
        player.familiar = None
        assert [tab.label for tab in screen.visible_tabs(player)] == [
            *expected_tabs,
            "Progression",
        ]


def test_modern_character_class_mechanic_tabs_include_mage_branches():
    presenter = _make_presenter()
    screen = ModernCharacterScreen(presenter)
    player = _make_player()
    familiar = SimpleNamespace(name="Aster", is_alive=lambda: True)

    for class_name, expected_tabs, has_familiar in (
        ("Sorcerer", ["Character", "Equipment", "School Affinity"], False),
        ("Wizard", ["Character", "Equipment", "School Affinity"], False),
        ("Warlock", ["Character", "Equipment", "Familiar"], True),
        ("Shadowcaster", ["Character", "Equipment"], True),
        ("Demonologist", ["Character", "Equipment", "Contracts"], True),
        ("Spellblade", ["Character", "Equipment"], False),
        ("Knight Enchanter", ["Character", "Equipment"], False),
        ("Conjurer", ["Character", "Equipment"], False),
        ("Thaumaturgist", ["Character", "Equipment", "Xenids"], False),
    ):
        player.cls = SimpleNamespace(name=class_name)
        player.summons = {}
        player.familiar = familiar if has_familiar else None
        assert [tab.label for tab in screen.visible_tabs(player)] == [
            *expected_tabs,
            "Progression",
        ]


def test_modern_character_class_mechanic_tabs_include_footpad_branches():
    presenter = _make_presenter()
    screen = ModernCharacterScreen(presenter)
    player = _make_player()

    for class_name, expected_tabs in (
        ("Thief", ["Character", "Equipment"]),
        ("Rogue", ["Character", "Equipment"]),
        ("Inquisitor", ["Character", "Equipment", "Case Journal"]),
        ("Seeker", ["Character", "Equipment", "Case Journal"]),
        ("Assassin", ["Character", "Equipment"]),
        ("Ninja", ["Character", "Equipment"]),
        ("Spell Stealer", ["Character", "Equipment"]),
        ("Arcane Trickster", ["Character", "Equipment"]),
    ):
        player.cls = SimpleNamespace(name=class_name)
        player.summons = {}
        player.familiar = None
        assert [tab.label for tab in screen.visible_tabs(player)] == [
            *expected_tabs,
            "Progression",
        ]


def test_modern_character_class_mechanic_tabs_include_healer_branches():
    presenter = _make_presenter()
    screen = ModernCharacterScreen(presenter)
    player = _make_player()

    for class_name, expected_tabs in (
        ("Cleric", ["Character", "Equipment"]),
        ("Templar", ["Character", "Equipment"]),
        ("Hierophant", ["Character", "Equipment"]),
        ("Monk", ["Character", "Equipment"]),
        ("Master Monk", ["Character", "Equipment"]),
        ("Priest", ["Character", "Equipment"]),
        ("Archbishop", ["Character", "Equipment"]),
        ("Bard", ["Character", "Equipment", "Crescendo"]),
        ("Troubadour", ["Character", "Equipment", "Crescendo"]),
    ):
        player.cls = SimpleNamespace(name=class_name)
        player.summons = {}
        player.familiar = None
        assert [tab.label for tab in screen.visible_tabs(player)] == [
            *expected_tabs,
            "Progression",
        ]


def test_modern_character_class_tab_supports_multiple_summon_tiles_and_popup(monkeypatch):
    presenter = _make_presenter()
    screen = ModernCharacterScreen(presenter)
    player = _make_player()

    def summon(name):
        return SimpleNamespace(
            name=name,
            cls=None,
            health=SimpleNamespace(current=40, max=50),
            mana=SimpleNamespace(current=5, max=10),
            combat=SimpleNamespace(attack=14, defense=8, magic=0, magic_def=3),
            level=SimpleNamespace(level=1, exp=25, exp_to_gain=75),
            spellbook={"Skills": {"Throw Rock": object()}, "Spells": {}},
            is_alive=lambda: True,
        )

    player.cls = SimpleNamespace(
        name="Thaumaturgist", description="Calls Xenids from distant realms. " * 12
    )
    player.promotion_kit_state = {"summon_bonds": {"Patagon": 15, "Dilong": 0, "Agloolik": 0}}
    player.summons = {
        "Patagon": summon("Patagon"),
        "Dilong": summon("Dilong"),
        "Agloolik": summon("Agloolik"),
    }
    screen.companion_art_manager = SimpleNamespace(
        get_scaled_sprite=lambda _entity, size: DummySurface(size)
    )
    popups = []

    class FakeCompanionPopup:
        def __init__(self, _presenter, _screen, _player, kind, companion):
            self.kind = kind
            self.companion = companion
            self.show_kwargs = None
            popups.append(self)

        def show(self, **kwargs):
            self.show_kwargs = kwargs
            return None

    import src.ui_pygame.gui.modern_character_screen as modern_module

    monkeypatch.setattr(modern_module.layout, "ClassCompanionDetailsPopup", FakeCompanionPopup)
    monkeypatch.setattr(
        screen,
        "draw_semi_transparent_panel",
        lambda rect, alpha=180: DummySurface((rect.width, rect.height)),
    )
    monkeypatch.setattr(
        "src.ui_pygame.gui.modern_character_screen.pygame.draw.rect", lambda *_args, **_kwargs: None
    )
    monkeypatch.setattr(
        "src.ui_pygame.gui.modern_character_screen.pygame.draw.line", lambda *_args, **_kwargs: None
    )

    screen.draw_class_tab(player)

    assert len(screen.class_companion_tile_rects(screen.class_companion_entries(player))) == 3
    rendered_text = set(presenter.small_font.render_calls + presenter.normal_font.render_calls)
    assert {"Patagon", "Dilong", "Agloolik", "XP", "25/100 XP", "Bond", "15/100"}.issubset(
        rendered_text
    )
    assert "Calls allies from distant realms." not in rendered_text

    screen.selected_class_companion_index = 1
    screen._open_class_companion_popup(player)

    assert popups
    assert popups[-1].kind == "Xenid"
    assert popups[-1].companion is player.summons["Dilong"]
    assert callable(popups[-1].show_kwargs["background_draw_func"])


def test_modern_character_class_tab_stacks_all_eleven_summons(monkeypatch):
    presenter = _make_presenter()
    screen = ModernCharacterScreen(presenter)
    player = _make_player()
    summon_names = [
        "Patagon",
        "Dilong",
        "Agloolik",
        "Cacus",
        "Fuath",
        "Izulu",
        "Hala",
        "Seraphim",
        "Bardi",
        "Kobalos",
        "Zahhak",
    ]

    def summon(name):
        return SimpleNamespace(
            name=name,
            cls=None,
            health=SimpleNamespace(current=40, max=50),
            mana=SimpleNamespace(current=5, max=10),
            combat=SimpleNamespace(attack=14, defense=8, magic=0, magic_def=3),
            level=SimpleNamespace(level=1, exp=25, exp_to_gain=75),
            spellbook={"Skills": {}, "Spells": {}},
            is_alive=lambda: True,
        )

    player.cls = SimpleNamespace(name="Thaumaturgist", description="Calls every Xenid.")
    player.promotion_kit_state = {"summon_bonds": {name: 0 for name in summon_names}}
    player.summons = {name: summon(name) for name in summon_names}

    monkeypatch.setattr(
        screen,
        "draw_semi_transparent_panel",
        lambda rect, alpha=180: DummySurface((rect.width, rect.height)),
    )
    monkeypatch.setattr(
        "src.ui_pygame.gui.modern_character_screen.pygame.draw.rect", lambda *_args, **_kwargs: None
    )
    monkeypatch.setattr(
        "src.ui_pygame.gui.modern_character_screen.pygame.draw.line", lambda *_args, **_kwargs: None
    )

    screen.draw_class_tab(player)
    rects = screen.class_companion_tile_rects(screen.class_companion_entries(player))

    assert len(rects) == 11
    assert all(rect.left == rects[0].left and rect.width == rects[0].width for rect in rects)
    assert all(rects[index].bottom < rects[index + 1].top for index in range(len(rects) - 1))
    assert rects[-1].bottom <= screen._class_roster_rect.bottom


def test_class_companion_details_popup_uses_character_tab_style_and_art(monkeypatch):
    presenter = _make_presenter()
    screen = ModernCharacterScreen(presenter)
    player = _make_player()
    companion = SimpleNamespace(
        name="Patagon",
        cls=None,
        health=SimpleNamespace(current=40, max=50),
        mana=SimpleNamespace(current=5, max=10),
        stats=SimpleNamespace(strength=20, intel=5, wisdom=8, con=15, charisma=3, dex=14),
        combat=SimpleNamespace(attack=14.9, defense=8.2, magic=0.8, magic_def=3.4),
        resistance={"Fire": -0.25, "Physical": 0.2},
        level=SimpleNamespace(level=1, exp=25, exp_to_gain=75),
        spellbook={"Skills": {"Throw Rock": object(), "Charge": object()}, "Spells": {}},
        is_alive=lambda: True,
    )
    player.promotion_kit_state = {"summon_bonds": {"Patagon": 15}}
    calls = []
    screen.companion_art_manager = SimpleNamespace(
        get_scaled_sprite=lambda entity, size: calls.append((entity, size)) or DummySurface(size)
    )

    monkeypatch.setattr(
        screen,
        "draw_semi_transparent_panel",
        lambda rect, alpha=180: DummySurface((rect.width, rect.height)),
    )
    monkeypatch.setattr(
        "src.ui_pygame.gui.modern_character_screen.pygame.draw.rect", lambda *_args, **_kwargs: None
    )
    monkeypatch.setattr(
        "src.ui_pygame.gui.modern_character_screen.pygame.draw.line", lambda *_args, **_kwargs: None
    )
    monkeypatch.setattr(
        "src.ui_pygame.gui.modern_character_screen.draw_popup_close_button",
        lambda *_args, **_kwargs: pygame.Rect(0, 0, 20, 20),
    )
    monkeypatch.setattr(
        "src.ui_pygame.gui.modern_character_screen.pygame.display.flip", lambda: None
    )

    popup = ClassCompanionDetailsPopup(presenter, screen, player, "Summon", companion)
    popup.draw("background")

    assert calls and calls[0][0] is companion
    rendered_text = set(
        presenter.title_font.render_calls
        + presenter.large_font.render_calls
        + presenter.normal_font.render_calls
        + presenter.small_font.render_calls
    )
    assert {
        "Patagon Details",
        "Summon",
        "Core Attributes",
        "Combat Stats",
        "Abilities",
        "Throw Rock, Charge",
        "Weaknesses",
        "Resistances",
        "Fire (-25%)",
        "Physical (+20%)",
        "15/100",
        "14",
        "8",
        "0",
        "3",
    }.issubset(rendered_text)
    assert "14.9" not in rendered_text
    assert "8.2" not in rendered_text


def test_tamed_companion_details_popup_uses_flavor_instead_of_stats(monkeypatch):
    presenter = _make_presenter()
    screen = ModernCharacterScreen(presenter)
    player = _make_player()
    companion = SimpleNamespace(
        name="Needle (Giant Hornet)",
        race="Needle (Giant Hornet)",
        enemy_class="GiantHornet",
        spec="Tamed",
        evolution="Stingwing",
        special_ability="Wingbeat",
        health=SimpleNamespace(current=6, max=6),
        mana=SimpleNamespace(current=0, max=0),
        stats=SimpleNamespace(strength=9, intel=1, wisdom=1, con=5, charisma=1, dex=12),
        combat=SimpleNamespace(attack=8, defense=4, magic=1, magic_def=1),
        resistance={},
        spellbook={"Skills": {}, "Spells": {}},
        inspect=lambda: "Needle (Giant Hornet) is a Stingwing tamed companion with Wingbeat.",
        is_alive=lambda: True,
    )
    calls = []
    screen.companion_art_manager = SimpleNamespace(
        get_scaled_sprite=lambda entity, size: calls.append((entity, size)) or DummySurface(size)
    )

    monkeypatch.setattr(
        screen,
        "draw_semi_transparent_panel",
        lambda rect, alpha=180: DummySurface((rect.width, rect.height)),
    )
    monkeypatch.setattr(
        "src.ui_pygame.gui.modern_character_screen.pygame.draw.rect", lambda *_args, **_kwargs: None
    )
    monkeypatch.setattr(
        "src.ui_pygame.gui.modern_character_screen.pygame.draw.line", lambda *_args, **_kwargs: None
    )
    monkeypatch.setattr(
        "src.ui_pygame.gui.modern_character_screen.draw_popup_close_button",
        lambda *_args, **_kwargs: pygame.Rect(0, 0, 20, 20),
    )
    monkeypatch.setattr(
        "src.ui_pygame.gui.modern_character_screen.pygame.display.flip", lambda: None
    )

    popup = ClassCompanionDetailsPopup(presenter, screen, player, "Companion", companion)
    popup.draw("background")

    assert calls and calls[0][0] is companion
    rendered_text = set(
        presenter.title_font.render_calls
        + presenter.large_font.render_calls
        + presenter.normal_font.render_calls
        + presenter.small_font.render_calls
    )
    assert {
        "Needle (Giant Hornet) Details",
        "Bond & Form",
        "Companion Notes",
        "Stingwing",
        "Wingbeat",
        "The animal acts through bond and instinct rather than a",
        "visible resource pool.",
    }.issubset(rendered_text)
    assert {"Core Attributes", "Combat Stats", "HP", "MP", "Strength", "Attack"}.isdisjoint(
        rendered_text
    )


def test_modern_character_draw_all_renders_active_tabs(monkeypatch):
    presenter = _make_presenter()
    screen = ModernCharacterScreen(presenter)
    player = _make_player()

    monkeypatch.setattr(
        screen,
        "draw_semi_transparent_panel",
        lambda rect, alpha=180: DummySurface((rect.width, rect.height)),
    )
    draw_rect_calls = []
    monkeypatch.setattr(
        "src.ui_pygame.gui.modern_character_screen.pygame.draw.rect",
        lambda *_args, **_kwargs: draw_rect_calls.append((_args, _kwargs)),
    )
    draw_line_calls = []
    monkeypatch.setattr(
        "src.ui_pygame.gui.modern_character_screen.pygame.draw.line",
        lambda *_args, **_kwargs: draw_line_calls.append((_args, _kwargs)),
    )
    flip_calls = []
    monkeypatch.setattr(
        "src.ui_pygame.gui.modern_character_screen.pygame.display.flip",
        lambda: flip_calls.append(True),
    )
    loaded_renders = []
    screen.item_render_manager = SimpleNamespace(
        get_scaled_render=lambda item, size: loaded_renders.append(
            (getattr(item, "name", ""), size)
        )
        or pygame.Surface(size, pygame.SRCALPHA)
    )

    screen.draw_all(player)
    rendered_text = set(
        presenter.large_font.render_calls
        + presenter.normal_font.render_calls
        + presenter.small_font.render_calls
    )
    assert "Character" in presenter.large_font.render_calls
    assert "Combat Stats" in presenter.large_font.render_calls
    assert "Core Attributes" in presenter.large_font.render_calls
    assert "Strength" in rendered_text
    assert "RACE" in presenter.normal_font.render_calls
    assert "CLASS" in presenter.normal_font.render_calls
    assert "Human" in presenter.large_font.render_calls
    assert "Warrior" in presenter.large_font.render_calls
    assert "HP" in rendered_text
    assert "Weaknesses" in presenter.large_font.render_calls
    assert "Resistances" in presenter.large_font.render_calls
    assert "Fire (-15%)" in rendered_text
    assert "Equipment" not in presenter.large_font.render_calls
    assert "XP EARNED" not in presenter.small_font.render_calls
    assert "XP TO NEXT" not in presenter.small_font.render_calls
    assert "250/300 XP (50 next)" in presenter.small_font.render_calls
    assert len(draw_line_calls) >= 2
    assert flip_calls

    screen.select_tab("class")
    screen.draw_all(player, do_flip=False)
    assert screen.active_tab.key == "character"
    assert "Class Profile" not in presenter.normal_font.render_calls
    assert "Companions & Summons" not in presenter.normal_font.render_calls

    screen.select_tab("equipment")
    screen.draw_all(player, do_flip=False)
    assert "Equipment" in presenter.large_font.render_calls
    assert "E: Select gear" in presenter.small_font.render_calls
    screen.equipment_selector_active = True
    screen.draw_all(player, do_flip=False)
    assert "Arrows: Select gear  Enter: Change  E/Esc: Back" in presenter.small_font.render_calls
    assert "Equipment Layout" not in presenter.large_font.render_calls
    assert "Item Details" not in presenter.normal_font.render_calls
    assert "Equipment Buffs" not in presenter.normal_font.render_calls
    assert {"Helmet", "Weapon", "Armor", "OffHand", "Ring", "Pendant"}.issubset(
        set(presenter.normal_font.render_calls)
    )
    assert "Sword (1H)" in presenter.normal_font.render_calls
    assert "Type:" in presenter.small_font.render_calls
    assert "Sword" in presenter.small_font.render_calls
    assert "Base Damage:" in presenter.small_font.render_calls
    assert "12" in presenter.small_font.render_calls
    assert "Crit:" in presenter.small_font.render_calls
    assert any(name == "Sword" for name, _size in loaded_renders)
    assert any(name == "Mail" for name, _size in loaded_renders)
    assert any(name == "Iron Helm" for name, _size in loaded_renders)
    assert "15%" in presenter.small_font.render_calls
    assert "Medium" in presenter.small_font.render_calls
    assert "Base Armor:" in presenter.small_font.render_calls
    assert "8" in presenter.small_font.render_calls
    assert "Weight:" not in presenter.small_font.render_calls
    assert "Mod Block" not in presenter.small_font.render_calls
    assert "Buff: Block" in presenter.small_font.render_calls
    assert "Buff: Vision" in presenter.small_font.render_calls
    assert any(name == "Ruby Ring" for name, _size in loaded_renders)
    assert any(name == "Pendant of Sight" for name, _size in loaded_renders)


def test_modern_character_menu_renders_with_and_without_portrait_assets(monkeypatch):
    presenter = _make_presenter()
    screen = ModernCharacterScreen(presenter)
    player = _make_player()
    monkeypatch.setattr(
        screen,
        "draw_semi_transparent_panel",
        lambda rect, alpha=180: DummySurface((rect.width, rect.height)),
    )
    monkeypatch.setattr(
        "src.ui_pygame.gui.modern_character_screen.pygame.draw.rect", lambda *_args, **_kwargs: None
    )
    monkeypatch.setattr(
        "src.ui_pygame.gui.modern_character_screen.pygame.draw.line", lambda *_args, **_kwargs: None
    )
    monkeypatch.setattr(
        "src.ui_pygame.gui.modern_character_screen.pygame.display.flip", lambda: None
    )

    screen.load_portrait = lambda _player: pygame.Surface((225, 400), pygame.SRCALPHA)
    screen.draw_all(player)
    assert presenter.screen.blit_calls
    assert "Gold" in presenter.small_font.render_calls
    assert "321G" in presenter.small_font.render_calls
    assert "Location" in presenter.small_font.render_calls
    assert "Town" in presenter.small_font.render_calls
    gold_label_x = next(
        position[0]
        for surface, position in presenter.screen.blit_calls
        if getattr(surface, "text", None) == "Gold"
    )
    gold_value_x = next(
        position[0]
        for surface, position in presenter.screen.blit_calls
        if getattr(surface, "text", None) == "321G"
    )
    assert gold_value_x > gold_label_x

    atlas_surface = pygame.Surface((225, 400), pygame.SRCALPHA)
    frame = screen.portrait_frame_rect(screen.character_panel_rect.top + 52, atlas_surface)
    assert frame.size == (225, 400)

    presenter.small_font.render_calls.clear()
    screen.load_portrait = lambda _player: None
    screen.draw_all(player)
    assert "Portrait" in presenter.small_font.render_calls


def test_modern_character_resistance_columns_render_all_possible_entries(monkeypatch):
    presenter = _make_presenter()
    screen = ModernCharacterScreen(presenter)
    player = _make_player()
    player.resistance = {name: -0.1 for name in RESISTANCE_ORDER}

    monkeypatch.setattr(
        screen,
        "draw_semi_transparent_panel",
        lambda rect, alpha=180: DummySurface((rect.width, rect.height)),
    )
    monkeypatch.setattr(
        "src.ui_pygame.gui.modern_character_screen.pygame.draw.rect", lambda *_args, **_kwargs: None
    )
    monkeypatch.setattr(
        "src.ui_pygame.gui.modern_character_screen.pygame.draw.line", lambda *_args, **_kwargs: None
    )
    monkeypatch.setattr(
        "src.ui_pygame.gui.modern_character_screen.pygame.display.flip", lambda: None
    )

    screen.draw_all(player)
    rendered_text = set(presenter.normal_font.render_calls + presenter.small_font.render_calls)
    for name in RESISTANCE_ORDER:
        assert f"{name} (-10%)" in rendered_text


def test_modern_character_navigation_switches_tabs_and_exits(monkeypatch):
    presenter = _make_presenter()
    screen = ModernCharacterScreen(presenter)
    player = _make_player()

    event_batches = iter(
        [
            [pygame.event.Event(pygame.KEYDOWN, key=pygame.K_2)],
            [pygame.event.Event(pygame.KEYDOWN, key=pygame.K_3)],
            [pygame.event.Event(pygame.KEYDOWN, key=pygame.K_ESCAPE)],
        ]
    )
    monkeypatch.setattr(screen, "draw_all", lambda *_args, **_kwargs: None)
    monkeypatch.setattr("src.ui_pygame.gui.input_guards.pygame.key.get_pressed", lambda: [])
    monkeypatch.setattr(
        "src.ui_pygame.gui.modern_character_screen.pygame.event.get",
        lambda: next(event_batches, []),
    )

    assert screen.navigate(player) == "Exit Menu"
    assert screen.active_tab.key == "progression"


def test_progression_tree_requires_shortcut_before_arrow_navigation(monkeypatch):
    presenter = _make_presenter()
    screen = ModernCharacterScreen(presenter)
    player = _make_player()
    screen.select_tab("progression")
    screen.current_selection = 0
    handled_keys = []
    original_handle_event = screen.progression_view.handle_event

    def record_progression_event(event):
        handled_keys.append(event.key)
        return original_handle_event(event)

    monkeypatch.setattr(
        screen.progression_view,
        "handle_event",
        record_progression_event,
    )
    monkeypatch.setattr(screen, "draw_all", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(
        "src.ui_pygame.gui.input_guards.pygame.key.get_pressed",
        lambda: [],
    )
    event_batches = iter(
        [
            [pygame.event.Event(pygame.KEYDOWN, key=pygame.K_DOWN)],
            [pygame.event.Event(pygame.KEYDOWN, key=pygame.K_p)],
            [pygame.event.Event(pygame.KEYDOWN, key=pygame.K_RIGHT)],
            [pygame.event.Event(pygame.KEYDOWN, key=pygame.K_LEFT)],
            [pygame.event.Event(pygame.KEYDOWN, key=pygame.K_DOWN)],
            [pygame.event.Event(pygame.KEYDOWN, key=pygame.K_p)],
            [pygame.event.Event(pygame.KEYDOWN, key=pygame.K_ESCAPE)],
        ]
    )
    monkeypatch.setattr(
        "src.ui_pygame.gui.modern_character_screen.pygame.event.get",
        lambda: next(event_batches, []),
    )

    assert screen.navigate(player) == "Exit Menu"
    assert screen.current_selection == 1
    assert handled_keys == [
        pygame.K_RIGHT,
        pygame.K_LEFT,
        pygame.K_DOWN,
    ]
    assert screen.progression_selector_active is False


def test_modern_equipment_selector_requires_explicit_toggle(monkeypatch):
    presenter = _make_presenter()
    screen = ModernCharacterScreen(presenter)
    player = _make_player()

    event_batches = iter(
        [
            [pygame.event.Event(pygame.KEYDOWN, key=pygame.K_2)],
            [pygame.event.Event(pygame.KEYDOWN, key=pygame.K_RIGHT)],
            [pygame.event.Event(pygame.KEYDOWN, key=pygame.K_2)],
            [pygame.event.Event(pygame.KEYDOWN, key=pygame.K_e)],
            [pygame.event.Event(pygame.KEYDOWN, key=pygame.K_RIGHT)],
            [pygame.event.Event(pygame.KEYDOWN, key=pygame.K_ESCAPE)],
            [pygame.event.Event(pygame.KEYDOWN, key=pygame.K_ESCAPE)],
        ]
    )
    monkeypatch.setattr(screen, "draw_all", lambda *_args, **_kwargs: None)
    monkeypatch.setattr("src.ui_pygame.gui.input_guards.pygame.key.get_pressed", lambda: [])
    monkeypatch.setattr(
        "src.ui_pygame.gui.modern_character_screen.pygame.event.get",
        lambda: next(event_batches, []),
    )

    assert screen.navigate(player) == "Exit Menu"
    assert screen.active_tab.key == "equipment"
    assert screen.selected_equipment_slot(player) == "Armor"
    assert screen.equipment_selector_active is False


def test_modern_equipment_tab_enter_opens_selected_slot_change(monkeypatch):
    presenter = _make_presenter()
    screen = ModernCharacterScreen(presenter)
    player = _make_player()
    screen.select_tab("equipment")
    screen.set_selected_equipment_slot(player, "Ring")

    opened = []

    class FakeEquipmentPopup:
        def __init__(self, _presenter, _parent):
            self.items = []
            self.selected_index = 0

        def build_items(self, _player):
            self.items = [("Weapon", object()), ("Ring", object())]

        def on_select(self, _player, item):
            opened.append(item[0])

    import src.ui_pygame.gui.modern_character_screen as modern_module

    monkeypatch.setattr(modern_module.equipment, "EquipmentPopupMenu", FakeEquipmentPopup)

    screen.open_selected_equipment_change(player)

    assert opened == ["Ring"]


def test_modern_character_c_toggles_class_summon_focus_and_opens_popup(monkeypatch):
    presenter = _make_presenter()
    screen = ModernCharacterScreen(presenter)
    player = _make_player()

    def summon(name):
        return SimpleNamespace(
            name=name,
            cls=None,
            health=SimpleNamespace(current=40, max=50),
            mana=SimpleNamespace(current=5, max=10),
            combat=SimpleNamespace(attack=14, defense=8, magic=0, magic_def=3),
            level=SimpleNamespace(level=1, exp=0, exp_to_gain=100),
            spellbook={"Skills": {}, "Spells": {}},
            is_alive=lambda: True,
        )

    player.cls = SimpleNamespace(name="Thaumaturgist", description="")
    player.summons = {"Patagon": summon("Patagon"), "Dilong": summon("Dilong")}
    opened = []

    class FakeCompanionPopup:
        def __init__(self, _presenter, _screen, _player, kind, companion):
            opened.append((kind, companion.name))

        def show(self, **_kwargs):
            return None

    import src.ui_pygame.gui.modern_character_screen as modern_module

    monkeypatch.setattr(modern_module.layout, "ClassCompanionDetailsPopup", FakeCompanionPopup)
    monkeypatch.setattr(screen, "draw_all", lambda *_args, **_kwargs: None)
    monkeypatch.setattr("src.ui_pygame.gui.input_guards.pygame.key.get_pressed", lambda: [])
    event_batches = iter(
        [
            [pygame.event.Event(pygame.KEYDOWN, key=pygame.K_c)],
            [pygame.event.Event(pygame.KEYDOWN, key=pygame.K_3)],
            [pygame.event.Event(pygame.KEYDOWN, key=pygame.K_c)],
            [pygame.event.Event(pygame.KEYDOWN, key=pygame.K_DOWN)],
            [pygame.event.Event(pygame.KEYDOWN, key=pygame.K_RETURN)],
            [pygame.event.Event(pygame.KEYDOWN, key=pygame.K_ESCAPE)],
            [pygame.event.Event(pygame.KEYDOWN, key=pygame.K_ESCAPE)],
        ]
    )
    monkeypatch.setattr(
        "src.ui_pygame.gui.modern_character_screen.pygame.event.get",
        lambda: next(event_batches, []),
    )

    assert screen.navigate(player) == "Exit Menu"
    assert screen.active_tab.key == "class"
    assert opened == [("Xenid", "Dilong")]
    assert screen.class_companion_selector_active is False


def test_modern_character_menu_mouse_selects_equipment_slot(monkeypatch):
    presenter = _make_presenter()
    screen = ModernCharacterScreen(presenter)
    player = _make_player()
    screen.select_tab("equipment")
    opened = []

    monkeypatch.setattr(screen, "draw_all", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(
        screen,
        "open_selected_equipment_change",
        lambda _player: opened.append(screen.selected_equipment_slot(_player)),
    )
    monkeypatch.setattr("src.ui_pygame.gui.input_guards.pygame.key.get_pressed", lambda: [])

    click_pos = screen.equipment_slot_rects()["Ring"].center
    event_batches = iter(
        [
            [SimpleNamespace(type=pygame.MOUSEBUTTONDOWN, button=1, pos=click_pos)],
            [SimpleNamespace(type=pygame.KEYDOWN, key=pygame.K_ESCAPE)],
            [SimpleNamespace(type=pygame.KEYDOWN, key=pygame.K_ESCAPE)],
        ]
    )
    monkeypatch.setattr(
        "src.ui_pygame.gui.modern_character_screen.pygame.event.get",
        lambda: next(event_batches, []),
    )

    assert screen.navigate(player) == "Exit Menu"
    assert screen.equipment_selector_active is False
    assert screen.selected_equipment_slot(player) == "Ring"
    assert opened == ["Ring"]


def test_modern_character_menu_mouse_tabs_and_actions(monkeypatch):
    presenter = _make_presenter()
    screen = ModernCharacterScreen(presenter)
    player = _make_player()
    monkeypatch.setattr(screen, "draw_all", lambda *_args, **_kwargs: None)
    monkeypatch.setattr("src.ui_pygame.gui.input_guards.pygame.key.get_pressed", lambda: [])

    equipment_tab_pos = screen.tab_button_rects(player)[1].center
    exit_pos = screen.action_rects()[-1].center
    event_batches = iter(
        [
            [SimpleNamespace(type=pygame.MOUSEBUTTONDOWN, button=1, pos=equipment_tab_pos)],
            [SimpleNamespace(type=pygame.MOUSEBUTTONDOWN, button=1, pos=exit_pos)],
        ]
    )
    monkeypatch.setattr(
        "src.ui_pygame.gui.modern_character_screen.pygame.event.get",
        lambda: next(event_batches, []),
    )

    assert screen.navigate(player) == "Exit Menu"
    assert screen.active_tab.key == "equipment"


def test_modern_character_menu_actions_remove_quit_and_put_exit_last(monkeypatch):
    presenter = _make_presenter()
    screen = ModernCharacterScreen(presenter)
    player = _make_player()

    event_batches = iter([[pygame.event.Event(pygame.KEYDOWN, key=pygame.K_ESCAPE)]])
    monkeypatch.setattr(screen, "draw_all", lambda *_args, **_kwargs: None)
    monkeypatch.setattr("src.ui_pygame.gui.input_guards.pygame.key.get_pressed", lambda: [])
    monkeypatch.setattr(
        "src.ui_pygame.gui.modern_character_screen.pygame.event.get",
        lambda: next(event_batches, []),
    )

    assert screen.navigate(player) == "Exit Menu"
    assert screen.menu_options == [
        "Inventory",
        "Quests",
        "Key Items",
        "Bestiary",
        "Abilities",
        "Action Layout",
        "Exit Menu",
    ]
    assert "Change Equipment" not in screen.menu_options
    assert "Quit Game" not in screen.menu_options


def test_abilities_workspace_splits_icons_and_accepts_drag_to_shortcut(monkeypatch):
    presenter = _make_presenter()
    screen = ModernCharacterScreen(presenter)
    player = _make_player()
    player.action_bar_autofill_complete = True
    player.action_bar_assignments = (None,) * 6
    player.spellbook = {
        "Skills": {
            "Cleave": SimpleNamespace(
                ability_id="warrior.cleave",
                passive=False,
                exploration_cast=False,
                resource_type="",
                cost=0,
                description="Sweep the front rank.",
                is_available=lambda _player, _target=None: True,
            )
        },
        "Spells": {
            "Spark": SimpleNamespace(
                ability_id="mage.spark",
                passive=False,
                exploration_cast=False,
                resource_type="",
                cost=2,
                description="A small arc of lightning.",
                is_available=lambda _player, _target=None: True,
            )
        },
    }
    monkeypatch.setattr(screen, "draw_all", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(screen, "draw_semi_transparent_panel", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(
        "src.ui_pygame.gui.modern_character_screen.pygame.draw.rect",
        lambda *_args, **_kwargs: None,
    )
    monkeypatch.setattr("src.ui_pygame.gui.input_guards.pygame.key.get_pressed", lambda: [])
    monkeypatch.setattr(
        "src.ui_pygame.gui.modern_character_screen.equipment.get_ability_icon_manager",
        lambda: SimpleNamespace(get_icon=lambda _key: pygame.Surface((32, 32))),
    )
    monkeypatch.setattr(
        "src.ui_pygame.gui.modern_character_screen.pygame.display.flip", lambda: None
    )

    panel = screen.content_rect.inflate(-48, -48)
    catalog_rect = pygame.Rect(
        panel.left + 18,
        panel.top + 80,
        panel.width - 36,
        panel.height - 220,
    )
    skill_card_center = (
        catalog_rect.left + (catalog_rect.width - 14) // 4,
        catalog_rect.top + 32 + 22,
    )
    slot_width = max(72, (panel.width - 48) // 6)
    slot_center = (
        panel.left + 18 + slot_width // 2,
        panel.bottom - 116 + 44,
    )
    event_batches = iter(
        [
            [
                pygame.event.Event(
                    pygame.MOUSEBUTTONDOWN,
                    button=1,
                    pos=skill_card_center,
                ),
                pygame.event.Event(
                    pygame.MOUSEBUTTONUP,
                    button=1,
                    pos=slot_center,
                ),
                pygame.event.Event(
                    pygame.MOUSEBUTTONDOWN,
                    button=1,
                    pos=(panel.right - 20, panel.top + 18),
                ),
            ]
        ]
    )
    monkeypatch.setattr(
        "src.ui_pygame.gui.modern_character_screen.pygame.event.get",
        lambda: next(event_batches, []),
    )

    screen._edit_action_layout(player)

    assert player.action_bar_assignments[0].action_id == "warrior.cleave"
    assert {"Skills", "Spells"}.issubset(_rendered_text(presenter))


def test_modern_character_aerial_tempo_tab_toggles_jump_mods_inline(monkeypatch):
    presenter = _make_presenter()
    screen = ModernCharacterScreen(presenter)
    player = _make_player()
    player.cls = SimpleNamespace(name="Lancer")
    jump_skill = FakeJumpSkill()
    player.spellbook["Skills"]["Jump"] = jump_skill
    screen.select_tab("class")

    event_batches = iter(
        [
            [pygame.event.Event(pygame.KEYDOWN, key=pygame.K_DOWN)],
            [pygame.event.Event(pygame.KEYDOWN, key=pygame.K_RETURN)],
            [pygame.event.Event(pygame.KEYDOWN, key=pygame.K_ESCAPE)],
        ]
    )
    monkeypatch.setattr(screen, "draw_all", lambda *_args, **_kwargs: None)
    monkeypatch.setattr("src.ui_pygame.gui.input_guards.pygame.key.get_pressed", lambda: [])
    monkeypatch.setattr(
        "src.ui_pygame.gui.modern_character_screen.pygame.event.get",
        lambda: next(event_batches, []),
    )

    assert screen.navigate(player) == "Exit Menu"
    assert "Jump Mods" not in screen.menu_options
    assert screen.selected_jump_mod_index == 1
    assert jump_skill.modifications["Recover"] is True


def test_modern_character_menu_opens_bestiary(monkeypatch):
    presenter = _make_presenter()
    screen = ModernCharacterScreen(presenter)
    player = _make_player()
    opened = []

    class FakeBestiaryPopup:
        def __init__(self, _presenter, _parent):
            opened.append("created")

        def show(self, _player, **kwargs):
            opened.append((kwargs.get("flush_events"), kwargs.get("require_key_release")))

    import src.ui_pygame.gui.modern_character_screen as modern_module

    monkeypatch.setattr(modern_module.equipment, "BestiaryPopupMenu", FakeBestiaryPopup)

    assert screen._open_menu_choice("Bestiary", player) is None
    assert opened == ["created", (True, True)]


def test_modern_character_menu_opens_quest_popup(monkeypatch):
    presenter = _make_presenter()
    screen = ModernCharacterScreen(presenter)
    player = _make_player()
    opened = []

    class FakeQuestPopup:
        def __init__(self, _presenter, _parent):
            opened.append("created")

        def show(self, _player, **kwargs):
            opened.append((kwargs.get("flush_events"), kwargs.get("require_key_release")))

    import src.ui_pygame.gui.modern_character_screen as modern_module

    monkeypatch.setattr(modern_module.equipment, "QuestPopupMenu", FakeQuestPopup)

    assert screen._open_menu_choice("Quests", player) is None
    assert opened == ["created", (True, True)]


def test_town_character_info_uses_modern_screen_by_default(monkeypatch):
    used = []

    class FakeModern:
        def __init__(self, _presenter):
            used.append("modern")

        def navigate(self, _player):
            return "Exit Menu"

    game = pygame_game.PygameGame.__new__(pygame_game.PygameGame)
    game.presenter = SimpleNamespace()
    game.player_char = SimpleNamespace(quit=False)
    monkeypatch.setattr(pygame_game, "ModernCharacterScreen", FakeModern)

    game.show_character_info()

    assert used == ["modern"]


def test_dungeon_character_screen_router_lazy_loads_modern_default(monkeypatch):
    created = []

    class FakeModern:
        def __init__(self, presenter):
            self.presenter = presenter
            self.background = None
            created.append(self)

    import src.ui_pygame.gui.modern_character_screen as modern_module

    monkeypatch.setattr(
        "src.ui_pygame.gui.modern_character_screen.screen.ModernCharacterScreen", FakeModern
    )

    manager = DungeonManager.__new__(DungeonManager)
    manager.presenter = SimpleNamespace()
    manager.game = SimpleNamespace()
    manager.character_screen = None
    manager._dungeon_background = "dungeon-bg"

    first = manager._get_character_screen()
    second = manager._get_character_screen()

    assert first is second
    assert first.background == "dungeon-bg"
    assert created == [first]
