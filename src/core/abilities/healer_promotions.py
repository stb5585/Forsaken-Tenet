"""Active and passive techniques for the Monk and Priest promotion lines."""

from __future__ import annotations

from typing import Any

from src.core.randomness import gameplay_random as random

from .base import Class, Skill


class UnarmedProficiency(Class):
    """Improve attacks made without a conventional weapon."""

    def __init__(self) -> None:
        super().__init__(
            "Unarmed Proficiency",
            "Passive: Gain 10% accuracy and weapon damage while unarmed or using a fist weapon.",
        )
        self.passive = True


class FlowingPalm(Skill):
    """A reliable unarmed strike that rewards accumulated Ki."""

    def __init__(self) -> None:
        super().__init__(
            "Flowing Palm",
            "Strike for 115% weapon damage and gain 5 accuracy points per stored Ki.",
            weapon=True,
        )
        self.cost = 8
        self.subtyp = "Offensive"

    def use(self, user: Any, target: Any | None = None, **kwargs: Any):
        result = super().use(user, target, **kwargs)
        if target is None:
            result.message = "Flowing Palm needs a target.\n"
            return result
        if user.mana.current < self.cost:
            result.message = f"{user.name} does not have enough mana.\n"
            return result
        weapon = user.equipment.get("Weapon")
        if getattr(weapon, "subtyp", "None") not in {"None", "Fist"}:
            result.message = "Flowing Palm requires an empty hand or fist weapon.\n"
            return result
        from ..classes import promotion_kits

        user.mana.current -= self.cost
        accuracy = 0.05 * int(promotion_kits.combat_state(user).get("ki", 0) or 0)
        before = int(target.health.current)
        message, hit, critical = user.weapon_damage(
            target,
            dmg_mod=1.15,
            use_offhand=False,
            accuracy_modifier=accuracy,
        )
        result.hit = hit
        result.crit = critical if critical > 1 else None
        result.damage = max(0, before - int(target.health.current))
        result.message = message
        return result


class RopeADope(Skill):
    """Challenge a foe and turn three consecutive dodges into a combination."""

    def __init__(self) -> None:
        super().__init__(
            "Rope-a-Dope",
            (
                "Challenge a target, enter an escalating dodge stance, and answer "
                "three consecutive dodges with a four-hit combination. A hit ends the stance."
            ),
        )
        self.cost = 14
        self.subtyp = "Defensive"

    def use(self, user: Any, target: Any | None = None, **kwargs: Any):
        result = super().use(user, target, **kwargs)
        if target is None:
            result.message = "Rope-a-Dope needs a target.\n"
            return result
        if user.mana.current < self.cost:
            result.message = f"{user.name} does not have enough mana.\n"
            return result
        user.mana.current -= self.cost
        from ..classes import promotion_kits

        promotion_kits.combat_state(user)["rope_a_dope"] = {
            "active": True,
            "dodges": 0,
            "target": target,
        }
        user.enter_defensive_stance(duration=4)
        generator = kwargs.get("rng") or random
        challenged = False
        chance = (
            0.75 if promotion_kits._has_track_talent(user, "master-monk.goading-smile") else 0.50
        )
        if not target.has_status_protection("Berserk") and generator.random() < chance:
            effect = target.status_effects["Berserk"]
            effect.active = True
            effect.duration = max(2, int(effect.duration or 0))
            effect.source = self.name
            challenged = True
        result.hit = challenged
        result.message = f"{user.name} settles into the Rope-a-Dope stance.\n"
        if challenged:
            result.message += f"{target.name} accepts the challenge in a rage.\n"
        return result


class MagicalInvigoration(Class):
    """Turn successive regeneration ticks into independently expiring Magic."""

    def __init__(self) -> None:
        super().__init__(
            "Magical Invigoration",
            (
                "Passive: Each Regen tick grants 4 Magic. Each stack expires "
                "independently in the same cadence in which it was gained."
            ),
        )
        self.passive = True
