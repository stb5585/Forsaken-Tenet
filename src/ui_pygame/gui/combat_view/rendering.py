"""Rendering behavior for the combat view package."""

from __future__ import annotations

import math
import sys

import pygame

from src.core.classes import astromancer
from src.ui_pygame.screen_runtime import get_events

from ..enemy_presentation import (
    invisible_target_note,
    presented_enemy_name,
)


class CombatRenderingMixin:
    def _render_enemy(self, enemy, has_sight=True):
        """Render the enemy sprite/representation with animations."""
        if self._hide_enemy_for_flee:
            return

        visual_offset_x, visual_offset_y = self.enemy_visual_offset
        center_x = self.combat_width // 2 + visual_offset_x + self._enemy_recoil_offset()
        polymorphed = self._enemy_is_polymorphed(enemy)
        boss_enemy = self._is_boss_enemy(enemy) and not polymorphed
        center_y = (
            int(self.combat_height * 0.42) if boss_enemy else self.combat_height // 3
        ) + visual_offset_y

        is_flying = getattr(enemy, "flying", False)
        is_tunneled = getattr(enemy, "tunnel", False)
        if is_flying:
            center_y -= min(48, max(24, int(self.combat_height * 0.05)))

        # If enemy is tunneled, show a "burrowed" message instead of sprite
        if is_tunneled:
            font = pygame.font.Font(None, 40)
            text_surf = font.render(f"{enemy.name} is underground", True, (150, 100, 50))
            text_rect = text_surf.get_rect(center=(center_x, center_y))
            self.screen.blit(text_surf, text_rect)

            # Show HP bar if visible
            if has_sight:
                bar_width = 200
                bar_height = 20
                bar_x = center_x - bar_width // 2
                bar_y = center_y + 60

                # Background
                pygame.draw.rect(self.screen, (50, 50, 50), (bar_x, bar_y, bar_width, bar_height))
                # HP fill
                hp_pct = max(0, enemy.health.current / enemy.health.max) if enemy.health.max else 0
                filled_width = int(bar_width * hp_pct)
                pygame.draw.rect(self.screen, (0, 200, 0), (bar_x, bar_y, filled_width, bar_height))
                # Border
                pygame.draw.rect(
                    self.screen, (255, 255, 255), (bar_x, bar_y, bar_width, bar_height), 2
                )
            return

        # Get animator for this enemy
        animator = self._get_sprite_animator(enemy)

        sprite_size = self._enemy_combat_sprite_size(enemy)
        display_sprite = self._enemy_sprite_surface(enemy, sprite_size, has_sight=has_sight)
        enemy_size = sprite_size[1] // 2

        if display_sprite is not None:
            # Apply damage flash tint
            if animator.damage_flash > 0:
                display_sprite = animator.apply_tint(
                    display_sprite, (255, 100, 100), animator.damage_flash
                )

            # Apply death animation (scale down and fade)
            if animator.animation_type == "death":
                # Scale from 1.0 to 0.3 as death progresses
                scale = 1.0 - (animator.death_progress * 0.7)
                death_size = (
                    max(1, int(display_sprite.get_width() * scale)),
                    max(1, int(display_sprite.get_height() * scale)),
                )
                display_sprite = pygame.transform.scale(display_sprite, death_size)

                # Fade out by modulating per-pixel alpha (preserves sprite shape)
                fade_alpha = int(255 * (1.0 - animator.death_progress))
                alpha_surf = pygame.Surface(display_sprite.get_size(), pygame.SRCALPHA)
                alpha_surf.fill((255, 255, 255, fade_alpha))
                display_sprite = display_sprite.copy()
                display_sprite.blit(alpha_surf, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)

            if animator.animation_type != "death":
                display_sprite = self._fade_sprite_for_smoke_screen(display_sprite, enemy, "enemy")

            # Calculate Y position with bob animation
            bob_y = center_y + animator.bob_offset if is_flying else center_y
            pace_offset = animator.confused_pace_offset() if polymorphed else 0
            bob_x = center_x if is_flying else center_x + animator.sway_offset + pace_offset

            if animator.animation_type != "death":
                self._draw_mirror_images(
                    display_sprite,
                    (int(bob_x), int(bob_y)),
                    self._active_duplicate_count(enemy),
                )

            sprite_rect = display_sprite.get_rect(center=(bob_x, bob_y))
            self._last_enemy_target_rect = sprite_rect.copy()
            self.screen.blit(display_sprite, sprite_rect)
        elif self._enemy_hidden_by_invisibility(enemy, has_sight):
            enemy_size = 0
            self._last_enemy_target_rect = pygame.Rect(center_x, center_y, 1, 1)
        else:
            # Fallback to simple representation
            enemy_size = 120
            fallback_x = center_x if is_flying else center_x + animator.sway_offset
            fallback_y = center_y + animator.bob_offset if is_flying else center_y
            pygame.draw.circle(
                self.screen, self.colors["enemy"], (int(fallback_x), int(fallback_y)), enemy_size
            )
            self._last_enemy_target_rect = pygame.Rect(
                int(fallback_x - enemy_size),
                int(fallback_y - enemy_size),
                enemy_size * 2,
                enemy_size * 2,
            )

            # Add eyes
            eye_offset = enemy_size // 3
            eye_size = enemy_size // 6
            pygame.draw.circle(
                self.screen,
                (255, 255, 255),
                (int(fallback_x - eye_offset), int(fallback_y - eye_offset)),
                eye_size,
            )
            pygame.draw.circle(
                self.screen,
                (255, 255, 255),
                (int(fallback_x + eye_offset), int(fallback_y - eye_offset)),
                eye_size,
            )
            pygame.draw.circle(
                self.screen,
                (0, 0, 0),
                (int(fallback_x - eye_offset), int(fallback_y - eye_offset)),
                eye_size // 2,
            )
            pygame.draw.circle(
                self.screen,
                (0, 0, 0),
                (int(fallback_x + eye_offset), int(fallback_y - eye_offset)),
                eye_size // 2,
            )

        self._render_ability_status_visuals(enemy, "enemy", include_duplicates=False)

        # Enemy identity is concealed while genuine invisibility defeats Sight.
        font = pygame.font.Font(None, 32)
        name_surf = font.render(
            presented_enemy_name(enemy, has_sight),
            True,
            self.colors["text"],
        )
        name_rect = name_surf.get_rect(center=(center_x, center_y - enemy_size - 30))
        self.screen.blit(name_surf, name_rect)

        # Enemy HP/MP bars (only visible with sight)
        if has_sight:
            bar_width = 200
            bar_height = 20
            bar_x = center_x - bar_width // 2
            bar_y = center_y + enemy_size + 20

            # Background
            pygame.draw.rect(
                self.screen, (100, 100, 100), pygame.Rect(bar_x, bar_y, bar_width, bar_height)
            )

            # HP fill
            hp_ratio = enemy.health.current / max(enemy.health.max, 1)
            hp_width = int(bar_width * hp_ratio)
            pygame.draw.rect(
                self.screen, self.colors["hp_bar"], pygame.Rect(bar_x, bar_y, hp_width, bar_height)
            )

            # HP text
            small_font = pygame.font.Font(None, 18)
            hp_text = f"HP {enemy.health.current}/{enemy.health.max}"
            hp_surf = small_font.render(hp_text, True, self.colors["text"])
            hp_rect = hp_surf.get_rect(center=(center_x, bar_y + bar_height // 2))
            self.screen.blit(hp_surf, hp_rect)

            enemy_mana = getattr(enemy, "mana", None)
            if enemy_mana is not None and getattr(enemy_mana, "max", 0) > 0:
                mp_y = bar_y + bar_height + 6
                pygame.draw.rect(
                    self.screen, (100, 100, 100), pygame.Rect(bar_x, mp_y, bar_width, bar_height)
                )
                mp_ratio = enemy_mana.current / max(enemy_mana.max, 1)
                mp_width = int(bar_width * mp_ratio)
                pygame.draw.rect(
                    self.screen,
                    self.colors["mp_bar"],
                    pygame.Rect(bar_x, mp_y, mp_width, bar_height),
                )
                mp_text = f"MP {enemy_mana.current}/{enemy_mana.max}"
                mp_surf = small_font.render(mp_text, True, self.colors["text"])
                mp_rect = mp_surf.get_rect(center=(center_x, mp_y + bar_height // 2))
                self.screen.blit(mp_surf, mp_rect)

        self._render_active_impact_effects()
        self._render_floating_texts()

    def _render_enemy_info_panel(self, enemy, has_sight=True, overlay=True):
        """Render combat artwork and target details without replacing gameplay sprites."""
        if self._hide_enemy_for_flee:
            return

        panel_x = int(self.screen_width * 0.65) + 12 if overlay else self.combat_width + 12
        panel_w = self.screen_width - panel_x - 12
        if panel_w < 170:
            return

        panel_y = 80 if overlay else 86
        panel_h = min(390, self.screen_height - panel_y - 170)
        if panel_h < 210:
            return

        panel_rect = pygame.Rect(panel_x, panel_y, panel_w, panel_h)
        panel = pygame.Surface(panel_rect.size, pygame.SRCALPHA)
        panel.fill((16, 16, 22, 232 if overlay else 255))
        self.screen.blit(panel, panel_rect.topleft)
        pygame.draw.rect(self.screen, (106, 82, 48), panel_rect, 2, border_radius=6)

        pad = 12
        title_font = pygame.font.Font(None, 26)
        body_font = pygame.font.Font(None, 18)

        hidden_by_invisibility = self._enemy_hidden_by_invisibility(
            enemy,
            has_sight,
        )
        name = self._truncate_text(
            title_font,
            presented_enemy_name(enemy, has_sight),
            panel_w - (pad * 2),
        )
        name_surf = title_font.render(name, True, self.colors["text"])
        self.screen.blit(name_surf, (panel_rect.left + pad, panel_rect.top + pad))

        note = invisible_target_note(enemy, has_sight)
        if note:
            note_text = self._truncate_text(body_font, note, panel_w - (pad * 2))
            note_surf = body_font.render(note_text, True, (210, 196, 150))
            self.screen.blit(note_surf, (panel_rect.left + pad, panel_rect.top + pad + 28))

        art_top = panel_rect.top + pad + (52 if note else 30)
        art_h = max(110, min(210, panel_h - 150))
        art_rect = pygame.Rect(panel_rect.left + pad, art_top, panel_w - (pad * 2), art_h)
        if has_sight:
            try:
                artwork = self.enemy_combat_sprite_manager.get_scaled_sprite(enemy, art_rect.size)
            except (
                Exception
            ) as exc:  # pragma: no cover - hard runtime fallback for broken external assets
                print(
                    f"Failed to render enemy combat sprite for {getattr(enemy, 'name', enemy)}: {exc}"
                )
                artwork = self.enemy_combat_sprite_manager.fallback_surface()
                artwork = pygame.transform.smoothscale(artwork, art_rect.size)
            self.screen.blit(artwork, art_rect.topleft)
            pygame.draw.rect(self.screen, (58, 48, 38), art_rect, 1)
        else:
            pygame.draw.rect(self.screen, (32, 32, 38), art_rect, 1)

        y = art_rect.bottom + 10
        if has_sight and hasattr(enemy, "health"):
            hp_text = f"HP {enemy.health.current} / {enemy.health.max}"
            hp_surf = body_font.render(hp_text, True, self.colors["hp_bar"])
            self.screen.blit(hp_surf, (panel_rect.left + pad, y))
            y += 22

        enemy_type = "" if hidden_by_invisibility else getattr(enemy, "enemy_typ", "")
        if enemy_type:
            type_surf = body_font.render(f"Type {enemy_type}", True, (205, 197, 176))
            self.screen.blit(type_surf, (panel_rect.left + pad, y))
            y += 22

        if has_sight:
            y = self._render_enemy_resistance_summary(enemy, panel_rect, y, body_font)

        icons = [] if hidden_by_invisibility else self._collect_status_icons(enemy)
        if icons and y + 20 < panel_rect.bottom:
            self._render_status_icons(
                icons, panel_rect.left + pad, y + 4, max_width=panel_w - (pad * 2), max_rows=2
            )

    def _render_enemy_resistance_summary(self, enemy, panel_rect, y, font):
        resistance = getattr(enemy, "resistance", {}) or {}
        if not resistance:
            return y

        weaknesses = []
        strengths = []
        for name, value in resistance.items():
            try:
                numeric = float(value)
            except (TypeError, ValueError):
                continue
            if numeric < 0:
                weaknesses.append(name)
            elif numeric > 0:
                strengths.append(name)

        max_width = panel_rect.width - 24
        for label, entries, color in (
            ("Weak", weaknesses, (230, 110, 100)),
            ("Resist", strengths, (126, 205, 132)),
        ):
            if not entries or y + 18 >= panel_rect.bottom:
                continue
            text = f"{label} {', '.join(entries[:4])}"
            if len(entries) > 4:
                text += f" +{len(entries) - 4}"
            text = self._truncate_text(font, text, max_width)
            surf = font.render(text, True, color)
            self.screen.blit(surf, (panel_rect.left + 12, y))
            y += 20
        return y

    def _render_player_status(self, player_char):
        """Render player HP/MP at bottom left."""
        x = 20
        y = self.combat_height - 120

        font = pygame.font.Font(None, 24)
        small_font = pygame.font.Font(None, 18)

        # HP
        hp_text = f"HP: {player_char.health.current}/{player_char.health.max}"
        hp_surf = font.render(hp_text, True, self.colors["hp_bar"])
        self.screen.blit(hp_surf, (x, y))

        # MP
        mp_text = f"MP: {player_char.mana.current}/{player_char.mana.max}"
        mp_surf = font.render(mp_text, True, self.colors["mp_bar"])
        self.screen.blit(mp_surf, (x, y + 30))

        if astromancer.has_rune_system(player_char):
            rune_y = y + 56
            if astromancer.is_astromancer(player_char):
                sign_text = f"Sign: {astromancer.active_constellation(player_char)}"
                sign_surf = small_font.render(
                    sign_text, True, self.colors.get("gold", (232, 196, 92))
                )
                self.screen.blit(sign_surf, (x, rune_y))
                rune_y += 16
            for line in astromancer.rune_grid_lines(player_char):
                rune_surf = small_font.render(line, True, self.colors.get("text", (230, 230, 230)))
                self.screen.blit(rune_surf, (x, rune_y))
                rune_y += 14

        # Status icons
        icons = self._collect_status_icons(player_char)
        if icons:
            icon_y = y + 60
            if astromancer.has_rune_system(player_char):
                icon_y += 66 if astromancer.is_astromancer(player_char) else 50
            self._render_status_icons(icons, x, icon_y, max_width=260)
        self._last_player_target_rect = pygame.Rect(x - 8, y - 10, 248, 104)
        self._render_ability_status_visuals(player_char, "player")

        # Encumbered warning
        if getattr(player_char, "encumbered", False):
            y += 60
            # Warning icon/text
            warning_text = "⚠ ENCUMBERED"
            warning_surf = font.render(warning_text, True, (255, 165, 0))  # Orange
            self.screen.blit(warning_surf, (x, y))

            # Penalties list
            penalty_lines = ["• Always lose initiative", "• -25% hit chance", "• -50% dodge chance"]
            y += 25
            for line in penalty_lines:
                penalty_surf = small_font.render(line, True, (255, 100, 100))  # Light red
                self.screen.blit(penalty_surf, (x + 5, y))
                y += 18

    @staticmethod
    def _action_grid_layout(
        width: int, menu_height: int, action_count: int
    ) -> tuple[int, int, int, int, int]:
        actions_per_row = 4 if action_count > 9 else 3
        row_count = max(1, math.ceil(max(1, action_count) / actions_per_row))
        start_y_offset = 46
        bottom_padding = 14
        available_height = max(24, menu_height - start_y_offset - bottom_padding)
        row_height = max(22, min(34, available_height // row_count))
        cell_width = max(92, (width - 54) // actions_per_row)
        return actions_per_row, row_count, start_y_offset, row_height, cell_width

    def _render_action_grid(
        self,
        actions,
        selected_action,
        *,
        rect: pygame.Rect,
        action_font: pygame.font.Font,
        text_color,
        highlight_color,
        border_color=None,
        translucent_highlight: bool = False,
    ) -> None:
        actions_per_row, _row_count, start_y_offset, row_height, cell_width = (
            self._action_grid_layout(
                rect.width,
                rect.height,
                len(actions),
            )
        )
        cell_padding = 10

        for i, action in enumerate(actions):
            row = i // actions_per_row
            col = i % actions_per_row
            x = rect.left + 28 + col * cell_width
            y = rect.top + start_y_offset + row * row_height
            highlight_rect = pygame.Rect(
                x - 5, y - 4, max(42, cell_width - 12), max(20, row_height - 3)
            )

            if i == selected_action:
                if translucent_highlight:
                    highlight_overlay = pygame.Surface(highlight_rect.size)
                    highlight_overlay.set_alpha(150)
                    highlight_overlay.fill(highlight_color)
                    self.screen.blit(highlight_overlay, highlight_rect.topleft)
                else:
                    pygame.draw.rect(self.screen, highlight_color, highlight_rect)
                selected_border = border_color or self.colors["panel_accent"]
                pygame.draw.rect(self.screen, selected_border, highlight_rect, 2)
                try:
                    pygame.draw.line(
                        self.screen,
                        (235, 215, 165),
                        (highlight_rect.left + 2, highlight_rect.top + 2),
                        (highlight_rect.right - 3, highlight_rect.top + 2),
                        1,
                    )
                except TypeError:
                    pass

            fitted_action = self._truncate_text(
                action_font, str(action), max(20, highlight_rect.width - cell_padding)
            )
            action_surf = action_font.render(fitted_action, True, text_color)
            self.screen.blit(action_surf, (x, y))

    def _render_action_menu(self, actions, selected_action):
        """Render the action selection menu."""
        menu_height = 150
        menu_y = self.combat_height - menu_height

        menu_rect = pygame.Rect(0, menu_y, self.combat_width, menu_height)
        self._draw_panel_surface(
            menu_rect,
            fill=(24, 24, 30),
            border=self.colors["action_border"],
            accent=self.colors["panel_accent"],
            border_width=2,
        )

        # Title
        font = pygame.font.Font(None, 28)
        title_surf = font.render("Choose Action:", True, (232, 224, 205))
        self.screen.blit(title_surf, (24, menu_y + 10))

        action_font = pygame.font.Font(None, 24)
        self._render_action_grid(
            actions,
            selected_action,
            rect=menu_rect,
            action_font=action_font,
            text_color=self.colors["text"],
            highlight_color=self.colors["action_selected"],
        )

    def _render_combat_log(self):
        """Render recent combat messages."""
        log_height = 120
        log_y = self.combat_height - 270  # Above action menu

        log_rect = pygame.Rect(0, log_y, self.combat_width, log_height)
        self._draw_panel_surface(
            log_rect,
            fill=self.colors["message_bg"],
            border=(76, 76, 84),
            accent=(105, 90, 58),
            border_width=1,
        )

        # Messages
        font = pygame.font.Font(None, 20)
        y = log_y + 10
        line_height = 22
        max_lines = self.log_lines_per_page
        lines_rendered = 0

        display_lines = self._wrapped_combat_log_entries(self.combat_width - 30, font=font)
        max_scroll = max(0, len(display_lines) - max_lines)
        self.log_scroll_offset = min(self.log_scroll_offset, max_scroll)

        for line in display_lines[self.log_scroll_offset : self.log_scroll_offset + max_lines]:
            if lines_rendered >= max_lines:
                break
            marker_color = (90, 90, 98) if line.continuation else line.marker_color
            pygame.draw.rect(self.screen, marker_color, pygame.Rect(11, y + 5, 4, 12))
            msg_surf = font.render(line.text, True, line.color)
            self.screen.blit(msg_surf, (31 if line.continuation else 20, y))
            y += line_height
            lines_rendered += 1

    def show_damage_flash(self, is_player_hit, event_handler=None):
        """Flash the screen to indicate damage."""
        base_surface = self.screen.copy()
        flash_color = (160, 28, 20) if is_player_hit else (176, 128, 62)

        # Brief pause while still pumping events to keep the window responsive.
        flash_clock = pygame.time.Clock()
        elapsed = 0
        duration_ms = 180
        while elapsed < duration_ms:
            for event in get_events():
                if event.type == pygame.QUIT:
                    pygame.quit()
                    sys.exit(0)
                if event_handler is not None:
                    event_handler(event)
            self.screen.blit(base_surface, (0, 0))
            flash_surface = pygame.Surface((self.combat_width, self.combat_height), pygame.SRCALPHA)
            flash_surface.fill((*flash_color, int(82 * (1.0 - elapsed / duration_ms))))
            self.screen.blit(flash_surface, (0, 0))
            self._render_active_impact_effects()
            pygame.display.flip()
            flash_clock.tick(60)
            elapsed += flash_clock.get_time()
