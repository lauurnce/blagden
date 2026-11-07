"""Solar position from the Astronomical Almanac low-precision formulas (SCIENCE.md section 4).

This is a port of ``solarposition()`` (Nels Larson, PNNL, version 3.0, 1992) as
used by Liljegren's WBGT code (WBGT Version 1.1, Copyright 2008 UChicago Argonne,
LLC). It uses the low-precision formulas for the Sun's coordinates in the
Astronomical Almanac of 1990, which states a precision of 0.01 degree for
1950 to 2050. Refraction is computed for a standard sea-level atmosphere
(1013.25 hPa, 15 C) and, as Liljegren added to match Michalsky's program, is
added to the altitude. Diurnal parallax and aberration are ignored.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import UTC, datetime

_REFRACTION_PRESSURE_HPA = 1013.25
_REFRACTION_TEMP_C = 15.0
_BEGIN_MONTH = (0, 0, 31, 59, 90, 120, 151, 181, 212, 243, 273, 304, 334)


@dataclass(frozen=True)
class SunPosition:
    """Sun as seen from one place at one instant.

    ``elevation_deg`` includes the refraction correction; ``zenith_deg`` is
    90 minus that elevation and ``cos_zenith`` its cosine, as the WBGT model
    uses them. ``distance_au`` is the Earth-Sun distance in astronomical units.
    """

    elevation_deg: float
    refraction_deg: float
    zenith_deg: float
    cos_zenith: float
    azimuth_deg: float
    distance_au: float


def _day_number(year: int, month: int, day: int) -> int:
    leap = (year % 4 == 0 and year % 100 != 0) or year % 400 == 0
    return _BEGIN_MONTH[month] + day + (1 if leap and month > 2 else 0)


def _frac(x: float) -> float:
    """Return the fractional part with the sign of ``x``, like C ``modf``."""
    return math.modf(x)[0]


def sun_position(when: datetime, lat_deg: float, lon_deg: float) -> SunPosition:
    """Compute the Sun's position.

    Parameters
    ----------
    when
        A timezone-aware instant. It is converted to UTC.
    lat_deg, lon_deg
        Geodetic latitude (north positive) and longitude (east positive), degrees.

    Raises
    ------
    ValueError
        If ``when`` is naive, the year is outside 1950 to 2049 (the stated range
        of the formulas), or the coordinates are out of range.
    """
    if when.tzinfo is None or when.utcoffset() is None:
        raise ValueError("when must be timezone-aware")
    if not (-90.0 <= lat_deg <= 90.0 and -180.0 <= lon_deg <= 180.0):
        raise ValueError("latitude must be in -90..90 and longitude in -180..180")
    t = when.astimezone(UTC)
    if not 1950 <= t.year <= 2049:
        raise ValueError("the low-precision formulas cover 1950 to 2049")

    ut_hours = t.hour + t.minute / 60.0 + (t.second + t.microsecond / 1e6) / 3600.0
    day = t.day + ut_hours / 24.0
    delta_years = t.year - 2000
    delta_days = delta_years * 365 + int(delta_years / 4) + _day_number(t.year, t.month, t.day)
    if t.year > 2000:
        delta_days += 1
    days_j2000 = delta_days - 1.5
    cent_j2000 = days_j2000 / 36525.0
    ut = _frac(day)
    days_j2000 += ut
    ut *= 24.0

    # A. A. 1990, C24.
    mean_anomaly = _frac((357.528 + 0.9856003 * days_j2000) / 360.0) * 2.0 * math.pi
    mean_longitude = _frac((280.460 + 0.9856474 * days_j2000) / 360.0) * 2.0 * math.pi
    mean_obliquity = math.radians(23.439 - 4.0e-7 * days_j2000)
    ecliptic_long = (
        math.radians(1.915 * math.sin(mean_anomaly) + 0.020 * math.sin(2.0 * mean_anomaly))
        + mean_longitude
    )
    distance = 1.00014 - 0.01671 * math.cos(mean_anomaly) - 0.00014 * math.cos(2.0 * mean_anomaly)
    ap_ra = math.atan2(math.cos(mean_obliquity) * math.sin(ecliptic_long), math.cos(ecliptic_long))
    if ap_ra < 0.0:
        ap_ra += 2.0 * math.pi
    ap_ra_hours = _frac(ap_ra / (2.0 * math.pi)) * 24.0
    ap_dec = math.asin(math.sin(mean_obliquity) * math.sin(ecliptic_long))

    # A. A. 1990, B6-B7: local mean sidereal time.
    gmst0h = 24110.54841 + cent_j2000 * (
        8640184.812866 + cent_j2000 * (0.093104 - cent_j2000 * 6.2e-6)
    )
    gmst0h = _frac(gmst0h / 3600.0 / 24.0) * 24.0
    if gmst0h < 0.0:
        gmst0h += 24.0
    lmst = gmst0h + ut * 1.00273790934 + lon_deg / 15.0
    lmst = _frac(lmst / 24.0) * 24.0
    if lmst < 0.0:
        lmst += 24.0

    # A. A. 1990, B61-B62: hour angle, altitude, azimuth.
    local_ha = lmst - ap_ra_hours
    if local_ha < -12.0:
        local_ha += 24.0
    elif local_ha > 12.0:
        local_ha -= 24.0
    lat = math.radians(lat_deg)
    ha = local_ha / 24.0 * 2.0 * math.pi
    altitude = math.asin(
        math.sin(ap_dec) * math.sin(lat) + math.cos(ap_dec) * math.cos(ha) * math.cos(lat)
    )
    cos_alt = math.cos(altitude)
    tan_alt = math.tan(altitude) if abs(altitude) < 1.57079615 else 6.0e6
    cos_az = (
        math.sin(ap_dec) * math.cos(lat) - math.cos(ap_dec) * math.cos(ha) * math.sin(lat)
    ) / cos_alt
    sin_az = -(math.cos(ap_dec) * math.sin(ha) / cos_alt)
    azimuth = math.acos(max(-1.0, min(1.0, cos_az)))
    if math.atan2(sin_az, cos_az) < 0.0:
        azimuth = 2.0 * math.pi - azimuth
    alt_deg = math.degrees(altitude)

    # Refraction for altitudes of -1 degree or more; smooth crossover at 19.225 degrees.
    p, temp = _REFRACTION_PRESSURE_HPA, _REFRACTION_TEMP_C
    if alt_deg < -1.0 or tan_alt == 6.0e6:
        refraction = 0.0
    elif alt_deg < 19.225:
        refraction = (0.1594 + alt_deg * (0.0196 + 0.00002 * alt_deg)) * p
        refraction /= (1.0 + alt_deg * (0.505 + 0.0845 * alt_deg)) * (273.0 + temp)
    else:
        refraction = 0.00452 * (p / (273.0 + temp)) / tan_alt
    elevation = alt_deg + refraction
    zenith = 90.0 - elevation
    return SunPosition(
        elevation_deg=elevation,
        refraction_deg=refraction,
        zenith_deg=zenith,
        cos_zenith=math.cos(math.radians(zenith)),
        azimuth_deg=math.degrees(azimuth),
        distance_au=distance,
    )


def cos_zenith(when: datetime, lat_deg: float, lon_deg: float) -> float:
    """Return the cosine of the solar zenith angle, refraction included."""
    return sun_position(when, lat_deg, lon_deg).cos_zenith
