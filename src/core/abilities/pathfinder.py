"""Authored abilities for the Pathfinder base-class tree."""

from __future__ import annotations

from typing import Any

from src.core.randomness import gameplay_random as random

from ..combat.combat_result import CombatResult, CombatResultGroup
from ..combat.targeting import TargetScope
from .base import Class, Skill, Spell
from .spell_types import _simple_spell_damage


class _PathfinderPassive(Class):
    """Small passive wrapper for Pathfinder-tree mechanics."""

    def __init__(self, name: str, description: str) -> None:
        super().__init__(name=name, description=description)
        self.passive = True


class RayOfMoonlight(Spell):
    """Deal Nature damage and force a shapeshifter into its original form."""

    damage_types = ("Nature", "Holy")

    def __init__(self) -> None:
        super().__init__(
            "Ray of Moonlight",
            "Deal Nature damage and suppress an enemy's shapeshifting for this combat.",
            school="Nature",
        )
        self.cost = 8
        self.subtyp = "Nature"

    def cast(self, user, target=None, **kwargs):
        from ..classes import pathfinder

        result = super().cast(user, target, **kwargs)
        if target is None:
            result.message = "Ray of Moonlight needs a target.\n"
            return result
        if user.mana.current < self.cost:
            result.message = f"{user.name} does not have enough mana.\n"
            return result
        user.mana.current -= self.cost
        message, damage = pathfinder.spell_damage(
            user,
            target,
            self,
            damage_type="Nature",
            damage_modifier=1.20,
            rng=kwargs.get("rng"),
        )
        result.damage = damage
        result.hit = damage > 0
        if damage > 0:
            message += pathfinder.suppress_shapeshifting(target)
        result.message = message
        return result


class NullifyPoison(Spell):
    """Remove poison from one target."""

    damage_types = ("Nature",)

    def __init__(self) -> None:
        super().__init__("Nullify Poison", "Cure the target's poison effect.", school="Nature")
        self.cost = 6
        self.subtyp = "Support"

    def cast(self, user, target=None, **kwargs):
        target = target or user
        result = super().cast(user, target, **kwargs)
        if user.mana.current < self.cost:
            result.message = f"{user.name} does not have enough mana.\n"
            return result
        user.mana.current -= self.cost
        poison = target.status_effects["Poison"]
        was_poisoned = poison.active
        poison.active = False
        poison.duration = 0
        poison.extra = 0
        poison.source = ""
        result.message = (
            f"{target.name} is cured of poison.\n"
            if was_poisoned
            else f"{target.name} is not poisoned.\n"
        )
        return result


class ThornyVine(Spell):
    """Ensnare a target in a damaging living vine."""

    damage_types = ("Nature", "Earth")

    def __init__(self) -> None:
        super().__init__(
            "Thorny Vine",
            "Call forth a vine that deals Nature damage when escape attempts fail.",
            school="Nature",
        )
        self.cost = 9
        self.subtyp = "Nature"

    def cast(self, user, target=None, **kwargs):
        from ..classes import pathfinder

        result = super().cast(user, target, **kwargs)
        if target is None:
            result.message = "Thorny Vine needs a target.\n"
            return result
        if user.mana.current < self.cost:
            result.message = f"{user.name} does not have enough mana.\n"
            return result
        user.mana.current -= self.cost
        result.message = pathfinder.ensnare_with_vine(user, target)
        result.effects_applied["Physical"].append("Thorny Vine")
        return result


class PoisonStrike(Spell):
    """Partially transform and deliver a poisonous bite."""

    damage_types = ("Nature", "Poison", "Physical")

    def __init__(self) -> None:
        super().__init__(
            "Poison Strike",
            "Partially transform, biting the target for physical and poison damage.",
            school="Nature",
        )
        self.cost = 12
        self.subtyp = "Poison"

    def cast(self, user, target=None, **kwargs):
        from ..classes import pathfinder

        result = super().cast(user, target, **kwargs)
        if target is None:
            result.message = "Poison Strike needs a target.\n"
            return result
        if user.mana.current < self.cost:
            result.message = f"{user.name} does not have enough mana.\n"
            return result
        user.mana.current -= self.cost
        message, damage = pathfinder.poison_strike(
            user,
            target,
            self,
            rng=kwargs.get("rng"),
        )
        result.damage = damage
        result.hit = damage > 0
        result.message = message
        return result


