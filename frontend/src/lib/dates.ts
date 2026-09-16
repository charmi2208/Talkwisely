/**
 * The backend stores naive UTC datetimes and serializes them without an offset
 * ("2026-09-16T18:02:11"). Browsers would read those as local time, so treat
 * offset-less timestamps as UTC.
 */
export function parseApiDate(value: string): Date {
  const hasZone = /[zZ]$|[+-]\d{2}:?\d{2}$/.test(value);
  return new Date(hasZone ? value : `${value}Z`);
}
