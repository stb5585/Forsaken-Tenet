"""Character combat-event emission behavior."""

from __future__ import annotations

from typing import TYPE_CHECKING

from src.core.randomness import gameplay_random as random

if TYPE_CHECKING:
    from .core import Character


class CharacterEventsMixin:
    def abilities_suppressed(self) -> bool:
        return bool(
            self.status_effects["Silence"].active or getattr(self, "anti_magic_active", False)
        )

    def _emit_damage_event(
        self,
        target: Character,
        damage: int,
        damage_type: str = "Physical",
        is_critical: bool = False,
        *,
        source: str = "Unknown",
        attack_source: str | None = None,
        weapon_name: str | None = None,
        weapon_slot: str | None = None,
        weapon_type: str | None = None,
        ability_name: str | None = None,
        item_name: str | None = None,
    ) -> None:
        """Helper to emit damage dealt events."""
        if target is not None and int(getattr(target, "_distracted_turns", 0) or 0) > 0:
            target._distracted_turns = 0
        if damage and damage > 0:
            shell_health = max(0, int(getattr(target, "war_turtle_shell_health", 0) or 0))
            if shell_health:
                target.health.current = min(target.health.max, target.health.current + damage)
                absorbed = min(shell_health, int(damage))
                target.war_turtle_shell_health = shell_health - absorbed
                if damage_type == "Physical":
                    reflected = max(1, int(damage * 0.25))
                    self.health.current = max(0, self.health.current - reflected)
                if target.war_turtle_shell_health <= 0:
                    target.turtle = False
                    target.war_turtle_shell_health = 0
            if damage_type == "Holy" and "Dazed or Confused" in getattr(self, "spellbook", {}).get(
                "Skills", {}
            ):
                from ..progression import has_talent

                stun_chance = 0.35 if has_talent(self, "priest.holy-disorientation") else 0.25
                confuse_chance = 0.40 if has_talent(self, "archbishop.overwhelming-light") else 0.25
                if random.random() < stun_chance:
                    target.apply_stun(2, source="Dazed or Confused", applier=self)
                elif random.random() < confuse_chance:
                    target.confused_turns = max(2, int(getattr(target, "confused_turns", 0) or 0))
                    berserk = target.status_effects.get("Berserk")
                    if berserk is not None:
                        berserk.active = True
                        berserk.duration = max(2, int(berserk.duration or 0))
                        berserk.source = "Dazed or Confused"
            if (
                getattr(target, "shadow_curtain_turns", 0) > 0
                and "Sciophobia" in getattr(target, "spellbook", {}).get("Skills", {})
                and random.random() < 0.25
            ):
                self.haunted_turns = max(3, int(getattr(self, "haunted_turns", 0) or 0))
            if getattr(self, "shadow_curtain_turns", 0) > 0 and damage_type == "Physical":
                target.health.current = max(0, target.health.current - max(1, int(damage * 0.25)))
            from .. import persistent_afflictions as afflictions

            fracture_chance = 0.30 if afflictions.curse_is_empowered(target, "Elijah") else 0.20
            if afflictions.has_curse(target, "Elijah") and random.random() < fracture_chance:
                afflictions.apply_fracture(target)
            if (
                afflictions.has_curse(target, "Demon Eyes")
                and str(getattr(self, "enemy_typ", "")) == "Fiend"
            ):
                multiplier = 0.40 if afflictions.curse_is_empowered(target, "Demon Eyes") else 0.25
                target.health.current = max(
                    0,
                    target.health.current - max(1, int(damage * multiplier)),
                )
            linked = getattr(target, "soul_bound_to", None)
            if linked is not None and linked is not target and linked.is_alive():
                mortal_shackles = "Mortal Shackles" in getattr(
                    linked,
                    "spellbook",
                    {},
                ).get("Skills", {})
                if mortal_shackles and getattr(target, "_soul_binding_caster", None) is linked:
                    target.health.current = max(0, target.health.current - int(damage * 0.25))
                    shared_damage = max(1, int(damage * 0.50))
                else:
                    shared_damage = int(damage)
                linked.health.current = max(0, linked.health.current - shared_damage)
            from ..classes import class_rings, promotion_kits

            reduced_damage = class_rings.reduce_major_hit(target, damage)
            if reduced_damage < damage:
                target.health.current = min(
                    target.health.max, target.health.current + (damage - reduced_damage)
                )
                damage = reduced_damage
            shielded_damage, shield_message = class_rings.absorb_aerial_supremacy_shield(
                target, damage
            )
            if shielded_damage < damage:
                target.health.current = min(
                    target.health.max,
                    target.health.current + (damage - shielded_damage),
                )
                damage = shielded_damage
            if shield_message:
                promotion_kits._message(target, shield_message)
            if hasattr(self, "record_damage_dealt"):
                self.record_damage_dealt(damage)
            if hasattr(target, "record_damage_taken"):
                target.record_damage_taken(damage)
            if hasattr(self, "record_archdruid_damage_dealt"):
                self.record_archdruid_damage_dealt(damage, damage_type)
            if hasattr(target, "record_archdruid_damage_taken"):
                target.record_archdruid_damage_taken(damage, damage_type)
            class_rings.record_damage_dealt(self, damage, damage_type)
            class_rings.trigger_umbral_debt(self)
            class_rings.divine_intervention(target)
            promotion_kits.record_damage_event(
                self,
                target,
                damage,
                damage_type,
                metadata={
                    "source": source,
                    "attack_source": attack_source,
                    "weapon_name": weapon_name,
                    "weapon_slot": weapon_slot,
                    "weapon_type": weapon_type,
                    "ability_name": ability_name,
                    "item_name": item_name,
                    "is_critical": is_critical,
                    "crit": is_critical,
                },
            )
            promotion_kits.record_damage_taken(target, damage, damage_type)
            from ..classes import pathfinder

            if attack_source == "spell" or source == "spell":
                pathfinder.record_elemental_spell_damage(self, damage_type)
            pathfinder.record_elemental_damage_taken(target, damage_type)
        from ..events.event_bus import EventType, create_combat_event, get_event_bus

        event_bus = get_event_bus()
        event_data = {
            "damage": damage,
            "damage_type": damage_type,
            "is_critical": is_critical,
            "crit": is_critical,
            "source": source,
        }
        optional_payload = {
            "attack_source": attack_source,
            "weapon_name": weapon_name,
            "weapon_slot": weapon_slot,
            "weapon_type": weapon_type,
            "ability_name": ability_name,
            "item_name": item_name,
        }
        event_data.update({key: value for key, value in optional_payload.items() if value})
        event_bus.emit(
            create_combat_event(
                EventType.DAMAGE_DEALT if damage > 0 else EventType.MISS,
                actor=self,
                target=target,
                **event_data,
            )
        )

    def _emit_healing_event(self, amount: int, source: str = "Unknown") -> None:
        """Helper to emit healing events."""
        if amount and amount > 0 and hasattr(self, "record_archdruid_healing_done"):
            self.record_archdruid_healing_done(amount)
        if amount and amount > 0:
            familiar = getattr(self, "familiar", None)
            skills = getattr(self, "spellbook", {}).get("Skills", {})
            if (
                familiar is not None
                and getattr(familiar, "spec", "") == "Support"
                and "Restorative Barrier" in skills
                and not str(source).lower().startswith("regen")
            ):
                self.restorative_barrier = int(getattr(self, "restorative_barrier", 0) or 0) + int(
                    amount
                )
            from ..classes import ability_mechanics, class_rings

            ability_mechanics.trigger_blessed_light(self, amount, source)
            echo = class_rings.shared_recovery_amount(self, amount)
            familiar = getattr(self, "familiar", None)
            if echo and familiar is not None and familiar.is_alive():
                familiar.health.current = min(familiar.health.max, familiar.health.current + echo)
            if getattr(self, "power_up", False) and "Eternal Conduit" in getattr(
                self, "spellbook", {}
            ).get("Skills", {}):
                echo = max(1, int(amount * 0.25))
                for summon in getattr(self, "summons", {}).values():
                    if summon.is_alive():
                        summon.health.current = min(summon.health.max, summon.health.current + echo)
                familiar = getattr(self, "familiar", None)
                if familiar is not None and familiar.is_alive():
                    familiar.health.current = min(
                        familiar.health.max, familiar.health.current + echo
                    )
        from ..events.event_bus import EventType, create_combat_event, get_event_bus

        event_bus = get_event_bus()
        event_bus.emit(
            create_combat_event(
                EventType.HEALING_DONE, actor=self, target=self, amount=amount, source=source
            )
        )

    def _emit_status_event(
        self,
        target: Character,
        status_name: str,
        applied: bool,
        duration: int = 0,
        source: str = "Unknown",
    ) -> None:
        """Helper to emit status effect events."""
        if applied:
            from ..classes import archdruid, pathfinder, promotion_kits

            if status_name == "Poison":
                promotion_kits._message(
                    self,
                    promotion_kits.add_aspect(self, "Venom"),
                )
            archdruid.record_status_applied(self, target, status_name)
            message = pathfinder.activate_superstitious_barrier(
                target,
                status_name,
                duration,
            )
            if message:
                promotion_kits._message(target, message)
        from ..events.event_bus import EventType, create_combat_event, get_event_bus

        event_bus = get_event_bus()
        event_bus.emit(
            create_combat_event(
                EventType.STATUS_APPLIED if applied else EventType.STATUS_REMOVED,
                actor=self,
                target=target,
                status_name=status_name,
                duration=duration,
                source=source,
            )
        )

    def _emit_status_tick_event(
        self,
        target: Character,
        status_name: str,
        amount: int,
        kind: str,
        source: str = "Unknown",
    ) -> None:
        """Emit a status tick (damage/heal) event for analytics/tests."""
        if kind == "damage" and amount and amount > 0 and hasattr(target, "record_damage_taken"):
            target.record_damage_taken(amount)
        if (
            kind == "damage"
            and amount
            and amount > 0
            and hasattr(target, "record_archdruid_damage_taken")
        ):
            damage_type = "Poison" if status_name == "Poison" else status_name
            target.record_archdruid_damage_taken(amount, damage_type)
        if (
            kind == "healing"
            and amount
            and amount > 0
            and hasattr(self, "record_archdruid_healing_done")
        ):
            self.record_archdruid_healing_done(amount)
        from ..events.event_bus import EventType, create_combat_event, get_event_bus

        event_bus = get_event_bus()
        event_bus.emit(
            create_combat_event(
                EventType.STATUS_TICK,
                actor=self,
                target=target,
                status_name=status_name,
                amount=amount,
                kind=kind,
                source=source,
            )
        )
