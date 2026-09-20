#!/usr/bin/env python3
"""Focused coverage for pygame combat-manager helper logic."""

from __future__ import annotations

from types import SimpleNamespace

import pygame
import pytest

from src.core import abilities, enemies, items, main_story
from src.core.classes import ability_mechanics, class_rings, promotion_kits
from src.ui_pygame.gui import combat_manager
from src.ui_pygame.gui.combat_manager.outcomes import POST_DEATH_PAUSE_MS
from src.ui_pygame.gui.combat_view.animator import DEATH_ANIMATION_FRAMES


@pytest.fixture(autouse=True)
def _init_pygame():
    if not pygame.get_init():
        pygame.init()
    if not pygame.font.get_init():
        pygame.font.init()
    yield


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
        return f"screen-copy-{len(self.blit_calls)}"

    def get_size(self):
        return self._size

    def get_width(self):
        return self._size[0]

    def get_height(self):
        return self._size[1]


class RecordingFont:
    def __init__(self):
        self.render_calls = []

    def render(self, text, _antialias, _color):
        self.render_calls.append(text)
        return SimpleNamespace(
            text=text,
            get_rect=lambda **kwargs: pygame.Rect(0, 0, max(8, len(text) * 8), 24),
        )

    def size(self, text):
        return (max(8, len(text) * 8), 24)


class DummyCombatView:
    def __init__(self, screen, presenter):
        self.screen = screen
        self.presenter = presenter
        self.combat_width = screen.get_size()[0]
        self.combat_height = screen.get_size()[1]
        self.scrolled = []
        self.messages = []
        self.enemy_damage_calls = []
        self.flash_calls = []
        self.impact_calls = []
        self.reload_calls = []
        self.enemy_deaths = []
        self.reset_calls = 0
        self.render_calls = []
        self.hide_enemy_calls = 0
        self.colors = {"log_damage": (235, 120, 105), "log_heal": (120, 210, 135)}

    def scroll_log(self, amount):
        self.scrolled.append(amount)

    def add_combat_message(self, message):
        self.messages.append(message)

    def reset_combat_log(self):
        self.reset_calls += 1

    def hide_enemy_for_flee(self):
        self.hide_enemy_calls += 1

    def render_enemy_in_dungeon(self, *args, **kwargs):
        self.render_calls.append(("enemy", args, kwargs))
        return None

    def render_combat_overlay(self, *args, **kwargs):
        self.render_calls.append(("overlay", args, kwargs))
        return None

    def enemy_take_damage(self, enemy):
        self.enemy_damage_calls.append(enemy)

    def show_damage_flash(self, player_side, event_handler=None):
        self.flash_calls.append((player_side, event_handler))

    def trigger_impact_effect(self, target, kind="weapon", element=None, critical=False):
        self.impact_calls.append((target, kind, element, critical))

    def trigger_floating_text(self, target, text, color=None):
        self.impact_calls.append(("float", target, text, color))

    def reload_enemy_sprite(self, enemy):
        self.reload_calls.append(enemy)

    def enemy_dies(self, enemy):
        self.enemy_deaths.append(enemy)


def test_combat_entry_and_turn_delay_constants():
    assert combat_manager.COMBAT_START_TRANSITION_FRAMES == 12
    assert combat_manager.POST_TURN_DELAY_FRAMES == 3


class DummyLevelUpScreen:
    def __init__(self, screen, presenter):
        self.screen = screen
        self.presenter = presenter
        self.calls = []

    def show_level_up(self, player_char, game):
        self.calls.append((player_char, game))


class DummyHud:
    def __init__(self):
        self.calls = []

    def render_hud(self, *args, **kwargs):
        self.calls.append((args, kwargs))


class DummyPresenter:
    def __init__(self):
        self.screen = RecordingScreen()
        self.title_font = RecordingFont()
        self.normal_font = RecordingFont()
        self.small_font = RecordingFont()
        self._background = "presenter-background"
        self.text_inputs = []
        self.next_text_input = ""

    def get_background_surface(self):
        return self._background

    def get_text_input(self, prompt, default=""):
        self.text_inputs.append((prompt, default))
        return self.next_text_input


class DummyClock:
    def __init__(self, frame_ms=100):
        self.ticks = []
        self.frame_ms = frame_ms

    def tick(self, fps):
        self.ticks.append(fps)

    def get_time(self):
        return self.frame_ms


def test_controller_parity_maps_dpad_buttons_and_focus_bumpers(monkeypatch):
    manager = _make_manager(monkeypatch)

    assert (
        manager._controller_key(SimpleNamespace(type=pygame.JOYHATMOTION, value=(0, 1)))
        == pygame.K_UP
    )
    assert (
        manager._controller_key(SimpleNamespace(type=pygame.JOYBUTTONDOWN, button=0))
        == pygame.K_RETURN
    )
    assert (
        manager._controller_key(SimpleNamespace(type=pygame.JOYBUTTONDOWN, button=1))
        == pygame.K_ESCAPE
    )
    assert (
        manager._controller_key(SimpleNamespace(type=pygame.JOYBUTTONDOWN, button=2)) == pygame.K_x
    )
    assert (
        manager._controller_key(SimpleNamespace(type=pygame.JOYBUTTONDOWN, button=3)) == pygame.K_y
    )
    assert (
        manager._controller_key(SimpleNamespace(type=pygame.JOYBUTTONDOWN, button=4)) == pygame.K_q
    )
    assert (
        manager._controller_key(SimpleNamespace(type=pygame.JOYBUTTONDOWN, button=5)) == pygame.K_e
    )


class DummySurface:
    def __init__(self, size=(800, 600)):
        self._size = size
        self.alpha = None
        self.fill_calls = []

    def set_alpha(self, value):
        self.alpha = value

    def fill(self, color):
        self.fill_calls.append(color)

    def get_size(self):
        return self._size


def _make_manager(monkeypatch):
    presenter = DummyPresenter()
    hud = DummyHud()
    game = SimpleNamespace()

    monkeypatch.setattr(combat_manager.core, "CombatView", DummyCombatView)
    monkeypatch.setattr(combat_manager.core, "LevelUpScreen", DummyLevelUpScreen)

    manager = combat_manager.GUICombatManager(presenter, hud, game)
    return manager


def _make_player(name="Hero"):
    story_state = main_story.default_state()
    player = SimpleNamespace(
        name=name,
        health=SimpleNamespace(current=50, max=50),
        mana=SimpleNamespace(current=10, max=10),
        spellbook={"Spells": {}, "Skills": {}},
        inventory={},
        encumbered=False,
        anti_magic_active=False,
        main_story=story_state,
        state="fight",
        location_x=9,
        location_y=9,
        location_z=9,
        facing="south",
    )
    player.in_town = lambda: False
    player.is_alive = lambda: player.health.current > 0
    player.is_disarmed = lambda: False
    player.abilities_suppressed = lambda: False
    player.effects = lambda end=False: None
    player.ensure_main_story_state = lambda: player.main_story
    return player


def _make_enemy(name="Goblin", hp=(20, 20)):
    enemy = SimpleNamespace(name=name, health=SimpleNamespace(current=hp[0], max=hp[1]))
    enemy.is_alive = lambda: enemy.health.current > 0
    return enemy


def test_resolve_bursts_require_mastery_and_a_full_bar(monkeypatch):
    manager = _make_manager(monkeypatch)
    player = _make_player()
    player.cls = SimpleNamespace(name="Stalwart Defender")
    player.equipment = {"OffHand": SimpleNamespace(subtyp="Shield")}
    player.class_ring_awakening = class_rings.default_state()
    state = class_rings.ensure_state(player)["data"]["Stalwart Defender"]
    state["guard_meter"] = 99
    state["resolve_mastery"] = {
        "citadel_aegis": 0,
        "ironwall_revenge": 0,
        "last_bastion": 0,
        "stronghold": 0,
    }

    assert not manager._skill_available_for_selection(player, abilities.CitadelAegis())
    class_rings.ensure_state(player)["data"]["Stalwart Defender"]["guard_meter"] = 100
    assert not manager._skill_available_for_selection(player, abilities.CitadelAegis())
    assert not manager._skill_available_for_selection(player, abilities.IronwallReprisal())
    assert not manager._skill_available_for_selection(player, abilities.LastBastionSurge())
    assert not manager._skill_available_for_selection(player, abilities.Stronghold())
    assert manager._skill_available_for_selection(player, abilities.BraceWall())

    state = class_rings.ensure_state(player)["data"]["Stalwart Defender"]
    state["guard_meter"] = 99
    state["resolve_mastery"]["ironwall_revenge"] = 3
    assert not manager._skill_available_for_selection(
        player,
        abilities.IronwallReprisal(),
    )
    state = class_rings.ensure_state(player)["data"]["Stalwart Defender"]
    state["resolve_mastery"]["ironwall_revenge"] = 4
    assert not manager._skill_available_for_selection(player, abilities.IronwallReprisal())

    class_rings.ensure_state(player)["data"]["Stalwart Defender"]["guard_meter"] = 100
    assert manager._skill_available_for_selection(player, abilities.IronwallReprisal())


def test_silence_keeps_resolve_and_zero_mana_skills_available(monkeypatch):
    manager = _make_manager(monkeypatch)
    player = _make_player()
    enemy = _make_enemy()
    player.cls = SimpleNamespace(name="Sentinel")
    player.equipment = {
        "OffHand": SimpleNamespace(subtyp="Shield"),
    }
    player.status_effects = {
        "Silence": SimpleNamespace(active=True),
    }
    player.spellbook["Skills"] = {
        "Brace Wall": abilities.BraceWall(),
        "Free Technique": SimpleNamespace(
            name="Free Technique",
            cost=0,
            passive=False,
        ),
        "Mana Technique": SimpleNamespace(
            name="Mana Technique",
            cost=4,
            passive=False,
        ),
    }
    manager.engine = SimpleNamespace(
        available_actions=["Attack", "Use Skill", "Use Item"],
        player=player,
        attacker=player,
        defender=enemy,
    )

    assert manager._available_skill_names(player, enemy, resolve=True) == [
        "Brace Wall",
    ]
    assert manager._available_skill_names(player, enemy, resolve=False) == [
        "Free Technique",
    ]
    assert manager._build_display_actions() == [
        "Attack",
        "Defend",
        "Resolve",
        "Skills",
        "Items",
    ]


def test_adrenaline_is_hidden_until_health_is_below_threshold(monkeypatch):
    manager = _make_manager(monkeypatch)
    player = _make_player()
    skill = abilities.Adrenaline()

    player.health.current = 5
    assert not manager._skill_available_for_selection(player, skill)

    player.health.current = 4
    assert manager._skill_available_for_selection(player, skill)


def test_mortal_strike_requires_a_two_handed_weapon_in_skill_menu(monkeypatch):
    manager = _make_manager(monkeypatch)
    player = _make_player()
    player.cls = SimpleNamespace(name="Weapon Master")
    player.status_effects = {"Silence": SimpleNamespace(active=False)}
    player.equipment = {
        "Weapon": SimpleNamespace(handed=1),
        "OffHand": SimpleNamespace(subtyp="None"),
    }
    skill = abilities.MortalStrike()

    assert not manager._skill_available_for_selection(player, skill)
    player.equipment["Weapon"].handed = 2
    assert manager._skill_available_for_selection(player, skill)


