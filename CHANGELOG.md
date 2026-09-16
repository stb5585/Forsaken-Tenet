# The Forsaken Tenet - Changelog

## [Unreleased]

### Foundational Gameplay Baseline

- Completed the foundational gameplay refactor: immutable ability slugs and
  typed taxonomy, versioned current-save serialization, actor-relative combat
  intents, one-roll fitted contact, virtual readiness, concealment/targeting,
  and a unified action interface.
- Established the post-refactor seed-1337 characterization reports and kept
  ordinary dungeon encounters singleton after Multi-Enemy Pilot 3 qualified no
  pair. One- and two-enemy encounter support remains available through the
  bounded combat APIs and development overrides.
- Retired unmarked pre-foundation save compatibility rather than guessing at
  ambiguous state; current versioned saves retain deterministic dungeon state
  and round-trip coverage.

### Combat Presentation And Input

- Reworked combat actions into a persisted six-slot shortcut bar plus a
  read-only All Actions catalog. Shortcut assignment now lives in the combined
  Character Menu Abilities workspace, with learned Skills and Spells presented
  as draggable icon cards.
- Made empty shortcuts inert; keyboard menu navigation skips shortcut tiles,
  while number keys, mouse, and touch continue to activate assigned shortcuts.
- Combined the current actor and timeline into a single ribbon with player- and
  enemy-side outlines, and deferred level-up/resource mutations and timeline
  cleanup until enemy-fade presentation completes.
- Restored Defend to boss-room action lists while retaining the intentional
  boss-fight Flee restriction. Increased Charge's delayed hit to 2.5× weapon
  damage without changing its one-turn setup, MP cost, or contested stun.
- Corrected enemy escape settlement so an escaped singleton grants no
  experience, gold, loot, kill, bounty, or quest credit.
- Added labeled previous/next hostile targeting controls, stable hostile-lane
  timeline colors, direct lane selection, and debug-only `K` Auto Kill access.
- Added affected bounty counts to combat victory popups and retained combat
  outcome sequencing behind the completed enemy fade.
- Rebalanced Barghest for a normally geared level-15 encounter, reducing its
  overwhelming initiative and damage pressure while preserving its boss kit.
- Routed natural-weapon blocks to the generic impact effect instead of the
  metal weapon shield-block effect.
- Made Cambion anti-magic encounter-wide for both player and enemies, and
  added metal-weapon Disarm audio feedback.

### Dungeon, Gathering, And Persistence

- Kept the shared dungeon music continuous through dungeon combat and assigned
  dedicated pending themes for final level 6, the Funhouse, and the Realm of
  Cambion; ordinary levels 1–5 retain the current dungeon bed.
- Organized the reviewed Sonniss source library into local candidate,
  unsuitable, and source-metadata directories without promoting or deleting
  any raw audio.
- Renamed the local source/reference workspace from `old_assets/` to
  `unused_assets/` to distinguish currently unused material from retired work.
- Integrated Sonniss-derived effects into the primary sound directory with
  provenance documented separately, and added blade-specific parry feedback.
- Converted the dungeon bed and longer custom effects to compact runtime OGG
  assets while preserving source WAV files outside the runtime asset tree.
- Replaced automatic Deathcap collection with deterministic, persistent
  gathering nodes on eligible cave paths. Druid/Archdruid identify and harvest
  Acorn, Vine Seed, Fungus Spore, and Hemlock Root; Assassin identifies and
  harvests Deathcap Mushroom. Themed enemy drops remain an additional route.
- Added visible, floor-projected root and fungus overlays, specialist and
  non-specialist discovery feedback, explicit `O` harvesting, guarded forage
  loot popups, node persistence, and legacy Deathcap-node migration.
- Stored ordinary chest Mimic outcomes at deterministic dungeon generation so
  loading a save cannot reroll a Mimic into a normal chest. Guaranteed Funhouse
  Mimics remain unchanged.
- Cleared stale dungeon frames after death/re-entry and completed catalog item
  icon routing, including Monocane, crossbows, bolts, and venoms.
- Made trap damage an input-guarded dungeon acknowledgement that blocks movement
  until dismissed, and made acknowledgement popups resistant to buffered input.
- Surface existing post-level-10 resurrection gold costs and possible stat loss
  in the defeat summary before returning to town.

### Quest, Content, And Playtest Reliability

- Added Magic Shop and Thieves Guild quest access, with eight level-spread
  quests using collection, defeat, landmark, and staged town-conversation
  objectives. Early Magic Shop beats provide route guidance without restricting
  exploration.
- Made conversation leads advance into follow-up objectives rather than
  standalone turn-ins; added Bandit defeat progress, lower-level slime access
  to Fungus Spore drops, and moved the Lich commission to its higher-level
  placement.
- Fixed bounty initialization, collection-progress reconciliation and capping,
  completed-count journal display, repeat-safe turn-in behavior, and generated
  catalog spreadsheet drift.
- Added focused regression coverage for gathering rendering/persistence,
  chest outcomes, quest stages and collection progress, escape settlement,
  combat presentation, and deterministic post-hit ability assertions.
- Made shop Quest entries conditional on active, available, or turn-in quests;
  shop equipment comparisons now identify items already equipped in compatible
  slots without preventing duplicate purchases.
- Restored the Character Menu's learned-ability reference view, including
  passive abilities, and retained Action Layout for shortcut assignment with
  hover descriptions.
- Recorded the current shop-gate and stock-filter audit as a deferred economy
  design gate; no prices, stock, or opening levels changed.
- Moved Scorpion Venom from Wererat loot to Giant Scorpion loot to match the
  creature-themed drop source.

### Promotion Stabilization

- Recorded pre-release saves as disposable development artifacts, removed
  format versions and legacy migration machinery, and retained atomic writes
  for current saves.
- Added portable checkout/frozen resource paths and platform user-data paths,
  moved runtime maps into package data, and introduced a PyInstaller onedir
  build with a headless frozen-resource smoke test.
- Added the MIT license and complete asset-category inventory, recorded
  OpenAI-generated and Sonniss-derived audio provenance, separated review
  sheets from runtime assets, and removed retired curses ASCII enemy art and
  conversion tools.
- Made startup failures return nonzero, moved signal registration into the
  executable path, and retained structured event subscriber failures.
- Established Black, isort, focused Ruff, incremental strict mypy, source
  coverage, and release/manual-only artifact CI gates.
- Restored current architecture and stabilization decision records and fixed
  stale launcher, module, map, and test-count documentation.

### Development Tool And Code Cleanup

- Split the monolithic ability-tree manifest into shared metadata and five
  base-class lineage modules while preserving its existing import facade.
- Split the progression runtime into value models, tree construction/registry,
  and player-facing service modules while preserving `src.core.progression`.
- Split the pygame progression screen into tree rendering, panel rendering,
  and interaction orchestration modules while preserving its public class.
- Split battle-engine turn handling into preparation, targeting, resolution,
  and lifecycle phases behind the existing turn mixin.
- Split battle actions into attack, spell, skill, and inventory/summon modules
  behind the existing action mixin and package exports.
- Split pygame combat selections into ability, class-mechanic, special-action,
  and shared menu-support modules behind the existing selection mixin.
- Removed pre-release progression migrations and refunds, including a reversed
  Spell Reflection node-ID rewrite that corrupted current persisted ownership.
- Retired the obsolete tab-delimited numbered-map conversion workflow, made
  Tiled JSON the explicit numbered-map authority, and retained text loading
  only for the Liminal Gap special-area map.
- Separated optional Class Ring modifiers from ordinary second-promotion
  progression: Templar Ordered Blessings and Archbishop Divine Intervention
  upgrades are terminal leaves, while ambiguous Arcane Trickster, Hierophant,
  and Troubadour tree labels now distinguish their non-ring mechanics.
- Returned Volcano and Weaken Mind to enemy-learned acquisition, made Tephra
  and Neural Connection optional terminal modifiers, completed rank metadata
  for Volcano and Stupefy.
- Repaired the balance-suite enemy roster after the enemy `Conjurer` was
  renamed to `Necromancer`, and added a regression test for CLI startup.
- Restored the Power Core quest reward path for every terminal class, removed
  Dim Mak from point-purchased progression, isolated its modifiers as optional
  leaves, and disambiguated Astromancer's Celestial Mastery talent.
- Removed the unreachable legacy Pygame level-up implementation so the screen
  has one progression-service-backed path.
- Removed confirmed unused imports and stale cleanup markers without changing
  gameplay rules.

### Documentation Consolidation And Refactor Sequencing

- Retired the temporary stabilization checklist after moving its remaining
  audio, asset-history, quality-gate, API, combat-refactor, save-policy, build,
  and playtest follow-ups into their durable owner documents.
- Replaced stale manually maintained game spreadsheets with 83 deterministic
  CSV exports covering current character, special, item, enemy, and quest
  catalogs, plus a regeneration tool and drift regression.
- Replaced the shipped-history-heavy roadmap with a forward-looking priority
  map centered on foundational gameplay refactors before broad manual
  playtesting.
- Added an ordered refactor plan for ability taxonomy, combat timing and
  accuracy, invisibility and targeting, multi-enemy scope, combat actions and
  resource presentation, and dungeon recovery.
- Rebased the playtest documentation as a post-refactor queue while preserving
  focused slice validation and the class-kit evidence format.
- Retired the completed progression checkpoint and Multi-Enemy Pilot 1-2 plans
  from the active documentation set after consolidating their durable
  boundaries into current owner documents. Their full text remains available
  in Git history.
- Corrected stale ability-tree, promotion, class-kit, Class Ring, multi-enemy,
  combat, story, presentation, dungeon, and equipment status language.

### Class-Kit Closure Cleanup And Coverage

- Made shared Momentum copy class-neutral while keeping its Death Mark setup
  identity in Ninja-specific progression detail.
- Removed the retired Shield Check, Bulwark, Covering Guard, and active Shield
  Riposte/Spell Reflection APIs while preserving the finalized passive forms.
- Added parameterized behavioral coverage for every Grandmaster Weapon Art
  rank, Wizard school modifier, Warlock familiar modifier, and Shadowcaster
  terminal passive.
- Reconciled legacy Transform and Dim Mak tests with their shipped persistent
  form and full-Ki contracts, leaving the complete repository suite green.

### Spell Stealer And Arcane Trickster Stolen Magic

- Completed validate-before-spend MP handling for both spell-theft abilities
  without risking Blank Scrolls or permanent spellbook changes on invalid use.
- Connected every stolen-magic Charge source and moved its Arcane payoff to
  one action-level resolution across damaging spells, standard attacks, and
  weapon-tagged skills, including aggregate damage and miss consumption.
