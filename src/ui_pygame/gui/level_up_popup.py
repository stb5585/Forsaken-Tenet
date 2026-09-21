"""
Level up information popup.
Displays level up bonuses in a popup overlay.
"""

import pygame

from src.ui_pygame.screen_runtime import get_events

from .input_guards import prepare_guarded_input, release_guard_allows_input


class LevelUpPopup:
    """
    A popup that displays level up information.
    """

    def __init__(self, presenter, level_info):
        """
        Initialize the level up popup.

        Args:
            presenter: The pygame presenter with screen and fonts
            level_info: Dictionary containing level up information
        """
        self.presenter = presenter
        self.screen = presenter.screen
        self.width = presenter.width
        self.height = presenter.height
        self.level_info = level_info

        # Colors
        self.BLACK = (0, 0, 0)
        self.WHITE = (255, 255, 255)
        self.GOLD = (218, 165, 32)
        self.GRAY = (128, 128, 128)
        self.GAIN_COLOR = (100, 255, 100)
        self.POPUP_BG = (20, 20, 30)

        # Fonts
        self.title_font = (
            presenter.title_font if hasattr(presenter, "title_font") else pygame.font.Font(None, 56)
        )
        self.header_font = (
            presenter.header_font
            if hasattr(presenter, "header_font")
            else pygame.font.Font(None, 36)
        )
        self.normal_font = (
            presenter.normal_font
            if hasattr(presenter, "normal_font")
            else pygame.font.Font(None, 28)
        )
        self.small_font = (
            presenter.small_font if hasattr(presenter, "small_font") else pygame.font.Font(None, 22)
        )

        # Calculate content height
        self.content_lines = self._prepare_content()
        self.popup_width = 600
        # Fixed height for consistency
        self.popup_height = 500
        self.popup_x = (self.width - self.popup_width) // 2
        self.popup_y = (self.height - self.popup_height) // 2
        self.popup_rect = pygame.Rect(
            self.popup_x, self.popup_y, self.popup_width, self.popup_height
        )

    def _prepare_content(self):
        """Prepare the content lines to display."""
        lines = []

        # Level line
        lines.append(("header", f"You are now level {self.level_info['new_level']}!"))
        lines.append(("spacer", ""))

        # Stats header
        lines.append(("subheader", "Stats Gained:"))

        # Stats
        lines.append(("gain", f"Health: +{self.level_info['health_gain']}"))
        lines.append(("gain", f"Mana: +{self.level_info['mana_gain']}"))

        if self.level_info["attack_gain"] > 0:
            lines.append(("gain", f"Attack: +{self.level_info['attack_gain']}"))
        if self.level_info["defense_gain"] > 0:
            lines.append(("gain", f"Defense: +{self.level_info['defense_gain']}"))
        if self.level_info["magic_gain"] > 0:
            lines.append(("gain", f"Magic: +{self.level_info['magic_gain']}"))
        if self.level_info["magic_def_gain"] > 0:
            lines.append(("gain", f"Magic Defense: +{self.level_info['magic_def_gain']}"))

        # New abilities
        if self.level_info["new_abilities"]:
            lines.append(("spacer", ""))
            lines.append(("subheader", "New Abilities:"))
            for ability in self.level_info["new_abilities"]:
                lines.append(("ability", ability))

        # Upgrades
        all_upgrades = self.level_info["spell_upgrades"] + self.level_info["skill_upgrades"]
        if all_upgrades:
            lines.append(("spacer", ""))
            lines.append(("subheader", "Upgrades:"))
            for upgrade in all_upgrades:
                lines.append(("ability", upgrade))

        return lines

    def show(
        self,
        background_draw_func=None,
        flush_events: bool = False,
        require_key_release: bool = False,
    ):
        """
        Display the level up popup and wait for user to continue.

        Args:
            background_draw_func: Optional function to draw the background
        """
        waiting = True
        input_armed = prepare_guarded_input(
            flush_events=flush_events,
            require_key_release=require_key_release,
        )

        if background_draw_func is None:
            background = self._get_background_surface()

            def background_draw_func():
                return self.screen.blit(background, (0, 0))

        while waiting:
            # Draw background if provided
            if background_draw_func:
                background_draw_func()

            # Draw popup
            self.draw_popup()

            pygame.display.flip()

            # Handle input
            input_armed = release_guard_allows_input(require_key_release, input_armed)

            for event in get_events():
                if event.type == pygame.QUIT:
                    waiting = False
                elif event.type == pygame.KEYDOWN:
                    if not input_armed:
                        continue
                    waiting = False
                elif (
                    event.type == pygame.MOUSEBUTTONDOWN
                    and getattr(event, "button", None) == 1
                    and input_armed
                ):
                    waiting = False

            self.presenter.clock.tick(30)

    def _get_background_surface(self):
        if hasattr(self.presenter, "get_background_surface"):
            try:
                surface = self.presenter.get_background_surface()
                if surface is not None and surface is not self.screen:
                    return surface
            except Exception:
                pass
        return self.screen.copy()

    def draw_popup(self):
        """Draw the level up popup over the current screen."""
        # Draw semi-transparent overlay
        overlay = pygame.Surface((self.width, self.height))
        overlay.set_alpha(128)
        overlay.fill(self.BLACK)
        self.screen.blit(overlay, (0, 0))

        # Draw popup background
        pygame.draw.rect(self.screen, self.POPUP_BG, self.popup_rect)
        pygame.draw.rect(self.screen, self.GOLD, self.popup_rect, 3)

        # Draw title
        title_text = self.title_font.render("LEVEL UP!", True, self.GOLD)
        title_rect = title_text.get_rect(center=(self.popup_rect.centerx, self.popup_rect.top + 35))
        self.screen.blit(title_text, title_rect)

        # Draw content
        y = self.popup_rect.top + 80
        for line_type, text in self.content_lines:
            if line_type == "spacer":
                y += 15
            elif line_type == "header":
                surface = self.header_font.render(text, True, self.WHITE)
                rect = surface.get_rect(center=(self.popup_rect.centerx, y))
                self.screen.blit(surface, rect)
                y += 40
            elif line_type == "subheader":
                surface = self.normal_font.render(text, True, self.WHITE)
                self.screen.blit(surface, (self.popup_x + 40, y))
                y += 35
            elif line_type == "gain":
                surface = self.normal_font.render(text, True, self.GAIN_COLOR)
                self.screen.blit(surface, (self.popup_x + 60, y))
                y += 30
            elif line_type == "ability":
                surface = self.normal_font.render(text, True, self.GOLD)
                self.screen.blit(surface, (self.popup_x + 60, y))
                y += 30

        # Draw instruction
        instruction_text = self.small_font.render(
            "Click or press any key to continue...", True, self.GRAY
        )
        instruction_rect = instruction_text.get_rect(
            center=(self.popup_rect.centerx, self.popup_rect.bottom - 20)
        )
        self.screen.blit(instruction_text, instruction_rect)
