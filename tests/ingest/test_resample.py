from datetime import UTC, datetime, timedelta

import numpy as np
from hypothesis import given, settings
from hypothesis import strategies as st

from blagden.ingest.clean import clean
from blagden.ingest.resample import resample_minutes
from blagden.ingest.table import RawActivity, RawRecord

T0 = datetime(2026, 1, 4, 21, 0, tzinfo=UTC)


def table_from(samples: list[tuple[float, float | None]]):  # type: ignore[no-untyped-def]
    recs = tuple(RawRecord(T0 + timedelta(seconds=s), hr) for s, hr in samples)
    return clean(RawActivity(recs, "tcx"))[0]


def test_hand_built_example() -> None:
    # minute 0: 100, 110, 120 -> 110
    # minute 1: no sample at all (gap) -> missing
    # minute 2: 130, (no HR), 140 -> 135 from two samples
    table = table_from([(0, 100), (20, 110), (40, 120), (130, 130), (150, None), (175, 140)])
    m = resample_minutes(table)
    assert len(m) == 3
    assert m.hr_bpm[0] == 110.0
    assert np.isnan(m.hr_bpm[1])
    assert m.hr_bpm[2] == 135.0
    assert list(m.n_samples) == [3, 0, 2]
    assert list(m.has_hr) == [True, False, True]
    assert m.missing_minutes == 1
    assert m.minute_start_utc(2) == T0 + timedelta(minutes=2)


def test_sample_on_the_end_boundary_joins_the_last_minute() -> None:
    m = resample_minutes(table_from([(0, 100), (60, 120), (120, 140)]))
    assert len(m) == 2
    assert list(m.hr_bpm) == [100.0, 130.0]


def test_single_sample_gives_one_minute() -> None:
    m = resample_minutes(table_from([(0, 150)]))
    assert len(m) == 1 and m.hr_bpm[0] == 150.0


def test_removed_heart_rates_do_not_count() -> None:
    m = resample_minutes(table_from([(0, 150), (10, 250), (20, 10)]))
    assert m.hr_bpm[0] == 150.0 and m.n_samples[0] == 1


samples = st.lists(
    st.tuples(st.integers(0, 3600), st.one_of(st.none(), st.floats(30, 230))),
    min_size=1,
    max_size=200,
)


@settings(max_examples=200, deadline=None)
@given(samples)
def test_minutes_never_invent_heart_rate(rows: list[tuple[int, float | None]]) -> None:
    table = table_from([(float(s), hr) for s, hr in rows])
    m = resample_minutes(table)
    assert int(m.n_samples.sum()) == int(np.isfinite(table.hr_bpm).sum())
    assert (m.has_hr == (m.n_samples > 0)).all()
    assert np.isnan(m.hr_bpm[~m.has_hr]).all()
    idx = np.minimum((table.elapsed_s // 60).astype(int), len(m) - 1)
    for i in np.flatnonzero(m.has_hr):
        in_minute = table.hr_bpm[(idx == i) & np.isfinite(table.hr_bpm)]
        assert in_minute.min() - 1e-9 <= m.hr_bpm[i] <= in_minute.max() + 1e-9
