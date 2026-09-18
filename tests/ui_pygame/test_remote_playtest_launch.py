"""Tests for enabling the opt-in remote playtest controls at launch."""

from src.ui_pygame import game as pygame_game


def test_main_passes_remote_playtest_flag_to_game(monkeypatch) -> None:
    calls = []

    class FakeGame:
        def __init__(self, **kwargs) -> None:
            calls.append(kwargs)

        def main_menu(self) -> None:
            calls.append("main_menu")

        def cleanup(self) -> None:
            calls.append("cleanup")

    monkeypatch.setattr(pygame_game, "PygameGame", FakeGame)
    monkeypatch.setattr(pygame_game, "install_signal_handlers", lambda: None)
    monkeypatch.setattr(
        pygame_game.sys,
        "argv",
        ["game_pygame.py", "--remote-playtest-controls"],
    )

    assert pygame_game.main() == 0
    assert calls == [
        {"debug_mode": False, "remote_playtest_controls": True},
        "main_menu",
        "cleanup",
    ]


def test_main_passes_opt_in_remote_input_diagnostics_to_game(monkeypatch) -> None:
    calls = []

    class FakeGame:
        def __init__(self, **kwargs) -> None:
            calls.append(kwargs)

        def main_menu(self) -> None:
            calls.append("main_menu")

        def cleanup(self) -> None:
            calls.append("cleanup")

    monkeypatch.setattr(pygame_game, "PygameGame", FakeGame)
    monkeypatch.setattr(pygame_game, "install_signal_handlers", lambda: None)
    monkeypatch.setattr(
        pygame_game.sys,
        "argv",
        [
            "game_pygame.py",
            "--remote-playtest-controls",
            "--remote-playtest-input-diagnostics",
        ],
    )

    assert pygame_game.main() == 0
    assert calls == [
        {
            "debug_mode": False,
            "remote_playtest_controls": True,
            "remote_playtest_input_diagnostics": True,
        },
        "main_menu",
        "cleanup",
    ]
