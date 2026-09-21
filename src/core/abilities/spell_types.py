"""Spell mechanics, spell subtypes, and specialized spell implementations."""

from __future__ import annotations

from typing import TYPE_CHECKING

from src.core.randomness import gameplay_random as random

from ..combat.combat_result import CombatResult, CombatResultGroup
from ..combat.reactions import execute_reaction, reaction_result
from ..combat.targeting import TargetLossPolicy, TargetScope
from ..constants import DAMAGE_VARIANCE_HIGH, DAMAGE_VARIANCE_LOW
from ..events.event_bus import combat_event_context
from .base import Skill, Spell
from .enemy import Counterspell

if TYPE_CHECKING:
    from typing import Any

    from ..character import Character


# Spell types
class Attack(Spell):
    def __init__(
        self,
        name: str,
        description: str,
        cost: int,
        dmg_mod: float,
        crit: int,
    ) -> None:
        super().__init__(name, description)
        self.cost = cost
        self.dmg_mod = dmg_mod
        self.crit = crit
        self.turns = None

    @reaction_result
    def cast(
        self,
        caster: Character,
        target: Character | None = None,
        cover: bool = False,
        special: bool = False,
        fam: bool = False,
    ) -> str:
        cast_message = ""
        if not (
            special
            or fam
            or (caster.cls.name == "Wizard" and caster.class_effects["Power Up"].active)
        ):
            caster.mana.current -= self.cost
        if any([target.magic_effects["Ice Block"].active, target.tunnel]):
            return "It has no effect.\n"
        reflect = target.magic_effects["Reflect"].active
        spell_mod = caster.check_mod("magic", enemy=target)
        contact = caster.resolve_contact(
            target,
            typ="magic",
            always_hit=target.incapacitated(),
            rng=random,
        )
        if not contact.hit and not reflect:
            if contact.attribution is not None and contact.attribution.value == "dodge":
                cast_message += f"{target.name} dodged the {self.name} and was unhurt.\n"
            else:
                cast_message += f"The spell misses {target.name}.\n"
        else:
            if reflect:
                target = caster
                cast_message += f"{self.name} is reflected back at {caster.name}!\n"
            # Calculate base damage first
            crit = 1
            if not random.randint(0, self.crit):
                crit = 2
            crit_per = random.uniform(1, crit)
            damage = int(self.dmg_mod * spell_mod * crit_per)
            # Apply defenses and reductions
            hit, message, damage = target.handle_defenses(caster, damage, cover, typ="Magic")
            cast_message += message
            hit, message, damage = target.damage_reduction(damage, caster, typ=self.subtyp)
            cast_message += message
            if hit:
                if (
                    caster.cls.name == "Archbishop"
                    and caster.class_effects["Power Up"].active
                    and self.subtyp == "Holy"
                ):
                    damage = int(damage * 1.25)
                if damage < 0:
                    target.health.current -= damage
                    cast_message += f"{target.name} absorbs {self.subtyp} and is healed for {abs(damage)} health.\n"
                else:
                    variance = random.uniform(DAMAGE_VARIANCE_LOW, DAMAGE_VARIANCE_HIGH)
                    damage = int(damage * variance)
                    if damage <= 0:
                        cast_message += "The spell was ineffective and does no damage.\n"
                        damage = 0
                    elif random.randint(0, target.stats.con // 2) > random.randint(
                        (caster.stats.intel * crit) // 2, (caster.stats.intel * crit)
                    ):
                        damage //= 2
                        if damage > 0:
                            cast_message += f"{target.name} shrugs off the spell and only receives half of the damage.\n"
                            damage_msg = (
                                f"{caster.name} damages {target.name} for {damage} hit points"
                            )
                            if crit > 1:
                                damage_msg += " (Critical hit!)"
                            cast_message += damage_msg + ".\n"
                        else:
                            cast_message += "The spell was ineffective and does no damage.\n"
                    else:
                        damage_msg = f"{caster.name} damages {target.name} for {damage} hit points"
                        if crit > 1:
                            damage_msg += " (Critical hit!)"
                        cast_message += damage_msg + ".\n"
                    try:
                        from ..classes import promotion_kits

                        damage, block_message = promotion_kits.apply_spell_block(
                            target,
                            caster,
                            damage,
                            spell=self,
                        )
                        cast_message += block_message
                        damage, shield_message, _fully_absorbed = (
                            promotion_kits.absorb_novel_shield(
                                target,
                                damage,
                                source="reflected" if reflect else "spell",
                            )
                        )
                        cast_message += shield_message
                    except Exception:
                        pass
                    if crit > 1:
                        try:
                            from ..classes import healer

                            damage, delayed_message = healer.delay_critical_damage(
                                target,
                                damage,
                            )
                            cast_message += delayed_message
                        except Exception:
                            pass
                    target.health.current -= damage
                    caster._emit_damage_event(
                        target,
                        damage,
                        damage_type=self.subtyp,
                        is_critical=(crit > 1),
                        ability_name=self.name,
                        attack_source="spell",
                        source="spell",
                    )
                    if target.is_alive() and damage > 0 and not reflect:
                        cast_message += self.special_effect(caster, target, damage, crit)
                    elif target.is_alive() and damage > 0 and reflect:
                        cast_message += self.special_effect(caster, caster, damage, crit)
                if "Counterspell" in target.spellbook["Spells"] and not random.randint(0, 4):
                    counterspell = execute_reaction(
                        "counterspell",
                        target,
                        lambda: Counterspell().use(target, caster),
                    )
                    if counterspell:
                        cast_message += f"{target.name} uses Counterspell.\n"
                        cast_message += counterspell
            if (
                caster.cls.name == "Wizard"
                and caster.class_effects["Power Up"].active
                and damage > 0
            ):
                cast_message += f"{caster.name} regens {damage} mana.\n"
                caster.mana.current += damage
                if caster.mana.current > caster.mana.max:
                    caster.mana.current = caster.mana.max
        return cast_message


