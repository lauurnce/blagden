/** Parity with the Python reference: every golden case within the tolerance stored in the file. */
import { readFileSync } from "node:fs";
import { join } from "node:path";

import { describe, expect, it } from "vitest";

import { ectempStep, estimateCoreTemp } from "../lib/ectemp";
import { psi } from "../lib/psi";

type Num = number | null;
const golden = (name: string) =>
  JSON.parse(readFileSync(join(__dirname, "golden", name), "utf-8")) as {
    tolerance: Record<string, number>;
    cases: {
      name: string;
      kind?: string;
      inputs: Record<string, unknown>;
      expected: Record<string, unknown>;
    }[];
  };

export function expectClose(
  actual: Num | Num[],
  expected: Num | Num[],
  tol: number,
  label: string,
) {
  const a = Array.isArray(actual) ? actual : [actual];
  const e = Array.isArray(expected) ? expected : [expected];
  expect(a.length, label).toBe(e.length);
  a.forEach((v, i) => {
    const want = e[i];
    if (want === null || want === undefined) {
      expect(
        v === null || Number.isNaN(v),
        `${label}[${i}] should be missing`,
      ).toBe(true);
    } else {
      expect(
        Math.abs((v as number) - want),
        `${label}[${i}]`,
      ).toBeLessThanOrEqual(tol);
    }
  });
}

describe("ectemp parity", () => {
  const g = golden("ectemp.json");
  for (const c of g.cases) {
    it(c.name, () => {
      const exp = c.expected as Record<string, Num | Num[]>;
      if (c.kind === "step") {
        const i = c.inputs as {
          tc_prev_c: number;
          v_prev_c2: number;
          hr_bpm: number | null;
        };
        const [tc, v, k] = ectempStep(i.tc_prev_c, i.v_prev_c2, i.hr_bpm);
        expectClose(tc, exp.tc_c!, g.tolerance.tc_c!, "tc_c");
        expectClose(v, exp.var_c2!, g.tolerance.var_c2!, "var_c2");
        expectClose(k, exp.gain!, g.tolerance.gain!, "gain");
      } else {
        const i = c.inputs as { hr_bpm: Num[]; tc0_c: number; v0_c2: number };
        const est = estimateCoreTemp(i.hr_bpm, i.tc0_c, i.v0_c2);
        expectClose(est.tcC, exp.tc_c!, g.tolerance.tc_c!, "tc_c");
        expectClose(est.varC2, exp.var_c2!, g.tolerance.var_c2!, "var_c2");
        expectClose(est.gain, exp.gain!, g.tolerance.gain!, "gain");
        expect(est.observed).toEqual(c.expected.observed);
      }
    });
  }
});

describe("psi parity", () => {
  const g = golden("psi.json");
  for (const c of g.cases) {
    it(c.name, () => {
      const i = c.inputs as {
        tc_c: Num[];
        hr_bpm: Num[];
        tc0_c: number;
        hr0_bpm: number;
      };
      expectClose(
        psi(i.tc_c, i.hr_bpm, i.tc0_c, i.hr0_bpm),
        c.expected.psi as Num[],
        g.tolerance.psi!,
        "psi",
      );
    });
  }
});
