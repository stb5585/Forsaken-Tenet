"""Persistent player-facing Pygame preferences."""

from __future__ import annotations

import json
from pathlib import Path

from src.paths import USER_CONFIG_DIR

DIALOGUE_SPEEDS: dict[str, int] = {
    "Slow": 20,
    "Normal": 35,
    "Fast": 60,
    "Instant": 0,
}
DEFAULT_DIALOGUE_CPS = DIALOGUE_SPEEDS["Normal"]
SETTINGS_PATH = USER_CONFIG_DIR / "ui_settings.json"


def load_dialogue_speed(path: Path = SETTINGS_PATH) -> int:
    """Load a validated dialogue characters-per-second preference."""
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        return DEFAULT_DIALOGUE_CPS
    if not isinstance(data, dict):
        return DEFAULT_DIALOGUE_CPS
    value = data.get("dialogue_characters_per_second")
    if isinstance(value, int) and not isinstance(value, bool) and value in DIALOGUE_SPEEDS.values():
        return value
    return DEFAULT_DIALOGUE_CPS


def save_dialogue_speed(characters_per_second: int, path: Path = SETTINGS_PATH) -> None:
    """Persist one validated dialogue-speed preference."""
    if characters_per_second not in DIALOGUE_SPEEDS.values():
        raise ValueError("unsupported dialogue speed")
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary_path = path.with_suffix(f"{path.suffix}.tmp")
    temporary_path.write_text(
        json.dumps(
            {"dialogue_characters_per_second": characters_per_second},
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    temporary_path.replace(path)


def dialogue_speed_label(characters_per_second: int) -> str:
    """Return the menu label for a stored dialogue speed."""
    for label, value in DIALOGUE_SPEEDS.items():
        if value == characters_per_second:
            return label
    return "Normal"
