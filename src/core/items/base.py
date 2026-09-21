"""Shared item base types and presentation metadata helpers."""

from __future__ import annotations

from textwrap import wrap
from typing import TYPE_CHECKING

from ..identity import ITEM_TYPES

if TYPE_CHECKING:
    from typing import Any

    from ..character import Character
    from ..combat.combat_result import CombatResultGroup


_STAT_THEME_PREFIXES = {
    "strength": "Mighty",
    "intelligence": "Arcane",
    "wisdom": "Sage",
    "constitution": "Stalwart",
    "charisma": "Fortunate",
    "dexterity": "Swift",
    "resistance": "Warded",
}


def stat_theme_for_item(item: object) -> str | None:
    """Infer the primary stat theme for an item without mutating it."""
    explicit_theme = getattr(item, "stat_theme", None)
    if explicit_theme:
        return str(explicit_theme)

    name = str(getattr(item, "name", ""))
    mod = str(getattr(item, "mod", ""))
    subtyp = str(getattr(item, "subtyp", ""))
    typ = str(getattr(item, "typ", ""))

    if "Strength" in name or "Physical Damage" in mod:
        return "strength"
    if "Intelligence" in name or "Magic Damage" in mod or subtyp in {"Staff", "Tome", "Rod"}:
        return "intelligence"
    if "Wisdom" in name or "Magic Defense" in mod or "Status-" in mod:
        return "wisdom"
    if "Constitution" in name or "Physical Defense" in mod or typ in {"Armor", "Helmet"}:
        return "constitution"
    if "Charisma" in name or "Luck" in mod:
        return "charisma"
    if (
        "Dexterity" in name
        or mod in {"Accuracy", "Dodge"}
        or subtyp in {"Dagger", "Ninja Blade", "Crossbow"}
    ):
        return "dexterity"
    if "Resist-" in mod or getattr(item, "element", None):
        return "resistance"
    if typ == "Weapon" and getattr(item, "damage", 0):
        return "strength"
    return None


def stat_themed_item_name(item: object) -> str:
    """Return a generated display name that reflects the item's stat theme."""
    name = str(getattr(item, "name", "Unknown Item"))
    theme = stat_theme_for_item(item)
    prefix = _STAT_THEME_PREFIXES.get(theme or "")
    if not prefix or name.startswith(f"{prefix} "):
        return name
    return f"{prefix} {name}"


def item_metadata_lines(item: object) -> list[str]:
    """Return concise presentation metadata for item descriptions."""
    lines: list[str] = []

    element = getattr(item, "element", None)
    if element:
        lines.append(f"Element: {element}")

    name = str(getattr(item, "name", "") or "")
    if name == "Svalinn":
        lines.append("Resistance: Fire +25%")
    if name == "Palangina":
        lines.append("Resistance: Fire +25%, Water +25%")

    resist_mod = getattr(item, "resist_mod", None)
    if resist_mod is not None and element:
        try:
            percent = int(float(resist_mod) * 100)
        except (TypeError, ValueError):
            percent = 0
        if percent:
            lines.append(f"Resistance: {element} +{percent}%")

    mod = str(getattr(item, "mod", "") or "")
    if mod.startswith("Resist-"):
        lines.append(f"Resistance: {mod.removeprefix('Resist-')} +50%")
    elif mod.startswith("Immune-"):
        lines.append(f"Immunity: {mod.removeprefix('Immune-')}")

    return lines


