"""Charts are written as PNG and SVG, deterministic, and carry their caveats."""

from __future__ import annotations

import json
import re
from datetime import date, datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

import numpy as np
import pytest

from blagden.charts import core_temp_chart, wbgt_chart
from blagden.physio import estimate_core_temp
from blagden.weather.cache import DiskCache
from blagden.weather.openmeteo import OpenMeteoClient
from blagden.weather.race_morning import race_morning

DATA = Path(__file__).resolve().parent / "data" / "open_meteo" / "forecast_qmc_2026-11-15.json"
PNG_MAGIC = b"\x89PNG\r\n\x1a\n"


def svg_text(path: Path) -> str:
    """All text in an SVG, lines joined with spaces."""
    parts = re.findall(r"<text[^>]*>(.*?)</text>", path.read_text(encoding="utf-8"), re.S)
    return " ".join(re.sub(r"<[^>]+>", "", p).strip() for p in parts)


def test_core_temp_chart(tmp_path: Path) -> None:
    hr = np.array([110.0] * 5 + [160.0] * 40 + [np.nan] * 3 + [150.0] * 10)
    files = core_temp_chart(hr, estimate_core_temp(hr), tmp_path)
    assert files.png.read_bytes().startswith(PNG_MAGIC)
    svg = svg_text(files.svg)
    assert "less sensitive above" in svg and "de Korte et al. 2022" in svg
    assert "not medical advice" in svg and "heart rate (bpm)" in svg


def test_charts_are_deterministic(tmp_path: Path) -> None:
    hr = np.full(30, 150.0)
    a = core_temp_chart(hr, estimate_core_temp(hr), tmp_path / "a")
    b = core_temp_chart(hr, estimate_core_temp(hr), tmp_path / "b")
    assert a.svg.read_bytes() == b.svg.read_bytes()
    assert a.png.read_bytes() == b.png.read_bytes()


def test_wbgt_chart(tmp_path: Path) -> None:
    body = json.dumps(json.loads(DATA.read_text(encoding="utf-8"))["response"]).encode()
    client = OpenMeteoClient(
        DiskCache(tmp_path / "c"), fetch=lambda u, t: body, today=lambda: date(2026, 11, 9)
    )
    rm = race_morning(14.6517, 121.0493, date(2026, 11, 15), 3, 10, client=client)
    start = datetime(2026, 11, 15, 5, 0, tzinfo=ZoneInfo("Asia/Manila"))
    files = wbgt_chart(rm, tmp_path, start=start, end=start + timedelta(hours=2), stem="w")
    assert files.png.name == "w.png" and files.png.read_bytes().startswith(PNG_MAGIC)
    svg = svg_text(files.svg)
    for text in ("red flag", "black flag", "predicted finish", "Open-Meteo.com", "05:00"):
        assert text in svg


def test_wbgt_chart_needs_values(tmp_path: Path) -> None:
    from blagden.weather.race_morning import RaceMorning

    empty = RaceMorning(0.0, 0.0, date(2026, 11, 15), "forecast", True, ())
    with pytest.raises(ValueError):
        wbgt_chart(empty, tmp_path)
