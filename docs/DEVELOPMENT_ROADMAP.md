# The Forsaken Tenet Development Roadmap

*Updated: September 20, 2026*

This roadmap contains the current priority, completed baseline summaries needed
for sequencing, ordered candidates, and deferred decision gates. Detailed
shipped history belongs in [`CHANGELOG.md`](../CHANGELOG.md), and runtime
contracts belong in their owner documents.

## Current Baseline

- Pygame is the supported player-facing frontend. Core logic lives under
  `src/core/`; headless tests, simulators, and reports provide non-graphical
  development coverage.
- Flat global progression and all 49 authored class ability trees are shipped.
  [`ABILITY_TREE_DESIGN.md`](ABILITY_TREE_DESIGN.md),
  [`PROMOTION_ABILITY_RULES.md`](PROMOTION_ABILITY_RULES.md), and the
  [`ability_trees/`](ability_trees/) references define the current contract.
- Critical promotion class-kit closure is shipped. Remaining class-kit work is
  evidence-driven tuning, presentation, or separately approved expansion.
- Multi-enemy combat supports one or two enemies through direct APIs and
  development encounter overrides. Ordinary random encounters remain
  singleton.
- The Vesperion/Voluntas endgame route, Class Ring awakening paths, Pygame
  dungeon/town/combat flows, and the current save contract are implemented.

## Planning States

- `Active`: the next planning or implementation program.
- `Ready`: sufficiently bounded to begin after higher-priority work.
- `Spec Gate`: requires an approved behavior and compatibility contract before
  implementation.
- `Evidence Gate`: requires focused automated or manual evidence before a
  decision.
- `Deferred`: intentionally postponed until its dependency is complete.
- `Watch`: preserve current behavior and record issues encountered nearby.

## Completed Milestone — Foundational Gameplay Refactors

Status: `Complete — Foundational Baseline Established`

[`FOUNDATIONAL_REFACTOR_PLAN.md`](FOUNDATIONAL_REFACTOR_PLAN.md) records the
completed contract: immutable ability slugs and taxonomy, version-2 saves,
one-roll contact, virtual readiness, core concealment and targeting, the
action interface, and bounded multi-enemy support. Its committed reports are
the baseline for all subsequent evidence. Ordinary random encounters remain
singleton because no Pilot 3 pair qualified; dungeon rest remains deferred.

## Active Priority — Post-Foundation Stabilization And Playtest

Status: `Active — Evidence Collection And Reliability Hardening`

Use [`playtest/CURRENT.md`](playtest/CURRENT.md) and
[`CLASS_KIT_EVIDENCE_NOTES.md`](CLASS_KIT_EVIDENCE_NOTES.md) to collect broad
manual evidence against the completed baseline. Record reproducible defects
and promote numeric, content, or architecture changes only through their owner
gate. Do not tune combat values merely to resolve an observation.

The ordered stabilization work is:

1. Run the post-refactor smoke, class-kit, progression/interface, and
   world/story evidence queues.
2. Fix reproducible correctness defects, starting with broad exception handling
   in save, progression, simulator, and combat-presentation paths.
3. Extend strict typing through stable non-Pygame contracts and converge
   remaining compatibility seams only when covered by focused regressions.
4. Decompose the largest combat and Pygame functions behind preserved behavior
   and tests.
5. Promote one evidence-supported tuning or presentation slice at a time.

Package-barrel cleanup, asset optimization/LFS evaluation, and public-release
infrastructure (platform builds, release attachments, provenance, and branch
protection) are separate infrastructure initiatives. Do not bundle them into
numeric combat tuning.

### September 2026 Repository Audit Hardening

Status: `Complete — Approved Follow-ups Landed; Residual Backlog Tracked`

The post-foundation repository audit covered gameplay correctness, persistence,
runtime contracts, frontend loops, stale code, assets, static-analysis scope,
and active documentation. The current bounded implementation completed the
following work without choosing new combat or compatibility behavior:

- Fixed the Devil's reachable Regen crash and neutral fallback for unrecognized
  damage types, with direct final-boss regressions.
