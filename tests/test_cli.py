"""CLI smoke tests with Typer's runner, JSON schema checks and output files. Offline only."""

from __future__ import annotations

import json
import re
from datetime import date
from pathlib import Path
from typing import Any

import jsonschema
import pytest
from typer.testing import CliRunner

import blagden.app as app_module
from blagden.brief import llm
from blagden.cli import EXIT_INPUT, EXIT_WEATHER, app
from blagden.weather import WeatherError
from blagden.weather.cache import DiskCache
from blagden.weather.openmeteo import OpenMeteoClient
from blagden.weather.race_morning import race_morning
from tests.ingest.builders import gpx_point, write_gpx

ROOT = Path(__file__).resolve().parent
FIXTURE = ROOT / "fixtures" / "synthetic_loop.gpx"
FORECAST = ROOT / "data" / "open_meteo" / "forecast_qmc_2026-11-15.json"
VENUE = ["--lat", "14.6517", "--lon", "121.0493"]
PREDICT = [*VENUE, "--distance", "21.0975", "--recent-time", "52:30", "--recent-distance", "10",
           "--race-date", "2026-11-15"]  # fmt: skip
COORD = re.compile(r"\b(lat|lon|latitude|longitude)\b", re.I)

NUM = {"type": ["number", "null"]}
STR = {"type": ["string", "null"]}
CHARTS = {"type": ["object", "null"], "required": ["png", "svg"]}
ANALYZE_SCHEMA = {
    "type": "object",
    "required": ["file", "activity", "strain", "note", "charts"],
    "properties": {
        "activity": {"type": "object", "required": ["duration_s", "hr_mean_bpm", "minutes"]},
        "strain": {
            "type": "object",
            "required": ["start_tc_c", "peak_tc_c", "minutes_above_threshold", "peak_psi"],
            "properties": {"peak_tc_c": {"type": "number"}, "peak_psi": NUM},
        },
        "note": {"type": "string", "pattern": "39.0 C"},
        "charts": CHARTS,
    },
}
HOUR = {"type": "object", "required": ["time_local", "t_air_c", "rh_pct", "heat_index_c",
        "pagasa_category", "wbgt_c", "flag", "racinais_level"],
        "properties": {"wbgt_c": NUM, "heat_index_c": NUM, "flag": STR}}  # fmt: skip
FORECAST_SCHEMA = {
    "type": "object",
    "required": ["forecast", "notes", "charts"],
    "properties": {"forecast": {"type": "object", "required": ["day", "hours", "attribution"],
                                "properties": {"hours": {"type": "array", "items": HOUR}}}},
}  # fmt: skip
PREDICT_SCHEMA = {
    "type": "object",
    "required": ["baseline", "prediction", "start_local", "finish_local", "wbgt_by_hour",
                 "attribution"],
    "properties": {
        "prediction": {"type": "object", "properties": {"time_s": {"type": "number"}},
                       "required": ["time_s", "lo_s", "hi_s", "level", "extrapolated",
                                    "driver_text"]},
        "baseline": {"type": "object", "required": ["time_s", "source", "warnings"]},
    },
}  # fmt: skip
BRIEF_SCHEMA = {
    "allOf": [PREDICT_SCHEMA],
    "required": ["brief", "source", "lang", "facts"],
    "properties": {"brief": {"type": "string"}, "source": {"enum": ["template", "llm"]},
                   "facts": {"type": "object", "required": ["start_time", "allowed_numbers"]}},
}  # fmt: skip


