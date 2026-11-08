/** Weather parity with Python: solar, WBGT, heat index and risk within the stored tolerances. */
import { readFileSync } from "node:fs";
import { join } from "node:path";

import { describe, expect, it } from "vitest";

import { heatIndexC, pagasaCategory } from "../lib/heatIndex";
import { riskLabel } from "../lib/risk";
import { sunPosition } from "../lib/solar";
import { outdoorWbgt, type WbgtInputs } from "../lib/wbgt";

interface Golden {
  tolerance: Record<string, number>;
  cases: {
    name: string;
    inputs: Record<string, unknown>;
    expected: Record<string, unknown>;
  }[];
}
const load = (name: string) =>
  JSON.parse(readFileSync(join(__dirname, "golden", name), "utf-8")) as Golden;

function compare(
  got: Record<string, unknown>,
  expected: Record<string, unknown>,
  tol: Record<string, number>,
) {
  for (const [key, want] of Object.entries(expected)) {
    const have = got[key];
    const t = tol[key];
    if (t !== undefined && typeof want === "number") {
      expect(Math.abs((have as number) - want), key).toBeLessThanOrEqual(t);
    } else if (t !== undefined && Array.isArray(want)) {
      (want as number[]).forEach((w, i) =>
        expect(
          Math.abs((have as number[])[i]! - w),
          `${key}[${i}]`,
        ).toBeLessThanOrEqual(t),
      );
    } else {
      expect(have, key).toEqual(want);
    }
  }
}

describe("solar parity", () => {
  const g = load("solar.json");
  for (const c of g.cases) {
    it(c.name, () => {
      const i = c.inputs as {
        time_utc: string;
        lat_deg: number;
        lon_deg: number;
      };
      const p = sunPosition(new Date(i.time_utc), i.lat_deg, i.lon_deg);
      compare(p as unknown as Record<string, unknown>, c.expected, g.tolerance);
    });
  }
});

describe("wbgt parity", () => {
  const g = load("wbgt.json");
  for (const c of g.cases) {
    it(c.name, () => {
      const r = outdoorWbgt(c.inputs as unknown as WbgtInputs);
      compare(r as unknown as Record<string, unknown>, c.expected, g.tolerance);
    });
  }
});

describe("heat index parity", () => {
  const g = load("heat_index.json");
  for (const c of g.cases) {
    it(c.name, () => {
      const i = c.inputs as { t_c: number; rh_pct: number };
      const hi = heatIndexC(i.t_c, i.rh_pct);
      compare(
        { hi_c: hi, category: pagasaCategory(hi).name },
        c.expected,
        g.tolerance,
      );
    });
  }
});

describe("risk parity", () => {
  const g = load("risk.json");
  for (const c of g.cases) {
    it(c.name, () => {
      const i = c.inputs as { wbgt_c: number; rh_pct: number };
      compare(
        riskLabel(i.wbgt_c, i.rh_pct) as unknown as Record<string, unknown>,
        c.expected,
        g.tolerance,
      );
    });
  }
});
