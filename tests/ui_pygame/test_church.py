#!/usr/bin/env python3
"""Focused coverage for church manager helpers."""

from __future__ import annotations

from types import SimpleNamespace

import pygame

from src.core import companions, items
from src.core.classes import class_rings, demonologist, paladin
from src.ui_pygame.gui import church


class FakePopup:
    messages = []
    show_kwargs = []

    def __init__(self, _presenter, message, show_buttons=False, **_kwargs):
        self.message = message
        FakePopup.messages.append(message)

    def show(self, **kwargs):
        FakePopup.show_kwargs.append(kwargs)
        return True


def _make_player():
    return SimpleNamespace(
        name="Ada Hero",
        quest_dict={"Main": {}, "Bounty": {}},
        gold=0,
        familiar=None,
        summons={},
        cls=SimpleNamespace(name="Warrior", equipment={}),
        race=SimpleNamespace(cls_res={"First": []}),
        level=SimpleNamespace(level=10, pro_level=1, exp_to_gain=10),
        stats=SimpleNamespace(strength=10, intel=10, wisdom=10, con=10, charisma=10, dex=10),
        health=SimpleNamespace(max=100, current=100),
        mana=SimpleNamespace(max=50, current=50),
        combat=SimpleNamespace(attack=10, defense=10, magic=10, magic_def=10),
        spellbook={"Spells": {}, "Skills": {}},
        equipment={},
        level_exp=lambda: 42,
        save=lambda filepath=None: None,
        unequip=lambda promo=False: None,
        equip=lambda slot, item, check=True: None,
    )


def _make_presenter():
    pygame.font.init()
    return SimpleNamespace(
        screen=object(),
        width=900,
        height=700,
        title_font=pygame.font.Font(None, 30),
        large_font=pygame.font.Font(None, 26),
        normal_font=pygame.font.Font(None, 22),
        small_font=pygame.font.Font(None, 18),
        clock=SimpleNamespace(tick=lambda _fps: None),
        render_menu=lambda *_args, **_kwargs: None,
        show_message=lambda *_args, **_kwargs: None,
        get_text_input=lambda *_args, **_kwargs: "Buddy",
        debug_mode=False,
    )


def _make_surface_presenter(width=900, height=700):
    presenter = _make_presenter()
    presenter.screen = pygame.Surface((width, height))
    presenter.width = width
    presenter.height = height
    return presenter


def test_paladin_vow_selection_popup_draws_details_and_selects_highlighted(monkeypatch):
    pygame.init()
    pygame.event.clear()
    presenter = _make_surface_presenter()
    flips = []
    monkeypatch.setattr("src.ui_pygame.gui.church.pygame.display.flip", lambda: flips.append(True))

    popup = church.PaladinVowSelectionPopup(presenter)
    popup.draw(lambda: presenter.screen.fill((0, 0, 0)))

    assert popup.options == list(paladin.PATHS)
    assert len(popup.option_rects) == len(paladin.PATHS)
    assert popup.detail_rect is not None
    assert popup.instruction_rect is not None
    assert popup.instruction_rect.top > popup.detail_rect.bottom
    popup_copy = " ".join(
        list(paladin.DESCRIPTIONS.values())
        + list(paladin.SIGNATURE_DESCRIPTIONS.values())
        + list(paladin.AURA_DESCRIPTIONS.values())
        + list(paladin.MARK_DESCRIPTIONS.values())
    )
    for documented_mechanic in (
        "three encounters",
        "two-turn",
        "+5%",
        "percentage points",
    ):
        assert documented_mechanic in popup_copy

    pygame.event.post(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_DOWN))
    pygame.event.post(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_RETURN))

    selected = popup.show(
        flush_events=False,
        require_key_release=False,
        background_draw_func=lambda: presenter.screen.fill((0, 0, 0)),
    )

    assert selected == "Conquest"
    assert flips


