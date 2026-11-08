"""Command-line interface for Blagden.

Every command prints Rich tables by default and JSON with ``--json``. ``--out
DIR`` saves charts (PNG and SVG); ``--report`` also writes ``REPORT.md``.
Exit codes: 0 success, 1 bad input or unusable data, 2 usage error,
3 weather service unavailable. Training insight, not medical advice.
"""

from __future__ import annotations

import dataclasses
import json
import math
import sys
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import date, datetime, time
from pathlib import Path
from typing import Any

import numpy as np
import typer
from rich.console import Console
from rich.table import Table as RichTable

from blagden import __version__
from blagden.app import (
    AnalyzeResult,
    BriefResult,
    PredictResult,
    analyze_run,
    forecast_window,
    parse_clock,
    predict_race,
    race_brief,
)
from blagden.charts import ChartFiles, core_temp_chart, wbgt_chart
from blagden.ingest import IngestError, read_activity, resample_minutes
from blagden.ingest.summary import format_duration, summarize
from blagden.physio import LIMITATION_NOTE
from blagden.predict import format_hms
from blagden.report import md_chart, md_table, write_report
from blagden.weather import WeatherError
from blagden.weather.openmeteo import ATTRIBUTION
from blagden.weather.race_morning import SCALES_NOTE, RaceMorning

EXIT_INPUT = 1
EXIT_WEATHER = 3
DEFAULT_REPORT_DIR = Path("blagden-report")

app = typer.Typer(
    name="blagden",
    help="Heat intelligence for runners in the tropics. Training insight, not medical advice.",
    no_args_is_help=True,
    add_completion=False,
)
PIPE_WIDTH = 140
"""Table width when output is not a terminal (pipes, files, tests), so cells are not cut."""
out_console = Console(highlight=False, width=None if sys.stdout.isatty() else PIPE_WIDTH)
err_console = Console(stderr=True, highlight=False)

RUN_FILE_ARG = typer.Argument(..., exists=True, dir_okay=False, help="A .fit, .gpx or .tcx file.")
JSON_OPT = typer.Option(False, "--json", help="Print JSON instead of tables.")
OUT_OPT = typer.Option(None, "--out", help="Folder for charts (PNG and SVG).")
REPORT_OPT = typer.Option(
    False, "--report", help="Also write REPORT.md (default folder blagden-report)."
)


class Table(RichTable):
    """Rich table whose cells wrap instead of being cut."""

    def add_column(self, *args: Any, **kwargs: Any) -> None:
        """Add a column that folds long values."""
        kwargs.setdefault("overflow", "fold")
        super().add_column(*args, **kwargs)


def jsonable(value: Any) -> Any:
    """Convert results to JSON values: dataclasses, arrays, times, sets; NaN becomes null."""
    if dataclasses.is_dataclass(value) and not isinstance(value, type):
        return {f.name: jsonable(getattr(value, f.name)) for f in dataclasses.fields(value)}
    if isinstance(value, dict):
        return {str(k): jsonable(v) for k, v in value.items()}
    if isinstance(value, np.ndarray):
        return jsonable(value.tolist())
    if isinstance(value, (list, tuple)):
        return [jsonable(v) for v in value]
    if isinstance(value, (frozenset, set)):
        return sorted(jsonable(v) for v in value)
    if isinstance(value, (datetime, date, time)):
        return value.isoformat()
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, (np.floating, float)):
        return None if math.isnan(float(value)) else float(value)
    if isinstance(value, (np.integer,)):
        return int(value)
    if isinstance(value, np.bool_):
        return bool(value)
    return value


def emit_json(data: Any) -> None:
    """Print JSON on stdout."""
    sys.stdout.write(json.dumps(jsonable(data), indent=2, allow_nan=False) + "\n")


@contextmanager
def handled() -> Iterator[None]:
    """Turn expected failures into a clear message and an exit code."""
    try:
        yield
    except WeatherError as exc:
        err_console.print(f"error: weather data unavailable: {exc}")
        raise typer.Exit(code=EXIT_WEATHER) from exc
    except (IngestError, ValueError, FileNotFoundError) as exc:
        err_console.print(f"error: {exc}")
        raise typer.Exit(code=EXIT_INPUT) from exc


