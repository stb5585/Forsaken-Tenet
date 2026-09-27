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
    # A keyboard guard starts unarmed without reading key state. The first
    # frame must still discard a queued KEYDOWN that opened this view; its
    # usual per-frame release check will arm the next frame after the key is
    # physically up. Pointer-only views can be armed immediately, but never
    # while the pointer button is held.
    if require_key_release:
        return False
    return _input_devices_released(False)


def release_guard_allows_input(require_key_release: bool, input_armed: bool) -> bool:
    """Return whether guarded input may accept a new selection event."""
    if input_armed:
        return True
    return _input_devices_released(require_key_release)


def update_input_armed_from_event(event, require_key_release: bool, input_armed: bool) -> bool:
    """Refresh a release guard after a release event.

    A release event is the reliable ordering boundary for queued input. Do not
    poll device state here: headless backends and remote input can report
    stale state after Pygame has already delivered the release event.
    """
    if input_armed or not require_key_release:
        return True
    if event.type in (pygame.KEYUP, pygame.MOUSEBUTTONUP):
        return True
    return input_armed
