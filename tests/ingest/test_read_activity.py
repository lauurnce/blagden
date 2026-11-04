import shutil
from datetime import UTC, datetime
from pathlib import Path

import numpy as np
import pytest

from blagden.ingest import (
    NoHeartRateError,
    UnsupportedFormatError,
    read_activity,
    resample_minutes,
)
from tests.ingest.builders import gpx_point, tcx_point, tpx_hr, write_gpx, write_tcx
from tests.ingest.fitwriter import write_fit

FIXTURES = Path(__file__).resolve().parent.parent / "fixtures"


@pytest.mark.parametrize("name", ["synthetic_loop.gpx", "synthetic_loop.tcx"])
def test_synthetic_fixtures_end_to_end(name: str) -> None:
    table, report = read_activity(FIXTURES / name)
    assert len(table) == 361 and report.rows_dropped == {}
    assert table.duration_s == 1800.0
    minutes = resample_minutes(table)
    assert len(minutes) == 30 and minutes.missing_minutes == 0


def test_gpx_and_tcx_fixtures_agree_on_heart_rate() -> None:
    gpx, _ = read_activity(FIXTURES / "synthetic_loop.gpx")
    tcx, _ = read_activity(FIXTURES / "synthetic_loop.tcx")
    assert np.array_equal(gpx.hr_bpm, tcx.hr_bpm)
    assert gpx.distance_source == "computed" and tcx.distance_source == "device"


def test_fit_end_to_end(tmp_path: Path) -> None:
    t = [datetime(2026, 1, 4, 21, 0, s, tzinfo=UTC) for s in range(0, 60, 10)]
    path = write_fit(tmp_path / "r.fit", [(ti, 150, 28.0 * i, 0.0) for i, ti in enumerate(t)])
    table, _ = read_activity(path)
    assert table.source_format == "fit" and len(table) == 6


def test_wrong_extension_is_read_by_content(tmp_path: Path) -> None:
    path = tmp_path / "actually_tcx.gpx"
    shutil.copy(FIXTURES / "synthetic_loop.tcx", path)
    table, report = read_activity(path)
    assert table.source_format == "tcx"
    assert any("content is tcx" in n for n in report.notes)


def test_unknown_extension_with_known_content(tmp_path: Path) -> None:
    path = tmp_path / "run.xml"
    shutil.copy(FIXTURES / "synthetic_loop.gpx", path)
    assert read_activity(path)[0].source_format == "gpx"


def test_unsupported_file_raises(tmp_path: Path) -> None:
    path = tmp_path / "notes.txt"
    path.write_text("not a run")
    with pytest.raises(UnsupportedFormatError, match="not a FIT, GPX or TCX"):
        read_activity(path)


def test_run_without_heart_rate_raises_a_clear_error(tmp_path: Path) -> None:
    path = write_gpx(
        tmp_path / "nohr.gpx", [gpx_point(f"2026-01-04T21:00:{s:02d}Z") for s in (0, 5)]
    )
    with pytest.raises(NoHeartRateError, match="no heart-rate data.*heart-rate sensor"):
        read_activity(path)
    table, _ = read_activity(path, require_hr=False)
    assert len(table) == 2


def test_run_whose_heart_rates_are_all_impossible_says_so(tmp_path: Path) -> None:
    path = write_tcx(tmp_path / "bad.tcx", [tcx_point("2026-01-04T21:00:00Z", 250)])
    with pytest.raises(NoHeartRateError, match="outside 30 to 230 bpm"):
        read_activity(path)


def test_run_with_a_gap_has_missing_minutes_not_filled(tmp_path: Path) -> None:
    times = ["21:00:00", "21:00:30", "21:01:00", "21:04:10", "21:04:40", "21:05:10"]
    path = write_gpx(
        tmp_path / "gap.gpx", [gpx_point(f"2026-01-04T{t}Z", tpx_hr(150)) for t in times]
    )
    table, report = read_activity(path)
    assert [(g.start_elapsed_s, g.duration_s) for g in report.gaps] == [(60.0, 190.0)]
    minutes = resample_minutes(table)
    assert list(minutes.has_hr) == [True, True, False, False, True, True]
    assert minutes.missing_minutes == 2


def test_manila_times_become_utc_and_keep_the_offset(tmp_path: Path) -> None:
    path = write_tcx(tmp_path / "mnl.tcx", [tcx_point("2026-01-05T05:00:00+08:00", 140)])
    table, _ = read_activity(path)
    assert table.time_utc[0] == datetime(2026, 1, 4, 21, 0, tzinfo=UTC)
    assert table.local_utc_offset_s == 8 * 3600
