"""
Character creation screen for class selection.
"""

import pygame

from src.ui_pygame.screen_runtime import get_events

from .input_guards import (
    prepare_guarded_input,
    release_guard_allows_input,
    update_input_armed_from_event,
)
from .menu_layout import menu_unit, touch_target_height
from .mouse_helpers import hit_index, is_left_click, mouse_position

# Mapping of base classes to their available first-tier promotions
# This defines the class progression paths
PROMOTION_PATHS = {
    "Warrior": ["Weapon Master", "Paladin", "Lancer", "Sentinel"],
    "Mage": ["Sorcerer", "Warlock", "Spellblade", "Conjurer"],
    "Footpad": ["Thief", "Inquisitor", "Assassin", "Spell Stealer"],
    "Healer": ["Cleric", "Priest", "Monk", "Bard"],
    "Pathfinder": ["Druid", "Diviner", "Shaman", "Ranger"],
}


class ClassSelectionScreen:
    """
    Class selection screen with class details and filtered list.
    Left panel: Class information (description, stats, equipment restrictions, promotions)
    Right panel: List of available classes for the selected race
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
        self.DARK_GRAY = (64, 64, 64)
        self.BORDER_COLOR = (200, 200, 200)
        self.HIGHLIGHT_BG = (60, 60, 80)

        # Fonts
        self.title_font = presenter.title_font
        self.normal_font = presenter.normal_font
        self.small_font = presenter.small_font

        # State
        self.current_selection = 0
        self.available_classes = []
        self.class_data = {}
        self.race_name = ""
        self.race_instance = None

        # Calculate window positions
        self.calculate_window_rects()

    def option_rects(self, options: list[str] | None = None) -> list[pygame.Rect]:
        """Return clickable rectangles for visible class rows."""
        options = options if options is not None else self.available_classes
        line_height = touch_target_height(self.presenter)
        return [
            pygame.Rect(
                self.list_rect.left + menu_unit(self.presenter, 5),
                self.list_rect.top + menu_unit(self.presenter, 20) + i * line_height,
                self.list_rect.width - menu_unit(self.presenter, 10),
                line_height,
            )
            for i, _option in enumerate(options[:10])
        ]

    def calculate_window_rects(self):
        """Calculate the rectangles for each UI section."""
        # Top header
        header_height = self.height // 12
        self.header_rect = pygame.Rect(0, 0, self.width, header_height)

        # Left panel: Class details
        left_width = self.width // 2
        left_height = self.height - header_height
        self.details_rect = pygame.Rect(0, header_height, left_width, left_height)

        # Right panel: Class list
        right_width = self.width // 2
        right_height = self.height - header_height
        self.list_rect = pygame.Rect(left_width, header_height, right_width, right_height)

    def draw_header(self):
        """Draw the header with title."""
        pygame.draw.rect(self.screen, self.BLACK, self.header_rect)
        pygame.draw.rect(self.screen, self.BORDER_COLOR, self.header_rect, 2)

        title = self.normal_font.render(
            f"Select the class for your {self.race_name} character", True, self.GOLD
        )
        title_rect = title.get_rect(centerx=self.width // 2, centery=self.header_rect.centery)
        self.screen.blit(title, title_rect)

    def draw_class_details(self):
        """Draw the detailed class information panel."""
        pygame.draw.rect(self.screen, self.BLACK, self.details_rect)
        pygame.draw.rect(self.screen, self.BORDER_COLOR, self.details_rect, 2)

        if not self.available_classes or self.current_selection >= len(self.available_classes):
            return

        class_name = self.available_classes[self.current_selection]
        class_info = self.class_data[class_name]

        x = self.details_rect.left + 20
        line_height = 18

        # Fixed Y positions for consistent layout
        name_y = self.details_rect.top + 20
        desc_y = name_y + 35
        stats_y = self.details_rect.top + 175
        equip_y = self.details_rect.top + 350
        promo_y = self.details_rect.top + 500

        # Class name as title
        name_text = self.normal_font.render(class_name, True, self.GOLD)
        self.screen.blit(name_text, (x, name_y))

        # Description (limit lines to avoid pushing sections)
        if "description" in class_info:
            desc_lines = class_info["description"].split("\n")
            y_desc = desc_y
            max_desc_lines = 5
            line_count = 0
            for line in desc_lines:
                if line.strip() and line_count < max_desc_lines:
                    text = self.small_font.render(line, True, self.WHITE)
                    self.screen.blit(text, (x, y_desc))
                    y_desc += line_height
                    line_count += 1

        # Starting Stats section (fixed position)
        if "stats" in class_info:
            stats_header = self.small_font.render("Starting Stats", True, self.GOLD)
            self.screen.blit(stats_header, (x, stats_y))

            stats = class_info["stats"]

            col1_x = x
            col2_x = x + 180
            col1_y = stats_y + line_height + 5
            col2_y = stats_y + line_height + 5

            col1_stats = [
                ("strength", "Strength"),
                ("intelligence", "Intelligence"),
                ("wisdom", "Wisdom"),
                ("constitution", "Constitution"),
                ("charisma", "Charisma"),
                ("dexterity", "Dexterity"),
            ]
            for stat_key, stat_label in col1_stats:
                if stat_key in stats:
                    stat_val = stats[stat_key]["base"]
                    bonus = stats[stat_key]["bonus"]
                    display = f"{stat_val}(+{bonus})" if bonus >= 0 else f"{stat_val}({bonus})"
                    label_text = self.small_font.render(stat_label, True, self.WHITE)
                    value_text = self.small_font.render(display, True, self.WHITE)
                    self.screen.blit(label_text, (col1_x, col1_y))
                    self.screen.blit(value_text, (col1_x + 120, col1_y))
                    col1_y += line_height - 2

            col2_stats = [
                ("health", "Health"),
                ("mana", "Mana"),
                ("attack", "Attack"),
                ("defense", "Defense"),
                ("magic", "Magic"),
                ("magic_defense", "Magic Defense"),
            ]
            for stat_key, stat_label in col2_stats:
                if stat_key in stats:
                    stat_val = stats[stat_key]["base"]
                    bonus = stats[stat_key]["bonus"]
                    display = f"{stat_val}(+{bonus})" if bonus >= 0 else f"{stat_val}({bonus})"
                    label_text = self.small_font.render(stat_label, True, self.WHITE)
                    value_text = self.small_font.render(display, True, self.WHITE)
                    self.screen.blit(label_text, (col2_x, col2_y))
                    self.screen.blit(value_text, (col2_x + 120, col2_y))
                    col2_y += line_height - 2

        # Equipment Restrictions section (fixed position)
        if "equipment_restrictions" in class_info:
            equip_header = self.small_font.render("Equipment Restrictions", True, self.GOLD)
            self.screen.blit(equip_header, (x, equip_y))
            y_equip = equip_y + line_height + 5
            restrictions = class_info["equipment_restrictions"]
            for equip_type, allowed_types in restrictions.items():
                if allowed_types:
                    types_str = ", ".join(allowed_types)
                    equip_text = self.small_font.render(
                        f"{equip_type.capitalize()}: {types_str}", True, self.WHITE
                    )
                    self.screen.blit(equip_text, (x, y_equip))
                    y_equip += line_height

        # Available Promotions section (fixed position)
        if "promotions" in class_info and class_info["promotions"]:
            promo_header = self.small_font.render("Available Promotions", True, self.GOLD)
            self.screen.blit(promo_header, (x, promo_y))
            y_promo = promo_y + line_height + 5
            promo_str = ", ".join(class_info["promotions"])
            words = promo_str.split(", ")
            current_line = []
            for word in words:
                current_line.append(word)
                line = ", ".join(current_line)
                line_width = self.small_font.size(line)[0]
                if line_width > self.details_rect.width - 60:
                    current_line.pop()
                    line = ", ".join(current_line)
                    text = self.small_font.render(line, True, self.WHITE)
                    self.screen.blit(text, (x, y_promo))
                    y_promo += line_height
                    current_line = [word]
            if current_line:
                line = ", ".join(current_line)
                text = self.small_font.render(line, True, self.WHITE)
                self.screen.blit(text, (x, y_promo))

    def draw_class_list(self):
        """Draw the class list panel."""
        pygame.draw.rect(self.screen, self.BLACK, self.list_rect)
        pygame.draw.rect(self.screen, self.BORDER_COLOR, self.list_rect, 2)

        if not self.available_classes:
            no_classes = self.normal_font.render("No classes available", True, self.GRAY)
            no_classes_rect = no_classes.get_rect(
                centerx=self.list_rect.centerx, centery=self.list_rect.centery
            )
            self.screen.blit(no_classes, no_classes_rect)
            return

        # Draw class list
        x = self.list_rect.left + menu_unit(self.presenter, 20)

        max_visible = 10
        option_rects = self.option_rects()
        for i, class_name in enumerate(self.available_classes[:max_visible]):
            y = option_rects[i].centery

            # Highlight selected
            if i == self.current_selection:
                highlight_rect = option_rects[i]
                pygame.draw.rect(self.screen, self.HIGHLIGHT_BG, highlight_rect)
                pygame.draw.rect(self.screen, self.GOLD, highlight_rect, 1)
                color = self.GOLD
            else:
                color = self.WHITE

            text = self.normal_font.render(class_name, True, color)
            self.screen.blit(text, text.get_rect(left=x, centery=y))

    def draw_all(self):
        """Draw all UI elements."""
        self.screen.fill(self.BLACK)
        self.draw_header()
        self.draw_class_details()
        self.draw_class_list()
        pygame.display.flip()

    def set_classes(self, race_name, race_instance, classes_dict):
        """
        Set available classes for the selected race.

        Args:
            race_name: Name of the selected race
            race_instance: Instance of the race class
            classes_dict: Dictionary of class_name -> class_info
        """
        self.race_name = race_name
        self.race_instance = race_instance
        self.available_classes = []
        self.class_data = {}
        self.current_selection = 0

        # Get available classes for this race from cls_res['Base']
        available_for_race = []
        if hasattr(race_instance, "cls_res"):
            available_for_race = race_instance.cls_res.get("Base", [])

        for class_name, class_info_dict in classes_dict.items():
            # Check if this class is available for this race
            if available_for_race and class_name not in available_for_race:
                continue

            self.available_classes.append(class_name)

            # Extract class information
            class_obj = class_info_dict.get("class")
            if not class_obj:
                continue

            class_instance = class_obj()
            class_detail = {
                "name": class_name,
            }

            # Get description
            if hasattr(class_instance, "description"):
                class_detail["description"] = class_instance.description

            # Get stats with bonuses
            class_detail["stats"] = {
                "strength": {
                    "base": getattr(race_instance, "strength", 10)
                    + getattr(class_instance, "str_plus", 0),
                    "bonus": getattr(class_instance, "str_plus", 0),
                },
                "intelligence": {
                    "base": getattr(race_instance, "intel", 10)
                    + getattr(class_instance, "int_plus", 0),
                    "bonus": getattr(class_instance, "int_plus", 0),
                },
                "wisdom": {
                    "base": getattr(race_instance, "wisdom", 10)
                    + getattr(class_instance, "wis_plus", 0),
                    "bonus": getattr(class_instance, "wis_plus", 0),
                },
                "constitution": {
                    "base": getattr(race_instance, "con", 10)
                    + getattr(class_instance, "con_plus", 0),
                    "bonus": getattr(class_instance, "con_plus", 0),
                },
                "charisma": {
                    "base": getattr(race_instance, "charisma", 10)
                    + getattr(class_instance, "cha_plus", 0),
                    "bonus": getattr(class_instance, "cha_plus", 0),
                },
                "dexterity": {
                    "base": getattr(race_instance, "dex", 10)
                    + getattr(class_instance, "dex_plus", 0),
                    "bonus": getattr(class_instance, "dex_plus", 0),
                },
                "health": {
                    "base": (
                        getattr(race_instance, "con", 10) + getattr(class_instance, "con_plus", 0)
                    )
                    * 2,
                    "bonus": getattr(class_instance, "con_plus", 0) * 2,
                },
                "mana": {
                    "base": (
                        getattr(race_instance, "intel", 10) + getattr(class_instance, "int_plus", 0)
                    )
                    * 2,
                    "bonus": getattr(class_instance, "int_plus", 0) * 2,
                },
                "attack": {
                    "base": getattr(race_instance, "base_attack", 1)
                    + getattr(class_instance, "att_plus", 0),
                    "bonus": getattr(class_instance, "att_plus", 0),
                },
                "defense": {
                    "base": getattr(race_instance, "base_defense", 1)
                    + getattr(class_instance, "def_plus", 0),
                    "bonus": getattr(class_instance, "def_plus", 0),
                },
                "magic": {
                    "base": getattr(race_instance, "base_magic", 1)
                    + getattr(class_instance, "magic_plus", 0),
                    "bonus": getattr(class_instance, "magic_plus", 0),
                },
                "magic_defense": {
                    "base": getattr(race_instance, "base_magic_def", 1)
                    + getattr(class_instance, "magic_def_plus", 0),
                    "bonus": getattr(class_instance, "magic_def_plus", 0),
                },
            }

            # Get equipment restrictions
            class_detail["equipment_restrictions"] = {}
            if hasattr(class_instance, "restrictions"):
                class_detail["equipment_restrictions"] = class_instance.restrictions

            # Get available promotions from PROMOTION_PATHS, filtered by what this race has
            class_detail["promotions"] = []
            if class_name in PROMOTION_PATHS:
                # Get promotions available for this base class
                base_promotions = PROMOTION_PATHS[class_name]
                # Filter to only those available for this race
                available_first_tier = race_instance.cls_res.get("First", [])
                class_detail["promotions"] = [
                    p for p in base_promotions if p in available_first_tier
                ]

            self.class_data[class_name] = class_detail

    def navigate(
        self,
        race_name,
        race_instance,
        classes_dict,
        flush_events: bool = False,
        require_key_release: bool = False,
    ):
        """
        Navigate class selection and return selected class name.

        Args:
            race_name: Name of the selected race
            race_instance: Instance of the race class
            classes_dict: Dictionary of class_name -> class_info

        Returns:
            str: Selected class name, or None if cancelled
        """
        self.set_classes(race_name, race_instance, classes_dict)

        if not self.available_classes:
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
                hovered = hit_index(self.option_rects(), mouse_position(event))
                if hovered is not None and event.type == pygame.MOUSEMOTION:
                    self.current_selection = hovered
                elif hovered is not None and is_left_click(event):
                    if input_armed:
                        self.current_selection = hovered
                        return self.available_classes[self.current_selection]
                if event.type == pygame.KEYDOWN:
                    if not input_armed:
                        continue
                    if event.key == pygame.K_UP:
                        self.current_selection = (self.current_selection - 1) % len(
                            self.available_classes
                        )
                    elif event.key == pygame.K_DOWN:
                        self.current_selection = (self.current_selection + 1) % len(
                            self.available_classes
                        )
                    elif event.key == pygame.K_RETURN or event.key == pygame.K_SPACE:
                        return self.available_classes[self.current_selection]
                    elif event.key == pygame.K_ESCAPE:
                        return None

            self.presenter.clock.tick(30)
