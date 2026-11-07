"""Outdoor WBGT from forecast weather with the Liljegren model (docs/SCIENCE.md section 4).

A Python port of Liljegren's "WBGT, Version 1.1" C code, the reference
implementation of Liljegren et al. (2008). This product includes software
produced by UChicago Argonne, LLC under Contract No. DE-AC02-06CH11357 with
the Department of Energy. Changes from that code, noted as its licence asks:
the direct-beam fraction comes from the forecast's direct and diffuse
irradiance instead of the ratio to clear-sky irradiance (SCIENCE.md section 4),
a failure to converge returns None instead of -9999, and results carry flags
for inputs outside the stated valid ranges.

WBGT = 0.7 Tnwb + 0.2 Tg + 0.1 Ta. Temperatures in C unless a name ends in
``_k``; pressure in hPa (mb); wind in m/s; irradiance in W/m2.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field

# Physical constants (wbgt.h).
SOLAR_CONST = 1367.0
"""Solar constant used by the code, W/m2."""
STEFANB = 5.6696e-8
"""Stefan-Boltzmann constant as used in the code, W/(m2 K4)."""
CP = 1003.5
"""Specific heat of dry air at constant pressure, J/(kg K)."""
M_AIR = 28.97
"""Molecular weight of dry air, g/mol."""
M_H2O = 18.015
"""Molecular weight of water, g/mol."""
R_GAS = 8314.34
"""Universal gas constant, J/(kmol K)."""
R_AIR = R_GAS / M_AIR
RATIO = CP * M_AIR / M_H2O
PRANDTL = CP / (CP + 1.25 * R_AIR)

# Wick, globe and surface (wbgt.h; SCIENCE.md section 4 table).
EMIS_WICK = 0.95
ALB_WICK = 0.4
D_WICK = 0.007
L_WICK = 0.0254
EMIS_GLOBE = 0.95
ALB_GLOBE = 0.05
D_GLOBE = 0.0508
EMIS_SFC = 0.999
ALB_SFC = 0.45

# Computational limits (wbgt.h).
CZA_MIN = 0.00873
"""Cosine of 89.5 degrees; below it the sun is treated as down."""
NORMSOLAR_MAX = 0.85
"""Cap on irradiance over top-of-atmosphere irradiance."""
REF_HEIGHT = 2.0
"""Height the wind is converted to, m."""
MIN_SPEED = 0.13
"""Floor on wind speed, m/s."""
CONVERGENCE = 0.02
"""Iteration stop rule, K."""
MAX_ITER = 500
FDIR_MAX = 0.9
"""Upper clamp on the direct-beam fraction (code and thermofeel)."""

# Wind power-law exponents by stability class 1 to 6 (EPA-454/5-99-005 section 6.2.5).
URBAN_EXP = (0.15, 0.15, 0.20, 0.25, 0.30, 0.30)
RURAL_EXP = (0.07, 0.07, 0.10, 0.15, 0.35, 0.55)
# Stability class by wind row and solar or night column (stab_srdt).
_LSRDT = (
    (1, 1, 2, 4, 0, 5, 6, 0),
    (1, 2, 3, 4, 0, 5, 6, 0),
    (2, 2, 3, 4, 0, 4, 4, 0),
    (3, 3, 4, 4, 0, 0, 0, 0),
    (3, 4, 4, 4, 0, 0, 0, 0),
)

# Valid input ranges (SCIENCE.md section 4). Outside them a result is flagged.
VALID_RANGES = {
    "t_air_c": (20.0, 45.0),
    "rh_pct": (20.0, 100.0),
    "pressure_hpa": (950.0, 1050.0),
    "wind_mps": (0.0, 20.0),
    "ghi_wm2": (0.0, 1200.0),
}


def esat_hpa(t_k: float) -> float:
    """Saturation vapour pressure over water, hPa. Buck (1981) eqn 3, with the code's 1.004."""
    y = (t_k - 273.15) / (t_k - 32.18)
    return 1.004 * 6.1121 * math.exp(17.502 * y)


