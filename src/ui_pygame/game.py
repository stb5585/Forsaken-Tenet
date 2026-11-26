#!/usr/bin/env python3
"""
GUI Game Launcher for The Forsaken Tenet
Uses Pygame for graphical presentation.
"""

import math
import signal
import sys

import pygame

from src.core import items, main_story, opening_story, quest_progress, thieves_guild
from src.core.character import Combat, Level, Resource, Stats
from src.core.classes import archdruid, class_rings, classes_dict
from src.core.data.data_loader import get_intro_story, get_special_events
from src.core.player import summarize_gameplay_stat_groups
from src.core.races import races_dict
from src.core.save_system import SaveManager
from src.paths import CORE_DATA_DIR, MAP_FILES_DIR, PYGAME_ASSETS_DIR, USER_SAVE_DIR
from src.ui_pygame.assets.npc_art_manager import get_npc_art_manager
from src.ui_pygame.screen_runtime import get_events

from .gui.barracks import BarracksManager
from .gui.character_naming import CharacterNamingScreen
from .gui.church import ChurchManager
from .gui.class_selection import ClassSelectionScreen
from .gui.confirmation_popup import ChoicePopup, ConfirmationPopup, confirm_yes_no
from .gui.dungeon_manager import DungeonManager
from .gui.inn import InnManager
from .gui.load_game import LoadGameScreen
from .gui.main_menu import MainMenuScreen
from .gui.modern_character_screen import ModernCharacterScreen
from .gui.presentation_asset_screens import (
    DUNGEON_ENTRY_IMAGE_PATHS,
    INTRO_STORY_IMAGE_PATHS,
    CharacterCreatedScreen,
    StoryCardSequence,
    fade_to_black,
)
from .gui.race_selection import RaceSelectionScreen
from .gui.shop_screen import ShopScreen
from .gui.shop_selection import ShopSelectionScreen
from .gui.shops import ShopManager
from .gui.story_scene import PLAYER_PORTRAIT_KEY, StoryBeat, StorySceneScreen
from .gui.town_menu import TownMenuScreen
from .gui.town_navigation import TownNavigationScreen
from .presentation.pygame_presenter import PygamePresenter
from .user_settings import DIALOGUE_SPEEDS, dialogue_speed_label, save_dialogue_speed

# Use enhanced combat by default
USE_ENHANCED_COMBAT = True


def signal_handler(sig, frame):
    """Handle Ctrl+C gracefully."""
    print("\nExiting game...")
    pygame.quit()
    sys.exit(0)


def install_signal_handlers() -> None:
    """Install process handlers only when launching the executable."""
    signal.signal(signal.SIGINT, signal_handler)


def runtime_smoke_check() -> None:
    """Validate frozen resources and headless Pygame startup, then exit."""
    required_paths = (
        CORE_DATA_DIR / "content" / "quests.json",
        MAP_FILES_DIR / "map_level_1.json",
        MAP_FILES_DIR / "dungeon_tiles.tsx",
        PYGAME_ASSETS_DIR / "backgrounds" / "main_menu.png",
    )
    missing = [str(path) for path in required_paths if not path.is_file()]
    if missing:
        raise FileNotFoundError(f"Missing runtime resources: {', '.join(missing)}")

    from src.core import map_tiles
    from src.core.player.maps import _load_tiled_map

    pygame.init()
    try:
        pygame.display.set_mode((1, 1), flags=pygame.HIDDEN)
        pygame.image.load(str(required_paths[-1]))
        world = _load_tiled_map(required_paths[1], 1, map_tiles)
        if not world:
            raise RuntimeError("Runtime map loaded without tiles.")
        SaveManager.ensure_dirs()
    finally:
        pygame.quit()


