/**
 * The synthetic 4-hour heart-rate trace used by the golden fixtures
 * (scripts/make_golden.py, marathon_trace). Built from a formula; no real run.
 *
 * Warm-up from 100 to 150 bpm over 15 minutes, then a drift of 0.08 bpm per
 * minute with a 3 bpm wave every 20 minutes, and two short dropouts.
 */
export function syntheticMarathonHr(): (number | null)[] {
  const hr: (number | null)[] = [];
  for (let m = 0; m < 240; m++) {
    const value =
      m < 15
        ? 100 + (50 * m) / 15
        : 150 + 0.08 * (m - 15) + 3 * Math.sin((2 * Math.PI * m) / 20);
    const dropout = (m >= 90 && m < 94) || (m >= 200 && m < 202);
    hr.push(dropout ? null : Math.round(value * 1000) / 1000);
  }
  return hr;
}
