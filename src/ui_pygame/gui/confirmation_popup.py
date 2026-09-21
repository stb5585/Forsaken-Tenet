"""
Confirmation popup for character creation decisions.
"""

import pygame

from src.ui_pygame.screen_runtime import get_events

from .input_guards import prepare_guarded_input, release_guard_allows_input
from .mouse_helpers import hit_index, is_left_click, mouse_position


def _get_safe_background_surface(presenter, screen):
    """Return a copied popup background when provider output is unusable."""
    if hasattr(presenter, "get_background_surface"):
        try:
            surface = presenter.get_background_surface()
            if surface is not None and surface is not screen:
                return surface
        except Exception:
            pass
    return screen.copy()


def popup_close_rect(popup_rect: pygame.Rect) -> pygame.Rect:
    """Return the shared close-button hitbox for popup chrome."""
    return pygame.Rect(popup_rect.right - 30, popup_rect.top + 8, 20, 20)


def draw_popup_close_button(
    screen, popup_rect: pygame.Rect, font, *, hovered: bool = False
) -> pygame.Rect:
    """Draw a compact x close button and return its hitbox."""
    rect = popup_close_rect(popup_rect)
    fill = (72, 48, 56) if hovered else (36, 32, 40)
    border = (218, 165, 32) if hovered else (150, 150, 158)
    pygame.draw.rect(screen, fill, rect)
    pygame.draw.rect(screen, border, rect, 1)
    text = font.render("x", True, border)
    screen.blit(text, text.get_rect(center=rect.center))
    return rect


def popup_close_clicked(event, popup_rect: pygame.Rect) -> bool:
    """Return whether a mouse event clicked the shared popup close button."""
    return is_left_click(event) and popup_close_rect(popup_rect).collidepoint(
        mouse_position(event) or (-1, -1)
    )


