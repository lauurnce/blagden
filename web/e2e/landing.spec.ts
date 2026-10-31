import AxeBuilder from "@axe-core/playwright";
import { expect, test } from "@playwright/test";

const SECTIONS = [
  "A heated room, 1775",
  "Humid heat is a different problem from hot weather.",
  "Three steps, all on your side.",
  "Four hours of heart rate, read as core temperature.",
  "Every number has a source.",
  "What Blagden cannot tell you.",
];

for (const colorScheme of ["light", "dark"] as const) {
  test(`landing page has every section and passes axe (${colorScheme})`, async ({
    page,
  }) => {
    await page.emulateMedia({ colorScheme });
    await page.goto("/");
    await expect(page.getByRole("heading", { level: 1 })).toHaveText(
      /The steak cooked\. He didn.t\./,
    );
    for (const name of SECTIONS) {
      await expect(page.getByRole("heading", { level: 2, name })).toBeVisible();
    }
    await expect(
      page.getByRole("link", { name: "Try the demo" }),
    ).toHaveAttribute("href", "/demo");
    await expect(
      page.getByRole("link", { name: "View on GitHub" }),
    ).toHaveAttribute("href", "https://github.com/lauurnce/blagden");
    const axe = await new AxeBuilder({ page })
      .withTags(["wcag2a", "wcag2aa", "wcag21aa"])
      .analyze();
    expect(axe.violations).toEqual([]);
  });
}

test("landing page fits a 360 px screen without sideways scroll", async ({
  page,
}) => {
  await page.setViewportSize({ width: 360, height: 800 });
  await page.goto("/");
  const width = await page.evaluate(() => document.documentElement.scrollWidth);
  expect(width).toBeLessThanOrEqual(360);
});

test("serves robots.txt, the sitemap and the Open Graph image", async ({
  request,
}) => {
  expect(await (await request.get("/robots.txt")).text()).toContain("Sitemap:");
  expect(await (await request.get("/sitemap.xml")).text()).toContain(
    "/forecast",
  );
  const og = await request.get("/opengraph-image");
  expect(og.headers()["content-type"]).toBe("image/png");
});
