"""Armor and helmet implementations."""

from __future__ import annotations

from typing import TYPE_CHECKING

from src.core.randomness import gameplay_random as random

from .base import Armor, Helmet

if TYPE_CHECKING:
    from combat import CombatResultGroup


class NoArmor(Armor):

    def __init__(self):
        super().__init__(
            name="No Armor",
            description="No armor equipped.",
            value=0,
            rarity=0,
            armor=0,
            subtyp="None",
            unequip=True,
        )


class NoHelmet(Helmet):

    def __init__(self):
        super().__init__(
            name="No Helmet",
            description="No helmet equipped.",
            value=0,
            rarity=0,
            armor=0,
            subtyp="None",
            unequip=True,
        )


class ClothCap(Helmet):

    def __init__(self):
        super().__init__(
            name="Cloth Cap",
            description="A simple padded cap that offers modest protection without "
            "interfering with spellcasting.",
            value=45,
            rarity=0.95,
            armor=1,
            subtyp="Cloth",
            unequip=False,
        )
        self.weight = 1


class Jaapi(Helmet):

    def __init__(self):
        super().__init__(
            name="Jaapi",
            description="A quilted cloth head wrap that cushions blows while staying light "
            "enough for spellwork.",
            value=180,
            rarity=0.9,
            armor=2,
            subtyp="Cloth",
            unequip=False,
        )
        self.weight = 1


class Turban(Helmet):

    def __init__(self):
        super().__init__(
            name="Turban",
            description="Layered cloth wound into a protective wrap that softens glancing "
            "strikes.",
            value=550,
            rarity=0.8,
            armor=3,
            subtyp="Cloth",
            unequip=False,
        )
        self.weight = 1


class WitchHat(Helmet):

    def __init__(self):
        super().__init__(
            name="Witch Hat",
            description="A tall enchanted hat stiffened with hidden ribs and protective " "wards.",
            value=1600,
            rarity=0.65,
            armor=4,
            subtyp="Cloth",
            unequip=False,
        )
        self.weight = 1


class EnchantedHood(Helmet):

    def __init__(self):
        super().__init__(
            name="Enchanted Hood",
            description="A hood embroidered with protective thread that turns "
            "aside glancing blows.",
            value=3500,
            rarity=0.5,
            armor=5,
            subtyp="Cloth",
            unequip=False,
        )
        self.weight = 1


class MitreHat(Helmet):

    def __init__(self):
        super().__init__(
            name="Mitre Hat",
            description="A ceremonial mitre reinforced with sacred thread and geomantic " "sigils.",
            value=10000,
            rarity=0.4,
            armor=9,
            subtyp="Cloth",
            unequip=False,
        )
        self.weight = 1
        self.restriction = ["Priest", "Archbishop", "Diviner", "Astromancer"]


class Circlet(Helmet):

    def __init__(self):
        super().__init__(
            name="Circlet",
            description="A thin metal circlet that focuses the wearer's will into a "
            "protective halo.",
            value=12000,
            rarity=0.4,
            armor=8,
            subtyp="Cloth",
            unequip=False,
        )
        self.weight = 2
        self.restricted_against = ["Priest", "Archbishop", "Diviner", "Astromancer"]


class CohuleenDruith(Helmet):

    def __init__(self):
        super().__init__(
            name="Cohuleen Druith",
            description="A fey cap steeped in old river magic and woven with "
            "reeds from a hidden ford.",
            value=40000,
            rarity=0.2,
            armor=10,
            subtyp="Cloth",
            unequip=False,
        )
        self.weight = 1
        self.element = "Water"
        self.resist_mod = 0.5


class AriadnesDiadem(Helmet):

    def __init__(self):
        super().__init__(
            name="Ariadne's Diadem",
            description="A legendary diadem whose threadlike filigree guides the "
            "wearer safely through impossible danger.",
            value=0,
            rarity=0,
            armor=12,
            subtyp="Cloth",
            unequip=False,
        )
        self.weight = 1
        self.special = True


