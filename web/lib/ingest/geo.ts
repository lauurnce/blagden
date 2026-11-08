/** Distance on a spherical Earth (port of blagden.ingest.geo). GRS80 mean radius (Moritz 2000). */
export const EARTH_MEAN_RADIUS_M = 6_371_008.7714;
const rad = (d: number) => (d * Math.PI) / 180;

export function haversineM(
  lat1: number,
  lon1: number,
  lat2: number,
  lon2: number,
): number {
  const p1 = rad(lat1);
  const p2 = rad(lat2);
  const a =
    Math.sin((p2 - p1) / 2) ** 2 +
    Math.cos(p1) * Math.cos(p2) * Math.sin((rad(lon2) - rad(lon1)) / 2) ** 2;
  return (
    2 * EARTH_MEAN_RADIUS_M * Math.asin(Math.sqrt(Math.min(Math.max(a, 0), 1)))
  );
}

/** Cumulative path length; rows without a position carry the distance so far (never interpolated). */
export function cumulativeDistanceM(
  lat: (number | null)[],
  lon: (number | null)[],
): (number | null)[] {
  const out: (number | null)[] = [];
  let total: number | null = null;
  let prev: [number, number] | null = null;
  for (let i = 0; i < lat.length; i++) {
    const la = lat[i];
    const lo = lon[i];
    if (la !== null && la !== undefined && lo !== null && lo !== undefined) {
      total =
        prev === null ? 0 : (total ?? 0) + haversineM(prev[0], prev[1], la, lo);
      prev = [la, lo];
    }
    out.push(total);
  }
  return out;
}
