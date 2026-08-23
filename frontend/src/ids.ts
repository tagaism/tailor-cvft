/** Positive integer route id, or null. Invalid strings return null, never NaN. */
export function parseRouteId(value: string | undefined): number | null {
  if (!value || !/^[1-9]\d*$/.test(value)) return null;
  const n = Number(value);
  if (Number.isNaN(n) || !Number.isSafeInteger(n) || n < 1) return null;
  return n;
}