def _patch_fast_start_combat(monkeypatch, manager):
    monkeypatch.setattr("src.ui_pygame.gui.combat_manager.pygame.event.get", lambda *_args: [])
    monkeypatch.setattr("src.ui_pygame.gui.combat_manager.pygame.display.flip", lambda: None)
    monkeypatch.setattr("src.ui_pygame.gui.combat_manager.pygame.time.Clock", lambda: DummyClock())
    monkeypatch.setattr(manager, "_render_combat_frame", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(manager, "_refresh_combat_background", lambda *_args, **_kwargs: None)


class ScriptedEngine:
    def __init__(self, player, enemy, *, player_turn=True):
        self.player = player
        self.enemy = enemy
        self.player_turn = player_turn
        self.available_actions = ["Attack"]
        self.flee = False
        self.ended = False
        self.post_turn_calls = 0
        self.swap_calls = 0

    def start_battle(self):
        return (self.player if self.player_turn else self.enemy, None)

    def battle_continues(self):
        return True

    def is_player_turn(self):
        return self.player_turn

    def post_turn(self):
        self.post_turn_calls += 1
        return SimpleNamespace(messages=[])

    def swap_turns(self):
        self.swap_calls += 1

    def end_battle(self):
        self.ended = True
        raise AssertionError("false-final branch must not call normal battle end")


def test_vesperion_false_final_triggers_at_hp_threshold_without_battle_end(monkeypatch):
    manager = _make_manager(monkeypatch)
    _patch_fast_start_combat(monkeypatch, manager)
    player = _make_player()
    enemy = enemies.Vesperion()
    enemy.health.max = 1000
    enemy.health.current = 1000
    engine = ScriptedEngine(player, enemy, player_turn=True)
    monkeypatch.setattr(combat_manager.lifecycle, "BattleEngine", lambda **_kwargs: engine)

    def player_turn(_player, target):
        target.health.current = 700
        return True

    monkeypatch.setattr(manager, "_player_turn", player_turn)

    assert manager.start_combat(player, enemy, SimpleNamespace()) is False
    assert engine.ended is False
    assert player.main_story["vesperion_false_final_triggered"] is True
    assert player.main_story["pending_liminal_gap_entry"] is True


def test_vesperion_false_final_triggers_after_three_enemy_turns(monkeypatch):
    manager = _make_manager(monkeypatch)
    _patch_fast_start_combat(monkeypatch, manager)
    player = _make_player()
    enemy = enemies.Vesperion()
    enemy.health.max = 1000
    enemy.health.current = 1000
    engine = ScriptedEngine(player, enemy, player_turn=False)
    enemy_turns = []
    monkeypatch.setattr(combat_manager.lifecycle, "BattleEngine", lambda **_kwargs: engine)
    monkeypatch.setattr(
        manager, "_enemy_turn", lambda _player, _enemy: enemy_turns.append("turn") or None
    )

    assert manager.start_combat(player, enemy, SimpleNamespace()) is False
    assert enemy_turns == ["turn", "turn", "turn"]
    assert engine.ended is False
    assert player.main_story["vesperion_false_final_triggered"] is True
    assert player.main_story["pending_liminal_gap_entry"] is True


def test_vesperion_death_before_threshold_uses_false_final_not_defeat(monkeypatch):
    manager = _make_manager(monkeypatch)
    _patch_fast_start_combat(monkeypatch, manager)
    player = _make_player()
    enemy = enemies.Vesperion()
    enemy.health.max = 1000
    enemy.health.current = 1000
    engine = ScriptedEngine(player, enemy, player_turn=False)
    monkeypatch.setattr(combat_manager.lifecycle, "BattleEngine", lambda **_kwargs: engine)

    def enemy_turn(_player, _enemy):
        _player.health.current = 0
        return None

    monkeypatch.setattr(manager, "_enemy_turn", enemy_turn)

    assert manager.start_combat(player, enemy, SimpleNamespace()) is False
    assert engine.ended is False
    assert player.main_story["vesperion_false_final_triggered"] is True
    assert player.main_story["pending_liminal_gap_entry"] is True


def test_fleeing_vesperion_does_not_set_liminal_flags(monkeypatch):
    manager = _make_manager(monkeypatch)
    _patch_fast_start_combat(monkeypatch, manager)
    player = _make_player()
    enemy = enemies.Vesperion()
    engine = ScriptedEngine(player, enemy, player_turn=True)
    handled = []
    monkeypatch.setattr(combat_manager.lifecycle, "BattleEngine", lambda **_kwargs: engine)
    monkeypatch.setattr(manager, "_player_turn", lambda _player, _enemy: "flee")
    monkeypatch.setattr(
        manager,
        "_handle_combat_end",
        lambda _player, _enemy, fled: handled.append(fled) or False,
    )

    assert manager.start_combat(player, enemy, SimpleNamespace()) is False
    assert handled == [True]
    assert player.main_story == main_story.default_state()


def test_reflection_psychopomp_victory_unlocks_true_final_without_engine_end(monkeypatch):
    manager = _make_manager(monkeypatch)
    player = _make_player()
    player.main_story["voluntas_revealed"] = True
    enemy = enemies.ReflectionPsychopomp()
    enemy.health.current = 0
    manager.engine = SimpleNamespace(
        flee=False,
        end_battle=lambda: (_ for _ in ()).throw(
            AssertionError("normal end_battle should not run")
        ),
    )

    result = manager._handle_combat_end(player, enemy, fled=False)

    assert result is True
    assert player.main_story["reflection_defeated"] is True
    assert player.main_story["true_final_unlocked"] is True
    assert player.state == "normal"
    assert "The Reflection yields to the self you chose." in manager.combat_view.messages
    assert manager.combat_view.reset_calls == 1


def test_reflection_psychopomp_defeat_returns_to_liminal_hub_without_death(monkeypatch):
    manager = _make_manager(monkeypatch)
    player = _make_player()
    player.health.max = 101
    player.health.current = 0
    player.mana.max = 51
    player.mana.current = 0
    effect_calls = []
    player.effects = lambda end=False: effect_calls.append(end)
    enemy = enemies.ReflectionPsychopomp()
    manager.engine = SimpleNamespace(
        flee=False,
        end_battle=lambda: (_ for _ in ()).throw(
            AssertionError("normal end_battle should not run")
        ),
    )

    result = manager._handle_combat_end(player, enemy, fled=False)

    assert result is False
    assert (
        player.location_x,
        player.location_y,
        player.location_z,
    ) == combat_manager.LIMINAL_GAP_ENTRY_POS
    assert player.facing == combat_manager.LIMINAL_GAP_ENTRY_FACING
    assert player.health.current == 50
    assert player.mana.current == 25
    assert player.state == "normal"
    assert player.main_story["reflection_defeated"] is False
    assert player.main_story["true_final_unlocked"] is False
    assert effect_calls == [True]
    assert (
        "The Reflection breaks your stance and returns you to the Liminal hub."
        in manager.combat_view.messages
    )


def test_guardian_trial_echo_victory_bypasses_normal_rewards(monkeypatch):
    manager = _make_manager(monkeypatch)
    player = _make_player()
    enemy = enemies.GuardianTrialEcho("Triangulus", profile="Memory")
    enemy.health.current = 0
    manager.engine = SimpleNamespace(
        flee=False,
        end_battle=lambda: (_ for _ in ()).throw(
            AssertionError("normal end_battle should not run")
        ),
    )

    result = manager._handle_combat_end(player, enemy, fled=False)

    assert result is True
    assert player.state == "normal"
    assert player.main_story["guardian_trials_completed"]["Triangulus"] is False
    assert (
        "Triangulus yields to the choice you carried into the fight."
        in manager.combat_view.messages
    )
    assert manager.combat_view.reset_calls == 1


def test_guardian_trial_echo_defeat_returns_to_liminal_hub_without_death(monkeypatch):
    manager = _make_manager(monkeypatch)
    player = _make_player()
    player.health.max = 101
    player.health.current = 0
    player.mana.max = 51
    player.mana.current = 0
    effect_calls = []
    player.effects = lambda end=False: effect_calls.append(end)
    enemy = enemies.GuardianTrialEcho("Infinitas", profile="Rest")
    manager.engine = SimpleNamespace(
        flee=False,
        end_battle=lambda: (_ for _ in ()).throw(
            AssertionError("normal end_battle should not run")
        ),
    )

    result = manager._handle_combat_end(player, enemy, fled=False)

    assert result is False
    assert (
        player.location_x,
        player.location_y,
        player.location_z,
    ) == combat_manager.LIMINAL_GAP_ENTRY_POS
    assert player.facing == combat_manager.LIMINAL_GAP_ENTRY_FACING
    assert player.health.current == 50
    assert player.mana.current == 25
    assert player.state == "normal"
    assert player.main_story["guardian_trials_completed"]["Infinitas"] is False
    assert effect_calls == [True]
    assert (
        "Infinitas returns you to the Liminal hub to choose again." in manager.combat_view.messages
    )


def test_vesperion_true_final_victory_completes_story_without_engine_end(monkeypatch):
    manager = _make_manager(monkeypatch)
    player = _make_player()
    player.main_story["true_final_unlocked"] = True
    enemy = enemies.Vesperion()
    enemy.health.current = 0
    manager.engine = SimpleNamespace(
        flee=False,
        end_battle=lambda: (_ for _ in ()).throw(
            AssertionError("normal end_battle should not run")
        ),
    )

    result = manager._handle_combat_end(player, enemy, fled=False)

    assert result is True
    assert player.main_story["vesperion_true_final_defeated"] is True
    assert player.main_story["main_story_complete"] is True
    assert player.state == "normal"
    assert "Vesperion falls silent. Voluntas remains." in manager.combat_view.messages
    assert manager.combat_view.reset_calls == 1


def test_render_combat_frame_preserves_enemy_draw_before_overlay(monkeypatch):
    manager = _make_manager(monkeypatch)
    player = _make_player()
    enemy = _make_enemy()
    dungeon_calls = []
    manager.dungeon_renderer = SimpleNamespace(
        render_dungeon_view=lambda *args, **kwargs: dungeon_calls.append((args, kwargs))
    )
    manager.player_world_dict = {"tile": object()}
    manager.engine = SimpleNamespace(is_player_turn=lambda: False, show_enemy_details=lambda: False)

    manager._render_combat_frame(player, enemy, ["Attack"], 0)

    assert dungeon_calls
    assert [call[0] for call in manager.combat_view.render_calls] == ["enemy", "overlay"]
    assert manager.combat_view.render_calls[0][1] == (player, enemy)
    assert manager.combat_view.render_calls[1][2]["current_turn"] is None
    assert manager.combat_view.render_calls[1][2]["show_enemy_details"] is False
    assert manager.hud.calls
    assert manager.hud.calls[-1][1]["active_summon"] is None


def test_render_combat_frame_passes_active_summon_to_hud(monkeypatch):
    manager = _make_manager(monkeypatch)
    player = _make_player()
    enemy = _make_enemy()
    summon = SimpleNamespace(name="Patagon", is_alive=lambda: True)
    manager.engine = SimpleNamespace(
        attacker=summon,
        summon_active=True,
        summon=summon,
        is_player_turn=lambda: True,
        show_enemy_details=lambda: False,
    )

    manager._render_combat_frame(player, enemy, ["Attack"], 0)

    assert manager.hud.calls[-1][1]["active_summon"] is summon


def test_render_combat_frame_records_bestiary_details_when_visible(monkeypatch):
    manager = _make_manager(monkeypatch)
    player = _make_player()
    enemy = _make_enemy("Specter")
    enemy.enemy_typ = "Undead"
    calls = []
    player.record_bestiary_enemy = lambda observed, enemy_type=None: calls.append(
        (observed, enemy_type)
    )
    manager.engine = SimpleNamespace(is_player_turn=lambda: False, show_enemy_details=lambda: True)

    manager._render_combat_frame(player, enemy, ["Attack"], 0)

    assert calls == [(enemy, "Undead")]


def test_capture_background_scroll_handling_and_action_deduplication(monkeypatch):
    manager = _make_manager(monkeypatch)

    assert manager._capture_background() == "presenter-background"
    manager.presenter.get_background_surface = lambda: (_ for _ in ()).throw(RuntimeError("boom"))
    assert str(manager._capture_background()).startswith("screen-copy")

    up = pygame.event.Event(pygame.KEYDOWN, key=pygame.K_PAGEUP)
    down = pygame.event.Event(pygame.KEYDOWN, key=pygame.K_PAGEDOWN)
    wheel_up = pygame.event.Event(pygame.MOUSEWHEEL, y=1)
    wheel_down = pygame.event.Event(pygame.MOUSEWHEEL, y=-1)
    noop = pygame.event.Event(pygame.KEYDOWN, key=pygame.K_RETURN)

    assert manager._handle_combat_log_scroll_event(up) is True
    assert manager._handle_combat_log_scroll_event(down) is True
    assert manager._handle_combat_log_scroll_event(wheel_up) is True
    assert manager._handle_combat_log_scroll_event(wheel_down) is True
    assert manager._handle_combat_log_scroll_event(noop) is False
    assert manager.combat_view.scrolled == [-1, 1, -1, 1]

    player = _make_player()
    player.is_disarmed = lambda: True
    manager.engine = SimpleNamespace(
        available_actions=[
            "Attack",
            "Cast Spell",
            "Cast Spell",
            {"name": "Use Skill"},
            "Use Item",
            "",
        ],
        player=player,
    )
    assert manager._build_display_actions() == [
        "Attack",
        "Defend",
        "Pickup Weapon",
        "Spells",
        "Skills",
        "Items",
    ]

    player.is_disarmed = lambda: False
    player.equipment = {"OffHand": SimpleNamespace(subtyp="Shield")}
    player.spellbook["Skills"] = {
        "Brace Wall": abilities.BraceWall(),
        "Shield Slam": SimpleNamespace(name="Shield Slam", cost=2, passive=False),
    }
    manager.engine = SimpleNamespace(
        available_actions=["Attack", "Use Skill", "Use Item"],
        player=player,
        defender=_make_enemy(),
    )
    assert manager._build_display_actions() == ["Attack", "Defend", "Resolve", "Skills", "Items"]

    player.spellbook["Skills"].pop("Shield Slam")
    assert manager._build_display_actions() == ["Attack", "Defend", "Resolve", "Items"]

    player.cls = SimpleNamespace(name="Sentinel")
    player.spellbook["Skills"]["Hold the Line"] = abilities.HoldTheLine()
    assert manager._build_display_actions() == [
        "Attack",
        "Hold the Line",
        "Resolve",
        "Items",
    ]
    promotion_kits.combat_state(player)["hold_the_line"] = 2
    assert manager._build_display_actions() == ["Attack", "Resolve", "Items"]

    sentinel_skills = player.spellbook["Skills"]
    player.cls = SimpleNamespace(name="Knight Enchanter")
    player.spellbook["Skills"] = {
        "Defensive Release": abilities.DefensiveRelease(),
    }
    assert manager._build_display_actions() == [
        "Attack",
        "Defensive Release",
        "Skills",
        "Items",
    ]

    player.cls = SimpleNamespace(name="Stalwart Defender")
    player.spellbook["Skills"] = sentinel_skills
    player.spellbook["Skills"]["Citadel Aegis"] = abilities.CitadelAegis()
    state = class_rings.ensure_state(player)["data"]["Stalwart Defender"]
    state["guard_meter"] = 100
    state["resolve_mastery"]["citadel_aegis"] = 4
    assert manager._build_display_actions() == [
        "Attack",
        "Resolve",
        "Bursts",
        "Items",
    ]

    player = _make_player()
    player.is_disarmed = lambda: True
    manager.engine = SimpleNamespace(
        available_actions=["Attack", "Cast Spell", {"name": "Use Skill"}, "Use Item"],
        player=player,
    )
    manager.game.debug_mode = True
    assert manager._build_display_actions() == [
        "Attack",
        "Defend",
        "Pickup Weapon",
        "Spells",
        "Skills",
        "Items",
    ]

    beast = _make_player()
    manager.game.debug_mode = False
    beast.cls = SimpleNamespace(name="Beast Master")
    beast.equipment = {"OffHand": SimpleNamespace(subtyp="None")}
    beast.tamed_companion = {"active": True, "name": "Wolf", "bond": 50}
    beast.familiar = SimpleNamespace(name="Wolf", spec="Tamed", is_alive=lambda: True)
    beast.spellbook["Skills"] = {
        "Pack Strike": SimpleNamespace(name="Pack Strike", cost=0, passive=False),
        "Guard Partner": SimpleNamespace(name="Guard Partner", cost=0, passive=False),
        "Quick Strike": SimpleNamespace(name="Quick Strike", cost=0, passive=False),
    }
    manager.engine = SimpleNamespace(
        available_actions=["Attack", "Companion", "Use Skill", "Use Item"],
        player=beast,
        attacker=beast,
        defender=_make_enemy(),
    )
    assert manager._build_display_actions() == ["Attack", "Defend", "Companion", "Skills", "Items"]
    assert manager._available_skill_names(beast, manager.engine.defender) == ["Quick Strike"]
    assert ability_mechanics.available_beast_companion_commands(beast) == [
        "Pack Strike",
        "Guard Partner",
    ]


def test_combat_damage_effect_classifies_actions_and_elements(monkeypatch):
    manager = _make_manager(monkeypatch)

    assert manager._combat_effect_kind("Attack") == "weapon"
    assert manager._combat_effect_kind("Spells") == "spell"
    assert manager._combat_effect_kind("Use Skill") == "skill"
    assert (
        manager._combat_effect_kind("Attack", None, "The spell reflects for 8 damage.") == "reflect"
    )
    assert manager._combat_effect_kind("Attack", None, "Goblin is stunned for 1 turn.") == "status"
    assert manager._combat_effect_element("Lightning Bolt", "Goblin takes damage") == "Electric"
    assert manager._combat_effect_element(None, "The target burns in holy fire") == "Fire"

    manager._show_combat_damage_effect(
        "enemy", "Spells", "Lightning Bolt", "Goblin takes 12 electric damage.", 12
    )
    manager._show_combat_damage_effect("player", "Attack", None, "Hero takes 4 damage.", 4)
    manager._show_combat_damage_effect("enemy", "Attack", None, "Goblin takes 6 fire damage.", 6)
    manager._show_combat_damage_effect(
        "player", "Attack", None, "The spell reflects for 5 damage.", 5
    )
    manager._show_combat_damage_effect(
        "enemy", "Attack", None, "Goblin is knocked prone for 3 damage.", 3
    )

    assert manager.combat_view.impact_calls == [
        ("enemy", "spell", "Electric", False),
        ("float", "enemy", "-12", (235, 120, 105)),
        ("player", "weapon", None, False),
        ("float", "player", "-4", (235, 120, 105)),
        ("enemy", "elemental_strike", "Fire", False),
        ("float", "enemy", "-6", (235, 120, 105)),
        ("player", "reflect", None, False),
        ("float", "player", "-5", (235, 120, 105)),
        ("enemy", "status", None, False),
        ("float", "enemy", "-3", (235, 120, 105)),
    ]
    assert [call[0] for call in manager.combat_view.flash_calls] == [True, True]


def test_floating_damage_uses_recorded_primary_damage_not_total_hp_loss():
    result = SimpleNamespace(
        combat_results=SimpleNamespace(
            results=[
                SimpleNamespace(target_id="goblin", damage=40),
                SimpleNamespace(target_id="orc", damage=25),
            ]
        )
    )

    assert (
        combat_manager.GUICombatManager._recorded_floating_damage(
            result,
            45,
            target_id="goblin",
        )
        == 40
    )
    assert (
        combat_manager.GUICombatManager._recorded_floating_damage(
            result,
            30,
            target_id="orc",
        )
        == 25
    )
    assert (
        combat_manager.GUICombatManager._recorded_floating_damage(
            SimpleNamespace(),
            45,
        )
        == 45
    )

    missile_result = SimpleNamespace(
        combat_results=SimpleNamespace(
            results=[
                SimpleNamespace(
                    target_id="goblin",
                    damage=33,
                    extra={"damage_instances": [15, 18]},
                )
            ]
        )
    )
    assert combat_manager.GUICombatManager._recorded_floating_damage(
        missile_result,
        33,
        target_id="goblin",
    ) == (15, 18)


def test_combat_damage_effect_renders_each_recorded_damage_instance(monkeypatch):
    manager = _make_manager(monkeypatch)

    manager._show_combat_damage_effect(
        "enemy",
        "Cast Spell",
        "Magic Missile",
        "",
        (15, 18),
    )

    assert ("float", "enemy", "-15", (235, 120, 105)) in manager.combat_view.impact_calls
    assert ("float", "enemy", "-18", (235, 120, 105)) in manager.combat_view.impact_calls


def test_post_turn_and_special_effect_helpers(monkeypatch):
    manager = _make_manager(monkeypatch)
    manager.engine = SimpleNamespace(
        post_turn=lambda: SimpleNamespace(messages=["Line one\nLine two", "", "Last line"])
    )
    flushes = []
    manager._flush_result_frame = lambda player, enemy: flushes.append(
        (player, enemy, tuple(manager.combat_view.messages))
    )
    manager._post_turn_processing(_make_player(), _make_enemy())
    assert manager.combat_view.messages == ["Line one", "Line two", "Last line"]
    assert flushes[-1][2] == ("Line one", "Line two", "Last line")

    manager.combat_view.messages.clear()
    flushes.clear()
    enemy = _make_enemy()
    enemy.picture = "jester.png"

    def post_turn():
        enemy.picture = "jester2.png"
        return SimpleNamespace(messages=["Palette shift!"])

    monkeypatch.setattr("src.ui_pygame.gui.combat_manager.pygame.event.get", lambda: [])
    monkeypatch.setattr("src.ui_pygame.gui.combat_manager.pygame.display.flip", lambda: None)
    monkeypatch.setattr("src.ui_pygame.gui.combat_manager.pygame.time.Clock", lambda: DummyClock())
    manager.dungeon_renderer = SimpleNamespace(render_dungeon_view=lambda *_args, **_kwargs: None)
    manager.player_world_dict = {}
    manager.engine = SimpleNamespace(post_turn=post_turn, is_player_turn=lambda: True)
    manager.hud = DummyHud()

    manager._post_turn_processing(_make_player(), enemy)
    assert enemy.picture == "jester2.png"
    assert len(manager.combat_view.reload_calls) >= 6
    assert any(call[0] == "enemy" for call in manager.combat_view.render_calls)
    assert manager.combat_view.messages == ["Palette shift!"]
    assert flushes[-1][2] == ("Palette shift!",)


def test_show_slot_machine_reveal_returns_three_digits_and_renders(monkeypatch):
    manager = _make_manager(monkeypatch)
    player = _make_player()
    enemy = _make_enemy()

    frame_calls = []
    event_calls = []

    def slot_events():
        event_calls.append("poll")
        if len(event_calls) == 103:
            return [pygame.event.Event(pygame.KEYUP, key=pygame.K_SPACE)]
        if len(event_calls) == 104:
            return [pygame.event.Event(pygame.KEYDOWN, key=pygame.K_SPACE)]
        return []

    monkeypatch.setattr(
        "src.ui_pygame.gui.combat_manager.random.sample",
        lambda _deck, _count: ["AS", "2S", "3S"],
    )
    monkeypatch.setattr("src.ui_pygame.gui.combat_manager.pygame.event.get", slot_events)
    monkeypatch.setattr("src.ui_pygame.gui.combat_manager.pygame.display.flip", lambda: None)
    monkeypatch.setattr(
        "src.ui_pygame.gui.combat_manager.pygame.draw.rect", lambda *_args, **_kwargs: None
    )
    monkeypatch.setattr(
        "src.ui_pygame.gui.combat_manager.pygame.font.Font",
        lambda *_args, **_kwargs: RecordingFont(),
    )
    monkeypatch.setattr(
        "src.ui_pygame.gui.combat_manager.pygame.Surface",
        lambda size, *_args, **_kwargs: RecordingScreen(size),
    )
    monkeypatch.setattr("src.ui_pygame.gui.combat_manager.pygame.time.Clock", lambda: DummyClock())
    monkeypatch.setattr(
        manager, "_render_combat_frame", lambda *args, **kwargs: frame_calls.append((args, kwargs))
    )
    monkeypatch.setattr(manager, "_slot_symbol_surfaces", lambda: [])

    result = manager._show_slot_machine_reveal(player, enemy)

    assert result == "AS,2S,3S"
    assert frame_calls
    assert any(
        getattr(surface, "text", "") == "Press any key or click to continue"
        for surface, _position in manager.screen.blit_calls
    )
    assert any(
        getattr(surface, "text", "") == "Straight Flush"
        for surface, _position in manager.screen.blit_calls
    )
    assert len(event_calls) == 104


def test_slot_machine_result_labels_match_core_hands():
    assert (
        combat_manager.GUICombatManager._slot_machine_result_label("AS,2S,3S") == "Straight Flush"
    )
    assert combat_manager.GUICombatManager._slot_machine_result_label("AS,9S,KS") == "Flush"
    assert combat_manager.GUICombatManager._slot_machine_result_label("AH,2S,3D") == "Straight"
    assert combat_manager.GUICombatManager._slot_machine_result_label("AH,AD,AC") == "3 of a Kind"
    assert combat_manager.GUICombatManager._slot_machine_result_label("AH,AD,9C") == "Pair"
    assert combat_manager.GUICombatManager._slot_machine_result_label("AH,7D,9C") == "Chance"
    assert combat_manager.GUICombatManager._slot_machine_result_label("666") == "Death"
    assert combat_manager.GUICombatManager._slot_machine_result_label("777") == "3 of a Kind"
    assert combat_manager.GUICombatManager._slot_machine_result_label("345") == "Straight"
    assert combat_manager.GUICombatManager._slot_machine_result_label("121") == "Palindrome"
    assert combat_manager.GUICombatManager._slot_machine_result_label("112") == "Pairs"
    assert combat_manager.GUICombatManager._slot_machine_result_label("246") == "Evens"
    assert combat_manager.GUICombatManager._slot_machine_result_label("135") == "Odds"
    assert combat_manager.GUICombatManager._slot_machine_result_label("148") == "Chance"


def test_slot_machine_symbol_atlas_slices_ten_reel_images(monkeypatch):
    manager = _make_manager(monkeypatch)
    atlas = pygame.Surface((500, 200), pygame.SRCALPHA)
    atlas.fill((0, 0, 0, 0))
    pygame.draw.rect(atlas, (255, 0, 0, 255), pygame.Rect(12, 14, 30, 40))
    loads = []

    monkeypatch.setattr(
        "src.ui_pygame.gui.combat_manager.pygame.image.load",
        lambda path: loads.append(path) or atlas,
    )

    symbols = manager._slot_symbol_surfaces()

    assert len(symbols) == 10
    assert symbols[0].get_size() == (42, 52)
    assert all(symbol.get_size() == (100, 100) for symbol in symbols[1:])
    assert loads == [str(combat_manager.SLOT_SYMBOL_ATLAS)]
    assert manager._slot_symbol_surfaces() is symbols


def test_slot_machine_symbol_atlas_slices_full_deck(monkeypatch):
    manager = _make_manager(monkeypatch)
    atlas = pygame.Surface((1300, 400), pygame.SRCALPHA)
    atlas.fill((0, 0, 0, 0))
    pygame.draw.rect(atlas, (255, 0, 0, 255), pygame.Rect(12, 14, 30, 40))

    monkeypatch.setattr(
        "src.ui_pygame.gui.combat_manager.pygame.image.load",
        lambda _path: atlas,
    )

    symbols = manager._slot_symbol_surfaces()

    assert len(symbols) == 52
    assert symbols[0].get_size() == (42, 52)


def test_waitress_transition_and_preservation_helpers(monkeypatch):
    manager = _make_manager(monkeypatch)
    popup_calls = []

    class FakeNightHag2:
        pass

    class FakePopup:
        def __init__(self, presenter, message, show_buttons=False):
            self.message = message
            self.show_buttons = show_buttons

        def show(self, **kwargs):
            popup_calls.append((self.message, kwargs))

    monkeypatch.setattr(combat_manager.enemies, "NightHag2", FakeNightHag2)
    monkeypatch.setattr("src.ui_pygame.gui.confirmation_popup.ConfirmationPopup", FakePopup)

    enemy = FakeNightHag2()
    enemy.name = "Mad Waitress"
    enemy.health = SimpleNamespace(current=5, max=100)
    enemy.is_alive = lambda: enemy.health.current > 0

    manager._check_enemy_form_change(_make_player(), enemy)

    assert enemy._form_changed is True
    assert enemy.name == "Waitress"
    assert enemy.health.current == 0
    assert manager.combat_view.reload_calls == [enemy]
    assert manager.combat_view.enemy_deaths == [enemy]
    assert any("visibly changes form" in message for message in manager.combat_view.messages)
    assert any("turns her weapon on herself" in message for message in manager.combat_view.messages)
    assert popup_calls
    assert "visible form change" in popup_calls[0][0]
    assert popup_calls[0][1].get("flush_events") is True
    assert popup_calls[0][1].get("require_key_release") is True

    enemy2 = FakeNightHag2()
    enemy2._form_changed = False
    enemy2.health = SimpleNamespace(current=0, max=100)
    manager._preserve_waitress_for_transition(enemy2)
    assert enemy2.health.current == 1


def test_execute_action_handles_suppression_and_slot_machine_skill(monkeypatch):
    manager = _make_manager(monkeypatch)
    player = _make_player()
    enemy = _make_enemy()

    player.abilities_suppressed = lambda: True
    player.anti_magic_active = True
    assert manager._execute_action("Spells", player, enemy) is None
    assert "cannot cast spells because of the anti-magic field" in manager.combat_view.messages[-1]

    manager.combat_view.messages.clear()
    player.abilities_suppressed = lambda: False
    player.spellbook["Skills"]["Slot Machine"] = SimpleNamespace(name="Slot Machine")
    manager._select_skill = lambda _player, _enemy: "Slot Machine"
    manager._show_slot_machine_reveal = lambda _player, _enemy: "777"
    frame_calls = []
    manager._render_combat_frame = lambda *args, **kwargs: frame_calls.append((args, kwargs))
    monkeypatch.setattr("src.ui_pygame.gui.combat_manager.pygame.display.flip", lambda: None)

    def execute_action(action, choice=None, slot_machine_callback=None):
        assert frame_calls
        assert action == "Use Skill"
        assert choice == "Slot Machine"
        assert slot_machine_callback and slot_machine_callback(player, enemy) == "777"
        enemy.health.current = 11
        enemy.name = "Goblin King"
        return SimpleNamespace(message="Big hit!\nJackpot!", fled=False)

    manager.engine = SimpleNamespace(execute_action=execute_action)
    result = manager._execute_action("Skills", player, enemy)

    assert result == "action_taken"
    assert manager.combat_view.messages[-2:] == ["Big hit!", "Jackpot!"]
    assert manager.combat_view.enemy_damage_calls == [enemy]
    assert manager.combat_view.flash_calls == []
    assert manager.combat_view.reload_calls[-1] == enemy
    assert frame_calls[-1][0] == (player, enemy, [], -1)

    manager.combat_view.messages.clear()
    frame_calls.clear()
    manager._select_summon = lambda _player, _enemy: "Patagon"

    def execute_summon(action, choice=None, slot_machine_callback=None):
        assert action == "Summon"
        assert choice == "Patagon"
        assert slot_machine_callback is None
        return SimpleNamespace(message="Hero summons Patagon.", fled=False)

    manager.engine = SimpleNamespace(execute_action=execute_summon)
    enemy.health.current = 11
    assert manager._execute_action("Summon", player, enemy) == "action_taken"
    assert manager.combat_view.messages[-1] == "Hero summons Patagon."

    manager.combat_view.messages.clear()
    manager._select_companion_command = lambda _player, _enemy: "Pack Strike"

    def execute_companion(action, choice=None, slot_machine_callback=None):
        assert action == "Companion"
        assert choice == "Pack Strike"
        assert slot_machine_callback is None
        return SimpleNamespace(message="Hero orders their companion: Pack Strike.", fled=False)

    manager.engine = SimpleNamespace(execute_action=execute_companion)
    assert manager._execute_action("Companion", player, enemy) == "action_taken"
    assert manager.combat_view.messages[-1] == "Hero orders their companion: Pack Strike."

    manager.combat_view.messages.clear()
    promotion_kits.combat_state(player)["favored_enemy_bonus_logged"] = True

    def execute_favored_attack(action, choice=None, slot_machine_callback=None):
        assert action == "Attack"
        return SimpleNamespace(message="Hero attacks Goblin.", fled=False)

    manager.engine = SimpleNamespace(execute_action=execute_favored_attack)
    assert manager._execute_action("Attack", player, enemy) == "action_taken"
    assert manager.combat_view.messages == ["Hero attacks Goblin."]
    assert "favored_enemy_bonus_logged" not in promotion_kits.combat_state(player)

    manager.combat_view.messages.clear()
    promotion_kits.combat_state(player)["favored_enemy_bonus_logged"] = True

    def execute_favored_hit(action, choice=None, slot_machine_callback=None):
        assert action == "Attack"
        enemy.health.current -= 5
        return SimpleNamespace(message="Hero attacks Goblin.\nGoblin takes 5 damage.", fled=False)

    manager.engine = SimpleNamespace(execute_action=execute_favored_hit)
    assert manager._execute_action("Attack", player, enemy) == "action_taken"
    assert manager.combat_view.messages[:3] == [
        "Favored Enemy pressure guides the strike.",
        "Hero attacks Goblin.",
        "Goblin takes 5 damage.",
    ]


def test_execute_empty_shortcut_does_not_call_engine_or_spend_turn(monkeypatch):
    manager = _make_manager(monkeypatch)
    player = _make_player()
    enemy = _make_enemy()
    engine_calls = []
    manager.engine = SimpleNamespace(
        attacker=player,
        execute_action=lambda *args, **kwargs: engine_calls.append((args, kwargs)),
    )

    assert manager._execute_action("1. Empty", player, enemy) is None
    assert engine_calls == []
    assert manager.combat_view.messages == []


def test_timeline_keeps_defeated_badges_only_while_death_fade_runs(monkeypatch):
    manager = _make_manager(monkeypatch)
    fading = True
    manager.combat_view.death_animation_in_progress = lambda: fading
    player_entry = SimpleNamespace(actor_id="player")
    enemy_entry = SimpleNamespace(actor_id="enemy-a")
    manager._last_combat_timeline = (player_entry, enemy_entry, player_entry, enemy_entry)

    during_fade = manager._timeline_entries_for_frame((player_entry, player_entry))

    assert [entry.actor_id for entry in during_fade] == [
        "player",
        "enemy-a",
        "player",
        "enemy-a",
    ]

    fading = False
    after_fade = manager._timeline_entries_for_frame((player_entry, player_entry))

    assert after_fade == (player_entry, player_entry)


def test_execute_action_tame_skips_damage_animation_and_defers_nickname(monkeypatch):
    manager = _make_manager(monkeypatch)
    player = _make_player()
    enemy = _make_enemy("Giant Hornet", hp=(3, 10))
    manager._render_combat_frame = lambda *args, **kwargs: None
    manager._flush_result_frame = lambda *args, **kwargs: None
    damage_effects = []
    manager._show_combat_damage_effect = lambda *args, **kwargs: damage_effects.append(
        (args, kwargs)
    )
    manager._show_combat_heal_text = lambda *args, **kwargs: None
    monkeypatch.setattr("src.ui_pygame.gui.combat_manager.pygame.display.flip", lambda: None)

    def execute_action(action, choice=None, slot_machine_callback=None):
        assert action == "Tame"
        enemy.tamed_by_player = True
        enemy.health.current = 0
        player.tamed_companion = {
            "active": True,
            "name": "Giant Hornet",
            "enemy_class": "GiantHornet",
            "bond": 5,
            "companions": [
                {
                    "active": True,
                    "name": "Giant Hornet",
                    "enemy_class": "GiantHornet",
                    "bond": 5,
                }
            ],
            "active_index": 0,
        }
        return SimpleNamespace(message="Hero tames Giant Hornet.", fled=False, summon_started=False)

    manager.engine = SimpleNamespace(execute_action=execute_action)

    assert manager._execute_action("Tame", player, enemy) == "action_taken"
    assert damage_effects == []
    assert manager.combat_view.enemy_damage_calls == []
    assert player.tamed_companion.get("custom_name") is None
    assert manager.combat_view.messages == ["Hero tames Giant Hornet."]


def test_select_companion_command_shows_beast_master_orders(monkeypatch):
    manager = _make_manager(monkeypatch)
    player = _make_player()
    enemy = _make_enemy()
    player.cls = SimpleNamespace(name="Beast Master")
    player.tamed_companion = {"active": True, "name": "Wolf", "bond": 75}
    player.familiar = SimpleNamespace(name="Wolf", spec="Tamed", is_alive=lambda: True)
    player.spellbook["Skills"] = {
        name: SimpleNamespace(name=name, cost=0, passive=False, description=f"{name} desc")
        for name in ability_mechanics.BEAST_COMPANION_COMMANDS
    }

    rendered = []
    manager._clear_pending_input = lambda: True
    manager._render_combat_frame = lambda *_args, **_kwargs: None
    manager._render_described_selection_menu = (
        lambda title, options, selected, scroll_offset, descriptions: rendered.append(
            (title, list(options), list(descriptions))
        )
    )
    monkeypatch.setattr(
        "src.ui_pygame.gui.combat_manager.release_guard_allows_input",
        lambda *_args, **_kwargs: True,
    )
    monkeypatch.setattr("src.ui_pygame.gui.combat_manager.pygame.display.flip", lambda: None)
    event_batches = iter([[pygame.event.Event(pygame.KEYDOWN, key=pygame.K_RETURN)]])
    monkeypatch.setattr(
        "src.ui_pygame.gui.combat_manager.pygame.event.get", lambda: next(event_batches, [])
    )

    assert manager._select_companion_command(player, enemy) == "Pack Strike"
    assert rendered
    assert rendered[-1][0] == "Command Companion"
    assert rendered[-1][1] == list(ability_mechanics.BEAST_COMPANION_COMMANDS)


def test_execute_spell_flushes_result_log_before_damage_effect(monkeypatch):
    manager = _make_manager(monkeypatch)
    player = _make_player()
    enemy = _make_enemy(hp=(20, 20))
    order = []

    manager._select_spell = lambda _player, _enemy: "Firebolt"
    manager._flush_result_frame = lambda _player, _enemy: order.append("flush")
    manager._show_combat_damage_effect = lambda *_args, **_kwargs: order.append("effect")
    monkeypatch.setattr("src.ui_pygame.gui.combat_manager.pygame.display.flip", lambda: None)

    def execute_action(action, choice=None, slot_machine_callback=None):
        assert action == "Cast Spell"
        assert choice == "Firebolt"
        enemy.health.current = 7
        return SimpleNamespace(message="Hero damages Goblin for 13 hit points.", fled=False)

    manager.engine = SimpleNamespace(execute_action=execute_action)

    assert manager._execute_action("Spells", player, enemy) == "action_taken"
    assert order == ["flush", "effect", "flush"]
    assert manager.combat_view.messages[-1] == "Hero damages Goblin for 13 hit points."


def test_debug_auto_kill_action_requires_debug_mode(monkeypatch):
    manager = _make_manager(monkeypatch)
    player = _make_player()
    enemy = _make_enemy()

    manager.game.debug_mode = False
    assert manager._execute_action("Auto Kill", player, enemy) is None
    assert enemy.health.current == 20
    assert manager.combat_view.messages[-1] == "Auto Kill is only available in debug mode."

    manager.game.debug_mode = True
    assert manager._execute_action("Auto Kill", player, enemy) == "action_taken"
    assert enemy.health.current == 0
    assert manager.combat_view.messages[-1] == "Debug: Goblin defeated."
    assert manager.combat_view.enemy_damage_calls == [enemy]
    assert manager.combat_view.flash_calls == []


def test_handle_combat_end_victory_defeat_and_flee_paths(monkeypatch):
    manager = _make_manager(monkeypatch)
    player = _make_player()
    enemy = _make_enemy()
    popup_messages = []
    popup_kwargs = []

    class FakePopup:
        def __init__(self, presenter, message, show_buttons=False):
            popup_messages.append(message)

        def show(self, **kwargs):
            popup_messages.append("shown")
            popup_kwargs.append(kwargs)

    monkeypatch.setattr("src.ui_pygame.gui.confirmation_popup.ConfirmationPopup", FakePopup)
    monkeypatch.setattr("src.ui_pygame.gui.combat_manager.pygame.display.flip", lambda: None)
    monkeypatch.setattr("src.ui_pygame.gui.combat_manager.pygame.event.get", lambda: [])
    monkeypatch.setattr("src.ui_pygame.gui.combat_manager.pygame.time.Clock", lambda: DummyClock())
    render_calls = []
    monkeypatch.setattr(
        manager, "_render_combat_frame", lambda *args, **kwargs: render_calls.append((args, kwargs))
    )
    monkeypatch.setattr(manager, "_pause_with_events", lambda _ms: None)

    manager.engine = SimpleNamespace(
        flee=False,
        end_battle=lambda: SimpleNamespace(
            result="victory",
            message="Gold +5\nGiant Spider bond increased.\nQuest updated",
            level_up=True,
        ),
    )
    assert manager._handle_combat_end(player, enemy, fled=False) is True
    assert popup_messages[0].startswith("Victory! Goblin defeated!")
    assert "Giant Spider bond increased." in popup_messages[0]
    assert "bond grows by" not in popup_messages[0]
    assert manager.level_up_screen.calls == [(player, manager.game)]
    assert manager.combat_view.reset_calls == 1
    assert manager._combat_background is None
    assert popup_kwargs[0].get("flush_events") is True
    assert popup_kwargs[0].get("require_key_release") is True

    popup_messages.clear()
    manager.combat_view.reset_calls = 0
    render_calls.clear()
    manager.engine = SimpleNamespace(
        flee=False,
        end_battle=lambda: SimpleNamespace(result="defeat", message="You lost", level_up=False),
    )
    assert manager._handle_combat_end(player, enemy, fled=False) is False
    assert popup_messages[0] == "You have been defeated!"
    assert manager.combat_view.reset_calls == 1
    assert popup_kwargs[0].get("flush_events") is True
    assert popup_kwargs[0].get("require_key_release") is True
    assert render_calls == []

    popup_messages.clear()
    manager.combat_view.reset_calls = 0
    manager.engine = SimpleNamespace(
        flee=False,
        end_battle=lambda: SimpleNamespace(result="flee", message="Escaped", level_up=False),
    )
    assert manager._handle_combat_end(player, enemy, fled=True) is False
    assert manager.engine.flee is True
    assert popup_messages[0] == "You fled from combat!"

    popup_messages.clear()
    manager.combat_view.reset_calls = 0
    manager.game.debug_mode = True
    manager.engine = SimpleNamespace(
        flee=False,
        end_battle=lambda: SimpleNamespace(
            result="victory",
            message="Giant Spider bond increased.",
            level_up=False,
        ),
    )
    assert manager._handle_combat_end(player, enemy, fled=False) is True
    assert "Giant Spider bond increased." in popup_messages[0]


def test_tamed_combat_end_skips_death_fade_then_names_companion(monkeypatch):
    manager = _make_manager(monkeypatch)
    player = _make_player()
    enemy = _make_enemy("Giant Hornet", hp=(0, 10))
    enemy.tamed_by_player = True
    player.tamed_companion = {
        "active": True,
        "name": "Giant Hornet",
        "enemy_class": "GiantHornet",
        "species": "Hornet",
        "evolution": "Needle Drone",
        "special_ability": "Wingbeat",
        "bond": 5,
        "companions": [
            {
                "active": True,
                "name": "Giant Hornet",
                "enemy_class": "GiantHornet",
                "species": "Hornet",
                "evolution": "Needle Drone",
                "special_ability": "Wingbeat",
                "bond": 5,
            }
        ],
        "active_index": 0,
    }
    popup_messages = []

    class FakePopup:
        def __init__(self, _presenter, message, show_buttons=False):
            popup_messages.append(message)

        def show(self, **_kwargs):
            popup_messages.append("shown")

    class FakeCompanionNamingScreen:
        def __init__(self, _presenter, companion_name, species="", form="", special=""):
            popup_messages.append(f"name-screen:{companion_name}:{species}:{form}:{special}")

        def navigate(self, **_kwargs):
            popup_messages.append("name-screen-shown")
            return "Needle"

    monkeypatch.setattr("src.ui_pygame.gui.confirmation_popup.ConfirmationPopup", FakePopup)
    monkeypatch.setattr(
        "src.ui_pygame.gui.combat_manager.selection_special.CompanionNamingScreen",
        FakeCompanionNamingScreen,
    )
    monkeypatch.setattr("src.ui_pygame.gui.combat_manager.pygame.display.flip", lambda: None)
    monkeypatch.setattr("src.ui_pygame.gui.combat_manager.pygame.event.get", lambda: [])
    monkeypatch.setattr("src.ui_pygame.gui.combat_manager.pygame.time.Clock", lambda: DummyClock())
    render_calls = []
    monkeypatch.setattr(
        manager, "_render_combat_frame", lambda *args, **kwargs: render_calls.append((args, kwargs))
    )
    monkeypatch.setattr(manager, "_pause_with_events", lambda _ms: None)
    manager.engine = SimpleNamespace(
        flee=False,
        end_battle=lambda: SimpleNamespace(
            result="victory",
            message="Giant Hornet leaves the fight as a companion.",
            level_up=False,
        ),
    )

    assert manager._handle_combat_end(player, enemy, fled=False) is True
    assert popup_messages[0].startswith("Giant Hornet tamed!")
    assert "name-screen:Giant Hornet:Hornet:Stingwing:Wingbeat" in popup_messages
    assert popup_messages.index("shown") < popup_messages.index("name-screen-shown")
    assert player.familiar.name == "Needle (Giant Hornet)"
    assert len(render_calls) == 1
    assert manager.combat_view.reset_calls == 1


def test_jester_victory_runs_death_fade_before_dungeon_end_event(monkeypatch):
    manager = _make_manager(monkeypatch)
    player = _make_player()
    enemy = _make_enemy("Jester", hp=(0, 20))

    class JesterBossRoom:
        pass

    class FakePopup:
        def __init__(self, _presenter, message, show_buttons=False):
            popup_messages.append(message)

        def show(self, **_kwargs):
            popup_messages.append("shown")

    monkeypatch.setattr("src.ui_pygame.gui.confirmation_popup.ConfirmationPopup", FakePopup)
    monkeypatch.setattr("src.ui_pygame.gui.combat_manager.pygame.display.flip", lambda: None)
    monkeypatch.setattr("src.ui_pygame.gui.combat_manager.pygame.event.get", lambda: [])
    monkeypatch.setattr("src.ui_pygame.gui.combat_manager.pygame.time.Clock", lambda: DummyClock())
    render_calls = []
    event_order = []
    monkeypatch.setattr(
        manager,
        "_render_combat_frame",
        lambda *args, **kwargs: (
            render_calls.append((args, kwargs)),
            event_order.append("render"),
        ),
    )
    pauses = []
    monkeypatch.setattr(manager, "_pause_with_events", lambda ms: pauses.append(ms))
    popup_messages = []

    manager.current_tile = JesterBossRoom()

    def end_battle():
        event_order.append("bookkeeping")
        return SimpleNamespace(result="victory", message="Gold +5", level_up=False)

    manager.engine = SimpleNamespace(
        flee=False,
        end_battle=end_battle,
    )

    assert manager._handle_combat_end(player, enemy, fled=False) is True
    assert popup_messages[0].startswith("Victory! Jester defeated!")
    assert "Gold +5" in popup_messages[0]
    assert len(render_calls) == DEATH_ANIMATION_FRAMES
    assert event_order == ["render"] * DEATH_ANIMATION_FRAMES + ["bookkeeping"]
    assert pauses == [POST_DEATH_PAUSE_MS]
    assert manager.combat_view.reset_calls == 1
    assert manager._combat_background is None


def test_debug_battle_log_persistence_is_opt_in_and_sanitized(monkeypatch):
    manager = _make_manager(monkeypatch)
    manager.game.debug_mode = False
    manager.presenter.debug_mode = False

    exported = []
    manager.logger = SimpleNamespace(
        metadata={
            "player": {"name": "Ada Hero"},
            "enemy": {"name": "Slime/Blob"},
        },
        export_json_file=lambda path: exported.append(path) or path,
    )

    assert manager._persist_debug_battle_log("victory") is None
    assert exported == []

    manager.game.debug_mode = True
    output_path = manager._persist_debug_battle_log("victory")

    assert output_path is exported[0]
    assert output_path.parent.parts[-2:] == ("debug_logs", "battles")
    assert output_path.name.endswith("-ada-hero-vs-slime-blob-victory.json")


def test_debug_battle_log_persistence_ignores_export_errors(monkeypatch):
    manager = _make_manager(monkeypatch)
    manager.game.debug_mode = True
    manager.logger = SimpleNamespace(
        metadata={},
        export_json_file=lambda _path: (_ for _ in ()).throw(OSError("disk full")),
    )

    assert manager._persist_debug_battle_log("defeat") is None


def test_select_item_spell_and_skill_cover_empty_cancel_and_selection_paths(monkeypatch):
    manager = _make_manager(monkeypatch)
    player = _make_player()
    enemy = _make_enemy()

    pauses = []
    manager._pause_with_events = lambda ms: pauses.append(ms)
    manager._render_combat_frame = lambda *args, **kwargs: None
    menu_calls = []
    manager._render_selection_menu = (
        lambda title, options, selected, scroll_offset=0: menu_calls.append(
            (title, tuple(options), selected, scroll_offset)
        )
    )
    monkeypatch.setattr("src.ui_pygame.gui.combat_manager.pygame.display.flip", lambda: None)

    assert manager._select_item(player, enemy) is None
    assert manager.combat_view.messages[-1] == "No usable items!"
    assert pauses[-1] == 500

    player.inventory = {
        "Potion": [SimpleNamespace(name="Potion", subtyp="Health") for _ in range(2)],
        "Bomb": [SimpleNamespace(name="Bomb", subtyp="Throwing")],
        "Blank Scroll": [SimpleNamespace(name="Blank Scroll", subtyp="Scroll")],
        "Scroll": [
            SimpleNamespace(
                name="Scroll of Ice", subtyp="Scroll", spell=SimpleNamespace(name="Ice")
            )
        ],
    }
    pressed_states = iter([[1], [], [], []])
    monkeypatch.setattr(
        "src.ui_pygame.gui.input_guards.pygame.key.get_pressed", lambda: next(pressed_states, [])
    )
    event_batches = iter(
        [
            [SimpleNamespace(type=pygame.KEYDOWN, key=pygame.K_RETURN)],
            [SimpleNamespace(type=pygame.KEYDOWN, key=pygame.K_DOWN)],
            [SimpleNamespace(type=pygame.KEYDOWN, key=pygame.K_RETURN)],
        ]
    )
    monkeypatch.setattr(
        "src.ui_pygame.gui.combat_manager.pygame.event.get", lambda: next(event_batches, [])
    )
    selected_item = manager._select_item(player, enemy)
    assert selected_item.name == "Scroll of Ice"
    assert menu_calls[-2][1] == ("Potion (2)", "Scroll (1)")
    assert "Blank Scroll (1)" not in menu_calls[-2][1]
    assert menu_calls[-1][2] == 1

    monkeypatch.setattr("src.ui_pygame.gui.input_guards.pygame.key.get_pressed", lambda: [])
    click_pos = manager._selection_menu_option_rects(["Potion (2)", "Scroll (1)"], 0)[1][1].center
    event_batches = iter(
        [
            [SimpleNamespace(type=pygame.MOUSEMOTION, pos=click_pos)],
            [SimpleNamespace(type=pygame.MOUSEBUTTONDOWN, button=1, pos=click_pos)],
        ]
    )
    monkeypatch.setattr(
        "src.ui_pygame.gui.combat_manager.pygame.event.get", lambda: next(event_batches, [])
    )
    selected_item = manager._select_item(player, enemy)
    assert selected_item.name == "Scroll of Ice"

    player.inventory = {
        f"Potion {index}": [SimpleNamespace(name=f"Potion {index}", subtyp="Health")]
        for index in range(4)
    }
    item_options = [f"Potion {index} (1)" for index in range(4)]
    fourth_item_pos = manager._selection_menu_option_rects(item_options, 1)[2][1].center
    event_batches = iter(
        [
            [SimpleNamespace(type=pygame.MOUSEWHEEL, y=-3)],
            [SimpleNamespace(type=pygame.MOUSEBUTTONDOWN, button=1, pos=fourth_item_pos)],
        ]
    )
    monkeypatch.setattr(
        "src.ui_pygame.gui.combat_manager.pygame.event.get", lambda: next(event_batches, [])
    )
    selected_item = manager._select_item(player, enemy)
    assert selected_item.name == "Potion 3"

    back_pos = manager._selection_menu_back_rect().center
    event_batches = iter([[SimpleNamespace(type=pygame.MOUSEBUTTONDOWN, button=1, pos=back_pos)]])
    monkeypatch.setattr(
        "src.ui_pygame.gui.combat_manager.pygame.event.get", lambda: next(event_batches, [])
    )
    assert manager._select_item(player, enemy) is None

    event_batches = iter(
        [
            [SimpleNamespace(type=pygame.KEYUP, key=pygame.K_ESCAPE)],
            [SimpleNamespace(type=pygame.KEYDOWN, key=pygame.K_ESCAPE)],
        ]
    )
    monkeypatch.setattr(
        "src.ui_pygame.gui.combat_manager.pygame.event.get", lambda: next(event_batches, [])
    )
    assert manager._select_item(player, enemy) is None

    player.spellbook["Spells"] = {}
    assert manager._select_spell(player, enemy) is None
    assert manager.combat_view.messages[-1] == "No spells learned!"

    player.spellbook["Spells"] = {
        "Passive Aura": SimpleNamespace(cost=0, passive=True),
        "Fireball": SimpleNamespace(cost=4, passive=False),
        "Ice": SimpleNamespace(cost=2, passive=False),
        "Resist Shadow": SimpleNamespace(
            cost=1,
            passive=False,
            exploration_cast=True,
        ),
    }
    monkeypatch.setattr("src.ui_pygame.gui.input_guards.pygame.key.get_pressed", lambda: [])
    event_batches = iter(
        [
            [SimpleNamespace(type=pygame.KEYDOWN, key=pygame.K_DOWN)],
            [SimpleNamespace(type=pygame.KEYDOWN, key=pygame.K_RETURN)],
        ]
    )
    monkeypatch.setattr(
        "src.ui_pygame.gui.combat_manager.pygame.event.get", lambda: next(event_batches, [])
    )
    assert manager._select_spell(player, enemy) == "Ice"
    assert any(call[0] == "Select Spell" for call in menu_calls)

    stolen_scroll = items.InscribedSpellScroll("Firebolt", charges=2)
    player.inventory = {stolen_scroll.name: [stolen_scroll]}
    event_batches = iter(
        [
            [SimpleNamespace(type=pygame.KEYDOWN, key=pygame.K_PAGEDOWN)],
            [SimpleNamespace(type=pygame.KEYDOWN, key=pygame.K_RETURN)],
        ]
    )
    monkeypatch.setattr(
        "src.ui_pygame.gui.combat_manager.pygame.event.get", lambda: next(event_batches, [])
    )
    assert (
        manager._select_spell(player, enemy)
        == f"{combat_manager.STOLEN_SCROLL_CHOICE_PREFIX}{stolen_scroll.name}"
    )
    assert menu_calls[-1][1] == (
        "Fireball (MP: 4)",
        "Ice (MP: 2)",
        f"{stolen_scroll.name} (Scroll)",
    )

    click_pos = manager._selection_menu_option_rects(menu_calls[-1][1], 0)[2][1].center
    event_batches = iter(
        [
            [SimpleNamespace(type=pygame.MOUSEBUTTONDOWN, button=1, pos=click_pos)],
        ]
    )
    monkeypatch.setattr(
        "src.ui_pygame.gui.combat_manager.pygame.event.get", lambda: next(event_batches, [])
    )
    assert (
        manager._select_spell(player, enemy)
        == f"{combat_manager.STOLEN_SCROLL_CHOICE_PREFIX}{stolen_scroll.name}"
    )

    player.spellbook["Skills"] = {}
    assert manager._select_skill(player, enemy) is None
    assert manager.combat_view.messages[-1] == "No skills learned!"

    player.equipment = {"OffHand": SimpleNamespace(subtyp="None")}
    player.spellbook["Skills"] = {
        "Shield Slam": SimpleNamespace(name="Shield Slam", cost=2, passive=False),
    }
    assert manager._select_skill(player, enemy) is None
    assert manager.combat_view.messages[-1] == "No skills learned!"

    player.equipment = {"OffHand": SimpleNamespace(subtyp="Shield")}
    player.spellbook["Skills"]["Brace Wall"] = abilities.BraceWall()
    event_batches = iter([[SimpleNamespace(type=pygame.KEYDOWN, key=pygame.K_RETURN)]])
    monkeypatch.setattr(
        "src.ui_pygame.gui.combat_manager.pygame.event.get", lambda: next(event_batches, [])
    )
    assert manager._select_skill(player, enemy) == "Shield Slam"
    assert menu_calls[-1][1] == ("Shield Slam (MP: 2)",)

    event_batches = iter([[SimpleNamespace(type=pygame.KEYDOWN, key=pygame.K_RETURN)]])
    monkeypatch.setattr(
        "src.ui_pygame.gui.combat_manager.pygame.event.get", lambda: next(event_batches, [])
    )
    assert manager._select_resolve_ability(player, enemy) == "Brace Wall"
    assert menu_calls[-1][0] == "Select Resolve"
    assert menu_calls[-1][1] == ("Brace Wall (Resolve: 15)",)

    player.cls = SimpleNamespace(name="Stalwart Defender")
    player.spellbook["Skills"]["Citadel Aegis"] = abilities.CitadelAegis()
    state = class_rings.ensure_state(player)["data"]["Stalwart Defender"]
    state["guard_meter"] = 100
    state["resolve_mastery"]["citadel_aegis"] = 4
    event_batches = iter(
        [
            [SimpleNamespace(type=pygame.KEYDOWN, key=pygame.K_RETURN)],
        ]
    )
    monkeypatch.setattr(
        "src.ui_pygame.gui.combat_manager.pygame.event.get",
        lambda: next(event_batches, []),
    )
    assert (
        manager._select_resolve_ability(
            player,
            enemy,
            bursts=True,
        )
        == "Citadel Aegis"
    )
    assert menu_calls[-1][0] == "Select Resolve Burst"
    assert menu_calls[-1][1] == ("Citadel Aegis (Full Resolve)",)

    player.cls = SimpleNamespace(name="Paladin")
    player.paladin_vow = "Conquest"
    player.spellbook["Skills"] = {
        "Oath's Judgment": abilities.OathsJudgment(),
    }
    promotion_kits.combat_state(player)["oath_conviction"] = 2
    event_batches = iter(
        [
            [SimpleNamespace(type=pygame.KEYDOWN, key=pygame.K_RETURN)],
        ]
    )
    monkeypatch.setattr(
        "src.ui_pygame.gui.combat_manager.pygame.event.get",
        lambda: next(event_batches, []),
    )
    assert manager._select_skill(player, enemy) == "Oath's Judgment"
    assert menu_calls[-1][1] == ("Oath's Judgment (Conviction: all 2)",)

    player.is_disarmed = lambda: True
    player.spellbook["Skills"] = {
        "Piercing Strike": SimpleNamespace(
            name="Piercing Strike", cost=5, passive=False, weapon=True
        ),
        "Smoke Screen": SimpleNamespace(name="Smoke Screen", cost=1, passive=False, weapon=False),
    }
    event_batches = iter([[SimpleNamespace(type=pygame.KEYDOWN, key=pygame.K_RETURN)]])
    monkeypatch.setattr(
        "src.ui_pygame.gui.combat_manager.pygame.event.get", lambda: next(event_batches, [])
    )
    assert manager._select_skill(player, enemy) == "Smoke Screen"
    assert menu_calls[-1][1] == ("Smoke Screen (MP: 1)",)
    player.is_disarmed = lambda: False

    player.cls = SimpleNamespace(name="Cleric")
    player.spellbook["Skills"] = {"Sanctuary Ward": abilities.SanctuaryWard()}
    assert manager._available_skill_names(player, enemy) == []
    promotion_kits.gain_meter(player, "devotion", 1, "test")
    assert manager._available_skill_names(player, enemy) == ["Sanctuary Ward"]

    player.cls = SimpleNamespace(name="Ranger")
    player.spellbook["Skills"] = {
        "Tame": abilities.Tame(),
        "Favored Enemy": abilities.FavoredEnemy(),
    }
    assert manager._available_skill_names(player, enemy) == ["Favored Enemy"]

    player.equipment = {
        "Weapon": SimpleNamespace(subtyp="Polearm"),
        "OffHand": SimpleNamespace(subtyp="None"),
    }
    player.spellbook["Skills"] = {
        "Reaver's Mark": SimpleNamespace(name="Reaver's Mark", cost=9, passive=False, weapon=True),
        "Brace": SimpleNamespace(name="Brace", cost=8, passive=False, weapon=True),
    }
    event_batches = iter([[SimpleNamespace(type=pygame.KEYDOWN, key=pygame.K_RETURN)]])
    monkeypatch.setattr(
        "src.ui_pygame.gui.combat_manager.pygame.event.get", lambda: next(event_batches, [])
    )
    assert manager._select_skill(player, enemy) == "Brace"
    assert menu_calls[-1][1] == ("Brace (MP: 8)",)

    enemy.incapacitated = lambda: False
    player.spellbook["Skills"] = {
        "Backstab": SimpleNamespace(
            name="Backstab", cost=4, passive=False, _requires_incapacitated=True
        ),
        "Slash": SimpleNamespace(name="Slash", cost=1, passive=False),
    }
    event_batches = iter([[SimpleNamespace(type=pygame.KEYDOWN, key=pygame.K_RETURN)]])
    monkeypatch.setattr(
        "src.ui_pygame.gui.combat_manager.pygame.event.get", lambda: next(event_batches, [])
    )
    assert manager._select_skill(player, enemy) == "Slash"
    assert menu_calls[-1][1] == ("Slash (MP: 1)",)

    player.summons = {}
    assert manager._select_summon(player, enemy) is None
    assert manager.combat_view.messages[-1] == "No summons available!"

    player.summons = {
        "Spent": SimpleNamespace(name="Spent", is_alive=lambda: False),
        "Patagon": SimpleNamespace(
            name="Patagon", level=SimpleNamespace(level=1), is_alive=lambda: True
        ),
    }
    event_batches = iter([[SimpleNamespace(type=pygame.KEYDOWN, key=pygame.K_RETURN)]])
    monkeypatch.setattr(
        "src.ui_pygame.gui.combat_manager.pygame.event.get", lambda: next(event_batches, [])
    )
    assert manager._select_summon(player, enemy) == "Patagon"
    assert menu_calls[-1][0] == "Select Summon"
    assert menu_calls[-1][1] == ("Patagon (Lv 1)",)

    enemy.incapacitated = lambda: True
    event_batches = iter([[SimpleNamespace(type=pygame.KEYDOWN, key=pygame.K_RETURN)]])
    monkeypatch.setattr(
        "src.ui_pygame.gui.combat_manager.pygame.event.get", lambda: next(event_batches, [])
    )
    assert manager._select_skill(player, enemy) == "Backstab"
    assert menu_calls[-1][1] == ("Backstab (MP: 4)", "Slash (MP: 1)")

    player.spellbook["Skills"] = {
        "Passive Stance": SimpleNamespace(cost=0, passive=True),
        "Slash": SimpleNamespace(cost=1, passive=False),
        "Jump": SimpleNamespace(cost=3, passive=False),
    }
    monkeypatch.setattr("src.ui_pygame.gui.input_guards.pygame.key.get_pressed", lambda: [])
    event_batches = iter(
        [
            [SimpleNamespace(type=pygame.KEYDOWN, key=pygame.K_PAGEDOWN)],
            [SimpleNamespace(type=pygame.KEYDOWN, key=pygame.K_RETURN)],
        ]
    )
    monkeypatch.setattr(
        "src.ui_pygame.gui.combat_manager.pygame.event.get", lambda: next(event_batches, [])
    )
    assert manager._select_skill(player, enemy) == "Jump"


def test_select_totem_aspect_ignores_stale_confirm_until_key_release(monkeypatch):
    manager = _make_manager(monkeypatch)
    player = _make_player()
    enemy = _make_enemy()
    manager._render_combat_frame = lambda *args, **kwargs: None
    menu_calls = []
    manager._render_selection_menu = (
        lambda title, options, selected, scroll_offset=0: menu_calls.append(
            (title, tuple(options), selected, scroll_offset)
        )
    )
    monkeypatch.setattr("src.ui_pygame.gui.combat_manager.pygame.display.flip", lambda: None)
    clear_calls = []
    monkeypatch.setattr(
        "src.ui_pygame.gui.combat_manager.pygame.event.clear", lambda: clear_calls.append(True)
    )
    pressed_states = iter([[1], [], [], []])
    monkeypatch.setattr(
        "src.ui_pygame.gui.input_guards.pygame.key.get_pressed", lambda: next(pressed_states, [])
    )
    event_batches = iter(
        [
            [SimpleNamespace(type=pygame.KEYDOWN, key=pygame.K_RETURN)],
            [SimpleNamespace(type=pygame.KEYDOWN, key=pygame.K_DOWN)],
            [SimpleNamespace(type=pygame.KEYDOWN, key=pygame.K_RETURN)],
        ]
    )
    monkeypatch.setattr(
        "src.ui_pygame.gui.combat_manager.pygame.event.get", lambda: next(event_batches, [])
    )
    totem = SimpleNamespace(
        active_aspect="Wolf",
        get_unlocked_aspects=lambda _player: ["Wolf", "Bear"],
    )

    assert manager._select_totem_aspect(player, enemy, totem) == "Bear"
    assert clear_calls == [True]
    assert menu_calls[0][1] == ("Wolf (Active)", "Bear")


def test_runic_steal_and_contract_pickers_support_mouse_confirm(monkeypatch):
    manager = _make_manager(monkeypatch)
    player = _make_player()
    enemy = _make_enemy()
    manager._render_combat_frame = lambda *args, **kwargs: None
    manager._render_selection_menu = lambda *_args, **_kwargs: None
    manager._pause_with_events = lambda _ms: None
    manager._clear_pending_input = lambda: True
    monkeypatch.setattr("src.ui_pygame.gui.combat_manager.pygame.display.flip", lambda: None)
    monkeypatch.setattr("src.ui_pygame.gui.input_guards.pygame.key.get_pressed", lambda: [])

    player.spellbook["Spells"] = {
        "Fire": SimpleNamespace(cost=3, subtyp="Damage"),
        "Ice": SimpleNamespace(cost=2, subtyp="Damage"),
    }
    monkeypatch.setattr(
        combat_manager.astromancer, "boostable_spells", lambda _player: ["Fire", "Ice"]
    )
    monkeypatch.setattr(combat_manager.astromancer, "sign_for_spell", lambda _spell: "Solar")
    runic_options = ["Solar: Fire (MP: 3)", "Solar: Ice (MP: 2)"]
    click_pos = manager._selection_menu_option_rects(runic_options, 0)[1][1].center
    event_batches = iter(
        [
            [SimpleNamespace(type=pygame.MOUSEBUTTONDOWN, button=1, pos=click_pos)],
        ]
    )
    monkeypatch.setattr(
        "src.ui_pygame.gui.combat_manager.pygame.event.get", lambda: next(event_batches, [])
    )
    assert manager._select_runic_boost_spell(player, enemy) == "Ice"

    steal_options = ["Fire", "Ice"]
    click_pos = manager._selection_menu_option_rects(steal_options, 0)[1][1].center
    event_batches = iter(
        [
            [SimpleNamespace(type=pygame.MOUSEBUTTONDOWN, button=1, pos=click_pos)],
        ]
    )
    monkeypatch.setattr(
        "src.ui_pygame.gui.combat_manager.pygame.event.get", lambda: next(event_batches, [])
    )
    assert manager._select_steal_as_well_spell(player, enemy) == "Ice"

    intents = ["Wound", "Guard"]
    click_pos = manager._selection_menu_option_rects(intents, 0)[1][1].center
    monkeypatch.setattr(combat_manager.demonologist, "available_intents", lambda _player: intents)
    monkeypatch.setattr(
        combat_manager.demonologist,
        "quote_contract",
        lambda _player, _enemy, intent: {
            "ok": True,
            "patron": "A fiend",
            "costs": {"gold": 3},
            "misbehavior_chance": 0.2,
        },
    )
    monkeypatch.setattr(combat_manager.demonologist, "can_pay_quote", lambda _player, _quote: True)
    manager.presenter.render_menu = lambda prompt, options: 0
    event_batches = iter(
        [
            [SimpleNamespace(type=pygame.MOUSEBUTTONDOWN, button=1, pos=click_pos)],
        ]
    )
    monkeypatch.setattr(
        "src.ui_pygame.gui.combat_manager.pygame.event.get", lambda: next(event_batches, [])
    )
    assert manager._select_contract_intent(player, enemy) == "Guard"


def test_all_actions_supports_mouse_wheel_scrolling_and_selection(monkeypatch):
    manager = _make_manager(monkeypatch)
    player = _make_player()
    enemy = _make_enemy()
    entries = tuple(
        SimpleNamespace(display_label=f"Action {index}", description=f"Description {index}")
        for index in range(4)
    )
    renders = []
    manager._render_combat_frame = lambda *_args, **_kwargs: None
    manager._render_selection_menu = (
        lambda _title, _options, selected, scroll_offset=0: renders.append(
            (selected, scroll_offset)
        )
    )
    manager._clear_pending_input = lambda: True
    monkeypatch.setattr(
        combat_manager.lifecycle,
        "combat_interface_snapshot",
        lambda *_args: SimpleNamespace(all_actions=entries),
    )
    monkeypatch.setattr("src.ui_pygame.gui.combat_manager.pygame.display.flip", lambda: None)
    fourth_action_pos = manager._selection_menu_option_rects(
        [entry.display_label for entry in entries], 1
    )[2][1].center
    event_batches = iter(
        [
            [SimpleNamespace(type=pygame.MOUSEWHEEL, y=-3)],
            [SimpleNamespace(type=pygame.MOUSEBUTTONDOWN, button=1, pos=fourth_action_pos)],
        ]
    )
    monkeypatch.setattr(
        "src.ui_pygame.gui.combat_manager.pygame.event.get", lambda: next(event_batches, [])
    )

    assert manager._select_all_action(player, enemy) is entries[3]
    assert renders[-1] == (3, 1)


def test_render_selection_menu_refresh_background_and_pause_helpers(monkeypatch):
    manager = _make_manager(monkeypatch)
    player = _make_player()
    enemy = _make_enemy()

    large_font = RecordingFont()
    medium_font = RecordingFont()
    small_font = RecordingFont()
    fonts = iter([large_font, medium_font, small_font])

    monkeypatch.setattr(
        "src.ui_pygame.gui.combat_manager.pygame.font.Font", lambda *_args, **_kwargs: next(fonts)
    )
    monkeypatch.setattr(
        "src.ui_pygame.gui.combat_manager.pygame.Surface",
        lambda size, *_args, **_kwargs: DummySurface(size),
    )
    draw_calls = []
    monkeypatch.setattr(
        "src.ui_pygame.gui.combat_manager.pygame.draw.rect",
        lambda *_args, **_kwargs: draw_calls.append((_args, _kwargs)),
    )
    monkeypatch.setattr("src.ui_pygame.gui.combat_manager.pygame.display.flip", lambda: None)

    long_options = [
        f"Option {index} with very long descriptive text that should truncate"
        for index in range(15)
    ]
    manager._selection_menu_descriptions = [""] * 13 + ["Selected option description"] + [""]
    manager._render_selection_menu("Choose Action", long_options, selected=13, scroll_offset=99)

    assert "Choose Action" in large_font.render_calls
    fitted_option = next(
        text for text in medium_font.render_calls if text.startswith("13. Option 12")
    )
    assert fitted_option.endswith("...")
    assert medium_font.size(fitted_option)[0] <= 462
    assert "Selected option description" in small_font.render_calls
    assert "Back" in small_font.render_calls
    assert (
        "Wheel: Scroll | PgUp/PgDn: Scroll | Enter: Select | Esc: Cancel" in small_font.render_calls
    )
    assert draw_calls

    manager._combat_background = None
    manager._render_combat_frame = lambda *args, **kwargs: manager.screen.blit(
        "combat-frame", (1, 2)
    )
    manager._refresh_combat_background(player, enemy)
    assert str(manager._combat_background).startswith("screen-copy-")

    scroll_events = [
        pygame.event.Event(pygame.KEYDOWN, key=pygame.K_PAGEUP),
        pygame.event.Event(pygame.QUIT),
    ]
    event_batches = iter([[scroll_events[0]], []])
    clock = DummyClock(frame_ms=300)
    monkeypatch.setattr(
        "src.ui_pygame.gui.combat_manager.pygame.event.get", lambda: next(event_batches, [])
    )
    monkeypatch.setattr("src.ui_pygame.gui.combat_manager.pygame.time.Clock", lambda: clock)
    manager._pause_with_events(500)
    assert manager.combat_view.scrolled[-1] == -1
    assert clock.ticks == [60, 60]


def test_start_combat_handles_initiative_and_sanctuary_escape(monkeypatch):
    manager = _make_manager(monkeypatch)
    player = _make_player()
    enemy = _make_enemy()
    tile = SimpleNamespace()

    player.world_dict = {"z": {}}
    player.encumbered = True
    player.in_town = lambda: False

    end_calls = []
    fake_engine = SimpleNamespace(
        available_actions=["Attack"],
        start_battle=lambda: (enemy, player),
        battle_continues=lambda: True,
        is_player_turn=lambda: True,
        swap_turns=lambda: end_calls.append("swap"),
        player=player,
    )

    monkeypatch.setattr(combat_manager.lifecycle, "BattleEngine", lambda **kwargs: fake_engine)
    monkeypatch.setattr("src.ui_pygame.gui.combat_manager.pygame.display.flip", lambda: None)
    monkeypatch.setattr("src.ui_pygame.gui.combat_manager.pygame.event.get", lambda: [])
    monkeypatch.setattr("src.ui_pygame.gui.combat_manager.pygame.time.Clock", lambda: DummyClock())
    monkeypatch.setattr(manager, "_render_combat_frame", lambda *args, **kwargs: None)
    monkeypatch.setattr(manager, "_player_turn", lambda _player, _enemy: "flee")
    monkeypatch.setattr(
        manager,
        "_handle_combat_end",
        lambda _player, _enemy, fled: end_calls.append(("end", fled)) or False,
    )

    result = manager.start_combat(player, enemy, tile)

    assert result is False
    assert manager.current_tile is tile
    assert manager.player_world_dict == player.world_dict
    assert "Combat started with Goblin!" in manager.combat_view.messages
    assert "You are ENCUMBERED! Enemy strikes first!" in manager.combat_view.messages
    assert "Goblin has the initiative!" in manager.combat_view.messages
    assert end_calls == [("end", True)]

    sanctuary_manager = _make_manager(monkeypatch)
    sanctuary_player = _make_player()
    sanctuary_player.in_town = lambda: True
    sanctuary_player.effects = lambda end=False: end_calls.append(("effects", end))
    sanctuary_manager.logger = SimpleNamespace(
        end_battle=lambda **kwargs: end_calls.append(("logger", kwargs))
    )
    sanctuary_manager.engine = SimpleNamespace(flee=False)
    sanctuary_manager._combat_background = "cached"
    sanctuary_manager.combat_view.reset_calls = 0

    assert sanctuary_manager._handle_combat_end(sanctuary_player, enemy, fled=False) is False
    assert ("effects", True) in end_calls
    assert any(
        call[0] == "logger" and call[1]["result"] == "Escaped"
        for call in end_calls
        if isinstance(call, tuple)
    )
    assert sanctuary_manager.combat_view.reset_calls == 1
    assert sanctuary_manager._combat_background is None


def test_render_combat_frame_waits_for_initiative_before_turn_label(monkeypatch):
    manager = _make_manager(monkeypatch)
    player = _make_player()
    enemy = _make_enemy()

    turn_calls = []
    manager.engine = SimpleNamespace(attacker=None, is_player_turn=lambda: True)
    manager.dungeon_renderer = None
    manager.player_world_dict = None
    manager.combat_view.render_enemy_in_dungeon = lambda *_args, **_kwargs: None
    manager.combat_view.render_combat_overlay = lambda *_args, **kwargs: turn_calls.append(
        kwargs.get("current_turn")
    )
    manager.hud.render_hud = lambda *_args, **_kwargs: None

    manager._render_combat_frame(player, enemy, [], -1)

    assert turn_calls == [None]


def test_player_turn_covers_preturn_forced_actions_and_grid_selection(monkeypatch):
    manager = _make_manager(monkeypatch)
    player = _make_player()
    enemy = _make_enemy()

    manager._render_combat_frame = lambda *args, **kwargs: None
    flushed_messages = []
    manager._flush_result_frame = lambda *_args: flushed_messages.append(
        tuple(manager.combat_view.messages)
    )
    monkeypatch.setattr("src.ui_pygame.gui.combat_manager.pygame.display.flip", lambda: None)

    manager.engine = SimpleNamespace(
        pre_turn=lambda: SimpleNamespace(
            effects_text="Poison ticks", died_from_effects=True, can_act=True, inactive_reason=""
        ),
    )
    assert manager._player_turn(player, enemy) is True
    assert manager.combat_view.messages[-1] == "Poison ticks"
    assert flushed_messages[-1] == ("Poison ticks",)

    manager.engine = SimpleNamespace(
        pre_turn=lambda: SimpleNamespace(
            effects_text="", died_from_effects=False, can_act=False, inactive_reason="Asleep"
        ),
    )
    assert manager._player_turn(player, enemy) is True
    assert manager.combat_view.messages[-1] == "Asleep"
    assert flushed_messages[-1][-1] == "Asleep"

    forced = SimpleNamespace(action="Cancelled", cancel_message="Jump failed", choice=None)
    manager.engine = SimpleNamespace(
        pre_turn=lambda: SimpleNamespace(
            effects_text="", died_from_effects=False, can_act=True, inactive_reason=""
        ),
        get_forced_action=lambda: forced,
    )
    assert manager._player_turn(player, enemy) is True
    assert manager.combat_view.messages[-1] == "Jump failed"

    enemy.health.current = 12
    forced = SimpleNamespace(action="Attack", cancel_message="", choice=None)
    manager.engine = SimpleNamespace(
        pre_turn=lambda: SimpleNamespace(
            effects_text="", died_from_effects=False, can_act=True, inactive_reason=""
        ),
        get_forced_action=lambda: forced,
        execute_action=lambda action, choice=None: SimpleNamespace(message="Hit hard", fled=False),
        companion_turn=lambda: None,
    )
    assert manager._player_turn(player, enemy) is True
    assert any("BERSERKED" in message for message in manager.combat_view.messages)

    actions = []
    manager.available_actions = ["Attack", "Defend", "Items", "Spells"]
    manager.engine = SimpleNamespace(
        pre_turn=lambda: SimpleNamespace(
            effects_text="", died_from_effects=False, can_act=True, inactive_reason=""
        ),
        get_forced_action=lambda: None,
        companion_turn=lambda: "Fairy assists",
    )
    manager._execute_action = (
        lambda action, _player, _enemy: actions.append(action) or "action_taken"
    )
    pressed_states = iter([[1], [], [], []])
    monkeypatch.setattr(
        "src.ui_pygame.gui.input_guards.pygame.key.get_pressed", lambda: next(pressed_states, [])
    )
    event_batches = iter(
        [
            [SimpleNamespace(type=pygame.KEYDOWN, key=pygame.K_RETURN)],
            [SimpleNamespace(type=pygame.KEYDOWN, key=pygame.K_RIGHT)],
            [SimpleNamespace(type=pygame.KEYDOWN, key=pygame.K_RETURN)],
        ]
    )
    monkeypatch.setattr(
        "src.ui_pygame.gui.combat_manager.pygame.event.get", lambda: next(event_batches, [])
    )
    assert manager._player_turn(player, enemy) is True
    assert actions == ["Defend"]

    manager.available_actions = [
        "1. Skill: Strike",
        "2. Skill: Guard",
        "3. Spell: Spark",
        "4. Spell: Ward",
        "5. Empty",
        "6. Empty",
        "Attack",
        "Flee",
    ]
    actions.clear()
    event_batches = iter(
        [
            [SimpleNamespace(type=pygame.KEYDOWN, key=pygame.K_UP)],
            [SimpleNamespace(type=pygame.KEYDOWN, key=pygame.K_RETURN)],
        ]
    )
    monkeypatch.setattr(
        "src.ui_pygame.gui.combat_manager.pygame.event.get", lambda: next(event_batches, [])
    )
    assert manager._player_turn(player, enemy) is True
    assert actions == ["Attack"]
    assert manager.combat_view.messages[-1] == "Fairy assists"

    actions.clear()
    monkeypatch.setattr("src.ui_pygame.gui.input_guards.pygame.key.get_pressed", lambda: [])
    shortcut_rect = manager._combat_action_rects(manager.available_actions)[1]
    event_batches = iter(
        [
            [
                SimpleNamespace(
                    type=pygame.FINGERUP,
                    x=shortcut_rect.centerx / manager.screen.get_width(),
                    y=shortcut_rect.centery / manager.screen.get_height(),
                )
            ]
        ]
    )
    monkeypatch.setattr(
        "src.ui_pygame.gui.combat_manager.pygame.event.get", lambda: next(event_batches, [])
    )
    assert manager._player_turn(player, enemy) is True
    assert actions == ["2. Skill: Guard"]

    manager.available_actions = ["Attack", "Defend", "Items"]
    actions.clear()
    monkeypatch.setattr("src.ui_pygame.gui.input_guards.pygame.key.get_pressed", lambda: [])
    event_batches = iter(
        [
            [SimpleNamespace(type=pygame.KEYDOWN, key=pygame.K_3)],
        ]
    )
    monkeypatch.setattr(
        "src.ui_pygame.gui.combat_manager.pygame.event.get", lambda: next(event_batches, [])
    )
    assert manager._player_turn(player, enemy) is True
    assert actions == ["Items"]

    manager.available_actions = ["Attack", "Defend", "Items"]
    actions.clear()
    click_pos = manager._combat_action_rects(manager.available_actions)[1].center
    event_batches = iter(
        [
            [SimpleNamespace(type=pygame.MOUSEMOTION, pos=click_pos)],
            [SimpleNamespace(type=pygame.MOUSEBUTTONDOWN, button=1, pos=click_pos)],
        ]
    )
    monkeypatch.setattr(
        "src.ui_pygame.gui.combat_manager.pygame.event.get", lambda: next(event_batches, [])
    )
    assert manager._player_turn(player, enemy) is True
    assert actions == ["Defend"]


def test_player_turn_accepts_first_fresh_key_after_guard_pumps_state(monkeypatch):
    manager = _make_manager(monkeypatch)
    player = _make_player()
    enemy = _make_enemy()

    manager._render_combat_frame = lambda *args, **kwargs: None
    flushed_messages = []
    manager._flush_result_frame = lambda *_args: flushed_messages.append(
        tuple(manager.combat_view.messages)
    )
    monkeypatch.setattr("src.ui_pygame.gui.combat_manager.pygame.display.flip", lambda: None)

    actions = []
    manager.available_actions = ["Attack", "Defend", "Items"]
    manager.engine = SimpleNamespace(
        pre_turn=lambda: SimpleNamespace(
            effects_text="", died_from_effects=False, can_act=True, inactive_reason=""
        ),
        get_forced_action=lambda: None,
        companion_turn=lambda: None,
    )
    manager._execute_action = (
        lambda action, _player, _enemy: actions.append(action) or "action_taken"
    )

    key_held = {"value": True}

    def fake_pump():
        key_held["value"] = False

    monkeypatch.setattr("src.ui_pygame.gui.input_guards.pygame.event.pump", fake_pump)
    monkeypatch.setattr(
        "src.ui_pygame.gui.input_guards.pygame.key.get_pressed",
        lambda: [1] if key_held["value"] else [],
    )
    event_batches = iter(
        [
            [SimpleNamespace(type=pygame.KEYDOWN, key=pygame.K_RIGHT)],
            [SimpleNamespace(type=pygame.KEYDOWN, key=pygame.K_RETURN)],
        ]
    )
    monkeypatch.setattr(
        "src.ui_pygame.gui.combat_manager.pygame.event.get", lambda: next(event_batches, [])
    )

    assert manager._player_turn(player, enemy) is True
    assert actions == ["Defend"]


def test_player_turn_refreshes_actions_after_silence_expires(monkeypatch):
    manager = _make_manager(monkeypatch)
    player = _make_player()
    enemy = _make_enemy()

    manager._render_combat_frame = lambda *args, **kwargs: None
    manager._flush_result_frame = lambda *_args: None
    monkeypatch.setattr("src.ui_pygame.gui.combat_manager.pygame.display.flip", lambda: None)
    monkeypatch.setattr("src.ui_pygame.gui.input_guards.pygame.key.get_pressed", lambda: [])

    actions = []
    manager.available_actions = ["Attack", "Defend", "Items"]
    manager.engine = SimpleNamespace(
        available_actions=["Attack", "Cast Spell", "Use Skill", "Use Item"],
        player=player,
        pre_turn=lambda: SimpleNamespace(
            effects_text=f"{player.name} can speak again.",
            died_from_effects=False,
            can_act=True,
            inactive_reason="",
        ),
        get_forced_action=lambda: None,
        companion_turn=lambda: None,
    )
    manager._execute_action = (
        lambda action, _player, _enemy: actions.append(action) or "action_taken"
    )
    event_batches = iter(
        [
            [SimpleNamespace(type=pygame.KEYDOWN, key=pygame.K_3)],
        ]
    )
    monkeypatch.setattr(
        "src.ui_pygame.gui.combat_manager.pygame.event.get", lambda: next(event_batches, [])
    )

    assert manager._player_turn(player, enemy) is True
    assert actions == ["Spells"]
    assert manager.available_actions == ["Attack", "Defend", "Spells", "Skills", "Items"]


def test_player_turn_continues_after_summoning_for_summon_action(monkeypatch):
    manager = _make_manager(monkeypatch)
    player = _make_player("Rydia")
    enemy = _make_enemy("Warrior")

    manager._render_combat_frame = lambda *args, **kwargs: None
    manager._flush_result_frame = lambda *_args: None
    monkeypatch.setattr("src.ui_pygame.gui.combat_manager.pygame.display.flip", lambda: None)
    monkeypatch.setattr("src.ui_pygame.gui.input_guards.pygame.key.get_pressed", lambda: [])

    companion_turns = []
    engine = SimpleNamespace(
        available_actions=["Summon"],
        pre_turn=lambda: SimpleNamespace(
            effects_text="", died_from_effects=False, can_act=True, inactive_reason=""
        ),
        get_forced_action=lambda: None,
        companion_turn=lambda: companion_turns.append(True) or None,
    )
    manager.engine = engine
    manager.available_actions = ["Summon"]
    actions = []

    def execute_action(action, _player, _enemy):
        actions.append(action)
        if action == "Summon":
            engine.available_actions = ["Attack"]
            return "continue_turn"
        return "action_taken"

    manager._execute_action = execute_action
    event_batches = iter(
        [
            [SimpleNamespace(type=pygame.KEYDOWN, key=pygame.K_RETURN)],
            [SimpleNamespace(type=pygame.KEYDOWN, key=pygame.K_RETURN)],
        ]
    )
    monkeypatch.setattr(
        "src.ui_pygame.gui.combat_manager.pygame.event.get", lambda: next(event_batches, [])
    )

    assert manager._player_turn(player, enemy) is True
    assert actions == ["Summon", "Attack"]
    assert companion_turns == [True]


def test_execute_skill_uses_active_summon_spellbook(monkeypatch):
    manager = _make_manager(monkeypatch)
    player = _make_player("Rydia")
    enemy = _make_enemy("Warrior")
    skill = SimpleNamespace(name="Throw Rock", cost=0)
    summon = SimpleNamespace(
        name="Patagon",
        health=SimpleNamespace(current=35, max=35),
        mana=SimpleNamespace(current=35, max=35),
        spellbook={"Spells": {}, "Skills": {"Throw Rock": skill}},
        abilities_suppressed=lambda: False,
        is_disarmed=lambda: False,
    )
    calls = {}

    manager.engine = SimpleNamespace(
        attacker=summon,
        execute_action=lambda action, choice=None, slot_machine_callback=None: calls.update(
            action=action,
            choice=choice,
            slot_machine_callback=slot_machine_callback,
        )
        or SimpleNamespace(message="Patagon uses Throw Rock.\n", fled=False),
        flee=False,
    )

    def select_skill(actor, _enemy):
        calls["selected_actor"] = actor
        return "Throw Rock"

    manager._select_skill = select_skill
    manager._render_combat_frame = lambda *_args, **_kwargs: None
    manager._flush_result_frame = lambda *_args, **_kwargs: None
    manager._show_combat_damage_effect = lambda *_args, **_kwargs: None
    manager._show_combat_heal_text = lambda *_args, **_kwargs: None
    manager._preserve_waitress_for_transition = lambda _enemy: None
    monkeypatch.setattr("src.ui_pygame.gui.combat_manager.pygame.display.flip", lambda: None)

    assert manager._execute_action("Skills", player, enemy) == "action_taken"
    assert calls["selected_actor"] is summon
    assert calls["action"] == "Use Skill"
    assert calls["choice"] == "Throw Rock"


def test_select_skill_for_active_summon_renders_player_frame(monkeypatch):
    manager = _make_manager(monkeypatch)
    player = _make_player("Rydia")
    enemy = _make_enemy("Warrior")
    skill = SimpleNamespace(name="Throw Rock", cost=0, passive=False)
    summon = SimpleNamespace(
        name="Patagon",
        spellbook={"Spells": {}, "Skills": {"Throw Rock": skill}},
        is_disarmed=lambda: False,
    )
    manager.engine = SimpleNamespace(player=player)

    rendered_players = []
    manager._render_combat_frame = lambda frame_player, *_args, **_kwargs: rendered_players.append(
        frame_player
    )
    manager._render_selection_menu = lambda *_args, **_kwargs: None
    monkeypatch.setattr("src.ui_pygame.gui.combat_manager.pygame.display.flip", lambda: None)
    monkeypatch.setattr("src.ui_pygame.gui.input_guards.pygame.key.get_pressed", lambda: [])
    event_batches = iter([[SimpleNamespace(type=pygame.KEYDOWN, key=pygame.K_RETURN)]])
    monkeypatch.setattr(
        "src.ui_pygame.gui.combat_manager.pygame.event.get", lambda: next(event_batches, [])
    )

    assert manager._select_skill(summon, enemy) == "Throw Rock"
    assert rendered_players == [player]


def test_enemy_turn_covers_skip_forced_nothing_and_damage_paths(monkeypatch):
    manager = _make_manager(monkeypatch)
    player = _make_player()
    enemy = _make_enemy()

    manager._render_combat_frame = lambda *args, **kwargs: None
    flushed_messages = []
    manager._flush_result_frame = lambda *_args: flushed_messages.append(
        tuple(manager.combat_view.messages)
    )
    monkeypatch.setattr("src.ui_pygame.gui.combat_manager.pygame.display.flip", lambda: None)
    monkeypatch.setattr("src.ui_pygame.gui.combat_manager.pygame.event.get", lambda: [])
    monkeypatch.setattr("src.ui_pygame.gui.combat_manager.pygame.time.Clock", lambda: DummyClock())
    player.status_effects = {"Stun": SimpleNamespace(active=False)}

    manager.engine = SimpleNamespace(
        pre_turn=lambda: SimpleNamespace(
            effects_text="Bleeding", died_from_effects=True, can_act=True, inactive_reason=""
        ),
    )
    assert manager._enemy_turn(player, enemy) is None
    assert manager.combat_view.messages[-1] == "Bleeding"
    assert flushed_messages[-1] == ("Bleeding",)

    manager.engine = SimpleNamespace(
        pre_turn=lambda: SimpleNamespace(
            effects_text="", died_from_effects=False, can_act=False, inactive_reason="Stunned"
        ),
    )
    assert manager._enemy_turn(player, enemy) is None
    assert manager.combat_view.messages[-1] == "Stunned"
    assert flushed_messages[-1][-1] == "Stunned"

    manager.engine = SimpleNamespace(
        pre_turn=lambda: SimpleNamespace(
            effects_text="", died_from_effects=False, can_act=True, inactive_reason=""
        ),
        get_forced_action=lambda: SimpleNamespace(
            action="Cancelled", cancel_message="Charge broken", choice=None
        ),
    )
    assert manager._enemy_turn(player, enemy) is None
    assert manager.combat_view.messages[-1] == "Charge broken"

    enemy.name = "Shifter"
    enemy.spellbook = {"Skills": {}}
    player.health.current = 42
    manager.engine = SimpleNamespace(
        pre_turn=lambda: SimpleNamespace(
            effects_text="", died_from_effects=False, can_act=True, inactive_reason=""
        ),
        get_forced_action=lambda: None,
        get_enemy_action=lambda: ("Nothing", None),
    )
    assert manager._enemy_turn(player, enemy) is None
    assert manager.combat_view.messages[-1] == "Shifter does nothing."

    enemy.name = "Mage"
    enemy.spellbook = {"Skills": {}}
    player.health.current = 30

    def execute_action(action, choice=None, slot_machine_callback=None):
        player.health.current = 18
        player.status_effects["Stun"].active = True
        enemy.name = "Mage Form"
        return SimpleNamespace(message="Dark blast", fled=False)

    manager.engine = SimpleNamespace(
        pre_turn=lambda: SimpleNamespace(
            effects_text="", died_from_effects=False, can_act=True, inactive_reason=""
        ),
        get_forced_action=lambda: None,
        get_enemy_action=lambda: ("Use Skill", "Hex"),
        show_enemy_details=lambda: True,
        execute_action=execute_action,
    )
    ability_calls = []
    player.record_bestiary_ability = lambda observed, ability_name: ability_calls.append(
        (observed, ability_name)
    )
    assert manager._enemy_turn(player, enemy) is None
    assert ability_calls == [(enemy, "Hex")]
    assert "Dark blast" in manager.combat_view.messages
    assert manager.combat_view.messages[-1] == "Hero is stunned and cannot act."
    assert manager.combat_view.reload_calls[-1] == enemy
    assert manager.combat_view.flash_calls[-1][0] is True


def test_enemy_turn_applies_vesperion_phase_pressure_before_action(monkeypatch):
    manager = _make_manager(monkeypatch)
    player = _make_player()
    enemy = enemies.Vesperion()
    player.main_story["guardian_trials_completed"]["Hexagonum"] = True
    player.main_story["guardian_trials_completed"]["Luna"] = True
    manager._render_combat_frame = lambda *args, **kwargs: None
    monkeypatch.setattr("src.ui_pygame.gui.combat_manager.pygame.display.flip", lambda: None)
    monkeypatch.setattr("src.ui_pygame.gui.combat_manager.pygame.event.get", lambda: [])
    monkeypatch.setattr("src.ui_pygame.gui.combat_manager.pygame.time.Clock", lambda: DummyClock())

    manager.engine = SimpleNamespace(
        pre_turn=lambda: SimpleNamespace(
            effects_text="", died_from_effects=False, can_act=True, inactive_reason=""
        ),
        get_forced_action=lambda: None,
        get_enemy_action=lambda: ("Nothing", None),
    )

    assert manager._enemy_turn(player, enemy) is None

    assert (
        "Hexagonum answers twilight's attrition with living choice that refuses to be managed into stillness."
        in manager.combat_view.messages
    )
    assert (
        "Luna refuses mercy that would make love into a cage; Voluntas leaves compassion free."
        in manager.combat_view.messages
    )
    assert manager.combat_view.messages[-1] == "Vesperion does nothing."
    assert enemy._vesperion_pressure_phases_used == {1}


def test_enemy_smoke_screen_flee_keeps_enemy_hidden_for_end_transition(monkeypatch):
    manager = _make_manager(monkeypatch)
    player = _make_player()
    enemy = _make_enemy("Bandit")
    enemy.spellbook = {"Skills": {"Smoke Screen": SimpleNamespace(name="Smoke Screen")}}
    player.status_effects = {"Stun": SimpleNamespace(active=False)}
    smoke_visuals = []

    monkeypatch.setattr("src.ui_pygame.gui.combat_manager.pygame.display.flip", lambda: None)
    monkeypatch.setattr("src.ui_pygame.gui.combat_manager.pygame.event.get", lambda: [])
    monkeypatch.setattr("src.ui_pygame.gui.combat_manager.pygame.time.Clock", lambda: DummyClock())
    manager._render_combat_frame = lambda *args, **kwargs: None
    manager._flush_result_frame = lambda *_args: None

    def play_smoke_screen_visual(_player, _enemy, target):
        smoke_visuals.append((target, manager.combat_view.hide_enemy_calls))

    manager._play_smoke_screen_visual = play_smoke_screen_visual

    def execute_smoke_screen(action, choice=None, slot_machine_callback=None):
        manager.engine.flee = True
        return SimpleNamespace(
            message="Bandit vanishes in smoke.",
            fled=False,
        )

    manager.engine = SimpleNamespace(
        flee=False,
        pre_turn=lambda: SimpleNamespace(
            effects_text="", died_from_effects=False, can_act=True, inactive_reason=""
        ),
        get_forced_action=lambda: None,
        get_enemy_action=lambda: ("Use Skill", "Smoke Screen"),
        execute_action=execute_smoke_screen,
    )

    assert manager._enemy_turn(player, enemy) == "flee"
    assert smoke_visuals == [("enemy", 1)]
    assert manager.combat_view.hide_enemy_calls == 1


def test_enemy_smoke_screen_without_flee_does_not_play_smoke_or_hide_enemy(monkeypatch):
    manager = _make_manager(monkeypatch)
    player = _make_player()
    enemy = _make_enemy("Bandit")
    enemy.spellbook = {"Skills": {"Smoke Screen": SimpleNamespace(name="Smoke Screen")}}
    player.status_effects = {"Stun": SimpleNamespace(active=False)}
    smoke_visuals = []
    flushes = []

    monkeypatch.setattr("src.ui_pygame.gui.combat_manager.pygame.display.flip", lambda: None)
    monkeypatch.setattr("src.ui_pygame.gui.combat_manager.pygame.event.get", lambda: [])
    monkeypatch.setattr("src.ui_pygame.gui.combat_manager.pygame.time.Clock", lambda: DummyClock())
    manager._render_combat_frame = lambda *args, **kwargs: None
    manager._flush_result_frame = lambda *_args: flushes.append(True)
    manager._play_smoke_screen_visual = lambda _player, _enemy, target: smoke_visuals.append(target)

    manager.engine = SimpleNamespace(
        flee=False,
        pre_turn=lambda: SimpleNamespace(
            effects_text="", died_from_effects=False, can_act=True, inactive_reason=""
        ),
        get_forced_action=lambda: None,
        get_enemy_action=lambda: ("Use Skill", "Smoke Screen"),
        execute_action=lambda *_args, **_kwargs: SimpleNamespace(
            message="Smoke Screen requires a weapon.",
            fled=False,
        ),
    )

    assert manager._enemy_turn(player, enemy) is None
    assert smoke_visuals == []
    assert manager.combat_view.hide_enemy_calls == 0
    assert flushes


def test_enemy_shapeshift_gets_one_same_turn_followup_action(monkeypatch):
    manager = _make_manager(monkeypatch)
    player = _make_player()
    enemy = _make_enemy("Shifter")
    enemy.spellbook = {
        "Skills": {
            "Shapeshift": SimpleNamespace(name="Shapeshift"),
            "Claw": SimpleNamespace(name="Claw"),
        }
    }
    player.status_effects = {"Stun": SimpleNamespace(active=False)}
    actions = iter([("Use Skill", "Shapeshift"), ("Use Skill", "Claw")])
    executed = []

    monkeypatch.setattr("src.ui_pygame.gui.combat_manager.pygame.display.flip", lambda: None)
    monkeypatch.setattr("src.ui_pygame.gui.combat_manager.pygame.event.get", lambda: [])
    monkeypatch.setattr("src.ui_pygame.gui.combat_manager.pygame.time.Clock", lambda: DummyClock())
    manager._render_combat_frame = lambda *args, **kwargs: None
    manager._flush_result_frame = lambda *_args: None

    def execute_action(action, choice=None, slot_machine_callback=None):
        executed.append((action, choice))
        if choice == "Shapeshift":
            enemy.name = "Wolf"
            return SimpleNamespace(message="Shifter changes shape.", fled=False)
        player.health.current -= 7
        return SimpleNamespace(message="Wolf uses Claw.", fled=False)

    manager.engine = SimpleNamespace(
        flee=False,
        pre_turn=lambda: SimpleNamespace(
            effects_text="", died_from_effects=False, can_act=True, inactive_reason=""
        ),
        get_forced_action=lambda: None,
        get_enemy_action=lambda: next(actions),
        show_enemy_details=lambda: False,
        execute_action=execute_action,
    )

    assert manager._enemy_turn(player, enemy) is None
    assert executed == [("Use Skill", "Shapeshift"), ("Use Skill", "Claw")]
    assert manager.combat_view.reload_calls == [enemy]
    assert player.health.current == 43
