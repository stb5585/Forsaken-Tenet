#!/usr/bin/env python3
"""Coverage for pygame sound-manager behavior using mixer fakes."""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest

from src.core.events import EventBus, EventType, GameEvent
from src.ui_pygame.assets import sound_manager as sound_module


class FakeSound:
    def __init__(self, path: str):
        self.path = path
        self.volumes: list[float] = []
        self.play_loops: list[int] = []

    def set_volume(self, value: float):
        self.volumes.append(value)

    def play(self, loops: int = 0):
        self.play_loops.append(loops)


class FakeMusic:
    def __init__(self):
        self.busy = False
        self.raise_on_load = False
        self.fadeouts: list[int] = []
        self.loaded: list[str] = []
        self.volumes: list[float] = []
        self.plays: list[tuple[int, int]] = []
        self.paused = 0
        self.unpaused = 0

    def get_busy(self):
        return self.busy

    def fadeout(self, value: int):
        self.fadeouts.append(value)
        self.busy = False

    def load(self, path: str):
        if self.raise_on_load:
            raise sound_module.pygame.error("music boom")
        self.loaded.append(path)

    def set_volume(self, value: float):
        self.volumes.append(value)

    def play(self, loops: int = -1, fade_ms: int = 0):
        self.plays.append((loops, fade_ms))
        self.busy = True

    def pause(self):
        self.paused += 1

    def unpause(self):
        self.unpaused += 1


@pytest.fixture
def fake_mixer(monkeypatch):
    state = {
        "initialized": True,
        "init_calls": [],
        "channels": [],
        "loaded_sounds": [],
        "stop_calls": 0,
        "quit_calls": 0,
        "init_exception": None,
        "sound_exception": None,
    }
    music = FakeMusic()

    def fake_get_init():
        return state["initialized"]

    def fake_init(**kwargs):
        state["init_calls"].append(kwargs)
        if state["init_exception"] is not None:
            raise state["init_exception"]
        state["initialized"] = True

    def fake_set_num_channels(count):
        state["channels"].append(count)

    def fake_sound(path):
        if state["sound_exception"] is not None:
            raise state["sound_exception"]
        sound = FakeSound(path)
        state["loaded_sounds"].append(sound)
        return sound

    def fake_stop():
        state["stop_calls"] += 1

    def fake_quit():
        state["quit_calls"] += 1
        state["initialized"] = False

    monkeypatch.setattr(sound_module.pygame.mixer, "get_init", fake_get_init)
    monkeypatch.setattr(sound_module.pygame.mixer, "init", fake_init)
    monkeypatch.setattr(sound_module.pygame.mixer, "set_num_channels", fake_set_num_channels)
    monkeypatch.setattr(sound_module.pygame.mixer, "Sound", fake_sound)
    monkeypatch.setattr(sound_module.pygame.mixer, "music", music, raising=False)
    monkeypatch.setattr(sound_module.pygame.mixer, "stop", fake_stop)
    monkeypatch.setattr(sound_module.pygame.mixer, "quit", fake_quit)
    return state, music


def _make_assets_dir(tmp_path: Path) -> Path:
    assets_dir = tmp_path / "assets"
    (assets_dir / "sounds").mkdir(parents=True)
    (assets_dir / "music").mkdir(parents=True)
    return assets_dir


def test_sound_manager_initializes_mixer_and_subscribes_to_bus(tmp_path, fake_mixer):
    state, _music = fake_mixer
    state["initialized"] = False
    bus = EventBus()
    manager = sound_module.SoundManager(assets_dir=str(_make_assets_dir(tmp_path)), event_bus=bus)

    assert manager.enabled is True
    assert state["init_calls"] == [{"frequency": 44100, "size": -16, "channels": 2, "buffer": 512}]
    assert state["channels"] == [16]
    assert EventType.COMBAT_START in bus._subscribers
    assert EventType.ITEM_USE in bus._subscribers
    assert EventType.LEVEL_UP in bus._subscribers


def test_sound_manager_disables_when_mixer_init_fails(tmp_path, fake_mixer):
    state, _music = fake_mixer
    state["initialized"] = False
    state["init_exception"] = sound_module.pygame.error("no audio")

    manager = sound_module.SoundManager(assets_dir=str(_make_assets_dir(tmp_path)))

    assert manager.enabled is False
    assert state["channels"] == []


