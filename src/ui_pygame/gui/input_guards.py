"""Shared helpers for pygame stale-input guards."""

from __future__ import annotations

import pygame


def prepare_guarded_input(*, flush_events: bool = False, require_key_release: bool = False) -> bool:
    """Clear buffered events when requested and return the initial armed state."""
    if flush_events:
        try:
            pygame.event.clear()
        except pygame.error:
            pass
    return not require_key_release


def release_guard_allows_input(require_key_release: bool, input_armed: bool) -> bool:
    """Return whether guarded input may accept a new selection event."""
    if input_armed or not require_key_release:
        return True
    try:
        pygame.event.pump()
    except pygame.error:
        pass
    try:
        keys_released = not any(pygame.key.get_pressed())
        mouse_released = not any(pygame.mouse.get_pressed())
        return keys_released and mouse_released
    except pygame.error:
        return True


def update_input_armed_from_event(event, require_key_release: bool, input_armed: bool) -> bool:
    """Update guarded input state from release events or current keyboard state."""
    if input_armed or not require_key_release:
        return True
    if event.type in (pygame.KEYUP, pygame.MOUSEBUTTONUP):
        return True
    return input_armed
