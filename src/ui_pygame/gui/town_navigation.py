"""Optional first-person-style town navigation prototype."""

from __future__ import annotations

from dataclasses import dataclass

import pygame

from src.ui_pygame.screen_runtime import get_events

from .input_guards import (
    prepare_guarded_input,
    release_guard_allows_input,
    update_input_armed_from_event,
)
from .mouse_helpers import is_left_click, mouse_position
from .town_base import TownScreenBase


@dataclass(frozen=True)
class TownNode:
    """One prototype town-navigation location."""

    name: str
    description: str
    exits: dict[str, str]
    action: str | None = None
    landmark_color: tuple[int, int, int] = (120, 120, 135)


TOWN_NODES: dict[str, TownNode] = {
    "Town Square": TownNode(
        "Town Square",
        "Lanterns sway over the old well. Every road in Silvana starts here.",
        {
            "north": "Barracks",
            "east": "Shops",
            "south": "Tavern",
            "west": "Church",
        },
        landmark_color=(145, 120, 80),
    ),
    "Barracks": TownNode(
        "Barracks",
        "Sergeant's maps and casualty ledgers crowd the command room.",
        {"south": "Town Square", "east": "Warp Point"},
        "Barracks",
        landmark_color=(105, 120, 135),
    ),
    "Shops": TownNode(
        "Shops",
        "Three shopfronts share the lantern-lit market row.",
        {"west": "Town Square", "north": "Warp Point", "south": "Dungeon Gate"},
        "Shops",
        landmark_color=(150, 115, 65),
    ),
    "Tavern": TownNode(
        "The Thirsty Dog Tavern",
        "Warm windows glow through pipe smoke and low conversation.",
        {"north": "Town Square", "east": "Dungeon Gate", "west": "Old Warehouse"},
        "The Thirsty Dog Tavern",
        landmark_color=(140, 80, 55),
    ),
    "Church": TownNode(
        "Church of Elysia",
        "Candles burn against the dark glass of the sanctuary.",
        {"east": "Town Square", "south": "Old Warehouse"},
        "Church of Elysia",
        landmark_color=(120, 120, 160),
    ),
    "Old Warehouse": TownNode(
        "Old Warehouse",
        "Reinforced doors sit beneath quiet machinery and colder guards.",
        {"north": "Church", "east": "Tavern"},
        "Old Warehouse",
        landmark_color=(95, 95, 100),
    ),
    "Warp Point": TownNode(
        "Warp Point",
        "A brass-ringed platform hums while field scientists check their gauges.",
        {"west": "Barracks", "south": "Shops"},
        "Warp Point",
        landmark_color=(70, 145, 150),
    ),
    "Dungeon Gate": TownNode(
        "Dungeon Gate",
        "Cold dungeon air spills from the stairwell under the town wall.",
        {"north": "Shops", "west": "Tavern"},
        "Enter Dungeon",
        landmark_color=(85, 80, 95),
    ),
}

DIRECTION_KEYS = {
    pygame.K_UP: "north",
    pygame.K_w: "north",
    pygame.K_RIGHT: "east",
    pygame.K_d: "east",
    pygame.K_DOWN: "south",
    pygame.K_s: "south",
    pygame.K_LEFT: "west",
    pygame.K_a: "west",
}

DIRECTION_LABELS = {
    "north": "North",
    "east": "East",
    "south": "South",
    "west": "West",
}


