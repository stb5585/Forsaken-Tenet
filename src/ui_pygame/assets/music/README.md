# Music Directory

This directory contains background music for The Forsaken Tenet.

## Supported Formats

- `.ogg` - Recommended (compressed, loopable)
- `.mp3` - Supported but OGG preferred
- `.wav` - Supported for local/staged assets; convert to OGG for final compressed tracks when practical

## Music Tracks

### Locations
- `town.ogg` - Town/hub area theme
- `shop.ogg` - Shop ambient music
- `church.ogg` - Church ambient music
- `inn.ogg` - Inn/tavern music
- `eerie_dungeon_background.wav` - Current staged dungeon theme; resolved by the runtime `dungeon` theme alias

### Dungeons
- `dungeon.ogg` - Generic dungeon theme
- `dungeon_floor1.ogg` - Early dungeon floors
- `dungeon_floor2.ogg` - Mid dungeon floors
- `dungeon_floor3.ogg` - Deep dungeon floors
- `dungeon_final.ogg` - Final dungeon area
- `funhouse.ogg` - Funhouse challenge area
- `realm_of_cambion.ogg` - Realm of Cambion area

`dungeon` is used on ordinary dungeon levels 1–5 (and any non-special
side-area level). `dungeon_final`, `funhouse`, and `realm_of_cambion` are
separate runtime themes for levels 6, 7, and 8 respectively. The latter three
tracks are currently required assets; their absence is reported by audio
diagnostics and degrades safely until they are supplied.

### Combat
- `combat_normal.ogg` - Normal combat music
- `combat_boss.ogg` - Boss battle music
- `combat_final.ogg` - Final boss music

### Events
- `menu.ogg` - Main menu screen
- `victory.ogg` - Victory fanfare
- `game_over.ogg` - Game over screen

## Music Requirements

- Should loop seamlessly
- Recommended length: 1-3 minutes per track
- Keep file size reasonable (<5MB per track)
- Use 44100Hz sample rate, stereo

## Creating Placeholder Music

For development without music assets, the game will simply run without background music. The sound system gracefully handles missing files. Theme aliases may point a stable runtime name, such as `dungeon`, at a more descriptive staged filename while final track names are still being settled.
