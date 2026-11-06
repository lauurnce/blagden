"""The grounding check: invented numbers are caught, reformatted ones accepted."""

from __future__ import annotations

import pytest

from blagden.brief.grounding import allowed_from, extract_numbers, ground_check, normalize

ALLOWED = allowed_from(["5:00 AM", "26.1", "6:05", "2:06:42", "2:03:05", "8", "6:30 AM", "23"])


@pytest.mark.parametrize(
    "text",
    [
        "Start is 5:00 AM at WBGT 26.1.",
        "Start 05:00, WBGT 26.10.",
        "Cap your pace at 6:05/km.",
        "Cap your pace at 6:05 per km.",
        "Pace 6:05min/km until 06:30.",
        "High risk by 6:30 (06:30).",
        "Drink after km 8, aim for 2:06:42 (2:03:05 at best).",
        "WBGT under 23 all morning.",
    ],
)
def test_accepts_reformatted_allowed_numbers(text: str) -> None:
    result = ground_check(text, ALLOWED)
    assert result.ok, result.reason()


@pytest.mark.parametrize(
    ("text", "unknown"),
    [
        ("Cap your pace at 6:10 per km.", "6:10"),
        ("WBGT 26 at the start.", "26"),  # rounding is a change
        ("Drink after km 10.", "10"),
        ("Expect about 2:05:00.", "2:05:00"),
        ("Your heart rate should stay under 175.", "175"),
        ("Start is 5:00 AM at WBGT 26.1 and 30.2 by 8:00.", "30.2"),
    ],
)
def test_catches_invented_numbers(text: str, unknown: str) -> None:
    result = ground_check(text, ALLOWED)
    assert not result.ok and unknown in result.unknown_numbers
    assert unknown in result.reason()


def test_pm_times_allow_24_hour_form() -> None:
    allowed = allowed_from(["6:30 PM"])
    assert ground_check("Back off by 18:30.", allowed).ok
    assert not ground_check("Back off by 6:31.", allowed).ok


def test_forbidden_words() -> None:
    result = ground_check("Conditions are safe at 5:00 AM.", ALLOWED)
    assert not result.ok and result.forbidden_words == ("safe",)
    assert ground_check("Stay safer by drinking.", ALLOWED).ok  # whole words only


def test_extraction_and_normalisation() -> None:
    assert extract_numbers("km 8, 26.10 C, 05:00, 6:05/km, 1.5x") == [
        "8",
        "26.1",
        "5:00",
        "6:05",
        "1.5",
    ]
    assert normalize("007") == "7" and normalize("2:06:42") == "2:06:42"
