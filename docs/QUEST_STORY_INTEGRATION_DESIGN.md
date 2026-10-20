# Quest Story Integration Design

Status: `Holy Relics V1 Implemented; Main-Quest Classification Accepted`

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

Early-game copy must not name Vesperion, Voluntas, the busboy identity, the
Hooded Figure truth, or true-final route mechanics. It may hint at old
principles, relic-light, sealed chambers, and incomplete reports.

## Accepted Campaign Quest Classification

The campaign audit assigns each of the fourteen entries currently authored
under `Main` to one accepted role:

| Current quest | Accepted category | Campaign role |
| --- | --- | --- |
| `Uncertain Reports` | Main | Chapters 1-2 investigation. |
| `The Butcher` | Main | Chapter 1 crisis and first-floor access. |
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
`Immovable Object` in isolation.

`The Holy Relics` remains the aggregate six-relic quest. Polaris is represented
as one of its staged milestones, and `Dracarys` unlocks only after that
milestone. No separate Polaris quest is required.

`A Bad Dream` retains its current level and rewards but is unavailable until
Joffrey's four living scenes and the preceding relic states are complete.
Domingo kills Joffrey after Vesperion's distorted evidence draws him onto the
fatal route. `In the Day of Our Lord` unlocks only after `A Bad Dream` is
completed.

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