def output_dir(out: Path | None, report: bool) -> Path | None:
    """Where charts go: ``--out``, or the default report folder when only ``--report`` is set."""
    if out is not None:
        return out
    return DEFAULT_REPORT_DIR if report else None


def n(value: float | None, spec: str = ".1f", unit: str = "") -> str:
    """Format a number or n/a."""
    return "n/a" if value is None else f"{value:{spec}}{unit}"


@app.callback()
def main() -> None:
    """Blagden command-line tools."""


@app.command()
def version(as_json: bool = JSON_OPT) -> None:
    """Print the Blagden version."""
    if as_json:
        emit_json({"version": __version__})
    else:
        out_console.print(__version__)


# --- summary -----------------------------------------------------------------


@app.command()
def summary(
    files: list[Path] = typer.Argument(..., exists=True, dir_okay=False, help="Run files."),  # noqa: B008
    as_json: bool = JSON_OPT,
) -> None:
    """Summarise run files: duration, distance, heart rate and missing minutes. No coordinates."""
    results, failed = [], 0
    for path in files:
        try:
            t, rep = read_activity(path)
        except IngestError as exc:
            failed += 1
            err_console.print(f"{path.name}: error: {exc}")
            continue
        results.append((path.name, summarize(t, rep, resample_minutes(t))))
    if as_json:
        emit_json([{"file": name, **jsonable(s)} for name, s in results])
    else:
        table = Table(title="Run summary")
        for col in ("file", "format", "duration", "distance", "HR mean", "HR max", "minutes",
                    "missing HR", "gaps"):  # fmt: skip
            table.add_column(col)
        for name, s in results:
            dist = (
                "n/a" if s.distance_km is None else f"{s.distance_km:.2f} km ({s.distance_source})"
            )
            table.add_row(name, s.source_format, format_duration(s.duration_s), dist,
                          n(s.hr_mean_bpm, ".0f"), n(s.hr_max_bpm, ".0f"), str(s.minutes),
                          str(s.missing_minutes), str(s.gaps))  # fmt: skip
        out_console.print(table)
    if failed:
        raise typer.Exit(code=EXIT_INPUT)


# --- analyze -----------------------------------------------------------------


def analyze_table(r: AnalyzeResult) -> Table:
    """Activity and strain figures for one run."""
    a, s = r.activity, r.strain
    t = Table(title=f"{r.file} [{a.source_format}]", show_header=False)
    t.add_column("item")
    t.add_column("value")
    dist = "n/a" if a.distance_km is None else f"{a.distance_km:.2f} km ({a.distance_source})"
    rows = [
        ("duration", format_duration(a.duration_s)),
        ("distance", dist),
        ("heart rate", f"mean {n(a.hr_mean_bpm, '.0f')}, max {n(a.hr_max_bpm, '.0f')} bpm"),
        ("minutes", f"{a.minutes} (missing heart rate {a.missing_minutes})"),
        (
            "core temp start",
            f"{s.start_tc_c:.2f} C ({'measured' if s.start_measured else 'assumed'})",
        ),
        ("core temp peak", f"{s.peak_tc_c:.2f} C at {format_duration(60.0 * (s.peak_minute + 1))}"),
        (f"minutes > {s.threshold_c:.1f} C", str(s.minutes_above_threshold)),
        ("peak PSI", n(s.peak_psi) + (" (above the 0 to 10 scale)" if s.psi_above_scale else "")),
        (
            "resting HR for PSI",
            f"{s.hr0_bpm:.0f} bpm ({'default' if s.hr0_defaulted else 'given'})",
        ),
    ]
    for k, v in rows:
        t.add_row(k, v)
    return t


