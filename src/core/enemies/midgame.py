"""Enemy implementations for the middle dungeon and Funhouse."""

from __future__ import annotations

from src.core.randomness import gameplay_random as random

from .. import abilities, items
from ..character import Character, Combat, Resource, Stats
from ..combat.action_queue import ActionPriority
from .base import (
    Animal,
    Construct,
    Dragon,
    Elemental,
    Fey,
    Fiend,
    Humanoid,
    Monster,
    Slime,
    Undead,
    _build_spellbook,
    _fixed_resistances,
)


# Level 3
class Acolyte(Humanoid):
    """Early holy spellcaster with healing and countermagic."""

    def __init__(self):
        super().__init__(
            name="Acolyte",
            health=random.randint(34, 46),
            mana=90,
            strength=9,
            intel=22,
            wisdom=24,
            con=13,
            charisma=18,
            dex=12,
            attack=12,
            defense=18,
            magic=28,
            magic_def=25,
            exp=random.randint(145, 210),
        )
        self.equipment = {
            "Weapon": items.Kukri(),
            "Armor": items.WizardRobe(),
            "OffHand": items.TomeKnowledge(),
            "Ring": items.NoRing(),
            "Pendant": items.NoPendant(),
        }
        self.gold = random.randint(28, 48)
        self.spellbook = {
            "Spells": {"Holy": abilities.Holy(), "Heal": abilities.Heal()},
            "Skills": {"Counterspell": abilities.Counterspell()},
        }
        self.action_stack = [
            {"ability": "Holy", "priority": ActionPriority.NORMAL},
            {
                "ability": "Heal",
                "priority": ActionPriority.NORMAL,
                "priority_if": [
                    {"condition": "self_hp_pct_lt", "value": 55, "priority": ActionPriority.HIGH}
                ],
            },
            {"ability": "Counterspell", "priority": ActionPriority.NORMAL},
        ]
        self.level.pro_level = 2
        self.picture = "disciple.txt"


class WarTurtle(Animal):
    """Spiked turtle that can retreat into a destructible shell."""

    def __init__(self):
        super().__init__(
            name="War Turtle",
            health=random.randint(66, 84),
            mana=55,
            strength=23,
            intel=9,
            wisdom=17,
            con=30,
            charisma=8,
            dex=7,
            attack=25,
            defense=38,
            magic=14,
            magic_def=28,
            exp=random.randint(225, 310),
        )
        self.equipment = {
            "Weapon": items.Bite2(),
            "Armor": items.AnimalHide(),
            "OffHand": items.NoOffHand(),
            "Ring": items.NoRing(),
            "Pendant": items.NoPendant(),
        }
        self.gold = random.randint(36, 60)
        self.spellbook = {
            "Spells": {"Reflect": abilities.Reflect()},
            "Skills": {"Headbutt": abilities.Headbutt(), "Retract": abilities.Retract()},
        }
        self.resistance.update(
            {
                "Water": 0.75,
                "Poison": 0.25,
                "Physical": 0.50,
                "Electric": -0.50,
            }
        )
        self.action_stack = [
            {"ability": "Attack", "priority": ActionPriority.NORMAL},
            {"ability": "Headbutt", "priority": ActionPriority.NORMAL},
            {"ability": "Reflect", "priority": ActionPriority.NORMAL},
            {
                "ability": "Retract",
                "priority": ActionPriority.LOW,
                "priority_if": [
                    {"condition": "self_hp_pct_lt", "value": 40, "priority": ActionPriority.HIGH}
                ],
            },
        ]
        self.single_use_abilities = {"Retract"}
        self.level.pro_level = 3
        self.picture = "battletoad.txt"


class WaywardPriest(Humanoid):
    """Dungeon healer whose Holy magic destabilizes its victims."""

    def __init__(self):
        super().__init__(
            name="Wayward Priest",
            health=random.randint(48, 64),
            mana=125,
            strength=11,
            intel=25,
            wisdom=29,
            con=17,
            charisma=25,
            dex=13,
            attack=14,
            defense=22,
            magic=36,
            magic_def=34,
            exp=random.randint(245, 335),
        )
        self.equipment = {
            "Weapon": items.HolyStaff(),
            "Armor": items.WizardRobe(),
            "OffHand": items.NoOffHand(),
            "Ring": items.NoRing(),
            "Pendant": items.NoPendant(),
        }
        self.gold = random.randint(48, 76)
        self.spellbook = {
            "Spells": {
                "Heal II": abilities.Heal2(),
                "Cleanse": abilities.Cleanse(),
                "Resist Shadow": abilities.ResistShadow(),
                "Holy II": abilities.Holy2(),
            },
            "Skills": {"Dazed or Confused": abilities.DazedOrConfused()},
        }
        self.resistance.update({"Holy": 0.25, "Shadow": -0.25})
        self.action_stack = [
            {"ability": "Holy II", "priority": ActionPriority.NORMAL},
            {
                "ability": "Heal II",
                "priority": ActionPriority.NORMAL,
                "priority_if": [
                    {"condition": "self_hp_pct_lt", "value": 60, "priority": ActionPriority.HIGH}
                ],
            },
            {"ability": "Cleanse", "priority": ActionPriority.NORMAL},
            {"ability": "Resist Shadow", "priority": ActionPriority.NORMAL},
        ]
        self.level.pro_level = 3
        self.picture = "disciple.txt"


class Direbear(Animal):

    def __init__(self):
        super().__init__(
            name="Direbear",
            health=random.randint(55, 70),
            mana=30,
            strength=24,
            intel=6,
            wisdom=6,
            con=24,
            charisma=12,
            dex=17,
            attack=28,
            defense=28,
            magic=13,
            magic_def=15,
            exp=random.randint(210, 310),
        )
        self.equipment = {
            "Weapon": items.BearClaw(),
            "Armor": items.AnimalHide(),
            "OffHand": items.BearClaw(),
            "Ring": items.NoRing(),
            "Pendant": items.NoPendant(),
        }
        self.gold = random.randint(40, 65)
        self.inventory["Leather"] = [items.Leather]
        self.spellbook = {
            "Spells": {},
            "Skills": {"Piercing Strike": abilities.PiercingStrike(), "Charge": abilities.Charge()},
        }
        self.resistance["Physical"] = 0.25
        self.action_stack = [
            {"ability": "Attack", "priority": ActionPriority.NORMAL},
            {"ability": "Piercing Strike", "priority": ActionPriority.NORMAL},
            {"ability": "Charge", "priority": ActionPriority.NORMAL},
        ]
        self.level.pro_level = 3
        self.picture = "direbear.txt"


class Direbear2(Direbear):
    """
    Transform Level 2 creature
    """

    def __init__(self):
        super().__init__()
        self.stats = Stats(0, 0, 0, 0, 0, 0)
        self.combat = Combat(0, 0, 0, 0)


class Giant(Humanoid):

    def __init__(self):
        super().__init__(
            name="Giant",
            health=random.randint(62, 82),
            mana=20,
            strength=30,
            intel=8,
            wisdom=10,
            con=28,
            charisma=12,
            dex=12,
            attack=30,
            defense=30,
            magic=12,
            magic_def=20,
            exp=random.randint(235, 325),
        )
        self.equipment = {
            "Weapon": items.SpikeMaul(),
            "Armor": items.Cuirboulli(),
            "OffHand": items.NoOffHand(),
            "Ring": items.NoRing(),
            "Pendant": items.NoPendant(),
        }
        self.gold = random.randint(55, 85)
        self.spellbook = {
            "Spells": {},
            "Skills": {
                "Charge": abilities.Charge(),
                "Mortal Strike": abilities.MortalStrike(),
                "Dishearten": abilities.Dishearten(),
            },
        }
        self.resistance.update(
            {
                "Fire": -0.25,
                "Ice": -0.25,
                "Electric": -0.25,
                "Water": -0.25,
                "Earth": -0.25,
                "Wind": -0.25,
                "Holy": -0.50,
                "Shadow": -0.20,
                "Poison": 0.50,
                "Physical": 0.25,
            }
        )
        self.action_stack = [
            {"ability": "Attack", "priority": ActionPriority.NORMAL},
            {"ability": "Charge", "priority": ActionPriority.NORMAL},
            {"ability": "Mortal Strike", "priority": ActionPriority.NORMAL},
            {"ability": "Dishearten", "priority": ActionPriority.NORMAL},
        ]
        self.level.pro_level = 4
        self.picture = "giant.txt"


class Unicorn(Fey):
    """Dangerous holy fey that heals from radiant magic."""

    def __init__(self):
        super().__init__(
            name="Unicorn",
            health=random.randint(92, 118),
            mana=165,
            strength=28,
            intel=27,
            wisdom=32,
            con=27,
            charisma=34,
            dex=28,
            attack=38,
            defense=40,
            magic=47,
            magic_def=46,
            exp=random.randint(440, 575),
        )
        self.equipment = {
            "Weapon": items.UnicornHorn(),
            "Armor": items.AnimalHide(),
            "OffHand": items.NoOffHand(),
            "Ring": items.NoRing(),
            "Pendant": items.NoPendant(),
        }
        self.gold = random.randint(85, 130)
        self.spellbook = {
            "Spells": {"Holy III": abilities.Holy3(), "Regen III": abilities.Regen3()},
            "Skills": {"Stomp": abilities.Stomp(), "Gore": abilities.Gore()},
        }
        self.resistance.update(
            {
                "Holy": 1.50,
                "Shadow": -0.25,
                "Poison": 1.0,
                "Physical": 0.25,
            }
        )
        self.status_immunity = ["Poison"]
        self.action_stack = [
            {"ability": "Attack", "priority": ActionPriority.NORMAL},
            {"ability": "Holy III", "priority": ActionPriority.NORMAL},
            {
                "ability": "Regen III",
                "priority": ActionPriority.NORMAL,
                "priority_if": [
                    {"condition": "self_hp_pct_lt", "value": 65, "priority": ActionPriority.HIGH}
                ],
            },
            {"ability": "Stomp", "priority": ActionPriority.NORMAL},
            {"ability": "Gore", "priority": ActionPriority.NORMAL},
        ]
        self.level.pro_level = 5
        self.picture = "unicorn.txt"


class Owlbear(Monster):

    def __init__(self):
        super().__init__(
            name="Owlbear",
            health=random.randint(58, 76),
            mana=75,
            strength=23,
            intel=18,
            wisdom=22,
            con=24,
            charisma=12,
            dex=16,
            attack=26,
            defense=29,
            magic=34,
            magic_def=32,
            exp=random.randint(240, 335),
        )
        self.equipment = {
            "Weapon": items.Claw2(),
            "Armor": items.AnimalHide(),
            "OffHand": items.Claw2(),
            "Ring": items.NoRing(),
            "Pendant": items.NoPendant(),
        }
        self.gold = random.randint(45, 70)
        self.inventory["Feather"] = [items.Feather]
        self.inventory["Leather"] = [items.Leather]
        self.spellbook = {
            "Spells": {
                "Shock": abilities.Shock(),
                "Wind Speed": abilities.WindSpeed(),
                "Regen": abilities.Regen(),
            },
            "Skills": {},
        }
        self.resistance["Electric"] = 0.25
        self.resistance["Wind"] = 0.25
        self.action_stack = [
            {"ability": "Attack", "priority": ActionPriority.NORMAL},
            {"ability": "Shock", "priority": ActionPriority.NORMAL},
            {"ability": "Wind Speed", "priority": ActionPriority.NORMAL},
            {
                "ability": "Regen",
                "priority": ActionPriority.NORMAL,
                "priority_if": [
                    {"condition": "self_hp_pct_lt", "value": 50, "priority": ActionPriority.HIGH},
                    {"condition": "self_status", "value": "Regen", "priority": ActionPriority.LOW},
                ],
            },
        ]
        self.level.pro_level = 3
        self.picture = "owlbear.txt"


