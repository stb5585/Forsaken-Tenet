"""
Combat Analytics Module

This module provides tools for analyzing combat balance, simulating battles,
and generating reports for game balancing purposes.
"""

from __future__ import annotations

import copy
import json
import logging
import random as stdlib_random
import statistics
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING

from src.core.randomness import RandomSource, using_random_source

logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    from collections.abc import Callable

    from src.core.character import Character
    from src.core.player import Player


def _combat_level(ch: object) -> int:
    try:
        lvl = getattr(ch, "level", 1)
    except (AttributeError, RuntimeError, TypeError):
        return 1
    try:
        nested_level = getattr(lvl, "level")
    except AttributeError:
        nested_level = None
    except (AttributeError, RuntimeError, TypeError):
        return 1
    else:
        try:
            return int(nested_level)
        except (TypeError, ValueError):
            return 1
    try:
        return int(lvl)
    except (TypeError, ValueError):
        return 1


_CLASS_KIT_TERMS = (
    "aerial tempo",
    "arcane larceny",
    "aegis weave",
    "aspect harmony",
    "backlash",
    "battle scars",
    "blade charge",
    "bloodied momentum",
    "case journal",
    "cheat death",
    "conduit",
    "enchanted assault",
    "foundation",
    "spellbind",
    "weave",
    "conviction",
    "corruption",
    "crescendo",
    "death mark",
    "devotion",
    "divine intervention",
    "dragon essence",
    "eclipse",
    "encore",
    "foresight",
    "fortune",
    "harmony bonus",
    "ki",
    "loaded dice",
    "misfortune",
    "oath",
    "ordered blessings",
    "prayer",
    "repertoire",
    "revelation",
    "resolve",
    "shared recovery",
    "stolen charge",
    "threaded cast",
    "totem resonance",
    "umbral debt",
    "vow affirmation",
)

_CLASS_KIT_EVENT_KEYWORDS = {
    "meter_gain": ("gains", "stores", "rises", "represents", "bond grows"),
    "meter_cap": ("capped", "cap"),
    "meter_spend": ("spends", "cashes in", "releases"),
    "preservation": ("preserves", "preservation"),
    "cleanup": ("clears", "fades", "expires"),
    "payoff": ("payoff", "follow-through", "burst", "coda", "surge", "force", "empowers"),
}

_ACTION_ECONOMY_KEYWORDS = {
    "totem_output": ("totem pulses", "totem surge", "force "),
    "song_coda": ("coda", "encore"),
    "summon_output": ("summon", "invokes", "conduit command"),
    "companion_output": ("companion", "pack strike", "guard partner", "harry prey", "mend wounds"),
    "multi_output": ("doublecast", "fourfold surge", "threaded cast"),
    "passive_echo": ("shared recovery", "echo", "intervention", "counter", "riposte"),
}


def _merge_counts(target: dict[str, int], source: dict[str, int]) -> None:
    for key, value in source.items():
        target[key] += int(value or 0)


def _classify_class_kit_text(value: object) -> dict[str, int]:
    text = str(value or "").lower()
    if not text or not any(term in text for term in _CLASS_KIT_TERMS):
        return {}
    counts: dict[str, int] = {}
    for bucket, needles in _CLASS_KIT_EVENT_KEYWORDS.items():
        if any(needle in text for needle in needles):
            counts[bucket] = counts.get(bucket, 0) + 1
    if not counts:
        counts["mention"] = 1
    return counts


def _classify_action_economy_text(value: object) -> dict[str, int]:
    text = str(value or "").lower()
    if not text:
        return {}
    counts: dict[str, int] = {}
    for bucket, needles in _ACTION_ECONOMY_KEYWORDS.items():
        if any(needle in text for needle in needles):
            counts[bucket] = counts.get(bucket, 0) + 1
    return counts


@dataclass
class CombatStats:
    """Statistics from a single combat encounter."""

    winner: str
    loser: str
    winner_class: str
    loser_class: str
    winner_level: int
    loser_level: int
    turns: int
    winner_hp_remaining: int
    winner_hp_max: int
    total_damage_dealt: int
    total_damage_taken: int
    abilities_used: dict[str, int] = field(default_factory=dict)
    status_effects_applied: dict[str, int] = field(default_factory=dict)
    class_kit_events: dict[str, int] = field(default_factory=dict)
    action_economy_events: dict[str, int] = field(default_factory=dict)
    critical_hits: int = 0
    misses: int = 0
    rounds: int = 0
    actor_turns: int = 0
    roster: tuple[str, ...] = ()
    enemy_hp_remaining: dict[str, int] = field(default_factory=dict)
    player_mana_remaining: int = 0
    player_hp_remaining: int = 0
    player_hp_max: int = 0
    resolutions: tuple[str | None, ...] = ()
    consumables_used: int = 0
    damage_by_combatant: dict[str, int] = field(default_factory=dict)
    reward_experience: int = 0
    reward_gold: int = 0
    action_sequence: tuple[str, ...] = ()
    repeated_non_progress_actions: int = 0
    max_non_progress_streak: int = 0
    invalid_intents: int = 0
    max_turns_reached: bool = False
    timeline_trace: tuple[TimelineTurnDiagnostic, ...] = ()
    final_readiness: dict[str, float] = field(default_factory=dict)
    readiness_is_monotonic: bool = True
    max_consecutive_actor_turns: int = 0

    @property
    def hp_remaining_percent(self) -> float:
        """Percentage of HP remaining for winner."""
        if self.winner_hp_max == 0:
            return 0.0
        return (self.winner_hp_remaining / self.winner_hp_max) * 100

    @property
    def was_close(self) -> bool:
        """Was this a close fight? (winner had < 30% HP)"""
        return self.hp_remaining_percent < 30


