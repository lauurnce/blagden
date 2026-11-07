"""ECTemp extended Kalman filter for core temperature (docs/SCIENCE.md section 1).

Core temperature is estimated minute by minute from one-minute mean heart rate
with the quadratic observation model of Buller et al. (2013). The estimate is an
indication of thermal strain, not a measurement. The heart-rate method is less
sensitive above 39.0 C (de Korte et al. 2022, docs/SCIENCE.md section 2).

Units: core temperature in degrees Celsius, variance in degrees Celsius squared,
heart rate in beats per minute, one step per minute.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from numpy.typing import NDArray

FloatArray = NDArray[np.float64]


@dataclass(frozen=True)
class EctempParams:
    """Parameters of the 2013 quadratic ECTemp model.

    Every value is from docs/SCIENCE.md section 1, read from US patent
    US10702165B2 (which reproduces the 2013 model text and MATLAB appendix)
    and Hunt et al. (2019), and tagged VERIFIED there. The time update is the
    identity (a1 = 1, a0 = 0), so it has no field.
    """

    gamma: float = 0.022
    """Process noise standard deviation, C per minute. US10702165B2; Hunt 2019."""

    b0: float = -7887.1
    """Observation intercept, bpm. US10702165B2; Hunt 2019."""

    b1: float = 384.4286
    """Observation linear term, bpm per C. US10702165B2; Hunt 2019."""

    b2: float = -4.5714
    """Observation quadratic term, bpm per C squared. US10702165B2; Hunt 2019."""

    sigma: float = 18.88
    """Observation noise standard deviation, bpm. US10702165B2; Hunt 2019."""

    def expected_hr(self, tc_c: float) -> float:
        """Heart rate the observation model expects at core temperature ``tc_c``."""
        return self.b2 * tc_c * tc_c + self.b1 * tc_c + self.b0


ECTEMP_2013 = EctempParams()
"""The published 2013 parameter set."""

DEFAULT_TC0_C = 37.0
"""Starting core temperature without a measurement, C. Hunt 2019; D-012."""

DEFAULT_V0_C2 = 0.01
"""Starting variance without a measurement, C squared. Hunt 2019; D-012."""