- Made foundational event, result, action-queue, and base-effect annotations
  runtime-resolvable through a dependency-free combatant protocol; broader
  effect-module annotation cleanup remains incremental.
- Stopped atomic saves from stringifying unsupported runtime objects and kept
  failed writes from replacing the prior save.
- Isolated raw cached quest JSON from runtime reward compilation.
- Removed silent exception suppression from Soul Vessel, player gold bonuses,
  and shield-block class-kit/event rules, preserving their existing tested
  behavior.
- Replaced quadratic inventory flattening in loot and Bestiary presentation,
  and throttled the confirmed busy loop in the empty-chest popup.
- Made the Warlock familiar specialization regression deterministic by fixing
  its previously uncontrolled spell-contact roll.
- Reconciled the root status, mobile status, ability ownership, GUI launch, save
  history, and tracked-tools documentation with the current repository.

The approved follow-up delivered schema-version 2 registries and atomic invalid
save rejection, neutral (`0.0`) ultimate Physical resistance, typed combat
intents and explicit forced-action cancellation, context-local deterministic
randomness for combat-reachable core draws, and narrow exception handling in
save/progression/combat/simulator paths. Version-1 saves are intentionally
rejected with a restart message.

The Pygame frontend now has a typed screen stack, normalized pointer/text/key
input, a 60 FPS owner clock, and a single direct event-queue boundary. Legacy
blocking screens use the centralized compatibility event source while their
state-by-state conversion continues. Verified-unused tutorial, standalone
sex/stat screens, generic sprite tools, alternate presenters, composite-effect
facade, and the completed taxonomy migration script were removed.

CI now checks Ruff B004/B023/B039, strict types for the new stable contracts,
and a committed asset budget: a 240,718,690-byte baseline, 5 MiB aggregate
allowance, and 4 MiB per-file cap.

Bounded implementation backlog:

- Triage noncritical broad exception handlers outside saves, progression,
  combat resolution, simulator policy, and migrated runtime observers.
- Convert the centralized legacy `show()`/`navigate()` loops to native
  `ScreenRuntime` states, prioritizing save/load, town/dungeon/combat, level-up,
  story, and ending transitions; then remove `get_events()` compatibility use.
- Extend runtime annotation resolution and strict mypy coverage beyond the
  current stable contracts, and stage selected Ruff correctness rules after
  triage.
- Decompose unrelated large combat, status, serializer, and Pygame functions
  only behind preserved behavior tests.
- Migrate remaining non-core/global random sites as they become
  simulation-reachable; the combat simulator and core draws are isolated now.
- Perceptually review asset recompression before changing any shipped image or
  audio; the budget gate prevents unreviewed growth but does not optimize.

## Completed Evidence — Multi-Enemy Pilot 3 Rebenchmark

Status: `Complete — Rollout Blocked By Post-Refactor Evidence`

The post-refactor floor-3/floor-4 matrices are complete. No candidate met every
aggregate gate, so ordinary generation remains singleton. The retained reports
and any future qualified-pair work are owned by
[`MULTI_ENEMY_FUTURE_GATE.md`](MULTI_ENEMY_FUTURE_GATE.md). Floor 5 and rosters
larger than two remain deferred.

## Active Program — Broad Manual Playtest

Status: `Active — Foundational Baseline Established`

The comprehensive class-kit, progression, balance, interface, and endgame pass
now begins. Follow the current queue and evidence format above. A reproducible
defect may be fixed when the fix is narrow and does not settle an unapproved
design question. Numeric tuning requires a focused evidence row and promoted
one-page spec.

## Ready After The Foundational Refactors

These are bounded follow-ups, not current priorities:

