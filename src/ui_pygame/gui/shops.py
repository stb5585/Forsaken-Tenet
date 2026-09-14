"""
Shop system for GUI - handles blacksmith, alchemist, jeweler, and magic shops.
Implements the core shop logic from town.py adapted for Pygame presenter.
"""

from src.core import items as items_module
from src.core.classes import dragoon

from .confirmation_popup import ConfirmationPopup
from .popup_menus import SelectionPopup
from .shop_screen import ShopScreen
from .town_base import TownScreenBase


class ShopManager(TownScreenBase):
    """Manages all shop interactions with pygame presenter."""

    MAGIC_SHOPKEEPER = "Seraphine Voss"
    MAGIC_SHOP_MESSAGE = "Seraphine Voss's Magic Shop"
    MAGIC_SHOP_MIN_LEVEL = 3

    def __init__(self, presenter, player_char):
        super().__init__(presenter)
        self.player_char = player_char
        self._active_shopkeeper_portrait: str | None = None
        self._active_price_multiplier = 1.0

    def _set_shopkeeper_portrait(self, shop_screen: ShopScreen) -> None:
        if self._active_shopkeeper_portrait:
            shop_screen.set_location_portrait(self._active_shopkeeper_portrait)

    def visit_blacksmith(self):
        """Visit Griswold's Blacksmith - weapons and shields."""
        if self.player_char.player_level() < 5:
            popup = ConfirmationPopup(
                self.presenter,
                "Sorry but the blacksmith is currently closed. Try again later.",
                show_buttons=False,
            )
            popup.show(flush_events=True, require_key_release=True)
            return

        if "Unobtainium" in self.player_char.special_inventory:
            self._offer_ultimate_weapon_crafting()

        # Use ShopScreen for the main interface
        shop_screen = ShopScreen(self.presenter, self.player_char, "Griswold's Blacksmith")
        self._active_shopkeeper_portrait = "Griswold"
        self._set_shopkeeper_portrait(shop_screen)
        shop_screen.set_options(["Buy", "Sell", "Quests", "Leave"])

        from .quest_manager import QuestManager

        qm = QuestManager(
            self.presenter,
            self.player_char,
            quest_text_renderer=lambda text: shop_screen.display_quest_text(
                text, npc_name="Griswold"
            ),
            renderer_preserve_formatting=True,
        )

        while True:
            choice = shop_screen.navigate_options()

            if choice is None or choice == "Leave":
                popup = ConfirmationPopup(
                    self.presenter, "Come back whenever you'd like.", show_buttons=False
                )
                popup.show(flush_events=True, require_key_release=True)
                break
            elif choice == "Buy":
                # Update options to show buy categories
                shop_screen.set_options(["Weapons", "Shields", "Armor", "Helmets", "Back"])
                buy_choice = shop_screen.navigate_options()

                if buy_choice == "Weapons":
                    self.buy_weapons()
                elif buy_choice == "Shields":
                    self.buy_shields()
                elif buy_choice == "Armor":
                    self.buy_armor()
                elif buy_choice == "Helmets":
                    self.buy_helmets()
                # Always restore main options after buy submenu (including ESC/Back)
                shop_screen.set_options(["Buy", "Sell", "Quests", "Leave"])
                shop_screen.shop_message = "Griswold's Blacksmith"
            elif choice == "Sell":
                self.sell_items()
            elif choice == "Quests":
                qm.check_and_offer("Griswold")

    def _offer_ultimate_weapon_crafting(self):
        """Offer the Unobtainium ultimate weapon craft through the pygame UI."""
        options = items_module.ultimate_weapon_options_for(self.player_char)
        intro = (
            "Oh my...can it possibly be?...the legendary ore...Unobtainium?\n\n"
            "I can't believe you have found it!\n\n"
            "It has been a lifelong dream of mine to forge a weapon from the mythical metal."
        )
        if not options:
            self.presenter.show_message(
                f"{intro}\n\n"
                "But I don't know how to forge a weapon your class can use. Come back if your path changes."
            )
            return

        selector = SelectionPopup(
            self.presenter,
            None,
            title="Ultimate Weapon",
            header_message="What type of weapon would you like me to make?",
            options=[typ for typ, _weapon in options] + ["Not Yet"],
        )
        result = selector.show(self.player_char)
        if result is None:
            return
        _kind, choice = result
        if choice in {None, "Not Yet"}:
            self.presenter.show_message(
                f"{intro}\n\nI am sorry to hear that...please come back if you change your mind."
            )
            return

        weapon_cls = dict(options).get(choice)
        if weapon_cls is None:
            return
        weapon = weapon_cls()
        self.player_char.modify_inventory(weapon)
        del self.player_char.special_inventory["Unobtainium"]
        self.presenter.show_message(
            f"{intro}\n\nGive me a moment and I will make you an ultimate weapon...\n\n"
            f"I present to you the mighty {weapon.name}!"
        )

    def visit_alchemist(self):
        """Visit the Alchemist - potions and consumables."""
        from .quest_manager import QuestManager

        # Use ShopScreen for the main interface
        shop_screen = ShopScreen(
            self.presenter, self.player_char, "Welcome to Ye Olde Item Shoppe."
        )
        self._active_shopkeeper_portrait = "Alchemist"
        self._set_shopkeeper_portrait(shop_screen)
        qm = QuestManager(
            self.presenter,
            self.player_char,
            quest_text_renderer=lambda text: shop_screen.display_quest_text(
                text, npc_name="Alchemist"
            ),
            renderer_preserve_formatting=True,
        )
        shop_screen.set_options(["Buy", "Sell", "Quests", "Leave"])

        while True:
            choice = shop_screen.navigate_options()

            if choice is None or choice == "Leave":
                popup = ConfirmationPopup(
                    self.presenter, "Good luck on your adventures!", show_buttons=False
                )
                popup.show(flush_events=True, require_key_release=True)
                break
            elif choice == "Buy":
                self.buy_alchemist_goods()
                shop_screen.shop_message = "Welcome to Ye Olde Item Shoppe."
            elif choice == "Sell":
                self.sell_items()
            elif choice == "Quests":
                qm.check_and_offer("Alchemist")

    def visit_jeweler(self):
        """Visit the Jeweler - rings and pendants."""
        if self.player_char.player_level() < 10:
            popup = ConfirmationPopup(
                self.presenter,
                "Sorry but the jeweler is currently closed. Try again later.",
                show_buttons=False,
            )
            popup.show(flush_events=True, require_key_release=True)
            return

        from .quest_manager import QuestManager

        # Use ShopScreen for the main interface
        shop_screen = ShopScreen(
            self.presenter, self.player_char, "Come glimpse the finest jewelry in the land."
        )
        self._active_shopkeeper_portrait = "Jeweler"
        self._set_shopkeeper_portrait(shop_screen)
        qm = QuestManager(
            self.presenter,
            self.player_char,
            quest_text_renderer=lambda text: shop_screen.display_quest_text(
                text, npc_name="Jeweler"
            ),
            renderer_preserve_formatting=True,
        )
        options = ["Buy", "Sell", "Quests", "Leave"]
        if dragoon.can_craft_draconite_pendant(self.player_char):
            options.insert(3, "Craft Draconite Pendant")
        shop_screen.set_options(options)

        while True:
            choice = shop_screen.navigate_options()

            if choice is None or choice == "Leave":
                popup = ConfirmationPopup(
                    self.presenter, "May fortune favor you!", show_buttons=False
                )
                popup.show(flush_events=True, require_key_release=True)
                break
            elif choice == "Buy":
                self.buy_jewelry()
                shop_screen.shop_message = "Come glimpse the finest jewelry in the land."
            elif choice == "Sell":
                self.sell_items()
            elif choice == "Quests":
                qm.check_and_offer("Jeweler")
            elif choice == "Craft Draconite Pendant":
                ok, message = dragoon.craft_draconite_pendant(self.player_char)
                self.presenter.show_message(message)
                options = ["Buy", "Sell", "Quests", "Leave"]
                if dragoon.can_craft_draconite_pendant(self.player_char):
                    options.insert(3, "Craft Draconite Pendant")
                shop_screen.set_options(options)

    def visit_magic_shop(self):
        """Visit the Magic Shop - scrolls and arcane implements."""
        if self.player_char.player_level() < self.MAGIC_SHOP_MIN_LEVEL:
            popup = ConfirmationPopup(
                self.presenter,
                "The Magic Shop is currently closed.",
                show_buttons=False,
            )
            popup.show(flush_events=True, require_key_release=True)
            return
        shop_screen = ShopScreen(self.presenter, self.player_char, self.MAGIC_SHOP_MESSAGE)
        self._active_shopkeeper_portrait = self.MAGIC_SHOPKEEPER
        self._set_shopkeeper_portrait(shop_screen)
        shop_screen.set_options(["Buy", "Sell", "Quests", "Leave"])

        while True:
            choice = shop_screen.navigate_options()

            if choice is None or choice == "Leave":
                popup = ConfirmationPopup(
                    self.presenter, "Mind the candles on your way out.", show_buttons=False
                )
                popup.show(flush_events=True, require_key_release=True)
                break
            elif choice == "Buy":
                self.buy_magic_shop_goods()
                shop_screen.shop_message = self.MAGIC_SHOP_MESSAGE
            elif choice == "Sell":
                self.sell_items()
            elif choice == "Quests":
                from .quest_manager import QuestManager

                qm = QuestManager(
                    self.presenter,
                    self.player_char,
                    quest_text_renderer=lambda text: shop_screen.display_quest_text(
                        text, npc_name=self.MAGIC_SHOPKEEPER
                    ),
                    renderer_preserve_formatting=True,
                )
                qm.check_and_offer(self.MAGIC_SHOPKEEPER)

    def buy_weapons(self):
        """Buy weapons - choose handedness first, then browse subtype tabs."""
        # Use ShopScreen for weapon type selection
        shop_screen = ShopScreen(self.presenter, self.player_char, "Choose weapon type")
        self._set_shopkeeper_portrait(shop_screen)
        shop_screen.set_options(["1-Handed", "2-Handed", "Back"])
        handed_choice = shop_screen.navigate_options()

        # Treat ESC ("Leave") the same as Back for submenus
        if handed_choice is None or handed_choice in ("Back", "Leave"):
            return

        handed = handed_choice
        weapon_groups = dict(items_module.items_dict["Weapon"][handed])
        if handed == "2-Handed":
            weapon_groups.pop("Staff", None)
        weapon_tabs = self._available_item_groups(weapon_groups)
        if not weapon_tabs:
            return

        self._buy_with_shop_screen(weapon_tabs, f"{handed} Weapons")

    def buy_shields(self):
        """Buy shields from blacksmith."""
        shield_list = items_module.items_dict["OffHand"]["Shield"]
        self.buy_equipment(
            shield_list,
            "Shield",
        )

    def buy_armor(self):
        """Buy armor from blacksmith with armor-type tabs."""
        armor_tabs = self._available_item_groups(items_module.items_dict["Armor"])
        if not armor_tabs:
            return

        self._buy_with_shop_screen(armor_tabs, "Armor")

    def buy_helmets(self):
        """Buy helmets from blacksmith with helmet-type tabs."""
        helmet_tabs = self._available_item_groups(items_module.items_dict["Helmet"])
        if not helmet_tabs:
            return

        self._buy_with_shop_screen(helmet_tabs, "Helmets")

    def buy_rings(self):
        """Buy rings from jeweler."""
        ring_list = items_module.items_dict["Accessory"]["Ring"]
        self.buy_equipment(
            ring_list,
            "Ring",
        )

    def buy_pendants(self):
        """Buy pendants from jeweler."""
        pendant_list = items_module.items_dict["Accessory"]["Pendant"]
        self.buy_equipment(
            pendant_list,
            "Pendant",
        )

    def buy_jewelry(self):
        """Buy rings and pendants from one tabbed jeweler browser."""
        jewelry_tabs = {
            "Rings": items_module.items_dict["Accessory"]["Ring"],
            "Pendants": items_module.items_dict["Accessory"]["Pendant"],
        }
        self._buy_with_shop_screen(jewelry_tabs, "Jewelry")

    def buy_scrolls(self, background_image="town.png"):
        """Buy scrolls from alchemist."""
        scroll_list = items_module.items_dict["Misc"]["Scroll"]
        self.buy_equipment(scroll_list, "Scroll", background_image=background_image)

    def buy_misc(self):
        """Buy misc items from alchemist (excluding scrolls)."""
        misc_dict = dict(items_module.items_dict.get("Misc", {}))
        if "Scroll" in misc_dict:
            misc_dict.pop("Scroll")
        if not misc_dict:
            return
        self._buy_with_shop_screen(
            self._available_item_groups(misc_dict),
            "Misc",
        )

    def buy_potions(self, background_image="town.png"):
        """Buy potions from alchemist with level-based availability."""
        potion_dict = {
            "Health Potions": self._health_potion_item_classes(),
            "Mana Potions": self._mana_potion_item_classes(),
            "Status Items": self._status_item_classes(),
        }
        self._buy_with_shop_screen(potion_dict, "Potions", background_image=background_image)

    def buy_alchemist_goods(self):
        """Buy alchemist stock from one tabbed browser."""
        alchemist_tabs = {
            "Health Potions": self._health_potion_item_classes(),
            "Mana Potions": self._mana_potion_item_classes(),
            "Status Items": self._status_item_classes(),
        }
        self._buy_with_shop_screen(alchemist_tabs, "Alchemist Goods")

    def buy_thieves_guild_goods(self):
        """Buy keys, blank scrolls, and miscellaneous contraband from the Thieves Guild."""
        misc_dict = dict(items_module.items_dict.get("Misc", {}))
        tools = list(misc_dict.get("Key", []))
        tools.extend(cls for cls in misc_dict.get("Scroll", []) if cls is items_module.BlankScroll)
        for label, item_classes in misc_dict.items():
            if label in {
                "Key",
                "Scroll",
                "Magic Tool",
                "Toxin Reagent",
                "Toxin",
                "Ammunition",
                "Crossbow Bolts",
            }:
                continue
            tools.extend(item_classes)
        guild_tabs = {"Tools": tools} if self._has_available_items(tools) else {}
        guild_tabs["Toxins"] = [items_module.MildToxin]
        guild_tabs["Ammunition"] = [items_module.ThrowingDaggers]
        guild_tabs["Crossbows"] = list(items_module.items_dict["OffHand"].get("Crossbow", []))
        guild_tabs["Crossbow Bolts"] = list(
            items_module.items_dict["Misc"].get("Crossbow Bolts", [])
        )
        self._buy_with_shop_screen(guild_tabs, "Thieves Guild Goods")

    def buy_magic_shop_goods(self):
        """Buy spell scrolls, staves, tomes, rods, and musical instruments."""
        spell_scrolls = [
            cls
            for cls in items_module.items_dict["Misc"].get("Scroll", [])
            if cls is not items_module.BlankScroll
        ]
        magic_tabs = {
            "Spell Scrolls": spell_scrolls,
            "Staves": items_module.items_dict["Weapon"]["2-Handed"].get("Staff", []),
            "Tomes": items_module.items_dict["OffHand"].get("Tome", []),
            "Rods": items_module.items_dict["OffHand"].get("Rod", []),
            "Musical Instruments": self._musical_instrument_item_classes(),
            "Magic Items": items_module.items_dict["Misc"].get("Magic Tool", []),
        }
        self._buy_with_shop_screen(
            {label: item_classes for label, item_classes in magic_tabs.items() if item_classes},
            "Magic Shop Goods",
        )

    def _status_item_classes(self):
        """Return status-curing consumable classes sold by alchemists."""
        return list(items_module.items_dict.get("Potion", {}).get("Status", []))

    def _health_potion_item_classes(self):
        """Return level-appropriate health potion classes."""
        potion_classes = [items_module.HealthPotion]
        player_level = self.player_char.player_level()
        if player_level >= 10:
            potion_classes.append(items_module.GreatHealthPotion)
        if player_level >= 30:
            potion_classes.append(items_module.SuperHealthPotion)
        return potion_classes

    def _mana_potion_item_classes(self):
        """Return level-appropriate mana potion classes."""
        potion_classes = [items_module.ManaPotion]
        player_level = self.player_char.player_level()
        if player_level >= 10:
            potion_classes.append(items_module.GreatManaPotion)
        if player_level >= 30:
            potion_classes.append(items_module.SuperManaPotion)
        return potion_classes

    def _potion_item_classes(self):
        """Return level-appropriate restorative potion classes."""
        return self._health_potion_item_classes() + self._mana_potion_item_classes()

    def _musical_instrument_item_classes(self):
        """Return musical instruments sold by the Magic Shop."""
        return [
            items_module.Lute,
            items_module.Mbira,
            items_module.Lyre,
            items_module.Tambourine,
            items_module.Accordina,
            items_module.Didgeridoo,
            items_module.Sitar,
            items_module.Bagpipes,
            items_module.Shamisen,
        ]

    def buy_equipment(self, item_list, category_name, background_image="town.png"):
        """Generic equipment buying interface using ShopScreen."""
        # Build item dictionary
        itemdict = {category_name: item_list}

        # Use the new shop screen
        self._buy_with_shop_screen(itemdict, category_name, background_image=background_image)

    def _buy_with_shop_screen(
        self,
        itemdict,
        category_name,
        background_image="town.png",
        *,
        ignore_rarity_filter: bool = False,
    ):
        """Use the new ShopScreen interface for buying items."""
        from .confirmation_popup import QuantityPopup

        if not itemdict:
            return

        shop_screen = ShopScreen(
            self.presenter,
            self.player_char,
            f"Buy {category_name}",
            background_image=background_image,
            options_list=[],
        )
        shop_screen.price_multiplier = self._active_price_multiplier
        shop_screen.ignore_rarity_filter = ignore_rarity_filter
        self._set_shopkeeper_portrait(shop_screen)
        shop_screen.update_item_list(itemdict, "Buy")

        # Create background function for popups
        def bg_func():
            return shop_screen.draw_all(do_flip=False)

        while True:
            result = shop_screen.navigate_items()

            # Result will be None if ESC was pressed (handled in navigate_items)
            if result is None:
                return

            display_str, item, cost, owned = result

            # Skip navigation items
            if display_str in ["Next Page"] or not item:
                continue

            # Use QuantityPopup for better quantity selection
            self.player_char.stats.strength * 10
            max_qty = min(self.player_char.gold // cost, 99) if cost > 0 else 99

            qty_popup = QuantityPopup(self.presenter, item.name, cost, max_qty)
            quantity = qty_popup.show(
                background_draw_func=bg_func,
                flush_events=True,
                require_key_release=True,
            )

            if quantity is None or quantity == 0:
                continue

            total_cost = cost * quantity

            if self.player_char.gold < total_cost:
                self.presenter.show_message(f"Not enough gold! Need {total_cost}g")
                # Update the shop screen to reflect current gold
                shop_screen.draw_all()
                continue

            equip_actions = self._equip_actions_for_purchase(item, quantity)

            # Purchase items
            self.player_char.gold -= total_cost
            if equip_actions:
                for _ in range(quantity):
                    self.player_char.modify_inventory(self._fresh_shop_item(item))
            else:
                self.player_char.modify_inventory(item, num=quantity)

            # Show transaction summary in popup
            summary_popup = ConfirmationPopup(
                self.presenter,
                f"Purchased {quantity}x {item.name}!\n\nGold remaining: {self.player_char.gold}",
                show_buttons=False,
            )
            summary_popup.show(
                background_draw_func=bg_func, flush_events=True, require_key_release=True
            )
            if equip_actions:
                self._offer_equip_after_buy(shop_screen, item, quantity, equip_actions)

            # Update item list to reflect new owned count
            shop_screen.update_item_list(itemdict, "Buy")

    @staticmethod
    def _fresh_shop_item(item):
        try:
            return item.__class__()
        except TypeError:
            return item

    @staticmethod
    def _slot_label(slot: str) -> str:
        return "Main Hand" if slot == "Weapon" else slot

    def _current_slot_item_name(self, slot: str) -> str:
        current = getattr(self.player_char, "equipment", {}).get(slot)
        if current is None or getattr(current, "subtyp", None) == "None":
            return "empty"
        return getattr(current, "name", "current item")

    def _equip_preview_lines(self, item, slots: tuple[str, ...]) -> list[str]:
        lines: list[str] = []
        for slot in slots:
            label = self._slot_label(slot)
            lines.append(f"{label}: replaces {self._current_slot_item_name(slot)}")
            equip_diff = getattr(self.player_char, "equip_diff", None)
            diff_lines: list[str] = []
            if not callable(equip_diff):
                lines.append("  no stat change")
                continue
            try:
                diff = equip_diff(item, slot, buy=True)
            except Exception:
                diff = ""
            for diff_line in str(diff or "").splitlines():
                if diff_line.strip():
                    diff_lines.append(f"  {diff_line.strip()}")
            if diff_lines:
                lines.extend(diff_lines)
            else:
                lines.append("  no stat change")
        return lines

    def _equip_prompt_header(self, item, quantity: int, actions: dict[str, tuple[str, ...]]) -> str:
        lines = [f"Purchased {quantity}x {item.name}. Equip now?"]
        if quantity > 1:
            lines.append("Cancel keeps every purchased item in inventory.")
        else:
            lines.append("Cancel keeps the purchased item in inventory.")
        for action, slots in actions.items():
            lines.append("")
            lines.append(f"{action}:")
            if action == "Dual Wield":
                lines.append("  uses 2 purchased copies")
            lines.extend(self._equip_preview_lines(item, slots))
        if (
            quantity < 2
            and "Main Hand" in actions
            and "OffHand" in actions
            and "Dual Wield" not in actions
        ):
            lines.append("")
            lines.append("Dual Wield: buy 2 copies to equip both hands.")
        return "\n".join(lines)

    def _equip_actions_for_purchase(self, item, quantity: int) -> dict[str, tuple[str, ...]]:
        slots = items_module.equipment_slots_for_item(item, self.player_char)
        actions: dict[str, tuple[str, ...]] = {}
        if not slots:
            return actions
        if getattr(item, "typ", None) == "Weapon":
            if "Weapon" in slots:
                actions["Main Hand"] = ("Weapon",)
            if "OffHand" in slots:
                actions["OffHand"] = ("OffHand",)
            if quantity >= 2 and "Weapon" in slots and "OffHand" in slots:
                actions["Dual Wield"] = ("Weapon", "OffHand")
            return actions
        actions["Equip Now"] = (slots[0],)
        return actions

    def _purchased_inventory_items(self, item, count: int) -> list:
        return list(getattr(self.player_char, "inventory", {}).get(item.name, []))[-count:]

    def _can_equip_purchase_slot(self, item, slot: str) -> bool:
        can_equip = getattr(self.player_char, "can_equip_item", None)
        if callable(can_equip):
            try:
                return bool(can_equip(item, slot))
            except Exception:
                return False
        equip_check = getattr(getattr(self.player_char, "cls", None), "equip_check", None)
        if not callable(equip_check):
            return False
        try:
            return bool(equip_check(item, slot))
        except Exception:
            return False

    def _can_equip_purchased_item(self, item, slots: tuple[str, ...]) -> bool:
        if len(self._purchased_inventory_items(item, len(slots))) < len(slots):
            return False
        return all(self._can_equip_purchase_slot(item, slot) for slot in slots)

    def _snapshot_equip_state(self) -> tuple[dict, dict]:
        equipment = getattr(self.player_char, "equipment", {})
        inventory = getattr(self.player_char, "inventory", {})
        return dict(equipment), {name: list(item_list) for name, item_list in inventory.items()}

    def _restore_equip_state(self, snapshot: tuple[dict, dict]) -> None:
        equipment_snapshot, inventory_snapshot = snapshot
        equipment = getattr(self.player_char, "equipment", None)
        inventory = getattr(self.player_char, "inventory", None)
        if isinstance(equipment, dict):
            equipment.clear()
            equipment.update(equipment_snapshot)
        else:
            self.player_char.equipment = dict(equipment_snapshot)
        if isinstance(inventory, dict):
            inventory.clear()
            inventory.update(
                {name: list(item_list) for name, item_list in inventory_snapshot.items()}
            )
        else:
            self.player_char.inventory = {
                name: list(item_list) for name, item_list in inventory_snapshot.items()
            }

    def _equip_purchased_item(self, item, slots: tuple[str, ...]) -> bool:
        if not self._can_equip_purchased_item(item, slots):
            return False
        purchased = self._purchased_inventory_items(item, len(slots))
        snapshot = self._snapshot_equip_state()
        for slot, purchased_item in zip(slots, purchased):
            equip_method = getattr(self.player_char, "equip", None)
            if not callable(equip_method):
                self._restore_equip_state(snapshot)
                return False
            try:
                equipped = equip_method(slot, purchased_item)
            except Exception:
                self._restore_equip_state(snapshot)
                return False
            if equipped is False:
                self._restore_equip_state(snapshot)
                return False
        return True

    def _offer_equip_after_buy(self, shop_screen, item, quantity: int, actions=None) -> None:
        actions = actions or self._equip_actions_for_purchase(item, quantity)
        if not actions:
            return
        options = list(actions) + ["Cancel"]
        popup = SelectionPopup(
            self.presenter,
            shop_screen,
            title=f"Equip {item.name}?",
            header_message=self._equip_prompt_header(item, quantity, actions),
            options=options,
        )
        result = popup.show(self.player_char, flush_events=True, require_key_release=True)
        if not result or result[0] != "selection":
            return
        action = result[1]
        if action == "Cancel":
            return
        slots = actions.get(action)
        if not slots:
            return
        if self._equip_purchased_item(item, slots):
            slot_text = " and ".join(self._slot_label(slot) for slot in slots)
            ConfirmationPopup(
                self.presenter,
                f"Equipped {item.name} to {slot_text}.",
                show_buttons=False,
            ).show(
                background_draw_func=lambda: shop_screen.draw_all(do_flip=False),
                flush_events=True,
                require_key_release=True,
            )
        else:
            ConfirmationPopup(
                self.presenter,
                f"Could not equip {item.name}. It remains in inventory.",
                show_buttons=False,
            ).show(
                background_draw_func=lambda: shop_screen.draw_all(do_flip=False),
                flush_events=True,
                require_key_release=True,
            )

    def _available_item_groups(self, itemdict):
        """Return item groups that have at least one item available to this player."""
        return {
            subtype: item_list
            for subtype, item_list in itemdict.items()
            if self._has_available_items(item_list)
        }

    def _format_item_info(self, item):
        """Format item information with description and stat comparison."""
        info_lines = []

        # Item name and type
        info_lines.append(f"Type: {item.typ}")
        themed_name = items_module.stat_themed_item_name(item)
        if themed_name != item.name:
            info_lines.append(f"Theme Name: {themed_name}")
        if hasattr(item, "subtyp"):
            info_lines.append(f"Subtype: {item.subtyp}")
        info_lines.extend(items_module.item_metadata_lines(item))

        # Item stats
        info_lines.append("")
        if hasattr(item, "damage") and item.damage > 0:
            info_lines.append(f"Damage: {item.damage}")
        if hasattr(item, "armor") and item.armor > 0:
            info_lines.append(f"Armor: {item.armor}")
        if hasattr(item, "magic") and item.magic != 0:
            info_lines.append(f"Magic: {item.magic:+d}")
        if hasattr(item, "magic_defense") and item.magic_defense != 0:
            info_lines.append(f"Magic Defense: {item.magic_defense:+d}")

        # Description
        if item.description:
            info_lines.append("")
            # Word wrap the description
            words = item.description.split()
            current_line = []
            for word in words:
                current_line.append(word)
                line = " ".join(current_line)
                if len(line) > 50:
                    current_line.pop()
                    info_lines.append(" ".join(current_line))
                    current_line = [word]
            if current_line:
                info_lines.append(" ".join(current_line))

        # Value
        info_lines.append("")
        info_lines.append(f"Value: {item.value}g")

        # Equipment comparison for equipment items
        if item.typ in ["Weapon", "OffHand", "Armor", "Helmet", "Accessory"]:
            dual_slot_lines = self._dual_wield_comparison_lines(item)
            if dual_slot_lines:
                info_lines.append("")
                info_lines.extend(dual_slot_lines)
                return "\n".join(info_lines)

            equip_slot = item.typ
            if item.typ == "Accessory":
                equip_slot = item.subtyp

            # Get current equipped item
            current_item = self.player_char.equipment.get(equip_slot)

            if current_item and current_item.name != "None":
                info_lines.append("")
                info_lines.append("=== Currently Equipped ===")
                info_lines.append(f"{current_item.name}")

                # Show stat comparison
                stat_diff = self.player_char.equip_diff(item, equip_slot, buy=True)

                if stat_diff:
                    info_lines.append("")
                    info_lines.append("=== If Equipped ===")
                    for line in stat_diff.splitlines():
                        if line.strip():
                            # Parse the stat difference
                            parts = line.split("  ")
                            if len(parts) >= 2:
                                stat_name = parts[0].strip()
                                stat_value = parts[1].strip()
                                # Add color indicator
                                if stat_value.startswith("+"):
                                    indicator = "(Better)"
                                elif stat_value.startswith("-"):
                                    indicator = "(Worse)"
                                else:
                                    indicator = ""
                                info_lines.append(f"{stat_name}: {stat_value} {indicator}".strip())
            else:
                info_lines.append("")
                info_lines.append(f"(No {equip_slot} currently equipped)")

        return "\n".join(info_lines)

    def _dual_wield_comparison_lines(self, item) -> list[str]:
        """Return explicit main/offhand shop comparison lines for hand items."""
        if getattr(item, "typ", None) not in {"Weapon", "OffHand"}:
            return []

        lines = ["=== Hand Comparison ==="]
        for label, slot in (("Main Hand", "Weapon"), ("OffHand", "OffHand")):
            lines.append(f"{label}:")
            if slot not in items_module.equipment_slots_for_item(item):
                lines.append("  not usable in this slot")
                continue
            can_equip = getattr(self.player_char, "can_equip_item", None)
            if callable(can_equip):
                slot_allowed = can_equip(item, slot)
            else:
                equip_check = getattr(getattr(self.player_char, "cls", None), "equip_check", None)
                slot_allowed = bool(callable(equip_check) and equip_check(item, slot))
            if not slot_allowed:
                lines.append("  not usable by this character")
                continue
            current_item = self.player_char.equipment.get(slot)
            current_name = getattr(current_item, "name", "empty")
            if current_name == "None":
                current_name = "empty"
            lines.append(f"  replaces {current_name}")
            stat_diff = self.player_char.equip_diff(item, slot, buy=True)
            diff_lines = [line.strip() for line in stat_diff.splitlines() if line.strip()]
            if diff_lines:
                lines.extend(f"  {line}" for line in diff_lines)
            else:
                lines.append("  no stat change")
        return lines

    def _has_available_items(self, item_classes):
        """Check if any items in the given list are available at the player's level."""
        player_level = self.player_char.player_level()

        for item_class in item_classes:
            item = item_class()

            # Check level restrictions
            if hasattr(item, "restriction") and item.restriction:
                try:
                    if player_level < min(item.restriction):
                        continue
                except (TypeError, ValueError):
                    # Restriction contains non-numeric values (e.g., class names like "Ninja")
                    # Skip items with class restrictions
                    continue

            # Check rarity for town shops
            if self.player_char.in_town():
                min_rarity = max(0.4, (1.0 - (0.02 * player_level)))
                if item.rarity < min_rarity:
                    continue

            # If we get here, the item is available
            return True

        # No available items found
        return False

    def sell_items(self, background_image="town.png"):
        """Sell items from inventory using ShopScreen."""
        # Create background function for popups
        bg_func = None
        if background_image != "town.png":
            # For non-town shops, we'll set up bg_func after creating shop_screen
            pass

        if not self.player_char.inventory:
            popup = ConfirmationPopup(
                self.presenter, "You have nothing to sell!", show_buttons=False
            )
            popup.show(
                background_draw_func=bg_func if bg_func else None,
                flush_events=True,
                require_key_release=True,
            )
            return

        # Create ShopScreen once outside the loop to preserve cursor position
        shop_screen = ShopScreen(
            self.presenter,
            self.player_char,
            "Sell Items",
            background_image=background_image,
            options_list=[],
        )

        # Now set up background function for popups if using custom background
        if background_image != "town.png":

            def bg_func():
                return shop_screen.draw_all(do_flip=False)

        while True:
            # Build sellable inventory (exclude ultimate items)
            sellable = {}
            for name, items_list in self.player_char.inventory.items():
                if items_list and not items_list[0].ultimate:
                    sellable[name] = items_list

            if not sellable:
                # Capture current shop background to avoid flicker
                shop_screen.draw_all(do_flip=False)
                popup = ConfirmationPopup(
                    self.presenter, "You have no items to sell.", show_buttons=False
                )
                popup.show(
                    background_draw_func=bg_func if bg_func else None,
                    flush_events=True,
                    require_key_release=True,
                )
                return

            # Update the item list (preserves cursor position)
            shop_screen.update_item_list(sellable, "Sell")

            result = shop_screen.navigate_items()

            # Result will be None if ESC was pressed
            if result is None:
                return

            display_str, item, sell_price, count = result

            # Skip navigation items or items without data
            if display_str in ["Next Page"] or not item:
                continue

            # Use QuantityPopup for sell quantity selection
            from .confirmation_popup import QuantityPopup

            shop_screen.draw_all(do_flip=False)
            qty_popup = QuantityPopup(
                self.presenter, item.name, sell_price, count, action="sell", default_quantity=count
            )
            quantity = qty_popup.show(
                background_draw_func=bg_func if bg_func else None,
                flush_events=True,
                require_key_release=True,
            )

            if quantity is None or quantity == 0:
                continue

            total_gold = sell_price * quantity

            # Confirm sale via popup
            # Capture current shop screen as background to avoid flicker
            shop_screen.draw_all(do_flip=False)
            confirm_popup = ConfirmationPopup(
                self.presenter, f"Sell {quantity}x {item.name} for {total_gold}g?"
            )
            confirm = confirm_popup.show(
                background_draw_func=bg_func if bg_func else None,
                flush_events=True,
                require_key_release=True,
            )

            if confirm:
                self.player_char.gold += total_gold
                self.player_char.modify_inventory(item, num=quantity, subtract=True)

                # Show transaction summary in popup using captured background
                shop_screen.draw_all(do_flip=False)
                summary_popup = ConfirmationPopup(
                    self.presenter,
                    f"Sold {quantity}x {item.name} for {total_gold}g!\n\nGold: {self.player_char.gold}",
                    show_buttons=False,
                )
                summary_popup.show(
                    background_draw_func=bg_func if bg_func else None,
                    flush_events=True,
                    require_key_release=True,
                )
                # Continue selling (will reload inventory)
            else:
                # Continue browsing
                pass

    def visit_secret_shop(self):
        """Visit the secret shop in the dungeon - sells everything."""
        # Use ShopScreen with dungeon background
        shop_screen = ShopScreen(
            self.presenter,
            self.player_char,
            "Secret Shop - Rare Goods for Sale",
            background_image="dungeon.png",
        )
        shop_screen.set_options(["Buy", "Sell", "Leave"])

        # Create background function for popups
        def bg_func():
            return shop_screen.draw_all(do_flip=False)

        while True:
            choice = shop_screen.navigate_options()

            if choice is None or choice == "Leave":
                popup = ConfirmationPopup(self.presenter, "Come back anytime!", show_buttons=False)
                popup.show(
                    background_draw_func=bg_func, flush_events=True, require_key_release=True
                )
                break
            elif choice == "Buy":
                # Show buy submenu
                shop_screen.set_options(
                    [
                        "Weapons",
                        "Shields & Tomes",
                        "Armor",
                        "Helmets",
                        "Accessories",
                        "Potions & Scrolls",
                        "Back",
                    ]
                )
                buy_choice = shop_screen.navigate_options()

                if buy_choice == "Weapons":
                    self._buy_secret_weapons(shop_screen)
                elif buy_choice == "Shields & Tomes":
                    self._buy_secret_offhand(shop_screen)
                elif buy_choice == "Armor":
                    self._buy_secret_armor(shop_screen)
                elif buy_choice == "Helmets":
                    self._buy_secret_helmets(shop_screen)
                elif buy_choice == "Accessories":
                    self._buy_secret_accessories(shop_screen)
                elif buy_choice == "Potions & Scrolls":
                    self._buy_secret_consumables(shop_screen)

                # Restore main menu
                shop_screen.set_options(["Buy", "Sell", "Leave"])
                shop_screen.shop_message = "Secret Shop - Rare Goods for Sale"
            elif choice == "Sell":
                self.sell_items(background_image="dungeon.png")
                # Restore shop message after selling
                shop_screen.shop_message = "Secret Shop - Rare Goods for Sale"

    def _buy_secret_weapons(self, shop_screen):
        """Buy weapons from secret shop."""
        # Use shop screen for weapon type selection
        shop_screen.shop_message = "Choose weapon type"
        shop_screen.set_options(["1-Handed", "2-Handed", "Back"])

        handed_choice = shop_screen.navigate_options()

        if handed_choice is None or handed_choice == "Back":
            return

        handed = handed_choice
        weapon_tabs = self._available_item_groups(items_module.items_dict["Weapon"][handed])
        if not weapon_tabs:
            return

        self._buy_with_shop_screen(weapon_tabs, f"{handed} Weapons", background_image="dungeon.png")

    def _buy_secret_offhand(self, shop_screen):
        """Buy shields, tomes, and rods from secret shop."""
        offhand_tabs = {
            "Shields": items_module.items_dict["OffHand"]["Shield"],
            "Tomes": items_module.items_dict["OffHand"]["Tome"],
            "Rods": items_module.items_dict["OffHand"]["Rod"],
        }
        self._buy_with_shop_screen(
            self._available_item_groups(offhand_tabs), "Off-Hand", background_image="dungeon.png"
        )

    def _buy_secret_armor(self, shop_screen):
        """Buy armor from secret shop."""
        armor_tabs = self._available_item_groups(items_module.items_dict["Armor"])
        self._buy_with_shop_screen(armor_tabs, "Armor", background_image="dungeon.png")

    def _buy_secret_helmets(self, shop_screen):
        """Buy helmets from secret shop."""
        helmet_tabs = self._available_item_groups(items_module.items_dict["Helmet"])
        self._buy_with_shop_screen(helmet_tabs, "Helmets", background_image="dungeon.png")

    def _buy_secret_accessories(self, shop_screen):
        """Buy accessories from secret shop."""
        accessory_tabs = {
            "Rings": items_module.items_dict["Accessory"]["Ring"],
            "Pendants": items_module.items_dict["Accessory"]["Pendant"],
        }
        self._buy_with_shop_screen(
            self._available_item_groups(accessory_tabs),
            "Accessories",
            background_image="dungeon.png",
        )

    def _buy_secret_consumables(self, shop_screen):
        """Buy potions and scrolls from secret shop."""
        consumable_tabs = {
            "Potions": self._potion_item_classes(),
            "Status Items": self._status_item_classes(),
            "Stat Potions": items_module.items_dict["Potion"].get("Stat", []),
            "Scrolls": items_module.items_dict["Misc"].get("Scroll", []),
            "Keys": items_module.items_dict.get("Misc", {}).get("Key", []),
        }
        self._buy_with_shop_screen(
            self._available_item_groups(consumable_tabs),
            "Consumables",
            background_image="dungeon.png",
        )

    def _buy_secret_stat_potions(self):
        """Buy stat potions from secret shop."""
        stat_potions = items_module.items_dict["Potion"].get("Stat", [])
        if not stat_potions:
            return
        self.buy_equipment(stat_potions, "Stat Potions", background_image="dungeon.png")

    def _buy_secret_keys(self):
        """Buy key items from secret shop."""
        key_items = items_module.items_dict.get("Misc", {}).get("Key", [])
        if not key_items:
            return
        self.buy_equipment(key_items, "Keys", background_image="dungeon.png")
