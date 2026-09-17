# Enemy Visual System

Enemy visuals are split into three presentation layers. Each layer solves a different readability problem and should remain separate.

## Layer 1: Combat Sprite

Combat sprites are the active battlefield representation. They are used for the visible enemy body in combat and dungeon-facing combat overlays.

Do not replace combat sprites with portrait-style enemy renders, token crops, item-card art, or rectangular encounter artwork.

Combat sprite loading uses:

1. `EnemyCombatSpriteManager` for transparent PNG loading from `enemy_combat_sprites/`.
2. Exact enemy display-name mappings in `enemy_combat_sprite_map.json`.
3. Boss and generic fallback sprites when a specific combat-sprite file is missing.

Combat sprites must be transparent, full-body creature images with no frame, no label, no rectangular background, and no UI decoration.

The retired `assets/sprites/enemies/` PNG set is not a runtime fallback. Missing or failed enemy combat sprites should fall back through `EnemyCombatSpriteManager` to `generic_enemy`, not to legacy generated sprites.

Current combat-sprite coverage is complete for concrete enemy display names in the `src/core/enemies/` package, excluding the development `Test` enemy and the base `Myrmidon` template. Upgraded variants that share a display name use the same sprite mapping.

Enemies that intentionally change `picture` to a PNG during combat can use form-specific combat sprites. `EnemyCombatSpriteManager` prefers a matching explicit `picture` stem before the display-name map. The Jester uses this for `jester.png`, `jester1.png`, `jester2.png`, `jester3.png`, and `jester4.png`, giving the player a color clue when his combat strategy changes forms.

### Combat Sprite Scale

Combat sprite scale is data-driven through `enemy_combat_sprites/enemy_combat_sprite_scale.json`.

The scale map is used when a sprite needs a different battlefield footprint than the default sprite canvas implies. This is especially useful for large enemies that share the same source image dimensions as small enemies.

Scale lookup uses this order:

1. Exact enemy display name, such as `Minotaur`.
2. Combat sprite key, such as `red_dragon`.
3. The `boss` fallback entry for enemies classified as bosses.
4. Default scale `1.0`.

The live dungeon-backed combat foreground uses a 320px base sprite box before applying the scale multiplier. The classic centered combat renderer uses the current combat pane size for boss-scale enemies and 256px for ordinary enemies before applying the same multiplier. Scale values are clamped between `0.25` and `2.5`.

Only use the scale map for intentional presentation differences. Do not resize source PNG canvases just to make a particular enemy appear larger or smaller in combat.

Dungeon navigation scale is tuned separately through `enemy_combat_sprites/enemy_dungeon_sprite_scale.json`. Use this when an enemy should keep normal combat size but appear smaller or larger as a dungeon-navigation figure. For example, the Jester uses a smaller dungeon scale because he is a human-sized boss rather than a huge monster.

Jester form changes should remain visually legible. When his combat `picture` changes between `jester.png` and `jester1.png` through `jester4.png`, combat briefly alternates between old and new sprites with a small horizontal shudder before settling on the new form.

## Layer 2: Enemy Token

Enemy tokens are compact circular portraits generated automatically from combat sprites. They are used for compact combat UI such as turn/initiative banners, future target lists, future encounter summaries, and other status-heavy layouts.

Player turn banners use the same compact-token presentation, but derive the face token from the player's portrait via `PlayerTokenManager`.

Token generation uses:

1. `EnemyCombatSpriteManager` sprite-key lookup.
2. `enemy_combat_sprites/enemy_token_crop.json` crop override when available.
3. A default centered head-and-shoulders crop when no override exists.
4. Circular framing and token-size caching in `EnemyTokenManager`.

Token crops should be tuned for 64x64 and 96x96 readability.

## Layer 3: Enemy Inspection And Boss Navigation

Enemy inspection panels and boss navigation figures use the same transparent combat sprites as the battlefield view.

This keeps the visible enemy identity consistent between dungeon navigation, combat, target panels, and compact tokens.

The retired `enemy_renders/` atlas and `enemy_combat_art/` artwork set have been moved to `unused_assets/retired_enemy_art/`. The retired generated enemy sprite PNGs have been moved to `unused_assets/retired_enemy_sprites/`.

## Asset Validation

Run this after changing combat sprites to rebuild the review sheet from approved transparent PNGs:

```bash
./.venv/bin/python tools/build_enemy_combat_sprites.py
```

This tool does not generate replacement artwork. Production combat sprites are approved transparent PNG assets stored individually under `src/ui_pygame/assets/enemy_combat_sprites/`.

## Future Sprite Generation Requirements

Future enemy sprite prompts must preserve enemy distinctions at token size, not only at full combat-panel size.

- Goblin: green skin, large ears, yellow eyes, hunched raider silhouette.
- Kobold: reptilian, scaled skin, narrow snout, smaller tunnel-creature profile.
- Bandit: human, leather hood or outlaw gear, visible face.
- Cultist: robes, mask, ritual elements, occult silhouette.
- Orc: larger than goblin, tusks, heavier jaw and armor.
- Skeleton Warrior: helmet, armor, weapon silhouette distinct from basic skeleton.
- Dire Wolf: larger, darker, more scarred and aggressive than wolf.
- Ooze: darker and more corrosive than slime.
- Greater Demon: larger horns and more imposing facial structure than demon.
- Wyrm: serpentine profile distinct from broader dragon head.
