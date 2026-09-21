"""Loot tables, equipment routing, and ultimate-weapon catalogs."""

from __future__ import annotations

from typing import Any

import numpy as np

from src.core.randomness import gameplay_random as random

from .accessories import (
    AccuracyRing,
    AntidotePendant,
    BarrierRing,
    CalmingPendant,
    DharmaPendant,
    DiamondLocket,
    EarthAmulet,
    EarthChain,
    ElectricAmulet,
    ElectricChain,
    ElementalAmulet,
    ElementalChain,
    EvasionRing,
    FireAmulet,
    FireChain,
    ForceRing,
    GarfunkelPendant,
    GoldNecklace,
    GorgonPendant,
    IceAmulet,
    IceChain,
    InvisibilityPendant,
    IronRing,
    LevitationPendant,
    MightRing,
    NoPendant,
    NoRing,
    PlatinumNecklace,
    PowerRing,
    RibbonPendant,
    RubyLocket,
    SapphireLocket,
    SilverNecklace,
    SteelRing,
    TitaniumRing,
    VisionPendant,
    WaterAmulet,
    WaterChain,
    WindAmulet,
    WindChain,
)
from .armor import (
    AriadnesDiadem,
    ArmingCap,
    Barbute,
    Breastplate,
    Cervelliere,
    ChainCoif,
    ChainMail,
    ChainShirt,
    Circlet,
    CloakEnchantment,
    CloseHelm,
    ClothCap,
    ClothCloak,
    CohuleenDruith,
    Cuirboulli,
    DemonCowl,
    EnchantedHood,
    GoldCloak,
    GreatHelm,
    HalfPlate,
    HelmOfRostam,
    HideArmor,
    IronHelm,
    Jaapi,
    Kabuto,
    Katapu,
    KettleHelm,
    KulahKhud,
    Kusari,
    LeatherArmor,
    LeatherCap,
    Maximilian,
    MithrilCoat,
    MitreHat,
    NoArmor,
    NoHelmet,
    PaddedArmor,
    Palangina,
    PithHelmet,
    PlateHelm,
    PlateMail,
    RingMail,
    ScaleHelm,
    ScaleMail,
    SilverCloak,
    Somen,
    Splint,
    StuddedCuirboulli,
    StuddedLeather,
    Tarnhelm,
    Tarnkappe,
    Tolga,
    Tunic,
    Turban,
    WarMask,
    WitchHat,
    WizardRobe,
)
from .base import (
    Item,
    Weapon,
)
from .consumables import (
    AardBeing,
    Antidote,
    Bandage,
    CharismaPotion,
    ConPotion,
    DexterityPotion,
    EchoScreen,
    Elixir,
    EyeDrop,
    GreatHealthPotion,
    GreatManaPotion,
    HealthPotion,
    HPPotion,
    IntelPotion,
    ManaPotion,
    MasterHealthPotion,
    MasterManaPotion,
    Megalixir,
    MPPotion,
    PhoenixDown,
    StrengthPotion,
    SuperHealthPotion,
    SuperManaPotion,
    WisdomPotion,
)
from .misc import (
    Amatoxin,
    ArmorPiercingBolts,
    BattleHymnSheet,
    BlankScroll,
    BlessScroll,
    BonesThugsHarmonySheet,
    BoostScroll,
    CenserOfChokingAsh,
    ChorusTimeSheet,
    CleanseScroll,
    DeathcapMushroom,
    DeathScroll,
    DelayedBolts,
    DispelScroll,
    DysfunctionSymphonySheet,
    EarthScroll,
    ElectricScroll,
    FireScroll,
    GoldTriggerSheet,
    HeatSeekingBolts,
    Hemotoxin,
    HolyScroll,
    IceScroll,
    Key,
    LizardVenom,
    LockpickKit,
    LowDefenseRhapsodySheet,
    MagicBolts,
    MetalBolts,
    MildToxin,
    Monocane,
    Myotoxin,
    NapalmBolts,
    Necrotoxin,
    Neurotoxin,
    Oculus,
    OldKey,
    RampartsOdeSheet,
    RealityFragment,
    SanctuaryScroll,
    ScoresAndScoresScoreSheet,
    ScorpionVenom,
    ShadowScroll,
    ShadowVenom,
    ShellScroll,
    SilenceScroll,
    SleepScroll,
    SlowRideSheet,
    SmokeBomb,
    SnakeVenom,
    SoulGem,
    ThrowingDaggers,
    UltimaScroll,
    ViperVenom,
    WaterBladder,
    WaterScroll,
    WindScroll,
    WoodenBolts,
)
from .offhands import (
    Aspis,
    Book,
    Buckler,
    CompendiumAncients,
    CopperLeyRod,
    DowsingRod,
    DragonRouge,
    ElementalPrimer,
    GaiasBranch,
    Glagwa,
    GoldenClaw,
    HandCrossbow,
    HeavyCrossbow,
    InfernalGrimoire,
    KiteShield,
    LightCrossbow,
    MagicCrossbow,
    MoonlitHazelRod,
    Necronomicon,
    NoOffHand,
    Pavise,
    PistolCrossbow,
    RepeatingCrossbow,
    ScepterIfrit,
    Svalinn,
    Targe,
    TomeKnowledge,
    TreatiseBalance,
    Vedas,
    WillowDiviningRod,
    Zephyruswand,
)
from .weapons import (
    BaghNahk,
    Baselard,
    Bastard,
    Baston,
    BattleGauntlet,
    BrassKnuckles,
    Broadaxe,
    Carnwennan,
    Cestus,
    Changdao,
    Claymore,
    Dirk,
    DoubleAxe,
    DragonStaff,
    EarthHammer,
    Excalibur,
    Falchion,
    Flamberge,
    Framea,
    GodsHand,
    Greataxe,
    GreatMaul,
    Gungnir,
    Halberd,
    HolyStaff,
    IndrasFist,
    IronshodStaff,
    Jarnbjorn,
    Jian,
    Katana,
    Khanjar,
    Khatvanga,
    Khopesh,
    Kris,
    Kukri,
    Mace,
    Mattock,
    MithrilshodStaff,
    Mjolnir,
    Morgenstern,
    Naginata,
    Ninjato,
    NoWeapon,
    Parashu,
    Partisan,
    Pernach,
    PrincessGuard,
    Quarterstaff,
    Ranseur,
    Rapier,
    Rondel,
    RuneStaff,
    RuyiJinguBang,
    SerpentStaff,
    Shamshir,
    Shishpar,
    Skullcrusher,
    Sledgehammer,
    SpikeMaul,
    Streithammer,
    Tabarzin,
    Talwar,
    Tanto,
    Trident,
    Wakizashi,
    WarHammer,
    Zweihander,
)

