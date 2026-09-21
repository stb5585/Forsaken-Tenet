"""SpellStealer class definition and scroll theft helpers."""

from __future__ import annotations

from typing import Any

from src.core.randomness import gameplay_random as random

from .. import abilities, items
from .base import Job


class SpellStealer(Job):
    """
    Promotion: Footpad -> Spell Stealer -> Arcane Trickster
    Pros: Intel and wisdom gain; can use Tomes in offhand and can wear cloth armor
    Cons: Lower dex and no constitution gain; lose access to fist and club weapons
    Special Mechanic: can steal magic from enemies by inscribing it onto Blank Scrolls.
    """

    def __init__(self):
        super().__init__(
            name="Spell Stealer",
            description="The Spell Stealer is an elite evolution of the Footpad, "
            "blending agility and cunning with mystical talent. Masters"
            " of magical deception, they can cast a variety of spells "
            "while uniquely able to steal magic from enemies. Spells "
            "directed at them may be absorbed or reflected back at "
            "their casters. Their versatility allows them to adapt to "
            "both offensive and defensive situations, disrupting foes' "
            "strategies while empowering themselves with stolen magic.",
            str_plus=0,
            int_plus=2,
            wis_plus=1,
            con_plus=0,
            cha_plus=1,
            dex_plus=2,
            att_plus=1,
            def_plus=1,
            magic_plus=4,
            magic_def_plus=2,
            restrictions={
                "Weapon": ["Dagger", "Sword"],
                "OffHand": ["Dagger", "Tome"],
                "Armor": ["Cloth", "Light"],
            },
            pro_level=2,
        )


def has_stolen_magic_talent(character: Any, talent_key: str) -> bool:
    """Return whether a stolen-magic tree talent has been purchased."""
    try:
        from ..progression import has_talent

        return has_talent(character, talent_key)
    except (AttributeError, KeyError, TypeError, ValueError):
        return False


def eligible_spell_classes(target: Any) -> list[type]:
    if getattr(target, "class_ring_trial_enemy", False) and not getattr(
        target, "thieves_guild_trial_enemy", False
    ):
        return []
    spells = getattr(target, "spellbook", {}).get("Spells", {})
    classes: list[type] = []
    for spell in spells.values():
        class_name = getattr(spell, "_class_name", spell.__class__.__name__)
        if class_name and hasattr(abilities, class_name):
            ability_cls = getattr(abilities, class_name)
            classes.append(ability_cls)
    if getattr(target, "boss", False) or getattr(target, "boss_type", None):
        return [cls for cls in classes if not cls.__name__.lower().endswith("ultimate")]
    return classes


def steal_spell(user: Any, target: Any, *, rng: Any = random) -> tuple[bool, str]:
    if getattr(getattr(user, "cls", None), "name", "") not in {"Spell Stealer", "Arcane Trickster"}:
        return False, f"{user.name} cannot steal spells.\n"
    blanks = getattr(user, "inventory", {}).get("Blank Scroll", [])
    if not blanks:
        return False, f"{user.name} needs a Blank Scroll to steal a spell.\n"
    spell_classes = eligible_spell_classes(target)
    if not spell_classes:
        return False, f"{getattr(target, 'name', 'The target')} has no stealable spell.\n"
    spell_cls = rng.choice(spell_classes)
    blank = blanks[0]
    preserve_blank = (
        has_stolen_magic_talent(user, "spell-stealer.perfect-forgery") and rng.random() < 0.25
    )
    if not preserve_blank:
        user.modify_inventory(blank, subtract=True)
    scroll = items.InscribedSpellScroll(spell_cls.__name__)
    user.modify_inventory(scroll)
    try:
        from . import class_rings

        class_rings.activate_spell_steal_buff(user)
    except Exception:
        pass
    message = f"{user.name} steals {scroll.spell.name} onto a Blank Scroll.\n"
    if preserve_blank:
        message += "Perfect Forgery preserves the Blank Scroll.\n"
    return True, message
