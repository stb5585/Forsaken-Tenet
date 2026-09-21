"""Non-blocking Pygame screen stack with a single event-pump owner."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any, Protocol, TypeVar

import pygame

from src.ui_common.input import UiCommand


class TransitionKind(str, Enum):
    """Operations a screen may request from the runtime."""

    PUSH = "push"
    REPLACE = "replace"
    POP = "pop"
    QUIT = "quit"


@dataclass(frozen=True)
class ScreenInput:
    """Normalized input plus optional pointer and text payloads."""

    command: UiCommand | None = None
    pointer: tuple[int, int] | None = None
    text: str = ""
    pressed: bool | None = None
    button: int | None = None


ScreenResult = TypeVar("ScreenResult")


@dataclass(frozen=True)
class ScreenTransition:
    """One requested stack transition."""

    kind: TransitionKind
    screen: Screen | None = None
    result: Any = None

    @classmethod
    def push(cls, screen: Screen) -> ScreenTransition:
        return cls(TransitionKind.PUSH, screen=screen)

    @classmethod
    def replace(cls, screen: Screen) -> ScreenTransition:
        return cls(TransitionKind.REPLACE, screen=screen)

    @classmethod
    def pop(cls, result: Any = None) -> ScreenTransition:
        return cls(TransitionKind.POP, result=result)

    @classmethod
    def quit(cls) -> ScreenTransition:
        return cls(TransitionKind.QUIT)


class Screen(Protocol):
    """Lifecycle implemented by non-blocking Pygame screens."""

    def enter(self) -> None:
        """Prepare the screen after it becomes the active stack entry."""

    def handle_input(self, event: ScreenInput) -> ScreenTransition | None:
        """Handle one normalized input event."""

    def update(self, elapsed_seconds: float) -> ScreenTransition | None:
        """Advance animations and time-dependent state."""

    def render(self, surface: pygame.Surface) -> None:
        """Draw the current frame."""

    def resume(self, result: Any = None) -> None:
        """Resume after a child screen pops and optionally returns a result."""

    def exit(self) -> None:
        """Release screen-local state before removal from the stack."""


_KEY_COMMANDS: dict[int, UiCommand] = {
    pygame.K_UP: UiCommand.NAVIGATE_UP,
    pygame.K_w: UiCommand.NAVIGATE_UP,
    pygame.K_DOWN: UiCommand.NAVIGATE_DOWN,
    pygame.K_s: UiCommand.NAVIGATE_DOWN,
    pygame.K_RETURN: UiCommand.CONFIRM,
    pygame.K_KP_ENTER: UiCommand.CONFIRM,
    pygame.K_SPACE: UiCommand.CONFIRM,
    pygame.K_ESCAPE: UiCommand.CANCEL,
    pygame.K_PAGEUP: UiCommand.PAGE_PREVIOUS,
    pygame.K_PAGEDOWN: UiCommand.PAGE_NEXT,
}


def normalize_event(event: pygame.event.Event) -> ScreenInput | None:
    """Translate a Pygame event into the screen input contract."""
    if event.type == pygame.KEYDOWN:
        return ScreenInput(
            command=_KEY_COMMANDS.get(event.key),
            text=getattr(event, "unicode", ""),
            pressed=True,
        )
    if event.type == pygame.KEYUP:
        return ScreenInput(command=_KEY_COMMANDS.get(event.key), pressed=False)
    if event.type == pygame.TEXTINPUT:
        return ScreenInput(text=event.text)
    if event.type == pygame.MOUSEMOTION:
        return ScreenInput(pointer=tuple(event.pos))
    if event.type in (pygame.MOUSEBUTTONDOWN, pygame.MOUSEBUTTONUP):
        return ScreenInput(
            pointer=tuple(event.pos),
            pressed=event.type == pygame.MOUSEBUTTONDOWN,
            button=event.button,
        )
    return None


def _poll_pygame_events(event_types: int | tuple[int, ...] | None = None) -> list[pygame.event.Event]:
    """Read the process event queue; this is the sole direct polling boundary."""
    if event_types is None:
        return list(pygame.event.get())
    return list(pygame.event.get(event_types))


def get_events(event_types: int | tuple[int, ...] | None = None) -> list[pygame.event.Event]:
    """Return queued events for legacy flows during incremental screen migration.

    New screens receive normalized input from :class:`ScreenRuntime`. This
    compatibility boundary keeps remaining blocking screens from owning a
    direct Pygame queue read while they are converted to runtime states.
    """
    return _poll_pygame_events(event_types)


class ScreenRuntime:
    """Own the Pygame event pump, frame clock, and active screen stack."""

    def __init__(
        self,
        surface: pygame.Surface,
        initial_screen: Screen | None = None,
        *,
        frames_per_second: int = 60,
        clock: pygame.time.Clock | None = None,
    ) -> None:
        if frames_per_second <= 0:
            raise ValueError("frames_per_second must be positive")
        self.surface = surface
        self.frames_per_second = frames_per_second
        self.clock = clock or pygame.time.Clock()
        self._screens: list[Screen] = []
        self.running = True
        if initial_screen is not None:
            self.push(initial_screen)

    @property
    def current(self) -> Screen | None:
        """Return the active screen, if the stack is non-empty."""
        return self._screens[-1] if self._screens else None

    @property
    def depth(self) -> int:
        """Return the current stack depth."""
        return len(self._screens)

    def push(self, screen: Screen) -> None:
        """Place and enter a screen above the current one."""
        self._screens.append(screen)
        screen.enter()

    def replace(self, screen: Screen) -> None:
        """Exit the active screen and replace it."""
        if self._screens:
            self._screens.pop().exit()
        self.push(screen)

    def pop(self, result: Any = None) -> None:
        """Exit the active screen and resume its parent with a result."""
        if not self._screens:
            self.running = False
            return
        self._screens.pop().exit()
        if self._screens:
            self._screens[-1].resume(result)
        else:
            self.running = False

    def quit(self) -> None:
        """Exit every screen and stop the runtime."""
        while self._screens:
            self._screens.pop().exit()
        self.running = False

    def _apply(self, transition: ScreenTransition | None) -> None:
        if transition is None:
            return
        if transition.kind == TransitionKind.PUSH:
            if transition.screen is None:
                raise ValueError("push transition requires a screen")
            self.push(transition.screen)
        elif transition.kind == TransitionKind.REPLACE:
            if transition.screen is None:
                raise ValueError("replace transition requires a screen")
            self.replace(transition.screen)
        elif transition.kind == TransitionKind.POP:
            self.pop(transition.result)
        elif transition.kind == TransitionKind.QUIT:
            self.quit()

    def run_frame(self) -> bool:
        """Process one frame and return whether the runtime remains active."""
        if not self.running or self.current is None:
            self.running = False
            return False

        elapsed_seconds = self.clock.tick(self.frames_per_second) / 1000.0
        for event in _poll_pygame_events():
            if event.type == pygame.QUIT:
                self.quit()
                return False
            normalized = normalize_event(event)
            if normalized is not None and self.current is not None:
                active = self.current
                self._apply(active.handle_input(normalized))
                if not self.running:
                    return False

        active = self.current
        if active is None:
            self.running = False
            return False
        self._apply(active.update(elapsed_seconds))
        if self.current is not None and self.running:
            self.current.render(self.surface)
            pygame.display.flip()
        return self.running

    def run(self) -> None:
        """Run frames until a screen requests quit or the stack empties."""
        while self.run_frame():
            pass
