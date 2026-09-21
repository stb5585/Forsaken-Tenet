"""Weapon, flee, and defense actions for the battle engine."""

from __future__ import annotations

from typing import TYPE_CHECKING

from src.core.randomness import gameplay_random as random

from ...classes import (
    footpad,
    promotion_kits,
)
from ...constants import SPECIAL_ATTACK_LUCK_FACTOR, SPECIAL_ATTACK_ROLL_MAX
from ...events.event_bus import EventType, create_combat_event
from ..actor_cycle import initiative_rating
from ..combat_result import CombatResult
from ..encounter import EnemyResolution

if TYPE_CHECKING:
    pass


class AttackActionMixin:
    """Resolve attacks, fleeing, weapon recovery, and defense."""

    def player_has_sight(self) -> bool:
        """Check if the player can see enemy details (Seeker/Inquisitor/Vision)."""
        return any(
            [
                promotion_kits.class_name(self.player) in ["Inquisitor", "Seeker"],
                getattr(self.player.equipment.get("Pendant"), "mod", None) == "Vision",
                getattr(self.player, "sight", False),
            ]
        )

    def show_enemy_details(self, enemy=None) -> bool:
        """Return whether details for one enemy should be visible."""
        enemy = enemy or self._focused_enemy()
        return all(
            [
                self.player_has_sight(),
                not self.boss,
                enemy.name != "Waitress",
            ]
        )

    # ── Private action helpers ───────────────────────────────────────

    def _execute_attack(self) -> str:
        """Execute a basic/special attack."""
        self._event_bus.emit(
            create_combat_event(
                EventType.ATTACK,
                actor=self.attacker,
                target=self.defender,
                is_special=False,
                source="weapon_damage",
                attack_source="weapon",
                weapon_name=getattr(self.attacker.equipment.get("Weapon"), "name", None),
                weapon_slot="Weapon",
                weapon_type=getattr(self.attacker.equipment.get("Weapon"), "subtyp", None),
            )
        )

        # Roll for special attack
        luck_mod = self.attacker.check_mod("luck", luck_factor=SPECIAL_ATTACK_LUCK_FACTOR)
        roll_max = max(1, SPECIAL_ATTACK_ROLL_MAX - luck_mod)
        if not random.randint(0, roll_max):
            try:
                result = self.attacker.special_attack(target=self.defender)
                self._event_bus.emit(
                    create_combat_event(
                        EventType.ATTACK,
                        actor=self.attacker,
                        target=self.defender,
                        is_special=True,
                        source="special_attack",
                        attack_source="special_attack",
                    )
                )
                return result
            except NotImplementedError:
                pass

        opener_marks, opener_multiplier, opener_message = promotion_kits.begin_no_trace_opener(
            self.attacker,
            self.defender,
        )
        opener_message += promotion_kits.prepare_stolen_charge_payoff(
            self.attacker,
            "Attack",
        )
        hp_before = int(self.defender.health.current)
        message, hit, crit = self.attacker.weapon_damage(
            self.defender,
            dmg_mod=opener_multiplier,
            basic_attack=True,
        )
        message = opener_message + message
        opener_damage = max(0, hp_before - int(self.defender.health.current))
        if opener_marks:
            message += promotion_kits.resolve_weapon_finisher(
                self.attacker,
                self.defender,
                "No-Trace Opener",
                opener_marks,
                opener_damage,
                mana_cost=0,
                hit=hit,
            )
            message += promotion_kits.finish_no_trace_opener(
                self.attacker,
                self.defender,
                marks=opener_marks,
                hit=hit,
            )
        from ...classes import crossbow

        crossbow_message, crossbow_hit, crossbow_damage = crossbow.fire_crossbow(
            self.attacker,
            self.defender,
            encounter=self.encounter,
            rng=self._rng,
        )
        message += crossbow_message
        hit = hit or crossbow_hit
        if crossbow_damage:
            self.attacker._last_weapon_primary_damage += sum(crossbow_damage)
            self.attacker._last_weapon_primary_damage_instances.extend(crossbow_damage)
        damage = getattr(self.attacker, "_last_weapon_primary_damage", None)
        if damage is None:
            # Test doubles and legacy combatants may still return damage in the
            # third tuple position instead of the Character critical multiplier.
            damage = crit
        damage_instances = list(
            getattr(self.attacker, "_last_weapon_primary_damage_instances", ()) or ()
        )
        self._last_combat_result = CombatResult(
            action="Attack",
            actor=self.attacker,
            target=self.defender,
            hit=hit,
            crit=crit,
            damage=damage,
            extra={"damage_instances": damage_instances},
            message=message,
        )
        return message

    def _execute_flee(self) -> tuple[str, bool]:
        """Attempt to flee. Returns (message, success)."""
        if self.attacker is not self.player:
            escaped, message = footpad.aggressive_pursuit(
                self.player,
                self.attacker,
            )
            if escaped:
                member = self._member_for_character(self.attacker)
                if member is not None and member.resolution is None:
                    self.encounter.resolve_enemy(
                        member.combatant_id,
                        EnemyResolution.ESCAPED,
                        cause="enemy_flee",
                    )
                self.attacker.state = "normal"
            return message, escaped
        hostile = self._fastest_living_hostile()
        self._event_bus.emit(
            create_combat_event(
                EventType.FLEE_ATTEMPT,
                actor=self.attacker,
                target=hostile,
            )
        )
        success, message = self.attacker.flee(hostile)
        return message, success

    def _fastest_living_hostile(self):
        """Return the fastest hostile, resolving equal ratings by authored slot."""
        living = self.encounter.living_members
        if not living:
            return self.encounter.primary_enemy
        return max(
            living,
            key=lambda member: (
                initiative_rating(member.enemy, self.player),
                -member.slot,
            ),
        ).enemy

    def _execute_defend(self) -> str:
        """Enter defensive stance."""
        self._event_bus.emit(
            create_combat_event(
                EventType.DEFEND,
                actor=self.attacker,
                target=self.defender,
            )
        )
        skills = getattr(self.attacker, "spellbook", {}).get("Skills", {})
        hold_the_line = skills.get("Hold the Line")
        class_name = getattr(getattr(self.attacker, "cls", None), "name", "")
        if (
            self.attacker == self.player
            and class_name == "Knight Enchanter"
            and skills.get("Defensive Release") is not None
        ):
            from ...classes import promotion_kits

            return promotion_kits.defensive_release(self.attacker)
        if (
            self.attacker == self.player
            and class_name in {"Sentinel", "Stalwart Defender"}
            and hold_the_line is not None
        ):
            from ...classes import promotion_kits

            return promotion_kits.hold_the_line(self.attacker, as_defend=True)

        message = self.attacker.enter_defensive_stance(duration=1, source="Defend")
        if self.attacker == self.player:
            from ...classes import promotion_kits

            message += promotion_kits.build_resolve(
                self.player,
                10,
                "Defend",
            )
            message += promotion_kits.record_resolve_mastery(
                self.player,
                "stronghold",
                "Defend",
                action_deduplicated=True,
            )
        return message
