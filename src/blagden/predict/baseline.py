"""Baseline finish-time predictors: Riegel, manual and PaceBrain (docs/SCIENCE.md section 6).

A baseline is a neutral-weather prediction; the heat adjustment in
``blagden.predict.heat`` is applied on top.
"""

from __future__ import annotations

import math
from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Literal, Protocol

RIEGEL_EXPONENT = 1.06
"""Riegel (1981), American Scientist 69(3):285-290, b = 1.06 for the "endurance range";
formula and exponent read via a secondary source (SCIENCE.md section 6)."""

RIEGEL_RANGE_MIN = (3.5, 230.0)
"""Endurance range of the exponent, minutes (Riegel 1981 via SCIENCE.md section 6)."""

MARATHON_KM = 42.195

Source = Literal["riegel", "pacebrain", "manual"]


@dataclass(frozen=True)
class BaselinePrediction:
    """A neutral-weather finish time. Times in seconds."""

    distance_km: float
    time_s: float
    lo_s: float | None
    hi_s: float | None
    source: Source
    inputs: Mapping[str, float]
    warnings: tuple[str, ...] = field(default=())


class BaselinePredictor(Protocol):
    """Anything that predicts a neutral-weather time for a distance."""

    def predict(self, distance_km: float) -> BaselinePrediction:
        """Predict the finish time for ``distance_km``."""
        ...


def riegel_time_s(
    known_distance_km: float,
    known_time_s: float,
    distance_km: float,
    exponent: float = RIEGEL_EXPONENT,
) -> float:
    """Return T2 = T1 (D2 / D1) ** exponent, in seconds."""
    if known_distance_km <= 0 or known_time_s <= 0 or distance_km <= 0:
        raise ValueError("distances and times must be positive")
    return known_time_s * math.pow(distance_km / known_distance_km, exponent)


def _riegel_range_warnings(known_time_s: float, time_s: float) -> tuple[str, ...]:
    lo, hi = RIEGEL_RANGE_MIN
    out = []
    for label, t in (("known", known_time_s), ("predicted", time_s)):
        if not lo <= t / 60.0 <= hi:
            out.append(
                f"{label} time is outside Riegel's 3.5 to 230 minute endurance range; "
                "the exponent may not hold"
            )
    return tuple(out)


@dataclass(frozen=True)
class RiegelPredictor:
    """Riegel prediction from one known race.

    ``interval_fraction`` is a declared assumption, not a sourced value: Riegel
    publishes no uncertainty. None means no baseline interval.
    """

    known_distance_km: float
    known_time_s: float
    exponent: float = RIEGEL_EXPONENT
    interval_fraction: float | None = None

    def predict(self, distance_km: float) -> BaselinePrediction:
        """Predict with Riegel's formula."""
        t = riegel_time_s(self.known_distance_km, self.known_time_s, distance_km, self.exponent)
        lo = hi = None
        if self.interval_fraction is not None:
            if not 0.0 <= self.interval_fraction < 1.0:
                raise ValueError("interval_fraction must be in [0, 1)")
            lo, hi = t * (1.0 - self.interval_fraction), t * (1.0 + self.interval_fraction)
        inputs = {
            "known_distance_km": self.known_distance_km,
            "known_time_s": self.known_time_s,
            "exponent": self.exponent,
        }
        return BaselinePrediction(
            distance_km=distance_km,
            time_s=t,
            lo_s=lo,
            hi_s=hi,
            source="riegel",
            inputs=inputs,
            warnings=_riegel_range_warnings(self.known_time_s, t),
        )


@dataclass(frozen=True)
class ManualBaseline:
    """A time the runner or a coach supplies directly, for one distance."""

    distance_km: float
    time_s: float

    def predict(self, distance_km: float) -> BaselinePrediction:
        """Return the given time; only valid for the distance it was given for."""
        if abs(distance_km - self.distance_km) > 1e-9:
            raise ValueError("a manual baseline is only valid for the distance it was given for")
        return BaselinePrediction(
            distance_km=distance_km,
            time_s=self.time_s,
            lo_s=None,
            hi_s=None,
            source="manual",
            inputs={"time_s": self.time_s},
        )