_rarity_table_cache: dict[str, list[type[Item]]] | None = None
_RARITY_BUCKETS = np.array([1.0, 0.9, 0.8, 0.75, 0.50, 0.4, 0.2, 0.0])


def _build_rarity_table() -> dict[str, list[type[Item]]]:
    """Build and cache the rarity-bucketed loot table from items_dict."""
    global _rarity_table_cache
    if _rarity_table_cache is not None:
        return _rarity_table_cache

    rarity_table: dict[str, list[type[Item]]] = {str(i): [] for i in range(1, 9)}
    for typ, typ_dict in items_dict.items():
        if typ == "Weapon":
            for handed in ["1-Handed", "2-Handed"]:
                for lst in items_dict[typ][handed].values():
                    for item_cls in lst:
                        rarity = np.digitize(item_cls().rarity, _RARITY_BUCKETS)
                        rarity_table[str(rarity)].append(item_cls)
        elif typ == "Accessory":
            for acc in ["Ring", "Pendant"]:
                for item_cls in items_dict[typ][acc]:
                    rarity = np.digitize(item_cls().rarity, _RARITY_BUCKETS)
                    rarity_table[str(rarity + 1)].append(item_cls)
        else:
            for value in typ_dict.values():
                for item_cls in value:
                    if not getattr(item_cls, "random_drop", True):
                        continue
                    rarity = np.digitize(item_cls().rarity, _RARITY_BUCKETS)
                    rarity_table[str(rarity + 1)].append(item_cls)
    _rarity_table_cache = rarity_table
    return _rarity_table_cache


def random_item(z: int, *, rng: Any | None = None) -> type[Item]:
    """
    Returns a random item based on the given integer.
    Clamps z to the valid range [1, 8].
    """
    # Clamp z to valid range to prevent KeyError
    z = max(1, min(z, 8))
    rarity_table = _build_rarity_table()
    source = rng or random
    return source.choice(rarity_table[str(z)])