- Made awakened Arcane Larceny require the equipped ring, expire after three
  turns, clear with combat state, and preserve one clean payoff per combat.
- Added discreet combat status and focused regressions for caps, sources,
  spending, typed mitigation, lifecycle behavior, and ring gating.

### Inquisitor And Seeker Investigation Payoff

- Connected target-specific Revelation to standard attacks, Exploit Weakness,
  and precision weapon skills with pre-roll spending, reliability, damage
  pressure, miss consumption, and target/lifecycle cleanup.
- Completed visible-detail and telegraph evidence, all four Case Journal
  milestone effects, anti-magic/setup insight, and awakened Hidden Cache
  smoothing while keeping hidden advancement math out of player UI.
- Routed Wayfinding into all four movement tools and integrated one
  sufficiently mapped, depth-sensitive Hidden Cache reward into navigation.
- Added focused regressions for persistence, caps, hit accounting, milestones,
  prediction, selected-target presentation, movement, ring gating, and rewards.

### Thief And Rogue Authored Kit

- Connected action-scoped Fortune and Misfortune to meaningful attacks,
  avoidance, theft, luck, and status outcomes, with real pre-roll reliability
  and typed or outcome-specific severity payoffs.
- Implemented learned `Scavenger's Eye` rarity nudges and `Finders Keepers`
  extra ordinary finds while excluding quest, special, ability, summon-gated,
  class-invalid, unique, and ultimate rewards.
- Gated Cheat Death on its learned skill, made Jinx penalize accuracy and luck,
  and connected Loaded Dice to failed eligible checks and one clean
  meter-preservation payoff per combat.
- Added focused regressions for caps, action deduplication, payoff timing,
  typed damage, status and Slot Machine scaling, loot exclusions, survival,
  ring conversion, preservation, and cleanup.

### Thaumaturgist Conduit Payoff

- Connected Conduit Command to the active Xenid's next committed action with
  damage/healing amplification, miss and non-damage consumption, lifecycle
  expiration, and awakened-ring True Name signatures.
- Replaced generic borrowed-summon damage with fourteen typed Xenid
  invocations and their authored offensive, defensive, healing, and status
  riders, adding the missing Hodag and Caladrius skills.
- Added focused validation, typed-mitigation, complete-roster, action-flow,
  cleanup, healing, and ring-gating regressions.

### Shadowcaster Shade And Backlash

- Consolidated Shade of Ahool onto one combat timer and removed its obsolete
  weapon, critical, excessive-Speed, and physical-siphon predecessor effects.
- Completed Shade-expiration and low-HP-heal backlash conversion with awakened
  ring stabilization and Homunculus, Fairy, Mephit, and Jinkin variations.
- Added focused normalization, generation, modifier, conversion, lifecycle,
  and familiar regression coverage.

### Wizard School Streak And Hidden Mastery Presentation

- Connected the awakened-and-equipped Wizard ring to four registered random
  elemental riders with school-specific failure streaks, success resets, a
  consumed guarantee, and once-per-spell-action resolution.
- Made Wizard affinity mastery buffs explicitly combat-only with start/end and
  save/load cleanup.
- Hid exact Resolve Surge progress and undiscovered Burst identities while
  retaining discovery feedback, and established general-over-formula
  disclosure as the default for class-kit presentation.

### Stalwart Resolve Mastery And Surges

- Replaced placeholder scalar Resolve mastery with four persistent tracks
  trained through their associated Sentinel and Stalwart actions.
- Locked each full-bar Surge behind four qualifying uses, with action/event
  deduplication, Sentinel-to-Stalwart carryover, and save/load normalization.
- Added hidden discovery states to the Resolve tab, clearer combat logs, and
  focused progression, defensive-event, menu, and persistence regressions.

### Berserker Bloodied Momentum

- Completed action-deduplicated Bloodied Momentum generation, the shared
  below-25% round bonus, and exact Battle Scar caps of 3/4/5.
- Connected validated heavy weapon arts and Final Assault to pre-resolution
  Momentum spending, conservative accuracy/damage scaling, themed art riders,
  miss consumption, and once-per-combat Battle Scar/Class Ring preservation.
- Added the 20-scar 15% victory threshold, combat-only lifecycle cleanup,
  expanded status/log feedback, and focused end-to-end regression coverage.

### Bard And Ranger Kit Cleanup

- Connected mastered Troubadour repertoire to an MP-costed combat action and
  completed composition, exploration-step, clean-finish, route-coda, and
  Chorus Time practice/payoff behavior.
- Extended awakened/equipped Beast Master `Shared Recovery` to strengthen all
  four companion commands without adding companion turns.
- Updated Character Menu progress/coda presentation, class guidance, playtest
  coverage, and focused runtime regressions for both comparatively healthy kits.

### Promoted Tree Integrity

- Removed generated rating-family padding from the remaining Footpad, Healer,
  and Pathfinder promotion trees and pinned their compact catalog-only sizes.
- Removed generic meter-cap and Lycan control-acceleration masteries that
  contradicted finalized class-kit contracts. Bonded Bulwark remains as the
  sole authored promoted-tree payoff and no longer grants a generic rating.
- Regenerated promoted-tree diagrams and added regressions preventing the
  removed talent families and repeated ranks from returning.

### Divine And Nature Action Kits

- Rebuilt Devotion and Prayer generation around authored once-per-action
  outcomes, including shield/block, support, anti-magic, Resurrection, and
  power-up round boundaries.
- Completed Sanctuary Ward, Relic Aegis, Consecrated Conduit, Supplication,
  Great Benediction, Great Gospel, Ordered Blessings, and their class-ring
  preservation and typed-damage rules.
- Reworked combat Aspect Harmony into capped aspect charges with Fourfold
  Surge riders, Primal Ascendance, Tree of Life, and once-per-combat Harmony
  preservation.
- Moved Totem Resonance gain to successful action resolution and connected
  Soul harvest scaling plus Aspect Evolution accuracy, reliability, and output
  to nonlethal Soul Totem and Totem Surge payoffs.

### Monk, Diviner, Astromancer, Druid, And Lycan Kits

- Rebuilt Monk Ki around authored once-per-action martial, healing, and
  defensive sources; connected five one-Ki riders and made Dim Mak a full-Ki,
  18-MP Master Monk finisher with weapon, Death/Stun, essence, and ring rules.
- Added guaranteed Diviner/Astromancer learning for explicitly ranked,
  successfully resolved hostile spells and completed action-authored Foresight
  Threads, Threaded Cast bonuses, active-sign ring payoff, and Rewind safety.
- Replaced temporary-save transformation with serialized persistent overlays,
  purchased-node form unlocks, exact deficit-preserving restoration, explicit
  combat/Forms-tab controls, Lycan moon stress and behavior-earned control,
  canonical Dragon Essence, and Werewolf-only Winged Pounce.

### Pygame-Only Frontend And Headless Development

- Retired the unplaytested curses frontend from the active codebase and
  preserved its final committed revision at the annotated Git tag
  `curses-ui-final`.
- Removed the curses source, entry point, dedicated tests, package commands,
  and the last direct core-to-curses import.
- Made `launch.sh`, `launch_debug.sh`, and the primary `forsaken-tenet` package
  command start the supported Pygame frontend.
- Kept terminal development through core and integration tests, combat
  simulators, balance reports, debug encounter overrides, and diagnostic
  tools.
- Preserved JSON save compatibility through the shared `SaveManager` and
  updated active design, playtest, packaging, and contributor contracts to no
  longer require curses parity.

### Flat Progression And Authored Ability Trees

- Replaced local class-level promotion with a shared global-level progression
  runtime, stored progression points every two levels, and separately stored
  primary-attribute points every four levels.
- Rebuilt Assassin as five authored Utility, Combat, Status/Death, Stealth,
  and Counter columns. Added toxin reagent drops and crafting/coating reactions,
  rare Deathcap gathering, reusable dagger-pack serialization, Thieves Guild
  stock, Hidden Blade, and the new Assassin active and passive mechanics.
- Rebuilt Ninja as five authored Utility, Combat, Toxin/Death, Stealth, and
  Defense columns. Death Mark now uses six explicit setup attacks and three
  dedicated finishers, with resistance-aware execution, toxin mastery,
  combat concealment, trap warnings, and an integrated No-Trace Opener.
- Reworked Refueling into a cancellable channel that restores 10% maximum MP
  on its first tick and doubles its restoration on consecutive ticks.
- Added seven Ranger/Beast Master off-hand crossbows and seven selectable
  ten-shot bolt packs to the Thieves Guild. Basic attacks now fire the equipped
  crossbow, with repeating, armor-piercing, Arcane, heat-seeking, Napalm,
  delayed-explosion, recovery, inventory, shop, and save behavior.
- Added active Resist buff indicators to the Character Menu, dungeon HUD, and
  combat HUD, including distinct Shadow and Holy ward labels. Resist All now
  applies its documented resistance buffs instead of being message-only.
- Reworked promotion connectors into clear gold paths: conjunctive requirements
  merge above each promotion, while shared prerequisite nodes fan out through
  distinct anchors and alternatives retain separate stems. Hover-only violet
  highlighting covers complete required paths regardless of node availability
  and clears when the pointer leaves. SVG promotion cards are taller and place
  their `Requires ALL/ANY` summary on a dedicated second detail line. Long
  routes now stay in adjacent column gutters, and compact seven-row trees
  reserve an eighth row for unobstructed promotion paths.
- Restored Lancer's Shield Slam and Shield Block promotion requirements, made
  Assassin's Status/Death path the sole Ninja prerequisite, and restored the
  Mage elemental connection into Classical Force with straight promotion
  stems for Spellblade, Warlock, and Conjurer.
- Moved Warrior's shield requirement onto Retaliate, added missing Sentinel and
  Conjurer buffer rows, routed outer alternative paths into promotion-card
  sides, and made Shadowcaster require Shadow Bolt II plus either Doom or Mana
  Drain. In-game graph icons now rely on the details panel instead of duplicate
  labels; SVGs truncate long names and place Resolve/Blade Charges on their own
  metadata line.
- Added version-5 authored tree manifests, stable node IDs, atomic staged
  purchases, promotion previews, branch closure, equipment cleanup, ability
  retention, save/load normalization, and validation for all 49 playable
  classes.
- Made ability retention universal across promotions, including Monk, Bard,
  Ranger, Warlock, Weapon Master, and Inquisitor. Removed the obsolete pruning
  rule API and the unreachable Church learn-as-you-level promotion handler;
  class-specific promotion grants are now explicitly additive.
