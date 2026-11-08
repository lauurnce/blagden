/**
 * Clean raw records into one activity table (port of blagden.ingest.clean; SCIENCE.md 8, D-021).
 * Rows without a time are dropped; rows are sorted; duplicate timestamps merge, keeping the first
 * present value of each field; heart rates outside 30 to 230 bpm are removed (row kept); positions
 * out of range and negative speeds are removed; gaps over 60 s are reported, never filled.
 */
import { cumulativeDistanceM } from "./geo";
import {
  IngestError,
  type ActivityTable,
  type CleaningReport,
  type RawActivity,
  type RawRecord,
} from "./types";

export const HR_VALID_RANGE_BPM: [number, number] = [30, 230];
export const GAP_THRESHOLD_S = 60;
const FIELDS = ["hr", "lat", "lon", "alt", "speed", "distance"] as const;

function bump(c: Record<string, number>, k: string) {
  c[k] = (c[k] ?? 0) + 1;
}

export function clean(raw: RawActivity): {
  table: ActivityTable;
  report: CleaningReport;
} {
  const dropped: Record<string, number> = {};
  const removed: Record<string, number> = {};
  const timed = raw.records.filter(
    (r): r is RawRecord & { timeMs: number } => r.timeMs !== null,
  );
  if (timed.length < raw.records.length)
    dropped.missing_time = raw.records.length - timed.length;
  if (timed.length === 0) throw new IngestError("no record has a usable time");
  const reordered = timed.some(
    (r, i) => i > 0 && r.timeMs < timed[i - 1]!.timeMs,
  );
  const ordered = timed
    .map((r, i) => ({ r, i }))
    .sort((a, b) => a.r.timeMs - b.r.timeMs || a.i - b.i)
    .map((x) => x.r);

  const merged: (RawRecord & { timeMs: number })[] = [];
  for (const rec of ordered) {
    const last = merged[merged.length - 1];
    if (last && last.timeMs === rec.timeMs) {
      for (const f of FIELDS) if (last[f] === null) last[f] = rec[f];
    } else merged.push({ ...rec });
  }
  if (merged.length < ordered.length)
    dropped.duplicate_time = ordered.length - merged.length;

  const [lo, hi] = HR_VALID_RANGE_BPM;
  for (const r of merged) {
    if (r.hr !== null && !(r.hr >= lo && r.hr <= hi)) {
      bump(removed, "hr_out_of_range");
      r.hr = null;
    }
    if (
      r.lat !== null &&
      r.lon !== null &&
      !(r.lat >= -90 && r.lat <= 90 && r.lon >= -180 && r.lon <= 180)
    ) {
      bump(removed, "position_out_of_range");
      r.lat = r.lon = null;
    }
    if (r.speed !== null && r.speed < 0) {
      bump(removed, "speed_negative");
      r.speed = null;
    }
  }
  const t0 = merged[0]!.timeMs;
  const elapsedS = merged.map((r) => (r.timeMs - t0) / 1000);
  const lat = merged.map((r) => r.lat);
  const lon = merged.map((r) => r.lon);
  const device = merged.map((r) => r.distance);
  let distance: (number | null)[] = device;
  let distanceSource: ActivityTable["distanceSource"] = "none";
  if (device.some((d) => d !== null)) distanceSource = "device";
  else if (merged.some((r) => r.lat !== null && r.lon !== null)) {
    distance = cumulativeDistanceM(lat, lon);
    distanceSource = "computed";
  }
  const gaps: [number, number][] = [];
  for (let i = 1; i < elapsedS.length; i++) {
    const step = elapsedS[i]! - elapsedS[i - 1]!;
    if (step > GAP_THRESHOLD_S) gaps.push([elapsedS[i - 1]!, step]);
  }
  const hr = merged.map((r) => r.hr);
  const table: ActivityTable = {
    timeMs: merged.map((r) => r.timeMs),
    elapsedS,
    hr,
    lat,
    lon,
    alt: merged.map((r) => r.alt),
    speed: merged.map((r) => r.speed),
    distance,
    sourceFormat: raw.sourceFormat,
    distanceSource,
    localUtcOffsetS: raw.localUtcOffsetS,
  };
  const report: CleaningReport = {
    rows_in: raw.records.length,
    rows_out: merged.length,
    rows_dropped: dropped,
    values_removed: removed,
    hr_missing_rows: hr.filter((h) => h === null).length,
    reordered,
    gaps,
    notes: [...raw.notes],
  };
  return { table, report };
}
