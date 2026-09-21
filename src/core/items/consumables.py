"""Potion and consumable implementations."""

from __future__ import annotations

from textwrap import wrap
from typing import TYPE_CHECKING

from src.core.randomness import gameplay_random as random

from .base import Potion

if TYPE_CHECKING:
    from typing import Any

    from ..character import Character


def _hold_magical_thirst(user: Character) -> None:
    """Let a consumed drink postpone Polydipsia for one turn."""
    from .. import persistent_afflictions as afflictions

    if afflictions.has_curse(user, "Polydipsia"):
        afflictions.ensure_curses(user)["Polydipsia"]["held_turns"] = 1


class HealthPotion(Potion):

    def __init__(self):
        super().__init__(
            name="Health Potion",
            description="A potion that restores up to 25% of your health.",
            value=100,
            rarity=0.99,
            subtyp="Health",
        )
        self.percent = 0.25
        self.minimum_heal = 25

    def _base_heal_amount(self, user: Character) -> int:
        return max(int(getattr(self, "minimum_heal", 0) or 0), int(user.health.max * self.percent))

    def use(self, user: Character, target: Character | None = None, tile: Any = None) -> str:
        use_str = ""
        if user.health.current == user.health.max:
            use_str += "You are already at full health.\n"
            return use_str
        user.modify_inventory(self, subtract=True)
        # Dwarf Temperance/Gluttony: combat consumables are stronger, but may cause hangover.
        is_dwarf = getattr(getattr(user, "race", None), "name", None) == "Dwarf"
        if user.state != "fight":
            # Out of combat: 80-110% of base amount for variance and improved usefulness
            base_heal = self._base_heal_amount(user)
            heal = int(random.uniform(0.8, 1.1) * base_heal)
        else:
            # In combat: 50-100% with luck modifier
            rand_heal = self._base_heal_amount(user)
            heal_cap = max(1, rand_heal)
            heal_floor = min(heal_cap, int(getattr(self, "minimum_heal", 0) or 0))
            heal = random.randint(rand_heal // 2, rand_heal) * max(
                1, user.check_mod("luck", luck_factor=12)
            )
            heal = max(min(heal, heal_cap), heal_floor)
        if is_dwarf:
            from ..constants import (
                DWARF_COMBAT_CONSUMABLE_MULTIPLIER,
                DWARF_HANGOVER_COMBAT_DURATION,
                DWARF_HANGOVER_MAX_STEPS,
                DWARF_HANGOVER_STEPS_PER_USE,
            )

            heal = int(heal * DWARF_COMBAT_CONSUMABLE_MULTIPLIER)
            if user.state == "fight":
                h = user.status_effects.get("Hangover")
                if h is not None:
                    h.active = True
                    h.duration = max(int(h.duration or 0), DWARF_HANGOVER_COMBAT_DURATION)
            else:
                user.dwarf_hangover_steps = min(
                    DWARF_HANGOVER_MAX_STEPS,
                    int(getattr(user, "dwarf_hangover_steps", 0) or 0)
                    + DWARF_HANGOVER_STEPS_PER_USE,
                )
        use_str += f"The potion healed you for {heal} life.\n"
        user.health.current += heal
        if user.health.current >= user.health.max:
            user.health.current = user.health.max
            use_str += "You are at max health.\n"
        _hold_magical_thirst(user)
        return use_str


class GreatHealthPotion(HealthPotion):

    def __init__(self):
        super().__init__()
        self.name = "Great Health Potion"
        self.description = "\n".join(
            wrap("A potion that restores up to 50% of your health.", 35, break_on_hyphens=False)
        )
        self.value = 600
        self.rarity = 0.7
        self.percent = 0.50
        self.minimum_heal = 60


class SuperHealthPotion(HealthPotion):

    def __init__(self):
        super().__init__()
        self.name = "Super Health Potion"
        self.description = "\n".join(
            wrap("A potion that restores up to 75% of your health.", 35, break_on_hyphens=False)
        )
        self.value = 3000
        self.rarity = 0.5
        self.percent = 0.75
        self.minimum_heal = 120


