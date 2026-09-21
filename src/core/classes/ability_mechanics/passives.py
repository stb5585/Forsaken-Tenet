"""Passive class bonuses, triggers, and defensive resources."""

from __future__ import annotations

from typing import Any

from src.core.randomness import gameplay_random as random

from .equipment import has_skill


def third_eye_intelligence(character: Any) -> int:
    """Return Intelligence contributed to avoidance and critical calculations."""
    if not has_skill(character, "Third Eye"):
        return 0
    return max(0, int(getattr(character.stats, "intel", 0)))


def drunken_brawler_damage_bonus(character: Any) -> float:
    if not has_skill(character, "Drunken Brawler"):
        return 0.0
    effect = getattr(character, "class_effects", {}).get("Drunken Brawler")
    return 0.25 if effect is not None and effect.active else 0.0


def drunken_brawler_crit_bonus(character: Any) -> float:
    if not has_skill(character, "Drunken Brawler"):
        return 0.0
    effect = getattr(character, "class_effects", {}).get("Drunken Brawler")
    return 0.10 if effect is not None and effect.active else 0.0


def trigger_drunken_brawler(character: Any) -> str:
    if not has_skill(character, "Drunken Brawler"):
        return ""
    effect = getattr(character, "class_effects", {}).get("Drunken Brawler")
    if effect is None:
        return ""
    effect.active = True
    effect.duration = max(int(effect.duration or 0), 2)
    return f"{character.name}'s Drunken Brawler rhythm sharpens.\n"


