###########################################
"""race manager"""

from __future__ import annotations

from dataclasses import dataclass
from textwrap import wrap

from .identity import RACE_TYPES


# ── Racial traits (7 sins / 7 virtues) ───────────────────────────────
@dataclass(frozen=True)
class RacialTrait:
    """Displayable always-on race trait (used by character creation + UI screens)."""

    name: str
    description: str


# Race objects
class Race:
    """
    Base definition for the Race class
    Stat parameters define the starting stats for each race
    Class restriction lists the available classes for each race
    Resistance describes each race's resistances to magic
    """

    race_id: str

    def __init_subclass__(cls, *, race_id: str | None = None, **kwargs: object) -> None:
        """Register every race type at definition time for strict persistence."""
        super().__init_subclass__(**kwargs)
        cls.race_id = RACE_TYPES.register(cls, race_id)

    def __init__(
        self,
        name: str,
        description: str,
        strength: int,
        intel: int,
        wisdom: int,
        con: int,
        charisma: int,
        dex: int,
        base_attack: int,
        base_defense: int,
        base_magic: int,
        base_magic_def: int,
        cls_res: dict,
        resistance: dict,
        virtue: RacialTrait | None = None,
        sin: RacialTrait | None = None,
    ):
        self.name = name
        self.description = "\n".join(wrap(description, 75, break_on_hyphens=False))
        self.strength = strength
        self.intel = intel
        self.wisdom = wisdom
        self.con = con
        self.charisma = charisma
        self.dex = dex
        self.base_attack = base_attack
        self.base_defense = base_defense
        self.base_magic = base_magic
        self.base_magic_def = base_magic_def
        self.cls_res = cls_res
        self.resistance = resistance
        self.virtue = virtue or RacialTrait(name="", description="")
        self.sin = sin or RacialTrait(name="", description="")


class Human(Race):

    def __init__(self):
        super().__init__(
            name="Human",
            description="Humans are something you can relate to. They are the most "
            "versatile of all races, making a viable option for all classes. "
            "While they have no magical resistances, they also have no "
            "weaknesses.",
            strength=10,
            intel=10,
            wisdom=10,
            con=10,
            charisma=10,
            dex=10,
            base_attack=2,
            base_defense=2,
            base_magic=2,
            base_magic_def=2,
            cls_res={
                "Base": ["Warrior", "Mage", "Footpad", "Healer", "Pathfinder"],
                "First": [
                    "Weapon Master",
                    "Paladin",
                    "Lancer",
                    "Sentinel",
                    "Sorcerer",
                    "Warlock",
                    "Spellblade",
                    "Conjurer",
                    "Thief",
                    "Inquisitor",
                    "Assassin",
                    "Spell Stealer",
                    "Cleric",
                    "Priest",
                    "Monk",
                    "Bard",
                    "Druid",
                    "Diviner",
                    "Shaman",
                    "Ranger",
                ],
                "Second": [
                    "Grandmaster of Arms",
                    "Berserker",
                    "Crusader",
                    "Dragoon",
                    "Stalwart Defender",
                    "Wizard",
                    "Knight Enchanter",
                    "Thaumaturgist",
                    "Rogue",
                    "Seeker",
                    "Ninja",
                    "Arcane Trickster",
                    "Templar",
                    "Hierophant",
                    "Archbishop",
                    "Master Monk",
                    "Troubadour",
                    "Lycan",
                    "Archdruid",
                    "Astromancer",
                    "Soulcatcher",
                    "Beast Master",
                ],
            },
            resistance={
                "Fire": 0.0,
                "Ice": 0.0,
                "Electric": 0.0,
                "Water": 0.0,
                "Earth": 0.0,
                "Wind": 0.0,
                "Shadow": 0.0,
                "Holy": 0.0,
                "Poison": 0.0,
                "Physical": 0.0,
            },
            virtue=RacialTrait(
                name="Diligence",
                description="You learn quickly from battle, gaining increased experience.",
            ),
            sin=RacialTrait(
                name="Lust",
                description="Temptation dulls your caution, reducing your resistance to debilitating effects.",
            ),
        )


