"""Heat index (NWS procedure) and PAGASA categories against docs/SCIENCE.md section 5."""

from __future__ import annotations

import math
from pathlib import Path

import pytest

from blagden.weather.heat_index import (
    PAGASA_CATEGORIES,
    c_to_f,
    f_to_c,
    heat_index_c,
    heat_index_f,
    pagasa_category,
)

SCIENCE_MD = Path(__file__).resolve().parents[2] / "docs" / "SCIENCE.md"


def rothfusz(t: float, rh: float) -> float:
    """The regression exactly as printed on the NWS page."""
    return (
        -42.379 + 2.04901523 * t + 10.14333127 * rh - 0.22475541 * t * rh
        - 0.00683783 * t * t - 0.05481717 * rh * rh + 0.00122874 * t * t * rh
        + 0.00085282 * t * rh * rh - 0.00000199 * t * t * rh * rh
    )  # fmt: skip


def test_categories_match_science_table() -> None:
    text = SCIENCE_MD.read_text(encoding="utf-8")
    body = text[text.index("### PAGASA heat index") : text.index("PAGASA's infographic notes")]
    rows = {}
    for line in body.splitlines():
        cells = [c.strip() for c in line.strip("|").split("|")]
        if line.startswith("| ") and len(cells) == 5 and cells[0] != "Category":
            rows[cells[0]] = cells
    assert [c.name for c in PAGASA_CATEGORIES] == list(rows)
    for cat in PAGASA_CATEGORIES:
        band = rows[cat.name][1]
        if cat.low_c is None:
            assert band == f"below {cat.high_c + 1}" if cat.high_c is not None else False
        elif cat.high_c is None:
            assert band == f"{cat.low_c} and above"
        else:
            assert band == f"{cat.low_c} to {cat.high_c}"
        assert (cat.colour or "") == rows[cat.name][2]
        if cat.effect:
            assert cat.effect in rows[cat.name][3]


def test_full_regression_above_80f() -> None:
    assert heat_index_f(90.0, 70.0) == pytest.approx(rothfusz(90.0, 70.0), abs=1e-12)


def test_simple_formula_when_average_below_80f() -> None:
    simple = 0.5 * (70.0 + 61.0 + 1.2 * (70.0 - 68.0) + 0.094 * 50.0)
    assert (simple + 70.0) / 2 < 80.0
    assert heat_index_f(70.0, 50.0) == pytest.approx(simple, abs=1e-12)


def test_low_humidity_adjustment() -> None:
    t, rh = 100.0, 10.0
    adj = (13.0 - rh) / 4.0 * math.sqrt((17.0 - abs(t - 95.0)) / 17.0)
    assert heat_index_f(t, rh) == pytest.approx(rothfusz(t, rh) - adj, abs=1e-12)


def test_high_humidity_adjustment() -> None:
    t, rh = 84.0, 90.0
    adj = (rh - 85.0) / 10.0 * (87.0 - t) / 5.0
    assert heat_index_f(t, rh) == pytest.approx(rothfusz(t, rh) + adj, abs=1e-12)


def test_celsius_wrapper_and_conversions() -> None:
    assert c_to_f(30.0) == 86.0 and f_to_c(86.0) == 30.0
    assert heat_index_c(30.0, 70.0) == pytest.approx(f_to_c(heat_index_f(86.0, 70.0)))


@pytest.mark.parametrize(
    ("hi_c", "name"),
    [
        (26.49, "Not hazardous"),
        (26.5, "Caution"),
        (32.49, "Caution"),
        (32.5, "Extreme Caution"),
        (41.49, "Extreme Caution"),
        (41.5, "Danger"),
        (51.49, "Danger"),
        (51.5, "Extreme Danger"),
        (60.0, "Extreme Danger"),
        (10.0, "Not hazardous"),
    ],
)
def test_category_boundaries_after_rounding(hi_c: float, name: str) -> None:
    assert pagasa_category(hi_c).name == name
