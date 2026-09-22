"""Data behavior for the modern character screen package."""

from __future__ import annotations

from typing import Any

import pygame

from src.core import items
from src.core.classes import ability_mechanics, grandmaster

from ..status_icons import active_resist_effect_names
from .models import (
    EQUIPMENT_SLOT_ORDER,
    RESISTANCE_ORDER,
    TWO_HANDED_WEAPON_SUBTYPES,
    WEAPON_DISCIPLINE_ICON_FACTORIES,
    EquipmentBuffSummary,
    EquipmentSlotSummary,
    ResistanceSummary,
    _whole_stat_text,
)


class CharacterDataMixin:
    def portrait_frame_rect(
        self,
        y: int,
        surface: pygame.Surface | None = None,
        *,
        reserved_bottom: int = 32,
    ) -> pygame.Rect:
        source_width, source_height = (225, 400)
        if surface is not None:
            surface_width, surface_height = surface.get_size()
            if surface_width > 0 and surface_height > 0:
                source_width, source_height = surface_width, surface_height

        metrics = self.presenter.layout_metrics
        max_width = min(
            source_width,
            max(metrics.unit(150), self.character_panel_rect.width // 2 - metrics.unit(12)),
        )
        max_height = min(
            source_height,
            max(
                metrics.unit(120),
                self.character_panel_rect.height
                - (y - self.character_panel_rect.top)
                - reserved_bottom,
            ),
        )
        scale = min(max_width / source_width, max_height / source_height, 1.0)
        portrait_width = max(1, int(source_width * scale))
        portrait_height = max(1, int(source_height * scale))
        return pygame.Rect(
            self.character_panel_rect.left + metrics.unit(16),
            y,
            portrait_width,
            portrait_height,
        )

    @staticmethod
    def _call_or_attr(player_char, name: str, default: int = 0) -> int:
        value = getattr(player_char, name, default)
        if callable(value):
            try:
                value = value()
            except (TypeError, ValueError):
                value = default
        try:
            return int(value)
        except (TypeError, ValueError):
            return int(default)

    def _get_jump_skill(self, player_char):
        skills = getattr(player_char, "spellbook", {}).get("Skills", {})
        if "Jump" in skills:
            return skills["Jump"]
        for skill in skills.values():
            if getattr(skill, "name", "") == "Jump":
                return skill
        return None

    def _has_jump_mods(self, player_char) -> bool:
        jump_skill = self._get_jump_skill(player_char)
        return bool(jump_skill and hasattr(jump_skill, "modifications"))

    def _get_totem_skill(self, player_char):
        skills = getattr(player_char, "spellbook", {}).get("Skills", {})
        if "Totem" in skills:
            return skills["Totem"]
        for skill in skills.values():
            if getattr(skill, "name", "") == "Totem":
                return skill
        return None

    def _has_totem_aspects(self, player_char) -> bool:
        totem_skill = self._get_totem_skill(player_char)
        return bool(totem_skill and hasattr(totem_skill, "get_unlocked_aspects"))

    @staticmethod
    def _is_living_companion(entity: Any) -> bool:
        is_alive = getattr(entity, "is_alive", None)
        return bool(is_alive()) if callable(is_alive) else True

    def active_companion_for_display(self, player_char) -> tuple[str, Any] | None:
        """Return the companion that should be visually highlighted."""
        familiar = getattr(player_char, "familiar", None)
        if familiar is not None and self._is_living_companion(familiar):
            kind = "Companion" if getattr(familiar, "spec", "") == "Tamed" else "Familiar"
            return kind, familiar

        summons = getattr(player_char, "summons", {}) or {}
        for summon in summons.values():
            if self._is_living_companion(summon):
                return "Xenid", summon
        return None

    def companion_summary_rows(self, kind: str, companion: Any) -> list[tuple[str, str]]:
        """Return compact Character Menu rows for the selected companion."""
        name = str(getattr(companion, "name", "") or kind)
        identity = (
            getattr(companion, "species", None)
            or getattr(companion, "race", None)
            or getattr(companion, "spec", None)
            or getattr(companion, "cls", None)
            or kind
        )
        if not isinstance(identity, str):
            identity = self._attr_name(identity, kind)
        if identity == name:
            identity = kind
        rows = [("Companion", name), ("Type", str(identity))]
        if getattr(companion, "spec", "") == "Tamed":
            evolution = str(getattr(companion, "evolution", "") or "")
            special = str(getattr(companion, "special_ability", "") or "")
            if evolution:
                rows.append(("Form", evolution))
            if special:
                rows.append(("Special", special))
        if getattr(companion, "spec", "") != "Tamed":
            level = getattr(companion, "level", None)
            for attr in ("level", "pro_level"):
                value = getattr(level, attr, None)
                if value is not None:
                    rows.append(("Level", str(value)))
                    break
        return rows

    def companion_detail_rows(self, kind: str, companion: Any) -> list[tuple[str, str]]:
        """Return stat rows for a familiar, companion, or summon."""
        rows = self.companion_summary_rows(kind, companion)
        if kind == "Familiar":
            abilities = [
                *getattr(companion, "spellbook", {}).get("Skills", {}),
                *getattr(companion, "spellbook", {}).get("Spells", {}),
            ]
            rows.append(("Specialization", str(getattr(companion, "spec", "General"))))
            rows.append(("Abilities", ", ".join(abilities) or "None"))
            return rows
        health = getattr(companion, "health", None)
        mana = getattr(companion, "mana", None)
        combat = getattr(companion, "combat", None)
        if getattr(companion, "spec", "") != "Tamed":
            rows.extend(
                [
                    ("HP", f"{getattr(health, 'current', 0)}/{getattr(health, 'max', 0)}"),
                    ("MP", f"{getattr(mana, 'current', 0)}/{getattr(mana, 'max', 0)}"),
                    ("Attack", _whole_stat_text(getattr(combat, "attack", 0))),
                    ("Defense", _whole_stat_text(getattr(combat, "defense", 0))),
                    ("Magic", _whole_stat_text(getattr(combat, "magic", 0))),
                    ("Magic Defense", _whole_stat_text(getattr(combat, "magic_def", 0))),
                ]
            )
        return rows

    def class_summary_rows(self, player_char) -> list[tuple[str, str]]:
        """Return class-specific summary rows for the Class tab."""
        if grandmaster.is_weapon_discipline_class(player_char):
            return []
        summons = getattr(player_char, "summons", {}) or {}
        familiar = getattr(player_char, "familiar", None)
        class_name = self._attr_name(getattr(player_char, "cls", None), "")
        rows = []
        if class_name in {"Ranger", "Beast Master"}:
            try:
                favored = ability_mechanics.favored_enemy_label(player_char)
            except Exception:
                favored = "None"
            rows.append(("Favored Enemy", favored))
        if summons:
            rows.append(("Known Xenids", str(len(summons))))
        if familiar is not None:
            if getattr(familiar, "spec", "") == "Tamed":
                rows.append(("Companion", self._attr_name(familiar, "Companion")))
                tamed = getattr(player_char, "tamed_companion", {}) or {}
                bond = getattr(familiar, "bond", 0)
                evolution = str(getattr(familiar, "evolution", "") or "")
                special = str(getattr(familiar, "special_ability", "") or "")
                if isinstance(tamed, dict):
                    bond = tamed.get("bond", bond)
                    evolution = str(tamed.get("evolution") or evolution)
                    special = str(tamed.get("special_ability") or special)
                rows.append(("Bond", f"{self._non_negative_int(bond)}/100"))
                if evolution:
                    rows.append(("Form", evolution))
                if special:
                    rows.append(("Special", special))
                roster = tamed.get("companions", []) if isinstance(tamed, dict) else []
                if (
                    class_name not in {"Ranger", "Beast Master"}
                    and isinstance(roster, list)
                    and roster
                ):
                    rows.append(
                        ("Held", f"{len(roster)}/{ability_mechanics.TAMED_COMPANION_ROSTER_LIMIT}")
                    )
            else:
                rows.append(("Familiar", self._attr_name(familiar, "Familiar")))
        return rows

    def favored_enemy_progress_rows(self, player_char) -> list[tuple[str, int, int, str]]:
        """Return the marked enemy-type practice row for Ranger/Beast Master."""
        try:
            state = ability_mechanics.favored_enemy_state(player_char)
        except Exception:
            state = {"type": None, "practice": 0, "switches": 0}
        marked = state.get("type")
        practice = self._non_negative_int(state.get("practice", 0))
        if not marked:
            return [("No marked quarry", 0, 100, "Use Favored Enemy in combat")]
        return [
            (
                str(marked),
                min(100, practice),
                100,
                f"{ability_mechanics.favored_enemy_rank(practice)} - {practice} practice",
            )
        ]

    def _draw_favored_enemy_progress_panel(self, player_char, rect: pygame.Rect, y: int) -> int:
        """Draw Ranger/Beast Master enemy-type tracking mastery progress."""
        self._draw_text(
            "Tracking Mastery", self.normal_font, self.colors.GOLD, rect.left, y, rect.width
        )
        y += self.normal_font.get_height() + 10
        for label, value, cap, detail in self.favored_enemy_progress_rows(player_char):
            if y + 54 > rect.bottom:
                break
            y = self._draw_progress_row(
                rect, label, value, cap, y, detail=detail, color=self.colors.GREEN
            )
        try:
            switches = ability_mechanics.favored_enemy_state(player_char).get("switches", 0)
        except Exception:
            switches = 0
        if y + self.small_font.get_height() <= rect.bottom:
            self._draw_text(
                f"Quarry changes: {self._non_negative_int(switches)}",
                self.small_font,
                self.colors.GRAY,
                rect.left,
                y,
                rect.width,
            )
            y += self.small_font.get_height() + 10
        return y

    def _weapon_discipline_progress_label(self, xp: float, rank: int) -> str:
        if rank >= grandmaster.MAX_RANK:
            return "MAX"
        next_threshold = grandmaster.XP_THRESHOLDS[rank]
        return f"{grandmaster.format_xp_value(xp)}/{next_threshold} XP"

    def _weapon_discipline_progress_fraction(self, xp: int, rank: int) -> float:
        if rank >= grandmaster.MAX_RANK:
            return 1.0
        previous_threshold = grandmaster.XP_THRESHOLDS[rank - 1] if rank > 0 else 0
        next_threshold = grandmaster.XP_THRESHOLDS[rank]
        span = max(1, next_threshold - previous_threshold)
        return max(0.0, min(1.0, (xp - previous_threshold) / span))

    def weapon_discipline_rows(self, player_char) -> list[tuple[str, str]]:
        """Return per-weapon Weapon Discipline progression rows."""
        state = grandmaster.normalize_state(getattr(player_char, "grandmaster_discipline", None))
        rows: list[tuple[str, str]] = []
        for weapon_type in grandmaster.weapon_discipline_types(player_char):
            entry = state["disciplines"][weapon_type]
            xp = self._non_negative_float(entry.get("xp", 0))
            rank = self._non_negative_int(entry.get("rank", 0))
            progress = self._weapon_discipline_progress_label(xp, rank)
            rows.append((weapon_type, f"Rank {rank} - {progress}"))
        return rows

    def weapon_discipline_detail_text(self, player_char, weapon_type: str) -> str:
        """Return readable progression details for one Weapon Discipline row."""
        state = grandmaster.normalize_state(getattr(player_char, "grandmaster_discipline", None))
        entry = state["disciplines"].get(weapon_type, {"xp": 0, "rank": 0})
        xp = self._non_negative_float(entry.get("xp", 0))
        rank = self._non_negative_int(entry.get("rank", 0))
        progress = self._weapon_discipline_progress_label(xp, rank)
        art_name = grandmaster.WEAPON_ARTS.get(weapon_type, "Weapon Art")
        equipped = weapon_type in {
            grandmaster.get_weapon_type(player_char, "Weapon"),
            grandmaster.get_weapon_type(player_char, "OffHand"),
        }
        unlocked = rank >= 1
        improved = rank >= 5
        mastered = rank >= grandmaster.MAX_RANK
        lines = [
            f"{weapon_type} Discipline",
            f"Rank {rank} - {progress}",
            f"Equipped now: {'Yes' if equipped else 'No'}",
            "",
            f"Weapon Art: {art_name}",
            f"Required weapon: {weapon_type}",
            "",
            "Unlocks:",
            f"Rank 1: {'Unlocked' if unlocked else 'Locked'} - learn {art_name}.",
            f"Rank 5: {'Unlocked' if improved else 'Locked'} - learn {art_name} 2.",
            (
                f"Rank {grandmaster.MAX_RANK}: "
                f"{'Unlocked' if mastered else 'Locked'} - learn {art_name} 3."
            ),
        ]
        if rank < grandmaster.MAX_RANK:
            next_threshold = grandmaster.XP_THRESHOLDS[rank]
            remaining = max(0, next_threshold - int(xp))
            lines.append(f"Next rank: {remaining} XP remaining.")
        return "\n".join(lines)

    def _weapon_discipline_icon_item(self, weapon_type: str):
        if not hasattr(self, "_weapon_discipline_icon_cache"):
            self._weapon_discipline_icon_cache = {}
        cache = self._weapon_discipline_icon_cache
        if weapon_type not in cache:
            factory = WEAPON_DISCIPLINE_ICON_FACTORIES.get(weapon_type, items.NoWeapon)
            try:
                cache[weapon_type] = factory()
            except Exception:
                cache[weapon_type] = items.NoWeapon()
        return cache[weapon_type]

    def _get_key_items_list(self, player_char):
        special_inv = getattr(player_char, "special_inventory", {})
        if not special_inv:
            return ["No key items"]

        key_items = []
        for item_name, item_list in special_inv.items():
            if not item_list:
                continue
            item_obj = item_list[0]
            quantity = len(item_list)
            if quantity > 1:
                key_items.append(
                    {
                        "text": f"{item_name} ({quantity})",
                        "value": item_obj,
                        "is_header": False,
                    }
                )
            else:
                key_items.append(item_obj)
        return key_items if key_items else ["No key items"]

    def _get_specials_list(self, player_char):
        result = []

        race = getattr(player_char, "race", None)
        virtue = getattr(race, "virtue", None) if race else None
        sin = getattr(race, "sin", None) if race else None
        if virtue and getattr(virtue, "name", ""):
            result.append("--- RACIAL TRAITS ---")
            result.append(virtue)
            if sin and getattr(sin, "name", ""):
                result.append(sin)

        spellbook = getattr(player_char, "spellbook", None)
        if spellbook and isinstance(spellbook, dict):
            from src.core.abilities.descriptions import presented_abilities

            spells = presented_abilities(player_char, "Spells")
            skills = presented_abilities(player_char, "Skills")
            if spells:
                result.append("--- SPELLS ---")
                result.extend(spells)
            if skills:
                result.append("--- SKILLS ---")
                result.extend(skills)

        return result if result else ["No special abilities"]

    @staticmethod
    def _check_mod(player_char, mod: str, default: int = 0) -> int:
        try:
            return int(player_char.check_mod(mod))
        except (AttributeError, KeyError, TypeError, ValueError):
            combat = getattr(player_char, "combat", None)
            fallback = {
                "weapon": getattr(combat, "attack", default),
                "armor": getattr(combat, "defense", default),
                "magic": getattr(combat, "magic", default),
                "magic def": getattr(combat, "magic_def", default),
                "shield": default,
                "speed": getattr(getattr(player_char, "stats", None), "dex", default),
            }
            return int(fallback.get(mod, default) or default)

    @staticmethod
    def _non_negative_int(value: Any, default: int = 0) -> int:
        try:
            return max(0, int(value or default))
        except (TypeError, ValueError):
            return max(0, int(default))

    @staticmethod
    def _non_negative_float(value: Any, default: float = 0.0) -> float:
        try:
            return max(0.0, float(value or default))
        except (TypeError, ValueError):
            return max(0.0, float(default))

    @staticmethod
    def xp_progress(player_char) -> float:
        level = getattr(player_char, "level", None)
        raw_to_next = getattr(level, "exp_to_gain", 0)
        if isinstance(raw_to_next, str) and raw_to_next.upper() == "MAX":
            return 1.0
        to_next = CharacterDataMixin._non_negative_int(raw_to_next)
        total = CharacterDataMixin.xp_required_for_current_level(player_char)
        if total <= 0:
            return 0.0
        current = max(0, total - to_next)
        return max(0.0, min(1.0, current / total))

    @staticmethod
    def xp_label(player_char) -> str:
        level = getattr(player_char, "level", None)
        raw_to_next = getattr(level, "exp_to_gain", 0)
        if isinstance(raw_to_next, str) and raw_to_next.upper() == "MAX":
            exp = CharacterDataMixin._non_negative_int(getattr(level, "exp", 0))
            return f"{exp} XP / MAX level"
        to_next = CharacterDataMixin._non_negative_int(raw_to_next)
        total = CharacterDataMixin.xp_required_for_current_level(player_char)
        current = max(0, total - to_next)
        return f"{current}/{total} XP ({to_next} next)"

    @staticmethod
    def xp_required_for_current_level(player_char) -> int:
        try:
            return CharacterDataMixin._non_negative_int(player_char.level_exp())
        except (AttributeError, TypeError, ValueError):
            level = getattr(player_char, "level", None)
            exp = CharacterDataMixin._non_negative_int(getattr(level, "exp", 0))
            to_next = CharacterDataMixin._non_negative_int(getattr(level, "exp_to_gain", 0))
            return exp + to_next

    def build_character_summary(self, player_char) -> list[tuple[str, str]]:
        race = self._attr_name(getattr(player_char, "race", None), "")
        cls = self._attr_name(getattr(player_char, "cls", None), "")
        level = getattr(getattr(player_char, "level", None), "level", 1)
        rows = [
            ("Name", str(getattr(player_char, "name", "Adventurer"))),
            ("Race", race or "Unknown"),
            ("Class", cls or "Unknown"),
            ("Level", str(level)),
        ]
        active_resists = active_resist_effect_names(player_char)
        if active_resists:
            rows.append(("Active Buffs", ", ".join(active_resists)))
        return rows

    def location_label(self, player_char) -> str:
        location_z = getattr(player_char, "location_z", 0)
        try:
            location_z = int(location_z)
        except (TypeError, ValueError):
            location_z = 0
        if location_z == 0:
            return "Town"
        return f"Dungeon Level {location_z}"

    def build_portrait_details(self, player_char) -> list[tuple[str, str]]:
        gold = self._non_negative_int(getattr(player_char, "gold", 0))
        rows = [
            ("Gold", f"{gold}G"),
            ("Location", self.location_label(player_char)),
        ]
        if getattr(player_char, "_transformed", False):
            rows.append(("Form", self._attr_name(getattr(player_char, "cls", None), "Transformed")))
        return rows

    def _draw_portrait_details(self, rows: list[tuple[str, str]], rect: pygame.Rect, y: int) -> int:
        font = self.small_font
        metrics = self.presenter.layout_metrics
        line_gap = metrics.unit(4)
        for label, value in rows:
            if y + font.get_height() > rect.bottom:
                break
            label_width = min(
                max(metrics.unit(62), font.size(label)[0] + metrics.unit(8)),
                max(metrics.unit(62), rect.width // 2),
            )
            value_width = max(1, rect.width - label_width - metrics.unit(12))
            self._draw_text(
                label,
                font,
                self.colors.GRAY,
                rect.left + metrics.unit(4),
                y,
                label_width,
            )
            if font.size(str(value))[0] <= value_width:
                value_text = str(value)
                value_x = rect.right - metrics.unit(4) - font.size(value_text)[0]
                self._draw_text(value_text, font, self.colors.WHITE, value_x, y, value_width)
                y += font.get_height() + line_gap
            else:
                y += font.get_height()
                full_width = max(1, rect.width - metrics.unit(8))
                value_text = str(value)
                self._draw_text(
                    value_text,
                    font,
                    self.colors.WHITE,
                    rect.left + metrics.unit(4),
                    y,
                    full_width,
                )
                y += font.get_height() + line_gap
            if y > rect.bottom:
                break
        return y

    def _portrait_details_min_height(self, rows: list[tuple[str, str]], width: int) -> int:
        """Return the height needed for compact portrait metadata rows."""
        font = self.small_font
        metrics = self.presenter.layout_metrics
        line_gap = metrics.unit(4)
        height = 0
        for label, value in rows:
            label_width = min(
                max(metrics.unit(62), font.size(label)[0] + metrics.unit(8)),
                max(metrics.unit(62), width // 2),
            )
            value_width = max(1, width - label_width - metrics.unit(12))
            row_lines = 1 if font.size(str(value))[0] <= value_width else 2
            height += (font.get_height() * row_lines) + line_gap
        return height

    def build_core_attributes(self, player_char) -> list[tuple[str, str]]:
        stats = getattr(player_char, "stats", None)
        return [
            ("Strength", str(getattr(stats, "strength", 0))),
            ("Intelligence", str(getattr(stats, "intel", 0))),
            ("Wisdom", str(getattr(stats, "wisdom", 0))),
            ("Constitution", str(getattr(stats, "con", 0))),
            ("Charisma", str(getattr(stats, "charisma", 0))),
            ("Dexterity", str(getattr(stats, "dex", 0))),
        ]

    def attack_display(self, player_char) -> str:
        main_attack = self._check_mod(player_char, "weapon")
        equipment = getattr(player_char, "equipment", {}) or {}
        offhand = equipment.get("OffHand") if isinstance(equipment, dict) else None
        if getattr(offhand, "typ", None) == "Weapon":
            return f"{main_attack}/{self._check_mod(player_char, 'offhand')}"
        return str(main_attack)

    def build_combat_stats(self, player_char) -> list[tuple[str, str]]:
        health = getattr(player_char, "health", None)
        mana = getattr(player_char, "mana", None)
        try:
            crit = float(player_char.critical_chance("Weapon")) * 100
        except (AttributeError, TypeError, ValueError):
            crit = 0.0
        weight = self._call_or_attr(player_char, "current_weight")
        max_weight = self._call_or_attr(player_char, "max_weight")
        return [
            ("HP", f"{getattr(health, 'current', 0)}/{getattr(health, 'max', 0)}"),
            ("MP", f"{getattr(mana, 'current', 0)}/{getattr(mana, 'max', 0)}"),
            ("Attack", self.attack_display(player_char)),
            ("Defense", str(self._check_mod(player_char, "armor"))),
            ("Magic Attack", str(self._check_mod(player_char, "magic"))),
            ("Magic Defense", str(self._check_mod(player_char, "magic def"))),
            ("Critical", f"{crit:.1f}%"),
            ("Block", f"{self._check_mod(player_char, 'shield')}%"),
            ("Speed", str(self._check_mod(player_char, "speed"))),
            ("Weight", f"{weight}/{max_weight}"),
        ]

    def build_equipment_slots(self, player_char) -> list[EquipmentSlotSummary]:
        equipment = getattr(player_char, "equipment", {}) or {}
        slots: list[EquipmentSlotSummary] = []
        weapon = equipment.get("Weapon") if isinstance(equipment, dict) else None
        for slot in EQUIPMENT_SLOT_ORDER:
            item = equipment.get(slot) if isinstance(equipment, dict) else None
            if slot == "OffHand" and self.should_show_two_handed_occupancy(
                player_char, weapon, item
            ):
                item = weapon
                description = "Off-hand occupied by two-handed weapon."
                detail_rows = self.equipment_slot_detail_rows("Weapon", item)
                details = tuple(f"{label}: {value}" for label, value in detail_rows)
                slots.append(
                    EquipmentSlotSummary(
                        slot,
                        self._equipment_display_name(item),
                        description,
                        ", ".join(details),
                        details,
                        detail_rows,
                        (),
                        item,
                    )
                )
                continue
            if self.is_empty_equipment(item):
                slots.append(EquipmentSlotSummary(slot, "(empty)", "No item equipped.", ""))
                continue
            description = str(getattr(item, "description", "") or getattr(item, "desc", "") or "")
            detail_rows = self.equipment_slot_detail_rows(slot, item)
            details = tuple(f"{label}: {value}" for label, value in detail_rows)
            buffs = self.equipment_slot_buffs(item)
            slots.append(
                EquipmentSlotSummary(
                    slot,
                    self._equipment_display_name(item),
                    description,
                    ", ".join(details),
                    details,
                    detail_rows,
                    buffs,
                    item,
                )
            )
        return slots

    def selectable_equipment_slots(self, player_char) -> list[str]:
        return [slot.slot for slot in self.build_equipment_slots(player_char) if slot.implemented]

    def selected_equipment_slot(self, player_char) -> str:
        slots = self.selectable_equipment_slots(player_char)
        if not slots:
            return "Weapon"
        self.selected_equipment_slot_index = max(
            0, min(self.selected_equipment_slot_index, len(slots) - 1)
        )
        return slots[self.selected_equipment_slot_index]

    def set_selected_equipment_slot(self, player_char, slot_name: str) -> None:
        slots = self.selectable_equipment_slots(player_char)
        if slot_name in slots:
            self.selected_equipment_slot_index = slots.index(slot_name)

    def move_equipment_selector(self, player_char, direction: str) -> None:
        current = self.selected_equipment_slot(player_char)
        nav = {
            "Helmet": {"down": "Armor", "left": "Weapon", "right": "OffHand"},
            "Weapon": {"up": "Helmet", "right": "Armor", "down": "Ring"},
            "Armor": {"up": "Helmet", "left": "Weapon", "right": "OffHand", "down": "Ring"},
            "OffHand": {"up": "Helmet", "left": "Armor", "down": "Pendant"},
            "Ring": {"up": "Weapon", "right": "Pendant"},
            "Pendant": {"up": "OffHand", "left": "Ring"},
        }
        target = nav.get(current, {}).get(direction, current)
        self.set_selected_equipment_slot(player_char, target)

    @staticmethod
    def is_empty_equipment(item: Any) -> bool:
        if item is None:
            return True
        return str(getattr(item, "subtyp", "") or "") == "None"

    def should_show_two_handed_occupancy(self, player_char, weapon: Any, offhand: Any) -> bool:
        if self.is_empty_equipment(weapon) or not self.is_empty_equipment(offhand):
            return False
        try:
            handed = int(getattr(weapon, "handed", 1) or 1)
        except (TypeError, ValueError):
            handed = 1
        if handed != 2:
            return False
        if self.can_use_two_hander_without_blocking_offhand(player_char, weapon):
            return False
        return True

    def can_use_two_hander_without_blocking_offhand(self, player_char, weapon: Any) -> bool:
        cls = getattr(player_char, "cls", None)
        cls_name = self._attr_name(cls, "")
        if (
            cls_name in {"Lancer", "Dragoon"}
            and str(getattr(weapon, "subtyp", "") or "") == "Polearm"
        ):
            return True
        if str(getattr(weapon, "subtyp", "") or "") == "Staff" and ability_mechanics.has_skill(
            player_char, "Staff Conduit"
        ):
            return True
        equipment = getattr(player_char, "equipment", {}) or {}
        offhand = equipment.get("OffHand")
        if ability_mechanics.can_keep_staff_shield(player_char, weapon, offhand):
            return True
        try:
            return bool(cls.equip_check(weapon, "OffHand"))
        except (AttributeError, KeyError, TypeError, ValueError):
            return False

    @staticmethod
    def _display_number(value: Any) -> str:
        try:
            numeric = float(value)
        except (TypeError, ValueError):
            return str(value)
        if numeric.is_integer():
            return str(int(numeric))
        return f"{numeric:.2f}".rstrip("0").rstrip(".")

    @staticmethod
    def _display_percent(value: Any) -> str:
        try:
            numeric = float(value)
        except (TypeError, ValueError):
            return str(value)
        return f"{numeric * 100:.1f}%".replace(".0%", "%")

    @staticmethod
    def _weapon_handedness(item) -> str:
        handed = getattr(item, "handed", None)
        try:
            if int(handed) >= 2:
                return "Two-handed"
            if int(handed) == 1:
                return "One-handed"
        except (TypeError, ValueError):
            pass

        subtyp = str(getattr(item, "subtyp", "") or "")
        return "Two-handed" if subtyp in TWO_HANDED_WEAPON_SUBTYPES else "One-handed"

    @classmethod
    def _equipment_display_name(cls, item) -> str:
        name = cls._attr_name(item)
        typ = str(getattr(item, "typ", "") or "")
        if typ == "Weapon":
            handedness = cls._weapon_handedness(item)
            if handedness == "Two-handed":
                return f"{name} (2H)"
            if handedness == "One-handed":
                return f"{name} (1H)"
        return name

    def equipment_slot_detail_rows(self, slot: str, item) -> tuple[tuple[str, str], ...]:
        details: list[tuple[str, str]] = []
        typ = str(getattr(item, "typ", "") or "")
        subtyp = str(getattr(item, "subtyp", "") or "")
        if subtyp and subtyp != "None" and slot in {"Weapon", "Armor", "OffHand", "Helmet"}:
            details.append(("Type", subtyp))

        if slot in {"Weapon", "OffHand"} and (
            typ == "Weapon" or getattr(item, "damage", None) not in (None, 0, "")
        ):
            details.append(("Base Damage", self._display_number(getattr(item, "damage", 0))))
            details.append(
                (
                    "Crit",
                    self._display_percent(getattr(item, "crit_chance", getattr(item, "crit", 0))),
                )
            )
        elif (
            slot in {"Armor", "Helmet"}
            or typ in {"Armor", "Helmet"}
            or getattr(item, "armor", None) not in (None, 0, "")
        ):
            details.append(("Base Armor", self._display_number(getattr(item, "armor", 0))))
        elif slot == "OffHand" or typ == "OffHand":
            mod = getattr(item, "mod", None)
            if subtyp == "Shield" and mod not in (None, "", 0):
                details.append(("Block", self._display_percent(mod)))
            elif mod not in (None, "", 0):
                details.append(("Spell Mod", self._display_number(mod)))

        element = getattr(item, "element", None)
        if element:
            details.append(("Element", str(element)))
        return tuple(details)

    def equipment_slot_details(self, slot: str, item) -> tuple[str, ...]:
        return tuple(
            f"{label}: {value}" for label, value in self.equipment_slot_detail_rows(slot, item)
        )

    def equipment_slot_buffs(self, item) -> tuple[str, ...]:
        buffs: list[str] = []
        if self._attr_name(item) == "Svalinn":
            buffs.append("+25% Fire Resistance")

        resist_mod = getattr(item, "resist_mod", None)
        element = getattr(item, "element", None)
        if resist_mod is not None and element:
            try:
                percent = int(float(resist_mod) * 100)
            except (TypeError, ValueError):
                percent = 0
            if percent:
                buffs.append(f"+{percent}% {element} Resistance")

        resistances = getattr(item, "resistances", None)
        if isinstance(resistances, dict):
            for name, value in resistances.items():
                try:
                    percent = int(float(value) * 100)
                except (TypeError, ValueError):
                    percent = 0
                if percent:
                    buffs.append(f"{percent:+d}% {name} Resistance")

        str(getattr(item, "subtyp", "") or "")
        mod = str(getattr(item, "mod", "") or "")
        if mod and mod not in {"0", "No Mod", "None"} and not self._is_number(mod):
            if mod.startswith("Resist-"):
                buffs.append(f"+50% {mod.removeprefix('Resist-')} Resistance")
            elif mod.startswith("Immune-"):
                buffs.append(f"Immune to {mod.removeprefix('Immune-')}")
            else:
                buffs.append(mod)
        return tuple(buffs)

    @staticmethod
    def _is_number(value: Any) -> bool:
        try:
            float(value)
        except (TypeError, ValueError):
            return False
        return True

    def group_resistances(self, player_char) -> dict[str, list[ResistanceSummary]]:
        resistance = getattr(player_char, "resistance", {}) or {}
        weaknesses: list[ResistanceSummary] = []
        resistances: list[ResistanceSummary] = []
        for name in RESISTANCE_ORDER:
            try:
                value = float(player_char.check_mod("resist", typ=name) or 0.0)
            except (AttributeError, TypeError, ValueError):
                value = float(resistance.get(name, 0.0) or 0.0)
            summary = ResistanceSummary(name, value)
            if value < 0:
                weaknesses.append(summary)
            elif value > 0:
                resistances.append(summary)
        return {"weaknesses": weaknesses, "resistances": resistances}

    def collect_equipment_buffs(self, player_char) -> list[EquipmentBuffSummary]:
        equipment = getattr(player_char, "equipment", {}) or {}
        buffs: list[EquipmentBuffSummary] = []
        seen: set[str] = set()

        def add(name: str, source: str) -> None:
            if not name or name in seen:
                return
            buffs.append(EquipmentBuffSummary(name, source))
            seen.add(name)

        for slot in ("Weapon", "Armor", "OffHand", "Ring", "Pendant"):
            item = equipment.get(slot)
            mod = str(getattr(item, "mod", "") or "")
            if not mod:
                continue
            if mod in {
                "Vision",
                "Flying",
                "Invisible",
                "Accuracy",
                "Dodge",
                "Block",
            } or mod.startswith("Status-"):
                add(mod, f"{slot}: {self._attr_name(item)}")

        if getattr(player_char, "sight", False):
            add("Vision", "Character state")
        if getattr(player_char, "flying", False):
            add("Flying", "Character state")
        if getattr(player_char, "invisible", False):
            add("Invisible", "Character state")
        return buffs

    def _fit_text(self, text: str, font, max_width: int) -> str:
        if font.size(text)[0] <= max_width:
            return text
        ellipsis = "..."
        trimmed = text
        while trimmed and font.size(trimmed + ellipsis)[0] > max_width:
            trimmed = trimmed[:-1]
        return (trimmed + ellipsis) if trimmed else ellipsis
