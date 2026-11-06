"""Check that brief text contains only numbers that are in its Facts.

Every numeric token is pulled out of the text and compared with the Facts'
allowed numbers after normalising formatting, so "6:05", "6:05/km" and
"6:05 per km" are the same number, as are "26.1" and "26.10", or "05:00" and
"5:00". Anything else, including a rounded or invented value, is rejected.
Spelled-out numbers ("ten") are not detected.
"""

from __future__ import annotations

import re
from collections.abc import Iterable
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation

_NUMBER = re.compile(r"(?<![\d.])\d+(?::\d{2}){0,2}(?:\.\d+)?")

FORBIDDEN_WORDS = ("diagnose", "diagnosis", "safe", "guarantee", "guaranteed", "cure")
"""Words the brief must never use: it is training insight, not medical advice."""


def normalize(token: str) -> str:
    """Return a canonical form: no leading zero on a clock hour, no trailing decimal zeros."""
    if ":" in token:
        head, *rest = token.split(":")
        return ":".join([str(int(head)), *rest])
    try:
        value = Decimal(token)
    except InvalidOperation:
        return token
    text = format(value.normalize(), "f")
    return text


def extract_numbers(text: str) -> list[str]:
    """Return every numeric token in ``text``, normalised, in order of appearance."""
    return [normalize(m.group(0)) for m in _NUMBER.finditer(text)]


def allowed_from(values: Iterable[str]) -> frozenset[str]:
    """Build an allowed set from formatted Facts strings, with 24-hour forms of clock times."""
    allowed: set[str] = set()
    for value in values:
        pm = value.strip().upper().endswith("PM")
        am = value.strip().upper().endswith("AM")
        for token in extract_numbers(value):
            allowed.add(token)
            if (am or pm) and token.count(":") == 1:
                hour, minute = token.split(":")
                h24 = int(hour) % 12 + (12 if pm else 0)
                allowed.add(f"{h24}:{minute}")
    return frozenset(allowed)


@dataclass(frozen=True)
class GroundingResult:
    """Outcome of a grounding check."""

    ok: bool
    unknown_numbers: tuple[str, ...]
    forbidden_words: tuple[str, ...]

    def reason(self) -> str:
        """Explain a rejection in one line."""
        parts = []
        if self.unknown_numbers:
            parts.append("numbers not in Facts: " + ", ".join(self.unknown_numbers))
        if self.forbidden_words:
            parts.append("forbidden words: " + ", ".join(self.forbidden_words))
        return "; ".join(parts) or "ok"


def ground_check(
    text: str, allowed: frozenset[str], *, forbidden: tuple[str, ...] = FORBIDDEN_WORDS
) -> GroundingResult:
    """Accept ``text`` only if every number is in ``allowed`` and no forbidden word appears."""
    unknown = tuple(dict.fromkeys(n for n in extract_numbers(text) if n not in allowed))
    words = set(re.findall(r"[a-z]+", text.lower()))
    bad = tuple(w for w in forbidden if w in words)
    return GroundingResult(ok=not unknown and not bad, unknown_numbers=unknown, forbidden_words=bad)
