#!/usr/bin/env python3
"""Focused coverage for shared pygame popup helpers."""

from __future__ import annotations

from types import SimpleNamespace

import pygame

from src.ui_pygame.gui import confirmation_popup
from src.ui_pygame.gui.input_guards import (
    prepare_guarded_input,
    release_guard_allows_input,
    update_input_armed_from_event,
)


class RenderedText:
    def __init__(self, text):
        self.text = text

    def get_width(self):
        return max(8, len(self.text) * 8)

    def get_height(self):
        return 18

    def get_rect(self, **kwargs):
        rect = SimpleNamespace(x=0, y=0, width=self.get_width(), height=self.get_height())
        for key, value in kwargs.items():
            setattr(rect, key, value)
        return rect


class RecordingFont:
    def __init__(self):
        self.render_calls = []

    def render(self, text, _antialias, _color):
        self.render_calls.append(text)
        return RenderedText(text)

    def get_height(self):
        return 18

    def size(self, text):
        return (max(8, len(text) * 8), 18)


class RecordingScreen:
    def __init__(self):
        self.blit_calls = []
        self.fill_calls = []

    def blit(self, surface, position):
        self.blit_calls.append((surface, position))

    def fill(self, color):
        self.fill_calls.append(color)

    def copy(self):
        return "copied-surface"


def _make_presenter(*, debug_mode=False):
    return SimpleNamespace(
        screen=RecordingScreen(),
        width=640,
        height=480,
        title_font=RecordingFont(),
        large_font=RecordingFont(),
        normal_font=RecordingFont(),
        small_font=RecordingFont(),
        debug_mode=debug_mode,
        clock=SimpleNamespace(tick=lambda _fps: None),
    )


def _event(event_type, key=None):
    evt = SimpleNamespace(type=event_type)
    if key is not None:
        evt.key = key
    return evt


def _mouse_event(event_type, pos, button=1, y=0):
    return SimpleNamespace(type=event_type, pos=pos, button=button, y=y)


def _patch_visuals(monkeypatch):
    monkeypatch.setattr(
        "src.ui_pygame.gui.confirmation_popup.pygame.draw.rect", lambda *_args, **_kwargs: None
    )
    monkeypatch.setattr("src.ui_pygame.gui.confirmation_popup.pygame.display.flip", lambda: None)


def test_confirmation_popup_wrap_visible_lines_and_background_helpers(monkeypatch):
    _patch_visuals(monkeypatch)
    presenter = _make_presenter()
    popup = confirmation_popup.ConfirmationPopup(
        presenter,
        "Alpha beta gamma delta epsilon zeta eta theta\n\nSecond paragraph",
        show_buttons=False,
        slow_print=True,
    )

    assert popup.popup_height >= 180
    assert "" in popup._wrapped_lines

    tick_values = iter([popup._start_ms + 100, popup._start_ms + 10000])
    monkeypatch.setattr(
        "src.ui_pygame.gui.confirmation_popup.pygame.time.get_ticks", lambda: next(tick_values)
    )
    visible = popup._get_visible_lines()
    assert visible[0].startswith("Al")
    assert popup._reveal_complete() is True

    presenter.get_background_surface = lambda: "bg-surface"
    assert popup._get_background_surface() == "bg-surface"
    presenter.get_background_surface = lambda: None
    assert popup._get_background_surface() == "copied-surface"
    presenter.get_background_surface = lambda: presenter.screen
    assert popup._get_background_surface() == "copied-surface"
    presenter.get_background_surface = lambda: (_ for _ in ()).throw(RuntimeError("boom"))
    assert popup._get_background_surface() == "copied-surface"


def test_release_guard_allows_input_after_buffered_keys_clear(monkeypatch):
    pressed_states = iter([[1], [], [1]])
    monkeypatch.setattr("src.ui_pygame.gui.input_guards.pygame.event.pump", lambda: None)
    monkeypatch.setattr(
        "src.ui_pygame.gui.input_guards.pygame.key.get_pressed",
        lambda: next(pressed_states),
    )
    monkeypatch.setattr(
        "src.ui_pygame.gui.input_guards.pygame.mouse.get_pressed",
        lambda: (False, False, False),
    )

    assert release_guard_allows_input(True, False) is False
    assert release_guard_allows_input(True, False) is True
    assert release_guard_allows_input(True, True) is True
    assert release_guard_allows_input(False, False) is True


