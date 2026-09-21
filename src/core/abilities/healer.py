"""Authored abilities for the Healer base-class tree."""

from __future__ import annotations

from typing import Any

from src.core.randomness import gameplay_random as random

from ..combat.combat_result import CombatResult, CombatResultGroup
from ..combat.targeting import TargetScope
from .base import Class, Skill, Spell
from .spell_types import _simple_spell_damage


def _targets(user: Any, battle_engine: Any | None) -> list[Any]:
    """Return living hostile targets available to an area ability."""
    if battle_engine is None:
        return []
    if user is getattr(battle_engine, "player", None):
        return [member.enemy for member in battle_engine.encounter.living_members]
    return [getattr(battle_engine, "player", None)]


def _apply_status(target: Any, name: str, duration: int, source: str) -> bool:
    """Apply a timed status unless the target is protected."""
    if target is None or target.has_status_protection(name):
        return False
    effect = target.status_effects[name]
    effect.active = True
    effect.duration = max(duration, int(effect.duration or 0))
    effect.source = source
    return True


class _HealerPassive(Class):
    """Small passive wrapper for Healer-tree mechanics."""

    def __init__(self, name: str, description: str) -> None:
        super().__init__(name=name, description=description)
        self.passive = True


class Lullaby(Skill):
    """Use Charisma to put one target to sleep."""

    def __init__(self) -> None:
        super().__init__("Lullaby", "Serenade a target with a chance to put it to sleep.")
        self.cost = 5
        self.subtyp = "Control"

    def use(self, user, target=None, **kwargs):
        result = super().use(user, target, **kwargs)
        if target is None:
            result.message = "Lullaby needs a target.\n"
            return result
        if user.mana.current < self.cost:
            result.message = f"{user.name} does not have enough mana.\n"
            return result
        user.mana.current -= self.cost
        generator = kwargs.get("rng") or random
        chance = max(
            0.20,
            min(0.85, 0.50 + (int(user.stats.charisma) - int(target.stats.wisdom)) * 0.02),
        )
        if generator.random() < chance and _apply_status(target, "Sleep", 3, self.name):
            result.effects_applied["Status"].append("Sleep")
            result.message = f"{target.name} falls asleep to {user.name}'s lullaby.\n"
        else:
            result.message = f"{target.name} resists the lullaby.\n"
        return result


class BeginnersLuck(Skill):
    """Improve Charisma's contribution to luck rolls for one combat."""

    def __init__(self) -> None:
        super().__init__(
            "Beginner's Luck",
            "Increase the Charisma bonus on luck rolls for the rest of combat.",
        )
        self.cost = 5
        self.subtyp = "Luck"
        self.target_self = True

    def use(self, user, target=None, **kwargs):
        result = super().use(user, user, **kwargs)
        if user.mana.current < self.cost:
            result.message = f"{user.name} does not have enough mana.\n"
            return result
        user.mana.current -= self.cost
        user._beginners_luck_active = True
        result.message = f"{user.name} trusts in beginner's luck.\n"
        return result


class MentalShard(Skill):
    """Deal psychic damage and temporarily reduce Intelligence."""

    def __init__(self) -> None:
        super().__init__(
            "Mental Shard",
            "Drive psychic spines into a target and lower its Intelligence.",
        )
        self.cost = 7
        self.subtyp = "Offensive"

    def use(self, user, target=None, **kwargs):
        result = super().use(user, target, **kwargs)
        if target is None:
            result.message = "Mental Shard needs a target.\n"
            return result
        if user.mana.current < self.cost:
            result.message = f"{user.name} does not have enough mana.\n"
            return result
        user.mana.current -= self.cost
        message, damage = _simple_spell_damage(user, target, dmg_mod=0.90, typ="Magic")
        result.damage = damage
        result.hit = damage > 0
        if damage > 0:
            existing = getattr(target, "_mental_shard", None)
            if not isinstance(existing, dict):
                amount = max(2, int(target.stats.intel * 0.25))
                target.stats.intel = max(1, int(target.stats.intel) - amount)
                target._mental_shard = {"amount": amount, "turns": 3}
            else:
                existing["turns"] = 3
            message += f"{target.name}'s Intelligence is temporarily reduced.\n"
        result.message = message
        return result


