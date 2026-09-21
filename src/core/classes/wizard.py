"""Wizard class definition and six-school affinity helpers."""

from __future__ import annotations

from typing import Any

from src.core.randomness import gameplay_random as random

from .base import Job

AFFINITY_SCHOOLS = ("Fire", "Ice", "Water", "Electric", "Earth", "Wind", "Arcane")
OPPOSITES = {
    "Fire": "Ice",
    "Ice": "Fire",
    "Water": "Electric",
    "Electric": "Water",
    "Earth": "Wind",
    "Wind": "Earth",
}
DEFAULT_AFFINITY = 0.0
SORCERER_CAP = 50.0
WIZARD_CAP = 100.0
AFFINITY_STEP = 2.0
RING_AFFINITY_STEP = 3.0
ARCANE_AFFINITY_STEP = 1.0
RING_ARCANE_AFFINITY_STEP = 1.5
OPPOSITE_DRIFT = 1.0
OTHER_DRIFT = 0.2
AFFINITY_MIN = 0
AFFINITY_MAX = 100.0
SORCERER_UNLOCK_THRESHOLD = 30.0
SORCERER_MASTERY_THRESHOLD = 50.0
WIZARD_UNLOCK_THRESHOLD = 80.0
WIZARD_MASTERY_THRESHOLD = 100.0
PHOTON_SPHERE_QUEST = "The Light Beyond Domingo"
ELEMENTAL_ULTIMATE_QUEST = "The Sixfold Calamity"
ARCANE_EVIDENCE_ENEMIES = (
    "Lich",
    "Beholder",
    "Brain Gorger",
    "Mind Flayer",
    "Warforged",
    "Aboleth",
)
ELEMENTAL_EVIDENCE_ENEMIES = (
    "Fire Myrmidon",
    "Ice Myrmidon",
    "Storm Myrmidon",
    "Wind Myrmidon",
    "Water Myrmidon",
    "Earth Myrmidon",
)

SPELL_UPGRADES: dict[str, tuple[str, str, str]] = {
    "Fire": ("Firebolt", "Fireball", "Firestorm"),
    "Ice": ("Ice Lance", "Icicle", "Blizzard"),
    "Electric": ("Shock", "Lightning", "Electrocution"),
    "Water": ("Water Jet", "Aqualung", "Tsunami"),
    "Earth": ("Tremor", "Mudslide", "Earthquake"),
    "Wind": ("Gust", "Hurricane", "Tornado"),
    "Arcane": ("Magic Missile", "Magic Missile II", "Magic Missile III"),
}


class Wizard(Job):
    """
    Promotion: Mage -> Sorcerer -> Wizard
    Additional Pros: Increased dex gain
    Additional Cons: None
    """

    def __init__(self):
        super().__init__(
            name="Wizard",
            description="The Wizard is a master of arcane magic, unparalleled in their "
            "magical ability. Being able to cast the most powerful spells makes"
            " the wizard an ideal class for anyone who prefers to live fast "
            "and die hard if not properly prepared.",
            str_plus=0,
            int_plus=3,
            wis_plus=2,
            con_plus=0,
            cha_plus=1,
            dex_plus=1,
            att_plus=0,
            def_plus=1,
            magic_plus=5,
            magic_def_plus=4,
            restrictions={
                "Weapon": ["Dagger", "Staff"],
                "OffHand": ["Tome"],
                "Armor": ["Cloth"],
            },
            pro_level=3,
        )


def default_affinity() -> dict[str, float]:
    return {school: DEFAULT_AFFINITY for school in AFFINITY_SCHOOLS}


def cap_for(character: Any | None) -> float:
    class_name = getattr(getattr(character, "cls", None), "name", None)
    return WIZARD_CAP if class_name == "Wizard" else SORCERER_CAP


def normalize_affinity(
    state: Any, *, cap: float = WIZARD_CAP, migrate_legacy: bool = False
) -> dict[str, float]:
    affinity = default_affinity()
    if isinstance(state, dict):
        for school in AFFINITY_SCHOOLS:
            try:
                value = float(state.get(school, DEFAULT_AFFINITY) or DEFAULT_AFFINITY)
            except (TypeError, ValueError):
                value = DEFAULT_AFFINITY
            if migrate_legacy:
                value = max(0.0, value - 50.0)
            affinity[school] = max(float(AFFINITY_MIN), min(float(cap), value))
    return affinity


