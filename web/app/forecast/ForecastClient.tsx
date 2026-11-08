"use client";

import { useId, useState, type FormEvent } from "react";

import { FLAG_LEGEND, FlagBadge } from "@/app/components/RiskBadge";
import { fetchHourly, manilaToday } from "@/lib/openMeteo";
import {
  manilaClock,
  raceMorning,
  SCALES_NOTE,
  type RaceHour,
} from "@/lib/raceMorning";
import { VENUES } from "@/lib/venues";

const CUSTOM = "custom";
const HOURS = Array.from({ length: 24 }, (_, h) => h);
const fmt = (v: number | null, d = 1) => (v === null ? "n/a" : v.toFixed(d));

export default function ForecastClient() {
  const ids = {
    venue: useId(),
    lat: useId(),
    lon: useId(),
    date: useId(),
    from: useId(),
    to: useId(),
    rural: useId(),
  };
  const [venueId, setVenueId] = useState(VENUES[0]!.id);
  const venue = VENUES.find((v) => v.id === venueId);
  const [lat, setLat] = useState(String(VENUES[0]!.lat));
  const [lon, setLon] = useState(String(VENUES[0]!.lon));
  const [rural, setRural] = useState(false);
  const [day, setDay] = useState(manilaToday());
  const [from, setFrom] = useState(4);
  const [to, setTo] = useState(9);
  const [rows, setRows] = useState<RaceHour[] | null>(null);
  const [status, setStatus] = useState("Choose a place and date.");
  const [error, setError] = useState<string | null>(null);

  function pickVenue(id: string) {
    setVenueId(id);
    const v = VENUES.find((x) => x.id === id);
    if (v) {
      setLat(String(v.lat));
      setLon(String(v.lon));
      setRural(!v.urban);
    }
  }

  async function submit(e: FormEvent) {
    e.preventDefault();
    setError(null);
    setRows(null);
    const la = Number(lat);
    const lo = Number(lon);
    if (
      !Number.isFinite(la) ||
      !Number.isFinite(lo) ||
      lat.trim() === "" ||
      lon.trim() === ""
    ) {
      setError("Enter latitude and longitude as decimal degrees.");
      return;
    }
    if (to < from) {
      setError("The last hour must not be before the first hour.");
      return;
    }
    setStatus("Fetching the forecast from Open-Meteo...");
    try {
      const w = await fetchHourly(la, lo, day);
      const all = raceMorning(w, la, lo, !rural);
      const window = all.filter((r) => {
        const h = Number(manilaClock(r.timeMs).slice(0, 2));
        return h >= from && h <= to;
      });
      setRows(window);
      setStatus(`Showing ${window.length} hours (${w.source}).`);
    } catch (err) {
      setError((err as Error).message);
      setStatus("No forecast available.");
    }
  }

  return (
    <div className="flex flex-col gap-6">
      <form
        onSubmit={submit}
        className="grid gap-4 rounded border border-border p-4 sm:grid-cols-2"
        aria-label="Forecast options"
      >
        <div className="sm:col-span-2">
          <label htmlFor={ids.venue} className="block font-medium">
            Place
          </label>
          <select
            id={ids.venue}
            value={venueId}
            onChange={(e) => pickVenue(e.target.value)}
            className="mt-1 w-full rounded border border-border bg-background px-2 py-1"
          >
            {VENUES.map((v) => (
              <option key={v.id} value={v.id}>
                {v.name}
              </option>
            ))}
            <option value={CUSTOM}>Other place: enter coordinates</option>
          </select>
          {venue && (
            <p className="mt-1 text-sm text-muted">
              Coordinates from{" "}
              <a className="underline" href={venue.source}>
                the place&apos;s Wikipedia article
              </a>
              ; they mark the area, not the start line.
            </p>
          )}
        </div>
        <div>
          <label htmlFor={ids.lat} className="block text-sm">
            Latitude, decimal degrees north
          </label>
          <input
            id={ids.lat}
            inputMode="decimal"
            value={lat}
            readOnly={venueId !== CUSTOM}
            onChange={(e) => setLat(e.target.value)}
            className="mt-1 w-full rounded border border-border bg-background px-2 py-1"
          />
        </div>
        <div>
          <label htmlFor={ids.lon} className="block text-sm">
            Longitude, decimal degrees east
          </label>
          <input
            id={ids.lon}
            inputMode="decimal"
            value={lon}
            readOnly={venueId !== CUSTOM}
            onChange={(e) => setLon(e.target.value)}
            className="mt-1 w-full rounded border border-border bg-background px-2 py-1"
          />
        </div>
        <div>
          <label htmlFor={ids.date} className="block text-sm">
            Race date (Manila)
          </label>
          <input
            id={ids.date}
            type="date"
            value={day}
            onChange={(e) => setDay(e.target.value)}
            className="mt-1 w-full rounded border border-border bg-background px-2 py-1"
          />
        </div>
        <div className="flex gap-4">
          <div>
            <label htmlFor={ids.from} className="block text-sm">
              From
            </label>
            <select
              id={ids.from}
              value={from}
              onChange={(e) => setFrom(Number(e.target.value))}
              className="mt-1 rounded border border-border bg-background px-2 py-1"
            >
              {HOURS.map((h) => (
                <option key={h} value={h}>
                  {String(h).padStart(2, "0")}:00
                </option>
              ))}
            </select>
          </div>
          <div>
            <label htmlFor={ids.to} className="block text-sm">
              To
            </label>
            <select
              id={ids.to}
              value={to}
              onChange={(e) => setTo(Number(e.target.value))}
              className="mt-1 rounded border border-border bg-background px-2 py-1"
            >
              {HOURS.map((h) => (
                <option key={h} value={h}>
                  {String(h).padStart(2, "0")}:00
                </option>
              ))}
            </select>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <input
            id={ids.rural}
            type="checkbox"
            checked={rural}
            disabled={venueId !== CUSTOM}
            onChange={(e) => setRural(e.target.checked)}
          />
          <label htmlFor={ids.rural} className="text-sm">
            Open rural site (changes how wind is converted to 2 m)
          </label>
        </div>
        <div className="sm:col-span-2">
          <button
            type="submit"
            className="rounded bg-accent px-4 py-2 font-medium text-accent-contrast"
          >
            Show forecast
          </button>
        </div>
      </form>

      <p role="status" aria-live="polite" className="text-sm">
        {status}
      </p>
      {error && (
        <p
          role="alert"
          data-testid="error"
          className="rounded border border-[#b91c1c] px-3 py-2"
        >
          {error}
        </p>
      )}

      {rows && (
        <section aria-labelledby="fc-heading" className="flex flex-col gap-4">
          <h2 id="fc-heading" className="text-2xl font-semibold">
            Hourly forecast, {day} (Manila time)
          </h2>
          <div className="overflow-x-auto">
            <table
              className="w-full border-collapse text-left text-sm"
              data-testid="forecast-table"
            >
              <caption className="sr-only">
                Hourly air temperature, humidity, heat index, WBGT and risk
              </caption>
              <thead>
                <tr className="border-b border-border">
                  {[
                    "Hour",
                    "Air C",
                    "Humidity %",
                    "Heat index C (PAGASA scale)",
                    "WBGT C",
                    "Race flag",
                    "World Athletics 2020",
                    "Humidity-corrected risk",
                  ].map((h) => (
                    <th key={h} scope="col" className="px-2 py-1">
                      {h}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {rows.map((r) => (
                  <tr key={r.timeMs} className="border-b border-border">
                    <th scope="row" className="px-2 py-1 font-normal">
                      {manilaClock(r.timeMs)}
                    </th>
                    <td className="px-2 py-1">{fmt(r.t_air_c)}</td>
                    <td className="px-2 py-1">{fmt(r.rh_pct, 0)}</td>
                    <td className="px-2 py-1">
                      {fmt(r.heat_index_c, 0)} {r.pagasa_category ?? ""}
                    </td>
                    <td className="px-2 py-1">{fmt(r.wbgt_c)}</td>
                    <td className="px-2 py-1">
                      <FlagBadge flag={r.flag} />
                    </td>
                    <td className="px-2 py-1">{r.wa2020_band ?? "n/a"}</td>
                    <td className="px-2 py-1">{r.racinais_level ?? "n/a"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <p className="text-sm">
            Flag symbols:{" "}
            {FLAG_LEGEND.map((f) => `${f.symbol} ${f.flag}`).join(", ")}.
          </p>
          <p className="text-sm">
            WBGT model error is about +/- 1 C, so read a value near a band edge
            as near the edge. {SCALES_NOTE} Training insight, not a go or no-go
            decision.
          </p>
          <p className="text-sm">
            <a className="underline" href="https://open-meteo.com/">
              Weather data by Open-Meteo.com
            </a>{" "}
            (CC BY 4.0).
          </p>
        </section>
      )}
    </div>
  );
}