class LeatherCap(Helmet):

    def __init__(self):
        super().__init__(
            name="Leather Cap",
            description="A boiled leather cap that protects the head while keeping "
            "movement light.",
            value=80,
            rarity=0.95,
            armor=2,
            subtyp="Light",
            unequip=False,
        )
        self.weight = 2


class PithHelmet(Helmet):

    def __init__(self):
        super().__init__(
            name="Pith Helmet",
            description="A stiffened light helmet with a broad brim and padded crown.",
            value=700,
            rarity=0.85,
            armor=3,
            subtyp="Light",
            unequip=False,
        )
        self.weight = 3


class WarMask(Helmet):

    def __init__(self):
        super().__init__(
            name="War Mask",
            description="A hardened leather mask shaped to intimidate and deflect cuts.",
            value=1800,
            rarity=0.75,
            armor=4,
            subtyp="Light",
            unequip=False,
        )
        self.weight = 2


class ArmingCap(Helmet):

    def __init__(self):
        super().__init__(
            name="Arming Cap",
            description="A reinforced cap worn under heavier helms or alone by light " "fighters.",
            value=8500,
            rarity=0.5,
            armor=5,
            subtyp="Light",
            unequip=False,
        )
        self.weight = 3


class Katapu(Helmet):

    def __init__(self):
        super().__init__(
            name="Katapu",
            description="A light protective headpiece built from layered plates and lacquered "
            "leather.",
            value=18000,
            rarity=0.4,
            armor=7,
            subtyp="Light",
            unequip=False,
        )
        self.weight = 2


class Somen(Helmet):

    def __init__(self):
        super().__init__(
            name="Sōmen",
            description="A full-face light helm that protects without sacrificing agility.",
            value=48000,
            rarity=0.2,
            armor=10,
            subtyp="Light",
            unequip=False,
        )
        self.weight = 4


class DemonCowl(Helmet):

    def __init__(self):
        super().__init__(
            name="Demon Cowl",
            description="A sinister cowl threaded with funereal charms and ash-dark " "silk.",
            value=0,
            rarity=0,
            armor=16,
            subtyp="Light",
            unequip=False,
        )
        self.weight = 4
        self.special = True
        self.element = "Death"
        self.resist_mod = 0.5


class ScaleHelm(Helmet):

    def __init__(self):
        super().__init__(
            name="Scale Helm",
            description="A sturdy helmet of overlapping metal scales.",
            value=120,
            rarity=0.95,
            armor=3,
            subtyp="Medium",
            unequip=False,
        )
        self.weight = 4


class ChainCoif(Helmet):

    def __init__(self):
        super().__init__(
            name="Chain Coif",
            description="A hood of interlocking metal rings worn under or instead of " "a helmet.",
            value=900,
            rarity=0.85,
            armor=4,
            subtyp="Medium",
            unequip=False,
        )
        self.weight = 5


class KulahKhud(Helmet):

    def __init__(self):
        super().__init__(
            name="Kulah Khud",
            description="A domed medium helm with cheek guards and a mail aventail.",
            value=2400,
            rarity=0.75,
            armor=6,
            subtyp="Medium",
            unequip=False,
        )
        self.weight = 4


class Cervelliere(Helmet):

    def __init__(self):
        super().__init__(
            name="Cervelliere",
            description="A close-fitting steel skullcap that can be worn beneath other "
            "headgear.",
            value=10000,
            rarity=0.5,
            armor=8,
            subtyp="Medium",
            unequip=False,
        )
        self.weight = 8


class VisoredSallet(Helmet):

    def __init__(self):
        super().__init__(
            name="Visored Sallet",
            description="A fitted steel helmet with a narrow visor and strong " "neck guard.",
            value=22000,
            rarity=0.4,
            armor=10,
            subtyp="Medium",
            unequip=False,
        )
        self.weight = 6


class Tolga(Helmet):

    def __init__(self):
        super().__init__(
            name="Tolga",
            description="A heavy medium helm with reinforced bands and a high nasal guard.",
            value=22000,
            rarity=0.4,
            armor=10,
            subtyp="Medium",
            unequip=False,
        )
        self.weight = 6


