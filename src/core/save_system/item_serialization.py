"""Item and ability serialization."""

from __future__ import annotations

import re
from functools import lru_cache
from typing import TYPE_CHECKING

from src.paths import CORE_DATA_DIR

from .. import items
from ..data.ability_loader import AbilityFactory
from ..data.ability_schema import validate_ability_directory
from ..identity import ABILITY_TYPES, ITEM_TYPES
from .errors import SaveValidationError

if TYPE_CHECKING:
    from typing import Any


@lru_cache(maxsize=1)
def _ability_alias_ids() -> dict[str, str]:
    """Return the validated runtime-class alias to canonical ability-ID map."""
    report = validate_ability_directory(require_complete=True)
    if not report.valid:
        details = "; ".join(f"{issue.ability_id}: {issue.message}" for issue in report.issues)
        raise RuntimeError(f"ability identity registry is invalid: {details}")
    return {
        alias: definition.ability_id
        for definition in report.definitions
        for alias in definition.aliases
        if alias.isidentifier()
    }


class ItemSerializer:
    """Serializes items to IDs and names."""

    @staticmethod
    def serialize(item: Any) -> dict[str, Any]:
        """Convert item object to data dict."""
        if item is None or not isinstance(item, items.Item):
            raise SaveValidationError("item", "expected a registered Item instance")

        try:
            item_id = ITEM_TYPES.id_for(item)
        except KeyError as exc:
            raise SaveValidationError("item.item_id", str(exc)) from exc

        data = {
            "item_id": item_id,
            "name": item.name,
            "typ": getattr(item, "typ", "Unknown"),
            "subtyp": getattr(item, "subtyp", "None"),
        }
        if item.__class__.__name__ == "InscribedSpellScroll":
            data["spell_class_name"] = getattr(item, "spell_class_name", "MagicMissile")
            data["charges"] = int(getattr(item, "charges", 1) or 1)
        elif (
            item.__class__.__name__ in {"LockpickKit", "WaterBladder", "ThrowingDaggers"}
            or getattr(item, "subtyp", None) == "Crossbow Bolts"
        ):
            default_charges = (
                10 if item.__class__.__name__ in {"WaterBladder", "ThrowingDaggers"} else 3
            )
            data["charges"] = int(getattr(item, "charges", default_charges))
        return data

    @staticmethod
    def deserialize(data: dict[str, Any], *, path: str = "item") -> Any:
        """Reconstruct item from data dict."""
        if not isinstance(data, dict):
            raise SaveValidationError(path, "expected an object")
        item_id = data.get("item_id")
        if not isinstance(item_id, str) or not item_id:
            raise SaveValidationError(f"{path}.item_id", "expected a non-empty string")
        try:
            item_class = ITEM_TYPES.resolve(item_id)
        except KeyError as exc:
            raise SaveValidationError(f"{path}.item_id", str(exc)) from exc

        try:
            if item_id == "inscribed_spell_scroll":
                spell_class_name = data.get("spell_class_name")
                if not isinstance(spell_class_name, str) or not spell_class_name:
                    raise SaveValidationError(
                        f"{path}.spell_class_name", "expected a non-empty string"
                    )
                return item_class(spell_class_name, charges=data.get("charges"))
            if (
                item_id in {"lockpick_kit", "water_bladder", "throwing_daggers"}
                or data.get("subtyp") == "Crossbow Bolts"
            ):
                default_charges = 10 if item_id in {"water_bladder", "throwing_daggers"} else 3
                return item_class(charges=data.get("charges", default_charges))
            return item_class()
        except SaveValidationError:
            raise
        except (TypeError, ValueError) as exc:
            raise SaveValidationError(path, f"could not construct {item_id!r}: {exc}") from exc


class AbilitySerializer:
    """Serializes abilities exclusively by stable slug."""

    @staticmethod
    def serialize(ability: Any) -> str:
        """Convert an ability to its canonical slug."""
        if ability is None:
            return ""
        from ..abilities.catalog import ensure_catalog_ability_identity

        ensure_catalog_ability_identity(ability)
        ability_id = getattr(ability, "ability_id", None)
        if not ability_id:
            runtime_name = str(getattr(ability, "_class_name", ability.__class__.__name__))
            ability_id = _ability_alias_ids().get(runtime_name)
        if not ability_id:
            try:
                ability_id = ABILITY_TYPES.id_for(ability)
            except KeyError:
                ability_id = None
        if not isinstance(ability_id, str) or not ability_id:
            raise SaveValidationError("ability", "ability has no canonical identity")
        return ability_id

    @staticmethod
    def deserialize(name: str) -> Any | None:
        """Reconstruct an ability from its canonical slug."""
        if not name:
            return None

        from ..abilities.catalog import catalog_ability_from_id

        catalog_ability = catalog_ability_from_id(name)
        if catalog_ability is not None:
            return catalog_ability

        if not re.fullmatch(r"[a-z][a-z0-9_]*", name):
            raise SaveValidationError("ability", f"invalid ability id: {name!r}")
        yaml_path = CORE_DATA_DIR / "abilities" / f"{name}.yaml"
        try:
            if yaml_path.is_file():
                return AbilityFactory.create_from_yaml(yaml_path)
            ability_type = ABILITY_TYPES.resolve(name)
            return ability_type()
        except KeyError as exc:
            raise SaveValidationError("ability", f"unknown ability id: {name!r}") from exc
        except (TypeError, ValueError) as exc:
            raise SaveValidationError("ability", f"could not construct {name!r}: {exc}") from exc