class RazorTalons(_PathfinderPassive):
    def __init__(self) -> None:
        super().__init__(
            "Razor Talons",
            "Passive: Increase melee damage and Bleed damage caused by melee attacks.",
        )


class CallAnimal(Spell):
    """Call a local transient animal companion in or out of combat."""

    exploration_cast = True
    damage_types = ("Nature",)

    def __init__(self) -> None:
        super().__init__(
            "Call Animal",
            "Call a local animal companion to aid in combat for a time.",
            school="Nature",
        )
        self.cost = 10
        self.subtyp = "Calling"
        self.target_scope = TargetScope.NONE

    def cast_out(self, game_or_user):
        from ..classes import pathfinder

        user = getattr(game_or_user, "player_char", game_or_user)
        return pathfinder.call_animal(user, self.cost)

    def cast(self, user, target=None, **kwargs):
        del target, kwargs
        return self.cast_out(user)


class CreatureComforts(Spell):
    """Pacify animals during exploration or remove them from combat."""

    exploration_cast = True
    damage_types = ("Nature",)

    def __init__(self) -> None:
        super().__init__(
            "Creature Comforts",
            "Pacify nearby animals, reducing encounters or urging them from combat.",
            school="Nature",
        )
        self.cost = 10
        self.subtyp = "Support"
        self.target_scope = TargetScope.NONE

    def cast_out(self, game_or_user):
        from ..classes import pathfinder

        user = getattr(game_or_user, "player_char", game_or_user)
        return pathfinder.activate_creature_comforts(user, self.cost)

    def cast(self, user, target=None, **kwargs):
        from ..classes import pathfinder

        engine = kwargs.get("battle_engine")
        if engine is None:
            return self.cast_out(user)
        return pathfinder.pacify_combat_animals(user, engine, self.cost)


class CautiousAssault(_PathfinderPassive):
    def __init__(self) -> None:
        super().__init__(
            "Cautious Assault",
            "Passive: Increase dodge chance against counterattacks.",
        )


class UnnaturalPurge(Skill):
    """Strike unnatural enemies for additional damage."""

    def __init__(self) -> None:
        super().__init__(
            "Unnatural Purge",
            "Strike an enemy, dealing 50% more damage to unnatural creatures.",
            weapon=True,
        )
        self.cost = 10
        self.subtyp = "Offensive"

    def use(self, user, target=None, **kwargs):
        result = super().use(user, target, **kwargs)
        if target is None:
            result.message = "Unnatural Purge needs a target.\n"
            return result
        if user.mana.current < self.cost:
            result.message = f"{user.name} does not have enough mana.\n"
            return result
        user.mana.current -= self.cost
        unnatural = str(getattr(target, "enemy_typ", "")) in {
            "Slime",
            "Monster",
            "Undead",
            "Aberration",
        }
        message, hit, crit = user.weapon_damage(
            target,
            dmg_mod=1.5 if unnatural else 1.0,
            use_offhand=False,
        )
        result.hit = hit
        result.crit = crit if crit > 1 else None
        result.damage = int(getattr(user, "_last_weapon_primary_damage", 0) or 0)
        if unnatural and hit:
            message += "Unnatural Purge exploits the creature's unnatural form.\n"
        result.message = message
        return result


class BounceBack(_PathfinderPassive):
    def __init__(self) -> None:
        super().__init__("Bounce Back", "Passive: Recover from Prone more quickly.")


class SpiritStrike(Skill):
    """Attack and add spirit damage when the user has higher Wisdom."""

    def __init__(self) -> None:
        super().__init__(
            "Spirit Strike",
            "Attack and deal additional spirit damage when your Wisdom is higher.",
            weapon=True,
        )
        self.cost = 7
        self.subtyp = "Offensive"

    def use(self, user, target=None, **kwargs):
        from ..classes import pathfinder

        result = super().use(user, target, **kwargs)
        if target is None:
            result.message = "Spirit Strike needs a target.\n"
            return result
        if user.mana.current < self.cost:
            result.message = f"{user.name} does not have enough mana.\n"
            return result
        user.mana.current -= self.cost
        message, damage = pathfinder.spirit_strike(user, target)
        result.damage = damage
        result.hit = damage > 0
        result.message = message
        return result


class Conversion(_PathfinderPassive):
    def __init__(self) -> None:
        super().__init__(
            "Conversion",
            "Passive: Elemental spell damage empowers the next melee critical strike.",
        )