- Added a pygame Progression tab with authored graph geometry, an ability icon
  atlas, compact connectors, completed-tree navigation, staged node/attribute
  distribution, full Primary Attribute names, and promotion confirmation.
- Grouped generated ability-tree SVG references by base-class lineage and
  base/first-promotion/second-promotion tier.
- Completed bespoke Warrior, Weapon Master, Berserker, Grandmaster of Arms,
  Lancer, Dragoon, Sentinel, Stalwart Defender, Paladin, and Crusader trees.
- Rebuilt Warrior as six connected columns with paired shared trunks, added
  Commitment, Improved Defend, Upsurge, and Achilles Heel, and enabled
  outclassed enemies to flee with Aggressive Pursuit interception while Smoke
  Screen escapes remain exempt.
- Expanded Crusader to 26 nodes with Radiant Healing, Undead Hunter, Beyond
  Reproach, Penalization, and Divine Protection II; separated Condemnation's
  disintegration mark into Beyond Reproach and replaced the former Attack,
  Magic Defense, and HP padding with active/passive class mechanics.
- Raised Penalization, Smite III, and Divine Protection II to two-point nodes;
  compacted Sentinel to five columns without Parry; and expanded Stalwart
  Defender to five columns with Shield Offense and new Resolve engines.
- Replaced Footpad, Healer, and Pathfinder's generic four-route manifests with
  authored vertical graphs. Shared Defense, Support/Healing, Naturalism,
  Melee, and Elemental tracks can feed multiple promotions.
- Expanded Pathfinder into 40 nodes across Druid, Naturalism, Ranger, Melee,
  Shaman, Elemental, and Diviner tracks. Added Ray of Moonlight, Nullify
  Poison, Thorny Vine, Razor Talons, Call Animal, Creature Comforts, Cautious
  Assault, Unnatural Purge, Bounce Back, Spirit Strike, Conversion, Very
  Superstitious, Primal Trance, Fundamental Harmony, Intensify Elements,
  Chronology, Geomancy, and Control Z, with combat and exploration hooks.
- Added Nature as a spell damage/resistance type with multi-type ability
  metadata, and reworked Poison Strike from a dual-wield weapon skill into a
  main-hand Poison Druid spell.
- Removed promotion stat requirements of 10 or lower across every class and
  rebalanced the first-promotion gates for Pathfinder, Healer, Footpad,
  Warrior, and Mage. Shaman now requires Dexterity 14 and Intelligence 12;
  the complete authored requirement maps are enforced by progression tests.
- Expanded Healer into 36 authored Bard, Support, Cleric, Healing, Priest, and
  Monk nodes. Added Lullaby, Beginner's Luck, Mental Shard, Cacophany,
  Tranquility, Courage, Vision, Tutelary, Safeguarding, Flash Blindness, Incite
  Panic, Zen Accuracy, Staff Proficiency, Delayed Reaction, and Meditation,
  including their combat, status, healing, exploration, and weapon hooks.
- Expanded Footpad into authored Thief, Control, Assassin, Spell Stealer,
  Defense, and Inquisitor progression. Control now gates both Thief and
  Assassin, while Defense gates both Spell Stealer and Inquisitor;
  implemented Stumble Upon, Avoid Traps, Do-over, Serendipity, Aggressive
  Pursuit, Obscuration, Incantation Comprehension, Mana Depletion, Disruption,
  and Mystical Evasion.
- Added the reusable 5,000G Censer of Choking Ash to the Magic Shop as the
  required implement for Obscuration.
- Added sparse, one-use Tripwire, Magic Ward, Alert, and Red Alert traps to
  ordinary dungeon paths. Trap state persists in saves, defenses apply to
  damage, Alert traps force enemy initiative, and Avoid Traps can negate or
  halve their effects.
- Restored Grandmaster of Arms' Weapon Swap level gate to 70, removed Retort's
  counterattack damage bonus, and unified HP, MP, and rating-node SVG colors
  under a stat-node color distinct from promotions.
- Expanded their 26 promoted and terminal trees to 16-20 and 14-18
  development nodes respectively, added four path-specific passive families
  per class, and gave every generic terminal tree a two-point class-system
  mastery.
- Added terminal meter-cap masteries plus Tethered Instinct's Lycan control
  acceleration and Bonded Bulwark's bond-derived companion scaling.
- Audited every Healer and Pathfinder promotion against its live runtime and
  focused coverage. Corrected the design, tree, promotion-rule, ring, roadmap,
  and playtest documents to distinguish implemented foundations from generated
  rating scaffolds and disconnected mechanics; this audit made no gameplay
  changes.
- Rebaselined Mage as a six-column Elemental/Enhancement/Arcana/Occultism/
  Conjuration/Universal graph with `5/8/8/8` Sorcerer/Spellblade/Warlock/
  Conjurer route costs and registry-affordable stat gates.
- Added six matching elemental Enhancements, Classical Force versus
  Arcane Tradition specialization-aware School Affinity, Polymorph and its
  transparent bunny combat sprite, Inflate Health, all-enemy Blinding Fog,
  Enliven Dead, and the four Conjure spells.
- Rebuilt Spellblade around independent Arcane and Elemental Blade Charge
  pools and evolved Knight Enchanter with two-slot Foundation/Accent weaving.
  Enchanted Assault, Aegis Weave, and Spellbind spend both pools through
  offensive, defensive, and spell-shaping releases.
- Reorganized Knight Enchanter into three connected release lanes and an
  independent universal column. Quick Recharge, Third Eye, and Storage
  Capacity II cost two points; the other 25 development nodes cost one point;
  Storage Capacity II adds two slots to each typed pool, and Quick Recharge
  repeats a weapon-triggered Weave across every hit of a multi-hit attack.
- Added two-point decision pressure to selected tier-3 capstones and advanced
  nodes across Berserker, Crusader, Dragoon, Grandmaster of Arms, Knight
  Enchanter, and Thaumaturgist.
- Expanded Crusader with Censure, Shield Ricochet, Sanctification, and Prayer
  of Faith; standardized its row gates and reordered its spell/healing paths.
- Made inherited middle-path nodes require an unbroken purchased prerequisite
  chain before unlocking successors, and connected Bless into Paladin's Magic
  Defense path.
- Realigned Knight Enchanter's late Assault, Spellbind, and universal nodes to
  the terminal-tree level rows.
- Added eleven timed Detect creature-family spells, with Paladin placements for
  Detect Undead and Detect Fiend and a player choice to fight or avoid revealed
  random encounters.
- Standardized weapon abilities on main-hand attacks unless explicitly marked
  for dual wielding, rebuilt Flurry of Blades as a degrading-accuracy sequence,
  separated Parry damage deflection from Riposte counterattacks, and added the
  Dual Wield Excellence/Mastery accuracy progression.
- Added the five-use Monocane required by Sleeping Powder to Thieves Guild
  stock, creature-type bonuses to Smite II/III, resource-specific SVG node
  colors, and the Fear status icon.
- Expanded Lancer and Dragoon with split polearm Assault/Guard paths, Vigilant
  Landing, Extended Reach, Swing & Bash, Phalanx, Critical Vigor, Dragon Soul,
  and Dragonheart.
- Rebuilt Sentinel around eight Resolve actions and four promotion capstones;
  made Shield Riposte and Spell Reflection passive reactions and replaced the
  overlapping shield actions with Spell Block and Bulwark Guard.
- Rebuilt Stalwart Defender around four disciplines and four immediately
  available full-Resolve Bursts: Citadel Aegis, Ironwall Revenge, Last Bastion,
  and Stronghold. Burst wrappers no longer appear in ordinary Specials.
- Removed redundant numeric Tome buffs from Equipment cards when the same
  value is already presented as the Tome's Spell Mod.
- Moved learned spell/ability modifiers such as Fire Inside out of the base
  description and into a dedicated multi-entry `Modifications` section on the
  affected ability card; modifier nodes remain hidden as standalone Special
  Abilities.
- Made Polymorph deny actions through the shared turn gate, gave bosses a 90%
  resistance chance instead of immunity, and reduced and animated the bunny
  combat presentation with randomized confused pacing.
- Replaced Blade Charge's conditional text-only HUD line with persistent,
  lit/dormant Arcane and Elemental indicators, including visible zero states.
- Accepted NPC names in shop quest text routing so blacksmith, alchemist, and
  jeweler quest offers can open their in-shop dialogue panels.
- Restored shop quests to the shared blocking dialogue presentation so their
  typewriter text appears before confirmation and clears after dismissal.
- Made combat floating damage use structured per-hit damage for attacks,
  weapon skills such as Imbue Weapon, and Magic Missile instead of combining
  separately logged damage into an unmatched HP-loss total.
- Reworked Enfeeble to use a stat-adjusted application chance and a static
  four-turn, 20% Attack/Defense reduction that scales from target ratings.
- Repaired the modern Character screen's Quests action to use the public popup
  package instead of importing a nonexistent nested module.
- Cleared and briefly suppressed buffered movement after dungeon-entry loading
  so transition key presses cannot move the player or trigger combat.
- Expanded the player's Mana Shield visual across the battlefield between the
  combat log and action menu, and added pulsing `MAX` feedback to full Arcane
  and Elemental Blade Charge pools.
- Simplified multi-enemy targeting to a single arrow above the focused enemy;
  removed selection plates, focus boxes, and approximate health-state labels.
- Corrected dungeon relic altars to the Triangulus-through-Infinitas floor
  order and prevented wall sconces from rendering on invalid surfaces or over
  foreground stairs and altar fixtures.
- Upgraded the Rookie Mistake body encounter to two Zombies and made storage
  retrieval quantity prompts default to the entire stored stack.
- Replaced Knight Enchanter Arcane Tempo with the Arcane Duel ring's Weave
  Memory, which preserves a spent Accent as the next Foundation. Third Eye now
  adds Intelligence to critical-hit and weapon/spell dodge calculations.
- Replaced tier-2 Summoner with Conjurer and combined the former Summoner and
  Grand Summoner permanent-roster systems into terminal Thaumaturgist.
  Conjurer now has authored Constructs, Binding, Illusion/Movement, and
  Calling disciplines. Conjurer Callings create location-aware ordinary
  transient companions; the six nodes carry into Thaumaturgist, where each
  Calling instead permanently selects one of two Xenids.
- Rebuilt the Xenid roster as Patagon/Kobalos, Dilong/Cacus,
  Agloolik/Izulu, Hala/Lamashtu, Seraphim/Bardi, and Tiamat/Zahhak. Fuath
  remains the Underground Spring boss, and Grigori was renamed Seraphim.
