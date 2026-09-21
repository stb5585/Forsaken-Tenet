"""Public save-system API.

Serialization responsibilities and filesystem persistence live in focused
modules. Existing imports from the save-system package remain supported.
"""

from .. import (
    abilities,
    enemies,
    items,
    main_story,
    quest_progress,
    thieves_guild,
)
from .. import town as town_core
from ..character import Combat, Level, Resource, Stats
from ..classes import promotion_kits
from .enemy import EnemyStateSerializer
from .errors import SaveValidationError
from .item_serialization import AbilitySerializer, ItemSerializer
from .manager import SaveFileMetadata, SaveLoadResult, SaveManager, json, os
from .models import (
    SAVE_SCHEMA_VERSION,
    CombatData,
    LevelData,
    ResourceData,
    SaveCompatibilityStatus,
    SaveLoadCode,
    StatsData,
    StatusEffectData,
)
from .player import PlayerDataSerializer
from .quests import QuestDataSerializer
from .summons import SummonSerializer
from .tiles import TileStateSerializer
