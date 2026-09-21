"""
Generic location menu screen for town locations (church, barracks, inn).
Provides a consistent menu interface with background support, using ShopScreen-style layout.
"""

import pygame

from src.ui_pygame.screen_runtime import get_events

from .input_guards import (
    prepare_guarded_input,
    release_guard_allows_input,
    update_input_armed_from_event,
)
from .mouse_helpers import hit_index, is_left_click, mouse_position
from .town_base import TownScreenBase


class LocationMenuScreen(TownScreenBase):
    """
    A generic menu screen for town locations.
    Uses a two-column layout similar to ShopScreen: options on left, content area on right.
    """

    def __init__(self, presenter, location_name):
        super().__init__(presenter)
        self.location_name = location_name

        # State
        self.current_option = 0
        self.scroll_offset = 0
        self.options_list = []
        self.location_portrait_name: str | None = None
        self.option_portrait_names: list[str | None] | None = None

    def set_location_portrait(self, npc_name: str | None) -> None:
        """Set a persistent portrait for this location menu."""
        self.location_portrait_name = npc_name
        self.option_portrait_names = None

    def set_option_portraits(self, npc_names: list[str | None] | None) -> None:
        """Set per-option portrait names for menus with multiple speakers."""
        self.option_portrait_names = npc_names

    def current_portrait_name(self) -> str | None:
        """Return the portrait name for the current highlighted option."""
        if self.option_portrait_names is not None:
            if 0 <= self.current_option < len(self.option_portrait_names):
                return self.option_portrait_names[self.current_option]
            return None
        return self.location_portrait_name

    def option_rects(self, options: list[str] | None = None) -> list[pygame.Rect]:
        """Return clickable rectangles for the visible location options."""
        options = options if options is not None else self.options_list
        if not options:
            return []
        top_height = self.height // 12
        options_width = self.width // 3
        options_height = self.height // 4
        options_rect = pygame.Rect(0, top_height, options_width, options_height)
        option_height = options_rect.height // (len(options) + 1)
        return [
            pygame.Rect(
                options_rect.left + 12,
                options_rect.top + (idx + 1) * option_height - 6,
                options_rect.width - 24,
                self.normal_font.get_height() + 12,
            )
            for idx, _option in enumerate(options)
        ]

    def _content_item_layout(self) -> tuple[pygame.Rect, int, int, int, int, int]:
        top_height = self.height // 12
        content_width = 2 * self.width // 3
        content_height = self.height - top_height
        content_x = self.width // 3
        content_y = top_height
        content_rect = pygame.Rect(content_x, content_y, content_width, content_height)
        line_height = 28
        max_visible = max(1, (content_height - 80) // line_height)
        cursor_x = content_rect.left + 20
        item_x = cursor_x + 20
        quantity_x = content_rect.right - 80
        return content_rect, line_height, max_visible, cursor_x, item_x, quantity_x

    def content_row_rects(self, item_count: int) -> list[tuple[int, pygame.Rect]]:
        """Return visible content-row indexes and clickable rectangles."""
        if item_count <= 0:
            return []
        content_rect, line_height, max_visible, _cursor_x, item_x, _quantity_x = (
            self._content_item_layout()
        )
        max_scroll = max(0, item_count - max_visible)
        self.scroll_offset = max(0, min(self.scroll_offset, max_scroll))
        end = min(item_count, self.scroll_offset + max_visible)
        rows = []
        for visible_idx, item_idx in enumerate(range(self.scroll_offset, end)):
            text_y = content_rect.top + 40 + (visible_idx * line_height)
            rows.append(
                (
                    item_idx,
                    pygame.Rect(
                        item_x - 8, text_y - 4, content_rect.right - item_x - 20, line_height
                    ),
                )
            )
        return rows

    def _hit_content_row(self, item_count: int, pos: tuple[int, int] | None) -> int | None:
        if pos is None:
            return None
        for item_idx, rect in self.content_row_rects(item_count):
            if rect.collidepoint(pos):
                return item_idx
        return None

    def _ensure_content_selection_visible(self, item_count: int, max_visible: int) -> None:
        if item_count <= 0:
            self.current_option = 0
            self.scroll_offset = 0
            return
        max_visible = max(1, max_visible)
        max_scroll = max(0, item_count - max_visible)
        self.current_option = max(0, min(self.current_option, item_count - 1))
        if self.current_option < self.scroll_offset:
            self.scroll_offset = self.current_option
        if self.current_option >= self.scroll_offset + max_visible:
            self.scroll_offset = self.current_option - max_visible + 1
        self.scroll_offset = max(0, min(self.scroll_offset, max_scroll))

    def _move_content_selection(self, delta: int, item_count: int, max_visible: int) -> None:
        if item_count <= 0:
            self._ensure_content_selection_visible(item_count, max_visible)
            return
        self.current_option = (self.current_option + delta) % item_count
        self._ensure_content_selection_visible(item_count, max_visible)

    def draw_all(self):
        """Draw the location menu interface."""
        self.draw_frame(do_flip=True)

    def draw_frame(self, *, do_flip: bool = False):
        """Draw the location frame, optionally flipping the display."""
        self.draw_background()

        self.draw_top()
        self.draw_options()
        self.draw_npc_portrait(npc_name=self.current_portrait_name())
        self.draw_content()
        if do_flip:
            pygame.display.flip()

    def draw_top(self):
        """Draw the top header with location name."""
        top_height = self.height // 12
        top_rect = pygame.Rect(0, 0, self.width, top_height)

        self.draw_semi_transparent_panel(top_rect)
        pygame.draw.rect(self.screen, self.colors.BORDER_COLOR, top_rect, 2)

        # Center the location name
        text = self.large_font.render(self.location_name, True, self.colors.GOLD)
        text_rect = text.get_rect(center=(self.width // 2, top_rect.centery))
        self.screen.blit(text, text_rect)

    def draw_options(self):
        """Draw the menu options on the left side."""
        top_height = self.height // 12
        options_width = self.width // 3
        options_height = self.height // 4
        options_y = top_height
        options_rect = pygame.Rect(0, options_y, options_width, options_height)

        self.draw_semi_transparent_panel(options_rect)
        pygame.draw.rect(self.screen, self.colors.BORDER_COLOR, options_rect, 2)

        # Calculate spacing for options
        num_options = len(self.options_list)
        option_height = options_rect.height // (num_options + 1)

        option_rects = self.option_rects()
        for idx, option in enumerate(self.options_list):
            # Highlight selected option
            color = self.colors.GOLD if idx == self.current_option else self.colors.WHITE

            # Draw option text centered
            text = self.normal_font.render(option, True, color)
            text_x = options_rect.centerx - text.get_width() // 2
            text_y = options_rect.top + (idx + 1) * option_height

            # Highlight background for selected
            if idx == self.current_option:
                highlight_rect = option_rects[idx]
                pygame.draw.rect(self.screen, self.colors.HIGHLIGHT_BG, highlight_rect)
                pygame.draw.rect(self.screen, self.colors.GOLD, highlight_rect, 1)

            self.screen.blit(text, (text_x, text_y))

    def draw_content(self, content_text="", items_data=None):
        """Draw the content area on the right side with optional text or formatted items."""
        top_height = self.height // 12
        content_width = 2 * self.width // 3
        content_height = self.height - top_height
        content_x = self.width // 3
        content_y = top_height
        content_rect = pygame.Rect(content_x, content_y, content_width, content_height)

        self.draw_semi_transparent_panel(content_rect)
        pygame.draw.rect(self.screen, self.colors.BORDER_COLOR, content_rect, 2)

        # Handle structured items data with proper alignment and scrolling
        if items_data:
            font = self.large_font
            _content_rect, line_height, max_visible, cursor_x, item_x, quantity_x = (
                self._content_item_layout()
            )

            row_rects = dict(self.content_row_rects(len(items_data)))

            # Determine visible window of items
            visible_items = items_data[self.scroll_offset : self.scroll_offset + max_visible]

            text_y = content_rect.top + 40  # Start with some padding

            for idx, item_name, quantity, is_selected in visible_items:
                if is_selected:
                    row_rect = row_rects[idx]
                    pygame.draw.rect(self.screen, self.colors.HIGHLIGHT_BG, row_rect)
                    pygame.draw.rect(self.screen, self.colors.GOLD, row_rect, 1)
                # Draw cursor for selected item
                if is_selected:
                    cursor = font.render(">", True, self.colors.GOLD)
                    self.screen.blit(cursor, (cursor_x, text_y))

                # Draw item name
                color = self.colors.GOLD if is_selected else self.colors.WHITE
                name_surface = font.render(item_name, True, color)
                self.screen.blit(name_surface, (item_x, text_y))

                # Draw quantity (right-aligned) if not zero
                if quantity > 0:
                    qty_text = f"x{quantity}"
                    qty_surface = font.render(qty_text, True, color)
                    qty_rect = qty_surface.get_rect(right=quantity_x, top=text_y)
                    self.screen.blit(qty_surface, qty_rect)

                text_y += line_height

            return

        # Draw content text if provided
        if content_text:
            text_x = content_rect.left + 20
            text_y = content_rect.top + 20

            # Check if this is an item list (contains cursor marker or item quantity pattern)
            import re

            is_item_list = "►" in content_text or bool(re.search(r"\bx\s*\d+\b", content_text))

            # Wrap text and render
            lines = content_text.split("\n")
            for line in lines:
                # For item lists, use monospace font and don't wrap
                if is_item_list:
                    # Use a smaller monospace-like font for item lists
                    font = self.large_font
                    text_surface = font.render(line, True, self.colors.WHITE)
                    self.screen.blit(text_surface, (text_x, text_y))
                    text_y += 28
                else:
                    # For regular text, wrap long lines
                    import textwrap

                    wrapped_lines = textwrap.wrap(line, width=50)
                    for wrapped_line in wrapped_lines:
                        text_surface = self.large_font.render(wrapped_line, True, self.colors.WHITE)
                        self.screen.blit(text_surface, (text_x, text_y))
                        text_y += 25

    def navigate(
        self,
        options,
        reset_cursor: bool = True,
        flush_events: bool = False,
        require_key_release: bool = False,
    ):
        """
        Navigate the menu and return the selected option index.

        Args:
            options: List of menu options
            reset_cursor: When False, retain current selection index

        Returns:
            Index of selected option, or None if escaped
        """
        self.options_list = options
        if reset_cursor:
            self.current_option = 0
            self.scroll_offset = 0
        else:
            # Clamp to valid range in case options changed
            if self.options_list:
                self.current_option = max(0, min(self.current_option, len(self.options_list) - 1))
            else:
                self.current_option = 0
            self.scroll_offset = 0  # Reset scroll when options change

        input_armed = prepare_guarded_input(
            flush_events=flush_events,
            require_key_release=require_key_release,
        )

        while True:
            self.draw_all()

            input_armed = release_guard_allows_input(require_key_release, input_armed)
            for event in get_events():
                if event.type == pygame.QUIT:
                    pygame.quit()
                    import sys

                    sys.exit()
                input_armed = update_input_armed_from_event(event, require_key_release, input_armed)
                hovered = hit_index(self.option_rects(), mouse_position(event))
                if hovered is not None and event.type == pygame.MOUSEMOTION:
                    self.current_option = hovered
                elif hovered is not None and is_left_click(event):
                    if input_armed:
                        self.current_option = hovered
                        return self.current_option
                if event.type == pygame.KEYDOWN:
                    if not input_armed:
                        continue
                    if event.key == pygame.K_ESCAPE:
                        return None
                    elif event.key == pygame.K_UP:
                        self.current_option = (self.current_option - 1) % len(self.options_list)
                    elif event.key == pygame.K_DOWN:
                        self.current_option = (self.current_option + 1) % len(self.options_list)
                    elif event.key == pygame.K_RETURN or event.key == pygame.K_SPACE:
                        return self.current_option

            self.presenter.clock.tick(30)

    def display_items_list(self, items_data):
        """
        Display a list of items with quantities in the content area.
        items_data: list of tuples (item_name, quantity)
        """

        # Build items display text
        lines = []
        for item_name, quantity in items_data:
            lines.append(f"{item_name:30} x{quantity:3}")

        items_text = "\n".join(lines)

        # Continuously draw with items list displayed
        while True:
            self.draw_background()
            self.draw_top()
            self.draw_options()
            self.draw_npc_portrait(npc_name=self.current_portrait_name())
            self.draw_content(items_text)
            pygame.display.flip()

            for event in get_events():
                if event.type == pygame.QUIT:
                    pygame.quit()
                    import sys

                    sys.exit()
                elif event.type == pygame.KEYDOWN or is_left_click(event):
                    # Exit display on any key
                    return

            self.presenter.clock.tick(30)

    def draw_options_instructions(self):
        """Draw instructions only on the left side, without menu highlighting."""
        top_height = self.height // 12
        left_width = self.width // 3
        options_rect = pygame.Rect(0, top_height, left_width, self.height - top_height)

        self.draw_semi_transparent_panel(options_rect)
        pygame.draw.rect(self.screen, self.colors.BORDER_COLOR, options_rect, 2)

        # Draw instructions text
        instr_font = self.normal_font
        instructions = ["[Use arrows to select]", "[Press ESC to go back]"]

        y = options_rect.top + 20
        for instruction in instructions:
            text = instr_font.render(instruction, True, self.colors.GOLD)
            text_rect = text.get_rect(centerx=options_rect.centerx, top=y)
            self.screen.blit(text, text_rect)
            y += 40

    def navigate_with_content(
        self,
        items_data,
        flush_events: bool = False,
        require_key_release: bool = False,
    ):
        """
        Navigate menu with items displayed in the right content area.
        items_data: list of tuples (item_name, quantity) to display and navigate on right
        """

        # Ensure indices are valid for the current items_data
        if items_data:
            self.current_option = min(self.current_option, max(0, len(items_data) - 1))
            self.scroll_offset = min(self.scroll_offset, max(0, len(items_data) - 1))
        else:
            self.current_option = 0
            self.scroll_offset = 0

        # Calculate max visible items
        _content_rect, _line_height, max_visible, _cursor_x, _item_x, _quantity_x = (
            self._content_item_layout()
        )

        input_armed = prepare_guarded_input(
            flush_events=flush_events,
            require_key_release=require_key_release,
        )

        while True:
            self.draw_background()
            self.draw_top()
            self.draw_options_instructions()
            self.draw_npc_portrait(npc_name=self.current_portrait_name())

            # Build structured items data with selection state
            formatted_items = []
            for idx, (item_name, quantity) in enumerate(items_data):
                is_selected = idx == self.current_option
                formatted_items.append((idx, item_name, quantity, is_selected))

            self.draw_content(items_data=formatted_items)
            pygame.display.flip()

            input_armed = release_guard_allows_input(require_key_release, input_armed)
            for event in get_events():
                if event.type == pygame.QUIT:
                    pygame.quit()
                    import sys

                    sys.exit()
                input_armed = update_input_armed_from_event(event, require_key_release, input_armed)
                hovered = self._hit_content_row(len(items_data), mouse_position(event))
                if hovered is not None and event.type == pygame.MOUSEMOTION:
                    self.current_option = hovered
                    self._ensure_content_selection_visible(len(items_data), max_visible)
                elif hovered is not None and is_left_click(event):
                    if input_armed:
                        self.current_option = hovered
                        self._ensure_content_selection_visible(len(items_data), max_visible)
                        return self.current_option
                elif event.type == pygame.MOUSEWHEEL and items_data:
                    wheel_y = getattr(event, "y", 0)
                    if wheel_y:
                        direction = -1 if wheel_y > 0 else 1
                        for _ in range(abs(wheel_y)):
                            self._move_content_selection(direction, len(items_data), max_visible)
                if event.type == pygame.KEYDOWN:
                    if not input_armed:
                        continue
                    if event.key == pygame.K_ESCAPE:
                        return None
                    elif event.key == pygame.K_UP:
                        self._move_content_selection(-1, len(items_data), max_visible)
                    elif event.key == pygame.K_DOWN:
                        self._move_content_selection(1, len(items_data), max_visible)
                    elif event.key == pygame.K_RETURN or event.key == pygame.K_SPACE:
                        return self.current_option

            self.presenter.clock.tick(30)