class Cacophany(Skill):
    """Resolve one of four Charisma-driven performance outcomes."""

    def __init__(self) -> None:
        super().__init__("Cacophany", "Perform an unpredictable Charisma-driven vocal warm-up.")
        self.cost = 10
        self.subtyp = "Support"
        self.target_scope = TargetScope.ALL_ENEMIES

    def use(self, user, target=None, **kwargs):
        result = super().use(user, target, **kwargs)
        if user.mana.current < self.cost:
            result.message = f"{user.name} does not have enough mana.\n"
            return result
        user.mana.current -= self.cost
        generator = kwargs.get("rng") or random
        roll = generator.randint(1, 20) + ((int(user.stats.charisma) - 10) // 2)
        enemies = _targets(user, kwargs.get("battle_engine")) or ([target] if target else [])
        if roll <= 5:
            _apply_status(user, "Silence", 2, self.name)
            result.message = f"{user.name} loses their voice and is silenced.\n"
        elif roll <= 10:
            affected = [user, *enemies]
            for character in affected:
                _apply_status(character, "Berserk", 2, self.name)
            result.message = "The cacophany enrages everyone.\n"
        elif roll <= 15:
            for enemy in enemies:
                _apply_status(enemy, "Sleep", 2, self.name)
            result.message = "The strange harmony soothes the enemies to sleep.\n"
        else:
            messages = []
            for enemy in enemies:
                message, damage = _simple_spell_damage(user, enemy, dmg_mod=1.10, typ="Magic")
                result.damage += damage
                messages.append(message)
            result.message = "A psychic scream tears through the battlefield.\n" + "".join(messages)
        return result

    def use_group(self, user, targets, *, battle_engine, rng=None):
        """Resolve one performance once while recording every affected enemy."""
        health_before = {target_id: int(target.health.current) for target_id, target in targets}
        first_target = targets[0][1] if targets else None
        resolved = self.use(
            user,
            target=first_target,
            battle_engine=battle_engine,
            rng=rng,
        )
        group = CombatResultGroup(
            action=self.name,
            actor_id=battle_engine.current_actor_id,
            target_scope=TargetScope.ALL_ENEMIES,
            target_ids=tuple(target_id for target_id, _target in targets),
        )
        for index, (target_id, target) in enumerate(targets):
            group.add(
                CombatResult(
                    action=self.name,
                    actor=user,
                    target=target,
                    actor_id=battle_engine.current_actor_id,
                    target_id=target_id,
                    damage=max(0, health_before[target_id] - int(target.health.current)),
                    message=resolved.message if index == 0 else "",
                )
            )
        return group


class Tranquility(Spell):
    """Apply Peaceful, which already blocks Berserk in the status system."""

    def __init__(self) -> None:
        super().__init__(
            "Tranquility",
            "Apply Peaceful and grant immunity to Berserk.",
            school="Holy",
        )
        self.cost = 5
        self.subtyp = "Support"

    def cast(self, user, target=None, **kwargs):
        result = super().cast(user, user, **kwargs)
        if user.mana.current < self.cost:
            result.message = f"{user.name} does not have enough mana.\n"
            return result
        user.mana.current -= self.cost
        _apply_status(user, "Peaceful", 4, self.name)
        result.message = f"{user.name} becomes peaceful and immune to Berserk.\n"
        return result


class Courage(Spell):
    """Protect against Fear and grant temporary health."""

    def __init__(self) -> None:
        super().__init__(
            "Courage",
            "Become immune to Fear and gain 15% maximum health temporarily.",
            school="Holy",
        )
        self.cost = 7
        self.subtyp = "Support"

    def cast(self, user, target=None, **kwargs):
        result = super().cast(user, user, **kwargs)
        if user.mana.current < self.cost:
            result.message = f"{user.name} does not have enough mana.\n"
            return result
        user.mana.current -= self.cost
        amount = max(1, int(user.health.max * 0.15))
        user.temporary_health = {"amount": amount, "turns": 4, "source": self.name}
        user._courage_turns = 4
        result.message = f"{user.name} gains Courage and {amount} temporary health.\n"
        return result


class Vision(Spell):
    """Grant sight in combat or during exploration."""

    exploration_cast = True

    def __init__(self) -> None:
        super().__init__(
            "Vision",
            "Grant sight to the target for a time, including outside combat.",
            school="Divination",
        )
        self.cost = 6
        self.subtyp = "Support"

    @staticmethod
    def _apply(user) -> str:
        user.sight = True
        user._vision_steps = 50
        user._vision_turns = 5
        return f"{user.name}'s sight is magically sharpened.\n"

    def cast(self, user, target=None, **kwargs):
        result = super().cast(user, user, **kwargs)
        if user.mana.current < self.cost:
            result.message = f"{user.name} does not have enough mana.\n"
            return result
        user.mana.current -= self.cost
        result.message = self._apply(user)
        return result

    def cast_out(self, game_or_user):
        user = getattr(game_or_user, "player_char", game_or_user)
        if user.mana.current < self.cost:
            return f"{user.name} does not have enough mana.\n"
        user.mana.current -= self.cost
        return self._apply(user)


class Tutelary(Spell):
    """Call a temporary guardian spirit that can reduce incoming damage."""

    def __init__(self) -> None:
        super().__init__(
            "Tutelary",
            "Call a spirit that sometimes reduces incoming damage.",
            school="Conjuration",
        )
        self.cost = 9
        self.subtyp = "Support"

    def cast(self, user, target=None, **kwargs):
        result = super().cast(user, user, **kwargs)
        if user.mana.current < self.cost:
            result.message = f"{user.name} does not have enough mana.\n"
            return result
        user.mana.current -= self.cost
        user._tutelary_turns = 5
        result.message = f"A tutelary spirit begins guarding {user.name}.\n"
        return result


class Safeguarding(_HealerPassive):
    def __init__(self) -> None:
        super().__init__(
            "Safeguarding",
            "Direct heals reduce damage from the target's next melee source.",
        )


class FlashBlindness(_HealerPassive):
    def __init__(self) -> None:
        super().__init__(
            "Flash Blindness",
            "Holy spells may blind every nearby enemy with brilliant radiance.",
        )


class IncitePanic(Spell):
    """Attempt to apply Fear to all enemies."""

    def __init__(self) -> None:
        super().__init__(
            "Incite Panic",
            "Attempt to inflict Fear on every enemy.",
            school="Enchantment",
        )
        self.cost = 10
        self.subtyp = "Status"
        self.target_scope = TargetScope.ALL_ENEMIES

    def cast(self, user, target=None, **kwargs):
        result = super().cast(user, target, **kwargs)
        if user.mana.current < self.cost:
            result.message = f"{user.name} does not have enough mana.\n"
            return result
        user.mana.current -= self.cost
        generator = kwargs.get("rng") or random
        enemies = _targets(user, kwargs.get("battle_engine")) or ([target] if target else [])
        affected = 0
        for enemy in enemies:
            chance = max(0.25, min(0.80, 0.50 + (user.stats.charisma - enemy.stats.wisdom) * 0.02))
            if generator.random() < chance and _apply_status(enemy, "Fear", 3, self.name):
                affected += 1
        result.message = f"{user.name} incites panic; {affected} target(s) succumb to Fear.\n"
        return result


class ZenAccuracy(_HealerPassive):
    def __init__(self) -> None:
        super().__init__("Zen Accuracy", "Passive: Increase hit chance by 5%.")


class StaffProficiency(_HealerPassive):
    def __init__(self) -> None:
        super().__init__("Staff Proficiency", "Passive: Gain 10% accuracy and damage with Staves.")


class DelayedReaction(_HealerPassive):
    def __init__(self) -> None:
        super().__init__(
            "Delayed Reaction",
            "Passive: Critical damage may be spread over three turns.",
        )


class Meditation(Skill):
    """Store incoming damage for two turns and release it through melee."""

    def __init__(self) -> None:
        super().__init__(
            "Meditation",
            "Enter a two-turn trance, storing damage to release two-fold on the next melee attack.",
        )
        self.cost = 8
        self.subtyp = "Enhance"
        self.target_self = True

    def use(self, user, target=None, **kwargs):
        result = super().use(user, user, **kwargs)
        if user.mana.current < self.cost:
            result.message = f"{user.name} does not have enough mana.\n"
            return result
        user.mana.current -= self.cost
        user._meditation_state = {"turns": 2, "stored": 0, "ready": False}
        result.message = f"{user.name} enters a concentrating trance for two turns.\n"
        return result
