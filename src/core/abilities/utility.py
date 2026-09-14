"""Utility, stealth, enhancement, summon, martial, and luck skills."""

from __future__ import annotations

import random
from typing import TYPE_CHECKING

from .base import (
    Class,
    Defensive,
    Enhance,
    MartialArts,
    Offensive,
    Skill,
    Stealth,
    Truth,
    _load_yaml_ability,
)

if TYPE_CHECKING:
    from typing import Any

    from ..character import Character


class Parry(Defensive):
    """Passive chance to deflect incoming melee damage without a shield."""

    def __init__(self):
        super().__init__(
            name="Parry",
            description=(
                "Passive: Chance to deflect some or all damage from an incoming "
                "melee attack. Cannot Parry while wielding a shield."
            ),
        )
        self.passive = True


class Riposte(Defensive):
    """Passive chance to counterattack after a successful Parry."""

    def __init__(self):
        super().__init__(
            name="Riposte",
            description=(
                "Passive: Chance to make an automatic main-hand counterattack "
                "after a successful Parry."
            ),
        )
        self.passive = True


class Quickstep(Defensive):
    """
    Passive ability; improves dodge chance via DEX scaling.

    This is intended as a Footpad-line defensive baseline so DEX-forward builds
    have a meaningful mitigation path without relying on flee mechanics.
    """

    def __init__(self):
        super().__init__(
            name="Quickstep",
            description="You fight light on your feet, improving your ability to evade attacks.",
        )
        self.passive = True


class NaturalAttunement(Skill):
    """Neutral Pathfinder support skill for both martial and arcane paths."""

    def __init__(self):
        super().__init__(
            name="Natural Attunement",
            description=("Attune to nature, increasing Defense and Magic Defense."),
        )
        self.subtyp = "Enhance"
        self.cost = 5
        self.target_self = True

    def use(self, user, target=None, **kwargs):
        result = super().use(user, user, **kwargs)
        if user.mana.current < self.cost:
            result.message = f"{user.name} does not have enough mana.\n"
            return result
        user.mana.current -= self.cost
        level = int(getattr(user.level, "level", user.level))
        extra = level // 2 + 1
        for stat_name in ("Defense", "Magic Defense"):
            effect = user.stat_effects[stat_name]
            effect.active = True
            effect.duration = max(effect.duration, 3)
            effect.extra = max(effect.extra, extra)
            result.effects_applied["Stat"].append(f"{stat_name} Buff")
        result.message = (
            f"{user.name} attunes to nature, gaining Defense and "
            "Magic Defense for three turns.\n"
        )
        return result


class Rally(Skill):
    """Warrior support skill that briefly fortifies both defenses."""

    def __init__(self):
        super().__init__(
            name="Rally",
            description=("Steel your resolve, increasing Defense and Magic Defense."),
        )
        self.subtyp = "Enhance"
        self.cost = 5
        self.target_self = True

    def use(self, user, target=None, **kwargs):
        result = super().use(user, user, **kwargs)
        if user.mana.current < self.cost:
            result.message = f"{user.name} does not have enough mana.\n"
            return result
        user.mana.current -= self.cost
        level = int(getattr(user.level, "level", user.level))
        extra = level // 2 + 1
        for stat_name in ("Defense", "Magic Defense"):
            effect = user.stat_effects[stat_name]
            effect.active = True
            effect.duration = max(effect.duration, 3)
            effect.extra = max(effect.extra, extra)
            result.effects_applied["Stat"].append(f"{stat_name} Buff")
        result.message = (
            f"{user.name} rallies, gaining Defense and Magic Defense for three turns.\n"
        )
        return result


class Adrenaline(Skill):
    """Emergency self-heal usable only below ten percent health."""

    def __init__(self):
        super().__init__(
            name="Adrenaline",
            description=(
                "When in dire need, trigger the body's reserves to restore up "
                "to 20% of maximum health while below 10% health."
            ),
        )
        self.subtyp = "Enhance"
        self.cost = 0
        self.target_self = True

    def is_available(self, user, target=None) -> bool:
        """Return whether the user is below Adrenaline's health threshold."""
        del target
        maximum = max(1, int(user.health.max))
        return int(user.health.current) * 10 < maximum

    def use(self, user, target=None, **kwargs):
        result = super().use(user, user, **kwargs)
        maximum = max(1, int(user.health.max))
        if int(user.health.current) * 10 >= maximum:
            result.message = f"{user.name} can only trigger Adrenaline below 10% health.\n"
            return result
        healing = max(1, int(maximum * 0.20))
        healing_multiplier = getattr(user, "healing_received_multiplier", None)
        if callable(healing_multiplier):
            healing = int(healing * healing_multiplier())
        actual = max(
            0,
            min(healing, maximum - int(user.health.current)),
        )
        user.health.current += actual
        if hasattr(user, "_emit_healing_event"):
            user._emit_healing_event(actual, source=self.name)
        result.healing = actual
        result.message = f"{user.name}'s adrenaline surges, restoring {actual} health.\n"
        return result


