"""Presentation-polish screens for character creation and story beats."""

from __future__ import annotations

import sys
import textwrap
from typing import Iterable

import pygame

from src.ui_pygame.assets.portrait_manager import PortraitManager
from src.ui_pygame.screen_runtime import get_events

from .input_guards import (
    prepare_guarded_input,
    release_guard_allows_input,
    update_input_armed_from_event,
)
from .mouse_helpers import is_left_click, mouse_position
from .town_base import TownColors


class _PresentationScreenBase:
    """Shared drawing and guarded-input helpers for one-shot presentation screens."""

    def __init__(self, presenter) -> None:
        self.presenter = presenter
        self.screen = presenter.screen
        self.width = presenter.width
        self.height = presenter.height
        self.colors = TownColors
        self.title_font = presenter.title_font
        self.large_font = presenter.large_font
        self.normal_font = presenter.normal_font
        self.small_font = presenter.small_font
        self.continue_rect = pygame.Rect(0, 0, 1, 1)

    @staticmethod
    def _font_height(font) -> int:
        getter = getattr(font, "get_height", None)
        if callable(getter):
            return int(getter())
        return int(font.size("Ag")[1])

    @staticmethod
    def _surface_width(surface) -> int:
        getter = getattr(surface, "get_width", None)
        if callable(getter):
            return int(getter())
        return int(surface.get_size()[0])

    def _draw_background(self) -> None:
        self.screen.fill((9, 9, 14))
        band_height = max(140, self.height // 4)
        band = pygame.Surface((self.width, band_height), pygame.SRCALPHA)
        band.fill((28, 22, 34, 210))
        self.screen.blit(band, (0, 0))
        pygame.draw.line(
            self.screen, (124, 102, 58), (0, band_height), (self.width, band_height), 2
        )

    def _draw_panel(self, rect: pygame.Rect, *, fill=(18, 18, 24), border=None) -> None:
        panel = pygame.Surface(rect.size, pygame.SRCALPHA)
        panel.fill((*fill, 232))
        self.screen.blit(panel, rect.topleft)
        pygame.draw.rect(self.screen, border or self.colors.BORDER_COLOR, rect, 2)

    def _wrap_text(self, text: str, font, max_width: int) -> list[str]:
        lines: list[str] = []
        for paragraph in str(text).splitlines() or [""]:
            words = paragraph.split()
            if not words:
                lines.append("")
                continue
            line = words[0]
            for word in words[1:]:
                candidate = f"{line} {word}"
                if font.size(candidate)[0] <= max_width:
                    line = candidate
                else:
                    lines.append(line)
                    line = word
            lines.append(line)
        return lines

    def _draw_wrapped_text(
        self,
        text: str,
        font,
        color: tuple[int, int, int],
        rect: pygame.Rect,
        *,
        line_gap: int = 6,
    ) -> int:
        y = rect.top
        line_height = self._font_height(font)
        for line in self._wrap_text(text, font, rect.width):
            if y + line_height > rect.bottom:
                break
            surface = font.render(line, True, color)
            self.screen.blit(surface, (rect.left, y))
            y += line_height + line_gap
        return y

    def _draw_continue_button(self, label: str, bottom: int | None = None) -> pygame.Rect:
        text = self.normal_font.render(label, True, self.colors.BLACK)
        text_width = self._surface_width(text)
        button_width = min(self.width - 80, max(190, text_width + 54))
        button_height = max(42, self._font_height(self.normal_font) + 18)
        y = (bottom - button_height) if bottom is not None else (self.height - button_height - 42)
        self.continue_rect = pygame.Rect(
            self.width // 2 - button_width // 2, y, button_width, button_height
        )
        pygame.draw.rect(self.screen, self.colors.GOLD, self.continue_rect)
        pygame.draw.rect(self.screen, self.colors.WHITE, self.continue_rect, 2)
        self.screen.blit(text, text.get_rect(center=self.continue_rect.center))
        return self.continue_rect

    def _event_accepts_continue(self, event) -> bool:
        if event.type == pygame.KEYDOWN and event.key in (pygame.K_RETURN, pygame.K_SPACE):
            return True
        if is_left_click(event):
            pos = mouse_position(event)
            return pos is not None and self.continue_rect.collidepoint(pos)
        return False

    @staticmethod
    def _handle_quit_event(event) -> None:
        if event.type == pygame.QUIT:
            pygame.quit()
            sys.exit()


class CharacterCreatedScreen(_PresentationScreenBase):
    """Visual character-created summary shown after the creation flow."""

    def __init__(
        self, presenter, player_char, *, portrait_manager: PortraitManager | None = None
    ) -> None:
        super().__init__(presenter)
        self.player_char = player_char
        self.portrait_manager = portrait_manager or PortraitManager()
        self.portrait = self._load_portrait()

    @staticmethod
    def _attr_name(value, default: str = "") -> str:
        return str(getattr(value, "name", value) or default)

    def _load_portrait(self):
        try:
            return self.portrait_manager.get_portrait(
                self._attr_name(getattr(self.player_char, "race", None), "Human"),
                self._attr_name(getattr(self.player_char, "sex", "Male"), "Male"),
                class_name=self._attr_name(getattr(self.player_char, "cls", None), ""),
                variant=int(getattr(self.player_char, "portrait_variant", 0) or 0),
            )
        except Exception:
            return None

    def _summary_rows(self) -> list[tuple[str, str]]:
        return [
            ("Name", self._attr_name(getattr(self.player_char, "name", None), "Hero")),
            ("Race", self._attr_name(getattr(self.player_char, "race", None), "Human")),
            ("Sex", self._attr_name(getattr(self.player_char, "sex", None), "Male")),
            ("Class", self._attr_name(getattr(self.player_char, "cls", None), "Adventurer")),
            ("HP", str(getattr(getattr(self.player_char, "health", None), "max", 0))),
            ("MP", str(getattr(getattr(self.player_char, "mana", None), "max", 0))),
        ]

    def _portrait_rect(self, panel: pygame.Rect) -> pygame.Rect:
        source_size = (225, 400)
        if self.portrait is not None:
            try:
                source_size = self.portrait.get_size()
            except Exception:
                pass
        max_width = min(280, panel.width - 56)
        max_height = max(140, panel.height - 86)
        scale = min(max_width / max(1, source_size[0]), max_height / max(1, source_size[1]))
        size = (max(1, int(source_size[0] * scale)), max(1, int(source_size[1] * scale)))
        rect = pygame.Rect(0, 0, *size)
        rect.center = panel.center
        return rect

    def draw(self) -> None:
        self._draw_background()
        title = self.title_font.render("Character Created", True, self.colors.GOLD)
        self.screen.blit(title, title.get_rect(centerx=self.width // 2, top=38))

        margin = max(28, self.width // 24)
        top = max(120, self.height // 6)
        gap = max(22, self.width // 48)
        panel_height = self.height - top - 118
        portrait_panel = pygame.Rect(
            margin, top, (self.width - margin * 2 - gap) // 2, panel_height
        )
        summary_panel = pygame.Rect(
            portrait_panel.right + gap, top, portrait_panel.width, panel_height
        )
        self._draw_panel(portrait_panel)
        self._draw_panel(summary_panel)

        portrait_rect = self._portrait_rect(portrait_panel)
        pygame.draw.rect(self.screen, (34, 32, 38), portrait_rect)
        if self.portrait is not None:
            try:
                fitted = pygame.transform.smoothscale(self.portrait, portrait_rect.size)
                self.screen.blit(fitted, portrait_rect)
            except Exception:
                pass
        pygame.draw.rect(self.screen, self.colors.GOLD, portrait_rect, 2)

        y = summary_panel.top + 42
        heading = self.large_font.render("Ready for Silvana", True, self.colors.WHITE)
        self.screen.blit(heading, (summary_panel.left + 36, y))
        y += self._font_height(self.large_font) + 28

        label_x = summary_panel.left + 42
        value_x = summary_panel.right - 42
        row_gap = max(8, self._font_height(self.normal_font) // 2)
        for label, value in self._summary_rows():
            label_surface = self.normal_font.render(label, True, self.colors.GRAY)
            value_surface = self.normal_font.render(value, True, self.colors.WHITE)
            self.screen.blit(label_surface, (label_x, y))
            self.screen.blit(value_surface, value_surface.get_rect(right=value_x, top=y))
            y += self._font_height(self.normal_font) + row_gap

        progression_note = (
            "You begin with 1 Progression Point. Spend it at any time in "
            "Character → Progression on a tree node or primary attribute. "
            "You gain another point at level 2 and every even level after."
        )
        for line in textwrap.wrap(progression_note, 48):
            note_surface = self.small_font.render(line, True, self.colors.GOLD)
            self.screen.blit(note_surface, (label_x, y))
            y += self._font_height(self.small_font) + 3

        self._draw_continue_button("Begin Adventure")

    def show(self, *, flush_events: bool = False, require_key_release: bool = False) -> bool:
        input_armed = prepare_guarded_input(
            flush_events=flush_events, require_key_release=require_key_release
        )
        while True:
            self.draw()
            pygame.display.flip()
            input_armed = release_guard_allows_input(require_key_release, input_armed)
            for event in get_events():
                self._handle_quit_event(event)
                input_armed = update_input_armed_from_event(event, require_key_release, input_armed)
                if input_armed and self._event_accepts_continue(event):
                    return True
            self.presenter.clock.tick(30)


class StoryCardSequence(_PresentationScreenBase):
    """Paged story-card presentation for short narrative sequences."""

    def __init__(self, presenter, pages: Iterable[str], *, title: str = "Story") -> None:
        super().__init__(presenter)
        self.pages = [str(page) for page in pages]
        self.title = title
        self.page_index = 0

    def draw(self) -> None:
        self._draw_background()
        title = self.title_font.render(self.title, True, self.colors.GOLD)
        self.screen.blit(title, title.get_rect(centerx=self.width // 2, top=44))

        card_width = min(760, self.width - 96)
        card_height = min(430, self.height - 210)
        card = pygame.Rect(self.width // 2 - card_width // 2, 142, card_width, card_height)
        self._draw_panel(card, fill=(18, 16, 22), border=self.colors.GOLD)

        page_count = max(1, len(self.pages))
        counter = self.small_font.render(
            f"{self.page_index + 1}/{page_count}", True, self.colors.GRAY
        )
        self.screen.blit(counter, counter.get_rect(right=card.right - 24, top=card.top + 20))

        body_rect = card.inflate(-72, -92)
        body_rect.top += 18
        self._draw_wrapped_text(
            self.pages[self.page_index] if self.pages else "",
            self.large_font,
            self.colors.WHITE,
            body_rect,
            line_gap=10,
        )

        label = "Continue" if self.page_index < page_count - 1 else "Enter Silvana"
        self._draw_continue_button(label, bottom=min(self.height - 36, card.bottom + 88))

    def show(self, *, flush_events: bool = False, require_key_release: bool = False) -> bool:
        if not self.pages:
            return True

        input_armed = prepare_guarded_input(
            flush_events=flush_events, require_key_release=require_key_release
        )
        while True:
            self.draw()
            pygame.display.flip()
            input_armed = release_guard_allows_input(require_key_release, input_armed)
            for event in get_events():
                self._handle_quit_event(event)
                input_armed = update_input_armed_from_event(event, require_key_release, input_armed)
                if event.type == pygame.KEYDOWN and input_armed and event.key == pygame.K_ESCAPE:
                    return False
                if input_armed and self._event_accepts_continue(event):
                    if self.page_index >= len(self.pages) - 1:
                        return True
                    self.page_index += 1
            self.presenter.clock.tick(30)
