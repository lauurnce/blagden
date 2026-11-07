"""Tests for the Physiological Strain Index against docs/SCIENCE.md section 3."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest
from hypothesis import given
from hypothesis import strategies as st

from blagden.physio.psi import (
    DEFAULT_HR0_BPM,
    PSI_HR_CEILING_BPM,
    PSI_SCALE_MAX,
    PSI_TC_CEILING_C,
    PSI_WEIGHT,
    psi,
)

SCIENCE_MD = Path(__file__).resolve().parents[2] / "docs" / "SCIENCE.md"


def test_constants_match_science_table() -> None:
    text = SCIENCE_MD.read_text(encoding="utf-8")
    body = text[text.index("\n## 3.") : text.index("\n## 4.")]
    rows: dict[str, list[str]] = {}
    for line in body.splitlines():
        cells = [c.strip() for c in line.strip("|").split("|")]
        if line.startswith("| ") and len(cells) > 5:
            rows[cells[0]] = cells
    assert float(rows["39.5"][1]) == PSI_TC_CEILING_C
    assert float(rows["180"][1]) == PSI_HR_CEILING_BPM
    assert float(rows["5, 5"][1]) == PSI_WEIGHT
    for key in ("39.5", "180", "5, 5"):
        assert rows[key][-1].startswith("VERIFIED"), key
    assert "70 bpm" in body  # default resting heart rate convention


def test_worked_value() -> None:
    # 5 * (38.5 - 37.0) / (39.5 - 37.0) + 5 * (150 - 70) / (180 - 70) = 3 + 3.636364
    assert psi(38.5, 150.0, 37.0, 70.0) == pytest.approx(3.0 + 40.0 / 11.0, abs=1e-12)


def test_baseline_is_zero_and_ceilings_are_ten() -> None:
    assert psi(37.0, 70.0, 37.0, 70.0) == 0.0
    assert psi(39.5, 180.0, 37.0, 70.0) == pytest.approx(PSI_SCALE_MAX)


def test_negative_total_clips_to_zero() -> None:
    assert psi(36.8, 60.0, 37.0, 70.0) == 0.0


def test_above_scale_is_kept_not_clamped() -> None:
    value = float(psi(40.0, 200.0, 37.0, 70.0))
    assert value > PSI_SCALE_MAX
    assert value == pytest.approx(5 * 3.0 / 2.5 + 5 * 130.0 / 110.0)


def test_missing_hr_gives_nan() -> None:
    out = psi([37.5, 37.6], [120.0, np.nan], 37.0, DEFAULT_HR0_BPM)
    assert np.isfinite(out[0]) and np.isnan(out[1])


@pytest.mark.parametrize(("tc0", "hr0"), [(39.5, 70.0), (37.0, 180.0), (np.nan, 70.0)])
def test_rejects_baseline_at_or_above_ceiling(tc0: float, hr0: float) -> None:
    with pytest.raises(ValueError):
        psi(38.0, 150.0, tc0, hr0)


@given(
    tc=st.floats(36.0, 42.0),
    hr=st.floats(30.0, 230.0),
    dtc=st.floats(0.0, 2.0),
    dhr=st.floats(0.0, 50.0),
)
def test_never_decreases_with_tc_or_hr(tc: float, hr: float, dtc: float, dhr: float) -> None:
    low = float(psi(tc, hr, 37.0, 70.0))
    high = float(psi(tc + dtc, hr + dhr, 37.0, 70.0))
    assert 0.0 <= low <= high + 1e-12
