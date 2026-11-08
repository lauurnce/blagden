/**
 * Outdoor WBGT with the Liljegren model (docs/SCIENCE.md section 4). Port of
 * blagden.weather.wbgt, itself a port of Liljegren's WBGT Version 1.1 C code.
 * This product includes software produced by UChicago Argonne, LLC under Contract
 * No. DE-AC02-06CH11357 with the Department of Energy.
 */

const SOLAR_CONST = 1367.0;
const STEFANB = 5.6696e-8;
const CP = 1003.5;
const M_AIR = 28.97;
const M_H2O = 18.015;
const R_GAS = 8314.34;
const R_AIR = R_GAS / M_AIR;
const RATIO = (CP * M_AIR) / M_H2O;
const PRANDTL = CP / (CP + 1.25 * R_AIR);
const EMIS_WICK = 0.95;
const ALB_WICK = 0.4;
const D_WICK = 0.007;
const L_WICK = 0.0254;
const EMIS_GLOBE = 0.95;
const ALB_GLOBE = 0.05;
const D_GLOBE = 0.0508;
const EMIS_SFC = 0.999;
const ALB_SFC = 0.45;
export const CZA_MIN = 0.00873;
const NORMSOLAR_MAX = 0.85;
const REF_HEIGHT = 2.0;
const MIN_SPEED = 0.13;
const CONVERGENCE = 0.02;
const MAX_ITER = 500;
const FDIR_MAX = 0.9;
const URBAN_EXP = [0.15, 0.15, 0.2, 0.25, 0.3, 0.3];
const RURAL_EXP = [0.07, 0.07, 0.1, 0.15, 0.35, 0.55];
const LSRDT = [
  [1, 1, 2, 4, 0, 5, 6, 0],
  [1, 2, 3, 4, 0, 5, 6, 0],
  [2, 2, 3, 4, 0, 4, 4, 0],
  [3, 3, 4, 4, 0, 0, 0, 0],
  [3, 4, 4, 4, 0, 0, 0, 0],
];
const VALID_RANGES: Record<string, [number, number]> = {
  t_air_c: [20, 45],
  rh_pct: [20, 100],
  pressure_hpa: [950, 1050],
  wind_mps: [0, 20],
  ghi_wm2: [0, 1200],
};

const esatHpa = (tK: number) =>
  1.004 * 6.1121 * Math.exp((17.502 * (tK - 273.15)) / (tK - 32.18));
function dewPointK(eHpa: number): number {
  const z = Math.log(eHpa / (6.1121 * 1.004));
  return 273.15 + (240.97 * z) / (17.502 - z);
}
function viscosity(tK: number): number {
  const sigma = 3.617;
  const omega = ((tK / 97.0 - 2.9) / 0.4) * -0.034 + 1.048;
  return (2.6693e-6 * Math.sqrt(M_AIR * tK)) / (sigma * sigma * omega);
}
const thermalCond = (tK: number) => (CP + 1.25 * R_AIR) * viscosity(tK);
function diffusivity(tK: number, pHpa: number): number {
  const pcrit13 = Math.pow(36.4 * 218.0, 1 / 3);
  const tcrit512 = Math.pow(132.0 * 647.3, 5 / 12);
  const tcrit12 = Math.sqrt(132.0 * 647.3);
  const mmix = Math.sqrt(1 / M_AIR + 1 / M_H2O);
  const pAtm = pHpa / 1013.25;
  return (
    ((3.64e-4 * Math.pow(tK / tcrit12, 2.334) * pcrit13 * tcrit512 * mmix) /
      pAtm) *
    1e-4
  );
}
const evap = (tK: number) => ((313.15 - tK) / 30.0) * -71100.0 + 2.4073e6;
const emisAtm = (tK: number, rh: number) =>
  0.575 * Math.pow(rh * esatHpa(tK), 0.143);