class Elf(Race):

    def __init__(self):
        super().__init__(
            name="Elf",
            description="Elves are the magic users of the game. They are excellent spell "
            "casters and have decent resistance to elemental magic. They are not,"
            " however, very good at fighting with weapons and have low "
            "constitution, making them more susceptible to physical damage.",
            strength=6,
            intel=12,
            wisdom=11,
            con=8,
            charisma=11,
            dex=12,
            base_attack=1,
            base_defense=1,
            base_magic=3,
            base_magic_def=3,
            cls_res={
                "Base": ["Mage", "Footpad", "Healer", "Pathfinder"],
                "First": [
                    "Sorcerer",
                    "Warlock",
                    "Spellblade",
                    "Conjurer",
                    "Thief",
                    "Inquisitor",
                    "Assassin",
                    "Spell Stealer",
                    "Priest",
                    "Bard",
                    "Druid",
                    "Diviner",
                    "Ranger",
                ],
                "Second": [
                    "Wizard",
                    "Knight Enchanter",
                    "Thaumaturgist",
                    "Rogue",
                    "Seeker",
                    "Ninja",
                    "Arcane Trickster",
                    "Archbishop",
                    "Troubadour",
                    "Archdruid",
                    "Astromancer",
                    "Beast Master",
                ],
            },
            resistance={
                "Fire": 0.25,
                "Ice": 0.25,
                "Electric": 0.25,
                "Water": 0.25,
                "Earth": 0.25,
                "Wind": 0.25,
                "Shadow": 0.0,
                "Holy": 0.0,
                "Poison": 0.0,
                "Physical": -0.2,
            },
            virtue=RacialTrait(
                name="Humility",
                description="You see through deception, suffering fewer penalties when fighting the unseen or obscured.",
            ),
            sin=RacialTrait(
                name="Pride",
                description="Your pride resists aid, slightly reducing healing received.",
            ),
        )


class HalfElf(Race):

    def __init__(self):
        super().__init__(
            name="Half Elf",
            description="Half elves are the result of the interbreeding between humans and "
            "elves. They are almost as versatile as humans and possess an "
            "improved magical prowess, as well as mild elemental resistance. "
            "Like their elf cousins, they do have a slight susceptibility to "
            "physical damage.",
            strength=9,
            intel=11,
            wisdom=10,
            con=9,
            charisma=10,
            dex=11,
            base_attack=2,
            base_defense=1,
            base_magic=2,
            base_magic_def=3,
            cls_res={
                "Base": ["Warrior", "Mage", "Footpad", "Healer", "Pathfinder"],
                "First": [
                    "Weapon Master",
                    "Paladin",
                    "Lancer",
                    "Sorcerer",
                    "Warlock",
                    "Spellblade",
                    "Conjurer",
                    "Thief",
                    "Inquisitor",
                    "Assassin",
                    "Spell Stealer",
                    "Cleric",
                    "Priest",
                    "Monk",
                    "Bard",
                    "Druid",
                    "Diviner",
                    "Ranger",
                ],
                "Second": [
                    "Grandmaster of Arms",
                    "Crusader",
                    "Dragoon",
                    "Wizard",
                    "Knight Enchanter",
                    "Thaumaturgist",
                    "Rogue",
                    "Seeker",
                    "Ninja",
                    "Arcane Trickster",
                    "Templar",
                    "Hierophant",
                    "Archbishop",
                    "Master Monk",
                    "Troubadour",
                    "Archdruid",
                    "Astromancer",
                    "Beast Master",
                ],
            },
            resistance={
                "Fire": 0.1,
                "Ice": 0.1,
                "Electric": 0.1,
                "Water": 0.1,
                "Earth": 0.1,
                "Wind": 0.1,
                "Shadow": 0.0,
                "Holy": 0.0,
                "Poison": 0.0,
                "Physical": -0.1,
            },
            virtue=RacialTrait(
                name="Gratitude",
                description="You recover steadily, increasing healing received.",
            ),
            sin=RacialTrait(
                name="Envy",
                description="Envy undermines resolve, slightly reducing your critical damage spikes.",
            ),
        )


