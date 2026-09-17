"""
Sound Manager - Handles sound effects and music for The Forsaken Tenet.

Integrates with the event bus to play sounds based on game events.
"""

from __future__ import annotations

import logging
from pathlib import Path

import pygame.mixer

from src.core.events.event_bus import EventBus, EventType
from src.paths import PYGAME_ASSETS_DIR

logger = logging.getLogger(__name__)


DEFAULT_SFX_NAMES = (
    "combat_start",
    "victory",
    "flee",
    "defeat",
    "critical_hit",
    "heavy_hit",
    "hit",
    "laser_beam",
    "heal",
    "spell_fire",
    "spell_ice",
    "ice_spell",
    "spell_lightning",
    "spell_heal",
    "spell_cast",
    "distorted_scream",
    "bird_attack_sound",
    "mortal_strike",
    "shield_block_metal_weapon",
    "metal_weapon_disarm",
    "blade_parry",
    "underground_spring",
    "open_door",
    "poison",
    "stun",
    "burn",
    "player_death",
    "enemy_death",
    "level_up",
)

DEFAULT_MUSIC_NAMES = (
    "menu",
    "town",
    "shop",
    "church",
    "inn",
    "dungeon",
    "dungeon_final",
    "funhouse",
    "realm_of_cambion",
    "combat_normal",
    "combat_boss",
    "combat_final",
)

LOCATION_MUSIC_THEMES = {
    "menu": "menu",
    "main_menu": "menu",
    "town": "town",
    "shop": "shop",
    "blacksmith": "shop",
    "alchemist": "shop",
    "jeweler": "shop",
    "church": "church",
    "inn": "inn",
    "dungeon": "dungeon",
    "dungeon_final": "dungeon_final",
    "funhouse": "funhouse",
    "realm_of_cambion": "realm_of_cambion",
    "combat": "combat_normal",
}

DUNGEON_EXPLORATION_MUSIC = frozenset({"dungeon", "dungeon_final", "funhouse", "realm_of_cambion"})

_METAL_DISARM_WEAPON_TYPES = frozenset(
    {"Battle Axe", "Crossbow", "Dagger", "Hammer", "Longsword", "Polearm", "Sword"}
)

MUSIC_ASSET_ALIASES = {
    "dungeon": ("dungeon", "eerie_dungeon_background"),
}


