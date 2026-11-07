"""Tests for the per-run heat strain summary."""

from __future__ import annotations

import numpy as np
import pytest

from blagden.physio.ectemp import estimate_core_temp
from blagden.physio.psi import psi
from blagden.physio.summary import LIMITATION_NOTE, REPORT_THRESHOLD_C, summarize_strain


def test_summary_matches_filter_and_psi() -> None:
    hr = np.array([90.0] * 10 + [165.0] * 80 + [np.nan] * 5 + [120.0] * 10)
    s = summarize_strain(hr)
    tc = estimate_core_temp(hr).tc_c
    assert s.minutes == hr.size
    assert (s.start_tc_c, s.start_measured) == (37.0, False)
    assert s.peak_tc_c == tc.max()
    assert s.peak_minute == int(np.argmax(tc))
    assert s.minutes_above_threshold == int((tc > REPORT_THRESHOLD_C).sum()) > 0
    assert s.peak_psi == pytest.approx(float(np.nanmax(psi(tc, hr, 37.0, 70.0))))
    assert (s.hr0_bpm, s.hr0_defaulted) == (70.0, True)
    assert not s.psi_above_scale


def test_measured_start_and_resting_hr() -> None:
    s = summarize_strain([150.0] * 30, tc0=37.4, hr0=55.0)
    assert (s.start_tc_c, s.start_measured) == (37.4, True)
    assert (s.hr0_bpm, s.hr0_defaulted) == (55.0, False)
    est = estimate_core_temp([150.0] * 30, tc0=37.4, v0=0.0)
    assert s.peak_tc_c == est.tc_c.max()


def test_above_scale_flag() -> None:
    s = summarize_strain([200.0] * 240)
    assert s.peak_psi is not None and s.peak_psi > 10.0
    assert s.psi_above_scale


def test_run_without_hr_has_no_psi() -> None:
    s = summarize_strain([np.nan] * 5)
    assert s.peak_psi is None and s.minutes_above_threshold == 0
    assert s.peak_tc_c == 37.0


def test_empty_run_is_rejected() -> None:
    with pytest.raises(ValueError):
        summarize_strain([])


def test_note_states_the_39_c_limit() -> None:
    s = summarize_strain([140.0] * 3)
    assert s.note == LIMITATION_NOTE
    assert "above 39.0 C" in LIMITATION_NOTE and "de Korte et al. 2022" in LIMITATION_NOTE
