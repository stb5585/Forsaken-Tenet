"""Footpad class definition and shared Footpad-tree mechanics."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from src.core.randomness import gameplay_random as random

from .. import items
from .base import Job

OBSCURATION_STEPS = 50
TOXIN_RECIPES = {
    "Snake Venom": items.MildToxin,
    "Scorpion Venom": items.Neurotoxin,
    "Viper Venom": items.Hemotoxin,
    "Deathcap Mushroom": items.Amatoxin,
    "Lizard Venom": items.Myotoxin,
    "Shadow Venom": items.Necrotoxin,
}


def has_skill(character: Any, name: str) -> bool:
    """Return whether a character knows a named Footpad-tree skill."""
    return name in getattr(character, "spellbook", {}).get("Skills", {})


def start_combat(character: Any) -> None:
    """Reset Footpad passives that can trigger once per battle."""
    character._do_over_used = False
    character._live_and_learn_stacks = 0
    character._surprise_ready = False
    character._surprise_attack = False
    character._combat_concealed = False
    character._shadow_evasion_turns = 0
    character._ghost_step_used = False
    character._untouchable_used = False


def arm_surprise(character: Any, *, has_initiative: bool) -> None:
    """Arm Surprise for the opening attack when its authored conditions hold."""
    character._surprise_ready = bool(
        has_initiative
        and has_skill(character, "Surprise!")
        and int(getattr(character, "obscuration_steps", 0) or 0) > 0
    )


def surprise_accuracy_bonus(character: Any) -> float:
    return 0.20 if getattr(character, "_surprise_attack", False) else 0.0


def surprise_critical_bonus(character: Any) -> float:
    return 0.20 if getattr(character, "_surprise_attack", False) else 0.0


def concealment_dodge_bonus(character: Any) -> float:
    """Return active Invisibility and post-break Shadow Evasion dodge."""
    if getattr(character, "_combat_concealed", False):
        return 0.25
    if (
        has_skill(character, "Shadow Evasion")
        and int(getattr(character, "_shadow_evasion_turns", 0) or 0) > 0
    ):
        return 0.15
    return 0.0


def restore_ghost_step(character: Any) -> str:
    """Restore concealment once per combat after a successful avoidance."""
    if not has_skill(character, "Ghost Step") or getattr(character, "_ghost_step_used", False):
        return ""
    character._ghost_step_used = True
    character._combat_concealed = True
    return f"{character.name}'s Ghost Step restores concealment.\n"


def try_do_over(character: Any, *, rng: Any | None = None) -> bool:
    """Attempt the once-per-battle Do-over reroll after a missed attack."""
    if not has_skill(character, "Do-over") or getattr(character, "_do_over_used", False):
        return False
    generator = rng or random
    if generator.random() >= 0.25:
        return False
    character._do_over_used = True
    return True


def drain_basic_attack_mana(character: Any, target: Any, damage: int) -> int:
    """Apply Mana Depletion to damage dealt by the basic Attack action."""
    if not has_skill(character, "Mana Depletion") or damage <= 0:
        return 0
    mana = getattr(target, "mana", None)
    if mana is None:
        return 0
    drained = min(int(mana.current), max(1, int(damage * 0.10)))
    mana.current -= drained
    return drained


def loot_drop_multiplier(character: Any) -> float:
    """Return Serendipity's ordinary item-drop multiplier."""
    return 1.25 if has_skill(character, "Serendipity") else 1.0


def ordinary_loot_eligible(character: Any, item: Any) -> bool:
    """Return whether a passive loot find may safely grant an item."""
    if item is None or getattr(item, "subtyp", None) in {"Quest", "Special", "Ability"}:
        return False
    if bool(getattr(item, "ultimate", False) or getattr(item, "unique", False)):
        return False
    if " - " in str(getattr(item, "subtyp", "")):
        return False
    allowed = getattr(item, "restricted_classes", None)
    class_value = getattr(getattr(character, "cls", None), "name", "")
    if allowed is not None and class_value not in allowed:
        return False
    return getattr(item, "name", None) not in getattr(character, "special_inventory", {})


def ordinary_loot_threshold(character: Any, item: Any, base_chance: float) -> float:
    """Return the ordinary drop threshold with Scavenger's Eye's rarity nudge."""
    threshold = max(0.0, min(1.0, float(getattr(item, "rarity", 0.0)) * base_chance))
    if not has_skill(character, "Scavenger's Eye") or not ordinary_loot_eligible(
        character,
        item,
    ):
        return threshold
    rarity_nudge = 0.05 * (1.0 - float(getattr(item, "rarity", 0.0)))
    return min(1.0, (threshold * 1.10) + rarity_nudge)


