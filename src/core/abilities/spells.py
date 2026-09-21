"""Concrete elemental, healing, support, status, and enemy spells."""

from __future__ import annotations

from typing import TYPE_CHECKING

from src.core.randomness import gameplay_random as random

from .base import Spell, _load_yaml_ability
from .spell_types import Attack, _simple_spell_damage

if TYPE_CHECKING:
    from typing import Any

    from ..character import Character


# Spells
class MagicMissile(Attack):
    """Data-driven (magic_missile.yaml)"""

    def __new__(cls):
        return _load_yaml_ability("magic_missile.yaml", cls_name="MagicMissile")


class MagicMissile2(MagicMissile):
    """Data-driven (magic_missile_2.yaml)"""

    def __new__(cls):
        return _load_yaml_ability("magic_missile_2.yaml", cls_name="MagicMissile2")


class MagicMissile3(MagicMissile):
    """Data-driven (magic_missile_3.yaml)"""

    replaces = "Magic Missile II"

    def __new__(cls):
        return _load_yaml_ability("magic_missile_3.yaml", cls_name="MagicMissile3")


class PhotonSphere:
    """Ultimate multi-hit non-elemental spell — data-driven (ultima.yaml)."""

    def __new__(cls):
        return _load_yaml_ability("ultima.yaml", cls_name="PhotonSphere")


class Ultima(PhotonSphere):
    """Compatibility alias for saves and content authored before the rename."""


class Maelstrom:
    """Data-driven (maelstrom.yaml)"""

    def __new__(cls):
        return _load_yaml_ability("maelstrom.yaml", cls_name="Maelstrom")


class Meteor:
    """Data-driven (meteor.yaml)"""

    def __new__(cls):
        return _load_yaml_ability("meteor.yaml", cls_name="Meteor")


