# Foundational Gameplay Refactor Plan

Status: `Complete — Foundational Baseline Established`

This document organizes the gameplay-changing work that should be resolved
before broad manual playtesting. It does not approve new mechanics by itself.
Each phase must first replace its open questions with an explicit decision
block covering runtime behavior, UI behavior, compatibility, and validation.

## Why This Precedes Broad Playtesting

Combat timing, targetability, ability classification, encounter size, and the
combat action interface shape nearly every playtest observation. Testing class
balance, pacing, and readability extensively before those foundations settle
would produce short-lived evidence. Focused manual checks remain appropriate
inside each implementation slice; the comprehensive playtest queue resumes
after the refactor baseline is stable.

## Dependency Order

### 1. Ability Taxonomy And Ownership

State: `Approved`

Define canonical metadata for each spell and skill without changing stable
ability IDs merely to improve organization.

The taxonomy should decide:

- origin: arcane, divine, natural, spiritual, extraplanar, innate, or another
  approved set;
- method: manifestation, binding, transformation, channeling, projection, or
  another approved set;
- intent: damage, protection, restoration, control, mobility, information,
  summoning, or another approved set;
- active, passive, reaction, field, summon, and item-action boundaries;
- target scope and target-loss behavior;
- which module owns behavior versus declarative data; and
- how hidden interactions such as Wizard cross-element effects are represented
  without disclosing them in player-facing descriptions.

Implementation should migrate metadata and ownership in small batches with
loader validation and stable-ID regression coverage. File reorganization is a
consequence of the contract, not the first step.

Owner references:

- [`src/core/data/abilities/README.md`](../src/core/data/abilities/README.md)
- [`PROMOTION_ABILITY_RULES.md`](PROMOTION_ABILITY_RULES.md)
- [`MULTI_ENEMY_COMBAT_DESIGN.md`](MULTI_ENEMY_COMBAT_DESIGN.md)
- [`WIZARD_CROSS_ELEMENT_INTERACTIONS.md`](WIZARD_CROSS_ELEMENT_INTERACTIONS.md)

### 2. Combat Timing, Speed, And Accuracy

State: `Approved`

Define one combat timing model before extending the existing action-queue helper
or replacing the actor-cycle UI.

The decision must cover:

- initiative and turn ordering;
- whether Speed changes order, action frequency, accuracy, dodge, or a bounded
  subset of those effects;
- elimination of unintended Dexterity or Speed double counting;
- minimum and maximum turn frequency;
- delayed, charged, forced, companion, summon, Totem, and reaction actions;
- status-tick timing and defeat during pre-turn processing;
- deterministic simulator behavior and diagnostics; and
- whether current saves or in-progress combat snapshots are affected and
  whether local saves must be reset.

Numeric balance changes should follow the structural implementation and a new
simulator baseline rather than being bundled into the architecture change.

Owner reference: [`COMBAT_BALANCE_DESIGN_GATES.md`](COMBAT_BALANCE_DESIGN_GATES.md).

### 3. Visibility, Reveal, And Targetability

State: `Approved`

Define invisibility as a targeting rule shared by combat logic, AI, ability
metadata, and presentation.

The decision must cover:

- whether an invisible enemy can be selected by single-target actions;
- whether area actions can affect an unrevealed enemy;
- Sight, detection, Wisdom, class-feature, and scripted reveal sources;
- sprite, token, HP/MP, status, and target-card visibility;
- target loss after an action is chosen;
- AI behavior when no legal visible target exists; and
- boss, trial, transformation, and multi-enemy exceptions.

Do not implement a Pygame-only concealment rule. Core target validation must be
authoritative.

Owner references:

- [`COMBAT_BALANCE_DESIGN_GATES.md`](COMBAT_BALANCE_DESIGN_GATES.md)
- [`MULTI_ENEMY_COMBAT_DESIGN.md`](MULTI_ENEMY_COMBAT_DESIGN.md)
- [`ENEMY_VISUAL_SYSTEM.md`](ENEMY_VISUAL_SYSTEM.md)

### 4. Multi-Enemy Scope And Combat View

State: `Approved; Post-Refactor Evidence Required Before Rollout`

First rerun the Pilot 3 promoted-class matrices now that all authored trees are
complete. Then decide:

- whether curated pairs enter ordinary encounter generation;
- eligible floors, probability, exclusions, telemetry, and a runtime kill
  switch;
- the representative floor-5 second-promotion matrix;
- enemy-authored area-action behavior;
- whether the supported roster remains capped at two;
- battlefield slots, sprite scale, flying offsets, turn-order display, target
  cards, and status readability; and
- reward, quest, Bestiary, loot, and kill-credit behavior for every member.

Do not use local encounter multipliers to hide a class-matrix or action-contract
problem. Do not expand beyond two enemies until the UI and action model have an
approved larger-roster contract.

Owner references:

- [`MULTI_ENEMY_COMBAT_DESIGN.md`](MULTI_ENEMY_COMBAT_DESIGN.md)
- [`MULTI_ENEMY_FUTURE_GATE.md`](MULTI_ENEMY_FUTURE_GATE.md)

### 5. Combat Actions And Resource Presentation

State: `Approved`

Replace or extend the combat ability menus only after ability categories and
combat timing are stable.

The decision must cover:

- a bounded or unbounded action shortcut bar;
- assignment, rearrangement, defaults, empty slots, and controller/keyboard/
  mouse behavior;
- current-save ownership of player layouts and any required local reset;
- access to actions not placed on the shortcut bar;
- separation of active, passive, reaction, and unavailable abilities;
- spellbook and Character Menu responsibilities;
- charged-action preparation and cancellation;
- class-resource meters below HP/MP, including overflow and color/accessibility;
  and
- multi-target selection and action preview.

The first implementation slice should preserve keyboard behavior and expose the
new model behind a compatibility adapter before removing the current picker.

Owner references:

- [`PRESENTATION_ASSET_DESIGN_GATES.md`](PRESENTATION_ASSET_DESIGN_GATES.md)
- [`CLASS_KIT_DESIGN_GATES.md`](CLASS_KIT_DESIGN_GATES.md)
- [`CLASS_RING_SYSTEM.md`](CLASS_RING_SYSTEM.md)

### 6. Dungeon Rest And Recovery

State: `Deferred By Decision`

Decide whether resting is part of this foundational milestone or a later
exploration feature. A promoted spec must define recovery amounts, resource
reset behavior, interruption odds, initiative loss, usable tools/items,
location restrictions, save behavior, and the relationship to Inns and other
recovery services.

Owner reference:
[`DUNGEON_WORLD_ENCOUNTER_DESIGN_GATES.md`](DUNGEON_WORLD_ENCOUNTER_DESIGN_GATES.md).

## Approved Foundational Decisions

These decisions were approved together because ability identity, timing, and
target legality share one action contract. Implementation must preserve this
dependency order and must not bundle unrelated numeric tuning into the
structural work.

### Ability And Action Contract

- Every YAML ability receives an immutable ID equal to its filename stem.
  Display names and legacy Python class tokens remain aliases.
- Canonical taxonomy uses closed axes: `origin` is `martial`, `arcane`,
  `divine`, `natural`, `spiritual`, `extraplanar`, `innate`, or `alchemical`;
  `method` is `strike`, `projection`, `manifestation`, `binding`,
  `transformation`, `channeling`, `movement`, `command`, or `consumption`;
  `primary_intent` is `damage`, `protection`, `restoration`, `control`,
  `mobility`, `information`, `summoning`, or `utility`; `activation` is
  `active`, `passive`, or `reaction`; and `form` is `direct`, `field`,
  `summon`, or `item_action`.
- Registered namespaced traits express secondary roles and hidden
  interactions. Unknown traits fail validation and `internal.*` traits are
  never player-facing. YAML owns declarative metadata/effects; specialized
  Python modules own only execution that validated effects cannot express.
  Progression remains separate from combat definitions.
- Canonical target scopes are actor-relative. Single-opponent actions retarget
  the current legal focus by default, explicitly locked actions fail if their
  target is lost, and area actions snapshot their roster.
- Six persisted shortcut slots hold typed ability or item references. Attack,
  Defend, Items, All Actions, and Flee remain fixed system commands; contextual
  actions such as Cancel Charge appear only when legal. Unavailable learned
  actions remain visible with a reason.
- Current versioned saves use `schema_version: 2`. Unmarked and version-1 saves are rejected
  with a new-game-required message; no migration is provided for this
  pre-release reset.