@pytest.fixture(autouse=True)
def offline(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    body = json.dumps(json.loads(FORECAST.read_text(encoding="utf-8"))["response"]).encode()
    client = OpenMeteoClient(
        DiskCache(tmp_path / "cache"), fetch=lambda u, t: body, today=lambda: date(2026, 11, 9)
    )
    monkeypatch.setattr(
        app_module, "race_morning", lambda *a, **k: race_morning(*a, **{**k, "client": client})
    )
    monkeypatch.delenv(llm.ENV_PROVIDER, raising=False)
    monkeypatch.chdir(tmp_path)


def run(args: list[str]) -> Any:
    return CliRunner().invoke(app, args)


def as_json(args: list[str], schema: dict[str, Any]) -> dict[str, Any]:
    result = run([*args, "--json"])
    assert result.exit_code == 0, result.output
    data: dict[str, Any] = json.loads(result.stdout)
    jsonschema.validate(data, schema)
    return data


def test_version() -> None:
    assert run(["version"]).exit_code == 0
    assert "version" in json.loads(run(["version", "--json"]).stdout)


def test_analyze_text_json_and_no_coordinates() -> None:
    text = run(["analyze", str(FIXTURE)])
    assert text.exit_code == 0, text.output
    assert "core temp peak" in text.stdout and "less sensitive" not in text.stdout
    assert "above 39.0 C" in text.stdout.replace("\n", " ")
    data = as_json(["analyze", str(FIXTURE)], ANALYZE_SCHEMA)
    assert data["charts"] is None
    assert not COORD.search(text.stdout) and not COORD.search(json.dumps(data))


def test_analyze_charts_and_report(tmp_path: Path) -> None:
    out = tmp_path / "out"
    data = as_json(["analyze", str(FIXTURE), "--out", str(out), "--report"], ANALYZE_SCHEMA)
    assert Path(data["charts"]["png"]).exists() and Path(data["charts"]["svg"]).exists()
    report = (out / "REPORT.md").read_text(encoding="utf-8")
    assert "![core temperature](core_temperature.png)" in report and "de Korte" in report
    assert not COORD.search(report)


def test_report_without_out_uses_default_folder(tmp_path: Path) -> None:
    assert run(["analyze", str(FIXTURE), "--report"]).exit_code == 0
    assert (tmp_path / "blagden-report" / "REPORT.md").exists()


def test_analyze_errors(tmp_path: Path) -> None:
    nohr = write_gpx(tmp_path / "nohr.gpx", [gpx_point("2026-01-04T21:00:00Z")])
    result = run(["analyze", str(nohr)])
    assert result.exit_code == EXIT_INPUT and "no valid heart rate" in result.stderr
    assert run(["analyze", str(tmp_path / "missing.gpx")]).exit_code == 2  # usage error


def test_forecast(tmp_path: Path) -> None:
    text = run(["forecast", *VENUE, "--date", "2026-11-15", "--from", "04:00", "--to", "09:00"])
    assert text.exit_code == 0, text.output
    assert "04:00" in text.stdout and "09:00" in text.stdout and "Open-Meteo" in text.stdout
    data = as_json(["forecast", *VENUE, "--date", "2026-11-15", "--out", str(tmp_path / "f")],
                   FORECAST_SCHEMA)  # fmt: skip
    assert [h["time_local"][11:16] for h in data["forecast"]["hours"]][0] == "04:00"
    assert (tmp_path / "f" / "wbgt.png").exists() and (tmp_path / "f" / "wbgt.svg").exists()


def test_forecast_errors(monkeypatch: pytest.MonkeyPatch) -> None:
    bad = run(["forecast", *VENUE, "--date", "2026-11-15", "--from", "09:00", "--to", "04:00"])
    assert bad.exit_code == EXIT_INPUT and "error:" in bad.stderr
    assert run(["forecast", *VENUE, "--date", "15/11/2026"]).exit_code == EXIT_INPUT

    def down(*a: object, **k: object) -> None:
        raise WeatherError("Open-Meteo unavailable after 4 attempts")

    monkeypatch.setattr(app_module, "race_morning", down)
    result = run(["forecast", *VENUE, "--date", "2026-11-15"])
    assert result.exit_code == EXIT_WEATHER and "weather data unavailable" in result.stderr


def test_predict(tmp_path: Path) -> None:
    text = run(["predict", *PREDICT])
    assert text.exit_code == 0, text.output
    assert "heat-adjusted" in text.stdout and "PaceBrain" not in text.stdout
    data = as_json(["predict", *PREDICT, "--report", "--out", str(tmp_path / "p")], PREDICT_SCHEMA)
    p = data["prediction"]
    assert p["lo_s"] <= p["time_s"] <= p["hi_s"] and data["baseline"]["source"] == "riegel"
    assert "![WBGT across the race](wbgt.png)" in (tmp_path / "p" / "REPORT.md").read_text()


def test_brief(tmp_path: Path) -> None:
    text = run(["brief", *PREDICT])
    assert text.exit_code == 0, text.output
    assert text.stdout.startswith("Start is 5:00 AM at WBGT 24.7")
    assert "ang start" in run(["brief", *PREDICT, "--lang", "tl"]).stdout
    data = as_json(["brief", *PREDICT, "--report", "--out", str(tmp_path / "b")], BRIEF_SCHEMA)
    assert data["source"] == "template"
    report = (tmp_path / "b" / "REPORT.md").read_text(encoding="utf-8")
    assert data["brief"] in report and "## Forecast" in report
    assert run(["brief", *PREDICT, "--lang", "fr"]).exit_code == EXIT_INPUT
