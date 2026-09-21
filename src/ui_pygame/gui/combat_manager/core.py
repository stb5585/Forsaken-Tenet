"""Core behavior for the combat manager package."""

from __future__ import annotations

import datetime
import random
import sys
from pathlib import Path
from typing import TYPE_CHECKING, Any

import pygame

from src.core import enemies, main_story
from src.core.character import Character
from src.core.classes import ability_mechanics, promotion_kits
from src.core.combat.battle_engine import BattleEngine
from src.core.combat.battle_logger import BattleLogger
from src.core.player import LIMINAL_GAP_ENTRY_FACING, LIMINAL_GAP_ENTRY_POS, Player
from src.paths import DEBUG_LOGS_DIR
from src.ui_pygame.screen_runtime import get_events

from ..combat_view.view import CombatView
from ..input_guards import (
    prepare_guarded_input,
    release_guard_allows_input,
    update_input_armed_from_event,
)
from ..level_up import LevelUpScreen
from ..mouse_helpers import hit_index, is_left_click, mouse_position
from .constants import (
    SLOT_CARD_DECK,
    SLOT_CARD_ORDER,
    SLOT_CARD_SUITS,
    SLOT_CARD_VALUES,
    SLOT_SYMBOL_ATLAS,
    VESPERION_FALSE_FINAL_HP_RATIO,
)
from .helpers import _battle_log_slug

if TYPE_CHECKING:
    from src.ui_pygame.gui.dungeon_hud import DungeonHUD
    from src.ui_pygame.presentation.pygame_presenter import PygamePresenter


