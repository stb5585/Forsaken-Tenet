# Documentation Index

Use this index as the front door for project documentation. The roadmap owns
priority, owner documents define current behavior and decision gates, and
[`CHANGELOG.md`](../CHANGELOG.md) owns shipped history.

## Start Here

- [`DEVELOPMENT_ROADMAP.md`](DEVELOPMENT_ROADMAP.md) — current priorities,
  ordered candidates, and deferred gates.
- [`FOUNDATIONAL_REFACTOR_PLAN.md`](FOUNDATIONAL_REFACTOR_PLAN.md) — completed
  gameplay-refactor contract, implementation record, and preserved boundaries.
- [`CONTACT_MODEL_CONTRACT.md`](CONTACT_MODEL_CONTRACT.md) — active fitted-contact
  behavior and characterization acceptance thresholds.
- [`PLAYTEST_CHECKLIST.md`](PLAYTEST_CHECKLIST.md) — playtest index and current
  evidence policy.

## Gameplay And Progression Contracts

- [`ABILITY_TREE_DESIGN.md`](ABILITY_TREE_DESIGN.md) — authored tree rules,
  identities, and ownership boundaries.
- [`ability_trees/ABILITY_TREE_STATUS.md`](ability_trees/ABILITY_TREE_STATUS.md)
  — completion table and links to all 49 tree references and diagrams.
- [`PROMOTION_ABILITY_RULES.md`](PROMOTION_ABILITY_RULES.md) — promotion,
  retention, closure, and transactional purchase rules.
- [`CLASS_KIT_DESIGN_GATES.md`](CLASS_KIT_DESIGN_GATES.md) — shipped class-kit
  contracts plus separately gated expansion and tuning rules.
- [`CLASS_RING_SYSTEM.md`](CLASS_RING_SYSTEM.md) — awakening, persistent state,
  class-specific effects, and presentation rules.
- [`CLASS_STAT_PRIORITIES.md`](CLASS_STAT_PRIORITIES.md) — player-facing stat
  effects and class priorities.
- [`WIZARD_CROSS_ELEMENT_INTERACTIONS.md`](WIZARD_CROSS_ELEMENT_INTERACTIONS.md)
  — developer-only hidden interaction reference.

## Combat And Encounters

- [`COMBAT_BALANCE_DESIGN_GATES.md`](COMBAT_BALANCE_DESIGN_GATES.md) — current
  combat contract, foundational refactor gates, balance evidence, and
  validation commands.
- [`MULTI_ENEMY_COMBAT_DESIGN.md`](MULTI_ENEMY_COMBAT_DESIGN.md) — implemented
  one-or-two-enemy architecture and remaining rollout decisions.
- [`MULTI_ENEMY_FUTURE_GATE.md`](MULTI_ENEMY_FUTURE_GATE.md) — rollout block,
  floor-5 boundary, and larger-roster requirements.
- [`DUNGEON_WORLD_ENCOUNTER_DESIGN_GATES.md`](DUNGEON_WORLD_ENCOUNTER_DESIGN_GATES.md)
  — dungeon interaction, encounter, recovery, and world-content gates.

## Content, Story, Items, And Presentation

- [`STORY_AND_ENDGAME_DESIGN.md`](STORY_AND_ENDGAME_DESIGN.md) — current
  Vesperion/Voluntas canon, route contract, and future story gates.
- [`QUEST_STORY_INTEGRATION_DESIGN.md`](QUEST_STORY_INTEGRATION_DESIGN.md) —
  quest staging, persisted-state normalization, and postgame dialogue boundaries.
- [`EQUIPMENT_ITEMS_ECONOMY_DESIGN_GATES.md`](EQUIPMENT_ITEMS_ECONOMY_DESIGN_GATES.md)
  — equipment, item state, shop, and economy gates.
- [`PRESENTATION_ASSET_DESIGN_GATES.md`](PRESENTATION_ASSET_DESIGN_GATES.md) —
  screen, cue, asset, and generated-bitmap workflow.
- [`DUNGEON_TILE_ART.md`](DUNGEON_TILE_ART.md) — dungeon texture manifest and
  asset-generation instructions.
- [`ENEMY_VISUAL_SYSTEM.md`](ENEMY_VISUAL_SYSTEM.md) — combat sprites, tokens,
  inspection art, and scale rules.
- [`SOUND_SYSTEM.md`](SOUND_SYSTEM.md) — audio runtime, routing, assets, and
  future audio gates.
- [`spreadsheets/README.md`](spreadsheets/README.md) — generated CSV snapshots
  for classes, races, specials, items, enemies, quests, and Google Sheets.

## Architecture And Development References

- [`ARCHITECTURE.md`](ARCHITECTURE.md) — runtime boundaries, public APIs,
  combat/targeting flow, save policy, resource paths, and distribution.
- [`MOBILE_PLATFORM_ROADMAP.md`](MOBILE_PLATFORM_ROADMAP.md) — active,
  incremental native-layout and semantic-input path toward a supported
  desktop-and-Android release while preserving one core game engine.
- [`ASSET_PROVENANCE.md`](ASSET_PROVENANCE.md) — runtime and source asset
  inventory, known provenance, and attribution gaps.
- [`EVENT_EMISSIONS.md`](EVENT_EMISSIONS.md) — event contracts, emitters,
  consumers, and payload-enrichment gate.
- [`CURSES_UI_RETIREMENT.md`](CURSES_UI_RETIREMENT.md) — why Pygame is the only
  supported player-facing frontend and what headless coverage remains.
- [`../tests/README.md`](../tests/README.md) — test layout and commands.
- [`../tools/README.md`](../tools/README.md) — development and asset tools.
- [`../src/core/data/abilities/README.md`](../src/core/data/abilities/README.md)
  — ability-data schema and authoring workflow.

## Playtest References

- [`playtest/CURRENT.md`](playtest/CURRENT.md) — preserved post-refactor manual
  queue and milestone exit criteria.
- [`CLASS_KIT_EVIDENCE_NOTES.md`](CLASS_KIT_EVIDENCE_NOTES.md) — evidence
  ledger and capture format.
- [`history/playtest/SHIPPED_REGRESSIONS.md`](history/playtest/SHIPPED_REGRESSIONS.md)
  — detailed historical/manual regression prompts; not the current queue.
- [`playtest/DEFERRED_SPEC.md`](playtest/DEFERRED_SPEC.md) — features that need
  a promoted design contract before implementation or broad testing.

## Historical Material

[`history/`](history/README.md) contains tracked, browsable records whose
original evidence remains useful but is not current implementation authority.
Local recovery copies under `docs/archive/` are ignored and must not be treated
as current direction. Deleted stale material remains recoverable through Git
history.
