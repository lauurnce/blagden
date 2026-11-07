"""Command-line interface for Blagden."""

import dataclasses
import json
from datetime import date
from pathlib import Path

import typer

from blagden import __version__
from blagden.ingest import IngestError, read_activity, resample_minutes
from blagden.ingest.summary import format_duration, summarize
from blagden.physio import LIMITATION_NOTE, summarize_strain
from blagden.weather import WeatherError, format_race_morning, race_morning

app = typer.Typer(
    name="blagden",
    help="Heat intelligence for runners in the tropics. Training insight, not medical advice.",
    no_args_is_help=True,
    add_completion=False,
)


@app.callback()
def main() -> None:
    """Blagden command-line tools."""


@app.command()
def version() -> None:
    """Print the Blagden version."""
    typer.echo(__version__)


def _fmt(value: float | None, spec: str, unit: str) -> str:
    return "n/a" if value is None else f"{value:{spec}} {unit}"


@app.command()
def summary(
    files: list[Path] = typer.Argument(..., exists=True, dir_okay=False, help="Run files."),  # noqa: B008
    as_json: bool = typer.Option(False, "--json", help="Print JSON instead of text."),
) -> None:
    """Summarise run files: duration, distance, heart rate and missing minutes. No coordinates."""
    failed = 0
    results = []
    for path in files:
        try:
            table, report = read_activity(path)
        except IngestError as exc:
            failed += 1
            typer.echo(f"{path.name}: error: {exc}", err=True)
            continue
        s = summarize(table, report, resample_minutes(table))
        if as_json:
            results.append({"file": path.name, **dataclasses.asdict(s)})
            continue
        typer.echo(
            f"{path.name}  [{s.source_format}]\n"
            f"  duration         {format_duration(s.duration_s)}\n"
            f"  distance         {_fmt(s.distance_km, '.2f', 'km')} ({s.distance_source})\n"
            f"  heart rate       mean {_fmt(s.hr_mean_bpm, '.0f', 'bpm')}, "
            f"max {_fmt(s.hr_max_bpm, '.0f', 'bpm')}\n"
            f"  minutes          {s.minutes}, missing heart rate {s.missing_minutes}\n"
            f"  cleaning         rows {s.rows}, dropped {s.rows_dropped or 'none'}, "
            f"removed {s.values_removed or 'none'}, gaps {s.gaps}"
        )
    if as_json:
        typer.echo(json.dumps(results, indent=2))
    if failed:
        raise typer.Exit(code=1)


@app.command()
def strain(
    files: list[Path] = typer.Argument(..., exists=True, dir_okay=False, help="Run files."),  # noqa: B008
    start_temp: float | None = typer.Option(
        None, "--start-temp", help="Measured starting core temperature, C (default 37.0, assumed)."
    ),
    resting_hr: float | None = typer.Option(
        None, "--resting-hr", help="Resting heart rate in bpm for PSI (default: 70)."
    ),
    as_json: bool = typer.Option(False, "--json", help="Print JSON instead of text."),
) -> None:
    """Estimate core temperature and strain per run. Training insight, not medical advice."""
    failed = 0
    results = []
    for path in files:
        try:
            table, _ = read_activity(path)
        except IngestError as exc:
            failed += 1
            typer.echo(f"{path.name}: error: {exc}", err=True)
            continue
        s = summarize_strain(resample_minutes(table).hr_bpm, tc0=start_temp, hr0=resting_hr)
        if as_json:
            results.append({"file": path.name, **dataclasses.asdict(s)})
            continue
        start = "measured" if s.start_measured else "assumed, no measurement given"
        if s.peak_psi is None:
            psi_text = "n/a"
        else:
            above = " (above the 0 to 10 scale)" if s.psi_above_scale else ""
            psi_text = f"{s.peak_psi:.1f}{above}"
        rest = "default" if s.hr0_defaulted else "given"
        peak_at = format_duration(60.0 * (s.peak_minute + 1))
        typer.echo(
            f"{path.name}  [{table.source_format}]\n"
            f"  minutes            {s.minutes}\n"
            f"  core temp start    {s.start_tc_c:.2f} C ({start})\n"
            f"  core temp peak     {s.peak_tc_c:.2f} C at {peak_at}\n"
            f"  minutes > {s.threshold_c:.1f} C   {s.minutes_above_threshold}\n"
            f"  peak PSI           {psi_text} (resting HR {s.hr0_bpm:.0f} bpm, {rest})"
        )
    if as_json:
        typer.echo(json.dumps(results, indent=2))
    elif failed < len(files):
        typer.echo(f"\nNote: {LIMITATION_NOTE}")
    if failed:
        raise typer.Exit(code=1)


@app.command("race-morning")
def race_morning_cmd(
    lat: float = typer.Option(..., help="Venue latitude, decimal degrees north."),
    lon: float = typer.Option(..., help="Venue longitude, decimal degrees east."),
    day: str = typer.Option(..., "--date", help="Race date, YYYY-MM-DD (Manila)."),
    start: int = typer.Option(4, help="First hour, Manila time."),
    end: int = typer.Option(9, help="Last hour, Manila time (inclusive)."),
    rural: bool = typer.Option(False, "--rural", help="Use rural wind exponents (e.g. Clark)."),
    as_json: bool = typer.Option(False, "--json", help="Print JSON instead of text."),
) -> None:
    """Hourly heat index and WBGT for a race window. Training insight, not a go or no-go call."""
    try:
        rm = race_morning(lat, lon, date.fromisoformat(day), start, end, urban=not rural)
    except (WeatherError, ValueError) as exc:
        typer.echo(f"error: {exc}", err=True)
        raise typer.Exit(code=1) from exc
    if as_json:
        typer.echo(json.dumps(dataclasses.asdict(rm), indent=2, default=str))
    else:
        typer.echo(format_race_morning(rm))
