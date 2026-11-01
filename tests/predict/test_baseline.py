"""Baseline predictors: Riegel against SCIENCE.md section 6, manual, PaceBrain adapter."""

from __future__ import annotations

import sys
import types
from pathlib import Path

import pytest

from blagden.predict import baseline as b

SCIENCE_MD = Path(__file__).resolve().parents[2] / "docs" / "SCIENCE.md"


def test_exponent_matches_science() -> None:
    text = SCIENCE_MD.read_text(encoding="utf-8")
    assert r"\right)^{1.06}" in text and "$b$ = 1.06" in text
    assert b.RIEGEL_EXPONENT == 1.06
    assert "3.5 to 230 minutes" in text and b.RIEGEL_RANGE_MIN == (3.5, 230.0)


def test_riegel_formula_and_scaling() -> None:
    p = b.RiegelPredictor(21.1, 6600.0).predict(42.195)
    assert p.time_s == pytest.approx(6600.0 * (42.195 / 21.1) ** 1.06)
    assert p.source == "riegel" and p.lo_s is None and p.warnings == ()
    double = b.RiegelPredictor(21.1, 13200.0).predict(42.195)
    assert double.time_s == pytest.approx(2 * p.time_s)
    assert b.RiegelPredictor(10.0, 3000.0).predict(10.0).time_s == pytest.approx(3000.0)


def test_riegel_interval_is_a_declared_assumption() -> None:
    p = b.RiegelPredictor(10.0, 3000.0, interval_fraction=0.05).predict(21.1)
    assert p.lo_s == pytest.approx(0.95 * p.time_s) and p.hi_s == pytest.approx(1.05 * p.time_s)
    with pytest.raises(ValueError):
        b.RiegelPredictor(10.0, 3000.0, interval_fraction=1.5).predict(21.1)


def test_riegel_warns_outside_endurance_range() -> None:
    p = b.RiegelPredictor(42.195, 14400.0).predict(100.0)  # about 9.8 hours
    assert any("230 minute" in w for w in p.warnings)
    with pytest.raises(ValueError):
        b.riegel_time_s(0.0, 100.0, 10.0)


def test_manual_baseline() -> None:
    m = b.ManualBaseline(21.0975, 7200.0)
    assert m.predict(21.0975).source == "manual"
    with pytest.raises(ValueError):
        m.predict(42.195)


@pytest.fixture
def fake_pacebrain(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> Path:
    """Install a stand-in pacebrain package that returns 5 minutes per km."""
    seen: dict[str, object] = {}
    pkg = types.ModuleType("pacebrain")
    config = types.ModuleType("pacebrain.config")
    inference = types.ModuleType("pacebrain.inference")

    class Cfg:
        def __init__(self, checkpoint_path: str) -> None:
            seen["checkpoint"] = checkpoint_path

    def predict_finish_time(model: object, scaler: object, features: dict[str, float]) -> float:
        seen["features"] = features
        return 5.0 * features["race_distance_km"]

    config.FinishPredictorConfig = Cfg  # type: ignore[attr-defined]
    inference.load_finish_model = lambda cfg: "model"  # type: ignore[attr-defined]
    inference.load_scaler = lambda cfg: "scaler"  # type: ignore[attr-defined]
    inference.predict_finish_time = predict_finish_time  # type: ignore[attr-defined]
    for name, mod in (
        ("pacebrain", pkg),
        ("pacebrain.config", config),
        ("pacebrain.inference", inference),
    ):
        monkeypatch.setitem(sys.modules, name, mod)
    monkeypatch.setattr(b.importlib.util, "find_spec", lambda name: object())
    ckpt = tmp_path / "finish_predictor.pt"
    ckpt.write_bytes(b"x")
    return ckpt


def test_pacebrain_adapter(fake_pacebrain: Path) -> None:
    feats = b.PaceBrainFeatures(weekly_mileage_km=150.0, avg_pace_min_per_km=6.0, long_run_km=25.0)
    p = b.PaceBrainPredictor(feats, fake_pacebrain).predict(21.0975)
    assert p.source == "pacebrain" and p.time_s == pytest.approx(5.0 * 21.1 * 60.0)
    assert p.inputs["race_distance_km"] == 21.1
    assert p.warnings[0] == b.PACEBRAIN_CAUTION
    assert any("weekly_mileage_km 150" in w for w in p.warnings)
    with pytest.raises(ValueError):
        b.PaceBrainPredictor(feats, fake_pacebrain).predict(15.0)


def test_choose_prefers_pacebrain_when_it_runs(fake_pacebrain: Path) -> None:
    feats = b.PaceBrainFeatures(50.0, 6.0, 25.0)
    p = b.choose_baseline(10.0, pacebrain=feats, checkpoint_path=fake_pacebrain)
    assert p.source == "pacebrain"


def test_choose_falls_back_to_riegel_and_says_so(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(b.importlib.util, "find_spec", lambda name: None)
    feats = b.PaceBrainFeatures(50.0, 6.0, 25.0)
    p = b.choose_baseline(42.195, known_distance_km=21.1, known_time_s=6600.0, pacebrain=feats)
    assert p.source == "riegel"
    assert p.warnings[0] == "PaceBrain is not installed; used Riegel instead"


def test_choose_falls_back_when_checkpoint_missing(fake_pacebrain: Path, tmp_path: Path) -> None:
    feats = b.PaceBrainFeatures(50.0, 6.0, 25.0)
    p = b.choose_baseline(
        10.0, known_distance_km=5.0, known_time_s=1500.0, pacebrain=feats,
        checkpoint_path=tmp_path / "missing.pt",
    )  # fmt: skip
    assert p.source == "riegel" and "checkpoint not found" in p.warnings[0]


def test_choose_needs_some_inputs(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(b.importlib.util, "find_spec", lambda name: None)
    with pytest.raises(ValueError, match="not installed"):
        b.choose_baseline(10.0, pacebrain=b.PaceBrainFeatures(50.0, 6.0, 25.0))
    with pytest.raises(ValueError, match="known race"):
        b.choose_baseline(10.0)