def ensure_affinity(character: Any) -> dict[str, float]:
    version = int(getattr(character, "wizard_affinity_version", 1) or 1)
    affinity = normalize_affinity(
        getattr(character, "wizard_affinity", None),
        cap=cap_for(character),
        migrate_legacy=version < 2,
    )
    setattr(character, "wizard_affinity", affinity)
    setattr(character, "wizard_affinity_version", 2)
    return affinity


def school_from_ability(ability: Any) -> str | None:
    for candidate in (
        getattr(ability, "subtyp", None),
        getattr(ability, "school", None),
        getattr(ability, "damage_type", None),
    ):
        if str(candidate) in AFFINITY_SCHOOLS:
            return str(candidate)
    return None


def record_cast(character: Any, school: str | None) -> dict[str, float]:
    if school not in AFFINITY_SCHOOLS:
        return ensure_affinity(character)
    affinity = ensure_affinity(character)
    cap = cap_for(character)
    ring_accelerates = _wizard_ring_accelerates(character)
    if school == "Arcane":
        step = RING_ARCANE_AFFINITY_STEP if ring_accelerates else ARCANE_AFFINITY_STEP
    else:
        step = RING_AFFINITY_STEP if ring_accelerates else AFFINITY_STEP
    affinity[school] = min(cap, affinity[school] + step)
    if school == "Arcane":
        return affinity
    opposite = OPPOSITES[school]
    affinity[opposite] = max(float(AFFINITY_MIN), affinity[opposite] - OPPOSITE_DRIFT)
    for other in AFFINITY_SCHOOLS:
        if other not in {school, opposite}:
            affinity[other] = max(float(AFFINITY_MIN), affinity[other] - OTHER_DRIFT)
    return affinity


