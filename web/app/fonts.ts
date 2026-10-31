import { Inter, Newsreader } from "next/font/google";

/** Clean sans for the interface. Self-hosted by next/font at build time; "optional" avoids a late swap that delays LCP. */
export const sans = Inter({
  subsets: ["latin"],
  display: "optional",
  variable: "--font-sans",
});

/** Serif display face for headlines and the story. */
export const serif = Newsreader({
  subsets: ["latin"],
  display: "optional",
  style: ["normal", "italic"],
  variable: "--font-serif",
});
