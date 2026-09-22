"""Ability-tree layout and rendering for the pygame progression screen."""

from __future__ import annotations

import math

import pygame

from src.core.progression import (
    ABILITY_TREES,
    TREE_NODES,
    NodeKind,
    NodeState,
    prerequisite_groups,
)
from src.ui_pygame.assets.ability_icon_manager import get_ability_icon_manager

from .town_base import wrap_text_to_pixel_width


class ProgressionTreeMixin:
    """Render and lay out progression-tree nodes and connectors."""

    @staticmethod
    def _node_frame_rect(icon_rect: pygame.Rect) -> pygame.Rect:
        """Return the shared node frame and selection-highlight bounds."""
        padding = max(1, round(min(icon_rect.width, icon_rect.height) / 16))
        return icon_rect.inflate(padding * 2, padding * 2)

    def _layout_node_rects(self, rect, statuses, branches):
        """Lay icon nodes at explicit manifest columns and rows."""
        if not statuses:
            self.node_icon_rects = []
            return []
        explicit_column_count = math.ceil(max(status.node.position[0] for status in statuses) + 1)
        column_count = max(1, len(branches), explicit_column_count)
        metrics = self.presenter.layout_metrics
        unit = metrics.unit
        margin = unit(12)
        lane_width = (rect.width - (margin * 2)) // column_count
        self._tree_column_origin = rect.left + margin + lane_width // 2
        self._tree_lane_width = lane_width
        graph_top = rect.top + unit(42)
        graph_bottom = rect.bottom - self.TREE_WARNING_HEIGHT
        cell_height = unit(50)
        max_row = max(status.node.position[1] for status in statuses)
        available_height = graph_bottom - graph_top
        row_step = unit(58)
        if max_row:
            row_step = min(
                row_step,
                max(unit(52), (available_height - cell_height) // max_row),
            )
        self._tree_row_step = row_step
        visible_rows = max(
            1,
            (available_height - cell_height) // row_step + 1,
        )
        selected_row = statuses[self.current_node].node.position[1]
        if selected_row < self.tree_scroll_row:
            self.tree_scroll_row = selected_row
        elif selected_row >= self.tree_scroll_row + visible_rows:
            self.tree_scroll_row = selected_row - visible_rows + 1
        self.tree_scroll_row = max(
            0,
            min(self.tree_scroll_row, max(0, max_row - visible_rows + 1)),
        )
        self._tree_viewport = pygame.Rect(
            rect.left + unit(4),
            graph_top,
            rect.width - unit(8),
            graph_bottom - graph_top,
        )
        result: list[pygame.Rect] = []
        icon_rects: list[pygame.Rect] = []
        for status in statuses:
            column, row = status.node.position
            center_x = int(rect.left + margin + column * lane_width + lane_width // 2)
            y = graph_top + (row - self.tree_scroll_row) * row_step
            icon_size = unit(32)
            icon_rect = pygame.Rect(center_x - icon_size // 2, y, icon_size, icon_size)
            icon_rects.append(icon_rect)
            result.append(self._node_frame_rect(icon_rect))
        self.node_icon_rects = icon_rects
        return result

    def _draw_connectors(self, statuses):
        """Draw orthogonal prerequisite connectors behind talent nodes."""
        index_by_id = {status.node.id: index for index, status in enumerate(statuses)}
        promotion_targets_by_source: dict[str, list[tuple[str, pygame.Rect]]] = {}
        for target_index, target_status in enumerate(statuses):
            if target_status.node.kind != NodeKind.PROMOTION:
                continue
            target_rect = self.node_icon_rects[target_index]
            for prerequisite in target_status.node.prerequisites:
                promotion_targets_by_source.setdefault(prerequisite, []).append(
                    (target_status.node.id, target_rect)
                )
        source_anchor_x: dict[tuple[str, str], int] = {}
        for source_id, targets in promotion_targets_by_source.items():
            source_index = index_by_id.get(source_id)
            if source_index is None:
                continue
            source_rect = self.node_icon_rects[source_index]
            ordered_targets = sorted(targets, key=lambda entry: entry[1].centerx)
            for edge_index, (target_id, _target_rect) in enumerate(ordered_targets):
                source_anchor_x[(source_id, target_id)] = int(
                    source_rect.left
                    + source_rect.width * (edge_index + 1) / (len(ordered_targets) + 1)
                )
        for index, status in enumerate(statuses):
            target_rect = self.node_icon_rects[index]
            if not self._tree_viewport or not self._tree_viewport.colliderect(target_rect):
                continue
            if status.node.kind == NodeKind.PROMOTION:
                prerequisite_edges = [
                    (
                        self.node_icon_rects[source_index],
                        source_anchor_x.get(
                            (prerequisite, status.node.id),
                            self.node_icon_rects[source_index].centerx,
                        ),
                    )
                    for prerequisite in status.node.prerequisites
                    if (source_index := index_by_id.get(prerequisite)) is not None
                    and self._tree_viewport.colliderect(self.node_icon_rects[source_index])
                ]
                self._draw_promotion_connectors(
                    target_rect,
                    prerequisite_edges,
                    status.node.payload,
                )
                continue
            for prerequisite in status.node.prerequisites:
                source_index = index_by_id.get(prerequisite)
                if source_index is None:
                    continue
                source_rect = self.node_icon_rects[source_index]
                if not self._tree_viewport.colliderect(source_rect):
                    continue
                if status.node.payload.get("connector_enter_from_top"):
                    source_is_left = source_rect.centerx < target_rect.centerx
                    source_side = source_rect.midright if source_is_left else source_rect.midleft
                    channel_column = status.node.payload.get(
                        "connector_channel_columns",
                        {},
                    ).get(prerequisite)
                    channel_x = (
                        target_rect.centerx
                        if channel_column is None
                        else int(self._tree_column_origin + channel_column * self._tree_lane_width)
                    )
                    pygame.draw.lines(
                        self.screen,
                        self.CONNECTOR_COLOR,
                        False,
                        (
                            source_side,
                            (channel_x, source_side[1]),
                            (channel_x, target_rect.top),
                            target_rect.midtop,
                        ),
                        1,
                    )
                    continue
                if status.node.payload.get("connector_join_at_target_row"):
                    source_is_left = source_rect.centerx < target_rect.centerx
                    end = target_rect.midleft if source_is_left else target_rect.midright
                    pygame.draw.lines(
                        self.screen,
                        self.CONNECTOR_COLOR,
                        False,
                        (
                            source_rect.midbottom,
                            (source_rect.centerx, end[1]),
                            end,
                        ),
                        1,
                    )
                    continue
                end = target_rect.midtop
                color = self.CONNECTOR_COLOR
                channel_column = status.node.payload.get(
                    "connector_channel_columns",
                    {},
                ).get(prerequisite)
                if source_rect.centerx == target_rect.centerx and channel_column is None:
                    pygame.draw.line(
                        self.screen,
                        color,
                        source_rect.midbottom,
                        end,
                        1,
                    )
                    continue
                if source_rect.centerx == target_rect.centerx:
                    channel_x = int(
                        self._tree_column_origin + channel_column * self._tree_lane_width
                    )
                    source_side = (
                        source_rect.midright
                        if channel_x >= source_rect.centerx
                        else source_rect.midleft
                    )
                    end = (
                        target_rect.midright
                        if channel_x >= target_rect.centerx
                        else target_rect.midleft
                    )
                    pygame.draw.lines(
                        self.screen,
                        color,
                        False,
                        (
                            source_side,
                            (channel_x, source_side[1]),
                            (channel_x, end[1]),
                            end,
                        ),
                        1,
                    )
                    continue
                source_is_left = source_rect.centerx <= target_rect.centerx
                source_side = source_rect.midright if source_is_left else source_rect.midleft
                end = target_rect.midleft if source_is_left else target_rect.midright
                if channel_column is None:
                    channel_x = (source_side[0] + end[0]) // 2
                else:
                    channel_x = int(
                        self._tree_column_origin + channel_column * self._tree_lane_width
                    )
                pygame.draw.lines(
                    self.screen,
                    color,
                    False,
                    (
                        source_side,
                        (channel_x, source_side[1]),
                        (channel_x, end[1]),
                        end,
                    ),
                    1,
                )

    def _draw_promotion_connectors(
        self,
        target_rect,
        source_edges,
        payload=None,
    ):
        """Draw promotion routes with buffer-row junctions and side entries."""
        payload = payload or {}
        prerequisite_mode = payload.get("prerequisite_mode", "all")
        ordered_sources = sorted(source_edges, key=lambda edge: edge[0].centerx)
        edge_count = len(ordered_sources)
        merge_paths = (
            prerequisite_mode != "any" and not payload.get("prerequisite_groups") and edge_count > 1
        )
        row_step = getattr(self, "_tree_row_step", 58)
        max_source_bottom = max(
            (source_rect.bottom for source_rect, _source_x in ordered_sources),
            default=target_rect.top,
        )
        has_buffer_row = target_rect.top - max_source_bottom > row_step
        buffer_join_y = target_rect.top - row_step + target_rect.height // 2
        join_y = buffer_join_y if has_buffer_row else target_rect.top - 10
        for edge_index, (source_rect, source_x) in enumerate(ordered_sources):
            enters_left_side = not merge_paths and edge_count > 1 and edge_index == 0
            enters_right_side = not merge_paths and edge_count > 1 and edge_index == edge_count - 1
            enters_side = enters_left_side or enters_right_side
            if merge_paths:
                destination_x = target_rect.centerx
            elif edge_count == 1:
                destination_x = target_rect.centerx
            elif enters_left_side:
                destination_x = target_rect.left
            elif enters_right_side:
                destination_x = target_rect.right
            else:
                destination_x = int(
                    target_rect.left + target_rect.width * edge_index / (edge_count - 1)
                )
            destination_y = target_rect.centery if enters_side else join_y
            source_is_penultimate = (
                has_buffer_row and target_rect.top - source_rect.top == row_step * 2
            )
            if source_is_penultimate or (
                not enters_side and target_rect.top - source_rect.bottom <= 80
            ):
                source_anchor = (source_x, source_rect.bottom)
                points = (
                    source_anchor,
                    (source_x, destination_y),
                    (destination_x, destination_y),
                )
            else:
                branch_y = source_rect.bottom + 6
                source_anchor = (source_x, source_rect.bottom)
                lane_width = getattr(self, "_tree_lane_width", 120)
                if source_rect.centerx < target_rect.centerx:
                    channel_x = int(source_rect.centerx + lane_width / 2)
                elif source_rect.centerx > target_rect.centerx:
                    channel_x = int(source_rect.centerx - lane_width / 2)
                else:
                    channel_x = source_rect.centerx
                points = (
                    source_anchor,
                    (source_x, branch_y),
                    (channel_x, branch_y),
                    (channel_x, destination_y),
                    (destination_x, destination_y),
                )
            pygame.draw.lines(
                self.screen,
                self.PROMOTION_CONNECTOR_COLOR,
                False,
                points,
                2,
            )
            if not merge_paths and not enters_side:
                pygame.draw.line(
                    self.screen,
                    self.PROMOTION_CONNECTOR_COLOR,
                    (destination_x, join_y),
                    (destination_x, target_rect.top),
                    2,
                )
        if merge_paths:
            pygame.draw.line(
                self.screen,
                self.PROMOTION_CONNECTOR_COLOR,
                (target_rect.centerx, join_y),
                target_rect.midtop,
                2,
            )

    @staticmethod
    def _promotion_highlight_node_ids(statuses, selected_index):
        """Return full required paths and direct endpoints for a promotion."""
        if not 0 <= selected_index < len(statuses):
            return set(), set()
        selected_node = statuses[selected_index].node
        if selected_node.kind != NodeKind.PROMOTION:
            return set(), set()
        nodes_by_id = {status.node.id: status.node for status in statuses}
        endpoints = set(selected_node.prerequisites)
        highlighted = set()
        pending = list(endpoints)
        while pending:
            node_id = pending.pop()
            if node_id in highlighted:
                continue
            node = nodes_by_id.get(node_id)
            if node is None:
                continue
            highlighted.add(node_id)
            pending.extend(node.prerequisites)
        return highlighted, endpoints

    def _node_display_color(
        self,
        status,
        is_pending,
        required_path_ids,
        required_endpoint_ids,
    ):
        """Return node color with hover-path emphasis overriding every state."""
        if status.node.id in required_endpoint_ids:
            return self.REQUIRED_ENDPOINT_COLOR
        if status.node.id in required_path_ids:
            return self.REQUIRED_PATH_COLOR
        if is_pending:
            return (90, 175, 220)
        return self.STATE_COLORS[status.state]

    @staticmethod
    def _promotion_requirement_lines(node) -> list[str]:
        """Describe the exact branch endpoints needed by a promotion."""
        prerequisites = [
            TREE_NODES[node_id] for node_id in node.prerequisites if node_id in TREE_NODES
        ]
        prerequisites.sort(key=lambda prerequisite: prerequisite.position)
        if not prerequisites:
            return []
        groups = prerequisite_groups(node)
        if node.payload.get("prerequisite_groups"):
            lines = ["Path requirements (all groups required):"]
            for group in groups:
                members = [TREE_NODES[node_id] for node_id in group]
                prefix = "Choose one" if len(members) > 1 else "Required"
                names = " or ".join(f"{member.lane}: {member.name}" for member in members)
                lines.append(f"- {prefix}: {names}")
            return lines
        requirement_mode = node.payload.get("prerequisite_mode", "all")
        heading = (
            "Path requirement (choose any one):"
            if requirement_mode == "any"
            else "Path requirements (all required):"
        )
        return [
            heading,
            *(f"- {prerequisite.lane}: {prerequisite.name}" for prerequisite in prerequisites),
        ]

    def _draw_header(self):
        title = self.large_font.render("Progression", True, self.colors.GOLD)
        self.screen.blit(title, (32, 24))
        state = self.player_char.progression
        summary = (
            f"Global Level {state.level}  |  Class Tier "
            f"{self.player_char.level.pro_level}  |  Progression Points "
            f"{state.unspent_points}  |  Attribute Points "
            f"{state.unspent_attribute_points}"
        )
        self.screen.blit(
            self.normal_font.render(summary, True, self.colors.WHITE),
            (32, 62),
        )

    def _draw_tree(self, rect):
        self.draw_semi_transparent_panel(rect)
        pygame.draw.rect(self.screen, self.colors.BORDER_COLOR, rect, 2)
        points_text = f"Available Progression Points: {self._remaining_points()}"
        points_surface = self.normal_font.render(
            points_text,
            True,
            self.colors.GOLD,
        )
        self.screen.blit(
            points_surface,
            (
                rect.left + self.presenter.layout_metrics.unit(16),
                rect.top + self.presenter.layout_metrics.unit(12),
            ),
        )
        if getattr(self, "show_embedded_navigation_helper", False):
            helper = (
                "Arrows: Navigate  Enter: Select  P/Esc: Back"
                if getattr(self, "embedded_navigation_active", False)
                else "P: Navigate tree"
            )
            helper_surface = self.small_font.render(
                helper,
                True,
                self.colors.GRAY,
            )
            self.screen.blit(
                helper_surface,
                (
                    rect.right
                    - helper_surface.get_width()
                    - self.presenter.layout_metrics.unit(16),
                    rect.top + self.presenter.layout_metrics.unit(15),
                ),
            )
        statuses = self._statuses()
        tree = ABILITY_TREES[self._selected_tree_id()]
        self.node_rects = self._layout_node_rects(
            rect,
            statuses,
            tree.branches,
        )
        self._draw_connectors(statuses)
        required_path_ids, required_endpoint_ids = self._promotion_highlight_node_ids(
            statuses,
            (
                getattr(self, "hovered_node_index", None)
                if getattr(self, "hovered_node_index", None) is not None
                else -1
            ),
        )

        for index, status in enumerate(statuses):
            icon_rect = self.node_icon_rects[index]
            if not self._tree_viewport.colliderect(icon_rect):
                continue
            selected = self.focus == "nodes" and index == self.current_node
            is_pending = status.node.id in self.pending_node_ids
            frame_rect = self._node_frame_rect(icon_rect)
            pygame.draw.rect(
                self.screen,
                (self.colors.HIGHLIGHT_BG if selected else self.NODE_BACKING_COLOR),
                frame_rect,
            )
            icon_manager = getattr(self, "icon_manager", None)
            if icon_manager is None:
                icon_manager = get_ability_icon_manager()
                self.icon_manager = icon_manager
            icon = icon_manager.get_icon(status.node.icon_key).copy()
            if status.state == NodeState.BLOCKED:
                icon.fill((145, 145, 145, 190), special_flags=pygame.BLEND_RGBA_MULT)
            elif status.state == NodeState.CLOSED:
                icon.fill((150, 70, 70, 175), special_flags=pygame.BLEND_RGBA_MULT)
            self.screen.blit(pygame.transform.smoothscale(icon, icon_rect.size), icon_rect)
            state_color = self._node_display_color(
                status,
                is_pending,
                required_path_ids,
                required_endpoint_ids,
            )
            pygame.draw.rect(
                self.screen,
                state_color,
                frame_rect,
                (
                    3
                    if status.node.id in required_endpoint_ids
                    else 2 if status.node.id in required_path_ids or selected else 1
                ),
            )
        self._draw_tree_warning(rect)

    def _has_pending_promotion(self) -> bool:
        """Return whether the current distribution contains a promotion."""
        self._ensure_staging()
        return any(
            node_id in TREE_NODES and TREE_NODES[node_id].kind == NodeKind.PROMOTION
            for node_id in self.pending_node_ids
        )

    def _draw_tree_warning(self, rect) -> None:
        """Draw the permanent promotion warning at the tree's bottom edge."""
        try:
            selected_tree = self._selected_tree_id()
        except (AttributeError, ZeroDivisionError):
            selected_tree = ""
        warning_text = (
            self.LANCER_PROMOTION_TEXT if selected_tree == "Lancer" else self.TREE_WARNING_TEXT
        )
        lines = wrap_text_to_pixel_width(
            warning_text,
            self.small_font,
            rect.width - 32,
        )
        line_height = self.small_font.get_height() + 2
        warning_height = len(lines) * line_height
        warning_y = rect.bottom - warning_height - 8
        backing_rect = pygame.Rect(
            rect.left + 8,
            warning_y - 2,
            rect.width - 16,
            warning_height + 4,
        )
        pygame.draw.rect(
            self.screen,
            self.LABEL_BACKING_COLOR,
            backing_rect,
        )
        color = self.PROMOTION_WARNING_COLOR if self._has_pending_promotion() else self.colors.GRAY
        for index, line in enumerate(lines):
            self.screen.blit(
                self.small_font.render(line, True, color),
                (rect.left + 16, warning_y + index * line_height),
            )
