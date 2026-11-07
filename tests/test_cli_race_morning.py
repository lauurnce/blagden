import json
from datetime import date
from pathlib import Path

import pytest
from typer.testing import CliRunner

import blagden.cli as cli
from blagden.weather.cache import DiskCache
from blagden.weather.openmeteo import OpenMeteoClient
from blagden.weather.race_morning import race_morning

DATA = Path(__file__).resolve().parent / "data" / "open_meteo" / "forecast_qmc_2026-11-15.json"
ARGS = ["race-morning", "--lat", "14.6517", "--lon", "121.0493", "--date", "2026-11-15"]


@pytest.fixture
def offline(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    body = json.dumps(json.loads(DATA.read_text(encoding="utf-8"))["response"]).encode()
    client = OpenMeteoClient(
        DiskCache(tmp_path), fetch=lambda url, t: body, today=lambda: date(2026, 11, 9)
    )
    monkeypatch.setattr(cli, "race_morning", lambda *a, **k: race_morning(*a, **k, client=client))


@pytest.mark.usefixtures("offline")
def test_text_table() -> None:
    result = CliRunner().invoke(cli.app, ARGS)
    assert result.exit_code == 0, result.output
    assert "04:00" in result.stdout and "09:00" in result.stdout
    assert "Weather data by Open-Meteo.com" in result.stdout


@pytest.mark.usefixtures("offline")
def test_json_rows() -> None:
    result = CliRunner().invoke(cli.app, [*ARGS, "--json", "--start", "5", "--end", "6"])
    data = json.loads(result.stdout)
    assert [h["time_local"][11:16] for h in data["hours"]] == ["05:00", "06:00"]
    assert data["wbgt_model_error_c"] == 1.0


@pytest.mark.usefixtures("offline")
def test_bad_window_exits_nonzero() -> None:
    result = CliRunner().invoke(cli.app, [*ARGS, "--start", "9", "--end", "4"])
    assert result.exit_code == 1 and "error:" in result.stderr