class MasterHealthPotion(HealthPotion):

    def __init__(self):
        super().__init__()
        self.name = "Master Health Potion"
        self.description = "\n".join(
            wrap("A potion that restores up to 100% of your health.", 35, break_on_hyphens=False)
        )
        self.value = 10000
        self.rarity = 0.3
        self.percent = 1.0
        self.minimum_heal = 250


class ManaPotion(Potion):

    def __init__(self):
        super().__init__(
            name="Mana Potion",
            description="A potion that restores up to 25% of your mana.",
            value=250,
            rarity=0.9,
            subtyp="Mana",
        )
        self.percent = 0.25

    def use(self, user: Character, target: Character | None = None, tile: Any = None) -> str:
        use_str = ""
        if user.mana.current == user.mana.max:
            use_str += "You are already at full mana.\n"
            return use_str
        user.modify_inventory(self, subtract=True)
        is_dwarf = getattr(getattr(user, "race", None), "name", None) == "Dwarf"
        if user.state != "fight":
            # Out of combat: 80-110% of base amount for variance and improved usefulness
            base_heal = int(user.mana.max * self.percent)
            heal = int(random.uniform(0.8, 1.1) * base_heal)
        else:
            # In combat: 50-100% with luck modifier
            rand_res = int(user.mana.max * self.percent)
            heal = random.randint(rand_res // 2, rand_res) * max(
                1, user.check_mod("luck", luck_factor=12)
            )
        if is_dwarf:
            from ..constants import (
                DWARF_COMBAT_CONSUMABLE_MULTIPLIER,
                DWARF_HANGOVER_COMBAT_DURATION,
                DWARF_HANGOVER_MAX_STEPS,
                DWARF_HANGOVER_STEPS_PER_USE,
            )

            heal = int(heal * DWARF_COMBAT_CONSUMABLE_MULTIPLIER)
            if user.state == "fight":
                h = user.status_effects.get("Hangover")
                if h is not None:
                    h.active = True
                    h.duration = max(int(h.duration or 0), DWARF_HANGOVER_COMBAT_DURATION)
            else:
                user.dwarf_hangover_steps = min(
                    DWARF_HANGOVER_MAX_STEPS,
                    int(getattr(user, "dwarf_hangover_steps", 0) or 0)
                    + DWARF_HANGOVER_STEPS_PER_USE,
                )
        use_str += f"The potion restored {heal} mana points.\n"
        user.mana.current += heal
        if user.mana.current >= user.mana.max:
            user.mana.current = user.mana.max
            use_str += "You are at full mana.\n"
        _hold_magical_thirst(user)
        return use_str


class GreatManaPotion(ManaPotion):

    def __init__(self):
        super().__init__()
        self.name = "Great Mana Potion"
        self.description = "\n".join(
            wrap("A potion that restores up to 50% of your mana.", 35, break_on_hyphens=False)
        )
        self.value = 1500
        self.rarity = 0.45
        self.percent = 0.50


class SuperManaPotion(ManaPotion):

    def __init__(self):
        super().__init__()
        self.name = "Super Mana Potion"
        self.description = "\n".join(
            wrap("A potion that restores up to 75% of your mana.", 35, break_on_hyphens=False)
        )
        self.value = 8000
        self.rarity = 0.3
        self.percent = 0.75


class MasterManaPotion(ManaPotion):

    def __init__(self):
        super().__init__()
        self.name = "Master Mana Potion"
        self.description = "\n".join(
            wrap("A potion that restores up to 100% of your mana.", 35, break_on_hyphens=False)
        )
        self.value = 35000
        self.rarity = 0.15
        self.percent = 1.0


