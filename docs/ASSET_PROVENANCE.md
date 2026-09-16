# Asset Provenance And Distribution Inventory

Status: `Stabilization baseline — owner-confirmed provenance`

This inventory separates files required by the game from review and source
material. The repository's MIT license covers project code and documentation;
it does not establish rights for third-party media whose original terms are
not recorded.

## Runtime Visual Assets

The owner reports that the current visual assets were generated with GPT image
generation through the Codex plugin in VS Code. No third-party artist or stock
library is currently recorded for these categories.

| Runtime directory | Purpose | Distribution |
| --- | --- | --- |
| `ability_icons/`, `effects/`, `item_icons/`, `ui/` | Ability, effect, item, and interface atlases/icons | Required |
| `backgrounds/` | Menu, town, shop, and dungeon backgrounds | Required |
| `companion_art/`, `enemy_combat_sprites/`, `npc_art/` | Combat and dialogue character artwork | Required |
| `dungeon_tiles/` | First-person dungeon surfaces and special-tile art | Required |
| `item_art/`, `key_items/` | Equipment, consumable, material, and story-item renders | Required |
| `portraits/`, `sprites/` | Player portraits, tokens, and NPC sprites | Required |

The packaged map definitions and their 32-pixel editor tiles live under
`src/core/data/maps/`. Map JSON/TMX metadata is project-authored runtime data;
the tile images follow the same reported GPT-generated provenance as the other
visual assets.

## Audio

`src/ui_pygame/assets/sounds/` and `src/ui_pygame/assets/music/` are required
runtime audio. The owner confirms that `sounds/` contains both
OpenAI-generated effects and custom effects derived from the royalty-free
[Sonniss GameAudioGDC collection](https://sonniss.com/gameaudiogdc/). The
custom runtime filenames are listed in `sounds/README.md`; they were clipped,
modified, or layered to create project-specific sounds. Music remains in its
own directory because it is streamed separately from sound effects, not because
it has a different provenance category.

The exact source filename or annual bundle for each transformed Sonniss asset
is not recorded. Before public distribution, retain a copy of the applicable
Sonniss terms with the project and add per-file source mappings if the release
process requires them. Do not infer individual creators or source filenames.
Long custom runtime assets are now shipped as OGG derivatives, including
`music/dungeon.ogg` and `sounds/underground_spring.ogg`. Preserve the original
source-quality WAV files in `unused_assets/` or another owner-controlled archive
before replacing a runtime asset. Pygame 2 supports OGG playback; use it for
music, ambience, and multi-second effects where package size matters.

## Generated Review And Source Material

- `docs/assets/review-sheets/` contains generated visual contact sheets. They
  are documentation-only and excluded from the PyInstaller artifact.
- `docs/spreadsheets/` contains generated catalog CSVs. They are review data,
  not runtime resources, and are excluded from the artifact.
- `docs/ability_trees/` contains generated diagrams used for design review,
  not runtime resources.
- Local `unused_assets/` is a source/reference workspace ignored by Git and
  excluded from builds. Its contents are not covered by this tracked inventory.
- The tracked `ascii_files/` enemy-art directory and its unused conversion
  utilities belonged to the retired curses frontend and were deleted. They
  remain recoverable from the `curses-ui-final` Git tag and repository history.

If binary history makes clone size a maintenance problem, evaluate Git LFS in
a separately planned repository-maintenance task. Any adoption must inventory
the exact file patterns, coordinate with every active clone, preserve recovery
references, and explicitly approve the history rewrite; it must not occur as
incidental asset cleanup.
