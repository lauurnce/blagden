import { Inter, Newsreader } from "next/font/google";

/** Clean sans for the interface. Self-hosted by next/font at build time. */
export const sans = Inter({
  subsets: ["latin"],
  display: "swap",
  variable: "--font-sans",
});

/** Serif display face for headlines and the story. */
export const serif = Newsreader({
  subsets: ["latin"],
  display: "swap",
  style: ["normal", "italic"],
  variable: "--font-serif",
});
