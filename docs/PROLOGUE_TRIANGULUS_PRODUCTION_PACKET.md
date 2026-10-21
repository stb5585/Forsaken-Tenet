# Prologue Through Triangulus Production Packet

Status: **Ready for Implementation — Runtime Mapping Verified**

Review checkpoint: P0–P3, C1, and C4–C12 are accepted. C2–C3 remain preserved
implementation contracts. Owner-document reconciliation and static runtime
mapping verification are complete against `master` commit
`b38f97d5884bfdb0386f1f757341aae17da9b5cc`.

This packet owns the first implementation-quality narrative slice: the Prologue,
Chapter 1, and Chapter 2 through the recovery of Triangulus, the report back to
Caedmon Varr, and the creation of `The Holy Relics`.

It implements the accepted direction in `NARRATIVE_FOUNDATION.md`,
`MAIN_STORY_OUTLINE.md`, and `QUEST_STORY_INTEGRATION_DESIGN.md`. Those
documents remain the authority for campaign canon; this packet owns the exact
opening sequence and its implementation contract.

## Scope And Non-Goals

The slice must make Silvana worth returning to, establish the dungeon's human
cost, turn contradictory reports into a playable mystery, and give Triangulus a
distinct identity-centered payoff.

The slice does not change:

- combat numbers, enemy kits, rewards, item values, or experience;
- class, race, promotion, or Class Ring rules;
- level-1 map topology, boss coordinates, keys, gates, or warp behavior;
- the Minotaur or Barghest encounter mechanics;
- the six-relic collection requirement or late-game route;
- optional quest completion as a prerequisite for the critical path.

The implementation may add story-state fields, staged copy, one-time scenes,
reactive dialogue, and event triggers. Any mechanical expansion requires a
separate approved specification.

## Chapter Contracts

| Section | Entry state | Required result | Exit state |
| --- | --- | --- | --- |
| Prologue — The Lantern At The Edge | A newly created hero has completed character creation and the existing intro is ready to play. | Record why the hero came to Silvana, introduce the central town circle in motion, witness an incomplete patrol return, and offer `Uncertain Reports`. | The hero can accept or defer the first investigation and enter the ordinary town loop. |
| Chapter 1 — Names In The Ledger | `Uncertain Reports` is active. Level-1 routes and the separate Minotaur gate retain current state. | Show that the dungeon consumes named people, establish Joffrey as a living route-mapper, and reveal that contradictions repeat. Preserve the Minotaur as the independent Progression gate to level 2. | The Barghest report becomes the strongest surviving lead and `Cry Havoc!` becomes available under its existing level requirement; Minotaur state does not control that handoff. |
| Chapter 2 — The Shape Of Proof | `Cry Havoc!` is active and the Barghest route is reachable. | Defeat the Barghest, discover the first unnamed Acolyte trace, answer Triangulus, recover the relic, and report it. | `Uncertain Reports` is turned in, `The Holy Relics` is created, and Silvana knows only that a possible six-part pattern exists. |

## Information Boundary

Before Triangulus returns to town, no scene may confirm:

- that exactly six relics exist;
- that the relics embody a complete doctrine;
- Vesperion, Voluntas, or the Busboy identity;
- the Hooded Figure's allegiance;
- the title or complete fate of the Acolyte;
- true-final or Liminal mechanics.

The opening may name old symbols, sealed chambers, repeated structural details,
missing time, altered recollection, and a strange object whose purpose is not
yet known.

## Scene Board

