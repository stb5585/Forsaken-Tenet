"""Equipment behavior for the modern character screen package."""

from __future__ import annotations

import pygame

from src.core.classes import grandmaster
from src.core.combat.action_interface import (
    assign_shortcut,
    learned_action_presentations,
    shortcut_presentations,
)
from src.ui_pygame.assets.ability_icon_manager import get_ability_icon_manager

from ..confirmation_popup import ConfirmationPopup, draw_popup_close_button, popup_close_clicked
from ..input_guards import (
    prepare_guarded_input,
    release_guard_allows_input,
    update_input_armed_from_event,
)
from ..mouse_helpers import hit_index, is_left_click, mouse_position
from ..popup_menus.equipment import EquipmentPopupMenu
from ..popup_menus.inventory import InventoryPopupMenu
from ..popup_menus.journals import BestiaryPopupMenu, QuestPopupMenu
from ..popup_menus.mechanics import SimpleListPopupMenu, TotemAspectsPopupMenu
from .models import EQUIPMENT_SLOT_ORDER, EquipmentSlotSummary, ResistanceSummary


class CharacterEquipmentMixin:
    def _draw_key_values(
        self,
        rows: list[tuple[str, str]],
        rect: pygame.Rect,
        y: int,
        font=None,
        *,
        label_padding: int = 10,
        right_align_values: bool = False,
        row_gap: int = 8,
        bottom_limit: int | None = None,
    ) -> int:
        font = font or self.normal_font
        bottom_limit = bottom_limit if bottom_limit is not None else rect.bottom - 24
        label_width = min(
            220, max((font.size(label)[0] for label, _ in rows), default=80) + label_padding
        )
        x = rect.left + 16
        value_x = x + label_width
        max_value_width = rect.right - value_x - 16
        for label, value in rows:
            self._draw_text(label, font, self.colors.GRAY, x, y, label_width - label_padding)
            value_text = self._fit_text(value, font, max_value_width)
            draw_x = value_x
            if right_align_values:
                value_width = font.size(value_text)[0]
                draw_x = value_x + max(0, max_value_width - value_width)
            self._draw_text(value_text, font, self.colors.WHITE, draw_x, y, max_value_width)
            y += font.get_height() + row_gap
            if y > bottom_limit:
                break
        return y

    def _draw_resistance_group(
        self,
        entries: list[ResistanceSummary],
        rect: pygame.Rect,
        y: int,
        color,
        *,
        font=None,
        row_gap: int = 6,
    ) -> int:
        font = font or self.normal_font
        if not entries:
            self._draw_text("None", font, self.colors.GRAY, rect.left, y, rect.width)
            return y + font.get_height() + row_gap
        row_height = font.get_height() + row_gap
        for entry in entries:
            text = f"{entry.name} ({entry.value * 100:+.0f}%)"
            self._draw_text(text, font, color, rect.left, y, rect.width)
            y += row_height
        return y

    def _draw_equipment_slot_box(
        self, slot: EquipmentSlotSummary, rect: pygame.Rect, *, selected: bool = False
    ) -> None:
        bg_color = (
            (18, 16, 15)
            if slot.item_name != "(empty)" and slot.implemented
            else self.colors.DARK_GRAY
        )
        border_color = (
            self.colors.GOLD
            if slot.implemented and slot.item_name != "(empty)"
            else self.colors.BORDER_COLOR
        )
        text_color = self.colors.WHITE if slot.implemented else self.colors.GRAY
        pygame.draw.rect(self.screen, bg_color, rect)
        pygame.draw.rect(self.screen, border_color, rect, 2)
        if selected:
            overlay = pygame.Surface(rect.size, pygame.SRCALPHA)
            overlay.fill((*self.colors.HIGHLIGHT_BG[:3], 95))
            self.screen.blit(overlay, rect)
            inner = rect.inflate(-6, -6)
            pygame.draw.rect(self.screen, self.colors.GOLD, inner, 4)
            pygame.draw.rect(self.screen, (255, 244, 170), inner.inflate(-8, -8), 1)
            corner_len = min(28, max(14, rect.width // 7))
            for x1, x2 in (
                (inner.left, inner.left + corner_len),
                (inner.right - corner_len, inner.right),
            ):
                pygame.draw.line(self.screen, (255, 244, 170), (x1, inner.top), (x2, inner.top), 3)
                pygame.draw.line(
                    self.screen, (255, 244, 170), (x1, inner.bottom), (x2, inner.bottom), 3
                )
        x = rect.left + 10
        y = rect.top + 8
        width = rect.width - 20
        self._draw_text(slot.slot, self.normal_font, self.colors.GRAY, x, y, width)
        y += self.normal_font.get_height() + 2
        art_width = min(76, max(58, rect.width // 4))
        art_height = max(72, rect.height - (y - rect.top) - 12)
        art_rect = pygame.Rect(x, y, art_width, art_height)
        if slot.icon_item is not None:
            self._draw_item_art_backdrop(art_rect)
            render = self.item_render_manager.get_scaled_render(slot.icon_item, art_rect.size)
            self.screen.blit(render, art_rect)

        text_x = art_rect.right + 8
        text_width = max(40, rect.right - text_x - 10)
        item_name = self._fit_text(slot.item_name, self.normal_font, text_width)
        self._draw_text(item_name, self.normal_font, text_color, text_x, y, text_width)
        y += self.normal_font.get_height() + 4
        value_x = text_x + min(max(112, (text_width * 2) // 3), max(40, text_width - 40))
        value_width = max(32, rect.right - value_x - 10)
        label_width = max(32, value_x - text_x - 8)
        for label, value in slot.detail_rows[:4]:
            self._draw_text(f"{label}:", self.small_font, self.colors.WHITE, text_x, y, label_width)
            value_text = self._fit_text(value, self.small_font, value_width)
            rendered_width = self.small_font.size(value_text)[0]
            value_draw_x = value_x + max(0, value_width - rendered_width)
            self._draw_text(
                value_text, self.small_font, self.colors.WHITE, value_draw_x, y, value_width
            )
            y += self.small_font.get_height()
        for buff in slot.buffs[:2]:
            self._draw_text(
                f"Buff: {buff}", self.small_font, self.colors.GOLD, text_x, y, text_width
            )
            y += self.small_font.get_height()

    def _draw_item_art_backdrop(self, rect: pygame.Rect) -> None:
        backdrop = pygame.Surface(rect.size, pygame.SRCALPHA)
        backdrop.fill((0, 0, 0, 150))
        self.screen.blit(backdrop, rect)
        pygame.draw.rect(self.screen, (124, 99, 62), rect, 1)

    def equipment_slot_rects(self, rect: pygame.Rect | None = None) -> dict[str, pygame.Rect]:
        """Return fixed paper-doll slot rectangles for hit testing and drawing."""
        rect = rect or self.equipment_layout_rect()
        box_width = min(260, max(180, (rect.width - 56) // 3))
        box_height = min(150, max(140, (rect.height - 28) // 3))
        center_x = rect.centerx
        row_gap = max(12, (rect.height - (box_height * 3) - 36) // 2)
        top_y = rect.top + 8
        middle_y = top_y + box_height + row_gap
        bottom_y = middle_y + box_height + row_gap

        return {
            "Helmet": pygame.Rect(center_x - box_width // 2, top_y, box_width, box_height),
            "Weapon": pygame.Rect(rect.left, middle_y, box_width, box_height),
            "Armor": pygame.Rect(center_x - box_width // 2, middle_y, box_width, box_height),
            "OffHand": pygame.Rect(rect.right - box_width, middle_y, box_width, box_height),
            "Ring": pygame.Rect(center_x - box_width - 8, bottom_y, box_width, box_height),
            "Pendant": pygame.Rect(center_x + 8, bottom_y, box_width, box_height),
        }

    def equipment_layout_rect(self) -> pygame.Rect:
        """Return the paper-doll layout rect without drawing the surrounding panel."""
        y = self.details_rect.top + 14 + self.large_font.get_height() + 10
        return pygame.Rect(
            self.details_rect.left + 28,
            y,
            self.details_rect.width - 56,
            self.details_rect.bottom - y - 20,
        )

    def _draw_equipment_paper_doll(
        self, slots: list[EquipmentSlotSummary], rect: pygame.Rect, selected_slot: str
    ) -> None:
        slot_by_name = {slot.slot: slot for slot in slots}
        positions = self.equipment_slot_rects(rect)
        for slot_name in EQUIPMENT_SLOT_ORDER:
            slot = slot_by_name.get(slot_name)
            if slot is not None:
                self._draw_equipment_slot_box(
                    slot,
                    positions[slot_name],
                    selected=slot_name == selected_slot and slot.implemented,
                )

    def draw_equipment_tab(self, player_char):
        self._draw_panel(self.details_rect, "Equipment")
        helper = (
            "Arrows: Select gear  Enter: Change  E/Esc: Back"
            if self.equipment_selector_active
            else "E: Select gear"
        )
        helper_width = self.small_font.size(helper)[0]
        self._draw_text(
            helper,
            self.small_font,
            self.colors.GRAY,
            self.details_rect.right - 16 - min(helper_width, self.details_rect.width - 32),
            self.details_rect.top + 18,
            self.details_rect.width - 32,
        )
        layout_rect = self.equipment_layout_rect()
        slots = self.build_equipment_slots(player_char)
        selected_slot = (
            self.selected_equipment_slot(player_char) if self.equipment_selector_active else ""
        )
        self._draw_equipment_paper_doll(slots, layout_rect, selected_slot)

    def action_rects(self) -> list[pygame.Rect]:
        """Return clickable rectangles for the bottom action menu."""
        y = self.actions_rect.top + 14 + self.large_font.get_height() + 10
        x = self.actions_rect.left + 16
        option_width = max(130, (self.actions_rect.width - 32) // max(1, len(self.menu_options)))
        return [
            pygame.Rect(
                x + (index * option_width), y, option_width - 8, self.actions_rect.bottom - y - 12
            )
            for index, _option in enumerate(self.menu_options)
        ]

    def draw_menu(self):
        self._draw_panel(self.actions_rect, "Actions")
        for index, option in enumerate(self.menu_options):
            rect = self.action_rects()[index]
            if index == self.current_selection:
                pygame.draw.rect(self.screen, self.colors.HIGHLIGHT_BG, rect)
                pygame.draw.rect(self.screen, self.colors.GOLD, rect, 1)
            self._draw_text(
                option,
                self.small_font,
                self.colors.GOLD if index == self.current_selection else self.colors.WHITE,
                rect.left + 8,
                rect.centery - self.small_font.get_height() // 2,
                rect.width - 16,
            )

    def draw_all(self, player_char, do_flip=True):
        self._progression_player = player_char
        self.ensure_active_tab_visible(player_char)
        self.draw_background()
        self.draw_tabs(player_char)
        if self.active_tab.key == "character":
            self.draw_character_panel(player_char)
            self.draw_combat_panel(player_char)
        elif self.active_tab.key == "class":
            self.draw_class_tab(player_char)
        elif self.active_tab.key == "equipment":
            self.draw_equipment_tab(player_char)
        elif self.active_tab.key == "progression":
            self.progression_view.show_embedded_navigation_helper = True
            self.progression_view.embedded_navigation_active = self.progression_selector_active
            self.progression_view.draw_embedded(player_char, self.content_rect)
        self.draw_menu()
        if do_flip:
            pygame.display.flip()

    def _open_menu_choice(self, chosen: str, player_char) -> str | None:
        if chosen == "Inventory":
            popup = InventoryPopupMenu(self.presenter, self)
            popup.show(player_char, flush_events=True, require_key_release=True)
        elif chosen == "Quests":
            popup = QuestPopupMenu(self.presenter, self)
            _ = popup.show(player_char, flush_events=True, require_key_release=True)
        elif chosen == "Key Items":
            special_inv = getattr(player_char, "special_inventory", {})
            if not special_inv:
                self.draw_all(player_char, do_flip=False)
                popup = ConfirmationPopup(
                    self.presenter, "You do not have any key items.", show_buttons=False
                )
                popup.show(flush_events=True, require_key_release=True)
            else:
                popup = SimpleListPopupMenu(
                    self.presenter, self, title="Key Items", source_fn=self._get_key_items_list
                )
                _ = popup.show(player_char, flush_events=True, require_key_release=True)
        elif chosen == "Bestiary":
            popup = BestiaryPopupMenu(self.presenter, self)
            _ = popup.show(player_char, flush_events=True, require_key_release=True)
        elif chosen == "Abilities":
            popup = SimpleListPopupMenu(
                self.presenter,
                self,
                title="Abilities",
                source_fn=self._ability_reference_entries,
            )
            popup.show(player_char, flush_events=True, require_key_release=True)
        elif chosen in {"Action Layout", "Specials"}:
            self._edit_action_layout(player_char)
        elif chosen == "Totem Aspects":
            popup = TotemAspectsPopupMenu(self.presenter, self, title="Totem Aspects")
            _ = popup.show(player_char, flush_events=True, require_key_release=True)
        elif chosen == "Exit Menu":
            return chosen
        return None

    def _base_menu_options(self) -> list[str]:
        return [
            "Inventory",
            "Quests",
            "Key Items",
            "Bestiary",
            "Abilities",
            "Action Layout",
            "Exit Menu",
        ]

    @staticmethod
    def _ability_reference_entries(player_char):
        """Return every learned active and passive ability for the reference view."""
        spellbook = getattr(player_char, "spellbook", {}) or {}
        entries = []
        for category in ("Skills", "Spells"):
            abilities = spellbook.get(category, {}) if isinstance(spellbook, dict) else {}
            if not abilities:
                continue
            entries.append(f"--- {category} ---")
            entries.extend(abilities.values())
        return entries

    def _edit_action_layout(self, player_char) -> None:
        """Edit the same persisted shortcut layout used by in-combat All Actions."""
        actions = learned_action_presentations(player_char)
        if not actions:
            popup = ConfirmationPopup(
                self.presenter, "No active learned actions.", show_buttons=False
            )
            popup.show(flush_events=True, require_key_release=True)
            return
        selected_action = 0
        selected_slot = 0
        category_offsets = {"Skill": 0, "Spell": 0}
        dragged_action = None
        dragged_position = None
        input_armed = prepare_guarded_input(flush_events=True, require_key_release=True)
        while True:
            self.draw_all(player_char, do_flip=False)
            panel = pygame.Rect(
                self.content_rect.left + 24,
                self.content_rect.top + 24,
                self.content_rect.width - 48,
                self.content_rect.height - 48,
            )
            self.draw_semi_transparent_panel(panel, alpha=235)
            pygame.draw.rect(self.screen, self.colors.GOLD, panel, 2)
            draw_popup_close_button(self.screen, panel, self.small_font)
            self._draw_text(
                "Learned Abilities",
                self.large_font,
                self.colors.GOLD,
                panel.left + 18,
                panel.top + 14,
            )
            self._draw_text(
                "Drag an icon to a shortcut slot · Enter assign · Backspace clear · Esc or x close",
                self.small_font,
                self.colors.LIGHT_GRAY,
                panel.left + 18,
                panel.top + 48,
                panel.width - 36,
            )
            catalog_rect = pygame.Rect(
                panel.left + 18,
                panel.top + 80,
                panel.width - 36,
                panel.height - 220,
            )
            gap = 14
            column_width = (catalog_rect.width - gap) // 2
            categories = {
                "Skill": [
                    (index, action)
                    for index, action in enumerate(actions)
                    if action.engine_action == "Use Skill"
                ],
                "Spell": [
                    (index, action)
                    for index, action in enumerate(actions)
                    if action.engine_action == "Cast Spell"
                ],
            }
            action_rows = []
            icon_manager = get_ability_icon_manager()
            visible_count = max(1, (catalog_rect.height - 34) // 50)
            for column, category in enumerate(("Skill", "Spell")):
                column_rect = pygame.Rect(
                    catalog_rect.left + column * (column_width + gap),
                    catalog_rect.top,
                    column_width,
                    catalog_rect.height,
                )
                pygame.draw.rect(self.screen, self.colors.BORDER_COLOR, column_rect, 1)
                self._draw_text(
                    f"{category}s",
                    self.normal_font,
                    self.colors.GOLD,
                    column_rect.left + 8,
                    column_rect.top + 7,
                    column_rect.width - 16,
                )
                entries = categories[category]
                selected_in_category = next(
                    (
                        position
                        for position, (index, _action) in enumerate(entries)
                        if index == selected_action
                    ),
                    None,
                )
                offset = min(category_offsets[category], max(0, len(entries) - visible_count))
                if selected_in_category is not None:
                    if selected_in_category < offset:
                        offset = selected_in_category
                    elif selected_in_category >= offset + visible_count:
                        offset = selected_in_category - visible_count + 1
                category_offsets[category] = offset
                y = column_rect.top + 32
                for index, action in entries[offset : offset + visible_count]:
                    rect = pygame.Rect(column_rect.left + 6, y, column_rect.width - 12, 45)
                    action_rows.append((index, category, rect))
                    fill = self.colors.HIGHLIGHT_BG if index == selected_action else (29, 29, 35)
                    pygame.draw.rect(self.screen, fill, rect, border_radius=4)
                    pygame.draw.rect(
                        self.screen,
                        self.colors.GOLD if index == selected_action else self.colors.BORDER_COLOR,
                        rect,
                        2 if index == selected_action else 1,
                        border_radius=4,
                    )
                    icon = pygame.transform.smoothscale(
                        icon_manager.get_icon(action.icon_key),
                        (34, 34),
                    )
                    self.screen.blit(icon, (rect.left + 6, rect.top + 5))
                    label = action.display_name.replace(f"{category}: ", "")
                    self._draw_text(
                        label,
                        self.small_font,
                        self.colors.WHITE,
                        rect.left + 46,
                        rect.top + 7,
                        rect.width - 52,
                    )
                    y += 50

            slot_rows = []
            slot_y = panel.bottom - 116
            self._draw_text(
                "Combat Shortcuts",
                self.normal_font,
                self.colors.GOLD,
                panel.left + 18,
                slot_y - 25,
                panel.width - 36,
            )
            slot_width = max(72, (panel.width - 48) // 6)
            for slot in shortcut_presentations(player_char):
                rect = pygame.Rect(
                    panel.left + 18 + slot.index * slot_width,
                    slot_y,
                    slot_width - 5,
                    88,
                )
                slot_rows.append(rect)
                if slot.index == selected_slot:
                    pygame.draw.rect(self.screen, self.colors.HIGHLIGHT_BG, rect)
                pygame.draw.rect(
                    self.screen,
                    self.colors.GOLD if slot.index == selected_slot else self.colors.BORDER_COLOR,
                    rect,
                    2 if slot.index == selected_slot else 1,
                    border_radius=4,
                )
                self._draw_text(
                    str(slot.index + 1),
                    self.small_font,
                    self.colors.GOLD,
                    rect.left + 6,
                    rect.top + 5,
                    18,
                )
                if slot.action is not None:
                    icon = pygame.transform.smoothscale(
                        icon_manager.get_icon(slot.action.icon_key),
                        (36, 36),
                    )
                    self.screen.blit(icon, icon.get_rect(centerx=rect.centerx, top=rect.top + 8))
                    label = slot.action.display_name.replace("Spell: ", "").replace("Skill: ", "")
                else:
                    label = "Empty"
                self._draw_text(
                    label,
                    self.small_font,
                    self.colors.WHITE if slot.action is not None else self.colors.GRAY,
                    rect.left + 5,
                    rect.top + 51,
                    rect.width - 10,
                )
            hovered_description = ""
            try:
                pointer = pygame.mouse.get_pos()
            except pygame.error:
                pointer = (-1, -1)
            for index, _category, rect in action_rows:
                if rect.collidepoint(pointer):
                    hovered_description = str(actions[index].description or "")
                    break
            if hovered_description:
                tooltip = pygame.Rect(panel.left + 18, slot_y - 70, panel.width - 36, 38)
                pygame.draw.rect(self.screen, (20, 20, 26), tooltip, border_radius=4)
                pygame.draw.rect(self.screen, self.colors.BORDER_COLOR, tooltip, 1, border_radius=4)
                self._draw_text(
                    hovered_description,
                    self.small_font,
                    self.colors.LIGHT_GRAY,
                    tooltip.left + 8,
                    tooltip.top + 9,
                    tooltip.width - 16,
                )
            if dragged_action is not None and dragged_position is not None:
                drag_icon = pygame.transform.smoothscale(
                    icon_manager.get_icon(actions[dragged_action].icon_key),
                    (42, 42),
                )
                drag_icon.set_alpha(210)
                self.screen.blit(drag_icon, drag_icon.get_rect(center=dragged_position))
            pygame.display.flip()
            input_armed = release_guard_allows_input(True, input_armed)
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    pygame.quit()
                    import sys

                    sys.exit()
                input_armed = update_input_armed_from_event(event, True, input_armed)
                if event.type == pygame.KEYDOWN and not input_armed:
                    continue
                if (
                    is_left_click(event)
                    and input_armed
                    and (
                        popup_close_clicked(event, panel)
                        or not panel.collidepoint(mouse_position(event) or (-1, -1))
                    )
                ):
                    return
                if event.type == pygame.KEYDOWN:
                    if event.key in (pygame.K_ESCAPE, pygame.K_BACKSPACE):
                        if event.key == pygame.K_BACKSPACE:
                            assign_shortcut(player_char, selected_slot, None)
                            continue
                        return
                    if event.key in (pygame.K_UP, pygame.K_w):
                        selected_action = (selected_action - 1) % len(actions)
                    elif event.key in (pygame.K_DOWN, pygame.K_s):
                        selected_action = (selected_action + 1) % len(actions)
                    elif event.key in (pygame.K_LEFT, pygame.K_a):
                        selected_slot = (selected_slot - 1) % 6
                    elif event.key in (pygame.K_RIGHT, pygame.K_d):
                        selected_slot = (selected_slot + 1) % 6
                    elif event.key in (pygame.K_RETURN, pygame.K_SPACE):
                        reference = actions[selected_action].reference
                        if reference is not None:
                            assign_shortcut(player_char, selected_slot, reference)
                elif event.type == pygame.MOUSEWHEEL:
                    position = pygame.mouse.get_pos()
                    for _index, category, rect in action_rows:
                        if rect.collidepoint(position):
                            entries = categories[category]
                            category_offsets[category] = max(
                                0,
                                min(
                                    max(0, len(entries) - visible_count),
                                    category_offsets[category] - event.y,
                                ),
                            )
                            break
                elif event.type in (
                    pygame.MOUSEMOTION,
                    pygame.MOUSEBUTTONDOWN,
                    pygame.MOUSEBUTTONUP,
                ):
                    position = mouse_position(event)
                    action_index = next(
                        (
                            index
                            for index, _category, rect in action_rows
                            if rect.collidepoint(position)
                        ),
                        None,
                    )
                    slot_index = hit_index(slot_rows, position)
                    if action_index is not None:
                        selected_action = action_index
                    if event.type == pygame.MOUSEBUTTONDOWN and is_left_click(event):
                        if action_index is not None:
                            dragged_action = action_index
                            dragged_position = position
                        elif slot_index is not None:
                            selected_slot = slot_index
                            slot_action = shortcut_presentations(player_char)[slot_index].action
                            if slot_action is not None:
                                dragged_action = next(
                                    (
                                        index
                                        for index, learned in enumerate(actions)
                                        if learned.reference == slot_action.reference
                                    ),
                                    None,
                                )
                                dragged_position = position
                    elif event.type == pygame.MOUSEMOTION and dragged_action is not None:
                        dragged_position = position
                    elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
                        if slot_index is not None and dragged_action is not None:
                            reference = actions[dragged_action].reference
                            if reference is not None:
                                assign_shortcut(player_char, slot_index, reference)
                            selected_slot = slot_index
                        dragged_action = None
                        dragged_position = None
                    elif slot_index is not None:
                        selected_slot = slot_index

    def open_selected_equipment_change(self, player_char) -> None:
        slot_name = self.selected_equipment_slot(player_char)
        popup = EquipmentPopupMenu(self.presenter, self)
        popup.build_items(player_char)
        for index, entry in enumerate(popup.items):
            if isinstance(entry, tuple) and entry[0] == slot_name:
                popup.selected_index = index
                popup.on_select(player_char, entry)
                return

    def _confirm_progression_departure(self, target_key: str | None = None) -> bool:
        """Guard tab/menu exits while a point distribution is uncommitted."""
        if self.active_tab.key != "progression":
            return True
        if target_key == "progression":
            return True
        return self.progression_view.confirm_discard_pending()

    def navigate(self, player_char, flush_events=True, require_key_release=True):
        self._progression_player = player_char
        self.progression_view.player_char = player_char
        menu_options = self._base_menu_options()
        if self._has_totem_aspects(player_char):
            menu_options.insert(-1, "Totem Aspects")
        self.menu_options = menu_options
        self.current_selection = min(self.current_selection, len(self.menu_options) - 1)

        started_in_town = player_char.in_town()
        try:
            input_armed = prepare_guarded_input(
                flush_events=flush_events, require_key_release=require_key_release
            )
        except pygame.error:
            input_armed = not require_key_release

        while True:
            if not started_in_town and player_char.in_town():
                return "Exit Menu"

            self.ensure_active_tab_visible(player_char)
            self.draw_all(player_char)
            input_armed = release_guard_allows_input(require_key_release, input_armed)
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    pygame.quit()
                    import sys

                    sys.exit()
                input_armed = update_input_armed_from_event(event, True, input_armed)

                if event.type in (pygame.MOUSEMOTION, pygame.MOUSEBUTTONDOWN):
                    if self.active_tab.key == "progression" and self.content_rect.collidepoint(
                        mouse_position(event)
                    ):
                        self.progression_selector_active = True
                        if self.progression_view.handle_event(event):
                            continue
                    pos = mouse_position(event)
                    tab_index = hit_index(self.tab_button_rects(player_char), pos)
                    action_index = hit_index(self.action_rects(), pos)
                    if action_index is not None and event.type == pygame.MOUSEMOTION:
                        self.current_selection = action_index
                    elif tab_index is not None and is_left_click(event):
                        if input_armed:
                            target_key = self.visible_tabs(player_char)[tab_index].key
                            if not self._confirm_progression_departure(target_key):
                                continue
                            self.select_visible_tab_index(tab_index, player_char)
                            if self.active_tab.key != "equipment":
                                self.equipment_selector_active = False
                            if self.active_tab.key != "class":
                                self.class_companion_selector_active = False
                        continue
                    elif action_index is not None and is_left_click(event):
                        if input_armed:
                            self.current_selection = action_index
                            chosen = self.menu_options[self.current_selection]
                            if chosen == "Exit Menu" and not self._confirm_progression_departure():
                                continue
                            result = self._open_menu_choice(chosen, player_char)
                            if result:
                                return result
                        continue
                    elif self.active_tab.key == "equipment":
                        slot_rects = self.equipment_slot_rects()
                        slot_names = list(EQUIPMENT_SLOT_ORDER)
                        slot_index = hit_index([slot_rects[name] for name in slot_names], pos)
                        if slot_index is not None:
                            self.equipment_selector_active = True
                            self.set_selected_equipment_slot(player_char, slot_names[slot_index])
                            if is_left_click(event) and input_armed:
                                self.open_selected_equipment_change(player_char)
                            continue
                    elif (
                        self.active_tab.key == "class"
                        and self.active_mechanic_label(player_char) == "Aerial Tempo"
                    ):
                        row_index = hit_index(self.jump_mod_row_rects(), pos)
                        if row_index is not None:
                            self.selected_jump_mod_index = row_index
                            if is_left_click(event) and input_armed:
                                self._toggle_selected_jump_mod(player_char)
                            continue
                    elif (
                        self.active_tab.key == "class"
                        and self.active_mechanic_label(player_char) == "Forms"
                    ):
                        form_action = next(
                            (
                                label
                                for label, rect in getattr(self, "_form_action_rects", [])
                                if rect.collidepoint(pos)
                            ),
                            None,
                        )
                        if form_action is not None and is_left_click(event) and input_armed:
                            if form_action == "Dismiss Form":
                                player_char.transform(back=True)
                            elif player_char.select_transform_form(form_action):
                                player_char.transform()
                            continue
                    elif (
                        self.active_tab.key == "class"
                        and not grandmaster.is_weapon_discipline_class(player_char)
                    ):
                        entries = self.class_companion_entries(player_char)
                        tile_index = hit_index(self.class_companion_tile_rects(entries), pos)
                        if tile_index is not None:
                            self.class_companion_selector_active = True
                            self.selected_class_companion_index = tile_index
                            if is_left_click(event) and input_armed:
                                self._open_class_companion_popup(player_char)
                            continue
                    elif self.active_tab.key == "class" and grandmaster.is_weapon_discipline_class(
                        player_char
                    ):
                        row_index = hit_index(self.weapon_discipline_row_rects(), pos)
                        if row_index is not None:
                            self.selected_weapon_discipline_index = row_index
                            if is_left_click(event) and input_armed:
                                self._open_weapon_discipline_popup(player_char)
                            continue

                if event.type == pygame.KEYDOWN and not input_armed:
                    continue
                if event.type != pygame.KEYDOWN:
                    continue

                if self.active_tab.key == "progression" and event.key == pygame.K_p:
                    self.progression_selector_active = not self.progression_selector_active
                    continue

                if (
                    self.active_tab.key == "progression"
                    and self.progression_selector_active
                    and self.progression_view.handle_event(event)
                ):
                    continue

                if event.key == pygame.K_ESCAPE and self.equipment_selector_active:
                    self.equipment_selector_active = False
                elif event.key == pygame.K_ESCAPE and self.class_companion_selector_active:
                    self.class_companion_selector_active = False
                elif event.key == pygame.K_ESCAPE and self.progression_selector_active:
                    self.progression_selector_active = False
                elif event.key == pygame.K_ESCAPE:
                    if not self._confirm_progression_departure():
                        continue
                    return "Exit Menu"
                elif event.key == pygame.K_e and self.active_tab.key == "equipment":
                    self.equipment_selector_active = not self.equipment_selector_active
                elif event.key == pygame.K_c and self.active_tab.key == "class":
                    if self.active_mechanic_label(player_char) == "Totems":
                        self._open_totem_aspects_popup(player_char)
                    elif self.active_mechanic_label(player_char) == "Crescendo":
                        self._open_composition_popup(player_char)
                    elif not grandmaster.is_weapon_discipline_class(player_char):
                        entries = self.class_companion_entries(player_char)
                        self.class_companion_selector_active = (
                            bool(entries) and not self.class_companion_selector_active
                        )
                elif event.key in (pygame.K_TAB, pygame.K_RIGHT):
                    if (
                        self.active_tab.key == "equipment"
                        and self.equipment_selector_active
                        and event.key == pygame.K_RIGHT
                    ):
                        self.move_equipment_selector(player_char, "right")
                    elif (
                        self.active_tab.key == "class"
                        and self.class_companion_selector_active
                        and event.key == pygame.K_RIGHT
                        and self.class_companion_entries(player_char)
                    ):
                        entries = self.class_companion_entries(player_char)
                        self.selected_class_companion_index = min(
                            len(entries) - 1, self.selected_class_companion_index + 1
                        )
                    else:
                        visible = self.visible_tabs(player_char)
                        active_index = next(
                            (
                                index
                                for index, tab in enumerate(visible)
                                if tab.key == self.active_tab.key
                            ),
                            0,
                        )
                        target_key = visible[(active_index + 1) % len(visible)].key
                        if not self._confirm_progression_departure(target_key):
                            continue
                        self.move_tab(1, player_char)
                elif event.key == pygame.K_LEFT:
                    if self.active_tab.key == "equipment" and self.equipment_selector_active:
                        self.move_equipment_selector(player_char, "left")
                    elif (
                        self.active_tab.key == "class"
                        and self.class_companion_selector_active
                        and self.class_companion_entries(player_char)
                    ):
                        self.selected_class_companion_index = max(
                            0, self.selected_class_companion_index - 1
                        )
                    else:
                        visible = self.visible_tabs(player_char)
                        active_index = next(
                            (
                                index
                                for index, tab in enumerate(visible)
                                if tab.key == self.active_tab.key
                            ),
                            0,
                        )
                        target_key = visible[(active_index - 1) % len(visible)].key
                        if not self._confirm_progression_departure(target_key):
                            continue
                        self.move_tab(-1, player_char)
                elif event.key == pygame.K_1:
                    target_key = self.visible_tabs(player_char)[0].key
                    if not self._confirm_progression_departure(target_key):
                        continue
                    self.select_visible_tab_index(0, player_char)
                elif event.key == pygame.K_2:
                    target_key = self.visible_tabs(player_char)[1].key
                    if not self._confirm_progression_departure(target_key):
                        continue
                    self.select_visible_tab_index(1, player_char)
                elif event.key == pygame.K_3:
                    visible = self.visible_tabs(player_char)
                    if len(visible) <= 2:
                        continue
                    target_key = visible[2].key
                    if not self._confirm_progression_departure(target_key):
                        continue
                    self.select_visible_tab_index(2, player_char)
                elif event.key == pygame.K_UP:
                    if self.active_tab.key == "equipment" and self.equipment_selector_active:
                        self.move_equipment_selector(player_char, "up")
                    elif (
                        self.active_tab.key == "class"
                        and self.active_mechanic_label(player_char) == "Aerial Tempo"
                        and self.jump_mod_entries(player_char)
                    ):
                        self.selected_jump_mod_index = max(0, self.selected_jump_mod_index - 1)
                    elif (
                        self.active_tab.key == "class"
                        and self.class_companion_selector_active
                        and self.class_companion_entries(player_char)
                    ):
                        self.selected_class_companion_index = max(
                            0, self.selected_class_companion_index - 1
                        )
                    elif self.active_tab.key == "class" and grandmaster.is_weapon_discipline_class(
                        player_char
                    ):
                        self.selected_weapon_discipline_index = max(
                            0, self.selected_weapon_discipline_index - 1
                        )
                    else:
                        self.current_selection = (self.current_selection - 1) % len(
                            self.menu_options
                        )
                elif event.key == pygame.K_DOWN:
                    if self.active_tab.key == "equipment" and self.equipment_selector_active:
                        self.move_equipment_selector(player_char, "down")
                    elif (
                        self.active_tab.key == "class"
                        and self.active_mechanic_label(player_char) == "Aerial Tempo"
                        and self.jump_mod_entries(player_char)
                    ):
                        entries = self.jump_mod_entries(player_char)
                        self.selected_jump_mod_index = min(
                            len(entries) - 1, self.selected_jump_mod_index + 1
                        )
                    elif (
                        self.active_tab.key == "class"
                        and self.class_companion_selector_active
                        and self.class_companion_entries(player_char)
                    ):
                        entries = self.class_companion_entries(player_char)
                        self.selected_class_companion_index = min(
                            len(entries) - 1, self.selected_class_companion_index + 1
                        )
                    elif self.active_tab.key == "class" and grandmaster.is_weapon_discipline_class(
                        player_char
                    ):
                        weapon_types = grandmaster.weapon_discipline_types(
                            player_char,
                        )
                        self.selected_weapon_discipline_index = min(
                            len(weapon_types) - 1,
                            self.selected_weapon_discipline_index + 1,
                        )
                    else:
                        self.current_selection = (self.current_selection + 1) % len(
                            self.menu_options
                        )
                elif (
                    event.key == pygame.K_a
                    and self.active_tab.key == "class"
                    and self.class_companion_selector_active
                    and self.class_companion_entries(player_char)
                ):
                    self.selected_class_companion_index = max(
                        0, self.selected_class_companion_index - 1
                    )
                elif (
                    event.key == pygame.K_d
                    and self.active_tab.key == "class"
                    and self.class_companion_selector_active
                    and self.class_companion_entries(player_char)
                ):
                    entries = self.class_companion_entries(player_char)
                    self.selected_class_companion_index = min(
                        len(entries) - 1, self.selected_class_companion_index + 1
                    )
                elif (
                    event.key == pygame.K_s
                    and self.active_tab.key == "class"
                    and self.class_companion_selector_active
                ):
                    self._activate_selected_tamed_companion(player_char)
                elif (
                    event.key == pygame.K_r
                    and self.active_tab.key == "class"
                    and self.class_companion_selector_active
                ):
                    self._release_selected_tamed_companion(player_char)
                elif event.key in (pygame.K_RETURN, pygame.K_SPACE):
                    if self.active_tab.key == "equipment" and self.equipment_selector_active:
                        self.open_selected_equipment_change(player_char)
                    elif (
                        self.active_tab.key == "class"
                        and self.active_mechanic_label(player_char) == "Aerial Tempo"
                        and self._has_jump_mods(player_char)
                    ):
                        self._toggle_selected_jump_mod(player_char)
                    elif (
                        self.active_tab.key == "class"
                        and self.active_mechanic_label(player_char) == "Totems"
                    ):
                        self._open_totem_aspects_popup(player_char)
                    elif (
                        self.active_tab.key == "class"
                        and self.active_mechanic_label(player_char) == "Crescendo"
                    ):
                        self._open_composition_popup(player_char)
                    elif (
                        self.active_tab.key == "class"
                        and self.class_companion_selector_active
                        and self.class_companion_entries(player_char)
                    ):
                        self._open_class_companion_popup(player_char)
                    elif self.active_tab.key == "class" and grandmaster.is_weapon_discipline_class(
                        player_char
                    ):
                        self._open_weapon_discipline_popup(player_char)
                    else:
                        chosen = self.menu_options[self.current_selection]
                        if chosen == "Exit Menu" and not self._confirm_progression_departure():
                            continue
                        result = self._open_menu_choice(chosen, player_char)
                        if result:
                            return result

            self.presenter.clock.tick(30)
