# Presentation And Asset Design Gates

This document is the durable reference for presentation and asset work. It maps
the roadmap's Presentation and Asset Gates into implementation slices, asset
workflow rules, and follow-up gates. Completed work should move to
`CHANGELOG.md`; this file should keep only active, deferred, or decision-gated
presentation direction.

## Status

Status: `V1 Screen, Cue, Identity, And Asset Baseline Shipped`

The first implementation slice prioritizes quick wins that do not require a new
art direction pass:

- Replace the plain Character Created popup with a visual character summary
  screen.
- Replace the New Game intro popup chain with reusable story-card pages.
- Extend the existing combat impact layer with richer cues for reflection,
  hard-control hits, and elemental weapon strikes.

Generated bitmap batches are allowed for later asset-heavy slices, but each
batch must have a review artifact before runtime integration.

The follow-up implementation set shipped Enemy Identity Presentation V1, the
Quasit
combat-sprite remake, active/inactive Warp Point dungeon art, and bespoke
summon companion art. Runtime PNGs remain transparent, review sheets are checked
in, and fallbacks remain valid.

## Screen Polish V1

Character creation should end with a presentation screen, not a plain text
popup. The screen shows the selected portrait, identity and resource summary,
then the newly created character's attack, defense, magic attack, magic defense,
critical chance, block, and speed. It has a single clear continue action and
accepts keyboard confirm or mouse click. The screen is presentation-only and
must not change character creation, save fields, starting stats, inventory, or
class/race selection behavior.

New Game intro text uses reusable illustrated story cards. Each card shows only
slow-printed story text over full-screen art: no title, text box, page counter,
or continue label. Complete passages are wrapped before their characters are
revealed so a partly typed word never jumps between lines. Every card fades in
and out. Keyboard confirm or mouse click first completes the current passage
and a second activation advances; Escape may skip the remaining story sequence
without cancelling character creation. After the final card, hold on black long
enough to create a clear break before opening dialogue.

The sixth card now ends at the illuminated Thirsty Dog rather than showing the
dungeon prematurely. P1 fades into a dedicated tavern interior with an
establishing narration beat; that background is shared by the tavern menus and
later tavern scenes, with the town art as fallback. The former sixth-card
descent art appears once when the player deliberately enters the dungeon.
Story-scene dialogue follows the same complete-passage wrapping rule as cards.
Story scenes use a dark visual-novel composition rather than a cumulative
transcript: the background remains visible, one beat occupies a lower dialogue
box, and no more than three existing portraits are staged at once. Principal
participants hold opposite sides, associated third participants use a smaller
recessed position, and only the least-relevant slot changes when another speaker
enters. Narration retains the staged scene without naming or picturing a
narrator. Dialogue history provides access to earlier authored beats.

Player dialogue bodies are transparent full-figure cutouts mapped from the same
canonical appearance ID as the character-creation face atlas. All 70 playable
race, sex, and portrait-variant combinations are populated; character creation
continues to use its existing face crops.
The hero consumes one of the three staged-character slots and follows the same
beat-relevance rotation as NPCs: it enters for authored player beats, can remain
visible while relevant, and rotates out without special protection. Each mapped
cutout may declare its native facing; the renderer mirrors that same surface
when its stage side would otherwise point it away from the exchange. Missing
dialogue-body assets remain absent rather than displaying a generic body,
rectangular face crop, or framed portrait.

NPC dialogue cutouts use the same inward-facing contract. Their native facing
is recorded by art key, aliases inherit that metadata, and the renderer mirrors
the existing surface only when its fixed stage side would point it off-screen.
Listeners remain fully opaque and are subdued by darkening their color values;
the scene background must never show through solid areas of a character cutout.
Story scenes use clean venue artwork rather than snapshots of navigable menus,
so unrelated option lists, borders, and selection state do not appear behind
dialogue.

The barracks owns a dedicated empty map-room background with normal and
high-resolution runtime variants. Patrol-ledger review and the post-descent
route correction use that interior. The latter first establishes Joffrey and
Liora waiting in the rainy courtyard, then moves the cast into the barracks;
it must not imply that Caedmon convened military route work in the tavern.

Character-creation panels remain translucent so the title backdrop is visible.
The accepted-character screen uses the selected portrait, with the matching
base portrait as a fallback if class-layer composition is unavailable.

Shop screen mouse support has shipped for main shop options, item rows, subtype
tabs, and item-list wheel scrolling while preserving keyboard behavior and
guarded input.

## Endgame Story Presentation Polish

Endgame presentation polish should reuse the existing story-card, dialogue, and
special-event surfaces before adding new UI. The target sequence is:

1. false-final Vesperion transition into the Liminal Gap;
2. Guardian clue completion and Seventh Seat reveal;
3. Acolyte warning and Reflection/Psychopomp prelude;
4. return from The Liminal Gap;
5. true-final Vesperion prelude, choice argument, and tragedy reframing;
6. true-final victory, Voluntas ending, tavern epilogue, and final-room
   reminder.

Presentation polish may improve pacing, page breaks, title text, portrait
routing, continue/skip behavior, and audio cue timing. It must not change
story flags, combat stats, rewards, inventory, quest state, save state, death
flow, or true-final gates.

Preferred first slice: review and polish page breaks/title treatment for the
true-final victory, `The Forsaken Tenet Ending`, and `The Thirsty Dog Epilogue`
so they feel like a deliberate ending sequence rather than three unrelated
popups. Preserve shared content text so presentation polish does not own story
state or canonical copy.

Endgame story-card polish should be validated on both fresh endgame state and a
post-`main_story_complete` save. Re-entering the final room after completion
should show a concise reminder, not replay the final boss or duplicate the
ending.

## Combat Status Art

Evasive Guard now uses the approved `evasive_guard.png` status icon through the
shared `status_icons.py` resolver, including counted stack labels such as
`EG2`.

Status-effect artwork remains opt-in. Missing effect PNGs continue to fall back
to readable initials or compact pills. New status assets belong under
`src/ui_pygame/assets/effects/` and must map through the existing status icon
helpers rather than through one-off UI logic.

Adding status artwork must not change status mechanics, duration, stacking,
priority, save data, or combat result text.

## Ability Visual Batch V1

Combat cues should use the existing `CombatView` impact-effect layer. V1 covers:

- Reflection and Magic Reflect: shield/ripple style flashes on confirmed
  reflected damage.
- Stun and Prone: hard-control hit accents when the confirmed result text
  applies those states with damage.
- Elemental strikes: elemental color rings layered over weapon-hit slashes when
  non-spell damage carries a recognized element.

Effects trigger only after confirmed relevant outcomes. Misses, fully resisted
actions, and non-damaging actions must not play hit/spell particle effects.

### Improvements

- Elemental attack spell effects should more resemble there actual effect
  - Fire spells look like fire
    - Firebolt looks like a small fireball
    - Fireball would be the same but larger
    - Firestorm would be multiple Fireballs coming from above
    - Scorch
    - Molten Rock
    - Volcano
    - add burn effect if triggered
  - Ice spells resemble the spell name
    - Ice Lance looks like an ice dagger
    - Icicle falls from above with multiple icicle-looking daggers
    - Blizzard shows wind and snow blanketing the view
    - triggered effect should "freeze" the target
  - Electric spells resemble the spell name
    - Shock is short electric shock around the target sprite
    - Lightning
    - Electrocution
    - Bolt
    - Ball Lightning
  - Water
    - Water Jet
    - Aqualung
    - Tsunami
  - Earth
    - Tremor
    - Mudslide
    - Earthquake
    - Sandstorm
  - Wind
    - Gust
    - Hurricane
    - Tornado
- Existing Ability Effects
  - Player Mana Shield effect should cover the visible battlefield between the
    combat log and action menu with a blue hue that "vibrates" between blue and
    purple on a hit.

### Jump And Charge Visuals

Full Jump and Charge wind-up/impact animation remains deferred until enemy
sprite stance adjustments are planned. Future work may add lightweight hooks for
pre-action wind-up and landing/impact cues, but it must not replace enemy
sprites or require alternate enemy stance art in this slice.

## Warp Point Art Pass

Warp Point artistic renderings are a generated-bitmap batch. Targets are:

- active Warp Point;
- inactive or spent Warp Point;
- optional charged shimmer overlay.

V1 uses transparent PNGs through dungeon special-tile manifest entries:
`warp_point_active` and `warp_point_inactive`. Active Warp Points keep the
existing spark overlay. Runtime logic falls back to the legacy `teleporter`
sprite when an approved Warp Point asset is absent.

## Town, NPC, And Venue Art Pass

Town/NPC/Venue renderings are batch-gated by art direction, target list,
dimensions, and review workflow. Approved shipped targets include recurring
town NPCs, Old Warehouse guards, staffed Warp Point scientists, selected
endgame story figures, and the `Bring Him Home` child/family cast.

### NPC Artistic Renderings

NPC renderings should match the established dark fantasy painterly look used by
enemy, companion, item, and character artwork. This is a presentation-only art
pass: it must not change quest routing, dialogue availability, shop inventory,
town navigation, save fields, or NPC mechanics.

V1 recurring town NPC portraits have shipped for dialogue and location/menu
surfaces where the NPC is the subject. The approved runtime keys are:

- `alchemist`;
- `barkeep`;
- `busboy`;
- `drunkard`;
- `gray_broker`;
- `griswold`;
- `hooded_figure`;
- `jeweler`;
- `mara_vale`;
- `nimue`;
- `old_warehouse_guard`;
- `priest`;
- `sergeant`;
- `soldier`;
- `waitress`;
- `warp_point_scientist`.

NPC Story Portrait Batch V2 adds endgame story figures to the same manager and
review-sheet workflow:

- `acolyte`: failed former hero, worn pilgrim/adventurer silhouette,
  ash-gray Liminal light, sorrowful but not hostile.
- `reflection`: mirror-dark Psychopomp/almost-self figure, ambiguous
  martial/mystic/hybrid cues, reflective edges, not a player portrait clone.
- `vesperion`: fallen Guardian of Voluntas, radiant twilight severity, Evening
  Star motif, controlled mercy rather than demonic cruelty.

V2 runtime use is dialogue-only and title-driven. Acolyte, Reflection, and
Vesperion portraits may appear in named Liminal/final-room special-event
dialogue, but must not replace combat sprites, enemy info panels, map tiles,
combat HUD art, shop item panes, bounty boards, town hover panels, or ending
text where no named figure is speaking. `Voluntas` remains an abstract
principle/title, not a portrait target.

Each NPC should have one canonical runtime key and one approved neutral-state
rendering before adding variants. Variants such as injured, missing, hostile,
celebrating, or post-quest states remain deferred until the base NPC pass has a
manager, manifest, and review sheet.

Vesperion also requires a separate full-body
`enemy_combat_sprites/vesperion.png` combat sprite so narrative dialogue art and
center-combat presentation stay related without reusing portrait-shaped bust
art. The combat sprite should show the complete standing body, head to feet,
with no frame, label, rectangular background, portrait crop, or token crop.
This is a presentation asset mapping only and must not change Vesperion stats,
AI, phase pressure, rewards, or Liminal route state.

### NPC Diversity Refresh V3

V3 improves fantasy-town ensemble variety for approved grounded town-human
portraits while respecting story anchors such as the Waitress/Joffrey tragedy,
town guard roles, shop identities, and approved supernatural/story portraits.
The shipped replacement portraits are Alchemist, Barkeep, Jeweler, Priest,
Soldier, Waitress, and Warp Point Scientist. New shop/story portraits include
Seraphine Voss, Mara Vale, and The Gray Broker. Busboy, Drunkard, Griswold, Old
Warehouse Guard, and Sergeant keep their prior approved portraits for now.

The reviewed candidate batch and replaced originals are archived under
`src/ui_pygame/assets/npc_art/old_files/`. Archive files must remain unavailable
to `NpcArtManager`; only root-level files mapped by `npc_art_map.json` are live
runtime portraits. This pass must not change quests, dialogue availability,
save data, shop behavior, combat, rewards, or town routing.

### Story Scene Targets

Future story-scene assets are deferred as named special-event/dialogue-only
targets. They should not appear in venue-wide location panels, town hover
panels, shop panes, combat HUDs, enemy info panels, bounty boards, or ending
text unless that future pass explicitly adds a matching runtime surface.

- `joffrey_body`: Joffrey discovery/dead-body story art.
- `waitress_grief`: Waitress locket/Joffrey grief scene or variant.
- `waitress_mad`: optional hostile grief-transformed variant, separate from
  the existing Mad Waitress enemy sprite.
- `vesperion_true_final_victory`: optional final-room story card art, distinct
  from the full-body combat sprite and dialogue portrait.
- `voluntas_ending`: optional abstract ending-card art; `Voluntas` must remain
  a principle, not a person or portrait target.
- `thirsty_dog_epilogue`: optional tavern aftermath art after
  `main_story_complete`, focused on absence and aftermath rather than triumph.

`Bring Him Home` now uses the shared staged-dialogue surface at both quest
moments. `timmy`, `timmy_mother`, and `timmy_father` are transparent full-body
cutouts used only by those scenes. Discovery retains the clean dungeon
background and occurs before the existing automatic return to town; reunion
uses the clean town background before quest rewards, experience, level-up, and
the turned-in flag are applied, then rotates Timmy, both parents, and Caedmon
through the three-portrait limit.

Venue-wide scenes and location-panel art remain deferred to a separate future
batch.

Runtime use should favor focused NPC detail/dialogue panels and town/venue
surfaces where the character is the subject. Do not place large NPC portraits in
shop item comparison panes, quest reward selection, combat HUD, or any surface
where they would compete with functional information.

