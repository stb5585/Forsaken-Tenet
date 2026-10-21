# Quest Story Integration Design

Status: `Holy Relics V1 Implemented; Quest Audit Accepted; Opening Packet Ready`

This document owns quest-system changes whose purpose is to stage story
information, preserve mystery, and keep quest guidance aligned with the
Forsaken Tenet canon. It complements `STORY_AND_ENDGAME_DESIGN.md`, which owns
the late-game Vesperion, Voluntas, Liminal Gap, and true-final route.

## Holy Relics Staged Mystery Chain

The level-1 main quest no longer tells the player to collect all six Holy
Relics immediately. That framing is mechanically useful but narratively too
certain: early NPCs should not understand the ultimate goal, the relic pattern,
or the identities behind the conflict.

The shipped chain starts with Sergeant-led uncertainty:

1. `Uncertain Reports` introduces patrol losses, sealed rooms, old symbols, and
   contradictory witness accounts.
2. `Cry Havoc!` points at the Barghest as a dangerous lead near one sealed
   chamber, not as the confirmed first guardian of six relics.
3. Finding the first relic updates `Uncertain Reports` to a report-back stage.
4. Turning in `Uncertain Reports` creates `The Holy Relics` as the long
   collection quest.
5. `The Holy Relics` then preserves the existing six-relic collection and final
   threshold gating behavior.

The exact opening sequence, copy, saved choices, migration behavior, and
verified runtime anchors are owned by
[`PROLOGUE_TRIANGULUS_PRODUCTION_PACKET.md`](PROLOGUE_TRIANGULUS_PRODUCTION_PACKET.md).

Early-game copy must not name Vesperion, Voluntas, the busboy identity, the
Hooded Figure truth, or true-final route mechanics. It may hint at old
principles, relic-light, sealed chambers, and incomplete reports.

## Accepted Campaign Quest Classification

The campaign audit assigns each of the fourteen entries currently authored
under `Main` to one accepted role:

| Current quest | Accepted category | Campaign role |
| --- | --- | --- |
| `Uncertain Reports` | Main | Chapters 1-2 investigation. |
| `The Butcher` | Progression | Sole gate from level 1 to level 2; independent of the Triangulus Main route. |
| `Cry Havoc!` | Main | Chapter 2 Barghest confrontation. |
| `The Holy Relics` | Main | Chapters 2-8 aggregate campaign spine. |
| `Payback` | Side | Chapter 3 supporting threat. |
| `Ignis Equus` | Main | Chapter 3 Quadrata route. |
| `Lapidation` | Side | Chapter 4 supporting survivor arc. |
| `The Power of Elysia Compels You!` | Main | Chapter 4 Hexagonum route. |
| `Immovable Object` | Progression | Chapter 5 floor gate. |
| `A Bad Dream` | Main | Chapter 5 discovery of Joffrey's death. |
| `In the Day of Our Lord` | Main | Chapter 5 Domingo confrontation. |
| `Dracarys` | Main | Chapter 6 post-Polaris barrier. |
| `No Laughing Matter` | Side | Chapter 6 supporting false-guidance arc. |
| `Hotter Than Hades` | Main | Chapter 7 Infinitas route. |

`Main` is reserved for causal story progression. Every Main quest uses
explicit story-state prerequisites; character level is only a secondary
eligibility check. `Progression` is a distinct authored category for required
mechanical gates that do not advance the central narrative. `Side` remains
the runtime category for optional supporting content and may receive chapter
role metadata. `Bounty` remains outside the authored campaign route.

The current runtime still assumes `Main`, `Side`, and `Bounty`.
`Progression` therefore remains an accepted implementation contract until the
loader, player state, advancement helpers, Pygame quest surfaces, serializers,
normalization, and regressions are migrated together. Content must not move
`The Butcher` or `Immovable Object` in isolation.

`The Butcher` joins `Immovable Object` in Progression. The Minotaur remains the
unavoidable guard before the only stair from level 1 to level 2, but defeating
it does not cause access to the level-1 Barghest, Triangulus, or first-relic
report. Its target, level, rewards, coordinates, combat, and gate remain
unchanged.

Static verification confirms that `Cry Havoc!` currently has no `Requires`
field and Pygame's generic prerequisite path accepts only a quest that has
already been turned in. The opening implementation must therefore use shared
story-state eligibility for active `Uncertain Reports` plus the completed
ledger scene. Adding `Requires: Uncertain Reports` would be incorrect because
it would delay the Barghest lead until after Triangulus report-back.

`The Holy Relics` remains the aggregate six-relic quest. Polaris is represented
as one of its staged milestones, and `Dracarys` unlocks only after that
milestone. No separate Polaris quest is required.