def test_load_sfx_uses_cache_and_fallback_extensions(tmp_path, fake_mixer):
    state, _music = fake_mixer
    assets_dir = _make_assets_dir(tmp_path)
    (assets_dir / "sounds" / "hit.ogg").write_bytes(b"ogg")
    manager = sound_module.SoundManager(assets_dir=str(assets_dir))

    first = manager.load_sfx("hit")
    second = manager.load_sfx("hit")

    assert first is second
    assert len(state["loaded_sounds"]) == 1
    assert state["loaded_sounds"][0].path.endswith("hit.ogg")


def test_audio_asset_diagnostics_report_sound_and_music_availability(tmp_path, fake_mixer):
    _state, _music = fake_mixer
    assets_dir = _make_assets_dir(tmp_path)
    (assets_dir / "sounds" / "hit.wav").write_bytes(b"wav")
    (assets_dir / "sounds" / "heal.ogg").write_bytes(b"ogg")
    (assets_dir / "sounds" / "spring.wav").write_bytes(b"wav")
    (assets_dir / "sounds" / "distorted_scream.wav").write_bytes(b"wav")
    (assets_dir / "sounds" / "bird_attack_sound.wav").write_bytes(b"wav")
    (assets_dir / "sounds" / "laser_beam.wav").write_bytes(b"wav")
    (assets_dir / "sounds" / "mortal_strike.wav").write_bytes(b"wav")
    (assets_dir / "sounds" / "ice_spell.wav").write_bytes(b"wav")
    (assets_dir / "sounds" / "shield_block_metal_weapon.wav").write_bytes(b"wav")
    (assets_dir / "sounds" / "underground_spring.wav").write_bytes(b"wav")
    (assets_dir / "sounds" / "open_door.wav").write_bytes(b"wav")
    (assets_dir / "music" / "town.mp3").write_bytes(b"mp3")
    (assets_dir / "music" / "eerie_dungeon_background.wav").write_bytes(b"wav")
    manager = sound_module.SoundManager(assets_dir=str(assets_dir))
    manager.current_music = "town"
    manager.sfx_cache["hit"] = FakeSound("hit")

    assert manager.resolve_sfx_path("hit") == assets_dir / "sounds" / "hit.wav"
    assert manager.resolve_sfx_path("heal") == assets_dir / "sounds" / "heal.ogg"
    assert manager.resolve_sfx_path("spring") == assets_dir / "sounds" / "spring.wav"
    assert manager.resolve_music_path("town") == assets_dir / "music" / "town.mp3"
    assert (
        manager.resolve_music_path("dungeon")
        == assets_dir / "music" / "eerie_dungeon_background.wav"
    )
    assert manager.get_sfx_candidate_paths("hit") == (
        assets_dir / "sounds" / "hit.wav",
        assets_dir / "sounds" / "hit.ogg",
    )
    assert manager.get_music_candidate_paths("town") == (
        assets_dir / "music" / "town.ogg",
        assets_dir / "music" / "town.mp3",
        assets_dir / "music" / "town.wav",
    )
    assert manager.get_music_candidate_paths("dungeon") == (
        assets_dir / "music" / "dungeon.ogg",
        assets_dir / "music" / "dungeon.mp3",
        assets_dir / "music" / "dungeon.wav",
        assets_dir / "music" / "eerie_dungeon_background.ogg",
        assets_dir / "music" / "eerie_dungeon_background.mp3",
        assets_dir / "music" / "eerie_dungeon_background.wav",
    )

    diagnostics = manager.describe_audio_assets(
        sfx_names=("hit", "heal", "spring", "missing"),
        music_names=("town", "dungeon", "battle"),
    )

    assert diagnostics == {
        "enabled": True,
        "sfx": {
            "hit": {
                "available": True,
                "path": str(assets_dir / "sounds" / "hit.wav"),
                "checked_paths": [
                    str(assets_dir / "sounds" / "hit.wav"),
                    str(assets_dir / "sounds" / "hit.ogg"),
                ],
            },
            "heal": {
                "available": True,
                "path": str(assets_dir / "sounds" / "heal.ogg"),
                "checked_paths": [
                    str(assets_dir / "sounds" / "heal.wav"),
                    str(assets_dir / "sounds" / "heal.ogg"),
                ],
            },
            "spring": {
                "available": True,
                "path": str(assets_dir / "sounds" / "spring.wav"),
                "checked_paths": [
                    str(assets_dir / "sounds" / "spring.wav"),
                    str(assets_dir / "sounds" / "spring.ogg"),
                ],
            },
            "missing": {
                "available": False,
                "path": None,
                "checked_paths": [
                    str(assets_dir / "sounds" / "missing.wav"),
                    str(assets_dir / "sounds" / "missing.ogg"),
                ],
            },
        },
        "music": {
            "town": {
                "available": True,
                "path": str(assets_dir / "music" / "town.mp3"),
                "checked_paths": [
                    str(assets_dir / "music" / "town.ogg"),
                    str(assets_dir / "music" / "town.mp3"),
                    str(assets_dir / "music" / "town.wav"),
                ],
            },
            "dungeon": {
                "available": True,
                "path": str(assets_dir / "music" / "eerie_dungeon_background.wav"),
                "checked_paths": [
                    str(assets_dir / "music" / "dungeon.ogg"),
                    str(assets_dir / "music" / "dungeon.mp3"),
                    str(assets_dir / "music" / "dungeon.wav"),
                    str(assets_dir / "music" / "eerie_dungeon_background.ogg"),
                    str(assets_dir / "music" / "eerie_dungeon_background.mp3"),
                    str(assets_dir / "music" / "eerie_dungeon_background.wav"),
                ],
            },
            "battle": {
                "available": False,
                "path": None,
                "checked_paths": [
                    str(assets_dir / "music" / "battle.ogg"),
                    str(assets_dir / "music" / "battle.mp3"),
                    str(assets_dir / "music" / "battle.wav"),
                ],
            },
        },
        "loaded_sfx_count": 1,
        "current_music": "town",
    }
    assert sound_module.SoundManager.summarize_audio_asset_diagnostics(diagnostics) == {
        "sfx_total": 4,
        "sfx_available": 3,
        "sfx_missing": 1,
        "sfx_available_names": ["hit", "heal", "spring"],
        "sfx_missing_names": ["missing"],
        "music_total": 3,
        "music_available": 2,
        "music_missing": 1,
        "music_available_names": ["town", "dungeon"],
        "music_missing_names": ["battle"],
    }

    default_diagnostics = manager.describe_default_audio_assets()
    assert "combat_start" in default_diagnostics["sfx"]
    assert "combat_final" in default_diagnostics["music"]
    assert default_diagnostics["sfx"]["hit"]["available"] is True
    assert default_diagnostics["music"]["town"]["available"] is True
    assert default_diagnostics["music"]["combat_final"]["available"] is False
    default_summary = manager.summarize_default_audio_assets()
    assert default_summary["sfx_available"] == 10
    assert default_summary["music_available"] == 2
    assert "hit" in default_summary["sfx_available_names"]
    assert "laser_beam" in default_summary["sfx_available_names"]
    assert "bird_attack_sound" in default_summary["sfx_available_names"]
    assert "distorted_scream" in default_summary["sfx_available_names"]
    assert "mortal_strike" in default_summary["sfx_available_names"]
    assert "ice_spell" in default_summary["sfx_available_names"]
    assert "shield_block_metal_weapon" in default_summary["sfx_available_names"]
    assert "underground_spring" in default_summary["sfx_available_names"]
    assert "open_door" in default_summary["sfx_available_names"]
    assert "combat_final" in default_summary["music_missing_names"]


