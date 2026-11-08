/** Strain summary and race-morning table against Python, plus the Open-Meteo client and venues. */
import { readFileSync } from "node:fs";
import { join } from "node:path";

import { describe, expect, it } from "vitest";

import {
  buildUrl,
  chooseSource,
  fetchHourly,
  HOURLY_VARIABLES,
  parseHourly,
} from "../lib/openMeteo";
import { manilaClock, raceMorning } from "../lib/raceMorning";
import { summarizeStrain, zoneMinutes } from "../lib/strain";
import { VENUES } from "../lib/venues";

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
const recorded = JSON.parse(
  readFileSync(
    join(
      __dirname,
      "..",
      "..",
      "tests",
      "data",
      "open_meteo",
      "forecast_qmc_2026-11-15.json",
    ),
    "utf-8",
  ),
) as { url: string; response: unknown };

function close(
  have: unknown,
  want: unknown,
  tol: number | undefined,
  label: string,
) {
  if (tol !== undefined && typeof want === "number")
    expect(Math.abs((have as number) - want), label).toBeLessThanOrEqual(tol);
  else expect(have, label).toEqual(want);
}

describe("strain parity", () => {
  const g = load("strain.json");
  for (const c of g.cases) {
    it(c.name, () => {
      const i = c.inputs as {
        hr_bpm: (number | null)[];
        tc0?: number;
        hr0?: number;
      };
      const { summary } = summarizeStrain(i.hr_bpm, { tc0: i.tc0, hr0: i.hr0 });
      for (const [k, v] of Object.entries(c.expected))
        close(
          (summary as unknown as Record<string, unknown>)[k],
          v,
          g.tolerance[k],
          k,
        );
    });
  }
});

describe("race morning parity", () => {
  const g = load("race_morning.json");
  for (const c of g.cases) {
    it(c.name, () => {
      const i = c.inputs as {
        response: unknown;
        lat: number;
        lon: number;
        urban: boolean;
      };
      const rows = raceMorning(
        parseHourly(i.response, "forecast"),
        i.lat,
        i.lon,
        i.urban,
      );
      const want = (c.expected as { hours: Record<string, unknown>[] }).hours;
      expect(rows.length).toBe(want.length);
      rows.forEach((r, n) => {
        const w = want[n]!;
        expect(new Date(r.timeMs).getTime()).toBe(
          Date.parse(w.time_local as string),
        );
        for (const [k, v] of Object.entries(w)) {
          if (k === "time_local") continue;
          close(
            (r as unknown as Record<string, unknown>)[k],
            v,
            g.tolerance[k],
            `${n}.${k}`,
          );
        }
      });
    });
  }
});

describe("open-meteo client", () => {
  it("builds the same request as Python", () => {
    expect(buildUrl("forecast", 14.6517, 121.0493, "2026-11-15")).toBe(
      recorded.url,
    );
    expect(
      new URL(recorded.url).searchParams.get("hourly")!.split(","),
    ).toEqual([...HOURLY_VARIABLES]);
  });
  it("chooses forecast or archive like Python", () => {
    expect(chooseSource("2026-11-15", "2026-11-09")).toBe("forecast");
    expect(chooseSource("2026-10-18", "2026-11-09")).toBe("archive");
    expect(() => chooseSource("2026-12-01", "2026-11-09")).toThrow(/16 days/);
  });
  it("retries a transient failure and parses the body", async () => {
    let calls = 0;
    const fake = (async () => {
      calls += 1;
      if (calls === 1) return new Response("busy", { status: 503 });
      return new Response(JSON.stringify(recorded.response), { status: 200 });
    }) as typeof fetch;
    const w = await fetchHourly(14.6517, 121.0493, "2026-11-15", fake);
    expect(calls).toBe(2);
    expect(manilaClock(w.timeMs[5]!)).toBe("05:00");
  });
  it("rejects bad responses", () => {
    expect(() =>
      parseHourly({ error: true, reason: "bad" }, "forecast"),
    ).toThrow("bad");
    expect(() =>
      parseHourly({ timezone: "UTC", hourly: { time: [] } }, "forecast"),
    ).toThrow(/time zone/);
  });
});

describe("zones and venues", () => {
  it("counts minutes in each zone", () => {
    expect(
      zoneMinutes([38.0, 38.5, 38.6, 39.0, 39.1]).map((z) => z.minutes),
    ).toEqual([2, 2, 1]);
  });
  it("venues are cited and in range", () => {
    expect(VENUES.map((v) => v.id)).toContain("qmc");
    for (const v of VENUES) {
      expect(v.source.startsWith("https://en.wikipedia.org/wiki/")).toBe(true);
      expect(v.lat).toBeGreaterThan(14);
      expect(v.lat).toBeLessThan(16);
      expect(v.lon).toBeGreaterThan(120);
      expect(v.lon).toBeLessThan(122);
    }
    expect(VENUES.find((v) => v.id === "clark")!.urban).toBe(false);
  });
});
