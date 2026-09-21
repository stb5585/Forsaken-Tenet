"""Enemy implementations for the late dungeon and endgame."""

from __future__ import annotations

from src.core.randomness import gameplay_random as random

from .. import abilities, items
from ..character import Character, Combat, Stats, StatusEffect
from ..combat.action_queue import ActionPriority
from .base import (
    Aberration,
    Construct,
    Dragon,
    Elemental,
    Fiend,
    Humanoid,
    Monster,
    Slime,
    Undead,
)


# Level 5
class ShadowSerpent(Elemental):

    def __init__(self):
        super().__init__(
            name="Shadow Serpent",
            health=random.randint(130, 180),
            mana=100,
            strength=28,
            intel=18,
            wisdom=15,
            con=22,
            charisma=16,
            dex=23,
            attack=46,
            defense=41,
            magic=46,
            magic_def=40,
            exp=random.randint(780, 1090),
        )
        self.equipment = {
            "Weapon": items.SnakeFang2(),
            "Armor": items.SnakeScales2(),
            "OffHand": items.SnakeFang2(),
            "Ring": items.NoRing(),
            "Pendant": items.NoPendant(),
        }
        self.gold = random.randint(280, 485)
        self.inventory["Megalixir"] = [items.Megalixir]
        self.inventory["Shadow Venom"] = [items.ShadowVenom]
        self.spellbook = {
            "Spells": {"Corruption": abilities.Corruption()},
            "Skills": {"Double Strike": abilities.DoubleStrike()},
        }
        self.resistance["Shadow"] = 0.9
        self.resistance["Holy"] = -0.75
        self.resistance["Poison"] = 0.25
        self.invisible = True
        self.action_stack = [
            {"ability": "Attack", "priority": ActionPriority.NORMAL},
            {"ability": "Double Strike", "priority": ActionPriority.NORMAL},
            {"ability": "Corruption", "priority": ActionPriority.NORMAL},
        ]
        self.level.pro_level = 5
        self.picture = "snake.txt"


class Aboleth(Slime):

    def __init__(self):
        super().__init__(
            name="Aboleth",
            health=random.randint(210, 500),
            mana=120,
            strength=25,
            intel=50,
            wisdom=50,
            con=25,
            charisma=12,
            dex=10,
            attack=32,
            defense=40,
            magic=65,
            magic_def=300,
            exp=random.randint(650, 1230),
        )
        self.equipment = {
            "Weapon": items.NoWeapon(),
            "Armor": items.NoArmor(),
            "OffHand": items.NoOffHand(),
            "Ring": items.NoRing(),
            "Pendant": items.NoPendant(),
        }
        self.gold = random.randint(130, 750)
        self.spellbook = {
            "Spells": {
                "Disease Breath": abilities.DiseaseBreath(),
                "Enfeeble": abilities.Enfeeble(),
                "Boost": abilities.Boost(),
            },
            "Skills": {"Acid Spit": abilities.AcidSpit()},
        }
        self.resistance["Poison"] = 1.5
        self.status_immunity = ["Poison"]
        self.action_stack = [
            {"ability": "Attack", "priority": ActionPriority.LOW},
            {"ability": "Acid Spit", "priority": ActionPriority.NORMAL},
            {"ability": "Disease Breath", "priority": ActionPriority.NORMAL},
            {"ability": "Enfeeble", "priority": ActionPriority.NORMAL},
            {
                "ability": "Boost",
                "priority": ActionPriority.NORMAL,
                "priority_if": {
                    "self_stat": "Magic",
                    "priority": ActionPriority.SKIP,
                    "else": ActionPriority.NORMAL,
                },
            },
        ]
        self.level.pro_level = 5


class Beholder(Aberration):

    def __init__(self):
        super().__init__(
            name="Beholder",
            health=random.randint(150, 300),
            mana=100,
            strength=25,
            intel=40,
            wisdom=35,
            con=28,
            charisma=20,
            dex=20,
            attack=47,
            defense=45,
            magic=60,
            magic_def=55,
            exp=random.randint(800, 1200),
        )
        self.equipment = {
            "Weapon": items.Gaze(),
            "Armor": items.NoArmor(),
            "OffHand": items.NoOffHand(),
            "Ring": items.NoRing(),
            "Pendant": items.NoPendant(),
        }
        self.gold = random.randint(300, 500)
        self.spellbook = {
            "Spells": {
                "Magic Missile": abilities.MagicMissile2(),
                "Terrify": abilities.Terrify(),
                "Dispel": abilities.Dispel(),
                "Disintegrate": abilities.Disintegrate(),
            },
            "Skills": {"Mana Drain": abilities.ManaDrain()},
        }
        self.flying = True
        self.status_immunity = ["Death"]
        self.action_stack = [
            {"ability": "Attack", "priority": ActionPriority.NORMAL},
            {"ability": "Magic Missile", "priority": ActionPriority.NORMAL},
            {"ability": "Disintegrate", "priority": ActionPriority.NORMAL},
            {"ability": "Terrify", "priority": ActionPriority.NORMAL},
            {
                "ability": "Mana Drain",
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
                    "target_has_positive_effects": True,
                    "priority": ActionPriority.NORMAL,
                    "else": ActionPriority.SKIP,
                },
            },
        ]
        self.level.pro_level = 5
        self.picture = "beholder.txt"


class Behemoth(Aberration):

    def __init__(self):
        super().__init__(
            name="Behemoth",
            health=random.randint(200, 300),
            mana=100,
            strength=38,
            intel=25,
            wisdom=20,
            con=30,
            charisma=18,
            dex=25,
            attack=58,
            defense=51,
            magic=57,
            magic_def=53,
            exp=random.randint(920, 1250),
        )
        self.equipment = {
            "Weapon": items.LionPaw(),
            "Armor": items.AnimalHide2(),
            "OffHand": items.LionPaw(),
            "Ring": items.NoRing(),
            "Pendant": items.NoPendant(),
        }
        self.gold = random.randint(400, 550)
        self.spellbook = {
            "Spells": {
                "Holy": abilities.Holy3(),
                "Regen": abilities.Regen3(),
                "Berserk": abilities.Berserk(),
            },
            "Skills": {
                "True Strike": abilities.TrueStrike(),
                "Counterspell": abilities.Counterspell(),
            },
        }
        self.action_stack = [
            {"ability": "Attack", "priority": ActionPriority.NORMAL},
            {"ability": "True Strike", "priority": ActionPriority.NORMAL},
            {"ability": "Holy", "priority": ActionPriority.NORMAL},
            {"ability": "Berserk", "priority": ActionPriority.NORMAL},
        ]
        self.resistance["Fire"] = 1.0
        self.resistance["Electric"] = 0.75
        self.resistance["Holy"] = 0.75
        self.resistance["Poison"] = 0.75
        self.resistance["Physical"] = 0.5
        self.status_immunity = ["Death", "Stone"]
        self.level.pro_level = 5
        self.picture = "behemoth.txt"

    def special_effects(self, target: Character) -> str:
        """Has a 60% chance to cast Meteor on death"""
        special_str = ""
        if not self.is_alive():
            if random.randint(0, 100) < 60:  # 60% chance to cast
                special_str += f"{self.name} unleashes a powerful attack as it dies.\n"
                special_str += abilities.Meteor().cast(self, target=target, special=True)
        return special_str


