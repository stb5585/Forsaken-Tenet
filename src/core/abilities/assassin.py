"""Assassin abilities and toxin crafting actions."""

from __future__ import annotations

from typing import Any

from src.core.randomness import gameplay_random as random

from .base import Skill


class _AssassinPassive(Skill):
    def __init__(self, name: str, description: str):
        super().__init__(name, f"Passive: {description}")
        self.passive = True
        self.subtyp = "Passive"


class TwistTheKnife(_AssassinPassive):
    def __init__(self):
        super().__init__("Twist the Knife", "A successful Kidney Punch stun triggers Backstab.")


class OffHandExcellence(_AssassinPassive):
    def __init__(self):
        super().__init__("OffHand Excellence", "Reduces the damage penalty for off-hand attacks.")


class ForGoodMeasure(_AssassinPassive):
    def __init__(self):
        super().__init__(
            "For Good Measure", "A successful Disarm is followed by an off-hand attack."
        )


class Cutthroat(_AssassinPassive):
    def __init__(self):
        super().__init__("Cutthroat", "Critical Backstab attacks have a chance to kill instantly.")


class Surprise(_AssassinPassive):
    def __init__(self):
        super().__init__(
            "Surprise!",
            "While Obscuration is active, an initiative-winning opening attack gains accuracy, "
            "critical chance, and 50% experience if it kills.",
        )


class MainGauche(_AssassinPassive):
    def __init__(self):
        super().__init__("Main Gauche", "Daggers and Ninja blades in the off hand improve Parry.")


class LiveAndLearn(_AssassinPassive):
    def __init__(self):
        super().__init__(
            "Live and Learn", "Critical hits taken can increase dodge, stacking three times."
        )


class ApplyToxin(Skill):
    exploration_cast = True

    def __init__(self):
        super().__init__("Apply Toxin", "Apply an available toxin to an equipped dagger.")
        self.combat = False
        self.subtyp = "Utility"

    def cast_out(self, game_or_user: Any) -> str:
        from ..classes import footpad

        user = getattr(game_or_user, "player_char", game_or_user)
        return footpad.apply_toxin(user)

    def use(self, user: Any, target: Any = None, **kwargs: Any):
        del target, kwargs
        result = self._reset_result(actor=user)
        result.message = self.cast_out(user)
        return result


class MakeToxin(Skill):
    exploration_cast = True

    def __init__(self):
        super().__init__(
            "Make Toxin", "Craft an available venom or Deathcap into its matching toxin."
        )
        self.combat = False
        self.subtyp = "Utility"

    def cast_out(self, game_or_user: Any) -> str:
        from ..classes import footpad

        user = getattr(game_or_user, "player_char", game_or_user)
        return footpad.make_toxin(user)

    def use(self, user: Any, target: Any = None, **kwargs: Any):
        del target, kwargs
        result = self._reset_result(actor=user)
        result.message = self.cast_out(user)
        return result


class ResistDeath(Skill):
    exploration_cast = True

    def __init__(self):
        super().__init__("Resist Death", "Increase resistance to Death magic for a duration.")
        self.combat = False
        self.subtyp = "Enhance"
        self.cost = 15

    def cast_out(self, game_or_user: Any) -> str:
        user = getattr(game_or_user, "player_char", game_or_user)
        user.resist_death_steps = 50
        return f"{user.name} steels themselves against Death magic.\n"

    def use(self, user: Any, target: Any = None, **kwargs: Any):
        del target, kwargs
        result = self._reset_result(actor=user)
        result.message = self.cast_out(user)
        return result


class Distract(Skill):
    def __init__(self):
        super().__init__(
            "Distract",
            "Create a diversion that costs the target two turns; attacking restores its focus.",
        )
        self.cost = 8
        self.subtyp = "Control"

    def use(self, user: Any, target: Any = None, **kwargs: Any):
        del kwargs
        result = self._reset_result(actor=user, target=target)
        if target is None:
            result.message = "Distract needs a target.\n"
        elif user.mana.current < self.cost:
            result.message = f"{user.name} does not have enough mana.\n"
        else:
            user.mana.current -= self.cost
            target._distracted_turns = 2
            result.message = f"{target.name} loses focus for two turns.\n"
        return result