def test_load_sfx_returns_none_for_missing_files_or_loader_errors(tmp_path, fake_mixer):
    state, _music = fake_mixer
    assets_dir = _make_assets_dir(tmp_path)
    manager = sound_module.SoundManager(assets_dir=str(assets_dir))

    assert manager.load_sfx("missing") is None

    (assets_dir / "sounds" / "bad.wav").write_bytes(b"wav")
    state["sound_exception"] = sound_module.pygame.error("bad sound")
    assert manager.load_sfx("bad") is None


def test_play_sfx_applies_volume_and_loops(tmp_path, fake_mixer, monkeypatch):
    _state, _music = fake_mixer
    manager = sound_module.SoundManager(assets_dir=str(_make_assets_dir(tmp_path)))
    sound = FakeSound("manual")
    monkeypatch.setattr(manager, "load_sfx", lambda sound_name: sound)

    manager.master_volume = 0.5
    manager.play_sfx("hit")
    manager.play_sfx("critical", volume=1.0, loops=2)

    assert sound.volumes == [0.35, 0.5]
    assert sound.play_loops == [0, 2]


def test_play_music_handles_busy_track_and_fallback_files(tmp_path, fake_mixer):
    _state, music = fake_mixer
    assets_dir = _make_assets_dir(tmp_path)
    (assets_dir / "music" / "battle.mp3").write_bytes(b"mp3")
    manager = sound_module.SoundManager(assets_dir=str(assets_dir))
    music.busy = True

    manager.play_music("battle", loops=3, fade_ms=600)

    assert music.fadeouts == [300]
    assert music.loaded and music.loaded[0].endswith("battle.mp3")
    assert music.volumes == [manager.music_volume]
    assert music.plays == [(3, 600)]
    assert manager.current_music == "battle"