class HolySpell(Spell):
    def __init__(self, name: str, description: str, cost: int, dmg_mod: float, crit: int) -> None:
        super().__init__(name, description)
        self.cost = cost
        self.dmg_mod = dmg_mod
        self.crit = crit
        self.subtyp = "Holy"


class SupportSpell(Spell):
    def __init__(self, name: str, description: str, cost: int) -> None:
        super().__init__(name, description)
        self.cost = cost
        self.subtyp = "Support"


class DeathSpell(Spell):
    def __init__(self, name: str, description: str, cost: int) -> None:
        super().__init__(name, description)
        self.cost = cost
        self.subtyp = "Death"


class StatusSpell(Spell):
    def __init__(self, name: str, description: str, cost: int) -> None:
        super().__init__(name, description)
        self.cost = cost
        self.subtyp = "Status"


class HealSpell(Spell):
    """
    Base class for all heal spells

    Attributes:
        heal(float): base heal amount equal to the percentage of the target's health
        - Heal 1: 0.3 (pro 1 lvl 1)
        - Heal 2: 0.45 (pro 1 lvl 26)
        - Heal 3: 0.6 (pro 3 lvl 1)
        - Hydration: 0.3 (pro 2 lvl 9)
        - Regen 1: 0.2 (pro 1 lvl 8)
        - Regen 2: 0.3 (pro 2 lvl 1)
        - Regen 3: 0.4 (pro 3 lvl 7)
    """

    def __init__(self, name: str, description: str, cost: int, heal: int, crit: int) -> None:
        super().__init__(name, description)
        self.cost = cost
        self.heal = heal
        self.crit = crit
        self.turns = 0
        self.subtyp = "Heal"
        self.combat = False

    def _apply_instant_healing(
        self,
        caster: Character,
        target: Character,
        heal: int,
    ) -> int:
        """Apply a rolled heal after target modifiers and return actual healing."""
        try:
            from ..classes import astromancer

            heal = int(heal * (1.0 + astromancer.threaded_bonus(caster, "output")))
        except Exception:
            pass
        try:
            from ..classes import promotion_kits

            heal = int(heal * promotion_kits.benediction_healing_multiplier(caster))
        except Exception:
            pass
        heal = int(heal * target.healing_received_multiplier())
        actual_heal = max(0, min(heal, target.health.max - target.health.current))
        target.health.current += actual_heal
        caster._emit_healing_event(actual_heal, source=self.name)
        try:
            from ..classes import promotion_kits

            promotion_kits._message(
                caster,
                promotion_kits.record_healing_done(
                    caster,
                    actual_heal,
                    source=self.name,
                    target=target,
                ),
            )
        except Exception:
            pass
        try:
            from ..classes import healer

            healer.apply_safeguarding(caster, target, self.name)
        except Exception:
            pass
        return actual_heal

    def cast(
        self,
        caster: Character,
        target: Character | None = None,
        cover: bool = False,
        special: bool = False,
        fam: bool = False,
    ) -> str:
        """Heal calculation while in combat"""
        cast_message = ""
        if not fam:
            target = caster
        if not (special or fam):
            caster.mana.current -= self.cost
        crit = 1
        heal_mod = caster.check_mod("heal")
        heal = int(
            (random.randint(target.health.max // 2, target.health.max) + heal_mod) * self.heal
        )
        if self.turns:
            self.hot(target, heal)
        else:
            if not random.randint(0, self.crit):
                cast_message += "Critical Heal!\n"
                crit = 2
            crit_per = random.uniform(1, crit)
            heal = int(heal * crit_per)
            actual_heal = self._apply_instant_healing(caster, target, heal)
            cast_message += f"{caster.name} heals {target.name} for {actual_heal} hit points.\n"
            if target.health.current >= target.health.max:
                target.health.current = target.health.max
                cast_message += f"{target.name} is at full health.\n"
        return cast_message


class MovementSpell(Spell):
    def __init__(self, name: str, description: str, cost: int) -> None:
        super().__init__(name, description)
        self.cost = cost
        self.subtyp = "Movement"


class IllusionSpell(Spell):
    """
    subtyp: the subtype of these abilities is 'Illusion', meaning they rely on deception
    """

    def __init__(self, name: str, description: str, cost: int) -> None:
        super().__init__(name, description)
        self.cost = cost
        self.subtyp = "Illusion"


def _inventory_count(character: Character, item_name: str) -> int:
    return len(getattr(character, "inventory", {}).get(item_name, []) or [])


def _consume_inventory_item(character: Character, item_name: str) -> bool:
    stack = getattr(character, "inventory", {}).get(item_name, [])
    if not stack:
        return False
    character.modify_inventory(stack[0], subtract=True)
    return True


def _simple_spell_damage(
    caster: Character, target: Character, *, dmg_mod: float, typ: str
) -> tuple[str, int]:
    if target is None:
        return "There is no target.\n", 0
    if target.magic_effects["Ice Block"].active or target.tunnel:
        return "It has no effect.\n", 0
    guaranteed = bool(getattr(caster, "_twist_fate_success", False))
    if guaranteed:
        caster._twist_fate_success = False
    contact = caster.resolve_contact(
        target,
        typ="magic",
        always_hit=guaranteed or target.incapacitated(),
        rng=random,
    )
    if not contact.hit:
        if contact.attribution is not None and contact.attribution.value == "dodge":
            return f"{target.name} dodged the spell and was unhurt.\n", 0
        return f"The spell misses {target.name}.\n", 0
    spell_mod = caster.check_mod("magic", enemy=target)
    damage = max(1, int(spell_mod * dmg_mod))
    hit, msg, damage = target.damage_reduction(damage, caster, typ=typ)
    if not hit:
        return msg, 0
    variance = random.uniform(DAMAGE_VARIANCE_LOW, DAMAGE_VARIANCE_HIGH)
    damage = max(0, int(damage * variance))
    try:
        from ..classes import promotion_kits

        damage, shield_message, _fully_absorbed = promotion_kits.absorb_novel_shield(
            target,
            damage,
            source="spell",
        )
        msg += shield_message
    except Exception:
        pass
    target.health.current -= damage
    return (
        msg + f"{caster.name} damages {target.name} for {damage} hit points.\n",
        damage,
    )


class _ReagentSpell(Spell):
    required_items: tuple[str, ...] = ()

    def _consume_reagents(self, user: Character) -> str | None:
        missing = [item for item in self.required_items if _inventory_count(user, item) <= 0]
        if missing:
            return f"{user.name} needs {', '.join(missing)} to cast {self.name}.\n"
        for item in self.required_items:
            _consume_inventory_item(user, item)
        return None

    def _consume_reagent(self, user: Character, item_name: str) -> str | None:
        if _inventory_count(user, item_name) <= 0:
            return f"{user.name} needs {item_name} to cast {self.name}.\n"
        _consume_inventory_item(user, item_name)
        return None


class PlantSeeds(_ReagentSpell):
    reagent_effects = ("Acorn", "Vine Seed", "Fungus Spore")

    def __init__(self):
        super().__init__(
            "Plant Seeds",
            "Spread seeds of life around the battlefield; each seed changes the growth.",
            school="Nature",
        )
        self.cost = 0
        self.subtyp = "Earth"

    def cast(self, user: Character, target: Character | None = None, **kwargs: Any) -> str:
        super().cast(user, target, **kwargs)
        user.mana.current -= self.cost
        if target is None:
            return "The seeds find no soil.\n"
        selected = kwargs.get("reagent") or kwargs.get("seed")
        if selected is None:
            selected = next(
                (name for name in self.reagent_effects if _inventory_count(user, name) > 0),
                None,
            )
        if selected not in self.reagent_effects:
            return f"{selected or 'That reagent'} cannot be planted with Plant Seeds.\n"
        failed = self._consume_reagent(user, selected)
        if failed:
            return failed

        if selected == "Acorn":
            msg, damage = _simple_spell_damage(user, target, dmg_mod=1.15, typ="Earth")
            if damage > 0 and not target.has_status_protection("Stun"):
                target.apply_stun(1, source="Plant Seeds", applier=user)
                msg += f"A mighty oak bashes {target.name} senseless.\n"
            return msg or f"A mighty oak erupts beneath {target.name}.\n"

        if selected == "Vine Seed":
            target.physical_effects["Prone"].active = True
            target.physical_effects["Prone"].duration = max(
                target.physical_effects["Prone"].duration, 3
            )
            return f"Fast-growing vines strangle {target.name}, restricting movement.\n"

        if target.has_status_protection("Poison"):
            return f"Deadly mushroom caps bloom, but {target.name} resists the poison.\n"
        target.status_effects["Poison"].active = True
        target.status_effects["Poison"].duration = max(target.status_effects["Poison"].duration, 4)
        target.status_effects["Poison"].extra = max(
            int(target.status_effects["Poison"].extra or 0),
            max(1, user.check_mod("magic", enemy=target) // 4),
        )
        return f"Deadly mushroom caps bloom around {target.name}, spreading poison.\n"


class TreeOfLife(Spell):
    def __init__(self):
        super().__init__(
            "Tree of Life",
            "Transform into a giant oak tree for 3 turns, becoming a living bastion.",
            school="Nature",
        )
        self.cost = 28
        self.subtyp = "Support"

    def cast(self, user: Character, target: Character | None = None, **kwargs: Any) -> str:
        from ..classes import archdruid

        super().cast(user, user, **kwargs)
        if not archdruid.mastery_unlocked(user, "Growth"):
            return f"{user.name} has not mastered Growth attunement.\n"
        user.mana.current -= self.cost
        tree = user.magic_effects["Tree of Life"]
        tree.active = True
        tree.duration = max(tree.duration, 3)
        return f"{user.name} transforms into a giant oak tree.\n"


class VilePotion(_ReagentSpell):
    required_items = ("Hemlock Root", "Fungus Spore")

    def __init__(self):
        super().__init__(
            "Vile Potion",
            "Imbibe rot and spew putrid vomitus at a foe.",
            school="Nature",
        )
        self.cost = 0
        self.subtyp = "Poison"

    def cast(self, user: Character, target: Character | None = None, **kwargs: Any) -> str:
        super().cast(user, target, **kwargs)
        failed = self._consume_reagents(user)
        if failed:
            return failed
        if target is None:
            return "The potion spills harmlessly.\n"
        health_cost = max(1, int(user.health.max * 0.10))
        user.health.current = max(1, user.health.current - health_cost)
        msg = f"{user.name} chokes down rot and loses {health_cost} HP.\n"
        damage_msg, damage = _simple_spell_damage(user, target, dmg_mod=1.0, typ="Poison")
        msg += damage_msg
        if damage > 0 and not target.has_status_protection("Poison") and random.random() < 0.65:
            target.status_effects["Poison"].active = True
            target.status_effects["Poison"].duration = max(
                target.status_effects["Poison"].duration, 4
            )
            target.status_effects["Poison"].extra = max(
                target.status_effects["Poison"].extra, max(1, damage // 3)
            )
            msg += f"{target.name} is poisoned.\n"
        return msg


class Foretell(Spell):
    def __init__(self):
        super().__init__("Foretell", "Read the enemy's next likely action.", school="Time")
        self.cost = 16
        self.subtyp = "Time"

    def cast(self, user: Character, target: Character | None = None, **kwargs: Any) -> str:

        super().cast(user, target, **kwargs)
        engine = kwargs.get("battle_engine")
        if engine is None:
            return "There is no combat thread to foretell.\n"
        user.mana.current -= self.cost
        enemy = target
        if enemy is None:
            focused = getattr(engine, "_focused_enemy", None)
            enemy = focused() if callable(focused) else None
        if enemy is None:
            return "There is no hostile thread to foretell.\n"
        action = "Attack"
        stack = getattr(enemy, "action_stack", []) or []
        if stack:
            entry = stack[0]
            if isinstance(entry, dict):
                action = str(entry.get("ability") or entry.get("action") or action)
            else:
                action = str(entry)
        return f"{user.name} foresees {enemy.name}'s next action: {action}.\n"


class Rewind(Spell):
    def __init__(self):
        super().__init__(
            "Rewind",
            "Return combat to the previous player choice point.",
            school="Time",
        )
        self.cost = 40
        self.subtyp = "Time"

    def cast(self, user: Character, target: Character | None = None, **kwargs: Any) -> str:
        from ..classes import ability_mechanics

        super().cast(user, target, **kwargs)
        engine = kwargs.get("battle_engine")
        if engine is None:
            return "There is no combat thread to rewind.\n"
        message = ability_mechanics.restore_rewind_snapshot(engine)
        if message.startswith("No "):
            return message
        user.mana.current = max(0, user.mana.current - self.cost)
        return message


class TwistFate(Spell):
    def __init__(self):
        super().__init__("Twist Fate", "Guarantee the success of your next action.", school="Time")
        self.cost = 18
        self.subtyp = "Time"

    def cast(self, user: Character, target: Character | None = None, **kwargs: Any) -> str:
        super().cast(user, user, **kwargs)
        user.mana.current -= self.cost
        user._twist_fate_success = True
        return f"Fate bends toward {user.name}'s next action.\n"


class Wormhole(Spell):
    def __init__(self):
        super().__init__("Wormhole", "Send a spell two turns into the future.", school="Time")
        self.cost = 10
        self.subtyp = "Time"

    def cast(self, user: Character, target: Character | None = None, **kwargs: Any) -> str:
        super().cast(user, target, **kwargs)
        engine = kwargs.get("battle_engine")
        spell_name = kwargs.get("spell_name") or kwargs.get("choice")
        user.mana.current -= self.cost
        if engine is None:
            return f"{user.name} opens a wormhole, but it collapses without a battle thread.\n"
        spellbook = user.spellbook.get("Spells", {})
        if not spell_name:
            candidates = [
                name
                for name, spell in spellbook.items()
                if name != self.name and getattr(spell, "subtyp", "") != "Support"
            ]
            spell_name = candidates[0] if candidates else None
        if not spell_name or spell_name not in spellbook or spell_name == self.name:
            return "No spell is shaped into the wormhole.\n"
        spell = spellbook[spell_name]
        if user.mana.current < getattr(spell, "cost", 0):
            return f"{user.name} does not have enough mana to send {spell_name} through time.\n"
        user.mana.current -= getattr(spell, "cost", 0)
        target_member = engine._member_for_character(target)
        engine.delayed_spells.append(
            {
                "turns": 2,
                "caster": user,
                "spell": spell,
                "owner_id": engine._actor_id_for(user),
                "target_id": target_member.combatant_id if target_member else None,
                "skip_next_owner_tick": True,
            }
        )
        return f"{user.name} sends {spell_name} two turns into the future.\n"


class Volitation(MovementSpell):
    def __init__(self):
        super().__init__("Volitation", "Float above hazardous ground for a short time.", 16)

    def cast(self, user: Character, target: Character | None = None, **kwargs: Any) -> str:
        return self.cast_out(user)

    def cast_out(self, game_or_user) -> str:
        from ..classes import ability_mechanics, promotion_kits

        user = getattr(game_or_user, "player_char", game_or_user)
        cost, route_message = promotion_kits.wayfinding_cost(
            user,
            self.cost,
            mapping_progress=promotion_kits.level_mapping_progress(user),
        )
        if user.mana.current < cost:
            return f"{user.name} does not have enough mana to use Volitation.\n"
        user.mana.current -= cost
        ability_mechanics.apply_exploration_effect(user, "volitation", 40)
        return route_message + f"{user.name} rises gently above the ground.\n"


class EnterWall(MovementSpell):
    def __init__(self):
        super().__init__("Enter Wall", "Pass through ordinary walls for a few steps.", 75)

    def cast(self, user: Character, target: Character | None = None, **kwargs: Any) -> str:
        return "Enter Wall has no combat use.\n"

    def cast_out(self, game_or_user) -> str:
        from ..classes import ability_mechanics, promotion_kits

        user = getattr(game_or_user, "player_char", game_or_user)
        cost, route_message = promotion_kits.wayfinding_cost(
            user,
            self.cost,
            mapping_progress=promotion_kits.level_mapping_progress(user),
        )
        if user.mana.current < cost:
            return f"{user.name} does not have enough mana to use Enter Wall.\n"
        user.mana.current -= cost
        ability_mechanics.apply_exploration_effect(user, "enter_wall", 8)
        return route_message + f"{user.name} slips partly into the stone.\n"


class Invisibility(IllusionSpell):
    def __init__(self):
        super().__init__("Invisibility", "Fade from sight for surprise and defense.", 18)

    def cast(self, user: Character, target: Character | None = None, **kwargs: Any) -> str:
        del target, kwargs
        from ..classes import ability_mechanics

        user.mana.current -= self.cost
        ability_mechanics.apply_exploration_effect(user, "invisibility", 30)
        user._combat_concealed = True
        return f"{user.name} fades from sight and becomes concealed.\n"

    def cast_out(self, game_or_user) -> str:
        from ..classes import ability_mechanics

        user = getattr(game_or_user, "player_char", game_or_user)
        user.mana.current -= self.cost
        ability_mechanics.apply_exploration_effect(user, "invisibility", 30)
        return f"{user.name} fades from sight.\n"


class _ResistElement(Spell):
    element = "Fire"

    def __init__(self, name: str, element: str):
        super().__init__(
            name, f"Raise {element} resistance for several turns.", school="Abjuration"
        )
        self.cost = 12
        self.subtyp = "Support"
        self.element = element

    def cast(self, user: Character, target: Character | None = None, **kwargs: Any) -> str:
        super().cast(user, user, **kwargs)
        user.mana.current -= self.cost
        effect = user.magic_effects[f"Resist {self.element}"]
        effect.active = True
        try:
            from ..progression import has_talent

            studied = has_talent(user, "inquisitor.warding-studies")
        except (AttributeError, KeyError, TypeError, ValueError):
            studied = False
        effect.duration = max(effect.duration, 7 if studied else 5)
        effect.extra = max(float(effect.extra or 0), 0.5)
        return f"{user.name} gains resistance to {self.element.lower()}.\n"


class ResistFire(_ResistElement):
    def __init__(self):
        super().__init__("Resist Fire", "Fire")


class ResistIce(_ResistElement):
    def __init__(self):
        super().__init__("Resist Ice", "Ice")


class ResistElectric(_ResistElement):
    def __init__(self):
        super().__init__("Resist Electric", "Electric")


class ResistWater(_ResistElement):
    def __init__(self):
        super().__init__("Resist Water", "Water")


class ResistEarth(_ResistElement):
    def __init__(self):
        super().__init__("Resist Earth", "Earth")


class ResistWind(_ResistElement):
    def __init__(self):
        super().__init__("Resist Wind", "Wind")


class ResistShadow(Spell):
    """Long-lived exploration ward against Shadow damage."""

    exploration_cast = True

    def __init__(self):
        super().__init__(
            "Resist Shadow",
            ("Increase Shadow resistance outside battle for 100 steps of game time."),
            school="Abjuration",
        )
        self.cost = 15
        self.combat = False
        self.subtyp = "Support"

    def cast(
        self,
        user: Character,
        target: Character | None = None,
        **kwargs: Any,
    ) -> str:
        return "Resist Shadow must be cast outside battle.\n"

    def cast_out(self, game_or_user) -> str:
        from ..classes import ability_mechanics

        user = getattr(game_or_user, "player_char", game_or_user)
        if user.mana.current < self.cost:
            return f"{user.name} does not have enough mana to cast Resist Shadow.\n"
        user.mana.current -= self.cost
        ability_mechanics.apply_exploration_effect(
            user,
            "resist_shadow",
            100,
        )
        return f"{user.name} gains 50% Shadow resistance for 100 steps of game time.\n"


class ResistHoly(Spell):
    """Long-lived exploration ward against Holy damage."""

    exploration_cast = True

    def __init__(self):
        super().__init__(
            "Resist Holy",
            "Increase Holy resistance outside battle for 100 steps of game time.",
            school="Abjuration",
        )
        self.cost = 15
        self.combat = False
        self.subtyp = "Support"

    def cast(
        self,
        user: Character,
        target: Character | None = None,
        **kwargs: Any,
    ) -> str:
        return "Resist Holy must be cast outside battle.\n"

    def cast_out(self, game_or_user) -> str:
        from ..classes import ability_mechanics

        user = getattr(game_or_user, "player_char", game_or_user)
        if user.mana.current < self.cost:
            return f"{user.name} does not have enough mana to cast Resist Holy.\n"
        user.mana.current -= self.cost
        ability_mechanics.apply_exploration_effect(user, "resist_holy", 100)
        return f"{user.name} gains 50% Holy resistance for 100 steps of game time.\n"


class HallowedGround(Spell):
    """Three-turn holy field that harms foes and restores its caster."""

    def __init__(self):
        super().__init__(
            "Hallowed Ground",
            (
                "The ground around you glows with sacred light, damaging "
                "nearby enemies and healing you for 3 turns."
            ),
            school="Holy",
        )
        self.cost = 20
        self.subtyp = "Holy"
        self.target_scope = TargetScope.ALL_ENEMIES
        self.target_loss_policy = TargetLossPolicy.SNAPSHOT_ROSTER

    @staticmethod
    def _apply_field(target: Character, *, mode: str, amount: int) -> None:
        effect = target.magic_effects["Hallowed Ground"]
        effect.active = True
        effect.duration = max(3, int(effect.duration or 0))
        prior = effect.extra if isinstance(effect.extra, dict) else {}
        effect.extra = {
            "mode": mode,
            "amount": max(amount, int(prior.get("amount", 0) or 0)),
        }
        effect.source = "Hallowed Ground"

    def cast(
        self,
        user: Character,
        target: Character | None = None,
        **kwargs: Any,
    ) -> str:
        from ..classes import paladin

        super().cast(user, target, **kwargs)
        user.mana.current -= self.cost
        targets = list(kwargs.get("targets") or ())
        if target is not None:
            targets.append(target)
        unique_targets = []
        seen = set()
        for candidate in targets:
            if candidate is None or candidate is user or id(candidate) in seen:
                continue
            seen.add(id(candidate))
            unique_targets.append(candidate)
        if not unique_targets:
            return "There are no nearby enemies to consecrate.\n"

        for enemy in unique_targets:
            raw_damage = max(
                1,
                int(
                    user.check_mod("magic", enemy=enemy)
                    * 0.5
                    * paladin.holy_damage_multiplier(user)
                ),
            )
            resistance = float(enemy.check_mod("resist", typ="Holy"))
            damage = max(1, int(raw_damage * (1.0 - resistance)))
            self._apply_field(enemy, mode="damage", amount=damage)
            user._emit_status_event(
                enemy,
                "Hallowed Ground",
                applied=True,
                duration=3,
                source=self.name,
            )

        healing = max(
            1,
            int(user.health.max * 0.05) + user.check_mod("heal") // 10,
        )
        self._apply_field(user, mode="healing", amount=healing)
        user._emit_status_event(
            user,
            "Hallowed Ground",
            applied=True,
            duration=3,
            source=self.name,
        )
        names = ", ".join(enemy.name for enemy in unique_targets)
        return f"{user.name} hallows the ground beneath {names} for 3 turns.\n"

    def cast_group(
        self,
        user: Character,
        targets: list[tuple[str, Character]],
        *,
        battle_engine: Any,
    ) -> CombatResultGroup:
        """Apply one paid field cast to each living enemy and the player slot."""
        from ..classes import paladin

        group = CombatResultGroup(
            action=self.name,
            actor_id=battle_engine.current_actor_id,
            target_scope=TargetScope.ALL_ENEMIES,
            target_ids=tuple(target_id for target_id, _target in targets),
        )
        user.mana.current -= self.cost
        for target_id, enemy in targets:
            member = battle_engine.encounter.member_by_id(target_id)
            if not member.is_living_hostile:
                group.add(
                    CombatResult(
                        action=self.name,
                        actor=user,
                        target=enemy,
                        actor_id=battle_engine.current_actor_id,
                        target_id=target_id,
                        hit=False,
                        extra={"skipped": True},
                        message=f"{member.display_label} is no longer a valid target.\n",
                    )
                )
                continue
            raw_damage = max(
                1,
                int(
                    user.check_mod("magic", enemy=enemy)
                    * 0.5
                    * paladin.holy_damage_multiplier(user)
                ),
            )
            resistance = float(enemy.check_mod("resist", typ="Holy"))
            damage = max(1, int(raw_damage * (1.0 - resistance)))
            with battle_engine._target_resolution_context(
                member,
                TargetScope.ALL_ENEMIES,
                group.target_ids,
            ):
                self._apply_field(enemy, mode="damage", amount=damage)
                user._emit_status_event(
                    enemy,
                    "Hallowed Ground",
                    applied=True,
                    duration=3,
                    source=self.name,
                )
            group.add(
                CombatResult(
                    action=self.name,
                    actor=user,
                    target=enemy,
                    actor_id=battle_engine.current_actor_id,
                    target_id=target_id,
                    hit=True,
                    extra={
                        "field": "damage",
                        "tick_amount": damage,
                        "display_label": member.display_label,
                    },
                    message=(
                        f"{user.name} hallows the ground beneath "
                        f"{member.display_label} for 3 turns.\n"
                    ),
                )
            )

        healing = max(1, int(user.health.max * 0.05) + user.check_mod("heal") // 10)
        self._apply_field(user, mode="healing", amount=healing)
        with combat_event_context(
            encounter_id=battle_engine.encounter.encounter_id,
            actor_id=battle_engine.current_actor_id,
            target_id="player",
            target_scope=TargetScope.ALL_ENEMIES.value,
            expanded_target_ids=list(group.target_ids),
        ):
            user._emit_status_event(
                user,
                "Hallowed Ground",
                applied=True,
                duration=3,
                source=self.name,
            )
        group.add(
            CombatResult(
                action=self.name,
                actor=user,
                target=user,
                actor_id=battle_engine.current_actor_id,
                target_id="player",
                healing=0,
                extra={"field": "healing", "tick_amount": healing, "self_result": True},
                message=f"Hallowed Ground will restore {user.name} on their turns.\n",
            )
        )
        return group


class Corruption2(Spell):
    replaces = "Corruption"

    def __init__(self):
        super().__init__(
            "Corruption 2",
            "A stronger corruption that damages over time, fed by fiend contracts.",
            school="Shadow",
        )
        self.cost = 22
        self.subtyp = "Shadow"

    def cast(self, user: Character, target: Character | None = None, **kwargs: Any) -> str:
        from ..classes import ability_mechanics, demonologist, mage_mechanics

        super().cast(user, target, **kwargs)
        user.mana.current -= mage_mechanics.spell_mana_cost(user, self)
        if target is None:
            return "Corruption finds no soul to cling to.\n"
        contracts = ability_mechanics.abyssal_contract_count(
            user,
            len(demonologist.ensure_state(user).get("unlocked_contracts", [])),
        )
        msg, damage = _simple_spell_damage(
            user, target, dmg_mod=0.9 + (0.12 * contracts), typ="Shadow"
        )
        if damage > 0 and "DOT" not in getattr(target, "status_immunity", []):
            dot = target.magic_effects["DOT"]
            dot.active = True
            dot.duration = max(dot.duration, 3 + min(2, contracts // 2))
            dot.extra = max(int(dot.extra or 0), max(1, damage // 3 + contracts))
            if "Persistent Corruption" in getattr(user, "spellbook", {}).get("Skills", {}):
                dot.duration = max(dot.duration, 4)
                dot.extra = max(1, int(dot.extra * 1.25))
            dot.source = "Corruption"
            from ..classes import warlock

            warlock.mark_corruption(
                user,
                target,
                rank=2,
                contracts=contracts,
            )
            msg += f"{target.name} is deeply corrupted.\n"
        return msg


class Nightmare(Spell):
    def __init__(self):
        super().__init__(
            "Nightmare",
            "Twist fear into shadow damage against the enemy.",
            school="Shadow",
        )
        self.cost = 24
        self.subtyp = "Shadow"

    def cast(self, user: Character, target: Character | None = None, **kwargs: Any) -> str:
        super().cast(user, target, **kwargs)
        user.mana.current -= self.cost
        msg, damage = _simple_spell_damage(user, target, dmg_mod=1.2, typ="Shadow")
        if target and damage > 0 and not target.has_status_protection("Sleep"):
            target.status_effects["Sleep"].active = True
            target.status_effects["Sleep"].duration = max(
                target.status_effects["Sleep"].duration, 2
            )
            msg += f"{target.name} is trapped in a nightmare.\n"
        return msg


class BadBreath(Skill):
    def __init__(self):
        super().__init__("Bad Breath", "Exhale a foul cloud of debilitating statuses.")
        self.subtyp = "Enemy"
        self.cost = 32

    def use(self, user: Character, target: Character | None = None, **kwargs: Any) -> str:
        super().use(user, target, **kwargs)
        if target is None:
            return "The foul breath hits nothing.\n"
        msg = ""
        for status in ("Poison", "Blind", "Silence"):
            if target.has_status_protection(status):
                msg += f"{target.name} is immune to {status.lower()}.\n"
                continue
            effect = target.status_effects[status]
            effect.active = True
            effect.duration = max(effect.duration, 3)
            if status == "Poison":
                effect.extra = max(effect.extra, max(1, user.stats.con // 3))
            msg += f"{target.name} suffers {status.lower()}.\n"
        return msg
