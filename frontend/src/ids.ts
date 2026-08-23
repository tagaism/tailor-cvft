/** Matches FastAPI 404 detail for GET /api/jobs/{id}. */
export const JOB_NOT_FOUND = "Job not found.";

/** Matches FastAPI 404 detail for GET /api/companies/{id}. */
export const COMPANY_NOT_FOUND = "Company not found.";

/** Positive integer route id, or null. Invalid strings return null, never NaN. */
export function parseRouteId(value: string | undefined): number | null {
  if (!value || !/^[1-9]\d*$/.test(value)) return null;
  const n = Number(value);
  if (Number.isNaN(n) || !Number.isSafeInteger(n) || n < 1) return null;
  return n;
}
