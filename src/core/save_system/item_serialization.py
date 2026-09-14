"""Item and ability serialization."""

from __future__ import annotations

import re
from functools import lru_cache
from typing import TYPE_CHECKING

from src.paths import CORE_DATA_DIR

from .. import abilities, items
from ..data.ability_loader import AbilityFactory
from ..data.ability_schema import validate_ability_directory

if TYPE_CHECKING:
    from typing import Any


@lru_cache(maxsize=1)
def _ability_identity_maps() -> tuple[dict[str, str], dict[str, tuple[str, ...]]]:
    """Return validated legacy-token-to-slug and slug-to-alias maps."""
    report = validate_ability_directory(require_complete=True)
    if not report.valid:
        details = "; ".join(f"{issue.ability_id}: {issue.message}" for issue in report.issues)
        raise RuntimeError(f"ability identity registry is invalid: {details}")
    aliases_to_ids: dict[str, str] = {}
    ids_to_aliases: dict[str, tuple[str, ...]] = {}
    for definition in report.definitions:
        ids_to_aliases[definition.ability_id] = definition.aliases
        for alias in definition.aliases:
            if alias.isidentifier():
                aliases_to_ids[alias] = definition.ability_id
    return aliases_to_ids, ids_to_aliases


class ItemSerializer:
    """Serializes items to IDs and names."""

    @staticmethod
    def serialize(item: Any) -> dict[str, Any]:
        """Convert item object to data dict."""
        if item is None or not hasattr(item, "name"):
            return {"name": "None", "typ": "None", "subtyp": "None"}

        data = {
            "name": item.name,
            "typ": getattr(item, "typ", "Unknown"),
            "subtyp": getattr(item, "subtyp", "None"),
            "class": item.__class__.__name__,
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
    def deserialize(data: dict[str, Any]) -> Any:
        """Reconstruct item from data dict."""
        # Normalize typ for Accessory items (Ring/Pendant)
        typ = data.get("typ", "Weapon")
        if typ == "Accessory":
            # Determine if Ring or Pendant from class name
            class_name = data.get("class", "")
            if "Ring" in class_name:
                typ = "Ring"
            elif "Pendant" in class_name:
                typ = "Pendant"
            else:
                typ = "Ring"  # Default to Ring

        if data.get("name") == "None" or data.get("subtyp") == "None":
            return items.remove_equipment(typ)

        # Try to find and instantiate the item class
        item_class_name = data.get("class")
        if item_class_name and hasattr(items, item_class_name):
            try:
                item_class = getattr(items, item_class_name)
                # Don't try to instantiate abstract base classes
                if item_class_name not in [
                    "Item",
                    "Weapon",
                    "OffHand",
                    "Armor",
                    "Helmet",
                    "Accessory",
                ]:
                    if item_class_name == "InscribedSpellScroll":
                        return item_class(
                            data.get("spell_class_name", "MagicMissile"),
                            charges=data.get("charges"),
                        )
                    if (
                        item_class_name in {"LockpickKit", "WaterBladder", "ThrowingDaggers"}
                        or data.get("subtyp") == "Crossbow Bolts"
                    ):
                        default_charges = (
                            10 if item_class_name in {"WaterBladder", "ThrowingDaggers"} else 3
                        )
                        return item_class(charges=data.get("charges", default_charges))
                    return item_class()
            except Exception:
                pass

        # Fallback: create empty equipment
        return items.remove_equipment(typ)


class AbilitySerializer:
    """Serializes YAML abilities by stable slug with legacy read adapters."""

    @staticmethod
    def serialize(ability: Any) -> str:
        """Convert an ability to its canonical slug or legacy class token."""
        if ability is None:
            return ""
        from ..abilities.catalog import ensure_catalog_ability_identity

        ensure_catalog_ability_identity(ability)
        if getattr(ability, "ability_id", None):
            return str(ability.ability_id)
        legacy_token = str(getattr(ability, "_class_name", ability.__class__.__name__))
        aliases_to_ids, _ = _ability_identity_maps()
        return aliases_to_ids.get(legacy_token, legacy_token)

    @staticmethod
    def deserialize(name: str) -> Any | None:
        """Reconstruct an ability from a slug, class token, or display name.

        Supports:
        - Canonical slugs: 'heal_2' (preferred)
        - Class names: 'Heal', 'Heal2', 'Heal3' (unambiguous)
        - Display names: 'Heal' (ambiguous, returns first match)
        """
        if not name:
            return None

        from ..abilities.catalog import catalog_ability_from_id

        catalog_ability = catalog_ability_from_id(name)
        if catalog_ability is not None:
            return catalog_ability

        if re.fullmatch(r"[a-z][a-z0-9_]*", name):
            yaml_path = CORE_DATA_DIR / "abilities" / f"{name}.yaml"
            if yaml_path.is_file():
                _, ids_to_aliases = _ability_identity_maps()
                for alias in ids_to_aliases.get(name, ()):
                    if alias.isidentifier() and hasattr(abilities, alias):
                        try:
                            ability = getattr(abilities, alias)()
                            if getattr(ability, "ability_id", None) is None:
                                ability.ability_id = name
                            return ability
                        except Exception:
                            continue
                return AbilityFactory.create_from_yaml(yaml_path)

        # Temporary compatibility adapter for version-1 development saves.
        if hasattr(abilities, name):
            try:
                attr = getattr(abilities, name)
                if hasattr(attr, "__call__"):
                    return attr()
            except Exception:
                pass

        # Fallback to display name lookup (may be ambiguous)
        for attr_name in dir(abilities):
            attr = getattr(abilities, attr_name)
            if hasattr(attr, "__call__"):
                try:
                    instance = attr()
                    if hasattr(instance, "name") and instance.name == name:
                        return instance
                except Exception:
                    pass

        return None
