"""Open-Meteo forecast and archive client (docs/SCIENCE.md section 7).

Requests the hourly variables the WBGT model and heat index need, in the
Asia/Manila time zone, with wind in m/s. Transient failures (HTTP 429, 5xx,
network errors and timeouts) are retried with exponential backoff. Responses
are cached on disk keyed by the request URL: forecasts for one hour, archive
data indefinitely. Weather data by Open-Meteo.com, CC BY 4.0.
"""

from __future__ import annotations

import json
import math
import time
import urllib.error
import urllib.parse
import urllib.request
from collections.abc import Callable
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from typing import Any, Literal
from zoneinfo import ZoneInfo

import numpy as np
from numpy.typing import NDArray

from blagden import __version__
from blagden.weather.cache import DiskCache

FORECAST_URL = "https://api.open-meteo.com/v1/forecast"
ARCHIVE_URL = "https://archive-api.open-meteo.com/v1/archive"
TIMEZONE = "Asia/Manila"
ATTRIBUTION = "Weather data by Open-Meteo.com (CC BY 4.0)"

HOURLY_VARIABLES = (
    "temperature_2m",
    "relative_humidity_2m",
    "dew_point_2m",
    "wind_speed_10m",
    "surface_pressure",
    "shortwave_radiation_instant",
    "direct_radiation_instant",
    "diffuse_radiation_instant",
    "cloud_cover",
    "precipitation",
)
"""Ten variables, so one request counts as one call under the free-tier weighting."""

WIND_HEIGHT_M = 10.0
FORECAST_TTL_S = 3600.0
"""Forecast cache lifetime, s. Blagden choice: models update a few times a day."""
FORECAST_MAX_DAYS = 16
ARCHIVE_LAG_DAYS = 7
"""Dates older than this use the archive; ERA5 lags real time by about 5 days."""

Source = Literal["forecast", "archive"]
Fetch = Callable[[str, float], bytes]
FloatArray = NDArray[np.float64]


class WeatherError(RuntimeError):
    """The weather service could not provide the requested data."""


@dataclass(frozen=True)
class HourlyWeather:
    """Hourly weather at one point. Missing values are NaN. Times are Asia/Manila."""

    time_local: tuple[datetime, ...]
    temperature_c: FloatArray
    rh_pct: FloatArray
    dew_point_c: FloatArray
    wind10_mps: FloatArray
    pressure_hpa: FloatArray
    ghi_wm2: FloatArray
    direct_wm2: FloatArray
    diffuse_wm2: FloatArray
    cloud_pct: FloatArray
    precipitation_mm: FloatArray
    latitude: float
    longitude: float
    elevation_m: float
    source: Source
    wind_height_m: float = WIND_HEIGHT_M

    def __len__(self) -> int:
        """Return the number of hours."""
        return len(self.time_local)


def choose_source(start: date, end: date, today: date) -> Source:
    """Use the archive for dates older than ``ARCHIVE_LAG_DAYS``, else the forecast API."""
    if end < start:
        raise ValueError("end date is before start date")
    if end > today + timedelta(days=FORECAST_MAX_DAYS - 1):
        raise WeatherError(f"forecasts reach at most {FORECAST_MAX_DAYS} days ahead")
    if end < today - timedelta(days=ARCHIVE_LAG_DAYS):
        return "archive"
    return "forecast"


def build_url(source: Source, lat_deg: float, lon_deg: float, start: date, end: date) -> str:
    """Build the request URL. Parameter order is fixed so the cache key is stable."""
    if not (-90.0 <= lat_deg <= 90.0 and -180.0 <= lon_deg <= 180.0):
        raise ValueError("latitude must be in -90..90 and longitude in -180..180")
    params = [
        ("latitude", f"{lat_deg:.4f}"),
        ("longitude", f"{lon_deg:.4f}"),
        ("start_date", start.isoformat()),
        ("end_date", end.isoformat()),
        ("hourly", ",".join(HOURLY_VARIABLES)),
        ("timezone", TIMEZONE),
        ("wind_speed_unit", "ms"),
        ("timeformat", "unixtime"),
    ]
    base = ARCHIVE_URL if source == "archive" else FORECAST_URL
    return f"{base}?{urllib.parse.urlencode(params)}"


def urllib_fetch(url: str, timeout_s: float) -> bytes:
    """Fetch ``url`` with the standard library."""
    req = urllib.request.Request(url, headers={"User-Agent": f"blagden/{__version__}"})
    with urllib.request.urlopen(req, timeout=timeout_s) as resp:  # fixed https URLs only
        body: bytes = resp.read()
    return body


