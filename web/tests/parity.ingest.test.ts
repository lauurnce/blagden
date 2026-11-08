// @vitest-environment jsdom
/** Browser ingest against Python: the same cleaning and minute series for the shared run files. */
import { readFileSync } from "node:fs";
import { join } from "node:path";

import { describe, expect, it } from "vitest";

import { durationS, readActivity } from "../lib/ingest";

const ROOT = join(__dirname, "..", "..");
const golden = JSON.parse(
  readFileSync(join(__dirname, "golden", "ingest.json"), "utf-8"),
) as {
  tolerance: Record<string, number>;
  cases: {
    name: string;
    inputs: { path: string };
    expected: Record<string, unknown>;
  }[];
};

function bufferOf(path: string): ArrayBuffer {
  const b = readFileSync(join(ROOT, path));
  return b.buffer.slice(
    b.byteOffset,
    b.byteOffset + b.byteLength,
  ) as ArrayBuffer;
}

describe("ingest parity", () => {
  for (const c of golden.cases) {
    it(c.name, async () => {
      const e = c.expected as {
        source_format: string;
        rows_in: number;
        rows_out: number;
        rows_dropped: Record<string, number>;
        values_removed: Record<string, number>;
        hr_missing_rows: number;
        reordered: boolean;
        gaps: [number, number][];
        duration_s: number;
        distance_source: string;
        distance_m_end: number | null;
        start_utc: string;
        hr_bpm: (number | null)[];
        n_samples: number[];
        has_hr: boolean[];
      };
      const { table, report, minutes } = await readActivity(
        c.name,
        bufferOf(c.inputs.path),
      );
      expect(table.sourceFormat).toBe(e.source_format);
      expect([report.rows_in, report.rows_out]).toEqual([
        e.rows_in,
        e.rows_out,
      ]);
      expect(report.rows_dropped).toEqual(e.rows_dropped);
      expect(report.values_removed).toEqual(e.values_removed);
      expect(report.hr_missing_rows).toBe(e.hr_missing_rows);
      expect(report.reordered).toBe(e.reordered);
      expect(report.gaps).toEqual(e.gaps);
      expect(durationS(table)).toBeCloseTo(e.duration_s, 9);
      expect(table.distanceSource).toBe(e.distance_source);
      const end = table.distance[table.distance.length - 1];
      if (e.distance_m_end === null) expect(end).toBeNull();
      else
        expect(
          Math.abs((end as number) - e.distance_m_end),
        ).toBeLessThanOrEqual(golden.tolerance.distance_m_end!);
      expect(new Date(minutes.startMs).getTime()).toBe(
        new Date(e.start_utc).getTime(),
      );
      expect(minutes.nSamples).toEqual(e.n_samples);
      expect(minutes.hasHr).toEqual(e.has_hr);
      minutes.hr.forEach((h, i) => {
        const want = e.hr_bpm[i];
        if (want === null || want === undefined) expect(h).toBeNull();
        else
          expect(Math.abs((h as number) - want)).toBeLessThanOrEqual(
            golden.tolerance.hr_bpm!,
          );
      });
    });
  }
});

describe("ingest errors", () => {
  const enc = (s: string) => new TextEncoder().encode(s).buffer as ArrayBuffer;
  it("explains a file without heart rate", async () => {
    const gpx =
      '<gpx xmlns="http://www.topografix.com/GPX/1/1"><trk><trkseg><trkpt lat="0" lon="0"><time>2026-01-04T21:00:00Z</time></trkpt></trkseg></trk></gpx>';
    await expect(readActivity("a.gpx", enc(gpx))).rejects.toThrow(
      /no valid heart rate/,
    );
  });
  it("rejects an unknown file", async () => {
    await expect(readActivity("notes.txt", enc("hello"))).rejects.toThrow(
      /not a FIT, GPX or TCX/,
    );
  });
  it("rejects a corrupted FIT file", async () => {
    const b = new Uint8Array(bufferOf("tests/fixtures/synthetic_loop.fit"));
    b[200] = b[200]! ^ 0xff;
    await expect(readActivity("bad.fit", b.buffer)).rejects.toThrow(
      /not a readable FIT file/,
    );
  });
  it("reads naive times as UTC with a note", async () => {
    const pt = (t: string, hr: number) =>
      `<trkpt lat="0" lon="0"><time>${t}</time><extensions><hr>${hr}</hr></extensions></trkpt>`;
    const gpx = `<gpx><trk><trkseg>${pt("2026-01-04T21:00:00", 120)}${pt("2026-01-04T21:01:00", 130)}</trkseg></trk></gpx>`;
    const r = await readActivity("n.gpx", enc(gpx));
    expect(r.table.timeMs[0]).toBe(Date.parse("2026-01-04T21:00:00Z"));
    expect(r.report.notes[0]).toMatch(/read as UTC/);
  });
});