class Tarnhelm(Helmet):

    def __init__(self):
        super().__init__(
            name="Tarnhelm",
            description="A mythic helm that bends sight around its wearer and grants "
            "invisibility.",
            value=55000,
            rarity=0.2,
            armor=13,
            subtyp="Medium",
            unequip=False,
        )
        self.weight = 11
        self.special = True


class HelmOfRostam(Helmet):

    def __init__(self):
        super().__init__(
            name="Helm of Rostam",
            description="A heroic medium helm whose crest steadies the wearer "
            "against panic and stunning blows.",
            value=0,
            rarity=0,
            armor=19,
            subtyp="Medium",
            unequip=False,
        )
        self.weight = 8
        self.mod = "Status-Berserk Status-Stun"
        self.special = True


class IronHelm(Helmet):

    def __init__(self):
        super().__init__(
            name="Iron Helm",
            description="A heavy iron helmet that favors protection over comfort.",
            value=160,
            rarity=0.95,
            armor=4,
            subtyp="Heavy",
            unequip=False,
        )
        self.weight = 6


class KettleHelm(Helmet):

    def __init__(self):
        super().__init__(
            name="Kettle Helm",
            description="A brimmed iron helmet that sheds blows away from the face and " "neck.",
            value=1200,
            rarity=0.85,
            armor=6,
            subtyp="Heavy",
            unequip=False,
        )
        self.weight = 5


class Barbute(Helmet):

    def __init__(self):
        super().__init__(
            name="Barbute",
            description="A heavy helm with a T-shaped opening and strong cheek protection.",
            value=3200,
            rarity=0.75,
            armor=8,
            subtyp="Heavy",
            unequip=False,
        )
        self.weight = 7


class GreatHelm(Helmet):

    def __init__(self):
        super().__init__(
            name="Great Helm",
            description="A full steel helm with narrow eye slits and thick plates.",
            value=13000,
            rarity=0.5,
            armor=10,
            subtyp="Heavy",
            unequip=False,
        )
        self.weight = 8


class PlateHelm(Helmet):

    def __init__(self):
        super().__init__(
            name="Plate Helm",
            description="A masterwork plate helmet that completes a knight's " "heavy armor kit.",
            value=28000,
            rarity=0.4,
            armor=12,
            subtyp="Heavy",
            unequip=False,
        )
        self.weight = 9


class CloseHelm(Helmet):

    def __init__(self):
        super().__init__(
            name="Close Helm",
            description="A fully enclosing heavy helm with a fitted visor and reinforced "
            "gorget.",
            value=62000,
            rarity=0.2,
            armor=18,
            subtyp="Heavy",
            unequip=False,
        )
        self.weight = 14


class Kabuto(Helmet):

    def __init__(self):
        super().__init__(
            name="Kabuto",
            description="A legendary heavy helm with layered plates and a commanding crest.",
            value=0,
            rarity=0,
            armor=25,
            subtyp="Heavy",
            unequip=False,
        )
        self.weight = 16
        self.special = True


class Tunic(Armor):

    def __init__(self):
        super().__init__(
            name="Tunic",
            description="A close-fitting short coat as part of a uniform, especially a "
            "police or military uniform.",
            value=60,
            rarity=0.95,
            armor=2,
            subtyp="Cloth",
            unequip=False,
        )
        self.weight = 2


class ClothCloak(Armor):

    def __init__(self):
        super().__init__(
            name="Cloth Cloak",
            description="An outdoor cloth garment, typically sleeveless, that hangs "
            "loosely from the shoulders.",
            value=200,
            rarity=0.9,
            armor=4,
            subtyp="Cloth",
            unequip=False,
        )
        self.weight = 2


class SilverCloak(Armor):

    def __init__(self):
        super().__init__(
            name="Silver Cloak",
            description="A cloak weaved with strands of silver to improve protective " "power.",
            value=2500,
            rarity=0.85,
            armor=6,
            subtyp="Cloth",
            unequip=False,
        )
        self.weight = 3


