"""Action targeting and validation for the battle engine."""

from __future__ import annotations

from typing import Any

from ..actor_cycle import PLAYER_ACTOR_ID
from ..combat_result import CombatResultGroup
from ..targeting import TargetScope
from ..visibility import is_revealed_to
from .models import (
    ActionIntent,
    ActionResult,
    ActionValidationCode,
)


class TurnExecutionMixin:
    """Translate actions into validated, explicitly targeted intents."""

    def _pending_charge(self, actor_id: str) -> dict[str, Any] | None:
        """Return the active charged action for an actor, if one is registered."""
        pending = self.pending_actions.get(actor_id)
        if pending is None or pending.get("action") != "Use Skill":
            return None
        return pending

    def _charge_is_ready(self, pending: dict[str, Any]) -> bool:
        """Return whether a pending charge has reached a later owner turn."""
        started_turn_id = pending.get("started_actor_turn_id")
        return started_turn_id is None or self._current_actor_turn_id > started_turn_id

    def _clear_pending_charge(self, actor_id: str, skill: Any | None = None) -> None:
        """Forget engine-owned bookkeeping for a completed or cancelled charge."""
        self.pending_actions.pop(actor_id, None)
        if self.charging_ability and self.charging_ability[0] is self.attacker:
            self.charging_ability = None
        if skill is not None and "Jump" in str(getattr(skill, "name", "")):
            self.attacker.class_effects["Jump"].active = False

    def _register_pending_charge(
        self,
        choice: str,
        skill: Any,
        *,
        preserve_start: bool,
    ) -> None:
        """Record a charge so it can progress only on later owner opportunities."""
        owner_id = self._actor_id_for(self.attacker)
        existing = self._pending_charge(owner_id)
        member = self._member_for_character(self.defender)
        target_id = existing.get("target_id") if preserve_start and existing else None
        if target_id is None:
            target_id = member.combatant_id if member else None
        self.pending_actions[owner_id] = {
            "action": "Use Skill",
            "choice": choice,
            "ability": skill,
            "target_id": target_id,
            "policy": getattr(skill, "target_loss_policy", "locked"),
            "started_actor_turn_id": (
                existing.get("started_actor_turn_id")
                if preserve_start and existing
                else self._current_actor_turn_id
            ),
        }

    def _cancel_pending_charge(self) -> str:
        """Cancel the current actor's ready charge without refunding its cost."""
        actor_id = self.current_actor_id or self._actor_id_for(self.attacker)
        pending = self._pending_charge(actor_id)
        if pending is None:
            return f"{self.attacker.name} has no charge to cancel.\n"
        skill = pending.get("ability")
        try:
            message = skill.cancel_charge(self.attacker) if skill is not None else ""
        except AttributeError:
            if skill is not None:
                skill.charging = False
                if hasattr(skill, "charge_turns"):
                    skill.charge_turns = 0
                if hasattr(skill, "charge_target"):
                    skill.charge_target = None
            message = ""
        self._clear_pending_charge(actor_id, skill)
        return message or f"{self.attacker.name} cancels their charge.\n"

    def prepare_intent(
        self,
        action_id: str,
        choice: str | None = None,
    ) -> ActionIntent:
        """Build an explicitly targeted intent from a selected action ID."""
        scope = self._target_scope_for_action(action_id, choice)
        target_ids: tuple[str, ...] = ()
        player_side = self.current_actor_id == PLAYER_ACTOR_ID or (
            self.current_actor_id is None and self.is_player_turn()
        )
        if (
            scope == TargetScope.SINGLE_ENEMY
            and player_side
            and len(self.encounter.members) == 1
            and len(self.encounter.living_members) == 1
        ):
            target_ids = (self.encounter.living_members[0].combatant_id,)
        elif scope == TargetScope.SINGLE_ENEMY and player_side:
            pending = self._pending_charge(PLAYER_ACTOR_ID)
            if pending:
                target_id = pending.get("target_id")
                try:
                    member = self.encounter.member_by_id(target_id)
                except KeyError:
                    member = None
                policy = pending.get("policy")
                if (
                    member is not None
                    and member.is_living_hostile
                    and is_revealed_to(self.attacker, member.enemy)
                ):
                    target_ids = (member.combatant_id,)
                elif getattr(policy, "value", policy) == "retarget_focus":
                    legal_targets = [
                        candidate
                        for candidate in self.encounter.living_members
                        if is_revealed_to(self.attacker, candidate.enemy)
                    ]
                    if legal_targets:
                        member = next(
                            (
                                candidate
                                for candidate in legal_targets
                                if candidate.combatant_id == self._focus_target_id
                            ),
                            legal_targets[0],
                        )
                        self._focus_target_id = member.combatant_id
                        target_ids = (member.combatant_id,)
                        skill = pending.get("ability")
                        if skill is not None and hasattr(skill, "charge_target"):
                            skill.charge_target = member.enemy
            else:
                self._refresh_focus()
                if self.encounter.living_members:
                    target_ids = (self._focus_target_id,)
        return ActionIntent(action_id=action_id, choice=choice, target_ids=target_ids)

    def _ability_for_action(self, action: str, choice: str | None):
        if not choice:
            return None
        actor = self.attacker if self.attacker is not None else self.player
        if actor is None:
            return None
        spellbook = getattr(actor, "spellbook", {})
        if action in {"Cast Spell", "Runic Boost"}:
            return spellbook.get("Spells", {}).get(choice)
        if action in {"Use Skill", "Tame"}:
            return spellbook.get("Skills", {}).get(choice if action == "Use Skill" else "Tame")
        return None

    def _target_scope_for_action(
        self,
        action: str,
        choice: str | None,
    ) -> TargetScope:
        """Derive the canonical target scope for a legacy action."""
        if action in {
            "Nothing",
            "Cancelled",
            "Cancel Charge",
            "Pickup Weapon",
            "Flee",
            "Recall",
            "Companion",
            "Repertoire",
            "Totem",
            "Transform",
            "Untransform",
            "Dismiss Form",
        }:
            return TargetScope.NONE
        if action in {"Defend", "Summon"}:
            return TargetScope.SELF
        if action == "Use Item":
            if choice:
                import re

                item_key = re.split(r"\s{2,}", choice)[0]
                actor = self.attacker if self.attacker is not None else self.player
                items = getattr(actor, "inventory", {}).get(item_key, [])
                item = items[0] if items else None
                if isinstance(item, type):
                    item = item()
                spell = getattr(item, "spell", None)
                if (
                    getattr(item, "subtyp", None) == "Scroll"
                    and getattr(spell, "subtyp", None) != "Support"
                ):
                    return TargetScope.SINGLE_ENEMY
            return TargetScope.SELF
        ability = self._ability_for_action(action, choice)
        if ability is not None:
            declared = getattr(ability, "target_scope", TargetScope.SINGLE_ENEMY)
            raw_data = getattr(ability, "_raw_data", {})
            if isinstance(raw_data, dict) and "target_scope" in raw_data:
                return declared
            if declared in {TargetScope.NONE, TargetScope.ALL_ENEMIES}:
                return declared
            if getattr(ability, "passive", False):
                return TargetScope.NONE
            if getattr(ability, "subtyp", None) in {"Heal", "Support"} or getattr(
                ability, "self_target", False
            ):
                return TargetScope.SELF
            return declared
        return TargetScope.SINGLE_ENEMY

    def target_scope_for_action(
        self,
        action: str,
        choice: str | None = None,
    ) -> TargetScope:
        """Return the canonical target scope for a prospective action."""
        return self._target_scope_for_action(action, choice)

    def _reject_intent(
        self,
        code: ActionValidationCode,
        message: str,
    ) -> ActionResult:
        self._turn_action_committed = False
        self.logger.log_event(
            "Invalid Intent",
            self.attacker,
            target=self.defender,
            outcome=code.value,
            notes=message.strip(),
            actor_id=self.current_actor_id,
            target_id=self._actor_id_for(self.defender),
            opportunity_actor_id=self.current_actor_id,
            ready_at=self.current_readiness,
            round_number=self.round_number,
            actor_turn_id=getattr(self, "_current_actor_turn_id", 0),
        )
        return ActionResult(
            message=message,
            committed=False,
            validation_code=code,
            combat_results=CombatResultGroup(message=message),
        )

    def _validated_intent_targets(
        self,
        intent: ActionIntent,
        scope: TargetScope,
    ):
        supplied = intent.target_ids
        if scope in {TargetScope.NONE, TargetScope.SELF, TargetScope.ALL_ENEMIES}:
            if supplied:
                return self._reject_intent(
                    ActionValidationCode.WRONG_TARGET_SCOPE,
                    f"{scope.value} actions do not accept explicit target IDs.\n",
                )
            if scope == TargetScope.ALL_ENEMIES:
                player_side = self.current_actor_id == PLAYER_ACTOR_ID or (
                    self.current_actor_id is None and self.is_player_turn()
                )
                if not player_side:
                    return []
                return list(self.encounter.living_members)
            return []

        player_side = self.current_actor_id == PLAYER_ACTOR_ID or (
            self.current_actor_id is None and self.is_player_turn()
        )
        if not player_side:
            if supplied:
                return self._reject_intent(
                    ActionValidationCode.WRONG_TARGET_SCOPE,
                    "Enemy actions target the active player-side combatant.\n",
                )
            if not is_revealed_to(self.attacker, self.active_player_character):
                return self._reject_intent(
                    ActionValidationCode.CONCEALED_TARGET,
                    "That concealed opponent cannot be targeted directly. Wait for detection or use an area action.\n",
                )
            return []
        if not supplied:
            return self._reject_intent(
                ActionValidationCode.MISSING_TARGET,
                "Choose one enemy target.\n",
            )
        if len(supplied) != 1:
            return self._reject_intent(
                ActionValidationCode.WRONG_TARGET_COUNT,
                "Single-enemy actions require exactly one target.\n",
            )
        try:
            member = self.encounter.member_by_id(supplied[0])
        except KeyError:
            return self._reject_intent(
                ActionValidationCode.UNKNOWN_TARGET,
                "That target is not part of this encounter.\n",
            )
        if not member.is_living_hostile:
            return self._reject_intent(
                ActionValidationCode.UNAVAILABLE_TARGET,
                "That target is dead or has already left the encounter.\n",
            )
        if not is_revealed_to(self.attacker, member.enemy):
            return self._reject_intent(
                ActionValidationCode.CONCEALED_TARGET,
                "That concealed opponent cannot be targeted directly. Wait for detection or use an area action.\n",
            )
        return [member]
