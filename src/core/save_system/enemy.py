"""Enemy state serialization."""

from __future__ import annotations

from typing import TYPE_CHECKING

from ..identity import ENEMY_TYPES
from .errors import SaveValidationError

if TYPE_CHECKING:
    from typing import Any


class EnemyStateSerializer:
    """Serializes/deserializes enemy state (for bosses and key enemies)."""

    @staticmethod
    def serialize(enemy) -> dict[str, Any] | None:
        """Convert enemy to data dictionary."""
        if not enemy:
            return None

        try:
            enemy_id = ENEMY_TYPES.id_for(enemy)
        except KeyError as exc:
            raise SaveValidationError("enemy.enemy_id", str(exc)) from exc

        if isinstance(enemy, type):
            return {"enemy_id": enemy_id, "is_class": True}

        # It's an instance
        return {
            "name": getattr(enemy, "name", "Unknown"),
            "enemy_id": enemy_id,
            "is_class": False,
            "health": {
                "max": getattr(enemy.health, "max", 100) if hasattr(enemy, "health") else 100,
                "current": (
                    getattr(enemy.health, "current", 100) if hasattr(enemy, "health") else 100
                ),
            },
            "mana": {
                "max": getattr(enemy.mana, "max", 0) if hasattr(enemy, "mana") else 0,
                "current": getattr(enemy.mana, "current", 0) if hasattr(enemy, "mana") else 0,
            },
            "alive": enemy.is_alive() if hasattr(enemy, "is_alive") else True,
        }

    @staticmethod
    def deserialize(enemy_data: dict):
        """Reconstruct enemy from data dictionary."""
        if not enemy_data:
            return None

        enemy_id = enemy_data.get("enemy_id")
        if not isinstance(enemy_id, str) or not enemy_id:
            raise SaveValidationError("enemy.enemy_id", "expected a non-empty string")
        try:
            enemy_class = ENEMY_TYPES.resolve(enemy_id)
        except KeyError as exc:
            raise SaveValidationError("enemy.enemy_id", str(exc)) from exc

        # If it was stored as a class, return the class
        if enemy_data.get("is_class"):
            return enemy_class

        # Create instance
        try:
            enemy = enemy_class()
        except (TypeError, ValueError) as exc:
            raise SaveValidationError("enemy", f"could not construct {enemy_id!r}: {exc}") from exc

        # Restore health/mana if present
        if "health" in enemy_data and hasattr(enemy, "health"):
            enemy.health.max = enemy_data["health"]["max"]
            enemy.health.current = enemy_data["health"]["current"]

        if "mana" in enemy_data and hasattr(enemy, "mana"):
            enemy.mana.max = enemy_data["mana"]["max"]
            enemy.mana.current = enemy_data["mana"]["current"]

        return enemy
