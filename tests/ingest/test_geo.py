import math

import numpy as np
import pytest

from blagden.ingest.geo import EARTH_MEAN_RADIUS_M, cumulative_distance_m, haversine_m


def test_one_degree_of_latitude_is_a_ninetieth_of_a_quarter_circle() -> None:
    d = haversine_m(np.array([0.0]), np.array([0.0]), np.array([1.0]), np.array([0.0]))
    assert d[0] == pytest.approx(EARTH_MEAN_RADIUS_M * math.pi / 180.0, rel=1e-12)


def test_zero_distance_for_same_point() -> None:
    p = np.array([0.001])
    assert haversine_m(p, p, p, p)[0] == 0.0


def test_cumulative_distance_skips_missing_positions_without_interpolating() -> None:
    lat = np.array([np.nan, 0.0, np.nan, 0.001, 0.002])
    lon = np.zeros(5)
    out = cumulative_distance_m(lat, lon)
    step = EARTH_MEAN_RADIUS_M * math.radians(0.001)
    assert math.isnan(out[0])
    assert out[1] == 0.0
    assert out[2] == 0.0  # carried, not interpolated
    assert out[3] == pytest.approx(step, rel=1e-9)
    assert out[4] == pytest.approx(2 * step, rel=1e-9)


def test_cumulative_distance_all_missing_is_nan() -> None:
    assert np.isnan(cumulative_distance_m(np.full(3, np.nan), np.full(3, np.nan))).all()