class GoldCloak(Armor):

    def __init__(self):
        super().__init__(
            name="Gold Cloak",
            description="A cloak weaved with strands of gold to improve protective " "power.",
            value=7000,
            rarity=0.75,
            armor=10,
            subtyp="Cloth",
            unequip=False,
        )
        self.weight = 4


class CloakEnchantment(Armor):

    def __init__(self):
        super().__init__(
            name="Cloak of Enchantment",
            description="A magical cloak that shields the wearer from all " "forms of attack.",
            value=22000,
            rarity=0.5,
            armor=14,
            subtyp="Cloth",
            unequip=False,
        )
        self.weight = 3


class WizardRobe(Armor):

    def __init__(self):
        super().__init__(
            name="Wizard's Robe",
            description="A knee-length, long-sleeved robe with an impressive hood "
            "designed to add a mysterious feel to magic users.",
            value=45000,
            rarity=0.4,
            armor=20,
            subtyp="Cloth",
            unequip=False,
        )
        self.weight = 4


class Tarnkappe(Armor):

    def __init__(self):
        super().__init__(
            name="Tarnkappe",
            description="A tarnkappe is a mythical garment that grants its wearer the "
            "power to become invisible and move undetected. The Tarnkappe "
            "is depicted as a dark, enchanted cloak or hood, embodying the "
            "idea of secrecy, stealth, and mysticism.",
            value=90000,
            rarity=0.2,
            armor=24,
            subtyp="Cloth",
            unequip=False,
        )
        self.weight = 1


class MerlinRobe(Armor):

    def __init__(self):
        super().__init__(
            name="Robes of Merlin",
            description="The enchanted robes of Merlin the enchanter.",
            value=0,
            rarity=0.0,
            armor=30,
            subtyp="Cloth",
            unequip=False,
        )
        self.weight = 2

    def special_effect(self, results: CombatResultGroup) -> None:
        result = results[-1]
        mana = getattr(result.target, "mana", None)
        if mana is None:
            return results
        amount = max(1, int((result.damage or 0) * 0.25))
        before = mana.current
        mana.current = min(mana.max, mana.current + amount)
        restored = mana.current - before
        if restored > 0:
            result.extra["Mana Restored"] = restored
            result.message += f"{result.target.name}'s Robes of Merlin restore {restored} mana.\n"
        return results


class PaddedArmor(Armor):

    def __init__(self):
        super().__init__(
            name="Padded Armor",
            description="Consists of quilted layers of cloth and feathers to provide"
            " some protection from attack.",
            value=75,
            rarity=0.95,
            armor=4,
            subtyp="Light",
            unequip=False,
        )
        self.weight = 4


class LeatherArmor(Armor):

    def __init__(self):
        super().__init__(
            name="Leather Armor",
            description="A protective covering made of animal hide, boiled to make "
            "it tough and rigid and worn over the torso to protect it "
            "from injury.",
            value=600,
            rarity=0.85,
            armor=6,
            subtyp="Light",
            unequip=False,
        )
        self.weight = 5


class Cuirboulli(Armor):

    def __init__(self):
        super().__init__(
            name="Cuirboulli",
            description='French for "boiled leather", this armor has increased '
            "rigidity for add protection",
            value=3000,
            rarity=0.75,
            armor=8,
            subtyp="Light",
            unequip=False,
        )
        self.weight = 6


class StuddedLeather(Armor):

    def __init__(self):
        super().__init__(
            name="Studded Leather",
            description="Leather armor embedded with iron studs to improve "
            "defensive capabilities.",
            value=20000,
            rarity=0.5,
            armor=16,
            subtyp="Light",
            unequip=False,
        )
        self.weight = 7


class StuddedCuirboulli(Armor):

    def __init__(self):
        super().__init__(
            name="Studded Cuirboulli",
            description="Boiled leather armor embedded with iron studs to "
            "improve defensive capabilities.",
            value=42000,
            rarity=0.4,
            armor=24,
            subtyp="Light",
            unequip=False,
        )
        self.weight = 8


