"""Text layout helpers that do not depend on a rendering library."""

from collections.abc import Callable


TextWidthMeasurer = Callable[[str], int]


def wrap_text_to_width(
    text: str,
    measure_width: TextWidthMeasurer,
    max_width: int,
) -> list[str]:
    """Wrap whitespace-separated text to a caller-provided pixel width.

    The caller owns font selection and measurement, so this behavior can be
    shared by Pygame and future platform-specific renderers.

    Args:
        text: Text to wrap.
        measure_width: Returns the rendered width of a candidate line.
        max_width: Maximum permitted rendered line width.

    Returns:
        Lines that preserve word order. An empty input produces one empty line.
    """
    if not text:
        return [""]

    lines: list[str] = []
    current = ""
    for word in text.split():
        candidate = f"{current} {word}".strip()
        if not current or measure_width(candidate) <= max_width:
            current = candidate
            continue

        lines.append(current)
        current = word

    if current:
        lines.append(current)
    return lines or [text]
