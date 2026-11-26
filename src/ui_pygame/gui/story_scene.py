"""Town-style multi-speaker presentation for authored storyline scenes."""

from __future__ import annotations

from dataclasses import dataclass

import pygame

from src.ui_pygame.assets.npc_art_manager import get_npc_art_manager
from src.ui_pygame.assets.player_dialogue_art_manager import PlayerDialogueArtManager
from src.ui_pygame.screen_runtime import get_events

from .input_guards import (
    prepare_guarded_input,
    release_guard_allows_input,
    update_input_armed_from_event,
)
from .mouse_helpers import hit_index, is_left_click, mouse_position
from .town_base import TownScreenBase, wrap_text_to_pixel_width

PLAYER_PORTRAIT_KEY = "__player_portrait__"
MAX_VISIBLE_PORTRAITS = 3


@dataclass(frozen=True)
class StoryBeat:
    """One displayed line or narration block in a storyline scene."""

    speaker: str
    text: str
    portrait_name: str | None = None

    @property
    def portrait(self) -> str | None:
        """Return the NPC-art lookup name for this beat."""
        if self.portrait_name is not None:
            return self.portrait_name or None
        if self.speaker == "Narrator":
            return None
        return self.speaker


@dataclass(frozen=True)
class StagedPortrait:
    """One persistent visual-novel portrait assignment."""

    speaker: str
    portrait_name: str
    slot: str


