"""Tests for the ECTemp filter against docs/SCIENCE.md section 1."""

from __future__ import annotations

import math
import re
from pathlib import Path

import numpy as np
import pytest

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
