"""Core behavior for the modern character screen package."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pygame

from src.core.classes import grandmaster, promotion_mechanic_tab_label, transformation
from src.ui_pygame.assets.companion_art_manager import get_companion_art_manager
from src.ui_pygame.assets.item_render_manager import get_item_render_manager
from src.ui_pygame.assets.portrait_manager import PortraitManager

from ..progression_screen import ProgressionScreen
from .models import DEFAULT_CHARACTER_TABS, PORTRAIT_DIR, CharacterTab


class CharacterCoreMixin:
    def __init__(self, presenter, tabs: tuple[CharacterTab, ...] = DEFAULT_CHARACTER_TABS):
        self.tabs = tabs
        self.active_tab_key = tabs[0].key
        self.active_tab_index = 0
        self.portrait_manager = PortraitManager()
        self.item_render_manager = get_item_render_manager()
        self.companion_art_manager = get_companion_art_manager()
        self.selected_equipment_slot_index = 0
        self.selected_class_companion_index = 0
        self.selected_weapon_discipline_index = 0
        self.equipment_selector_active = False
        self.class_companion_selector_active = False
        self.weapon_discipline_selector_active = False
        self.progression_selector_active = False
        self.selected_jump_mod_index = 0
        self._jump_mod_row_rects: list[pygame.Rect] = []
        self._form_action_rects: list[tuple[str, pygame.Rect]] = []
        self.current_selection = 0
        self.menu_options: list[str] = []
        super().__init__(presenter)
        self.progression_view = ProgressionScreen(presenter, None)
        self.progression_view.background_draw_func = lambda: self.draw_all(
            self._progression_player,
            do_flip=False,
        )
        self._progression_player = None
        self.calculate_rects()

    def calculate_rects(self):
        """Calculate responsive panel rectangles for the modern layout."""
        metrics = self.presenter.layout_metrics
        margin = metrics.unit(18)
        gap = metrics.unit(12)
        tab_height = max(metrics.unit(44), self.height // 16)
        action_height = max(metrics.unit(92), self.height // 8)
        content_top = margin + tab_height + gap
        content_height = self.height - content_top - action_height - (gap * 2) - margin
        content_height = max(320, content_height)

        self.tab_rect = pygame.Rect(margin, margin, self.width - (margin * 2), tab_height)
        self.content_rect = pygame.Rect(
            margin, content_top, self.width - (margin * 2), content_height
        )
        self.actions_rect = pygame.Rect(
            margin, self.content_rect.bottom + gap, self.width - (margin * 2), action_height
        )

        available_panel_width = self.content_rect.width - gap
        character_width = (available_panel_width * 3) // 5
        self.character_panel_rect = pygame.Rect(
            self.content_rect.left, self.content_rect.top, character_width, self.content_rect.height
        )
        self.combat_panel_rect = pygame.Rect(
            self.character_panel_rect.right + gap,
            self.content_rect.top,
            self.content_rect.right - self.character_panel_rect.right - gap,
            self.content_rect.height,
        )
        self.details_rect = pygame.Rect(
            self.content_rect.left,
            self.content_rect.top,
            self.content_rect.width,
            self.content_rect.height,
        )
        self.equipment_panel_rect = self.details_rect

        self.menu_rect = self.actions_rect
        self.info_rect = self.character_panel_rect
        self.exp_rect = self.character_panel_rect
        self.stats_rect = self.content_rect
        self.menu_options = self._base_menu_options()

    @property
    def active_tab(self) -> CharacterTab:
        for tab in self.tabs:
            if tab.key == self.active_tab_key:
                return tab
        return self.tabs[0]

    def select_tab(self, key: str) -> None:
        for index, tab in enumerate(self.tabs):
            if tab.key == key:
                self.active_tab_key = key
                self.active_tab_index = index
                if key != "equipment":
                    self.equipment_selector_active = False
                if key != "class":
                    self.class_companion_selector_active = False
                    self.weapon_discipline_selector_active = False
                if key != "progression":
                    self.progression_selector_active = False
                return
        raise ValueError(f"Unknown character tab: {key}")

    def class_mechanic_tab(self, player_char) -> CharacterTab | None:
        if grandmaster.is_weapon_discipline_class(player_char):
            return CharacterTab("class", "Weapon Discipline")
        class_name = transformation.permanent_class_name(player_char)
        mechanic_label = promotion_mechanic_tab_label(class_name)
        getattr(player_char, "familiar", None)
        if class_name == "Thaumaturgist":
            return CharacterTab("class", "Xenids")
        if class_name in {"Ranger", "Beast Master"}:
            return CharacterTab("class", "Companion & Hunt")
        if mechanic_label:
            return CharacterTab("class", mechanic_label)
        return None

    def visible_tabs(self, player_char=None) -> tuple[CharacterTab, ...]:
        if player_char is None:
            return self.tabs
        equipment_tab = next(tab for tab in self.tabs if tab.key == "equipment")
        progression_tab = next(tab for tab in self.tabs if tab.key == "progression")
        tabs = [self.tabs[0], equipment_tab]
        mechanic_tab = self.class_mechanic_tab(player_char)
        if mechanic_tab is not None:
            tabs.append(mechanic_tab)
        tabs.append(progression_tab)
        return tuple(tabs)

    def ensure_active_tab_visible(self, player_char) -> None:
        visible = self.visible_tabs(player_char)
        if self.active_tab_key not in {tab.key for tab in visible}:
            self.select_tab(visible[0].key)

    def select_visible_tab_index(self, index: int, player_char) -> None:
        visible = self.visible_tabs(player_char)
        if 0 <= index < len(visible):
            self.select_tab(visible[index].key)

    def active_mechanic_label(self, player_char) -> str:
        if self.active_tab_key != "class":
            return ""
        mechanic_tab = self.class_mechanic_tab(player_char)
        return mechanic_tab.label if mechanic_tab is not None else ""

    def move_tab(self, delta: int, player_char=None) -> None:
        visible = self.visible_tabs(player_char)
        active_index = next(
            (index for index, tab in enumerate(visible) if tab.key == self.active_tab_key),
            0,
        )
        self.select_tab(visible[(active_index + delta) % len(visible)].key)
        if self.active_tab.key != "equipment":
            self.equipment_selector_active = False
        if self.active_tab.key != "class":
            self.class_companion_selector_active = False

    @staticmethod
    def _attr_name(value: Any, default: str = "Unknown") -> str:
        return str(getattr(value, "name", default) or default)

    @staticmethod
    def portrait_filename(player_char) -> str:
        race = CharacterCoreMixin._attr_name(getattr(player_char, "race", None), "Human")
        race_key = PortraitManager.normalize_key(race, "human")
        return f"{race_key}_base_portraits.png"

    def portrait_path(self, player_char) -> Path:
        return PORTRAIT_DIR / self.portrait_filename(player_char)

    def load_portrait(self, player_char):
        race = getattr(player_char, "race", "Human")
        gender = getattr(player_char, "gender", getattr(player_char, "sex", "Male"))
        class_name = self._attr_name(getattr(player_char, "cls", None), "")
        first_promotion = getattr(player_char, "first_promotion", None)
        second_promotion = getattr(player_char, "second_promotion", None)
        effects = getattr(player_char, "active_visual_effects", ())
        variant = getattr(player_char, "portrait_variant", 0)
        return self.portrait_manager.get_portrait(
            race=race,
            gender=gender,
            class_name=class_name,
            first_promotion=first_promotion,
            second_promotion=second_promotion,
            effects=effects,
            variant=variant,
        )

    def _draw_fitted_surface(self, surface: pygame.Surface, rect: pygame.Rect) -> None:
        source_width, source_height = surface.get_size()
        if source_width <= 0 or source_height <= 0:
            return
        scale = min(rect.width / source_width, rect.height / source_height)
        target_size = (max(1, int(source_width * scale)), max(1, int(source_height * scale)))
        fitted = pygame.transform.smoothscale(surface, target_size)
        target_rect = fitted.get_rect(center=rect.center)
        self.screen.blit(fitted, target_rect)
