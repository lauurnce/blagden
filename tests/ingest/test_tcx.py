from datetime import UTC, datetime
from pathlib import Path

import pytest

from blagden.ingest.table import EmptyActivityError
from blagden.ingest.tcx import read_tcx
from tests.ingest.builders import tcx_point, write_tcx

FIXTURES = Path(__file__).resolve().parent.parent / "fixtures"


def test_synthetic_fixture_reads_every_point() -> None:
    raw = read_tcx(FIXTURES / "synthetic_loop.tcx")
    assert raw.source_format == "tcx"
    assert len(raw.records) == 361
    first, last = raw.records[0], raw.records[-1]
    assert first.time_utc == datetime(2026, 1, 4, 21, 0, tzinfo=UTC)
    assert first.hr_bpm is not None and first.distance_m == 0.0
    assert last.distance_m == pytest.approx(2.8 * 1800, abs=0.1)


def test_fields_are_read(tmp_path: Path) -> None:
    path = write_tcx(tmp_path / "a.tcx", [tcx_point("2026-01-04T21:00:00Z", 140, 12.5, 2.9)])
    rec = read_tcx(path).records[0]
    assert (rec.hr_bpm, rec.distance_m, rec.speed_mps, rec.alt_m) == (140.0, 12.5, 2.9, 5.0)
    assert (rec.lat_deg, rec.lon_deg) == (0.001, 0.001)


def test_trackpoint_without_position_or_hr(tmp_path: Path) -> None:
    path = write_tcx(tmp_path / "b.tcx", [tcx_point("2026-01-04T21:00:00Z", position=False)])
    rec = read_tcx(path).records[0]
    assert rec.hr_bpm is None and rec.lat_deg is None and rec.lon_deg is None


def test_manila_offset_is_converted_to_utc(tmp_path: Path) -> None:
    path = write_tcx(tmp_path / "c.tcx", [tcx_point("2026-01-05T05:00:00+08:00", 130)])
    raw = read_tcx(path)
    assert raw.records[0].time_utc == datetime(2026, 1, 4, 21, 0, tzinfo=UTC)
    assert raw.records[0].time_utc is not None and raw.records[0].time_utc.tzinfo is UTC
    assert raw.local_utc_offset_s == 28800


def test_empty_tcx_raises(tmp_path: Path) -> None:
    with pytest.raises(EmptyActivityError, match="no trackpoints"):
        read_tcx(write_tcx(tmp_path / "e.tcx", []))
