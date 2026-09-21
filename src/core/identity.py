"""Stable identity registries for persisted gameplay types."""

from __future__ import annotations

import re
from collections.abc import Iterator
from typing import Generic, TypeVar

T = TypeVar("T", bound=type)


def canonical_slug(value: str) -> str:
    """Return a lowercase snake-case identifier for a type or display name."""
    separated = re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", value)
    return re.sub(r"[^a-z0-9]+", "_", separated.lower()).strip("_")


class IdentityRegistry(Generic[T]):
    """Bidirectional registry that rejects duplicate IDs and unregistered types."""

    def __init__(self, domain: str) -> None:
        self.domain = domain
        self._by_id: dict[str, T] = {}
        self._by_type: dict[T, str] = {}

    def register(self, value_type: T, identity: str | None = None) -> str:
        """Register a concrete type and return its canonical identifier."""
        type_id = canonical_slug(identity or value_type.__name__)
        existing = self._by_id.get(type_id)
        if existing is not None and existing is not value_type:
            raise ValueError(
                f"duplicate {self.domain} id {type_id!r}: "
                f"{existing.__name__} and {value_type.__name__}"
            )
        self._by_id[type_id] = value_type
        self._by_type[value_type] = type_id
        return type_id

    def id_for(self, value: object | T) -> str:
        """Return the registered identifier for an instance or type."""
        value_type = value if isinstance(value, type) else type(value)
        try:
            return self._by_type[value_type]  # type: ignore[index]
        except KeyError as exc:
            raise KeyError(f"unregistered {self.domain} type: {value_type.__name__}") from exc

    def resolve(self, identity: str) -> T:
        """Return the type registered for an identifier."""
        try:
            return self._by_id[identity]
        except KeyError as exc:
            raise KeyError(f"unknown {self.domain} id: {identity!r}") from exc

    def items(self) -> Iterator[tuple[str, T]]:
        """Iterate over registered identifiers and types."""
        return iter(self._by_id.items())


ITEM_TYPES: IdentityRegistry[type] = IdentityRegistry("item")
CLASS_TYPES: IdentityRegistry[type] = IdentityRegistry("class")
RACE_TYPES: IdentityRegistry[type] = IdentityRegistry("race")
ENEMY_TYPES: IdentityRegistry[type] = IdentityRegistry("enemy")
COMPANION_TYPES: IdentityRegistry[type] = IdentityRegistry("companion")
ABILITY_TYPES: IdentityRegistry[type] = IdentityRegistry("ability")
