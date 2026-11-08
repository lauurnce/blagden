"""Open-Meteo client on recorded responses. No test makes a live call."""

from __future__ import annotations

import io
import json
import urllib.error
import urllib.parse
from datetime import date
from pathlib import Path

import numpy as np
import pytest

from blagden.weather.cache import DiskCache
from blagden.weather.openmeteo import (
    ARCHIVE_URL,
    FORECAST_TTL_S,
    FORECAST_URL,
    HOURLY_VARIABLES,
    OpenMeteoClient,
    WeatherError,
    build_url,
    choose_source,
    parse_hourly,
)

DATA = Path(__file__).resolve().parents[1] / "data" / "open_meteo"
QMC = (14.6517, 121.0493)
TODAY = date(2026, 11, 9)


def recorded(name: str) -> tuple[str, bytes]:
    rec = json.loads((DATA / name).read_text(encoding="utf-8"))
    return rec["url"], json.dumps(rec["response"]).encode("utf-8")


FORECAST = recorded("forecast_qmc_2026-11-15.json")
ARCHIVE = recorded("archive_qmc_2026-10-18.json")


class FakeNet:
    """Serves recorded bodies by URL, optionally failing first."""

    def __init__(self, bodies: dict[str, bytes], failures: list[Exception] | None = None):
        self.bodies = bodies
        self.failures = list(failures or [])
        self.calls: list[str] = []

    def __call__(self, url: str, timeout_s: float) -> bytes:
        self.calls.append(url)
        if self.failures:
            raise self.failures.pop(0)
        return self.bodies[url]


def http_error(code: int, reason: str = "") -> urllib.error.HTTPError:
    body = io.BytesIO(json.dumps({"error": True, "reason": reason}).encode())
    return urllib.error.HTTPError("u", code, "err", {}, body)  # type: ignore[arg-type]


def client(tmp_path: Path, net: FakeNet, sleeps: list[float] | None = None) -> OpenMeteoClient:
    return OpenMeteoClient(
        DiskCache(tmp_path),
        fetch=net,
        sleep=(sleeps.append if sleeps is not None else lambda s: None),
        today=lambda: TODAY,
    )


def test_request_has_spec_variables_timezone_and_units() -> None:
    url = build_url("forecast", *QMC, date(2026, 11, 15), date(2026, 11, 15))
    assert url == FORECAST[0]
    q = dict(urllib.parse.parse_qsl(urllib.parse.urlsplit(url).query))
    assert q["hourly"].split(",") == list(HOURLY_VARIABLES)
    assert q["timezone"] == "Asia/Manila" and q["wind_speed_unit"] == "ms"
    assert url.startswith(FORECAST_URL)
    assert build_url("archive", *QMC, date(2026, 10, 18), date(2026, 10, 18)) == ARCHIVE[0]
    assert ARCHIVE[0].startswith(ARCHIVE_URL)


def test_parse_forecast_gives_manila_times_and_si_units() -> None:
    w = parse_hourly(FORECAST[1], "forecast")
    assert len(w) == 24
    assert w.time_local[0].isoformat() == "2026-11-15T00:00:00+08:00"
    assert all(t.utcoffset().total_seconds() == 8 * 3600 for t in w.time_local)  # type: ignore[union-attr]
    assert np.all(np.isfinite(w.temperature_c)) and np.all((w.rh_pct >= 0) & (w.rh_pct <= 100))
    assert np.all(w.ghi_wm2[:5] == 0.0)  # before sunrise
    assert w.wind_height_m == 10.0 and w.source == "forecast"


def test_choose_source() -> None:
    assert choose_source(date(2026, 11, 15), date(2026, 11, 15), TODAY) == "forecast"
    assert choose_source(date(2026, 11, 5), date(2026, 11, 5), TODAY) == "forecast"
    assert choose_source(date(2026, 10, 18), date(2026, 10, 18), TODAY) == "archive"
    with pytest.raises(ValueError, match="16 days"):  # a request problem, not an outage
        choose_source(date(2026, 12, 1), date(2026, 12, 1), TODAY)
    with pytest.raises(ValueError):
        choose_source(date(2026, 11, 2), date(2026, 11, 1), TODAY)