def affinity_damage_bonus(character: Any, damage_type: str | None) -> float:
    if getattr(getattr(character, "cls", None), "name", None) not in {"Sorcerer", "Wizard"}:
        return 0.0
    if damage_type not in AFFINITY_SCHOOLS:
        return 0.0
    affinity = ensure_affinity(character)
    return max(0.0, int(affinity[damage_type] // 10) * 0.01)


def frozen_armor_reduction(character: Any, damage: int) -> tuple[int, str]:
    """Retain the legacy hook; Frozen Armor now reduces only incoming Ice."""
    return damage, ""


def process_cast(character: Any, spell: Any, target: Any | None = None) -> str:
    from . import mage_mechanics

    message = mage_mechanics.process_cast(character, spell, target)
    if getattr(getattr(character, "cls", None), "name", None) not in {"Sorcerer", "Wizard"}:
        return message
    school = mage_mechanics.school_from_ability(spell)
    if school not in AFFINITY_SCHOOLS:
        return message
    chosen = mage_mechanics.specialization(character)
    if chosen == "Arcane" and school != "Arcane":
        return message
    if chosen == "Elemental" and school == "Arcane":
        return message
    affinity = ensure_affinity(character)
    previous = affinity[school]
    affinity = record_cast(character, school)
    mastery_threshold = cap_for(character)
    if previous < mastery_threshold <= affinity[school]:
        message += f"{character.name} has mastered {school} affinity!\n"
    message += _upgrade_spellbook(character, school)
    message += _apply_mastery_proc(character, school, target)
    return message


def _wizard_ring_accelerates(character: Any) -> bool:
    if getattr(getattr(character, "cls", None), "name", None) != "Wizard":
        return False
    try:
        from . import class_rings

        return class_rings.is_awakened(character, "Wizard") and class_rings.has_equipped_class_ring(
            character
        )
    except Exception:
        return False


def _spell_class_by_name(spell_name: str):
    from .. import abilities

    class_names = {
        "Ice Lance": "IceLance",
        "Ball Lightning": "BallLightning",
        "Water Jet": "WaterJet",
        "Molten Rock": "MoltenRock",
        "Firebolt": "Firebolt",
        "Fireball": "Fireball",
        "Firestorm": "Firestorm",
        "Icicle": "Icicle",
        "Blizzard": "IceBlizzard",
        "Shock": "Shock",
        "Lightning": "Lightning",
        "Electrocution": "Electrocution",
        "Aqualung": "Aqualung",
        "Tsunami": "Tsunami",
        "Tremor": "Tremor",
        "Mudslide": "Mudslide",
        "Earthquake": "Earthquake",
        "Gust": "Gust",
        "Hurricane": "Hurricane",
        "Tornado": "Tornado",
        "Magic Missile": "MagicMissile",
        "Magic Missile II": "MagicMissile2",
        "Magic Missile III": "MagicMissile3",
    }
    return getattr(abilities, class_names.get(spell_name, spell_name.replace(" ", "")), None)


def _upgrade_spellbook(character: Any, school: str) -> str:
    """Tier-two and tier-three spells are purchased from affinity-gated trees."""
    del character, school
    return ""


def observe_photon_sphere(observer: Any, caster: Any) -> str:
    """Begin the Wizard-only research quest after witnessing Domingo's spell."""
    if getattr(caster, "name", "") != "Domingo":
        return ""
    if getattr(getattr(observer, "cls", None), "name", "") != "Wizard":
        return ""
    quest_dict = getattr(observer, "quest_dict", None)
    if not isinstance(quest_dict, dict):
        return ""
    side_quests = quest_dict.setdefault("Side", {})
    if PHOTON_SPHERE_QUEST in side_quests:
        return ""
    side_quests[PHOTON_SPHERE_QUEST] = {
        "Who": "Warp Point Scientists",
        "Type": "Discovery",
        "What": "",
        "Total": len(ARCANE_EVIDENCE_ENEMIES),
        "Killed": 0,
        "Stage": "consult_scientists",
        "Start Text": (
            "Domingo shaped an impossible sphere of light. The spell was not "
            "part of its designed arsenal; ask its creators how it learned it."
        ),
        "End Text": "The scientists reconstruct Photon Sphere from six arcane proofs.",
        "Help Text": "Approach the scientists at Silvana's staffed warp point.",
        "Reward": [],
        "Reward Number": 1,
        "Experience": 0,
        "Completed": False,
        "Turned In": False,
    }
    return "Quest started: The Light Beyond Domingo. You witnessed Domingo cast " "Photon Sphere.\n"


def observe_elemental_ultimate(observer: Any, caster: Any) -> str:
    """Begin the elemental capstone investigation after witnessing Circe."""
    if getattr(caster, "name", "") != "Circe":
        return ""
    if getattr(getattr(observer, "cls", None), "name", "") != "Wizard":
        return ""
    quest_dict = getattr(observer, "quest_dict", None)
    if not isinstance(quest_dict, dict):
        return ""
    side_quests = quest_dict.setdefault("Side", {})
    if ELEMENTAL_ULTIMATE_QUEST in side_quests:
        return ""
    side_quests[ELEMENTAL_ULTIMATE_QUEST] = {
        "Who": "Warp Point Scientists",
        "Type": "Discovery",
        "What": "",
        "Total": len(ELEMENTAL_EVIDENCE_ENEMIES),
        "Killed": 0,
        "Stage": "consult_scientists",
        "Start Text": (
            "Circe folded all six elemental schools into one catastrophic spell. "
            "Ask the field scientists how such a pattern could remain stable."
        ),
        "End Text": "The six elemental proofs resolve into Prismatic Cataclysm.",
        "Help Text": "Approach the scientists at Silvana's staffed warp point.",
        "Reward": [],
        "Reward Number": 1,
        "Experience": 0,
        "Completed": False,
        "Turned In": False,
    }
    return (
        "Quest started: The Sixfold Calamity. You witnessed Circe cast an "
        "impossible elemental spell.\n"
    )


def consult_photon_sphere_scientists(character: Any) -> str:
    """Advance the Photon Sphere investigation at the staffed warp point."""
    quest = getattr(character, "quest_dict", {}).get("Side", {}).get(PHOTON_SPHERE_QUEST)
    if not isinstance(quest, dict) or quest.get("Turned In"):
        return ""
    if quest.get("Stage") == "consult_scientists":
        quest.update(
            {
                "Stage": "recover_arcane_proofs",
                "Type": "Discovery",
                "What": "",
                "Required Enemies": list(ARCANE_EVIDENCE_ENEMIES),
                "Defeated Enemies": [],
                "Help Text": (
                    "Recover six distinct proofs of self-taught magic from a Lich, "
                    "Beholder, Brain Gorger, Mind Flayer, Warforged, and Aboleth."
                ),
            }
        )
        return (
            "The scientists confirm they never taught Domingo Photon Sphere. "
            "To explain how it invented the spell, recover six distinct proofs "
            "of adaptive magic from the dungeon's most dangerous arcanists."
        )
    if not quest.get("Completed"):
        return ""

    from .. import abilities

    _grant_ultimate(
        character,
        quest,
        spell_name="Photon Sphere",
        spell=abilities.PhotonSphere(),
        node_id="wizard.ability.photon-sphere",
    )
    return (
        "The six proofs reveal how Domingo taught itself to collapse raw Arcane "
        "force. You learn Photon Sphere, gain 50 maximum MP, and earn 3 "
        "progression points."
    )


def consult_elemental_ultimate_scientists(character: Any) -> str:
    """Advance or complete the elemental ultimate investigation."""
    quest = getattr(character, "quest_dict", {}).get("Side", {}).get(ELEMENTAL_ULTIMATE_QUEST)
    if not isinstance(quest, dict) or quest.get("Turned In"):
        return ""
    if quest.get("Stage") == "consult_scientists":
        quest.update(
            {
                "Stage": "recover_elemental_proofs",
                "Type": "Discovery",
                "What": "",
                "Required Enemies": list(ELEMENTAL_EVIDENCE_ENEMIES),
                "Defeated Enemies": [],
                "Help Text": (
                    "Master all six elemental affinities and recover a core proof "
                    "from each of the six Myrmidon schools."
                ),
            }
        )
        return (
            "The pattern requires complete elemental mastery and six living "
            "proofs. Defeat one Myrmidon of every school after mastering all "
            "six elemental affinities."
        )
    defeated = set(quest.get("Defeated Enemies", ()))
    mastered = all(
        ensure_affinity(character).get(school, 0) >= WIZARD_MASTERY_THRESHOLD
        for school in OPPOSITES
    )
    quest["Completed"] = set(ELEMENTAL_EVIDENCE_ENEMIES).issubset(defeated) and mastered
    if not quest["Completed"]:
        return ""

    from .. import abilities

    _grant_ultimate(
        character,
        quest,
        spell_name="Prismatic Cataclysm",
        spell=abilities.PrismaticCataclysm(),
        node_id="wizard.ability.prismatic-cataclysm",
    )
    return (
        "The mastered schools and six Myrmidon proofs lock into a stable whole. "
        "You learn Prismatic Cataclysm, gain 50 maximum MP, and earn 3 "
        "progression points."
    )


def consult_ultimate_research(character: Any) -> str:
    """Resolve every ultimate-spell discussion available at the scientists."""
    return "\n\n".join(
        filter(
            None,
            (
                consult_photon_sphere_scientists(character),
                consult_elemental_ultimate_scientists(character),
            ),
        )
    )


def record_ultimate_quest_defeat(character: Any, enemy_name: str) -> str:
    """Record one distinct late-game proof for either ultimate investigation."""
    messages = []
    side_quests = getattr(character, "quest_dict", {}).get("Side", {})
    for quest_name, required in (
        (PHOTON_SPHERE_QUEST, ARCANE_EVIDENCE_ENEMIES),
        (ELEMENTAL_ULTIMATE_QUEST, ELEMENTAL_EVIDENCE_ENEMIES),
    ):
        quest = side_quests.get(quest_name)
        if not isinstance(quest, dict) or enemy_name not in required:
            continue
        if not str(quest.get("Stage", "")).startswith("recover_"):
            continue
        defeated = set(quest.get("Defeated Enemies", ()))
        if enemy_name in defeated:
            continue
        defeated.add(enemy_name)
        quest["Defeated Enemies"] = sorted(defeated)
        quest["Killed"] = len(defeated)
        if quest_name == PHOTON_SPHERE_QUEST:
            quest["Completed"] = set(required).issubset(defeated)
        messages.append(
            f"Recovered {enemy_name}'s proof for {quest_name} "
            f"({len(defeated)}/{len(required)}).\n"
        )
    return "".join(messages)


def _grant_ultimate(
    character: Any,
    quest: dict[str, Any],
    *,
    spell_name: str,
    spell: Any,
    node_id: str,
) -> None:
    spells = getattr(character, "spellbook", {}).setdefault("Spells", {})
    spells.setdefault(spell_name, spell)
    quest["Stage"] = "learned"
    quest["Turned In"] = True
    character.mana.max += 50
    character.mana.current = min(character.mana.max, character.mana.current + 50)
    try:
        from ..progression import ensure_progression

        progression = ensure_progression(character)
        progression.purchased_node_ids.add(node_id)
        progression.unspent_points += 3
    except Exception:
        pass


def _buff_state(character: Any) -> dict[str, int]:
    from . import mage_mechanics

    state = mage_mechanics._combat_state(character)
    buffs = state.get("school_mastery_buffs")
    if not isinstance(buffs, dict):
        buffs = {}
        state["school_mastery_buffs"] = buffs
    return buffs


def _apply_mastery_proc(character: Any, school: str, target: Any | None) -> str:
    if school == "Arcane":
        return ""
    affinity = ensure_affinity(character)[school]
    class_name = getattr(getattr(character, "cls", None), "name", None)
    if class_name not in {"Sorcerer", "Wizard"}:
        return ""
    if affinity < SORCERER_MASTERY_THRESHOLD:
        return ""
    mastery = affinity >= WIZARD_MASTERY_THRESHOLD and _wizard_ring_accelerates(character)
    chance = 0.12 + (0.08 if mastery else 0.0)
    if random.random() >= chance:
        return ""
    stacks = _buff_state(character)
    stacks[school] = min(3, int(stacks.get(school, 0) or 0) + 1)
    stack = stacks[school]
    if school == "Fire":
        character.stat_effects["Magic"].active = True
        character.stat_effects["Magic"].duration = max(character.stat_effects["Magic"].duration, 2)
        character.stat_effects["Magic"].extra = max(character.stat_effects["Magic"].extra, stack)
        return f"{character.name}'s fire affinity burns brighter ({stack}).\n"
    if school == "Ice":
        character.stat_effects["Defense"].active = True
        character.stat_effects["Defense"].duration = max(
            character.stat_effects["Defense"].duration, 2
        )
        character.stat_effects["Defense"].extra = max(
            character.stat_effects["Defense"].extra, stack
        )
        return f"{character.name}'s ice affinity hardens their guard ({stack}).\n"
    if school == "Water":
        heal = min(character.health.max - character.health.current, stack)
        mana = min(character.mana.max - character.mana.current, stack)
        character.health.current += max(0, heal)
        character.mana.current += max(0, mana)
        return (
            f"{character.name}'s water affinity restores {max(0, heal)} HP and {max(0, mana)} MP.\n"
        )
    if school == "Electric" and target is not None:
        damage = max(1, stack * (2 if mastery else 1))
        target.health.current -= damage
        return f"{character.name}'s electric affinity arcs for {damage} extra damage.\n"
    if school == "Earth":
        character.stat_effects["Defense"].active = True
        character.stat_effects["Defense"].duration = max(
            character.stat_effects["Defense"].duration, 2
        )
        character.stat_effects["Defense"].extra = max(
            character.stat_effects["Defense"].extra, stack
        )
        character.stat_effects["Magic Defense"].active = True
        character.stat_effects["Magic Defense"].duration = max(
            character.stat_effects["Magic Defense"].duration, 2
        )
        character.stat_effects["Magic Defense"].extra = max(
            character.stat_effects["Magic Defense"].extra, stack
        )
        return f"{character.name}'s earth affinity settles into a ward ({stack}).\n"
    if school == "Wind":
        character.stat_effects["Speed"].active = True
        character.stat_effects["Speed"].duration = max(character.stat_effects["Speed"].duration, 2)
        character.stat_effects["Speed"].extra = max(character.stat_effects["Speed"].extra, stack)
        return f"{character.name}'s wind affinity quickens them ({stack}).\n"
    return ""
