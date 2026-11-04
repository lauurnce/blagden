"""Distance between positions on a spherical Earth."""

from __future__ import annotations

import numpy as np

from blagden.ingest.table import FloatArray

# GRS80 mean radius R1 = (2a + b) / 3 (Moritz 2000), docs/SCIENCE.md section 8.
EARTH_MEAN_RADIUS_M = 6_371_008.7714


def haversine_m(
    lat1: FloatArray, lon1: FloatArray, lat2: FloatArray, lon2: FloatArray
) -> FloatArray:
    """Great-circle distance in metres between paired positions in decimal degrees."""
    p1, p2 = np.radians(lat1), np.radians(lat2)
    dp = p2 - p1
    dl = np.radians(lon2) - np.radians(lon1)
    a = np.sin(dp / 2) ** 2 + np.cos(p1) * np.cos(p2) * np.sin(dl / 2) ** 2
    out: FloatArray = 2 * EARTH_MEAN_RADIUS_M * np.arcsin(np.sqrt(np.clip(a, 0.0, 1.0)))
    return out


def cumulative_distance_m(lat_deg: FloatArray, lon_deg: FloatArray) -> FloatArray:
    """Cumulative path length in metres, adding a step only between two valid positions.

    Rows without a position get the distance reached so far, or NaN before the first valid
    position. Missing positions are never interpolated.
    """
    n = len(lat_deg)
    out = np.full(n, np.nan)
    valid = np.isfinite(lat_deg) & np.isfinite(lon_deg)
    idx = np.flatnonzero(valid)
    if idx.size == 0:
        return out
    steps = haversine_m(lat_deg[idx[:-1]], lon_deg[idx[:-1]], lat_deg[idx[1:]], lon_deg[idx[1:]])
    totals = np.concatenate(([0.0], np.cumsum(steps)))
    out[idx] = totals
    # carry the last known total forward over rows without a position
    last = np.maximum.accumulate(np.where(valid, np.arange(n), -1))
    has_prior = last >= 0
    out[has_prior] = out[last[has_prior]]
    return out
