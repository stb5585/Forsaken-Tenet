"""Overlay behavior for the combat view package."""

from __future__ import annotations

import pygame

from src.core.combat.actor_cycle import PLAYER_ACTOR_ID
from src.ui_pygame.assets.ability_icon_manager import get_ability_icon_manager
from src.ui_pygame.assets.companion_art_manager import get_companion_art_manager

from ..enemy_presentation import presented_enemy_name


class CombatOverlayMixin:
    def render_encounter_in_dungeon(
        self,
        player_char,
        encounter,
        *,
        focus_target_id: str,
        details_by_id: dict[str, bool],
    ) -> None:
        """Render two stable battlefield lanes with independently animated enemies."""
        if len(encounter.members) == 1:
            enemy = encounter.primary_enemy
            self._enemy_card_rects = {}
            self._enemy_target_rects = {}
            self._enemy_focus_control_rects = {}
            self.render_enemy_in_dungeon(
                player_char,
                enemy,
                show_enemy_details=details_by_id.get(
                    encounter.primary_member.combatant_id,
                    False,
                ),
            )
            return

        self.update_animations()
        view_width = self.dungeon_view_width
        gap = 12
        margin = 12
        top = 230
        bottom = self.screen_height - 158
        lane_height = max(250, bottom - top)
        lane_width = max(230, (view_width - (margin * 2) - gap) // 2)
        self._enemy_card_rects = {}
        self._enemy_target_rects = {}
        self._enemy_focus_control_rects = {}
        control_font = pygame.font.Font(None, 17)
        for direction, label, x in (
            (-1, "Previous Target  Q / LB", 12),
            (1, "Next Target  E / RB", 174),
        ):
            rect = pygame.Rect(x, 166, 150, 28)
            self._enemy_focus_control_rects[direction] = rect
            pygame.draw.rect(self.screen, (32, 30, 36), rect, border_radius=4)
            pygame.draw.rect(
                self.screen,
                self._hostile_lane_color(0 if direction < 0 else 1),
                rect,
                1,
                border_radius=4,
            )
            text = control_font.render(label, True, (230, 225, 210))
            self.screen.blit(text, text.get_rect(center=rect.center))

        for index, member in enumerate(encounter.members):
            enemy = member.enemy
            lane = pygame.Rect(
                margin + index * (lane_width + gap),
                top,
                lane_width,
                lane_height,
            )
            focused = member.combatant_id == focus_target_id
            living = member.is_living_hostile
            animator = self._get_sprite_animator(enemy)
            if member.resolution is not None and not animator.is_dead:
                animator.trigger_death()
            removing = (
                member.resolution is not None
                and animator.animation_type == "death"
                and not animator.is_dead
            )
            if not living and not removing:
                continue
            if living:
                self._enemy_card_rects[member.combatant_id] = lane
            lane_color = self._hostile_lane_color(index)
            pygame.draw.rect(self.screen, lane_color, lane, 3 if focused else 1)

            title_font = pygame.font.Font(None, 25)
            body_font = pygame.font.Font(None, 20)
            has_sight = bool(details_by_id.get(member.combatant_id, False))
            hidden_by_invisibility = self._enemy_hidden_by_invisibility(
                enemy,
                has_sight,
            )
            presented_label = "Unseen force" if hidden_by_invisibility else member.display_label
            label = self._truncate_text(
                title_font,
                presented_label,
                lane.width - 20,
            )
            sprite_area = pygame.Rect(
                lane.left + 10,
                lane.top + 42,
                lane.width - 20,
                max(120, lane.height - 50),
            )
            sprite = self._enemy_sprite_surface(
                enemy,
                self._enemy_encounter_sprite_size(
                    enemy,
                    (sprite_area.width, lane.height),
                ),
                has_sight=has_sight,
            )
            if sprite is not None:
                if animator.damage_flash > 0:
                    sprite = animator.apply_tint(
                        sprite,
                        (255, 100, 100),
                        animator.damage_flash,
                    )
                if animator.animation_type == "death":
                    scale = 1.0 - (animator.death_progress * 0.7)
                    sprite = pygame.transform.scale(
                        sprite,
                        (
                            max(1, int(sprite.get_width() * scale)),
                            max(1, int(sprite.get_height() * scale)),
                        ),
                    )
                    sprite.set_alpha(int(255 * (1.0 - animator.death_progress)))
                else:
                    sprite = self._fade_sprite_for_smoke_screen(
                        sprite,
                        enemy,
                        "enemy",
                    )
                try:
                    visible_bounds = sprite.get_bounding_rect(min_alpha=1)
                except (AttributeError, TypeError):
                    visible_bounds = sprite.get_rect()
                if getattr(enemy, "flying", False):
                    sprite_left = sprite_area.centerx - visible_bounds.centerx
                    sprite_top = lane.centery - 10 + animator.bob_offset - visible_bounds.centery
                else:
                    pace_offset = (
                        animator.confused_pace_offset() if self._enemy_is_polymorphed(enemy) else 0
                    )
                    sprite_left = (
                        sprite_area.centerx
                        + animator.sway_offset
                        + pace_offset
                        - visible_bounds.centerx
                    )
                    sprite_top = sprite_area.bottom - visible_bounds.bottom
                sprite_rect = sprite.get_rect(
                    topleft=(sprite_left, sprite_top),
                )
                visible_rect = visible_bounds.move(sprite_rect.topleft)
                self.screen.blit(sprite, sprite_rect)
                self._enemy_target_rects[member.combatant_id] = visible_rect
            elif self._enemy_hidden_by_invisibility(enemy, has_sight):
                self._enemy_target_rects[member.combatant_id] = lane.copy()

            if not living:
                continue
            title = title_font.render(label, True, self.colors["text"])
            title_shadow = title_font.render(label, True, (0, 0, 0))
            title_center = (lane.centerx, lane.top + 16)
            self.screen.blit(
                title_shadow,
                title_shadow.get_rect(center=(title_center[0] + 2, title_center[1] + 2)),
            )
            self.screen.blit(title, title.get_rect(center=title_center))
            if has_sight:
                mana = getattr(enemy, "mana", None)
                if mana is not None and getattr(mana, "max", 0) > 0:
                    detail_text = (
                        f"HP {enemy.health.current}/{enemy.health.max} · "
                        f"MP {mana.current}/{mana.max}"
                    )
                else:
                    detail_text = f"HP {enemy.health.current}/{enemy.health.max}"
            else:
                detail_text = None
            if detail_text is not None:
                info = body_font.render(detail_text, True, self.colors["text"])
                self.screen.blit(
                    info,
                    info.get_rect(center=(lane.centerx, lane.top + 36)),
                )
            if focused:
                target_rect = self._enemy_target_rects.get(
                    member.combatant_id,
                    lane,
                )
                marker_y = max(lane.top + 44, target_rect.top - 18)
                pygame.draw.polygon(
                    self.screen,
                    lane_color,
                    (
                        (target_rect.centerx - 8, marker_y),
                        (target_rect.centerx + 8, marker_y),
                        (target_rect.centerx, marker_y + 10),
                    ),
                )
            if has_sight:
                icons = self._collect_status_icons(enemy)
                if icons:
                    self._render_status_icons(
                        icons,
                        lane.left + 12,
                        lane.bottom - 28,
                        max_width=lane.width - 24,
                        max_rows=1,
                    )
            self._render_ability_status_visuals(
                enemy,
                member.combatant_id,
                include_duplicates=False,
            )

        self._last_enemy_target_rect = self._enemy_target_rects.get(
            focus_target_id,
            self._last_enemy_target_rect,
        ).copy()
        self._render_active_impact_effects()
        self._render_floating_texts()

    def render_enemy_in_dungeon(self, player_char, enemy, show_enemy_details=None):
        """Render the enemy as if it's standing in the dungeon ahead of the player."""
        if self._hide_enemy_for_flee:
            return

        # Update animations
        self.update_animations()

        # Enemy appears in the center-front of the dungeon view (foreground layer)
        # Position at bottom-center of the dungeon view area (left 65% of screen)
        visual_offset_x, visual_offset_y = self.enemy_visual_offset
        view_width = self.dungeon_view_width
        center_x = view_width // 2 + visual_offset_x + self._enemy_recoil_offset()

        # Position enemy at bottom third (standing on the floor ahead)
        center_y = int(self.screen_height * 0.65) + visual_offset_y

        is_flying = getattr(enemy, "flying", False)
        polymorphed = self._enemy_is_polymorphed(enemy)
        if is_flying:
            center_y -= min(56, max(28, int(self.screen_height * 0.05)))

        # Get animator for this enemy
        animator = self._get_sprite_animator(enemy)

        # Check if player can see enemy details
        has_sight = self._enemy_details_visible(player_char, enemy, show_enemy_details)

        sprite_size = self._enemy_dungeon_combat_sprite_size(enemy)
        display_sprite = self._enemy_sprite_surface(enemy, sprite_size, has_sight=has_sight)
        enemy_size = sprite_size[1] // 2

        if display_sprite is not None:
            # Apply damage flash tint
            if animator.damage_flash > 0:
                display_sprite = animator.apply_tint(
                    display_sprite, (255, 100, 100), animator.damage_flash
                )

            # Apply death animation
            if animator.animation_type == "death":
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
            enemy_size = 150
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

        hidden_by_invisibility = self._enemy_hidden_by_invisibility(
            enemy,
            has_sight,
        )
        if not hidden_by_invisibility:
            # Enemy name label at top of sprite
            font = pygame.font.Font(None, 36)
            name_surf = font.render(enemy.name, True, (255, 255, 255))
            # Add shadow for better readability
            shadow_surf = font.render(enemy.name, True, (0, 0, 0))
            name_rect = name_surf.get_rect(center=(center_x, center_y - enemy_size - 40))
            shadow_rect = shadow_surf.get_rect(center=(center_x + 2, center_y - enemy_size - 38))
            self.screen.blit(shadow_surf, shadow_rect)
            self.screen.blit(name_surf, name_rect)

        # Enemy HP/MP bars above name (only visible with sight)
        if has_sight:
            bar_width = 250
            bar_height = 25
            bar_x = center_x - bar_width // 2
            bar_y = center_y - enemy_size - 80

            # Background
            pygame.draw.rect(
                self.screen, (40, 40, 40), pygame.Rect(bar_x, bar_y, bar_width, bar_height)
            )

            # HP fill
            hp_ratio = enemy.health.current / max(enemy.health.max, 1)
            hp_width = int(bar_width * hp_ratio)
            pygame.draw.rect(
                self.screen, self.colors["hp_bar"], pygame.Rect(bar_x, bar_y, hp_width, bar_height)
            )

            # Border
            pygame.draw.rect(
                self.screen, (150, 150, 150), pygame.Rect(bar_x, bar_y, bar_width, bar_height), 2
            )

            # HP text
            hp_font = pygame.font.Font(None, 22)
            hp_text = f"HP {enemy.health.current}/{enemy.health.max}"
            hp_surf = hp_font.render(hp_text, True, (255, 255, 255))
            hp_rect = hp_surf.get_rect(center=(center_x, bar_y + bar_height // 2))
            self.screen.blit(hp_surf, hp_rect)

            resource_bottom = bar_y + bar_height
            enemy_mana = getattr(enemy, "mana", None)
            if enemy_mana is not None and getattr(enemy_mana, "max", 0) > 0:
                mp_y = resource_bottom + 6
                pygame.draw.rect(
                    self.screen, (40, 40, 40), pygame.Rect(bar_x, mp_y, bar_width, bar_height)
                )
                mp_ratio = enemy_mana.current / max(enemy_mana.max, 1)
                mp_width = int(bar_width * mp_ratio)
                pygame.draw.rect(
                    self.screen,
                    self.colors["mp_bar"],
                    pygame.Rect(bar_x, mp_y, mp_width, bar_height),
                )
                pygame.draw.rect(
                    self.screen, (150, 150, 150), pygame.Rect(bar_x, mp_y, bar_width, bar_height), 2
                )
                mp_text = f"MP {enemy_mana.current}/{enemy_mana.max}"
                mp_surf = hp_font.render(mp_text, True, (255, 255, 255))
                mp_rect = mp_surf.get_rect(center=(center_x, mp_y + bar_height // 2))
                self.screen.blit(mp_surf, mp_rect)
                resource_bottom = mp_y + bar_height

            # Status icons under the HP bar
            icons = self._collect_status_icons(enemy)
            if icons:
                self._render_status_icons(icons, bar_x, resource_bottom + 8, max_width=bar_width)

        self._render_active_impact_effects()
        self._render_floating_texts()

    def render_combat_overlay(
        self,
        player_char,
        enemy,
        actions,
        selected_action,
        current_turn=None,
        show_enemy_details=None,
        current_actor=None,
        timeline_entries=(),
        interface_snapshot=None,
        engine=None,
    ):
        """Render combat UI overlay (action menu and combat log) over the dungeon view."""
        self._set_combat_log_actors(player_char, enemy)
        self._last_player_target_rect = pygame.Rect(
            26,
            self.screen_height - 312,
            max(180, int(self.screen_width * 0.24)),
            130,
        )
        self._render_player_danger_vignette(player_char)
        self._render_telegraph_banner(enemy=enemy, overlay=True)
        # The dungeon HUD owns the right-side column. The legacy enemy-info
        # card previously overlapped that native responsive HUD at wide sizes.
        self._render_ability_status_visuals(enemy, "enemy")
        self._render_ability_status_visuals(player_char, "player")

        # Render combat log at bottom-left
        self._render_combat_log_overlay()
        self._render_timeline_ribbon(
            timeline_entries,
            player_char,
            engine=engine,
            current_actor=current_actor,
            current_turn=current_turn,
        )
        if interface_snapshot is not None:
            self._render_environmental_effect_banner(interface_snapshot.environmental_effects)

        # Render action menu at bottom
        if actions:  # Only show action menu if there are actions
            self._render_action_menu_overlay(actions, selected_action, interface_snapshot)

    def _render_timeline_ribbon(
        self,
        entries,
        player_char,
        *,
        engine=None,
        current_actor=None,
        current_turn=None,
    ) -> None:
        """Render the current actor and upcoming opportunities in one ribbon."""
        if not entries:
            return
        view_width = self.dungeon_view_width
        visible_entries = entries[:6]
        active_width = self.native_unit(154)
        next_token_size = self.native_unit(28)
        next_spacing = next_token_size + self.native_unit(8)
        width = (
            active_width + max(0, len(visible_entries) - 1) * next_spacing + self.native_unit(16)
        )
        rect = pygame.Rect(
            max(self.native_unit(8), view_width - width - self.native_unit(10)),
            self.native_unit(164),
            width,
            self.native_unit(58),
        )
        self._draw_panel_surface(
            rect,
            fill=(20, 20, 25),
            border=(100, 100, 115),
            accent=(105, 90, 58),
            alpha=210,
            border_width=1,
        )
        label_font = pygame.font.Font(None, self.native_unit(20))
        name_font = pygame.font.Font(None, self.native_unit(16))
        for index, entry in enumerate(visible_entries):
            active = index == 0
            token_size = self.native_unit(40) if active else next_token_size
            next_token_x = rect.left + active_width + (index - 1) * next_spacing
            token_x = rect.left + self.native_unit(9) if active else next_token_x
            token_rect = pygame.Rect(
                token_x,
                rect.centery - token_size // 2,
                token_size,
                token_size,
            )
            border = self._timeline_actor_border(entry.actor_id, engine)
            token_padding = self.native_unit(4)
            pygame.draw.rect(
                self.screen,
                (30, 30, 38),
                token_rect.inflate(token_padding, token_padding),
                border_radius=token_padding,
            )
            pygame.draw.rect(
                self.screen,
                border,
                token_rect.inflate(token_padding, token_padding),
                self.native_unit(3 if active else 2),
                border_radius=token_padding,
            )
            actor = self._timeline_actor(entry.actor_id, player_char, engine, current_actor)
            hidden_enemy = entry.actor_id != PLAYER_ACTOR_ID and self._enemy_hidden_by_invisibility(
                actor,
                self._has_sight(player_char),
            )
            token = (
                None
                if hidden_enemy
                else self._timeline_token(actor, entry.actor_id, player_char, token_size)
            )
            if token is not None:
                self.screen.blit(token, token.get_rect(center=token_rect.center))
            else:
                fallback = pygame.font.Font(None, self.native_unit(17)).render(
                    str(entry.display_label or "?")[:1].upper(), True, (230, 225, 210)
                )
                self.screen.blit(fallback, fallback.get_rect(center=token_rect.center))
            if active:
                player_turn = current_turn == "player" or (
                    current_turn is None and entry.actor_id == PLAYER_ACTOR_ID
                )
                label = "Your Turn" if player_turn else "Enemy Turn"
                actor_name = str(getattr(actor, "name", "") or entry.display_label)
                if hidden_enemy:
                    actor_name = presented_enemy_name(actor, self._has_sight(player_char))
                actor_name = self._truncate_text(
                    name_font, actor_name, active_width - self.native_unit(62)
                )
                self.screen.blit(
                    label_font.render(label, True, (250, 245, 230)),
                    (token_rect.right + self.native_unit(9), rect.top + self.native_unit(10)),
                )
                self.screen.blit(
                    name_font.render(actor_name, True, (205, 205, 210)),
                    (token_rect.right + self.native_unit(9), rect.top + self.native_unit(34)),
                )

        if len(visible_entries) > 1:
            pygame.draw.line(
                self.screen,
                (100, 100, 115),
                (rect.left + active_width - self.native_unit(8), rect.top + self.native_unit(8)),
                (rect.left + active_width - self.native_unit(8), rect.bottom - self.native_unit(8)),
                self.native_unit(1),
            )

    def _timeline_actor_border(self, actor_id: str, engine=None) -> tuple[int, int, int]:
        """Return the established side color for a timeline token outline."""
        if actor_id == PLAYER_ACTOR_ID:
            return self.colors["turn_player"]
        encounter = getattr(engine, "encounter", None)
        members = getattr(encounter, "members", ())
        for index, member in enumerate(members):
            if getattr(member, "combatant_id", None) == actor_id:
                return self._hostile_lane_color(index)
        return self.colors["turn_enemy"]

    def _hostile_lane_color(self, index: int) -> tuple[int, int, int]:
        """Return a stable, readable color for an encounter hostile lane."""
        return self.colors["turn_enemy" if index % 2 == 0 else "turn_enemy_alt"]

    @staticmethod
    def _timeline_actor(actor_id, player_char, engine, current_actor):
        """Resolve a timeline actor from its stable ID for token rendering."""
        if actor_id == PLAYER_ACTOR_ID:
            if getattr(engine, "current_actor_id", None) == actor_id and current_actor is not None:
                return current_actor
            return player_char
        if getattr(engine, "current_actor_id", None) == actor_id and current_actor is not None:
            return current_actor
        encounter = getattr(engine, "encounter", None)
        member_by_id = getattr(encounter, "member_by_id", None)
        if callable(member_by_id):
            try:
                return member_by_id(actor_id).enemy
            except (KeyError, AttributeError):
                return None
        return None

    def _timeline_token(self, actor, actor_id, player_char, size):
        """Load a compact player-side or enemy token with safe visual fallback."""
        if actor is None:
            return None
        try:
            if actor_id == PLAYER_ACTOR_ID:
                if actor is not player_char:
                    return get_companion_art_manager().get_scaled_sprite(actor, (size, size))
                return self.player_token_manager.get_scaled_token(player_char, (size, size))
            return self.enemy_token_manager.get_scaled_token(actor, (size, size))
        except (AttributeError, OSError, pygame.error):
            return None

    def _render_environmental_effect_banner(self, effects) -> None:
        """Show world modifiers not already represented by the persistent HUD."""
        effects = [effect for effect in effects if effect.label != "Anti-Magic Field"]
        if not effects:
            return
        view_width = self.dungeon_view_width
        y = self.screen_height - self.native_unit(204)
        rect = pygame.Rect(
            self.native_unit(10),
            y,
            max(self.native_unit(180), view_width - self.native_unit(20)),
            self.native_unit(29),
        )
        self._draw_panel_surface(
            rect,
            fill=(79, 35, 91),
            border=(235, 126, 248),
            accent=(255, 207, 86),
            alpha=242,
            border_width=2,
        )
        effect = effects[0]
        font = pygame.font.Font(None, self.native_unit(19))
        text = self._truncate_text(
            font,
            f"{effect.icon_label}  {effect.label.upper()}: {effect.detail}",
            rect.width - self.native_unit(14),
        )
        self.screen.blit(
            font.render(text, True, (255, 241, 255)),
            (rect.left + self.native_unit(7), rect.top + self.native_unit(6)),
        )

    def _render_combat_log_overlay(self):
        """Render combat log as semi-transparent overlay on dungeon view."""
        view_width = self.dungeon_view_width
        log_height = self.native_unit(150)
        log_y = self.native_unit(10)  # Top of screen

        log_rect = pygame.Rect(0, log_y, view_width, log_height)
        self._draw_panel_surface(
            log_rect,
            fill=(15, 15, 20),
            border=(80, 80, 90),
            accent=(105, 90, 58),
            alpha=200,
            border_width=2,
        )

        # Messages
        font = pygame.font.Font(None, self.native_unit(22))
        y = log_y + self.native_unit(10)
        line_height = self.native_unit(25)
        max_lines = self.log_lines_per_page
        lines_rendered = 0

        display_lines = self._wrapped_combat_log_entries(
            view_width - self.native_unit(30), font=font, overlay=True
        )
        max_scroll = max(0, len(display_lines) - max_lines)
        self.log_scroll_offset = min(self.log_scroll_offset, max_scroll)

        for line in display_lines[self.log_scroll_offset : self.log_scroll_offset + max_lines]:
            if lines_rendered >= max_lines:
                break
            marker_color = (90, 90, 98) if line.continuation else line.marker_color
            pygame.draw.rect(
                self.screen,
                marker_color,
                pygame.Rect(
                    self.native_unit(11),
                    y + self.native_unit(5),
                    self.native_unit(4),
                    self.native_unit(12),
                ),
            )
            msg_surf = font.render(line.text, True, line.color)
            self.screen.blit(msg_surf, (self.native_unit(31 if line.continuation else 20), y))
            y += line_height
            lines_rendered += 1

        if len(display_lines) > max_lines:
            indicator_font = pygame.font.Font(None, 18)
            if self.log_scroll_offset > 0:
                up_surf = indicator_font.render("^", True, (210, 210, 210))
                self.screen.blit(up_surf, (view_width - 24, log_y + 8))
            if self.log_scroll_offset < max_scroll:
                down_surf = indicator_font.render("v", True, (210, 210, 210))
                self.screen.blit(down_surf, (view_width - 24, log_y + log_height - 22))

            hint = indicator_font.render("PgUp/PgDn or Mouse Wheel", True, (170, 170, 170))
            self.screen.blit(hint, (view_width - hint.get_width() - 34, log_y + log_height - 22))

    def _render_action_menu_overlay(self, actions, selected_action, interface_snapshot=None):
        """Render a six-slot ability bar and compact fixed-system commands."""
        view_width = self.dungeon_view_width
        menu_height = self.native_unit(174)
        menu_y = self.screen_height - menu_height

        menu_rect = pygame.Rect(0, menu_y, view_width, menu_height)
        self._draw_panel_surface(
            menu_rect,
            fill=(20, 20, 25),
            border=self.colors["action_border"],
            accent=self.colors["panel_accent"],
            alpha=220,
            border_width=3,
        )

        slots = tuple(getattr(interface_snapshot, "shortcuts", ()) or ())
        if len(slots) != 6:
            self._render_action_grid(
                actions,
                selected_action,
                rect=menu_rect,
                action_font=pygame.font.Font(None, 26),
                text_color=(240, 240, 240),
                highlight_color=(100, 100, 120),
                border_color=(150, 150, 170),
                translucent_highlight=True,
            )
            return

        card_y = menu_y + self.native_unit(9)
        card_height = self.native_unit(104)
        card_width = max(self.native_unit(72), (view_width - self.native_unit(28)) // 6)
        icon_manager = get_ability_icon_manager()
        name_font = pygame.font.Font(None, self.native_unit(18))
        slot_font = pygame.font.Font(None, self.native_unit(17))
        for index, slot in enumerate(slots):
            rect = pygame.Rect(
                self.native_unit(12) + index * card_width,
                card_y,
                card_width - self.native_unit(4),
                card_height,
            )
            action = slot.action
            enabled = action is not None and action.enabled
            selected = selected_action == index
            fill = (45, 52, 66) if enabled else (45, 40, 47)
            border = (244, 204, 91) if selected else (118, 128, 150) if enabled else (100, 74, 86)
            self._draw_panel_surface(
                rect,
                fill=fill,
                border=border,
                accent=(150, 170, 206),
                alpha=240,
                border_width=self.native_unit(3 if selected else 1),
            )
            slot_text = slot_font.render(str(index + 1), True, (248, 226, 151))
            self.screen.blit(
                slot_text, (rect.left + self.native_unit(5), rect.top + self.native_unit(4))
            )
            icon_key = getattr(action, "icon_key", "unknown") if action is not None else "unknown"
            icon = icon_manager.get_icon(icon_key)
            icon_size = self.native_unit(34)
            icon = pygame.transform.smoothscale(icon, (icon_size, icon_size))
            self.screen.blit(
                icon,
                icon.get_rect(centerx=rect.centerx, top=rect.top + self.native_unit(18)),
            )
            label = action.display_name if action is not None else "Empty"
            label = label.replace("Spell: ", "").replace("Skill: ", "")
            label = self._truncate_text(name_font, label, rect.width - self.native_unit(8))
            color = (242, 242, 238) if enabled else (178, 154, 160)
            label_surf = name_font.render(label, True, color)
            self.screen.blit(
                label_surf,
                label_surf.get_rect(centerx=rect.centerx, top=rect.top + self.native_unit(57)),
            )
            if action is not None and not action.enabled:
                reason = self._truncate_text(
                    name_font, action.availability.reason, rect.width - self.native_unit(8)
                )
                reason_surf = name_font.render(reason, True, (226, 154, 148))
                self.screen.blit(
                    reason_surf,
                    reason_surf.get_rect(centerx=rect.centerx, top=rect.top + self.native_unit(78)),
                )

        commands = actions[6:]
        command_y = menu_y + self.native_unit(122)
        if commands:
            command_width = max(
                self.native_unit(70), (view_width - self.native_unit(24)) // len(commands)
            )
            command_font = pygame.font.Font(None, self.native_unit(20))
            for offset, command in enumerate(commands):
                index = offset + 6
                rect = pygame.Rect(
                    self.native_unit(12) + offset * command_width,
                    command_y,
                    command_width - self.native_unit(4),
                    self.native_unit(37),
                )
                selected = selected_action == index
                unavailable = " — Not available this turn." in str(command)
                pygame.draw.rect(
                    self.screen,
                    (73, 67, 78) if unavailable else (52, 58, 70),
                    rect,
                    border_radius=4,
                )
                pygame.draw.rect(
                    self.screen,
                    (244, 204, 91) if selected else (128, 125, 145),
                    rect,
                    self.native_unit(2 if selected else 1),
                    border_radius=self.native_unit(4),
                )
                label = str(command).replace(" — Not available this turn.", "")
                label = self._truncate_text(command_font, label, rect.width - self.native_unit(8))
                color = (185, 170, 175) if unavailable else (238, 235, 225)
                text = command_font.render(label, True, color)
                self.screen.blit(text, text.get_rect(center=rect.center))

    def _render_turn_indicator(
        self, player_char, enemy, current_turn=None, overlay=False, current_actor=None
    ):
        """Render a compact banner showing whose turn is active."""
        if current_turn not in {"player", "enemy"}:
            return
        turn_actor = (
            current_actor
            if current_actor is not None
            else (player_char if current_turn == "player" else enemy)
        )
        incapacitated = getattr(turn_actor, "incapacitated", None)
        if callable(incapacitated) and incapacitated():
            return

        view_width = self.dungeon_view_width
        token_size = self.native_unit(46)
        text_left = token_size + self.native_unit(26)
        min_height = self.native_unit(64)
        label = "Your Turn" if current_turn == "player" else "Enemy Turn"
        hidden_enemy = current_turn == "enemy" and self._enemy_hidden_by_invisibility(
            turn_actor,
            self._has_sight(player_char),
        )
        if current_turn == "enemy":
            sublabel = presented_enemy_name(
                turn_actor,
                self._has_sight(player_char),
            )
        else:
            sublabel = getattr(turn_actor, "name", "Player")
        color = self.colors["turn_player" if current_turn == "player" else "turn_enemy"]

        font = pygame.font.Font(None, self.native_unit(26))
        small_font = pygame.font.Font(None, self.native_unit(18))
        label_surf = font.render(label, True, (255, 255, 255))

        max_width = max(self.native_unit(120), view_width - self.native_unit(30))
        width = min(
            max(
                label_surf.get_width() + text_left + self.native_unit(14),
                small_font.size(sublabel)[0] + text_left + self.native_unit(14),
                self.native_unit(180),
            ),
            max_width,
        )
        sublabel = self._truncate_text(
            small_font, sublabel, width - text_left - self.native_unit(14)
        )
        sublabel_surf = small_font.render(sublabel, True, (220, 220, 220))
        x = max(self.native_unit(15), (view_width - width) // 2)
        rect = pygame.Rect(
            x,
            self.native_unit(164 if overlay else 12),
            width,
            min_height,
        )

        if overlay:
            panel = pygame.Surface(rect.size)
            panel.set_alpha(210)
            panel.fill((18, 18, 24))
            self.screen.blit(panel, rect.topleft)
        else:
            pygame.draw.rect(self.screen, (18, 18, 24), rect)

        pygame.draw.rect(self.screen, color, rect, self.native_unit(3))
        if current_turn == "player":
            try:
                if turn_actor is player_char:
                    token = self.player_token_manager.get_scaled_token(
                        player_char, (token_size, token_size)
                    )
                else:
                    token = get_companion_art_manager().get_scaled_sprite(
                        turn_actor, (token_size, token_size)
                    )
            except (
                Exception
            ) as exc:  # pragma: no cover - defensive runtime fallback for external art failures
                print(
                    f"Failed to render player-side token for {getattr(turn_actor, 'name', turn_actor)}: {exc}"
                )
                token = None
        else:
            token = None
            if not hidden_enemy:
                try:
                    token = self.enemy_token_manager.get_scaled_token(
                        turn_actor,
                        (token_size, token_size),
                    )
                except (
                    Exception
                ) as exc:  # pragma: no cover - defensive runtime fallback for external art failures
                    print(
                        f"Failed to render enemy token for {getattr(enemy, 'name', enemy)}: {exc}"
                    )
        if token is not None:
            self.screen.blit(
                token, (rect.left + self.native_unit(8), rect.centery - token_size // 2)
            )
        self.screen.blit(label_surf, (rect.left + text_left, rect.top + self.native_unit(8)))
        self.screen.blit(sublabel_surf, (rect.left + text_left, rect.top + self.native_unit(34)))
        if current_turn == "player" and turn_actor is not player_char:
            icons = self._collect_status_icons(turn_actor)
            if icons:
                self._render_status_icons(
                    icons,
                    rect.left + text_left,
                    rect.bottom + self.native_unit(4),
                    max_width=width - text_left - self.native_unit(10),
                    max_rows=1,
                )

    def _latest_telegraph_line(self, actor=None) -> str | None:
        if self._active_telegraph_line:
            if actor is None or self._message_starts_with_actor(self._active_telegraph_line, actor):
                return self._active_telegraph_line
        if self._suppress_logged_telegraph_banner:
            return None
        for message in reversed(self.combat_log):
            for line in reversed(
                [segment.strip() for segment in message.split("\n") if segment.strip()]
            ):
                if self._is_telegraph_message(line) and (
                    actor is None or self._message_starts_with_actor(line, actor)
                ):
                    return line
        return None

    @staticmethod
    def _message_starts_with_actor(message: str, actor) -> bool:
        actor_name = getattr(actor, "name", "")
        return bool(actor_name and message.startswith(f"{actor_name} "))

    def _render_telegraph_banner(self, enemy=None, overlay: bool = False) -> None:
        line = self._latest_telegraph_line(actor=enemy)
        if not line:
            return

        available_width = self.combat_width - 56
        if available_width <= 0:
            return

        title_font = pygame.font.Font(None, 20)
        body_font = pygame.font.Font(None, 19)
        title_text = "Incoming"
        title_surf = title_font.render(title_text, True, (246, 238, 216))
        body_text = self._truncate_text(body_font, line, max(120, available_width - 128))
        body_surf = body_font.render(body_text, True, self.colors["telegraph"])

        width = min(max(title_surf.get_width() + body_surf.get_width() + 102, 340), available_width)
        height = 46
        x = max(20, (self.combat_width - width) // 2)
        y = 205 if overlay else 74
        rect = pygame.Rect(x, y, width, height)

        self._draw_panel_surface(
            rect,
            fill=(26, 20, 14),
            border=self.colors["telegraph"],
            accent=(176, 96, 58),
            alpha=225,
            border_width=2,
        )
        pygame.draw.rect(
            self.screen,
            (132, 58, 42),
            pygame.Rect(rect.left + 10, rect.top + 9, 7, rect.height - 18),
        )
        pygame.draw.circle(self.screen, self.colors["telegraph"], (rect.left + 30, rect.centery), 5)
        self.screen.blit(title_surf, (rect.left + 44, rect.top + 6))
        self.screen.blit(body_surf, (rect.left + 44, rect.top + 24))
