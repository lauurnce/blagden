/**
 * Open-Meteo client for the browser (same request shape as blagden.weather.openmeteo; D-010).
 * The forecast request carries only the venue coordinates and date; never any run file data.
 * Weather data by Open-Meteo.com (CC BY 4.0).
 */
export const FORECAST_URL = "https://api.open-meteo.com/v1/forecast";
export const ARCHIVE_URL = "https://archive-api.open-meteo.com/v1/archive";
export const TIMEZONE = "Asia/Manila";
export const ATTRIBUTION = "Weather data by Open-Meteo.com (CC BY 4.0)";
export const HOURLY_VARIABLES = [
  "temperature_2m",
  "relative_humidity_2m",
  "dew_point_2m",
  "wind_speed_10m",
  "surface_pressure",
  "shortwave_radiation_instant",
  "direct_radiation_instant",
  "diffuse_radiation_instant",
  "cloud_cover",
  "precipitation",
] as const;
const FORECAST_MAX_DAYS = 16;
const ARCHIVE_LAG_DAYS = 7;

export interface HourlyWeather {
  timeMs: number[];
  temperature_c: (number | null)[];
  rh_pct: (number | null)[];
  wind10_mps: (number | null)[];
  pressure_hpa: (number | null)[];
  ghi_wm2: (number | null)[];
  direct_wm2: (number | null)[];
  diffuse_wm2: (number | null)[];
  source: "forecast" | "archive";
  windHeightM: number;
}

const dayMs = 86_400_000;
const isoDay = (d: string) => Date.parse(`${d}T00:00:00Z`);

export function chooseSource(
  day: string,
  today: string,
): "forecast" | "archive" {
  const d = isoDay(day);
  const t = isoDay(today);
  if (Number.isNaN(d)) throw new Error("date must be YYYY-MM-DD");
  if (d > t + (FORECAST_MAX_DAYS - 1) * dayMs)
    throw new Error(`forecasts reach at most ${FORECAST_MAX_DAYS} days ahead`);
  return d < t - ARCHIVE_LAG_DAYS * dayMs ? "archive" : "forecast";
}

export function buildUrl(
  source: "forecast" | "archive",
  lat: number,
  lon: number,
  day: string,
): string {
  if (!(lat >= -90 && lat <= 90 && lon >= -180 && lon <= 180)) {
    throw new Error("latitude must be in -90..90 and longitude in -180..180");
  }
  const params = new URLSearchParams([
    ["latitude", lat.toFixed(4)],
    ["longitude", lon.toFixed(4)],
    ["start_date", day],
    ["end_date", day],
    ["hourly", HOURLY_VARIABLES.join(",")],
    ["timezone", TIMEZONE],
    ["wind_speed_unit", "ms"],
    ["timeformat", "unixtime"],
  ]);
  return `${source === "archive" ? ARCHIVE_URL : FORECAST_URL}?${params.toString()}`;
}

export function parseHourly(
  data: unknown,
  source: "forecast" | "archive",
): HourlyWeather {
  const d = data as {
    error?: boolean;
    reason?: string;
    timezone?: string;
    hourly?: Record<string, unknown>;
  };
  if (d.error) throw new Error(d.reason ?? "Open-Meteo returned an error");
  const h = d.hourly;
  if (!h || !Array.isArray(h.time))
    throw new Error("response has no hourly data");
  if (d.timezone !== TIMEZONE)
    throw new Error(`response time zone is ${d.timezone}, not ${TIMEZONE}`);
  const n = h.time.length;
  const series = (name: string) => {
    const v = h[name];
    if (!Array.isArray(v) || v.length !== n)
      throw new Error(`response has no complete '${name}' series`);
    return v.map((x) => (typeof x === "number" ? x : null));
  };
  return {
    timeMs: (h.time as number[]).map((t) => t * 1000),
    temperature_c: series("temperature_2m"),
    rh_pct: series("relative_humidity_2m"),
    wind10_mps: series("wind_speed_10m"),
    pressure_hpa: series("surface_pressure"),
    ghi_wm2: series("shortwave_radiation_instant"),
    direct_wm2: series("direct_radiation_instant"),
    diffuse_wm2: series("diffuse_radiation_instant"),
    source,
    windHeightM: 10,
  };
}

/** Manila's calendar date today, YYYY-MM-DD. */
export function manilaToday(now = new Date()): string {
  return new Date(now.getTime() + 8 * 3600_000).toISOString().slice(0, 10);
}

export async function fetchHourly(
  lat: number,
  lon: number,
  day: string,
  fetchFn: typeof fetch = fetch,
): Promise<HourlyWeather> {
  const source = chooseSource(day, manilaToday());
  const url = buildUrl(source, lat, lon, day);
  let lastError: unknown;
  for (let attempt = 0; attempt < 3; attempt++) {
    try {
      const res = await fetchFn(url);
      if (res.status === 429 || res.status >= 500)
        throw new Error(`HTTP ${res.status}`);
      const body: unknown = await res.json();
      if (!res.ok)
        throw Object.assign(
          new Error(
            (body as { reason?: string }).reason ?? `HTTP ${res.status}`,
          ),
          { final: true },
        );
      return parseHourly(body, source);
    } catch (e) {
      if ((e as { final?: boolean }).final) throw e;
      lastError = e;
      await new Promise((r) => setTimeout(r, 500 * 2 ** attempt));
    }
  }
  throw new Error(
    `Open-Meteo unavailable after 3 attempts: ${(lastError as Error)?.message ?? lastError}`,
  );
}