class TownNavigationScreen(TownScreenBase):
    """Prototype node-based town exploration screen."""

    def __init__(self, presenter, nodes: dict[str, TownNode] | None = None):
        super().__init__(presenter)
        self.nodes = nodes or TOWN_NODES
        self.current_node_key = "Town Square"
        self.hover_direction: str | None = None
        self.hover_action = False
        self._direction_rects: dict[str, pygame.Rect] = {}
        self._action_rect: pygame.Rect | None = None
        self._exit_rect: pygame.Rect | None = None

    @property
    def current_node(self) -> TownNode:
        return self.nodes[self.current_node_key]

    def available_moves(self) -> dict[str, str]:
        """Return directional exits for the current node."""
        return dict(self.current_node.exits)

    def build_options(self) -> list[tuple[str, str]]:
        """Return compatibility labels for tests and debug callers."""
        node = self.current_node
        options = [
            (f"{DIRECTION_LABELS[direction]} to {target}", target)
            for direction, target in node.exits.items()
        ]
        if node.action:
            options.insert(0, (f"Interact: {node.name}", node.action))
        options.append(("Return to Town Menu", "Exit Town Navigation"))
        return options

    def option_rects(self) -> list[pygame.Rect]:
        """Return clickable rectangles for compatibility with mouse tests."""
        rects = list(self._direction_rects.values())
        if self._action_rect is not None:
            rects.append(self._action_rect)
        if self._exit_rect is not None:
            rects.append(self._exit_rect)
        return rects

    def view_rect(self) -> pygame.Rect:
        margin = 28
        return pygame.Rect(margin, 32, self.width - margin * 2, self.height - 235)

    def detail_panel_rect(self) -> pygame.Rect:
        margin = 24
        return pygame.Rect(margin, self.height - 188, self.width - margin * 2, 150)

    def move(self, direction: str) -> bool:
        """Move to the connected town node for a direction if one exists."""
        target = self.current_node.exits.get(direction)
        if not target:
            return False
        self.current_node_key = target
        self.hover_direction = None
        self.hover_action = False
        return True

    def interact(self) -> str:
        """Return the current node action, if any."""
        return self.current_node.action or ""

    def draw(self) -> None:
        """Draw the prototype town-navigation surface."""
        self.draw_background()
        node = self.current_node

        view_rect = self.view_rect()
        header = self.title_font.render("Explore Town", True, self.colors.GOLD)
        self.screen.blit(header, header.get_rect(centerx=self.width // 2, top=4))
        self._draw_town_view(view_rect, node)

        detail_rect = self.detail_panel_rect()
        self.draw_semi_transparent_panel(detail_rect, alpha=185)
        pygame.draw.rect(self.screen, self.colors.BORDER_COLOR, detail_rect, 2)
        title = self.large_font.render(node.name, True, self.colors.GOLD)
        self.screen.blit(title, (detail_rect.left + 18, detail_rect.top + 14))
        y = detail_rect.top + 52
        for line in self._wrap(node.description, detail_rect.width - 320, self.normal_font)[:3]:
            self.screen.blit(
                self.normal_font.render(line, True, self.colors.WHITE), (detail_rect.left + 16, y)
            )
            y += self.normal_font.get_height() + 4

        self._draw_action_bar(detail_rect, node)

    def _draw_town_view(self, rect: pygame.Rect, node: TownNode) -> None:
        """Draw a lightweight first-person town view with directional exits."""
        pygame.draw.rect(self.screen, (20, 24, 32), rect)
        pygame.draw.rect(self.screen, self.colors.BORDER_COLOR, rect, 2)

        sky_rect = pygame.Rect(rect.left + 2, rect.top + 2, rect.width - 4, rect.height // 2)
        street_rect = pygame.Rect(rect.left + 2, rect.centery, rect.width - 4, rect.height // 2 - 2)
        pygame.draw.rect(self.screen, (30, 36, 54), sky_rect)
        pygame.draw.rect(self.screen, (42, 40, 38), street_rect)

        horizon_y = rect.top + int(rect.height * 0.46)
        center_x = rect.centerx
        pygame.draw.polygon(
            self.screen,
            (70, 67, 60),
            [
                (center_x - 70, horizon_y),
                (center_x + 70, horizon_y),
                (rect.right - 76, rect.bottom - 8),
                (rect.left + 76, rect.bottom - 8),
            ],
        )
        pygame.draw.line(
            self.screen, (120, 110, 82), (center_x, horizon_y), (center_x, rect.bottom - 8), 2
        )

        building_rect = pygame.Rect(center_x - 120, horizon_y - 112, 240, 112)
        pygame.draw.rect(self.screen, node.landmark_color, building_rect)
        pygame.draw.rect(self.screen, (25, 22, 20), building_rect, 3)
        roof = [
            (building_rect.left - 18, building_rect.top),
            (building_rect.centerx, building_rect.top - 42),
            (building_rect.right + 18, building_rect.top),
        ]
        pygame.draw.polygon(self.screen, (45, 35, 32), roof)
        pygame.draw.rect(
            self.screen,
            (38, 30, 24),
            pygame.Rect(building_rect.centerx - 22, building_rect.bottom - 54, 44, 54),
        )
        label = self.normal_font.render(node.name, True, self.colors.WHITE)
        self.screen.blit(
            label, label.get_rect(centerx=building_rect.centerx, bottom=building_rect.top - 8)
        )

        self._direction_rects = self._town_direction_rects(rect)
        for direction, target in node.exits.items():
            self._draw_direction_prompt(direction, target)

        self._draw_town_position_map(rect)

    def _town_direction_rects(self, rect: pygame.Rect) -> dict[str, pygame.Rect]:
        prompt_width = min(250, max(170, rect.width // 4))
        prompt_height = 48
        return {
            "north": pygame.Rect(
                rect.centerx - prompt_width // 2, rect.top + 18, prompt_width, prompt_height
            ),
            "east": pygame.Rect(
                rect.right - prompt_width - 24,
                rect.centery - prompt_height // 2,
                prompt_width,
                prompt_height,
            ),
            "south": pygame.Rect(
                rect.centerx - prompt_width // 2,
                rect.bottom - prompt_height - 18,
                prompt_width,
                prompt_height,
            ),
            "west": pygame.Rect(
                rect.left + 24, rect.centery - prompt_height // 2, prompt_width, prompt_height
            ),
        }

    def _draw_direction_prompt(self, direction: str, target: str) -> None:
        rect = self._direction_rects[direction]
        selected = direction == self.hover_direction
        fill = self.colors.HIGHLIGHT_BG if selected else (28, 28, 34)
        border = self.colors.GOLD if selected else self.colors.BORDER_COLOR
        pygame.draw.rect(self.screen, fill, rect)
        pygame.draw.rect(self.screen, border, rect, 2)
        label = f"{DIRECTION_LABELS[direction]}: {target}"
        surface = self.small_font.render(
            label, True, self.colors.GOLD if selected else self.colors.WHITE
        )
        self.screen.blit(surface, surface.get_rect(center=rect.center))

    def _draw_town_position_map(self, view_rect: pygame.Rect) -> None:
        map_rect = pygame.Rect(view_rect.right - 188, view_rect.bottom - 146, 152, 112)
        self.draw_semi_transparent_panel(map_rect, alpha=150)
        pygame.draw.rect(self.screen, self.colors.BORDER_COLOR, map_rect, 1)
        positions = {
            "Barracks": (map_rect.centerx - 28, map_rect.top + 24),
            "Warp Point": (map_rect.centerx + 34, map_rect.top + 24),
            "Church": (map_rect.centerx - 56, map_rect.centery),
            "Town Square": (map_rect.centerx, map_rect.centery),
            "Shops": (map_rect.centerx + 56, map_rect.centery),
            "Old Warehouse": (map_rect.centerx - 56, map_rect.bottom - 24),
            "Tavern": (map_rect.centerx, map_rect.bottom - 24),
            "Dungeon Gate": (map_rect.centerx + 56, map_rect.bottom - 24),
        }
        for key, node in self.nodes.items():
            x, y = positions.get(key, map_rect.center)
            color = (
                self.colors.GOLD
                if key == self.current_node_key
                else getattr(node, "landmark_color", (110, 110, 120))
            )
            pygame.draw.circle(self.screen, color, (x, y), 6)
            if key == self.current_node_key:
                pygame.draw.circle(self.screen, (10, 10, 10), (x, y), 3)

    def _draw_action_bar(self, detail_rect: pygame.Rect, node: TownNode) -> None:
        right = detail_rect.right - 18
        self._exit_rect = pygame.Rect(right - 128, detail_rect.bottom - 48, 112, 32)
        pygame.draw.rect(self.screen, (32, 32, 38), self._exit_rect)
        pygame.draw.rect(self.screen, self.colors.BORDER_COLOR, self._exit_rect, 1)
        exit_label = self.small_font.render("Esc: Menu", True, self.colors.WHITE)
        self.screen.blit(exit_label, exit_label.get_rect(center=self._exit_rect.center))

        self._action_rect = None
        if node.action:
            self._action_rect = pygame.Rect(right - 304, detail_rect.bottom - 54, 160, 40)
            fill = self.colors.HIGHLIGHT_BG if self.hover_action else (42, 36, 28)
            pygame.draw.rect(self.screen, fill, self._action_rect)
            pygame.draw.rect(self.screen, self.colors.GOLD, self._action_rect, 2)
            action_label = "Enter Dungeon" if node.action == "Enter Dungeon" else "Interact"
            text = self.normal_font.render(action_label, True, self.colors.GOLD)
            self.screen.blit(text, text.get_rect(center=self._action_rect.center))

        move_text = "Arrows/WASD move between places"
        if node.action:
            move_text += "    Enter/Space interacts"
        instructions = self.small_font.render(move_text, True, self.colors.GRAY)
        self.screen.blit(instructions, (detail_rect.left + 18, detail_rect.bottom - 38))

    def _wrap(self, text: str, max_width: int, font) -> list[str]:
        words = text.split()
        lines: list[str] = []
        current = ""
        for word in words:
            candidate = word if not current else f"{current} {word}"
            if font.size(candidate)[0] <= max_width:
                current = candidate
                continue
            if current:
                lines.append(current)
            current = word
        if current:
            lines.append(current)
        return lines

    def navigate(
        self,
        flush_events: bool = False,
        require_key_release: bool = False,
    ) -> str | None:
        """Return an interaction action, or None when the prototype closes."""
        input_armed = prepare_guarded_input(
            flush_events=flush_events,
            require_key_release=require_key_release,
        )

        while True:
            self.draw()
            pygame.display.flip()

            input_armed = release_guard_allows_input(require_key_release, input_armed)
            for event in get_events():
                if event.type == pygame.QUIT:
                    pygame.quit()
                    import sys

                    sys.exit()
                input_armed = update_input_armed_from_event(event, require_key_release, input_armed)
                pos = mouse_position(event)
                hovered_direction = None
                hovered_action = False
                hovered_exit = False
                if pos is not None:
                    hovered_direction = next(
                        (
                            direction
                            for direction, rect in self._direction_rects.items()
                            if direction in self.current_node.exits and rect.collidepoint(pos)
                        ),
                        None,
                    )
                    hovered_action = bool(self._action_rect and self._action_rect.collidepoint(pos))
                    hovered_exit = bool(self._exit_rect and self._exit_rect.collidepoint(pos))
                if event.type == pygame.MOUSEMOTION:
                    self.hover_direction = hovered_direction
                    self.hover_action = hovered_action
                    continue
                if is_left_click(event):
                    if input_armed:
                        if hovered_direction:
                            self.move(hovered_direction)
                        elif hovered_action:
                            result = self.interact()
                            if result:
                                return result
                        elif hovered_exit:
                            return None
                    continue
                if event.type != pygame.KEYDOWN or not input_armed:
                    continue
                if event.key == pygame.K_ESCAPE:
                    return None
                if event.key in DIRECTION_KEYS:
                    self.move(DIRECTION_KEYS[event.key])
                elif event.key in (pygame.K_RETURN, pygame.K_SPACE):
                    result = self.interact()
                    if result:
                        return result

            self.presenter.clock.tick(30)