| Area | State | First safe slice | Owner |
| --- | --- | --- | --- |
| Final-room and ending continuity | `Ready` | Story-card and dialogue continuity only; no boss or route-rule changes. | [`STORY_AND_ENDGAME_DESIGN.md`](STORY_AND_ENDGAME_DESIGN.md) |
| Postgame town fallout | `Ready` | Extend the shipped V1 acknowledgement dialogue only with local, repeat-safe copy. | [`QUEST_STORY_INTEGRATION_DESIGN.md`](QUEST_STORY_INTEGRATION_DESIGN.md) |
| Red Dragon continuity | `Ready` | Copy-only distinction between defeat, restoration, and binding outcomes. | [`STORY_AND_ENDGAME_DESIGN.md`](STORY_AND_ENDGAME_DESIGN.md) |
| Presentation readability | `Evidence Gate` | One UI/log or asset fix supported by a concrete readability finding. | [`PRESENTATION_ASSET_DESIGN_GATES.md`](PRESENTATION_ASSET_DESIGN_GATES.md) |
| Class-kit tuning | `Evidence Gate` | One mechanic and one explicit tuning contract. | [`CLASS_KIT_DESIGN_GATES.md`](CLASS_KIT_DESIGN_GATES.md) |

## Deferred Design Gates

| Area | Required before promotion | Owner |
| --- | --- | --- |
| Durability, identification, item modification, equipment actives, and rarity | State model, current serializer, local-save reset policy, UI, economy, and balance contract. | [`EQUIPMENT_ITEMS_ECONOMY_DESIGN_GATES.md`](EQUIPMENT_ITEMS_ECONOMY_DESIGN_GATES.md) |
| Harvesting, salvage, destructible dungeon features, and deeper Cambion rooms | Content beat, tile state, reward, current persistence, and local-save reset policy. | [`DUNGEON_WORLD_ENCOUNTER_DESIGN_GATES.md`](DUNGEON_WORLD_ENCOUNTER_DESIGN_GATES.md) |
| Broader class-kit systems | One track-specific trigger, state, UI, save, action-economy, and tuning spec. | [`CLASS_KIT_DESIGN_GATES.md`](CLASS_KIT_DESIGN_GATES.md) |
| Guardian rooms, mini-bosses, deeper Reflection, and Vesperion tuning | Story trigger, failure/retry behavior, route compatibility, and balance target. | [`STORY_AND_ENDGAME_DESIGN.md`](STORY_AND_ENDGAME_DESIGN.md) |
| Dynamic/spatial audio and final asset replacement | Concrete asset list, runtime routing, fallback, and settings behavior. | [`SOUND_SYSTEM.md`](SOUND_SYSTEM.md) |
| Profiles, achievements, run summaries, and account-wide Bestiary data | Ownership, privacy, storage, migration, and reset contract. | This roadmap plus a future dedicated spec. |
| Mobile and multi-platform support | Phase 1 semantic-input foundation is in progress. Promotion beyond the shared input/display/runtime foundations still requires a successful Android feasibility spike and explicit release ownership. | [`MOBILE_PLATFORM_ROADMAP.md`](MOBILE_PLATFORM_ROADMAP.md) |
| Broad UI/core cleanup | A concrete duplicated rule or save/testability defect with a bounded extraction plan. | The affected domain owner document. |

## Watch Items

Do not promote these observations directly into numeric or architectural
changes:

- Footpad early damage and survivability.
- Poison duration, application, and immunity consistency.
- Multi-strike accuracy and single-action accounting.
- Ironwall Revenge reliability and Repercussion area tuning.
- Resolve generation and Burst cost.
- Race/class balance deltas.
- Bounty restock pacing.
- Class Ring preservation effects and high-action-economy class kits.

Record combat findings using
[`COMBAT_BALANCE_DESIGN_GATES.md`](COMBAT_BALANCE_DESIGN_GATES.md) and class-kit
findings using [`CLASS_KIT_EVIDENCE_NOTES.md`](CLASS_KIT_EVIDENCE_NOTES.md).

## Working Rules

1. The roadmap owns priority; domain documents own behavior.
2. `CHANGELOG.md` owns shipped history. Do not leave completed phase narratives
   in the active roadmap.
3. Do not implement a `Spec Gate` by inference from a loose idea.
4. Preserve stable ability, node, event, item, quest, and current-save identifiers
   unless the approved slice explicitly requires a local-save reset.
5. Run focused tests for every changed system before broad validation.
6. Update the owner document and roadmap in the same change when a gate is
   promoted, completed, or deferred.

## Active Slice — Combat Presentation And Playtest Reliability