function hCylinder(
  d: number,
  l: number,
  tK: number,
  p: number,
  speed: number,
): number {
  const density = (p * 100) / (R_AIR * tK);
  const re = (Math.max(speed, MIN_SPEED) * density * d) / viscosity(tK);
  const nu = 0.281 * Math.pow(re, 1 - 0.4) * Math.pow(PRANDTL, 1 - 0.56);
  return (nu * thermalCond(tK)) / d;
}
function hSphere(d: number, tK: number, p: number, speed: number): number {
  const density = (p * 100) / (R_AIR * tK);
  const re = (Math.max(speed, MIN_SPEED) * density * d) / viscosity(tK);
  const nu = 2.0 + 0.6 * Math.sqrt(re) * Math.pow(PRANDTL, 0.3333);
  return (nu * thermalCond(tK)) / d;
}

/** Globe temperature, C, or null when the iteration does not converge. rh is a fraction. */
export function globeTempC(
  tC: number,
  rh: number,
  p: number,
  speed: number,
  solar: number,
  fdir: number,
  cza: number,
): number | null {
  const tK = tC + 273.15;
  let prev = tK;
  for (let i = 0; i < MAX_ITER; i++) {
    const tRef = 0.5 * (prev + tK);
    const h = hSphere(D_GLOBE, tRef, p, speed);
    const balance =
      0.5 * (emisAtm(tK, rh) * tK ** 4 + EMIS_SFC * tK ** 4) -
      (h / (STEFANB * EMIS_GLOBE)) * (prev - tK) +
      (solar / (2 * STEFANB * EMIS_GLOBE)) *
        (1 - ALB_GLOBE) *
        (fdir * (1 / (2 * cza) - 1) + 1 + ALB_SFC);
    if (!(balance > 0)) return null;
    const next = Math.pow(balance, 0.25);
    const converged = Math.abs(next - prev) < CONVERGENCE;
    prev = 0.9 * prev + 0.1 * next;
    if (converged) return next - 273.15;
  }
  return null;
}

/** Natural (radiative) or psychrometric wet bulb, C, or null. rh is a fraction. */
export function wetBulbC(
  tC: number,
  rh: number,
  p: number,
  speed: number,
  solar: number,
  fdir: number,
  cza: number,
  radiative = true,
): number | null {
  const tK = tC + 273.15;
  const sza = Math.acos(Math.max(-1, Math.min(1, cza)));
  const eAir = rh * esatHpa(tK);
  let prev = dewPointK(eAir);
  const radOn = radiative ? 1 : 0;
  for (let i = 0; i < MAX_ITER; i++) {
    const tRef = 0.5 * (prev + tK);
    const h = hCylinder(D_WICK, L_WICK, tRef, p, speed);
    const fAtm =
      STEFANB *
        EMIS_WICK *
        (0.5 * (emisAtm(tK, rh) * tK ** 4 + EMIS_SFC * tK ** 4) - prev ** 4) +
      (1 - ALB_WICK) *
        solar *
        ((1 - fdir) * (1 + (0.25 * D_WICK) / L_WICK) +
          fdir * (Math.tan(sza) / Math.PI + (0.25 * D_WICK) / L_WICK) +
          ALB_SFC);
    const eWick = esatHpa(prev);
    const density = (p * 100) / (R_AIR * tRef);
    const sc = viscosity(tRef) / (density * diffusivity(tRef, p));
    const next =
      tK -
      (((evap(tRef) / RATIO) * (eWick - eAir)) / (p - eWick)) *
        Math.pow(PRANDTL / sc, 0.56) +
      (fAtm / h) * radOn;
    const converged = Math.abs(next - prev) < CONVERGENCE;
    prev = 0.9 * prev + 0.1 * next;
    if (converged) return next - 273.15;
  }
  return null;
}

export function stabilityClass(
  daytime: boolean,
  speed: number,
  solar: number,
  dtC: number,
): number {
  let i: number;
  let j: number;
  if (daytime) {
    j = solar >= 925 ? 0 : solar >= 675 ? 1 : solar >= 175 ? 2 : 3;
    i = speed >= 6 ? 4 : speed >= 5 ? 3 : speed >= 3 ? 2 : speed >= 2 ? 1 : 0;
  } else {
    j = dtC >= 0 ? 6 : 5;
    i = speed >= 2.5 ? 2 : speed >= 2.0 ? 1 : 0;
  }
  return LSRDT[i]![j]!;
}