class Item:
    """
    name: name of the item
    description: description of the item
    value: price in gold; sale price will be half this amount
    rarity: represented as a value between 0 and 1 and indicates the chance of dropping
    subtyp: the subtype of the item (i.e. Sword would be a subtype of Weapon)
    """

    item_id: str

    def __init_subclass__(cls, *, item_id: str | None = None, **kwargs: object) -> None:
        """Register every item type at definition time for strict persistence."""
        super().__init_subclass__(**kwargs)
        cls.item_id = ITEM_TYPES.register(cls, item_id)

    def __init__(self, name: str, description: str, value: int, rarity: float, subtyp: str) -> None:
        self.name = name
        self.description = "\n".join(wrap(description, 35, break_on_hyphens=False))
        self.value = value
        self.rarity = rarity
        self.subtyp = subtyp
        self.mod = 0
        self.weight = 0
        self.restriction = []
        self.restricted_against = []
        self.ultimate = False

    def __str__(self) -> str:
        return (
            f"{'=' * ((35 - len(self.name)) // 2)}{self.name}{'=' * ((36 - len(self.name)) // 2)}\n"
            f"{self.description}\n"
            f"{35*'-'}\n"
            f"Sub-type: {'Special' if 'Summon' in self.subtyp else self.subtyp}\n"
            f"{35*'='}"
        )

    def use(self, user: Character, target: Character | None = None, tile: Any = None) -> str:
        return ""

    def special_effect(self, results: CombatResultGroup) -> None:
        return


class Weapon(Item):
    """
    Subclass of the Item class
    damage: the base damage for each weapon
    crit: legacy storage for critical-hit chance as a 0..1 ratio
    crit_chance: preferred alias for critical-hit chance as a 0..1 ratio
    handed: identifies weapon as 1-handed or 2-handed; 2-handed weapons prohibit the ability to use a shield
    unequip: boolean parameter indicating whether the object the base class used when an item is unequipped
    off: whether the weapon can be equipped in the offhand
    typ: the item type; 'Weapon' for this class
    disarm: boolean indicating whether the weapon can be disarmed; default is True
    ignore: boolean indicating whether the weapon automatically ignores armor when calculating damage
    """

    def __init__(
        self,
        name: str,
        description: str,
        value: int,
        rarity: float,
        damage: int,
        crit: float | None,
        handed: int,
        subtyp: str,
        unequip: bool,
        off: bool,
        *,
        crit_chance: float | None = None,
    ) -> None:
        super().__init__(name, description, value, rarity, subtyp)
        self.damage = damage
        self.crit = crit if crit_chance is None else crit_chance
        self.handed = handed
        self.unequip = unequip
        self.off = off
        self.typ = "Weapon"
        self.disarm = True
        if subtyp == "Fist":
            self.disarm = False
        self.ignore = False
        self.element = None

    @property
    def crit_chance(self) -> float:
        """Critical-hit chance as a 0..1 ratio."""
        return self.crit

    @crit_chance.setter
    def crit_chance(self, value: float) -> None:
        self.crit = value

    def __str__(self) -> str:
        return (
            f"{'=' * ((35 - len(self.name)) // 2)}{self.name}{'=' * ((36 - len(self.name)) // 2)}\n"
            f"{self.description}\n"
            f"{35*'-'}\n"
            f"Type: {self.subtyp}\n"
            f"{self.handed}-handed\n"
            f"Damage: {self.damage}\n"
            f"Critical Chance: {int(self.crit_chance * 100)}%\n"
            f"Weight: {self.weight}\n"
            f"{35*'='}"
        )

    def special_effect(self, results: CombatResultGroup) -> None:
        return


class Armor(Item):
    """
    armor: base armor for the item
    unequip: boolean parameter indicating whether the object the base class used when an item is unequipped
    typ: the item type; 'Armor' for this class
    """

    def __init__(
        self,
        name: str,
        description: str,
        value: int,
        rarity: float,
        armor: int,
        subtyp: str,
        unequip: bool,
    ) -> None:
        super().__init__(name, description, value, rarity, subtyp)
        self.armor = armor
        self.unequip = unequip
        self.typ = "Armor"
        self.element = None

    def __str__(self) -> str:
        return (
            f"{'=' * ((35 - len(self.name)) // 2)}{self.name}{'=' * ((36 - len(self.name)) // 2)}\n"
            f"{self.description}\n"
            f"{35*'-'}\n"
            f"Type: {self.subtyp}\n"
            f"Armor: {self.armor}\n"
            f"Weight: {self.weight}\n"
            f"{35*'='}"
        )


class Helmet(Armor):
    """Head-slot armor that contributes to the normal Defense modifier."""

    def __init__(
        self,
        name: str,
        description: str,
        value: int,
        rarity: float,
        armor: int,
        subtyp: str,
        unequip: bool,
    ) -> None:
        super().__init__(name, description, value, rarity, armor, subtyp, unequip)
        self.typ = "Helmet"

    def special_effect(self, results: CombatResultGroup) -> None:
        return