@app.command()
def analyze(
    run_file: Path = RUN_FILE_ARG,
    start_temp: float | None = typer.Option(None, help="Measured starting core temperature, C."),
    resting_hr: float | None = typer.Option(
        None, help="Resting heart rate for PSI, bpm (default 70)."
    ),
    as_json: bool = JSON_OPT,
    out: Path | None = OUT_OPT,
    report: bool = REPORT_OPT,
) -> None:
    """Core temperature, PSI and a summary for one run. No coordinates are printed."""
    with handled():
        r = analyze_run(run_file, tc0=start_temp, hr0=resting_hr)
    folder = output_dir(out, report)
    chart = None
    if folder is not None:
        chart = core_temp_chart(r.hr_bpm_per_min, r.estimate, folder,
                                title=f"Estimated core temperature: {r.file}")  # fmt: skip
    if report and folder is not None and chart is not None:
        a, s = r.activity, r.strain
        body = md_table(["item", "value"], [
            ["duration", format_duration(a.duration_s)],
            ["distance km", None if a.distance_km is None else f"{a.distance_km:.2f}"],
            ["heart rate mean / max bpm", f"{n(a.hr_mean_bpm, '.0f')} / {n(a.hr_max_bpm, '.0f')}"],
            ["core temp start / peak C", f"{s.start_tc_c:.2f} / {s.peak_tc_c:.2f}"],
            [f"minutes above {s.threshold_c:.1f} C", s.minutes_above_threshold],
            ["peak PSI", n(s.peak_psi)],
        ])  # fmt: skip
        write_report(folder, f"Run analysis: {r.file}", [
            ("Summary", body), ("Core temperature", md_chart(chart, folder, "core temperature")),
            ("Limitation", LIMITATION_NOTE),
        ])  # fmt: skip
    if as_json:
        emit_json({"file": r.file, "activity": r.activity, "strain": r.strain,
                   "charts": chart, "note": LIMITATION_NOTE})  # fmt: skip
        return
    out_console.print(analyze_table(r))
    out_console.print(f"Note: {LIMITATION_NOTE}")
    if chart:
        out_console.print(f"Chart: {chart.png} and {chart.svg}")


# --- forecast ----------------------------------------------------------------


def forecast_table(rm: RaceMorning) -> Table:
    """Hourly weather and labels."""
    t = Table(title=f"Race morning {rm.day.isoformat()} ({rm.source}), Manila time")
    for col in (
        "hour",
        "air C",
        "RH %",
        "heat index C",
        "PAGASA",
        "WBGT C",
        "flag",
        "WA 2020",
        "humid-corrected",
    ):
        t.add_column(col)
    for h in rm.hours:
        t.add_row(
            f"{h.time_local:%H:%M}",
            n(h.t_air_c),
            n(h.rh_pct, ".0f"),
            n(h.heat_index_c, ".0f"),
            h.pagasa_category or "n/a",
            n(h.wbgt_c),
            h.flag or "n/a",
            h.wa2020_band or "n/a",
            h.racinais_level or "n/a",
        )
    return t


def forecast_md(rm: RaceMorning) -> str:
    """Render the hourly table as Markdown."""
    return md_table(
        ["hour", "air C", "RH %", "heat index C", "PAGASA", "WBGT C", "flag", "humid-corrected"],
        [[f"{h.time_local:%H:%M}", n(h.t_air_c), n(h.rh_pct, ".0f"), n(h.heat_index_c, ".0f"),
          h.pagasa_category, n(h.wbgt_c), h.flag, h.racinais_level] for h in rm.hours],
    )  # fmt: skip


def weather_notes() -> str:
    """Return the caveats every forecast output carries."""
    return (f"WBGT model error is about +/- 1 C. {SCALES_NOTE} "
            f"Training insight, not a go or no-go decision. {ATTRIBUTION}")  # fmt: skip


@app.command()
def forecast(
    lat: float = typer.Option(..., help="Venue latitude, decimal degrees north."),
    lon: float = typer.Option(..., help="Venue longitude, decimal degrees east."),
    day: str = typer.Option(..., "--date", help="Race date, YYYY-MM-DD (Manila)."),
    start: str = typer.Option("04:00", "--from", help="First hour, HH:MM Manila."),
    end: str = typer.Option("09:00", "--to", help="Last hour, HH:MM Manila (inclusive)."),
    rural: bool = typer.Option(
        False, "--rural", help="Use rural wind exponents (for example Clark)."
    ),
    as_json: bool = JSON_OPT,
    out: Path | None = OUT_OPT,
    report: bool = REPORT_OPT,
) -> None:
    """Hourly heat index and WBGT with risk labels for a race window."""
    with handled():
        race_day = date.fromisoformat(day)
        t0, t1 = parse_clock(start), parse_clock(end)
        rm = forecast_window(lat, lon, race_day, t0, t1, urban=not rural)
    folder = output_dir(out, report)
    chart: ChartFiles | None = None
    if folder is not None and rm.hours:
        with handled():
            chart = wbgt_chart(rm, folder)
    if report and folder is not None:
        sections = [("Hourly forecast", forecast_md(rm))]
        if chart:
            sections.append(("WBGT", md_chart(chart, folder, "WBGT across the window")))
        sections.append(("Notes", weather_notes()))
        write_report(folder, f"Race morning forecast {rm.day.isoformat()}", sections)
    if as_json:
        emit_json({"forecast": rm, "charts": chart, "notes": weather_notes()})
        return
    out_console.print(forecast_table(rm))
    out_console.print(weather_notes())
    if chart:
        out_console.print(f"Chart: {chart.png} and {chart.svg}")