class MithrilCoat(Armor):

    def __init__(self):
        super().__init__(
            name="Mithril Coat",
            description="A mithril coat is a lightweight, shimmering shirt of armor "
            "made from mithril, a rare and incredibly strong metal. "
            "Known for its silver-like appearance and superior "
            "durability, the mithril coat offers exceptional protection"
            " while remaining much lighter than traditional steel armor.",
            value=95000,
            rarity=0.2,
            armor=28,
            subtyp="Light",
            unequip=False,
        )
        self.weight = 2


class DragonHide(Armor):

    def __init__(self):
        super().__init__(
            name="Dragon Hide",
            description="Hide armor made from the scales of a red dragon, "
            "inconceivably light for this type of armor.",
            value=0,
            rarity=0.0,
            armor=36,
            subtyp="Light",
            unequip=False,
        )
        self.weight = 10
        self.special = True
        self.element = "Fire"

    def special_effect(self, results: CombatResultGroup) -> None:
        result = results[-1]
        if not result.actor or not result.target:
            return results
        try:
            resist = result.actor.check_mod("resist", enemy=result.target, typ=self.element)
        except KeyError:
            resist = 0
        damage = max(0, int((result.damage or 0) * 0.25 * (1 - resist)))
        if damage > 0:
            result.actor.health.current -= damage
            result.extra["Dragon Hide Damage"] = damage
            result.effects_applied["Magic"].append(self.element)
            result.message += f"{result.target.name}'s Dragon Hide scorches {result.actor.name} for {damage} fire damage.\n"
        return results


class HideArmor(Armor):

    def __init__(self):
        super().__init__(
            name="Hide Armor",
            description="A crude armor made from thick furs and pelts.",
            value=100,
            rarity=0.95,
            armor=6,
            subtyp="Medium",
            unequip=False,
        )
        self.weight = 9


class ChainShirt(Armor):

    def __init__(self):
        super().__init__(
            name="Chain Shirt",
            description="A type of armor consisting of small metal rings linked "
            "together in a pattern to form a mesh.",
            value=800,
            rarity=0.85,
            armor=8,
            subtyp="Medium",
            unequip=False,
        )
        self.weight = 12


class ScaleMail(Armor):

    def __init__(self):
        super().__init__(
            name="Scale Mail",
            description="Armor consisting of a coat and leggings of leather covered"
            " with overlapping pieces of metal, mimicking the scales of a "
            "fish.",
            value=4000,
            rarity=0.75,
            armor=10,
            subtyp="Medium",
            unequip=False,
        )
        self.weight = 10


class Breastplate(Armor):

    def __init__(self):
        super().__init__(
            name="Breastplate",
            description="Armor consisting of a fitted metal chest piece worn with "
            "supple leather. Although it leaves the legs and arms "
            "relatively unprotected, this armor provides good protection "
            "for the wearer's vital organs while leaving the wearer "
            "relatively unencumbered.",
            value=23500,
            rarity=0.5,
            armor=18,
            subtyp="Medium",
            unequip=False,
        )
        self.weight = 15


class HalfPlate(Armor):

    def __init__(self):
        super().__init__(
            name="Half Plate",
            description="Armor consisting of shaped metal plates that cover most of the"
            " wearer's body. It does not include leg Protection beyond "
            "simple greaves that are attached with leather straps.",
            value=46000,
            rarity=0.4,
            armor=26,
            subtyp="Medium",
            unequip=False,
        )
        self.weight = 20


class Kusari(Armor):

    def __init__(self):
        super().__init__(
            name="Kusari",
            description="Kusari armor is made from interconnected metal rings, providing "
            "excellent flexibility and mobility. This chain mail offers robust"
            " protection while allowing for ease of movement, making it ideal "
            "for both ranged and close combat.",
            value=100000,
            rarity=0.2,
            armor=32,
            subtyp="Medium",
            unequip=False,
        )
        self.weight = 17


