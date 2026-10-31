/** Site-wide constants for metadata, links and the sitemap. */

const vercelHost = process.env.VERCEL_PROJECT_PRODUCTION_URL;

/** Canonical origin. Vercel sets VERCEL_PROJECT_PRODUCTION_URL at build time. */
export const SITE_URL =
  process.env.NEXT_PUBLIC_SITE_URL ??
  (vercelHost ? `https://${vercelHost}` : "http://localhost:3000");

export const SITE_NAME = "Blagden";
export const SITE_TAGLINE = "Heat intelligence for runners in the tropics.";
export const SITE_DESCRIPTION =
  "Estimate core temperature from your run's heart rate, forecast WBGT for race morning in Metro Manila, and plan a pace for the heat. Runs in your browser.";

export const REPO_URL = "https://github.com/lauurnce/blagden";
export const SCIENCE_URL = `${REPO_URL}/blob/main/docs/SCIENCE.md`;
export const AUTHOR_NAME = "Lawrence Panes";
export const AUTHOR_URL = "https://lauurnce.is-a.dev";
