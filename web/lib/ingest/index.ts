/**
 * Read a run file in the browser: detect the format from content (extension as fallback), parse,
 * clean and resample. Nothing leaves the device.
 */
import { clean } from "./clean";
import { readFit } from "./fit";
import { readGpx } from "./gpx";
import { resampleMinutes, type MinuteSeries } from "./resample";
import { readTcx } from "./tcx";
import {
  IngestError,
  NoHeartRateError,
  type ActivityTable,
  type CleaningReport,
  type SourceFormat,
} from "./types";

export * from "./types";
export type { MinuteSeries } from "./resample";

const EXTENSIONS: Record<string, SourceFormat> = {
  ".fit": "fit",
  ".gpx": "gpx",
  ".tcx": "tcx",
};

export function sniffFormat(bytes: Uint8Array): SourceFormat | null {
  if (
    bytes.length >= 12 &&
    String.fromCharCode(...bytes.slice(8, 12)) === ".FIT"
  )
    return "fit";
  const text = new TextDecoder("utf-8", { fatal: false })
    .decode(bytes.slice(0, 4096))
    .toLowerCase();
  if (text.includes("<trainingcenterdatabase")) return "tcx";
  if (text.includes("<gpx")) return "gpx";
  return null;
}

export function detectFormat(
  name: string,
  bytes: Uint8Array,
): { format: SourceFormat; note: string | null } {
  const dot = name.lastIndexOf(".");
  const byExt =
    dot >= 0 ? EXTENSIONS[name.slice(dot).toLowerCase()] : undefined;
  const byContent = sniffFormat(bytes);
  if (byContent) {
    const note =
      byExt && byExt !== byContent
        ? `extension says ${byExt} but content is ${byContent}; read as ${byContent}`
        : null;
    return { format: byContent, note };
  }
  if (byExt) return { format: byExt, note: null };
  throw new IngestError(
    `${name}: not a FIT, GPX or TCX activity (unknown extension and content)`,
  );
}

export interface ReadResult {
  table: ActivityTable;
  report: CleaningReport;
  minutes: MinuteSeries;
}

export async function readActivity(
  name: string,
  buffer: ArrayBuffer,
): Promise<ReadResult> {
  const bytes = new Uint8Array(buffer);
  const { format, note } = detectFormat(name, bytes);
  const raw =
    format === "fit"
      ? await readFit(buffer, name)
      : (format === "gpx" ? readGpx : readTcx)(
          new TextDecoder("utf-8").decode(bytes),
          name,
        );
  const { table, report } = clean(raw);
  if (note) report.notes.push(note);
  if (!table.hr.some((h) => h !== null)) {
    const removed = report.values_removed.hr_out_of_range ?? 0;
    const why = removed
      ? `all ${removed} heart-rate values were outside 30 to 230 bpm`
      : "the file has no heart-rate data";
    throw new NoHeartRateError(
      `${name}: no valid heart rate (${why}). Core temperature is estimated from heart rate, so record the run with a heart-rate sensor.`,
    );
  }
  return { table, report, minutes: resampleMinutes(table) };
}
