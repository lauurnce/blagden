"""Heat adjustment against docs/SCIENCE.md section 6 and the cited studies."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
from hypothesis import given
from hypothesis import strategies as st

from blagden.predict.baseline import BaselinePrediction
from blagden.predict.heat import (
    DEFAULT_BASE_WBGT_C,
    K_PER_C,
    K_RANGE_PER_C,
    heat_adjust,
    predict_for_window,
    runner_level,
    window_wbgt,
)

SCIENCE_MD = Path(__file__).resolve().parents[2] / "docs" / "SCIENCE.md"


def base(
    time_s: float, km: float = 42.195, lo: float | None = None, hi: float | None = None
) -> BaselinePrediction:
    return BaselinePrediction(km, time_s, lo, hi, "manual", {})


ELITE = base(2 * 3600 + 20 * 60)
RECREATIONAL = base(4 * 3600 + 30 * 60)


def test_slopes_match_science_table() -> None:
    text = SCIENCE_MD.read_text(encoding="utf-8")
    assert "| $k_{elite}$ | 0.0018 per C; range 0.0010 to 0.0030 |" in text
    assert "| $k_{nonelite}$ | 0.0060 per C; range 0.0040 to 0.0080 |" in text
    assert K_PER_C == {"elite": 0.0018, "nonelite": 0.0060}
    assert K_RANGE_PER_C == {"elite": (0.0010, 0.0030), "nonelite": (0.0040, 0.0080)}
    assert DEFAULT_BASE_WBGT_C == 10.0


@pytest.mark.parametrize("wbgt", [-3.0, 5.0, 10.0])
def test_no_adjustment_at_cool_reference_conditions(wbgt: float) -> None:
    for b in (ELITE, RECREATIONAL):
        p = heat_adjust(b, wbgt)
        assert p.time_s == b.time_s and p.lo_s == b.time_s and p.hi_s == b.time_s
        assert p.delta_wbgt_c == 0.0 and p.driver == "none"
        assert p.driver_text.startswith("No heat adjustment")


def test_no_adjustment_when_race_matches_known_baseline_weather() -> None:
    p = heat_adjust(RECREATIONAL, 24.0, wbgt_base_c=24.0)
    assert p.time_s == RECREATIONAL.time_s and not p.baseline_wbgt_defaulted


@given(w1=st.floats(-10.0, 40.0), w2=st.floats(-10.0, 40.0))
def test_slowdown_grows_as_wbgt_rises(w1: float, w2: float) -> None:
    lo, hi = sorted((w1, w2))
    for b in (ELITE, RECREATIONAL):
        a, c = heat_adjust(b, lo), heat_adjust(b, hi)
        assert c.time_s >= a.time_s and c.hi_s >= a.hi_s and c.lo_s >= a.lo_s
        if hi > lo and lo >= DEFAULT_BASE_WBGT_C:
            assert c.time_s > a.time_s


def test_elite_slope_reproduces_ely_2007_top_men() -> None:
    # Ely 2007: top men 1.7, 2.5, 3.3, 4.5 percent slower at quartile midpoints 7.5..22.5 C.
    xs, ys = [7.5, 12.5, 17.5, 22.5], [1.7, 2.5, 3.3, 4.5]
    mx, my = sum(xs) / 4, sum(ys) / 4
    slope = sum((x - mx) * (y - my) for x, y in zip(xs, ys, strict=True)) / sum(
        (x - mx) ** 2 for x in xs
    )
    assert K_PER_C["elite"] == pytest.approx(slope / 100, abs=5e-5)


def test_slower_runners_affected_at_least_as_much_as_cited() -> None:
    # Ely 2007: 25th to 300th place slowed more than faster runners; Mantzios 2022
    # restating Ely: about 0.6 percent per C for well-trained runners, 0.1 to 0.3 for elites.
    for wbgt in (15.0, 20.0, 25.0, 30.0):
        e, r = heat_adjust(ELITE, wbgt), heat_adjust(RECREATIONAL, wbgt)
        e_pct = (e.time_s / ELITE.time_s - 1) / e.delta_wbgt_c
        r_pct = (r.time_s / RECREATIONAL.time_s - 1) / r.delta_wbgt_c
        assert r_pct >= e_pct
        assert r_pct >= 0.006 - 1e-12
        assert 0.001 <= e_pct <= 0.003


@given(
    t=st.floats(600.0, 8 * 3600.0),
    km=st.sampled_from([5.0, 10.0, 21.0975, 42.195]),
    frac=st.one_of(st.none(), st.floats(0.0, 0.3)),
    wbgt=st.floats(-10.0, 40.0),
    w_base=st.one_of(st.none(), st.floats(0.0, 30.0)),
)
def test_range_always_contains_point(
    t: float, km: float, frac: float | None, wbgt: float, w_base: float | None
) -> None:
    b = base(t, km) if frac is None else base(t, km, t * (1 - frac), t * (1 + frac))
    p = heat_adjust(b, wbgt, wbgt_base_c=w_base)
    assert p.lo_s <= p.time_s <= p.hi_s


def test_worked_example_from_architecture() -> None:
    p = heat_adjust(base(14400.0), 28.0)
    assert p.time_s == pytest.approx(15955.2)
    assert p.lo_s == pytest.approx(15436.8)
    assert p.hi_s == pytest.approx(14400.0 * (1 + 0.008 * 15 + 2 * 0.008 * 3))
    assert p.level == "nonelite" and p.extrapolated and p.baseline_wbgt_defaulted
    assert p.driver == "heat" and "18.0 C above the 10.0 C baseline (assumed)" in p.driver_text


def test_level_rule_at_2_30() -> None:
    assert runner_level(base(2.5 * 3600 - 1)) == "elite"
    assert runner_level(base(2.5 * 3600)) == "nonelite"
    assert runner_level(base(30 * 60, 10.0)) == "elite"  # a 2:18 marathon equivalent
    assert runner_level(base(45 * 60, 10.0)) == "nonelite"


def test_extrapolation_flags() -> None:
    assert not heat_adjust(base(3 * 3600), 20.0).extrapolated
    assert heat_adjust(base(3 * 3600), 25.5).extrapolated
    assert heat_adjust(base(4 * 3600), 15.0).extrapolated  # non-elite beyond 3:40
    assert not heat_adjust(ELITE, 24.0).extrapolated


def test_baseline_uncertainty_can_be_the_main_driver() -> None:
    b = base(4 * 3600, lo=3.5 * 3600, hi=4.5 * 3600)
    p = heat_adjust(b, 12.0)
    assert p.driver == "baseline_uncertainty"
    assert p.driver_text.startswith("Main driver: uncertainty in the baseline time")


MANILA_0400 = datetime(2026, 11, 14, 20, 0, tzinfo=UTC)  # 04:00 in Manila
HOURLY = [(MANILA_0400 + timedelta(hours=i), w) for i, w in enumerate([24.0, 25.0, 26.0, 28.0])]


def test_window_average_by_hand() -> None:
    # 04:30 to 05:30: line from 24.5 to 25.0 then 25.0 to 25.5, mean 25.0.
    assert window_wbgt(HOURLY, MANILA_0400 + timedelta(minutes=30), 3600.0) == pytest.approx(25.0)
    # 05:00 to 07:00: halves average 25.5 and 27.0, mean 26.25.
    assert window_wbgt(HOURLY, MANILA_0400 + timedelta(hours=1), 7200.0) == pytest.approx(26.25)


def test_window_must_be_covered() -> None:
    with pytest.raises(ValueError):
        window_wbgt(HOURLY, MANILA_0400, 4 * 3600.0)
    with pytest.raises(ValueError):
        window_wbgt(
            [(MANILA_0400, 24.0), (MANILA_0400 + timedelta(hours=1), None)], MANILA_0400, 600.0
        )


def test_predict_for_window_uses_its_own_time_on_course() -> None:
    b = base(2 * 3600, 21.0975)
    p = predict_for_window(b, HOURLY, MANILA_0400)
    expected_w = window_wbgt(HOURLY, MANILA_0400, p.time_s)
    assert p.wbgt_race_c == pytest.approx(expected_w, abs=0.01)
    assert p.wbgt_race_c > window_wbgt(HOURLY, MANILA_0400, b.time_s)  # longer race, hotter window
