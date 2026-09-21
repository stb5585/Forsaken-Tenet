"""Bespoke Mage-tree spells and trained passives."""

from __future__ import annotations

import math
from copy import deepcopy
from typing import Any

from src.core.randomness import gameplay_random as random

from ..combat.combat_result import CombatResult, CombatResultGroup
from ..combat.targeting import TargetScope
from .base import PowerUp, Spell
from .spell_types import _simple_spell_damage


class _MagePassive(PowerUp):
    """Small passive wrapper used by authored Mage ability nodes."""

    def __init__(self, name: str, description: str) -> None:
        super().__init__(name, description)
        self.passive = True


class _SchoolEnhancement(_MagePassive):
    """Mage passive presented inside every spell of one school."""

    def __init__(self, name: str, description: str, school: str) -> None:
        super().__init__(name, description)
        self.presentation_modifier = True
        self.modifies_school = school


class FireInside(_SchoolEnhancement):
    def __init__(self) -> None:
        super().__init__(
            "Fire Inside",
            "Fire spells have a 20% chance to grant +25% critical chance to "
            "the next attack. The charge expires after 3 turns and is consumed "
            "by the next attack regardless of its result.",
            "Fire",
        )


class FrozenArmor(_SchoolEnhancement):
    def __init__(self) -> None:
        super().__init__(
            "Frozen Armor",
            "Ice spells have a 20% chance to grant +10 Defense and 25% Ice "
            "resistance for one turn.",
            "Ice",
        )


class Electrified(_SchoolEnhancement):
    def __init__(self) -> None:
        super().__init__(
            "Electrified",
            "Electric spells have a 20% chance to electrify the caster for 3 "
            "turns; successful melee attacks against them trigger an "
            "Intelligence-scaled jolt.",
            "Electric",
        )


class WindCurrents(_SchoolEnhancement):
    def __init__(self) -> None:
        super().__init__(
            "Wind Currents",
            "Wind spells have a 20% chance to grant +3 Speed and +10% melee "
            "accuracy for 3 turns.",
            "Wind",
        )


class Refreshment(_SchoolEnhancement):
    def __init__(self) -> None:
        super().__init__(
            "Refreshment",
            "Water spells have a 20% chance to restore 5% of maximum HP and MP.",
            "Water",
        )


class TerraFirma(_SchoolEnhancement):
    def __init__(self) -> None:
        super().__init__(
            "Terra Firma",
            "Earth spells have a 20% chance to increase melee damage by 50% " "for 3 turns.",
            "Earth",
        )


class ClassicalForce(_MagePassive):
    def __init__(self) -> None:
        super().__init__(
            "Classical Force",
            "Specialize School Affinity in elemental magic. Arcane spell "
            "damage, control, barriers, and enhancements operate at 75% potency.",
        )
        self.presentation_modifier = True
        self.modifies_school = "Arcane"


class ArcaneTradition(_MagePassive):
    def __init__(self) -> None:
        super().__init__(
            "Arcane Tradition",
            "Specialize School Affinity in Arcane magic. Elemental spell "
            "damage operates at 75% potency and Enhancement proc chances are halved.",
        )
        self.presentation_modifier = True
        self.modifies_schools = ("Fire", "Ice", "Electric", "Wind", "Water", "Earth")


class ClassicalEnrichment(_MagePassive):
    def __init__(self) -> None:
        super().__init__(
            "Classical Enrichment",
            "Further specialize in elemental magic, lowering Arcane spell "
            "potency by an additional 25%.",
        )
        self.presentation_modifier = True
        self.modifies_school = "Arcane"


class ArcaneRitual(_MagePassive):
    def __init__(self) -> None:
        super().__init__(
            "Arcane Ritual",
            "Further specialize in Arcane magic, lowering elemental spell "
            "potency by an additional 25%.",
        )
        self.presentation_modifier = True
        self.modifies_schools = ("Fire", "Ice", "Electric", "Wind", "Water", "Earth")


class ForceMultiplier(_MagePassive):
    def __init__(self) -> None:
        super().__init__(
            "Force Multiplier",
            "Magic Missile casts cost 25% more mana. Each projectile deals " "25% more damage.",
        )
        self.presentation_modifier = True
        self.modifies = ("Magic Missile", "Magic Missile II", "Magic Missile III")


class ArcaneEmpowerment(_MagePassive):
    def __init__(self) -> None:
        super().__init__(
            "Arcane Empowerment",
            "Gain 5% magic damage for every enemy hit by Kinetic Explosion, "
            "stacking up to five times for the current combat.",
        )
        self.presentation_modifier = True
        self.modifies = ("Kinetic Explosion",)


class _SorcererSchoolModifier(_SchoolEnhancement):
    """Sorcerer passive that adds a rider to every spell of one school."""


class Combustion(_SorcererSchoolModifier):
    def __init__(self) -> None:
        super().__init__(
            "Combustion",
            "Fire spells also burn their targets.",
            "Fire",
        )


class Snowpiercer(_SorcererSchoolModifier):
    def __init__(self) -> None:
        super().__init__(
            "Snowpiercer",
            "Ice spells also deal additional cold damage.",
            "Ice",
        )


class Paralyzer(_SorcererSchoolModifier):
    def __init__(self) -> None:
        super().__init__(
            "Paralyzer",
            "Electric spells gain a chance to stun their targets.",
            "Electric",
        )


