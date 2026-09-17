"""Core behavior for the dungeon manager package."""

import logging
import random
import sys
from pathlib import Path

import pygame

from src.core import map_tiles
from src.core.data.data_loader import get_special_events
from src.paths import PYGAME_ASSETS_DIR
from src.ui_pygame.assets.npc_art_manager import get_npc_art_manager

from ..combat_manager.manager import GUICombatManager
from ..dungeon_hud import DungeonHUD
from ..dungeon_playtest_controls import DungeonPlaytestControls
from ..dungeon_renderer import DungeonRenderer
from ..loot_popup import LootPopup

logger = logging.getLogger(__name__)


_FINAL_DUNGEON_LEVEL = 6
_FUNHOUSE_LEVEL = 7


class DungeonCoreMixin:
    def __init__(
        self, presenter, player_char, game_instance, *, remote_playtest_controls: bool = False
    ):
        self.presenter = presenter
        self.player_char = player_char
        self.game = game_instance

        # Cache for dungeon background (used for loading screen & character menu)
        self._dungeon_background = None
        self._dungeon_background_loaded = False

        # Initialize renderer and HUD
        self.renderer = DungeonRenderer(presenter)
        self.hud = DungeonHUD(presenter)

        # Initialize combat manager
        self.combat_manager = GUICombatManager(presenter, self.hud, game_instance)
        # Give combat manager access to dungeon renderer for in-place combat
        self.combat_manager.dungeon_renderer = self.renderer

        # Initialize character screen lazily so dungeon backgrounds can be applied.
        self.character_screen = None

        # Initialize loot popup
        self.loot_popup = LootPopup(presenter.screen, presenter)

        # Import shop manager (lazy import to avoid circular dependencies)
        from ..shops import ShopManager

        self.shop_manager = ShopManager(presenter, player_char)

        # Import ultimate armor shop
        from ..ultimate_armor import UltimateArmorShop

        self.ultimate_armor_shop = UltimateArmorShop(presenter)

        # Message log
        self.messages = []
        self.max_messages = 50
        self.message_lines_per_page = 4
        self.message_scroll_offset = 0

        # Control state
        self.running = True
        self._navigation_input_suppressed_until = 0
        self._navigation_keys_awaiting_release: set[int] = set()
        self.playtest_controls = (
            DungeonPlaytestControls(presenter) if remote_playtest_controls else None
        )

        # --- Render throttling / caching ---
        # The 3D view is expensive; only redraw it when something actually changes.
        self.view_dirty = True
        self.ui_dirty = True
        self._render_error_logged = False
        self._cached_view = None  # pygame.Surface
        self._cached_frame = None  # pygame.Surface
        self._next_anim_tick = 0
        self._anim_interval_ms = 120  # torch flicker / subtle view effects

        # Load dungeon background for in-dungeon popups and character menu.
        self._load_dungeon_background()

        if hasattr(self.presenter, "set_background_provider"):
            self.presenter.set_background_provider(self._get_popup_background)

    @staticmethod
    def _resolve_tile_enemy(tile):
        """Return a concrete enemy instance for a tile, instantiating stored classes if needed."""
        if not hasattr(tile, "enemy"):
            return None

        enemy = tile.enemy
        if not enemy:
            return None

        if callable(enemy) and not hasattr(enemy, "name"):
            enemy = enemy()
            tile.enemy = enemy

        return enemy

    def _get_popup_background(self):
        if self._cached_frame is not None:
            return self._cached_frame
        if self._cached_view is not None:
            return self._cached_view
        return self.presenter.screen.copy()

    def _sync_dungeon_music(self) -> None:
        """Select the exploration theme matching the player's current dungeon area."""
        level = self.player_char.location_z
        if level == map_tiles.REALM_OF_CAMBION_LEVEL:
            location = "realm_of_cambion"
        elif level == _FUNHOUSE_LEVEL:
            location = "funhouse"
        elif level == _FINAL_DUNGEON_LEVEL:
            location = "dungeon_final"
        else:
            location = "dungeon"

        play_location_music = getattr(self.game, "_play_location_music", None)
        if callable(play_location_music):
            play_location_music(location)

    def _get_character_screen(self):
        if self.character_screen is None:
            from ..modern_character_screen.screen import ModernCharacterScreen

            self.character_screen = ModernCharacterScreen(self.presenter)
            if self._dungeon_background is not None:
                self.character_screen.background = self._dungeon_background
        return self.character_screen

    def add_message(self, message: str):
        """Add a message to the message log."""
        was_at_bottom = self.message_scroll_offset >= self._max_message_scroll()
        # Split long messages into multiple lines if needed
        max_length = 60
        if len(message) > max_length:
            words = message.split()
            lines = []
            current_line = ""
            for word in words:
                if len(current_line) + len(word) + 1 <= max_length:
                    current_line += word + " "
                else:
                    if current_line:
                        lines.append(current_line.strip())
                    current_line = word + " "
            if current_line:
                lines.append(current_line.strip())
            for line in lines:
                self.messages.append(line)
        else:
            self.messages.append(message)

        # Keep only last max_messages
        if len(self.messages) > self.max_messages:
            self.messages = self.messages[-self.max_messages :]

        if was_at_bottom:
            self.message_scroll_offset = self._max_message_scroll()
        else:
            self.message_scroll_offset = min(self.message_scroll_offset, self._max_message_scroll())

        # Messages affect the UI overlay.
        self.ui_dirty = True

    def _play_sfx(self, sound_name: str):
        """Play a sound effect when the presenter has an audio manager."""
        sound_manager = getattr(self.presenter, "sound_manager", None)
        if sound_manager is not None and hasattr(sound_manager, "play_sfx"):
            sound_manager.play_sfx(sound_name)

    def _max_message_scroll(self) -> int:
        return max(0, len(self.messages) - self.message_lines_per_page)

    def scroll_message_log(self, delta: int):
        """Scroll dungeon navigation log by delta lines (negative=older, positive=newer)."""
        self.message_scroll_offset = max(
            0, min(self._max_message_scroll(), self.message_scroll_offset + delta)
        )
        self.ui_dirty = True

    def reset_message_log(self):
        """Clear navigation history and reset scroll state."""
        self.messages = []
        self.message_scroll_offset = 0
        self.ui_dirty = True

    def get_current_tile(self):
        """Return the tile the player is currently standing on."""
        return self.player_char.world_dict.get(
            (self.player_char.location_x, self.player_char.location_y, self.player_char.location_z)
        )

    def _check_random_cry(self):
        """
        Check if player should hear random cries on floor 2 during "Something to Cry About" quest.
        Cries get louder as player gets closer to the dead body location.
        """
        # Only trigger on floor 2 (location_z == 2)
        if self.player_char.location_z != 2:
            return

        # Check if quest "Something to Cry About" is active and not completed
        if "Something to Cry About" not in self.player_char.quest_dict.get("Side", {}):
            return

        if self.player_char.quest_dict["Side"]["Something to Cry About"].get("Completed"):
            return

        # Dead body is at approximately (18, 12, 2) - you can adjust these coords if needed
        dead_body_x, dead_body_y = 18, 12
        player_x = self.player_char.location_x
        player_y = self.player_char.location_y

        # Calculate distance to dead body
        distance = ((player_x - dead_body_x) ** 2 + (player_y - dead_body_y) ** 2) ** 0.5

        # Only trigger if within 30 tiles of dead body
        if distance > 30:
            return

        # Random chance increases as player gets closer
        # At 5 tiles: 60% chance, at 10 tiles: 40% chance, at 20 tiles: 20% chance
        base_chance = max(0.1, (30 - distance) / 50)  # Scales from 10% to 60%

        if random.random() > base_chance:
            return

        # Generate cry message based on distance
        cries = [
            "*Heart-wrenching sobs echo through the dungeon...*",
            "*A mournful wail reverberates in the distance...*",
            "*The anguished cry of a broken soul pierces the air...*",
            "*You hear desperate weeping somewhere nearby...*",
            "*A wail of grief and despair fills the dungeon...*",
            "*Anguished sobbing echoes through the corridors...*",
        ]

        cry = random.choice(cries)
        self.add_message(cry)

    def _animate_nimue_materialization(self):
        """Animate Nimue's sprite materializing from the spring."""
        nimue_path = PYGAME_ASSETS_DIR / "sprites" / "npcs" / "nimue.png"

        if not nimue_path.exists():
            # Sprite not found, skip animation
            return

        try:
            nimue_sprite = pygame.image.load(nimue_path).convert_alpha()
        except Exception:
            # Failed to load sprite, skip animation
            return

        # Scale sprite to reasonable size (512x512)
        sprite_width = 512
        sprite_height = 768
        nimue_sprite = pygame.transform.scale(nimue_sprite, (sprite_width, sprite_height))

        screen = self.presenter.screen
        clock = pygame.time.Clock()

        # Animation parameters
        duration_ms = 2000  # 2 seconds for materialization
        start_time = pygame.time.get_ticks()

        while True:
            now = pygame.time.get_ticks()
            elapsed = now - start_time
            progress = min(1.0, elapsed / duration_ms)

            # Render current dungeon view as background
            self._render()

            # Draw dimming overlay
            overlay = pygame.Surface((self.presenter.width, self.presenter.height), pygame.SRCALPHA)
            overlay.fill((0, 0, 0, int(100 * progress)))  # Slight darkening
            screen.blit(overlay, (0, 0))

            # Calculate sprite alpha and scale (materialization effect)
            # Start from 0 alpha and scale from smaller to full size
            alpha = int(255 * progress)
            scale_start = 0.5  # Start at 50% size
            scale = scale_start + (1.0 - scale_start) * progress

            # Create scaled sprite with alpha
            scaled_sprite = pygame.transform.scale(
                nimue_sprite, (int(sprite_width * scale), int(sprite_height * scale))
            )
            scaled_sprite.set_alpha(alpha)

            # Center sprite on the dungeon view area (not the entire screen)
            # Dungeon view is 65% of width on the left side
            view_width = int(self.presenter.width * 0.65)
            sprite_rect = scaled_sprite.get_rect(
                center=(view_width // 2, self.presenter.height // 2)
            )
            screen.blit(scaled_sprite, sprite_rect)

            pygame.display.flip()

            # Check for quit events
            for _ in pygame.event.get(pygame.QUIT):
                pygame.quit()
                sys.exit()

            if progress >= 1.0:
                break
            clock.tick(60)

        # Brief pause to let animation complete
        pygame.time.wait(500)

    def _dungeon_dialog_background(self):
        """Draw current dungeon frame as dialogue background."""
        self._render()

    def _draw_cached_popup_background(self):
        """Draw the latest cached dungeon frame for lightweight popups."""
        self.presenter.screen.blit(self._get_popup_background(), (0, 0))

    def _show_dungeon_dialogue(self, message: str, title: str = "", image_path: str = ""):
        """Show split dialogue panel with optional NPC image on the left."""
        image_path = image_path or get_npc_art_manager().get_image_path(title)
        self.presenter.show_message(
            message,
            title=title,
            image_path=image_path,
            split_layout=True,
            background_draw_func=self._dungeon_dialog_background,
        )

    def _show_dungeon_choice(self, prompt: str, options: list[str], image_path: str = ""):
        """Show split choice panel with optional NPC image on the left."""
        return self.presenter.render_menu(
            prompt,
            options,
            image_path=image_path,
            split_layout=True,
            background_draw_func=self._dungeon_dialog_background,
        )

    def _show_special_event_dialogue(self, event_name: str, title: str = "", image_path: str = ""):
        """Show special event text using split dialogue layout."""
        try:
            lines = get_special_events().get(event_name, {}).get("Text", [])
            message = (
                " ".join(line.strip() for line in lines if line is not None).strip()
                if lines
                else event_name
            )
        except Exception:
            message = event_name
        image_path = image_path or get_npc_art_manager().get_image_path(title or event_name)
        self.presenter.show_message(
            message,
            title=title or event_name,
            image_path=image_path,
            split_layout=True,
            background_draw_func=self._dungeon_dialog_background,
            min_display_seconds=2.0,
        )

    def _npc_image_path(self, filename: str) -> str:
        """Return the stable absolute path for an NPC portrait asset."""
        return str(PYGAME_ASSETS_DIR / "sprites" / "npcs" / filename)

    def _enemy_combat_sprite_image_path(self, filename: str) -> str:
        """Return the stable absolute path for an enemy combat sprite asset."""
        return str(PYGAME_ASSETS_DIR / "enemy_combat_sprites" / filename)

    def _enemy_dialogue_image_path(self, enemy) -> str:
        """Return the best available combat sprite path for boss dialogue."""
        picture = getattr(enemy, "picture", "")
        if isinstance(picture, str) and picture.lower().endswith(".png"):
            return self._enemy_combat_sprite_image_path(Path(picture).name)
        try:
            from src.ui_pygame.assets.enemy_combat_sprite_manager import (
                get_enemy_combat_sprite_manager,
            )

            manager = get_enemy_combat_sprite_manager()
            sprite_key = manager.get_sprite_key_for_enemy(enemy)
            sprite_path = manager.sprite_root / f"{sprite_key}.png"
            if sprite_path.exists():
                return str(sprite_path)
        except Exception:
            pass
        name = str(getattr(enemy, "name", "boss")).lower().replace(" ", "_")
        return self._enemy_combat_sprite_image_path(f"{name}.png")

    def _show_boss_intro_dialogue(self, boss_tile, enemy) -> None:
        """Show boss introduction text in the split NPC-style dialogue window."""
        try:
            lines = get_special_events().get(enemy.name, {}).get("Text", [])
            message = " ".join(line.strip() for line in lines if line is not None).strip()
        except Exception:
            message = ""
        if not message:
            try:
                message = boss_tile.intro_text(self.game)
            except Exception:
                message = f"{enemy.name} stands before you."
        if message:
            self._show_dungeon_dialogue(
                message,
                title=getattr(enemy, "name", "Boss"),
                image_path=self._enemy_dialogue_image_path(enemy),
            )
            if hasattr(boss_tile, "read"):
                boss_tile.read = True

    def _handle_defeated_jester_boss(self, boss_tile) -> None:
        """Resolve the funhouse immediately after the Jester is defeated."""
        if type(boss_tile).__name__ != "JesterBossRoom" or self.player_char.location_z != 7:
            return
        boss_tile.defeated = True
        boss_tile.enemy = None
        self._show_special_event_dialogue(
            "Jester Defeated",
            title="Jester Defeated",
            image_path=self._enemy_combat_sprite_image_path("jester.png"),
        )
        self._return_player_to_funhouse_teleporter()
        self._cached_view = None
        self._cached_frame = None
        self._mark_view_dirty()
        self.add_message("The funhouse dissolves behind you.")

    def _return_player_to_funhouse_teleporter(self) -> None:
        """Place the player back on the level 4 funhouse teleporter."""
        map_tiles.deactivate_funhouse_teleporters(self.player_char)
        for (x, y, z), tile in getattr(self.player_char, "world_dict", {}).items():
            if z == 4 and type(tile).__name__ == "FunhouseTeleporter":
                self.player_char.location_x = x
                self.player_char.location_y = y
                self.player_char.location_z = z
                self.player_char.facing = "south"
                self.player_char.funhouse_return = None
                self._sync_dungeon_music()
                return
        if hasattr(self.player_char, "exit_funhouse"):
            self.player_char.exit_funhouse()
            self._sync_dungeon_music()

    def _load_dungeon_background(self):
        """Load and scale the dungeon background once."""
        if self._dungeon_background_loaded:
            return self._dungeon_background

        self._dungeon_background_loaded = True
        bg_path = PYGAME_ASSETS_DIR / "backgrounds" / "dungeon.png"

        if bg_path.exists():
            try:
                bg_image = pygame.image.load(bg_path).convert()
                bg_width, bg_height = bg_image.get_size()
                scale_x = self.presenter.width / bg_width
                scale_y = self.presenter.height / bg_height
                scale = max(scale_x, scale_y)

                new_width = int(bg_width * scale)
                new_height = int(bg_height * scale)
                self._dungeon_background = pygame.transform.scale(bg_image, (new_width, new_height))
            except Exception as exc:
                print(f"Warning: Could not load dungeon background: {exc}")
                self._dungeon_background = None
        else:
            print(f"Warning: Dungeon background not found at {bg_path}")
            self._dungeon_background = None

        return self._dungeon_background

    def _show_dungeon_loading_screen(self, message: str, duration: float = 1.25):
        """Display a short fake-loading screen with progress bar."""
        bg = self._load_dungeon_background()
        screen = self.presenter.screen
        clock = pygame.time.Clock()

        start_ms = pygame.time.get_ticks()
        end_ms = start_ms + int(duration * 1000)

        while True:
            now = pygame.time.get_ticks()
            progress = min(1.0, (now - start_ms) / max(1, end_ms - start_ms))

            # Draw background + dim overlay
            if bg:
                bg_rect = bg.get_rect(
                    center=(self.presenter.width // 2, self.presenter.height // 2)
                )
                screen.blit(bg, bg_rect)
            else:
                screen.fill((0, 0, 0))

            overlay = pygame.Surface((self.presenter.width, self.presenter.height), pygame.SRCALPHA)
            overlay.fill((0, 0, 0, 170))
            screen.blit(overlay, (0, 0))

            # Title text
            text = self.presenter.title_font.render(message, True, (255, 255, 255))
            text_rect = text.get_rect(
                center=(self.presenter.width // 2, self.presenter.height // 2 - 40)
            )
            screen.blit(text, text_rect)

            # Progress bar
            bar_width = self.presenter.width // 2
            bar_height = 24
            bar_x = (self.presenter.width - bar_width) // 2
            bar_y = self.presenter.height // 2 + 10

            border_rect = pygame.Rect(bar_x, bar_y, bar_width, bar_height)
            fill_rect = pygame.Rect(
                bar_x + 3, bar_y + 3, int((bar_width - 6) * progress), bar_height - 6
            )

            pygame.draw.rect(screen, (220, 220, 220), border_rect, 2)
            pygame.draw.rect(screen, (218, 165, 32), fill_rect)

            # Percent text
            percent_text = self.presenter.small_font.render(
                f"{int(progress * 100)}%", True, (255, 255, 255)
            )
            percent_rect = percent_text.get_rect(
                center=(self.presenter.width // 2, bar_y + bar_height + 16)
            )
            screen.blit(percent_text, percent_rect)

            pygame.display.flip()

            # Keep window responsive
            for event in pygame.event.get(pygame.QUIT):
                pygame.quit()
                sys.exit()

            if progress >= 1.0:
                break

            clock.tick(60)

    def _show_town_entry_loading_screen(self, message: str = "Returning to town...") -> None:
        """Display the shared transition screen before control returns to town."""
        try:
            self._detach_dungeon_background_provider()
            self._show_dungeon_loading_screen(message)
            self._cached_view = None
            self.view_dirty = False
            self.ui_dirty = False
        except Exception as exc:
            logger.warning("Could not show town loading screen: %s", exc)

    def _mark_view_dirty(self):
        """Mark the 3D view and UI overlays to redraw next frame."""
        self.view_dirty = True
        self.ui_dirty = True

    def _refresh_cached_frame(self):
        """Ensure cached background reflects the current tile before popups/combat."""
        if self.view_dirty or self.ui_dirty or self._cached_view is None:
            self._render()

    def _detach_dungeon_background_provider(self) -> None:
        """Prevent town UI from sampling dungeon backgrounds after dungeon exit."""
        if hasattr(self.presenter, "set_background_provider"):
            self.presenter.set_background_provider(None)