| ID | Section | Location | Participants | Player control | Mandatory result |
| --- | --- | --- | --- | --- | --- |
| P0 | Prologue | Story-card sequence | Narrator | Advance or skip pages using existing story-card controls. | Establish Silvana, the opened stair, missing people, and the hero's voluntary arrival without naming Guardians or principles. |
| P1 | Prologue | The Thirsty Dog | Oren, Liora, Joffrey, Tavin, Pell, patrons, hero; Hooded Figure observed | Choose one arrival motive. | Record Fortune, Service, Knowledge, or Reinvention. Establish the tavern as a lived-in chosen family and complete Joffrey's ordinary tavern scene. |
| P2 | Prologue | The Thirsty Dog | Edrin Shaw, Caedmon, tavern circle, hero | Choose how to help during the interruption. | A wounded patrol scout returns without Mira Venn and Tomas Reed. His incompatible route account becomes immediate human evidence. |
| P3 | Prologue | The Thirsty Dog to barracks handoff | Oren, Caedmon, hero | Accept or defer `Uncertain Reports`. | Oren vouches for the hero's conduct; Caedmon offers a bounded investigation rather than declaring the hero chosen. |
| C1 | Chapter 1 | Barracks ledger | Caedmon, Joffrey, Edrin, hero | Inspect three short report excerpts in any order. | The same symbols, missing interval, and sealed structure recur in mutually incompatible accounts; complete Joffrey's patrol briefing scene. |
| C2 | Chapter 1 | Town and first descent | Hero; town NPCs reactively | Normal town and dungeon control. | First descent receives a one-time environmental beat; town services remain available in the current order. |
| C3 | Chapter 1 | Level 1 routes | Hero; Timmy or the Rookie when their optional quests are active | Existing exploration and quest interactions. | Optional rescue and burial outcomes gain multi-character reactions but never gate the main route. |
| C4 | Chapter 1 | Tavern or barracks | Joffrey, Caedmon, Liora, hero | Short mandatory scene on next eligible town return. | Joffrey compares the hero's observations with his own maps; Liora challenges the normalization of repeated risk; complete Joffrey's route-review scene. |
| C5 | Chapter 1 | Minotaur route at `(3, 2, 1)` | Hero, Minotaur | Existing boss interaction and combat; timing is independent of the Main route. | The Butcher remains the sole Progression gate to the level-2 stair at `(3, 0, 1)`, not a relic custodian or prerequisite for the Barghest. Mechanics and rewards remain unchanged. |
| C6 | Chapter 1 | Barracks | Caedmon, Joffrey, hero | Report current evidence. | Caedmon identifies the Barghest account as the one lead that survives every rewrite. `Cry Havoc!` becomes available when its level requirement is also met. |
| C7 | Chapter 2 | Barghest route at `(18, 2, 1)` | Hero, Barghest | Existing boss interaction and combat. | Witness descriptions are reconciled as different forms of the same creature. The Barghest remains a later occupant, not a Guardian. |
| C8 | Chapter 2 | Sealed-chamber threshold | Hero | Inspect or continue; the patrol discovery and fragment must be presented before relic interaction. | Confirm Tomas Reed's death, preserve Mira Venn as missing, and recover the first unnamed prior-explorer fragment without using the title Acolyte. |
| C9 | Chapter 2 | Relic room at `(19, 0, 1)` | Hero, Triangulus response | Choose one of four identity lenses. | Record Chosen Name, Deeds, Memory, or Next Choice; recover Triangulus; advance `Uncertain Reports` to report-back. |
| C10 | Chapter 2 | Barracks | Caedmon, Joffrey, Edrin, hero | Turn in `Uncertain Reports`. | Caedmon identifies a possible six-part pattern, marks uncertainty explicitly, and creates `The Holy Relics`. Edrin's recognition ties the proof back to the opening loss. |
| C11 | Chapter 2 | The Thirsty Dog | Oren, Liora, Joffrey, Tavin, Pell, hero | Hear short reactions; no new mandatory choice. | Show the relic's effect on ordinary people. Tavin asks a subtle identity question; no one supplies the correct interpretation. |
| C12 | Chapter 2 | Town threshold after C11 | Hooded Figure, hero | Listen or leave; either completes the beat. | The Hooded Figure respects the hero's answer without commanding a meaning, then withdraws. |

## Cast Authority

| Character | Knows at entry | Wants in this slice | May reveal | Must not reveal |
| --- | --- | --- | --- | --- |
| Oren Caldus | The tavern's history, recent disappearances, and the character of local patrol members. | Keep the room functioning and judge whether the newcomer is safe to involve. | The town is tired of treating absence as ordinary. | Relic doctrine, hidden identities, or certainty about the dungeon. |
| Liora Fen | Joffrey's work patterns and the human cost of patrol culture. | Protect her chosen family without denying that others need help. | She and Joffrey are preparing a wedding; repeated “necessary” risk frightens her. | Later tragedy or supernatural explanations. |
| Joffrey | Current patrol routes, incomplete maps, and contradictory field reports. | Make the routes safer and recover missing people. | Practical observations and willingness to accept responsibility for his maps. | His Chapter 5 fatal route or Vesperion's influence. |
| Tavin | Far more than his public role permits. | Observe which reasons and interpretations the hero chooses. | Accurate memory, helpful service, and questions that sound sympathetic. | Vesperion, Voluntas, the six-part design, or overt manipulation. |
| Caedmon Varr | Patrol records, casualties, and the limits of his evidence. | Protect Silvana while refusing false certainty. | Three recurring anomalies and the possible six-part pattern only after Triangulus. | Guardian history or claims unsupported by the ledger. |
| Pell Morn | Old rumors, survivor memory, and tavern history. | Deflect pain with humor while still recognizing danger. | A symbol seems familiar, followed by a retreat into a plausible joke. | A reliable exposition dump. |
| Hooded Figure | The larger pattern and the importance of voluntary identity. | Place a question without taking the answer away from the hero. | A chosen name can become a vow. | Their allegiance, witness role, Vesperion, or the correct identity answer. |
| Edrin Shaw | What he perceived during the failed patrol. | Recover, make the town record Mira and Tomas rather than reduce them to missing numbers, and learn whether his testimony can still help. | Contradictory route testimony, named losses, and later recognition of the first relic's markings. | Why the route changed or what lies beyond the sealed threshold. He survives this slice and remains a witness, not a quest vendor. |

First encounters may begin with role labels. Personal names replace or accompany
them after natural introductions. Stable internal identifiers remain unchanged.

## Exact Dialogue And Event Script

The dialogue below is mandatory in meaning and sequence. Implementation may
adjust line wrapping and contractions but must not add early spoilers.

### P0 — Revised Intro Cards

1. **Silvana:** “Silvana was never meant to be famous. It was a lantern town at
   the kingdom's edge, a place of rain-slick roofs, warm tavern smoke, and old
   roads that ended at a sealed dungeon stair.”