def test_location_music_routes_context_to_theme_names(tmp_path, fake_mixer, monkeypatch):
    _state, _music = fake_mixer
    manager = sound_module.SoundManager(assets_dir=str(_make_assets_dir(tmp_path)))
    calls = []
    monkeypatch.setattr(
        manager,
        "play_music",
        lambda music_name, loops=-1, fade_ms=1000: calls.append((music_name, loops, fade_ms)),
    )

    assert manager.resolve_music_theme("Town") == "town"
    assert manager.resolve_music_theme("Main Menu") == "menu"
    assert manager.resolve_music_theme("Blacksmith") == "shop"
    assert manager.resolve_music_theme("Dungeon Final") == "dungeon_final"
    assert manager.resolve_music_theme("Funhouse") == "funhouse"
    assert manager.resolve_music_theme("Realm of Cambion") == "realm_of_cambion"
    assert manager.resolve_music_theme("Final Room", final=True) == "combat_final"
    assert manager.resolve_music_theme("Combat", boss=True) == "combat_boss"
    assert manager.resolve_music_theme("Unknown Place") == "town"

    theme = manager.play_location_music("Dungeon", loops=2, fade_ms=250)

    assert theme == "dungeon"
    assert calls == [("dungeon", 2, 250)]

    manager.current_music = "dungeon"
    assert manager.play_location_music("Dungeon") == "dungeon"
    assert calls == [("dungeon", 2, 250)]

    assert manager.play_location_music("Dungeon", force=True, fade_ms=10) == "dungeon"
    assert calls == [("dungeon", 2, 250), ("dungeon", -1, 10)]


def test_play_music_missing_or_erroring_files_are_safe(tmp_path, fake_mixer):
    _state, music = fake_mixer
    assets_dir = _make_assets_dir(tmp_path)
    manager = sound_module.SoundManager(assets_dir=str(assets_dir))

    music.busy = True
    manager.play_music("missing")
    assert music.fadeouts == [500]
    assert manager.current_music == "missing"

    (assets_dir / "music" / "broken.ogg").write_bytes(b"ogg")
    music.raise_on_load = True
    manager.play_music("broken")
    assert manager.current_music == "missing"


def test_missing_town_music_stops_stale_dungeon_track(tmp_path, fake_mixer):
    _state, music = fake_mixer
    assets_dir = _make_assets_dir(tmp_path)
    (assets_dir / "music" / "eerie_dungeon_background.wav").write_bytes(b"wav")
    manager = sound_module.SoundManager(assets_dir=str(assets_dir))

    manager.play_location_music("dungeon", fade_ms=400)
    assert manager.current_music == "dungeon"
    assert music.busy is True

    manager.play_location_music("town", fade_ms=400)

    assert manager.current_music == "town"
    assert music.fadeouts == [200]


