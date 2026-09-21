"""Player familiar, transformation, combat-end, and special-power behavior."""

from src.core.randomness import gameplay_random as random

from .. import abilities
from ..character import armor_resistance_modifier, armor_spell_modifier
from ..classes import (
    ability_mechanics,
    archdruid,
    bard,
    class_rings,
    footpad,
    healer,
    lycan,
    mage_mechanics,
    nature_totems,
    paladin,
    promotion_kits,
    transformation,
    wizard,
)

_SPECIAL_POWER_ABILITIES = {
    "Berserker": abilities.BloodRage,
    "Grandmaster of Arms": abilities.ArsenalMastery,
    "Crusader": abilities.DivineAegis,
    "Dragoon": abilities.DraconicOnslaught,
    "Stalwart Defender": abilities.ShieldMastery,
    "Wizard": abilities.SpellMastery,
    "Shadowcaster": abilities.ShadeOfAhool,
    "Demonologist": abilities.AbyssalCovenant,
    "Knight Enchanter": abilities.ArcaneBlast,
    "Thaumaturgist": abilities.EternalConduit,
    "Rogue": abilities.StrokeLuck,
    "Seeker": abilities.EyesUnseen,
    "Ninja": abilities.BladeFatalities,
    "Arcane Trickster": abilities.TrickstersGambit,
    "Hierophant": abilities.SacredOverchannel,
    "Templar": abilities.HolyRetribution,
    "Archbishop": abilities.GreatGospel,
    "Master Monk": abilities.DimMak,
    "Troubadour": abilities.MelodyInspiration,
    "Archdruid": abilities.PrimalAscendance,
    "Lycan": abilities.LunarFrenzy,
    "Astromancer": abilities.AstralJudgment,
    "Soulcatcher": abilities.SoulHarvest,
    "Beast Master": abilities.PackBond,
}


def has_special_power_reward(character) -> bool:
    """Return whether a character's terminal class has a Power Core reward."""
    class_name = getattr(getattr(character, "cls", None), "name", "")
    return class_name in _SPECIAL_POWER_ABILITIES