class ConfirmationPopup:
    """
    A Yes/No confirmation popup that appears over the current screen.
    """

    def __init__(
        self, presenter, message: str, show_buttons: bool = True, slow_print: bool = False
    ):
        self.presenter = presenter
        self.screen = presenter.screen
        self.width = presenter.width
        self.height = presenter.height
        self.message = message
        self.show_buttons = show_buttons
        # Slow print (typewriter) if True; disabled if debug mode is enabled
        self.slow_print = not getattr(presenter, "debug_mode", False) and slow_print
        self._start_ms = 10
        self._reveal_cps = 30  # characters per second

        # Colors
        self.BLACK = (0, 0, 0)
        self.WHITE = (255, 255, 255)
        self.GOLD = (218, 165, 32)  # Warm gold instead of bright yellow
        self.GRAY = (128, 128, 128)
        self.BORDER_COLOR = (200, 200, 200)
        self.HIGHLIGHT_BG = (60, 60, 80)
        self.POPUP_BG = (20, 20, 30)

        # Fonts
        self.normal_font = presenter.normal_font
        self.small_font = presenter.small_font
        self.message_font = presenter.normal_font
        self.instruction_font = presenter.small_font

        # State
        self.current_selection = 0  # 0 = Yes, 1 = No
        self.options = ["Yes", "No"]

        # Calculate popup size based on message content
        self.popup_width = 500
        # First, wrap text to calculate required height
        wrapped_lines = self._wrap_text(message, self.popup_width - 40)
        self._wrapped_lines = wrapped_lines
        self._full_text = "\n".join(wrapped_lines)
        # Each line takes approximately 30 pixels in height, plus padding
        min_height = 150 if show_buttons else 180
        content_height = len(wrapped_lines) * 30
        self.popup_height = max(min_height, content_height + 100)

        self.popup_x = (self.width - self.popup_width) // 2
        self.popup_y = (self.height - self.popup_height) // 2
        self.popup_rect = pygame.Rect(
            self.popup_x, self.popup_y, self.popup_width, self.popup_height
        )

    def button_rects(self) -> list[pygame.Rect]:
        """Return clickable Yes/No button rectangles."""
        y = self.popup_y + self.popup_height - 70
        return [
            pygame.Rect(
                self.popup_x + (self.popup_width // 4) + i * (self.popup_width // 2) - 50,
                y - 5,
                100,
                35,
            )
            for i, _option in enumerate(self.options)
        ]

    def _get_visible_lines(self):
        if not self.slow_print or not self._full_text:
            return self._wrapped_lines
        elapsed_ms = max(0, pygame.time.get_ticks() - self._start_ms)
        visible_chars = int((elapsed_ms / 1000.0) * self._reveal_cps)
        visible_text = self._full_text[:visible_chars]
        return visible_text.split("\n")

    def _reveal_complete(self) -> bool:
        if not self.slow_print:
            return True
        elapsed_ms = max(0, pygame.time.get_ticks() - self._start_ms)
        visible_chars = int((elapsed_ms / 1000.0) * self._reveal_cps)
        return visible_chars >= len(self._full_text)

    def draw_popup(self):
        """Draw the confirmation popup over the current screen."""
        # Draw semi-transparent overlay
        overlay = pygame.Surface((self.width, self.height))
        overlay.set_alpha(180)
        overlay.fill((0, 0, 0))
        self.screen.blit(overlay, (0, 0))

        # Draw popup background
        pygame.draw.rect(self.screen, self.POPUP_BG, self.popup_rect)
        pygame.draw.rect(self.screen, self.BORDER_COLOR, self.popup_rect, 3)
        draw_popup_close_button(self.screen, self.popup_rect, self.small_font)

        # Original compact confirmation layout
        y = self.popup_y + 30
        message_lines = self._get_visible_lines()
        for line in message_lines:
            text = self.normal_font.render(line, True, self.WHITE)
            text_rect = text.get_rect(centerx=self.popup_x + self.popup_width // 2)
            text_rect.y = y
            self.screen.blit(text, text_rect)
            y += 30

        if self.show_buttons:
            y = self.popup_y + self.popup_height - 70
            for i, option in enumerate(self.options):
                x = self.popup_x + (self.popup_width // 4) + i * (self.popup_width // 2)

                if i == self.current_selection:
                    option_rect = self.button_rects()[i]
                    pygame.draw.rect(self.screen, self.HIGHLIGHT_BG, option_rect)
                    pygame.draw.rect(self.screen, self.GOLD, option_rect, 2)
                    color = self.GOLD
                else:
                    color = self.WHITE

                text = self.normal_font.render(option, True, color)
                text_rect = text.get_rect(centerx=x, centery=y + 10)
                self.screen.blit(text, text_rect)
        else:
            instr_text = self.small_font.render("Press any key to continue...", True, self.GRAY)
            instr_rect = instr_text.get_rect(
                centerx=self.popup_x + self.popup_width // 2,
                bottom=self.popup_y + self.popup_height - 10,
            )
            self.screen.blit(instr_text, instr_rect)

        pygame.display.flip()

    def _wrap_text(self, text, max_width):
        """Wrap text to fit within max_width while preserving explicit line breaks."""
        lines = []
        # First split by newlines to preserve explicit line breaks
        paragraphs = text.split("\n")

        for paragraph in paragraphs:
            if not paragraph.strip():
                # Preserve empty lines
                lines.append("")
                continue

            # Then wrap each paragraph by word
            words = paragraph.split()
            current_line = []

            for word in words:
                current_line.append(word)
                line = " ".join(current_line)
                line_width = self.message_font.size(line)[0]

                if line_width > max_width:
                    current_line.pop()
                    if current_line:
                        lines.append(" ".join(current_line))
                    current_line = [word]

            if current_line:
                lines.append(" ".join(current_line))

        return lines

    def show(
        self,
        background_draw_func=None,
        flush_events: bool = False,
        require_key_release: bool = False,
        min_display_ms: int = 0,
    ) -> bool:
        """
        Show the popup and wait for user response.

        Args:
            background_draw_func: Optional function to redraw background screen

        Returns:
            True if Yes (or any key if no buttons), False if No
        """
        # Informational popups must never consume the key/click that opened them.
        # Choice dialogs keep their caller-controlled input behavior.
        if not self.show_buttons:
            flush_events = True
            require_key_release = True

        background = None
        if background_draw_func is None:
            background = self._get_background_surface()

            def background_draw_func():
                return self.screen.blit(background, (0, 0))

        start_ms = pygame.time.get_ticks()
        self._start_ms = start_ms
        input_armed = prepare_guarded_input(
            flush_events=flush_events,
            require_key_release=require_key_release,
        )

        def finish(result: bool) -> bool:
            if background_draw_func is not None:
                background_draw_func()
            elif background is not None:
                self.screen.blit(background, (0, 0))
            return result

        while True:
            # Draw background each frame
            if background_draw_func:
                background_draw_func()

            # Draw popup on top
            self.draw_popup()

            # Arm input once all keys are released (prevents buffered input from skipping popups)
            input_armed = release_guard_allows_input(require_key_release, input_armed)

            for event in get_events():
                if event.type == pygame.QUIT:
                    pygame.quit()
                    import sys

                    sys.exit()
                elif event.type == pygame.KEYDOWN:
                    if not input_armed:
                        continue
                    if self.slow_print and not self._reveal_complete():
                        continue
                    if min_display_ms and (pygame.time.get_ticks() - start_ms) < min_display_ms:
                        continue
                    if self.show_buttons:
                        # Yes/No button behavior
                        if event.key == pygame.K_LEFT:
                            self.current_selection = 0
                        elif event.key == pygame.K_RIGHT:
                            self.current_selection = 1
                        elif event.key == pygame.K_RETURN or event.key == pygame.K_SPACE:
                            return finish(self.current_selection == 0)  # True for Yes, False for No
                        elif event.key == pygame.K_ESCAPE:
                            return finish(False)  # ESC = No
                    else:
                        # Message only - any key to dismiss
                        return finish(True)
                elif event.type in (pygame.MOUSEMOTION, pygame.MOUSEBUTTONDOWN):
                    if not input_armed:
                        continue
                    if self.slow_print and not self._reveal_complete():
                        continue
                    if min_display_ms and (pygame.time.get_ticks() - start_ms) < min_display_ms:
                        continue
                    if popup_close_clicked(event, self.popup_rect):
                        return finish(False if self.show_buttons else True)
                    if self.show_buttons:
                        hovered = hit_index(self.button_rects(), mouse_position(event))
                        if hovered is not None:
                            self.current_selection = hovered
                            if is_left_click(event):
                                return finish(self.current_selection == 0)
                    elif event.type == pygame.MOUSEBUTTONDOWN:
                        return finish(True)

            self.presenter.clock.tick(30)

    def _get_background_surface(self):
        return _get_safe_background_surface(self.presenter, self.screen)


class ChoicePopup:
    """Popup for selecting one option from a list."""

    def __init__(
        self, presenter, title: str, options: list[str], header_message: str | None = None
    ):
        self.presenter = presenter
        self.screen = presenter.screen
        self.width = presenter.width
        self.height = presenter.height
        self.title = title
        self.options = options
        self.header_message = header_message or ""

        # Colors
        self.BLACK = (0, 0, 0)
        self.WHITE = (255, 255, 255)
        self.GOLD = (218, 165, 32)
        self.GRAY = (128, 128, 128)
        self.BORDER_COLOR = (200, 200, 200)
        self.HIGHLIGHT_BG = (60, 60, 80)
        self.POPUP_BG = (20, 20, 30)

        # Fonts
        self.title_font = presenter.title_font
        self.normal_font = presenter.normal_font
        self.small_font = presenter.small_font

        # State
        self.current_selection = 0

        # Layout
        self.popup_width = 520
        max_content_width = self.popup_width - 60
        header_lines = (
            self._wrap_text(self.header_message, max_content_width) if self.header_message else []
        )
        self._header_lines = header_lines
        line_height = 30
        min_height = 220
        content_height = (len(header_lines) + len(self.options)) * line_height + 120
        self.popup_height = max(min_height, content_height)
        self.popup_x = (self.width - self.popup_width) // 2
        self.popup_y = (self.height - self.popup_height) // 2
        self.popup_rect = pygame.Rect(
            self.popup_x, self.popup_y, self.popup_width, self.popup_height
        )

    def option_rects(self) -> list[pygame.Rect]:
        """Return clickable option rectangles."""
        y = self.popup_y + 80 + (28 * len(self._header_lines))
        return [
            pygame.Rect(self.popup_x + 60, y + (i * 30) - 4, self.popup_width - 120, 28)
            for i, _option in enumerate(self.options)
        ]

    def _wrap_text(self, text: str, max_width: int) -> list[str]:
        if not text:
            return []
        words = text.split()
        lines = []
        current_line = []
        for word in words:
            current_line.append(word)
            line = " ".join(current_line)
            if self.normal_font.size(line)[0] > max_width:
                current_line.pop()
                if current_line:
                    lines.append(" ".join(current_line))
                current_line = [word]
        if current_line:
            lines.append(" ".join(current_line))
        return lines

    def _get_background_surface(self):
        return _get_safe_background_surface(self.presenter, self.screen)

    def draw_popup(self, background_surface, do_flip: bool = True):
        self.screen.blit(background_surface, (0, 0))

        overlay = pygame.Surface((self.width, self.height))
        overlay.set_alpha(180)
        overlay.fill((0, 0, 0))
        self.screen.blit(overlay, (0, 0))

        pygame.draw.rect(self.screen, self.POPUP_BG, self.popup_rect)
        pygame.draw.rect(self.screen, self.BORDER_COLOR, self.popup_rect, 3)
        draw_popup_close_button(self.screen, self.popup_rect, self.small_font)

        title_text = self.title_font.render(self.title, True, self.GOLD)
        title_rect = title_text.get_rect(centerx=self.popup_rect.centerx, top=self.popup_y + 20)
        self.screen.blit(title_text, title_rect)

        y = self.popup_y + 70
        for line in self._header_lines:
            text = self.normal_font.render(line, True, self.WHITE)
            text_rect = text.get_rect(centerx=self.popup_rect.centerx)
            text_rect.y = y
            self.screen.blit(text, text_rect)
            y += 28

        y += 10
        for i, option in enumerate(self.options):
            if i == self.current_selection:
                option_rect = self.option_rects()[i]
                pygame.draw.rect(self.screen, self.HIGHLIGHT_BG, option_rect)
                pygame.draw.rect(self.screen, self.GOLD, option_rect, 2)
                color = self.GOLD
            else:
                color = self.WHITE
            text = self.normal_font.render(option, True, color)
            text_rect = text.get_rect(centerx=self.popup_rect.centerx)
            text_rect.y = y
            self.screen.blit(text, text_rect)
            y += 30

        instr = "UP/DOWN: Navigate  ENTER: Select  ESC: Cancel"
        instr_text = self.small_font.render(instr, True, self.GRAY)
        instr_rect = instr_text.get_rect(
            centerx=self.popup_rect.centerx, bottom=self.popup_rect.bottom - 10
        )
        self.screen.blit(instr_text, instr_rect)

        if do_flip:
            pygame.display.flip()

    def show(self) -> int | None:
        background = self._get_background_surface()
        clock = self.presenter.clock

        if not self.options:
            return None

        while True:
            self.draw_popup(background)

            for event in get_events():
                if event.type == pygame.QUIT:
                    pygame.quit()
                    import sys

                    sys.exit()
                elif event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_UP:
                        self.current_selection = (self.current_selection - 1) % len(self.options)
                    elif event.key == pygame.K_DOWN:
                        self.current_selection = (self.current_selection + 1) % len(self.options)
                    elif event.key == pygame.K_RETURN or event.key == pygame.K_SPACE:
                        return self.current_selection
                    elif event.key == pygame.K_ESCAPE:
                        return None
                elif event.type in (pygame.MOUSEMOTION, pygame.MOUSEBUTTONDOWN):
                    if popup_close_clicked(event, self.popup_rect):
                        return None
                    hovered = hit_index(self.option_rects(), mouse_position(event))
                    if hovered is not None:
                        self.current_selection = hovered
                        if is_left_click(event):
                            return self.current_selection

            clock.tick(30)


class RewardSelectionPopup:
    """Popup for selecting a reward with details and inline confirmation."""

    def __init__(self, presenter, title: str, items: list, detail_provider):
        self.presenter = presenter
        self.screen = presenter.screen
        self.width = presenter.width
        self.height = presenter.height
        self.title = title
        self.items = items
        self.detail_provider = detail_provider

        # Colors
        self.BLACK = (0, 0, 0)
        self.WHITE = (255, 255, 255)
        self.GOLD = (218, 165, 32)
        self.GRAY = (128, 128, 128)
        self.BORDER_COLOR = (200, 200, 200)
        self.HIGHLIGHT_BG = (60, 60, 80)
        self.POPUP_BG = (20, 20, 30)

        # Fonts
        self.title_font = presenter.title_font
        self.normal_font = presenter.normal_font
        self.small_font = presenter.small_font

        # State
        self.selected_index = 0

        # Layout
        self.popup_rect = pygame.Rect(
            self.width // 10, self.height // 8, self.width * 8 // 10, self.height * 3 // 4
        )
        self.list_rect = pygame.Rect(
            self.popup_rect.left + 24,
            self.popup_rect.top + 72,
            self.popup_rect.width * 2 // 5,
            self.popup_rect.height - 120,
        )
        self.details_rect = pygame.Rect(
            self.popup_rect.left + self.popup_rect.width * 2 // 5 + 40,
            self.popup_rect.top + 72,
            self.popup_rect.width * 3 // 5 - 64,
            self.popup_rect.height - 160,
        )
        self.line_height = 24

    def row_rects(self) -> list[pygame.Rect]:
        """Return clickable reward-list row rectangles."""
        return [
            pygame.Rect(
                self.list_rect.left + 8,
                self.list_rect.top + 8 + (idx * self.line_height) - 2,
                self.list_rect.width - 16,
                self.line_height,
            )
            for idx, _item in enumerate(self.items)
        ]

    def _get_background_surface(self):
        return _get_safe_background_surface(self.presenter, self.screen)

    def _wrap_text(self, text: str, max_width: int) -> list[str]:
        if not text:
            return []
        lines = []
        for paragraph in text.split("\n"):
            if not paragraph.strip():
                lines.append("")
                continue
            words = paragraph.split()
            current_line = []
            for word in words:
                current_line.append(word)
                line = " ".join(current_line)
                if self.normal_font.size(line)[0] > max_width:
                    current_line.pop()
                    if current_line:
                        lines.append(" ".join(current_line))
                    current_line = [word]
            if current_line:
                lines.append(" ".join(current_line))
        return lines

    def draw_popup(self, background_surface, do_flip: bool = True):
        self.screen.blit(background_surface, (0, 0))

        overlay = pygame.Surface((self.width, self.height))
        overlay.set_alpha(180)
        overlay.fill((0, 0, 0))
        self.screen.blit(overlay, (0, 0))

        pygame.draw.rect(self.screen, self.POPUP_BG, self.popup_rect)
        pygame.draw.rect(self.screen, self.BORDER_COLOR, self.popup_rect, 2)
        draw_popup_close_button(self.screen, self.popup_rect, self.small_font)

        title_text = self.title_font.render(self.title, True, self.GOLD)
        self.screen.blit(
            title_text,
            (self.popup_rect.centerx - title_text.get_width() // 2, self.popup_rect.top + 16),
        )

        pygame.draw.rect(self.screen, self.BLACK, self.list_rect)
        pygame.draw.rect(self.screen, self.BORDER_COLOR, self.list_rect, 2)
        pygame.draw.rect(self.screen, self.BLACK, self.details_rect)
        pygame.draw.rect(self.screen, self.BORDER_COLOR, self.details_rect, 2)

        # List
        y = self.list_rect.top + 8
        text_max_width = self.list_rect.width - 32
        for idx, item in enumerate(self.items):
            name = getattr(item, "name", str(item))
            if self.normal_font.size(name)[0] > text_max_width:
                while name and self.normal_font.size(name + "...")[0] > text_max_width:
                    name = name[:-1]
                name = f"{name}..."
            row_rect = self.row_rects()[idx]
            if idx == self.selected_index:
                pygame.draw.rect(self.screen, self.HIGHLIGHT_BG, row_rect)
                color = self.GOLD
            else:
                color = self.WHITE
            text = self.normal_font.render(name, True, color)
            self.screen.blit(text, (self.list_rect.left + 16, y))
            y += self.line_height

        # Details
        if self.items:
            current_item = self.items[self.selected_index]
            details = self.detail_provider(current_item)
            x = self.details_rect.left + 12
            y = self.details_rect.top + 10
            max_width = self.details_rect.width - 24
            for line in self._wrap_text(details, max_width):
                text = self.normal_font.render(line, True, self.WHITE)
                self.screen.blit(text, (x, y))
                y += self.line_height

        help_str = "UP/DOWN: Navigate  ENTER: Select  ESC: Cancel"
        help_text = self.small_font.render(help_str, True, self.GRAY)
        self.screen.blit(
            help_text,
            (self.popup_rect.left + 16, self.popup_rect.bottom - help_text.get_height() - 12),
        )

        if do_flip:
            pygame.display.flip()

    def show(self, flush_events: bool = False, require_key_release: bool = False) -> int | None:
        background = self._get_background_surface()
        clock = self.presenter.clock
        input_armed = prepare_guarded_input(
            flush_events=flush_events,
            require_key_release=require_key_release,
        )

        if not self.items:
            return None

        while True:
            self.draw_popup(background)

            input_armed = release_guard_allows_input(require_key_release, input_armed)

            for event in get_events():
                if event.type == pygame.QUIT:
                    pygame.quit()
                    import sys

                    sys.exit()
                elif event.type == pygame.KEYDOWN:
                    if not input_armed:
                        continue
                    if event.key == pygame.K_UP:
                        self.selected_index = (self.selected_index - 1) % len(self.items)
                    elif event.key == pygame.K_DOWN:
                        self.selected_index = (self.selected_index + 1) % len(self.items)
                    elif event.key in (pygame.K_RETURN, pygame.K_SPACE):
                        current_item = self.items[self.selected_index]
                        name = getattr(current_item, "name", str(current_item))
                        confirm_popup = ConfirmationPopup(
                            self.presenter, f"Take {name}?", show_buttons=True
                        )
                        choice = confirm_popup.show(
                            background_draw_func=lambda: self.draw_popup(background, do_flip=False),
                            flush_events=True,
                            require_key_release=True,
                        )
                        if choice:
                            return self.selected_index
                    elif event.key == pygame.K_ESCAPE:
                        return None
                elif event.type in (pygame.MOUSEMOTION, pygame.MOUSEBUTTONDOWN):
                    if not input_armed:
                        continue
                    if popup_close_clicked(event, self.popup_rect):
                        return None
                    hovered = hit_index(self.row_rects(), mouse_position(event))
                    if hovered is not None:
                        self.selected_index = hovered
                        if is_left_click(event):
                            current_item = self.items[self.selected_index]
                            name = getattr(current_item, "name", str(current_item))
                            confirm_popup = ConfirmationPopup(
                                self.presenter, f"Take {name}?", show_buttons=True
                            )
                            choice = confirm_popup.show(
                                background_draw_func=lambda: self.draw_popup(
                                    background, do_flip=False
                                ),
                                flush_events=True,
                                require_key_release=True,
                            )
                            if choice:
                                return self.selected_index

            clock.tick(30)


def confirm_yes_no(presenter, message) -> bool:
    """
    Convenience helper for simple Yes/No confirmations.

    Args:
        presenter: Active presenter with screen/clock/fonts
        message: Prompt to display

    Returns:
        bool: True for Yes, False for No (ESC also returns False)
    """
    popup = ConfirmationPopup(presenter, message)
    return popup.show(flush_events=True, require_key_release=True)


class QuantityPopup:
    """
    A popup for selecting quantity with incremental controls.
    UP/DOWN adjusts ones place, LEFT/RIGHT adjusts tens place.
    """

    def __init__(
        self, presenter, item_name, unit_cost=0, max_quantity=999, action="buy", default_quantity=0
    ):
        self.presenter = presenter
        self.screen = presenter.screen
        self.width = presenter.width
        self.height = presenter.height
        self.item_name = item_name
        self.unit_cost = unit_cost
        self.max_quantity = max_quantity
        self.action = action  # "buy", "store", "retrieve", "sell"

        # Colors
        self.BLACK = (0, 0, 0)
        self.WHITE = (255, 255, 255)
        self.GOLD = (218, 165, 32)
        self.GRAY = (128, 128, 128)
        self.BORDER_COLOR = (200, 200, 200)
        self.HIGHLIGHT_BG = (60, 60, 80)
        self.POPUP_BG = (20, 20, 30)

        # Fonts
        self.title_font = presenter.title_font
        self.normal_font = presenter.normal_font
        self.small_font = presenter.small_font

        # State - quantity as [tens, ones], initialized from default_quantity
        default_quantity = min(default_quantity, max_quantity)  # Clamp to max
        self.tens = (default_quantity // 10) % 10
        self.ones = default_quantity % 10
        self.selected_place = 0  # 0 = ones, 1 = tens
        self.focus_control = "ones"

        # Calculate popup position (centered)
        self.popup_width = 500
        self.popup_height = 300
        self.popup_x = (self.width - self.popup_width) // 2
        self.popup_y = (self.height - self.popup_height) // 2
        self.popup_rect = pygame.Rect(
            self.popup_x, self.popup_y, self.popup_width, self.popup_height
        )

    def digit_rects(self) -> list[pygame.Rect]:
        """Return clickable tens/ones rectangles in index order [tens, ones]."""
        qty_y = self.popup_y + 80
        return [
            pygame.Rect(self.popup_x + 250 - 30, qty_y - 10, 60, 50),
            pygame.Rect(self.popup_x + 320 - 30, qty_y - 10, 60, 50),
        ]

    def button_rects(self) -> dict[str, pygame.Rect]:
        """Return clickable Confirm/Cancel button rectangles."""
        button_y = self.popup_y + 212
        return {
            "confirm": pygame.Rect(self.popup_rect.centerx - 150, button_y, 130, 36),
            "cancel": pygame.Rect(self.popup_rect.centerx + 20, button_y, 130, 36),
        }

    @property
    def quantity(self):
        """Get current quantity."""
        return self.tens * 10 + self.ones

    def _focus_order(self) -> list[str]:
        return ["tens", "ones", "confirm", "cancel"]

    def _set_focus(self, control: str) -> None:
        if control not in self._focus_order():
            return
        self.focus_control = control
        if control == "tens":
            self.selected_place = 1
        elif control == "ones":
            self.selected_place = 0

    def _move_focus(self, delta: int) -> None:
        order = self._focus_order()
        index = order.index(self.focus_control) if self.focus_control in order else 1
        self._set_focus(order[(index + delta) % len(order)])

    def draw_popup(self, background_draw_func=None):
        """Draw the quantity popup over the current screen."""
        # Draw background if provided
        if background_draw_func:
            background_draw_func()
        else:
            self.screen.fill(self.BLACK)

        # Draw semi-transparent overlay
        overlay = pygame.Surface((self.width, self.height))
        overlay.set_alpha(180)
        overlay.fill((0, 0, 0))
        self.screen.blit(overlay, (0, 0))

        # Draw popup background
        pygame.draw.rect(self.screen, self.POPUP_BG, self.popup_rect)
        pygame.draw.rect(self.screen, self.BORDER_COLOR, self.popup_rect, 3)
        draw_popup_close_button(self.screen, self.popup_rect, self.small_font)

        # Title based on action
        if self.action == "store":
            title = f"Store {self.item_name}"
        elif self.action == "retrieve":
            title = f"Retrieve {self.item_name}"
        elif self.action == "sell":
            title = f"Sell {self.item_name}"
        else:
            title = f"Buy {self.item_name}"

        title_text = self.title_font.render(title, True, self.GOLD)
        title_rect = title_text.get_rect(centerx=self.popup_rect.centerx, top=self.popup_y + 20)
        self.screen.blit(title_text, title_rect)

        # Quantity selector with tens and ones
        qty_y = self.popup_y + 80
        qty_label = self.normal_font.render("Quantity:", True, self.WHITE)
        self.screen.blit(qty_label, (self.popup_x + 50, qty_y))

        # Tens place
        tens_x = self.popup_x + 250
        tens_highlight = pygame.Rect(tens_x - 30, qty_y - 10, 60, 50)
        if self.focus_control == "tens":
            pygame.draw.rect(self.screen, self.HIGHLIGHT_BG, tens_highlight)
            pygame.draw.rect(self.screen, self.GOLD, tens_highlight, 2)
            tens_color = self.GOLD
        else:
            tens_color = self.WHITE

        tens_text = self.title_font.render(str(self.tens), True, tens_color)
        self.screen.blit(tens_text, (tens_x - tens_text.get_width() // 2, qty_y))

        # Ones place
        ones_x = self.popup_x + 320
        ones_highlight = pygame.Rect(ones_x - 30, qty_y - 10, 60, 50)
        if self.focus_control == "ones":
            pygame.draw.rect(self.screen, self.HIGHLIGHT_BG, ones_highlight)
            pygame.draw.rect(self.screen, self.GOLD, ones_highlight, 2)
            ones_color = self.GOLD
        else:
            ones_color = self.WHITE

        ones_text = self.title_font.render(str(self.ones), True, ones_color)
        self.screen.blit(ones_text, (ones_x - ones_text.get_width() // 2, qty_y))

        # Total cost/value
        cost_y = self.popup_y + 160
        if self.unit_cost > 0:
            total_value = self.quantity * self.unit_cost
            if self.action == "sell":
                cost_text = self.normal_font.render(f"Total Value: {total_value}g", True, self.GOLD)
            elif self.action == "buy":
                cost_text = self.normal_font.render(f"Total Cost: {total_value}g", True, self.GOLD)
            else:
                cost_text = None

            if cost_text:
                cost_rect = cost_text.get_rect(centerx=self.popup_rect.centerx, top=cost_y)
                self.screen.blit(cost_text, cost_rect)

        # Instructions
        instr_y = self.popup_y + 254
        instr1 = self.small_font.render(
            "UP/DOWN: Adjust | LEFT/RIGHT: Switch | ENTER: Confirm | ESC: Cancel", True, self.GRAY
        )
        instr_rect = instr1.get_rect(centerx=self.popup_rect.centerx, top=instr_y)
        self.screen.blit(instr1, instr_rect)

        for label, rect in self.button_rects().items():
            focused = self.focus_control == label
            disabled_confirm = label == "confirm" and self.quantity <= 0
            fill_color = self.HIGHLIGHT_BG if focused else self.POPUP_BG
            border_color = self.GOLD if focused else self.BORDER_COLOR
            text_color = self.GRAY if disabled_confirm else (self.GOLD if focused else self.WHITE)
            pygame.draw.rect(self.screen, fill_color, rect)
            pygame.draw.rect(self.screen, border_color, rect, 2)
            text = self.small_font.render(label.title(), True, text_color)
            text_rect = text.get_rect(center=rect.center)
            self.screen.blit(text, text_rect)

    def show(
        self,
        background_draw_func=None,
        flush_events: bool = False,
        require_key_release: bool = False,
    ):
        """
        Show the quantity popup and return selected quantity or None if cancelled.

        Args:
            background_draw_func: Optional function to draw the background

        Returns:
            int: Selected quantity, or None if cancelled
        """
        background = None
        if background_draw_func is None:
            background = self._get_background_surface()

            def background_draw_func():
                return self.screen.blit(background, (0, 0))

        def finish(result):
            if background_draw_func is not None:
                background_draw_func()
            elif background is not None:
                self.screen.blit(background, (0, 0))
            return result

        input_armed = prepare_guarded_input(
            flush_events=flush_events,
            require_key_release=require_key_release,
        )

        while True:
            self.draw_popup(background_draw_func)
            pygame.display.flip()

            input_armed = release_guard_allows_input(require_key_release, input_armed)

            for event in get_events():
                if event.type == pygame.QUIT:
                    pygame.quit()
                    import sys

                    sys.exit()
                elif event.type == pygame.KEYDOWN:
                    if not input_armed:
                        continue
                    if event.key == pygame.K_ESCAPE:
                        return finish(None)
                    elif event.key == pygame.K_UP:
                        # Increase current digit (clamp to 0-9)
                        if self.focus_control not in {"ones", "tens"}:
                            continue
                        if self.selected_place == 0:  # Ones
                            self.ones = min(9, self.ones + 1)
                        else:  # Tens
                            self.tens = min(9, self.tens + 1)

                        # Ensure we don't exceed max quantity
                        if self.quantity > self.max_quantity:
                            if self.selected_place == 0:
                                self.ones = max(0, self.ones - 1)
                            else:
                                self.tens = max(0, self.tens - 1)

                    elif event.key == pygame.K_DOWN:
                        # Decrease current digit (clamp to 0-9)
                        if self.focus_control not in {"ones", "tens"}:
                            continue
                        if self.selected_place == 0:  # Ones
                            self.ones = max(0, self.ones - 1)
                        else:  # Tens
                            self.tens = max(0, self.tens - 1)

                    elif event.key == pygame.K_LEFT:
                        self._move_focus(-1)

                    elif event.key == pygame.K_RIGHT:
                        self._move_focus(1)

                    elif event.key == pygame.K_RETURN or event.key == pygame.K_SPACE:
                        if self.focus_control == "cancel":
                            return finish(None)
                        if self.quantity > 0:
                            return finish(self.quantity)
                elif event.type in (pygame.MOUSEMOTION, pygame.MOUSEBUTTONDOWN, pygame.MOUSEWHEEL):
                    if not input_armed:
                        continue
                    if popup_close_clicked(event, self.popup_rect):
                        return finish(None)
                    if event.type == pygame.MOUSEWHEEL:
                        delta = 1 if getattr(event, "y", 0) > 0 else -1
                        if self.selected_place == 0:
                            self.ones = max(0, min(9, self.ones + delta))
                        else:
                            self.tens = max(0, min(9, self.tens + delta))
                        if self.quantity > self.max_quantity:
                            if self.selected_place == 0:
                                self.ones = max(0, self.ones - 1)
                            else:
                                self.tens = max(0, self.tens - 1)
                        continue
                    digit_hit = hit_index(self.digit_rects(), mouse_position(event))
                    if digit_hit is not None:
                        self._set_focus("tens" if digit_hit == 0 else "ones")
                        continue
                    buttons = self.button_rects()
                    pos = mouse_position(event)
                    for label, rect in buttons.items():
                        if rect.collidepoint(pos or (-1, -1)):
                            self._set_focus(label)
                            break
                    if is_left_click(event):
                        if buttons["confirm"].collidepoint(pos or (-1, -1)) and self.quantity > 0:
                            return finish(self.quantity)
                        if buttons["cancel"].collidepoint(pos or (-1, -1)):
                            return finish(None)

            self.presenter.clock.tick(30)

    def _get_background_surface(self):
        return _get_safe_background_surface(self.presenter, self.screen)


class CodeEntryPopup:
    """Popup for entering a 4-digit code."""

    def __init__(self, presenter, title: str, message: str):
        self.presenter = presenter
        self.screen = presenter.screen
        self.width = presenter.width
        self.height = presenter.height
        self.title = title
        self.message = message
        self.digits = [0, 0, 0, 0]
        self.selected_digit = 0

        self.WHITE = (255, 255, 255)
        self.GOLD = (218, 165, 32)
        self.GRAY = (128, 128, 128)
        self.BORDER_COLOR = (200, 200, 200)
        self.HIGHLIGHT_BG = (60, 60, 80)
        self.POPUP_BG = (20, 20, 30)

        self.title_font = presenter.title_font
        self.normal_font = presenter.normal_font
        self.small_font = presenter.small_font

        self.popup_width = 560
        self.popup_height = 260
        self.popup_x = (self.width - self.popup_width) // 2
        self.popup_y = (self.height - self.popup_height) // 2
        self.popup_rect = pygame.Rect(
            self.popup_x, self.popup_y, self.popup_width, self.popup_height
        )

    def digit_rects(self) -> list[pygame.Rect]:
        """Return clickable code digit rectangles."""
        digit_y = self.popup_y + 130
        spacing = 72
        start_x = self.popup_rect.centerx - (spacing * 3) // 2
        return [
            pygame.Rect(start_x + idx * spacing - 24, digit_y - 8, 48, 64)
            for idx in range(len(self.digits))
        ]

    def button_rects(self) -> dict[str, pygame.Rect]:
        """Return clickable Confirm/Cancel button rectangles."""
        button_y = self.popup_y + 204
        return {
            "confirm": pygame.Rect(self.popup_rect.centerx - 150, button_y, 130, 34),
            "cancel": pygame.Rect(self.popup_rect.centerx + 20, button_y, 130, 34),
        }

    def draw_popup(self, background_draw_func):
        if background_draw_func:
            background_draw_func()

        overlay = pygame.Surface((self.width, self.height))
        overlay.set_alpha(180)
        overlay.fill((0, 0, 0))
        self.screen.blit(overlay, (0, 0))

        pygame.draw.rect(self.screen, self.POPUP_BG, self.popup_rect)
        pygame.draw.rect(self.screen, self.BORDER_COLOR, self.popup_rect, 3)
        draw_popup_close_button(self.screen, self.popup_rect, self.small_font)

        title_text = self.title_font.render(self.title, True, self.GOLD)
        title_rect = title_text.get_rect(centerx=self.popup_rect.centerx, top=self.popup_y + 18)
        self.screen.blit(title_text, title_rect)

        message_text = self.normal_font.render(self.message, True, self.WHITE)
        message_rect = message_text.get_rect(centerx=self.popup_rect.centerx, top=self.popup_y + 72)
        self.screen.blit(message_text, message_rect)

        self.popup_y + 130
        spacing = 72
        start_x = self.popup_rect.centerx - (spacing * 3) // 2
        for idx, digit in enumerate(self.digits):
            start_x + idx * spacing
            rect = self.digit_rects()[idx]
            if idx == self.selected_digit:
                pygame.draw.rect(self.screen, self.HIGHLIGHT_BG, rect)
                pygame.draw.rect(self.screen, self.GOLD, rect, 2)
                color = self.GOLD
            else:
                pygame.draw.rect(self.screen, self.POPUP_BG, rect)
                pygame.draw.rect(self.screen, self.BORDER_COLOR, rect, 1)
                color = self.WHITE
            digit_text = self.title_font.render(str(digit), True, color)
            digit_rect = digit_text.get_rect(center=rect.center)
            self.screen.blit(digit_text, digit_rect)

        instructions = self.small_font.render(
            "UP/DOWN: Adjust | LEFT/RIGHT: Move | ENTER: Confirm | ESC: Cancel",
            True,
            self.GRAY,
        )
        instructions_rect = instructions.get_rect(
            centerx=self.popup_rect.centerx, top=self.popup_y + 220
        )
        self.screen.blit(instructions, instructions_rect)

        for label, rect in self.button_rects().items():
            pygame.draw.rect(
                self.screen, self.HIGHLIGHT_BG if label == "confirm" else self.POPUP_BG, rect
            )
            pygame.draw.rect(
                self.screen, self.GOLD if label == "confirm" else self.BORDER_COLOR, rect, 2
            )
            text = self.small_font.render(
                label.title(), True, self.GOLD if label == "confirm" else self.WHITE
            )
            text_rect = text.get_rect(center=rect.center)
            self.screen.blit(text, text_rect)

        pygame.display.flip()

    def show(
        self,
        background_draw_func=None,
        flush_events: bool = False,
        require_key_release: bool = False,
    ):
        background = None
        if background_draw_func is None:
            background = self._get_background_surface()

            def background_draw_func():
                return self.screen.blit(background, (0, 0))

        def finish(result):
            if background_draw_func is not None:
                background_draw_func()
            elif background is not None:
                self.screen.blit(background, (0, 0))
            return result

        input_armed = prepare_guarded_input(
            flush_events=flush_events,
            require_key_release=require_key_release,
        )

        while True:
            self.draw_popup(background_draw_func)
            input_armed = release_guard_allows_input(require_key_release, input_armed)

            for event in get_events():
                if event.type == pygame.QUIT:
                    pygame.quit()
                    import sys

                    sys.exit()
                if event.type == pygame.KEYDOWN:
                    if not input_armed:
                        continue
                    if event.key == pygame.K_ESCAPE:
                        return finish(None)
                    if event.key == pygame.K_LEFT:
                        self.selected_digit = max(0, self.selected_digit - 1)
                    elif event.key == pygame.K_RIGHT:
                        self.selected_digit = min(3, self.selected_digit + 1)
                    elif event.key == pygame.K_UP:
                        self.digits[self.selected_digit] = min(
                            9, self.digits[self.selected_digit] + 1
                        )
                    elif event.key == pygame.K_DOWN:
                        self.digits[self.selected_digit] = max(
                            0, self.digits[self.selected_digit] - 1
                        )
                    elif event.key in (pygame.K_RETURN, pygame.K_SPACE):
                        return finish("".join(str(digit) for digit in self.digits))
                elif event.type in (pygame.MOUSEMOTION, pygame.MOUSEBUTTONDOWN, pygame.MOUSEWHEEL):
                    if not input_armed:
                        continue
                    if popup_close_clicked(event, self.popup_rect):
                        return finish(None)
                    if event.type == pygame.MOUSEWHEEL:
                        delta = 1 if getattr(event, "y", 0) > 0 else -1
                        self.digits[self.selected_digit] = max(
                            0, min(9, self.digits[self.selected_digit] + delta)
                        )
                        continue
                    digit_hit = hit_index(self.digit_rects(), mouse_position(event))
                    if digit_hit is not None:
                        self.selected_digit = digit_hit
                        continue
                    if is_left_click(event):
                        buttons = self.button_rects()
                        pos = mouse_position(event)
                        if buttons["confirm"].collidepoint(pos or (-1, -1)):
                            return finish("".join(str(digit) for digit in self.digits))
                        if buttons["cancel"].collidepoint(pos or (-1, -1)):
                            return finish(None)
            self.presenter.clock.tick(30)

    def _get_background_surface(self):
        return _get_safe_background_surface(self.presenter, self.screen)