# --- predict -----------------------------------------------------------------


def predict_args(distance: float, recent_time: str, recent_distance: float, race_date: str,
                 lat: float, lon: float, start: str, recent_wbgt: float | None,
                 rural: bool) -> dict[str, Any]:  # fmt: skip
    """Build validated keyword arguments for ``predict_race``."""
    return {
        "distance_km": distance, "recent_time": recent_time, "recent_distance_km": recent_distance,
        "race_date": date.fromisoformat(race_date), "lat": lat, "lon": lon,
        "start": parse_clock(start), "recent_wbgt_c": recent_wbgt, "urban": not rural,
    }  # fmt: skip


def window_only(p: PredictResult) -> RaceMorning:
    """Keep the weather hours from an hour before the gun to an hour after the finish."""
    lo, hi = p.start_local.replace(minute=0), p.finish_local
    hours = tuple(
        h
        for h in p.weather.hours
        if lo.timestamp() - 3600 <= h.time_local.timestamp() <= hi.timestamp() + 3600
    )
    return dataclasses.replace(p.weather, hours=hours)


def prediction_rows(p: PredictResult) -> list[tuple[str, str]]:
    """Rows describing a prediction."""
    pr, b = p.prediction, p.baseline
    return [
        ("baseline", f"{format_hms(b.time_s)} ({b.source})"),
        ("heat-adjusted", format_hms(pr.time_s)),
        ("range", f"{format_hms(pr.lo_s)} to {format_hms(pr.hi_s)}"),
        ("race WBGT (time on course)", f"{pr.wbgt_race_c:.1f} C"),
        (
            "baseline WBGT",
            f"{pr.wbgt_base_c:.1f} C" + (" (assumed)" if pr.baseline_wbgt_defaulted else ""),
        ),
        ("level", pr.level),
        ("extrapolated", "yes" if pr.extrapolated else "no"),
        ("gun / predicted finish", f"{p.start_local:%H:%M} / {p.finish_local:%H:%M}"),
        ("main driver", pr.driver_text),
        *[("warning", w) for w in b.warnings],
    ]


def predict_json(p: PredictResult) -> dict[str, Any]:
    """JSON body for a prediction, with the WBGT hours on course."""
    w = window_only(p)
    return {
        "baseline": p.baseline,
        "prediction": {k: v for k, v in jsonable(p.prediction).items() if k != "baseline"},
        "start_local": p.start_local,
        "finish_local": p.finish_local,
        "wbgt_by_hour": [
            {"time_local": h.time_local, "wbgt_c": h.wbgt_c, "flag": h.flag} for h in w.hours
        ],  # fmt: skip
        "attribution": ATTRIBUTION,
    }


def window_chart(p: PredictResult, folder: Path) -> ChartFiles:
    """WBGT chart for the hours around the race."""
    return wbgt_chart(window_only(p), folder, start=p.start_local, end=p.finish_local)


