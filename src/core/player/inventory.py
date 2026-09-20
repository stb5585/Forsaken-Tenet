"""Player inventory, equipment, loot, saving, and Bestiary behavior."""

import os
import random
from itertools import chain

from .. import items
from ..classes import ability_mechanics, archdruid, bard, footpad, paladin
from ..constants import BASE_CRIT_PER_POINT
from ..items import remove_equipment
from ..save_system import SaveManager
from .config import BASIC_BESTIARY_ACTIONS, RESISTANCE_DISPLAY_ORDER


class PlayerInventoryMixin:
    def loot(self, enemy, tile):
        loot_message = ""
        items = list(chain.from_iterable(enemy.inventory.values()))
        resolved_items = []
        rare = [False] * len(items)
        drop = [False] * len(items)
        scavenged = [False] * len(items)
        if enemy.gold > 0:
            gold = int(enemy.gold)
            # Gnome Charity (virtue): charisma has a stronger effect on gold outcomes.
            if getattr(getattr(self, "race", None), "name", None) == "Gnome":
                from ..constants import GNOME_GOLD_CHARISMA_MULTIPLIER

                eff_cha = int(getattr(self.stats, "charisma", 0) * GNOME_GOLD_CHARISMA_MULTIPLIER)
                bonus_pct = min(0.25, max(0.0, eff_cha * 0.01))  # up to +25%
                gold = max(0, int(gold * (1.0 + bonus_pct)))
            gold = max(0, int(gold * paladin.redemption_reward_multiplier(self)))
            if getattr(enemy, "_pious_bounty_gold", False):
                gold *= 10
            loot_message += f"{enemy.name} dropped {gold} gold.\n"
            self.gold += gold
        for i, item_typ in enumerate(items):
            try:
                item = item_typ()
            except TypeError:
                item = item_typ
            resolved_items.append(item)

            # Check if item has class restrictions
            if hasattr(item, "restricted_classes"):
                if self.cls.name not in item.restricted_classes:
                    drop[i] = False
                    continue

            drop[i] = item.subtyp == "Special"
            rare[i] = item.subtyp == "Special"
            if item.subtyp == "Quest":
                quest_found = False
                # Check both Main and Side quests
                for quest_type in ["Main", "Side"]:
                    for info in self.quest_dict.get(quest_type, {}).values():
                        try:
                            quest_what = info["What"]
                            # Handle different types of 'What': class, instance, or string
                            quest_item_name = None
                            quest_item_class_name = None
                            if isinstance(quest_what, str):
                                # JSON quests may store class name (e.g. ElementalMote) or display name.
                                quest_item_name = quest_what
                                quest_item_class_name = quest_what
                            elif callable(quest_what):
                                # It's a class, instantiate for display name and use class name too.
                                quest_item_name = quest_what().name
                                quest_item_class_name = quest_what.__name__
                            else:
                                # It's already an instance.
                                quest_item_name = quest_what.name
                                quest_item_class_name = quest_what.__class__.__name__

                            is_completed = info.get("Completed", False)
                            item_class_name = item.__class__.__name__
                            matches_item = (
                                item.name == quest_item_name
                                or item_class_name == quest_item_class_name
                            )
                            if matches_item and not is_completed:
                                rarity = item.rarity
                                if item.name == "Bird Fat" and "Thaumaturgist" not in self.cls.name:
                                    rarity = 0.75
                                rarity_roll = random.random()
                                rare[i] = True
                                drop[i] = True if rarity > rarity_roll else False
                                quest_found = True
                                break
                        except (AttributeError, TypeError, KeyError):
                            pass
                    if quest_found:
                        break
                # No matching active quest -> do not drop quest item.
                if not quest_found:
                    drop[i] = False
                    rare[i] = False
            elif "Boss" in str(tile):
                if item.subtyp == "Special":
                    drop[i] = True if item.rarity > random.random() else False
                    rare[i] = True
                else:
                    drop[i] = True  # all non-quest, non-special items will drop from bosses
            elif item.subtyp == "Ability":
                drop[i] = True if item.rarity > random.random() else False
                rare[i] = True
            else:
                chance = self.check_mod("luck", enemy=enemy, luck_factor=16) + self.level.pro_level
                chance *= bard.loot_drop_multiplier(self)
                chance *= footpad.loot_drop_multiplier(self)
                base_threshold = min(1.0, max(0.0, item.rarity * chance))
                threshold = footpad.ordinary_loot_threshold(self, item, chance)
                roll = random.random()
                if roll < threshold:
                    scavenged[i] = roll >= base_threshold
                    try:
                        summon, name = item.subtyp.split(" - ")
                        summon_drop = item.name in self.special_inventory
                    except ValueError:
                        summon, _name = None, None
                        summon_drop = False
                    if summon and "Thaumaturgist" not in self.cls.name:
                        continue
                    drop[i] = True if not summon_drop else False
                    rare[i] = True if summon else False
            if drop[i]:
                loot_message += f"{enemy.name} dropped a {item.name}.\n"
                if scavenged[i]:
                    loot_message += f"Scavenger's Eye uncovers {item.name}.\n"
                self.modify_inventory(item, rare=rare[i])
                loot_message += self.quests(item=item)
                # Unlock Jump modification for special items
                if item.name and hasattr(self.spellbook.get("Skills", {}), "values"):
                    jump_skill = None
                    skills = self.spellbook.get("Skills", {})
                    if "Jump" in skills:
                        jump_skill = skills["Jump"]
                    else:
                        for sk in skills.values():
                            if getattr(sk, "name", "") == "Jump":
                                jump_skill = sk
                                break
                    if jump_skill is not None and hasattr(jump_skill, "unlock_item_modification"):
                        unlocked = jump_skill.unlock_item_modification(item.name)
                        if unlocked:
                            loot_message += f"New Jump modification unlocked: {unlocked}.\n"
        if "Boss" not in str(tile):
            extra_candidates = [
                item for index, item in enumerate(resolved_items) if not drop[index]
            ]
            extra = footpad.finders_keepers_candidate(
                self,
                extra_candidates,
                rng=random,
            )
            if extra is not None:
                self.modify_inventory(extra)
                loot_message += f"Finders Keepers turns up an extra {extra.name}.\n"

        # Unlock Jump modification for boss defeats
        if "Boss" in str(tile):
            skills = self.spellbook.get("Skills", {})
            jump_skill = skills.get("Jump")
            if jump_skill is None:
                for sk in skills.values():
                    if getattr(sk, "name", "") == "Jump":
                        jump_skill = sk
                        break
            if jump_skill is not None and hasattr(jump_skill, "unlock_boss_modification"):
                unlocked = jump_skill.unlock_boss_modification(enemy.name)
                if unlocked:
                    loot_message += f"New Jump modification unlocked: {unlocked}.\n"

        catalyst = archdruid.catalyst_for_enemy(self, enemy)
        if catalyst is not None:
            catalyst_name, catalyst_cls = catalyst
            item = catalyst_cls()
            self.modify_inventory(item, rare=True)
            archdruid.record_catalyst_obtained(self, catalyst_name)
            loot_message += f"{enemy.name} dropped a {catalyst_name}.\n"
        return loot_message

    def save(self, tmp=False, filepath=None):
        """Save player state directly or under the player's default filename.

        Args:
            tmp: If True, save to the temporary save directory.
            filepath: Optional path whose basename becomes the save filename.
        """
        if filepath:
            # Direct save to specified path
            SaveManager.save_player(self, os.path.basename(filepath), is_tmp=False)
            return

        if tmp:
            # Save to tmp_files with player name
            filename = f"{str(self.name).lower()}.save"
            SaveManager.save_player(self, filename, is_tmp=True)
            return

        filename = f"{str(self.name).lower()}.save"
        SaveManager.save_player(self, filename, is_tmp=False)

    def equip(self, equip_slot: str, item, check: bool = False) -> bool:
        """
        Handles equiping and character modification effects of equipment

        Args:
            equip_slot: Equipment slot where item is to be equipped. Must be one of the following: "Weapon",
                "OffHand", "Armor", "Helmet", "Ring", "Pendant"
            item: Equipment object to be equipped
            check: A flag signifying whether this is an equipment check or an actual equipment change.
                Default is False.

        Returns:
            True if equipment was successful, False if item is not allowed for this class.

        Example:
            >>> equip("Weapon", Dirk)
            >>> equip("Armor", LeatherArmor, check=True)

        """
        if getattr(self, "_transformed", False) and not check:
            return False
        equip_slots = {"Weapon", "OffHand", "Armor", "Helmet", "Ring", "Pendant"}
        if equip_slot not in equip_slots:
            raise ValueError(
                f"'equip_slot' must be one of {equip_slots}. Got {equip_slot} instead."
            )

        # Check if the class allows this item type (allow unequip items)
        allowed = self.cls.equip_check(item, equip_slot)
        allowed = allowed or ability_mechanics.can_dual_wield_item(
            self,
            item,
            equip_slot,
        )
        if item.subtyp != "None" and not allowed:
            return False

        if self.equipment[equip_slot].subtyp != "None" and not check:
            self.modify_inventory(self.equipment[equip_slot])
        if self.equipment[equip_slot].name == "Pendant of Vision" and (
            self.cls.name not in ["Inquisitor", "Seeker"]
        ):
            self.sight = False
        if self.equipment[equip_slot].name in ["Invisibility Amulet", "Tarnkappe", "Tarnhelm"]:
            self.invisible = False
        if self.equipment[equip_slot].name == "Levitation Necklace":
            self.flying = False

        # Handle two-handed weapon conflicts with offhand items
        if equip_slot == "Weapon":
            if item.handed == 2:
                can_keep_offhand = (
                    ability_mechanics.can_keep_polearm_shield(self, item, self.equipment["OffHand"])
                    or ability_mechanics.can_keep_staff_shield(
                        self, item, self.equipment["OffHand"]
                    )
                    or ability_mechanics.can_keep_berserker_heavy_offhand(
                        self, item, self.equipment["OffHand"]
                    )
                )

                if not can_keep_offhand:
                    if self.equipment["OffHand"].subtyp != "None" and not check:
                        self.modify_inventory(self.equipment["OffHand"])
                    if not check:
                        self.equipment["OffHand"] = remove_equipment("OffHand")

        if equip_slot == "OffHand":
            if self.equipment["Weapon"].handed == 2:
                can_keep_weapon = (
                    ability_mechanics.can_keep_polearm_shield(self, self.equipment["Weapon"], item)
                    or ability_mechanics.can_keep_staff_shield(self, self.equipment["Weapon"], item)
                    or ability_mechanics.can_keep_berserker_heavy_offhand(
                        self, self.equipment["Weapon"], item
                    )
                )

                if not can_keep_weapon:
                    if self.equipment["Weapon"].subtyp != "None" and not check:
                        self.modify_inventory(self.equipment["Weapon"])
                    if not check:
                        self.equipment["Weapon"] = remove_equipment("Weapon")
        self.equipment[equip_slot] = item
        if item.name == "Pendant of Vision":
            self.sight = True
        if item.name in ["Invisibility Amulet", "Tarnkappe", "Tarnhelm"]:
            self.invisible = True
        if item.name == "Levitation Necklace":
            self.flying = True
        if not check and item.subtyp != "None":
            self.modify_inventory(item, subtract=True)

        # If Ring slot changed, check if we need to enforce Jump modification limits
        if equip_slot == "Ring" and not check:
            # Check if character has Jump skill
            jump_skill = None
            if "Skills" in self.spellbook and "Jump" in self.spellbook["Skills"]:
                jump_skill = self.spellbook["Skills"]["Jump"]
            else:
                for skill in self.spellbook.get("Skills", {}).values():
                    if getattr(skill, "name", "") == "Jump":
                        jump_skill = skill
                        break

            if jump_skill and hasattr(jump_skill, "enforce_modification_limit"):
                jump_skill.enforce_modification_limit(self)
                # Could emit a message here if needed
                # if deactivated:
                #     print(f"Jump modifications deactivated due to equipment change: {', '.join(deactivated)}")

        return True

    def can_equip_item(self, item, equip_slot: str | None = None) -> bool:
        """Return whether this player can equip an item without mutating equipment."""
        if item is None:
            return False
        slots = items.equipment_slots_for_item(item) if equip_slot is None else [equip_slot]
        if not slots:
            return False
        equip_check = getattr(getattr(self, "cls", None), "equip_check", None)
        if not callable(equip_check):
            return False
        for slot in slots:
            if slot not in {"Weapon", "OffHand", "Armor", "Helmet", "Ring", "Pendant"}:
                continue
            if (
                getattr(item, "subtyp", None) == "None"
                or equip_check(item, slot)
                or ability_mechanics.can_dual_wield_item(self, item, slot)
            ):
                return True
        return False

    def equip_diff(self, item, equip_slot, buy=False):
        """
        function to analyze impact of item on player
        Temporarily equips the item, calculates stat differences, then safely restores original equipment
        """
        if equip_slot == "Accessory":
            equip_slot = item.subtyp

        # Save the current equipment reference BEFORE any modifications
        original_item = self.equipment[equip_slot]
        original_offhand = self.equipment["OffHand"] if equip_slot == "Weapon" else None
        original_sight = self.sight
        original_invisible = self.invisible
        original_flying = self.flying

        try:
            # Get current stats with original equipment
            main_dmg = self.check_mod("weapon")
            main_crit = int(
                (self.equipment["Weapon"].crit + (BASE_CRIT_PER_POINT * self.check_mod("speed")))
                * 100
            )

            def offhand_weapon_stats() -> tuple[bool, int, int]:
                offhand_item = self.equipment.get("OffHand")
                if (
                    getattr(offhand_item, "typ", None) != "Weapon"
                    and getattr(offhand_item, "subtyp", None) != "Crossbow"
                ):
                    return False, 0, 0
                damage = self.check_mod("offhand")
                crit_chance = int(
                    (
                        getattr(offhand_item, "crit", 0)
                        + (BASE_CRIT_PER_POINT * self.check_mod("speed"))
                    )
                    * 100
                )
                return True, damage, crit_chance

            had_offhand_weapon, off_dmg, off_crit = offhand_weapon_stats()
            armor = self.check_mod("armor")
            block = self.check_mod("shield")
            spell_def = self.check_mod("magic def")
            spell_mod = self.check_mod("magic")
            heal_mod = self.check_mod("heal")
            buffs = self.buff_str()
            resistance_before = self._equipment_resistance_preview()
            diff_dict = {}

            # return empty if item is not equipable by player
            allowed = self.cls.equip_check(item, equip_slot)
            allowed = allowed or ability_mechanics.can_dual_wield_item(
                self,
                item,
                equip_slot,
            )
            if not allowed and item.subtyp not in ["Ring", "Pendant", "None"]:
                return ""

            # Temporarily equip new item - directly modify equipment dict
            self.equipment[equip_slot] = item
            if equip_slot == "Pendant":
                if getattr(
                    original_item, "name", ""
                ) == "Pendant of Vision" and self.cls.name not in ["Inquisitor", "Seeker"]:
                    self.sight = False
                if getattr(original_item, "name", "") in [
                    "Invisibility Amulet",
                    "Tarnkappe",
                    "Tarnhelm",
                ]:
                    self.invisible = False
                if getattr(original_item, "name", "") == "Levitation Necklace":
                    self.flying = False
                if item.name == "Pendant of Vision":
                    self.sight = True
                if item.name in ["Invisibility Amulet", "Tarnkappe", "Tarnhelm"]:
                    self.invisible = True
                if item.name == "Levitation Necklace":
                    self.flying = True
            if equip_slot == "Weapon" and item.subtyp in self.cls.restrictions["OffHand"] and buy:
                self.equipment["OffHand"] = item

            # Handle two-handed weapon conflicts with offhand items (preview only)
            if equip_slot == "Weapon" and item.handed == 2:
                can_keep_offhand = (
                    ability_mechanics.can_keep_polearm_shield(self, item, self.equipment["OffHand"])
                    or ability_mechanics.can_keep_staff_shield(
                        self, item, self.equipment["OffHand"]
                    )
                    or ability_mechanics.can_keep_berserker_heavy_offhand(
                        self, item, self.equipment["OffHand"]
                    )
                )
                if not can_keep_offhand:
                    self.equipment["OffHand"] = remove_equipment("OffHand")

            # Get new stats with test equipment
            new_main_dmg = self.check_mod("weapon")
            if new_main_dmg != main_dmg:
                diff_dict["Main Attack"] = f"{main_dmg} -> {new_main_dmg}"
            new_main_crit = int(
                (self.equipment["Weapon"].crit + (BASE_CRIT_PER_POINT * self.check_mod("speed")))
                * 100
            )
            if new_main_crit != main_crit:
                diff_dict["Main Crit"] = f"{main_crit}% -> {new_main_crit}%"

            has_new_offhand_weapon, new_off_dmg, new_off_crit = offhand_weapon_stats()
            if had_offhand_weapon or has_new_offhand_weapon:
                if new_off_dmg != off_dmg:
                    diff_dict["OffHand Attack"] = f"{off_dmg} -> {new_off_dmg}"
                if new_off_crit != off_crit:
                    diff_dict["OffHand Crit"] = f"{off_crit}% -> {new_off_crit}%"
            if self.check_mod("shield") != block:
                diff_dict["Block Chance"] = f"{block}% -> {self.check_mod('shield')}%"
            if self.check_mod("armor") != armor:
                diff_dict["Armor"] = f"{armor} -> {self.check_mod('armor')}"
            if self.check_mod("magic def") != spell_def:
                diff_dict["Spell Defense"] = f"{spell_def} -> {self.check_mod('magic def')}"
            if self.check_mod("magic") != spell_mod:
                diff_dict["Spell Modifier"] = f"{spell_mod} -> {self.check_mod('magic')}"
            if self.check_mod("heal") != heal_mod:
                diff_dict["Heal Modifier"] = f"{heal_mod} -> {self.check_mod('heal')}"
            resistance_after = self._equipment_resistance_preview()
            for resistance_name in RESISTANCE_DISPLAY_ORDER:
                before = resistance_before.get(resistance_name, 0.0)
                after = resistance_after.get(resistance_name, 0.0)
                if before != after:
                    diff_dict[f"{resistance_name} Resist"] = (
                        f"{self._format_resistance_preview(before)} -> {self._format_resistance_preview(after)}"
                    )
            new_buffs = self.buff_str()
            if new_buffs != buffs:
                diff_dict["Buffs"] = f"{buffs} -> {new_buffs}"

            return "\n".join([f"{x:16}{' ':2}{y:>6}" for x, y in diff_dict.items()])
        finally:
            # ALWAYS restore original equipment, even if an exception occurs
            self.equipment[equip_slot] = original_item
            if equip_slot == "Weapon":
                self.equipment["OffHand"] = original_offhand
            self.sight = original_sight
            self.invisible = original_invisible
            self.flying = original_flying

    def _equipment_resistance_preview(self) -> dict[str, float]:
        """Return current resistance values including equipment preview state."""
        values = {}
        player_resistance = getattr(self, "resistance", {}) or {}
        race_resistance = getattr(getattr(self, "race", None), "resistance", {}) or {}
        for resistance_name in RESISTANCE_DISPLAY_ORDER:
            try:
                values[resistance_name] = float(
                    self.check_mod("resist", typ=resistance_name) or 0.0
                )
            except (TypeError, ValueError):
                values[resistance_name] = 0.0
            try:
                player_base = float(player_resistance.get(resistance_name, 0.0) or 0.0)
                race_base = float(race_resistance.get(resistance_name, 0.0) or 0.0)
            except (AttributeError, TypeError, ValueError):
                continue
            if player_base == 0.0 and race_base != 0.0:
                values[resistance_name] += race_base
        return values

    @staticmethod
    def _format_resistance_preview(value: float) -> str:
        return f"{int(round(float(value) * 100)):+d}%"

    def record_bestiary_encounter(self, enemy, enemy_type: str | None = None) -> None:
        """Record that an enemy was encountered without revealing combat details."""
        if enemy is None:
            return
        if not isinstance(getattr(self, "bestiary", None), dict):
            self.bestiary = {}

        enemy_name = str(getattr(enemy, "name", "") or "").strip()
        if not enemy_name:
            return

        record = self.bestiary.setdefault(enemy_name, {})
        record["name"] = enemy_name
        record["type"] = str(
            enemy_type or getattr(enemy, "enemy_typ", "") or record.get("type") or "Unknown"
        )
        try:
            seen_count = int(record.get("seen_count", 0) or 0)
        except (TypeError, ValueError):
            seen_count = 0
        record["seen_count"] = max(0, seen_count) + 1
        record.setdefault("details_unlocked", False)

    def record_bestiary_enemy(self, enemy, enemy_type: str | None = None) -> None:
        """Store stable enemy details observed while the player has combat insight."""
        if enemy is None:
            return
        if not isinstance(getattr(self, "bestiary", None), dict):
            self.bestiary = {}

        enemy_name = str(getattr(enemy, "name", "") or "").strip()
        if not enemy_name:
            return

        record = self.bestiary.setdefault(enemy_name, {})
        record["name"] = enemy_name
        record["type"] = str(enemy_type or getattr(enemy, "enemy_typ", "") or "Unknown")
        record["details_unlocked"] = True
        try:
            record["seen_count"] = max(0, int(record.get("seen_count", 0) or 0))
        except (TypeError, ValueError):
            record["seen_count"] = 0

        level = getattr(enemy, "level", None)
        base_level = getattr(level, "level", None)
        pro_level = getattr(level, "pro_level", None)
        difficulty_level = pro_level if pro_level not in (None, "", 0) else base_level
        if difficulty_level not in (None, ""):
            record["difficulty_level"] = difficulty_level
        if base_level not in (None, ""):
            record["level"] = base_level
        if pro_level not in (None, ""):
            record["pro_level"] = pro_level

        resistance = getattr(enemy, "resistance", {}) or {}
        notable_resistances = {}
        for resistance_name in RESISTANCE_DISPLAY_ORDER:
            try:
                value = float(resistance.get(resistance_name, 0.0) or 0.0)
            except (AttributeError, TypeError, ValueError):
                value = 0.0
            if value:
                notable_resistances[resistance_name] = value
        record["resistances"] = notable_resistances

        features = []
        for attr_name, label in (
            ("flying", "Flying"),
            ("sight", "Sight"),
            ("invisible", "Invisible"),
            ("tunnel", "Tunnel"),
            ("boss", "Boss"),
        ):
            if getattr(enemy, attr_name, False):
                features.append(label)
        for effect_dict_name in ("status_effects", "physical_effects", "magic_effects"):
            effect_dict = getattr(enemy, effect_dict_name, {}) or {}
            for effect_name, effect in effect_dict.items():
                if getattr(effect, "active", False):
                    features.append(str(effect_name))
        immunities = sorted(
            set(str(value) for value in (getattr(enemy, "status_immunity", []) or []) if value)
        )
        observed_features = set(record.get("features", []) or [])
        observed_immunities = set(record.get("immunities", []) or [])
        for feature in list(observed_features):
            if str(feature).startswith("Immune:"):
                observed_features.discard(feature)
                observed_immunities.update(
                    part.strip()
                    for part in str(feature).removeprefix("Immune:").split(",")
                    if part.strip()
                )
        record["features"] = sorted(observed_features | set(features))
        record["immunities"] = sorted(observed_immunities | set(immunities))
        record.setdefault("known_abilities", [])

    def record_bestiary_ability(self, enemy, ability_name: str | None) -> None:
        """Record an enemy ability after it is seen during a revealed combat."""
        if enemy is None:
            return
        ability = str(ability_name or "").strip()
        if ability in BASIC_BESTIARY_ACTIONS:
            return
        self.record_bestiary_enemy(enemy)
        enemy_name = str(getattr(enemy, "name", "") or "").strip()
        if not enemy_name:
            return
        record = self.bestiary.setdefault(enemy_name, {})
        abilities_seen = set(record.get("known_abilities", []) or [])
        abilities_seen.add(ability)
        record["known_abilities"] = sorted(abilities_seen)

    def unequip(self, typ=None, promo=False):
        if typ:
            return remove_equipment(typ)  # imported from items
        if promo:
            for item in ["Weapon", "Armor", "Helmet", "OffHand"]:
                if self.equipment[item].subtyp != "None":
                    self.modify_inventory(self.equipment[item], 1)
        else:
            raise NotImplementedError
