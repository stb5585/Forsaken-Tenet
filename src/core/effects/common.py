"""Reusable combinators and shared effects."""

from __future__ import annotations

import math
from typing import TYPE_CHECKING, Callable

from .base import Effect

if TYPE_CHECKING:
    from ..character import Character
    from ..combat.combat_result import CombatResult


class ConditionalEffect(Effect):
    """
    An effect that only applies if a condition is met.

    Example: "Deal extra damage if target is poisoned"
    """

    def __init__(self, condition: Callable, effect: Effect):
        """
        Args:
            condition: Function that takes (actor, target, result) and returns bool
            effect: The effect to apply if condition is True
        """
        self.condition = condition
        self.effect = effect

    def apply(self, actor: Character, target: Character, result: CombatResult) -> None:
        """Apply the effect only if the condition is met."""
        if self.condition(actor, target, result):
            self.effect.apply(actor, target, result)


class CompositeEffect(Effect):
    """
    Combines multiple effects into a single effect.

    Example: Fireball deals damage AND applies burn
    """

    def __init__(self, effects: list[Effect]):
        """
        Args:
            effects: List of effects to apply
        """
        self.effects = effects

    def apply(self, actor: Character, target: Character, result: CombatResult) -> None:
        """Apply all effects in sequence."""
        for effect in self.effects:
            effect.apply(actor, target, result)


class ChanceEffect(Effect):
    """
    An effect that has a chance to apply based on probability.

    Example: "30% chance to stun"
    """

    def __init__(self, effect: Effect, chance: float):
        """
        Args:
            effect: The effect to potentially apply
            chance: Probability of applying (0.0 to 1.0)
        """
        self.effect = effect
        self.chance = chance

    def apply(self, actor: Character, target: Character, result: CombatResult) -> None:
        """Apply the effect based on random chance."""
        import random

        if random.random() < self.chance:
            self.effect.apply(actor, target, result)
            result.extra["chance_effect_triggered"] = True
        else:
            result.extra["chance_effect_triggered"] = False