class VerySuperstitious(_PathfinderPassive):
    def __init__(self) -> None:
        super().__init__(
            "Very Superstitious",
            "Passive: Negative status effects may create a matching-duration damage barrier.",
        )


class PrimalTrance(Skill):
    """Charge, then automatically cast increasingly powerful elemental spells."""

    def __init__(self) -> None:
        super().__init__(
            "Primal Trance",
            "Charge for one turn, then automatically cast increasingly powerful elemental spells.",
        )
        self.cost = 18
        self.subtyp = "Enhance"
        self.charging = False
        self.charge_turns = 0
        self.charge_target = None
        self.trance_casts = 0

    def get_charge_time(self) -> int:
        return 1

    def cancel_charge(self, user) -> str:
        from ..classes import pathfinder

        self.charging = False
        self.charge_turns = 0
        self.charge_target = None
        self.trance_casts = 0
        pathfinder.end_primal_trance(user)
        return f"{user.name}'s Primal Trance ends.\n"

    def use(self, user, target=None, **kwargs):
        from ..classes import pathfinder

        if not self.charging:
            if user.mana.current < self.cost:
                return f"{user.name} does not have enough mana.\n"
            user.mana.current -= self.cost
            self.charging = True
            self.charge_turns = 1
            self.charge_target = target
            self.trance_casts = 0
            pathfinder.begin_primal_trance(user)
            return f"{user.name} sinks into a Primal Trance and begins charging.\n"
        self.charge_turns -= 1
        if self.charge_turns > 0:
            return f"{user.name} continues concentrating.\n"
        self.trance_casts += 1
        message = pathfinder.primal_trance_cast(
            user,
            self.charge_target or target,
            self.trance_casts,
            rng=kwargs.get("rng"),
        )
        if self.trance_casts >= 4 or target is None or not target.is_alive():
            return message + self.cancel_charge(user)
        self.charge_turns = 1
        self.charging = True
        return message


class FundamentalHarmony(_PathfinderPassive):
    def __init__(self) -> None:
        super().__init__(
            "Fundamental Harmony",
            "Passive: Increase damage from offensive Elemental spells.",
        )


class IntensifyElements(_PathfinderPassive):
    def __init__(self) -> None:
        super().__init__(
            "Intensify Elements",
            "Passive: Taking elemental damage empowers the next spell of that school.",
        )


class Chronology(_PathfinderPassive):
    def __init__(self) -> None:
        super().__init__(
            "Chronology",
            "Passive: Add the Intelligence modifier to initiative rolls.",
        )


class Geomancy(Spell):
    """Read useful combat information or point toward an unexplored location."""

    exploration_cast = True
    damage_types = ("Earth", "Nature")

    def __init__(self) -> None:
        super().__init__(
            "Geomancy",
            "Ask the earth for useful quest information or direction.",
            school="Earth",
        )
        self.cost = 8
        self.subtyp = "Divination"
        self.target_scope = TargetScope.NONE

    def cast(self, user, target=None, **kwargs):
        from ..classes import pathfinder

        if user.mana.current < self.cost:
            return f"{user.name} does not have enough mana.\n"
        user.mana.current -= self.cost
        return pathfinder.geomancy_combat(user, target)

    def cast_out(self, game_or_user):
        from ..classes import pathfinder

        user = getattr(game_or_user, "player_char", game_or_user)
        if user.mana.current < self.cost:
            return f"{user.name} does not have enough mana.\n"
        user.mana.current -= self.cost
        return pathfinder.geomancy_exploration(user)


class ControlZ(Spell):
    """Restore the player state from immediately before the last damaging action."""

    def __init__(self) -> None:
        super().__init__(
            "Control Z",
            "Undo the last damaging action against you as if it never happened.",
            school="Time",
        )
        self.cost = 20
        self.subtyp = "Time"
        self.target_scope = TargetScope.NONE

    def cast(self, user, target=None, **kwargs):
        from ..classes import pathfinder

        del target
        if user.mana.current < self.cost:
            return f"{user.name} does not have enough mana.\n"
        message = pathfinder.control_z(user)
        if message.startswith("Time rewinds"):
            user.mana.current = max(0, user.mana.current - self.cost)
        return message


