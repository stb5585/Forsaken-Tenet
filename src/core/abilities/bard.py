"""Active Bard-family combat techniques beyond sustained songs."""

from __future__ import annotations

from typing import Any

from src.core.randomness import gameplay_random as random

from ..combat.targeting import TargetScope
from .base import Class, Skill, Spell
from .spell_types import _simple_spell_damage


def _spend_mana(user: Any, cost: int, action: str) -> str:
    if int(user.mana.current) < cost:
        return f"{user.name} does not have enough mana for {action}.\n"
    user.mana.current -= cost
    return ""


def _gain_song_crescendo(user: Any, reason: str) -> str:
    from ..classes import bard, promotion_kits

    if not bard.active_song(user):
        return ""
    return promotion_kits.gain_meter(user, "crescendo", 1, reason)


class InspiringVerse(Spell):
    """Deliver immediate support without replacing the active song."""

    def __init__(self) -> None:
        super().__init__(
            "Inspiring Verse",
            "Bolster Attack and Magic for three turns without replacing the active song.",
            school="Performance",
        )
        self.cost = 8
        self.subtyp = "Support"
        self.target_scope = TargetScope.SELF

    def cast(self, user: Any, target: Any | None = None, **kwargs: Any):
        del target, kwargs
        result = super().cast(user, user)
        result.message = _spend_mana(user, self.cost, self.name)
        if result.message:
            return result
        amount = max(2, int(user.check_mod("magic") * 0.15))
        for stat_name in ("Attack", "Magic"):
            effect = user.stat_effects[stat_name]
            effect.active = True
            effect.duration = max(effect.duration, 3)
            effect.extra = max(int(effect.extra or 0), amount)
            result.effects_applied["Stat"].append(stat_name)
        result.hit = True
        result.message = f"{user.name}'s Inspiring Verse raises Attack and Magic by {amount}.\n"
        result.message += _gain_song_crescendo(user, self.name)
        return result


