"""Tests for device-neutral dungeon command dispatch."""

from types import SimpleNamespace

from src.ui_common.input import UiCommand
from src.ui_pygame.gui.dungeon_manager.exploration import DungeonExplorationMixin


class StubDungeon(DungeonExplorationMixin):
    """Minimal command target that records the actions it receives."""

    def __init__(self) -> None:
        self.calls: list[str | int] = []
        self.game = SimpleNamespace(debug_mode=True, debug_level_up=self._record_debug_level_up)

    def move_forward(self) -> None:
        self.calls.append("forward")

    def turn_left(self) -> None:
        self.calls.append("left")

    def turn_right(self) -> None:
        self.calls.append("right")

    def turn_around(self) -> None:
        self.calls.append("around")

    def use_stairs_up(self) -> None:
        self.calls.append("stairs_up")

    def use_stairs_down(self) -> None:
        self.calls.append("stairs_down")

    def interact(self) -> None:
        self.calls.append("interact")

    def scroll_message_log(self, delta: int) -> None:
        self.calls.append(delta)

    def _show_enlarged_minimap(self) -> None:
        self.calls.append("map")

    def _get_character_screen(self) -> SimpleNamespace:
        return SimpleNamespace(navigate=lambda _player: "Exit Menu")

    def _show_menu(self) -> None:
        self.calls.append("menu")

    def _record_debug_level_up(self) -> None:
        self.calls.append("debug")


def test_dungeon_command_dispatch_is_device_neutral() -> None:
    dungeon = StubDungeon()

    assert dungeon.handle_command(UiCommand.DUNGEON_MOVE_FORWARD) is True
    assert dungeon.handle_command(UiCommand.DUNGEON_TURN_LEFT) is True
    assert dungeon.handle_command(UiCommand.DUNGEON_INTERACT) is True
    assert dungeon.handle_command(UiCommand.PAGE_PREVIOUS) is True
    assert dungeon.handle_command(UiCommand.OPEN_MENU) is True
    assert dungeon.handle_command(UiCommand.DEBUG_LEVEL_UP) is True
    assert dungeon.handle_command(UiCommand.CONFIRM) is False

    assert dungeon.calls == ["forward", "left", "interact", -1, "menu", "debug"]
