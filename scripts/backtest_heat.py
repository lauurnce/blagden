"""Back-test the heat adjustment on past races.

Reads a CSV of past races, pulls each race day's weather from the Open-Meteo
historical archive (dates within the last week use the forecast API's past
data), computes WBGT for the runner's own time on course, and compares the
unadjusted prediction with the heat-adjusted one.

CSV columns (header required):
    date        race date, YYYY-MM-DD (Manila)
    place       a label; or "LAT LON" when no lat and lon columns are given
    distance    race distance in km
    predicted   the neutral-weather prediction, h:mm:ss or seconds
    actual      the actual finish time, h:mm:ss or seconds
Optional columns:
    lat, lon    venue coordinates in decimal degrees
    start       gun time, HH:MM Manila (default 05:00, a Blagden choice)
    rural       1 for rural wind exponents (default 0, urban)
    wbgt_base   WBGT of the race the prediction came from, C (default 10 C, flagged)

Usage:
    uv run python scripts/backtest_heat.py examples/backtest_synthetic.csv [--json]

Reports mean absolute error (minutes) and mean absolute percentage error for
both, and how often the actual time fell inside the predicted range.
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from dataclasses import asdict, dataclass
from datetime import date, datetime, time
from pathlib import Path
from zoneinfo import ZoneInfo

from blagden.predict.baseline import ManualBaseline, parse_time_s
from blagden.predict.heat import format_hms, predict_for_window
from blagden.weather.openmeteo import ATTRIBUTION, OpenMeteoClient
from blagden.weather.race_morning import race_morning

MANILA = ZoneInfo("Asia/Manila")
DEFAULT_START = time(5, 0)


@dataclass(frozen=True)
class RaceResult:
    """One back-tested race."""

    date: str
    place: str
    distance_km: float
    actual_s: float
    unadjusted_s: float
    adjusted_s: float
    lo_s: float
    hi_s: float
    wbgt_race_c: float
    level: str
    extrapolated: bool
    in_range: bool


def coordinates(row: dict[str, str]) -> tuple[float, float]:
    """Return (lat, lon) from lat and lon columns or a "LAT LON" place."""
    if row.get("lat") and row.get("lon"):
        return float(row["lat"]), float(row["lon"])
    try:
        lat, lon = (float(x) for x in row["place"].replace(",", " ").split())
    except ValueError as exc:
        raise ValueError(
            f"place {row['place']!r} needs lat and lon columns, or must be written as 'LAT LON'"
        ) from exc
    return lat, lon


def backtest_row(row: dict[str, str], client: OpenMeteoClient) -> RaceResult:
    """Back-test one CSV row."""
    day = date.fromisoformat(row["date"].strip())
    lat, lon = coordinates(row)
    distance = float(row["distance"])
    predicted = parse_time_s(row["predicted"])
    actual = parse_time_s(row["actual"])
    start_t = time.fromisoformat(row["start"]) if row.get("start") else DEFAULT_START
    start = datetime.combine(day, start_t, MANILA)
    urban = row.get("rural", "0").strip() not in ("1", "true", "yes")
    w_base = float(row["wbgt_base"]) if row.get("wbgt_base") else None
    rm = race_morning(lat, lon, day, 0, 23, urban=urban, client=client)
    hourly = [(h.time_local, h.wbgt_c) for h in rm.hours]
    baseline = ManualBaseline(distance, predicted).predict(distance)
    pred = predict_for_window(baseline, hourly, start, wbgt_base_c=w_base)
    return RaceResult(
        date=day.isoformat(),
        place=row["place"],
        distance_km=distance,
        actual_s=actual,
        unadjusted_s=predicted,
        adjusted_s=pred.time_s,
        lo_s=pred.lo_s,
        hi_s=pred.hi_s,
        wbgt_race_c=pred.wbgt_race_c,
        level=pred.level,
        extrapolated=pred.extrapolated,
        in_range=pred.lo_s <= actual <= pred.hi_s,
    )


def scores(results: list[RaceResult]) -> dict[str, float]:
    """Mean absolute error in minutes, MAPE in percent, and range coverage."""
    n = len(results)
    if n == 0:
        raise ValueError("no races to score")

    def mae(key: str) -> float:
        return sum(abs(getattr(r, key) - r.actual_s) for r in results) / n / 60.0

    def mape(key: str) -> float:
        return 100.0 * sum(abs(getattr(r, key) - r.actual_s) / r.actual_s for r in results) / n

    return {
        "races": float(n),
        "mae_unadjusted_min": mae("unadjusted_s"),
        "mae_adjusted_min": mae("adjusted_s"),
        "mape_unadjusted_pct": mape("unadjusted_s"),
        "mape_adjusted_pct": mape("adjusted_s"),
        "range_coverage_pct": 100.0 * sum(r.in_range for r in results) / n,
    }


def render(results: list[RaceResult], s: dict[str, float]) -> str:
    """Plain-text report."""
    lines = [
        f"{'date':10}  {'place':26}  {'km':>6}  {'WBGT':>5}  {'actual':>8}  {'unadj':>8}  "
        f"{'adjusted':>8}  {'range':17}  in"
    ]
    for r in results:
        lines.append(
            f"{r.date:10}  {r.place[:26]:26}  {r.distance_km:6.2f}  {r.wbgt_race_c:5.1f}  "
            f"{format_hms(r.actual_s):>8}  {format_hms(r.unadjusted_s):>8}  "
            f"{format_hms(r.adjusted_s):>8}  {format_hms(r.lo_s)}-{format_hms(r.hi_s)}  "
            f"{'yes' if r.in_range else 'no'}"
        )
    lines += [
        "",
        f"races {int(s['races'])}",
        f"MAE   unadjusted {s['mae_unadjusted_min']:.2f} min, "
        f"adjusted {s['mae_adjusted_min']:.2f} min",
        f"MAPE  unadjusted {s['mape_unadjusted_pct']:.2f}%, adjusted {s['mape_adjusted_pct']:.2f}%",
        f"actual inside the predicted range: {s['range_coverage_pct']:.0f}%",
        ATTRIBUTION,
    ]
    return "\n".join(lines)


def main(argv: list[str] | None = None, client: OpenMeteoClient | None = None) -> int:
    """Run the back-test. ``client`` is injectable for offline tests."""
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("csv", type=Path, help="CSV of past races")
    parser.add_argument("--json", action="store_true", help="print JSON instead of text")
    args = parser.parse_args(argv)
    om = client or OpenMeteoClient()
    with args.csv.open(newline="", encoding="utf-8") as fh:
        rows = list(csv.DictReader(fh))
    missing = {"date", "place", "distance", "predicted", "actual"} - set(rows[0] if rows else {})
    if missing:
        print(f"error: CSV is missing columns: {', '.join(sorted(missing))}", file=sys.stderr)
        return 1
    results = [backtest_row(r, om) for r in rows]
    s = scores(results)
    if args.json:
        print(json.dumps({"races": [asdict(r) for r in results], "scores": s}, indent=2))
    else:
        print(render(results, s))
    return 0


if __name__ == "__main__":
    sys.exit(main())
