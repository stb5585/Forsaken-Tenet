"""
Data-Driven Ability Classes

These classes bridge the effects system into actual combat execution.
DataDrivenSpell replicates the Attack.cast() damage pipeline but delegates
secondary effects to composed Effect objects loaded from YAML.

DataDrivenSkill does the same for weapon-based skills.

Both return CombatResult with a populated .message field, so str(result)
works transparently with the existing battle engine code.
"""

from __future__ import annotations

from copy import deepcopy
from typing import TYPE_CHECKING

from src.core.abilities import Spell
from src.core.combat.combat_result import CombatResult, CombatResultGroup
from src.core.combat.reactions import execute_reaction, reaction_result
from src.core.combat.targeting import TargetScope
from src.core.constants import (
    DAMAGE_VARIANCE_HIGH,
    DAMAGE_VARIANCE_LOW,
)
from src.core.randomness import gameplay_random as random

if TYPE_CHECKING:
    from typing import Any

    from src.core.character import Character
    from src.core.effects.base import Effect


# ---------------------------------------------------------------------------
# Lazy imports for base classes exported by the abilities package. We import them
# at call-time to avoid circular-import issues.
# ---------------------------------------------------------------------------
def _get_heal_spell_class():
    from src.core.abilities import HealSpell

    return HealSpell


def _get_support_spell_class():
    from src.core.abilities import SupportSpell

    return SupportSpell


def _get_status_spell_class():
    from src.core.abilities import StatusSpell

    return StatusSpell


def _fate_floor(actor: Character) -> float:
    try:
        return max(0.0, min(1.0, float(getattr(actor, "_runic_boost_floor", 0.0) or 0.0)))
    except (TypeError, ValueError):
        return 0.0


def _floor_uniform(actor: Character, value: float, low: float, high: float) -> float:
    floor = _fate_floor(actor)
    if floor <= 0:
        return value
    return max(value, low + ((high - low) * floor))


def _floor_int(actor: Character, value: int, low: int, high: int) -> int:
    floor = _fate_floor(actor)
    if floor <= 0:
        return value
    return max(value, int(low + ((high - low) * floor)))


