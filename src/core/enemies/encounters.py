"""Enemy encounter catalogs, random selection, and debug overrides."""

from __future__ import annotations

import os
from collections.abc import Callable, Iterable
from dataclasses import dataclass
from typing import NamedTuple

from src.core.randomness import gameplay_random as random

from ..combat.encounter import CombatEncounter
from .base import Enemy
from .catalog import CURATED_PAIR_SPECS
from .registry import ENEMY_NAMESPACE, FUNHOUSE_ENEMY_CATALOG, RANDOM_ENEMY_CATALOG

AbilityFactory = Callable[[], object]
EnemyFactory = Callable[[], Enemy]
RandomEnemyOverride = str | type[Enemy] | EnemyFactory
_random_enemy_override: RandomEnemyOverride | None = None
_RANDOM_ENEMY_OVERRIDE_ENV = "DUNGEON_FORCE_ENEMY"
_CURATED_ENCOUNTER_OVERRIDE_ENV = "DUNGEON_FORCE_ENCOUNTER"
_PILOT3_ROLLOUT_ENV = "DUNGEON_PILOT3_ROLLOUT"
PILOT3_PAIR_CHANCE = 0.15
# This tuple is evidence-owned.  A pair may be added only after it clears the
# promoted-class future-expansion gates recorded in MULTI_ENEMY_FUTURE_GATE.md.
QUALIFIED_PILOT3_PAIR_KEYS: tuple[str, ...] = ()

_ENEMY_NAMESPACE = ENEMY_NAMESPACE
_RANDOM_ENEMY_CATALOG = RANDOM_ENEMY_CATALOG
_FUNHOUSE_ENEMY_CATALOG = FUNHOUSE_ENEMY_CATALOG


class EnemyCandidate(NamedTuple):
    """Lightweight encounter choice preserving the historical ``.name`` API."""

    name: str
    factory: EnemyFactory


@dataclass(frozen=True)
class CuratedEncounterSpec:
    """Immutable development-pilot encounter definition."""

    key: str
    display_name: str
    floor: int
    member_factories: tuple[EnemyFactory, EnemyFactory]
    health_multiplier: float = 1.0
    offense_multiplier: float = 1.0

    def build(self) -> CombatEncounter:
        """Build a fresh runtime encounter in authored member order."""
        members = [factory() for factory in self.member_factories]
        for enemy in members:
            enemy._curated_base_health_max = enemy.health.max
            enemy.health.max = max(
                1,
                int(enemy._curated_base_health_max * self.health_multiplier),
            )
            enemy.health.current = enemy.health.max
            enemy._encounter_offense_multiplier = self.offense_multiplier
        encounter = CombatEncounter.from_enemies(members)
        # Runtime-only rollout metadata belongs on the encounter, never on a
        # persistent enemy state.  BattleLogger exports it for rollout review.
        encounter.encounter_key = self.key
        encounter.encounter_source = "curated"
        return encounter


def set_random_enemy_override(enemy: RandomEnemyOverride | None) -> None:
    """Force random encounters to use a specific enemy for debug playtesting.

    Accepts an enemy class, a zero-argument factory, an enemy class name, or
    ``None`` to clear the override.
    """
    global _random_enemy_override
    _random_enemy_override = enemy


def clear_random_enemy_override() -> None:
    """Return random encounters to normal catalog selection."""
    set_random_enemy_override(None)


def curated_encounter_specs() -> tuple[CuratedEncounterSpec, ...]:
    """Return the development-only pair catalog in authored order."""
    specs = []
    for key, raw_spec in CURATED_PAIR_SPECS.items():
        display_name, floor, class_names, *modifiers = raw_spec
        health_multiplier, offense_multiplier = modifiers[0] if modifiers else (1.0, 1.0)
        factories = tuple(_ENEMY_NAMESPACE[name] for name in class_names)
        specs.append(
            CuratedEncounterSpec(
                key=key,
                display_name=display_name,
                floor=floor,
                member_factories=factories,
                health_multiplier=health_multiplier,
                offense_multiplier=offense_multiplier,
            )
        )
    return tuple(specs)


def curated_encounter_spec(key: str) -> CuratedEncounterSpec:
    """Return one curated encounter definition by stable key."""
    for spec in curated_encounter_specs():
        if spec.key == key:
            return spec
    raise ValueError(f"Unknown curated encounter override: {key}")


def build_curated_encounter(key: str) -> CombatEncounter:
    """Build a fresh curated development encounter."""
    return curated_encounter_spec(key).build()


def pilot3_rollout_enabled() -> bool:
    """Return whether the default-on ordinary Pilot 3 rollout is enabled.

    Set ``DUNGEON_PILOT3_ROLLOUT=0`` (or ``false``/``off``) to immediately
    return ordinary generation to singleton encounters.  Development overrides
    intentionally remain available while the rollout is disabled.
    """
    value = os.getenv(_PILOT3_ROLLOUT_ENV, "1").strip().lower()
    return value not in {"0", "false", "no", "off"}


def qualified_pilot3_encounter_specs(level: str) -> tuple[CuratedEncounterSpec, ...]:
    """Return approved rollout pairs for one floor in stable authored order."""
    try:
        floor = int(level)
    except (TypeError, ValueError):
        return ()
    return tuple(
        spec
        for spec in curated_encounter_specs()
        if spec.key in QUALIFIED_PILOT3_PAIR_KEYS and spec.floor == floor
    )