def _hostile_targets(user: Any, battle_engine: Any | None) -> list[Any]:
    """Return the living hostile side for a player-facing area spell."""
    if battle_engine is None:
        return []
    if user is getattr(battle_engine, "player", None):
        return [member.enemy for member in battle_engine.encounter.living_members]
    return [getattr(battle_engine, "player", None)]


class NoxiousMist(Spell):
    """Blanket the hostile side in damaging, lingering poison."""

    damage_types = ("Poison",)

    def __init__(self) -> None:
        super().__init__(
            "Noxious Mist",
            "Deal Poison damage to all enemies and possibly Poison each target.",
            school="Nature",
        )
        self.cost = 14
        self.subtyp = "Poison"
        self.target_scope = TargetScope.ALL_ENEMIES

    def _affect(self, user: Any, target: Any, rng: Any) -> CombatResult:
        result = CombatResult(action=self.name, actor=user, target=target)
        message, damage = _simple_spell_damage(user, target, dmg_mod=0.75, typ="Poison")
        result.damage = damage
        result.hit = damage > 0
        if damage > 0 and not target.has_status_protection("Poison") and rng.random() < 0.45:
            poison = target.status_effects["Poison"]
            poison.active = True
            poison.duration = max(3, int(poison.duration or 0))
            poison.extra = max(max(1, damage // 5), int(poison.extra or 0))
            poison.source = self.name
            result.effects_applied["Status"].append("Poison")
            message += f"{target.name} is poisoned by the mist.\n"
        result.message = message
        return result

    def cast(self, user: Any, target: Any | None = None, **kwargs: Any):
        result = super().cast(user, target, **kwargs)
        if target is None:
            result.message = "Noxious Mist needs a target.\n"
            return result
        if user.mana.current < self.cost:
            result.message = f"{user.name} does not have enough mana.\n"
            return result
        user.mana.current -= self.cost
        return self._affect(user, target, kwargs.get("rng") or random)

    def cast_group(self, user, targets, *, battle_engine, rng=None):
        """Resolve the mist once against every selected hostile."""
        if user.mana.current < self.cost:
            return self.cast(user, target=targets[0][1] if targets else None, rng=rng)
        user.mana.current -= self.cost
        group = CombatResultGroup(
            action=self.name,
            actor_id=battle_engine.current_actor_id,
            target_scope=TargetScope.ALL_ENEMIES,
            target_ids=tuple(target_id for target_id, _target in targets),
        )
        generator = rng or random
        for target_id, target in targets:
            affected = self._affect(user, target, generator)
            affected.target_id = target_id
            group.add(affected)
        return group


class RestoringBoon(Spell):
    """Consume remaining Regrowth ticks for an amplified immediate heal."""

    def __init__(self) -> None:
        super().__init__(
            "Restoring Boon",
            "Consume remaining Regrowth healing and restore 25% more immediately.",
            school="Nature",
        )
        self.cost = 6
        self.subtyp = "Heal"
        self.target_scope = TargetScope.SELF

    def cast(self, user: Any, target: Any | None = None, **kwargs: Any):
        del target, kwargs
        result = super().cast(user, user)
        regen = user.magic_effects["Regen"]
        if not regen.active or int(regen.duration or 0) <= 0:
            result.message = "Restoring Boon requires active Regrowth.\n"
            return result
        if user.mana.current < self.cost:
            result.message = f"{user.name} does not have enough mana.\n"
            return result
        user.mana.current -= self.cost
        remaining = max(0, int(regen.extra or 0)) * max(0, int(regen.duration or 0))
        healing = int(remaining * 1.25 * user.healing_received_multiplier())
        actual = min(healing, user.health.max - user.health.current)
        user.health.current += actual
        regen.active = False
        regen.duration = 0
        regen.extra = 0
        regen.source = ""
        result.healing = actual
        result.message = f"{user.name} gathers Regrowth into a {actual} HP restoring boon.\n"
        return result


class Starfall(Spell):
    """Strike every hostile with three small falling stars."""

    damage_types = "Earth"

    def __init__(self) -> None:
        super().__init__(
            "Starfall",
            "Call three small meteors onto every enemy, each dealing Earth damage.",
            school="Nature",
        )
        self.cost = 18
        self.subtyp = "Earth"
        self.target_scope = TargetScope.ALL_ENEMIES

    def _affect(self, user: Any, target: Any) -> CombatResult:
        result = CombatResult(action=self.name, actor=user, target=target)
        result.damage = 0
        messages = []
        for _index in range(3):
            message, damage = _simple_spell_damage(user, target, dmg_mod=0.38, typ="Earth")
            messages.append(message)
            result.damage += damage
            if not target.is_alive():
                break
        result.hit = result.damage > 0
        result.extra["hits"] = len(messages)
        result.message = "".join(messages)
        return result

    def cast(self, user: Any, target: Any | None = None, **kwargs: Any):
        result = super().cast(user, target, **kwargs)
        if target is None:
            result.message = "Starfall needs a target.\n"
            return result
        if user.mana.current < self.cost:
            result.message = f"{user.name} does not have enough mana.\n"
            return result
        user.mana.current -= self.cost
        return self._affect(user, target)

    def cast_group(self, user, targets, *, battle_engine, rng=None):
        """Resolve three impacts against every selected hostile."""
        del rng
        if user.mana.current < self.cost:
            return self.cast(user, target=targets[0][1] if targets else None)
        user.mana.current -= self.cost
        group = CombatResultGroup(
            action=self.name,
            actor_id=battle_engine.current_actor_id,
            target_scope=TargetScope.ALL_ENEMIES,
            target_ids=tuple(target_id for target_id, _target in targets),
        )
        for target_id, target in targets:
            affected = self._affect(user, target)
            affected.target_id = target_id
            group.add(affected)
        return group


class ResistPoison(Spell):
    """Apply a long-lived exploration ward against Poison damage."""

    exploration_cast = True

    def __init__(self) -> None:
        super().__init__(
            "Resist Poison",
            "Increase Poison resistance by 50% for 100 steps of game time.",
            school="Nature",
        )
        self.cost = 12
        self.combat = False
        self.subtyp = "Support"

    def cast(self, user: Any, target: Any | None = None, **kwargs: Any) -> str:
        del user, target, kwargs
        return "Resist Poison must be cast outside battle.\n"

    def cast_out(self, game_or_user: Any) -> str:
        from ..classes import ability_mechanics

        user = getattr(game_or_user, "player_char", game_or_user)
        if user.mana.current < self.cost:
            return f"{user.name} does not have enough mana to cast Resist Poison.\n"
        user.mana.current -= self.cost
        ability_mechanics.apply_exploration_effect(user, "resist_poison", 100)
        return f"{user.name} gains 50% Poison resistance for 100 steps of game time.\n"


class TemporaryStasis(Spell):
    """Suspend a target and every one of its timed effects."""

    def __init__(self) -> None:
        super().__init__(
            "Temporary Stasis",
            "Prevent a target from acting for two turns while all its other timers stand still.",
            school="Time",
        )
        self.cost = 16
        self.subtyp = "Time"

    def cast(self, user: Any, target: Any | None = None, **kwargs: Any):
        result = super().cast(user, target, **kwargs)
        if target is None:
            result.message = "Temporary Stasis needs a target.\n"
            return result
        if user.mana.current < self.cost:
            result.message = f"{user.name} does not have enough mana.\n"
            return result
        if target.has_status_protection("Stun"):
            result.message = f"{target.name} resists Temporary Stasis.\n"
            return result
        user.mana.current -= self.cost
        target._temporary_stasis_turns = max(
            2,
            int(getattr(target, "_temporary_stasis_turns", 0) or 0),
        )
        stun = target.status_effects["Stun"]
        stun.active = True
        stun.duration = max(2, int(stun.duration or 0))
        stun.source = self.name
        result.hit = True
        result.effects_applied["Status"].append("Stun")
        result.message = f"{target.name} is suspended outside time.\n"
        return result


class LunarRend(Skill):
    """Open a bleeding wound with a transformed weapon strike."""

    def __init__(self) -> None:
        super().__init__(
            "Lunar Rend",
            "Werewolf only: strike for 140% weapon damage and inflict Bleed.",
            weapon=True,
        )
        self.cost = 12
        self.subtyp = "Offensive"

    def use(self, user: Any, target: Any | None = None, **kwargs: Any):
        del kwargs
        from ..classes import lycan, transformation

        result = super().use(user, target)
        if target is None:
            result.message = "Lunar Rend needs a target.\n"
            return result
        if not lycan.is_transformed(user) or transformation.permanent_class_name(user) != "Lycan":
            result.message = "Lunar Rend requires the Werewolf form.\n"
            return result
        if user.mana.current < self.cost:
            result.message = f"{user.name} does not have enough mana.\n"
            return result
        user.mana.current -= self.cost
        before = int(target.health.current)
        message, hit, critical = user.weapon_damage(target, dmg_mod=1.40, use_offhand=False)
        damage = max(0, before - int(target.health.current))
        result.hit = hit
        result.crit = critical if critical > 1 else None
        result.damage = damage
        if hit and damage > 0:
            bleed = target.physical_effects["Bleed"]
            bleed.active = True
            bleed.duration = max(3, int(bleed.duration or 0))
            bleed.extra = max(max(1, damage // 6), int(bleed.extra or 0))
            bleed.source = self.name
            result.effects_applied["Physical"].append("Bleed")
            message += f"{target.name} bleeds beneath the moon.\n"
        result.message = message
        return result


class PrimalPractice(Class):
    """Adopt a short offensive practice suited to the current form."""

    def __init__(self) -> None:
        super().__init__(
            "Primal Practice",
            "Raise Attack while transformed, or Magic while in natural form, for three turns.",
        )
        self.cost = 8
        self.subtyp = "Enhance"
        self.target_scope = TargetScope.SELF

    def use(self, user: Any, target: Any | None = None, **kwargs: Any):
        del target, kwargs
        from ..classes import transformation

        result = super().use(user, user)
        if user.mana.current < self.cost:
            result.message = f"{user.name} does not have enough mana.\n"
            return result
        user.mana.current -= self.cost
        stat_name = "Attack" if transformation.is_transformed(user) else "Magic"
        effect = user.stat_effects[stat_name]
        effect.active = True
        effect.duration = max(int(effect.duration or 0), 3)
        effect.extra = max(int(effect.extra or 0), 10)
        effect.source = self.name
        result.effects_applied["Stat"].append(stat_name)
        result.hit = True
        result.message = f"{user.name}'s Primal Practice raises {stat_name} by 10.\n"
        return result


class DragonFang(Skill):
    """Combine a Werewolf strike with Dragon Essence fire."""

    def __init__(self) -> None:
        super().__init__(
            "Dragon Fang",
            "Werewolf and Dragon Essence only: strike, then deal additional Fire damage.",
            weapon=True,
        )
        self.cost = 15
        self.subtyp = "Offensive"

    def use(self, user: Any, target: Any | None = None, **kwargs: Any):
        del kwargs
        from ..classes import lycan, promotion_kits, transformation

        result = super().use(user, target)
        if target is None:
            result.message = "Dragon Fang needs a target.\n"
            return result
        if not lycan.is_transformed(user) or transformation.permanent_class_name(user) != "Lycan":
            result.message = "Dragon Fang requires the Werewolf form.\n"
            return result
        if not promotion_kits.lycan_control_state(user).get("dragon_essence"):
            result.message = "Dragon Fang requires Dragon Essence.\n"
            return result
        if user.mana.current < self.cost:
            result.message = f"{user.name} does not have enough mana.\n"
            return result
        user.mana.current -= self.cost
        before = int(target.health.current)
        message, hit, critical = user.weapon_damage(target, dmg_mod=1.20, use_offhand=False)
        result.hit = hit
        result.crit = critical if critical > 1 else None
        result.damage = max(0, before - int(target.health.current))
        if hit and target.is_alive():
            fire_message, fire_damage = _simple_spell_damage(
                user,
                target,
                dmg_mod=0.45,
                typ="Fire",
            )
            message += fire_message
            result.damage += fire_damage
        result.message = message
        return result


class CenterBeast(Skill):
    """Prepare a controlled defensive response to the next Frenzy check."""

    def __init__(self) -> None:
        super().__init__(
            "Center the Beast",
            "Werewolf only: defend for two turns and halve the next Frenzy trigger chance.",
        )
        self.cost = 10
        self.subtyp = "Defensive"
        self.target_scope = TargetScope.SELF

    def use(self, user: Any, target: Any | None = None, **kwargs: Any):
        del target, kwargs
        from ..classes import lycan, promotion_kits, transformation

        result = super().use(user, user)
        if not lycan.is_transformed(user) or transformation.permanent_class_name(user) != "Lycan":
            result.message = "Center the Beast requires the Werewolf form.\n"
            return result
        if user.mana.current < self.cost:
            result.message = f"{user.name} does not have enough mana.\n"
            return result
        user.mana.current -= self.cost
        promotion_kits.combat_state(user)["center_beast_ready"] = True
        result.message = user.enter_defensive_stance(duration=2, source=self.name)
        result.message += "The next Frenzy check is met with centered will.\n"
        result.hit = True
        return result


class GrovePulse(Spell):
    """Deal Nature damage and recycle part of it into life and Harmony."""

    damage_types = ("Nature",)

    def __init__(self) -> None:
        super().__init__(
            "Grove Pulse",
            "Deal Nature damage, heal for half the damage, and represent one fitting aspect.",
            school="Nature",
        )
        self.cost = 16
        self.subtyp = "Nature"

    def cast(self, user: Any, target: Any | None = None, **kwargs: Any):
        del kwargs
        from ..classes import promotion_kits

        result = super().cast(user, target)
        if target is None:
            result.message = "Grove Pulse needs a target.\n"
            return result
        if user.mana.current < self.cost:
            result.message = f"{user.name} does not have enough mana.\n"
            return result
        user.mana.current -= self.cost
        message, damage = _simple_spell_damage(user, target, dmg_mod=0.95, typ="Nature")
        healing = min(
            user.health.max - user.health.current,
            int(damage * 0.50 * user.healing_received_multiplier()),
        )
        user.health.current += healing
        if healing:
            user._emit_healing_event(healing, source=self.name)
        poisoned = target.status_effects.get("Poison")
        aspect = "Venom" if poisoned is not None and poisoned.active else "Growth"
        message += promotion_kits.add_aspect(user, aspect)
        message += f"Grove Pulse restores {healing} HP.\n"
        result.damage = damage
        result.healing = healing
        result.hit = damage > 0
        result.message = message
        return result


class Tephra(_PathfinderPassive):
    """Cause Vulcanize to scatter damaging volcanic debris."""

    def __init__(self) -> None:
        super().__init__(
            "Tephra",
            "Passive: Vulcanize scatters debris that damages other nearby enemies.",
        )


class AccessStorage(Skill):
    """Move one item between inventory and storage during exploration."""

    exploration_cast = True

    def __init__(self) -> None:
        super().__init__(
            "Access Storage",
            "Move one item between dungeon inventory and storage for MP equal to its weight.",
        )
        self.combat = False
        self.subtyp = "Support"
        self.target_scope = TargetScope.NONE

    def use_out(
        self,
        game_or_user: Any,
        *,
        item_name: str | None = None,
        retrieve: bool = True,
    ) -> str:
        user = getattr(game_or_user, "player_char", game_or_user)
        if not item_name:
            return "Access Storage requires an item selection.\n"
        source = user.storage if retrieve else user.inventory
        stack = source.get(item_name, []) if isinstance(source, dict) else []
        if not stack:
            location = "storage" if retrieve else "inventory"
            return f"{item_name} is not in {location}.\n"
        item = stack[0]
        cost = max(1, int(getattr(item, "weight", 1) or 1))
        if user.mana.current < cost:
            return f"{user.name} needs {cost} mana to move {item_name}.\n"
        user.mana.current -= cost
        source[item_name].remove(item)
        if not source[item_name]:
            del source[item_name]
        destination = user.inventory if retrieve else user.storage
        destination.setdefault(item_name, []).append(item)
        direction = "retrieves" if retrieve else "stores"
        return f"{user.name} {direction} {item_name} for {cost} mana.\n"

    def cast_out(
        self,
        game_or_user: Any,
        *,
        item_name: str | None = None,
        retrieve: bool = True,
    ) -> str:
        """Expose the selection-driven action to exploration ability menus."""
        return self.use_out(
            game_or_user,
            item_name=item_name,
            retrieve=retrieve,
        )

    def use(self, user: Any, target: Any | None = None, **kwargs: Any) -> str:
        del target
        if kwargs.get("battle_engine") is not None:
            return "Access Storage cannot be used in combat.\n"
        return self.use_out(
            user,
            item_name=kwargs.get("item_name"),
            retrieve=bool(kwargs.get("retrieve", True)),
        )


class SilentLucidity(_PathfinderPassive):
    """Permit time and divination spellcasting while asleep."""

    def __init__(self) -> None:
        super().__init__(
            "Silent Lucidity",
            "Passive: While asleep, you may still cast Time and Divination spells.",
        )
