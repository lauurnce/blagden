/**
 * GPX reader for the browser (port of blagden.ingest.gpx). Heart rate is found by element name
 * anywhere in a point's extensions (Garmin TrackPointExtension v1/v2, Cluetrust, heartrate, heart_rate).
 */
import { IngestError, type RawActivity, type RawRecord } from "./types";
import { localName, localOffset, parseTime, parseXml, toFloat } from "./xml";

const HR_NAMES = new Set(["hr", "heartrate", "heart_rate"]);

export function readGpx(text: string, fileName = "file"): RawActivity {
  const doc = parseXml(text);
  const records: RawRecord[] = [];
  const offsets = new Set<number>();
  let naive = 0;
  for (const point of Array.from(doc.getElementsByTagName("*"))) {
    if (localName(point) !== "trkpt") continue;
    let timeMs: number | null = null;
    let alt: number | null = null;
    let hr: number | null = null;
    let speed: number | null = null;
    for (const child of Array.from(point.children)) {
      const name = localName(child);
      if (name === "time") {
        const t = parseTime(child.textContent);
        timeMs = t.ms;
        if (t.naive) naive += 1;
        if (t.offsetS !== null) offsets.add(t.offsetS);
      } else if (name === "ele") {
        alt = toFloat(child.textContent);
      } else if (name === "extensions") {
        for (const ext of [
          child,
          ...Array.from(child.getElementsByTagName("*")),
        ]) {
          const en = localName(ext);
          if (HR_NAMES.has(en) && hr === null) hr = toFloat(ext.textContent);
          else if (en === "speed" && speed === null)
            speed = toFloat(ext.textContent);
        }
      }
    }
    records.push({
      timeMs,
      hr,
      lat: toFloat(point.getAttribute("lat")),
      lon: toFloat(point.getAttribute("lon")),
      alt,
      speed,
      distance: null,
    });
  }
  if (records.length === 0)
    throw new IngestError(`${fileName}: no track points found in the GPX file`);
  return {
    records,
    sourceFormat: "gpx",
    localUtcOffsetS: localOffset(offsets),
    notes: naive ? [`${naive} times without a zone were read as UTC`] : [],
  };
}
