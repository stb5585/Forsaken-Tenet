"""Character absorption, shielding, and damage-reduction behavior."""

from __future__ import annotations

import random
from typing import TYPE_CHECKING

from .. import persistent_afflictions as afflictions
from ..constants import (
    ARMOR_SCALING_FACTOR,
    ASTRAL_SHIFT_REDUCTION,
    DAMAGE_VARIANCE_HIGH,
    DAMAGE_VARIANCE_LOW,
    MAGIC_DEF_SCALING_FACTOR,
)
from .models import BLEED_MELEE_DAMAGE_TAKEN_MULTIPLIER, _class_name

if TYPE_CHECKING:
    from .core import Character
    from .models import AbsorptionResult, DamageReductionResult, DefenseResolution


class CharacterDefenseMixin:
    def _apply_absorption(
        self,
        defender: Character,
        damage: int,
        raw_dmg: int,
        crit_per: float,
        att: str,
        cover: bool,
        crit: int,
    ) -> AbsorptionResult:
        """
        Apply cover, shield block, mana shield, class shields, and reflect.

        Returns:
            (remaining_damage, message, fully_absorbed)
        """
        msg = ""
        absorbed = False
        from ..classes import ability_mechanics, paladin, promotion_kits
        from ..events.event_bus import EventType, create_combat_event, get_event_bus

        if cover:
            msg += (
                f"{defender.familiar.name} steps in front of the attack, "
                f"taking the damage for {defender.name}.\n"
            )
            if getattr(
                defender.familiar, "spec", ""
            ) == "Defense" and "Thorn By My Side" in defender.spellbook.get("Skills", {}):
                reflected = max(1, int(raw_dmg))
                self.health.current = max(0, self.health.current - reflected)
                msg += f"The Homunculus redirects {reflected} damage to {self.name}.\n"
            return 0, msg, False  # damage zeroed but hit still counts

        # Shield block
        cross_block = ability_mechanics.cross_block_profile(defender)
        can_block = (
            (
                defender.equipment["OffHand"].subtyp == "Shield"
                or "Dodge" in defender.equipment["Ring"].mod
                or cross_block is not None
            )
            and not defender.magic_effects["Mana Shield"].active
            and not (
                _class_name(defender) == "Crusader"
                and defender.power_up
                and defender.class_effects["Power Up"].active
            )
            and not defender.incapacitated()
        )
        if can_block:
            blk_chance = (
                cross_block[0]
                if cross_block is not None
                else defender.check_mod("shield", enemy=self) / 100
            )
            blk_chance += paladin.protection_block_bonus(defender)
            if blk_chance > random.random():
                blk_per = (
                    cross_block[1]
                    if cross_block is not None
                    else (
                        blk_chance
                        + (
                            (
                                (
                                    defender.stats.strength
                                    * afflictions.strength_multiplier(defender)
                                )
                                - self.stats.strength
                            )
                            / damage
                        )
                        if damage
                        else 0
                    )
                )
                if "Shield Block" in defender.spellbook["Skills"]:
                    blk_per *= 1.25
                blk_per += paladin.protection_mitigation_bonus(defender)
                if int(
                    promotion_kits.combat_state(defender).get(
                        "stronghold_turns",
                        0,
                    )
                    or 0
                ):
                    blk_per += 0.30
                if blk_per > 0:
                    blk_per = min(1, blk_per)
                    incoming_damage = damage
                    damage = int(damage * (1 - blk_per))
                    blocked_damage = max(0, incoming_damage - damage)
                    event_bus = get_event_bus()
                    event_bus.emit(
                        create_combat_event(
                            EventType.BLOCK,
                            actor=defender,
                            target=self,
                            damage_blocked=blocked_damage,
                            **self._weapon_event_metadata(att),
                        )
                    )
                    blocked_pct = round(blk_per * 100)
                    if blocked_pct > 0:
                        msg += (
                            f"{defender.name} blocks {self.name}'s attack and mitigates "
                            f"{blocked_pct} percent of the damage.\n"
                        )
                        resolve_gain = max(
                            5,
                            min(15, blocked_damage // 5),
                        )
                        msg += promotion_kits.build_resolve(
                            defender,
                            resolve_gain,
                            "a successful block",
                        )
                        msg += promotion_kits.record_devotion_block(defender)
                        msg += promotion_kits.add_aspect(
                            defender,
                            "Stone",
                            incoming=True,
                        )
                    if (
                        cross_block is not None
                        and damage <= 0
                        and getattr(self, "can_be_disarmed", lambda: False)()
                    ):
                        disarm = self.physical_effects["Disarm"]
                        disarm.active = True
                        disarm.duration = max(2, int(disarm.duration or 0))
                        disarm.source = "Cross Block"
                        msg += (
                            f"{defender.name}'s Cross Block completely stops the "
                            f"attack and disarms {self.name}.\n"
                        )
                    msg += ability_mechanics.retaliate_after_block(defender, self)
                    if damage <= 0:
                        try:
                            from ..classes import promotion_kits

                            msg += promotion_kits.record_resolve_mastery(
                                defender,
                                "stronghold",
                                "a full shield block",
                            )
                            msg += promotion_kits.shield_riposte_after_full_block(
                                defender,
                                self,
                            )
                        except Exception:
                            pass
                    try:
                        from ..classes import paladin

                        msg += paladin.block_succeeded(defender)
                    except Exception:
                        pass
            return damage, msg, False

        # Barrier Wall
        wall_hp = max(0, int(getattr(defender, "barrier_wall_hp", 0) or 0))
        if wall_hp and damage > 0:
            absorbed = min(wall_hp, damage)
            defender.barrier_wall_hp = wall_hp - absorbed
            damage -= absorbed
            msg += f"{defender.name}'s barrier wall absorbs {absorbed} damage" + (
                " and shatters.\n"
                if defender.barrier_wall_hp <= 0
                else f" ({defender.barrier_wall_hp} HP remains).\n"
            )
            if damage <= 0:
                return 0, msg, True

        # Mana Shield
        if defender.magic_effects["Mana Shield"].active:
            damage, shield_msg, absorbed = self._apply_mana_shield(
                defender,
                damage,
                physical=True,
            )
            return damage, msg + shield_msg, absorbed

        # Crusader absorb shield
        if (
            _class_name(defender) == "Crusader"
            and defender.power_up
            and defender.class_effects["Power Up"].active
        ):
            damage, shield_msg, absorbed = self._apply_crusader_shield(defender, damage)
            return damage, msg + shield_msg, absorbed

        # Templar reflect
        if (
            _class_name(defender) == "Templar"
            and defender.power_up
            and defender.class_effects["Power Up"].active
        ):
            ref_dam = int(0.25 * damage)
            damage -= ref_dam
            self.health.current -= ref_dam
            defender._emit_damage_event(self, ref_dam, damage_type="Reflected", is_critical=False)
            msg += f"{ref_dam} is reflected back at {self.name}.\n"
            return damage, msg, False

        # Totem reflect
        if (
            defender.magic_effects["Totem"].active
            and isinstance(defender.magic_effects["Totem"].extra, dict)
            and defender.magic_effects["Totem"].extra.get("secondary") == "reflect"
        ):
            ref_dam = int(0.25 * damage)
            damage -= ref_dam
            self.health.current -= ref_dam
            defender._emit_damage_event(self, ref_dam, damage_type="Reflected", is_critical=False)
            msg += f"{ref_dam} bounces off the totem's barrier back to {self.name}.\n"
            return damage, msg, False

        return damage, msg, False

    @staticmethod
    def _apply_temporary_health(
        defender: Character,
        damage: int,
    ) -> tuple[int, str]:
        """Consume temporary HP after mitigation and before real health."""
        temporary_health = getattr(defender, "temporary_health", None)
        if not isinstance(temporary_health, dict) or damage <= 0:
            return damage, ""
        if temporary_health.get("blocks_all_damage"):
            source = str(temporary_health.get("source") or "protective barrier")
            return 0, f"{defender.name}'s {source} blocks {damage} damage.\n"
        available = max(0, int(temporary_health.get("amount", 0) or 0))
        absorbed = min(available, damage)
        temporary_health["amount"] = available - absorbed
        source = str(temporary_health.get("source") or "inflated health")
        if temporary_health["amount"] <= 0:
            defender.temporary_health = None
        return (
            damage - absorbed,
            f"{defender.name}'s {source} absorbs {absorbed} damage.\n",
        )

    def _apply_mana_shield(
        self,
        defender: Character,
        damage: int,
        *,
        physical: bool = False,
    ) -> AbsorptionResult:
        """Redirect a capped share of physical damage into the defender's MP."""
        msg = ""
        if damage <= 0 or not physical:
            return damage, msg, False

        redirect_percent = max(
            0.0,
            min(
                1.0,
                float(defender.magic_effects["Mana Shield"].duration or 0) / 100.0,
            ),
        )
        try:
            from ..classes import mage_mechanics

            redirect_percent *= mage_mechanics.arcane_potency_multiplier(defender)
        except Exception:
            pass
        available_mana = max(0, int(defender.mana.current))
        if available_mana <= 0:
            self._emit_status_event(defender, "Mana Shield", applied=False, source="Mana Depleted")
            defender.magic_effects["Mana Shield"].active = False
            msg += f"The mana shield dissolves around {defender.name}.\n"
            return damage, msg, False

        redirected = min(
            available_mana,
            max(0, int(damage * redirect_percent)),
        )
        if redirected <= 0:
            return damage, msg, False
        defender.mana.current = max(0, available_mana - redirected)
        damage -= redirected
        msg += (
            f"The mana shield around {defender.name} redirects "
            f"{redirected} physical damage into MP.\n"
        )
        if defender.mana.current <= 0:
            self._emit_status_event(defender, "Mana Shield", applied=False, source="Mana Depleted")
            defender.magic_effects["Mana Shield"].active = False
            msg += f"The mana shield dissolves around {defender.name}.\n"
        return damage, msg, damage <= 0

    def _apply_crusader_shield(self, defender: Character, damage: int) -> AbsorptionResult:
        """Handle Crusader Power Up absorb shield. Returns (damage, msg, fully_absorbed)."""
        msg = ""
        if damage >= defender.class_effects["Power Up"].extra:
            msg += (
                f"The shield around {defender.name} absorbs "
                f"{defender.class_effects['Power Up'].extra} damage.\n"
            )
            damage -= defender.class_effects["Power Up"].extra
            defender.class_effects["Power Up"].active = False
            msg += f"The shield dissolves around {defender.name}.\n"
            return damage, msg, False
        else:
            msg += f"The shield around {defender.name} absorbs {damage} damage.\n"
            defender.class_effects["Power Up"].extra -= damage
            return 0, msg, True

    def _apply_damage_reduction(
        self, defender: Character, damage: int, att: str, ignore: bool
    ) -> DamageReductionResult:
        """Apply resistance, armor, defensive stance, and astral shift reductions."""
        from ..classes import ability_mechanics

        msg = ""

        # Elemental + physical resistance
        e_resist = 0
        if self.equipment[att].element:
            e_resist = defender.check_mod("resist", enemy=self, typ=self.equipment[att].element)
        p_resist = defender.check_mod(
            "resist", enemy=self, typ="Physical", ultimate=self.equipment[att].ultimate
        )
        dam_red = defender.check_mod("armor", enemy=self, ignore=ignore)
        damage = max(
            0,
            int(
                damage
                * (1 - p_resist)
                * (1 - e_resist)
                * (1 - (dam_red / (dam_red + ARMOR_SCALING_FACTOR)))
            ),
        )
        variance = random.uniform(DAMAGE_VARIANCE_LOW, DAMAGE_VARIANCE_HIGH)
        damage = int(damage * variance)
        try:
            from ..classes import paladin

            damage = int(damage * paladin.incoming_damage_multiplier(defender, "Physical"))
        except Exception:
            pass

        # Bleed makes melee hits more punishing (before defensive stance reductions).
        if (
            damage > 0
            and hasattr(defender, "physical_effects")
            and defender.physical_effects.get("Bleed")
            and defender.physical_effects["Bleed"].active
        ):
            bleed_multiplier = ability_mechanics.pain_tolerance_bleed_multiplier(
                defender,
            )
            bonus = max(
                1,
                int(damage * (BLEED_MELEE_DAMAGE_TAKEN_MULTIPLIER - 1.0) * bleed_multiplier),
            )
            damage += bonus
            msg += f"{defender.name}'s bleeding leaves them vulnerable (+{bonus} damage).\n"

        # Defensive stance
        defensive_reduction = (
            defender.get_defensive_reduction()
            if hasattr(defender, "get_defensive_reduction")
            else 0.0
        )
        if defensive_reduction > 0 and damage > 0:
            reduced = max(1, int(damage * defensive_reduction))
            damage = max(0, damage - reduced)
            msg += f"{defender.name} braces defensively, reducing damage by {reduced}.\n"

        if (
            defender.magic_effects.get("Stone Skin")
            and defender.magic_effects["Stone Skin"].active
            and damage > 0
        ):
            reduced = max(1, int(damage * 0.35))
            damage = max(0, damage - reduced)
            msg += f"{defender.name}'s stone skin absorbs {reduced} damage.\n"

        try:
            from ..classes import wizard

            damage, frozen_message = wizard.frozen_armor_reduction(defender, damage)
            msg += frozen_message
        except Exception:
            pass

        # Astral Shift (25%)
        if defender.magic_effects["Astral Shift"].active and damage > 0:
            astral_reduction = int(damage * ASTRAL_SHIFT_REDUCTION)
            damage = max(0, damage - astral_reduction)
            msg += f"{defender.name}'s astral form deflects {astral_reduction} damage.\n"

        # Footpad-line passive damage reduction (weapon hits only): stackable proc, DEX-scaling.
        # Stacks build when hit (max 3) and reset on dodge.
        # Applied late so it plays nicely with armor/resists/stance and stays readable.
        if damage > 0 and "Evasive Guard" in defender.spellbook.get("Skills", {}):
            dex = int(getattr(defender.stats, "dex", 10))
            stacks = int(getattr(defender, "evasive_guard_stacks", 0) or 0)
            if stacks > 0:
                # Per-stack reduction: 3% base + 0.2% per DEX above 10, capped at 8%.
                per_stack = min(0.08, max(0.03, 0.03 + max(0, dex - 10) * 0.002))
                guard_red = min(0.25, per_stack * min(3, stacks))
                reduced = max(1, int(damage * guard_red))
                damage = max(0, damage - reduced)
                msg += f"{defender.name}'s evasive guard reduces damage by {reduced}.\n"

        try:
            from ..classes import promotion_kits

            damage, devotion_message = promotion_kits.devotion_guard_reduction(defender, damage)
            msg += devotion_message
            damage, benediction_message = promotion_kits.benediction_damage_reduction(
                defender,
                damage,
            )
            msg += benediction_message
            damage, landing_message = promotion_kits.grounded_landing_reduction(
                defender,
                damage,
            )
            msg += landing_message
            damage, phalanx_message = promotion_kits.phalanx_reduction(
                defender,
                damage,
            )
            msg += phalanx_message
            damage, stronghold_message = promotion_kits.stronghold_melee_reduction(
                defender,
                damage,
                self,
            )
            msg += stronghold_message
        except Exception:
            pass
        try:
            from ..classes import paladin

            damage, shelter_message = paladin.oath_shelter_damage_reduction(
                defender,
                self,
                damage,
            )
            msg += shelter_message
            msg += paladin.resolve_oath_judgment_counter(defender, self)
        except Exception:
            pass

        barrier = int(getattr(defender, "restorative_barrier", 0) or 0)
        if barrier > 0 and damage > 0:
            absorbed = min(barrier, damage)
            defender.restorative_barrier = barrier - absorbed
            damage -= absorbed
            msg += f"{defender.name}'s restorative barrier absorbs {absorbed} damage.\n"
        try:
            from ..classes import healer

            damage, healer_message = healer.reduce_incoming_damage(
                defender,
                damage,
                melee=True,
            )
            msg += healer_message
        except Exception:
            pass
        try:
            from ..classes import pathfinder

            damage, barrier_message = pathfinder.absorb_superstitious_barrier(
                defender,
                damage,
            )
            msg += barrier_message
            damage, ranger_message = pathfinder.ranger_damage_reduction(
                defender,
                self,
                damage,
                physical=True,
            )
            msg += ranger_message
        except Exception:
            pass
        try:
            from ..classes import promotion_kits

            msg += promotion_kits.resolve_devotion_counter(
                defender,
                self,
                damage,
            )
        except Exception:
            pass
        return damage, msg

    def _build_damage_message(
        self, defender: Character, damage: int, typ: str, crit: int, att: str
    ) -> str:
        """Build the main damage-dealt message string."""
        msg = f"{self.name} {typ} {defender.name} for {damage} damage"
        if crit > 1:
            msg += " (Critical hit!)"
        msg += ".\n"
        return msg

    def _apply_on_hit_effects(
        self,
        defender: Character,
        damage: int,
        crit: int,
        att: str = "Weapon",
        *,
        damage_type_override: str | None = None,
    ) -> str:
        """Apply post-damage triggers: Maelstrom tracking, sleep wakeup, life steal."""
        msg = ""

        # Update Maelstrom Weapon counter for non-critical hits
        if "Maelstrom Weapon" in self.spellbook["Skills"] and crit == 1:
            if not hasattr(self, "maelstrom_hits"):
                self.maelstrom_hits = 0
            self.maelstrom_hits += 1

        # Emit damage event
        damage_type = damage_type_override or "Physical"
        if damage_type_override is None and self.equipment[att].element:
            damage_type = self.equipment[att].element
        self._emit_damage_event(
            defender,
            damage,
            damage_type=damage_type,
            is_critical=(crit > 1),
            **self._weapon_event_metadata(att),
        )
        try:
            from ..classes import promotion_kits

            msg += promotion_kits.pop_messages(self)
            msg += promotion_kits.pop_messages(defender)
        except Exception:
            pass

        # Sleep wakeup
        if defender.status_effects["Sleep"].active and not random.randint(
            0, defender.status_effects["Sleep"].duration
        ):
            msg += f"The attack awakens {defender.name}!\n"
            self._emit_status_event(defender, "Sleep", applied=False, source="Awakened by Damage")
            defender.status_effects["Sleep"].active = False
            defender.status_effects["Sleep"].duration = 0

        # Ninja life steal
        if _class_name(self) == "Ninja" and self.power_up:
            dam_abs = self.class_effects["Power Up"].active * damage
            dam_abs = int(dam_abs * self.healing_received_multiplier())
            dam_abs = min(dam_abs, self.health.max - self.health.current)
            self.health.current += dam_abs
            self._emit_healing_event(dam_abs, source="Ninja Life Steal")
            if hasattr(defender, "record_archdruid_life_drained"):
                defender.record_archdruid_life_drained()
            msg += f"{self.name} absorbs {dam_abs} from {defender.name}.\n"

        # Lycan life steal
        if _class_name(self) == "Lycan" and self.power_up:
            dam_abs = damage // 2
            dam_abs = int(dam_abs * self.healing_received_multiplier())
            dam_abs = min(dam_abs, self.health.max - self.health.current)
            self.health.current += dam_abs
            if dam_abs > 0:
                self._emit_healing_event(dam_abs, source="Lycan Life Steal")
                if hasattr(defender, "record_archdruid_life_drained"):
                    defender.record_archdruid_life_drained()
            msg += f"{self.name} absorbs {dam_abs} from {defender.name}.\n"

        return msg

    def _apply_equipment_effects(
        self, defender: Character, att: str, damage: int, crit: int
    ) -> str:
        """Process armor/weapon special effects on a successful hit."""
        from ..combat.combat_result import CombatResult, CombatResultGroup

        msg = ""
        result = CombatResult(
            action=att, actor=self, target=defender, hit=True, crit=crit, damage=damage, healing=0
        )
        results = CombatResultGroup()
        results.add(result)

        # Armor special effects (thorns, reflection)
        defender.equipment["Armor"].special_effect(results)

        # Weapon special effects (life steal, elemental effects, instant death)
        if defender.is_alive() and damage > 0 and not defender.magic_effects["Mana Shield"].active:
            self.equipment[att].special_effect(results)

        # Process special effect results
        for res in results.results:
            if res.message:
                msg += res.message
            if "Drain" in res.extra and res.extra["Drain"]:
                drain_amount = res.actor.health.current - (res.actor.health.current - res.damage)
                msg += f"{res.actor.name} drains {drain_amount} health from {res.target.name}.\n"
            if "Instant Death" in res.extra and res.extra["Instant Death"]:
                res.target.health.current = 0
                msg += f"{res.target.name} is instantly killed!\n"

        return msg

    def handle_defenses(
        self,
        attacker: Character,
        damage: int,
        cover: bool = False,
        typ: str = "Physical",
    ) -> DefenseResolution:
        """
        Resolve active pre-reduction defenses for spell/effect damage.

        This is the shared entry point used by legacy spells, YAML abilities,
        and composite effects before elemental or magic-defense reduction. It
        currently handles Mana Shield absorption and returns pass-through
        damage for callers without an active shield.

        Args:
            attacker: The attacking character
            damage: Base damage value
            cover: Whether attack can be blocked by familiar/pet
            typ: Damage type ("Physical", "Magic", etc.)

        Returns:
            tuple: (hit: bool, message: str, damage: int)
        """
        message = ""
        hit = True

        # Handle Mana Shield
        if self.magic_effects["Mana Shield"].active:
            damage, shield_message, fully_absorbed = attacker._apply_mana_shield(
                self,
                damage,
                physical=typ == "Physical",
            )
            message += shield_message
            hit = not fully_absorbed

        if hit and typ == "Magic":
            try:
                from src.core.classes import nature_totems

                damage, ward_message = nature_totems.water_ward_absorb(self, damage)
                message += ward_message
            except Exception:
                pass

        return (hit, message, damage)

    def damage_reduction(
        self, damage: int, attacker: Character, typ: str = "Physical"
    ) -> DefenseResolution:
        """
        Apply elemental resistance and magic-defense reduction to incoming damage.

        This is the shared post-defense reduction step for legacy spells, YAML
        abilities, and composite effects. Weapon attacks use
        ``_apply_damage_reduction()`` because they also need equipment and
        armor-specific context.

        Args:
            damage: Incoming damage value
            attacker: The attacking character
            typ: Damage type for resistance calculation

        Returns:
            tuple: (hit: bool, message: str, final_damage: int)
        """
        if typ != "Physical" and damage > 0:
            try:
                from ..classes import ability_mechanics

                if ability_mechanics.spend_nature_shield_orb(self):
                    healing = max(1, int(damage * 0.5))
                    self.health.current = min(self.health.max, self.health.current + healing)
                    return (
                        False,
                        f"A Nature Shield orb intercepts the spell and heals {self.name} for {healing}.\n",
                        0,
                    )
            except Exception:
                pass

        if typ == "Holy" and damage > 0:
            try:
                from ..classes import paladin

                damage = int(damage * paladin.holy_damage_multiplier(attacker))
            except Exception:
                pass

        # Apply basic resistance only if typ is a valid resistance type
        resist = 0
        if typ in self.resistance:
            resist = self.check_mod("resist", enemy=attacker, typ=typ)
        if typ == "Shadow" and getattr(attacker, "_piercing_bolt_cast", False):
            resist *= 0.5 if resist > 0 else 1.5
        try:
            from ..classes import mage_mechanics

            resist = min(
                0.95,
                resist + mage_mechanics.ice_resistance_bonus(self, typ),
            )
        except Exception:
            pass

        message = ""
        final_damage = int(damage * (1 - resist))
        darkness_active = (
            int(getattr(attacker, "shadow_dungeon_darkness_steps", 0) or 0) > 0
            or int(getattr(self, "shadow_dungeon_darkness_steps", 0) or 0) > 0
        )
        if typ == "Shadow" and darkness_active:
            final_damage = int(final_damage * 1.25)
        try:
            from ..classes import paladin

            final_damage = int(final_damage * paladin.incoming_damage_multiplier(self, typ))
        except Exception:
            pass
        try:
            from ..classes import bard

            final_damage = int(final_damage * (1 - bard.damage_reduction(self)))
        except Exception:
            pass

        # Magic defense reduction: allow primary stats (WIS/CHA) to matter for
        # survival even on physical builds, by reducing incoming elemental/magic damage.
        if typ != "Physical" and final_damage > 0:
            mdef = int(self.check_mod("magic def", enemy=attacker) or 0)
            if mdef > 0:
                final_damage = int(final_damage * (1 - (mdef / (mdef + MAGIC_DEF_SCALING_FACTOR))))
        try:
            from ..classes import wizard

            final_damage, frozen_message = wizard.frozen_armor_reduction(self, final_damage)
            message += frozen_message
        except Exception:
            pass
        try:
            from ..classes import mage_mechanics

            final_damage = int(final_damage * mage_mechanics.incoming_damage_multiplier(self))
        except Exception:
            pass

        if resist > 0 and final_damage < damage:
            reduction = damage - final_damage
            message += f"{self.name}'s resistance reduces damage by {reduction}.\n"

        try:
            from ..classes import promotion_kits

            final_damage, devotion_message = promotion_kits.devotion_guard_reduction(
                self, final_damage
            )
            message += devotion_message
            final_damage, benediction_message = promotion_kits.benediction_damage_reduction(
                self,
                final_damage,
            )
            message += benediction_message
            final_damage, landing_message = promotion_kits.grounded_landing_reduction(
                self,
                final_damage,
            )
            message += landing_message
        except Exception:
            pass
        try:
            from ..classes import paladin

            final_damage, shelter_message = paladin.oath_shelter_damage_reduction(
                self,
                attacker,
                final_damage,
            )
            message += shelter_message
        except Exception:
            pass

        final_damage, temporary_health_message = self._apply_temporary_health(
            self,
            final_damage,
        )
        message += temporary_health_message

        barrier = int(getattr(self, "restorative_barrier", 0) or 0)
        if barrier > 0 and final_damage > 0:
            absorbed = min(barrier, final_damage)
            self.restorative_barrier = barrier - absorbed
            final_damage -= absorbed
            message += f"{self.name}'s restorative barrier absorbs {absorbed} damage.\n"
        try:
            from ..classes import healer

            final_damage, healer_message = healer.reduce_incoming_damage(
                self,
                final_damage,
                melee=False,
            )
            message += healer_message
        except Exception:
            pass
        try:
            from ..classes import pathfinder

            final_damage, barrier_message = pathfinder.absorb_superstitious_barrier(
                self,
                final_damage,
            )
            message += barrier_message
            final_damage, ranger_message = pathfinder.ranger_damage_reduction(
                self,
                attacker,
                final_damage,
                physical=typ == "Physical",
            )
            message += ranger_message
        except Exception:
            pass
        return True, message, final_damage
