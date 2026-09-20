"""
Character creation screen for race selection.
"""

import pygame

from .input_guards import (
    prepare_guarded_input,
    release_guard_allows_input,
    update_input_armed_from_event,
)
from .menu_layout import menu_unit, touch_target_height
from .mouse_helpers import hit_index, is_left_click, mouse_position


class RaceSelectionScreen:
    """
    Race selection screen with race details and list.
    Left panel: Race information (description, stats, resistances, classes)
    Right panel: List of available races
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
        self.races = []
        self.race_data = {}

        # Calculate window positions
        self.calculate_window_rects()

    def option_rects(self, options: list[str] | None = None) -> list[pygame.Rect]:
        """Return clickable rectangles for visible race rows."""
        options = options if options is not None else self.races
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

        # Left panel: Race details
        left_width = self.width // 2
        left_height = self.height - header_height
        self.details_rect = pygame.Rect(0, header_height, left_width, left_height)

        # Right panel: Race list
        right_width = self.width // 2
        right_height = self.height - header_height
        self.list_rect = pygame.Rect(left_width, header_height, right_width, right_height)

    def draw_header(self):
        """Draw the header with title."""
        pygame.draw.rect(self.screen, self.BLACK, self.header_rect)
        pygame.draw.rect(self.screen, self.BORDER_COLOR, self.header_rect, 2)

        title = self.normal_font.render("Select the race for your character", True, self.GOLD)
        title_rect = title.get_rect(centerx=self.width // 2, centery=self.header_rect.centery)
        self.screen.blit(title, title_rect)

    def draw_race_details(self):
        """Draw the detailed race information panel."""
        pygame.draw.rect(self.screen, self.BLACK, self.details_rect)
        pygame.draw.rect(self.screen, self.BORDER_COLOR, self.details_rect, 2)

        if not self.races or self.current_selection >= len(self.races):
            return

        race_name = self.races[self.current_selection]
        race = self.race_data[race_name]

        x = self.details_rect.left + 20
        line_height = 18

        # Fixed Y positions for each section
        name_y = self.details_rect.top + 20
        desc_y = name_y + 35
        stats_y = self.details_rect.top + 175  # Fixed position
        resist_y = self.details_rect.top + 350  # Fixed position
        classes_y = self.details_rect.top + 500  # Fixed position

        # Race name as title
        name_text = self.normal_font.render(race_name, True, self.GOLD)
        self.screen.blit(name_text, (x, name_y))

        # Description (limited to fixed height)
        if "description" in race:
            desc_lines = race["description"].split("\n")
            y = desc_y
            max_desc_lines = 5  # Limit description to 5 lines
            line_count = 0
            for line in desc_lines:
                if line.strip() and line_count < max_desc_lines:
                    text = self.small_font.render(line, True, self.WHITE)
                    self.screen.blit(text, (x, y))
                    y += line_height
                    line_count += 1

        # Base Stats section (fixed position)
        if "stats" in race:
            stats_header = self.small_font.render("Base Stats", True, self.GOLD)
            self.screen.blit(stats_header, (x, stats_y))

            stats = race["stats"]

            # Two columns of stats with fixed pixel positions for alignment
            col1_x = x
            col2_x = x + 180  # Fixed position for second column
            col1_y = stats_y + line_height + 5
            col2_y = stats_y + line_height + 5

            # Left column - base attributes
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
                    # Render label and value at fixed positions
                    label_text = self.small_font.render(stat_label, True, self.WHITE)
                    self.screen.blit(label_text, (col1_x, col1_y))

                    value_text = self.small_font.render(str(stats[stat_key]), True, self.WHITE)
                    self.screen.blit(value_text, (col1_x + 120, col1_y))

                    col1_y += line_height - 2

            # Right column - combat stats
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
                    # Render label and value at fixed positions
                    label_text = self.small_font.render(stat_label, True, self.WHITE)
                    self.screen.blit(label_text, (col2_x, col2_y))

                    value_text = self.small_font.render(str(stats[stat_key]), True, self.WHITE)
                    self.screen.blit(value_text, (col2_x + 120, col2_y))

                    col2_y += line_height - 2

        # Resistances section (fixed position)
        if "resistance" in race:
            resist_header = self.small_font.render("Resistances", True, self.GOLD)
            self.screen.blit(resist_header, (x, resist_y))

            resistances = race["resistance"]

            col1_x = x
            col2_x = x + 180  # Fixed position for second column
            col1_y = resist_y + line_height + 5
            col2_y = resist_y + line_height + 5

            # Left column resistances
            col1_resists = [
                ("fire", "Fire"),
                ("electric", "Electric"),
                ("earth", "Earth"),
                ("shadow", "Shadow"),
                ("poison", "Poison"),
            ]
            for resist_key, resist_label in col1_resists:
                if resist_key in resistances:
                    label_text = self.small_font.render(resist_label, True, self.WHITE)
                    self.screen.blit(label_text, (col1_x, col1_y))

                    value_text = self.small_font.render(
                        f"{resistances[resist_key]:.1f}", True, self.WHITE
                    )
                    self.screen.blit(value_text, (col1_x + 120, col1_y))

                    col1_y += line_height - 2

            # Right column resistances
            col2_resists = [
                ("ice", "Ice"),
                ("water", "Water"),
                ("wind", "Wind"),
                ("holy", "Holy"),
                ("physical", "Physical"),
            ]
            for resist_key, resist_label in col2_resists:
                if resist_key in resistances:
                    label_text = self.small_font.render(resist_label, True, self.WHITE)
                    self.screen.blit(label_text, (col2_x, col2_y))

                    value_text = self.small_font.render(
                        f"{resistances[resist_key]:.1f}", True, self.WHITE
                    )
                    self.screen.blit(value_text, (col2_x + 120, col2_y))

                    col2_y += line_height - 2

        # Available Base Classes section (fixed position)
        if "available_classes" in race:
            classes_header = self.small_font.render("Available Base Classes", True, self.GOLD)
            self.screen.blit(classes_header, (x, classes_y))

            y = classes_y + line_height + 5
            classes_str = ", ".join(race["available_classes"])
            # Word wrap the classes
            words = classes_str.split(", ")
            current_line = []
            for word in words:
                current_line.append(word)
                line = ", ".join(current_line)
                line_width = self.small_font.size(line)[0]
                if line_width > self.details_rect.width - 60:
                    current_line.pop()
                    line = ", ".join(current_line)
                    text = self.small_font.render(line, True, self.WHITE)
                    self.screen.blit(text, (x, y))
                    y += line_height
                    current_line = [word]

            if current_line:
                line = ", ".join(current_line)
                text = self.small_font.render(line, True, self.WHITE)
                self.screen.blit(text, (x, y))

        # Virtue / Sin (bottom anchored so it doesn't collide with stats/resistances)
        if race.get("virtue") or race.get("sin"):

            def _wrap_lines(s: str, max_px: int) -> list[str]:
                words = (s or "").split()
                out = []
                line = ""
                for w in words:
                    test = f"{line} {w}".strip()
                    if self.small_font.size(test)[0] <= max_px:
                        line = test
                    else:
                        if line:
                            out.append(line)
                        line = w
                if line:
                    out.append(line)
                return out

            max_px = self.details_rect.width - 60
            virtue = race.get("virtue") or {}
            sin = race.get("sin") or {}

            trait_lines = 1  # header
            if virtue.get("name"):
                trait_lines += 1 + min(2, len(_wrap_lines(virtue.get("description", ""), max_px)))
            if sin.get("name"):
                trait_lines += 1 + min(2, len(_wrap_lines(sin.get("description", ""), max_px)))

            trait_y = self.details_rect.bottom - 20 - (trait_lines * (line_height - 2))
            trait_header = self.small_font.render("Virtue / Sin", True, self.GOLD)
            self.screen.blit(trait_header, (x, trait_y))
            trait_y += line_height

            if virtue.get("name"):
                vname = self.small_font.render(f"Virtue: {virtue.get('name','')}", True, self.WHITE)
                self.screen.blit(vname, (x, trait_y))
                trait_y += line_height - 2
                for ln in _wrap_lines(virtue.get("description", ""), max_px)[:2]:
                    self.screen.blit(self.small_font.render(ln, True, self.GRAY), (x + 12, trait_y))
                    trait_y += line_height - 2
            if sin.get("name"):
                self.screen.blit(
                    self.small_font.render(f"Sin: {sin.get('name','')}", True, self.WHITE),
                    (x, trait_y),
                )
                trait_y += line_height - 2
                for ln in _wrap_lines(sin.get("description", ""), max_px)[:2]:
                    self.screen.blit(self.small_font.render(ln, True, self.GRAY), (x + 12, trait_y))
                    trait_y += line_height - 2

    def draw_race_list(self):
        """Draw the race list panel."""
        pygame.draw.rect(self.screen, self.BLACK, self.list_rect)
        pygame.draw.rect(self.screen, self.BORDER_COLOR, self.list_rect, 2)

        if not self.races:
            no_races = self.normal_font.render("No races available", True, self.GRAY)
            no_races_rect = no_races.get_rect(
                centerx=self.list_rect.centerx, centery=self.list_rect.centery
            )
            self.screen.blit(no_races, no_races_rect)
            return

        # Draw race list
        x = self.list_rect.left + menu_unit(self.presenter, 20)

        max_visible = 10
        option_rects = self.option_rects()
        for i, race_name in enumerate(self.races[:max_visible]):
            y = option_rects[i].centery

            # Highlight selected
            if i == self.current_selection:
                highlight_rect = option_rects[i]
                pygame.draw.rect(self.screen, self.HIGHLIGHT_BG, highlight_rect)
                pygame.draw.rect(self.screen, self.GOLD, highlight_rect, 1)
                color = self.GOLD
            else:
                color = self.WHITE

            text = self.normal_font.render(race_name, True, color)
            self.screen.blit(text, text.get_rect(left=x, centery=y))

    def draw_all(self):
        """Draw all UI elements."""
        self.screen.fill(self.BLACK)
        self.draw_header()
        self.draw_race_details()
        self.draw_race_list()
        pygame.display.flip()

    def set_races(self, races_dict):
        """
        Set available races.

        Args:
            races_dict: Dictionary of race_name -> race_class
        """
        self.races = []
        self.race_data = {}
        self.current_selection = 0

        for race_name, race_class in races_dict.items():
            self.races.append(race_name)

            # Extract race information
            race_instance = race_class()
            race_info = {
                "name": race_name,
            }

            # Get description if available
            if hasattr(race_instance, "description"):
                race_info["description"] = race_instance.description

            # Get stats directly from race instance
            race_info["stats"] = {
                "strength": getattr(race_instance, "strength", 10),
                "intelligence": getattr(race_instance, "intel", 10),
                "wisdom": getattr(race_instance, "wisdom", 10),
                "constitution": getattr(race_instance, "con", 10),
                "charisma": getattr(race_instance, "charisma", 10),
                "dexterity": getattr(race_instance, "dex", 10),
                "health": getattr(race_instance, "con", 10) * 2,
                "mana": getattr(race_instance, "intel", 10) * 2,
                "attack": getattr(race_instance, "base_attack", 1),
                "defense": getattr(race_instance, "base_defense", 1),
                "magic": getattr(race_instance, "base_magic", 1),
                "magic_defense": getattr(race_instance, "base_magic_def", 1),
            }

            # Get resistances if available
            if hasattr(race_instance, "resistance"):
                resistances = race_instance.resistance
                race_info["resistance"] = {
                    "fire": resistances.get("Fire", 0.0) * 100,  # Convert to percentage
                    "ice": resistances.get("Ice", 0.0) * 100,
                    "electric": resistances.get("Electric", 0.0) * 100,
                    "water": resistances.get("Water", 0.0) * 100,
                    "earth": resistances.get("Earth", 0.0) * 100,
                    "wind": resistances.get("Wind", 0.0) * 100,
                    "shadow": resistances.get("Shadow", 0.0) * 100,
                    "holy": resistances.get("Holy", 0.0) * 100,
                    "poison": resistances.get("Poison", 0.0) * 100,
                    "physical": resistances.get("Physical", 0.0) * 100,
                }

            # Get available base classes from cls_res
            if hasattr(race_instance, "cls_res"):
                cls_res = race_instance.cls_res
                if "Base" in cls_res:
                    race_info["available_classes"] = cls_res["Base"]

            # Racial traits (virtue/sin)
            virtue = getattr(race_instance, "virtue", None)
            sin = getattr(race_instance, "sin", None)
            if virtue is not None:
                race_info["virtue"] = {
                    "name": getattr(virtue, "name", ""),
                    "description": getattr(virtue, "description", ""),
                }
            if sin is not None:
                race_info["sin"] = {
                    "name": getattr(sin, "name", ""),
                    "description": getattr(sin, "description", ""),
                }

            self.race_data[race_name] = race_info

    def navigate(
        self,
        races_dict,
        flush_events: bool = False,
        require_key_release: bool = False,
    ):
        """
        Navigate race selection and return selected race name.

        Args:
            races_dict: Dictionary of race_name -> race_class

        Returns:
            str: Selected race name, or None if cancelled
        """
        self.set_races(races_dict)

        if not self.races:
            return None

        input_armed = prepare_guarded_input(
            flush_events=flush_events,
            require_key_release=require_key_release,
        )

        while True:
            self.draw_all()

            input_armed = release_guard_allows_input(require_key_release, input_armed)
            for event in pygame.event.get():
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
                        return self.races[self.current_selection]
                if event.type == pygame.KEYDOWN:
                    if not input_armed:
                        continue
                    if event.key == pygame.K_UP:
                        self.current_selection = (self.current_selection - 1) % len(self.races)
                    elif event.key == pygame.K_DOWN:
                        self.current_selection = (self.current_selection + 1) % len(self.races)
                    elif event.key == pygame.K_RETURN or event.key == pygame.K_SPACE:
                        return self.races[self.current_selection]
                    elif event.key == pygame.K_ESCAPE:
                        return None

            self.presenter.clock.tick(30)
