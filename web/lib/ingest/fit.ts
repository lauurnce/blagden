/** FIT reader for the browser with fit-file-parser (MIT; D-013). CRC errors are rejected. */
import FitParser from "fit-file-parser";

import { IngestError, type RawActivity, type RawRecord } from "./types";

type FitValue = number | Date | string | undefined | null;

function num(rec: Record<string, FitValue>, ...keys: string[]): number | null {
  for (const k of keys) {
    const v = rec[k];
    if (typeof v === "number" && Number.isFinite(v)) return v;
  }
  return null;
}

export async function readFit(
  content: ArrayBuffer,
  fileName = "file",
): Promise<RawActivity> {
  let data: Awaited<ReturnType<FitParser["parseAsync"]>>;
  try {
    // A Uint8Array view works whatever realm the buffer came from; the library's
    // ArrayBuffer branch relies on instanceof, which fails across realms.
    const view = new Uint8Array(content) as unknown as ArrayBuffer;
    data = await new FitParser({ force: false, strict: true }).parseAsync(view);
  } catch (e) {
    throw new IngestError(
      `${fileName}: not a readable FIT file (${(e as Error).message ?? e})`,
    );
  }
  const raw = (data.records ?? []) as unknown as Record<string, FitValue>[];
  const records: RawRecord[] = raw.map((r) => {
    const t = r.timestamp;
    return {
      timeMs:
        t instanceof Date && !Number.isNaN(t.getTime()) ? t.getTime() : null,
      hr: num(r, "heart_rate"),
      lat: num(r, "position_lat"),
      lon: num(r, "position_long"),
      alt: num(r, "enhanced_altitude", "altitude"),
      speed: num(r, "enhanced_speed", "speed"),
      distance: num(r, "distance"),
    };
  });
  if (records.length === 0)
    throw new IngestError(
      `${fileName}: no record messages found in the FIT file`,
    );
  const a = data.activity;
  let offset: number | null = null;
  if (a?.timestamp instanceof Date && a.local_timestamp instanceof Date) {
    offset = Math.round(
      (a.local_timestamp.getTime() - a.timestamp.getTime()) / 1000,
    );
  }
  return { records, sourceFormat: "fit", localUtcOffsetS: offset, notes: [] };
}