class StatContestEffect(Effect):
    """
    An effect that only triggers if the actor wins a stat contest vs the target.

    The contest rolls ``random(actor_lo, actor_stat // actor_div)`` against
    ``random(target_stat // target_lo_div, target_stat // target_hi_div)``
    and applies the inner effect when the actor wins.

    When ``use_crit_multiplier`` is True, the actor's stat value is multiplied
    by the crit value from the last damage roll before computing the range.

    When ``actor_lo_divisor`` is set, the actor's low roll is
    ``actor_stat // actor_lo_divisor`` instead of 0.

    When ``base_chance`` is set, the contest instead uses a direct chance
    adjusted by the actor-target stat difference and clamped to the configured
    minimum and maximum.

    Example: Fire DOT triggers on ``intel//2 > wisdom//4..wisdom``
    Example: Corruption DOT uses ``(charisma*crit)//2..(charisma*crit) > wisdom//2..wisdom``
    """

    def __init__(
        self,
        effect: Effect,
        actor_stat: str = "intel",
        actor_divisor: int = 2,
        target_stat: str = "wisdom",
        target_lo_divisor: int = 4,
        target_hi_divisor: int = 1,
        actor_lo_divisor: int | None = None,
        use_crit_multiplier: bool = False,
        base_chance: float | None = None,
        chance_per_point: float = 0.0,
        minimum_chance: float = 0.0,
        maximum_chance: float = 1.0,
    ):
        self.effect = effect
        self.actor_stat = actor_stat
        self.actor_divisor = actor_divisor
        self.target_stat = target_stat
        self.target_lo_divisor = target_lo_divisor
        self.target_hi_divisor = target_hi_divisor
        self.actor_lo_divisor = actor_lo_divisor
        self.use_crit_multiplier = use_crit_multiplier
        self.base_chance = base_chance
        self.chance_per_point = chance_per_point
        self.minimum_chance = minimum_chance
        self.maximum_chance = maximum_chance

    def apply(self, actor: Character, target: Character, result: CombatResult) -> None:
        import random

        a_val = getattr(actor.stats, self.actor_stat, 10)
        t_val = getattr(target.stats, self.target_stat, 10)

        if self.use_crit_multiplier:
            crit = result.extra.get("last_crit", 1)
            a_val = int(a_val * crit)

        if self.base_chance is not None:
            chance = self.base_chance + ((a_val - t_val) * self.chance_per_point)
            try:
                from ..classes import astromancer

                chance += astromancer.threaded_bonus(actor, "status")
            except Exception:
                pass
            chance += max(0.0, float(getattr(actor, "_totem_surge_reliability", 0.0) or 0.0))
            chance = max(self.minimum_chance, min(self.maximum_chance, chance))
            result.extra["stat_contest_chance"] = chance
            if random.random() < chance:
                self.effect.apply(actor, target, result)
                result.extra["stat_contest_won"] = True
            else:
                result.extra["stat_contest_won"] = False
            return

        if self.actor_lo_divisor is not None:
            roll_lo = max(0, a_val // self.actor_lo_divisor)
        else:
            roll_lo = 0

        roll_actor = random.randint(roll_lo, max(1, a_val // self.actor_divisor))
        roll_target = random.randint(
            max(0, t_val // self.target_lo_divisor),
            max(1, t_val // self.target_hi_divisor),
        )

        contest_success = roll_actor > roll_target
        if not contest_success:
            try:
                from ..classes import astromancer

                contest_success = random.random() < astromancer.threaded_bonus(
                    actor,
                    "status",
                )
            except Exception:
                pass
        if not contest_success:
            contest_success = random.random() < max(
                0.0,
                float(getattr(actor, "_totem_surge_reliability", 0.0) or 0.0),
            )
        if contest_success:
            self.effect.apply(actor, target, result)
            result.extra["stat_contest_won"] = True
        else:
            result.extra["stat_contest_won"] = False


class DynamicDotEffect(Effect):
    """
    A DOT effect whose damage_per_tick is computed from the last damage dealt.

    Used by fire spells that set DOT damage to ``random(damage//4, damage//2)``.
    """

    FIRE_DOT_ACTIONS = {
        "Firebolt",
        "Fireball",
        "Firestorm",
        "Scorch",
        "Molten Rock",
        "Volcano",
        "Hellfire",
    }

    def __init__(
        self,
        dot_type: str = "DOT",
        duration: int = 2,
        damage_lo_fraction: float = 0.25,
        damage_hi_fraction: float = 0.5,
    ):
        self.dot_type = dot_type
        self.duration = duration
        self.damage_lo_fraction = damage_lo_fraction
        self.damage_hi_fraction = damage_hi_fraction

    def apply(self, actor: Character, target: Character, result: CombatResult) -> None:
        import random

        last_damage = result.extra.get("last_damage", 0)
        lo = max(1, int(last_damage * self.damage_lo_fraction))
        hi = max(lo, int(last_damage * self.damage_hi_fraction))
        dmg = random.randint(lo, hi)
        duration = self.duration
        if result.action == "Corruption" and (
            "Persistent Corruption" in getattr(actor, "spellbook", {}).get("Skills", {})
        ):
            duration = max(4, duration)
            dmg = max(1, int(dmg * 1.25))
        if (
            result.action in self.FIRE_DOT_ACTIONS
            and int(getattr(target, "demon_grease_turns", 0) or 0) > 0
        ):
            duration += 1
            dmg = max(1, int(dmg * 1.50))

        target.magic_effects[self.dot_type].active = True
        target.magic_effects[self.dot_type].duration = max(
            duration, target.magic_effects[self.dot_type].duration
        )
        target.magic_effects[self.dot_type].extra = max(
            dmg, target.magic_effects[self.dot_type].extra
        )
        if self.dot_type == "DOT":
            target.magic_effects[self.dot_type].source = (
                "Burn" if result.action in self.FIRE_DOT_ACTIONS else result.action
            )
        else:
            target.magic_effects[self.dot_type].source = self.dot_type
        result.effects_applied["Magic"].append(f"DOT ({self.dot_type})")

        try:
            actor._emit_status_event(
                target,
                self.dot_type,
                applied=True,
                duration=target.magic_effects[self.dot_type].duration,
                source=result.action,
            )
        except Exception:
            pass
        if result.action == "Corruption":
            from ..classes import warlock

            warlock.mark_corruption(actor, target)


class DynamicExtraDamageEffect(Effect):
    """
    Deals bonus damage computed as a fraction of the last damage dealt.

    Used by ice spells: ``random(damage//2, damage)`` extra chill damage.
    """

    def __init__(
        self,
        damage_lo_fraction: float = 0.5,
        damage_hi_fraction: float = 1.0,
        message_template: str = "{target} is chilled to the bone, taking an extra {damage} damage.\n",
    ):
        self.damage_lo_fraction = damage_lo_fraction
        self.damage_hi_fraction = damage_hi_fraction
        self.message_template = message_template

    def apply(self, actor: Character, target: Character, result: CombatResult) -> None:
        import random

        last_damage = result.extra.get("last_damage", 0)
        lo = max(1, int(last_damage * self.damage_lo_fraction))
        hi = max(lo, int(last_damage * self.damage_hi_fraction))
        dmg = random.randint(lo, hi)

        target.health.current -= dmg
        result.extra["extra_damage"] = dmg
        result.extra.setdefault("messages", []).append(
            self.message_template.format(target=target.name, damage=dmg)
        )


class StatusApplyEffect(Effect):
    """
    Applies a status effect with immunity/pendant checks (like ElectricSpell stun).

    When ``crit_only`` is True, the effect only triggers on critical hits
    (e.g., Holy's Blind on crit).
    When ``skip_if_active`` is True, the effect is skipped if the target already
    has this status active (e.g., Sleep, Stupefy).
    When ``duration_stat`` is set, duration is computed from caster stats
    (e.g., Berserk uses intel-based random duration).
    """

    def __init__(
        self,
        status_name: str,
        duration: int = 1,
        use_crit_bonus: bool = False,
        crit_only: bool = False,
        skip_if_active: bool = False,
        duration_stat: str | None = None,
        duration_stat_divisor: int = 10,
        duration_min: int = 2,
        duration_random: bool = False,
    ):
        self.status_name = status_name
        self.duration = duration
        self.use_crit_bonus = use_crit_bonus
        self.crit_only = crit_only
        self.skip_if_active = skip_if_active
        self.duration_stat = duration_stat
        self.duration_stat_divisor = duration_stat_divisor
        self.duration_min = duration_min
        self.duration_random = duration_random

    def apply(self, actor: Character, target: Character, result: CombatResult) -> None:
        import random as _rng

        # If crit_only, skip when there's no critical hit
        crit = result.extra.get("last_crit", 1)
        if self.crit_only and crit <= 1:
            return

        # Check immunities
        if target.has_status_protection(self.status_name):
            result.extra["status_immune"] = self.status_name
            return

        # Check already active
        if self.skip_if_active and target.status_effects[self.status_name].active:
            result.extra["status_already_active"] = self.status_name
            return

        # --- Resist check (WIS/CHA matter) ---
        # Historically many statuses applied deterministically (unless immune), which made
        # "dump" mental stats (WIS/CHA) feel nearly free for non-casters. Add a lightweight
        # saving-throw contest for high-impact control effects.
        if self.status_name in {"Stun", "Sleep", "Silence", "Blind", "Stupefy", "Stone"}:
            # Offense: caster intelligence + a bit of luck
            a_stat = int(getattr(actor.stats, "intel", 10) or 0)
            a_luck = int(actor.check_mod("luck", enemy=target, luck_factor=12) or 0)
            # Defense: target wisdom + luck (luck includes WIS/CHA via check_mod)
            t_stat = int(getattr(target.stats, "wisdom", 10) or 0)
            t_luck = int(target.check_mod("luck", enemy=actor, luck_factor=10) or 0)

            actor_roll = _rng.randint(0, max(1, a_stat)) + a_luck
            target_roll = _rng.randint(0, max(1, t_stat)) + t_luck
            from ..classes import mage_mechanics

            target_roll = int(target_roll * mage_mechanics.save_roll_multiplier(target))
            try:
                from ..classes import promotion_kits

                target_roll = int(
                    target_roll * promotion_kits.benediction_status_multiplier(target)
                )
            except Exception:
                pass
            # Human Lust (sin): slightly reduced status resistance.
            try:
                if getattr(getattr(target, "race", None), "name", None) == "Human":
                    from src.core.constants import HUMAN_STATUS_RESIST_MULTIPLIER

                    target_roll = int(target_roll * HUMAN_STATUS_RESIST_MULTIPLIER)
            except Exception:
                pass
            if actor_roll <= target_roll:
                result.extra.setdefault("messages", []).append(
                    f"{target.name} resists {self.status_name}.\n"
                )
                result.extra["status_resisted"] = self.status_name
                return

        # Calculate duration
        if self.duration_stat:
            stat_val = getattr(actor.stats, self.duration_stat, 10)
            dynamic = stat_val // self.duration_stat_divisor
            base_dur = max(self.duration_min, dynamic)
            dur = _rng.randint(1, base_dur) if self.duration_random else base_dur
        elif self.use_crit_bonus:
            dur = self.duration + crit
        else:
            dur = self.duration

        if self.status_name == "Stun":
            if target.apply_stun(dur, source=result.action, applier=actor):
                result.effects_applied["Status"].append(self.status_name)
            else:
                stun = target.status_effects.get("Stun")
                if stun is not None and stun.active:
                    result.extra["status_already_active"] = self.status_name
                else:
                    result.extra["status_immune"] = self.status_name
            return

        target.status_effects[self.status_name].active = True
        target.status_effects[self.status_name].duration = max(
            dur, target.status_effects[self.status_name].duration
        )
        result.effects_applied["Status"].append(self.status_name)

        try:
            actor._emit_status_event(
                target,
                self.status_name,
                applied=True,
                duration=target.status_effects[self.status_name].duration,
                source=result.action,
            )
        except Exception:
            pass


class ScalingEffect(Effect):
    """
    An effect whose magnitude scales with character stats or conditions.

    Example: "Damage scales with missing health"
    """

    def __init__(self, base_effect: Effect, scaling_func: Callable):
        """
        Args:
            base_effect: The base effect to apply
            scaling_func: Function that takes (actor, target) and returns a multiplier
        """
        self.base_effect = base_effect
        self.scaling_func = scaling_func

    def apply(self, actor: Character, target: Character, result: CombatResult) -> None:
        """Apply the effect with scaling."""
        multiplier = self.scaling_func(actor, target)

        # Modify the base effect's magnitude
        if hasattr(self.base_effect, "base_damage"):
            original_damage = self.base_effect.base_damage
            self.base_effect.base_damage = int(original_damage * multiplier)
            self.base_effect.apply(actor, target, result)
            self.base_effect.base_damage = original_damage  # Restore original
        elif hasattr(self.base_effect, "base_healing"):
            original_healing = self.base_effect.base_healing
            self.base_effect.base_healing = int(original_healing * multiplier)
            self.base_effect.apply(actor, target, result)
            self.base_effect.base_healing = original_healing
        else:
            # Default: just apply the effect
            self.base_effect.apply(actor, target, result)


class LifestealEffect(Effect):
    """
    Heals the actor for a percentage of damage dealt.
    """

    def __init__(self, lifesteal_percent: float):
        """
        Args:
            lifesteal_percent: Percentage of damage to heal (0.0 to 1.0)
        """
        self.lifesteal_percent = lifesteal_percent

    def apply(self, actor: Character, target: Character, result: CombatResult) -> None:
        """Heal actor based on damage dealt."""
        if result.damage and result.damage > 0:
            heal_amount = int(result.damage * self.lifesteal_percent)
            heal_amount = int(heal_amount * actor.healing_received_multiplier())
            actual_heal = min(heal_amount, actor.health.max - actor.health.current)
            actor.health.current += actual_heal
            result.extra["lifesteal"] = actual_heal
            result.healing = actual_heal


class ReflectDamageEffect(Effect):
    """
    Reflects a portion of damage back to the attacker.
    """

    def __init__(self, reflect_percent: float, duration: int):
        """
        Args:
            reflect_percent: Percentage of damage to reflect (0.0 to 1.0)
            duration: Number of turns the effect lasts
        """
        self.reflect_percent = reflect_percent
        self.duration = duration

    def apply(self, actor: Character, target: Character, result: CombatResult) -> None:
        """Apply reflect buff to target."""
        target.magic_effects["Reflect"].active = True
        target.magic_effects["Reflect"].duration = self.duration
        target.magic_effects["Reflect"].extra = int(self.reflect_percent * 100)
        result.effects_applied["Magic"].append("Reflect")


class DamageOverTimeEffect(Effect):
    """
    Applies damage over multiple turns.

    Examples: Poison, Burn, Bleed
    """

    def __init__(
        self, dot_type: str, damage_per_tick: int, duration: int, element: str = "Physical"
    ):
        """
        Args:
            dot_type: Type of DOT ('Poison', 'Burn', 'Bleed', etc.)
            damage_per_tick: Damage dealt each turn
            duration: Number of turns the effect lasts
            element: Damage type for resistance calculations
        """
        self.dot_type = dot_type
        self.damage_per_tick = damage_per_tick
        self.duration = duration
        self.element = element

    def apply(self, actor: Character, target: Character, result: CombatResult) -> None:
        """Apply the DOT effect to target."""
        # Check if using status_effects (e.g., Poison) or magic_effects (DOT)
        if self.dot_type in target.status_effects:
            target.status_effects[self.dot_type].active = True
            target.status_effects[self.dot_type].duration = self.duration
            target.status_effects[self.dot_type].extra = self.damage_per_tick
            result.effects_applied["Status"].append(self.dot_type)
        else:
            # Use generic DOT magic effect
            target.magic_effects["DOT"].active = True
            target.magic_effects["DOT"].duration = self.duration
            target.magic_effects["DOT"].extra = self.damage_per_tick
            target.magic_effects["DOT"].source = self.dot_type
            result.effects_applied["Magic"].append(f"DOT ({self.dot_type})")
            result.extra["dot_type"] = self.dot_type


class DispelEffect(Effect):
    """
    Removes buffs or debuffs from target.
    """

    def __init__(self, dispel_type: str = "all"):
        """
        Args:
            dispel_type: What to dispel ('buffs', 'debuffs', 'all')
        """
        self.dispel_type = dispel_type

    def apply(self, actor: Character, target: Character, result: CombatResult) -> None:
        """Remove effects from target."""
        dispelled = []

        # Dispel stat effects
        for stat_name, effect in target.stat_effects.items():
            if effect.active:
                if self.dispel_type == "all":
                    effect.active = False
                    effect.duration = 0
                    effect.extra = 0
                    dispelled.append(stat_name)
                elif self.dispel_type == "buffs" and effect.extra > 0:
                    effect.active = False
                    effect.duration = 0
                    effect.extra = 0
                    dispelled.append(stat_name)
                elif self.dispel_type == "debuffs" and effect.extra < 0:
                    effect.active = False
                    effect.duration = 0
                    effect.extra = 0
                    dispelled.append(stat_name)

        result.extra["dispelled"] = dispelled


class ShieldEffect(Effect):
    """
    Grants a shield that absorbs damage.
    """

    def __init__(self, shield_amount: int, duration: int):
        """
        Args:
            shield_amount: Amount of damage the shield can absorb
            duration: Number of turns the shield lasts
        """
        self.shield_amount = shield_amount
        self.duration = duration

    def apply(self, actor: Character, target: Character, result: CombatResult) -> None:
        """Apply shield to target."""
        target.magic_effects["Mana Shield"].active = True
        target.magic_effects["Mana Shield"].duration = self.duration
        # Note: Current implementation uses mana as shield, might need adjustment
        result.effects_applied["Magic"].append("Shield")
        result.extra["shield_amount"] = self.shield_amount


class DynamicStatusDotEffect(Effect):
    """
    Applies a status-based DOT (e.g. Poison) whose damage scales from the
    last damage dealt.

    Unlike ``DynamicDotEffect`` which writes to ``target.magic_effects``,
    this writes to ``target.status_effects`` for statuses like Poison that
    have their own tick logic in the game loop.

    Optionally multiplies damage by a fraction of ``target.health.max``
    (e.g., PoisonBreath: ``damage * max_hp * 0.005``).

    The duration can be stat-based (e.g. ``max(duration_min, stat // 10)``).
    """

    def __init__(
        self,
        status_name: str = "Poison",
        duration: int = 2,
        duration_min: int = 2,
        duration_stat: str | None = None,
        duration_stat_divisor: int = 10,
        damage_lo_fraction: float = 1.0,
        damage_hi_fraction: float = 1.0,
        health_multiplier: float | None = None,
    ):
        self.status_name = status_name
        self.duration = duration
        self.duration_min = duration_min
        self.duration_stat = duration_stat
        self.duration_stat_divisor = duration_stat_divisor
        self.damage_lo_fraction = damage_lo_fraction
        self.damage_hi_fraction = damage_hi_fraction
        self.health_multiplier = health_multiplier

    def apply(self, actor: Character, target: Character, result: CombatResult) -> None:
        import random

        # Check immunities
        if target.has_status_protection(self.status_name):
            return

        # Compute duration
        if self.duration_stat:
            stat_val = getattr(actor.stats, self.duration_stat, 10)
            dur = max(self.duration_min, stat_val // self.duration_stat_divisor)
        else:
            dur = self.duration

        # Compute damage per tick
        last_damage = result.extra.get("last_damage", 0)
        lo = max(1, int(last_damage * self.damage_lo_fraction))
        hi = max(lo, int(last_damage * self.damage_hi_fraction))
        dmg = random.randint(lo, hi) if lo != hi else lo

        if self.health_multiplier is not None:
            dmg = int(dmg * (target.health.max * self.health_multiplier))

        target.status_effects[self.status_name].active = True
        target.status_effects[self.status_name].duration = max(
            dur, target.status_effects[self.status_name].duration
        )
        target.status_effects[self.status_name].extra = max(
            dmg, target.status_effects[self.status_name].extra
        )
        result.effects_applied["Status"].append(self.status_name)

        try:
            actor._emit_status_event(
                target,
                self.status_name,
                applied=True,
                duration=target.status_effects[self.status_name].duration,
                source=result.action,
            )
        except Exception:
            pass


class MagicEffectApplyEffect(Effect):
    """
    Applies a named magic_effect to the target (IceBlock, Duplicates, Reflect,
    Astral Shift, etc.).  Duration can be fixed or stat-based.
    """

    def __init__(
        self,
        effect_name: str,
        duration: int = 3,
        duration_stat: str | None = None,
        duration_stat_divisor: int = 10,
        duration_stat_mode: str = "add",
    ):
        self.effect_name = effect_name
        self.duration = duration
        self.duration_stat = duration_stat
        self.duration_stat_divisor = duration_stat_divisor
        self.duration_stat_mode = duration_stat_mode  # "add" or "max"

    def apply(self, actor: Character, target: Character, result: CombatResult) -> None:
        if self.duration_stat:
            stat_val = getattr(actor.stats, self.duration_stat, 10)
            dynamic = stat_val // self.duration_stat_divisor
            if self.duration_stat_mode == "add":
                dur = self.duration + dynamic
            else:
                dur = max(self.duration, dynamic)
        else:
            dur = self.duration

        target.magic_effects[self.effect_name].active = True
        target.magic_effects[self.effect_name].duration = max(
            dur, target.magic_effects[self.effect_name].duration
        )
        result.effects_applied["Magic"].append(self.effect_name)

        try:
            actor._emit_status_event(
                target,
                self.effect_name,
                applied=True,
                duration=target.magic_effects[self.effect_name].duration,
                source=result.action,
            )
        except Exception:
            pass


class DynamicStatBuffEffect(Effect):
    """
    Applies a single-stat buff whose amount is computed from character stats
    at cast time.  Pattern: ``random(source_val // lo_div, source_val // hi_div)``.

    Used by Boost (Magic), Shell (Magic Defense), WindSpeed (Speed),
    DivineProtection (Defense).
    """

    def __init__(
        self,
        buff_stat: str,
        source: str = "target_combat",
        source_stat: str = "attack",
        lo_divisor: int = 4,
        hi_divisor: int = 2,
        duration: int = 3,
        duration_stat: str | None = None,
        duration_divisor: int = 10,
        duration_min: int = 3,
        apply_to_caster: bool = False,
    ):
        self.buff_stat = buff_stat
        self.source = source
        self.source_stat = source_stat
        self.lo_divisor = lo_divisor
        self.hi_divisor = hi_divisor
        self.duration = duration
        self.duration_stat = duration_stat
        self.duration_divisor = duration_divisor
        self.duration_min = duration_min
        self.apply_to_caster = apply_to_caster

    def apply(self, actor: Character, target: Character, result: CombatResult) -> None:
        import random as _rng

        if self.source == "target_combat":
            obj = actor.combat if self.apply_to_caster else target.combat
            source_val = getattr(obj, self.source_stat, 10)
        else:
            source_val = getattr(actor.stats, self.source_stat, 10)

        lo = max(1, source_val // self.lo_divisor)
        hi = max(lo, source_val // self.hi_divisor)
        amount = _rng.randint(lo, hi)

        if self.duration_stat:
            stat_val = getattr(actor.stats, self.duration_stat, 10)
            dur = max(self.duration_min, stat_val // self.duration_divisor)
        else:
            dur = self.duration

        apply_target = actor if self.apply_to_caster else target
        apply_target.stat_effects[self.buff_stat].active = True
        apply_target.stat_effects[self.buff_stat].duration = max(
            dur, apply_target.stat_effects[self.buff_stat].duration
        )
        apply_target.stat_effects[self.buff_stat].extra = amount

        result.effects_applied["Stat"].append(f"{self.buff_stat} Buff")
        result.extra.setdefault("buff_amounts", {})[self.buff_stat] = amount


class DynamicMultiDebuffEffect(Effect):
    """
    Apply multi-stat debuffs using legacy dynamic scaling or a fixed percentage.

    Legacy formula per stat:
        amount   = target.combat.<combat_attr> // amount_divisor
        dv       = actor.stats.<scaling_stat> // scaling_divisor
        lo       = amount // max(2, 9 - dv)
        hi       = amount // max(1, 5 - dv)
        debuff   = random(lo, hi)
        duration = max(duration_min, dv)
    """

    def __init__(
        self,
        stats: list[dict],
        scaling_stat: str = "intel",
        scaling_divisor: int = 10,
        amount_divisor: int = 10,
        duration_min: int = 3,
        percentage: float | None = None,
        duration: int | None = None,
    ):
        self.stats = stats
        self.scaling_stat = scaling_stat
        self.scaling_divisor = scaling_divisor
        self.amount_divisor = amount_divisor
        self.duration_min = duration_min
        self.percentage = percentage
        self.duration = duration

    def apply(self, actor: Character, target: Character, result: CombatResult) -> None:
        import random as _rng

        dv = getattr(actor.stats, self.scaling_stat, 10) // self.scaling_divisor
        dur = self.duration if self.duration is not None else max(self.duration_min, dv)
        applied_amounts: dict[str, int] = {}

        for spec in self.stats:
            stat_name = spec["stat_name"]
            combat_attr = spec["combat_attr"]
            base_amount = max(0, int(getattr(target.combat, combat_attr, 10) or 0))
            if base_amount <= 0:
                continue
            if self.percentage is not None:
                stat_mod = max(1, math.ceil(base_amount * self.percentage))
            else:
                amount = base_amount // self.amount_divisor
                if amount <= 0:
                    continue
                lo = amount // max(2, 9 - dv)
                hi = amount // max(1, 5 - dv)
                stat_mod = _rng.randint(max(0, lo), max(0, hi))
            if stat_mod <= 0:
                continue

            target.stat_effects[stat_name].active = True
            target.stat_effects[stat_name].duration = max(
                dur,
                int(target.stat_effects[stat_name].duration or 0),
            )
            target.stat_effects[stat_name].extra = min(
                -stat_mod,
                int(target.stat_effects[stat_name].extra or 0),
            )

            result.effects_applied["Stat"].append(f"{stat_name} Debuff")
            applied_amounts[stat_name] = stat_mod
            if self.percentage is not None:
                percent = round(self.percentage * 100)
                message = f"{target.name}'s {stat_name.lower()} is lowered by {percent}%."
            else:
                message = f"{target.name}'s {stat_name.lower()} is lowered."
            result.extra.setdefault("messages", []).append(message)

        if result.action == "Weaken Mind" and applied_amounts:
            try:
                from ..progression import has_talent

                neural_connection = has_talent(
                    actor,
                    "arcane-trickster.neural-connection",
                )
            except (AttributeError, KeyError, TypeError, ValueError):
                neural_connection = False
            if neural_connection:
                for stat_name in ("Magic", "Magic Defense"):
                    amount = applied_amounts.get(stat_name, 0)
                    if amount <= 0:
                        continue
                    effect = actor.stat_effects[stat_name]
                    effect.active = True
                    effect.duration = max(dur, int(effect.duration or 0))
                    effect.extra = max(amount, int(effect.extra or 0))
                    effect.source = "Neural Connection"
                result.extra.setdefault("messages", []).append(
                    f"Neural Connection mirrors the stolen magical strength to {actor.name}."
                )


class CleanseEffect(Effect):
    """Clears all ``status_effects`` (Blind, Stun, Sleep, Poison, etc.)."""

    def apply(self, actor: Character, target: Character, result: CombatResult) -> None:
        reverse = (
            "Uno Reverse Card" in getattr(actor, "spellbook", {}).get("Skills", {})
            and getattr(getattr(actor, "familiar", None), "spec", "") == "Support"
            and bool(result.extra.get("use_kwargs", {}).get("fam", False))
        )
        reversed_count = 0
        for name in list(target.status_effects):
            if target.status_effects[name].active:
                duration = max(1, int(target.status_effects[name].duration or 0))
                target.status_effects[name].active = False
                result.effects_applied.setdefault("Cleansed", []).append(name)
                if reverse:
                    reversed_count += 1
                    buff = target.stat_effects["Defense"]
                    buff.active = True
                    buff.duration = max(duration, int(buff.duration or 0))
                    buff.extra = max(1, int(getattr(target.stats, "con", 10) * 0.10))
        if reversed_count:
            result.extra.setdefault("messages", []).append(
                f"Uno Reverse Card turns {reversed_count} affliction(s) into protection.\n"
            )


class FullDispelEffect(Effect):
    """
    Removes all positive buffs from the target: specified ``magic_effects``
    (Regen, Reflect by default) **and** all ``stat_effects``.
    """

    DEFAULT_MAGIC_EFFECTS = [
        "Astral Shift",
        "Duplicates",
        "Ice Block",
        "Mana Shield",
        "Reflect",
        "Regen",
        "Resist Fire",
        "Resist Ice",
        "Resist Electric",
        "Resist Water",
        "Resist Earth",
        "Resist Wind",
        "Resist Shadow",
        "Resist Holy",
        "Hallowed Ground",
        "Totem",
    ]

    def __init__(
        self,
        magic_effects: list[str] | None = None,
    ):
        self.magic_effects_to_clear = magic_effects or list(self.DEFAULT_MAGIC_EFFECTS)

    def apply(self, actor: Character, target: Character, result: CombatResult) -> None:
        dispelled = []
        for name in self.magic_effects_to_clear:
            effect = target.magic_effects.get(name)
            if effect and effect.active:
                effect.active = False
                effect.duration = 0
                if hasattr(effect, "extra"):
                    effect.extra = 0
                dispelled.append(name)
        for name in ["Attack", "Defense", "Magic", "Magic Defense", "Speed"]:
            effect = target.stat_effects.get(name)
            if effect and effect.active:
                effect.active = False
                effect.duration = 0
                if hasattr(effect, "extra"):
                    effect.extra = 0
                dispelled.append(name)
        result.effects_applied["Dispelled"] = dispelled


class ManaDrainOnHitEffect(Effect):
    """
    After a weapon hit, drain a fraction of the target's current mana and
    give it to the actor.  Used by ManaSlice / ManaSlice2.

    Formula: ``drain_percent = (dmg_mod * crit) / divisor``
             ``mana_gain = int(target.mana.current * drain_percent)``
    """

    def __init__(self, divisor: int = 5):
        self.divisor = divisor

    def apply(self, actor: Character, target: Character, result: CombatResult) -> None:
        crit = result.extra.get("last_crit", 1)
        dmg_mod = result.extra.get("dmg_mod", 1.0)
        drain_per = (dmg_mod * crit) / self.divisor
        mana_gain = int(target.mana.current * drain_per)
        if mana_gain > 0:
            target.mana.current -= mana_gain
            actor.mana.current = min(actor.mana.max, actor.mana.current + mana_gain)
            result.extra.setdefault("messages", []).append(
                f"{actor.name} steals {mana_gain} mana from {target.name}.\n"
            )


class ResourceConvertEffect(Effect):
    """
    Convert a percentage of one resource (health / mana) into the other.
    Used by LifeTap (health → mana) and ManaTap (mana → health).

    ``source``: ``"health"`` or ``"mana"``
    ``target_resource``: ``"mana"`` or ``"health"``
    ``percent``: fraction of source max to convert (default 0.1 = 10%)
    ``ring_mod``: optional equipment mod that doubles the percent
    """

    def __init__(
        self,
        source: str = "health",
        target_resource: str = "mana",
        percent: float = 0.1,
        ring_mod: str | None = None,
    ):
        self.source = source
        self.target_resource = target_resource
        self.percent = percent
        self.ring_mod = ring_mod

    def apply(self, actor: Character, target: Character, result: CombatResult) -> None:
        # Determine effective percent (may be doubled by ring mod)
        pct = self.percent
        if self.ring_mod and hasattr(actor, "equipment"):
            if self.ring_mod in actor.equipment.get("Ring", type("", (), {"mod": ""})()).mod:
                pct *= 2
        resource_abuse = (
            self.source == "mana"
            and self.target_resource == "health"
            and "Resource Abuse" in getattr(actor, "spellbook", {}).get("Skills", {})
        )
        if resource_abuse:
            pct *= 2

        src_pool = getattr(actor, self.source)
        dst_pool = getattr(actor, self.target_resource)

        # Check: target resource already full
        if dst_pool.current >= dst_pool.max and not resource_abuse:
            result.extra["resource_full"] = True
            result.extra.setdefault("messages", []).append(
                f"You are already at full {self.target_resource}.\n"
            )
            return

        cost = int(src_pool.max * pct)

        # For health→mana (LifeTap): need enough health
        if self.source == "health" and actor.health.current < cost:
            result.extra["insufficient_source"] = True
            result.extra.setdefault("messages", []).append(
                f"Your {self.source} is too low to use this ability.\n"
            )
            return

        # For mana→health (ManaTap): cap at current mana
        if self.source == "mana":
            cost = int(min(src_pool.max * pct, src_pool.current))

        src_pool.current -= cost
        gained = min(cost, dst_pool.max - dst_pool.current)
        dst_pool.current += gained
        if resource_abuse and cost > gained:
            actor.resource_abuse_shadow_bonus = int(
                getattr(actor, "resource_abuse_shadow_bonus", 0) or 0
            ) + (cost - gained)

        result.extra["converted_amount"] = cost
        result.extra["gained_amount"] = gained
        result.extra.setdefault("messages", []).append(
            f"{actor.name} sacrifices {cost} {self.source} to restore {self.target_resource}.\n"
        )
        if resource_abuse and cost > gained:
            result.extra.setdefault("messages", []).append(
                f"Resource Abuse stores {cost - gained} excess healing as Shadow damage.\n"
            )


class PhysicalEffectApplyEffect(Effect):
    """
    Applies a physical effect (Bleed, Prone, Disarm) to the target via a
    stat contest.  Supports immunity checks and duration calculation.

    For ``Bleed``: damage is calculated from actor strength * crit.
    For ``Prone``: simple boolean, respects ``target.flying``.
    For ``Disarm``: respects ``target.can_be_disarmed()``.
    """

    def __init__(
        self,
        effect_name: str,
        actor_stat: str = "strength",
        actor_lo_divisor: int = 2,
        actor_hi_divisor: int = 1,
        target_stat: str = "con",
        target_lo_divisor: int = 2,
        target_hi_divisor: int = 1,
        duration: int = 3,
        duration_stat: str | None = None,
        duration_divisor: int = 10,
        duration_min: int = 1,
        skip_if_active: bool = False,
        requires_crit: bool = False,
        use_crit_multiplier: bool = False,
        damage_multiplier: float = 0.0,
        check_flying: bool = False,
        check_disarmable: bool = False,
    ):
        self.effect_name = effect_name
        self.actor_stat = actor_stat
        self.actor_lo_divisor = actor_lo_divisor
        self.actor_hi_divisor = actor_hi_divisor
        self.target_stat = target_stat
        self.target_lo_divisor = target_lo_divisor
        self.target_hi_divisor = target_hi_divisor
        self.duration = duration
        self.duration_stat = duration_stat
        self.duration_divisor = duration_divisor
        self.duration_min = duration_min
        self.skip_if_active = skip_if_active
        self.requires_crit = requires_crit
        self.use_crit_multiplier = use_crit_multiplier
        self.damage_multiplier = damage_multiplier
        self.check_flying = check_flying
        self.check_disarmable = check_disarmable

    def apply(self, actor: Character, target: Character, result: CombatResult) -> None:
        import random as _rng

        crit = result.extra.get("last_crit", 1)

        # Gate: requires crit for prone-on-crit pattern (Slam)
        if self.requires_crit and crit <= 1:
            return

        # Gate: flying creatures can't be knocked prone
        if self.check_flying and getattr(target, "flying", False):
            return

        # Gate: disarm check
        if self.check_disarmable:
            if not hasattr(target, "can_be_disarmed") or not target.can_be_disarmed():
                result.extra.setdefault("messages", []).append(
                    f"{target.name} cannot be disarmed.\n"
                )
                return

        # Gate: skip if already active
        if self.skip_if_active and target.physical_effects[self.effect_name].active:
            result.extra.setdefault("messages", []).append(
                f"{target.name} is already affected by {self.effect_name}.\n"
            )
            return

        # Stat contest
        actor_val = getattr(actor.stats, self.actor_stat, 10)
        if self.use_crit_multiplier:
            actor_val = (
                int(actor_val * crit * self.damage_multiplier)
                if self.damage_multiplier
                else actor_val
            )
        actor_roll = _rng.randint(
            actor_val // self.actor_lo_divisor, actor_val // max(1, self.actor_hi_divisor)
        )
        target_val = getattr(target.stats, self.target_stat, 10)
        target_roll = _rng.randint(
            target_val // self.target_lo_divisor, target_val // max(1, self.target_hi_divisor)
        )
        from ..classes import mage_mechanics

        target_roll = int(target_roll * mage_mechanics.save_roll_multiplier(target))

        contest_success = actor_roll > target_roll
        control_bonus = 0.0
        if self.effect_name == "Prone":
            try:
                from ..classes import promotion_kits

                ability_name = str(getattr(result, "action", "") or "")
                control_bonus = promotion_kits.ki_control_bonus(actor, ability_name)
            except Exception:
                control_bonus = 0.0
        if not contest_success and control_bonus > 0:
            contest_success = _rng.random() < control_bonus

        if contest_success:
            # Calculate duration
            if self.duration_stat:
                stat_val = getattr(actor.stats, self.duration_stat, 10)
                dur = max(self.duration_min, stat_val // self.duration_divisor)
            else:
                dur = self.duration
            if control_bonus > 0:
                dur += 1

            target.physical_effects[self.effect_name].active = True
            target.physical_effects[self.effect_name].duration = max(
                dur, target.physical_effects[self.effect_name].duration
            )

            # For Bleed: set damage amount
            if self.damage_multiplier > 0 and self.effect_name == "Bleed":
                # Always compute from raw stat — actor_val may already include
                # crit & damage_multiplier when use_crit_multiplier is True.
                raw_stat = getattr(actor.stats, self.actor_stat, 10)
                base_dmg = int(raw_stat * crit * self.damage_multiplier)
                bleed_dmg = _rng.randint(max(1, base_dmg // 4), max(1, base_dmg))
                target.physical_effects[self.effect_name].extra = max(
                    bleed_dmg, target.physical_effects[self.effect_name].extra
                )

            result.extra.setdefault("messages", []).append(
                f"{target.name} is affected by {self.effect_name}.\n"
            )
            result.extra["physical_applied"] = self.effect_name
        else:
            result.extra.setdefault("messages", []).append(
                f"{target.name} resists {self.effect_name}.\n"
            )


class InstantKillEffect(Effect):
    """
    Instant-kill effect used by death spells (Desoul, Petrify).

    Pipeline:
      1. Optional **reflect_item** check — if the target wields a named item
         in the given slot the spell is reflected back at the caster.
      2. **Immunity** — either *resist-based* (``apply_resist_multiplier``,
         full resist ≥ 1 → immune) or *status-based* (``immunity_status``,
         e.g. ``"Stone"``).
      3. **Stat contest** — actor stat (optionally multiplied by ``1-resist``)
         versus target stat + luck.
      4. On **win** → ``target.health.current = 0`` and a success message is
         appended to ``result.extra["messages"]``.
      5. On **loss** → ``result.extra["stat_contest_won"] = False``.
    """

    def __init__(
        self,
        success_message: str = "{target} is slain.",
        actor_stat: str = "charisma",
        actor_divisor: int = 1,
        target_stat: str = "con",
        target_lo_divisor: int = 2,
        target_hi_divisor: int = 1,
        apply_resist_multiplier: bool = True,
        resist_type: str = "Death",
        luck_factor: int = 10,
        immunity_status: str | None = None,
        reflect_item: str | None = None,
        reflect_slot: str = "OffHand",
        reflect_message: str = "",
    ):
        self.success_message = success_message
        self.actor_stat = actor_stat
        self.actor_divisor = actor_divisor
        self.target_stat = target_stat
        self.target_lo_divisor = target_lo_divisor
        self.target_hi_divisor = target_hi_divisor
        self.apply_resist_multiplier = apply_resist_multiplier
        self.resist_type = resist_type
        self.luck_factor = luck_factor
        self.immunity_status = immunity_status
        self.reflect_item = reflect_item
        self.reflect_slot = reflect_slot
        self.reflect_message = reflect_message

    def apply(self, actor: Character, target: Character, result: CombatResult) -> None:
        import random

        if result.action == "Desoul":
            from ..classes import promotion_kits

            killed, immune = promotion_kits.resolve_death_contest(actor, target)
            if immune:
                result.extra["status_immune"] = "Death"
            elif killed:
                result.extra.setdefault("messages", []).append(
                    self.success_message.format(target=target.name, caster=actor.name)
                )
                result.extra["stat_contest_won"] = True
            else:
                result.extra["stat_contest_won"] = False
            return

        # --- Reflect check (e.g. Medusa Shield) ---
        if self.reflect_item and self.reflect_slot:
            equip = getattr(target, "equipment", {})
            item = (
                equip.get(self.reflect_slot)
                if isinstance(equip, dict)
                else getattr(equip, self.reflect_slot, None)
            )
            if item and getattr(item, "name", None) == self.reflect_item:
                msg = self.reflect_message.format(
                    target=target.name,
                    caster=actor.name,
                    name=result.action,
                )
                result.extra.setdefault("messages", []).append(msg)
                target = actor  # reflected!

        # --- Status immunity check (e.g. "Stone" in status_immunity) ---
        if self.immunity_status:
            if self.immunity_status in getattr(target, "status_immunity", []):
                result.extra["status_immune"] = self.immunity_status
                return

        # --- Resist-based immunity ---
        resist = 0.0
        if self.apply_resist_multiplier:
            resist = target.check_mod("resist", enemy=actor, typ=self.resist_type)
            if resist >= 1:
                result.extra["status_immune"] = "Death"
                return

        # --- Luck modifier ---
        chance = target.check_mod("luck", enemy=actor, luck_factor=self.luck_factor)

        # --- Stat contest ---
        a_val = getattr(actor.stats, self.actor_stat, 10)
        t_val = getattr(target.stats, self.target_stat, 10)

        actor_roll = random.randint(0, max(1, a_val // self.actor_divisor))
        if self.apply_resist_multiplier:
            actor_roll = int(actor_roll * (1 - resist))

        target_roll = (
            random.randint(
                max(0, t_val // self.target_lo_divisor),
                max(1, t_val // self.target_hi_divisor),
            )
            + chance
        )
        from ..classes import mage_mechanics

        target_roll = int(target_roll * mage_mechanics.save_roll_multiplier(target))

        if actor_roll > target_roll:
            target.health.current = 0
            msg = self.success_message.format(
                target=target.name,
                caster=actor.name,
            )
            result.extra.setdefault("messages", []).append(msg)
            result.extra["stat_contest_won"] = True
        else:
            result.extra["stat_contest_won"] = False


class StatReduceEffect(Effect):
    """
    Permanently reduce a target's stat (e.g. DiseaseBreath lowering CON).

    Has an internal two-stage contest:
      1. Actor stat contest — ``random(0, actor_stat // actor_divisor)`` vs
         ``random(target_stat // target_lo, target_stat // target_hi)``.
      2. Secondary chance — ``not random(0, target_stat_value + luck)`` must
         be True (i.e. the roll must be 0).

    On success, ``target.stats.<stat>`` is decremented by ``amount`` and a
    formatted ``success_message`` is added to ``result.extra["messages"]``.
    """

    def __init__(
        self,
        stat: str = "con",
        amount: int = 1,
        actor_stat: str = "intel",
        actor_divisor: int = 2,
        target_stat: str = "con",
        target_lo_divisor: int = 2,
        target_hi_divisor: int = 1,
        luck_factor: int = 10,
        success_message: str = "",
    ):
        self.stat = stat
        self.amount = amount
        self.actor_stat = actor_stat
        self.actor_divisor = actor_divisor
        self.target_stat = target_stat
        self.target_lo_divisor = target_lo_divisor
        self.target_hi_divisor = target_hi_divisor
        self.luck_factor = luck_factor
        self.success_message = success_message

    def apply(self, actor: Character, target: Character, result: CombatResult) -> None:
        import random

        # Stage 1: stat contest
        a_val = getattr(actor.stats, self.actor_stat, 10)
        t_val = getattr(target.stats, self.target_stat, 10)

        actor_roll = random.randint(0, max(1, a_val // self.actor_divisor))
        target_roll = random.randint(
            max(0, t_val // self.target_lo_divisor),
            max(1, t_val // self.target_hi_divisor),
        )
        from ..classes import mage_mechanics

        target_roll = int(target_roll * mage_mechanics.save_roll_multiplier(target))

        if actor_roll > target_roll:
            # Stage 2: secondary luck-gated chance
            chance = target.check_mod("luck", enemy=actor, luck_factor=self.luck_factor)
            stat_val = getattr(target.stats, self.stat, 10)
            if not random.randint(0, stat_val + chance):
                setattr(target.stats, self.stat, stat_val - self.amount)
                msg = self.success_message.format(
                    target=target.name,
                    caster=actor.name,
                )
                result.extra.setdefault("messages", []).append(msg)
                result.extra["stat_contest_won"] = True
                return

        result.extra["stat_contest_won"] = False


class SetFlagEffect(Effect):
    """
    Set a boolean attribute on the target character.

    Used by abilities like Tunnel (``tunnel = True``) and Surface
    (``tunnel = False``).  When the owning skill has ``self_target: true``,
    the *target* passed to :meth:`apply` is the actor themselves.

    ``flag``     - attribute name to set on the target (e.g. ``"tunnel"``)
    ``value``    - boolean value to assign (default ``True``)
    ``message``  - optional template; may contain ``{actor}`` and ``{target}``
    """

    def __init__(
        self,
        flag: str,
        value: bool = True,
        message: str | None = None,
    ):
        self.flag = flag
        self.value = value
        self.message = message

    def apply(self, actor: Character, target: Character, result: CombatResult) -> None:
        setattr(target, self.flag, self.value)
        if self.message:
            result.extra.setdefault("messages", []).append(
                self.message.format(actor=actor.name, target=target.name) + "\n"
            )