2. **The opening:** “Then the stair opened. Treasure-seekers, soldiers,
   scholars, and fools entered with bright steel and louder promises. Most did
   not return.”
3. **Contradictory returns:** “Those who came back spoke of doors where no door
   should be, symbols repeated in rooms that shared no map, and hours none of
   them could remember the same way.”
4. **The town:** “Now the tavern keeps a candle in the window. The barracks
   counts missing names. The church prays for people it has not met yet.”
5. **The hero:** “You arrive with reasons of your own: fortune, service,
   knowledge, or the chance to become someone your old life would not permit.”
6. **The choice:** “Silvana has sent out its plea. Step below, if you choose.
   Return with answers, if the dark allows it.”

### P1 — Ordinary Evening And Arrival Motive

The scene opens on work already in progress.

- **Liora:** “If Pell invites everyone he owes a drink, we will need three more
  tables for the wedding.”
- **Joffrey:** “Only three?”
- **Pell:** “A debt is a kind of invitation.”
- **Oren:** “Not in my tavern.”

Oren turns to the hero.

- **Oren:** “New face. Oren Caldus. People come to Silvana chasing something or
  fleeing it. What brought you to my door?”

The player chooses exactly one saved motive:

| Value | Player-facing answer |
| --- | --- |
| `Fortune` | “The opened depths promise a better fortune than the road behind me.” |
| `Service` | “People are missing. If I can help, I should.” |
| `Knowledge` | “I want to know what opened beneath this town.” |
| `Reinvention` | “I needed a place where my old life would not choose for me.” |

Oren acknowledges without judging the answer. Tavin places the drink Oren
offered beside the hero before they ask twice. The Hooded Figure is visible in
an unlit corner but does not speak.

Set `joffrey_tavern_scene_seen`. This is the first of the four required living
Joffrey scenes and must not be replayed later as new information.

### P2 — Incomplete Patrol Return

The tavern door strikes the wall. Joffrey catches Edrin before he falls; Liora
clears a table and begins binding his wounds.

- **Caedmon:** “Edrin. You left with Mira and Tomas. Where are they?”
- **Edrin:** “Still below. We took the north survey route—the one Joffrey
  marked last week. Mira chalked every turn.”
- **Joffrey:** “That route has two junctions before the old drainage hall.”
- **Edrin:** “I counted four. Tomas swore the passage never bent. We checked the
  wall. Mira's marks were there, but not in the order she made them.”
- **Caedmon:** “Then what happened?”
- **Edrin:** “The lamps went out. We heard stone moving. When the light came
  back, a sealed door stood where the passage had been. Mira and Tomas were on
  the other side.”
- **Caedmon:** “Did you hear them?”
- **Edrin:** “Tomas, once. Mira kept striking the stone. She shouted that the
  same three marks were carved beneath our feet, but I saw them above the
  door.”
- **Joffrey:** “Why did you leave?”
- **Edrin:** “Something was following me. Pale eyes. Every time I looked back,
  it wore a different shape. I came back because they need help—not because I
  stopped looking.”

The hero chooses one response. All are compassionate, mechanically neutral, and
set one remembered expression:

| Value | Player-facing action |
| --- | --- |
| `ClearSpace` | Clear a place for Edrin and keep the crowd back. |
| `SteadySurvivor` | Steady Edrin while Liora binds the wound. |
| `RememberAccount` | Listen closely and repeat the account to Caedmon without embellishment. |
| `FetchHelp` | Bring Caedmon's kit and Oren's clean water before being asked. |

Oren later vouches for the conduct he observed. No response awards an item,
experience, reputation, or mechanical bonus.

### P3 — Caedmon's Offer

- **Oren:** “They helped before anyone promised coin.”
- **Caedmon:** “That tells me why you trust their hands. It does not tell me
  whether I trust their judgment.”
- **Oren:** “Then give them something small enough to prove it.”
- **Caedmon:** “Three patrols have returned with reports that contradict their
  own maps. My people know those routes too well; every one of them begins by
  defending what they remember.”
- **Caedmon, to the hero:** “You are new. You have no old map to protect and no
  comrade's pride to excuse. I do not need another confident story. Follow the
  reports and bring me something the ledger cannot argue with.”

The player may accept `Uncertain Reports` or defer. Deferral returns control to
town and leaves the offer available from Caedmon. It does not replay P1 or P2.

### C1 — Ledger Examination

The barracks presents three concise entries in any order:

- **Route entry:** “North passage, fourteen turns. The returning scout remembers
  nine. Both maps bear the same hand.”
- **Time entry:** “Patrol absent two nights. Every survivor insists they were
  below for less than an hour.”
- **Threshold entry:** “Sealed stone, three marks around an empty center.
  Witnesses disagree whether the marks stood above, below, or behind the door.”

After all three are inspected:

- **Edrin:** “I know what I saw. I just do not know when I saw it.”
- **Joffrey:** “Bad maps drift. They do not repeat the same mistake in three
  different hands.”
- **Caedmon:** “Then find what is repeating.”

Set `joffrey_patrol_briefing_seen`. This is the second required living Joffrey
scene.

