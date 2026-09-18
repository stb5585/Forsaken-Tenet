"""Status behavior for the combat view package."""

from __future__ import annotations

import math

import pygame

from ..enemy_presentation import effect_icon_label
from ..status_icons import (
    RESIST_STATUS_LABELS,
    combine_duplicate_status_icons,
    compact_status_icons,
    fit_status_icon_label,
    load_status_icon_surface,
    prioritize_status_icons,
    stat_effect_status_icon,
    status_icon_color,
    status_icon_stack_count,
    totem_status_icons,
)


class CombatStatusMixin:
    @staticmethod
    def _combat_log_font_cache_key(font: pygame.font.Font | None) -> int:
        if font is None:
            return 0
        try:
            return int(font.size("Dungeon Combat Log Probe")[0])
        except Exception:
            return id(font)

    def _draw_panel_surface(
        self,
        rect: pygame.Rect,
        *,
        fill: tuple[int, int, int],
        border: tuple[int, int, int],
        accent: tuple[int, int, int] | None = None,
        alpha: int | None = None,
        border_width: int = 2,
    ) -> None:
        if alpha is None:
            pygame.draw.rect(self.screen, fill, rect)
        else:
            panel = pygame.Surface(rect.size)
            panel.set_alpha(alpha)
            panel.fill(fill)
            self.screen.blit(panel, rect.topleft)
        pygame.draw.rect(self.screen, border, rect, border_width)
        if accent is not None and rect.height >= 10:
            try:
                pygame.draw.line(
                    self.screen,
                    accent,
                    (rect.left + 2, rect.top + 2),
                    (rect.right - 3, rect.top + 2),
                    1,
                )
                pygame.draw.line(
                    self.screen,
                    (18, 18, 22),
                    (rect.left + 2, rect.bottom - 3),
                    (rect.right - 3, rect.bottom - 3),
                    1,
                )
            except TypeError:
                return

    def _render_player_danger_vignette(self, player_char) -> None:
        health = getattr(player_char, "health", None)
        current = getattr(health, "current", 0)
        maximum = max(1, getattr(health, "max", 1))
        ratio = current / maximum
        if ratio > 0.25:
            return

        intensity = min(1.0, (0.25 - ratio) / 0.25)
        pulse = (math.sin(pygame.time.get_ticks() / 210.0) + 1.0) / 2.0
        alpha = int(36 + intensity * 58 + pulse * (12 + intensity * 34))
        overlay = pygame.Surface((self.combat_width, self.screen_height), pygame.SRCALPHA)
        center_rect = pygame.Rect(
            -int(self.combat_width * 0.10),
            -int(self.screen_height * 0.18),
            int(self.combat_width * 1.20),
            int(self.screen_height * 1.32),
        )
        for index, width in enumerate((80, 54, 32, 16)):
            ring_alpha = max(18, alpha - index * 22)
            ring_rect = center_rect.inflate(index * 56, index * 42)
            pygame.draw.ellipse(
                overlay,
                (160, 24, 22, ring_alpha),
                ring_rect,
                width=width,
            )
        if intensity > 0.5:
            pulse_alpha = int((intensity - 0.5) * (58 + pulse * 48))
            pygame.draw.rect(
                overlay,
                (110, 18, 18, pulse_alpha),
                pygame.Rect(0, self.screen_height - 312, self.combat_width, 156),
            )
        self.screen.blit(overlay, (0, 0))

    def _effect_label(self, effect_name):
        labels = {
            "Berserk": "BRK",
            "Blind": "BLD",
            "Blind Rage": "BRG",
            "Doom": "DOM",
            "Fear": "FEA",
            "Poison": "PSN",
            "Silence": "SIL",
            "Sleep": "SLP",
            "Stun": "STN",
            "Defend": "DEF",
            "Steal Success": "STE",
            "Bleed": "RND",
            "Disarm": "DSA",
            "Prone": "PRN",
            "Attack": "ATK",
            "Defense": "DEF",
            "Magic": "MAG",
            "Magic Defense": "MDF",
            "Speed": "SPD",
            "DOT": "DOT",
            "Duplicates": "DUP",
            "Ice Block": "ICE",
            "Mana Shield": "MSH",
            "Reflect": "RFL",
            "Regen": "REG",
            **RESIST_STATUS_LABELS,
            "Jump": "JMP",
            "Power Up": "PWR",
            "Vision": "VIS",
            "Reaver's Mark": "RMK",
            "Brace": "BRC",
            "Riposte Line": "RIP",
        }
        return labels.get(effect_name, effect_name[:3].upper())

    def _collect_status_icons(self, character):
        icons = []
        skip_effects = {
            "DOT",
            "Duplicates",
            "Jump",
            "Power Up",
            "Shapeshifted",
            "Steal Success",
            "Totem",
        }
        positive_status = {"Defend", "Steal Success"}
        positive_magic = {
            "Astral Shift",
            "Duplicates",
            "Ice Block",
            "Mana Shield",
            "Reflect",
            "Regen",
            *RESIST_STATUS_LABELS,
        }

        icons.extend(totem_status_icons(character))

        charging_skills = [
            name
            for name, skill in getattr(character, "spellbook", {}).get("Skills", {}).items()
            if getattr(skill, "charging", False)
        ]
        jump_effect = character.class_effects.get("Jump")
        if charging_skills or (jump_effect is not None and jump_effect.active):
            icons.append(("CHG", True))

        if self._vision_icon_active(character):
            icons.append(("VIS", True))
        if getattr(character, "invisible", False):
            icons.append(("INV", True))

        if self._timed_art_state_active(character, "_reavers_mark"):
            icons.append(("RMK", False))
        if self._timed_art_state_active(character, "_brace_art"):
            icons.append(("BRC", True))
        if self._timed_art_state_active(character, "_riposte_line"):
            icons.append(("RIP", True))

        dot_effect = character.magic_effects.get("DOT")
        if dot_effect and dot_effect.active:
            source = getattr(dot_effect, "source", "").lower()
            icons.append(("BRN" if source == "burn" else "DOT", False))

        for name, effect in character.status_effects.items():
            if effect.active and name not in skip_effects:
                icons.append((self._effect_label(name), name in positive_status))
        for name, effect in character.physical_effects.items():
            if effect.active and name not in skip_effects:
                icons.append(
                    (
                        effect_icon_label(name, self._effect_label(name), character),
                        name in positive_status,
                    )
                )
        for name, effect in character.stat_effects.items():
            if name not in skip_effects:
                icon = stat_effect_status_icon(self._effect_label(name), effect)
                if icon is not None:
                    icons.append(icon)
        for name, effect in character.magic_effects.items():
            if effect.active and name not in skip_effects:
                icons.append(
                    (self._effect_label(name), name in positive_magic or name in positive_status)
                )
        for name, effect in character.class_effects.items():
            if effect.active and name not in skip_effects:
                icons.append((self._effect_label(name), True))

        try:
            maelstrom_hits = int(getattr(character, "maelstrom_hits", 0))
            skills = getattr(character, "spellbook", {}).get("Skills", {})
            if "Maelstrom Weapon" in skills and maelstrom_hits > 0:
                icons.append((f"MW{maelstrom_hits}", True))
        except (AttributeError, TypeError, ValueError):
            pass

        try:
            guard_stacks = int(getattr(character, "evasive_guard_stacks", 0) or 0)
            skills = getattr(character, "spellbook", {}).get("Skills", {})
            if "Evasive Guard" in skills and guard_stacks > 0:
                icons.append((f"EG{min(3, guard_stacks)}", True))
        except (AttributeError, TypeError, ValueError):
            pass

        if ("DEF", True) in icons:
            icons = [icon for icon in icons if icon != ("DEF", False)]

        return prioritize_status_icons(combine_duplicate_status_icons(icons))

    @staticmethod
    def _timed_art_state_active(character, attr_name: str) -> bool:
        state = getattr(character, attr_name, None)
        if not isinstance(state, dict):
            return False
        try:
            return int(state.get("turns", 0) or 0) > 0
        except (TypeError, ValueError):
            return False

    @staticmethod
    def _vision_icon_active(character) -> bool:
        cls_name = getattr(getattr(character, "cls", None), "name", "")
        if cls_name in {"Inquisitor", "Seeker"}:
            return True
        equipment = getattr(character, "equipment", {})
        pendant = equipment.get("Pendant") if isinstance(equipment, dict) else None
        if getattr(pendant, "mod", None) == "Vision":
            return True
        return bool(getattr(character, "sight", False))

    @staticmethod
    def _is_telegraph_message(line: str) -> bool:
        lower = line.lower()
        telegraph_terms = (
            " is lowering ",
            " is raising ",
            " is inhaling ",
            " is gathering ",
            " is coiling ",
            " is channeling ",
            " is melding ",
            " is drawing in ",
            " is preparing",
            " is charging",
            " continues charging",
            " begins to charge",
            " while preparing",
        )
        return any(term in lower for term in telegraph_terms)

    @staticmethod
    def _short_telegraph_message(line: str) -> str:
        stripped = str(line).strip()
        if not stripped:
            return "Enemy is charging."
        if " continues charging" in stripped:
            return stripped.split(" continues charging", 1)[0] + " is charging."
        for marker in (
            " is lowering ",
            " is raising ",
            " is inhaling ",
            " is gathering ",
            " is coiling ",
            " is channeling ",
            " is melding ",
            " is drawing in ",
            " is preparing",
        ):
            if marker in stripped:
                return stripped.split(marker, 1)[0] + " is charging."
        if " begins to charge" in stripped:
            return stripped.split(" begins to charge", 1)[0] + " is charging."
        if " while preparing" in stripped:
            return stripped.split(" while preparing", 1)[0] + " is charging."
        return stripped

    def _combat_log_color(self, line: str, overlay: bool = False):
        lower = line.lower()
        if self._is_telegraph_message(line):
            return self.colors["telegraph"]
        if any(
            term in lower
            for term in (
                "health regenerated",
                "health has regenerated",
                "regenerates",
                "restore",
                "restores",
                "recovers",
                "heals",
            )
        ):
            return self.colors["log_heal"]
        if any(term in lower for term in ("miss", "resist", "immune", "fails")):
            return self.colors["log_muted"]
        if any(
            term in lower
            for term in (
                " damage",
                "damages ",
                "bleeding",
                "bleeds",
                "burns",
                "poison",
                "blind",
                "silence",
                "silenced",
                "scorches",
                "shocks",
                "slain",
                "stun",
                "disarm",
                "falls prone",
                "knocked",
                "takes ",
                "loses ",
            )
        ):
            return self.colors["log_damage"]
        if self._line_starts_with_actor(lower, self._combat_log_player_name):
            return self.colors["log_player"]
        if self._line_starts_with_actor(lower, self._combat_log_summon_name):
            return self.colors["log_summon"]
        if self._line_starts_with_actor(lower, self._combat_log_enemy_name):
            return self.colors["log_enemy"]
        return (240, 240, 240) if overlay else self.colors["text"]

    @staticmethod
    def _line_starts_with_actor(lower_line: str, actor_name: str | None) -> bool:
        if not actor_name:
            return False
        actor = actor_name.strip().lower()
        return bool(actor) and (
            lower_line.startswith(actor + " ") or lower_line.startswith(actor + "'")
        )

    def _set_combat_log_actors(self, player_char, enemy) -> None:
        player_name = str(getattr(player_char, "name", "") or "") or None
        enemy_name = str(getattr(enemy, "name", "") or "") or None
        summon_name = str(getattr(player_char, "active_summon_name", "") or "") or None
        if (
            player_name != self._combat_log_player_name
            or enemy_name != self._combat_log_enemy_name
            or summon_name != self._combat_log_summon_name
        ):
            self._combat_log_player_name = player_name
            self._combat_log_enemy_name = enemy_name
            self._combat_log_summon_name = summon_name
            self._invalidate_combat_log_wrap_cache()
        self._combat_log_enemy = enemy

    def _combat_log_marker_color(self, line: str, overlay: bool = False) -> tuple[int, int, int]:
        if self._is_telegraph_message(line):
            return self.colors["telegraph"]
        color = self._combat_log_color(line, overlay=overlay)
        if color == self.colors["text"] or color == (240, 240, 240):
            return (120, 120, 128)
        return color

    @staticmethod
    def _truncate_text(font: pygame.font.Font, text: str, max_width: int) -> str:
        def measured_width(value: str) -> int:
            if hasattr(font, "size"):
                return font.size(value)[0]
            return len(value) * 8

        if max_width <= 0 or measured_width(text) <= max_width:
            return text

        ellipsis = "..."
        ellipsis_width = measured_width(ellipsis)
        clipped = text
        while clipped and measured_width(clipped) + ellipsis_width > max_width:
            clipped = clipped[:-1]
        return f"{clipped}{ellipsis}" if clipped else ellipsis

    def _render_status_icons(self, icons, x, y, max_width, max_rows=2):
        if not icons:
            return

        font = pygame.font.Font(None, self.native_unit(16))
        icon_w = self.native_unit(38)
        icon_h = self.native_unit(26)
        padding = self.native_unit(6)
        per_row = max(1, max_width // (icon_w + padding))
        visible_icons = compact_status_icons(icons, per_row, max_rows)

        for idx, (label, is_positive) in enumerate(visible_icons):
            row = idx // per_row
            col = idx % per_row
            icon_x = x + col * (icon_w + padding)
            icon_y = y + row * (icon_h + padding)
            color = status_icon_color(is_positive, label)

            rect = pygame.Rect(icon_x, icon_y, icon_w, icon_h)
            icon_surface = load_status_icon_surface(label, (icon_h - 2, icon_h - 2), is_positive)
            if icon_surface is not None:
                icon_rect = icon_surface.get_rect(center=rect.center)
                self.screen.blit(icon_surface, icon_rect)
                stack_count = status_icon_stack_count(label)
                if stack_count > 1:
                    badge_text = str(stack_count)
                    badge_font = pygame.font.Font(None, self.native_unit(15))
                    badge_surf = badge_font.render(badge_text, True, (255, 255, 255))
                    badge_radius = max(
                        self.native_unit(7), badge_surf.get_width() // 2 + self.native_unit(4)
                    )
                    badge_center = (
                        rect.right - badge_radius + self.native_unit(2),
                        rect.top + badge_radius - self.native_unit(1),
                    )
                    pygame.draw.circle(self.screen, (22, 22, 28), badge_center, badge_radius)
                    pygame.draw.circle(
                        self.screen,
                        (240, 210, 92),
                        badge_center,
                        badge_radius,
                        self.native_unit(1),
                    )
                    badge_rect = badge_surf.get_rect(center=badge_center)
                    self.screen.blit(badge_surf, badge_rect)
            else:
                pygame.draw.rect(self.screen, color, rect, border_radius=self.native_unit(4))
                pygame.draw.rect(
                    self.screen,
                    (20, 20, 20),
                    rect,
                    self.native_unit(1),
                    border_radius=self.native_unit(4),
                )
                fitted_label = fit_status_icon_label(font, label, icon_w - self.native_unit(6))
                text_surf = font.render(fitted_label, True, (255, 255, 255))
                text_rect = text_surf.get_rect(center=rect.center)
                self.screen.blit(text_surf, text_rect)

    def reload_enemy_sprite(self, enemy) -> None:
        """Compatibility hook for enemies that change visual form during combat."""
        return None
