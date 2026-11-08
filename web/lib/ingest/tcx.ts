/** TCX reader for the browser (port of blagden.ingest.tcx). Elements matched by local name. */
import { IngestError, type RawActivity, type RawRecord } from "./types";
import { localName, localOffset, parseTime, parseXml, toFloat } from "./xml";

export function readTcx(text: string, fileName = "file"): RawActivity {
  const doc = parseXml(text);
  const records: RawRecord[] = [];
  const offsets = new Set<number>();
  let naive = 0;
  for (const point of Array.from(doc.getElementsByTagName("*"))) {
    if (localName(point) !== "trackpoint") continue;
    const r: RawRecord = {
      timeMs: null,
      hr: null,
      lat: null,
      lon: null,
      alt: null,
      speed: null,
      distance: null,
    };
    for (const child of Array.from(point.children)) {
      const name = localName(child);
      if (name === "time") {
        const t = parseTime(child.textContent);
        r.timeMs = t.ms;
        if (t.naive) naive += 1;
        if (t.offsetS !== null) offsets.add(t.offsetS);
      } else if (name === "position") {
        for (const pos of Array.from(child.children)) {
          const pn = localName(pos);
          if (pn === "latitudedegrees") r.lat = toFloat(pos.textContent);
          else if (pn === "longitudedegrees") r.lon = toFloat(pos.textContent);
        }
      } else if (name === "altitudemeters") r.alt = toFloat(child.textContent);
      else if (name === "distancemeters")
        r.distance = toFloat(child.textContent);
      else if (name === "heartratebpm") {
        for (const v of Array.from(child.children))
          if (localName(v) === "value") r.hr = toFloat(v.textContent);
      } else if (name === "extensions") {
        for (const ext of Array.from(child.getElementsByTagName("*"))) {
          if (localName(ext) === "speed" && r.speed === null)
            r.speed = toFloat(ext.textContent);
        }
      }
    }
    records.push(r);
  }
  if (records.length === 0)
    throw new IngestError(`${fileName}: no trackpoints found in the TCX file`);
  return {
    records,
    sourceFormat: "tcx",
    localUtcOffsetS: localOffset(offsets),
    notes: naive ? [`${naive} times without a zone were read as UTC`] : [],
  };
}
