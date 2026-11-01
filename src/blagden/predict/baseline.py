"""Baseline finish-time predictors: Riegel, manual and PaceBrain (docs/SCIENCE.md section 6).

A baseline is a neutral-weather prediction; the heat adjustment in
``blagden.predict.heat`` is applied on top. The PaceBrain adapter is optional:
PaceBrain is imported only when used, and when it is not installed or has no
checkpoint, ``choose_baseline`` falls back to Riegel and says so in the
prediction's warnings.
"""

from __future__ import annotations

import importlib
import importlib.util
import math
from collections.abc import Mapping
from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal, Protocol

RIEGEL_EXPONENT = 1.06
"""Riegel (1981), American Scientist 69(3):285-290, b = 1.06 for the "endurance range";
formula and exponent read via a secondary source (SCIENCE.md section 6)."""

RIEGEL_RANGE_MIN = (3.5, 230.0)
"""Endurance range of the exponent, minutes (Riegel 1981 via SCIENCE.md section 6)."""

MARATHON_KM = 42.195

PACEBRAIN_DISTANCES_KM = (5.0, 10.0, 21.1, 42.2)
"""Race distances PaceBrain was trained on (ARCHITECTURE.md section 5.1)."""

PACEBRAIN_RANGES: dict[str, tuple[float, float]] = {
    "weekly_mileage_km": (20.0, 120.0),
    "avg_pace_min_per_km": (4.5, 7.5),
    "long_run_km": (10.0, 35.0),
    "days_since_long_run": (3.0, 21.0),
    "runs_per_week": (3.0, 7.0),
}
"""Training ranges checked by PaceBrain's own CLI (ARCHITECTURE.md section 5.1)."""

PACEBRAIN_CAUTION = (
    "PaceBrain is experimental: it is trained on synthetic data only, and its model card "
    "says not to use it to plan a real race."
)

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


class PaceBrainUnavailableError(RuntimeError):
    """PaceBrain is not installed or has no trained checkpoint."""


@dataclass(frozen=True)
class PaceBrainFeatures:
    """The training-load inputs PaceBrain needs (ARCHITECTURE.md section 5.3)."""

    weekly_mileage_km: float
    avg_pace_min_per_km: float
    long_run_km: float
    days_since_long_run: float = 7.0
    runs_per_week: float = 4.0


def pacebrain_distance(distance_km: float) -> float:
    """Map a race distance to PaceBrain's nearest trained distance, within 0.1 km."""
    for d in PACEBRAIN_DISTANCES_KM:
        if abs(distance_km - d) <= 0.1:
            return d
    raise ValueError(f"PaceBrain predicts only {PACEBRAIN_DISTANCES_KM} km")


@dataclass(frozen=True)
class PaceBrainPredictor:
    """Adapter for PaceBrain (github.com/lauurnce/pacebrain), imported lazily."""

    features: PaceBrainFeatures
    checkpoint_path: Path = Path("models/finish_predictor.pt")

    def predict(self, distance_km: float) -> BaselinePrediction:
        """Predict with PaceBrain. Raises PaceBrainUnavailableError when it cannot run."""
        if importlib.util.find_spec("pacebrain") is None:
            raise PaceBrainUnavailableError("PaceBrain is not installed")
        if not self.checkpoint_path.exists():
            raise PaceBrainUnavailableError(
                f"PaceBrain checkpoint not found at {self.checkpoint_path}"
            )
        trained_km = pacebrain_distance(distance_km)
        config = importlib.import_module("pacebrain.config")
        inference = importlib.import_module("pacebrain.inference")
        cfg = config.FinishPredictorConfig(checkpoint_path=str(self.checkpoint_path))
        model = inference.load_finish_model(cfg)
        scaler = inference.load_scaler(cfg)
        values = {
            "weekly_mileage_km": self.features.weekly_mileage_km,
            "avg_pace_min_per_km": self.features.avg_pace_min_per_km,
            "long_run_km": self.features.long_run_km,
            "days_since_long_run": self.features.days_since_long_run,
            "runs_per_week": self.features.runs_per_week,
        }
        minutes = float(
            inference.predict_finish_time(model, scaler, {**values, "race_distance_km": trained_km})
        )
        warnings = [PACEBRAIN_CAUTION]
        for name, (lo, hi) in PACEBRAIN_RANGES.items():
            if not lo <= values[name] <= hi:
                warnings.append(
                    f"{name} {values[name]:g} is outside PaceBrain's training range "
                    f"{lo:g} to {hi:g}"
                )
        return BaselinePrediction(
            distance_km=distance_km,
            time_s=minutes * 60.0,
            lo_s=None,
            hi_s=None,
            source="pacebrain",
            inputs={**values, "race_distance_km": trained_km},
            warnings=tuple(warnings),
        )


def choose_baseline(
    distance_km: float,
    *,
    known_distance_km: float | None = None,
    known_time_s: float | None = None,
    pacebrain: PaceBrainFeatures | None = None,
    checkpoint_path: Path | None = None,
    interval_fraction: float | None = None,
) -> BaselinePrediction:
    """Use PaceBrain when its inputs are given and it can run, otherwise Riegel.

    When PaceBrain was asked for but cannot run, the Riegel prediction carries a
    warning that says so. Raises ValueError when neither predictor has its inputs.
    """
    fallback_note: str | None = None
    if pacebrain is not None:
        predictor = PaceBrainPredictor(
            pacebrain, checkpoint_path or PaceBrainPredictor.checkpoint_path
        )
        try:
            return predictor.predict(distance_km)
        except PaceBrainUnavailableError as exc:
            fallback_note = f"{exc}; used Riegel instead"
    if known_distance_km is None or known_time_s is None:
        reason = f"{fallback_note}, but " if fallback_note else ""
        raise ValueError(f"{reason}a Riegel prediction needs a known race distance and time")
    pred = RiegelPredictor(
        known_distance_km, known_time_s, interval_fraction=interval_fraction
    ).predict(distance_km)
    if fallback_note:
        pred = BaselinePrediction(
            distance_km=pred.distance_km,
            time_s=pred.time_s,
            lo_s=pred.lo_s,
            hi_s=pred.hi_s,
            source=pred.source,
            inputs=pred.inputs,
            warnings=(fallback_note, *pred.warnings),
        )
    return pred
