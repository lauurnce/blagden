/**
 * ECTemp extended Kalman filter for core temperature (docs/SCIENCE.md section 1).
 * Port of blagden.physio.ectemp; Python is the reference and the golden fixtures
 * in tests/golden/ectemp.json are the contract. The estimate is an indication of
 * thermal strain, not a measurement, and the method is less sensitive above 39.0 C.
 */

export interface EctempParams {
  /** Process noise SD, C per minute. US10702165B2; Hunt 2019. */
  gamma: number;
  /** Observation intercept, bpm. */
  b0: number;
  /** Observation linear term, bpm per C. */
  b1: number;
  /** Observation quadratic term, bpm per C squared. */
  b2: number;
  /** Observation noise SD, bpm. */
  sigma: number;
}

export const ECTEMP_2013: EctempParams = {
  gamma: 0.022,
  b0: -7887.1,
  b1: 384.4286,
  b2: -4.5714,
  sigma: 18.88,
};

/** Starting core temperature without a measurement, C (Hunt 2019; D-012). */
export const DEFAULT_TC0_C = 37.0;
/** Starting variance without a measurement, C squared (Hunt 2019; D-012). */
export const DEFAULT_V0_C2 = 0.01;

export function expectedHr(tcC: number, p: EctempParams = ECTEMP_2013): number {
  return p.b2 * tcC * tcC + p.b1 * tcC + p.b0;
}

/** One minute of the filter. A null or NaN heart rate runs the time update only. */
export function ectempStep(
  tcPrevC: number,
  vPrevC2: number,
  hrBpm: number | null,
  p: EctempParams = ECTEMP_2013,
): [tc: number, v: number, gain: number] {
  const tcPred = tcPrevC;
  const vPred = vPrevC2 + p.gamma * p.gamma;
  if (hrBpm === null || Number.isNaN(hrBpm)) return [tcPred, vPred, 0];
  const c = 2 * p.b2 * tcPred + p.b1;
  const gain = (vPred * c) / (c * c * vPred + p.sigma * p.sigma);
  const tc = tcPred + gain * (hrBpm - expectedHr(tcPred, p));
  const v = (1 - gain * c) * vPred;
  return [tc, v, gain];
}

export interface CoreTempEstimate {
  tcC: number[];
  varC2: number[];
  gain: number[];
  observed: boolean[];
  tc0C: number;
  v0C2: number;
}

/** Estimate core temperature for each minute from one-minute mean heart rate (NaN = missing). */
export function estimateCoreTemp(
  hrBpmPerMin: readonly (number | null)[],
  tc0 = DEFAULT_TC0_C,
  v0 = DEFAULT_V0_C2,
  p: EctempParams = ECTEMP_2013,
): CoreTempEstimate {
  if (!Number.isFinite(tc0))
    throw new Error("tc0 must be a finite temperature in C");
  if (!Number.isFinite(v0) || v0 < 0)
    throw new Error("v0 must be a finite variance of zero or more");
  const out: CoreTempEstimate = {
    tcC: [],
    varC2: [],
    gain: [],
    observed: [],
    tc0C: tc0,
    v0C2: v0,
  };
  let tc = tc0;
  let v = v0;
  for (const hr of hrBpmPerMin) {
    if (hr !== null && !Number.isNaN(hr) && !Number.isFinite(hr)) {
      throw new Error("heart rate must not contain infinite values");
    }
    const [t, vv, k] = ectempStep(tc, v, hr, p);
    tc = t;
    v = vv;
    out.tcC.push(t);
    out.varC2.push(vv);
    out.gain.push(k);
    out.observed.push(hr !== null && !Number.isNaN(hr));
  }
  return out;
}
