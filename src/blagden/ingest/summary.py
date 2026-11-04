"""A short, position-free summary of one activity, for people and for the CLI.

The summary never contains coordinates, so it is safe to print or share.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from blagden.ingest.resample import MinuteSeries
from blagden.ingest.table import ActivityTable, CleaningReport


@dataclass(frozen=True)
class ActivitySummary:
    """Position-free facts about one activity. Missing values are None."""

    source_format: str
    duration_s: float
    distance_km: float | None
    distance_source: str
    hr_mean_bpm: float | None
    hr_max_bpm: float | None
    minutes: int
    missing_minutes: int
    rows: int
    rows_dropped: dict[str, int]
    values_removed: dict[str, int]
    gaps: int
    local_utc_offset_s: int | None


def summarize(
    table: ActivityTable, report: CleaningReport, minutes: MinuteSeries
) -> ActivitySummary:
    """Build the summary from a cleaned table, its report and its minute series."""
    hr = table.hr_bpm[np.isfinite(table.hr_bpm)]
    dist = table.distance_m[np.isfinite(table.distance_m)]
    return ActivitySummary(
        source_format=table.source_format,
        duration_s=table.duration_s,
        distance_km=float(dist.max()) / 1000.0 if dist.size else None,
        distance_source=table.distance_source,
        hr_mean_bpm=float(hr.mean()) if hr.size else None,
        hr_max_bpm=float(hr.max()) if hr.size else None,
        minutes=len(minutes),
        missing_minutes=minutes.missing_minutes,
        rows=len(table),
        rows_dropped=dict(report.rows_dropped),
        values_removed=dict(report.values_removed),
        gaps=len(report.gaps),
        local_utc_offset_s=table.local_utc_offset_s,
    )


def format_duration(seconds: float) -> str:
    """Format seconds as H:MM:SS."""
    total = int(round(seconds))
    return f"{total // 3600}:{total % 3600 // 60:02d}:{total % 60:02d}"
