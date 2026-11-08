/** Shared ingest types (port of blagden.ingest.table). Times are milliseconds since the epoch, UTC. */

export type SourceFormat = "gpx" | "tcx" | "fit";

export class IngestError extends Error {
  override name = "IngestError";
}
export class NoHeartRateError extends IngestError {
  override name = "NoHeartRateError";
}

export interface RawRecord {
  timeMs: number | null;
  hr: number | null;
  lat: number | null;
  lon: number | null;
  alt: number | null;
  speed: number | null;
  distance: number | null;
}

export interface RawActivity {
  records: RawRecord[];
  sourceFormat: SourceFormat;
  localUtcOffsetS: number | null;
  notes: string[];
}

export interface ActivityTable {
  timeMs: number[];
  elapsedS: number[];
  hr: (number | null)[];
  lat: (number | null)[];
  lon: (number | null)[];
  alt: (number | null)[];
  speed: (number | null)[];
  distance: (number | null)[];
  sourceFormat: SourceFormat;
  distanceSource: "device" | "computed" | "none";
  localUtcOffsetS: number | null;
}

/** Same keys as the Python CleaningReport, so the golden fixtures compare directly. */
export interface CleaningReport {
  rows_in: number;
  rows_out: number;
  rows_dropped: Record<string, number>;
  values_removed: Record<string, number>;
  hr_missing_rows: number;
  reordered: boolean;
  gaps: [startElapsedS: number, durationS: number][];
  notes: string[];
}

export const durationS = (t: ActivityTable) =>
  t.elapsedS.length ? t.elapsedS[t.elapsedS.length - 1]! : 0;
