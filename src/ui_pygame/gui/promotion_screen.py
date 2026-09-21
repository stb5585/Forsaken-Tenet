"""Promotion selection screen with detailed class-impact previews."""

import pygame

from src.core.classes import promotion_mechanic_details, promotion_mechanic_tab_label
from src.core.progression import promotion_combat_bonuses
from src.ui_pygame.screen_runtime import get_events

from .confirmation_popup import ConfirmationPopup
from .mouse_helpers import hit_index, is_left_click, mouse_position
from .town_base import TownScreenBase, wrap_text_to_pixel_width


class PromotionScreen(TownScreenBase):
    """Promotion selection UI styled like the other town menus."""

    MECHANIC_TEXT_COLOR = (105, 185, 225)
    STAT_LABEL_COLOR = (210, 190, 145)
    ZERO_DELTA_COLOR = (175, 185, 210)

    def __init__(self, presenter, player_char, options, option_map, current_class, pro_level):
        super().__init__(presenter)
        self.player_char = player_char
        self.options = list(options) + ["Go Back"]
        self.option_map = option_map
        self.current_class = current_class
        self.pro_level = pro_level
        self.current_selection = 0

        self.container_rect = self._build_container_rect()
        self.options_width = 240

    def _build_container_rect(self):
        width = int(self.width * 0.92)
        height = int(self.height * 0.76)
        x = (self.width - width) // 2
        y = int(self.height * 0.14)
        return pygame.Rect(x, y, width, height)

    def _wrap_lines(self, text, font, max_width):
        """Wrap paragraphs to the available rendered width."""
        lines = []
        for paragraph in text.splitlines():
            if not paragraph.strip():
                lines.append("")
                continue
            lines.extend(wrap_text_to_pixel_width(paragraph, font, max_width))
        return lines

    def _restriction_changes(self, cls_instance):
        """Return equipment allowances added or removed by a promotion."""
        current_class = getattr(self.player_char, "cls", None)
        current = getattr(current_class, "restrictions", {}) or {}
        target = cls_instance.restrictions
        changes = []
        for slot in dict.fromkeys((*current, *target)):
            current_allowed = list(current.get(slot, ()))
            target_allowed = list(target.get(slot, ()))
            gained = [item_type for item_type in target_allowed if item_type not in current_allowed]
            lost = [item_type for item_type in current_allowed if item_type not in target_allowed]
            if gained or lost:
                changes.append((slot, gained, lost))
        return changes

    @staticmethod
    def _restriction_change_text(slot, gained, lost):
        """Describe changed equipment allowances without repeating unchanged ones."""
        parts = []
        if gained:
            parts.append(f"allows {', '.join(gained)}")
        if lost:
            parts.append(f"no longer allows {', '.join(lost)}")
        return f"{slot}: {'; '.join(parts)}"

    def _stat_pairs(self, cls_instance):
        pc = self.player_char
        combat_bonuses = promotion_combat_bonuses(cls_instance)
        return [
            (
                ("Strength", pc.stats.strength + cls_instance.str_plus, cls_instance.str_plus),
                ("Health", pc.health.max + (cls_instance.con_plus * 2), cls_instance.con_plus * 2),
            ),
            (
                ("Intelligence", pc.stats.intel + cls_instance.int_plus, cls_instance.int_plus),
                ("Mana", pc.mana.max + (cls_instance.int_plus * 2), cls_instance.int_plus * 2),
            ),
            (
                ("Wisdom", pc.stats.wisdom + cls_instance.wis_plus, cls_instance.wis_plus),
                ("Attack", pc.combat.attack + combat_bonuses["attack"], combat_bonuses["attack"]),
            ),
            (
                ("Constitution", pc.stats.con + cls_instance.con_plus, cls_instance.con_plus),
                (
                    "Defense",
                    pc.combat.defense + combat_bonuses["defense"],
                    combat_bonuses["defense"],
                ),
            ),
            (
                ("Charisma", pc.stats.charisma + cls_instance.cha_plus, cls_instance.cha_plus),
                ("Magic", pc.combat.magic + combat_bonuses["magic"], combat_bonuses["magic"]),
            ),
            (
                ("Dexterity", pc.stats.dex + cls_instance.dex_plus, cls_instance.dex_plus),
                (
                    "Magic Defense",
                    pc.combat.magic_def + combat_bonuses["magic defense"],
                    combat_bonuses["magic defense"],
                ),
            ),
        ]

    def _stat_delta_color(self, delta):
        if delta > 0:
            return self.colors.GREEN
        if delta < 0:
            return self.colors.RED
        return self.ZERO_DELTA_COLOR

    def _draw_wrapped_lines(self, lines, font, color, x, y, line_height, *, max_y=None):
        for line in lines:
            if max_y is not None and y + line_height > max_y:
                break
            text = font.render(line, True, color)
            self.screen.blit(text, (x, y))
            y += line_height
        return y

    def _draw_promotion_stat_grid(self, rect, cls_instance, y):
        header = self.normal_font.render("Promotion Impact", True, self.colors.GOLD)
        self.screen.blit(header, (rect.left + 18, y))
        y += header.get_height() + 8

        line_height = self.small_font.get_height() + 6
        col_width = (rect.width - 68) // 2
        col1_x = rect.left + 24
        col2_x = rect.left + 42 + col_width
        for left, right in self._stat_pairs(cls_instance):
            for x, row in ((col1_x, left), (col2_x, right)):
                label, value, delta = row
                label_text = self.small_font.render(
                    label,
                    True,
                    self.STAT_LABEL_COLOR,
                )
                self.screen.blit(label_text, (x, y))

                value_x = x + min(120, max(88, col_width // 2))
                value_text = self.small_font.render(str(value), True, self.colors.WHITE)
                self.screen.blit(value_text, (value_x, y))

                delta_text = f"+{delta}" if delta >= 0 else str(delta)
                delta_surface = self.small_font.render(
                    delta_text, True, self._stat_delta_color(delta)
                )
                self.screen.blit(delta_surface, (value_x + 48, y))
            y += line_height
        return y

    def _draw_header(self):
        top_rect = pygame.Rect(0, 0, self.width, self.height // 12)
        self.draw_semi_transparent_panel(top_rect)
        pygame.draw.rect(self.screen, self.colors.BORDER_COLOR, top_rect, 2)

        title = self.normal_font.render("Class Promotion", True, self.colors.GOLD)
        title_rect = title.get_rect(center=(self.width // 2, top_rect.centery - 12))
        self.screen.blit(title, title_rect)

        tier_label = {1: "First Promotion", 2: "Second Promotion"}.get(
            self.pro_level, "Final Promotion"
        )
        subtext = self.small_font.render(
            f"Current Class: {self.current_class}  •  {tier_label}", True, self.colors.WHITE
        )
        sub_rect = subtext.get_rect(center=(self.width // 2, top_rect.centery + 12))
        self.screen.blit(subtext, sub_rect)

    def _draw_options_panel(self):
        options_rect = self.options_panel_rect()
        self.draw_semi_transparent_panel(options_rect)
        pygame.draw.rect(self.screen, self.colors.BORDER_COLOR, options_rect, 2)

        header = self.normal_font.render("Choose your path", True, self.colors.GOLD)
        header_rect = header.get_rect(centerx=options_rect.centerx, top=options_rect.top + 20)
        self.screen.blit(header, header_rect)

        option_rects = self.option_rects()
        for idx, option in enumerate(self.options):
            highlight_rect = option_rects[idx]
            if idx == self.current_selection:
                pygame.draw.rect(self.screen, self.colors.HIGHLIGHT_BG, highlight_rect)
                pygame.draw.rect(self.screen, self.colors.GOLD, highlight_rect, 2)
                color = self.colors.GOLD
            else:
                color = self.colors.WHITE

            text = self.normal_font.render(option, True, color)
            text_rect = text.get_rect(center=highlight_rect.center)
            self.screen.blit(text, text_rect)

    def options_panel_rect(self) -> pygame.Rect:
        """Return the promotion option panel geometry."""
        return pygame.Rect(
            self.container_rect.right - self.options_width - 20,
            self.container_rect.top + 20,
            self.options_width,
            self.container_rect.height - 40,
        )

    def option_rects(self) -> list[pygame.Rect]:
        """Return clickable rectangles for promotion options."""
        options_rect = self.options_panel_rect()
        line_height = self.normal_font.get_height() + 12
        start_y = options_rect.centery - (line_height * len(self.options) // 2)
        return [
            pygame.Rect(
                options_rect.left + 12,
                start_y + idx * line_height - 6,
                options_rect.width - 24,
                line_height,
            )
            for idx, _option in enumerate(self.options)
        ]

    def _draw_detail_panel(self, cls_ctor):
        cls_instance = cls_ctor()
        left_rect = pygame.Rect(
            self.container_rect.left + 20,
            self.container_rect.top + 20,
            self.container_rect.width - self.options_width - 60,
            self.container_rect.height - 40,
        )
        self.draw_semi_transparent_panel(left_rect)
        pygame.draw.rect(self.screen, self.colors.BORDER_COLOR, left_rect, 2)

        y = left_rect.top + 14

        transition = f"{self.current_class} -> {cls_instance.name}"
        name_text = self.large_font.render(transition, True, self.colors.GOLD)
        name_rect = name_text.get_rect(centerx=left_rect.centerx, top=y)
        self.screen.blit(name_text, name_rect)
        y = name_rect.bottom + 8

        content_x = left_rect.left + 18
        content_width = left_rect.right - content_x - 18
        description = " ".join(cls_instance.description.splitlines())
        desc_lines = self._wrap_lines(
            description,
            self.small_font,
            content_width,
        )
        line_height = self.small_font.get_height() + 4
        desc_start_y = y
        y = self._draw_wrapped_lines(
            desc_lines[:4],
            self.small_font,
            self.colors.WHITE,
            content_x,
            y,
            line_height,
        )

        # Reserve a fixed block for descriptions so lower sections stay aligned
        y = desc_start_y + (line_height * 4) + 10

        mechanic_tab = promotion_mechanic_tab_label(cls_instance.name)
        mechanic_guidance = promotion_mechanic_details(cls_instance.name)
        if mechanic_tab or mechanic_guidance:
            note = mechanic_guidance
            if mechanic_tab:
                note = f"Character Menu: {mechanic_tab}"
            if mechanic_tab and mechanic_guidance:
                note = f"{note} - {mechanic_guidance}"
            note_lines = self._wrap_lines(
                note,
                self.small_font,
                content_width,
            )[:3]
            y = self._draw_wrapped_lines(
                note_lines,
                self.small_font,
                self.MECHANIC_TEXT_COLOR,
                content_x,
                y,
                line_height,
            )
            y += 8

        y = self._draw_promotion_stat_grid(left_rect, cls_instance, y)
        y += 10
        rest_header = self.normal_font.render("Equipment Restrictions", True, self.colors.GOLD)
        self.screen.blit(rest_header, (left_rect.left + 18, y))
        y = rest_header.get_height() + y + 4

        line_height = self.small_font.get_height() + 5
        max_restriction_y = left_rect.bottom - 48
        restriction_changes = self._restriction_changes(cls_instance)
        if not restriction_changes:
            restriction_changes = [
                ("", ["No equipment restrictions change."], []),
            ]
        for slot, gained, lost in restriction_changes:
            if slot:
                line = self._restriction_change_text(slot, gained, lost)
            else:
                line = gained[0]
            for wrapped in self._wrap_lines(
                line,
                self.small_font,
                content_width - 10,
            ):
                if y + line_height > max_restriction_y:
                    break
                text = self.small_font.render(wrapped, True, self.colors.WHITE)
                self.screen.blit(text, (left_rect.left + 28, y))
                y += line_height

        note = "Existing legal gear is kept; illegal gear moves to inventory."
        note_lines = self._wrap_lines(
            note,
            self.small_font,
            content_width - 10,
        )
        note_y = left_rect.bottom - 18 - (len(note_lines) * line_height)
        for wrapped in note_lines:
            text = self.small_font.render(wrapped, True, self.colors.GRAY)
            self.screen.blit(text, (left_rect.left + 28, note_y))
            note_y += line_height

    def _draw_instructions(self):
        hint = "UP/DOWN: Select   ENTER: Promote   ESC: Cancel"
        text = self.small_font.render(hint, True, self.colors.GRAY)
        rect = text.get_rect(centerx=self.width // 2, bottom=self.height - 16)
        self.screen.blit(text, rect)

    def draw_all(self):
        self.draw_background()
        self._draw_header()

        if self.options:
            selected_name = self.options[self.current_selection]
            cls_ctor = self.option_map.get(selected_name)
            if cls_ctor:
                self._draw_detail_panel(cls_ctor)

        self._draw_options_panel()
        self._draw_instructions()
        pygame.display.flip()

    def draw_modal_background(self):
        """Redraw the promotion preview behind confirmation popups."""
        self.draw_background()
        self._draw_header()

        if self.options:
            selected_name = self.options[self.current_selection]
            cls_ctor = self.option_map.get(selected_name)
            if cls_ctor:
                self._draw_detail_panel(cls_ctor)

        self._draw_options_panel()
        self._draw_instructions()

    def _confirmation_kwargs(self):
        kwargs = self.popup_show_kwargs()
        kwargs.setdefault("background_draw_func", self.draw_modal_background)
        return kwargs

    def navigate(self):
        if not self.options:
            return None

        while True:
            self.draw_all()
            for event in get_events():
                if event.type == pygame.QUIT:
                    pygame.quit()
                    import sys

                    sys.exit()
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_UP:
                        self.current_selection = (self.current_selection - 1) % len(self.options)
                    elif event.key == pygame.K_DOWN:
                        self.current_selection = (self.current_selection + 1) % len(self.options)
                    elif event.key in (pygame.K_RETURN, pygame.K_SPACE):
                        selected_name = self.options[self.current_selection]
                        if selected_name == "Go Back":
                            return None
                        popup = ConfirmationPopup(self.presenter, f"Promote to {selected_name}?")
                        if popup.show(**self._confirmation_kwargs()):
                            return selected_name
                    elif event.key == pygame.K_ESCAPE:
                        return None
                elif event.type in (pygame.MOUSEMOTION, pygame.MOUSEBUTTONDOWN):
                    hovered = hit_index(self.option_rects(), mouse_position(event))
                    if hovered is None:
                        continue
                    self.current_selection = hovered
                    if not is_left_click(event):
                        continue
                    selected_name = self.options[self.current_selection]
                    if selected_name == "Go Back":
                        return None
                    popup = ConfirmationPopup(self.presenter, f"Promote to {selected_name}?")
                    if popup.show(**self._confirmation_kwargs()):
                        return selected_name
            self.presenter.clock.tick(30)