class HalfGiant(Race):

    def __init__(self):
        super().__init__(
            name="Half Giant",
            description="We do not speculate on how they are made but we do know the "
            "union between humans and giants does occur. These half giants "
            "dwarf most men but are seen as runts amongst their giant "
            "brethren. Their brutish nature make the excellent Warriors "
            "and not much else. Half giants have mild resistances to "
            "poisons and physical damage but poor agility and sharp "
            "weaknesses against most other magics, especially holy spells.",
            strength=15,
            intel=7,
            wisdom=8,
            con=14,
            charisma=6,
            dex=8,
            base_attack=4,
            base_defense=2,
            base_magic=1,
            base_magic_def=0,
            cls_res={
                "Base": ["Warrior", "Footpad", "Healer", "Pathfinder"],
                "First": ["Weapon Master", "Sentinel", "Inquisitor", "Monk", "Ranger"],
                "Second": ["Berserker", "Stalwart Defender", "Seeker", "Monk", "Beast Master"],
            },
            resistance={
                "Fire": -0.15,
                "Ice": -0.15,
                "Electric": -0.15,
                "Water": -0.15,
                "Earth": -0.15,
                "Wind": -0.15,
                "Shadow": -0.1,
                "Holy": -0.4,
                "Poison": 0.2,
                "Physical": 0.15,
            },
            virtue=RacialTrait(
                name="Perseverance",
                description="Your charge cannot be broken by pain alone; only incapacitation can interrupt it.",
            ),
            sin=RacialTrait(
                name="Sloth",
                description="You advance slowly, gaining reduced experience from combat.",
            ),
        )


class Gnome(Race):

    def __init__(self):
        super().__init__(
            name="Gnome",
            description="Gnomes are very charismatic, giving them a distinct advantage in "
            "money making, vendor relations, and are especially lucky. They are "
            "also above average spell caster with a slight affinity toward the "
            "divine, giving them a slight resistance to holy spells. Gnomes "
            "prefer the civilized world and thus are not found among the ranks"
            " of Pathfinders.",
            strength=8,
            intel=10,
            wisdom=12,
            con=8,
            charisma=12,
            dex=10,
            base_attack=1,
            base_defense=2,
            base_magic=2,
            base_magic_def=3,
            cls_res={
                "Base": ["Warrior", "Mage", "Footpad", "Healer"],
                "First": [
                    "Weapon Master",
                    "Paladin",
                    "Sorcerer",
                    "Warlock",
                    "Spellblade",
                    "Conjurer",
                    "Thief",
                    "Inquisitor",
                    "Assassin",
                    "Spell Stealer",
                    "Cleric",
                    "Priest",
                    "Bard",
                ],
                "Second": [
                    "Grandmaster of Arms",
                    "Crusader",
                    "Wizard",
                    "Shadowcaster",
                    "Knight Enchanter",
                    "Thaumaturgist",
                    "Rogue",
                    "Seeker",
                    "Ninja",
                    "Arcane Trickster",
                    "Templar",
                    "Hierophant",
                    "Archbishop",
                    "Troubadour",
                ],
            },
            resistance={
                "Fire": 0.0,
                "Ice": 0.0,
                "Electric": 0.0,
                "Water": 0.0,
                "Earth": 0.0,
                "Wind": 0.0,
                "Shadow": -0.2,
                "Holy": 0.2,
                "Poison": 0.0,
                "Physical": 0.0,
            },
            virtue=RacialTrait(
                name="Charity",
                description="Your charm opens purses; charisma has a stronger effect on gold outcomes.",
            ),
            sin=RacialTrait(
                name="Greed",
                description="When you carry too much, the penalties of encumbrance are harsher.",
            ),
        )


