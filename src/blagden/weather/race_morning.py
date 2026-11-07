"""Hourly race-morning heat table: air, humidity, heat index, WBGT and risk.

Training insight, not a go or no-go decision. WBGT is shown with its model
error of about 1 C (SCIENCE.md section 4), and the heat index is labelled as
being on the PAGASA scale because it is computed here, not published by PAGASA.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import date, datetime

from blagden.weather.heat_index import heat_index_c, pagasa_category
from blagden.weather.openmeteo import ATTRIBUTION, HourlyWeather, OpenMeteoClient
from blagden.weather.risk import WBGT_MODEL_ERROR_C, risk_label
from blagden.weather.solar import sun_position
from blagden.weather.wbgt import outdoor_wbgt

SCALES_NOTE = (
    "The heat index assumes shade, rest and a light wind; WBGT counts the sun on a globe "
    "and the evaporation off a wick. On a sunny morning WBGT can sit in a higher band "
    "than the heat index suggests."
)


@dataclass(frozen=True)
class RaceHour:
    """One hour of the race window. Values are None when an input was missing."""

    time_local: datetime
    t_air_c: float | None
    rh_pct: float | None
    heat_index_c: float | None
    pagasa_category: str | None
    wbgt_c: float | None
    flag: str | None
    wa2020_band: str | None
    racinais_level: str | None
    wind2_mps: float | None
    ghi_wm2: float | None
    sun_elevation_deg: float
    flags: tuple[str, ...]


@dataclass(frozen=True)
class RaceMorning:
    """The table plus what a reader needs to interpret it."""

    latitude: float
    longitude: float
    day: date
    source: str
    urban: bool
    hours: tuple[RaceHour, ...]
    wbgt_model_error_c: float = WBGT_MODEL_ERROR_C
    attribution: str = ATTRIBUTION
    note: str = SCALES_NOTE


def _finite(*values: float) -> bool:
    return all(math.isfinite(v) for v in values)


def hour_row(w: HourlyWeather, i: int, lat: float, lon: float, *, urban: bool) -> RaceHour:
    """Compute one table row from hour ``i`` of ``w``."""
    t, rh = float(w.temperature_c[i]), float(w.rh_pct[i])
    sun = sun_position(w.time_local[i], lat, lon)
    flags: list[str] = []
    hi = cat = None
    if _finite(t, rh):
        hi = heat_index_c(t, rh)
        cat = pagasa_category(hi).name
    else:
        flags.append("missing_temperature_or_humidity")
    inputs = (
        t,
        rh,
        float(w.pressure_hpa[i]),
        float(w.wind10_mps[i]),
        float(w.ghi_wm2[i]),
        float(w.direct_wm2[i]),
        float(w.diffuse_wm2[i]),
    )
    wbgt = wind2 = None
    label = None
    if _finite(*inputs):
        r = outdoor_wbgt(
            t_air_c=t,
            rh_pct=rh,
            pressure_hpa=inputs[2],
            wind_mps=inputs[3],
            wind_height_m=w.wind_height_m,
            ghi_wm2=inputs[4],
            direct_wm2=inputs[5],
            diffuse_wm2=inputs[6],
            cos_zenith=sun.cos_zenith,
            distance_au=sun.distance_au,
            urban=urban,
        )
        flags.extend(r.flags)
        wbgt, wind2 = r.wbgt_c, r.wind2_mps
        if wbgt is not None:
            label = risk_label(wbgt, rh)
    else:
        flags.append("missing_wbgt_input")  # no approximate WBGT is ever substituted
    return RaceHour(
        time_local=w.time_local[i],
        t_air_c=t if math.isfinite(t) else None,
        rh_pct=rh if math.isfinite(rh) else None,
        heat_index_c=hi,
        pagasa_category=cat,
        wbgt_c=wbgt,
        flag=label.flag if label else None,
        wa2020_band=label.wa2020_band if label else None,
        racinais_level=label.racinais_level if label else None,
        wind2_mps=wind2,
        ghi_wm2=inputs[4] if math.isfinite(inputs[4]) else None,
        sun_elevation_deg=sun.elevation_deg,
        flags=tuple(flags),
    )


def race_morning(
    lat: float,
    lon: float,
    day: date,
    start_hour: int,
    end_hour: int,
    *,
    urban: bool = True,
    client: OpenMeteoClient | None = None,
) -> RaceMorning:
    """Build the hourly heat table for ``start_hour`` to ``end_hour`` (inclusive), Manila time.

    ``urban`` selects the urban wind exponents (Metro Manila venues) or the rural
    set (for example Clark), SCIENCE.md section 4.
    """
    if not 0 <= start_hour <= end_hour <= 23:
        raise ValueError("hours must satisfy 0 <= start_hour <= end_hour <= 23")
    w = (client or OpenMeteoClient()).hourly(lat, lon, day, day)
    rows = tuple(
        hour_row(w, i, lat, lon, urban=urban)
        for i, t in enumerate(w.time_local)
        if t.date() == day and start_hour <= t.hour <= end_hour
    )
    return RaceMorning(
        latitude=lat, longitude=lon, day=day, source=w.source, urban=urban, hours=rows
    )


def _num(v: float | None, spec: str = ".1f") -> str:
    return "n/a" if v is None else format(v, spec)


def format_race_morning(rm: RaceMorning) -> str:
    """Render the table as plain text."""
    head = (
        f"Race morning {rm.day.isoformat()}, {rm.hours[0].time_local:%H:%M} to "
        f"{rm.hours[-1].time_local:%H:%M} Manila time ({rm.source})"
        if rm.hours
        else f"Race morning {rm.day.isoformat()}: no hours in the window"
    )
    lines = [
        head,
        f"{'hour':5}  {'air C':>5}  {'RH %':>4}  {'HI C':>4}  {'PAGASA':16}  "
        f"{'WBGT C':>6}  {'flag':6}  {'WA 2020':14}  {'humid-corrected':15}",
    ]
    for h in rm.hours:
        lines.append(
            f"{h.time_local:%H:%M}  {_num(h.t_air_c):>5}  {_num(h.rh_pct, '.0f'):>4}  "
            f"{_num(h.heat_index_c, '.0f'):>4}  {h.pagasa_category or 'n/a':16}  "
            f"{_num(h.wbgt_c):>6}  {h.flag or 'n/a':6}  {h.wa2020_band or 'n/a':14}  "
            f"{h.racinais_level or 'n/a':15}" + (f"  [{', '.join(h.flags)}]" if h.flags else "")
        )
    lines += [
        "",
        f"WBGT model error is about +/- {rm.wbgt_model_error_c:.0f} C; read a value near a "
        "band edge as near the edge.",
        rm.note,
        "Training insight, not a go or no-go decision.",
        rm.attribution,
    ]
    return "\n".join(line.rstrip() for line in lines)