class HonedAttack(Class):
    """Passive training that increases the bonus damage of critical hits."""

    def __init__(self):
        super().__init__(
            name="Honed Attack",
            description=("Passive: Increase the damage bonus from critical hits by 25%."),
        )
        self.passive = True


class Commitment(Class):
    """Reward a Paladin-bound Warrior for focusing one opponent."""

    def __init__(self):
        super().__init__(
            name="Commitment",
            description=(
                "Passive: Consecutive attacks against the same target gain "
                "stacking accuracy and critical-strike damage. The focus ends "
                "after another combat action, changing targets, or combat. "
                "Choosing Commitment closes the other Warrior promotions."
            ),
        )
        self.passive = True


class ImprovedDefend(Class):
    """Improve the damage reduction granted by the Defend action."""

    def __init__(self):
        super().__init__(
            name="Improved Defend",
            description="Passive: Defend grants an additional 15% damage reduction.",
        )
        self.passive = True


class Upsurge(Skill):
    """Grant the combat party short-lived temporary health."""

    def __init__(self):
        super().__init__(
            name="Upsurge",
            description=(
                "Reach deep and grant all allies temporary health equal to "
                "15% of their maximum health for three turns."
            ),
        )
        self.cost = 8
        self.subtyp = "Enhance"
        self.target_self = True

    def use(self, user, target=None, **kwargs):
        result = super().use(user, user, **kwargs)
        if user.mana.current < self.cost:
            result.message = f"{user.name} does not have enough mana to use Upsurge.\n"
            return result
        user.mana.current -= self.cost
        allies = [user]
        engine = kwargs.get("battle_engine")
        summon = getattr(engine, "summon", None) if engine is not None else None
        if summon is not None and summon.is_alive():
            allies.append(summon)
        messages = []
        for ally in allies:
            amount = max(1, int(ally.health.max * 0.15))
            existing = getattr(ally, "temporary_health", None)
            if isinstance(existing, dict):
                amount = max(amount, int(existing.get("amount", 0) or 0))
            ally.temporary_health = {
                "amount": amount,
                "turns": 3,
                "source": self.name,
            }
            messages.append(f"{ally.name} gains {amount} temporary health.\n")
        result.message = "".join(messages)
        return result


class AchillesHeel(Skill):
    """Slow a target and leave it vulnerable to being knocked prone."""

    def __init__(self):
        super().__init__(
            name="Achilles Heel",
            description=(
                "Launch a targeted main-hand attack that cripples the target's "
                "speed and makes it easier to knock prone."
            ),
            weapon=True,
        )
        self.cost = 7
        self.subtyp = "Offensive"

    def use(self, user, target=None, **kwargs):
        result = super().use(user, target, **kwargs)
        if target is None:
            result.message = "Achilles Heel needs a target.\n"
            return result
        if user.mana.current < self.cost:
            result.message = f"{user.name} does not have enough mana.\n"
            return result
        user.mana.current -= self.cost
        before = int(target.health.current)
        message, hit, crit = user.weapon_damage(
            target,
            dmg_mod=0.90,
            use_offhand=False,
            accuracy_modifier=0.10,
        )
        result.hit = hit
        result.crit = crit if crit > 1 else None
        result.damage = max(0, before - int(target.health.current))
        if hit:
            effect = target.stat_effects["Speed"]
            penalty = max(2, int(target.stats.dex * 0.25))
            effect.active = True
            effect.duration = max(3, int(effect.duration or 0))
            effect.extra = min(-penalty, int(effect.extra or 0))
            effect.source = self.name
            target._achilles_heel_turns = 3
            result.effects_applied["Stat"].append("Speed Debuff")
            message += f"{target.name}'s speed is crippled and their footing becomes vulnerable.\n"
        result.message = message
        return result