def test_release_guard_pumps_events_before_reading_key_state(monkeypatch):
    held = {"value": True}
    pump_calls = []

    def fake_pump():
        pump_calls.append(True)
        held["value"] = False

    monkeypatch.setattr("src.ui_pygame.gui.input_guards.pygame.event.pump", fake_pump)
    monkeypatch.setattr(
        "src.ui_pygame.gui.input_guards.pygame.key.get_pressed",
        lambda: [1] if held["value"] else [],
    )
    monkeypatch.setattr(
        "src.ui_pygame.gui.input_guards.pygame.mouse.get_pressed",
        lambda: (False, False, False),
    )

    assert release_guard_allows_input(True, False) is True
    assert pump_calls == [True]


def test_release_guard_waits_for_mouse_button_release(monkeypatch):
    """A popup must not accept the mouse-down event that opened it."""
    mouse_states = iter([(True, False, False), (False, False, False)])
    monkeypatch.setattr("src.ui_pygame.gui.input_guards.pygame.event.pump", lambda: None)
    monkeypatch.setattr("src.ui_pygame.gui.input_guards.pygame.key.get_pressed", lambda: [])
    monkeypatch.setattr(
        "src.ui_pygame.gui.input_guards.pygame.mouse.get_pressed",
        lambda: next(mouse_states),
    )

    assert release_guard_allows_input(True, False) is False
    assert release_guard_allows_input(True, False) is True


def test_shared_input_guard_prepare_and_event_release(monkeypatch):
    clear_calls = []
    monkeypatch.setattr(
        "src.ui_pygame.gui.input_guards.pygame.event.clear", lambda: clear_calls.append(True)
    )
    monkeypatch.setattr("src.ui_pygame.gui.input_guards.pygame.key.get_pressed", lambda: [1])

    assert prepare_guarded_input(flush_events=True, require_key_release=True) is False
    assert clear_calls == [True]
    assert (
        update_input_armed_from_event(_event(pygame.KEYDOWN, pygame.K_RETURN), True, False) is False
    )
    assert update_input_armed_from_event(_event(pygame.KEYUP, pygame.K_RETURN), True, False) is True


def test_all_popup_background_helpers_reject_live_or_empty_provider(monkeypatch):
    _patch_visuals(monkeypatch)
    presenter = _make_presenter()

    popups = [
        confirmation_popup.ConfirmationPopup(presenter, "Proceed?"),
        confirmation_popup.ChoicePopup(presenter, "Pick", ["Alpha"]),
        confirmation_popup.RewardSelectionPopup(
            presenter,
            "Rewards",
            [SimpleNamespace(name="Potion")],
            detail_provider=lambda item: item.name,
        ),
        confirmation_popup.QuantityPopup(presenter, "Potion"),
        confirmation_popup.CodeEntryPopup(presenter, "Vault", "Enter code"),
    ]

    for popup in popups:
        presenter.get_background_surface = lambda: "provided-background"
        assert popup._get_background_surface() == "provided-background"
        presenter.get_background_surface = lambda: None
        assert popup._get_background_surface() == "copied-surface"
        presenter.get_background_surface = lambda: presenter.screen
        assert popup._get_background_surface() == "copied-surface"
        presenter.get_background_surface = lambda: (_ for _ in ()).throw(RuntimeError("boom"))
        assert popup._get_background_surface() == "copied-surface"


