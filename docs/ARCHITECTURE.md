# Architecture

This document describes the supported runtime boundaries after the
`improvements` stabilization pass. Design-gate documents own future gameplay
decisions; this document owns the shape of the application.

## Runtime Boundaries

`src/core/` is the UI-independent game engine. It owns characters, progression,
combat, encounters, items, quests, maps, persistence, events, and content
loading. Core code must not render, poll Pygame input, or require a display.

`src/ui_pygame/` is the supported player-facing frontend. It translates input
into core operations and renders core state and results. The retired curses UI
is preserved at the `curses-ui-final` Git tag and is not a second supported
runtime.

## Public Package APIs

Callers should import package-owned types from stable package entry points when
one exists, including `src.core.character`, `src.core.abilities`,
`src.core.combat.battle_engine`, `src.core.events`, and
`src.core.save_system`. Their `__init__.py` imports are intentional public or
compatibility re-exports, so lint configuration exempts only package
initializers from unused-import reporting.

Compatibility re-exports are transitional, but they must not be removed just
because an implementation was split into modules. A later cleanup should first
inventory external and internal callers, document a replacement import for
each symbol, add a deprecation period where practical, and remove the alias in
a separately announced breaking release.

## Foundational Contracts

Dependency-free contracts in `src/core/contracts` define ability identity and
taxonomy, actor-relative targeting, action references and availability,
timeline entries, visibility observations, and combat-resource presentation.
Core systems and Pygame may depend on these models; the contracts do not depend
on either runtime. This keeps validation, persistence, simulation, and
presentation on one vocabulary.

The YAML taxonomy validator enforces complete closed enum values and registered
namespaced traits for migrated definitions. Its exact legacy allowlist must
shrink whenever a family migrates and becomes an error once complete
validation is enabled.

## Combat Actions And Targets

The Pygame combat manager drives `BattleEngine`; the engine owns the combat
state and never reads input. A requested action is represented by an immutable
`ActionIntent` containing an action ID, optional migration choice, and stable
encounter target IDs. The temporary `action` property adapts legacy command
strings while callers migrate. Canonical `TargetScope` values are
actor-relative: no target, self, single opponent, and all opponents.
`TargetLossPolicy` determines whether a committed action stays locked,
retargets to focus, or uses a roster snapshot. Enemy-named scopes remain only
in the legacy combat adapter during migration.

The engine validates the intent, expands and resolves targets against the live
`CombatEncounter`, executes the action, and returns an `ActionResult` with a
machine-readable validation code when rejected. The actor cycle now owns
virtual readiness timestamps: initial seeded jitter and bounded Luck head
starts determine the first opportunity, while current effective Speed advances
readiness against the encounter-start median. Pre-turn and post-turn results
carry status and resolution effects, and `BattleOutcome` carries final
settlement. Events and the battle logger observe this flow without becoming the
source of combat truth.

The next combat architecture phase is intentionally deferred. Large mutation
methods such as weapon damage and status-effect resolution should be replaced
incrementally by typed, ordered modifier pipelines operating on explicit
combat context and result models. That work needs compatibility tests and
design approval; it is not part of stabilization.

## Saves

Save files are stamped with root `schema_version: 2`. Unmarked, version-1, and
unknown-version saves remain visible with an explanatory status but cannot be
loaded; this deliberate pre-release reset has no migration path. Version 2
uses canonical registries and stores six typed action-bar slots as ability-slug
or item-ID references. Unknown IDs reject the entire load without rewriting the
file. Missing item inventory never deletes the assignment. Combat
timelines, visibility observations, encounters, and mid-combat state remain
runtime-only.

`SaveManager` uses typed result codes and atomic replacement so an interrupted
write does not leave a partially written current save. Any future schema change
must explicitly choose a new reset or migration before implementation.

## Resources And Writable Data

`src.paths` is the path authority. In a checkout, resources resolve from the
repository root; in a PyInstaller process they resolve from `sys._MEIPASS`.
Packaged maps live under `src/core/data/maps/`, and Pygame assets live under
`src/ui_pygame/assets/`. Runtime code must not use the current working directory
to find either category.

Saves, temporary files, configuration, and debug logs use the platform user-data
directory: `%LOCALAPPDATA%` on Windows, `~/Library/Application Support` on
macOS, and `$XDG_DATA_HOME` or `~/.local/share` on Linux. The
`FORSAKEN_TENET_DATA_DIR` environment variable provides an explicit test and
development override.

## Distribution

The supported portable model is a PyInstaller onedir application built from
`packaging/forsaken_tenet.spec` with
`./.venv/bin/python tools/build_distribution.py --clean`. The bundle includes
runtime maps and assets but excludes documentation review sheets. Its
`--smoke-test` mode initializes headless Pygame, checks representative images
and maps, and verifies writable user-data directories without entering an
interactive loop.

Ordinary CI pushes validate source only. Artifact construction, headless frozen
startup, and artifact upload run only for a manual workflow dispatch or a
published release. Linux is the only verified artifact target during
development; Windows and macOS packaging are deferred until the
pre-distribution milestone.