### C2 — First Descent

At the existing north-edge descent target `(3, 0, 1)`, show once:

> The worked stone nearest Silvana bears recent tool marks and drainage cuts.
> Beneath them, an older arch continues into masonry no town ledger claims.

This establishes layered practical construction without explaining the deeper
Guardian foundation.

### C3 — Optional Human Outcomes

`Bring Him Home` and `Rookie Mistake` remain optional.

- Timmy returns alive through the existing encounter and `Timmy Home` event.
  Oren, Liora, and Caedmon receive short repeat-safe acknowledgement lines.
- The Rookie remains dead. Preserve the body at `(8, 8, 1)`, the two-Zombie
  encounter, the `Dead Soldier` inventory state, death-drop recovery, burial
  turn-in, rewards, and tests.
- Rewrite victim-blaming copy. Caedmon accepts responsibility for sending an
  unready recruit into a culture that praised risk.
- Neither outcome gates `The Butcher`, `Cry Havoc!`, or Triangulus.
- If both resolve, the ledger shows the intended contrast: one name returned to
  a family and one returned for burial.

The revised `Something to Cry About` is an optional later echo of this
expedition, not a requirement for this slice. After `Rookie Mistake` is turned
in, Caedmon may offer it under its separate implementation contract. Its
anguished figure is the expedition's sole survivor mourning a different dead
companion on floor 2; the Rookie was not rescued.

### C4 — Joffrey's First Living Work Scene

On the first eligible town return after the ledger is read:

- **Joffrey:** “Your route and mine disagree at the same junction. I drew mine
  before you arrived.”
- **Hero response:** acknowledge uncertainty, defend the observation, or ask
  what changed. The response is local flavor and need not persist in V1.
- **Caedmon:** “A map is a promise to the next patrol. We correct it before we
  ask someone else to trust it.”
- **Liora:** “And when the correction sends another patrol down?”
- **Joffrey:** “Then I go with them.”
- **Liora:** “That is the answer I was afraid you would give.”

Set `joffrey_route_review_seen`. This is the third required living Joffrey
scene. Chapter 5 owns the fourth, his missing-patrol departure. Later gates must
check these explicit flags rather than infer the scenes from character level.

### C5 — The Butcher

Reclassify `The Butcher` from Main to Progression. Preserve the Minotaur at
`(3, 2, 1)`, the only approach to the level-2 stair at `(3, 0, 1)`, the two
`OldKey` rewards, experience, combat, and access behavior.

Use this framing:

- **Oren, offer:** “That stair was open a week ago. Then the Minotaur came up
  from the lower passages and claimed the corridor before it. Patrols reached
  the second level before; now no patrol, rescue party, or explorer can go
  deeper. Kill the Butcher and I will give you the keys carried by the last
  people who tried.”
- **Oren, completion:** “The stair is open again. That does not make it safe.
  Take the keys. Their last owners will not need them.”

The Minotaur is a recent threat rather than the reason older expeditions could
not reach level 2. It is neither a Guardian nor part of the relic doctrine. It
is not part of Edrin's patrol route, cannot be bypassed on the way to level 2,
and is not a prerequisite for `Cry Havoc!`, the Barghest, or Triangulus.

### C6 — Barghest Lead

When `Uncertain Reports` is active, the ledger scene is complete, and the
existing level requirement is met:

- **Caedmon:** “One account survives every rewrite: a dog-shaped thing near a
  sealed chamber. Each witness gives it a different body and the same eyes.”
- **Joffrey:** “Barghest, if the old bestiary is useful. Fear gives a
  shapeshifter plenty to work with.”
- **Caedmon:** “Put it down. Search the chamber. Bring back evidence, not a name
  from a book.”

This offers `Cry Havoc!`. Its target, reward, and experience remain unchanged.

### C7 — Barghest Encounter

Replace the claim that it guards the altar with presentation that preserves
uncertainty:

> The shape in the chamber will not hold. Wolf, goblin, hound, and something
> between them pass across the same pair of spectral eyes. Every form looks
> briefly like the one you expected to see.

The Barghest attacks because the hero enters its claimed lair. It does not speak
as an appointed custodian and does not administer a deliberate trial.

### C8 — Patrol Fate And First Prior-Explorer Fragment

After the Barghest is defeated and before Triangulus can be collected, the hero
finds Tomas Reed beneath fallen stone, identifiable by his patrol clasp. Mira
Venn is not present. Her chalk route marks continue beyond Tomas, cross the
threshold, and end without a body or a clear return path. This confirms Tomas's
death while preserving Mira as missing; neither the Barghest nor the relic is
presented as a complete explanation for her disappearance.

This is an environmental discovery, not a transported body, quest item, new
combat, reward, or map gate. Set `opening_patrol_fate_seen` and allow later
ledger and Edrin dialogue to remember the fixed outcome.

At the same threshold, present a weathered note:

> I wrote my name beside every turn so the dark could not take it. At the
> seventh mark, the letters were mine but the hand was not. A name is proof only
> while someone still chooses to answer to it.

The fragment has no signature and never uses `Acolyte`. It is a one-time
critical-path event attached to the existing threshold flow, not a new tile,
inventory item, reward, or map gate.

