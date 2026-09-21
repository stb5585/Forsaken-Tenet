"""
Shop screen for the Pygame frontend.
Layout structure:
- Top: Shop header message
- Below: Two boxes side-by-side (menu options left, item description right)
- Bottom: Large item list box (left), stat comparison box (right top), gold box (right bottom)
"""

from textwrap import wrap

import pygame

from src.core import items as items_module
from src.ui_pygame.assets.item_render_manager import get_item_render_manager
from src.ui_pygame.screen_runtime import get_events

from .input_guards import (
    prepare_guarded_input,
    release_guard_allows_input,
    update_input_armed_from_event,
)
from .mouse_helpers import hit_index, is_left_click, mouse_position
from .town_base import TownScreenBase


class ShopScreen(TownScreenBase):
    """
    Pygame shop interface with inventory, item detail, and transaction panels.
    """

    def __init__(
        self, presenter, player_char, shop_message, background_image="town.png", options_list=None
    ):
        self.background_image = (
            background_image  # Set before super().__init__ so _load_background can use it
        )
        super().__init__(presenter)
        self.player_char = player_char
        self.shop_message = shop_message

        # State
        self.current_option = 0
        self.current_item = 0
        self.options_list = (
            options_list if options_list is not None else ["Buy", "Sell", "Quests", "Leave"]
        )
        self.item_list = []  # List of tuples: (display_string, item_object, cost, owned_count)
        self.buy_or_sell = None
        self.scroll_offset = 0
        self.tab_labels: list[str] = []
        self.active_tab_index = 0
        self._itemdict_source = {}
        self.item_render_manager = get_item_render_manager()
        self.location_portrait_name: str | None = None
        self.price_multiplier = 1.0
        self.ignore_rarity_filter = False

        # Caching for equip_diff to prevent recalculation on every blit
        self.cached_item_index = -1
        self.cached_diff_str = ""

        # Calculate window positions for the multi-panel shop layout.
        self.calculate_window_rects()

    def set_options(self, options_list, reset_cursor=True):
        """Replace options and optionally reset the selection index."""
        self.options_list = options_list
        if reset_cursor:
            self.current_option = 0

    def set_location_portrait(self, npc_name: str | None) -> None:
        """Set a persistent shopkeeper portrait for the main shop menu."""
        self.location_portrait_name = npc_name

    def display_quest_text(
        self,
        text: str,
        *,
        title: str = "",
        npc_name: str | None = None,
    ) -> None:
        """Show blocking quest dialogue using the shared town presentation."""
        speaker = npc_name or title or self.location_portrait_name
        dialogue = str(text)
        first_line = dialogue.split("\n", 1)[0].strip()
        has_header = (
            first_line.startswith("======") and first_line.endswith("======")
        ) or first_line.startswith(("Quest: ", "Quest Complete: "))
        if title and not has_header:
            dialogue = f"====== {title} ======\n{dialogue}"
        super().display_quest_text(dialogue, npc_name=speaker)

    def option_rects(self) -> list[pygame.Rect]:
        """Return clickable rectangles for the main shop option rows."""
        num_options = len(self.options_list)
        if num_options <= 0:
            return []
        option_height = self.options_rect.height // (num_options + 1)
        rects: list[pygame.Rect] = []
        for idx in range(num_options):
            text_y = self.options_rect.top + (idx + 1) * option_height
            rects.append(
                pygame.Rect(
                    self.options_rect.left + 10,
                    text_y - 5,
                    self.options_rect.width - 20,
                    self.normal_font.get_height() + 10,
                )
            )
        return rects

    def calculate_window_rects(self):
        """Calculate the rectangles for each shop UI section."""
        # Top window: 1/12 of height
        top_height = self.height // 12
        self.top_rect = pygame.Rect(0, 0, self.width, top_height)

        # Options window: left 1/3, below top, height 1/4
        options_height = self.height // 4
        options_width = self.width // 3
        options_y = top_height
        self.options_rect = pygame.Rect(0, options_y, options_width, options_height)

        # Item description window: right 2/3, below top, height 1/4
        desc_width = 2 * self.width // 3
        self.desc_rect = pygame.Rect(options_width, options_y, desc_width, options_height)

        # Shop list window: left 2/3, below options, height 2/3
        list_y = options_y + options_height
        list_height = 2 * self.height // 3
        list_width = 2 * self.width // 3
        self.list_rect = pygame.Rect(0, list_y, list_width, list_height)

        # Mod window: right 1/3, below options, height 7/12
        mod_width = self.width // 3
        mod_height = 7 * self.height // 12
        self.mod_rect = pygame.Rect(list_width, list_y, mod_width, mod_height)

        # Gold window: right 1/3, at bottom, height 1/12
        gold_y = list_y + mod_height
        gold_height = self.height // 12
        self.gold_rect = pygame.Rect(list_width, gold_y, mod_width, gold_height)

    def draw_top(self):
        """Draw the top header with shop message."""
        self.draw_semi_transparent_panel(self.top_rect)
        pygame.draw.rect(self.screen, self.colors.BORDER_COLOR, self.top_rect, 2)

        # Center the shop message
        text = self.large_font.render(self.shop_message, True, self.colors.GOLD)
        text_rect = text.get_rect(center=(self.width // 2, self.top_rect.centery))
        self.screen.blit(text, text_rect)

    def draw_options(self):
        """Draw the menu options (Buy, Sell, Quests, Leave)."""
        self.draw_semi_transparent_panel(self.options_rect)
        pygame.draw.rect(self.screen, self.colors.BORDER_COLOR, self.options_rect, 2)

        selected_item = self.selected_item_for_artwork()
        if selected_item is not None:
            self.draw_selected_item_art(self.options_rect, selected_item)
            return

        option_rects = self.option_rects()

        for idx, option in enumerate(self.options_list):
            # Highlight selected option
            color = self.colors.GOLD if idx == self.current_option else self.colors.WHITE

            # Draw option text centered
            text = self.normal_font.render(option, True, color)
            text_x = self.options_rect.centerx - text.get_width() // 2
            text_y = option_rects[idx].top + 5 if idx < len(option_rects) else self.options_rect.top

            # Highlight background for selected
            if idx == self.current_option:
                highlight_rect = (
                    option_rects[idx]
                    if idx < len(option_rects)
                    else pygame.Rect(text_x, text_y, text.get_width(), text.get_height())
                )
                pygame.draw.rect(self.screen, self.colors.HIGHLIGHT_BG, highlight_rect)
                pygame.draw.rect(self.screen, self.colors.GOLD, highlight_rect, 2)

            self.screen.blit(text, (text_x, text_y))

    def selected_item_for_artwork(self):
        """Return the highlighted shop item when the shop is in item-list mode."""
        if self.buy_or_sell not in {"Buy", "Sell"}:
            return None
        if not self.item_list or not (0 <= self.current_item < len(self.item_list)):
            return None
        display_str, item, _, _ = self.item_list[self.current_item]
        if display_str in {"Go Back", "Next Page"}:
            return None
        return item

    def is_item_browsing(self) -> bool:
        """Return whether the shop should draw item browser panels."""
        return self.buy_or_sell in {"Buy", "Sell"}

    def draw_selected_item_art(self, rect: pygame.Rect, item) -> None:
        panel_rect = rect.inflate(-4, -4)
        panel = pygame.Surface(panel_rect.size, pygame.SRCALPHA)
        panel.fill((0, 0, 0, 170))
        self.screen.blit(panel, panel_rect)
        padding = 14
        render_rect = pygame.Rect(
            rect.left + padding,
            rect.top + padding,
            rect.width - (padding * 2),
            rect.height - (padding * 2),
        )
        self.draw_item_art_backdrop(render_rect)
        render = self.item_render_manager.get_scaled_render(item, render_rect.size)
        self.screen.blit(render, render_rect)

    def draw_item_art_backdrop(self, rect: pygame.Rect) -> None:
        backdrop = pygame.Surface(rect.size, pygame.SRCALPHA)
        backdrop.fill((0, 0, 0, 135))
        self.screen.blit(backdrop, rect)
        pygame.draw.rect(self.screen, (124, 99, 62), rect, 1)

    def draw_item_desc(self):
        """Draw the description of the currently highlighted item."""
        self.draw_semi_transparent_panel(self.desc_rect)
        pygame.draw.rect(self.screen, self.colors.BORDER_COLOR, self.desc_rect, 2)

        if self.item_list and 0 <= self.current_item < len(self.item_list):
            display_str, item, _, _ = self.item_list[self.current_item]

            # Don't show description for "Go Back" or "Next Page"
            if display_str in ["Go Back", "Next Page"]:
                return

            text_left = self.desc_rect.left + 16
            text_width = self.desc_rect.width - 32

            if item and hasattr(item, "description") and item.description:
                # Word wrap the description to fit
                wrap_width = max(24, text_width // 8)
                lines = wrap(item.description, wrap_width, break_on_hyphens=False)
                for metadata_line in items_module.item_metadata_lines(item):
                    lines.extend(wrap(metadata_line, wrap_width, break_on_hyphens=False))

                # Draw description lines centered vertically
                line_height = self.normal_font.get_height() + 2
                total_height = len(lines) * line_height
                start_y = self.desc_rect.centery - total_height // 2

                for i, line in enumerate(lines):
                    text = self.normal_font.render(line, True, self.colors.WHITE)
                    text_x = text_left + max(0, (text_width - text.get_width()) // 2)
                    text_y = start_y + i * line_height
                    self.screen.blit(text, (text_x, text_y))

    def draw_shop_list(self):
        """Draw the list of items for sale or selling."""
        if not self.is_item_browsing():
            if self.location_portrait_name:
                portrait_rect = pygame.Rect(
                    self.list_rect.left,
                    self.list_rect.top,
                    self.width // 3,
                    self.list_rect.height,
                )
                self.draw_npc_portrait(npc_name=self.location_portrait_name, rect=portrait_rect)
            return

        self.draw_semi_transparent_panel(self.list_rect)
        pygame.draw.rect(self.screen, self.colors.BORDER_COLOR, self.list_rect, 2)

        if not self.item_list:
            self.draw_item_tabs()
            # Display message when no items available
            no_items_text = self.normal_font.render("No items available", True, self.colors.GRAY)
            text_rect = no_items_text.get_rect(
                centerx=self.list_rect.centerx, centery=self.list_rect.centery
            )
            self.screen.blit(no_items_text, text_rect)
            return

        # Define fixed column positions (in pixels from left edge)
        base_x = self.list_rect.left + 10
        type_col_x = base_x
        item_col_x = base_x + 120  # After "Type" column
        cost_col_x = self.list_rect.right - 180  # Fixed position for Cost
        owned_col_x = self.list_rect.right - 60  # Fixed position for Owned

        self.draw_item_tabs()

        # Draw header row at fixed positions
        header_y = self.list_rect.top + (38 if self.tab_labels else 10)

        type_header = self.small_font.render("Type", True, self.colors.GOLD)
        self.screen.blit(type_header, (type_col_x, header_y))

        item_header = self.small_font.render("Item", True, self.colors.GOLD)
        self.screen.blit(item_header, (item_col_x, header_y))

        if self.buy_or_sell == "Buy":
            cost_header = self.small_font.render("Cost", True, self.colors.GOLD)
            self.screen.blit(cost_header, (cost_col_x, header_y))

        owned_header = self.small_font.render("Owned", True, self.colors.GOLD)
        self.screen.blit(owned_header, (owned_col_x, header_y))

        # Draw items (scrollable)
        max_visible = self._visible_item_count()
        line_height = (self.list_rect.height - 40) // max_visible

        visible_start = self.scroll_offset
        visible_end = min(self.scroll_offset + max_visible, len(self.item_list))
        if len(self.item_list) > max_visible:
            range_text = self.small_font.render(
                f"{visible_start + 1}-{visible_end} / {len(self.item_list)}",
                True,
                self.colors.GOLD,
            )
            self.screen.blit(
                range_text,
                (self.list_rect.right - range_text.get_width() - 10, self.list_rect.bottom - 22),
            )

        for i in range(visible_start, visible_end):
            display_str, item, cost, owned = self.item_list[i]

            y = header_y + 25 + (i - visible_start) * line_height

            # Highlight selected item
            if i == self.current_item:
                highlight_rect = pygame.Rect(
                    self.list_rect.left + 5, y - 2, self.list_rect.width - 10, line_height - 2
                )
                pygame.draw.rect(self.screen, self.colors.HIGHLIGHT_BG, highlight_rect)
                pygame.draw.rect(self.screen, self.colors.GOLD, highlight_rect, 1)

            # Draw each column at fixed positions
            color = self.colors.GOLD if i == self.current_item else self.colors.WHITE

            # Skip special items (like Next Page for pagination)
            if display_str in ["Next Page", "Go Back", "Back"]:
                text = self.small_font.render(display_str, True, color)
                self.screen.blit(text, (item_col_x, y))
                continue

            # Parse the item data
            if item:
                # Type column
                type_text = self.normal_font.render(item.typ, True, color)
                self.screen.blit(type_text, (type_col_x, y))

                # Item name column
                item_text = self.normal_font.render(item.name, True, color)
                self.screen.blit(item_text, (item_col_x, y))

                # Cost column (buy mode only)
                if self.buy_or_sell == "Buy":
                    cost_text = self.normal_font.render(str(cost), True, color)
                    self.screen.blit(cost_text, (cost_col_x, y))

                # Owned column
                owned_text = self.normal_font.render(f"x {owned}", True, color)
                self.screen.blit(owned_text, (owned_col_x, y))

    def draw_item_tabs(self) -> None:
        """Draw subtype tabs for grouped buy lists."""
        if not self.tab_labels:
            return

        for idx, label in enumerate(self.tab_labels):
            tab_rect = self.item_tab_rects()[idx]
            active = idx == self.active_tab_index
            fill_color = self.colors.HIGHLIGHT_BG if active else (0, 0, 0, 80)
            pygame.draw.rect(self.screen, fill_color, tab_rect)
            pygame.draw.rect(
                self.screen, self.colors.GOLD if active else self.colors.BORDER_COLOR, tab_rect, 1
            )

            text_color = self.colors.GOLD if active else self.colors.WHITE
            display_label = self._fit_tab_label(label, max(8, tab_rect.width - 8))
            text = self.small_font.render(display_label, True, text_color)
            text_x = tab_rect.centerx - text.get_width() // 2
            text_y = tab_rect.centery - text.get_height() // 2
            self.screen.blit(text, (text_x, text_y))

    def _fit_tab_label(self, label: str, max_width: int) -> str:
        """Return a tab label that fits the available pixel width."""
        if self.small_font.size(label)[0] <= max_width:
            return label
        clipped = label
        while len(clipped) > 1 and self.small_font.size(f"{clipped}.")[0] > max_width:
            clipped = clipped[:-1]
        return f"{clipped}." if clipped else "."

    def draw_mod(self):
        """Draw equipment modification comparison."""
        self.draw_semi_transparent_panel(self.mod_rect)
        pygame.draw.rect(self.screen, self.colors.BORDER_COLOR, self.mod_rect, 2)

        if not self.item_list or self.current_item >= len(self.item_list):
            return

        display_str, item, _, _ = self.item_list[self.current_item]

        # Skip for non-items
        if display_str in ["Go Back", "Next Page"] or not item:
            return

        # Only show for equipment that can be equipped
        if not hasattr(item, "typ") or item.typ not in [
            "Weapon",
            "OffHand",
            "Armor",
            "Helmet",
            "Accessory",
        ]:
            return

        # Draw title
        title = self.normal_font.render("Equipment Modifications", True, self.colors.GOLD)
        title_x = self.mod_rect.centerx - title.get_width() // 2
        self.screen.blit(title, (title_x, self.mod_rect.top + 10))

        # Get stat comparison (cached to prevent recalculation on every blit)
        try:
            equip_slot = item.typ
            if item.typ == "Accessory":
                equip_slot = item.subtyp

            # Show not equippable message
            can_equip = getattr(self.player_char, "can_equip_item", None)
            allowed = (
                can_equip(item, equip_slot)
                if callable(can_equip)
                else self.player_char.cls.equip_check(item, equip_slot)
            )
            if not allowed:
                cant_text = self.normal_font.render("Can't Equip", True, self.colors.RED)
                cant_rect = cant_text.get_rect(
                    center=(self.mod_rect.centerx, self.mod_rect.centery)
                )
                self.screen.blit(cant_text, cant_rect)
                return

            compatible_slots = []
            try:
                from src.core import items as items_module

                compatible_slots = items_module.equipment_slots_for_item(item)
            except (AttributeError, TypeError):
                compatible_slots = [equip_slot]
            if any(
                getattr(getattr(self.player_char, "equipment", {}).get(slot), "name", None)
                == item.name
                for slot in compatible_slots
            ):
                equipped_text = self.normal_font.render("Already Equipped", True, self.colors.GOLD)
                equipped_rect = equipped_text.get_rect(
                    center=(self.mod_rect.centerx, self.mod_rect.top + 34)
                )
                self.screen.blit(equipped_text, equipped_rect)

            # Only recalculate if the item selection changed
            if self.current_item != self.cached_item_index:
                self.cached_diff_str = self.player_char.equip_diff(item, equip_slot, buy=True)
                self.cached_item_index = self.current_item

            stat_diff_str = self.cached_diff_str

            if stat_diff_str:
                lines = stat_diff_str.splitlines()
                line_height = self.normal_font.get_height() + 4

                y = self.mod_rect.top + 40
                for line in lines:
                    if line.strip():
                        # Parse stat name and value
                        parts = [x.strip() for x in line.split("  ") if x.strip()]
                        if len(parts) >= 2:
                            stat_name = parts[0]
                            stat_value = parts[1]

                            # Color code based on positive/negative
                            if stat_value.startswith("+"):
                                value_color = self.colors.GREEN
                            elif stat_value.startswith("-"):
                                value_color = self.colors.RED
                            else:
                                value_color = self.colors.WHITE

                            # Draw stat name (left aligned)
                            name_text = self.normal_font.render(stat_name, True, self.colors.WHITE)
                            self.screen.blit(name_text, (self.mod_rect.left + 10, y))

                            # Draw stat value (right aligned)
                            value_text = self.normal_font.render(stat_value, True, value_color)
                            value_x = self.mod_rect.right - value_text.get_width() - 10
                            self.screen.blit(value_text, (value_x, y))

                            y += line_height
        except (KeyError, AttributeError):
            pass

    def draw_gold(self):
        """Draw player's current gold."""
        self.draw_semi_transparent_panel(self.gold_rect)
        pygame.draw.rect(self.screen, self.colors.BORDER_COLOR, self.gold_rect, 2)

        gold_str = f"{self.player_char.gold}G"
        text = self.normal_font.render(gold_str, True, self.colors.GOLD)
        text_x = self.gold_rect.right - text.get_width() - 10
        text_y = self.gold_rect.centery - text.get_height() // 2
        self.screen.blit(text, (text_x, text_y))

    def draw_all(self, player_char=None, do_flip=True):
        """Draw all shop UI elements. Set do_flip=False when drawing as a background for overlays."""
        if isinstance(player_char, bool):
            do_flip = player_char
            player_char = None
        if player_char is not None:
            self.player_char = player_char
        self.draw_background()
        self.draw_top()
        self.draw_options()
        self.draw_shop_list()
        if self.is_item_browsing():
            self.draw_item_desc()
            self.draw_mod()
            self.draw_gold()
        if do_flip:
            pygame.display.flip()

    @staticmethod
    def _arm_guarded_input(event, input_armed):
        return update_input_armed_from_event(event, True, input_armed)

    @staticmethod
    def _prepare_guarded_input(flush_events=True, require_key_release=True):
        return prepare_guarded_input(
            flush_events=flush_events,
            require_key_release=require_key_release,
        )

    @staticmethod
    def _visible_item_count() -> int:
        """Return the number of item rows visible in the shop list."""
        return 19

    def item_tab_rects(self) -> list[pygame.Rect]:
        """Return clickable rectangles for buy-list subtype tabs."""
        if not self.tab_labels:
            return []
        tab_y = self.list_rect.top + 6
        tab_height = 26
        available_width = self.list_rect.width - 20
        tab_width = max(1, available_width // len(self.tab_labels))
        rects: list[pygame.Rect] = []
        for idx in range(len(self.tab_labels)):
            left = self.list_rect.left + 10 + (idx * tab_width)
            width = max(1, min(tab_width - 4, self.list_rect.right - 10 - left))
            rects.append(pygame.Rect(left, tab_y, width, tab_height))
        return rects

    def item_row_rects(self) -> list[tuple[int, pygame.Rect]]:
        """Return visible item-list indexes and clickable row rectangles."""
        if not self.item_list:
            return []
        max_visible = self._visible_item_count()
        header_y = self.list_rect.top + (38 if self.tab_labels else 10)
        line_height = (self.list_rect.height - 40) // max_visible
        visible_start = self.scroll_offset
        visible_end = min(self.scroll_offset + max_visible, len(self.item_list))
        return [
            (
                index,
                pygame.Rect(
                    self.list_rect.left + 5,
                    header_y + 25 + (index - visible_start) * line_height - 2,
                    self.list_rect.width - 10,
                    line_height - 2,
                ),
            )
            for index in range(visible_start, visible_end)
        ]

    def _hit_item_row(self, pos: tuple[int, int] | None) -> int | None:
        """Return the item-list index under a mouse position."""
        if pos is None:
            return None
        for index, rect in self.item_row_rects():
            if rect.collidepoint(pos):
                return index
        return None

    def _max_scroll_offset(self) -> int:
        """Return the highest scroll offset that can still fill the list window."""
        return max(0, len(self.item_list) - self._visible_item_count())

    def _keep_current_item_visible(self) -> None:
        """Adjust scroll offset so the current item remains visible."""
        max_visible = self._visible_item_count()
        if self.current_item < self.scroll_offset:
            self.scroll_offset = self.current_item
        elif self.current_item >= self.scroll_offset + max_visible:
            self.scroll_offset = self.current_item - max_visible + 1
        self.scroll_offset = max(0, min(self.scroll_offset, self._max_scroll_offset()))

    def update_item_list(self, itemdict, buy_or_sell):
        """
        Update the list of items to display.
        itemdict: Dictionary of items from items_module.items_dict
        buy_or_sell: "Buy" or "Sell"
        """
        # Save cursor position if we're staying in the same mode
        preserve_cursor = self.buy_or_sell == buy_or_sell
        previous_tab = self.tab_labels[self.active_tab_index] if self.tab_labels else None

        self.buy_or_sell = buy_or_sell
        self._itemdict_source = itemdict
        self.item_list = []
        self.tab_labels = []

        if buy_or_sell == "Buy":
            self._build_buy_tabs(itemdict, previous_tab)
        else:
            self._build_sell_list(itemdict)

        self._finalize_item_list(preserve_cursor)

    def _build_buy_tabs(self, itemdict, previous_tab: str | None) -> None:
        """Build the active buy list and tab labels from a grouped item dictionary."""
        if len(itemdict) <= 1:
            self.active_tab_index = 0
            self._build_buy_list(itemdict)
            return

        rows_by_tab = {
            label: self._build_buy_rows(item_classes) for label, item_classes in itemdict.items()
        }
        self.tab_labels = [label for label, rows in rows_by_tab.items() if rows]

        if not self.tab_labels:
            self.active_tab_index = 0
            return

        if previous_tab in self.tab_labels:
            self.active_tab_index = self.tab_labels.index(previous_tab)
        else:
            self.active_tab_index = min(self.active_tab_index, len(self.tab_labels) - 1)

        self.item_list.extend(rows_by_tab[self.tab_labels[self.active_tab_index]])

    def _finalize_item_list(self, preserve_cursor: bool) -> None:
        """Clamp item-list cursor state and append the shared back row."""
        if not preserve_cursor or not self.item_list:
            self.current_item = 0
            self.scroll_offset = 0
        else:
            # Clamp to real item rows before appending the navigation row.
            self.current_item = min(self.current_item, max(0, len(self.item_list) - 1))

        if self.item_list and self.item_list[-1][0] not in {"Go Back", "Back"}:
            self.item_list.append(("Go Back", None, 0, 0))

        if self.item_list:
            self.current_item = min(self.current_item, max(0, len(self.item_list) - 1))
            self.scroll_offset = min(self.scroll_offset, self._max_scroll_offset())
            self._keep_current_item_visible()
        self.cached_item_index = -1

    def _build_buy_list(self, itemdict):
        """Build item list for buying."""
        for _, item_classes in itemdict.items():
            self.item_list.extend(self._build_buy_rows(item_classes))

    def _build_buy_rows(self, item_classes):
        """Return visible buy rows for one item class list."""
        rows = []
        for item_class in item_classes:
            item = item_class()

            # Check class restrictions
            if hasattr(item, "restriction") and item.restriction:
                if self.player_char.cls.name not in item.restriction:
                    continue

            # Old Key should only be sold in the Secret Shop
            if self.player_char.in_town() and item.name == "Old Key":
                continue

            # Check rarity for town shops
            if self.player_char.in_town() and not self.ignore_rarity_filter:
                min_rarity = max(0.4, (1.0 - (0.02 * self.player_char.player_level())))
                if item.rarity < min_rarity:
                    continue
            elif self.background_image == "dungeon.png":
                # Secret shop: strictly mid-rare items
                in_secret_rarity_band = 0.2 <= item.rarity <= 0.5
                if not in_secret_rarity_band:
                    continue

            # Calculate adjusted cost based on charisma (race-aware).
            adj_scale = self.player_char.shop_price_scale()
            adj_cost = max(1, int(item.value * adj_scale * self.price_multiplier))

            # Count owned items
            owned = 0
            if item.name in self.player_char.inventory:
                owned = len(self.player_char.inventory[item.name])

            # Store item data (no formatting needed - we render at fixed positions)
            rows.append((item.name, item, adj_cost, owned))
        return rows

    def _build_sell_list(self, itemdict):
        """Build item list for selling."""
        for name, items_list in itemdict.items():
            if not items_list:
                continue

            item = items_list[0]
            owned = len(items_list)

            # Calculate sell price (half value, adjusted by charisma; race-aware).
            sell_price = int((item.value // 2) * self.player_char.shop_sell_price_multiplier())

            # Store item data (no formatting needed - we render at fixed positions)
            self.item_list.append((name, item, sell_price, owned))

    def navigate_options(self, flush_events=True, require_key_release=True):
        """Navigate the main menu options (Buy, Sell, Quests, Leave)."""
        input_armed = self._prepare_guarded_input(flush_events, require_key_release)
        while True:
            self.draw_all()

            input_armed = release_guard_allows_input(require_key_release, input_armed)
            for event in get_events():
                if event.type == pygame.QUIT:
                    pygame.quit()
                    import sys

                    sys.exit()
                input_armed = self._arm_guarded_input(event, input_armed)
                hovered = hit_index(self.option_rects(), mouse_position(event))
                if hovered is not None and event.type == pygame.MOUSEMOTION:
                    self.current_option = hovered
                elif hovered is not None and is_left_click(event):
                    if input_armed:
                        self.current_option = hovered
                        return self.options_list[self.current_option]
                if event.type == pygame.KEYDOWN and not input_armed:
                    continue
                elif event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        return "Leave"
                    elif event.key == pygame.K_UP:
                        self.current_option = (self.current_option - 1) % len(self.options_list)
                    elif event.key == pygame.K_DOWN:
                        self.current_option = (self.current_option + 1) % len(self.options_list)
                    elif event.key == pygame.K_RETURN or event.key == pygame.K_SPACE:
                        return self.options_list[self.current_option]

            self.presenter.clock.tick(30)

    def navigate_items(self, flush_events=True, require_key_release=True):
        """Navigate the item list and return selected item."""
        # Handle empty item list
        if not self.item_list and not self.tab_labels:
            return None

        # Calculate max visible items (must match draw_shop_list)
        max_visible = self._visible_item_count()
        input_armed = self._prepare_guarded_input(flush_events, require_key_release)

        while True:
            self.draw_all()

            input_armed = release_guard_allows_input(require_key_release, input_armed)
            for event in get_events():
                if event.type == pygame.QUIT:
                    pygame.quit()
                    import sys

                    sys.exit()
                input_armed = self._arm_guarded_input(event, input_armed)
                if event.type == pygame.MOUSEWHEEL:
                    if not self.item_list:
                        continue
                    direction = -1 if getattr(event, "y", 0) > 0 else 1
                    self.current_item = max(
                        0, min(len(self.item_list) - 1, self.current_item + direction)
                    )
                    self._keep_current_item_visible()
                    continue
                if event.type in (pygame.MOUSEMOTION, pygame.MOUSEBUTTONDOWN):
                    pos = mouse_position(event)
                    tab_index = hit_index(self.item_tab_rects(), pos)
                    if tab_index is not None:
                        if event.type == pygame.MOUSEMOTION:
                            pass
                        elif (
                            is_left_click(event)
                            and input_armed
                            and tab_index != self.active_tab_index
                        ):
                            self.active_tab_index = tab_index
                            active_label = self.tab_labels[self.active_tab_index]
                            self.item_list = list(
                                self._build_buy_rows(self._itemdict_source[active_label])
                            )
                            self.current_item = 0
                            self.scroll_offset = 0
                            self._finalize_item_list(preserve_cursor=False)
                        continue
                    hovered_item = self._hit_item_row(pos)
                    if hovered_item is not None:
                        self.current_item = hovered_item
                        self._keep_current_item_visible()
                        if is_left_click(event) and input_armed:
                            display_str, item, cost, owned = self.item_list[self.current_item]
                            if display_str in {"Go Back", "Back"}:
                                return None
                            return (display_str, item, cost, owned)
                        continue
                if event.type == pygame.KEYDOWN and not input_armed:
                    continue
                elif event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        return None
                    elif event.key == pygame.K_UP:
                        self.current_item = (self.current_item - 1) % len(self.item_list)
                        self._keep_current_item_visible()
                    elif event.key == pygame.K_DOWN:
                        self.current_item = (self.current_item + 1) % len(self.item_list)
                        self._keep_current_item_visible()
                    elif event.key == pygame.K_PAGEUP:
                        self.current_item = max(0, self.current_item - max_visible)
                        self._keep_current_item_visible()
                    elif event.key == pygame.K_PAGEDOWN:
                        self.current_item = min(
                            len(self.item_list) - 1, self.current_item + max_visible
                        )
                        self._keep_current_item_visible()
                    elif event.key == pygame.K_HOME:
                        self.current_item = 0
                        self._keep_current_item_visible()
                    elif event.key == pygame.K_END:
                        self.current_item = len(self.item_list) - 1
                        self._keep_current_item_visible()
                    elif event.key in (pygame.K_LEFT, pygame.K_RIGHT) and self.tab_labels:
                        self.switch_item_tab(-1 if event.key == pygame.K_LEFT else 1)
                    elif event.key == pygame.K_RETURN or event.key == pygame.K_SPACE:
                        if not self.item_list:
                            continue
                        display_str, item, cost, owned = self.item_list[self.current_item]
                        if display_str in {"Go Back", "Back"}:
                            return None
                        return (display_str, item, cost, owned)

            self.presenter.clock.tick(30)

    def switch_item_tab(self, direction: int) -> None:
        """Switch between buy-list subtype tabs."""
        if not self.tab_labels:
            return
        self.active_tab_index = (self.active_tab_index + direction) % len(self.tab_labels)
        active_label = self.tab_labels[self.active_tab_index]
        self.item_list = list(self._build_buy_rows(self._itemdict_source[active_label]))
        self.current_item = 0
        self.scroll_offset = 0
        self._finalize_item_list(preserve_cursor=False)