If a future pass needs shared loading/caching, add a small manager following the
existing asset-manager pattern. Do not introduce one-off path loading in several
screens.

### Additional Targets

- Add storage locker image to show where Sergeant shows in Barracks

## Companion And Summon Art

Familiar and summon artwork uses `CompanionArtManager` and
`src/ui_pygame/assets/companion_art/companion_art_map.json`. Runtime companion
PNGs must remain transparent 512x512 sprites. Renamed tamed companions resolve
art from their original enemy class before nickname/name so `Nickname (Enemy
Name)` still finds the correct animal sprite. Tamed companions and any future
unmapped companion continue to fall back through `EnemyCombatSpriteManager`;
do not remove that fallback path when adding new companion art.

In the Character Menu, the Class tab should keep companion and summon rows
compact and text-first. The companion/summon overview roster uses stacked
full-width rows, not a square grid, and must fit all 11 summon creatures without
requiring hidden rows. Companion/summon artwork belongs in the selected
companion details popup, which should follow the Character tab's visual pattern.
Familiars and summons show art/identity/core attributes on the left and combat
stats, abilities, and resistance groups on the right. Tamed companions are not
targetable/resource-managed actors in the current UI, so their details popup
shows art/identity, form, trait, bond, and flavor notes instead of HP/MP/stat
sheet rows.

For classes with non-companion usage mechanics, the middle Character Menu tab
is renamed to that mechanic instead of showing a generic Class tab or
`Promotion Tier` summary. Weapon
Master, Berserker, and Grandmaster of Arms use the `Weapon Discipline` tab,
with a full-width per-weapon board, item icons, rank/XP progress bars, and
equipped-weapon highlighting. Classes without a class-usage mechanic hide the
middle tab entirely.

The first summon art pass covers Patagon, Dilong, Agloolik, Cacus, Fuath,
Izulu, Hala, Lamashtu, Seraphim, Bardi, Kobalos, Tiamat, and Zahhak. The
checked-in review sheet is
`docs/assets/review-sheets/companion-art.png`.
Rebuild the review sheet with
`./.venv/bin/python tools/build_companion_art_sprites.py` after changing those
sprites.

## Enemy Identity Presentation

Enemy identity presentation is a readability layer and must preserve underlying
combat mechanics.

- Invisible enemies: keep identity, art, HP, weaknesses, and resistances gated
  by existing Sight/visibility rules. Any reveal note should explain why the
  player can or cannot inspect the target.
- Special forms: form-change notes should describe the visible state change
  without replacing the canonical enemy name or combat sprite lookup.
- Construct-friendly bleed flavor: wording such as `Oil Leak` may be presented
  for construct enemies, but the underlying effect remains `Bleed` for combat
  logic, saves, tests, and compatibility.

V1 implements this in pygame presentation only. Invisible target notes appear
inside the combat target panel, Mad Waitress uses a visible form-change note,
and construct enemies can show `Oil Leak` wording/icons while core effect maps
and simulator metrics continue to use `Bleed`.

## Website

The public-facing website/project page remains deferred until title and identity
direction are stable. Do not spec or implement website files from this gate
until the roadmap promotes that work out of deferral.

## Generated Bitmap Workflow

Generated bitmap batches require:

- transparent PNGs for runtime sprites and overlays;
- JSON map or manifest entries when the existing loader pattern requires them;
- runtime fallback behavior for missing or failed assets;
- a checked-in review sheet/contact sheet before runtime integration.

The review-sheet requirement follows the enemy combat sprite precedent. Review
sheets should show every generated asset against a neutral game-adjacent
background and make clipping, rectangular backgrounds, scale mismatches, and
silhouette problems visible.

Prefer existing systems:

- status and effect icons through `status_icons.py`;
- enemy combat visuals through `EnemyCombatSpriteManager`;
- dungeon and Warp Point visuals through the dungeon texture manifest;
- companion/familiar/summon visuals through `CompanionArtManager`;
- town/NPC art through a dedicated manager only if direct path loading would be
  duplicated.

Do not replace combat sprites with portraits, tokens, rectangular cards, or
UI-framed art.

## Validation

Focused tests should cover:

- Character Created screen drawing, keyboard/mouse continue, portrait fallback,
  and text wrapping.
- Story-card page advancement, Escape skip, mouse continue, and page counters.
- Combat cue classification and drawing for reflect, stun/prone, elemental
  strikes, and no-cue no-damage outcomes.
- Asset managers or manifest mappings for missing asset fallback, invalid
  mapping tolerance, cache clearing, and review-sheet builder smoke behavior
  when new generated batches are integrated.
- Enemy identity presentation for invisible reveal text, form-change notes, and
  construct bleed-flavor wording without changing the canonical effect name.