def remove_equipment(typ: str) -> Item:
    typ_dict = {
        "Weapon": NoWeapon,
        "OffHand": NoOffHand,
        "Armor": NoArmor,
        "Helmet": NoHelmet,
        "Pendant": NoPendant,
        "Ring": NoRing,
    }
    return typ_dict[typ]()


def equipment_slots_for_item(item: object, player: object | None = None) -> list[str]:
    """Return equipment slots that can hold this item, optionally filtered by player rules."""
    typ = getattr(item, "typ", None)
    subtyp = getattr(item, "subtyp", None)
    slots: list[str] = []

    if typ == "Weapon":
        slots.append("Weapon")
        if getattr(item, "off", False):
            slots.append("OffHand")
    elif typ in {"Armor", "Helmet", "OffHand"}:
        slots.append(str(typ))
    elif typ == "Accessory" and subtyp in {"Ring", "Pendant"}:
        slots.append(str(subtyp))

    if player is None:
        return slots

    can_equip = getattr(player, "can_equip_item", None)
    if callable(can_equip):
        return [slot for slot in slots if can_equip(item, slot)]

    equip_check = getattr(getattr(player, "cls", None), "equip_check", None)
    if callable(equip_check):
        return [slot for slot in slots if equip_check(item, slot)]
    return slots


