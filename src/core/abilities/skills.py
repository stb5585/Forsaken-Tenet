"""Core weapon, defensive, class, and composition skills."""

from __future__ import annotations

from typing import TYPE_CHECKING

from src.core.randomness import gameplay_random as random

from ..combat.combat_result import CombatResult, CombatResultGroup
from ..combat.targeting import TargetLossPolicy, TargetScope
from .base import (
    Class,
    Defensive,
    MartialArts,
    Offensive,
    Skill,
    _load_yaml_ability,
)

if TYPE_CHECKING:
    from typing import Any

    from ..character import Character


# Skills #
# Offensive
class ShieldSlam:
    """Data-driven (shield_slam.yaml) - str+shield damage + stun."""

    def __new__(cls):
        return _load_yaml_ability("shield_slam.yaml", cls_name="ShieldSlam")


class DoubleStrike:
    """Data-driven (double_strike.yaml)"""

    def __new__(cls):
        return _load_yaml_ability("double_strike.yaml", cls_name="DoubleStrike")


class TripleStrike:
    """Data-driven (triple_strike.yaml)"""

    replaces = "Double Strike"

    def __new__(cls):
        return _load_yaml_ability("triple_strike.yaml", cls_name="TripleStrike")


class FlurryBlades:
    """Data-driven (flurry_blades.yaml)"""

    replaces = "Triple Strike"

    def __new__(cls):
        return _load_yaml_ability("flurry_blades.yaml", cls_name="FlurryBlades")


class PiercingStrike:
    """Data-driven (piercing_strike.yaml)"""

    def __new__(cls):
        return _load_yaml_ability("piercing_strike.yaml", cls_name="PiercingStrike")


class TrueStrike:
    """Data-driven (true_strike.yaml)"""

    def __new__(cls):
        return _load_yaml_ability("true_strike.yaml", cls_name="TrueStrike")


class TruePiercingStrike:
    """Data-driven (true_piercing_strike.yaml)"""

    def __new__(cls):
        return _load_yaml_ability("true_piercing_strike.yaml", cls_name="TruePiercingStrike")


class Jump:
    """Data-driven (jump.yaml) - leap attack with full modification system."""

    def __new__(cls):
        return _load_yaml_ability("jump.yaml", cls_name="Jump")


class Doublecast:
    """Data-driven (doublecast.yaml) - cast 2 spells in a single turn."""

    def __new__(cls):
        return _load_yaml_ability("doublecast.yaml", cls_name="Doublecast")


class Triplecast:
    """Data-driven (triplecast.yaml) - cast 3 spells in a single turn."""

    def __new__(cls):
        return _load_yaml_ability("triplecast.yaml", cls_name="Triplecast")


class MortalStrike:
    """Data-driven (mortal_strike.yaml)"""

    def __new__(cls):
        return _load_yaml_ability("mortal_strike.yaml", cls_name="MortalStrike")


class MortalStrike2:
    """Data-driven (mortal_strike_2.yaml)"""

    def __new__(cls):
        return _load_yaml_ability("mortal_strike_2.yaml", cls_name="MortalStrike2")


class BattleCry:
    """Data-driven (battle_cry.yaml)"""

    def __new__(cls):
        return _load_yaml_ability("battle_cry.yaml", cls_name="BattleCry")


class Charge(Offensive):
    """Data-driven (charge.yaml)"""

    def __new__(cls):
        return _load_yaml_ability("charge.yaml", cls_name="Charge")


class DrivingThrust:
    """Data-driven thrust that exploits a stunned target."""

    def __new__(cls):
        return _load_yaml_ability("driving_thrust.yaml", cls_name="DrivingThrust")


class Cripple(Skill):
    """Damage a foe's weapon arm and temporarily reduce its melee damage."""

    def __init__(self):
        super().__init__(
            "Cripple",
            (
                "Launch a less accurate attack against the target's main hand. "
                "On hit, reduce its melee damage based on damage dealt."
            ),
            weapon=True,
        )
        self.cost = 6
        self.subtyp = "Offensive"

    def use(self, user, target=None, **kwargs):
        result = super().use(user, target, **kwargs)
        if target is None:
            result.message = "Cripple needs a target.\n"
            return result
        if user.mana.current < self.cost:
            result.message = f"{user.name} does not have enough mana to use Cripple.\n"
            return result
        if not getattr(target, "can_be_disarmed", lambda: False)():
            result.message = f"{target.name} has no vulnerable main-hand weapon.\n"
            return result

        user.mana.current -= self.cost
        before = int(target.health.current)
        message, hit, crit = user.weapon_damage(
            target,
            dmg_mod=0.90,
            use_offhand=False,
            accuracy_modifier=-0.20,
        )
        damage = max(0, before - int(target.health.current))
        result.hit = hit
        result.crit = crit if crit > 1 else None
        result.damage = damage
        if hit:
            effect = target.physical_effects["Cripple"]
            effect.active = True
            effect.duration = max(3, int(effect.duration or 0))
            effect.extra = max(
                float(effect.extra or 0),
                min(0.50, max(0.05, damage / max(1, target.health.max))),
            )
            effect.source = self.name
            message += (
                f"{target.name}'s weapon arm is crippled, reducing melee "
                f"damage by {round(effect.extra * 100)} percent.\n"
            )
        result.message = message
        return result


class DevastatingThrow(Skill):
    """Throw the main-hand weapon for massive damage and become disarmed."""

    def __init__(self):
        super().__init__(
            "Devastating Throw",
            (
                "Throw your main-hand weapon at the enemy for massive damage, "
                "disarming yourself afterward."
            ),
            weapon=True,
        )
        self.cost = 15
        self.subtyp = "Offensive"

    def use(self, user, target=None, **kwargs):
        result = super().use(user, target, **kwargs)
        if target is None:
            result.message = "Devastating Throw needs a target.\n"
            return result
        if user.mana.current < self.cost:
            result.message = f"{user.name} does not have enough mana to use Devastating Throw.\n"
            return result
        if not getattr(user, "can_be_disarmed", lambda: False)():
            result.message = f"{user.name} has no throwable main-hand weapon.\n"
            return result

        user.mana.current -= self.cost
        before = int(target.health.current)
        skills = getattr(user, "spellbook", {}).get("Skills", {})
        if "Boomerang Toss" in skills:
            messages: list[str] = []
            hits: list[bool] = []
            crits: list[int] = []
            for _strike in range(3):
                message, hit, crit = user.weapon_damage(
                    target,
                    dmg_mod=1.10,
                    use_offhand=False,
                )
                messages.append(message)
                hits.append(hit)
                crits.append(crit)
                if not target.is_alive():
                    break
            messages.append(f"{user.name}'s weapon completes its arc and returns to hand.\n")
            message = "".join(messages)
            hit = any(hits)
            crit = max(crits, default=1)
        else:
            message, hit, crit = user.weapon_damage(
                target,
                dmg_mod=2.50,
                use_offhand=False,
            )
            disarm = user.physical_effects["Disarm"]
            disarm.active = True
            disarm.duration = -1
            disarm.source = self.name
            message += f"{user.name} is disarmed after throwing the main-hand weapon.\n"
        result.hit = hit
        result.crit = crit if crit > 1 else None
        result.damage = max(0, before - int(target.health.current))
        result.message = message
        return result


