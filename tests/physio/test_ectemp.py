"""Tests for the ECTemp filter against docs/SCIENCE.md section 1."""

from __future__ import annotations

import math
import re
from pathlib import Path

import numpy as np
import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from blagden.physio.ectemp import (
    DEFAULT_TC0_C,
    DEFAULT_V0_C2,
    ECTEMP_2013,
    EctempParams,
    ectemp_step,
    estimate_core_temp,
)

SCIENCE_MD = Path(__file__).resolve().parents[2] / "docs" / "SCIENCE.md"


def steady_state_tc(hr_bpm: float, p: EctempParams = ECTEMP_2013) -> float:
    """Solve b2 CT^2 + b1 CT + b0 = HR on the rising branch."""
    a, b, c = p.b2, p.b1, p.b0 - hr_bpm
    roots = [(-b + s * math.sqrt(b * b - 4 * a * c)) / (2 * a) for s in (1, -1)]
    return min(roots)


def science_table(section: str, next_section: str) -> dict[str, list[str]]:
    """Return the parameter table rows of one SCIENCE.md section, keyed by symbol."""
    text = SCIENCE_MD.read_text(encoding="utf-8")
    body = text[text.index(f"\n## {section}") : text.index(f"\n## {next_section}")]
    table = body[body.index("### Parameters") :]
    rows: dict[str, list[str]] = {}
    for line in table.splitlines()[1:]:
        if line.startswith("### "):
            break
        if line.startswith("|") and not line.startswith("|---"):
            cells = [cell.strip() for cell in line.strip("|").split("|")]
            rows[cells[0]] = cells[1:]
    return rows


def test_parameters_match_science_table() -> None:
    rows = science_table("1.", "2.")
    expected = {
        r"$\gamma$": ECTEMP_2013.gamma,
        r"$b_0$": ECTEMP_2013.b0,
        r"$b_1$": ECTEMP_2013.b1,
        r"$b_2$": ECTEMP_2013.b2,
        r"$\sigma$": ECTEMP_2013.sigma,
    }
    for symbol, value in expected.items():
        assert float(rows[symbol][0]) == value, symbol
        assert rows[symbol][-1].startswith("VERIFIED"), symbol
    assert float(rows[r"$\gamma^2$"][0]) == pytest.approx(ECTEMP_2013.gamma**2, abs=1e-12)
    assert float(rows[r"$\sigma^2$"][0]) == pytest.approx(ECTEMP_2013.sigma**2, abs=1e-9)
    start = rows["$CT_0$, $v_0$ with no measurement"]
    tc0, v0 = (float(x) for x in re.split(r",\s*", start[0]))
    assert (tc0, v0) == (DEFAULT_TC0_C, DEFAULT_V0_C2)
    assert start[-1].startswith("VERIFIED")


def test_hand_worked_step_from_b3() -> None:
    # B3 teach-back: start 37.1 C with variance 0, one minute at 150 bpm.
    # Predict: v = 0 + 0.022^2 = 0.000484. Slope c = -9.1428 * 37.1 + 384.4286 = 45.23072.
    # Gain k = 0.000484 * 45.23072 / (45.23072^2 * 0.000484 + 356.4544) = 0.0000612449.
    # Expected HR at 37.1 C is 83.0866 bpm, so the residual is 66.9134 bpm.
    tc, v, k = ectemp_step(37.1, 0.0, 150.0)
    assert round(tc, 4) == 37.1041
    assert round(v, 7) == 0.0004827
    assert round(k, 7) == 0.0000612
    assert tc == pytest.approx(37.1040984872, abs=1e-9)
    assert v == pytest.approx(0.0004826592, abs=1e-9)
    assert k == pytest.approx(0.0000612449, abs=1e-9)


def test_series_first_minute_equals_step() -> None:
    est = estimate_core_temp([150.0], tc0=37.1, v0=0.0)
    assert (est.tc_c[0], est.var_c2[0], est.gain[0]) == ectemp_step(37.1, 0.0, 150.0)


@pytest.mark.parametrize(("hr", "spec_tc"), [(120.0, 38.0), (152.0, 39.0), (160.0, 39.3)])
def test_constant_hr_converges_to_observation_model(hr: float, spec_tc: float) -> None:
    target = steady_state_tc(hr)
    assert target == pytest.approx(spec_tc, abs=0.05)  # derived values in SCIENCE.md 1
    tc = estimate_core_temp(np.full(360, hr)).tc_c
    assert tc[-1] == pytest.approx(target, abs=0.01)
    # Above the baseline heart rate the estimate rises toward the target, never past it.
    assert np.all(np.diff(tc) >= 0.0)
    assert np.all(tc <= target + 1e-9)