def test_stop_pause_resume_and_volume_controls(tmp_path, fake_mixer):
    _state, music = fake_mixer
    assets_dir = _make_assets_dir(tmp_path)
    (assets_dir / "music" / "battle.ogg").write_bytes(b"ogg")
    manager = sound_module.SoundManager(assets_dir=str(assets_dir))
    music.busy = True
    manager.current_music = "battle"

    manager.stop_music(fade_ms=700)
    manager.pause_music()
    manager.resume_music()
    music.busy = True
    manager.set_master_volume(1.5)
    manager.set_sfx_volume(-0.2)
    manager.set_music_volume(2.0)

    assert music.fadeouts == [700]
    assert music.paused == 1
    assert music.unpaused == 1
    assert manager.current_music is None
    assert manager.master_volume == 1.0
    assert manager.sfx_volume == 0.0
    assert manager.music_volume == 1.0
    assert music.volumes[-2:] == [0.1, 1.0]

    manager.current_music = "dungeon"
    music.busy = False
    manager.stop_music()
    assert manager.current_music is None


def test_enable_disable_cleanup_and_singleton_access(tmp_path, fake_mixer, monkeypatch):
    state, music = fake_mixer
    assets_dir = _make_assets_dir(tmp_path)
    manager = sound_module.SoundManager(assets_dir=str(assets_dir))
    manager.sfx_cache["hit"] = FakeSound("cached")
    music.busy = True

    manager.disable()
    assert manager.enabled is False
    assert music.fadeouts == [0]
    assert state["stop_calls"] == 1

    manager.enable()
    assert manager.enabled is True

    music.busy = True
    manager.cleanup()
    assert manager.sfx_cache == {}
    assert state["quit_calls"] == 1
    assert music.fadeouts[-1] == 0

    created = []

    class FakeSingleton:
        def __init__(self, assets_dir="src/ui_pygame/assets", event_bus=None):
            self.assets_dir = assets_dir
            self.event_bus = event_bus
            created.append((assets_dir, event_bus))

    monkeypatch.setattr(sound_module, "_sound_manager", None)
    monkeypatch.setattr(sound_module, "SoundManager", FakeSingleton)

    first = sound_module.get_sound_manager("alpha", event_bus="bus")
    second = sound_module.get_sound_manager("beta", event_bus=None)

    assert first is second
    assert created == [("alpha", "bus")]


