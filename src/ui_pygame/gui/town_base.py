"""
Base class for all town UI screens.
Centralizes common functionality, colors, fonts, and background management.
"""

import os

import pygame

from src.paths import PYGAME_ASSETS_DIR
from src.ui_common.text import wrap_text_to_width
from src.ui_pygame.assets.npc_art_manager import get_npc_art_manager

from .mouse_helpers import is_left_click


def wrap_text_to_pixel_width(text: str, font: pygame.font.Font, max_width: int) -> list[str]:
    """Wrap text using a Pygame font's rendered pixel widths."""
    return wrap_text_to_width(text, lambda candidate: font.size(candidate)[0], max_width)


class TownColors:
    """Centralized color definitions for town UI."""

    BLACK = (0, 0, 0)
    WHITE = (255, 255, 255)
    GOLD = (218, 165, 32)  # Warm gold for highlights
    YELLOW = (255, 255, 0)  # Bright yellow for special cases
    GRAY = (128, 128, 128)
    LIGHT_GRAY = (192, 192, 192)
    DARK_GRAY = (64, 64, 64)
    BLUE = (100, 149, 237)
    GREEN = (0, 200, 0)
    RED = (200, 0, 0)
    BORDER_COLOR = (200, 200, 200)
    HIGHLIGHT_BG = (60, 60, 80)
    DARK_OVERLAY = (0, 0, 0, 180)  # Semi-transparent black for overlays


