"""Python asserts the committed golden fixtures too, so no fixture is checked by one side only."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from typing import Any

import numpy as np
import pytest

from blagden.physio.ectemp import ectemp_step, estimate_core_temp
from blagden.physio.psi import psi

ROOT = Path(__file__).resolve().parents[1]
GOLDEN = ROOT / "web" / "tests" / "golden"


def load(name: str) -> dict[str, Any]:
    data: dict[str, Any] = json.loads((GOLDEN / name).read_text(encoding="utf-8"))
    return data


def as_array(values: list[float | None]) -> np.ndarray:
    return np.array([np.nan if v is None else v for v in values], dtype=np.float64)


def assert_close(actual: Any, expected: Any, tol: float) -> None:
    a = np.atleast_1d(np.asarray(actual, dtype=np.float64))
    e = np.atleast_1d(as_array(expected) if isinstance(expected, list) else np.float64(expected))
    np.testing.assert_allclose(a, e, rtol=0, atol=tol, equal_nan=True)


ECTEMP = load("ectemp.json")
PSI = load("psi.json")


@pytest.mark.parametrize("case", ECTEMP["cases"], ids=lambda c: c["name"])
def test_ectemp_reproduces_fixture(case: dict[str, Any]) -> None:
    tol = ECTEMP["tolerance"]
    inp, exp = case["inputs"], case["expected"]
    if case["kind"] == "step":
        tc, v, k = ectemp_step(inp["tc_prev_c"], inp["v_prev_c2"], inp["hr_bpm"])
        got = {"tc_c": tc, "var_c2": v, "gain": k}
    else:
        est = estimate_core_temp(as_array(inp["hr_bpm"]), tc0=inp["tc0_c"], v0=inp["v0_c2"])
        got = {"tc_c": est.tc_c, "var_c2": est.var_c2, "gain": est.gain}
        assert est.observed.tolist() == exp["observed"]
    for field, value in got.items():
        assert_close(value, exp[field], tol[field])


@pytest.mark.parametrize("case", PSI["cases"], ids=lambda c: c["name"])
def test_psi_reproduces_fixture(case: dict[str, Any]) -> None:
    inp = case["inputs"]
    got = psi(as_array(inp["tc_c"]), as_array(inp["hr_bpm"]), inp["tc0_c"], inp["hr0_bpm"])
    assert_close(got, case["expected"]["psi"], PSI["tolerance"]["psi"])


def test_hand_example_matches_spec_values() -> None:
    case = next(c for c in ECTEMP["cases"] if c["name"] == "hand_example_37.1_v0_hr150")
    assert case["expected"]["tc_c"] == pytest.approx(37.1040984872, abs=1e-9)


def test_fixtures_are_current() -> None:
    script = ROOT / "scripts" / "make_golden.py"
    result = subprocess.run(
        [sys.executable, str(script), "--check"], capture_output=True, text=True, check=False
    )
    assert result.returncode == 0, result.stdout + result.stderr
