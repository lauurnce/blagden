import json
from datetime import date
from pathlib import Path

import pytest
from typer.testing import CliRunner

import blagden.cli as cli
from blagden.brief import llm
from blagden.weather.cache import DiskCache
from blagden.weather.openmeteo import OpenMeteoClient
from blagden.weather.race_morning import race_morning

DATA = Path(__file__).resolve().parent / "data" / "open_meteo" / "forecast_qmc_2026-11-15.json"
ARGS = [
    "brief", "--lat", "14.6517", "--lon", "121.0493", "--date", "2026-11-15",
    "--distance", "21.0975", "--known-distance", "10", "--known-time", "52:30",
]  # fmt: skip


@pytest.fixture(autouse=True)
def offline(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    body = json.dumps(json.loads(DATA.read_text(encoding="utf-8"))["response"]).encode()
    client = OpenMeteoClient(
        DiskCache(tmp_path), fetch=lambda url, t: body, today=lambda: date(2026, 11, 9)
    )
    monkeypatch.setattr(cli, "race_morning", lambda *a, **k: race_morning(*a, **k, client=client))
    monkeypatch.delenv(llm.ENV_PROVIDER, raising=False)


def test_english_brief() -> None:
    result = CliRunner().invoke(cli.app, ARGS)
    assert result.exit_code == 0, result.output
    assert result.stdout.startswith("Start is 5:00 AM at WBGT 24.7")
    assert result.stdout.strip().endswith("Training insight, not medical advice.")


def test_taglish_brief() -> None:
    result = CliRunner().invoke(cli.app, [*ARGS, "--lang", "tl"])
    assert result.exit_code == 0 and "ang start" in result.stdout


def test_bad_language_and_bad_time() -> None:
    assert CliRunner().invoke(cli.app, [*ARGS, "--lang", "fr"]).exit_code == 1
    bad = [*ARGS[:-1], "0:00"]
    result = CliRunner().invoke(cli.app, bad)
    assert result.exit_code == 1 and "error:" in result.stderr
