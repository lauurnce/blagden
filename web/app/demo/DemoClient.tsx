"use client";

import { useId, useState, type DragEvent } from "react";

import CoreTempChart from "@/app/components/CoreTempChart";
import { durationS, readActivity, type ReadResult } from "@/lib/ingest";
import {
  summarizeStrain,
  zoneMinutes,
  LIMITATION_NOTE,
  type StrainResult,
} from "@/lib/strain";

export const PRIVACY_LINE =
  "Your file is processed on this device and never uploaded.";

function hms(s: number): string {
  const t = Math.round(s);
  return `${Math.floor(t / 3600)}:${String(Math.floor((t % 3600) / 60)).padStart(2, "0")}:${String(t % 60).padStart(2, "0")}`;
}

function optionalNumber(text: string): number | null {
  const v = Number(text);
  return text.trim() === "" || !Number.isFinite(v) ? null : v;
}

interface Analysis {
  name: string;
  run: ReadResult;
  strain: StrainResult;
}

export default function DemoClient() {
  const ids = { file: useId(), rest: useId(), start: useId(), status: useId() };
  const [restingHr, setRestingHr] = useState("");
  const [startTemp, setStartTemp] = useState("");
  const [status, setStatus] = useState("No file yet.");
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<Analysis | null>(null);
  const [dragging, setDragging] = useState(false);

  async function analyse(file: File) {
    setError(null);
    setResult(null);
    setStatus(`Reading ${file.name} on this device...`);
    try {
      const run = await readActivity(file.name, await file.arrayBuffer());
      const strain = summarizeStrain(run.minutes.hr, {
        tc0: optionalNumber(startTemp),
        hr0: optionalNumber(restingHr),
      });
      setResult({ name: file.name, run, strain });
      setStatus(`Analysed ${file.name}: ${run.minutes.hr.length} minutes.`);
    } catch (e) {
      setError((e as Error).message);
      setStatus("The file could not be analysed.");
    }
  }

  function onDrop(e: DragEvent<HTMLDivElement>) {
    e.preventDefault();
    setDragging(false);
    const file = e.dataTransfer.files[0];
    if (file) void analyse(file);
  }

  const s = result?.strain.summary;
  const t = result?.run.table;
  const distM = t ? t.distance[t.distance.length - 1] : null;
  const hrValues = result
    ? result.run.table.hr.filter((h): h is number => h !== null)
    : [];

  return (
    <div className="flex flex-col gap-6">
      <p
        className="rounded border border-border bg-panel px-3 py-2 font-medium"
        data-testid="privacy-line"
      >
        {PRIVACY_LINE}
      </p>

      <div
        onDragOver={(e) => {
          e.preventDefault();
          setDragging(true);
        }}
        onDragLeave={() => setDragging(false)}
        onDrop={onDrop}
        className={`rounded border-2 border-dashed p-6 ${dragging ? "border-accent" : "border-border"}`}
      >
        <label htmlFor={ids.file} className="block font-medium">
          Choose a run file (.fit, .gpx or .tcx with heart rate), or drop it
          here
        </label>
        <input
          id={ids.file}
          type="file"
          accept=".fit,.gpx,.tcx"
          className="mt-3 block w-full text-sm file:mr-3 file:rounded file:border-0 file:bg-accent file:px-3 file:py-2 file:text-accent-contrast"
          aria-describedby={ids.status}
          onChange={(e) => {
            const f = e.currentTarget.files?.[0];
            if (f) void analyse(f);
          }}
        />
        <div className="mt-4 grid gap-4 sm:grid-cols-2">
          <div>
            <label htmlFor={ids.rest} className="block text-sm">
              Resting heart rate, bpm (optional; 70 is assumed)
            </label>
            <input
              id={ids.rest}
              inputMode="numeric"
              value={restingHr}
              onChange={(e) => setRestingHr(e.target.value)}
              className="mt-1 w-32 rounded border border-border bg-background px-2 py-1"
            />
          </div>
          <div>
            <label htmlFor={ids.start} className="block text-sm">
              Measured starting core temperature, C (optional; 37.0 is assumed)
            </label>
            <input
              id={ids.start}
              inputMode="decimal"
              value={startTemp}
              onChange={(e) => setStartTemp(e.target.value)}
              className="mt-1 w-32 rounded border border-border bg-background px-2 py-1"
            />
          </div>
        </div>
        <p className="mt-2 text-sm text-muted">
          Set these before choosing the file.
        </p>
      </div>

      <p id={ids.status} role="status" aria-live="polite" className="text-sm">
        {status}
      </p>
      {error && (
        <p role="alert" data-testid="error" className="rounded border border-[#b91c1c] px-3 py-2">
          {error}
        </p>
      )}

      {result && s && t && (
        <section
          aria-labelledby="results-heading"
          className="flex flex-col gap-6"
          data-testid="results"
        >
          <h2 id="results-heading" className="text-2xl font-semibold">
            {result.name}
          </h2>
          <dl className="grid grid-cols-2 gap-x-6 gap-y-2 sm:grid-cols-3">
            {[
              ["Duration", hms(durationS(t))],
              [
                "Distance",
                distM === null || distM === undefined
                  ? "n/a"
                  : `${(distM / 1000).toFixed(2)} km (${t.distanceSource})`,
              ],
              [
                "Heart rate",
                `mean ${(hrValues.reduce((a, b) => a + b, 0) / hrValues.length).toFixed(0)}, max ${Math.max(...hrValues).toFixed(0)} bpm`,
              ],
              [
                "Core temp start",
                `${s.start_tc_c.toFixed(2)} C (${s.start_measured ? "measured" : "assumed"})`,
              ],
              [
                "Core temp peak",
                `${s.peak_tc_c.toFixed(2)} C at ${hms(60 * (s.peak_minute + 1))}`,
              ],
              [
                "Peak PSI",
                s.peak_psi === null
                  ? "n/a"
                  : `${s.peak_psi.toFixed(1)}${s.psi_above_scale ? " (above the 0 to 10 scale)" : ""} of 10`,
              ],
              [
                "Resting HR for PSI",
                `${s.hr0_bpm.toFixed(0)} bpm (${s.hr0_defaulted ? "assumed" : "given"})`,
              ],
              [
                "Minutes without heart rate",
                String(result.run.minutes.hasHr.filter((h) => !h).length),
              ],
            ].map(([k, v]) => (
              <div key={k}>
                <dt className="text-sm text-muted">{k}</dt>
                <dd className="font-medium" data-testid={`stat-${k}`}>
                  {v}
                </dd>
              </div>
            ))}
          </dl>

          <p
            className="rounded border-l-4 border-[#b45309] bg-panel px-3 py-2"
            data-testid="limitation-note"
          >
            <strong>Limitation:</strong> {LIMITATION_NOTE} Training insight, not
            medical advice.
          </p>

          <CoreTempChart
            tcC={result.strain.estimate.tcC}
            hr={result.run.minutes.hr}
          />

          <table
            className="w-full max-w-md border-collapse text-left"
            data-testid="zones"
          >
            <caption className="mb-2 text-left font-medium">
              Minutes in each estimated core temperature zone
            </caption>
            <thead>
              <tr className="border-b border-border">
                <th scope="col" className="py-1 pr-4">
                  Zone
                </th>
                <th scope="col" className="py-1 pr-4">
                  Minutes
                </th>
                <th scope="col" className="py-1 pr-4">
                  Meaning
                </th>
              </tr>
            </thead>
            <tbody>
              {zoneMinutes(result.strain.estimate.tcC).map((z) => (
                <tr key={z.label} className="border-b border-border">
                  <th scope="row" className="py-1 pr-4 font-normal">
                    {z.label}
                  </th>
                  <td className="py-1 pr-4">{z.minutes}</td>
                  <td className="py-1 text-sm">{z.description}</td>
                </tr>
              ))}
            </tbody>
          </table>

          <details>
            <summary className="cursor-pointer">
              Minute-by-minute values
            </summary>
            <table className="mt-2 text-sm">
              <thead>
                <tr>
                  <th scope="col" className="pr-4 text-left">
                    Minute
                  </th>
                  <th scope="col" className="pr-4 text-left">
                    Heart rate (bpm)
                  </th>
                  <th scope="col" className="text-left">
                    Core temp (C)
                  </th>
                </tr>
              </thead>
              <tbody>
                {result.strain.estimate.tcC.map((tc, i) => (
                  <tr key={i}>
                    <td className="pr-4">{i + 1}</td>
                    <td className="pr-4">
                      {result.run.minutes.hr[i]?.toFixed(0) ?? "none"}
                    </td>
                    <td>{tc.toFixed(2)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </details>
        </section>
      )}
    </div>
  );
}
