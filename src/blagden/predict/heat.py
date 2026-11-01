"""Heat adjustment of a baseline time with a range and flags (docs/SCIENCE.md section 6, D-015).

T_pred = T_base (1 + k_L max(0, W_race - W_base)). The range uses the slope
range for the runner's level, with the upper slope doubled for degrees above
25 C WBGT. Recreational runners in Manila heat are outside every source, so
predictions are flagged as extrapolated and the range widens rather than
pretending. Training insight, not a race plan.
"""

from __future__ import annotations

import math
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Literal

from blagden.predict.baseline import MARATHON_KM, BaselinePrediction, riegel_time_s

Level = Literal["elite", "nonelite"]
Driver = Literal["none", "heat", "baseline_uncertainty"]

K_PER_C: dict[Level, float] = {"elite": 0.0018, "nonelite": 0.0060}
"""Point slopes, fraction per C WBGT. Elite: least-squares slope of Ely 2007 top-men quartile
means; non-elite: 0.6 percent per C for well-trained runners (Mantzios 2022 restating Ely)."""

K_RANGE_PER_C: dict[Level, tuple[float, float]] = {
    "elite": (0.0010, 0.0030),
    "nonelite": (0.0040, 0.0080),
}
"""Slope ranges, fraction per C (SCIENCE.md section 6 table)."""

DOUBLING_ABOVE_C = 25.0
"""The upper slope doubles for WBGT above this, C (Blagden choice motivated by El Helou 2012)."""

DEFAULT_BASE_WBGT_C = 10.0
"""Baseline WBGT when the baseline race's weather is unknown, C (Blagden choice, flagged)."""

ELITE_MARATHON_S = 2.5 * 3600.0
"""Elite if the marathon-equivalent time is under 2:30:00 (D-015)."""

EXTRAPOLATION_WBGT_C = 25.0
"""Above this WBGT the prediction is beyond Ely 2007 (SCIENCE.md section 6)."""

EXTRAPOLATION_MARATHON_S = 3 * 3600.0 + 40 * 60.0
"""Non-elite marathon-equivalent above 3:40 is outside every WBGT source."""


@dataclass(frozen=True)
class HeatAdjustedPrediction:
    """A heat-adjusted time with its range, flags and the main driver in words."""

    time_s: float
    lo_s: float
    hi_s: float
    level: Level
    k_per_c: float
    wbgt_race_c: float
    wbgt_base_c: float
    delta_wbgt_c: float
    extrapolated: bool
    baseline_wbgt_defaulted: bool
    driver: Driver
    driver_text: str
    baseline: BaselinePrediction


def marathon_equivalent_s(baseline: BaselinePrediction) -> float:
    """Scale the baseline to 42.195 km with Riegel's formula."""
    return riegel_time_s(baseline.distance_km, baseline.time_s, MARATHON_KM)


def runner_level(baseline: BaselinePrediction) -> Level:
    """Elite if the marathon-equivalent time is under 2:30:00, else non-elite (D-015)."""
    return "elite" if marathon_equivalent_s(baseline) < ELITE_MARATHON_S else "nonelite"


def format_hms(seconds: float) -> str:
    """Format seconds as h:mm:ss."""
    s = int(round(seconds))
    return f"{s // 3600}:{s % 3600 // 60:02d}:{s % 60:02d}"


def _driver(
    base: BaselinePrediction, t_pred: float, delta: float, level: Level, k: float,
    w_race: float, w_base: float, defaulted: bool, extrapolated: bool,
) -> tuple[Driver, str]:  # fmt: skip
    if delta <= 0.0:
        return "none", (
            f"No heat adjustment: race WBGT {w_race:.1f} C is at or below the "
            f"{w_base:.1f} C baseline{' (assumed)' if defaulted else ''}."
        )
    heat_s = t_pred - base.time_s
    base_half = None if base.lo_s is None or base.hi_s is None else (base.hi_s - base.lo_s) / 2
    who = "elite" if level == "elite" else "non-elite"
    heat_text = (
        f"race WBGT {w_race:.1f} C is {delta:.1f} C above the {w_base:.1f} C baseline"
        f"{' (assumed)' if defaulted else ''}; at {100 * k:.2f}% per C for {who} "
        f"runners that adds {format_hms(heat_s)} ({100 * heat_s / base.time_s:.1f}%)."
    )
    tail = (
        " This is beyond the conditions in the studies, so the range is wide."
        if extrapolated
        else ""
    )
    if base_half is not None and base_half > heat_s:
        return "baseline_uncertainty", (
            f"Main driver: uncertainty in the baseline time (+/- {format_hms(base_half)}). "
            f"Heat is smaller: {heat_text}{tail}"
        )
    return "heat", f"Main driver: heat. The {heat_text}{tail}"


