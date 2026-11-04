"""Command-line interface for Blagden."""

import dataclasses
import json
from pathlib import Path

import typer

from blagden import __version__
from blagden.ingest import IngestError, read_activity, resample_minutes
from blagden.ingest.summary import format_duration, summarize

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
