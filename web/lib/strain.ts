/**
 * Per-run heat strain summary (port of blagden.physio.summary) and minutes in each core
 * temperature zone. Training insight, not medical advice.
 */
import {
  DEFAULT_TC0_C,
  DEFAULT_V0_C2,
  estimateCoreTemp,
  type CoreTempEstimate,
} from "./ectemp";
import { DEFAULT_HR0_BPM, PSI_SCALE_MAX, psi } from "./psi";

/** Display threshold for "minutes above", C (D-022); not a safety limit. */
export const REPORT_THRESHOLD_C = 38.5;
/** Above this the heart-rate method detects fewer than half of readings (de Korte et al. 2022). */
export const SENSITIVITY_LIMIT_C = 39.0;

/** Fixed text from docs/SCIENCE.md section 2, "What Blagden shows". */
export const LIMITATION_NOTE =
  "Core temperature is estimated from heart rate alone with the ECTemp method. " +
  "In 101 elite athletes exercising in heat it agreed with measured core temperature " +
  "within about +/- 0.45 C on average, but detected fewer than half of the readings " +
  "above 39.0 C (de Korte et al. 2022). It is an indication of thermal strain, not a " +
  "measurement, and not a basis for a safety decision.";

export interface StrainSummary {
  minutes: number;
  start_tc_c: number;
  start_measured: boolean;
  peak_tc_c: number;
  peak_minute: number;
  minutes_above_threshold: number;
  threshold_c: number;
  peak_psi: number | null;
  psi_above_scale: boolean;
  hr0_bpm: number;
  hr0_defaulted: boolean;
  note: string;
}

export interface StrainResult {
  summary: StrainSummary;
  estimate: CoreTempEstimate;
  psi: (number | null)[];
}

export function summarizeStrain(
  hr: readonly (number | null)[],
  opts: { tc0?: number | null; hr0?: number | null } = {},
): StrainResult {
  if (hr.length === 0) throw new Error("the run has no minutes");
  const measured = opts.tc0 !== undefined && opts.tc0 !== null;
  const start = measured ? (opts.tc0 as number) : DEFAULT_TC0_C;
  const rest = opts.hr0 ?? DEFAULT_HR0_BPM;
  const est = estimateCoreTemp(hr, start, measured ? 0 : DEFAULT_V0_C2);
  const strain = psi(est.tcC, hr, start, rest);
  const valid = strain.filter((v): v is number => v !== null);
  const peakPsi = valid.length ? Math.max(...valid) : null;
  let peakMinute = 0;
  est.tcC.forEach((t, i) => {
    if (t > est.tcC[peakMinute]!) peakMinute = i;
  });
  return {
    estimate: est,
    psi: strain,
    summary: {
      minutes: hr.length,
      start_tc_c: start,
      start_measured: measured,
      peak_tc_c: est.tcC[peakMinute]!,
      peak_minute: peakMinute,
      minutes_above_threshold: est.tcC.filter((t) => t > REPORT_THRESHOLD_C)
        .length,
      threshold_c: REPORT_THRESHOLD_C,
      peak_psi: peakPsi,
      psi_above_scale: peakPsi !== null && peakPsi > PSI_SCALE_MAX,
      hr0_bpm: rest,
      hr0_defaulted: opts.hr0 === undefined || opts.hr0 === null,
      note: LIMITATION_NOTE,
    },
  };
}

export interface ZoneMinutes {
  label: string;
  description: string;
  minutes: number;
}

/** Minutes of estimated core temperature in each display zone (thresholds from D-022 and SCIENCE.md 2). */
export function zoneMinutes(tcC: readonly number[]): ZoneMinutes[] {
  const below = tcC.filter((t) => t <= REPORT_THRESHOLD_C).length;
  const mid = tcC.filter(
    (t) => t > REPORT_THRESHOLD_C && t <= SENSITIVITY_LIMIT_C,
  ).length;
  const high = tcC.filter((t) => t > SENSITIVITY_LIMIT_C).length;
  return [
    {
      label: "38.5 C or below",
      description: "at or below the summary threshold",
      minutes: below,
    },
    {
      label: "38.5 to 39.0 C",
      description: "above the summary threshold",
      minutes: mid,
    },
    {
      label: "above 39.0 C",
      description: "the method is less sensitive here; readings may be missed",
      minutes: high,
    },
  ];
}