def _attach_runtime_encounter(enemy: Enemy, encounter: CombatEncounter, key: str) -> Enemy:
    """Attach runtime-only roster metadata to the legacy primary-enemy API."""
    enemy._runtime_combat_encounter = encounter
    enemy._curated_encounter_key = key
    return enemy


def _forced_curated_encounter(
    level: str,
    *,
    enabled: bool,
) -> CombatEncounter | None:
    """Build an environment-forced pair for an authorized random encounter."""
    key = os.getenv(_CURATED_ENCOUNTER_OVERRIDE_ENV, "").strip()
    forced_enemy = _random_enemy_override is not None or bool(
        os.getenv(_RANDOM_ENEMY_OVERRIDE_ENV, "").strip()
    )
    if key and forced_enemy:
        raise ValueError(
            "DUNGEON_FORCE_ENEMY and DUNGEON_FORCE_ENCOUNTER " "cannot be used together."
        )
    if not key or not enabled:
        return None
    spec = curated_encounter_spec(key)
    if int(level) != spec.floor:
        raise ValueError(
            f"Curated encounter {key!r} belongs to floor {spec.floor}, " f"not floor {level}."
        )
    return spec.build()


def _rollout_curated_encounter(
    level: str,
    *,
    enabled: bool,
    rng: random.Random,
) -> Enemy | None:
    """Choose an evidence-qualified ordinary pair at the fixed rollout rate."""
    if not enabled or not pilot3_rollout_enabled() or rng.random() >= PILOT3_PAIR_CHANCE:
        return None
    candidates = qualified_pilot3_encounter_specs(level)
    if not candidates:
        return None
    spec = rng.choice(candidates)
    encounter = spec.build()
    return _attach_runtime_encounter(encounter.primary_enemy, encounter, spec.key)


def _build_random_enemy_override() -> Enemy | None:
    override = _random_enemy_override
    if override is None:
        env_override = os.getenv(_RANDOM_ENEMY_OVERRIDE_ENV, "").strip()
        override = env_override or None
    if override is None:
        return None
    if isinstance(override, str):
        enemy_cls = _ENEMY_NAMESPACE.get(override)
        if not isinstance(enemy_cls, type) or not issubclass(enemy_cls, Enemy):
            raise ValueError(f"Unknown random enemy override: {override}")
        return enemy_cls()
    if isinstance(override, type):
        if not issubclass(override, Enemy):
            raise TypeError("Random enemy override class must inherit Enemy.")
        return override()
    enemy = override()
    if not isinstance(enemy, Enemy):
        raise TypeError("Random enemy override factory must return an Enemy.")
    return enemy


def random_enemy_catalog() -> dict[str, list[Enemy]]:
    """Return freshly instantiated random-encounter enemies keyed by floor.

    This compatibility view intentionally creates every entry. Runtime selection
    should use :func:`random_enemy`, which instantiates only the chosen enemy.
    """
    return {
        level: [factory() for _name, factory in entries]
        for level, entries in _RANDOM_ENEMY_CATALOG.items()
    }


def random_enemy_candidates(level: str) -> tuple[tuple[str, EnemyFactory], ...]:
    """Return immutable ``(display_name, factory)`` entries for one floor."""
    if level not in _RANDOM_ENEMY_CATALOG:
        level = max(_RANDOM_ENEMY_CATALOG, key=int)
    return _RANDOM_ENEMY_CATALOG[level]


def random_enemy(
    level: str,
    preferred_names: Iterable[str] | None = None,
    preferred_chance: float = 0.0,
    rng=random,
    *,
    allow_curated_encounter: bool = False,
    allow_pilot3_rollout: bool = False,
) -> Enemy:
    """Return an enemy appropriate for one random-selection consumer.

    Curated pair overrides are disabled by default so utility consumers such
    as bounty generation cannot accidentally receive runtime encounters.
    Ordinary dungeon entry points must opt in explicitly.
    """
    if forced_encounter := _forced_curated_encounter(
        level,
        enabled=allow_curated_encounter,
    ):
        return _attach_runtime_encounter(
            forced_encounter.primary_enemy,
            forced_encounter,
            os.getenv(_CURATED_ENCOUNTER_OVERRIDE_ENV, "").strip(),
        )
    if forced_enemy := _build_random_enemy_override():
        return forced_enemy

    preferred_names = tuple(preferred_names or ())
    # Quest-biased calls supply preferred targets.  Keeping those and all
    # callers that do not explicitly opt in singleton protects quests, chests,
    # bosses, trials, scripted fights, bounties, and utility catalog users.
    if not preferred_names:
        if rollout_enemy := _rollout_curated_encounter(
            level,
            enabled=allow_pilot3_rollout,
            rng=rng,
        ):
            return rollout_enemy

    candidates = tuple(EnemyCandidate(*entry) for entry in random_enemy_candidates(level))
    preferred = {str(name) for name in preferred_names if str(name)}
    preferred_candidates = [entry for entry in candidates if entry.name in preferred]
    if preferred_candidates and rng.random() < max(0.0, min(1.0, preferred_chance)):
        candidates = tuple(preferred_candidates)

    selected = rng.choice(candidates)
    return selected.factory()


def funhouse_enemy_catalog() -> list[Enemy]:
    """Return the Funhouse challenge enemy catalog."""
    return [factory() for _name, factory in _FUNHOUSE_ENEMY_CATALOG]


def funhouse_enemy() -> Enemy:
    """Return a random Funhouse challenge enemy."""
    _name, enemy_factory = random.choice(_FUNHOUSE_ENEMY_CATALOG)
    return enemy_factory()