`A Bad Dream` retains its current level and rewards but is unavailable until
Joffrey's four living scenes and the preceding relic states are complete.
Domingo kills Joffrey after Vesperion's distorted evidence draws him onto the
fatal route. `In the Day of Our Lord` unlocks only after `A Bad Dream` is
completed.

## Accepted Side-Quest Audit

The audit covers all twenty-nine entries currently authored under `Side` plus
the three entries moving from `Main`, for a post-migration total of thirty-two
authored Side quests. `Bounty` entries remain contract-style hunting content
and do not require individual campaign classification.

`Preserve` means that the quest's current function, target, and reward remain
valid. `Revise` means that the identifier and useful mechanics remain, but its
copy, ownership, prerequisite, or aftermath must change to fit the accepted
campaign. Chapter-role metadata is descriptive and must not itself become a
completion trigger.

| Side quest | Disposition | Accepted story role or required revision |
| --- | --- | --- |
| `Pandora's Box` | Revise | Chapter 6 supporting mystery. Preserve its objective and reward; rewrite Hooded Figure framing so it supports uncertain guidance without premature certainty. |
| `Rat Trap` | Preserve | Opening town-and-dungeon texture. Keep it optional and outside the campaign chain. |
| `Something to Cry About` | Revise | Preserve the floor-2 crying trail and anguished-scream battle, but replace Liora with a fellow survivor of the failed expedition behind `Rookie Mistake`, mourning a companion who died there. |
| `A Candle for the Descent` | Preserve | Opening memorial and descent texture. Separate tutorial instruction from character voice where the production copy requires it. |
| `Bring Him Home` | Preserve | Chapter 1 human rescue supporting the opening crisis. |
| `Where's the Beef?` | Revise | Liora remains the sole owner. The provisions are for her and Joffrey's wedding feast. After Joffrey's death, an unfinished collection changes purpose to a church donation for people in need. Preserve accepted progress and rewards; remove the duplicate Busboy-authored entry and transfer logic. |
| `Spores in the Dark` | Preserve | Early environmental texture and optional dungeon work. |
| `Ticket to Ride` | Preserve | Optional town/economy texture; naturalize copy during the supporting-content pass. |
| `An Honest Introduction` | Preserve | Early character and system introduction. Keep tutorial directions distinct from in-world dialogue. |
| `Rookie Mistake` | Revise | Chapter 1 body recovery and burial. Preserve the Rookie's death, body-transport mechanics, and rewards; soften victim-blaming language. The revised `Something to Cry About` uses the expedition's sole survivor mourning a different dead companion. |
| `Loose Ends` | Preserve | Chapter 3 supporting Order conflict. |
| `Eight Is Enough` | Preserve | Optional creature-hunt texture; polish tone without promoting it to campaign causality. |
| `The Spring's Reflection` | Preserve | Chapter 4 location and nature support. |
| `I'm Molting!` | Preserve | Optional material/economy texture; retain background humor. |
| `Put A Feather In It` | Preserve | Optional material/economy texture; retain background humor. |
| `A Breath Between Stones` | Preserve | Chapter 4 environmental support and quiet counterpoint. |
| `Metalingus` | Preserve | Guard-facing salvage work. It may share a Scrap Metal target with `The Iron Ledger` because the owners and purposes differ. |
| `The Iron Ledger` | Preserve | Guild/economy salvage work. Do not merge it with `Metalingus` without later pacing evidence. |
| `Knock Back a Couple Brewskis` | Preserve | Town-character texture supporting the Drunkard's longer endurance arc. |
| `The Shocker` | Revise | Preserve its class/mechanical role; replace generic "greater evil" framing with a local threat and earned consequence. |
| `Naivete` | Preserve | Chapter 4 nature and judgment support; polish copy as needed. |
| `Earth, Wind, and Fire...and Water and...` | Preserve | Optional elemental texture; keep the reference in the background rather than as a critical revelation. |
| `Oedipal Complex` | Preserve | Optional Cambion/underworld and illusion chain. |
| `The Unquiet Thesis` | Preserve | Optional Chapter 6 guidance and interpretation support. |
| `The Holy Grail of Quests` | Preserve | Optional Cambion/underworld and illusion chain; keep its humor outside serious campaign beats. |
| `This Thing's Nuclear` | Preserve | Polaris-supporting optional content. Preserve mechanics and naturalize conspicuously modern phrasing only where it breaks tone. |
| `The Wizard's Folly` | Preserve | Optional Cambion/underworld and illusion chain. |
| `He Ain't Heavy` | Revise | Preserve the late rescue role; replace stale "primal evil" language with the specific danger and survivor stakes. |
| `Payback` | Reclassify and revise | Move from Main to Side as Chapter 3 supporting threat. Preserve target and reward; rewrite Hooded Figure and rival framing to avoid false campaign causality. |
| `Lapidation` | Reclassify and revise | Move from Main to Side as Chapter 4/Pell survivor history. Preserve mechanics and polish continuity copy. |
| `No Laughing Matter` | Reclassify and revise | Move from Main to Side as Chapter 6 false-guidance and illusion support. Preserve mechanics and reward; naturalize the "Agent of Chaos" reference. |