class CombatManagerCoreMixin:
    def __init__(self, presenter: PygamePresenter, hud: DungeonHUD, game: Any):
        self.presenter = presenter
        self.screen = presenter.screen
        self.hud = hud
        self.game = game
        self.combat_view = CombatView(self.screen, presenter)
        self.level_up_screen = LevelUpScreen(self.screen, presenter)
        self.logger = BattleLogger()
        self.running = False
        self.engine: BattleEngine | None = None
        # References to dungeon rendering (set by dungeon_manager)
        self.dungeon_renderer = None
        self.player_world_dict = None
        self._combat_background = None
        self._last_combat_timeline = ()
        self.available_actions = []
        self._slot_symbol_cache = None
        self._debug_auto_kill_hint_shown = False

    def _capture_background(self):
        if hasattr(self.presenter, "get_background_surface"):
            try:
                surface = self.presenter.get_background_surface()
                if surface is not None:
                    return surface
            except Exception:
                pass
        return self.screen.copy()

    def _debug_mode_enabled(self) -> bool:
        """Return whether debug-only combat tools should be exposed."""
        return bool(
            getattr(self.game, "debug_mode", False) or getattr(self.presenter, "debug_mode", False)
        )

    @staticmethod
    def _controller_key(event):
        """Map the supported controller parity controls onto combat key semantics."""
        if event.type == pygame.JOYHATMOTION:
            value = getattr(event, "value", (0, 0))
            mapping = {
                (0, 1): pygame.K_UP,
                (0, -1): pygame.K_DOWN,
                (-1, 0): pygame.K_LEFT,
                (1, 0): pygame.K_RIGHT,
            }
            return mapping.get(value)
        if event.type != pygame.JOYBUTTONDOWN:
            return None
        return {
            0: pygame.K_RETURN,  # A: confirm
            1: pygame.K_ESCAPE,  # B: back
            2: pygame.K_x,  # X: resource details
            3: pygame.K_y,  # Y: All Actions
            4: pygame.K_q,  # LB: previous hostile lane
            5: pygame.K_e,  # RB: next hostile lane
        }.get(getattr(event, "button", -1))

    def _show_combat_resource_details(self, player_char) -> None:
        """Expose text-complete resource detail without committing an action."""
        from src.core.combat.action_interface import combat_interface_snapshot

        if self.engine is None:
            return
        resources = combat_interface_snapshot(self.engine, player_char).resources
        if not resources:
            self.combat_view.add_combat_message("No class resources are active.")
            return
        for resource in resources:
            detail = resource.state_text or ("Ready" if resource.ready else "Inactive")
            self.combat_view.add_combat_message(f"{resource.label}: {detail}")

    def _slot_symbol_surfaces(self) -> list[pygame.Surface]:
        """Load and slice the slot-machine symbol atlas."""
        if self._slot_symbol_cache is not None:
            return self._slot_symbol_cache

        symbols: list[pygame.Surface] = []
        try:
            atlas = pygame.image.load(str(SLOT_SYMBOL_ATLAS))
            atlas_w, atlas_h = atlas.get_size()
            full_deck_grid = (
                atlas_w % 13 == 0 and atlas_h % 4 == 0 and atlas_w // 13 == atlas_h // 4
            )
            columns = 13 if full_deck_grid else 5
            rows = 4 if full_deck_grid else 2
            cell_w = atlas_w // columns
            cell_h = atlas_h // rows
            for index in range(columns * rows):
                col = index % columns
                row = index // columns
                rect = pygame.Rect(col * cell_w, row * cell_h, cell_w, cell_h)
                symbol = atlas.subsurface(rect).copy()
                bounds = symbol.get_bounding_rect(min_alpha=1)
                if bounds.width and bounds.height and bounds.size != symbol.get_size():
                    cropped = symbol.subsurface(bounds).copy()
                    padding = 6
                    padded = pygame.Surface(
                        (cropped.get_width() + padding * 2, cropped.get_height() + padding * 2),
                        pygame.SRCALPHA,
                    )
                    padded.blit(cropped, (padding, padding))
                    symbol = padded
                symbols.append(symbol)
        except Exception:
            symbols = []
        self._slot_symbol_cache = symbols
        return symbols

    @staticmethod
    def _slot_machine_result_label(spin: str) -> str:
        """Return the visible Slot Machine hand name for a spin."""
        cards = CombatManagerCoreMixin._parse_slot_cards(spin)
        if cards:
            ranks = [rank for rank, _suit in cards]
            suits = [suit for _rank, suit in cards]
            values = sorted(SLOT_CARD_VALUES[rank] for rank in ranks)
            low_ace_values = sorted(1 if rank == "A" else SLOT_CARD_VALUES[rank] for rank in ranks)
            flush = len(set(suits)) == 1
            straight = (
                values[1] == values[0] + 1 and values[2] == values[1] + 1
            ) or low_ace_values == [1, 2, 3]
            if flush and straight:
                return "Straight Flush"
            if len(set(ranks)) == 1:
                return "3 of a Kind"
            if straight:
                return "Straight"
            if flush:
                return "Flush"
            if len(set(ranks)) == 2:
                return "Pair"
            return "Chance"

        if spin in {"666", "999"}:
            return "Death"
        if spin in {"000", "111", "222", "333", "444", "555", "777", "888"}:
            return "3 of a Kind"
        if "".join(sorted(spin)) in {"012", "123", "234", "345", "456", "567", "678", "789"}:
            return "Straight"
        if len(spin) == 3 and spin[0] == spin[2] and spin[0] != spin[1]:
            return "Palindrome"
        if len(set(spin)) == 2:
            return "Pairs"
        if all(int(digit) % 2 == 0 for digit in spin):
            return "Evens"
        if all(int(digit) % 2 == 1 for digit in spin):
            return "Odds"
        return "Chance"

    @staticmethod
    def _parse_slot_cards(spin: str) -> list[tuple[str, str]] | None:
        if not isinstance(spin, str) or "," not in spin:
            return None
        cards: list[tuple[str, str]] = []
        for raw_card in spin.split(","):
            card = raw_card.strip().upper()
            rank = card[:-1]
            suit = card[-1:] if card else ""
            if rank not in SLOT_CARD_VALUES or suit not in SLOT_CARD_SUITS:
                return None
            cards.append((rank, suit))
        if len(cards) != 3 or len(set(cards)) != 3:
            return None
        return cards

    def _handle_combat_log_scroll_event(self, event) -> bool:
        """Handle combat-log scrolling input. Returns True when handled."""
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_PAGEUP:
                self.combat_view.scroll_log(-1)
                return True
            if event.key == pygame.K_PAGEDOWN:
                self.combat_view.scroll_log(1)
                return True
        elif event.type == pygame.MOUSEWHEEL:
            if event.y > 0:
                self.combat_view.scroll_log(-1)
            elif event.y < 0:
                self.combat_view.scroll_log(1)
            return True
        return False

    def _clear_pending_input(self) -> bool:
        """Clear buffered events and require a fresh key release before selection input."""
        return prepare_guarded_input(flush_events=True, require_key_release=True)

    def _persist_debug_battle_log(self, result: str) -> Path | None:
        """Persist the current battle log when debug logging is enabled."""
        if not self._debug_mode_enabled():
            return None

        metadata = getattr(self.logger, "metadata", {}) or {}
        player_name = metadata.get("player", {}).get("name", "player")
        enemy_name = metadata.get("enemy", {}).get("name", "enemy")
        timestamp = datetime.datetime.now().strftime("%Y%m%d-%H%M%S-%f")
        filename = (
            f"{timestamp}-"
            f"{_battle_log_slug(player_name)}-vs-{_battle_log_slug(enemy_name)}-"
            f"{_battle_log_slug(result)}.json"
        )
        try:
            return self.logger.export_json_file(DEBUG_LOGS_DIR / "battles" / filename)
        except Exception:
            return None

    @staticmethod
    def _is_vesperion_false_final_combat(player_char: Player, enemy: Character) -> bool:
        """Return whether this combat should use Vesperion's scripted false-final branch."""
        if not isinstance(enemy, enemies.Vesperion) and getattr(enemy, "name", "") != "Vesperion":
            return False

        ensure_story = getattr(player_char, "ensure_main_story_state", None)
        story_state = (
            ensure_story() if callable(ensure_story) else getattr(player_char, "main_story", {})
        )
        if not isinstance(story_state, dict):
            return False
        return not story_state.get(
            "vesperion_false_final_triggered", False
        ) and not story_state.get("true_final_unlocked", False)

    @staticmethod
    def _is_reflection_psychopomp_combat(enemy: Character) -> bool:
        """Return whether this is the Liminal Reflection/Psychopomp encounter."""
        return (
            bool(getattr(enemy, "reflection_psychopomp", False))
            or getattr(enemy, "name", "") == "Reflection Psychopomp"
        )

    @staticmethod
    def _is_guardian_trial_echo_combat(enemy: Character) -> bool:
        """Return whether this is a Liminal Guardian trial echo encounter."""
        return bool(getattr(enemy, "guardian_trial_echo", False))

    @staticmethod
    def _is_vesperion_true_final_combat(player_char: Player, enemy: Character) -> bool:
        """Return whether Vesperion should resolve as the completed true final."""
        if not isinstance(enemy, enemies.Vesperion) and getattr(enemy, "name", "") != "Vesperion":
            return False
        ensure_story = getattr(player_char, "ensure_main_story_state", None)
        story_state = (
            ensure_story() if callable(ensure_story) else getattr(player_char, "main_story", {})
        )
        if not isinstance(story_state, dict):
            return False
        return bool(story_state.get("true_final_unlocked")) and not bool(
            story_state.get("vesperion_true_final_defeated")
        )

    @staticmethod
    def _vesperion_false_final_hp_threshold_met(enemy: Character) -> bool:
        """Return whether Vesperion has crossed the first-confrontation HP threshold."""
        health = getattr(enemy, "health", None)
        max_hp = max(1, int(getattr(health, "max", 1) or 1))
        current_hp = int(getattr(health, "current", max_hp) or 0)
        return current_hp <= max_hp * VESPERION_FALSE_FINAL_HP_RATIO

    def _handle_vesperion_false_final(self, player_char: Player, enemy: Character) -> bool:
        """Mark the pending Liminal transition without invoking normal battle-end rewards."""
        ensure_story = getattr(player_char, "ensure_main_story_state", None)
        story_state = (
            ensure_story() if callable(ensure_story) else getattr(player_char, "main_story", None)
        )
        if isinstance(story_state, dict):
            story_state["vesperion_false_final_triggered"] = True
            story_state["pending_liminal_gap_entry"] = True

        self.combat_view.add_combat_message(
            "Vesperion raises the Evening Star. The battle ends before victory can become yours."
        )
        self.running = False
        self.combat_view.reset_combat_log()
        self._combat_background = None
        return False

    def _handle_reflection_psychopomp_end(self, player_char: Player, enemy: Character) -> bool:
        """Resolve Reflection combat without normal rewards or death penalties."""
        ensure_story = getattr(player_char, "ensure_main_story_state", None)
        story_state = (
            ensure_story() if callable(ensure_story) else getattr(player_char, "main_story", {})
        )

        if player_char.is_alive() and not enemy.is_alive():
            if isinstance(story_state, dict):
                story_state["reflection_defeated"] = True
                if main_story.can_unlock_true_final(story_state):
                    story_state["true_final_unlocked"] = True
            player_char.state = "normal"
            self.combat_view.add_combat_message("The Reflection yields to the self you chose.")
            self.running = False
            self.combat_view.reset_combat_log()
            self._combat_background = None
            return True

        player_char.state = "normal"
        try:
            player_char.effects(end=True)
        except Exception:
            pass
        try:
            enemy.effects(end=True)
        except Exception:
            pass
        player_char.location_x, player_char.location_y, player_char.location_z = (
            LIMINAL_GAP_ENTRY_POS
        )
        player_char.facing = LIMINAL_GAP_ENTRY_FACING
        player_char.health.current = max(1, player_char.health.max // 2)
        player_char.mana.current = max(0, player_char.mana.max // 2)
        enemy.health.current = enemy.health.max
        enemy.mana.current = enemy.mana.max
        self.combat_view.add_combat_message(
            "The Reflection breaks your stance and returns you to the Liminal hub."
        )
        self.running = False
        self.combat_view.reset_combat_log()
        self._combat_background = None
        return False

    def _handle_guardian_trial_echo_end(self, player_char: Player, enemy: Character) -> bool:
        """Resolve a Guardian trial echo without normal rewards or death penalties."""
        if player_char.is_alive() and not enemy.is_alive():
            player_char.state = "normal"
            guardian_name = getattr(enemy, "liminal_trial_guardian", "The trial")
            self.combat_view.add_combat_message(
                f"{guardian_name} yields to the choice you carried into the fight."
            )
            self.running = False
            self.combat_view.reset_combat_log()
            self._combat_background = None
            return True

        player_char.state = "normal"
        try:
            player_char.effects(end=True)
        except Exception:
            pass
        try:
            enemy.effects(end=True)
        except Exception:
            pass
        player_char.location_x, player_char.location_y, player_char.location_z = (
            LIMINAL_GAP_ENTRY_POS
        )
        player_char.facing = LIMINAL_GAP_ENTRY_FACING
        player_char.health.current = max(1, player_char.health.max // 2)
        player_char.mana.current = max(0, player_char.mana.max // 2)
        enemy.health.current = enemy.health.max
        enemy.mana.current = enemy.mana.max
        guardian_name = getattr(enemy, "liminal_trial_guardian", "The trial")
        self.combat_view.add_combat_message(
            f"{guardian_name} returns you to the Liminal hub to choose again."
        )
        self.running = False
        self.combat_view.reset_combat_log()
        self._combat_background = None
        return False

    def _handle_vesperion_true_final_victory(self, player_char: Player, enemy: Character) -> bool:
        """Resolve true-final Vesperion victory without normal loot/reward handling."""
        ensure_story = getattr(player_char, "ensure_main_story_state", None)
        story_state = (
            ensure_story() if callable(ensure_story) else getattr(player_char, "main_story", {})
        )
        if isinstance(story_state, dict):
            story_state["vesperion_true_final_defeated"] = True
            story_state["main_story_complete"] = True
        player_char.state = "normal"
        self.combat_view.add_combat_message("Vesperion falls silent. Voluntas remains.")
        self.running = False
        self.combat_view.reset_combat_log()
        self._combat_background = None
        return True

    def _apply_vesperion_phase_pressure(self, player_char: Player, enemy: Character) -> bool:
        """Apply Vesperion's once-per-phase pressure outside normal action rewards."""
        pressure = getattr(enemy, "apply_phase_pressure", None)
        if not callable(pressure):
            return False
        message = pressure(player_char)
        if not message:
            return False
        for line in message.strip().split("\n"):
            if line.strip():
                self.combat_view.add_combat_message(line)
        self._flush_result_frame(player_char, enemy)
        return True

    @staticmethod
    def _arm_guarded_input(event, input_armed: bool) -> bool:
        return update_input_armed_from_event(event, True, input_armed)

    def _combat_action_rects(self, actions) -> list[pygame.Rect]:
        """Return clickable rectangles for the six-slot bar and command row."""
        combat_width = int(getattr(self.combat_view, "combat_width", self.screen.get_width()))
        combat_height = int(getattr(self.combat_view, "combat_height", self.screen.get_height()))
        menu_height = 174
        menu_rect = pygame.Rect(0, combat_height - menu_height, combat_width, menu_height)
        shortcut_count = min(6, len(actions))
        card_width = max(72, (menu_rect.width - 28) // 6)
        rects = [
            pygame.Rect(12 + index * card_width, menu_rect.top + 9, card_width - 4, 104)
            for index in range(shortcut_count)
        ]
        command_count = max(0, len(actions) - shortcut_count)
        if command_count:
            command_width = max(70, (menu_rect.width - 24) // command_count)
            rects.extend(
                pygame.Rect(
                    12 + index * command_width,
                    menu_rect.top + 122,
                    command_width - 4,
                    37,
                )
                for index in range(command_count)
            )
        return rects

    def _selection_menu_option_rects(
        self, options, scroll_offset: int = 0
    ) -> list[tuple[int, pygame.Rect]]:
        """Return visible option indices and click rectangles for an in-combat picker."""
        panel_width = max(420, int(self.screen.get_width() * 0.65))
        panel_height = 176
        panel_x = 0
        panel_y = self.screen.get_height() - panel_height
        max_visible = 3
        max_scroll = max(0, len(options) - max_visible)
        scroll_offset = max(0, min(scroll_offset, max_scroll))
        option_y = panel_y + 50
        option_rect_width = panel_width - 58
        rects = []
        for index in range(scroll_offset, min(len(options), scroll_offset + max_visible)):
            rects.append(
                (
                    index,
                    pygame.Rect(panel_x + 18, option_y - 4, option_rect_width, 30),
                )
            )
            option_y += 34
        return rects

    def _selection_menu_back_rect(self) -> pygame.Rect:
        """Return the shared click target that cancels an in-combat picker."""
        panel_width = max(420, int(self.screen.get_width() * 0.65))
        panel_y = self.screen.get_height() - 176
        return pygame.Rect(panel_width - 88, panel_y + 12, 68, 26)

    def _selection_menu_back_clicked(self, event, input_armed: bool) -> bool:
        """Return whether an armed left click chose the picker Back target."""
        return (
            input_armed
            and is_left_click(event)
            and self._selection_menu_back_rect().collidepoint(mouse_position(event) or (-1, -1))
        )

    def _selection_menu_hit_index(self, options, scroll_offset: int, event) -> int | None:
        rect_pairs = self._selection_menu_option_rects(options, scroll_offset)
        visible_index = hit_index([rect for _index, rect in rect_pairs], mouse_position(event))
        if visible_index is None:
            return None
        return rect_pairs[visible_index][0]

    def _selection_menu_mouse_update(
        self,
        event,
        options,
        selected: int,
        scroll_offset: int,
        input_armed: bool,
    ) -> tuple[int, int, bool]:
        """Return updated selection, scroll, and whether the mouse confirmed."""
        hovered = self._selection_menu_hit_index(options, scroll_offset, event)
        if hovered is None:
            return selected, scroll_offset, False
        selected = hovered
        scroll_offset = self._scroll_offset_for_selection(selected, scroll_offset)
        return selected, scroll_offset, is_left_click(event) and input_armed

    def _render_described_selection_menu(
        self, title, options, selected, scroll_offset, descriptions
    ):
        self._selection_menu_descriptions = descriptions
        try:
            self._render_selection_menu(title, options, selected, scroll_offset)
        finally:
            self._selection_menu_descriptions = None

    @staticmethod
    def _scroll_offset_for_selection(
        selected: int, scroll_offset: int, max_visible: int = 3
    ) -> int:
        if selected < scroll_offset:
            return selected
        if selected >= scroll_offset + max_visible:
            return selected - max_visible + 1
        return scroll_offset

    def _selection_frame_player(self, actor):
        """Return the player object to use while rendering actor submenus."""
        return getattr(self.engine, "player", None) or actor

    @staticmethod
    def _canonical_resolve_skill_name(name: object) -> str:
        return str(name or "")

    def _is_resolve_skill(self, skill) -> bool:
        name = self._canonical_resolve_skill_name(getattr(skill, "name", ""))
        resolve_names = {entry["name"] for entry in promotion_kits.RESOLVE_SPEND_ABILITIES}
        surge_names = {entry["name"] for entry in promotion_kits.RESOLVE_SURGES}
        return (
            getattr(skill, "resource_type", None) == "Resolve"
            or name in resolve_names
            or name in surge_names
        )

    def _available_skill_names(
        self, player_char, enemy=None, *, allowed_names=None, resolve: bool | None = None
    ) -> list[str]:
        allowed = set(allowed_names) if allowed_names is not None else None
        if getattr(player_char, "tunnel", False):
            allowed = {"Surface"} if allowed is None else allowed & {"Surface"}
        names = []
        for name, skill in getattr(player_char, "spellbook", {}).get("Skills", {}).items():
            if allowed is None and name in ability_mechanics.BEAST_COMPANION_COMMANDS:
                continue
            if allowed is None and name == "Tame":
                continue
            if allowed is None and name == "Transform":
                continue
            is_resolve = self._is_resolve_skill(skill)
            if resolve is not None and is_resolve != resolve:
                continue
            if allowed is not None and name not in allowed:
                continue
            if self._skill_available_for_selection(player_char, skill, enemy):
                names.append(name)
        return names

    def _resolve_skill_cost_label(self, skill, player_char=None) -> str:
        cost = getattr(skill, "resolve_cost", None)
        name = self._canonical_resolve_skill_name(getattr(skill, "name", ""))
        if cost is None:
            for entry in promotion_kits.RESOLVE_SPEND_ABILITIES:
                if entry["name"] == name:
                    cost = entry["cost"]
                    break
        if cost is None and name in {entry["name"] for entry in promotion_kits.RESOLVE_SURGES}:
            cost = "Full"
        if str(cost).lower() == "full":
            return "Full Resolve"
        if player_char is not None:
            cost = promotion_kits.effective_resolve_cost(player_char, int(cost or 0))
        return f"Resolve: {int(cost or 0)}"

    @staticmethod
    def _fit_text_to_width(font: pygame.font.Font, text: str, max_width: int) -> str:
        """Trim text to the rendered width available for compact combat overlays."""
        text = " ".join(str(text or "").split())
        if max_width <= 0 or font.size(text)[0] <= max_width:
            return text

        ellipsis = "..."
        ellipsis_width = font.size(ellipsis)[0]
        if ellipsis_width >= max_width:
            return ellipsis

        trimmed = text
        while trimmed and font.size(trimmed)[0] + ellipsis_width > max_width:
            trimmed = trimmed[:-1]
        return f"{trimmed.rstrip()}{ellipsis}"

    @staticmethod
    def _combat_effect_kind(action: str, choice: str | None = None, message: str = "") -> str:
        text = f"{choice or ''} {message or ''}".lower()
        if "reflect" in text or "reflection" in text:
            return "reflect"
        if any(term in text for term in ("stun", "stunned", "prone", "knocked down")):
            return "status"
        if action in {"Spells", "Cast Spell"}:
            return "spell"
        if action in {"Skills", "Resolve", "Use Skill"}:
            return "skill"
        if choice and any(
            term in str(choice).lower()
            for term in ("spell", "bolt", "blast", "storm", "fire", "ice")
        ):
            return "spell"
        return "weapon"

    @staticmethod
    def _combat_effect_element(choice: object = None, message: str = "") -> str | None:
        text = f"{choice or ''} {message or ''}".lower()
        element_terms = {
            "Fire": ("fire", "flame", "burn", "ember"),
            "Ice": ("ice", "frost", "freeze", "frozen"),
            "Electric": ("electric", "lightning", "storm", "thunder", "shock"),
            "Water": ("water", "wave", "flood"),
            "Earth": ("earth", "stone", "rock"),
            "Wind": ("wind", "air", "gale"),
            "Poison": ("poison", "venom", "toxin"),
            "Holy": ("holy", "light", "radiant"),
            "Dark": ("dark", "shadow", "void"),
            "Death": ("death", "doom", "fatal"),
        }
        for element, terms in element_terms.items():
            if any(term in text for term in terms):
                return element
        return None

    def _show_combat_damage_effect(
        self,
        target: str,
        action: str,
        choice: str | None,
        message: str,
        amount: int | tuple[int, ...] | None = None,
    ) -> None:
        kind = self._combat_effect_kind(action, choice, message)
        element = self._combat_effect_element(choice, message)
        if kind == "weapon" and element is not None:
            kind = "elemental_strike"
        self.combat_view.trigger_impact_effect(
            target,
            kind,
            element,
        )
        if amount:
            color = self.combat_view.colors.get("log_damage", (235, 120, 105))
            amounts = amount if isinstance(amount, tuple) else (amount,)
            for damage in amounts:
                if damage > 0:
                    self.combat_view.trigger_floating_text(
                        target,
                        f"-{damage}",
                        color,
                    )
        # Enemy sprites already provide a localized tint, recoil, impact, and
        # floating text. A second full-battlefield snapshot flash could briefly
        # replace the live lane rendering and make the target appear to blink.
        if target == "player":
            self.combat_view.show_damage_flash(
                True,
                event_handler=self._handle_combat_log_scroll_event,
            )

    @staticmethod
    def _recorded_floating_damage(
        action_result: object,
        fallback: int,
        *,
        target_id: str | None = None,
    ) -> int | tuple[int, ...]:
        """Return logged damage instances instead of aggregate HP loss."""
        group = getattr(action_result, "combat_results", None)
        portions = list(getattr(group, "results", ()) or ())
        if target_id is not None:
            portions = [
                portion for portion in portions if getattr(portion, "target_id", None) == target_id
            ]
        amounts = []
        for portion in portions:
            instances = getattr(portion, "extra", {}).get("damage_instances")
            if isinstance(instances, (list, tuple)):
                for instance in instances:
                    try:
                        amount = int(instance or 0)
                    except (TypeError, ValueError):
                        continue
                    if amount > 0:
                        amounts.append(amount)
                continue
            try:
                amount = int(getattr(portion, "damage", 0) or 0)
            except (TypeError, ValueError):
                continue
            if amount > 0:
                amounts.append(amount)
        if len(amounts) > 1:
            return tuple(amounts)
        if amounts:
            return amounts[0]
        return max(0, int(fallback or 0))

    def _show_combat_heal_text(self, target: str, amount: int) -> None:
        if amount <= 0:
            return
        color = self.combat_view.colors.get("log_heal", (120, 210, 135))
        self.combat_view.trigger_floating_text(target, f"+{amount}", color)

    def _play_smoke_screen_visual(
        self,
        player_char: Player,
        enemy: Character,
        target: str,
        frames: int = 24,
    ) -> None:
        """Briefly show smoke for instant Smoke Screen escapes."""
        self.combat_view.trigger_smoke_screen_visual(target)
        clock = pygame.time.Clock()
        for _ in range(frames):
            for event in get_events():
                if event.type == pygame.QUIT:
                    pygame.quit()
                    sys.exit(0)
                self._handle_combat_log_scroll_event(event)
            self._render_combat_frame(self._selection_frame_player(player_char), enemy, [], -1)
            pygame.display.flip()
            clock.tick(60)

    def _show_slot_machine_reveal(self, user: Character, target: Character) -> str:
        """Animate a Slot Machine spin popup and reveal cards left-to-right."""
        cards = random.sample(SLOT_CARD_DECK, 3)
        spin = ",".join(cards)
        result_label = self._slot_machine_result_label(spin)
        symbols = self._slot_symbol_surfaces()
        clock = pygame.time.Clock()

        def draw_symbol(
            symbol_index: int, reel_rect: pygame.Rect, alpha: int = 255, y_offset: int = 0
        ) -> None:
            if symbols:
                symbol = symbols[symbol_index]
                inset = reel_rect.inflate(-24, -20)
                scale = min(inset.width / symbol.get_width(), inset.height / symbol.get_height())
                scaled_size = (
                    max(1, int(symbol.get_width() * scale)),
                    max(1, int(symbol.get_height() * scale)),
                )
                symbol_surface = pygame.transform.smoothscale(symbol, scaled_size)
                symbol_surface.set_alpha(alpha)
                symbol_rect = symbol_surface.get_rect(
                    center=(reel_rect.centerx, reel_rect.centery + y_offset)
                )
                self.screen.blit(symbol_surface, symbol_rect)
                return

            fallback_font = pygame.font.Font(None, 62)
            fallback_text = (
                SLOT_CARD_DECK[symbol_index] if 0 <= symbol_index < len(SLOT_CARD_DECK) else "?"
            )
            fallback = fallback_font.render(fallback_text, True, (120, 20, 30))
            if hasattr(fallback, "set_alpha"):
                fallback.set_alpha(alpha)
            self.screen.blit(
                fallback,
                fallback.get_rect(center=(reel_rect.centerx, reel_rect.centery + y_offset)),
            )

        def draw_overlay(revealed_count: int, final: bool = False) -> None:
            self._render_combat_frame(user, target, [], -1)

            overlay = pygame.Surface(
                (self.combat_view.combat_width, self.combat_view.combat_height), pygame.SRCALPHA
            )
            overlay.fill((0, 0, 0, 185))
            self.screen.blit(overlay, (0, 0))

            popup_width = min(560, self.combat_view.combat_width - 40)
            popup_height = min(390, self.combat_view.combat_height - 40)
            popup_x = (self.combat_view.combat_width - popup_width) // 2
            popup_y = (self.combat_view.combat_height - popup_height) // 2
            popup_rect = pygame.Rect(popup_x, popup_y, popup_width, popup_height)

            pygame.draw.rect(self.screen, (42, 9, 16), popup_rect, border_radius=8)
            pygame.draw.rect(
                self.screen, (144, 24, 34), popup_rect.inflate(-14, -14), border_radius=6
            )
            pygame.draw.rect(self.screen, (236, 188, 72), popup_rect, 5, border_radius=8)
            pygame.draw.rect(
                self.screen, (72, 14, 24), popup_rect.inflate(-34, -32), border_radius=5
            )

            top_rect = pygame.Rect(
                popup_rect.left + 42, popup_rect.top + 22, popup_rect.width - 84, 64
            )
            pygame.draw.rect(
                self.screen,
                (122, 20, 34),
                top_rect,
                border_radius=6,
            )
            pygame.draw.rect(self.screen, (244, 202, 88), top_rect, 3, border_radius=6)

            for index in range(11):
                bulb_x = popup_rect.left + 28 + index * ((popup_rect.width - 56) // 10)
                bulb_color = (
                    (255, 228, 126)
                    if (pygame.time.get_ticks() // 240 + index) % 2 == 0
                    else (178, 92, 46)
                )
                pygame.draw.rect(
                    self.screen,
                    bulb_color,
                    pygame.Rect(bulb_x - 5, popup_rect.top + 8, 10, 10),
                    border_radius=5,
                )

            title_font = pygame.font.Font(None, 46)
            subtitle_font = pygame.font.Font(None, 25)

            title_text = title_font.render("Slots", True, (255, 225, 106))
            title_rect = title_text.get_rect(center=(popup_rect.centerx, top_rect.centery - 2))
            self.screen.blit(title_text, title_rect)

            reel_area = pygame.Rect(
                popup_rect.left + 58, popup_rect.top + 104, popup_rect.width - 136, 158
            )
            pygame.draw.rect(self.screen, (25, 18, 22), reel_area.inflate(24, 20), border_radius=7)
            pygame.draw.rect(
                self.screen, (232, 192, 92), reel_area.inflate(24, 20), 3, border_radius=7
            )
            reel_gap = 14
            reel_width = (reel_area.width - reel_gap * 2) // 3
            for i in range(3):
                reel_rect = pygame.Rect(
                    reel_area.left + i * (reel_width + reel_gap),
                    reel_area.top,
                    reel_width,
                    reel_area.height,
                )
                pygame.draw.rect(self.screen, (232, 222, 190), reel_rect, border_radius=5)
                pygame.draw.rect(
                    self.screen, (255, 250, 224), reel_rect.inflate(-8, -8), border_radius=4
                )
                pygame.draw.rect(self.screen, (40, 24, 30), reel_rect, 3, border_radius=5)

                symbol_index = SLOT_CARD_ORDER[cards[i]]
                if i >= revealed_count:
                    spin_index = (pygame.time.get_ticks() // 145 + i * 11) % len(SLOT_CARD_DECK)
                    draw_symbol(
                        (spin_index - 1) % len(SLOT_CARD_DECK), reel_rect, alpha=85, y_offset=-44
                    )
                    draw_symbol(spin_index, reel_rect, alpha=210)
                    draw_symbol(
                        (spin_index + 1) % len(SLOT_CARD_DECK), reel_rect, alpha=85, y_offset=44
                    )
                else:
                    draw_symbol(symbol_index, reel_rect)

            payout_rect = pygame.Rect(
                popup_rect.left + 120, popup_rect.bottom - 82, popup_rect.width - 240, 26
            )
            pygame.draw.rect(self.screen, (30, 22, 26), payout_rect, border_radius=4)
            pygame.draw.rect(self.screen, (178, 150, 84), payout_rect, 2, border_radius=4)
            payout_text = result_label if final else "..."
            payout = subtitle_font.render(
                payout_text, True, (245, 225, 150) if final else (120, 112, 116)
            )
            self.screen.blit(payout, payout.get_rect(center=payout_rect.center))

            handle_x = popup_rect.right - 34
            pygame.draw.rect(
                self.screen,
                (86, 68, 54),
                (handle_x, popup_rect.top + 116, 10, 110),
                border_radius=4,
            )
            pygame.draw.rect(
                self.screen,
                (218, 45, 54),
                (handle_x - 12, popup_rect.top + 98, 34, 34),
                border_radius=16,
            )

            subtitle_text = "Press any key or click to continue" if final else "Reels spinning..."
            subtitle_color = (245, 225, 150) if final else (194, 182, 176)
            subtitle = subtitle_font.render(subtitle_text, True, subtitle_color)
            subtitle_rect = subtitle.get_rect(center=(popup_rect.centerx, popup_rect.bottom - 34))
            self.screen.blit(subtitle, subtitle_rect)

            pygame.display.flip()

        for reveal_idx in range(1, 4):
            frames = 18 + reveal_idx * 8
            for _ in range(frames):
                for event in get_events():
                    if event.type == pygame.QUIT:
                        pygame.quit()
                        sys.exit(0)
                draw_overlay(reveal_idx)
                clock.tick(90)

        input_armed = prepare_guarded_input(flush_events=False, require_key_release=True)
        waiting = True
        while waiting:
            for event in get_events():
                if event.type == pygame.QUIT:
                    pygame.quit()
                    sys.exit(0)
                input_armed = self._arm_guarded_input(event, input_armed)
                if (
                    event.type in (pygame.KEYDOWN, pygame.MOUSEBUTTONDOWN, pygame.JOYBUTTONDOWN)
                    and input_armed
                ):
                    waiting = False
                    break
            if waiting:
                if release_guard_allows_input(True, input_armed):
                    input_armed = True
                draw_overlay(3, final=True)
                clock.tick(18)

        return spin
