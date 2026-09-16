# Sound System

## Overview

The Forsaken Tenet sound system provides audio feedback through sound effects
and background music. It integrates with the game's event-driven architecture.

## Architecture

### Sound Manager

The `SoundManager` class (`src/ui_pygame/assets/sound_manager.py`) handles:
- Sound effect loading and caching
- Background music playback
- Volume control (master, SFX, and music separately)
- Event-driven sound playback

### Event Integration

The sound manager subscribes to combat and game events:
- `COMBAT_START` - Combat begins sound
- `COMBAT_END` - Victory/defeat/flee sounds
- `DAMAGE_DEALT` - Hit sounds (normal/heavy/critical)
- `BLOCK` - Shield/block impact sounds
- `HEALING_DONE` - Healing sound
- `SPELL_CAST` - Spell casting sounds (fire/ice/lightning/etc.)
- `SKILL_USE` - Skill usage sounds
- `ITEM_USE` - Scroll and recovery-item sounds
- `STATUS_APPLIED` - Status effect sounds (poison/stun/burn)
- `CHARACTER_DEATH` - Death sounds (player/enemy)
- `LEVEL_UP` - Level up fanfare

### Menu Sounds

UI navigation triggers sounds automatically:
- Arrow keys - `menu_select.wav`
- Enter/Space - `menu_confirm.wav`
- Escape - `menu_cancel.wav`

## File Structure

```
src/ui_pygame/assets/
├── sounds/          # Sound effects (.wav or .ogg)
│   ├── combat_start.wav
│   ├── hit.wav
│   ├── critical_hit.wav
│   ├── spell_fire.wav
│   ├── menu_select.wav
│   └── ... (see sounds/README.md)
└── music/           # Background music (.ogg or .mp3)
    ├── town.ogg
    ├── dungeon_floor1.ogg
    ├── combat_boss.ogg
    └── ... (see music/README.md)
```

## Usage

### Basic Usage

The sound manager is automatically initialized when the PygamePresenter starts:

```python
from src.ui_pygame.assets.sound_manager import get_sound_manager

# Get the singleton instance
sound_manager = get_sound_manager()

# Play a sound effect
sound_manager.play_sfx("hit")

# Play background music (loops by default)
sound_manager.play_music("dungeon_floor1")

# Stop music
sound_manager.stop_music()
```

### Volume Control

```python
# Set master volume (0.0 to 1.0)
sound_manager.set_master_volume(0.8)

# Set SFX volume
sound_manager.set_sfx_volume(0.7)

# Set music volume
sound_manager.set_music_volume(0.1)

# Disable all sound
sound_manager.disable()

# Re-enable sound
sound_manager.enable()
```

### Playing Custom Sounds

```python
# Play with custom volume
sound_manager.play_sfx("explosion", volume=1.0)

# Loop a sound effect
sound_manager.play_sfx("ambient_wind", loops=-1)  # -1 = infinite

# Play music with fade-in
sound_manager.play_music("boss_battle", fade_ms=2000)
```

## Adding New Sounds

1. **Create or find sound files** (WAV or OGG format recommended)
2. **Place files in appropriate directory**:
   - Sound effects → `src/ui_pygame/assets/sounds/`
   - Music → `src/ui_pygame/assets/music/`
3. **Use descriptive names** (lowercase, underscores)
4. **Play the sound** using the sound manager

### Example: Adding a New Spell Sound

1. Add `spell_explosion.wav` to `src/ui_pygame/assets/sounds/`
2. Update the `_on_spell_cast` or `_on_skill_use` event handler in `sound_manager.py`:

```python
elif 'explosion' in spell_name.lower():
    self.play_sfx("spell_explosion")
```

### Source-Specific Routing

Prefer event payload fields over broad name guessing when routing a sound to a
specific source. Weapon-damage events can expose `weapon_name`, `weapon_slot`,
`weapon_type`, `attack_source`, and `source`; action events can expose
`ability_name`, `spell_name`, `skill_name`, `item_name`, `item_type`, or
`item_subtype`.

Current source-specific staged routes include:

- `laser_beam.wav` for Laser weapon damage.
- `bird_attack_sound.wav` for `Screech`.
- `spell_cast` for scroll item use, and `heal` for potion/elixir item use.
- `shield_block_metal_weapon.wav` for block events.
- `ice_spell.ogg`, `distorted_scream.wav`, `mortal_strike.wav`,
  `underground_spring.ogg`, and `open_door.ogg` through existing runtime hooks.

## Audio Gates

This document owns the audio side of the Systems, Audio, and Meta gates.
Preserve the current missing-asset fallback behavior, diagnostics,
direct `sounds/` lookup, music aliases, and combat/location music theme routing
unless a promoted audio spec explicitly changes them.

Dungeon-origin combat deliberately retains its running exploration music bed,
including boss and final encounters, so it continues without a restart. Combat
start and outcome effects still play; non-dungeon combat retains normal theme
routing.

Ordinary dungeon levels 1–5 use the shared `dungeon` theme. Level 6, the
Funhouse (level 7), and the Realm of Cambion (level 8) route to the distinct
`dungeon_final`, `funhouse`, and `realm_of_cambion` themes. Those three OGG
assets are pending; diagnostics expose the missing files without breaking play.

