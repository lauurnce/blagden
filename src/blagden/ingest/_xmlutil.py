"""Helpers shared by the GPX and TCX readers."""

from __future__ import annotations

import math
from datetime import UTC, datetime


def local_name(tag: object) -> str:
    """Return an element tag without its namespace, lower-cased."""
    text = tag if isinstance(tag, str) else ""
    return text.rsplit("}", 1)[-1].lower()


def to_float(text: str | None) -> float | None:
    """Parse a number, returning None for empty, malformed or non-finite text."""
    if text is None:
        return None
    try:
        value = float(text.strip())
    except ValueError:
        return None
    return value if math.isfinite(value) else None


def parse_time(text: str | None) -> tuple[datetime | None, int | None, bool]:
    """Parse an ISO 8601 time into UTC.

    Returns
    -------
    (time_utc, offset_s, naive)
        ``time_utc`` is timezone-aware UTC, or None when the text is missing or malformed.
        ``offset_s`` is the UTC offset written in the file, when it had one.
        ``naive`` is True when the file gave no zone; GPX defines times as UTC, so naive times
        are read as UTC and the caller records a note.
    """
    if not text:
        return None, None, False
    try:
        parsed = datetime.fromisoformat(text.strip())
    except ValueError:
        return None, None, False
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=UTC), None, True
    offset = parsed.utcoffset()
    offset_s = int(offset.total_seconds()) if offset is not None else None
    return parsed.astimezone(UTC), offset_s, False