@app.command()
def predict(
    distance: float = typer.Option(..., help="Race distance, km."),
    recent_time: str = typer.Option(..., help="A recent race time, h:mm:ss."),
    recent_distance: float = typer.Option(..., help="That race's distance, km."),
    race_date: str = typer.Option(..., help="Race date, YYYY-MM-DD (Manila)."),
    lat: float = typer.Option(..., help="Venue latitude."),
    lon: float = typer.Option(..., help="Venue longitude."),
    start: str = typer.Option("05:00", help="Gun time, HH:MM Manila."),
    recent_wbgt: float | None = typer.Option(
        None, help="WBGT of the recent race, C (default 10, flagged)."
    ),
    rural: bool = typer.Option(False, "--rural", help="Use rural wind exponents."),
    as_json: bool = JSON_OPT,
    out: Path | None = OUT_OPT,
    report: bool = REPORT_OPT,
) -> None:
    """Heat-adjusted finish time with a range, from a recent race and the race-day forecast."""
    with handled():
        p = predict_race(**predict_args(distance, recent_time, recent_distance, race_date, lat, lon,
                                        start, recent_wbgt, rural))  # fmt: skip
    folder = output_dir(out, report)
    chart = window_chart(p, folder) if folder is not None else None
    if report and folder is not None and chart is not None:
        write_report(folder, f"Heat-adjusted prediction, {p.start_local:%Y-%m-%d}", [
            ("Prediction", md_table(["item", "value"], [list(r) for r in prediction_rows(p)])),
            ("WBGT on course", md_chart(chart, folder, "WBGT across the race")),
            ("Notes", weather_notes()),
        ])  # fmt: skip
    if as_json:
        emit_json({**predict_json(p), "charts": chart})
        return
    t = Table(
        title=f"Prediction for {distance:g} km on {p.start_local:%Y-%m-%d}", show_header=False
    )
    t.add_column("item")
    t.add_column("value")
    for k, v in prediction_rows(p):
        t.add_row(k, v)
    out_console.print(t)
    out_console.print(weather_notes())
    if chart:
        out_console.print(f"Chart: {chart.png} and {chart.svg}")


# --- brief -------------------------------------------------------------------


@app.command()
def brief(
    distance: float = typer.Option(..., help="Race distance, km."),
    recent_time: str = typer.Option(..., help="A recent race time, h:mm:ss."),
    recent_distance: float = typer.Option(..., help="That race's distance, km."),
    race_date: str = typer.Option(..., help="Race date, YYYY-MM-DD (Manila)."),
    lat: float = typer.Option(..., help="Venue latitude."),
    lon: float = typer.Option(..., help="Venue longitude."),
    start: str = typer.Option("05:00", help="Gun time, HH:MM Manila."),
    recent_wbgt: float | None = typer.Option(None, help="WBGT of the recent race, C."),
    lang: str = typer.Option("en", help="en, or tl for Taglish."),
    rural: bool = typer.Option(False, "--rural", help="Use rural wind exponents."),
    as_json: bool = JSON_OPT,
    out: Path | None = OUT_OPT,
    report: bool = REPORT_OPT,
) -> None:
    """Race-morning brief from the forecast and a heat-adjusted prediction."""
    if lang not in ("en", "tl"):
        err_console.print("error: --lang must be en or tl")
        raise typer.Exit(code=EXIT_INPUT)
    with handled():
        r: BriefResult = race_brief(
            "tl" if lang == "tl" else "en",
            **predict_args(
                distance,
                recent_time,
                recent_distance,
                race_date,
                lat,
                lon,
                start,
                recent_wbgt,
                rural,
            ),
        )
    folder = output_dir(out, report)
    chart = window_chart(r.predicted, folder) if folder is not None else None
    if r.brief.rejected_reason:
        err_console.print(f"LLM wording rejected ({r.brief.rejected_reason}); template used")
    if report and folder is not None and chart is not None:
        write_report(folder, f"Race-morning brief, {r.predicted.start_local:%Y-%m-%d}", [
            ("Brief", r.brief.text),
            ("Prediction", md_table(["item", "value"],
                                    [list(x) for x in prediction_rows(r.predicted)])),
            ("Forecast", forecast_md(window_only(r.predicted))),
            ("WBGT on course", md_chart(chart, folder, "WBGT across the race")),
            ("Notes", weather_notes()),
        ])  # fmt: skip
    if as_json:
        emit_json({"brief": r.brief.text, "source": r.brief.source, "lang": lang,
                   "rejected_reason": r.brief.rejected_reason, "facts": r.facts,
                   **predict_json(r.predicted), "charts": chart})  # fmt: skip
        return
    out_console.print(r.brief.text)
    if chart:
        out_console.print(f"Chart: {chart.png} and {chart.svg}")