- Replaced the enemy Conjurer with a Necromancer whose Raise Dead action adds
  a rewardless undead ally to the live multi-enemy turn order.
- Capped Mana Shield physical redirection at 25% per attack and Mana Shield 2
  at 50%, limited Conjure Potion to Health/Mana potions, removed Conjurer's
  Strength promotion gate, and changed Forbidden Studies to `+20%` Shadow
  Bolt damage and `+50%` raised-undead duration.
- Mage transient companions still act independently, use one slot, persist
  for 50 exploration steps, and carry no XP/bond/loot/quest/roster
  progression.
- Expanded the Conjurer graph with Torchlight, an ungated path-only Magic
  node, Sleep, and Nightmare Fuel; shifted the remaining authored rows and the
  Thaumaturgist promotion to preserve the four-discipline layout. Torchlight
  halves random encounters for 50 steps.
- Finalized the revised Conjurer layout: Calling and Constructs swap outer
  lanes, development begins one row below the header, inherited Sleep and
  Mirror Image display as owned, and Explosive Decoy consumes one remaining
  image for a level-55 attack.
- Rebuilt Thaumaturgist as a 29-node, five-column
  Calling/choice/ultimate/conduit/Miracles graph.
  Conjure Animal adds the Hodag/Caladrius pair; the other six Callings retain
  their Conjurer IDs. Xenid conduit now replaces XP leveling, controls stat and
  ability growth, and grants entity-specific caster effects amplified by the
  reworked level-80 Conduit Mastery.
- Removed the obsolete Summon and Summon 2 training passives; living Xenids now
  expose the combat Summon action directly from Thaumaturgist class state.
- Added Reality Fragments as extremely rare reagents and the level-65/70/75/80
  Miracle Blade, Miracle Shackles, Miracle Potion, and Miracle Crystal chain.
  These effects deliberately bypass normal protection, restraint, item
  creation, and mana-generation rules.
- Reworked Raise Summon into a 100-MP combat-only recovery for the just-fallen
  active Xenid. Xenid death removes 25 conduit; raising at 25% HP refunds 10 of
  that loss without reviving the rest of the roster.
- Suppressed redundant carried-ability level gates throughout promoted trees:
  any ability requirement below that class's level-30 or level-60 promotion
  floor now has no runtime check or `Required level` display in that tree.
- Added original transparent combat portraits for Hodag, Caladrius, Tiamat,
  and Lamashtu, plus generated SVG reference diagrams for every class ability
  tree with an automated runtime-drift regression.
- Changed Floating Crystal to siphon 10% maximum MP per caster turn, burst at
  30%, and scale stored-mana damage by spell power. Conjure Animal now selects
  only implemented Animal enemies and prioritizes the current floor.
- Corrected Mage specialization connector routing so both half-column
  specialization nodes receive their prerequisite lines from above through
  their authored midpoint channels.
- Removed Warded Casting, added confirmation for staged choices that
  permanently close abilities, and made all numeric rating/HP/MP nodes
  path-gated without independent level gates. Recorded that future
  class-specific nodes must include a basic class mechanic rather than plain
  stat padding.
- Kept all learned Mage spells through promotion and carried only Arcane
  Fundamentals plus the six elemental-school nodes into the editable Sorcerer
  and Wizard trees, while leaving completed historical tabs read-only.
- Added Aerial Tempo, Landing Shield, Resolve, Spell Block/Reflection, Resolve
  Surges, Oath Conviction, shared Oath techniques, Hallowed Ground, Resist
  Shadow, Blessed Light, Condemnation, Repel the Wicked, Sword & Board, and the
  accompanying battle/frontend integration.
- Preserved externally owned quest, item, boss, Class Ring, Power Core,
  contract, companion, Weapon Discipline, and Jump-modification rewards.
- Fixed inherited gated abilities so they adopt only their matching node and
  added compatibility repair for recursively adopted phantom Paladin nodes.
- Added `docs/PROGRESSION_REFACTOR_CHECKPOINT.md` as the complete implementation
  record and pause boundary before the next fundamental progression redesign.
- Made all three Weapon Master styles mutually exclusive, enforced Mortal
  Strike's two-handed requirement, and made Triple Strike and Flurry of Blades
  replace their learned predecessors.
- Rebalanced first-promotion gates so Druid no longer requires Strength and
  Monk is Dexterity/Wisdom-forward, split the long Monk path, and made Monks
  immune to Disarm through unarmed training.
- Fixed transformed characters opening Progression, added explicit Panther or
  Direbear selection, removed Transform from the Skills submenu, and exposed
  transformed and invisible character states in Pygame.
- Replaced Warlock's bare familiar selector with an artwork-backed descriptive
  popup, added familiar naming, improved familiar identity/ability details,
  and removed meaningless zero-stat presentation.

### Playtest Readiness And Maintenance

- Split the 6,230-line composite effect module into focused common, enemy,
  skill, special, and summon modules while preserving legacy imports through a
  compatibility façade.
- Replaced the 5,822-line item module with a focused `src/core/items/` package
  for base types, weapons, armor, off-hands, accessories, consumables, and
  miscellaneous items while keeping rarity, shop-catalog, ultimate-weapon, and
  legacy APIs in `src.core.items`.
- Replaced the 5,325-line enemy module with a focused `src/core/enemies/`
  package for shared behavior, progression-grouped implementations, encounter
  selection, Bestiary helpers, defeat identity, and constructor-free metadata.
- Optimized random-enemy selection and Bestiary location lookup so only the
  selected enemy is instantiated.
- Replaced the 4,568-line ability module with a focused
  `src/core/abilities/` package for shared types, skills, promotions, power-ups,
  enemy abilities, spells, and progression catalogs, and removed an unreachable
  duplicate `DimMak` definition.
- Replaced the 3,114-line player module with a focused `src/core/player/`
  package that composes state, exploration, presentation, inventory,
  progression, and combat behavior while preserving the public `Player` API
  through an export-only package façade.
- Replaced the 2,704-line map-tile module with a focused
  `src/core/map_tiles/` package for shared rules, paths, interactive tiles,
  boss rooms, event rooms, and endgame tiles.
- Replaced the 2,366-line data-driven ability module with a focused
  `src/core/data/data_driven_abilities/` package for base spells, skills,
  spell families, charging abilities, Magic Missile, Jump, and movement.
- Replaced the 2,252-line character module with a composed
  `src/core/character/` package for models, events, statuses, offense, defense,
  and utility behavior.
- Replaced the 2,243-line promotion-kit module with a focused
  `src/core/classes/promotion_kits/` package for persistent state, combat
  meters, Resolve, class tracks, companion progression, and presentation.
- Replaced the 1,464-line save-system module with a focused
  `src/core/save_system/` package for value objects, item, ability, summon,
  tile, enemy, quest, and player serialization plus filesystem persistence.
- Replaced the 1,518-line ability-loader module with a focused
  `src/core/data/ability_loader/` package for YAML caching, grouped effect
  constructors, ability construction, and example exports.
- Replaced the 1,307-line class ability-mechanics module with a focused
  `src/core/classes/ability_mechanics/` package for equipment, passive,
  companion, exploration, rewind, and summon mechanics.
- Replaced the 1,597-line battle-engine module with a composed
  `src/core/combat/battle_engine/` package for turn flow, action execution,
  outcome processing, and shared result models.
- Replaced seven large frontend modules with focused packages: pygame character
  screens, dungeon and combat managers, combat rendering, dungeon scene
  rendering, popup menus, and curses menus. Stateful screens now compose
  behavior mixins, menu collections are grouped by responsibility, and all
  legacy import paths remain available through export-only façades.
- Removed unused imports across the new frontend implementation modules and
  retained façade-level collaborator hooks used by tests and integrations.
- Cached parsed ability YAML by path and modification time while preserving
  fresh, isolated ability definitions for every caller.
- Kept all package initializers limited to public exports, with regression
  coverage enforcing export-only initializers across the source tree.
- Consolidated packaged game entry points around the supported Pygame
  frontend and moved SciPy from runtime dependencies into the tooling extra.
- Added repeat-safe postgame tavern dialogue for the Barkeep, Waitress, and
  Soldier after `main_story_complete`, shared by both frontends.
- Normalized the Gray Broker portrait to a transparent cutout and repaired
  stale documentation, class-mechanic descriptions, and regression fixtures.

### Design Gate Spec Maps

- Added durable Presentation/Asset, Dungeon/World/Encounter, and
  Equipment/Items/Economy design-gate docs, then converted the matching roadmap
  sections into compact status summaries.
- Moved Class/Ability/Combat, Story/Endgame, and Systems/Audio/Meta gates into
  their existing owner docs while keeping the roadmap as the index of next
  implementation slices.
- Updated documentation indexes so current gate docs are discoverable from the
  project README and docs README.

### Presentation And Asset Gates

- Added `docs/PRESENTATION_ASSET_DESIGN_GATES.md` as the durable spec map for
  presentation, generated bitmap, visual-cue, and screen-polish gates.
- Replaced the plain pygame Character Created popup with a visual summary screen
  and moved New Game intro text into reusable story-card pages.
- Added reusable combat impact cues for reflected damage, hard-control hits,
  and elemental weapon strikes.

### Roadmap Polish And Bugfixes

- Moved the embedded Progression navigation helper into the tree's upper-right
  corner, moved available Progression Points to the upper-left, removed the
  redundant class-tree heading, and kept left/right tree navigation from
  switching Character tabs while tree input is active.
- Tightened the Resolve class-tab layout by removing its redundant panel
  heading and moving its meter and ability sections upward.
- Replaced the debug auto-level max-level blackout message with the standard
  in-context popup.
- Made Hold the Line replace Defend for trained Sentinels and Stalwart
  Defenders, removed it from the Resolve-spend menu, and prevented it from
  refreshing itself or generating Resolve while already active.
- Added a separate Bursts combat menu that appears when an unlocked
  full-bar ability is ready.
- Simplified Resolve ability labels to show their resource cost without
  transient `Need` or `Ready` suffixes.
- Made Dishearten display its Attack-down status in pygame while preserving
  its dedicated percentage-based damage penalty.
- Limited Silence skill suppression to techniques that require MP, leaving
  Resolve spends, Resolve Bursts, and zero-MP techniques usable.
- Kept undiscovered Stalwart Defender Resolve Burst identities hidden until
  their defensive mastery requirement is fulfilled.
- Rendered multi-enemy HP and MP as independent resource labels to avoid
  unsupported separator glyphs in enemy plates.
- Made multi-enemy resource plates opaque so bright dungeon geometry cannot
  resemble a stray character between HP and MP.
