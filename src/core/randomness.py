"""Injectable, context-local randomness for gameplay systems."""

from __future__ import annotations

import random as _stdlib_random
from contextlib import contextmanager
from contextvars import ContextVar, Token
from typing import Any, Protocol


class RandomSource(Protocol):
    """Operations used by gameplay code from a deterministic random source."""

    def random(self) -> float: ...

    def randint(self, a: int, b: int) -> int: ...

    def randrange(self, *args: int) -> int: ...

    def uniform(self, a: float, b: float) -> float: ...

    def choice(self, sequence: Any) -> Any: ...

    def choices(self, population: Any, *args: Any, **kwargs: Any) -> list[Any]: ...

    def sample(self, population: Any, k: int) -> list[Any]: ...

    def shuffle(self, sequence: Any) -> None: ...


_ACTIVE_RANDOM_SOURCE: ContextVar[RandomSource | None] = ContextVar(
    "active_gameplay_random_source", default=None
)


def set_random_source(source: RandomSource) -> Token[RandomSource | None]:
    """Set the random source for the current execution context."""
    return _ACTIVE_RANDOM_SOURCE.set(source)


def reset_random_source(token: Token[RandomSource | None]) -> None:
    """Restore the random source previously active in this context."""
    _ACTIVE_RANDOM_SOURCE.reset(token)


@contextmanager
def using_random_source(source: RandomSource):
    """Route gameplay draws through ``source`` for the context lifetime."""
    token = set_random_source(source)
    try:
        yield source
    finally:
        reset_random_source(token)


class RandomRouter:
    """Module-like proxy that consults the context-local gameplay source."""

    Random = _stdlib_random.Random
    SystemRandom = _stdlib_random.SystemRandom

    @staticmethod
    def _source() -> Any:
        return _ACTIVE_RANDOM_SOURCE.get() or _stdlib_random

    def random(self) -> float:
        return float(self._source().random())

    def randint(self, a: int, b: int) -> int:
        return int(self._source().randint(a, b))

    def randrange(self, *args: int) -> int:
        return int(self._source().randrange(*args))

    def uniform(self, a: float, b: float) -> float:
        return float(self._source().uniform(a, b))

    def choice(self, sequence: Any) -> Any:
        return self._source().choice(sequence)

    def choices(self, population: Any, *args: Any, **kwargs: Any) -> list[Any]:
        return list(self._source().choices(population, *args, **kwargs))

    def sample(self, population: Any, k: int) -> list[Any]:
        return list(self._source().sample(population, k))

    def shuffle(self, sequence: Any) -> None:
        self._source().shuffle(sequence)

    def seed(self, value: Any = None) -> None:
        self._source().seed(value)

    def getstate(self) -> object:
        return self._source().getstate()

    def setstate(self, state: object) -> None:
        self._source().setstate(state)


_SHARED_RANDOM_ROUTER = RandomRouter()
gameplay_random = _SHARED_RANDOM_ROUTER


def random_router() -> RandomRouter:
    """Return the shared, monkeypatch-compatible gameplay-random proxy."""
    return _SHARED_RANDOM_ROUTER
