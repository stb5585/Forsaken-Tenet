"""Enemy implementations for the opening and early dungeon."""

from __future__ import annotations

from src.core.randomness import gameplay_random as random

from .. import abilities, items, thieves_guild
from ..character import Character, Combat, Resource, Stats, StatusEffect
from ..combat.action_queue import ActionPriority
from .base import (
    Aberration,
    Animal,
    Construct,
    Dragon,
    Elemental,
    Fey,
    Fiend,
    Humanoid,
    Misc,
    Monster,
    Slime,
    Undead,
)


# Enemies
class Test(Misc):
    """
    Used for testing new implementations
    """

    def __init__(self):
        super().__init__(
            name="Test",
            health=1,
            mana=999,
            strength=20,
            intel=0,
            wisdom=0,
            con=10,
            charisma=99,
            dex=25,
            attack=0,
            defense=0,
            magic=0,
            magic_def=0,
            exp=5000,
        )
        self.equipment = {
            "Weapon": items.NoWeapon(),
            "Armor": items.NoArmor(),
            "OffHand": items.NoOffHand(),
            "Ring": items.NoRing(),
            "Pendant": items.NoPendant(),
        }
        self.spellbook = {"Spells": {}, "Skills": {"Slot Machine": abilities.SlotMachine()}}
        self.action_stack = [
            {"ability": "Attack", "priority": ActionPriority.SKIP},
            {"ability": "Slot Machine", "priority": ActionPriority.HIGH},
        ]
        self.level.pro_level = 99  # test for enemies running away

    def special_attack(self, target: Character) -> str:
        return abilities.BreatheFire().use(self, target=target)