### C9 — Triangulus Discovery And Answer

Use the existing relic-room interaction and full-restoration behavior. Replace
generic discovery copy with:

> Triangulus rises from the altar, its three points bright with mind, body, and
> remembered choice. The chamber steadies, but the relic does not feel complete
> or self-explanatory.

Before granting the relic, ask:

> When title, blood, and expectation fall silent, what remains yours?

| Value | Player-facing answer |
| --- | --- |
| `ChosenName` | “The name I choose to answer to.” |
| `Deeds` | “What I have done, and what I do next.” |
| `Memory` | “What I refuse to forget.” |
| `NextChoice` | “The choice that is still mine to make.” |

Every answer is valid. It does not change stats, rewards, class legality,
relic access, or quest completion. Store the answer for later dialogue,
Guardian echoes, and Reflection.

After the answer, grant Triangulus exactly once, set `Uncertain Reports` to
`report_first_relic`, and preserve current relic synchronization.

### C10 — Barracks Report

Turning in `Uncertain Reports` remains the sole event that creates
`The Holy Relics`. Caedmon resolves the expedition first:

- **Caedmon:** “Before we discuss what you recovered, we finish the patrol
  account.”
- **Edrin:** “Tomas?”
- **Caedmon:** “Found dead at the sealed threshold. Mira's route marks continued
  beyond him, but they ended without a body.”
- **Edrin:** “Still missing is not the same as gone.”
- **Caedmon:** “No. It is not.”

Caedmon then lays out three old expedition ledgers beside the recovered
Triangulus relic:

- **Caedmon:** “These patrols entered by different routes and believed they had
  found different chambers. All three copied the same markings.”
- **Joffrey:** “The lines were incomplete. Set the relic beside them and the
  fragments form the same arrangement.”
- **Edrin:** “Mira kept saying the empty center mattered.”
- **Caedmon:** “There is more. An older, damaged record shows six positions
  arranged around that center.”
- **Joffrey:** “Six chambers?”
- **Caedmon:** “Perhaps. Or six objects, six stations, or one mistake repeated
  by generations of scribes.”
- **Caedmon:** “We have evidence of a pattern, not an explanation. Recover
  anything that answers this relic and bring it home.”

Create `The Holy Relics` and preserve its aggregate collection behavior. The
scene does not name the principles, identify the relics' purpose, or suggest a
seventh absence.

### C11 — Tavern Aftermath

On the next tavern visit after C10, news of the discovery has already spread.
Several conversations stop when the hero enters.

The first reactions overlap:

- **Excited patron:** “If one of those can make sense of the old records,
  imagine what six could show us.”
- **Uneasy patron:** “Those records describe changing passages and missing
  hours. Perhaps some things were hidden for a reason.”
- **Angry patron:** “Tomas is dead, Mira is gone, and we brought the thing they
  found home? Break it before it costs another name.”
- **Oren:** “No one is breaking anything in my tavern. No one is calling it our
  salvation, either.”

The familiar circle responds:

- **Liora:** “Put it somewhere people do not have to die proving what it is.”
- **Joffrey:** “If it explains the routes, it may keep the next patrol alive.
  That is reason enough to study it—not reason enough to trust it.”
- **Pell:** “Three points. Knew a fellow with a three-point plan once. Lost two
  points and married the third.”

Oren's look ends Pell's joke before it displaces the argument.

As the room returns to scattered debate, Tavin clears an untouched cup near the
hero:

- **Tavin:** “Everyone in this room has decided what that relic is. Did it seem
  so eager to decide what you are?”

The hero need not answer, and Tavin does not press. The varied reactions present
the relic as opportunity, omen, and intolerable danger without supplying the
correct interpretation.

### C12 — Hooded Figure Response

At the next transition out of the tavern after C11, the Hooded Figure stands
beneath the eaves without obstructing the hero's path.

- **Hooded Figure:** “Inside, they have already named it promise, omen, and
  threat. Certainty is often the first chain people offer one another.”

The next line repeats the hero's stored `triangulus_identity_answer`:

| Stored value | Hooded Figure line |
| --- | --- |
| `ChosenName` | “At the altar, you said what remained yours was the name you choose to answer to.” |
| `Deeds` | “At the altar, you said what remained yours was what you have done, and what you do next.” |
| `Memory` | “At the altar, you said what remained yours was what you refuse to forget.” |
| `NextChoice` | “At the altar, you said what remained yours was the choice that is still yours to make.” |
| `Unrecorded` or unavailable | “At the altar, you gave an answer no witness could reward or correct.” |

The Hooded Figure concludes:

- **Hooded Figure:** “Let them argue over the relic. Do not let their certainty
  replace it. Your answer mattered because it was freely yours—not because it
  was the answer someone else wanted.”

The hero may stop and listen or continue walking. Either action completes the
scene. The Hooded Figure does not follow, block movement, grant an item, reveal
an allegiance, or judge which answer the hero selected.

## Quest Mapping

