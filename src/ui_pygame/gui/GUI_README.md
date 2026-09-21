# The Forsaken Tenet Pygame Frontend

Pygame is the supported player-facing frontend. It owns menus, town and dungeon
presentation, combat presentation, input adaptation, audio routing, and
save/load screens; gameplay rules remain under `src/core/`.

## Launch

From the repository root, using the project virtual environment:

```bash
./launch.sh
```

The direct entry point is:

```bash
./.venv/bin/python game_pygame.py
```

Useful development variants are documented in the root
[`README.md`](../../../README.md), including the Character Menu preview, debug
launch, and remote-playtest controls.

## Current Architecture

- `src/ui_pygame/gui/` contains screens and gameplay presentation flows.
- `src/ui_pygame/presentation/pygame_presenter.py` owns shared presentation and
  event subscriptions.
- `src/ui_pygame/input_adapter.py` maps supported inputs to semantic commands.
- `src/ui_pygame/screen_runtime.py` owns direct event polling, normalized
  screen input, the frame clock, and push/replace/pop/quit transitions.
- `src/ui_pygame/assets/` contains runtime managers and packaged visual assets.
- `src/core/events/` exposes UI-agnostic events consumed by presentation code.

The frontend includes the complete playable combat, exploration, character,
shop, quest, save/load, victory, defeat, and ending flows. Current migration
work focuses on native/adaptive layout and converting centralized legacy modal
loops into non-blocking `ScreenRuntime` states. See
[`docs/MOBILE_PLATFORM_ROADMAP.md`](../../../docs/MOBILE_PLATFORM_ROADMAP.md).

## Development Rules

- Keep Pygame imports and input decisions out of `src/core/`.
- Load runtime assets through the specialized managers and paths in `src.paths`;
  the unused generic sprite generator/manager has been removed.
- Preserve keyboard and mouse behavior when adding controller or touch input.
- Add a frame limiter to any temporary modal loop and prefer the shared screen
  runtime as it becomes available.
- Run focused tests under `tests/ui_pygame/` for changed screens before the full
  suite.

Headless tests use SDL's dummy drivers where needed. Interactive play still
requires a graphical environment.