@dataclass(frozen=True)
class TimelineTurnDiagnostic:
    """One scheduled actor opportunity captured by a combat simulation."""

    actor_id: str
    ready_at: float
    round_number: int
    actor_turn_id: int
    can_act: bool
    action: str | None = None
    committed: bool | None = None
    forced: bool = False

    def export_payload(self) -> dict[str, object]:
        """Return a JSON-compatible diagnostic record."""
        return {
            "actor_id": self.actor_id,
            "ready_at": self.ready_at,
            "round_number": self.round_number,
            "actor_turn_id": self.actor_turn_id,
            "can_act": self.can_act,
            "action": self.action,
            "committed": self.committed,
            "forced": self.forced,
        }


@dataclass
class BalanceReport:
    """
    Comprehensive report on combat balance from multiple simulations.
    """

    total_battles: int
    results: list[CombatStats]

    def __post_init__(self):
        self._win_rates: dict[str, float] = {}
        self._calculate_metrics()

    def _calculate_metrics(self) -> None:
        """Pre-calculate common metrics."""
        if not self.results:
            return

        # Win rates by class
        wins_by_class = defaultdict(int)
        total_by_class = defaultdict(int)

        for result in self.results:
            wins_by_class[result.winner_class] += 1
            total_by_class[result.winner_class] += 1
            total_by_class[result.loser_class] += 1

        for cls, wins in wins_by_class.items():
            total = total_by_class[cls]
            self._win_rates[cls] = (wins / total) * 100 if total > 0 else 0

    @property
    def win_rates(self) -> dict[str, float]:
        """Win rate percentage by class."""
        return self._win_rates

    @property
    def average_turns(self) -> float:
        """Average number of turns per battle."""
        if not self.results:
            return 0.0
        return statistics.mean(r.turns for r in self.results)

    @property
    def median_turns(self) -> float:
        """Median number of turns per battle."""
        if not self.results:
            return 0.0
        return statistics.median(r.turns for r in self.results)

    @property
    def close_fight_rate(self) -> float:
        """Percentage of fights that were close (< 30% HP remaining)."""
        if not self.results:
            return 0.0
        close_fights = sum(1 for r in self.results if r.was_close)
        return (close_fights / len(self.results)) * 100

    @property
    def stomp_rate(self) -> float:
        """Percentage of fights that were stomps (> 90% HP remaining)."""
        if not self.results:
            return 0.0
        stomps = sum(1 for r in self.results if r.hp_remaining_percent > 90)
        return (stomps / len(self.results)) * 100

    def get_ability_usage(self) -> dict[str, int]:
        """Get total usage count for each ability across all battles."""
        usage = defaultdict(int)
        for result in self.results:
            for ability, count in result.abilities_used.items():
                usage[ability] += count
        return dict(usage)

    def get_most_used_abilities(self, limit: int = 10) -> list[tuple[str, int]]:
        """Get the most frequently used abilities."""
        usage = self.get_ability_usage()
        return sorted(usage.items(), key=lambda x: x[1], reverse=True)[:limit]

    def get_status_effect_frequency(self) -> dict[str, int]:
        """Get frequency of status effects applied across all battles."""
        freq = defaultdict(int)
        for result in self.results:
            for effect, count in result.status_effects_applied.items():
                freq[effect] += count
        return dict(freq)

    def get_class_kit_events(self) -> dict[str, int]:
        """Get aggregate class-kit event counts across all battles."""
        events = defaultdict(int)
        for result in self.results:
            for event_name, count in result.class_kit_events.items():
                events[event_name] += count
        return dict(events)

    def get_action_economy_events(self) -> dict[str, int]:
        """Get aggregate bonus-output/action-economy counts across all battles."""
        events = defaultdict(int)
        for result in self.results:
            for event_name, count in result.action_economy_events.items():
                events[event_name] += count
        return dict(events)

    def get_timeline_diagnostics(self) -> dict[str, int]:
        """Return aggregate readiness-schedule diagnostics across simulations."""
        return {
            "traced_actor_turns": sum(len(result.timeline_trace) for result in self.results),
            "readiness_monotonic_battles": sum(
                result.readiness_is_monotonic for result in self.results
            ),
            "max_consecutive_actor_turns": max(
                (result.max_consecutive_actor_turns for result in self.results),
                default=0,
            ),
        }

    def export_payload(self) -> dict:
        """Export report metrics and raw combat stats for tooling."""
        return {
            "total_battles": self.total_battles,
            "average_turns": self.average_turns,
            "median_turns": self.median_turns,
            "close_fight_rate": self.close_fight_rate,
            "stomp_rate": self.stomp_rate,
            "win_rates": dict(self.win_rates),
            "ability_usage": self.get_ability_usage(),
            "status_effect_frequency": self.get_status_effect_frequency(),
            "class_kit_events": self.get_class_kit_events(),
            "action_economy_events": self.get_action_economy_events(),
            "timeline_diagnostics": self.get_timeline_diagnostics(),
            "outliers": self.identify_outliers(),
            "results": [self._result_payload(result) for result in self.results],
        }

    @staticmethod
    def _result_payload(result: CombatStats) -> dict[str, object]:
        """Convert nested simulation diagnostics to JSON-compatible values."""
        payload = result.__dict__.copy()
        payload["timeline_trace"] = [
            diagnostic.export_payload() for diagnostic in result.timeline_trace
        ]
        return payload

    def summary_payload(self, *, ability_limit: int = 5, status_limit: int = 5) -> dict:
        """Export compact report metrics for dashboards and quick balance checks."""
        status_frequency = self.get_status_effect_frequency()
        return {
            "total_battles": self.total_battles,
            "average_turns": self.average_turns,
            "median_turns": self.median_turns,
            "close_fight_rate": self.close_fight_rate,
            "stomp_rate": self.stomp_rate,
            "win_rates": dict(self.win_rates),
            "most_used_abilities": self.get_most_used_abilities(max(0, ability_limit)),
            "most_common_status_effects": sorted(
                status_frequency.items(),
                key=lambda item: item[1],
                reverse=True,
            )[: max(0, status_limit)],
            "class_kit_events": self.get_class_kit_events(),
            "action_economy_events": self.get_action_economy_events(),
            "timeline_diagnostics": self.get_timeline_diagnostics(),
            "outliers": self.identify_outliers(),
        }

    def export_json(self, *, indent: int = 2) -> str:
        """Export the balance report as JSON text."""
        return json.dumps(self.export_payload(), indent=indent, sort_keys=True)

    def export_json_file(self, path: str | Path, *, indent: int = 2) -> Path:
        """Write the balance report JSON to disk and return its path."""
        output_path = Path(path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(self.export_json(indent=indent), encoding="utf-8")
        return output_path

    def identify_outliers(self, threshold: float = 2.0) -> dict[str, list]:
        """
        Identify statistical outliers in the data.

        Args:
            threshold: Number of standard deviations to consider an outlier

        Returns:
            Dictionary with 'overpowered' and 'underpowered' classes
        """
        if len(self._win_rates) < 2:
            return {"overpowered": [], "underpowered": []}

        mean_wr = statistics.mean(self._win_rates.values())
        stdev_wr = statistics.stdev(self._win_rates.values())

        overpowered = []
        underpowered = []

        for cls, win_rate in self._win_rates.items():
            z_score = (win_rate - mean_wr) / stdev_wr if stdev_wr > 0 else 0

            if z_score > threshold:
                overpowered.append((cls, win_rate, z_score))
            elif z_score < -threshold:
                underpowered.append((cls, win_rate, z_score))

        return {
            "overpowered": sorted(overpowered, key=lambda x: x[2], reverse=True),
            "underpowered": sorted(underpowered, key=lambda x: x[2]),
        }

    def generate_summary(self) -> str:
        """Generate a text summary of the balance report."""
        lines = [
            "=" * 60,
            "COMBAT BALANCE REPORT",
            "=" * 60,
            f"Total Battles: {self.total_battles}",
            f"Average Turns: {self.average_turns:.2f}",
            f"Median Turns: {self.median_turns:.2f}",
            f"Close Fight Rate: {self.close_fight_rate:.1f}%",
            f"Stomp Rate: {self.stomp_rate:.1f}%",
            "",
            "Win Rates by Class:",
            "-" * 40,
        ]

        for cls, win_rate in sorted(self._win_rates.items(), key=lambda x: x[1], reverse=True):
            lines.append(f"  {cls:20s} {win_rate:6.2f}%")

        outliers = self.identify_outliers()

        if outliers["overpowered"]:
            lines.extend(
                [
                    "",
                    "⚠️  Overpowered Classes:",
                    "-" * 40,
                ]
            )
            for cls, win_rate, z_score in outliers["overpowered"]:
                lines.append(f"  {cls:20s} {win_rate:6.2f}% (z={z_score:.2f})")

        if outliers["underpowered"]:
            lines.extend(
                [
                    "",
                    "⚠️  Underpowered Classes:",
                    "-" * 40,
                ]
            )
            for cls, win_rate, z_score in outliers["underpowered"]:
                lines.append(f"  {cls:20s} {win_rate:6.2f}% (z={z_score:.2f})")

        lines.extend(
            [
                "",
                "Most Used Abilities:",
                "-" * 40,
            ]
        )

        for ability, count in self.get_most_used_abilities(5):
            lines.append(f"  {ability:30s} {count:5d} uses")

        lines.append("=" * 60)

        return "\n".join(lines)


class CombatSimulator:
    """
    Simulates combat encounters for balance testing.

    This is a simplified simulator that doesn't require the full game infrastructure.
    """

    def __init__(self):
        self.results: list[CombatStats] = []

    def simulate_battle(
        self,
        char1: Player,
        char2: Character | None = None,
        max_turns: int = 200,
        *,
        encounter=None,
        seed: int | None = None,
        rng: RandomSource | None = None,
        char1_policy: Callable | None = None,
        char2_policy: Callable | None = None,
        include_flee: bool = False,
    ) -> CombatStats:
        """Simulate a battle with an isolated deterministic random source."""
        if seed is not None and rng is not None:
            raise ValueError("seed and rng are mutually exclusive")
        source = rng or stdlib_random.Random(seed)
        with using_random_source(source):
            return self._simulate_battle(
                char1,
                char2,
                max_turns,
                encounter=encounter,
                rng=source,
                char1_policy=char1_policy,
                char2_policy=char2_policy,
                include_flee=include_flee,
            )

    def _simulate_battle(
        self,
        char1: Player,
        char2: Character | None = None,
        max_turns: int = 200,
        *,
        encounter=None,
        rng: RandomSource,
        char1_policy: Callable | None = None,
        char2_policy: Callable | None = None,
        include_flee: bool = False,
    ) -> CombatStats:
        """
        Simulate a single battle using the real BattleEngine.

        Args:
            char1: Player-side combatant (BattleEngine expects a Player)
            char2: Legacy singleton enemy-side combatant.
            encounter: Optional runtime hostile roster.
            max_turns: Maximum turns before declaring a draw
            rng: Context-local random source used for every gameplay draw.
            char1_policy: Optional policy(engine) -> ActionIntent.
            char2_policy: Optional policy(engine) -> ActionIntent.
            include_flee: If True, allow Flee to be selected by policies

        Returns:
            Combat statistics from the battle
        """
        from src.core.combat import ActionIntent, CombatEncounter
        from src.core.combat.battle_engine import BattleEngine
        from src.core.events.event_bus import EventType, get_event_bus, reset_event_bus

        using_legacy_enemy = encounter is None
        if (char2 is None) == (encounter is None):
            raise ValueError("Supply exactly one of char2 or encounter.")
        if encounter is None:
            assert char2 is not None
            encounter = CombatEncounter.singleton(char2)
        elif not isinstance(encounter, CombatEncounter):
            raise TypeError("encounter must be a CombatEncounter.")
        primary_enemy = encounter.primary_enemy
        paired_policy = len(encounter.members) > 1

        # Isolate global event bus per simulation to avoid cross-test pollution.
        reset_event_bus()
        event_bus = get_event_bus()

        abilities_used: dict[str, int] = defaultdict(int)
        status_applied: dict[str, int] = defaultdict(int)
        crits = 0
        misses = 0
        damage_by_actor: dict[str, int] = defaultdict(int)
        damage_by_combatant: dict[str, int] = defaultdict(int)
        class_kit_events: dict[str, int] = defaultdict(int)
        action_economy_events: dict[str, int] = defaultdict(int)
        consumables_used = 0
        action_sequence: list[str] = []
        timeline_trace: list[TimelineTurnDiagnostic] = []
        readiness_is_monotonic = True
        previous_ready_at: float | None = None
        previous_actor_id: str | None = None
        consecutive_actor_turns = 0
        max_consecutive_actor_turns = 0
        repeated_non_progress_actions = 0
        max_non_progress_streak = 0
        non_progress_streak = 0
        prior_non_progress_action = None
        invalid_intents = 0
        member_labels = {member.combatant_id: member.display_label for member in encounter.members}

        def record_analytics_text(value: object) -> None:
            _merge_counts(class_kit_events, _classify_class_kit_text(value))
            _merge_counts(action_economy_events, _classify_action_economy_text(value))

        def record_action_selection(action: object, choice: object = None) -> None:
            nonlocal consumables_used
            action_name = getattr(action, "action", action)
            if action_name == "Use Item":
                consumables_used += 1
            record_analytics_text(action)
            if choice:
                record_analytics_text(choice)

        def on_event(ev) -> None:
            nonlocal crits, misses
            try:
                if ev.type == EventType.SPELL_CAST:
                    nm = ev.data.get("spell_name")
                    if nm:
                        abilities_used[str(nm)] += 1
                        record_analytics_text(nm)
                elif ev.type == EventType.SKILL_USE:
                    nm = ev.data.get("skill_name")
                    if nm:
                        abilities_used[str(nm)] += 1
                        record_analytics_text(nm)
                elif ev.type == EventType.ATTACK:
                    abilities_used["Attack"] += 1
                elif ev.type == EventType.STATUS_APPLIED:
                    nm = ev.data.get("status_name")
                    if nm:
                        status_applied[str(nm)] += 1
                elif ev.type == EventType.CRITICAL_HIT:
                    crits += 1
                elif ev.type == EventType.MISS:
                    misses += 1
                elif ev.type == EventType.DAMAGE_DEALT:
                    actor = getattr(ev, "actor", None) or ev.data.get("actor")
                    dmg = int(ev.data.get("damage", 0) or 0)
                    if actor and dmg > 0:
                        damage_by_actor[str(actor)] += dmg
                    target_id = ev.data.get("target_combatant_id") or ev.data.get("target_id")
                    if target_id in member_labels and dmg > 0:
                        damage_by_combatant[member_labels[target_id]] += dmg
            except (AttributeError, KeyError, TypeError, ValueError) as exc:
                logger.warning("Ignoring malformed simulator analytics event: %s", exc)

        for et in [
            EventType.SPELL_CAST,
            EventType.SKILL_USE,
            EventType.ATTACK,
            EventType.STATUS_APPLIED,
            EventType.CRITICAL_HIT,
            EventType.MISS,
            EventType.DAMAGE_DEALT,
        ]:
            event_bus.subscribe(et, on_event)

        class _SimTile:
            def __init__(self):
                self.enemy = primary_enemy
                self.defeated = False

            def available_actions(self, _player):
                actions = ["Attack", "Cast Spell", "Use Skill", "Defend", "Use Item"]
                if include_flee:
                    actions.append("Flee")
                if getattr(char1, "summons", None):
                    actions.append("Summon")
                    actions.append("Recall")
                # Totem/Transform are implemented as top-level actions in BattleEngine.
                if "Totem" in getattr(char1, "spellbook", {}).get("Skills", {}):
                    actions.append("Totem")
                if "Transform" in getattr(char1, "spellbook", {}).get("Skills", {}):
                    actions.append("Transform")
                    actions.append("Untransform")
                return actions

            def __str__(self) -> str:
                return "SimTile"

        tile = _SimTile()
        if using_legacy_enemy:
            engine = BattleEngine(
                player=char1,
                enemy=primary_enemy,
                tile=tile,
                rng=rng,
            )
        else:
            engine = BattleEngine(
                player=char1,
                encounter=encounter,
                tile=tile,
                rng=rng,
            )
        engine.start_battle()

        def default_policy(_engine: BattleEngine):
            attacker = _engine.attacker
            defender = _engine.defender
            if attacker is None or defender is None:
                return "Attack", None

            # Meta-actions (summons/totems) first: these are major class-defining levers.
            if (
                attacker == char1
                and "Summon" in _engine.available_actions
                and getattr(char1, "summons", None)
                and not getattr(_engine, "summon_active", False)
            ):
                choice = next(iter(char1.summons.keys()))
                return "Summon", choice
            if (
                attacker == char1
                and "Totem" in _engine.available_actions
                and not (
                    attacker.magic_effects.get("Totem") and attacker.magic_effects["Totem"].active
                )
            ):
                return "Totem", "Earth"

            def _is_combat_offense(ab) -> bool:
                """
                Best-effort classifier for "worth spending a turn on" actions.

                The base game has many non-damaging combat-legal abilities
                (buffs, utility, resource conversion). For analytics we want a
                policy that doesn't soft-lock on e.g. Mana Tap spam.
                """
                if ab is None or getattr(ab, "passive", False):
                    return False
                if getattr(ab, "combat", True) is False:
                    return False
                nm = str(getattr(ab, "name", "") or "")
                if nm in {"Inspect", "Reveal", "Teleport", "Sanctuary"}:
                    return False
                typ = str(getattr(ab, "typ", "") or "")
                sub = str(getattr(ab, "subtyp", "") or "")
                if typ == "Movement" or sub in {"Truth", "Movement"}:
                    return False
                # Treat explicit heals/support as non-offensive for selection.
                if sub in {"Heal", "Support"}:
                    return False

                # Weapon-based skills are almost always offensively useful.
                if bool(getattr(ab, "weapon", False)):
                    return True

                # Data-driven abilities expose effect objects; classify those.
                effects = getattr(ab, "_effects", None)
                if effects:
                    non_offense = {
                        "ResourceConvertEffect",
                        "HealEffect",
                        "RegenEffect",
                        "ShieldEffect",
                        "AttackBuffEffect",
                        "DefenseBuffEffect",
                        "MagicBuffEffect",
                        "SpeedBuffEffect",
                        "MultiStatBuffEffect",
                        "ResistanceEffect",
                        "DynamicStatBuffEffect",
                        "CleanseEffect",
                        "DispelEffect",
                        "FullDispelEffect",
                        "MagicEffectApplyEffect",
                        "MagicEffectToggleEffect",
                        "PowerUpActivateEffect",
                        "SetFlagEffect",
                        "InspectEffect",
                        "RevealEffect",
                        "TotemEffect",
                        "TransformEffect",
                        "ResurrectionEffect",
                        "ConsumeItemEffect",
                        "DestroyMetalEffect",
                    }
                    for eff in effects:
                        if type(eff).__name__ not in non_offense:
                            return True
                    return False

                return True

            def _is_damage_ability(ab) -> bool:
                """Return True if the ability is likely to affect enemy HP."""
                if ab is None:
                    return False
                if bool(getattr(ab, "weapon", False)):
                    return True
                effects = getattr(ab, "_effects", None)
                if not effects:
                    return False
                for eff in effects:
                    nm = type(eff).__name__
                    # Explicit non-damaging utility effects.
                    if nm in {"StealEffect", "MugEffect", "InspectEffect", "RevealEffect"}:
                        continue
                    # Common damage indicators.
                    if (
                        "Damage" in nm
                        or "Drain" in nm
                        or "Lifesteal" in nm
                        or "Kill" in nm
                        or nm
                        in {
                            "GoldTossEffect",
                            "SlotMachineEffect",
                            "LickEffect",
                            "GoblinPunchEffect",
                            "CrushEffect",
                            "DisintegrateEffect",
                            "DevourEffect",
                            "StompEffect",
                            "BreathDamageEffect",
                        }
                        or any(
                            k in nm
                            for k in ("Punch", "Crush", "Lick", "Toss", "Breath", "Devour", "Stomp")
                        )
                    ):
                        return True
                return False

            # Heal when low (self-targeting heal spells are handled by engine)
            try:
                hp_pct = attacker.health.current / max(1, attacker.health.max)
            except (AttributeError, TypeError, ZeroDivisionError):
                hp_pct = 1.0
            try:
                mp_pct = attacker.mana.current / max(1, attacker.mana.max)
            except (AttributeError, TypeError, ZeroDivisionError):
                mp_pct = 1.0

            # Use items under pressure (keeps simulator closer to real PvE play).
            # This is intentionally conservative: only fire when resources are critical.
            try:
                inv = getattr(attacker, "inventory", {}) or {}

                def _best_item(subtyp: str) -> str | None:
                    best_key = None
                    best_score = -1.0
                    for key, lst in inv.items():
                        if not lst:
                            continue
                        itm = lst[0]
                        if getattr(itm, "subtyp", None) != subtyp:
                            continue
                        # Prefer larger % potions when available.
                        score = float(getattr(itm, "percent", 0.0) or 0.0)
                        if score > best_score:
                            best_score = score
                            best_key = key
                    return best_key

                if (
                    (not paired_policy or turns <= max(1, int(max_turns * 0.6)))
                    and "Use Item" in _engine.available_actions
                    and inv
                ):
                    # If both HP/MP are critical and we have an elixir, prefer it.
                    if hp_pct <= 0.25 and mp_pct <= 0.20:
                        el = _best_item("Elixir")
                        if el:
                            return "Use Item", el
                    if hp_pct <= 0.25:
                        hp = _best_item("Health")
                        if hp:
                            return "Use Item", hp
                    # Mana potions: only if we are resource-starved and could plausibly cast something.
                    if mp_pct <= 0.15 and (
                        not attacker.status_effects.get("Silence")
                        or not attacker.status_effects["Silence"].active
                    ):
                        mp = _best_item("Mana")
                        if mp:
                            return "Use Item", mp
            except (AttributeError, KeyError, TypeError):
                pass

            if (not paired_policy or turns < int(max_turns * 0.6) or max_turns == 1) and (
                hp_pct < 0.35
                and "Spells" in attacker.spellbook
                and not attacker.status_effects["Silence"].active
            ):
                for nm, sp in attacker.spellbook["Spells"].items():
                    if getattr(sp, "subtyp", "") in ["Heal", "Support"]:
                        if getattr(attacker, "mana", None) and attacker.mana.current >= getattr(
                            sp, "cost", 0
                        ):
                            return "Cast Spell", nm

            # Note: "Smoke Screen" is primarily an escape tool (it triggers flee logic in BattleEngine),
            # so the simulator intentionally does not use it as a defensive/accuracy-denial opener.

            # Offensive spell if affordable
            if "Spells" in attacker.spellbook and not attacker.status_effects["Silence"].active:
                for nm, sp in attacker.spellbook["Spells"].items():
                    if _is_combat_offense(sp) and _is_damage_ability(sp):
                        if attacker.mana.current >= getattr(sp, "cost", 0):
                            return "Cast Spell", nm
                if not paired_policy:
                    for nm, sp in attacker.spellbook["Spells"].items():
                        if _is_combat_offense(sp):
                            if attacker.mana.current >= getattr(sp, "cost", 0):
                                return "Cast Spell", nm
            # Offensive skill if affordable
            if "Skills" in attacker.spellbook:

                def _skill_score(name: str, ab) -> float:
                    # Avoid analytics degeneracy: these are valuable in the real game,
                    # but in the simulator they often waste turns and swamp results.
                    # Avoid analytics degeneracy: these are valuable in the real game,
                    # but in the simulator they waste turns or end fights early.
                    if name in {"Steal", "Mug", "Inspect", "Reveal", "Smoke Screen"}:
                        return -1e9
                    # Don't spam Disarm into natural weapons / already-disarmed targets.
                    if name == "Disarm":
                        try:
                            if (
                                getattr(defender, "physical_effects", {}).get("Disarm")
                                and defender.physical_effects["Disarm"].active
                            ):
                                return -1e9
                            if (
                                hasattr(defender, "can_be_disarmed")
                                and not defender.can_be_disarmed()
                            ):
                                return -1e9
                        except (AttributeError, KeyError, TypeError):
                            return -1e9
                    score = 0.0
                    if _is_damage_ability(ab):
                        score += 100.0
                    if bool(getattr(ab, "weapon", False)):
                        score += 50.0
                    # Prefer status/control over pure utility when it's the best available.
                    if name in {"Pocket Sand", "Sleeping Powder", "Disarm"}:
                        score += 10.0
                    if name == "Conduit Command":
                        score += 25.0
                    return score

                best = None
                best_score = -1e9
                for nm, sk in attacker.spellbook["Skills"].items():
                    if not _is_combat_offense(sk):
                        continue
                    if paired_policy and bool(getattr(sk, "weapon", False)):
                        is_disarmed = getattr(attacker, "is_disarmed", None)
                        if callable(is_disarmed) and is_disarmed():
                            continue
                    if attacker.mana.current < getattr(sk, "cost", 0):
                        continue
                    sc = _skill_score(nm, sk)
                    if sc > best_score:
                        best_score = sc
                        best = nm
                if best is not None and (
                    best_score > 0 or (not paired_policy and best_score > -1e8)
                ):
                    return "Use Skill", best

            return "Attack", None

        turns = 0
        while engine.battle_continues() and turns < max_turns:
            turns += 1
            actor_id = str(getattr(engine, "current_actor_id", None) or "unknown")
            ready_at = float(getattr(engine, "current_readiness", 0.0) or 0.0)
            if previous_ready_at is not None and ready_at < previous_ready_at:
                readiness_is_monotonic = False
            previous_ready_at = ready_at
            if actor_id == previous_actor_id:
                consecutive_actor_turns += 1
            else:
                consecutive_actor_turns = 1
            previous_actor_id = actor_id
            max_consecutive_actor_turns = max(
                max_consecutive_actor_turns,
                consecutive_actor_turns,
            )
            round_number = int(getattr(engine, "round_number", 0) or 0)
            actor_turn_id = int(getattr(engine, "total_started_actor_turns", turns) or turns)
            pre = engine.pre_turn()
            action_label: str | None = None
            action_committed: bool | None = None
            forced_action = False
            if pre.can_act:
                hp_before = (
                    int(char1.health.current),
                    tuple(int(member.enemy.health.current) for member in encounter.members),
                )
                forced = engine.get_forced_action()
                if forced:
                    if forced.cancelled:
                        intent = engine.prepare_intent("Cancelled")
                    else:
                        assert forced.intent is not None
                        intent = forced.intent
                    forced_action = True
                else:
                    if engine.is_player_turn():
                        if char1_policy is None:
                            action, choice = default_policy(engine)
                            intent = engine.prepare_intent(action, choice)
                        else:
                            intent = char1_policy(engine)
                            if not isinstance(intent, ActionIntent):
                                raise TypeError("char1_policy must return ActionIntent")
                    else:
                        # By default, let enemies use their real AI (action_stack / priority rules)
                        # rather than the player-centric default_policy.
                        if char2_policy is not None:
                            intent = char2_policy(engine)
                            if not isinstance(intent, ActionIntent):
                                raise TypeError("char2_policy must return ActionIntent")
                        else:
                            action, choice = engine.get_enemy_action()
                            intent = engine.prepare_intent(action, choice)
                record_action_selection(intent.action_id, intent.choice)
                action_name = intent.action_id
                action_choice = intent.choice
                action_label = f"{action_name}:{action_choice}" if action_choice else action_name
                action_label = f"{actor_id}=" f"{action_label}"
                action_sequence.append(action_label)
                action_result = engine.execute_intent(intent)
                if not getattr(action_result, "committed", True):
                    invalid_intents += 1
                action_committed = bool(getattr(action_result, "committed", True))
                hp_after = (
                    int(char1.health.current),
                    tuple(int(member.enemy.health.current) for member in encounter.members),
                )
                if hp_after == hp_before and action_label == prior_non_progress_action:
                    repeated_non_progress_actions += 1
                    non_progress_streak += 1
                elif hp_after == hp_before:
                    non_progress_streak = 1
                else:
                    non_progress_streak = 0
                prior_non_progress_action = action_label if hp_after == hp_before else None
                max_non_progress_streak = max(
                    max_non_progress_streak,
                    non_progress_streak,
                )
                record_analytics_text(getattr(action_result, "message", ""))
            timeline_trace.append(
                TimelineTurnDiagnostic(
                    actor_id=actor_id,
                    ready_at=ready_at,
                    round_number=round_number,
                    actor_turn_id=actor_turn_id,
                    can_act=bool(pre.can_act),
                    action=action_label,
                    committed=action_committed,
                    forced=forced_action,
                )
            )
            companion_text = engine.companion_turn()
            record_analytics_text(companion_text)
            post = engine.post_turn()
            for message in getattr(post, "messages", []) or []:
                record_analytics_text(message)
            engine.swap_turns()

        # Outcome (avoid engine.end_battle bookkeeping for analytics)
        living_enemies = [member.enemy for member in encounter.living_members]
        roster_name = " / ".join(member.display_label for member in encounter.members)
        if turns >= max_turns and char1.is_alive() and living_enemies:
            winner = "draw"
            loser = "draw"
            winner_obj = char1
            loser_obj = primary_enemy
        elif not char1.is_alive() and not living_enemies:
            winner = "draw"
            loser = "draw"
            winner_obj = char1
            loser_obj = primary_enemy
        elif char1.is_alive():
            winner = char1.name
            loser = roster_name
            winner_obj = char1
            loser_obj = primary_enemy
        else:
            winner = roster_name
            loser = char1.name
            winner_obj = primary_enemy
            loser_obj = char1

        winner_class = (
            winner_obj.cls.name if hasattr(winner_obj, "cls") and winner_obj.cls else "Unknown"
        )
        loser_class = (
            loser_obj.cls.name if hasattr(loser_obj, "cls") and loser_obj.cls else "Unknown"
        )
        winner_hp = max(0, winner_obj.health.current)
        winner_max = winner_obj.health.max
        outcome = None
        if turns < max_turns or not char1.is_alive() or not living_enemies:
            outcome = engine.end_battle()
        settlements = tuple(getattr(outcome, "member_settlements", ()) or ())

        return CombatStats(
            winner=winner,
            loser=loser,
            winner_class=winner_class,
            loser_class=loser_class,
            winner_level=_combat_level(winner_obj),
            loser_level=_combat_level(loser_obj),
            turns=turns,
            winner_hp_remaining=winner_hp,
            winner_hp_max=winner_max,
            total_damage_dealt=sum(damage_by_actor.values()),
            total_damage_taken=0,
            abilities_used=dict(abilities_used),
            status_effects_applied=dict(status_applied),
            class_kit_events=dict(class_kit_events),
            action_economy_events=dict(action_economy_events),
            critical_hits=crits,
            misses=misses,
            rounds=int(getattr(engine, "round_number", 0) or 0),
            actor_turns=int(getattr(engine, "total_started_actor_turns", turns) or turns),
            roster=tuple(member.display_label for member in encounter.members),
            enemy_hp_remaining={
                member.combatant_id: max(
                    0,
                    int(member.enemy.health.current),
                )
                for member in encounter.members
            },
            player_mana_remaining=max(0, int(char1.mana.current)),
            player_hp_remaining=max(0, int(char1.health.current)),
            player_hp_max=max(1, int(char1.health.max)),
            resolutions=tuple(
                member.resolution.value if member.resolution else None
                for member in encounter.members
            ),
            consumables_used=consumables_used,
            damage_by_combatant=dict(damage_by_combatant),
            reward_experience=int(getattr(outcome, "total_experience", 0) or 0),
            reward_gold=sum(int(getattr(settlement, "gold", 0) or 0) for settlement in settlements),
            action_sequence=tuple(action_sequence[-80:]),
            repeated_non_progress_actions=repeated_non_progress_actions,
            max_non_progress_streak=max_non_progress_streak,
            invalid_intents=invalid_intents,
            max_turns_reached=(turns >= max_turns and char1.is_alive() and bool(living_enemies)),
            timeline_trace=tuple(timeline_trace[-80:]),
            final_readiness={
                actor_id: float(ready_at)
                for actor_id, ready_at in sorted(
                    getattr(getattr(engine, "_actor_cycle", None), "readiness", {}).items()
                )
            },
            readiness_is_monotonic=readiness_is_monotonic,
            max_consecutive_actor_turns=max_consecutive_actor_turns,
        )

    def run_simulations(
        self,
        char1: Player | Callable[[], Player],
        char2: Character | Callable[[], Character] | None = None,
        iterations: int = 1000,
        *,
        encounter=None,
        seed: int | None = None,
    ) -> BalanceReport:
        """
        Run multiple simulations between two characters.

        Args:
            char1: First combatant
            char2: Legacy singleton combatant or factory.
            encounter: Encounter instance or zero-argument factory.
            iterations: Number of battles to simulate

        Returns:
            Balance report with aggregated statistics
        """
        results = []
        if (char2 is None) == (encounter is None):
            raise ValueError("Supply exactly one of char2 or encounter.")

        base_seed = seed if seed is not None else None
        for i in range(iterations):
            sim_seed = None if base_seed is None else (base_seed + i)
            source = stdlib_random.Random(sim_seed)
            with using_random_source(source):
                if callable(char1):
                    c1 = char1()
                else:
                    c1 = copy.deepcopy(char1)

                if char2 is not None:
                    c2 = char2() if callable(char2) else copy.deepcopy(char2)
                    runtime_encounter = None
                else:
                    c2 = None
                    runtime_encounter = (
                        encounter() if callable(encounter) else copy.deepcopy(encounter)
                    )

                if c2 is not None:
                    result = self.simulate_battle(c1, c2, rng=source)
                else:
                    result = self.simulate_battle(c1, encounter=runtime_encounter, rng=source)
            results.append(result)

        self.results.extend(results)

        return BalanceReport(total_battles=iterations, results=results)


def remaining_improvement_tuning_report() -> dict[str, object]:
    """Return the bounded simulation targets for deferred roadmap tuning."""
    return {
        "footpad": {
            "status": "measure_before_tuning",
            "levels": [1, 5, 10],
            "matchups": ["Warrior", "Rogue", "Mage", "Cleric"],
            "metrics": ["win_rate", "average_turns", "damage_taken", "close_fight_rate"],
        },
        "ordinary_drops": {
            "status": "measure_before_tuning",
            "luck_profiles": ["low", "average", "high"],
            "iterations_per_profile": 500,
            "excluded_drop_sources": ["quest", "special", "boss"],
            "metrics": ["drop_rate", "items_per_kill", "gold_value_per_kill"],
        },
        "multi_strike_accuracy": {
            "status": "measure_before_tuning",
            "strike_counts": [2, 3, 4],
            "metrics": ["hits_per_use", "damage_per_use", "miss_streak_rate"],
            "candidate_change": "per_strike_accuracy_falloff",
        },
        "enfeeble": {
            "status": "measure_before_tuning",
            "metrics": ["land_rate", "debuff_amount", "duration", "enemy_damage_delta"],
        },
        "poison_consistency": {
            "status": "measure_before_tuning",
            "sources": ["Poison Dart", "Poison Breath", "Poison Strike", "Hex"],
            "metrics": [
                "application_rate",
                "duration",
                "tick_damage",
                "resist_outcome",
                "immunity_outcome",
            ],
        },
    }


def quick_balance_test(class_name: str, level: int = 10) -> BalanceReport:
    """
    Quick helper function to test a class against all other classes.

    Args:
        class_name: Name of the class to test
        level: Level to test at

    Returns:
        Balance report
    """
    # Character factory wiring for full class-vs-class simulations is still
    # future work; return a real empty report so callers can handle the helper
    # consistently while that broader feature is deferred.
    return BalanceReport(total_battles=0, results=[])
