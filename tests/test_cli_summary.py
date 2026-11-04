import json
from pathlib import Path

from typer.testing import CliRunner

from blagden.cli import app
from tests.ingest.builders import gpx_point, write_gpx

FIXTURES = Path(__file__).resolve().parent / "fixtures"


def test_summary_text_has_no_coordinates() -> None:
    result = CliRunner().invoke(app, ["summary", str(FIXTURES / "synthetic_loop.tcx")])
    assert result.exit_code == 0, result.output
    out = result.stdout
    assert "duration         0:30:00" in out
    assert "distance         5.04 km (device)" in out
    assert "missing heart rate 0" in out
    for word in ("lat", "lon", "0.00"):
        assert word not in out


def test_summary_json_has_no_coordinates() -> None:
    result = CliRunner().invoke(app, ["summary", "--json", str(FIXTURES / "synthetic_loop.gpx")])
    assert result.exit_code == 0
    data = json.loads(result.stdout)[0]
    assert data["minutes"] == 30 and data["distance_source"] == "computed"
    assert not any("lat" in k or "lon" in k for k in data)


def test_summary_reports_unreadable_file_and_exits_nonzero(tmp_path: Path) -> None:
    path = write_gpx(tmp_path / "nohr.gpx", [gpx_point("2026-01-04T21:00:00Z")])
    result = CliRunner().invoke(app, ["summary", str(path)])
    assert result.exit_code == 1
    assert "no valid heart rate" in result.stderr
