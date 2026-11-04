"""One-minute heart-rate series for the core temperature filter (docs/SCIENCE.md section 8).

Minute ``i`` covers elapsed seconds [60 i, 60 (i + 1)) from the first row of the table. The
number of minutes is the duration rounded up to whole minutes (at least one); a final sample
that lands exactly on the end boundary is counted in the last minute. Each minute holds the
mean of its valid heart-rate samples. A minute with no valid sample is NaN and flagged, so the
filter runs its prediction step without an update. Heart rate is never interpolated or
otherwise invented (D-021).
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import datetime, timedelta

import numpy as np
import numpy.typing as npt

from blagden.ingest.table import ActivityTable, FloatArray

MINUTE_S = 60.0


@dataclass(frozen=True)
class MinuteSeries:
    """Heart rate per minute.

    Attributes
    ----------
    start_utc : timezone-aware UTC time of the first row; minute 0 starts here
    hr_bpm : mean heart rate of the minute in beats per minute, NaN when the minute has none
    n_samples : number of valid heart-rate samples averaged into each minute
    has_hr : True where the minute has at least one valid sample
    """

    start_utc: datetime
    hr_bpm: FloatArray
    n_samples: npt.NDArray[np.int64]
    has_hr: npt.NDArray[np.bool_]

    def __len__(self) -> int:
        """Return the number of minutes."""
        return len(self.hr_bpm)

    @property
    def missing_minutes(self) -> int:
        """Number of minutes without any valid heart rate."""
        return int(np.count_nonzero(~self.has_hr))

    def minute_start_utc(self, i: int) -> datetime:
        """Start time of minute ``i`` in UTC."""
        return self.start_utc + timedelta(seconds=MINUTE_S * i)


def resample_minutes(table: ActivityTable) -> MinuteSeries:
    """Average heart rate into one-minute bins without filling empty minutes."""
    n_min = max(1, math.ceil(table.duration_s / MINUTE_S))
    idx = np.minimum((table.elapsed_s // MINUTE_S).astype(np.int64), n_min - 1)
    valid = np.isfinite(table.hr_bpm)
    counts = np.bincount(idx[valid], minlength=n_min).astype(np.int64)
    sums = np.bincount(idx[valid], weights=table.hr_bpm[valid], minlength=n_min)
    has_hr = counts > 0
    hr = np.full(n_min, np.nan)
    hr[has_hr] = sums[has_hr] / counts[has_hr]
    return MinuteSeries(start_utc=table.time_utc[0], hr_bpm=hr, n_samples=counts, has_hr=has_hr)
