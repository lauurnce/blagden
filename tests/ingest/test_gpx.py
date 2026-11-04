from datetime import UTC, datetime
from pathlib import Path

import pytest

from blagden.ingest.gpx import read_gpx
from blagden.ingest.table import EmptyActivityError
from tests.ingest.builders import gpx_point, tpx_hr, write_gpx

FIXTURES = Path(__file__).resolve().parent.parent / "fixtures"


def test_synthetic_fixture_reads_every_point_with_heart_rate() -> None:
    raw = read_gpx(FIXTURES / "synthetic_loop.gpx")
    assert raw.source_format == "gpx"
    assert len(raw.records) == 361
    assert all(r.hr_bpm is not None for r in raw.records)
    assert raw.records[0].time_utc == datetime(2026, 1, 4, 21, 0, tzinfo=UTC)
    assert raw.records[-1].time_utc == datetime(2026, 1, 4, 21, 30, tzinfo=UTC)
    assert all(r.distance_m is None for r in raw.records)


@pytest.mark.parametrize(
    "hr_xml",
    [
        "<gpxtpx:TrackPointExtension><gpxtpx:hr>151</gpxtpx:hr></gpxtpx:TrackPointExtension>",
        "<tpx2:TrackPointExtension><tpx2:hr>151</tpx2:hr></tpx2:TrackPointExtension>",
        "<gpxdata:hr>151</gpxdata:hr>",
        "<heartrate>151</heartrate>",
        "<heart_rate>151</heart_rate>",
    ],
    ids=["garmin_tpx_v1", "garmin_tpx_v2", "cluetrust", "heartrate", "heart_rate"],
)
def test_heart_rate_variants(tmp_path: Path, hr_xml: str) -> None:
    path = write_gpx(tmp_path / "v.gpx", [gpx_point("2026-01-04T21:00:00Z", hr_xml)])
    assert read_gpx(path).records[0].hr_bpm == 151.0


def test_speed_from_tpx_v2(tmp_path: Path) -> None:
    ext = (
        "<tpx2:TrackPointExtension><tpx2:hr>140</tpx2:hr>"
        "<tpx2:speed>3.1</tpx2:speed></tpx2:TrackPointExtension>"
    )
    path = write_gpx(tmp_path / "s.gpx", [gpx_point("2026-01-04T21:00:00Z", ext)])
    assert read_gpx(path).records[0].speed_mps == 3.1


def test_point_without_heart_rate_has_none(tmp_path: Path) -> None:
    path = write_gpx(tmp_path / "n.gpx", [gpx_point("2026-01-04T21:00:00Z")])
    assert read_gpx(path).records[0].hr_bpm is None


def test_offset_time_is_converted_to_utc_and_offset_kept(tmp_path: Path) -> None:
    path = write_gpx(tmp_path / "o.gpx", [gpx_point("2026-01-05T05:00:00+08:00", tpx_hr(120))])
    raw = read_gpx(path)
    assert raw.records[0].time_utc == datetime(2026, 1, 4, 21, 0, tzinfo=UTC)
    assert raw.local_utc_offset_s == 8 * 3600


def test_naive_time_is_read_as_utc_with_a_note(tmp_path: Path) -> None:
    path = write_gpx(tmp_path / "z.gpx", [gpx_point("2026-01-04T21:00:00", tpx_hr(120))])
    raw = read_gpx(path)
    assert raw.records[0].time_utc == datetime(2026, 1, 4, 21, 0, tzinfo=UTC)
    assert any("without a zone" in n for n in raw.notes)


def test_missing_and_malformed_times_become_none(tmp_path: Path) -> None:
    path = write_gpx(
        tmp_path / "m.gpx", [gpx_point(None, tpx_hr(120)), gpx_point("yesterday", tpx_hr(121))]
    )
    assert [r.time_utc for r in read_gpx(path).records] == [None, None]


def test_empty_gpx_raises(tmp_path: Path) -> None:
    path = write_gpx(tmp_path / "e.gpx", [])
    with pytest.raises(EmptyActivityError, match="no track points"):
        read_gpx(path)
