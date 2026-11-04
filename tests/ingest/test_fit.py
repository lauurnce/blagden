from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from blagden.ingest.fit import read_fit
from blagden.ingest.table import IngestError
from tests.ingest.fitwriter import write_fit

T0 = datetime(2026, 1, 4, 21, 0, tzinfo=UTC)


def _rows(n: int) -> list[tuple[datetime, int | None, float | None, float | None]]:
    return [(T0 + timedelta(seconds=10 * i), 140 + i, 28.0 * i, 0.001) for i in range(n)]


def test_records_are_read_with_units(tmp_path: Path) -> None:
    raw = read_fit(write_fit(tmp_path / "a.fit", _rows(3)))
    assert raw.source_format == "fit"
    assert len(raw.records) == 3
    rec = raw.records[2]
    assert rec.time_utc == T0 + timedelta(seconds=20)
    assert rec.time_utc is not None and rec.time_utc.tzinfo is not None
    assert rec.hr_bpm == 142.0
    assert rec.distance_m == pytest.approx(56.0)
    assert rec.speed_mps == pytest.approx(2.8)
    assert rec.alt_m == pytest.approx(5.0)
    assert rec.lat_deg == pytest.approx(0.001, abs=1e-7)


def test_invalid_heart_rate_and_position_are_none(tmp_path: Path) -> None:
    raw = read_fit(write_fit(tmp_path / "b.fit", [(T0, None, None, None)]))
    rec = raw.records[0]
    assert rec.hr_bpm is None and rec.lat_deg is None and rec.distance_m is None


def test_local_offset_from_activity_message(tmp_path: Path) -> None:
    raw = read_fit(write_fit(tmp_path / "c.fit", _rows(2), local_offset_s=8 * 3600))
    assert raw.local_utc_offset_s == 28800


def test_offset_is_none_without_activity_message(tmp_path: Path) -> None:
    assert read_fit(write_fit(tmp_path / "d.fit", _rows(2))).local_utc_offset_s is None


def test_corrupt_file_raises_ingest_error(tmp_path: Path) -> None:
    path = write_fit(tmp_path / "e.fit", _rows(3))
    data = bytearray(path.read_bytes())
    data[30] ^= 0xFF
    path.write_bytes(bytes(data))
    with pytest.raises(IngestError, match="not a readable FIT file"):
        read_fit(path)
