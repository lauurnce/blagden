/**
 * Solar position, Astronomical Almanac 1990 low-precision formulas, as used by
 * Liljegren's WBGT code (docs/SCIENCE.md section 4). Port of blagden.weather.solar.
 * Refraction for a standard sea-level atmosphere is added to the altitude.
 */

export interface SunPosition {
  elevation_deg: number;
  refraction_deg: number;
  zenith_deg: number;
  cos_zenith: number;
  azimuth_deg: number;
  distance_au: number;
}

const BEGIN_MONTH = [0, 0, 31, 59, 90, 120, 151, 181, 212, 243, 273, 304, 334];
const rad = (d: number) => (d * Math.PI) / 180;
const deg = (r: number) => (r * 180) / Math.PI;
/** Fractional part with the sign of x, like C modf. */
const frac = (x: number) => x - Math.trunc(x);

function dayNumber(year: number, month: number, day: number): number {
  const leap = (year % 4 === 0 && year % 100 !== 0) || year % 400 === 0;
  return (BEGIN_MONTH[month] ?? 0) + day + (leap && month > 2 ? 1 : 0);
}

/** Sun position for an instant (a Date is always an absolute instant). */
export function sunPosition(
  when: Date,
  latDeg: number,
  lonDeg: number,
): SunPosition {
  if (!(latDeg >= -90 && latDeg <= 90 && lonDeg >= -180 && lonDeg <= 180)) {
    throw new Error("latitude must be in -90..90 and longitude in -180..180");
  }
  const year = when.getUTCFullYear();
  if (year < 1950 || year > 2049)
    throw new Error("the low-precision formulas cover 1950 to 2049");
  const utHours =
    when.getUTCHours() +
    when.getUTCMinutes() / 60 +
    (when.getUTCSeconds() + when.getUTCMilliseconds() / 1000) / 3600;
  const day = when.getUTCDate() + utHours / 24;
  const deltaYears = year - 2000;
  let deltaDays =
    deltaYears * 365 +
    Math.trunc(deltaYears / 4) +
    dayNumber(year, when.getUTCMonth() + 1, when.getUTCDate());
  if (year > 2000) deltaDays += 1;
  let daysJ2000 = deltaDays - 1.5;
  const centJ2000 = daysJ2000 / 36525;
  let ut = frac(day);
  daysJ2000 += ut;
  ut *= 24;

  const meanAnomaly =
    frac((357.528 + 0.9856003 * daysJ2000) / 360) * 2 * Math.PI;
  const meanLongitude =
    frac((280.46 + 0.9856474 * daysJ2000) / 360) * 2 * Math.PI;
  const meanObliquity = rad(23.439 - 4.0e-7 * daysJ2000);
  const eclipticLong =
    rad(1.915 * Math.sin(meanAnomaly) + 0.02 * Math.sin(2 * meanAnomaly)) +
    meanLongitude;
  const distance =
    1.00014 -
    0.01671 * Math.cos(meanAnomaly) -
    0.00014 * Math.cos(2 * meanAnomaly);
  let apRa = Math.atan2(
    Math.cos(meanObliquity) * Math.sin(eclipticLong),
    Math.cos(eclipticLong),
  );
  if (apRa < 0) apRa += 2 * Math.PI;
  const apRaHours = frac(apRa / (2 * Math.PI)) * 24;
  const apDec = Math.asin(Math.sin(meanObliquity) * Math.sin(eclipticLong));

  let gmst0h =
    24110.54841 +
    centJ2000 * (8640184.812866 + centJ2000 * (0.093104 - centJ2000 * 6.2e-6));
  gmst0h = frac(gmst0h / 3600 / 24) * 24;
  if (gmst0h < 0) gmst0h += 24;
  let lmst = gmst0h + ut * 1.00273790934 + lonDeg / 15;
  lmst = frac(lmst / 24) * 24;
  if (lmst < 0) lmst += 24;

  let localHa = lmst - apRaHours;
  if (localHa < -12) localHa += 24;
  else if (localHa > 12) localHa -= 24;
  const lat = rad(latDeg);
  const ha = (localHa / 24) * 2 * Math.PI;
  const altitude = Math.asin(
    Math.sin(apDec) * Math.sin(lat) +
      Math.cos(apDec) * Math.cos(ha) * Math.cos(lat),
  );
  const cosAlt = Math.cos(altitude);
  const tanAlt = Math.abs(altitude) < 1.57079615 ? Math.tan(altitude) : 6.0e6;
  const cosAz =
    (Math.sin(apDec) * Math.cos(lat) -
      Math.cos(apDec) * Math.cos(ha) * Math.sin(lat)) /
    cosAlt;
  const sinAz = -((Math.cos(apDec) * Math.sin(ha)) / cosAlt);
  let azimuth = Math.acos(Math.max(-1, Math.min(1, cosAz)));
  if (Math.atan2(sinAz, cosAz) < 0) azimuth = 2 * Math.PI - azimuth;
  const altDeg = deg(altitude);

  const p = 1013.25;
  const temp = 15.0;
  let refraction: number;
  if (altDeg < -1 || tanAlt === 6.0e6) refraction = 0;
  else if (altDeg < 19.225) {
    refraction = (0.1594 + altDeg * (0.0196 + 0.00002 * altDeg)) * p;
    refraction /= (1 + altDeg * (0.505 + 0.0845 * altDeg)) * (273 + temp);
  } else refraction = (0.00452 * (p / (273 + temp))) / tanAlt;
  const elevation = altDeg + refraction;
  const zenith = 90 - elevation;
  return {
    elevation_deg: elevation,
    refraction_deg: refraction,
    zenith_deg: zenith,
    cos_zenith: Math.cos(rad(zenith)),
    azimuth_deg: deg(azimuth),
    distance_au: distance,
  };
}
