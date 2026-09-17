# Sound Effects Directory

This directory contains sound effects for The Forsaken Tenet.

## Supported Formats

- `.wav` - Uncompressed audio (best for short sound effects)
- `.ogg` - Compressed audio (good for longer sounds)

## Sound Effect Categories

### Combat Sounds
- `combat_start.wav` - Combat begins
- `hit.wav` - Normal attack hit
- `heavy_hit.wav` - Heavy damage hit (>50 damage)
- `critical_hit.wav` - Critical hit
- `miss.wav` - Attack missed
- `block.wav` - Attack blocked/parried
- `victory.wav` - Combat won
- `defeat.wav` - Combat lost
- `flee.wav` - Fled from combat

### Spell/Ability Sounds
- `spell_cast.wav` - Generic spell casting
- `spell_fire.wav` - Fire spell
- `spell_ice.wav` - Ice/frost spell  
- `ice_spell.ogg` - Ice/frost spell and skill effect
- `laser_beam.wav` - Laser weapon-damage effect
- `bird_attack_sound.wav` - Screech/lightning-bird call effect
- `spell_lightning.wav` - Lightning/shock spell
- `spell_heal.wav` - Healing spell
- `spell_buff.wav` - Buff spell
- `shield_block_metal_weapon.wav` - Shield block impact effect
- `blade_parry.wav` - Blade-equipped parry (dagger, sword, longsword, battle axe, or polearm)
- `metal_weapon_disarm.wav` - Metal main-hand weapon knocked away by Disarm
- `underground_spring.ogg` - Underground spring interaction ambience
- `open_door.ogg` - Door-opening effect
- `spell_debuff.wav` - Debuff spell
- `distorted_scream.wav` - Scream/howl/nightmare skill effect
- `mortal_strike.wav` - Mortal Strike skill effect

### Status Effect Sounds
- `poison.wav` - Poison/bleed applied
- `stun.wav` - Stun/freeze applied
- `burn.wav` - Burn applied

### Character Sounds
- `heal.wav` - Healing received
- `level_up.wav` - Character leveled up
- `player_death.wav` - Player died
- `enemy_death.wav` - Enemy died

### UI Sounds
- `menu_select.wav` - Menu option selected
- `menu_confirm.wav` - Menu confirmed
- `menu_cancel.wav` - Menu cancelled
- `item_pickup.wav` - Item picked up
- `item_equip.wav` - Item equipped
- `coin.wav` - Gold obtained
- `door_open.wav` - Door opened
- `chest_open.wav` - Chest opened

## Adding New Sounds

1. Place sound files in this directory
2. Use descriptive names (lowercase, underscores)
3. Keep files small (<100KB for SFX recommended)
4. Use 44100Hz sample rate for compatibility

## Runtime Organization And Provenance

All short effects live directly in this directory regardless of origin. The
runtime path is intentionally not a provenance classification: the
Sonniss-derived custom effects are `bird_attack_sound.wav`, `blade_parry.wav`,
`distorted_scream.wav`, `ice_spell.ogg`, `laser_beam.wav`,
`mortal_strike.wav`, `open_door.ogg`, `shield_block_metal_weapon.wav`, and
`underground_spring.ogg`, and `metal_weapon_disarm.wav`. Other current effects are OpenAI-generated
placeholders or effects. See [`docs/ASSET_PROVENANCE.md`](../../../../docs/ASSET_PROVENANCE.md)
before distributing or replacing an asset.

Background music remains in `assets/music/`: it is streamed and looped through
`pygame.mixer.music`, whereas these short effects are cached as
`pygame.mixer.Sound` instances.

## Creating Placeholder Sounds

For development, you can use the `tools/generate_placeholder_sounds.py` script to create simple beep sounds as placeholders.