class StoryChoicePopup:
    """Responsive modal menu drawn over a storyline scene."""

    def __init__(
        self,
        presenter,
        prompt: str,
        options: list[str],
        *,
        background_draw_func=None,
        allow_cancel: bool = True,
    ):
        self.presenter = presenter
        self.screen = presenter.screen
        self.width = presenter.width
        self.height = presenter.height
        self.prompt = prompt
        self.options = list(options)
        self.background_draw_func = background_draw_func
        self.allow_cancel = allow_cancel
        self.current_selection = 0
        self.normal_font = presenter.normal_font
        self.small_font = presenter.small_font
        self.title_font = presenter.large_font

        margin = max(24, int(self.width * 0.08))
        popup_width = min(self.width - (margin * 2), max(560, int(self.width * 0.68)))
        text_width = popup_width - 64
        self.prompt_lines = wrap_text_to_pixel_width(prompt, self.title_font, text_width)
        self.option_lines = [
            wrap_text_to_pixel_width(option, self.normal_font, text_width - 36)
            for option in self.options
        ]
        self.row_gap = 8
        self.row_padding = 10
        self.option_heights = [
            max(38, (len(lines) * self.normal_font.get_height()) + (self.row_padding * 2))
            for lines in self.option_lines
        ]
        prompt_height = len(self.prompt_lines) * (self.title_font.get_height() + 4)
        popup_height = (
            48
            + prompt_height
            + 20
            + sum(self.option_heights)
            + (self.row_gap * max(0, len(self.options) - 1))
            + 54
        )
        popup_height = min(self.height - (margin * 2), popup_height)
        self.popup_rect = pygame.Rect(
            (self.width - popup_width) // 2,
            (self.height - popup_height) // 2,
            popup_width,
            popup_height,
        )

    def option_rects(self) -> list[pygame.Rect]:
        """Return variable-height hitboxes for each wrapped response."""
        y = (
            self.popup_rect.top
            + 44
            + (len(self.prompt_lines) * (self.title_font.get_height() + 4))
            + 20
        )
        rects = []
        for height in self.option_heights:
            rects.append(
                pygame.Rect(self.popup_rect.left + 24, y, self.popup_rect.width - 48, height)
            )
            y += height + self.row_gap
        return rects

    def draw(self) -> None:
        """Draw the modal prompt and its wrapped responses over the scene."""
        if self.background_draw_func is not None:
            self.background_draw_func()
        overlay = pygame.Surface((self.width, self.height), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 165))
        self.screen.blit(overlay, (0, 0))
        pygame.draw.rect(self.screen, (18, 18, 24), self.popup_rect)
        pygame.draw.rect(self.screen, (200, 200, 200), self.popup_rect, 3)

        y = self.popup_rect.top + 24
        for line in self.prompt_lines:
            surface = self.title_font.render(line, True, (218, 165, 32))
            self.screen.blit(surface, surface.get_rect(centerx=self.popup_rect.centerx, top=y))
            y += self.title_font.get_height() + 4

        for index, (rect, lines) in enumerate(zip(self.option_rects(), self.option_lines)):
            selected = index == self.current_selection
            if selected:
                pygame.draw.rect(self.screen, (60, 60, 80), rect)
            pygame.draw.rect(self.screen, (218, 165, 32) if selected else (96, 96, 104), rect, 2)
            color = (218, 165, 32) if selected else (255, 255, 255)
            line_y = rect.top + self.row_padding
            for line in lines:
                surface = self.normal_font.render(line, True, color)
                self.screen.blit(surface, (rect.left + 18, line_y))
                line_y += self.normal_font.get_height()

        instruction_text = "UP/DOWN: Choose   ENTER: Confirm"
        if self.allow_cancel:
            instruction_text += "   ESC: Return"
        instruction = self.small_font.render(instruction_text, True, (160, 160, 168))
        self.screen.blit(
            instruction,
            instruction.get_rect(
                centerx=self.popup_rect.centerx, bottom=self.popup_rect.bottom - 12
            ),
        )
        pygame.display.flip()

    def show(self, *, flush_events: bool = True, require_key_release: bool = True) -> int | None:
        """Run guarded popup navigation and return the selected response index."""
        if not self.options:
            return None
        input_armed = prepare_guarded_input(
            flush_events=flush_events, require_key_release=require_key_release
        )
        while True:
            self.draw()
            input_armed = release_guard_allows_input(require_key_release, input_armed)
            for event in get_events():
                if event.type == pygame.QUIT:
                    pygame.quit()
                    raise SystemExit
                input_armed = update_input_armed_from_event(event, require_key_release, input_armed)
                hovered = hit_index(self.option_rects(), mouse_position(event))
                if hovered is not None and event.type == pygame.MOUSEMOTION:
                    self.current_selection = hovered
                elif hovered is not None and is_left_click(event) and input_armed:
                    self.current_selection = hovered
                    return hovered
                elif event.type == pygame.KEYDOWN and input_armed:
                    if event.key in (pygame.K_UP, pygame.K_w):
                        self.current_selection = (self.current_selection - 1) % len(self.options)
                    elif event.key in (pygame.K_DOWN, pygame.K_s):
                        self.current_selection = (self.current_selection + 1) % len(self.options)
                    elif event.key in (pygame.K_RETURN, pygame.K_SPACE):
                        return self.current_selection
                    elif event.key == pygame.K_ESCAPE and self.allow_cancel:
                        return None
            self.presenter.clock.tick(30)


