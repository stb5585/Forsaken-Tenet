"""Intent orchestration and result-ledger assembly for the battle engine."""

from __future__ import annotations

from copy import deepcopy
from typing import TYPE_CHECKING

from src.core.randomness import gameplay_random as random

from ...events.event_bus import EventType, create_combat_event
from ..actor_cycle import PLAYER_ACTOR_ID
from ..combat_result import CombatResult, CombatResultGroup
from ..targeting import TargetScope
from ..visibility import break_concealment
from .models import ActionIntent, ActionResult, ActionValidationCode

if TYPE_CHECKING:
    from collections.abc import Callable


class IntentResolutionMixin:
    """Route validated intents to their target-specific action resolvers."""

    def _execute_intent(
        self,
        intent: ActionIntent,
        *,
        slot_machine_callback: Callable | None = None,
    ) -> ActionResult:
        """Validate and execute an action for the engine-owned active actor."""
        actor_id = self.current_actor_id or self._actor_id_for(self.attacker)
        pending_charge = self._pending_charge(actor_id)
        if pending_charge is not None:
            if not self._charge_is_ready(pending_charge):
                return self._reject_intent(
                    ActionValidationCode.CHARGE_NOT_READY,
                    f"{self.attacker.name}'s charge resolves on a later readiness opportunity.\n",
                )
            if intent.engine_action == "Cancel Charge":
                pass
            elif intent.engine_action != pending_charge.get(
                "action"
            ) or intent.choice != pending_charge.get("choice"):
                return self._reject_intent(
                    ActionValidationCode.CHARGE_PENDING,
                    f"{self.attacker.name} must resolve or cancel their charge.\n",
                )

        if intent.engine_action == "Cancel Charge" and pending_charge is None:
            return self._reject_intent(
                ActionValidationCode.NO_CHARGE_TO_CANCEL,
                f"{self.attacker.name} has no charge to cancel.\n",
            )

        forced_action = self.get_forced_action()
        if forced_action is not None and forced_action.cancelled:
            return self._reject_intent(
                ActionValidationCode.FORCED_ACTION_REQUIRED,
                forced_action.cancel_message or "The forced action was cancelled.\n",
            )
        cancelling_pending_charge = (
            intent.engine_action == "Cancel Charge" and pending_charge is not None
        )
        if (
            forced_action is not None
            and not forced_action.cancelled
            and not cancelling_pending_charge
            and forced_action.intent is not None
            and (
                intent.engine_action != forced_action.intent.engine_action
                or intent.choice != forced_action.intent.choice
            )
        ):
            required = forced_action.intent.choice or forced_action.intent.engine_action
            return self._reject_intent(
                ActionValidationCode.FORCED_ACTION_REQUIRED,
                f"{self.attacker.name} must perform their forced action: {required}.\n",
            )

        if pending_charge is not None and intent.engine_action == pending_charge.get("action"):
            pending_target = pending_charge.get("target_id")
            if pending_target and not intent.target_ids:
                try:
                    pending_member = self.encounter.member_by_id(pending_target)
                except KeyError:
                    pending_member = None
                policy = getattr(
                    pending_charge.get("policy"), "value", pending_charge.get("policy")
                )
                if pending_member is None or not pending_member.is_living_hostile:
                    skill = pending_charge.get("ability")
                    if skill is not None:
                        skill.charging = False
                        if hasattr(skill, "charge_turns"):
                            skill.charge_turns = 0
                        if hasattr(skill, "charge_target"):
                            skill.charge_target = None
                    self._clear_pending_charge(actor_id, skill)
                    loss = (
                        "has no legal focus"
                        if policy == "retarget_focus"
                        else "lost its locked target"
                    )
                    message = (
                        f"{getattr(skill, 'name', 'The charged action')} fizzles "
                        f"because it {loss}.\n"
                    )
                    return ActionResult(
                        message=message,
                        combat_results=CombatResultGroup(
                            action=getattr(skill, "name", intent.engine_action),
                            actor_id=actor_id,
                            target_scope=TargetScope.SINGLE_ENEMY,
                            message=message,
                        ),
                    )

        scope = self._target_scope_for_action(intent.engine_action, intent.choice)
        targets = self._validated_intent_targets(intent, scope)
        if isinstance(targets, ActionResult):
            return targets
        confused_friendly_fire = False
        if (
            scope == TargetScope.SINGLE_ENEMY
            and actor_id != PLAYER_ACTOR_ID
            and int(getattr(self.attacker, "confused_turns", 0) or 0) > 0
        ):
            self.attacker.confused_turns = max(0, int(self.attacker.confused_turns) - 1)
            allies = [
                member
                for member in self.encounter.living_members
                if member.enemy is not self.attacker
            ]
            if allies and random.random() < 0.50:
                targets = [random.choice(allies)]
                confused_friendly_fire = True
        self._turn_action_committed = True

        if self._is_hostile_action(intent.engine_action, intent.choice, scope):
            # A hostile committed action identifies the concealed actor, even
            # when its contact roll later misses or it affects an area.
            break_concealment(self.attacker)

        target_ids = tuple(member.combatant_id for member in targets)
        if scope == TargetScope.SELF:
            target_ids = (actor_id or PLAYER_ACTOR_ID,)
        elif scope == TargetScope.ALL_ENEMIES and actor_id != PLAYER_ACTOR_ID:
            target_ids = (PLAYER_ACTOR_ID,)
        elif (
            scope == TargetScope.SINGLE_ENEMY
            and actor_id != PLAYER_ACTOR_ID
            and not confused_friendly_fire
        ):
            target_ids = (PLAYER_ACTOR_ID,)
        group = CombatResultGroup(
            action=intent.choice or intent.engine_action,
            actor_id=actor_id,
            target_scope=scope,
            target_ids=target_ids,
        )

        if scope == TargetScope.ALL_ENEMIES:
            return self._execute_all_enemy_intent(intent, targets, group)

        member = targets[0] if targets else None
        original_defender = self.defender
        if member is not None:
            self.defender = member.enemy
        elif scope == TargetScope.SELF:
            self.defender = self.attacker
        resolved_target = self.defender
        try:
            with self._target_resolution_context(member, scope, target_ids):
                result = self._execute_committed_action(
                    intent.engine_action,
                    intent.choice,
                    slot_machine_callback,
                )
        finally:
            if member is None:
                self.defender = original_defender

        # Multi-enemy rendering depends on the ledger to distinguish a newly
        # defeated member that should fade out from a merely dead, unresolved
        # combatant. Finalize the target before returning the action so pygame
        # never renders an intermediate "dead but unresolved" frame.
        if len(self.encounter.members) > 1:
            if member is not None and not member.enemy.is_alive():
                resurrection = member.enemy.spellbook.get("Spells", {}).get("Resurrection")
                if (
                    resurrection is not None
                    and abs(member.enemy.health.current) <= member.enemy.mana.current
                ):
                    resurrection_message = resurrection.cast(member.enemy)
                    if resurrection_message:
                        result.message += str(resurrection_message)
            self._record_final_enemy_resolutions()

        target_id = (
            member.combatant_id
            if member
            else (
                actor_id
                if scope == TargetScope.SELF
                else PLAYER_ACTOR_ID if scope == TargetScope.SINGLE_ENEMY else None
            )
        )
        raw_portion = getattr(self, "_last_combat_result", None)
        if isinstance(raw_portion, CombatResult):
            portion = deepcopy(raw_portion)
            portion.action = intent.choice or intent.engine_action
            portion.actor = self.attacker
            portion.target = member.enemy if member else resolved_target
            portion.actor_id = actor_id
            portion.target_id = target_id
            portion.message = result.message
        else:
            portion = CombatResult(
                action=intent.choice or intent.engine_action,
                actor=self.attacker,
                target=member.enemy if member else resolved_target,
                actor_id=actor_id,
                target_id=target_id,
                message=result.message,
            )
        group.add(portion)
        self._event_bus.emit(
            create_combat_event(
                EventType.ACTION_RESULT,
                actor=self.attacker,
                target=portion.target,
                result=portion,
                encounter_id=self.encounter.encounter_id,
                actor_id=actor_id,
                target_id=target_id,
                target_scope=scope.value,
                expanded_target_ids=list(target_ids),
            )
        )
        result.combat_results = group
        if member is not None and actor_id == PLAYER_ACTOR_ID and bool(intent.target_ids):
            self._focus_target_id = member.combatant_id
        return result

    def _is_hostile_action(self, action: str, choice: str | None, scope: TargetScope) -> bool:
        """Return whether a committed action exposes a concealed acting combatant."""
        if scope not in {TargetScope.SINGLE_ENEMY, TargetScope.ALL_ENEMIES}:
            return False
        if action == "Attack":
            return True
        ability = self._ability_for_action(action, choice)
        return ability is None or bool(getattr(ability, "targeting_hostile", True))
