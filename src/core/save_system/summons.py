"""Summon serialization and restoration."""

from __future__ import annotations

from dataclasses import asdict
from typing import TYPE_CHECKING

from ..character import Combat, Level, Resource, Stats
from ..identity import COMPANION_TYPES
from .errors import SaveValidationError
from .item_serialization import AbilitySerializer
from .models import CombatData, LevelData, ResourceData, StatsData

if TYPE_CHECKING:
    from typing import Any


class SummonSerializer:
    """Serializes summon roster entries by stable companion ID."""

    @staticmethod
    def _serialize_spellbook(spellbook) -> dict[str, dict[str, str]]:
        serialized = {"Spells": {}, "Skills": {}}
        if not isinstance(spellbook, dict):
            return serialized

        for typ in ("Spells", "Skills"):
            entries = spellbook.get(typ, {})
            if not isinstance(entries, dict):
                if entries:
                    serialized[typ] = {
                        getattr(entries, "name", typ): AbilitySerializer.serialize(entries)
                    }
                continue
            serialized[typ] = {
                name: AbilitySerializer.serialize(ability)
                for name, ability in entries.items()
                if ability
            }
        return serialized

    @staticmethod
    def _deserialize_spellbook(spellbook_data: dict[str, dict[str, str]]) -> dict[str, dict]:
        restored = {"Spells": {}, "Skills": {}}
        if not isinstance(spellbook_data, dict):
            return restored

        for typ in ("Spells", "Skills"):
            entries = spellbook_data.get(typ, {})
            if not isinstance(entries, dict):
                continue
            restored[typ] = {
                name: ability
                for name, ability_name in entries.items()
                if (ability := AbilitySerializer.deserialize(ability_name))
            }
        return restored

    @staticmethod
    def serialize(summon) -> dict[str, Any]:
        """Convert a summon object to save data."""
        return {
            "companion_id": COMPANION_TYPES.id_for(summon),
            "name": getattr(summon, "name", summon.__class__.__name__),
            "health": asdict(ResourceData(summon.health.max, summon.health.current)),
            "mana": asdict(ResourceData(summon.mana.max, summon.mana.current)),
            "stats": asdict(
                StatsData(
                    summon.stats.strength,
                    summon.stats.intel,
                    summon.stats.wisdom,
                    summon.stats.con,
                    summon.stats.charisma,
                    summon.stats.dex,
                )
            ),
            "combat": asdict(
                CombatData(
                    summon.combat.attack,
                    summon.combat.defense,
                    summon.combat.magic,
                    summon.combat.magic_def,
                )
            ),
            "level": asdict(
                LevelData(
                    summon.level.level,
                    summon.level.pro_level,
                    summon.level.exp,
                    summon.level.exp_to_gain,
                )
            ),
            "spellbook": SummonSerializer._serialize_spellbook(getattr(summon, "spellbook", {})),
            "resistance": dict(getattr(summon, "resistance", {})),
            "status_immunity": list(getattr(summon, "status_immunity", [])),
            "flying": bool(getattr(summon, "flying", False)),
            "invisible": bool(getattr(summon, "invisible", False)),
        }

    @staticmethod
    def deserialize(data: dict[str, Any]):
        """Rebuild a summon object from save data."""
        if not isinstance(data, dict):
            return None

        companion_id = data.get("companion_id")
        if not isinstance(companion_id, str) or not companion_id:
            raise SaveValidationError("summon.companion_id", "expected a non-empty string")
        try:
            summon_class = COMPANION_TYPES.resolve(companion_id)
        except KeyError as exc:
            raise SaveValidationError("summon.companion_id", str(exc)) from exc

        try:
            summon = summon_class()
        except (TypeError, ValueError) as exc:
            raise SaveValidationError(
                "summon", f"could not construct {companion_id!r}: {exc}"
            ) from exc

        summon.name = data.get("name", getattr(summon, "name", companion_id))

        health = data.get("health", {})
        summon.health = Resource(
            health.get("max", summon.health.max),
            health.get("current", summon.health.current),
        )

        mana = data.get("mana", {})
        summon.mana = Resource(
            mana.get("max", summon.mana.max),
            mana.get("current", summon.mana.current),
        )

        stats = data.get("stats", {})
        summon.stats = Stats(
            strength=stats.get("strength", summon.stats.strength),
            intel=stats.get("intel", summon.stats.intel),
            wisdom=stats.get("wisdom", summon.stats.wisdom),
            con=stats.get("con", summon.stats.con),
            charisma=stats.get("charisma", summon.stats.charisma),
            dex=stats.get("dex", summon.stats.dex),
        )

        combat = data.get("combat", {})
        summon.combat = Combat(
            attack=combat.get("attack", summon.combat.attack),
            defense=combat.get("defense", summon.combat.defense),
            magic=combat.get("magic", summon.combat.magic),
            magic_def=combat.get("magic_def", summon.combat.magic_def),
        )

        level = data.get("level", {})
        summon.level = Level(
            level=level.get("level", summon.level.level),
            pro_level=level.get("pro_level", summon.level.pro_level),
            exp=level.get("exp", summon.level.exp),
            exp_to_gain=level.get("exp_to_gain", summon.level.exp_to_gain),
        )

        summon.spellbook = SummonSerializer._deserialize_spellbook(data.get("spellbook", {}))
        summon.resistance = dict(data.get("resistance", getattr(summon, "resistance", {})))
        summon.status_immunity = list(
            data.get("status_immunity", getattr(summon, "status_immunity", []))
        )
        summon.flying = bool(data.get("flying", getattr(summon, "flying", False)))
        summon.invisible = bool(data.get("invisible", getattr(summon, "invisible", False)))
        return summon

    @staticmethod
    def serialize_summons(summons: dict) -> dict[str, dict[str, Any]]:
        if not isinstance(summons, dict):
            return {}
        return {
            name: SummonSerializer.serialize(summon)
            for name, summon in summons.items()
            if summon is not None
        }

    @staticmethod
    def deserialize_summons(data: dict[str, dict[str, Any]]) -> dict:
        if not isinstance(data, dict):
            return {}

        summons = {}
        for name, summon_data in data.items():
            summon = SummonSerializer.deserialize(summon_data)
            if summon is not None:
                summons[getattr(summon, "name", name)] = summon
        return summons
