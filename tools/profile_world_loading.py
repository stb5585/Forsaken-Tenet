"""Measure dungeon-world construction and save restoration on the current maps."""

from __future__ import annotations

import argparse
import gc
import tracemalloc
from collections import Counter
from collections.abc import Callable
from pathlib import Path
from statistics import median
from tempfile import TemporaryDirectory
from time import perf_counter
from unittest.mock import patch

from src.core import map_tiles
from src.core.player import Player
from src.core.save_system import SaveManager
from tests.test_framework import TestGameState

SAVE_NAME = "world-loading-profile.save"


def report_measurement(name: str, operation: Callable[[], Player], repeats: int) -> None:
    """Measure wall time separately from Python allocation tracing."""
    elapsed_ms = []
    for _ in range(repeats):
        started = perf_counter()
        player = operation()
        elapsed_ms.append((perf_counter() - started) * 1000)
        del player

    gc.collect()
    tracemalloc.start()
    try:
        player = operation()
        retained, peak = tracemalloc.get_traced_memory()
        tile_count = len(player.world_dict)
    finally:
        tracemalloc.stop()

    print(
        f"{name}: first={elapsed_ms[0]:.1f} ms, median={median(elapsed_ms):.1f} ms, "
        f"max={max(elapsed_ms):.1f} ms, tiles={tile_count}, "
        f"retained={retained / 1024**2:.2f} MiB, peak={peak / 1024**2:.2f} MiB"
    )


def create_world() -> Player:
    """Construct the production world for a fixed character and dungeon seed."""
    player = TestGameState.create_player()
    player.dungeon_trap_seed = 1337
    player.load_tiles()
    return player


def restore_save(*, skip_tiles: bool = False) -> Player:
    """Read and deserialize the benchmark save using the normal loader."""
    result = SaveManager.load_player_result(SAVE_NAME, skip_tiles=skip_tiles)
    if not isinstance(result.player, Player):
        raise RuntimeError(result.error or "Unable to restore benchmark player")
    return result.player


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repeats", type=int, default=15)
    args = parser.parse_args()
    if args.repeats < 1:
        parser.error("--repeats must be at least 1")

    print(f"{args.repeats} samples per operation. Memory counts traced Python allocations.")
    report_measurement("Build player and world", create_world, args.repeats)
    player = create_world()
    print("Tiles by floor:", dict(sorted(Counter(pos[2] for pos in player.world_dict).items())))
    # Include a small amount of changed state rather than benchmarking a pristine save.
    door = next(
        tile for tile in player.world_dict.values() if isinstance(tile, map_tiles.LockedDoor)
    )
    door.visited = door.open = True
    door.locked = False
    with TemporaryDirectory(prefix="tenet-world-profile-") as directory:
        with patch.multiple(SaveManager, SAVE_DIR=directory, TMP_DIR=directory):
            if not SaveManager.save_player(player, SAVE_NAME):
                raise RuntimeError("Unable to create benchmark save")
            print(f"Save size: {(Path(directory) / SAVE_NAME).stat().st_size / 1024**2:.2f} MiB")
            report_measurement("Restore save and world", restore_save, args.repeats)
            report_measurement(
                "Read and restore save with tiles skipped",
                lambda: restore_save(skip_tiles=True),
                args.repeats,
            )


if __name__ == "__main__":
    main()
