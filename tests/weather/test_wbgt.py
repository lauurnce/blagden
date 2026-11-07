"""WBGT port: constants against docs/SCIENCE.md section 4 and model behaviour."""

from __future__ import annotations

from pathlib import Path

import pytest

from blagden.weather import wbgt as w

SCIENCE_MD = Path(__file__).resolve().parents[2] / "docs" / "SCIENCE.md"


def section_4() -> str:
    text = SCIENCE_MD.read_text(encoding="utf-8")
    return text[text.index("\n## 4.") : text.index("\n## 5.")]


def test_constants_match_science_table() -> None:
    rows: dict[str, list[str]] = {}
    for line in section_4().splitlines():
        cells = [c.strip() for c in line.strip("|").split("|")]
        if line.startswith("| ") and len(cells) == 6:
            rows[cells[0]] = cells
    expected = {
        "EMIS_WICK": w.EMIS_WICK,
        "ALB_WICK": w.ALB_WICK,
        "D_WICK": w.D_WICK,
        "L_WICK": w.L_WICK,
        "EMIS_GLOBE": w.EMIS_GLOBE,
        "ALB_GLOBE": w.ALB_GLOBE,
        "D_GLOBE": w.D_GLOBE,
        "EMIS_SFC": w.EMIS_SFC,
        "ALB_SFC": w.ALB_SFC,
        "STEFANB": w.STEFANB,
        "MIN_SPEED": w.MIN_SPEED,
        "REF_HEIGHT": w.REF_HEIGHT,
        "CZA_MIN": w.CZA_MIN,
        "NORMSOLAR_MAX": w.NORMSOLAR_MAX,
    }
    for name, value in expected.items():
        assert float(rows[name][1]) == value, name
        assert rows[name][-1].startswith("VERIFIED"), name
    conv, iters = rows["CONVERGENCE, MAX_ITER"][1].split(",")
    assert (float(conv), int(iters)) == (w.CONVERGENCE, w.MAX_ITER)
    assert rows["direct fraction clamp"][1] == f"0 to {w.FDIR_MAX}"


def test_wind_exponents_match_science_text() -> None:
    text = section_4()
    urban = "{" + ", ".join(f"{x:.2f}" for x in w.URBAN_EXP) + "}"
    rural = "{" + ", ".join(f"{x:.2f}" for x in w.RURAL_EXP) + "}"
    assert f"urban {urban}" in text and f"rural {rural}" in text


def test_wbgt_is_the_weighted_sum() -> None:
    r = w.outdoor_wbgt(
        t_air_c=31.0, rh_pct=70.0, pressure_hpa=1008.0, wind_mps=2.0, wind_height_m=10.0,
        ghi_wm2=600.0, direct_wm2=400.0, diffuse_wm2=200.0, cos_zenith=0.7, distance_au=0.99,
        urban=True,
    )  # fmt: skip
    assert r.wbgt_c is not None and r.tg_c is not None and r.tnwb_c is not None
    assert r.wbgt_c == pytest.approx(0.7 * r.tnwb_c + 0.2 * r.tg_c + 0.1 * 31.0, abs=1e-12)
    assert r.tg_c > 31.0 > r.tnwb_c  # sun heats the globe; evaporation cools the wick
    assert r.flags == ()


def test_without_sun_natural_wet_bulb_is_near_psychrometric() -> None:
    # SCIENCE.md 4: with no solar radiation the natural wet bulb is close to the
    # psychrometric wet bulb; the remaining difference is long-wave exchange.
    r = w.outdoor_wbgt(
        t_air_c=27.0, rh_pct=85.0, pressure_hpa=1008.0, wind_mps=1.5, wind_height_m=10.0,
        ghi_wm2=0.0, direct_wm2=0.0, diffuse_wm2=0.0, cos_zenith=-0.2, distance_au=0.99,
        urban=True,
    )  # fmt: skip
    assert r.tnwb_c is not None and r.tpsy_c is not None
    assert abs(r.tnwb_c - r.tpsy_c) < 0.1
    assert r.fdir == 0.0