class TownScreenBase:
    """
    Base class for all town-related UI screens.
    Manages the town background and provides common functionality.
    """

    def __init__(self, presenter):
        self.presenter = presenter
        self.screen = presenter.screen
        self.width = presenter.width
        self.height = presenter.height

        # Use centralized colors
        self.colors = TownColors

        # Fonts
        self.title_font = presenter.title_font
        self.large_font = presenter.large_font
        self.normal_font = presenter.normal_font
        self.small_font = presenter.small_font

        # Load background once
        self.background = None
        self._npc_portrait_surface_cache = {}
        self._popup_background_draw_func = None
        self._load_background()

    def _load_background(self):
        """Load and scale the town background image."""
        bg_path = PYGAME_ASSETS_DIR / "backgrounds" / "town.png"
        if os.path.exists(bg_path):
            try:
                bg_image = pygame.image.load(bg_path)
                # Scale to fit screen while maintaining aspect ratio
                bg_width, bg_height = bg_image.get_size()
                scale_x = self.width / bg_width
                scale_y = self.height / bg_height
                scale = max(scale_x, scale_y)  # Use max to cover entire screen

                new_width = int(bg_width * scale)
                new_height = int(bg_height * scale)
                self.background = pygame.transform.scale(bg_image, (new_width, new_height))
            except Exception as e:
                print(f"Warning: Could not load town background: {e}")
                self.background = None
        else:
            print(f"Warning: Town background not found at {bg_path}")

    def draw_background(self):
        """Draw the town background image."""
        if self.background:
            # Center the background
            bg_rect = self.background.get_rect(center=(self.width // 2, self.height // 2))
            self.screen.blit(self.background, bg_rect)
        else:
            # Fallback: solid color
            self.screen.fill(self.colors.BLACK)

    def draw_top(self):
        """Draw the top area (can be overridden by subclasses)."""
        pass

    def draw_options(self):
        """Draw the options panel (can be overridden by subclasses)."""
        pass

    def draw_semi_transparent_panel(self, rect, alpha=180):
        """Draw a semi-transparent dark panel."""
        overlay = pygame.Surface((rect.width, rect.height), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, alpha))
        self.screen.blit(overlay, (rect.x, rect.y))
        return overlay

    def popup_show_kwargs(self):
        """Common modal-popup options for town screens."""
        kwargs = {
            "flush_events": True,
            "require_key_release": True,
        }
        if self._popup_background_draw_func is not None:
            kwargs["background_draw_func"] = self._popup_background_draw_func
        return kwargs

    def dialogue_portrait_rect(self) -> pygame.Rect:
        """Return the left-column portrait area below the location options."""
        top_height = self.height // 12
        options_width = self.width // 3
        options_height = self.height // 4
        portrait_y = top_height + options_height
        return pygame.Rect(0, portrait_y, options_width, self.height - portrait_y)

    def npc_portrait_surface(self, *, npc_name: str | None = None, image_path: str = ""):
        """Return a cached NPC portrait surface, or None when art is unavailable."""
        portrait_path = image_path or get_npc_art_manager().get_image_path(npc_name or "")
        if not portrait_path:
            return None
        if portrait_path not in self._npc_portrait_surface_cache:
            try:
                self._npc_portrait_surface_cache[portrait_path] = pygame.image.load(
                    portrait_path
                ).convert_alpha()
            except Exception:
                self._npc_portrait_surface_cache[portrait_path] = None
        return self._npc_portrait_surface_cache[portrait_path]

    def draw_dialogue_portrait(self, portrait_surface, rect: pygame.Rect | None = None) -> None:
        """Draw an optional dialogue portrait under the left-side options."""
        if portrait_surface is None:
            return
        portrait_rect = rect or self.dialogue_portrait_rect()
        if portrait_rect.width <= 0 or portrait_rect.height <= 0:
            return

        self.draw_semi_transparent_panel(portrait_rect)
        pygame.draw.rect(self.screen, self.colors.BORDER_COLOR, portrait_rect, 2)

        art_rect = portrait_rect.inflate(-28, -28)
        source_w, source_h = portrait_surface.get_size()
        scale = min(art_rect.width / max(1, source_w), art_rect.height / max(1, source_h))
        fitted_size = (max(1, int(source_w * scale)), max(1, int(source_h * scale)))
        fitted = pygame.transform.smoothscale(portrait_surface, fitted_size)
        self.screen.blit(fitted, fitted.get_rect(center=art_rect.center))

    def draw_npc_portrait(
        self,
        *,
        npc_name: str | None = None,
        image_path: str = "",
        rect: pygame.Rect | None = None,
    ) -> None:
        """Resolve and draw an NPC portrait when mapped art exists."""
        self.draw_dialogue_portrait(
            self.npc_portrait_surface(npc_name=npc_name, image_path=image_path),
            rect=rect,
        )

    def display_quest_text(self, quest_text, *, npc_name: str | None = None, image_path: str = ""):
        """Display quest text in the content area with slow printing animation."""
        import time

        import pygame

        # Normalize text and peel off a header line if present (====== Name ======)
        text = quest_text.replace("\r\n", "\n")
        header_text = None

        lines = text.split("\n", 1)
        first_line = lines[0].strip()
        if first_line.startswith("======") and first_line.endswith("======"):
            header_text = first_line.replace("=", "").strip()
            text = lines[1] if len(lines) > 1 else ""
        if header_text is None and first_line in {"Quest Complete"}:
            header_text = first_line
            text = lines[1] if len(lines) > 1 else ""
        elif header_text is None and first_line.startswith(("Quest: ", "Quest Complete: ")):
            header_text = first_line
            text = lines[1] if len(lines) > 1 else ""
            if text.startswith("\n"):
                text = text[1:]
        portrait_surface = self.npc_portrait_surface(
            npc_name=npc_name or header_text or "", image_path=image_path
        )

        def text_wrap_width() -> int:
            content_width = 2 * self.width // 3
            return max(1, content_width - 40)

        def wrapped_text_lines() -> list[str]:
            wrapped_lines: list[str] = []
            for raw_line in text.split("\n"):
                if not raw_line.strip():
                    wrapped_lines.append("")
                    continue
                wrapped = wrap_text_to_pixel_width(raw_line, self.large_font, text_wrap_width())
                wrapped_lines.extend(wrapped or [raw_line])
            return wrapped_lines

        def draw_content_formatted(lines_to_draw):
            """Draw content with special formatting for headers."""
            nonlocal header_text
            top_height = self.height // 12
            content_width = 2 * self.width // 3
            content_height = self.height - top_height
            content_x = self.width // 3
            content_y = top_height
            content_rect = pygame.Rect(content_x, content_y, content_width, content_height)

            self.draw_semi_transparent_panel(content_rect)
            pygame.draw.rect(self.screen, self.colors.BORDER_COLOR, content_rect, 2)

            if lines_to_draw:
                text_rect = content_rect.inflate(-40, -40)

                text_x = text_rect.left
                text_y = content_rect.top + 20

                # Draw header (once per frame) if present
                if header_text:
                    surface = self.normal_font.render(header_text, True, self.colors.GOLD)
                    line_width = surface.get_width()
                    centered_x = text_rect.centerx - line_width // 2
                    self.screen.blit(surface, (centered_x, text_y))
                    text_y += self.normal_font.get_height() + 8
                for line in lines_to_draw:
                    if line == "":
                        text_y += self.large_font.get_height()
                        continue

                    surface = self.large_font.render(line, True, self.colors.WHITE)
                    self.screen.blit(surface, (text_x, text_y))
                    text_y += self.large_font.get_height() + 4

        if getattr(self.presenter, "debug_mode", False):
            # Show everything at once in debug
            full_lines = wrapped_text_lines()
            while True:
                self.draw_background()
                self.draw_top()
                self.draw_options()
                self.draw_dialogue_portrait(portrait_surface)
                draw_content_formatted(full_lines)
                pygame.display.flip()

                for event in pygame.event.get():
                    if event.type == pygame.QUIT:
                        pygame.quit()
                        import sys

                        sys.exit()
                    elif event.type == pygame.KEYDOWN or is_left_click(event):
                        return
                self.presenter.clock.tick(30)
        else:
            # Drain any pending key presses before starting slow-print
            try:
                pygame.event.clear(pygame.KEYDOWN)
            except Exception:
                for _ in pygame.event.get():
                    pass
            wrapped_lines = wrapped_text_lines()
            displayed_lines = []
            skipped = False

            for wrapped_line in wrapped_lines:
                if wrapped_line == "":
                    displayed_lines.append("")
                    continue

                displayed_chars = ""
                for char in wrapped_line:
                    displayed_chars += char

                    # Redraw screen
                    self.draw_background()
                    self.draw_top()
                    self.draw_options()
                    self.draw_dialogue_portrait(portrait_surface)

                    draw_content_formatted(displayed_lines + [displayed_chars])
                    pygame.display.flip()

                    time.sleep(0.02)

                    # Skip current dialogue on SPACE/ENTER/ESC or left click.
                    for event in pygame.event.get():
                        if event.type == pygame.QUIT:
                            pygame.quit()
                            import sys

                            sys.exit()
                        elif event.type == pygame.KEYDOWN:
                            if event.key in (pygame.K_SPACE, pygame.K_RETURN, pygame.K_ESCAPE):
                                skipped = True
                                break
                        elif is_left_click(event):
                            skipped = True
                            break
                    if skipped:
                        break

                if skipped:
                    displayed_lines = wrapped_lines
                    break
                else:
                    displayed_lines.append(wrapped_line)

            # Show full dialogue and wait for key to advance.
            while True:
                self.draw_background()
                self.draw_top()
                self.draw_options()
                self.draw_dialogue_portrait(portrait_surface)
                draw_content_formatted(displayed_lines)
                pygame.display.flip()

                for event in pygame.event.get():
                    if event.type == pygame.QUIT:
                        pygame.quit()
                        import sys

                        sys.exit()
                    elif event.type == pygame.KEYDOWN or is_left_click(event):
                        break
                else:
                    self.presenter.clock.tick(30)
                    continue
                break

            # Done with all paragraphs
            return
