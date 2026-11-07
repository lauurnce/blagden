"""WBGT port against ECMWF thermofeel 2.3.0, a port of the Liljegren reference code.

thermofeel's ``thermofeel.liljegren`` solves the same globe and wet-bulb energy
balances with the same constants (docs/SCIENCE.md section 4). Stated tolerance:
1e-6 C, far inside the 0.1 C acceptance criterion in SCIENCE.md section 4 and
the model's own error of about 1 C. Both ports use the urban exponents here;
thermofeel has no rural set.
"""

from __future__ import annotations

import itertools
import math

import pytest

thermofeel = pytest.importorskip("thermofeel")
liljegren = pytest.importorskip("thermofeel.liljegren")

from blagden.weather.wbgt import (  # noqa: E402
    globe_temp_c,
    outdoor_wbgt,
    stability_class,
    wet_bulb_c,
    wind_at_2m,
)

TOL_C = 1e-6
P_HPA = 1008.0

GRID = list(
    itertools.product(
        (22.0, 26.0, 30.0, 34.0, 38.0),
        (0.4, 0.7, 0.95),
        (0.13, 0.5, 1.5, 4.0),
        (0.0, 200.0, 600.0, 1000.0),
        (0.0, 0.5, 0.9),
        (0.05, 0.3, 0.7, 1.0),
    )
)


def both_or_neither(mine: float | None, ref: float) -> bool:
    """Both ports fail to converge on the same inputs, or both give a value."""
    return (mine is None) == math.isnan(ref)


def test_globe_temperature_matches() -> None:
    worst = 0.0
    for t, rh, u, s, f, c in GRID:
        mine = globe_temp_c(t, rh, P_HPA, u, s, f, c)
        ref = float(liljegren.solve_globe(t + 273.15, rh, P_HPA, u, s, f, c))
        assert both_or_neither(mine, ref)
        if mine is not None:
            worst = max(worst, abs(mine - ref))
    assert worst <= TOL_C


@pytest.mark.parametrize("radiative", [True, False])
def test_wet_bulb_matches(radiative: bool) -> None:
    worst = 0.0
    for t, rh, u, s, f, c in GRID:
        mine = wet_bulb_c(t, rh, P_HPA, u, s, f, c, radiative=radiative)
        ref = float(
            liljegren.solve_wetbulb(t + 273.15, rh, P_HPA, u, s, f, c, 1.0 if radiative else 0.0)
        )
        assert both_or_neither(mine, ref)
        if mine is not None:
            worst = max(worst, abs(mine - ref))
    assert worst <= TOL_C


def test_wind_conversion_matches() -> None:
    for u, s, c in itertools.product(
        (0.62, 1.0, 2.0, 2.6, 3.0, 5.0, 6.0, 9.0), (0.0, 100.0, 200.0, 700.0, 950.0), (-0.3, 0.2)
    ):
        k = stability_class(c > 0.0, u, s, -0.1)  # thermofeel uses the dT < 0 night column
        assert wind_at_2m(u, 10.0, k, urban=True) == pytest.approx(
            float(liljegren.wind_speed_2m(u, c, s)), abs=1e-12
        )


def test_outdoor_wbgt_matches() -> None:
    for t, rh, u, s, c in itertools.product(
        (26.0, 30.0, 34.0), (60.0, 85.0), (0.7, 2.0, 5.0), (0.0, 300.0, 700.0), (0.2, 0.6, 0.95)
    ):
        r = outdoor_wbgt(
            t_air_c=t,
            rh_pct=rh,
            pressure_hpa=P_HPA,
            wind_mps=u,
            wind_height_m=10.0,
            ghi_wm2=s,
            direct_wm2=0.6 * s,
            diffuse_wm2=0.4 * s,
            cos_zenith=c,
            distance_au=1.0,
            urban=True,
            dt_c=-0.1,
        )
        ref = float(
            thermofeel.calculate_wbgt_liljegren(t + 273.15, rh, P_HPA, u, r.solar_wm2, r.fdir, c)
        )
        assert r.wbgt_c is not None
        assert r.wbgt_c == pytest.approx(ref - 273.15, abs=TOL_C)
