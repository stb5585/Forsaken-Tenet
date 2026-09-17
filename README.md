# The Forsaken Tenet

The Forsaken Tenet is a Python 3.12+ visual dungeon-crawl RPG built with
Pygame. Some legacy module names and archived documents still refer to the
earlier Dungeon Crawl working title.

## Current Status

The current source of truth is
[docs/DEVELOPMENT_ROADMAP.md](docs/DEVELOPMENT_ROADMAP.md). As of the latest
roadmap pass:

- Core gameplay lives under `src/core/`.
- The supported visual frontend lives under `src/ui_pygame/`.
- Terminal development remains available through tests, simulators, reports,
  and diagnostic tools rather than a second playable frontend.
- Ability data is substantially migrated to YAML under
  `src/core/data/abilities/`.
- All 49 authored class ability trees and the critical class-kit closure pass
  are complete.
- Foundational gameplay refactors are the active planning lane. Broad manual
  playtesting is deferred until combat timing, targeting, multi-enemy scope,
  and the combat action interface stabilize.
- Completed class-kit scope and deferred deep-kit gates are tracked in
  [docs/CLASS_KIT_DESIGN_GATES.md](docs/CLASS_KIT_DESIGN_GATES.md).
- Combat architecture and balance decisions are specified in
  [docs/COMBAT_BALANCE_DESIGN_GATES.md](docs/COMBAT_BALANCE_DESIGN_GATES.md)
  before gameplay or balance rules change.
- Presentation, dungeon/world/encounter, and equipment/economy work now have
  dedicated design-gate docs linked from the roadmap and docs index.
- Retired phase plans are removed from the active documentation set and remain
  recoverable through Git history.

## Requirements

- Python 3.12+
- Project virtual environment at `./.venv/`
- Runtime packages include `numpy`, `PyYAML`, `pygame`, and `Pillow`

Always prefer the project virtual environment for Python commands:

```bash
./.venv/bin/python -m pytest tests/core -q
./.venv/bin/python tools/dev_tools.py --help
```

## Running The Game

```bash
# Standard Pygame launch
./launch.sh

# Direct Pygame entry point
./.venv/bin/python game_pygame.py

# Character Menu preview
./launch_character_menu.sh
./.venv/bin/python game_pygame.py --character-menu

# Debug launch
./launch_debug.sh

# Add on-screen dungeon controls for Moonlight or touch playtesting
./.venv/bin/python game_pygame.py --remote-playtest-controls
```

Installed and frozen builds store saves and other mutable state in the
platform user-data directory. Set `FORSAKEN_TENET_DATA_DIR` to override that
location for development or testing.

## Distribution

Build the supported PyInstaller onedir application and run its headless
resource smoke test:

```bash
./.venv/bin/python tools/build_distribution.py --clean
SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy \
  FORSAKEN_TENET_DATA_DIR=/tmp/forsaken-tenet-smoke \
  ./dist/forsaken-tenet/forsaken-tenet --smoke-test
```

Release artifacts are built by manual dispatch or a published GitHub release;
ordinary pushes perform validation only.

## Terminal Development

The retired curses frontend remains recoverable from the Git tag
`curses-ui-final`. Current terminal workflows exercise the shared engine
without maintaining a second player-facing UI:

```bash
./.venv/bin/python -m pytest tests/core -q
./.venv/bin/python -m pytest tests/integration -q
./.venv/bin/python tools/dev_tools.py effects
./.venv/bin/python tools/dev_tools.py events
```

## Testing

Run focused tests for the area you changed:

```bash
./.venv/bin/python -m pytest tests/core -q
./.venv/bin/python -m pytest tests/ui_pygame -q
./.venv/bin/python -m pytest tests/integration -q
```

Run the full suite when broader validation is needed:

```bash
./.venv/bin/python -m pytest tests/ -q
```

See [tests/README.md](tests/README.md) for current coverage notes and test
layout.

## Repository Layout

```text
src/
  core/          Shared game logic, combat, data, classes, items, saves
    data/maps/   Packaged dungeon maps and tileset images
  ui_pygame/     Pygame UI, assets, renderer, menus, combat view

docs/            Roadmap, durable design references, implementation notes, archive
tools/           Development, asset, audio, and balance utilities
tests/           Regression suite

game_pygame.py   Pygame entry point
```

## Documentation

Start with [docs/README.md](docs/README.md). The most useful current docs are:

- [docs/DEVELOPMENT_ROADMAP.md](docs/DEVELOPMENT_ROADMAP.md)
- [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)
- [docs/FOUNDATIONAL_REFACTOR_PLAN.md](docs/FOUNDATIONAL_REFACTOR_PLAN.md)
- [docs/CLASS_KIT_DESIGN_GATES.md](docs/CLASS_KIT_DESIGN_GATES.md)
- [docs/COMBAT_BALANCE_DESIGN_GATES.md](docs/COMBAT_BALANCE_DESIGN_GATES.md)
- [docs/CLASS_RING_SYSTEM.md](docs/CLASS_RING_SYSTEM.md)
- [docs/PRESENTATION_ASSET_DESIGN_GATES.md](docs/PRESENTATION_ASSET_DESIGN_GATES.md)
- [docs/DUNGEON_WORLD_ENCOUNTER_DESIGN_GATES.md](docs/DUNGEON_WORLD_ENCOUNTER_DESIGN_GATES.md)
- [docs/EQUIPMENT_ITEMS_ECONOMY_DESIGN_GATES.md](docs/EQUIPMENT_ITEMS_ECONOMY_DESIGN_GATES.md)
- [docs/STORY_AND_ENDGAME_DESIGN.md](docs/STORY_AND_ENDGAME_DESIGN.md)
- [docs/PLAYTEST_CHECKLIST.md](docs/PLAYTEST_CHECKLIST.md)
- [docs/ENEMY_VISUAL_SYSTEM.md](docs/ENEMY_VISUAL_SYSTEM.md)
- [docs/DUNGEON_TILE_ART.md](docs/DUNGEON_TILE_ART.md)
- [docs/ASSET_PROVENANCE.md](docs/ASSET_PROVENANCE.md)

## Development Tools

```bash
./.venv/bin/python tools/dev_tools.py effects
./.venv/bin/python tools/dev_tools.py queue
./.venv/bin/python tools/dev_tools.py events
./.venv/bin/python tools/dev_tools.py abilities --directory src/core/data/abilities
./.venv/bin/python tools/run_balance_suite.py --help
```

See [tools/README.md](tools/README.md) for more.
