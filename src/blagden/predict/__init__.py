"""Baseline finish-time predictors and the heat adjustment (docs/SCIENCE.md section 6).

Training insight, not a race plan. Every heat-adjusted time comes with its range.
"""

from blagden.predict.baseline import (
    BaselinePrediction,
    BaselinePredictor,
    ManualBaseline,
    PaceBrainFeatures,
    PaceBrainPredictor,
    PaceBrainUnavailableError,
    RiegelPredictor,
    choose_baseline,
)
from blagden.predict.heat import (
    HeatAdjustedPrediction,
    format_hms,
    heat_adjust,
    predict_for_window,
    runner_level,
    window_wbgt,
)

__all__ = [
    "BaselinePrediction",
    "BaselinePredictor",
    "HeatAdjustedPrediction",
    "ManualBaseline",
    "PaceBrainFeatures",
    "PaceBrainPredictor",
    "PaceBrainUnavailableError",
    "RiegelPredictor",
    "choose_baseline",
    "format_hms",
    "heat_adjust",
    "predict_for_window",
    "runner_level",
    "window_wbgt",
]