- Recorded lethal single-target resolutions before returning the committed
  action, eliminating the dead-but-unresolved frame that hid a sprite before
  its death fade began.
- Added a reusable combat-availability hook for abilities, hid Adrenaline
  until its health condition is met, and added the `CHG` combat-status
  indicator for active player charge-up abilities.
- Combined Deflect Spell and Spell Reflection into Spell Reflection, retaining
  compatible single-target reflection while also raising Magic Defense, with
  compatibility migration for old skills and progression node IDs.
- Corrected Lycan transformation state so Untransform is not offered to
  classes that have not transformed.
- Made race-ineligible and mutually excluded promotion choices render closed,
  and preserved learned Sentinel Resolve abilities through promotion to
  Stalwart Defender.
- Fixed pygame character naming so printable `m` and `f` key presses enter the
  name field instead of being swallowed by sex-selection shortcuts.
- Fixed the stairs-up ceiling-void placement so the missing ceiling tile stays
  above the current stairs rather than the space in front of the player.
- Added tiered minimum floors to health potion healing before percent scaling,
  preserving combat caps while making low-HP pools receive useful healing.
- Added selected equipment artwork to the pygame Equip popup details pane.
- Suppressed unchanged resistance rows in equipment diffs and moved the
  teleport-to-town popup before the return loading screen.
- Cleaned up shop quantity confirmation, keyboard Cancel selection, Equip Now
  prompt wrapping, and the final dungeon-frame flash on return to town.
- Improved minimap readability with outlined special-tile indicators and a
  blinking player-position marker.
- Fixed data-driven stealth-skill regressions so Kidney Punch costs exactly
  18 MP, mana/resource pools cannot underflow, and Backstab only works against
  incapacitated targets.
- Surfaced Footpad Evasive Guard stacks in pygame status icons and Combat Focus,
  and changed undetailed boss Bestiary entries so they no longer suggest Vision
  can reveal boss details.
- Fixed roadmap bugfix queue items for Smoke Screen flee visuals, promoted
  highest-level statistics, long character-screen locations, and status
  consumables missing from pygame shops.
- Improved contained pygame flows for bounty acceptance, incapacitated turn
  indicators, flying enemy placement, minimap adjacent visibility, enemy
  Shapeshift follow-up actions, and dual-wield shop comparison text.
- Fixed additional playtest polish around state-gated skill menu visibility,
  fake-wall wall overlays, non-enterable minimap review tiles, Evasive Guard
  dodge falloff, dead-body dungeon placement, and the Bad Dream Lucky Locket
  turn-in handoff.
- Fixed Demon Claw Doom feedback, PyGame bounty abandonment parity, softer
  quest encounter bias including enemy-drop collection quests, movement log
  coordinate spam, and Thief/Rogue Fortune/Misfortune combat focus behavior.
- Fixed flying target Earth interactions so flying no longer grants blanket
  Earth immunity; only ground-contact spells such as `Tremor`, `Mudslide`, and
  `Earthquake` fail to damage flying targets, while `Sandstorm` and Earth
  elemental damage can still connect.
- Implemented remaining contained roadmap improvements for PyGame death parity,
  Rookie Mistake body drop/recovery, promotion equipment cleanup, menu cursor
  policy coverage, save-preview portraits, Mad Waitress dungeon cue/SFX hooks,
  and the Minotaur approach bone pile; added measurement targets for deferred
  Footpad, drop-rate, multi-strike, and Enfeeble tuning.
- Finished the Mouse Support V1 shared-layer pass for pygame NPC/quest text,
  bounty/content selection lists, read-only item boxes, and reusable popup-menu
  row hover/click/wheel behavior.
- Shipped pygame Shop Polish V1 buy/equip clarity with replacement previews,
  stat/no-stat comparison lines, dual-wield copy guidance, and inventory-safe
  cancel/failure handling.
- Closed Dungeon Quick Wins V1 with regression coverage for one-and-done
  chests, relic-specific discovery text, soft active-quest encounter bias, and
  the persistent pygame low-health dungeon cue.
- Expanded relic discovery text into shared core handling so pygame and
  core/curses relic-room interactions use the same relic-specific copy and
  generic fallback.
- Shipped Enemy Identity Presentation V1 with Sight-gated invisible target
  notes, Mad Waitress form-change readability, and construct-facing `Oil Leak`
  wording while keeping canonical `Bleed` mechanics unchanged.
- Added the remaining-improvement balance baseline wrapper, dry-run summary
  coverage, and ignored timestamped report outputs so Footpad, drop-rate,
  multi-strike, and Enfeeble tuning remain evidence-gated.
- Remade the Quasit combat sprite and added active/inactive Warp Point dungeon
  art with review sheets and fallback-preserving renderer coverage.
- Added saved, progress-gated bounty-board restocks so completed boards refill
  intermittently after enough steps, enemy defeats, or a level gain instead of
  refreshing immediately.
- Fixed empty pygame bounty-board prompts so the “No new bounties” popup redraws
  over the Bounty Board submenu instead of the main tavern menu.
- Fixed Invisible Stalker combat presentation so it does not draw the generic
  fallback body when the player lacks Vision or another sight source.
- Concealed invisible-enemy identity from the battlefield label, combat HUD,
  and player-facing combat log until Sight reveals it, using `Unseen force`
  rather than leaking the canonical enemy name.
- Fixed failed multi-enemy encounter retries so restored members also discard
  stale death-animation state and render normally on re-entry.
- Replaced the unsupported multi-enemy focus glyph with a procedural target
  marker and added elemental ability icons to School Affinity rows.
- Gated Paladin's Resist Shadow behind Heal and the preceding MP node, then
  made it the prerequisite for Sworn Purpose so the Grace path must be
  purchased in order.
- Registered the three Pilot 2 screening pairs as development-only forced
  encounters for automated and manual validation, without changing normal
  random encounter generation.
- Completed Pilot 2 automated screening: Twisted Dwarf & Xorn passed after
  encounter-local tuning, while Zombie & Quasit and Battle Toad & Satyr remain
  development-only and blocked on excessive duration.
- Clarified Pilot 2 manual evidence as six total battles (two per pair) with
  explicit targeting, presentation, cleanup, reward, and duration checks.
- Closed Multi-Enemy Pilot 2 after seven successful manual battles, including
  dedicated Hallowed Ground and `ALL_ENEMIES` coverage, and identified
  deeper-floor curated encounters as the next validation phase.
- Added three development-only deeper-floor pair candidates across floors 3
  and 4, extended pair tuning to promoted-class matrices, and documented the
  separate floor-5 class-tier and enemy-area-action gate.
- Completed Pilot 3 automated screening: Ghoul & Golden Eagle passed every
  aggregate band, while Night Hag & Pit Viper and Antlion & Troll remained
  stable but blocked on duration and other balance metrics.
- Matched paired-enemy presentation to singleton combat scaling for ordinary
  enemies and grounded non-flying sprites at the battlefield floor.
- Labeled the upgraded base-Healer progression node as Heal II so it is
  distinguishable from the initial Heal purchase.
- Extended the pair-tuning tool with focused member selection and corrected
  no-pass ranking so bounded grids retain the lowest-score fallback.
- Added compact combat indicators for Vision/sight and Weapon Art states such
  as Reaver's Mark, Brace, and Riposte Line.
- Improved Weapon Discipline presentation with required-weapon text in Weapon
  Art descriptions, selectable/clickable discipline rows, detail popups, and
  cleaner class-tab rows that no longer duplicate art names under weapon types.
- Expanded pygame promotion-preview mechanic tabs for Pathfinder branches so
  Diviner, Shaman, and Ranger previews announce their Runes, Totems, and
  Companion class tabs.
- Wired Warrior-line promotion mechanic tabs so Paladin/Crusader, Lancer/Dragoon,
  and Sentinel/Stalwart Defender previews and Character Menu tabs announce Oath
  Conviction, Aerial Tempo, and Resolve.
- Replaced the pygame Paladin vow picker with a styled selection popup that
  previews each vow's signature skill, aura, mark, and broad playstyle identity
  before a terse final oath confirmation without exposing tuning details.
- Moved pygame Lancer/Dragoon Jump Mods management inline into the `Aerial
  Tempo` Character Menu tab, expanded `Oath Conviction` vow details, and rebuilt
  Sentinel/Stalwart `Resolve` around a large red meter with ability boxes.
- Added Sentinel/Stalwart `Resolve` class-tab spend and Surge listings and
  captured future Paladin vow drift/oathless recovery as a design gate instead
  of loose roadmap notes.
- Rendered Sentinel/Stalwart `Resolve` in Combat Focus as a red value bar and
  kept active Defend from displaying as a Defense-down combat status icon.
- Implemented the Sentinel/Stalwart Resolve direction so Sentinel owns normal
  Resolve spending, Stalwart Defender inherits those shield actions, and
  Stalwart adds full-bar `Resolve Surges`.
- Split Sentinel/Stalwart Resolve actions into their own pygame combat menu
  with Resolve-cost labels; the later redesign retired Shield Check in favor
  of the eight-action Resolve set.
- Wired Mage-tree promotion mechanic tabs so Sorcerer/Wizard, Warlock,
  Shadowcaster, Demonologist, Spellblade/Knight Enchanter, and Summoner
  previews and Character Menu tabs announce School Affinity, Familiar,
  Umbral Debt, Contracts, Blade Charge, Arcane Tempo, and Summons.
- Wired Footpad-tree promotion mechanic tabs so Thief/Rogue, Inquisitor/Seeker,
  Assassin/Ninja, and Spell Stealer/Arcane Trickster previews and Character
  Menu tabs announce Fortune, Case Journal, Death Mark, and Stolen Charge.
- Wired Healer-tree promotion mechanic tabs so Cleric/Templar, Monk/Master
  Monk, Priest/Archbishop, and Bard/Troubadour previews and Character Menu tabs
  announce Devotion, Ki, Prayer, and Crescendo.

### Promotion Class Kits

- Added the initial promotion class-kit foundation, including shared state and
  hooks, combat-only meters, persistent track state, representative
  active/passive abilities, class-ring identity updates, and save/load
  normalization. The 2026-09-02 lineage audits supersede the earlier V1
  completion claim for any mechanic without a full production path.
- Added representative coverage for promotion-kit state, selected actives,
  Demonologist corruption/patron mood, Shadowcaster Eclipse, summon and
  companion bond state, Footpad-track meters, direct Lycan control helpers,
  and ring display compatibility. Helper coverage alone is not evidence that
  every advertised setup, spend, payoff, or progression loop is integrated.
