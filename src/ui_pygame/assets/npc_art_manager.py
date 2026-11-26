"""Path resolution for approved NPC dialogue artwork."""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

from src.paths import PYGAME_ASSETS_DIR

logger = logging.getLogger(__name__)

NPC_ART_ROOT = PYGAME_ASSETS_DIR / "npc_art"
NPC_ART_FACING_MAP = NPC_ART_ROOT / "npc_art_facing.json"
_SHARED_NPC_ART_MANAGER: NpcArtManager | None = None


class NpcArtManager:
    """Resolve NPC display names to project-local portrait PNG paths."""

    def __init__(
        self,
        *,
        art_root: Path | None = None,
        art_map_path: Path | None = None,
        facing_map_path: Path | None = None,
    ) -> None:
        self.art_root = Path(art_root or NPC_ART_ROOT)
        self.art_map_path = Path(art_map_path or self.art_root / "npc_art_map.json")
        self.facing_map_path = Path(
            facing_map_path or self.art_root / NPC_ART_FACING_MAP.name
        )
        self.available_keys = {path.stem for path in self.art_root.glob("*.png") if path.is_file()}
        self.art_map: dict[str, str] = {}
        self.facing_map: dict[str, str] = {}
        self.load_map()
        self.load_facing_map()

    def load_map(self) -> None:
        if not self.art_map_path.exists():
            return
        try:
            data = json.loads(self.art_map_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            logger.warning("Could not load NPC art map %s: %s", self.art_map_path, exc)
            return
        if not isinstance(data, dict):
            logger.warning("NPC art map must be an object: %s", self.art_map_path)
            return
        self.art_map = {str(name): self.normalize_key(key) for name, key in data.items()}

    def load_facing_map(self) -> None:
        """Load native horizontal facing for inward stage composition."""
        if not self.facing_map_path.exists():
            return
        try:
            data = json.loads(self.facing_map_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            logger.warning("Could not load NPC facing map %s: %s", self.facing_map_path, exc)
            return
        if not isinstance(data, dict):
            logger.warning("NPC facing map must be an object: %s", self.facing_map_path)
            return
        self.facing_map = {
            self.normalize_key(key): str(direction)
            for key, direction in data.items()
            if str(direction) in {"left", "right", "front"}
        }

    @staticmethod
    def normalize_key(value: Any) -> str:
        text = str(value or "").strip().lower()
        return "_".join(part for part in text.replace("-", " ").split() if part)

    def get_art_key_for_npc(self, npc_name: Any) -> str | None:
        name = str(npc_name or "").strip()
        if not name:
            return None
        for candidate in (name, name.removeprefix("The ").strip()):
            mapped = self.art_map.get(candidate)
            if mapped and mapped in self.available_keys:
                return mapped
            normalized = self.normalize_key(candidate)
            if normalized in self.available_keys:
                return normalized
        return None

    def get_image_path(self, npc_name: Any) -> str:
        key = self.get_art_key_for_npc(npc_name)
        if key is None:
            return ""
        return str(self.art_root / f"{key}.png")

    def should_mirror(self, npc_name: Any, *, stage_side: str) -> bool:
        """Return whether an NPC's native gaze points off its current stage side."""
        key = self.get_art_key_for_npc(npc_name)
        direction = self.facing_map.get(key or "", "front")
        return direction == stage_side and direction in {"left", "right"}

    def clear_cache(self) -> None:
        self.available_keys = {path.stem for path in self.art_root.glob("*.png") if path.is_file()}


def get_npc_art_manager() -> NpcArtManager:
    """Return the shared runtime NPC art manager."""
    global _SHARED_NPC_ART_MANAGER
    if _SHARED_NPC_ART_MANAGER is None:
        _SHARED_NPC_ART_MANAGER = NpcArtManager()
    return _SHARED_NPC_ART_MANAGER