class Momentum(Skill):
    """Chain two weapon hits into a combined dual-wield finisher."""

    def __init__(self):
        super().__init__(
            "Momentum",
            (
                "Attack with both weapons. If both connect, finish with a "
                "two-handed strike using their combined strength."
            ),
            weapon=True,
        )
        self.cost = 12
        self.subtyp = "Offensive"

    def use(self, user, target=None, **kwargs):
        result = super().use(user, target, **kwargs)
        if target is None:
            result.message = "Momentum needs a target.\n"
            return result
        main = user.equipment.get("Weapon")
        offhand = user.equipment.get("OffHand")
        if getattr(main, "typ", None) != "Weapon" or getattr(offhand, "typ", None) != "Weapon":
            result.message = "Momentum requires a weapon in each hand.\n"
            return result
        if user.mana.current < self.cost:
            result.message = f"{user.name} does not have enough mana to use Momentum.\n"
            return result

        from ..classes import promotion_kits

        user.mana.current -= self.cost
        user._death_mark_toxin_status = False
        before = int(target.health.current)
        main_message, main_hit, main_crit = user.weapon_damage(
            target,
            use_offhand=False,
            attack_slots=("Weapon",),
        )
        message = main_message
        offhand_hit = False
        offhand_crit = 1
        if target.is_alive():
            offhand_message, offhand_hit, offhand_crit = user.weapon_damage(
                target,
                use_offhand=True,
                attack_slots=("OffHand",),
            )
            message += offhand_message
        if main_hit and offhand_hit and target.is_alive():
            main_strength = max(0, int(getattr(main, "damage", 0) or 0))
            offhand_strength = max(0, int(getattr(offhand, "damage", 0) or 0))
            baseline = max(1, main_strength + int(user.combat.attack))
            combined = main_strength + offhand_strength + int(user.combat.attack)
            finisher_message, _finisher_hit, finisher_crit = user.weapon_damage(
                target,
                dmg_mod=max(1.0, combined / baseline),
                hit=True,
                use_offhand=False,
                attack_slots=("Weapon",),
            )
            message += f"{user.name}'s momentum becomes a two-handed finisher!\n"
            message += finisher_message
            offhand_crit = max(offhand_crit, finisher_crit)
        result.hit = bool(main_hit or offhand_hit)
        result.crit = max(main_crit, offhand_crit)
        result.damage = max(0, before - int(target.health.current))
        message += promotion_kits.resolve_death_mark_setup(
            user,
            target,
            self.name,
            hit=result.hit,
            status_applied=bool(getattr(user, "_death_mark_toxin_status", False)),
        )
        result.message = message
        return result


class Maim(Skill):
    """Cripple upgrade that temporarily makes a foe's main hand unusable."""

    replaces = "Cripple"

    def __init__(self):
        super().__init__(
            "Maim",
            (
                "Target the foe's main hand, rendering it unusable. A critical "
                "hit deals triple damage."
            ),
            weapon=True,
        )
        self.cost = 10
        self.subtyp = "Offensive"

    def use(self, user, target=None, **kwargs):
        result = super().use(user, target, **kwargs)
        if target is None:
            result.message = "Maim needs a target.\n"
            return result
        if user.mana.current < self.cost:
            result.message = f"{user.name} does not have enough mana to use Maim.\n"
            return result
        if not getattr(target, "can_be_disarmed", lambda: False)():
            result.message = f"{target.name} has no main hand that can be maimed.\n"
            return result

        user.mana.current -= self.cost
        before = int(target.health.current)
        message, hit, crit = user.weapon_damage(
            target,
            use_offhand=False,
            critical_multiplier=3,
        )
        result.hit = hit
        result.crit = crit if crit > 1 else None
        result.damage = max(0, before - int(target.health.current))
        if hit:
            effect = target.physical_effects["Maim"]
            effect.active = True
            effect.duration = max(3, int(effect.duration or 0))
            effect.source = self.name
            message += f"{target.name}'s main hand is maimed and unusable.\n"
        result.message = message
        return result


class _PassiveSkill(Class):
    def __init__(self, name: str, description: str) -> None:
        super().__init__(name=name, description=description)
        self.passive = True
        self.cost = 0


class DualWield(_PassiveSkill):
    """Unlock one-handed weapons in the off-hand slot."""

    def __init__(self):
        super().__init__(
            name="Dual Wield",
            description=(
                "Passive: Equip a one-handed weapon in the off hand, with an "
                "accuracy penalty to attacks made by either hand."
            ),
        )


class DualWieldExcellence(_PassiveSkill):
    """Remove Dual Wield's main-hand accuracy penalty."""

    def __init__(self):
        super().__init__(
            "Dual Wield Excellence",
            "Passive: Dual Wield no longer penalizes main-hand accuracy; the off-hand penalty remains.",
        )


class DualWieldMastery(_PassiveSkill):
    """Remove all Dual Wield accuracy penalties."""

    def __init__(self):
        super().__init__(
            "Dual Wield Mastery",
            "Passive: Dual Wield no longer penalizes accuracy with either hand.",
        )


class Duelist(_PassiveSkill):
    """Reward fighting with one one-handed weapon and an empty off hand."""

    def __init__(self):
        super().__init__(
            "Duelist",
            (
                "Passive: Gain accuracy, critical chance, and melee damage while "
                "wielding a one-handed weapon without a shield."
            ),
        )


class CrossBlock(_PassiveSkill):
    """Let a dual wielder cross weapons to block attacks."""

    def __init__(self):
        super().__init__(
            "Cross Block",
            (
                "Passive: Cross two weapons to block attacks. A complete block "
                "can disarm the attacker."
            ),
        )