| Quest | Category | Packet action | Prerequisite and handoff |
| --- | --- | --- | --- |
| `Uncertain Reports` | Main | Rewrite offer/help/report copy; retain staged implementation and reward. | Offered after P2/P3; first relic advances it; turn-in creates `The Holy Relics`. |
| `The Butcher` | Progression | Preserve target, rewards, level, and sole level-2 gate; correct its framing and category. | Independent of the Barghest/Triangulus Main route. Runtime category migration must occur atomically with the approved Progression work. |
| `Cry Havoc!` | Main | Preserve target, reward, level, and combat; revise Barghest framing. | Requires active `Uncertain Reports`, the completed ledger scene, and current level eligibility. It is independent of Minotaur state. |
| `The Holy Relics` | Main | No split. Preserve aggregate six-relic contract. | Created only when `Uncertain Reports` is turned in after Triangulus. |
| `Bring Him Home` | Side | Preserve optional rescue and rewards; add town acknowledgement. | Never gates Main progression. |
| `Rookie Mistake` | Side | Preserve death/body recovery mechanics and rewards; rewrite blame and add ledger reaction. | Never gates Main progression. |
| `A Candle for the Descent` | Side | Preserve optional tutorial route; keep instructions separate from Seraphine's voice. | May echo C2; never gates Main progression. |
| `Rat Trap` | Side | Preserve as ordinary opening texture. | No story-state dependency. |
| `An Honest Introduction` | Side | Preserve as optional character/system introduction. | No critical-path dependency. |
| `Something to Cry About` | Side | Record the corrected expedition relationship for its later implementation. | May be offered only after `Rookie Mistake` turn-in; not required by this packet. |

## World Mapping

| Surface | Existing anchor | Packet use |
| --- | --- | --- |
| The Thirsty Dog | Existing tavern/town interaction | P1, P2, P3, C11. No venue topology change. |
| Barracks | Existing Sergeant quest surface | C1, C6, C10 and optional quest reactions. |
| First descent | `(3, 0, 1)` | One-time layered-dungeon environmental text. |
| Rookie body | `(8, 8, 1)` | Preserve body recovery, combat, inventory, drop, and burial behavior. |
| Minotaur room | `(3, 2, 1)` | Preserve encounter; revise narrative framing only. |
| Locked door | `(11, 18, 1)` | Preserve existing key and door behavior; no new story lock. |
| Barghest room | `(18, 2, 1)` | Preserve encounter; revise presentation and prerequisite. |
| Relic room | `(19, 0, 1)` | C8 fragment trigger and C9 Triangulus choice/discovery. |

### Verified Runtime Anchors

Static verification against the loaded level-1 map and tileset confirms every
coordinate used by this packet:

| Coordinate | Loaded tile | Verified contract |
| --- | --- | --- |
| `(3, 0, 1)` | GID 36 / `StairsDown` | The first descent target is correct. Its corridor is a dead end reached only through the Minotaur route. |
| `(3, 2, 1)` | GID 26 / `MinotaurBossRoom` | Walls on both sides and the stair corridor immediately north make the Minotaur the sole level-2 gate. |
| `(8, 8, 1)` | GID 5 / `CavePath1` | `CavePath1.rookie_body_marker` explicitly binds the Rookie encounter to this coordinate. |
| `(11, 18, 1)` | GID 12 / `LockedDoor` | Existing Old Key and lockpick behavior remains the route gate. |
| `(18, 2, 1)` | GID 1 / `BarghestBossRoom` | The Barghest room and existing combat anchor are correct. |
| `(19, 0, 1)` | GID 32 / `RelicRoom` | The level-indexed relic interaction grants `Relic1`/Triangulus and performs the existing full restoration. |

C8 is not a new threshold tile. Its patrol fate and fragment presentation must
run once from the existing approach/interact flow before the first successful
C9 interaction with the `RelicRoom` at `(19, 0, 1)`.

### Verified Runtime Constraints

- Runtime quest dictionaries currently contain only `Main`, `Side`, and
  `Bounty`. `Player`, `quest_progress.ensure_quest_categories()`, and
  Pygame `QuestManager` all encode that three-category assumption. Moving
  `The Butcher` to `Progression` therefore requires the previously approved
  atomic category migration; changing only quest content would lose offers,
  advancement, presentation, or save state.
- `Cry Havoc!` currently lives at `Sergeant/Main/20` with no `Requires`
  field. Pygame eligibility currently checks only level plus a single
  prerequisite that must already be turned in. The opening slice must add a
  shared story-state eligibility predicate for active `Uncertain Reports` and
  `opening_ledger_seen`. It must not encode `Requires: Uncertain Reports`,
  because that would delay `Cry Havoc!` until after Triangulus is recovered
  and reported.
- The shipped staged chain already advances `Uncertain Reports` when the first
  relic enters special inventory and creates `The Holy Relics` only from the
  shared post-turn-in hook. The new scenes must preserve those owners rather
  than duplicate quest creation.
- Relic collection currently has two execution paths:
  `RelicRoom.special_text()` in core and
  `DungeonInteractionMixin._interact_relic()` in Pygame. Both grant the
  level-indexed relic, mark the tile read, restore health and mana, and
  synchronize quests. C8/C9 eligibility, choice persistence, grant-once
  behavior, and restoration must be factored through one shared core transition
  used by both paths.
