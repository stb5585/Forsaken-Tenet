"""Shared selection validation and menu rendering for pygame combat."""

from __future__ import annotations

import pygame

from src.core.classes import (
    grandmaster,
    promotion_kits,
)


class SelectionSupportMixin:
    """Validate selectable skills and render shared selection menus."""

    def _skill_available_for_selection(self, player_char, skill, target=None) -> bool:
        """Return whether a learned skill should be shown in the combat skill list."""
        if getattr(skill, "passive", False):
            return False
        if not promotion_kits.combat_skill_visible(player_char, skill):
            return False

        is_resolve_skill = self._is_resolve_skill(skill)
        if (
            getattr(player_char, "anti_magic_active", False)
            and not is_resolve_skill
            and getattr(skill, "resource_type", None) != "Oath Conviction"
        ):
            return False
        silence = getattr(player_char, "status_effects", {}).get("Silence")
        if (
            getattr(silence, "active", False)
            and not is_resolve_skill
            and getattr(skill, "resource_type", None) != "Oath Conviction"
            and int(getattr(skill, "cost", 0) or 0) > 0
        ):
            return False

        if getattr(skill, "name", None) == "Shield Slam":
            offhand = getattr(player_char, "equipment", {}).get("OffHand")
            return getattr(offhand, "subtyp", None) == "Shield"

        if getattr(skill, "name", None) == "Mortal Strike":
            weapon = getattr(player_char, "equipment", {}).get("Weapon")
            if int(getattr(weapon, "handed", 0) or 0) != 2:
                return False

        if is_resolve_skill:
            offhand = getattr(player_char, "equipment", {}).get("OffHand")
            if getattr(offhand, "subtyp", None) != "Shield":
                return False

        class_name = getattr(getattr(player_char, "cls", None), "name", "")
        if (
            getattr(skill, "weapon", False)
            and player_char.is_disarmed()
            and "Monk" not in class_name
        ):
            return False

        availability = getattr(skill, "is_available", None)
        if callable(availability) and not availability(player_char, target):
            return False

        art_name = getattr(skill, "name", None)
        if art_name in grandmaster.ART_WEAPON_TYPES:
            return grandmaster.matching_weapon_for_art_equipped(player_char, art_name)

        if art_name in {entry["name"] for entry in promotion_kits.RESOLVE_SURGES}:
            return promotion_kits.resolve_surge_available(player_char, art_name)

        if getattr(skill, "_requires_incapacitated", False):
            incapacitated = getattr(target, "incapacitated", None)
            if target is None or not callable(incapacitated) or not incapacitated():
                return False

        return True

    def _render_selection_menu(self, title, options, selected, scroll_offset=0):
        """Render an in-combat selection panel without covering the enemy view."""
        view_width = int(self.screen.get_width() * 0.65)
        panel_width = max(420, view_width)
        panel_height = 176
        panel_x = 0
        panel_y = self.screen.get_height() - panel_height
        max_visible = 3

        max_scroll = max(0, len(options) - max_visible)
        scroll_offset = max(0, min(scroll_offset, max_scroll))
        start_idx = scroll_offset
        end_idx = min(len(options), scroll_offset + max_visible)

        panel = pygame.Surface((panel_width, panel_height))
        panel.set_alpha(228)
        panel.fill((20, 20, 25))
        self.screen.blit(panel, (panel_x, panel_y))
        pygame.draw.rect(
            self.screen,
            (124, 99, 62),
            pygame.Rect(panel_x, panel_y, panel_width, panel_height),
            3,
        )

        font_large = pygame.font.Font(None, 30)
        font_medium = pygame.font.Font(None, 24)
        font_small = pygame.font.Font(None, 18)
        title_surf = font_large.render(title, True, (232, 218, 186))
        self.screen.blit(title_surf, (panel_x + 20, panel_y + 12))
        back_rect = self._selection_menu_back_rect()
        pygame.draw.rect(self.screen, (72, 64, 48), back_rect)
        pygame.draw.rect(self.screen, (188, 150, 86), back_rect, 1)
        back_text = font_small.render("Back", True, (232, 218, 186))
        self.screen.blit(back_text, back_text.get_rect(center=back_rect.center))
        descriptions = getattr(self, "_selection_menu_descriptions", None)
        if descriptions and 0 <= selected < len(descriptions):
            title_width = (
                title_surf.get_width()
                if hasattr(title_surf, "get_width")
                else font_large.size(title)[0]
            )
            description = self._fit_text_to_width(
                font_small,
                str(descriptions[selected] or ""),
                max(80, panel_width - title_width - back_rect.width - 74),
            )
            if description:
                desc_surf = font_small.render(description, True, (188, 188, 176))
                self.screen.blit(desc_surf, (panel_x + title_width + 34, panel_y + 18))

        option_y = panel_y + 50
        option_rect_width = panel_width - 58

        for i in range(start_idx, end_idx):
            option = options[i]
            if i == selected:
                highlight_rect = pygame.Rect(panel_x + 18, option_y - 4, option_rect_width, 30)
                pygame.draw.rect(self.screen, (72, 64, 48), highlight_rect)
                pygame.draw.rect(self.screen, (188, 150, 86), highlight_rect, 1)

            prefix = f"{i + 1}. "
            option = self._fit_text_to_width(
                font_medium,
                option,
                option_rect_width - 18 - font_medium.size(prefix)[0],
            )

            color = (255, 255, 255) if i == selected else (220, 220, 220)
            option_surf = font_medium.render(f"{prefix}{option}", True, color)
            self.screen.blit(option_surf, (panel_x + 28, option_y))
            option_y += 34

        if len(options) > max_visible:
            track_rect = pygame.Rect(panel_x + panel_width - 22, panel_y + 50, 6, 102)
            pygame.draw.rect(self.screen, (58, 58, 66), track_rect)
            scrollbar_height = int(track_rect.height * max_visible / len(options))
            scrollbar_height = max(20, scrollbar_height)
            scrollbar_y = track_rect.y + int(
                (track_rect.height - scrollbar_height) * scroll_offset / max_scroll
            )
            pygame.draw.rect(
                self.screen,
                (170, 138, 82),
                pygame.Rect(track_rect.x, scrollbar_y, track_rect.width, scrollbar_height),
            )

        if len(options) > max_visible:
            instructions = "Wheel: Scroll | PgUp/PgDn: Scroll | Enter: Select | Esc: Cancel"
        else:
            instructions = "Click Back or Esc: Cancel | Enter/Space: Select"
        instr_surf = font_small.render(instructions, True, (176, 176, 176))
        self.screen.blit(instr_surf, (panel_x + 20, panel_y + panel_height - 24))
