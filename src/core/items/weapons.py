"""Weapon implementations."""

from __future__ import annotations

import random
from textwrap import wrap
from typing import TYPE_CHECKING

from .. import abilities
from ..character import StatusEffect
from .base import Weapon

if TYPE_CHECKING:
    from ..combat.combat_result import CombatResultGroup


class NoWeapon(Weapon):

    def __init__(self):
        super().__init__(
            name="Bare Hands",
            description="Nothing but good ol' lefty and righty.",
            value=0,
            rarity=0,
            damage=2,
            crit=0.025,
            handed=1,
            subtyp="None",
            unequip=True,
            off=True,
        )


class NaturalWeapon(Weapon):

    def __init__(self, name: str, damage: int, crit: float, description: str, off: bool) -> None:
        super().__init__(
            name=name,
            damage=damage,
            crit=crit,
            subtyp="Natural",
            description=description,
            handed=1,
            off=off,
            rarity=0,
            unequip=False,
            value=0,
        )
        self.att_name = "attacks"


class BrassKnuckles(Weapon):

    def __init__(self):
        super().__init__(
            name="Brass Knuckles",
            description="Brass knuckles are pieces of metal shaped to fit around "
            "the knuckles to add weight during hand-to-hand combat.",
            value=2000,
            rarity=0.85,
            damage=12,
            crit=0.1,
            handed=1,
            subtyp="Fist",
            unequip=False,
            off=True,
        )
        self.weight = 1


class Cestus(Weapon):

    def __init__(self):
        super().__init__(
            name="Cestus",
            description="A cestus is a battle glove that is typically used in gladiatorial "
            "events.",
            value=7500,
            rarity=0.75,
            damage=16,
            crit=0.15,
            handed=1,
            subtyp="Fist",
            unequip=False,
            off=True,
        )
        self.weight = 1


class BattleGauntlet(Weapon):

    def __init__(self):
        super().__init__(
            name="Battle Gauntlet",
            description="A battle gauntlet is a type of glove that protects the "
            "hand and wrist of a combatant, constructed with metal "
            "platings to inflict additional damage.",
            value=20000,
            rarity=0.5,
            damage=24,
            crit=0.2,
            handed=1,
            subtyp="Fist",
            unequip=False,
            off=True,
        )
        self.weight = 3


class BaghNahk(Weapon):

    def __init__(self):
        super().__init__(
            name="Bagh Nahk",
            description="The bagh nahk is a 'fist-load, claw-like' dagger designed to "
            "fit over the knuckles or be concealed under and against the "
            "palm.",
            value=45000,
            rarity=0.4,
            damage=30,
            crit=0.25,
            handed=1,
            subtyp="Fist",
            unequip=False,
            off=True,
        )
        self.weight = 1


