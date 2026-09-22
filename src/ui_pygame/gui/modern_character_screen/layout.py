"""Layout behavior for the modern character screen package."""

from __future__ import annotations

from typing import Any

import pygame

from src.core.classes import ability_mechanics, grandmaster

from ..confirmation_popup import ConfirmationPopup
from .companion_popup import ClassCompanionDetailsPopup
from .models import RESISTANCE_SLOT_COUNT


class CharacterLayoutMixin:
    def _draw_text(
        self, text: str, font, color, x: int, y: int, max_width: int | None = None
    ) -> int:
        display_text = (
            self._fit_text(str(text), font, max_width) if max_width is not None else str(text)
        )
        surface = font.render(display_text, True, color)
        self.screen.blit(surface, (x, y))
        return surface.get_height()

    def _draw_wrapped_text(
        self, text: str, font, color, x: int, y: int, max_width: int, max_lines: int = 2
    ) -> int:
        words = str(text).split()
        if not words:
            return y

        lines: list[str] = []
        current = ""
        for word in words:
            candidate = word if not current else f"{current} {word}"
            if font.size(candidate)[0] <= max_width:
                current = candidate
                continue
            if current:
                lines.append(current)
            current = word
            if len(lines) >= max_lines:
                break
        if current and len(lines) < max_lines:
            lines.append(current)

        for index, line in enumerate(lines[:max_lines]):
            if (
                index == max_lines - 1
                and len(lines) == max_lines
                and words
                and " ".join(words) != " ".join(lines)
            ):
                line = self._fit_text(line, font, max_width)
            self._draw_text(line, font, color, x, y, max_width)
            y += font.get_height() + 4
        return y

    def _draw_panel(self, rect: pygame.Rect, title: str | None = None) -> int:
        self.draw_semi_transparent_panel(rect, alpha=205)
        pygame.draw.rect(self.screen, self.colors.BORDER_COLOR, rect, 2)
        y = rect.top + 14
        if title:
            self._draw_text(
                title, self.large_font, self.colors.GOLD, rect.left + 16, y, rect.width - 32
            )
            y += self.large_font.get_height() + 10
        return y

    def _draw_divider(self, rect: pygame.Rect, y: int) -> None:
        pygame.draw.line(
            self.screen,
            self.colors.BORDER_COLOR,
            (rect.left + 16, y),
            (rect.right - 16, y),
            1,
        )

    def draw_tabs(self, player_char=None):
        self._draw_panel(self.tab_rect)
        visible_tabs = self.visible_tabs(player_char)
        for index, tab in enumerate(visible_tabs):
            rect = self.tab_button_rects(player_char)[index]
            active = tab.key == self.active_tab_key
            if active:
                pygame.draw.rect(self.screen, self.colors.HIGHLIGHT_BG, rect)
                pygame.draw.rect(self.screen, self.colors.GOLD, rect, 2)
            self._draw_text(
                tab.label,
                self.normal_font,
                self.colors.GOLD if active else self.colors.WHITE,
                rect.left + 12,
                rect.centery - self.normal_font.get_height() // 2,
                rect.width - 24,
            )

    def tab_button_rects(self, player_char=None) -> list[pygame.Rect]:
        """Return clickable rectangles for character tabs."""
        visible_tabs = self.visible_tabs(player_char)
        metrics = self.presenter.layout_metrics
        padding = metrics.unit(12)
        x = self.tab_rect.left + padding
        tab_width = max(
            metrics.unit(120),
            min(
                metrics.unit(220),
                (self.tab_rect.width - (padding * 2)) // max(1, len(visible_tabs)),
            ),
        )
        return [
            pygame.Rect(
                x + (index * tab_width),
                self.tab_rect.top + metrics.unit(8),
                tab_width - metrics.unit(8),
                self.tab_rect.height - metrics.unit(16),
            )
            for index, _tab in enumerate(visible_tabs)
        ]

    def character_stat_column_rects(
        self,
        rows: list[tuple[str, str]],
        rect: pygame.Rect,
        preferred_font,
    ) -> tuple[pygame.Rect, pygame.Rect, object]:
        """Measure separate label and value columns without abbreviating stat labels."""
        metrics = self.presenter.layout_metrics
        padding = metrics.unit(16)
        column_gap = metrics.unit(12)
        available_width = rect.width - (padding * 2) - column_gap
        value_width = max(
            metrics.unit(42),
            max((preferred_font.size(value)[0] for _label, value in rows), default=0),
        )
        label_font = preferred_font
        for candidate in (preferred_font, self.normal_font, self.small_font):
            label_width = max((candidate.size(label)[0] for label, _value in rows), default=0)
            if label_width + value_width <= available_width:
                label_font = candidate
                break
        else:
            label_width = max((self.small_font.size(label)[0] for label, _value in rows), default=0)
            label_font = self.small_font

        label_width = max((label_font.size(label)[0] for label, _value in rows), default=0)
        value_column_width = max(metrics.unit(1), available_width - label_width)
        label_rect = pygame.Rect(rect.left + padding, rect.top, label_width, rect.height)
        value_rect = pygame.Rect(
            label_rect.right + column_gap,
            rect.top,
            value_column_width,
            rect.height,
        )
        return label_rect, value_rect, label_font

    def _draw_character_stat_rows(
        self,
        rows: list[tuple[str, str]],
        rect: pygame.Rect,
        y: int,
        *,
        preferred_font,
        row_gap: int,
        bottom_limit: int,
    ) -> int:
        """Draw Character-tab stats in measured, non-overlapping columns."""
        label_rect, value_rect, label_font = self.character_stat_column_rects(
            rows, rect, preferred_font
        )
        row_height = max(label_font.get_height(), preferred_font.get_height())
        for label, value in rows:
            if y + row_height > bottom_limit:
                break
            label_surface = label_font.render(label, True, self.colors.GRAY)
            value_surface = preferred_font.render(value, True, self.colors.WHITE)
            self.screen.blit(
                label_surface,
                (label_rect.left, y + (row_height - label_surface.get_height()) // 2),
            )
            self.screen.blit(
                value_surface,
                (
                    value_rect.right - value_surface.get_width(),
                    y + (row_height - value_surface.get_height()) // 2,
                ),
            )
            y += row_height + row_gap
        return y

    def draw_character_panel(self, player_char):
        y = self._draw_panel(self.character_panel_rect, "Character")
        portrait_surface = self.load_portrait(player_char)
        portrait_rows = self.build_portrait_details(player_char)
        initial_portrait = self.portrait_frame_rect(y, portrait_surface)
        detail_gap = 8
        detail_bottom_padding = 8
        detail_height = self._portrait_details_min_height(portrait_rows, initial_portrait.width)
        portrait = self.portrait_frame_rect(
            y,
            portrait_surface,
            reserved_bottom=detail_gap + detail_height + detail_bottom_padding,
        )
        pygame.draw.rect(self.screen, self.colors.DARK_GRAY, portrait)
        pygame.draw.rect(self.screen, self.colors.BORDER_COLOR, portrait, 2)
        if portrait_surface is not None:
            self._draw_fitted_surface(portrait_surface, portrait)
            pygame.draw.rect(self.screen, self.colors.BORDER_COLOR, portrait, 2)
        else:
            self._draw_text(
                "Portrait",
                self.small_font,
                self.colors.GRAY,
                portrait.left + 10,
                portrait.centery - self.small_font.get_height() // 2,
                portrait.width - 20,
            )

        detail_y = portrait.bottom + detail_gap
        detail_rect = pygame.Rect(
            portrait.left,
            detail_y,
            portrait.width,
            self.character_panel_rect.bottom - detail_y - detail_bottom_padding,
        )
        self._draw_portrait_details(portrait_rows, detail_rect, detail_y)

        info_x = portrait.right + 16
        info_y = y
        info_width = self.character_panel_rect.right - info_x - 16
        identity_label_font = self.normal_font
        identity_value_font = self.large_font
        for label, value in self.build_character_summary(player_char):
            label_text = label.upper()
            label_width = identity_label_font.size(label_text)[0]
            self._draw_text(
                label_text,
                identity_label_font,
                self.colors.GRAY,
                info_x + max(0, info_width - label_width),
                info_y,
                info_width,
            )
            info_y += identity_label_font.get_height()
            value_text = self._fit_text(value, identity_value_font, info_width)
            value_width = identity_value_font.size(value_text)[0]
            self._draw_text(
                value_text,
                identity_value_font,
                self.colors.WHITE,
                info_x + max(0, info_width - value_width),
                info_y,
                info_width,
            )
            info_y += identity_value_font.get_height() + 8

        bar_width = max(140, info_width * 3 // 4)
        bar_rect = pygame.Rect(
            self.character_panel_rect.right - 16 - bar_width, info_y + 2, bar_width, 18
        )
        pygame.draw.rect(self.screen, self.colors.DARK_GRAY, bar_rect)
        fill_rect = pygame.Rect(
            bar_rect.left,
            bar_rect.top,
            int(bar_rect.width * self.xp_progress(player_char)),
            bar_rect.height,
        )
        pygame.draw.rect(self.screen, self.colors.GREEN, fill_rect)
        pygame.draw.rect(self.screen, self.colors.BORDER_COLOR, bar_rect, 1)
        xp_label = self.xp_label(player_char)
        xp_label_width = self.small_font.size(xp_label)[0]
        xp_label_x = self.character_panel_rect.right - 16 - min(info_width, xp_label_width)
        self._draw_text(
            xp_label, self.small_font, self.colors.GRAY, xp_label_x, bar_rect.bottom + 6, info_width
        )

        attribute_rows = self.build_core_attributes(player_char)
        y = bar_rect.bottom + self.small_font.get_height() + 22
        attribute_rect = pygame.Rect(
            info_x - 16,
            y,
            self.character_panel_rect.right - info_x + 16,
            self.character_panel_rect.bottom - y - 16,
        )
        attribute_font = self.large_font
        attribute_gap = 8
        available_attribute_height = (
            self.character_panel_rect.bottom - y - self.large_font.get_height() - 16
        )
        large_attribute_height = len(attribute_rows) * (
            self.large_font.get_height() + attribute_gap
        )
        normal_attribute_height = len(attribute_rows) * (self.normal_font.get_height() + 2)
        if large_attribute_height > available_attribute_height:
            attribute_font = self.normal_font
            attribute_gap = 2
        if normal_attribute_height > available_attribute_height:
            attribute_font = self.small_font
            attribute_gap = 2
        self._draw_divider(attribute_rect, y - 10)
        self._draw_text("Core Attributes", self.large_font, self.colors.GOLD, info_x, y, info_width)
        y += self.large_font.get_height() + 8
        self._draw_character_stat_rows(
            attribute_rows,
            attribute_rect,
            y,
            preferred_font=attribute_font,
            row_gap=attribute_gap,
            bottom_limit=self.character_panel_rect.bottom - self.presenter.layout_metrics.unit(16),
        )

    def draw_combat_panel(self, player_char):
        y = self._draw_panel(self.combat_panel_rect, "Combat Stats")
        combat_rows = self.build_combat_stats(player_char)
        groups = self.group_resistances(player_char)
        resistance_font = self.small_font
        resistance_row_gap = 3
        resistance_row_height = resistance_font.get_height() + resistance_row_gap
        resistance_height = (
            self.large_font.get_height() + 6 + (RESISTANCE_SLOT_COUNT * resistance_row_height)
        )
        resistance_top = self.combat_panel_rect.bottom - resistance_height - 16
        available_stat_height = resistance_top - y - 12
        if available_stat_height >= len(combat_rows) * (self.large_font.get_height() + 4):
            stat_font = self.large_font
            stat_gap = 4
        elif available_stat_height >= len(combat_rows) * (self.normal_font.get_height() + 3):
            stat_font = self.normal_font
            stat_gap = 3
        else:
            stat_font = self.small_font
            stat_gap = 1
        y = self._draw_character_stat_rows(
            combat_rows,
            self.combat_panel_rect,
            y,
            preferred_font=stat_font,
            row_gap=stat_gap,
            bottom_limit=resistance_top - self.presenter.layout_metrics.unit(12),
        )

        y = max(y + 12, resistance_top)
        self._draw_divider(self.combat_panel_rect, y - 10)
        column_gap = 12
        column_width = (self.combat_panel_rect.width - 32 - column_gap) // 2
        weakness_rect = pygame.Rect(
            self.combat_panel_rect.left + 16,
            y,
            column_width,
            self.combat_panel_rect.bottom - y - 16,
        )
        resistance_rect = pygame.Rect(
            weakness_rect.right + column_gap, y, column_width, weakness_rect.height
        )
        self._draw_text(
            "Weaknesses",
            self.large_font,
            self.colors.RED,
            weakness_rect.left,
            y,
            weakness_rect.width,
        )
        self._draw_text(
            "Resistances",
            self.large_font,
            self.colors.GREEN,
            resistance_rect.left,
            y,
            resistance_rect.width,
        )
        group_y = y + self.large_font.get_height() + 6
        self._draw_resistance_group(
            groups["weaknesses"],
            weakness_rect,
            group_y,
            self.colors.RED,
            font=resistance_font,
            row_gap=resistance_row_gap,
        )
        self._draw_resistance_group(
            groups["resistances"],
            resistance_rect,
            group_y,
            self.colors.GREEN,
            font=resistance_font,
            row_gap=resistance_row_gap,
        )

    def _draw_companion_art_block(self, kind: str, companion: Any, rect: pygame.Rect) -> None:
        pygame.draw.rect(self.screen, (14, 14, 19), rect)
        pygame.draw.rect(self.screen, self.colors.BORDER_COLOR, rect, 1)
        art_size = max(54, min(84, rect.height - 20, rect.width // 4))
        art_rect = pygame.Rect(
            rect.left + 10, rect.top + (rect.height - art_size) // 2, art_size, art_size
        )
        sprite = self.companion_art_manager.get_scaled_sprite(companion, art_rect.size)
        self.screen.blit(sprite, art_rect)

        text_x = art_rect.right + 12
        text_width = rect.right - text_x - 10
        y = rect.top + 10
        self._draw_text(kind, self.small_font, self.colors.GOLD, text_x, y, text_width)
        y += self.small_font.get_height() + 4
        for label, value in self.companion_summary_rows(kind, companion)[:3]:
            self._draw_text(
                label, self.small_font, self.colors.GRAY, text_x, y, max(70, text_width // 3)
            )
            self._draw_text(
                value,
                self.small_font,
                self.colors.WHITE,
                text_x + max(76, text_width // 3),
                y,
                max(40, text_width - max(76, text_width // 3)),
            )
            y += self.small_font.get_height() + 3

    def class_companion_entries(self, player_char) -> list[tuple[str, Any]]:
        """Return all companions worth showing on the Class tab."""
        entries: list[tuple[str, Any]] = []
        familiar = getattr(player_char, "familiar", None)
        class_name = self._attr_name(getattr(player_char, "cls", None), "")
        tamed_state = ability_mechanics.normalize_tamed_companion(
            getattr(player_char, "tamed_companion", None)
        )
        tamed_roster = tamed_state.get("companions", [])
        if isinstance(tamed_roster, list) and tamed_roster:
            try:
                from src.core import companions

                indexed_roster = list(enumerate(tamed_roster))
                if class_name in {"Ranger", "Beast Master"}:
                    active_index = tamed_state.get("active_index")
                    indexed_roster = [
                        (index, entry) for index, entry in indexed_roster if index == active_index
                    ]
                for index, entry in indexed_roster:
                    display_entry = dict(entry)
                    display_entry["active"] = True
                    companion = companions.tamed_companion_from_state(display_entry)
                    if companion is None:
                        continue
                    kind = (
                        "Companion"
                        if index == tamed_state.get("active_index")
                        else "Held Companion"
                    )
                    entries.append((kind, companion))
            except Exception:
                if familiar is not None:
                    entries.append(("Companion", familiar))
        elif familiar is not None:
            kind = "Companion" if getattr(familiar, "spec", "") == "Tamed" else "Familiar"
            entries.append((kind, familiar))

        summons = getattr(player_char, "summons", {}) or {}
        for summon in summons.values():
            entries.append(("Xenid", summon))
        return entries

    def _companion_xp_label(self, companion: Any) -> str:
        level = getattr(companion, "level", None)
        if getattr(companion, "cls", None) == "Familiar":
            return f"Level {int(getattr(level, 'pro_level', 1) or 1)}"
        if getattr(level, "level", 1) >= 10:
            return "MAX"
        exp = self._non_negative_int(getattr(level, "exp", 0))
        to_next = self._non_negative_int(getattr(level, "exp_to_gain", 0))
        total = exp + to_next
        if total <= 0:
            return "0/0 XP"
        return f"{exp}/{total} XP"

    def _summon_bond_label(self, player_char, companion: Any) -> str | None:
        name = self._attr_name(companion, "")
        if getattr(companion, "spec", "") == "Tamed":
            return f"{self._non_negative_int(getattr(companion, 'bond', 0))}/100"
        state = getattr(player_char, "promotion_kit_state", {}) or {}
        bonds = state.get("summon_bonds", {}) if isinstance(state, dict) else {}
        if name not in bonds:
            return None
        return f"{self._non_negative_int(bonds.get(name))}/100"

    def _draw_class_companion_card(self, kind: str, companion: Any, rect: pygame.Rect) -> None:
        pygame.draw.rect(self.screen, (14, 14, 19), rect)
        pygame.draw.rect(self.screen, self.colors.BORDER_COLOR, rect, 1)
        art_size = max(72, min(116, rect.height - 22, rect.width // 5))
        art_rect = pygame.Rect(
            rect.left + 12, rect.top + (rect.height - art_size) // 2, art_size, art_size
        )
        sprite = self.companion_art_manager.get_scaled_sprite(companion, art_rect.size)
        self.screen.blit(sprite, art_rect)

        text_x = art_rect.right + 14
        text_width = rect.right - text_x - 12
        y = rect.top + 12
        name = self._attr_name(companion, kind)
        self._draw_text(name, self.normal_font, self.colors.GOLD, text_x, y, text_width)
        y += self.normal_font.get_height() + 4

        row_rect = pygame.Rect(text_x, y, text_width, rect.bottom - y - 10)
        detail_rows = self.companion_detail_rows(kind, companion)
        self._draw_key_values(
            detail_rows,
            row_rect,
            y,
            font=self.small_font,
            label_padding=18,
            row_gap=1,
            bottom_limit=rect.bottom - 10,
        )

    def _class_companion_large_slot_rect(self) -> pygame.Rect:
        """Return the shared large slot geometry for a tamed companion."""
        roster_rect = self._class_roster_rect
        top = roster_rect.top + self.normal_font.get_height() + 10
        available_height = max(1, roster_rect.bottom - top)
        return pygame.Rect(
            roster_rect.left,
            top,
            roster_rect.width,
            min(180, available_height),
        )

    def _draw_empty_companion_slot(self) -> None:
        """Draw one large placeholder for a Ranger without a companion."""
        rect = self._class_companion_large_slot_rect()
        pygame.draw.rect(self.screen, (14, 14, 19), rect)
        pygame.draw.rect(self.screen, self.colors.BORDER_COLOR, rect, 1)
        label_y = rect.centery - self.normal_font.get_height() - 4
        self._draw_text(
            "No Active Companion",
            self.normal_font,
            self.colors.GRAY,
            rect.left + 16,
            label_y,
            rect.width - 32,
        )
        self._draw_text(
            "Tame a wounded Animal to form a bond.",
            self.small_font,
            self.colors.GRAY,
            rect.left + 16,
            label_y + self.normal_font.get_height() + 8,
            rect.width - 32,
        )

    def class_companion_tile_rects(self, entries: list[tuple[str, Any]]) -> list[pygame.Rect]:
        """Return stacked clickable companion row rectangles for the Class tab."""
        if not entries or not hasattr(self, "_class_roster_rect"):
            return []
        if len(entries) == 1 and getattr(entries[0][1], "spec", "") == "Tamed":
            return [self._class_companion_large_slot_rect()]

        roster_rect = self._class_roster_rect
        gap = 6
        tile_width = roster_rect.width
        top = roster_rect.top + self.normal_font.get_height() + 10
        available_height = max(1, roster_rect.bottom - top)
        tile_height = min(
            64, max(30, (available_height - gap * (len(entries) - 1)) // len(entries))
        )
        rects = []
        for index, _entry in enumerate(entries):
            rects.append(
                pygame.Rect(
                    roster_rect.left,
                    top + index * (tile_height + gap),
                    tile_width,
                    tile_height,
                )
            )
        return rects

    def weapon_discipline_row_rects(self) -> list[pygame.Rect]:
        """Return clickable Weapon Discipline row rectangles for the Class tab."""
        return list(getattr(self, "_weapon_discipline_row_rects", []))

    def _draw_inline_companion_fields(
        self,
        fields: list[tuple[str, str]],
        rect: pygame.Rect,
        y: int,
        *,
        selected: bool,
    ) -> None:
        x = rect.left + 12
        max_x = rect.right - 10
        label_color = self.colors.GOLD if selected else self.colors.GRAY
        for label, value in fields:
            label_text = str(label)
            label_width = self.small_font.size(label_text)[0]
            value_width = self.small_font.size(str(value))[0]
            if x + label_width + 4 + value_width > max_x:
                break
            self._draw_text(label_text, self.small_font, label_color, x, y, label_width)
            x += label_width + 4
            self._draw_text(str(value), self.small_font, self.colors.WHITE, x, y, max_x - x)
            x += value_width + 14

    def _draw_class_companion_tile(
        self,
        kind: str,
        companion: Any,
        rect: pygame.Rect,
        *,
        selected: bool,
        player_char,
    ) -> None:
        if rect.height > 100:
            self._draw_class_companion_card(kind, companion, rect)
            pygame.draw.rect(
                self.screen,
                self.colors.GOLD if selected else self.colors.BORDER_COLOR,
                rect,
                2 if selected else 1,
            )
            return

        pygame.draw.rect(self.screen, self.colors.HIGHLIGHT_BG if selected else (14, 14, 19), rect)
        pygame.draw.rect(
            self.screen,
            self.colors.GOLD if selected else self.colors.BORDER_COLOR,
            rect,
            2 if selected else 1,
        )

        text_x = rect.left + 12
        text_width = rect.right - text_x - 8
        y = rect.top + 8
        name = self._attr_name(companion, kind)
        name_width = max(90, min(text_width // 2, self.normal_font.size(name)[0] + 8))
        self._draw_text(name, self.normal_font, self.colors.GOLD, text_x, y, name_width)

        fields = [("Type", kind)]
        if getattr(companion, "spec", "") != "Tamed":
            level = getattr(getattr(companion, "level", None), "level", "?")
            fields.append(("Level", str(level)))
        if getattr(companion, "spec", "") == "Tamed":
            evolution = str(getattr(companion, "evolution", "") or "")
            special = str(getattr(companion, "special_ability", "") or "")
            if evolution:
                fields.append(("Form", evolution))
            if special:
                fields.append(("Special", special))
        if getattr(companion, "spec", "") != "Tamed":
            health = getattr(companion, "health", None)
            fields.append(("HP", f"{getattr(health, 'current', 0)}/{getattr(health, 'max', 0)}"))
            fields.append(("XP", self._companion_xp_label(companion)))
        bond = self._summon_bond_label(player_char, companion)
        if bond is not None:
            fields.append(("Bond", bond))

        first_line_fields = fields[:2]
        second_line_fields = fields[2:]
        field_x = text_x + name_width + 8
        self._draw_inline_companion_fields(
            first_line_fields,
            pygame.Rect(field_x, y + 2, rect.right - field_x - 8, self.small_font.get_height()),
            y + 2,
            selected=selected,
        )
        detail_y = min(
            rect.bottom - self.small_font.get_height() - 4, y + self.normal_font.get_height() + 1
        )
        self._draw_inline_companion_fields(
            second_line_fields,
            pygame.Rect(text_x, detail_y, text_width, self.small_font.get_height()),
            detail_y,
            selected=selected,
        )

    def _open_class_companion_popup(self, player_char) -> None:
        entries = self.class_companion_entries(player_char)
        if not entries:
            return
        self.selected_class_companion_index = max(
            0,
            min(self.selected_class_companion_index, len(entries) - 1),
        )
        kind, companion = entries[self.selected_class_companion_index]
        background = self.screen.copy()
        popup = ClassCompanionDetailsPopup(self.presenter, self, player_char, kind, companion)
        popup.show(
            background_draw_func=lambda: self.screen.blit(background, (0, 0)),
            flush_events=True,
            require_key_release=True,
        )

    def _selected_tamed_roster_index(self, player_char) -> int | None:
        entries = self.class_companion_entries(player_char)
        if not entries:
            return None
        selected_index = max(0, min(self.selected_class_companion_index, len(entries) - 1))
        kind, companion = entries[selected_index]
        if kind not in {"Companion", "Held Companion"} or getattr(companion, "spec", "") != "Tamed":
            return None
        class_name = self._attr_name(getattr(player_char, "cls", None), "")
        if class_name in {"Ranger", "Beast Master"}:
            state = ability_mechanics.normalize_tamed_companion(
                getattr(player_char, "tamed_companion", None)
            )
            active_index = state.get("active_index")
            return active_index if isinstance(active_index, int) else None
        roster_index = 0
        for entry_kind, entry_companion in entries[: selected_index + 1]:
            if (
                entry_kind in {"Companion", "Held Companion"}
                and getattr(entry_companion, "spec", "") == "Tamed"
            ):
                if entry_companion is companion:
                    return roster_index
                roster_index += 1
        return None

    def _activate_selected_tamed_companion(self, player_char) -> None:
        roster_index = self._selected_tamed_roster_index(player_char)
        if roster_index is None:
            return
        ability_mechanics.activate_tamed_companion(player_char, roster_index)
        self.selected_class_companion_index = roster_index

    def _release_selected_tamed_companion(self, player_char) -> None:
        roster_index = self._selected_tamed_roster_index(player_char)
        if roster_index is None:
            return
        entries = self.class_companion_entries(player_char)
        companion_name = "this companion"
        tamed_index = -1
        for kind, companion in entries:
            if (
                kind in {"Companion", "Held Companion"}
                and getattr(companion, "spec", "") == "Tamed"
            ):
                tamed_index += 1
                if tamed_index == roster_index:
                    companion_name = getattr(companion, "name", companion_name)
                    break
        background = self.screen.copy()
        popup = ConfirmationPopup(
            self.presenter,
            f"Release {companion_name}?",
            show_buttons=True,
        )
        if not popup.show(
            background_draw_func=lambda: self.screen.blit(background, (0, 0)),
            flush_events=True,
            require_key_release=True,
        ):
            return
        ability_mechanics.release_tamed_companion(player_char, roster_index)
        entries = self.class_companion_entries(player_char)
        self.selected_class_companion_index = max(
            0,
            min(self.selected_class_companion_index, max(0, len(entries) - 1)),
        )
        self.class_companion_selector_active = bool(entries)

    def _open_weapon_discipline_popup(self, player_char) -> None:
        if not grandmaster.is_weapon_discipline_class(player_char):
            return
        weapon_types = grandmaster.weapon_discipline_types(player_char)
        self.selected_weapon_discipline_index = max(
            0,
            min(self.selected_weapon_discipline_index, len(weapon_types) - 1),
        )
        weapon_type = weapon_types[self.selected_weapon_discipline_index]
        background = self.screen.copy()
        popup = ConfirmationPopup(
            self.presenter,
            self.weapon_discipline_detail_text(player_char, weapon_type),
            show_buttons=False,
        )
        popup.show(
            background_draw_func=lambda: self.screen.blit(background, (0, 0)),
            flush_events=True,
            require_key_release=True,
        )

    def _draw_weapon_discipline_progress_bar(
        self,
        rect: pygame.Rect,
        *,
        xp: int,
        rank: int,
        equipped: bool,
    ) -> None:
        fill_width = int(rect.width * self._weapon_discipline_progress_fraction(xp, rank))
        pygame.draw.rect(self.screen, (24, 24, 28), rect)
        if fill_width > 0:
            fill_rect = pygame.Rect(rect.left, rect.top, fill_width, rect.height)
            pygame.draw.rect(
                self.screen, self.colors.GOLD if equipped else self.colors.GREEN, fill_rect
            )
        pygame.draw.rect(
            self.screen, self.colors.GOLD if equipped else self.colors.BORDER_COLOR, rect, 1
        )

    def _draw_weapon_discipline_row(
        self,
        weapon_type: str,
        entry: dict[str, Any],
        rect: pygame.Rect,
        *,
        equipped: bool,
        selected: bool,
    ) -> None:
        highlighted = equipped or selected
        border_color = self.colors.GOLD if highlighted else self.colors.BORDER_COLOR
        pygame.draw.rect(
            self.screen, self.colors.HIGHLIGHT_BG if highlighted else (14, 14, 19), rect
        )
        pygame.draw.rect(self.screen, border_color, rect, 2 if highlighted else 1)

        icon_size = min(40, max(28, rect.height - 12))
        icon_rect = pygame.Rect(
            rect.left + 8, rect.top + (rect.height - icon_size) // 2, icon_size, icon_size
        )
        self._draw_item_art_backdrop(icon_rect)
        icon_item = self._weapon_discipline_icon_item(weapon_type)
        render = self.item_render_manager.get_scaled_render(icon_item, icon_rect.size)
        self.screen.blit(render, icon_rect)

        xp = self._non_negative_float(entry.get("xp", 0))
        rank = self._non_negative_int(entry.get("rank", 0))
        name_color = self.colors.GOLD if equipped else self.colors.WHITE
        detail_color = self.colors.WHITE if highlighted else self.colors.GRAY
        text_x = icon_rect.right + 10
        name_width = min(150, max(104, rect.width // 3))
        name_y = rect.centery - self.normal_font.get_height() // 2
        self._draw_text(weapon_type, self.normal_font, name_color, text_x, name_y, name_width)
        if equipped:
            equipped_y = min(
                rect.bottom - self.small_font.get_height() - 4,
                name_y + self.normal_font.get_height() - 1,
            )
            self._draw_text(
                "Equipped", self.small_font, detail_color, text_x, equipped_y, name_width
            )

        bar_x = text_x + name_width + 12
        bar_width = max(80, rect.right - bar_x - 12)
        rank_text = f"Rank {rank}"
        xp_text = self._weapon_discipline_progress_label(xp, rank)
        self._draw_text(
            rank_text, self.small_font, self.colors.WHITE, bar_x, rect.top + 7, bar_width
        )
        xp_width = self.small_font.size(xp_text)[0]
        self._draw_text(
            xp_text,
            self.small_font,
            detail_color,
            rect.right - 12 - min(xp_width, bar_width),
            rect.top + 7,
            bar_width,
        )
        bar_rect = pygame.Rect(bar_x, rect.top + 30, bar_width, 10)
        self._draw_weapon_discipline_progress_bar(bar_rect, xp=xp, rank=rank, equipped=equipped)

    def _draw_weapon_discipline_panel(
        self, player_char, rect: pygame.Rect, y: int, *, show_heading: bool = True
    ) -> None:
        if show_heading:
            self._draw_text(
                "Weapon Discipline", self.normal_font, self.colors.GOLD, rect.left, y, rect.width
            )
            y += self.normal_font.get_height() + 10
        weapon_types = grandmaster.weapon_discipline_types(player_char)
        self.selected_weapon_discipline_index = max(
            0,
            min(self.selected_weapon_discipline_index, len(weapon_types) - 1),
        )
        helper = "Arrows: Select  Enter: Details"
        helper_width = self.small_font.size(helper)[0]
        self._draw_text(
            helper,
            self.small_font,
            self.colors.GRAY,
            rect.right - min(helper_width, rect.width),
            y,
            rect.width,
        )
        y += self.small_font.get_height() + 6
        state = grandmaster.normalize_state(getattr(player_char, "grandmaster_discipline", None))
        equipped = {
            weapon_type
            for weapon_type in (
                grandmaster.get_weapon_type(player_char, "Weapon"),
                grandmaster.get_weapon_type(player_char, "OffHand"),
            )
            if weapon_type is not None
        }
        row_gap = 6
        available_height = max(1, rect.bottom - y - 4)
        row_height = min(
            54,
            max(
                42,
                (available_height - row_gap * (len(weapon_types) - 1)) // len(weapon_types),
            ),
        )
        self._weapon_discipline_row_rects = []
        for index, weapon_type in enumerate(weapon_types):
            row_rect = pygame.Rect(
                rect.left, y + index * (row_height + row_gap), rect.width, row_height
            )
            if row_rect.bottom > rect.bottom:
                break
            self._weapon_discipline_row_rects.append(row_rect)
            self._draw_weapon_discipline_row(
                weapon_type,
                state["disciplines"][weapon_type],
                row_rect,
                equipped=weapon_type in equipped,
                selected=index == self.selected_weapon_discipline_index,
            )

    def _draw_meter_bar(self, rect: pygame.Rect, value: int, cap: int, *, color=None) -> None:
        cap = max(1, int(cap or 1))
        value = max(0, min(cap, int(value or 0)))
        fill_width = int(rect.width * (value / cap))
        pygame.draw.rect(self.screen, (24, 24, 28), rect)
        if fill_width > 0:
            pygame.draw.rect(
                self.screen,
                color or self.colors.GREEN,
                pygame.Rect(rect.left, rect.top, fill_width, rect.height),
            )
        pygame.draw.rect(self.screen, self.colors.BORDER_COLOR, rect, 1)

    def _draw_mechanic_note_card(self, rect: pygame.Rect, title: str, body: str, y: int) -> int:
        card = pygame.Rect(rect.left, y, rect.width, max(74, self.small_font.get_height() * 3 + 28))
        pygame.draw.rect(self.screen, (14, 14, 19), card)
        pygame.draw.rect(self.screen, self.colors.BORDER_COLOR, card, 1)
        self._draw_text(
            title,
            self.normal_font,
            self.colors.GOLD,
            card.left + 12,
            card.top + 10,
            card.width - 24,
        )
        return (
            self._draw_wrapped_text(
                body,
                self.small_font,
                self.colors.WHITE,
                card.left + 12,
                card.top + self.normal_font.get_height() + 14,
                card.width - 24,
                max_lines=3,
            )
            + 10
        )