class FireSpell(Attack):
    """
    Arcane and elemental fire spells have lower crit but hit harder on average; chance to apply damage over time
    """

    def __init__(self, name: str, description: str, cost: int, dmg_mod: float, crit: int) -> None:
        super().__init__(name, description, cost, dmg_mod, crit)
        self.subtyp = "Fire"

    def special_effect(self, caster: Character, target: Character, damage: int, crit: int) -> str:
        special_str = ""
        if random.randint(0, caster.stats.intel // 2) > random.randint(
            target.stats.wisdom // 4, target.stats.wisdom
        ):
            special_str += f"{target.name} is set ablaze.\n"
            dmg = random.randint(damage // 4, damage // 2)
            target.magic_effects["DOT"].active = True
            target.magic_effects["DOT"].duration = max(2, target.magic_effects["DOT"].duration)
            target.magic_effects["DOT"].extra = max(dmg, target.magic_effects["DOT"].extra)
            target.magic_effects["DOT"].source = "Burn"
            caster._emit_status_event(
                target,
                "DOT",
                applied=True,
                duration=target.magic_effects["DOT"].duration,
                source=self.name,
            )
        return special_str


class Firebolt:
    """Data-driven (firebolt.yaml)"""

    def __new__(cls):
        return _load_yaml_ability("firebolt.yaml", cls_name="Firebolt")


class Fireball:
    """Data-driven (fireball.yaml)"""

    replaces = "Firebolt"

    def __new__(cls):
        return _load_yaml_ability("fireball.yaml", cls_name="Fireball")


class Firestorm:
    """Data-driven (firestorm.yaml)"""

    def __new__(cls):
        return _load_yaml_ability("firestorm.yaml", cls_name="Firestorm")


class Scorch:
    """Data-driven (scorch.yaml)"""

    def __new__(cls):
        return _load_yaml_ability("scorch.yaml", cls_name="Scorch")


class MoltenRock:
    """Data-driven (molten_rock.yaml)"""

    def __new__(cls):
        return _load_yaml_ability("molten_rock.yaml", cls_name="MoltenRock")


class Volcano:
    """Data-driven (volcano.yaml)"""

    def __new__(cls):
        return _load_yaml_ability("volcano.yaml", cls_name="Volcano")


class IceSpell(Attack):
    """
    Arcane ice spells have lower average damage but have the highest chance to crit; chance to do extra damage
    """

    def __init__(self, name: str, description: str, cost: int, dmg_mod: float, crit: int) -> None:
        super().__init__(name, description, cost, dmg_mod, crit)
        self.subtyp = "Ice"

    def special_effect(self, caster: Character, target: Character, damage: int, crit: int) -> str:
        special_str = ""
        if random.randint(0, caster.stats.intel // 2) > random.randint(
            target.stats.wisdom // 4, target.stats.wisdom
        ):
            dmg = random.randint(damage // 2, damage)
            special_str += f"{target.name} is chilled to the bone, taking an extra {dmg} damage.\n"
            target.health.current -= dmg
        return special_str


class IceLance:
    """Data-driven (ice_lance.yaml)"""

    def __new__(cls):
        return _load_yaml_ability("ice_lance.yaml", cls_name="IceLance")


class Icicle:
    """Data-driven (icicle.yaml)"""

    replaces = "Ice Lance"

    def __new__(cls):
        return _load_yaml_ability("icicle.yaml", cls_name="Icicle")


class IceBlizzard:
    """Data-driven (blizzard.yaml)"""

    def __new__(cls):
        return _load_yaml_ability("blizzard.yaml", cls_name="IceBlizzard")


class ElectricSpell(Attack):
    """
    Arcane electric spells have better crit than fire and better damage than ice; chance to stun
    """

    def __init__(self, name: str, description: str, cost: int, dmg_mod: float, crit: int) -> None:
        super().__init__(name, description, cost, dmg_mod, crit)
        self.subtyp = "Electric"

    def special_effect(self, caster: Character, target: Character, damage: int, crit: int) -> str:
        special_str = ""
        if not any(
            [
                "Stun" in target.status_immunity,
                "Status-Stun" in target.equipment["Pendant"].mod,
                "Status-All" in target.equipment["Pendant"].mod,
            ]
        ):
            att_roll = random.randint(0, caster.stats.intel // 2)
            def_roll = random.randint(target.stats.wisdom // 4, target.stats.wisdom)
            if target.stun_contest_success(caster, att_roll, def_roll):
                applied = target.apply_stun(
                    max(1 + crit, target.status_effects["Stun"].duration),
                    source=self.name,
                    applier=caster,
                )
                if applied:
                    special_str += f"{target.name} gets shocked and is stunned.\n"
        return special_str


class Shock:
    """Data-driven (shock.yaml)"""

    def __new__(cls):
        return _load_yaml_ability("shock.yaml", cls_name="Shock")


class Lightning:
    """Data-driven (lightning.yaml)"""

    replaces = "Shock"

    def __new__(cls):
        return _load_yaml_ability("lightning.yaml", cls_name="Lightning")


class Electrocution:
    """Data-driven (electrocution.yaml)"""

    def __new__(cls):
        return _load_yaml_ability("electrocution.yaml", cls_name="Electrocution")


class Bolt:
    """Data-driven (bolt.yaml)"""

    def __new__(cls):
        return _load_yaml_ability("bolt.yaml", cls_name="Bolt")


class BallLightning(Spell):
    def __init__(self):
        super().__init__(
            "Ball Lightning",
            "Conjure a ball of electricity that repeatedly zaps the target.",
            school="Nature",
        )
        self.cost = 34
        self.subtyp = "Electric"

    def cast(self, user: Character, target: Character | None = None, **kwargs: Any) -> str:
        super().cast(user, target, **kwargs)
        user.mana.current -= self.cost
        if target is None:
            return "The ball lightning crackles without a target.\n"
        msg = ""
        for _ in range(3):
            zap_msg, _damage = _simple_spell_damage(user, target, dmg_mod=0.65, typ="Electric")
            msg += zap_msg
            if not target.is_alive():
                break
        return msg


class Kaleidoscope(Spell):
    """Release a randomly colored elemental mist with a distinct rider."""

    COLORS = ("Crimson", "Azure", "Emerald", "Violet")

    def __init__(self):
        super().__init__(
            "Kaleidoscope",
            (
                "Unleash a random elemental mist: Crimson burns, Azure slows, "
                "Emerald restores, and Violet weakens magic defense."
            ),
            school="Elemental",
        )
        self.cost = 12
        self.subtyp = "Elemental"

    def cast(
        self,
        user: Character,
        target: Character | None = None,
        **kwargs: Any,
    ) -> str:
        super().cast(user, target, **kwargs)
        if int(user.mana.current) < self.cost:
            return f"{user.name} does not have enough mana for Kaleidoscope.\n"
        if target is None:
            return "Kaleidoscope needs a target.\n"
        user.mana.current -= self.cost
        rng = kwargs.get("rng") or random
        color = str(rng.choice(self.COLORS))
        vivid = False
        try:
            from ..progression import has_talent

            vivid = has_talent(user, "bard.vivid-palette")
        except (AttributeError, KeyError, TypeError):
            pass
        potency = 1.15 if vivid else 1.0
        message = f"{user.name}'s Kaleidoscope blooms {color}.\n"
        if color == "Emerald":
            amount = max(1, int(user.check_mod("magic") * 0.55 * potency))
            restored = min(user.health.max - user.health.current, amount)
            user.health.current += restored
            if vivid:
                restored_bonus = min(
                    user.mana.max - user.mana.current,
                    max(1, amount // 4),
                )
                user.mana.current += restored_bonus
                message += f"Vivid color restores {restored_bonus} MP.\n"
            _kaleidoscope_cadence(user)
            return message + f"Emerald mist restores {restored} HP.\n"

        damage_type = "Fire" if color == "Crimson" else "Arcane"
        damage_message, damage = _simple_spell_damage(
            user,
            target,
            dmg_mod=(0.95 if color == "Crimson" else 0.65) * potency,
            typ=damage_type,
        )
        message += damage_message
        if damage <= 0:
            return message
        duration = 3 if _bard_talent(user, "bard.prismatic-flourish") else 2
        if color == "Azure":
            effect = target.stat_effects["Speed"]
            effect.active = True
            effect.duration = max(effect.duration, duration)
            effect.extra = min(int(effect.extra or 0), -max(2, damage // 8))
            message += f"Azure mist slows {target.name}.\n"
        elif color == "Violet":
            effect = target.stat_effects["Magic Defense"]
            effect.active = True
            effect.duration = max(effect.duration, duration)
            effect.extra = min(int(effect.extra or 0), -max(2, damage // 8))
            message += f"Violet mist weakens {target.name}'s magic defense.\n"
        _kaleidoscope_cadence(user)
        return message


def _bard_talent(character: Any, key: str) -> bool:
    try:
        from ..progression import has_talent

        return has_talent(character, key)
    except (AttributeError, KeyError, TypeError):
        return False


def _kaleidoscope_cadence(character: Any) -> None:
    if not _bard_talent(character, "bard.elemental-cadence"):
        return
    from ..classes import bard, promotion_kits

    if bard.active_song(character):
        promotion_kits.gain_meter(character, "crescendo", 1, "Kaleidoscope")


class WaterJet:
    """Data-driven (water_jet.yaml)"""

    def __new__(cls):
        return _load_yaml_ability("water_jet.yaml", cls_name="WaterJet")


class Aqualung:
    """Rank 1 Enemy Spell — data-driven (aqualung.yaml)"""

    replaces = "Water Jet"

    def __new__(cls):
        return _load_yaml_ability("aqualung.yaml", cls_name="Aqualung")


class Tsunami:
    """Rank 2 Enemy Spell — data-driven (tsunami.yaml)"""

    def __new__(cls):
        return _load_yaml_ability("tsunami.yaml", cls_name="Tsunami")


class Hydration:
    def __new__(cls):
        return _load_yaml_ability("hydration.yaml", cls_name="Hydration")


class Tremor:
    """Data-driven (tremor.yaml)"""

    def __new__(cls):
        return _load_yaml_ability("tremor.yaml", cls_name="Tremor")


class Mudslide:
    """Rank 1 Enemy Spell — data-driven (mudslide.yaml)"""

    replaces = "Tremor"

    def __new__(cls):
        return _load_yaml_ability("mudslide.yaml", cls_name="Mudslide")


class Earthquake:
    """Rank 2 Enemy Spell — data-driven (earthquake.yaml)"""

    def __new__(cls):
        return _load_yaml_ability("earthquake.yaml", cls_name="Earthquake")


class Sandstorm:
    """Enemy Spell — data-driven (sandstorm.yaml)"""

    def __new__(cls):
        return _load_yaml_ability("sandstorm.yaml", cls_name="Sandstorm")


class Gust:
    """Data-driven (gust.yaml)"""

    def __new__(cls):
        return _load_yaml_ability("gust.yaml", cls_name="Gust")


class Hurricane:
    """Rank 1 Enemy Spell — data-driven (hurricane.yaml)"""

    replaces = "Gust"

    def __new__(cls):
        return _load_yaml_ability("hurricane.yaml", cls_name="Hurricane")


class Tornado:
    """Rank 2 Enemy Spell — data-driven (tornado.yaml)"""

    def __new__(cls):
        return _load_yaml_ability("tornado.yaml", cls_name="Tornado")


# Shadow spells
class ShadowBolt:
    """Data-driven (shadow_bolt.yaml)"""

    def __new__(cls):
        return _load_yaml_ability("shadow_bolt.yaml", cls_name="ShadowBolt")


class ShadowBolt2:
    """Data-driven (shadow_bolt_2.yaml)"""

    def __new__(cls):
        return _load_yaml_ability("shadow_bolt_2.yaml", cls_name="ShadowBolt2")


class ShadowBolt3:
    """Data-driven (shadow_bolt_3.yaml)"""

    def __new__(cls):
        return _load_yaml_ability("shadow_bolt_3.yaml", cls_name="ShadowBolt3")


class Corruption:
    """Data-driven (corruption.yaml)"""

    def __new__(cls):
        return _load_yaml_ability("corruption.yaml", cls_name="Corruption")


class Terrify:
    """Data-driven (terrify.yaml)"""

    def __new__(cls):
        return _load_yaml_ability("terrify.yaml", cls_name="Terrify")


# Death spells
class Doom:
    """Data-driven (doom.yaml)"""

    def __new__(cls):
        return _load_yaml_ability("doom.yaml", cls_name="Doom")


class Desoul:
    """Death spell — data-driven (desoul.yaml)"""

    def __new__(cls):
        return _load_yaml_ability("desoul.yaml", cls_name="Desoul")


class SoulDrain:
    """Soul spell — data-driven (soul_drain.yaml)"""

    def __new__(cls):
        return _load_yaml_ability("soul_drain.yaml", cls_name="SoulDrain")


class PoisonDart:
    """Nature spell — data-driven (poison_dart.yaml)"""

    def __new__(cls):
        return _load_yaml_ability("poison_dart.yaml", cls_name="PoisonDart")


class Petrify:
    """Death spell — data-driven (petrify.yaml)"""

    def __new__(cls):
        return _load_yaml_ability("petrify.yaml", cls_name="Petrify")


class Disintegrate:
    """Data-driven (disintegrate.yaml)"""

    def __new__(cls):
        return _load_yaml_ability("disintegrate.yaml", cls_name="Disintegrate")


# Holy spells
class Smite:
    """Data-driven (smite.yaml) - weapon strike + holy follow-up."""

    def __new__(cls):
        return _load_yaml_ability("smite.yaml", cls_name="Smite")


class Smite2:
    """Data-driven (smite_2.yaml) - upgraded Smite."""

    def __new__(cls):
        return _load_yaml_ability("smite_2.yaml", cls_name="Smite2")


class Smite3:
    """Data-driven (smite_3.yaml) - upgraded Smite."""

    def __new__(cls):
        return _load_yaml_ability("smite_3.yaml", cls_name="Smite3")


class Holy:
    """Data-driven (holy.yaml)"""

    def __new__(cls):
        return _load_yaml_ability("holy.yaml", cls_name="Holy")


class Holy2:
    """Data-driven (holy_2.yaml)"""

    def __new__(cls):
        return _load_yaml_ability("holy_2.yaml", cls_name="Holy2")


class Holy3:
    """Data-driven (holy_3.yaml)"""

    def __new__(cls):
        return _load_yaml_ability("holy_3.yaml", cls_name="Holy3")


class TurnUndead:
    """Data-driven (turn_undead.yaml) - undead-only kill or holy damage."""

    def __new__(cls):
        return _load_yaml_ability("turn_undead.yaml", cls_name="TurnUndead")


class TurnUndead2:
    """Data-driven (turn_undead_2.yaml) - upgraded Turn Undead."""

    def __new__(cls):
        return _load_yaml_ability("turn_undead_2.yaml", cls_name="TurnUndead2")


class RepelTheWicked(Spell):
    """Drive fiends and undead from combat with sacred authority."""

    def __init__(self):
        super().__init__(
            "Repel the Wicked",
            (
                "Attempt to drive a fiend or undead foe from combat. A foe "
                "marked by Condemnation is disintegrated on a successful cast."
            ),
            school="Holy",
        )
        self.cost = 12
        self.subtyp = "Holy"

    def cast(
        self,
        user: Character,
        target: Character | None = None,
        **kwargs: Any,
    ) -> str:
        from ..classes import paladin

        return paladin.repel_the_wicked(
            user,
            target,
            rng=kwargs.get("rng"),
        )


# Heal spells
class Heal:
    def __new__(cls):
        return _load_yaml_ability("heal.yaml", cls_name="Heal")


class Heal2:
    def __new__(cls):
        return _load_yaml_ability("heal_2.yaml", cls_name="Heal2")


class Heal3:
    def __new__(cls):
        return _load_yaml_ability("heal_3.yaml", cls_name="Heal3")


class Regen:
    def __new__(cls):
        return _load_yaml_ability("regen.yaml", cls_name="Regen")


class Regen2:
    def __new__(cls):
        return _load_yaml_ability("regen_2.yaml", cls_name="Regen2")


class Regen3:
    def __new__(cls):
        return _load_yaml_ability("regen_3.yaml", cls_name="Regen3")


# Support spells
class Bless:
    def __new__(cls):
        return _load_yaml_ability("bless.yaml", cls_name="Bless")


class Boost:
    def __new__(cls):
        return _load_yaml_ability("boost.yaml", cls_name="Boost")


class Shell:
    def __new__(cls):
        return _load_yaml_ability("shell.yaml", cls_name="Shell")


class Reflect:
    def __new__(cls):
        return _load_yaml_ability("reflect.yaml", cls_name="Reflect")


class Resurrection:
    """Data-driven (resurrection.yaml)"""

    def __new__(cls):
        return _load_yaml_ability("resurrection.yaml", cls_name="Resurrection")


class Cleanse:
    def __new__(cls):
        return _load_yaml_ability("cleanse.yaml", cls_name="Cleanse")


class ResistAll:
    """Data-driven (resist_all.yaml)"""

    def __new__(cls):
        return _load_yaml_ability("resist_all.yaml", cls_name="ResistAll")


class DivineProtection:
    def __new__(cls):
        return _load_yaml_ability("divine_protection.yaml", cls_name="DivineProtection")


class DivineProtection2(Spell):
    """Greatly fortify the caster and weaken every nearby enemy."""

    replaces = "Divine Protection"

    def __init__(self):
        super().__init__(
            "Divine Protection II",
            (
                "Greatly increase Defense for five turns and weaken nearby "
                "enemies for three turns."
            ),
            school="Holy",
        )
        self.cost = 20
        self.subtyp = "Support"

    def cast(
        self,
        caster: Character,
        target: Character | None = None,
        **kwargs: Any,
    ) -> str:
        del target
        if not kwargs.get("special", False) and not kwargs.get("fam", False):
            caster.mana.current -= self.cost

        base_defense = caster.check_mod("defense")
        defense = caster.stat_effects["Defense"]
        defense.active = True
        defense.duration = max(int(defense.duration or 0), 5)
        defense.extra = max(
            int(defense.extra or 0),
            max(1, int(base_defense * 0.75)),
        )
        defense.source = self.name

        weakened = []
        encounter = getattr(caster, "_combat_encounter", None)
        for member in getattr(encounter, "living_members", ()):
            enemy = member.enemy
            for stat_name, mod_name in (("Attack", "attack"), ("Magic", "magic")):
                base_rating = enemy.check_mod(mod_name, enemy=caster)
                effect = enemy.stat_effects[stat_name]
                penalty = max(
                    1,
                    int(base_rating * 0.25),
                )
                effect.active = True
                effect.duration = max(int(effect.duration or 0), 3)
                effect.extra = min(int(effect.extra or 0), -penalty)
                effect.source = self.name
            weakened.append(enemy.name)

        message = f"Divine Protection II greatly fortifies {caster.name} for five turns.\n"
        if weakened:
            message += f"Sacred pressure weakens {', '.join(weakened)} for three turns.\n"
        return message


class IceBlock:
    def __new__(cls):
        return _load_yaml_ability("ice_block.yaml", cls_name="IceBlock")


class Vulcanize:
    """Data-driven (vulcanize.yaml) - self fire-damage + defense buff."""

    def __new__(cls):
        return _load_yaml_ability("vulcanize.yaml", cls_name="Vulcanize")


class WindSpeed:
    def __new__(cls):
        return _load_yaml_ability("wind_speed.yaml", cls_name="WindSpeed")


class Haste:
    """Data-driven (haste.yaml)"""

    def __new__(cls):
        return _load_yaml_ability("haste.yaml", cls_name="Haste")


class StoneSkin(Spell):
    def __init__(self):
        super().__init__(
            "Stone Skin",
            "Transform your skin into solid rock, reducing melee damage and resisting fire.",
            school="Nature",
        )
        self.cost = 21
        self.subtyp = "Support"

    def cast(self, user: Character, target: Character | None = None, **kwargs: Any) -> str:
        super().cast(user, user, **kwargs)
        user.mana.current -= self.cost
        effect = user.magic_effects["Stone Skin"]
        effect.active = True
        effect.duration = max(effect.duration, 5)
        return f"{user.name}'s skin hardens into living stone.\n"


class CalmingBreeze(Spell):
    def __init__(self):
        super().__init__(
            "Calming Breeze", "Conjure a gentle breeze that grants peaceful focus.", school="Nature"
        )
        self.cost = 18
        self.subtyp = "Support"

    def cast(self, user: Character, target: Character | None = None, **kwargs: Any) -> str:
        super().cast(user, user, **kwargs)
        if user.status_effects["Berserk"].active:
            return f"{user.name} is too berserk to call a calming breeze.\n"
        user.mana.current -= self.cost
        peaceful = user.status_effects["Peaceful"]
        peaceful.active = True
        peaceful.duration = max(peaceful.duration, 5)
        return f"A calming breeze steadies {user.name}.\n"


class Windswept(Spell):
    def __init__(self):
        super().__init__(
            "Windswept", "Launch the target on a mighty gust of wind.", school="Nature"
        )
        self.cost = 15
        self.subtyp = "Wind"

    def cast(self, user: Character, target: Character | None = None, **kwargs: Any) -> str:
        super().cast(user, target or user, **kwargs)
        user.mana.current -= self.cost
        engine = kwargs.get("battle_engine")
        target = target or user
        if target is user:
            user.flying = True
            return f"The wind lifts {user.name} away from danger.\n"
        chance = min(0.70, 0.25 + (user.stats.wisdom * 0.01))
        if random.random() < chance:
            target.health.current = 0
            if engine is not None:
                target.windswept_ejected = True
            return f"{target.name} is swept out of the battle by a mighty gust.\n"
        msg, damage = _simple_spell_damage(user, target, dmg_mod=1.1, typ="Wind")
        return msg + (f"{target.name} crashes back down from the gust.\n" if damage > 0 else "")


class Regrowth:
    """Data-driven (regrowth.yaml)"""

    def __new__(cls):
        return _load_yaml_ability("regrowth.yaml", cls_name="Regrowth")


class NatureShield(Spell):
    def __init__(self):
        super().__init__(
            "Nature Shield",
            "Conjure life-orbs that intercept attack spells and heal you.",
            school="Nature",
        )
        self.cost = 28
        self.subtyp = "Support"

    def cast(self, user: Character, target: Character | None = None, **kwargs: Any) -> str:
        super().cast(user, user, **kwargs)
        user.mana.current -= self.cost
        shield = user.magic_effects["Nature Shield"]
        shield.active = True
        shield.duration = max(shield.duration, 6)
        shield.extra = max(int(shield.extra or 0), 3)
        return f"Three living orbs circle {user.name}.\n"


# Movement spells
class Sanctuary:
    """Data-driven (sanctuary.yaml) - return to town, full heal."""

    def __new__(cls):
        return _load_yaml_ability("sanctuary.yaml", cls_name="Sanctuary")


class Teleport:
    """Data-driven (teleport.yaml) - set/restore location."""

    def __new__(cls):
        return _load_yaml_ability("teleport.yaml", cls_name="Teleport")


# Illusion spells
class MirrorImage:
    def __new__(cls):
        return _load_yaml_ability("mirror_image.yaml", cls_name="MirrorImage")


class MirrorImage2:
    replaces = "Mirror Image"

    def __new__(cls):
        return _load_yaml_ability("mirror_image_2.yaml", cls_name="MirrorImage2")


class AstralShift:
    def __new__(cls):
        return _load_yaml_ability("astral_shift.yaml", cls_name="AstralShift")


# Status spells
class Hex:
    """Data-driven (hex.yaml) - multi-status spell (Poison/Blind/Silence)."""

    def __new__(cls):
        return _load_yaml_ability("hex.yaml", cls_name="Hex")


class BlindingFog:
    def __new__(cls):
        return _load_yaml_ability("blinding_fog.yaml", cls_name="BlindingFog")


class PoisonBreath:
    """Rank 2 Enemy Spell — data-driven (poison_breath.yaml)"""

    def __new__(cls):
        return _load_yaml_ability("poison_breath.yaml", cls_name="PoisonBreath")


class DiseaseBreath:
    """Status spell — data-driven (disease_breath.yaml)"""

    def __new__(cls):
        return _load_yaml_ability("disease_breath.yaml", cls_name="DiseaseBreath")


class Sleep:
    def __new__(cls):
        return _load_yaml_ability("sleep.yaml", cls_name="Sleep")


class Stupefy:
    def __new__(cls):
        return _load_yaml_ability("stupefy.yaml", cls_name="Stupefy")


class WeakenMind:
    def __new__(cls):
        return _load_yaml_ability("weaken_mind.yaml", cls_name="WeakenMind")


class Enfeeble:
    def __new__(cls):
        return _load_yaml_ability("enfeeble.yaml", cls_name="Enfeeble")


class Ruin:
    """Status spell — data-driven (ruin.yaml)"""

    def __new__(cls):
        return _load_yaml_ability("ruin.yaml", cls_name="Ruin")


class Dispel:
    def __new__(cls):
        return _load_yaml_ability("dispel.yaml", cls_name="Dispel")


class Silence:
    def __new__(cls):
        return _load_yaml_ability("silence.yaml", cls_name="Silence")


class Berserk:
    def __new__(cls):
        return _load_yaml_ability("berserk.yaml", cls_name="Berserk")


# Enemy spells
class Hellfire:
    """Devil's spell — data-driven (hellfire.yaml)"""

    def __new__(cls):
        return _load_yaml_ability("hellfire.yaml", cls_name="Hellfire")
