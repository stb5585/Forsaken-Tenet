"""Shared helpers for pygame stale-input guards."""

from __future__ import annotations

import pygame


def _input_devices_released(require_key_release: bool) -> bool:
    """Return whether input that could activate a control is no longer held."""
    try:
        pygame.event.pump()
    except pygame.error:
        pass
    if require_key_release:
        try:
            keys_released = not any(pygame.key.get_pressed())
        except pygame.error:
            # Headless tests and a transient display reset may not expose key
            # state, but that must not override a known held mouse button.
            keys_released = True
    else:
        keys_released = True
    try:
        mouse_released = not any(pygame.mouse.get_pressed())
    except pygame.error:
        mouse_released = True
    return keys_released and mouse_released


def prepare_guarded_input(*, flush_events: bool = False, require_key_release: bool = False) -> bool:
    """Clear buffered events and arm only after any held pointer is released."""
    if flush_events:
        try:
            pygame.event.clear()
        except pygame.error:
            pass
    # Pointer release is always required for a newly entered clickable view.
    # Keyboard release remains opt-in so text/menu flows retain their existing
    # behavior unless they explicitly request it.
    return _input_devices_released(require_key_release)


def release_guard_allows_input(require_key_release: bool, input_armed: bool) -> bool:
    """Return whether guarded input may accept a new selection event."""
    if input_armed:
        return True
    return _input_devices_released(require_key_release)


def update_input_armed_from_event(event, require_key_release: bool, input_armed: bool) -> bool:
    """Refresh a release guard after a release event.

    The physical state check avoids arming one input device while another is
    still held, which is what allows a click that opened a popup to activate a
    control inside it.
    """
    if input_armed:
        return True
    if event.type == pygame.MOUSEBUTTONUP or (require_key_release and event.type == pygame.KEYUP):
        return _input_devices_released(require_key_release)
    return input_armed
