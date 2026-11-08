/**
 * Physiological Strain Index (docs/SCIENCE.md section 3). Port of blagden.physio.psi.
 * PSI = 5 (Tc - Tc0) / (39.5 - Tc0) + 5 (HR - HR0) / (180 - HR0). A negative total is
 * reported as 0; values above 10 are kept and shown as above scale. With an estimated
 * core temperature this is an estimated PSI and carries the ECTemp limitations.
 */

export const PSI_TC_CEILING_C = 39.5;
export const PSI_HR_CEILING_BPM = 180;
export const PSI_WEIGHT = 5;
export const PSI_SCALE_MAX = 10;
/** Resting heart rate when the user gives none, bpm (Blagden convention, D-014). */
export const DEFAULT_HR0_BPM = 70;

/** PSI per minute; null where the core temperature or heart rate is missing. */
export function psi(
  tc: readonly (number | null)[],
  hr: readonly (number | null)[],
  tc0: number,
  hr0: number,
): (number | null)[] {
  if (!Number.isFinite(tc0) || tc0 >= PSI_TC_CEILING_C) {
    throw new Error(
      `tc0 must be a finite temperature below ${PSI_TC_CEILING_C} C`,
    );
  }
  if (!Number.isFinite(hr0) || hr0 >= PSI_HR_CEILING_BPM) {
    throw new Error(
      `hr0 must be a finite heart rate below ${PSI_HR_CEILING_BPM} bpm`,
    );
  }
  if (tc.length !== hr.length)
    throw new Error("tc and hr must have the same length");
  return tc.map((t, i) => {
    const h = hr[i];
    if (
      t === null ||
      h === null ||
      h === undefined ||
      Number.isNaN(t) ||
      Number.isNaN(h)
    )
      return null;
    const total =
      (PSI_WEIGHT * (t - tc0)) / (PSI_TC_CEILING_C - tc0) +
      (PSI_WEIGHT * (h - hr0)) / (PSI_HR_CEILING_BPM - hr0);
    return Math.max(total, 0);
  });
}