def dew_point_k(e_hpa: float) -> float:
    """Dew point for vapour pressure ``e_hpa``, K (inverse of ``esat_hpa``)."""
    z = math.log(e_hpa / (6.1121 * 1.004))
    return 273.15 + 240.97 * z / (17.502 - z)


def viscosity(t_k: float) -> float:
    """Viscosity of air, kg/(m s). Bird, Stewart and Lightfoot, page 23."""
    sigma, eps_kappa = 3.617, 97.0
    omega = (t_k / eps_kappa - 2.9) / 0.4 * (-0.034) + 1.048
    return 2.6693e-6 * math.sqrt(M_AIR * t_k) / (sigma * sigma * omega)


def thermal_cond(t_k: float) -> float:
    """Thermal conductivity of air, W/(m K). Bird, Stewart and Lightfoot, page 257."""
    return (CP + 1.25 * R_AIR) * viscosity(t_k)


def diffusivity(t_k: float, p_hpa: float) -> float:
    """Diffusivity of water vapour in air, m2/s. Bird, Stewart and Lightfoot, page 505."""
    pcrit13 = math.pow(36.4 * 218.0, 1.0 / 3.0)
    tcrit512 = math.pow(132.0 * 647.3, 5.0 / 12.0)
    tcrit12 = math.sqrt(132.0 * 647.3)
    mmix = math.sqrt(1.0 / M_AIR + 1.0 / M_H2O)
    p_atm = p_hpa / 1013.25
    return 3.640e-4 * math.pow(t_k / tcrit12, 2.334) * pcrit13 * tcrit512 * mmix / p_atm * 1e-4


def evap(t_k: float) -> float:
    """Heat of evaporation, J/kg, for 283 to 313 K. Van Wylen and Sonntag, Table A.1.1."""
    return (313.15 - t_k) / 30.0 * (-71100.0) + 2.4073e6


def emis_atm(t_k: float, rh: float) -> float:
    """Atmospheric emissivity. Oke (2nd edition), page 373. ``rh`` is a fraction."""
    return 0.575 * math.pow(rh * esat_hpa(t_k), 0.143)


def h_cylinder(diameter: float, length: float, t_k: float, p_hpa: float, speed: float) -> float:
    """Convective heat transfer, long cylinder in cross flow, W/(m2 K). Bedingfield and Drew."""
    a, b, c = 0.56, 0.281, 0.4
    density = p_hpa * 100.0 / (R_AIR * t_k)
    re = max(speed, MIN_SPEED) * density * diameter / viscosity(t_k)
    nu = b * math.pow(re, 1.0 - c) * math.pow(PRANDTL, 1.0 - a)
    return nu * thermal_cond(t_k) / diameter


def h_sphere(diameter: float, t_k: float, p_hpa: float, speed: float) -> float:
    """Convective heat transfer, sphere in air, W/(m2 K). Bird, Stewart and Lightfoot, page 409."""
    density = p_hpa * 100.0 / (R_AIR * t_k)
    re = max(speed, MIN_SPEED) * density * diameter / viscosity(t_k)
    nu = 2.0 + 0.6 * math.sqrt(re) * math.pow(PRANDTL, 0.3333)
    return nu * thermal_cond(t_k) / diameter