- Public contracts introduce typed `AbilityDefinition`, `AbilityTaxonomy`,
  `TargetingPolicy`, `ActionDefinition`, `ActionReference`,
  `ActionAvailability`, timeline entry, visibility state, and combat-resource
  presentation models. Canonical intents carry an action ID and target IDs;
  combat execution accepts canonical `ActionIntent` values; the legacy string
  execution adapter has been removed.
- Actor-relative scopes include `SINGLE_OPPONENT` and `ALL_OPPONENTS`.
  Deprecated enemy-named aliases exist only at the public compatibility
  boundary. Version-2 saves persist shortcut references, but combat timelines,
  visibility observations, encounters, and mid-combat state remain runtime
  only.

### Timing And Resolution Contract

- Combat uses virtual readiness timestamps. Standard actions cost 100 units.
  Tempo is current effective Speed divided by the encounter-start median,
  clamped to `0.75-1.5`; readiness advances by `100 / tempo`.
- Initial readiness adds seeded jitter in `[-10, 10]` and subtracts at most 10
  units of the existing Luck rating. Surprise acts at time zero; forced-last
  conditions follow every initial opponent.
- An actor may not take more than two consecutive normal turns while another
  living actor waits. A round completes after each combatant present at its
  start receives or loses an eligible turn. Reinforcements act immediately but
  enter that completion set next round. Effects tick at owner-turn start;
  stuns and forced skips consume the opportunity, and pre-turn death removes
  the actor before action selection.
- Charges spend their starting turn and resolve at a later owner readiness.
  Manual cancellation spends that later turn and refunds nothing. Reactions
  cost no readiness and are limited to one execution per triggering result.
- Companions, familiars, and Totems remain attached output. An active summon
  continues to replace the player-side actor slot.
- Each strike makes one contact roll. Weapon evasion uses Speed; spell
  accuracy uses Intelligence and spell evasion uses Wisdom plus the existing
  bounded Charisma term. Weapon accuracy also preserves its fitted base,
  proficiency differential, and explicit accuracy modifiers; armor and
  explicit dodge modifiers contribute to weapon evasion. Authored contests
  remain post-contact checks. Always-hit bypasses contact but not resistance
  or immunity.
- The weapon and spell curves are fitted deterministically to the old combined
  hit/dodge distributions with seed 1337 and regularization. Weighted mean
  error must be at most three percentage points and no ordinary cell may
  exceed seven points; failure blocks implementation rather than authorizing
  hand tuning.

### Visibility And Multi-Enemy Contract

- Concealed combatants cannot be selected by single-target hostile actions.
  Hostile damage/control breaks the actor's concealment on commitment even on
  a miss. Defensive, informational, and self-support actions preserve it unless
  explicitly tagged otherwise.
- Area actions include concealed opponents without revealing them. Existing
  Sight sources reveal automatically; area results redact concealed identity.
  Detect spends a turn and checks every concealed foe independently at
  `clamp(25%, 90%, 50% + 2.5% * (Wisdom - 10) + bonuses - concealment)`.
  Success reveals until concealment is reapplied; failure still spends the
  turn.
- Enemy AI Detects when it has no legal hostile target. Otherwise it chooses
  among visible legal targets plus self/area actions, and Defends if nothing
  else is legal. Bosses, trials, and transformations receive no implicit
  exception.
- Default single-target loss is `RETARGET_FOCUS`; charged, delayed, and
  identity-dependent actions can explicitly use `LOCKED`, and area actions use
  `SNAPSHOT_ROSTER`. If no legal retarget exists, the action fails with clear
  diagnostics while retaining its time and resource cost.
- Supported hostile rosters remain capped at two. Enemy area actions use the
  same structured all-opponents result pipeline; the initial player side has
  one active player-or-summon slot.
- Ordinary generation remains singleton until the new model is benchmarked.
  Passing authored floor-3/4 pairs occur 15% of the time behind a default-on
  runtime kill switch. Tutorials, quests, chests, bosses, trials, and scripted
  encounters are excluded. Telemetry records encounter key, roster, timeline
  turns, invalid intents, and resolution outcomes. If no pair passes the
  existing Pilot 3 bands, rollout stays blocked without local tuning. Floor 5
  remains deferred.

### Presentation And Recovery Contract