def test_confirmation_popup_show_handles_navigation_and_message_only(monkeypatch):
    _patch_visuals(monkeypatch)
    presenter = _make_presenter()
    popup = confirmation_popup.ConfirmationPopup(presenter, "Proceed?")
    clear_calls = []
    draw_calls = []
    popup.draw_popup = lambda: draw_calls.append("drawn")

    event_batches = iter(
        [
            [_event(pygame.KEYDOWN, pygame.K_RIGHT)],
            [_event(pygame.KEYDOWN, pygame.K_RETURN)],
        ]
    )
    monkeypatch.setattr(
        "src.ui_pygame.gui.confirmation_popup.pygame.event.get", lambda: next(event_batches, [])
    )
    monkeypatch.setattr(
        "src.ui_pygame.gui.confirmation_popup.pygame.event.clear", lambda: clear_calls.append(True)
    )
    monkeypatch.setattr("src.ui_pygame.gui.confirmation_popup.pygame.time.get_ticks", lambda: 1000)

    bg_calls = []
    assert (
        popup.show(background_draw_func=lambda: bg_calls.append("bg"), flush_events=True) is False
    )
    assert clear_calls == [True]
    assert draw_calls
    assert bg_calls[-1] == "bg"

    message_popup = confirmation_popup.ConfirmationPopup(presenter, "Notice", show_buttons=False)
    message_popup.draw_popup = lambda: None
    monkeypatch.setattr(
        "src.ui_pygame.gui.confirmation_popup.pygame.event.get",
        lambda: [_event(pygame.KEYDOWN, pygame.K_SPACE)],
    )
    assert message_popup.show() is True


def test_confirmation_popup_show_respects_require_release_slow_print_and_min_display(monkeypatch):
    _patch_visuals(monkeypatch)
    presenter = _make_presenter()
    popup = confirmation_popup.ConfirmationPopup(presenter, "Slow reveal test", slow_print=True)
    popup.draw_popup = lambda: None

    tick_values = iter([1000, 1005, 1010, 4000, 4000, 4000, 4000])
    monkeypatch.setattr(
        "src.ui_pygame.gui.confirmation_popup.pygame.time.get_ticks", lambda: next(tick_values)
    )

    pressed_states = iter([[1], [], []])
    monkeypatch.setattr(
        "src.ui_pygame.gui.confirmation_popup.pygame.key.get_pressed", lambda: next(pressed_states)
    )

    event_batches = iter(
        [
            [_event(pygame.KEYDOWN, pygame.K_RETURN)],
            [_event(pygame.KEYDOWN, pygame.K_RETURN)],
            [_event(pygame.KEYDOWN, pygame.K_RETURN)],
            [_event(pygame.KEYDOWN, pygame.K_RETURN)],
        ]
    )
    monkeypatch.setattr(
        "src.ui_pygame.gui.confirmation_popup.pygame.event.get", lambda: next(event_batches, [])
    )

    assert popup.show(require_key_release=True, min_display_ms=2000) is True


def test_choice_popup_draw_and_show_cover_wrap_navigation_and_escape(monkeypatch):
    _patch_visuals(monkeypatch)
    presenter = _make_presenter()
    popup = confirmation_popup.ChoicePopup(
        presenter,
        "Pick One",
        ["Alpha", "Beta", "Gamma"],
        header_message="This is a long header that should wrap across multiple lines.",
    )

    popup.draw_popup("background", do_flip=False)
    assert len(popup._header_lines) >= 1
    assert "UP/DOWN: Navigate  ENTER: Select  ESC: Cancel" in presenter.small_font.render_calls

    event_batches = iter(
        [
            [_event(pygame.KEYDOWN, pygame.K_DOWN)],
            [_event(pygame.KEYDOWN, pygame.K_RETURN)],
        ]
    )
    monkeypatch.setattr(
        "src.ui_pygame.gui.confirmation_popup.pygame.event.get", lambda: next(event_batches, [])
    )
    assert popup.show() == 1

    popup.current_selection = 0
    monkeypatch.setattr(
        "src.ui_pygame.gui.confirmation_popup.pygame.event.get",
        lambda: [_event(pygame.KEYDOWN, pygame.K_ESCAPE)],
    )
    assert popup.show() is None


