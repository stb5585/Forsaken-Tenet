"""Character creation screen for sex selection."""

from __future__ import annotations

import pygame

from .input_guards import (
    prepare_guarded_input,
    release_guard_allows_input,
    update_input_armed_from_event,
)
from .menu_layout import menu_unit, touch_target_height
from .mouse_helpers import hit_index, is_left_click, mouse_position
from .town_base import TownColors

SEX_OPTIONS = ("Male", "Female")


class SexSelectionScreen:
    """Sex selection screen matching the race/class creation layout."""

    def __init__(self, presenter):
        self.presenter = presenter
        self.screen = presenter.screen
        self.width = presenter.width
        self.height = presenter.height
        self.colors = TownColors
        self.title_font = presenter.title_font
        self.normal_font = presenter.normal_font
        self.small_font = presenter.small_font
        self.current_selection = 0
        self.calculate_window_rects()

    def option_rects(self, options: tuple[str, ...] = SEX_OPTIONS) -> list[pygame.Rect]:
        """Return clickable rectangles for visible sex rows."""
        line_height = touch_target_height(self.presenter)
        return [
            pygame.Rect(
                self.list_rect.left + menu_unit(self.presenter, 5),
                self.list_rect.top + menu_unit(self.presenter, 20) + i * line_height,
                self.list_rect.width - menu_unit(self.presenter, 10),
                line_height,
            )
            for i, _option in enumerate(options)
        ]

    def calculate_window_rects(self):
        header_height = self.height // 12
        self.header_rect = pygame.Rect(0, 0, self.width, header_height)

        left_width = self.width // 2
        left_height = self.height - header_height
        self.details_rect = pygame.Rect(0, header_height, left_width, left_height)

        right_width = self.width // 2
        right_height = self.height - header_height
        self.list_rect = pygame.Rect(left_width, header_height, right_width, right_height)

    def draw_header(self) -> None:
        pygame.draw.rect(self.screen, self.colors.BLACK, self.header_rect)
        pygame.draw.rect(self.screen, self.colors.BORDER_COLOR, self.header_rect, 2)

        title = self.normal_font.render("Select the sex for your character", True, self.colors.GOLD)
        title_rect = title.get_rect(centerx=self.width // 2, centery=self.header_rect.centery)
        self.screen.blit(title, title_rect)

    def draw_details(self) -> None:
        pygame.draw.rect(self.screen, self.colors.BLACK, self.details_rect)
        pygame.draw.rect(self.screen, self.colors.BORDER_COLOR, self.details_rect, 2)

        x = self.details_rect.left + 20
        y = self.details_rect.top + 20
        selected = SEX_OPTIONS[self.current_selection]
        title = self.title_font.render(selected, True, self.colors.GOLD)
        self.screen.blit(title, (x, y))

        y += title.get_height() + 22
        desc_header = self.normal_font.render("Description", True, self.colors.GOLD)
        self.screen.blit(desc_header, (x, y))

    def draw_list(self, options: tuple[str, ...] = SEX_OPTIONS) -> None:
        pygame.draw.rect(self.screen, self.colors.BLACK, self.list_rect)
        pygame.draw.rect(self.screen, self.colors.BORDER_COLOR, self.list_rect, 2)

        x = self.list_rect.left + menu_unit(self.presenter, 20)
        option_rects = self.option_rects(options)
        for index, option in enumerate(options):
            y = option_rects[index].centery
            if index == self.current_selection:
                highlight_rect = option_rects[index]
                pygame.draw.rect(self.screen, self.colors.HIGHLIGHT_BG, highlight_rect)
                pygame.draw.rect(self.screen, self.colors.GOLD, highlight_rect, 1)
                color = self.colors.GOLD
            else:
                color = self.colors.WHITE
            text = self.normal_font.render(option, True, color)
            self.screen.blit(text, text.get_rect(left=x, centery=y))

    def draw(self, options: tuple[str, ...] = SEX_OPTIONS) -> None:
        self.screen.fill(self.colors.BLACK)
        self.draw_header()
        self.draw_details()
        self.draw_list(options)

        instructions = self.small_font.render(
            "UP/DOWN: Navigate   ENTER: Select   ESC: Back", True, self.colors.GRAY
        )
        instructions_rect = instructions.get_rect(
            centerx=self.list_rect.centerx, bottom=self.list_rect.bottom - 24
        )
        self.screen.blit(instructions, instructions_rect)

    def navigate(
        self,
        options: tuple[str, ...] = SEX_OPTIONS,
        flush_events: bool = False,
        require_key_release: bool = False,
    ) -> str | None:
        """Return selected sex label, or None when cancelled."""
        input_armed = prepare_guarded_input(
            flush_events=flush_events,
            require_key_release=require_key_release,
        )

        while True:
            self.draw(options)
            pygame.display.flip()

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
                    continue
                if hovered is not None and is_left_click(event):
                    if input_armed:
                        self.current_selection = hovered
                        return options[self.current_selection]
                    continue
                if event.type != pygame.KEYDOWN or not input_armed:
                    continue
                if event.key == pygame.K_UP:
                    self.current_selection = (self.current_selection - 1) % len(options)
                elif event.key == pygame.K_DOWN:
                    self.current_selection = (self.current_selection + 1) % len(options)
                elif event.key in (pygame.K_RETURN, pygame.K_SPACE):
                    return options[self.current_selection]
                elif event.key == pygame.K_ESCAPE:
                    return None

            self.presenter.clock.tick(30)