def globe_temp_c(
    t_c: float, rh: float, p_hpa: float, speed: float, solar: float, fdir: float, cza: float
) -> float | None:
    """Globe temperature, C, or None if the iteration does not converge. ``rh`` is a fraction."""
    t_k = t_c + 273.15
    t_sfc = t_k
    prev = t_k
    for _ in range(MAX_ITER):
        t_ref = 0.5 * (prev + t_k)
        h = h_sphere(D_GLOBE, t_ref, p_hpa, speed)
        balance = (
            0.5 * (emis_atm(t_k, rh) * t_k**4 + EMIS_SFC * t_sfc**4)
            - h / (STEFANB * EMIS_GLOBE) * (prev - t_k)
            + solar
            / (2.0 * STEFANB * EMIS_GLOBE)
            * (1.0 - ALB_GLOBE)
            * (fdir * (1.0 / (2.0 * cza) - 1.0) + 1.0 + ALB_SFC)
        )
        if not balance > 0.0:  # no physical solution; C pow would give NaN
            return None
        new = math.pow(balance, 0.25)
        converged = abs(new - prev) < CONVERGENCE
        prev = 0.9 * prev + 0.1 * new
        if converged:
            return new - 273.15
    return None


def wet_bulb_c(
    t_c: float,
    rh: float,
    p_hpa: float,
    speed: float,
    solar: float,
    fdir: float,
    cza: float,
    *,
    radiative: bool = True,
) -> float | None:
    """Natural wet bulb (``radiative=True``) or psychrometric wet bulb, C, or None.

    ``rh`` is a fraction. Without radiative heating the result is the
    psychrometric wet bulb.
    """
    a = 0.56  # Bedingfield and Drew
    t_k = t_c + 273.15
    t_sfc = t_k
    sza = math.acos(max(-1.0, min(1.0, cza)))
    e_air = rh * esat_hpa(t_k)
    prev = dew_point_k(e_air)
    rad = 1.0 if radiative else 0.0
    for _ in range(MAX_ITER):
        t_ref = 0.5 * (prev + t_k)
        h = h_cylinder(D_WICK, L_WICK, t_ref, p_hpa, speed)
        f_atm = STEFANB * EMIS_WICK * (
            0.5 * (emis_atm(t_k, rh) * t_k**4 + EMIS_SFC * t_sfc**4) - prev**4
        ) + (1.0 - ALB_WICK) * solar * (
            (1.0 - fdir) * (1.0 + 0.25 * D_WICK / L_WICK)
            + fdir * (math.tan(sza) / math.pi + 0.25 * D_WICK / L_WICK)
            + ALB_SFC
        )
        e_wick = esat_hpa(prev)
        density = p_hpa * 100.0 / (R_AIR * t_ref)
        sc = viscosity(t_ref) / (density * diffusivity(t_ref, p_hpa))
        new = (
            t_k
            - evap(t_ref) / RATIO * (e_wick - e_air) / (p_hpa - e_wick) * math.pow(PRANDTL / sc, a)
            + f_atm / h * rad
        )
        converged = abs(new - prev) < CONVERGENCE
        prev = 0.9 * prev + 0.1 * new
        if converged:
            return new - 273.15
    return None


def stability_class(daytime: bool, speed: float, solar: float, dt_c: float) -> int:
    """Pasquill-Gifford stability class 1 to 6 from the solar radiation and delta-T method.

    ``speed`` is the measured wind, ``solar`` the irradiance and ``dt_c`` the
    vertical temperature difference (upper minus lower), used only at night.
    """
    if daytime:
        j = 0 if solar >= 925.0 else 1 if solar >= 675.0 else 2 if solar >= 175.0 else 3
        if speed >= 6.0:
            i = 4
        elif speed >= 5.0:
            i = 3
        elif speed >= 3.0:
            i = 2
        elif speed >= 2.0:
            i = 1
        else:
            i = 0
    else:
        j = 6 if dt_c >= 0.0 else 5
        i = 2 if speed >= 2.5 else 1 if speed >= 2.0 else 0
    return _LSRDT[i][j]


def wind_at_2m(speed: float, height_m: float, stability: int, *, urban: bool) -> float:
    """Convert wind at ``height_m`` to 2 m with the power law, floored at ``MIN_SPEED``."""
    exponent = (URBAN_EXP if urban else RURAL_EXP)[stability - 1]
    return max(speed * math.pow(REF_HEIGHT / height_m, exponent), MIN_SPEED)