def _is_transient(exc: Exception) -> bool:
    if isinstance(exc, urllib.error.HTTPError):
        return exc.code == 429 or exc.code >= 500
    return isinstance(exc, urllib.error.URLError | TimeoutError | ConnectionError)


def _reason(exc: urllib.error.HTTPError) -> str:
    try:
        data = json.loads(exc.read().decode("utf-8"))
        return str(data.get("reason", exc.reason))
    except (ValueError, OSError):
        return str(exc.reason)


def _array(values: Any, n: int, name: str) -> FloatArray:
    if not isinstance(values, list) or len(values) != n:
        raise WeatherError(f"response has no complete '{name}' series")
    return np.array([math.nan if v is None else float(v) for v in values], dtype=np.float64)


def parse_hourly(body: bytes, source: Source) -> HourlyWeather:
    """Parse an Open-Meteo response with ``timeformat=unixtime``."""
    try:
        data = json.loads(body.decode("utf-8"))
    except ValueError as exc:
        raise WeatherError("response is not JSON") from exc
    if data.get("error"):
        raise WeatherError(str(data.get("reason", "Open-Meteo returned an error")))
    hourly = data.get("hourly")
    if not isinstance(hourly, dict) or not isinstance(hourly.get("time"), list):
        raise WeatherError("response has no hourly data")
    if data.get("timezone") != TIMEZONE:
        raise WeatherError(f"response time zone is {data.get('timezone')!r}, not {TIMEZONE}")
    tz = ZoneInfo(TIMEZONE)
    times = tuple(datetime.fromtimestamp(int(t), tz) for t in hourly["time"])
    n = len(times)
    a = {name: _array(hourly.get(name), n, name) for name in HOURLY_VARIABLES}
    return HourlyWeather(
        time_local=times,
        temperature_c=a["temperature_2m"],
        rh_pct=a["relative_humidity_2m"],
        dew_point_c=a["dew_point_2m"],
        wind10_mps=a["wind_speed_10m"],
        pressure_hpa=a["surface_pressure"],
        ghi_wm2=a["shortwave_radiation_instant"],
        direct_wm2=a["direct_radiation_instant"],
        diffuse_wm2=a["diffuse_radiation_instant"],
        cloud_pct=a["cloud_cover"],
        precipitation_mm=a["precipitation"],
        latitude=float(data["latitude"]),
        longitude=float(data["longitude"]),
        elevation_m=float(data.get("elevation", math.nan)),
        source=source,
    )


class OpenMeteoClient:
    """Client for the forecast and archive APIs.

    ``fetch``, ``sleep`` and ``today`` are injectable so tests run on recorded
    responses and never make live calls.
    """

    def __init__(
        self,
        cache: DiskCache | None = None,
        *,
        fetch: Fetch = urllib_fetch,
        attempts: int = 4,
        backoff_s: float = 1.0,
        timeout_s: float = 20.0,
        sleep: Callable[[float], None] = time.sleep,
        today: Callable[[], date] | None = None,
    ) -> None:
        if attempts < 1:
            raise ValueError("attempts must be at least 1")
        self.cache = cache if cache is not None else DiskCache()
        self.fetch = fetch
        self.attempts = attempts
        self.backoff_s = backoff_s
        self.timeout_s = timeout_s
        self.sleep = sleep
        self.today = today or (lambda: datetime.now(ZoneInfo(TIMEZONE)).date())

    def get(self, url: str, ttl_s: float | None) -> bytes:
        """Return the body for ``url`` from the cache or the network, with retries."""
        cached = self.cache.get(url, ttl_s)
        if cached is not None:
            return cached
        for attempt in range(self.attempts):
            try:
                body = self.fetch(url, self.timeout_s)
            except Exception as exc:  # classified below
                if isinstance(exc, urllib.error.HTTPError) and not _is_transient(exc):
                    raise WeatherError(f"Open-Meteo refused the request: {_reason(exc)}") from exc
                if not _is_transient(exc):
                    raise
                if attempt == self.attempts - 1:
                    raise WeatherError(
                        f"Open-Meteo unavailable after {self.attempts} attempts: {exc}"
                    ) from exc
                self.sleep(self.backoff_s * 2**attempt)
                continue
            parse_hourly(body, "forecast" if FORECAST_URL in url else "archive")  # validate
            self.cache.put(url, body)
            return body
        raise AssertionError("unreachable")  # pragma: no cover

    def hourly(self, lat_deg: float, lon_deg: float, start: date, end: date) -> HourlyWeather:
        """Fetch hourly weather for whole local days ``start`` to ``end`` inclusive."""
        source = choose_source(start, end, self.today())
        url = build_url(source, lat_deg, lon_deg, start, end)
        body = self.get(url, None if source == "archive" else FORECAST_TTL_S)
        return parse_hourly(body, source)