class OffHand(Item):
    """
    mod: stat depends on the off-hand item; mod for shields is block and spell damage modifier for tomes
        block: determines block chance, calculated as 1 / mod parameter (i.e. 1/2 or 50%)
        spell damage: base attack spell modifier
    unequip: boolean parameter indicating whether the object the base class used when an item is unequipped
    typ: the item type; 'OffHand' for this class
    """

    def __init__(
        self,
        name: str,
        description: str,
        value: int,
        rarity: float,
        mod: float,
        subtyp: str,
        unequip: bool,
    ) -> None:
        super().__init__(name, description, value, rarity, subtyp)
        self.mod = mod
        self.unequip = unequip
        self.typ = "OffHand"

    def __str__(self) -> str:
        if self.subtyp == "Shield":
            return (
                f"{'=' * ((35 - len(self.name)) // 2)}{self.name}{'=' * ((36 - len(self.name)) // 2)}\n"
                f"{self.description}\n"
                f"{35*'-'}\n"
                f"Type: {self.subtyp}\n"
                f"Block: {int(self.mod * 100)}%\n"
                f"Weight: {self.weight}\n"
                f"{35*'='}"
            )
        if self.subtyp == "Crossbow":
            return (
                f"{'=' * ((35 - len(self.name)) // 2)}{self.name}{'=' * ((36 - len(self.name)) // 2)}\n"
                f"{self.description}\n"
                f"{35*'-'}\n"
                f"Type: {self.subtyp}\n"
                f"Damage: {self.damage}\n"
                f"Weight: {self.weight}\n"
                f"{35*'='}"
            )
        return (
            f"{'=' * ((35 - len(self.name)) // 2)}{self.name}{'=' * ((36 - len(self.name)) // 2)}\n"
            f"{self.description}\n"
            f"{35*'-'}\n"
            f"Type: {self.subtyp}\n"
            f"Spell Damage Mod: {self.mod}\n"
            f"Weight: {self.weight}\n"
            f"{35*'='}"
        )


class Accessory(Item):
    """
    Each character can equip 1 ring and 1 pendant
    Rings improve physical capabilities (either attack or defense)
    Pendants improve magical capabilities (either magic damage or defense)
    All modifications are considered magical and can't be ignored
    mod: defines the specific mod for each item; string that will be parsed later
    unequip: boolean parameter indicating whether the object the base class used when an item is unequipped
    typ: the item type; 'Accessory' for this class
    """

    def __init__(
        self,
        name: str,
        description: str,
        value: int,
        rarity: float,
        mod: str,
        subtyp: str,
        unequip: bool,
    ) -> None:
        super().__init__(name, description, value, rarity, subtyp)
        self.mod = mod
        self.unequip = unequip
        self.typ = "Accessory"

    def __str__(self) -> str:
        return (
            f"{'=' * ((35 - len(self.name)) // 2)}{self.name}{'=' * ((36 - len(self.name)) // 2)}\n"
            f"{self.description}\n"
            f"{35*'-'}\n"
            f"Mod: {self.mod}\n"
            f"Weight: {self.weight}\n"
            f"{35*'='}"
        )


class Potion(Item):
    """
    typ: the item type; 'Potion' for this class
    """

    def __init__(self, name: str, description: str, value: int, rarity: float, subtyp: str) -> None:
        super().__init__(name, description, value, rarity, subtyp)
        self.typ = "Potion"
        self.weight = 0.1

    def __str__(self) -> str:
        return (
            f"{'=' * ((35 - len(self.name)) // 2)}{self.name}{'=' * ((36 - len(self.name)) // 2)}\n"
            f"{self.description}\n"
            f"{35*'-'}\n"
            f"Weight: {self.weight}\n"
            f"{35*'='}"
        )


class Misc(Item):
    """
    typ: the item type; 'Misc' for this class
    """

    def __init__(self, name: str, description: str, value: int, rarity: float, subtyp: str) -> None:
        super().__init__(name, description, value, rarity, subtyp)
        self.typ = "Misc"