- Added the Master Monk-only `Ruyi Jingu Bang` ultimate staff, class-specific
  ultimate-staff selection, and curses/pygame blacksmith coverage for the
  `Unobtainium` crafting flow.
- Expanded Weapon Master/Berserker/Grandmaster Weapon Discipline into a
  player-facing progression loop with weapon-type ranks, active Weapon Arts,
  whole-XP insight rolls, INT-scaled insight chance, enemy-promotion difficulty
  gating, combat/victory/rank-up messaging, and pygame Character Menu progress
  bars with weapon icons and equipped highlighting.
- Redesigned the pygame promotion preview to show class transitions,
  promotion stat deltas, and post-promotion Character Menu mechanic tabs;
  pygame promotion now applies class stat/resource/combat bonuses, increases
  current HP/MP alongside max HP/MP bonuses, and shows one concise
  congratulations popup without extra tutorial popups.
- Tuned Weapon Master and Grandmaster of Arms promotion stat bonuses to include
  `+1 INT`, reinforcing Intelligence as martial study and Weapon Discipline
  insight rather than only spellcasting.
- Completed additional promotion-kit smoothing hooks for `Loaded Dice`,
  `Ordered Blessings`, `Divine Intervention`, `Encore`, and bond-scaling
  `Shared Recovery`, including representative Rogue Fortune/Misfortune payoff,
  `Cheat Death`, and Bard/Troubadour Crescendo coda coverage.
- Updated class-kit, class-ring, roadmap, and docs-index references for the
  initial V1 baseline. Later lineage audits reopened incomplete ability riders,
  action boundaries, class-specific payoffs, and orphaned helpers as
  implementation work rather than balance or presentation polish.

### P7 Additional Improvements

- Added mouse hover/click support for selector-style pygame screens: main menu,
  town menu, shop selection, generic location menus, race/class selection,
  Character Menu tabs/actions, and equipment paper-doll slots.
- Improved Equipment tab selected-slot visibility with a fixed-size high-contrast
  highlight that does not resize or shift the paper-doll layout.
- Added live dungeon HUD location labels for Town, ordinary dungeon levels,
  Realm of Cambion, and Liminal Gap.
- Added an enlarged dungeon minimap modal opened with `M` or by clicking the
  existing minimap; it reuses current minimap discovery/reveal rules and closes
  with `M`, `Esc`, or outside click.
- Added an optional first-person-style `Explore Town` prototype that navigates a
  small Silvana node graph and routes interactions back through the existing
  Barracks, Shops, Tavern, Church, Old Warehouse, Warp Point, and dungeon-entry
  flows.
- Revised the `Explore Town` prototype from a menu-like selector into a
  directional town walk: arrow keys/WASD move between venues and Enter/Space
  interacts with the current venue.
- Updated the enlarged dungeon minimap modal to frame all currently revealed
  tiles on the active level instead of enlarging only the local HUD viewport.
- Added numbered portrait-atlas variant support for character creation. The
  creation screen starts on a random portrait variant, lets players browse with
  arrows/clickable portrait buttons, and persists the chosen variant for later
  Character Menu and player-token rendering.
- Hardened save loading so missing core equipment slots are backfilled with
  empty equipment, preventing legacy or synthetic saves without `OffHand` from
  crashing Character Menu resistance calculations.
- Replaced the base racial portrait source with per-race portrait sheets,
  providing five male and five female selectable base portraits per race.
- Folded sex selection into the character naming screen so character creation
  skips the old standalone sex page; Male/Female buttons below the portrait now
  switch the race-specific portrait set before confirmation.
- Extended mouse support to load-game save rows, promotion choices, the
  level-up stat picker, the main combat action grid, and core in-combat
  item/spell/skill/totem picker panels.
- Replaced the dungeon special-tile artwork for stairs up, stairs down, and the
  secret shop with new painterly RGBA sprites matched to the current dungeon
  wall/floor/ceiling treatment.
- Added generated companion/familiar artwork for Homunculus, Fairy, Mephit, and
  Jinkin, plus a companion art manager that uses those assets first and falls
  back to existing enemy sprites for tamed beasts and summons.
- Added bespoke transparent companion-art sprites for all 11 summon creatures
  and a summon companion-art review sheet; summon mappings now resolve to those
  assets before enemy fallback lookup.
- Moved companion/summon artwork out of Class tab tiles and into a
  Character-tab-style companion details popup with identity, attributes, combat
  stats, abilities, weaknesses, and resistances.
- Changed the Class tab companion/summon overview from a square grid to stacked
  full-width rows that fit the complete 11-summon roster.
- Moved active-summon HP, MP, level, and XP presentation into the pygame Combat
  Focus panel.
- Added active-summon `Support`, level-span-based summon bond rolls, explicit
  summon starting combat stats, Dilong `Surface`, Class-tab summon selection via
  `C`, Combat Focus summon-bond cleanup, and faster pygame combat entry pacing;
  `C` no longer jumps to the Class tab from other Character Menu tabs.
- Removed passive `Class` and known-`Summons` summary rows from pygame Combat
  Focus; the panel now shows active focus content, active summon resources, or a
  quiet no-focus message.
- Changed dungeon special-location text in pygame from a scrolling combat/log
  line into a popup message so one-off location events remain visible.
- Fixed Dragon Breath damage so it routes through Mana Shield before applying
  elemental reduction and HP loss.
- Kept summon level-up combat stat gains as integers so details popups no
  longer show fractional Attack/Defense/Magic/Magic Defense values.
- Cached bestiary location/drop hint rows inside the pygame Bestiary popup to
  reduce repeated redraw work while browsing enemy entries.
- Fixed the pygame equipment replacement popup so slot selection no longer
  flashes the full equipment-slot list before the filtered replacement list.
- Added summon calling costs, including MP for summon creatures and an
  additional gold fee for Kobalos.
- Added active-summon combat log coloring, active summon status icons in Combat
  Focus, boss-victory guaranteed/doubled summon bond gain, and a Dilong starting
  Attack bump for better low/mid-level hit payoff.
- Removed the deferred `Explore Town` prototype entry from the normal town menu
  while keeping the direct prototype launcher available for later work.
- Reworked the stairs-down dungeon tile as a floor-bound stairwell overlay
  instead of a wall-filling shaft, with renderer placement that sits it on the
  projected floor tile and sizes it from floor-slot width rather than shallow
  floor-slot height, plus a flatter, tapered perspective so it reads as
  descending into the floor without rising up the back wall.
- Shortened and darkened the stairs-up dungeon tile so the arch sits lower and
  the stone color better matches the surrounding dungeon walls.
- Reworked the stairs-up tile experiment to remove the custom dark upper
  opening, lower the top of the visible staircase below the ceiling plane, and
  color-match the stone more closely to the stairs-down tile while preserving
  normal wall/ceiling rendering.
- Adjusted center stairs-up rendering so the visible staircase spans from the
  floor edge into the ceiling opening at its projected depth, with a wider
  centered target, upward darkening gradient, and a generated `ceiling_void`
  slot that removes the center ceiling tile while leaving void visible above
  the stair top.
- Expanded pygame mouse support across reusable presenter menus and shared popup
  flows, including list/grid/split menus, confirmations, choice lists, reward
  selection, quantity selection, and code entry.
- Added mouse hover/click support for remaining named combat pickers: Runic
  Boost, Steal As Well, and Demonologist Ask Fiend contract intent selection.
- Wired companion/familiar artwork into the Character Menu combat-stats panel,
  preferring the active familiar and falling back to the first living summon
  without changing companion mechanics or save data.

### Roadmap Completion Consolidation

This entry consolidates completed roadmap work from `docs/DEVELOPMENT_ROADMAP.md`
and completed roadmap-sidecar notes, including the retired
`docs/P3_EFFECTS_AUDIT.md`. The active roadmap now tracks only current,
deferred, or decision-gated work.

#### P0 - Current Playtest Regressions And Trust
- Fixed the first-key combat input regression by pumping pygame events before
  guarded physical-key reads.
- Re-ran focused playtest coverage for main-menu/dungeon music transitions,
  Character Menu Attack/Defense display, Enfeeble zero-value reporting,
  Half Giant early balance, Old Key prompts, audio diagnostics, and
  location/combat music routing.
- Recorded the P0 verification pass in roadmap and playtest docs.

#### P1 - Pygame UX Polish
- Completed the modern Character Menu acceptance pass: tabbed character and
  equipment views, portrait/identity presentation, wider stat panels,
  resistance/weakness grouping, paper-doll equipment layout, Helmet support,
  dual-wield Attack display, selected-item artwork, item detail popups, and
  town/dungeon default routing.
- Replaced shop sub-type selection with tabbed buy-list browsing for town shops
  and secret-shop grouped categories.
- Added combat visual polish: procedural hit/spell/skill overlays, floating
  damage/healing text, enemy recoil, low-HP danger vignette, compact bottom
  command panels, paged wrapped combat logs, compact enemy telegraph warnings,
  boss-detail suppression, and improved Defend presentation.
- Replaced the basic pygame naming prompt with a visual naming screen showing
  portrait, sex, race, and class.
- Reworked enemy presentation around approved transparent combat sprites,
  compact tokens, per-enemy scale data, target-panel rendering, and boss
  navigation figures.
- Completed large selected-item artwork coverage for regular, key, and special
  inventory presentation contexts.
- Completed the dungeon rendering art pass: manifest-driven texture loading,
  painterly projected dungeon textures, decorative tile hooks, deterministic
  torch/sconce overlays, richer Tiled JSON layer handling, chunked/infinite map
  support, funhouse boundary-wall rendering, and authoring-tile stability.

#### P2 - Renderer And Exploration Presentation
- Preserved and expanded structural-depth renderer coverage for center walls,
  side corridors, floor/ceiling/wall slot routing, side doors, Ore Vault door
  states, defeated-boss visuals, springs, chests, and side-special placement.
- Added floor-bound presentation for Rotator and active FunhouseTeleporter
  tiles.
- Added visited-only FakeWall/Fake Path translucent wall presentation without
  revealing hidden fake walls.
- Smoothed the pygame load progress popup with time-based interpolation while
  preserving the existing load flow and test hooks.

#### P3 - Core Refactoring And Test Confidence
- Completed the effects audit previously tracked in `docs/P3_EFFECTS_AUDIT.md`.
- Updated stale primitive effect contracts, including `DamageEffect`,
  `HealEffect`, result bucket writes, and type-only imports.
- Added result-shape and lifecycle coverage for data-driven spells, weapon
  skills, legacy `Spell`/`Skill` instances, passive placeholder power-ups, and
  all built-in YAML ability files.