class SoundManager:
    """Manages sound effects and background music."""

    def __init__(
        self,
        assets_dir: str | Path = PYGAME_ASSETS_DIR,
        event_bus: EventBus | None = None,
    ):
        """
        Initialize sound manager.

        Args:
            assets_dir: Base directory for assets
            event_bus: Event bus for subscribing to game events
        """
        self.assets_dir = Path(assets_dir)
        self.sounds_dir = self.assets_dir / "sounds"
        self.music_dir = self.assets_dir / "music"

        # Sound caches
        self.sfx_cache: dict[str, pygame.mixer.Sound] = {}
        self.current_music: str | None = None
        self._pre_combat_music: str | None = None

        # Volume settings (0.0 to 1.0)
        self.master_volume = 1.0
        self.sfx_volume = 0.7
        self.music_volume = 0.1
        self.enabled = True

        # Event bus integration
        self.event_bus = event_bus

        # Initialize pygame mixer if not already done
        if not pygame.mixer.get_init():
            try:
                pygame.mixer.init(frequency=44100, size=-16, channels=2, buffer=512)
                logger.info("Pygame mixer initialized")
            except pygame.error as e:
                logger.error(f"Failed to initialize pygame mixer: {e}")
                self.enabled = False
                return

        # Set channel count for simultaneous sounds
        pygame.mixer.set_num_channels(16)

        if self.event_bus:
            self._subscribe_to_events()

        logger.info("SoundManager initialized")

    def _subscribe_to_events(self):
        """Subscribe to combat and game events."""
        if not self.event_bus:
            return

        # Combat events
        self.event_bus.subscribe(EventType.COMBAT_START, self._on_combat_start)
        self.event_bus.subscribe(EventType.COMBAT_END, self._on_combat_end)
        self.event_bus.subscribe(EventType.DAMAGE_DEALT, self._on_damage_dealt)
        self.event_bus.subscribe(EventType.BLOCK, self._on_block)
        self.event_bus.subscribe(EventType.HEALING_DONE, self._on_healing)
        self.event_bus.subscribe(EventType.SPELL_CAST, self._on_spell_cast)
        self.event_bus.subscribe(EventType.SKILL_USE, self._on_skill_use)
        self.event_bus.subscribe(EventType.ITEM_USE, self._on_item_use)
        self.event_bus.subscribe(EventType.STATUS_APPLIED, self._on_status_applied)
        self.event_bus.subscribe(EventType.CHARACTER_DEATH, self._on_death)
        self.event_bus.subscribe(EventType.LEVEL_UP, self._on_level_up)

        logger.info("SoundManager subscribed to events")

    def _on_combat_start(self, event):
        """Handle combat start event."""
        self.play_sfx("combat_start")
        # Dungeon combat uses the existing dungeon bed so the transition keeps
        # its playback position instead of restarting a music loop.
        if self.current_music in DUNGEON_EXPLORATION_MUSIC:
            return
        if not (self.current_music or "").startswith("combat_"):
            self._pre_combat_music = self.current_music
        self.play_location_music(
            "combat",
            boss=bool(event.data.get("boss", False)),
            final=bool(event.data.get("final", False)),
        )

    def _on_combat_end(self, event):
        """Handle combat end event."""
        if event.data.get("player_alive"):
            self.play_sfx("victory")
        elif event.data.get("fled"):
            self.play_sfx("flee")
        else:
            self.play_sfx("defeat")
        if self._pre_combat_music:
            self.play_music(self._pre_combat_music)
            self._pre_combat_music = None

    def _on_damage_dealt(self, event):
        """Handle damage dealt event."""
        weapon_name = str(event.data.get("weapon_name", "") or "").lower()
        attack_source = str(event.data.get("attack_source", "") or "").lower()
        if "laser" in weapon_name or attack_source == "laser":
            self.play_sfx("laser_beam")
            return

        is_crit = event.data.get("crit", event.data.get("is_critical", False))
        damage = event.data.get("damage", 0)

        if is_crit:
            self.play_sfx("critical_hit", volume=1.0)
        elif damage > 50:
            self.play_sfx("heavy_hit")
        else:
            self.play_sfx("hit")

    def _on_block(self, event):
        """Route shield blocks and parries to their appropriate effects."""
        if event.data.get("reaction") == "parry":
            sound_name = "blade_parry" if event.data.get("parry_style") == "blade" else "block"
            self.play_sfx(sound_name)
            return
        if event.data.get("attack_source") == "natural_weapon":
            self.play_sfx("block")
            return
        self.play_sfx("shield_block_metal_weapon")

    def _on_healing(self, event):
        """Handle healing event."""
        self.play_sfx("heal")

    def _on_spell_cast(self, event):
        """Handle spell cast event."""
        spell_name = event.data.get("spell_name", event.data.get("ability_name", ""))

        # Map spells to sound effects
        if "fire" in spell_name.lower():
            self.play_sfx("spell_fire")
        elif "ice" in spell_name.lower() or "frost" in spell_name.lower():
            self.play_sfx("ice_spell")
        elif "lightning" in spell_name.lower() or "shock" in spell_name.lower():
            self.play_sfx("spell_lightning")
        elif "heal" in spell_name.lower():
            self.play_sfx("spell_heal")
        else:
            self.play_sfx("spell_cast")

    def _on_skill_use(self, event):
        """Handle skill use event."""
        skill_name = event.data.get("skill_name", event.data.get("ability_name", ""))
        skill_name_lower = skill_name.lower()

        # Map skills to sound effects
        if "fire" in skill_name_lower:
            self.play_sfx("spell_fire")
        elif "ice" in skill_name_lower or "frost" in skill_name_lower:
            self.play_sfx("ice_spell")
        elif "lightning" in skill_name_lower or "shock" in skill_name_lower:
            self.play_sfx("spell_lightning")
        elif "heal" in skill_name_lower:
            self.play_sfx("spell_heal")
        elif "mortal strike" in skill_name_lower:
            self.play_sfx("mortal_strike")
        elif "screech" in skill_name_lower:
            self.play_sfx("bird_attack_sound")
        elif any(keyword in skill_name_lower for keyword in ("howl", "nightmare")):
            self.play_sfx("distorted_scream")
        else:
            self.play_sfx("spell_cast")

    def _on_item_use(self, event):
        """Handle item use event."""
        item_name = str(event.data.get("item_name", "") or "").lower()
        item_subtype = str(event.data.get("item_subtype", "") or "").lower()

        if item_subtype == "scroll" or "scroll" in item_name:
            self.play_sfx("spell_cast")
        elif item_subtype in {"health", "mana", "elixir", "both"} or any(
            keyword in item_name for keyword in ("potion", "elixir", "megalixir")
        ):
            self.play_sfx("heal")

    def _on_status_applied(self, event):
        """Handle status effect applied event."""
        status_name = event.data.get("status_name", "").lower()

        if status_name == "disarm":
            equipment = getattr(getattr(event, "target", None), "equipment", {})
            weapon = equipment.get("Weapon") if isinstance(equipment, dict) else None
            weapon_type = str(getattr(weapon, "subtyp", "") or "")
            if weapon_type in _METAL_DISARM_WEAPON_TYPES:
                self.play_sfx("metal_weapon_disarm")
        elif "poison" in status_name or "bleed" in status_name:
            self.play_sfx("poison")
        elif "stun" in status_name or "freeze" in status_name:
            self.play_sfx("stun")
        elif "burn" in status_name:
            self.play_sfx("burn")

    def _on_death(self, event):
        """Handle death event."""
        is_player = event.data.get("is_player", False)

        if is_player:
            self.play_sfx("player_death")
        else:
            self.play_sfx("enemy_death")

    def _on_level_up(self, event):
        """Handle level up event."""
        self.play_sfx("level_up")

    def resolve_sfx_path(self, sound_name: str) -> Path | None:
        """Return the first available sound-effect asset path."""
        for sound_path in self.get_sfx_candidate_paths(sound_name):
            if sound_path.exists():
                return sound_path
        return None

    def resolve_music_path(self, music_name: str) -> Path | None:
        """Return the first available music asset path."""
        for music_path in self.get_music_candidate_paths(music_name):
            if music_path.exists():
                return music_path
        return None

    def get_sfx_candidate_paths(self, sound_name: str) -> tuple[Path, ...]:
        """Return sound-effect filenames checked for a sound name."""
        return tuple(self.sounds_dir / f"{sound_name}.{extension}" for extension in ("wav", "ogg"))

    def get_music_candidate_paths(self, music_name: str) -> tuple[Path, ...]:
        """Return music filenames checked for a music name."""
        names = MUSIC_ASSET_ALIASES.get(music_name, (music_name,))
        return tuple(
            self.music_dir / f"{name}.{extension}"
            for name in names
            for extension in ("ogg", "mp3", "wav")
        )

    def describe_audio_assets(
        self,
        *,
        sfx_names: tuple[str, ...] = (),
        music_names: tuple[str, ...] = (),
    ) -> dict[str, object]:
        """Return compact audio asset availability diagnostics without loading assets."""
        sfx = {
            name: {
                "available": (path := self.resolve_sfx_path(name)) is not None,
                "path": str(path) if path is not None else None,
                "checked_paths": [
                    str(candidate) for candidate in self.get_sfx_candidate_paths(name)
                ],
            }
            for name in sfx_names
        }
        music = {
            name: {
                "available": (path := self.resolve_music_path(name)) is not None,
                "path": str(path) if path is not None else None,
                "checked_paths": [
                    str(candidate) for candidate in self.get_music_candidate_paths(name)
                ],
            }
            for name in music_names
        }
        return {
            "enabled": self.enabled,
            "sfx": sfx,
            "music": music,
            "loaded_sfx_count": len(self.sfx_cache),
            "current_music": self.current_music,
        }

    @staticmethod
    def summarize_audio_asset_diagnostics(diagnostics: dict[str, object]) -> dict[str, int]:
        """Return compact availability counts for an audio diagnostics payload."""
        sfx = diagnostics.get("sfx", {})
        music = diagnostics.get("music", {})
        sfx_available_names = [name for name, item in sfx.items() if item.get("available")]
        sfx_missing_names = [name for name, item in sfx.items() if not item.get("available")]
        music_available_names = [name for name, item in music.items() if item.get("available")]
        music_missing_names = [name for name, item in music.items() if not item.get("available")]
        return {
            "sfx_total": len(sfx),
            "sfx_available": len(sfx_available_names),
            "sfx_missing": len(sfx_missing_names),
            "sfx_available_names": sfx_available_names,
            "sfx_missing_names": sfx_missing_names,
            "music_total": len(music),
            "music_available": len(music_available_names),
            "music_missing": len(music_missing_names),
            "music_available_names": music_available_names,
            "music_missing_names": music_missing_names,
        }

    def describe_default_audio_assets(self) -> dict[str, object]:
        """Return availability diagnostics for the runtime's expected audio assets."""
        return self.describe_audio_assets(
            sfx_names=DEFAULT_SFX_NAMES,
            music_names=DEFAULT_MUSIC_NAMES,
        )

    def summarize_default_audio_assets(self) -> dict[str, int]:
        """Return availability counts for the runtime's expected audio assets."""
        return self.summarize_audio_asset_diagnostics(self.describe_default_audio_assets())

    def resolve_music_theme(
        self,
        location: str,
        *,
        boss: bool = False,
        final: bool = False,
    ) -> str:
        """Map a game location/context to a background music asset name."""
        if final:
            return "combat_final"
        if boss:
            return "combat_boss"

        normalized = location.strip().lower().replace(" ", "_").replace("-", "_")
        return LOCATION_MUSIC_THEMES.get(normalized, "town")

    def play_location_music(
        self,
        location: str,
        *,
        boss: bool = False,
        final: bool = False,
        loops: int = -1,
        fade_ms: int = 1000,
        force: bool = False,
    ) -> str:
        """Play the music theme for a game location and return the chosen theme name."""
        theme = self.resolve_music_theme(location, boss=boss, final=final)
        if force or theme != self.current_music:
            self.play_music(theme, loops=loops, fade_ms=fade_ms)
        return theme

    def load_sfx(self, sound_name: str) -> pygame.mixer.Sound | None:
        """
        Load a sound effect from cache or file.

        Args:
            sound_name: Name of the sound file (without extension)

        Returns:
            Pygame Sound object or None if not found
        """
        if not self.enabled:
            return None

        # Check cache first
        if sound_name in self.sfx_cache:
            return self.sfx_cache[sound_name]

        sound_path = self.resolve_sfx_path(sound_name)
        if sound_path is None:
            logger.debug(f"Sound file not found: {sound_name}")
            return None

        try:
            sound = pygame.mixer.Sound(str(sound_path))
            self.sfx_cache[sound_name] = sound
            logger.debug(f"Loaded sound: {sound_name}")
            return sound
        except pygame.error as e:
            logger.error(f"Failed to load sound {sound_name}: {e}")
            return None

    def play_sfx(self, sound_name: str, volume: float | None = None, loops: int = 0):
        """
        Play a sound effect.

        Args:
            sound_name: Name of the sound to play
            volume: Optional volume override (0.0 to 1.0)
            loops: Number of additional times to play (-1 for infinite)
        """
        if not self.enabled:
            return

        sound = self.load_sfx(sound_name)
        if sound is None:
            return

        # Calculate final volume
        if volume is None:
            volume = self.sfx_volume
        final_volume = volume * self.master_volume

        sound.set_volume(final_volume)
        sound.play(loops=loops)

    def play_music(self, music_name: str, loops: int = -1, fade_ms: int = 1000):
        """
        Play background music.

        Args:
            music_name: Name of the music file (without extension)
            loops: Number of times to loop (-1 for infinite)
            fade_ms: Fade in duration in milliseconds
        """
        if not self.enabled:
            return

        music_path = self.resolve_music_path(music_name)
        if music_path is None:
            logger.debug(f"Music file not found: {music_name}")
            if pygame.mixer.music.get_busy():
                pygame.mixer.music.fadeout(fade_ms // 2)
            self.current_music = music_name
            return

        try:
            # Stop current music with fade out
            if pygame.mixer.music.get_busy():
                pygame.mixer.music.fadeout(fade_ms // 2)

            pygame.mixer.music.load(str(music_path))
            pygame.mixer.music.set_volume(self.music_volume * self.master_volume)
            pygame.mixer.music.play(loops=loops, fade_ms=fade_ms)
            self.current_music = music_name
            logger.info(f"Playing music: {music_name}")
        except pygame.error as e:
            logger.error(f"Failed to play music {music_name}: {e}")

    def stop_music(self, fade_ms: int = 1000):
        """
        Stop background music.

        Args:
            fade_ms: Fade out duration in milliseconds
        """
        if pygame.mixer.music.get_busy():
            pygame.mixer.music.fadeout(fade_ms)
        self.current_music = None

    def pause_music(self):
        """Pause background music."""
        pygame.mixer.music.pause()

    def resume_music(self):
        """Resume background music."""
        pygame.mixer.music.unpause()

    def set_master_volume(self, volume: float):
        """
        Set master volume.

        Args:
            volume: Volume level (0.0 to 1.0)
        """
        self.master_volume = max(0.0, min(1.0, volume))
        if pygame.mixer.music.get_busy():
            pygame.mixer.music.set_volume(self.music_volume * self.master_volume)

    def set_sfx_volume(self, volume: float):
        """
        Set sound effects volume.

        Args:
            volume: Volume level (0.0 to 1.0)
        """
        self.sfx_volume = max(0.0, min(1.0, volume))

    def set_music_volume(self, volume: float):
        """
        Set music volume.

        Args:
            volume: Volume level (0.0 to 1.0)
        """
        self.music_volume = max(0.0, min(1.0, volume))
        if pygame.mixer.music.get_busy():
            pygame.mixer.music.set_volume(self.music_volume * self.master_volume)

    def enable(self):
        """Enable sound system."""
        self.enabled = True

    def disable(self):
        """Disable sound system."""
        self.enabled = False
        self.stop_music(fade_ms=0)
        pygame.mixer.stop()

    def cleanup(self):
        """Clean up sound resources."""
        self.stop_music(fade_ms=0)
        self.sfx_cache.clear()
        if pygame.mixer.get_init():
            pygame.mixer.quit()
        logger.info("SoundManager cleaned up")


# Singleton instance
_sound_manager: SoundManager | None = None


def get_sound_manager(
    assets_dir: str | Path = PYGAME_ASSETS_DIR,
    event_bus: EventBus | None = None,
) -> SoundManager:
    """Get or create the singleton sound manager instance."""
    global _sound_manager
    if _sound_manager is None:
        _sound_manager = SoundManager(assets_dir=assets_dir, event_bus=event_bus)
    return _sound_manager
