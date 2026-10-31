import { readFileSync } from "node:fs";
import { join } from "node:path";

import { describe, expect, it } from "vitest";

import { syntheticMarathonHr } from "../lib/syntheticRun";

const golden = JSON.parse(
  readFileSync(join(__dirname, "golden", "ectemp.json"), "utf8"),
) as {
  cases: { name: string; inputs: { hr_bpm: (number | string | null)[] } }[];
};

describe("syntheticMarathonHr", () => {
  it("matches the trace in the Python golden fixture", () => {
    const want = golden.cases
      .find((c) => c.name === "synthetic_marathon_4h")!
      .inputs.hr_bpm.map((v) =>
        typeof v === "number" && !Number.isNaN(v) ? v : null,
      );
    const got = syntheticMarathonHr();
    expect(got).toHaveLength(want.length);
    got.forEach((v, i) => {
      if (want[i] === null) expect(v).toBeNull();
      else expect(v).toBeCloseTo(want[i]!, 9);
    });
  });
});
