"""
Shop Selection screen for choosing which shop to visit.
"""

import pygame

from .input_guards import (
    prepare_guarded_input,
    release_guard_allows_input,
    update_input_armed_from_event,
)
from .menu_layout import menu_unit, menu_viewport_size, touch_target_height
from .mouse_helpers import hit_index, is_left_click, mouse_position
from .town_base import TownScreenBase


class ShopSelectionScreen(TownScreenBase):
    """
    Menu screen for selecting which shop to visit in town.
    """

    def __init__(self, presenter):
        super().__init__(presenter)
        # Menu state
        self.current_selection = 0

    def option_rects(self, options) -> list[pygame.Rect]:
        """Return clickable rectangles for the visible shop options."""
        width, height = menu_viewport_size(self.presenter)
        panel_width = min(menu_unit(self.presenter, 400), width - menu_unit(self.presenter, 48))
        panel_x = width - panel_width
        options_start_y = menu_unit(self.presenter, 130)
        instruction_height = menu_unit(self.presenter, 118)
        available_height = max(1, height - options_start_y - instruction_height)
        desired_height = touch_target_height(self.presenter) + menu_unit(self.presenter, 6)
        line_height = max(
            menu_unit(self.presenter, 42),
            min(desired_height, available_height // max(1, len(options))),
        )
        row_height = max(menu_unit(self.presenter, 38), line_height - menu_unit(self.presenter, 4))
        return [
            pygame.Rect(
                panel_x + menu_unit(self.presenter, 20),
                options_start_y + i * line_height,
                panel_width - menu_unit(self.presenter, 40),
                row_height,
            )
            for i, _option in enumerate(options)
        ]

    def draw_menu_panel(self, options):
        """Draw the semi-transparent menu panel with options."""
        # Menu panel on the right side
        width, height = menu_viewport_size(self.presenter)
        panel_width = min(menu_unit(self.presenter, 400), width - menu_unit(self.presenter, 48))
        panel_height = height
        panel_x = width - panel_width
        panel_y = 0

        # Create semi-transparent overlay
        panel_rect = pygame.Rect(panel_x, panel_y, panel_width, panel_height)
        self.draw_semi_transparent_panel(panel_rect)

        # Draw border
        pygame.draw.rect(self.screen, self.colors.GOLD, panel_rect, 3)

        # Title
        title_text = self.title_font.render("Select a Shop", True, self.colors.GOLD)
        title_rect = title_text.get_rect(centerx=panel_x + panel_width // 2, top=40)
        self.screen.blit(title_text, title_rect)

        # Options list
        option_rects = self.option_rects(options)
        for i, option in enumerate(options):
            y = option_rects[i].centery

            # Highlight selected option
            if i == self.current_selection:
                highlight_rect = option_rects[i]
                pygame.draw.rect(self.screen, self.colors.HIGHLIGHT_BG, highlight_rect)
                pygame.draw.rect(self.screen, self.colors.GOLD, highlight_rect, 2)
                color = self.colors.GOLD
            else:
                color = self.colors.WHITE

            # Option text
            option_text = self.normal_font.render(option, True, color)
            option_rect = option_text.get_rect(
                left=panel_x + menu_unit(self.presenter, 40), centery=y
            )
            self.screen.blit(option_text, option_rect)

        # Instructions at bottom
        instructions = ["UP/DOWN: Navigate", "ENTER: Select", "ESC: Back"]
        instructions_y = height - menu_unit(self.presenter, 120)
        for instruction in instructions:
            instr_text = self.small_font.render(instruction, True, self.colors.GRAY)
            instr_rect = instr_text.get_rect(centerx=panel_x + panel_width // 2, top=instructions_y)
            self.screen.blit(instr_text, instr_rect)
            instructions_y += menu_unit(self.presenter, 25)

    def navigate(
        self,
        options,
        flush_events: bool = False,
        require_key_release: bool = False,
    ):
        """
        Navigate the shop selection menu and return selected option index.

        Args:
            options: List of shop names to display

        Returns:
            int: Index of selected option, or None if cancelled
        """
        input_armed = prepare_guarded_input(
            flush_events=flush_events,
            require_key_release=require_key_release,
        )

        while True:
            # Draw background and panel
            self.draw_background()
            self.draw_menu_panel(options)
            pygame.display.flip()

            # Handle events
            input_armed = release_guard_allows_input(require_key_release, input_armed)
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    pygame.quit()
                    import sys

                    sys.exit()
                input_armed = update_input_armed_from_event(event, require_key_release, input_armed)
                hovered = hit_index(self.option_rects(options), mouse_position(event))
                if hovered is not None and event.type == pygame.MOUSEMOTION:
                    self.current_selection = hovered
                elif hovered is not None and is_left_click(event):
                    if input_armed:
                        self.current_selection = hovered
                        return self.current_selection
                if event.type == pygame.KEYDOWN:
                    if not input_armed:
                        continue
                    if event.key == pygame.K_UP:
                        self.current_selection = (self.current_selection - 1) % len(options)
                    elif event.key == pygame.K_DOWN:
                        self.current_selection = (self.current_selection + 1) % len(options)
                    elif event.key == pygame.K_RETURN or event.key == pygame.K_SPACE:
                        return self.current_selection
                    elif event.key == pygame.K_ESCAPE:
                        return None  # Cancel

            self.presenter.clock.tick(30)