No audited Side quest becomes required merely because it supports a campaign
chapter. References and puns remain welcome as background texture, but grief,
Guardian revelations, and causal handoffs use direct language.

## Quest-Change Consequence Register

Quest edits must be implemented as world, state, presentation, and save changes
rather than treated as isolated JSON copy edits.

### Joffrey, the Floor-2 Corpse, and `Something to Cry About`

- The current `DeadBody` tile at level 2, coordinate `(11, 9)`, remains on
  floor 2 and becomes the dead member of the `Rookie Mistake` expedition. It
  anchors `Something to Cry About` and its proximity-based crying.
- Joffrey receives a distinct `JoffreyBody` world asset on level 4 near the
  Domingo route. The exact coordinate belongs to the Chapter 5 production
  packet and must not be inferred during this audit.
- Joffrey's body remains hidden or absent until his fatal departure and the
  corresponding story state. Interacting with it advances `A Bad Dream`;
  the generic corpse interaction must no longer own Joffrey's quest logic.
- The current floor-2 random-cry check uses an obsolete approximate coordinate
  `(18, 12)`. It must use the actual corpse position or, preferably, query the
  relevant tile rather than duplicate coordinates.
- `Something to Cry About` keeps its escalating crying and anguished-scream
  battle. Its opponent is the sole survivor of the failed expedition, grieving
  a different companion whose floor-2 corpse anchors the encounter. The Rookie
  remains dead and is recovered separately on floor 1. The text must make the
  relationship legible without making either quest mandatory.
- Remove canonical Mad Waitress triggers from corpse interaction, enemy-defeat
  quest advancement, and Chapter 5 aftermath. Existing enemy, sprite, and audio
  data may remain for compatibility or later repurposing, but must be
  unreachable from the accepted story route.

### Liora, Provisions, and Joffrey's Effects

- Liora survives Chapter 5 and remains available for her Chapters 8 and 10
  scenes and the epilogue.
- `Where's the Beef?` remains with Liora and initially collects provisions for
  her and Joffrey's wedding feast. If it remains active after Joffrey's death,
  Liora repurposes the unfinished collection as a church donation to feed
  people in need. Existing progress and rewards survive the text transition.
  Remove the duplicate Busboy quest record and the post-`A Bad Dream`
  ownership transfer.
- The Brass Key, `Joffrey's Letter`, and their useful rewards can no longer
  depend on defeating Liora. Move their handoff into a nonviolent Liora,
  Sergeant, or joint aftermath scene; the Chapter 5 packet will choose the
  exact scene while preserving the items and rewards.
- Rewrite `Joffrey's Key`, `Joffrey's Letter`, and related event text so
  Joffrey acted voluntarily under distorted evidence rather than supernatural
  compulsion. The letter must recall details from the four witnessed living
  scenes.
- Remove or replace the current Busboy event that assumes Liora fled and Tavin
  took over her tables. Grief changes her dialogue and quest purpose without
  removing her from town.

### State, Saves, Presentation, and Validation

- Add explicit story-state prerequisites for `A Bad Dream` and
  `In the Day of Our Lord`; a level check alone cannot reveal Joffrey's body
  or Domingo's resolution early.
- Give the Joffrey body and the floor-2 expedition corpse independent stable
  state. Existing coordinate-keyed world state must migrate so an old floor-2
  read flag neither pre-reads the new Joffrey asset nor creates duplicate
  rewards.
- Preserve completed and accepted quest identifiers wherever possible.
  `Where's the Beef?` changes stage/copy in place; its collected-item progress
  must not reset during the transition.
- Update the body interaction, random-cry, quest-manager handoff, enemy-defeat
  advancement, special-event, dialogue, renderer, map, and save-normalization
  surfaces together.
- Add focused regressions for the level-2 corpse coordinate and crying radius,
  the separate level-4 Joffrey body and visibility gate, the two corpse states
  across save round trips, `A Bad Dream` and Domingo sequence, Liora's
  survival, the provisions-purpose transition, and the absence of duplicate
  Brass Key or letter rewards.
- Audit current body-tile, dungeon-manager, quest-manager, progression, and
  player-helper tests. Mad Waitress combat may retain isolated enemy behavior
  coverage, but it is no longer a canonical route regression.

## Late-Game Quest Continuity Hooks

Late-game quest copy can acknowledge story truths only after the relevant route
has earned them. This document owns quest-facing continuity language; the
larger Vesperion/Voluntas route still belongs to
`STORY_AND_ENDGAME_DESIGN.md`.

