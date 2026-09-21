"""Save-file persistence manager."""

import json
import os
from dataclasses import dataclass
from typing import TypedDict

from src.paths import USER_SAVE_DIR, USER_TEMP_DIR

from .errors import SaveValidationError
from .models import (
    SAVE_SCHEMA_VERSION,
    SaveCompatibilityStatus,
    SaveLoadCode,
)
from .player import PlayerDataSerializer

PRE_FOUNDATION_SAVE_MESSAGE = (
    "This save predates save schema version 2 and is incompatible with the "
    "strict identity update. Start a new game."
)


@dataclass(frozen=True)
class SaveLoadResult:
    """Explicit save-load outcome for UI error reporting."""

    player: object | None
    error: str | None = None
    code: SaveLoadCode = SaveLoadCode.SUCCESS


class SaveFileMetadata(TypedDict):
    """Filesystem facts used to render and diagnose one save entry."""

    filename: object
    is_tmp: bool
    valid: bool
    expected_extension: str
    extension_matches_expected: bool
    path: str | None
    exists: bool
    is_file: bool
    is_dir: bool
    loadable: bool
    size: int | None
    empty: bool
    schema_version: int | None
    compatibility_status: SaveCompatibilityStatus
    status_message: str


class SaveManager:
    """High-level save/load management."""

    SAVE_DIR = str(USER_SAVE_DIR)
    TMP_DIR = str(USER_TEMP_DIR)
    last_load_result = SaveLoadResult(None, code=SaveLoadCode.NOT_FOUND)

    @staticmethod
    def _schema_status(data: object) -> tuple[SaveCompatibilityStatus, int | None, str]:
        """Return compatibility facts for a decoded save payload."""
        if not isinstance(data, dict):
            return (
                SaveCompatibilityStatus.UNREADABLE,
                None,
                "Save data is not a JSON object.",
            )
        raw_version = data.get("schema_version")
        if raw_version is None:
            return SaveCompatibilityStatus.PRE_FOUNDATION, None, PRE_FOUNDATION_SAVE_MESSAGE
        if isinstance(raw_version, bool) or not isinstance(raw_version, int):
            return (
                SaveCompatibilityStatus.UNSUPPORTED_VERSION,
                None,
                "Save schema version is invalid. Start a new game.",
            )
        if raw_version != SAVE_SCHEMA_VERSION:
            return (
                SaveCompatibilityStatus.UNSUPPORTED_VERSION,
                raw_version,
                f"Save schema version {raw_version} is unsupported; this build requires "
                f"version {SAVE_SCHEMA_VERSION}.",
            )
        return SaveCompatibilityStatus.COMPATIBLE, raw_version, "Ready to load."

    @staticmethod
    def is_valid_save_filename(filename: object) -> bool:
        """Return True when filename is safe to resolve inside save directories."""
        separators = {os.sep, os.altsep, "/", "\\"}
        return (
            isinstance(filename, str)
            and bool(filename.strip())
            and filename not in {".", ".."}
            and not os.path.isabs(filename)
            and not any(sep and sep in filename for sep in separators)
        )

    @staticmethod
    def _resolve_save_path(filename: str, is_tmp: bool = False) -> str:
        """Return a save path confined to the configured save directory."""
        if not SaveManager.is_valid_save_filename(filename):
            raise ValueError(f"Invalid save filename: {filename!r}")

        directory = SaveManager.TMP_DIR if is_tmp else SaveManager.SAVE_DIR
        return os.path.join(directory, filename)

    @staticmethod
    def ensure_dirs() -> None:
        """Ensure save directories exist."""
        for dir_path in [SaveManager.SAVE_DIR, SaveManager.TMP_DIR]:
            if not os.path.isdir(dir_path):
                os.makedirs(dir_path, exist_ok=True)

    @staticmethod
    def _write_json_atomic(filepath: str, data: dict[str, object]) -> None:
        """Replace one JSON file only after a complete, durable temporary write."""
        tmp_filepath = f"{filepath}.tmp"
        try:
            with open(tmp_filepath, "w", encoding="utf-8") as file_obj:
                json.dump(data, file_obj, indent=2)
                file_obj.flush()
                os.fsync(file_obj.fileno())
            os.replace(tmp_filepath, filepath)
        except (OSError, TypeError, ValueError):
            try:
                os.remove(tmp_filepath)
            except FileNotFoundError:
                pass
            raise

    @staticmethod
    def save_player(player: object, filename: str, is_tmp: bool = False) -> bool:
        """Save player to file."""
        SaveManager.ensure_dirs()

        try:
            filepath = SaveManager._resolve_save_path(filename, is_tmp=is_tmp)
            data = PlayerDataSerializer.serialize(player)
            SaveManager._write_json_atomic(filepath, data)
            return True
        except (OSError, TypeError, ValueError) as e:
            print(f"Error saving player: {e}")
            return False

    @staticmethod
    def load_player(
        filename: str,
        is_tmp: bool = False,
        skip_tiles: bool = False,
    ) -> object | None:
        """Load player from file.

        Args:
            filename: Name of save file
            is_tmp: Whether to load from tmp directory
            skip_tiles: If True, skip loading world tiles (for transform feature)
        """
        result = SaveManager.load_player_result(
            filename,
            is_tmp=is_tmp,
            skip_tiles=skip_tiles,
        )
        return result.player

    @staticmethod
    def load_player_result(
        filename: str,
        is_tmp: bool = False,
        skip_tiles: bool = False,
    ) -> SaveLoadResult:
        """Load one current-development save and retain a clear error outcome."""
        try:
            filepath = SaveManager._resolve_save_path(filename, is_tmp=is_tmp)

            if not os.path.isfile(filepath):
                result = SaveLoadResult(
                    None,
                    "Save file not found.",
                    SaveLoadCode.NOT_FOUND,
                )
                SaveManager.last_load_result = result
                return result

            with open(filepath, "r", encoding="utf-8") as file_obj:
                data = json.load(file_obj)
            status, _version, message = SaveManager._schema_status(data)
            if status is not SaveCompatibilityStatus.COMPATIBLE:
                result = SaveLoadResult(None, message, SaveLoadCode.INCOMPATIBLE_SCHEMA)
                SaveManager.last_load_result = result
                return result
            player = PlayerDataSerializer.deserialize(
                data,
                skip_tiles=skip_tiles,
            )
            result = SaveLoadResult(player, code=SaveLoadCode.SUCCESS)
            SaveManager.last_load_result = result
            return result
        except SaveValidationError as e:
            result = SaveLoadResult(None, f"Save data is invalid: {e}", SaveLoadCode.INVALID_DATA)
            SaveManager.last_load_result = result
            return result
        except (
            AttributeError,
            IndexError,
            KeyError,
            OSError,
            TypeError,
            ValueError,
        ) as e:
            print(f"Error loading player: {e}")
            code = (
                SaveLoadCode.INVALID_FILENAME
                if isinstance(e, ValueError) and not SaveManager.is_valid_save_filename(filename)
                else SaveLoadCode.UNREADABLE
            )
            result = SaveLoadResult(None, f"Unable to load save: {e}", code)
            SaveManager.last_load_result = result
            return result

    @staticmethod
    def list_saves() -> list[str]:
        """List all save files."""
        SaveManager.ensure_dirs()
        if not os.path.isdir(SaveManager.SAVE_DIR):
            return []
        saves = []
        for filename in os.listdir(SaveManager.SAVE_DIR):
            filepath = os.path.join(SaveManager.SAVE_DIR, filename)
            if filename.endswith(".save") and os.path.isfile(filepath):
                saves.append(filename)
        return sorted(saves)

    @staticmethod
    def describe_save_file(filename: object, is_tmp: bool = False) -> SaveFileMetadata:
        """Return filesystem and schema-compatibility metadata for one save entry."""
        metadata: SaveFileMetadata = {
            "filename": filename,
            "is_tmp": is_tmp,
            "valid": SaveManager.is_valid_save_filename(filename),
            "expected_extension": ".tmp" if is_tmp else ".save",
            "extension_matches_expected": False,
            "path": None,
            "exists": False,
            "is_file": False,
            "is_dir": False,
            "loadable": False,
            "size": None,
            "empty": False,
            "schema_version": None,
            "compatibility_status": SaveCompatibilityStatus.INVALID_NAME,
            "status_message": "Invalid save filename.",
        }
        if not metadata["valid"]:
            return metadata

        if not isinstance(filename, str):
            return metadata

        metadata["extension_matches_expected"] = filename.endswith(metadata["expected_extension"])
        filepath = SaveManager._resolve_save_path(filename, is_tmp=is_tmp)
        metadata["path"] = filepath
        metadata["exists"] = os.path.exists(filepath)
        metadata["is_file"] = os.path.isfile(filepath)
        metadata["is_dir"] = os.path.isdir(filepath)
        if not metadata["is_file"]:
            metadata["compatibility_status"] = SaveCompatibilityStatus.NOT_A_FILE
            metadata["status_message"] = "Save file not found."
        if metadata["is_file"]:
            try:
                metadata["size"] = os.path.getsize(filepath)
                metadata["empty"] = metadata["size"] == 0
            except OSError:
                metadata["size"] = None
                metadata["empty"] = False
            if metadata["empty"]:
                metadata["compatibility_status"] = SaveCompatibilityStatus.UNREADABLE
                metadata["status_message"] = "Save file is empty or corrupted."
            else:
                try:
                    with open(filepath, "r", encoding="utf-8") as file_obj:
                        payload = json.load(file_obj)
                    status, version, message = SaveManager._schema_status(payload)
                    metadata["compatibility_status"] = status
                    metadata["schema_version"] = version
                    metadata["status_message"] = message
                except (OSError, TypeError, ValueError, json.JSONDecodeError):
                    metadata["compatibility_status"] = SaveCompatibilityStatus.UNREADABLE
                    metadata["status_message"] = "Save file is unreadable or corrupted."
        metadata["loadable"] = (
            metadata["is_file"]
            and metadata["compatibility_status"] is SaveCompatibilityStatus.COMPATIBLE
        )
        return metadata

    @staticmethod
    def list_save_metadata() -> list[SaveFileMetadata]:
        """Return metadata for player-visible save files in load-menu order."""
        return [SaveManager.describe_save_file(filename) for filename in SaveManager.list_saves()]

    @staticmethod
    def summarize_save_metadata() -> dict[str, object]:
        """Return compact summary diagnostics for player-visible save files."""
        metadata = SaveManager.list_save_metadata()
        sizes = [entry["size"] for entry in metadata if entry["size"] is not None]
        largest = max(
            metadata,
            key=lambda entry: entry["size"] if entry["size"] is not None else -1,
            default=None,
        )
        return {
            "visible_count": len(metadata),
            "visible_filenames": [entry["filename"] for entry in metadata],
            "loadable_count": sum(1 for entry in metadata if entry["loadable"]),
            "total_size": sum(sizes),
            "empty_save_count": sum(1 for size in sizes if size == 0),
            "largest_save": None if largest is None else largest["filename"],
            "largest_size": None if largest is None else largest["size"],
        }

    @staticmethod
    def summarize_save_directory() -> dict[str, object]:
        """Return compact diagnostics for visible and hidden save-directory entries."""
        SaveManager.ensure_dirs()
        visible = set(SaveManager.list_saves())
        directory_entry_filenames: list[str] = []
        tmp_leftover_filenames: list[str] = []
        ignored_filenames: list[str] = []

        for filename in os.listdir(SaveManager.SAVE_DIR):
            filepath = os.path.join(SaveManager.SAVE_DIR, filename)
            if filename in visible:
                continue
            if filename.endswith(".tmp"):
                tmp_leftover_filenames.append(filename)
            elif filename.endswith(".save") and os.path.isdir(filepath):
                directory_entry_filenames.append(filename)
            else:
                ignored_filenames.append(filename)

        return {
            "visible_count": len(visible),
            "visible_filenames": sorted(visible),
            "tmp_leftover_count": len(tmp_leftover_filenames),
            "tmp_leftover_filenames": sorted(tmp_leftover_filenames),
            "directory_entry_count": len(directory_entry_filenames),
            "directory_entry_filenames": sorted(directory_entry_filenames),
            "ignored_entry_count": len(ignored_filenames),
            "ignored_filenames": sorted(ignored_filenames),
            "hidden_entry_count": (
                len(tmp_leftover_filenames)
                + len(directory_entry_filenames)
                + len(ignored_filenames)
            ),
        }

    @staticmethod
    def delete_save(filename: str, is_tmp: bool = False) -> bool:
        """Delete a save file."""
        try:
            filepath = SaveManager._resolve_save_path(filename, is_tmp=is_tmp)
            if os.path.isfile(filepath):
                os.remove(filepath)
                return True
        except (OSError, ValueError) as error:
            print(f"Error deleting save: {error}")
        return False
