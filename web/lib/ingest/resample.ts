/**
 * One-minute heart rate (port of blagden.ingest.resample). Minute i covers elapsed [60 i, 60 (i+1));
 * minutes = duration rounded up (at least one); a final sample on the end boundary counts in the
 * last minute. Each minute is the mean of its valid samples; a minute with none is null and the
 * filter predicts without an update. Heart rate is never interpolated (D-021).
 */
import { durationS, type ActivityTable } from "./types";

export interface MinuteSeries {
  startMs: number;
  hr: (number | null)[];
  nSamples: number[];
  hasHr: boolean[];
}

export function resampleMinutes(t: ActivityTable): MinuteSeries {
  const n = Math.max(1, Math.ceil(durationS(t) / 60));
  const sums = new Array<number>(n).fill(0);
  const counts = new Array<number>(n).fill(0);
  t.elapsedS.forEach((e, i) => {
    const h = t.hr[i];
    if (h === null || h === undefined) return;
    const idx = Math.min(Math.floor(e / 60), n - 1);
    sums[idx]! += h;
    counts[idx]! += 1;
  });
  return {
    startMs: t.timeMs[0]!,
    hr: counts.map((c, i) => (c > 0 ? sums[i]! / c : null)),
    nSamples: counts,
    hasHr: counts.map((c) => c > 0),
  };
}