- `main_story.normalize_state()` currently treats unspecified scalar fields as
  booleans. The three new enumerated values—`arrival_motive`,
  `arrival_aid`, and `triangulus_identity_answer`—need explicit
  normalization branches or they will be coerced and lost.
- Cross-system migration cannot be inferred by `main_story.normalize_state()`
  alone. `src/core/save_system/player.py` must run the opening-story migration
  after special inventory and quests are restored and after `main_story` is
  normalized, so existing relic and quest state can set the accepted
  `Unrecorded` and seen values safely.
- Intro pages are loaded from `special_events.json["Intro"]` through
  `data_loader.get_intro_story()` and presented by
  `Game.show_intro()` with `StoryCardSequence`. P1 must enter from that
  new-game flow after the intro completes and before the ordinary town loop;
  established saves must continue to bypass it.

No map relocation or topology change is authorized to satisfy this packet.

## State Contract

Add these normalized fields to `main_story`:

| Field | Default | Allowed values or meaning |
| --- | --- | --- |
| `arrival_scene_seen` | `false` | P1–P2 have completed. |
| `arrival_motive` | `null` | `Fortune`, `Service`, `Knowledge`, `Reinvention`, or `Unrecorded` for migrated saves. |
| `arrival_aid` | `null` | `ClearSpace`, `SteadySurvivor`, `RememberAccount`, `FetchHelp`, or `Unrecorded`. |
| `hooded_figure_observed` | `false` | The silent P1 observation has occurred. |
| `opening_ledger_seen` | `false` | All three C1 entries and their conclusion have been presented. |
| `first_descent_story_seen` | `false` | C2 environmental text has appeared. |
| `joffrey_tavern_scene_seen` | `false` | P1 has completed; this is the first required living Joffrey scene. |
| `joffrey_patrol_briefing_seen` | `false` | C1 has completed; this is the second required living Joffrey scene. |
| `joffrey_route_review_seen` | `false` | C4 has completed; this is the third required living Joffrey scene. |
| `opening_patrol_fate_seen` | `false` | C8 confirmed Tomas dead and Mira still missing. |
| `acolyte_triangulus_fragment_seen` | `false` | C8 has completed. |
| `triangulus_identity_answer` | `null` | `ChosenName`, `Deeds`, `Memory`, `NextChoice`, or `Unrecorded`. |
| `first_relic_tavern_aftermath_seen` | `false` | C11 has completed. |
| `hooded_figure_triangulus_response_seen` | `false` | C12 has completed. |

Do not duplicate boss-defeat, relic ownership, quest stage, quest completion, or
turn-in state inside `main_story`. Derive those facts from their existing
owners.

### Retry And Repeat Behavior

- P1–P2 run once on a fresh game after the intro cards.
- P3 can be deferred and remains available through Caedmon.
- Closing a presentation early must leave the current scene eligible to replay
  unless its mandatory state and choice were committed.
- P1, C1, C4, C8, C11, and C12 are one-time and repeat-safe.
- Triangulus is granted only after a valid identity answer is stored.
- Reloading after an answer or relic grant must not prompt again or duplicate
  the relic, restoration, quest progress, or event.
- Optional NPC reactions may repeat only as short ambient lines and must never
  re-award or mutate quest state.

### Current-Save Migration

Current saves must not be forced through a new arrival scene retroactively.

- New-player construction receives the fresh defaults above.
- Loading a save created before these fields existed sets already-passed opening
  scenes to seen and records unavailable choices as `Unrecorded`.
- Migrated saves treat all three opening Joffrey living scenes as seen if
  `The Holy Relics` already exists; they must not be forced to replay scenes
  solely to satisfy the later Chapter 5 gate.
- If Triangulus is already owned, `triangulus_identity_answer` becomes
  `Unrecorded`, the patrol fate and fragment become seen, and no discovery
  scene replays. Migrated state records Tomas as dead and Mira as missing
  without replaying the threshold presentation.
- If `Uncertain Reports` is already at `report_first_relic`, treat C8 and C9
  as complete without changing its current stage.
- If `The Holy Relics` already exists, treat the barracks report and tavern
  aftermath as complete; do not recreate or reopen either quest.
- Preserve existing `Rookie Mistake` body possession, dropped-body coordinate,
  completion, and turn-in state exactly.

The implementation must distinguish fresh construction from load normalization;
missing fields alone are not permission to replay P1 on an established
character.

## Presentation Contract

- Use the existing `StoryCardSequence` for P0.
- Use existing dialogue/special-event surfaces for P1–P3, C1, C4, and C10–C12.
- Reuse current NPC art when available. No new portrait, map, or cinematic asset
  is required for V1.
- Keep the hero's motive and Triangulus answers in explicit selectable menus;
  do not encode them as free text.
- Clear or release buffered input between consecutive cards, dialogue, and
  choice menus so one action cannot skip multiple beats.
- Every scene must support keyboard and the existing semantic command path.
- Preserve town and dungeon music ownership. Optional door, rain, crowd, or
  relic accents may be added only through the shared sound manager with silent
  fallback.