def test_popup_mouse_paths_select_confirm_and_adjust(monkeypatch):
    _patch_visuals(monkeypatch)
    presenter = _make_presenter()
    monkeypatch.setattr("src.ui_pygame.gui.confirmation_popup.pygame.event.clear", lambda: None)
    monkeypatch.setattr("src.ui_pygame.gui.confirmation_popup.pygame.key.get_pressed", lambda: [])
    monkeypatch.setattr("src.ui_pygame.gui.confirmation_popup.pygame.display.flip", lambda: None)

    confirm = confirmation_popup.ConfirmationPopup(presenter, "Proceed?")
    no_pos = confirm.button_rects()[1].center
    event_batches = iter(
        [
            [_mouse_event(pygame.MOUSEMOTION, no_pos, button=0)],
            [_mouse_event(pygame.MOUSEBUTTONDOWN, no_pos)],
        ]
    )
    monkeypatch.setattr(
        "src.ui_pygame.gui.confirmation_popup.pygame.event.get", lambda: next(event_batches, [])
    )
    assert confirm.show() is False

    choice = confirmation_popup.ChoicePopup(presenter, "Pick", ["Alpha", "Beta"])
    beta_pos = choice.option_rects()[1].center
    event_batches = iter(
        [
            [_mouse_event(pygame.MOUSEBUTTONDOWN, beta_pos)],
        ]
    )
    monkeypatch.setattr(
        "src.ui_pygame.gui.confirmation_popup.pygame.event.get", lambda: next(event_batches, [])
    )
    assert choice.show() == 1

    quantity = confirmation_popup.QuantityPopup(
        presenter, "Potion", max_quantity=9, default_quantity=1
    )
    event_batches = iter(
        [
            [_mouse_event(pygame.MOUSEWHEEL, (0, 0), button=0, y=1)],
            [_mouse_event(pygame.MOUSEBUTTONDOWN, quantity.button_rects()["confirm"].center)],
        ]
    )
    monkeypatch.setattr(
        "src.ui_pygame.gui.confirmation_popup.pygame.event.get", lambda: next(event_batches, [])
    )
    assert quantity.show() == 2

    code = confirmation_popup.CodeEntryPopup(presenter, "Vault", "Enter code")
    digit_pos = code.digit_rects()[1].center
    event_batches = iter(
        [
            [_mouse_event(pygame.MOUSEBUTTONDOWN, digit_pos)],
            [_mouse_event(pygame.MOUSEWHEEL, digit_pos, button=0, y=1)],
            [_mouse_event(pygame.MOUSEBUTTONDOWN, code.button_rects()["confirm"].center)],
        ]
    )
    monkeypatch.setattr(
        "src.ui_pygame.gui.confirmation_popup.pygame.event.get", lambda: next(event_batches, [])
    )
    assert code.show() == "0100"


def test_popup_close_x_returns_cancel_or_dismiss(monkeypatch):
    presenter = _make_presenter()
    monkeypatch.setattr("src.ui_pygame.gui.confirmation_popup.pygame.event.clear", lambda: None)
    monkeypatch.setattr("src.ui_pygame.gui.confirmation_popup.pygame.key.get_pressed", lambda: [])
    monkeypatch.setattr("src.ui_pygame.gui.confirmation_popup.pygame.display.flip", lambda: None)

    confirm = confirmation_popup.ConfirmationPopup(presenter, "Proceed?")
    confirm.draw_popup = lambda: None
    close_pos = confirmation_popup.popup_close_rect(confirm.popup_rect).center
    event_batches = iter([[_mouse_event(pygame.MOUSEBUTTONDOWN, close_pos)]])
    monkeypatch.setattr(
        "src.ui_pygame.gui.confirmation_popup.pygame.event.get", lambda: next(event_batches, [])
    )
    assert confirm.show() is False

    message = confirmation_popup.ConfirmationPopup(presenter, "Read this.", show_buttons=False)
    message.draw_popup = lambda: None
    close_pos = confirmation_popup.popup_close_rect(message.popup_rect).center
    event_batches = iter([[_mouse_event(pygame.MOUSEBUTTONDOWN, close_pos)]])
    monkeypatch.setattr(
        "src.ui_pygame.gui.confirmation_popup.pygame.event.get", lambda: next(event_batches, [])
    )
    assert message.show() is True

    choice = confirmation_popup.ChoicePopup(presenter, "Pick", ["Alpha", "Beta"])
    choice.draw_popup = lambda *_args, **_kwargs: None
    close_pos = confirmation_popup.popup_close_rect(choice.popup_rect).center
    event_batches = iter([[_mouse_event(pygame.MOUSEBUTTONDOWN, close_pos)]])
    monkeypatch.setattr(
        "src.ui_pygame.gui.confirmation_popup.pygame.event.get", lambda: next(event_batches, [])
    )
    assert choice.show() is None

    quantity = confirmation_popup.QuantityPopup(
        presenter, "Potion", max_quantity=9, default_quantity=1
    )
    quantity.draw_popup = lambda *_args, **_kwargs: None
    close_pos = confirmation_popup.popup_close_rect(quantity.popup_rect).center
    event_batches = iter([[_mouse_event(pygame.MOUSEBUTTONDOWN, close_pos)]])
    monkeypatch.setattr(
        "src.ui_pygame.gui.confirmation_popup.pygame.event.get", lambda: next(event_batches, [])
    )
    assert quantity.show() is None


