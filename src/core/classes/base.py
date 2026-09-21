"""Base class definitions for player jobs."""

from __future__ import annotations

from textwrap import wrap

from .. import items
from ..identity import CLASS_TYPES


class Job:
    """
    Base definition for the class.
    *_plus describe the bonus at first level for each class (5 -> 6 -> 7 gain).
    equipment lists the items the player_char starts out with for the selected base class.
    restrictions list the allowable item types the class can equip.
    """

    class_id: str

    def __init_subclass__(cls, *, class_id: str | None = None, **kwargs: object) -> None:
        """Register every job type at definition time for strict persistence."""
        super().__init_subclass__(**kwargs)
        cls.class_id = CLASS_TYPES.register(cls, class_id)

    def __init__(
        self,
        name: str,
        description: str,
        str_plus: int,
        int_plus: int,
        wis_plus: int,
        con_plus: int,
        cha_plus: int,
        dex_plus: int,
        att_plus: int,
        def_plus: int,
        magic_plus: int,
        magic_def_plus: int,
        equipment: dict[str, items.Item] | None = None,
        restrictions: dict[str, list[str]] | None = None,
        pro_level: int = 1,
    ):
        self.name = name
        self.description = "\n".join(wrap(description, 75, break_on_hyphens=False))
        self.str_plus = str_plus
        self.int_plus = int_plus
        self.wis_plus = wis_plus
        self.con_plus = con_plus
        self.cha_plus = cha_plus
        self.dex_plus = dex_plus
        self.att_plus = att_plus
        self.def_plus = def_plus
        self.magic_plus = magic_plus
        self.magic_def_plus = magic_def_plus
        self.equipment = dict(equipment or {})
        self.restrictions = restrictions or {}
        self.equipment.setdefault("Weapon", items.NoWeapon())
        self.equipment.setdefault("OffHand", items.NoOffHand())
        self.equipment.setdefault("Armor", items.NoArmor())
        self.equipment.setdefault("Helmet", items.NoHelmet())
        self.equipment.setdefault("Ring", items.NoRing())
        self.equipment.setdefault("Pendant", items.NoPendant())
        if "Helmet" not in self.restrictions:
            self.restrictions["Helmet"] = list(self.restrictions.get("Armor", []))
        self.pro_level = pro_level

    def equip_check(self, item: items.Item | type[items.Item], equip_slot: str) -> bool:
        """
        Checks if the class allows the item type to be equipped
        """

        item = item if type(item) is not type else item()
        if equip_slot in ["Ring", "Pendant"]:
            if item.subtyp == equip_slot:
                return True
            return False
        if item.subtyp in self.restrictions[equip_slot]:
            if self.name in getattr(item, "restricted_against", []):
                return False
            if item.restriction:
                if self.name not in item.restriction:
                    return False
            return True
        return False