class Elixir(Potion):

    def __init__(self):
        super().__init__(
            name="Elixir",
            description="A potion that restores up to 50% of your health and mana.",
            value=20000,
            rarity=0.2,
            subtyp="Elixir",
        )
        self.percent = 0.5

    def use(self, user: Character, target: Character | None = None, tile: Any = None) -> str:
        use_str = ""
        if user.health.current == user.health.max and user.mana.current == user.mana.max:
            use_str += "You are already at full health and mana.\n"
            return use_str
        user.modify_inventory(self, subtract=True)
        is_dwarf = getattr(getattr(user, "race", None), "name", None) == "Dwarf"
        if user.state != "fight":
            health_heal = int(user.health.max * self.percent)
            mana_heal = int(user.mana.max * self.percent)
        else:
            rand_heal = int(user.health.max * self.percent)
            rand_res = int(user.mana.max * self.percent)
            health_heal = random.randint(rand_heal // 2, rand_heal) * max(
                1, user.check_mod("luck", luck_factor=12)
            )
            mana_heal = random.randint(rand_res // 2, rand_res) * max(
                1, user.check_mod("luck", luck_factor=12)
            )
        if is_dwarf:
            from ..constants import (
                DWARF_COMBAT_CONSUMABLE_MULTIPLIER,
                DWARF_HANGOVER_COMBAT_DURATION,
                DWARF_HANGOVER_MAX_STEPS,
                DWARF_HANGOVER_STEPS_PER_USE,
            )

            health_heal = int(health_heal * DWARF_COMBAT_CONSUMABLE_MULTIPLIER)
            mana_heal = int(mana_heal * DWARF_COMBAT_CONSUMABLE_MULTIPLIER)
            if user.state == "fight":
                h = user.status_effects.get("Hangover")
                if h is not None:
                    h.active = True
                    h.duration = max(int(h.duration or 0), DWARF_HANGOVER_COMBAT_DURATION)
            else:
                user.dwarf_hangover_steps = min(
                    DWARF_HANGOVER_MAX_STEPS,
                    int(getattr(user, "dwarf_hangover_steps", 0) or 0)
                    + DWARF_HANGOVER_STEPS_PER_USE,
                )
        use_str += f"The potion restored {health_heal} health points and {mana_heal} mana points.\n"
        user.health.current += health_heal
        user.mana.current += mana_heal
        if user.health.current >= user.health.max:
            user.health.current = user.health.max
            use_str += "You are at max health.\n"
        if user.mana.current >= user.mana.max:
            user.mana.current = user.mana.max
            use_str += "You are at full mana.\n"
        _hold_magical_thirst(user)
        return use_str


class Megalixir(Elixir):

    def __init__(self):
        super().__init__()
        self.name = "Megalixir"
        self.description = "\n".join(
            wrap(
                "A potion that restores up to 100% of your health and mana.",
                35,
                break_on_hyphens=False,
            )
        )
        self.value = 50000
        self.rarity = 0.05
        self.percent = 1.0


class HPPotion(Potion):

    def __init__(self):
        super().__init__(
            name="HP Potion",
            description="A potion that permanently increases your max health by 10.",
            value=10000,
            rarity=0.7,
            subtyp="Stat",
        )
        self.mod = 10

    def use(
        self,
        user: Character,
        target: Character | None = None,
        tile: Any = None,
    ) -> str:
        user.modify_inventory(self, subtract=True)
        user.health.max += self.mod
        if user.in_town():
            user.health.current = user.health.max
        use_str = f"{user.name}'s HP has increased by {self.mod}!\n"
        return use_str


class MPPotion(Potion):

    def __init__(self):
        super().__init__(
            name="MP Potion",
            description="A potion that permanently increases your max mana by 10.",
            value=15000,
            rarity=0.6,
            subtyp="Stat",
        )
        self.mod = 10

    def use(
        self,
        user: Character,
        target: Character | None = None,
        tile: Any = None,
    ) -> str:
        user.modify_inventory(self, subtract=True)
        user.mana.max += self.mod
        if user.in_town():
            user.mana.current = user.mana.max
        use_str = f"{user.name}'s MP has increased by {self.mod}!\n"
        return use_str


class StrengthPotion(Potion):

    def __init__(self):
        super().__init__(
            name="Strength Potion",
            description="A potion that permanently increases your strength by 1.",
            value=50000,
            rarity=0.3,
            subtyp="Stat",
        )

    def use(
        self,
        user: Character,
        target: Character | None = None,
        tile: Any = None,
    ) -> str:
        user.modify_inventory(self, subtract=True)
        user.stats.strength += 1
        use_str = f"{user.name}'s strength has increased by 1!\n"
        return use_str


class IntelPotion(Potion):

    def __init__(self):
        super().__init__(
            name="Intelligence Potion",
            description="A potion that permanently increases your intelligence" " by 1.",
            value=50000,
            rarity=0.3,
            subtyp="Stat",
        )

    def use(
        self,
        user: Character,
        target: Character | None = None,
        tile: Any = None,
    ) -> str:
        user.modify_inventory(self, subtract=True)
        user.stats.intel += 1
        use_str = f"{user.name}'s intelligence has increased by 1!\n"
        return use_str


