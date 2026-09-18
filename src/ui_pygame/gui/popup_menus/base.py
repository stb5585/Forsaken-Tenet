"""Shared popup presentation and input behavior."""

from pathlib import Path

import pygame

from src.paths import PYGAME_ASSETS_DIR
from src.ui_pygame.assets.icon_manager import IconManager
from src.ui_pygame.assets.item_render_manager import get_item_render_manager

from ..confirmation_popup import draw_popup_close_button, popup_close_clicked
from ..input_guards import (
    prepare_guarded_input,
    release_guard_allows_input,
    update_input_armed_from_event,
)
from ..mouse_helpers import is_left_click, mouse_position

ITEM_ART_DIR = PYGAME_ASSETS_DIR / "item_art"
RELIC_ART_FILES = {
    "Triangulus": Path("special/relics/triangulus.png"),
    "Quadrata": Path("special/relics/quadrata.png"),
    "Hexagonum": Path("special/relics/hexagonum.png"),
    "Luna": Path("special/relics/luna.png"),
    "Polaris": Path("special/relics/polaris.png"),
    "Infinitas": Path("special/relics/infinitas.png"),
    "Golden Chalice": Path("special/story/golden_chalice.png"),
}


class BasePopupMenu:
    def __init__(self, presenter, parent_screen, title="Menu"):
        self.presenter = presenter
        self.parent_screen = parent_screen  # Character menu/screen instance for background draw
        self.screen = presenter.screen
        self.width = presenter.width
        self.height = presenter.height

        self.title = title

        # Colors
        self.BLACK = (0, 0, 0)
        self.WHITE = (255, 255, 255)
        self.GOLD = (218, 165, 32)
        self.GREEN = (95, 210, 110)
        self.RED = (230, 90, 80)
        self.GRAY = (128, 128, 128)
        self.LIGHT_GRAY = (192, 192, 192)
        self.BORDER_COLOR = (200, 200, 200)
        self.HIGHLIGHT_BG = (60, 60, 80)

        # Fonts
        self.title_font = presenter.title_font
        self.large_font = presenter.large_font
        self.normal_font = presenter.normal_font
        self.small_font = presenter.small_font
        self.icon_manager = IconManager()
        self.item_render_manager = get_item_render_manager()
        self._relic_sprite_cache: dict[str, pygame.Surface] = {}

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
            self.popup_rect.height - 120,
        )

        # Data
        self.items = []  # list of displayable items (objects or strings)
        self.selected_index = 0
        self.scroll_offset = 0
        self.line_height = 24
        self.quick_scroll_delay = 10
        self._quick_scroll_frame = 0

    def _truncate_text(self, text, max_width):
        """Truncate text with ellipsis to fit within max_width pixels."""
        if self.normal_font.size(text)[0] <= max_width:
            return text
        ellipsis = "..."
        max_width = max(0, max_width - self.normal_font.size(ellipsis)[0])
        if max_width <= 0:
            return ellipsis
        truncated = text
        while truncated and self.normal_font.size(truncated)[0] > max_width:
            truncated = truncated[:-1]
        return f"{truncated}{ellipsis}"

    def _ensure_visible(self):
        """Ensure selected_index is visible and scroll_offset is clamped."""
        if not self.items:
            self.selected_index = 0
            self.scroll_offset = 0
            return
        max_visible = self.visible_row_count()
        max_scroll = max(0, len(self.items) - max_visible)
        self.selected_index = max(0, min(self.selected_index, len(self.items) - 1))
        if self.selected_index < self.scroll_offset:
            self.scroll_offset = self.selected_index
        if self.selected_index >= self.scroll_offset + max_visible:
            self.scroll_offset = self.selected_index - max_visible + 1
        self.scroll_offset = max(0, min(self.scroll_offset, max_scroll))

    def _is_selectable_index(self, index: int) -> bool:
        if index < 0 or index >= len(self.items):
            return False
        item = self.items[index]
        return not (isinstance(item, dict) and item.get("is_header"))

    def _move_selection(self, delta: int) -> None:
        if not self.items:
            self._ensure_visible()
            return
        index = self.selected_index
        for _ in range(len(self.items)):
            index = (index + delta) % len(self.items)
            if self._is_selectable_index(index):
                self.selected_index = index
                break
        self._ensure_visible()

    def _page_selection(self, delta_pages: int) -> None:
        if not self.items:
            self._ensure_visible()
            return
        max_visible = self.visible_row_count()
        step = max_visible * (1 if delta_pages > 0 else -1)
        self.selected_index = max(0, min(len(self.items) - 1, self.selected_index + step))
        if not self._is_selectable_index(self.selected_index):
            direction = 1 if step > 0 else -1
            for _ in range(len(self.items)):
                self.selected_index = max(
                    0, min(len(self.items) - 1, self.selected_index + direction)
                )
                if self._is_selectable_index(self.selected_index):
                    break
        self._ensure_visible()

    def _wrap_text(self, text, max_width):
        """Wrap text to fit within max_width in pixels."""
        text = str(text)
        if not text:
            return [""]
        lines = []
        for paragraph in text.splitlines() or [""]:
            words = paragraph.split()
            if not words:
                lines.append("")
                continue
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

    def _draw_wrapped_lines(self, text: str, x: int, y: int, max_width: int, color=None) -> int:
        color = color or self.WHITE
        for line in self._wrap_text(text, max_width):
            if line:
                self.screen.blit(self.normal_font.render(line, True, color), (x, y))
            y += self.line_height
        return y

    def list_vertical_padding(self) -> int:
        return 16

    def visible_row_count(self) -> int:
        return max(
            1, (self.list_rect.height - (self.list_vertical_padding() * 2)) // self.line_height
        )

    def visible_row_rects(self) -> list[tuple[int, pygame.Rect]]:
        """Return visible popup-list indexes and clickable row rectangles."""
        if not self.items:
            return []
        max_visible = self.visible_row_count()
        start = max(0, min(self.scroll_offset, max(0, len(self.items) - max_visible)))
        self.scroll_offset = start
        end = min(len(self.items), start + max_visible)
        y = self.list_rect.top + self.list_vertical_padding()
        return [
            (
                idx,
                pygame.Rect(
                    self.list_rect.left + 8,
                    y + ((idx - start) * self.line_height) - 2,
                    self.list_rect.width - 16,
                    self.line_height,
                ),
            )
            for idx in range(start, end)
        ]

    def _hit_visible_row(self, pos: tuple[int, int] | None) -> int | None:
        if pos is None:
            return None
        for index, rect in self.visible_row_rects():
            if rect.collidepoint(pos):
                return index
        return None

    def scrollbar_rects(self) -> tuple[pygame.Rect, pygame.Rect] | None:
        """Return the list scrollbar track and thumb when the list overflows."""
        max_visible = self.visible_row_count()
        if len(self.items) <= max_visible:
            return None
        track = pygame.Rect(
            self.list_rect.right - 14, self.list_rect.top + 4, 10, self.list_rect.height - 8
        )
        thumb_height = max(24, int(track.height * max_visible / len(self.items)))
        max_scroll = len(self.items) - max_visible
        thumb_top = track.top + int((track.height - thumb_height) * self.scroll_offset / max_scroll)
        return track, pygame.Rect(track.left, thumb_top, track.width, thumb_height)

    def _scroll_to_pointer(self, position: tuple[int, int]) -> bool:
        """Move the list based on a scrollbar click and report whether it was handled."""
        scrollbar = self.scrollbar_rects()
        if scrollbar is None:
            return False
        track, _thumb = scrollbar
        if not track.collidepoint(position):
            return False
        max_visible = self.visible_row_count()
        max_scroll = len(self.items) - max_visible
        travel = max(1, track.height - max(24, int(track.height * max_visible / len(self.items))))
        relative_y = max(0, min(travel, position[1] - track.top))
        self.scroll_offset = round(relative_y * max_scroll / travel)
        self.selected_index = max(
            self.scroll_offset,
            min(self.selected_index, self.scroll_offset + max_visible - 1),
        )
        self._ensure_visible()
        return True

    def _handle_held_scroll(self):
        try:
            pressed = pygame.key.get_pressed()
        except pygame.error:
            return
        self._quick_scroll_frame += 1
        if self._quick_scroll_frame < self.quick_scroll_delay:
            return
        self._quick_scroll_frame = 0
        try:
            if pressed[pygame.K_UP]:
                self._move_selection(-1)
            elif pressed[pygame.K_DOWN]:
                self._move_selection(1)
        except (IndexError, TypeError):
            return

    def _render_wrapped_attribute(self, label: str, val, x: int, y: int, max_width: int) -> int:
        value_text = str(val)
        if label == "Value":
            value_text = f"{value_text}G"
        label_text = f"{self.attribute_label(label)}:"
        label_width = min(100, max_width // 3)
        text_width = max_width - label_width - 8
        if label == "Description":
            value_text = " ".join(value_text.split())
        lines = []
        for raw_line in value_text.split("\n"):
            wrap_width = (
                max_width - 16 if label == "Description" or "\n" in value_text else text_width
            )
            lines.extend(self._wrap_text(raw_line, wrap_width))
        if label == "Description" or len(lines) > 1 or "\n" in value_text:
            self.screen.blit(self.normal_font.render(label_text, True, self.WHITE), (x, y))
            y += self.line_height
            for wrapped_line in lines:
                text = self.normal_font.render(wrapped_line, True, self.WHITE)
                self.screen.blit(text, (x + 16, y))
                y += self.line_height
            return y

        line = f"{label_text} {value_text}"
        if self.normal_font.size(line)[0] <= max_width:
            text = self.normal_font.render(line, True, self.WHITE)
            self.screen.blit(text, (x, y))
            return y + self.line_height

        self.screen.blit(self.normal_font.render(label_text, True, self.WHITE), (x, y))
        text = self.normal_font.render(lines[0] if lines else value_text, True, self.WHITE)
        self.screen.blit(text, (x + label_width, y))
        return y + self.line_height

    @staticmethod
    def attribute_label(label: str) -> str:
        return {
            "Subtyp": "Sub-type",
            "Subtyp:": "Sub-type",
        }.get(label, label)

    @staticmethod
    def _weapon_handedness(item) -> str:
        handed = getattr(item, "handed", None)
        try:
            if int(handed) >= 2:
                return "Two-handed"
            if int(handed) == 1:
                return "One-handed"
        except (TypeError, ValueError):
            pass
        return (
            "Two-handed"
            if str(getattr(item, "subtyp", "") or "") in {"Longsword", "Battle Axe", "Hammer"}
            else "One-handed"
        )

    @classmethod
    def _equipment_display_name(cls, item) -> str:
        name = str(getattr(item, "name", item) or item)
        if str(getattr(item, "typ", "") or "") == "Weapon":
            handedness = cls._weapon_handedness(item)
            if handedness == "Two-handed":
                return f"{name} (2H)"
            if handedness == "One-handed":
                return f"{name} (1H)"
        return name

    def build_items(self, player_char):
        """Override in subclass to populate self.items."""
        self.items = []

    def item_display_text(self, item):
        """Override for how to show each row's text."""
        return str(item)

    def _can_render_item_icon(self, value) -> bool:
        if value is None or isinstance(value, (str, int, float, bool)):
            return False
        typ = str(getattr(value, "typ", "") or "")
        return typ in IconManager.ITEM_TYPES

    def icon_subject_for_item(self, item):
        if isinstance(item, dict):
            if item.get("is_header"):
                return None
            value = item.get("value")
            return value if self._can_render_item_icon(value) else None
        if isinstance(item, tuple) and len(item) >= 2:
            return item[1] if self._can_render_item_icon(item[1]) else None
        return item if self._can_render_item_icon(item) else None

    def draw_large_item_render(self, item, rect: pygame.Rect) -> None:
        if rect.width <= 0 or rect.height <= 0:
            return
        relic = self.relic_sprite_for_item(item)
        if relic is not None:
            self._draw_fitted_surface(relic, rect)
            return
        render = self.item_render_manager.get_scaled_render(item, rect.size)
        self.screen.blit(render, rect)

    def relic_sprite_for_item(self, item) -> pygame.Surface | None:
        name = str(getattr(item, "name", item) or "")
        rel_path = RELIC_ART_FILES.get(name)
        if rel_path is None:
            return None
        cached = self._relic_sprite_cache.get(name)
        if cached is not None:
            return cached
        path = ITEM_ART_DIR / rel_path
        if not path.exists():
            return None
        try:
            surface = pygame.image.load(str(path))
        except (pygame.error, OSError):
            return None
        try:
            surface = surface.convert_alpha()
        except pygame.error:
            surface = surface.copy()
        self._relic_sprite_cache[name] = surface
        return surface

    def _draw_fitted_surface(self, surface: pygame.Surface, rect: pygame.Rect) -> None:
        source_width, source_height = surface.get_size()
        if source_width <= 0 or source_height <= 0:
            return
        scale = min(rect.width / source_width, rect.height / source_height)
        target_size = (max(1, int(source_width * scale)), max(1, int(source_height * scale)))
        fitted = pygame.transform.smoothscale(surface, target_size)
        target_rect = fitted.get_rect(center=rect.center)
        self.screen.blit(fitted, target_rect)

    def detail_attribute_rows(
        self,
        item,
        *,
        exclude: set[str] | None = None,
        hide_zero_value: bool = False,
        hide_zero_weight: bool = False,
    ) -> list[tuple[str, object]]:
        exclude = exclude or set()
        rows: list[tuple[str, object]] = []
        for key in ("description", "slot", "subtyp", "value", "weight"):
            if key in exclude:
                continue
            if not hasattr(item, key):
                continue
            value = getattr(item, key)
            if key == "subtyp" and value in (None, "", "None"):
                continue
            if key == "value" and hide_zero_value and self._is_zero(value):
                continue
            if key == "weight" and hide_zero_weight and self._is_zero(value):
                continue
            rows.append((key.capitalize(), value))
        return rows

    @staticmethod
    def _is_zero(value) -> bool:
        try:
            return float(value or 0) == 0
        except (TypeError, ValueError):
            return False

    def draw_item_detail_layout(
        self,
        item,
        *,
        category: str = "",
        y: int | None = None,
        art_height: int | None = None,
        exclude_attrs: set[str] | None = None,
        hide_zero_value: bool = False,
        hide_zero_weight: bool = False,
    ) -> int:
        x = self.details_rect.left + 16
        y = self.details_rect.top + 12 if y is None else y
        text_width = self.details_rect.width - 32
        art_height = art_height or min(180, max(112, self.details_rect.height // 4))
        art_width = min(160, max(96, self.details_rect.width // 3))
        render_rect = pygame.Rect(0, 0, art_width, art_height)
        render_rect.midtop = (self.details_rect.centerx, y)
        self.draw_large_item_render(item, render_rect)
        y = render_rect.bottom + 12

        name = getattr(item, "name", str(item))
        name_text = self.large_font.render(name, True, self.WHITE)
        name_x = self.details_rect.centerx - name_text.get_width() // 2
        self.screen.blit(name_text, (name_x, y))
        y += name_text.get_height() + 8

        for label, value in self.detail_attribute_rows(
            item,
            exclude=exclude_attrs,
            hide_zero_value=hide_zero_value,
            hide_zero_weight=hide_zero_weight,
        ):
            y = self._render_wrapped_attribute(label, value, x, y, text_width)
        return y

    def handle_key_down(self, player_char, event) -> bool:
        """Subclass hook for custom key handling. Return True if handled."""
        return False

    def help_footer(self) -> str:
        return "Arrows: Navigate  Enter: Select  Esc: Close  PgUp/PgDn: Scroll"

    def draw_background(self, background_surface):
        # Blit pre-rendered background and a semi-transparent overlay
        self.screen.blit(background_surface, (0, 0))
        overlay = pygame.Surface((self.width, self.height), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 180))
        self.screen.blit(overlay, (0, 0))

    def draw_popup(self, player_char):
        pygame.draw.rect(self.screen, self.BLACK, self.popup_rect)
        pygame.draw.rect(self.screen, self.BORDER_COLOR, self.popup_rect, 2)
        draw_popup_close_button(self.screen, self.popup_rect, self.small_font)

        # Title
        title_text = self.title_font.render(self.title, True, self.GOLD)
        self.screen.blit(
            title_text,
            (self.popup_rect.centerx - title_text.get_width() // 2, self.popup_rect.top + 16),
        )

        # Column borders
        pygame.draw.rect(self.screen, self.BLACK, self.list_rect)
        pygame.draw.rect(self.screen, self.BORDER_COLOR, self.list_rect, 2)
        pygame.draw.rect(self.screen, self.BLACK, self.details_rect)
        pygame.draw.rect(self.screen, self.BORDER_COLOR, self.details_rect, 2)

        # Help footer
        help_str = self.help_footer()
        help_text = self.small_font.render(help_str, True, self.WHITE)
        self.screen.blit(
            help_text,
            (self.popup_rect.left + 16, self.popup_rect.bottom - help_text.get_height() - 12),
        )

    def draw_list(self):
        # Visible rows
        max_visible = self.visible_row_count()
        start = self.scroll_offset
        end = min(len(self.items), start + max_visible)
        y = self.list_rect.top + self.list_vertical_padding()
        icon_size = min(18, max(14, self.line_height - 6))
        text_max_width = self.list_rect.width - 32 - icon_size - 8

        for idx in range(start, end):
            item = self.items[idx]
            is_header = isinstance(item, dict) and item.get("is_header")
            text_str = self._truncate_text(self.item_display_text(item), text_max_width)
            row_rect = dict(self.visible_row_rects())[idx]
            if is_header:
                text = self.normal_font.render(text_str, True, self.GOLD)
            elif idx == self.selected_index:
                pygame.draw.rect(self.screen, self.HIGHLIGHT_BG, row_rect)
                text = self.normal_font.render(text_str, True, self.GOLD)
            else:
                text = self.normal_font.render(text_str, True, self.WHITE)
            text_x = self.list_rect.left + 16
            icon_subject = self.icon_subject_for_item(item)
            if icon_subject is not None and not is_header:
                icon = self.icon_manager.get_icon(icon_subject)
                icon_rect = pygame.Rect(
                    text_x, y + max(0, (self.line_height - icon_size) // 2), icon_size, icon_size
                )
                fitted_icon = pygame.transform.smoothscale(icon, icon_rect.size)
                self.screen.blit(fitted_icon, icon_rect)
                text_x = icon_rect.right + 8
            self.screen.blit(text, (text_x, y))
            y += self.line_height

        scrollbar = self.scrollbar_rects()
        if scrollbar is not None:
            track, thumb = scrollbar
            pygame.draw.rect(self.screen, (48, 48, 56), track)
            pygame.draw.rect(self.screen, self.GRAY, thumb)

    def draw_details(self, player_char):
        item = self.items[self.selected_index] if self.items else None
        x = self.details_rect.left + 16
        y = self.details_rect.top + 12

        if item is None:
            self.screen.blit(self.normal_font.render("No items", True, self.GRAY), (x, y))
            return

        # Extract header/value metadata when present
        is_header = isinstance(item, dict) and item.get("is_header")
        value = item.get("value") if isinstance(item, dict) else item
        text_label = item.get("text") if isinstance(item, dict) else None

        if is_header:
            header_text = self.large_font.render(text_label or "", True, self.GOLD)
            self.screen.blit(header_text, (x, y))
            return

        # Name
        name = getattr(value, "name", text_label if text_label else str(value))
        name_text = self.large_font.render(name, True, self.WHITE)
        icon_subject = self.icon_subject_for_item(item)
        if icon_subject is not None:
            icon = self.icon_manager.get_icon(icon_subject)
            icon_size = min(42, max(32, self.large_font.get_height() + 8))
            icon_rect = pygame.Rect(x, y, icon_size, icon_size)
            self.screen.blit(pygame.transform.smoothscale(icon, icon_rect.size), icon_rect)
            self.screen.blit(
                name_text,
                (icon_rect.right + 10, y + max(0, (icon_size - name_text.get_height()) // 2)),
            )
            y += max(icon_size, name_text.get_height()) + 8
        else:
            self.screen.blit(name_text, (x, y))
            y += name_text.get_height() + 8

        # Generic attributes if present
        attrs = []
        for key in ("description", "slot", "subtyp", "value", "weight"):
            if hasattr(value, key):
                val = getattr(value, key)
                attrs.append((key.capitalize(), val))

        for label, val in attrs:
            y = self._render_wrapped_attribute(label, val, x, y, self.details_rect.width - 32)

        # Custom details hook
        self.draw_details_extra(player_char, value, x, y)

    def draw_details_extra(self, player_char, item, x, y):
        """Subclasses can render more information."""
        pass

    def on_select(self, player_char, item):
        """Handle selection. Subclasses should override. Return a result or None."""
        return ("selected", item)

    def _capture_menu_surface(self, player_char):
        """Render the menu without popups and return a surface snapshot."""
        self.parent_screen.draw_all(player_char, do_flip=False)
        background_surface = self.screen.copy()
        self.draw_background(background_surface)
        self.draw_popup(player_char)
        self.draw_list()
        self.draw_details(player_char)
        pygame.display.flip()
        return self.screen.copy()

    def show(self, player_char, flush_events: bool = False, require_key_release: bool = False):
        # Prepare items
        self.build_items(player_char)
        if not self.items:
            self.items = []
            self.selected_index = 0
            self.scroll_offset = 0
        # Ensure initial selection is on a selectable item (not a header)
        while (
            self.items
            and isinstance(self.items[self.selected_index], dict)
            and self.items[self.selected_index].get("is_header")
        ):
            if self.selected_index < len(self.items) - 1:
                self.selected_index += 1
            else:
                break

        running = True
        result = None
        clock = self.presenter.clock
        input_armed = prepare_guarded_input(
            flush_events=flush_events,
            require_key_release=require_key_release,
        )

        # Render and capture background once to prevent flicker
        self.parent_screen.draw_all(player_char, do_flip=False)
        background_surface = self.screen.copy()

        prev_provider = getattr(self.presenter, "_background_provider", None)
        menu_surface_ref = [None]
        if hasattr(self.presenter, "set_background_provider"):
            self.presenter.set_background_provider(
                lambda: menu_surface_ref[0] or self.screen.copy()
            )

        try:

            def activate_selected_item():
                nonlocal running, result, background_surface
                if not self.items or not self._is_selectable_index(self.selected_index):
                    return
                current_item = self.items[self.selected_index]
                result = self.on_select(player_char, current_item)
                if result is not None:
                    running = False
                else:
                    self.parent_screen.draw_all(player_char, do_flip=False)
                    background_surface = self.screen.copy()
                    menu_surface_ref[0] = None

            while running:
                self.draw_background(background_surface)
                self.draw_popup(player_char)
                self.draw_list()
                self.draw_details(player_char)
                pygame.display.flip()
                menu_surface_ref[0] = self.screen.copy()
                input_armed = release_guard_allows_input(require_key_release, input_armed)

                for event in pygame.event.get():
                    if event.type == pygame.QUIT:
                        pygame.quit()
                        import sys

                        sys.exit()
                    input_armed = update_input_armed_from_event(
                        event, require_key_release, input_armed
                    )
                    if popup_close_clicked(event, self.popup_rect):
                        if not input_armed:
                            continue
                        running = False
                        result = None
                        continue
                    if (
                        event.type == pygame.MOUSEBUTTONDOWN
                        and getattr(event, "button", None) in (4, 5)
                        and self.items
                    ):
                        self._move_selection(-1 if event.button == 4 else 1)
                        self._quick_scroll_frame = 0
                        continue
                    if is_left_click(event) and self._scroll_to_pointer(
                        mouse_position(event) or (-1, -1)
                    ):
                        continue
                    hovered = self._hit_visible_row(mouse_position(event))
                    if (
                        hovered is not None
                        and event.type == pygame.MOUSEMOTION
                        and self._is_selectable_index(hovered)
                    ):
                        self.selected_index = hovered
                        self._ensure_visible()
                    elif hovered is not None and is_left_click(event):
                        if not input_armed:
                            continue
                        if self._is_selectable_index(hovered):
                            self.selected_index = hovered
                            self._ensure_visible()
                            activate_selected_item()
                        continue
                    elif event.type == pygame.MOUSEWHEEL and self.items:
                        wheel_y = getattr(event, "y", 0)
                        if wheel_y:
                            direction = -1 if wheel_y > 0 else 1
                            for _ in range(abs(wheel_y)):
                                self._move_selection(direction)
                            self._quick_scroll_frame = 0
                    if event.type == pygame.KEYUP:
                        continue
                    if event.type == pygame.KEYDOWN:
                        if not input_armed:
                            continue
                        if self.handle_key_down(player_char, event):
                            self.parent_screen.draw_all(player_char, do_flip=False)
                            background_surface = self.screen.copy()
                            menu_surface_ref[0] = None
                            continue
                        if event.key == pygame.K_ESCAPE:
                            running = False
                            result = None
                        elif event.key == pygame.K_RETURN or event.key == pygame.K_SPACE:
                            activate_selected_item()
                        elif event.key == pygame.K_UP:
                            self._move_selection(-1)
                            self._quick_scroll_frame = 0
                        elif event.key == pygame.K_DOWN:
                            self._move_selection(1)
                            self._quick_scroll_frame = 0
                        elif event.key == pygame.K_PAGEUP:
                            self._page_selection(-1)
                            self._quick_scroll_frame = 0
                        elif event.key == pygame.K_PAGEDOWN:
                            self._page_selection(1)
                            self._quick_scroll_frame = 0
                self._handle_held_scroll()
                clock.tick(30)
        finally:
            if hasattr(self.presenter, "set_background_provider"):
                self.presenter.set_background_provider(prev_provider)

        return result