class Klivanion(Armor):

    def __init__(self):
        super().__init__(
            name="Klivanion",
            description="A lamellar breastplate whose charged plates lash attackers with "
            "lightning and can stun them in place.",
            value=0,
            rarity=0.0,
            armor=36,
            subtyp="Medium",
            unequip=False,
        )
        self.weight = 18
        self.special = True
        self.element = "Electric"

    def special_effect(self, results: CombatResultGroup) -> None:
        result = results[-1]
        if not result.actor or not result.target:
            return results
        damage = result.damage or 0
        if damage <= 0:
            return results
        try:
            resist = result.actor.check_mod("resist", enemy=result.target, typ=self.element)
        except KeyError:
            resist = 0
        shock_damage = max(0, int(damage * 0.15 * (1 - resist)))
        if shock_damage > 0:
            result.actor.health.current -= shock_damage
            result.extra["Klivanion Shock Damage"] = shock_damage
            result.effects_applied["Magic"].append(self.element)
            result.message += f"{result.target.name}'s Klivanion shocks {result.actor.name} for {shock_damage} lightning damage.\n"
        if shock_damage > 0 and random.random() < 0.25:
            stun = result.actor.status_effects.get("Stun")
            if (
                stun
                and not stun.active
                and result.actor.apply_stun(1, source=self.name, applier=result.target)
            ):
                result.effects_applied["Status"].append("Stun")
                result.message += f"{result.actor.name} is stunned by the Klivanion.\n"
        return results


class RingMail(Armor):

    def __init__(self):
        super().__init__(
            name="Ring Mail",
            description="Leather armor with heavy rings sewn into it. The rings help "
            "reinforce the armor against blows from Swords and axes.",
            value=200,
            rarity=0.95,
            armor=8,
            subtyp="Heavy",
            unequip=False,
        )
        self.weight = 15


class ChainMail(Armor):

    def __init__(self):
        super().__init__(
            name="Chain Mail",
            description="Made of interlocking metal rings, includes a layer of quilted "
            "fabric worn underneath the mail to prevent chafing and to "
            "cushion the impact of blows. The suit includes gauntlets.",
            value=1000,
            rarity=0.85,
            armor=10,
            subtyp="Heavy",
            unequip=False,
        )
        self.weight = 18


class Splint(Armor):

    def __init__(self):
        super().__init__(
            name="Splint Mail",
            description="Armor made of narrow vertical strips of metal riveted to a "
            "backing of leather that is worn over cloth padding. Flexible "
            "chain mail protects the joints.",
            value=6000,
            rarity=0.75,
            armor=14,
            subtyp="Heavy",
            unequip=False,
        )
        self.weight = 20


class PlateMail(Armor):

    def __init__(self):
        super().__init__(
            name="Plate Mail",
            description="Armor consisting of shaped, interlocking metal plates to "
            "cover most of the body.",
            value=27500,
            rarity=0.5,
            armor=20,
            subtyp="Heavy",
            unequip=False,
        )
        self.weight = 25


class Palangina(Armor):

    def __init__(self):
        super().__init__(
            name="Palangina",
            description="A Persian lamellar cuirass worked with fire-red and water-blue inlays.",
            value=55000,
            rarity=0.4,
            armor=30,
            subtyp="Heavy",
            unequip=False,
        )
        self.weight = 30
        self.resistances = {"Fire": 0.25, "Water": 0.25}


class Maximilian(Armor):

    def __init__(self):
        super().__init__(
            name="Maximilian",
            description="Maximilian armor is characterized by its intricate designs "
            "and full-coverage plates. Known for its effectiveness in both"
            " defense and mobility, this armor often features a "
            "distinctive fluted design, which not only enhances its "
            "aesthetic appeal but also reinforces the structure, providing"
            " extra strength without adding excessive weight.",
            value=110000,
            rarity=0.2,
            armor=40,
            subtyp="Heavy",
            unequip=False,
        )
        self.weight = 30