class Disembowel(Skill):
    def __init__(self):
        super().__init__(
            "Disembowel",
            "Death Mark Setup: slash with both weapons and open a bleeding wound.",
            weapon=True,
        )
        self.cost = 12
        self.subtyp = "Offensive"

    def use(self, user: Any, target: Any = None, **kwargs: Any):
        del kwargs
        result = self._reset_result(actor=user, target=target)
        offhand = getattr(user, "equipment", {}).get("OffHand")
        if target is None or getattr(offhand, "typ", None) != "Weapon":
            result.message = "Disembowel requires a target and two weapons.\n"
            return result
        if user.mana.current < self.cost:
            result.message = f"{user.name} does not have enough mana.\n"
            return result
        from ..classes import promotion_kits

        user.mana.current -= self.cost
        user._death_mark_toxin_status = False
        before = int(target.health.current)
        message, hit, crit = user.weapon_damage(target, attack_slots=("Weapon", "OffHand"))
        if hit and target.is_alive() and "Bleed" in target.physical_effects:
            bleed = target.physical_effects["Bleed"]
            bleed.active = True
            bleed.duration = max(int(bleed.duration or 0), 4)
            bleed.extra = max(int(bleed.extra or 0), max(1, (before - target.health.current) // 8))
            message += f"{target.name} is disemboweled and bleeding.\n"
        result.hit, result.crit = hit, crit
        result.damage = max(0, before - int(target.health.current))
        message += promotion_kits.resolve_death_mark_setup(
            user,
            target,
            self.name,
            hit=hit,
            status_applied=(
                bool(getattr(user, "_death_mark_toxin_status", False))
                or bool(hit and target.is_alive() and "Bleed" in target.physical_effects)
            ),
        )
        result.message = message
        return result


class HiddenBlade(Skill):
    def __init__(self):
        super().__init__(
            "Hidden Blade",
            "Attack normally, then follow with a concealed throwing dagger.",
            weapon=True,
        )
        self.cost = 8
        self.subtyp = "Offensive"

    def use(self, user: Any, target: Any = None, **kwargs: Any):
        del kwargs
        from ..classes import footpad

        result = self._reset_result(actor=user, target=target)
        if target is None:
            result.message = "Hidden Blade needs a target.\n"
            return result
        ammunition = footpad.throwing_dagger_pack(user)
        if ammunition is None:
            result.message = "Hidden Blade requires Throwing Daggers.\n"
            return result
        if user.mana.current < self.cost:
            result.message = f"{user.name} does not have enough mana.\n"
            return result
        user.mana.current -= self.cost
        before = int(target.health.current)
        message, hit, crit = user.weapon_damage(target, use_offhand=False)
        if target.is_alive():
            thrown = max(1, int(user.check_mod("attack", enemy=target) * 0.65))
            thrown = max(1, int(thrown * (1 - target.check_mod("resist", typ="Physical"))))
            target.health.current -= thrown
            message += f"{user.name}'s hidden dagger strikes for {thrown} damage.\n"
            hit = True
        message += footpad.spend_throwing_dagger(user, ammunition, retrieve=random.random() < 0.35)
        result.hit, result.crit = hit, crit
        result.damage = max(0, before - int(target.health.current))
        result.message = message
        return result


def _valid_finisher_weapon(user: Any, *, allow_fist: bool = False) -> bool:
    weapon = getattr(user, "equipment", {}).get("Weapon")
    allowed = {"Dagger", "Ninja Blade"}
    if allow_fist:
        allowed.add("Fist")
    return getattr(weapon, "subtyp", None) in allowed


class Deathblow(Skill):
    """Assassin's precise single-target Death Mark finisher."""

    def __init__(self):
        super().__init__(
            "Deathblow",
            "Death Mark Finisher: spend all marks on one accurate, critical strike.",
            weapon=True,
        )
        self.cost = 15
        self.subtyp = "Offensive"

    def use(self, user: Any, target: Any = None, **kwargs: Any):
        del kwargs
        from ..classes import promotion_kits

        result = self._reset_result(actor=user, target=target)
        if target is None or not _valid_finisher_weapon(user, allow_fist=True):
            result.message = "Deathblow requires a target and a dagger, fist, or Ninja Blade.\n"
            return result
        if user.mana.current < self.cost:
            result.message = f"{user.name} does not have enough mana.\n"
            return result
        marks, message = promotion_kits.begin_death_mark_finisher(user, target, self.name)
        if marks <= 0:
            result.message = message
            return result
        user.mana.current -= self.cost
        before = int(target.health.current)
        attack_message, hit, crit = user.weapon_damage(
            target,
            use_offhand=False,
            accuracy_modifier=0.10 * marks,
            critical_chance_modifier=0.10 * marks,
        )
        base_damage = max(0, before - int(target.health.current))
        message += attack_message
        message += promotion_kits.resolve_weapon_finisher(
            user,
            target,
            self.name,
            marks,
            base_damage,
            mana_cost=self.cost,
            hit=hit,
        )
        result.hit, result.crit = hit, crit
        result.damage = max(0, before - int(target.health.current))
        result.message = message
        return result


class MarkedShuriken(Skill):
    """Ranged Ninja setup attack using the throwing-dagger supply."""

    def __init__(self):
        super().__init__(
            "Marked Shuriken",
            "Death Mark Setup: throw a concealed blade that may Blind the target.",
            weapon=True,
        )
        self.cost = 12
        self.subtyp = "Stealth"

    def use(self, user: Any, target: Any = None, **kwargs: Any):
        del kwargs
        from ..classes import footpad, promotion_kits

        result = self._reset_result(actor=user, target=target)
        ammunition = footpad.throwing_dagger_pack(user)
        if target is None or ammunition is None:
            result.message = "Marked Shuriken requires a target and Throwing Daggers.\n"
            return result
        if user.mana.current < self.cost:
            result.message = f"{user.name} does not have enough mana.\n"
            return result
        user.mana.current -= self.cost
        user._death_mark_toxin_status = False
        before = int(target.health.current)
        message, hit, crit = user.weapon_damage(target, dmg_mod=0.80, use_offhand=False)
        status_applied = False
        if hit and target.is_alive() and "Blind" not in getattr(target, "status_immunity", ()):
            blind = target.status_effects.get("Blind")
            if blind is not None and random.random() < 0.30:
                blind.active = True
                blind.duration = max(int(blind.duration or 0), 2)
                status_applied = True
                message += f"{target.name} is blinded by Marked Shuriken.\n"
        status_applied = status_applied or bool(getattr(user, "_death_mark_toxin_status", False))
        message += promotion_kits.resolve_death_mark_setup(
            user,
            target,
            self.name,
            hit=hit,
            status_applied=status_applied,
        )
        message += footpad.spend_throwing_dagger(user, ammunition, retrieve=random.random() < 0.35)
        result.hit, result.crit = hit, crit
        result.damage = max(0, before - int(target.health.current))
        result.message = message
        return result


class ThousandCuts(Skill):
    """Five-hit Ninja Death Mark finisher."""

    def __init__(self):
        super().__init__(
            "Thousand Cuts",
            "Death Mark Finisher: spend all marks to sharpen five rapid blade strikes.",
            weapon=True,
        )
        self.cost = 40
        self.subtyp = "Offensive"

    def use(self, user: Any, target: Any = None, **kwargs: Any):
        del kwargs
        from ..classes import promotion_kits

        result = self._reset_result(actor=user, target=target)
        if target is None or not _valid_finisher_weapon(user):
            result.message = "Thousand Cuts requires a target and a dagger or Ninja Blade.\n"
            return result
        if user.mana.current < self.cost:
            result.message = f"{user.name} does not have enough mana.\n"
            return result
        marks, message = promotion_kits.begin_death_mark_finisher(user, target, self.name)
        if marks <= 0:
            result.message = message
            return result
        user.mana.current -= self.cost
        before = int(target.health.current)
        any_hit = False
        crit = 1
        for index in range(5):
            if not target.is_alive():
                break
            attack_message, hit, strike_crit = user.weapon_damage(
                target,
                dmg_mod=0.55,
                use_offhand=False,
                accuracy_modifier=(0.05 * marks) - (0.08 * index),
            )
            message += attack_message
            any_hit = any_hit or hit
            crit = max(crit, strike_crit)
        base_damage = max(0, before - int(target.health.current))
        message += promotion_kits.resolve_weapon_finisher(
            user,
            target,
            self.name,
            marks,
            base_damage,
            mana_cost=self.cost,
            hit=any_hit,
        )
        result.hit, result.crit = any_hit, crit
        result.damage = max(0, before - int(target.health.current))
        result.message = message
        return result


class DeathSentence(Skill):
    """Ninja weapon strike followed by a Death-resistance contest."""

    def __init__(self):
        super().__init__(
            "Death Sentence",
            "Death Mark Finisher: strike once, then test Death resistance for execution.",
            weapon=True,
        )
        self.cost = 50
        self.subtyp = "Death"

    def use(self, user: Any, target: Any = None, **kwargs: Any):
        del kwargs
        from ..classes import promotion_kits

        result = self._reset_result(actor=user, target=target)
        if target is None or not _valid_finisher_weapon(user):
            result.message = "Death Sentence requires a target and a dagger or Ninja Blade.\n"
            return result
        if user.mana.current < self.cost:
            result.message = f"{user.name} does not have enough mana.\n"
            return result
        marks, message = promotion_kits.begin_death_mark_finisher(user, target, self.name)
        if marks <= 0:
            result.message = message
            return result
        user.mana.current -= self.cost
        before = int(target.health.current)
        attack_message, hit, crit = user.weapon_damage(target, use_offhand=False)
        message += attack_message
        base_damage = max(0, before - int(target.health.current))
        message += promotion_kits.resolve_weapon_finisher(
            user,
            target,
            self.name,
            marks,
            base_damage,
            mana_cost=self.cost,
            hit=hit,
        )
        if hit and target.is_alive():
            killed, immune = promotion_kits.resolve_death_contest(user, target, marks=marks)
            if killed:
                message += f"{target.name}'s Death Sentence is carried out.\n"
            elif immune:
                message += f"{target.name} is immune to Death Sentence's execution.\n"
            else:
                message += f"{target.name} resists Death Sentence's execution.\n"
        result.hit, result.crit = hit, crit
        result.damage = max(0, before - int(target.health.current))
        result.message = message
        return result


class FindTraps(_AssassinPassive):
    def __init__(self):
        super().__init__("Find Traps", "Warns before entering some adjacent armed traps.")


class SmashAndGrab(_AssassinPassive):
    def __init__(self):
        super().__init__("Smash and Grab", "Mug strikes three times and may stun after two hits.")


class ExecutionRhythm(_AssassinPassive):
    def __init__(self):
        super().__init__(
            "Execution Rhythm", "Marked finishers refund 10% of their MP cost per mark."
        )


class ToxicPrecision(_AssassinPassive):
    def __init__(self):
        super().__init__("Toxic Precision", "Coated weapons gain 10% critical chance.")


class LingeringVenom(_AssassinPassive):
    def __init__(self):
        super().__init__(
            "Lingering Venom", "Improves toxin potency and ordinary reaction duration."
        )


class CoatingConservation(_AssassinPassive):
    def __init__(self):
        super().__init__("Coating Conservation", "Poison immunity no longer consumes a coating.")


class Potentiation(_AssassinPassive):
    def __init__(self):
        super().__init__("Potentiation", "Noncritical toxin reactions can become severe.")


class BlackLotusMastery(_AssassinPassive):
    def __init__(self):
        super().__init__(
            "Black Lotus Mastery", "Perfects toxin severity, potency, and coating retention."
        )


class ShadowEvasion(_AssassinPassive):
    def __init__(self):
        super().__init__("Shadow Evasion", "Retains dodge briefly after concealment breaks.")


class GhostStep(_AssassinPassive):
    def __init__(self):
        super().__init__("Ghost Step", "Once per combat, a dodge or parry restores concealment.")


class ShadowCounter(_AssassinPassive):
    def __init__(self):
        super().__init__("Shadow Counter", "A Riposte after parrying gains accuracy and damage.")


class Untouchable(_AssassinPassive):
    def __init__(self):
        super().__init__("Untouchable", "Once per combat, reroll a failed weapon avoidance.")


class SilentWalking(Skill):
    exploration_cast = True

    def __init__(self):
        super().__init__("Silent Walking", "Halve random encounters for 50 exploration steps.")
        self.cost = 20
        self.combat = False
        self.subtyp = "Stealth"

    def cast_out(self, game_or_user: Any) -> str:
        user = getattr(game_or_user, "player_char", game_or_user)
        if user.mana.current < self.cost:
            return f"{user.name} does not have enough mana.\n"
        user.mana.current -= self.cost
        user.silent_walking_steps = 50
        return f"{user.name} begins walking without a sound.\n"

    def use(self, user: Any, target: Any = None, **kwargs: Any):
        del target, kwargs
        result = self._reset_result(actor=user)
        result.message = self.cast_out(user)
        return result