class BlindFighting(_PassiveSkill):
    """Reduce both the application chance and accuracy penalty of Blind."""

    def __init__(self):
        super().__init__(
            "Blind Fighting",
            (
                "Passive: Reduce Blind's accuracy penalty and make Blind less "
                "likely to be inflicted."
            ),
        )


class Retort(_PassiveSkill):
    """Use Intelligence to improve Parry chance."""

    def __init__(self):
        super().__init__(
            "Retort",
            ("Passive: Add your Intelligence modifier to Parry chance."),
        )


class TwoHandedWeaponProficiency(_PassiveSkill):
    """Improve attacks made with two-handed weapons."""

    def __init__(self):
        super().__init__(
            "Two-Handed Weapon Proficiency",
            "Passive: Increase accuracy and damage while wielding a two-handed weapon.",
        )


class SwordAndBoard(_PassiveSkill):
    """Improve one-handed weapon attacks made while carrying a shield."""

    def __init__(self):
        super().__init__(
            "Sword & Board",
            (
                "Passive: Gain accuracy and weapon damage while wielding a "
                "one-handed weapon and a shield."
            ),
        )


class BrutishStrength(_PassiveSkill):
    """Scale critical damage with the equipped weapon discipline."""

    def __init__(self):
        super().__init__(
            "Brutish Strength",
            (
                "Passive: Increase critical damage based on the equipped weapon's "
                "discipline rank."
            ),
        )


class BlessedLight(_PassiveSkill):
    """Turn successful combat healing into a brief offensive blessing."""

    def __init__(self):
        super().__init__(
            "Blessed Light",
            (
                "Passive: Successfully casting a healing spell in combat "
                "grants +10 Attack for three turns."
            ),
        )


class Frenzy(Skill):
    """Enter a controlled three-turn Berserk state."""

    def __init__(self):
        super().__init__(
            "Frenzy",
            (
                "Enter a controlled Berserk state for three turns. You can only "
                "attack, but gain increased weapon damage and critical chance."
            ),
        )
        self.cost = 10
        self.subtyp = "Enhance"

    def use(self, user, target=None, **kwargs):
        result = super().use(user, user, **kwargs)
        if user.mana.current < self.cost:
            result.message = f"{user.name} does not have enough mana to use Frenzy.\n"
            return result
        user.mana.current -= self.cost
        effect = user.status_effects["Berserk"]
        effect.active = True
        effect.duration = 3
        effect.extra = 1
        effect.source = self.name
        result.message = (
            f"{user.name} enters a controlled frenzy for three turns and can " "only attack.\n"
        )
        return result


class RecklessOnslaught(Skill):
    """Trade mounting defense for offense with a parry vulnerability."""

    def __init__(self):
        super().__init__(
            "Reckless Onslaught",
            (
                "Unleash an all-out attack for double weapon damage. Gain "
                "stacking Attack Up and Defense Down; being parried knocks "
                "you prone."
            ),
            weapon=True,
        )
        self.cost = 14
        self.subtyp = "Offensive"

    def use(self, user, target=None, **kwargs):
        result = super().use(user, target, **kwargs)
        if target is None:
            result.message = "Reckless Onslaught needs a target.\n"
            return result
        if user.mana.current < self.cost:
            result.message = (
                f"{user.name} does not have enough mana to use " "Reckless Onslaught.\n"
            )
            return result
        if getattr(user.equipment.get("Weapon"), "typ", None) != "Weapon":
            result.message = f"{user.name} needs a main-hand weapon to use " "Reckless Onslaught.\n"
            return result

        user.mana.current -= self.cost
        before = int(target.health.current)
        message, hit, crit = user.weapon_damage(
            target,
            dmg_mod=2.0,
            use_offhand=False,
            attack_slots=("Weapon",),
        )
        for stat_name, modifier in (("Attack", 5), ("Defense", -5)):
            effect = user.stat_effects[stat_name]
            effect.extra = int(effect.extra or 0) + modifier if effect.active else modifier
            effect.active = True
            effect.duration = max(3, int(effect.duration or 0))
            effect.source = self.name
            result.effects_applied["Stat"].append(
                f"{stat_name} {'Buff' if modifier > 0 else 'Debuff'}"
            )
        message += f"{user.name}'s attack rises as their defense falls.\n"
        if getattr(user, "_last_attack_parried", False):
            prone = user.physical_effects["Prone"]
            prone.active = True
            prone.duration = max(2, int(prone.duration or 0))
            prone.source = self.name
            result.effects_applied["Physical"].append("Prone")
            message += f"{user.name} is knocked prone by the parry.\n"
        result.hit = hit
        result.crit = crit if crit > 1 else None
        result.damage = max(0, before - int(target.health.current))
        result.message = message
        return result


class PainTolerance(_PassiveSkill):
    """Resist bleeding and gain more healing from bandages."""

    def __init__(self):
        super().__init__(
            "Pain Tolerance",
            (
                "Passive: Halve bleed damage and its melee vulnerability. "
                "Bandages heal twice as much as normal."
            ),
        )


class HemorrhageThirst(_PassiveSkill):
    """Feed on an enemy's bleeding at the risk of a bloodlust crash."""

    def __init__(self):
        super().__init__(
            "Hemorrhage Thirst",
            (
                "Passive: Enemy bleed damage restores the same amount of "
                "health. Triggering this on more than two consecutive turns "
                "causes two turns of unconsciousness."
            ),
        )


class Fatality(Skill):
    """Risk an immediate counterattack to attempt a lethal weapon strike."""

    def __init__(self):
        super().__init__(
            "Fatality",
            (
                "Attempt to finish the enemy with double weapon damage. If the "
                "enemy survives, they immediately parry and counterattack. If "
                "the enemy dies, restore 15% of your maximum health."
            ),
            weapon=True,
        )
        self.cost = 16
        self.subtyp = "Offensive"

    def use(self, user, target=None, **kwargs):
        result = super().use(user, target, **kwargs)
        if target is None:
            result.message = "Fatality needs a target.\n"
            return result
        if user.mana.current < self.cost:
            result.message = f"{user.name} does not have enough mana to use Fatality.\n"
            return result
        if getattr(user.equipment.get("Weapon"), "typ", None) != "Weapon":
            result.message = f"{user.name} needs a main-hand weapon to use Fatality.\n"
            return result

        user.mana.current -= self.cost
        before = int(target.health.current)
        message, hit, crit = user.weapon_damage(
            target,
            dmg_mod=2.0,
            use_offhand=False,
            attack_slots=("Weapon",),
        )
        result.hit = hit
        result.crit = crit if crit > 1 else None
        result.damage = max(0, before - int(target.health.current))
        if target.is_alive():
            user._last_attack_parried = True
            message += (
                f"{target.name} survives Fatality, parries {user.name}, " "and counterattacks!\n"
            )
            counter_message, _counter_hit, _counter_crit = target.weapon_damage(
                user,
                use_offhand=False,
            )
            message += counter_message
        else:
            healing = min(
                max(0, int(user.health.max) - int(user.health.current)),
                max(1, int(user.health.max * 0.15)),
            )
            user.health.current += healing
            user._emit_healing_event(healing, source=self.name)
            if healing:
                message += f"{user.name} recovers {healing} health from the fatal blow.\n"
        result.message = message
        return result