class Ghoul(Undead):

    def __init__(self):
        super().__init__(
            name="Ghoul",
            health=random.randint(42, 60),
            mana=50,
            strength=25,
            intel=10,
            wisdom=8,
            con=24,
            charisma=11,
            dex=12,
            attack=26,
            defense=28,
            magic=16,
            magic_def=17,
            exp=random.randint(210, 290),
        )
        self.equipment = {
            "Weapon": items.Bite(),
            "Armor": items.NoArmor(),
            "OffHand": items.NoOffHand(),
            "Ring": items.NoRing(),
            "Pendant": items.NoPendant(),
        }
        self.gold = random.randint(35, 45)
        self.spellbook = {"Spells": {"Disease Breath": abilities.DiseaseBreath()}, "Skills": {}}
        self.action_stack = [
            {"ability": "Attack", "priority": ActionPriority.NORMAL},
            {"ability": "Disease Breath", "priority": ActionPriority.LOW},
        ]
        self.level.pro_level = 3
        self.picture = "ghoul.txt"


class PitViper(Animal):

    def __init__(self):
        super().__init__(
            name="Pit Viper",
            health=random.randint(38, 50),
            mana=30,
            strength=17,
            intel=6,
            wisdom=8,
            con=16,
            charisma=10,
            dex=18,
            attack=25,
            defense=24,
            magic=12,
            magic_def=19,
            exp=random.randint(215, 290),
        )
        self.equipment = {
            "Weapon": items.SnakeFang2(),
            "Armor": items.SnakeScales(),
            "OffHand": items.NoOffHand(),
            "Ring": items.NoRing(),
            "Pendant": items.NoPendant(),
        }
        self.gold = random.randint(50, 85)
        self.inventory["Snake Skin"] = [items.SnakeSkin]
        self.inventory["Viper Venom"] = [items.ViperVenom]
        self.spellbook = {"Spells": {}, "Skills": {"Double Strike": abilities.DoubleStrike()}}
        self.resistance["Poison"] = 0.25
        self.action_stack = [
            {"ability": "Attack", "priority": ActionPriority.NORMAL},
            {"ability": "Double Strike", "priority": ActionPriority.NORMAL},
        ]
        self.level.pro_level = 3
        self.picture = "snake.txt"


class Disciple(Humanoid):

    def __init__(self):
        super().__init__(
            name="Disciple",
            health=random.randint(40, 50),
            mana=70,
            strength=16,
            intel=17,
            wisdom=15,
            con=16,
            charisma=12,
            dex=16,
            attack=14,
            defense=20,
            magic=38,
            magic_def=36,
            exp=random.randint(210, 290),
        )
        self.equipment = {
            "Weapon": items.SerpentStaff(),
            "Armor": items.SilverCloak(),
            "OffHand": items.NoOffHand(),
            "Ring": items.NoRing(),
            "Pendant": items.NoPendant(),
        }
        self.gold = random.randint(55, 95)
        self.spellbook = {
            "Spells": {
                "Firebolt": abilities.Firebolt(),
                "Ice Lance": abilities.IceLance(),
                "Shock": abilities.Shock(),
                "Enfeeble": abilities.Enfeeble(),
                "Boost": abilities.Boost(),
            },
            "Skills": {},
        }
        self.action_stack = [
            {"ability": "Attack", "priority": ActionPriority.NORMAL},
            {"ability": "Firebolt", "priority": ActionPriority.NORMAL},
            {"ability": "Ice Lance", "priority": ActionPriority.NORMAL},
            {"ability": "Shock", "priority": ActionPriority.NORMAL},
            {"ability": "Enfeeble", "priority": ActionPriority.NORMAL},
            {
                "ability": "Boost",
                "priority": ActionPriority.NORMAL,
                "priority_if": {
                    "self_stat": "Magic",
                    "priority": ActionPriority.LOW,
                    "else": ActionPriority.NORMAL,
                },
            },
        ]
        self.level.pro_level = 3
        self.picture = "disciple.txt"


class BlackSlime(Slime):
    """
    Stupefy - Rank 1 enemy spell learnable by Diviner/Astromancer.
    """

    def __init__(self):
        super().__init__(
            name="Black Slime",
            health=random.randint(48, 90),
            mana=80,
            strength=13,
            intel=25,
            wisdom=30,
            con=15,
            charisma=12,
            dex=6,
            attack=12,
            defense=24,
            magic=35,
            magic_def=200,
            exp=random.randint(185, 360),
        )
        self.equipment = {
            "Weapon": items.NoWeapon(),
            "Armor": items.NoArmor(),
            "OffHand": items.NoOffHand(),
            "Ring": items.NoRing(),
            "Pendant": items.NoPendant(),
        }
        self.gold = random.randint(30, 180)
        self.inventory["Fungus Spore"] = [items.FungusSpore]
        self.spellbook = {
            "Spells": {
                "Shadow Bolt": abilities.ShadowBolt(),
                "Corruption": abilities.Corruption(),
                "Curse of Umbra": abilities.CurseUmbra(),
                "Stupefy": abilities.Stupefy(),
            },
            "Skills": {},
        }
        self.action_stack = [
            {"ability": "Attack", "priority": ActionPriority.LOW},
            {"ability": "Shadow Bolt", "priority": ActionPriority.NORMAL},
            {"ability": "Corruption", "priority": ActionPriority.NORMAL},
            {"ability": "Curse of Umbra", "priority": ActionPriority.NORMAL},
            {"ability": "Stupefy", "priority": ActionPriority.NORMAL},
        ]
        self.level.pro_level = 3


class Ogre(Monster):

    def __init__(self):
        super().__init__(
            name="Ogre",
            health=random.randint(40, 50),
            mana=40,
            strength=24,
            intel=18,
            wisdom=14,
            con=20,
            charisma=10,
            dex=14,
            attack=28,
            defense=27,
            magic=30,
            magic_def=31,
            exp=random.randint(215, 295),
        )
        self.equipment = {
            "Weapon": items.SpikeMaul(),
            "Armor": items.Cuirboulli(),
            "OffHand": items.NoOffHand(),
            "Ring": items.NoRing(),
            "Pendant": items.NoPendant(),
        }
        self.gold = random.randint(50, 75)
        self.spellbook = {
            "Spells": {"Magic Missile": abilities.MagicMissile(), "Dispel": abilities.Dispel()},
            "Skills": {"Piercing Strike": abilities.PiercingStrike()},
        }
        self.action_stack = [
            {"ability": "Attack", "priority": ActionPriority.NORMAL},
            {"ability": "Piercing Strike", "priority": ActionPriority.NORMAL},
            {"ability": "Magic Missile", "priority": ActionPriority.NORMAL},
            {
                "ability": "Dispel",
                "priority": ActionPriority.NORMAL,
                "priority_if": {
                    "target_has_positive_effects": True,
                    "priority": ActionPriority.NORMAL,
                    "else": ActionPriority.SKIP,
                },
            },
        ]
        self.level.pro_level = 3
        self.picture = "ogre.txt"


class Alligator(Animal):

    def __init__(self):
        super().__init__(
            name="Alligator",
            health=random.randint(60, 75),
            mana=20,
            strength=26,
            intel=8,
            wisdom=7,
            con=20,
            charisma=10,
            dex=15,
            attack=26,
            defense=27,
            magic=16,
            magic_def=23,
            exp=random.randint(220, 300),
        )
        self.equipment = {
            "Weapon": items.AlligatorTail(),
            "Armor": items.NoArmor(),
            "OffHand": items.Claw(),
            "Ring": items.NoRing(),
            "Pendant": items.NoPendant(),
        }
        self.gold = random.randint(40, 50)
        self.spellbook = {"Spells": {}, "Skills": {"Trip": abilities.Trip()}}
        self.action_stack = [
            {"ability": "Attack", "priority": ActionPriority.NORMAL},
            {"ability": "Trip", "priority": ActionPriority.NORMAL},
        ]
        self.level.pro_level = 3
        self.picture = "alligator.txt"


class Troll(Humanoid):

    def __init__(self):
        super().__init__(
            name="Troll",
            health=random.randint(50, 65),
            mana=20,
            strength=24,
            intel=10,
            wisdom=8,
            con=24,
            charisma=12,
            dex=15,
            attack=25,
            defense=24,
            magic=22,
            magic_def=21,
            exp=random.randint(225, 310),
        )
        self.equipment = {
            "Weapon": items.DoubleAxe(),
            "Armor": items.Cuirboulli(),
            "OffHand": items.NoOffHand(),
            "Ring": items.NoRing(),
            "Pendant": items.NoPendant(),
        }
        self.gold = random.randint(35, 45)
        self.spellbook = {"Spells": {}, "Skills": {"Mortal Strike": abilities.MortalStrike()}}
        self.action_stack = [
            {"ability": "Attack", "priority": ActionPriority.NORMAL},
            {"ability": "Mortal Strike", "priority": ActionPriority.NORMAL},
        ]
        self.level.pro_level = 3
        self.picture = "troll.txt"


class GoldenEagle(Animal):

    def __init__(self):
        super().__init__(
            name="Golden Eagle",
            health=random.randint(40, 50),
            mana=20,
            strength=19,
            intel=15,
            wisdom=15,
            con=17,
            charisma=15,
            dex=25,
            attack=23,
            defense=22,
            magic=25,
            magic_def=26,
            exp=random.randint(230, 320),
        )
        self.equipment = {
            "Weapon": items.Claw2(),
            "Armor": items.NoArmor(),
            "OffHand": items.Claw2(),
            "Ring": items.NoRing(),
            "Pendant": items.NoPendant(),
        }
        self.gold = random.randint(50, 75)
        self.inventory["Feather"] = [items.Feather]
        self.inventory["Bird Fat"] = [items.BirdFat]
        self.spellbook = {"Spells": {}, "Skills": {"Screech": abilities.Screech()}}
        self.flying = True
        self.action_stack = [
            {"ability": "Attack", "priority": ActionPriority.NORMAL},
            {"ability": "Screech", "priority": ActionPriority.NORMAL},
        ]
        self.level.pro_level = 3
        self.picture = "goldeneagle.txt"