class DissonantChord(Spell):
    """Deal untyped damage and disrupt the target's magical output."""

    def __init__(self) -> None:
        super().__init__(
            "Dissonant Chord",
            "Deal non-elemental damage and reduce the target's Magic for two turns.",
            school="Performance",
        )
        self.cost = 10
        self.subtyp = "Non-elemental"

    def cast(self, user: Any, target: Any | None = None, **kwargs: Any):
        result = super().cast(user, target, **kwargs)
        if target is None:
            result.message = "Dissonant Chord needs a target.\n"
            return result
        result.message = _spend_mana(user, self.cost, self.name)
        if result.message:
            return result
        before = int(target.health.current)
        message, damage = _simple_spell_damage(
            user,
            target,
            dmg_mod=0.80,
            typ="Non-elemental",
        )
        result.damage = max(damage, before - int(target.health.current))
        result.hit = result.damage > 0
        result.message = message
        if result.hit:
            penalty = max(2, result.damage // 8)
            effect = target.stat_effects["Magic"]
            effect.active = True
            effect.duration = max(effect.duration, 2)
            effect.extra = min(int(effect.extra or 0), -penalty)
            result.effects_applied["Stat"].append("Magic")
            result.message += f"The chord reduces {target.name}'s Magic by {penalty}.\n"
        return result


class PrismaticRay(Spell):
    """Focus one randomly selected element into direct damage and a rider."""

    ELEMENTS = ("Fire", "Ice", "Electric", "Wind")

    def __init__(self) -> None:
        super().__init__(
            "Prismatic Ray",
            "Deal focused Fire, Ice, Electric, or Wind damage with a matching stat rider.",
            school="Elemental",
        )
        self.cost = 13
        self.subtyp = "Elemental"

    def cast(self, user: Any, target: Any | None = None, **kwargs: Any):
        result = super().cast(user, target, **kwargs)
        if target is None:
            result.message = "Prismatic Ray needs a target.\n"
            return result
        result.message = _spend_mana(user, self.cost, self.name)
        if result.message:
            return result
        rng = kwargs.get("rng") or random
        element = str(rng.choice(self.ELEMENTS))
        before = int(target.health.current)
        message, damage = _simple_spell_damage(
            user,
            target,
            dmg_mod=1.05,
            typ=element,
        )
        result.damage = max(damage, before - int(target.health.current))
        result.hit = result.damage > 0
        result.extra["element"] = element
        result.message = f"Prismatic Ray focuses {element}.\n{message}"
        if result.hit:
            stat_name = {
                "Fire": "Attack",
                "Ice": "Speed",
                "Electric": "Magic",
                "Wind": "Defense",
            }[element]
            effect = target.stat_effects[stat_name]
            effect.active = True
            effect.duration = max(effect.duration, 2)
            effect.extra = min(int(effect.extra or 0), -max(2, result.damage // 10))
            result.effects_applied["Stat"].append(stat_name)
        return result


class RhythmicStrike(Skill):
    """Make a weapon attack that rewards fighting inside a song."""

    def __init__(self) -> None:
        super().__init__(
            "Rhythmic Strike",
            "Strike for 115% weapon damage and gain Crescendo if a combat song is active.",
            weapon=True,
        )
        self.cost = 6
        self.subtyp = "Offensive"

    def use(self, user: Any, target: Any | None = None, **kwargs: Any):
        result = super().use(user, target, **kwargs)
        if target is None:
            result.message = "Rhythmic Strike needs a target.\n"
            return result
        result.message = _spend_mana(user, self.cost, self.name)
        if result.message:
            return result
        before = int(target.health.current)
        message, hit, critical = user.weapon_damage(
            target,
            dmg_mod=1.15,
            use_offhand=False,
        )
        result.hit = hit
        result.crit = critical if critical > 1 else None
        result.damage = max(0, before - int(target.health.current))
        result.message = message
        if hit:
            result.message += _gain_song_crescendo(user, self.name)
        return result


class CurtainGuard(Class):
    """Raise a short defensive curtain while maintaining the performance."""

    def __init__(self) -> None:
        super().__init__(
            "Curtain Guard",
            "Raise Defense and Magic Defense for three turns without ending the active song.",
        )
        self.cost = 7
        self.subtyp = "Defensive"
        self.target_scope = TargetScope.SELF

    def use(self, user: Any, target: Any | None = None, **kwargs: Any):
        del target, kwargs
        result = super().use(user, user)
        result.message = _spend_mana(user, self.cost, self.name)
        if result.message:
            return result
        amount = max(3, int(user.check_mod("magic def") * 0.15))
        for stat_name in ("Defense", "Magic Defense"):
            effect = user.stat_effects[stat_name]
            effect.active = True
            effect.duration = max(effect.duration, 3)
            effect.extra = max(int(effect.extra or 0), amount)
            result.effects_applied["Stat"].append(stat_name)
        result.hit = True
        result.message = f"{user.name} raises a defensive curtain worth {amount}.\n"
        result.message += _gain_song_crescendo(user, self.name)
        return result


class RallyingChorus(Spell):
    """Restore vitality and add a short offensive support beat."""

    def __init__(self) -> None:
        super().__init__(
            "Rallying Chorus",
            "Restore HP and raise Attack and Magic for two turns.",
            school="Performance",
        )
        self.cost = 14
        self.subtyp = "Support"
        self.target_scope = TargetScope.SELF

    def cast(self, user: Any, target: Any | None = None, **kwargs: Any):
        del target, kwargs
        result = super().cast(user, user)
        result.message = _spend_mana(user, self.cost, self.name)
        if result.message:
            return result
        healing = min(
            user.health.max - user.health.current,
            max(1, int(user.check_mod("magic") * 0.65)),
        )
        user.health.current += healing
        result.healing = healing
        amount = max(3, int(user.check_mod("magic") * 0.12))
        for stat_name in ("Attack", "Magic"):
            effect = user.stat_effects[stat_name]
            effect.active = True
            effect.duration = max(effect.duration, 2)
            effect.extra = max(int(effect.extra or 0), amount)
            result.effects_applied["Stat"].append(stat_name)
        result.hit = True
        result.message = f"Rallying Chorus restores {healing} HP and raises offense by {amount}.\n"
        return result


class ResonantWave(Spell):
    """Project forceful untyped sound that weakens enemy offense."""

    def __init__(self) -> None:
        super().__init__(
            "Resonant Wave",
            "Deal non-elemental damage and reduce Attack and Magic for two turns.",
            school="Performance",
        )
        self.cost = 16
        self.subtyp = "Non-elemental"

    def cast(self, user: Any, target: Any | None = None, **kwargs: Any):
        result = super().cast(user, target, **kwargs)
        if target is None:
            result.message = "Resonant Wave needs a target.\n"
            return result
        result.message = _spend_mana(user, self.cost, self.name)
        if result.message:
            return result
        before = int(target.health.current)
        message, damage = _simple_spell_damage(
            user,
            target,
            dmg_mod=1.15,
            typ="Non-elemental",
        )
        result.damage = max(damage, before - int(target.health.current))
        result.hit = result.damage > 0
        result.message = message
        if result.hit:
            penalty = max(3, result.damage // 10)
            for stat_name in ("Attack", "Magic"):
                effect = target.stat_effects[stat_name]
                effect.active = True
                effect.duration = max(effect.duration, 2)
                effect.extra = min(int(effect.extra or 0), -penalty)
                result.effects_applied["Stat"].append(stat_name)
        return result


class PrismaticFinale(Spell):
    """Spend Crescendo on a concentrated random-element attack."""

    def __init__(self) -> None:
        super().__init__(
            "Prismatic Finale",
            "Spend all Crescendo to deal scaling Fire, Ice, Electric, or Wind damage.",
            school="Elemental",
        )
        self.cost = 18
        self.subtyp = "Elemental"

    def cast(self, user: Any, target: Any | None = None, **kwargs: Any):
        from ..classes import promotion_kits

        result = super().cast(user, target, **kwargs)
        if target is None:
            result.message = "Prismatic Finale needs a target.\n"
            return result
        state = promotion_kits.combat_state(user)
        spent = int(state.get("crescendo", 0) or 0)
        if spent <= 0:
            result.message = "Prismatic Finale requires Crescendo.\n"
            return result
        result.message = _spend_mana(user, self.cost, self.name)
        if result.message:
            return result
        state["crescendo"] = 0
        rng = kwargs.get("rng") or random
        element = str(rng.choice(PrismaticRay.ELEMENTS))
        before = int(target.health.current)
        message, damage = _simple_spell_damage(
            user,
            target,
            dmg_mod=0.80 + (0.25 * spent),
            typ=element,
        )
        result.damage = max(damage, before - int(target.health.current))
        result.hit = result.damage > 0
        result.extra.update({"element": element, "crescendo_spent": spent})
        result.message = (
            f"{user.name} spends {spent} Crescendo on a {element} Prismatic Finale.\n" f"{message}"
        )
        return result


class SyncopatedStrike(RhythmicStrike):
    """Troubadour weapon phrase that prolongs the active song on hit."""

    def __init__(self) -> None:
        super().__init__()
        self.name = "Syncopated Strike"
        self.description = (
            "Strike for 135% weapon damage; on hit, extend the active song by one turn."
        )
        self.cost = 10

    def use(self, user: Any, target: Any | None = None, **kwargs: Any):
        from ..classes import bard

        result = Skill.use(self, user, target, **kwargs)
        if target is None:
            result.message = "Syncopated Strike needs a target.\n"
            return result
        result.message = _spend_mana(user, self.cost, self.name)
        if result.message:
            return result
        before = int(target.health.current)
        message, hit, critical = user.weapon_damage(
            target,
            dmg_mod=1.35,
            use_offhand=False,
        )
        result.hit = hit
        result.crit = critical if critical > 1 else None
        result.damage = max(0, before - int(target.health.current))
        result.message = message
        if hit:
            state = bard.ensure_song_state(user)
            if state.get("active") and int(state.get("turns", 0) or 0) > 0:
                state["turns"] += 1
                result.message += "Syncopation extends the active song by one turn.\n"
        return result


class Countermelody(Class):
    """Convert current musical momentum into a non-spending ward."""

    def __init__(self) -> None:
        super().__init__(
            "Countermelody",
            "Raise a two-turn ward whose strength scales with current Crescendo without spending it.",
        )
        self.cost = 10
        self.subtyp = "Defensive"
        self.target_scope = TargetScope.SELF

    def use(self, user: Any, target: Any | None = None, **kwargs: Any):
        del target, kwargs
        from ..classes import promotion_kits

        result = super().use(user, user)
        result.message = _spend_mana(user, self.cost, self.name)
        if result.message:
            return result
        crescendo = int(promotion_kits.combat_state(user).get("crescendo", 0) or 0)
        amount = max(10, int(user.check_mod("magic def") * 0.25) + crescendo * 8)
        effect = user.magic_effects["Nature Shield"]
        effect.active = True
        effect.duration = max(effect.duration, 2)
        effect.extra = max(int(effect.extra or 0), amount)
        result.hit = True
        result.effects_applied["Magic"].append("Nature Shield")
        result.message = f"Countermelody raises a {amount}-point ward.\n"
        return result