def finders_keepers_candidate(
    character: Any,
    candidates: list[Any],
    *,
    rng: Any | None = None,
) -> Any | None:
    """Roll one conservative extra ordinary find from valid defeated-enemy loot."""
    if not has_skill(character, "Finders Keepers"):
        return None
    generator = rng or random
    eligible = [item for item in candidates if ordinary_loot_eligible(character, item)]
    chance = 0.15
    try:
        from .thief import has_thief_talent

        if has_thief_talent(character, "rogue.deep-pockets"):
            chance += 0.10
    except (AttributeError, KeyError, TypeError, ValueError):
        pass
    if not eligible or generator.random() >= chance:
        return None
    return generator.choice(eligible)


def trap_damage(character: Any, damage: int, *, rng: Any | None = None) -> tuple[int, str]:
    """Resolve Avoid Traps against a triggered trap's negative effect."""
    damage = max(0, int(damage))
    severity, message = trap_severity_multiplier(character, rng=rng)
    return int(damage * severity), message


def trap_severity_multiplier(
    character: Any,
    *,
    rng: Any | None = None,
) -> tuple[float, str]:
    """Return 0, 0.5, or 1 for a trap effect after Avoid Traps."""
    if not has_skill(character, "Avoid Traps"):
        return 1.0, ""
    generator = rng or random
    dexterity = int(getattr(getattr(character, "stats", None), "dex", 10))
    avoid_chance = max(0.25, min(0.75, 0.35 + (dexterity - 10) * 0.02))
    if generator.random() < avoid_chance:
        return 0.0, f"{character.name} avoids the trap's effect."
    return 0.5, "Avoid Traps halves the trap's effect."


def tick_exploration(character: Any, steps: int) -> None:
    """Reduce Obscuration's exploration duration."""
    character.obscuration_steps = max(
        0,
        int(getattr(character, "obscuration_steps", 0) or 0) - max(0, int(steps)),
    )
    character.resist_death_steps = max(
        0,
        int(getattr(character, "resist_death_steps", 0) or 0) - max(0, int(steps)),
    )
    character.silent_walking_steps = max(
        0,
        int(getattr(character, "silent_walking_steps", 0) or 0) - max(0, int(steps)),
    )


def _inventory_stack(character: Any, name: str) -> list[Any]:
    stack = getattr(character, "inventory", {}).get(name, [])
    return stack if isinstance(stack, list) else []


def make_toxin(character: Any) -> str:
    """Consume the first available toxin reagent and craft its toxin."""
    for reagent_name, toxin_class in TOXIN_RECIPES.items():
        stack = _inventory_stack(character, reagent_name)
        if not stack:
            continue
        reagent = stack[0]
        character.modify_inventory(reagent, subtract=True)
        toxin = toxin_class()
        character.modify_inventory(toxin)
        return f"{character.name} crafts {toxin.name} from {reagent_name}.\n"
    return "Make Toxin requires venom or a Deathcap Mushroom.\n"


def apply_toxin(character: Any) -> str:
    """Consume an available toxin and coat an equipped dagger-class weapon."""
    slot = next(
        (
            candidate
            for candidate in ("Weapon", "OffHand")
            if getattr(getattr(character, "equipment", {}).get(candidate), "subtyp", None)
            in {"Dagger", "Ninja Blade"}
        ),
        None,
    )
    if slot is None:
        return "Apply Toxin requires an equipped Dagger or Ninja Blade.\n"
    for toxin_class in TOXIN_RECIPES.values():
        sample = toxin_class()
        stack = _inventory_stack(character, sample.name)
        if stack:
            character.modify_inventory(stack[0], subtract=True)
            character._applied_toxin = {"name": sample.name, "slot": slot}
            return f"{character.name} applies {sample.name} to their {slot.lower()}.\n"
    return "Apply Toxin requires a crafted toxin.\n"


@dataclass(frozen=True)
class ToxinReactionResult:
    """Structured result from consuming a weapon coating."""

    message: str = ""
    status_applied: bool = False
    severe: bool = False
    coating_preserved: bool = False


