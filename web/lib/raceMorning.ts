/** Hourly race-morning table (port of blagden.weather.race_morning.hour_row). */
import { heatIndexC, pagasaCategory } from "./heatIndex";
import type { HourlyWeather } from "./openMeteo";
import { riskLabel } from "./risk";
import { sunPosition } from "./solar";
import { outdoorWbgt } from "./wbgt";

export const SCALES_NOTE =
  "The heat index assumes shade, rest and a light wind; WBGT counts the sun on a globe and the evaporation off a wick. On a sunny morning WBGT can sit in a higher band than the heat index suggests.";

export interface RaceHour {
  timeMs: number;
  t_air_c: number | null;
  rh_pct: number | null;
  heat_index_c: number | null;
  pagasa_category: string | null;
  wbgt_c: number | null;
  flag: string | null;
  wa2020_band: string | null;
  racinais_level: string | null;
  wind2_mps: number | null;
  ghi_wm2: number | null;
  sun_elevation_deg: number;
  flags: string[];
}

const ok = (...v: (number | null | undefined)[]) =>
  v.every((x) => typeof x === "number" && Number.isFinite(x));

export function hourRow(
  w: HourlyWeather,
  i: number,
  lat: number,
  lon: number,
  urban: boolean,
): RaceHour {
  const t = w.temperature_c[i] ?? null;
  const rh = w.rh_pct[i] ?? null;
  const sun = sunPosition(new Date(w.timeMs[i]!), lat, lon);
  const flags: string[] = [];
  let hi: number | null = null;
  let cat: string | null = null;
  if (ok(t, rh)) {
    hi = heatIndexC(t!, rh!);
    cat = pagasaCategory(hi).name;
  } else flags.push("missing_temperature_or_humidity");
  const p = w.pressure_hpa[i];
  const u = w.wind10_mps[i];
  const g = w.ghi_wm2[i];
  const dir = w.direct_wm2[i];
  const dif = w.diffuse_wm2[i];
  let wbgt: number | null = null;
  let wind2: number | null = null;
  let label = null;
  if (ok(t, rh, p, u, g, dir, dif)) {
    const r = outdoorWbgt({
      t_air_c: t!,
      rh_pct: rh!,
      pressure_hpa: p!,
      wind_mps: u!,
      wind_height_m: w.windHeightM,
      ghi_wm2: g!,
      direct_wm2: dir!,
      diffuse_wm2: dif!,
      cos_zenith: sun.cos_zenith,
      distance_au: sun.distance_au,
      urban,
    });
    flags.push(...r.flags);
    wbgt = r.wbgt_c;
    wind2 = r.wind2_mps;
    if (wbgt !== null) label = riskLabel(wbgt, rh!);
  } else flags.push("missing_wbgt_input");
  return {
    timeMs: w.timeMs[i]!,
    t_air_c: ok(t) ? t : null,
    rh_pct: ok(rh) ? rh : null,
    heat_index_c: hi,
    pagasa_category: cat,
    wbgt_c: wbgt,
    flag: label?.flag ?? null,
    wa2020_band: label?.wa2020_band ?? null,
    racinais_level: label?.racinais_level ?? null,
    wind2_mps: wind2,
    ghi_wm2: ok(g) ? g! : null,
    sun_elevation_deg: sun.elevation_deg,
    flags,
  };
}

export function raceMorning(
  w: HourlyWeather,
  lat: number,
  lon: number,
  urban: boolean,
): RaceHour[] {
  return w.timeMs.map((_, i) => hourRow(w, i, lat, lon, urban));
}

/** Format an instant as Manila clock time, HH:MM. */
export function manilaClock(ms: number): string {
  return new Date(ms + 8 * 3600_000).toISOString().slice(11, 16);
}
