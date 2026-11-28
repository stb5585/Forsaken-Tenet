"""Regression coverage for scaled surface cache eviction."""

import pygame

from src.ui_pygame.assets.scaled_surface_cache import ScaledSurfaceCache


def test_scaled_surface_cache_evicts_by_bytes_and_access_order():
    first, second, third = (pygame.Surface((8, 8), pygame.SRCALPHA) for _ in range(3))
    size = first.get_pitch() * first.get_height()
    cache = ScaledSurfaceCache[str](size * 2)
    cache["first"] = first
    cache["second"] = second
    assert cache.get("first") is first

    cache["third"] = third

    assert cache.get("second") is None
    assert cache.get("first") is first
    assert cache.get("third") is third
    assert cache.stats() == {
        "entries": 2,
        "bytes": size * 2,
        "max_bytes": size * 2,
        "hits": 3,
        "misses": 1,
        "evictions": 1,
        "oversized": 0,
    }


def test_oversized_surfaces_do_not_evict_other_entries():
    small = pygame.Surface((4, 4), pygame.SRCALPHA)
    size = small.get_pitch() * small.get_height()
    cache = ScaledSurfaceCache[str](size)
    cache["small"] = small
    cache["oversized"] = pygame.Surface((8, 8), pygame.SRCALPHA)

    assert cache.get("oversized") is None
    assert cache.get("small") is small
    assert cache.stats()["oversized"] == 1
    assert cache.stats()["bytes"] == size

    cache.clear()
    assert cache.stats()["bytes"] == 0
    assert cache.stats()["hits"] == 0
