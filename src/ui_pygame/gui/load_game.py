"""
Load Game screen for Pygame GUI - matches the shop layout with character details.
"""

import pygame

from src.core.save_system import SaveManager
from src.ui_pygame.assets.portrait_manager import PortraitManager
from src.ui_pygame.screen_runtime import get_events

from .confirmation_popup import ConfirmationPopup
from .input_guards import (
    prepare_guarded_input,
    release_guard_allows_input,
    update_input_armed_from_event,
)
from .menu_layout import menu_unit, touch_target_height
from .mouse_helpers import hit_index, is_left_click, mouse_position


class LoadGameScreen:
    """
    Load game screen that displays save file information in a two-panel layout.
    Left panel: Character details (name, race, class, level, stats, etc.)
    Right panel: List of save files
    """

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

        # State
        self.current_selection = 0
        self.scroll_offset = 0
        self.save_files = []
        self.save_data = []
        try:
            self.portrait_manager = PortraitManager()
        except Exception:
            self.portrait_manager = None

        # Calculate window positions (left for character info, right for file list)
        self.calculate_window_rects()

    def calculate_window_rects(self):
        """Calculate the rectangles for each UI section."""
        # Top header
        header_height = self.height // 12
        self.header_rect = pygame.Rect(0, 0, self.width, header_height)

        # Left panel: Character information
        left_width = self.width // 2
        left_height = self.height - header_height
        self.char_info_rect = pygame.Rect(0, header_height, left_width, left_height)

        # Right panel: Save file list
        right_width = self.width // 2
        right_height = self.height - header_height
        self.file_list_rect = pygame.Rect(left_width, header_height, right_width, right_height)

    def draw_header(self):
        """Draw the header with title."""
        pygame.draw.rect(self.screen, self.BLACK, self.header_rect)
        pygame.draw.rect(self.screen, self.BORDER_COLOR, self.header_rect, 2)

        title = self.normal_font.render("Choose the character to load", True, self.GOLD)
        title_rect = title.get_rect(centerx=self.width // 2, centery=self.header_rect.centery)
        self.screen.blit(title, title_rect)

    def draw_char_info(self):
        """Draw the character information panel."""
        pygame.draw.rect(self.screen, self.BLACK, self.char_info_rect)
        pygame.draw.rect(self.screen, self.BORDER_COLOR, self.char_info_rect, 2)

        if not self.save_data or self.current_selection >= len(self.save_data):
            return

        info = self.save_data[self.current_selection]

        x = self.char_info_rect.left + 20
        y = self.char_info_rect.top + 20
        line_height = 30

        portrait = self._portrait_for_save_info(info)
        details_x = x
        if portrait is not None:
            target_h = min(180, self.char_info_rect.height // 3)
            src_w = max(1, portrait.get_width())
            src_h = max(1, portrait.get_height())
            target_w = max(1, int(src_w * (target_h / src_h)))
            portrait_rect = pygame.Rect(x, y, target_w, target_h)
            try:
                portrait = pygame.transform.smoothscale(portrait, (target_w, target_h))
            except Exception:
                pass
            self.screen.blit(portrait, portrait_rect)
            details_x = portrait_rect.right + 18

        # Character name (bold/larger)
        name_text = self.normal_font.render(info["name"], True, self.GOLD)
        self.screen.blit(name_text, (details_x, y))
        y += line_height * 1.5

        # Character details
        details = [
            f"Level: {info['level']}",
            f"Race: {info['race']}",
            f"Sex: {info.get('sex', 'Unknown')}",
            f"Class: {info['class']}",
        ]

        if "experience" in info:
            details.append(f"Experience: {info['experience']:,}")

        if "gold" in info:
            details.append(f"Gold: {info['gold']}")

        for detail in details:
            text = self.small_font.render(detail, True, self.WHITE)
            self.screen.blit(text, (details_x, y))
            y += line_height

        # Stats if available
        if "stats" in info and info["stats"]:
            y += 10
            if portrait is not None:
                y = max(y, self.char_info_rect.top + 20 + target_h + 18)
            stats_header = self.small_font.render("Stats:", True, self.GOLD)
            self.screen.blit(stats_header, (x, y))
            y += line_height

            for stat_name, stat_value in info["stats"].items():
                stat_text = self.small_font.render(f"{stat_name}: {stat_value}", True, self.WHITE)
                self.screen.blit(stat_text, (x, y))
                y += line_height - 5

    def _portrait_for_save_info(self, info):
        """Return a save preview portrait, falling back silently when unavailable."""
        if not info.get("loadable", True) or self.portrait_manager is None:
            return None
        try:
            return self.portrait_manager.get_portrait(
                info.get("race", "Human"),
                info.get("sex", "Male"),
                class_name=info.get("class"),
                variant=info.get("portrait_variant", 0),
            )
        except Exception:
            return None

    def draw_file_list(self):
        """Draw the save file list panel."""
        pygame.draw.rect(self.screen, self.BLACK, self.file_list_rect)
        pygame.draw.rect(self.screen, self.BORDER_COLOR, self.file_list_rect, 2)

        if not self.save_data:
            no_saves = self.normal_font.render("No save files found", True, self.GRAY)
            no_saves_rect = no_saves.get_rect(
                centerx=self.file_list_rect.centerx, centery=self.file_list_rect.centery
            )
            self.screen.blit(no_saves, no_saves_rect)
            return

        # Draw list header
        x = self.file_list_rect.left + 10
        y = self.file_list_rect.top + 10
        line_height = touch_target_height(self.presenter)

        header = self.small_font.render("Save Files", True, self.GOLD)
        self.screen.blit(header, (x, y))
        y += line_height

        hint = self.small_font.render("DEL/BACKSPACE: Delete selected save", True, self.GRAY)
        hint_rect = hint.get_rect(
            centerx=self.file_list_rect.centerx,
            bottom=self.file_list_rect.bottom - 12,
        )
        self.screen.blit(hint, hint_rect)

        self.ensure_selection_visible()
        if self.scroll_offset > 0:
            up_text = self.small_font.render("^", True, self.GRAY)
            up_rect = up_text.get_rect(
                centerx=self.file_list_rect.centerx, top=self.file_list_rect.top + 32
            )
            self.screen.blit(up_text, up_rect)
        if self.scroll_offset + self.max_visible_saves() < len(self.save_data):
            down_text = self.small_font.render("v", True, self.GRAY)
            down_rect = down_text.get_rect(
                centerx=self.file_list_rect.centerx, bottom=hint_rect.top - 8
            )
            self.screen.blit(down_text, down_rect)

        # Draw file list
        for visible_index, data in enumerate(self.visible_save_data()):
            data_index = self.scroll_offset + visible_index
            highlight_rect = self.save_row_rects()[visible_index]
            y = highlight_rect.top + 2

            # Highlight selected
            if data_index == self.current_selection:
                pygame.draw.rect(self.screen, self.HIGHLIGHT_BG, highlight_rect)
                pygame.draw.rect(self.screen, self.GOLD, highlight_rect, 1)
                color = self.GOLD
            else:
                color = self.WHITE

            # Display file name with level
            file_text = self.small_font.render(f"{data['name']} (Lvl {data['level']})", True, color)
            self.screen.blit(file_text, (x, y))

    def max_visible_saves(self) -> int:
        """Return the number of save rows rendered in the current panel."""
        row_height = touch_target_height(self.presenter)
        header_height = row_height + menu_unit(self.presenter, 20)
        footer_height = menu_unit(self.presenter, 48)
        return max(1, (self.file_list_rect.height - header_height - footer_height) // row_height)

    def max_scroll_offset(self) -> int:
        """Return the highest valid save-list scroll offset."""
        return max(0, len(self.save_data) - self.max_visible_saves())

    def visible_save_data(self) -> list[dict]:
        """Return the save rows currently visible in the file list."""
        end = self.scroll_offset + self.max_visible_saves()
        return self.save_data[self.scroll_offset : end]

    def ensure_selection_visible(self) -> None:
        """Clamp scroll state and keep the selected save inside the visible window."""
        if not self.save_data:
            self.current_selection = 0
            self.scroll_offset = 0
            return
        self.current_selection = max(0, min(self.current_selection, len(self.save_data) - 1))
        if self.current_selection < self.scroll_offset:
            self.scroll_offset = self.current_selection
        visible_count = self.max_visible_saves()
        if self.current_selection >= self.scroll_offset + visible_count:
            self.scroll_offset = self.current_selection - visible_count + 1
        self.scroll_offset = max(0, min(self.scroll_offset, self.max_scroll_offset()))

    def scroll_file_list(self, delta: int) -> None:
        """Scroll the visible save list and keep the selection in view."""
        if not self.save_data:
            self.scroll_offset = 0
            self.current_selection = 0
            return
        self.scroll_offset = max(0, min(self.scroll_offset + int(delta), self.max_scroll_offset()))
        if self.current_selection < self.scroll_offset:
            self.current_selection = self.scroll_offset
        last_visible = min(
            len(self.save_data) - 1, self.scroll_offset + self.max_visible_saves() - 1
        )
        if self.current_selection > last_visible:
            self.current_selection = last_visible

    def save_row_rects(self) -> list[pygame.Rect]:
        """Return clickable rectangles for visible save rows."""
        line_height = touch_target_height(self.presenter)
        rects = []
        for i, _data in enumerate(self.visible_save_data()):
            y = (
                self.file_list_rect.top
                + line_height
                + menu_unit(self.presenter, 10)
                + i * line_height
            )
            rects.append(
                pygame.Rect(
                    self.file_list_rect.left + 5,
                    y - 2,
                    self.file_list_rect.width - 10,
                    line_height - menu_unit(self.presenter, 4),
                )
            )
        return rects

    def draw_all(self):
        """Draw all UI elements."""
        self.screen.fill(self.BLACK)
        self.draw_header()
        self.draw_char_info()
        self.draw_file_list()
        pygame.display.flip()

    def load_save_files(self, save_files):
        """
        Load save file data.

        Args:
            save_files: List of save file paths
        """
        self.save_files = save_files
        self.save_data = []
        self.current_selection = 0
        self.scroll_offset = 0

        for save_file in save_files:
            try:
                metadata = SaveManager.describe_save_file(save_file)
                if (
                    not metadata["valid"]
                    or not metadata["extension_matches_expected"]
                    or not metadata["is_file"]
                ):
                    self.save_data.append(
                        {
                            "name": "Invalid save",
                            "race": "?",
                            "sex": "?",
                            "class": "?",
                            "level": "?",
                            "file": save_file,
                            "loadable": False,
                        }
                    )
                    continue
                if metadata["empty"]:
                    self.save_data.append(
                        {
                            "name": "Corrupted save",
                            "race": "?",
                            "sex": "?",
                            "class": "?",
                            "level": "?",
                            "file": save_file,
                            "loadable": False,
                        }
                    )
                    continue
                if not metadata.get("loadable", True):
                    raw_status = metadata.get("compatibility_status", "")
                    compatibility_status = str(getattr(raw_status, "value", raw_status))
                    incompatible = compatibility_status.endswith(
                        ("pre_foundation", "unsupported_version")
                    )
                    self.save_data.append(
                        {
                            "name": "Incompatible save" if incompatible else "Corrupted save",
                            "race": "?",
                            "sex": "?",
                            "class": "?",
                            "level": "?",
                            "file": save_file,
                            "loadable": False,
                            "status_message": metadata.get(
                                "status_message", "This save cannot be loaded."
                            ),
                        }
                    )
                    continue

                player_char = SaveManager.load_player(save_file)
                if player_char:
                    # Extract character information
                    char_data = {
                        "name": getattr(player_char, "name", "Unknown").title(),
                        "race": getattr(getattr(player_char, "race", None), "name", "Unknown"),
                        "sex": getattr(player_char, "sex", "Unknown"),
                        "class": getattr(getattr(player_char, "cls", None), "name", "Unknown"),
                        "level": (
                            getattr(player_char.level, "level", 1)
                            if hasattr(player_char, "level")
                            else 1
                        ),
                        "experience": (
                            getattr(player_char.level, "exp", 0)
                            if hasattr(player_char, "level")
                            else 0
                        ),
                        "gold": getattr(player_char, "gold", 0),
                        "portrait_variant": getattr(player_char, "portrait_variant", 0),
                        "file": save_file,
                        "loadable": True,
                    }

                    # Try to get stats
                    if hasattr(player_char, "stats"):
                        stats = getattr(player_char, "stats", None)
                        if stats:
                            char_data["stats"] = {
                                "STR": getattr(stats, "strength", 0),
                                "INT": getattr(stats, "intel", 0),
                                "WIS": getattr(stats, "wisdom", 0),
                                "CON": getattr(stats, "con", 0),
                                "CHA": getattr(stats, "charisma", 0),
                                "DEX": getattr(stats, "dex", 0),
                            }

                    self.save_data.append(char_data)
                else:
                    # Corrupted save
                    self.save_data.append(
                        {
                            "name": "Corrupted save",
                            "race": "?",
                            "sex": "?",
                            "class": "?",
                            "level": "?",
                            "file": save_file,
                            "loadable": False,
                        }
                    )
            except Exception:
                # Error loading save
                self.save_data.append(
                    {
                        "name": "Error loading",
                        "race": "?",
                        "sex": "?",
                        "class": "?",
                        "level": "?",
                        "file": save_file,
                        "loadable": False,
                    }
                )

    def show_unloadable_save_notice(self, save_file) -> None:
        """Warn that the selected save cannot be loaded without leaving this screen."""
        save_data = next(
            (entry for entry in self.save_data if entry.get("file") == save_file),
            {},
        )
        reason = save_data.get(
            "status_message",
            f"{save_file} cannot be loaded.\n\nUse DEL/BACKSPACE to delete it.",
        )
        notice = ConfirmationPopup(
            self.presenter,
            reason,
            show_buttons=False,
        )
        self.draw_all()
        notice_background = self.screen.copy()
        notice.show(
            background_draw_func=lambda: self.screen.blit(notice_background, (0, 0)),
            flush_events=True,
            require_key_release=True,
        )

    def delete_selected_save(self) -> bool:
        """Delete the currently selected save file after confirmation."""
        if not self.save_data or self.current_selection >= len(self.save_data):
            return False

        save_file = self.save_data[self.current_selection]["file"]
        popup = ConfirmationPopup(
            self.presenter,
            f"Delete {save_file}? This cannot be undone.",
        )
        self.draw_all()
        popup_background = self.screen.copy()
        if not popup.show(
            background_draw_func=lambda: self.screen.blit(popup_background, (0, 0)),
            flush_events=True,
            require_key_release=True,
        ):
            return False

        if not SaveManager.delete_save(save_file):
            notice = ConfirmationPopup(
                self.presenter,
                f"Could not delete {save_file}.",
                show_buttons=False,
            )
            self.draw_all()
            notice_background = self.screen.copy()
            notice.show(
                background_draw_func=lambda: self.screen.blit(notice_background, (0, 0)),
                flush_events=True,
                require_key_release=True,
            )
            return False

        del self.save_data[self.current_selection]
        if save_file in self.save_files:
            self.save_files.remove(save_file)
        if self.current_selection >= len(self.save_data):
            self.current_selection = max(0, len(self.save_data) - 1)
        self.ensure_selection_visible()
        return True

    def navigate(
        self,
        save_files,
        flush_events: bool = False,
        require_key_release: bool = False,
    ):
        """
        Navigate the load game screen and return selected save file path.

        Args:
            save_files: List of save file paths

        Returns:
            str: Path to selected save file, or None if cancelled
        """
        self.load_save_files(save_files)

        if not self.save_data:
            return None

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
                if event.type == pygame.KEYDOWN:
                    if not input_armed:
                        continue
                    if event.key == pygame.K_UP:
                        self.current_selection = (self.current_selection - 1) % len(self.save_data)
                    elif event.key == pygame.K_DOWN:
                        self.current_selection = (self.current_selection + 1) % len(self.save_data)
                    elif event.key == pygame.K_PAGEUP:
                        self.current_selection = max(
                            0, self.current_selection - self.max_visible_saves()
                        )
                    elif event.key == pygame.K_PAGEDOWN:
                        self.current_selection = min(
                            len(self.save_data) - 1,
                            self.current_selection + self.max_visible_saves(),
                        )
                    elif event.key == pygame.K_RETURN or event.key == pygame.K_SPACE:
                        selected_save = self.save_data[self.current_selection]
                        if selected_save.get("loadable", True):
                            return selected_save["file"]
                        self.show_unloadable_save_notice(selected_save["file"])
                        input_armed = prepare_guarded_input(
                            flush_events=True,
                            require_key_release=True,
                        )
                    elif event.key in (pygame.K_DELETE, pygame.K_BACKSPACE):
                        self.delete_selected_save()
                        if not self.save_data:
                            return None
                        input_armed = prepare_guarded_input(
                            flush_events=True,
                            require_key_release=True,
                        )
                    elif event.key == pygame.K_ESCAPE:
                        return None
                    self.ensure_selection_visible()
                elif event.type == pygame.MOUSEWHEEL:
                    self.scroll_file_list(-event.y)
                elif event.type in (pygame.MOUSEMOTION, pygame.MOUSEBUTTONDOWN):
                    hovered = hit_index(self.save_row_rects(), mouse_position(event))
                    if hovered is None:
                        continue
                    self.current_selection = self.scroll_offset + hovered
                    if not is_left_click(event):
                        continue
                    if not input_armed:
                        continue
                    selected_save = self.save_data[self.current_selection]
                    if selected_save.get("loadable", True):
                        return selected_save["file"]
                    self.show_unloadable_save_notice(selected_save["file"])
                    input_armed = prepare_guarded_input(
                        flush_events=True,
                        require_key_release=True,
                    )

            self.presenter.clock.tick(30)