class EvilCrusader(Humanoid):

    def __init__(self):
        super().__init__(
            name="Evil Crusader",
            health=random.randint(45, 60),
            mana=50,
            strength=21,
            intel=18,
            wisdom=17,
            con=26,
            charisma=14,
            dex=14,
            attack=24,
            defense=34,
            magic=23,
            magic_def=27,
            exp=random.randint(240, 325),
        )
        self.equipment = {
            "Weapon": items.Pernach(),
            "Armor": items.Splint(),
            "OffHand": items.KiteShield(),
            "Ring": items.NoRing(),
            "Pendant": items.NoPendant(),
        }
        self.gold = random.randint(65, 90)
        self.inventory["Scrap Metal"] = [items.ScrapMetal]
        self.spellbook = {
            "Spells": {"Smite": abilities.Smite2(), "Bless": abilities.Bless()},
            "Skills": {
                "Shield Slam": abilities.ShieldSlam(),
                "Shield Block": abilities.ShieldBlock(),
                "Goad": abilities.Goad(),
            },
        }
        self.resistance["Shadow"] = -0.5
        self.resistance["Holy"] = 0.5
        self.action_stack = [
            {"ability": "Attack", "priority": ActionPriority.NORMAL},
            {"ability": "Shield Slam", "priority": ActionPriority.NORMAL},
            {"ability": "Smite", "priority": ActionPriority.NORMAL},
            {
                "ability": "Bless",
                "priority": ActionPriority.NORMAL,
                "priority_if": {
                    "self_stat_any": ["Attack", "Defense"],
                    "priority": ActionPriority.LOW,
                    "else": ActionPriority.NORMAL,
                },
            },
            {"ability": "Goad", "priority": ActionPriority.NORMAL},
        ]
        self.level.pro_level = 3
        self.picture = "skeleton.txt"


class Werewolf(Monster):
    """ """

    def __init__(self):
        super().__init__(
            name="Werewolf",
            health=random.randint(55, 75),
            mana=85,
            strength=24,
            intel=10,
            wisdom=10,
            con=20,
            charisma=14,
            dex=20,
            attack=28,
            defense=31,
            magic=21,
            magic_def=20,
            exp=random.randint(220, 300),
        )
        self.equipment = {
            "Weapon": items.Claw3(),
            "Armor": items.AnimalHide(),
            "OffHand": items.Claw2(),
            "Ring": items.NoRing(),
            "Pendant": items.NoPendant(),
        }
        self.gold = random.randint(45, 55)
        self.inventory["Leather"] = [items.Leather]
        self.spellbook = {
            "Spells": {},
            "Skills": {"True Strike": abilities.TrueStrike(), "Howl": abilities.Howl()},
        }
        self.resistance["Physical"] = 0.1
        self.action_stack = [
            {"ability": "Attack", "priority": ActionPriority.NORMAL},
            {"ability": "True Strike", "priority": ActionPriority.NORMAL},
            {"ability": "Howl", "priority": ActionPriority.NORMAL},
        ]
        self.level.pro_level = 3
        self.picture = "werewolf.txt"


class Werewolf2(Werewolf):
    """
    Transform Level 3 creature
    """

    def __init__(self):
        super().__init__()
        self.stats = Stats(0, 0, 0, 0, 0, 0)
        self.combat = Combat(0, 0, 0, 0)


class Antlion(Animal):
    """
    modeled after the boss from FF2 (FFIV)
    """

    def __init__(self):
        super().__init__(
            name="Antlion",
            health=random.randint(52, 70),
            mana=70,
            strength=22,
            intel=8,
            wisdom=12,
            con=18,
            charisma=12,
            dex=18,
            attack=26,
            defense=32,
            magic=18,
            magic_def=22,
            exp=random.randint(210, 310),
        )
        self.equipment = {
            "Weapon": items.Pincers2(),
            "Armor": items.Carapace(),
            "OffHand": items.Pincers2(),
            "Ring": items.NoRing(),
            "Pendant": items.NoPendant(),
        }
        self.gold = random.randint(40, 52)
        self.spellbook = {
            "Spells": {},
            "Skills": {
                "Double Strike": abilities.DoubleStrike(),
                "Tunnel": abilities.Tunnel(),
                "Surface": abilities.Surface(),
            },
        }
        self.resistance["Physical"] = 0.25
        self.action_stack = [
            {"ability": "Attack", "priority": ActionPriority.NORMAL},
            {"ability": "Double Strike", "priority": ActionPriority.NORMAL},
            {
                "ability": "Tunnel",
                "priority": ActionPriority.LOW,
                "priority_if": {
                    "self_hp_pct_lt": 0.25,
                    "priority": ActionPriority.HIGH,
                    "else": ActionPriority.SKIP,
                },
            },
            {
                "ability": "Surface",
                "priority": ActionPriority.NORMAL,
                "priority_if": {
                    "tunneled": True,
                    "priority": ActionPriority.HIGH,
                    "else": ActionPriority.SKIP,
                },
            },
        ]
        self.level.pro_level = 3
        self.picture = "antlion.txt"


class InvisibleStalker(Elemental):
    """
    Invisible
    """

    def __init__(self):
        super().__init__(
            name="Invisible Stalker",
            health=random.randint(25, 46),
            mana=60,
            strength=19,
            intel=13,
            wisdom=16,
            con=14,
            charisma=18,
            dex=29,
            attack=21,
            defense=27,
            magic=22,
            magic_def=22,
            exp=random.randint(230, 330),
        )
        self.equipment = {
            "Weapon": items.InvisibleBlade(),
            "Armor": items.NoArmor(),
            "OffHand": items.InvisibleBlade(),
            "Ring": items.NoRing(),
            "Pendant": items.NoPendant(),
        }
        self.gold = random.randint(65, 79)
        self.spellbook = {
            "Spells": {},
            "Skills": {
                "Backstab": abilities.Backstab(),
                "Kidney Punch": abilities.KidneyPunch(),
                "Piercing Strike": abilities.PiercingStrike(),
                "Smoke Screen": abilities.SmokeScreen(),
                "Parry": abilities.Parry(),
            },
        }
        self.resistance["Poison"] = 1.0
        self.status_immunity = ["Poison"]
        self.invisible = True
        self.sight = True
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
            {"ability": "Piercing Strike", "priority": ActionPriority.NORMAL},
            {
                "ability": "Smoke Screen",
                "priority": ActionPriority.LOW,
                "priority_if": {
                    "self_hp_pct_lt": 0.25,
                    "priority": ActionPriority.HIGH,
                    "else": ActionPriority.LOW,
                },
            },
        ]
        self.level.pro_level = 3
        self.picture = "assassin.txt"