def test_more_sun_never_lowers_wbgt() -> None:
    values = []
    for ghi in (0.0, 200.0, 400.0, 600.0, 800.0):
        r = w.outdoor_wbgt(
            t_air_c=30.0, rh_pct=75.0, pressure_hpa=1008.0, wind_mps=2.0, wind_height_m=10.0,
            ghi_wm2=ghi, direct_wm2=0.7 * ghi, diffuse_wm2=0.3 * ghi, cos_zenith=0.8,
            distance_au=0.99, urban=True,
        )  # fmt: skip
        assert r.wbgt_c is not None
        values.append(r.wbgt_c)
    assert values == sorted(values)


def test_direct_fraction_rules() -> None:
    assert w.direct_fraction(950.0, 50.0, 0.8) == w.FDIR_MAX
    assert w.direct_fraction(300.0, 300.0, 0.8) == pytest.approx(0.5)
    assert w.direct_fraction(300.0, 300.0, 0.005) == 0.0  # sun below 89.5 degrees zenith
    assert w.direct_fraction(0.0, 0.0, 0.5) == 0.0


def test_irradiance_cap() -> None:
    toa = w.SOLAR_CONST * 0.5
    assert w.limit_solar(2000.0, 0.5, 1.0) == pytest.approx(w.NORMSOLAR_MAX * toa)
    assert w.limit_solar(300.0, 0.5, 1.0) == pytest.approx(300.0)
    assert w.limit_solar(5.0, 0.0, 1.0) == 5.0  # sun down: left as given, like the code


def test_night_stability_matters_only_for_rural() -> None:
    stable = w.stability_class(False, 1.0, 0.0, 0.0)
    unstable = w.stability_class(False, 1.0, 0.0, -0.1)
    assert (stable, unstable) == (6, 5)
    assert w.wind_at_2m(3.0, 10.0, stable, urban=True) == w.wind_at_2m(
        3.0, 10.0, unstable, urban=True
    )
    assert w.wind_at_2m(3.0, 10.0, stable, urban=False) < w.wind_at_2m(
        3.0, 10.0, unstable, urban=False
    )


def test_wind_floor_and_reference_height() -> None:
    assert w.wind_at_2m(0.0, 10.0, 4, urban=True) == w.MIN_SPEED
    r = w.outdoor_wbgt(
        t_air_c=30.0, rh_pct=70.0, pressure_hpa=1008.0, wind_mps=1.7, wind_height_m=2.0,
        ghi_wm2=0.0, direct_wm2=0.0, diffuse_wm2=0.0, cos_zenith=-0.1, distance_au=1.0,
        urban=True,
    )  # fmt: skip
    assert r.wind2_mps == 1.7 and r.stability_class == 0


def test_out_of_range_inputs_are_flagged() -> None:
    r = w.outdoor_wbgt(
        t_air_c=18.0, rh_pct=15.0, pressure_hpa=1008.0, wind_mps=2.0, wind_height_m=10.0,
        ghi_wm2=0.0, direct_wm2=0.0, diffuse_wm2=0.0, cos_zenith=-0.1, distance_au=1.0,
        urban=True,
    )  # fmt: skip
    assert "t_air_c_out_of_range" in r.flags and "rh_pct_out_of_range" in r.flags


def test_non_convergence_gives_no_value(monkeypatch: pytest.MonkeyPatch) -> None:
    # Uncapped 1000 W/m2 with the sun 3 degrees up and calm air has no solution.
    assert w.wet_bulb_c(22.0, 0.4, 1008.0, 0.13, 1000.0, 0.9, 0.05) is None
    monkeypatch.setattr(w, "wet_bulb_c", lambda *a, **k: None)
    r = w.outdoor_wbgt(
        t_air_c=30.0, rh_pct=70.0, pressure_hpa=1008.0, wind_mps=2.0, wind_height_m=10.0,
        ghi_wm2=0.0, direct_wm2=0.0, diffuse_wm2=0.0, cos_zenith=-0.1, distance_au=1.0,
        urban=True,
    )  # fmt: skip
    assert r.wbgt_c is None and "not_converged" in r.flags