- Aligned Stun, Silence, Poison, burn DOT, Bleed, Regen, Mana Shield,
  Crusader shield, reflected spell, Fire/Ice legacy-vs-YAML, healing, Smite,
  Sleep/Prone, enemy priority, enemy item, random enemy override, forced enemy
  debug, quest completion, class progression, loot helper, enemy catalog, and
  character defense contracts with current runtime behavior.
- Added targeted typed signatures/docstrings around player quests, class
  promotion rules, legacy ability entry points, item use overrides,
  data-driven spell wrappers, enemy helpers, loot helpers, and core character
  state aliases.
- Audited explicit `pytest.mark.skip` / `xfail` usage in the focused test tree
  and found no remaining P3 blockers.
- Deferred final passive Power Up gameplay effects, item TODOs, content
  expansion placeholders, and future helper extraction to later evidence-backed
  specs.

#### P4 - Content And Systems Expansion
- Completed P4a immediate content and UX polish: town/tavern/Sergeant/Warp
  Point hints, equipment hand details, inventory sort persistence, combat-log
  color improvements, Smoke Screen tuning and visuals, status icon artwork,
  load popup lifecycle fixes, Vision suppression for bosses/Waitress, enemy
  HP/MP labels when details are visible, and limited ability-specific visuals.
- Completed P4b quest and realm scope: Rookie Mistake polish, Realm of Cambion
  portal/rotator/anti-magic/Merzhin flow, Cambion flavor and reactions, town
  presentation hooks, Bring Him Home follow-up, Dragoon dragon route, class
  ring activation systems, legacy class-kit hooks, Vesperion/Voluntas plot
  direction, Liminal Gap hub and Guardian trial shells, clue aggregation,
  Seventh Seat/Voluntas/Acolyte/Reflection route, true-final re-entry,
  Guardian counters, true-final victory resolution, ending, and tavern
  epilogue.
- Completed P4c Bestiary scope: per-save seen/defeated/detailed records,
  Character Menu Bestiary UI, detail visibility rules, stable practical enemy
  details, completion counts, coarse encounter locations, and broad drop
  labels.
- Completed P4d lightweight equipment foundation: shared slot/eligibility
  helpers, buy-to-equip flows for pygame and curses shops, multi-copy/dual-wield
  handling, current item foundation validation, and stat-themed display-name
  confirmation.
- Completed P4e class-mechanics foundation: Grandmaster disciplines, Demonologist
  contracts, Archdruid attunement, legacy Class Ring awakening flows, Paladin
  vows and Crusader affirmation, Dragoon dragon quest route, Astromancer rune
  foundation, Shaman/Soulcatcher Totem foundation, and related save/UI/test
  coverage.
- Completed P4f combat architecture and balance design-gate slice. No gameplay rules
  changed in that slice; future combat and tuning changes are gated by
  `docs/COMBAT_BALANCE_DESIGN_GATES.md`.

#### P5 - Audio Content Completion
- Completed the non-asset audio-routing and event-payload readiness slice:
  weapon/action metadata, `laser_beam.wav`, `bird_attack_sound.wav`, scroll cast
  routing, and potion/elixir recovery cues.
- Deferred final SFX and music replacement to the later asset-content pass.

#### P6 - Expand Enemies, Items, And Abilities
- Added `Giant` and `Owlbear` to the level 3/4 encounter catalog.
- Added `Helm of Rostam`, reshuffled the medium helmet progression, retained
  `Visored Sallet` for legacy compatibility, and added reagent items `Acorn`,
  `Vine Seed`, `Fungus Spore`, and `Hemlock Root`.
- Added approved combat/item artwork and sprite/icon/render mappings for the
  new enemies, helmet, and reagents.
- Added passive entries and first-pass hooks for `Zephyrstrike`, `Retaliate`,
  `Defensive Regen`, `Posturing`, `Third Eye`, and `Pious Bounty`.
- Added Druid/Archdruid nature spells and straightforward data-driven spell
  entries for poison, lightning, stone, wind, growth, nature shield, and haste
  effects.
- Completed the current ability mechanics slice: Berserker and Dragoon martial
  abilities, Stalwart Defender and Monk/Master Monk strikes, Ranger `Tame` and
  `Favored Enemy`, Spell Stealer/Arcane Trickster theft follow-ups,
  Archdruid reagent/Growth abilities, Astromancer time spells,
  Seeker/Wizard movement and illusion spells, summon support, elemental
  resistance spells, advanced one-use sheet music, dark spells, enemy-only
  `Bad Breath`, and current second-promotion power-up hooks.

#### Resolved Roadmap Archive Cleanup
- Consolidated recent completed UI improvements that were previously parked in
  the roadmap archive: combat HUD class-focus panel, Totem combat presentation,
  additional PNG status icons, equipment resistance previews, Bestiary detail
  reveal and completion summaries, compact charge telegraphs, danger vignette,
  enlarged/re-anchored minimap, Alchemist/Jeweler tabbed buy flows, enemy combat
  sprite warmup, Old Key reward tuning, staged SFX routing, dungeon music
  aliasing, location/context music routing, and long shop-list paging.
- Consolidated recent completed bug fixes that were previously parked in the
  roadmap archive: torch/sconce overlay restoration, resistance preview context,
  Magic Pendant buff reporting, Bestiary lazy detail loading and Mimic artwork,
  Mirror Image duplicate interception, Mana Shield nonpositive-damage handling,
  Slot Machine logging, Regen Dispel, combat post-turn log flushing, combat-log
  wrapping cache, side-opening decorative prop grounding, Hex log coloring,
  action-menu refresh after Silence expiry, charged-skill resolution through
  Silence, Health Potion combat heal caps, Jester AI/storage/event ordering,
  Slot Machine DOT metadata/icons, generic DOT icons, Lick status filtering,
  town-return background cleanup, stale music cleanup, first-key guarded input,
  Jump forced-action cleanup, Berserk/Jump ordering, duration-1 incapacitation,
  equipment submenu input guards, unstoppable Jump behavior, side-door textures,
  two-handed shield unequip, initiative-hidden turn indicator, side-view chest
  orientation, charge log wrapping, enemy sprite fallback paths, Character Menu
  stat display, and zero-value Enfeeble filtering.

#### Consolidated Commit Messages
- `b086723` - Fix guarded input first-key handling
- `6194924` - Document completed P0 verification
- `51bba63` - Complete pygame character and item presentation pass
- `d46ceba` - Implement helmet equipment and standard character screen
- `e486c9a` - Complete combat polish pass
- `a08425e` - Finalize P1 dungeon rendering art
- `6d16c17` - Advance P2 renderer presentation polish
- `66fa9f1` - Close P2 renderer presentation pass
- `1bf7414` - Start P3 effects primitive cleanup
- `3f3af3a` - Add P3 ability result contracts
- `477d65d` - Expand P3 ability catalog coverage
- `6483f1e` - Cover status tick ordering
- `fc31792` - Share mana shield defense handling
- `18967e3` - Share instant heal application helper
- `348d681` - Close P3 roadmap work
- `a77fce6` - Organize P4 roadmap tracks
- `61180bc` - Complete P4a and polish Rookie Mistake
- `3d1895b` - Audit Realm of Cambion flow
- `08898aa` - Add P4b town presentation hooks
- `96edc4f` - Add Bring Him Home follow-up scene
- `22ff50e` - Add Bestiary MVP
- `424d33c` - Document Forsaken Tenet story direction
- `5778ea0` - Implement class ring activation systems
- `cb943c4` - Implement Paladin vows and Crusader ring affirmation
- `e20d843` - Implement Dragoon dragon quest route
- `3b36188` - Implement legacy class ring kits
- `8e8d1cf` - Close P4b quest and finale route
- `bcd17fd` - Close P4c bestiary scope
- `1f0172d` - Add P4d equipment foundation
- `f886726` - Implement P4e class mechanic foundations
- `7184a61` - Clean up roadmap and class kit docs
- `bd6f4d5` - Add P4f combat balance spec
- `3eaedf5` - Complete P5 non-asset audio routing
- `1487b5e` - Complete P6 content and ability mechanics

### Changed

#### Item Artwork Organization
- Organized large selected-item artwork into category subdirectories under `src/ui_pygame/assets/item_art/`.
- Replaced the old flat item-art render keys with nested `item_render_map.json` entries and kept optional legacy atlas fallback support.
- Preserved the Chalice Map split: selected-item art uses `item_art/special/story/chalice_map.png`, while the dungeon/location reveal uses `assets/key_items/chalice_map.png`.

#### Pygame Renderer and Combat UI Polish
- Improved combat status icon readability with urgent-effect prioritization, duplicate compaction, counted labels, Maelstrom Weapon stack visibility, stronger alert coloring, and shared helper behavior across the main combat view and dungeon-combat HUD.
- Tightened combat telegraph presentation with warning-colored wrapped log lines, a dedicated banner that tracks the full latest telegraph message, and clearing behavior after non-telegraph follow-up messages.
- Fit long combat selection labels and turn-indicator subtitles by rendered width so dense item/spell/skill names and long player/enemy names stay inside their UI surfaces.
- Hardened stale-input handling across Pygame popups and navigation loops, including town menus, class/race/load/shop selection, shared popup menus, dungeon escape/loot/key-use prompts, combat action/submenu selectors, shop screens, and the character screen.
- Expanded dungeon renderer smoke coverage around side-corridor walls, open/closed and hidden Ore Vault doors, side-door state preservation, depth-3 outer floor/ceiling slot routing, and left/right floor-special placement parity.

### Documentation
- Updated `docs/DEVELOPMENT_ROADMAP.md` with the completed Pygame polish items and current follow-up notes.

## [2.1.0] - 2026-02-22

### Added

#### Sound System (2026-02-22) 🔊
- **Complete sound manager with event-driven audio**
  - SoundManager class with pygame.mixer integration
  - Automatic pygame.mixer initialization (44.1kHz, 16-bit, stereo)
  - 16 simultaneous sound channels
  - Sound effect caching for performance
  - Graceful handling of missing audio files

- **Event-driven sound effects**
  - Combat sounds: hit, heavy_hit, critical_hit, victory, defeat, flee
  - Spell sounds: cast, fire, ice, lightning, heal, buff, debuff
  - Status effects: poison, stun, burn
  - Character events: heal, level_up, player_death, enemy_death
  - UI sounds: menu_select, menu_confirm, menu_cancel

- **Background music support**
  - Looping music with fade in/out transitions
  - Separate music directory structure
  - Designed for location-based and combat music

- **Volume controls**
  - Independent master, SFX, and music volume
  - Enable/disable sound system
  - Volume ranges from 0.0 to 1.0