class Genji(Armor):

    def __init__(self):
        super().__init__(
            name="Genji Armor",
            description="Mythical armor crafted by an unknown master blacksmith and "
            "embued with protective enchantments that allow the user to "
            "shrug off damage.",
            value=0,
            rarity=0.0,
            armor=50,
            subtyp="Heavy",
            unequip=False,
        )
        self.weight = 25
        self.special = True

    def special_effect(self, results: CombatResultGroup) -> None:
        result = results[-1]
        if not result.target:
            return results
        reduction = max(1, int((result.damage or 0) * 0.20))
        result.target.health.current = min(
            result.target.health.max, result.target.health.current + reduction
        )
        result.healing = (result.healing or 0) + reduction
        result.extra["Genji Damage Recovered"] = reduction
        result.message += f"{result.target.name}'s Genji Armor shrugs off {reduction} damage.\n"
        return results


class NaturalArmor(Armor):

    def __init__(self, name: str, armor: int, description: str) -> None:
        super().__init__(
            name=name,
            armor=armor,
            description=description,
            rarity=0,
            subtyp="Natural",
            unequip=False,
            value=0,
        )


class AnimalHide(NaturalArmor):

    def __init__(self):
        super().__init__(name="Animal Hide", armor=4, description="")


class AnimalHide2(AnimalHide):

    def __init__(self):
        super().__init__()
        self.armor = 12


class Carapace(NaturalArmor):

    def __init__(self):
        super().__init__(name="Carapace", armor=6, description="")


class StoneArmor(NaturalArmor):

    def __init__(self):
        super().__init__(name="Stone Armor", armor=8, description="")


class StoneArmor2(StoneArmor):

    def __init__(self):
        super().__init__()
        self.armor = 18


class SnakeScales(NaturalArmor):

    def __init__(self):
        super().__init__(name="Snake Scales", armor=6, description="")


class SnakeScales2(SnakeScales):

    def __init__(self):
        super().__init__()
        self.armor = 6


class DemonArmor(NaturalArmor):

    def __init__(self):
        super().__init__(name="Demon Armor", armor=8, description="")


class DemonArmor2(DemonArmor):
    """
    Deals additional shadow damage to attacker
    """

    def __init__(self):
        super().__init__()
        self.armor = 20
        self.special = True
        self.shadow_damage = 25

    def special_effect(self, results: CombatResultGroup) -> None:
        result = results[-1]
        resist = result.actor.check_mod("resist", enemy=result.target, typ="Shadow")
        damage = int(random.randint(self.shadow_damage // 2, self.shadow_damage) * (1 - resist))
        result.actor.health.current -= damage
        if damage > 0:
            result.damage += damage
        elif damage < 0:
            result.healing = abs(damage)
        return results


class MetalPlating(NaturalArmor):

    def __init__(self):
        super().__init__(name="Metal Plating", armor=10, description="")


class DragonScale(NaturalArmor):

    def __init__(self):
        super().__init__(name="Dragon Scales", armor=12, description="")


class CerberusHide(NaturalArmor):
    """
    deals additional fire damage to attacker
    """

    def __init__(self):
        super().__init__(name="Cerberus Hide", armor=36, description="")
        self.special = True
        self.fire_damage = 50

    def special_effect(self, results: CombatResultGroup) -> None:
        result = results[-1]
        resist = result.actor.check_mod("resist", enemy=result.target, typ="Fire")
        damage = int(random.randint(self.fire_damage // 2, self.fire_damage) * (1 - resist))
        result.actor.health.current -= damage
        if damage > 0:
            pass
        elif damage < 0:
            result.healing[-1] = abs(damage)
        return results


class DevilSkin(NaturalArmor):
    """
    deals additional non-elemental damage to attacker
    """

    def __init__(self):
        super().__init__(name="Devil Skin", armor=80, description="")
        self.special = True
        self.damage = 100

    def special_effect(self, results: CombatResultGroup) -> None:
        result = results[-1]
        a_chance = result.actor.check_mod("luck", enemy=result.target, luck_factor=10)
        damage = random.randint(self.damage // (1 + a_chance), self.damage)
        result.actor.health.current -= damage
        return results
