import { ImageResponse } from "next/og";

import { SITE_TAGLINE } from "@/lib/site";

export const alt = "Blagden: heat intelligence for runners in the tropics";
export const size = { width: 1200, height: 630 };
export const contentType = "image/png";

/** Fetch a TrueType Newsreader cut from Google Fonts at build time. */
async function newsreader(style: "normal" | "italic"): Promise<ArrayBuffer> {
  const axis = style === "italic" ? "ital,wght@1,400" : "wght@400";
  const css = await (
    await fetch(
      `https://fonts.googleapis.com/css2?family=Newsreader:${axis}&display=swap`,
    )
  ).text();
  const url = css.match(
    /src: url\((.+?)\) format\('(?:truetype|opentype)'\)/,
  )?.[1];
  if (!url) throw new Error("Newsreader font URL not found");
  return (await fetch(url)).arrayBuffer();
}

export default async function OpenGraphImage() {
  const [regular, italic] = await Promise.all([
    newsreader("normal"),
    newsreader("italic"),
  ]);
  return new ImageResponse(
    <div
      style={{
        width: "100%",
        height: "100%",
        display: "flex",
        flexDirection: "column",
        justifyContent: "space-between",
        background: "#0c1018",
        color: "#ece6dc",
        padding: "72px 80px",
        fontFamily: "Newsreader",
      }}
    >
      <div style={{ display: "flex", fontSize: 34, color: "#f0b35e" }}>
        Blagden
      </div>
      <div style={{ display: "flex", flexDirection: "column" }}>
        <div style={{ display: "flex", fontSize: 96, lineHeight: 1.05 }}>
          The steak cooked.
        </div>
        <div
          style={{
            display: "flex",
            fontSize: 96,
            lineHeight: 1.05,
            fontStyle: "italic",
            color: "#f2836f",
          }}
        >
          He didn&rsquo;t.
        </div>
        <div
          style={{
            display: "flex",
            marginTop: 32,
            fontSize: 34,
            color: "#b4ada3",
            fontFamily: "sans-serif",
          }}
        >
          {SITE_TAGLINE}
        </div>
      </div>
      <div
        style={{
          display: "flex",
          height: 12,
          width: "100%",
          background: "linear-gradient(90deg, #1e3a5f, #f0b35e, #f2836f)",
        }}
      />
    </div>,
    {
      ...size,
      fonts: [
        { name: "Newsreader", data: regular, style: "normal", weight: 400 },
        { name: "Newsreader", data: italic, style: "italic", weight: 400 },
      ],
    },
  );
}
