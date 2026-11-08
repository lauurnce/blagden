/** XML helpers shared by the GPX and TCX readers (port of blagden.ingest._xmlutil). */

export const localName = (el: Element) =>
  (el.localName || el.nodeName).replace(/^.*:/, "").toLowerCase();

export function toFloat(text: string | null | undefined): number | null {
  if (text === null || text === undefined) return null;
  const s = text.trim();
  if (s === "" || !/^[+-]?(\d+\.?\d*|\.\d+)([eE][+-]?\d+)?$/.test(s))
    return null;
  const v = Number(s);
  return Number.isFinite(v) ? v : null;
}

const ZONE = /(Z|[+-]\d{2}:?\d{2})$/i;

/** Parse an ISO 8601 time to UTC milliseconds. Times without a zone are read as UTC and flagged. */
export function parseTime(text: string | null | undefined): {
  ms: number | null;
  offsetS: number | null;
  naive: boolean;
} {
  if (!text) return { ms: null, offsetS: null, naive: false };
  const s = text.trim();
  const zone = s.match(ZONE);
  const ms = Date.parse(zone ? s : `${s}Z`);
  if (Number.isNaN(ms)) return { ms: null, offsetS: null, naive: false };
  if (!zone) return { ms, offsetS: null, naive: true };
  const z = zone[1]!;
  if (z.toUpperCase() === "Z") return { ms, offsetS: 0, naive: false };
  const sign = z.startsWith("-") ? -1 : 1;
  const digits = z.replace(/[+:-]/g, "");
  const offsetS =
    sign *
    (Number(digits.slice(0, 2)) * 3600 + Number(digits.slice(2, 4)) * 60);
  return { ms, offsetS, naive: false };
}

export function parseXml(text: string): Document {
  const doc = new DOMParser().parseFromString(text, "application/xml");
  if (doc.getElementsByTagName("parsererror").length > 0)
    throw new Error("not well-formed XML");
  return doc;
}

export function localOffset(offsets: Set<number>): number | null {
  const nonzero = [...offsets].filter((o) => o !== 0);
  return nonzero.length === 1 ? nonzero[0]! : null;
}