def test_reward_selection_popup_draw_and_show_confirm_branch(monkeypatch):
    _patch_visuals(monkeypatch)
    presenter = _make_presenter()
    long_name = "Very Long Reward Name That Needs Truncation"
    items = [SimpleNamespace(name=long_name), SimpleNamespace(name="Potion")]
    popup = confirmation_popup.RewardSelectionPopup(
        presenter,
        "Rewards",
        items,
        detail_provider=lambda item: f"Details for {item.name}\nSecond line",
    )

    popup.draw_popup("background", do_flip=False)
    assert any(text.endswith("...") for text in presenter.normal_font.render_calls)

    class FakeConfirm:
        def __init__(self, _presenter, message, show_buttons=True):
            self.message = message
            self.show_buttons = show_buttons

        def show(self, **_kwargs):
            return True

    monkeypatch.setattr(confirmation_popup, "ConfirmationPopup", FakeConfirm)
    event_batches = iter(
        [
            [_event(pygame.KEYDOWN, pygame.K_DOWN)],
            [_event(pygame.KEYDOWN, pygame.K_RETURN)],
        ]
    )
    monkeypatch.setattr(
        "src.ui_pygame.gui.confirmation_popup.pygame.event.get", lambda: next(event_batches, [])
    )
    assert popup.show() == 1

    empty_popup = confirmation_popup.RewardSelectionPopup(
        presenter, "Rewards", [], lambda _item: ""
    )
    assert empty_popup.show() is None


def test_reward_selection_popup_mouse_selects_and_confirms(monkeypatch):
    _patch_visuals(monkeypatch)
    presenter = _make_presenter()
    popup = confirmation_popup.RewardSelectionPopup(
        presenter,
        "Rewards",
        [SimpleNamespace(name="Gold"), SimpleNamespace(name="Potion")],
        detail_provider=lambda item: item.name,
    )

    class FakeConfirm:
        def __init__(self, _presenter, message, show_buttons=True):
            self.message = message
            self.show_buttons = show_buttons

        def show(self, **_kwargs):
            return True

    monkeypatch.setattr(confirmation_popup, "ConfirmationPopup", FakeConfirm)
    monkeypatch.setattr("src.ui_pygame.gui.confirmation_popup.pygame.key.get_pressed", lambda: [])
    click_pos = popup.row_rects()[1].center
    event_batches = iter(
        [
            [_mouse_event(pygame.MOUSEBUTTONDOWN, click_pos)],
        ]
    )
    monkeypatch.setattr(
        "src.ui_pygame.gui.confirmation_popup.pygame.event.get", lambda: next(event_batches, [])
    )

    assert popup.show() == 1


