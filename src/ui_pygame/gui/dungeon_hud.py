"""
Dungeon HUD (Heads-Up Display)
Displays character stats, minimap, inventory quick-access, and other UI elements.
"""

import re

import pygame

from src.core import map_tiles
from src.core.classes import promotion_kits, wizard
from src.core.combat.action_interface import environmental_effect_presentations
from src.core.player import LIMINAL_GAP_LEVEL, REALM_OF_CAMBION_LEVEL

from .enemy_presentation import player_has_sight, presented_enemy_name
from .status_icons import (
    RESIST_STATUS_LABELS,
    STATUS_ICON_COLORS,
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


class DungeonHUD:
    """
    Manages the HUD overlay for dungeon exploration.
    Shows character stats, minimap, compass, inventory, etc.
    """

    def __init__(self, presenter):
        self.presenter = presenter
        self.screen = presenter.screen
        self.width = 0
        self.height = 0
        self._refresh_layout()

        # Colors
        self.bg_color = (25, 25, 30)
        self.border_color = (100, 100, 110)
        self.text_color = (220, 220, 220)
        self.hp_color = (200, 50, 50)
        self.mp_color = (50, 100, 200)
        self.exp_color = (100, 200, 100)
        self.status_colors = STATUS_ICON_COLORS
        self.last_minimap_rect: pygame.Rect | None = None

    def _refresh_layout(self) -> None:
        """Reflow the native-pixel dungeon HUD after a viewport-size change."""
        self.screen = self.presenter.screen
        width, height = self.screen.get_size()
        if (width, height) == (self.width, self.height):
            return
        self.width, self.height = width, height
        metrics = getattr(self.presenter, "layout_metrics", None)
        hud_fraction = metrics.dungeon_hud_fraction if metrics is not None else 0.35
        self.hud_width = int(self.width * hud_fraction)
        self.hud_x = self.width - self.hud_width
        self.hud_rect = pygame.Rect(self.hud_x, 0, self.hud_width, self.height)
        font_size = metrics.font_size if metrics is not None else int
        self.title_font = pygame.font.Font(None, font_size(32))
        self.stat_font = pygame.font.Font(None, font_size(28))
        self.small_font = pygame.font.Font(None, font_size(20))
        self.small_bold_font = pygame.font.Font(None, font_size(20))
        set_bold = getattr(self.small_bold_font, "set_bold", None)
        if callable(set_bold):
            set_bold(True)

    def render_hud(
        self,
        player_char,
        combat_mode=False,
        enemy=None,
        active_summon=None,
        combat_resources=(),
    ):
        """Render the complete HUD.

        Args:
            player_char: The player character
            combat_mode: Whether we're in combat (shows combat indicator)
            enemy: The enemy being fought (if in combat)
            active_summon: The currently summoned combat ally, when active
        """
        self._refresh_layout()
        # Background
        pygame.draw.rect(self.screen, self.bg_color, self.hud_rect)
        pygame.draw.line(
            self.screen, self.border_color, (self.hud_x, 0), (self.hud_x, self.height), 3
        )

        y_offset = 20

        # Combat mode indicator (if in combat)
        if combat_mode:
            self._combat_indicator_player_char = player_char
            y_offset = self._render_combat_indicator(enemy, y_offset)
            y_offset += 15

        # Character name and level
        y_offset = self._render_character_info(player_char, y_offset)
        y_offset += 20

        if not combat_mode:
            y_offset = self._render_location_label(player_char, y_offset)
            y_offset += 12

        y_offset = self._render_environmental_effects(player_char, y_offset)

        # Health and Mana bars
        y_offset = self._render_resource_bars(player_char, y_offset)
        y_offset += 20

        # Status icons (combat only)
        if combat_mode:
            y_offset = self._render_status_icons(player_char, y_offset)
            y_offset += 15

        if combat_mode:
            feature_height = self._combat_feature_height()
            feature_y = self._combat_feature_title_y(feature_height)
            feature_kwargs = {
                "feature_height": feature_height,
                "active_summon": active_summon,
            }
            if combat_resources:
                feature_kwargs["combat_resources"] = combat_resources
            self._render_combat_features(player_char, enemy, feature_y, **feature_kwargs)
            return

        # Compass - hide during combat and keep it above the anchored minimap.
        if not combat_mode:
            y_offset = self._render_compass(player_char, y_offset)
            y_offset += 20

        # Minimap stays pinned low in the HUD during exploration.
        minimap_size = self._minimap_size(combat_mode=False)
        minimap_y = self._minimap_title_y(minimap_size)
        self._render_minimap(player_char, minimap_y, minimap_size=minimap_size)

    @staticmethod
    def location_label(player_char) -> str:
        """Return the player-facing label for the current world location."""
        try:
            location_z = int(getattr(player_char, "location_z", 0) or 0)
        except (TypeError, ValueError):
            location_z = 0
        if location_z == 0:
            return "Town"
        if location_z == REALM_OF_CAMBION_LEVEL:
            return "Realm of Cambion"
        if location_z == LIMINAL_GAP_LEVEL:
            return "Liminal Gap"
        return f"Dungeon Level {location_z}"

    def _render_location_label(self, player_char, y_offset):
        """Render a compact location label in exploration HUD mode."""
        x_margin = self.hud_x + 20
        label = self.location_label(player_char)
        label_surface = self.small_font.render(label, True, (220, 205, 145))
        label_rect = pygame.Rect(
            x_margin, y_offset, self.hud_width - 40, label_surface.get_height() + 10
        )
        pygame.draw.rect(self.screen, (35, 31, 25), label_rect)
        pygame.draw.rect(self.screen, (150, 130, 80), label_rect, 1)
        text_x = label_rect.left + max(8, (label_rect.width - label_surface.get_width()) // 2)
        self.screen.blit(label_surface, (text_x, label_rect.top + 5))
        return label_rect.bottom

    def _render_environmental_effects(self, player_char, y_offset: int) -> int:
        """Render active world modifiers in the shared HUD path."""
        effects = environmental_effect_presentations(player_char)
        if not effects:
            return y_offset
        effect = effects[0]
        rect = pygame.Rect(self.hud_x + 16, y_offset, self.hud_width - 32, 32)
        pygame.draw.rect(self.screen, (66, 42, 72), rect, border_radius=4)
        pygame.draw.rect(self.screen, (190, 118, 205), rect, 1, border_radius=4)
        label = f"{effect.icon_label} {effect.label}"
        surface = self.small_font.render(label, True, (247, 226, 245))
        self.screen.blit(surface, surface.get_rect(center=rect.center))
        return rect.bottom + 12

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
            "Bleed": "RND",
            "Disarm": "DSA",
            "Prone": "PRN",
            "Attack": "ATK",
            "Defense": "DEF",
            "Magic": "MAG",
            "Magic Defense": "MDF",
            "Speed": "SPD",
            "DOT": "DOT",
            "Ice Block": "ICE",
            "Mana Shield": "MSH",
            "Reflect": "RFL",
            "Regen": "REG",
            **RESIST_STATUS_LABELS,
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
        if getattr(character, "invisible", False):
            icons.append(("INV", True))

        dot_effect = character.magic_effects.get("DOT")
        if dot_effect and dot_effect.active:
            source = getattr(dot_effect, "source", "").lower()
            icons.append(("BRN" if source == "burn" else "DOT", False))

        for name, effect in character.status_effects.items():
            if effect.active and name not in skip_effects:
                icons.append((self._effect_label(name), name in positive_status))
        for name, effect in character.physical_effects.items():
            if effect.active and name not in skip_effects:
                icons.append((self._effect_label(name), False))
        for name, effect in character.stat_effects.items():
            if name not in skip_effects:
                icon = stat_effect_status_icon(self._effect_label(name), effect)
                if icon is not None:
                    icons.append(icon)
        for name, effect in character.magic_effects.items():
            if effect.active and name not in skip_effects:
                icons.append((self._effect_label(name), name in positive_magic))
        for name, effect in character.class_effects.items():
            if effect.active and name not in skip_effects:
                icons.append((self._effect_label(name), True))

        # Maelstrom Weapon passive stack indicator (display current consecutive hit stacks)
        try:
            maelstrom_hits = int(getattr(character, "maelstrom_hits", 0))
            skills = getattr(character, "spellbook", {}).get("Skills", {})
            has_maelstrom = "Maelstrom Weapon" in skills
            if has_maelstrom and maelstrom_hits > 0:
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

    def _render_status_icons(self, player_char, y_offset, max_rows=2):
        x_margin = self.hud_x + 20
        icons = self._collect_status_icons(player_char)
        if not icons:
            return y_offset

        icon_w = 42
        icon_h = 26
        padding = 6
        max_width = self.hud_width - 40
        per_row = max(1, max_width // (icon_w + padding))
        visible_icons = compact_status_icons(icons, per_row, max_rows)
        font = pygame.font.Font(None, 16)

        for idx, (label, is_positive) in enumerate(visible_icons):
            row = idx // per_row
            col = idx % per_row
            icon_x = x_margin + col * (icon_w + padding)
            icon_y = y_offset + row * (icon_h + padding)
            color = status_icon_color(is_positive, label)

            rect = pygame.Rect(icon_x, icon_y, icon_w, icon_h)
            icon_surface = load_status_icon_surface(label, (icon_h - 2, icon_h - 2), is_positive)
            if icon_surface is not None:
                icon_rect = icon_surface.get_rect(center=rect.center)
                self.screen.blit(icon_surface, icon_rect)
                stack_count = status_icon_stack_count(label)
                if stack_count > 1:
                    badge_text = str(stack_count)
                    badge_font = pygame.font.Font(None, 15)
                    badge_surf = badge_font.render(badge_text, True, (255, 255, 255))
                    badge_radius = max(7, badge_surf.get_width() // 2 + 4)
                    badge_center = (rect.right - badge_radius + 2, rect.top + badge_radius - 1)
                    pygame.draw.circle(self.screen, (22, 22, 28), badge_center, badge_radius)
                    pygame.draw.circle(self.screen, (240, 210, 92), badge_center, badge_radius, 1)
                    badge_rect = badge_surf.get_rect(center=badge_center)
                    self.screen.blit(badge_surf, badge_rect)
            else:
                pygame.draw.rect(self.screen, color, rect, border_radius=4)
                pygame.draw.rect(self.screen, (20, 20, 20), rect, 1, border_radius=4)
                fitted_label = fit_status_icon_label(font, label, icon_w - 6)
                text_surf = font.render(fitted_label, True, (255, 255, 255))
                text_rect = text_surf.get_rect(center=rect.center)
                self.screen.blit(text_surf, text_rect)

        rows = (len(visible_icons) + per_row - 1) // per_row
        return y_offset + rows * (icon_h + padding)

    def _render_character_info(self, player_char, y_offset):
        """Render character name, race, class, and level."""
        x_margin = self.hud_x + 20

        # Name
        name_text = self.title_font.render(player_char.name, True, (255, 215, 0))
        self.screen.blit(name_text, (x_margin, y_offset))
        y_offset += 35

        # Race and Class
        race_name = player_char.race.name if getattr(player_char, "race", None) else "Unknown"
        class_name = player_char.cls.name if getattr(player_char, "cls", None) else "Unknown"
        info_text = f"{race_name} {class_name}"
        info_surface = self.stat_font.render(info_text, True, self.text_color)
        self.screen.blit(info_surface, (x_margin, y_offset))
        y_offset += 30

        # Level and XP
        level_text = f"Level {player_char.level.level}"
        level_surface = self.stat_font.render(level_text, True, self.exp_color)
        self.screen.blit(level_surface, (x_margin, y_offset))
        y_offset += 25

        # XP Bar
        xp_width = self.hud_width - 40

        # Check if player is at max level
        if isinstance(player_char.level.exp_to_gain, str):
            # Max level - show full XP bar
            xp_percent = 1.0
            xp_text = "MAX LEVEL"
        else:
            # Calculate XP progress for current level
            # level_exp() returns total XP needed for current level
            # exp_to_gain counts down from level_exp() to 0
            # So progress = level_exp() - exp_to_gain
            total_xp_for_level = player_char.level_exp()
            current_progress = total_xp_for_level - player_char.level.exp_to_gain
            xp_percent = min(1.0, max(0.0, current_progress / max(1, total_xp_for_level)))
            xp_text = f"{current_progress}/{total_xp_for_level} XP"

        # XP bar background
        pygame.draw.rect(self.screen, (40, 40, 45), pygame.Rect(x_margin, y_offset, xp_width, 15))
        # XP bar fill
        pygame.draw.rect(
            self.screen,
            self.exp_color,
            pygame.Rect(x_margin, y_offset, int(xp_width * xp_percent), 15),
        )
        # XP bar border
        pygame.draw.rect(
            self.screen, self.border_color, pygame.Rect(x_margin, y_offset, xp_width, 15), 1
        )

        # XP text - show progress toward next level
        xp_surface = self.small_font.render(xp_text, True, self.text_color)
        text_x = x_margin + (xp_width - xp_surface.get_width()) // 2
        self.screen.blit(xp_surface, (text_x, y_offset - 1))
        y_offset += 20

        return y_offset

    @staticmethod
    def _is_living_active_summon(active_summon) -> bool:
        if active_summon is None:
            return False
        is_alive = getattr(active_summon, "is_alive", None)
        return bool(is_alive()) if callable(is_alive) else True

    def _render_resource_pair(
        self,
        character,
        y_offset,
        *,
        bar_width: int,
        bar_height: int,
        x_margin: int,
        font,
        label_prefix: str = "",
        border_width: int = 2,
        row_gap: int = 10,
    ):
        """Render HP and MP bars for a combatant and return the next y offset."""
        health = getattr(character, "health", None)
        mana = getattr(character, "mana", None)
        hp_current = getattr(health, "current", 0)
        hp_max = max(1, getattr(health, "max", 0))
        mp_current = getattr(mana, "current", 0)
        mp_max = max(1, getattr(mana, "max", 0))

        hp_percent = hp_current / hp_max
        hp_text = f"{label_prefix}HP: {hp_current}/{hp_max}"

        pygame.draw.rect(
            self.screen, (40, 40, 45), pygame.Rect(x_margin, y_offset, bar_width, bar_height)
        )
        pygame.draw.rect(
            self.screen,
            self.hp_color,
            pygame.Rect(x_margin, y_offset, int(bar_width * hp_percent), bar_height),
        )
        pygame.draw.rect(
            self.screen,
            self.border_color,
            pygame.Rect(x_margin, y_offset, bar_width, bar_height),
            border_width,
        )

        hp_surface = font.render(hp_text, True, (255, 255, 255))
        text_x = x_margin + (bar_width - hp_surface.get_width()) // 2
        self.screen.blit(
            hp_surface, (text_x, y_offset + max(1, (bar_height - hp_surface.get_height()) // 2))
        )
        y_offset += bar_height + row_gap

        mp_percent = mp_current / mp_max
        mp_text = f"{label_prefix}MP: {mp_current}/{mp_max}"

        pygame.draw.rect(
            self.screen, (40, 40, 45), pygame.Rect(x_margin, y_offset, bar_width, bar_height)
        )
        pygame.draw.rect(
            self.screen,
            self.mp_color,
            pygame.Rect(x_margin, y_offset, int(bar_width * mp_percent), bar_height),
        )
        pygame.draw.rect(
            self.screen,
            self.border_color,
            pygame.Rect(x_margin, y_offset, bar_width, bar_height),
            border_width,
        )

        mp_surface = font.render(mp_text, True, (255, 255, 255))
        text_x = x_margin + (bar_width - mp_surface.get_width()) // 2
        self.screen.blit(
            mp_surface, (text_x, y_offset + max(1, (bar_height - mp_surface.get_height()) // 2))
        )
        return y_offset + bar_height

    def _render_resource_bars(self, player_char, y_offset, active_summon=None):
        """Render player HP/MP bars."""
        x_margin = self.hud_x + 20
        bar_width = self.hud_width - 40
        bar_height = 25

        y_offset = self._render_resource_pair(
            player_char,
            y_offset,
            bar_width=bar_width,
            bar_height=bar_height,
            x_margin=x_margin,
            font=self.stat_font,
            row_gap=10,
        )
        y_offset += 5

        return y_offset

    def _render_stats(self, player_char, y_offset):
        """Render character statistics."""
        x_margin = self.hud_x + 20

        # Title
        stats_title = self.stat_font.render("Stats", True, (200, 200, 50))
        self.screen.blit(stats_title, (x_margin, y_offset))
        y_offset += 28

        # Stats
        stats = [
            ("STR", player_char.stats.strength),
            ("INT", player_char.stats.intel),
            ("WIS", player_char.stats.wisdom),
            ("CON", player_char.stats.con),
            ("DEX", player_char.stats.dex),
            ("CHA", player_char.stats.charisma),
        ]

        # Render in two columns
        col_width = (self.hud_width - 40) // 2
        for i, (stat_name, stat_value) in enumerate(stats):
            col = i % 2
            row = i // 2
            x = x_margin + (col * col_width)
            y = y_offset + (row * 22)

            stat_text = f"{stat_name}: {stat_value}"
            stat_surface = self.small_font.render(stat_text, True, self.text_color)
            self.screen.blit(stat_surface, (x, y))

        y_offset += (len(stats) // 2 + 1) * 22
        return y_offset

    def _minimap_size(self, combat_mode: bool = False) -> int:
        max_size = max(80, self.hud_width - 40)
        if combat_mode:
            return min(max_size, max(220, self.height - 420))
        return min(max_size, max(220, self.height - 450))

    def _minimap_title_y(self, minimap_size: int) -> int:
        return max(20, self.height - minimap_size - 52)

    def _combat_feature_height(self) -> int:
        return min(max(190, self.height - 420), 260)

    def _combat_feature_title_y(self, feature_height: int) -> int:
        return max(20, self.height - feature_height - 52)

    @staticmethod
    def _truncate_text(font, text: str, max_width: int) -> str:
        text = str(text)

        def width(value: str) -> int:
            size = getattr(font, "size", None)
            if callable(size):
                return size(value)[0]
            return font.render(value, True, (255, 255, 255)).get_width()

        if width(text) <= max_width:
            return text
        ellipsis = "..."
        while text and width(text + ellipsis) > max_width:
            text = text[:-1]
        return text + ellipsis if text else ellipsis

    @staticmethod
    def _level_value(entity) -> int | None:
        level = getattr(entity, "level", None)
        for attr in ("level", "pro_level"):
            value = getattr(level, attr, None)
            if value is not None:
                try:
                    return int(value)
                except (TypeError, ValueError):
                    return None
        return None

    @staticmethod
    def _totem_effect(player_char):
        try:
            effect = player_char.magic_effects.get("Totem")
        except AttributeError:
            return None
        return effect if effect and getattr(effect, "active", False) else None

    @staticmethod
    def _totem_summary(effect) -> tuple[str, str]:
        extra = getattr(effect, "extra", None)
        if not isinstance(extra, dict):
            return "Totem", "Active"
        aspect = str(extra.get("aspect") or "Totem")
        secondary_labels = {
            "reflect": "Reflect",
            "healing": "Healing",
            "elemental": "Elemental",
            "speed": "Speed",
            "crit_damage": "Crit Dmg",
        }
        benefits = []
        try:
            attack_bonus = float(extra.get("attack_bonus", 0) or 0)
            defense_bonus = float(extra.get("defense_bonus", 0) or 0)
        except (TypeError, ValueError):
            attack_bonus = defense_bonus = 0
        if attack_bonus > 0:
            benefits.append(f"+{int(attack_bonus * 100)}% ATK")
        if defense_bonus > 0:
            benefits.append(f"+{int(defense_bonus * 100)}% DEF")
        secondary = secondary_labels.get(extra.get("secondary"))
        if secondary:
            benefits.append(secondary)
        return f"{aspect} Totem", ", ".join(benefits) or "Active"

    def _class_kit_feature_color(self, label: str) -> tuple[int, int, int]:
        if label in {"Ring Ready", "Ring Preserve"}:
            return (248, 226, 142)
        if label in {"Fortune", "Threads", "Devotion", "Prayer", "Ki", "Crescendo"}:
            return (230, 205, 120)
        if label in {"Misfortune", "Backlash", "Death Mark", "Corruption"}:
            return (220, 150, 150)
        if label in {
            "Aerial Tempo",
            "Foundation",
            "Accent",
            "Weave",
            "Spellbind",
            "Revelation",
            "Stolen Charge",
            "Conduit",
        }:
            return (170, 210, 255)
        if label in {
            "Companion",
            "Xenid Bond",
            "Xenid Conduit",
            "Command",
            "Patron",
            "Echo",
        }:
            return (170, 210, 255)
        return self.text_color

    @staticmethod
    def _blade_charge_counts(value: str) -> tuple[int, int]:
        """Parse stable typed Blade Charge status text for the HUD meter."""
        arcane_match = re.search(r"Arcane\s+×(\d+)", value)
        elemental_match = re.search(r"Elemental\s+×(\d+)", value)
        return (
            int(arcane_match.group(1)) if arcane_match else 0,
            int(elemental_match.group(1)) if elemental_match else 0,
        )

    def _render_blade_charge_glyph(
        self,
        center: tuple[int, int],
        charge_type: str,
        active: bool,
        maxed: bool = False,
    ) -> None:
        """Render a lit or dormant Arcane/Elemental charge glyph."""
        if charge_type == "Arcane":
            bright = (160, 116, 255)
            dim = (52, 43, 66)
        else:
            bright = (245, 152, 54)
            dim = (64, 48, 35)
        color = bright if active else dim
        outline = tuple(min(255, component + (38 if active else 15)) for component in color)
        if maxed:
            pulse = (pygame.time.get_ticks() // 180) % 2
            pygame.draw.circle(
                self.screen,
                (255, 232, 145) if pulse else outline,
                center,
                12,
                2,
            )
        if active:
            pygame.draw.circle(self.screen, (*bright, 42), center, 11)
        pygame.draw.circle(self.screen, (18, 18, 24), center, 9)
        pygame.draw.circle(self.screen, color, center, 8)
        pygame.draw.circle(self.screen, outline, center, 8, 1)
        if charge_type == "Arcane":
            points = [
                (center[0], center[1] - 5),
                (center[0] + 2, center[1] - 1),
                (center[0] + 5, center[1]),
                (center[0] + 2, center[1] + 1),
                (center[0], center[1] + 5),
                (center[0] - 2, center[1] + 1),
                (center[0] - 5, center[1]),
                (center[0] - 2, center[1] - 1),
            ]
            pygame.draw.polygon(self.screen, (224, 211, 255) if active else (88, 78, 102), points)
        else:
            flame = [
                (center[0], center[1] - 6),
                (center[0] + 5, center[1] + 3),
                (center[0], center[1] + 6),
                (center[0] - 5, center[1] + 3),
            ]
            pygame.draw.polygon(self.screen, (255, 223, 112) if active else (92, 75, 53), flame)

    @staticmethod
    def _blade_charge_capacity(player_char) -> int:
        skills = getattr(player_char, "spellbook", {}).get("Skills", {})
        return 2 if "Storage Capacity" in skills else 1

    def _render_blade_charge_meter(
        self,
        value: str,
        x: int,
        y: int,
        max_width: int,
        *,
        capacity: int = 1,
    ) -> None:
        """Render both typed Blade Charge pools, including empty pools."""
        arcane, elemental = self._blade_charge_counts(value)
        segment_width = max(72, max_width // 2)
        entries = (
            ("Arcane", arcane, x),
            ("Elemental", elemental, x + segment_width),
        )
        for charge_type, count, entry_x in entries:
            self._render_blade_charge_glyph(
                (entry_x + 9, y + 9),
                charge_type,
                count > 0,
                count >= capacity,
            )
            text_color = (220, 220, 238) if count > 0 else (100, 100, 112)
            available_width = max(42, segment_width - 23)
            text = self._truncate_text(
                self.small_font,
                f"{charge_type} ×{count}",
                available_width,
            )
            surface = self.small_font.render(text, True, text_color)
            self.screen.blit(surface, (entry_x + 22, y))
            if count >= capacity:
                max_surface = self.small_font.render("MAX", True, (255, 225, 135))
                self.screen.blit(max_surface, (entry_x + 22, y + 15))

    @staticmethod
    def _class_kit_row_bucket(label: str) -> int:
        if label == "Ring Preserve":
            return 0
        if label == "Ring Ready":
            return 1
        if label in {
            "Threads",
            "Threaded",
            "Backlash",
            "Shade of Ahool",
            "Blade Charge",
            "Foundation",
            "Accent",
            "Weave",
            "Spellbind",
            "Momentum",
            "Bloodied Momentum",
            "Bloodied State",
            "Scar Cap",
            "Scar Preserve",
            "Conviction",
            "Aerial Tempo",
            "Resolve",
            "Guard Stance",
            "Fortune",
            "Misfortune",
            "Jinx",
            "Revelation",
            "Death Mark",
            "Stolen Charge",
            "Devotion",
            "Prayer",
            "Ki",
            "Crescendo",
            "Harmony",
            "Command",
            "Totem",
            "Conduit",
        }:
            return 2
        return 4

    def _combat_feature_lines(
        self, player_char, enemy=None, active_summon=None
    ) -> list[tuple[str, str, tuple[int, int, int]]]:
        active_rows: list[tuple[str, str, tuple[int, int, int]]] = []
        rich_rows: list[tuple[str, str, tuple[int, int, int]]] = []
        persistent_rows: list[tuple[str, str, tuple[int, int, int]]] = []

        class_name = getattr(getattr(player_char, "cls", None), "name", "")
        affinity_rows: list[tuple[str, str, tuple[int, int, int]]] = []
        if class_name in {"Sorcerer", "Wizard"}:
            affinity = wizard.ensure_affinity(player_char)
            cap = wizard.cap_for(player_char)
            for school in wizard.AFFINITY_SCHOOLS:
                value = float(affinity.get(school, 0) or 0)
                mastered = value >= cap
                affinity_rows.append(
                    (
                        school,
                        f"{value:g}/{cap:g}" + (" MASTERED" if mastered else ""),
                        (248, 226, 142) if mastered else self.text_color,
                    )
                )

        familiar = getattr(player_char, "familiar", None)
        if familiar and getattr(familiar, "spec", "") != "Tamed":
            familiar_name = getattr(familiar, "name", "Familiar")
            spec = getattr(familiar, "spec", "")
            level = self._level_value(familiar)
            suffix = (
                f"{spec} Lv {level}"
                if spec and level is not None
                else spec or (f"Lv {level}" if level is not None else "Ready")
            )
            rich_rows.append(("Familiar", familiar_name, (170, 210, 255)))
            rich_rows.append(("Bond", suffix, self.text_color))

        totem = self._totem_effect(player_char)
        if totem:
            label, benefits = self._totem_summary(totem)
            rich_rows.append(("Totem", label, (230, 205, 120)))
            rich_rows.append(("Benefit", benefits, self.text_color))
            rich_rows.append(("Turns", getattr(totem, "duration", 0), self.text_color))

        class_effects = getattr(player_char, "class_effects", {}) or {}
        for name, effect in class_effects.items():
            if getattr(effect, "active", False):
                rich_rows.append((name, f"{getattr(effect, 'duration', 0)} turns", (200, 190, 255)))

        rich_labels = {label for label, _value, _color in rich_rows}
        for label, value in promotion_kits.status_summary_rows(player_char, target=enemy):
            if label in {"Xenid Bond", "Xenid Conduit"}:
                continue
            if label in rich_labels:
                continue
            row = (label, value, self._class_kit_feature_color(label))
            bucket = self._class_kit_row_bucket(label)
            if bucket < 3:
                active_rows.append(row)
            else:
                persistent_rows.append(row)
        active_rows.sort(key=lambda row: self._class_kit_row_bucket(row[0]))

        lines = [*affinity_rows, *active_rows, *rich_rows, *persistent_rows]
        if not lines and not self._is_living_active_summon(active_summon):
            lines.append(
                (
                    "Focus",
                    "No active combat focuses",
                    self.GRAY if hasattr(self, "GRAY") else (145, 145, 155),
                )
            )
        return lines

    def _render_totem_focus_glyph(self, rect: pygame.Rect, effect) -> None:
        extra = getattr(effect, "extra", None)
        aspect = extra.get("aspect", "Earth") if isinstance(extra, dict) else "Earth"
        colors = {
            "Earth": (142, 104, 62),
            "Water": (78, 156, 212),
            "Fire": (220, 92, 48),
            "Wind": (150, 204, 166),
            "Soul": (180, 122, 220),
        }
        color = colors.get(aspect, (160, 136, 86))
        center_x = rect.right - 44
        base_y = rect.bottom - 30
        pygame.draw.ellipse(
            self.screen, (18, 16, 18), pygame.Rect(center_x - 34, base_y + 12, 68, 16)
        )
        pygame.draw.ellipse(self.screen, color, pygame.Rect(center_x - 42, base_y + 4, 84, 28), 2)
        shaft = pygame.Rect(center_x - 6, base_y - 34, 12, 50)
        pygame.draw.rect(self.screen, color, shaft, border_radius=3)
        pygame.draw.rect(self.screen, (35, 28, 24), shaft, 2, border_radius=3)
        head = pygame.Rect(center_x - 18, base_y - 52, 36, 24)
        pygame.draw.rect(self.screen, tuple(min(255, c + 38) for c in color), head, border_radius=4)
        pygame.draw.rect(self.screen, (35, 28, 24), head, 2, border_radius=4)
        pygame.draw.circle(self.screen, (248, 226, 142), head.center, 4)

    def _render_active_summon_focus(self, active_summon, panel_rect: pygame.Rect, y: int) -> int:
        """Render active summon resources inside Combat Focus."""
        if not self._is_living_active_summon(active_summon):
            return y

        x = panel_rect.left + 12
        width = panel_rect.width - 24
        level = self._level_value(active_summon)
        name = getattr(active_summon, "name", "Summon")
        title = f"{name} Lv {level}" if level is not None else str(name)
        title_surf = self.small_font.render(
            self._truncate_text(self.small_font, title, width), True, (170, 210, 255)
        )
        self.screen.blit(title_surf, (x, y))
        y += title_surf.get_height() + 3

        level_obj = getattr(active_summon, "level", None)
        exp_to_gain = getattr(level_obj, "exp_to_gain", 0)
        if isinstance(exp_to_gain, str):
            xp_percent = 1.0
            xp_text = "MAX LEVEL"
        else:
            try:
                creature_level = max(1, int(getattr(level_obj, "level", 1) or 1))
                pro_level = max(1, int(getattr(level_obj, "pro_level", 1) or 1))
                exp_scale = max(1, int(getattr(active_summon, "exp_scale", 1000) or 1000))
                total_xp = max(1, pro_level * exp_scale * creature_level)
                remaining = max(0, int(exp_to_gain or 0))
            except (TypeError, ValueError):
                total_xp = 1
                remaining = 0
            progress = max(0, min(total_xp, total_xp - remaining))
            xp_percent = progress / total_xp
            xp_text = f"{progress}/{total_xp} XP"

        xp_rect = pygame.Rect(x, y, width, 10)
        pygame.draw.rect(self.screen, (40, 40, 45), xp_rect)
        pygame.draw.rect(
            self.screen, self.exp_color, pygame.Rect(x, y, int(width * xp_percent), 10)
        )
        pygame.draw.rect(self.screen, self.border_color, xp_rect, 1)
        xp_surf = self.small_font.render(
            self._truncate_text(self.small_font, xp_text, width), True, self.text_color
        )
        self.screen.blit(xp_surf, (x + max(0, (width - xp_surf.get_width()) // 2), y - 5))
        y += 16

        y = self._render_resource_pair(
            active_summon,
            y,
            bar_width=width,
            bar_height=13,
            x_margin=x,
            font=self.small_font,
            border_width=1,
            row_gap=4,
        )
        y = self._render_status_icons(active_summon, y, max_rows=1)
        return y + 9

    def _render_combat_features(
        self,
        player_char,
        enemy,
        y_offset,
        feature_height=None,
        active_summon=None,
        combat_resources=(),
    ):
        """Render combat-relevant class systems in place of the exploration minimap."""
        x_margin = self.hud_x + 20
        panel_width = self.hud_width - 40
        feature_height = feature_height or self._combat_feature_height()
        title = self.stat_font.render("Combat Focus", True, (150, 150, 255))
        self.screen.blit(title, (x_margin, y_offset))
        panel_rect = pygame.Rect(x_margin, y_offset + 30, panel_width, feature_height - 30)
        pygame.draw.rect(self.screen, (15, 15, 20), panel_rect)
        pygame.draw.rect(self.screen, self.border_color, panel_rect, 2)

        y = panel_rect.top + 12
        y = self._render_active_summon_focus(active_summon, panel_rect, y)
        if combat_resources:
            lines = [
                (
                    resource.label,
                    resource.state_text or "Ready" if resource.ready else resource.state_text,
                    (248, 226, 142) if resource.ready else self.text_color,
                )
                for resource in sorted(combat_resources, key=lambda resource: resource.priority)
            ]
            max_lines = 3
            if len(lines) > max_lines:
                lines = [
                    *lines[:max_lines],
                    ("More", f"+{len(lines) - max_lines} details", self.text_color),
                ]
                max_lines += 1
        else:
            lines = self._combat_feature_lines(player_char, enemy, active_summon=active_summon)
            max_lines = 4 if self._is_living_active_summon(active_summon) else 7
        visible_lines = lines[:max_lines]
        label_gap = 10
        label_widths = [
            self.small_font.render(f"{label}:", True, (170, 170, 180)).get_width()
            for label, _value, _color in visible_lines
        ]
        max_label_w = max(label_widths, default=68)
        label_w = min(max(78, max_label_w + label_gap), max(78, panel_rect.width - 120))
        max_value_w = max(60, panel_rect.width - label_w - 26)
        for label, value, color in visible_lines:
            if y + 20 > panel_rect.bottom - 12:
                break
            row_height = 22
            label_surf = self.small_font.render(f"{label}:", True, (170, 170, 180))
            self.screen.blit(label_surf, (panel_rect.left + 12, y))
            value_x = panel_rect.left + 12 + label_w
            if label in {"Fortune", "Misfortune"}:
                self._render_coin_meter(label, str(value), value_x, y + 10, max_value_w)
            elif label == "Resolve":
                self._render_focus_meter(
                    str(value), value_x, y + 10, max_value_w, fill_color=(190, 55, 55)
                )
            elif label == "Blade Charge":
                self._render_blade_charge_meter(
                    str(value),
                    panel_rect.left + 12,
                    y + 20,
                    panel_rect.width - 24,
                    capacity=self._blade_charge_capacity(player_char),
                )
                row_height = 42
            else:
                value_text = self._truncate_text(self.small_font, str(value), max_value_w)
                value_font = (
                    self.small_bold_font if str(value).endswith(" MASTERED") else self.small_font
                )
                value_surf = value_font.render(value_text, True, color)
                self.screen.blit(value_surf, (value_x, y))
            y += row_height

        totem = self._totem_effect(player_char)
        if totem:
            self._render_totem_focus_glyph(panel_rect, totem)

        return panel_rect.bottom + 5

    def _render_coin_meter(
        self, label: str, value: str, x: int, center_y: int, max_width: int
    ) -> None:
        try:
            active_text, cap_text = value.split("/", 1)
            active = max(0, int(active_text))
            cap = max(1, int(str(cap_text).split()[0]))
        except (AttributeError, TypeError, ValueError):
            active, cap = 0, 3
        cap = min(cap, max(1, max_width // 18))
        active = min(active, cap)
        radius = 7
        gap = 4
        active_color = (232, 196, 72) if label == "Fortune" else (176, 70, 82)
        inactive_color = (82, 82, 88)
        mark = "H" if label == "Fortune" else "T"
        for index in range(cap):
            cx = x + radius + index * ((radius * 2) + gap)
            color = active_color if index < active else inactive_color
            pygame.draw.circle(self.screen, color, (cx, center_y), radius)
            pygame.draw.circle(self.screen, (32, 28, 24), (cx, center_y), radius, 1)
            mark_color = (42, 30, 20) if index < active else (145, 145, 150)
            mark_surf = self.small_font.render(mark, True, mark_color)
            mark_rect = mark_surf.get_rect(center=(cx, center_y))
            self.screen.blit(mark_surf, mark_rect)

    def _render_focus_meter(
        self, value: str, x: int, center_y: int, max_width: int, *, fill_color
    ) -> None:
        try:
            active_text, cap_text = value.split("/", 1)
            active = max(0, int(active_text))
            cap = max(1, int(str(cap_text).split()[0]))
        except (AttributeError, TypeError, ValueError):
            active, cap = 0, 1
        width = max(150, min(max_width, 220))
        height = 18
        rect = pygame.Rect(x, center_y - height // 2, width, height)
        fill_width = int(width * (min(active, cap) / cap))
        pygame.draw.rect(self.screen, (40, 40, 45), rect)
        if fill_width > 0:
            pygame.draw.rect(
                self.screen, fill_color, pygame.Rect(rect.left, rect.top, fill_width, rect.height)
            )
        pygame.draw.rect(self.screen, self.border_color, rect, 1)
        value_text = f"{active}/{cap}"
        value_surf = self.small_font.render(value_text, True, self.text_color)
        self.screen.blit(value_surf, value_surf.get_rect(center=rect.center))

    def _render_minimap(
        self,
        player_char,
        y_offset,
        minimap_size=None,
        *,
        x_margin: int | None = None,
        title: str = "Map",
        full_level: bool = False,
    ):
        """Render minimap showing nearby explored areas."""
        x_margin = self.hud_x + 20 if x_margin is None else x_margin
        minimap_size = minimap_size or min(200, self.hud_width - 40)
        visible_adjacent = self._get_visible_adjacent_positions(player_char)

        # Title
        if title:
            map_title = self.stat_font.render(title, True, (150, 150, 255))
            self.screen.blit(map_title, (x_margin, y_offset))
            y_offset += 28

        # Minimap background
        minimap_rect = pygame.Rect(x_margin, y_offset, minimap_size, minimap_size)
        self.last_minimap_rect = minimap_rect
        pygame.draw.rect(self.screen, (15, 15, 20), minimap_rect)
        pygame.draw.rect(self.screen, self.border_color, minimap_rect, 2)

        player_x, player_y = player_char.location_x, player_char.location_y

        if full_level:
            positions = self._revealed_level_minimap_positions(player_char, visible_adjacent)
            if not positions:
                positions = [(player_x, player_y)]
            min_x = min(x for x, _y in positions)
            max_x = max(x for x, _y in positions)
            min_y = min(y for _x, y in positions)
            max_y = max(y for _x, y in positions)
            grid_width = max(1, max_x - min_x + 1)
            grid_height = max(1, max_y - min_y + 1)
            tile_size = max(3, min(minimap_size // grid_width, minimap_size // grid_height))
            map_width = grid_width * tile_size
            map_height = grid_height * tile_size
            origin_x = x_margin + (minimap_size - map_width) // 2
            origin_y = y_offset + (minimap_size - map_height) // 2
            x_values = range(min_x, max_x + 1)
            y_values = range(min_y, max_y + 1)
        else:
            tile_size = minimap_size // 11  # Show 11x11 grid
            origin_x = x_margin
            origin_y = y_offset
            x_values = range(player_x - 5, player_x + 6)
            y_values = range(player_y - 5, player_y + 6)

        for tile_y in y_values:
            for tile_x in x_values:
                tile = player_char.world_dict.get((tile_x, tile_y, player_char.location_z))
                if tile and self._is_concealed_trial_room(player_char, tile_x, tile_y, tile):
                    tile = None

                if full_level:
                    screen_x = origin_x + (tile_x - min_x) * tile_size
                    screen_y = origin_y + (tile_y - min_y) * tile_size
                else:
                    screen_x = origin_x + (tile_x - (player_x - 5)) * tile_size
                    screen_y = origin_y + (tile_y - (player_y - 5)) * tile_size
                tile_rect = pygame.Rect(screen_x, screen_y, tile_size - 1, tile_size - 1)

                if tile:
                    tile_type = type(tile).__name__
                    is_funhouse_wall = tile_type in ("FunhouseWall", "MirrorWall")
                    is_fake_wall = self._is_fake_wall_tile(tile)
                    is_directly_visible = (tile_x, tile_y) in visible_adjacent
                    is_discovered_explorable = bool(
                        getattr(tile, "near", False)
                        and getattr(tile, "enter", True)
                        and not is_fake_wall
                        and not is_funhouse_wall
                    )
                    is_wall_tile = bool(
                        not getattr(tile, "enter", True) or is_fake_wall or is_funhouse_wall
                    )
                    is_discovered_special = bool(
                        getattr(tile, "near", False)
                        and (
                            any(
                                marker in tile_type
                                for marker in (
                                    "Chest",
                                    "Stairs",
                                    "Ladder",
                                    "Door",
                                    "WarpPoint",
                                    "UndergroundSpring",
                                    "SecretShop",
                                    "Relic",
                                )
                            )
                            or (
                                "GoldenChaliceRoom" in tile_type
                                and map_tiles.chalice_altar_visible(player_char)
                            )
                        )
                    )

                    if tile_x == player_x and tile_y == player_y:
                        # Player position - draw base tile first, then player marker with arrow
                        if getattr(tile, "visited", False):
                            if is_funhouse_wall or not getattr(tile, "enter", True):
                                pygame.draw.rect(self.screen, (80, 80, 90), tile_rect)
                            else:
                                pygame.draw.rect(self.screen, (120, 120, 130), tile_rect)
                        self._render_minimap_player_marker(tile_rect, player_char.facing, tile_size)

                    elif (
                        getattr(tile, "visited", False)
                        or (is_directly_visible and not is_wall_tile)
                        or is_discovered_explorable
                        or is_discovered_special
                    ):
                        # Explored tile (visited) or directly visible adjacent tile
                        is_visited = getattr(tile, "visited", False)
                        is_near = getattr(tile, "near", False)
                        is_fire_path = tile_type in ("FirePath", "FirePathSpecial")
                        if is_fake_wall:
                            # Keep FakeWall hidden unless actually visited
                            if is_visited:
                                pygame.draw.rect(self.screen, (150, 100, 150), tile_rect)
                            else:
                                pygame.draw.rect(self.screen, (80, 80, 90), tile_rect)
                        elif is_funhouse_wall:
                            wall_color = (130, 90, 145) if is_visited else (85, 70, 95)
                            pygame.draw.rect(self.screen, wall_color, tile_rect)
                        elif is_fire_path:
                            # FirePath stays visually distinct as soon as it is discovered.
                            pygame.draw.rect(self.screen, (175, 55, 55), tile_rect)
                        elif is_discovered_special and not is_visited:
                            # Persist discovered special tiles without re-enabling broad near-tile shading
                            pygame.draw.rect(self.screen, (100, 100, 110), tile_rect)
                        elif not getattr(tile, "enter", True):
                            # Wall
                            wall_color = (80, 80, 90) if is_visited else (70, 70, 80)
                            pygame.draw.rect(self.screen, wall_color, tile_rect)
                        else:
                            # Corridor
                            if is_visited:
                                corridor_color = (120, 120, 130)
                            elif is_near:
                                corridor_color = (105, 105, 115)
                            else:
                                corridor_color = (95, 95, 105)
                            pygame.draw.rect(self.screen, corridor_color, tile_rect)

                        if self._is_minimap_special_tile(tile_type, tile, player_char):
                            self._render_minimap_special_outline(tile_rect, tile_size)

                        # Draw icons for special features on visible/discovered tiles
                        if "Chest" in tile_type:
                            self._render_minimap_chest_icon(tile, screen_x, screen_y, tile_size)

                        if "Door" in tile_type:
                            self._render_minimap_door_icon(tile, screen_x, screen_y, tile_size)

                        if "Relic" in tile_type and not getattr(tile, "read", False):
                            # Relic (uncollected) - cyan/bright blue diamond
                            icon_size = tile_size // 3
                            center_x = screen_x + tile_size // 2
                            center_y = screen_y + tile_size // 2
                            points = [
                                (center_x, center_y - icon_size // 2),
                                (center_x + icon_size // 2, center_y),
                                (center_x, center_y + icon_size // 2),
                                (center_x - icon_size // 2, center_y),
                            ]
                            pygame.draw.polygon(self.screen, (0, 255, 255), points)

                        if "RelicRoom" in tile_type and getattr(tile, "read", False):
                            self._render_minimap_spent_relic_altar_icon(
                                screen_x, screen_y, tile_size
                            )

                        if "GoldenChaliceRoom" in tile_type and map_tiles.chalice_altar_visible(
                            player_char
                        ):
                            # Chalice altar - warm gold cup marker
                            icon_width = max(2, tile_size // 2)
                            icon_height = max(2, tile_size // 3)
                            icon_x = screen_x + (tile_size - icon_width) // 2
                            icon_y = screen_y + (tile_size - icon_height) // 2
                            chalice_color = (
                                (196, 160, 70) if getattr(tile, "read", False) else (255, 215, 0)
                            )
                            pygame.draw.rect(
                                self.screen,
                                chalice_color,
                                pygame.Rect(
                                    icon_x,
                                    icon_y + icon_height // 3,
                                    icon_width,
                                    max(2, icon_height // 2),
                                ),
                            )
                            stem_width = max(1, icon_width // 4)
                            stem_height = max(2, icon_height // 3)
                            stem_x = screen_x + (tile_size - stem_width) // 2
                            stem_y = icon_y + icon_height // 3
                            pygame.draw.rect(
                                self.screen,
                                chalice_color,
                                pygame.Rect(stem_x, stem_y, stem_width, stem_height),
                            )

                        if "UndergroundSpring" in tile_type:
                            # Spring marker - cyan circle
                            icon_radius = max(2, tile_size // 4)
                            center = (screen_x + tile_size // 2, screen_y + tile_size // 2)
                            pygame.draw.circle(self.screen, (0, 200, 255), center, icon_radius)

                        if "SecretShop" in tile_type:
                            # Secret shop marker - magenta square
                            icon_size = max(2, tile_size // 3)
                            icon_x = screen_x + (tile_size - icon_size) // 2
                            icon_y = screen_y + (tile_size - icon_size) // 2
                            pygame.draw.rect(
                                self.screen,
                                (200, 80, 200),
                                pygame.Rect(icon_x, icon_y, icon_size, icon_size),
                            )

                        if "WarpPoint" in tile_type:
                            # Warp point / teleporter - green star
                            icon_size = tile_size // 3
                            center_x = screen_x + tile_size // 2
                            center_y = screen_y + tile_size // 2
                            # Draw 5-pointed star
                            import math

                            star_points = []
                            for i in range(5):
                                angle = math.radians(i * 72 - 90)  # Start from top
                                x = center_x + int(icon_size * math.cos(angle))
                                y = center_y + int(icon_size * math.sin(angle))
                                star_points.append((x, y))
                            # Draw star by connecting every other point
                            star_order = [0, 2, 4, 1, 3, 0]
                            star_lines = [
                                star_points[star_order[i]] for i in range(len(star_order))
                            ]
                            pygame.draw.polygon(self.screen, (50, 255, 50), star_lines)

                        if "StairsDown" in tile_type or "LadderDown" in tile_type:
                            # Stairs/Ladder down - red downward arrow
                            icon_size = tile_size // 3
                            center_x = screen_x + tile_size // 2
                            center_y = screen_y + tile_size // 2
                            points = [
                                (center_x, center_y + icon_size // 2),
                                (center_x - icon_size // 2, center_y - icon_size // 3),
                                (center_x + icon_size // 2, center_y - icon_size // 3),
                            ]
                            pygame.draw.polygon(self.screen, (255, 50, 50), points)

                        if "StairsUp" in tile_type or "LadderUp" in tile_type:
                            # Stairs/Ladder up - green upward arrow
                            icon_size = tile_size // 3
                            center_x = screen_x + tile_size // 2
                            center_y = screen_y + tile_size // 2
                            points = [
                                (center_x, center_y - icon_size // 2),
                                (center_x - icon_size // 2, center_y + icon_size // 3),
                                (center_x + icon_size // 2, center_y + icon_size // 3),
                            ]
                            pygame.draw.polygon(self.screen, (50, 255, 50), points)

        y_offset += minimap_size + 5
        return y_offset

    @staticmethod
    def _is_minimap_special_tile(tile_type: str, tile, player_char) -> bool:
        if any(
            marker in tile_type
            for marker in (
                "Chest",
                "Stairs",
                "Ladder",
                "Door",
                "WarpPoint",
                "UndergroundSpring",
                "SecretShop",
                "Relic",
            )
        ):
            return True
        return "GoldenChaliceRoom" in tile_type and map_tiles.chalice_altar_visible(player_char)

    def _render_minimap_special_outline(self, tile_rect: pygame.Rect, tile_size: int) -> None:
        width = max(1, tile_size // 8)
        pygame.draw.rect(self.screen, (220, 180, 80), tile_rect, width)

    def _render_minimap_spent_relic_altar_icon(
        self, screen_x: int, screen_y: int, tile_size: int
    ) -> None:
        pad = max(2, tile_size // 5)
        base_h = max(2, tile_size // 5)
        base_rect = pygame.Rect(
            screen_x + pad,
            screen_y + tile_size - pad - base_h,
            max(2, tile_size - pad * 2),
            base_h,
        )
        pillar_rect = pygame.Rect(
            screen_x + tile_size // 2 - max(1, tile_size // 10),
            screen_y + pad,
            max(2, tile_size // 5),
            max(2, tile_size - pad * 2 - base_h),
        )
        pygame.draw.rect(self.screen, (72, 72, 80), pillar_rect)
        pygame.draw.rect(self.screen, (165, 145, 88), pillar_rect, max(1, tile_size // 10))
        pygame.draw.rect(self.screen, (72, 72, 80), base_rect)
        pygame.draw.rect(self.screen, (165, 145, 88), base_rect, max(1, tile_size // 10))

    @staticmethod
    def _minimap_blink_on() -> bool:
        return (pygame.time.get_ticks() // 350) % 2 == 0

    def _render_minimap_player_marker(
        self, tile_rect: pygame.Rect, facing: str, tile_size: int
    ) -> None:
        blink_on = self._minimap_blink_on()
        fill = (255, 255, 110) if blink_on else (245, 185, 35)
        outline = (255, 255, 255) if blink_on else (150, 110, 20)
        pygame.draw.rect(self.screen, fill, tile_rect)
        pygame.draw.rect(self.screen, outline, tile_rect, max(1, tile_size // 6))

        center_x = tile_rect.x + tile_size // 2
        center_y = tile_rect.y + tile_size // 2
        arrow_size = max(3, tile_size // 3)

        if facing == "north":
            points = [
                (center_x, center_y - arrow_size),
                (center_x - arrow_size // 2, center_y + arrow_size // 2),
                (center_x + arrow_size // 2, center_y + arrow_size // 2),
            ]
        elif facing == "south":
            points = [
                (center_x, center_y + arrow_size),
                (center_x - arrow_size // 2, center_y - arrow_size // 2),
                (center_x + arrow_size // 2, center_y - arrow_size // 2),
            ]
        elif facing == "east":
            points = [
                (center_x + arrow_size, center_y),
                (center_x - arrow_size // 2, center_y - arrow_size // 2),
                (center_x - arrow_size // 2, center_y + arrow_size // 2),
            ]
        else:  # west
            points = [
                (center_x - arrow_size, center_y),
                (center_x + arrow_size // 2, center_y - arrow_size // 2),
                (center_x + arrow_size // 2, center_y + arrow_size // 2),
            ]

        pygame.draw.polygon(self.screen, (0, 0, 0), points)

    def _revealed_level_minimap_positions(
        self, player_char, visible_adjacent: set[tuple[int, int]]
    ) -> set[tuple[int, int]]:
        """Return current-level positions visible enough for the enlarged map."""
        positions: set[tuple[int, int]] = {(player_char.location_x, player_char.location_y)}
        current_z = player_char.location_z
        for (tile_x, tile_y, tile_z), tile in getattr(player_char, "world_dict", {}).items():
            if tile_z != current_z or tile is None:
                continue
            if self._minimap_tile_is_revealed(player_char, tile_x, tile_y, tile, visible_adjacent):
                positions.add((tile_x, tile_y))
        return positions

    @staticmethod
    def _minimap_tile_is_revealed(
        player_char, tile_x: int, tile_y: int, tile, visible_adjacent: set[tuple[int, int]]
    ) -> bool:
        if DungeonHUD._is_concealed_trial_room(player_char, tile_x, tile_y, tile):
            return False
        tile_type = type(tile).__name__
        is_fake_wall = DungeonHUD._is_fake_wall_tile(tile)
        is_funhouse_wall = tile_type in ("FunhouseWall", "MirrorWall")
        tile_is_wall = bool(not getattr(tile, "enter", True) or is_fake_wall or is_funhouse_wall)
        if getattr(tile, "visited", False):
            return True
        if (tile_x, tile_y) in visible_adjacent and not tile_is_wall:
            return True
        if (
            getattr(tile, "near", False)
            and getattr(tile, "enter", True)
            and not is_fake_wall
            and not is_funhouse_wall
        ):
            return True
        if not getattr(tile, "near", False):
            return False
        special_markers = (
            "Chest",
            "Stairs",
            "Ladder",
            "Door",
            "WarpPoint",
            "UndergroundSpring",
            "SecretShop",
            "Relic",
        )
        if any(marker in tile_type for marker in special_markers):
            return True
        return "GoldenChaliceRoom" in tile_type and map_tiles.chalice_altar_visible(player_char)

    def enlarged_map_rect(self) -> pygame.Rect:
        """Return the modal panel rectangle for the enlarged minimap."""
        panel_width = min(int(self.width * 0.78), 720)
        panel_height = min(int(self.height * 0.82), 680)
        return pygame.Rect(
            (self.width - panel_width) // 2,
            (self.height - panel_height) // 2,
            panel_width,
            panel_height,
        )

    def render_enlarged_minimap_modal(self, player_char) -> pygame.Rect:
        """Render the enlarged minimap modal and return its panel rect."""
        overlay = pygame.Surface((self.width, self.height), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 175))
        self.screen.blit(overlay, (0, 0))

        panel_rect = self.enlarged_map_rect()
        pygame.draw.rect(self.screen, (18, 18, 24), panel_rect)
        pygame.draw.rect(self.screen, self.border_color, panel_rect, 3)

        title = f"{self.location_label(player_char)} Map"
        title_surface = self.stat_font.render(title, True, (220, 205, 145))
        self.screen.blit(title_surface, (panel_rect.left + 24, panel_rect.top + 18))

        close_surface = self.small_font.render("M/Esc: Close", True, self.text_color)
        close_rect = close_surface.get_rect(right=panel_rect.right - 24, top=panel_rect.top + 24)
        self.screen.blit(close_surface, close_rect)

        map_size = min(panel_rect.width - 64, panel_rect.height - 96)
        map_x = panel_rect.centerx - map_size // 2
        map_y = panel_rect.top + 56
        self._render_minimap(
            player_char,
            map_y,
            minimap_size=map_size,
            x_margin=map_x,
            title="",
            full_level=True,
        )
        return panel_rect

    @staticmethod
    def _tile_is_open(tile) -> bool:
        return bool(getattr(tile, "open", False) or getattr(tile, "opened", False))

    def _render_minimap_chest_icon(
        self, tile, screen_x: int, screen_y: int, tile_size: int
    ) -> None:
        icon_size = max(3, tile_size // 3)
        icon_x = screen_x + (tile_size - icon_size) // 2
        icon_y = screen_y + (tile_size - icon_size) // 2
        icon_rect = pygame.Rect(icon_x, icon_y, icon_size, icon_size)

        if self._tile_is_open(tile):
            pygame.draw.rect(self.screen, (130, 130, 120), icon_rect, 1)
            return

        pygame.draw.rect(self.screen, (255, 215, 0), icon_rect)

    def _render_minimap_door_icon(self, tile, screen_x: int, screen_y: int, tile_size: int) -> None:
        icon_width = max(4, tile_size // 2)
        icon_height = max(3, tile_size // 3)
        icon_x = screen_x + (tile_size - icon_width) // 2
        icon_y = screen_y + (tile_size - icon_height) // 2
        icon_rect = pygame.Rect(icon_x, icon_y, icon_width, icon_height)

        if self._tile_is_open(tile):
            pygame.draw.rect(self.screen, (95, 170, 120), icon_rect, 1)
            return

        pygame.draw.rect(self.screen, (139, 69, 19), icon_rect)

    def _get_visible_adjacent_positions(self, player_char):
        """Return adjacent N/S/E/W positions visible from the player's current tile."""
        visible = set()
        player_x, player_y, player_z = (
            player_char.location_x,
            player_char.location_y,
            player_char.location_z,
        )
        current_tile = player_char.world_dict.get((player_x, player_y, player_z))

        directions = {
            "north": (0, -1),
            "south": (0, 1),
            "east": (1, 0),
            "west": (-1, 0),
        }

        for direction, (dx, dy) in directions.items():
            tile_x = player_x + dx
            tile_y = player_y + dy
            adjacent_tile = player_char.world_dict.get((tile_x, tile_y, player_z))
            if adjacent_tile is None:
                continue
            if not self._is_direction_visible_from_tile(current_tile, direction, adjacent_tile):
                continue
            tile_type = type(adjacent_tile).__name__
            if (
                self._is_fake_wall_tile(adjacent_tile)
                or tile_type in ("FunhouseWall", "MirrorWall")
            ) and not getattr(adjacent_tile, "visited", False):
                continue
            if not getattr(adjacent_tile, "enter", True):
                continue
            visible.add((tile_x, tile_y))

        return visible

    @staticmethod
    def _is_fake_wall_tile(tile) -> bool:
        tile_type = type(tile).__name__ if not isinstance(tile, str) else tile
        return tile_type == "FakeWall" or tile_type.endswith("FakeWall")

    @staticmethod
    def _is_concealed_trial_room(player_char, tile_x: int, tile_y: int, tile) -> bool:
        if type(tile).__name__ != "ThievesGuildTrialBossRoom":
            return False
        if getattr(tile, "visited", False):
            return False
        world = getattr(player_char, "world_dict", {})
        z = getattr(player_char, "location_z", 0)
        for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            wall = world.get((tile_x + dx, tile_y + dy, z))
            if type(wall).__name__ == "ThievesGuildTrialFakeWall" and not getattr(
                wall, "visited", False
            ):
                return True
        return False

    def _is_direction_visible_from_tile(self, current_tile, direction, adjacent_tile=None):
        """Return whether a cardinal direction is visible from the current tile."""
        if not current_tile:
            return True

        opposite = {
            "north": "south",
            "south": "north",
            "east": "west",
            "west": "east",
        }

        # Closed doors block line of sight
        if "Door" in type(current_tile).__name__ and not getattr(current_tile, "open", False):
            return False
        if (
            adjacent_tile
            and "Door" in type(adjacent_tile).__name__
            and not getattr(adjacent_tile, "open", False)
        ):
            return False

        blocked = getattr(current_tile, "blocked", None)
        if blocked and blocked.lower() == direction:
            if hasattr(current_tile, "open") and getattr(current_tile, "open", False):
                return True
            return False

        if adjacent_tile:
            adjacent_blocked = getattr(adjacent_tile, "blocked", None)
            opposite_direction = opposite.get(direction)
            if (
                adjacent_blocked
                and opposite_direction
                and adjacent_blocked.lower() == opposite_direction
            ):
                if hasattr(adjacent_tile, "open") and getattr(adjacent_tile, "open", False):
                    return True
                return False

        return True

    def _render_compass(self, player_char, y_offset):
        """Render compass showing current facing direction."""
        x_margin = self.hud_x + 20
        compass_size = 60
        compass_center_x = x_margin + compass_size
        compass_center_y = y_offset + compass_size

        # Compass circle
        pygame.draw.circle(
            self.screen, (30, 30, 35), (compass_center_x, compass_center_y), compass_size
        )
        pygame.draw.circle(
            self.screen, self.border_color, (compass_center_x, compass_center_y), compass_size, 2
        )

        # Cardinal directions
        directions = {
            "N": (0, -compass_size + 15),
            "E": (compass_size - 15, 0),
            "S": (0, compass_size - 15),
            "W": (-compass_size + 15, 0),
        }

        for direction, (dx, dy) in directions.items():
            text_surface = self.small_font.render(direction, True, self.text_color)
            text_rect = text_surface.get_rect(center=(compass_center_x + dx, compass_center_y + dy))
            self.screen.blit(text_surface, text_rect)

        # Facing indicator (arrow)
        facing_map = {
            "north": 0,
            "east": 90,
            "south": 180,
            "west": 270,
        }

        angle = facing_map.get(player_char.facing, 0)
        import math

        rad = math.radians(angle - 90)  # -90 to point upward at 0 degrees
        arrow_length = compass_size - 20

        end_x = compass_center_x + int(arrow_length * math.cos(rad))
        end_y = compass_center_y + int(arrow_length * math.sin(rad))

        pygame.draw.line(
            self.screen, (255, 50, 50), (compass_center_x, compass_center_y), (end_x, end_y), 3
        )
        pygame.draw.circle(self.screen, (255, 50, 50), (end_x, end_y), 5)

        y_offset += compass_size * 2 + 10
        return y_offset

    def _render_quick_info(self, player_char, y_offset):
        """Render quick info like gold, depth, etc."""
        x_margin = self.hud_x + 20

        # Calculate depth - z=0 is town, z=1-6 are dungeon levels 1-6
        if player_char.location_z == 0:
            depth_str = "Town"
        else:
            depth_str = f"Level {player_char.location_z}"

        info_items = [
            f"Gold: {player_char.gold}",
            f"Depth: {depth_str}",
            f"Position: ({player_char.location_x}, {player_char.location_y})",
        ]

        for info in info_items:
            info_surface = self.small_font.render(info, True, self.text_color)
            self.screen.blit(info_surface, (x_margin, y_offset))
            y_offset += 20

        return y_offset

    def _render_combat_indicator(self, enemy, y_offset):
        """Render combat mode indicator at top of HUD."""
        x_margin = self.hud_x + 20

        # Combat banner background
        banner_width = self.hud_width - 40
        banner_height = 50
        banner_rect = pygame.Rect(x_margin - 10, y_offset - 5, banner_width + 20, banner_height)

        # Pulsing effect for combat indicator
        pulse = abs((pygame.time.get_ticks() % 1000) / 1000.0 - 0.5) * 2  # 0 to 1 and back
        alpha = int(150 + pulse * 80)  # 150-230

        # Draw semi-transparent red background
        combat_bg = pygame.Surface((banner_rect.width, banner_rect.height))
        combat_bg.set_alpha(alpha)
        combat_bg.fill((180, 30, 30))
        self.screen.blit(combat_bg, (banner_rect.x, banner_rect.y))

        # Border
        pygame.draw.rect(self.screen, (220, 50, 50), banner_rect, 3)

        # "COMBAT" text
        combat_font = pygame.font.Font(None, 32)
        combat_text = combat_font.render("** COMBAT **", True, (255, 255, 255))
        text_rect = combat_text.get_rect(center=(self.hud_x + self.hud_width // 2, y_offset + 10))
        self.screen.blit(combat_text, text_rect)

        # Enemy name below
        if enemy:
            enemy_font = pygame.font.Font(None, 24)
            player_char = getattr(self, "_combat_indicator_player_char", None)
            has_sight = player_char is not None and player_has_sight(player_char)
            enemy_name = presented_enemy_name(enemy, has_sight)
            enemy_text = enemy_font.render(
                f"vs. {enemy_name}",
                True,
                (255, 200, 200),
            )
            enemy_rect = enemy_text.get_rect(
                center=(self.hud_x + self.hud_width // 2, y_offset + 32)
            )
            self.screen.blit(enemy_text, enemy_rect)

        y_offset += banner_height + 5
        return y_offset
