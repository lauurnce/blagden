/**
 * WBGT risk labels (docs/SCIENCE.md section 5, D-017). Port of blagden.weather.risk.
 * Training insight, not a go or no-go decision.
 */

export type Flag = "white" | "green" | "yellow" | "red" | "black";
export type RacinaisLevel =
  "below moderate" | "moderate" | "high" | "excessive";

export const WBGT_MODEL_ERROR_C = 1.0;

export const FLAG_MEANINGS: Record<Flag, string> = {
  white: "Generally safe; EHS can occur associated with individual factors",
  green: "Risk low but still exists on the basis of risk factors",
  yellow: "Risk increases as event progresses through the day",
  red: "Everyone should be aware of injury potential; individuals at risk should not compete",
  black:
    "Consider rescheduling or delaying the event until safer conditions prevail; if the event must take place, be on high alert",
};

const ACSM_2007_ROWS: [number, string][] = [
  [10.0, "Generally safe; EHS can occur associated with individual factors"],
  [18.3, "Generally safe; EHS can occur"],
  [
    22.2,
    "Risk of EHS and other heat illness begins to rise; high-risk individuals should be monitored or not compete",
  ],
  [25.6, "Risk for all competitors is increased"],
  [27.8, "Risk for unfit, nonacclimatized individuals is high"],
  [30.0, "Cancel level for EHS risk"],
];

const RACINAIS_RH = [50, 75, 100];
const RACINAIS: Record<
  "moderate" | "high" | "excessive",
  [number, number, number]
> = {
  moderate: [24, 20, 18],
  high: [28, 26, 24],
  excessive: [33, 29, 28],
};

export function flagFor(w: number): Flag {
  if (w < 10) return "white";
  if (w < 18) return "green";
  if (w < 23) return "yellow";
  if (w <= 28) return "red";
  return "black";
}

export function wa2020Band(w: number): string {
  if (w < 21) return "Almost Safe";
  if (w < 25) return "Caution";
  if (w < 28) return "Warning";
  if (w <= 30) return "Severe Warning";
  return "Danger";
}

/** Python round() is round-half-even; WBGT rounded to 0.1 C the same way. */
function roundHalfEven1(x: number): number {
  const scaled = x * 10;
  const floor = Math.floor(scaled);
  const diff = scaled - floor;
  let r: number;
  if (Math.abs(diff - 0.5) < 1e-9) r = floor % 2 === 0 ? floor : floor + 1;
  else r = Math.round(scaled);
  return r / 10;
}

export function acsm2007Text(w: number): string | null {
  const v = roundHalfEven1(w);
  for (const [upper, text] of ACSM_2007_ROWS) if (v <= upper) return text;
  return null;
}

export function racinaisThresholds(
  rhPct: number,
): [[number, number, number], boolean] {
  const clamped = rhPct < RACINAIS_RH[0]!;
  const rh = Math.min(Math.max(rhPct, RACINAIS_RH[0]!), RACINAIS_RH[2]!);
  const lo = rh <= RACINAIS_RH[1]! ? 0 : 1;
  const x0 = RACINAIS_RH[lo]!;
  const x1 = RACINAIS_RH[lo + 1]!;
  const f = (rh - x0) / (x1 - x0);
  const at = (col: [number, number, number]) =>
    col[lo]! + f * (col[lo + 1]! - col[lo]!);
  return [
    [at(RACINAIS.moderate), at(RACINAIS.high), at(RACINAIS.excessive)],
    clamped,
  ];
}

export function racinaisLevel(w: number, rhPct: number): RacinaisLevel {
  const [[mod, high, exc]] = racinaisThresholds(rhPct);
  if (w >= exc) return "excessive";
  if (w >= high) return "high";
  if (w >= mod) return "moderate";
  return "below moderate";
}

export interface RiskLabel {
  wbgt_c: number;
  flag: Flag;
  flag_meaning: string;
  wa2020_band: string;
  acsm2007_text: string | null;
  racinais_level: RacinaisLevel;
  racinais_thresholds_c: [number, number, number];
  racinais_rh_clamped: boolean;
  model_error_c: number;
}

export function riskLabel(w: number, rhPct: number): RiskLabel {
  const flag = flagFor(w);
  const [thresholds, clamped] = racinaisThresholds(rhPct);
  return {
    wbgt_c: w,
    flag,
    flag_meaning: FLAG_MEANINGS[flag],
    wa2020_band: wa2020Band(w),
    acsm2007_text: acsm2007Text(w),
    racinais_level: racinaisLevel(w, rhPct),
    racinais_thresholds_c: thresholds,
    racinais_rh_clamped: clamped,
    model_error_c: WBGT_MODEL_ERROR_C,
  };
}