class ComposedWrath(_PassiveSkill):
    """Retain tactical control while Frenzy is active."""

    def __init__(self):
        super().__init__(
            "Composed Wrath",
            "Passive: You can Attack or use Skills while under the effects of Frenzy.",
        )


class TectonicRift(Skill):
    """Crash two heavy weapons down to rupture the entire battlefield."""

    def __init__(self):
        super().__init__(
            "Tectonic Rift",
            "Slam both two-handed weapons into the ground, dealing massive Earth "
            "damage to all enemies and knocking grounded enemies prone. Flying "
            "enemies take partial damage from debris.",
            weapon=True,
        )
        self.cost = 24
        self.subtyp = "Offensive"
        self.target_scope = TargetScope.ALL_ENEMIES
        self.target_loss_policy = TargetLossPolicy.SNAPSHOT_ROSTER

    @staticmethod
    def _has_two_heavy_weapons(user) -> bool:
        return all(
            getattr(user.equipment.get(slot), "typ", None) == "Weapon"
            and int(getattr(user.equipment.get(slot), "handed", 0) or 0) == 2
            for slot in ("Weapon", "OffHand")
        )

    def is_available(self, user, target=None):
        del target
        return self._has_two_heavy_weapons(user)

    def use_group(self, user, targets, *, battle_engine, rng=None):
        del rng
        group = CombatResultGroup(
            action=self.name,
            actor_id=battle_engine.current_actor_id,
            target_scope=TargetScope.ALL_ENEMIES,
            target_ids=tuple(target_id for target_id, _target in targets),
        )
        if not self._has_two_heavy_weapons(user):
            group.message = "Tectonic Rift requires two two-handed weapons.\n"
            return group
        user.mana.current -= self.cost
        for target_id, target in targets:
            raw_damage = max(
                1,
                int(
                    user.check_mod("weapon", enemy=target) + user.check_mod("offhand", enemy=target)
                ),
            )
            if getattr(target, "flying", False):
                raw_damage = max(1, raw_damage // 2)
            _hit, message, damage = target.damage_reduction(
                raw_damage,
                user,
                typ="Earth",
            )
            target.health.current -= damage
            user._emit_damage_event(
                target,
                damage,
                damage_type="Earth",
                ability_name=self.name,
                attack_source="skill",
                source="skill",
            )
            if not getattr(target, "flying", False) and not target.has_status_protection("Prone"):
                prone = target.physical_effects["Prone"]
                prone.active = True
                prone.duration = max(2, int(prone.duration or 0))
                prone.source = self.name
                message += f"{target.name} is knocked prone by the rupture.\n"
            group.add(
                CombatResult(
                    action=self.name,
                    actor=user,
                    target=target,
                    hit=damage > 0,
                    damage=damage,
                    message=message,
                    actor_id=battle_engine.current_actor_id,
                    target_id=target_id,
                )
            )
        return group


class ThunderousVault(Skill):
    """Vault into a two-weapon strike that releases an electrical field."""

    def __init__(self):
        super().__init__(
            "Thunderous Vault",
            "Leap at an enemy and strike with both weapons in midair, releasing "
            "an expanding electrical field on landing that may stun enemies.",
            weapon=True,
        )
        self.cost = 18
        self.subtyp = "Offensive"

    def is_available(self, user, target=None):
        del target
        return TectonicRift._has_two_heavy_weapons(user)

    def use(self, user, target=None, **kwargs):
        del kwargs
        result = self._reset_result(actor=user, target=target)
        if target is None:
            result.message = "Thunderous Vault needs a target.\n"
            return result
        if not TectonicRift._has_two_heavy_weapons(user):
            result.message = "Thunderous Vault requires two two-handed weapons.\n"
            return result
        if user.mana.current < self.cost:
            result.message = f"{user.name} does not have enough mana to vault.\n"
            return result
        user.mana.current -= self.cost
        message = ""
        total_damage = 0
        for slot in ("Weapon", "OffHand"):
            before = int(target.health.current)
            attack_text, hit, _crit = user.weapon_damage(
                target,
                dmg_mod=1.0,
                use_offhand=(slot == "OffHand"),
                attack_slots=(slot,),
            )
            message += attack_text
            if hit:
                total_damage += max(0, before - int(target.health.current))
        encounter = getattr(user, "_combat_encounter", None)
        field_targets = [member.enemy for member in getattr(encounter, "living_members", ())] or [
            target
        ]
        for enemy in field_targets:
            raw = max(1, int(user.stats.strength * 0.75))
            _hit, field_message, damage = enemy.damage_reduction(
                raw,
                user,
                typ="Electric",
            )
            enemy.health.current -= damage
            total_damage += max(0, damage)
            message += field_message
            if random.random() < 0.25 and enemy.apply_stun(
                2,
                source=self.name,
                applier=user,
            ):
                message += f"{enemy.name} is stunned by the electrical field.\n"
            user._emit_damage_event(
                enemy,
                damage,
                damage_type="Electric",
                ability_name=self.name,
                attack_source="skill",
                source="skill",
            )
        result.hit = total_damage > 0
        result.damage = total_damage
        result.message = message
        return result


class WeaponSwap(Skill):
    """Equip a different carried weapon without leaving combat."""

    def __init__(self):
        super().__init__(
            "Weapon Swap",
            "Change to a different weapon during combat.",
        )
        self.selected_weapon = None

    def available_weapons(self, user):
        current = user.equipment.get("Weapon")
        return [
            item
            for stack in getattr(user, "inventory", {}).values()
            for item in stack
            if getattr(item, "typ", None) == "Weapon"
            and getattr(item, "name", None) != getattr(current, "name", None)
            and user.can_equip_item(item, "Weapon")
        ]

    def is_available(self, user, target=None):
        del target
        return bool(self.available_weapons(user))

    def use(self, user, target=None, **kwargs):
        del target
        weapon = kwargs.get("weapon") or self.selected_weapon
        self.selected_weapon = None
        choices = self.available_weapons(user)
        if weapon is None and choices:
            weapon = choices[0]
        if weapon not in choices:
            return "There is no different weapon available to equip.\n"
        old_name = user.equipment["Weapon"].name
        if not user.equip("Weapon", weapon):
            return f"{user.name} cannot equip {weapon.name}.\n"
        return f"{user.name} swaps {old_name} for {weapon.name}.\n"


class BoomerangToss(_PassiveSkill):
    """Return Devastating Throw after a multi-hit attack."""

    def __init__(self):
        super().__init__(
            "Boomerang Toss",
            (
                "Passive: Devastating Throw hits three times and returns the "
                "main-hand weapon instead of disarming you."
            ),
        )


class WeaponFocus(_PassiveSkill):
    """Warrior passive that improves weapon accuracy."""

    def __init__(self):
        super().__init__(
            "Weapon Focus",
            "Focused weapon practice increases weapon hit chance.",
        )


class MonkeyGrip(_PassiveSkill):
    def __init__(self):
        super().__init__(
            "Monkey Grip",
            "Your two-handed dual wielding becomes steadier, reducing its accuracy and damage penalties.",
        )


class MonkeyGrip2(_PassiveSkill):
    def __init__(self):
        super().__init__(
            "Monkey Grip 2",
            "Your two-handed dual wielding is fully stabilized, removing its accuracy and damage penalties.",
        )


class PolearmProficiency(_PassiveSkill):
    def __init__(self):
        super().__init__(
            "Polearm Proficiency",
            "You can wield a two-handed polearm with a shield, but your accuracy and damage suffer.",
        )


class PolearmExcellence(_PassiveSkill):
    replaces = "Polearm Proficiency"

    def __init__(self):
        super().__init__(
            "Polearm Excellence",
            "You can wield a two-handed polearm with a shield without accuracy or damage penalties.",
        )


class PolearmMastery(_PassiveSkill):
    replaces = "Polearm Excellence"

    def __init__(self):
        super().__init__(
            "Polearm Mastery",
            "Your one-handed polearm technique grants bonus accuracy and damage.",
        )


class LanceSweep(Skill):
    """Sweep a polearm across the target to suppress its speed."""

    def __init__(self):
        super().__init__(
            "Lance Sweep",
            (
                "Sweep a polearm through the target for normal weapon damage, "
                "reducing its Speed for two turns."
            ),
            weapon=True,
        )
        self.cost = 8
        self.subtyp = "Offensive"

    def use(self, user, target=None, **kwargs):
        result = super().use(user, target, **kwargs)
        if target is None:
            result.message = "Lance Sweep needs a target.\n"
            return result
        weapon = user.equipment.get("Weapon")
        if getattr(weapon, "subtyp", None) != "Polearm":
            result.message = "Lance Sweep requires a main-hand polearm.\n"
            return result
        if user.mana.current < self.cost:
            result.message = f"{user.name} does not have enough mana to use Lance Sweep.\n"
            return result

        user.mana.current -= self.cost
        before = int(target.health.current)
        message, hit, crit = user.weapon_damage(
            target,
            dmg_mod=1.0,
            use_offhand=False,
            attack_slots=("Weapon",),
        )
        result.hit = hit
        result.crit = crit if crit > 1 else None
        result.damage = max(0, before - int(target.health.current))
        if hit:
            speed = target.stat_effects["Speed"]
            penalty = max(2, int(getattr(user.stats, "dex", 0) or 0) // 10)
            speed.active = True
            speed.duration = max(2, int(speed.duration or 0))
            speed.extra = min(int(speed.extra or 0), -penalty)
            message += f"{target.name}'s Speed falls by {penalty} for two turns.\n"
        result.message = message
        return result


class DragonDive(Skill):
    """Spend Aerial Tempo on a scaling aerial weapon strike."""

    def __init__(self):
        super().__init__(
            "Dragon Dive",
            (
                "Consume all Aerial Tempo in a decisive aerial strike. Each "
                "stack increases weapon damage and accuracy."
            ),
            weapon=True,
        )
        self.cost = 18
        self.subtyp = "Offensive"

    def use(self, user, target=None, **kwargs):
        from ..classes import promotion_kits

        result = super().use(user, target, **kwargs)
        if target is None:
            result.message = "Dragon Dive needs a target.\n"
            return result
        weapon = user.equipment.get("Weapon")
        if getattr(weapon, "subtyp", None) not in {"Sword", "Polearm"}:
            result.message = "Dragon Dive requires a main-hand Sword or Polearm.\n"
            return result
        stacks = promotion_kits.current_aerial_tempo(user)
        if stacks <= 0:
            result.message = "Dragon Dive requires Aerial Tempo.\n"
            return result
        if user.mana.current < self.cost:
            result.message = f"{user.name} does not have enough mana to use Dragon Dive.\n"
            return result

        user.mana.current -= self.cost
        stacks = promotion_kits.spend_aerial_tempo(user)
        before = int(target.health.current)
        message, hit, crit = user.weapon_damage(
            target,
            dmg_mod=1.25 + (0.25 * stacks),
            use_offhand=False,
            accuracy_modifier=0.05 * stacks,
            attack_slots=("Weapon",),
        )
        result.hit = hit
        result.crit = crit if crit > 1 else None
        result.damage = max(0, before - int(target.health.current))
        message = f"{user.name} spends {stacks} Aerial Tempo on Dragon Dive.\n" f"{message}"
        if not hit:
            message += "Dragon Dive misses, but its Aerial Tempo is spent.\n"
        result.message = message
        return result


class _WeaponArt(Class):
    def __init__(self, name: str, weapon_type: str, description: str):
        super().__init__(name=name, description=description)
        art_level = (
            int(name[-1]) if len(name) >= 2 and name[-2] == " " and name[-1] in {"2", "3"} else 1
        )
        base_name = name[:-2] if art_level > 1 else name
        self.cost = {
            "Iron Palm": 6,
            "Hemorrhage": 7,
            "Riposte Line": 7,
            "Low Sweep": 7,
            "Guard Cleaver": 9,
            "Reaver's Mark": 9,
            "Brace": 8,
            "Anvil Strike": 10,
        }.get(base_name, 0)
        self.cost += 2 * (art_level - 1)
        self.art_level = art_level
        self.weapon = True
        self.required_weapon_type = weapon_type

    def use(
        self,
        user: Character,
        target: Character | None = None,
        **kwargs: Any,
    ) -> str:
        from ..classes import grandmaster

        super().use(user, target, **kwargs)
        if target is None:
            return f"{self.name} needs a target.\n"
        return grandmaster.perform_weapon_art(user, target, self.name)


class IronPalm(_WeaponArt):
    def __init__(self):
        super().__init__(
            "Iron Palm",
            "Fist",
            "A fist discipline art that disrupts the target's attack and hardens your stance as mastery grows.",
        )


class Hemorrhage(_WeaponArt):
    def __init__(self):
        super().__init__(
            "Hemorrhage",
            "Dagger",
            "A dagger discipline art that opens and worsens bleeding wounds.",
        )


class RiposteLine(_WeaponArt):
    def __init__(self):
        super().__init__(
            "Riposte Line",
            "Sword",
            "A sword discipline art that strikes and prepares a brief counter line.",
        )


class LowSweep(_WeaponArt):
    def __init__(self):
        super().__init__(
            "Low Sweep",
            "Club",
            "A club discipline art that disrupts footing with speed pressure and prone chances.",
        )


class GuardCleaver(_WeaponArt):
    def __init__(self):
        super().__init__(
            "Guard Cleaver",
            "Longsword",
            "A longsword discipline art that cuts through and weakens guard.",
        )


class ReaversMark(_WeaponArt):
    def __init__(self):
        super().__init__(
            "Reaver's Mark",
            "Battle Axe",
            "A battle axe discipline art that marks a foe to take increased weapon pressure.",
        )


class Brace(_WeaponArt):
    def __init__(self):
        super().__init__(
            "Brace",
            "Polearm",
            "A polearm discipline art that prepares a defensive counter stance.",
        )


class AnvilStrike(_WeaponArt):
    def __init__(self):
        super().__init__(
            "Anvil Strike",
            "Hammer",
            "A hammer discipline art that crushes defense and can suppress guard at mastery.",
        )


class IronPalm2(_WeaponArt):
    replaces = "Iron Palm"

    def __init__(self):
        super().__init__(
            "Iron Palm 2",
            "Fist",
            "A mastered palm strike with greater force and discipline scaling.",
        )


class Hemorrhage2(_WeaponArt):
    replaces = "Hemorrhage"

    def __init__(self):
        super().__init__(
            "Hemorrhage 2",
            "Dagger",
            "A mastered dagger cut with greater force before it opens a deep wound.",
        )


class RiposteLine2(_WeaponArt):
    replaces = "Riposte Line"

    def __init__(self):
        super().__init__(
            "Riposte Line 2",
            "Sword",
            "A mastered sword counter-line with greater damage and precision.",
        )


class LowSweep2(_WeaponArt):
    replaces = "Low Sweep"

    def __init__(self):
        super().__init__(
            "Low Sweep 2",
            "Club",
            "A mastered sweep with greater impact against the target's footing.",
        )


class GuardCleaver2(_WeaponArt):
    replaces = "Guard Cleaver"

    def __init__(self):
        super().__init__(
            "Guard Cleaver 2",
            "Longsword",
            "A mastered longsword blow with greater force against an enemy's guard.",
        )


class ReaversMark2(_WeaponArt):
    replaces = "Reaver's Mark"

    def __init__(self):
        super().__init__(
            "Reaver's Mark 2",
            "Battle Axe",
            "A mastered reaping strike that deepens the mark left on its target.",
        )


class Brace2(_WeaponArt):
    replaces = "Brace"

    def __init__(self):
        super().__init__(
            "Brace 2",
            "Polearm",
            "A mastered defensive brace with greater force behind its answering strike.",
        )


class AnvilStrike2(_WeaponArt):
    replaces = "Anvil Strike"

    def __init__(self):
        super().__init__(
            "Anvil Strike 2",
            "Hammer",
            "A mastered hammer blow with greater impact against armor and balance.",
        )


class IronPalm3(_WeaponArt):
    replaces = "Iron Palm 2"

    def __init__(self):
        super().__init__(
            "Iron Palm 3",
            "Fist",
            "A perfected palm strike backed by complete unarmed mastery.",
        )


class Hemorrhage3(_WeaponArt):
    replaces = "Hemorrhage 2"

    def __init__(self):
        super().__init__(
            "Hemorrhage 3",
            "Dagger",
            "A perfected dagger cut that opens a devastating wound.",
        )


class RiposteLine3(_WeaponArt):
    replaces = "Riposte Line 2"

    def __init__(self):
        super().__init__(
            "Riposte Line 3",
            "Sword",
            "A perfected sword counter-line with masterful precision.",
        )


class LowSweep3(_WeaponArt):
    replaces = "Low Sweep 2"

    def __init__(self):
        super().__init__(
            "Low Sweep 3",
            "Club",
            "A perfected sweep that overwhelms the target's footing.",
        )


class GuardCleaver3(_WeaponArt):
    replaces = "Guard Cleaver 2"

    def __init__(self):
        super().__init__(
            "Guard Cleaver 3",
            "Longsword",
            "A perfected longsword blow that tears through an enemy's guard.",
        )


class ReaversMark3(_WeaponArt):
    replaces = "Reaver's Mark 2"

    def __init__(self):
        super().__init__(
            "Reaver's Mark 3",
            "Battle Axe",
            "A perfected reaping strike that leaves an inescapable mark.",
        )


class Brace3(_WeaponArt):
    replaces = "Brace 2"

    def __init__(self):
        super().__init__(
            "Brace 3",
            "Polearm",
            "A perfected brace that turns defense into a masterful counter.",
        )


class AnvilStrike3(_WeaponArt):
    replaces = "Anvil Strike 2"

    def __init__(self):
        super().__init__(
            "Anvil Strike 3",
            "Hammer",
            "A perfected hammer blow that crushes armor and balance.",
        )


class FavoredEnemy(Class):
    def __init__(self):
        super().__init__(
            "Favored Enemy",
            "Mark the current enemy type as your quarry. Keeping the same mark "
            "builds tracking mastery; changing quarry carries over only some practice.",
        )
        self.cost = 0

    def use(self, user: Character, target: Character | None = None, **kwargs: Any) -> str:
        from ..classes import ability_mechanics

        super().use(user, target, **kwargs)
        user.mana.current -= self.cost
        return ability_mechanics.mark_favored_enemy(user, target)


class FinalAssault(_PassiveSkill):
    def __init__(self):
        super().__init__(
            "Final Assault",
            "When a melee blow would kill you, counterattack; if the attacker falls, stabilize at 1 HP.",
        )


class LastStand(_PassiveSkill):
    def __init__(self):
        super().__init__(
            "Last Stand",
            "Increase defense and block strength at the expense of attack power.",
        )


class _MartialStrike(MartialArts):
    status_name: str | None = None
    damage_mod: float = 1.0

    def __init__(self, name: str, description: str, cost: int = 8):
        super().__init__(name=name, description=description, weapon=True)
        self.cost = cost

    def _has_martial_weapon(self, user: Character) -> bool:
        return any(
            getattr(user.equipment.get(slot), "subtyp", None) in {"Fist", "None"}
            for slot in ("Weapon", "OffHand")
        )

    def use(self, user: Character, target: Character | None = None, **kwargs: Any) -> str:
        super().use(user, target, **kwargs)
        if target is None:
            return "There is no target.\n"
        if not self._has_martial_weapon(user):
            return f"{user.name} needs a free hand or fist weapon to use {self.name}.\n"
        user.mana.current -= self.cost
        from ..classes import promotion_kits

        accuracy = promotion_kits.ki_accuracy_bonus(user, self.name)
        msg, hit, _crit = user.weapon_damage(
            target,
            dmg_mod=self.damage_mod,
            use_offhand=False,
            accuracy_modifier=accuracy,
        )
        if (
            hit
            and self.status_name
            and target.is_alive()
            and not target.has_status_protection(self.status_name)
        ):
            apply_status = True
            duration = 2
            control_bonus = promotion_kits.ki_control_bonus(user, self.name)
            if self.name == "Suplex":
                actor_roll = random.randint(user.stats.strength // 2, user.stats.strength)
                target_roll = random.randint(target.stats.con // 2, target.stats.con)
                apply_status = actor_roll > target_roll
                if not apply_status and control_bonus:
                    apply_status = random.random() < control_bonus
            if apply_status:
                effect_dict = target.effect_handler(self.status_name)
                effect_dict[self.status_name].active = True
                effect_dict[self.status_name].duration = max(
                    effect_dict[self.status_name].duration,
                    duration + int(control_bonus > 0),
                )
                msg += f"{target.name} is affected by {self.status_name.lower()}.\n"
        return msg


class Uppercut(_MartialStrike):
    damage_mod = 1.25

    def __init__(self):
        super().__init__("Uppercut", "A rising martial strike that deals increased damage.", 8)


class Headbutt(_MartialStrike):
    status_name = "Stun"
    damage_mod = 1.0

    def __init__(self):
        super().__init__("Headbutt", "A close strike that can stun.", 6)


class DrunkenBrawler(_PassiveSkill):
    def __init__(self):
        super().__init__(
            "Drunken Brawler",
            "After using a potion, your next turn gains bonus damage and critical chance.",
        )


class Hyakuretsukyaku(_MartialStrike):
    def __init__(self):
        super().__init__("Hyakuretsukyaku", "A rushing flurry of kicks.", 14)

    def use(self, user: Character, target: Character | None = None, **kwargs: Any) -> str:
        MartialArts.use(self, user, target, **kwargs)
        if target is None:
            return "There is no target.\n"
        if not self._has_martial_weapon(user):
            return f"{user.name} needs a free hand or fist weapon to use {self.name}.\n"
        user.mana.current -= self.cost
        msg = ""
        for _ in range(4):
            from ..classes import promotion_kits

            hit_msg, _hit, _crit = user.weapon_damage(
                target,
                dmg_mod=0.45,
                use_offhand=False,
                accuracy_modifier=promotion_kits.ki_accuracy_bonus(user, self.name),
            )
            msg += hit_msg
            if not target.is_alive():
                break
        return msg


class SpinningBackElbow(_MartialStrike):
    status_name = "Blind"
    damage_mod = 1.2

    def __init__(self):
        super().__init__("Spinning Back Elbow", "A turning blow that can blind.", 10)


class Suplex(_MartialStrike):
    status_name = "Prone"
    damage_mod = 1.35

    def __init__(self):
        super().__init__("Suplex", "A crushing throw that can knock the target prone.", 12)


class Hadouken(_MartialStrike):
    damage_mod = 1.4

    def __init__(self):
        super().__init__("Hadouken", "A focused chi strike delivered at range.", 16)


# Defensive skills
class ShieldBlock(Defensive):
    """
    Passive ability; increases damage blocked by 25% when using a shield
    """

    def __init__(self):
        super().__init__(
            name="Shield Block",
            description="You are much more proficient with a shield than most, "
            "increasing the amount of damage blocked.",
        )
        self.passive = True


class StealSpell(Class):
    """Steal an enemy spell onto a Blank Scroll."""

    def __init__(self):
        super().__init__(
            name="Steal Spell",
            description="Inscribes one of the target's spells onto a Blank Scroll.",
        )
        self.cost = 8

    def use(
        self,
        user: Character,
        target: Character | None = None,
        **kwargs: Any,
    ) -> str:
        from ..classes import spell_stealer

        if target is None:
            return "There is no spell to steal.\n"
        if getattr(getattr(user, "cls", None), "name", "") not in {
            "Spell Stealer",
            "Arcane Trickster",
        }:
            return f"{user.name} cannot steal spells.\n"
        if not getattr(user, "inventory", {}).get("Blank Scroll", []):
            return f"{user.name} needs a Blank Scroll to steal a spell.\n"
        if not spell_stealer.eligible_spell_classes(target):
            return f"{target.name} has no stealable spell.\n"
        effective_cost = self.cost
        if spell_stealer.has_stolen_magic_talent(
            user,
            "spell-stealer.arcane-ledger",
        ):
            effective_cost -= 2
        if user.mana.current < effective_cost:
            return f"{user.name} does not have enough mana to use Steal Spell!\n"
        user.mana.current -= effective_cost
        _success, message = spell_stealer.steal_spell(
            user,
            target,
            rng=kwargs.get("rng", random),
        )
        if _success:
            from ..classes import promotion_kits

            message += promotion_kits.gain_stolen_charge(user, "Steal Spell")
        return message


class StealSpell2(Class):
    """Chance to permanently learn one stealable enemy spell."""

    def __init__(self):
        super().__init__(
            name="Steal Spell 2",
            description="Attempt to permanently learn one of the target's stealable spells.",
        )
        self.cost = 22

    def use(self, user: Character, target: Character | None = None, **kwargs: Any) -> str:
        from ..classes import spell_stealer

        if target is None:
            return "There is no spell to steal.\n"
        if getattr(getattr(user, "cls", None), "name", "") != "Arcane Trickster":
            return f"{user.name} cannot permanently steal spells.\n"
        spell_classes = spell_stealer.eligible_spell_classes(target)
        spell_classes = [
            spell_cls
            for spell_cls in spell_classes
            if spell_cls().name not in user.spellbook.get("Spells", {})
        ]
        if not spell_classes:
            return f"{target.name} has no new spell to learn.\n"
        if user.mana.current < self.cost:
            return f"{user.name} does not have enough mana to use Steal Spell 2!\n"
        user.mana.current -= self.cost
        mastery = spell_stealer.has_stolen_magic_talent(
            user,
            "arcane-trickster.master-thief",
        )
        chance = 0.20 + ((user.stats.intel + user.stats.dex) * 0.01)
        chance = min(0.90 if mastery else 0.75, chance + (0.15 if mastery else 0.0))
        rng = kwargs.get("rng", random)
        if rng.random() > chance:
            return f"{user.name} fails to bind the stolen spell.\n"
        spell_cls = rng.choice(spell_classes)
        spell = spell_cls()
        user.spellbook["Spells"][spell.name] = spell
        from ..classes import class_rings, promotion_kits

        class_rings.activate_spell_steal_buff(user)

        message = (
            f"{user.name} permanently learns {spell.name}.\n"
            + promotion_kits.gain_stolen_charge(user, "Steal Spell 2")
        )
        if spell_stealer.has_stolen_magic_talent(
            user,
            "arcane-trickster.mnemonic-larceny",
        ):
            restored = min(self.cost // 2, user.mana.max - user.mana.current)
            user.mana.current += restored
            message += f"Mnemonic Larceny restores {restored} MP.\n"
        return message


class StealAsWell(Class):
    """Marker skill used by the Steal As Well combat action."""

    def __init__(self):
        super().__init__(
            name="Steal As Well",
            description="Cast an attack spell and attempt to steal after it lands.",
        )
        self.cost = 0

    def use(self, user: Character, target: Character | None = None, **kwargs: Any) -> str:
        return "Choose Steal As Well from the combat action menu to weave theft into a spell.\n"


class SongValor(Class):
    """Begin Song of Valor."""

    def __init__(self):
        super().__init__(
            name="Song of Valor",
            description="Perform a 3-turn song that raises weapon and magic damage.",
        )
        self.cost = 0

    def use(self, user: Character, target: Character | None = None, **kwargs: Any) -> str:
        from ..classes import bard

        _success, message = bard.start_song(user, "Valor")
        return message


class SongShelter(Class):
    """Begin Song of Shelter."""

    def __init__(self):
        super().__init__(
            name="Song of Shelter",
            description="Perform a 3-turn song that reduces incoming damage.",
        )
        self.cost = 0

    def use(self, user: Character, target: Character | None = None, **kwargs: Any) -> str:
        from ..classes import bard

        _success, message = bard.start_song(user, "Shelter")
        return message


class SongRenewal(Class):
    """Begin Song of Renewal."""

    def __init__(self):
        super().__init__(
            name="Song of Renewal",
            description="Perform a 3-turn song that restores HP and MP each turn.",
        )
        self.cost = 0

    def use(self, user: Character, target: Character | None = None, **kwargs: Any) -> str:
        from ..classes import bard

        _success, message = bard.start_song(user, "Renewal")
        return message


class Compose(Class):
    """Create one matching advanced-song sheet through a single action."""

    def __init__(self):
        super().__init__(
            name="Compose",
            description=(
                "Choose an advanced song and compose it onto one-use sheet "
                "music with its matching equipped instrument."
            ),
        )
        self.cost = 0
        self.combat = False

    def use(
        self,
        user: Character,
        target: Character | None = None,
        **kwargs: Any,
    ) -> str:
        del target
        from ..classes import bard

        song = kwargs.get("song")
        if song is None:
            options = bard.available_compositions(user)
            if not options:
                return f"{user.name} has no composition for the equipped instrument.\n"
            names = ", ".join(options)
            return f"Choose a composition: {names}.\n"
        _success, message = bard.compose_sheet_music(
            user,
            str(song),
            rng=kwargs.get("rng", random),
        )
        return message

    def use_out(self, game_or_user, *, song: str | None = None) -> str:
        user = getattr(game_or_user, "player_char", game_or_user)
        return self.use(user, song=song)


class _ComposeSong(Class):
    sheet_cls_name = ""

    def __init__(self, name: str, sheet_cls_name: str):
        song_name = name.removeprefix("Compose ")
        super().__init__(
            name=name,
            description=f"Compose {song_name} into one-use sheet music from the character menu.",
        )
        self.cost = 0
        self.song_name = song_name
        self.sheet_cls_name = sheet_cls_name

    def use(self, user: Character, target: Character | None = None, **kwargs: Any) -> str:
        from ..classes import bard

        _success, message = bard.compose_sheet_music(user, self.song_name)
        return message

    def use_out(self, game_or_user) -> str:
        user = getattr(game_or_user, "player_char", game_or_user)
        return self.use(user)


class ComposeBattleHymn(_ComposeSong):
    def __init__(self):
        super().__init__("Compose Battle Hymn", "BattleHymnSheet")


class ComposeOdeToTheRamparts(_ComposeSong):
    def __init__(self):
        super().__init__("Compose Ode to the Ramparts", "RampartsOdeSheet")


class ComposeSymphonyOfDisfunction(_ComposeSong):
    def __init__(self):
        super().__init__("Compose Symphony of Disfunction", "DysfunctionSymphonySheet")


class ComposeLowDefenseRhapsody(_ComposeSong):
    def __init__(self):
        super().__init__("Compose Low-defense-ian Rhapsody", "LowDefenseRhapsodySheet")


class ComposeSlowRide(_ComposeSong):
    def __init__(self):
        super().__init__("Compose Slow Ride", "SlowRideSheet")


class ComposeBonesThugsHarmony(_ComposeSong):
    def __init__(self):
        super().__init__("Compose Bones, Thugs, and Harmony", "BonesThugsHarmonySheet")


class ComposeScoresAndScoresScore(_ComposeSong):
    def __init__(self):
        super().__init__("Compose Scores and Scores Score", "ScoresAndScoresScoreSheet")


class ComposeGoldTrigger(_ComposeSong):
    def __init__(self):
        super().__init__("Compose Gold Trigger", "GoldTriggerSheet")


class ComposeChorusTime(_ComposeSong):
    def __init__(self):
        super().__init__("Compose Chorus Time", "ChorusTimeSheet")
