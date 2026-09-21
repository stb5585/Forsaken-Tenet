"""Serializable save-data value objects."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

SAVE_SCHEMA_VERSION = 2


class SaveCompatibilityStatus(str, Enum):
    """Compatibility state shown for one player-visible save."""

    COMPATIBLE = "compatible"
    PRE_FOUNDATION = "pre_foundation"
    UNSUPPORTED_VERSION = "unsupported_version"
    UNREADABLE = "unreadable"
    NOT_A_FILE = "not_a_file"
    INVALID_NAME = "invalid_name"


class SaveLoadCode(str, Enum):
    """Machine-readable result of a save load attempt."""

    SUCCESS = "success"
    NOT_FOUND = "not_found"
    INVALID_FILENAME = "invalid_filename"
    INCOMPATIBLE_SCHEMA = "incompatible_schema"
    INVALID_DATA = "invalid_data"
    UNREADABLE = "unreadable"


@dataclass
class ResourceData:
    """Serializable resource (health/mana)."""

    max: int
    current: int


@dataclass
class StatsData:
    """Serializable character stats."""

    strength: int = 0
    intel: int = 0
    wisdom: int = 0
    con: int = 0
    charisma: int = 0
    dex: int = 0


@dataclass
class CombatData:
    """Serializable combat stats."""

    attack: int = 0
    defense: int = 0
    magic: int = 0
    magic_def: int = 0


@dataclass
class LevelData:
    """Serializable level info."""

    level: int = 1
    pro_level: int = 1
    exp: int = 0
    exp_to_gain: int = 25


@dataclass
class StatusEffectData:
    """Serializable status effect."""

    active: bool = False
    duration: int = 0
    extra: int = 0
