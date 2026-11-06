"""Facts: every number a race-morning brief may use, already formatted.

Built only from computed values: the race-morning weather table
(``blagden.weather.race_morning``) and the heat-adjusted prediction
(``blagden.predict.heat``). The template renderer reads only Facts, and the
grounding check rejects any text with a number that is not in
``Facts.allowed_numbers``. Training insight, not medical advice.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field, fields
from datetime import datetime, timedelta

from blagden.brief.grounding import allowed_from
from blagden.predict.heat import HeatAdjustedPrediction, format_hms
from blagden.weather.heat_index import pagasa_category
from blagden.weather.race_morning import RaceMorning
from blagden.weather.risk import flag_for, racinais_level

LEVEL_ORDER = ("below moderate", "moderate", "high", "excessive")
COOL_THRESHOLD_C = 23
"""Start of the red flag band, C (1996 ACSM flags, SCIENCE.md section 5). Below it the
brief uses the "cooler" wording."""
DRINK_LEVEL = "high"
"""Humidity-corrected level from which the brief reminds the runner to use every aid
station (Racinais 2015 "high"; the reminder wording is awaiting review, COPY_REVIEW.md)."""
ROUND_TIMES_TO_MIN = 5


def clock(t: datetime) -> str:
    """Format a time as 12-hour "6:30 AM"."""
    suffix = "AM" if t.hour < 12 else "PM"
    return f"{t.hour % 12 or 12}:{t.minute:02d} {suffix}"


def floor_minutes(t: datetime, step: int = ROUND_TIMES_TO_MIN) -> datetime:
    """Round a time down to the step, so warnings are early rather than late."""
    return t.replace(minute=t.minute - t.minute % step, second=0, microsecond=0)


@dataclass(frozen=True)
class Facts:
    """Every value a brief may state. Strings are exactly as they may appear."""

    start_time: str
    start_wbgt: str
    start_flag: str
    start_level: str
    rise_time: str | None
    rise_level: str | None
    cool_threshold: str | None
    cool_until: str | None
    drink_km: str | None
    drink_from_start: bool
    pace_cap: str | None
    finish: str | None
    finish_low: str | None
    finish_high: str | None
    hi_peak: str | None
    hi_category: str | None
    extrapolated: bool
    distance_km: str
    wbgt_by_hour: tuple[tuple[str, str, str], ...]
    allowed_numbers: frozenset[str] = field(default=frozenset())


def _interp(t: datetime, pts: list[tuple[datetime, float]]) -> float:
    for (t0, v0), (t1, v1) in zip(pts, pts[1:], strict=False):
        if t0 <= t <= t1:
            return v0 + (v1 - v0) * (t - t0).total_seconds() / (t1 - t0).total_seconds()
    raise ValueError("time outside the weather table")


def build_facts(
    rm: RaceMorning,
    start: datetime,
    distance_km: float,
    prediction: HeatAdjustedPrediction | None = None,
) -> Facts:
    """Collect the brief's numbers for a race starting at ``start``.

    The race window runs from the start to the predicted finish, or to the end
    of the table when there is no prediction. ``rm`` must cover the window
    with WBGT for every hour.
    """
    wbgt_pts = [(h.time_local, h.wbgt_c) for h in rm.hours]
    rh_pts = [(h.time_local, h.rh_pct) for h in rm.hours]
    if any(v is None for _, v in wbgt_pts + rh_pts):
        raise ValueError("WBGT or humidity is missing for an hour in the table")
    wbgt = [(t, float(v)) for t, v in wbgt_pts if v is not None]
    rh = [(t, float(v)) for t, v in rh_pts if v is not None]
    end = start + timedelta(seconds=prediction.time_s) if prediction else wbgt[-1][0]
    if start < wbgt[0][0] or end > wbgt[-1][0]:
        raise ValueError("the weather table does not cover the race window")

    minutes = int(math.floor((end - start).total_seconds() / 60.0))
    samples = []
    for m in range(minutes + 1):
        t = start + timedelta(minutes=m)
        w = _interp(t, wbgt)
        samples.append((t, w, racinais_level(w, _interp(t, rh))[0]))
    start_w, start_level = samples[0][1], samples[0][2]

    rise_time = rise_level = None
    for t, _, level in samples[1:]:
        if LEVEL_ORDER.index(level) > LEVEL_ORDER.index(start_level):
            rise_time, rise_level = floor_minutes(t), level
            break

    cool_threshold = cool_until = None
    if start_w < COOL_THRESHOLD_C:
        cool_threshold = str(COOL_THRESHOLD_C)
        for t, w, _ in samples:
            if w >= COOL_THRESHOLD_C:
                cool_until = clock(floor_minutes(t))
                break

    pace_cap = finish = finish_low = finish_high = None
    drink_km: str | None = None
    drink_from_start = False
    if prediction is not None:
        pace_s = prediction.time_s / distance_km
        whole = int(round(pace_s))
        pace_cap = f"{whole // 60}:{whole % 60:02d}"
        finish, finish_low, finish_high = (
            format_hms(prediction.time_s),
            format_hms(prediction.lo_s),
            format_hms(prediction.hi_s),
        )
        hot_at_start = LEVEL_ORDER.index(start_level) >= LEVEL_ORDER.index(DRINK_LEVEL)
        if hot_at_start:
            drink_from_start = True
        else:
            for t, _, level in samples:
                if LEVEL_ORDER.index(level) >= LEVEL_ORDER.index(DRINK_LEVEL):
                    km = int(math.floor((floor_minutes(t) - start).total_seconds() / pace_s))
                    if km <= 0:
                        drink_from_start = True
                    else:
                        drink_km = str(km)
                    break

    in_window = [
        h for h in rm.hours
        if h.heat_index_c is not None and start.replace(minute=0) <= h.time_local <= end
    ]  # fmt: skip
    hi_peak = hi_cat = None
    if in_window:
        peak = max(in_window, key=lambda h: h.heat_index_c or -math.inf)
        hi_value = float(peak.heat_index_c or 0.0)
        hi_peak = str(math.floor(hi_value + 0.5))
        hi_cat = pagasa_category(hi_value).name

    facts = Facts(
        start_time=clock(start),
        start_wbgt=f"{start_w:.1f}",
        start_flag=flag_for(start_w),
        start_level=start_level,
        rise_time=clock(rise_time) if rise_time else None,
        rise_level=rise_level,
        cool_threshold=cool_threshold,
        cool_until=cool_until,
        drink_km=drink_km,
        drink_from_start=drink_from_start,
        pace_cap=pace_cap,
        finish=finish,
        finish_low=finish_low,
        finish_high=finish_high,
        hi_peak=hi_peak,
        hi_category=hi_cat,
        extrapolated=bool(prediction and prediction.extrapolated),
        distance_km=f"{round(distance_km, 1):g}",
        wbgt_by_hour=tuple(
            (clock(h.time_local), f"{h.wbgt_c:.1f}", h.flag or "")
            for h in rm.hours
            if h.wbgt_c is not None and start.replace(minute=0) <= h.time_local <= end
        ),
    )
    return with_allowed(facts)


def with_allowed(facts: Facts) -> Facts:
    """Return ``facts`` with ``allowed_numbers`` computed from every string field."""
    values: list[str] = []
    for f in fields(facts):
        v = getattr(facts, f.name)
        if isinstance(v, str):
            values.append(v)
        elif f.name == "wbgt_by_hour":
            values.extend(x for row in v for x in row)
    return Facts(**{**{f.name: getattr(facts, f.name) for f in fields(facts)},
                    "allowed_numbers": allowed_from(values)})  # fmt: skip