def test_reward_selection_popup_can_flush_and_wait_for_key_release(monkeypatch):
    _patch_visuals(monkeypatch)
    presenter = _make_presenter()
    popup = confirmation_popup.RewardSelectionPopup(
        presenter,
        "Rewards",
        [SimpleNamespace(name="Potion")],
        detail_provider=lambda item: item.name,
    )

    class FakeConfirm:
        def __init__(self, _presenter, _message, show_buttons=True):
            pass

        def show(self, **_kwargs):
            return True

    clear_calls = []
    pressed_states = iter([[1], []])
    event_batches = iter(
        [
            [_event(pygame.KEYDOWN, pygame.K_RETURN)],
            [_event(pygame.KEYDOWN, pygame.K_RETURN)],
        ]
    )
    monkeypatch.setattr(confirmation_popup, "ConfirmationPopup", FakeConfirm)
    monkeypatch.setattr(
        "src.ui_pygame.gui.confirmation_popup.pygame.event.clear", lambda: clear_calls.append(True)
    )
    monkeypatch.setattr(
        "src.ui_pygame.gui.confirmation_popup.pygame.key.get_pressed", lambda: next(pressed_states)
    )
    monkeypatch.setattr(
        "src.ui_pygame.gui.confirmation_popup.pygame.event.get", lambda: next(event_batches, [])
    )

    assert popup.show(flush_events=True, require_key_release=True) == 0
    assert clear_calls == [True]


def test_quantity_popup_draw_and_show_cover_adjustment_confirmation_and_cancel(monkeypatch):
    _patch_visuals(monkeypatch)
    presenter = _make_presenter()
    popup = confirmation_popup.QuantityPopup(
        presenter,
        "Potion",
        unit_cost=5,
        max_quantity=12,
        action="sell",
        default_quantity=27,
    )

    popup.draw_popup(background_draw_func=lambda: presenter.screen.fill((1, 2, 3)))
    assert popup.quantity == 12
    assert "Sell Potion" in presenter.title_font.render_calls
    assert "Total Value: 60g" in presenter.normal_font.render_calls

    event_batches = iter(
        [
            [_event(pygame.KEYDOWN, pygame.K_UP)],
            [_event(pygame.KEYDOWN, pygame.K_LEFT)],
            [_event(pygame.KEYDOWN, pygame.K_DOWN)],
            [_event(pygame.KEYDOWN, pygame.K_RETURN)],
        ]
    )
    monkeypatch.setattr(
        "src.ui_pygame.gui.confirmation_popup.pygame.event.get", lambda: next(event_batches, [])
    )
    assert popup.show() == 2

    cancel_popup = confirmation_popup.QuantityPopup(presenter, "Potion", max_quantity=9)
    monkeypatch.setattr(
        "src.ui_pygame.gui.confirmation_popup.pygame.event.get",
        lambda: [_event(pygame.KEYDOWN, pygame.K_ESCAPE)],
    )
    assert cancel_popup.show() is None

    arrow_cancel_popup = confirmation_popup.QuantityPopup(
        presenter, "Potion", max_quantity=9, default_quantity=1
    )
    arrow_cancel_events = iter(
        [
            [_event(pygame.KEYDOWN, pygame.K_RIGHT)],
            [_event(pygame.KEYDOWN, pygame.K_RIGHT)],
            [_event(pygame.KEYDOWN, pygame.K_RETURN)],
        ]
    )
    monkeypatch.setattr(
        "src.ui_pygame.gui.confirmation_popup.pygame.event.get",
        lambda: next(arrow_cancel_events, []),
    )
    assert arrow_cancel_popup.show() is None


def test_quantity_popup_can_flush_and_wait_for_key_release(monkeypatch):
    _patch_visuals(monkeypatch)
    presenter = _make_presenter()
    popup = confirmation_popup.QuantityPopup(presenter, "Potion", max_quantity=9)
    clear_calls = []

    monkeypatch.setattr(
        "src.ui_pygame.gui.confirmation_popup.pygame.event.clear", lambda: clear_calls.append(True)
    )
    pressed_states = iter([[1], [], []])
    monkeypatch.setattr(
        "src.ui_pygame.gui.confirmation_popup.pygame.key.get_pressed",
        lambda: next(pressed_states, []),
    )
    monkeypatch.setattr(
        "src.ui_pygame.gui.confirmation_popup.pygame.mouse.get_pressed",
        lambda: (False, False, False),
    )
    event_batches = iter(
        [
            [_event(pygame.KEYDOWN, pygame.K_RETURN)],
            [_event(pygame.KEYDOWN, pygame.K_UP)],
            [_event(pygame.KEYDOWN, pygame.K_RETURN)],
        ]
    )
    monkeypatch.setattr(
        "src.ui_pygame.gui.confirmation_popup.pygame.event.get", lambda: next(event_batches, [])
    )

    assert popup.show(flush_events=True, require_key_release=True) == 1
    assert clear_calls == [True]