def trigger_zephyrstrike(character: Any) -> str:
    if not has_skill(character, "Zephyrstrike"):
        return ""
    speed = getattr(character, "stat_effects", {}).get("Speed")
    if speed is None:
        return ""
    bonus = max(1, int(getattr(character.stats, "dex", 0)) // 5)
    speed.active = True
    speed.duration = max(int(speed.duration or 0), 2)
    speed.extra = max(int(speed.extra or 0), bonus)
    return f"Zephyrstrike quickens {character.name}.\n"


def trigger_blessed_light(character: Any, amount: int, source: str) -> str:
    """Apply Blessed Light after a successful healing-spell cast in combat."""
    if amount <= 0 or not getattr(character, "_active_combat", False):
        return ""
    if not has_skill(character, "Blessed Light"):
        return ""
    spell = getattr(character, "spellbook", {}).get("Spells", {}).get(source)
    if spell is None or getattr(spell, "subtyp", None) != "Heal":
        return ""
    attack = getattr(character, "stat_effects", {}).get("Attack")
    if attack is None:
        return ""
    attack.active = True
    attack.duration = max(int(attack.duration or 0), 3)
    attack.extra = max(int(attack.extra or 0), 10)
    attack.source = "Blessed Light"
    return f"Blessed Light grants {character.name} +10 Attack for three turns.\n"


def power_up_active(
    character: Any, skill_name: str | None = None, class_name: str | None = None
) -> bool:
    if class_name and getattr(getattr(character, "cls", None), "name", None) != class_name:
        return False
    if skill_name and not has_skill(character, skill_name):
        return False
    effect = getattr(character, "class_effects", {}).get("Power Up")
    return bool(getattr(character, "power_up", False) and effect is not None and effect.active)


def passive_power_up_unlocked(
    character: Any, skill_name: str, class_name: str | None = None
) -> bool:
    if class_name and getattr(getattr(character, "cls", None), "name", None) != class_name:
        return False
    return bool(getattr(character, "power_up", False) and has_skill(character, skill_name))


def tricksters_gambit_magic_bonus(character: Any) -> float:
    return 0.20 if power_up_active(character, "Trickster's Gambit", "Arcane Trickster") else 0.0


def tricksters_gambit_crit_bonus(character: Any) -> float:
    return 0.10 if power_up_active(character, "Trickster's Gambit", "Arcane Trickster") else 0.0


def tricksters_gambit_dodge_bonus(character: Any) -> float:
    return 0.10 if power_up_active(character, "Trickster's Gambit", "Arcane Trickster") else 0.0


def primal_ascendance_multiplier(character: Any, aspect: str) -> float:
    if not power_up_active(character, "Primal Ascendance", "Archdruid"):
        return 1.0
    return {
        "Growth": 1.25,
        "Venom": 1.25,
        "Storm": 1.20,
        "Stone": 1.20,
    }.get(aspect, 1.0)


def abyssal_covenant_magic_bonus(character: Any) -> float:
    if not power_up_active(character, "Abyssal Covenant", "Demonologist"):
        return 0.0
    return 0.35


def abyssal_contract_count(character: Any, count: int) -> int:
    return (
        int(count) * 2
        if power_up_active(character, "Abyssal Covenant", "Demonologist")
        else int(count)
    )


def arsenal_mastery_weapon_multiplier(character: Any) -> float:
    if not power_up_active(character, "Arsenal Mastery", "Grandmaster of Arms"):
        return 1.0
    ranks = getattr(character, "grandmaster_discipline", {}).get("disciplines", {})
    mastered = 0
    if isinstance(ranks, dict):
        mastered = sum(
            1
            for entry in ranks.values()
            if isinstance(entry, dict) and int(entry.get("rank", 0) or 0) >= 10
        )
    return 1.10 + min(0.20, mastered * 0.03)


def shield_mastery_block_bonus(character: Any) -> int:
    return 25 if passive_power_up_unlocked(character, "Shield Mastery", "Stalwart Defender") else 0


def melody_inspiration_bonus(character: Any) -> float:
    return (
        0.05 if passive_power_up_unlocked(character, "Melody of Inspiration", "Troubadour") else 0.0
    )


def pack_bond_multiplier(character: Any) -> float:
    familiar = getattr(character, "familiar", None)
    if not (familiar is not None and getattr(familiar, "is_alive", lambda: False)()):
        return 1.0
    if passive_power_up_unlocked(character, "Pack Bond", "Beast Master"):
        return 1.15
    return 1.0


def last_stand_attack_multiplier(character: Any) -> float:
    return 0.75 if has_skill(character, "Last Stand") else 1.0


def last_stand_defense_bonus(character: Any) -> int:
    if not has_skill(character, "Last Stand"):
        return 0
    defense = int(getattr(getattr(character, "combat", None), "defense", 0) or 0)
    return max(1, defense // 2)


def last_stand_block_bonus(character: Any) -> int:
    if not has_skill(character, "Last Stand"):
        return 0
    bonus = 25
    try:
        from ...progression import has_talent

        last_stand = getattr(character, "class_effects", {}).get("Last Stand")
        if (
            has_talent(character, "stalwart.unbroken-wall")
            and last_stand is not None
            and last_stand.active
        ):
            bonus += 10
    except Exception:
        pass
    return bonus


def activate_last_stand(character: Any) -> str:
    if not has_skill(character, "Last Stand"):
        return ""
    effect = getattr(character, "class_effects", {}).get("Last Stand")
    if effect is None or effect.active:
        return ""
    hp = getattr(character, "health", None)
    hp_max = max(1, int(getattr(hp, "max", 1) or 1))
    if getattr(hp, "current", hp_max) / hp_max > 0.35:
        return ""
    effect.active = True
    effect.duration = max(int(effect.duration or 0), 4)
    defense = int(getattr(getattr(character, "combat", None), "defense", 0) or 0)
    effect.extra = max(int(effect.extra or 0), max(1, defense // 2))
    message = f"{character.name} makes a Last Stand.\n"
    try:
        from ..cleric import has_cleric_talent
        from ..promotion_kits import gain_meter

        if has_cleric_talent(character, "templar.last-line"):
            message += gain_meter(character, "devotion", 1, "Last Line")
    except (AttributeError, KeyError, TypeError, ValueError):
        pass
    return message


def posturing_parry_bonus(character: Any) -> float:
    if not has_skill(character, "Posturing"):
        return 0.0
    defend = getattr(character, "status_effects", {}).get("Defend")
    return 0.20 if defend is not None and defend.active else 0.0


def retort_parry_bonus(character: Any) -> float:
    """Add the positive Intelligence modifier to Parry chance."""
    if not has_skill(character, "Retort"):
        return 0.0
    intelligence = int(getattr(getattr(character, "stats", None), "intel", 10) or 10)
    return max(0.0, (intelligence - 10) * 0.01)


def retort_counter_multiplier(character: Any) -> float:
    """Return the compatibility multiplier after Retort's damage bonus removal."""
    del character
    return 1.0


def pain_tolerance_bleed_multiplier(character: Any) -> float:
    """Halve bleed damage and bleed-driven vulnerability."""
    return 0.50 if has_skill(character, "Pain Tolerance") else 1.0


def bandage_healing_multiplier(character: Any) -> float:
    """Double Bandage healing for a character with Pain Tolerance."""
    return 2.0 if has_skill(character, "Pain Tolerance") else 1.0


def trigger_hemorrhage_thirst(character: Any, bleed_damage: int) -> str:
    """Resolve healing and consecutive-turn bloodlust from enemy bleed damage."""
    if not has_skill(character, "Hemorrhage Thirst"):
        character._hemorrhage_thirst_streak = 0
        return ""
    damage = max(0, int(bleed_damage or 0))
    if damage <= 0:
        character._hemorrhage_thirst_streak = 0
        return ""

    healed = min(
        damage,
        max(0, int(character.health.max) - int(character.health.current)),
    )
    character.health.current += healed
    streak = int(getattr(character, "_hemorrhage_thirst_streak", 0) or 0) + 1
    character._hemorrhage_thirst_streak = streak
    message = (
        f"{character.name}'s Hemorrhage Thirst restores {healed} health "
        "from the enemy's bleeding.\n"
    )
    if streak > 2:
        sleep = character.status_effects["Sleep"]
        sleep.active = True
        sleep.duration = max(2, int(sleep.duration or 0))
        sleep.source = "Hemorrhage Thirst"
        character._hemorrhage_thirst_streak = 0
        message += (
            f"{character.name}'s bloodlust becomes overwhelming, leaving "
            "them unconscious for two turns.\n"
        )
    return message


def retaliate_after_block(defender: Any, attacker: Any, *, rng: Any = random) -> str:
    if not has_skill(defender, "Retaliate"):
        return ""
    chance = min(0.75, 0.20 + (int(getattr(defender.stats, "dex", 0)) * 0.01))
    try:
        from ...progression import has_talent

        if has_talent(defender, "sentinel.watchful-reprisal"):
            chance = min(0.85, chance + 0.10)
    except Exception:
        pass
    if rng.random() >= chance:
        return ""
    from ...combat.reactions import execute_reaction

    reaction = execute_reaction(
        "retaliate_after_block",
        defender,
        lambda: defender.weapon_damage(
            attacker,
            dmg_mod=0.75,
            use_offhand=False,
            counterattack=True,
        ),
    )
    if reaction is None:
        return ""
    counter, hit, _crit = reaction
    msg = f"{defender.name} retaliates after the block!\n"
    if hit:
        try:
            from .. import promotion_kits

            counter += promotion_kits.record_resolve_mastery(
                defender,
                "ironwall_revenge",
                "Retaliate",
            )
            counter += promotion_kits.prepare_get_even(defender)
        except (AttributeError, KeyError, TypeError, ValueError):
            pass
    return msg + counter


def final_assault_response(defender: Any, attacker: Any, incoming_damage: int) -> tuple[str, bool]:
    if incoming_damage < getattr(defender.health, "current", 0):
        return "", False
    if not has_skill(defender, "Final Assault"):
        return "", False
    if getattr(defender, "_final_assault_used", False) or getattr(
        defender, "_final_assault_countering", False
    ):
        return "", False
    defender._final_assault_used = True
    defender._final_assault_countering = True
    try:
        from .. import berserker

        momentum, momentum_msg = berserker.prepare_final_assault_payoff(defender)
        msg = f"{defender.name} answers lethal force with a Final Assault!\n"
        msg += momentum_msg
        from ...combat.reactions import execute_reaction

        reaction = execute_reaction(
            "final_assault",
            defender,
            lambda: defender.weapon_damage(
                attacker,
                dmg_mod=1.25 + momentum.damage_bonus,
                use_offhand=False,
                accuracy_modifier=momentum.accuracy_bonus,
            ),
        )
        if reaction is not None:
            counter, _hit, _crit = reaction
            msg += counter
    finally:
        defender._final_assault_countering = False
    if getattr(attacker.health, "current", 0) <= 0:
        defender.health.current = 1
        return msg + f"{defender.name} stabilizes at 1 HP.\n", True
    return msg, False


def nature_shield_orbs(character: Any) -> int:
    effect = getattr(character, "magic_effects", {}).get("Nature Shield")
    if effect is None or not effect.active:
        return 0
    return max(0, int(effect.extra or 0))


def spend_nature_shield_orb(character: Any) -> bool:
    effect = getattr(character, "magic_effects", {}).get("Nature Shield")
    if effect is None or not effect.active:
        return False
    orbs = max(0, int(effect.extra or 0))
    if orbs <= 0:
        effect.active = False
        return False
    effect.extra = orbs - 1
    if effect.extra <= 0:
        effect.active = False
        effect.duration = 0
    return True
