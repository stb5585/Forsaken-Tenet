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

The Thirsty Dog exterior and interior opening backgrounds were generated with
the built-in Codex image-generation workflow on November 19, 2026. Their
checked-in comparison is `docs/assets/review-sheets/opening-location-backgrounds.png`.

The Silvana barracks map-room background was generated with the built-in Codex
image-generation workflow on November 25, 2026. The prompt requested an empty,
wide dark-fantasy military planning room with a scarred ledger table, practical
weapon storage, rainy windows, warm lantern light, and stable left/center/right
zones for staged dialogue cutouts. The 1672×941 generation is retained as the
high-resolution runtime variant; the 1024×768 export uses the same art and a
centered cover crop. Both appear on the opening-location review sheet above.

The Silvana graveyard background was generated with the built-in Codex
image-generation workflow on November 26, 2026. The prompt requested an empty,
rain-dark medieval graveyard beside Silvana's walls, with a fresh grave, simple
marker, funeral lanterns, a weathered chapel, and open left/center/right staging
zones for the existing dialogue cutouts. The 1448×1086 generation is retained
as the high-resolution runtime variant; the 1024×768 runtime export uses the
same composition.

The 70 transparent `player_dialogue/` cutouts were generated with the built-in
Codex image-generation workflow on November 21, 2026. Each race/sex/variant
asset used its corresponding character-creation face-atlas cell as the identity
and style reference; the previously approved `human_male_5.png` pilot remains
part of that complete set.

The transparent `timmy.png`, `timmy_mother.png`, and `timmy_father.png`
dialogue cutouts were generated with the built-in Codex image-generation
workflow on November 25, 2026. Timmy used the approved Waitress and Caedmon
cutouts as style references; each parent used Timmy for family resemblance and
the approved town NPCs for rendering direction. The 1024×1536 generation
outputs were exported as 512×768 runtime PNGs; Timmy retains additional
transparent margin so he stages at a child-appropriate height.

| Runtime directory | Purpose | Distribution |
| --- | --- | --- |
| `ability_icons/`, `effects/`, `item_icons/`, `ui/` | Ability, effect, item, and interface atlases/icons | Required |
| `backgrounds/` | Menu, town, shop, and dungeon backgrounds | Required |
| `companion_art/`, `enemy_combat_sprites/`, `npc_art/` | Combat and dialogue character artwork | Required |
| `dungeon_tiles/` | First-person dungeon surfaces and special-tile art | Required |
| `item_art/`, `key_items/` | Equipment, consumable, material, and story-item renders | Required |
| `portraits/`, `sprites/` | Player portraits, tokens, and NPC sprites | Required |
| `player_dialogue/` | Appearance-ID-matched transparent player dialogue cutouts | Required |

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