class NightHag(Fey):

    def __init__(self):
        super().__init__(
            name="Night Hag",
            health=random.randint(30, 48),
            mana=105,
            strength=16,
            intel=22,
            wisdom=26,
            con=12,
            charisma=14,
            dex=19,
            attack=20,
            defense=26,
            magic=41,
            magic_def=40,
            exp=random.randint(215, 312),
        )
        self.equipment = {
            "Weapon": items.Kris(),
            "Armor": items.SilverCloak(),
            "OffHand": items.InfernalGrimoire(),
            "Ring": items.NoRing(),
            "Pendant": items.NoPendant(),
        }
        self.gold = random.randint(70, 99)
        self.inventory["Hemlock Root"] = [items.HemlockRoot]
        self.spellbook = {
            "Spells": {
                "Sleep": abilities.Sleep(),
                "Enfeeble": abilities.Enfeeble(),
                "Magic Missile": abilities.MagicMissile(),
            },
            "Skills": {"Nightmare Fuel": abilities.NightmareFuel()},
        }
        self.resistance["Fire"] = 0.25
        self.resistance["Cold"] = 0.25
        self.resistance["Physical"] = 0.25
        self.action_stack = [
            {"ability": "Attack", "priority": ActionPriority.NORMAL},
            {"ability": "Magic Missile", "priority": ActionPriority.NORMAL},
            {"ability": "Sleep", "priority": ActionPriority.NORMAL},
            {"ability": "Enfeeble", "priority": ActionPriority.NORMAL},
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
        self.picture = "nighthag.txt"


class NightHag2(NightHag):
    """
    Waitress from tavern after Joffrey is discovered; modeled after Night Hag
    """

    def __init__(self):
        super().__init__()
        self.name = "Mad Waitress"
        self.health = Resource(500, 500)
        self.mana = Resource(300, 300)
        self.stats = Stats(18, 24, 30, 15, 15, 20)
        self.combat = Combat(40, 51, 72, 68)
        self.experience = 2500
        self.gold = 1000
        self.inventory["Brass Key"] = [items.BrassKey]
        self.spellbook["Skills"]["Widow's Wail"] = abilities.WidowsWail()
        self.status_immunity = ["Death", "Stone"]
        # Track form state for sanity transition
        self._form_changed = False
        self.action_stack = [
            {"ability": "Attack", "priority": ActionPriority.NORMAL},
            {"ability": "Magic Missile", "priority": ActionPriority.NORMAL},
            {"ability": "Sleep", "priority": ActionPriority.NORMAL},
            {"ability": "Enfeeble", "priority": ActionPriority.NORMAL},
            {
                "ability": "Nightmare Fuel",
                "priority": ActionPriority.LOW,
                "priority_if": {
                    "target_status": "Sleep",
                    "priority": ActionPriority.HIGH,
                    "else": ActionPriority.LOW,
                },
            },
            {
                "ability": "Widow's Wail",
                "priority": ActionPriority.NORMAL,
                "priority_if": {
                    "self_hp_pct_lt": "0.5",
                    "priority": ActionPriority.HIGH,
                    "else": ActionPriority.NORMAL,
                },
            },
        ]


class Treant(Fey):

    def __init__(self):
        super().__init__(
            name="Treant",
            health=random.randint(52, 78),
            mana=65,
            strength=26,
            intel=16,
            wisdom=21,
            con=20,
            charisma=12,
            dex=16,
            attack=30,
            defense=35,
            magic=37,
            magic_def=43,
            exp=random.randint(235, 320),
        )
        self.equipment = {
            "Weapon": items.NoWeapon(),
            "Armor": items.NoArmor(),
            "OffHand": items.NoOffHand(),
            "Ring": items.NoRing(),
            "Pendant": items.NoPendant(),
        }
        self.gold = random.randint(60, 85)
        self.inventory["Cursed Hops"] = [items.CursedHops]
        self.inventory["Acorn"] = [items.Acorn]
        self.inventory["Vine Seed"] = [items.VineSeed]
        self.spellbook = {
            "Spells": {"Regen": abilities.Regen()},
            "Skills": {
                "Crushing Blow": abilities.CrushingBlow(),
                "Throw Rock": abilities.ThrowRock(),
            },
        }
        self.resistance["Fire"] = -1.0
        self.resistance["Water"] = 1.5
        self.resistance["Poison"] = 1.0
        self.resistance["Physical"] = 0.25
        self.status_immunity = ["Poison"]
        self.action_stack = [
            {"ability": "Attack", "priority": ActionPriority.NORMAL},
            {"ability": "Crushing Blow", "priority": ActionPriority.NORMAL},
            {"ability": "Throw Rock", "priority": ActionPriority.NORMAL},
            {
                "ability": "Regen",
                "priority": ActionPriority.NORMAL,
                "priority_if": [
                    {"condition": "self_hp_pct_lt", "value": 50, "priority": ActionPriority.HIGH},
                    {"condition": "self_status", "value": "Regen", "priority": ActionPriority.LOW},
                ],
            },
        ]
        self.level.pro_level = 3
        self.picture = "treant.txt"


class Ankheg(Monster):

    def __init__(self):
        super().__init__(
            name="Ankheg",
            health=random.randint(45, 69),
            mana=65,
            strength=23,
            intel=17,
            wisdom=14,
            con=19,
            charisma=6,
            dex=14,
            attack=27,
            defense=32,
            magic=21,
            magic_def=23,
            exp=random.randint(240, 330),
        )
        self.equipment = {
            "Weapon": items.Claw3(),
            "Armor": items.Carapace(),
            "OffHand": items.Pincers2(),
            "Ring": items.NoRing(),
            "Pendant": items.NoPendant(),
        }
        self.gold = random.randint(55, 78)
        self.spellbook = {
            "Spells": {},
            "Skills": {"Trip": abilities.Trip(), "Acid Spit": abilities.AcidSpit()},
        }
        self.resistance["Holy"] = -0.25
        self.resistance["Poison"] = 1.0
        self.resistance["Physical"] = 0.1
        self.status_immunity = ["Poison"]
        self.action_stack = [
            {"ability": "Attack", "priority": ActionPriority.NORMAL},
            {"ability": "Trip", "priority": ActionPriority.NORMAL},
            {"ability": "Acid Spit", "priority": ActionPriority.NORMAL},
        ]
        self.level.pro_level = 3
        self.picture = "ankheg.txt"


class Fuath(Monster):
    """
    Unique Underground Spring boss; Fuath is not part of the Xenid roster.
    """

    def __init__(self):
        super().__init__(
            name="Fuath",
            health=340,
            mana=147,
            strength=19,
            intel=14,
            wisdom=18,
            con=14,
            charisma=11,
            dex=15,
            attack=65,
            defense=46,
            magic=75,
            magic_def=82,
            exp=3000,
        )
        self.equipment = {
            "Weapon": items.Pincers2(),
            "Armor": items.NoArmor(),
            "OffHand": items.Pincers2(),
            "Ring": items.NoRing(),
            "Pendant": items.NoPendant(),
        }
        self.spellbook = {
            "Spells": {"Water Jet": abilities.WaterJet(), "Sleep": abilities.Sleep()},
            "Skills": {"Screech": abilities.Screech()},
        }
        self.resistance["Electric"] = -0.75
        self.resistance["Water"] = 1.25
        self.resistance["Shadow"] = 0.25
        self.resistance["Holy"] = -0.25
        self.action_stack = [
            {"ability": "Attack", "priority": ActionPriority.NORMAL},
            {"ability": "Water Jet", "priority": ActionPriority.NORMAL},
            {"ability": "Sleep", "priority": ActionPriority.NORMAL},
            {"ability": "Screech", "priority": ActionPriority.NORMAL},
        ]
        self.level.pro_level = 3
        self.picture = "fuath.txt"


class Cockatrice(Monster):
    """
    Level 3 Boss
    """

    def __init__(self):
        super().__init__(
            name="Cockatrice",
            health=580,
            mana=99,
            strength=30,
            intel=16,
            wisdom=15,
            con=16,
            charisma=16,
            dex=22,
            attack=53,
            defense=48,
            magic=71,
            magic_def=62,
            exp=3500,
        )
        self.equipment = {
            "Weapon": items.Claw3(),
            "Armor": items.NoArmor(),
            "OffHand": items.DragonTail(),
            "Ring": items.NoRing(),
            "Pendant": items.NoPendant(),
        }
        self.gold = 5000
        self.inventory["Pendant"] = [items.random_item(4)]
        self.inventory["Old Key"] = [items.OldKey]
        self.inventory["Feather"] = [items.Feather]
        self.spellbook = {
            "Spells": {"Petrify": abilities.Petrify()},
            "Skills": {"Screech": abilities.Screech(), "Double Strike": abilities.DoubleStrike()},
        }
        self.flying = True
        self.status_immunity = ["Death", "Stone"]
        self.action_stack = [
            {"ability": "Attack", "priority": ActionPriority.NORMAL},
            {"ability": "Double Strike", "priority": ActionPriority.NORMAL},
            {"ability": "Screech", "priority": ActionPriority.NORMAL},
            {"ability": "Petrify", "priority": ActionPriority.NORMAL},
        ]
        self.level.pro_level = 3
        self.sight = True
        self.picture = "cockatrice.txt"


class Wendigo(Fey):
    """
    Level 3 Special Boss - guards third of six relics (HEXAGONUM) required to beat the final boss
    """

    def __init__(self):
        super().__init__(
            name="Wendigo",
            health=750,
            mana=130,
            strength=32,
            intel=16,
            wisdom=19,
            con=21,
            charisma=14,
            dex=22,
            attack=64,
            defense=48,
            magic=71,
            magic_def=62,
            exp=6000,
        )
        self.equipment = {
            "Weapon": items.Bite2(),
            "Armor": items.NoArmor(),
            "OffHand": items.DemonClaw2(),
            "Ring": items.NoRing(),
            "Pendant": items.NoPendant(),
        }
        self.gold = 7500
        self.inventory["Item"] = [items.random_item(5)]
        self.inventory["Old Key"] = [items.OldKey]
        self.spellbook = {
            "Spells": {
                "Regen": abilities.Regen2(),
                "Terrify": abilities.Terrify(),
                "Curse of Frailty": abilities.CurseFrailty(),
                "Berserk": abilities.Berserk(),
            },
            "Skills": {
                "Double Strike": abilities.DoubleStrike(),
                "Crushing Blow": abilities.CrushingBlow(),
            },
        }
        self.resistance["Fire"] = -0.75
        self.resistance["Ice"] = 1
        self.resistance["Poison"] = 1
        self.status_immunity = ["Poison", "Death"]
        self.action_stack = [
            {"ability": "Attack", "priority": ActionPriority.NORMAL},
            {"ability": "Double Strike", "priority": ActionPriority.NORMAL},
            {"ability": "Crushing Blow", "priority": ActionPriority.NORMAL},
            {"ability": "Terrify", "priority": ActionPriority.NORMAL},
            {"ability": "Curse of Frailty", "priority": ActionPriority.NORMAL},
            {"ability": "Berserk", "priority": ActionPriority.NORMAL},
            {
                "ability": "Regen",
                "priority": ActionPriority.NORMAL,
                "priority_if": [
                    {"condition": "self_hp_pct_lt", "value": 50, "priority": ActionPriority.HIGH},
                    {"condition": "self_status", "value": "Regen", "priority": ActionPriority.LOW},
                ],
            },
        ]
        self.level.pro_level = 4
        self.sight = True
        self.picture = "wendigo.txt"


# Level 4
class BrownSlime(Slime):

    def __init__(self):
        super().__init__(
            name="Brown Slime",
            health=random.randint(70, 112),
            mana=85,
            strength=17,
            intel=35,
            wisdom=40,
            con=15,
            charisma=10,
            dex=8,
            attack=22,
            defense=32,
            magic=55,
            magic_def=300,
            exp=random.randint(390, 660),
        )
        self.equipment = {
            "Weapon": items.NoWeapon(),
            "Armor": items.NoArmor(),
            "OffHand": items.NoOffHand(),
            "Ring": items.NoRing(),
            "Pendant": items.NoPendant(),
        }
        self.gold = random.randint(150, 280)
        self.inventory["Fungus Spore"] = [items.FungusSpore]
        self.spellbook = {
            "Spells": {"Mudslide": abilities.Mudslide(), "Enfeeble": abilities.Enfeeble()},
            "Skills": {},
        }
        self.action_stack = [
            {"ability": "Attack", "priority": ActionPriority.NORMAL},
            {"ability": "Mudslide", "priority": ActionPriority.NORMAL},
            {"ability": "Enfeeble", "priority": ActionPriority.NORMAL},
        ]
        self.level.pro_level = 4


class Gargoyle(Elemental):

    def __init__(self):
        super().__init__(
            name="Gargoyle",
            health=random.randint(55, 75),
            mana=20,
            strength=26,
            intel=10,
            wisdom=12,
            con=18,
            charisma=15,
            dex=21,
            attack=33,
            defense=36,
            magic=32,
            magic_def=37,
            exp=random.randint(410, 530),
        )
        self.equipment = {
            "Weapon": items.Claw3(),
            "Armor": items.StoneArmor(),
            "OffHand": items.Claw2(),
            "Ring": items.NoRing(),
            "Pendant": items.NoPendant(),
        }
        self.gold = random.randint(75, 125)
        self.spellbook = {
            "Spells": {"Blinding Fog": abilities.BlindingFog()},
            "Skills": {"Piercing Strike": abilities.PiercingStrike()},
        }
        self.flying = True
        self.resistance["Poison"] = 1
        self.status_immunity = ["Poison", "Stone"]
        self.action_stack = [
            {"ability": "Attack", "priority": ActionPriority.NORMAL},
            {"ability": "Piercing Strike", "priority": ActionPriority.NORMAL},
            {"ability": "Blinding Fog", "priority": ActionPriority.NORMAL},
        ]
        self.level.pro_level = 4
        self.picture = "gargoyle.txt"


class Necromancer(Humanoid):

    def __init__(self):
        super().__init__(
            name="Necromancer",
            health=random.randint(40, 65),
            mana=150,
            strength=14,
            intel=22,
            wisdom=18,
            con=14,
            charisma=12,
            dex=13,
            attack=26,
            defense=27,
            magic=50,
            magic_def=45,
            exp=random.randint(415, 540),
        )
        self.equipment = {
            "Weapon": items.RuneStaff(),
            "Armor": items.GoldCloak(),
            "OffHand": items.NoOffHand(),
            "Ring": items.NoRing(),
            "Pendant": items.NoPendant(),
        }
        self.gold = random.randint(40, 65)
        self.spellbook = {
            "Spells": {
                "Raise Dead": abilities.RaiseUndeadAlly(),
                "Shadow Bolt": abilities.ShadowBolt(),
                "Enfeeble": abilities.Enfeeble(),
                "Curse of Polydipsia": abilities.CursePolydipsia(),
            },
            "Skills": {},
        }
        self.action_stack = [
            {"ability": "Attack", "priority": ActionPriority.NORMAL},
            {"ability": "Raise Dead", "priority": ActionPriority.HIGH},
            {"ability": "Shadow Bolt", "priority": ActionPriority.NORMAL},
            {"ability": "Enfeeble", "priority": ActionPriority.NORMAL},
            {"ability": "Curse of Polydipsia", "priority": ActionPriority.LOW},
        ]
        self.single_use_abilities = {"Raise Dead"}
        self.level.pro_level = 4
        self.picture = "disciple.txt"


class Chimera(Monster):

    def __init__(self):
        super().__init__(
            name="Chimera",
            health=random.randint(60, 95),
            mana=140,
            strength=26,
            intel=14,
            wisdom=16,
            con=20,
            charisma=14,
            dex=14,
            attack=38,
            defense=36,
            magic=46,
            magic_def=47,
            exp=random.randint(430, 580),
        )
        self.equipment = {
            "Weapon": items.LionPaw(),
            "Armor": items.AnimalHide2(),
            "OffHand": items.LionPaw(),
            "Ring": items.NoRing(),
            "Pendant": items.NoPendant(),
        }
        self.gold = random.randint(100, 250)
        self.spellbook = {
            "Spells": {"Molten Rock": abilities.MoltenRock(), "Dispel": abilities.Dispel()},
            "Skills": {"True Strike": abilities.TrueStrike()},
        }
        self.resistance["Physical"] = 0.5
        self.action_stack = [
            {"ability": "Attack", "priority": ActionPriority.NORMAL},
            {"ability": "True Strike", "priority": ActionPriority.NORMAL},
            {"ability": "Molten Rock", "priority": ActionPriority.NORMAL},
            {
                "ability": "Dispel",
                "priority": ActionPriority.NORMAL,
                "priority_if": {
                    "target_has_positive_effects": True,
                    "priority": ActionPriority.NORMAL,
                    "else": ActionPriority.SKIP,
                },
            },
        ]
        self.level.pro_level = 4
        self.picture = "chimera.txt"


class Dragonkin(Dragon):

    def __init__(self):
        super().__init__(
            name="Dragonkin",
            health=random.randint(80, 115),
            mana=90,
            strength=26,
            intel=10,
            wisdom=18,
            con=20,
            charisma=18,
            dex=19,
            attack=39,
            defense=34,
            magic=28,
            magic_def=42,
            exp=random.randint(450, 680),
        )
        self.equipment = {
            "Weapon": items.Halberd(),
            "Armor": items.Breastplate(),
            "OffHand": items.KiteShield(),
            "Ring": items.NoRing(),
            "Pendant": items.NoPendant(),
        }
        self.gold = random.randint(150, 300)
        self.inventory["Scrap Metal"] = [items.ScrapMetal]
        self.spellbook = {
            "Spells": {},
            "Skills": {
                "Disarm": abilities.Disarm(),
                "Charge": abilities.Charge(),
                "Goad": abilities.Goad(),
            },
        }
        self.flying = True
        self.action_stack = [
            {"ability": "Attack", "priority": ActionPriority.NORMAL},
            {"ability": "Charge", "priority": ActionPriority.NORMAL},
            {
                "ability": "Disarm",
                "priority": ActionPriority.LOW,
                "priority_if": {
                    "target_has_weapon": True,
                    "priority": ActionPriority.HIGH,
                    "else": ActionPriority.SKIP,
                },
            },
            {"ability": "Goad", "priority": ActionPriority.NORMAL},
        ]
        self.level.pro_level = 4
        self.picture = "dragonkin.txt"


class Griffin(Monster):

    def __init__(self):
        super().__init__(
            name="Griffin",
            health=random.randint(75, 105),
            mana=110,
            strength=26,
            intel=21,
            wisdom=18,
            con=18,
            charisma=16,
            dex=18,
            attack=37,
            defense=39,
            magic=41,
            magic_def=37,
            exp=random.randint(440, 650),
        )
        self.equipment = {
            "Weapon": items.LionPaw(),
            "Armor": items.AnimalHide2(),
            "OffHand": items.Claw3(),
            "Ring": items.NoRing(),
            "Pendant": items.NoPendant(),
        }
        self.gold = random.randint(140, 280)
        self.spellbook = {
            "Spells": {"Hurricane": abilities.Hurricane()},
            "Skills": {"Screech": abilities.Screech()},
        }
        self.flying = True
        self.resistance["Physical"] = 0.5
        self.action_stack = [
            {"ability": "Attack", "priority": ActionPriority.NORMAL},
            {"ability": "Screech", "priority": ActionPriority.NORMAL},
            {"ability": "Hurricane", "priority": ActionPriority.NORMAL},
        ]
        self.level.pro_level = 4
        self.picture = "griffin.txt"


class DrowAssassin(Humanoid):
    """
    true sight
    """

    def __init__(self):
        super().__init__(
            name="Drow Assassin",
            health=random.randint(65, 85),
            mana=75,
            strength=22,
            intel=16,
            wisdom=15,
            con=14,
            charisma=22,
            dex=28,
            attack=32,
            defense=30,
            magic=33,
            magic_def=30,
            exp=random.randint(480, 680),
        )
        self.equipment = {
            "Weapon": items.Rondel(),
            "Armor": items.StuddedLeather(),
            "OffHand": items.Rondel(),
            "Ring": items.NoRing(),
            "Pendant": items.NoPendant(),
        }
        self.gold = random.randint(160, 250)
        self.spellbook = {
            "Spells": {},
            "Skills": {
                "Backstab": abilities.Backstab(),
                "Kidney Punch": abilities.KidneyPunch(),
                "Mug": abilities.Mug(),
                "Parry": abilities.Parry(),
                "Piercing Strike": abilities.PiercingStrike(),
                "Smoke Screen": abilities.SmokeScreen(),
                "Shadow Strike": abilities.ShadowStrike(),
            },
        }
        self.action_stack = [
            {"ability": "Attack", "priority": ActionPriority.NORMAL},
            {"ability": "Piercing Strike", "priority": ActionPriority.NORMAL},
            {"ability": "Backstab", "priority": ActionPriority.HIGH},
            {
                "ability": "Shadow Strike",
                "priority": ActionPriority.HIGH,
                "delay": 1,
                "telegraph": "melding with the shadows, preparing a deadly strike",
            },
        ]
        self.level.pro_level = 4
        self.sight = True
        self.picture = "assassin.txt"


class Cyborg(Construct):
    """
    Electric spells heal Cyborg
    """

    def __init__(self):
        super().__init__(
            name="Cyborg",
            health=random.randint(90, 120),
            mana=80,
            strength=28,
            intel=13,
            wisdom=10,
            con=18,
            charisma=10,
            dex=14,
            attack=45,
            defense=43,
            magic=39,
            magic_def=27,
            exp=random.randint(490, 700),
        )
        self.equipment = {
            "Weapon": items.Laser(),
            "Armor": items.MetalPlating(),
            "OffHand": items.ForceField(),
            "Ring": items.NoRing(),
            "Pendant": items.NoPendant(),
        }
        self.gold = random.randint(200, 300)
        self.inventory["Scrap Metal"] = [items.ScrapMetal]
        self.spellbook = {"Spells": {"Shock": abilities.Shock()}, "Skills": {}}
        self.resistance["Electric"] = 1.25
        self.resistance["Water"] = -0.75
        self.action_stack = [
            {"ability": "Attack", "priority": ActionPriority.NORMAL},
            {"ability": "Shock", "priority": ActionPriority.NORMAL},
        ]
        self.level.pro_level = 4
        self.picture = "cyborg.txt"

    def special_effects(self, target: Character) -> str:
        """25% chance to detonate if health below 25%"""
        special_str = ""
        if (
            self.is_alive()
            and self.health.current < int(self.health.current * 0.25)
            and not random.randint(0, 3)
        ):
            special_str += abilities.Detonate().use(self, target=target)
        return special_str


class DarkKnight(Fiend):

    def __init__(self):
        super().__init__(
            name="Dark Knight",
            health=random.randint(85, 110),
            mana=60,
            strength=28,
            intel=15,
            wisdom=12,
            con=21,
            charisma=14,
            dex=17,
            attack=37,
            defense=45,
            magic=30,
            magic_def=29,
            exp=random.randint(500, 750),
        )
        self.equipment = {
            "Weapon": items.Flamberge(),
            "Armor": items.PlateMail(),
            "OffHand": items.KiteShield(),
            "Ring": items.NoRing(),
            "Pendant": items.NoPendant(),
        }
        self.gold = random.randint(300, 420)
        self.inventory["Scrap Metal"] = [items.ScrapMetal]
        self.spellbook = {
            "Spells": {"Enhance Blade": abilities.EnhanceBlade()},
            "Skills": {
                "Shield Slam": abilities.ShieldSlam(),
                "Disarm": abilities.Disarm(),
                "Shield Block": abilities.ShieldBlock(),
            },
        }
        self.action_stack = [
            {"ability": "Attack", "priority": ActionPriority.NORMAL},
            {"ability": "Shield Slam", "priority": ActionPriority.NORMAL},
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
        self.level.pro_level = 4
        self.picture = "darkknight.txt"


class Myrmidon(Elemental):

    def __init__(self):
        super().__init__(
            name="Myrmidon",
            health=random.randint(75, 125),
            mana=75,
            strength=26,
            intel=18,
            wisdom=16,
            con=18,
            charisma=10,
            dex=14,
            attack=35,
            defense=36,
            magic=38,
            magic_def=34,
            exp=random.randint(520, 800),
        )
        self.equipment = {
            "Weapon": items.ElementalBlade(),
            "Armor": items.PlateMail(),
            "OffHand": items.KiteShield(),
            "Ring": items.NoRing(),
            "Pendant": items.NoPendant(),
        }
        self.gold = random.randint(300, 450)
        self.inventory["Elemental Mote"] = [items.ElementalMote]
        self.inventory["Scrap Metal"] = [items.ScrapMetal]
        self.resistance["Poison"] = 1
        self.status_immunity = ["Poison"]
        self.level.pro_level = 4
        self.picture = "myrmidon.txt"


class FlameWisp(Elemental):
    """A volatile fire spirit found only along supernatural fire paths."""

    def __init__(self):
        super().__init__(
            name="Flame Wisp",
            health=random.randint(115, 155),
            mana=120,
            strength=8,
            intel=30,
            wisdom=22,
            con=14,
            charisma=18,
            dex=28,
            attack=38,
            defense=42,
            magic=66,
            magic_def=54,
            exp=random.randint(850, 1150),
        )
        self.equipment = {
            "Weapon": items.NoWeapon(),
            "Armor": items.NoArmor(),
            "OffHand": items.NoOffHand(),
            "Ring": items.NoRing(),
            "Pendant": items.NoPendant(),
        }
        self.gold = random.randint(175, 260)
        self.inventory["Elemental Mote"] = [items.ElementalMote]
        self.spellbook = {
            "Spells": {
                "Fireball": abilities.Fireball(),
                "Scorch": abilities.Scorch(),
            },
            "Skills": {},
        }
        # Resistance values above 1 convert part of incoming damage into healing.
        self.resistance["Fire"] = 1.5
        self.resistance["Ice"] = -0.5
        self.resistance["Water"] = -0.5
        self.resistance["Poison"] = 1.0
        self.status_immunity = ["Poison"]
        self.action_stack = [
            {"ability": "Fireball", "priority": ActionPriority.NORMAL},
            {"ability": "Scorch", "priority": ActionPriority.NORMAL},
            {"ability": "Attack", "priority": ActionPriority.LOW},
        ]
        self.level.pro_level = 5
        self.picture = "flame_wisp.txt"


class FireMyrmidon(Myrmidon):
    """
    Fire elemental; gains fire DOT applied to elemental blade
    """

    def __init__(self):
        super().__init__()
        self.name = "Fire Myrmidon"
        self.spellbook = {
            "Spells": {"Scorch": abilities.Scorch()},
            "Skills": {"Shield Slam": abilities.ShieldSlam()},
        }
        self.resistance["Fire"] = 1.5
        self.resistance["Ice"] = -0.5
        self.action_stack = [
            {"ability": "Attack", "priority": ActionPriority.NORMAL},
            {"ability": "Shield Slam", "priority": ActionPriority.NORMAL},
            {"ability": "Scorch", "priority": ActionPriority.NORMAL},
        ]


class IceMyrmidon(Myrmidon):
    """
    Ice elemental; gains Mortal Strike
    """

    def __init__(self):
        super().__init__()
        self.name = "Ice Myrmidon"
        self.spellbook = {
            "Spells": {"Ice Lance": abilities.IceLance()},
            "Skills": {
                "Shield Slam": abilities.ShieldSlam(),
                "True Strike": abilities.TrueStrike(),
            },
        }
        self.resistance["Fire"] = -0.5
        self.resistance["Ice"] = 1.5
        self.action_stack = [
            {"ability": "Attack", "priority": ActionPriority.NORMAL},
            {"ability": "Shield Slam", "priority": ActionPriority.NORMAL},
            {"ability": "True Strike", "priority": ActionPriority.NORMAL},
            {"ability": "Ice Lance", "priority": ActionPriority.NORMAL},
        ]


class StormMyrmidon(Myrmidon):
    """
    Electric elemental; gains Piercing Strike
    """

    def __init__(self):
        super().__init__()
        self.name = "Storm Myrmidon"
        self.spellbook = {
            "Spells": {"Shock": abilities.Shock()},
            "Skills": {
                "Shield Slam": abilities.ShieldSlam(),
                "Piercing Strike": abilities.PiercingStrike(),
            },
        }
        self.resistance["Electric"] = 1.5
        self.resistance["Water"] = -0.5
        self.action_stack = [
            {"ability": "Attack", "priority": ActionPriority.NORMAL},
            {"ability": "Shield Slam", "priority": ActionPriority.NORMAL},
            {"ability": "Piercing Strike", "priority": ActionPriority.NORMAL},
            {"ability": "Shock", "priority": ActionPriority.NORMAL},
        ]


class WaterMyrmidon(Myrmidon):
    """
    Water elemental; gains Parry
    """

    def __init__(self):
        super().__init__()
        self.name = "Water Myrmidon"
        self.spellbook = {
            "Spells": {"Water Jet": abilities.WaterJet()},
            "Skills": {"Shield Slam": abilities.ShieldSlam(), "Parry": abilities.Parry()},
        }
        self.resistance["Electric"] = -0.5
        self.resistance["Water"] = 1.5
        self.action_stack = [
            {"ability": "Attack", "priority": ActionPriority.NORMAL},
            {"ability": "Shield Slam", "priority": ActionPriority.NORMAL},
            {"ability": "Water Jet", "priority": ActionPriority.NORMAL},
        ]


class EarthMyrmidon(Myrmidon):
    """
    Earth elemental; gains Shield Block
    """

    def __init__(self):
        super().__init__()
        self.name = "Earth Myrmidon"
        self.spellbook = {
            "Spells": {"Tremor": abilities.Tremor()},
            "Skills": {
                "Shield Slam": abilities.ShieldSlam(),
                "Shield Block": abilities.ShieldBlock(),
                "Goad": abilities.Goad(),
            },
        }
        self.resistance["Earth"] = 1.5
        self.resistance["Wind"] = -0.5
        self.action_stack = [
            {"ability": "Attack", "priority": ActionPriority.NORMAL},
            {"ability": "Shield Slam", "priority": ActionPriority.NORMAL},
            {"ability": "Goad", "priority": ActionPriority.NORMAL},
            {"ability": "Tremor", "priority": ActionPriority.NORMAL},
        ]


class WindMyrmidon(Myrmidon):
    """
    Wind elemental; gains Double Strike
    """

    def __init__(self):
        super().__init__()
        self.name = "Wind Myrmidon"
        self.spellbook = {
            "Spells": {"Gust": abilities.Gust()},
            "Skills": {
                "Shield Slam": abilities.ShieldSlam(),
                "Double Strike": abilities.DoubleStrike(),
            },
        }
        self.resistance["Earth"] = -0.5
        self.resistance["Wind"] = 1.5
        self.action_stack = [
            {"ability": "Attack", "priority": ActionPriority.NORMAL},
            {"ability": "Shield Slam", "priority": ActionPriority.NORMAL},
            {"ability": "Double Strike", "priority": ActionPriority.NORMAL},
            {"ability": "Gust", "priority": ActionPriority.NORMAL},
        ]


class DisplacerBeast(Fey):

    def __init__(self):
        super().__init__(
            name="Displacer Beast",
            health=random.randint(80, 115),
            mana=100,
            strength=24,
            intel=11,
            wisdom=14,
            con=24,
            charisma=14,
            dex=26,
            attack=32,
            defense=30,
            magic=29,
            magic_def=31,
            exp=random.randint(500, 775),
        )
        self.equipment = {
            "Weapon": items.Claw3(),
            "Armor": items.AnimalHide2(),
            "OffHand": items.Tentacle(),
            "Ring": items.NoRing(),
            "Pendant": items.NoPendant(),
        }
        self.gold = random.randint(250, 360)
        self.spellbook = {
            "Spells": {},
            "Skills": {
                "Double Strike": abilities.DoubleStrike(),
                "Smoke Screen": abilities.SmokeScreen(),
            },
        }
        self.invisible = True
        self.action_stack = [
            {"ability": "Attack", "priority": ActionPriority.NORMAL},
            {"ability": "Double Strike", "priority": ActionPriority.NORMAL},
            {
                "ability": "Smoke Screen",
                "priority": ActionPriority.LOW,
                "priority_if": {
                    "self_hp_pct_lt": 0.25,
                    "priority": ActionPriority.HIGH,
                    "else": ActionPriority.LOW,
                },
            },
        ]
        self.level.pro_level = 4
        self.picture = "displacerbeast.txt"


class Golem(Construct):
    """
    Guardians of chests on Level 5
    """

    def __init__(self):
        super().__init__(
            name="Golem",
            health=1200,
            mana=100,
            strength=32,
            intel=25,
            wisdom=30,
            con=35,
            charisma=21,
            dex=14,
            attack=50,
            defense=48,
            magic=35,
            magic_def=46,
            exp=8000,
        )
        self.equipment = {
            "Weapon": items.Laser(),
            "Armor": items.StoneArmor2(),
            "OffHand": items.Laser(),
            "Ring": items.NoRing(),
            "Pendant": items.NoPendant(),
        }
        self.gold = 12000
        self.inventory["Power Core"] = [items.PowerCore]
        self.spellbook = {
            "Spells": {"Enfeeble": abilities.Enfeeble()},
            "Skills": {"Crush": abilities.Crush(), "Goad": abilities.Goad()},
        }
        self.resistance["Fire"] = 0.5
        self.resistance["Ice"] = -0.25
        self.resistance["Electric"] = 0.5
        self.resistance["Water"] = -0.25
        self.resistance["Earth"] = 0.5
        self.action_stack = [
            {"ability": "Attack", "priority": ActionPriority.NORMAL},
            {"ability": "Crush", "priority": ActionPriority.LOW},
            {"ability": "Enfeeble", "priority": ActionPriority.NORMAL},
            {"ability": "Goad", "priority": ActionPriority.NORMAL},
        ]
        self.level.pro_level = 5
        self.sight = True
        self.picture = "golem.txt"


class IronGolem(Golem):
    """
    Level 4 Boss
    """

    def __init__(self):
        super().__init__()
        self.name = "Iron Golem"
        self.health = Resource(1250, 1250)
        self.mana = Resource(250, 250)
        self.stats = Stats(35, 25, 35, 40, 21, 16)
        self.combat = Combat(65, 62, 45, 66)
        self.experience = 12000
        self.equipment = {
            "Weapon": items.Laser2(),
            "Armor": items.StoneArmor2(),
            "OffHand": items.ForceField2(),
            "Ring": items.NoRing(),
            "Pendant": items.NoPendant(),
        }
        self.inventory["Aard of Being"] = [items.AardBeing]
        self.inventory["Old Key"] = [items.OldKey]
        self.inventory["Scrap Metal"] = [items.ScrapMetal]
        self.spellbook["Skills"]["Triple Strike"] = abilities.TripleStrike()
        self.resistance["Fire"] = 1.0
        self.resistance["Electric"] = -0.25
        self.resistance["Water"] = -0.5
        self.turtled = False  # signifies if enemy has used turtle or not; limited to once a battle
        self.action_stack = [
            {"ability": "Attack", "priority": ActionPriority.NORMAL},
            {"ability": "Crush", "priority": ActionPriority.LOW},
            {"ability": "Triple Strike", "priority": ActionPriority.NORMAL},
            {"ability": "Enfeeble", "priority": ActionPriority.NORMAL},
            {"ability": "Goad", "priority": ActionPriority.NORMAL},
        ]

    def special_effects(self, target: Character) -> str:
        """If health below 10%, turtle and heal for 25% of max health"""
        special_str = ""
        if self.is_alive() and not self.incapacitated():
            if (
                self.health.current < int(self.health.max * 0.1)
                and not self.turtle
                and not self.turtled
            ):
                self.turtle = True
                self.turtled = True
                special_str += f"{self.name} curls up into a ball for protection.\n"
            if self.health.current > int(self.health.max * 0.5) and self.turtle:
                self.turtle = False
                special_str += f"{self.name} stands up into an offensive stance.\n"
            if self.turtle:
                heal = int(self.health.max * 0.25)
                if heal + self.health.current > self.health.max:
                    heal = self.health.max - self.health.current
                self.health.current += heal
                special_str += f"{self.name} heals for {heal}.\n"
        return special_str


class Jester(Humanoid):
    """
    Level 4 Special Boss - guards fourth of six relics (LUNA) required to beat the final boss
    """

    FORM_DEFS = {
        "crimson": {
            "title": "Crimson Reveler",
            "picture": "jester.png",
            "announcement": "The Jester's bells flare crimson as he embraces pure chaos.",
            "stats": {
                "strength": 28,
                "intel": 30,
                "wisdom": 24,
                "con": 38,
                "charisma": 99,
                "dex": 34,
            },
            "combat": {"attack": 50, "defense": 34, "magic": 42, "magic_def": 32},
            "resistance": _fixed_resistances(Shadow=0.35, Holy=-0.15, Poison=0.25, Physical=0.10),
            "spells": (abilities.Silence, abilities.Hex, abilities.Fireball, abilities.Dispel),
            "skills": (abilities.SlotMachine,),
            "action_stack": [
                {"ability": "Attack", "priority": ActionPriority.NORMAL},
                {"ability": "Slot Machine", "priority": ActionPriority.NORMAL},
                {"ability": "Hex", "priority": ActionPriority.NORMAL},
                {"ability": "Fireball", "priority": ActionPriority.NORMAL},
                {
                    "ability": "Silence",
                    "priority": ActionPriority.NORMAL,
                    "priority_if": {
                        "target_has_mana": True,
                        "priority": ActionPriority.NORMAL,
                        "else": ActionPriority.SKIP,
                    },
                },
                {
                    "ability": "Dispel",
                    "priority": ActionPriority.NORMAL,
                    "priority_if": {
                        "target_has_positive_stat_effects": True,
                        "priority": ActionPriority.NORMAL,
                        "else": ActionPriority.SKIP,
                    },
                },
            ],
        },
        "amber": {
            "title": "Yellow Heckler",
            "picture": "jester1.png",
            "announcement": "A yellow grin spreads across his mask, mocking every spark of magic you raise.",
            "stats": {
                "strength": 20,
                "intel": 38,
                "wisdom": 34,
                "con": 34,
                "charisma": 99,
                "dex": 28,
            },
            "combat": {"attack": 32, "defense": 28, "magic": 54, "magic_def": 46},
            "resistance": _fixed_resistances(
                Fire=0.15, Electric=0.25, Shadow=0.25, Holy=0.20, Physical=-0.10
            ),
            "spells": (abilities.Silence, abilities.WeakenMind),
            "skills": (abilities.GoldToss, abilities.ManaShield, abilities.ManaDrain),
            "action_stack": [
                {
                    "ability": "Silence",
                    "priority": ActionPriority.HIGH,
                    "priority_if": {
                        "target_has_mana": True,
                        "priority": ActionPriority.HIGH,
                        "else": ActionPriority.SKIP,
                    },
                },
                {
                    "ability": "Weaken Mind",
                    "priority": ActionPriority.HIGH,
                    "priority_if": {
                        "target_has_mana": True,
                        "priority": ActionPriority.HIGH,
                        "else": ActionPriority.NORMAL,
                    },
                },
                {
                    "ability": "Mana Shield",
                    "priority": ActionPriority.HIGH,
                    "priority_if": [
                        {
                            "condition": "self_mana_pct_lt",
                            "value": 0.20,
                            "priority": ActionPriority.SKIP,
                        },
                        {
                            "condition": "self_status",
                            "value": "Mana Shield",
                            "priority": ActionPriority.SKIP,
                            "else": ActionPriority.HIGH,
                        },
                    ],
                },
                {
                    "ability": "Mana Drain",
                    "priority": ActionPriority.NORMAL,
                    "priority_if": {
                        "target_has_mana": True,
                        "priority": ActionPriority.NORMAL,
                        "else": ActionPriority.SKIP,
                    },
                },
                {"ability": "Gold Toss", "priority": ActionPriority.NORMAL},
                {"ability": "Attack", "priority": ActionPriority.LOW},
            ],
        },
        "violet": {
            "title": "Purple Hexer",
            "picture": "jester2.png",
            "announcement": "Purple smoke coils from his sleeves as he prepares a killing punchline.",
            "stats": {
                "strength": 22,
                "intel": 40,
                "wisdom": 32,
                "con": 32,
                "charisma": 99,
                "dex": 30,
            },
            "combat": {"attack": 30, "defense": 30, "magic": 56, "magic_def": 40},
            "resistance": _fixed_resistances(Shadow=0.60, Holy=-0.35, Poison=0.35, Physical=-0.05),
            "spells": (abilities.Sleep, abilities.Corruption, abilities.Terrify),
            "skills": (abilities.NightmareFuel,),
            "action_stack": [
                {
                    "ability": "Sleep",
                    "priority": ActionPriority.HIGH,
                    "priority_if": {
                        "target_status": "Sleep",
                        "priority": ActionPriority.SKIP,
                        "else": ActionPriority.HIGH,
                    },
                },
                {
                    "ability": "Nightmare Fuel",
                    "priority": ActionPriority.HIGH,
                    "priority_if": {
                        "target_status": "Sleep",
                        "priority": ActionPriority.HIGH,
                        "else": ActionPriority.SKIP,
                    },
                },
                {"ability": "Corruption", "priority": ActionPriority.HIGH},
                {"ability": "Terrify", "priority": ActionPriority.NORMAL},
                {"ability": "Attack", "priority": ActionPriority.LOW},
            ],
        },
        "verdant": {
            "title": "Green Cutpurse",
            "picture": "jester3.png",
            "announcement": "Green motes scatter from his boots as the Jester slips into a knife dancer's stance.",
            "stats": {
                "strength": 38,
                "intel": 18,
                "wisdom": 20,
                "con": 34,
                "charisma": 99,
                "dex": 42,
            },
            "combat": {"attack": 56, "defense": 42, "magic": 22, "magic_def": 26},
            "resistance": _fixed_resistances(
                Earth=0.20, Wind=0.20, Poison=0.50, Physical=0.30, Holy=-0.10
            ),
            "spells": (),
            "skills": (
                abilities.TripleStrike,
                abilities.PiercingStrike,
                abilities.Mug,
                abilities.SleepingPowder,
            ),
            "action_stack": [
                {"ability": "Triple Strike", "priority": ActionPriority.NORMAL},
                {"ability": "Piercing Strike", "priority": ActionPriority.HIGH},
                {"ability": "Mug", "priority": ActionPriority.NORMAL},
                {
                    "ability": "Sleeping Powder",
                    "priority": ActionPriority.NORMAL,
                    "priority_if": {
                        "target_status": "Sleep",
                        "priority": ActionPriority.SKIP,
                        "else": ActionPriority.NORMAL,
                    },
                },
                {"ability": "Attack", "priority": ActionPriority.NORMAL},
            ],
        },
        "azure": {
            "title": "Blue Mirrorlord",
            "picture": "jester4.png",
            "announcement": "Blue glass ripples over his costume, turning the whole room into a laughing mirror.",
            "stats": {
                "strength": 24,
                "intel": 30,
                "wisdom": 38,
                "con": 40,
                "charisma": 99,
                "dex": 24,
            },
            "combat": {"attack": 28, "defense": 48, "magic": 38, "magic_def": 52},
            "resistance": _fixed_resistances(
                Ice=0.35, Water=0.35, Shadow=0.20, Holy=0.20, Physical=0.25
            ),
            "spells": (abilities.Reflect, abilities.Regen2, abilities.MirrorImage2),
            "skills": (abilities.Parry, abilities.Disarm),
            "action_stack": [
                {
                    "ability": "Reflect",
                    "priority": ActionPriority.HIGH,
                    "priority_if": {
                        "self_status": "Reflect",
                        "priority": ActionPriority.SKIP,
                        "else": ActionPriority.HIGH,
                    },
                },
                {
                    "ability": "Regen",
                    "priority": ActionPriority.HIGH,
                    "priority_if": {
                        "self_hp_pct_lt": 0.60,
                        "priority": ActionPriority.HIGH,
                        "else": ActionPriority.SKIP,
                    },
                },
                {
                    "ability": "Mirror Image",
                    "priority": ActionPriority.HIGH,
                    "priority_if": {
                        "self_status": "Duplicates",
                        "priority": ActionPriority.SKIP,
                        "else": ActionPriority.HIGH,
                    },
                },
                {
                    "ability": "Disarm",
                    "priority": ActionPriority.NORMAL,
                    "priority_if": {
                        "target_has_weapon": True,
                        "priority": ActionPriority.NORMAL,
                        "else": ActionPriority.SKIP,
                    },
                },
                {"ability": "Attack", "priority": ActionPriority.LOW},
            ],
        },
    }

    def __init__(self):
        super().__init__(
            name="Jester",
            health=1100,
            mana=260,
            strength=28,
            intel=30,
            wisdom=24,
            con=38,
            charisma=99,
            dex=34,
            attack=50,
            defense=34,
            magic=42,
            magic_def=32,
            exp=22000,
        )
        self.gold = 25000
        self._gold_toss_pool = 25000
        self.equipment = {
            "Weapon": items.Kukri(),
            "Armor": items.StuddedCuirboulli(),
            "OffHand": items.Kukri(),
            "Ring": items.NoRing(),
            "Pendant": items.NoPendant(),
        }
        self.inventory["Item"] = [items.random_item(6)]
        self.inventory["Old Key"] = [items.OldKey]
        self.inventory["Joker"] = [items.Joker]
        self.status_immunity = ["Death", "Stone", "Disarm"]
        self.level.pro_level = 5
        self.sight = True
        self._jester_form = ""
        self._jester_form_cooldowns: dict[str, int] = {}
        self._jester_form_shift_delay = 1
        self._apply_jester_form("crimson", track_cooldown=False)

    def _apply_jester_form(self, form_key: str, *, track_cooldown: bool = True) -> None:
        form = self.FORM_DEFS[form_key]
        self._jester_form = form_key
        self.stats = Stats(**form["stats"])
        self.combat = Combat(**form["combat"])
        self.resistance = dict(form["resistance"])
        self.spellbook = _build_spellbook(spells=form["spells"], skills=form["skills"])
        self.action_stack = [dict(entry) for entry in form["action_stack"]]
        self.picture = form["picture"]
        if track_cooldown:
            self._refresh_jester_form_cooldowns(form_key)

    def _refresh_jester_form_cooldowns(self, active_form: str) -> None:
        self._jester_form_cooldowns = {
            form: turns - 1
            for form, turns in self._jester_form_cooldowns.items()
            if form != active_form and turns > 1
        }
        self._jester_form_cooldowns[active_form] = 3
        self._jester_form_shift_delay = random.randint(1, 2)

    def _advance_jester_form_timers(self) -> None:
        self._jester_form_cooldowns = {
            form: turns - 1 for form, turns in self._jester_form_cooldowns.items() if turns > 1
        }
        if self._jester_form_shift_delay > 0:
            self._jester_form_shift_delay -= 1

    def _choose_jester_form(self, target: Character) -> str:
        hp_pct = (
            (target.health.current / max(1, target.health.max))
            if getattr(target, "health", None)
            else 1.0
        )
        mana_pct = 0.0
        if getattr(target, "mana", None) and getattr(target.mana, "max", 0):
            mana_pct = target.mana.current / max(1, target.mana.max)

        target_has_buffs = False
        for bucket_name in ("stat_effects", "magic_effects", "class_effects"):
            bucket = getattr(target, bucket_name, {})
            if isinstance(bucket, dict) and any(
                bool(getattr(effect, "active", False)) for effect in bucket.values()
            ):
                target_has_buffs = True
                break

        physical_pressure = 0
        magic_pressure = 0
        if hasattr(target, "check_mod"):
            try:
                physical_pressure = float(target.check_mod("weapon", enemy=self))
            except Exception:
                physical_pressure = 0
            try:
                magic_pressure = float(target.check_mod("magic", enemy=self))
            except Exception:
                magic_pressure = 0

        weights = {
            "crimson": 2,
            "amber": 1,
            "violet": 1,
            "verdant": 1,
            "azure": 1,
        }
        if hp_pct <= 0.35:
            weights["violet"] += 6
        elif hp_pct <= 0.60:
            weights["crimson"] += 2
        if target_has_buffs:
            weights["azure"] += 5
        if mana_pct >= 0.50 and magic_pressure >= physical_pressure * 0.80:
            weights["amber"] += 5
        if physical_pressure > magic_pressure * 0.80:
            weights["verdant"] += 5
        if abs(physical_pressure - magic_pressure) <= max(
            10, max(physical_pressure, magic_pressure) * 0.20
        ):
            weights["crimson"] += 3

        candidates = [
            form
            for form in self.FORM_DEFS
            if form != self._jester_form and self._jester_form_cooldowns.get(form, 0) <= 0
        ]
        if not candidates:
            return self._jester_form

        return random.choices(candidates, weights=[weights[form] for form in candidates], k=1)[0]

    def special_effects(self, target: Character) -> str:
        if not self.is_alive() or self.incapacitated():
            return ""
        if self._jester_form_shift_delay > 0:
            self._advance_jester_form_timers()
            return ""
        self._advance_jester_form_timers()
        if random.random() >= 0.65:
            self._jester_form_shift_delay = 1
            return ""
        next_form = self._choose_jester_form(target)
        if next_form == self._jester_form:
            return ""
        self._apply_jester_form(next_form)
        form = self.FORM_DEFS[next_form]
        return f"The Jester changes form: {form['title']}.\n" f"{form['announcement']}"


def _funhouse_resistances(low=-0.5, high=0.5):
    return {
        "Fire": round(random.uniform(low, high), 2),
        "Ice": round(random.uniform(low, high), 2),
        "Electric": round(random.uniform(low, high), 2),
        "Water": round(random.uniform(low, high), 2),
        "Earth": round(random.uniform(low, high), 2),
        "Wind": round(random.uniform(low, high), 2),
        "Shadow": round(random.uniform(low, high), 2),
        "Holy": round(random.uniform(low, high), 2),
        "Poison": round(random.uniform(low, high), 2),
        "Physical": round(random.uniform(low, high), 2),
    }


def _funhouse_tricks():
    spellbook = {"Spells": {}, "Skills": {}}
    trick_pool = [
        ("Gold Toss", abilities.GoldToss(), "Skills"),
        ("Smoke Screen", abilities.SmokeScreen(), "Skills"),
        ("Double Strike", abilities.DoubleStrike(), "Skills"),
        ("Silence", abilities.Silence(), "Spells"),
        ("Mirror Image", abilities.MirrorImage2(), "Spells"),
    ]
    random.shuffle(trick_pool)
    for name, ability, bucket in trick_pool[: random.randint(2, 3)]:
        spellbook[bucket][name] = ability
    return spellbook


class FunhouseMinion(Humanoid):
    def __init__(self, name, health_range, mana_range, stat_range, combat_range, exp_range):
        super().__init__(
            name=name,
            health=random.randint(*health_range),
            mana=random.randint(*mana_range),
            strength=random.randint(*stat_range),
            intel=random.randint(*stat_range),
            wisdom=random.randint(*stat_range),
            con=random.randint(*stat_range),
            charisma=random.randint(*stat_range),
            dex=random.randint(*stat_range),
            attack=random.randint(*combat_range),
            defense=random.randint(*combat_range),
            magic=random.randint(*combat_range),
            magic_def=random.randint(*combat_range),
            exp=random.randint(*exp_range),
        )
        self.gold = random.randint(200, 900)
        self.equipment = {
            "Weapon": items.Kris(),
            "Armor": items.Cuirboulli(),
            "OffHand": items.NoOffHand(),
            "Ring": items.NoRing(),
            "Pendant": items.NoPendant(),
        }
        self.spellbook = _funhouse_tricks()
        self.resistance = _funhouse_resistances()
        self.action_stack = [{"ability": "Attack", "priority": ActionPriority.NORMAL}]
        for ability_name in list(self.spellbook["Skills"].keys()) + list(
            self.spellbook["Spells"].keys()
        ):
            self.action_stack.append({"ability": ability_name, "priority": ActionPriority.NORMAL})
        self.level.pro_level = 4


class Puppet(FunhouseMinion):
    def __init__(self):
        super().__init__(
            name="Puppet",
            health_range=(120, 220),
            mana_range=(40, 120),
            stat_range=(8, 22),
            combat_range=(18, 38),
            exp_range=(1200, 2200),
        )


class Harlequin(FunhouseMinion):
    def __init__(self):
        super().__init__(
            name="Harlequin",
            health_range=(150, 260),
            mana_range=(60, 140),
            stat_range=(10, 26),
            combat_range=(22, 42),
            exp_range=(1600, 2600),
        )
        self.stats.dex += random.randint(4, 8)
        self.combat.attack += random.randint(4, 8)


class Trickster(FunhouseMinion):
    def __init__(self):
        super().__init__(
            name="Trickster",
            health_range=(140, 240),
            mana_range=(80, 180),
            stat_range=(9, 24),
            combat_range=(20, 40),
            exp_range=(1500, 2600),
        )
        self.stats.intel += random.randint(4, 10)
        self.stats.wisdom += random.randint(4, 10)
        self.combat.magic += random.randint(4, 8)
        self.combat.magic_def += random.randint(4, 8)


class Copycat(FunhouseMinion):
    """
    Funhouse minion that mirrors a small subset of the player's combat abilities.

    Implementation notes:
    - Copies once per instance (first options() call) to avoid per-turn churn.
    - Clones abilities via AbilitySerializer to avoid shared mutable state
      (e.g., charging abilities).
    """

    MAX_COPIED_SPELLS = 2
    MAX_COPIED_SKILLS = 2
    _BLACKLIST_ACTION_IDS = {
        # World-state / UI-callback / special-context abilities
        "teleport",
        "sanctuary",
        "choose_fate",
        "slot_machine",
        "inspect",
    }

    def __init__(self):
        super().__init__(
            name="Copycat",
            health_range=(160, 280),
            mana_range=(120, 240),
            stat_range=(10, 28),
            combat_range=(22, 44),
            exp_range=(1800, 3200),
        )
        # Start with only the base Funhouse trick pool; we will mirror additional
        # abilities from the player at combat start.
        self._mirrored: bool = False

    def _clone_from_target(self, target: Character) -> None:
        from src.core.save_system import AbilitySerializer

        if not isinstance(getattr(target, "spellbook", None), dict):
            self._mirrored = True
            return

        def _pool(bucket: str) -> list[tuple[str, object, str]]:
            out: list[tuple[str, object, str]] = []
            src = target.spellbook.get(bucket, {})
            if not isinstance(src, dict):
                return out
            for key, ab in src.items():
                if ab is None:
                    continue
                if bool(getattr(ab, "passive", False)):
                    continue
                try:
                    action_id = AbilitySerializer.serialize(ab)
                except Exception:
                    action_id = ab.__class__.__name__
                if action_id in self._BLACKLIST_ACTION_IDS:
                    continue
                cost = int(getattr(ab, "cost", 0) or 0)
                if cost > int(getattr(self.mana, "max", 0) or 0):
                    continue
                out.append((str(key), ab, action_id))
            return out

        spells_pool = _pool("Spells")
        skills_pool = _pool("Skills")
        random.shuffle(spells_pool)
        random.shuffle(skills_pool)

        spells_take = spells_pool[: self.MAX_COPIED_SPELLS]
        skills_take = skills_pool[: self.MAX_COPIED_SKILLS]

        # Clone and install
        copied_any = False
        for bucket_name, selected in (("Spells", spells_take), ("Skills", skills_take)):
            for orig_key, orig_ab, _cls_name in selected:
                try:
                    clone = AbilitySerializer.deserialize(AbilitySerializer.serialize(orig_ab))
                except Exception:
                    continue
                if clone is None:
                    continue

                # Prefer human-readable name as key, but avoid collisions.
                key = str(getattr(clone, "name", orig_key) or orig_key)
                bucket = self.spellbook.setdefault(bucket_name, {})
                if key in bucket:
                    key = str(getattr(clone, "_class_name", clone.__class__.__name__))
                bucket[key] = clone
                copied_any = True

        # Rebuild action_stack to include copied abilities (priority-weighted selection).
        if copied_any:
            self.action_stack = [{"ability": "Attack", "priority": ActionPriority.NORMAL}]
            for ability_name in list(self.spellbook.get("Skills", {}).keys()):
                self.action_stack.append(
                    {"ability": ability_name, "priority": ActionPriority.NORMAL}
                )
            for ability_name in list(self.spellbook.get("Spells", {}).keys()):
                self.action_stack.append(
                    {"ability": ability_name, "priority": ActionPriority.NORMAL}
                )

        self._mirrored = True

    def options(
        self, target: Character, action_list: list[str], tile: object
    ) -> tuple[str, str | None]:
        if not self._mirrored:
            try:
                self._clone_from_target(target)
            except Exception:
                self._mirrored = True
        return super().options(target, action_list, tile)


class Incubus(Fiend):
    """
    Father of Merzhin; must locate and defeat to gain access to Realm of Cambion
    """

    def __init__(self):
        super().__init__(
            name="Incubus",
            health=1250,
            mana=320,
            strength=26,
            intel=38,
            wisdom=34,
            con=38,
            charisma=46,
            dex=40,
            attack=74,
            defense=80,
            magic=84,
            magic_def=86,
            exp=22000,
        )
        self.equipment = {
            "Weapon": items.Rondel(),
            "Armor": items.StuddedLeather(),
            "OffHand": items.NoOffHand(),
            "Ring": items.NoRing(),
            "Pendant": items.NoPendant(),
        }
        self.gold = 15000
        self.inventory["Item"] = [items.random_item(6)]
        self.spellbook = {
            "Spells": {"Sleep": abilities.Sleep(), "Terrify": abilities.Terrify()},
            "Skills": {
                "Double Strike": abilities.DoubleStrike(),
                "Mana Drain": abilities.ManaDrain(),
            },
        }
        self.resistance["Shadow"] = 0.5
        self.resistance["Holy"] = -0.25
        self.status_immunity = ["Death", "Stone", "Disarm"]
        self.action_stack = [
            {"ability": "Attack", "priority": ActionPriority.NORMAL},
            {"ability": "Double Strike", "priority": ActionPriority.NORMAL},
            {
                "ability": "Sleep",
                "priority": ActionPriority.LOW,
                "priority_if": {
                    "target_incapacitated": True,
                    "priority": ActionPriority.SKIP,
                    "else": ActionPriority.LOW,
                },
            },
            {
                "ability": "Mana Drain",
                "priority": ActionPriority.LOW,
                "priority_if": {
                    "target_has_mana": True,
                    "priority": ActionPriority.LOW,
                    "else": ActionPriority.SKIP,
                },
            },
            {
                "ability": "Terrify",
                "priority": ActionPriority.LOW,
                "priority_if": {
                    "target_incapacitated": True,
                    "priority": ActionPriority.SKIP,
                    "else": ActionPriority.LOW,
                },
            },
        ]
        self.level.pro_level = 5
        self.sight = True
        self.picture = "incubus.txt"
