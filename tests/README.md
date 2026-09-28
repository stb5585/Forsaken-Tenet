# Test Suite Summary

## Overview

This directory contains the automated regression suite for The Forsaken Tenet.

Current snapshot:
- The authoritative test count and pass/fail status come from the latest CI
  run rather than a copied total in this document.
- Coverage is measured on demand rather than copied here as a stale percentage
- The suite covers core combat/content systems, integration and persistence
  flows, pygame-facing UI helpers, dungeon rendering/math, and
  balance/simulator workflows.
- Most day-to-day focused work should use targeted pytest runs inside the project venv

## Run Tests

Run the full suite:

```bash
./.venv/bin/python -m pytest tests/ -q
```

Run a module/domain slice:

```bash
./.venv/bin/python -m pytest tests/core -q
./.venv/bin/python -m pytest tests/integration -q
./.venv/bin/python -m pytest tests/ui_pygame -q
```

Run a specific file:

```bash
./.venv/bin/python -m pytest tests/core/test_character.py -q
./.venv/bin/python -m pytest tests/ui_pygame/test_pygame_sound_manager.py -q
```

Run a specific test:

```bash
./.venv/bin/python -m pytest tests/integration/test_battle.py::TestBattleLogger::test_export_payload_includes_metadata_events_and_summary -q
```

## Coverage Areas

High-coverage areas:
- `test_data_driven_abilities.py`: migrated abilities and effect behaviors
- `core/test_character.py` / `integration/test_battle.py`: character logic, battle
  engine flow, gameplay statistics, current-save round trips, and battle logging
- `integration/test_save_system_manager.py`: current-save round trips, atomic
  persistence behavior, metadata, and invalid-file handling
- `test_distribution.py`: runtime path and frozen-build configuration contracts
- Dungeon renderer/math tests:
  - `tests/ui_pygame/test_dungeon_renderer_smoke.py`
  - `tests/ui_pygame/test_dungeon_geometry.py`
  - `tests/ui_pygame/test_dungeon_projector.py`
  - `tests/ui_pygame/test_dungeon_scene.py`
  - `tests/ui_pygame/test_perspective.py`
  - `tests/ui_pygame/test_tileset.py`
- Balance and analytics:
  - `tests/test_balance_tuning.py`
  - `tests/core/test_combat_simulator.py`

Supporting coverage:
- Equipment and weapon effects
- Enemy AI / specialty enemies
- Shop, presenter, and shared menu smoke tests
- Integration and harness-based combat checks

Current layout:
- `tests/core/`: focused tests for `src/core/*`
  - currently includes character/player, equipment, items, enemies, companions, race/special-effect, town, combat-simulator, and map/realm focused tests
- `tests/integration/`: broader flow and cross-module tests
  - currently includes battle-system API/flow coverage, combat integration smoke tests, and save-system round-trip coverage
- `tests/ui_pygame/`: focused tests for `src/ui_pygame/*`
  - currently includes presenter, sound, shop, popup, town, dungeon, combat-manager/view, and menu/helper coverage
- top-level `tests/` still holds a smaller set of legacy or cross-cutting files such as `test_data_driven_abilities.py`, `test_core.py`, `test_balance_tuning.py`, and framework helpers
- bucket directories now include `__init__.py` markers so duplicate basenames like `test_battle.py` can coexist without pytest import collisions

## Recent Improvements

Recent test-debt cleanup completed:
- replaced stale skipped tests in the character and battle coverage files with real assertions
- added gameplay-statistics persistence coverage
- added save/load round-trip coverage for inventory, quest, storage, and tile state
- upgraded battle logger tests to cover structured export behavior
- replaced placeholder assertions in the pygame smoke tests and weapon-effect helpers
- tightened `ConsumeItem` fallback coverage in `test_data_driven_abilities.py`
- reorganized the suite into import-safe package buckets so duplicate basenames like `test_battle.py` and `test_town.py` no longer collide during pytest collection

## Notes

- Use the project venv for all pytest runs: `./.venv/bin/python -m pytest ...`
- Some tests exercise pygame/PIL asset paths but are written to complete without interactive loops
- The most active regression surfaces are the shared core systems, the Pygame
  helper/presenter layer, and headless combat and balance tooling.

## Quality Gates

CI reports coverage for `src`, checks formatting and import order, applies the
focused Ruff baseline configured in `pyproject.toml`, and runs `compileall` for
`src`. The incremental strict mypy baseline is:

```bash
./.venv/bin/mypy --strict --follow-imports=skip \
  src/paths.py \
  tools/build_distribution.py \
  src/core/combat/encounter.py \
  src/core/combat/targeting.py \
  src/core/combat/battle_engine/models.py \
  src/core/identity.py \
  src/core/randomness.py \
  src/core/contracts \
  src/core/data/ability_schema.py \
  src/core/data/ability_traits.py \
  src/core/progression/models.py \
  src/core/save_system/manager.py \
  src/ui_pygame/screen_runtime.py \
  src/core/combat/contact.py \
  tools/fit_contact_model.py \
  tools/characterize_foundational_contract.py
```

`--follow-imports=skip` keeps unrelated legacy annotation debt from entering
the strict set through imports. Expand Ruff and strict mypy coverage one
package at a time after that package passes; do not disable useful rules
globally to absorb the existing backlog. Frozen artifact builds are
intentionally limited to manual dispatches and releases.
