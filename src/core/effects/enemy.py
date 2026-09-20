"""Enemy and spell-specific effects."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..character import Character
    from ..combat.combat_result import CombatResult


class PowerUpActivateEffect:
    """
    Activate the actor's class-specific Power Up buff.

    Sets ``actor.power_up = True`` and configures
    ``actor.class_effects["Power Up"]`` with the given duration.  Optionally
    computes an ``extra`` value stored on the effect for use by the class's
    combat code:

    ``extra_mode``:
      - ``None`` - no extra value
      - ``"random_health"`` - random int between ``lo_frac * health.max``
        and ``hi_frac * health.max``
      - ``"sacrifice_health"`` - sacrifice ``sacrifice_pct`` of current
        health; ``extra = max(lost // divisor, minimum)``
    """

    def __init__(
        self,
        duration: int = 5,
        extra_mode: str | None = None,
        lo_frac: float = 0.25,
        hi_frac: float = 0.5,
        sacrifice_pct: float = 0.25,
        sacrifice_divisor: int = 5,
        sacrifice_minimum: int = 5,
        message: str | None = None,
    ):
        self.duration = duration
        self.extra_mode = extra_mode
        self.lo_frac = lo_frac
        self.hi_frac = hi_frac
        self.sacrifice_pct = sacrifice_pct
        self.sacrifice_divisor = sacrifice_divisor
        self.sacrifice_minimum = sacrifice_minimum
        self.message = message

    def apply(self, actor: Character, target: Character, result: CombatResult) -> None:
        import random as _rng

        if self.extra_mode == "sacrifice_health":
            per_health = int(actor.health.current * self.sacrifice_pct)
            actor.health.current -= per_health
            extra = max(per_health // self.sacrifice_divisor, self.sacrifice_minimum)
            actor.class_effects["Power Up"].extra = extra
        elif self.extra_mode == "random_health":
            extra = _rng.randint(
                int(actor.health.max * self.lo_frac),
                int(actor.health.max * self.hi_frac),
            )
            actor.class_effects["Power Up"].extra = extra

        actor.power_up = True
        actor.class_effects["Power Up"].active = True
        actor.class_effects["Power Up"].duration = self.duration

        if self.message:
            # Supports {actor}, {extra} placeholders
            extra_val = getattr(actor.class_effects["Power Up"], "extra", 0)
            result.extra.setdefault("messages", []).append(
                self.message.format(actor=actor.name, extra=extra_val) + "\n"
            )


class AbilityChainEffect:
    """
    Instantiate and execute another ability as part of this ability's
    effects.  The chained ability is looked up by class name in the
    ``src.core.abilities`` module, constructed, and invoked with
    ``special=True`` (to skip its own mana cost).

    ``use_method`` - ``"cast"`` for spells, ``"use"`` for skills,
    ``"auto"`` to pick based on whether the ability has a ``school``
    attribute (→ cast) or not (→ use).
    """

    def __init__(
        self,
        ability_name: str,
        target_self: bool = False,
        special: bool = True,
        use_method: str = "auto",
    ):
        self.ability_name = ability_name
        self.target_self = target_self
        self.special = special
        self.use_method = use_method

    def apply(self, actor: Character, target: Character, result: CombatResult) -> None:
        import importlib

        mod = importlib.import_module("src.core.abilities")
        cls = getattr(mod, self.ability_name)
        ability = cls()
        actual_target = actor if self.target_self else target

        if self.use_method == "cast" or (
            self.use_method == "auto" and hasattr(ability, "school") and ability.school is not None
        ):
            msg = str(ability.cast(actor, actual_target, special=self.special))
        else:
            msg = str(ability.use(actor, actual_target, special=self.special))

        result.extra.setdefault("messages", []).append(msg)


class DrainEffect:
    """
    Drain a resource from the target and transfer it to the actor.

    The drain amount is calculated from actor stats:

        drain = randint((base_stat + secondary_stat) // lo_divisor,
                        (base_stat + secondary_stat) / hi_divisor)

    A wisdom-vs-wisdom contest (with luck) may halve the drain.
    The drain is capped at ``cap_percent`` of the target's max resource
    and at the target's current resource amount.
    """

    def __init__(
        self,
        resource: str = "health",
        base_stat: str = "health_current",
        secondary_stat: str = "charisma",
        lo_divisor: int = 5,
        hi_divisor: float = 1.5,
        luck_factor: int = 10,
        cap_percent: float = 0.18,
        message: str | None = None,
    ):
        self.resource = resource
        self.base_stat = base_stat
        self.secondary_stat = secondary_stat
        self.lo_divisor = lo_divisor
        self.hi_divisor = hi_divisor
        self.luck_factor = luck_factor
        self.cap_percent = cap_percent
        self.message = message

    def _get_stat(self, char: Character, stat_key: str) -> int:
        if stat_key == "health_current":
            return char.health.current
        elif stat_key == "health_max":
            return char.health.max
        elif stat_key == "mana_current":
            return char.mana.current
        elif stat_key == "mana_max":
            return char.mana.max
        return getattr(char.stats, stat_key, 0)

    def apply(self, actor: Character, target: Character, result: CombatResult) -> None:
        import random as _rng

        base = self._get_stat(actor, self.base_stat)
        secondary = self._get_stat(actor, self.secondary_stat)
        total = base + secondary

        lo = total // self.lo_divisor
        hi = int(total / self.hi_divisor)
        if hi < lo:
            hi = lo
        drain = _rng.randint(lo, hi)

        potency = 1.0
        if self.resource == "health" and "Vim and Rigor" in getattr(actor, "spellbook", {}).get(
            "Skills", {}
        ):
            target_max = max(1, int(target.health.max or 1))
            potency += 0.50 * (target.health.current / target_max)
            drain = int(drain * potency)

        # Wisdom-vs-wisdom contest; losing halves the drain
        chance = target.check_mod("luck", enemy=actor, luck_factor=self.luck_factor)
        if not (
            _rng.randint(actor.stats.wisdom // 2, actor.stats.wisdom)
            > _rng.randint(0, target.stats.wisdom // 2) + chance
        ):
            drain = drain // 2

        # Cap at percent of target's max + target's current
        if self.resource == "health":
            cap = max(1, int(target.health.max * self.cap_percent * potency))
            drain = min(drain, cap, target.health.current)
            target.health.current -= drain
            actor.health.current = min(actor.health.max, actor.health.current + drain)
            try:
                actor._emit_damage_event(target, drain, damage_type="Drain", is_critical=False)
                actor._emit_healing_event(drain, source="Life Drain")
            except Exception:
                pass
        else:
            cap = max(1, int(target.mana.max * self.cap_percent))
            drain = min(drain, cap, target.mana.current)
            target.mana.current -= drain
            actor.mana.current = min(actor.mana.max, actor.mana.current + drain)

        msg = (self.message or "{actor} drains {amount} {resource} from {target}.\n").format(
            actor=actor.name,
            target=target.name,
            amount=drain,
            resource=self.resource,
        )
        result.extra.setdefault("messages", []).append(msg)


class MagicEffectToggleEffect:
    """
    Toggle a magic effect on the actor.  When the effect is already active,
    it is deactivated (no mana cost).  When inactive, mana is deducted and
    the effect is activated with ``duration`` set to *reduction* (used by
    ``_apply_mana_shield`` as the maximum redirected physical-damage
    percentage, not a turn count).

    The ``cost`` is only charged on activation.  Set the parent skill's
    cost to 0 so the ``DataDrivenSkill`` pipeline does not double-charge.
    """

    def __init__(
        self,
        effect_name: str,
        cost: int = 0,
        reduction: int = 2,
        activate_message: str | None = None,
        deactivate_message: str | None = None,
    ):
        self.effect_name = effect_name
        self.cost = cost
        self.reduction = reduction
        self.activate_message = activate_message or f"{effect_name} has been activated.\n"
        self.deactivate_message = deactivate_message or f"{effect_name} has been deactivated.\n"

    def apply(self, actor: Character, target: Character, result: CombatResult) -> None:
        if actor.magic_effects[self.effect_name].active:
            actor.magic_effects[self.effect_name].active = False
            result.extra.setdefault("messages", []).append(self.deactivate_message)
            result.extra["toggled_off"] = True
        else:
            if self.cost:
                actor.mana.current -= self.cost
            actor.magic_effects[self.effect_name].active = True
            actor.magic_effects[self.effect_name].duration = self.reduction
            result.extra.setdefault("messages", []).append(self.activate_message)


class ScreechEffect:
    """
    Speed+intel vs con+wisdom stat contest.  On success, deal
    ``intel * (1 - Physical resist)`` damage and permanently silence the
    target (duration = -1) if the damage is positive and the target is not
    immune.
    """

    def __init__(
        self,
        damage_message: str = "The deafening screech hurts {target} for {damage} damage.\n",
        silence_message: str = "{target} has been silenced.\n",
        fail_message: str = "The spell is ineffective.\n",
    ):
        self.damage_message = damage_message
        self.silence_message = silence_message
        self.fail_message = fail_message

    def apply(self, actor: Character, target: Character, result: CombatResult) -> None:
        import random as _rng

        messages = result.extra.setdefault("messages", [])
        damage = 0

        # Stat contest: speed_check_mod + intel  vs  con(half-to-full) + wisdom
        actor_val = _rng.randint(0, actor.check_mod("speed", enemy=actor)) + actor.stats.intel
        target_val = _rng.randint(target.stats.con // 2, target.stats.con) + target.stats.wisdom

        if actor_val > target_val:
            resist = target.check_mod("resist", enemy=actor, typ="Physical")
            damage = int(actor.stats.intel * (1 - resist))
            if damage > 0:
                target.health.current -= damage
                result.damage = damage
                messages.append(self.damage_message.format(target=target.name, damage=damage))
                # Silence check
                if not any(
                    [
                        "Silence" in getattr(target, "status_immunity", []),
                        "Status-Silence" in target.equipment["Pendant"].mod,
                        "Status-All" in target.equipment["Pendant"].mod,
                    ]
                ):
                    target.status_effects["Silence"].active = True
                    target.status_effects["Silence"].duration = -1
                    try:
                        actor._emit_status_event(
                            target,
                            "Silence",
                            applied=True,
                            duration=-1,
                            source="Screech",
                        )
                    except Exception:
                        pass
                    messages.append(self.silence_message.format(target=target.name))

        if damage <= 0:
            messages.append(self.fail_message)


class AcidSpitEffect:
    """
    Intel-based magic damage with magic-defense armor curve, dodge
    halving, and a CON-based chance to apply DOT.

    Cost is ``base_cost * user.level.pro_level`` (deducted by the effect,
    so set the YAML ``cost: 0``).
    """

    def __init__(
        self,
        base_cost: int = 6,
        dot_duration: int = 2,
        damage_message: str = "{target} takes {damage} damage from the acid.\n",
        dot_message: str = "{target} is covered in a corrosive substance.\n",
        miss_message: str = "{actor} misses {target} with Acid Spit.\n",
        ineffective_message: str = "The acid is ineffective.\n",
        dodge_message: str = "{target} partially dodges the attack, only taking half damage.\n",
    ):
        self.base_cost = base_cost
        self.dot_duration = dot_duration
        self.damage_message = damage_message
        self.dot_message = dot_message
        self.miss_message = miss_message
        self.ineffective_message = ineffective_message
        self.dodge_message = dodge_message

    def apply(self, actor: Character, target: Character, result: CombatResult) -> None:
        import random as _rng

        from src.core.constants import (
            ARMOR_SCALING_FACTOR,
            DAMAGE_VARIANCE_HIGH,
            DAMAGE_VARIANCE_LOW,
        )

        messages = result.extra.setdefault("messages", [])

        # Dynamic mana cost
        actual_cost = self.base_cost * actor.level.pro_level
        actor.mana.current -= actual_cost

        # Intel-based magic damage with armor curve
        dmg = (actor.stats.intel // 2) + actor.combat.magic
        dam_red = target.check_mod("magic def", enemy=actor)
        damage = int(dmg * (1 - (dam_red / (dam_red + ARMOR_SCALING_FACTOR))))
        variance = _rng.uniform(DAMAGE_VARIANCE_LOW, DAMAGE_VARIANCE_HIGH)
        damage = int(damage * variance)

        contact = actor.resolve_contact(target, typ="magic", rng=_rng)
        if contact.hit:
            if damage > 0:
                messages.append(self.damage_message.format(target=target.name, damage=damage))
                target.health.current -= damage
                result.damage = damage
                # DOT chance via con check
                if not _rng.randint(0, target.stats.con // 2):
                    target.magic_effects["DOT"].active = True
                    target.magic_effects["DOT"].duration = self.dot_duration
                    target.magic_effects["DOT"].extra = max(
                        damage, target.magic_effects["DOT"].extra
                    )
                    target.magic_effects["DOT"].source = "Acid"
                    try:
                        actor._emit_status_event(
                            target,
                            "DOT",
                            applied=True,
                            duration=self.dot_duration,
                            source="Acid Splash",
                        )
                    except Exception:
                        pass
                    messages.append(self.dot_message.format(target=target.name))
            else:
                messages.append(self.ineffective_message)
        else:
            messages.append(self.miss_message.format(actor=actor.name, target=target.name))


class BreathDamageEffect:
    """
    Breath weapon: ``(strength + intel) * multiplier * variance``, then active
    spell defenses and ``damage_reduction(typ=element)``.  The element can be
    set in YAML or overridden at call-time via ``result.extra["use_kwargs"]["typ"]``.
    """

    def __init__(
        self,
        multiplier: float = 1.5,
        element: str = "Non-elemental",
        announce_message: str = "{actor} unleashes a breath of {element} energy!\n",
        damage_message: str = "{target} takes {damage} damage from the breath weapon.\n",
        no_effect_message: str = "The breath weapon has no effect on {target}.\n",
    ):
        self.multiplier = multiplier
        self.element = element
        self.announce_message = announce_message
        self.damage_message = damage_message
        self.no_effect_message = no_effect_message

    def apply(self, actor: Character, target: Character, result: CombatResult) -> None:
        import random as _rng

        from src.core.constants import DAMAGE_VARIANCE_HIGH, DAMAGE_VARIANCE_LOW

        messages = result.extra.setdefault("messages", [])

        # Allow element override from caller kwargs
        typ = result.extra.get("use_kwargs", {}).get("typ", self.element)

        base_damage = int((actor.stats.strength + actor.stats.intel) * self.multiplier)
        variance = _rng.uniform(DAMAGE_VARIANCE_LOW, DAMAGE_VARIANCE_HIGH)
        damage = int(base_damage * variance)

        hit, defense_msg, damage = target.handle_defenses(actor, damage, typ=typ)
        reduction_msg = ""
        if hit:
            _, reduction_msg, damage = target.damage_reduction(damage, actor, typ=typ)

        messages.append(self.announce_message.format(actor=actor.name, element=typ))
        if defense_msg:
            messages.append(defense_msg)
        if reduction_msg:
            messages.append(reduction_msg)

        if damage > 0:
            target.health.current -= damage
            result.damage = damage
            try:
                actor._emit_damage_event(target, damage, damage_type=typ, is_critical=False)
            except Exception:
                pass
            messages.append(self.damage_message.format(target=target.name, damage=damage))
        else:
            messages.append(self.no_effect_message.format(target=target.name))


class NightmareFuelEffect:
    """
    Requires the target to be asleep.  ``damage = sleep_duration * intel
    * crit_multiplier * variance``.  Intel-vs-wisdom contest to land.
    50% crit chance.
    """

    def __init__(
        self,
        crit_chance: float = 0.5,
        damage_message: str = ("{actor} invades {target}'s dreams, dealing {damage} damage"),
        fail_message: str = "{target} resists the spell.\n",
        no_sleep_message: str = "The spell does nothing.\n",
    ):
        self.crit_chance = crit_chance
        self.damage_message = damage_message
        self.fail_message = fail_message
        self.no_sleep_message = no_sleep_message

    def apply(self, actor: Character, target: Character, result: CombatResult) -> None:
        import random as _rng

        from src.core.constants import DAMAGE_VARIANCE_HIGH, DAMAGE_VARIANCE_LOW

        messages = result.extra.setdefault("messages", [])

        if not target.status_effects["Sleep"].active:
            messages.append(self.no_sleep_message)
            return

        # Intel vs wisdom contest
        if _rng.randint(actor.stats.intel // 2, actor.stats.intel) > _rng.randint(
            target.stats.wisdom // 2, target.stats.wisdom
        ):
            crit = 2 if _rng.random() > self.crit_chance else 1
            variance = _rng.uniform(DAMAGE_VARIANCE_LOW, DAMAGE_VARIANCE_HIGH)
            damage = int(
                target.status_effects["Sleep"].duration * actor.stats.intel * crit * variance
            )
            target.health.current -= damage
            result.damage = damage

            dmg_msg = self.damage_message.format(
                actor=actor.name, target=target.name, damage=damage
            )
            if crit > 1:
                dmg_msg += " (Critical hit!)"
            messages.append(dmg_msg + ".\n")
        else:
            messages.append(self.fail_message.format(target=target.name))


class WidowsWailEffect:
    """
    Damage = ``min(max_damage, (health.max / health.current) * multiplier)``.
    Independent intel-vs-wisdom contests for self-damage and target-damage.
    Ice Block / tunnel blocks target-damage only.
    """

    def __init__(
        self,
        multiplier: int = 20,
        max_damage: int = 200,
        self_message: str = "Anguish overwhelms {name}, taking {damage} damage.\n",
        target_message: str = "Anguish overwhelms {name}, taking {damage} damage.\n",
    ):
        self.multiplier = multiplier
        self.max_damage = max_damage
        self.self_message = self_message
        self.target_message = target_message

    def apply(self, actor: Character, target: Character, result: CombatResult) -> None:
        import random as _rng

        messages = result.extra.setdefault("messages", [])

        dmg = int((actor.health.max / max(1, actor.health.current)) * self.multiplier)
        damage = min(self.max_damage, dmg)

        # Self-damage: intel vs wisdom (actor vs self)
        if _rng.randint(actor.stats.intel // 2, actor.stats.intel) > _rng.randint(
            actor.stats.wisdom // 2, actor.stats.wisdom
        ):
            messages.append(self.self_message.format(name=actor.name, damage=damage))
            actor.health.current -= damage

        # Target-damage: skip if ice block / tunnel
        if any(
            [
                target.magic_effects["Ice Block"].active,
                getattr(target, "tunnel", False),
            ]
        ):
            return

        # Target-damage: intel vs wisdom (actor vs target)
        if _rng.randint(actor.stats.intel // 2, actor.stats.intel) > _rng.randint(
            target.stats.wisdom // 2, target.stats.wisdom
        ):
            messages.append(self.target_message.format(name=target.name, damage=damage))
            target.health.current -= damage
            result.damage = damage


class GoblinPunchEffect:
    """
    ``num_attacks = randint(pro_level, max_punches)``.  Each punch deals
    ``str_diff = max(1 + pro_level, (target.str - user.str) // 2)`` damage
    if it hits (standard hit_chance).
    """

    def __init__(
        self,
        max_punches: int = 5,
        hit_message: str = "{actor} punches {target} for {damage} damage.\n",
        miss_message: str = "{actor} punches air, missing {target}.\n",
    ):
        self.max_punches = max_punches
        self.hit_message = hit_message
        self.miss_message = miss_message

    def apply(self, actor: Character, target: Character, result: CombatResult) -> None:
        import random as _rng

        messages = result.extra.setdefault("messages", [])

        num_attacks = max(1, _rng.randint(actor.level.pro_level, self.max_punches))
        str_diff = max(
            1 + actor.level.pro_level,
            (target.stats.strength - actor.stats.strength) // 2,
        )
        total_damage = 0
        for _ in range(num_attacks):
            if actor.resolve_contact(target, typ="weapon", rng=_rng).hit:
                target.health.current -= str_diff
                total_damage += str_diff
                messages.append(
                    self.hit_message.format(
                        actor=actor.name,
                        target=target.name,
                        damage=str_diff,
                    )
                )
            else:
                messages.append(
                    self.miss_message.format(
                        actor=actor.name,
                        target=target.name,
                    )
                )
        result.damage = total_damage


class HexEffect:
    """
    Attempt to apply Poison, Blind, and Silence independently.  Each has
    its own immunity / pendant / already-active check and a separate stat
    contest (intel vs con for Poison & Blind, intel vs wisdom for Silence).
    """

    def __init__(
        self,
        duration: int = 3,
        announce_message: str = "{caster} curses {target} with a hex.\n",
        poison_message: str = "{target} is poisoned.\n",
        blind_message: str = "{target} is blinded.\n",
        silence_message: str = "{target} is silenced.\n",
        no_effect_message: str = "The hex has no effect.\n",
    ):
        self.duration = duration
        self.announce_message = announce_message
        self.poison_message = poison_message
        self.blind_message = blind_message
        self.silence_message = silence_message
        self.no_effect_message = no_effect_message

    def _is_immune(self, target: Character, status_name: str) -> bool:
        """Check immunity via status_immunity list and pendant."""
        return any(
            [
                status_name in getattr(target, "status_immunity", []),
                f"Status-{status_name}" in target.equipment["Pendant"].mod,
                "Status-All" in target.equipment["Pendant"].mod,
            ]
        )

    def apply(self, actor: Character, target: Character, result: CombatResult) -> None:
        import random as _rng

        messages = result.extra.setdefault("messages", [])
        messages.append(self.announce_message.format(caster=actor.name, target=target.name))
        applied = False

        # ── Poison: intel vs con ──
        if not self._is_immune(target, "Poison"):
            if not target.status_effects["Poison"].active:
                if _rng.randint(actor.stats.intel // 2, actor.stats.intel) > _rng.randint(
                    target.stats.con // 2, target.stats.con
                ):
                    poison_damage = max(1, actor.stats.intel // 4)
                    target.status_effects["Poison"].active = True
                    target.status_effects["Poison"].duration = max(
                        self.duration,
                        target.status_effects["Poison"].duration,
                    )
                    target.status_effects["Poison"].extra = max(
                        poison_damage,
                        target.status_effects["Poison"].extra,
                    )
                    try:
                        actor._emit_status_event(
                            target,
                            "Poison",
                            applied=True,
                            duration=target.status_effects["Poison"].duration,
                            source="Hex",
                        )
                    except Exception:
                        pass
                    messages.append(self.poison_message.format(target=target.name))
                    applied = True

        # ── Blind: intel vs con ──
        if not self._is_immune(target, "Blind"):
            if not target.status_effects["Blind"].active:
                if _rng.randint(actor.stats.intel // 2, actor.stats.intel) > _rng.randint(
                    target.stats.con // 2, target.stats.con
                ):
                    target.status_effects["Blind"].active = True
                    target.status_effects["Blind"].duration = max(
                        self.duration,
                        target.status_effects["Blind"].duration,
                    )
                    try:
                        actor._emit_status_event(
                            target,
                            "Blind",
                            applied=True,
                            duration=target.status_effects["Blind"].duration,
                            source="Hex",
                        )
                    except Exception:
                        pass
                    messages.append(self.blind_message.format(target=target.name))
                    applied = True

        # ── Silence: intel vs wisdom ──
        if not self._is_immune(target, "Silence"):
            if not target.status_effects["Silence"].active:
                if _rng.randint(actor.stats.intel // 2, actor.stats.intel) > _rng.randint(
                    target.stats.wisdom // 2, target.stats.wisdom
                ):
                    target.status_effects["Silence"].active = True
                    target.status_effects["Silence"].duration = max(
                        self.duration,
                        target.status_effects["Silence"].duration,
                    )
                    try:
                        actor._emit_status_event(
                            target,
                            "Silence",
                            applied=True,
                            duration=target.status_effects["Silence"].duration,
                            source="Hex",
                        )
                    except Exception:
                        pass
                    messages.append(self.silence_message.format(target=target.name))
                    applied = True

        if not applied:
            messages.append(self.no_effect_message)


class VulcanizeEffect:
    """
    Deals fire damage to the *caster* based on fire resistance and current
    health, then grants a defense buff if still alive.  Always targets
    self (ignores the ``target`` argument).
    """

    def __init__(
        self,
        health_fraction: float = 0.1,
        buff_duration: int = 5,
        buff_lo_divisor: int = 4,
        buff_hi_divisor: int = 2,
        damage_message: str = "{target} takes {damage} damage from the flames.\n",
        heal_message: str = "{target} is healed by the flames for {damage} hit points.\n",
        buff_message: str = "{target} is hardened by the flames.\n",
    ):
        self.health_fraction = health_fraction
        self.buff_duration = buff_duration
        self.buff_lo_divisor = buff_lo_divisor
        self.buff_hi_divisor = buff_hi_divisor
        self.damage_message = damage_message
        self.heal_message = heal_message
        self.buff_message = buff_message

    def apply(self, actor: Character, target: Character, result: CombatResult) -> None:
        import random as _rng

        # target is always self (set by DataDrivenSupportSpell)
        messages = result.extra.setdefault("messages", [])

        fire_resist = target.check_mod("resist", enemy=actor, typ="Fire")
        damage = int((1 - fire_resist) * (target.health.current * self.health_fraction))
        target.health.current -= damage
        try:
            actor._emit_damage_event(target, damage, damage_type="Fire", is_critical=False)
        except Exception:
            pass

        if damage > 0:
            messages.append(self.damage_message.format(target=target.name, damage=damage))
        elif damage < 0:
            messages.append(self.heal_message.format(target=target.name, damage=abs(damage)))

        if target.is_alive():
            def_gain = target.combat.defense + actor.stats.intel
            target.stat_effects["Defense"].active = True
            target.stat_effects["Defense"].duration = self.buff_duration
            target.stat_effects["Defense"].extra = _rng.randint(
                def_gain // self.buff_lo_divisor,
                def_gain // self.buff_hi_divisor,
            )
            messages.append(self.buff_message.format(target=target.name))


class HolyFollowupEffect:
    """
    Holy spell damage pipeline executed after a successful weapon hit
    (used by Smite and its upgrades).

    Reads ``dmg_mod`` and ``last_crit`` from ``result.extra``.

    Pipeline: spell_mod (half-to-full) → dmg_mod × spell_mod × crit →
    Mana Shield / Crusader Shield → Holy resist → if absorbed: heal;
    else armor curve (magic def) → variance → CON save (half) → damage.
    """

    def __init__(
        self,
        resist_type: str = "Holy",
        damage_message: str = "{actor} smites {target} for {damage} hit points.\n",
        ineffective_message: str = "{name} was ineffective and does no damage.\n",
        absorb_message: str = "{target} absorbs {subtyp} and is healed for {heal} health.\n",
        con_save_message: str = "{target} shrugs off the {name} and only receives half of the damage.\n",
    ):
        self.resist_type = resist_type
        self.damage_message = damage_message
        self.ineffective_message = ineffective_message
        self.absorb_message = absorb_message
        self.con_save_message = con_save_message

    def apply(self, actor: Character, target: Character, result: CombatResult) -> None:
        import random as _rng

        from src.core.constants import (
            ARMOR_SCALING_FACTOR,
            DAMAGE_VARIANCE_HIGH,
            DAMAGE_VARIANCE_LOW,
        )

        messages = result.extra.setdefault("messages", [])
        dmg_mod = result.extra.get("dmg_mod", 1.0)
        crit = result.extra.get("last_crit", 1)

        spell_mod = actor.check_mod("magic", enemy=target)
        spell_mod = _rng.randint(spell_mod // 2, spell_mod)
        dam_red = target.check_mod("magic def", enemy=actor)
        resist = target.check_mod("resist", enemy=actor, typ=self.resist_type)

        damage = int(dmg_mod * spell_mod)
        damage *= crit
        try:
            from src.core.classes import paladin

            damage = int(damage * paladin.holy_damage_multiplier(actor))
        except Exception:
            pass

        # Mana Shield / Crusader Shield
        if target.magic_effects["Mana Shield"].active:
            damage, shield_msg, absorbed = actor._apply_mana_shield(
                target,
                damage,
                physical=False,
            )
            messages.append(shield_msg)
        elif (
            target.cls.name == "Crusader"
            and getattr(target, "power_up", False)
            and target.class_effects["Power Up"].active
        ):
            damage, shield_msg, absorbed = actor._apply_crusader_shield(target, damage)
            messages.append(shield_msg)

        # Holy resist
        damage = int(damage * (1 - resist))

        if damage < 0:
            target.health.current -= damage
            messages.append(
                self.absorb_message.format(
                    target=target.name,
                    subtyp=self.resist_type,
                    heal=abs(damage),
                )
            )
        else:
            # Armor curve
            damage = int(damage * (1 - (dam_red / (dam_red + ARMOR_SCALING_FACTOR))))
            # Variance
            variance = _rng.uniform(DAMAGE_VARIANCE_LOW, DAMAGE_VARIANCE_HIGH)
            damage = int(damage * variance)

            if damage <= 0:
                damage = 0
                messages.append(self.ineffective_message.format(name="Smite"))
            elif _rng.randint(0, target.stats.con // 2) > _rng.randint(
                (actor.stats.intel * crit) // 2,
                (actor.stats.intel * crit),
            ):
                # CON save → half damage
                damage //= 2
                if damage > 0:
                    messages.append(self.con_save_message.format(target=target.name, name="Smite"))
                    messages.append(
                        self.damage_message.format(
                            actor=actor.name,
                            target=target.name,
                            damage=damage,
                        )
                    )
                else:
                    messages.append(self.ineffective_message.format(name="Smite"))
            else:
                messages.append(
                    self.damage_message.format(
                        actor=actor.name,
                        target=target.name,
                        damage=damage,
                    )
                )

            target.health.current -= damage
            result.damage = (result.damage or 0) + damage


class TurnUndeadEffect:
    """
    Only works on Undead targets.  Luck-based instant-kill chance, with
    a fallback holy-damage pipeline (spell_mod half-to-full, armor curve,
    Holy resist, variance).

    Reads ``dmg_mod`` and ``crit_chance`` from ``result.extra`` (set by
    the DataDriven wrapper).
    """

    def __init__(
        self,
        luck_factor: int = 6,
        kill_message: str = "The {target} has been rebuked, destroying the undead monster.\n",
        no_undead_message: str = "The spell does nothing.\n",
        damage_message: str = "{actor} damages {target} for {damage} hit points",
    ):
        self.luck_factor = luck_factor
        self.kill_message = kill_message
        self.no_undead_message = no_undead_message
        self.damage_message = damage_message

    def apply(self, actor: Character, target: Character, result: CombatResult) -> None:
        import random as _rng

        from src.core.constants import (
            ARMOR_SCALING_FACTOR,
            DAMAGE_VARIANCE_HIGH,
            DAMAGE_VARIANCE_LOW,
        )

        messages = result.extra.setdefault("messages", [])
        dmg_mod = result.extra.get("dmg_mod", 1.5)
        crit_chance = result.extra.get("crit_chance", 5)

        if getattr(target, "enemy_typ", None) != "Undead":
            messages.append(self.no_undead_message)
            return

        # Crit roll
        crit = 1
        if not _rng.randint(0, crit_chance):
            crit = 2

        # Kill chance (luck-based)
        chance = max(
            2,
            target.check_mod("luck", enemy=actor, luck_factor=self.luck_factor),
        )
        if crit > 1:
            chance -= 1
        if not _rng.randint(0, chance):
            target.health.current = 0
            result.damage = target.health.max
            messages.append(self.kill_message.format(target=target.name))
            return

        # Fallback holy damage
        spell_mod = actor.check_mod("magic", enemy=target)
        spell_mod = _rng.randint(spell_mod // 2, spell_mod)
        dam_red = target.check_mod("magic def", enemy=actor)
        resist = target.check_mod("resist", enemy=actor, typ="Holy")

        damage = int(dmg_mod * spell_mod)
        damage *= crit
        damage = int(damage * (1 - resist) * (1 - (dam_red / (dam_red + ARMOR_SCALING_FACTOR))))
        variance = _rng.uniform(DAMAGE_VARIANCE_LOW, DAMAGE_VARIANCE_HIGH)
        damage = int(damage * variance)

        target.health.current -= damage
        result.damage = damage

        dmg_msg = self.damage_message.format(actor=actor.name, target=target.name, damage=damage)
        if crit > 1:
            dmg_msg += " (Critical hit!)"
        messages.append(dmg_msg + ".\n")
