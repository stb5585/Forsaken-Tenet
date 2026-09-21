"""
Presentation Layer Interface

This module defines the abstract interface that all presenters must implement.
This allows game logic to remain independent of Pygame or future presentation
technologies.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from src.core.character import Character


class GamePresenter(ABC):
    """
    Abstract base class for game presentation/rendering.

    All UI implementations (terminal, GUI, web) should inherit from this
    and implement these methods.
    """

    @abstractmethod
    def initialize(self) -> None:
        """Initialize the presenter (setup window, screen, etc.)"""
        pass

    @abstractmethod
    def cleanup(self) -> None:
        """Clean up resources (close window, restore terminal, etc.)"""
        pass

    @abstractmethod
    def render_combat(
        self, player: Character, enemy: Character, available_actions: list[str], message: str = ""
    ) -> None:
        """
        Render the combat screen.

        Args:
            player: The player character
            enemy: The enemy character
            available_actions: List of actions the player can take
            message: Optional message to display
        """
        pass

    @abstractmethod
    def render_menu(
        self,
        title: str,
        options: list[str],
        selected_index: int = 0,
        max_visible: int | None = None,
    ) -> None:
        """
        Render a menu screen.

        Args:
            title: Menu title
            options: List of menu options
            selected_index: Currently selected option index
        """
        pass

    @abstractmethod
    def render_character_sheet(self, character: Character) -> None:
        """
        Render the character sheet/stats screen.

        Args:
            character: The character to display
        """
        pass

    @abstractmethod
    def render_map(self, world_map: list[list[str]], player_x: int, player_y: int) -> None:
        """
        Render the game map.

        Args:
            world_map: 2D array representing the map
            player_x: Player's X coordinate
            player_y: Player's Y coordinate
        """
        pass

    @abstractmethod
    def show_message(self, message: str, wait_for_input: bool = True) -> None:
        """
        Display a message to the player.

        Args:
            message: The message to display
            wait_for_input: Whether to wait for user input before continuing
        """
        pass

    @abstractmethod
    def show_dialogue(self, speaker: str, text: str, choices: list[str] = None) -> int | None:
        """
        Display dialogue with optional choices.

        Args:
            speaker: Name of the speaking character/NPC
            text: The dialogue text
            choices: Optional list of response choices

        Returns:
            Index of selected choice, or None if no choices
        """
        pass

    @abstractmethod
    def get_player_action(self, available_actions: list[str]) -> str:
        """
        Get the player's chosen action.

        Args:
            available_actions: List of valid actions

        Returns:
            The selected action
        """
        pass

    @abstractmethod
    def get_text_input(self, prompt: str, max_length: int = 50) -> str:
        """
        Get text input from the player.

        Args:
            prompt: The input prompt
            max_length: Maximum allowed input length

        Returns:
            The entered text
        """
        pass

    @abstractmethod
    def confirm(self, question: str) -> bool:
        """
        Ask for yes/no confirmation.

        Args:
            question: The question to ask

        Returns:
            True for yes, False for no
        """
        pass

    @abstractmethod
    def update(self) -> None:
        """Refresh/update the display."""
        pass

    @abstractmethod
    def clear(self) -> None:
        """Clear the display."""
        pass