class PlayerCombatMixin:
    def available_transform_forms(self) -> tuple[str, ...]:
        """Return the forms currently available to the permanent class."""
        return transformation.available_forms(self)

    def select_transform_form(self, form_name: str) -> bool:
        """Select an unlocked Druid form without transforming immediately."""
        if form_name not in self.available_transform_forms():
            return False
        self._selected_transform_form = form_name
        return True

    def familiar_turn(self, enemy):
        familiar_str = ""
        self._familiar_acted = False
        if self.familiar:
            special = None
            target = enemy
            if getattr(self.familiar, "spec", "") == "Tamed":
                command_text = ability_mechanics.resolve_tamed_companion_command(self, target)
                if command_text:
                    return command_text
                if not ability_mechanics.tamed_companion_should_auto_act(self):
                    return ""
                familiar_str += f"{self.familiar.name} attacks {target.name}.\n"
                companion_damage_mod = 0.75 * promotion_kits.companion_bond_multiplier(self)
                companion_damage_mod *= ability_mechanics.tamed_companion_damage_multiplier(
                    self,
                    target,
                )
                attack_str, _hit, _crit = self.familiar.weapon_damage(
                    target,
                    dmg_mod=companion_damage_mod,
                )
                familiar_str += attack_str
                familiar_str += ability_mechanics.tamed_companion_special_turn(
                    self,
                    target,
                    hit=_hit,
                    crit=_crit,
                )
                return familiar_str

            action_chance = 0.25
            skills = self.spellbook.get("Skills", {})
            if "Familiar Bond II" in skills:
                action_chance = 0.50
            elif "Familiar Bond" in skills:
                action_chance = 1 / 3
            action_denominator = (
                2 if action_chance >= 0.50 else 3 if action_chance >= (1 / 3) else 4
            )
            if not random.randint(0, action_denominator - 1):
                if self.familiar.spec == "Defense":  # skills and spells
                    while True:
                        if not random.randint(0, 1):
                            special_list = list(self.familiar.spellbook["Spells"])
                            special_type = "Spells"
                        else:
                            special_list = list(self.familiar.spellbook["Skills"])
                            special_type = "Skills"
                        if len(special_list) == 1:
                            special = self.familiar.spellbook[special_type][special_list[0]]
                        else:
                            choice = random.choice(special_list)
                            special = self.familiar.spellbook[special_type][choice]
                        if special.name not in ["Resurrection", "Cover"]:
                            break
                if self.familiar.spec == "Support":  # just spells
                    target = self
                    if not random.randint(0, 4) and self.mana.current < self.mana.max:
                        mana_regen = int(self.mana.max * 0.05)
                        mana_regen = min(mana_regen, self.mana.max - self.mana.current)
                        self.mana.current += mana_regen
                        familiar_str += (
                            f"{self.familiar.name} restores {self.name}'s mana by {mana_regen}.\n"
                        )
                    else:
                        if self.health.current < self.health.max and random.randint(0, 1):
                            if random.randint(0, 1):
                                special = self.familiar.spellbook["Spells"]["Heal"]
                            else:
                                special = self.familiar.spellbook["Spells"]["Regen"]
                        elif not self.stat_effects["Attack"].active:
                            special = self.familiar.spellbook["Spells"]["Bless"]
                        elif (
                            self.familiar.level.level > 1
                            and not self.magic_effects["Reflect"].active
                        ):
                            special = self.familiar.spellbook["Spells"]["Reflect"]
                        elif self.familiar.level.level == 3 and random.randint(0, 1):
                            special = self.familiar.spellbook["Spells"]["Cleanse"]
                        else:
                            if random.randint(0, 1):
                                special = self.familiar.spellbook["Spells"]["Heal"]
                            else:
                                special = self.familiar.spellbook["Spells"]["Regen"]
                if self.familiar.spec == "Arcane":  # just spells
                    spell_list = list(self.familiar.spellbook["Spells"])
                    choice = random.choice(spell_list)
                    if (
                        choice == "Boost"
                        and not random.randint(0, 1)
                        and not self.stat_effects["Magic"].active
                    ):
                        special = self.familiar.spellbook["Spells"]["Boost"]
                        target = self
                    else:
                        special = self.familiar.spellbook["Spells"][choice]
                if self.familiar.spec == "Luck":
                    if not random.randint(0, 1):
                        spell_list = list(self.familiar.spellbook["Spells"])
                        choice = random.choice(spell_list)
                        special = self.familiar.spellbook["Spells"][choice]
                    else:
                        while True:
                            skill_list = list(self.familiar.spellbook["Skills"])
                            choice = random.choice(skill_list)
                            if choice == "Lockpick":
                                pass
                            else:
                                special = self.familiar.spellbook["Skills"][choice]
                                break
                if special is not None:
                    self._familiar_acted = True
                    if special.typ == "Skill":
                        familiar_str += f"{self.familiar.name} uses {special.name}.\n"
                        familiar_str += special.use(self, target=target, fam=True)
                        if special.name == "Goad" and "Indiscriminate Provocation" in skills:
                            confused = target.status_effects.get("Berserk")
                            if confused is not None:
                                confused.active = True
                                confused.duration = max(3, int(confused.duration or 0))
                                confused.source = "Indiscriminate Provocation"
                                target.confused_turns = 3
                                familiar_str += f"{target.name} is goaded into confused violence.\n"
                    elif special.typ == "Spell":
                        familiar_str += f"{self.familiar.name} casts {special.name}.\n"
                        familiar_str += special.cast(self, target=target, fam=True)
                        if (
                            self.familiar.spec == "Arcane"
                            and "Night Moves" in skills
                            and int(
                                class_rings.ensure_state(self)["data"]["Shadowcaster"].get(
                                    "eclipse_turns", 0
                                )
                                or 0
                            )
                            > 0
                        ):
                            second = self.familiar.spellbook["Spells"][
                                random.choice(list(self.familiar.spellbook["Spells"]))
                            ]
                            familiar_str += f"{self.familiar.name} casts {second.name} again.\n"
                            familiar_str += second.cast(self, target=target, fam=True)
        return familiar_str

    def transform(self, back=False):
        if back:
            return transformation.dismiss_form(self)
        forms = self.available_transform_forms()
        selected = getattr(self, "_selected_transform_form", "")
        form_name = selected if selected in forms else (forms[0] if forms else "")
        if not form_name:
            return "No transformation form has been unlocked."
        return transformation.apply_form(self, form_name)

    def check_mod(self, mod, enemy=None, typ=None, luck_factor=1, ultimate=False, ignore=False):
        class_mod = nature_totems.passive_rating_bonus(self, str(mod))
        berserk_per = (
            int(self.status_effects["Berserk"].active) * 0.1
        )  # berserk increases damage by 10%
        disarm_damage_multiplier = 0.5 if self.is_disarmed() else 1.0
        if self.cls.name == "Soulcatcher" and self.power_up:
            if enemy and getattr(enemy, "enemy_typ", None) in self.kill_dict:
                class_mod += sum(self.kill_dict[enemy.enemy_typ].values()) // 20
        class_mod += ability_mechanics.favored_enemy_bonus(self, enemy)
        if mod == "weapon":
            if getattr(self, "fractures", {}).get("Arm"):
                return 0
            weapon_mod = self.equipment["Weapon"].damage * int(not self.is_disarmed())
            weapon_mod += mage_mechanics.enhance_blade_bonus(self)
            class_mod += promotion_kits.xenid_caster_attribute_bonus(
                self,
                "strength",
            )
            if "Monk" in self.cls.name:
                class_mod += self.stats.wisdom
            # Footpad-line weapon damage is DEX-forward.
            if self.cls.name in ["Footpad", "Thief", "Rogue", "Assassin", "Ninja"]:
                class_mod += self.stats.dex
            if self.cls.name == "Berserker" and self.power_up:
                class_mod += int(
                    min(self.health.max / self.health.current, 10) * (self.player_level() // 11)
                )
            if self.cls.name in ["Dragoon", "Shadowcaster"] and self.power_up:
                class_mod += (
                    weapon_mod
                    * self.class_effects["Power Up"].active
                    * self.class_effects["Power Up"].duration
                )
            if self.cls.name == "Ninja" and self.power_up:
                class_mod += (
                    self.class_effects["Power Up"].active * self.class_effects["Power Up"].extra
                )
            if (
                self.cls.name == "Templar"
                and self.power_up
                and self.class_effects["Power Up"].active
            ):
                class_mod += self.player_level() // 5
            if (
                self.cls.name == "Hierophant"
                and self.power_up
                and self.class_effects["Power Up"].active
                and self.equipment["Weapon"].subtyp == "Staff"
            ):
                class_mod += max(1, self.stats.wisdom // 3)
            if self.cls.name == "Lycan" and self.power_up:
                class_mod += (self.player_level() // 10) * self.class_effects["Power Up"].duration
            if "Physical Damage" in self.equipment["Ring"].mod:
                weapon_mod += int(self.equipment["Ring"].mod.split(" ")[0])
            weapon_mod += self.stat_effects["Attack"].extra * self.stat_effects["Attack"].active
            from .. import persistent_afflictions as afflictions

            total_mod = (weapon_mod + class_mod + self.combat.attack) * disarm_damage_multiplier
            total_mod *= afflictions.strength_multiplier(self)
            total_mod *= class_rings.weapon_damage_multiplier(self)
            total_mod *= ability_mechanics.polearm_damage_multiplier(self)
            total_mod *= ability_mechanics.monkey_grip_damage_multiplier(self, "Weapon")
            total_mod *= 1 + ability_mechanics.drunken_brawler_damage_bonus(self)
            total_mod *= ability_mechanics.last_stand_attack_multiplier(self)
            total_mod *= 1 + bard.damage_bonus(self)
            total_mod *= ability_mechanics.arsenal_mastery_weapon_multiplier(self)
            total_mod *= ability_mechanics.pack_bond_multiplier(self)
            total_mod *= 1 + ability_mechanics.melody_inspiration_bonus(self)
            total_mod *= 1 + lycan.phase_damage_bonus(self) + lycan.frenzy_damage_bonus(self)
            total_mod *= paladin.conquest_damage_multiplier(self, enemy)
            total_mod *= promotion_kits.xenid_caster_multiplier(self, "melee")
            if (
                self.stat_effects["Attack"].active
                and self.stat_effects["Attack"].source == "Dishearten"
            ):
                total_mod *= 0.75
            return max(0, int(total_mod * (1 + berserk_per)))
        if mod == "shield":
            if getattr(self, "fractures", {}).get("Arm"):
                return 0
            if int(getattr(self, "_guard_suppressed", 0) or 0) > 0:
                return 0
            block_mod = 0
            if self.equipment["OffHand"] and self.equipment["OffHand"].subtyp == "Shield":
                block_mod = round(self.equipment["OffHand"].mod * 100)
            if self.equipment["Ring"] and self.equipment["Ring"].mod == "Block":
                block_mod += 25
            block_mod += ability_mechanics.last_stand_block_bonus(self)
            block_mod += ability_mechanics.shield_mastery_block_bonus(self)
            try:
                from ..progression import has_talent

                if (
                    int(
                        promotion_kits.combat_state(self).get(
                            "hold_the_line",
                            0,
                        )
                        or 0
                    )
                    > 0
                ):
                    block_mod += 10
                    if has_talent(self, "sentinel.resolute-guard"):
                        block_mod += 5
            except Exception:
                pass
            return max(0, block_mod)
        if mod == "offhand":
            if "Monk" in self.cls.name:
                class_mod += self.stats.wisdom
            if self.cls.name in ["Spellblade", "Knight Enchanter"]:
                class_mod += (self.level.level + ((self.level.pro_level - 1) * 20)) * (
                    self.mana.current / self.mana.max
                )
            if self.cls.name in ["Thief", "Rogue", "Assassin", "Ninja", "Druid", "Lycan"]:
                class_mod += self.stats.dex // 2
            try:
                class_mod += promotion_kits.xenid_caster_attribute_bonus(
                    self,
                    "strength",
                )
                off_mod = self.equipment["OffHand"].damage
                if (
                    self.equipment["Ring"] is not None
                    and "Physical Damage" in self.equipment["Ring"].mod
                ):
                    off_mod += int(self.equipment["Ring"].mod.split(" ")[0])
                off_mod += self.stat_effects["Attack"].extra * self.stat_effects["Attack"].active
                total_offhand = (off_mod + class_mod + self.combat.attack) * (
                    footpad.offhand_damage_multiplier(self) + berserk_per
                )
                total_offhand *= ability_mechanics.monkey_grip_damage_multiplier(self, "OffHand")
                total_offhand *= ability_mechanics.arsenal_mastery_weapon_multiplier(self)
                total_offhand *= ability_mechanics.pack_bond_multiplier(self)
                total_offhand *= promotion_kits.xenid_caster_multiplier(
                    self,
                    "melee",
                )
                if (
                    self.stat_effects["Attack"].active
                    and self.stat_effects["Attack"].source == "Dishearten"
                ):
                    total_offhand *= 0.75
                return max(0, int(total_offhand))
            except AttributeError:
                return 0
        if mod == "armor":
            armor_mod = self.equipment["Armor"].armor
            armor_mod += mage_mechanics.enhance_armor_bonus(self)
            helmet = self.equipment.get("Helmet")
            if helmet is not None and getattr(helmet, "subtyp", "None") != "None":
                armor_mod += getattr(helmet, "armor", 0)
            if self.cls.name in ["Warlock", "Shadowcaster"]:
                if (
                    self.familiar
                    and self.familiar.spec == "Homunculus"
                    and random.randint(0, 1)
                    and self.familiar.level.pro_level > 1
                ):
                    fam_mod = random.randint(0, 3) ** self.familiar.level.pro_level
                    class_mod += fam_mod
            if (
                self.cls.name == "Berserker"
                and self.power_up
                and (self.health.current / self.health.max) < 0.3
            ):
                class_mod += self.player_level() // 11
            if self.cls.name == "Dragoon" and self.power_up:
                class_mod = (
                    armor_mod
                    * self.class_effects["Power Up"].active
                    * self.class_effects["Power Up"].duration
                )
            if (
                self.equipment["Ring"] is not None
                and "Physical Defense" in self.equipment["Ring"].mod
            ):
                armor_mod += int(self.equipment["Ring"].mod.split(" ")[0])
            armor_mod += self.stat_effects["Defense"].extra * self.stat_effects["Defense"].active
            class_mod += ability_mechanics.last_stand_defense_bonus(self)
            if archdruid.mastery_unlocked(self, "Stone"):
                class_mod += max(1, int((armor_mod + self.combat.defense) * 0.08))
            armor_total = (armor_mod * int(not ignore)) + class_mod + self.combat.defense
            armor_total *= class_rings.armor_multiplier(self)
            armor_total *= ability_mechanics.primal_ascendance_multiplier(self, "Stone")
            armor_total *= ability_mechanics.pack_bond_multiplier(self)
            armor_total *= promotion_kits.xenid_caster_multiplier(
                self,
                "armor",
            )
            armor_total *= 1 + ability_mechanics.melody_inspiration_bonus(self)
            if self.magic_effects.get("Tree of Life") and self.magic_effects["Tree of Life"].active:
                armor_total *= 1.75
            from .. import persistent_afflictions as afflictions

            if afflictions.has_curse(self, "Elijah"):
                armor_total *= 0.65
            return max(0, int(armor_total))
        if mod == "magic":
            conduit_intel = promotion_kits.xenid_caster_attribute_bonus(
                self,
                "intel",
            )
            magic_mod = int((self.stats.intel + conduit_intel) // 4) * self.level.pro_level
            if self.equipment["OffHand"] is not None and self.equipment["OffHand"].subtyp == "Tome":
                magic_mod += self.equipment["OffHand"].mod
            if self.equipment["Weapon"] is not None and self.equipment["Weapon"].subtyp == "Staff":
                magic_mod += int(self.equipment["Weapon"].damage * 0.75)
            magic_mod += armor_spell_modifier(self.equipment.get("Armor"))
            if (
                self.equipment["Pendant"] is not None
                and "Magic Damage" in self.equipment["Pendant"].mod
            ):
                magic_mod += int(self.equipment["Pendant"].mod.split(" ")[0])
            magic_mod += self.stat_effects["Magic"].extra * self.stat_effects["Magic"].active
            if self.cls.name == "Shadowcaster" and self.class_effects["Power Up"].active:
                class_mod += magic_mod
            harmony = archdruid.harmony_bonus(self)
            if harmony:
                class_mod += int((magic_mod + self.combat.magic) * harmony)
            trickster = class_rings.arcane_trickster_magic_bonus(self)
            if trickster:
                class_mod += int((magic_mod + self.combat.magic) * trickster)
            gambit = ability_mechanics.tricksters_gambit_magic_bonus(self)
            if gambit:
                class_mod += int((magic_mod + self.combat.magic) * gambit)
            abyssal = ability_mechanics.abyssal_covenant_magic_bonus(self)
            if abyssal:
                class_mod += int((magic_mod + self.combat.magic) * abyssal)
            if ability_mechanics.power_up_active(self, "Sacred Overchannel", "Hierophant"):
                class_mod += int((magic_mod + self.combat.magic) * 0.15)
            astro = class_rings.constellation_bonus(self, typ)
            if astro:
                class_mod += int((magic_mod + self.combat.magic) * astro)
            affinity = wizard.affinity_damage_bonus(self, typ)
            if affinity:
                class_mod += int((magic_mod + self.combat.magic) * affinity)
            song = bard.damage_bonus(self)
            if song:
                class_mod += int((magic_mod + self.combat.magic) * song)
            total_magic = magic_mod + class_mod + self.combat.magic
            if typ in {"Poison", "Venom"}:
                total_magic = int(
                    total_magic * ability_mechanics.primal_ascendance_multiplier(self, "Venom")
                )
            elif typ in {"Electric", "Wind", "Water"}:
                total_magic = int(
                    total_magic * ability_mechanics.primal_ascendance_multiplier(self, "Storm")
                )
            total_magic = int(total_magic * (1 + ability_mechanics.melody_inspiration_bonus(self)))
            total_magic *= paladin.conquest_damage_multiplier(self, enemy)
            total_magic *= promotion_kits.xenid_caster_multiplier(
                self,
                "magic",
            )
            return max(0, int(total_magic))
        if mod == "magic def":
            # Wisdom is the primary magic-defense stat; charisma provides a secondary
            # willpower component so low-CHA physical builds have a tangible downside.
            conduit_wisdom = promotion_kits.xenid_caster_attribute_bonus(
                self,
                "wisdom",
            )
            conduit_charisma = promotion_kits.xenid_caster_attribute_bonus(
                self,
                "charisma",
            )
            m_def_mod = (
                self.stats.wisdom + conduit_wisdom + ((self.stats.charisma + conduit_charisma) // 2)
            ) * self.level.pro_level
            if (
                self.equipment["Pendant"] is not None
                and "Magic Defense" in self.equipment["Pendant"].mod
            ):
                m_def_mod += int(self.equipment["Pendant"].mod.split(" ")[0])
            m_def_mod += (
                self.stat_effects["Magic Defense"].extra * self.stat_effects["Magic Defense"].active
            )
            total_magic_def = m_def_mod + class_mod + self.combat.magic_def
            try:
                if nature_totems.active_totem_aspect(self) == "Water":
                    total_magic_def = int(
                        total_magic_def * (1 + nature_totems.WATER_WARD_MAGIC_DEFENSE_BONUS)
                    )
            except Exception:
                pass
            total_magic_def = int(
                total_magic_def * ability_mechanics.primal_ascendance_multiplier(self, "Stone")
            )
            total_magic_def = int(
                total_magic_def * (1 + ability_mechanics.melody_inspiration_bonus(self))
            )
            if self.magic_effects.get("Tree of Life") and self.magic_effects["Tree of Life"].active:
                total_magic_def = int(total_magic_def * 1.75)
            total_magic_def = int(
                total_magic_def
                * promotion_kits.xenid_caster_multiplier(
                    self,
                    "magic_defense",
                )
            )
            return max(0, total_magic_def)
        if mod == "heal":
            conduit_wisdom = promotion_kits.xenid_caster_attribute_bonus(
                self,
                "wisdom",
            )
            heal_mod = (self.stats.wisdom + conduit_wisdom) * self.level.pro_level
            if self.equipment["OffHand"] is not None and self.equipment["OffHand"].subtyp == "Tome":
                heal_mod += self.equipment["OffHand"].mod
            elif (
                self.equipment["Weapon"] is not None and self.equipment["Weapon"].subtyp == "Staff"
            ):
                heal_mod += self.equipment["Weapon"].damage
            heal_mod += self.stat_effects["Magic"].extra * self.stat_effects["Magic"].active
            harmony = archdruid.harmony_bonus(self)
            if harmony:
                class_mod += int((heal_mod + self.combat.magic) * harmony)
            if ability_mechanics.power_up_active(self, "Sacred Overchannel", "Hierophant"):
                class_mod += int((heal_mod + self.combat.magic) * 0.15)
            total_heal = heal_mod + class_mod + self.combat.magic
            total_heal = int(
                total_heal * ability_mechanics.primal_ascendance_multiplier(self, "Growth")
            )
            total_heal = int(total_heal * promotion_kits.xenid_caster_multiplier(self, "healing"))
            return max(0, total_heal)
        if mod == "resist":
            if ultimate and typ == "Physical":  # ultimate weapons bypass Physical resistance
                return 0.0
            res_mod = self.resistance.get(typ, 0)
            if typ == "Death" and int(getattr(self, "resist_death_steps", 0) or 0) > 0:
                res_mod += 0.50
            if typ == "Poison":
                exploration = getattr(self, "temporary_exploration_effects", {}) or {}
                if int(exploration.get("resist_poison", 0) or 0) > 0:
                    res_mod += 0.50
            if typ == "Shadow":
                from .. import persistent_afflictions as afflictions

                res_mod += afflictions.shadow_resistance_penalty(self)
            if typ == "Fire":
                from .. import persistent_afflictions as afflictions

                res_mod += afflictions.fire_resistance_penalty(self)
            resist_effect = self.magic_effects.get(f"Resist {typ}")
            if resist_effect is not None and resist_effect.active:
                try:
                    res_mod += float(resist_effect.extra or 0)
                except (TypeError, ValueError):
                    pass
            if self.flying:
                if typ == "Wind":
                    res_mod = -0.25
            if (
                typ == "Fire"
                and self.magic_effects.get("Stone Skin")
                and self.magic_effects["Stone Skin"].active
            ):
                res_mod += 0.5
            if self.cls.name in ["Warlock", "Shadowcaster"]:
                if (
                    self.familiar
                    and self.familiar.spec == "Mephit"
                    and random.randint(0, 1)
                    and self.familiar.level.pro_level > 1
                ):
                    fam_mod = 0.25 * random.randint(1, max(1, self.stats.charisma // 10))
                    res_mod += fam_mod
            if self.equipment["Pendant"].mod.split("-")[-1] in [typ, "Elemental"] and typ in [
                "Fire",
                "Ice",
                "Electric",
                "Water",
                "Earth",
                "Wind",
            ]:
                if "Immune" in self.equipment["Pendant"].mod:
                    res_mod += 1
                elif "Resist" in self.equipment["Pendant"].mod:
                    res_mod += 0.5
            if self.equipment["OffHand"].name == "Svalinn" and typ == "Fire":
                res_mod += 0.25
            res_mod += armor_resistance_modifier(self.equipment.get("Armor"), typ)
            res_mod += armor_resistance_modifier(self.equipment.get("Helmet"), typ)
            if self.cls.name == "Archbishop" and self.class_effects["Power Up"].active:
                res_mod += 0.25
            if (
                self.cls.name == "Astromancer"
                and self.class_effects["Power Up"].active
                and typ in ["Fire", "Water", "Wind", "Earth"]
            ):
                res_mod += 0.5
            harmony = archdruid.harmony_bonus(self)
            if harmony:
                res_mod += harmony
            if typ == "Fire":
                res_mod += ability_mechanics.primal_ascendance_multiplier(self, "Stone") - 1.0
            res_mod += class_rings.constellation_bonus(self, typ)
            try:
                data = self.class_ring_awakening["data"]["Shadowcaster"]
                if (
                    self.cls.name == "Shadowcaster"
                    and typ == "Holy"
                    and int(data.get("eclipse_turns", 0) or 0) > 0
                ):
                    penalty = (
                        0.20
                        if getattr(getattr(self, "familiar", None), "spec", "") == "Defense"
                        else 0.25
                    )
                    res_mod -= penalty
            except Exception:
                pass
            if typ == "Holy" and int(getattr(self, "warlock_eclipse_turns", 0) or 0) > 0:
                res_mod -= 0.25
            return res_mod
        if mod == "luck":
            if self.cls.name == "Rogue" and self.power_up:
                luck_factor = max(1, luck_factor // 2)
            lf = max(1, int(luck_factor))
            base = int(self.stats.charisma) + int(self.stats.wisdom)
            luck = max(0, (base * 2) // lf) + healer.luck_bonus(self, lf)
            return int(luck * promotion_kits.jinx_luck_multiplier(self))
        if mod == "speed":
            speed_mod = self.stats.dex
            if getattr(self, "warlock_eclipse_turns", 0) > 0:
                speed_mod *= 1.10
            speed_mod += self.stat_effects["Speed"].extra * self.stat_effects["Speed"].active
            if self.invisible and "Alacrity" in self.spellbook.get("Skills", {}):
                speed_mod *= 1.25
            speed_mod *= paladin.initiative_multiplier(self)
            speed_mod *= paladin.undead_hunter_speed_multiplier(self)
            speed_mod *= 1 + ability_mechanics.melody_inspiration_bonus(self)
            try:
                data = self.class_ring_awakening["data"]["Shadowcaster"]
                if self.cls.name == "Shadowcaster" and int(data.get("eclipse_turns", 0) or 0) > 0:
                    speed_mod *= 1.10
            except Exception:
                pass
            if getattr(self, "fractures", {}).get("Leg"):
                speed_mod *= 0.1
            return int(speed_mod)
        return 0

    def special_power(self, game=None):
        """Grant the current terminal class's Power Core quest ability."""
        ability_ctor = _SPECIAL_POWER_ABILITIES.get(self.cls.name)
        if ability_ctor is None:
            return "Complete a second promotion before claiming the Power Core reward.\n"
        if game is not None:
            game.special_event("Power Up")
        skill = ability_ctor()
        self.spellbook["Skills"][skill.name] = skill
        self.power_up = True
        return f"You gain the skill {skill.name}.\n"