- Keyboard keys 1-6 activate shortcuts. Empty shortcut slots are inert and
  shortcuts are excluded from keyboard menu traversal; pointer and touch input
  can still activate them directly. The
  Character Menu's Abilities workspace combines the learned Skills and Spells
  catalog with an icon-based, drag-and-drop shortcut editor; All Actions is a
  read-only combat catalog. Mouse and controller navigation provide equivalent
  selection, target, detail, and cancellation operations.
- Ordinary cave paths can contain persistent gathering nodes. Every character
  sees the node overlay, but Druid/Archdruid identify and harvest Acorn, Vine
  Seed, Fungus Spore, and Hemlock Root, while Assassin identifies and harvests
  Deathcap Mushroom. Harvesting is an explicit interaction; unqualified
  characters receive generic unfamiliar-growth feedback. Node state persists
  per save, including legacy Deathcap-node conversion.
- Shortcut references contain an ability slug or existing item serializer
  token. Missing items leave a disabled assignment. Empty slots auto-fill from
  learned active abilities in acquisition order without overwriting a player
  choice; upgrades replace their predecessor in place.
- YAML abilities declare their own slugs. Active Python abilities in the
  player progression catalogs receive validated canonical slugs from their
  unique catalog names; a rename requires an explicit compatibility alias.
- All Actions lists every learned active action and keeps assigned or
  unavailable entries visible with a specific MP, status, equipment, target,
  item-count, or class-resource reason. Passives and reactions remain read-only
  Spellbook categories. Single targets use legal focus and area actions preview
  all affected lanes.
- Keyboard Q/E, lane clicks, and controller LB/RB change focus. Controller
  parity uses D-pad navigation, A confirm, B back, Y for All Actions, and X for
  resource details.
- The HUD combines the current actor with the next six predicted normal actor
  opportunities. Player-side and enemy-side token outlines reuse the established
  blue and red turn colors, while text retains complete meaning without color.
  Defeated actor badges remain through their sprite fade. Up to three prioritized
  class-resource rows are supplied under stable provider keys; extra rows collapse
  behind an accessible `+N` detail entry.
- The minimum supported layout remains 1024x720 and the existing two enemy
  lanes remain authoritative. Concealed lanes show only a generic presence.
- Dungeon and paid Inn resting are deferred. Current town auto-heal remains
  unchanged throughout this milestone.

## Implementation Sequence

Each slice updates its owner documentation, avoids unrelated numeric tuning,
and is developed as a short sequential branch from the preceding reviewed
foundation:

1. Decision and characterization: approve all gates and freeze ability,
   contact, singleton, and Pilot 3 evidence.
2. Core contracts: add typed models, save rejection, validators, and temporary
   compatibility adapters without changing combat behavior.
3. Ability migration: migrate all 197 YAML definitions in coherent families,
   shrink the legacy allowlist, switch serialization to slugs, and gate the
   complete taxonomy in CI.
4. Resolution: fit and introduce one-roll contact, concealment/Detect,
   symmetric targeting, retarget behavior, and structured enemy areas.
5. Timeline: replace the actor cycle and migrate charges, forced actions,
   reactions, owner-turn statuses, rounds, logs, and simulator diagnostics.
6. Interface: implement shortcuts, All Actions, availability reasons,
   resources, timeline ribbon, concealed lanes, and controller parity.
7. Evidence and rollout: rerun singleton and Pilot 3 matrices and enable only
   qualifying floor-3/4 pairs at 15% behind the kill switch.
8. Closure: remove internal adapters, update baselines and playtest material,
   and record rest as deferred.

Post-foundation interface polish keeps target focus actor-ID based: hostile
lanes remain directly selectable and expose previous/next focus controls with
keyboard and controller labels. Timeline token colors are stable per hostile
lane, while the player remains blue; these colors are presentation only and do
not alter action legality or engine targeting.

Current slice status:

- Decision and characterization: complete in `8e64224`.
- Core contracts: complete; typed models, v2 registry-backed saves, atomic
  invalid-data rejection, and explicit no-v1-migration behavior are established.
- Ability migration: complete; all 197 definitions have canonical IDs,
  taxonomy, aliases, targeting policy, and registered traits. CI rejects any
  incomplete definition and new saves serialize ability slugs.