def test_event_handlers_route_to_expected_sound_effects(tmp_path, fake_mixer, monkeypatch):
    _state, _music = fake_mixer
    manager = sound_module.SoundManager(assets_dir=str(_make_assets_dir(tmp_path)))
    calls = []
    music_calls = []
    monkeypatch.setattr(
        manager, "play_sfx", lambda name, volume=None, loops=0: calls.append((name, volume, loops))
    )
    monkeypatch.setattr(
        manager,
        "play_location_music",
        lambda location, **kwargs: music_calls.append((location, kwargs)) or "combat_normal",
    )

    manager._on_combat_start(GameEvent(type=EventType.COMBAT_START, timestamp=0, data={}))
    manager._on_combat_end(
        GameEvent(type=EventType.COMBAT_END, timestamp=0, data={"player_alive": True})
    )
    manager._on_combat_end(GameEvent(type=EventType.COMBAT_END, timestamp=0, data={"fled": True}))
    manager._on_combat_end(GameEvent(type=EventType.COMBAT_END, timestamp=0, data={}))
    manager._on_damage_dealt(
        GameEvent(type=EventType.DAMAGE_DEALT, timestamp=0, data={"crit": True, "damage": 1})
    )
    manager._on_damage_dealt(
        GameEvent(type=EventType.DAMAGE_DEALT, timestamp=0, data={"is_critical": True, "damage": 1})
    )
    manager._on_damage_dealt(
        GameEvent(
            type=EventType.DAMAGE_DEALT, timestamp=0, data={"weapon_name": "Laser", "damage": 10}
        )
    )
    manager._on_damage_dealt(
        GameEvent(type=EventType.DAMAGE_DEALT, timestamp=0, data={"damage": 80})
    )
    manager._on_damage_dealt(
        GameEvent(type=EventType.DAMAGE_DEALT, timestamp=0, data={"damage": 10})
    )
    manager._on_block(GameEvent(type=EventType.BLOCK, timestamp=0, data={"damage_blocked": 25}))
    manager._on_block(
        GameEvent(
            type=EventType.BLOCK,
            timestamp=0,
            data={"damage_blocked": 25, "attack_source": "natural_weapon"},
        )
    )
    manager._on_block(
        GameEvent(
            type=EventType.BLOCK,
            timestamp=0,
            data={"reaction": "parry", "parry_style": "blade"},
        )
    )
    manager._on_block(
        GameEvent(
            type=EventType.BLOCK,
            timestamp=0,
            data={"reaction": "parry", "parry_style": "generic"},
        )
    )
    manager._on_healing(GameEvent(type=EventType.HEALING_DONE, timestamp=0, data={}))
    manager._on_spell_cast(
        GameEvent(type=EventType.SPELL_CAST, timestamp=0, data={"spell_name": "Fireball"})
    )
    manager._on_spell_cast(
        GameEvent(type=EventType.SPELL_CAST, timestamp=0, data={"spell_name": "Frost Lance"})
    )
    manager._on_spell_cast(
        GameEvent(type=EventType.SPELL_CAST, timestamp=0, data={"ability_name": "Lightning Arc"})
    )
    manager._on_spell_cast(
        GameEvent(type=EventType.SPELL_CAST, timestamp=0, data={"spell_name": "Heal"})
    )
    manager._on_spell_cast(
        GameEvent(type=EventType.SPELL_CAST, timestamp=0, data={"spell_name": "Mystery"})
    )
    manager._on_skill_use(
        GameEvent(type=EventType.SKILL_USE, timestamp=0, data={"skill_name": "Fire Slash"})
    )
    manager._on_skill_use(
        GameEvent(type=EventType.SKILL_USE, timestamp=0, data={"skill_name": "Ice Kick"})
    )
    manager._on_skill_use(
        GameEvent(type=EventType.SKILL_USE, timestamp=0, data={"ability_name": "Shock Palm"})
    )
    manager._on_skill_use(
        GameEvent(type=EventType.SKILL_USE, timestamp=0, data={"skill_name": "Healing Waltz"})
    )
    manager._on_skill_use(
        GameEvent(type=EventType.SKILL_USE, timestamp=0, data={"skill_name": "Mortal Strike"})
    )
    manager._on_skill_use(
        GameEvent(type=EventType.SKILL_USE, timestamp=0, data={"skill_name": "Screech"})
    )
    manager._on_skill_use(
        GameEvent(type=EventType.SKILL_USE, timestamp=0, data={"skill_name": "Howl"})
    )
    manager._on_skill_use(
        GameEvent(type=EventType.SKILL_USE, timestamp=0, data={"skill_name": "Backflip"})
    )
    manager._on_item_use(
        GameEvent(type=EventType.ITEM_USE, timestamp=0, data={"item_name": "Fire Scroll"})
    )
    manager._on_item_use(
        GameEvent(type=EventType.ITEM_USE, timestamp=0, data={"item_subtype": "Elixir"})
    )
    manager._on_item_use(
        GameEvent(type=EventType.ITEM_USE, timestamp=0, data={"item_name": "Mystery Token"})
    )
    manager._on_status_applied(
        GameEvent(type=EventType.STATUS_APPLIED, timestamp=0, data={"status_name": "Poison"})
    )
    manager._on_status_applied(
        SimpleNamespace(
            data={"status_name": "Disarm"},
            target=SimpleNamespace(
                equipment={"Weapon": SimpleNamespace(subtyp="Sword")},
            ),
        )
    )
    manager._on_status_applied(
        SimpleNamespace(
            data={"status_name": "Disarm"},
            target=SimpleNamespace(
                equipment={"Weapon": SimpleNamespace(subtyp="Staff")},
            ),
        )
    )
    manager._on_status_applied(
        GameEvent(type=EventType.STATUS_APPLIED, timestamp=0, data={"status_name": "Freeze"})
    )
    manager._on_status_applied(
        GameEvent(type=EventType.STATUS_APPLIED, timestamp=0, data={"status_name": "Burn"})
    )
    manager._on_status_applied(
        GameEvent(type=EventType.STATUS_APPLIED, timestamp=0, data={"status_name": "Sleep"})
    )
    manager._on_death(
        GameEvent(type=EventType.CHARACTER_DEATH, timestamp=0, data={"is_player": True})
    )
    manager._on_death(
        GameEvent(type=EventType.CHARACTER_DEATH, timestamp=0, data={"is_player": False})
    )
    manager._on_level_up(GameEvent(type=EventType.LEVEL_UP, timestamp=0, data={}))

    assert calls == [
        ("combat_start", None, 0),
        ("victory", None, 0),
        ("flee", None, 0),
        ("defeat", None, 0),
        ("critical_hit", 1.0, 0),
        ("critical_hit", 1.0, 0),
        ("laser_beam", None, 0),
        ("heavy_hit", None, 0),
        ("hit", None, 0),
        ("shield_block_metal_weapon", None, 0),
        ("block", None, 0),
        ("blade_parry", None, 0),
        ("block", None, 0),
        ("heal", None, 0),
        ("spell_fire", None, 0),
        ("ice_spell", None, 0),
        ("spell_lightning", None, 0),
        ("spell_heal", None, 0),
        ("spell_cast", None, 0),
        ("spell_fire", None, 0),
        ("ice_spell", None, 0),
        ("spell_lightning", None, 0),
        ("spell_heal", None, 0),
        ("mortal_strike", None, 0),
        ("bird_attack_sound", None, 0),
        ("distorted_scream", None, 0),
        ("spell_cast", None, 0),
        ("spell_cast", None, 0),
        ("heal", None, 0),
        ("poison", None, 0),
        ("metal_weapon_disarm", None, 0),
        ("stun", None, 0),
        ("burn", None, 0),
        ("player_death", None, 0),
        ("enemy_death", None, 0),
        ("level_up", None, 0),
    ]
    assert music_calls == [("combat", {"boss": False, "final": False})]


