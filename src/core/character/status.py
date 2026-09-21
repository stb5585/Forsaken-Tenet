"""Character status, healing, and effect-lifecycle behavior."""

from __future__ import annotations

from typing import TYPE_CHECKING

from src.core.randomness import gameplay_random as random

from ..constants import (
    ELF_HEALING_RECEIVED_MULTIPLIER,
    HALF_ELF_HEALING_RECEIVED_MULTIPLIER,
    HUMAN_STATUS_RESIST_MULTIPLIER,
)
from .models import (
    POISON_HEALING_MULTIPLIER,
    STUN_IMMUNITY_TURNS_AFTER_EXPIRY,
    STUN_LEVEL_DIFF_CAP,
    STUN_LEVEL_DIFF_MULT_MAX,
    STUN_LEVEL_DIFF_MULT_MIN,
    STUN_LEVEL_DIFF_SCALE,
    _class_name,
    _combat_level,
    scaled_decay_function,
)

if TYPE_CHECKING:
    from .core import Character
    from .models import EffectMap


class CharacterStatusMixin:
    def enter_defensive_stance(
        self, duration: int = 1, reduction: float | None = None, source: str = "Defend"
    ) -> str:
        """
        Put the character into a defensive stance for a number of turns.

        Args:
            duration: Number of turns the stance lasts
            reduction: Optional damage reduction percentage (0.0 - 1.0)
            source: Source name for status event logging

        Returns:
            str: Message describing the stance
        """
        if reduction is None:
            reduction = self.defensive_stance_reduction

        self.status_effects["Defend"].active = True
        self.status_effects["Defend"].duration = max(
            self.status_effects["Defend"].duration, duration
        )
        self.status_effects["Defend"].extra = reduction
        self._emit_status_event(self, "Defend", applied=True, duration=duration, source=source)

        return f"{self.name} takes a defensive stance.\n"

    def get_defensive_reduction(self) -> float:
        """Return total defensive damage reduction from stances/modifiers."""
        reduction = 0.0
        if self.status_effects.get("Defend") and self.status_effects["Defend"].active:
            reduction += float(self.status_effects["Defend"].extra)
            if "Improved Defend" in self.spellbook.get("Skills", {}):
                reduction += 0.15
        if hasattr(self, "jump_defend_active") and self.jump_defend_active:
            reduction += 0.15
        return min(0.75, reduction)

    def incapacitated(self) -> bool:
        return any(
            [
                self.status_effects["Sleep"].active,
                self.status_effects.get("Polymorph") and self.status_effects["Polymorph"].active,
                self.physical_effects["Prone"].active,
                self.status_effects["Stun"].active,
            ]
        )

    def check_active(self) -> tuple[bool, str]:
        """
        Check if the character can act in combat this turn.

        Returns:
            tuple: (is_active: bool, message: str)
                  - (True, "") if character can act
                  - (False, reason) if character cannot act
        """
        distracted = int(getattr(self, "_distracted_turns", 0) or 0)
        if distracted > 0:
            self._distracted_turns = distracted - 1
            return False, f"{self.name} is distracted and cannot act."
        if self.status_effects["Sleep"].active:
            try:
                from ..classes import astromancer

                if not astromancer.silent_lucidity_active(self):
                    return False, f"{self.name} is asleep and cannot act."
            except Exception:
                return False, f"{self.name} is asleep and cannot act."
        polymorph = self.status_effects.get("Polymorph")
        if polymorph is not None and polymorph.active:
            return False, f"{self.name} is polymorphed and cannot act."
        if self.physical_effects["Prone"].active and not getattr(
            self, "_primal_trance_active", False
        ):
            return False, f"{self.name} is prone and cannot act."
        if self.status_effects["Stun"].active:
            return False, f"{self.name} is stunned and cannot act."
        fear = self.status_effects.get("Fear")
        if fear is not None and fear.active:
            if random.random() < 0.5:
                return False, f"{self.name} cowers in fear and cannot act."
            self._fear_flee_attempt = True
            return False, f"{self.name} tries to flee in fear."
        fractures = getattr(self, "fractures", {})
        if fractures.get("Skull") and random.random() < 0.25:
            return False, f"{self.name} is incapacitated by a fractured skull."
        if self.magic_effects["Ice Block"].active:
            return False, f"{self.name} is encased in ice and does nothing.\n"
        return True, ""

    def healing_received_multiplier(self) -> float:
        """Return multiplier applied to healing received (e.g., poison reduces healing)."""
        mult = 1.0
        if self.status_effects.get("Poison") and self.status_effects["Poison"].active:
            mult *= POISON_HEALING_MULTIPLIER
        # Racial traits (7 sins / 7 virtues)
        try:
            race_name = getattr(getattr(self, "race", None), "name", None)
            if race_name == "Elf":
                mult *= ELF_HEALING_RECEIVED_MULTIPLIER
            elif race_name == "Half Elf":
                mult *= HALF_ELF_HEALING_RECEIVED_MULTIPLIER
        except Exception:
            pass
        try:
            from ..classes import lycan

            mult *= lycan.healing_multiplier(self)
        except Exception:
            pass
        return mult

    # ── Economy helpers shared by presentation and headless tools ─────
    def shop_price_scale(self) -> float:
        """Return multiplicative scale applied to shop buy prices based on charisma (race-aware)."""
        cha = int(getattr(self.stats, "charisma", 0) or 0)
        try:
            if getattr(getattr(self, "race", None), "name", None) == "Gnome":
                from ..constants import GNOME_GOLD_CHARISMA_MULTIPLIER

                cha = int(cha * GNOME_GOLD_CHARISMA_MULTIPLIER)
        except Exception:
            pass
        return scaled_decay_function(cha // 2)

    def shop_sell_price_multiplier(self) -> float:
        """Return multiplicative scale applied to shop sell prices based on charisma (race-aware)."""
        cha = int(getattr(self.stats, "charisma", 0) or 0)
        try:
            if getattr(getattr(self, "race", None), "name", None) == "Gnome":
                from ..constants import GNOME_GOLD_CHARISMA_MULTIPLIER

                cha = int(cha * GNOME_GOLD_CHARISMA_MULTIPLIER)
        except Exception:
            pass
        return 1.0 + (0.025 * cha)

    def apply_stun(
        self,
        duration: int,
        *,
        source: str = "Unknown",
        applier: Character | None = None,
    ) -> bool:
        """
        Apply stun with basic stun-lock prevention.

        Uses ``status_effects["Stun"].extra`` as a short post-stun immunity
        counter (decremented in ``effects()`` each turn when not stunned).
        """
        stun = self.status_effects.get("Stun")
        if stun is None:
            return False
        if self.has_status_protection("Stun"):
            return False
        if stun.active:
            return False
        if stun.extra > 0:
            return False

        stun.active = True
        stun.duration = max(int(duration), stun.duration)
        stun.extra = 0

        try:
            (applier or self)._emit_status_event(
                self, "Stun", applied=True, duration=stun.duration, source=source
            )
        except Exception:
            pass
        return True

    def has_status_protection(self, status_name: str) -> bool:
        """Return whether innate immunity or equipped item mods block a status."""
        normalized = str(status_name or "").strip()
        if not normalized:
            return False
        if normalized in getattr(self, "status_immunity", []):
            return True
        if "Status-All" in getattr(self, "status_immunity", []):
            return True
        try:
            from ..classes import promotion_kits

            if int(promotion_kits.combat_state(self).get("purge_immunity_turns", 0) or 0):
                return True
        except Exception:
            pass
        if self.magic_effects.get("Tree of Life") and self.magic_effects["Tree of Life"].active:
            return True
        if (
            normalized == "Berserk"
            and self.status_effects.get("Peaceful")
            and self.status_effects["Peaceful"].active
        ):
            return True
        if normalized == "Fear" and int(getattr(self, "_courage_turns", 0) or 0) > 0:
            return True

        equipment = getattr(self, "equipment", {}) or {}
        for item in equipment.values():
            mod = str(getattr(item, "mod", "") or "")
            tokens = {
                token.strip()
                for token in mod.replace(",", " ").replace(";", " ").split()
                if token.strip()
            }
            if "Status-All" in tokens or f"Status-{normalized}" in tokens:
                return True
        return False

    def stun_contest_success(
        self,
        applier: Character | None,
        attacker_roll: int,
        defender_roll: int,
    ) -> bool:
        """
        Resolve a stun contest roll with level-difference bias.

        The caller computes rolls (STR vs CON, SPD vs CON, etc.). This helper
        biases the attacker's roll based on applier-vs-target level gap.
        """
        if applier is None:
            return attacker_roll > defender_roll

        diff = _combat_level(applier) - _combat_level(self)
        diff = max(-STUN_LEVEL_DIFF_CAP, min(STUN_LEVEL_DIFF_CAP, diff))
        mult = 1.0 + (diff * STUN_LEVEL_DIFF_SCALE)
        mult = max(STUN_LEVEL_DIFF_MULT_MIN, min(STUN_LEVEL_DIFF_MULT_MAX, mult))
        adj_attacker = int(attacker_roll * mult)
        # Racial status-resist tuning: Humans are slightly more susceptible to control.
        try:
            if getattr(getattr(self, "race", None), "name", None) == "Human":
                defender_roll = int(defender_roll * HUMAN_STATUS_RESIST_MULTIPLIER)
        except Exception:
            pass
        return adj_attacker > defender_roll

    def effect_handler(self, effect: str) -> EffectMap:
        effect_dicts = [
            self.status_effects,
            self.physical_effects,
            self.stat_effects,
            self.magic_effects,
            self.class_effects,
        ]
        for effect_dict in effect_dicts:
            if effect in effect_dict:
                return effect_dict
        raise NotImplementedError(f"{effect} does not exist in character attributes.")

    def can_be_disarmed(self) -> bool:
        if "Disarm" in getattr(self, "status_immunity", []):
            return False
        class_name = getattr(getattr(self, "cls", None), "name", "")
        if "Monk" in class_name:
            return False
        weapon = self.equipment.get("Weapon") if isinstance(self.equipment, dict) else None
        if weapon is None:
            return False
        if getattr(weapon, "subtyp", None) in ["Natural", "Summon", "None"]:
            return False
        return bool(getattr(weapon, "disarm", True))

    def is_disarmed(self) -> bool:
        return bool(self.physical_effects["Disarm"].active and self.can_be_disarmed())

    def effects(self, end: bool = False) -> str | None:
        """
        Silence, Blind, and Disarm can be indefinite unless cured (duration=-1)
        """
        from ..classes import ability_mechanics

        self._last_bleed_tick_damage = 0
        effect_dicts = [
            self.status_effects,
            self.physical_effects,
            self.stat_effects,
            self.magic_effects,
            self.class_effects,
        ]

        def default(effect=None, end_combat=False):
            if end_combat:
                for effect_dict in effect_dicts:
                    for effect in effect_dict.keys():
                        if effect_dict[effect].active:
                            self._emit_status_event(
                                self, effect, applied=False, source="Combat End"
                            )
                        effect_dict[effect].active = False
                        effect_dict[effect].duration = 0
                        effect_dict[effect].extra = 0
                        effect_dict[effect].source = ""
                for skill_group in getattr(self, "spellbook", {}).values():
                    for skill in getattr(skill_group, "values", lambda: [])():
                        if getattr(skill, "charging", False):
                            cancel_charge = getattr(skill, "cancel_charge", None)
                            if callable(cancel_charge):
                                try:
                                    cancel_charge(self)
                                    continue
                                except Exception:
                                    pass
                            skill.charging = False
                            if hasattr(skill, "charge_turns"):
                                skill.charge_turns = 0
                            if hasattr(skill, "charge_target"):
                                skill.charge_target = None
                self.grandmaster_technique_stacks = {}
                self._hemorrhage_thirst_streak = 0
                self._corruption_payload = None
            else:
                effect_dict = self.effect_handler(effect=effect)
                if effect_dict[effect].active:
                    self._emit_status_event(self, effect, applied=False, source="Duration Expired")
                effect_dict[effect].active = False
                effect_dict[effect].duration = 0
                effect_dict[effect].extra = 0
                effect_dict[effect].source = ""
                if effect == "DOT":
                    self._corruption_payload = None

        if end:
            try:
                from ..classes import pathfinder

                pathfinder.tick_combat_state(self, end=True)
            except Exception:
                pass
            try:
                from ..classes import healer

                healer.tick_combat_state(self, end=True)
            except Exception:
                pass
            try:
                from ..classes import mage_mechanics

                mage_mechanics.tick_combat_state(self, end=True)
            except Exception:
                pass
            default(end_combat=True)
            self.temporary_health = None
            self.fractures = {}
            for attr in (
                "soul_bound_to",
                "soul_siphon",
                "shadow_curtain_turns",
                "shade_of_ahool_turns",
                "warlock_eclipse_turns",
                "mystical_vitality_turns",
                "demon_grease_turns",
                "soul_vessel_turns",
                "temporary_undead_allies",
                "haunted_turns",
                "_temporary_stasis_turns",
                "_soul_binding_caster",
            ):
                if hasattr(self, attr):
                    delattr(self, attr)
            try:
                from ..classes import promotion_kits

                promotion_kits.clear_combat_state(self)
            except Exception:
                pass
            ability_mechanics.sync_exploration_flags(self)
        else:
            from ..classes import grandmaster

            status_text = ""
            stasis_turns = max(
                0,
                int(getattr(self, "_temporary_stasis_turns", 0) or 0),
            )
            if stasis_turns:
                self._temporary_stasis_turns = stasis_turns - 1
                if self._temporary_stasis_turns <= 0:
                    delattr(self, "_temporary_stasis_turns")
                    stun = self.status_effects.get("Stun")
                    if stun is not None and stun.source == "Temporary Stasis":
                        stun.active = False
                        stun.duration = 0
                        stun.source = ""
                    return f"Time resumes around {self.name}.\n"
                return f"{self.name} remains suspended outside time.\n"
            haunted_turns = max(0, int(getattr(self, "haunted_turns", 0) or 0))
            if haunted_turns:
                self.haunted_turns = haunted_turns - 1
                if random.randint(1, 20) > int(getattr(self.stats, "wisdom", 0) or 0):
                    fear = self.status_effects["Fear"]
                    fear.active = True
                    fear.duration = max(1, int(fear.duration or 0))
                    fear.source = "Sciophobia"
                    status_text += f"The haunting fills {self.name} with fear.\n"
            try:
                from ..classes import promotion_kits

                status_text += promotion_kits.tick_combat_state(self)
            except Exception:
                pass
            try:
                from ..classes import mage_mechanics

                status_text += mage_mechanics.tick_combat_state(self)
            except Exception:
                pass
            try:
                from ..classes import healer

                status_text += healer.tick_combat_state(self)
            except Exception:
                pass
            try:
                from ..classes import pathfinder

                status_text += pathfinder.tick_combat_state(self)
            except Exception:
                pass
            temporary_health = getattr(self, "temporary_health", None)
            if isinstance(temporary_health, dict):
                temporary_health["turns"] = max(0, int(temporary_health.get("turns", 0) or 0) - 1)
                if temporary_health["turns"] <= 0:
                    source = str(temporary_health.get("source") or "inflated health")
                    status_text += f"{self.name}'s {source} dissolves.\n"
                    self.temporary_health = None
            polymorph = self.status_effects.get("Polymorph")
            if polymorph is not None and polymorph.active:
                polymorph.duration -= 1
                if polymorph.duration <= 0:
                    status_text += f"{self.name} returns to their true form.\n"
                    default(effect="Polymorph")
            for expired in grandmaster.tick_technique_stacks(self):
                status_text += f"{self.name}'s {expired} technique fades.\n"
            if self.status_effects["Doom"].active:
                self.status_effects["Doom"].duration -= 1
                if not self.status_effects["Doom"].duration:
                    status_text += f"The Doom countdown has expired and so has {self.name}!\n"
                    self.health.current = 0
                    return status_text
            from ..classes import crossbow

            status_text += crossbow.tick_delayed_bolts(self)
            if not self.is_alive():
                return status_text
            toxin_death = int(getattr(self, "_toxin_death_turns", 0) or 0)
            if toxin_death > 0:
                self._toxin_death_turns = toxin_death - 1
                if self._toxin_death_turns <= 0:
                    self.health.current = 0
                    status_text += f"{self.name} succumbs to the toxin.\n"
                    return status_text
            toxin_petrify = int(getattr(self, "_toxin_petrify_turns", 0) or 0)
            if toxin_petrify > 0:
                self._toxin_petrify_turns = toxin_petrify - 1
                if self._toxin_petrify_turns <= 0:
                    stone = self.status_effects.get("Stone")
                    if stone is not None:
                        stone.active = True
                    status_text += f"{self.name} is petrified by the toxin.\n"
            if self.magic_effects["Ice Block"].active:
                self.magic_effects["Ice Block"].duration -= 1
                gain_perc = 0.10 * (1 + (self.stats.intel / 30))
                health_gain = min(
                    self.health.max - self.health.current, int(self.health.max * gain_perc)
                )
                health_gain = int(health_gain * self.healing_received_multiplier())
                self.health.current += health_gain
                mana_gain = min(self.mana.max - self.mana.current, int(self.mana.max * gain_perc))
                self.mana.current += mana_gain
                status_text += f"{self.name} regens {health_gain} health and {mana_gain} mana.\n"
                if health_gain > 0:
                    self._emit_status_tick_event(
                        self, "Ice Block", health_gain, "healing", source="Ice Block"
                    )
                if not self.magic_effects["Ice Block"].duration:
                    status_text += f"The ice block around {self.name} melts.\n"
                    default(effect="Ice Block")
                else:
                    return status_text
            shackles = getattr(self, "conjured_shackles", None)
            if isinstance(shackles, dict) and self.physical_effects["Prone"].active:
                shackles["turns"] = max(0, int(shackles.get("turns", 0) or 0) - 1)
                unbreakable = bool(shackles.get("unbreakable", False))
                strength_roll = (
                    -1
                    if unbreakable
                    else random.randint(
                        max(0, self.stats.strength // 2),
                        max(1, self.stats.strength),
                    )
                )
                if not unbreakable and strength_roll >= int(shackles.get("difficulty", 1) or 1):
                    self.physical_effects["Prone"].active = False
                    self.conjured_shackles = None
                    status_text += f"{self.name} breaks free of the conjured shackles.\n"
                elif shackles["turns"] <= 0:
                    self.physical_effects["Prone"].active = False
                    self.conjured_shackles = None
                    status_text += f"The shackles around {self.name} disappear.\n"
                else:
                    status_text += (
                        f"Reality itself keeps {self.name} shackled.\n"
                        if unbreakable
                        else f"{self.name} struggles against the conjured shackles.\n"
                    )
            if (
                self.physical_effects["Prone"].active
                and not isinstance(getattr(self, "conjured_shackles", None), dict)
                and not getattr(self, "_primal_trance_active", False)
                and all(
                    [
                        not self.status_effects["Stun"].active,
                        not self.status_effects["Sleep"].active,
                    ]
                )
            ):
                try:
                    from ..classes import pathfinder

                    self.physical_effects["Prone"].duration = max(
                        0,
                        self.physical_effects["Prone"].duration
                        - pathfinder.bounce_back_bonus(self),
                    )
                except Exception:
                    pass
                if not random.randint(0, self.physical_effects["Prone"].duration) or random.randint(
                    0, self.check_mod("luck", luck_factor=10)
                ):
                    default(effect="Prone")
                    status_text += f"{self.name} is no longer prone.\n"
                else:
                    self.physical_effects["Prone"].duration -= 1
                    status_text += f"{self.name} is still prone.\n"
            if self.status_effects["Poison"].active:
                self.status_effects["Poison"].duration -= 1
                poison_damage = max(1, int(self.status_effects["Poison"].extra * 1.50))
                resist_div = max(0, self.stats.con // 15)
                if not random.randint(0, resist_div):
                    self.health.current -= poison_damage
                    status_text += (
                        f"The poison damages {self.name} for {poison_damage} health points.\n"
                    )
                    self._emit_status_tick_event(
                        self, "Poison", poison_damage, "damage", source="Poison"
                    )
                else:
                    status_text += f"{self.name} resisted the poison.\n"
                if not self.status_effects["Poison"].duration:
                    default(effect="Poison")
                    status_text += f"The poison has left {self.name}.\n"
            if self.magic_effects["DOT"].active:
                self.magic_effects["DOT"].duration -= 1
                dot_damage = int(self.magic_effects["DOT"].extra or 0)
                dot_source = self.magic_effects["DOT"].source
                if dot_source.lower().startswith("corruption"):
                    payload = getattr(self, "_corruption_payload", {})
                    caster = payload.get("caster") if isinstance(payload, dict) else None
                    if "Festering Anguish" in getattr(caster, "spellbook", {}).get("Skills", {}):
                        dot_damage = max(1, int(dot_damage * 1.25))
                        self.magic_effects["DOT"].extra = dot_damage
                is_burn = dot_source.lower() in {
                    "burn",
                    "fire",
                    "volcano",
                    "fireball",
                    "firestorm",
                    "hellfire",
                }
                if dot_damage <= 0:
                    # Defensive guard: DOT should always have positive damage,
                    # but some effect paths may leave .extra unset/zero.
                    default(effect="DOT")
                    self.magic_effects["DOT"].duration = 0
                else:
                    if not random.randint(0, self.check_mod("magic def") // dot_damage):
                        self.health.current -= dot_damage
                        if is_burn:
                            status_text += f"{self.name} burns for {dot_damage} health points.\n"
                        else:
                            status_text += (
                                f"The magic damages {self.name} for {dot_damage} health points.\n"
                            )
                        self._emit_status_tick_event(
                            self,
                            "DOT",
                            dot_damage,
                            "damage",
                            source="Burn" if is_burn else "DOT",
                        )
                    else:
                        if is_burn:
                            status_text += f"{self.name} resisted the flames.\n"
                        else:
                            status_text += f"{self.name} resisted the magic.\n"
                    if dot_source.lower().startswith("corruption"):
                        from ..classes import warlock

                        status_text += warlock.spread_corruption(self)
                    if not self.magic_effects["DOT"].duration:
                        default(effect="DOT")
                        if is_burn:
                            status_text += f"The flames around {self.name} burn out.\n"
                        else:
                            status_text += f"The magic affecting {self.name} has worn off.\n"
            try:
                from .. import persistent_afflictions as afflictions

                status_text += afflictions.hemorrhaging_tick(self)
                status_text += afflictions.swarms_tick(self)
                status_text += afflictions.polydipsia_tick(self)
            except Exception:
                pass
            fractures = getattr(self, "fractures", {})
            if fractures.get("Ribs") or fractures.get("Exoskeleton"):
                fracture_damage = max(1, int(self.health.max * 0.05))
                self.health.current = max(0, self.health.current - fracture_damage)
                status_text += f"{self.name}'s fracture deals {fracture_damage} damage.\n"
            hallowed_ground = self.magic_effects.get("Hallowed Ground")
            if hallowed_ground is not None and hallowed_ground.active:
                hallowed_ground.duration -= 1
                payload = hallowed_ground.extra if isinstance(hallowed_ground.extra, dict) else {}
                if payload.get("mode") == "damage":
                    damage = max(1, int(payload.get("amount", 0) or 0))
                    self.health.current -= damage
                    status_text += (
                        f"Sacred light damages {self.name} for {damage} " "holy damage.\n"
                    )
                    self._emit_status_tick_event(
                        self,
                        "Hallowed Ground",
                        damage,
                        "damage",
                        source="Hallowed Ground",
                    )
                elif payload.get("mode") == "healing":
                    healing = max(1, int(payload.get("amount", 0) or 0))
                    healing = int(healing * self.healing_received_multiplier())
                    healing = max(
                        0,
                        min(healing, self.health.max - self.health.current),
                    )
                    self.health.current += healing
                    status_text += (
                        f"Hallowed Ground heals {self.name} for {healing} " "hit points.\n"
                    )
                    if healing > 0:
                        self._emit_status_tick_event(
                            self,
                            "Hallowed Ground",
                            healing,
                            "healing",
                            source="Hallowed Ground",
                        )
                if hallowed_ground.duration <= 0:
                    status_text += "The sacred light fades from the ground.\n"
                    default(effect="Hallowed Ground")
            if self.physical_effects["Bleed"].active:
                self.physical_effects["Bleed"].duration -= 1
                bleed_damage = max(1, int(self.physical_effects["Bleed"].extra * 0.75))
                bleed_damage = max(
                    1,
                    int(bleed_damage * ability_mechanics.pain_tolerance_bleed_multiplier(self)),
                )
                if not random.randint(0, self.stats.con // 10):
                    self.health.current -= bleed_damage
                    self._last_bleed_tick_damage = bleed_damage
                    status_text += f"{self.name} bleeds for {bleed_damage} health points.\n"
                    self._emit_status_tick_event(
                        self, "Bleed", bleed_damage, "damage", source="Bleed"
                    )
                else:
                    status_text += f"{self.name} resisted the bleed.\n"
                if not self.physical_effects["Bleed"].duration:
                    default(effect="Bleed")
                    status_text += f"{self.name}'s wounds have healed and is no longer bleeding.\n"
            for effect_name, expiry_message in (
                ("Cripple", f"{self.name}'s weapon arm recovers.\n"),
                ("Maim", f"{self.name} can use their main hand again.\n"),
            ):
                effect = self.physical_effects.get(effect_name)
                if effect is None or not effect.active or effect.duration < 0:
                    continue
                effect.duration -= 1
                if not effect.duration:
                    default(effect=effect_name)
                    status_text += expiry_message
            if self.status_effects["Blind"].active:
                self.status_effects["Blind"].duration -= 1
                if not self.status_effects["Blind"].duration:
                    status_text += f"{self.name} regains sight and is no longer blind.\n"
                    default(effect="Blind")
            if self.status_effects["Blind Rage"].active:
                self.status_effects["Blind Rage"].duration -= 1
                if not self.status_effects["Blind Rage"].duration:
                    status_text += f"{self.name} calms down.\n"
                    default(effect="Blind Rage")
            if self.status_effects["Hangover"].active:
                self.status_effects["Hangover"].duration -= 1
                if not self.status_effects["Hangover"].duration:
                    status_text += f"{self.name} shakes off the hangover.\n"
                    default(effect="Hangover")
            if (not self.status_effects["Stun"].active) and self.status_effects["Stun"].extra > 0:
                # Post-stun immunity countdown (stun-lock prevention).
                self.status_effects["Stun"].extra -= 1
            if self.status_effects["Stun"].active:
                self.status_effects["Stun"].duration -= 1
                if not self.status_effects["Stun"].duration:
                    status_text += f"{self.name} is no longer stunned.\n"
                    if self.status_effects["Stun"].active:
                        self._emit_status_event(
                            self, "Stun", applied=False, source="Duration Expired"
                        )
                    self.status_effects["Stun"].active = False
                    self.status_effects["Stun"].duration = 0
                    self.status_effects["Stun"].extra = max(
                        self.status_effects["Stun"].extra, STUN_IMMUNITY_TURNS_AFTER_EXPIRY
                    )
            if self.status_effects["Sleep"].active:
                self.status_effects["Sleep"].duration -= 1
                if not self.status_effects["Sleep"].duration:
                    status_text += f"{self.name} is no longer asleep.\n"
                    default(effect="Sleep")
            if (
                self.status_effects["Silence"].active
                and self.status_effects["Silence"].duration > 0
            ):
                self.status_effects["Silence"].duration -= 1
                if not self.status_effects["Silence"].duration:
                    status_text += f"{self.name} can speak again.\n"
                    default(effect="Silence")
            if self.status_effects["Berserk"].active:
                self.status_effects["Berserk"].duration -= 1
                if not self.status_effects["Berserk"].duration:
                    status_text += f"{self.name} has regained their composure.\n"
                    default(effect="Berserk")
            if self.status_effects["Peaceful"].active:
                self.status_effects["Peaceful"].duration -= 1
                if not self.status_effects["Peaceful"].duration:
                    status_text += f"{self.name}'s peaceful focus fades.\n"
                    default(effect="Peaceful")
            if self.status_effects["Defend"].active:
                if (
                    ability_mechanics.has_skill(self, "Defensive Regen")
                    and self.health.current < self.health.max
                ):
                    heal = max(1, int(self.health.max * 0.05))
                    heal = min(heal, self.health.max - self.health.current)
                    self.health.current += heal
                    status_text += f"{self.name}'s defensive focus restores {heal} health.\n"
                    try:
                        from ..classes import promotion_kits

                        status_text += promotion_kits.record_defensive_regen(
                            self,
                            heal,
                        )
                    except Exception:
                        pass
                self.status_effects["Defend"].duration -= 1
                if not self.status_effects["Defend"].duration:
                    status_text += f"{self.name} lowers their guard.\n"
                    default(effect="Defend")
            if self.status_effects["Steal Success"].active:
                self.status_effects["Steal Success"].duration -= 1
                if not self.status_effects["Steal Success"].duration:
                    default(effect="Steal Success")
            if self.magic_effects["Reflect"].active:
                self.magic_effects["Reflect"].duration -= 1
                if not self.magic_effects["Reflect"].duration:
                    status_text += f"{self.name} is no longer reflecting magic.\n"
                    default(effect="Reflect")
            for element in ["Fire", "Ice", "Electric", "Water", "Earth", "Wind"]:
                effect_name = f"Resist {element}"
                if self.magic_effects[effect_name].active:
                    self.magic_effects[effect_name].duration -= 1
                    if not self.magic_effects[effect_name].duration:
                        status_text += f"{self.name}'s {element.lower()} resistance fades.\n"
                        default(effect=effect_name)
            if self.magic_effects["Stone Skin"].active:
                self.magic_effects["Stone Skin"].duration -= 1
                if not self.magic_effects["Stone Skin"].duration:
                    status_text += f"{self.name}'s stone skin crumbles away.\n"
                    default(effect="Stone Skin")
            if self.magic_effects["Nature Shield"].active:
                self.magic_effects["Nature Shield"].duration -= 1
                if (
                    self.magic_effects["Nature Shield"].extra <= 0
                    or not self.magic_effects["Nature Shield"].duration
                ):
                    status_text += f"{self.name}'s nature shield fades.\n"
                    default(effect="Nature Shield")
            if self.magic_effects["Tree of Life"].active:
                heal = max(1, int(self.health.max * 0.33))
                heal = min(heal, self.health.max - self.health.current)
                self.health.current += heal
                status_text += f"Tree of Life restores {heal} health to {self.name}.\n"
                if heal > 0:
                    self._emit_status_tick_event(
                        self, "Tree of Life", heal, "healing", source="Tree of Life"
                    )
                self.magic_effects["Tree of Life"].duration -= 1
                if not self.magic_effects["Tree of Life"].duration:
                    status_text += f"{self.name} returns from the Tree of Life.\n"
                    default(effect="Tree of Life")
            if self.magic_effects["Totem"].active:
                self.magic_effects["Totem"].duration -= 1
                if not self.magic_effects["Totem"].duration:
                    status_text += f"{self.name}'s totem crumbles to dust.\n"
                    default(effect="Totem")
            if self.magic_effects["Astral Shift"].active:
                self.magic_effects["Astral Shift"].duration -= 1
                if not self.magic_effects["Astral Shift"].duration:
                    status_text += f"{self.name} fully returns from the astral plane.\n"
                    default(effect="Astral Shift")
            for stat in ["Attack", "Defense", "Magic", "Magic Defense", "Speed"]:
                if self.stat_effects[stat].active:
                    self.stat_effects[stat].duration -= 1
                    if not self.stat_effects[stat].duration:
                        default(effect=stat)
            for attr in ("_guard_suppressed",):
                value = int(getattr(self, attr, 0) or 0)
                if value > 0:
                    setattr(self, attr, max(0, value - 1))
            for attr in (
                "shadow_curtain_turns",
                "warlock_eclipse_turns",
                "mystical_vitality_turns",
                "demon_grease_turns",
                "soul_vessel_turns",
            ):
                value = int(getattr(self, attr, 0) or 0)
                if value > 0:
                    setattr(self, attr, value - 1)
            for attr in ("_reavers_mark", "_riposte_line", "_brace_art"):
                state = getattr(self, attr, None)
                if isinstance(state, dict):
                    state["turns"] = int(state.get("turns", 0) or 0) - 1
                    if state["turns"] <= 0:
                        try:
                            delattr(self, attr)
                        except AttributeError:
                            pass
            soul_siphon = getattr(self, "soul_siphon", None)
            if isinstance(soul_siphon, dict):
                soul_siphon["turns"] = int(soul_siphon.get("turns", 0) or 0) - 1
                if soul_siphon["turns"] <= 0:
                    delattr(self, "soul_siphon")
            try:
                from ..classes import promotion_kits

                promotion_kits.tick_magical_invigoration(self)
            except Exception:
                pass
            if self.magic_effects["Regen"].active:
                self.magic_effects["Regen"].duration -= 1
                heal = self.magic_effects["Regen"].extra
                heal = int(heal * self.healing_received_multiplier())
                heal = min(heal, self.health.max - self.health.current)
                self.health.current += heal
                status_text += f"{self.name}'s health has regenerated by {heal}.\n"
                if heal > 0:
                    self._emit_status_tick_event(self, "Regen", heal, "healing", source="Regen")
                    try:
                        status_text += promotion_kits.record_magical_invigoration_tick(self)
                    except Exception:
                        pass
                if not self.magic_effects["Regen"].duration:
                    status_text += "Regeneration spell ends.\n"
                    default(effect="Regen")
            if self.class_effects["Power Up"].active:
                if _class_name(self) == "Lycan":
                    self.class_effects["Power Up"].duration += 1
                elif _class_name(self) == "Dragoon":
                    pass
                else:
                    self.class_effects["Power Up"].duration -= 1
                if _class_name(self) == "Knight Enchanter" and self.power_up:
                    missing_mana = self.mana.max - self.mana.current
                    mana_regen = (
                        max(1, min(self.class_effects["Power Up"].extra, missing_mana))
                        if missing_mana > 0
                        else 0
                    )
                    self.mana.current += mana_regen
                    status_text += f"{self.name} regens {mana_regen} mana.\n"
                    if mana_regen > 0:
                        self._emit_status_tick_event(
                            self, "Power Up", mana_regen, "mana", source="Power Up"
                        )
                if _class_name(self) == "Archbishop" and self.power_up:
                    health_regen = min(
                        int(self.health.max * 0.10), self.health.max - self.health.current
                    )
                    health_regen = int(health_regen * self.healing_received_multiplier())
                    mana_regen = min(int(self.mana.max * 0.10), self.mana.max - self.mana.current)
                    self.health.current += health_regen
                    self.mana.current += mana_regen
                    status_text += (
                        f"{self.name} regens {health_regen} health and {mana_regen} mana.\n"
                    )
                    if health_regen > 0:
                        self._emit_status_tick_event(
                            self, "Power Up", health_regen, "healing", source="Power Up"
                        )
                    if mana_regen > 0:
                        self._emit_status_tick_event(
                            self, "Power Up", mana_regen, "mana", source="Power Up"
                        )
                if not self.class_effects["Power Up"].duration:
                    if _class_name(self) == "Crusader" and self.power_up:
                        status_text += (
                            f"The shield around {self.name} explodes, dealing "
                            f"{self.class_effects['Power Up'].extra} damage to the enemy.\n"
                        )
                    default(effect="Power Up")
            return status_text

    def special_effects(self, target: Character) -> str:
        special_str = ""
        return special_str

    def familiar_turn(self, target: Character) -> str:
        familiar_str = ""
        return familiar_str