def test_visit_church_routes_actions(monkeypatch):
    FakePopup.messages = []
    FakePopup.show_kwargs = []
    player = _make_player()
    presenter = _make_presenter()
    monkeypatch.setattr(
        church.ChurchManager, "_load_background", lambda self: setattr(self, "background", None)
    )
    monkeypatch.setattr("src.ui_pygame.gui.church.ConfirmationPopup", FakePopup)
    manager = church.ChurchManager(presenter, player)

    calls = []
    manager.save_game = lambda: calls.append("save")

    selections = iter([0, 1, 2])
    rendered = []
    draw_frame_calls = []
    option_snapshots = []

    class FakeLocationMenuScreen:
        def __init__(self, _presenter, _title):
            pass

        def set_location_portrait(self, _npc_name):
            return None

        def draw_frame(self, *, do_flip=False):
            draw_frame_calls.append(do_flip)

        def navigate(self, options, reset_cursor=False, **_kwargs):
            option_snapshots.append(tuple(options))
            return next(selections)

        def display_quest_text(self, text, **kwargs):
            rendered.append((text, kwargs.get("npc_name")))

    class FakeQuestManager:
        def __init__(self, _presenter, _player, quest_text_renderer=None, **_kwargs):
            self.quest_text_renderer = quest_text_renderer

        def has_available_or_active_quest(self, _giver):
            return True

        def check_and_offer(self, patron):
            self.quest_text_renderer(f"{patron} quest")

    monkeypatch.setattr("src.ui_pygame.gui.church.LocationMenuScreen", FakeLocationMenuScreen)
    monkeypatch.setattr("src.ui_pygame.gui.church.QuestManager", FakeQuestManager)

    manager.visit_church()

    assert calls == ["save"]
    assert all("Promote" not in options for options in option_snapshots)
    assert rendered == [("Priest quest", "Priest")]
    assert "Let the light of Elysia guide you." in FakePopup.messages
    assert FakePopup.show_kwargs[-1]["flush_events"] is True
    assert FakePopup.show_kwargs[-1]["require_key_release"] is True
    assert callable(FakePopup.show_kwargs[-1]["background_draw_func"])
    FakePopup.show_kwargs[-1]["background_draw_func"]()
    assert draw_frame_calls == [False]


def test_visit_church_hides_quest_option_without_available_or_active_quest(monkeypatch):
    player = _make_player()
    presenter = _make_presenter()
    monkeypatch.setattr(
        church.ChurchManager, "_load_background", lambda self: setattr(self, "background", None)
    )
    monkeypatch.setattr("src.ui_pygame.gui.church.ConfirmationPopup", FakePopup)
    manager = church.ChurchManager(presenter, player)

    option_snapshots = []

    class FakeLocationMenuScreen:
        def __init__(self, _presenter, _title):
            pass

        def set_location_portrait(self, _npc_name):
            return None

        def draw_frame(self, *, do_flip=False):
            return None

        def navigate(self, options, **_kwargs):
            option_snapshots.append(tuple(options))
            return options.index("Leave")

    class FakeQuestManager:
        def __init__(self, *_args, **_kwargs):
            pass

        def has_available_or_active_quest(self, _giver):
            return False

    monkeypatch.setattr("src.ui_pygame.gui.church.LocationMenuScreen", FakeLocationMenuScreen)
    monkeypatch.setattr("src.ui_pygame.gui.church.QuestManager", FakeQuestManager)

    manager.visit_church()

    assert option_snapshots == [("Save Game", "Leave")]


