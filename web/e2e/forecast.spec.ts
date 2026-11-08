import { readFileSync } from "node:fs";
import { join } from "node:path";

import AxeBuilder from "@axe-core/playwright";
import { expect, test } from "@playwright/test";

const RECORDED = JSON.parse(
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
) as { response: unknown };
const SHOTS = process.env.BLAGDEN_SCREENSHOTS;

test("forecast shows hourly WBGT, heat index and risk for a preset venue", async ({
  page,
}) => {
  const seen: string[] = [];
  await page.route("https://api.open-meteo.com/**", async (route) => {
    seen.push(route.request().url());
    await route.fulfill({ json: RECORDED.response });
  });
  await page.goto("/forecast");

  // Keyboard only: choose the venue, set the date and submit.
  await page.getByLabel("Place").focus();
  await page.getByLabel("Place").selectOption("qmc");
  await page.getByLabel("Race date (Manila)").fill("2026-11-15");
  await page.getByRole("button", { name: "Show forecast" }).focus();
  await page.keyboard.press("Enter");

  const table = page.getByTestId("forecast-table");
  await expect(table).toBeVisible();
  await expect(table.locator("tbody tr")).toHaveCount(6);
  await expect(table.locator("tbody tr").first()).toContainText("04:00");
  await expect(table).toContainText("red flag");
  await expect(table).toContainText("Caution");
  await expect(page.getByText(/Weather data by Open-Meteo.com/)).toBeVisible();

  expect(seen).toHaveLength(1);
  const q = new URL(seen[0]!).searchParams;
  expect([q.get("latitude"), q.get("longitude"), q.get("start_date")]).toEqual([
    "14.6514",
    "121.0492",
    "2026-11-15",
  ]);

  const axe = await new AxeBuilder({ page })
    .withTags(["wcag2a", "wcag2aa", "wcag21aa"])
    .analyze();
  expect(axe.violations.map((v) => `${v.id}: ${v.help}`)).toEqual([]);
  if (SHOTS)
    await page.screenshot({
      path: join(SHOTS, "forecast.png"),
      fullPage: true,
    });
});

test("forecast accepts manual coordinates and reports an outage", async ({
  page,
}) => {
  await page.route("https://api.open-meteo.com/**", (route) =>
    route.fulfill({ status: 503, body: "down" }),
  );
  await page.goto("/forecast");
  await page.getByLabel("Place").selectOption("custom");
  await page.getByLabel(/Latitude/).fill("14.60");
  await page.getByLabel(/Longitude/).fill("121.00");
  await page.getByLabel("Race date (Manila)").fill("2026-11-15");
  await page.getByRole("button", { name: "Show forecast" }).click();
  await expect(page.getByTestId("error")).toContainText(
    "Open-Meteo unavailable",
    { timeout: 15_000 },
  );
});