Final SFX and music replacement remains an asset-content pass. It should cover
menu, town, shops, Church, inn, dungeon, normal combat, boss combat, and final
combat themes/effects while keeping missing-file fallback behavior intact.

## Sonniss GDC 2024 Source Audit

The reviewed Sonniss GDC 2024 sources from bundles 1–9 are organized under
`unused_assets/audio_candidates/` and `unused_assets/audio_unsuitable/`. They
contain 482 WAV assets in total. The included README files say the supplied
assets are royalty-free for personal and commercial use without attribution;
retain the supplied licence PDF and source path in
[`ASSET_PROVENANCE.md`](ASSET_PROVENANCE.md) whenever an asset is promoted.

The bundle is a source library, not a runtime dependency. Do not copy a raw
asset into live assets until it has been auditioned, trimmed, normalized,
converted to a suitable mono/stereo WAV or OGG, and named after its runtime
route. Avoid using real-world guns, vehicles, sports crowds, voices, or modern
office/city ambience for the medieval-fantasy game except where an explicit
anomalous setting calls for it.

For local auditioning, the reviewed source directories are arranged as follows:

- `unused_assets/audio_candidates/<bundle>/` contains the 23 high-value libraries
  listed below.
- `unused_assets/audio_unsuitable/<bundle>/` contains the 125 reviewed libraries
  that do not fit the current game-audio needs.
- `unused_assets/audio_source_metadata/<bundle>/` retains the original licence,
  README, and file-list materials for every bundle.

This is a local, ignored workspace organization only; it does not promote raw
audio into the game or change the required provenance process.

### High-Value Candidate Families

| Runtime need | Recommended source family | First files to audition | Intended use |
| --- | --- | --- | --- |
| Dungeon bed and water detail | Bundle 1 `InMotionAudio - Cave Design` | `AMBUndr_CaveDesign01...`, `WATRDrip_SingleDrip03...`, `AMBUndwtr_WaterFlow05...` | Replace/augment the dungeon loop, cave drips, and spring interaction. |
| Underground Spring | Bundle 6 `Pole Position - Winter Forest Stream`; Bundle 8 `Stefano Cremona - Rivers, Streams, Creeks` | `Stream - LIGHT - Medium Speed - Flow...`, `Small_Creek_Close_02.wav` | Softer location-loop and short interaction tail. |
| Physical impacts and blocks | Bundle 2 `Justsoundeffects - Melee Weapons`; Bundle 6 `Pole Position - The Metal Hit Sweeteners Library` | `WEAPArmr_Metal Shield Block Hits...`, `WEAPAxe_Long Two-Handed Axe Flesh Hit...`, `Iron - Thick - HIT - Hammer.wav` | Upgrade hit, heavy hit, critical hit, and shield block variants. |
| Doors, locks, and chests | Bundle 2 `Jake Fielding - Squeaky Gates`; Bundle 6 `Rogue Waves - Creaking Door`; Bundle 8 `Sonic Bat - Videogame Foley Essentials Vol. II` | `DOORGate_Wooden Metal Hinge Creaks...`, `DOORCreak_Wooden Door, Opening and Closing 09...`, `SBvfe2_Shaking Small Wooden Box 030.wav` | Door open/close, secret-door, chest, and lock feedback. |
| Spell motion and magic | Bundle 6 `Rescopic Sound - Distinct Whooshes` and `High Voltage`; Bundle 2 `Mechanical Wave - Sound Effects Collection` | `WHSH_Airy-Whoosh Wind Gust 11...`, `ELECEmf_Electrical Panel Pitchdown 12st...`, `ICEMisc_Ice Sizzle_05...` | Wind, lightning, ice, generic cast, and anti-magic/sigil design layers. |
| Horror, boss, and revelation stingers | Bundle 1 `InMotionAudio - Sinister Textures` / `GEODRONE`; Bundle 2 `Jake Fielding - Haunted Metal` | `DSGNErie_EerieBoilerRoom06...`, `DSGNDron_Geofon17...`, `DSGNBoom_Cinematic Metallic Hit...` | Boss reveals, relics, anti-magic activation, and defeat punctuation; use sparingly. |
| UI feedback | Bundle 6 `Rescopic Sound - User Interaction` | `UIClick_Select Middle 29...`, `UIAlert_Confirm Middle 12...`, `UIData_Progress 19...` | Replace generic menu select, confirm, and progression/level-up feedback. |
| Town and exterior ambience | Bundle 2 `Justsoundeffects - Forest Ambiences`; Bundle 8 `Systematic Sound - Rural Countryside` / `Nightscapes` | `AMBForst_Spring Noon Deciduous Forest...`, `AMBRurl_Field Wheat Dry Sizzle...`, `AMBForst_Nighttime-Woodlands...` | Optional low-level town/outdoor beds and night-event ambience. |
| Fire and hearth | Bundle 9 `UberDuo - The Wood Stove Audio Prop Set` | `FIREMisc_Fire Crackling In A Woodstove...`, `DOORMetl_Woodstove, Door, Iron, Close...` | Inn, campfire, fire spell, forge, and hearth variations. |

