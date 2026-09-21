"""Headless tests for the single-owner Pygame screen runtime."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import pygame

from src.ui_common.input import UiCommand
from src.ui_pygame.screen_runtime import ScreenInput, ScreenRuntime, ScreenTransition


class Clock:
    """Deterministic clock double."""

    def tick(self, frames_per_second: int) -> int:
        assert frames_per_second == 60
        return 25


@dataclass
class RecordingScreen:
    """Minimal screen implementation that records lifecycle calls."""

    transitions: list[ScreenTransition | None] = field(default_factory=list)
    calls: list[Any] = field(default_factory=list)

    def enter(self) -> None:
        self.calls.append("enter")

    def handle_input(self, event: ScreenInput) -> ScreenTransition | None:
        self.calls.append(("input", event))
        return self.transitions.pop(0) if self.transitions else None

    def update(self, elapsed_seconds: float) -> ScreenTransition | None:
        self.calls.append(("update", elapsed_seconds))
        return None

    def render(self, surface: pygame.Surface) -> None:
        self.calls.append(("render", surface.get_size()))

    def resume(self, result: Any = None) -> None:
        self.calls.append(("resume", result))

    def exit(self) -> None:
        self.calls.append("exit")


def test_runtime_push_pop_resumes_parent(monkeypatch):
    parent = RecordingScreen()
    child = RecordingScreen(transitions=[ScreenTransition.pop("accepted")])
    parent.transitions.append(ScreenTransition.push(child))
    runtime = ScreenRuntime(pygame.Surface((32, 24)), parent, clock=Clock())
    events = iter(
        [
            [pygame.event.Event(pygame.KEYDOWN, key=pygame.K_RETURN, unicode="")],
            [pygame.event.Event(pygame.KEYDOWN, key=pygame.K_RETURN, unicode="")],
        ]
    )
    monkeypatch.setattr("src.ui_pygame.screen_runtime._poll_pygame_events", lambda: next(events))
    monkeypatch.setattr("src.ui_pygame.screen_runtime.pygame.display.flip", lambda: None)

    assert runtime.run_frame() is True
    assert runtime.current is child
    assert runtime.run_frame() is True
    assert runtime.current is parent
    assert ("resume", "accepted") in parent.calls
    assert "exit" in child.calls


def test_runtime_replace_and_quit(monkeypatch):
    replacement = RecordingScreen()
    first = RecordingScreen(transitions=[ScreenTransition.replace(replacement)])
    runtime = ScreenRuntime(pygame.Surface((8, 8)), first, clock=Clock())
    monkeypatch.setattr(
        "src.ui_pygame.screen_runtime._poll_pygame_events",
        lambda: [pygame.event.Event(pygame.KEYDOWN, key=pygame.K_DOWN, unicode="")],
    )
    monkeypatch.setattr("src.ui_pygame.screen_runtime.pygame.display.flip", lambda: None)

    assert runtime.run_frame() is True
    assert runtime.current is replacement
    assert "exit" in first.calls
    assert replacement.calls[0] == "enter"

    monkeypatch.setattr(
        "src.ui_pygame.screen_runtime._poll_pygame_events",
        lambda: [pygame.event.Event(pygame.QUIT)],
    )
    assert runtime.run_frame() is False
    assert runtime.current is None


def test_runtime_normalizes_text_and_pointer_payloads(monkeypatch):
    screen = RecordingScreen()
    runtime = ScreenRuntime(pygame.Surface((8, 8)), screen, clock=Clock())
    monkeypatch.setattr(
        "src.ui_pygame.screen_runtime._poll_pygame_events",
        lambda: [
            pygame.event.Event(pygame.TEXTINPUT, text="ø"),
            pygame.event.Event(pygame.MOUSEBUTTONDOWN, pos=(4, 6), button=1),
            pygame.event.Event(pygame.KEYDOWN, key=pygame.K_ESCAPE, unicode=""),
        ],
    )
    monkeypatch.setattr("src.ui_pygame.screen_runtime.pygame.display.flip", lambda: None)

    assert runtime.run_frame() is True
    inputs = [call[1] for call in screen.calls if isinstance(call, tuple) and call[0] == "input"]
    assert inputs[0].text == "ø"
    assert inputs[1].pointer == (4, 6)
    assert inputs[1].button == 1
    assert inputs[2].command == UiCommand.CANCEL


def test_screen_runtime_is_the_only_direct_event_queue_reader():
    """Player-facing modules must consume the centralized event source."""
    package_root = Path("src/ui_pygame")
    offenders = []
    for path in package_root.rglob("*.py"):
        if path.name == "screen_runtime.py":
            continue
        if "pygame.event.get(" in path.read_text(encoding="utf-8"):
            offenders.append(path)
    assert offenders == []
