from datetime import UTC, datetime, timedelta

import numpy as np
import pytest

from blagden.ingest.clean import clean
from blagden.ingest.table import EmptyActivityError, RawActivity, RawRecord

T0 = datetime(2026, 1, 4, 21, 0, tzinfo=UTC)


def at(s: float, hr: float | None = 150.0, **kw: float | None) -> RawRecord:
    return RawRecord(T0 + timedelta(seconds=s), hr, **kw)


def raw(*recs: RawRecord) -> RawActivity:
    return RawActivity(tuple(recs), "gpx")


def test_impossible_heart_rates_are_removed_not_rows() -> None:
    table, report = clean(raw(at(0, 29.0), at(1, 30.0), at(2, 230.0), at(3, 231.0), at(4, 0.0)))
    assert len(table) == 5
    assert np.isnan(table.hr_bpm[[0, 3, 4]]).all()
    assert table.hr_bpm[1] == 30.0 and table.hr_bpm[2] == 230.0
    assert report.values_removed == {"hr_out_of_range": 3}
    assert report.hr_missing_rows == 3


def test_rows_without_time_are_dropped_and_counted() -> None:
    table, report = clean(raw(RawRecord(None, 140.0), at(0), at(5)))
    assert len(table) == 2
    assert report.rows_in == 3 and report.rows_out == 2
    assert report.rows_dropped == {"missing_time": 1}


def test_duplicates_merge_first_present_value() -> None:
    table, report = clean(raw(at(0, None, lat_deg=0.001, lon_deg=0.0), at(0, 141.0), at(5, 142.0)))
    assert len(table) == 2
    assert table.hr_bpm[0] == 141.0
    assert table.lat_deg[0] == 0.001
    assert report.rows_dropped == {"duplicate_time": 1}


def test_out_of_order_rows_are_sorted_and_reported() -> None:
    table, report = clean(raw(at(10, 150.0), at(0, 140.0), at(5, 145.0)))
    assert list(table.elapsed_s) == [0.0, 5.0, 10.0]
    assert list(table.hr_bpm) == [140.0, 145.0, 150.0]
    assert report.reordered


def test_gaps_are_reported_not_filled() -> None:
    table, report = clean(raw(at(0), at(30), at(200), at(230)))
    assert len(table) == 4
    assert [(g.start_elapsed_s, g.duration_s) for g in report.gaps] == [(30.0, 170.0)]


def test_times_stay_timezone_aware_utc_and_elapsed_starts_at_zero() -> None:
    table, _ = clean(raw(at(0), at(7)))
    assert all(t.tzinfo is UTC for t in table.time_utc)
    assert table.elapsed_s[0] == 0.0 and table.elapsed_s[1] == 7.0
    assert table.duration_s == 7.0


def test_device_distance_wins_over_positions() -> None:
    table, _ = clean(raw(at(0, distance_m=0.0, lat_deg=0.0, lon_deg=0.0), at(5, distance_m=14.0)))
    assert table.distance_source == "device"
    assert list(table.distance_m) == [0.0, 14.0]


def test_distance_is_computed_from_positions_when_device_has_none() -> None:
    table, _ = clean(raw(at(0, lat_deg=0.0, lon_deg=0.0), at(5, lat_deg=0.001, lon_deg=0.0)))
    assert table.distance_source == "computed"
    assert table.distance_m[1] == pytest.approx(111.19, abs=0.01)


def test_no_distance_and_no_position_gives_none_source() -> None:
    table, _ = clean(raw(at(0), at(5)))
    assert table.distance_source == "none"
    assert np.isnan(table.distance_m).all()


def test_bad_positions_and_negative_speed_are_removed() -> None:
    table, report = clean(raw(at(0, lat_deg=91.0, lon_deg=0.0, speed_mps=-1.0), at(5)))
    assert np.isnan(table.lat_deg[0]) and np.isnan(table.speed_mps[0])
    assert report.values_removed == {"position_out_of_range": 1, "speed_negative": 1}


def test_no_timed_rows_raises() -> None:
    with pytest.raises(EmptyActivityError):
        clean(raw(RawRecord(None, 140.0)))
