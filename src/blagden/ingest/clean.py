"""Turn raw records into a clean activity table and say exactly what was changed.

Rules (docs/SCIENCE.md section 8 and D-021):

- Rows without a usable time are dropped.
- Rows are sorted by time. Rows that share a timestamp are merged into one, taking the first
  present value of each field in file order; the extra rows are counted as dropped.
- Heart rates outside 30 to 230 bpm are removed (set to missing); the row is kept.
- Positions outside the WGS84 ranges and negative speeds are removed.
- Gaps between consecutive rows longer than the gap threshold are reported, never filled.
- Distance comes from the device when any row has it; otherwise it is computed from positions.
"""

from __future__ import annotations

from collections import Counter
from typing import Literal

import numpy as np

from blagden.ingest.geo import cumulative_distance_m
from blagden.ingest.table import (
    ActivityTable,
    CleaningReport,
    EmptyActivityError,
    FloatArray,
    Gap,
    RawActivity,
    RawRecord,
)

HR_VALID_RANGE_BPM = (30.0, 230.0)
GAP_THRESHOLD_S = 60.0


_VALUE_FIELDS = RawRecord._fields[1:]


def _merge(group: list[RawRecord]) -> RawRecord:
    """Merge rows that share a timestamp, keeping the first present value of each field."""
    values = {
        name: next((getattr(r, name) for r in group if getattr(r, name) is not None), None)
        for name in _VALUE_FIELDS
    }
    return group[0]._replace(**values)


def _array(values: list[float | None]) -> FloatArray:
    return np.array([np.nan if v is None else v for v in values], dtype=np.float64)


def clean(
    raw: RawActivity,
    *,
    hr_range_bpm: tuple[float, float] = HR_VALID_RANGE_BPM,
    gap_threshold_s: float = GAP_THRESHOLD_S,
) -> tuple[ActivityTable, CleaningReport]:
    """Clean raw records into an :class:`ActivityTable` and a :class:`CleaningReport`.

    Raises
    ------
    EmptyActivityError
        When no record has a usable time.
    """
    dropped: Counter[str] = Counter()
    removed: Counter[str] = Counter()

    timed = [(r.time_utc, r) for r in raw.records if r.time_utc is not None]
    if len(timed) < len(raw.records):
        dropped["missing_time"] = len(raw.records) - len(timed)
    if not timed:
        raise EmptyActivityError("no record has a usable time")

    times = [t for t, _ in timed]
    reordered = any(b < a for a, b in zip(times, times[1:], strict=False))
    ordered = [r for _, r in sorted(timed, key=lambda pair: pair[0])]

    merged: list[RawRecord] = []
    group: list[RawRecord] = []
    for rec in ordered:
        if group and rec.time_utc != group[0].time_utc:
            merged.append(_merge(group))
            group = []
        group.append(rec)
    merged.append(_merge(group))
    if len(merged) < len(ordered):
        dropped["duplicate_time"] = len(ordered) - len(merged)

    lo, hi = hr_range_bpm
    hr: list[float | None] = []
    lat: list[float | None] = []
    lon: list[float | None] = []
    speed: list[float | None] = []
    for rec in merged:
        h = rec.hr_bpm
        if h is not None and not lo <= h <= hi:
            removed["hr_out_of_range"] += 1
            h = None
        hr.append(h)
        la, lo_ = rec.lat_deg, rec.lon_deg
        if la is not None and lo_ is not None and not (-90 <= la <= 90 and -180 <= lo_ <= 180):
            removed["position_out_of_range"] += 1
            la = lo_ = None
        lat.append(la)
        lon.append(lo_)
        s = rec.speed_mps
        if s is not None and s < 0:
            removed["speed_negative"] += 1
            s = None
        speed.append(s)

    time_utc = tuple(r.time_utc for r in merged if r.time_utc is not None)
    t0 = time_utc[0]
    elapsed = np.array([(t - t0).total_seconds() for t in time_utc], dtype=np.float64)
    lat_a, lon_a = _array(lat), _array(lon)
    device_dist = _array([r.distance_m for r in merged])
    source: Literal["device", "computed", "none"]
    if np.isfinite(device_dist).any():
        distance, source = device_dist, "device"
    elif (np.isfinite(lat_a) & np.isfinite(lon_a)).any():
        distance, source = cumulative_distance_m(lat_a, lon_a), "computed"
    else:
        distance, source = device_dist, "none"

    steps = np.diff(elapsed)
    gaps = tuple(
        Gap(start_elapsed_s=float(elapsed[i]), duration_s=float(steps[i]))
        for i in np.flatnonzero(steps > gap_threshold_s)
    )
    hr_a = _array(hr)
    table = ActivityTable(
        time_utc=time_utc,
        elapsed_s=elapsed,
        hr_bpm=hr_a,
        lat_deg=lat_a,
        lon_deg=lon_a,
        alt_m=_array([r.alt_m for r in merged]),
        speed_mps=_array(speed),
        distance_m=distance,
        source_format=raw.source_format,
        distance_source=source,
        local_utc_offset_s=raw.local_utc_offset_s,
    )
    report = CleaningReport(
        rows_in=len(raw.records),
        rows_out=len(table),
        rows_dropped=dict(dropped),
        values_removed=dict(removed),
        hr_missing_rows=int(np.count_nonzero(~np.isfinite(hr_a))),
        reordered=reordered,
        gaps=gaps,
        notes=raw.notes,
    )
    return table, report