def test_save_game_reports_success_and_failure(monkeypatch):
    FakePopup.messages = []
    player = _make_player()
    presenter = _make_presenter()
    monkeypatch.setattr(
        church.ChurchManager,
        "_load_background",
        lambda self: setattr(self, "background", None),
    )
    monkeypatch.setattr(
        "src.ui_pygame.gui.church.ConfirmationPopup",
        FakePopup,
    )
    manager = church.ChurchManager(presenter, player)

    save_calls = []
    monkeypatch.setattr(
        church.SaveManager,
        "save_player",
        lambda saved_player, filename: save_calls.append((saved_player, filename)) or True,
    )
    manager.save_game()

    assert save_calls == [(player, "ada_hero.save")]
    assert "Game saved successfully!" in FakePopup.messages[-1]

    monkeypatch.setattr(
        church.SaveManager,
        "save_player",
        lambda _saved_player, _filename: False,
    )
    manager.save_game()

    assert "Error saving game." in FakePopup.messages[-1]


def test_hidden_crypt_binds_contract_and_awakens_ring(monkeypatch):
    FakePopup.messages = []
    FakePopup.show_kwargs = []
    player = _make_player()
    player.cls = SimpleNamespace(name="Demonologist")
    player.kill_dict = {"Fiend": {"Imp": 1, "Balor": 1}}
    player.demonologist_contracts = demonologist.default_state()
    player.ensure_demonologist_contracts = lambda: demonologist.ensure_state(player)
    player.refresh_demonologist_contracts = lambda: demonologist.refresh_unlocked_contracts(player)
    player.equipment = {"Ring": items.ClassRing()}
    familiar = companions.Mephit()
    familiar.name = "Spark"
    player.familiar = familiar

    presenter = _make_presenter()
    selections = iter([1, 1, 2, 2])
    presenter.render_menu = lambda *_args, **_kwargs: next(selections)

    monkeypatch.setattr(
        church.ChurchManager, "_load_background", lambda self: setattr(self, "background", None)
    )
    monkeypatch.setattr("src.ui_pygame.gui.church.ConfirmationPopup", FakePopup)

    manager = church.ChurchManager(presenter, player)
    assert manager.visit_hidden_crypt() is True

    assert player.demonologist_contracts["active_patron"] == "Balor"
    assert player.demonologist_contracts["ring_awakened"] is True
    assert player.familiar is None
    assert any("Balor is now your active contract." in message for message in FakePopup.messages)
    assert any("Class Ring awakens" in message for message in FakePopup.messages)


def test_arcane_class_ring_rite_requires_visible_dormant_ring(monkeypatch):
    player = _make_player()
    player.cls = SimpleNamespace(name="Wizard")
    player.class_ring_awakening = class_rings.default_state()
    player.inventory = {"Class Ring": [items.ClassRing()]}
    presenter = _make_presenter()
    monkeypatch.setattr(
        church.ChurchManager, "_load_background", lambda self: setattr(self, "background", None)
    )

    manager = church.ChurchManager(presenter, player)
    assert manager._arcane_class_ring_rite_label() == "Four Formulae"
    assert manager._arcane_class_ring_rite_available() is False

    player.storage = {"Class Ring": [items.ClassRing()]}
    assert manager._arcane_class_ring_rite_available() is True

    player.storage = {}
    player.equipment["Ring"] = items.ClassRing()
    assert manager._arcane_class_ring_rite_available() is True

    player.class_ring_awakening["awakened"]["Wizard"] = True
    assert manager._arcane_class_ring_rite_available() is False