class WisdomPotion(Potion):

    def __init__(self):
        super().__init__(
            name="Wisdom Potion",
            description="A potion that permanently increases your wisdom by 1.",
            value=50000,
            rarity=0.3,
            subtyp="Stat",
        )

    def use(
        self,
        user: Character,
        target: Character | None = None,
        tile: Any = None,
    ) -> str:
        user.modify_inventory(self, subtract=True)
        user.stats.wisdom += 1
        use_str = f"{user.name}'s wisdom has increased by 1!\n"
        return use_str


class ConPotion(Potion):

    def __init__(self):
        super().__init__(
            name="Constitution Potion",
            description="A potion that permanently increases your constitution" " by 1.",
            value=50000,
            rarity=0.3,
            subtyp="Stat",
        )

    def use(
        self,
        user: Character,
        target: Character | None = None,
        tile: Any = None,
    ) -> str:
        user.modify_inventory(self, subtract=True)
        user.stats.con += 1
        use_str = f"{user.name}'s constitution has increased by 1!\n"
        return use_str


class CharismaPotion(Potion):

    def __init__(self):
        super().__init__(
            name="Charisma Potion",
            description="A potion that permanently increases your charisma by 1.",
            value=50000,
            rarity=0.3,
            subtyp="Stat",
        )

    def use(
        self,
        user: Character,
        target: Character | None = None,
        tile: Any = None,
    ) -> str:
        user.modify_inventory(self, subtract=True)
        user.stats.charisma += 1
        use_str = f"{user.name}'s charisma has increased by 1!\n"
        return use_str


class DexterityPotion(Potion):

    def __init__(self):
        super().__init__(
            name="Dexterity Potion",
            description="A potion that permanently increases your dexterity by " "1.",
            value=50000,
            rarity=0.3,
            subtyp="Stat",
        )

    def use(
        self,
        user: Character,
        target: Character | None = None,
        tile: Any = None,
    ) -> str:
        user.modify_inventory(self, subtract=True)
        user.stats.dex += 1
        use_str = f"{user.name}'s dexterity has increased by 1!\n"
        return use_str


class AardBeing(Potion):

    def __init__(self):
        super().__init__(
            name="Aard of Being",
            description="A potion that permanently increases all stats by 1.",
            value=250000,
            rarity=0.01,
            subtyp="Stat",
        )

    def use(
        self,
        user: Character,
        target: Character | None = None,
        tile: Any = None,
    ) -> str:
        user.modify_inventory(self, subtract=True)
        user.stats.strength += 1
        user.stats.intel += 1
        user.stats.wisdom += 1
        user.stats.con += 1
        user.stats.charisma += 1
        user.stats.dex += 1
        use_str = f"All of {user.name}'s stats have been increased by 1!\n"
        return use_str


