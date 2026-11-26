"""Selections behavior for the popup menus package."""

import re

import pygame

from src.core import items

from .base import BasePopupMenu


class SelectionPopup(BasePopupMenu):
    """Generic selection popup: header + options, returns selected item."""

    def __init__(self, presenter, parent_screen, title="Select", header_message=None, options=None):
        super().__init__(presenter, parent_screen, title=title)
        self.header_message = header_message or ""
        self._options = options or []

    def build_items(self, player_char):
        self.items = list(self._options)

    def draw_details_extra(self, player_char, item, x, y):
        # Render header message
        if self.header_message:
            self._draw_wrapped_lines(str(self.header_message), x, y, self.details_rect.width - 32)

    def on_select(self, player_char, item):
        return ("selection", item)


class EquipmentSelectionPopup(BasePopupMenu):
    """Equipment selection popup with stat diff display."""

    def __init__(
        self,
        presenter,
        parent_screen,
        title="Select",
        header_message=None,
        options=None,
        slot=None,
        current_item=None,
        player_char=None,
    ):
        super().__init__(presenter, parent_screen, title=title)
        self.header_message = header_message or ""
        self._options = options or []
        self.slot = slot
        self.current_item = current_item
        self.player_char_ref = player_char  # Store reference for equip_diff calls

    def build_items(self, player_char):
        self.items = list(self._options)

    def _find_option_item(self, player_char, item_str: str):
        for _category, items_list in player_char.inventory.items():
            for inv_item in items_list:
                if getattr(inv_item, "name", str(inv_item)) == item_str:
                    return inv_item
        return None

    @staticmethod
    def _numeric_tokens(text: str) -> list[float]:
        return [float(token) for token in re.findall(r"[+-]?\d+(?:\.\d+)?", text)]

    @classmethod
    def _diff_value_direction(cls, value: str) -> int:
        if "->" not in value:
            return 0
        before_text, after_text = value.split("->", 1)
        before_values = cls._numeric_tokens(before_text)
        after_values = cls._numeric_tokens(after_text)
        if not before_values or not after_values:
            return 0
        before = sum(before_values)
        after = sum(after_values)
        if after > before:
            return 1
        if after < before:
            return -1
        return 0

    def _diff_value_color(self, value: str):
        direction = self._diff_value_direction(value)
        if direction > 0:
            return self.GREEN
        if direction < 0:
            return self.RED
        return self.LIGHT_GRAY

    def _render_aligned_detail_row(self, label: str, value: str, x: int, y: int, color=None) -> int:
        color = color or self.LIGHT_GRAY
        label_text = self.normal_font.render(label, True, color)
        value_text = self.normal_font.render(value, True, color)
        self.screen.blit(label_text, (x, y))
        value_x = max(x + 145, self.details_rect.right - 16 - value_text.get_width())
        self.screen.blit(value_text, (value_x, y))
        return y + self.line_height

    def _render_diff_lines(self, diff_str: str, x: int, y: int) -> int:
        for line in diff_str.split("\n"):
            if not line.strip():
                continue
            label = line[:16].strip()
            value = line[18:].strip() if len(line) > 18 else ""
            if not value:
                parts = line.split(None, 1)
                label = parts[0] if parts else line.strip()
                value = parts[1] if len(parts) > 1 else ""
            y = self._render_aligned_detail_row(label, value, x, y, self._diff_value_color(value))
        return y

    def draw_details(self, player_char):
        """Override to show item details with equipment diffs."""
        item = self.items[self.selected_index] if self.items else None
        x = self.details_rect.left + 16
        y = self.details_rect.top + 12

        if item is None:
            self.screen.blit(self.normal_font.render("No items", True, self.GRAY), (x, y))
            return

        # Extract the actual item from the option string
        item_str = str(item)
        actual_item = (
            None
            if item_str in {"Cancel", "Unequip"}
            else self._find_option_item(player_char, item_str)
        )
        display_name = (
            self._equipment_display_name(actual_item) if actual_item is not None else item_str
        )

        if actual_item is not None:
            art_height = min(140, max(92, self.details_rect.height // 3))
            art_width = min(130, max(88, self.details_rect.width // 3))
            art_rect = pygame.Rect(0, 0, art_width, art_height)
            art_rect.midtop = (self.details_rect.centerx, y)
            self.draw_large_item_render(actual_item, art_rect)
            y = art_rect.bottom + 8

        # Display item name
        name_text = self.large_font.render(display_name, True, self.WHITE)
        self.screen.blit(name_text, (x, y))
        y += name_text.get_height() + 8

        if actual_item is not None:
            subtype = str(getattr(actual_item, "subtyp", "") or "")
            if subtype and subtype != "None":
                y = self._render_aligned_detail_row("Type", subtype, x, y)

        # Handle different option types
        if item_str == "Cancel":
            return  # Don't show diff for cancel

        elif item_str == "Unequip":
            # Show diffs for unequipping (switching to placeholder)
            if self.slot and self.player_char_ref and self.current_item:
                no_item_classes = {
                    "Weapon": items.NoWeapon,
                    "Armor": items.NoArmor,
                    "Helmet": items.NoHelmet,
                    "OffHand": items.NoOffHand,
                    "Ring": items.NoRing,
                    "Pendant": items.NoPendant,
                }

                if self.slot in no_item_classes:
                    placeholder = no_item_classes[self.slot]()
                    diff_str = self.player_char_ref.equip_diff(placeholder, self.slot)
                    if diff_str:
                        y = self._render_diff_lines(diff_str, x, y)

        else:
            # If we found the item, show the diff
            if actual_item and self.slot and self.player_char_ref:
                try:
                    diff_str = self.player_char_ref.equip_diff(actual_item, self.slot)
                    if diff_str:
                        y = self._render_diff_lines(diff_str, x, y)
                except Exception:
                    pass  # Silently fail if equip_diff fails

    def draw_details_extra(self, player_char, item, x, y):
        # Render header message
        if self.header_message:
            self._draw_wrapped_lines(str(self.header_message), x, y, self.details_rect.width - 32)

    def on_select(self, player_char, item):
        return ("selection", item)