def test_code_entry_popup_draw_and_show_cover_digit_navigation(monkeypatch):
    _patch_visuals(monkeypatch)
    presenter = _make_presenter()
    popup = confirmation_popup.CodeEntryPopup(presenter, "Vault", "Enter code")

    popup.draw_popup(background_draw_func=lambda: presenter.screen.fill((0, 0, 0)))
    assert "Enter code" in presenter.normal_font.render_calls

    event_batches = iter(
        [
            [_event(pygame.KEYDOWN, pygame.K_UP)],
            [_event(pygame.KEYDOWN, pygame.K_RIGHT)],
            [_event(pygame.KEYDOWN, pygame.K_UP)],
            [_event(pygame.KEYDOWN, pygame.K_RETURN)],
        ]
    )
    monkeypatch.setattr(
        "src.ui_pygame.gui.confirmation_popup.pygame.event.get", lambda: next(event_batches, [])
    )
    assert popup.show() == "1100"

    cancel_popup = confirmation_popup.CodeEntryPopup(presenter, "Vault", "Enter code")
    monkeypatch.setattr(
        "src.ui_pygame.gui.confirmation_popup.pygame.event.get",
        lambda: [_event(pygame.KEYDOWN, pygame.K_ESCAPE)],
    )
    assert cancel_popup.show() is None


def test_code_entry_popup_can_flush_and_wait_for_key_release(monkeypatch):
    _patch_visuals(monkeypatch)
    presenter = _make_presenter()
    popup = confirmation_popup.CodeEntryPopup(presenter, "Vault", "Enter code")
    clear_calls = []

    monkeypatch.setattr(
        "src.ui_pygame.gui.confirmation_popup.pygame.event.clear", lambda: clear_calls.append(True)
    )
    pressed_states = iter([[1], [], []])
    monkeypatch.setattr(
        "src.ui_pygame.gui.confirmation_popup.pygame.key.get_pressed",
        lambda: next(pressed_states, []),
    )
    monkeypatch.setattr(
        "src.ui_pygame.gui.confirmation_popup.pygame.mouse.get_pressed",
        lambda: (False, False, False),
    )
    event_batches = iter(
        [
            [_event(pygame.KEYDOWN, pygame.K_RETURN)],
            [_event(pygame.KEYDOWN, pygame.K_UP)],
            [_event(pygame.KEYDOWN, pygame.K_RETURN)],
        ]
    )
    monkeypatch.setattr(
        "src.ui_pygame.gui.confirmation_popup.pygame.event.get", lambda: next(event_batches, [])
    )

    assert popup.show(flush_events=True, require_key_release=True) == "1000"
    assert clear_calls == [True]


def test_confirm_yes_no_helper_delegates_to_popup(monkeypatch):
    presenter = _make_presenter()

    class FakeConfirm:
        def __init__(self, received_presenter, message):
            self.received_presenter = received_presenter
            self.message = message
            self.show_kwargs = None

        def show(self, **kwargs):
            self.show_kwargs = kwargs
            return True

    monkeypatch.setattr(confirmation_popup, "ConfirmationPopup", FakeConfirm)
    assert confirmation_popup.confirm_yes_no(presenter, "Continue?") is True


def test_confirm_yes_no_uses_stale_input_guard(monkeypatch):
    presenter = _make_presenter()
    created = []

    class FakeConfirm:
        def __init__(self, received_presenter, message):
            self.received_presenter = received_presenter
            self.message = message
            self.show_kwargs = None
            created.append(self)

        def show(self, **kwargs):
            self.show_kwargs = kwargs
            return False

    monkeypatch.setattr(confirmation_popup, "ConfirmationPopup", FakeConfirm)

    assert confirmation_popup.confirm_yes_no(presenter, "Quit?") is False
    assert created[0].show_kwargs == {
        "flush_events": True,
        "require_key_release": True,
    }