def test_combat_start_music_uses_boss_and_final_flags(tmp_path, fake_mixer, monkeypatch):
    _state, _music = fake_mixer
    manager = sound_module.SoundManager(assets_dir=str(_make_assets_dir(tmp_path)))
    music_calls = []
    monkeypatch.setattr(manager, "play_sfx", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(
        manager,
        "play_location_music",
        lambda location, **kwargs: music_calls.append((location, kwargs)) or "combat_boss",
    )

    manager._on_combat_start(
        GameEvent(type=EventType.COMBAT_START, timestamp=0, data={"boss": True})
    )
    manager._on_combat_start(
        GameEvent(type=EventType.COMBAT_START, timestamp=0, data={"final": True})
    )

    assert music_calls == [
        ("combat", {"boss": True, "final": False}),
        ("combat", {"boss": False, "final": True}),
    ]


@pytest.mark.parametrize(
    "area_music", ("dungeon", "dungeon_final", "funhouse", "realm_of_cambion")
)
def test_dungeon_combat_keeps_the_running_area_music(
    tmp_path, fake_mixer, monkeypatch, area_music
):
    _state, _music = fake_mixer
    manager = sound_module.SoundManager(assets_dir=str(_make_assets_dir(tmp_path)))
    manager.current_music = area_music
    music_calls = []
    sfx_calls = []
    monkeypatch.setattr(manager, "play_sfx", lambda name, **_kwargs: sfx_calls.append(name))
    monkeypatch.setattr(
        manager,
        "play_location_music",
        lambda location, **kwargs: setattr(manager, "current_music", "combat_boss")
        or music_calls.append(("location", location, kwargs)),
    )
    monkeypatch.setattr(
        manager,
        "play_music",
        lambda music_name, **_kwargs: setattr(manager, "current_music", music_name)
        or music_calls.append(("music", music_name)),
    )

    manager._on_combat_start(
        GameEvent(type=EventType.COMBAT_START, timestamp=0, data={"boss": True})
    )
    manager._on_combat_end(
        GameEvent(type=EventType.COMBAT_END, timestamp=0, data={"player_alive": True})
    )

    assert sfx_calls == ["combat_start", "victory"]
    assert music_calls == []
    assert manager.current_music == area_music
    assert manager._pre_combat_music is None