Ellipses in the table preserve the distinctive filename prefix. Locate a
candidate by its source directory and prefix; select a short clean region only
after listening. The `Rogue Waves - Kawaii UI`, Sci-Fi, and Anime collections
are useful only for intentionally stylized UI or arcane effects, not default
fantasy combat.

### Upgrade And Missing-Sound Backlog

Priority order for an asset pass:

1. **Music remains the largest gap.** Only `dungeon.ogg` is currently
   currently present. Commission or license seamless original tracks for menu,
   town, shop, church, inn, normal combat, boss combat, and final combat; the
   Sonniss material should be treated as ambience/stinger layers, not score.
2. **Replace placeholder-like core combat sounds** with coherent variations for
   light hit, heavy hit, critical hit, miss, block/parry, player death, enemy
   death, victory, defeat, and flee. Create a small randomized variant pool
   only after the base routes are approved.
3. **Complete elemental identity:** distinct fire, ice, lightning, wind,
   water, earth, poison, holy, shadow, heal, buff, debuff, and anti-magic
   sounds. Current routing collapses several categories into generic cast or
   status effects.
4. **Fill world interactions:** chest/lockpick, trap trigger and damage,
   stairs, gathering/foraging, key item/relic discovery, Mimic reveal, secret
   door, merchant purchase/sale, quest accepted/completed/turned-in, and gold
   reward.
5. **Add location ambience deliberately:** town daytime/night, inn hearth and
   crowd murmur, blacksmith forge, church room tone, dungeon cave/water,
   funhouse, boss room, and weather/realm variants. These require loop-point
   checks and quiet mixing, not one-shot playback.

### Promotion Checklist

- Audition against the existing gameplay event at the intended in-game volume.
- Create only a derived runtime asset under `assets/sounds/` or `assets/music/`;
  keep the original bundle file under `unused_assets/`.
- Trim silence, remove problematic peaks, apply short fades, and preserve the
  source sample rate where practical. Use OGG for long loops.
- Record source bundle, provider, original filename, derived filename, and
  intended route in `ASSET_PROVENANCE.md`.
- Add/update the sound-manager route and a focused asset-resolution test only
  when the selected asset is ready to ship.

Future audio enhancements such as spatial audio, dynamic combat-intensity
music, randomized SFX, audio ducking, sound profiles, and per-entity sound
customization require a settings or audio-content spec before implementation.

Source-specific SFX routing should continue to use stable event payload fields
instead of broad name guessing. Add new payload fields through
`EVENT_EMISSIONS.md` only when a concrete audio or presentation consumer needs
them.

## Development Without Sound Files

The sound system gracefully handles missing audio files:
- Missing sounds are logged but don't cause errors
- Game continues to function normally
- Use `tools/generate_placeholder_sounds.py` to create simple beeps for testing

## Generating Placeholder Sounds

For development without proper sound assets:

```bash
# Generate all placeholder sound effects
./.venv/bin/python tools/generate_placeholder_sounds.py

# Specify custom output directory
./.venv/bin/python tools/generate_placeholder_sounds.py --output path/to/sounds
```

**Note**: Placeholder sounds are simple sine wave tones. Replace with professional sound effects for production.

## Configuration

### Pygame Mixer Settings

Default settings (configured in `SoundManager.__init__`):
- **Frequency**: 44100 Hz
- **Size**: 16-bit
- **Channels**: 2 (stereo)
- **Buffer**: 512 samples
- **Simultaneous sounds**: 16 channels

### Default Volumes

- **Master**: 1.0 (100%)
- **SFX**: 0.7 (70%)
- **Music**: 0.1 (10%)

## Performance Notes

- **Sound caching**: SFX are loaded once and reused
- **Music streaming**: Music files are streamed, not cached
- **Channel limit**: Up to 16 sounds can play simultaneously
- **Small file sizes**: Keep SFX under 100KB when possible

## Troubleshooting

### No Sound Playing

1. Check if pygame.mixer initialized:
   ```python
   import pygame
   print(pygame.mixer.get_init())  # Should return settings tuple
   ```

2. Check sound files exist:
   ```bash
   ls -la src/ui_pygame/assets/sounds/
   ```

3. Check volume levels:
   ```python
   print(sound_manager.enabled)
   print(sound_manager.master_volume)
   ```

### Sound Cutting Out

- Increase buffer size in `SoundManager.__init__`
- Reduce number of simultaneous channels
- Use compressed audio formats (OGG) instead of WAV

### Music Not Looping

- Ensure music file has seamless loop points
- Use OGG format which supports better looping
- Check `loops` parameter is set to -1

Future audio enhancements are tracked in the Audio Gates section above.

## Deferred Format Optimization

Long runtime music, ambience, and multi-second effects now use OGG where that
meaningfully reduces package size. Preserve high-quality masters in an
owner-controlled archive, then verify playback through Pygame and a fresh
frozen-artifact smoke test after replacing or reconverting an asset.
