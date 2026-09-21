"""Strict quest and quest-reference serialization."""

from __future__ import annotations

from typing import Any

from .. import items
from ..identity import ENEMY_TYPES
from .errors import SaveValidationError
from .item_serialization import ItemSerializer
from .quest_identity import QUEST_IDS_BY_NAME, QUEST_NAMES_BY_ID


class QuestDataSerializer:
    """Serialize quest state with canonical quest, enemy, and item IDs."""

    @staticmethod
    def _serialize_item_reference(value: object, *, path: str) -> object:
        if isinstance(value, type) and issubclass(value, items.Item):
            try:
                value = value()
            except (TypeError, ValueError) as exc:
                raise SaveValidationError(path, f"could not construct reward item: {exc}") from exc
        if isinstance(value, items.Item):
            return ItemSerializer.serialize(value)
        if isinstance(value, str):
            return value
        raise SaveValidationError(path, f"unsupported quest item reference: {type(value).__name__}")

    @staticmethod
    def _deserialize_item_reference(value: object, *, path: str) -> object:
        if isinstance(value, dict):
            return ItemSerializer.deserialize(value, path=path)
        if isinstance(value, str):
            return value
        raise SaveValidationError(path, "expected an item object or string token")

    @staticmethod
    def serialize_quest_dict(quest_dict: dict[str, Any]) -> dict[str, Any]:
        """Convert runtime quest state into schema-version-2 data."""
        if not isinstance(quest_dict, dict):
            raise SaveValidationError("quest_dict", "expected an object")
        serialized: dict[str, Any] = {}

        for category, quests in quest_dict.items():
            if not isinstance(quests, dict):
                raise SaveValidationError(f"quest_dict.{category}", "expected an object")
            if category == "Bounty":
                serialized[category] = QuestDataSerializer._serialize_bounties(quests)
                continue
            if category not in {"Main", "Side"}:
                serialized[category] = dict(quests)
                continue

            encoded: dict[str, Any] = {}
            for quest_name, quest_data in quests.items():
                quest_id = QUEST_IDS_BY_NAME.get(quest_name)
                if quest_id is None:
                    raise SaveValidationError(
                        f"quest_dict.{category}", f"unknown authored quest: {quest_name!r}"
                    )
                if not isinstance(quest_data, dict):
                    raise SaveValidationError(
                        f"quest_dict.{category}.{quest_id}", "expected an object"
                    )
                record = dict(quest_data)
                if record.get("Type") == "Collect" and "What" in record:
                    record["What"] = QuestDataSerializer._serialize_item_reference(
                        record["What"], path=f"quest_dict.{category}.{quest_id}.What"
                    )
                if "Reward" in record:
                    reward = record["Reward"]
                    values = reward if isinstance(reward, list) else [reward]
                    record["Reward"] = [
                        QuestDataSerializer._serialize_item_reference(
                            value,
                            path=f"quest_dict.{category}.{quest_id}.Reward[{index}]",
                        )
                        for index, value in enumerate(values)
                    ]
                encoded[quest_id] = record
            serialized[category] = encoded
        return serialized

    @staticmethod
    def _serialize_bounties(quests: dict[str, Any]) -> dict[str, Any]:
        encoded: dict[str, Any] = {}
        for quest_info in quests.values():
            if not isinstance(quest_info, list) or len(quest_info) < 3:
                raise SaveValidationError("quest_dict.Bounty", "expected [data, count, completed]")
            bounty_data = quest_info[0]
            if not isinstance(bounty_data, dict):
                raise SaveValidationError("quest_dict.Bounty.data", "expected an object")
            enemy = bounty_data.get("enemy")
            try:
                enemy_id = ENEMY_TYPES.id_for(enemy)
            except KeyError as exc:
                raise SaveValidationError("quest_dict.Bounty.enemy_id", str(exc)) from exc
            record = dict(bounty_data)
            record["enemy_id"] = enemy_id
            record.pop("enemy", None)
            reward = record.get("reward")
            if reward is not None:
                record["reward"] = QuestDataSerializer._serialize_item_reference(
                    reward, path=f"quest_dict.Bounty.{enemy_id}.reward"
                )
            encoded[enemy_id] = [record, quest_info[1], quest_info[2]]
        return encoded

    @staticmethod
    def deserialize_quest_dict(serialized: dict[str, Any]) -> dict[str, Any]:
        """Reconstruct quest state after validating every persisted identity."""
        if not isinstance(serialized, dict):
            raise SaveValidationError("quest_dict", "expected an object")
        quest_dict: dict[str, Any] = {}
        for category, quests in serialized.items():
            if not isinstance(quests, dict):
                raise SaveValidationError(f"quest_dict.{category}", "expected an object")
            if category == "Bounty":
                quest_dict[category] = QuestDataSerializer._deserialize_bounties(quests)
                continue
            if category not in {"Main", "Side"}:
                quest_dict[category] = dict(quests)
                continue
            decoded: dict[str, Any] = {}
            for quest_id, quest_data in quests.items():
                quest_name = QUEST_NAMES_BY_ID.get(quest_id)
                if quest_name is None:
                    raise SaveValidationError(
                        f"quest_dict.{category}", f"unknown quest id: {quest_id!r}"
                    )
                if not isinstance(quest_data, dict):
                    raise SaveValidationError(
                        f"quest_dict.{category}.{quest_id}", "expected an object"
                    )
                record = dict(quest_data)
                if record.get("Type") == "Collect" and "What" in record:
                    record["What"] = QuestDataSerializer._deserialize_item_reference(
                        record["What"], path=f"quest_dict.{category}.{quest_id}.What"
                    )
                if "Reward" in record:
                    reward = record["Reward"]
                    if not isinstance(reward, list):
                        raise SaveValidationError(
                            f"quest_dict.{category}.{quest_id}.Reward", "expected a list"
                        )
                    record["Reward"] = [
                        QuestDataSerializer._deserialize_item_reference(
                            value,
                            path=f"quest_dict.{category}.{quest_id}.Reward[{index}]",
                        )
                        for index, value in enumerate(reward)
                    ]
                decoded[quest_name] = record
            quest_dict[category] = decoded
        return quest_dict

    @staticmethod
    def _deserialize_bounties(quests: dict[str, Any]) -> dict[str, Any]:
        decoded: dict[str, Any] = {}
        for enemy_id, quest_info in quests.items():
            path = f"quest_dict.Bounty.{enemy_id}"
            if not isinstance(quest_info, list) or len(quest_info) < 3:
                raise SaveValidationError(path, "expected [data, count, completed]")
            if not isinstance(quest_info[0], dict):
                raise SaveValidationError(f"{path}.data", "expected an object")
            try:
                enemy_type = ENEMY_TYPES.resolve(enemy_id)
                enemy = enemy_type()
            except KeyError as exc:
                raise SaveValidationError(path, str(exc)) from exc
            except (TypeError, ValueError) as exc:
                raise SaveValidationError(path, f"could not construct enemy: {exc}") from exc
            record = dict(quest_info[0])
            persisted_enemy_id = record.pop("enemy_id", enemy_id)
            if persisted_enemy_id != enemy_id:
                raise SaveValidationError(f"{path}.enemy_id", "does not match bounty key")
            record["enemy"] = enemy
            if record.get("reward") is not None:
                reward = QuestDataSerializer._deserialize_item_reference(
                    record["reward"], path=f"{path}.reward"
                )
                record["reward"] = type(reward) if isinstance(reward, items.Item) else reward
            decoded[enemy.name] = [record, quest_info[1], quest_info[2]]
        return decoded
