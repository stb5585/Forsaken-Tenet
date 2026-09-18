"""Core behavior for the combat view package."""

from __future__ import annotations

import math

import pygame

from src.core.classes import promotion_kits
from src.ui_pygame.assets.enemy_combat_sprite_manager import get_enemy_combat_sprite_manager
from src.ui_pygame.assets.enemy_token_manager import get_enemy_token_manager
from src.ui_pygame.assets.player_token_manager import get_player_token_manager

from ..enemy_presentation import (
    present_status_log_line,
    redact_hidden_enemy_identities,
)
from ..status_icons import STATUS_ICON_COLORS
from .animator import SpriteAnimator
from .models import CombatImpactEffect, CombatLogLine, FloatingCombatText


class CombatViewCoreMixin:
    def __init__(self, screen, presenter):
        self.screen = screen
        self.presenter = presenter
        self.screen_width = 0
        self.screen_height = 0
        self.combat_width = 0
        self.combat_height = 0
        self.refresh_layout()

        # Colors
        self.colors = {
            "background": (20, 20, 25),
            "enemy": (200, 50, 50),
            "player": (50, 150, 250),
            "hp_bar": (200, 50, 50),
            "mp_bar": (50, 100, 200),
            "text": (255, 255, 255),
            "action_bg": (40, 40, 45),
            "action_selected": (80, 80, 90),
            "action_border": (118, 116, 126),
            "panel_accent": (166, 132, 74),
            "message_bg": (30, 30, 35),
            "turn_player": (70, 130, 210),
            "turn_enemy": (180, 80, 70),
            "turn_enemy_alt": (205, 145, 65),
            "telegraph": (255, 205, 110),
            "log_damage": (235, 120, 105),
            "log_heal": (120, 210, 135),
            "log_muted": (175, 175, 180),
            "log_player": (50, 150, 250),
            "log_enemy": (200, 50, 50),
            "log_summon": (85, 215, 190),
        }

        # Combat log
        self.combat_log = []
        self.max_log_lines = 200
        self.log_lines_per_page = 5
        self.log_scroll_offset = 0
        self._active_telegraph_line: str | None = None
        self._suppress_logged_telegraph_banner = False
        self._combat_log_player_name: str | None = None
        self._combat_log_enemy_name: str | None = None
        self._combat_log_summon_name: str | None = None
        self._combat_log_enemy = None
        self._combat_log_revision = 0
        self._combat_log_wrap_cache: dict[tuple[int, int, bool, int], list[CombatLogLine]] = {}

        # Status icon colors
        self.status_colors = STATUS_ICON_COLORS

        # Sprite animators (per enemy instance)
        self.sprite_animators = {}  # Key by enemy id()
        self.enemy_visual_offset = (0, 0)
        self._active_impact_effects: list[CombatImpactEffect] = []
        self._active_float_texts: list[FloatingCombatText] = []
        self._transient_smoke_visuals: dict[str, int] = {}
        self._enemy_recoil_until_ms = 0
        self._last_enemy_target_rect = pygame.Rect(
            self.combat_width // 2 - 120,
            self.combat_height // 3 - 120,
            240,
            240,
        )
        self._enemy_target_rects: dict[str, pygame.Rect] = {}
        self._enemy_card_rects: dict[str, pygame.Rect] = {}
        self._enemy_focus_control_rects: dict[int, pygame.Rect] = {}
        self._last_player_target_rect = pygame.Rect(
            28,
            self.screen_height - 270,
            220,
            110,
        )
        self._hide_enemy_for_flee = False
        self._hidden_enemy_names: set[str] = set()
        self.enemy_combat_sprite_manager = get_enemy_combat_sprite_manager()
        self.enemy_token_manager = get_enemy_token_manager()
        self.player_token_manager = get_player_token_manager()

    def refresh_layout(self) -> None:
        """Refresh native combat bounds after a display-resolution change."""
        self.screen = getattr(self.presenter, "screen", self.screen)
        get_size = getattr(self.screen, "get_size", None)
        if callable(get_size):
            self.screen_width, self.screen_height = get_size()
        else:
            self.screen_width = self.screen.get_width()
            self.screen_height = self.screen.get_height()
        metrics = getattr(self.presenter, "layout_metrics", None)
        view_fraction = metrics.dungeon_view_fraction if metrics is not None else 0.65
        self.dungeon_view_width = int(self.screen_width * view_fraction)
        self.combat_width = (
            self.dungeon_view_width if metrics is not None else int(self.screen_width * 2 / 3)
        )
        self.combat_height = self.screen_height

    def native_unit(self, reference_pixels: int, minimum: int = 1) -> int:
        """Convert a reference combat dimension to the active native size."""
        metrics = getattr(self.presenter, "layout_metrics", None)
        if metrics is None:
            return max(minimum, reference_pixels)
        return metrics.unit(reference_pixels, minimum=minimum)

    def _get_sprite_animator(self, enemy):
        """Get or create animator for this enemy instance."""
        enemy_id = id(enemy)
        if enemy_id not in self.sprite_animators:
            self.sprite_animators[enemy_id] = SpriteAnimator()
        return self.sprite_animators[enemy_id]

    def update_animations(self):
        """Update all active sprite animations."""
        for animator in self.sprite_animators.values():
            animator.update()
        self._prune_impact_effects()
        self._prune_float_texts()

    def enemy_take_damage(self, enemy):
        """Trigger damage flash when enemy takes damage."""
        animator = self._get_sprite_animator(enemy)
        animator.trigger_damage()
        self._enemy_recoil_until_ms = max(
            self._enemy_recoil_until_ms, pygame.time.get_ticks() + 220
        )

    def enemy_card_at(self, position) -> str | None:
        """Return the living-card combatant ID under a mouse position."""
        for combatant_id, rect in self._enemy_card_rects.items():
            if rect.collidepoint(position):
                return combatant_id
        return None

    def enemy_focus_control_at(self, position) -> int | None:
        """Return target-cycle direction for a visible focus control."""
        for direction, rect in self._enemy_focus_control_rects.items():
            if rect.collidepoint(position):
                return direction
        return None

    def trigger_impact_effect(
        self,
        target: str,
        kind: str = "weapon",
        element: str | None = None,
        critical: bool = False,
    ) -> None:
        """Start a short hit/spell effect at the last known target location."""
        self._active_impact_effects.append(
            CombatImpactEffect(
                target=target,
                kind=kind,
                color=self._impact_color(kind, element),
                start_ms=pygame.time.get_ticks(),
                duration_ms=520 if critical else 420,
                critical=critical,
            )
        )

    def trigger_floating_text(
        self,
        target: str,
        text: str,
        color: tuple[int, int, int] | None = None,
    ) -> None:
        """Start a brief floating combat result label."""
        if not text:
            return
        now = pygame.time.get_ticks()
        stack_index = sum(
            1
            for active in self._active_float_texts
            if active.target == target and now - active.start_ms < 100
        )
        self._active_float_texts.append(
            FloatingCombatText(
                target=target,
                text=str(text),
                color=color or self.colors["text"],
                start_ms=now,
                stack_index=stack_index,
            )
        )

    def trigger_smoke_screen_visual(self, target: str, duration_ms: int = 900) -> None:
        """Show the smoke cloud briefly for instant Smoke Screen escapes."""
        if target not in {"enemy", "player"}:
            return
        self._transient_smoke_visuals[target] = pygame.time.get_ticks() + max(1, int(duration_ms))

    def hide_enemy_for_flee(self) -> None:
        """Keep the enemy hidden after a smoke-screen escape until combat cleanup."""
        self._hide_enemy_for_flee = True

    def _transient_smoke_active(self, target: str) -> bool:
        until_ms = self._transient_smoke_visuals.get(target, 0)
        if until_ms <= 0:
            return False
        if pygame.time.get_ticks() <= until_ms:
            return True
        self._transient_smoke_visuals.pop(target, None)
        return False

    def enemy_dies(self, enemy):
        """Trigger death animation when enemy dies."""
        animator = self._get_sprite_animator(enemy)
        animator.trigger_death()

    def death_animation_in_progress(self) -> bool:
        """Return whether a defeated combatant is still visibly fading."""
        return any(
            animator.animation_type == "death" and not animator.is_dead
            for animator in self.sprite_animators.values()
        )

    def set_hidden_enemy_identities(self, enemy_names) -> None:
        """Set canonical enemy names that current combat text must conceal."""
        self._hidden_enemy_names = {str(name) for name in enemy_names if str(name)}

    def add_combat_message(self, message):
        """Add a message to the combat log."""
        presented_message = redact_hidden_enemy_identities(
            str(message),
            self._hidden_enemy_names,
        )
        cleaned_lines = self._filter_status_message(presented_message)
        if not cleaned_lines:
            return
        has_telegraph_line = any(self._is_telegraph_message(line) for line in cleaned_lines)
        if not has_telegraph_line:
            self._active_telegraph_line = None
            self._suppress_logged_telegraph_banner = True
        was_at_bottom = self.log_scroll_offset >= self._max_log_scroll()
        for line in cleaned_lines:
            if self._is_telegraph_message(line):
                line = self._short_telegraph_message(line)
                self._active_telegraph_line = line
                self._suppress_logged_telegraph_banner = False
            line = present_status_log_line(line, self._combat_log_enemy)
            self.combat_log.append(line)
        while len(self.combat_log) > self.max_log_lines:
            self.combat_log.pop(0)
        self._invalidate_combat_log_wrap_cache()
        if was_at_bottom:
            self.log_scroll_offset = self._max_log_scroll()
        else:
            self.log_scroll_offset = min(self.log_scroll_offset, self._max_log_scroll())

    def _max_log_scroll(self):
        display_lines = self._wrapped_combat_log_lines(self.combat_width - 30)
        return max(0, len(display_lines) - self.log_lines_per_page)

    def scroll_log(self, delta: int):
        """Scroll combat log by delta lines (negative=older, positive=newer)."""
        self.log_scroll_offset = max(0, min(self._max_log_scroll(), self.log_scroll_offset + delta))

    def reset_combat_log(self):
        """Clear combat log history and transient presentation state."""
        self.combat_log.clear()
        self.log_scroll_offset = 0
        self._active_telegraph_line = None
        self._suppress_logged_telegraph_banner = False
        self._hide_enemy_for_flee = False
        self._hidden_enemy_names.clear()
        self.sprite_animators.clear()
        self._active_impact_effects.clear()
        self._active_float_texts.clear()
        self._transient_smoke_visuals.clear()
        self._enemy_recoil_until_ms = 0
        self._enemy_target_rects.clear()
        self._enemy_card_rects.clear()
        self._invalidate_combat_log_wrap_cache()

    def _prune_impact_effects(self) -> None:
        if not self._active_impact_effects:
            return
        now = pygame.time.get_ticks()
        self._active_impact_effects = [
            effect
            for effect in self._active_impact_effects
            if now - effect.start_ms < effect.duration_ms
        ]

    def _prune_float_texts(self) -> None:
        if not self._active_float_texts:
            return
        now = pygame.time.get_ticks()
        self._active_float_texts = [
            text for text in self._active_float_texts if now - text.start_ms < text.duration_ms
        ]

    def _enemy_recoil_offset(self) -> int:
        remaining = max(0, self._enemy_recoil_until_ms - pygame.time.get_ticks())
        if remaining <= 0:
            return 0
        phase = remaining / 220
        return int(math.sin(phase * math.pi * 5) * 8 * phase)

    @staticmethod
    def _impact_color(kind: str, element: str | None = None) -> tuple[int, int, int]:
        element_colors = {
            "Fire": (226, 92, 42),
            "Ice": (150, 206, 230),
            "Electric": (236, 210, 88),
            "Water": (82, 150, 192),
            "Earth": (150, 112, 70),
            "Wind": (178, 205, 182),
            "Poison": (118, 168, 86),
            "Holy": (232, 218, 162),
            "Dark": (142, 104, 174),
            "Death": (156, 144, 128),
        }
        if element in element_colors:
            return element_colors[element]
        if kind == "spell":
            return (178, 142, 222)
        if kind == "skill":
            return (210, 148, 82)
        return (218, 185, 128)

    def _target_rect_for_effect(self, target: str) -> pygame.Rect:
        if target == "player":
            return self._last_player_target_rect.copy()
        if target in self._enemy_target_rects:
            return self._enemy_target_rects[target].copy()
        return self._last_enemy_target_rect.copy()

    def _render_active_impact_effects(self) -> None:
        if not self._active_impact_effects:
            return
        now = pygame.time.get_ticks()
        for effect in list(self._active_impact_effects):
            progress = (now - effect.start_ms) / max(1, effect.duration_ms)
            if progress >= 1:
                continue
            rect = self._target_rect_for_effect(effect.target)
            if effect.kind == "spell":
                self._draw_spell_impact(rect, effect, progress)
            elif effect.kind == "skill":
                self._draw_skill_impact(rect, effect, progress)
            elif effect.kind == "reflect":
                self._draw_reflect_impact(rect, effect, progress)
            elif effect.kind == "status":
                self._draw_status_impact(rect, effect, progress)
            elif effect.kind == "elemental_strike":
                self._draw_elemental_strike_impact(rect, effect, progress)
            else:
                self._draw_weapon_impact(rect, effect, progress)
        self._prune_impact_effects()

    def _render_floating_texts(self) -> None:
        if not self._active_float_texts:
            return
        now = pygame.time.get_ticks()
        font = pygame.font.Font(None, 28)
        for text in list(self._active_float_texts):
            progress = (now - text.start_ms) / max(1, text.duration_ms)
            if progress >= 1:
                continue
            alpha = int(230 * (1.0 - progress))
            if alpha <= 0:
                continue
            rect = self._target_rect_for_effect(text.target)
            surf = font.render(text.text, True, text.color)
            surf.set_alpha(alpha)
            shadow = font.render(text.text, True, (0, 0, 0))
            shadow.set_alpha(max(0, alpha - 50))
            y_offset = int(34 * progress)
            stack_y = text.stack_index * 24
            text_rect = surf.get_rect(center=(rect.centerx, rect.top - 18 - y_offset - stack_y))
            shadow_rect = shadow.get_rect(center=(text_rect.centerx + 2, text_rect.centery + 2))
            self.screen.blit(shadow, shadow_rect)
            self.screen.blit(surf, text_rect)
        self._prune_float_texts()

    def _draw_weapon_impact(
        self, rect: pygame.Rect, effect: CombatImpactEffect, progress: float
    ) -> None:
        alpha = int(190 * (1.0 - progress))
        if alpha <= 0:
            return
        overlay = pygame.Surface(rect.inflate(80, 80).size, pygame.SRCALPHA)
        color = (*effect.color, alpha)
        width = 5 if effect.critical else 3
        slash_shift = int(progress * 42)
        pygame.draw.line(
            overlay,
            color,
            (overlay.get_width() // 2 - 54 + slash_shift, overlay.get_height() // 2 - 36),
            (overlay.get_width() // 2 + 54 + slash_shift, overlay.get_height() // 2 + 24),
            width,
        )
        pygame.draw.line(
            overlay,
            (*effect.color, max(40, alpha // 2)),
            (overlay.get_width() // 2 - 36, overlay.get_height() // 2 + 28),
            (overlay.get_width() // 2 + 38, overlay.get_height() // 2 - 28),
            2,
        )
        for index in range(5):
            spark_alpha = max(0, alpha - index * 18)
            spark_x = overlay.get_width() // 2 + index * 14 - 30
            spark_y = overlay.get_height() // 2 - int(progress * 36) + ((index % 2) * 14)
            pygame.draw.circle(
                overlay, (*effect.color, spark_alpha), (spark_x, spark_y), max(2, 5 - index // 2)
            )
        self.screen.blit(overlay, overlay.get_rect(center=rect.center))

    def _draw_skill_impact(
        self, rect: pygame.Rect, effect: CombatImpactEffect, progress: float
    ) -> None:
        alpha = int(150 * (1.0 - progress))
        if alpha <= 0:
            return
        overlay = pygame.Surface(rect.inflate(100, 70).size, pygame.SRCALPHA)
        center = (overlay.get_width() // 2, overlay.get_height() // 2)
        radius = int(22 + progress * 48)
        pygame.draw.circle(overlay, (*effect.color, max(25, alpha // 2)), center, radius, 2)
        for angle in (0, math.pi / 3, math.pi * 2 / 3):
            dx = int(math.cos(angle) * (radius + 12))
            dy = int(math.sin(angle) * (radius // 2))
            pygame.draw.line(
                overlay,
                (*effect.color, alpha),
                (center[0] - dx, center[1] - dy),
                (center[0] + dx, center[1] + dy),
                2,
            )
        self.screen.blit(overlay, overlay.get_rect(center=rect.center))

    def _draw_spell_impact(
        self, rect: pygame.Rect, effect: CombatImpactEffect, progress: float
    ) -> None:
        alpha = int(170 * (1.0 - progress))
        if alpha <= 0:
            return
        overlay = pygame.Surface(rect.inflate(120, 120).size, pygame.SRCALPHA)
        center = (overlay.get_width() // 2, overlay.get_height() // 2)
        glow_radius = int(28 + progress * 62)
        pygame.draw.circle(overlay, (*effect.color, max(24, alpha // 3)), center, glow_radius)
        pygame.draw.circle(overlay, (*effect.color, alpha), center, max(8, glow_radius // 3), 2)
        for index in range(8):
            angle = (math.pi * 2 * index / 8) + progress * 1.4
            inner = glow_radius // 3
            outer = glow_radius
            start = (
                center[0] + int(math.cos(angle) * inner),
                center[1] + int(math.sin(angle) * inner),
            )
            end = (
                center[0] + int(math.cos(angle) * outer),
                center[1] + int(math.sin(angle) * outer),
            )
            pygame.draw.line(overlay, (*effect.color, max(35, alpha // 2)), start, end, 2)
        self.screen.blit(overlay, overlay.get_rect(center=rect.center))

    def _draw_reflect_impact(
        self, rect: pygame.Rect, effect: CombatImpactEffect, progress: float
    ) -> None:
        alpha = int(180 * (1.0 - progress))
        if alpha <= 0:
            return
        overlay = pygame.Surface(rect.inflate(130, 110).size, pygame.SRCALPHA)
        center = (overlay.get_width() // 2, overlay.get_height() // 2)
        radius_x = int(34 + progress * 48)
        radius_y = int(22 + progress * 32)
        for index in range(3):
            ring_rect = pygame.Rect(0, 0, radius_x * 2 + index * 18, radius_y * 2 + index * 12)
            ring_rect.center = center
            pygame.draw.ellipse(overlay, (*effect.color, max(35, alpha - index * 42)), ring_rect, 2)
        for angle in (-0.65, 0.0, 0.65):
            start = (
                center[0] - int(math.cos(angle) * (radius_x + 18)),
                center[1] - int(math.sin(angle) * (radius_y + 10)),
            )
            end = (
                center[0] + int(math.cos(angle) * (radius_x + 18)),
                center[1] + int(math.sin(angle) * (radius_y + 10)),
            )
            pygame.draw.line(overlay, (*effect.color, max(50, alpha // 2)), start, end, 2)
        self.screen.blit(overlay, overlay.get_rect(center=rect.center))

    def _draw_status_impact(
        self, rect: pygame.Rect, effect: CombatImpactEffect, progress: float
    ) -> None:
        alpha = int(175 * (1.0 - progress))
        if alpha <= 0:
            return
        overlay = pygame.Surface(rect.inflate(100, 90).size, pygame.SRCALPHA)
        center = (overlay.get_width() // 2, overlay.get_height() // 2)
        radius = int(16 + progress * 34)
        pygame.draw.circle(overlay, (*effect.color, max(40, alpha // 2)), center, radius, 2)
        for index in range(6):
            angle = math.pi * 2 * index / 6
            marker_center = (
                center[0] + int(math.cos(angle) * (radius + 18)),
                center[1] + int(math.sin(angle) * (radius + 8)),
            )
            pygame.draw.circle(
                overlay, (*effect.color, max(35, alpha - index * 10)), marker_center, 4
            )
        self.screen.blit(overlay, overlay.get_rect(center=rect.center))

    def _draw_elemental_strike_impact(
        self, rect: pygame.Rect, effect: CombatImpactEffect, progress: float
    ) -> None:
        self._draw_weapon_impact(rect, effect, progress)
        alpha = int(120 * (1.0 - progress))
        if alpha <= 0:
            return
        overlay = pygame.Surface(rect.inflate(100, 100).size, pygame.SRCALPHA)
        center = (overlay.get_width() // 2, overlay.get_height() // 2)
        radius = int(24 + progress * 58)
        pygame.draw.circle(overlay, (*effect.color, max(25, alpha // 2)), center, radius, 2)
        for index in range(5):
            angle = progress * math.pi * 2 + index * math.pi * 2 / 5
            start = (
                center[0] + int(math.cos(angle) * max(6, radius // 3)),
                center[1] + int(math.sin(angle) * max(6, radius // 3)),
            )
            end = (
                center[0] + int(math.cos(angle) * radius),
                center[1] + int(math.sin(angle) * radius),
            )
            pygame.draw.line(overlay, (*effect.color, max(35, alpha // 2)), start, end, 2)
        self.screen.blit(overlay, overlay.get_rect(center=rect.center))

    def _filter_status_message(self, message):
        """Remove status-effect log lines to keep the log focused on actions."""
        kept_lines = []
        suppress_terms = (
            "fails to",
            "resists the spell",
            "is immune to",
        )
        suppress_already = (
            "stunned",
            "asleep",
            "prone",
            "blind",
            "disarmed",
            "silenced",
        )
        for line in message.split("\n"):
            line_lower = line.lower()
            keep_class_kit_line = any(
                term in line_lower for term in promotion_kits.CLASS_KIT_LOG_TERMS
            )
            if "is affected by" in line_lower:
                continue
            if not keep_class_kit_line and any(term in line_lower for term in suppress_terms):
                continue
            if (
                not keep_class_kit_line
                and "already" in line_lower
                and any(term in line_lower for term in suppress_already)
            ):
                continue
            if line.strip():
                kept_lines.append(line.strip())
        return kept_lines

    def _wrap_log_line(
        self,
        line: str,
        max_width: int | None = None,
        font: pygame.font.Font | None = None,
    ) -> list[str]:
        """Wrap a combat log line to the combat pane width."""
        if not line:
            return []

        max_width = max(160, max_width if max_width is not None else self.combat_width - 30)
        measure_font = font or pygame.font.Font(None, 20)
        wrapped: list[str] = []
        for paragraph in line.split("\n"):
            stripped = paragraph.strip()
            if not stripped:
                continue

            current = ""
            for word in stripped.split():
                candidate = f"{current} {word}".strip() if current else word
                if measure_font.size(candidate)[0] <= max_width:
                    current = candidate
                    continue

                if current:
                    wrapped.append(current)
                    current = ""

                if measure_font.size(word)[0] <= max_width:
                    current = word
                    continue

                chunk = ""
                for char in word:
                    chunk_candidate = f"{chunk}{char}"
                    if chunk and measure_font.size(chunk_candidate)[0] > max_width:
                        wrapped.append(chunk)
                        chunk = char
                    else:
                        chunk = chunk_candidate
                current = chunk

            if current:
                wrapped.append(current)
        return wrapped

    def _wrapped_combat_log_lines(
        self,
        max_width: int,
        font: pygame.font.Font | None = None,
    ) -> list[str]:
        """Return combat log history flattened into render-ready wrapped lines."""
        return [
            line.text for line in self._wrapped_combat_log_entries(max_width=max_width, font=font)
        ]

    def _wrapped_combat_log_entries(
        self,
        max_width: int,
        font: pygame.font.Font | None = None,
        overlay: bool = False,
    ) -> list[CombatLogLine]:
        """Return combat log history flattened with source-message styling intact."""
        cache_key = (
            self._combat_log_revision,
            max(160, max_width - 12),
            overlay,
            self._combat_log_font_cache_key(font),
        )
        cached = self._combat_log_wrap_cache.get(cache_key)
        if cached is not None:
            return cached

        entries: list[CombatLogLine] = []
        wrap_width = cache_key[1]
        for message in self.combat_log:
            color = self._combat_log_color(message, overlay=overlay)
            marker_color = self._combat_log_marker_color(message, overlay=overlay)
            wrapped_lines = self._wrap_log_line(message, max_width=wrap_width, font=font)
            for index, wrapped_line in enumerate(wrapped_lines):
                entries.append(
                    CombatLogLine(
                        text=wrapped_line,
                        color=color,
                        marker_color=marker_color,
                        continuation=index > 0,
                    )
                )
        self._combat_log_wrap_cache[cache_key] = entries
        return entries

    def _invalidate_combat_log_wrap_cache(self) -> None:
        self._combat_log_revision += 1
        self._combat_log_wrap_cache.clear()
