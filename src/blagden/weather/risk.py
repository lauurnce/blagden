"""WBGT risk labels from published sports-medicine guidance (docs/SCIENCE.md section 5, D-017).

Training insight, not a go or no-go decision. Bands are shown as published and
not shifted for local climate. Where a source gives a range like "18 to 23 C"
without saying which end is inclusive, Blagden puts each boundary in the higher
band, except that the top band starts above its stated value when the source
says "above" (a Blagden convention, recorded in SCIENCE.md section 5).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

Flag = Literal["white", "green", "yellow", "red", "black"]
RacinaisLevel = Literal["below moderate", "moderate", "high", "excessive"]

WBGT_MODEL_ERROR_C = 1.0
"""About 1 C: Liljegren 2008 "better than 1 degree C"; Lemke and Kjellstrom 2012 RMSE 0.95 C."""

FLAG_MEANINGS: dict[Flag, str] = {
    "white": "Generally safe; EHS can occur associated with individual factors",
    "green": "Risk low but still exists on the basis of risk factors",
    "yellow": "Risk increases as event progresses through the day",
    "red": "Everyone should be aware of injury potential; individuals at risk should not compete",
    "black": "Consider rescheduling or delaying the event until safer conditions prevail; "
    "if the event must take place, be on high alert",
}
"""1996 ACSM distance-running flags, as reproduced by Roberts 2010 and Bermon and Adami 2019."""

ACSM_2007_ROWS = (
    (10.0, "Generally safe; EHS can occur associated with individual factors"),
    (18.3, "Generally safe; EHS can occur"),
    (22.2, "Risk of EHS and other heat illness begins to rise; high-risk individuals should be "
     "monitored or not compete"),
    (25.6, "Risk for all competitors is increased"),
    (27.8, "Risk for unfit, nonacclimatized individuals is high"),
    (30.0, "Cancel level for EHS risk"),
)  # fmt: skip
"""ACSM 2007 Table 2, continuous activity and competition: upper bound of each row, C.
Above 30.0 C the cells could not be read (UNVERIFIED), so no text is given."""

RACINAIS_RH_PCT = (50.0, 75.0, 100.0)
RACINAIS_THRESHOLDS_C: dict[str, tuple[float, float, float]] = {
    "moderate": (24.0, 20.0, 18.0),
    "high": (28.0, 26.0, 24.0),
    "excessive": (33.0, 29.0, 28.0),
}
"""Racinais et al. 2015 Table 3, WBGT at 50, 75 and 100 percent relative humidity."""


@dataclass(frozen=True)
class RiskLabel:
    """Every published label for one WBGT value."""

    wbgt_c: float
    flag: Flag
    flag_meaning: str
    wa2020_band: str
    acsm2007_text: str | None
    racinais_level: RacinaisLevel
    racinais_thresholds_c: tuple[float, float, float]
    racinais_rh_clamped: bool
    model_error_c: float = WBGT_MODEL_ERROR_C


def flag_for(wbgt_c: float) -> Flag:
    """Return the race flag: white below 10, green, yellow from 18, red from 23, black above 28."""
    if wbgt_c < 10.0:
        return "white"
    if wbgt_c < 18.0:
        return "green"
    if wbgt_c < 23.0:
        return "yellow"
    if wbgt_c <= 28.0:
        return "red"
    return "black"


def wa2020_band(wbgt_c: float) -> str:
    """Return the World Athletics 2020 band name."""
    if wbgt_c < 21.0:
        return "Almost Safe"
    if wbgt_c < 25.0:
        return "Caution"
    if wbgt_c < 28.0:
        return "Warning"
    if wbgt_c <= 30.0:
        return "Severe Warning"
    return "Danger"


def acsm2007_text(wbgt_c: float) -> str | None:
    """Return the ACSM 2007 row text for WBGT rounded to 0.1 C, or None above 30.0 C."""
    value = round(wbgt_c, 1)
    for upper, text in ACSM_2007_ROWS:
        if value <= upper:
            return text
    return None


def racinais_thresholds(rh_pct: float) -> tuple[tuple[float, float, float], bool]:
    """Interpolate the moderate, high and excessive thresholds linearly in humidity.

    Humidity below 50 percent uses the 50 percent column and is reported as
    clamped, because the table gives no lower column.
    """
    clamped = rh_pct < RACINAIS_RH_PCT[0]
    rh = min(max(rh_pct, RACINAIS_RH_PCT[0]), RACINAIS_RH_PCT[-1])
    lo = 0 if rh <= RACINAIS_RH_PCT[1] else 1
    x0, x1 = RACINAIS_RH_PCT[lo], RACINAIS_RH_PCT[lo + 1]
    frac = (rh - x0) / (x1 - x0)
    out = []
    for key in ("moderate", "high", "excessive"):
        col = RACINAIS_THRESHOLDS_C[key]
        out.append(col[lo] + frac * (col[lo + 1] - col[lo]))
    return (out[0], out[1], out[2]), clamped


def racinais_level(
    wbgt_c: float, rh_pct: float
) -> tuple[RacinaisLevel, tuple[float, float, float], bool]:
    """Return the humidity-corrected risk level, the thresholds used and the clamp flag."""
    (mod, high, exc), clamped = racinais_thresholds(rh_pct)
    level: RacinaisLevel = "below moderate"
    if wbgt_c >= exc:
        level = "excessive"
    elif wbgt_c >= high:
        level = "high"
    elif wbgt_c >= mod:
        level = "moderate"
    return level, (mod, high, exc), clamped


def risk_label(wbgt_c: float, rh_pct: float) -> RiskLabel:
    """Label a WBGT value with every published scale Blagden shows."""
    flag = flag_for(wbgt_c)
    level, thresholds, clamped = racinais_level(wbgt_c, rh_pct)
    return RiskLabel(
        wbgt_c=wbgt_c,
        flag=flag,
        flag_meaning=FLAG_MEANINGS[flag],
        wa2020_band=wa2020_band(wbgt_c),
        acsm2007_text=acsm2007_text(wbgt_c),
        racinais_level=level,
        racinais_thresholds_c=thresholds,
        racinais_rh_clamped=clamped,
    )
