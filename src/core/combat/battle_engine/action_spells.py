"""Spell and spell-adjacent actions for the battle engine."""

from __future__ import annotations

import inspect
from copy import deepcopy
from typing import TYPE_CHECKING

from src.core.randomness import gameplay_random as random

from ... import items
from ...classes import (
    astromancer,
    mage_mechanics,
    promotion_kits,
    wizard,
)
from ...events.event_bus import EventType, create_combat_event
from ..combat_result import CombatResult

if TYPE_CHECKING:
    pass


STOLEN_SCROLL_CHOICE_PREFIX = "__scroll__:"


class SpellActionMixin:
    """Resolve spells, stolen scrolls, runes, and spell theft."""

    def _execute_spell(self, choice: str | None) -> str:
        """Cast a spell. Handles silence check."""
        fractures = getattr(self.attacker, "fractures", {})
        if (fractures.get("Ribs") or fractures.get("Exoskeleton")) and random.random() < 0.25:
            return f"{self.attacker.name}'s fractured body disrupts the spell.\n"
        if self.attacker.abilities_suppressed():
            reason = (
                "the anti-magic field"
                if getattr(self.attacker, "anti_magic_active", False)
                else "silence"
            )
            return f"{self.attacker.name} cannot cast spells because of {reason}!\n"

        if choice and choice.startswith(STOLEN_SCROLL_CHOICE_PREFIX):
            return self._execute_stolen_scroll_spell(choice)

        if not choice or choice not in self.attacker.spellbook.get("Spells", {}):
            return f"{self.attacker.name} fumbles the spell.\n"

        spell = self.attacker.spellbook["Spells"][choice]
        from ... import persistent_afflictions as afflictions

        if afflictions.spell_delay(self.attacker):
            pending = getattr(self.attacker, "_dysarthria_pending_spell", None)
            if pending != choice:
                self.attacker._dysarthria_pending_spell = choice
                return f"{self.attacker.name} struggles to pronounce {choice} and begins casting.\n"
            self.attacker._dysarthria_pending_spell = None
        if self.attacker.mana.current < mage_mechanics.spell_mana_cost(
            self.attacker,
            spell,
        ):
            return f"{self.attacker.name} does not have enough mana to cast {choice}!\n"

        stolen_payoff_message = promotion_kits.prepare_stolen_charge_payoff(
            self.attacker,
            "Cast Spell",
            spell,
        )

        threaded_validation = True
        if choice == "Rewind" and getattr(self.attacker, "_rewind_snapshot", None) is None:
            threaded_validation = False
        elif choice == "Wormhole":
            candidates = [
                candidate
                for name, candidate in self.attacker.spellbook.get("Spells", {}).items()
                if name != "Wormhole" and getattr(candidate, "subtyp", "") != "Support"
            ]
            threaded_validation = bool(
                candidates
                and self.attacker.mana.current
                >= mage_mechanics.spell_mana_cost(self.attacker, spell)
                + int(getattr(candidates[0], "cost", 0) or 0)
            )
        if threaded_validation:
            _thread_count, threaded_message = astromancer.begin_threaded_spell(
                self.attacker,
                spell,
            )
        else:
            _thread_count, threaded_message = 0, ""

        self._event_bus.emit(
            create_combat_event(
                EventType.SPELL_CAST,
                actor=self.attacker,
                target=self.defender,
                spell_name=choice,
                ability_name=choice,
                source="spell",
            )
        )

        defender_was_alive = self.defender.is_alive()
        message = f"{self.attacker.name} casts {choice}.\n{threaded_message}{stolen_payoff_message}"
        try:
            cast_result = self._cast_spell_with_context(
                spell,
                self.attacker,
                self.defender,
            )
        finally:
            astromancer.clear_threaded_spell(self.attacker)
        if isinstance(cast_result, CombatResult):
            self._last_combat_result = deepcopy(cast_result)
        else:
            recorded_result = getattr(spell, "result", None)
            if (
                isinstance(recorded_result, CombatResult)
                and recorded_result.actor is self.attacker
                and recorded_result.target is self.defender
            ):
                self._last_combat_result = deepcopy(recorded_result)
        message += str(cast_result)
        if choice == "Volcano" and self.attacker == self.player:
            message += astromancer.tephra_splash(
                self.player,
                self.defender,
                self.encounter,
            )
        if self.attacker != self.player:
            message += astromancer.learn_witnessed_spell(
                self.player,
                spell,
                cast_result,
            )
        if defender_was_alive and not self.defender.is_alive():
            self.defender._killed_by_ability = choice
            if choice == "Desoul" and "Death Becomes Us" in self.attacker.spellbook.get(
                "Skills", {}
            ):
                self.attacker.shadow_dungeon_darkness_steps = max(
                    100,
                    int(getattr(self.attacker, "shadow_dungeon_darkness_steps", 0) or 0),
                )
                message += "Death Becomes Us throws the dungeon into darkness.\n"
        if self.attacker == self.player:
            from ...classes import healer

            if "Holy" in {
                str(getattr(spell, "subtyp", "")),
                str(getattr(spell, "school", "")),
            }:
                message += healer.flash_blindness(
                    self.player,
                    [member.enemy for member in self.encounter.living_members],
                )
            if (
                choice in {"Turn Undead", "TurnUndead", "Turn Undead 2", "TurnUndead2"}
                and defender_was_alive
                and not self.defender.is_alive()
                and "Pious Bounty" in self.player.spellbook.get("Skills", {})
            ):
                self.defender._pious_bounty_gold = True
            message += wizard.process_cast(self.player, spell, self.defender)
            message += astromancer.record_thread_action(
                self.player,
                choice,
                successful=astromancer.spell_resolution_succeeded(cast_result, spell),
            )
            if not self.defender.is_alive():
                message += self._record_player_natural_spell_kill(spell)
            if astromancer.is_astromancer(self.player) and astromancer.sign_for_spell(spell):
                astromancer.advance_constellation(self.player)
        return message

    def _execute_stolen_scroll_spell(self, choice: str) -> str:
        """Cast an inscribed stolen-spell scroll selected from the Spells menu."""
        scroll_name = choice.removeprefix(STOLEN_SCROLL_CHOICE_PREFIX)
        if not scroll_name:
            return f"{self.attacker.name} fumbles the spell.\n"
        if scroll_name not in self.attacker.inventory or not self.attacker.inventory[scroll_name]:
            return f"{self.attacker.name} can't find {scroll_name}.\n"

        scroll = self.attacker.inventory[scroll_name][0]
        if not isinstance(scroll, items.InscribedSpellScroll):
            return f"{scroll_name} is not a stolen spell scroll.\n"

        payoff_message = promotion_kits.prepare_stolen_charge_payoff(
            self.attacker,
            "Cast Spell",
            scroll.spell,
        )

        self._event_bus.emit(
            create_combat_event(
                EventType.ITEM_USE,
                actor=self.attacker,
                target=self.defender,
                item_name=scroll.name,
                item_type=getattr(scroll, "typ", ""),
                item_subtype=getattr(scroll, "subtyp", ""),
                source="stolen_spell_scroll",
            )
        )

        message = payoff_message + str(scroll.use(self.attacker, target=self.defender))
        recorded_result = getattr(scroll.spell, "result", None)
        if (
            isinstance(recorded_result, CombatResult)
            and recorded_result.actor is self.attacker
            and recorded_result.target is self.defender
        ):
            self._last_combat_result = deepcopy(recorded_result)
        if self.attacker == self.player:
            message += promotion_kits.gain_stolen_charge(self.player, "stolen spell scroll")
        return message

    def _record_player_natural_spell_kill(self, spell: object) -> str:
        if not astromancer.has_rune_system(self.player):
            return ""
        gained, sign, _chance = astromancer.maybe_award_rune(
            self.player,
            self.defender,
            spell,
        )
        if gained and sign:
            return f"{self.player.name} claims an {sign} rune.\n"
        return ""

    def _cast_spell_with_context(self, spell: object, caster: object, target: object) -> object:
        """Cast a spell, passing this engine only when the spell accepts it."""
        cast = getattr(spell, "cast")
        try:
            signature = inspect.signature(cast)
        except (TypeError, ValueError):
            return cast(caster, target=target)
        accepts_engine = any(
            parameter.kind == inspect.Parameter.VAR_KEYWORD or parameter.name == "battle_engine"
            for parameter in signature.parameters.values()
        )
        if accepts_engine:
            return cast(caster, target=target, battle_engine=self)
        return cast(caster, target=target)

    def _execute_runic_boost(self, choice: str | None) -> str:
        """Spend a rune to empower and cast a matching natural spell."""
        if self.attacker.abilities_suppressed():
            reason = (
                "the anti-magic field"
                if getattr(self.attacker, "anti_magic_active", False)
                else "silence"
            )
            return f"{self.attacker.name} cannot cast spells because of {reason}!\n"

        if self.attacker != self.player or not astromancer.has_rune_system(self.player):
            return f"{self.attacker.name} cannot shape runes.\n"

        if not choice or choice not in self.player.spellbook.get("Spells", {}):
            return f"{self.player.name} fumbles the rune pattern.\n"

        spell = self.player.spellbook["Spells"][choice]
        sign = astromancer.sign_for_spell(spell)
        if not sign:
            return f"{choice} cannot be empowered by the current rune lore.\n"
        if self.player.mana.current < mage_mechanics.spell_mana_cost(
            self.player,
            spell,
        ):
            return f"{self.player.name} does not have enough mana to cast {choice}!\n"
        if not astromancer.consume_rune(self.player, sign):
            return f"{self.player.name} has no {sign} runes.\n"

        _thread_count, threaded_message = astromancer.begin_threaded_spell(
            self.player,
            spell,
        )

        floor = astromancer.runic_boost_floor(self.player, sign)
        prior_floor = getattr(self.player, "_runic_boost_floor", None)
        self.player._runic_boost_floor = floor
        try:
            message = (
                f"{self.player.name} spends one {sign} rune to boost {choice}.\n{threaded_message}"
            )
            message += str(spell.cast(self.player, target=self.defender))
        finally:
            astromancer.clear_threaded_spell(self.player)
            if prior_floor is None:
                try:
                    delattr(self.player, "_runic_boost_floor")
                except AttributeError:
                    pass
            else:
                self.player._runic_boost_floor = prior_floor

        message += wizard.process_cast(self.player, spell, self.defender)
        message += astromancer.record_thread_action(
            self.player,
            "Runic Boost",
            successful=True,
        )
        if not self.defender.is_alive():
            message += self._record_player_natural_spell_kill(spell)
        if astromancer.is_astromancer(self.player):
            astromancer.advance_constellation(self.player)
        return message

    def _execute_steal_as_well(self, choice: str | None) -> str:
        """Cast a selected spell or stolen-spell scroll, then steal if damage lands."""
        if self.attacker != self.player:
            return f"{self.attacker.name} cannot use Steal As Well.\n"
        if self.attacker.abilities_suppressed():
            reason = (
                "the anti-magic field"
                if getattr(self.attacker, "anti_magic_active", False)
                else "silence"
            )
            return f"{self.attacker.name} cannot use Steal As Well because of {reason}!\n"
        if not choice:
            return f"{self.attacker.name} fumbles the spell theft.\n"

        from ... import abilities, items

        message = f"{self.attacker.name} weaves theft into {choice}.\n"
        before_hp = self.defender.health.current
        stolen_scroll = False
        if choice in self.attacker.spellbook.get("Spells", {}):
            spell = self.attacker.spellbook["Spells"][choice]
            if self.attacker.mana.current < getattr(spell, "cost", 0):
                return f"{self.attacker.name} does not have enough mana to cast {choice}!\n"
        elif choice in self.attacker.inventory and self.attacker.inventory[choice]:
            scroll = self.attacker.inventory[choice][0]
            if not isinstance(scroll, items.InscribedSpellScroll):
                return f"{choice} is not a stolen spell scroll.\n"
            spell = scroll.spell
            stolen_scroll = True
        else:
            return f"{self.attacker.name} cannot find {choice}.\n"

        message += promotion_kits.prepare_stolen_charge_payoff(
            self.attacker,
            "Steal As Well",
            spell,
        )
        if stolen_scroll:
            cast_result = scroll.use(self.attacker, target=self.defender)
        else:
            cast_result = self._cast_spell_with_context(
                spell,
                self.attacker,
                self.defender,
            )
        message += str(cast_result)
        if isinstance(cast_result, CombatResult):
            self._last_combat_result = deepcopy(cast_result)
        else:
            recorded_result = getattr(spell, "result", None)
            if (
                isinstance(recorded_result, CombatResult)
                and recorded_result.actor is self.attacker
                and recorded_result.target is self.defender
            ):
                self._last_combat_result = deepcopy(recorded_result)
        if stolen_scroll:
            message += promotion_kits.gain_stolen_charge(
                self.player,
                "stolen spell scroll",
            )

        if before_hp > self.defender.health.current:
            steal_skill = (
                self.attacker.spellbook.get("Skills", {}).get("Steal") or abilities.Steal()
            )
            message += str(steal_skill.use(self.attacker, target=self.defender))
        else:
            message += "The spell fails to open a path for theft.\n"
        return message

    @staticmethod
    @staticmethod
    def _skill_uses_resolve(skill: object) -> bool:
        if getattr(skill, "resource_type", None) == "Resolve":
            return True
        skill_name = str(getattr(skill, "name", "") or "")
        resolve_names = {entry["name"] for entry in promotion_kits.RESOLVE_SPEND_ABILITIES}
        surge_names = {entry["name"] for entry in promotion_kits.RESOLVE_SURGES}
        return skill_name in resolve_names or skill_name in surge_names