class Mimic(Aberration):
    """
    true sight
    z: location level plus 1 if Locked plus 1 if ChestRoom2
    health:
    mana:
    strength:
    intel:
    wisdom:
    con:
    charisma:
    dex:
    attack:
    defense:
    magic:
    magic def:
    exp:
    gold:
    """

    def __init__(self, z, player_level: int | None = None):
        # Keep dungeon-depth baseline, but prevent chest mimics from becoming trivial
        # when encountered on lower floors later in progression.
        progression_tier = 0
        if player_level is not None:
            # Scale with player progression, but avoid "linear-to-absurd" stats
            # at late game, especially because Mimic has swingy control and
            # high-variance skills (e.g., Lick/Slot Machine).
            #
            # Tiering: 1 @ 1-10, 2 @ 11-20, ... 5 @ 41-50.
            progression_tier = max(1, min(12, (int(player_level) + 9) // 10))
        effective_level = max(int(z), progression_tier)

        super().__init__(
            name="Mimic",
            health=20 + (random.randint(10, 40) * effective_level),
            mana=10 + (random.randint(20, 35) * effective_level),
            strength=(15 + (5 * (effective_level - 1))),
            intel=(6 + (3 * (effective_level - 1))),
            wisdom=(11 + (5 * (effective_level - 1))),
            con=(13 + (5 * (effective_level - 1))),
            charisma=(8 + (4 * (effective_level - 1))),
            dex=(12 + (4 * (effective_level - 1))),
            attack=(random.randint(10, 20) * effective_level),
            defense=(random.randint(6, 15) * effective_level),
            magic=(random.randint(8, 16) * effective_level),
            magic_def=(random.randint(4, 12) * effective_level),
            exp=25 + (random.randint(25, 50) * effective_level),
        )
        self.gold = 50 + (random.randint(50, 100) * effective_level)
        self.equipment = {
            "Weapon": items.NoWeapon(),
            "Armor": items.NoArmor(),
            "OffHand": items.NoOffHand(),
            "Ring": items.NoRing(),
            "Pendant": items.NoPendant(),
        }
        self.spellbook = {
            "Spells": {},
            "Skills": {
                "Lick": abilities.Lick(),
                "Gold Toss": abilities.GoldToss(),
                "Slot Machine": abilities.SlotMachine(),
            },
        }
        self.resistance["Poison"] = 1.0
        self.status_immunity = ["Poison", "Death", "Stone"]
        self.action_stack = [
            {"ability": "Attack", "priority": ActionPriority.NORMAL},
            {"ability": "Lick", "priority": ActionPriority.HIGH},
            {"ability": "Gold Toss", "priority": ActionPriority.HIGH},
            {"ability": "Slot Machine", "priority": ActionPriority.NORMAL},
        ]
        self.level.pro_level = effective_level
        self.sight = True
        self.picture = "mimic.txt"


# Starting enemies
class GreenSlime(Slime):

    def __init__(self):
        super().__init__(
            name="Green Slime",
            health=random.randint(6, 9),
            mana=25,
            strength=6,
            intel=15,
            wisdom=15,
            con=8,
            charisma=1,
            dex=6,
            attack=3,
            defense=7,
            magic=8,
            magic_def=99,
            exp=random.randint(1, 20),
        )
        self.equipment = {
            "Weapon": items.NoWeapon(),
            "Armor": items.NoArmor(),
            "OffHand": items.NoOffHand(),
            "Ring": items.NoRing(),
            "Pendant": items.NoPendant(),
        }
        self.gold = random.randint(1, 8)
        self.inventory["Key"] = [items.Key]
        self.inventory["Fungus Spore"] = [items.FungusSpore]
        self.spellbook = {
            "Spells": {"Enfeeble": abilities.Enfeeble()},
            "Skills": {"Acid Spit": abilities.AcidSpit()},
        }
        self.action_stack = [
            {"ability": "Attack", "priority": ActionPriority.LOW},
            {"ability": "Acid Spit", "priority": ActionPriority.HIGH},
            {"ability": "Enfeeble", "priority": ActionPriority.NORMAL},
        ]
        self.level.pro_level = 0


class GiantRat(Animal):

    def __init__(self):
        super().__init__(
            name="Giant Rat",
            health=random.randint(2, 4),
            mana=3,
            strength=4,
            intel=3,
            wisdom=3,
            con=6,
            charisma=6,
            dex=15,
            attack=2,
            defense=5,
            magic=2,
            magic_def=6,
            exp=random.randint(7, 14),
        )
        self.equipment = {
            "Weapon": items.Bite(),
            "Armor": items.NoArmor(),
            "OffHand": items.NoOffHand(),
            "Ring": items.NoRing(),
            "Pendant": items.NoPendant(),
        }
        self.gold = random.randint(1, 5)
        self.inventory["Rat Tail"] = [items.RatTail]
        self.action_stack = [{"ability": "Attack", "priority": ActionPriority.NORMAL}]
        self.level.pro_level = 0
        self.picture = "giantrat.txt"


class Goblin(Humanoid):

    def __init__(self):
        super().__init__(
            name="Goblin",
            health=random.randint(3, 7),
            mana=5,
            strength=7,
            intel=5,
            wisdom=2,
            con=8,
            charisma=12,
            dex=8,
            attack=2,
            defense=6,
            magic=5,
            magic_def=7,
            exp=random.randint(7, 16),
        )
        self.equipment = {
            "Weapon": items.Rapier(),
            "Armor": items.NoArmor(),
            "OffHand": items.NoOffHand(),
            "Ring": items.NoRing(),
            "Pendant": items.NoPendant(),
        }
        self.gold = random.randint(10, 20)
        self.spellbook = {
            "Spells": {},
            "Skills": {"Goblin Punch": abilities.GoblinPunch(), "Gold Toss": abilities.GoldToss()},
        }
        self.action_stack = [
            {"ability": "Attack", "priority": ActionPriority.NORMAL},
            {"ability": "Goblin Punch", "priority": ActionPriority.NORMAL},
            {"ability": "Gold Toss", "priority": ActionPriority.NORMAL},
        ]
        self.level.pro_level = 0
        self.picture = "goblin.txt"


class Goblin2(Goblin):
    """
    Buffed version of a regular goblin; Barghest boss can transform into one
    """

    def __init__(self):
        super().__init__()
        self.stats = Stats(22, 16, 10, 17, 19, 14)
        self.combat = Combat(35, 18, 12, 22)
        self.equipment = {
            "Weapon": items.Jian(),
            "Armor": items.LeatherArmor(),
            "OffHand": items.Baselard(),
            "Ring": items.NoRing(),
            "Pendant": items.NoPendant(),
        }
        self.transform = [Barghest]
        self.spellbook["Spells"]["Mirror Image"] = abilities.MirrorImage()
        self.spellbook["Skills"]["Parry"] = abilities.Parry()
        self.action_stack = [
            {"ability": "Attack", "priority": ActionPriority.NORMAL},
            {"ability": "Goblin Punch", "priority": ActionPriority.NORMAL},
            {"ability": "Gold Toss", "priority": ActionPriority.NORMAL},
            {"ability": "Mirror Image", "priority": ActionPriority.HIGH},
            {
                "ability": "Shapeshift",
                "priority": ActionPriority.NORMAL,
                "priority_if": {
                    "self_status": "Shapeshifted",
                    "priority": ActionPriority.SKIP,
                    "else": ActionPriority.NORMAL,
                },
            },
        ]


class Bandit(Humanoid):

    def __init__(self):
        super().__init__(
            name="Bandit",
            health=random.randint(4, 8),
            mana=16,
            strength=8,
            intel=8,
            wisdom=5,
            con=8,
            charisma=10,
            dex=10,
            attack=4,
            defense=5,
            magic=3,
            magic_def=5,
            exp=random.randint(8, 18),
        )
        self.equipment = {
            "Weapon": items.Dirk(),
            "Armor": items.PaddedArmor(),
            "OffHand": items.NoOffHand(),
            "Ring": items.NoRing(),
            "Pendant": items.NoPendant(),
        }
        self.gold = random.randint(15, 25)
        self.inventory["Feather"] = [items.Feather]
        self.spellbook = {
            "Spells": {},
            "Skills": {
                "Steal": abilities.Steal(),
                "Disarm": abilities.Disarm(),
                "Smoke Screen": abilities.SmokeScreen(),
            },
        }
        self.action_stack = [
            {
                "ability": "Attack",
                "priority": ActionPriority.NORMAL,
                "priority_if": [
                    {
                        "condition": "self_status",
                        "value": "Steal Success",
                        "priority": ActionPriority.LOW,
                    }
                ],
            },
            {
                "ability": "Steal",
                "priority": ActionPriority.NORMAL,
                "priority_if": [
                    {
                        "condition": "self_status",
                        "value": "Steal Success",
                        "priority": ActionPriority.SKIP,
                    }
                ],
            },
            {
                "ability": "Disarm",
                "priority": ActionPriority.LOW,
                "priority_if": [
                    {
                        "condition": "self_status",
                        "value": "Steal Success",
                        "priority": ActionPriority.SKIP,
                    },
                    {
                        "condition": "target_has_weapon",
                        "value": True,
                        "priority": ActionPriority.HIGH,
                        "else": ActionPriority.SKIP,
                    },
                ],
            },
            {
                "ability": "Smoke Screen",
                "priority": ActionPriority.LOW,
                "priority_if": {
                    "self_status": "Steal Success",
                    "priority": ActionPriority.HIGH,
                    "else": ActionPriority.SKIP,
                },
            },
        ]
        self.level.pro_level = 0
        self.picture = "fighter.txt"


class Skeleton(Undead):

    def __init__(self):
        super().__init__(
            name="Skeleton",
            health=random.randint(5, 7),
            mana=2,
            strength=8,
            intel=4,
            wisdom=8,
            con=12,
            charisma=5,
            dex=6,
            attack=3,
            defense=8,
            magic=5,
            magic_def=6,
            exp=random.randint(11, 20),
        )
        self.equipment = {
            "Weapon": items.Rapier(),
            "Armor": items.NoArmor(),
            "OffHand": items.Buckler(),
            "Ring": items.NoRing(),
            "Pendant": items.NoPendant(),
        }
        self.gold = random.randint(1, 5)
        self.inventory["Health Potion"] = [items.HealthPotion]
        self.resistance["Fire"] = 0.0
        self.action_stack = [{"ability": "Attack", "priority": ActionPriority.NORMAL}]
        self.level.pro_level = 0
        self.picture = "skeleton.txt"


class Scarecrow(Construct):

    def __init__(self):
        super().__init__(
            name="Scarecrow",
            health=random.randint(5, 7),
            mana=10,
            strength=12,
            intel=3,
            wisdom=6,
            con=10,
            charisma=8,
            dex=11,
            attack=4,
            defense=5,
            magic=7,
            magic_def=5,
            exp=random.randint(13, 21),
        )
        self.equipment = {
            "Weapon": items.Claw(),
            "Armor": items.NoArmor(),
            "OffHand": items.NoOffHand(),
            "Ring": items.NoRing(),
            "Pendant": items.NoPendant(),
        }
        self.gold = random.randint(8, 16)
        self.spellbook = {"Spells": {}, "Skills": {"Sleeping Powder": abilities.SleepingPowder()}}
        self.resistance["Fire"] = -1.0
        self.resistance["Physical"] = 0.0
        self.action_stack = [
            {"ability": "Attack", "priority": ActionPriority.NORMAL},
            {"ability": "Sleeping Powder", "priority": ActionPriority.NORMAL},
        ]
        self.level.pro_level = 0
        self.picture = "scarecrow.txt"


# Level 1
class GiantCentipede(Animal):

    def __init__(self):
        super().__init__(
            name="Giant Centipede",
            health=random.randint(8, 13),
            mana=3,
            strength=10,
            intel=4,
            wisdom=6,
            con=8,
            charisma=8,
            dex=12,
            attack=10,
            defense=9,
            magic=5,
            magic_def=7,
            exp=random.randint(13, 24),
        )
        self.equipment = {
            "Weapon": items.Pincers(),
            "Armor": items.Carapace(),
            "OffHand": items.NoOffHand(),
            "Ring": items.NoRing(),
            "Pendant": items.NoPendant(),
        }
        self.gold = random.randint(10, 18)
        self.resistance["Physical"] = 0.25
        self.action_stack = [{"ability": "Attack", "priority": ActionPriority.NORMAL}]
        self.level.pro_level = 1
        self.picture = "centipede.txt"


class GiantHornet(Animal):

    def __init__(self):
        super().__init__(
            name="Giant Hornet",
            health=random.randint(6, 10),
            mana=25,
            strength=6,
            intel=4,
            wisdom=6,
            con=6,
            charisma=8,
            dex=18,
            attack=9,
            defense=8,
            magic=6,
            magic_def=9,
            exp=random.randint(13, 24),
        )
        self.equipment = {
            "Weapon": items.Stinger(),
            "Armor": items.NoArmor(),
            "OffHand": items.NoOffHand(),
            "Ring": items.NoRing(),
            "Pendant": items.NoPendant(),
        }
        self.gold = random.randint(6, 15)
        self.spellbook = {"Spells": {"Berserk": abilities.Berserk()}, "Skills": {}}
        self.flying = True
        self.action_stack = [
            {"ability": "Attack", "priority": ActionPriority.NORMAL},
            {"ability": "Berserk", "priority": ActionPriority.NORMAL},
        ]
        self.level.pro_level = 1
        self.picture = "hornet.txt"


class ElectricBat(Animal):

    def __init__(self):
        super().__init__(
            name="Electric Bat",
            health=random.randint(5, 9),
            mana=15,
            strength=6,
            intel=11,
            wisdom=7,
            con=5,
            charisma=12,
            dex=22,
            attack=10,
            defense=6,
            magic=14,
            magic_def=11,
            exp=random.randint(17, 31),
        )
        self.equipment = {
            "Weapon": items.Bite(),
            "Armor": items.NoArmor(),
            "OffHand": items.NoOffHand(),
            "Ring": items.NoRing(),
            "Pendant": items.NoPendant(),
        }
        self.gold = random.randint(8, 21)
        self.spellbook = {
            "Spells": {"Shock": abilities.Shock(), "Silence": abilities.Silence()},
            "Skills": {},
        }
        self.flying = True
        self.resistance["Electric"] = 0.25
        self.resistance["Water"] = -0.25
        self.action_stack = [
            {"ability": "Attack", "priority": ActionPriority.NORMAL},
            {"ability": "Shock", "priority": ActionPriority.NORMAL},
            {
                "ability": "Silence",
                "priority": ActionPriority.NORMAL,
                "priority_if": {
                    "target_status": "Silence",
                    "priority": ActionPriority.SKIP,
                    "else": ActionPriority.NORMAL,
                },
            },
        ]
        self.level.pro_level = 1
        self.picture = "bat.txt"


class Zombie(Undead):

    def __init__(self):
        super().__init__(
            name="Zombie",
            health=random.randint(11, 14),
            mana=20,
            strength=15,
            intel=1,
            wisdom=5,
            con=8,
            charisma=8,
            dex=8,
            attack=12,
            defense=10,
            magic=4,
            magic_def=8,
            exp=random.randint(11, 22),
        )
        self.equipment = {
            "Weapon": items.Bite(),
            "Armor": items.NoArmor(),
            "OffHand": items.NoOffHand(),
            "Ring": items.NoRing(),
            "Pendant": items.NoPendant(),
        }
        self.gold = random.randint(15, 30)
        self.spellbook = {
            "Spells": {},
            "Skills": {"Piercing Strike": abilities.PiercingStrike()},
        }
        self.action_stack = [
            {"ability": "Attack", "priority": ActionPriority.NORMAL},
            {"ability": "Piercing Strike", "priority": ActionPriority.NORMAL},
        ]
        self.level.pro_level = 1
        self.picture = "zombie.txt"


class Imp(Fiend):

    def __init__(self):
        super().__init__(
            name="Imp",
            health=random.randint(9, 14),
            mana=25,
            strength=6,
            intel=12,
            wisdom=10,
            con=8,
            charisma=12,
            dex=12,
            attack=7,
            defense=11,
            magic=16,
            magic_def=14,
            exp=random.randint(15, 24),
        )
        self.equipment = {
            "Weapon": items.DemonClaw(),
            "Armor": items.NoArmor(),
            "OffHand": items.NoOffHand(),
            "Ring": items.NoRing(),
            "Pendant": items.NoPendant(),
        }
        self.gold = random.randint(15, 30)
        self.spellbook = {
            "Spells": {"Corruption": abilities.Corruption(), "Silence": abilities.Silence()},
            "Skills": {},
        }
        self.flying = True
        self.action_stack = [
            {"ability": "Attack", "priority": ActionPriority.NORMAL},
            {"ability": "Corruption", "priority": ActionPriority.NORMAL},
            {
                "ability": "Silence",
                "priority": ActionPriority.NORMAL,
                "priority_if": {
                    "target_status": "Silence",
                    "priority": ActionPriority.SKIP,
                    "else": ActionPriority.NORMAL,
                },
            },
        ]
        self.level.pro_level = 1
        self.picture = "imp.txt"


class GiantSpider(Animal):

    def __init__(self):
        super().__init__(
            name="Giant Spider",
            health=random.randint(12, 15),
            mana=10,
            strength=9,
            intel=10,
            wisdom=10,
            con=8,
            charisma=10,
            dex=12,
            attack=11,
            defense=13,
            magic=8,
            magic_def=10,
            exp=random.randint(15, 24),
        )
        self.equipment = {
            "Weapon": items.Stinger(),
            "Armor": items.Carapace(),
            "OffHand": items.NoOffHand(),
            "Ring": items.NoRing(),
            "Pendant": items.NoPendant(),
        }
        self.gold = random.randint(15, 30)
        self.spellbook = {"Spells": {}, "Skills": {"Web": abilities.Web()}}
        self.resistance["Poison"] = 0.25
        self.action_stack = [
            {"ability": "Attack", "priority": ActionPriority.NORMAL},
            {"ability": "Web", "priority": ActionPriority.NORMAL},
        ]
        self.level.pro_level = 1
        self.picture = "spider.txt"


class Quasit(Fiend):
    """
    Can shapeshift between Electric Bat, Giant Centipede, Battle Toad, and natural forms
    """

    def __init__(self):
        super().__init__(
            name="Quasit",
            health=random.randint(13, 17),
            mana=15,
            strength=8,
            intel=8,
            wisdom=10,
            con=11,
            charisma=14,
            dex=16,
            attack=10,
            defense=11,
            magic=10,
            magic_def=13,
            exp=random.randint(25, 44),
        )
        self.equipment = {
            "Weapon": items.DemonClaw(),
            "Armor": items.DemonArmor(),
            "OffHand": items.Claw(),
            "Ring": items.NoRing(),
            "Pendant": items.NoPendant(),
        }
        self.gold = random.randint(25, 40)
        self.spellbook = {
            "Spells": {},
            "Skills": {
                "Piercing Strike": abilities.PiercingStrike(),
                "Shapeshift": abilities.Shapeshift(),
            },
        }
        self.resistance["Poison"] = 1
        self.status_immunity.append("Poison")
        self.transform = [Quasit, ElectricBat, GiantCentipede, BattleToad]
        self.action_stack = [
            {"ability": "Attack", "priority": ActionPriority.NORMAL},
            {"ability": "Piercing Strike", "priority": ActionPriority.NORMAL},
            {
                "ability": "Shapeshift",
                "priority": ActionPriority.HIGH,
                "priority_if": {
                    "self_status": "Shapeshifted",
                    "priority": ActionPriority.SKIP,
                    "else": ActionPriority.HIGH,
                },
            },
        ]
        self.level.pro_level = 1
        self.picture = "quasit.txt"


class Panther(Animal):

    def __init__(self):
        super().__init__(
            name="Panther",
            health=random.randint(10, 14),
            mana=25,
            strength=10,
            intel=8,
            wisdom=8,
            con=10,
            charisma=10,
            dex=13,
            attack=13,
            defense=10,
            magic=8,
            magic_def=7,
            exp=random.randint(19, 28),
        )
        self.equipment = {
            "Weapon": items.Claw(),
            "Armor": items.AnimalHide(),
            "OffHand": items.Claw(),
            "Ring": items.NoRing(),
            "Pendant": items.NoPendant(),
        }
        self.gold = random.randint(10, 20)
        self.inventory["Leather"] = [items.Leather]
        self.spellbook = {
            "Spells": {},
            "Skills": {
                "Backstab": abilities.Backstab(),
                "Kidney Punch": abilities.KidneyPunch(),
                "Disarm": abilities.Disarm(),
            },
        }
        self.resistance["Physical"] = 0.25
        self.action_stack = [
            {"ability": "Attack", "priority": ActionPriority.NORMAL},
            {
                "ability": "Backstab",
                "priority": ActionPriority.LOW,
                "priority_if": {
                    "target_incapacitated": True,
                    "priority": ActionPriority.HIGH,
                    "else": ActionPriority.LOW,
                },
            },
            {"ability": "Kidney Punch", "priority": ActionPriority.HIGH},
            {
                "ability": "Disarm",
                "priority": ActionPriority.LOW,
                "priority_if": {
                    "target_has_weapon": True,
                    "priority": ActionPriority.HIGH,
                    "else": ActionPriority.SKIP,
                },
            },
        ]
        self.level.pro_level = 1
        self.picture = "panther.txt"


class Panther2(Panther):
    """
    Transform Level 1 creature
    """

    def __init__(self):
        super().__init__()
        self.stats = Stats(0, 0, 0, 0, 0, 0)
        self.combat = Combat(0, 0, 0, 0)


class TwistedDwarf(Humanoid):

    def __init__(self):
        super().__init__(
            name="Twisted Dwarf",
            health=random.randint(15, 19),
            mana=10,
            strength=12,
            intel=8,
            wisdom=10,
            con=12,
            charisma=8,
            dex=10,
            attack=14,
            defense=14,
            magic=11,
            magic_def=11,
            exp=random.randint(25, 44),
        )
        self.equipment = {
            "Weapon": items.Mattock(),
            "Armor": items.HideArmor(),
            "OffHand": items.NoOffHand(),
            "Ring": items.NoRing(),
            "Pendant": items.NoPendant(),
        }
        self.gold = random.randint(10, 20)
        self.spellbook = {"Spells": {}, "Skills": {"Piercing Strike": abilities.PiercingStrike()}}
        self.action_stack = [
            {"ability": "Attack", "priority": ActionPriority.NORMAL},
            {"ability": "Piercing Strike", "priority": ActionPriority.NORMAL},
        ]
        self.level.pro_level = 1
        self.picture = "dwarf.txt"


class BattleToad(Animal):

    def __init__(self):
        super().__init__(
            name="Battle Toad",
            health=random.randint(15, 19),
            mana=20,
            strength=10,
            intel=9,
            wisdom=10,
            con=10,
            charisma=8,
            dex=15,
            attack=11,
            defense=10,
            magic=12,
            magic_def=9,
            exp=random.randint(30, 48),
        )
        self.equipment = {
            "Weapon": items.BrassKnuckles(),
            "Armor": items.NoArmor(),
            "OffHand": items.BrassKnuckles(),
            "Ring": items.NoRing(),
            "Pendant": items.NoPendant(),
        }
        self.gold = random.randint(31, 47)
        self.spellbook = {
            "Spells": {},
            "Skills": {"Kidney Punch": abilities.KidneyPunch(), "Jump": abilities.Jump()},
        }
        self.resistance["Water"] = 0.75
        self.action_stack = [
            {"ability": "Attack", "priority": ActionPriority.NORMAL},
            {"ability": "Kidney Punch", "priority": ActionPriority.NORMAL},
            {"ability": "Jump", "priority": ActionPriority.NORMAL},
        ]
        self.level.pro_level = 1
        self.picture = "battletoad.txt"


class Satyr(Fey):

    def __init__(self):
        super().__init__(
            name="Satyr",
            health=random.randint(17, 22),
            mana=25,
            strength=11,
            intel=12,
            wisdom=10,
            con=11,
            charisma=12,
            dex=12,
            attack=13,
            defense=14,
            magic=12,
            magic_def=18,
            exp=random.randint(28, 44),
        )
        self.equipment = {
            "Weapon": items.Rapier(),
            "Armor": items.PaddedArmor(),
            "OffHand": items.NoOffHand(),
            "Ring": items.NoRing(),
            "Pendant": items.NoPendant(),
        }
        self.gold = random.randint(29, 42)
        self.inventory["Leather"] = [items.Leather]
        self.spellbook = {"Spells": {}, "Skills": {"Stomp": abilities.Stomp()}}
        self.resistance["Fire"] = 0.1
        self.resistance["Ice"] = 0.1
        self.resistance["Electric"] = 0.1
        self.resistance["Water"] = 0.1
        self.resistance["Earth"] = 0.1
        self.resistance["Wind"] = 0.1
        self.resistance["Poison"] = 0.1
        self.resistance["Physical"] = 0.1
        self.action_stack = [
            {"ability": "Attack", "priority": ActionPriority.NORMAL},
            {"ability": "Stomp", "priority": ActionPriority.NORMAL},
        ]
        self.level.pro_level = 1
        self.picture = "satyr.txt"


class Minotaur(Monster):
    """
    Level 1 Boss
    """

    def __init__(self):
        super().__init__(
            name="Minotaur",
            health=86,
            mana=60,
            strength=18,
            intel=8,
            wisdom=10,
            con=14,
            charisma=14,
            dex=12,
            attack=24,
            defense=15,
            magic=12,
            magic_def=17,
            exp=250,
        )
        self.equipment = {
            "Weapon": items.Broadaxe(),
            "Armor": items.LeatherArmor(),
            "OffHand": items.NoOffHand(),
            "Ring": items.NoRing(),
            "Pendant": items.NoPendant(),
        }
        self.gold = 200
        self.inventory["Weapon"] = [items.random_item(2)]
        self.inventory["Leather"] = [items.Leather]
        self.spellbook = {
            "Spells": {},
            "Skills": {
                "Mortal Strike": abilities.MortalStrike(),
                "Charge": abilities.Charge(),
                "Disarm": abilities.Disarm(),
                "Parry": abilities.Parry(),
            },
        }
        self.status_immunity = ["Death", "Disarm"]
        self.action_stack = [
            {"ability": "Attack", "priority": ActionPriority.NORMAL},
            {"ability": "Mortal Strike", "priority": ActionPriority.NORMAL},
            {"ability": "Charge", "priority": ActionPriority.NORMAL},
            {
                "ability": "Disarm",
                "priority": ActionPriority.LOW,
                "priority_if": {
                    "target_has_weapon": True,
                    "priority": ActionPriority.NORMAL,
                    "else": ActionPriority.SKIP,
                },
            },
        ]
        self.level.pro_level = 1
        self.sight = True
        self.picture = "minotaur.txt"


class Barghest(Fiend):
    """
    Level 1 Extra Boss - guards first of six relics (TRIANGULUS) required to beat the final boss
    Can shapeshift between 3 forms: Direwolf, Goblin, and Hybrid (natural) forms
    """

    def __init__(self):
        super().__init__(
            name="Barghest",
            health=135,
            mana=120,
            strength=22,
            intel=15,
            wisdom=14,
            con=18,
            charisma=14,
            dex=12,
            attack=34,
            defense=30,
            magic=21,
            magic_def=32,
            exp=500,
        )
        self.gold = 600
        self.equipment = {
            "Weapon": items.Claw2(),
            "Armor": items.AnimalHide(),
            "OffHand": items.Claw2(),
            "Ring": items.NoRing(),
            "Pendant": items.NoPendant(),
        }
        self.inventory["Old Key"] = [items.OldKey]
        self.spellbook = {
            "Spells": {"Enfeeble": abilities.Enfeeble()},
            "Skills": {
                "Shapeshift": abilities.Shapeshift(),
                "Kidney Punch": abilities.KidneyPunch(),
                "Backstab": abilities.Backstab(),
            },
        }
        self.resistance["Physical"] = 0.25
        self.transform = [Barghest, Goblin2, Direwolf2]
        self.action_stack = [
            {"ability": "Attack", "priority": ActionPriority.NORMAL},
            {
                "ability": "Backstab",
                "priority": ActionPriority.LOW,
                "priority_if": {
                    "target_incapacitated": True,
                    "priority": ActionPriority.HIGH,
                    "else": ActionPriority.LOW,
                },
            },
            {"ability": "Kidney Punch", "priority": ActionPriority.NORMAL},
            {
                "ability": "Shapeshift",
                "priority": ActionPriority.NORMAL,
                "priority_if": {
                    "self_status": "Shapeshifted",
                    "priority": ActionPriority.SKIP,
                    "else": ActionPriority.NORMAL,
                },
            },
            {"ability": "Enfeeble", "priority": ActionPriority.LOW},
        ]
        self.level.pro_level = 2
        self.sight = True
        self.picture = "barghest.txt"


# Level 2
class Gnoll(Humanoid):

    def __init__(self):
        super().__init__(
            name="Gnoll",
            health=random.randint(16, 24),
            mana=20,
            strength=13,
            intel=10,
            wisdom=5,
            con=8,
            charisma=12,
            dex=16,
            attack=13,
            defense=12,
            magic=12,
            magic_def=13,
            exp=random.randint(45, 85),
        )
        self.equipment = {
            "Weapon": items.Partisan(),
            "Armor": items.PaddedArmor(),
            "OffHand": items.NoOffHand(),
            "Ring": items.NoRing(),
            "Pendant": items.NoPendant(),
        }
        self.gold = random.randint(10, 20)
        self.inventory["Feather"] = [items.Feather]
        self.spellbook = {"Spells": {}, "Skills": {"Disarm": abilities.Disarm()}}
        self.action_stack = [
            {"ability": "Attack", "priority": ActionPriority.NORMAL},
            {
                "ability": "Disarm",
                "priority": ActionPriority.LOW,
                "priority_if": {
                    "target_has_weapon": True,
                    "priority": ActionPriority.NORMAL,
                    "else": ActionPriority.SKIP,
                },
            },
        ]
        self.level.pro_level = 2
        self.picture = "gnoll.txt"


class GiantSnake(Animal):

    def __init__(self):
        super().__init__(
            name="Giant Snake",
            health=random.randint(18, 26),
            mana=2,
            strength=15,
            intel=5,
            wisdom=6,
            con=14,
            charisma=10,
            dex=16,
            attack=16,
            defense=15,
            magic=8,
            magic_def=11,
            exp=random.randint(60, 100),
        )
        self.equipment = {
            "Weapon": items.SnakeFang(),
            "Armor": items.SnakeScales(),
            "OffHand": items.NoOffHand(),
            "Ring": items.NoRing(),
            "Pendant": items.NoPendant(),
        }
        self.gold = random.randint(35, 75)
        self.inventory["Snake Skin"] = [items.SnakeSkin]
        self.inventory["Snake Venom"] = [items.SnakeVenom]
        self.spellbook = {"Spells": {}, "Skills": {"Slam": abilities.Slam()}}
        self.resistance["Poison"] = 0.25
        self.action_stack = [
            {"ability": "Attack", "priority": ActionPriority.NORMAL},
            {"ability": "Slam", "priority": ActionPriority.NORMAL},
        ]
        self.level.pro_level = 2
        self.picture = "snake.txt"


class Orc(Humanoid):

    def __init__(self):
        super().__init__(
            name="Orc",
            health=random.randint(17, 28),
            mana=14,
            strength=12,
            intel=6,
            wisdom=5,
            con=10,
            charisma=8,
            dex=14,
            attack=14,
            defense=13,
            magic=10,
            magic_def=10,
            exp=random.randint(45, 80),
        )
        self.equipment = {
            "Weapon": items.Jian(),
            "Armor": items.LeatherArmor(),
            "OffHand": items.NoOffHand(),
            "Ring": items.NoRing(),
            "Pendant": items.NoPendant(),
        }
        self.gold = random.randint(20, 65)
        self.inventory["Leather"] = [items.Leather]
        self.spellbook = {"Spells": {}, "Skills": {"Piercing Strike": abilities.PiercingStrike()}}
        self.action_stack = [
            {"ability": "Attack", "priority": ActionPriority.NORMAL},
            {"ability": "Piercing Strike", "priority": ActionPriority.HIGH},
        ]
        self.level.pro_level = 2
        self.picture = "orc.txt"


class GiantOwl(Animal):

    def __init__(self):
        super().__init__(
            name="Giant Owl",
            health=random.randint(12, 17),
            mana=12,
            strength=13,
            intel=12,
            wisdom=10,
            con=10,
            charisma=1,
            dex=15,
            attack=10,
            defense=12,
            magic=14,
            magic_def=16,
            exp=random.randint(45, 80),
        )
        self.equipment = {
            "Weapon": items.Claw2(),
            "Armor": items.NoArmor(),
            "OffHand": items.Claw2(),
            "Ring": items.NoRing(),
            "Pendant": items.NoPendant(),
        }
        self.gold = random.randint(20, 65)
        self.spellbook = {"Spells": {}, "Skills": {"Screech": abilities.Screech()}}
        self.inventory["Feather"] = [items.Feather]
        self.flying = True
        self.action_stack = [
            {"ability": "Attack", "priority": ActionPriority.NORMAL},
            {"ability": "Screech", "priority": ActionPriority.NORMAL},
        ]
        self.level.pro_level = 2
        self.picture = "giantowl.txt"


class Vampire(Undead):

    def __init__(self):
        super().__init__(
            name="Vampire",
            health=random.randint(20, 28),
            mana=30,
            strength=16,
            intel=14,
            wisdom=12,
            con=15,
            charisma=14,
            dex=14,
            attack=13,
            defense=17,
            magic=21,
            magic_def=18,
            exp=random.randint(50, 90),
        )
        self.equipment = {
            "Weapon": items.IronshodStaff(),
            "Armor": items.NoArmor(),
            "OffHand": items.VampireBite(),
            "Ring": items.NoRing(),
            "Pendant": items.NoPendant(),
        }
        self.gold = random.randint(40, 90)
        self.spellbook = {
            "Spells": {"Silence": abilities.Silence(), "Lightning": abilities.Lightning()},
            "Skills": {
                "Health Drain": abilities.HealthDrain(),
                "Shapeshift": abilities.Shapeshift(),
            },
        }
        self.transform = [Vampire, VampireBat]
        self.action_stack = [
            {"ability": "Attack", "priority": ActionPriority.NORMAL},
            {"ability": "Health Drain", "priority": ActionPriority.NORMAL},
            {"ability": "Lightning", "priority": ActionPriority.NORMAL},
            {
                "ability": "Silence",
                "priority": ActionPriority.NORMAL,
                "priority_if": {
                    "target_status": "Silence",
                    "priority": ActionPriority.SKIP,
                    "else": ActionPriority.NORMAL,
                },
            },
            {
                "ability": "Shapeshift",
                "priority": ActionPriority.NORMAL,
                "priority_if": {
                    "self_status": "Shapeshifted",
                    "priority": ActionPriority.SKIP,
                    "else": ActionPriority.NORMAL,
                },
            },
        ]
        self.level.pro_level = 2
        self.picture = "vampire.txt"


class VampireBat(Animal):

    def __init__(self):
        super().__init__(
            name="Vampire Bat",
            health=random.randint(20, 28),
            mana=30,
            strength=12,
            intel=16,
            wisdom=15,
            con=10,
            charisma=14,
            dex=18,
            attack=10,
            defense=11,
            magic=14,
            magic_def=11,
            exp=random.randint(50, 90),
        )
        self.equipment = {
            "Weapon": items.VampireBite(),
            "Armor": items.NoArmor(),
            "OffHand": items.NoOffHand(),
            "Ring": items.NoRing(),
            "Pendant": items.NoPendant(),
        }
        self.gold = random.randint(40, 90)
        self.spellbook = {
            "Spells": {},
            "Skills": {
                "Health Drain": abilities.HealthDrain(),
                "Shapeshift": abilities.Shapeshift(),
            },
        }
        self.transform = [Vampire, VampireBat]
        self.flying = True
        self.action_stack = [
            {"ability": "Attack", "priority": ActionPriority.NORMAL},
            {"ability": "Health Drain", "priority": ActionPriority.NORMAL},
            {
                "ability": "Shapeshift",
                "priority": ActionPriority.NORMAL,
                "priority_if": {
                    "self_status": "Shapeshifted",
                    "priority": ActionPriority.SKIP,
                    "else": ActionPriority.NORMAL,
                },
            },
        ]
        self.level.pro_level = 2
        self.picture = "bat.txt"


class Direwolf(Animal):

    def __init__(self):
        super().__init__(
            name="Direwolf",
            health=random.randint(16, 20),
            mana=8,
            strength=17,
            intel=7,
            wisdom=6,
            con=14,
            charisma=10,
            dex=16,
            attack=17,
            defense=16,
            magic=9,
            magic_def=8,
            exp=random.randint(60, 100),
        )
        self.equipment = {
            "Weapon": items.Claw2(),
            "Armor": items.AnimalHide(),
            "OffHand": items.Claw(),
            "Ring": items.NoRing(),
            "Pendant": items.NoPendant(),
        }
        self.gold = random.randint(35, 75)
        self.inventory["Leather"] = [items.Leather]
        self.spellbook = {
            "Spells": {},
            "Skills": {"Howl": abilities.Howl(), "Trip": abilities.Trip()},
        }
        self.resistance["Physical"] = 0.25
        self.action_stack = [
            {"ability": "Attack", "priority": ActionPriority.NORMAL},
            {"ability": "Howl", "priority": ActionPriority.NORMAL},
            {"ability": "Trip", "priority": ActionPriority.NORMAL},
        ]
        self.level.pro_level = 2
        self.picture = "direwolf.txt"


class Direwolf2(Direwolf):
    """
    Buffed version of Direwolf; Barghest will transform into
    """

    def __init__(self):
        super().__init__()
        self.stats = Stats(28, 10, 9, 20, 12, 20)
        self.combat = Combat(36, 38, 24, 33)
        self.equipment = {
            "Weapon": items.Claw2(),
            "Armor": items.AnimalHide2(),
            "OffHand": items.Claw2(),
            "Ring": items.NoRing(),
            "Pendant": items.NoPendant(),
        }
        self.transform = [Barghest]
        self.spellbook["Skills"]["Jump"] = abilities.Jump()
        self.action_stack = [
            {"ability": "Attack", "priority": ActionPriority.NORMAL},
            {"ability": "Howl", "priority": ActionPriority.NORMAL},
            {"ability": "Trip", "priority": ActionPriority.NORMAL},
            {"ability": "Jump", "priority": ActionPriority.HIGH},
            {
                "ability": "Shapeshift",
                "priority": ActionPriority.NORMAL,
                "priority_if": {
                    "self_status": "Shapeshifted",
                    "priority": ActionPriority.SKIP,
                    "else": ActionPriority.NORMAL,
                },
            },
        ]


class Wererat(Monster):

    def __init__(self):
        super().__init__(
            name="Wererat",
            health=random.randint(14, 17),
            mana=4,
            strength=14,
            intel=6,
            wisdom=12,
            con=11,
            charisma=8,
            dex=18,
            attack=11,
            defense=14,
            magic=7,
            magic_def=11,
            exp=random.randint(57, 94),
        )
        self.equipment = {
            "Weapon": items.Bite(),
            "Armor": items.AnimalHide(),
            "OffHand": items.Claw(),
            "Ring": items.NoRing(),
            "Pendant": items.NoPendant(),
        }
        self.gold = random.randint(40, 65)
        self.inventory["Rat Tail"] = [items.RatTail]
        self.inventory["Leather"] = [items.Leather]
        self.transform = [Wererat, Bandit2]
        self.action_stack = [
            {"ability": "Attack", "priority": ActionPriority.NORMAL},
            {
                "ability": "Shapeshift",
                "priority": ActionPriority.NORMAL,
                "priority_if": {
                    "self_status": "Shapeshifted",
                    "priority": ActionPriority.SKIP,
                    "else": ActionPriority.NORMAL,
                },
            },
        ]
        self.level.pro_level = 2
        self.picture = "giantrat.txt"


class Bandit2(Bandit):
    """
    Buffed version of Bandit; Wererat will transform into
    """

    def __init__(self):
        super().__init__()
        self.stats = Stats(28, 10, 9, 20, 12, 20)
        self.combat = Combat(36, 38, 24, 33)
        self.equipment = {
            "Weapon": items.Jian(),
            "Armor": items.LeatherArmor(),
            "OffHand": items.NoOffHand(),
            "Ring": items.NoRing(),
            "Pendant": items.NoPendant(),
        }
        self.transform = [Wererat, Bandit2]
        self.action_stack = [
            {"ability": "Attack", "priority": ActionPriority.NORMAL},
            {"ability": "Piercing Strike", "priority": ActionPriority.NORMAL},
            {
                "ability": "Shapeshift",
                "priority": ActionPriority.NORMAL,
                "priority_if": {
                    "self_status": "Shapeshifted",
                    "priority": ActionPriority.SKIP,
                    "else": ActionPriority.NORMAL,
                },
            },
        ]


class ThievesGuildTrialBoss(Bandit2):
    """Base upgraded Bandit used for Thieves Guild initiation branches."""

    branch = "cutpurse"
    trial_name = "Guild Cutpurse"

    def __init__(self):
        super().__init__()
        self.name = self.trial_name
        self.combat_sprite_archetype = "bandit"
        self.render_archetype = "bandit"
        self.boss = True
        self.is_boss = True
        self.thieves_guild_trial_enemy = True
        self.thieves_guild_trial_name = self.trial_name
        self.class_ring_trial_enemy = True
        self.health = Resource(90, 90)
        self.mana = Resource(40, 40)
        self.stats = Stats(34, 16, 14, 28, 20, 28)
        self.combat = Combat(48, 45, 32, 38)
        self.gold = random.randint(250, 450)
        self.inventory = {thieves_guild.SIGNET_NAME: [items.ThievesGuildSignet]}
        self.spellbook = {
            "Spells": {},
            "Skills": {
                "Steal": abilities.Steal(),
                "Kidney Punch": abilities.KidneyPunch(),
                "Backstab": abilities.Backstab(),
            },
        }
        self.action_stack = [
            {"ability": "Attack", "priority": ActionPriority.NORMAL},
            {"ability": "Steal", "priority": ActionPriority.NORMAL},
            {"ability": "Kidney Punch", "priority": ActionPriority.LOW},
            {"ability": "Backstab", "priority": ActionPriority.NORMAL},
        ]


class GuildCutpurseBoss(ThievesGuildTrialBoss):
    branch = "cutpurse"
    trial_name = "Guild Cutpurse"

    def __init__(self):
        super().__init__()
        self.stats = Stats(32, 14, 14, 26, 26, 34)
        self.combat = Combat(50, 42, 30, 38)


class GuildInquestBoss(ThievesGuildTrialBoss):
    branch = "inquest"
    trial_name = "False-Ledger Broker"

    def __init__(self):
        super().__init__()
        self.stats = Stats(30, 24, 28, 28, 20, 24)
        self.combat = Combat(44, 48, 38, 46)
        self.spellbook["Skills"]["Disarm"] = abilities.Disarm()
        self.action_stack = [
            {"ability": "Attack", "priority": ActionPriority.NORMAL},
            {"ability": "Disarm", "priority": ActionPriority.NORMAL},
            {"ability": "Smoke Screen", "priority": ActionPriority.LOW},
        ]


class GuildContractBoss(ThievesGuildTrialBoss):
    branch = "contract"
    trial_name = "Silent Contract Knife"

    def __init__(self):
        super().__init__()
        self.stats = Stats(38, 14, 14, 26, 20, 38)
        self.combat = Combat(56, 40, 30, 36)
        self.spellbook["Skills"]["Sneak Attack"] = abilities.SneakAttack()
        self.action_stack = [
            {"ability": "Attack", "priority": ActionPriority.NORMAL},
            {"ability": "Backstab", "priority": ActionPriority.NORMAL},
            {"ability": "Sneak Attack", "priority": ActionPriority.NORMAL},
        ]


class GuildArcaneBoss(ThievesGuildTrialBoss):
    branch = "arcane"
    trial_name = "Spell-Sealed Cutpurse"

    def __init__(self):
        super().__init__()
        self.stats = Stats(28, 30, 20, 26, 22, 30)
        self.combat = Combat(42, 40, 48, 44)
        self.spellbook["Spells"] = {"Firebolt": abilities.Firebolt(), "Shock": abilities.Shock()}
        self.action_stack = [
            {"ability": "Attack", "priority": ActionPriority.NORMAL},
            {"ability": "Firebolt", "priority": ActionPriority.NORMAL},
            {"ability": "Shock", "priority": ActionPriority.NORMAL},
            {"ability": "Smoke Screen", "priority": ActionPriority.LOW},
        ]


class RedSlime(Slime):

    def __init__(self):
        super().__init__(
            name="Red Slime",
            health=random.randint(18, 32),
            mana=30,
            strength=10,
            intel=20,
            wisdom=20,
            con=12,
            charisma=10,
            dex=5,
            attack=7,
            defense=13,
            magic=24,
            magic_def=150,
            exp=random.randint(43, 150),
        )
        self.equipment = {
            "Weapon": items.NoWeapon(),
            "Armor": items.NoArmor(),
            "OffHand": items.NoOffHand(),
            "Ring": items.NoRing(),
            "Pendant": items.NoPendant(),
        }
        self.gold = random.randint(40, 65)
        self.inventory["Mana Potion"] = [items.ManaPotion]
        self.inventory["Fungus Spore"] = [items.FungusSpore]
        self.spellbook = {
            "Spells": {"Firebolt": abilities.Firebolt(), "Enfeeble": abilities.Enfeeble()},
            "Skills": {},
        }
        self.action_stack = [
            {"ability": "Attack", "priority": ActionPriority.LOW},
            {"ability": "Firebolt", "priority": ActionPriority.NORMAL},
            {"ability": "Enfeeble", "priority": ActionPriority.NORMAL},
        ]
        self.level.pro_level = 2


class GiantScorpion(Animal):

    def __init__(self):
        super().__init__(
            name="Giant Scorpion",
            health=random.randint(13, 18),
            mana=2,
            strength=14,
            intel=5,
            wisdom=10,
            con=12,
            charisma=10,
            dex=9,
            attack=16,
            defense=18,
            magic=9,
            magic_def=15,
            exp=random.randint(65, 105),
        )
        self.equipment = {
            "Weapon": items.Claw2(),
            "Armor": items.Carapace(),
            "OffHand": items.Claw(),
            "Ring": items.NoRing(),
            "Pendant": items.NoPendant(),
        }
        self.gold = random.randint(40, 65)
        self.inventory["Scorpion Venom"] = [items.ScorpionVenom]
        self.resistance["Poison"] = 0.25
        self.resistance["Physical"] = 0.25
        self.spellbook["Skills"]["Piercing Strike"] = abilities.PiercingStrike()
        self.action_stack = [
            {"ability": "Attack", "priority": ActionPriority.NORMAL},
            {"ability": "Piercing Strike", "priority": ActionPriority.NORMAL},
        ]
        self.level.pro_level = 2
        self.picture = "giantscorpion.txt"


class Warrior(Humanoid):

    def __init__(self):
        super().__init__(
            name="Warrior",
            health=random.randint(22, 31),
            mana=25,
            strength=14,
            intel=10,
            wisdom=8,
            con=12,
            charisma=10,
            dex=10,
            attack=14,
            defense=14,
            magic=14,
            magic_def=12,
            exp=random.randint(65, 110),
        )
        self.equipment = {
            "Weapon": items.Jian(),
            "Armor": items.ChainMail(),
            "OffHand": items.NoOffHand(),
            "Ring": items.NoRing(),
            "Pendant": items.NoPendant(),
        }
        self.gold = random.randint(25, 100)
        self.inventory["Scrap Metal"] = [items.ScrapMetal]
        self.spellbook = {
            "Spells": {},
            "Skills": {
                "Piercing Strike": abilities.PiercingStrike(),
                "Disarm": abilities.Disarm(),
                "Parry": abilities.Parry(),
            },
        }
        self.action_stack = [
            {"ability": "Attack", "priority": ActionPriority.NORMAL},
            {"ability": "Piercing Strike", "priority": ActionPriority.NORMAL},
            {
                "ability": "Disarm",
                "priority": ActionPriority.LOW,
                "priority_if": {
                    "target_has_weapon": True,
                    "priority": ActionPriority.HIGH,
                    "else": ActionPriority.SKIP,
                },
            },
        ]
        self.level.pro_level = 2
        self.picture = "fighter.txt"


class Harpy(Monster):

    def __init__(self):
        super().__init__(
            name="Harpy",
            health=random.randint(18, 25),
            mana=23,
            strength=18,
            intel=13,
            wisdom=13,
            con=14,
            charisma=14,
            dex=23,
            attack=12,
            defense=15,
            magic=18,
            magic_def=14,
            exp=random.randint(65, 115),
        )
        self.equipment = {
            "Weapon": items.Claw2(),
            "Armor": items.NoArmor(),
            "OffHand": items.Claw(),
            "Ring": items.NoRing(),
            "Pendant": items.NoPendant(),
        }
        self.gold = random.randint(50, 75)
        self.inventory["Feather"] = [items.Feather]
        self.flying = True
        self.spellbook = {
            "Spells": {"Berserk": abilities.Berserk()},
            "Skills": {"Screech": abilities.Screech()},
        }
        self.action_stack = [
            {"ability": "Attack", "priority": ActionPriority.NORMAL},
            {"ability": "Screech", "priority": ActionPriority.NORMAL},
            {"ability": "Berserk", "priority": ActionPriority.LOW},
        ]
        self.level.pro_level = 2
        self.picture = "harpy.txt"


class Naga(Monster):

    def __init__(self):
        super().__init__(
            name="Naga",
            health=random.randint(22, 28),
            mana=17,
            strength=15,
            intel=13,
            wisdom=15,
            con=15,
            charisma=12,
            dex=17,
            attack=17,
            defense=16,
            magic=13,
            magic_def=16,
            exp=random.randint(67, 118),
        )
        self.equipment = {
            "Weapon": items.Partisan(),
            "Armor": items.NoArmor(),
            "OffHand": items.NoOffHand(),
            "Ring": items.NoRing(),
            "Pendant": items.NoPendant(),
        }
        self.gold = random.randint(55, 75)
        self.spellbook = {
            "Spells": {"Silence": abilities.Silence()},
            "Skills": {"Double Strike": abilities.DoubleStrike()},
        }
        self.resistance["Electric"] = -0.5
        self.resistance["Water"] = 0.75
        self.action_stack = [
            {"ability": "Attack", "priority": ActionPriority.NORMAL},
            {"ability": "Double Strike", "priority": ActionPriority.NORMAL},
            {
                "ability": "Silence",
                "priority": ActionPriority.NORMAL,
                "priority_if": {
                    "target_status": "Silence",
                    "priority": ActionPriority.SKIP,
                    "else": ActionPriority.NORMAL,
                },
            },
        ]
        self.level.pro_level = 2
        self.picture = "naga.txt"


class Clannfear(Fiend):

    def __init__(self):
        super().__init__(
            name="Clannfear",
            health=random.randint(28, 38),
            mana=55,
            strength=19,
            intel=10,
            wisdom=12,
            con=16,
            charisma=12,
            dex=16,
            attack=15,
            defense=22,
            magic=14,
            magic_def=16,
            exp=random.randint(77, 130),
        )
        self.equipment = {
            "Weapon": items.DemonClaw(),
            "Armor": items.AnimalHide(),
            "OffHand": items.DemonClaw(),
            "Ring": items.NoRing(),
            "Pendant": items.NoPendant(),
        }
        self.gold = random.randint(65, 92)
        self.spellbook = {
            "Spells": {},
            "Skills": {
                "Trip": abilities.Trip(),
                "Charge": abilities.Charge(),
                "Double Strike": abilities.DoubleStrike(),
            },
        }
        self.resistance["Fire"] = 0.75
        self.resistance["Electric"] = -0.5
        self.action_stack = [
            {"ability": "Attack", "priority": ActionPriority.NORMAL},
            {"ability": "Trip", "priority": ActionPriority.NORMAL},
            {"ability": "Charge", "priority": ActionPriority.HIGH},
            {"ability": "Double Strike", "priority": ActionPriority.HIGH},
        ]
        self.level.pro_level = 2
        self.picture = "clannfear.txt"


class Xorn(Elemental):
    """
    Earth elemental; rare drop to obtain summon Dilong
    """

    def __init__(self):
        super().__init__(
            name="Xorn",
            health=random.randint(27, 33),
            mana=40,
            strength=16,
            intel=11,
            wisdom=12,
            con=17,
            charisma=10,
            dex=12,
            attack=16,
            defense=19,
            magic=17,
            magic_def=17,
            exp=random.randint(74, 121),
        )
        self.equipment = {
            "Weapon": items.Claw(),
            "Armor": items.NoArmor(),
            "OffHand": items.Claw(),
            "Ring": items.NoRing(),
            "Pendant": items.NoPendant(),
        }
        self.gold = random.randint(61, 99)
        self.inventory["Scrap Metal"] = [items.ScrapMetal]
        self.inventory["Chiryu Koma"] = [items.ChiryuKoma]
        self.spellbook = {
            "Spells": {"Tremor": abilities.Tremor()},
            "Skills": {"ConsumeItem": abilities.ConsumeItem()},
        }
        self.resistance["Electric"] = 0.5
        self.resistance["Water"] = -0.5
        self.resistance["Earth"] = 1.0
        self.resistance["Poison"] = 1.0
        self.status_immunity = ["Poison", "Stone"]
        self.action_stack = [
            {"ability": "Attack", "priority": ActionPriority.NORMAL},
            {"ability": "Tremor", "priority": ActionPriority.NORMAL},
            {"ability": "ConsumeItem", "priority": ActionPriority.NORMAL},
        ]
        self.level.pro_level = 2
        self.picture = "xorn.txt"


class SteelPredator(Construct):

    def __init__(self):
        super().__init__(
            name="Steel Predator",
            health=random.randint(27, 33),
            mana=40,
            strength=17,
            intel=9,
            wisdom=12,
            con=14,
            charisma=12,
            dex=19,
            attack=18,
            defense=21,
            magic=11,
            magic_def=16,
            exp=random.randint(85, 129),
        )
        self.equipment = {
            "Weapon": items.Claw2(),
            "Armor": items.MetalPlating(),
            "OffHand": items.Claw(),
            "Ring": items.NoRing(),
            "Pendant": items.NoPendant(),
        }
        self.gold = random.randint(65, 110)
        self.status_effects["Blind"] = StatusEffect(True, -1)
        self.inventory["Scrap Metal"] = [items.ScrapMetal]
        self.spellbook = {
            "Spells": {"Silence": abilities.Silence()},
            "Skills": {"Charge": abilities.Charge(), "Destroy Metal": abilities.DestroyMetal()},
        }
        self.resistance["Fire"] = 0.5
        self.resistance["Ice"] = 0.5
        self.resistance["Electric"] = 0.5
        self.resistance["Water"] = -0.75
        self.resistance["Earth"] = 0.0
        self.action_stack = [
            {"ability": "Attack", "priority": ActionPriority.NORMAL},
            {"ability": "Charge", "priority": ActionPriority.NORMAL},
            {"ability": "Destroy Metal", "priority": ActionPriority.NORMAL},
            {
                "ability": "Silence",
                "priority": ActionPriority.NORMAL,
                "priority_if": {
                    "target_status": "Silence",
                    "priority": ActionPriority.SKIP,
                    "else": ActionPriority.NORMAL,
                },
            },
        ]
        self.level.pro_level = 2
        self.picture = "steelpredator.txt"


class Pseudodragon(Dragon):
    """
    Level 2 Boss
    """

    def __init__(self):
        super().__init__(
            name="Pseudodragon",
            health=250,
            mana=100,
            strength=28,
            intel=26,
            wisdom=24,
            con=20,
            charisma=20,
            dex=18,
            attack=38,
            defense=30,
            magic=42,
            magic_def=40,
            exp=800,
        )
        self.gold = 1500
        self.equipment = {
            "Weapon": items.DragonClaw(),
            "Armor": items.DragonScale(),
            "OffHand": items.DragonClaw(),
            "Ring": items.NoRing(),
            "Pendant": items.NoPendant(),
        }
        self.inventory["Item"] = [items.random_item(3)]
        self.inventory["Old Key"] = [items.OldKey]
        self.spellbook = {
            "Spells": {
                "Fireball": abilities.Fireball(),
                "Blinding Fog": abilities.BlindingFog(),
                "Dispel": abilities.Dispel(),
            },
            "Skills": {
                "Gold Toss": abilities.GoldToss(),
                "Dragon Breath (Fire)": abilities.DragonBreathFire(),
                "Goad": abilities.Goad(),
            },
        }
        self.action_stack = [
            {"ability": "Attack", "priority": ActionPriority.NORMAL},
            {"ability": "Fireball", "priority": ActionPriority.NORMAL},
            {
                "ability": "Dragon Breath (Fire)",
                "priority": ActionPriority.LOW,
                "delay": 2,
                "telegraph": "inhaling deeply, flames flickering in its throat",
            },
            {"ability": "Blinding Fog", "priority": ActionPriority.LOW},
            {"ability": "Dispel", "priority": ActionPriority.LOW},
            {"ability": "Gold Toss", "priority": ActionPriority.NORMAL},
            {"ability": "Goad", "priority": ActionPriority.NORMAL},
        ]
        self.level.pro_level = 2
        self.sight = True
        self.picture = "pseudodragon.txt"

    def special_attack(self, target: Character) -> str:
        return abilities.BreatheFire().use(self, target, typ="Fire")


class Nightmare(Fiend):
    """
    Level 2 Extra Boss - guards second of six relics (QUADRATA) required to beat the final boss
    """

    def __init__(self):
        super().__init__(
            name="Nightmare",
            health=410,
            mana=100,
            strength=30,
            intel=17,
            wisdom=15,
            con=22,
            charisma=16,
            dex=15,
            attack=58,
            defense=42,
            magic=46,
            magic_def=38,
            exp=2000,
        )
        self.equipment = {
            "Weapon": items.NightmareHoof(),
            "Armor": items.AnimalHide2(),
            "OffHand": items.NightmareHoof(),
            "Ring": items.NoRing(),
            "Pendant": items.NoPendant(),
        }
        self.gold = 2500
        self.inventory["Item"] = [items.random_item(4)]
        self.inventory["Old Key"] = [items.OldKey]
        self.spellbook = {
            "Spells": {"Sleep": abilities.Sleep(), "Fireball": abilities.Fireball()},
            "Skills": {
                "Stomp": abilities.Stomp(),
                "True Strike": abilities.TrueStrike(),
                "Nightmare Fuel": abilities.NightmareFuel(),
            },
        }
        self.resistance["Fire"] = 1.0
        self.resistance["Ice"] = -0.25
        self.resistance["Physical"] = 0.5
        self.flying = True
        self.action_stack = [
            {"ability": "Attack", "priority": ActionPriority.NORMAL},
            {"ability": "Stomp", "priority": ActionPriority.NORMAL},
            {"ability": "True Strike", "priority": ActionPriority.NORMAL},
            {"ability": "Sleep", "priority": ActionPriority.NORMAL},
            {"ability": "Fireball", "priority": ActionPriority.NORMAL},
            {
                "ability": "Nightmare Fuel",
                "priority": ActionPriority.LOW,
                "priority_if": {
                    "target_status": "Sleep",
                    "priority": ActionPriority.HIGH,
                    "else": ActionPriority.LOW,
                },
            },
        ]
        self.level.pro_level = 3
        self.sight = True
        self.picture = "nightmare.txt"

    def special_attack(self, target: Character) -> str:
        return super().special_attack(target)
