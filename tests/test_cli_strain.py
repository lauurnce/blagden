import json
import re
from datetime import UTC, datetime, timedelta
from pathlib import Path

from typer.testing import CliRunner

from blagden.cli import app
from tests.ingest.builders import gpx_point, tpx_hr, write_gpx

FIXTURES = Path(__file__).resolve().parent / "fixtures"


def hard_run(path: Path, minutes: int = 90, hr: int = 170) -> Path:
    start = datetime(2026, 1, 4, 21, 0, tzinfo=UTC)
    points = [
        gpx_point((start + timedelta(seconds=30 * i)).isoformat(), tpx_hr(hr))
        for i in range(2 * minutes + 1)
    ]
    return write_gpx(path, points)


def test_strain_text_shows_figures_and_limitation() -> None:
    result = CliRunner().invoke(app, ["strain", str(FIXTURES / "synthetic_loop.tcx")])
    assert result.exit_code == 0, result.output
    out = result.stdout
    assert "core temp start    37.00 C (assumed" in out
    assert "core temp peak" in out and "minutes > 38.5 C" in out and "peak PSI" in out
    assert "resting HR 70 bpm, default" in out
    assert "above 39.0 C (de Korte et al. 2022)" in out
    assert not re.search(r"\b(lat|lon|latitude|longitude)\b", out, re.IGNORECASE)


def test_strain_counts_minutes_above_threshold(tmp_path: Path) -> None:
    path = hard_run(tmp_path / "hard.gpx")
    result = CliRunner().invoke(app, ["strain", "--json", str(path)])
    assert result.exit_code == 0, result.output
    data = json.loads(result.stdout)[0]
    assert data["minutes"] == 90
    assert data["peak_tc_c"] > 38.5 and data["minutes_above_threshold"] > 0
    assert data["note"].startswith("Core temperature is estimated from heart rate alone")
    assert not any("lat" in k or "lon" in k for k in data)


def test_strain_options_set_start_and_resting_hr(tmp_path: Path) -> None:
    path = hard_run(tmp_path / "hard.gpx", minutes=20)
    args = ["strain", "--json", "--start-temp", "37.3", "--resting-hr", "52", str(path)]
    data = json.loads(CliRunner().invoke(app, args).stdout)[0]
    assert (data["start_tc_c"], data["start_measured"]) == (37.3, True)
    assert (data["hr0_bpm"], data["hr0_defaulted"]) == (52.0, False)


def test_strain_reports_file_without_hr(tmp_path: Path) -> None:
    path = write_gpx(tmp_path / "nohr.gpx", [gpx_point("2026-01-04T21:00:00Z")])
    result = CliRunner().invoke(app, ["strain", str(path)])
    assert result.exit_code == 1
    assert "no valid heart rate" in result.stderr