class PygameGame:
    """
    GUI version of The Forsaken Tenet using Pygame.
    """

    FOOTPAD_CLASS_RING_RITES = {
        "Rogue": {
            "label": "Loaded Game",
            "intro": (
                "The warehouse guards lead you to a crooked card table. You win by reading "
                "the loaded game, not by pretending the dice were ever fair."
            ),
        },
        "Seeker": {
            "label": "Cartographer's Proof",
            "intro": (
                "A guard spreads half-burned route maps across a crate. Mark the missing paths, "
                "and the Class Ring will learn where hidden caches breathe."
            ),
        },
        "Ninja": {
            "label": "No-Trace Contract",
            "intro": (
                "The lamps are snuffed one by one. A contract waits on black paper: leave no "
                "trace, strike first, and let the ring remember silence."
            ),
        },
        "Arcane Trickster": {
            "label": "Impossible Theft",
            "intro": (
                "The guards lock a spell-sealed coffer in plain sight. The trick is not opening "
                "it, but stealing the moment before the ward notices."
            ),
        },
    }

    def __init__(
        self,
        debug_mode=False,
        remote_playtest_controls=False,
        remote_playtest_input_diagnostics=False,
        remote_playtest_performance_diagnostics=False,
        fullscreen=False,
    ):
        pygame.init()
        presenter_kwargs = {"fullscreen": True} if fullscreen else {}
        self.presenter = PygamePresenter(**presenter_kwargs)
        self.presenter.game = self  # Expose game to presenter for managers (bounties, etc.)
        self.event_bus = self.presenter.event_bus  # Use the same event bus as presenter
        self.debug_mode = debug_mode
        self.remote_playtest_controls = remote_playtest_controls
        self.remote_playtest_input_diagnostics = remote_playtest_input_diagnostics
        self.remote_playtest_performance_diagnostics = remote_playtest_performance_diagnostics
        self.fullscreen = fullscreen
        self._random_combat = True
        self.load_files = SaveManager.list_saves()
        self.races_dict = races_dict
        self.classes_dict = classes_dict
        self.player_char = None
        self.running = True
        self.bounties = {}  # Populated by update_bounties()

        # Initialize managers (will be set after player_char is created)
        self.shop_manager = None
        self.church_manager = None
        self.inn_manager = None
        self.barracks_manager = None
        self.dungeon_manager = None

        # Initialize character menu on-demand when needed.

        self.presenter.debug_mode = debug_mode  # Propagate debug mode to presenter

        self._play_location_music("town")

    def refresh_load_files(self):
        """Refresh the cached save-file list from disk."""
        self.load_files = SaveManager.list_saves()
        return self.load_files

    @staticmethod
    def _popup_show_kwargs(background_draw_func=None, min_display_ms: int | None = None):
        """Common modal-popup options for top-level pygame flows."""
        kwargs = {
            "flush_events": True,
            "require_key_release": True,
        }
        if background_draw_func is not None:
            kwargs["background_draw_func"] = background_draw_func
        if min_display_ms is not None:
            kwargs["min_display_ms"] = min_display_ms
        return kwargs

    def _play_location_music(
        self, location: str, *, boss: bool = False, final: bool = False
    ) -> str | None:
        """Play a location music theme when audio is available, without affecting gameplay."""
        sound_manager = getattr(self.presenter, "sound_manager", None)
        if sound_manager is None or not hasattr(sound_manager, "play_location_music"):
            return None
        try:
            return sound_manager.play_location_music(location, boss=boss, final=final)
        except (AttributeError, OSError, RuntimeError, pygame.error):
            return None

    def _stop_music(self, *, fade_ms: int = 500) -> None:
        """Stop active location music when leaving gameplay screens."""
        sound_manager = getattr(self.presenter, "sound_manager", None)
        if sound_manager is None or not hasattr(sound_manager, "stop_music"):
            return
        try:
            sound_manager.stop_music(fade_ms=fade_ms)
        except (AttributeError, OSError, RuntimeError, pygame.error):
            return

    def special_event(self, name: str, *, message: str | None = None):
        """GUI implementation of narrative special events.

        Displays a formatted modal message using the Pygame confirmation popup.
        """
        if name == "Timmy":
            self._show_timmy_discovery()
            return

        if message is None:
            try:
                special_event_dict = get_special_events()
                lines = special_event_dict.get(name, {}).get("Text", [])
            except (OSError, TypeError, ValueError):
                lines = []

            if lines:
                # Join lines into paragraphs and let the popup handle wrapping
                message = " ".join(line.strip() for line in lines if line is not None).strip()
            else:
                message = name

        # Show message-only popup (any key to continue)
        # Pass a background draw function that maintains current screen state
        def draw_current_screen():
            """Redraw the current game state (dungeon or town) to screen."""
            try:
                if self.dungeon_manager and self.player_char.location_z > 0:
                    # In dungeon: render the dungeon view
                    self.dungeon_manager._render()
                else:
                    # In town: render town (currently just black, which is fine)
                    # The TownMenuScreen would be responsible for drawing if we're in town UI
                    pass
            except (AttributeError, pygame.error):
                return

        if name == "Funhouse Entry":
            self._play_funhouse_entry_effect(draw_current_screen)

        popup = ConfirmationPopup(self.presenter, message, show_buttons=False, slow_print=True)
        popup.show(
            background_draw_func=draw_current_screen,
            flush_events=True,
            require_key_release=True,
            min_display_ms=300,
        )

    def _show_timmy_discovery(self) -> None:
        """Stage Timmy's dungeon rescue before the existing return to town."""
        scene = StorySceneScreen(
            self.presenter,
            "The Dungeon — A Voice in the Rubble",
            participants=("Timmy",),
            background_image="dungeon.png",
            player_char=self.player_char,
        )
        scene.show_dialogue(
            (
                StoryBeat(
                    "Narrator",
                    "A small voice answers your footsteps from behind a fall of loose stone.",
                    portrait_name="",
                ),
                StoryBeat("Timmy", "Hello? Who's there?"),
                StoryBeat(
                    "Narrator",
                    "A boy edges out of the rubble. His clothes are torn, his hands are "
                    "scraped, and he is trying hard not to shake.",
                    portrait_name="",
                ),
                StoryBeat("Timmy", "I'm Timmy. I tried to go back, but I couldn't find the door."),
                StoryBeat(
                    "Timmy",
                    "Can you take me home? My mum and dad will be looking for me.",
                ),
                StoryBeat(
                    "Narrator",
                    "You give Timmy your hand and lead him toward the last route you know is "
                    "safe. He does not let go until Silvana's lanterns are in sight.",
                    portrait_name="",
                ),
            )
        )

    def _play_funhouse_entry_effect(self, draw_current_screen, duration_ms: int = 1100):
        """Play a brief reality-warp effect before the funhouse entry popup."""
        if not self.presenter or not self.dungeon_manager:
            return

        draw_current_screen()
        base_surface = self.presenter.screen.copy()
        clock = pygame.time.Clock()
        start = pygame.time.get_ticks()
        width, height = self.presenter.width, self.presenter.height

        while True:
            now = pygame.time.get_ticks()
            elapsed = now - start
            if elapsed >= duration_ms:
                break

            for event in get_events():
                if event.type == pygame.QUIT:
                    pygame.quit()
                    sys.exit(0)

            t = elapsed / duration_ms
            pulse = math.sin(t * math.pi * 4.5)
            wobble = math.sin(t * math.pi * 7.0)
            angle = pulse * 5.5
            scale = 1.0 + (0.03 * math.sin(t * math.pi * 3.0)) + (0.08 * t)
            warped = pygame.transform.rotozoom(base_surface, angle, scale)
            warped_rect = warped.get_rect(
                center=(
                    width // 2 + int(wobble * 18),
                    height // 2 + int(math.cos(t * math.pi * 5.5) * 10),
                )
            )

            self.presenter.screen.fill((4, 0, 8))
            self.presenter.screen.blit(warped, warped_rect)

            veil = pygame.Surface((width, height), pygame.SRCALPHA)
            magenta = int(55 + 70 * max(0.0, pulse))
            cyan = int(45 + 80 * max(0.0, -pulse))
            veil.fill((magenta, 20, cyan + 20, int(35 + 65 * t)))
            self.presenter.screen.blit(veil, (0, 0))

            band_count = 6
            for index in range(band_count):
                phase = (t * 240) + (index * 37)
                band_y = int((height / band_count) * index + math.sin(phase * 0.05) * 14)
                band_h = max(24, height // 9)
                src_y = max(0, min(height - band_h, band_y))
                slice_surface = base_surface.subsurface((0, src_y, width, band_h)).copy()
                offset_x = int(math.sin((phase + index * 11) * 0.12) * (18 + 14 * t))
                alpha = int(30 + 70 * (1.0 - t))
                slice_surface.set_alpha(alpha)
                self.presenter.screen.blit(slice_surface, (offset_x, src_y))

            flash = pygame.Surface((width, height), pygame.SRCALPHA)
            flash_alpha = int(max(0, 120 * (1.0 - abs(0.5 - t) * 2.0)))
            flash.fill((255, 255, 255, flash_alpha))
            self.presenter.screen.blit(flash, (0, 0))

            pygame.display.flip()
            clock.tick(60)

        draw_current_screen()

    def debug_level_up(self):
        """Debug-only shortcut to trigger a single level-up."""
        if not self.debug_mode or not self.player_char:
            return
        if self.player_char.max_level():
            popup = ConfirmationPopup(
                self.presenter,
                "Already at max level.",
                show_buttons=False,
            )
            popup.show(flush_events=True, require_key_release=True)
            return

        from .gui.level_up import LevelUpScreen

        level_up_screen = LevelUpScreen(self.presenter.screen, self.presenter)
        level_up_screen.show_level_up(self.player_char, self)

    def initialize_managers(self):
        """Initialize location managers after player character is created."""
        self.shop_manager = ShopManager(self.presenter, self.player_char)
        self.church_manager = ChurchManager(self.presenter, self.player_char)
        self.inn_manager = InnManager(self.presenter, self.player_char)
        try:
            self.barracks_manager = BarracksManager(self.presenter, self.player_char, game=self)
        except TypeError:
            self.barracks_manager = BarracksManager(self.presenter, self.player_char)
        manager_kwargs = {}
        if getattr(self, "remote_playtest_controls", False):
            manager_kwargs["remote_playtest_controls"] = True
            if getattr(self, "remote_playtest_input_diagnostics", False):
                manager_kwargs["remote_playtest_input_diagnostics"] = True
            if getattr(self, "remote_playtest_performance_diagnostics", False):
                manager_kwargs["remote_playtest_performance_diagnostics"] = True
        self.dungeon_manager = DungeonManager(
            self.presenter, self.player_char, self, **manager_kwargs
        )

    def _build_player_character(
        self, race_name, class_name, name="Hero", sex="Male", portrait_variant=0
    ):
        """Build a player character from selected race/class and name."""
        from src.core.player import Player

        race_ctor = self.races_dict.get(race_name)
        class_entry = self.classes_dict.get(class_name, {})
        class_ctor = class_entry.get("class") if isinstance(class_entry, dict) else None

        if race_ctor is None:
            race_name, race_ctor = next(iter(self.races_dict.items()))
        race = race_ctor()

        if class_ctor is None:
            class_name = race.cls_res["Base"][0]
            class_ctor = self.classes_dict[class_name]["class"]
        char_class = class_ctor()

        location_x, location_y, location_z = (5, 10, 0)
        stats_tuple = tuple(
            map(
                lambda x, y: x + y,
                (race.strength, race.intel, race.wisdom, race.con, race.charisma, race.dex),
                (
                    char_class.str_plus,
                    char_class.int_plus,
                    char_class.wis_plus,
                    char_class.con_plus,
                    char_class.cha_plus,
                    char_class.dex_plus,
                ),
            )
        )
        hp = stats_tuple[3] * 2
        mp = stats_tuple[1] * 2
        attack = race.base_attack + char_class.att_plus
        defense = race.base_defense + char_class.def_plus
        magic = race.base_magic + char_class.magic_plus
        magic_def = race.base_magic_def + char_class.magic_def_plus
        gold = stats_tuple[4] * 25

        player_char = Player(
            location_x,
            location_y,
            location_z,
            level=Level(),
            health=Resource(hp, hp),
            mana=Resource(mp, mp),
            stats=Stats(
                stats_tuple[0],
                stats_tuple[1],
                stats_tuple[2],
                stats_tuple[3],
                stats_tuple[4],
                stats_tuple[5],
            ),
            combat=Combat(attack=attack, defense=defense, magic=magic, magic_def=magic_def),
            gold=gold,
            resistance=race.resistance,
        )
        player_char.name = name or "Hero"
        player_char.sex = sex or "Male"
        player_char.portrait_variant = int(portrait_variant or 0)
        player_char.race = race
        player_char.cls = char_class
        player_char.transform_type = char_class
        player_char.equipment = char_class.equipment

        from ..core.progression import initialize_progression

        initialize_progression(player_char)

        player_char.storage["Health Potion"] = [items.HealthPotion() for _ in range(5)]
        player_char.load_tiles()
        return player_char

    def create_default_character(self, name="Hero"):
        """Create a default preview character for quick UI testing."""
        return self._build_player_character(
            race_name="Human", class_name="Warrior", name=name, sex="Male"
        )

    def main_menu(self):
        """Display main menu and handle selection."""
        self._stop_music(fade_ms=250)
        self._play_location_music("menu")
        # Check debug mode settings
        if self.debug_mode:
            if confirm_yes_no(self.presenter, "Debug Mode - Turn off random encounters?"):
                self._random_combat = False
                popup = ConfirmationPopup(
                    self.presenter, "Random encounters disabled", show_buttons=False
                )
                popup.show(**self._popup_show_kwargs())
            else:
                self._random_combat = True
                popup = ConfirmationPopup(
                    self.presenter, "Random encounters enabled", show_buttons=False
                )
                popup.show(**self._popup_show_kwargs())

        # Create main menu screen
        main_menu = MainMenuScreen(self.presenter)

        while self.running:
            # Build menu options each iteration to pick up new save files
            self.refresh_load_files()
            menu_options = ["New Game"]
            if self.load_files:
                menu_options.append("Load Game")
            menu_options.append("Settings")
            menu_options.append("Exit")

            choice = main_menu.navigate(
                menu_options,
                flush_events=True,
                require_key_release=True,
            )

            if choice is None:
                # ESC pressed
                self.running = False
            elif menu_options[choice] == "New Game":
                self._creation_background_draw_func = getattr(main_menu, "draw_background", None)
                self.player_char = self.new_game()
                if self.player_char:
                    self.run()
                    self._stop_music(fade_ms=250)
            elif menu_options[choice] == "Load Game":
                self.player_char = self.load_game()
                if self.player_char:
                    self.run()
                    self._stop_music(fade_ms=250)
            elif menu_options[choice] == "Settings":
                if self.show_display_settings():
                    main_menu = MainMenuScreen(self.presenter)
            elif menu_options[choice] == "Exit":
                self.running = False

    def show_display_settings(self) -> bool:
        """Let players adjust display mode and persistent dialogue speed."""
        choices = (
            ("Windowed 1024 x 768", False, (1024, 768)),
            ("Windowed 1366 x 768", False, (1366, 768)),
            ("Windowed 1920 x 1080", False, (1920, 1080)),
            ("Fullscreen (active display)", True, None),
        )
        changed = False
        while True:
            dialogue_cps = int(getattr(self.presenter, "story_dialogue_cps", 35))
            labels = [choice[0] for choice in choices]
            labels.extend([f"Dialogue Speed: {dialogue_speed_label(dialogue_cps)}", "Back"])
            selection = ChoicePopup(
                self.presenter,
                "Settings",
                labels,
                "Choose display behavior or how quickly storyline dialogue appears.",
            ).show()
            if selection is None or selection == len(labels) - 1:
                return changed
            if selection < len(choices):
                _label, fullscreen, resolution = choices[selection]
                self.presenter.apply_display_mode(fullscreen=fullscreen, resolution=resolution)
                self.fullscreen = fullscreen
                changed = True
                continue

            speed_labels = list(DIALOGUE_SPEEDS)
            speed_selection = ChoicePopup(
                self.presenter,
                "Dialogue Speed",
                speed_labels + ["Back"],
                "Click once to complete the current line; click again to continue.",
            ).show()
            if speed_selection is None or speed_selection == len(speed_labels):
                continue
            speed = DIALOGUE_SPEEDS[speed_labels[speed_selection]]
            self.presenter.story_dialogue_cps = speed
            save_dialogue_speed(speed)
            changed = True

    def new_game(self):
        """Create a new character."""
        background_draw_func = getattr(self, "_creation_background_draw_func", None)
        # Loop for race selection with confirmation
        while True:
            # Choose race using RaceSelectionScreen
            race_screen = RaceSelectionScreen(self.presenter)
            race_screen.background_draw_func = background_draw_func
            race_name = race_screen.navigate(
                self.races_dict,
                flush_events=True,
                require_key_release=True,
            )
            if race_name is None:
                return None  # ESC pressed, return to main menu
            race = self.races_dict[race_name]()  # Instantiate the race class

            # Confirm race selection with popup
            confirm_race = ConfirmationPopup(
                self.presenter,
                f"You have selected {race_name} as your race. Continue?",
                show_buttons=True,
            )
            if confirm_race.show(**self._popup_show_kwargs()):
                break  # Yes selected, continue to class selection
            # No selected, loop back to race selection

        # Loop for class selection with confirmation
        while True:
            # Choose class using ClassSelectionScreen
            class_screen = ClassSelectionScreen(self.presenter)
            class_screen.background_draw_func = background_draw_func
            class_name = class_screen.navigate(
                race_name,
                race,
                self.classes_dict,
                flush_events=True,
                require_key_release=True,
            )
            if class_name is None:
                return None  # ESC pressed, return to main menu
            self.classes_dict[class_name]["class"]()  # Get class from nested dict

            # Confirm class selection with popup
            confirm_class = ConfirmationPopup(
                self.presenter,
                f"You have selected {class_name} as your class. Continue?",
                show_buttons=True,
            )
            if confirm_class.show(**self._popup_show_kwargs()):
                break  # Yes selected, continue to name input
            # No selected, loop back to class selection

        # Get character name, sex, and portrait variant after race/class selection.
        name_screen = CharacterNamingScreen(self.presenter, race_name, class_name)
        name_screen.background_draw_func = background_draw_func
        name = name_screen.navigate(
            default="Hero",
            flush_events=True,
            require_key_release=True,
        )
        if name is None:
            return None

        # Create player character using the same logic as the original game
        player_char = self._build_player_character(
            race_name,
            class_name,
            name=name,
            sex=getattr(name_screen, "sex", "Male"),
            portrait_variant=getattr(name_screen, "selected_portrait_variant", 0),
        )

        created_screen = CharacterCreatedScreen(self.presenter, player_char)
        created_screen.background_draw_func = background_draw_func
        created_screen.show(
            flush_events=True,
            require_key_release=True,
        )
        fade_to_black(self.presenter, duration_ms=700, hold_ms=180)

        self.player_char = player_char
        self.initialize_managers()  # Initialize location managers

        return player_char

    def load_game(self):
        """Load a saved game."""
        self.refresh_load_files()
        if not self.load_files:
            self.presenter.show_message("No saved games found!")
            return None

        # Use the new LoadGameScreen interface
        load_screen = LoadGameScreen(self.presenter)
        selected_file = load_screen.navigate(
            self.load_files,
            flush_events=True,
            require_key_release=True,
        )

        if selected_file is None:
            return None

        def load_selected_game():
            player_char = SaveManager.load_player(selected_file)
            if player_char is None:
                load_result = SaveManager.last_load_result
                if load_result.error:
                    self.presenter.show_message(load_result.error)
                return None

            # Reset quit flag - player is loading to continue playing
            player_char.quit = False

            # Set flag to suppress heal message if loading in town
            if player_char.in_town():
                player_char._suppress_heal_message = True
            # Skip blocking message; jump straight into the game

            self.player_char = player_char
            self.initialize_managers()
            return player_char

        # Show a loading popup while the save and managers restore.
        player_char = self.presenter.show_progress_popup(
            header="Load Game",
            message="Loading game file...",
            work=load_selected_game,
        )
        if player_char is None:
            self.presenter.show_message("Failed to load character!")
            return None

        return player_char

    def run(self):
        """Main game loop."""
        if not self.player_char:
            return

        # Ensure bounties are available for GUI bounty board
        self.update_bounties()

        # Show intro story for new characters (level 1)
        if self.player_char.level.level == 1 and not getattr(
            self.player_char, "intro_shown", False
        ):
            self.show_intro()
            self.player_char.intro_shown = True

        ensure_story = getattr(self.player_char, "ensure_main_story_state", None)
        story_state = (
            ensure_story() if callable(ensure_story) else main_story.ensure_state(self.player_char)
        )
        if not story_state.get("arrival_scene_seen"):
            self.show_opening_arrival()

        # Main game loop
        while True:
            # Check if player quit
            if self.player_char.quit:
                break

            # Check if player is in town
            if self.player_char.in_town():
                choice = self.town_menu()
                if choice == "quit":
                    break
                elif choice == "dungeon":
                    # Enter the dungeon in first-person mode
                    self.enter_dungeon()
            else:
                # Already in dungeon - show exploration interface
                self.enter_dungeon()

    def update_bounties(self):
        """Generate bounties when the shared restock cadence allows it."""
        from src.core import town

        if getattr(self, "bounties", None):
            state = town.ensure_bounty_board_state(self.player_char)
            if not state["initialized"]:
                town.mark_bounty_board_restock(self.player_char)
                return
            if town._player_level(self.player_char) <= state["last_restock_level"]:
                return
            # Board offers have not been accepted yet, so replace them when a
            # level-up changes the appropriate bounty enemy band. Accepted
            # bounties remain in the player's quest dictionary.
        self.bounties = {}
        bounty_board = town.BountyBoard()
        bounty_board.generate_bounties(self)
        if bounty_board.bounties:
            self.bounties = {bounty["enemy"].name: bounty for bounty in bounty_board.bounties}

    def show_intro(self):
        """Show the game introduction story."""
        intro_texts = get_intro_story()

        StoryCardSequence(
            self.presenter,
            intro_texts,
            title="The Story Begins",
            image_paths=INTRO_STORY_IMAGE_PATHS,
        ).show(
            flush_events=True,
            require_key_release=True,
            fade_in_ms=700,
        )
        fade_to_black(self.presenter, duration_ms=1200, hold_ms=1500)

    def show_opening_arrival(self) -> bool:
        """Present the tavern arrival, failed patrol return, and first offer."""
        story_state = main_story.ensure_state(self.player_char)
        scene = StorySceneScreen(
            self.presenter,
            "The Thirsty Dog — A New Face",
            participants=("Liora", "Joffrey", "Pell", "Oren", "Tavin"),
            participant_anchors={"Pell": "Joffrey", "Tavin": "Oren"},
            background_image="tavern.jpg",
            player_char=self.player_char,
        )
        scene.show_dialogue(
            (
                StoryBeat(
                    "Narrator",
                    "Rain follows you through the door of The Thirsty Dog. The room is warm, "
                    "crowded, and loud enough that no one notices the newcomer at first. At "
                    "the bar, a familiar argument is already underway.",
                    portrait_name="",
                ),
                StoryBeat(
                    "Liora",
                    "If Pell invites everyone he owes a drink, we will need three more tables "
                    "for the wedding.",
                ),
                StoryBeat("Joffrey", "Only three?"),
                StoryBeat("Pell", "Hey! I thought that was pretty good..."),
                StoryBeat("Oren", "Too bad we don't have the room for all of them."),
                StoryBeat(
                    "Narrator",
                    "Oren moves a stack of empty plates off the stool beside you.",
                    portrait_name="",
                ),
                StoryBeat("Oren", "Sit down while there's a seat. I'm Oren. What brings you in?"),
            ),
            fade_in_ms=900,
        )
        motive_options = [
            "I came for the money.",
            "People are missing. If I can help, I should.",
            "I want to know what opened under this town.",
            "I needed a fresh start.",
        ]
        motive_choice = scene.choose(
            "What brought you to Silvana?",
            motive_options,
            allow_cancel=False,
        )
        scene.show_dialogue(
            (
                StoryBeat(
                    "Narrator",
                    "Oren accepts the answer with a nod. Tavin sets a drink beside you. In an "
                    "unlit corner, a hooded figure watches without speaking.",
                    portrait_name="",
                ),
            )
        )

        scene = StorySceneScreen(
            self.presenter,
            "The Thirsty Dog — The Patrol Returns",
            participants=("Edrin", "Caedmon", "Joffrey", "Liora"),
            participant_anchors={"Joffrey": "Edrin", "Liora": "Edrin"},
            background_image="tavern.jpg",
            player_char=self.player_char,
        )
        scene.show_dialogue(
            (
                StoryBeat(
                    "Narrator",
                    "The tavern door strikes the wall. Joffrey catches Edrin before he falls; "
                    "Liora clears a table and begins binding his wounds.",
                    portrait_name="",
                ),
                StoryBeat("Caedmon", "Edrin. You left with Mira and Tomas. Where are they?"),
                StoryBeat(
                    "Edrin",
                    "Still down there. We took your north route, Joffrey. Mira chalked the turns.",
                ),
                StoryBeat("Joffrey", "Two junctions before the drainage hall?"),
                StoryBeat(
                    "Edrin",
                    "Four. I counted. Tomas said we'd walked straight the whole way. "
                    "Even the chalk was wrong. We passed Mira's last mark before her first.",
                ),
                StoryBeat("Caedmon", "Where did you lose them?"),
                StoryBeat(
                    "Edrin",
                    "Our lamps went out. Stone grinding somewhere. When I got mine lit, "
                    "there was a door between us.",
                ),
                StoryBeat("Caedmon", "Could you hear them through it?"),
                StoryBeat(
                    "Edrin",
                    "I heard Tomas once. Mira kept knocking. She said there were three marks "
                    "underfoot. I could see all three above the door.",
                ),
                StoryBeat("Joffrey", "Was she still knocking when you left?"),
                StoryBeat(
                    "Edrin",
                    "I stayed as long as I could. There was something behind me. Every time "
                    "I looked it had a different shape. Same pale eyes, though.",
                ),
                StoryBeat("Joffrey", "Here, lean on me. I'm trying to work out where to dig."),
            )
        )
        aid_options = [
            "I'll clear some space. Keep the crowd back.",
            "I'll hold him steady while Liora works.",
            "I'll write it down while it's fresh.",
            "I'll get the kit and some clean water.",
        ]
        aid_choice = scene.choose("How do you help?", aid_options, allow_cancel=False)
        hero_name = str(getattr(self.player_char, "name", None) or "You")
        aid_responses = (
            (
                StoryBeat("Narrator", "You ease the onlookers back from the table."),
                StoryBeat("Liora", "That's better. Edrin, can you see me?"),
            ),
            (
                StoryBeat("Liora", "Here. His elbow. Hold him just there."),
                StoryBeat("Edrin", "Your sleeve. I've got blood all over it."),
            ),
            (
                StoryBeat("Oren", "Here. Use the back of the drinks bill."),
                StoryBeat("Caedmon", "How many junctions did you put down?"),
                StoryBeat(hero_name, "Four. That's how many Edrin counted.", PLAYER_PORTRAIT_KEY),
            ),
            (
                StoryBeat("Narrator", "You bring the kit and a basin of clean water."),
                StoryBeat("Liora", "Set it by my knee. Thank you."),
            ),
        )
        scene.show_dialogue(aid_responses[aid_choice])
        opening_story.record_arrival(
            story_state,
            opening_story.ARRIVAL_MOTIVES[motive_choice],
            opening_story.ARRIVAL_AID_CHOICES[aid_choice],
        )

        scene = StorySceneScreen(
            self.presenter,
            "The Thirsty Dog — An Uncertain Report",
            participants=("Oren", "Caedmon"),
            background_image="tavern.jpg",
            player_char=self.player_char,
        )
        scene.show_dialogue(
            (
                StoryBeat(
                    "Oren",
                    "Caedmon, take this one along. Saw what needed doing.",
                ),
                StoryBeat("Caedmon", "Ever been down those stairs before?"),
                StoryBeat("Oren", "Just got in. Hasn't even touched that drink."),
                StoryBeat(
                    "Caedmon",
                    "Good. I've had three patrols in my map room this week. Ask any of them "
                    "where a passage goes and they'll trace it with their eyes shut.",
                ),
                StoryBeat(
                    "Caedmon",
                    "Read their reports. Then go down and tell me what you actually find. "
                    "I need somewhere to start looking for those two.",
                ),
            )
        )
        offer_choice = scene.choose(
            "Will you investigate the reports?",
            ["I'll investigate them.", "Not yet."],
        )
        if offer_choice == 0:
            quest_progress.ensure_uncertain_reports_quest(self.player_char)
            handoff_text = (
                "Caedmon takes Edrin's report back to the barracks. He tells you the patrol "
                "ledgers will be ready there. For now, Silvana is open to you."
            )
        else:
            handoff_text = (
                "Caedmon takes Edrin's report back to the barracks. His offer remains open if "
                "you decide to hear it. For now, Silvana is open to you."
            )
        scene.show_dialogue((StoryBeat("Narrator", handoff_text, portrait_name=""),))
        self.player_char._suppress_heal_message = True
        return True

    def choose_triangulus_identity(self) -> str | None:
        """Ask and return the saved-value form of the Triangulus identity answer."""
        options = [
            "The name I choose.",
            "What I've done and what I do next.",
            "What I refuse to forget.",
            "My next choice.",
        ]
        scene = StorySceneScreen(
            self.presenter,
            "The Sealed Chamber — Triangulus",
            background_image="dungeon.png",
            player_char=self.player_char,
        )
        choice = scene.choose(
            "Take away your title, bloodline, and what others expect. What is still yours?",
            options,
        )
        if choice is None:
            return None
        return opening_story.TRIANGULUS_IDENTITY_ANSWERS[choice]

    def _story_dungeon_background(self) -> None:
        """Redraw the current dungeon view behind a storyline scene."""
        if self.dungeon_manager is not None:
            self.dungeon_manager._render()

    def show_triangulus_threshold(self) -> None:
        """Present Tomas, Mira, and the prior-explorer fragment in the story UI."""
        scene = StorySceneScreen(
            self.presenter,
            "The Sealed Threshold",
            participants=("Tomas Reed", "Mira Venn"),
            background_image="dungeon.png",
            player_char=self.player_char,
        )
        scene.show_dialogue(
            (
                StoryBeat(
                    "Narrator",
                    "Beneath fallen stone lies Tomas Reed, identified by his patrol clasp. "
                    "Mira Venn is not here. Her chalk route marks continue beyond Tomas, cross "
                    "the threshold, and end without a body or a clear return path.",
                    portrait_name="",
                ),
                StoryBeat(
                    "Weathered Note",
                    "I wrote my name beside every turn so the dark could not take it. At the "
                    "seventh mark, the letters were mine but the hand was not. A name is proof "
                    "only while someone still chooses to answer to it.",
                    portrait_name="",
                ),
            )
        )

    def show_relic_discovery(self, message: str) -> None:
        """Present a relic discovery without falling back to a generic event popup."""
        scene = StorySceneScreen(
            self.presenter,
            "The Sealed Chamber",
            background_image="dungeon.png",
            player_char=self.player_char,
        )
        scene.show_dialogue((StoryBeat("Narrator", message, portrait_name=""),))

    def _resolve_rookie_mistake_on_arrival(self) -> bool:
        """Turn in the recovered recruit through the authored arrival sequence."""
        quest = self.player_char.quest_dict.get("Side", {}).get("Rookie Mistake")
        has_body = "Dead Soldier" in getattr(self.player_char, "special_inventory", {})
        if not quest or not has_body or quest.get("Turned In"):
            return False

        quest["Completed"] = True
        from .gui.quest_manager import QuestManager

        manager = QuestManager(self.presenter, self.player_char)
        return manager.turn_in_completed_quest(
            "Rookie Mistake",
            "Side",
            show_end_text=False,
        )

    def town_menu(self):
        """Display town menu and handle selection."""
        self._play_location_music("town")
        self._resolve_rookie_mistake_on_arrival()
        story_state = main_story.ensure_state(self.player_char)
        if opening_story.should_show_route_review(story_state):
            courtyard_scene = StorySceneScreen(
                self.presenter,
                "Silvana Courtyard — Waiting At The Stair",
                participants=("Joffrey", "Liora"),
                participant_anchors={"Liora": "Joffrey"},
                background_image="town.png",
                player_char=self.player_char,
            )
            courtyard_scene.show_dialogue(
                (
                    StoryBeat(
                        "Narrator",
                        "Silvana's courtyard receives you in cold rain. Joffrey and Liora "
                        "are waiting beyond the last stair, watching each face that returns "
                        "from the depths.",
                        portrait_name="",
                    ),
                    StoryBeat(
                        "Liora",
                        "There you are. Caedmon's still in the barracks map room.",
                    ),
                    StoryBeat(
                        "Joffrey",
                        "Did you get a look at the stonework by the stairs? Come show me.",
                    ),
                    StoryBeat(
                        "Narrator",
                        "They lead you across the courtyard and into the barracks before the "
                        "rain can erase the mud from your boots.",
                        portrait_name="",
                    ),
                ),
                fade_in_ms=1400,
                fade_hold_ms=450,
            )
            barracks_scene = StorySceneScreen(
                self.presenter,
                "Barracks — Correcting The Route",
                participants=("Joffrey", "Caedmon", "Liora"),
                participant_anchors={"Liora": "Joffrey"},
                background_image="barracks.jpg",
                player_char=self.player_char,
            )
            barracks_scene.show_dialogue(
                (
                    StoryBeat(
                        "Narrator",
                        "Caedmon clears the planning table. Joffrey lays two maps beside the "
                        "patrol ledgers and pins the disputed junction beneath a brass weight.",
                        portrait_name="",
                    ),
                    StoryBeat(
                        "Joffrey",
                        "Here's the drain by the stairs. I drew one solid slab across the end. "
                        "What did you see there?",
                    ),
                ),
                fade_in_ms=700,
            )
            map_choice = barracks_scene.choose(
                "What do you tell Joffrey?",
                [
                    "An old arch. Right where you've drawn that wall.",
                    "I saw an arch. I couldn't tell where it led.",
                    "You're sure that was a wall when you drew it?",
                ],
            )
            map_replies = (
                "Right there? Give me the pencil. I'll put your arch beside my wall.",
                "Fair enough. I'll mark the arch. No passage until we've seen one.",
                "One unbroken slab. I sat with my back against it to draw the stair.",
            )
            if map_choice is not None:
                barracks_scene.show_dialogue((StoryBeat("Joffrey", map_replies[map_choice]),))
            barracks_scene.show_dialogue(
                (
                    StoryBeat("Caedmon", "Leave both marks. I want the next patrol to see them."),
                    StoryBeat("Liora", "And if they get down there and neither mark fits?"),
                    StoryBeat("Joffrey", "Then I go with them."),
                    StoryBeat("Liora", "I thought you might say that."),
                )
            )
            story_state["joffrey_route_review_seen"] = True
        # Build options list first so it can be reused for popups
        options = [
            "Barracks",
            "Shops",
            "The Thirsty Dog Tavern",
            "Church of Elysia",
        ]
        if archdruid.grove_unlocked(self.player_char):
            options.append("Ancient Grove")
        options.append("Enter Dungeon")

        # Add Warp Point or Old Warehouse based on player progress
        if getattr(self.player_char, "warp_point", False):
            options.append("Warp Point")
        else:
            options.append("Old Warehouse")

        options.append("Character Menu")
        options.append("Statistics")
        options.append("Settings")
        options.append("Quit to Main Menu")

        # Create and use the new town menu screen
        town_screen = TownMenuScreen(self.presenter)

        # Auto-heal when entering town menu. Gameplay failures must remain visible.
        self.player_char.town_heal()
        # Check if we should suppress the heal message (loading in town)
        if not getattr(self.player_char, "_suppress_heal_message", False):
            popup = ConfirmationPopup(
                self.presenter,
                "You rest in town. HP and MP fully restored.",
                show_buttons=False,
            )
            popup.show(
                **self._popup_show_kwargs(
                    lambda town_screen=town_screen, options=options: (
                        town_screen.draw_background(),
                        town_screen.draw_menu_panel(options),
                    )
                )
            )
        else:
            # Clear the flag after first use
            self.player_char._suppress_heal_message = False

        while True:
            choice_idx = town_screen.navigate(
                options,
                flush_events=True,
                require_key_release=True,
            )

            if choice_idx is None or choice_idx == len(options) - 1:  # Quit
                popup = ConfirmationPopup(self.presenter, "Return to the main menu?")
                if popup.show(
                    **self._popup_show_kwargs(
                        lambda town_screen=town_screen, options=options: (
                            town_screen.draw_background(),
                            town_screen.draw_menu_panel(options),
                        )
                    )
                ):
                    return "quit"
                continue
            choice_label = options[choice_idx]

            if choice_label == "Barracks":
                self.visit_barracks()

            elif choice_label == "Shops":
                self.visit_shop()

            elif choice_label == "The Thirsty Dog Tavern":
                self.visit_inn()

            elif choice_label == "Church of Elysia":
                self.visit_church()

            elif choice_label == "Ancient Grove":
                self.visit_ancient_grove()

            elif choice_label == "Enter Dungeon":
                return self._enter_dungeon_from_town()

            elif choice_label == "Warp Point":
                result = self.use_warp_point(
                    background_draw_func=lambda town_screen=town_screen, options=options: (
                        town_screen.draw_background(),
                        town_screen.draw_menu_panel(options),
                    )
                )
                if result == "dungeon":
                    return "dungeon"

            elif choice_label == "Old Warehouse":
                self.visit_old_warehouse(
                    background_draw_func=lambda town_screen=town_screen, options=options: (
                        town_screen.draw_background(),
                        town_screen.draw_menu_panel(options),
                    )
                )

            elif choice_label == "Character Menu":
                self.show_character_info()
                # Check if player quit while in character menu
                if self.player_char.quit:
                    return "quit"

            elif choice_label == "Statistics":
                self.show_gameplay_statistics(
                    background_draw_func=lambda town_screen=town_screen, options=options: (
                        town_screen.draw_background(),
                        town_screen.draw_menu_panel(options),
                    )
                )

            elif choice_label == "Settings":
                if self.show_display_settings():
                    # A display mode change replaces the native Pygame surface.
                    # Rebuild the town view so it uses the new dimensions.
                    town_screen = TownMenuScreen(self.presenter)

    def _enter_dungeon_from_town(self) -> str:
        """Place the player at the dungeon entrance and enter exploration."""
        story_state = main_story.ensure_state(self.player_char)
        if not story_state.get("dungeon_entry_story_seen"):
            StoryCardSequence(
                self.presenter,
                (opening_story.FIRST_DUNGEON_ENTRY_TEXT,),
                title="The First Descent",
                image_paths=DUNGEON_ENTRY_IMAGE_PATHS,
            ).show(
                flush_events=True,
                require_key_release=True,
                fade_in_ms=700,
            )
            opening_story.record_dungeon_entry_story(story_state)
            fade_to_black(self.presenter, duration_ms=500, hold_ms=150)
        if self.player_char.location_z == 0:
            self.player_char.location_x = 5
            self.player_char.location_y = 10
            self.player_char.location_z = 1
            self.player_char.facing = "east"
        return "dungeon"

    def explore_town_prototype(self):
        """Run the optional first-person-style town navigation prototype."""
        self._play_location_music("town")
        nav_screen = TownNavigationScreen(self.presenter)
        while True:
            action = nav_screen.navigate(flush_events=True, require_key_release=True)
            if not action:
                return None
            if action == "Barracks":
                self.visit_barracks()
            elif action == "Shops":
                self.visit_shop()
            elif action == "The Thirsty Dog Tavern":
                self.visit_inn()
            elif action == "Church of Elysia":
                self.visit_church()
            elif action == "Old Warehouse":
                self.visit_old_warehouse(background_draw_func=nav_screen.draw)
            elif action == "Warp Point":
                result = self.use_warp_point(background_draw_func=nav_screen.draw)
                if result == "dungeon":
                    return "dungeon"
            elif action == "Enter Dungeon":
                return self._enter_dungeon_from_town()

    @staticmethod
    def format_gameplay_statistics(player_char) -> str:
        """Return a player-facing summary of persistent gameplay counters."""
        stats = getattr(player_char, "gameplay_stats", {}) or {}

        try:
            current_level = int(getattr(getattr(player_char, "level", None), "level", 1) or 1)
        except (TypeError, ValueError):
            current_level = 1
        groups = summarize_gameplay_stat_groups(stats, current_level=current_level)
        exploration = groups["exploration"]
        combat = groups["combat"]
        records = groups["records"]

        return "\n".join(
            (
                "Adventure Statistics",
                "",
                "Exploration",
                f"Steps Taken: {exploration['steps_taken']}",
                f"Stairs Used: {exploration['stairs_used']}",
                f"Exploration Actions: {exploration['exploration_actions']}",
                "",
                "Combat",
                f"Enemies Defeated: {combat['enemies_defeated']}",
                f"Deaths: {combat['deaths']}",
                f"Flees: {combat['flees']}",
                f"Encounters Survived: {combat['encounters_survived']}",
                f"Combat Outcomes: {combat['combat_outcomes']}",
                f"Combat Survival Rate: {combat['combat_survival_rate_percent']}%",
                "",
                "Records",
                f"Total Activity: {records['total_activity']}",
                f"Highest Level Reached: {records['highest_level_reached']}",
                f"Highest Damage Dealt: {records['highest_damage_dealt']}",
                f"Highest Damage Taken: {records['highest_damage_taken']}",
            )
        )

    def show_gameplay_statistics(self, background_draw_func=None):
        """Show the player's tracked gameplay statistics."""
        message = self.format_gameplay_statistics(self.player_char)
        popup = ConfirmationPopup(self.presenter, message, show_buttons=False)
        popup.show(
            background_draw_func=background_draw_func,
            flush_events=True,
            require_key_release=True,
        )

    def _show_town_npc_dialogue(
        self, message: str, *, title: str, npc_name: str = "", background_draw_func=None
    ) -> None:
        """Show a town dialogue message with optional NPC portrait art."""
        image_path = get_npc_art_manager().get_image_path(npc_name or title)
        if hasattr(self.presenter, "show_message"):
            self.presenter.show_message(
                message,
                title=title,
                image_path=image_path,
                split_layout=True,
                background_draw_func=background_draw_func,
            )
            return

        popup = ConfirmationPopup(self.presenter, message, show_buttons=False)
        popup.show(
            background_draw_func=background_draw_func,
            flush_events=True,
            require_key_release=True,
        )

    def _footpad_class_ring_rite_config(self):
        return self.FOOTPAD_CLASS_RING_RITES.get(class_rings.class_name(self.player_char))

    def _footpad_class_ring_rite_label(self):
        config = self._footpad_class_ring_rite_config()
        return config["label"] if config else "Class Ring Job"

    def _footpad_class_ring_rite_available(self):
        class_name = class_rings.class_name(self.player_char)
        return (
            class_name in self.FOOTPAD_CLASS_RING_RITES
            and class_rings.has_visible_class_ring(self.player_char)
            and not class_rings.is_awakened(self.player_char, class_name)
        )

    def _thieves_guild_guidance(self, class_name: str) -> str:
        """Return backroom advice for the current promoted Footpad-line path."""
        guidance = {
            "Thief": (
                "Thieves keep the old tricks and learn to turn risk into money.\n\n"
                "Watch Fortune and Misfortune in combat. Theft, close calls, and bold plays feed the rhythm."
            ),
            "Rogue": (
                "Rogues win by making luck look rehearsed.\n\n"
                "Use Fortune and Misfortune deliberately, then let Loaded Dice smooth the one swing that matters."
            ),
            "Inquisitor": (
                "Inquisitors trade shadows for evidence.\n\n"
                "Inspect, Reveal, and Exploit Weakness build the case. You gave up stealth because the answer is supposed to stand in daylight."
            ),
            "Seeker": (
                "Seekers turn evidence into routes.\n\n"
                "Keep studying what hunts these halls. Revelation makes a chosen enemy readable, while Wayfinding keeps the dungeon from owning your path."
            ),
            "Assassin": (
                "Assassins prepare the end before anyone notices the beginning.\n\n"
                "Death Mark is your setup. Incapacitate, poison, and finish before the fight becomes fair."
            ),
            "Ninja": (
                "Ninjas turn initiative into disappearance.\n\n"
                "Death Mark still matters, but No-Trace Opener rewards striking first and leaving as little for the enemy to answer as possible."
            ),
            "Spell Stealer": (
                "Spell Stealers do not memorize what they can steal.\n\n"
                "Carry Blank Scrolls, use Steal Spell on enemies with magic, then cast inscribed stolen-spell scrolls from the combat Spells menu. "
                "Successful stolen-magic actions build Stolen Charge. Your next damaging spell, weapon attack, or weapon-tagged trickster skill commits that magic to an Arcane payoff."
            ),
            "Arcane Trickster": (
                "Arcane Tricksters keep the scroll racket and learn the deeper con.\n\n"
                "Blank Scroll theft still matters. Steal Spell 2 can permanently bind a new enemy spell, while stolen-scroll casting from the Spells menu feeds Stolen Charge. "
                "Stolen Charge deepens the next damaging spell, weapon attack, or weapon-tagged trickster skill with an Arcane payoff. Awakened Arcane Larceny can occasionally keep the rhythm alive after a clean release."
            ),
        }
        return guidance.get(
            class_name, "The Gray Broker has no branch ledger for your current path."
        )

    def _run_footpad_class_ring_rite(self, background_draw_func=None):
        class_name = class_rings.class_name(self.player_char)
        config = self._footpad_class_ring_rite_config()
        if not config:
            return False
        popup = ConfirmationPopup(self.presenter, config["intro"], show_buttons=False)
        popup.show(
            background_draw_func=background_draw_func,
            flush_events=True,
            require_key_release=True,
        )

        success, message = self.player_char.awaken_class_ring(class_name)
        ring = self.player_char.equipment.get("Ring")
        if success and getattr(ring, "name", None) == "Class Ring":
            ring.class_mod(self.player_char)
        popup = ConfirmationPopup(
            self.presenter,
            message.strip() or f"The Class Ring awakens through {config['label']}.",
            show_buttons=False,
        )
        popup.show(
            background_draw_func=background_draw_func,
            flush_events=True,
            require_key_release=True,
        )
        return success

    def _grant_thieves_guild_starter_kit(self):
        state = thieves_guild.ensure_state(self.player_char)
        if state.get("starter_kit_claimed"):
            return ""
        self.player_char.modify_inventory(items.Key(), num=2)
        self.player_char.modify_inventory(items.BlankScroll(), num=2)
        state["starter_kit_claimed"] = True
        return "\n\nMara slides over a starter kit: 2 Keys and 2 Blank Scrolls."

    def _offer_thieves_guild_membership(self, background_draw_func=None):
        if thieves_guild.member(self.player_char):
            self._visit_thieves_guild_backroom(background_draw_func=background_draw_func)
            return

        if not thieves_guild.can_join(self.player_char):
            self._show_town_npc_dialogue(
                "Mara Vale keeps the public ledger open and the backroom door shut.\n\n"
                '"The wares are for all but the backroom is for a select few."',
                title="Mara Vale",
                npc_name="Mara Vale",
                background_draw_func=background_draw_func,
            )
            return

        if thieves_guild.has_signet(self.player_char):
            success, message = thieves_guild.complete_membership(self.player_char)
            if success:
                self.player_char.modify_inventory(
                    items.ThievesGuildSignet(), subtract=True, rare=True
                )
                message += self._grant_thieves_guild_starter_kit()
                message += "\n\nGuild prices are now 25% lower at Mara's counter."
            self._show_town_npc_dialogue(
                message,
                title="The Gray Broker",
                npc_name="The Gray Broker",
                background_draw_func=background_draw_func,
            )
            return

        state = thieves_guild.ensure_state(self.player_char)
        if not state.get("trial_started"):
            _ok, branch = thieves_guild.start_trial(self.player_char)
            trial_wall = getattr(self.player_char, "world_dict", {}).get(
                thieves_guild.TRIAL_FAKE_WALL_POS
            )
            sync_wall = getattr(trial_wall, "sync_for_player", None)
            if callable(sync_wall):
                sync_wall(self.player_char)
            label = thieves_guild.branch_label(branch)
            message = (
                f"The Gray Broker writes one line in the black ledger: {label}.\n\n"
                "Below the old stone, a false face waits where a narrow northward approach "
                "makes liars of walls. Find the marked silence, pass through it, and bring "
                "back the Thieves Guild Signet from the examiner inside."
            )
        else:
            label = thieves_guild.branch_label(state.get("trial_branch", ""))
            message = (
                f"Your initiation remains open: {label}.\n\n"
                "Keep to the second depth. Look for the passage that denies itself from the north, "
                "and return with the Thieves Guild Signet when the examiner yields."
            )
        self._show_town_npc_dialogue(
            message,
            title="The Gray Broker",
            npc_name="The Gray Broker",
            background_draw_func=background_draw_func,
        )

    def _visit_thieves_guild_backroom(self, background_draw_func=None):
        if not thieves_guild.member(self.player_char):
            self._offer_thieves_guild_membership(background_draw_func=background_draw_func)
            return
        options = ["Class Guide", "Leave"]
        if self._footpad_class_ring_rite_available():
            options.insert(1, self._footpad_class_ring_rite_label())
        choice = 0
        if hasattr(self.presenter, "render_menu"):
            choice = self.presenter.render_menu(
                "Thieves Guild Backroom",
                options,
                split_layout=True,
                background_draw_func=background_draw_func,
            )
        selected = options[choice] if choice is not None and 0 <= choice < len(options) else "Leave"
        if selected == "Class Guide":
            class_name = getattr(getattr(self.player_char, "cls", None), "name", "")
            self._show_town_npc_dialogue(
                self._thieves_guild_guidance(class_name),
                title="The Gray Broker",
                npc_name="The Gray Broker",
                background_draw_func=background_draw_func,
            )
        elif selected == self._footpad_class_ring_rite_label():
            self._run_footpad_class_ring_rite(background_draw_func=background_draw_func)

    def visit_thieves_guild(self, background_draw_func=None):
        """Visit the public Thieves Guild shop and member backroom."""
        if self.player_char.player_level() < 10:
            popup = ConfirmationPopup(
                self.presenter,
                "Mara Vale's ledger is closed for now. Try again later.",
                show_buttons=False,
            )
            popup.show(flush_events=True, require_key_release=True)
            return

        self._play_location_music("shop")
        shop_screen = ShopScreen(self.presenter, self.player_char, "Mara Vale's Counter")
        shop_screen.set_location_portrait("Mara Vale")
        from .gui.quest_manager import QuestManager

        qm = None
        if hasattr(self.presenter, "screen"):
            qm = QuestManager(
                self.presenter,
                self.player_char,
                quest_text_renderer=lambda text: shop_screen.display_quest_text(
                    text, npc_name="Mara Vale"
                ),
                renderer_preserve_formatting=True,
            )
        options = ["Buy", "Sell"]
        if qm is not None and qm.has_available_or_active_quest("Mara Vale"):
            options.append("Quests")
        options.extend(["Ask About Backroom", "Leave"])
        shop_screen.set_options(options)

        def bg_func():
            return shop_screen.draw_all(do_flip=False)

        while True:
            choice = shop_screen.navigate_options()
            if choice is None or choice == "Leave":
                popup = ConfirmationPopup(
                    self.presenter, "Keep your keys close.", show_buttons=False
                )
                popup.show(
                    background_draw_func=bg_func, flush_events=True, require_key_release=True
                )
                return
            if choice == "Buy":
                self.shop_manager._active_shopkeeper_portrait = "Mara Vale"
                self.shop_manager._active_price_multiplier = (
                    thieves_guild.DISCOUNT_MULTIPLIER
                    if thieves_guild.member(self.player_char)
                    else 1.0
                )
                self.shop_manager.buy_thieves_guild_goods()
                self.shop_manager._active_price_multiplier = 1.0
                shop_screen.shop_message = "Mara Vale's Counter"
            elif choice == "Sell":
                self.shop_manager._active_shopkeeper_portrait = "Mara Vale"
                self.shop_manager._active_price_multiplier = 1.0
                self.shop_manager.sell_items()
                shop_screen.shop_message = "Mara Vale's Counter"
            elif choice == "Quests":
                if qm is not None:
                    qm.check_and_offer("Mara Vale")
            elif choice == "Ask About Backroom":
                if not thieves_guild.member(self.player_char) and not thieves_guild.can_join(
                    self.player_char
                ):
                    shop_screen.display_quest_text(
                        "Mara Vale keeps the public ledger open and the backroom door shut.\n\n"
                        '"The wares are for all but the backroom is for a select few."',
                        title="Mara Vale",
                    )
                    shop_screen.draw_all()
                    continue
                self._offer_thieves_guild_membership(
                    background_draw_func=background_draw_func or bg_func
                )

    def visit_old_warehouse(self, background_draw_func=None):
        """Handle Old Warehouse entry guard dialogue."""
        self._show_town_npc_dialogue(
            'A warehouse guard steps into your path.\n\n"Authorized personnel only. Please leave."',
            title="Old Warehouse Guard",
            npc_name="Old Warehouse Guard",
            background_draw_func=background_draw_func,
        )
        return False

    def use_warp_point(self, background_draw_func=None):
        """Use the warp point to teleport to dungeon level 5."""
        from src.core.classes import wizard

        research_message = wizard.consult_ultimate_research(self.player_char)
        if research_message:
            research_popup = ConfirmationPopup(
                self.presenter,
                research_message,
                show_buttons=False,
            )
            research_popup.show(**self._popup_show_kwargs(background_draw_func))
        prompt = (
            "Two field scientists stand beside the brass-ringed platform, "
            "checking gauges that hum with blue light.\n\n"
            f'"Hello, {self.player_char.name}."\n\n'
            "Do you want to warp down to level 5?"
        )
        if hasattr(self.presenter, "render_menu"):
            confirmed = (
                self.presenter.render_menu(
                    prompt,
                    ["Yes", "No"],
                    split_layout=True,
                    background_draw_func=background_draw_func,
                )
                == 0
            )
        else:
            confirm = ConfirmationPopup(self.presenter, prompt)
            confirmed = confirm.show(**self._popup_show_kwargs(background_draw_func))

        if confirmed:
            # Mark the destination as visited
            if (3, 0, 5) in self.player_char.world_dict:
                if not self.player_char.world_dict[(3, 0, 5)].visited:
                    self.player_char.world_dict[(3, 0, 5)].visited = True
                    # Mark adjacent tiles as near
                    for dx, dy in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
                        adj_pos = (3 + dx, 0 + dy, 5)
                        if adj_pos in self.player_char.world_dict:
                            self.player_char.world_dict[adj_pos].near = True

                # Mark as warped
                self.player_char.world_dict[(3, 0, 5)].warped = True

            popup = ConfirmationPopup(
                self.presenter,
                "The scientists throw their levers in sequence.\n"
                "You step into the warp point,\n"
                "taking you deep into the dungeon.",
                show_buttons=False,
            )
            popup.show(**self._popup_show_kwargs(background_draw_func))

            # Warp player to level 5
            self.player_char.location_x = 3
            self.player_char.location_y = 0
            self.player_char.location_z = 5
            self.player_char.facing = "south"

            # Return to dungeon
            return "dungeon"
        else:
            popup = ConfirmationPopup(
                self.presenter,
                "Not a problem, come back when you change your mind.",
                show_buttons=False,
            )
            popup.show(**self._popup_show_kwargs(background_draw_func))

    def visit_shop(self):
        """Visit the town shop - routes to appropriate shop via ShopManager."""
        self._play_location_music("shop")
        shop_options = ["Blacksmith", "Alchemist", "Jeweler", "Magic Shop", "Thieves Guild"]
        shop_options.append("Go Back")

        # Create shop selection screen
        shop_screen = ShopSelectionScreen(self.presenter)

        while True:
            choice = shop_screen.navigate(
                shop_options,
                flush_events=True,
                require_key_release=True,
            )

            if choice is None or choice == len(shop_options) - 1:  # Go Back
                break
            choice_label = shop_options[choice]

            if choice_label == "Blacksmith":
                self.shop_manager.visit_blacksmith()
            elif choice_label == "Alchemist":
                self.shop_manager.visit_alchemist()
            elif choice_label == "Jeweler":
                self.shop_manager.visit_jeweler()
            elif choice_label == "Magic Shop":
                self.shop_manager.visit_magic_shop()
            elif choice_label == "Thieves Guild":
                self.visit_thieves_guild()

    def visit_church(self):
        """Visit the Church - managed by ChurchManager."""
        self._play_location_music("church")
        self.church_manager.visit_church()

    def visit_barracks(self):
        """Visit the Barracks - managed by BarracksManager."""
        self._play_location_music("town")
        self.barracks_manager.visit_barracks()

    def visit_ancient_grove(self):
        """Visit the Archdruid Ancient Grove."""
        self._play_location_music("town")
        if not archdruid.grove_unlocked(self.player_char):
            popup = ConfirmationPopup(
                self.presenter, "The path to the Ancient Grove is hidden.", show_buttons=False
            )
            popup.show(**self._popup_show_kwargs())
            return

        while True:
            state = self.player_char.ensure_archdruid_attunement()
            options = ["Review Balance"]
            options.extend(
                f"{affinity} Ritual"
                for affinity in archdruid.AFFINITIES
                if not state["aspects"][affinity]
            )
            options.append("Leave")
            choice = self.presenter.render_menu("Ancient Grove", options)
            if choice is None or options[choice] == "Leave":
                return
            selected = options[choice]
            if selected == "Review Balance":
                attunement = ", ".join(
                    f"{affinity} {state['attunement'][affinity]}"
                    for affinity in archdruid.AFFINITIES
                )
                text = f"Attunement: {attunement}\nAspects: {archdruid.aspect_summary(self.player_char)}"
                popup = ConfirmationPopup(self.presenter, text, show_buttons=False)
                popup.show(**self._popup_show_kwargs())
                continue

            affinity = selected.replace(" Ritual", "")
            success, message = archdruid.perform_ritual(self.player_char, affinity)
            ring = self.player_char.equipment.get("Ring")
            if success and getattr(ring, "name", None) == "Class Ring":
                ring.class_mod(self.player_char)
            popup = ConfirmationPopup(self.presenter, message.strip(), show_buttons=False)
            popup.show(**self._popup_show_kwargs())

    def visit_inn(self):
        """Visit the Inn/Tavern - managed by InnManager."""
        self._play_location_music("inn")
        self.inn_manager.visit_inn()

    def enter_dungeon(self):
        """Enter first-person dungeon exploration mode."""
        self._play_location_music("dungeon")
        # Use DungeonManager for exploration
        self.dungeon_manager.explore_dungeon()

        if hasattr(self.presenter, "set_background_provider"):
            self.presenter.set_background_provider(None)

        # After exiting dungeon (returned to town, quit, etc.)
        # Check if player quit the game
        if self.player_char.quit:
            return
        in_town = getattr(self.player_char, "in_town", None)
        if callable(in_town) and in_town():
            self._play_location_music("town")

    def show_character_info(self):
        """Display character information using the character screen."""
        char_screen = ModernCharacterScreen(self.presenter)

        while True:
            choice = char_screen.navigate(self.player_char)

            if choice == "Exit Menu":
                break

    def save_game(self):
        """Save the current game."""
        filename = f"{str(self.player_char.name).lower()}.save"

        if SaveManager.save_player(self.player_char, filename):
            self.presenter.show_message(
                f"Game saved successfully!\n\nSaved to: {USER_SAVE_DIR / filename}"
            )
            self.load_files = SaveManager.list_saves()
        else:
            self.presenter.show_message("Save failed. Please try again.")

    def cleanup(self):
        """Clean up resources."""
        try:
            self.presenter.cleanup()
        finally:
            if hasattr(self.presenter, "set_background_provider"):
                self.presenter.set_background_provider(None)
            pygame.quit()


def main() -> int:
    """Entry point for GUI game."""
    import argparse

    parser = argparse.ArgumentParser(description="The Forsaken Tenet GUI Game")
    parser.add_argument(
        "--debug", action="store_true", help="Enable debug mode (disable random combat)"
    )
    parser.add_argument(
        "--character-menu",
        action="store_true",
        help="Launch directly into Character Menu using a default Human Warrior character",
    )
    parser.add_argument(
        "--town-navigation",
        action="store_true",
        help="Launch directly into the optional Explore Town prototype using a default Human Warrior character",
    )
    parser.add_argument(
        "--preview-name",
        default="Menu Preview",
        help="Character name used with --character-menu or --town-navigation (default: Menu Preview)",
    )
    parser.add_argument(
        "--smoke-test",
        action="store_true",
        help="Validate packaged resources and headless startup, then exit",
    )
    parser.add_argument(
        "--remote-playtest-controls",
        action="store_true",
        help="Enable on-screen dungeon controls for touch and remote playtesting",
    )
    parser.add_argument(
        "--remote-playtest-input-diagnostics",
        action="store_true",
        help="Print dungeon touch/mouse press events (requires --remote-playtest-controls)",
    )
    parser.add_argument(
        "--remote-playtest-performance-diagnostics",
        action="store_true",
        help="Print periodic dungeon render/cache timings (requires --remote-playtest-controls)",
    )
    parser.add_argument(
        "--fullscreen", action="store_true", help="Use the landscape logical fullscreen display"
    )
    args = parser.parse_args()

    install_signal_handlers()
    if args.smoke_test:
        try:
            runtime_smoke_check()
        except Exception as error:
            print(f"Startup smoke test failed: {error}", file=sys.stderr)
            return 1
        print("Startup smoke test passed.")
        return 0

    game = None
    try:
        if args.remote_playtest_input_diagnostics and not args.remote_playtest_controls:
            parser.error("--remote-playtest-input-diagnostics requires --remote-playtest-controls")
        if args.remote_playtest_performance_diagnostics and not args.remote_playtest_controls:
            parser.error(
                "--remote-playtest-performance-diagnostics requires --remote-playtest-controls"
            )
        game_kwargs = {"debug_mode": args.debug}
        if args.fullscreen:
            game_kwargs["fullscreen"] = True
        if args.remote_playtest_controls:
            game_kwargs["remote_playtest_controls"] = True
            if args.remote_playtest_input_diagnostics:
                game_kwargs["remote_playtest_input_diagnostics"] = True
            if args.remote_playtest_performance_diagnostics:
                game_kwargs["remote_playtest_performance_diagnostics"] = True
        game = PygameGame(**game_kwargs)
        if args.character_menu:
            game.player_char = game.create_default_character(name=args.preview_name)
            game.initialize_managers()
            game.show_character_info()
        elif args.town_navigation:
            game.player_char = game.create_default_character(name=args.preview_name)
            game.initialize_managers()
            result = game.explore_town_prototype()
            if result == "dungeon":
                game.enter_dungeon()
        else:
            game.main_menu()
    except KeyboardInterrupt:
        print("\nGame interrupted by user")
        return 130
    except Exception as e:
        print(f"Fatal startup error: {e}", file=sys.stderr)
        import traceback

        traceback.print_exc()
        return 1
    finally:
        if game is not None:
            game.cleanup()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
