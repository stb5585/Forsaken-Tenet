"""Portrait atlas loading and composition helpers for the Pygame UI."""

from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

import pygame

from src.paths import PYGAME_ASSETS_DIR

logger = logging.getLogger(__name__)

PORTRAIT_ROOT = PYGAME_ASSETS_DIR / "portraits"


@dataclass(frozen=True)
class PortraitFrame:
    """Atlas frame metadata for one race/gender portrait."""

    key: str
    race: str
    gender: str
    rect: pygame.Rect
    image_path: Path | None = None
    variant: int = 0


class PortraitManager:
    """Load base portrait atlas entries and compose optional overlay layers."""

    def __init__(
        self,
        portrait_root: Path | None = None,
        *,
        atlas_json: Path | None = None,
        atlas_image: Path | None = None,
        overlay_root: Path | None = None,
    ) -> None:
        self.portrait_root = Path(portrait_root or PORTRAIT_ROOT)
        self.base_root = self.portrait_root / "base"
        self.fallback_root = self.base_root / "fallback_individuals"
        self.overlay_root = Path(overlay_root or self.portrait_root / "overlays")
        self.atlas_json_path = Path(
            atlas_json
            or self._first_existing(
                self.portrait_root / "portrait_atlas_mapping.json",
                self.base_root / "base_portrait_atlas.json",
                self.portrait_root / "base_portrait_atlas.json",
            )
        )
        self.atlas_image_path = Path(atlas_image) if atlas_image else None
        self.atlas_image_paths: list[Path] = (
            [self.atlas_image_path] if self.atlas_image_path else []
        )
        self.sheet_image_paths: dict[str, Path] = {}
        self.sheet_variant_count = 0
        self.frames: dict[str, PortraitFrame] = {}
        self._atlas_surfaces: dict[Any, pygame.Surface] = {}
        self._base_cache: dict[tuple[str, str, int], pygame.Surface] = {}
        self._portrait_cache: dict[tuple[Any, ...], pygame.Surface] = {}
        self.missing_overlays: list[Path] = []
        self.load_atlas()

    @staticmethod
    def normalize_key(value: Any, default: str = "unknown") -> str:
        if hasattr(value, "name"):
            value = getattr(value, "name", default)
        text = str(value or default).strip().lower()
        normalized = "_".join("".join(ch if ch.isalnum() else " " for ch in text).split())
        return normalized or default

    @staticmethod
    def _first_existing(*paths: Path) -> Path:
        for path in paths:
            if path.exists():
                return path
        return paths[0]

    @staticmethod
    def _path_sort_key(path: Path) -> tuple[str, int, str]:
        match = re.search(r"_(\d+)$", path.stem)
        suffix = int(match.group(1)) if match else 0
        base = path.stem[: match.start()] if match else path.stem
        return base, suffix, path.name

    @classmethod
    def _discover_atlas_images(cls, primary_path: Path) -> list[Path]:
        """Return atlas images that reuse the primary atlas geometry."""
        candidates: list[Path] = []
        if primary_path.exists():
            candidates.append(primary_path)

        numbered = sorted(
            primary_path.parent.glob(f"{primary_path.stem}_*.png"),
            key=cls._path_sort_key,
        )
        for path in numbered:
            if path not in candidates:
                candidates.append(path)

        return candidates or [primary_path]

    def load_atlas(self) -> None:
        if not self.atlas_json_path.exists():
            logger.warning("Portrait atlas JSON missing: %s", self.atlas_json_path)
            return

        try:
            data = json.loads(self.atlas_json_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            logger.warning("Could not load portrait atlas JSON %s: %s", self.atlas_json_path, exc)
            return

        if data.get("sheets"):
            self._load_sheet_mapping(data)
            return

        image_name = str(data.get("image", "base_portrait_atlas.png"))
        if self.atlas_image_path is not None:
            self.atlas_image_paths = [self.atlas_image_path]
        else:
            self.atlas_image_paths = self._discover_atlas_images(
                self.atlas_json_path.parent / image_name
            )
            self.atlas_image_path = self.atlas_image_paths[0]
        for entry_key, entry in (data.get("entries") or {}).items():
            try:
                race = self.normalize_key(entry.get("race", entry_key.rsplit("_", 1)[0]))
                gender = self.normalize_key(entry.get("gender", entry_key.rsplit("_", 1)[-1]))
                rect = pygame.Rect(
                    int(entry["x"]), int(entry["y"]), int(entry["w"]), int(entry["h"])
                )
            except (KeyError, TypeError, ValueError) as exc:
                logger.warning("Skipping invalid portrait atlas entry %s: %s", entry_key, exc)
                continue
            key = self.entry_key(race, gender)
            self.frames[key] = PortraitFrame(key=key, race=race, gender=gender, rect=rect)

    def _load_sheet_mapping(self, data: dict[str, Any]) -> None:
        """Load per-race sheets where columns are portrait variants."""
        universal_frames = data.get("universal_frames") or {}
        max_variant = 0
        for race_name, sheet in (data.get("sheets") or {}).items():
            race = self.normalize_key(race_name, "human")
            image_path = self._resolve_sheet_image_path(race, str(sheet.get("image", "")))
            self.sheet_image_paths[race] = Path(self.atlas_image_path or image_path)
            frames = sheet.get("frames") if isinstance(sheet.get("frames"), dict) else None
            if frames is None and sheet.get("uses") == "universal_frames":
                frames = universal_frames
            if not isinstance(frames, dict):
                logger.warning("Skipping portrait sheet %s without frames", race_name)
                continue

            for frame_key, frame in frames.items():
                parsed = self._parse_sheet_frame_key(str(frame_key), race)
                if parsed is None:
                    logger.warning("Skipping invalid portrait sheet frame key %s", frame_key)
                    continue
                gender, variant_number = parsed
                try:
                    rect = pygame.Rect(
                        int(frame["x"]), int(frame["y"]), int(frame["w"]), int(frame["h"])
                    )
                except (KeyError, TypeError, ValueError) as exc:
                    logger.warning("Skipping invalid portrait sheet frame %s: %s", frame_key, exc)
                    continue

                max_variant = max(max_variant, variant_number)
                key = self.variant_entry_key(race, gender, variant_number - 1)
                portrait_frame = PortraitFrame(
                    key=key,
                    race=race,
                    gender=gender,
                    rect=rect,
                    image_path=self.sheet_image_paths[race],
                    variant=variant_number - 1,
                )
                self.frames[key] = portrait_frame
                if variant_number == 1:
                    self.frames[self.entry_key(race, gender)] = portrait_frame

        self.sheet_variant_count = max_variant
        if self.sheet_image_paths and self.atlas_image_path is None:
            self.atlas_image_paths = list(dict.fromkeys(self.sheet_image_paths.values()))
            self.atlas_image_path = self.atlas_image_paths[0] if self.atlas_image_paths else None

    def _resolve_sheet_image_path(self, race: str, image_name: str) -> Path:
        """Resolve mapping image names, accepting the current *_base_portraits convention."""
        base_dir = self.atlas_json_path.parent
        candidates: list[Path] = []
        if image_name:
            path = base_dir / image_name
            candidates.append(path)
            if image_name.endswith("_portraits.png") and not image_name.endswith(
                "_base_portraits.png"
            ):
                candidates.append(
                    base_dir / image_name.replace("_portraits.png", "_base_portraits.png")
                )
        candidates.extend(
            [
                base_dir / f"{race}_base_portraits.png",
                base_dir / f"{race}_portraits.png",
            ]
        )
        return self._first_existing(*candidates)

    @staticmethod
    def _parse_sheet_frame_key(frame_key: str, race: str) -> tuple[str, int] | None:
        key = PortraitManager.normalize_key(frame_key, "")
        race_prefix = f"{race}_"
        if key.startswith(race_prefix):
            key = key[len(race_prefix) :]
        match = re.fullmatch(r"(male|female)_(\d+)", key)
        if not match:
            return None
        variant_number = int(match.group(2))
        if variant_number < 1:
            return None
        return match.group(1), variant_number

    @staticmethod
    def entry_key(race: Any, gender: Any) -> str:
        return (
            f"{PortraitManager.normalize_key(race)}_{PortraitManager.normalize_key(gender, 'male')}"
        )

    @staticmethod
    def appearance_id(race: Any, gender: Any, variant: Any = None) -> str:
        """Return the canonical ID shared by face and dialogue appearance art."""
        variant_index = 0
        try:
            variant_index = int(variant or 0)
        except (TypeError, ValueError):
            variant_index = 0
        return f"{PortraitManager.entry_key(race, gender)}_{variant_index + 1}"

    @staticmethod
    def variant_entry_key(race: Any, gender: Any, variant: Any = None) -> str:
        """Return the legacy atlas name for a canonical appearance ID."""
        return PortraitManager.appearance_id(race, gender, variant)

    def cache_key(
        self,
        race: Any,
        gender: Any,
        class_name: Any = None,
        first_promotion: Any = None,
        second_promotion: Any = None,
        effects: Iterable[Any] | None = None,
        variant: Any = None,
    ) -> tuple[Any, ...]:
        return (
            self.normalize_key(race, "human"),
            self.normalize_key(gender, "male"),
            self.normalize_key(class_name, "") if class_name else "",
            self.normalize_key(first_promotion, "") if first_promotion else "",
            self.normalize_key(second_promotion, "") if second_promotion else "",
            tuple(self.normalize_key(effect, "") for effect in effects or ()),
            self.variant_index(variant),
        )

    def variant_count(self) -> int:
        if self.sheet_variant_count:
            return max(1, self.sheet_variant_count)
        return max(1, len(self.atlas_image_paths))

    def variant_index(self, variant: Any = None) -> int:
        if variant is None:
            return 0
        try:
            index = int(variant)
        except (TypeError, ValueError):
            index = 0
        return index % self.variant_count()

    def get_portrait(
        self,
        race: Any,
        gender: Any,
        class_name: Any = None,
        first_promotion: Any = None,
        second_promotion: Any = None,
        effects: Iterable[Any] | None = None,
        variant: Any = None,
    ) -> pygame.Surface:
        key = self.cache_key(
            race, gender, class_name, first_promotion, second_promotion, effects, variant=variant
        )
        cached = self._portrait_cache.get(key)
        if cached is not None:
            return cached

        portrait = self.base_portrait(key[0], key[1], variant=key[6]).copy()
        for overlay_path in self.overlay_paths(key[2], key[3], key[4], key[5]):
            overlay = self.load_overlay(overlay_path)
            if overlay is None:
                continue
            portrait.blit(overlay, (0, 0))

        self._portrait_cache[key] = portrait
        return portrait

    def base_portrait(self, race: Any, gender: Any, variant: Any = None) -> pygame.Surface:
        race_key = self.normalize_key(race, "human")
        gender_key = self.normalize_key(gender, "male")
        variant_key = self.variant_index(variant)
        cache_key = (race_key, gender_key, variant_key)
        cached = self._base_cache.get(cache_key)
        if cached is not None:
            return cached

        surface = self.atlas_portrait(race_key, gender_key, variant=variant_key)
        if surface is None:
            surface = self.fallback_portrait(race_key, gender_key)
        if surface is None:
            logger.warning("Portrait missing for race=%s gender=%s", race_key, gender_key)
            surface = self.placeholder_surface()

        self._base_cache[cache_key] = surface
        return surface

    def atlas_portrait(self, race: str, gender: str, variant: Any = None) -> pygame.Surface | None:
        variant_key = self.variant_index(variant)
        frame = self.frames.get(self.variant_entry_key(race, gender, variant_key))
        if frame is None:
            frame = self.frames.get(self.entry_key(race, gender))
        atlas = self.atlas_surface(variant_key, race=race if frame and frame.image_path else None)
        if frame is None or atlas is None:
            return None
        rect = self._frame_rect_for_atlas(frame.rect, atlas)
        try:
            return atlas.subsurface(rect).copy()
        except ValueError as exc:
            logger.warning("Portrait atlas frame out of bounds for %s: %s", frame.key, exc)
            return None

    def _frame_rect_for_atlas(self, rect: pygame.Rect, atlas: pygame.Surface) -> pygame.Rect:
        """Return a frame rect adjusted when atlas images are scaled variants."""
        atlas_width, atlas_height = atlas.get_size()
        max_right = max((frame.rect.right for frame in self.frames.values()), default=atlas_width)
        max_bottom = max(
            (frame.rect.bottom for frame in self.frames.values()), default=atlas_height
        )
        scale_x = atlas_width / max_right if max_right > atlas_width else 1.0
        scale_y = atlas_height / max_bottom if max_bottom > atlas_height else 1.0
        adjusted = pygame.Rect(
            int(round(rect.x * scale_x)),
            int(round(rect.y * scale_y)),
            max(1, int(round(rect.width * scale_x))),
            max(1, int(round(rect.height * scale_y))),
        )
        adjusted.width = min(adjusted.width, max(1, atlas_width - adjusted.x))
        adjusted.height = min(adjusted.height, max(1, atlas_height - adjusted.y))
        return adjusted

    def atlas_surface(
        self, variant: Any = None, *, race: str | None = None
    ) -> pygame.Surface | None:
        if race and race in self.sheet_image_paths:
            cache_key: Any = ("sheet", race)
            if cache_key in self._atlas_surfaces:
                return self._atlas_surfaces[cache_key]
            atlas_path = self.sheet_image_paths[race]
            if not atlas_path.exists():
                logger.warning("Portrait sheet image missing: %s", atlas_path)
                return None
            surface = self.load_image(atlas_path)
            if surface is not None:
                self._atlas_surfaces[cache_key] = surface
            return surface

        variant_key = self.variant_index(variant)
        if variant_key in self._atlas_surfaces:
            return self._atlas_surfaces[variant_key]
        try:
            atlas_path = self.atlas_image_paths[variant_key]
        except IndexError:
            return None
        if not atlas_path.exists():
            logger.warning("Portrait atlas image missing: %s", atlas_path)
            return None
        surface = self.load_image(atlas_path)
        if surface is not None:
            self._atlas_surfaces[variant_key] = surface
        return surface

    def fallback_portrait(self, race: str, gender: str) -> pygame.Surface | None:
        filename = f"{self.entry_key(race, gender)}.png"
        paths = (
            self.fallback_root / filename,
            self.portrait_root / filename,
            self.portrait_root / filename.replace("_", ""),
        )
        for path in paths:
            if path.exists():
                return self.load_image(path)
        return None

    def overlay_paths(
        self,
        class_name: str,
        first_promotion: str,
        second_promotion: str,
        effects: Iterable[str],
    ) -> list[Path]:
        paths: list[Path] = []
        if class_name:
            paths.append(self.overlay_root / "class" / f"{class_name}.png")
        if first_promotion:
            paths.append(self.overlay_root / "promotion" / f"{first_promotion}.png")
        if second_promotion:
            paths.append(self.overlay_root / "promotion" / f"{second_promotion}.png")
        for effect in effects:
            if effect:
                paths.append(self.overlay_root / "effects" / f"{effect}.png")
        return paths

    def load_overlay(self, path: Path) -> pygame.Surface | None:
        if not path.exists():
            self.missing_overlays.append(path)
            logger.debug("Portrait overlay missing: %s", path)
            return None
        return self.load_image(path)

    def load_image(self, path: Path) -> pygame.Surface | None:
        try:
            surface = pygame.image.load(str(path))
        except (pygame.error, OSError) as exc:
            logger.warning("Could not load portrait image %s: %s", path, exc)
            return None
        try:
            return surface.convert_alpha()
        except pygame.error:
            return surface.copy()

    def placeholder_surface(self, size: tuple[int, int] = (225, 400)) -> pygame.Surface:
        surface = pygame.Surface(size, pygame.SRCALPHA)
        surface.fill((28, 28, 34, 255))
        pygame.draw.rect(surface, (90, 90, 104), surface.get_rect(), 3)
        return surface

    def clear_cache(self) -> None:
        self._base_cache.clear()
        self._portrait_cache.clear()
