"""
Town Menu screen for Pygame GUI with background image.
"""

import textwrap

import pygame

from .input_guards import (
    prepare_guarded_input,
    release_guard_allows_input,
    update_input_armed_from_event,
)
from .mouse_helpers import hit_index, is_left_click, mouse_position
from .town_base import TownScreenBase

_TOWN_MENU_POINTER_COOLDOWN_MS = 180


class TownMenuScreen(TownScreenBase):
    """
    Town menu screen that displays the town background and location options.
    """

    LOCATION_DETAILS = {
        "Barracks": (
            "Sergeant's maps, casualty ledgers, and the quartermaster's storage lockers crowd the command room."
        ),
        "Shops": (
            "Lanterns burn over the counters while Griswold, the Alchemist, the Jeweler, Seraphine Voss, and Mara Vale prepare their wares."
        ),
        "The Thirsty Dog Tavern": (
            "Patrons trade rumors in low voices, and the Busboy hears more than anyone realizes."
        ),
        "Church of Elysia": (
            "The priest keeps vigil by candlelight, ready to heal wounds and bless the road ahead."
        ),
        "Enter Dungeon": (
            "The dungeon mouth waits beyond town, cold air spilling from the stairwell below."
        ),
        "Old Warehouse": (
            "Guards watch the reinforced doors and turn away anyone without warehouse business."
        ),
        "Warp Point": (
            "Two field scientists watch the brass-ringed platform, hands never far from the lever bank."
        ),
        "Character Menu": (
            "Review equipment, inventory, quests, and key items before stepping back into danger."
        ),
        "Statistics": (
            "Review the record of your run: travel, combat, survival, and personal bests."
        ),
        "Settings": ("Adjust fullscreen and native render resolution."),
        "Quit to Main Menu": ("Step away from Silvana and return to the main menu."),
    }

    def __init__(self, presenter):
        super().__init__(presenter)
        # Menu state
        self.current_selection = 0

    def option_rects(self, options) -> list[pygame.Rect]:
        """Return clickable rectangles for the visible town options."""
        panel_width = 400
        panel_x = self.width - panel_width
        options_start_y = 150
        line_height = 50
        return [
            pygame.Rect(
                panel_x + 20,
                options_start_y + i * line_height - 5,
                panel_width - 40,
                line_height - 10,
            )
            for i, _option in enumerate(options)
        ]

    def draw_menu_panel(self, options):
        """Draw the semi-transparent menu panel with options."""
        panel_width = 400
        panel_height = self.height
        panel_x = self.width - panel_width
        panel_y = 0

        # Create semi-transparent overlay
        panel_rect = pygame.Rect(panel_x, panel_y, panel_width, panel_height)
        self.draw_semi_transparent_panel(panel_rect)

        # Draw border
        pygame.draw.rect(self.screen, self.colors.GOLD, panel_rect, 3)

        # Title
        title_text = self.title_font.render("Town of Silvana", True, self.colors.GOLD)
        title_rect = title_text.get_rect(centerx=panel_x + panel_width // 2, top=40)
        self.screen.blit(title_text, title_rect)

        # Options list
        options_start_y = 150
        line_height = 50

        option_rects = self.option_rects(options)
        for i, option in enumerate(options):
            y = options_start_y + i * line_height

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
            option_rect = option_text.get_rect(left=panel_x + 40, centery=y + 15)
            self.screen.blit(option_text, option_rect)

        self.draw_location_detail(options)

        # Instructions at bottom
        instructions = ["UP/DOWN: Navigate", "ENTER: Select", "ESC: Quit"]
        if getattr(self.presenter, "debug_mode", False):
            instructions.append("L: Debug Level Up")
        instructions_y = self.height - 120
        for instruction in instructions:
            instr_text = self.small_font.render(instruction, True, self.colors.GRAY)
            instr_rect = instr_text.get_rect(centerx=panel_x + panel_width // 2, top=instructions_y)
            self.screen.blit(instr_text, instr_rect)
            instructions_y += 25

    def draw_location_detail(self, options):
        """Draw contextual flavor for the currently selected town location."""
        if not options:
            return

        selected = options[max(0, min(self.current_selection, len(options) - 1))]
        detail = self.LOCATION_DETAILS.get(selected)
        if not detail:
            return

        panel_margin = 24
        detail_rect = pygame.Rect(
            panel_margin,
            self.height - 150,
            max(260, self.width - 400 - (panel_margin * 2)),
            112,
        )
        self.draw_semi_transparent_panel(detail_rect, alpha=170)
        pygame.draw.rect(self.screen, self.colors.BORDER_COLOR, detail_rect, 2)

        title_surface = self.normal_font.render(selected, True, self.colors.GOLD)
        self.screen.blit(title_surface, (detail_rect.left + 16, detail_rect.top + 12))

        text_y = detail_rect.top + 42
        for line in textwrap.wrap(detail, width=58)[:3]:
            line_surface = self.small_font.render(line, True, self.colors.WHITE)
            self.screen.blit(line_surface, (detail_rect.left + 16, text_y))
            text_y += 20

    def navigate(
        self,
        options,
        flush_events: bool = False,
        require_key_release: bool = False,
    ):
        """
        Navigate the town menu and return selected option index.

        Args:
            options: List of location names to display

        Returns:
            int: Index of selected option, or None if cancelled
        """
        input_armed = prepare_guarded_input(
            flush_events=flush_events,
            require_key_release=require_key_release,
        )
        pointer_armed_at = getattr(self.presenter, "_town_menu_pointer_armed_at", 0)

        while True:
            # Draw everything
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
                        try:
                            if pygame.time.get_ticks() < pointer_armed_at:
                                continue
                            self.presenter._town_menu_pointer_armed_at = (
                                pygame.time.get_ticks() + _TOWN_MENU_POINTER_COOLDOWN_MS
                            )
                        except pygame.error:
                            pass
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
                    elif event.key == pygame.K_l and getattr(self.presenter, "debug_mode", False):
                        game = getattr(self.presenter, "game", None)
                        if game and hasattr(game, "debug_level_up"):
                            game.debug_level_up()
                    elif event.key == pygame.K_ESCAPE:
                        # Return the last option (typically Quit)
                        return len(options) - 1

            self.presenter.clock.tick(30)
