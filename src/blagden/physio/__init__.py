"""Physiology estimates from heart rate. Training insight, not medical advice.

Core temperature is estimated from heart rate alone; the method is less
sensitive above 39.0 C (docs/SCIENCE.md section 2).
"""

from blagden.physio.ectemp import (
    DEFAULT_TC0_C,
    DEFAULT_V0_C2,
    ECTEMP_2013,
    CoreTempEstimate,
    EctempParams,
    ectemp_step,
    estimate_core_temp,
)
from blagden.physio.psi import DEFAULT_HR0_BPM, PSI_SCALE_MAX, psi
from blagden.physio.summary import (
    LIMITATION_NOTE,
    REPORT_THRESHOLD_C,
    StrainSummary,
    summarize_strain,
)

__all__ = [
    "DEFAULT_HR0_BPM",
    "DEFAULT_TC0_C",
    "DEFAULT_V0_C2",
    "ECTEMP_2013",
    "LIMITATION_NOTE",
    "PSI_SCALE_MAX",
    "REPORT_THRESHOLD_C",
    "CoreTempEstimate",
    "EctempParams",
    "StrainSummary",
    "ectemp_step",
    "estimate_core_temp",
    "psi",
    "summarize_strain",
]
