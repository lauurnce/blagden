"""Facts built from the recorded forecast and from hand-made weather tables."""

from __future__ import annotations

import dataclasses
import json
from datetime import date, datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

import pytest

from blagden.brief.facts import build_facts, clock
from blagden.predict import ManualBaseline, heat_adjust, predict_for_window
from blagden.weather.cache import DiskCache
from blagden.weather.openmeteo import OpenMeteoClient
from blagden.weather.race_morning import RaceHour, RaceMorning, race_morning

MANILA = ZoneInfo("Asia/Manila")
DATA = Path(__file__).resolve().parents[1] / "data" / "open_meteo"


def recorded_rm(tmp_path: Path) -> RaceMorning:
    body = json.dumps(json.loads((DATA / "forecast_qmc_2026-11-15.json").read_text())["response"])
    c = OpenMeteoClient(
        DiskCache(tmp_path), fetch=lambda u, t: body.encode(), today=lambda: date(2026, 11, 9)
    )
    return race_morning(14.6517, 121.0493, date(2026, 11, 15), 0, 23, client=c)


def table(wbgts: list[float], rh: float = 80.0, first_hour: int = 4) -> RaceMorning:
    t0 = datetime(2026, 11, 15, first_hour, 0, tzinfo=MANILA)
    hours = tuple(
        RaceHour(
            t0 + timedelta(hours=i),
            27.0,
            rh,
            30.0,
            "Caution",
            w,
            None,
            None,
            None,
            1.0,
            0.0,
            0.0,
            (),
        )
        for i, w in enumerate(wbgts)
    )
    return RaceMorning(14.65, 121.05, date(2026, 11, 15), "forecast", True, hours)


def test_from_recorded_forecast(tmp_path: Path) -> None:
    rm = recorded_rm(tmp_path)
    start = datetime(2026, 11, 15, 5, 0, tzinfo=MANILA)
    base = ManualBaseline(21.0975, 6950.0).predict(21.0975)
    pred = predict_for_window(base, [(h.time_local, h.wbgt_c) for h in rm.hours], start)
    f = build_facts(rm, start, 21.0975, pred)
    assert (f.start_time, f.start_wbgt, f.start_flag) == ("5:00 AM", "24.7", "red")
    assert (f.start_level, f.rise_level, f.rise_time) == ("moderate", "high", "6:30 AM")
    pace_s = pred.time_s / 21.0975
    assert f.pace_cap == f"{round(pace_s) // 60}:{round(pace_s) % 60:02d}"
    assert f.drink_km == str(int(90 * 60 / pace_s))  # 6:30 is 90 minutes after the start
    assert f.extrapolated and f.distance_km == "21.1"
    for value in ("5:00", "24.7", "6:30", f.pace_cap, f.finish, f.drink_km, f.hi_peak):
        assert value in f.allowed_numbers


def test_cool_morning_reports_when_23_is_reached() -> None:
    rm = table([21.0, 22.0, 23.5, 25.0])  # 4:00 to 7:00
    start = datetime(2026, 11, 15, 4, 30, tzinfo=MANILA)
    pred = heat_adjust(ManualBaseline(10.0, 3000.0).predict(10.0), 21.7)
    f = build_facts(rm, start, 10.0, pred)
    assert f.cool_threshold == "23" and f.cool_until is None  # finish near 5:22, still under 23
    long = heat_adjust(ManualBaseline(21.0975, 7800.0).predict(21.0975), 22.0)
    g = build_facts(rm, start, 21.0975, long)
    assert g.cool_until == "5:40 AM"  # 23.0 at 5:40, between 22.0 at 5:00 and 23.5 at 6:00
    assert "23" in g.allowed_numbers


def test_drink_from_start_when_already_high() -> None:
    rm = table([27.0, 27.5, 28.0], rh=85.0)
    start = datetime(2026, 11, 15, 4, 0, tzinfo=MANILA)
    pred = heat_adjust(ManualBaseline(10.0, 3600.0).predict(10.0), 27.2)
    f = build_facts(rm, start, 10.0, pred)
    assert f.start_level in ("high", "excessive") and f.drink_from_start and f.drink_km is None


def test_without_prediction_there_is_no_pace_or_drink() -> None:
    f = build_facts(table([28.5, 29.0, 30.0]), datetime(2026, 11, 15, 4, 0, tzinfo=MANILA), 42.195)
    assert f.pace_cap is None and f.finish is None and f.drink_km is None


def test_window_must_be_covered_and_complete() -> None:
    with pytest.raises(ValueError, match="cover"):
        build_facts(table([25.0, 26.0]), datetime(2026, 11, 15, 3, 0, tzinfo=MANILA), 10.0)
    rm = table([25.0, 26.0])
    broken = dataclasses.replace(
        rm, hours=(rm.hours[0], dataclasses.replace(rm.hours[1], wbgt_c=None))
    )
    with pytest.raises(ValueError, match="missing"):
        build_facts(broken, datetime(2026, 11, 15, 4, 0, tzinfo=MANILA), 10.0)


def test_clock_format() -> None:
    assert clock(datetime(2026, 1, 1, 0, 5, tzinfo=MANILA)) == "12:05 AM"
    assert clock(datetime(2026, 1, 1, 13, 0, tzinfo=MANILA)) == "1:00 PM"
