"""Visual character naming screen for the Pygame creation flow."""

from __future__ import annotations

import random
import sys
from pathlib import Path

import pygame

from src.ui_pygame.assets.portrait_manager import PORTRAIT_ROOT, PortraitManager
from src.ui_pygame.screen_runtime import get_events

from .confirmation_popup import ConfirmationPopup
from .input_guards import (
    prepare_guarded_input,
    release_guard_allows_input,
    update_input_armed_from_event,
)
from .town_base import TownColors

PORTRAIT_DIR = PORTRAIT_ROOT
MAX_NAME_LENGTH = 20
SEX_OPTIONS = ("Male", "Female")


class CharacterNamingScreen:
    """Name-entry screen that previews the selected character identity."""

    def __init__(self, presenter, race_name: str, class_name: str, sex: str = "Male"):
        self.presenter = presenter
        self.screen = presenter.screen
        self.width = presenter.width
        self.height = presenter.height
        self.race_name = race_name
        self.class_name = class_name
        self.sex = self.normalized_sex(sex)
        self.colors = TownColors
        self.title_font = presenter.title_font
        self.large_font = presenter.large_font
        self.normal_font = presenter.normal_font
        self.small_font = presenter.small_font
        self.text = ""
        self.portrait_manager = PortraitManager()
        self.portrait_variant_count = self.portrait_manager.variant_count()
        self.selected_portrait_variant = random.randrange(self.portrait_variant_count)
        self.portrait = self.load_portrait()
        self.previous_portrait_rect: pygame.Rect | None = None
        self.next_portrait_rect: pygame.Rect | None = None
        self.sex_button_rects: dict[str, pygame.Rect] = {}
        self.calculate_rects()

    @staticmethod
    def normalized_sex(sex: str) -> str:
        normalized = str(sex or "Male").strip().lower()
        return "Female" if normalized == "female" else "Male"

    @staticmethod
    def portrait_filename(race_name: str, sex: str) -> str:
        race_key = PortraitManager.normalize_key(race_name, "human")
        return f"{race_key}_base_portraits.png"

    @property
    def portrait_path(self) -> Path:
        return PORTRAIT_DIR / self.portrait_filename(self.race_name, self.sex)

    def load_portrait(self) -> pygame.Surface:
        return self.portrait_manager.get_portrait(
            self.race_name,
            self.sex,
            variant=self.selected_portrait_variant,
        )

    def cycle_portrait(self, delta: int) -> None:
        if self.portrait_variant_count <= 1:
            return
        self.selected_portrait_variant = (
            self.selected_portrait_variant + delta
        ) % self.portrait_variant_count
        self.portrait = self.load_portrait()

    def select_sex(self, sex: str) -> None:
        selected = self.normalized_sex(sex)
        if selected == self.sex:
            return
        self.sex = selected
        self.portrait = self.load_portrait()

    def calculate_rects(self) -> None:
        header_height = self.height // 12
        self.header_rect = pygame.Rect(0, 0, self.width, header_height)

        margin = max(24, self.width // 32)
        gap = max(20, self.width // 48)
        content_top = self.header_rect.bottom
        content_height = self.height - content_top
        panel_width = (self.width - margin * 2 - gap) // 2
        panel_height = content_height - margin * 2
        self.preview_rect = pygame.Rect(margin, content_top + margin, panel_width, panel_height)
        self.name_rect = pygame.Rect(
            self.preview_rect.right + gap, content_top + margin, panel_width, panel_height
        )

    def draw_header(self) -> None:
        pygame.draw.rect(self.screen, self.colors.BLACK, self.header_rect)
        pygame.draw.rect(self.screen, self.colors.BORDER_COLOR, self.header_rect, 2)
        title = self.normal_font.render("Name your character", True, self.colors.GOLD)
        title_rect = title.get_rect(centerx=self.width // 2, centery=self.header_rect.centery)
        self.screen.blit(title, title_rect)

    def portrait_preview_rect(self) -> pygame.Rect:
        source_width, source_height = (225, 400)
        if self.portrait is not None:
            source_width, source_height = self.portrait.get_size()

        max_width = min(self.preview_rect.width - 48, 280)
        max_height = min(max(120, self.preview_rect.height - 190), 400)
        scale = min(max_width / source_width, max_height / source_height)
        portrait_width = max(1, int(source_width * scale))
        portrait_height = max(1, int(source_height * scale))
        portrait_rect = pygame.Rect(0, 0, portrait_width, portrait_height)
        portrait_rect.centerx = self.preview_rect.centerx
        portrait_rect.top = self.preview_rect.top + 30
        return portrait_rect

    def draw_preview(self) -> None:
        pygame.draw.rect(self.screen, self.colors.BLACK, self.preview_rect)
        pygame.draw.rect(self.screen, self.colors.BORDER_COLOR, self.preview_rect, 2)

        portrait_rect = self.portrait_preview_rect()
        pygame.draw.rect(self.screen, self.colors.DARK_GRAY, portrait_rect)
        pygame.draw.rect(self.screen, self.colors.BORDER_COLOR, portrait_rect, 2)

        if self.portrait is not None:
            fitted = pygame.transform.smoothscale(self.portrait, portrait_rect.size)
            self.screen.blit(fitted, portrait_rect)
            pygame.draw.rect(self.screen, self.colors.BORDER_COLOR, portrait_rect, 2)
        else:
            placeholder = self.small_font.render("Portrait", True, self.colors.GRAY)
            placeholder_rect = placeholder.get_rect(center=portrait_rect.center)
            self.screen.blit(placeholder, placeholder_rect)

        controls_bottom = self.draw_portrait_controls(portrait_rect)
        sex_bottom = self.draw_sex_buttons(controls_bottom)

        details = (
            ("Race", self.race_name),
            ("Class", self.class_name),
        )
        y = sex_bottom + 22
        label_x = self.preview_rect.left + 48
        value_x = self.preview_rect.right - 48
        for label, value in details:
            label_text = self.normal_font.render(label, True, self.colors.GRAY)
            value_text = self.normal_font.render(value, True, self.colors.WHITE)
            self.screen.blit(label_text, (label_x, y))
            value_rect = value_text.get_rect(right=value_x, top=y)
            self.screen.blit(value_text, value_rect)
            y += self.normal_font.get_height() + 16

    def draw_portrait_controls(self, portrait_rect: pygame.Rect) -> int:
        self.previous_portrait_rect = None
        self.next_portrait_rect = None
        count_bottom = portrait_rect.bottom
        if self.portrait_variant_count <= 1:
            return count_bottom

        button_size = 42
        center_y = portrait_rect.centery
        self.previous_portrait_rect = pygame.Rect(
            max(self.preview_rect.left + 12, portrait_rect.left - button_size - 12),
            center_y - button_size // 2,
            button_size,
            button_size,
        )
        self.next_portrait_rect = pygame.Rect(
            min(self.preview_rect.right - button_size - 12, portrait_rect.right + 12),
            center_y - button_size // 2,
            button_size,
            button_size,
        )
        for label, rect in (("<", self.previous_portrait_rect), (">", self.next_portrait_rect)):
            pygame.draw.rect(self.screen, self.colors.DARK_GRAY, rect)
            pygame.draw.rect(self.screen, self.colors.GOLD, rect, 2)
            surface = self.large_font.render(label, True, self.colors.GOLD)
            self.screen.blit(surface, surface.get_rect(center=rect.center))

        count_text = self.small_font.render(
            f"Portrait {self.selected_portrait_variant + 1}/{self.portrait_variant_count}",
            True,
            self.colors.GRAY,
        )
        count_rect = count_text.get_rect(
            centerx=portrait_rect.centerx, top=portrait_rect.bottom + 8
        )
        self.screen.blit(count_text, count_rect)
        return count_rect.bottom

    def draw_sex_buttons(self, top_y: int) -> int:
        button_width = min(140, max(96, (self.preview_rect.width - 128) // 2))
        button_height = 38
        gap = 18
        total_width = button_width * 2 + gap
        start_x = self.preview_rect.centerx - total_width // 2
        y = top_y + 14
        self.sex_button_rects = {}
        for index, option in enumerate(SEX_OPTIONS):
            rect = pygame.Rect(
                start_x + index * (button_width + gap), y, button_width, button_height
            )
            self.sex_button_rects[option] = rect
            selected = option == self.sex
            fill = self.colors.HIGHLIGHT_BG if selected else self.colors.DARK_GRAY
            border = self.colors.GOLD if selected else self.colors.BORDER_COLOR
            pygame.draw.rect(self.screen, fill, rect)
            pygame.draw.rect(self.screen, border, rect, 2)
            label = self.normal_font.render(
                option, True, self.colors.GOLD if selected else self.colors.WHITE
            )
            self.screen.blit(label, label.get_rect(center=rect.center))
        return y + button_height

    def draw_name_entry(self) -> None:
        pygame.draw.rect(self.screen, self.colors.BLACK, self.name_rect)
        pygame.draw.rect(self.screen, self.colors.BORDER_COLOR, self.name_rect, 2)

        x = self.name_rect.left + 42
        title_y = self.name_rect.top + 52
        title = self.title_font.render("Choose a Name", True, self.colors.GOLD)
        self.screen.blit(title, (x, title_y))

        input_width = self.name_rect.width - 84
        input_height = max(64, self.large_font.get_height() + 28)
        input_rect = pygame.Rect(x, title_y + title.get_height() + 42, input_width, input_height)
        pygame.draw.rect(self.screen, self.colors.DARK_GRAY, input_rect)
        pygame.draw.rect(self.screen, self.colors.GOLD, input_rect, 2)

        display_text = f"{self.text}_" if self.text else "_"
        available_width = input_rect.width - 36
        entry_font = self.large_font
        if entry_font.render(display_text, True, self.colors.WHITE).get_width() > available_width:
            entry_font = self.normal_font
        if entry_font.render(display_text, True, self.colors.WHITE).get_width() > available_width:
            entry_font = self.small_font
        name_surface = entry_font.render(display_text, True, self.colors.WHITE)
        name_rect = name_surface.get_rect(left=input_rect.left + 18, centery=input_rect.centery)
        self.screen.blit(name_surface, name_rect)

        hint = self.small_font.render(
            "ENTER: Confirm   BACKSPACE: Delete   ESC: Back", True, self.colors.GRAY
        )
        hint_rect = hint.get_rect(left=x, top=input_rect.bottom + 24)
        self.screen.blit(hint, hint_rect)

        current_name = self.text if self.text else "Hero"
        preview = self.normal_font.render(f"Created as {current_name}", True, self.colors.GOLD)
        preview_rect = preview.get_rect(left=x, bottom=self.name_rect.bottom - 46)
        self.screen.blit(preview, preview_rect)

    def draw(self) -> None:
        self.screen.fill(self.colors.BLACK)
        self.draw_header()
        self.draw_preview()
        self.draw_name_entry()

    def navigate(
        self,
        default: str = "Hero",
        flush_events: bool = False,
        require_key_release: bool = False,
    ) -> str | None:
        input_armed = prepare_guarded_input(
            flush_events=flush_events,
            require_key_release=require_key_release,
        )

        while True:
            self.draw()
            pygame.display.flip()

            input_armed = release_guard_allows_input(require_key_release, input_armed)
            for event in get_events():
                if event.type == pygame.QUIT:
                    pygame.quit()
                    sys.exit()

                input_armed = update_input_armed_from_event(event, require_key_release, input_armed)
                if (
                    event.type == pygame.MOUSEBUTTONDOWN
                    and getattr(event, "button", None) == 1
                    and input_armed
                ):
                    pos = getattr(event, "pos", None)
                    if pos is not None:
                        if (
                            self.previous_portrait_rect
                            and self.previous_portrait_rect.collidepoint(pos)
                        ):
                            self.cycle_portrait(-1)
                            continue
                        if self.next_portrait_rect and self.next_portrait_rect.collidepoint(pos):
                            self.cycle_portrait(1)
                            continue
                        for sex, rect in self.sex_button_rects.items():
                            if rect.collidepoint(pos):
                                self.select_sex(sex)
                                continue
                if event.type != pygame.KEYDOWN or not input_armed:
                    continue
                if event.key == pygame.K_LEFT:
                    self.cycle_portrait(-1)
                    continue
                if event.key == pygame.K_RIGHT:
                    self.cycle_portrait(1)
                    continue
                text_input = getattr(event, "unicode", "")
                printable_text = bool(text_input and text_input.isprintable())
                if event.key == pygame.K_m and not printable_text:
                    self.select_sex("Male")
                    continue
                if event.key == pygame.K_f and not printable_text:
                    self.select_sex("Female")
                    continue
                if event.key == pygame.K_RETURN:
                    return self.text.strip() or default
                if event.key == pygame.K_ESCAPE:
                    return None
                if event.key == pygame.K_BACKSPACE:
                    self.text = self.text[:-1]
                    continue
                if text_input and text_input.isprintable() and len(self.text) < MAX_NAME_LENGTH:
                    self.text += text_input

            self.presenter.clock.tick(30)


class CompanionNamingScreen:
    """Name-entry screen for newly tamed companions."""

    def __init__(
        self, presenter, companion_name: str, species: str = "", form: str = "", special: str = ""
    ):
        self.presenter = presenter
        self.screen = presenter.screen
        self.width = presenter.width
        self.height = presenter.height
        self.companion_name = str(companion_name or "Companion")
        self.species = str(species or "")
        self.form = str(form or "")
        self.special = str(special or "")
        self.colors = TownColors
        self.title_font = presenter.title_font
        self.large_font = presenter.large_font
        self.normal_font = presenter.normal_font
        self.small_font = presenter.small_font
        self.text = ""
        self.calculate_rects()

    def calculate_rects(self) -> None:
        header_height = self.height // 12
        self.header_rect = pygame.Rect(0, 0, self.width, header_height)
        margin = max(24, self.width // 28)
        self.panel_rect = pygame.Rect(
            margin,
            self.header_rect.bottom + margin,
            self.width - margin * 2,
            self.height - self.header_rect.height - margin * 2,
        )

    def draw_header(self) -> None:
        pygame.draw.rect(self.screen, self.colors.BLACK, self.header_rect)
        pygame.draw.rect(self.screen, self.colors.BORDER_COLOR, self.header_rect, 2)
        title = self.normal_font.render("Tame Complete", True, self.colors.GOLD)
        self.screen.blit(
            title, title.get_rect(centerx=self.width // 2, centery=self.header_rect.centery)
        )

    def draw(self, background_surface: pygame.Surface | None = None) -> None:
        if background_surface is not None:
            self.screen.blit(background_surface, (0, 0))
            overlay = pygame.Surface((self.width, self.height), pygame.SRCALPHA)
            overlay.fill((0, 0, 0, 170))
            self.screen.blit(overlay, (0, 0))
        else:
            self.screen.fill(self.colors.BLACK)
        self.draw_header()
        pygame.draw.rect(self.screen, (8, 8, 12), self.panel_rect)
        pygame.draw.rect(self.screen, self.colors.BORDER_COLOR, self.panel_rect, 2)

        x = self.panel_rect.left + 48
        y = self.panel_rect.top + 46
        title = self.title_font.render("Name Your Companion", True, self.colors.GOLD)
        self.screen.blit(title, (x, y))
        y += title.get_height() + 22

        details = [("Animal", self.companion_name)]
        if self.species:
            details.append(("Family", self.species))
        if self.form:
            details.append(("Form", self.form))
        if self.special:
            details.append(("Trait", self.special))
        for label, value in details:
            label_text = self.normal_font.render(label, True, self.colors.GRAY)
            value_text = self.normal_font.render(value, True, self.colors.WHITE)
            self.screen.blit(label_text, (x, y))
            self.screen.blit(value_text, (x + 150, y))
            y += self.normal_font.get_height() + 12

        input_rect = pygame.Rect(
            x, y + 18, self.panel_rect.width - 96, max(62, self.large_font.get_height() + 26)
        )
        pygame.draw.rect(self.screen, self.colors.DARK_GRAY, input_rect)
        pygame.draw.rect(self.screen, self.colors.GOLD, input_rect, 2)

        display_text = f"{self.text}_" if self.text else "_"
        entry_font = self.large_font
        available_width = input_rect.width - 36
        if entry_font.render(display_text, True, self.colors.WHITE).get_width() > available_width:
            entry_font = self.normal_font
        if entry_font.render(display_text, True, self.colors.WHITE).get_width() > available_width:
            entry_font = self.small_font
        surface = entry_font.render(display_text, True, self.colors.WHITE)
        self.screen.blit(
            surface, surface.get_rect(left=input_rect.left + 18, centery=input_rect.centery)
        )

        preview_name = self.text.strip() or self.companion_name
        if preview_name != self.companion_name:
            preview_name = f"{preview_name} ({self.companion_name})"
        preview = self.normal_font.render(f"Known as {preview_name}", True, self.colors.GOLD)
        self.screen.blit(preview, preview.get_rect(left=x, top=input_rect.bottom + 24))

        hint = self.small_font.render(
            "ENTER: Confirm   BACKSPACE: Delete   ESC: Keep original name", True, self.colors.GRAY
        )
        self.screen.blit(hint, hint.get_rect(left=x, bottom=self.panel_rect.bottom - 36))

    def navigate(
        self,
        default: str = "",
        flush_events: bool = False,
        require_key_release: bool = False,
        background_surface: pygame.Surface | None = None,
    ) -> str | None:
        input_armed = prepare_guarded_input(
            flush_events=flush_events,
            require_key_release=require_key_release,
        )

        while True:
            self.draw(background_surface)
            pygame.display.flip()
            input_armed = release_guard_allows_input(require_key_release, input_armed)
            for event in get_events():
                if event.type == pygame.QUIT:
                    pygame.quit()
                    sys.exit()
                input_armed = update_input_armed_from_event(event, require_key_release, input_armed)
                if event.type != pygame.KEYDOWN or not input_armed:
                    continue
                if event.key == pygame.K_RETURN:
                    chosen = self.text.strip() or default
                    display_name = chosen or self.companion_name
                    if chosen and chosen != self.companion_name:
                        display_name = f"{chosen} ({self.companion_name})"
                    confirm = ConfirmationPopup(
                        self.presenter, f"Keep the name {display_name}?", show_buttons=True
                    )
                    if confirm.show(
                        background_draw_func=lambda: self.draw(background_surface),
                        flush_events=True,
                        require_key_release=True,
                    ):
                        return chosen
                    input_armed = prepare_guarded_input(flush_events=True, require_key_release=True)
                    continue
                if event.key == pygame.K_ESCAPE:
                    return default
                if event.key == pygame.K_BACKSPACE:
                    self.text = self.text[:-1]
                    continue
                text_input = getattr(event, "unicode", "")
                if text_input and text_input.isprintable() and len(self.text) < MAX_NAME_LENGTH:
                    self.text += text_input
            self.presenter.clock.tick(30)