### Red Dragon Continuity

The Red Dragon encounter currently feeds ordinary progression, Lancer/Dragoon
Kaelenon restoration, and Thaumaturgist Dragon Calling. Quest text should
separate those meanings without making one route invalidate another.

Allowed copy direction:

- Hooded Figure/Red Dragon progression can describe the boss as a dangerous
  barrier and source of draconic power.
- Lancer/Dragoon `Recover` text can reveal Kaelenon as a trapped or restored
  identity inside the encounter.
- Zahhak unlock text can frame the summon as a draconic echo, spirit, pact, or
  aftermath binding rather than the same restored person.
- Non-Lancer/Dragoon victories remain narratively complete and should not be
  described as failed rescues.

Any copy-only continuity pass must preserve current quest names, boss target,
floor gate, rewards, summon unlock behavior, class unlock behavior, and
boss-room state. Mechanical changes require a promoted class/story spec.

### Postgame Town Dialogue

After `main_story_complete`, selected NPCs may receive lightweight reactive
dialogue about the Busboy's absence, the Waitress/Joffrey tragedy, the changed
town atmosphere, or the hero's return from the final threshold. This should be
local flavor and closure, not a hidden quest chain.

Postgame dialogue must not:

- reopen completed quests;
- create new required objectives;
- remove town services;
- alter bounties, shops, church, inn, barracks, or storage behavior;
- imply that Voluntas erases grief or reverses deaths.

The first slice is implemented for the Barkeep, Waitress, and Soldier. It is
gated only by `main_story_complete`, remains repeat-safe across saves, and uses
the shared reactive-hint path consumed by Pygame.

## Quest System Contract

Quest records may optionally define staged metadata:

- `Stage`: the current stage key saved on the player's accepted quest.
- `Stages`: stage definitions containing display text, objective/help text, and
  trigger identifiers.

Non-staged quests remain valid and ignore these fields. Future authored
entries may also define chapter-role metadata for documentation and
presentation without making that metadata a completion trigger.

The accepted Progression migration must add the category atomically across
new-player defaults, eligible-quest lookup, defeat/item/locate advancement,
quest menus, save serialization and normalization, and focused regressions.
Until that migration lands, current content remains in its shipped runtime
categories.

Shared core quest-progress helpers own story quest synchronization so Pygame
does not duplicate relic or staged-objective rules. The helper is responsible
for:

- syncing staged quest progress after relic pickup;
- syncing aggregate relic collection completion;
- creating `The Holy Relics` after `Uncertain Reports` is turned in;
- defensively collapsing obsolete immediate `The Holy Relics` entries when
  encountered; this is normalization, not a compatibility guarantee.

## Persisted Quest Normalization

When the obsolete pre-staging `The Holy Relics` entry is encountered, current
normalization replaces it according to restored relic state:

- `0` relics becomes active `Uncertain Reports`.
- `1-5` relics becomes active staged `The Holy Relics`.
- `6` relics becomes completed staged `The Holy Relics`.
- turned-in relic quests remain turned in after normalization.

Normalization happens after special inventory and quest data are restored, so the
relic count reflects the actual saved inventory.

## Implementation Notes

- The verified implementation contract for the first slice lives in
  `PROLOGUE_TRIANGULUS_PRODUCTION_PACKET.md`.
- Quest content lives in `src/core/data/content/quests.json`.
- Staged relic quest synchronization and missing-field normalization live in
  `src/core/quest_progress.py`.
- Quest-state normalization is called from `src/core/save_system/player.py`
  after special inventory restoration.
- Pygame quest turn-in paths call the shared quest-progress helper.
- Relic discovery copy uses `src/core/map_tiles/rules.py` so presentation and
  core validation share the same mapping and fallback.
- Postgame tavern fallout lives in `src/core/town.py`; Pygame uses the shared
  non-mutating reactive-hint source.

## Regression Targets

- A new game offers `Uncertain Reports`, not `The Holy Relics`, at level 1.
- `Uncertain Reports` contains no six-relic, Vesperion, or Voluntas spoiler.
- `Cry Havoc!` remains the Barghest quest and keeps its existing level, target,
  reward, and completion behavior.
- Finding Triangulus marks `Uncertain Reports` ready to report without naming
  late-game identities.
- Turning in `Uncertain Reports` creates active `The Holy Relics`.
- The six-relic count and completion behavior remain correct in Pygame quest
  menus and headless core validation.
- Current quest-state normalization covers 0, 1, 5, 6, completed, and turned-in
  relic states.
- Red Dragon continuity copy distinguishes progression victory, Kaelenon
  restoration, and Zahhak binding without changing quest gates or rewards.
- Postgame town dialogue appears only after `main_story_complete`, is
  repeat-safe, and does not mutate quest/shop/bounty/town service state.