- Critical text must remain readable without audio or generated imagery.
- Do not put long story text into combat HUD, shop comparison, or reward panels.
- Do not require a new save immediately after a choice; the next ordinary save
  persists the normalized story state.

## Implementation Surfaces

Verified owners include:

- `src/core/data/content/special_events.json`, specifically `Intro` and
  event-copy entries, for revised story text;
- `src/core/data/data_loader.py` and `src/ui_pygame/game.py` for the existing
  intro-card handoff into the new P1–P3 arrival flow;
- `src/core/data/content/quests.json` and
  `docs/spreadsheets/quests/quests.csv` for synchronized quest copy, levels,
  categories, and declarative prerequisites;
- `src/core/main_story.py` for defaults and explicit enum-aware normalization;
- `src/core/quest_progress.py` for staged relic synchronization and shared
  story-eligibility helpers;
- `src/ui_pygame/gui/quest_manager.py` plus every core/UI/save category
  consumer for the atomic `Progression` migration and quest presentation;
- barracks, tavern, and town-transition presentation for C1, C4, C6, and
  C10–C12;
- `src/core/map_tiles/rooms.py`,
  `src/ui_pygame/gui/dungeon_manager/interactions.py`, and a shared core relic
  transition for C8–C9;
- `src/core/map_tiles/paths.py` and `src/core/map_tiles/rules.py` for the
  preserved Rookie body/drop behavior;
- `src/core/save_system/player.py` for cross-system fresh-versus-migrated
  story-state handling after inventory and quest restoration;
- current map-tile and renderer owners for visibility and interaction only.

Use shared core helpers for eligibility and state transitions. Pygame presents
decisions and events but must not become the sole owner of story rules.

## Validation

### Automated Content And State

- Revised intro contains no Vesperion, Voluntas, Guardian, principle, or
  confirmed six-relic claim.
- Only the four accepted arrival-motive values and four Triangulus-answer values
  normalize as current choices; unknown values become `Unrecorded` or
  `null` according to migration context.
- C12 repeats the stored Triangulus answer through the matching dialogue
  variant; `Unrecorded` uses the neutral fallback and never invents a choice.
- New players receive fresh opening defaults.
- Current saves do not replay P1 and do not lose quest, relic, or Rookie body
  state.
- Each one-time scene is repeat-safe across save round trips.

### Quest And Route

- `Uncertain Reports` is offered after P2 and can be deferred safely.
- `The Butcher` retains target, rewards, experience, coordinates, and sole
  level-2 access behavior while moving to Progression.
- `Cry Havoc!` cannot appear before its story prerequisites and existing level
  requirement, does not depend on Minotaur defeat, and retains target, reward,
  and combat.
- Tomas's death, Mira's missing status, and the unnamed fragment always appear
  before first Triangulus collection.
- Triangulus cannot be duplicated by reload or repeated interaction.
- First relic collection advances `Uncertain Reports` without immediately
  creating `The Holy Relics`.
- Turning in `Uncertain Reports` creates exactly one `The Holy Relics`.
- Optional Timmy and Rookie outcomes never block the Main route.
- The Rookie remains dead and all body drop/recovery regressions remain green.

### Presentation

- Buffered input cannot skip the motive or Triangulus choice.
- Deferring P3 returns cleanly to town control.
- Leaving and returning during an eligible scene neither duplicates it nor
  leaves the player blocked.
- Dialogue is legible with existing resolution/scaling and without audio.
- No critical scene depends on optional art.

### Manual Playtest Prompts

1. Does the tavern feel like a community already in motion before it becomes a
   quest hub?
2. Does the wounded patrol return create urgency without overexplaining the
   mystery?
3. Does Caedmon's trust feel earned but limited?
4. Can the player state a motive without being assigned a fixed backstory?
5. Do Timmy and the Rookie deepen the town when completed without feeling
   mandatory?
6. Do Joffrey's tavern, patrol-briefing, and route-review scenes feel distinct,
   and does he register as competent, loved, and alive before later tragedy?
7. Is the Minotaur clearly the unavoidable gate to level 2 without being
   falsely connected to Edrin's patrol, the Barghest, or relic lore?
8. Does the Barghest make contradictory testimony physically legible?
9. Does finding Tomas while Mira remains missing feel like a meaningful answer
   and a bounded future question rather than an arbitrary sequel hook?
10. Does the Acolyte fragment invite curiosity without exposing the later title?
11. Does Triangulus feel like a story event rather than only a full-heal pickup?
12. Is the six-part possibility earned by evidence and still meaningfully
    uncertain?
13. After returning to ordinary play, is there a clear reason to continue?

## Acceptance Gate

The design gate is complete:

- dialogue, minor names, scene order, and remembered choices are accepted;
- quest identifiers, levels, rewards, staged relic behavior, coordinates, tile
  types, and route relationships are verified against the current runtime;
- the state and migration contract is accepted, including explicit enum
  normalization and cross-system old-save handling;
- owner documents and documentation indexes link to this packet without
  duplicating its script;
- no unresolved choice changes combat, rewards, topology, or save policy.

Implementation remains responsible for the automated and manual validation
above. This reconciliation changes documentation only; it does not claim the
opening slice or the `Progression` category is already implemented.
