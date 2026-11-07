"""Heat index by the NWS Rothfusz procedure on the PAGASA scale (docs/SCIENCE.md section 5).

PAGASA states its heat index is "obtained by multiple regression analysis (from
Steadman's table) carried out by Rothfusz (1990)". The equation and procedure
are those of the US National Weather Service. The heat index assumes shade, a
person at rest and a light wind, so it is not WBGT; Blagden shows both. Values
computed here are labelled "heat index on the PAGASA scale" because they are not
PAGASA's own published numbers.
"""

from __future__ import annotations

import math
from dataclasses import dataclass


def c_to_f(t_c: float) -> float:
    """Convert C to F."""
    return t_c * 9.0 / 5.0 + 32.0


def f_to_c(t_f: float) -> float:
    """Convert F to C."""
    return (t_f - 32.0) * 5.0 / 9.0


def heat_index_f(t_f: float, rh_pct: float) -> float:
    """Heat index in F from air temperature in F and relative humidity in percent.

    NWS procedure: the simple formula is averaged with the temperature; if that
    average is 80 F or more, the Rothfusz regression with its low- and
    high-humidity adjustments is used instead.
    """
    simple = 0.5 * (t_f + 61.0 + 1.2 * (t_f - 68.0) + 0.094 * rh_pct)
    if (simple + t_f) / 2.0 < 80.0:
        return simple
    t, rh = t_f, rh_pct
    hi = (
        -42.379
        + 2.04901523 * t
        + 10.14333127 * rh
        - 0.22475541 * t * rh
        - 0.00683783 * t * t
        - 0.05481717 * rh * rh
        + 0.00122874 * t * t * rh
        + 0.00085282 * t * rh * rh
        - 0.00000199 * t * t * rh * rh
    )
    if rh < 13.0 and 80.0 <= t <= 112.0:
        hi -= (13.0 - rh) / 4.0 * math.sqrt((17.0 - abs(t - 95.0)) / 17.0)
    elif rh > 85.0 and 80.0 <= t <= 87.0:
        hi += (rh - 85.0) / 10.0 * (87.0 - t) / 5.0
    return hi


def heat_index_c(t_c: float, rh_pct: float) -> float:
    """Heat index in C from air temperature in C and relative humidity in percent."""
    return f_to_c(heat_index_f(c_to_f(t_c), rh_pct))


@dataclass(frozen=True)
class PagasaCategory:
    """One PAGASA heat index category (DOST-PAGASA, SCIENCE.md section 5)."""

    name: str
    low_c: int | None
    high_c: int | None
    colour: str | None
    effect: str | None


PAGASA_CATEGORIES = (
    PagasaCategory("Not hazardous", None, 26, None, None),
    PagasaCategory(
        "Caution",
        27,
        32,
        "yellow",
        "prolonged exposure and activity may result in fatigue. Continuing such activities "
        "could also lead to heat cramps.",
    ),
    PagasaCategory(
        "Extreme Caution",
        33,
        41,
        "yellow-orange",
        "heat cramps and heat exhaustion are possible, and ongoing activity could result in "
        "heat stroke.",
    ),
    PagasaCategory(
        "Danger",
        42,
        51,
        "red-orange",
        "heat cramps and heat exhaustion are likely, and heat stroke is probable with "
        "continued exposure",
    ),
    PagasaCategory("Extreme Danger", 52, None, "red", "heat stroke is imminent"),
)
"""Bands from panahon.gov.ph and iHeatMAP; colours and effects from DOST (2025)."""


def round_half_up(x: float) -> int:
    """Round to the nearest whole number, halves upward."""
    return math.floor(x + 0.5)


def pagasa_category(hi_c: float) -> PagasaCategory:
    """Classify a heat index in C.

    The PAGASA bands are whole degrees, so the value is rounded to the nearest
    whole degree first (a Blagden choice, SCIENCE.md section 5).
    """
    whole = round_half_up(hi_c)
    for cat in reversed(PAGASA_CATEGORIES):
        if cat.low_c is not None and whole >= cat.low_c:
            return cat
    return PAGASA_CATEGORIES[0]
