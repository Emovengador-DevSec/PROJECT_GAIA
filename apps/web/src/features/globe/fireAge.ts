/** FIRMS age scale: < 24 h, 1–3 days, 4–7 days. Measured from the timeline cutoff when replaying. */
export const FIRE_AGE_COLORS = ["#ff2d2d", "#ff8a00", "#b4532a"] as const;
export const FIRE_AGE_ALPHA = [.8, .72, .5] as const;
const DAY_MS = 86_400_000;

export function fireAge(date: string, reference: number): 0 | 1 | 2 {
  const age = reference - Date.parse(date);
  return age < DAY_MS ? 0 : age < 3 * DAY_MS ? 1 : 2;
}
