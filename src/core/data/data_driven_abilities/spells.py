"""Data-driven healing, support, and status spell implementations."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from typing import Any

    from src.core.character import Character
    from src.core.effects.base import Effect

from src.core.combat.combat_result import CombatResult
from src.core.randomness import gameplay_random as random

from .base import _get_heal_spell_class, _get_status_spell_class, _get_support_spell_class


class DataDrivenHealSpell(_get_heal_spell_class()):
    """
    A heal spell loaded from YAML.  Supports instant heal, HoT (Regen),
    and hybrid (Hydration = instant + HoT).  Also provides ``cast_out()``
    for the out-of-combat healing UI.
    """

    def __init__(
        self,
        name: str,
        description: str,
        cost: int,
        heal: float,
        crit: int,
        turns: int = 0,
        effects: list[Effect] | None = None,
        rank: int | None = None,
        instant_heal: bool = False,
    ):
        super().__init__(name, description, cost, heal, crit)
        self.turns = turns
        self.combat = turns > 0
        self.rank = rank
        self._effects: list[Effect] = effects or []
        self._instant_heal = instant_heal

    def _apply_instant_healing(
        self,
        caster: Character,
        target: Character,
        heal: int,
    ) -> int:
        try:
            from src.core.classes import nature_totems

            heal = int(heal * nature_totems.spell_output_multiplier(caster, self.name))
        except Exception:
            pass
        return super()._apply_instant_healing(caster, target, heal)

    # -- HoT helper (Regen pattern) ------------------------------------
    def hot(self, target: Character, heal: int) -> None:
        """Apply heal-over-time using the Regen magic effect."""
        target.magic_effects["Regen"].active = True
        target.magic_effects["Regen"].duration = max(
            self.turns, target.magic_effects["Regen"].duration
        )
        target.magic_effects["Regen"].extra = max(heal, target.magic_effects["Regen"].extra)
        try:
            target._emit_status_event(
                target,
                "Regen",
                applied=True,
                duration=target.magic_effects["Regen"].duration,
                source="Heal",
            )
        except Exception:
            pass

    # -- cast override to support Hydration hybrid ---------------------
    def cast(
        self,
        caster: Character,
        target: Character | None = None,
        cover: bool = False,
        special: bool = False,
        fam: bool = False,
        **_kwargs: Any,
    ) -> str:
        resolved_target = target if fam else caster
        health_before = int(resolved_target.health.current) if resolved_target is not None else 0
        if self._instant_heal and self.turns > 0:
            message = self._cast_hybrid(caster, target, cover, special, fam)
        else:
            message = super().cast(caster, target, cover, special, fam)
        actual_healing = (
            max(0, int(resolved_target.health.current) - health_before)
            if resolved_target is not None
            else 0
        )
        if actual_healing:
            try:
                from src.core.classes import paladin

                message += paladin.radiant_healing_damage(
                    caster,
                    actual_healing,
                    source=self.name,
                )
            except (AttributeError, KeyError, TypeError, ValueError):
                pass
        return message

    def _cast_hybrid(
        self,
        caster: Character,
        target: Character | None,
        cover: bool,
        special: bool,
        fam: bool,
    ) -> str:
        """Hydration-style: instant heal THEN apply HoT."""
        cast_message = ""
        if not fam:
            target = caster
        if not (special or fam):
            caster.mana.current -= self.cost
        crit = 1
        heal_mod = caster.check_mod("heal")
        heal = int(
            (random.randint(target.health.max // 2, target.health.max) + heal_mod) * self.heal
        )
        if not random.randint(0, self.crit):
            cast_message += "Critical Heal!\n"
            crit = 2
        crit_per = random.uniform(1, crit)
        heal = int(heal * crit_per)
        actual_heal = self._apply_instant_healing(caster, target, heal)
        cast_message += f"{caster.name} heals {target.name} for {actual_heal} hit points.\n"
        if target.health.current >= target.health.max:
            target.health.current = target.health.max
            cast_message += f"{target.name} is at full health.\n"
        self.hot(target, actual_heal)
        return cast_message

    # -- out-of-combat heal --------------------------------------------
    def cast_out(self, actor: Character) -> str:
        """UI-agnostic out-of-combat heal."""
        cast_message = f"{actor.name} casts {self.name}.\n"
        if actor.health.current == actor.health.max:
            cast_message += "You are already at full health.\n"
            return cast_message
        actor.mana.current -= self.cost
        crit = 1
        heal_mod = actor.check_mod("heal")
        heal = int(actor.health.max * self.heal + heal_mod)
        if not random.randint(0, self.crit):
            cast_message += "Critical Heal!\n"
            crit = 2
        heal *= crit
        actual_heal = self._apply_instant_healing(actor, actor, heal)
        cast_message += f"{actor.name} heals themself for {actual_heal} hit points.\n"
        if actor.health.current >= actor.health.max:
            actor.health.current = actor.health.max
            cast_message += f"{actor.name} is at full health.\n"
        return cast_message


# ======================================================================
# DataDrivenSupportSpell - replaces SupportSpell / IllusionSpell subs
# ======================================================================


class DataDrivenSupportSpell(_get_support_spell_class()):
    """
    A self-targeting buff spell loaded from YAML.  The effects list handles
    all buff application (stat buffs, magic effects, cleanse, etc.).
    Messages are collected from ``result.extra["messages"]`` set by effects,
    or from the optional static ``message`` template.
    """

    def __init__(
        self,
        name: str,
        description: str,
        cost: int,
        effects: list[Effect] | None = None,
        school: str | None = None,
        rank: int | None = None,
        target_self: bool = True,
        wizard_free_cast: bool = False,
        message: str | None = None,
        subtype: str = "Support",
    ):
        super().__init__(name, description, cost)
        self._effects: list[Effect] = effects or []
        self.school = school
        self.rank = rank
        self._target_self = target_self
        self._wizard_free_cast = wizard_free_cast
        self._message = message
        self.subtyp = subtype

    def cast(
        self,
        caster: Character,
        target: Character | None = None,
        cover: bool = False,
        special: bool = False,
        fam: bool = False,
        **_kwargs: Any,
    ) -> str:
        if self._target_self and not fam:
            target = caster
        elif target is None:
            target = caster

        if not (
            special
            or fam
            or (
                self._wizard_free_cast
                and caster.cls.name == "Wizard"
                and caster.class_effects["Power Up"].active
            )
        ):
            caster.mana.current -= self.cost

        result = CombatResult(action=self.name, actor=caster, target=target)

        for effect in self._effects:
            try:
                effect.apply(caster, target, result)
            except Exception:
                continue

        # Collect messages from effects
        messages = result.extra.get("messages", [])

        # Stat buff messages (from DynamicStatBuffEffect)
        for stat, amount in result.extra.get("buff_amounts", {}).items():
            messages.append(f"{target.name}'s {stat.lower()} increases by {amount}.")

        # Cleanse message
        if result.effects_applied.get("Cleansed"):
            messages.append(f"All negative status effects have been cured for " f"{target.name}!")

        # Magic effect messages
        for eff_name in result.effects_applied.get("Magic", []):
            _magic_msgs = {
                "Ice Block": (
                    f"{target.name} encases themself in a block of ice, "
                    "making them invulnerable for a time."
                ),
                "Duplicates": (
                    f"{caster.name} creates duplicates of themself "
                    f"to fool {target.name if target != caster else 'the enemy'}."
                ),
                "Reflect": (f"A magic force field envelopes {target.name}."),
                "Astral Shift": (
                    f"{target.name} shifts partially into the astral plane, "
                    "reducing damage taken by 25%."
                ),
                "Regen": f"{target.name} begins to regenerate.",
            }
            messages.append(_magic_msgs.get(eff_name, f"{target.name} gains {eff_name}."))

        # Stat modifier messages for fixed multi_buff (no dynamic amounts)
        for stat_info in result.effects_applied.get("Stat", []):
            if stat_info not in [f"{s} Buff" for s in result.extra.get("buff_amounts", {})]:
                stat = stat_info.replace(" Buff", "").replace(" Debuff", "")
                val = getattr(target.stat_effects.get(stat), "extra", "?")
                messages.append(
                    f"{target.name}'s {stat.lower()} "
                    f"{'increases' if 'Buff' in stat_info else 'decreases'} by {val}."
                )

        # Static message template fallback
        if not messages and self._message:
            messages = [self._message.format(target=target.name, caster=caster.name)]

        if not messages:
            messages = [f"{self.name} was cast."]

        return "\n".join(messages) + "\n"


# ======================================================================
# DataDrivenStatusSpell - replaces StatusSpell subclasses
# ======================================================================


class DataDrivenStatusSpell(_get_status_spell_class()):
    """
    An enemy-targeting debuff/status spell loaded from YAML.  Handles:
    mana cost → Ice Block/tunnel immunity → effects (stat contests wrapping
    status_apply / debuffs / dispels) → message generation.
    """

    _STATUS_MESSAGES: dict[str, dict[str, str]] = {
        "Blind": {
            "success": "{target} is blinded.",
            "immune": "{target} is immune to blind status.",
            "already": "{target} is already blinded.",
        },
        "Sleep": {
            "success": "{target} is asleep.",
            "immune": "{target} is immune to sleep effect.",
            "already": "{target} is already asleep.",
            "resist": "{caster} fails to put {target} to sleep.",
        },
        "Stun": {
            "success": "{target} is stunned.",
            "immune": "{target} is immune to stun effect.",
            "already": "{target} is already stunned.",
            "resist": "{caster} fails to stun {target}.",
        },
        "Silence": {
            "success": "{target} has been silenced.",
            "immune": "{target} is immune to silence.",
        },
        "Berserk": {
            "success": "{target} is enraged.",
            "immune": "{target} is immune to berserk status.",
            "already": "{target} is already enraged.",
        },
    }

    def __init__(
        self,
        name: str,
        description: str,
        cost: int,
        effects: list[Effect] | None = None,
        rank: int | None = None,
        wizard_free_cast: bool = False,
        messages: dict[str, str] | None = None,
        subtype: str | None = None,
        school: str | None = None,
    ):
        super().__init__(name, description, cost)
        self._effects: list[Effect] = effects or []
        self.rank = rank
        self._wizard_free_cast = wizard_free_cast
        self._messages = messages or {}
        if subtype:
            self.subtyp = subtype
        if school:
            self.school = school

    def cast(
        self,
        caster: Character,
        target: Character | None = None,
        cover: bool = False,
        special: bool = False,
        fam: bool = False,
        **_kwargs: Any,
    ) -> str:
        # Mana deduction
        if not (
            special
            or fam
            or (
                self._wizard_free_cast
                and caster.cls.name == "Wizard"
                and caster.class_effects["Power Up"].active
            )
        ):
            caster.mana.current -= self.cost

        # Ice Block / tunnel immunity
        if any([target.magic_effects["Ice Block"].active, target.tunnel]):
            return "It has no effect.\n"

        # Apply effects (stat contest → status_apply / debuff / dispel)
        result = CombatResult(action=self.name, actor=caster, target=target)
        result.extra["last_crit"] = 1

        for effect in self._effects:
            try:
                effect.apply(caster, target, result)
            except Exception:
                continue

        # --- Message generation ---
        fmt = {"target": target.name, "caster": caster.name}

        # Immunity
        immune_status = result.extra.get("status_immune")
        if immune_status:
            msgs = self._STATUS_MESSAGES.get(immune_status, {})
            tmpl = self._messages.get("immune", msgs.get("immune", "{target} is immune."))
            return tmpl.format(**fmt) + "\n"

        # Already active
        already = result.extra.get("status_already_active")
        if already:
            msgs = self._STATUS_MESSAGES.get(already, {})
            tmpl = self._messages.get(
                "already", msgs.get("already", "{target} is already affected.")
            )
            return tmpl.format(**fmt) + "\n"

        # Effect-generated messages (DynamicMultiDebuff, FullDispel)
        effect_msgs = result.extra.get("messages", [])

        # Status applied
        statuses = result.effects_applied.get("Status", [])
        if statuses:
            status = statuses[0]
            msgs = self._STATUS_MESSAGES.get(status, {})
            tmpl = self._messages.get(
                "success",
                msgs.get("success", "{target} is afflicted with " + status.lower() + "."),
            )
            return tmpl.format(**fmt) + "\n"

        # Dispel success
        if result.effects_applied.get("Dispelled") is not None:
            tmpl = self._messages.get(
                "success",
                "All positive status effects removed from {target}.",
            )
            return tmpl.format(**fmt) + "\n"

        # Multi-debuff messages
        if effect_msgs:
            return "\n".join(effect_msgs) + "\n"

        # Contest lost / resist
        if result.extra.get("stat_contest_won") is False:
            # Determine resist message: find first status in effects
            first_status = None
            for eff in self._effects:
                inner = getattr(eff, "effect", None)
                if inner and hasattr(inner, "status_name"):
                    first_status = inner.status_name
                    break
            if first_status:
                msgs = self._STATUS_MESSAGES.get(first_status, {})
                tmpl = self._messages.get("resist", msgs.get("resist", "The spell is ineffective."))
            else:
                tmpl = self._messages.get("resist", "{target} resists the spell.")
            return tmpl.format(**fmt) + "\n"

        return ""