class Status(Potion):

    def __init__(self):
        super().__init__(
            name="Status",
            description="Base class for status items.",
            value=0,
            rarity=0,
            subtyp="Status",
        )
        self.status = None

    def use(self, user: Character, target: Character | None = None, tile: Any = None) -> str:
        use_str = ""
        if not user.status_effects[self.status].active:
            use_str += f"You are not affected by {self.status.lower()}.\n"
            return use_str
        user.modify_inventory(self, subtract=True)
        if getattr(getattr(user, "race", None), "name", None) == "Dwarf":
            from ..constants import (
                DWARF_HANGOVER_COMBAT_DURATION,
                DWARF_HANGOVER_MAX_STEPS,
                DWARF_HANGOVER_STEPS_PER_USE,
            )

            if user.state == "fight":
                h = user.status_effects.get("Hangover")
                if h is not None:
                    h.active = True
                    h.duration = max(int(h.duration or 0), DWARF_HANGOVER_COMBAT_DURATION)
            else:
                user.dwarf_hangover_steps = min(
                    DWARF_HANGOVER_MAX_STEPS,
                    int(getattr(user, "dwarf_hangover_steps", 0) or 0)
                    + DWARF_HANGOVER_STEPS_PER_USE,
                )
        user.status_effects[self.status].active = False
        user.status_effects[self.status].duration = 0
        try:
            user.status_effects[self.status].extra = 0
        except IndexError:
            pass
        use_str += f"You have been cured of {self.status.lower()}.\n"
        if user.health.current < user.health.max:
            heal = int(0.1 * user.health.max)
            heal = random.randint(heal // 2, heal)
            heal = min(heal, user.health.max - user.health.current)
            user.health.current += heal
            use_str += f"You have been healed for {heal} health.\n"
        return use_str


class Antidote(Status):

    def __init__(self):
        super().__init__()
        self.name = "Antidote"
        self.description = "\n".join(
            wrap("A potion that will cure poison.", 35, break_on_hyphens=False)
        )
        self.value = 250
        self.rarity = 0.9
        self.status = "Poison"


class EyeDrop(Status):

    def __init__(self):
        super().__init__()
        self.name = "Eye Drop"
        self.description = "\n".join(
            wrap("A potion that will cure blindness.", 35, break_on_hyphens=False)
        )
        self.value = 250
        self.rarity = 0.9
        self.status = "Blind"


class EchoScreen(Status):

    def __init__(self):
        super().__init__()
        self.name = "Echo Screen"
        self.description = "\n".join(
            wrap("A potion that will cure silence.", 35, break_on_hyphens=False)
        )
        self.value = 1000
        self.rarity = 0.8
        self.status = "Silence"


class Bandage(Status):

    def __init__(self):
        super().__init__()
        self.name = "Bandage"
        self.description = "\n".join(
            wrap("A linen bandage that will stop bleeding.", 35, break_on_hyphens=False)
        )
        self.value = 1000
        self.rarity = 0.8
        self.status = "Bleed"

    def use(
        self,
        user: Character,
        target: Character | None = None,
        tile: Any = None,
    ) -> str:
        use_str = ""
        if not user.physical_effects[self.status].active:
            use_str += f"You are not affected by {self.status.lower()}.\n"
            return use_str
        user.modify_inventory(self, subtract=True)
        user.physical_effects[self.status].active = False
        user.physical_effects[self.status].duration = 0
        user.physical_effects[self.status].extra = 0
        use_str += f"You have been cured of {self.status.lower()}.\n"
        if user.health.current < user.health.max:
            from ..classes import ability_mechanics

            heal = int(0.1 * user.health.max)
            heal = random.randint(heal // 2, heal)
            heal = int(heal * ability_mechanics.bandage_healing_multiplier(user))
            heal = min(heal, user.health.max - user.health.current)
            user.health.current += heal
            use_str += f"You have been healed for {heal} health.\n"
        return use_str


class PhoenixDown(Status):

    def __init__(self):
        super().__init__()
        self.name = "Phoenix Down"
        self.description = "\n".join(
            wrap("A potion that will cure doom status.", 35, break_on_hyphens=False)
        )
        self.value = 2000
        self.rarity = 0.7
        self.status = "Doom"


class Remedy(Status):
    # Silence, Doom, Blind, Poison

    def __init__(self):
        super().__init__()
        self.name = "Remedy"
        self.description = "\n".join(
            wrap("A potion that will cure all negative status effects.", 35, break_on_hyphens=False)
        )
        self.value = 5000
        self.rarity = 0.2
        self.status = ["Poison", "Blind", "Silence", "Doom"]

    def use(
        self,
        user: Character,
        target: Character | None = None,
        tile: Any = None,
    ) -> str:
        use_str = ""
        if not any([user.status_effects[x].active for x in self.status]):
            use_str += "You are not affected by any negative status effects.\n"
            return use_str
        user.modify_inventory(self, subtract=True)
        for status in self.status:
            user.status_effects[status].active = False
            user.status_effects[status].duration = 0
            try:
                user.status_effects[status].extra = 0
            except IndexError:
                pass
            use_str += f"You have been cured of {status.lower()}.\n"
        if user.health.current < user.health.max:
            heal = int(0.1 * user.health.max)
            heal = random.randint(heal // 2, heal)
            heal = min(heal, user.health.max - user.health.current)
            user.health.current += heal
            use_str += f"You have been healed for {heal} health.\n"
        return use_str