def apply_coated_toxin(
    attacker: Any,
    target: Any,
    slot: str,
    critical: bool,
) -> ToxinReactionResult:
    """Consume and resolve a weapon coating after its next successful hit."""
    coating = getattr(attacker, "_applied_toxin", None)
    if not isinstance(coating, dict) or coating.get("slot") != slot:
        return ToxinReactionResult()
    name = str(coating.get("name", "Toxin"))
    poison = getattr(target, "status_effects", {}).get("Poison")
    if poison is None or "Poison" in getattr(target, "status_immunity", []):
        preserved = has_skill(attacker, "Coating Conservation")
        if not preserved:
            attacker._applied_toxin = None
        return ToxinReactionResult(
            f"{target.name} is immune to {name}.\n",
            coating_preserved=preserved,
        )
    severe_chance = 0.40 if has_skill(attacker, "Black Lotus Mastery") else 0.25
    severe = bool(
        critical or (has_skill(attacker, "Potentiation") and random.random() < severe_chance)
    )
    severity = "severe" if severe else "standard"
    potency = 1.0
    if has_skill(attacker, "Lingering Venom"):
        potency += 0.20
    if has_skill(attacker, "Black Lotus Mastery"):
        potency += 0.25
    preserved = bool(has_skill(attacker, "Black Lotus Mastery") and random.random() < 0.25)
    if not preserved:
        attacker._applied_toxin = None
    if poison is not None:
        poison_tiers = {
            "Mild Toxin": ((3, 0.01), (4, 0.03)),
            "Neurotoxin": ((3, 0.01), (4, 0.03)),
            "Hemotoxin": ((4, 0.03), (5, 0.05)),
            "Amatoxin": ((5, 0.05), (6, 0.08)),
            "Myotoxin": ((5, 0.05), (6, 0.08)),
            "Necrotoxin": ((5, 0.05), (6, 0.08)),
        }
        turns, amount = poison_tiers.get(name, poison_tiers["Mild Toxin"])[int(severe)]
        if has_skill(attacker, "Lingering Venom"):
            turns += 1
        poison.active = True
        poison.duration = max(int(poison.duration or 0), turns)
        poison.extra = max(
            float(poison.extra or 0),
            max(1, int(target.health.max * amount * potency)),
        )
        poison.source = name
    messages = [f"{name} causes a {severity} reaction in {target.name}.\n"]
    if name == "Neurotoxin":
        if severe:
            effect = getattr(target, "status_effects", {}).get("Silence")
            if effect is not None:
                duration = 4 if has_skill(attacker, "Lingering Venom") else 3
                effect.active, effect.duration = True, max(int(effect.duration or 0), duration)
            damage = max(1, int(target.health.max * 0.05 * potency))
            target.health.current -= damage
            messages.append(f"Anaphylaxis deals {damage} damage and silences {target.name}.\n")
        elif random.random() < 0.5:
            numbness = getattr(target, "physical_effects", {}).get("Disarm")
            if numbness is not None:
                numbness.active, numbness.duration = True, max(int(numbness.duration or 0), 2)
                messages.append(f"Numbness makes {target.name} drop their weapon.\n")
    elif name == "Hemotoxin":
        key = "Bleed" if severe else "Blind"
        pool = target.physical_effects if key == "Bleed" else target.status_effects
        effect = pool.get(key)
        if effect is not None:
            duration = 5 if has_skill(attacker, "Lingering Venom") else 4
            effect.active, effect.duration = True, max(int(effect.duration or 0), duration)
    elif name == "Amatoxin":
        if severe and "Death" not in getattr(target, "status_immunity", []):
            target._toxin_death_turns = 4 if has_skill(attacker, "Lingering Venom") else 5
        else:
            for stat_name in ("Attack", "Defense"):
                effect = target.stat_effects.get(stat_name)
                if effect is not None:
                    effect.active = True
                    effect.duration = max(int(effect.duration or 0), 4)
                    effect.extra = min(int(effect.extra or 0), -3)
    elif name == "Myotoxin" and severe and "Stone" not in getattr(target, "status_immunity", []):
        target._toxin_petrify_turns = 2 if has_skill(attacker, "Lingering Venom") else 3
    elif name == "Necrotoxin" and severe and "Death" not in getattr(target, "status_immunity", []):
        target._toxin_death_turns = 1 if has_skill(attacker, "Lingering Venom") else 2
    elif name in {"Myotoxin", "Necrotoxin"}:
        effect = target.status_effects.get("Stun")
        if effect is not None and random.random() < 0.5:
            duration = 3 if has_skill(attacker, "Lingering Venom") else 2
            effect.active, effect.duration = True, max(int(effect.duration or 0), duration)
    attacker._death_mark_toxin_status = True
    return ToxinReactionResult(
        "".join(messages),
        status_applied=True,
        severe=severe,
        coating_preserved=preserved,
    )


def throwing_dagger_pack(character: Any) -> Any | None:
    """Return the first nonempty throwing-dagger pack."""
    return next(
        (
            pack
            for pack in _inventory_stack(character, "Throwing Daggers")
            if int(getattr(pack, "charges", 0) or 0) > 0
        ),
        None,
    )


