"""Solar position against the published NREL SPA example.

Reference: Reda I, Andreas A. Solar Position Algorithm for Solar Radiation
Applications. NREL/TP-560-34302, 2008. Example inputs and outputs as reproduced
in pvlib's tests/test_spa.py: 2003-10-17 12:30:30 at UTC-7, latitude 39.742476,
longitude -105.1786; topocentric elevation without refraction 39.872046 deg,
topocentric zenith with refraction (820 hPa, 11 C) 50.11162 deg, azimuth
194.340241 deg.

Tolerance: 0.01 deg, the precision the Astronomical Almanac states for its
low-precision formulas between 1950 and 2050. Our refraction is for a standard
sea-level atmosphere, not the example's 820 hPa and 11 C, which accounts for
most of the difference in the refracted zenith.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta, timezone

import pytest

from blagden.weather.solar import cos_zenith, sun_position

SPA_TIME = datetime(2003, 10, 17, 12, 30, 30, tzinfo=timezone(timedelta(hours=-7)))
SPA_LAT, SPA_LON = 39.742476, -105.1786
TOL_DEG = 0.01
MANILA = timezone(timedelta(hours=8))
QMC = (14.6517, 121.0493)


def test_geometric_zenith_matches_spa_example() -> None:
    p = sun_position(SPA_TIME, SPA_LAT, SPA_LON)
    geometric_zenith = p.zenith_deg + p.refraction_deg
    assert geometric_zenith == pytest.approx(90.0 - 39.872046, abs=TOL_DEG)


def test_refracted_zenith_matches_spa_example() -> None:
    assert sun_position(SPA_TIME, SPA_LAT, SPA_LON).zenith_deg == pytest.approx(
        50.11162, abs=TOL_DEG
    )


def test_azimuth_matches_spa_example() -> None:
    assert sun_position(SPA_TIME, SPA_LAT, SPA_LON).azimuth_deg == pytest.approx(
        194.340241, abs=TOL_DEG
    )


def test_same_instant_in_any_timezone() -> None:
    utc = SPA_TIME.astimezone(UTC)
    assert sun_position(utc, SPA_LAT, SPA_LON) == sun_position(SPA_TIME, SPA_LAT, SPA_LON)


def test_manila_night_and_noon() -> None:
    night = sun_position(datetime(2026, 11, 15, 3, 0, tzinfo=MANILA), *QMC)
    noon = sun_position(datetime(2026, 11, 15, 12, 0, tzinfo=MANILA), *QMC)
    assert night.elevation_deg < 0.0 and night.refraction_deg == 0.0
    assert noon.elevation_deg > 45.0 and 0.0 < noon.cos_zenith <= 1.0
    assert cos_zenith(datetime(2026, 11, 15, 12, 0, tzinfo=MANILA), *QMC) == noon.cos_zenith


def test_distance_is_near_one_au() -> None:
    assert 0.98 < sun_position(SPA_TIME, SPA_LAT, SPA_LON).distance_au < 1.02


@pytest.mark.parametrize(
    ("when", "lat", "lon"),
    [
        (datetime(2026, 1, 1), 0.0, 0.0),
        (datetime(1949, 12, 31, tzinfo=UTC), 0.0, 0.0),
        (datetime(2026, 1, 1, tzinfo=UTC), 91.0, 0.0),
        (datetime(2026, 1, 1, tzinfo=UTC), 0.0, 181.0),
    ],
)
def test_rejects_bad_input(when: datetime, lat: float, lon: float) -> None:
    with pytest.raises(ValueError):
        sun_position(when, lat, lon)
