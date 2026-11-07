"""Write golden fixtures for the TypeScript parity tests.

Python is the reference. Each file under web/tests/golden/ holds inputs and the
Python outputs for one module, plus the tolerance the TypeScript port must meet
(docs/ARCHITECTURE.md section 4). Output is deterministic: no timestamps, no
random numbers, so a rerun on unchanged code gives identical files.

Usage:
    uv run python scripts/make_golden.py           # rewrite the fixtures
    uv run python scripts/make_golden.py --check   # fail if a fixture is stale
"""

from __future__ import annotations

import argparse
import dataclasses
import json
import math
import sys
from pathlib import Path
from typing import Any

import numpy as np

from blagden.physio.ectemp import ECTEMP_2013, ectemp_step, estimate_core_temp
from blagden.physio.psi import (
    DEFAULT_HR0_BPM,
    PSI_HR_CEILING_BPM,
    PSI_TC_CEILING_C,
    PSI_WEIGHT,
    psi,
)

OUT_DIR = Path(__file__).resolve().parents[1] / "web" / "tests" / "golden"
GENERATOR = "scripts/make_golden.py"


def to_json(values: Any) -> Any:
    """Turn arrays and floats into JSON values, with NaN as null."""
    if isinstance(values, np.ndarray):
        values = values.tolist()
    if isinstance(values, list):
        return [to_json(v) for v in values]
    if isinstance(values, float) and math.isnan(values):
        return None
    if isinstance(values, (bool, np.bool_)):
        return bool(values)
    return values


def marathon_trace() -> list[float]:
    """Return a 4-hour synthetic heart-rate trace built from a formula (no real run).

    Warm-up from 100 to 150 bpm over 15 minutes, then a slow drift of 0.08 bpm
    per minute with a 3 bpm wave every 20 minutes, a 4-minute dropout at
    minute 90 and a 2-minute dropout at minute 200.
    """
    hr: list[float] = []
    for m in range(240):
        if m < 15:
            value = 100.0 + 50.0 * m / 15.0
        else:
            value = 150.0 + 0.08 * (m - 15) + 3.0 * math.sin(2.0 * math.pi * m / 20.0)
        if 90 <= m < 94 or 200 <= m < 202:
            value = math.nan
        hr.append(round(value, 3))
    return hr


def series_case(name: str, hr: list[float], tc0: float, v0: float) -> dict[str, Any]:
    """Run the full filter and record inputs and outputs."""
    est = estimate_core_temp(hr, tc0=tc0, v0=v0)
    return {
        "name": name,
        "kind": "series",
        "inputs": {"hr_bpm": to_json(hr), "tc0_c": tc0, "v0_c2": v0},
        "expected": {
            "tc_c": to_json(est.tc_c),
            "var_c2": to_json(est.var_c2),
            "gain": to_json(est.gain),
            "observed": to_json(est.observed),
        },
    }


def step_case(name: str, tc_prev: float, v_prev: float, hr: float | None) -> dict[str, Any]:
    """Run one filter step and record inputs and outputs."""
    tc, v, k = ectemp_step(tc_prev, v_prev, hr)
    return {
        "name": name,
        "kind": "step",
        "inputs": {"tc_prev_c": tc_prev, "v_prev_c2": v_prev, "hr_bpm": hr},
        "expected": {"tc_c": tc, "var_c2": v, "gain": k},
    }


def ectemp_fixture() -> dict[str, Any]:
    """Build the ECTemp fixture."""
    gap = [140.0] * 10 + [math.nan] * 5 + [140.0] * 5
    return {
        "module": "ectemp",
        "generator": GENERATOR,
        "science": "docs/SCIENCE.md section 1",
        "params": dataclasses.asdict(ECTEMP_2013),
        "tolerance": {"tc_c": 1e-6, "var_c2": 1e-9, "gain": 1e-9},
        "cases": [
            step_case("hand_example_37.1_v0_hr150", 37.1, 0.0, 150.0),
            step_case("step_without_hr", 37.5, 0.01, None),
            step_case("step_at_model_peak_hr230", 42.0, 0.05, 230.0),
            series_case("steady_160_default_start_60min", [160.0] * 60, 37.0, 0.01),
            series_case("steady_60_default_start_60min", [60.0] * 60, 37.0, 0.01),
            series_case("gap_5min_at_140", gap, 37.0, 0.01),
            series_case("measured_start_37.4_v0_150", [150.0] * 30, 37.4, 0.0),
            series_case("range_low_30_for_6h", [30.0] * 360, 37.0, 0.01),
            series_case("range_high_230_for_6h", [230.0] * 360, 37.0, 0.01),
            series_case("synthetic_marathon_4h", marathon_trace(), 37.0, 0.01),
        ],
    }


def psi_case(name: str, tc: Any, hr: Any, tc0: float, hr0: float) -> dict[str, Any]:
    """Compute PSI and record inputs and outputs."""
    return {
        "name": name,
        "inputs": {"tc_c": to_json(tc), "hr_bpm": to_json(hr), "tc0_c": tc0, "hr0_bpm": hr0},
        "expected": {"psi": to_json(psi(tc, hr, tc0, hr0))},
    }


def psi_fixture() -> dict[str, Any]:
    """Build the PSI fixture."""
    trace = marathon_trace()
    tc = estimate_core_temp(trace).tc_c
    return {
        "module": "psi",
        "generator": GENERATOR,
        "science": "docs/SCIENCE.md section 3",
        "params": {
            "tc_ceiling_c": PSI_TC_CEILING_C,
            "hr_ceiling_bpm": PSI_HR_CEILING_BPM,
            "weight": PSI_WEIGHT,
            "default_hr0_bpm": DEFAULT_HR0_BPM,
        },
        "tolerance": {"psi": 1e-9},
        "cases": [
            psi_case("worked_38.5_150", [38.5], [150.0], 37.0, 70.0),
            psi_case("baseline_is_zero", [37.0], [70.0], 37.0, 70.0),
            psi_case("negative_clips_to_zero", [36.8], [60.0], 37.0, 70.0),
            psi_case("above_scale_kept", [40.0], [200.0], 37.0, 70.0),
            psi_case("missing_hr_is_null", [37.5, 37.6], [120.0, math.nan], 37.0, 70.0),
            psi_case("resting_hr_55", [38.2, 38.9], [150.0, 172.0], 37.0, 55.0),
            psi_case("synthetic_marathon_4h", tc, trace, 37.0, 70.0),
        ],
    }


FIXTURES = {"ectemp.json": ectemp_fixture, "psi.json": psi_fixture}


def render(data: dict[str, Any]) -> str:
    """Serialise one fixture. Python's float repr round-trips exactly."""
    return json.dumps(data, indent=1, allow_nan=False) + "\n"


def main(argv: list[str] | None = None) -> int:
    """Write the fixtures, or with --check report any that are stale."""
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--check", action="store_true", help="fail if a fixture is stale")
    args = parser.parse_args(argv)
    stale = []
    for name, build in FIXTURES.items():
        path = OUT_DIR / name
        text = render(build())
        if args.check:
            if not path.exists() or path.read_text(encoding="utf-8") != text:
                stale.append(name)
        else:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(text, encoding="utf-8")
            print(f"wrote {path.relative_to(OUT_DIR.parents[2])}")
    if stale:
        print(f"stale golden fixtures: {', '.join(stale)}; run scripts/make_golden.py")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
