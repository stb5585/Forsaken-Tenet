"""Turn preparation and forced-action handling for the battle engine."""

from __future__ import annotations

from typing import TYPE_CHECKING

from src.core.randomness import gameplay_random as random

from ...classes import (
    ability_mechanics,
    bard,
    lycan,
    paladin,
)
from ...events.event_bus import combat_event_context
from ..targeting import TargetScope
from ..visibility import detect, is_concealed, is_revealed_to
from .models import (
    ActionIntent,
    ForcedAction,
    PreTurnResult,
)

if TYPE_CHECKING:
    from ...character import Character


class TurnPreparationMixin:
    """Prepare combatants and determine forced actions at turn start."""

    def _cached_forced_cancellation(self) -> ForcedAction | None:
        """Return a cancellation that already consumed this actor's choice."""
        forced = self._forced_cancellation
        actor_id = self.current_actor_id or self._actor_id_for(self.attacker)
        if (
            forced is not None
            and self._forced_cancellation_actor_id == actor_id
            and self._forced_cancellation_turn_id == self._current_actor_turn_id
        ):
            return forced
        self._forced_cancellation = None
        self._forced_cancellation_actor_id = None
        return None

    def _remember_forced_cancellation(self, message: str) -> ForcedAction:
        """Keep a forced cancellation enforceable after its charge state is cleared."""
        forced = ForcedAction(cancel_message=message)
        self._forced_cancellation = forced
        self._forced_cancellation_actor_id = self.current_actor_id or self._actor_id_for(
            self.attacker
        )
        self._forced_cancellation_turn_id = self._current_actor_turn_id
        return forced

    @staticmethod
    def _clear_stale_charging_actions(character: Character) -> None:
        """Clear charge state that should never persist across battles."""
        if hasattr(character, "class_effects") and "Jump" in character.class_effects:
            character.class_effects["Jump"].active = False

        for skill_group in getattr(character, "spellbook", {}).values():
            for skill in getattr(skill_group, "values", lambda: [])():
                if not getattr(skill, "charging", False):
                    continue
                skill.charging = False
                if hasattr(skill, "charge_turns"):
                    skill.charge_turns = 0
                if hasattr(skill, "charge_target"):
                    skill.charge_target = None

    def pre_turn(self) -> PreTurnResult:
        """
        Process the attacker's start-of-turn effects and check activity.

        Call this at the beginning of each turn before requesting an action.
        """
        result = PreTurnResult()

        # Capture activity before ticking durations so single-turn control-loss
        # effects still consume the current turn when they expire this tick.
        active_at_turn_start, inactive_reason_at_turn_start = self.attacker.check_active()

        hp_before = self.player.health.current if self.attacker == self.player else 0

        # Process status effects (poison ticks, bleed, regen, etc.)
        with combat_event_context(
            encounter_id=self.encounter.encounter_id,
            actor_id=self.current_actor_id,
            target_id=self.current_actor_id,
            target_scope=TargetScope.SELF.value,
            expanded_target_ids=[self.current_actor_id],
        ):
            effects_text = self.attacker.effects()
        if effects_text:
            result.effects_text = effects_text

            # Handle exploding shield (Crusader Power Up expiring deals damage)
            if "damage" in effects_text:
                try:
                    dmg = int(effects_text.split(" damage")[0].split(" ")[-1])
                    self.defender.health.current -= dmg
                    result.shield_explosion_damage = dmg
                except (ValueError, IndexError):
                    pass
        enemy_member = self._member_for_character(self.attacker)
        if enemy_member is not None:
            thirst_text = ability_mechanics.trigger_hemorrhage_thirst(
                self.player,
                getattr(self.attacker, "_last_bleed_tick_damage", 0),
            )
            if thirst_text:
                result.effects_text = f"{result.effects_text or ''}{thirst_text}"

        if self.attacker == self.player:
            paladin.tick_turn(self.player)
            song_text = bard.tick_song(self.player)
            if song_text:
                result.effects_text = f"{result.effects_text or ''}{song_text}"
            frenzy_text = lycan.tick_frenzy(self.player)
            if frenzy_text:
                result.effects_text = f"{result.effects_text or ''}{frenzy_text}"

        if self.attacker == self.player:
            duel_text = self._fail_no_healing_duel_if_healed(hp_before)
            if duel_text:
                result.effects_text = f"{result.effects_text or ''}{duel_text}"
                result.died_from_effects = True
                result.can_act = False
                return result

        # Check if the attacker died from their own effects
        if not self.attacker.is_alive():
            result.died_from_effects = True
            result.can_act = False
            return result

        if enemy_member is not None:
            active_chorus = bard.active_song(self.player) == "Chorus Time"
            dumbfounded = (
                bard.chorus_time_dumbfounds(
                    self.player,
                    self.attacker,
                    rng=random,
                )
                if active_chorus
                else bard.consume_chorus_time_coda(
                    self.player,
                    self.attacker,
                    rng=random,
                )
            )
            if dumbfounded:
                result.effects_text = (
                    f"{result.effects_text or ''}{self.attacker.name} is "
                    "dumbfounded by Chorus Time and loses the turn.\n"
                )
                result.can_act = False
                result.inactive_reason = "Dumbfounded by Chorus Time."
                return result

        if not active_at_turn_start:
            interrupted = self._cancel_interrupted_charging_action()
            if interrupted:
                result.effects_text = f"{result.effects_text or ''}{interrupted}"
            if self.attacker == self.player:
                vow_text = paladin.on_incapacitated(self.player)
                if vow_text:
                    result.effects_text = f"{result.effects_text or ''}{vow_text}"
            result.can_act = False
            result.inactive_reason = self._inactive_reason_after_effects(
                inactive_reason_at_turn_start,
                result.effects_text,
            )
            return result

        detection_text = self._automatic_detection_text()
        if detection_text:
            result.effects_text = f"{result.effects_text or ''}{detection_text}"

        # Check if the attacker can act this turn
        active, text = self.attacker.check_active()
        if not active:
            result.can_act = False
            result.inactive_reason = text

        return result

    def _automatic_detection_text(self) -> str:
        """Attempt to reveal concealed opponents at the start of an active turn."""
        if self._member_for_character(self.attacker) is not None:
            concealed = (
                [self.active_player_character]
                if is_concealed(self.active_player_character)
                and not is_revealed_to(self.attacker, self.active_player_character)
                else []
            )
        else:
            concealed = [
                member.enemy
                for member in self.encounter.living_members
                if is_concealed(member.enemy) and not is_revealed_to(self.attacker, member.enemy)
            ]
        found = sum(detect(self.attacker, target, rng=self._rng) for target in concealed)
        if not found:
            return ""
        opponent_label = "opponent" if found == 1 else "opponents"
        return f"{self.attacker.name} detects {found} concealed {opponent_label}.\n"

    @staticmethod
    @staticmethod
    def _inactive_reason_after_effects(reason: str, effects_text: str) -> str:
        """Suppress stale incapacity text when the logged status tick already explains recovery."""
        recovery_terms = (
            "is no longer stunned",
            "is no longer asleep",
            "is no longer prone",
            "returns to their true form",
        )
        effects_lower = (effects_text or "").lower()
        if any(term in effects_lower for term in recovery_terms):
            return ""
        return reason

    def _cancel_interrupted_charging_action(self) -> str:
        """Cancel active charge-up actions when the actor is incapacitated before acting."""
        if not self.attacker or not self.attacker.incapacitated():
            return ""

        if self.attacker.class_effects["Jump"].active:
            skills = self.attacker.spellbook.get("Skills", {})
            jump_choice = next((name for name in skills if "Jump" in name), None)
            jump_skill = skills.get(jump_choice) if jump_choice else None
            unstoppable = bool(getattr(jump_skill, "modifications", {}).get("Unstoppable", False))
            if unstoppable:
                return ""
            try:
                cancel_msg = jump_skill.cancel_charge(self.attacker) if jump_skill else ""
            except AttributeError:
                cancel_msg = ""
            self.attacker.class_effects["Jump"].active = False
            self._clear_pending_charge(self._actor_id_for(self.attacker), jump_skill)
            return cancel_msg or f"{self.attacker.name}'s Jump was cancelled.\n"

        for _skill_name, skill in self.attacker.spellbook.get("Skills", {}).items():
            if getattr(skill, "charging", False):
                try:
                    message = skill.cancel_charge(self.attacker)
                except AttributeError:
                    skill.charging = False
                    message = f"{self.attacker.name}'s {getattr(skill, 'name', 'charge')} was interrupted!\n"
                self._clear_pending_charge(self._actor_id_for(self.attacker), skill)
                return message
        return ""

    def get_forced_action(self) -> ForcedAction | None:
        """
        Check if the current attacker's action is forced.

        Returns a ForcedAction when the attacker must perform a specific action
        (berserk, charging skill, jump), or None when the actor has free choice.
        """
        cached_cancellation = self._cached_forced_cancellation()
        if cached_cancellation is not None:
            return cached_cancellation

        # Jump in progress. Resolve the airborne/charging state before Berserk
        # can force a basic attack, especially when Unstoppable is active.
        if self.attacker.class_effects["Jump"].active:
            skills = self.attacker.spellbook.get("Skills", {})
            jump_choice = next((name for name in skills if "Jump" in name), None)
            jump_skill = skills.get(jump_choice) if jump_choice else None
            unstoppable = bool(getattr(jump_skill, "modifications", {}).get("Unstoppable", False))

            if self.attacker.incapacitated() and not unstoppable:
                # Cancel the jump if incapacitated during charge.
                try:
                    cancel_msg = jump_skill.cancel_charge(self.attacker) if jump_skill else ""
                except AttributeError:
                    cancel_msg = ""
                if not cancel_msg:
                    cancel_msg = f"{self.attacker.name}'s Jump was cancelled.\n"
                self.attacker.class_effects["Jump"].active = False
                self._clear_pending_charge(self._actor_id_for(self.attacker), jump_skill)
                return self._remember_forced_cancellation(cancel_msg)

            if jump_choice:
                self.attacker.class_effects["Jump"].active = False
                return ForcedAction(intent=self._forced_intent("Use Skill", jump_choice))

        # Ongoing charging ability (e.g. Charge, Crushing Blow, Dragon Breath).
        for skill_name, skill in self.attacker.spellbook.get("Skills", {}).items():
            if getattr(skill, "charging", False):
                return ForcedAction(intent=self._forced_intent("Use Skill", skill_name))

        if self.charging_ability:
            charge_owner, ability_name, _skill_obj = self.charging_ability
            if charge_owner == self.attacker:
                return ForcedAction(intent=self._forced_intent("Use Skill", ability_name))

        # Berserk forces a basic attack unless a higher-priority forced action
        # such as an active Jump or charge-up has already claimed the turn.
        berserk = self.attacker.status_effects["Berserk"]
        composed_wrath = getattr(
            berserk, "source", None
        ) == "Frenzy" and "Composed Wrath" in self.attacker.spellbook.get("Skills", {})
        if berserk.active and not composed_wrath:
            return ForcedAction(intent=self._forced_intent("Attack"))

        return None

    def _forced_intent(self, action_id: str, choice: str | None = None) -> ActionIntent:
        """Build the fully targeted intent for an engine-owned forced action."""
        target_ids: tuple[str, ...] = ()
        scope = self._target_scope_for_action(action_id, choice)
        if scope == TargetScope.SINGLE_ENEMY and self.is_player_turn():
            pending = self._pending_charge(
                self.current_actor_id or self._actor_id_for(self.attacker)
            )
            pending_target = pending.get("target_id") if pending else None
            legal_ids = {member.combatant_id for member in self.encounter.living_members}
            if pending_target in legal_ids:
                target_ids = (str(pending_target),)
            elif legal_ids:
                self._refresh_focus()
                target_ids = (self._focus_target_id,)
        return ActionIntent(action_id=action_id, choice=choice, target_ids=target_ids)

    def get_enemy_action(self) -> tuple[str, str | None]:
        """Ask the enemy AI for its chosen action. Returns (action, choice)."""
        if not is_revealed_to(self.attacker, self.active_player_character):
            return "Nothing", None
        return self.attacker.options(
            self.active_player_character,
            self.available_actions,
            self.tile,
        )

    def is_player_turn(self) -> bool:
        """Return True if the current attacker is the player (or summon)."""
        return self.attacker == self.player or self.attacker == self.summon

    # ── Action execution ─────────────────────────────────────────────
