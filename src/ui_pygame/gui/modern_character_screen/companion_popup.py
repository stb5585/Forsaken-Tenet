"""Companion popup behavior for the modern character screen package."""

from __future__ import annotations

from typing import Any, Protocol

import pygame

from src.ui_pygame.screen_runtime import get_events

from ..confirmation_popup import draw_popup_close_button, popup_close_clicked
from ..input_guards import (
    prepare_guarded_input,
    release_guard_allows_input,
    update_input_armed_from_event,
)
from .models import _whole_stat_text


class ModernCharacterScreenProtocol(Protocol):
    """Structural parent-screen contract used by the companion details popup."""

    colors: Any
    companion_art_manager: Any


class ClassCompanionDetailsPopup:
    """Character-tab-style details modal for familiars, companions, and summons."""

    def __init__(
        self,
        presenter,
        parent_screen: ModernCharacterScreenProtocol,
        player_char,
        kind: str,
        companion: Any,
    ):
        self.presenter = presenter
        self.parent_screen = parent_screen
        self.player_char = player_char
        self.kind = kind
        self.companion = companion
        self.screen = presenter.screen
        self.width = presenter.width
        self.height = presenter.height
        self.small_font = presenter.small_font
        self.normal_font = presenter.normal_font
        self.large_font = presenter.large_font
        self.colors = parent_screen.colors

        popup_width = min(self.width - 60, max(760, self.width * 9 // 10))
        popup_height = min(self.height - 56, max(500, self.height * 4 // 5))
        self.popup_rect = pygame.Rect(
            (self.width - popup_width) // 2,
            (self.height - popup_height) // 2,
            popup_width,
            popup_height,
        )

    def _content_rects(self) -> tuple[pygame.Rect, pygame.Rect]:
        gap = 12
        content = self.popup_rect.inflate(-32, -104)
        content.top = self.popup_rect.top + 72
        content.height = self.popup_rect.bottom - content.top - 42
        left_width = (content.width * 3) // 5
        left_rect = pygame.Rect(content.left, content.top, left_width, content.height)
        right_rect = pygame.Rect(
            left_rect.right + gap,
            content.top,
            content.right - left_rect.right - gap,
            content.height,
        )
        return left_rect, right_rect

    def _draw_overlay(self, background_surface) -> None:
        self.screen.blit(background_surface, (0, 0))
        overlay = pygame.Surface((self.width, self.height), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 180))
        self.screen.blit(overlay, (0, 0))
        pygame.draw.rect(self.screen, (8, 8, 12), self.popup_rect)
        pygame.draw.rect(self.screen, self.colors.BORDER_COLOR, self.popup_rect, 2)
        draw_popup_close_button(self.screen, self.popup_rect, self.small_font)

    def _draw_art_and_identity(self, rect: pygame.Rect, y: int) -> int:
        art_width = min(max(170, rect.width // 3), rect.width // 2)
        art_height = min(max(190, (rect.height * 9) // 20), rect.height - 180)
        art_rect = pygame.Rect(rect.left + 16, y, art_width, art_height)
        sprite = self.parent_screen.companion_art_manager.get_scaled_sprite(
            self.companion, art_rect.size
        )
        self.screen.blit(sprite, art_rect)
        pygame.draw.rect(self.screen, self.colors.BORDER_COLOR, art_rect, 2)

        name = self.parent_screen._attr_name(self.companion, self.kind)
        info_x = art_rect.right + 16
        info_y = y
        info_width = rect.right - info_x - 16
        identity_rows = self.parent_screen.companion_summary_rows(self.kind, self.companion)
        identity_rows = [row for row in identity_rows if row[0] != "Companion"]
        identity_rows.insert(0, ("Name", name))
        if getattr(self.companion, "spec", "") != "Tamed":
            identity_rows.append(("XP", self.parent_screen._companion_xp_label(self.companion)))
        bond = self.parent_screen._summon_bond_label(self.player_char, self.companion)
        if bond is not None:
            identity_rows.append(("Bond", bond))

        for index, (label, value) in enumerate(identity_rows):
            label_text = label.upper()
            label_width = self.normal_font.size(label_text)[0]
            self.parent_screen._draw_text(
                label_text,
                self.normal_font,
                self.colors.GRAY,
                info_x + max(0, info_width - label_width),
                info_y,
                info_width,
            )
            info_y += self.normal_font.get_height()
            value_font = self.large_font if index == 0 else self.normal_font
            value_gap = 8 if index == 0 else 4
            value_text = self.parent_screen._fit_text(str(value), value_font, info_width)
            value_width = value_font.size(value_text)[0]
            self.parent_screen._draw_text(
                value_text,
                value_font,
                self.colors.WHITE,
                info_x + max(0, info_width - value_width),
                info_y,
                info_width,
            )
            info_y += value_font.get_height() + value_gap

        return max(art_rect.bottom, info_y)

    def _core_attribute_rows(self) -> list[tuple[str, str]]:
        stats = getattr(self.companion, "stats", None)
        return [
            ("Strength", str(getattr(stats, "strength", 0))),
            ("Intelligence", str(getattr(stats, "intel", 0))),
            ("Wisdom", str(getattr(stats, "wisdom", 0))),
            ("Constitution", str(getattr(stats, "con", 0))),
            ("Charisma", str(getattr(stats, "charisma", 0))),
            ("Dexterity", str(getattr(stats, "dex", 0))),
        ]

    def _combat_rows(self) -> list[tuple[str, str]]:
        health = getattr(self.companion, "health", None)
        mana = getattr(self.companion, "mana", None)
        combat = getattr(self.companion, "combat", None)
        return [
            ("HP", f"{getattr(health, 'current', 0)}/{getattr(health, 'max', 0)}"),
            ("MP", f"{getattr(mana, 'current', 0)}/{getattr(mana, 'max', 0)}"),
            ("Attack", _whole_stat_text(getattr(combat, "attack", 0))),
            ("Defense", _whole_stat_text(getattr(combat, "defense", 0))),
            ("Magic", _whole_stat_text(getattr(combat, "magic", 0))),
            ("Magic Defense", _whole_stat_text(getattr(combat, "magic_def", 0))),
        ]

    def _ability_names(self) -> list[str]:
        spellbook = getattr(self.companion, "spellbook", {}) or {}
        if not isinstance(spellbook, dict):
            return []
        names: list[str] = []
        for bucket in ("Skills", "Spells"):
            abilities = spellbook.get(bucket, {})
            if isinstance(abilities, dict):
                names.extend(str(name) for name in abilities.keys())
        return names

    def _draw_abilities(self, rect: pygame.Rect, y: int, bottom_limit: int) -> int:
        names = self._ability_names()
        self.parent_screen._draw_divider(rect, y - 10)
        self.parent_screen._draw_text(
            "Abilities", self.large_font, self.colors.GOLD, rect.left + 16, y, rect.width - 32
        )
        y += self.large_font.get_height() + 8
        if not names:
            self.parent_screen._draw_text(
                "None", self.normal_font, self.colors.GRAY, rect.left + 16, y, rect.width - 32
            )
            return y + self.normal_font.get_height() + 8

        available_lines = max(1, (bottom_limit - y) // (self.small_font.get_height() + 4))
        return self.parent_screen._draw_wrapped_text(
            ", ".join(names),
            self.small_font,
            self.colors.WHITE,
            rect.left + 16,
            y,
            rect.width - 32,
            max_lines=available_lines,
        )

    def _draw_familiar_details(self, left_rect, right_rect, y):
        """Draw only meaningful familiar identity and ability information."""
        spec = str(getattr(self.companion, "spec", "General"))
        self.parent_screen._draw_divider(left_rect, y - 8)
        self.parent_screen._draw_text(
            "Specialization",
            self.large_font,
            self.colors.GOLD,
            left_rect.left + 16,
            y,
            left_rect.width - 32,
        )
        y += self.large_font.get_height() + 8
        self.parent_screen._draw_text(
            spec,
            self.normal_font,
            self.colors.WHITE,
            left_rect.left + 16,
            y,
            left_rect.width - 32,
        )
        y += self.normal_font.get_height() + 12
        inspect_text = getattr(self.companion, "inspect", lambda: "")()
        self.parent_screen._draw_wrapped_text(
            inspect_text,
            self.small_font,
            self.colors.LIGHT_GRAY,
            left_rect.left + 16,
            y,
            left_rect.width - 32,
            max_lines=8,
        )

        right_y = self.parent_screen._draw_panel(right_rect, "Abilities")
        spellbook = getattr(self.companion, "spellbook", {}) or {}
        for bucket in ("Skills", "Spells"):
            for name, ability in spellbook.get(bucket, {}).items():
                if right_y + self.normal_font.get_height() > right_rect.bottom - 20:
                    return
                self.parent_screen._draw_text(
                    name,
                    self.normal_font,
                    self.colors.GOLD,
                    right_rect.left + 16,
                    right_y,
                    right_rect.width - 32,
                )
                right_y += self.normal_font.get_height() + 2
                right_y = self.parent_screen._draw_wrapped_text(
                    getattr(ability, "description", ""),
                    self.small_font,
                    self.colors.WHITE,
                    right_rect.left + 24,
                    right_y,
                    right_rect.width - 40,
                    max_lines=2,
                )
                right_y += 8

    def _draw_tamed_companion_flavor(self, rect: pygame.Rect, y: int) -> None:
        self.parent_screen._draw_text(
            "Companion Notes", self.large_font, self.colors.GOLD, rect.left + 16, y, rect.width - 32
        )
        y += self.large_font.get_height() + 10
        notes = [
            getattr(self.companion, "inspect", lambda: "")(),
            "The animal acts through bond and instinct rather than a visible resource pool.",
            "Evolution reflects growing trust and battlefield temperament; deeper effects are a future tuning pass.",
        ]
        for note in notes:
            if not str(note).strip():
                continue
            y = self.parent_screen._draw_wrapped_text(
                str(note).strip(),
                self.normal_font,
                self.colors.WHITE,
                rect.left + 16,
                y,
                rect.width - 32,
                max_lines=3,
            )
            y += 12

    def _draw_tamed_companion_bond_panel(self, rect: pygame.Rect, y: int) -> None:
        rows = self.parent_screen.companion_summary_rows(self.kind, self.companion)
        rows = [(label, value) for label, value in rows if label not in {"Companion", "Type"}]
        if not rows:
            rows = [("Bond", "New")]
        self.parent_screen._draw_key_values(
            rows,
            rect,
            y,
            font=self.normal_font,
            row_gap=8,
            right_align_values=False,
            bottom_limit=rect.bottom - 16,
        )

    def draw(self, background_surface) -> None:
        self._draw_overlay(background_surface)
        name = self.parent_screen._attr_name(self.companion, self.kind)
        title = f"{name} Details"
        title_text = self.presenter.title_font.render(title, True, self.colors.GOLD)
        self.screen.blit(
            title_text,
            (self.popup_rect.centerx - title_text.get_width() // 2, self.popup_rect.top + 18),
        )

        left_rect, right_rect = self._content_rects()
        y = self.parent_screen._draw_panel(left_rect, self.kind)
        y = self._draw_art_and_identity(left_rect, y)
        y += 16
        if getattr(self.companion, "spec", "") == "Tamed":
            self.parent_screen._draw_divider(left_rect, y - 8)
            self._draw_tamed_companion_flavor(left_rect, y)
            right_y = self.parent_screen._draw_panel(right_rect, "Bond & Form")
            self._draw_tamed_companion_bond_panel(right_rect, right_y)
        elif self.kind == "Familiar":
            self._draw_familiar_details(left_rect, right_rect, y)
        else:
            self.parent_screen._draw_divider(left_rect, y - 8)
            self.parent_screen._draw_text(
                "Core Attributes",
                self.large_font,
                self.colors.GOLD,
                left_rect.left + 16,
                y,
                left_rect.width - 32,
            )
            y += self.large_font.get_height() + 8
            self.parent_screen._draw_key_values(
                self._core_attribute_rows(),
                left_rect,
                y,
                font=self.small_font,
                label_padding=36,
                right_align_values=True,
                row_gap=2,
                bottom_limit=left_rect.bottom - 16,
            )

            y = self.parent_screen._draw_panel(right_rect, "Combat Stats")
            resistance_height = min(
                190,
                self.large_font.get_height() + 8 + (6 * (self.small_font.get_height() + 2)),
            )
            resistance_top = right_rect.bottom - resistance_height - 16
            y = self.parent_screen._draw_key_values(
                self._combat_rows(),
                right_rect,
                y,
                font=self.small_font,
                row_gap=2,
                right_align_values=True,
                bottom_limit=resistance_top - 14,
            )
            y = self._draw_abilities(right_rect, y + 18, resistance_top - 14)
            groups = self.parent_screen.group_resistances(self.companion)
            y = max(y + 12, resistance_top)
            self.parent_screen._draw_divider(right_rect, y - 10)
            column_gap = 12
            column_width = (right_rect.width - 32 - column_gap) // 2
            weakness_rect = pygame.Rect(
                right_rect.left + 16, y, column_width, right_rect.bottom - y - 16
            )
            resistance_rect = pygame.Rect(
                weakness_rect.right + column_gap, y, column_width, weakness_rect.height
            )
            self.parent_screen._draw_text(
                "Weaknesses",
                self.large_font,
                self.colors.RED,
                weakness_rect.left,
                y,
                weakness_rect.width,
            )
            self.parent_screen._draw_text(
                "Resistances",
                self.large_font,
                self.colors.GREEN,
                resistance_rect.left,
                y,
                resistance_rect.width,
            )
            group_y = y + self.large_font.get_height() + 6
            self.parent_screen._draw_resistance_group(
                groups["weaknesses"],
                weakness_rect,
                group_y,
                self.colors.RED,
                font=self.small_font,
                row_gap=2,
            )
            self.parent_screen._draw_resistance_group(
                groups["resistances"],
                resistance_rect,
                group_y,
                self.colors.GREEN,
                font=self.small_font,
                row_gap=2,
            )

        footer = "Esc/Enter: Close"
        footer_text = self.small_font.render(footer, True, self.colors.GRAY)
        self.screen.blit(
            footer_text,
            (self.popup_rect.left + 16, self.popup_rect.bottom - footer_text.get_height() - 12),
        )
        pygame.display.flip()

    def show(
        self,
        background_draw_func=None,
        flush_events: bool = False,
        require_key_release: bool = False,
    ) -> None:
        if background_draw_func is None:
            background = self.screen.copy()

            def background_draw_func():
                return self.screen.blit(background, (0, 0))

        background_draw_func()
        background_surface = self.screen.copy()
        input_armed = prepare_guarded_input(
            flush_events=flush_events, require_key_release=require_key_release
        )

        while True:
            self.draw(background_surface)
            input_armed = release_guard_allows_input(require_key_release, input_armed)
            for event in get_events():
                if event.type == pygame.QUIT:
                    pygame.quit()
                    import sys

                    sys.exit()
                input_armed = update_input_armed_from_event(event, require_key_release, input_armed)
                if popup_close_clicked(event, self.popup_rect):
                    if input_armed:
                        background_draw_func()
                        return
                    continue
                if event.type != pygame.KEYDOWN or not input_armed:
                    continue
                if event.key in (pygame.K_ESCAPE, pygame.K_RETURN, pygame.K_SPACE):
                    background_draw_func()
                    return
            self.presenter.clock.tick(30)