class IndrasFist(Weapon):
    """
    Electric element
    """

    def __init__(self):
        super().__init__(
            name="Indra's Fist",
            description="Indra's Fist is a powerful weapon named after the Hindu god"
            " of thunder and lightning and is said to embody the sheer "
            "force and power of a thunderstorm. The weapon crackles with"
            " electric energy, emitting a faint glow as if it holds the "
            "essence of a storm within.",
            value=80000,
            rarity=0.2,
            damage=40,
            crit=0.3,
            handed=1,
            subtyp="Fist",
            unequip=False,
            off=True,
        )
        self.weight = 1
        self.element = "Electric"

    def special_effect(self, results: CombatResultGroup) -> None:
        result = results[-1]
        if not any(
            [
                "Stun" in result.target.status_immunity,
                "Status-Stun" in result.target.equipment["Pendant"].mod,
                "Status-All" in result.target.equipment["Pendant"].mod,
            ]
        ):
            if result.crit > 1:
                att_roll = random.randint(
                    result.actor.stats.strength // 2, result.actor.stats.strength
                )
                def_roll = random.randint(result.target.stats.con // 2, result.target.stats.con)
                if result.target.stun_contest_success(result.actor, att_roll, def_roll):
                    duration = max(1, result.actor.stats.strength // 10)
                    if result.target.apply_stun(duration, source=self.name, applier=result.actor):
                        result.effects_applied["Stun"] = True


class GodsHand(Weapon):
    """
    Ultimate weapon; deals additional holy damage that won't heal even if the enemy would normally heal with holy damage
    Holy element
    """

    def __init__(self):
        super().__init__(
            name="God's Hand",
            description="With the appearance of an ordinary white glove, this weapon is"
            " said to be imbued with the power of God.",
            value=0,
            rarity=0,
            damage=52,
            crit=0.33,
            handed=1,
            subtyp="Fist",
            unequip=False,
            off=True,
        )
        self.ultimate = True
        self.element = "Holy"

    def special_effect(self, results: CombatResultGroup) -> None:
        result = results[-1]
        resist = result.target.check_mod("resist", enemy=result.actor, typ=self.element)
        damage = int(random.randint(result.damage // 2, result.damage) * (1 - resist))
        if damage > 0:
            result.target.health.current -= damage
            result.damage += damage
            result.extra["Holy Damage"] = True


class Dirk(Weapon):

    def __init__(self):
        super().__init__(
            name="Dirk",
            description="A dirk is a long bladed thrusting dagger with a smooth jumpshot.",
            value=125,
            rarity=0.95,
            damage=4,
            crit=0.15,
            handed=1,
            subtyp="Dagger",
            unequip=False,
            off=True,
        )
        self.weight = 2


class Baselard(Weapon):

    def __init__(self):
        super().__init__(
            name="Baselard",
            description="A baselard is a short bladed weapon with an H-shaped hilt.",
            value=1500,
            rarity=0.85,
            damage=10,
            crit=0.2,
            handed=1,
            subtyp="Dagger",
            unequip=False,
            off=True,
        )
        self.weight = 3


class Kris(Weapon):

    def __init__(self):
        super().__init__(
            name="Kris",
            description="A Kris is an asymmetrical dagger with distinctive blade-patterning "
            "achieved through alternating laminations of iron and nickelous iron,"
            " easily identified by its distinct wavy blade.",
            value=5000,
            rarity=0.75,
            damage=14,
            crit=0.25,
            handed=1,
            subtyp="Dagger",
            unequip=False,
            off=True,
        )
        self.weight = 3


class Rondel(Weapon):

    def __init__(self):
        super().__init__(
            name="Rondel",
            description="A type of dagger with a stiff-blade, named for the round hand "
            "guard and round or spherical pommel.",
            value=17000,
            rarity=0.5,
            damage=22,
            crit=0.33,
            handed=1,
            subtyp="Dagger",
            unequip=False,
            off=True,
        )
        self.weight = 3


class Kukri(Weapon):

    def __init__(self):
        super().__init__(
            name="Kukri",
            description="A kukri is a traditional Nepalese knife, recognized for its "
            "distinctive inwardly curved blade that widens towards the tip. "
            "The blade's unique design delivers powerful strikes, making it "
            "ideal for combat, especially in close quarters.",
            value=42000,
            rarity=0.4,
            damage=26,
            crit=0.4,
            handed=1,
            subtyp="Dagger",
            unequip=False,
            off=True,
        )
        self.weight = 4


class Khanjar(Weapon):

    def __init__(self):
        super().__init__(
            name="Khanjar",
            description="A khanjar is a curved dagger of Middle Eastern origin, known for"
            " its distinctive double-edged blade that tapers to a sharp "
            "point. It is designed for swift, precise strikes, making it "
            "ideal for close-quarters encounters.",
            value=75000,
            rarity=0.2,
            damage=36,
            crit=0.45,
            handed=1,
            subtyp="Dagger",
            unequip=False,
            off=True,
        )
        self.weight = 3


class Carnwennan(Weapon):
    """
    Ultimate weapon; chance to stun target on critical
    """

    def __init__(self):
        super().__init__(
            name="Carnwennan",
            description="King Arthur's dagger, sometimes described to shroud the user "
            "in shadow.",
            value=0,
            rarity=0,
            damage=48,
            crit=0.5,
            handed=1,
            subtyp="Dagger",
            unequip=False,
            off=True,
        )
        self.weight = 2
        self.ultimate = True

    def special_effect(self, results: CombatResultGroup) -> None:
        result = results[-1]
        if not any(
            [
                "Stun" in result.target.status_immunity,
                "Status-Stun" in result.target.equipment["Pendant"].mod,
                "Status-All" in result.target.equipment["Pendant"].mod,
            ]
        ):
            if result.crit > 1:
                spd = result.actor.check_mod("speed", enemy=result.target)
                att_roll = random.randint(spd // 2, spd)
                def_roll = random.randint(result.target.stats.con // 2, result.target.stats.con)
                if result.target.stun_contest_success(result.actor, att_roll, def_roll):
                    duration = max(1, result.actor.check_mod("speed", enemy=result.target) // 10)
                    if result.target.apply_stun(duration, source=self.name, applier=result.actor):
                        result.effects_applied["Stun"] = True
        return results


class Rapier(Weapon):

    def __init__(self):
        super().__init__(
            name="Rapier",
            description="A rapier is a slender and sharply pointed two-edged blade with a "
            "protective hilt.",
            value=125,
            rarity=0.95,
            damage=6,
            crit=0.075,
            handed=1,
            subtyp="Sword",
            unequip=False,
            off=True,
        )
        self.weight = 5


class Jian(Weapon):

    def __init__(self):
        super().__init__(
            name="Jian",
            description="A jian is a double-edged straight sword with a guard that protects "
            "the wielder from opposing blades,",
            value=2000,
            rarity=0.85,
            damage=14,
            crit=0.1,
            handed=1,
            subtyp="Sword",
            unequip=False,
            off=True,
        )
        self.weight = 6


class Talwar(Weapon):

    def __init__(self):
        super().__init__(
            name="Talwar",
            description="A talwar is curved, single-edged sword with an iron disc hilt and "
            "knucklebow, and a fullered blade.",
            value=5500,
            rarity=0.75,
            damage=20,
            crit=0.15,
            handed=1,
            subtyp="Sword",
            unequip=False,
            off=True,
        )
        self.weight = 8


class Shamshir(Weapon):

    def __init__(self):
        super().__init__(
            name="Shamshir",
            description="A shamshir has a radically curved blade featuring a slim blade "
            "with almost no taper until the very tip.",
            value=21000,
            rarity=0.5,
            damage=28,
            crit=0.2,
            handed=1,
            subtyp="Sword",
            unequip=False,
            off=True,
        )
        self.weight = 10


class Khopesh(Weapon):

    def __init__(self):
        super().__init__(
            name="Khopesh",
            description="A khopesh is a sickle-shaped sword that evolved from battle axes"
            " and that can be used to disarm an opponent.",
            value=47000,
            rarity=0.4,
            damage=36,
            crit=0.25,
            handed=1,
            subtyp="Sword",
            unequip=False,
            off=True,
        )
        self.weight = 10

    def special_effect(self, results: CombatResultGroup) -> None:
        result = results[-1]
        if not result.target.physical_effects["Disarm"].active:
            if result.target.can_be_disarmed():
                chance = result.target.check_mod("luck", enemy=result.actor, luck_factor=10)
                if (
                    random.randint(result.actor.stats.strength // 2, result.actor.stats.strength)
                    > random.randint(
                        result.target.check_mod("speed", enemy=result.actor) // 2,
                        result.target.check_mod("speed", enemy=result.actor),
                    )
                    + chance
                ):
                    result.target.physical_effects["Disarm"].active = True
                    result.target.physical_effects["Disarm"].duration = (
                        result.actor.stats.strength // 10
                    )
                    result.effects_applied["Physical"].append("Disarm")
        return results


class Falchion(Weapon):

    def __init__(self):
        super().__init__(
            name="Falchion",
            description="A falchion is a one-handed sword with a broad, curved blade "
            "that is designed to deliver powerful cleaving and chopping "
            "blows. Its slight curve and weight distribution make it capable"
            " of delivering decisive strikes, while the sturdy design "
            "provides balance for quick, fluid attacks.",
            value=90000,
            rarity=0.2,
            damage=46,
            crit=0.3,
            handed=1,
            subtyp="Sword",
            unequip=False,
            off=True,
        )
        self.weight = 10


class Excalibur(Weapon):
    """
    Ultimate weapon; chance on crit to add a bleed on target
    """

    def __init__(self):
        super().__init__(
            name="Excalibur",
            description="The legendary sword of King Arthur, bestowed upon him by the "
            "Lady of the Lake.",
            value=0,
            rarity=0,
            damage=60,
            crit=0.35,
            handed=1,
            subtyp="Sword",
            unequip=False,
            off=True,
        )
        self.weight = 8
        self.ultimate = True

    def special_effect(self, results: CombatResultGroup) -> None:
        result = results[-1]
        if result.crit > 1:
            if random.randint(
                (result.actor.stats.strength // 2), result.actor.stats.strength
            ) > random.randint(result.target.stats.con // 2, result.target.stats.con):
                duration = max(1, result.actor.stats.strength // 10)
                bleed_dmg = max(result.actor.stats.strength // 2, result.damage)
                if not result.target.physical_effects["Bleed"].active:
                    result.target.physical_effects["Bleed"].active = True
                    result.effects_applied["Physical"].append("Bleed")
                else:
                    result.effects_applied["Physical"].append("Bleed+")
                result.target.physical_effects["Bleed"].duration = max(
                    duration, result.target.physical_effects["Bleed"].duration
                )
                result.target.physical_effects["Bleed"].extra = max(
                    bleed_dmg, result.target.physical_effects["Bleed"].extra
                )
        return results


class Excalibur2(Excalibur):
    """Upgraded Excalibur bestowed by the Lady of the Lake."""

    def __init__(self):
        super().__init__()
        self.description = "\n".join(
            wrap(
                "An upgraded version of the legendary sword of King Arthur, bestowed upon "
                "him by the Lady of the Lake.",
                35,
                break_on_hyphens=False,
            )
        )


class Mace(Weapon):

    def __init__(self):
        super().__init__(
            name="Mace",
            description="A mace is a blunt weapon, a type of club or virge that uses a heavy"
            " head on the end of a handle to deliver powerful strikes. A mace "
            "typically consists of a strong, heavy, wooden or metal shaft, often"
            " reinforced with metal, featuring a head made of iron.",
            value=2000,
            rarity=0.85,
            damage=18,
            crit=0.05,
            handed=1,
            subtyp="Club",
            unequip=False,
            off=True,
        )
        self.weight = 6


class WarHammer(Weapon):

    def __init__(self):
        super().__init__(
            name="War Hammer",
            description="A war hammer is a club with a head featuring both a blunt end "
            "and a spike on the other end.",
            value=4500,
            rarity=0.75,
            damage=26,
            crit=0.075,
            handed=1,
            subtyp="Club",
            unequip=False,
            off=True,
        )
        self.weight = 10


class Pernach(Weapon):

    def __init__(self):
        super().__init__(
            name="Pernach",
            description="A pernach is a type of flanged mace used to penetrate even heavy "
            "armor plating.",
            value=18000,
            rarity=0.5,
            damage=36,
            crit=0.1,
            handed=1,
            subtyp="Club",
            unequip=False,
            off=True,
        )
        self.weight = 10


class Morgenstern(Weapon):

    def __init__(self):
        super().__init__(
            name="Morgenstern",
            description="A morgenstern, or morning star, is a club-like weapon "
            "consisting of a shaft with an attached ball adorned with "
            "several spikes.",
            value=43500,
            rarity=0.4,
            damage=48,
            crit=0.15,
            handed=1,
            subtyp="Club",
            unequip=False,
            off=True,
        )
        self.weight = 10


class Shishpar(Weapon):

    def __init__(self):
        super().__init__(
            name="Shishpar",
            description="A shishpar is a heavy, spiked mace traditionally used "
            " to crush armor and bone in combat. Its distinctive feature is "
            "the large head adorned with several protruding flanges or "
            "spikes, designed to maximize the impact force while easily "
            "breaking through defenses.",
            value=85000,
            rarity=0.2,
            damage=62,
            crit=0.2,
            handed=1,
            subtyp="Club",
            unequip=False,
            off=True,
        )
        self.weight = 9


class Mjolnir(Weapon):
    """
    Ultimate weapon; chance to stun on a critical hit based on strength
    """

    def __init__(self):
        super().__init__(
            name="Mjolnir",
            description="Mjolnir, wielded by the Thunder god Thor, is depicted in Norse "
            "mythology as one of the most fearsome and powerful weapons in "
            "existence, capable of leveling mountains.",
            value=0,
            rarity=0,
            damage=76,
            crit=0.25,
            handed=1,
            subtyp="Club",
            unequip=False,
            off=True,
        )
        self.weight = 8
        self.ultimate = True

    def special_effect(self, results: CombatResultGroup) -> None:
        result = results[-1]
        if not any(
            [
                "Stun" in result.target.status_immunity,
                "Status-Stun" in result.target.equipment["Pendant"].mod,
                "Status-All" in result.target.equipment["Pendant"].mod,
            ]
        ):
            if not result.target.status_effects["Stun"].active:
                if result.crit > 1:
                    att_roll = random.randint(
                        result.actor.stats.strength // 2, result.actor.stats.strength
                    )
                    def_roll = random.randint(result.target.stats.con // 2, result.target.stats.con)
                    if result.target.stun_contest_success(result.actor, att_roll, def_roll):
                        duration = max(1, result.actor.stats.strength // 10)
                        if result.target.apply_stun(
                            duration, source=self.name, applier=result.actor
                        ):
                            result.effects_applied["Status"].append("Stun")
        return results


class Tanto(Weapon):

    def __init__(self):
        super().__init__(
            name="Tanto",
            description="A tanto is a double-edged, straight blade, designed primarily as a "
            "stabbing weapon, but the edge can be used for slashing as well.",
            value=44000,
            rarity=0.4,
            damage=28,
            crit=0.33,
            handed=1,
            subtyp="Ninja Blade",
            unequip=False,
            off=True,
        )
        self.weight = 5
        self.restriction = ["Ninja"]


class Wakizashi(Weapon):

    def __init__(self):
        super().__init__(
            name="Wakizashi",
            description="A wakizashi is a curved, single-edged blade with a narrow "
            "cross-section, producing a deadly strike.",
            value=87000,
            rarity=0.2,
            damage=38,
            crit=0.4,
            handed=1,
            subtyp="Ninja Blade",
            unequip=False,
            off=True,
        )
        self.weight = 7
        self.restriction = ["Ninja"]


class Ninjato(Weapon):
    """
    Ultimate weapon; chance on crit to kill target
    """

    def __init__(self):
        super().__init__(
            name="Ninjato",
            description="A mythical blade used by ninjas said to be possessed by a demon "
            "who steals the soul of those slain by the weapon.",
            value=0,
            rarity=0,
            damage=50,
            crit=0.5,
            handed=1,
            subtyp="Ninja Blade",
            unequip=False,
            off=True,
        )
        self.weight = 5
        self.restriction = ["Ninja"]
        self.ultimate = True

    def special_effect(self, results: CombatResultGroup) -> None:
        result = results[-1]
        if result.crit > 1:
            if "Death" not in result.target.status_immunity:
                w_chance = result.actor.check_mod("luck", enemy=result.target, luck_factor=10)
                t_chance = result.target.check_mod("luck", enemy=result.actor, luck_factor=10)
                if (
                    random.randint(0, result.actor.check_mod("speed", enemy=result.target))
                    + w_chance
                    > random.randint(result.target.stats.con // 2, result.target.stats.con)
                    + t_chance
                ):
                    result.extra["Instant Death"] = True
        return results


class Bastard(Weapon):

    def __init__(self):
        super().__init__(
            name="Bastard Sword",
            description="The bastard sword, also referred to as a hand-and-a-half "
            "sword, is a type of longsword that typically requires two "
            "hands to wield but can be wielded in one if the need "
            "arises.",
            value=700,
            rarity=0.9,
            damage=10,
            crit=0.125,
            handed=2,
            subtyp="Longsword",
            unequip=False,
            off=False,
        )
        self.weight = 14


class Claymore(Weapon):

    def __init__(self):
        super().__init__(
            name="Claymore",
            description="The claymore is a two-handed sword featuring quillons "
            "(crossguards between the hilt and the blade) are angled in "
            "towards the blade and end in quatrefoils, and a tongue of metal"
            " protrudes down either side of the blade.",
            value=4200,
            rarity=0.85,
            damage=28,
            crit=0.15,
            handed=2,
            subtyp="Longsword",
            unequip=False,
            off=False,
        )
        self.weight = 20


class Zweihander(Weapon):

    def __init__(self):
        super().__init__(
            name="Zweihander",
            description="German for 'two-handed', the zweihander is a double-edged, "
            "straight blade with a cruciform hilt.",
            value=9500,
            rarity=0.75,
            damage=38,
            crit=0.2,
            handed=2,
            subtyp="Longsword",
            unequip=False,
            off=False,
        )
        self.weight = 18


class Changdao(Weapon):

    def __init__(self):
        super().__init__(
            name="Changdao",
            description="A single-edged two-hander over seven feet long, roughly "
            "translates to 'long saber'.",
            value=28000,
            rarity=0.5,
            damage=50,
            crit=0.25,
            handed=2,
            subtyp="Longsword",
            unequip=False,
            off=False,
        )
        self.weight = 16


class Flamberge(Weapon):
    """
    Fire element
    """

    def __init__(self):
        super().__init__(
            name="Flamberge",
            description="The flamberge is a type of flame-bladed sword featuring a "
            "signature wavy blade.",
            value=61000,
            rarity=0.4,
            damage=62,
            crit=0.33,
            handed=2,
            subtyp="Longsword",
            unequip=False,
            off=False,
        )
        self.weight = 18
        self.element = "Fire"


class Katana(Weapon):

    def __init__(self):
        super().__init__(
            name="Katana",
            description="The katana is a traditional Japanese sword characterized by its "
            "curved, slender, single-edged blade, circular or squared guard, "
            "and long grip suitable for two-handed use. Renowned for its "
            "sharpness, the katana was crafted with exceptional skill, "
            "incorporating a folded steel forging process that produced both "
            "resilience and flexibility.",
            value=100000,
            rarity=0.2,
            damage=78,
            crit=0.4,
            handed=2,
            subtyp="Longsword",
            unequip=False,
            off=False,
        )
        self.weight = 18


class Executioner(Weapon):

    def __init__(self):
        super().__init__(
            name="Executioner's Blade",
            description="Designed specifically for decapitation, the "
            "Executioner's Blade is a large, two-handed sword "
            "with a broad blade that is highly efficient at "
            "killing.",
            value=0,
            rarity=0,
            damage=100,
            crit=0.4,
            handed=2,
            subtyp="Longsword",
            unequip=False,
            off=False,
        )
        self.weight = 20
        self.ultimate = True

    def special_effect(self, results: CombatResultGroup) -> None:
        result = results[-1]
        if result.crit > 1:
            if "Death" not in result.target.status_immunity:
                w_chance = result.actor.check_mod("luck", enemy=result.target, luck_factor=10)
                t_chance = result.target.check_mod("luck", enemy=result.actor, luck_factor=10)
                if (
                    random.randint(0, result.actor.stats.strength) + w_chance
                    > random.randint(result.target.stats.con // 2, result.target.stats.con)
                    + t_chance
                ):
                    result.extra["Instant Death"] = True
        return results


class Mattock(Weapon):

    def __init__(self):
        super().__init__(
            name="Mattock",
            description="A mattock is a hand tool used for digging, prying, and chopping, "
            "similar to the pickaxe.",
            value=800,
            rarity=0.9,
            damage=12,
            crit=0.1,
            handed=2,
            subtyp="Battle Axe",
            unequip=False,
            off=False,
        )
        self.weight = 15


class Broadaxe(Weapon):

    def __init__(self):
        super().__init__(
            name="Broadaxe",
            description="A broadaxe is broad-headed axe with a large flared blade.",
            value=4500,
            rarity=0.85,
            damage=30,
            crit=0.15,
            handed=2,
            subtyp="Battle Axe",
            unequip=False,
            off=False,
        )
        self.weight = 17


class DoubleAxe(Weapon):

    def __init__(self):
        super().__init__(
            name="Double Axe",
            description="The double axe is basically a broadaxe but with a blade on "
            "each side of the axehead.",
            value=10000,
            rarity=0.75,
            damage=42,
            crit=0.2,
            handed=2,
            subtyp="Battle Axe",
            unequip=False,
            off=False,
        )
        self.weight = 22


class Parashu(Weapon):

    def __init__(self):
        super().__init__(
            name="Parashu",
            description="A parashu is a single-bladed battle axe with an arced edge "
            "extending beyond 180 degrees and paired with a spike on the non-"
            "cutting edge.",
            value=27500,
            rarity=0.5,
            damage=56,
            crit=0.25,
            handed=2,
            subtyp="Battle Axe",
            unequip=False,
            off=False,
        )
        self.weight = 20


class Greataxe(Weapon):

    def __init__(self):
        super().__init__(
            name="Greataxe",
            description="A greataxe is a scaled up version of the double axe with greater"
            " mass and killing power.",
            value=59000,
            rarity=0.4,
            damage=68,
            crit=0.3,
            handed=2,
            subtyp="Battle Axe",
            unequip=False,
            off=False,
        )
        self.weight = 26


class Tabarzin(Weapon):

    def __init__(self):
        super().__init__(
            name="Tabarzin",
            description="The tabarzin is notable for its single-bladed axe head, "
            "accompanied by a spike on the opposite side. Typically adorned "
            "with intricate carvings or inlays, the tabarzin reflects the "
            "a unique artistry, blending practical lethality with cultural "
            "craftsmanship.",
            value=100000,
            rarity=0.2,
            damage=86,
            crit=0.33,
            handed=2,
            subtyp="Battle Axe",
            unequip=False,
            off=False,
        )
        self.weight = 24


class Jarnbjorn(Weapon):
    """
    Ultimate weapon; chance on critical hit to cause bleed
    """

    def __init__(self):
        super().__init__(
            name="Jarnbjorn",
            description='Legendary axe of Thor Odinson. Old Norse for "iron bear".',
            value=0,
            rarity=0,
            damage=110,
            crit=0.33,
            handed=2,
            subtyp="Battle Axe",
            unequip=False,
            off=False,
        )
        self.weight = 20
        self.ultimate = True

    def special_effect(self, results: CombatResultGroup) -> None:
        result = results[-1]
        if result.crit > 1:
            if random.randint(
                (result.actor.stats.strength // 2), result.actor.stats.strength
            ) > random.randint(result.target.stats.con // 2, result.target.stats.con):
                duration = max(1, result.actor.stats.strength // 10)
                bleed_dmg = max(result.actor.stats.strength // 2, result.damage)
                if not result.target.physical_effects["Bleed"].active:
                    result.target.physical_effects["Bleed"].active = True
                    result.effects_applied["Physical"].append("Bleed")
                else:
                    result.effects_applied["Physical"].append("Bleed+")
                result.target.physical_effects["Bleed"].duration = max(
                    duration, result.target.physical_effects["Bleed"].duration
                )
                result.target.physical_effects["Bleed"].extra = max(
                    bleed_dmg, result.target.physical_effects["Bleed"].extra
                )
        return results


class Framea(Weapon):

    def __init__(self):
        super().__init__(
            name="Framea",
            description="A type of spear used by the ancient Germanic tribes and is a "
            "versatile weapon used in both melee combat and as a projectile.",
            value=800,
            rarity=0.9,
            damage=10,
            crit=0.15,
            handed=2,
            subtyp="Polearm",
            unequip=False,
            off=False,
        )
        self.weight = 10


class Partisan(Weapon):

    def __init__(self):
        super().__init__(
            name="Partisan",
            description="A partisan consists of a spearhead mounted on a long wooden "
            "shaft, with protrusions on the sides which aid in parrying "
            "sword thrusts.",
            value=3500,
            rarity=0.85,
            damage=26,
            crit=0.2,
            handed=2,
            subtyp="Polearm",
            unequip=False,
            off=False,
        )
        self.weight = 12


class Halberd(Weapon):

    def __init__(self):
        super().__init__(
            name="Halberd",
            description="A halberd is a two-handed pole weapon consisting of an axe blade "
            "topped with a spike mounted on a long shaft.",
            value=9000,
            rarity=0.75,
            damage=36,
            crit=0.25,
            handed=2,
            subtyp="Polearm",
            unequip=False,
            off=False,
        )
        self.weight = 15


class Naginata(Weapon):

    def __init__(self):
        super().__init__(
            name="Naginata",
            description="A naginata consists of a wooden or metal pole with a curved "
            "single-edged blade on the end that has a round handguard between"
            " the blade and shaft.",
            value=26500,
            rarity=0.5,
            damage=50,
            crit=0.3,
            handed=2,
            subtyp="Polearm",
            unequip=False,
            off=False,
        )
        self.weight = 14


class Trident(Weapon):
    """
    Water element
    """

    def __init__(self):
        super().__init__(
            name="Trident",
            description="A trident is a 3-pronged spear, the preferred weapon of the Sea"
            " god Poseidon.",
            value=57000,
            rarity=0.4,
            damage=62,
            crit=0.33,
            handed=2,
            subtyp="Polearm",
            unequip=False,
            off=False,
        )
        self.weight = 16
        self.element = "Water"


class Ranseur(Weapon):

    def __init__(self):
        super().__init__(
            name="Ranseur",
            description="A ranseur is a polearm characterized by a central spearhead "
            "flanked by two outward-curving prongs, giving it a trident-like "
            "appearance. Its primary purpose was to parry or entangle an "
            "opponent's weapon while still maintaining the thrusting "
            "capability of a spear.",
            value=95000,
            rarity=0.2,
            damage=76,
            crit=0.35,
            handed=2,
            subtyp="Polearm",
            unequip=False,
            off=False,
        )
        self.weight = 15

    def special_effect(self, results: CombatResultGroup) -> None:
        result = results[-1]
        if not result.target.physical_effects["Disarm"].active:
            if result.target.can_be_disarmed():
                chance = result.target.check_mod("luck", enemy=result.actor, luck_factor=10)
                if (
                    random.randint(result.actor.stats.strength // 2, result.actor.stats.strength)
                    > random.randint(
                        result.target.check_mod("speed", enemy=result.actor) // 2,
                        result.target.check_mod("speed", enemy=result.actor),
                    )
                    + chance
                ):
                    result.target.physical_effects["Disarm"].active = True
                    result.target.physical_effects["Disarm"].duration = (
                        result.actor.stats.strength // 10
                    )
                    result.effects_applied["Physical"].append("Disarm")
        return results


class Gungnir(Weapon):
    """
    Ultimate weapon; ignores armor
    """

    def __init__(self):
        super().__init__(
            name="Gungnir",
            description='Legendary spear of the god Odin. Old Norse for "swaying one".',
            value=0,
            rarity=0,
            damage=96,
            crit=0.4,
            handed=2,
            subtyp="Polearm",
            unequip=False,
            off=False,
        )
        self.weight = 14
        self.ignore = True
        self.ultimate = True


class Quarterstaff(Weapon):

    def __init__(self):
        super().__init__(
            name="Quarterstaff",
            description="A quarterstaff is a shaft of hardwood about eight feet long"
            " fitted with metal tips on each end.",
            value=250,
            rarity=0.95,
            damage=4,
            crit=0.025,
            handed=2,
            subtyp="Staff",
            unequip=False,
            off=False,
        )
        self.weight = 6


class Baston(Weapon):

    def __init__(self):
        super().__init__(
            name="Baston",
            description="A baston is a long, light, and flexible staff weapon that is ideal"
            " for speed and precision.",
            value=800,
            rarity=0.9,
            damage=8,
            crit=0.05,
            handed=2,
            subtyp="Staff",
            unequip=False,
            off=False,
        )
        self.weight = 6


class IronshodStaff(Weapon):

    def __init__(self):
        super().__init__(
            name="Ironshod Staff",
            description="An iron walking stick, making it ideal for striking.",
            value=4000,
            rarity=0.85,
            damage=18,
            crit=0.1,
            handed=2,
            subtyp="Staff",
            unequip=False,
            off=False,
        )
        self.weight = 10


class SerpentStaff(Weapon):

    def __init__(self):
        super().__init__(
            name="Serpent Staff",
            description="A magic staff, shaped to appear as a snake.",
            value=8000,
            rarity=0.75,
            damage=26,
            crit=0.12,
            handed=2,
            subtyp="Staff",
            unequip=False,
            off=False,
        )
        self.weight = 8


class HolyStaff(Weapon):

    def __init__(self):
        super().__init__(
            name="Holy Staff",
            description="A staff that emits a holy light. Only equipable by priests"
            " and archbishops.",
            value=25000,
            rarity=0.5,
            damage=30,
            crit=0.15,
            handed=2,
            subtyp="Staff",
            unequip=False,
            off=False,
        )
        self.weight = 6
        self.restriction = ["Priest", "Archbishop"]
        self.element = "Holy"

    def special_effect(self, results: CombatResultGroup) -> None:
        result = results[-1]
        t_chance = result.target.check_mod("luck", enemy=result.target, luck_factor=5) / 100
        if 0.05 + t_chance > random.random():  # 5% chance plus charisma // 5
            heal = min(result.actor.health.max - result.actor.health.current, result.damage)
            result.actor.health.current += heal
            result.healing += heal
        return results


class RuneStaff(Weapon):

    def __init__(self):
        super().__init__(
            name="Rune Staff",
            description="A wooden staff with a magical rune embedded in the handle.",
            value=27500,
            rarity=0.5,
            damage=36,
            crit=0.18,
            handed=2,
            subtyp="Staff",
            unequip=False,
            off=False,
        )
        self.weight = 7


class MithrilshodStaff(Weapon):

    def __init__(self):
        super().__init__(
            name="Mithrilshod Staff",
            description="A mithril walking stick, making it ideal for striking.",
            value=65000,
            rarity=0.4,
            damage=44,
            crit=0.2,
            handed=2,
            subtyp="Staff",
            unequip=False,
            off=False,
        )
        self.weight = 8


class Khatvanga(Weapon):

    def __init__(self):
        super().__init__(
            name="Khatvanga",
            description="A khatvanga is a ritual staff that consists of a wooden or "
            "metal shaft adorned with a trident or skull, symbolizing its "
            "esoteric nature.",
            value=100000,
            rarity=0.2,
            damage=56,
            crit=0.25,
            handed=2,
            subtyp="Staff",
            unequip=False,
            off=False,
        )
        self.weight = 7


class DragonStaff(Weapon):
    """
    Ultimate weapon; regen mana based on damage
    """

    def __init__(self):
        super().__init__(
            name="Dragon Staff",
            description="A magic staff, shaped to appear as a dragon.",
            value=0,
            rarity=0,
            damage=70,
            crit=0.3,
            handed=2,
            subtyp="Staff",
            unequip=False,
            off=False,
        )
        self.weight = 9
        self.restriction = [
            "Wizard",
            "Necromancer",
            "Master Monk",
            "Lycan",
            "Astromancer",
            "Soulcatcher",
        ]
        self.ultimate = True

    def special_effect(self, results: CombatResultGroup) -> None:
        result = results[-1]
        mana_heal = random.randint(result.damage // 2, result.damage)
        if result.actor.mana.current + mana_heal > result.actor.mana.max:
            mana_heal = result.actor.mana.max - result.actor.mana.current
        if mana_heal > 0:
            result.actor.mana.current += mana_heal
            result.extra["Mana"] = mana_heal
        return results


class PrincessGuard(Weapon):
    """
    Ultimate weapon; regen health based on damage
    """

    def __init__(self):
        super().__init__(
            name="Princess Guard",
            description="A mythical staff from another world.",
            value=0,
            rarity=0,
            damage=74,
            crit=0.25,
            handed=2,
            subtyp="Staff",
            unequip=False,
            off=False,
        )
        self.weight = 4
        self.restriction = ["Archbishop"]
        self.ultimate = True

    def special_effect(self, results: CombatResultGroup) -> None:
        result = results[-1]
        heal = random.randint(result.damage // 2, result.damage)
        if result.actor.health.current + heal > result.actor.health.max:
            heal = result.actor.health.max - result.actor.health.current
        if heal > 0:
            result.actor.mana.current += heal
            result.healing += heal
        return results


class RuyiJinguBang(Weapon):
    """
    Ultimate weapon; Master Monk chi-conduit staff.
    """

    def __init__(self):
        super().__init__(
            name="Ruyi Jingu Bang",
            description=(
                "A legendary iron staff that changes weight with the wielder's "
                "breath and carries chi cleanly through every strike."
            ),
            value=0,
            rarity=0,
            damage=72,
            crit=0.28,
            handed=2,
            subtyp="Staff",
            unequip=False,
            off=False,
        )
        self.weight = 8
        self.restriction = ["Master Monk"]
        self.ultimate = True

    def special_effect(self, results: CombatResultGroup) -> None:
        result = results[-1]
        actor = result.actor
        try:
            from ..classes import promotion_kits

            if promotion_kits.class_name(actor) != "Master Monk":
                return
            state = promotion_kits.combat_state(actor)
            if state.get("action_name") not in {None, "", "Attack"}:
                return
            action_token = int(state.get("action_token", 0) or 0)
            if state.get("ruyi_bonus_action_token") == action_token:
                return
            state["ruyi_bonus_action_token"] = action_token
            cap = promotion_kits.cap_for(actor, "ki")
            if int(state.get("ki", 0) or 0) >= cap:
                return
            if random.random() < 0.35:
                result.message += promotion_kits.gain_meter(actor, "ki", 1, self.name)
        except Exception:
            return


class Sledgehammer(Weapon):

    def __init__(self):
        super().__init__(
            name="Sledgehammer",
            description="A sledgehammer is a tool with a large, flat, metal head, "
            "attached to a long handle that gathers momentum during a "
            "swing to apply a large force upon the target.",
            value=800,
            rarity=0.9,
            damage=14,
            crit=0.075,
            handed=2,
            subtyp="Hammer",
            unequip=False,
            off=False,
        )
        self.weight = 20


class SpikeMaul(Weapon):

    def __init__(self):
        super().__init__(
            name="Spike Maul",
            description="A spike maul is similar to a sledgehammer except for having a"
            " more narrow face for increased damage.",
            value=7500,
            rarity=0.75,
            damage=36,
            crit=0.12,
            handed=2,
            subtyp="Hammer",
            unequip=False,
            off=False,
        )
        self.weight = 22


class EarthHammer(Weapon):

    def __init__(self):
        super().__init__(
            name="Earth Hammer",
            description="A large, 2-handed hammer infused with the power of Gaia.",
            value=29000,
            rarity=0.5,
            damage=50,
            crit=0.15,
            handed=2,
            subtyp="Hammer",
            unequip=False,
            off=False,
        )
        self.weight = 20
        self.element = "Earth"


class GreatMaul(Weapon):

    def __init__(self):
        super().__init__(
            name="Great Maul",
            description="A great maul looks similar to a sledgehammer but is "
            "significantly larger in all aspects.",
            value=60000,
            rarity=0.4,
            damage=72,
            crit=0.2,
            handed=2,
            subtyp="Hammer",
            unequip=False,
            off=False,
        )
        self.weight = 30


class Streithammer(Weapon):

    def __init__(self):
        super().__init__(
            name="Streithammer",
            description="The streithammer is a fearsome, two-handed war hammer "
            "designed for battle, particularly against heavily armored "
            "foes. Its solid steel head features a broad, flat face for "
            "crushing blows and a sharp, opposing spike for piercing "
            "armor or breaking shields.",
            value=98000,
            rarity=0.2,
            damage=94,
            crit=0.25,
            handed=2,
            subtyp="Hammer",
            unequip=False,
            off=False,
        )
        self.weight = 26


class Skullcrusher(Weapon):
    """
    Ultimate weapon; chance to stun on critical based on strength
    """

    def __init__(self):
        super().__init__(
            name="Skullcrusher",
            description="A massive hammer with the power to pulverize an enemy's "
            "skull to powder.",
            value=0,
            rarity=0,
            damage=120,
            crit=0.25,
            handed=2,
            subtyp="Hammer",
            unequip=False,
            off=False,
        )
        self.weight = 25
        self.ultimate = True

    def special_effect(self, results: CombatResultGroup) -> None:
        result = results[-1]
        if not any(
            [
                "Stun" in result.target.status_immunity,
                "Status-Stun" in result.target.equipment["Pendant"].mod,
                "Status-All" in result.target.equipment["Pendant"].mod,
            ]
        ):
            if not result.target.status_effects["Stun"].active:
                if result.crit > 1:
                    att_roll = random.randint(
                        result.actor.stats.strength // 2, result.actor.stats.strength
                    )
                    def_roll = random.randint(result.target.stats.con // 2, result.target.stats.con)
                    if result.target.stun_contest_success(result.actor, att_roll, def_roll):
                        duration = max(1, result.actor.stats.strength // 10)
                        if result.target.apply_stun(
                            duration, source=self.name, applier=result.actor
                        ):
                            result.effects_applied["Status"].append("Stun")
        return results


class GiantClub(Weapon):
    """
    Summon Patagon weapon
    """

    def __init__(self):
        super().__init__(
            name="Giant's Club",
            description="A massive club wielded by Patagon, the giant summon " "creature.",
            value=0,
            rarity=0,
            damage=50,
            crit=0.1,
            handed=2,
            subtyp="Summon",
            unequip=False,
            off=False,
        )


class EarthMaw(NaturalWeapon):
    """
    Summon Dilong weapon
    """

    def __init__(self):
        super().__init__(name="Earth Maw", damage=60, crit=0.2, description="", off=False)
        self.att_name = "bites"
        self.element = "Earth"

    def special_effect(self, results: CombatResultGroup) -> None:
        result = results[-1]
        if result.crit > 1:
            abilities.Sandstorm().cast(result.actor, result.target, special=True)
        return results


class IceShard(NaturalWeapon):
    """
    Summon Agloolik weapon
    """

    def __init__(self):
        super().__init__(name="Ice Shard", damage=30, crit=0.33, description="", off=False)
        self.att_name = "throws ice shards at"
        self.element = "Ice"

    def special_effect(self, results: CombatResultGroup) -> None:
        result = results[-1]
        shards = random.randint(0, result.actor.intel // 8) * round(1 + result.crit)
        if "Shards" not in result.extra:
            result.extra["Shards"] = shards
        else:
            result.extra["Shards"] += shards
        for _ in range(shards):
            result.damage += int(random.randint(1, result.actor.intel) * random.uniform(-1, 1))
        return results


class VulcansHammer(Weapon):
    """
    Summon Cacus weapon
    """

    def __init__(self):
        super().__init__(
            name="Vulcan's Hammer",
            description="A blacksmith's hammer that allegedly belonged to the fire god Vulcan.",
            value=0,
            rarity=0,
            damage=45,
            crit=0.25,
            handed=2,
            subtyp="Summon",
            unequip=False,
            off=False,
        )


class Scythe(Weapon):
    """
    Summon Bardi weapon
    """

    def __init__(self):
        super().__init__(
            name="Scythe",
            description="",
            value=0,
            rarity=0,
            damage=80,
            crit=0.3,
            handed=2,
            subtyp="Summon",
            unequip=False,
            off=False,
        )

    def special_effect(self, results: CombatResultGroup) -> None:
        result = results[-1]
        if result.crit > 1:
            result = abilities.Desoul(result, special=True)
        return results


class KoboldDagger(Weapon):
    """
    Used by the Kobalos Summon; has random affect on crit  TODO
    """

    def __init__(self):
        super().__init__(
            name="Kobold Dagger",
            description="",
            value=0,
            rarity=0,
            damage=50,
            crit=0.4,
            handed=1,
            subtyp="Summon",
            unequip=False,
            off=False,
        )

    def special_effect(self, results: CombatResultGroup) -> None:
        result = results[-1]
        if result.crit > 1:
            pass
        return results


class Bite(NaturalWeapon):

    def __init__(self):
        super().__init__(name="Bite", damage=6, crit=0.05, description="", off=False)
        self.special = True
        self.att_name = "bites"

    def special_effect(self, results: CombatResultGroup) -> None:
        result = results[-1]
        if self.crit > random.random():
            result.extra["Disease"] = False
            if not random.randint(0, 39 // result.crit):
                result.target.stats.con -= 1
                result.extra["Disease"] = True
                result.effects_applied["Stat"].append("Constitution Down")
                result.message += (
                    f"{result.target.name} contracts a disease! Constitution is reduced by 1.\n"
                )
        return results


class Bite2(Bite):

    def __init__(self):
        super().__init__()
        self.damage = 30
        self.crit = 0.2

    def special_effect(self, results: CombatResultGroup) -> None:
        result = results[-1]
        if self.crit > random.random():
            result.extra["Disease"] = False
            if not random.randint(0, 19 // result.crit):
                result.extra["Disease"] = True
                result.target.stats.con -= 1
                result.effects_applied["Stat"].append("Constitution Down")
                result.message += (
                    f"{result.target.name} contracts a disease! Constitution is reduced by 1.\n"
                )
        return results


class VampireBite(Bite):

    def __init__(self):
        super().__init__()
        self.damage = 20
        self.crit = 0.15

    def special_effect(self, results: CombatResultGroup) -> None:
        result = results[-1]
        if self.crit > random.random():
            result.actor.health.current += result.damage
            result.actor.health.current = min(result.actor.health.current, result.actor.health.max)
            result.extra["Drain"] = True
        return results


class Claw(NaturalWeapon):

    def __init__(self):
        super().__init__(name="Claw", damage=8, crit=0.2, description="", off=True)
        self.att_name = "swipes"


class Claw2(Claw):

    def __init__(self):
        super().__init__()
        self.damage = 20
        self.crit = 0.25


class Claw3(Claw):

    def __init__(self):
        super().__init__()
        self.special = True
        self.damage = 36
        self.crit = 0.33

    def special_effect(self, results: CombatResultGroup) -> None:
        result = results[-1]
        resist = result.target.check_mod("resist", enemy=result.actor, typ="Physical")
        if resist < 1:
            if random.randint(
                (result.actor.check_mod("speed", enemy=result.target) // 2) * result.crit,
                result.actor.check_mod("speed", enemy=result.target) * result.crit,
            ) > random.randint(result.target.stats.con // 2, result.target.stats.con):
                if not result.target.physical_effects["Bleed"].active:
                    result.target.physical_effects["Bleed"].active = True
                    result.effects_applied["Physical"].append("Bleed")
                else:
                    result.effects_applied["Physical"].append("Bleed+")
                duration = max(1, result.actor.check_mod("speed", enemy=result.target) // 10)
                bleed_dmg = int(
                    max(result.actor.check_mod("speed", enemy=result.target) // 2, result.damage)
                    * (1 - resist)
                )
                bleed_dmg = max(1, int(random.randint(bleed_dmg // 4, bleed_dmg) * 0.75))
                result.target.physical_effects["Bleed"] = StatusEffect(
                    True,
                    max(duration, result.target.physical_effects["Bleed"].duration),
                    max(bleed_dmg, result.target.physical_effects["Bleed"].extra),
                )
        return results


class BearClaw(NaturalWeapon):

    def __init__(self):
        super().__init__(name="Bear Claw", damage=24, crit=0.2, description="", off=True)
        self.special = True
        self.att_name = "mauls"

    def special_effect(self, results: CombatResultGroup) -> None:
        result = results[-1]
        resist = result.target.check_mod("resist", enemy=result.actor, typ="Physical")
        if resist < 1:
            if random.randint(
                (result.actor.stats.strength // 2) * result.crit,
                result.actor.stats.strength * result.crit,
            ) > random.randint(result.target.stats.con // 2, result.target.stats.con):
                if not result.target.physical_effects["Bleed"].active:
                    result.target.physical_effects["Bleed"].active = True
                    result.effects_applied["Physical"].append("Bleed")
                else:
                    result.effects_applied["Physical"].append("Bleed+")
                duration = max(1, result.actor.stats.strength // 10)
                bleed_dmg = int(max(result.actor.stats.strength // 2, result.damage) * (1 - resist))
                bleed_dmg = max(1, int(random.randint(bleed_dmg // 4, bleed_dmg) * 0.75))
                result.target.physical_effects["Bleed"] = StatusEffect(
                    True,
                    max(duration, result.target.physical_effects["Bleed"].duration),
                    max(bleed_dmg, result.target.physical_effects["Bleed"].extra),
                )
        return results


class Stinger(NaturalWeapon):

    def __init__(self):
        super().__init__(name="Stinger", damage=10, crit=0.25, description="", off=False)
        self.special = True
        self.att_name = "stings"

    def special_effect(self, results: CombatResultGroup) -> None:
        result = results[-1]
        resist = result.target.check_mod("resist", enemy=result.actor, typ="Poison")
        if resist < 1 and not any(
            [
                "Status-Poison" in result.target.status_immunity,
                "Status-All" in result.target.status_immunity,
            ]
        ):
            if random.randint(
                (result.actor.check_mod("speed", enemy=result.target) * result.crit) // 2,
                (result.actor.check_mod("speed", enemy=result.target) * result.crit),
            ) > random.randint(result.target.stats.con // 2, result.target.stats.con):
                if not result.target.status_effects["Poison"].active:
                    result.target.status_effects["Poison"].active = True
                    result.effects_applied["Status"].append("Poison")
                else:
                    result.effects_applied["Status"].append("Poison+")
                duration = max(1, result.actor.check_mod("speed", enemy=result.target) // 10)
                damage = int(result.target.health.max * 0.01)
                pois_dmg = max(1, int(damage * (1 - resist)))
                result.target.status_effects["Poison"] = StatusEffect(
                    True,
                    max(duration, result.target.status_effects["Poison"].duration),
                    max(pois_dmg, result.target.status_effects["Poison"].extra),
                )
        return results


class Pincers(NaturalWeapon):

    def __init__(self):
        super().__init__(name="Pincers", damage=8, crit=0.15, description="", off=True)
        self.special = True
        self.att_name = "bites"

    def special_effect(self, results: CombatResultGroup) -> None:
        result = results[-1]
        if not result.hit or not result.damage:
            return results
        if random.randint(
            result.actor.check_mod("speed", enemy=result.target) // 2,
            result.actor.check_mod("speed", enemy=result.target),
        ) > random.randint(result.target.stats.con // 2, result.target.stats.con):
            resist = result.target.check_mod("resist", enemy=result.actor, typ="Poison")
            if resist < 1 and not any(
                [
                    "Status-Poison" in result.target.status_immunity,
                    "Status-All" in result.target.status_immunity,
                ]
            ):
                if not result.target.status_effects["Poison"].active:
                    result.target.status_effects["Poison"].active = True
                    result.effects_applied["Status"].append("Poison")
                else:
                    result.effects_applied["Status"].append("Poison+")
                duration = max(1, result.actor.check_mod("speed", enemy=result.target) // 10)
                damage = int(result.target.health.max * 0.01)
                pois_dmg = max(1, int(damage * (1 - resist)))
                result.target.status_effects["Poison"] = StatusEffect(
                    True,
                    max(duration, result.target.status_effects["Poison"].duration),
                    max(pois_dmg, result.target.status_effects["Poison"].extra),
                )
            if not any(
                [
                    "Stun" in result.target.status_immunity,
                    "Status-Stun" in result.target.equipment["Pendant"].mod,
                    "Status-All" in result.target.equipment["Pendant"].mod,
                ]
            ):
                if not result.target.status_effects["Stun"].active:
                    p_resist = result.target.check_mod("resist", enemy=result.actor, typ="Physical")
                    if result.crit > 1:
                        att_roll = int(
                            random.randint(
                                result.actor.stats.strength // 2, result.actor.stats.strength
                            )
                            * (1 - p_resist)
                        )
                        def_roll = random.randint(
                            result.target.stats.con // 2, result.target.stats.con
                        )
                        if result.target.stun_contest_success(result.actor, att_roll, def_roll):
                            s_duration = max(1, result.actor.stats.strength // 10)
                            if result.target.apply_stun(
                                s_duration, source=self.name, applier=result.actor
                            ):
                                result.effects_applied["Status"].append("Stun")
        return results


class Pincers2(Pincers):

    def __init__(self):
        super().__init__()
        self.damage = 12
        self.crit = 0.2


class DemonClaw(NaturalWeapon):

    def __init__(self):
        super().__init__(name="Demon Claw", damage=10, crit=0.25, description="", off=True)
        self.special = True
        self.att_name = "claws"

    def special_effect(self, results: CombatResultGroup) -> None:
        # Extract caster and target from combat results
        if results.results:
            caster = results.results[0].actor
            target = results.results[0].target
            if caster and target:
                doom_message = abilities.Doom().cast(caster, target, special=True)
                if doom_message:
                    results.results[0].message += str(doom_message)
        return results


class DemonClaw2(DemonClaw):

    def __init__(self):
        super().__init__()
        self.damage = 30
        self.crit = 0.33
        self.special = True

    def special_effect(self, results: CombatResultGroup) -> None:
        if results.results:
            caster = results.results[0].actor
            target = results.results[0].target
            if caster and target:
                abilities.Desoul().cast(caster, target, special=True)
        return results


class SnakeFang(NaturalWeapon):

    def __init__(self):
        super().__init__(name="Snake Fang", damage=10, crit=0.25, description="", off=False)
        self.special = True
        self.att_name = "strikes"

    def special_effect(self, results: CombatResultGroup) -> None:
        result = results[-1]
        resist = result.target.check_mod("resist", enemy=result.actor, typ="Poison")
        if resist < 1 and not any(
            [
                "Status-Poison" in result.target.status_immunity,
                "Status-All" in result.target.status_immunity,
            ]
        ):
            if random.randint(
                (result.actor.check_mod("speed", enemy=result.target) * result.crit) // 2,
                (result.actor.check_mod("speed", enemy=result.target) * result.crit),
            ) > random.randint(result.target.stats.con // 2, result.target.stats.con):
                if not result.target.status_effects["Poison"].active:
                    result.target.status_effects["Poison"].active = True
                    result.effects_applied["Status"].append("Poison")
                else:
                    result.effects_applied["Status"].append("Poison+")
                duration = max(1, result.actor.check_mod("speed", enemy=result.target) // 10)
                damage = int(result.target.health.max * 0.005)
                pois_dmg = max(1, int(damage * (1 - resist)))
                result.target.status_effects["Poison"] = StatusEffect(
                    True,
                    max(duration, result.target.status_effects["Poison"].duration),
                    max(pois_dmg, result.target.status_effects["Poison"].extra),
                )
        return results


class SnakeFang2(SnakeFang):

    def __init__(self):
        super().__init__()
        self.damage = 32
        self.crit = 0.33


class AlligatorTail(NaturalWeapon):

    def __init__(self):
        super().__init__(name="Alligator Tail", damage=24, crit=0.1, description="", off=False)
        self.special = True
        self.att_name = "swipes"

    def special_effect(self, results: CombatResultGroup) -> None:
        result = results[-1]
        if not any(
            [
                "Stun" in result.target.status_immunity,
                "Status-Stun" in result.target.equipment["Pendant"].mod,
                "Status-All" in result.target.equipment["Pendant"].mod,
            ]
        ):
            if not result.target.status_effects["Stun"].active:
                resist = result.target.check_mod("resist", enemy=result.actor, typ="Physical")
                if resist < 1:
                    if result.crit > 1:
                        att_roll = int(
                            random.randint(
                                result.actor.stats.strength // 2, result.actor.stats.strength
                            )
                            * (1 - resist)
                        )
                        def_roll = random.randint(
                            result.target.stats.con // 2, result.target.stats.con
                        )
                        if result.target.stun_contest_success(result.actor, att_roll, def_roll):
                            duration = max(1, result.actor.stats.strength // 10)
                            if result.target.apply_stun(
                                duration, source=self.name, applier=result.actor
                            ):
                                result.effects_applied["Status"].append("Stun")
        return results


class LionPaw(NaturalWeapon):
    """
    Chance to berserk enemy
    """

    def __init__(self):
        super().__init__(name="Lion Paw", damage=34, crit=0.15, description="", off=True)
        self.att_name = "swipes"

    def special_effect(self, results: CombatResultGroup) -> None:
        result = results[-1]
        if not any(
            [
                "Berserk" in result.target.status_immunity,
                "Status-Berserk" in result.target.equipment["Pendant"].mod,
                "Status-All" in result.target.equipment["Pendant"].mod,
            ]
        ):
            if not result.target.status_effects["Berserk"].active:
                if result.crit > 1:
                    if random.randint(0, result.actor.stats.strength) > random.randint(
                        result.target.stats.con // 2, result.target.stats.con
                    ):
                        duration = max(3, result.actor.stats.strength // 10)
                        result.target.status_effects["Berserk"] = StatusEffect(True, duration)
                        result.effects_applied["Status"].append("Berserk")
        return results


class Laser(NaturalWeapon):
    """
    ignores armor
    """

    def __init__(self):
        super().__init__(name="Laser", damage=40, crit=0.25, description="", off=True)
        self.ignore = True
        self.att_name = "zaps"


class Laser2(Laser):
    """
    Chance on crit to permanently damage the enemy, reducing a random stat by 1
    """

    def __init__(self):
        super().__init__()
        self.damage = 70
        self.crit = 0.4
        self.special = True

    def special_effect(self, results: CombatResultGroup) -> None:
        result = results[-1]
        # Luck should reduce proc chance, but it shouldn't fully shut off the effect.
        # Cap the luck term so the threshold never reaches/exceeds 1.0 (which would disable procs).
        t_chance = min(
            0.015, result.target.check_mod("luck", enemy=result.actor, luck_factor=20) / 100
        )
        if result.crit > 1:
            # Balance tuning: permanent primary-stat damage is swingy and can
            # be punishing in long runs. Convert to a temporary combat-stat
            # debuff that matters immediately, with a lower proc chance.
            #
            # Proc chance ~ 2% on crit at low-CHA targets, reduced by luck.
            if random.random() > 0.98 + t_chance:
                stat_list = ["Attack", "Defense", "Magic", "Magic Defense", "Speed"]
                stat_name = random.choice(stat_list)
                eff = result.target.stat_effects.get(stat_name)
                if eff is not None:
                    duration = 5
                    amount = 10
                    eff.active = True
                    eff.duration = max(duration, eff.duration)
                    # Negative extra applies as a debuff in check_mod().
                    eff.extra = (
                        min(int(getattr(eff, "extra", 0) or 0), -amount)
                        if eff.extra < 0
                        else -amount
                    )
                    result.effects_applied["Stat"].append(f"{stat_name} Down")
        return results


class Gaze(NaturalWeapon):
    """
    Attempts to turn the player_char to stone
    """

    def __init__(self):
        super().__init__(name="Gaze", damage=0, crit=0, description="", off=False)
        self.special = True
        self.att_name = "leers"

    def special_effect(self, results: CombatResultGroup) -> None:
        result = results.results[-1]
        result.extra[self.att_name] = True
        # Cast Petrify with proper actor and target from the combat result
        abilities.Petrify().cast(result.actor, result.target, special=True)
        return results


class DragonClaw(NaturalWeapon):
    """
    ignores armor
    """

    def __init__(self):
        super().__init__(name="Dragon Claw", damage=28, crit=0.2, description="", off=True)
        self.ignore = True
        self.att_name = "rakes"


class DragonClaw2(DragonClaw):

    def __init__(self):
        super().__init__()
        self.damage = 70
        self.crit = 0.33
        self.special = True

    def special_effect(self, results: CombatResultGroup) -> None:
        result = results[-1]
        resist = result.target.check_mod("resist", enemy=result.actor, typ="Physical")
        if resist < 1:
            if random.randint(0, result.actor.stats.strength * result.crit) > random.randint(
                result.target.stats.con // 2, result.target.stats.con
            ):
                if not result.target.physical_effects["Bleed"].active:
                    result.target.physical_effects["Bleed"].active = True
                    result.effects_applied["Physical"].append("Bleed")
                else:
                    result.effects_applied["Physical"].append("Bleed+")
                duration = max(1, result.actor.stats.strength // 10)
                bleed_dmg = int(max(result.actor.stats.strength // 2, result.damage) * (1 - resist))
                bleed_dmg = max(1, int(random.randint(bleed_dmg // 4, bleed_dmg) * 0.75))
                result.target.physical_effects["Bleed"] = StatusEffect(
                    True,
                    max(duration, result.target.physical_effects["Bleed"].duration),
                    max(bleed_dmg, result.target.physical_effects["Bleed"].extra),
                )
        return results


class DragonTail(NaturalWeapon):

    def __init__(self):
        super().__init__(name="Dragon Tail", damage=40, crit=0.15, description="", off=True)
        self.att_name = "swipes"


class DragonTail2(DragonTail):

    def __init__(self):
        super().__init__()
        self.damage = 90
        self.crit = 0.3
        self.special = True

    def special_effect(self, results: CombatResultGroup) -> None:
        result = results[-1]
        if not any(
            [
                "Stun" in result.target.status_immunity,
                "Status-Stun" in result.target.equipment["Pendant"].mod,
                "Status-All" in result.target.equipment["Pendant"].mod,
            ]
        ):
            if not result.target.status_effects["Stun"].active:
                resist = result.target.check_mod("resist", enemy=result.actor, typ="Physical")
                if resist < 1:
                    if result.crit > 1:
                        att_roll = int(
                            random.randint(0, int(result.actor.stats.strength * result.crit))
                            * (1 - resist)
                        )
                        def_roll = random.randint(
                            result.target.stats.con // 2, result.target.stats.con
                        )
                        if result.target.stun_contest_success(result.actor, att_roll, def_roll):
                            duration = max(1, result.actor.stats.strength // 10)
                            if result.target.apply_stun(
                                duration, source=self.name, applier=result.actor
                            ):
                                result.effects_applied["Status"].append("Stun")
        return results


class NightmareHoof(NaturalWeapon):
    """
    Natural weapon of Nightmare; additional fire damage
    """

    def __init__(self):
        super().__init__(name="Nightmare Hoof", damage=26, crit=0.25, description="", off=True)
        self.special = True
        self.att_name = "attacks"
        self.element = "Fire"

    def special_effect(self, results: CombatResultGroup) -> None:
        result = results[-1]
        resist = result.target.check_mod("resist", enemy=result.actor, typ=self.element)
        damage = int(
            random.randint(result.actor.stats.intel // 2, result.actor.stats.intel) * (1 - resist)
        )
        result.target.health.current -= damage
        if damage > 0:
            pass
        elif damage < 0:
            result.healing[-1] = abs(damage)
        return results


class UnicornHorn(NaturalWeapon):
    """
    Natural weapon of Unicorn; additional holy damage
    """

    def __init__(self):
        super().__init__(name="Unicorn Horn", damage=28, crit=0.2, description="", off=True)
        self.special = True
        self.att_name = "attacks"
        self.element = "Holy"

    def special_effect(self, results: CombatResultGroup) -> None:
        result = results[-1]
        resist = result.target.check_mod("resist", enemy=result.actor, typ=self.element)
        damage = int(
            random.randint(result.actor.stats.intel // 2, result.actor.stats.intel) * (1 - resist)
        )
        result.target.health.current -= damage
        if damage > 0:
            pass
        elif damage < 0:
            result.healing[-1] = abs(damage)
        return results


class ElementalBlade(NaturalWeapon):
    """
    Innate weapon possessed by Myrmidons; does elemental damage based on the enemy type
    """

    def __init__(self):
        super().__init__(name="Elemental Blade", damage=30, crit=0.25, description="", off=True)
        self.special = True

    def special_effect(self, results: CombatResultGroup) -> None:
        result = results[-1]
        elemental_type = max(result.actor.resistance, key=result.actor.resistance.get)
        resist = result.target.check_mod("resist", enemy=result.actor, typ=elemental_type)
        damage = int(result.damage * (1 - resist))
        if damage < 0:
            result.healing = abs(damage)
        elif damage > 0:
            result.damage += damage
        result.target.health.current -= damage
        if damage > 0 and elemental_type == "Fire" and result.target.is_alive():
            if not result.target.magic_effects["DOT"].active:
                result.target.magic_effects["DOT"].active = True
                result.effects_applied["Magic"].append("Burn")
            result.target.magic_effects["DOT"] = StatusEffect(
                True,
                3,
                max(int(damage // 2), result.target.magic_effects["DOT"].extra),
                "Burn",
            )
        return results


class Tentacle(NaturalWeapon):
    """
    Chance to trip and leave prone
    """

    def __init__(self):
        super().__init__(
            name="Tentacle",
            damage=24,
            crit=0.2,
            description="A slender, flexible limb or appendage in an "
            "animal, especially around the mouth of an "
            "invertebrate, used for grasping or moving "
            "about, or bearing sense organs.",
            off=True,
        )
        self.special = True

    def special_effect(self, results: CombatResultGroup) -> None:
        # Weapon special effects operate on CombatResultGroup; data-driven skills
        # expect (user, target). Apply the effect to the last hit's actor/target
        # and append the generated message.
        result = results[-1]
        try:
            from ..constants import TENTACLE_TRIP_PROC_CHANCE

            if random.random() > float(TENTACLE_TRIP_PROC_CHANCE):
                return results
        except Exception:
            # If the tuning constant can't be loaded, fall back to current behavior.
            pass
        try:
            msg = abilities.Trip().use(result.actor, target=result.target, fam=True)
            if msg:
                result.message += str(msg)
        except Exception:
            pass
        return results


class Tentacle2(Tentacle):
    """
    Chance to stun
    """

    def __init__(self):
        super().__init__()
        self.damage = 48
        self.crit = 0.3
        self.special = True

    def special_effect(self, results: CombatResultGroup) -> None:
        result = results[-1]
        if not any(
            [
                "Stun" in result.target.status_immunity,
                "Status-Stun" in result.target.equipment["Pendant"].mod,
                "Status-All" in result.target.equipment["Pendant"].mod,
            ]
        ):
            if not result.target.status_effects["Stun"].active:
                resist = result.target.check_mod("resist", enemy=result.actor, typ="Physical")
                if resist < 1:
                    if result.crit > 1:
                        att_roll = int(
                            random.randint(
                                result.actor.stats.strength // 2, result.actor.stats.strength
                            )
                            * (1 - resist)
                        )
                        def_roll = random.randint(
                            result.target.stats.con // 2, result.target.stats.con
                        )
                        if result.target.stun_contest_success(result.actor, att_roll, def_roll):
                            duration = max(1, result.actor.stats.strength // 10)
                            result.target.apply_stun(
                                duration, source=self.name, applier=result.actor
                            )
        return results


class InvisibleBlade(NaturalWeapon):
    """
    Shadow element
    Only stuns on crit
    """

    def __init__(self):
        super().__init__(name="Invisible Blade", damage=18, crit=0.25, description="", off=True)
        self.special = True
        self.element = "Shadow"

    def special_effect(self, results: CombatResultGroup) -> None:
        result = results[-1]
        if not any(
            [
                "Stun" in result.target.status_immunity,
                "Status-Stun" in result.target.equipment["Pendant"].mod,
                "Status-All" in result.target.equipment["Pendant"].mod,
            ]
        ):
            if not result.target.status_effects["Stun"].active:
                resist = result.target.check_mod("resist", enemy=result.actor, typ="Physical")
                if resist < 1:
                    if result.crit > 1:
                        spd = result.actor.check_mod("speed", enemy=result.target)
                        att_roll = int(random.randint(0, spd // 2) * (1 - resist))
                        def_roll = random.randint(
                            result.target.stats.con // 2, result.target.stats.con
                        )
                        if result.target.stun_contest_success(result.actor, att_roll, def_roll):
                            duration = 1
                            result.target.apply_stun(
                                duration, source=self.name, applier=result.actor
                            )
        return results


class CerberusClaw(NaturalWeapon):

    def __init__(self):
        super().__init__(name="claws", damage=40, crit=0.25, description="", off=True)
        self.special = True

    def special_effect(self, results: CombatResultGroup) -> None:
        result = results[-1]
        resist = result.target.check_mod("resist", enemy=result.actor, typ="Physical")
        if resist < 1:
            if random.randint(
                (result.actor.stats.strength // 2) * result.crit,
                result.actor.stats.strength * result.crit,
            ) > random.randint(result.target.stats.con // 2, result.target.stats.con):
                if not result.target.physical_effects["Bleed"].active:
                    result.target.physical_effects["Bleed"].active = True
                    result.effects_applied["Physical"].append("Bleed")
                else:
                    result.effects_applied["Physical"].append("Bleed+")
                duration = max(1, result.actor.stats.strength // 10)
                bleed_dmg = int(max(result.actor.stats.strength // 2, result.damage) * (1 - resist))
                bleed_dmg = max(1, int(random.randint(bleed_dmg // 4, bleed_dmg) * 0.75))
                result.target.physical_effects["Bleed"] = StatusEffect(
                    True,
                    max(duration, result.target.physical_effects["Bleed"].duration),
                    max(bleed_dmg, result.target.physical_effects["Bleed"].extra),
                )
        return results


class CerberusBite(NaturalWeapon):

    def __init__(self):
        super().__init__(name="bites", damage=60, crit=0.25, description="", off=False)
        self.special = True
        self.element = "Fire"

    def special_effect(self, results: CombatResultGroup) -> None:
        result = results[-1]
        resist = result.target.check_mod("resist", enemy=result.actor, typ=self.element)
        damage = int(random.randint(result.damage // 2, result.damage) * (1 - resist))
        result.target.health.current -= damage
        if damage > 0:
            result.damage += damage
        elif damage < 0:
            result.healing = abs(damage)
        return results


class LichHand(NaturalWeapon):
    """
    Chance to paralyze (stun) enemy
    """

    def __init__(self):
        super().__init__(name="touches", damage=35, crit=0.2, description="", off=True)
        self.special = True
        self.element = "Ice"

    def special_effect(self, results: CombatResultGroup) -> None:
        result = results[-1]
        if not any(
            [
                "Stun" in result.target.status_immunity,
                "Status-Stun" in result.target.equipment["Pendant"].mod,
                "Status-All" in result.target.equipment["Pendant"].mod,
            ]
        ):
            if not result.target.status_effects["Stun"].active:
                if result.crit > 1:
                    att_roll = random.randint(
                        result.actor.stats.intel // 4, result.actor.stats.intel
                    )
                    def_roll = random.randint(
                        result.target.stats.wisdom // 2, result.target.stats.wisdom
                    )
                    if result.target.stun_contest_success(result.actor, att_roll, def_roll):
                        duration = max(1, result.actor.stats.intel // 10)
                        result.target.apply_stun(duration, source=self.name, applier=result.actor)
        return results


class Cannon(NaturalWeapon):
    """
    Chance to stun the target
    """

    def __init__(self):
        super().__init__(name="attacks", damage=80, crit=0.15, description="", off=True)
        self.special = True

    def special_effect(self, results: CombatResultGroup) -> None:
        result = results[-1]
        if not any(
            [
                "Stun" in result.target.status_immunity,
                "Status-Stun" in result.target.equipment["Pendant"].mod,
                "Status-All" in result.target.equipment["Pendant"].mod,
            ]
        ):
            if not result.target.status_effects["Stun"].active:
                if result.crit > 1:
                    att_roll = random.randint(
                        result.actor.stats.strength // 4, result.actor.stats.strength
                    )
                    def_roll = random.randint(result.target.stats.con // 2, result.target.stats.con)
                    if result.target.stun_contest_success(result.actor, att_roll, def_roll):
                        duration = max(1, result.actor.stats.strength // 10)
                        result.target.apply_stun(duration, source=self.name, applier=result.actor)
        return results


class DevilBlade(NaturalWeapon):
    """
    Chance on crit to apply one of the following status effects: Silence, Stun, Doom, Blind, Sleep, Poison, or Berserk
    """

    def __init__(self):
        super().__init__(name="attacks", damage=100, crit=0.33, description="", off=True)
        self.special = True

    def special_effect(self, results: CombatResultGroup) -> None:
        result = results[-1]
        if not result.hit or not result.damage:
            return results
        w_chance = result.actor.check_mod("luck", enemy=result.target, luck_factor=10)
        t_chance = result.target.check_mod("luck", enemy=result.actor, luck_factor=20)
        if result.crit > 1:
            # Only 25% chance for status effect to apply even on crit
            if random.random() < 0.1:
                if random.randint(0, w_chance) > random.randint(0, t_chance):
                    effect = random.choice(list(result.target.status_effects.keys()))
                    if any(
                        [
                            effect in result.target.status_immunity,
                            f"Status-{effect}" in result.target.equipment["Pendant"].mod,
                            "Status-All" in result.target.equipment["Pendant"].mod,
                        ]
                    ):
                        return results
                    result.target.status_effects[effect] = StatusEffect(
                        True,
                        max(random.randint(1, 5), result.target.status_effects[effect].duration),
                    )
                    if effect == "Poison":
                        damage = int(result.target.health.max * 0.05)
                        result.target.status_effects[
                            "Poison"
                        ].extra += damage  # damage builds over time
        return results
