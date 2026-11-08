"""Command logic behind the CLI: each function returns plain results, no printing.

The CLI renders these as Rich tables, JSON, charts and Markdown reports.
Training insight, not medical advice.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, time, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

import numpy as np

from blagden.brief import BriefText, Facts, build_facts, write_brief
from blagden.brief.template import Lang
from blagden.ingest import read_activity, resample_minutes
from blagden.ingest.summary import ActivitySummary, summarize
from blagden.physio import CoreTempEstimate, StrainSummary, estimate_core_temp, summarize_strain
from blagden.physio.ectemp import DEFAULT_TC0_C, DEFAULT_V0_C2
from blagden.predict import (
    BaselinePrediction,
    HeatAdjustedPrediction,
    choose_baseline,
    predict_for_window,
)
from blagden.predict.baseline import parse_time_s
from blagden.weather.openmeteo import OpenMeteoClient
from blagden.weather.race_morning import RaceMorning, race_morning

MANILA = ZoneInfo("Asia/Manila")


def parse_clock(text: str) -> time:
    """Parse "5", "05", "5:30" or "05:30" as a time of day."""
    parts = text.strip().split(":")
    if len(parts) == 1:
        return time(int(parts[0]), 0)
    return time(int(parts[0]), int(parts[1]))


@dataclass(frozen=True)
class AnalyzeResult:
    """One run file: activity summary, strain summary and the per-minute series."""

    file: str
    activity: ActivitySummary
    strain: StrainSummary
    hr_bpm_per_min: np.ndarray
    estimate: CoreTempEstimate


def analyze_run(path: Path, *, tc0: float | None = None, hr0: float | None = None) -> AnalyzeResult:
    """Read a run file and estimate core temperature and PSI."""
    table, report = read_activity(path)
    minutes = resample_minutes(table)
    activity = summarize(table, report, minutes)
    strain = summarize_strain(minutes.hr_bpm, tc0=tc0, hr0=hr0)
    est = estimate_core_temp(
        minutes.hr_bpm,
        tc0=DEFAULT_TC0_C if tc0 is None else tc0,
        v0=DEFAULT_V0_C2 if tc0 is None else 0.0,
    )
    return AnalyzeResult(path.name, activity, strain, minutes.hr_bpm, est)


def forecast_window(
    lat: float, lon: float, day: date, start: time, end: time, *, urban: bool = True,
    client: OpenMeteoClient | None = None,
) -> RaceMorning:  # fmt: skip
    """Hourly weather table from ``start`` to ``end`` (whole hours, inclusive)."""
    if (end.hour, end.minute) < (start.hour, start.minute):
        raise ValueError("--to must not be before --from")
    last = end.hour if end.minute == 0 else min(end.hour + 1, 23)
    return race_morning(lat, lon, day, start.hour, last, urban=urban, client=client)


@dataclass(frozen=True)
class PredictResult:
    """A heat-adjusted prediction with the weather it used."""

    baseline: BaselinePrediction
    prediction: HeatAdjustedPrediction
    start_local: datetime
    finish_local: datetime
    weather: RaceMorning


def predict_race(
    *,
    distance_km: float,
    recent_time: str,
    recent_distance_km: float,
    race_date: date,
    lat: float,
    lon: float,
    start: time = time(5, 0),
    recent_wbgt_c: float | None = None,
    urban: bool = True,
    client: OpenMeteoClient | None = None,
) -> PredictResult:
    """Baseline from a recent race, heat-adjusted for the race-day forecast."""
    baseline = choose_baseline(
        distance_km, known_distance_km=recent_distance_km, known_time_s=parse_time_s(recent_time)
    )
    weather = race_morning(lat, lon, race_date, 0, 23, urban=urban, client=client)
    gun = datetime.combine(race_date, start, MANILA)
    hourly = [(h.time_local, h.wbgt_c) for h in weather.hours]
    pred = predict_for_window(baseline, hourly, gun, wbgt_base_c=recent_wbgt_c)
    return PredictResult(baseline, pred, gun, gun + timedelta(seconds=pred.time_s), weather)


@dataclass(frozen=True)
class BriefResult:
    """The brief with the prediction and Facts it was built from."""

    brief: BriefText
    facts: Facts
    predicted: PredictResult


def race_brief(lang: Lang = "en", **predict_args: object) -> BriefResult:
    """Forecast plus prediction, rendered as a race-morning brief."""
    p = predict_race(**predict_args)  # type: ignore[arg-type]
    facts = build_facts(p.weather, p.start_local, p.baseline.distance_km, p.prediction)
    return BriefResult(write_brief(facts, lang), facts, p)
