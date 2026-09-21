"""Typed persistence failures exposed to save/load callers."""


class SaveValidationError(ValueError):
    """Raised when a save payload violates the current schema contract."""

    def __init__(self, path: str, message: str) -> None:
        self.path = path
        self.detail = message
        super().__init__(f"{path}: {message}")