- **Development tools**
  - `tools/generate_placeholder_sounds.py` - Creates simple beep sounds for testing
  - Generates 30+ sound effects as sine wave tones
  - Requires numpy and scipy for tone generation

- **Documentation**
  - `docs/SOUND_SYSTEM.md` - Comprehensive sound system guide
  - `assets/sounds/README.md` - Sound effects catalog
  - `assets/music/README.md` - Music tracks guide

#### Map and Sprite Tooling (2026-02-22)
- **Enemy sprites**: 42 new 32x32 enemy sprites for pygame UI
- **Tiled integration tools**
  - `tools/generate_tiled_tileset.py` - Creates Tiled .tsx tilesets
  - `tools/convert_maps_to_tiled_json.py` - Converts text maps to Tiled JSON
  - `tools/sprite_sheet_extractor.py` - Extracts sprites from sheets
  - `tools/sprite_merger.py` - Combines sprites into composite images

## [2.0.0] - 2026-01-28

### Major Reorganization - Code Structure Overhaul ✅

#### Codebase Reorganization
**Complete restructuring into modular architecture**:
- **src/core/** - All game logic modules (UI-agnostic)
  - Moved: abilities.py, battle.py, character.py, classes.py, combat_result.py
  - Moved: companions.py, enemies.py, items.py, map_tiles.py, player.py
  - Moved: races.py, save_system.py, town.py, tutorial.py
  - Kept: combat/ and events/ subdirectories

- **src/ui_curses/** - Terminal UI implementation
  - Moved: game.py, menus.py, town.py from root
  - Clean separation from game logic

- **src/ui_pygame/** - GUI implementation (Pygame)
  - Organized: gui/ directory with all pygame components
  - Created: presentation/pygame_presenter.py for event-driven UI

- **_old_code_archive/** - Archived original files
  - Git-ignored for safety during reorganization
  - Original file structure preserved

#### Import System Overhaul
**Fixed 20+ import errors across reorganized codebase**:
- **Core Modules**: Updated all imports to use relative imports (`from . import`, `from .. import`)
- **UI Modules**: Fixed cross-boundary imports (`from ..core import`, `from ...core import`)
- **Pygame GUI**: Corrected all relative import paths in gui/ subdirectories
- **Module-Level Imports**: Moved all local function imports to module level
- **Circular Dependencies**: Resolved with proper import structure

**Files Fixed** (20+ files):
- src/core/abilities.py (8 import fixes + 3 bugfixes for missing code)
- src/core/town.py (added enemies import)
- src/core/player.py (removed invalid utils import, fixed Mimic instantiation)
- src/core/classes.py (removed try/except fallbacks, added module imports)
- src/core/save_system.py (added enemies import, fixed indentation)
- src/ui_curses/town.py (added enemies import)
- src/ui_pygame/gui/combat_manager.py (fixed TYPE_CHECKING imports)
- src/ui_pygame/gui/enhanced_dungeon_renderer.py (added DIRECTIONS import)
- src/ui_pygame/gui/popup_menus.py (added module-level items import)
- And 10+ more files with import corrections

#### Code Quality Improvements
- **Syntax Errors Fixed**: 3 syntax errors from incomplete edits (abilities.py, save_system.py)
- **Indentation Fixed**: Corrected indentation errors in save_system.py
- **Missing Code Restored**: Added missing popup/result assignments in abilities.py
- **Dead Code Removed**: Eliminated unreachable pygame code in curses menus.py

#### Verification
- ✅ **Both UIs Working**: Terminal (curses) and GUI (pygame) both import successfully
- ✅ **Zero Import Errors**: Comprehensive grep search confirms no bad imports remain
- ✅ **All Tests Passing**: Import verification test passes for all critical modules
- ✅ **Entry Points Functional**: Both game_curses.py and game_pygame.py launch correctly

#### Developer Experience
- **Clearer Structure**: Logical separation of concerns (core vs UI)
- **Easier Navigation**: Files organized by purpose
- **Better Imports**: Consistent relative import patterns
- **Future-Proof**: Ready for additional UI implementations (web, mobile)

---

## [Phase 3 Started] - 2025-12-14

### Phase 3 Started - GUI Development with Pygame 🎮

#### Pygame Integration
- **Pygame 2.6.1 Installed**: Modern 2D graphics library for Python
- **PygamePresenter**: Complete presenter implementation with event subscriptions
- **Combat UI**: Character sprites, health/mana bars, status effects, turn display

#### Visual Features
- **Floating Damage Numbers**: Animated text showing damage/healing with color-coded types
- **Screen Shake**: Dynamic camera shake for critical hits and big damage
- **Combat Log**: Scrolling text log at bottom of screen
- **Telegraph Display**: Warning messages for charging abilities (Seeker/Inquisitor)
- **Status Icons**: Visual indicators for active status effects

#### Event Integration
- **COMBAT_START/END**: Initialize combat UI, display victory/defeat
- **DAMAGE_DEALT**: Create floating damage text with type-specific colors
- **HEALING_DONE**: Green floating text for healing
- **CRITICAL_HIT**: Enhanced visual feedback with extra screen shake
- **STATUS_APPLIED**: Add status to character display
- **TURN_START**: Update turn counter

#### Damage Type Colors
- Physical (White), Fire (Red), Ice (Light Blue), Lightning (Yellow)
- Poison (Green), Holy (Gold), Shadow/Arcane (Purple), Drain (Dark Red)

#### Next Steps
- Create sprite assets for characters and enemies
- Add spell effect animations
- Implement particle systems
- Create main menu and game over screens
- Add sound effects and music

---

### Phase 2 Complete - Enhanced Combat System ✅

#### Major Features Added
- **Action Queue System**: Turn-based combat with priority system (IMMEDIATE, HIGH, NORMAL, LOW, DELAYED)
- **Charging Abilities**: 18 abilities with charge times and telegraph messages for tactical gameplay
- **Event System**: 38 status effect events + combat events (damage, healing, dodge, block, critical hit)
- **YAML Ability System**: Externalized ability definitions for easier balance and modding

#### Combat Enhancements
- **Telegraph Messages**: Seeker/Inquisitor classes get foresight warnings about charging enemy abilities
- **Enhanced Battle Manager**: Full action queue integration with 117 enemy ability stacks
- **Status Effect Events**: All 38 status effects emit events with proper duration/source tracking
- **Damage/Healing Events**: Combat actions emit events for future GUI animations

#### Critical Fixes

##### Weapon Special Effects Re-enabled (Dec 14, 2025)
**Issue**: All weapon and armor special effects were disabled during CombatResultGroup API refactor
- 43 special effect methods completely non-functional
- Life steal, instant death, elemental damage, stun effects broken
- Leer/Gaze petrification attacks not working
- Armor thorns/reflection inactive

**Resolution**:
- **character.py** (lines 325-335, 508-540): Re-enabled special_effect calls with CombatResultGroup integration
- **combat_result.py** (lines 50-62): Made CombatResultGroup subscriptable (added `__getitem__`, `__len__`)
- **items.py** (line 1657): Fixed Gaze weapon missing result assignment
- **tests/test_weapon_special_effects.py**: Created comprehensive test suite (5/5 passing)

**Impact**: All weapon/armor special effects now operational - life steal, instant death, stun, elemental damage, petrification, thorns/reflection all working.

#### Project Configuration
- **pyproject.toml**: Modern Python packaging with PEP 621 standard
  - Dependencies: numpy, pyyaml
  - Dev dependencies: pytest, pytest-cov
  - GUI dependencies: pygame (for Phase 3)
  - Tool configs: pytest, black, mypy, isort, coverage
  - Entry point: `dungeon-crawl` command

#### YAML Ability Files Created (18 total)
**2-turn charge abilities**:
- meteor.yaml, dragon_breath.yaml, detonate.yaml

**1-turn charge abilities**:
- jump.yaml, charge.yaml, true_strike.yaml, true_piercing_strike.yaml
- ultima.yaml, disintegrate.yaml, dim_mak.yaml, arcane_blast.yaml
- shadow_strike.yaml, crushing_blow.yaml
- blessing.yaml, fireball.yaml

**Features**:
- Telegraph messages for foresight mechanics
- Special mechanics: prone_while_charging, unblockable, guaranteed_hit, ignore_defense
- Future: Cooldown system documented for Phase 3 implementation

#### Code Quality
- Removed unused imports (abilities.py - 4 effect imports)
- Fixed module conflicts (combat.py → battle.py)
- Added type hints with `from __future__ import annotations`
- Fixed mutable default arguments in dataclasses

#### Documentation
- **docs/PHASE_2.md**: Complete Phase 2 status and features
- **docs/ARCHITECTURE.md**: System architecture and design decisions
- **docs/PRE_PHASE_3_CLEANUP.md**: Pre-Phase 3 analysis and recommendations
- **data/abilities/README.md**: YAML ability system documentation
- **tests/**: Integration tests (6/6 passing), weapon special effects tests (5/5 passing)

#### Testing
- ✅ All modules import cleanly
- ✅ Enhanced combat manager integration (117/117 enemy stacks)
- ✅ Event system (38/38 status events + combat events)
- ✅ Weapon special effects (5/5 test suite passing)
- ✅ Action queue system functional
- ✅ YAML ability loader working

### Phase 3 Readiness 🟢

**Status**: Ready to proceed with GUI development

**What's Complete**:
- ✅ Event system for animations (38 status + 6 combat event types)
- ✅ Action queue for turn order display
- ✅ Combat mechanics fully functional
- ✅ Presentation interface ready for Pygame implementation
- ✅ Telegraph messages for UI display
- ✅ All special effects working

**Next Steps**:
1. Install Pygame: `pip install -e '.[gui]'`
2. Implement Pygame presenter in `presentation/pygame_presenter.py`
3. Create combat UI: sprites, health/mana bars, status icons
4. Add animations using event system
5. Implement telegraph message UI for Seeker/Inquisitor foresight

### Deferred to Phase 4+
- **Architecture Restructuring**: Current structure is functional, defer until after GUI stable
- **Companion Ultimate Attacks**: 9 missing (Carbuncle, Cait Sith, Chocobo, Imp, Moogle, Shiva, Sprite, Sylph, Tonberry)
- **Full YAML Migration**: 18/215 abilities done, complete remaining 197 in Phase 4
- **Quest System Expansion**: Basic system works, add more content later

---

## Format
All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

### Types of changes
- **Added** for new features
- **Changed** for changes in existing functionality
- **Deprecated** for soon-to-be removed features
- **Removed** for now removed features
- **Fixed** for any bug fixes
- **Security** in case of vulnerabilities