def test_hourly_uses_recorded_forecast_then_cache(tmp_path: Path) -> None:
    net = FakeNet(dict([FORECAST]))
    c = client(tmp_path, net)
    first = c.hourly(*QMC, date(2026, 11, 15), date(2026, 11, 15))
    second = c.hourly(*QMC, date(2026, 11, 15), date(2026, 11, 15))
    assert net.calls == [FORECAST[0]]
    assert np.array_equal(first.temperature_c, second.temperature_c)


def test_forecast_cache_expires(tmp_path: Path) -> None:
    now = [0.0]
    net = FakeNet(dict([FORECAST]))
    c = OpenMeteoClient(DiskCache(tmp_path, lambda: now[0]), fetch=net, today=lambda: TODAY)
    c.hourly(*QMC, date(2026, 11, 15), date(2026, 11, 15))
    now[0] += FORECAST_TTL_S + 1
    c.hourly(*QMC, date(2026, 11, 15), date(2026, 11, 15))
    assert len(net.calls) == 2


def test_archive_is_cached_forever(tmp_path: Path) -> None:
    now = [0.0]
    net = FakeNet(dict([ARCHIVE]))
    c = OpenMeteoClient(DiskCache(tmp_path, lambda: now[0]), fetch=net, today=lambda: TODAY)
    w = c.hourly(*QMC, date(2026, 10, 18), date(2026, 10, 18))
    now[0] += 10**8
    c.hourly(*QMC, date(2026, 10, 18), date(2026, 10, 18))
    assert w.source == "archive" and len(net.calls) == 1


@pytest.mark.parametrize(
    "failure",
    [http_error(429), http_error(503), urllib.error.URLError("dns"), TimeoutError("slow")],
)
def test_transient_failures_are_retried_with_backoff(tmp_path: Path, failure: Exception) -> None:
    sleeps: list[float] = []
    net = FakeNet(dict([FORECAST]), [failure, failure])
    w = client(tmp_path, net, sleeps).hourly(*QMC, date(2026, 11, 15), date(2026, 11, 15))
    assert len(w) == 24 and len(net.calls) == 3
    assert sleeps == [1.0, 2.0]


def test_gives_up_after_all_attempts(tmp_path: Path) -> None:
    sleeps: list[float] = []
    net = FakeNet(dict([FORECAST]), [http_error(503)] * 4)
    with pytest.raises(WeatherError, match="after 4 attempts"):
        client(tmp_path, net, sleeps).hourly(*QMC, date(2026, 11, 15), date(2026, 11, 15))
    assert sleeps == [1.0, 2.0, 4.0]


def test_client_error_is_not_retried(tmp_path: Path) -> None:
    net = FakeNet(dict([FORECAST]), [http_error(400, "Latitude must be in range")])
    with pytest.raises(WeatherError, match="Latitude must be in range"):
        client(tmp_path, net).hourly(*QMC, date(2026, 11, 15), date(2026, 11, 15))
    assert len(net.calls) == 1


def test_bad_responses_are_rejected_and_not_cached(tmp_path: Path) -> None:
    for body in (b"not json", b'{"error": true, "reason": "bad"}', b'{"timezone": "Asia/Manila"}'):
        with pytest.raises(WeatherError):
            parse_hourly(body, "forecast")
    data = json.loads(FORECAST[1])
    data["hourly"]["temperature_2m"] = data["hourly"]["temperature_2m"][:-1]
    net = FakeNet({FORECAST[0]: json.dumps(data).encode()})
    with pytest.raises(WeatherError, match="temperature_2m"):
        client(tmp_path, net).hourly(*QMC, date(2026, 11, 15), date(2026, 11, 15))
    assert DiskCache(tmp_path).get(FORECAST[0], None) is None


def test_null_values_become_nan() -> None:
    data = json.loads(FORECAST[1])
    data["hourly"]["wind_speed_10m"][3] = None
    w = parse_hourly(json.dumps(data).encode(), "forecast")
    assert np.isnan(w.wind10_mps[3])