class EjectionGale(_SorcererSchoolModifier):
    def __init__(self) -> None:
        super().__init__(
            "Ejection Gale",
            "Wind spells can eject their targets from combat.",
            "Wind",
        )


class Aspirate(_SorcererSchoolModifier):
    def __init__(self) -> None:
        super().__init__(
            "Aspirate",
            "Water spells can drown their targets, dealing damage over time "
            "and preventing them from acting.",
            "Water",
        )


class UnsteadyGround(_SorcererSchoolModifier):
    def __init__(self) -> None:
        super().__init__(
            "Unsteady Ground",
            "Earth spells also knock their targets prone.",
            "Earth",
        )


class Slow(Spell):
    """Lower a target's speed for several turns."""

    def __init__(self) -> None:
        super().__init__("Slow", "Lower the target's speed.", school="Arcane")
        self.cost = 14
        self.subtyp = "Status"

    def cast(self, user: Any, target: Any | None = None, **kwargs: Any) -> str:
        del kwargs
        if target is None:
            return "There is no target to slow.\n"
        user.mana.current -= self.cost
        effect = target.stat_effects["Speed"]
        effect.active = True
        effect.duration = max(int(effect.duration or 0), 3)
        effect.extra = min(int(effect.extra or 0), -3)
        effect.source = "Slow"
        return f"{target.name}'s speed is lowered.\n"


class Refueling(Spell):
    """Begin or cancel a mana-restoring channel."""

    def __init__(self) -> None:
        super().__init__(
            "Refueling",
            "Channel spirit force, regaining 10% of maximum mana on the first turn "
            "and twice the previous amount on every consecutive turn. At the start "
            "of each turn, continue Refueling or choose another action to cancel; "
            "while channeling, the caster is treated as prone for save rolls.",
            school="Arcane",
        )
        self.cost = 0
        self.subtyp = "Support"

    def cast(self, user: Any, target: Any | None = None, **kwargs: Any) -> str:
        del target, kwargs
        active = bool(getattr(user, "mage_refueling", False))
        if active:
            return f"{user.name} continues channeling spirit force.\n"
        user.mage_refueling = True
        user.mage_refueling_streak = 0
        return f"{user.name} begins channeling spirit force.\n"


