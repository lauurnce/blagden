/**
 * Heat index by the NWS Rothfusz procedure on the PAGASA scale (docs/SCIENCE.md section 5).
 * Port of blagden.weather.heat_index. Labelled "heat index on the PAGASA scale" because it is
 * computed here, not published by PAGASA.
 */

export const cToF = (c: number) => (c * 9) / 5 + 32;
export const fToC = (f: number) => ((f - 32) * 5) / 9;

export function heatIndexF(t: number, rh: number): number {
  const simple = 0.5 * (t + 61 + 1.2 * (t - 68) + 0.094 * rh);
  if ((simple + t) / 2 < 80) return simple;
  let hi =
    -42.379 +
    2.04901523 * t +
    10.14333127 * rh -
    0.22475541 * t * rh -
    0.00683783 * t * t -
    0.05481717 * rh * rh +
    0.00122874 * t * t * rh +
    0.00085282 * t * rh * rh -
    0.00000199 * t * t * rh * rh;
  if (rh < 13 && t >= 80 && t <= 112)
    hi -= ((13 - rh) / 4) * Math.sqrt((17 - Math.abs(t - 95)) / 17);
  else if (rh > 85 && t >= 80 && t <= 87)
    hi += ((rh - 85) / 10) * ((87 - t) / 5);
  return hi;
}

export const heatIndexC = (tC: number, rh: number) =>
  fToC(heatIndexF(cToF(tC), rh));

export interface PagasaCategory {
  name: string;
  low_c: number | null;
  high_c: number | null;
  colour: string | null;
  effect: string | null;
}

export const PAGASA_CATEGORIES: PagasaCategory[] = [
  {
    name: "Not hazardous",
    low_c: null,
    high_c: 26,
    colour: null,
    effect: null,
  },
  {
    name: "Caution",
    low_c: 27,
    high_c: 32,
    colour: "yellow",
    effect:
      "prolonged exposure and activity may result in fatigue. Continuing such activities could also lead to heat cramps.",
  },
  {
    name: "Extreme Caution",
    low_c: 33,
    high_c: 41,
    colour: "yellow-orange",
    effect:
      "heat cramps and heat exhaustion are possible, and ongoing activity could result in heat stroke.",
  },
  {
    name: "Danger",
    low_c: 42,
    high_c: 51,
    colour: "red-orange",
    effect:
      "heat cramps and heat exhaustion are likely, and heat stroke is probable with continued exposure",
  },
  {
    name: "Extreme Danger",
    low_c: 52,
    high_c: null,
    colour: "red",
    effect: "heat stroke is imminent",
  },
];

/** Classify after rounding half up to a whole degree (Blagden choice, SCIENCE.md 5). */
export function pagasaCategory(hiC: number): PagasaCategory {
  const whole = Math.floor(hiC + 0.5);
  for (const cat of [...PAGASA_CATEGORIES].reverse()) {
    if (cat.low_c !== null && whole >= cat.low_c) return cat;
  }
  return PAGASA_CATEGORIES[0]!;
}
