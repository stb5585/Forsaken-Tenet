"""Concrete UI-agnostic battle engine."""

from __future__ import annotations

import random
from contextlib import contextmanager
from typing import TYPE_CHECKING

from ...classes import ability_mechanics, astromancer, bard, footpad, paladin, promotion_kits
from ...contracts import TimelineEntry
from ...enemies.identity import remember_defeat_identity
from ...events.event_bus import (
    EventType,
    combat_event_context,
    create_combat_event,
    get_event_bus,
)
from ..actor_cycle import (
    MAX_TEMPO,
    MIN_TEMPO,
    PLAYER_ACTOR_ID,
    STANDARD_ACTION_COST,
    ActorCycle,
    build_readiness_cycle,
)
from ..battle_logger import BattleLogger
from ..encounter import CombatEncounter
from .actions import BattleActionMixin
from .models import ActionResult, ForcedAction
from .outcomes import BattleOutcomeMixin
from .turns import BattleTurnMixin

if TYPE_CHECKING:
    from typing import Any, Callable

    from ...character import Character
    from ...player import Player


class BattleEngine(BattleTurnMixin, BattleActionMixin, BattleOutcomeMixin):
    """
    UI-agnostic combat engine.

    Holds all combat state and provides methods for each phase of a turn.
    UI layers drive the loop and call these methods; the engine never
    renders or reads input itself.
    """

    def __init__(
        self,
        player: Player,
        enemy: Character | None = None,
        tile: Any | None = None,
        game: Any | None = None,
        logger: BattleLogger | None = None,
        *,
        encounter: CombatEncounter | None = None,
        rng: Any | None = None,
    ):
        if (enemy is None) == (encounter is None):
            raise ValueError("Supply exactly one of enemy or encounter.")
        if tile is None:
            raise ValueError("BattleEngine requires a combat tile.")
        if encounter is not None and not isinstance(encounter, CombatEncounter):
            raise TypeError("encounter must be a CombatEncounter.")

        self.player: Player = player
        self.player._active_combat = True
        if encounter is None:
            assert enemy is not None
            encounter = CombatEncounter.singleton(enemy)
        self.encounter: CombatEncounter = encounter
        self.player._combat_encounter = encounter
        self.tile: Any = tile
        self.game: Any = game
        self.logger: BattleLogger = logger if logger else BattleLogger()
        self._rng = rng or random
        for member in self.encounter.members:
            remember_defeat_identity(member.enemy)

        self.flee: bool = False
        self.boss: bool = "Boss" in str(tile)

        self.summon_active: bool = False
        self.summon: Character | None = None
        self.player.active_summon_name = None

        self.attacker: Character | None = None
        self.defender: Character | None = None
        self._actor_cycle: ActorCycle | None = None
        self._focus_target_id: str = self.encounter.primary_member.combatant_id
        self._active_target_member = None
        self._active_target_scope = None
        self._active_expanded_target_ids: tuple[str, ...] = ()
        self._current_actor_turn_id = 0
        self._turn_action_committed = True
        self._completed_outcome = None
        self._forced_cancellation: ForcedAction | None = None
        self._forced_cancellation_actor_id: str | None = None
        self._forced_cancellation_turn_id = 0
        self._reaction_executions: set[tuple[int, str]] = set()

        # Track charging abilities across turns
        self.charging_ability: tuple[Character, str, Any] | None = None  # (owner, name, skill_obj)
        self.pending_actions: dict[str, dict[str, Any]] = {}
        self.delayed_spells: list[dict[str, Any]] = []

        # Available actions refreshed each turn
        self.available_actions: list = self._available_actions()

        self._event_bus = get_event_bus()

    @property
    def fixed_turn_order(self) -> tuple[str, ...]:
        """Return stable actor IDs retained for compatibility with legacy callers."""
        return self._actor_cycle.order if self._actor_cycle else ()

    @property
    def current_actor_id(self) -> str | None:
        """Return the scheduled actor slot ID."""
        return self._actor_cycle.current_actor_id if self._actor_cycle else None

    @property
    def round_number(self) -> int:
        """Return the current one-based encounter round."""
        return self._actor_cycle.round_number if self._actor_cycle else 0

    @property
    def total_started_actor_turns(self) -> int:
        """Return the number of actor turns begun by the cycle."""
        return self._actor_cycle.total_started_actor_turns if self._actor_cycle else 0

    @property
    def current_readiness(self) -> float:
        """Return the virtual readiness time of the current opportunity."""
        return self._actor_cycle.current_ready_at if self._actor_cycle else 0.0

    def readiness_cost(self, actor: Character | None = None) -> float:
        """Return the current actor's approved virtual-time action cost.

        Effective Speed may change during combat, while the encounter-start
        median retained by the cycle remains the tempo baseline.
        """
        if self._actor_cycle is None:
            return STANDARD_ACTION_COST
        active_actor = actor if actor is not None else self.attacker
        if active_actor is None:
            return STANDARD_ACTION_COST
        member = self._member_for_character(active_actor)
        opponent = self.active_player_character if member is not None else self._focused_enemy()
        speed = max(0.0, float(active_actor.check_mod("speed", enemy=opponent)))
        tempo = max(
            MIN_TEMPO,
            min(MAX_TEMPO, speed / self._actor_cycle.median_speed),
        )
        return STANDARD_ACTION_COST / tempo

    def timeline_entries(self, limit: int = 6) -> tuple[TimelineEntry, ...]:
        """Return predicted normal opportunities for timeline consumers.

        This is a read-only runtime projection; presentation never owns or
        mutates readiness scheduling.
        """
        if self._actor_cycle is None or limit <= 0:
            return ()

        def actor_for_id(actor_id: str) -> Character:
            return (
                self.active_player_character
                if actor_id == PLAYER_ACTOR_ID
                else self.encounter.member_by_id(actor_id).enemy
            )

        opportunities = self._actor_cycle.preview(
            self._valid_actor_ids(),
            lambda actor_id: self.readiness_cost(actor_for_id(actor_id)),
            limit,
        )
        return tuple(
            TimelineEntry(
                actor_id=actor_id,
                display_label=str(getattr(actor, "name", actor_id)),
                ready_at=ready_at,
            )
            for actor_id, ready_at in opportunities
            for actor in (actor_for_id(actor_id),)
        )

    @property
    def focus_target_id(self) -> str:
        """Return the sticky player focus, falling back when necessary."""
        self._refresh_focus()
        return self._focus_target_id

    def set_focus_target(self, combatant_id: str) -> str:
        """Select a living hostile without committing the current actor's turn.

        Args:
            combatant_id: Stable encounter-member ID to focus.

        Returns:
            The selected combatant ID.

        Raises:
            KeyError: If the ID does not belong to this encounter.
            ValueError: If the member is dead or already resolved.
        """
        member = self.encounter.member_by_id(combatant_id)
        if not member.is_living_hostile:
            raise ValueError(f"Combatant {combatant_id!r} is not a living target.")
        self._focus_target_id = member.combatant_id
        if self.current_actor_id == PLAYER_ACTOR_ID:
            self.defender = member.enemy
        return self._focus_target_id

    def cycle_focus(self, direction: int = 1) -> str:
        """Cycle focus through living members in authored order."""
        living = self.encounter.living_members
        if not living:
            raise ValueError("The encounter has no living hostile targets.")
        ids = [member.combatant_id for member in living]
        self._refresh_focus()
        try:
            current = ids.index(self._focus_target_id)
        except ValueError:
            current = 0
        step = -1 if direction < 0 else 1
        return self.set_focus_target(ids[(current + step) % len(ids)])

    @property
    def active_player_character(self) -> Character:
        """Return the character currently occupying the player-side slot."""
        if self.summon_active and self.summon and self.summon.is_alive():
            return self.summon
        return self.player

    def _refresh_focus(self) -> None:
        try:
            member = self.encounter.member_by_id(self._focus_target_id)
        except KeyError:
            member = None
        if member is None or not member.is_living_hostile:
            living = self.encounter.living_members
            if living:
                self._focus_target_id = living[0].combatant_id

    def _focused_enemy(self) -> Character:
        """Return the valid focus enemy for internal automatic targeting."""
        self._refresh_focus()
        if self.encounter.living_members:
            return self.encounter.member_by_id(self._focus_target_id).enemy
        return self.encounter.primary_enemy

    def _member_for_character(self, character: Character | None):
        for member in self.encounter.members:
            if member.enemy is character:
                return member
        return None

    def _actor_id_for(self, character: Character | None) -> str | None:
        if character is self.player or character is self.summon:
            return PLAYER_ACTOR_ID
        member = self._member_for_character(character)
        return member.combatant_id if member else None

    def _valid_actor_ids(self) -> set[str]:
        valid = set()
        if self.active_player_character.is_alive():
            valid.add(PLAYER_ACTOR_ID)
        valid.update(member.combatant_id for member in self.encounter.living_members)
        return valid

    def add_enemy_reinforcement(self, enemy: Character):
        """Add one enemy reinforcement to the live encounter and actor cycle."""
        if len(self.encounter.living_members) >= 2:
            return None
        member = self.encounter.add_enemy(enemy)
        remember_defeat_identity(enemy)
        if self._actor_cycle is not None:
            self._actor_cycle.add_actor(member.combatant_id)
        return member

    def _sync_actor_aliases(self) -> None:
        if not self._actor_cycle:
            return
        actor_id = self._actor_cycle.current_actor_id
        self._refresh_focus()
        if actor_id == PLAYER_ACTOR_ID:
            self.attacker = self.active_player_character
            living = self.encounter.living_members
            self.defender = (
                self.encounter.member_by_id(self._focus_target_id).enemy
                if living
                else self.encounter.primary_enemy
            )
        else:
            self.attacker = self.encounter.member_by_id(actor_id).enemy
            self.defender = self.active_player_character

    @contextmanager
    def _target_resolution_context(self, member, scope, target_ids):
        previous = self._active_target_member
        self._active_target_member = member
        if member is not None:
            target_id = member.combatant_id
        elif getattr(scope, "value", scope) == "self":
            target_id = self._actor_id_for(self.attacker)
        elif getattr(scope, "value", scope) == "single_enemy":
            target_id = PLAYER_ACTOR_ID
        elif (
            getattr(scope, "value", scope) == "all_enemies"
            and self._actor_id_for(self.attacker) != PLAYER_ACTOR_ID
        ):
            target_id = PLAYER_ACTOR_ID
        else:
            target_id = None
        try:
            with combat_event_context(
                encounter_id=self.encounter.encounter_id,
                actor_id=self._actor_id_for(self.attacker),
                target_id=target_id,
                target_scope=scope.value,
                expanded_target_ids=list(target_ids),
            ):
                yield
        finally:
            self._active_target_member = previous

    def _is_class_ring_trial_enemy(self) -> bool:
        """Return whether this fight should use Class Ring trial bookkeeping."""
        return bool(
            getattr(self.encounter.primary_enemy, "grandmaster_trial_enemy", False)
            or getattr(self.encounter.primary_enemy, "class_ring_trial_enemy", False)
        )

    def _is_thieves_guild_trial_enemy(self) -> bool:
        """Return whether this fight is a Thieves Guild initiation trial."""
        return bool(getattr(self.encounter.primary_enemy, "thieves_guild_trial_enemy", False))

    def _class_ring_trial_name(self) -> str:
        return str(
            getattr(self.encounter.primary_enemy, "class_ring_trial_name", "Class Ring trial")
        )

    def _thieves_guild_trial_name(self) -> str:
        enemy = self.encounter.primary_enemy
        return str(
            getattr(
                enemy,
                "thieves_guild_trial_name",
                getattr(enemy, "name", "initiation trial"),
            )
        )

    def _no_healing_duel_active(self) -> bool:
        return bool(
            getattr(
                self.encounter.primary_enemy,
                "class_ring_no_healing_duel",
                False,
            )
        )

    def _available_actions(self) -> list:
        if self.summon_active and self.attacker == self.summon and self.summon:
            options = getattr(self.summon, "options", None)
            if callable(options):
                return options()
            return ["Attack", "Recall"]
        actions = list(self.tile.available_actions(self.player))
        if astromancer.boostable_spells(self.player) and "Runic Boost" not in actions:
            insert_at = actions.index("Cast Spell") + 1 if "Cast Spell" in actions else len(actions)
            actions.insert(insert_at, "Runic Boost")
        if (
            self.attacker == self.player
            and "Tame" in getattr(self.player, "spellbook", {}).get("Skills", {})
            and not ability_mechanics.has_living_tamed_companion(self.player)
            and not self.player.abilities_suppressed()
            and "Tame" not in actions
        ):
            insert_at = actions.index("Attack") + 1 if "Attack" in actions else len(actions)
            actions.insert(insert_at, "Tame")
        if (
            self.attacker == self.player
            and ability_mechanics.available_beast_companion_commands(self.player)
            and not self.player.abilities_suppressed()
            and "Companion" not in actions
        ):
            insert_at = actions.index("Attack") + 1 if "Attack" in actions else len(actions)
            actions.insert(insert_at, "Companion")
        if (
            self.attacker == self.player
            and bard.mastered_repertoire_songs(self.player)
            and not self.player.abilities_suppressed()
            and "Repertoire" not in actions
        ):
            insert_at = actions.index("Use Skill") + 1 if "Use Skill" in actions else len(actions)
            actions.insert(insert_at, "Repertoire")
        if self.attacker is not None:
            actor_id = self.current_actor_id or self._actor_id_for(self.attacker)
            if self._pending_charge(actor_id) is not None and "Cancel Charge" not in actions:
                actions.append("Cancel Charge")
        return actions

    def summoner_support_actions(self) -> list[str]:
        """Return limited owner actions available while a summon takes point."""
        if not self.summon_active or not self.summon:
            return []
        actions = []
        if getattr(self.player, "inventory", None):
            actions.append("Use Item")
        actions.append("Recall")
        skills = getattr(self.player, "spellbook", {}).get("Skills", {})
        for name in skills:
            if name in {"Heal Summon", "Raise Summon", "Conduit Command"} or name.startswith(
                "Invoke "
            ):
                actions.append("Use Skill")
                break
        return actions

    def summoner_support_skill_names(self) -> list[str]:
        """Return owner skill names valid through the active-summon Support menu."""
        skills = getattr(self.player, "spellbook", {}).get("Skills", {})
        return [
            name
            for name, skill in skills.items()
            if (
                name in {"Heal Summon", "Raise Summon", "Conduit Command"}
                or name.startswith("Invoke ")
            )
            and not getattr(skill, "passive", False)
        ]

    def execute_summoner_support_action(
        self,
        action: str,
        choice: str | None = None,
        slot_machine_callback: Callable | None = None,
    ) -> ActionResult:
        """Execute a constrained Thaumaturgist intervention during an active Xenid turn."""
        if not self.summon_active or not self.summon:
            result = ActionResult()
            result.message = "No active summon can be supported.\n"
            return result

        original_attacker = self.attacker
        original_defender = self.defender
        self.attacker = self.player
        self.defender = self._focused_enemy()
        try:
            result = self.execute_action(action, choice, slot_machine_callback)
        finally:
            if self.summon_active and self.summon:
                self.attacker = self.summon
                self.defender = self._focused_enemy()
            else:
                self.attacker = self.player
                self.defender = self._focused_enemy()
            self.available_actions = self._available_actions()
            if not self.summon_active and self._member_for_character(original_attacker) is not None:
                self.attacker = original_attacker
                self.defender = original_defender
        return result

    def _fail_no_healing_duel_if_healed(self, hp_before: int) -> str:
        """Fail the Berserker duel when the player restores HP during the bout."""
        if not self._no_healing_duel_active():
            return ""
        if self.player.health.current <= hp_before:
            return ""
        self.player.health.current = 0
        return "The No Healing Duel rejects restored life. You yield the bout.\n"

    # ── Lifecycle ────────────────────────────────────────────────────

    def start_battle(self) -> tuple[Character, Character]:
        """
        Initialise the battle: determine initiative, emit events, start logging.

        Returns:
            (first_actor, second_actor) — the initiative order.
        """
        if len(self.encounter.members) > 2:
            raise NotImplementedError("Multi-enemy combat currently supports at most two enemies.")
        if len(self.encounter.members) > 1 and (
            self.boss
            or any(
                getattr(member.enemy, flag, False)
                for member in self.encounter.members
                for flag in (
                    "grandmaster_trial_enemy",
                    "class_ring_trial_enemy",
                    "thieves_guild_trial_enemy",
                    "scripted_combat_enemy",
                )
            )
        ):
            raise NotImplementedError(
                "Boss, trial, and scripted multi-enemy encounters are not supported."
            )

        anti_magic_active = bool(getattr(self.player, "anti_magic_active", False))
        for member in self.encounter.members:
            member.enemy.anti_magic_active = anti_magic_active

        self._clear_stale_charging_actions(self.player)
        for member in self.encounter.members:
            self._clear_stale_charging_actions(member.enemy)
        self.player._final_assault_used = False
        self.player._last_stand_used = False
        self.player._foretell_snapshot = None
        self.player._rewind_snapshot = None
        footpad.start_combat(self.player)
        from ...classes import healer

        healer.start_combat(self.player)
        from ...classes import mage_mechanics

        mage_mechanics.start_combat(self.player)
        from ...classes import pathfinder

        pathfinder.start_combat(self.player)
        from ...classes import warrior

        warrior.start_combat(self.player)
        kit_start_message = promotion_kits.start_combat(self.player)
        promotion_kits.combat_state(self.player)["visible_enemy_types"] = {
            str(getattr(member.enemy, "enemy_typ", ""))
            for member in self.encounter.members
            if self.show_enemy_details(member.enemy) and getattr(member.enemy, "enemy_typ", None)
        }
        if kit_start_message:
            messages = getattr(self.player, "_promotion_kit_messages", None)
            if not isinstance(messages, list):
                messages = []
                self.player._promotion_kit_messages = messages
            messages.append(kit_start_message)
        forced_enemy_initiative = bool(getattr(self.tile, "trap_forced_initiative", False))
        player_loses_initiative = forced_enemy_initiative or bool(
            getattr(self.player, "encumbered", False)
        )
        self._actor_cycle = build_readiness_cycle(
            self.player,
            self.encounter,
            rng=self._rng,
            force_player_last=player_loses_initiative,
        )
        if forced_enemy_initiative:
            self.tile.trap_forced_initiative = False
        if self.boss:
            for member in self.encounter.living_members:
                member.enemy.boss = True
        self._sync_actor_aliases()
        footpad.arm_surprise(self.player, has_initiative=self.attacker == self.player)
        promotion_kits.combat_state(self.player)["has_initiative"] = self.attacker == self.player
        self._current_actor_turn_id = self._actor_cycle.start_current_turn()
        self.available_actions = self._available_actions()

        self._event_bus.emit(
            create_combat_event(
                EventType.COMBAT_START,
                actor=self.player,
                target=self.encounter.primary_enemy,
                initiative=self.attacker == self.player,
                boss=self.boss,
                encounter_id=self.encounter.encounter_id,
                enemies=self.encounter.roster_summary(),
            )
        )

        self.logger.start_battle(
            self.player,
            self.encounter.primary_enemy,
            initiative=self.attacker == self.player,
            boss=self.boss,
            encounter=self.encounter,
            ready_at=self.current_readiness,
            round_number=self.round_number,
            actor_turn_id=self._current_actor_turn_id,
        )

        self._event_bus.emit(
            create_combat_event(
                EventType.ROUND_START,
                actor=self.attacker,
                target=self.defender,
                encounter_id=self.encounter.encounter_id,
                actor_id=self.current_actor_id,
                round=self.round_number,
                actor_turn_id=self._current_actor_turn_id,
            )
        )
        self._event_bus.emit(
            create_combat_event(
                EventType.TURN_START,
                actor=self.attacker,
                target=self.defender,
                encounter_id=self.encounter.encounter_id,
                actor_id=self.current_actor_id,
                round=self.round_number,
                actor_turn_id=self._current_actor_turn_id,
            )
        )

        paladin.advance_encounter(self.player)
        paladin.clear_transient_marks(self.player)
        for member in self.encounter.members:
            enemy = member.enemy
            if hasattr(self.player, "record_bestiary_encounter"):
                self.player.record_bestiary_encounter(
                    enemy,
                    getattr(enemy, "enemy_typ", None),
                )
            debuff_text = bard.apply_enemy_opening_debuffs(self.player, enemy)
            if debuff_text:
                self.logger.log_event(
                    "Bard Song",
                    self.player,
                    target=enemy,
                    outcome=debuff_text,
                    actor_id=PLAYER_ACTOR_ID,
                    target_id=member.combatant_id,
                    opportunity_actor_id=self.current_actor_id,
                    ready_at=self.current_readiness,
                    round_number=self.round_number,
                    actor_turn_id=self._current_actor_turn_id,
                )
        return self.attacker, self.defender

    def battle_continues(self) -> bool:
        """Return True while both combatants are alive and nobody fled."""
        return self.player.is_alive() and bool(self.encounter.living_members) and not self.flee