class StorySceneScreen(TownScreenBase):
    """Display sequential dialogue with a visible cast and active speaker."""

    def __init__(
        self,
        presenter,
        title: str,
        *,
        participants: list[str] | tuple[str, ...] = (),
        participant_anchors: dict[str, str] | None = None,
        background_draw_func=None,
        background_image: str = "town.png",
        player_char=None,
        player_dialogue_art_manager: PlayerDialogueArtManager | None = None,
    ):
        self.background_image = background_image
        self.background_fallback_image = "town.png" if background_image != "town.png" else None
        super().__init__(presenter)
        self.title = title
        self.participants = tuple(dict.fromkeys(participants))
        self.participant_anchors = dict(participant_anchors or {})
        self.background_draw_func = background_draw_func
        self.player_char = player_char or getattr(presenter, "player", None)
        self.player_dialogue_art_manager = (
            player_dialogue_art_manager or PlayerDialogueArtManager()
        )
        self.current_beat = StoryBeat("Narrator", "")
        self.transcript: list[StoryBeat] = []
        self._staged_portraits: dict[str, StagedPortrait] = {}
        self._history_open = False
        self._history_scroll = 0
        self._seed_portrait_stage()

    def _player_portrait_surface(self):
        """Return full-body art matching the player's character-creation appearance."""
        if self.player_char is None:
            return None
        race = getattr(self.player_char, "race", "Human")
        sex = getattr(self.player_char, "sex", "Male")
        variant = getattr(self.player_char, "portrait_variant", 0)
        try:
            return self.player_dialogue_art_manager.get_portrait(
                race,
                sex,
                variant=variant,
            )
        except (AttributeError, OSError, TypeError, ValueError, pygame.error):
            return None

    def _draw_scene_background(self) -> None:
        if self.background_draw_func is not None:
            self.background_draw_func()
        else:
            self.draw_background()

    def _portrait_surface(self, portrait_name: str):
        """Resolve either an authored NPC portrait or the selected player portrait."""
        if portrait_name == PLAYER_PORTRAIT_KEY:
            return self._player_portrait_surface()
        return self.npc_portrait_surface(npc_name=portrait_name)

    def _next_stage_slot(self, speaker: str) -> str:
        """Return an unused fixed slot, preserving any declared association."""
        if "left" not in self._staged_portraits:
            return "left"
        if "right" not in self._staged_portraits:
            return "right"

        anchor = self.participant_anchors.get(speaker)
        anchor_slot = next(
            (
                staged.slot
                for staged in self._staged_portraits.values()
                if staged.speaker == anchor
            ),
            "left",
        )
        return "right_support" if anchor_slot.startswith("right") else "left_support"

    def _seed_portrait_stage(self) -> None:
        """Place up to three declared participants before beat-driven rotation."""
        for participant in self.participants:
            if len(self._staged_portraits) >= MAX_VISIBLE_PORTRAITS:
                break
            if self._portrait_surface(participant) is None:
                continue
            slot = self._next_stage_slot(participant)
            self._staged_portraits[slot] = StagedPortrait(participant, participant, slot)

    def _stage_for_beat(
        self,
        beat: StoryBeat,
        upcoming_beats: list[StoryBeat] | tuple[StoryBeat, ...] = (),
    ) -> None:
        """Keep the speaker visible while changing no more than one fixed slot."""
        portrait_name = beat.portrait
        if portrait_name is None:
            return
        if any(staged.speaker == beat.speaker for staged in self._staged_portraits.values()):
            return
        if self._portrait_surface(portrait_name) is None:
            return

        if len(self._staged_portraits) < MAX_VISIBLE_PORTRAITS:
            slot = self._next_stage_slot(beat.speaker)
        else:
            next_appearance: dict[str, int] = {}
            for staged in self._staged_portraits.values():
                next_appearance[staged.speaker] = next(
                    (
                        index
                        for index, future in enumerate(upcoming_beats)
                        if future.speaker == staged.speaker and future.portrait is not None
                    ),
                    len(upcoming_beats) + 1,
                )
            victim = max(
                self._staged_portraits.values(),
                key=lambda staged: (
                    next_appearance[staged.speaker],
                    "support" in staged.slot,
                ),
            )
            slot = victim.slot
            del self._staged_portraits[slot]
        self._staged_portraits[slot] = StagedPortrait(beat.speaker, portrait_name, slot)

    def _portrait_should_mirror(self, staged: StagedPortrait) -> bool:
        """Return whether staged art should turn inward for its current slot."""
        stage_side = "right" if staged.slot.startswith("right") else "left"
        if staged.portrait_name != PLAYER_PORTRAIT_KEY:
            return get_npc_art_manager().should_mirror(
                staged.portrait_name,
                stage_side=stage_side,
            )
        if self.player_char is None:
            return False
        race = getattr(self.player_char, "race", "Human")
        sex = getattr(self.player_char, "sex", "Male")
        variant = getattr(self.player_char, "portrait_variant", 0)
        try:
            return self.player_dialogue_art_manager.should_mirror(
                race,
                sex,
                variant=variant,
                stage_side=stage_side,
            )
        except (AttributeError, TypeError, ValueError):
            return False

    def _layout(self) -> tuple[pygame.Rect, pygame.Rect, dict[str, pygame.Rect]]:
        """Return compact title, dialogue, and fixed portrait geometry."""
        margin = max(12, int(min(self.width, self.height) * 0.024))
        title_height = self.normal_font.get_height() + max(12, margin)
        title_width = min(
            self.width - (margin * 2),
            max(240, self.normal_font.size(self.title)[0] + (margin * 2)),
        )
        title_rect = pygame.Rect(margin, margin, title_width, title_height)

        minimum_dialogue_height = (self.normal_font.get_height() * 6) + 78
        dialogue_height = min(
            int(self.height * 0.36),
            max(int(self.height * 0.25), minimum_dialogue_height),
        )
        dialogue_rect = pygame.Rect(
            margin,
            self.height - dialogue_height - margin,
            self.width - (margin * 2),
            dialogue_height,
        )

        portrait_top = title_rect.bottom + max(4, margin // 2)
        portrait_bottom = dialogue_rect.top + max(10, dialogue_rect.height // 12)
        portrait_height = max(1, portrait_bottom - portrait_top)
        main_width = min(int(self.width * 0.34), int(portrait_height * (2 / 3)))
        main_width = max(1, main_width)
        left = pygame.Rect(margin, portrait_top, main_width, portrait_height)
        right = pygame.Rect(
            self.width - margin - main_width,
            portrait_top,
            main_width,
            portrait_height,
        )
        support_width = max(1, int(main_width * 0.72))
        support_height = max(1, int(portrait_height * 0.78))
        support_top = portrait_bottom - support_height
        support_inset = max(8, int(main_width * 0.1))
        left_support = pygame.Rect(
            left.right - support_inset,
            support_top,
            support_width,
            support_height,
        )
        right_support = pygame.Rect(
            right.left - support_width + support_inset,
            support_top,
            support_width,
            support_height,
        )
        return title_rect, dialogue_rect, {
            "left": left,
            "right": right,
            "left_support": left_support,
            "right_support": right_support,
        }

    def _wrapped_beat_text(self, beat: StoryBeat, text_width: int | None = None) -> str:
        """Wrap a full beat before reveal so partially typed words cannot move."""
        if text_width is None:
            _title_rect, dialogue_rect, _portrait_rects = self._layout()
            text_width = dialogue_rect.width - max(48, int(dialogue_rect.width * 0.06))
        return "\n".join(wrap_text_to_pixel_width(beat.text, self.normal_font, text_width))

    def _draw_staged_portrait(
        self,
        staged: StagedPortrait,
        rect: pygame.Rect,
        *,
        active_speaker: str | None,
    ) -> None:
        """Draw one full-figure portrait with speaker/listener emphasis."""
        portrait = self._portrait_surface(staged.portrait_name)
        if portrait is None:
            return
        source_width, source_height = portrait.get_size()
        scale = min(rect.width / max(1, source_width), rect.height / max(1, source_height))
        size = (
            max(1, int(source_width * scale)),
            max(1, int(source_height * scale)),
        )
        fitted = pygame.transform.smoothscale(portrait, size)
        if self._portrait_should_mirror(staged):
            fitted = pygame.transform.flip(fitted, True, False)
        destination = fitted.get_rect(midbottom=rect.midbottom)
        active = staged.speaker == active_speaker
        if active:
            glow = pygame.Surface((destination.width + 20, 8), pygame.SRCALPHA)
            glow.fill((218, 165, 32, 82))
            self.screen.blit(
                glow,
                glow.get_rect(centerx=destination.centerx, bottom=destination.bottom - 2),
            )
        else:
            fitted = fitted.copy()
            # Preserve the cutout's opacity while pushing listeners into the
            # background.  Lowering surface alpha made the scenery visible
            # through otherwise solid clothing and skin.
            fitted.fill((128, 128, 128, 255), special_flags=pygame.BLEND_RGBA_MULT)
        self.screen.blit(fitted, destination)

    def _history_render_lines(
        self,
        beats: list[StoryBeat],
        text_width: int,
    ) -> list[tuple[str, tuple[int, int, int]]]:
        """Flatten authored beats into color-coded review lines."""
        lines: list[tuple[str, tuple[int, int, int]]] = []
        for beat in beats:
            narration = beat.speaker in ("", "Narrator")
            if not narration:
                lines.append((beat.speaker, self.colors.GOLD))
            wrapped = wrap_text_to_pixel_width(beat.text, self.small_font, text_width)
            lines.extend((line, self.colors.LIGHT_GRAY) for line in wrapped)
            lines.append(("", self.colors.LIGHT_GRAY))
        return lines

    def _draw_history(self, beats: list[StoryBeat]) -> None:
        """Draw a scrollable dialogue-history overlay without changing staging."""
        margin = max(20, int(min(self.width, self.height) * 0.06))
        panel = pygame.Rect(margin, margin, self.width - (margin * 2), self.height - (margin * 2))
        veil = pygame.Surface((self.width, self.height), pygame.SRCALPHA)
        veil.fill((0, 0, 0, 150))
        self.screen.blit(veil, (0, 0))
        self.draw_semi_transparent_panel(panel, alpha=238)
        pygame.draw.line(
            self.screen,
            (151, 113, 31),
            (panel.left, panel.top),
            (panel.right, panel.top),
            2,
        )
        heading = self.normal_font.render("Dialogue History", True, self.colors.GOLD)
        self.screen.blit(heading, (panel.left + 24, panel.top + 20))
        hint = self.small_font.render(
            "UP / DOWN: Scroll   H / ESC: Return",
            True,
            self.colors.LIGHT_GRAY,
        )
        self.screen.blit(hint, hint.get_rect(right=panel.right - 24, top=panel.top + 24))

        text_top = panel.top + self.normal_font.get_height() + 42
        text_bottom = panel.bottom - 24
        line_height = self.small_font.get_height() + 3
        max_lines = max(1, (text_bottom - text_top) // line_height)
        lines = self._history_render_lines(beats, panel.width - 48)
        end = max(0, len(lines) - self._history_scroll)
        start = max(0, end - max_lines)
        y = text_top
        for text, color in lines[start:end]:
            if text:
                self.screen.blit(self.small_font.render(text, True, color), (panel.left + 24, y))
            y += line_height

    def draw_frame(
        self,
        beat: StoryBeat | None = None,
        *,
        transcript: list[StoryBeat] | tuple[StoryBeat, ...] | None = None,
        visible_characters: int | None = None,
        do_flip: bool = True,
    ) -> None:
        """Draw one complete storyline frame."""
        if beat is not None:
            self.current_beat = beat
        beat = self.current_beat
        displayed_beats = list(transcript) if transcript is not None else list(self.transcript)
        if not displayed_beats or displayed_beats[-1] != beat:
            displayed_beats.append(beat)
        self._stage_for_beat(beat)
        self._draw_scene_background()
        title_rect, dialogue_rect, portrait_rects = self._layout()

        self.draw_semi_transparent_panel(title_rect, alpha=165)
        pygame.draw.line(
            self.screen,
            (151, 113, 31),
            title_rect.bottomleft,
            title_rect.bottomright,
            1,
        )
        title = self.normal_font.render(self.title, True, self.colors.LIGHT_GRAY)
        self.screen.blit(title, title.get_rect(center=title_rect.center))

        narration = beat.speaker in ("", "Narrator")
        active_speaker = None if narration else beat.speaker
        staged_portraits = sorted(
            self._staged_portraits.values(),
            key=lambda staged: (
                staged.speaker == active_speaker,
                "support" not in staged.slot,
            ),
        )
        for staged in staged_portraits:
            self._draw_staged_portrait(
                staged,
                portrait_rects[staged.slot],
                active_speaker=active_speaker,
            )

        self.draw_semi_transparent_panel(dialogue_rect, alpha=226)
        pygame.draw.line(
            self.screen,
            (174, 130, 32),
            dialogue_rect.topleft,
            dialogue_rect.topright,
            2,
        )
        padding = max(24, int(dialogue_rect.width * 0.03))
        text_width = dialogue_rect.width - (padding * 2)
        wrapped = self._wrapped_beat_text(beat, text_width)
        if visible_characters is not None:
            wrapped = wrapped[:visible_characters]
        lines = wrapped.splitlines() or [""]
        text_y = dialogue_rect.top + max(20, dialogue_rect.height // 10)
        if not narration:
            name = self.normal_font.render(beat.speaker, True, self.colors.GOLD)
            self.screen.blit(name, (dialogue_rect.left + padding, text_y))
            text_y += self.normal_font.get_height() + 8
        else:
            text_y += max(4, self.normal_font.get_height() // 4)
        instruction_top = dialogue_rect.bottom - self.small_font.get_height() - 14
        for line in lines:
            if text_y + self.normal_font.get_height() > instruction_top - 8:
                break
            surface = self.normal_font.render(line, True, self.colors.WHITE)
            self.screen.blit(surface, (dialogue_rect.left + padding, text_y))
            text_y += self.normal_font.get_height() + 2

        reveal_complete = visible_characters is None or visible_characters >= len(
            self._wrapped_beat_text(beat, dialogue_rect.width - 48)
        )
        instruction = self.small_font.render(
            (
                "ENTER / SPACE / CLICK: Continue   H: Review"
                if reveal_complete
                else "ENTER / SPACE / CLICK: Complete dialogue   H: Review"
            ),
            True,
            self.colors.LIGHT_GRAY,
        )
        self.screen.blit(
            instruction,
            instruction.get_rect(right=dialogue_rect.right - 18, bottom=dialogue_rect.bottom - 14),
        )
        if self._history_open:
            self._draw_history(displayed_beats)
        if do_flip:
            pygame.display.flip()

    def _fade_in_dialogue(self, beat: StoryBeat, duration_ms: int, hold_ms: int = 0) -> None:
        """Fade from black to the first empty dialogue frame."""
        if duration_ms <= 0:
            return
        frame_rate = 30
        frame_count = max(1, round(duration_ms * frame_rate / 1000))
        veil = pygame.Surface((self.width, self.height))
        veil.fill((0, 0, 0))
        hold_frames = max(0, round(hold_ms * frame_rate / 1000))
        for _frame in range(hold_frames):
            self.screen.blit(veil, (0, 0))
            pygame.display.flip()
            self.presenter.clock.tick(frame_rate)
        for frame in range(frame_count + 1):
            self.draw_frame(
                beat,
                transcript=self.transcript,
                visible_characters=0,
                do_flip=False,
            )
            veil.set_alpha(round(255 * (1 - frame / frame_count)))
            self.screen.blit(veil, (0, 0))
            pygame.display.flip()
            self.presenter.clock.tick(frame_rate)

    def show_dialogue(
        self,
        beats: list[StoryBeat] | tuple[StoryBeat, ...],
        *,
        fade_in_ms: int = 0,
        fade_hold_ms: int = 0,
    ) -> None:
        """Slow-print one beat at a time with guarded advance and review controls."""
        input_armed = prepare_guarded_input(flush_events=True, require_key_release=True)
        for index, beat in enumerate(beats):
            self.current_beat = beat
            self.transcript.append(beat)
            self._stage_for_beat(beat, beats[index + 1 :])
            if index == 0 and fade_in_ms > 0:
                if fade_hold_ms > 0:
                    self._fade_in_dialogue(beat, fade_in_ms, fade_hold_ms)
                else:
                    self._fade_in_dialogue(beat, fade_in_ms)
                input_armed = prepare_guarded_input(
                    flush_events=True, require_key_release=True
                )
            started_ms = pygame.time.get_ticks()
            force_complete = getattr(self.presenter, "debug_mode", False)
            display_length = len(self._wrapped_beat_text(beat))
            while True:
                characters_per_second = max(
                    0, int(getattr(self.presenter, "story_dialogue_cps", 35))
                )
                if force_complete or characters_per_second == 0:
                    visible_characters = display_length
                else:
                    elapsed_ms = max(0, pygame.time.get_ticks() - started_ms)
                    visible_characters = min(
                        display_length, int(elapsed_ms * characters_per_second / 1000)
                    )
                reveal_complete = visible_characters >= display_length
                self.draw_frame(
                    beat,
                    transcript=self.transcript,
                    visible_characters=visible_characters,
                )
                input_armed = release_guard_allows_input(True, input_armed)
                advance = False
                for event in get_events():
                    if event.type == pygame.QUIT:
                        pygame.quit()
                        raise SystemExit
                    input_armed = update_input_armed_from_event(event, True, input_armed)
                    if not input_armed:
                        continue
                    if self._history_open:
                        if event.type == pygame.KEYDOWN:
                            if event.key in (pygame.K_h, pygame.K_ESCAPE, pygame.K_TAB):
                                self._history_open = False
                                self._history_scroll = 0
                            elif event.key in (pygame.K_UP, pygame.K_PAGEUP):
                                self._history_scroll = min(
                                    len(self._history_render_lines(self.transcript, self.width)),
                                    self._history_scroll + 3,
                                )
                            elif event.key in (pygame.K_DOWN, pygame.K_PAGEDOWN):
                                self._history_scroll = max(0, self._history_scroll - 3)
                        elif is_left_click(event):
                            self._history_open = False
                            self._history_scroll = 0
                        continue
                    if event.type == pygame.KEYDOWN and event.key in (
                        pygame.K_h,
                        pygame.K_TAB,
                    ):
                        self._history_open = True
                        self._history_scroll = 0
                        continue
                    activate = (
                        event.type == pygame.KEYDOWN
                        and event.key in (pygame.K_RETURN, pygame.K_SPACE)
                    ) or is_left_click(event)
                    if not activate:
                        continue
                    if reveal_complete:
                        advance = True
                    else:
                        force_complete = True
                    # Consume at most one activation per frame so a buffered
                    # double-click cannot both finish and advance a line.
                    break
                if advance:
                    break
                self.presenter.clock.tick(30)

    def choose(
        self,
        prompt: str,
        options: list[str],
        *,
        speaker: str = "You",
        portrait_name: str | None = None,
        record_selection: bool = True,
        allow_cancel: bool = True,
    ) -> int | None:
        """Draw the story context and open a guarded modal response menu."""
        choice_beat = StoryBeat(speaker, prompt, portrait_name)
        choice_transcript = [*self.transcript, choice_beat]
        self.draw_frame(choice_beat, transcript=choice_transcript, do_flip=True)
        choice = StoryChoicePopup(
            self.presenter,
            prompt,
            options,
            background_draw_func=lambda: self.draw_frame(
                choice_beat, transcript=choice_transcript, do_flip=False
            ),
            allow_cancel=allow_cancel,
        ).show(flush_events=True, require_key_release=True)
        if choice is None or not record_selection:
            return choice

        player_name = str(getattr(self.player_char, "name", speaker) or speaker)
        selected_beat = StoryBeat(
            player_name,
            options[choice],
            PLAYER_PORTRAIT_KEY if self.player_char is not None else portrait_name,
        )
        self.show_dialogue((selected_beat,))
        return choice
