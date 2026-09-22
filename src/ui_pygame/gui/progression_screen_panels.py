"""Attribute and detail panels for the pygame progression screen."""

from __future__ import annotations

import re

import pygame

from src.core.progression import (
    PRIMARY_ATTRIBUTES,
    TREE_NODES,
    NodeKind,
    effective_node_level_requirement,
)

from .town_base import wrap_text_to_pixel_width


class ProgressionPanelMixin:
    """Render progression attributes, details, and action controls."""

    def _draw_attributes(self, rect):
        self._ensure_staging()
        metrics = self.presenter.layout_metrics
        horizontal_padding = metrics.unit(12)
        row_gap = metrics.unit(6)
        control_size = max(metrics.unit(24), self.small_font.get_height() + metrics.unit(6))
        row_height = max(
            control_size + metrics.unit(8), self.small_font.get_height() + metrics.unit(14)
        )
        self.draw_semi_transparent_panel(rect)
        pygame.draw.rect(self.screen, self.colors.BORDER_COLOR, rect, metrics.stroke(2))
        self.screen.blit(
            self.normal_font.render(
                "Primary Attributes",
                True,
                self.colors.GOLD,
            ),
            (rect.left + metrics.unit(16), rect.top + metrics.unit(12)),
        )
        self.attribute_rects = []
        self.attribute_minus_rects = []
        self.attribute_plus_rects = []
        for index, stat_name in enumerate(PRIMARY_ATTRIBUTES):
            row = pygame.Rect(
                rect.left + horizontal_padding,
                rect.top + metrics.unit(48) + index * (row_height + row_gap),
                rect.width - (horizontal_padding * 2),
                row_height,
            )
            self.attribute_rects.append(row)
            minus_rect = pygame.Rect(
                row.left + metrics.unit(4),
                row.centery - control_size // 2,
                control_size,
                control_size,
            )
            plus_rect = pygame.Rect(
                row.right - metrics.unit(4) - control_size,
                row.centery - control_size // 2,
                control_size,
                control_size,
            )
            self.attribute_minus_rects.append(minus_rect)
            self.attribute_plus_rects.append(plus_rect)
            selected = self.focus == "attributes" and index == self.current_attribute
            if selected:
                pygame.draw.rect(self.screen, self.colors.HIGHLIGHT_BG, row)
            pygame.draw.rect(
                self.screen,
                self.colors.GOLD if selected else self.colors.BORDER_COLOR,
                row,
                1,
            )
            pending = self.pending_attributes.get(stat_name, 0)
            value = getattr(self.player_char.stats, stat_name) + pending
            label = self.STAT_DISPLAY_NAMES[stat_name]
            text = f"{label}: {value} (+{pending})"
            text_surface = self.small_font.render(
                text,
                True,
                self.colors.WHITE,
            )
            self.screen.blit(
                text_surface,
                (
                    minus_rect.right + metrics.unit(6),
                    row.centery - self.small_font.get_height() // 2,
                ),
            )
            minus_color = self.colors.GOLD if pending > 0 else self.colors.GRAY
            plus_color = (
                self.colors.GOLD if self._remaining_attribute_points() > 0 else self.colors.GRAY
            )
            pygame.draw.rect(self.screen, minus_color, minus_rect, 1)
            pygame.draw.rect(self.screen, plus_color, plus_rect, 1)
            self.screen.blit(
                self.small_font.render("-", True, minus_color),
                (
                    minus_rect.centerx - self.small_font.size("-")[0] // 2,
                    minus_rect.centery - self.small_font.get_height() // 2,
                ),
            )
            self.screen.blit(
                self.small_font.render("+", True, plus_color),
                (
                    plus_rect.centerx - self.small_font.size("+")[0] // 2,
                    plus_rect.centery - self.small_font.get_height() // 2,
                ),
            )
        available_text = f"Available Attribute Points: {self._remaining_attribute_points()}"
        self.screen.blit(
            self.small_font.render(
                available_text,
                True,
                self.colors.GOLD,
            ),
            (rect.left + metrics.unit(16), rect.bottom - metrics.unit(26)),
        )

    def _draw_details(self, rect):
        metrics = self.presenter.layout_metrics
        self.draw_semi_transparent_panel(rect)
        pygame.draw.rect(self.screen, self.colors.BORDER_COLOR, rect, metrics.stroke(2))
        status = self._selected_status()
        if status is None:
            return
        point_label = "Point" if status.node.cost == 1 else "Points"
        lines = [
            status.node.name,
            f"{status.node.cost} {point_label}",
        ]
        warning_lines = set()
        content_width = rect.width - metrics.unit(28)
        displayed_class = (
            self._selected_tree_id() if hasattr(self, "player_char") else status.node.tree_id
        )
        required_level = effective_node_level_requirement(
            status.node,
            displayed_class,
        )
        description = status.node.payload.get("description", "")
        if description:
            lines.extend(
                wrap_text_to_pixel_width(
                    description,
                    self.small_font,
                    content_width,
                )
            )
        if status.node.kind == NodeKind.PROMOTION:
            requirements = status.node.payload["requirements"]
            for requirement_line in self._promotion_requirement_lines(status.node):
                lines.extend(
                    wrap_text_to_pixel_width(
                        requirement_line,
                        self.small_font,
                        content_width,
                    )
                )
            lines.extend(
                wrap_text_to_pixel_width(
                    (f"Required level: {status.node.payload['level_requirement']}"),
                    self.small_font,
                    content_width,
                )
            )
            lines.extend(
                wrap_text_to_pixel_width(
                    (
                        "Required Stats: "
                        + ", ".join(
                            f"{self.STAT_DISPLAY_NAMES.get(name, name.title())} {value}"
                            for name, value in requirements.items()
                        )
                    ),
                    self.small_font,
                    content_width,
                )
            )
        elif required_level:
            lines.append(f"Required level: {required_level}")
        specialization = status.node.payload.get("weapon_specialization")
        if specialization:
            weapon_type, rank = specialization
            lines.extend(
                wrap_text_to_pixel_width(
                    f"Required {weapon_type} specialization level: {rank}",
                    self.small_font,
                    content_width,
                )
            )
        implied_prerequisites = {
            f"Requires {TREE_NODES[node_id].name}." for node_id in status.node.prerequisites
        }
        point_noun = "point" if status.node.cost == 1 else "points"
        implied_cost_reasons = {
            f"Requires {status.node.cost} {point_noun}.",
            f"Requires {status.node.cost} progression {point_noun}.",
        }
        for reason in status.reasons:
            if not (
                reason not in implied_prerequisites
                and reason not in implied_cost_reasons
                and not (
                    required_level
                    and (
                        reason.startswith("Requires global level ")
                        or reason.startswith("Requires level ")
                    )
                )
                and not (
                    specialization
                    and reason.startswith(f"Requires {specialization[0]} specialization level ")
                )
                and not (
                    status.node.kind == NodeKind.PROMOTION
                    and any(
                        any(
                            reason.startswith(f"Requires {display_name} ")
                            for display_name in {
                                self.STAT_DISPLAY_NAMES.get(
                                    stat_name,
                                    stat_name.title(),
                                ),
                                stat_name.replace(
                                    "intel",
                                    "intelligence",
                                ).title(),
                            }
                        )
                        for stat_name in status.node.payload["requirements"]
                    )
                )
            ):
                continue
            cleaned_reason = re.sub(r" \(current [^)]+\)", "", reason)
            wrapped_reason = wrap_text_to_pixel_width(
                cleaned_reason,
                self.small_font,
                content_width,
            )
            lines.extend(wrapped_reason)
            if reason.startswith("Another promotion is already distributed"):
                warning_lines.update(wrapped_reason)
        line_height = self.small_font.get_height() + metrics.unit(2)
        max_lines = max(1, (rect.height - metrics.unit(20)) // line_height)
        for index, line in enumerate(lines[:max_lines]):
            if index == 0:
                color = self.colors.GOLD
            elif line in warning_lines:
                color = self.PROMOTION_WARNING_COLOR
            else:
                color = self.colors.WHITE
            self.screen.blit(
                self.small_font.render(line, True, color),
                (
                    rect.left + metrics.unit(14),
                    rect.top + metrics.unit(10) + index * line_height,
                ),
            )

    def _draw_spend_button(self, rect):
        self._ensure_staging()
        enabled = self.has_pending_changes()
        metrics = self.presenter.layout_metrics
        gap = metrics.unit(8)
        reset_width = max(metrics.unit(72), (rect.width - gap) // 3)
        self.reset_button_rect = pygame.Rect(
            rect.left,
            rect.top,
            reset_width,
            rect.height,
        )
        self.spend_button_rect = pygame.Rect(
            self.reset_button_rect.right + gap,
            rect.top,
            rect.right - self.reset_button_rect.right - gap,
            rect.height,
        )

        self._draw_action_button(
            self.reset_button_rect,
            "Reset",
            enabled,
            getattr(self, "focus", "nodes") == "reset",
        )
        label = "Spend Distribution"
        self._draw_action_button(
            self.spend_button_rect,
            label,
            enabled,
            getattr(self, "focus", "nodes") == "spend",
        )

    def _draw_action_button(self, rect, label, enabled, selected):
        metrics = self.presenter.layout_metrics
        if selected:
            pygame.draw.rect(self.screen, self.colors.HIGHLIGHT_BG, rect)
        color = self.colors.GOLD if enabled else self.colors.GRAY
        pygame.draw.rect(self.screen, color, rect, metrics.stroke(2 if selected else 1))
        surface = self.normal_font.render(label, True, color)
        self.screen.blit(
            surface,
            (
                rect.centerx - surface.get_width() // 2,
                rect.centery - surface.get_height() // 2,
            ),
        )

    def draw_all(self, player_char=None, do_flip=True):
        """Draw progression, accepting the shared popup parent-screen contract."""
        if isinstance(player_char, bool):
            do_flip = player_char
            player_char = None
        if player_char is not None:
            self.player_char = player_char
        self.draw_background()
        self._draw_header()
        layout = self.standalone_layout_rects()
        self._draw_tree(layout["tree"])
        self._draw_attributes(layout["attributes"])
        self._draw_details(layout["details"])
        hint = (
            "Q/E: Current/Completed Trees  TAB: Tree/Attributes  "
            "ARROWS: Select  ENTER/CLICK: Purchase  ESC: Back"
        )
        self.screen.blit(
            self.small_font.render(hint, True, self.colors.GRAY),
            (
                self.presenter.layout_metrics.unit(24),
                self.height - self.presenter.layout_metrics.unit(28),
            ),
        )
        if do_flip:
            pygame.display.flip()

    def standalone_layout_rects(self) -> dict[str, pygame.Rect]:
        """Return responsive visible bounds for the standalone progression screen."""
        metrics = self.presenter.layout_metrics
        margin = metrics.unit(24)
        gap = metrics.unit(12)
        header_height = metrics.unit(100)
        footer_height = metrics.unit(165)
        tree_width = int((self.width - (margin * 2) - gap) * 0.69)
        tree_rect = pygame.Rect(
            margin,
            header_height,
            tree_width,
            self.height - header_height - footer_height,
        )
        attr_left = tree_rect.right + gap
        attr_rect = pygame.Rect(
            attr_left,
            header_height,
            self.width - attr_left - margin,
            min(metrics.unit(320), tree_rect.height),
        )
        detail_rect = pygame.Rect(
            margin,
            self.height - footer_height,
            self.width - (margin * 2),
            footer_height - metrics.unit(40),
        )
        return {"tree": tree_rect, "attributes": attr_rect, "details": detail_rect}
