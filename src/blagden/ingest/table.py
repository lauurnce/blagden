"""Shared types for activity ingest: raw records, the activity table and the cleaning report.

Units are in every field name. Times are timezone-aware and in UTC. Missing numbers are NaN.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Literal, NamedTuple

import numpy as np
import numpy.typing as npt

SourceFormat = Literal["fit", "gpx", "tcx"]
FloatArray = npt.NDArray[np.float64]


class IngestError(ValueError):
    """Base error for files Blagden cannot read."""


class UnsupportedFormatError(IngestError):
    """The file is not a FIT, GPX or TCX activity."""


class EmptyActivityError(IngestError):
    """The file has no usable time-stamped records."""


class NoHeartRateError(IngestError):
    """The file has no valid heart rate, so core temperature cannot be estimated."""


class RawRecord(NamedTuple):
    """One record as parsed from a file, before cleaning.

    ``time_utc`` is timezone-aware UTC or None when the record had no usable time.
    Every other field is None when absent in the file.
    """

    time_utc: datetime | None
    hr_bpm: float | None = None
    lat_deg: float | None = None
    lon_deg: float | None = None
    alt_m: float | None = None
    speed_mps: float | None = None
    distance_m: float | None = None


@dataclass(frozen=True)
class RawActivity:
    """Records and metadata returned by a format reader."""

    records: tuple[RawRecord, ...]
    source_format: SourceFormat
    local_utc_offset_s: int | None = None
    notes: tuple[str, ...] = ()


@dataclass(frozen=True)
class Gap:
    """A stretch with no record at all, longer than the gap threshold."""

    start_elapsed_s: float
    duration_s: float


@dataclass(frozen=True)
class CleaningReport:
    """What cleaning removed or changed, and why.

    ``rows_dropped`` counts whole rows removed, by reason. ``values_removed`` counts single values
    set to missing while the row was kept, by reason. Nothing is ever filled in.
    """

    rows_in: int
    rows_out: int
    rows_dropped: dict[str, int] = field(default_factory=dict)
    values_removed: dict[str, int] = field(default_factory=dict)
    reordered: bool = False
    gaps: tuple[Gap, ...] = ()
    notes: tuple[str, ...] = ()


@dataclass(frozen=True)
class ActivityTable:
    """One cleaned activity, one row per record, sorted by time with unique timestamps.

    Columns
    -------
    time_utc : tuple of timezone-aware datetimes in UTC
    elapsed_s : seconds since the first row
    hr_bpm : heart rate in beats per minute, NaN where missing or removed
    lat_deg, lon_deg : WGS84 decimal degrees, NaN where missing
    alt_m : altitude in metres, NaN where missing
    speed_mps : speed in metres per second as recorded by the device, NaN where missing
    distance_m : cumulative distance in metres; from the device, or computed from positions when
        ``distance_source`` is "computed"
    """

    time_utc: tuple[datetime, ...]
    elapsed_s: FloatArray
    hr_bpm: FloatArray
    lat_deg: FloatArray
    lon_deg: FloatArray
    alt_m: FloatArray
    speed_mps: FloatArray
    distance_m: FloatArray
    source_format: SourceFormat
    distance_source: Literal["device", "computed", "none"]
    local_utc_offset_s: int | None = None

    def __len__(self) -> int:
        """Return the number of rows."""
        return len(self.time_utc)

    @property
    def duration_s(self) -> float:
        """Seconds from the first to the last row."""
        return float(self.elapsed_s[-1]) if len(self) else 0.0