def spend_throwing_dagger(character: Any, pack: Any, *, retrieve: bool) -> str:
    """Spend a thrown dagger, retaining it when it can be recovered."""
    if retrieve:
        return "The throwing dagger can be recovered.\n"
    pack.charges = max(0, int(getattr(pack, "charges", 0) or 0) - 1)
    pack.description = f"A pack used by Hidden Blade. Daggers remaining: {pack.charges}."
    if pack.charges <= 0:
        character.modify_inventory(pack, subtract=True)
    return f"{pack.charges} throwing daggers remain.\n"


def offhand_damage_multiplier(character: Any) -> float:
    return 0.90 if has_skill(character, "OffHand Excellence") else 0.75


def main_gauche_parry_bonus(character: Any) -> float:
    offhand = getattr(character, "equipment", {}).get("OffHand")
    return (
        0.12
        if (
            has_skill(character, "Main Gauche")
            and getattr(offhand, "subtyp", None) in {"Dagger", "Ninja Blade"}
        )
        else 0.0
    )


def record_live_and_learn(character: Any) -> None:
    if has_skill(character, "Live and Learn") and random.random() < 0.5:
        character._live_and_learn_stacks = min(
            3, int(getattr(character, "_live_and_learn_stacks", 0) or 0) + 1
        )


def live_and_learn_dodge_bonus(character: Any) -> float:
    return 0.05 * int(getattr(character, "_live_and_learn_stacks", 0) or 0)


def encounter_rate_multiplier(character: Any) -> float:
    """Reduce random encounters while Obscuration remains active."""
    obscured = int(getattr(character, "obscuration_steps", 0) or 0) > 0
    silent = int(getattr(character, "silent_walking_steps", 0) or 0) > 0
    return 0.5 if obscured or silent else 1.0


def toxic_precision_bonus(character: Any, slot: str | None = None) -> float:
    """Return coated-weapon critical chance from Toxic Precision."""
    coating = getattr(character, "_applied_toxin", None)
    coated_slot = coating.get("slot") if isinstance(coating, dict) else None
    return (
        0.10
        if (
            has_skill(character, "Toxic Precision")
            and coated_slot is not None
            and (slot is None or slot == coated_slot)
        )
        else 0.0
    )


def obscuration_accuracy_penalty(defender: Any) -> float:
    """Return the attack accuracy penalty imposed by active Obscuration."""
    return 0.15 if int(getattr(defender, "obscuration_steps", 0) or 0) > 0 else 0.0


def scroll_effectiveness_multiplier(character: Any) -> float:
    """Return Incantation Comprehension's scroll potency multiplier."""
    return 1.25 if has_skill(character, "Incantation Comprehension") else 1.0


def spell_dodge_bonus(character: Any) -> float:
    """Return Mystical Evasion's bonus against spells."""
    return 0.15 if has_skill(character, "Mystical Evasion") else 0.0


def aggressive_pursuit(
    character: Any,
    target: Any,
    *,
    rng: Any | None = None,
) -> tuple[bool, str]:
    """Resolve the advantaged attack granted when an enemy attempts to flee.

    Returns whether the target escaped and the resulting combat message.
    """
    if not has_skill(character, "Aggressive Pursuit"):
        return True, f"{target.name} flees from battle.\n"
    generator = rng or random
    contact = character.resolve_contact(target, typ="weapon", rng=generator)
    if not contact.hit:
        return True, f"{character.name}'s pursuit attack misses {target.name}.\n"
    message, _hit, _crit = character.weapon_damage(
        target,
        use_offhand=False,
        hit=True,
    )
    if not target.is_alive():
        return False, message + f"{character.name}'s pursuit stops {target.name} from fleeing.\n"
    return True, message + f"{target.name} survives the pursuit and flees.\n"


class Footpad(Job):
    """
    Promotion: Footpad -> Thief         -> Rogue
                       |
                       -> Inquisitor    -> Seeker
                       |
                       -> Assassin      -> Ninja
                       |
                       -> Spell Stealer -> Arcane Trickster
    """

    def __init__(self):
        super().__init__(
            name="Footpad",
            description="Footpads are agile and perceptive, with an natural ability of "
            "deftness. While more than capable of holding their own in hand-"
            "to-hand combat, they truly excel at subterfuge. Footpads are the"
            " only base class that can dual wield, albeit the offhand weapon "
            "must be a dagger.",
            str_plus=0,
            int_plus=0,
            wis_plus=0,
            con_plus=1,
            cha_plus=2,
            dex_plus=2,
            att_plus=2,
            def_plus=1,
            magic_plus=1,
            magic_def_plus=2,
            equipment={
                "Weapon": items.Dirk(),
                "OffHand": items.Dirk(),
                "Armor": items.PaddedArmor(),
            },
            restrictions={
                "Weapon": ["Fist", "Dagger", "Sword", "Club"],
                "OffHand": ["Fist", "Dagger"],
                "Armor": ["Light"],
            },
            pro_level=1,
        )