def test_constant_low_hr_falls_toward_observation_model() -> None:
    baseline_hr = ECTEMP_2013.expected_hr(DEFAULT_TC0_C)  # about 78.5 bpm at 37.0 C
    hr = 60.0
    assert hr < baseline_hr
    target = steady_state_tc(hr)
    tc = estimate_core_temp(np.full(360, hr)).tc_c
    assert tc[-1] == pytest.approx(target, abs=0.01)
    assert np.all(np.diff(tc) <= 0.0)
    assert np.all(tc >= target - 1e-9)


def test_baseline_hr_holds_the_estimate() -> None:
    hr = ECTEMP_2013.expected_hr(DEFAULT_TC0_C)
    tc = estimate_core_temp(np.full(120, hr)).tc_c
    assert np.allclose(tc, DEFAULT_TC0_C, atol=1e-9)


hr_value = st.floats(min_value=30.0, max_value=230.0, allow_nan=False)


@settings(max_examples=200, deadline=None)
@given(
    data=st.lists(
        st.tuples(hr_value, st.floats(min_value=0.0, max_value=100.0), st.booleans()),
        min_size=1,
        max_size=240,
    )
)
def test_higher_hr_never_lowers_estimate(data: list[tuple[float, float, bool]]) -> None:
    low = np.array([hr if present else np.nan for hr, _, present in data])
    high = np.array([min(hr + bump, 230.0) if present else np.nan for hr, bump, present in data])
    tc_low = estimate_core_temp(low).tc_c
    tc_high = estimate_core_temp(high).tc_c
    assert np.all(tc_high >= tc_low - 1e-12)


def test_missing_minutes_grow_variance_and_hold_estimate() -> None:
    hr = np.array([140.0] * 10 + [np.nan] * 5 + [140.0] * 3)
    est = estimate_core_temp(hr)
    gap = slice(10, 15)
    assert not est.observed[gap].any()
    assert np.all(est.gain[gap] == 0.0)
    assert np.all(est.tc_c[gap] == est.tc_c[9])
    steps = np.diff(est.var_c2[9:15])
    assert np.allclose(steps, ECTEMP_2013.gamma**2, rtol=0, atol=1e-15)
    assert est.observed[15] and est.var_c2[15] < est.var_c2[14]


def test_all_missing_runs_time_update_only() -> None:
    est = estimate_core_temp([np.nan] * 4, tc0=37.0, v0=0.01)
    assert np.all(est.tc_c == 37.0)
    assert est.var_c2 == pytest.approx([0.01 + (i + 1) * ECTEMP_2013.gamma**2 for i in range(4)])


@settings(max_examples=100, deadline=None)
@given(
    data=st.lists(st.one_of(hr_value, st.just(math.nan)), min_size=360, max_size=360),
    tc0=st.floats(min_value=36.0, max_value=39.0),
)
def test_six_hours_of_any_valid_hr_stays_finite(data: list[float], tc0: float) -> None:
    with np.errstate(all="raise"):
        est = estimate_core_temp(data, tc0=tc0)
    assert np.all(np.isfinite(est.tc_c))
    assert np.all(np.isfinite(est.var_c2))
    assert np.all(est.var_c2 > 0.0)
    # Bounded by the steady states of 30 bpm and of the model peak (42.05 C).
    assert np.all(est.tc_c >= min(tc0, steady_state_tc(30.0)) - 1e-9)
    assert np.all(est.tc_c <= 42.05)


@pytest.mark.parametrize("hr", [30.0, 230.0])
def test_six_hours_at_range_ends(hr: float) -> None:
    with np.errstate(all="raise"):
        est = estimate_core_temp(np.full(360, hr))
    assert np.all(np.isfinite(est.tc_c)) and np.all(np.isfinite(est.var_c2))


@pytest.mark.parametrize(
    ("hr", "kwargs"),
    [
        ([[150.0]], {}),
        ([150.0, math.inf], {}),
        ([150.0], {"tc0": math.nan}),
        ([150.0], {"v0": -0.1}),
    ],
)
def test_rejects_bad_input(hr: object, kwargs: dict[str, float]) -> None:
    with pytest.raises(ValueError):
        estimate_core_temp(hr, **kwargs)  # type: ignore[arg-type]