def limit_solar(solar: float, cza: float, distance_au: float) -> float:
    """Cap irradiance at ``NORMSOLAR_MAX`` of top-of-atmosphere, as the code does."""
    toa = SOLAR_CONST * max(0.0, cza) / (distance_au * distance_au)
    if cza < CZA_MIN or toa <= 0.0:
        return solar
    return min(solar / toa, NORMSOLAR_MAX) * toa


def direct_fraction(direct_wm2: float, diffuse_wm2: float, cza: float) -> float:
    """Direct-beam fraction from forecast components, clamped to 0..0.9 (SCIENCE.md 4)."""
    total = direct_wm2 + diffuse_wm2
    if cza < CZA_MIN or total <= 0.0:
        return 0.0
    return max(0.0, min(direct_wm2 / total, FDIR_MAX))


@dataclass(frozen=True)
class WbgtResult:
    """WBGT and its parts for one hour. Temperatures are None when not converged."""

    wbgt_c: float | None
    tg_c: float | None
    tnwb_c: float | None
    tpsy_c: float | None
    t_air_c: float
    wind2_mps: float
    stability_class: int
    fdir: float
    cos_zenith: float
    solar_wm2: float
    flags: tuple[str, ...] = field(default=())


def outdoor_wbgt(
    *,
    t_air_c: float,
    rh_pct: float,
    pressure_hpa: float,
    wind_mps: float,
    wind_height_m: float,
    ghi_wm2: float,
    direct_wm2: float,
    diffuse_wm2: float,
    cos_zenith: float,
    distance_au: float,
    urban: bool,
    dt_c: float = 0.0,
) -> WbgtResult:
    """Compute outdoor WBGT from one hour of forecast weather.

    ``cos_zenith`` and ``distance_au`` come from ``blagden.weather.solar`` for
    the same instant as the irradiance. ``dt_c`` is the night-time vertical
    temperature difference; forecasts do not provide it, and 0 (stable, as the
    code treats dT >= 0) is used. For urban venues both night classes give the
    same exponent, so the choice has no effect there.
    """
    flags = []
    values = {
        "t_air_c": t_air_c,
        "rh_pct": rh_pct,
        "pressure_hpa": pressure_hpa,
        "wind_mps": wind_mps,
        "ghi_wm2": ghi_wm2,
    }
    for name, value in values.items():
        lo, hi = VALID_RANGES[name]
        if not lo <= value <= hi:
            flags.append(f"{name}_out_of_range")
    solar = limit_solar(ghi_wm2, cos_zenith, distance_au)
    fdir = direct_fraction(direct_wm2, diffuse_wm2, cos_zenith)
    if wind_height_m != REF_HEIGHT:
        k = stability_class(cos_zenith > 0.0, wind_mps, solar, dt_c)
        wind2 = wind_at_2m(wind_mps, wind_height_m, k, urban=urban)
    else:
        k, wind2 = 0, wind_mps
    rh = 0.01 * rh_pct
    args = (t_air_c, rh, pressure_hpa, wind2, solar, fdir, cos_zenith)
    tg = globe_temp_c(*args)
    tnwb = wet_bulb_c(*args, radiative=True)
    tpsy = wet_bulb_c(*args, radiative=False)
    wbgt = None
    if tg is None or tnwb is None:
        flags.append("not_converged")
    else:
        wbgt = 0.1 * t_air_c + 0.2 * tg + 0.7 * tnwb
    return WbgtResult(
        wbgt_c=wbgt,
        tg_c=tg,
        tnwb_c=tnwb,
        tpsy_c=tpsy,
        t_air_c=t_air_c,
        wind2_mps=wind2,
        stability_class=k,
        fdir=fdir,
        cos_zenith=cos_zenith,
        solar_wm2=solar,
        flags=tuple(flags),
    )