def test_arcane_class_ring_rites_awaken_ring_and_apply_mods(monkeypatch):
    FakePopup.messages = []
    presenter = _make_presenter()
    monkeypatch.setattr(
        church.ChurchManager, "_load_background", lambda self: setattr(self, "background", None)
    )
    monkeypatch.setattr("src.ui_pygame.gui.church.ConfirmationPopup", FakePopup)

    for class_name, expected_mod, expected_label in (
        ("Wizard", "School Streak", "Four Formulae"),
        ("Shadowcaster", "Umbral Debt", "Debt Cap Trial"),
        ("Knight Enchanter", "Weave Memory", "Arcane Duel"),
        ("Thaumaturgist", "+30% Xenids", "Conduit Ritual"),
        ("Templar", "Ordered Blessings", "Relic Defense"),
        ("Hierophant", "Sacred Conduit", "Consecration Rite"),
        ("Master Monk", "Martial Master", "Purity Rite"),
        ("Archbishop", "Divine Intervention", "Miracle Vigil"),
        ("Troubadour", "Encore", "Lost Ballad"),
        ("Lycan", "Controlled Frenzy", "Control Rite"),
        ("Astromancer", "Constellation Cycle", "Star Chart"),
        ("Soulcatcher", "Aspect Evolution", "Ancestral Totem Rite"),
        ("Beast Master", "Shared Recovery", "Pack Trial"),
    ):
        player = _make_player()
        player.cls = SimpleNamespace(name=class_name)
        player.class_ring_awakening = class_rings.default_state()
        player.equipment["Ring"] = items.ClassRing()
        player.health = SimpleNamespace(current=200, max=200)
        player.awaken_class_ring = (
            lambda class_name=None, _player=player, **kwargs: class_rings.activate(
                _player,
                class_name,
                **kwargs,
            )
        )

        manager = church.ChurchManager(presenter, player)
        assert manager.visit_arcane_class_ring_rite() is True
        assert player.class_ring_awakening["awakened"][class_name] is True
        assert player.equipment["Ring"].mod == expected_mod
        assert any(expected_label in message for message in FakePopup.messages)
        if class_name == "Thaumaturgist":
            assert player.health.max == 190
            assert player.health.current == 190


def test_paladin_legacy_vow_choice_and_crusader_vow_trial(monkeypatch):
    FakePopup.messages = []
    FakePopup.show_kwargs = []
    presenter = _make_presenter()
    monkeypatch.setattr(
        church.ChurchManager, "_load_background", lambda self: setattr(self, "background", None)
    )
    monkeypatch.setattr("src.ui_pygame.gui.church.ConfirmationPopup", FakePopup)

    class FakeVowSelectionPopup:
        show_kwargs = []

        def __init__(self, _presenter):
            pass

        def show(self, **kwargs):
            FakeVowSelectionPopup.show_kwargs.append(kwargs)
            return "Redemption"

    monkeypatch.setattr("src.ui_pygame.gui.church.PaladinVowSelectionPopup", FakeVowSelectionPopup)

    player = _make_player()
    player.cls = SimpleNamespace(name="Paladin")
    player.paladin_vow = paladin.default_state()
    player.choose_paladin_vow = lambda vow: paladin.choose_vow(player, vow)
    manager = church.ChurchManager(presenter, player)

    assert manager._legacy_paladin_vow_available() is True
    assert manager.visit_legacy_paladin_vow_choice() is True
    assert FakeVowSelectionPopup.show_kwargs[-1]["flush_events"] is True
    assert FakeVowSelectionPopup.show_kwargs[-1]["require_key_release"] is True
    assert FakePopup.show_kwargs[-1]["flush_events"] is True
    assert FakePopup.show_kwargs[-1]["require_key_release"] is True
    assert FakePopup.messages[0] == "Swear the Vow of Redemption?"
    assert "Redeem offers" not in FakePopup.messages[0]
    assert player.paladin_vow["path"] == "Redemption"
    assert "Redeem" in player.spellbook["Skills"]

    player.cls = SimpleNamespace(name="Crusader")
    player.class_ring_awakening = class_rings.default_state()
    player.equipment = {"Ring": items.ClassRing()}
    player.awaken_class_ring = lambda class_name=None, **kwargs: class_rings.activate(
        player, class_name, **kwargs
    )

    assert manager._crusader_vow_trial_available() is True
    assert manager.visit_crusader_vow_trial() is True
    assert player.equipment["Ring"].mod == "Vow Affirmation"
    assert player.class_ring_awakening["data"]["Crusader"]["vow"] == "Redemption"
