"""Byte-bounded storage for transformed Pygame surfaces."""

from collections import OrderedDict
from collections.abc import Hashable
from typing import Generic, TypeVar

import pygame

Key = TypeVar("Key", bound=Hashable)


class ScaledSurfaceCache(Generic[Key]):
    """Keep recent surfaces within a budget measured by pixel buffer size."""

    def __init__(self, max_bytes: int) -> None:
        self.max_bytes = max(0, max_bytes)
        self._entries: OrderedDict[Key, tuple[pygame.Surface, int]] = OrderedDict()
        self._bytes = 0
        self._hits = 0
        self._misses = 0
        self._evictions = 0
        self._oversized = 0

    def get(self, key: Key) -> pygame.Surface | None:
        entry = self._entries.get(key)
        if entry is None:
            self._misses += 1
            return None
        self._hits += 1
        self._entries.move_to_end(key)
        return entry[0]

    def __setitem__(self, key: Key, surface: pygame.Surface) -> None:
        previous = self._entries.pop(key, None)
        if previous is not None:
            self._bytes -= previous[1]

        size = surface.get_pitch() * surface.get_height()
        if size > self.max_bytes:
            self._oversized += 1
            return

        while self._bytes + size > self.max_bytes:
            _, (_, evicted_size) = self._entries.popitem(last=False)
            self._bytes -= evicted_size
            self._evictions += 1

        self._entries[key] = (surface, size)
        self._bytes += size

    def clear(self) -> None:
        self._entries.clear()
        self._bytes = self._hits = self._misses = self._evictions = self._oversized = 0

    def stats(self) -> dict[str, int]:
        """Report retained pixel bytes and activity since the last clear."""
        return {
            "entries": len(self._entries),
            "bytes": self._bytes,
            "max_bytes": self.max_bytes,
            "hits": self._hits,
            "misses": self._misses,
            "evictions": self._evictions,
            "oversized": self._oversized,
        }
