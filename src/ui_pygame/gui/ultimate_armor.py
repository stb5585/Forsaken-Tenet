"""
Ultimate Armor Shop for Dungeon
Handles the special armor crafting encounter in the dungeon depths.
"""

import time

import pygame

from src.core import items
from src.ui_pygame.screen_runtime import get_events


class UltimateArmorShop:
    """Manages the ultimate armor shop encounter in the dungeon."""

    def __init__(self, presenter):
        self.presenter = presenter

    def visit_shop(self, player_char, tile):
        """
        Handle ultimate armor shop interaction.

        Args:
            player_char: The player character
            tile: The UltimateArmorShop tile
        """
        # Check for "He Ain't Heavy" quest completion
        if "He Ain't Heavy" in player_char.quest_dict.get("Side", {}):
            if not player_char.quest_dict["Side"]["He Ain't Heavy"].get("Completed", False):
                player_char.quest_dict["Side"]["He Ain't Heavy"]["Completed"] = True
                self.presenter.show_message(
                    "Hmmm, I see my big brother sent you to look for me.\n\n"
                    "Tell him do not worry about me and that I will not return "
                    "until the ultimate evil has been vanquished.",
                    "The Forge Master",
                )

        # Check if already looted
        if tile.looted:
            self.presenter.show_message(
                "Please, defeat him before it's too late...\n\n" "Do not worry about me.",
                "The Forge Master",
            )
            return

        # Show introduction
        self.presenter.show_message(
            "A large man stands before a blazing forge.\n\n"
            '"I can craft you a legendary armor, but you may only choose one.\n\n'
            'Choose wisely, for this opportunity comes but once."',
            "The Forge Master",
        )

        # Offer armor choices
        armor_options = ["Cloth", "Light", "Medium", "Heavy", "Leave"]

        choice = self.presenter.render_menu("Which type of armor do you choose?", armor_options)

        if choice is None or choice == 4:  # Leave
            self.presenter.show_message(
                "You need time to consider your choice, I respect that.\n\n"
                "Come back when you have made your decision.",
                "The Forge Master",
            )
            return

        # Armor list mapping
        armor_classes = [
            items.MerlinRobe,  # Cloth
            items.DragonHide,  # Light
            items.Klivanion,  # Medium
            items.Genji,  # Heavy
        ]

        armor_class = armor_classes[choice]
        armor_item = armor_class()
        armor_type = armor_options[choice]

        # Show armor description
        self.presenter.show_message(
            f"{armor_item.name}\n\n{armor_item.description}", f"{armor_type} Armor"
        )

        # Confirm choice
        confirm = self.presenter.render_menu(
            f"You have chosen an immaculate {armor_type.lower()} armor.\n\nIs this correct?",
            ["Yes", "No"],
        )

        if confirm == 0:  # Yes
            # Show crafting animation
            self._show_crafting_animation(armor_item.name)

            # Give the armor
            player_char.modify_inventory(armor_item)
            tile.looted = True

            self.presenter.show_message(
                f"I present to you the legendary armor:\n\n{armor_item.name}!", "The Forge Master"
            )
        else:
            self.presenter.show_message(
                "You need time to consider your choice, I respect that.\n\n"
                "Come back when you have made your decision.",
                "The Forge Master",
            )

    def _show_crafting_animation(self, armor_name):
        """Show a crafting animation while the armor is being made."""
        screen = self.presenter.screen
        width = screen.get_width()
        height = screen.get_height()

        # Colors
        bg_color = (20, 20, 30)
        text_color = (220, 220, 220)
        fire_colors = [(255, 100, 0), (255, 150, 50), (255, 200, 100)]

        # Fonts
        title_font = pygame.font.Font(None, 48)
        message_font = pygame.font.Font(None, 32)

        # Animation duration
        start_time = time.time()
        duration = 3.0  # 3 seconds

        clock = pygame.time.Clock()

        while time.time() - start_time < duration:
            # Check for quit events
            for event in get_events():
                if event.type == pygame.QUIT:
                    return

            screen.fill(bg_color)

            # Animated fire effect
            elapsed = time.time() - start_time
            fire_idx = int(elapsed * 5) % len(fire_colors)
            fire_color = fire_colors[fire_idx]

            # Title with fire color
            title = title_font.render("Crafting...", True, fire_color)
            title_rect = title.get_rect(center=(width // 2, height // 2 - 50))
            screen.blit(title, title_rect)

            # Message
            message = message_font.render("Please wait while I craft your armor.", True, text_color)
            message_rect = message.get_rect(center=(width // 2, height // 2 + 20))
            screen.blit(message, message_rect)

            # Progress dots
            dots = "." * (int(elapsed * 2) % 4)
            dots_text = message_font.render(dots, True, text_color)
            dots_rect = dots_text.get_rect(center=(width // 2, height // 2 + 60))
            screen.blit(dots_text, dots_rect)

            pygame.display.flip()
            clock.tick(30)