class Lich(Undead):

    def __init__(self):
        super().__init__(
            name="Lich",
            health=random.randint(210, 300),
            mana=120,
            strength=25,
            intel=35,
            wisdom=40,
            con=20,
            charisma=36,
            dex=22,
            attack=44,
            defense=42,
            magic=63,
            magic_def=70,
            exp=random.randint(880, 1220),
        )
        self.equipment = {
            "Weapon": items.LichHand(),
            "Armor": items.WizardRobe(),
            "OffHand": items.Necronomicon(),
            "Ring": items.NoRing(),
            "Pendant": items.NoPendant(),
        }
        self.gold = random.randint(400, 530)
        self.inventory["Phylactery"] = [items.Phylactery]
        self.spellbook = {
            "Spells": {
                "Blizzard": abilities.IceBlizzard(),
                "Desoul": abilities.Desoul(),
                "Terrify": abilities.Terrify(),
                "Ice Block": abilities.IceBlock(),
                "Boost": abilities.Boost(),
            },
            "Skills": {"Health/Mana Drain": abilities.HealthManaDrain()},
        }
        self.resistance["Ice"] = 0.9
        # Prevent Ice Block loops that can stall the fight indefinitely.
        self.single_use_abilities = {"Ice Block"}
        self.action_stack = [
            {"ability": "Attack", "priority": ActionPriority.NORMAL},
            {"ability": "Blizzard", "priority": ActionPriority.NORMAL},
            {"ability": "Desoul", "priority": ActionPriority.NORMAL},
            {
                "ability": "Health/Mana Drain",
                "priority": ActionPriority.NORMAL,
                "priority_if": {
                    "target_has_mana": True,
                    "priority": ActionPriority.NORMAL,
                    "else": ActionPriority.SKIP,
                },
            },
            {"ability": "Terrify", "priority": ActionPriority.NORMAL},
            {
                "ability": "Ice Block",
                "priority": ActionPriority.LOW,
                "priority_if": [
                    {"condition": "self_hp_pct_lt", "value": 0.1, "priority": ActionPriority.HIGH},
                    {
                        "condition": "self_mana_pct_lt",
                        "value": 0.1,
                        "priority": ActionPriority.HIGH,
                    },
                    {
                        "condition": "self_hp_pct_lt",
                        "value": 0.5,
                        "priority": ActionPriority.NORMAL,
                    },
                    {
                        "condition": "self_mana_pct_lt",
                        "value": 0.5,
                        "priority": ActionPriority.NORMAL,
                    },
                ],
            },
            {
                "ability": "Boost",
                "priority": ActionPriority.NORMAL,
                "priority_if": {
                    "self_stat": "Magic",
                    "priority": ActionPriority.SKIP,
                    "else": ActionPriority.NORMAL,
                },
            },
        ]
        self.level.pro_level = 5
        self.picture = "lich.txt"


class Basilisk(Monster):

    def __init__(self):
        super().__init__(
            name="Basilisk",
            health=random.randint(220, 325),
            mana=120,
            strength=29,
            intel=26,
            wisdom=30,
            con=27,
            charisma=17,
            dex=20,
            attack=49,
            defense=46,
            magic=51,
            magic_def=66,
            exp=random.randint(930, 1200),
        )
        self.equipment = {
            "Weapon": items.SnakeFang2(),
            "Armor": items.SnakeScales2(),
            "OffHand": items.SnakeFang2(),
            "Ring": items.NoRing(),
            "Pendant": items.NoPendant(),
        }
        self.gold = random.randint(380, 520)
        self.inventory["Lizard Venom"] = [items.LizardVenom]
        self.spellbook = {
            "Spells": {"Petrify": abilities.Petrify(), "Poison Breath": abilities.PoisonBreath()},
            "Skills": {"Slam": abilities.Slam(), "Bad Breath": abilities.BadBreath()},
        }
        self.resistance["Poison"] = 0.75
        self.status_immunity = ["Death", "Poison", "Stone"]
        self.action_stack = [
            {"ability": "Attack", "priority": ActionPriority.NORMAL},
            {"ability": "Slam", "priority": ActionPriority.NORMAL},
            {"ability": "Bad Breath", "priority": ActionPriority.LOW},
            {"ability": "Petrify", "priority": ActionPriority.NORMAL},
            {"ability": "Poison Breath", "priority": ActionPriority.NORMAL},
        ]
        self.level.pro_level = 5
        self.picture = "snake.txt"


class MindFlayer(Aberration):
    """
    true sight
    """

    def __init__(self):
        super().__init__(
            name="Mind Flayer",
            health=random.randint(190, 285),
            mana=150,
            strength=28,
            intel=40,
            wisdom=35,
            con=25,
            charisma=22,
            dex=18,
            attack=42,
            defense=38,
            magic=68,
            magic_def=81,
            exp=random.randint(890, 1150),
        )
        self.equipment = {
            "Weapon": items.MithrilshodStaff(),
            "Armor": items.WizardRobe(),
            "OffHand": items.NoOffHand(),
            "Ring": items.NoRing(),
            "Pendant": items.NoPendant(),
        }
        self.gold = random.randint(450, 600)
        self.spellbook = {
            "Spells": {
                "Doom": abilities.Doom(),
                "Terrify": abilities.Terrify(),
                "Corruption": abilities.Corruption(),
            },
            "Skills": {"Mana Drain": abilities.ManaDrain()},
        }
        self.resistance["Shadow"] = 0.5
        self.resistance["Holy"] = -0.25
        self.status_immunity = ["Death"]
        self.action_stack = [
            {"ability": "Attack", "priority": ActionPriority.NORMAL},
            {"ability": "Doom", "priority": ActionPriority.NORMAL},
            {"ability": "Terrify", "priority": ActionPriority.NORMAL},
            {"ability": "Corruption", "priority": ActionPriority.NORMAL},
            {
                "ability": "Mana Drain",
                "priority": ActionPriority.NORMAL,
                "priority_if": {
                    "target_has_mana": True,
                    "priority": ActionPriority.NORMAL,
                    "else": ActionPriority.SKIP,
                },
            },
        ]
        self.level.pro_level = 5
        self.sight = True
        self.picture = "mindflayer.txt"


