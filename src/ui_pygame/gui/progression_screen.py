"""Shared-service pygame progression tree and attribute screen."""

from __future__ import annotations

import pygame

from src.core import companions
from src.core.progression import (
    PRIMARY_ATTRIBUTES,
    TREE_NODES,
    NodeKind,
    NodeState,
    apply_progression_plan,
    available_nodes,
    permanent_closures_for_plan,
    prerequisite_groups,
    progression_class_name,
)
from src.ui_pygame.assets.ability_icon_manager import get_ability_icon_manager
from src.ui_pygame.screen_runtime import get_events

from .character_naming import CompanionNamingScreen
from .church import PaladinVowSelectionPopup
from .confirmation_popup import ConfirmationPopup
from .familiar_selection_popup import FamiliarSelectionPopup
from .mouse_helpers import hit_index, is_left_click, mouse_position
from .popup_menus import SelectionPopup
from .progression_screen_panels import ProgressionPanelMixin
from .progression_screen_tree import ProgressionTreeMixin
from .promotion_screen import PromotionScreen
from .town_base import TownScreenBase


class ProgressionScreen(ProgressionPanelMixin, ProgressionTreeMixin, TownScreenBase):
    """Keyboard-and-mouse progression screen backed only by core services."""

    STAT_DISPLAY_NAMES = {
        "strength": "Strength",
        "intel": "Intelligence",
        "wisdom": "Wisdom",
        "con": "Constitution",
        "charisma": "Charisma",
        "dex": "Dexterity",
    }
    CONNECTOR_COLOR = (72, 78, 88)
    PROMOTION_CONNECTOR_COLOR = (156, 126, 58)
    REQUIRED_PATH_COLOR = (174, 104, 238)
    REQUIRED_ENDPOINT_COLOR = (226, 166, 255)
    NODE_BACKING_COLOR = (12, 14, 20)
    LABEL_BACKING_COLOR = (8, 10, 14)
    PROMOTION_WARNING_COLOR = (205, 95, 95)
    TREE_WARNING_HEIGHT = 38
    TREE_WARNING_TEXT = (
        "Permanent choice: Buying promotion nodes may prevent the player "
        "from buying learning certain abilities. Choose carefully."
    )
    LANCER_PROMOTION_TEXT = (
        "Promoting to Dragoon retains all unpurchased Lancer nodes in the Dragoon tree."
    )

    STATE_COLORS = {
        NodeState.OWNED: (90, 190, 110),
        NodeState.AVAILABLE: (218, 165, 32),
        NodeState.BLOCKED: (130, 130, 130),
        NodeState.CLOSED: (120, 60, 60),
    }

    def __init__(self, presenter, player_char):
        super().__init__(presenter)
        self.player_char = player_char
        self.focus = "nodes"
        self.current_node = 0
        self.hovered_node_index: int | None = None
        self.current_attribute = 0
        self.tree_index = 0
        self.node_rects: list[pygame.Rect] = []
        self.node_icon_rects: list[pygame.Rect] = []
        self.attribute_rects: list[pygame.Rect] = []
        self.attribute_minus_rects: list[pygame.Rect] = []
        self.attribute_plus_rects: list[pygame.Rect] = []
        self.reset_button_rect = pygame.Rect(0, 0, 0, 0)
        self.spend_button_rect = pygame.Rect(0, 0, 0, 0)
        self.pending_node_ids: list[str] = []
        self.pending_attributes: dict[str, int] = {}
        self.background_draw_func = None
        self.show_embedded_navigation_helper = False
        self.embedded_navigation_active = False
        self.tree_scroll_row = 0
        self._tree_viewport: pygame.Rect | None = None
        self.icon_manager = get_ability_icon_manager()

    def _popup_background(self):
        if callable(self.background_draw_func):
            self.background_draw_func()
        else:
            self.draw_all(do_flip=False)

    def _statuses(self):
        self._ensure_staging()
        return available_nodes(
            self.player_char,
            self._selected_tree_id(),
            planned_node_ids=self.pending_node_ids,
            planned_attributes=self.pending_attributes,
        )

    def _ensure_staging(self):
        if not hasattr(self, "pending_node_ids"):
            self.pending_node_ids = []
        if not hasattr(self, "pending_attributes"):
            self.pending_attributes = {}
        if not hasattr(self, "attribute_minus_rects"):
            self.attribute_minus_rects = []
        if not hasattr(self, "attribute_plus_rects"):
            self.attribute_plus_rects = []
        if not hasattr(self, "spend_button_rect"):
            self.spend_button_rect = pygame.Rect(0, 0, 0, 0)
        if not hasattr(self, "reset_button_rect"):
            self.reset_button_rect = pygame.Rect(0, 0, 0, 0)

    def _pending_node_cost(self) -> int:
        self._ensure_staging()
        return sum(TREE_NODES[node_id].cost for node_id in self.pending_node_ids)

    def _pending_attribute_cost(self) -> int:
        self._ensure_staging()
        return sum(self.pending_attributes.values())

    def _remaining_points(self) -> int:
        return self.player_char.progression.unspent_points - self._pending_node_cost()

    def _remaining_attribute_points(self) -> int:
        return (
            self.player_char.progression.unspent_attribute_points - self._pending_attribute_cost()
        )

    def has_pending_changes(self) -> bool:
        """Return whether the screen has an uncommitted distribution."""
        return self._pending_node_cost() + self._pending_attribute_cost() > 0

    def _clear_pending(self) -> None:
        self._ensure_staging()
        self.pending_node_ids.clear()
        self.pending_attributes.clear()

    def _tree_ids(self):
        current = progression_class_name(self.player_char)
        completed = sorted(self.player_char.progression.completed_trees)
        return [current, *(tree for tree in completed if tree != current)]

    def _selected_tree_id(self):
        tree_ids = self._tree_ids()
        self.tree_index %= len(tree_ids)
        return tree_ids[self.tree_index]

    def _selected_status(self):
        statuses = self._statuses()
        return statuses[self.current_node] if statuses else None

    def _promotion_choices(self, target_class: str):
        if target_class == "Paladin":
            vow = PaladinVowSelectionPopup(self.presenter).show(
                flush_events=True,
                require_key_release=True,
                background_draw_func=self._popup_background,
            )
            if vow is None:
                return None
            confirm = ConfirmationPopup(
                self.presenter,
                f"Swear the Vow of {vow}?",
                show_buttons=True,
            )
            if not confirm.show(
                flush_events=True,
                require_key_release=True,
                background_draw_func=self._popup_background,
            ):
                return None
            return {"vow": vow}
        if target_class == "Warlock":
            familiar_types = [
                companions.Homunculus,
                companions.Fairy,
                companions.Mephit,
                companions.Jinkin,
            ]
            familiar = FamiliarSelectionPopup(
                self.presenter,
                self,
                familiar_types,
            ).show(
                self.player_char,
                flush_events=True,
                require_key_release=True,
            )
            if familiar is None:
                return None
            familiar.name = familiar.race
            naming = CompanionNamingScreen(
                self.presenter,
                familiar.race,
                species=familiar.race,
                form=familiar.spec,
                special=", ".join(
                    [
                        *familiar.spellbook.get("Skills", {}),
                        *familiar.spellbook.get("Spells", {}),
                    ]
                ),
            )
            nickname = naming.navigate(
                default=familiar.race,
                flush_events=True,
                require_key_release=True,
                background_surface=self.screen.copy(),
            )
            if nickname is None:
                return None
            familiar.name = str(nickname).strip() or familiar.race
            return {"familiar": familiar}
        return {}

    def _toggle_selected_node(self):
        self._ensure_staging()
        status = self._selected_status()
        if status is None:
            return
        node = status.node
        if node.id in self.pending_node_ids:
            removed = {node.id}
            changed = True
            while changed:
                changed = False
                for pending_id in self.pending_node_ids:
                    if pending_id in removed:
                        continue
                    pending_node = TREE_NODES[pending_id]
                    remaining = (
                        set(self.pending_node_ids) | self.player_char.progression.purchased_node_ids
                    ) - removed
                    loses_requirement = any(
                        not any(prerequisite in remaining for prerequisite in group)
                        for group in prerequisite_groups(pending_node)
                    )
                    if loses_requirement:
                        removed.add(pending_id)
                        changed = True
            self.pending_node_ids = [
                node_id for node_id in self.pending_node_ids if node_id not in removed
            ]
        elif status.state == NodeState.AVAILABLE:
            self.pending_node_ids.append(node.id)

    def _adjust_selected_attribute(self, amount: int):
        self._ensure_staging()
        stat_name = PRIMARY_ATTRIBUTES[self.current_attribute]
        current = self.pending_attributes.get(stat_name, 0)
        if amount > 0:
            if self._remaining_attribute_points() < amount:
                return
            self.pending_attributes[stat_name] = current + amount
            return
        if current <= 0:
            return
        new_value = max(0, current + amount)
        if new_value:
            self.pending_attributes[stat_name] = new_value
        else:
            self.pending_attributes.pop(stat_name, None)
        self._revalidate_pending_nodes()

    def _revalidate_pending_nodes(self):
        changed = True
        while changed:
            changed = False
            for node_id in reversed(self.pending_node_ids):
                other_nodes = [
                    candidate for candidate in self.pending_node_ids if candidate != node_id
                ]
                statuses = available_nodes(
                    self.player_char,
                    self._selected_tree_id(),
                    planned_node_ids=other_nodes,
                    planned_attributes=self.pending_attributes,
                )
                status = next(candidate for candidate in statuses if candidate.node.id == node_id)
                if status.state != NodeState.AVAILABLE:
                    self.pending_node_ids.remove(node_id)
                    changed = True
                    break

    def _reset_pending(self):
        self._clear_pending()

    def _confirm_staged_promotion(self, node) -> bool:
        target_name = node.payload["target_class"]
        target_ctor = node.payload["target_class_ctor"]
        target_tier = max(1, int(target_ctor().pro_level) - 1)
        promotion_screen = PromotionScreen(
            self.presenter,
            self.player_char,
            [target_name],
            {target_name: target_ctor},
            current_class=node.tree_id,
            pro_level=target_tier,
        )
        return promotion_screen.navigate() == target_name

    def _spend_pending(self):
        if not self.has_pending_changes():
            return
        closures = ()
        if (
            getattr(self.player_char, "cls", None) is not None
            and getattr(self.player_char, "progression", None) is not None
        ):
            closures = permanent_closures_for_plan(
                self.player_char,
                self._selected_tree_id(),
                self.pending_node_ids,
            )
        if closures:
            names = "\n".join(f"- {name}" for name in closures)
            confirmed = ConfirmationPopup(
                self.presenter,
                (
                    "Confirm Permanent Choice?\n\n"
                    "Spending this distribution will permanently close:\n"
                    f"{names}\n\nThese abilities cannot be learned later."
                ),
                show_buttons=True,
            ).show(background_draw_func=self._popup_background)
            if not confirmed:
                return
        promotion_choices_by_node: dict[str, dict] = {}
        node_choices: dict[str, dict] = {}
        for node_id in self.pending_node_ids:
            node = TREE_NODES[node_id]
            category = node.payload.get("xenid_category")
            if category:
                options = list(
                    node.payload.get(
                        "xenid_options",
                        companions.XENID_PAIRS.get(str(category), ()),
                    )
                )
                result = SelectionPopup(
                    self.presenter,
                    self,
                    title=f"Choose {category} Xenid",
                    header_message=(
                        "This choice is permanent. Select the Xenid that will answer this Calling."
                    ),
                    options=options,
                ).show(self.player_char)
                if not result or result[0] != "selection":
                    return
                selected = result[1]
                confirmed = ConfirmationPopup(
                    self.presenter,
                    (f"Permanently bind {selected} to the {category} Calling?"),
                    show_buttons=True,
                ).show(background_draw_func=self._popup_background)
                if not confirmed:
                    return
                node_choices[node_id] = {"xenid": selected}
            if node.kind != NodeKind.PROMOTION:
                continue
            if not self._confirm_staged_promotion(node):
                return
            promotion_choices = self._promotion_choices(
                node.payload["target_class"],
            )
            if promotion_choices is None:
                return
            promotion_choices_by_node[node_id] = promotion_choices
        result = apply_progression_plan(
            self.player_char,
            self.pending_node_ids,
            self.pending_attributes,
            promotion_choices=promotion_choices_by_node,
            node_choices=node_choices,
        )
        if result.success:
            self._clear_pending()
            self.current_node = 0
            self.tree_index = 0
            self.tree_scroll_row = 0
            if self.background_draw_func is not None:
                self.background_draw_func()
            return
        ConfirmationPopup(
            self.presenter,
            result.message,
            show_buttons=False,
        ).show(background_draw_func=self._popup_background)

    def confirm_discard_pending(self) -> bool:
        """Confirm leaving when distributed points have not been committed."""
        if not self.has_pending_changes():
            return True
        popup = ConfirmationPopup(
            self.presenter,
            "Leave Progression?\n\nDistributed points will not be spent.",
            show_buttons=True,
        )
        if not popup.show(background_draw_func=self._popup_background):
            return False
        self._clear_pending()
        return True

    def draw_embedded(self, player_char, rect):
        """Draw progression as a Character Menu tab without flipping."""
        self.player_char = player_char
        tree_width = int(rect.width * 0.74)
        tree_rect = pygame.Rect(
            rect.left,
            rect.top,
            tree_width,
            rect.height,
        )
        attr_rect = pygame.Rect(
            tree_rect.right + 10,
            rect.top,
            rect.right - tree_rect.right - 10,
            min(320, rect.height),
        )
        detail_top = attr_rect.bottom + 10
        detail_rect = pygame.Rect(
            attr_rect.left,
            detail_top,
            attr_rect.width,
            max(1, rect.bottom - detail_top - 48),
        )
        spend_rect = pygame.Rect(
            attr_rect.left,
            rect.bottom - 38,
            attr_rect.width,
            38,
        )
        self._draw_tree(tree_rect)
        self._draw_attributes(attr_rect)
        self._draw_details(detail_rect)
        self._draw_spend_button(spend_rect)

    def handle_event(self, event) -> bool:
        """Handle an event while embedded in the Character Menu."""
        if event.type in (pygame.MOUSEMOTION, pygame.MOUSEBUTTONDOWN):
            if event.type == pygame.MOUSEBUTTONDOWN and event.button in (4, 5):
                delta = -1 if event.button == 4 else 1
                self.current_node = (self.current_node + delta) % max(1, len(self._statuses()))
                return True
            node_index = hit_index(self.node_rects, mouse_position(event))
            if event.type == pygame.MOUSEMOTION:
                self.hovered_node_index = node_index
            attribute_index = hit_index(self.attribute_rects, mouse_position(event))
            minus_index = hit_index(
                self.attribute_minus_rects,
                mouse_position(event),
            )
            plus_index = hit_index(
                self.attribute_plus_rects,
                mouse_position(event),
            )
            if self.reset_button_rect.collidepoint(mouse_position(event)):
                self.focus = "reset"
                if is_left_click(event):
                    self._reset_pending()
                return True
            if self.spend_button_rect.collidepoint(mouse_position(event)):
                self.focus = "spend"
                if is_left_click(event):
                    self._spend_pending()
                return True
            if node_index is not None:
                self.focus = "nodes"
                self.current_node = node_index
                if is_left_click(event):
                    self._toggle_selected_node()
                return True
            if attribute_index is not None:
                self.focus = "attributes"
                self.current_attribute = attribute_index
                if is_left_click(event):
                    if minus_index is not None:
                        self._adjust_selected_attribute(-1)
                    elif plus_index is not None:
                        self._adjust_selected_attribute(1)
                return True
            return False
        if event.type != pygame.KEYDOWN:
            return False
        self.hovered_node_index = None
        if event.key in (pygame.K_q, pygame.K_e):
            direction = -1 if event.key == pygame.K_q else 1
            self.tree_index = (self.tree_index + direction) % len(self._tree_ids())
            self.current_node = 0
            self.tree_scroll_row = 0
            return True
        if event.key == pygame.K_a:
            self.focus = "attributes" if self.focus == "nodes" else "nodes"
            return True
        if event.key == pygame.K_UP:
            if self.focus == "nodes":
                self.current_node = (self.current_node - 1) % len(self._statuses())
            else:
                self.current_attribute = (self.current_attribute - 1) % len(PRIMARY_ATTRIBUTES)
            return True
        if event.key == pygame.K_LEFT:
            if self.focus == "nodes":
                self.current_node = (self.current_node - 1) % len(self._statuses())
            else:
                self.current_attribute = (self.current_attribute - 1) % len(PRIMARY_ATTRIBUTES)
            return True
        if event.key == pygame.K_DOWN:
            if self.focus == "nodes":
                self.current_node = (self.current_node + 1) % len(self._statuses())
            else:
                self.current_attribute = (self.current_attribute + 1) % len(PRIMARY_ATTRIBUTES)
            return True
        if event.key == pygame.K_RIGHT:
            if self.focus == "nodes":
                self.current_node = (self.current_node + 1) % len(self._statuses())
            else:
                self.current_attribute = (self.current_attribute + 1) % len(PRIMARY_ATTRIBUTES)
            return True
        if event.key in (pygame.K_RETURN, pygame.K_SPACE):
            if self.focus == "nodes":
                self._toggle_selected_node()
            elif self.focus == "attributes":
                self._adjust_selected_attribute(1)
            elif self.focus == "reset":
                self._reset_pending()
            elif self.focus == "spend":
                self._spend_pending()
            return True
        if event.key in (pygame.K_MINUS, pygame.K_KP_MINUS):
            if self.focus == "attributes":
                self._adjust_selected_attribute(-1)
                return True
        if event.key in (pygame.K_PLUS, pygame.K_EQUALS, pygame.K_KP_PLUS):
            if self.focus == "attributes":
                self._adjust_selected_attribute(1)
                return True
        if event.key == pygame.K_s:
            self.focus = "spend"
            self._spend_pending()
            return True
        if event.key == pygame.K_r:
            self.focus = "reset"
            self._reset_pending()
            return True
        return False

    def navigate(self):
        """Run the modal screen until the player returns."""
        while True:
            self.draw_all()
            for event in get_events():
                if event.type == pygame.QUIT:
                    return
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        if self.confirm_discard_pending():
                            return
                    if event.key in (pygame.K_q, pygame.K_e):
                        direction = -1 if event.key == pygame.K_q else 1
                        self.tree_index = (self.tree_index + direction) % len(self._tree_ids())
                        self.current_node = 0
                    if event.key == pygame.K_TAB:
                        self.focus = "attributes" if self.focus == "nodes" else "nodes"
                    elif event.key in (pygame.K_UP, pygame.K_LEFT):
                        if self.focus == "nodes":
                            self.current_node = (self.current_node - 1) % len(self._statuses())
                        else:
                            self.current_attribute = (self.current_attribute - 1) % len(
                                PRIMARY_ATTRIBUTES
                            )
                    elif event.key in (pygame.K_DOWN, pygame.K_RIGHT):
                        if self.focus == "nodes":
                            self.current_node = (self.current_node + 1) % len(self._statuses())
                        else:
                            self.current_attribute = (self.current_attribute + 1) % len(
                                PRIMARY_ATTRIBUTES
                            )
                    elif event.key in (pygame.K_RETURN, pygame.K_SPACE):
                        if self.focus == "nodes":
                            self._toggle_selected_node()
                        else:
                            self._adjust_selected_attribute(1)
                elif event.type in (pygame.MOUSEMOTION, pygame.MOUSEBUTTONDOWN):
                    node_index = hit_index(self.node_rects, mouse_position(event))
                    if event.type == pygame.MOUSEMOTION:
                        self.hovered_node_index = node_index
                    attribute_index = hit_index(self.attribute_rects, mouse_position(event))
                    if node_index is not None:
                        self.focus = "nodes"
                        self.current_node = node_index
                        if is_left_click(event):
                            self._toggle_selected_node()
                    elif attribute_index is not None:
                        self.focus = "attributes"
                        self.current_attribute = attribute_index
                        if is_left_click(event):
                            minus_index = hit_index(
                                self.attribute_minus_rects,
                                mouse_position(event),
                            )
                            plus_index = hit_index(
                                self.attribute_plus_rects,
                                mouse_position(event),
                            )
                            if minus_index is not None:
                                self._adjust_selected_attribute(-1)
                            elif plus_index is not None:
                                self._adjust_selected_attribute(1)
            self.presenter.clock.tick(30)
