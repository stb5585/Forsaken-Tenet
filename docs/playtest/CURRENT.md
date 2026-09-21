# Comprehensive Playtest Queue

Status: `Ready — Foundational Baseline Established`

The foundational gameplay refactor is complete. Broad evidence collection now
uses the committed baseline: typed ability slugs and version-2 saves,
one-roll fitted contact, virtual-readiness timing, core concealment/targeting,
the shortcut and All Actions interface, and a singleton ordinary encounter
catalog. The post-refactor seed-1337 reports are committed at:

- `reports/balance_baselines/multi_enemy_foundation_singleton.txt`
- `reports/balance_baselines/multi_enemy_pilot3_foundation_floor3.txt`
- `reports/balance_baselines/multi_enemy_pilot3_foundation_floor4.txt`

Pilot 3 qualified no ordinary pairs. `DUNGEON_PILOT3_ROLLOUT` remains a
default-on kill switch for a future evidence-qualified pair, but the qualified
catalog is currently empty and normal generation is singleton.

Record results against this baseline. Do not alter combat numbers merely to
resolve an observation; promote a reproducible defect to a focused regression
or a proposed, separately approved tuning slice.

## Post-Refactor Smoke Coverage

- Create and advance representative base, first-promotion, and
  second-promotion characters through the revised action and progression
  surfaces.
- Verify keyboard, mouse, and controller-supported action selection, target
  selection, cancellation, and unavailable-action feedback.
- Exercise singleton and every supported multi-enemy encounter size.
- Verify invisible, revealed, flying, defeated, transformed, and target-lost
  combatants.
- Verify ordinary, charged, delayed, forced, reaction, companion, summon, Totem,
  item, and flee actions under the revised timing model.
- Verify current-save round trips across every changed gameplay or UI state.

## Class Rings And Kit Evidence

- Review Class Ring wording when absent, inventory-only, stored,
  equipped-dormant, and equipped-awakened.
- Record one martial-meter route in
  [`CLASS_KIT_EVIDENCE_NOTES.md`](../CLASS_KIT_EVIDENCE_NOTES.md).
- Record one caster/support-meter route.
- Record one persistent-progress route.
- Record two awakened-ring preservation cases with different failure modes.
- Recheck meter cadence and action-economy findings after the action interface
  and combat timing are final.

## Progression And Interface

- Verify all five base lineages and representative promotion paths under the
  final progression contract.
- Verify staged spending, permanent closures, promotion previews, retained
  abilities, equipment routing, and current-save ownership.
- Confirm active, passive, reaction, and unavailable abilities appear only on
  their intended final surfaces.
- Confirm class resources remain readable at empty, building, ready, spent,
  preserved, and cleanup states.

## World And Story Regression

- Verify the staged relic route from `Uncertain Reports` through Triangulus
  report-back and creation of `The Holy Relics`.
- Verify normal death, special-route defeat, town return, and postgame town
  dialogue.
- On floors 1–6, verify visible gathering-node overlays. Druid/Archdruid should
  identify and explicitly harvest Acorn, Vine Seed, Fungus Spore, and Hemlock
  Root; Assassin should identify and explicitly harvest Deathcap Mushroom.
  Other classes should see unfamiliar growth but receive no harvest action.
- Verify the Vesperion/Voluntas route, Liminal trials, Reflection, true-final
  completion, and ending continuity.

## Exit Criteria

The comprehensive readiness pass is complete when:

1. every item above passes or has a reproducible issue;
2. all promoted issues have focused regression coverage;
3. class-kit and combat evidence is recorded against the final ruleset; and
4. the roadmap identifies the next content, tuning, or release-readiness slice.

## Playtesting Notes
- anti-magic field works to prevent ability usage and it did correctly allow the character to select another option
- the new turn stack works to allow faster characters to go twice in a row

## Current Focus — Combat Presentation

- Reconfigure shortcuts by dragging Skill and Spell icons in Character Menu →
  Abilities, then verify keys 1–6, mouse, touch, and controller activation in
  combat. Arrow-key navigation and Enter must skip the shortcut tiles.
- Clear a shortcut and confirm selecting its empty combat slot does not advance
  the turn.
- Confirm the ability bar preserves unavailable-action reasons and All Actions
  remains a read-only catalog.
- Confirm the combined actor/timeline ribbon shows a larger current actor,
  blue player-side and red enemy-side outlines, and no readiness values.
- Win a fight and confirm defeated timeline badges remain through the enemy
  fade, with level and HP/MP changes appearing only after the fade completes.
- Turn in a collection quest and confirm its retained journal entry shows its
  completed count (for example, 6/6), not 0/6.
- Die in the dungeon, return to town, then re-enter it; confirm the first frame
  is freshly rendered rather than a stale dungeon view.
- Inspect Monocane and crossbows, bolts, venoms, and other catalog items to
  confirm each has an item icon.
- Save and reload before and after gathering a resource node. Confirm the node
  remains available before harvest and absent afterward, while existing enemy
  reagent drops and toxin/Plant Seeds use remain unchanged.
- Enter an anti-magic encounter and verify the persistent field badge and its
  one-time combat-entry explanation before selecting an ability.
- Exercise Sleeping Powder or Smoke Screen on an enemy and a familiar without
  an item, then verify player item-gated use still requires its tool.
