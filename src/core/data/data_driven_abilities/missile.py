"""Data-driven Magic Missile implementation."""

from __future__ import annotations

from copy import deepcopy
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from typing import Any

    from src.core.character import Character
    from src.core.effects.base import Effect

from src.core.abilities import Spell
from src.core.combat.combat_result import CombatResult, CombatResultGroup
from src.core.combat.targeting import TargetScope
from src.core.constants import ARMOR_SCALING_FACTOR, DAMAGE_VARIANCE_HIGH, DAMAGE_VARIANCE_LOW
from src.core.randomness import gameplay_random as random


class DataDrivenMagicMissileSpell(Spell):
    """
    A spell that fires multiple missiles, each independently resolving
    dodge / hit / Duplicates / crit / Mana Shield / Crusader / armor /
    variance / CON save / damage.

    Cannot be reflected.  Parameterized by ``missiles`` count.

    Used by: MagicMissile, MagicMissile2, MagicMissile3.
    """

    def __init__(
        self,
        name: str,
        description: str,
        cost: int,
        dmg_mod: float = 1.0,
        crit: int = 8,
        subtyp: str = "Non-elemental",
        missiles: int = 1,
        effects: list[Effect] | None = None,
        school: str | None = None,
        rank: int | None = None,
    ):
        super().__init__(name, description, school=school)
        self.cost = cost
        self.dmg_mod = dmg_mod
        self.crit = crit
        self.subtyp = subtyp
        self.missiles = missiles
        self._effects: list[Effect] = effects or []
        self.rank = rank

    def cast(
        self,
        caster: Character,
        target: Character | None = None,
        cover: bool = False,
        special: bool = False,
        fam: bool = False,
        **_kwargs: Any,
    ) -> str:
        result = self._reset_result(actor=caster, target=target)
        cast_message = ""
        damage_instances: list[int] = []
        highest_crit = 1

        # ── 1. Mana cost (free with Wizard Power Up) ────────────────
        effective_cost = self.cost
        try:
            from src.core.classes import mage_mechanics

            effective_cost = mage_mechanics.spell_mana_cost(caster, self)
        except Exception:
            pass
        result.extra["cost"] = effective_cost
        if self.name == "Photon Sphere":
            try:
                from src.core.classes import wizard

                cast_message += wizard.observe_photon_sphere(target, caster)
            except Exception:
                pass
        if not _kwargs.get("_skip_cost", False) and not (
            special
            or fam
            or (caster.cls.name == "Wizard" and caster.class_effects["Power Up"].active)
        ):
            caster.mana.current -= effective_cost

        # ── 2. Immunity check ───────────────────────────────────────
        if any([target.magic_effects["Ice Block"].active, target.tunnel]):
            result.message = "It has no effect.\n"
            return result.message

        spell_mod = caster.check_mod("magic", enemy=target)
        fire_inside_bonus = 0.0
        try:
            from src.core.classes import mage_mechanics

            fire_inside_bonus = mage_mechanics.fire_inside_critical_bonus(caster)
            mage_mechanics.consume_fire_inside(caster)
        except Exception:
            pass
        hits: list[bool] = []

        # ── 3. Per-missile loop ─────────────────────────────────────
        for i in range(self.missiles):
            hits.append(False)
            contact = caster.resolve_contact(
                target,
                typ="magic",
                always_hit=target.incapacitated(),
                rng=random,
            )
            hits[i] = contact.hit

            if not contact.hit:
                if contact.attribution is not None and contact.attribution.value == "dodge":
                    cast_message += f"{target.name} dodged the {self.name} and was unhurt.\n"
                else:
                    cast_message += f"The spell misses {target.name}.\n"
            elif cover:
                cast_message += (
                    f"{target.familiar.name} steps in front of the attack, "
                    f"absorbing the damage directed at {target.name}.\n"
                )
            else:
                crit = 1
                if not random.randint(0, self.crit):
                    crit = 2
                if fire_inside_bonus and random.random() < fire_inside_bonus:
                    crit = 2
                fire_inside_bonus = 0.0

                # Duplicates (Mirror Image) interception
                if hits[i] and target.magic_effects["Duplicates"].active:
                    if target.consume_mirror_image(caster, rng=random):
                        hits[i] = False
                        cast_message += (
                            f"{self.name} hits a mirror image of "
                            f"{target.name} and it vanishes from existence.\n"
                        )

                if hits[i]:
                    crit_per = random.uniform(1, crit)
                    try:
                        from src.core.classes import mage_mechanics

                        crit_per = mage_mechanics.arcane_critical_multiplier(
                            caster,
                            crit_per,
                            self,
                        )
                    except Exception:
                        pass
                    damage = int(self.dmg_mod * spell_mod * crit_per)
                    try:
                        from src.core.classes import mage_mechanics, wizard

                        damage = int(damage * mage_mechanics.spell_potency_multiplier(caster, self))
                        damage = int(
                            damage * mage_mechanics.spell_damage_multiplier(caster, self, target)
                        )
                        school = mage_mechanics.school_from_ability(self)
                        damage = int(damage * (1 + wizard.affinity_damage_bonus(caster, school)))
                    except Exception:
                        pass

                    # Mana Shield
                    if target.magic_effects["Mana Shield"].active:
                        damage, message, absorbed = caster._apply_mana_shield(
                            target,
                            damage,
                            physical=False,
                        )
                        hits[i] = not absorbed
                        cast_message += message
                    elif (
                        target.cls.name == "Crusader"
                        and target.power_up
                        and target.class_effects["Power Up"].active
                    ):
                        damage, message, _absorbed = caster._apply_crusader_shield(target, damage)
                        cast_message += message

                    # Armor scaling
                    dam_red = target.check_mod("magic def", enemy=caster)
                    damage = int(damage * (1 - (dam_red / (dam_red + ARMOR_SCALING_FACTOR))))

                    # Variance
                    variance = random.uniform(DAMAGE_VARIANCE_LOW, DAMAGE_VARIANCE_HIGH)
                    damage = int(damage * variance)

                    if damage <= 0:
                        cast_message += f"{self.name} was ineffective and does no damage.\n"
                        damage = 0
                    elif random.randint(0, target.stats.con // 2) > random.randint(
                        caster.stats.intel // 2, caster.stats.intel
                    ):
                        damage //= 2
                        if damage > 0:
                            cast_message += (
                                f"{target.name} shrugs off the {self.name} "
                                f"and only receives half of the damage.\n"
                            )
                            damage_msg = (
                                f"{caster.name} damages {target.name} for {damage} hit points"
                            )
                            if crit > 1:
                                damage_msg += " (Critical hit!)"
                            cast_message += damage_msg + ".\n"
                        else:
                            cast_message += f"{self.name} was ineffective and does no damage.\n"
                    else:
                        damage_msg = f"{caster.name} damages {target.name} for {damage} hit points"
                        if crit > 1:
                            damage_msg += " (Critical hit!)"
                        cast_message += damage_msg + ".\n"

                    try:
                        from src.core.classes import promotion_kits

                        damage, shield_message, _fully_absorbed = (
                            promotion_kits.absorb_novel_shield(
                                target,
                                damage,
                                source="spell",
                            )
                        )
                        cast_message += shield_message
                    except Exception:
                        pass
                    target.health.current -= damage
                    if (
                        self.name == "Photon Sphere"
                        and target.is_alive()
                        and random.random() < 0.05
                    ):
                        try:
                            from src.core.classes import mage_mechanics

                            if mage_mechanics.has_skill(caster, "Spaghettification"):
                                target.health.current = 0
                                cast_message += (
                                    f"Spaghettification erases {target.name} from existence.\n"
                                )
                        except Exception:
                            pass
                    if damage > 0:
                        damage_instances.append(int(damage))
                        highest_crit = max(highest_crit, crit)
                    caster._emit_damage_event(
                        target,
                        damage,
                        damage_type=self.subtyp,
                        is_critical=(crit > 1),
                        ability_name=self.name,
                        attack_source="spell",
                        source="spell",
                    )
                    if not target.is_alive():
                        break
                else:
                    cast_message += f"The spell misses {target.name}.\n"

                # Wizard mana regen
                if (
                    caster.cls.name == "Wizard"
                    and caster.class_effects["Power Up"].active
                    and damage > 0
                ):
                    cast_message += f"{caster.name} regens {damage} mana.\n"
                    caster.mana.current += damage
                    if caster.mana.current > caster.mana.max:
                        caster.mana.current = caster.mana.max

        # ── 4. Counterspell check ───────────────────────────────────
        if any(hits):
            if "Counterspell" in target.spellbook.get("Spells", {}) and not random.randint(0, 4):
                from src.core.abilities import Counterspell

                cast_message += f"{target.name} uses Counterspell.\n"
                cast_message += Counterspell().use(target, target=caster)

        result.hit = any(hits)
        result.crit = highest_crit if highest_crit > 1 else None
        result.damage = sum(damage_instances)
        result.extra["damage_instances"] = damage_instances
        result.message = cast_message
        return cast_message

    def cast_group(
        self,
        caster: Character,
        targets: list[tuple[str, Character]],
        *,
        battle_engine: Any,
    ) -> CombatResultGroup:
        """Strike every hostile target multiple times while paying mana once."""
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
                    message=f"{member.display_label} is no longer a valid target.\n",
                )
            else:
                with battle_engine._target_resolution_context(
                    member,
                    TargetScope.ALL_ENEMIES,
                    group.target_ids,
                ):
                    self.cast(caster, target=target, _skip_cost=index > 0)
                    result = deepcopy(self.result)
                    result.actor_id = battle_engine.current_actor_id
                    result.target_id = target_id
                    result.target_scope = TargetScope.ALL_ENEMIES
            group.add(result)
        return group