items_dict = {
    "Weapon": {
        "1-Handed": {
            "Dagger": [Dirk, Baselard, Kris, Rondel, Kukri, Khanjar],
            "Sword": [Rapier, Jian, Talwar, Shamshir, Khopesh, Falchion],
            "Club": [Mace, WarHammer, Pernach, Morgenstern, Shishpar],
            "Fist": [BrassKnuckles, Cestus, BattleGauntlet, BaghNahk, IndrasFist],
            "Ninja Blade": [Tanto, Wakizashi],
        },
        "2-Handed": {
            "Longsword": [Bastard, Claymore, Zweihander, Changdao, Flamberge, Katana],
            "Battle Axe": [Mattock, Broadaxe, DoubleAxe, Parashu, Greataxe, Tabarzin],
            "Polearm": [Framea, Partisan, Halberd, Naginata, Trident, Ranseur],
            "Staff": [
                Quarterstaff,
                Baston,
                IronshodStaff,
                SerpentStaff,
                HolyStaff,
                RuneStaff,
                MithrilshodStaff,
                Khatvanga,
            ],
            "Hammer": [Sledgehammer, SpikeMaul, EarthHammer, GreatMaul, Streithammer],
        },
    },
    "OffHand": {
        "Shield": [Buckler, Aspis, Targe, Glagwa, KiteShield, Pavise, Svalinn],
        "Crossbow": [
            HandCrossbow,
            LightCrossbow,
            HeavyCrossbow,
            PistolCrossbow,
            RepeatingCrossbow,
            MagicCrossbow,
            GoldenClaw,
        ],
        "Tome": [
            Book,
            TomeKnowledge,
            InfernalGrimoire,
            ElementalPrimer,
            TreatiseBalance,
            DragonRouge,
            Vedas,
            CompendiumAncients,
            Necronomicon,
        ],
        "Rod": [
            WillowDiviningRod,
            CopperLeyRod,
            MoonlitHazelRod,
            DowsingRod,
            ScepterIfrit,
            GaiasBranch,
            Zephyruswand,
        ],
    },
    "Armor": {
        "Cloth": [
            Tunic,
            ClothCloak,
            SilverCloak,
            GoldCloak,
            CloakEnchantment,
            WizardRobe,
            Tarnkappe,
        ],
        "Light": [
            PaddedArmor,
            LeatherArmor,
            Cuirboulli,
            StuddedLeather,
            StuddedCuirboulli,
            MithrilCoat,
        ],
        "Medium": [HideArmor, ChainShirt, ScaleMail, Breastplate, HalfPlate, Kusari],
        "Heavy": [RingMail, ChainMail, Splint, PlateMail, Palangina, Maximilian],
    },
    "Helmet": {
        "Cloth": [
            ClothCap,
            Jaapi,
            Turban,
            WitchHat,
            EnchantedHood,
            MitreHat,
            Circlet,
            CohuleenDruith,
            AriadnesDiadem,
        ],
        "Light": [LeatherCap, PithHelmet, WarMask, ArmingCap, Katapu, Somen, DemonCowl],
        "Medium": [ScaleHelm, ChainCoif, KulahKhud, Cervelliere, Tolga, Tarnhelm, HelmOfRostam],
        "Heavy": [IronHelm, KettleHelm, Barbute, GreatHelm, PlateHelm, CloseHelm, Kabuto],
    },
    "Accessory": {
        "Ring": [
            IronRing,
            PowerRing,
            AccuracyRing,
            BarrierRing,
            SteelRing,
            MightRing,
            EvasionRing,
            TitaniumRing,
            ForceRing,
        ],
        "Pendant": [
            VisionPendant,
            RubyLocket,
            SilverNecklace,
            AntidotePendant,
            CalmingPendant,
            FireChain,
            IceChain,
            ElectricChain,
            WaterChain,
            EarthChain,
            WindChain,
            SapphireLocket,
            GoldNecklace,
            ElementalChain,
            GorgonPendant,
            GarfunkelPendant,
            DharmaPendant,
            LevitationPendant,
            FireAmulet,
            IceAmulet,
            ElectricAmulet,
            WaterAmulet,
            EarthAmulet,
            WindAmulet,
            InvisibilityPendant,
            DiamondLocket,
            PlatinumNecklace,
            ElementalAmulet,
            RibbonPendant,
        ],
    },
    "Potion": {
        "Health": [HealthPotion, GreatHealthPotion, SuperHealthPotion, MasterHealthPotion],
        "Mana": [ManaPotion, GreatManaPotion, SuperManaPotion, MasterManaPotion],
        "Elixir": [Elixir, Megalixir],
        "Stat": [
            HPPotion,
            MPPotion,
            StrengthPotion,
            IntelPotion,
            WisdomPotion,
            ConPotion,
            CharismaPotion,
            DexterityPotion,
            AardBeing,
        ],
        "Status": [Antidote, EyeDrop, EchoScreen, Bandage, PhoenixDown],
    },
    "Misc": {
        "Key": [Key, OldKey],
        "Tool": [LockpickKit, Monocane, SmokeBomb, WaterBladder],
        "Magic Tool": [Oculus, CenserOfChokingAsh],
        "Scroll": [
            BlankScroll,
            BlessScroll,
            SleepScroll,
            FireScroll,
            IceScroll,
            ElectricScroll,
            WaterScroll,
            EarthScroll,
            WindScroll,
            ShadowScroll,
            HolyScroll,
            CleanseScroll,
            BoostScroll,
            ShellScroll,
            SilenceScroll,
            DispelScroll,
            DeathScroll,
            SanctuaryScroll,
            UltimaScroll,
            BattleHymnSheet,
            RampartsOdeSheet,
            DysfunctionSymphonySheet,
            LowDefenseRhapsodySheet,
            SlowRideSheet,
            BonesThugsHarmonySheet,
            ScoresAndScoresScoreSheet,
            GoldTriggerSheet,
            ChorusTimeSheet,
        ],
        "Reagents": [RealityFragment, SoulGem],
        "Toxin Reagent": [
            SnakeVenom,
            ScorpionVenom,
            ViperVenom,
            LizardVenom,
            ShadowVenom,
            DeathcapMushroom,
        ],
        "Toxin": [MildToxin, Neurotoxin, Hemotoxin, Amatoxin, Myotoxin, Necrotoxin],
        "Ammunition": [ThrowingDaggers],
        "Crossbow Bolts": [
            WoodenBolts,
            MetalBolts,
            ArmorPiercingBolts,
            MagicBolts,
            HeatSeekingBolts,
            NapalmBolts,
            DelayedBolts,
        ],
    },
}


ultimate_weapons = {
    "Dagger": Carnwennan,
    "Sword": Excalibur,
    "Mace": Mjolnir,
    "Fist": GodsHand,
    "Axe": Jarnbjorn,
    "Polearm": Gungnir,
    "Staff": [PrincessGuard, RuyiJinguBang, DragonStaff],
    "Hammer": Skullcrusher,
    "Ninja Blade": Ninjato,
}


def ultimate_weapon_options_for(player: Any) -> list[tuple[str, type[Weapon]]]:
    """Return craftable ultimate weapon choices for the player's class."""
    options: list[tuple[str, type[Weapon]]] = []
    equip_check = getattr(getattr(player, "cls", None), "equip_check", None)
    if not callable(equip_check):
        return options

    for typ, weapon_entry in ultimate_weapons.items():
        weapon_classes = weapon_entry if isinstance(weapon_entry, (list, tuple)) else [weapon_entry]
        for weapon_cls in weapon_classes:
            if equip_check(weapon_cls, "Weapon"):
                options.append((typ, weapon_cls))
                break
    return options
