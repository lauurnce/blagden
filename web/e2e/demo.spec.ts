import { readFileSync } from "node:fs";
import { join } from "node:path";

import AxeBuilder from "@axe-core/playwright";
import { expect, test, type Request } from "@playwright/test";

const FIXTURE = join(
  __dirname,
  "..",
  "..",
  "tests",
  "fixtures",
  "synthetic_loop.gpx",
);
const SHOTS = process.env.BLAGDEN_SCREENSHOTS;

test("demo analyses a file on the device and sends none of it anywhere", async ({
  page,
  baseURL,
}) => {
  const requests: Request[] = [];
  page.on("request", (r) => requests.push(r));
  await page.goto("/demo");
  await expect(page.getByTestId("privacy-line")).toHaveText(
    "Your file is processed on this device and never uploaded.",
  );
  const before = requests.length;

  await page.getByLabel(/Choose a run file/).setInputFiles(FIXTURE);
  await expect(page.getByTestId("results")).toBeVisible();

  // The chart rendered with both lines drawn.
  const chart = page.getByTestId("core-temp-chart");
  await expect(chart).toBeVisible();
  expect(
    (await page.getByTestId("ct-line").getAttribute("d"))!.length,
  ).toBeGreaterThan(100);
  expect(
    (await page.getByTestId("hr-line").getAttribute("d"))!.length,
  ).toBeGreaterThan(100);
  await expect(page.getByTestId("stat-Core temp peak")).toHaveText(
    "38.28 C at 0:29:00",
  );
  await expect(page.getByTestId("stat-Peak PSI")).toHaveText("6.5 of 10");
  await expect(page.getByTestId("limitation-note")).toContainText(
    "above 39.0 C",
  );
  await expect(page.getByTestId("zones")).toContainText("above 39.0 C");

  // No request after choosing the file carries file data: nothing is posted, nothing leaves
  // this origin, and no URL or body holds any part of the file.
  const file = readFileSync(FIXTURE, "utf-8");
  const fragments = [
    file.slice(0, 200),
    "<trkpt",
    "TrackPointExtension",
    "<gpx",
  ];
  for (const r of requests.slice(before)) {
    expect(r.method(), r.url()).toBe("GET");
    expect(r.postData(), r.url()).toBeNull();
    expect(new URL(r.url()).origin, r.url()).toBe(new URL(baseURL!).origin);
    for (const f of fragments)
      expect(decodeURIComponent(r.url())).not.toContain(f);
  }

  const axe = await new AxeBuilder({ page })
    .withTags(["wcag2a", "wcag2aa", "wcag21aa"])
    .analyze();
  expect(axe.violations.map((v) => `${v.id}: ${v.help}`)).toEqual([]);
  if (SHOTS)
    await page.screenshot({ path: join(SHOTS, "demo.png"), fullPage: true });
});

test("demo explains a file without heart rate", async ({ page }) => {
  await page.goto("/demo");
  await page.getByLabel(/Choose a run file/).setInputFiles({
    name: "nohr.gpx",
    mimeType: "application/gpx+xml",
    buffer: Buffer.from(
      '<gpx><trk><trkseg><trkpt lat="0" lon="0"><time>2026-01-04T21:00:00Z</time></trkpt></trkseg></trk></gpx>',
    ),
  });
  await expect(page.getByTestId("error")).toContainText("no valid heart rate");
});

test("demo controls are reachable by keyboard", async ({ page }) => {
  await page.goto("/demo");
  await page.keyboard.press("Tab");
  await expect(
    page.getByRole("link", { name: "Skip to content" }),
  ).toBeFocused();
  const reached: string[] = [];
  for (let i = 0; i < 12; i++) {
    await page.keyboard.press("Tab");
    reached.push(
      await page.evaluate(
        () =>
          document.activeElement?.id ||
          document.activeElement?.textContent ||
          "",
      ),
    );
  }
  const fileId = await page.getByLabel(/Choose a run file/).getAttribute("id");
  const restId = await page.getByLabel(/Resting heart rate/).getAttribute("id");
  expect(reached).toContain(fileId);
  expect(reached).toContain(restId);
});
