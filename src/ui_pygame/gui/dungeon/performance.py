"""Opt-in, low-overhead dungeon rendering diagnostics."""

from __future__ import annotations

from collections import defaultdict
from time import perf_counter


class DungeonPerformanceDiagnostics:
    """Aggregate renderer timings and emit a compact periodic diagnostic line."""

    def __init__(self, enabled: bool = False, report_interval_seconds: float = 2.0):
        self.enabled = enabled
        self.report_interval_seconds = report_interval_seconds
        self._timings: dict[str, list[float]] = defaultdict(list)
        self._projection_hits = 0
        self._projection_misses = 0
        self._last_report = perf_counter()

    def record(self, name: str, elapsed_seconds: float) -> None:
        """Record one operation duration when diagnostics are enabled."""
        if self.enabled:
            self._timings[name].append(elapsed_seconds * 1000.0)

    def record_projection_activity(self, hits: int, misses: int) -> None:
        """Record cache activity from the scene render it belongs to."""
        if self.enabled:
            self._projection_hits += hits
            self._projection_misses += misses

    def report_if_due(self) -> None:
        """Print average/max timings and cache activity at a restrained cadence."""
        if not self.enabled:
            return
        now = perf_counter()
        if now - self._last_report < self.report_interval_seconds:
            return
        self._last_report = now
        timing_summary = " ".join(
            f"{name}={sum(samples) / len(samples):.1f}/{max(samples):.1f}ms"
            for name, samples in sorted(self._timings.items())
            if samples
        )
        hits, misses = self._projection_hits, self._projection_misses
        total = hits + misses
        cache_summary = "projection=none"
        if total:
            cache_summary = f"projection={hits}/{misses} hit/miss ({hits * 100 / total:.0f}% hit)"
        print(f"Dungeon render diagnostics: {timing_summary or 'no frames'} {cache_summary}")
        self._timings.clear()
        self._projection_hits = 0
        self._projection_misses = 0