class Sandworm(Monster):

    def __init__(self):
        super().__init__(
            name="Sandworm",
            health=random.randint(230, 300),
            mana=190,
            strength=34,
            intel=21,
            wisdom=22,
            con=30,
            charisma=20,
            dex=18,
            attack=56,
            defense=49,
            magic=49,
            magic_def=54,
            exp=random.randint(910, 1200),
        )
        self.equipment = {
            "Weapon": items.EarthMaw(),
            "Armor": items.NoArmor(),
            "OffHand": items.NoOffHand(),
            "Ring": items.NoRing(),
            "Pendant": items.NoPendant(),
        }
        self.gold = random.randint(380, 490)
        self.inventory["Scrap Metal"] = [items.ScrapMetal]
        self.spellbook = {
            "Spells": {"Earthquake": abilities.Earthquake(), "Sandstorm": abilities.Sandstorm()},
            "Skills": {
                "Consume Item": abilities.ConsumeItem(),
                "Tunnel": abilities.Tunnel(),
                "Surface": abilities.Surface(),
            },
        }
        self.resistance["Electric"] = 0.5
        self.resistance["Water"] = -0.25
        self.resistance["Earth"] = 1
        self.resistance["Poison"] = 1
        self.resistance["Physical"] = 0.5
        self.status_immunity = ["Stone"]
        self.action_stack = [
            {"ability": "Attack", "priority": ActionPriority.NORMAL},
            {"ability": "Earthquake", "priority": ActionPriority.NORMAL},
            {"ability": "Sandstorm", "priority": ActionPriority.NORMAL},
            {"ability": "Consume Item", "priority": ActionPriority.HIGH},
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
        self.level.pro_level = 5
        self.picture = "naga.txt"


class Warforged(Construct):

    def __init__(self):
        super().__init__(
            name="Warforged",
            health=random.randint(230, 300),
            mana=120,
            strength=40,
            intel=20,
            wisdom=16,
            con=33,
            charisma=12,
            dex=10,
            attack=66,
            defense=62,
            magic=45,
            magic_def=39,
            exp=random.randint(880, 1180),
        )
        self.equipment = {
            "Weapon": items.Cannon(),
            "Armor": items.StoneArmor2(),
            "OffHand": items.ForceField3(),
            "Ring": items.NoRing(),
            "Pendant": items.NoPendant(),
        }
        self.gold = random.randint(380, 490)
        self.inventory["Scrap Metal"] = [items.ScrapMetal]
        self.spellbook = {
            "Spells": {"Silence": abilities.Silence()},
            "Skills": {"Crush": abilities.Crush()},
        }
        self.action_stack = [
            {"ability": "Attack", "priority": ActionPriority.NORMAL},
            {"ability": "Crush", "priority": ActionPriority.LOW},
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
        self.level.pro_level = 5
        self.picture = "golem.txt"

    def special_effects(self, target: Character) -> str:
        """if health is below 10%, turtle and heal for 25% of max health"""
        special_str = ""
        if self.is_alive() and not self.incapacitated():
            if self.health.current < int(self.health.max * 0.1) and not self.turtle:
                self.turtle = True
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


class Wyrm(Dragon):

    def __init__(self):
        super().__init__(
            name="Wyrm",
            health=random.randint(320, 400),
            mana=150,
            strength=38,
            intel=28,
            wisdom=30,
            con=28,
            charisma=22,
            dex=23,
            attack=62,
            defense=53,
            magic=55,
            magic_def=59,
            exp=random.randint(920, 1180),
        )
        self.equipment = {
            "Weapon": items.DragonTail2(),
            "Armor": items.DragonScale(),
            "OffHand": items.NoOffHand(),
            "Ring": items.NoRing(),
            "Pendant": items.NoPendant(),
        }
        self.gold = random.randint(650, 830)
        self.spellbook = {
            "Spells": {"Volcano": abilities.Volcano()},
            "Skills": {
                "Triple Strike": abilities.TripleStrike(),
                "Dragon Breath (Fire)": abilities.DragonBreathFire(),
            },
        }
        self.action_stack = [
            {"ability": "Attack", "priority": ActionPriority.NORMAL},
            {"ability": "Triple Strike", "priority": ActionPriority.NORMAL},
            {"ability": "Volcano", "priority": ActionPriority.NORMAL},
            {
                "ability": "Dragon Breath (Fire)",
                "priority": ActionPriority.LOW,
                "delay": 2,
                "telegraph": "drawing in massive amounts of air, magma swirling in its throat",
            },
        ]
        self.level.pro_level = 5
        self.picture = "wyrm.txt"


class Hydra(Monster):

    def __init__(self):
        super().__init__(
            name="Hydra",
            health=random.randint(260, 375),
            mana=150,
            strength=37,
            intel=30,
            wisdom=26,
            con=28,
            charisma=24,
            dex=22,
            attack=60,
            defense=51,
            magic=52,
            magic_def=53,
            exp=random.randint(900, 1150),
        )
        self.equipment = {
            "Weapon": items.Bite2(),
            "Armor": items.DragonScale(),
            "OffHand": items.DragonTail(),
            "Ring": items.NoRing(),
            "Pendant": items.NoPendant(),
        }
        self.gold = random.randint(400, 550)
        self.spellbook = {
            "Spells": {"Tsunami": abilities.Tsunami()},
            "Skills": {
                "Double Strike": abilities.DoubleStrike(),
                "Dragon Breath (Water)": abilities.DragonBreathWater(),
            },
        }
        self.resistance["Electric"] = -1
        self.resistance["Water"] = 1.5
        self.resistance["Poison"] = 0.75
        self.resistance["Physical"] = 0.25
        self.status_immunity = ["Death", "Stone"]
        self.action_stack = [
            {"ability": "Attack", "priority": ActionPriority.NORMAL},
            {"ability": "Double Strike", "priority": ActionPriority.NORMAL},
            {"ability": "Tsunami", "priority": ActionPriority.NORMAL},
            {
                "ability": "Dragon Breath (Water)",
                "priority": ActionPriority.LOW,
                "delay": 2,
                "telegraph": "all heads rearing back, gathering torrential water in their maws",
            },
        ]
        self.level.pro_level = 5
        self.picture = "hydra.txt"


class Wyvern(Dragon):

    def __init__(self):
        super().__init__(
            name="Wyvern",
            health=random.randint(320, 410),
            mana=150,
            strength=35,
            intel=33,
            wisdom=24,
            con=30,
            charisma=25,
            dex=40,
            attack=66,
            defense=50,
            magic=50,
            magic_def=43,
            exp=random.randint(950, 1200),
        )
        self.equipment = {
            "Weapon": items.DragonClaw2(),
            "Armor": items.DragonScale(),
            "OffHand": items.DragonClaw2(),
            "Ring": items.NoRing(),
            "Pendant": items.NoPendant(),
        }
        self.gold = random.randint(420, 570)
        self.spellbook = {
            "Spells": {"Tornado": abilities.Tornado()},
            "Skills": {
                "Piercing Strike": abilities.PiercingStrike(),
                "Dragon Breath (Wind)": abilities.DragonBreathWind(),
            },
        }
        self.action_stack = [
            {"ability": "Attack", "priority": ActionPriority.NORMAL},
            {"ability": "Tornado", "priority": ActionPriority.NORMAL},
            {
                "ability": "Dragon Breath (Wind)",
                "priority": ActionPriority.LOW,
                "delay": 2,
                "telegraph": "inhaling deeply, gathering a powerful gale within",
            },
        ]
        self.flying = True
        self.level.pro_level = 5
        self.picture = "wyvern.txt"

    def special_attack(self, target: Character) -> str:
        return abilities.BreatheFire().use(self, target, typ="Wind")


class Archvile(Fiend):

    def __init__(self):
        super().__init__(
            name="Archvile",
            health=random.randint(360, 460),
            mana=200,
            strength=32,
            intel=31,
            wisdom=35,
            con=38,
            charisma=28,
            dex=32,
            attack=72,
            defense=53,
            magic=52,
            magic_def=58,
            exp=random.randint(1010, 1280),
        )
        self.equipment = {
            "Weapon": items.BattleGauntlet(),
            "Armor": items.DemonArmor2(),
            "OffHand": items.BattleGauntlet(),
            "Ring": items.NoRing(),
            "Pendant": items.NoPendant(),
        }
        self.gold = random.randint(375, 555)
        self.spellbook = {
            "Spells": {
                "Sleep": abilities.Sleep(),
                "Corruption": abilities.Corruption(),
                "Terrify": abilities.Terrify(),
                "Regen": abilities.Regen2(),
                "Firestorm": abilities.Firestorm(),
            },
            "Skills": {"Parry": abilities.Parry()},
        }
        self.resistance["Fire"] = 1.0
        self.resistance["Ice"] = 0.5
        self.resistance["Electric"] = 0.5
        self.resistance["Poison"] = 1.0
        self.status_immunity.append("Poison")
        self.action_stack = [
            {"ability": "Attack", "priority": ActionPriority.NORMAL},
            {"ability": "Firestorm", "priority": ActionPriority.NORMAL},
            {"ability": "Corruption", "priority": ActionPriority.NORMAL},
            {"ability": "Terrify", "priority": ActionPriority.NORMAL},
            {"ability": "Sleep", "priority": ActionPriority.NORMAL},
            {
                "ability": "Regen",
                "priority": ActionPriority.NORMAL,
                "priority_if": [
                    {"condition": "self_hp_pct_lt", "value": 50, "priority": ActionPriority.HIGH},
                    {"condition": "self_status", "value": "Regen", "priority": ActionPriority.LOW},
                ],
            },
        ]
        self.level.pro_level = 5
        self.picture = "archvile.txt"


class Succubus(Fiend):
    """Fiend contract patron focused on charm, curses, and draining sustain."""

    def __init__(self):
        super().__init__(
            name="Succubus",
            health=random.randint(330, 430),
            mana=260,
            strength=22,
            intel=34,
            wisdom=32,
            con=30,
            charisma=48,
            dex=38,
            attack=58,
            defense=50,
            magic=76,
            magic_def=72,
            exp=random.randint(1080, 1360),
        )
        self.equipment = {
            "Weapon": items.DemonClaw(),
            "Armor": items.NoArmor(),
            "OffHand": items.DemonClaw(),
            "Ring": items.NoRing(),
            "Pendant": items.NoPendant(),
        }
        self.gold = random.randint(450, 700)
        self.spellbook = {
            "Spells": {
                "Sleep": abilities.Sleep(),
                "Terrify": abilities.Terrify(),
                "Corruption": abilities.Corruption(),
            },
            "Skills": {
                "Health Drain": abilities.HealthDrain(),
                "Mana Drain": abilities.ManaDrain(),
            },
        }
        self.resistance["Shadow"] = 0.6
        self.resistance["Holy"] = -0.5
        self.status_immunity = ["Death", "Sleep"]
        self.action_stack = [
            {"ability": "Attack", "priority": ActionPriority.LOW},
            {
                "ability": "Sleep",
                "priority": ActionPriority.NORMAL,
                "priority_if": {
                    "target_incapacitated": True,
                    "priority": ActionPriority.SKIP,
                    "else": ActionPriority.NORMAL,
                },
            },
            {"ability": "Terrify", "priority": ActionPriority.NORMAL},
            {"ability": "Corruption", "priority": ActionPriority.NORMAL},
            {"ability": "Health Drain", "priority": ActionPriority.NORMAL},
            {
                "ability": "Mana Drain",
                "priority": ActionPriority.LOW,
                "priority_if": {
                    "target_has_mana": True,
                    "priority": ActionPriority.LOW,
                    "else": ActionPriority.SKIP,
                },
            },
        ]
        self.level.pro_level = 5
        self.picture = "incubus.txt"


class Maelephant(Fiend):
    """Massive fiend contract patron focused on protection and crushing force."""

    def __init__(self):
        super().__init__(
            name="Maelephant",
            health=random.randint(620, 760),
            mana=220,
            strength=48,
            intel=20,
            wisdom=36,
            con=58,
            charisma=28,
            dex=18,
            attack=96,
            defense=96,
            magic=58,
            magic_def=82,
            exp=random.randint(1450, 1780),
        )
        self.equipment = {
            "Weapon": items.BattleGauntlet(),
            "Armor": items.DemonArmor2(),
            "OffHand": items.NoOffHand(),
            "Ring": items.NoRing(),
            "Pendant": items.NoPendant(),
        }
        self.gold = random.randint(700, 1100)
        self.spellbook = {
            "Spells": {"Shell": abilities.Shell(), "Terrify": abilities.Terrify()},
            "Skills": {
                "Crush": abilities.Crush(),
                "Stomp": abilities.Stomp(),
                "Goad": abilities.Goad(),
            },
        }
        self.resistance["Physical"] = 0.25
        self.resistance["Shadow"] = 0.5
        self.resistance["Holy"] = -0.5
        self.status_immunity = ["Death", "Stun", "Prone"]
        self.action_stack = [
            {"ability": "Attack", "priority": ActionPriority.NORMAL},
            {"ability": "Crush", "priority": ActionPriority.NORMAL},
            {"ability": "Stomp", "priority": ActionPriority.NORMAL},
            {
                "ability": "Shell",
                "priority": ActionPriority.NORMAL,
                "priority_if": {
                    "self_stat": "Magic Defense",
                    "priority": ActionPriority.SKIP,
                    "else": ActionPriority.NORMAL,
                },
            },
            {"ability": "Terrify", "priority": ActionPriority.LOW},
        ]
        self.level.pro_level = 6
        self.picture = "behemoth.txt"


class Balor(Fiend):
    """Greater fiend contract patron; reuses the old devil visual direction."""

    def __init__(self):
        super().__init__(
            name="Balor",
            health=2600,
            mana=650,
            strength=58,
            intel=44,
            wisdom=48,
            con=62,
            charisma=54,
            dex=36,
            attack=148,
            defense=140,
            magic=132,
            magic_def=128,
            exp=0,
        )
        self.equipment = {
            "Weapon": items.DevilBlade(),
            "Armor": items.DevilSkin(),
            "OffHand": items.DevilBlade(),
            "Ring": items.NoRing(),
            "Pendant": items.NoPendant(),
        }
        self.gold = 40000
        self.inventory["Item"] = [items.random_item(7)]
        self.spellbook = {
            "Spells": {
                "Hellfire": abilities.Hellfire(),
                "Corruption": abilities.Corruption(),
                "Terrify": abilities.Terrify(),
                "Regen": abilities.Regen3(),
            },
            "Skills": {"Crush": abilities.Crush(), "Parry": abilities.Parry()},
        }
        self.resistance = {
            "Fire": 0.75,
            "Ice": 0.25,
            "Electric": 0.5,
            "Water": 0.25,
            "Earth": 0.5,
            "Wind": 0.5,
            "Shadow": 0.75,
            "Holy": -0.5,
            "Poison": 1.0,
            "Physical": 0.5,
        }
        self.status_immunity = ["Death", "Poison", "Stone"]
        self.action_stack = [
            {"ability": "Attack", "priority": ActionPriority.NORMAL},
            {"ability": "Hellfire", "priority": ActionPriority.NORMAL},
            {"ability": "Corruption", "priority": ActionPriority.NORMAL},
            {"ability": "Crush", "priority": ActionPriority.NORMAL},
            {
                "ability": "Regen",
                "priority": ActionPriority.LOW,
                "priority_if": [
                    {"condition": "self_hp_pct_lt", "value": 50, "priority": ActionPriority.HIGH},
                    {"condition": "self_status", "value": "Regen", "priority": ActionPriority.LOW},
                ],
            },
        ]
        self.level.pro_level = 7
        self.sight = True
        self.picture = "devil.txt"


class Vesperion(Humanoid):
    """Former Guardian of Voluntas; final boss concept built around choice."""

    RELIC_COUNTERS = {
        "Triangulus": "identity overwrite",
        "Quadrata": "forced order",
        "Hexagonum": "attrition pressure",
        "Luna": "sacrifice manipulation",
        "Polaris": "misdirection",
        "Infinitas": "endurance loops",
    }

    def __init__(self):
        super().__init__(
            name="Vesperion",
            health=3600,
            mana=1100,
            strength=52,
            intel=68,
            wisdom=72,
            con=66,
            charisma=78,
            dex=46,
            attack=150,
            defense=165,
            magic=175,
            magic_def=170,
            exp=0,
        )
        self.enemy_typ = "Celestial"
        self.equipment = {
            "Weapon": items.NoWeapon(),
            "Armor": items.NoArmor(),
            "OffHand": items.NoOffHand(),
            "Ring": items.NoRing(),
            "Pendant": items.NoPendant(),
        }
        self.spellbook = {
            "Spells": {
                "Holy III": abilities.Holy3(),
                "Silence": abilities.Silence(),
                "Ruin": abilities.Ruin(),
                "Oblivion": abilities.Oblivion(),
                "Regen": abilities.Regen3(),
            },
            "Skills": {"Choose Fate": abilities.VesperionChooseFate()},
        }
        self.resistance = {
            "Fire": 0.25,
            "Ice": 0.25,
            "Electric": 0.25,
            "Water": 0.25,
            "Earth": 0.25,
            "Wind": 0.25,
            "Shadow": 0.5,
            "Holy": 0.75,
            "Poison": 1.0,
            "Physical": 0.5,
        }
        self.status_immunity = ["Death", "Poison", "Stone", "Silence", "Berserk"]
        self.action_stack = [
            {"ability": "Choose Fate", "priority": ActionPriority.HIGH},
            {"ability": "Holy III", "priority": ActionPriority.NORMAL},
            {"ability": "Silence", "priority": ActionPriority.NORMAL},
            {"ability": "Ruin", "priority": ActionPriority.NORMAL},
            {"ability": "Oblivion", "priority": ActionPriority.LOW},
            {
                "ability": "Regen",
                "priority": ActionPriority.LOW,
                "priority_if": [
                    {"condition": "self_hp_pct_lt", "value": 45, "priority": ActionPriority.HIGH},
                    {"condition": "self_status", "value": "Regen", "priority": ActionPriority.LOW},
                ],
            },
        ]
        self.level.pro_level = 99
        self.sight = True
        self.picture = "vesperion.txt"
        self._vesperion_pressure_phases_used: set[int] = set()

    def vesperion_phase(self) -> int:
        if self.health.max <= 0:
            return 1
        hp_pct = self.health.current / self.health.max
        if hp_pct <= 0.33:
            return 3
        if hp_pct <= 0.66:
            return 2
        return 1

    def relic_counter_for(self, relic_name: str) -> str | None:
        return self.RELIC_COUNTERS.get(relic_name)

    def guardian_counter_active(self, target: Character, guardian: str) -> bool:
        """Return whether a completed Guardian trial can answer Vesperion."""
        story_state = getattr(target, "main_story", {})
        completed = (
            story_state.get("guardian_trials_completed", {})
            if isinstance(story_state, dict)
            else {}
        )
        return isinstance(completed, dict) and bool(completed.get(guardian))

    def apply_phase_pressure(self, target: Character) -> str:
        """Apply once-per-phase final-battle pressure answered by Guardian trials."""
        phase = self.vesperion_phase()
        used = getattr(self, "_vesperion_pressure_phases_used", set())
        if phase in used:
            return ""
        used.add(phase)
        self._vesperion_pressure_phases_used = used

        messages = [self._phase_pressure_intro(phase)]
        if phase == 1:
            messages.extend(self._apply_phase_one_pressure(target))
        elif phase == 2:
            messages.extend(self._apply_phase_two_pressure(target))
        else:
            messages.extend(self._apply_phase_three_pressure(target))
        return "\n".join(message for message in messages if message)

    def _phase_pressure_intro(self, phase: int) -> str:
        if phase == 1:
            return "Vesperion lowers the Evening Star, offering mercy shaped like a closed hand."
        if phase == 2:
            return "Vesperion enters the second pattern: every star becomes a rule, and every rule tries to choose before you can."
        return "Vesperion enters the final pattern, reaching for the private place where choice becomes self."

    def _apply_phase_one_pressure(self, target: Character) -> list[str]:
        messages: list[str] = []
        if self.guardian_counter_active(target, "Hexagonum"):
            messages.append(
                "Hexagonum answers twilight's attrition with living choice that refuses to be managed into stillness."
            )
        else:
            damage = max(1, int(target.health.max * 0.08))
            target.health.current = max(1, target.health.current - damage)
            messages.append(f"Twilight attrition burns {target.name} for {damage} HP.")

        if self.guardian_counter_active(target, "Luna"):
            messages.append(
                "Luna refuses mercy that would make love into a cage; Voluntas leaves compassion free."
            )
        else:
            mana_loss = max(0, min(target.mana.current, int(target.mana.max * 0.08)))
            target.mana.current -= mana_loss
            messages.append(f"Mercy without freedom drains {mana_loss} MP.")
        return messages

    def _apply_phase_two_pressure(self, target: Character) -> list[str]:
        messages: list[str] = []
        if self.guardian_counter_active(target, "Quadrata"):
            messages.append(
                "Quadrata breaks the forced order before law becomes a lock, preserving the right to consent."
            )
        else:
            self._apply_status(target, "Silence", 1)
            messages.append(f"{target.name}'s voice is arranged into silence.")

        if self.guardian_counter_active(target, "Polaris"):
            messages.append(
                "Polaris fixes true north through the false stars without commanding the step; guidance remains an invitation."
            )
        else:
            self._apply_status(target, "Blind", 1)
            messages.append(f"False stars blur {target.name}'s aim.")
        return messages

    def _apply_phase_three_pressure(self, target: Character) -> list[str]:
        messages: list[str] = []
        if self.guardian_counter_active(target, "Triangulus"):
            messages.append(
                "Triangulus holds the chosen self against the overwrite; Voluntas keeps the name yours."
            )
        else:
            self._apply_status(target, "Silence", 2)
            messages.append(f"{target.name}'s chosen name nearly vanishes.")

        if self.guardian_counter_active(target, "Infinitas"):
            messages.append(
                "Infinitas turns the endless loop into another step freely chosen, not an eternity imposed."
            )
        else:
            damage = max(1, int(target.health.max * 0.10))
            target.health.current = max(1, target.health.current - damage)
            messages.append(f"The loop of endurance crushes {target.name} for {damage} HP.")
        return messages

    @staticmethod
    def _apply_status(target: Character, status_name: str, duration: int) -> None:
        if status_name in getattr(target, "status_immunity", []):
            return
        effect = target.status_effects.get(status_name)
        if effect is None:
            return
        effect.active = True
        effect.duration = max(getattr(effect, "duration", 0), duration)


class ReflectionPsychopomp(Humanoid):
    """Liminal self-copy that tests whether the chosen path can hold."""

    def __init__(self):
        super().__init__(
            name="Reflection Psychopomp",
            health=1400,
            mana=450,
            strength=42,
            intel=42,
            wisdom=42,
            con=42,
            charisma=42,
            dex=42,
            attack=105,
            defense=115,
            magic=125,
            magic_def=120,
            exp=0,
        )
        self.enemy_typ = "Liminal"
        self.reflection_psychopomp = True
        self.equipment = {
            "Weapon": items.NoWeapon(),
            "Armor": items.NoArmor(),
            "OffHand": items.NoOffHand(),
            "Ring": items.NoRing(),
            "Pendant": items.NoPendant(),
        }
        self.spellbook = {
            "Spells": {
                "Holy II": abilities.Holy2(),
                "Silence": abilities.Silence(),
                "Ruin": abilities.Ruin(),
            },
            "Skills": {},
        }
        self.resistance = {
            "Fire": 0.25,
            "Ice": 0.25,
            "Electric": 0.25,
            "Water": 0.25,
            "Earth": 0.25,
            "Wind": 0.25,
            "Shadow": 0.25,
            "Holy": 0.25,
            "Poison": 1.0,
            "Physical": 0.25,
        }
        self.status_immunity = ["Death", "Poison", "Stone", "Berserk"]
        self.action_stack = [
            {"ability": "Attack", "priority": ActionPriority.NORMAL},
            {"ability": "Holy II", "priority": ActionPriority.NORMAL},
            {"ability": "Silence", "priority": ActionPriority.NORMAL},
            {"ability": "Ruin", "priority": ActionPriority.NORMAL},
        ]
        self.level.pro_level = 40
        self.sight = True
        self.picture = "vesperion.txt"
        self.mirrored_path = {
            "class": None,
            "profile": "hybrid",
            "level": 40,
        }

    def mirror_player(self, player) -> None:
        """Lightly scale the Reflection from the current player without copying the full build."""
        level_value = max(1, int(getattr(getattr(player, "level", None), "level", 40) or 40))
        health_max = max(600, int(getattr(getattr(player, "health", None), "max", 1000) * 0.85))
        mana_max = max(180, int(getattr(getattr(player, "mana", None), "max", 400) * 0.65))
        self.health.max = health_max
        self.health.current = health_max
        self.mana.max = mana_max
        self.mana.current = mana_max
        player_combat = getattr(player, "combat", None)
        for stat in ("attack", "defense", "magic", "magic_def"):
            current = int(getattr(self.combat, stat, 0))
            player_value = getattr(player_combat, stat, getattr(player, stat, current))
            setattr(self.combat, stat, max(current, int(player_value * 0.75)))
        self.level.level = level_value
        self._mirror_path_profile(player, level_value)

    def _mirror_path_profile(self, player, level_value: int) -> None:
        player_combat = getattr(player, "combat", None)
        player_stats = getattr(player, "stats", None)
        attack_score = int(getattr(player_combat, "attack", 0)) + int(
            getattr(player_stats, "strength", 0)
        )
        magic_score = (
            int(getattr(player_combat, "magic", 0))
            + int(getattr(player_stats, "intel", 0))
            + int(getattr(player_stats, "wisdom", 0))
        )
        class_name = getattr(getattr(player, "cls", None), "name", None)
        if attack_score >= int(magic_score * 1.2):
            profile = "martial"
            self.resistance["Physical"] = max(self.resistance.get("Physical", 0), 0.4)
            self.action_stack = [
                {"ability": "Attack", "priority": ActionPriority.HIGH},
                {"ability": "Silence", "priority": ActionPriority.NORMAL},
                {"ability": "Ruin", "priority": ActionPriority.NORMAL},
            ]
        elif magic_score >= int(attack_score * 1.2):
            profile = "mystic"
            self.combat.magic = max(self.combat.magic, int(magic_score * 0.55))
            self.action_stack = [
                {"ability": "Holy II", "priority": ActionPriority.HIGH},
                {"ability": "Ruin", "priority": ActionPriority.HIGH},
                {"ability": "Silence", "priority": ActionPriority.NORMAL},
            ]
        else:
            profile = "hybrid"
            self.action_stack = [
                {"ability": "Attack", "priority": ActionPriority.NORMAL},
                {"ability": "Holy II", "priority": ActionPriority.NORMAL},
                {"ability": "Silence", "priority": ActionPriority.NORMAL},
                {"ability": "Ruin", "priority": ActionPriority.NORMAL},
            ]
        self.mirrored_path = {
            "class": class_name,
            "profile": profile,
            "level": level_value,
        }


class GuardianTrialEcho(Humanoid):
    """Retry-safe Liminal combat echo used by combat-heavy Guardian trials."""

    def __init__(self, guardian_name: str, profile: str | None = None):
        self.liminal_trial_guardian = str(guardian_name)
        self.liminal_trial_profile = profile or "echo"
        super().__init__(
            name=f"{self.liminal_trial_guardian} Echo",
            health=900,
            mana=260,
            strength=36,
            intel=36,
            wisdom=36,
            con=36,
            charisma=30,
            dex=34,
            attack=88,
            defense=92,
            magic=96,
            magic_def=94,
            exp=0,
        )
        self.enemy_typ = "Liminal"
        self.guardian_trial_echo = True
        self.gold = 0
        self.equipment = {
            "Weapon": items.NoWeapon(),
            "Armor": items.NoArmor(),
            "OffHand": items.NoOffHand(),
            "Ring": items.NoRing(),
            "Pendant": items.NoPendant(),
        }
        self.spellbook = {
            "Spells": {"Holy II": abilities.Holy2(), "Ruin": abilities.Ruin()},
            "Skills": {},
        }
        self.resistance = {
            "Fire": 0.15,
            "Ice": 0.15,
            "Electric": 0.15,
            "Water": 0.15,
            "Earth": 0.15,
            "Wind": 0.15,
            "Shadow": 0.15,
            "Holy": 0.15,
            "Poison": 1.0,
            "Physical": 0.15,
        }
        self.status_immunity = ["Death", "Poison", "Stone", "Berserk"]
        self.action_stack = [
            {"ability": "Attack", "priority": ActionPriority.NORMAL},
            {"ability": "Holy II", "priority": ActionPriority.NORMAL},
            {"ability": "Ruin", "priority": ActionPriority.NORMAL},
        ]
        if self.liminal_trial_guardian == "Triangulus":
            self.action_stack[0]["priority"] = ActionPriority.HIGH
            self.resistance["Physical"] = 0.25
        elif self.liminal_trial_guardian == "Infinitas":
            self.health.max = 1100
            self.health.current = 1100
            self.resistance["Holy"] = 0.25
        self.level.pro_level = 38
        self.sight = True
        self.picture = "vesperion.txt"


class BrainGorger(Aberration):

    def __init__(self):
        super().__init__(
            name="Brain Gorger",
            health=random.randint(310, 420),
            mana=250,
            strength=27,
            intel=40,
            wisdom=35,
            con=31,
            charisma=25,
            dex=36,
            attack=62,
            defense=47,
            magic=70,
            magic_def=67,
            exp=random.randint(1050, 1310),
        )
        self.status_effects["Blind"] = StatusEffect(True, -1)
        self.equipment = {
            "Weapon": items.Claw3(),
            "Armor": items.NoArmor(),
            "OffHand": items.Claw3(),
            "Ring": items.NoRing(),
            "Pendant": items.NoPendant(),
        }
        self.gold = random.randint(320, 515)
        self.spellbook = {
            "Spells": {"Terrify": abilities.Terrify(), "Weaken Mind": abilities.WeakenMind()},
            "Skills": {
                "Brain Gorge": abilities.BrainGorge(),
                "Mana Shield": abilities.ManaShield(),
            },
        }
        self.resistance["Fire"] = 0.25
        self.resistance["Ice"] = 0.25
        self.resistance["Electric"] = 0.25
        self.resistance["Water"] = 0.25
        self.resistance["Earth"] = 0.25
        self.resistance["Wind"] = 0.25
        self.resistance["Poison"] = 1.0
        self.status_immunity = ["Poison"]
        self.action_stack = [
            {"ability": "Attack", "priority": ActionPriority.NORMAL},
            {"ability": "Brain Gorge", "priority": ActionPriority.NORMAL},
            {"ability": "Weaken Mind", "priority": ActionPriority.NORMAL},
            {"ability": "Terrify", "priority": ActionPriority.NORMAL},
            {
                "ability": "Mana Shield",
                "priority": ActionPriority.HIGH,
                "priority_if": {
                    "self_mana_pct_lt": 0.25,
                    "priority": ActionPriority.SKIP,
                    "else": ActionPriority.HIGH,
                },
            },
        ]
        self.level.pro_level = 5
        self.picture = "braingorger.txt"


class Domingo(Aberration):
    """
    Level 5 Special Boss - guards fifth of six relics (LUNA) required to beat the final boss
    """

    def __init__(self):
        super().__init__(
            name="Domingo",
            health=1500,
            mana=999,
            strength=20,
            intel=50,
            wisdom=40,
            con=45,
            charisma=60,
            dex=50,
            attack=92,
            defense=123,
            magic=135,
            magic_def=119,
            exp=40000,
        )
        self.equipment = {
            "Weapon": items.NoWeapon(),
            "Armor": items.NoArmor(),
            "OffHand": items.NoOffHand(),
            "Ring": items.NoRing(),
            "Pendant": items.NoPendant(),
        }
        self.gold = 25000
        self.spellbook = {
            "Spells": {
                "Photon Sphere": abilities.PhotonSphere(),
                "Desoul": abilities.Desoul(),
                "Boost": abilities.Boost(),
                "Ice Block": abilities.IceBlock(),
            },
            "Skills": {
                "Doublecast": abilities.Doublecast(),
                "Mana Shield": abilities.ManaShield2(),
            },
        }
        self.flying = True
        self.resistance = {
            "Fire": 0.25,
            "Ice": 0.25,
            "Electric": 0.25,
            "Water": 0.25,
            "Earth": 1.0,
            "Wind": -0.25,
            "Shadow": 0.25,
            "Holy": 0.25,
            "Poison": 0.25,
            "Physical": 0,
        }
        self.status_immunity = ["Death", "Stone"]
        self.action_stack = [
            {"ability": "Attack", "priority": ActionPriority.LOW},
            {"ability": "Photon Sphere", "priority": ActionPriority.NORMAL},
            {"ability": "Desoul", "priority": ActionPriority.NORMAL},
            {"ability": "Doublecast", "priority": ActionPriority.NORMAL},
            {
                "ability": "Boost",
                "priority": ActionPriority.NORMAL,
                "priority_if": {
                    "self_stat": "Magic",
                    "priority": ActionPriority.LOW,
                    "else": ActionPriority.NORMAL,
                },
            },
            {
                "ability": "Ice Block",
                "priority": ActionPriority.LOW,
                "priority_if": [
                    {"condition": "self_hp_pct_lt", "value": 0.1, "priority": ActionPriority.HIGH},
                    {
                        "condition": "self_mana_pct_lt",
                        "value": 0.1,
                        "priority": ActionPriority.HIGH,
                    },
                    {
                        "condition": "self_hp_pct_lt",
                        "value": 0.5,
                        "priority": ActionPriority.NORMAL,
                    },
                    {
                        "condition": "self_mana_pct_lt",
                        "value": 0.5,
                        "priority": ActionPriority.NORMAL,
                    },
                ],
            },
            {
                "ability": "Mana Shield",
                "priority": ActionPriority.HIGH,
                "priority_if": {
                    "self_mana_pct_lt": 0.25,
                    "priority": ActionPriority.SKIP,
                    "else": ActionPriority.HIGH,
                },
            },
        ]
        self.level.pro_level = 5
        self.sight = True
        self.picture = "domingo.txt"


class RedDragon(Dragon):
    """
    Level 5 Boss
    Highly resistant to spells and will heal from fire spells
    """

    def __init__(self):
        super().__init__(
            name="Red Dragon",
            health=1900,
            mana=500,
            strength=48,
            intel=34,
            wisdom=42,
            con=52,
            charisma=38,
            dex=32,
            attack=118,
            defense=124,
            magic=96,
            magic_def=148,
            exp=80000,
        )
        self.equipment = {
            "Weapon": items.DragonTail2(),
            "Armor": items.DragonScale(),
            "OffHand": items.DragonClaw2(),
            "Ring": items.NoRing(),
            "Pendant": items.NoPendant(),
        }
        self.gold = 50000
        self.inventory["Item"] = [items.random_item(7)]
        self.spellbook = {
            "Spells": {
                "Regen": abilities.Regen2(),
                "Volcano": abilities.Volcano(),
                "Photon Sphere": abilities.PhotonSphere(),
            },
            "Skills": {
                "Mortal Strike": abilities.MortalStrike2(),
                "Doublecast": abilities.Doublecast(),
                "Dragon Breath (Fire)": abilities.DragonBreathFire(),
            },
        }
        self.action_stack = [
            {"ability": "Attack", "priority": ActionPriority.NORMAL},
            {"ability": "Volcano", "priority": ActionPriority.LOW},
            {"ability": "Photon Sphere", "priority": ActionPriority.LOW},
            {"ability": "Regen", "priority": ActionPriority.LOW_HP_ONLY, "hp_threshold": 0.45},
            {"ability": "Mortal Strike", "priority": ActionPriority.LOW},
            {"ability": "Doublecast", "priority": ActionPriority.NORMAL},
            {
                "ability": "Dragon Breath (Fire)",
                "priority": ActionPriority.LOW,
                "delay": 2,
                "telegraph": "inhaling deeply, roaring flames building in its maw",
            },
        ]
        self.flying = True
        self.resistance = {
            "Fire": 1.5,
            "Ice": 0.5,
            "Electric": 0.5,
            "Water": 0.5,
            "Earth": 1.0,
            "Wind": -0.25,
            "Shadow": 0.5,
            "Holy": 0.5,
            "Poison": 0.75,
            "Physical": 0.25,
        }
        self.status_immunity = ["Death", "Poison", "Stone"]
        self.level.pro_level = 5
        self.sight = True
        self.picture = "reddragon.txt"

    def special_attack(self, target: Character) -> str:
        return abilities.BreatheFire().use(self, target)


class RedDragon2(RedDragon):
    """
    Transform Level 4 creature
    """

    def __init__(self):
        super().__init__()
        self.stats = Stats(0, 0, 0, 0, 0, 0)
        self.combat = Combat(0, 0, 0, 0)


class Circe(Humanoid):
    """ """

    def __init__(self):
        super().__init__(
            name="Circe",
            health=800,
            mana=425,
            strength=35,
            intel=51,
            wisdom=44,
            con=31,
            charisma=48,
            dex=36,
            attack=92,
            defense=77,
            magic=101,
            magic_def=99,
            exp=40000,
        )
        self.equipment = {
            "Weapon": items.Khatvanga(),
            "Armor": items.MerlinRobe(),
            "OffHand": items.InfernalGrimoire(),
            "Ring": items.NoRing(),
            "Pendant": items.NoPendant(),
        }
        self.gold = 18000
        self.inventory["Item"] = [items.random_item(6)]
        self.spellbook = {
            "Spells": {
                "Hex": abilities.Hex(),
                "Sleep": abilities.Sleep(),
                "Enfeeble": abilities.Enfeeble(),
                "Mirror Image": abilities.MirrorImage2(),
                "Magic Missile": abilities.MagicMissile3(),
                "Prismatic Cataclysm": abilities.PrismaticCataclysm(),
            },
            "Skills": {
                "Mana Shield": abilities.ManaShield(),
            },
        }
        self.resistance = {
            "Fire": 0.25,
            "Ice": 0.25,
            "Electric": 0.25,
            "Water": 0.25,
            "Earth": 0.25,
            "Wind": 0.25,
            "Shadow": 0.5,
            "Holy": -0.25,
            "Poison": 0.5,
            "Physical": 0.1,
        }
        self.status_immunity = ["Death", "Stone", "Sleep", "Disarm"]
        self.action_stack = [
            {"ability": "Attack", "priority": ActionPriority.LOW},
            {"ability": "Magic Missile", "priority": ActionPriority.NORMAL},
            {"ability": "Prismatic Cataclysm", "priority": ActionPriority.LOW},
            {"ability": "Hex", "priority": ActionPriority.NORMAL},
            {
                "ability": "Sleep",
                "priority": ActionPriority.NORMAL,
                "priority_if": {
                    "target_status": "Sleep",
                    "priority": ActionPriority.SKIP,
                    "else": ActionPriority.NORMAL,
                },
            },
            {"ability": "Enfeeble", "priority": ActionPriority.NORMAL},
            {"ability": "Mirror Image", "priority": ActionPriority.HIGH},
            {
                "ability": "Mana Shield",
                "priority": ActionPriority.HIGH,
                "priority_if": {
                    "self_mana_pct_lt": 0.2,
                    "priority": ActionPriority.SKIP,
                    "else": ActionPriority.HIGH,
                },
            },
        ]
        self.level.pro_level = 5
        self.sight = True
        self.picture = "nighthag.txt"


class Merzhin(Humanoid):
    """
    Breton name for Merlin; Maid of the Spring gives quest to defeat
    Create additional map for wizard's realm
    Can't die in Realm of Cambion, death will return to UndergroundSpring and reset level
    Special map tiles
    - anti-magic field (can't cast spells and/or skills)
    -
    """

    def __init__(self):
        super().__init__(
            name="Merzhin",
            health=1500,
            mana=2000,
            strength=32,
            intel=61,
            wisdom=58,
            con=28,
            charisma=35,
            dex=32,
            attack=103,
            defense=101,
            magic=140,
            magic_def=164,
            exp=90000,
        )
        self.equipment = {
            "Weapon": items.Khatvanga(),
            "Armor": items.MerlinRobe(),
            "OffHand": items.Vedas(),
            "Ring": items.NoRing(),
            "Pendant": items.NoPendant(),
        }
        self.gold = 125000
        self.inventory["Codex of Eternity"] = [items.CodexEternity]
        self.inventory["Master Key"] = [items.MasterKey]
        self.spellbook = {
            "Spells": {
                "Mirror Image": abilities.MirrorImage2(),
                "Magic Missile": abilities.MagicMissile3(),
                "Photon Sphere": abilities.PhotonSphere(),
                "Disintegrate": abilities.Disintegrate(),
                "Boost": abilities.Boost(),
                "Ruin": abilities.Ruin(),
            },
            "Skills": {"Mana Shield": abilities.ManaShield2()},
        }
        self.status_immunity = ["Death", "Stone", "Disarm"]
        self.action_stack = [
            {"ability": "Attack", "priority": ActionPriority.NORMAL},
            {"ability": "Magic Missile", "priority": ActionPriority.NORMAL},
            {"ability": "Photon Sphere", "priority": ActionPriority.NORMAL},
            {"ability": "Ruin", "priority": ActionPriority.NORMAL},
            {"ability": "Disintegrate", "priority": ActionPriority.NORMAL},
            {
                "ability": "Boost",
                "priority": ActionPriority.NORMAL,
                "priority_if": {
                    "self_stat": "Magic",
                    "priority": ActionPriority.LOW,
                    "else": ActionPriority.NORMAL,
                },
            },
            {"ability": "Mirror Image", "priority": ActionPriority.HIGH},
            {
                "ability": "Mana Shield",
                "priority": ActionPriority.HIGH,
                "priority_if": {
                    "self_mana_pct_lt": 0.25,
                    "priority": ActionPriority.SKIP,
                    "else": ActionPriority.HIGH,
                },
            },
        ]
        self.level.pro_level = 6
        self.sight = True
        self.picture = "merzhin.txt"


# Final Boss Guard
class Cerberus(Fiend):
    """
    Level 6 Special Boss - guards sixth and final of six relics (INFINITAS) required to beat the final boss
    """

    def __init__(self):
        super().__init__(
            name="Cerberus",
            health=2500,
            mana=500,
            strength=65,
            intel=28,
            wisdom=45,
            con=60,
            charisma=40,
            dex=38,
            attack=151,
            defense=142,
            magic=108,
            magic_def=132,
            exp=120000,
        )
        self.equipment = {
            "Weapon": items.CerberusBite(),
            "Armor": items.CerberusHide(),
            "OffHand": items.CerberusClaw(),
            "Ring": items.NoRing(),
            "Pendant": items.NoPendant(),
        }
        self.gold = 100000
        self.inventory["Item"] = [items.random_item(8)]
        self.spellbook = {
            "Spells": {"Regen": abilities.Regen3(), "Shell": abilities.Shell()},
            "Skills": {"Triple Strike": abilities.TripleStrike(), "Trip": abilities.Trip()},
        }
        self.resistance["Fire"] = 1
        self.resistance["Ice"] = -0.25
        self.resistance["Electric"] = 0.5
        self.resistance["Holy"] = 0.25
        self.resistance["Physical"] = 0.5
        self.status_immunity = ["Death", "Stone"]
        self.action_stack = [
            {"ability": "Attack", "priority": ActionPriority.NORMAL},
            {"ability": "Triple Strike", "priority": ActionPriority.NORMAL},
            {"ability": "Trip", "priority": ActionPriority.NORMAL},
            {
                "ability": "Regen",
                "priority": ActionPriority.NORMAL,
                "priority_if": [
                    {"condition": "self_hp_pct_lt", "value": 50, "priority": ActionPriority.HIGH},
                    {"condition": "self_status", "value": "Regen", "priority": ActionPriority.LOW},
                ],
            },
            {
                "ability": "Shell",
                "priority": ActionPriority.NORMAL,
                "priority_if": {
                    "self_status": "Shell",
                    "priority": ActionPriority.SKIP,
                    "else": ActionPriority.NORMAL,
                },
            },
        ]
        self.level.pro_level = 6
        self.sight = True
        self.picture = "cerberus.txt"


class CambionAcolyte(Fiend):
    """
    Support companion for the Devil boss.

    This is implemented as a "familiar-style" helper: the Devil's
    familiar_turn() delegates to CambionAcolyte.support_turn().
    """

    def __init__(self):
        super().__init__(
            name="Cambion Acolyte",
            health=900,
            mana=500,
            strength=24,
            intel=34,
            wisdom=36,
            con=28,
            charisma=22,
            dex=26,
            attack=55,
            defense=60,
            magic=80,
            magic_def=75,
            exp=0,
        )
        self.equipment = {
            "Weapon": items.RuneStaff(),
            "Armor": items.StuddedLeather(),
            "OffHand": items.NoOffHand(),
            "Ring": items.NoRing(),
            "Pendant": items.NoPendant(),
        }
        self.spellbook = {
            "Spells": {
                "Regen": abilities.Regen3(),
                "Shell": abilities.Shell(),
                "Boost": abilities.Boost(),
            },
            "Skills": {},
        }
        self.resistance["Shadow"] = 0.5
        self.resistance["Holy"] = -0.25
        self.status_immunity = ["Death", "Stone"]
        self.level.pro_level = 99
        self.picture = "imp.txt"

    @staticmethod
    def _regen_active(ch: Character) -> bool:
        try:
            return bool(ch.magic_effects.get("Regen").active)
        except Exception:
            return False

    @staticmethod
    def _shell_active(ch: Character) -> bool:
        """
        Shell is implemented as a Magic Defense stat buff (see shell.yaml).

        We treat it as active when the target has an active Magic Defense stat effect.
        """
        try:
            return bool(ch.stat_effects.get("Magic Defense").active)
        except Exception:
            return False

    def support_turn(self, *, boss: Character, player: Character) -> str:
        """
        Deterministic support-only logic:
        1) Apply Shell if not active
        2) Apply Regen if boss HP < 70% and Regen not active
        3) Otherwise do nothing
        """
        if boss is None or not getattr(boss, "is_alive", lambda: False)():
            return ""

        # 1) Shell (defensive buff)
        shell = self.spellbook.get("Spells", {}).get("Shell")
        if shell and not self._shell_active(boss):
            if self.mana.current >= getattr(shell, "cost", 0):
                msg = "Cambion Acolyte chants...\n"
                msg += f"{self.name} casts Shell.\n"
                msg += str(shell.cast(self, target=boss))
                return msg

        # 2) Regen (only when needed)
        regen = self.spellbook.get("Spells", {}).get("Regen")
        if regen and boss.health.max and (boss.health.current / boss.health.max) < 0.70:
            if not self._regen_active(boss) and self.mana.current >= getattr(regen, "cost", 0):
                # Heal/HoT spells default to self-target unless fam=True; we want
                # the acolyte to target the boss, while still paying the mana cost.
                self.mana.current -= int(getattr(regen, "cost", 0) or 0)
                msg = "Cambion Acolyte chants...\n"
                msg += f"{self.name} casts Regen.\n"
                msg += str(regen.cast(self, target=boss, special=True, fam=True))
                return msg

        return ""


# Final Boss
class Devil(Fiend):
    """
    Final Boss; highly resistant to spells; immune to weapon damage except ultimate weapons
    Aided in combat by his acolyte.
    Choose Fate ability:
     if Attack is chosen, damage mod is increased (increases attack damage and armor)
     if Hellfire is chosen, spell mod is increased (increase magic, healing, and magic defense)
     if Crush is chosen, both damage and spell mod decrease
    """

    def __init__(self):
        super().__init__(
            name="The Devil",
            health=3500,
            mana=800,
            strength=65,
            intel=48,
            wisdom=60,
            con=70,
            charisma=70,
            dex=40,
            attack=170,
            defense=170,
            magic=150,
            magic_def=140,
            exp=0,
        )
        self.equipment = {
            "Weapon": items.DevilBlade(),
            "Armor": items.DevilSkin(),
            "OffHand": items.DevilBlade(),
            "Ring": items.NoRing(),
            "Pendant": items.NoPendant(),
        }
        self.spellbook = {
            "Spells": {
                "Hellfire": abilities.Hellfire(),
                "Terrify": abilities.Terrify(),
                "Regen": abilities.Regen3(),
            },
            "Skills": {
                "Choose Fate": abilities.ChooseFate(),
                "Crush": abilities.Crush(),
                "Parry": abilities.Parry(),
            },
        }
        self.resistance = {
            "Fire": 0.5,
            "Ice": 0.5,
            "Electric": 0.5,
            "Water": 0.5,
            "Earth": 0.5,
            "Wind": 0.5,
            "Shadow": 0.5,
            "Holy": -0.25,
            "Poison": 1.0,
            "Physical": 1.0,
        }
        self.status_immunity = ["Death", "Poison", "Stone"]
        self.damage_mod = 0
        self.spell_mod = 0
        self.action_stack = [
            {"ability": "Attack", "priority": ActionPriority.NORMAL},
            {"ability": "Choose Fate", "priority": ActionPriority.NORMAL},
            {"ability": "Hellfire", "priority": ActionPriority.NORMAL},
            {"ability": "Terrify", "priority": ActionPriority.NORMAL},
            {
                "ability": "Regen",
                "priority": ActionPriority.NORMAL,
                "priority_if": [
                    {"condition": "self_hp_pct_lt", "value": 50, "priority": ActionPriority.HIGH},
                    {"condition": "self_status", "value": "Regen", "priority": ActionPriority.LOW},
                ],
            },
            {"ability": "Crush", "priority": ActionPriority.LOW},
        ]
        self.level.pro_level = 99
        self.sight = True
        self.picture = "devil.txt"
        # Support companion (acts during companion_turn via familiar_turn()).
        self.acolyte = CambionAcolyte()

    def familiar_turn(self, target: Character) -> str:
        try:
            if hasattr(self, "acolyte") and self.acolyte and self.acolyte.mana.current > 0:
                return self.acolyte.support_turn(boss=self, player=target)
        except Exception:
            pass
        return ""

    def check_mod(
        self,
        mod: str,
        enemy: Character | None = None,
        typ: str | None = None,
        luck_factor: int = 1,
        ultimate: bool = False,
        ignore: bool = False,
    ) -> int | float:
        class_mod = 0
        berserk_per = (
            int(self.status_effects["Berserk"].active) * 0.1
        )  # berserk increases damage by 10%
        disarm_damage_multiplier = 0.5 if self.is_disarmed() else 1.0
        if mod == "weapon":
            weapon_mod = self.equipment["Weapon"].damage * int(not self.is_disarmed())
            weapon_mod += self.stat_effects["Attack"].extra * self.stat_effects["Attack"].active
            total_mod = (weapon_mod + class_mod + self.combat.attack) * disarm_damage_multiplier
            return max(0, int(total_mod * (1 + berserk_per)))
        if mod == "offhand":
            off_mod = self.equipment["OffHand"].damage
            class_mod += self.damage_mod
            off_mod += self.stat_effects["Attack"].extra * self.stat_effects["Attack"].active
            return max(0, int((off_mod + class_mod + self.combat.attack) * (0.75 + berserk_per)))
        if mod == "armor":
            class_mod += self.damage_mod
            armor_mod = self.equipment["Armor"].armor
            armor_mod += self.stat_effects["Defense"].extra * self.stat_effects["Defense"].active
            return max(0, (armor_mod * (not ignore)) + class_mod + self.combat.defense)
        if mod == "magic":
            magic_mod = int(self.stats.intel // 4) * 10
            class_mod += self.spell_mod
            magic_mod += self.stat_effects["Magic"].extra * self.stat_effects["Magic"].active
            return max(0, magic_mod + class_mod + self.combat.magic)
        if mod == "magic def":
            m_def_mod = int(self.stats.wisdom) + (int(self.stats.charisma) // 2)
            class_mod += self.spell_mod
            m_def_mod += (
                self.stat_effects["Magic Defense"].extra * self.stat_effects["Magic Defense"].active
            )
            return max(0, m_def_mod + class_mod + self.combat.magic_def)
        if mod == "heal":
            class_mod += self.spell_mod
            heal_mod = self.stats.wisdom * self.level.pro_level
            heal_mod += self.stat_effects["Magic"].extra * self.stat_effects["Magic"].active
            return max(0, heal_mod + class_mod + self.combat.magic)
        if mod == "resist":
            if ultimate and typ == "Physical":  # ultimate weapons bypass Physical resistance
                return 0.0
            res_mod = self.resistance.get(typ, 0)
            if self.flying:
                if typ == "Wind":
                    res_mod = -0.25
            return res_mod
        if mod == "luck":
            lf = max(1, int(luck_factor))
            base = int(self.stats.charisma) + int(self.stats.wisdom)
            return max(0, (base * 2) // lf)
        if mod == "speed":
            speed_mod = self.stats.dex
            speed_mod += self.stat_effects["Speed"].extra * self.stat_effects["Speed"].active
            return speed_mod
        return 0
