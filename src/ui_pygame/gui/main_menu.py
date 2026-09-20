"""
Main menu screen for the Pygame GUI.
"""

import pygame

from src.paths import PYGAME_ASSETS_DIR

from .input_guards import (
    prepare_guarded_input,
    release_guard_allows_input,
    update_input_armed_from_event,
)
from .menu_layout import menu_unit, menu_viewport_size, touch_target_height
from .mouse_helpers import hit_index, is_left_click, mouse_position


class MainMenuScreen:
    """
    Main menu for starting, loading, and configuring the visual game.
    """

    BACKGROUND_PATH = PYGAME_ASSETS_DIR / "backgrounds" / "main_menu.png"

    def __init__(self, presenter):
        self.presenter = presenter
        self.screen = presenter.screen
        self.width = presenter.width
        self.height = presenter.height

        # Colors
        self.BLACK = (0, 0, 0)
        self.WHITE = (255, 255, 255)
        self.GOLD = (218, 165, 32)
        self.GRAY = (128, 128, 128)
        self.BORDER_COLOR = (200, 200, 200)
        self.HIGHLIGHT_BG = (60, 60, 80)

        # Fonts
        self.title_font = presenter.title_font
        self.normal_font = presenter.normal_font
        self.small_font = presenter.small_font
        self.background = self._load_background()

        self.current_option = 0
        self.options = []

    def option_rects(self, options: list[str] | None = None) -> list[pygame.Rect]:
        """Return clickable rectangles for the current menu options."""
        options = options if options is not None else self.options
        width, height = menu_viewport_size(self.presenter)
        target_height = touch_target_height(self.presenter)
        row_gap = menu_unit(self.presenter, 8, minimum=6)
        menu_width = min(menu_unit(self.presenter, 480), width - menu_unit(self.presenter, 48))
        line_height = target_height + row_gap
        menu_height = max(1, len(options)) * line_height + menu_unit(self.presenter, 28)
        menu_y = height - menu_height - menu_unit(self.presenter, 36)
        rects = []
        for i, option in enumerate(options):
            text_width, text_height = self.normal_font.size(option)
            option_width = min(
                menu_width - menu_unit(self.presenter, 24),
                max(menu_unit(self.presenter, 180), text_width + menu_unit(self.presenter, 42)),
            )
            option_height = max(target_height, text_height + menu_unit(self.presenter, 16))
            rects.append(
                pygame.Rect(
                    width // 2 - option_width // 2,
                    menu_y
                    + menu_unit(self.presenter, 14)
                    + i * line_height
                    + text_height // 2
                    - option_height // 2,
                    option_width,
                    option_height,
                )
            )
        return rects

    def _load_background(self):
        """Load the main menu title background if it is available."""
        try:
            return pygame.image.load(str(self.BACKGROUND_PATH))
        except (FileNotFoundError, pygame.error, OSError):
            return None

    def _scale_background(self, image):
        source_width, source_height = image.get_size()
        if source_width <= 0 or source_height <= 0:
            return image, (0, 0)

        scale = max(self.width / source_width, self.height / source_height)
        scaled_size = (int(source_width * scale), int(source_height * scale))
        scaled = pygame.transform.smoothscale(image, scaled_size)
        offset = ((self.width - scaled_size[0]) // 2, (self.height - scaled_size[1]) // 2)
        return scaled, offset

    def draw_background(self):
        """Draw the title background, falling back to a flat fill."""
        if self.background is None:
            self.screen.fill(self.BLACK)
            return

        scaled, offset = self._scale_background(self.background)
        self.screen.blit(scaled, offset)

    def draw_title(self):
        """Draw a text title only when the title background is unavailable."""
        if self.background is not None:
            return

        title = self.title_font.render("The Forsaken Tenet", True, self.GOLD)
        subtitle = self.normal_font.render(
            "A tale of choice, memory, and the Seventh Principle", True, self.WHITE
        )
        title_rect = title.get_rect(centerx=self.width // 2, top=max(40, self.height // 5))
        subtitle_rect = subtitle.get_rect(centerx=self.width // 2, top=title_rect.bottom + 16)
        self.screen.blit(title, title_rect)
        self.screen.blit(subtitle, subtitle_rect)

    def draw_menu(self):
        """Draw the menu options."""
        width, height = menu_viewport_size(self.presenter)
        target_height = touch_target_height(self.presenter)
        row_gap = menu_unit(self.presenter, 8, minimum=6)
        menu_width = min(menu_unit(self.presenter, 480), width - menu_unit(self.presenter, 48))
        line_height = target_height + row_gap
        menu_height = max(1, len(self.options)) * line_height + menu_unit(self.presenter, 28)
        menu_x = width // 2 - menu_width // 2
        menu_y = height - menu_height - menu_unit(self.presenter, 36)

        panel = pygame.Surface((menu_width, menu_height), pygame.SRCALPHA)
        panel.fill((0, 0, 0, 150))
        self.screen.blit(panel, (menu_x, menu_y))

        option_rects = self.option_rects()
        for i, option in enumerate(self.options):
            y = menu_y + menu_unit(self.presenter, 14) + i * line_height
            text = self.normal_font.render(
                option, True, self.BLACK if i == self.current_option else self.WHITE
            )

            # Highlight selected option
            if i == self.current_option:
                pygame.draw.rect(self.screen, self.WHITE, option_rects[i])
                pygame.draw.rect(self.screen, self.GOLD, option_rects[i], 1)
                text_rect = text.get_rect(centerx=width // 2, top=y)
                self.screen.blit(text, text_rect)
            else:
                text_rect = text.get_rect(centerx=width // 2, top=y)
                self.screen.blit(text, text_rect)

    def draw(self):
        """Draw the entire main menu."""
        self.draw_background()
        self.draw_title()
        self.draw_menu()
        pygame.display.flip()

    def navigate(
        self,
        options,
        flush_events: bool = False,
        require_key_release: bool = False,
    ):
        """
        Navigate the main menu and return selected option index.

        Args:
            options: List of menu option strings

        Returns:
            int: Index of selected option, or None if cancelled
        """
        self.options = options

        input_armed = prepare_guarded_input(
            flush_events=flush_events,
            require_key_release=require_key_release,
        )

        while True:
            self.draw()

            input_armed = release_guard_allows_input(require_key_release, input_armed)
            for event in pygame.event.get():
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
                    if event.key == pygame.K_UP:
                        self.current_option = (self.current_option - 1) % len(self.options)
                    elif event.key == pygame.K_DOWN:
                        self.current_option = (self.current_option + 1) % len(self.options)
                    elif event.key == pygame.K_RETURN or event.key == pygame.K_SPACE:
                        return self.current_option
                    elif event.key == pygame.K_ESCAPE:
                        return None

            self.presenter.clock.tick(30)
