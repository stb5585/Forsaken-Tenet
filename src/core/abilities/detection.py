"""Out-of-combat creature detection spells and encounter helpers."""

from __future__ import annotations

from typing import Any

from src.core.randomness import gameplay_random as random

from ..combat.targeting import TargetScope
from .base import Spell

DETECT_STEPS = 50


class DetectEnemy(Spell):
    """Maintain one timed creature-family detection spell at a time."""

    enemy_type = ""

    def __init__(self) -> None:
        super().__init__(
            f"Detect {self.enemy_type}",
            f"Cast outside combat. For {DETECT_STEPS} steps, encounters with "
            f"{self.enemy_type} enemies may be detected in time to fight or avoid them. "
            "Casting another Detect spell replaces this one.",
            school="Divination",
        )
        self.cost = 10
        self.combat = False
        self.subtyp = "Divination"
        self.target_scope = TargetScope.NONE

    def cast_out(self, user: Any) -> str:
        user.mana.current -= self.cost
        user.detect_enemy_type = self.enemy_type
        user.detect_enemy_steps = DETECT_STEPS
        return (
            f"{user.name} begins watching for {self.enemy_type} enemies for {DETECT_STEPS} steps.\n"
        )

    cast = cast_out


def _detect_class(enemy_type: str):
    return type(
        f"Detect{enemy_type}",
        (DetectEnemy,),
        {"enemy_type": enemy_type, "__module__": __name__},
    )


DetectSlime = _detect_class("Slime")
DetectAnimal = _detect_class("Animal")
DetectHumanoid = _detect_class("Humanoid")
DetectFey = _detect_class("Fey")
DetectFiend = _detect_class("Fiend")
DetectUndead = _detect_class("Undead")
DetectElemental = _detect_class("Elemental")
DetectDragon = _detect_class("Dragon")
DetectMonster = _detect_class("Monster")
DetectAberration = _detect_class("Aberration")
DetectConstruct = _detect_class("Construct")


def tick_detection(character: Any, steps: int) -> None:
    """Reduce an active Detect spell's exploration duration."""
    remaining = max(0, int(getattr(character, "detect_enemy_steps", 0) or 0) - steps)
    character.detect_enemy_steps = remaining
    if remaining == 0:
        character.detect_enemy_type = None


def detects_encounter(character: Any, enemy: Any, roll: float | None = None) -> bool:
    """Return whether active detection reveals a matching encounter."""
    if int(getattr(character, "detect_enemy_steps", 0) or 0) <= 0:
        return False
    enemy_type = str(getattr(enemy, "enemy_typ", ""))
    if enemy_type != getattr(character, "detect_enemy_type", None):
        return False
    wisdom = int(getattr(getattr(character, "stats", None), "wisdom", 10))
    chance = max(0.25, min(0.90, 0.50 + max(0, wisdom - 10) * 0.02))
    return (random.random() if roll is None else float(roll)) < chance