class Dwarf(Race):

    def __init__(self):
        super().__init__(
            name="Dwarf",
            description="Dwarves are short in stature only, being amongst the strongest "
            "both in body and will. They are lacking in physical agility and "
            "have a healthy mistrust of the arcane. As beings of the Earth, "
            "dwarves have resistance against earth, poison, and physical "
            "damage but are weak against shadow magic.",
            strength=12,
            intel=10,
            wisdom=10,
            con=12,
            charisma=8,
            dex=8,
            base_attack=2,
            base_defense=3,
            base_magic=1,
            base_magic_def=2,
            cls_res={
                "Base": ["Warrior", "Healer", "Pathfinder"],
                "First": ["Weapon Master", "Paladin", "Sentinel", "Cleric", "Priest", "Ranger"],
                "Second": [
                    "Berserker",
                    "Grandmaster of Arms",
                    "Crusader",
                    "Dragoon",
                    "Stalwart Defender",
                    "Templar",
                    "Hierophant",
                    "Archbishop",
                    "Beast Master",
                ],
            },
            resistance={
                "Fire": 0.0,
                "Ice": 0.0,
                "Electric": 0.0,
                "Water": 0.0,
                "Earth": 0.25,
                "Wind": 0.0,
                "Shadow": -0.3,
                "Holy": 0.0,
                "Poison": 0.25,
                "Physical": 0.1,
            },
            virtue=RacialTrait(
                name="Temperance",
                description="Combat consumables are more effective (does not affect permanent stat potions).",
            ),
            sin=RacialTrait(
                name="Gluttony",
                description="Overindulgence brings a hangover: using combat consumables can hinder your next fight.",
            ),
        )


class HalfOrc(Race):

    def __init__(self):
        super().__init__(
            name="Half Orc",
            description="Half orcs are the result of interbreeding between humans and "
            "orcs, which while rare does occur. While not a strong as their "
            "fullblood brethren, half orcs are much stronger on average "
            "than humans. However the stigma related to half orcs makes "
            "them far less charismatic, while there inherit bloodlust "
            "makes any pursuit of the divine unappealing.",
            strength=12,
            intel=10,
            wisdom=8,
            con=11,
            charisma=8,
            dex=11,
            base_attack=3,
            base_defense=2,
            base_magic=2,
            base_magic_def=1,
            cls_res={
                "Base": ["Warrior", "Mage", "Footpad", "Pathfinder"],
                "First": [
                    "Weapon Master",
                    "Lancer",
                    "Sentinel",
                    "Sorcerer",
                    "Warlock",
                    "Spellblade",
                    "Thief",
                    "Inquisitor",
                    "Assassin",
                    "Spell Stealer",
                    "Diviner",
                    "Shaman",
                    "Ranger",
                ],
                "Second": [
                    "Berserker",
                    "Grandmaster of Arms",
                    "Dragoon",
                    "Stalwart Defender",
                    "Wizard",
                    "Knight Enchanter",
                    "Rogue",
                    "Seeker",
                    "Ninja",
                    "Arcane Trickster",
                    "Astromancer",
                    "Soulcatcher",
                    "Beast Master",
                ],
            },
            resistance={
                "Fire": 0.0,
                "Ice": 0.0,
                "Electric": 0.0,
                "Water": 0.0,
                "Earth": 0.0,
                "Wind": 0.0,
                "Shadow": 0.2,
                "Holy": -0.2,
                "Poison": 0.1,
                "Physical": 0.0,
            },
            virtue=RacialTrait(
                name="Patience",
                description="You endure the worst blows, taking reduced damage from critical hits.",
            ),
            sin=RacialTrait(
                name="Wrath",
                description="Pain can trigger Blind Rage: you keep control, but your aim suffers briefly.",
            ),
        )


races_dict = {
    "Human": Human,
    "Elf": Elf,
    "Half Elf": HalfElf,
    "Half Giant": HalfGiant,
    "Gnome": Gnome,
    "Dwarf": Dwarf,
    "Half Orc": HalfOrc,
}