The current playtest slice improves action readability without changing combat
numbers: a persisted six-slot ability bar, compact fixed commands, a
badge-based timeline without visible readiness calculations, and persistent
environmental-effect feedback. The Character Menu's combined Abilities workspace
splits learned Skills and Spells into icon cards that can be dragged onto shortcut
slots; All Actions remains the full read-only combat catalog.

The slice also standardizes stat-debuff wording and lets non-player actors use
item-gated abilities without carrying or consuming player inventory. Player
item requirements remain unchanged. Focused regressions cover action
availability, anti-magic feedback, debuff text, and enemy/familiar ability use.
Empty shortcut buttons are inert and cannot commit a turn.
Specials and Action Layout are combined into an icon-based Abilities workspace,
  split into learned Skills and Spells with drag-and-drop shortcut assignment.
Victory rewards and level-up mutations are deferred until the enemy fade finishes;
  the pre-reward combat frame remains behind the outcome popup.
Defeated timeline badges remain until their sprites finish fading.
The current actor is integrated into the timeline ribbon, with blue player-side
  and red enemy-side token outlines.
Turned-in collection quests retain their completed collection count instead of
  reverting to zero progress.
Dungeon entry and death clear cached dungeon frames before the next view is
  rendered.
The item-icon map covers every catalog item, including Monocane and crossbow
  equipment and ammunition.
Keyboard menu navigation skips shortcut tiles; shortcuts remain available by
  number key, mouse click, or touch.
Specialist gathering now adds persistent visible resource nodes without
replacing themed enemy drops: Druid/Archdruid harvest botanical reagents and
Assassin harvests Deathcap Mushroom; other classes receive generic discovery
feedback only.

## Shipped — Early Progression, Quest, And Combat Improvements

Ordinary chest Mimic outcomes are now generated from the persisted dungeon seed,
so reloading cannot turn a planned Mimic into a normal chest. Seraphine Voss and
Mara Vale each offer four level-spread side quests, including reusable dungeon
landmark and town-conversation objectives; the early Magic Shop quests provide
route guidance without constraining exploration. Boss fights include Defend,
and Charge now pays off its one-round setup with 2.5× weapon damage while
retaining its contested one-turn stun.

Follow-up tuning makes the two conversation beats staged leads rather than
standalone turn-ins: the Barkeep points Seraphine's commission to the first
descent, and Griswold turns Mara's lead into a Bandit contract. Green and Red
Slimes now share the existing Fungus Spore drop, so the early Spore quest is
open to every class; the Lich commission moves to level 55.

## Shipped — Playtest Presentation And Encounter Follow-Up

Multi-enemy combat now presents explicit previous/next target controls alongside
direct lane selection, with stable distinct hostile-lane colors across the
battlefield and timeline. Debug mode exposes Auto Kill with `K`; normal combat
does not expose it. Victory popups include affected bounty progress.

Trap damage and other acknowledgement-only messages require fresh input before
they can close, and trap feedback blocks movement over the updated dungeon
frame. Post-level-10 death now surfaces its existing resurrection gold cost and
possible stat loss in the defeat summary.

Barghest is tuned for a normally geared level-15 encounter with approximately
even baseline initiative pressure. Shop panes identify equipment already worn
in a compatible slot, and shop Quest entries appear only when that giver has an
offer, active quest, or turn-in. The Character Menu separates the learned
ability reference from Action Layout and shows a description while an
assignable action is hovered.

## Deferred Design Gate — Shop Stock And Opening Pacing

No store gate or stock change is approved yet. The current gate and stock-filter
audit is recorded in
[`EQUIPMENT_ITEMS_ECONOMY_DESIGN_GATES.md`](EQUIPMENT_ITEMS_ECONOMY_DESIGN_GATES.md);
the next slice must approve starter access, route guidance, and class-equipment
needs before changing shop availability.

## Playtest Findings
- Level up should show a brilliant light surrounding the player
- Full restoration (like when looting a relic) should appear as a wash over of green/blue energy
- Barghest was nerfed too much; instead of scaling power, increase endurance for a longer fight
