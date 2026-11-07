"""race_morning on recorded Open-Meteo responses."""

from __future__ import annotations

import json
from datetime import date
from pathlib import Path

import pytest

from blagden.weather.cache import DiskCache
from blagden.weather.heat_index import heat_index_c, pagasa_category
from blagden.weather.openmeteo import OpenMeteoClient
from blagden.weather.race_morning import format_race_morning, race_morning
from blagden.weather.risk import flag_for

DATA = Path(__file__).resolve().parents[1] / "data" / "open_meteo"
QMC = (14.6517, 121.0493)


def offline_client(tmp_path: Path, name: str, edit=None) -> OpenMeteoClient:  # type: ignore[no-untyped-def]
    rec = json.loads((DATA / name).read_text(encoding="utf-8"))
    data = rec["response"]
    if edit:
        edit(data)
    body = json.dumps(data).encode()
    return OpenMeteoClient(
        DiskCache(tmp_path), fetch=lambda url, t: body, today=lambda: date(2026, 11, 9)
    )


def test_window_rows_and_labels(tmp_path: Path) -> None:
    c = offline_client(tmp_path, "forecast_qmc_2026-11-15.json")
    rm = race_morning(*QMC, date(2026, 11, 15), 4, 9, client=c)
    assert [h.time_local.hour for h in rm.hours] == [4, 5, 6, 7, 8, 9]
    assert rm.source == "forecast" and rm.urban
    for h in rm.hours:
        assert h.t_air_c is not None and h.rh_pct is not None and h.wbgt_c is not None
        assert h.heat_index_c == pytest.approx(heat_index_c(h.t_air_c, h.rh_pct))
        assert h.pagasa_category == pagasa_category(h.heat_index_c).name
        assert h.flag == flag_for(h.wbgt_c)
    night, day = rm.hours[0], rm.hours[-1]
    assert night.sun_elevation_deg < 0 < day.sun_elevation_deg
    assert day.wbgt_c > night.wbgt_c  # type: ignore[operator]


def test_archive_day_uses_archive(tmp_path: Path) -> None:
    c = offline_client(tmp_path, "archive_qmc_2026-10-18.json")
    rm = race_morning(*QMC, date(2026, 10, 18), 5, 7, client=c)
    assert rm.source == "archive" and len(rm.hours) == 3


def test_missing_input_gives_no_wbgt_rather_than_an_approximation(tmp_path: Path) -> None:
    def drop_radiation(data: dict) -> None:  # type: ignore[type-arg]
        data["hourly"]["shortwave_radiation_instant"][7] = None

    c = offline_client(tmp_path, "forecast_qmc_2026-11-15.json", drop_radiation)
    rm = race_morning(*QMC, date(2026, 11, 15), 7, 8, client=c)
    assert rm.hours[0].wbgt_c is None and rm.hours[0].flag is None
    assert "missing_wbgt_input" in rm.hours[0].flags
    assert rm.hours[0].heat_index_c is not None  # the heat index needs only air and humidity
    assert rm.hours[1].wbgt_c is not None


def test_rural_differs_only_through_wind(tmp_path: Path) -> None:
    c = offline_client(tmp_path, "forecast_qmc_2026-11-15.json")
    urban = race_morning(*QMC, date(2026, 11, 15), 4, 9, client=c)
    rural = race_morning(*QMC, date(2026, 11, 15), 4, 9, urban=False, client=c)
    assert [h.heat_index_c for h in urban.hours] == [h.heat_index_c for h in rural.hours]
    assert any(a.wind2_mps != b.wind2_mps for a, b in zip(urban.hours, rural.hours, strict=True))


@pytest.mark.parametrize(("start", "end"), [(9, 4), (-1, 5), (4, 24)])
def test_bad_window_is_rejected(tmp_path: Path, start: int, end: int) -> None:
    c = offline_client(tmp_path, "forecast_qmc_2026-11-15.json")
    with pytest.raises(ValueError):
        race_morning(*QMC, date(2026, 11, 15), start, end, client=c)


def test_text_carries_error_caveats_and_attribution(tmp_path: Path) -> None:
    c = offline_client(tmp_path, "forecast_qmc_2026-11-15.json")
    text = format_race_morning(race_morning(*QMC, date(2026, 11, 15), 4, 9, client=c))
    assert "04:00 to 09:00 Manila time" in text
    assert "+/- 1 C" in text and "not a go or no-go decision" in text
    assert "Weather data by Open-Meteo.com" in text
    assert all(line == line.rstrip() for line in text.splitlines())