class EvasiveGuard(Defensive):
    """
    Passive ability; stackable damage reduction against weapon hits (DEX-scaling).

    This is meant to give Footpad-line characters a way to mitigate damage without
    altering racial resistances or relying on flee mechanics.
    """

    def __init__(self):
        super().__init__(
            name="Evasive Guard",
            description="Each time you are hit, you learn and reduce future damage (stacks up to 3). "
            "Stacks reset when you dodge an attack.",
        )
        self.passive = True


class _FootpadPassive(Class):
    """Shared implementation for passive Footpad-tree nodes."""

    def __init__(self, name, description):
        super().__init__(name=name, description=description)
        self.passive = True


class AvoidTraps(_FootpadPassive):
    """Improve avoidance and mitigation when a trap triggers."""

    def __init__(self):
        super().__init__(
            "Avoid Traps",
            "Passive: Gain an increased chance to avoid a triggered trap's negative effect; halve it otherwise.",
        )


class DoOver(_FootpadPassive):
    """Occasionally reroll one missed attack per battle."""

    def __init__(self):
        super().__init__(
            "Do-over",
            "Passive: A missed attack has a chance to be rerolled once per battle.",
        )


class Serendipity(_FootpadPassive):
    """Increase ordinary enemy item-drop odds."""

    def __init__(self):
        super().__init__(
            "Serendipity",
            "Passive: Increase the chance of enemies dropping items.",
        )


class AggressivePursuit(_FootpadPassive):
    """Punish an enemy that attempts to flee."""

    def __init__(self):
        super().__init__(
            "Aggressive Pursuit",
            "Passive: Make an advantaged main-hand attack when an enemy attempts to flee; a survivor escapes.",
        )


class IncantationComprehension(_FootpadPassive):
    """Improve the effectiveness of spells cast from scrolls."""

    def __init__(self):
        super().__init__(
            "Incantation Comprehension",
            "Passive: Increase the effectiveness of scrolls by 25 percent.",
        )


class ManaDepletion(_FootpadPassive):
    """Drain mana with successful basic attacks."""

    def __init__(self):
        super().__init__(
            "Mana Depletion",
            "Passive: Basic attacks deplete mana from the target based on damage dealt.",
        )


class MysticalEvasion(_FootpadPassive):
    """Increase dodge chance specifically against spells."""

    def __init__(self):
        super().__init__(
            "Mystical Evasion",
            "Passive: Increase dodge chance against spells.",
        )