- Resolution: complete; one-roll contact, core concealment/Sight/Detect,
  canonical target-loss behavior, symmetric enemy-area results, and concealed
  area-result identity redaction are complete.
- Timeline: complete; virtual readiness owns actor scheduling with
  seeded initial jitter, bounded Luck head starts, encounter-median tempo,
  two-consecutive-turn protection, and owner opportunity round accounting.
  Charges are complete: their pending intent records the starting owner turn,
  cannot resolve or cancel on that same opportunity, preserves its committed
  target through subsequent charge ticks, and refunds nothing on cancellation
  or target loss. Forced actions are complete: canonical intents cannot bypass
  Berserk, charge, Jump, or cancellation decisions, and a cancellation stays
  enforced for its owner opportunity after clearing its charge state.
  Reactions now resolve inside their triggering result without advancing
  readiness and cannot re-enter through a counter-result. Statuses now tick
  only at their owner's pre-turn readiness opportunity, including Paladin
  encounter timers. Battle logs record each event's virtual readiness, round,
  actor-turn ID, and scheduled opportunity actor. Simulator results now retain
  a bounded normal-opportunity trace, final actor readiness, monotonic-time
  check, and consecutive-actor diagnostic for deterministic investigation.
- Interface: complete; the Pygame combat surface projects six persisted typed
  shortcut slots as an icon-capable action bar, fixed compact system commands,
  and an All Actions catalog that keeps learned-but-unavailable actions visible
  with an engine-derived reason. The Character Menu Abilities workspace is the
  only shortcut editor. The HUD receives prioritized text-complete class-resource
  rows, active environmental-effect feedback, and a combined current-actor and
  six-token projection of core-owned readiness opportunities; readiness numbers
  remain diagnostic-only.
  Existing concealed enemy lanes retain their generic presence presentation.
  Keyboard menu traversal covers fixed commands rather than shortcut tiles;
  keys 1-6, mouse, and touch directly activate shortcuts. Keyboard/mouse
  operations now have controller parity for navigation, confirmation,
  cancellation, focus, All Actions, and resource details.
- Evidence and rollout: complete; the seed-1337 singleton baseline and all
  three promoted Pilot 3 matrices were regenerated against the completed
  resolution and timeline. No floor-3/4 pair met every existing aggregate
  gate, so `QUALIFIED_PILOT3_PAIR_KEYS` is intentionally empty and ordinary
  generation remains singleton. The default-on rollout kill switch, 15% gate,
  source exclusions, and roster/timeline/intent/resolution telemetry are in
  place for a future evidence-qualified pair; no local balance tuning was made.
- Closure: complete; internal engine, simulator, and Pygame combat consumers use
  `ActionIntent.action_id` and the string execution boundary is removed. The
  regenerated singleton/Pilot 3
  evidence is committed, the playtest queue is rebased onto this baseline, and
  dungeon rest remains deferred by the approved decision.

## Progression Boundary

The flat-level, separate-currency, point-purchased tree system is the current
shipped baseline. All 49 trees were completed after the earlier
progression checkpoint, so that checkpoint is no longer an active plan.

Do not reopen progression as incidental cleanup. A replacement progression
proposal must explicitly decide:

1. whether global levels and separate progression/attribute currencies remain;
2. whether abilities, passives, and promotions share one tree;
3. how learned abilities participate in later class development;
4. how promotions close or carry options forward;
5. which class resources are inherent versus purchased; and
6. how node ownership is serialized and whether local saves must be reset.

State: `Hold Unless Explicitly Promoted`.

## Decision Block Template

Every phase must answer:

```text
Problem:
Current behavior:
Target behavior:
In scope:
Out of scope:
Core owner:
UI surfaces:
Stable IDs and current-save/reset policy:
Failure and fallback behavior:
Automated regression targets:
Focused manual validation:
New simulator or diagnostic evidence:
```

## Milestone Exit Criteria

The foundational refactor milestone is complete when:

- approved core contracts are implemented without unresolved compatibility
  adapters that change gameplay;
- stable identifiers and current-save behavior are validated;
- combat simulator baselines have been regenerated for the new rules;
- the supported combat UI represents every legal action and target state;
- focused automated and manual checks pass for each changed slice; and
- [`playtest/CURRENT.md`](playtest/CURRENT.md) has been rebased onto the new
  gameplay baseline.
