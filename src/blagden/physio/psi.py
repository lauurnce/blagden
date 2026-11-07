"""Physiological Strain Index from estimated core temperature (docs/SCIENCE.md section 3).

PSI = 5 (Tc - Tc0) / (39.5 - Tc0) + 5 (HR - HR0) / (180 - HR0), after Moran,
Shitzer and Pandolf (1998), on a scale where 0 is no strain and 10 is very
high strain. In Blagden ``tc`` is the ECTemp estimate, so the result is an
estimated PSI from heart rate and carries the limits of sections 1 and 2,
including low sensitivity above 39.0 C. No strain category labels are given
(D-014).
"""

from __future__ import annotations

import numpy as np
from numpy.typing import ArrayLike, NDArray

PSI_TC_CEILING_C = 39.5
"""Upper limit of core (rectal) temperature, C. Sun and Dong 2022; Buller USARIEM slides."""

PSI_HR_CEILING_BPM = 180.0
"""Upper limit of heart rate, bpm. Sun and Dong 2022; Buller USARIEM slides."""

PSI_WEIGHT = 5.0
"""Points given to each of the two terms. Notley et al. 2018."""

PSI_SCALE_MAX = 10.0
"""Top of the published 0 to 10 scale. Moran 1998 abstract."""

DEFAULT_HR0_BPM = 70.0
"""Resting heart rate used when the user gives none, bpm. Blagden convention (D-014),
the same fixed baseline as Bernard et al. 2026. Results that use it must say so."""


def psi(tc: ArrayLike, hr: ArrayLike, tc0: float, hr0: float) -> NDArray[np.float64]:
    """Compute the Physiological Strain Index for each minute.

    Parameters
    ----------
    tc
        Core temperature per minute, C (the ECTemp estimate in Blagden).
    hr
        Heart rate per minute, bpm. NaN marks a minute without heart rate.
    tc0
        Baseline core temperature, C: the filter's starting temperature.
    hr0
        Baseline (resting) heart rate, bpm. ``DEFAULT_HR0_BPM`` when unknown.

    Returns
    -------
    numpy.ndarray
        PSI per minute. NaN where ``tc`` or ``hr`` is NaN.

    Raises
    ------
    ValueError
        If a baseline is not finite or is at or above its ceiling, since the
        formula then divides by zero or changes sign.

    Notes
    -----
    Clipping follows docs/SCIENCE.md section 3. A negative total is reported
    as 0. Values above 10 are kept, not clamped: they occur whenever heart rate
    passes 180 bpm or the estimate passes 39.5 C, and callers show them as
    above scale (``value > PSI_SCALE_MAX``).
    """
    if not np.isfinite(tc0) or tc0 >= PSI_TC_CEILING_C:
        raise ValueError(f"tc0 must be a finite temperature below {PSI_TC_CEILING_C} C")
    if not np.isfinite(hr0) or hr0 >= PSI_HR_CEILING_BPM:
        raise ValueError(f"hr0 must be a finite heart rate below {PSI_HR_CEILING_BPM:g} bpm")
    tc_arr = np.asarray(tc, dtype=np.float64)
    hr_arr = np.asarray(hr, dtype=np.float64)
    thermal = PSI_WEIGHT * (tc_arr - tc0) / (PSI_TC_CEILING_C - tc0)
    cardio = PSI_WEIGHT * (hr_arr - hr0) / (PSI_HR_CEILING_BPM - hr0)
    total = np.asarray(thermal + cardio, dtype=np.float64)
    return np.where(np.isnan(total), np.nan, np.maximum(total, 0.0))
