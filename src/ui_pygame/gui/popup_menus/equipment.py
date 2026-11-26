"""Equipment behavior for the popup menus package."""

from src.core import items

from .base import BasePopupMenu
from .selections import EquipmentSelectionPopup


class EquipmentPopupMenu(BasePopupMenu):
    def __init__(self, presenter, parent_screen):
        super().__init__(presenter, parent_screen, title="Equipment")

    def build_items(self, player_char):
        eq = getattr(player_char, "equipment", {})
        items = []
        # items: (slot, obj)
        for slot in ("Weapon", "Armor", "Helmet", "OffHand", "Ring", "Pendant"):
            items.append((slot, eq.get(slot)))
        self.items = items
        self.selected_index = 0
        self.scroll_offset = 0

    def item_display_text(self, item):
        slot, obj = item
        name = getattr(obj, "name")
        if not name:
            raise NotImplementedError("Equipment item missing name attribute")
        # Truncate long names to fit
        if len(name) > 20:
            name = name[:17] + "..."
        return f"{slot}: {name}"

    def draw_details(self, player_char):
        """Override to extract object from (slot, obj) tuple."""
        if not self.items:
            x = self.details_rect.left + 16
            y = self.details_rect.top + 12
            self.screen.blit(self.normal_font.render("No items", True, self.GRAY), (x, y))
            return

        slot, obj = self.items[self.selected_index]
        x = self.details_rect.left + 16
        y = self.details_rect.top + 12

        if obj is None:
            # Empty slot
            slot_text = self.large_font.render(f"{slot} Slot", True, self.WHITE)
            self.screen.blit(slot_text, (x, y))
            y += slot_text.get_height() + 8
            self.screen.blit(self.normal_font.render("Empty slot", True, self.GRAY), (x, y))
            return

        # Name
        name = getattr(obj, "name")
        if not name:
            raise NotImplementedError("Equipment item missing name attribute")
        y = self.draw_item_detail_layout(obj, category=slot, exclude_attrs={"slot", "value"})

        # Custom details hook
        self.draw_details_extra(player_char, (slot, obj), x, y)

    def _wrap_text(self, text, max_width):
        """Wrap text to fit within max_width in pixels."""
        words = text.split()
        lines = []
        current_line = []

        for word in words:
            current_line.append(word)
            line = " ".join(current_line)
            line_width = self.normal_font.size(line)[0]

            if line_width > max_width:
                current_line.pop()
                if current_line:
                    lines.append(" ".join(current_line))
                current_line = [word]

        if current_line:
            lines.append(" ".join(current_line))

        return lines

    def draw_details_extra(self, player_char, item, x, y):
        _slot, obj = item
        if obj is None:
            self.screen.blit(self.normal_font.render("Empty slot", True, self.GRAY), (x, y))

    def on_select(self, player_char, item):
        slot, obj = item

        # Get items from inventory that can be equipped in this slot
        equippable_items = self._get_equippable_items_for_slot(player_char, slot)

        # Build options list
        options = []

        # Add equippable items from inventory
        for inv_item in equippable_items:
            options.append(getattr(inv_item, "name", str(inv_item)))

        # Add unequip option if something is equipped (not a placeholder)
        is_placeholder = getattr(obj, "unequip", False) if obj else False
        if obj and not is_placeholder:
            options.append("Unequip")

        options.append("Cancel")

        # Show selection menu
        action_popup = EquipmentSelectionPopup(
            self.presenter,
            self.parent_screen,
            title=f"{slot} Slot",
            header_message=f"Select an item to equip in {slot} slot:",
            options=options,
            slot=slot,
            current_item=obj,
            player_char=player_char,
        )

        # Capture current state for background
        self.parent_screen.draw_all(player_char, do_flip=False)
        self.draw_background(self.screen.copy())
        self.draw_popup(player_char)
        self.draw_list()
        self.draw_details(player_char)
        action_bg = self.screen.copy()

        # Temporarily override draw_background for nested popup
        original_draw_bg = action_popup.draw_background
        action_popup.draw_background = lambda surf: self.screen.blit(action_bg, (0, 0))
        try:
            result = action_popup.show(player_char, flush_events=True, require_key_release=True)
        finally:
            action_popup.draw_background = original_draw_bg

        if result and result[0] == "selection":
            selected = result[1]

            # Check if unequip was selected
            if selected == "Unequip":
                self._unequip_item(player_char, slot, obj)
            # Check if it's cancel
            elif selected == "Cancel":
                pass  # Do nothing
            else:
                # Find the selected item in equippable_items
                for inv_item in equippable_items:
                    if getattr(inv_item, "name", str(inv_item)) == selected:
                        self._equip_from_inventory(player_char, slot, inv_item)
                        break

        return None

    def _get_equippable_items_for_slot(self, player_char, slot):
        """Get all items from inventory that can be equipped in the given slot."""
        equippable = []
        seen_item_names = set()
        can_equip_item = getattr(player_char, "can_equip_item", None)
        equip_check = getattr(getattr(player_char, "cls", None), "equip_check", None)

        def can_equip(candidate, candidate_slot):
            if callable(can_equip_item):
                return can_equip_item(candidate, candidate_slot)
            return not callable(equip_check) or equip_check(candidate, candidate_slot)

        # Map slot to item types
        slot_to_typ = {
            "Weapon": "Weapon",
            "Armor": "Armor",
            "Helmet": "Helmet",
            "OffHand": "OffHand",
            "Ring": "Ring",
            "Pendant": "Pendant",
        }

        target_typ = slot_to_typ.get(slot)
        if not target_typ:
            return equippable

        # Search through inventory
        for category, items_list in player_char.inventory.items():
            for inv_item in items_list:
                item_typ = getattr(inv_item, "typ", None)
                item_name = getattr(inv_item, "name", str(inv_item))

                if item_name in seen_item_names:
                    continue

                # Direct type match
                if item_typ == target_typ:
                    if not can_equip(inv_item, slot):
                        continue
                    equippable.append(inv_item)
                    seen_item_names.add(item_name)
                # One-handed weapons that pass class restrictions can be equipped offhand.
                elif slot == "OffHand" and item_typ == "Weapon":
                    if can_equip(inv_item, "OffHand"):
                        equippable.append(inv_item)
                        seen_item_names.add(item_name)
                # Handle accessories (Ring/Pendant)
                elif item_typ == "Accessory":
                    subtyp = getattr(inv_item, "subtyp", None)
                    if (subtyp == "Ring" and slot == "Ring") or (
                        subtyp == "Pendant" and slot == "Pendant"
                    ):
                        if not can_equip(inv_item, slot):
                            continue
                        equippable.append(inv_item)
                        seen_item_names.add(item_name)

        return equippable

    def _equip_from_inventory(self, player_char, slot, new_item):
        """Equip an item from inventory, unequipping current item if needed."""
        equip_method = getattr(player_char, "equip", None)
        if callable(equip_method):
            if equip_method(slot, new_item) is False:
                return
        else:
            # Get current item
            current_item = player_char.equipment.get(slot)

            # If there's a current item that's not a placeholder, move it to inventory
            if current_item:
                is_placeholder = getattr(current_item, "unequip", False)
                if not is_placeholder:
                    item_name = getattr(current_item, "name", "Unknown")
                    if item_name not in player_char.inventory:
                        player_char.inventory[item_name] = []
                    player_char.inventory[item_name].append(current_item)

            # Equip the new item
            player_char.equipment[slot] = new_item

            # Remove new item from inventory
            for category, items_list in player_char.inventory.items():
                if new_item in items_list:
                    items_list.remove(new_item)
                    if not items_list:
                        del player_char.inventory[category]
                    break

        # Rebuild items list
        self.build_items(player_char)

    def _unequip_item(self, player_char, slot, item):
        """Unequip an item and move to inventory."""
        # Don't unequip placeholder items (NoRing, NoOffHand, etc.)
        if getattr(item, "unequip", False):
            return

        # Remove from equipment and replace with appropriate NoItem
        no_item_classes = {
            "Weapon": items.NoWeapon,
            "Armor": items.NoArmor,
            "Helmet": items.NoHelmet,
            "OffHand": items.NoOffHand,
            "Ring": items.NoRing,
            "Pendant": items.NoPendant,
        }

        if slot in no_item_classes:
            player_char.equipment[slot] = no_item_classes[slot]()
        else:
            player_char.equipment[slot] = None

        # Add to inventory using item name as key
        item_name = getattr(item, "name", "Unknown")
        if item_name not in player_char.inventory:
            player_char.inventory[item_name] = []
        player_char.inventory[item_name].append(item)

        # Rebuild items list
        self.build_items(player_char)