def heat_adjust(
    baseline: BaselinePrediction,
    wbgt_race_c: float,
    *,
    wbgt_base_c: float | None = None,
    level: Level | None = None,
) -> HeatAdjustedPrediction:
    """Apply the D-015 heat adjustment to a baseline prediction.

    ``wbgt_race_c`` is the WBGT averaged over the expected time on course
    (see ``window_wbgt``). ``wbgt_base_c`` is the WBGT of the race the baseline
    came from; when unknown, 10 C is used and flagged.
    """
    if not math.isfinite(wbgt_race_c):
        raise ValueError("race WBGT must be a finite number")
    defaulted = wbgt_base_c is None
    w_base = DEFAULT_BASE_WBGT_C if wbgt_base_c is None else wbgt_base_c
    lvl = level or runner_level(baseline)
    k = K_PER_C[lvl]
    k_lo, k_hi = K_RANGE_PER_C[lvl]
    delta = max(0.0, wbgt_race_c - w_base)
    # Split the heat above baseline into the part at or below 25 C and the part above it.
    above = max(0.0, wbgt_race_c - max(w_base, DOUBLING_ABOVE_C))
    below = delta - above
    t_base = baseline.time_s
    t_pred = t_base * (1.0 + k * delta)
    t_lo = (baseline.lo_s if baseline.lo_s is not None else t_base) * (1.0 + k_lo * delta)
    t_hi = (baseline.hi_s if baseline.hi_s is not None else t_base) * (
        1.0 + k_hi * below + 2.0 * k_hi * above
    )
    marathon_eq = marathon_equivalent_s(baseline)
    extrapolated = wbgt_race_c > EXTRAPOLATION_WBGT_C or (
        lvl == "nonelite" and marathon_eq > EXTRAPOLATION_MARATHON_S
    )
    driver, text = _driver(
        baseline, t_pred, delta, lvl, k, wbgt_race_c, w_base, defaulted, extrapolated
    )
    return HeatAdjustedPrediction(
        time_s=t_pred,
        lo_s=min(t_lo, t_pred),
        hi_s=max(t_hi, t_pred),
        level=lvl,
        k_per_c=k,
        wbgt_race_c=wbgt_race_c,
        wbgt_base_c=w_base,
        delta_wbgt_c=delta,
        extrapolated=extrapolated,
        baseline_wbgt_defaulted=defaulted,
        driver=driver,
        driver_text=text,
        baseline=baseline,
    )


def window_wbgt(
    hourly: Sequence[tuple[datetime, float | None]], start: datetime, duration_s: float
) -> float:
    """Average WBGT over ``[start, start + duration_s]``.

    Hourly values are joined by straight lines and the line is averaged over
    the window (a Blagden choice, SCIENCE.md section 6). Raises ValueError when
    the window is not fully covered by consecutive hours with values.
    """
    if duration_s <= 0:
        raise ValueError("duration must be positive")
    pts = sorted(hourly, key=lambda p: p[0])
    end = start + timedelta(seconds=duration_s)
    if not pts or start < pts[0][0] or end > pts[-1][0]:
        raise ValueError("the WBGT series does not cover the whole race window")
    total = 0.0
    for (t0, w0), (t1, w1) in zip(pts, pts[1:], strict=False):
        lo, hi = max(t0, start), min(t1, end)
        if hi <= lo:
            continue
        if w0 is None or w1 is None:
            raise ValueError("WBGT is missing for part of the race window")
        span = (t1 - t0).total_seconds()

        def at(
            t: datetime, t0: datetime = t0, w0: float = w0, w1: float = w1, span: float = span
        ) -> float:
            return w0 + (w1 - w0) * (t - t0).total_seconds() / span

        total += 0.5 * (at(lo) + at(hi)) * (hi - lo).total_seconds()
    return total / duration_s


def predict_for_window(
    baseline: BaselinePrediction,
    hourly: Sequence[tuple[datetime, float | None]],
    start: datetime,
    *,
    wbgt_base_c: float | None = None,
    level: Level | None = None,
) -> HeatAdjustedPrediction:
    """Heat-adjust with the WBGT averaged over the runner's own expected time on course.

    The window length depends on the adjusted time, so the two are solved
    together: start from the baseline time and repeat until the time changes
    by less than one second.
    """
    duration = baseline.time_s
    for _ in range(50):
        w = window_wbgt(hourly, start, duration)
        pred = heat_adjust(baseline, w, wbgt_base_c=wbgt_base_c, level=level)
        if abs(pred.time_s - duration) < 1.0:
            return pred
        duration = pred.time_s
    return pred
