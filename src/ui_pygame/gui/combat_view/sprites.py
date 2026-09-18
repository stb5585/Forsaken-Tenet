"""Sprites behavior for the combat view package."""

from __future__ import annotations

import math

import pygame

from src.ui_pygame.assets.enemy_combat_sprite_manager import EnemyCombatSpriteManager

from ..enemy_presentation import is_invisible_target, player_has_sight


class CombatSpriteMixin:
    def prepare_enemy_assets(self, enemy) -> None:
        """Populate scaled enemy sprite caches before the first combat frame."""
        for size in (
            self._enemy_combat_sprite_size(enemy),
            self._enemy_dungeon_combat_sprite_size(enemy),
        ):
            self._enemy_sprite_surface(enemy, size, has_sight=True)

    def _has_sight(self, player_char):
        """Check if player has sight ability.

        Sight is granted by:
        - Inquisitor or Seeker class
        - Pendant of Vision equipped
        - Reveal spell effect (sets sight = True)
        """
        return player_has_sight(player_char)

    @staticmethod
    def _enemy_hidden_by_invisibility(enemy, has_sight: bool) -> bool:
        return not has_sight and is_invisible_target(enemy)

    def _enemy_details_visible(self, player_char, enemy, show_enemy_details=None) -> bool:
        """Return whether sight-based enemy details should be displayed."""
        if show_enemy_details is not None:
            return bool(show_enemy_details)
        if self._is_boss_enemy(enemy) or getattr(enemy, "name", "") == "Waitress":
            return False
        return self._has_sight(player_char)

    def _colorize_sprite(self, sprite, enemy):
        """Prepare sprite for rendering.

        Current combat sprites are authored as full-color PNG assets that
        preserve detail and outlines. This method skips blanket colorization,
        which would destroy that detail.

        Combat sprites now include:
        - Base color for the enemy type
        - Shadow colors for depth
        - Highlight colors for detail
        - Accent colors for clothing, equipment, and eyes

        No additional colorization is needed.
        """
        # Return sprite as-is - it's already colored from generation
        return sprite

    def _enemy_sprite_surface(self, enemy, size: tuple[int, int], has_sight: bool = True):
        """Return the enemy battlefield sprite scaled to a fixed combat box."""
        if not self._enemy_hidden_by_invisibility(enemy, has_sight):
            try:
                sprite_key = self.enemy_combat_sprite_manager.get_sprite_key_for_enemy(enemy)
                return self.enemy_combat_sprite_manager.get_scaled_sprite_by_key(sprite_key, size)
            except (
                Exception
            ) as exc:  # pragma: no cover - defensive fallback for asset loading failures
                print(
                    f"Failed to render enemy combat sprite for {getattr(enemy, 'name', enemy)}: {exc}"
                )
        return None

    def _is_boss_enemy(self, enemy) -> bool:
        """Return whether an enemy should use boss-scale combat presentation."""
        is_boss = getattr(self.enemy_combat_sprite_manager, "_is_boss", None)
        if callable(is_boss):
            return bool(is_boss(enemy))
        name = str(getattr(enemy, "name", enemy) or "")
        return bool(
            getattr(enemy, "boss", False)
            or getattr(enemy, "is_boss", False)
            or name in EnemyCombatSpriteManager.BOSS_NAMES
        )

    @staticmethod
    def _enemy_is_polymorphed(enemy) -> bool:
        """Return whether the enemy should use bunny scale and movement."""
        polymorph = getattr(enemy, "status_effects", {}).get("Polymorph")
        return bool(polymorph is not None and getattr(polymorph, "active", False))

    def _enemy_combat_sprite_size(self, enemy) -> tuple[int, int]:
        """Return the combat sprite box size after optional per-enemy scaling."""
        if self._is_boss_enemy(enemy) and not self._enemy_is_polymorphed(enemy):
            base_edge = max(256, int(min(self.combat_width, self.combat_height)))
        else:
            base_edge = 256
        edge = max(1, int(base_edge * self._enemy_combat_sprite_scale(enemy)))
        return (edge, edge)

    def _enemy_combat_sprite_scale(self, enemy) -> float:
        get_scale = getattr(self.enemy_combat_sprite_manager, "get_combat_scale_for_enemy", None)
        if not callable(get_scale):
            return 1.0
        try:
            return max(0.25, min(2.5, float(get_scale(enemy))))
        except (TypeError, ValueError):
            return 1.0

    def _enemy_dungeon_combat_sprite_size(self, enemy) -> tuple[int, int]:
        """Return the foreground combat sprite size for the dungeon-backed combat view."""
        metrics = getattr(self.presenter, "layout_metrics", None)
        base_edge = metrics.unit(320) if metrics is not None else 320
        edge = max(1, int(base_edge * self._enemy_combat_sprite_scale(enemy)))
        return (edge, edge)

    def _enemy_encounter_sprite_size(
        self,
        enemy,
        available_size: tuple[int, int],
    ) -> tuple[int, int]:
        """Use singleton combat scale, shrinking only genuinely oversized art."""
        desired_width, desired_height = self._enemy_dungeon_combat_sprite_size(
            enemy,
        )
        # A sprite may extend slightly beyond its lane because its transparent
        # square contains substantial padding. This preserves the singleton
        # scale for ordinary enemies while still containing unusually large
        # presentation scales.
        maximum_width = max(1, int(available_size[0] * 1.25))
        maximum_height = max(1, int(available_size[1]))
        fit = min(
            1.0,
            maximum_width / desired_width,
            maximum_height / desired_height,
        )
        return (
            max(1, int(desired_width * fit)),
            max(1, int(desired_height * fit)),
        )

    @staticmethod
    def _magic_effect_active(character, name: str) -> bool:
        try:
            effect = character.magic_effects.get(name)
            return bool(effect and effect.active)
        except AttributeError:
            return False

    def _active_duplicate_count(self, character) -> int:
        """Return visible Mirror Image duplicate count for a character."""
        try:
            effect = character.magic_effects.get("Duplicates")
            if not effect or not effect.active:
                return 0
            duration = int(effect.duration)
            if duration <= 0:
                effect.active = False
                effect.duration = 0
                return 0
            return max(0, min(4, duration))
        except (AttributeError, TypeError, ValueError):
            return 0

    def _draw_mirror_images(self, sprite, center: tuple[int, int], duplicate_count: int) -> None:
        """Draw overlapping translucent duplicates behind the real sprite."""
        if duplicate_count <= 0:
            return

        offsets = [(-18, -6), (18, 6), (-10, 12), (10, -12)]
        shimmer = (pygame.time.get_ticks() // 120) % 2
        for index in range(duplicate_count):
            offset_x, offset_y = offsets[index % len(offsets)]
            if shimmer and index % 2 == 0:
                offset_x = -offset_x
            ghost = sprite.copy()
            ghost.set_alpha(max(55, 118 - index * 14))
            ghost_rect = ghost.get_rect(center=(center[0] + offset_x, center[1] + offset_y))
            self.screen.blit(ghost, ghost_rect)

    def _render_mana_shield_visual(
        self,
        rect: pygame.Rect,
        *,
        encompass_view: bool = False,
    ) -> None:
        if encompass_view:
            margin = 10
            log_bottom = 160
            menu_top = self.combat_height - 150
            shield_rect = pygame.Rect(
                margin,
                log_bottom + margin,
                max(1, self.combat_width - (margin * 2)),
                max(1, menu_top - log_bottom - (margin * 2)),
            )
            surface = pygame.Surface(shield_rect.size, pygame.SRCALPHA)
            pulse = (math.sin(pygame.time.get_ticks() / 180) + 1) / 2
            alpha = int(95 + pulse * 70)
            surface.fill((35, 105, 190, 12))
            outer = surface.get_rect().inflate(-2, -2)
            inner = outer.inflate(-12, -12)
            pygame.draw.rect(
                surface,
                (80, 170, 255, alpha),
                outer,
                5,
                border_radius=18,
            )
            pygame.draw.rect(
                surface,
                (145, 215, 255, max(40, alpha // 2)),
                inner,
                2,
                border_radius=14,
            )
            self.screen.blit(surface, shield_rect.topleft)
            return

        padding = 30
        shield_rect = rect.inflate(padding, padding)
        surface = pygame.Surface(shield_rect.size, pygame.SRCALPHA)
        pulse = (math.sin(pygame.time.get_ticks() / 180) + 1) / 2
        alpha = int(70 + pulse * 65)
        pygame.draw.ellipse(surface, (80, 170, 255, alpha), surface.get_rect(), 4)
        inner = surface.get_rect().inflate(-14, -14)
        if inner.width > 0 and inner.height > 0:
            pygame.draw.ellipse(surface, (140, 210, 255, max(35, alpha // 2)), inner, 2)
        self.screen.blit(surface, shield_rect.topleft)

    def _render_smoke_screen_visual(self, rect: pygame.Rect) -> None:
        smoke_width = max(120, int(rect.width * 1.35))
        smoke_height = max(120, int(rect.height * 0.95))
        smoke_rect = pygame.Rect(0, 0, smoke_width, smoke_height)
        smoke_rect.midbottom = (rect.centerx, rect.bottom + 12)
        surface = pygame.Surface(smoke_rect.size, pygame.SRCALPHA)
        ticks = pygame.time.get_ticks()

        base_puffs = (
            (0.20, 0.86, 32, 22, 106),
            (0.36, 0.90, 42, 26, 124),
            (0.54, 0.84, 46, 30, 132),
            (0.72, 0.89, 36, 24, 112),
            (0.84, 0.82, 28, 20, 92),
        )
        for index, (x_pct, y_pct, width, height, alpha) in enumerate(base_puffs):
            drift = math.sin((ticks / 180) + index * 0.8) * 6
            puff_rect = pygame.Rect(0, 0, width * 2, height * 2)
            puff_rect.center = (
                int(smoke_rect.width * x_pct + drift),
                int(smoke_rect.height * y_pct),
            )
            pygame.draw.ellipse(surface, (128, 132, 140, alpha), puff_rect)
            pygame.draw.circle(
                surface,
                (178, 180, 188, max(60, alpha - 42)),
                puff_rect.center,
                max(14, min(width, height)),
            )

        for index in range(16):
            phase = ((ticks / 760) + index * 0.137) % 1.0
            y_pct = 0.92 - phase * 0.74
            spread = 0.10 + phase * 0.30
            sway = math.sin((ticks / 230) + index * 1.9) * smoke_rect.width * spread
            x_pct = 0.50 + math.sin(index * 2.35) * (0.10 + phase * 0.12)
            center_x = int(smoke_rect.width * x_pct + sway)
            center_y = int(smoke_rect.height * y_pct)
            radius_x = int(20 + phase * 42 + (index % 3) * 5)
            radius_y = int(16 + phase * 34 + (index % 2) * 4)
            alpha = int(118 - phase * 48)
            wisp_rect = pygame.Rect(0, 0, radius_x * 2, radius_y * 2)
            wisp_rect.center = (center_x, center_y)
            color_shift = int(phase * 28)
            pygame.draw.ellipse(
                surface,
                (148 + color_shift, 150 + color_shift, 160 + color_shift, alpha),
                wisp_rect,
            )

        self.screen.blit(surface, smoke_rect.topleft)

    def _smoke_screen_active_for(self, character, target: str) -> bool:
        return (
            self._transient_smoke_active(target)
            or self._magic_effect_active(character, "Smoke Screen")
            or self._magic_effect_active(character, "SmokeScreen")
        )

    def _fade_sprite_for_smoke_screen(self, sprite, character, target: str):
        if not self._smoke_screen_active_for(character, target):
            return sprite
        pulse = (math.sin(pygame.time.get_ticks() / 140) + 1) / 2
        faded = sprite.copy()
        faded.set_alpha(int(56 + pulse * 42))
        return faded

    def _render_ability_status_visuals(
        self, character, target: str, *, include_duplicates: bool = True
    ) -> None:
        rect = self._target_rect_for_effect(target)
        if self._magic_effect_active(character, "Mana Shield"):
            self._render_mana_shield_visual(
                rect,
                encompass_view=target == "player",
            )
        if self._smoke_screen_active_for(character, target):
            self._render_smoke_screen_visual(rect)

    def render_combat(
        self,
        player_char,
        enemy,
        actions,
        selected_action=0,
        current_turn=None,
        show_enemy_details=None,
        current_actor=None,
    ):
        """Render the complete combat view."""
        self._set_combat_log_actors(player_char, enemy)
        # Update animations
        self.update_animations()

        # Fill combat area background
        combat_rect = pygame.Rect(0, 0, self.combat_width, self.combat_height)
        self.screen.fill(self.colors["background"], combat_rect)

        # Check if player can see enemy details
        has_sight = self._enemy_details_visible(player_char, enemy, show_enemy_details)

        # Render enemy in center
        self._render_enemy(enemy, has_sight)
        self._render_enemy_info_panel(enemy, has_sight, overlay=False)

        # Render current turn indicator
        self._render_turn_indicator(
            player_char, enemy, current_turn=current_turn, current_actor=current_actor
        )
        self._render_telegraph_banner(enemy=enemy, overlay=False)

        # Render player status at bottom left
        self._render_player_status(player_char)

        # Render action menu at bottom
        self._render_action_menu(actions, selected_action)

        # Render combat log
        self._render_combat_log()
