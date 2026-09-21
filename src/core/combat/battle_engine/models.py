"""Battle-engine phase and outcome value objects."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from ..combat_result import CombatResultGroup
from ..encounter import EnemyResolution, EnemyResolutionRecord
from ..targeting import ActionIntent as ActionIntent
from ..targeting import ActionValidationCode

if TYPE_CHECKING:
    from ...character import Character


@dataclass
class PreTurnResult:
    """Result of pre-turn processing (status effects, activity check)."""

    effects_text: str = ""
    can_act: bool = True
    inactive_reason: str = ""
    # Exploding shield damage dealt to the defender during effects processing
    shield_explosion_damage: int = 0
    # True when the attacker died from their own effects (poison, DOT, bleed)
    died_from_effects: bool = False


@dataclass
class ForcedAction:
    """Represents an automatically-determined action (berserk, charging, jump)."""

    intent: ActionIntent | None = None
    cancel_message: str = ""

    @property
    def cancelled(self) -> bool:
        """Return whether the forced turn was consumed by cancellation."""
        return self.intent is None


@dataclass
class ActionResult:
    """Result of executing a combat action."""

    message: str = ""
    fled: bool = False
    summon_started: bool = False
    summon_recalled: bool = False
    summon: Character | None = None
    committed: bool = True
    validation_code: ActionValidationCode | None = None
    combat_results: CombatResultGroup | None = None
    new_resolutions: tuple[EnemyResolutionRecord, ...] = ()


@dataclass
class PostTurnResult:
    """Result of post-turn processing."""

    messages: list[str] = field(default_factory=list)
    defender_died: bool = False
    resurrected: bool = False
    summon_died: bool = False
    new_resolutions: tuple[EnemyResolutionRecord, ...] = ()


@dataclass(frozen=True)
class LootAward:
    """One acquired item stack and its inventory destination."""

    item_name: str
    quantity: int
    destination: str


@dataclass
class BattleOutcome:
    """Final result of a completed battle."""

    result: str = ""  # "victory", "defeat", "flee"
    winner: str | None = None
    message: str = ""  # Summary text (exp, loot, quests, etc.)
    level_up: bool = False
    boss: bool = False
    enemy_escaped: bool = False
    rewards_settled: bool = True
    member_settlements: tuple[EnemySettlement, ...] = ()
    total_experience: int = 0
    total_gold: int = 0
    loot_awards: tuple[LootAward, ...] = ()
    resolution_counts: tuple[tuple[EnemyResolution, int], ...] = ()
    notices: tuple[str, ...] = ()


@dataclass(frozen=True)
class EnemySettlement:
    """Immutable reward summary for one resolved encounter member."""

    combatant_id: str
    display_label: str
    resolution: EnemyResolution
    experience: int = 0
    gold: int = 0
    loot_eligible: bool = False
    kill_credit: bool = False
    bestiary_credit: bool = False
    quest_credit: bool = False
    bounty_credit: bool = False
    loot_awards: tuple[LootAward, ...] = ()
    message: str = ""
