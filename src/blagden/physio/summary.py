"""Per-run heat strain summary from one-minute heart rate.

Training insight, not medical advice. Every summary carries ``LIMITATION_NOTE``,
the statement docs/SCIENCE.md section 2 requires wherever a core temperature
estimate is shown.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from numpy.typing import ArrayLike

from blagden.physio.ectemp import DEFAULT_TC0_C, DEFAULT_V0_C2, estimate_core_temp
from blagden.physio.psi import DEFAULT_HR0_BPM, PSI_SCALE_MAX, psi

REPORT_THRESHOLD_C = 38.5
"""Display threshold for "minutes above", C. A reporting choice (D-022), not a safety
limit. It sits inside the 37.75 to 38.75 C range where de Korte et al. (2022) found the
method gives a representative indication (docs/SCIENCE.md section 2)."""

LIMITATION_NOTE = (
    "Core temperature is estimated from heart rate alone with the ECTemp method. "
    "In 101 elite athletes exercising in heat it agreed with measured core temperature "
    "within about +/- 0.45 C on average, but detected fewer than half of the readings "
    "above 39.0 C (de Korte et al. 2022). It is an indication of thermal strain, not a "
    "measurement, and not a basis for a safety decision."
)
"""Fixed text from docs/SCIENCE.md section 2, "What Blagden shows"."""


@dataclass(frozen=True)
class StrainSummary:
    """Heat strain figures for one run.

    ``start_tc_c`` is the filter's starting temperature (assumed unless the user
    measured it). Peaks are over the whole run. ``peak_psi`` is None when the
    run has no minute with heart rate.
    """

    minutes: int
    start_tc_c: float
    start_measured: bool
    peak_tc_c: float
    peak_minute: int
    minutes_above_threshold: int
    threshold_c: float
    peak_psi: float | None
    psi_above_scale: bool
    hr0_bpm: float
    hr0_defaulted: bool
    note: str


def summarize_strain(
    hr_bpm_per_min: ArrayLike,
    *,
    tc0: float | None = None,
    hr0: float | None = None,
) -> StrainSummary:
    """Run ECTemp and PSI over one run and summarise them.

    Parameters
    ----------
    hr_bpm_per_min
        One-minute mean heart rate, bpm, NaN where a minute has none.
    tc0
        Measured starting core temperature, C. When given the filter starts
        there with variance 0; otherwise at 37.0 C with variance 0.01 (D-012).
    hr0
        Resting heart rate, bpm. When None, 70 bpm is used and flagged (D-014).
    """
    start_measured = tc0 is not None
    start = float(tc0) if tc0 is not None else DEFAULT_TC0_C
    v0 = 0.0 if start_measured else DEFAULT_V0_C2
    hr_rest = float(hr0) if hr0 is not None else DEFAULT_HR0_BPM

    hr = np.asarray(hr_bpm_per_min, dtype=np.float64)
    est = estimate_core_temp(hr, tc0=start, v0=v0)
    if len(est) == 0:
        raise ValueError("the run has no minutes")
    strain = psi(est.tc_c, hr, start, hr_rest)
    has_psi = bool(np.isfinite(strain).any())
    peak_psi = float(np.nanmax(strain)) if has_psi else None
    peak_minute = int(np.argmax(est.tc_c))

    return StrainSummary(
        minutes=len(est),
        start_tc_c=start,
        start_measured=start_measured,
        peak_tc_c=float(est.tc_c[peak_minute]),
        peak_minute=peak_minute,
        minutes_above_threshold=int(np.count_nonzero(est.tc_c > REPORT_THRESHOLD_C)),
        threshold_c=REPORT_THRESHOLD_C,
        peak_psi=peak_psi,
        psi_above_scale=peak_psi is not None and peak_psi > PSI_SCALE_MAX,
        hr0_bpm=hr_rest,
        hr0_defaulted=hr0 is None,
        note=LIMITATION_NOTE,
    )