class ManaRupture(Spell):
    """Damage a target in proportion to the mana it has left."""

    def __init__(self) -> None:
        super().__init__(
            "Mana Rupture",
            "Deal damage based on the target's remaining mana.",
            school="Arcane",
        )
        self.cost = 20
        self.subtyp = "Arcane"

    def cast(
        self,
        user: Any,
        target: Any | None = None,
        *,
        battle_engine: Any | None = None,
        **kwargs: Any,
    ) -> CombatResult:
        result = self._reset_result(actor=user, target=target)
        if target is None:
            result.message = "There is no target for Mana Rupture.\n"
            return result
        if not kwargs.get("_skip_cost", False):
            user.mana.current -= self.cost
        remaining_mana = max(0, int(getattr(target.mana, "current", 0) or 0))
        spell_power = max(1, int(user.check_mod("magic", enemy=target)))
        raw_damage = max(1, int(remaining_mana * 0.50) + spell_power // 2)
        hit, message, damage = target.damage_reduction(
            raw_damage,
            user,
            typ="Arcane",
        )
        if not hit:
            result.message = message + f"Mana Rupture misses {target.name}.\n"
            return result
        try:
            from ..classes import mage_mechanics

            damage = int(damage * mage_mechanics.spell_potency_multiplier(user, self))
        except Exception:
            pass
        damage = max(0, damage)
        target.health.current -= damage
        user._emit_damage_event(
            target,
            damage,
            damage_type="Arcane",
            ability_name=self.name,
            attack_source="spell",
            source="spell",
        )
        result.hit = damage > 0
        result.damage = damage
        result.extra["target_mana_before"] = remaining_mana
        result.message = (
            message + f"{user.name} ruptures {target.name}'s mana for {damage} damage.\n"
        )
        try:
            from ..classes import mage_mechanics

            result.message += mage_mechanics.resolve_mana_rupture(
                user,
                target,
                battle_engine=battle_engine,
            )
        except Exception:
            pass
        return result


class PrismaticCataclysm(Spell):
    """Wizard elemental capstone that strikes once with every school."""

    ELEMENTS = ("Fire", "Ice", "Electric", "Wind", "Water", "Earth")

    def __init__(self) -> None:
        super().__init__(
            "Prismatic Cataclysm",
            "Unleash all six elemental schools across every enemy.",
            school="Elemental",
        )
        self.cost = 180
        self.subtyp = "Elemental"
        self.target_scope = TargetScope.ALL_ENEMIES

    def cast(
        self,
        caster: Any,
        target: Any | None = None,
        **kwargs: Any,
    ) -> CombatResult:
        result = self._reset_result(actor=caster, target=target)
        if target is None:
            result.message = "There is no target for Prismatic Cataclysm.\n"
            return result
        if not kwargs.get("_skip_cost", False):
            caster.mana.current -= self.cost
        message = ""
        try:
            from ..classes import wizard

            message += wizard.observe_elemental_ultimate(target, caster)
        except Exception:
            pass
        total_damage = 0
        instances: list[int] = []
        converging = False
        try:
            from ..classes import mage_mechanics

            converging = mage_mechanics.has_skill(caster, "Elemental Convergence")
        except Exception:
            pass
        for index, element in enumerate(self.ELEMENTS):
            portion, damage = _simple_spell_damage(
                caster,
                target,
                dmg_mod=1.15 * (1 + (0.10 * index if converging else 0)),
                typ=element,
            )
            message += portion
            instances.append(damage)
            total_damage += damage
            if not target.is_alive():
                break
        result.hit = total_damage > 0
        result.damage = total_damage
        result.extra["damage_instances"] = instances
        result.message = message
        return result

    def cast_group(
        self,
        caster: Any,
        targets: list[tuple[str, Any]],
        *,
        battle_engine: Any,
    ) -> CombatResultGroup:
        group = CombatResultGroup(
            action=self.name,
            actor_id=battle_engine.current_actor_id,
            target_scope=TargetScope.ALL_ENEMIES,
            target_ids=tuple(target_id for target_id, _target in targets),
        )
        for index, (target_id, target) in enumerate(targets):
            result = deepcopy(self.cast(caster, target, _skip_cost=index > 0))
            result.actor_id = battle_engine.current_actor_id
            result.target_id = target_id
            result.target_scope = TargetScope.ALL_ENEMIES
            group.add(result)
        return group


class GravitationalPull(Spell):
    """Crush a target beneath an intensified gravitational well."""

    def __init__(self) -> None:
        super().__init__(
            "Gravitational Pull",
            "Increase the gravitational well under a target, dealing "
            "non-elemental force damage. Grounded creatures are slowed for "
            "two turns; flying creatures are pinned down and cannot act.",
            school="Arcane",
        )
        self.cost = 28
        self.subtyp = "Non-elemental"

    def cast(self, user: Any, target: Any | None = None, **kwargs: Any) -> CombatResult:
        result = self._reset_result(actor=user, target=target)
        if target is None:
            result.message = "There is no target for Gravitational Pull.\n"
            return result
        if not kwargs.get("_skip_cost", False):
            user.mana.current -= self.cost
        message, damage = _simple_spell_damage(
            user,
            target,
            dmg_mod=1.65,
            typ="Non-elemental",
        )
        if damage > 0 and getattr(target, "flying", False):
            target.flying = False
            target.apply_stun(2, source=self.name, applier=user)
            message += f"{target.name} is pinned to the ground.\n"
        elif damage > 0:
            speed = target.stat_effects["Speed"]
            speed.active = True
            speed.duration = max(int(speed.duration or 0), 2)
            speed.extra = min(int(speed.extra or 0), -3)
            speed.source = self.name
            message += f"{target.name} is slowed for two turns.\n"
        result.hit = damage > 0
        result.damage = damage
        result.message = message
        return result


class IllusoryLink(_MagePassive):
    def __init__(self) -> None:
        super().__init__(
            "Illusory Link",
            "While Mirror Image is active, the caster and a duplicate split "
            "incoming damage, reducing it by half.",
        )
        self.presentation_modifier = True
        self.modifies = ("Mirror Image", "Mirror Image II")


class _WizardSchoolModifier(_SchoolEnhancement):
    """Wizard passive that adds a discoverable rider to one elemental school."""


class Inferno(_WizardSchoolModifier):
    def __init__(self) -> None:
        super().__init__(
            "Inferno",
            "Flames feed more flames, allowing burns to spread through the "
            "battlefield and among enemies.",
            "Fire",
        )


class Subzero(_WizardSchoolModifier):
    def __init__(self) -> None:
        super().__init__(
            "Subzero",
            "Ice spells gain a chance to freeze an enemy, preventing it from "
            "acting for two turns.",
            "Ice",
        )


class ElectricalBurns(_WizardSchoolModifier):
    def __init__(self) -> None:
        super().__init__(
            "Electrical Burns",
            "Critical Electric spells can set their target on fire.",
            "Electric",
        )


class DivineWind(_WizardSchoolModifier):
    def __init__(self) -> None:
        super().__init__(
            "Divine Wind",
            "Call upon Fujin to lift grounded enemies or crash flying enemies "
            "to the ground, leaving them prone.",
            "Wind",
        )


class UnrelentingWaves(_WizardSchoolModifier):
    def __init__(self) -> None:
        super().__init__(
            "Unrelenting Waves",
            "Water spells gain a chance to recur on successive turns.",
            "Water",
        )


class Aftershock(_WizardSchoolModifier):
    def __init__(self) -> None:
        super().__init__(
            "Aftershock",
            "Earth spells reverberate through the ground, repeatedly damaging "
            "one or more enemies.",
            "Earth",
        )


class Fragmentation(_MagePassive):
    def __init__(self) -> None:
        super().__init__(
            "Fragmentation",
            "Each Magic Missile projectile has a chance to fragment on impact, "
            "leaving Arcane crystal shards on the battlefield.",
        )
        self.presentation_modifier = True
        self.modifies = ("Magic Missile III",)


class DetonationCascade(_MagePassive):
    def __init__(self) -> None:
        super().__init__(
            "Detonation Cascade",
            "Kinetic Explosion detonates scattered Arcane crystal shards into "
            "smaller explosions.",
        )
        self.presentation_modifier = True
        self.modifies = ("Kinetic Explosion",)


class ManaLeak(_MagePassive):
    def __init__(self) -> None:
        super().__init__(
            "Mana Leak",
            "Mana Rupture consumes Arcane Empowerment to deplete the target's " "mana pool.",
        )
        self.presentation_modifier = True
        self.modifies = ("Mana Rupture",)


class ManaSplinters(_MagePassive):
    def __init__(self) -> None:
        super().__init__(
            "Mana Splinters",
            "Mana Rupture shatters every Arcane crystal shard, damaging all "
            "enemies while the returning force restores the caster's mana.",
        )
        self.presentation_modifier = True
        self.modifies = ("Mana Rupture",)


class ElementalConvergence(_MagePassive):
    def __init__(self) -> None:
        super().__init__(
            "Elemental Convergence",
            "Each successive elemental strike in Prismatic Cataclysm deals " "10% more damage.",
        )
        self.presentation_modifier = True
        self.modifies = ("Prismatic Cataclysm",)


class Spaghettification(_MagePassive):
    def __init__(self) -> None:
        super().__init__(
            "Spaghettification",
            "Photon Sphere gains a chance to pull a target apart, instantly "
            "erasing it from existence.",
        )
        self.presentation_modifier = True
        self.modifies = ("Photon Sphere",)


class Multiplicity(_MagePassive):
    def __init__(self) -> None:
        super().__init__(
            "Multiplicity",
            "If combat ends while Mirror Image is active, restore 5% of "
            "maximum health for every duplicate still active.",
        )
        self.presentation_modifier = True
        self.modifies = ("Mirror Image", "Mirror Image II")


class Polymorph(Spell):
    """Temporarily transform a target, with bosses strongly resisting it."""

    BOSS_SUCCESS_CHANCE = 0.10

    def __init__(self) -> None:
        super().__init__(
            "Polymorph",
            "Transform an enemy into a harmless bunny that cannot act for 2 "
            "turns. Bosses resist the transformation 90% of the time.",
            school="Arcane",
        )
        self.cost = 12
        self.subtyp = "Arcane"

    def cast(self, user: Any, target: Any | None = None, **kwargs: Any) -> str:
        del kwargs
        if target is None:
            return "There is no target to polymorph.\n"
        user.mana.current -= self.cost
        from ..enemies.catalog import is_boss_enemy

        if is_boss_enemy(target) and random.random() >= self.BOSS_SUCCESS_CHANCE:
            return f"{target.name} resists the polymorph.\n"
        duration = 2
        try:
            from ..classes import mage_mechanics

            duration = max(1, int(duration * mage_mechanics.spell_potency_multiplier(user, self)))
        except Exception:
            pass
        effect = target.status_effects["Polymorph"]
        effect.active = True
        effect.duration = max(effect.duration, duration)
        effect.source = "Polymorph"
        return f"{target.name} is transformed into a harmless bunny for {duration} turns.\n"


class InflateHealth(Spell):
    def __init__(self) -> None:
        super().__init__(
            "Inflate Health",
            "Grant temporary HP that is consumed before real HP for 3 turns.",
            school="Shadow",
        )
        self.cost = 12
        self.subtyp = "Shadow"

    def cast(self, user: Any, target: Any | None = None, **kwargs: Any) -> str:
        del target, kwargs
        user.mana.current -= self.cost
        amount = max(5, int(user.health.max * 0.25) + int(user.stats.intel))
        user.temporary_health = {"amount": amount, "turns": 3}
        return f"{user.name} gains {amount} temporary HP for 3 turns.\n"


class EnlivenDead(Spell):
    def __init__(self) -> None:
        super().__init__(
            "Enliven Dead",
            "Outside combat, raise an undead version of the last defeated "
            "non-boss enemy after a Charisma/Luck check.",
            school="Shadow",
        )
        self.cost = 18
        self.combat = False
        self.subtyp = "Shadow"

    def cast_out(self, user: Any) -> str:
        snapshot = getattr(user, "last_defeated_enemy", None)
        if not isinstance(snapshot, dict):
            return "No defeated non-boss enemy can answer the rite.\n"
        user.mana.current -= self.cost
        luck = int(user.check_mod("luck", luck_factor=10))
        if random.randint(1, 20) + int(user.stats.charisma) + luck < 18:
            return "The corpse rejects the enlivening rite.\n"
        from ..classes import mage_mechanics

        mage_mechanics.set_transient_companion(
            user,
            name=f"Undead {snapshot['name']}",
            kind="undead",
            source="Enliven Dead",
            damage=max(2, int(snapshot.get("level", 1)) + user.stats.intel // 2),
        )
        return (
            f"Undead {snapshot['name']} will fight beside {user.name} for "
            f"{mage_mechanics.TRANSIENT_SUMMON_STEPS} steps.\n"
        )

    cast = cast_out


class ConjureBlade(Spell):
    def __init__(self) -> None:
        super().__init__(
            "Conjure Blade",
            "Call a level-scaled blade from another dimension; its damage uses "
            "the caster's Intelligence instead of Strength.",
            school="Arcane",
        )
        self.cost = 5
        self.subtyp = "Arcane"

    def cast(self, user: Any, target: Any | None = None, **kwargs: Any) -> str:
        del kwargs
        if target is None:
            return "There is no target for the conjured blade.\n"
        user.mana.current -= self.cost
        level = max(1, int(user.level.level))
        damage = max(1, random.randint(level, level * 2) + int(user.stats.intel))
        critical = False
        try:
            from ..classes import mage_mechanics, wizard

            critical = mage_mechanics.fire_inside_critical_bonus(user) > random.random()
            mage_mechanics.consume_fire_inside(user)
            critical_multiplier = 2.0 if critical else 1.0
            critical_multiplier = mage_mechanics.arcane_critical_multiplier(
                user,
                critical_multiplier,
            )
            damage = int(
                damage
                * critical_multiplier
                * mage_mechanics.spell_potency_multiplier(user, self)
                * (1 + wizard.affinity_damage_bonus(user, "Arcane"))
            )
        except Exception:
            pass
        _, reduction_message, damage = target.damage_reduction(
            damage,
            user,
            typ="Magic",
        )
        from ..classes import promotion_kits

        damage, shield_message, _fully_absorbed = promotion_kits.absorb_novel_shield(
            target,
            damage,
            source="spell",
        )
        target.health.current -= damage
        user._emit_damage_event(
            target,
            damage,
            damage_type="Arcane",
            source="spell",
            ability_name=self.name,
            is_critical=critical,
        )
        critical_text = " (Critical hit!)" if critical else ""
        return (
            reduction_message
            + shield_message
            + f"A conjured blade strikes {target.name} for {damage} damage"
            f"{critical_text}, then vanishes.\n"
        )


class ConjureAnimal(Spell):
    category = "Animal"

    def __init__(self) -> None:
        super().__init__(
            "Conjure Animal",
            "Outside combat, call a local animal that fights independently for " "a short time.",
            school="Arcane",
        )
        self.cost = 12
        self.combat = True
        self.self_target = True
        self.subtyp = "Calling"

    def cast_out(self, user: Any) -> str:
        from ..classes import mage_mechanics

        companion = mage_mechanics.conjure_standard_companion(
            user,
            "Animal",
            source="Conjure Animal",
        )
        if companion is None:
            return "No local animal answers the conjuration.\n"
        user.mana.current -= self.cost
        return (
            f"A {companion['name']} answers the call and will fight beside "
            f"{user.name} for "
            f"{mage_mechanics.TRANSIENT_SUMMON_STEPS} steps.\n"
        )

    def cast(
        self,
        user: Any,
        target: Any | None = None,
        *,
        battle_engine: Any | None = None,
        **kwargs: Any,
    ) -> str:
        del target, kwargs
        class_name = str(getattr(getattr(user, "cls", None), "name", ""))
        if class_name != "Thaumaturgist":
            return self.cast_out(user)
        from .. import companions

        xenid_name = companions.chosen_xenid(user, self.category)
        if not xenid_name:
            choices = " or ".join(companions.XENID_PAIRS[self.category])
            return f"Choose {choices} as the permanent animal Xenid first.\n"
        if battle_engine is None:
            return "Calling a Xenid requires an active battle.\n"
        xenid = user.summons[xenid_name]
        prior_cost = getattr(xenid, "summon_mana_cost", None)
        xenid.summon_mana_cost = 0
        try:
            message, success, _xenid = battle_engine._execute_summon(xenid_name)
        finally:
            xenid.summon_mana_cost = prior_cost
        if success:
            user.mana.current -= self.cost
        return message.replace("summons", "calls")


class ConjureShackles(Spell):
    def __init__(self) -> None:
        super().__init__(
            "Conjure Shackles",
            "Attempt to hold an enemy prone with dimensional shackles for up "
            "to 3 turns. It resists with Dexterity, then attempts to break free "
            "with Strength each turn.",
            school="Arcane",
        )
        self.cost = 15
        self.subtyp = "Arcane"

    def cast(self, user: Any, target: Any | None = None, **kwargs: Any) -> str:
        del kwargs
        if target is None:
            return "There is no target to shackle.\n"
        user.mana.current -= self.cost
        attack = random.randint(user.stats.intel // 2, max(user.stats.intel, 1))
        defense = random.randint(target.stats.dex // 2, max(target.stats.dex, 1))
        if defense >= attack:
            return f"{target.name} evades the conjured shackles.\n"
        target.conjured_shackles = {
            "turns": 3,
            "difficulty": max(1, int(user.stats.intel)),
        }
        target.physical_effects["Prone"].active = True
        target.physical_effects["Prone"].duration = 3
        target.physical_effects["Prone"].source = "Conjure Shackles"
        return f"Dimensional shackles hold {target.name} prone.\n"


class ConjurePotion(Spell):
    def __init__(self) -> None:
        super().__init__(
            "Conjure Potion",
            "Conjure a location-scaled Health or Mana potion. It cannot be "
            "used in town and enters a 50-step cooldown.",
            school="Arcane",
        )
        self.cost = 20
        self.combat = True
        self.subtyp = "Arcane"

    def is_available(self, user: Any, target: Any | None = None) -> bool:
        del target
        in_town = getattr(user, "in_town", False)
        in_town = in_town() if callable(in_town) else bool(in_town)
        return not in_town and int(getattr(user, "conjure_potion_cooldown", 0) or 0) <= 0

    def cast_out(self, user: Any) -> str:
        in_town = getattr(user, "in_town", False)
        in_town = in_town() if callable(in_town) else bool(in_town)
        if in_town:
            return "Conjure Potion cannot be used in town.\n"
        cooldown = int(getattr(user, "conjure_potion_cooldown", 0) or 0)
        if cooldown > 0:
            return f"Conjure Potion will recover in {cooldown} steps.\n"
        from .. import items

        depth = max(0, int(getattr(user, "location_z", 0) or 0))
        tiers = (
            (items.HealthPotion, items.ManaPotion),
            (items.GreatHealthPotion, items.GreatManaPotion),
            (items.SuperHealthPotion, items.SuperManaPotion),
            (items.MasterHealthPotion, items.MasterManaPotion),
        )
        tier = tiers[min(len(tiers) - 1, depth // 10)]
        potion = random.choice(tier)()
        user.mana.current -= self.cost
        user.modify_inventory(potion)
        user.conjure_potion_cooldown = 50
        return f"{user.name} conjures {potion.name}; the spell needs 50 steps to recover.\n"

    def cast(self, user: Any, target: Any | None = None, **kwargs: Any) -> str:
        del target, kwargs
        return self.cast_out(user)


class FloatingCrystal(Spell):
    """Create a mana-fed construct that eventually bursts at an enemy."""

    def __init__(self) -> None:
        super().__init__(
            "Floating Crystal",
            "Conjure a crystal that siphons 10% of maximum MP after each "
            "caster turn. At 30% it explodes, scaling the stored mana by the "
            "caster's spell power.",
            school="Conjuration",
        )
        self.cost = 0
        self.subtyp = "Construct"
        self.self_target = True

    def cast(self, user: Any, target: Any | None = None, **kwargs: Any) -> str:
        del target, kwargs
        if getattr(user, "floating_crystal", None):
            return "A floating crystal is already gathering mana.\n"
        maximum_mana = max(1, int(getattr(user.mana, "max", 1) or 1))
        user.floating_crystal = {
            "mana": 0,
            "siphon_percent": 0.10,
            "threshold": max(1, math.ceil(maximum_mana * 0.30)),
            "threshold_percent": 0.30,
        }
        return f"A giant crystal begins orbiting {user.name}.\n"


class ExplosiveDecoy(Spell):
    """Detonate one active Mirror Image into an Arcane attack."""

    def __init__(self) -> None:
        super().__init__(
            "Explosive Decoy",
            "Sacrifice one remaining Mirror Image, causing it to explode and "
            "deal Arcane damage to the target.",
            school="Arcane",
        )
        self.cost = 18
        self.subtyp = "Illusion"

    def cast(self, user: Any, target: Any | None = None, **kwargs: Any) -> str:
        del kwargs
        if target is None:
            return "There is no target for Explosive Decoy.\n"
        effect = user.magic_effects.get("Duplicates")
        image_count = int(getattr(effect, "duration", 0) or 0)
        if effect is None or not effect.active or image_count <= 0:
            return "Explosive Decoy requires a remaining Mirror Image.\n"
        user.mana.current -= self.cost
        effect.duration = image_count - 1
        if effect.duration <= 0:
            effect.active = False
            effect.duration = 0
        damage = max(1, int(user.check_mod("magic", enemy=target) * 1.25))
        from ..classes import promotion_kits

        damage, shield_message, _fully_absorbed = promotion_kits.absorb_novel_shield(
            target,
            damage,
            source="spell",
        )
        target.health.current -= damage
        user._emit_damage_event(
            target,
            damage,
            damage_type="Arcane",
            source="spell",
            ability_name=self.name,
        )
        return (
            shield_message + f"One of {user.name}'s mirror images rushes {target.name} and "
            f"explodes for {damage} Arcane damage.\n"
        )


class _MiracleSpell(Spell):
    """Reality-breaking conjuration that consumes a Reality Fragment."""

    reagent_name = "Reality Fragment"

    def _consume_reagent(self, user: Any) -> str | None:
        stack = getattr(user, "inventory", {}).get(self.reagent_name, [])
        if not stack:
            return f"{user.name} needs a {self.reagent_name} to cast {self.name}.\n"
        user.modify_inventory(stack[0], subtract=True)
        return None

    def is_available(self, user: Any, target: Any | None = None) -> bool:
        del target
        return bool(getattr(user, "inventory", {}).get(self.reagent_name, []))


class MiracleBlade(_MiracleSpell):
    """Cut through defenses and causality with an impossible blade."""

    def __init__(self) -> None:
        super().__init__(
            "Miracle Blade",
            "Consume a Reality Fragment to make an unavoidable blade that "
            "ignores defense, evasion, shields, and resistance.",
            school="Conjuration",
        )
        self.cost = 45
        self.subtyp = "Miracle"

    def cast(self, user: Any, target: Any | None = None, **kwargs: Any) -> str:
        del kwargs
        if target is None:
            return "There is no target for Miracle Blade.\n"
        failed = self._consume_reagent(user)
        if failed:
            return failed
        user.mana.current -= self.cost
        spell_power = int(user.check_mod("magic", enemy=target))
        damage = max(
            1,
            spell_power * 2,
            int(max(1, target.health.max) * 0.25),
        )
        from ..classes import promotion_kits

        damage, shield_message, _fully_absorbed = promotion_kits.absorb_novel_shield(
            target,
            damage,
            source="spell",
        )
        target.health.current = max(0, target.health.current - damage)
        user._emit_damage_event(
            target,
            damage,
            damage_type="Reality",
            source="spell",
            ability_name=self.name,
        )
        return (
            shield_message + f"An impossible blade cuts through every protection around "
            f"{target.name} for {damage} reality damage.\n"
        )


class MiracleShackles(_MiracleSpell):
    """Bind one target to a fixed point in reality without a saving throw."""

    def __init__(self) -> None:
        super().__init__(
            "Miracle Shackles",
            "Consume a Reality Fragment to hold a target prone for 3 turns "
            "without an evasion check, immunity check, or escape roll.",
            school="Conjuration",
        )
        self.cost = 55
        self.subtyp = "Miracle"

    def cast(self, user: Any, target: Any | None = None, **kwargs: Any) -> str:
        del kwargs
        if target is None:
            return "There is no target for Miracle Shackles.\n"
        failed = self._consume_reagent(user)
        if failed:
            return failed
        user.mana.current -= self.cost
        target.conjured_shackles = {
            "turns": 3,
            "difficulty": 0,
            "unbreakable": True,
        }
        prone = target.physical_effects["Prone"]
        prone.active = True
        prone.duration = 3
        prone.source = self.name
        return (
            f"Miraculous shackles fix {target.name} in place for 3 turns; "
            "nothing can break them early.\n"
        )


class MiraclePotion(_MiracleSpell):
    """Create both maximum-tier restorative potion types without cooldown."""

    def __init__(self) -> None:
        super().__init__(
            "Miracle Potion",
            "Consume a Reality Fragment to create both a Master Health Potion "
            "and Master Mana Potion, even in town and without a cooldown.",
            school="Conjuration",
        )
        self.cost = 60
        self.combat = True
        self.subtyp = "Miracle"

    def cast_out(self, user: Any) -> str:
        failed = self._consume_reagent(user)
        if failed:
            return failed
        from .. import items

        user.mana.current -= self.cost
        health_potion = items.MasterHealthPotion()
        mana_potion = items.MasterManaPotion()
        user.modify_inventory(health_potion)
        user.modify_inventory(mana_potion)
        return (
            f"{user.name} contradicts conservation itself and conjures "
            f"{health_potion.name} and {mana_potion.name}.\n"
        )

    def cast(self, user: Any, target: Any | None = None, **kwargs: Any) -> str:
        del target, kwargs
        return self.cast_out(user)


class MiracleCrystal(_MiracleSpell):
    """Create mana from nothing before bursting across every hostile target."""

    def __init__(self) -> None:
        super().__init__(
            "Miracle Crystal",
            "Consume a Reality Fragment to create a crystal that generates "
            "mana from nothing and bursts across every enemy after 4 turns.",
            school="Conjuration",
        )
        self.cost = 75
        self.subtyp = "Miracle"
        self.self_target = True

    def cast(self, user: Any, target: Any | None = None, **kwargs: Any) -> str:
        del target, kwargs
        if getattr(user, "floating_crystal", None):
            return "A floating crystal is already gathering mana.\n"
        failed = self._consume_reagent(user)
        if failed:
            return failed
        user.mana.current -= self.cost
        maximum_mana = max(1, int(getattr(user.mana, "max", 1) or 1))
        user.floating_crystal = {
            "mana": 0,
            "siphon_percent": 0.0,
            "threshold": maximum_mana,
            "threshold_percent": 1.0,
            "miracle": True,
            "generated_per_turn": max(1, math.ceil(maximum_mana * 0.25)),
        }
        return "A miraculous crystal begins creating mana where none existed.\n"


class Torchlight(Spell):
    """Suppress random encounters with a conjured exploration light."""

    def __init__(self) -> None:
        super().__init__(
            "Torchlight",
            "Conjure a bright light for 50 steps, halving the random encounter "
            "rate while it remains active.",
            school="Conjuration",
        )
        self.cost = 12
        self.combat = False
        self.subtyp = "Construct"

    def cast_out(self, user: Any) -> str:
        from ..classes import mage_mechanics

        user.mana.current -= self.cost
        mage_mechanics.activate_torchlight(user)
        return (
            f"A brilliant conjured light surrounds {user.name}, driving away "
            f"enemies for {mage_mechanics.TORCHLIGHT_STEPS} steps.\n"
        )

    cast = cast_out


class ConjureElixir(Spell):
    """Create a restorative elixir on a travel cooldown."""

    def __init__(self) -> None:
        super().__init__(
            "Conjure Elixir",
            "Conjure an Elixir. The spell then requires 100 travel steps to recover.",
            school="Conjuration",
        )
        self.cost = 28
        self.combat = False
        self.subtyp = "Construct"

    def is_available(self, user: Any, target: Any | None = None) -> bool:
        del target
        return int(getattr(user, "conjure_elixir_cooldown", 0) or 0) <= 0

    def cast_out(self, user: Any) -> str:
        cooldown = int(getattr(user, "conjure_elixir_cooldown", 0) or 0)
        if cooldown > 0:
            return f"Conjure Elixir will recover in {cooldown} steps.\n"
        from .. import items

        user.mana.current -= self.cost
        user.modify_inventory(items.Elixir())
        user.conjure_elixir_cooldown = 100
        return f"{user.name} conjures an Elixir.\n"

    cast = cast_out


class BarrierWall(Spell):
    """Create a destructible construct that intercepts enemy attacks."""

    def __init__(self) -> None:
        super().__init__(
            "Barrier Wall",
            "Conjure a wall that enemies must destroy before they can target " "the caster again.",
            school="Conjuration",
        )
        self.cost = 35
        self.subtyp = "Construct"
        self.self_target = True

    def cast(self, user: Any, target: Any | None = None, **kwargs: Any) -> str:
        del target, kwargs
        user.mana.current -= self.cost
        hit_points = max(
            30,
            int(getattr(getattr(user, "level", None), "level", 1)) + int(user.stats.intel) * 2,
        )
        user.barrier_wall_hp = hit_points
        return f"A barrier wall with {hit_points} HP rises before {user.name}.\n"


class Banish(Spell):
    """Eject a fiend or fey from the current battle."""

    def __init__(self) -> None:
        super().__init__(
            "Banish",
            "Send a fiend or fey away from this realm. Banished enemies grant no rewards.",
            school="Conjuration",
        )
        self.cost = 24
        self.subtyp = "Binding"

    def cast(self, user: Any, target: Any | None = None, **kwargs: Any) -> str:
        battle_engine = kwargs.get("battle_engine")
        if target is None:
            return "There is no target to banish.\n"
        creature_type = str(getattr(target, "enemy_typ", "")).lower()
        if creature_type not in {"fiend", "fey"}:
            return f"{target.name} is neither a fiend nor a fey.\n"
        user.mana.current -= self.cost
        target.health.current = 0
        target._banished_without_rewards = True
        if battle_engine is not None:
            from ..combat.encounter import EnemyResolution

            member = battle_engine._member_for_character(target)
            if member is not None and member.resolution is None:
                battle_engine.encounter.resolve_enemy(
                    member.combatant_id,
                    EnemyResolution.EJECTED,
                    cause="Banish",
                )
        return f"{target.name} is banished from this realm.\n"


class ManaBarbs(Spell):
    """Punish a target whenever it spends mana."""

    def __init__(self) -> None:
        super().__init__(
            "Mana Barbs",
            "For 3 turns, mana spent by the target deals the same amount of " "damage back to it.",
            school="Conjuration",
        )
        self.cost = 30
        self.subtyp = "Binding"

    def cast(self, user: Any, target: Any | None = None, **kwargs: Any) -> str:
        del kwargs
        if target is None:
            return "There is no target for Mana Barbs.\n"
        user.mana.current -= self.cost
        target.mana_barbs = {"turns": 3, "source": user}
        return f"Mana barbs coil around {target.name} for 3 turns.\n"


class _CallXenid(Spell):
    """Call ordinary transients until Thaumaturgist training unlocks Xenids."""

    category = ""

    def __init__(self, category: str, cost: int) -> None:
        self.category = category
        super().__init__(
            f"Conjure {category}",
            f"Conjure a nearby {category.lower()} creature as a transient ally. "
            "Thaumaturgists instead call their permanently chosen Xenid.",
            school="Conjuration",
        )
        self.cost = cost
        self.subtyp = "Calling"
        self.self_target = True

    def cast(
        self,
        user: Any,
        target: Any | None = None,
        *,
        battle_engine: Any | None = None,
        **kwargs: Any,
    ) -> str:
        del target, kwargs
        class_name = str(getattr(getattr(user, "cls", None), "name", ""))
        if class_name != "Thaumaturgist":
            from ..classes import mage_mechanics

            companion = mage_mechanics.conjure_standard_companion(
                user,
                self.category,
                source=self.name,
            )
            if companion is None:
                return f"No suitable {self.category.lower()} creature answers " "the conjuration.\n"
            user.mana.current -= self.cost
            return (
                f"{companion['name']} answers {self.name} and will fight "
                f"independently for {mage_mechanics.TRANSIENT_SUMMON_STEPS} "
                "steps.\n"
            )

        from .. import companions

        xenid_name = companions.chosen_xenid(user, self.category)
        if not xenid_name:
            choices = " or ".join(companions.XENID_PAIRS[self.category])
            return (
                f"Choose {choices} as the permanent {self.category.lower()} "
                "Xenid before casting this spell.\n"
            )
        if battle_engine is None:
            return "Calling a Xenid requires an active battle.\n"
        xenid = user.summons[xenid_name]
        prior_cost = getattr(xenid, "summon_mana_cost", None)
        xenid.summon_mana_cost = 0
        try:
            message, success, _xenid = battle_engine._execute_summon(xenid_name)
        finally:
            xenid.summon_mana_cost = prior_cost
        if success:
            user.mana.current -= self.cost
        return message.replace("summons", "calls")


class ConjureHumanoid(_CallXenid):
    def __init__(self) -> None:
        super().__init__("Humanoid", 12)


class ConjureMonster(_CallXenid):
    def __init__(self) -> None:
        super().__init__("Monster", 16)


class ConjureSpirit(_CallXenid):
    def __init__(self) -> None:
        super().__init__("Spirit", 20)


class ConjureFiend(_CallXenid):
    def __init__(self) -> None:
        super().__init__("Fiend", 24)


class ConjureCelestial(_CallXenid):
    def __init__(self) -> None:
        super().__init__("Celestial", 28)


class ConjureDragon(_CallXenid):
    def __init__(self) -> None:
        super().__init__("Dragon", 34)