export function windAt2m(
  speed: number,
  heightM: number,
  stability: number,
  urban: boolean,
): number {
  const exponent = (urban ? URBAN_EXP : RURAL_EXP)[stability - 1]!;
  return Math.max(speed * Math.pow(REF_HEIGHT / heightM, exponent), MIN_SPEED);
}

export function limitSolar(
  solar: number,
  cza: number,
  distanceAu: number,
): number {
  const toa = (SOLAR_CONST * Math.max(0, cza)) / (distanceAu * distanceAu);
  if (cza < CZA_MIN || toa <= 0) return solar;
  return Math.min(solar / toa, NORMSOLAR_MAX) * toa;
}

export function directFraction(
  directWm2: number,
  diffuseWm2: number,
  cza: number,
): number {
  const total = directWm2 + diffuseWm2;
  if (cza < CZA_MIN || total <= 0) return 0;
  return Math.max(0, Math.min(directWm2 / total, FDIR_MAX));
}

export interface WbgtInputs {
  t_air_c: number;
  rh_pct: number;
  pressure_hpa: number;
  wind_mps: number;
  wind_height_m: number;
  ghi_wm2: number;
  direct_wm2: number;
  diffuse_wm2: number;
  cos_zenith: number;
  distance_au: number;
  urban: boolean;
  dt_c?: number;
}

export interface WbgtResult {
  wbgt_c: number | null;
  tg_c: number | null;
  tnwb_c: number | null;
  tpsy_c: number | null;
  t_air_c: number;
  wind2_mps: number;
  stability_class: number;
  fdir: number;
  cos_zenith: number;
  solar_wm2: number;
  flags: string[];
}

export function outdoorWbgt(x: WbgtInputs): WbgtResult {
  const flags: string[] = [];
  const values: Record<string, number> = {
    t_air_c: x.t_air_c,
    rh_pct: x.rh_pct,
    pressure_hpa: x.pressure_hpa,
    wind_mps: x.wind_mps,
    ghi_wm2: x.ghi_wm2,
  };
  for (const [name, [lo, hi]] of Object.entries(VALID_RANGES)) {
    const v = values[name]!;
    if (!(v >= lo && v <= hi)) flags.push(`${name}_out_of_range`);
  }
  const solar = limitSolar(x.ghi_wm2, x.cos_zenith, x.distance_au);
  const fdir = directFraction(x.direct_wm2, x.diffuse_wm2, x.cos_zenith);
  let k = 0;
  let wind2 = x.wind_mps;
  if (x.wind_height_m !== REF_HEIGHT) {
    k = stabilityClass(x.cos_zenith > 0, x.wind_mps, solar, x.dt_c ?? 0);
    wind2 = windAt2m(x.wind_mps, x.wind_height_m, k, x.urban);
  }
  const rh = 0.01 * x.rh_pct;
  const args = [
    x.t_air_c,
    rh,
    x.pressure_hpa,
    wind2,
    solar,
    fdir,
    x.cos_zenith,
  ] as const;
  const tg = globeTempC(...args);
  const tnwb = wetBulbC(...args, true);
  const tpsy = wetBulbC(...args, false);
  let wbgt: number | null = null;
  if (tg === null || tnwb === null) flags.push("not_converged");
  else wbgt = 0.1 * x.t_air_c + 0.2 * tg + 0.7 * tnwb;
  return {
    wbgt_c: wbgt,
    tg_c: tg,
    tnwb_c: tnwb,
    tpsy_c: tpsy,
    t_air_c: x.t_air_c,
    wind2_mps: wind2,
    stability_class: k,
    fdir,
    cos_zenith: x.cos_zenith,
    solar_wm2: solar,
    flags,
  };
}
