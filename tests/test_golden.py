"""Python asserts the committed golden fixtures too, so no fixture is checked by one side only."""

from __future__ import annotations

import dataclasses
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


def _compare(got: dict[str, Any], expected: dict[str, Any], tol: dict[str, float]) -> None:
    for key, want in expected.items():
        have = got[key]
        if key in tol and want is not None and not isinstance(want, bool):
            assert_close(have, want, tol[key])
        else:
            assert jsonable_eq(have, want), key


def jsonable_eq(a: Any, b: Any) -> bool:
    if isinstance(a, tuple):
        a = list(a)
    if isinstance(a, list) and isinstance(b, list):
        return len(a) == len(b) and all(jsonable_eq(x, y) for x, y in zip(a, b, strict=True))
    return bool(a == b)


@pytest.mark.parametrize("case", load("solar.json")["cases"], ids=lambda c: c["name"])
def test_solar_reproduces_fixture(case: dict[str, Any]) -> None:
    from datetime import datetime

    from blagden.weather.solar import sun_position

    i = case["inputs"]
    p = sun_position(datetime.fromisoformat(i["time_utc"]), i["lat_deg"], i["lon_deg"])
    _compare(dataclasses.asdict(p), case["expected"], load("solar.json")["tolerance"])


@pytest.mark.parametrize("case", load("wbgt.json")["cases"], ids=lambda c: c["name"])
def test_wbgt_reproduces_fixture(case: dict[str, Any]) -> None:
    from blagden.weather.wbgt import outdoor_wbgt

    r = outdoor_wbgt(**case["inputs"])
    _compare(dataclasses.asdict(r), case["expected"], load("wbgt.json")["tolerance"])


@pytest.mark.parametrize("case", load("heat_index.json")["cases"], ids=lambda c: c["name"])
def test_heat_index_reproduces_fixture(case: dict[str, Any]) -> None:
    from blagden.weather.heat_index import heat_index_c, pagasa_category

    hi = heat_index_c(case["inputs"]["t_c"], case["inputs"]["rh_pct"])
    _compare({"hi_c": hi, "category": pagasa_category(hi).name}, case["expected"], {"hi_c": 1e-6})


@pytest.mark.parametrize("case", load("risk.json")["cases"], ids=lambda c: c["name"])
def test_risk_reproduces_fixture(case: dict[str, Any]) -> None:
    from blagden.weather.risk import risk_label

    r = risk_label(case["inputs"]["wbgt_c"], case["inputs"]["rh_pct"])
    _compare(dataclasses.asdict(r), case["expected"], load("risk.json")["tolerance"])


@pytest.mark.parametrize("case", load("ingest.json")["cases"], ids=lambda c: c["name"])
def test_ingest_reproduces_fixture(case: dict[str, Any]) -> None:
    from blagden.ingest import read_activity, resample_minutes

    table, report = read_activity(ROOT / case["inputs"]["path"])
    m = resample_minutes(table)
    exp = case["expected"]
    assert (report.rows_in, report.rows_out) == (exp["rows_in"], exp["rows_out"])
    assert report.rows_dropped == exp["rows_dropped"]
    assert report.values_removed == exp["values_removed"]
    assert m.n_samples.tolist() == exp["n_samples"] and m.has_hr.tolist() == exp["has_hr"]
    assert_close(m.hr_bpm, exp["hr_bpm"], 1e-9)
