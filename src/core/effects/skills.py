"""Equipment and player skill effects."""

from __future__ import annotations

from typing import TYPE_CHECKING

from .. import abilities
from .base import Effect

if TYPE_CHECKING:
    from ..character import Character
    from ..combat.combat_result import CombatResult


class ShieldSlamEffect(Effect):
    """Shield Slam: str + shield-weight damage with stun chance.

    Requires offhand shield.  Handles its own dodge/damage/stun pipeline.
    Expects: check_weapon=false in YAML; DataDrivenSkill handles mana + ice-block.
    """

    def __init__(self, **_kw):
        super().__init__()

    # noinspection PyMethodOverriding
    def apply(self, actor: Character, target: Character, result: CombatResult) -> None:
        import random as _rng

        from src.core.constants import DAMAGE_VARIANCE_HIGH, DAMAGE_VARIANCE_LOW

        messages = result.extra.setdefault("messages", [])

        # Shield requirement
        offhand = actor.equipment.get("OffHand") if hasattr(actor, "equipment") else None
        if offhand is None or getattr(offhand, "subtyp", None) != "Shield":
            messages.append(f"{actor.name} has no shield to slam with!\n")
            return

        # Dodge
        contact = actor.resolve_contact(target, typ="weapon", rng=_rng)
        if not contact.hit:
            if contact.attribution is not None and contact.attribution.value == "dodge":
                messages.append(f"{target.name} dodges {actor.name}'s shield slam!\n")
            else:
                messages.append(f"{actor.name}'s shield slam misses {target.name}!\n")
            return

        # Damage = strength + shield weight
        damage = max(1, actor.stats.strength + getattr(offhand, "weight", 0))
        from src.core.classes import ability_mechanics

        if ability_mechanics.has_skill(actor, "Chastise"):
            damage = max(1, int(damage * 1.25))
        variance = _rng.uniform(DAMAGE_VARIANCE_LOW, DAMAGE_VARIANCE_HIGH)
        damage = int(damage * variance)
        target.health.current -= damage
        result.damage = damage
        messages.append(
            f"{actor.name} slams {target.name} with their shield for {damage} damage!\n"
        )

        # Stun check
        if target.is_alive():
            if not any(
                [
                    "Stun" in getattr(target, "status_immunity", []),
                    "Status-Stun" in target.equipment["Pendant"].mod,
                    "Status-All" in target.equipment["Pendant"].mod,
                ]
            ):
                att_roll = _rng.randint(0, actor.stats.strength)
                def_roll = _rng.randint(target.stats.strength // 2, target.stats.strength)
                if target.stun_contest_success(actor, att_roll, def_roll):
                    turns = _rng.randint(1, max(1, actor.stats.strength // 8))
                    if target.apply_stun(turns, source="Shield Slam", applier=actor):
                        messages.append(f"{target.name} is stunned for {turns} turn(s)!\n")


class KidneyPunchEffect(Effect):
    """Kidney Punch: offhand-weapon check → weapon_damage → stun.

    Handles its own equipment check, weapon_damage call, and stun logic.
    Expects the owning skill to manage mana through its top-level YAML cost.
    """

    def __init__(self, **_kw):
        super().__init__()

    def apply(self, actor: Character, target: Character, result: CombatResult) -> None:
        import random as _rng

        messages = result.extra.setdefault("messages", [])

        # Offhand weapon requirement
        offhand = actor.equipment.get("OffHand") if hasattr(actor, "equipment") else None
        if not offhand or getattr(offhand, "typ", None) != "Weapon":
            messages.append(f"{actor.name} needs an off-hand weapon to use Kidney Punch.\n")
            return

        # Weapon damage (main hand)
        before = int(target.health.current)
        use_str, hit, crit = actor.weapon_damage(
            target,
            dmg_mod=1.0,
            cover=False,
            use_offhand=False,
        )
        if not hit:
            try:
                from src.core.classes import class_rings

                if class_rings.loaded_dice_succeeds(actor, rng=_rng):
                    use_str += "Loaded Dice turns the failed Kidney Punch.\n"
                    retry, hit, crit = actor.weapon_damage(
                        target,
                        dmg_mod=1.0,
                        cover=False,
                        use_offhand=False,
                    )
                    use_str += retry
            except Exception:
                pass
        messages.append(use_str)
        result.hit = hit
        result.crit = crit if crit > 1 else None
        result.damage = max(0, before - int(target.health.current))

        # Crusader Divine Aegis check
        crusader_aegis = (
            hasattr(target, "cls")
            and hasattr(target, "class_effects")
            and target.cls.name == "Crusader"
            and getattr(target, "power_up", False)
            and "Power Up" in target.class_effects
            and target.class_effects["Power Up"].active
        )

        if hit and target.is_alive() and not crusader_aegis:
            if not any(
                [
                    "Stun" in getattr(target, "status_immunity", []),
                    "Status-Stun" in target.equipment["Pendant"].mod,
                    "Status-All" in target.equipment["Pendant"].mod,
                ]
            ):
                speed = actor.check_mod("speed", enemy=actor)
                att_roll = _rng.randint(0, int(speed * crit))
                fortune_bonus = max(
                    0.0,
                    float(result.extra.get("fortune_bonus", 0.0) or 0.0),
                )
                att_roll += max(0, int(max(1, speed * crit) * fortune_bonus))
                def_roll = _rng.randint(target.stats.con // 2, target.stats.con)
                from ..classes import mage_mechanics

                def_roll = int(def_roll * mage_mechanics.save_roll_multiplier(target))
                contest_success = target.stun_contest_success(actor, att_roll, def_roll)
                if not contest_success:
                    try:
                        from src.core.classes import class_rings

                        contest_success = class_rings.loaded_dice_succeeds(actor, rng=_rng)
                        if contest_success:
                            messages.append("Loaded Dice turns the failed stun attempt.\n")
                    except Exception:
                        contest_success = False
                if contest_success:
                    dur = max(2, speed // 8)
                    if target.apply_stun(dur, source="Kidney Punch", applier=actor):
                        result.effects_applied["Status"].append("Stun")
                        messages.append(f"{target.name} is stunned.\n")
                        if "Twist the Knife" in actor.spellbook.get("Skills", {}):
                            backstab = abilities.Backstab()
                            follow_up = backstab.use(actor, target, special=True)
                            messages.append("Twist the Knife triggers Backstab.\n")
                            messages.append(str(getattr(follow_up, "message", follow_up)))
                else:
                    messages.append(f"{actor.name} fails to stun {target.name}.\n")
            else:
                messages.append(f"{target.name} is immune to stun.\n")


class PoisonStrikeEffect(Effect):
    """Poison Strike: after weapon hit, chance to poison (% of target max HP).

    Runs post-weapon_damage; checks result.extra['hit'].
    """

    def __init__(self, damage_pct: float = 0.1, **_kw):
        super().__init__()
        self.damage_pct = damage_pct

    def apply(self, actor: Character, target: Character, result: CombatResult) -> None:
        import random as _rng

        messages = result.extra.setdefault("messages", [])
        hit = getattr(result, "hit", False)
        crit = result.extra.get("last_crit", 1)
        if not (hit and target.is_alive()):
            return

        if any(
            [
                "Poison" in getattr(target, "status_immunity", []),
                "Status-Poison" in target.equipment["Pendant"].mod,
                "Status-All" in target.equipment["Pendant"].mod,
            ]
        ):
            messages.append(f"{target.name} is immune to poison.\n")
            return

        resist = target.check_mod("resist", enemy=actor, typ="Poison")
        speed = actor.check_mod("speed", enemy=actor)
        if _rng.randint(0, speed) * crit * (1 - resist) > _rng.randint(
            target.stats.con // 2, target.stats.con
        ):
            turns = max(5, speed // 5)
            pois_dmg = int(target.health.max * self.damage_pct * (1 - resist))
            target.status_effects["Poison"].active = True
            target.status_effects["Poison"].duration = max(
                turns, target.status_effects["Poison"].duration
            )
            target.status_effects["Poison"].extra = max(
                pois_dmg, target.status_effects["Poison"].extra
            )
            try:
                actor._emit_status_event(
                    target,
                    "Poison",
                    applied=True,
                    duration=target.status_effects["Poison"].duration,
                    source="Poison Blade",
                )
            except Exception:
                pass
            messages.append(f"{target.name} is poisoned.\n")
        else:
            messages.append(f"{target.name} resists the poison.\n")


class DimMakEffect(Effect):
    """Dim Mak: after weapon hit — kill chance, stun fallback, essence absorb.

    Runs post-weapon_damage; checks target alive for kill/stun.
    On target death (from weapon or effect), absorbs essence.
    """

    def __init__(self, **_kw):
        super().__init__()

    def apply(self, actor: Character, target: Character, result: CombatResult) -> None:
        import random as _rng

        messages = result.extra.setdefault("messages", [])

        if target.is_alive():
            # Ice block / tunnel — no secondary effect
            if any([target.magic_effects["Ice Block"].active, getattr(target, "tunnel", False)]):
                return

            # Instant kill check
            con_val = getattr(target.stats, "con", getattr(target, "con", 0))
            luck = target.check_mod("luck", enemy=actor, luck_factor=5)
            if not (_rng.randint(0, con_val) + luck) and "Death" not in getattr(
                target, "status_immunity", []
            ):
                messages.append(
                    f"{target.name} sustains a lethal blow and collapses to the ground.\n"
                )
                target.health.current = 0
            else:
                # Stun fallback
                if not any(
                    [
                        "Stun" in getattr(target, "status_immunity", []),
                        "Status-Stun" in target.equipment["Pendant"].mod,
                        "Status-All" in target.equipment["Pendant"].mod,
                        target.check_mod("resist", enemy=actor, typ="Physical") > _rng.random(),
                    ]
                ):
                    dur = actor.stats.wisdom // 10
                    if target.apply_stun(dur, source="Devour", applier=actor):
                        messages.append(f"{target.name} is stunned.\n")

            if target.is_alive():
                return

        # Essence absorb (target is dead)
        actor.health.current = min(actor.health.max, actor.health.current + target.health.max)
        actor.mana.current = min(actor.mana.max, actor.mana.current + target.mana.max)
        messages.append(
            f"{actor.name} gains the essence of {target.name}, gaining health and mana.\n"
        )


class ExploitWeaknessEffect(Effect):
    """Exploit Weakness: find target's lowest resistance, boost weapon mod or
    apply random status.  Handles its own weapon_damage call.

    Expects: check_weapon=false in YAML.
    Fixes the original bug where list.append returned None.
    """

    def __init__(self, **_kw):
        super().__init__()

    def apply(self, actor: Character, target: Character, result: CombatResult) -> None:
        import random as _rng

        messages = result.extra.setdefault("messages", [])

        types = list(target.resistance)
        resists = list(target.resistance.values())
        weak = min(resists)

        if weak < 0:
            mod = 1 - weak
            idx = resists.index(weak)
            messages.append(
                f"{actor.name} targets {target.name}'s weakness to "
                f"{types[idx].lower()} to increase their attack!\n"
            )
        else:
            mod = 1
            # Build list with "None" sentinel (fixes original .append bug)
            effects = list(target.status_effects) + ["None"]
            chances = [actor.check_mod("luck", enemy=target, luck_factor=10)] * len(
                target.status_effects
            )
            chances.append(target.stats.con // 5)
            effect = _rng.choices(effects, weights=chances)[0]
            if effect == "None":
                messages.append(
                    f"{target.name} has no identifiable weakness. The skill is ineffective.\n"
                )
            else:
                if any(
                    [
                        effect in getattr(target, "status_immunity", []),
                        f"Status-{effect}" in target.equipment["Pendant"].mod,
                        "Status-All" in target.equipment["Pendant"].mod,
                    ]
                ):
                    messages.append(f"{target.name} is immune to {effect.lower()}.\n")
                else:
                    messages.append(f"{target.name} is affected by {effect.lower()}.\n")
                    target.status_effects[effect].active = True
                    target.status_effects[effect].duration = -1

        # Weapon damage with calculated mod
        wd_str, hit, crit = actor.weapon_damage(target, dmg_mod=mod, use_offhand=False)
        result.hit = bool(hit)
        result.crit = crit if crit > 1 else None
        messages.append(wd_str)


class GoldTossEffect(Effect):
    """Gold Toss: throw gold for unblockable damage, enemy may catch some.

    Handles all damage logic.  Ice block check done inside.
    Expects: check_weapon=false, cost=0 in YAML.
    """

    def __init__(self, **_kw):
        super().__init__()

    def apply(self, actor: Character, target: Character, result: CombatResult) -> None:
        import random as _rng

        messages = result.extra.setdefault("messages", [])

        gold_pool_name = "_gold_toss_pool"
        uses_private_pool = hasattr(actor, gold_pool_name)
        bullionaire = (
            "Bullionaire" in getattr(actor, "spellbook", {}).get("Skills", {})
            and getattr(getattr(actor, "familiar", None), "spec", "") == "Luck"
            and bool(result.extra.get("use_kwargs", {}).get("fam", False))
        )
        available_gold = (
            max(1, int(target.health.current * 2))
            if bullionaire
            else int(getattr(actor, gold_pool_name, actor.gold))
        )
        if available_gold <= 0:
            messages.append("Nothing happens.\n")
            result.extra["luck_success"] = False
            return

        max_thrown = min(target.health.current, available_gold)
        gold_thrown = _rng.randint(1, max_thrown)
        if bullionaire:
            actor.bullionaire_bonus_gold = int(
                getattr(actor, "bullionaire_bonus_gold", 0) or 0
            ) + max(1, gold_thrown // 4)
        elif uses_private_pool:
            setattr(actor, gold_pool_name, available_gold - gold_thrown)
        else:
            actor.gold -= gold_thrown
        messages.append(f"{actor.name} throws {gold_thrown} gold at {target.name}.\n")

        if any([target.magic_effects["Ice Block"].active, getattr(target, "tunnel", False)]):
            messages.append("It has no effect.\n")
            result.extra["luck_success"] = False
            return

        if not bullionaire and not _rng.randint(0, 1) and not target.incapacitated():
            d_chance = target.check_mod("luck", enemy=actor, luck_factor=10)
            catch = _rng.randint(min(gold_thrown, d_chance), gold_thrown)
            gold_thrown -= catch
            if catch > 0:
                target.gold += catch
                if gold_thrown > 0:
                    messages.append(
                        f"{target.name} catches some of the gold thrown, gaining {catch} gold.\n"
                    )
                else:
                    messages.append(
                        f"{target.name} catches all of the gold thrown, gaining {catch} gold.\n"
                    )

        if gold_thrown > 0:
            d_chance = target.check_mod("luck", enemy=actor, luck_factor=10)
            damage = max(1, gold_thrown // (2 + d_chance))
            if bullionaire:
                damage *= 2
            target.health.current -= damage
            result.damage = damage
            try:
                actor._emit_damage_event(target, damage, damage_type="Gold", is_critical=False)
            except Exception:
                pass
            messages.append(f"{actor.name} does {damage} damage to {target.name}.\n")
            result.extra["luck_success"] = True
        else:
            result.extra["luck_success"] = False


class LickEffect(Effect):
    """Lick: after weapon hit, apply a random status effect.

    Silence/Blind get permanent duration (-1), Poison gets 5% HP extra.
    """

    RANDOM_STATUS_POOL = (
        "Berserk",
        "Blind",
        "Doom",
        "Poison",
        "Silence",
        "Sleep",
        "Stun",
    )

    def __init__(self, **_kw):
        super().__init__()

    def apply(self, actor: Character, target: Character, result: CombatResult) -> None:
        import random as _rng

        messages = result.extra.setdefault("messages", [])
        hit = getattr(result, "hit", False)
        if not hit:
            return

        if _rng.randint(actor.stats.strength // 2, actor.stats.strength) > _rng.randint(
            target.stats.con // 2, target.stats.con
        ):
            available_effects = [
                effect for effect in self.RANDOM_STATUS_POOL if effect in target.status_effects
            ]
            if not available_effects:
                return
            random_effect = _rng.choice(available_effects)
            if not any(
                [
                    random_effect in getattr(target, "status_immunity", []),
                    f"Status-{random_effect}" in target.equipment["Pendant"].mod,
                    "Status-All" in target.equipment["Pendant"].mod,
                ]
            ):
                if not target.status_effects[random_effect].active:
                    target.status_effects[random_effect].active = True
                    if random_effect in ["Silence", "Blind"]:
                        target.status_effects[random_effect].duration = -1
                    else:
                        target.status_effects[random_effect].duration = _rng.randint(
                            2, max(3, actor.stats.strength // 8)
                        )
                        if random_effect == "Poison":
                            target.status_effects[random_effect].extra = int(
                                target.health.max * 0.05
                            )
                    messages.append(f"{target.name} is affected by {random_effect.lower()}.\n")


class BrainGorgeEffect(Effect):
    """Brain Gorge: after weapon hit, latch + extra physical damage + intel drain.

    Ignores Mana Shield (original note).
    """

    def __init__(self, **_kw):
        super().__init__()

    def apply(self, actor: Character, target: Character, result: CombatResult) -> None:
        import random as _rng

        messages = result.extra.setdefault("messages", [])
        hit = getattr(result, "hit", False)
        crit = result.extra.get("last_crit", 1)
        if not hit:
            return

        t_chance = target.check_mod("luck", enemy=actor, luck_factor=15)
        messages.append(f"{actor.name} latches onto {target.name}.\n")

        if target.incapacitated() or (
            _rng.randint(actor.stats.strength // 2, actor.stats.strength)
            > _rng.randint(target.stats.con // 2, target.stats.con) + t_chance
        ):
            resist = target.check_mod("resist", enemy=actor, typ="Physical")
            damage = int(
                _rng.randint(actor.stats.strength // 4, actor.stats.strength) * (1 - resist) * crit
            )
            target.health.current -= damage
            if damage > 0:
                messages.append(
                    f"{actor.name} does an additional {damage} damage to {target.name}.\n"
                )
                if not target.is_alive() or (
                    _rng.randint(actor.stats.intel // 2, actor.stats.intel)
                    > _rng.randint(target.stats.wisdom // 2, target.stats.wisdom)
                    + target.check_mod("magic def", enemy=actor)
                ):
                    target.stats.intel -= 1
                    messages.append(
                        f"{actor.name} eats a part of {target.name}'s brain, "
                        f"lowering their intelligence by 1.\n"
                    )


class DetonateEffect(Effect):
    """Detonate: self-destruct; deals massive physical damage.

    User HP → 0.  Damage = max(HP/2, HP*(1-resist)) * 1-4.
    Handles Mana Shield / Crusader Shield / dodge / ice block.
    """

    def __init__(self, **_kw):
        super().__init__()

    def apply(self, actor: Character, target: Character, result: CombatResult) -> None:
        import random as _rng

        messages = result.extra.setdefault("messages", [])
        messages.append(f"{actor.name} explodes, sending shrapnel in all directions.\n")

        resist = target.check_mod("resist", enemy=actor, typ="Physical")
        damage = max(
            actor.health.current // 2,
            int(actor.health.current * (1 - resist)),
        ) * _rng.randint(1, 4)

        # Shield absorption
        if target.magic_effects["Mana Shield"].active:
            damage, message, _absorbed = actor._apply_mana_shield(
                target,
                damage,
                physical=True,
            )
            messages.append(message)
        elif (
            hasattr(target, "cls")
            and target.cls.name == "Crusader"
            and getattr(target, "power_up", False)
            and target.class_effects["Power Up"].active
        ):
            damage, message, _absorbed = actor._apply_crusader_shield(target, damage)
            messages.append(message)

        if damage > 0:
            if any([target.magic_effects["Ice Block"].active, getattr(target, "tunnel", False)]):
                messages.append("It has no effect.\n")
            else:
                t_chance = target.check_mod("luck", enemy=actor, luck_factor=20)
                if _rng.randint(0, target.check_mod("speed", enemy=actor) // 15) + t_chance:
                    damage = max(1, damage // 2)
                    messages.append(
                        f"{target.name} dodges the shrapnel, only taking half damage.\n"
                    )
                target.health.current -= damage
                result.damage = damage
                messages.append(f"{target.name} takes {damage} damage from the shrapnel.\n")
        else:
            messages.append(f"{target.name} was unhurt by the explosion.\n")

        # Self-destruct
        actor.health.current = 0


class CrushEffect(Effect):
    """Crush: grab + crush + throw for physical damage.

    Custom hit/dodge, 25% target HP or str-based, throw for fall damage.
    Fixes original bug where use_str was unbound in Duplicates branch.
    """

    def __init__(self, **_kw):
        super().__init__()

    def apply(self, actor: Character, target: Character, result: CombatResult) -> None:
        import random as _rng

        messages = result.extra.setdefault("messages", [])

        resist = target.check_mod("resist", enemy=actor, typ="Physical")
        a_chance = actor.check_mod("luck", enemy=target, luck_factor=15)
        d_chance = target.check_mod("luck", enemy=actor, luck_factor=10)

        # Dodge
        dodge = (
            _rng.randint(0, target.check_mod("speed", enemy=actor) // 2) + d_chance
            > _rng.randint(0, actor.check_mod("speed", enemy=target)) + a_chance
        )
        if target.incapacitated():
            hit = True
            dodge = False
        else:
            a_hit = actor.stats.dex + actor.stats.strength
            d_hit = target.stats.dex + target.stats.strength
            hit = (
                _rng.randint(a_hit // 2, a_hit) + a_chance
                > _rng.randint(d_hit // 2, d_hit) + d_chance
            )

        if dodge:
            messages.append(f"{target.name} evades the attack.\n")
            return

        # Duplicates check
        if hit and target.magic_effects["Duplicates"].active:
            if target.consume_mirror_image(actor, rng=_rng):
                hit = False
                messages.append(
                    f"{actor.name} grabs for {target.name} but gets a mirror image "
                    f"instead and it vanishes from existence.\n"
                )

        if hit:
            messages.append(f"{actor.name} grabs {target.name}.\n")
            crit = 1
            if (a_chance - d_chance) * 0.1 > _rng.random():
                crit = 2
            damage = max(
                int(target.health.current * 0.25),
                int(
                    _rng.randint(actor.stats.strength // 2, actor.stats.strength)
                    * (1 - resist)
                    * crit
                ),
            )
            target.health.current -= damage
            result.damage = damage
            dmg_msg = f"{actor.name} crushes {target.name}, dealing {damage} damage"
            if crit > 1:
                dmg_msg += " (Critical hit!)"
            messages.append(dmg_msg + ".\n")

            # Throw
            if (
                _rng.randint(actor.stats.strength // 2, actor.stats.strength)
                > _rng.randint(0, target.check_mod("speed", enemy=actor)) + d_chance
            ):
                fall_damage = int(
                    _rng.randint(actor.stats.strength // 2, actor.stats.strength) * (1 - resist)
                )
                target.health.current -= fall_damage
                messages.append(
                    f"{actor.name} throws {target.name} to the ground, "
                    f"dealing {fall_damage} damage.\n"
                )
            else:
                messages.append(
                    f"{target.name} rolls as they hit the ground, preventing any fall damage.\n"
                )
        else:
            messages.append(f"{actor.name} grabs for {target.name} but misses.\n")


class MaelstromEffect(Effect):
    """Maelstrom: reduce target HP to a percentage of max.

    Intel vs wisdom save determines severity (success_pct or fail_pct).
    Fixes original bug: uses actor.stats.intel instead of actor.intel.
    """

    def __init__(self, success_pct: float = 0.10, fail_pct: float = 0.25, **_kw):
        super().__init__()
        self.success_pct = success_pct
        self.fail_pct = fail_pct

    def apply(self, actor: Character, target: Character, result: CombatResult) -> None:
        import random as _rng

        messages = result.extra.setdefault("messages", [])

        if _rng.randint(0, actor.stats.intel) > _rng.randint(
            target.stats.wisdom // 2, target.stats.wisdom
        ):
            hp_cap = int(target.health.max * self.success_pct)
        else:
            hp_cap = int(target.health.max * self.fail_pct)

        target.health.current = min(target.health.current, hp_cap)
        # Original message logic (preserved faithfully, including quirks)
        if hp_cap > target.health.current:
            messages.append(
                f"{target.name} has their health reduced to {int(self.fail_pct * 100)}%.\n"
            )
        else:
            messages.append("The spell is ineffective.\n")


class DisintegrateEffect(Effect):
    """Disintegrate: instant-kill attempt then % HP damage.

    Phase 1: if Death resist < 1 and charisma*(1-resist) beats con+luck → kill.
    Phase 2: if still alive, (charisma + 25% current HP) damage, luck halves.
    Bypasses Mana Shield and Reflect (handled by DataDrivenCustomSpell).
    """

    def __init__(self, **_kw):
        super().__init__()

    def apply(self, actor: Character, target: Character, result: CombatResult) -> None:
        import random as _rng

        messages = result.extra.setdefault("messages", [])

        resist = target.check_mod("resist", enemy=actor, typ="Death")
        chance = target.check_mod("luck", enemy=actor, luck_factor=15)

        # Phase 1: instant kill
        if resist < 1:
            if (
                _rng.randint(0, actor.stats.charisma) * (1 - resist)
                > _rng.randint(target.stats.con // 2, target.stats.con) + chance
            ):
                target.health.current = 0
                messages.append(
                    f"The intense blast from disintegrate leaves "
                    f"{target.name} in a heap of ashes.\n"
                )

        # Phase 2: damage (if still alive)
        if target.is_alive():
            damage = int(actor.stats.charisma + (target.health.current * 0.25))
            if _rng.randint(0, chance):
                messages.append(
                    f"{target.name} dodges the brunt of the blast, taking only half damage.\n"
                )
                damage //= 2
            target.health.current -= damage
            result.damage = damage
            messages.append(
                f"The blast from disintegrate hurts {target.name} for {damage} damage.\n"
            )


class InspectEffect(Effect):
    """Inspect: call target.inspect() to reveal enemy details."""

    def __init__(self, **_kw):
        super().__init__()

    def apply(self, actor: Character, target: Character, result: CombatResult) -> None:
        messages = result.extra.setdefault("messages", [])
        inspect_text = target.inspect()
        messages.append(inspect_text + "\n")


class ResistImmunityEffect(Effect):
    """Set minimum resistance for a type + add status immunity.

    One-shot passive effect for PurityBody / PurityBody2.
    """

    def __init__(
        self,
        resist_type: str = "Poison",
        min_resist: float = 0.5,
        immunity_name: str = "Poison",
        **_kw,
    ):
        super().__init__()
        self.resist_type = resist_type
        self.min_resist = min_resist
        self.immunity_name = immunity_name

    def apply(self, actor: Character, target: Character, result: CombatResult) -> None:
        # target == user when self_target is true
        target.resistance[self.resist_type] = max(
            self.min_resist, target.resistance[self.resist_type]
        )
        if self.immunity_name not in getattr(target, "status_immunity", []):
            target.status_immunity.append(self.immunity_name)


class ResurrectionEffect(Effect):
    """Resurrection: mana-to-HP (self) or revive at % max HP (other).

    Self mode (actor == target): converts actor mana to health.
    Other mode (actor != target): sets target HP to revive_pct * max.
    """

    def __init__(self, revive_pct: float = 0.1, **_kw):
        super().__init__()
        self.revive_pct = revive_pct

    def apply(self, actor: Character, target: Character, result: CombatResult) -> None:
        messages = result.extra.setdefault("messages", [])

        if target is actor:
            # Self: convert mana to HP
            max_heal = target.health.max - target.health.current
            if target.mana.current > max_heal:
                target.health.current = target.health.max
                target.mana.current -= max_heal
                messages.append(f"{target.name} expends mana and is healed to full life!")
            else:
                heal_amount = target.mana.current
                target.health.current += heal_amount
                messages.append(
                    f"{target.name} expends all mana and is healed for {heal_amount} hit points!"
                )
                target.mana.current = 0
        else:
            # Revive other target
            heal = int(target.health.max * self.revive_pct)
            target.health.current = heal
            messages.append(
                f"{target.name} is brought back to life and is healed for {heal} hit points.\n"
            )


class RevealEffect(Effect):
    """Reveal: set sight, add shadow resistance, auto-unequip Pendant of Vision.

    Passive one-shot applied to the user (self_target=true).
    """

    def __init__(self, resist_bonus: float = 0.25, **_kw):
        super().__init__()
        self.resist_bonus = resist_bonus

    def apply(self, actor: Character, target: Character, result: CombatResult) -> None:
        result.extra.setdefault("messages", [])
        target.sight = True
        target.resistance["Shadow"] += self.resist_bonus
        if (
            hasattr(target, "equipment")
            and target.equipment.get("Pendant") is not None
            and getattr(target.equipment["Pendant"], "name", "") == "Pendant of Vision"
        ):
            target.modify_inventory(target.equipment["Pendant"], 1)
            target.equipment["Pendant"] = target.unequip("Pendant")


class TransformEffect(Effect):
    """Apply one unlocked persistent Druid or Lycan form."""

    def __init__(self, creature: str = "Panther", **_kw):
        super().__init__()
        self.creature = creature

    def apply(self, actor: Character, target: Character, result: CombatResult) -> None:
        messages = result.extra.setdefault("messages", [])
        select_form = getattr(target, "select_transform_form", None)
        transform = getattr(target, "transform", None)
        if callable(select_form) and callable(transform) and select_form(self.creature):
            messages.append(transform())


class StompEffect(Effect):
    """Stomp: STR-based damage with dodge/hit/crit/duplicates + stun chance.

    Full combat pipeline: dodge → hit → duplicates → cover → crit →
    damage (with resist + mana shield + crusader shield) → stun.
    """

    def __init__(self, **_kw):
        super().__init__()

    def apply(self, actor: Character, target: Character, result: CombatResult) -> None:
        import random as _rng

        messages = result.extra.setdefault("messages", [])

        resist = target.check_mod("resist", enemy=actor, typ="Physical")
        a_chance = actor.check_mod("luck", enemy=target, luck_factor=10)
        d_chance = target.check_mod("luck", enemy=actor, luck_factor=15)
        contact = actor.resolve_contact(
            target, typ="weapon", always_hit=target.incapacitated(), rng=_rng
        )
        hit = contact.hit
        if not hit:
            messages.append(f"{target.name} evades the attack.\n")
            return

        # Duplicates check
        if hit and target.magic_effects["Duplicates"].active:
            if target.consume_mirror_image(actor, rng=_rng):
                hit = False
                messages.append(
                    f"{actor.name} stomps but hits a mirror image of "
                    f"{target.name} and it vanishes from existence.\n"
                )

        cover = result.extra.get("use_kwargs", {}).get("cover", False)
        if cover and hit:
            messages.append(
                f"{target.familiar.name} steps in front of the attack, "
                f"absorbing the damage directed at {target.name}.\n"
            )
        elif hit:
            crit = 1
            if (a_chance - d_chance) * 0.1 > _rng.random():
                crit = 2
            damage = int(
                _rng.randint(actor.stats.strength // 2, actor.stats.strength) * (1 - resist) * crit
            )

            # Mana Shield
            if target.magic_effects["Mana Shield"].active:
                damage, message, absorbed = actor._apply_mana_shield(
                    target,
                    damage,
                    physical=True,
                )
                hit = not absorbed
                messages.append(message)
            elif (
                getattr(target, "cls", None)
                and target.cls.name == "Crusader"
                and getattr(target, "power_up", False)
                and target.class_effects["Power Up"].active
            ):
                damage, message, absorbed = actor._apply_crusader_shield(target, damage)
                hit = not absorbed
                messages.append(message)

            if damage > 0:
                target.health.current -= damage
                result.damage = damage
                dmg_msg = f"{actor.name} stomps {target.name}, dealing {damage} damage"
                if crit > 1:
                    dmg_msg += " (Critical hit!)"
                messages.append(dmg_msg + ".\n")

                # Stun check (with immunity)
                if not any(
                    [
                        "Stun" in getattr(target, "status_immunity", []),
                        (
                            "Status-Stun"
                            in getattr(target.equipment.get("Pendant", None), "mod", "")
                            if hasattr(target, "equipment")
                            else False
                        ),
                        (
                            "Status-All"
                            in getattr(target.equipment.get("Pendant", None), "mod", "")
                            if hasattr(target, "equipment")
                            else False
                        ),
                    ]
                ):
                    if not target.status_effects["Stun"].active:
                        att_roll = _rng.randint(actor.stats.strength // 2, actor.stats.strength)
                        def_roll = _rng.randint(target.stats.con // 2, target.stats.con)
                        if target.stun_contest_success(actor, att_roll, def_roll):
                            turns = 1 + int(crit > 1)
                            if target.apply_stun(turns, source="Stomp", applier=actor):
                                messages.append(f"{actor.name} stunned {target.name}.\n")
            else:
                messages.append(f"{actor.name} stomps {target.name} but deals no damage.\n")
        else:
            messages.append(f"{actor.name} misses {target.name}.\n")


class ThrowRockEffect(Effect):
    """ThrowRock: random rock size → STR-based damage + prone chance.

    Full combat pipeline: dodge → hit → duplicates → cover → crit →
    damage (with armor + resist + mana shield + crusader shield) → prone.
    """

    def __init__(self, **_kw):
        super().__init__()

    def apply(self, actor: Character, target: Character, result: CombatResult) -> None:
        import random as _rng

        messages = result.extra.setdefault("messages", [])

        size = _rng.randint(0, 4)
        sizes = ["tiny", "small", "medium", "large", "massive"]
        messages.append(f"{actor.name} throws a {sizes[size]} rock at {target.name}.\n")

        dam_red = target.check_mod("armor", enemy=actor)
        resist = target.check_mod("resist", enemy=actor, typ="Physical")
        a_chance = actor.check_mod("luck", enemy=target, luck_factor=10)
        d_chance = target.check_mod("luck", enemy=actor, luck_factor=15)
        contact = actor.resolve_contact(
            target, typ="weapon", always_hit=target.incapacitated(), rng=_rng
        )
        hit = contact.hit
        if not hit:
            messages.append(f"{target.name} evades the attack.\n")
            return

        # Duplicates check
        if hit and target.magic_effects["Duplicates"].active:
            if target.consume_mirror_image(actor, rng=_rng):
                hit = False
                messages.append(
                    f"{actor.name} throws a rock but hits a mirror image "
                    f"of {target.name} and it vanishes from existence.\n"
                )

        cover = result.extra.get("use_kwargs", {}).get("cover", False)
        if hit and cover:
            messages.append(
                f"{target.familiar.name} steps in front of the attack, "
                f"absorbing the damage directed at {target.name}.\n"
            )
        elif hit:
            crit = 1
            if (a_chance - d_chance) * 0.1 > _rng.random():
                crit = 2
            damage = (
                _rng.randint(
                    actor.stats.strength // 4,
                    actor.stats.strength // 3,
                )
                * (size + 1)
                * crit
            )
            damage = max(0, int((damage - dam_red) * (1 - resist)))

            # Mana Shield
            if target.magic_effects["Mana Shield"].active:
                damage, message, absorbed = actor._apply_mana_shield(
                    target,
                    damage,
                    physical=True,
                )
                hit = not absorbed
                messages.append(message)
            elif (
                getattr(target, "cls", None)
                and target.cls.name == "Crusader"
                and getattr(target, "power_up", False)
                and target.class_effects["Power Up"].active
            ):
                damage, message, absorbed = actor._apply_crusader_shield(target, damage)
                hit = not absorbed
                messages.append(message)

            if damage > 0:
                target.health.current -= damage
                result.damage = damage
                dmg_msg = f"{target.name} is hit by the rock and takes {damage} damage"
                if crit > 1:
                    dmg_msg += " (Critical hit!)"
                messages.append(dmg_msg + ".\n")

                # Prone check
                if not target.physical_effects["Prone"].active:
                    if _rng.randint(
                        actor.stats.strength // 2,
                        actor.stats.strength,
                    ) > _rng.randint(
                        target.stats.strength // 2,
                        target.stats.strength,
                    ):
                        prone_dur = max(1, size)
                        target.physical_effects["Prone"].active = True
                        target.physical_effects["Prone"].duration = prone_dur
                        if hasattr(actor, "_emit_status_event"):
                            actor._emit_status_event(
                                target,
                                "Prone",
                                applied=True,
                                duration=prone_dur,
                                source="Throw Rock",
                            )
                        messages.append(f"{target.name} is knocked over and falls prone.\n")
            else:
                messages.append(f"{target.name} shrugs off the damage.\n")
        else:
            messages.append(f"{actor.name} misses {target.name} with the throw.\n")


class StealEffect(Effect):
    """Steal: speed+luck contest to steal gold or a random item.

    Respects ice-block/tunnel, blind penalty, crit bonus.
    Activates "Steal Success" status on success.
    """

    def __init__(self, gold_cap: float = 0.05, **_kw):
        super().__init__()
        self.gold_cap = gold_cap

    def apply(self, actor: Character, target: Character, result: CombatResult) -> None:
        import random as _rng

        messages = result.extra.setdefault("messages", [])

        # Get crit from caller (Mug passes crit via use_kwargs)
        use_kw = result.extra.get("use_kwargs", {})
        crit = use_kw.get("crit", 1)

        gold_or_item = _rng.choice(["Gold", "Item"])
        chance = actor.check_mod("luck", enemy=target, luck_factor=16)
        dv = 1 + int(actor.status_effects["Blind"].active)

        fortune_bonus = max(0.0, float(result.extra.get("fortune_bonus", 0.0) or 0.0))
        actor_ceiling = max(0, int(actor.check_mod("speed", enemy=actor) * crit) // dv)
        actor_roll = _rng.randint(0, actor_ceiling) + chance
        actor_roll += max(0, int((actor_ceiling + chance) * fortune_bonus))
        target_roll = _rng.randint(0, target.check_mod("speed", enemy=actor))
        succeeded = actor_roll > target_roll
        if not succeeded:
            try:
                from src.core.classes import class_rings

                succeeded = class_rings.loaded_dice_succeeds(actor, rng=_rng)
                if succeeded:
                    messages.append("Loaded Dice turns the failed theft.\n")
            except Exception:
                succeeded = False
        if succeeded:
            if gold_or_item == "Item":
                if len(target.inventory) != 0:
                    item_key = _rng.choice(list(target.inventory))
                    item = target.inventory[item_key][0]
                    target.modify_inventory(item, subtract=True)
                    try:
                        actor.modify_inventory(item)
                    except AttributeError:
                        pass
                    steal_effect = actor.status_effects.get("Steal Success")
                    if steal_effect is not None:
                        steal_effect.active = True
                        steal_effect.duration = max(steal_effect.duration, 5)
                    messages.append(f"{actor.name} steals {item_key} from {target.name}.\n")
                    result.extra["luck_success"] = True
                    result.extra["stolen_item"] = item_key
                    return
                messages.append(f"{target.name} doesn't have anything to steal.\n")
                result.extra["luck_success"] = False
                return
            else:
                gold_amount = _rng.randint(1, max(1, int(target.gold * self.gold_cap)))
                actor.gold += gold_amount
                target.gold -= gold_amount
                steal_effect = actor.status_effects.get("Steal Success")
                if steal_effect is not None:
                    steal_effect.active = True
                    steal_effect.duration = max(steal_effect.duration, 5)
                messages.append(f"{actor.name} steals {gold_amount} gold from {target.name}.\n")
                result.extra["luck_success"] = True
                result.extra["stolen_gold"] = gold_amount
                return
        messages.append("Steal fails.\n")
        result.extra["luck_success"] = False


class MugEffect(Effect):
    """Mug: after a weapon hit, attempt to steal from the target.

    Instantiates Steal() and calls use() with the crit from the weapon hit.
    Preserves original double-mana-cost (Mug + Steal).
    """

    def __init__(self, **_kw):
        super().__init__()

    def apply(self, actor: Character, target: Character, result: CombatResult) -> None:
        if not result.hit:
            return
        messages = result.extra.setdefault("messages", [])
        crit = result.extra.get("last_crit", 1)
        from src.core.abilities import Steal

        steal_result = Steal().use(actor, target, crit=crit, mug=True)
        if isinstance(steal_result, str):
            messages.append(steal_result)
        else:
            messages.append(str(steal_result))


class CounterspellEffect(Effect):
    """Counterspell: pick a random spell from the user's spellbook and cast it.

    If the chosen spell is a healing spell, target = actor (self-heal).
    """

    def __init__(self, **_kw):
        super().__init__()

    def apply(self, actor: Character, target: Character, result: CombatResult) -> None:
        import random as _rng

        messages = result.extra.setdefault("messages", [])
        spells = list(actor.spellbook["Spells"].values())
        if not spells:
            messages.append(f"{actor.name} has no spells to counter with.\n")
            return
        spell = _rng.choice(spells)
        cast_target = actor if spell.subtyp == "Heal" else target
        cover = result.extra.get("use_kwargs", {}).get("cover", False)
        cast_result = spell.cast(actor, target=cast_target, cover=cover)
        if isinstance(cast_result, str):
            messages.append(cast_result)
        else:
            messages.append(str(cast_result))


class ElementalStrikeEffect(Effect):
    """ElementalStrike: on weapon hit, cast a random elemental spell.

    Picks from a hardcoded list filtered by user's spellbook.
    On crit, casts the spell twice.
    """

    _SPELL_NAMES = [
        "Firebolt",
        "Ice Lance",
        "Shock",
        "Scorch",
        "Water Jet",
        "Tremor",
        "Gust",
    ]

    def __init__(self, **_kw):
        super().__init__()

    def apply(self, actor: Character, target: Character, result: CombatResult) -> None:
        import random as _rng

        messages = result.extra.setdefault("messages", [])
        if not result.hit:
            return
        if target is not None and not target.is_alive():
            return

        forced_spell = None
        try:
            from src.core.classes import nature_totems

            aspect = nature_totems.active_totem_aspect(actor)
            if aspect in nature_totems.ELEMENTAL_ASPECTS:
                forced_name = nature_totems.highest_unlocked_spell_name(actor, aspect)
                forced_spell = actor.spellbook.get("Spells", {}).get(forced_name)
        except Exception:
            forced_spell = None

        if forced_spell is not None:
            spell = forced_spell
            cover = result.extra.get("use_kwargs", {}).get("cover", False)
            messages.append(f"The enemy is struck by the elemental force of {spell.subtyp}.\n")
            spell.cast(actor, target=target, special=True, cover=cover)

            crit = result.extra.get("last_crit", 1)
            if crit > 1 and target is not None and target.is_alive():
                spell.cast(actor, target=target, special=True, cover=cover)
            return

        # Build list of available elemental spells from actor's spellbook
        from src.core import abilities as _abilities

        cast_list = []
        for spell_name in self._SPELL_NAMES:
            if spell_name in actor.spellbook.get("Spells", {}):
                # Look up the class by converting name to class name
                cls_name = spell_name.replace(" ", "")
                spell_cls = getattr(_abilities, cls_name, None)
                if spell_cls is not None:
                    cast_list.append(spell_cls())
        if not cast_list:
            return

        cover = result.extra.get("use_kwargs", {}).get("cover", False)
        spell = _rng.choice(cast_list)
        messages.append(f"The enemy is struck by the elemental force of {spell.subtyp}.\n")
        spell.cast(actor, target=target, special=True, cover=cover)

        crit = result.extra.get("last_crit", 1)
        if crit > 1 and target is not None and target.is_alive():
            spell.cast(actor, target=target, special=True, cover=cover)


class BlackjackEffect(Effect):
    """Blackjack: play a round of blackjack with random or callback-driven outcome.

    Outcomes: User Win, Target Win, Draw, User Break, Target Break.
    Currently stub effects (flavor text only per original implementation).
    """

    def __init__(self, **_kw):
        super().__init__()

    def apply(self, actor: Character, target: Character, result: CombatResult) -> None:
        import random as _rng

        messages = result.extra.setdefault("messages", [])

        use_kw = result.extra.get("use_kwargs", {})
        callback = use_kw.get("blackjack_callback", None)
        if callback is not None:
            outcome = callback(actor, target)
        else:
            outcome = _rng.choice(
                [
                    "User Win",
                    "Target Win",
                    "Draw",
                    "User Break",
                    "Target Break",
                ]
            )

        if outcome == "Target Win":
            messages.append(f"{target.name} wins the hand!\n")
        elif outcome == "Target Break":
            messages.append(f"Oh no, {target.name} busted...\n")
        elif outcome == "User Break":
            messages.append(f"Oh no, {actor.name} busted...\n")
        elif outcome == "User Win":
            messages.append(f"{actor.name} wins the hand!\n")
        else:
            messages.append("It's a draw!\n")
