"""Presentation-polish screens for character creation and story beats."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Iterable

import pygame

from src.paths import PYGAME_ASSETS_DIR
from src.ui_pygame.assets.portrait_manager import PortraitManager
from src.ui_pygame.screen_runtime import get_events

from .creation_theme import draw_creation_background
from .input_guards import (
    prepare_guarded_input,
    release_guard_allows_input,
    update_input_armed_from_event,
)
from .mouse_helpers import is_left_click, mouse_position
from .town_base import TownColors

INTRO_STORY_IMAGE_PATHS = tuple(
    PYGAME_ASSETS_DIR / "backgrounds" / filename
    for filename in (
        "intro_01_silvana.jpg",
        "intro_02_open_stair.jpg",
        "intro_03_impossible_passages.jpg",
        "intro_04_vigil.jpg",
        "intro_05_arrival.jpg",
        "intro_06_thirsty_dog.jpg",
    )
)

DUNGEON_ENTRY_IMAGE_PATHS = (PYGAME_ASSETS_DIR / "backgrounds" / "intro_06_descent.jpg",)


def fade_to_black(presenter, *, duration_ms: int = 650, hold_ms: int = 0) -> None:
    """Fade the current frame to black and optionally hold the black frame."""
    if duration_ms < 0 or hold_ms < 0:
        raise ValueError("fade and hold durations cannot be negative")
    screen = getattr(presenter, "screen", None)
    clock = getattr(presenter, "clock", None)
    if screen is None or clock is None or not hasattr(screen, "copy"):
        return

    source = screen.copy()
    frame_rate = 30
    frame_count = max(1, round(duration_ms * frame_rate / 1000))
    veil = pygame.Surface(source.get_size())
    veil.fill((0, 0, 0))
    for frame in range(frame_count + 1):
        screen.blit(source, (0, 0))
        veil.set_alpha(round(255 * frame / frame_count))
        screen.blit(veil, (0, 0))
        pygame.display.flip()
        clock.tick(frame_rate)
    screen.fill((0, 0, 0))
    pygame.display.flip()
    for _frame in range(round(hold_ms * frame_rate / 1000)):
        clock.tick(frame_rate)


class _PresentationScreenBase:
    """Shared drawing and guarded-input helpers for one-shot presentation screens."""

    def __init__(self, presenter, *, background_draw_func=None) -> None:
        self.presenter = presenter
        self.screen = presenter.screen
        self.width = presenter.width
        self.height = presenter.height
        self.colors = TownColors
        self.title_font = presenter.title_font
        self.large_font = presenter.large_font
        self.normal_font = presenter.normal_font
        self.small_font = presenter.small_font
        self.background_draw_func = background_draw_func
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
        draw_creation_background(
            self.screen,
            (self.width, self.height),
            self.background_draw_func,
            fallback_color=(9, 9, 14),
        )
        band_height = max(140, self.height // 4)
        band = pygame.Surface((self.width, band_height), pygame.SRCALPHA)
        band.fill((28, 22, 34, 130))
        self.screen.blit(band, (0, 0))
        pygame.draw.line(
            self.screen, (124, 102, 58), (0, band_height), (self.width, band_height), 2
        )

    def _draw_panel(self, rect: pygame.Rect, *, fill=(18, 18, 24), border=None) -> None:
        panel = pygame.Surface(rect.size, pygame.SRCALPHA)
        panel.fill((*fill, 158))
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
        self,
        presenter,
        player_char,
        *,
        portrait_manager: PortraitManager | None = None,
        background_draw_func=None,
    ) -> None:
        super().__init__(presenter, background_draw_func=background_draw_func)
        self.player_char = player_char
        self.portrait_manager = portrait_manager or PortraitManager()
        self.portrait = self._load_portrait()

    @staticmethod
    def _attr_name(value, default: str = "") -> str:
        return str(getattr(value, "name", value) or default)

    def _load_portrait(self):
        race = self._attr_name(getattr(self.player_char, "race", None), "Human")
        sex = self._attr_name(getattr(self.player_char, "sex", "Male"), "Male")
        variant = int(getattr(self.player_char, "portrait_variant", 0) or 0)
        try:
            portrait = self.portrait_manager.get_portrait(
                race,
                sex,
                class_name=self._attr_name(getattr(self.player_char, "cls", None), ""),
                variant=variant,
            )
        except (AttributeError, OSError, TypeError, ValueError, pygame.error):
            portrait = None
        if portrait is not None:
            return portrait
        try:
            return self.portrait_manager.base_portrait(race, sex, variant=variant)
        except (AttributeError, OSError, TypeError, ValueError, pygame.error):
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

    def _check_mod(self, mod: str) -> int:
        """Return a combat modifier while tolerating incomplete preview characters."""
        check_mod = getattr(self.player_char, "check_mod", None)
        if not callable(check_mod):
            return 0
        try:
            return int(check_mod(mod))
        except (AttributeError, KeyError, TypeError, ValueError):
            return 0

    def _combat_rows(self) -> list[tuple[str, str]]:
        """Build the compact combat summary used on the creation result screen."""
        equipment = getattr(self.player_char, "equipment", {}) or {}
        offhand = equipment.get("OffHand") if isinstance(equipment, dict) else None
        attack = str(self._check_mod("weapon"))
        if getattr(offhand, "typ", None) == "Weapon":
            attack = f"{attack}/{self._check_mod('offhand')}"
        try:
            critical = float(self.player_char.critical_chance("Weapon")) * 100
        except (AttributeError, KeyError, TypeError, ValueError):
            critical = 0.0
        return [
            ("Attack", attack),
            ("Defense", str(self._check_mod("armor"))),
            ("Magic Attack", str(self._check_mod("magic"))),
            ("Magic Defense", str(self._check_mod("magic def"))),
            ("Critical", f"{critical:.1f}%"),
            ("Block", f"{self._check_mod('shield')}%"),
            ("Speed", str(self._check_mod("speed"))),
        ]

    def _portrait_rect(self, panel: pygame.Rect) -> pygame.Rect:
        source_size = (225, 400)
        if self.portrait is not None:
            try:
                source_size = self.portrait.get_size()
            except (AttributeError, TypeError, ValueError, pygame.error):
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
            except (AttributeError, TypeError, ValueError, pygame.error):
                pass
        pygame.draw.rect(self.screen, self.colors.GOLD, portrait_rect, 2)

        y = summary_panel.top + 42

        label_x = summary_panel.left + 42
        value_x = summary_panel.right - 42
        row_gap = max(8, self._font_height(self.normal_font) // 2)
        for label, value in self._summary_rows():
            label_surface = self.normal_font.render(label, True, self.colors.GRAY)
            value_surface = self.normal_font.render(value, True, self.colors.WHITE)
            self.screen.blit(label_surface, (label_x, y))
            self.screen.blit(value_surface, value_surface.get_rect(right=value_x, top=y))
            y += self._font_height(self.normal_font) + row_gap

        y += 8
        combat_heading = self.normal_font.render("Combat Stats", True, self.colors.GOLD)
        self.screen.blit(combat_heading, (label_x, y))
        y += self._font_height(self.normal_font) + 10
        combat_gap = max(4, self._font_height(self.small_font) // 3)
        for label, value in self._combat_rows():
            label_surface = self.small_font.render(label, True, self.colors.GRAY)
            value_surface = self.small_font.render(value, True, self.colors.WHITE)
            self.screen.blit(label_surface, (label_x, y))
            self.screen.blit(value_surface, value_surface.get_rect(right=value_x, top=y))
            y += self._font_height(self.small_font) + combat_gap

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
    """Slow-printed illustrated cards with protected two-step advancement."""

    def __init__(
        self,
        presenter,
        pages: Iterable[str],
        *,
        title: str = "Story",
        image_paths: Iterable[Path] | None = None,
    ) -> None:
        super().__init__(presenter)
        self.pages = [str(page) for page in pages]
        self.title = title
        self.page_index = 0
        self.story_font = getattr(presenter, "story_font", self.large_font)
        self.story_title_font = getattr(presenter, "story_title_font", self.title_font)
        self.images = self._load_images(tuple(image_paths or ()))
        self._scaled_images: dict[
            tuple[int, tuple[int, int]], tuple[pygame.Surface, tuple[int, int]]
        ] = {}
        self._page_started_ms = 0
        self._page_complete = False

    @staticmethod
    def _load_images(paths: tuple[Path, ...]) -> list[pygame.Surface | None]:
        images: list[pygame.Surface | None] = []
        for path in paths:
            try:
                images.append(pygame.image.load(str(path)))
            except (FileNotFoundError, OSError, pygame.error):
                images.append(None)
        return images

    def _scaled_image(self, index: int) -> tuple[pygame.Surface, tuple[int, int]] | None:
        if index >= len(self.images) or self.images[index] is None:
            return None
        cache_key = (index, (self.width, self.height))
        if cache_key in self._scaled_images:
            return self._scaled_images[cache_key]
        image = self.images[index]
        if image is None:
            return None
        source_width, source_height = image.get_size()
        scale = max(self.width / source_width, self.height / source_height)
        size = (round(source_width * scale), round(source_height * scale))
        scaled = pygame.transform.smoothscale(image, size)
        offset = ((self.width - size[0]) // 2, (self.height - size[1]) // 2)
        self._scaled_images[cache_key] = (scaled, offset)
        return scaled, offset

    def _draw_card_background(self) -> None:
        image = self._scaled_image(self.page_index)
        if image is None:
            self.screen.fill((9, 9, 14))
        else:
            self.screen.blit(*image)
        veil = pygame.Surface((self.width, self.height), pygame.SRCALPHA)
        veil.fill((4, 5, 10, 76))
        self.screen.blit(veil, (0, 0))

    def _visible_character_count(self, now_ms: int) -> int:
        if not self.pages:
            return 0
        page_length = len(self._wrapped_story_text(self.pages[self.page_index]))
        if self._page_complete:
            return page_length
        characters_per_second = max(1, int(getattr(self.presenter, "story_dialogue_cps", 35)))
        elapsed_ms = max(0, now_ms - self._page_started_ms)
        return min(page_length, elapsed_ms * characters_per_second // 1000)

    def _reveal_complete(self, now_ms: int) -> bool:
        if not self.pages:
            return True
        return self._visible_character_count(now_ms) >= len(
            self._wrapped_story_text(self.pages[self.page_index])
        )

    def _story_body_rect(self) -> pygame.Rect:
        """Return the prose area shared by wrapping, reveal timing, and drawing."""
        return pygame.Rect(
            max(48, self.width // 12),
            max(100, int(self.height * 0.48)),
            self.width - max(96, self.width // 6),
            int(self.height * 0.43),
        )

    def _wrapped_story_text(self, text: str) -> str:
        """Wrap a complete passage before revealing it to keep words on one line."""
        return "\n".join(self._wrap_text(text, self.story_font, self._story_body_rect().width))

    def draw(
        self,
        *,
        now_ms: int | None = None,
        hide_text: bool = False,
        force_complete: bool = False,
    ) -> None:
        now_ms = pygame.time.get_ticks() if now_ms is None else now_ms
        self._draw_card_background()
        body_rect = self._story_body_rect()
        page = self.pages[self.page_index] if self.pages else ""
        wrapped_page = self._wrapped_story_text(page)
        if hide_text:
            visible_count = 0
        elif force_complete:
            visible_count = len(wrapped_page)
        else:
            visible_count = self._visible_character_count(now_ms)
        self._draw_story_text(wrapped_page[:visible_count], body_rect)

    def _draw_story_text(self, text: str, rect: pygame.Rect) -> None:
        """Draw card prose directly over the art with a soft readability shadow."""
        y = rect.top
        line_height = self._font_height(self.story_font)
        for line in text.splitlines() or [""]:
            if y + line_height > rect.bottom:
                break
            shadow = self.story_font.render(line, True, (4, 4, 7))
            surface = self.story_font.render(line, True, (244, 235, 211))
            for offset in ((-2, 0), (2, 0), (0, -2), (0, 2), (2, 2)):
                self.screen.blit(shadow, (rect.left + offset[0], y + offset[1]))
            self.screen.blit(surface, (rect.left, y))
            y += line_height + 12

    def _fade_in(self, duration_ms: int) -> None:
        if duration_ms <= 0:
            return
        frame_rate = 30
        frame_count = max(1, round(duration_ms * frame_rate / 1000))
        veil = pygame.Surface((self.width, self.height))
        veil.fill((0, 0, 0))
        for frame in range(frame_count + 1):
            self.draw(now_ms=0, hide_text=True)
            veil.set_alpha(round(255 * (1 - frame / frame_count)))
            self.screen.blit(veil, (0, 0))
            pygame.display.flip()
            self.presenter.clock.tick(frame_rate)

    def _fade_out(self, duration_ms: int) -> None:
        """Fade the fully revealed current card to black."""
        if duration_ms <= 0:
            return
        frame_rate = 30
        frame_count = max(1, round(duration_ms * frame_rate / 1000))
        veil = pygame.Surface((self.width, self.height))
        veil.fill((0, 0, 0))
        for frame in range(frame_count + 1):
            self.draw(force_complete=True)
            veil.set_alpha(round(255 * frame / frame_count))
            self.screen.blit(veil, (0, 0))
            pygame.display.flip()
            self.presenter.clock.tick(frame_rate)

    @staticmethod
    def _event_advances(event) -> bool:
        return (
            event.type == pygame.KEYDOWN and event.key in (pygame.K_RETURN, pygame.K_SPACE)
        ) or is_left_click(event)

    def show(
        self,
        *,
        flush_events: bool = False,
        require_key_release: bool = False,
        fade_in_ms: int = 0,
        fade_out_ms: int | None = None,
    ) -> bool:
        if not self.pages:
            return True

        input_armed = prepare_guarded_input(
            flush_events=flush_events, require_key_release=require_key_release
        )
        card_fade_out_ms = fade_in_ms if fade_out_ms is None else fade_out_ms
        self._fade_in(fade_in_ms)
        if fade_in_ms > 0:
            input_armed = prepare_guarded_input(
                flush_events=True, require_key_release=require_key_release
            )
        self._page_started_ms = pygame.time.get_ticks()
        while True:
            now_ms = pygame.time.get_ticks()
            self.draw(now_ms=now_ms)
            pygame.display.flip()
            input_armed = release_guard_allows_input(require_key_release, input_armed)
            for event in get_events():
                self._handle_quit_event(event)
                input_armed = update_input_armed_from_event(event, require_key_release, input_armed)
                if event.type == pygame.KEYDOWN and input_armed and event.key == pygame.K_ESCAPE:
                    return False
                if input_armed and self._event_advances(event):
                    if not self._reveal_complete(now_ms):
                        self._page_complete = True
                        break
                    self._fade_out(card_fade_out_ms)
                    if self.page_index >= len(self.pages) - 1:
                        return True
                    self.page_index += 1
                    self._page_complete = False
                    self._fade_in(fade_in_ms)
                    if fade_in_ms > 0 or card_fade_out_ms > 0:
                        input_armed = prepare_guarded_input(
                            flush_events=True, require_key_release=require_key_release
                        )
                    self._page_started_ms = pygame.time.get_ticks()
                    break
            self.presenter.clock.tick(30)
