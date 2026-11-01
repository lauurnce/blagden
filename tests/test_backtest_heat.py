"""The back-test script, run offline on the recorded archive response."""

from __future__ import annotations

import csv
import importlib.util
import json
import sys
from datetime import date
from pathlib import Path

import pytest

from blagden.weather.cache import DiskCache
from blagden.weather.openmeteo import OpenMeteoClient

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location(
    "backtest_heat", ROOT / "scripts" / "backtest_heat.py"
)
assert spec and spec.loader
bt = importlib.util.module_from_spec(spec)
sys.modules["backtest_heat"] = bt
spec.loader.exec_module(bt)

ARCHIVE = ROOT / "tests" / "data" / "open_meteo" / "archive_qmc_2026-10-18.json"
HEADER = "date,place,distance,predicted,actual,lat,lon,start\n"


@pytest.fixture
def client(tmp_path: Path) -> OpenMeteoClient:
    body = json.dumps(json.loads(ARCHIVE.read_text(encoding="utf-8"))["response"]).encode()
    return OpenMeteoClient(
        DiskCache(tmp_path / "cache"), fetch=lambda url, t: body, today=lambda: date(2026, 11, 9)
    )


def write(tmp_path: Path, rows: str) -> Path:
    path = tmp_path / "races.csv"
    path.write_text(HEADER + rows, encoding="utf-8")
    return path


def test_scores_compare_unadjusted_and_adjusted(tmp_path: Path, client, capsys) -> None:  # type: ignore[no-untyped-def]
    path = write(
        tmp_path,
        "2026-10-18,Race 1,21.0975,2:00:00,2:10:00,14.6517,121.0493,05:00\n"
        "2026-10-18,Race 2,10,0:50:00,0:50:00,14.6517,121.0493,06:00\n",
    )
    assert bt.main([str(path), "--json"], client=client) == 0
    out = json.loads(capsys.readouterr().out)
    races, s = out["races"], out["scores"]
    assert [r["unadjusted_s"] for r in races] == [7200.0, 3000.0]
    assert all(r["adjusted_s"] > r["unadjusted_s"] for r in races)  # a warm Manila morning
    mae_u = (abs(7200 - 7800) + 0) / 2 / 60
    mae_a = sum(abs(r["adjusted_s"] - r["actual_s"]) for r in races) / 2 / 60
    assert s["mae_unadjusted_min"] == pytest.approx(mae_u)
    assert s["mae_adjusted_min"] == pytest.approx(mae_a)
    assert s["mape_unadjusted_pct"] == pytest.approx(100 * (600 / 7800) / 2)
    assert s["range_coverage_pct"] == pytest.approx(
        100 * sum(r["lo_s"] <= r["actual_s"] <= r["hi_s"] for r in races) / 2
    )


def test_text_report_and_place_as_coordinates(tmp_path: Path, client, capsys) -> None:  # type: ignore[no-untyped-def]
    path = tmp_path / "races.csv"
    path.write_text(
        "date,place,distance,predicted,actual\n2026-10-18,14.6517 121.0493,5,1500,1560\n",
        encoding="utf-8",
    )
    assert bt.main([str(path)], client=client) == 0
    text = capsys.readouterr().out
    assert "MAE   unadjusted" in text and "MAPE  unadjusted" in text
    assert "Weather data by Open-Meteo.com" in text


def test_missing_columns_and_bad_place(tmp_path: Path, client, capsys) -> None:  # type: ignore[no-untyped-def]
    path = tmp_path / "bad.csv"
    path.write_text("date,place\n2026-10-18,QMC\n", encoding="utf-8")
    assert bt.main([str(path)], client=client) == 1
    assert "missing columns" in capsys.readouterr().err
    with pytest.raises(ValueError, match="LAT LON"):
        bt.coordinates({"place": "Quezon Memorial Circle"})


def test_time_parsing() -> None:
    assert bt.parse_time_s("1:02:03") == 3723.0
    assert bt.parse_time_s("52:30") == 3150.0
    assert bt.parse_time_s("900") == 900.0
    with pytest.raises(ValueError):
        bt.parse_time_s("0:00")


def test_shipped_synthetic_csv_has_the_required_columns() -> None:
    with (ROOT / "examples" / "backtest_synthetic.csv").open(encoding="utf-8") as fh:
        rows = list(csv.DictReader(fh))
    assert rows and {"date", "place", "distance", "predicted", "actual"} <= set(rows[0])
    assert all(r["place"].startswith("Synthetic") for r in rows)