class StumbleUpon(Skill):
    """Attack, then trip the foe or risk falling prone on a complete miss."""

    def __init__(self):
        super().__init__(
            "Stumble Upon",
            "Attack the target and follow with a trip attempt. On a complete miss, pass a DEX check or fall prone.",
            weapon=True,
        )
        self.subtyp = "Offensive"
        self.cost = 5

    def use(self, user, target=None, **kwargs):
        result = super().use(user, target, **kwargs)
        if target is None:
            result.message = "Stumble Upon needs a target.\n"
            return result
        if user.mana.current < self.cost:
            result.message = f"{user.name} does not have enough mana.\n"
            return result
        user.mana.current -= self.cost
        before = int(target.health.current)
        message, hit, crit = user.weapon_damage(target, use_offhand=True)
        result.hit = hit
        result.crit = crit if crit > 1 else None
        result.damage = max(0, before - int(target.health.current))
        generator = kwargs.get("rng") or random
        if hit and not getattr(target, "flying", False):
            attack_roll = generator.randint(max(1, user.stats.dex // 2), max(1, user.stats.dex))
            defense_roll = generator.randint(
                max(1, target.stats.dex // 2), max(1, target.stats.dex)
            )
            speed_effect = target.stat_effects.get("Speed")
            if (
                speed_effect is not None
                and speed_effect.active
                and getattr(speed_effect, "source", "") == "Achilles Heel"
            ):
                defense_roll = max(0, defense_roll - 5)
            if attack_roll > defense_roll and not target.has_status_protection("Prone"):
                prone = target.physical_effects["Prone"]
                prone.active = True
                prone.duration = max(2, int(prone.duration or 0))
                prone.source = self.name
                result.effects_applied["Physical"].append("Prone")
                message += f"{target.name} is tripped and falls prone.\n"
            else:
                message += f"{target.name} keeps their footing.\n"
        elif not hit:
            dex_check = generator.randint(1, 20) <= int(user.stats.dex)
            if not dex_check:
                prone = user.physical_effects["Prone"]
                prone.active = True
                prone.duration = max(2, int(prone.duration or 0))
                prone.source = self.name
                result.effects_applied["Physical"].append("Prone")
                message += f"{user.name} stumbles and falls prone.\n"
            else:
                message += f"{user.name} recovers with a DEX check.\n"
        result.message = message
        return result


class Obscuration(Skill):
    """Use a censer outside combat to obscure the surrounding area."""

    def __init__(self):
        super().__init__(
            "Obscuration",
            "Cast outside combat with a Censer of Choking Ash to reduce encounters and enemy accuracy for 50 steps.",
        )
        self.combat = False
        self.subtyp = "Stealth"
        self.cost = 10

    def use(self, user, target=None, **kwargs):
        result = super().use(user, user, **kwargs)
        if "Censer of Choking Ash" not in getattr(user, "inventory", {}):
            result.message = "Obscuration requires a Censer of Choking Ash.\n"
            return result
        if user.mana.current < self.cost:
            result.message = f"{user.name} does not have enough mana.\n"
            return result
        from ..classes import footpad

        user.mana.current -= self.cost
        user.obscuration_steps = footpad.OBSCURATION_STEPS
        result.message = (
            f"{user.name} fills the surrounding area with choking ash for "
            f"{footpad.OBSCURATION_STEPS} steps.\n"
        )
        return result


class Disruption(Skill):
    """Strike a charging target and interrupt its charged ability."""

    def __init__(self):
        super().__init__(
            "Disruption",
            "Attack a charging target to interrupt its spell; a critical hit also Silences it for 2 turns.",
            weapon=True,
        )
        self.subtyp = "Offensive"
        self.cost = 10

    def use(self, user, target=None, **kwargs):
        result = super().use(user, target, **kwargs)
        if target is None:
            result.message = "Disruption needs a target.\n"
            return result
        if user.mana.current < self.cost:
            result.message = f"{user.name} does not have enough mana.\n"
            return result
        battle_engine = kwargs.get("battle_engine")
        charging_entry = getattr(battle_engine, "charging_ability", None)
        charging_skill = (
            charging_entry[2] if charging_entry and charging_entry[0] is target else None
        )
        if charging_skill is None:
            known_abilities = list(target.spellbook.get("Skills", {}).values()) + list(
                target.spellbook.get("Spells", {}).values()
            )
            charging_skill = next(
                (skill for skill in known_abilities if getattr(skill, "charging", False)),
                None,
            )
        if charging_skill is None:
            result.message = f"{target.name} is not charging an ability.\n"
            return result
        user.mana.current -= self.cost
        before = int(target.health.current)
        message, hit, crit = user.weapon_damage(target, use_offhand=False)
        result.hit = hit
        result.crit = crit if crit > 1 else None
        result.damage = max(0, before - int(target.health.current))
        if hit:
            cancel = getattr(charging_skill, "cancel_charge", None)
            message += (
                cancel(target)
                if callable(cancel)
                else f"{target.name}'s {charging_skill.name} is interrupted!\n"
            )
            charging_skill.charging = False
            if battle_engine is not None:
                battle_engine.charging_ability = None
                battle_engine.pending_actions.pop(battle_engine._actor_id_for(target), None)
            if crit > 1:
                silence = target.status_effects["Silence"]
                silence.active = True
                silence.duration = max(2, int(silence.duration or 0))
                silence.source = self.name
                result.effects_applied["Status"].append("Silence")
                message += f"{target.name} is Silenced for 2 turns.\n"
        result.message = message
        return result


class Disarm:
    """Disarm the enemy - data-driven (Batch 4)."""

    def __new__(cls):
        return _load_yaml_ability("disarm.yaml", cls_name="Disarm")


class Cover(Defensive):
    """
    Familiar only skill; stand in the way of an attack, protecting your master from harm.
    """

    def __init__(self):
        super().__init__(
            name="Cover",
            description="You stand in the way in the face of attack, protecting your master"
            " from harm.",
        )
        self.passive = True


class Goad:
    """Data-driven (goad.yaml)"""

    def __new__(cls):
        return _load_yaml_ability("goad.yaml", cls_name="Goad")


class Dishearten(Skill):
    """Timed shout that reduces an enemy's melee damage."""

    def __init__(self):
        super().__init__(
            name="Dishearten",
            description=(
                "Shout at an enemy, reducing the melee damage they deal by 25% " "for three turns."
            ),
        )
        self.subtyp = "Defensive"
        self.cost = 5

    def use(self, user, target=None, **kwargs):
        target = target or user
        result = super().use(user, target, **kwargs)
        if user.mana.current < self.cost:
            result.message = f"{user.name} does not have enough mana.\n"
            return result
        user.mana.current -= self.cost
        effect = target.stat_effects["Attack"]
        effect.active = True
        effect.duration = max(int(effect.duration or 0), 3)
        effect.extra = min(int(effect.extra or 0), 0)
        effect.source = "Dishearten"
        result.effects_applied["Stat"].append("Attack Debuff")
        result.message = (
            f"{user.name} disheartens {target.name}, reducing their melee "
            "damage for three turns.\n"
        )
        return result


# Stealth skills
class Backstab:
    """Data-driven (backstab.yaml)"""

    def __new__(cls):
        return _load_yaml_ability("backstab.yaml", cls_name="Backstab")


class PocketSand:
    """Data-driven (pocket_sand.yaml)"""

    def __new__(cls):
        return _load_yaml_ability("pocket_sand.yaml", cls_name="PocketSand")


class SleepingPowder:
    """Data-driven (sleeping_powder.yaml)"""

    def __new__(cls):
        return _load_yaml_ability("sleeping_powder.yaml", cls_name="SleepingPowder")


class KidneyPunch:
    """Data-driven (kidney_punch.yaml) - weapon hit + stun."""

    def __new__(cls):
        return _load_yaml_ability("kidney_punch.yaml", cls_name="KidneyPunch")


class SmokeScreen:
    """Data-driven (smoke_screen.yaml); player use consumes a Smoke Bomb."""

    def __new__(cls):
        return _load_yaml_ability("smoke_screen.yaml", cls_name="SmokeScreen")


class Steal:
    """Data-driven (steal.yaml)"""

    def __new__(cls):
        return _load_yaml_ability("steal.yaml", cls_name="Steal")


class Mug:
    """Data-driven (mug.yaml)"""

    def __new__(cls):
        return _load_yaml_ability("mug.yaml", cls_name="Mug")


class ShadowStrike:
    """Data-driven (shadow_strike.yaml)"""

    def __new__(cls):
        return _load_yaml_ability("shadow_strike.yaml", cls_name="ShadowStrike")


class Lockpick(Stealth):
    """
    Pick the lock on a chest, allowing you to open it.
    """

    def __init__(self):
        super().__init__(
            name="Lockpick",
            description="Unlock a locked chest while carrying a Lockpick Kit. The kit may lose durability or break.",
        )
        self.passive = True


class MasterLockpick(Lockpick):
    """
    Replaces Lockpick; pick the lock on a chest or door, allowing you to open it.
    """

    def __init__(self):
        super().__init__()
        self.name = "Master Lockpick"
        self.description = (
            "Unlock a locked chest or door while carrying a Lockpick Kit. "
            "Master technique lowers the kit's break chance."
        )
        self.passive = True


class PoisonStrike:
    """Data-driven (poison_strike.yaml) - weapon hit + poison."""

    def __new__(cls):
        return _load_yaml_ability("poison_strike.yaml", cls_name="PoisonStrike")


class SneakAttack:
    """Data-driven (sneak_attack.yaml)"""

    def __new__(cls):
        return _load_yaml_ability("sneak_attack.yaml", cls_name="SneakAttack")


# Enhance skills
class ImbueWeapon:
    """Data-driven (imbue_weapon.yaml)"""

    def __new__(cls):
        return _load_yaml_ability("imbue_weapon.yaml", cls_name="ImbueWeapon")


class ManaSlice:
    """Data-driven (mana_slice.yaml)"""

    def __new__(cls):
        return _load_yaml_ability("mana_slice.yaml", cls_name="ManaSlice")


class ManaSlice2:
    """Data-driven (mana_slice_2.yaml)"""

    def __new__(cls):
        return _load_yaml_ability("mana_slice_2.yaml", cls_name="ManaSlice2")


class DispelSlash:
    """Data-driven (dispel_slash.yaml)"""

    def __new__(cls):
        return _load_yaml_ability("dispel_slash.yaml", cls_name="DispelSlash")


class EnhanceBlade(Enhance):
    """Add base weapon damage scaled by the user's current mana percentage."""

    def __init__(self):
        super().__init__(
            name="Enhance Blade",
            description="Your blade thrums with arcane energy, amplifying its "
            "strength in proportion to your mana reserves. With each "
            "strike, you channel your magic into raw power, adding "
            "bonus damage equal to your weapon's base damage multiplied"
            " by your mana percentage.",
        )
        self.passive = True


class EnhanceArmor(Enhance):
    """Add equipped armor scaled by the user's missing mana percentage."""

    def __init__(self):
        super().__init__(
            name="Enhance Armor",
            description="Your armor adapts to your dwindling arcane reserves, "
            "fortifying itself as your mana depletes. The less mana "
            "you have, the greater your ' defense rating becomes. "
            "This protective enchantment ensures you can endure even "
            "when your magic is nearly exhausted.",
        )
        self.passive = True


class ManaShield:
    """Skill — data-driven (mana_shield.yaml)"""

    def __new__(cls):
        return _load_yaml_ability("mana_shield.yaml", cls_name="ManaShield")


class ManaShield2:
    """Skill — data-driven (mana_shield_2.yaml)"""

    def __new__(cls):
        return _load_yaml_ability("mana_shield_2.yaml", cls_name="ManaShield2")


class ElementalStrike:
    """Data-driven (elemental_strike.yaml)"""

    def __new__(cls):
        return _load_yaml_ability("elemental_strike.yaml", cls_name="ElementalStrike")


# Drain skills
class HealthDrain:
    """Skill — data-driven (health_drain.yaml)"""

    def __new__(cls):
        return _load_yaml_ability("health_drain.yaml", cls_name="HealthDrain")


class ManaDrain:
    """Skill — data-driven (mana_drain.yaml)"""

    def __new__(cls):
        return _load_yaml_ability("mana_drain.yaml", cls_name="ManaDrain")


class HealthManaDrain:
    """Skill — data-driven (health_mana_drain.yaml)"""

    def __new__(cls):
        return _load_yaml_ability("health_mana_drain.yaml", cls_name="HealthManaDrain")


class LifeTap:
    """Data-driven (life_tap.yaml)"""

    def __new__(cls):
        return _load_yaml_ability("life_tap.yaml", cls_name="LifeTap")


class ManaTap:
    """Data-driven (mana_tap.yaml)"""

    def __new__(cls):
        return _load_yaml_ability("mana_tap.yaml", cls_name="ManaTap")


# Class skills
class LearnSpell(Class):
    """
    Enables a diviner to learn rank 1 enemy spells.
    """

    def __init__(self):
        super().__init__(
            name="Learn Spell",
            description=(
                "Permanently learn an explicitly rank-1 hostile spell after "
                "witnessing it resolve successfully."
            ),
        )
        self.passive = True


class LearnSpell2(LearnSpell):
    """
    Enables a diviner to learn rank 2 enemy spells.
    - replaces Learn Spell
    """

    def __init__(self):
        super().__init__()
        self.description = (
            "Permanently learn explicitly ranked hostile spells up to rank 2 "
            "after witnessing them resolve successfully."
        )


class Transform:
    """Data-driven (transform.yaml)"""

    def __new__(cls):
        return _load_yaml_ability("transform.yaml", cls_name="Transform")


class Transform2:
    """Data-driven (transform2.yaml)"""

    def __new__(cls):
        return _load_yaml_ability("transform2.yaml", cls_name="Transform2")


class Transform3:
    """Data-driven (transform3.yaml)"""

    def __new__(cls):
        return _load_yaml_ability("transform3.yaml", cls_name="Transform3")


class Transform4:
    """Data-driven (transform4.yaml)"""

    def __new__(cls):
        return _load_yaml_ability("transform4.yaml", cls_name="Transform4")


class Totem:
    """Data-driven (totem.yaml)"""

    def __new__(cls):
        return _load_yaml_ability("totem.yaml", cls_name="Totem")


class MaelstromWeapon(Class):
    """
    Shaman passive ability: Maelstrom Weapon

    Each successive hit increases critical strike chance.
    The critical strike chance boost resets on a critical hit or a miss.

    Mechanics:
    - Gain 5% critical strike chance per consecutive hit
    - Max 6 consecutive hits = 30% bonus crit chance
    - Resets when: landing a critical strike, missing an attack, or being hit
    """

    def __init__(self):
        super().__init__(
            name="Maelstrom Weapon",
            description="Successive strikes channel maelstrom energy into your weapon, "
            "increasing critical strike chance with each hit. The energy "
            "dissipates on a critical strike or if you miss.",
        )
        self.passive = True
        self.crit_bonus_per_hit = 0.05  # 5% per hit
        self.max_hits = 6  # Max bonus of 30%


class Zephyrstrike(Offensive):
    """
    Passive martial timing; future tuning may hook this into wind/polearm crits.
    """

    def __init__(self):
        super().__init__(
            name="Zephyrstrike",
            description="You strike with the timing of a sudden gale.",
        )
        self.passive = True


class Retaliate(Defensive):
    """
    Passive counter-stance marker for Sentinel follow-up tuning.
    """

    def __init__(self):
        super().__init__(
            name="Retaliate",
            description="Your skill with a shield makes quick responses your forte.",
        )
        self.passive = True


class Chastise(Class):
    """Passive training that empowers Shield Slam."""

    def __init__(self):
        super().__init__(
            name="Chastise",
            description="Passive: Shield Slam deals 25% more damage.",
        )
        self.passive = True


class DefensiveRegen(Defensive):
    """
    Passive endurance marker for defensive regeneration follow-up tuning.
    """

    def __init__(self):
        super().__init__(
            name="Defensive Regen",
            description="You recover best when holding a defensive line; Regen is "
            "increased when defending.",
        )
        self.passive = True


class Posturing(Defensive):
    """
    Passive guard-presence marker for Crusader follow-up tuning.
    """

    def __init__(self):
        super().__init__(
            name="Posturing",
            description="You know how to present an impossible target; increased "
            "chance of parrying when defending.",
        )
        self.passive = True


class Familiar(Class):
    """
    Summon a familiar, a magic creature that serves as both a pet and a helper.
    """

    def __init__(self):
        super().__init__(
            name="Familiar",
            description="The warlock gains the assistance of a familiar, a magic serving "
            "as both a pet and a helper. The familiar's abilities rely on its"
            " master's statistics and resources.",
        )
        self.passive = True


class Familiar2(Familiar):

    def __init__(self):
        super().__init__()
        self.description = "The warlock's familiar gains strength, unlocking additional abilities."


class Familiar3(Familiar):

    def __init__(self):
        super().__init__()
        self.description = (
            "The warlock's familiar gains additional strength, unlocking even more abilities."
        )


class Tame(Class):

    def __init__(self):
        super().__init__(
            name="Tame",
            description="Attempt to bring a wild beast over to your side. You cannot "
            "perform any actions while channeling this ability.",
        )
        self.cost = 0

    def use(self, user: Character, target: Character | None = None, **kwargs: Any) -> str:
        from ..classes import ability_mechanics

        super().use(user, target, **kwargs)
        user.mana.current -= self.cost
        return ability_mechanics.attempt_tame(user, target, rng=kwargs.get("rng", random))


class HealSummon(Class):
    def __init__(self):
        super().__init__("Heal Summon", "Restore HP and MP to all owned summons.")
        self.cost = 18

    def use(self, user: Character, target: Character | None = None, **kwargs: Any) -> str:
        from ..classes import ability_mechanics

        super().use(user, target, **kwargs)
        user.mana.current -= self.cost
        return ability_mechanics.heal_all_summons(user)

    def use_out(self, game_or_user) -> str:
        user = getattr(game_or_user, "player_char", game_or_user)
        return self.use(user)


class RaiseSummon(Class):
    def __init__(self):
        super().__init__(
            "Raise Summon",
            "In combat, restore the Xenid that just fell. The rite refunds "
            "part of the conduit lost on death.",
        )
        self.cost = 100
        self.combat = True

    def use(self, user: Character, target: Character | None = None, **kwargs: Any) -> str:
        del target
        from ..classes import promotion_kits

        battle_engine = kwargs.get("battle_engine")
        success, message = promotion_kits.raise_fallen_xenid(
            user,
            battle_engine,
        )
        if success:
            user.mana.current -= self.cost
        return message

    def use_out(self, game_or_user) -> str:
        del game_or_user
        return "Raise Summon can only be used during combat.\n"


class AbsorbEssence(Class):
    """
    Currently 5% chance
    Different monster types improve different stats
    Reptile: increase strength
    Aberration: increase intelligence
    Slime: increase wisdom
    Construct: increase constitution
    Humanoid: increase charisma
    Insect: increase dexterity
    Animal: increase max health
    Monster: increase max mana
    Undead: increase level
    Dragon: increase gold
    """

    def __init__(self):
        super().__init__(
            name="Absorb Essence",
            description="When a Soulcatcher kills an enemy, there is a chance that "
            "they may absorb part of the enemy's essence. Different monster types "
            "improve different stats, allowing the Soulcatcher to grow stronger with"
            " each victory.",
        )
        self.passive = True


class Reveal:
    """Data-driven (reveal.yaml)"""

    def __new__(cls):
        return _load_yaml_ability("reveal.yaml", cls_name="Reveal")


class Inspect:
    """Data-driven (inspect.yaml)"""

    def __new__(cls):
        return _load_yaml_ability("inspect.yaml", cls_name="Inspect")


class ExploitWeakness:
    """Data-driven (exploit_weakness.yaml) - weakness detection + weapon."""

    def __new__(cls):
        return _load_yaml_ability("exploit_weakness.yaml", cls_name="ExploitWeakness")


class KeenEye(Truth):
    """
    Gives Inquisitor insights about their surroundings
    """

    def __init__(self):
        super().__init__(
            name="Keen Eye",
            description="As an Inquisitor, you can gain insights into your surroundings.",
        )
        self.passive = True


class ThirdEye(Truth):
    """Apply Intelligence to critical-hit and dodge calculations."""

    def __init__(self):
        super().__init__(
            name="Third Eye",
            description=(
                "Passive: Add Intelligence to critical-hit and dodge chance " "calculations."
            ),
        )
        self.passive = True


class Cartography(Truth):
    """
    Reveals minimap to Seeker, regardless of whether they have visited an area
    """

    def __init__(self):
        super().__init__(
            name="Cartography",
            description="Seekers are masters at map making and gain the ability to "
            "see all of the dungeon, regardless of whether an area has "
            "been visited.",
        )
        self.passive = True


# Martial Art Skills
class LegSweep:
    """Sweep the leg, trip the enemy - data-driven (Batch 4)."""

    def __new__(cls):
        return _load_yaml_ability("leg_sweep.yaml", cls_name="LegSweep")


class ChiHeal:
    """Skill — data-driven (chi_heal.yaml)"""

    def __new__(cls):
        return _load_yaml_ability("chi_heal.yaml", cls_name="ChiHeal")


class PurityBody:
    """Data-driven (purity_body.yaml)"""

    def __new__(cls):
        return _load_yaml_ability("purity_body.yaml", cls_name="PurityBody")


class PurityBody2:
    """Data-driven (purity_body2.yaml)"""

    def __new__(cls):
        return _load_yaml_ability("purity_body2.yaml", cls_name="PurityBody2")


class Evasion(MartialArts):

    def __init__(self):
        super().__init__(
            name="Evasion",
            description="You have become highly attuned at your surroundings, anticipating "
            "other's actions and increasing your chance to dodge attacks.",
        )
        self.passive = True


class PiousBounty(Class):
    """
    Passive divine-reward marker for future Healer-line bounty tuning.
    """

    def __init__(self):
        super().__init__(
            name="Pious Bounty",
            description="Your devotion draws extra providence from righteous victories.",
        )
        self.passive = True


class StaffConduit(Class):
    """
    Passive marker allowing Hierophants to channel a staff while bracing a shield.
    """

    def __init__(self):
        super().__init__(
            name="Staff Conduit",
            description="You can wield a two-handed staff with a shield and focus Devotion through staff strikes.",
        )
        self.passive = True


# Luck
class GoldToss:
    """Data-driven (gold_toss.yaml) - gold-based unblockable damage."""

    def __new__(cls):
        return _load_yaml_ability("gold_toss.yaml", cls_name="GoldToss")


class SlotMachine:
    """Data-driven (slot_machine.yaml)"""

    def __new__(cls):
        return _load_yaml_ability("slot_machine.yaml", cls_name="SlotMachine")


class Blackjack:
    """Data-driven (blackjack.yaml)"""

    def __new__(cls):
        return _load_yaml_ability("blackjack.yaml", cls_name="Blackjack")


# Power Up skills