class DataDrivenSpell(Spell):
    """
    A spell whose behavior is defined by composed Effect objects + YAML config.

    Replicates the Attack.cast() pipeline (mana → immunity → dodge → crit →
    base damage → defenses → resistance → variance → CON save → apply damage)
    and then executes the composed effects for secondary outcomes (burn, stun,
    chill damage, etc.).

    The .cast() method returns a CombatResult whose __str__ produces the display
    message, so the battle engine's ``str(spell.cast(...))`` works unchanged.
    """

    def __init__(
        self,
        name: str,
        description: str,
        cost: int,
        dmg_mod: float,
        crit: int,
        subtyp: str,
        effects: list[Effect] | None = None,
        school: str | None = None,
        rank: int | None = None,
        charge_time: int | None = None,
        delay: int | None = None,
        telegraph_message: str | None = None,
        priority: str | None = None,
        notes: str | None = None,
        grounded_damage: bool = False,
    ):
        super().__init__(name, description, school=school)
        self.cost = cost
        self.dmg_mod = dmg_mod
        self.crit = crit
        self.subtyp = subtyp
        self.turns = None
        self.rank = rank
        self._effects: list[Effect] = effects or []
        self._charge_time = charge_time
        self._delay = delay
        self._telegraph_message = telegraph_message
        self._priority = priority
        self._notes = notes
        self._grounded_damage = grounded_damage

    # ------------------------------------------------------------------
    # Attack.cast() replica with composed-effects integration
    # ------------------------------------------------------------------
    @reaction_result
    def cast(
        self,
        caster: Character,
        target: Character = None,
        cover: bool = False,
        special: bool = False,
        fam: bool = False,
        **kwargs: Any,
    ) -> CombatResult:
        result = self._reset_result(actor=caster, target=target)
        effective_cost = self.cost
        try:
            from src.core.classes import mage_mechanics

            effective_cost = mage_mechanics.spell_mana_cost(caster, self)
        except Exception:
            pass
        result.extra["cost"] = effective_cost
        msg = ""

        # ── 1. Mana cost ────────────────────────────────────────────
        if not kwargs.get("_skip_cost", False) and not (
            special
            or fam
            or (caster.cls.name == "Wizard" and caster.class_effects["Power Up"].active)
        ):
            caster.mana.current -= effective_cost

        # ── 2. Immunity checks ──────────────────────────────────────
        if any([target.magic_effects["Ice Block"].active, target.tunnel]):
            result.hit = False
            result.message = "It has no effect.\n"
            return result
        if self._grounded_damage and getattr(target, "flying", False):
            result.hit = False
            result.extra["no_effect_reason"] = "flying"
            result.message = f"{target.name} is airborne; the grounded spell has no effect.\n"
            return result

        # ── 3. Reflect ──────────────────────────────────────────────
        reaction_owner = target
        reflect = target.magic_effects["Reflect"].active

        # ── 4. Dodge / hit rolls ────────────────────────────────────
        spell_mod = caster.check_mod("magic", enemy=target)
        fire_inside_bonus = 0.0
        try:
            from ...classes import mage_mechanics

            fire_inside_bonus = mage_mechanics.fire_inside_critical_bonus(caster)
            mage_mechanics.consume_fire_inside(caster)
        except Exception:
            pass
        contact = caster.resolve_contact(
            target,
            typ="magic",
            always_hit=target.incapacitated(),
            rng=random,
        )
        if not contact.hit and not reflect:
            if contact.attribution is not None and contact.attribution.value == "dodge":
                msg += f"{target.name} dodged the {self.name} and was unhurt.\n"
                result.dodge = True
            else:
                msg += f"The spell misses {target.name}.\n"
            result.hit = False
            result.message = msg
            return result

        # ── 5. Crit roll ────────────────────────────────────────────
        if reflect:
            result.extra["reflected_by"] = target.name
            target = caster
            result.target = target
            msg += f"{self.name} is reflected back at {caster.name}!\n"

        crit = 1
        if not random.randint(0, self.crit):
            crit = 2
        if fire_inside_bonus and random.random() < fire_inside_bonus:
            crit = 2
        crit_per = _floor_uniform(caster, random.uniform(1, crit), 1, crit)
        try:
            from ...classes import mage_mechanics

            if mage_mechanics.school_from_ability(self) == "Arcane":
                crit_per = mage_mechanics.arcane_critical_multiplier(
                    caster,
                    crit_per,
                    self,
                )
        except Exception:
            pass
        result.crit = crit_per if crit > 1 else None

        # ── 6. Base damage ──────────────────────────────────────────
        damage = int(self.dmg_mod * spell_mod * crit_per)

        # ── 7. Defenses & resistance ────────────────────────────────
        hit, message, damage = target.handle_defenses(caster, damage, cover, typ="Magic")
        msg += message
        piercing_bolt = self.name.startswith("Shadow Bolt") and "Piercing Bolt" in getattr(
            caster, "spellbook", {}
        ).get("Skills", {})
        caster._piercing_bolt_cast = piercing_bolt
        try:
            hit, message, damage = target.damage_reduction(damage, caster, typ=self.subtyp)
        finally:
            caster._piercing_bolt_cast = False
        msg += message

        if hit:
            # ── 8. Class bonuses ────────────────────────────────────
            if (
                caster.cls.name == "Archbishop"
                and caster.class_effects["Power Up"].active
                and self.subtyp == "Holy"
            ):
                damage = int(damage * 1.25)

            if damage < 0:
                # Absorption - target heals
                target.health.current -= damage
                msg += (
                    f"{target.name} absorbs {self.subtyp} and is healed for {abs(damage)} health.\n"
                )
            else:
                # ── 9. Variance ─────────────────────────────────────
                variance = _floor_uniform(
                    caster,
                    random.uniform(DAMAGE_VARIANCE_LOW, DAMAGE_VARIANCE_HIGH),
                    DAMAGE_VARIANCE_LOW,
                    DAMAGE_VARIANCE_HIGH,
                )
                damage = int(damage * variance)
                try:
                    from src.core.classes import nature_totems

                    damage = int(damage * nature_totems.spell_output_multiplier(caster, self))
                except Exception:
                    pass
                try:
                    from src.core.classes import pathfinder

                    damage = int(damage * pathfinder.spell_output_multiplier(caster, self))
                except Exception:
                    pass
                skills = getattr(caster, "spellbook", {}).get("Skills", {})
                school_name = str(getattr(self, "school", "") or self.subtyp)
                if (
                    fam
                    and getattr(getattr(caster, "familiar", None), "spec", "") == "Arcane"
                    and "Insult to Injury" in skills
                    and school_name == "Arcane"
                    and str(getattr(target.magic_effects.get("DOT"), "source", ""))
                    .lower()
                    .startswith("corruption")
                ):
                    damage = int(damage * 1.50)
                if (
                    school_name in {"Shadow", "Dark"}
                    and "Penny Dreadful" in skills
                    and getattr(target.status_effects.get("Fear"), "active", False)
                ):
                    damage = int(damage * 1.25)
                try:
                    from src.core.classes import mage_mechanics, wizard

                    damage = int(damage * mage_mechanics.spell_potency_multiplier(caster, self))
                    damage = int(
                        damage * mage_mechanics.spell_damage_multiplier(caster, self, target)
                    )
                    damage += mage_mechanics.consume_shadow_overheal_bonus(caster, self)
                    school = mage_mechanics.school_from_ability(self)
                    damage = int(damage * (1 + wizard.affinity_damage_bonus(caster, school)))
                except Exception:
                    pass
                try:
                    from src.core.classes import class_rings

                    damage = int(
                        damage
                        * class_rings.shadowcaster_shade_damage_multiplier(
                            caster,
                            self.subtyp,
                        )
                    )
                except Exception:
                    pass

                if damage <= 0:
                    msg += "The spell was ineffective and does no damage.\n"
                    damage = 0
                else:
                    target_roll = random.randint(0, target.stats.con // 2)
                    caster_lo = (caster.stats.intel * crit) // 2
                    caster_hi = caster.stats.intel * crit
                    caster_roll = _floor_int(
                        caster,
                        random.randint(caster_lo, caster_hi),
                        caster_lo,
                        caster_hi,
                    )
                    resisted = target_roll > caster_roll
                    if resisted:
                        # ── 10. CON save → half damage ──────────────────
                        damage //= 2
                        if damage > 0:
                            msg += (
                                f"{target.name} shrugs off the spell and only "
                                f"receives half of the damage.\n"
                            )
                            damage_msg = (
                                f"{caster.name} damages {target.name} for {damage} hit points"
                            )
                            if crit > 1:
                                damage_msg += " (Critical hit!)"
                            msg += damage_msg + ".\n"
                        else:
                            msg += "The spell was ineffective and does no damage.\n"
                    else:
                        damage_msg = f"{caster.name} damages {target.name} for {damage} hit points"
                        if crit > 1:
                            damage_msg += " (Critical hit!)"
                        msg += damage_msg + ".\n"

                try:
                    from src.core.classes import promotion_kits

                    damage, block_message = promotion_kits.apply_spell_block(
                        target,
                        caster,
                        damage,
                        spell=self,
                    )
                    msg += block_message
                    damage, shield_message, _fully_absorbed = promotion_kits.absorb_novel_shield(
                        target,
                        damage,
                        source="reflected" if reflect else "spell",
                    )
                    msg += shield_message
                except Exception:
                    pass

                # ── 11. Apply damage ────────────────────────────────
                if crit > 1:
                    try:
                        from src.core.classes import healer

                        damage, delayed_message = healer.delay_critical_damage(
                            target,
                            damage,
                        )
                        msg += delayed_message
                    except Exception:
                        pass
                target.health.current -= damage
                caster._emit_damage_event(
                    target,
                    damage,
                    damage_type=self.subtyp,
                    is_critical=(crit > 1),
                    ability_name=self.name,
                    attack_source="spell",
                    source="spell",
                )
                try:
                    from src.core.classes import promotion_kits

                    msg += promotion_kits.pop_messages(caster)
                    msg += promotion_kits.pop_messages(target)
                except Exception:
                    pass
                result.damage = damage
                result.hit = True

                # ── 12. Execute composed effects (secondary) ────────
                if target.is_alive() and damage > 0:
                    effect_target = caster if reflect else target
                    msg += self._apply_effects(caster, effect_target, damage, crit, result)

            # ── 13. Counterspell check ──────────────────────────────
            if "Counterspell" in reaction_owner.spellbook.get("Spells", {}) and not random.randint(
                0, 4
            ):
                from src.core.abilities import Counterspell

                counterspell = execute_reaction(
                    "counterspell",
                    reaction_owner,
                    lambda: Counterspell().use(reaction_owner, caster),
                )
                if counterspell:
                    msg += f"{reaction_owner.name} uses Counterspell.\n"
                    msg += counterspell
        else:
            msg += f"The spell misses {target.name}.\n"

        # ── 14. Wizard mana regen on Power Up ───────────────────────
        if caster.cls.name == "Wizard" and caster.class_effects["Power Up"].active and damage > 0:
            msg += f"{caster.name} regens {damage} mana.\n"
            caster.mana.current += damage
            if caster.mana.current > caster.mana.max:
                caster.mana.current = caster.mana.max

        result.message = msg
        return result

    def cast_group(
        self,
        caster: Character,
        targets: list[tuple[str, Character]],
        *,
        battle_engine: Any,
    ) -> CombatResultGroup:
        """Resolve one paid cast independently against an authored target snapshot."""
        group = CombatResultGroup(
            action=self.name,
            actor_id=battle_engine.current_actor_id,
            target_scope=TargetScope.ALL_ENEMIES,
            target_ids=tuple(target_id for target_id, _target in targets),
        )
        for index, (target_id, target) in enumerate(targets):
            member = battle_engine.encounter.member_by_id(target_id)
            if not member.is_living_hostile:
                result = CombatResult(
                    action=self.name,
                    actor=caster,
                    target=target,
                    actor_id=battle_engine.current_actor_id,
                    target_id=target_id,
                    hit=False,
                    extra={
                        "skipped": True,
                        "reason": "target_unavailable",
                        "display_label": member.display_label,
                    },
                    message=f"{member.display_label} is no longer a valid target.\n",
                )
            else:
                with battle_engine._target_resolution_context(
                    member,
                    TargetScope.ALL_ENEMIES,
                    group.target_ids,
                ):
                    result = deepcopy(
                        self.cast(
                            caster,
                            target=target,
                            _skip_cost=index > 0,
                        )
                    )
                result.actor_id = battle_engine.current_actor_id
                result.target_id = target_id
                result.extra["display_label"] = member.display_label
                battle_engine._attempt_member_resurrection(member)
                battle_engine._record_final_enemy_resolutions()
            group.add(result)
        return group

    # ------------------------------------------------------------------
    # Effect execution - replaces the per-subtype special_effect()
    # ------------------------------------------------------------------
    def _apply_effects(
        self,
        caster: Character,
        target: Character,
        damage: int,
        crit: int,
        result: CombatResult,
    ) -> str:
        """
        Execute composed effects and return any messages they generate.

        Effects operate on the CombatResult; any text they produce is
        returned so the caller can append it to the running message.
        """
        msg = ""
        # Store damage/crit context so effects can reference it
        result.extra["last_damage"] = damage
        result.extra["last_crit"] = crit

        for effect in self._effects:
            # Snapshot target HP before effect
            hp_before = target.health.current
            effects_before = {key: list(values) for key, values in result.effects_applied.items()}
            messages_before = len(result.extra.get("messages", []))

            try:
                effect.apply(caster, target, result)
            except Exception:
                # Effects are non-breaking (same philosophy as event bus)
                continue

            # Build messages from observable state changes
            hp_diff = hp_before - target.health.current
            effect_messages = result.extra.get("messages", [])[messages_before:]
            if hp_diff > 0:
                # Effect dealt additional damage beyond the base spell
                if effect_messages:
                    msg += "".join(effect_messages)
                else:
                    msg += f"{target.name} takes an extra {hp_diff} damage.\n"
            elif effect_messages:
                msg += "".join(effect_messages)

            # Check for newly applied status effects
            for status in result.effects_applied.get("Status", []):
                if status not in effects_before.get("Status", []):
                    msg += f"{target.name} is afflicted with {status}.\n"

            for magic_eff in result.effects_applied.get("Magic", []):
                if magic_eff not in effects_before.get("Magic", []):
                    if "DOT" in magic_eff:
                        dot = target.magic_effects.get("DOT")
                        source = str(getattr(dot, "source", "") or "").lower()
                        if source == "burn":
                            msg += f"{target.name} is set ablaze.\n"
                        elif source == "corruption":
                            msg += f"{target.name} is wreathed in corrupting magic.\n"
                        else:
                            msg += f"{target.name} is afflicted by lingering magic.\n"
                    elif magic_eff == "Regen":
                        msg += f"{target.name} begins to regenerate.\n"

        return msg

    def special_effect(
        self,
        caster: Character,
        target: Character,
        damage: int,
        crit: int,
    ) -> str:
        """
        Compatibility shim — if called directly (e.g. from Attack.cast in
        a mixed-inheritance scenario), delegate to the composed effects.
        """
        result = CombatResult(action=self.name, actor=caster, target=target)
        result.damage = damage
        return self._apply_effects(caster, target, damage, crit, result)
