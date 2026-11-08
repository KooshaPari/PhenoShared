/** Format a Date or ISO string as YYYY-MM-DD. */
export function formatDate(d: Date | string, format: 'iso' | 'us' | 'eu' = 'iso'): string {
  const date = typeof d === 'string' ? new Date(d) : d;
  const y = date.getUTCFullYear();
  const m = String(date.getUTCMonth() + 1).padStart(2, '0');
  const day = String(date.getUTCDate()).padStart(2, '0');
  switch (format) {
    case 'iso':
      return `${y}-${m}-${day}`;
    case 'us':
      return `${m}/${day}/${y}`;
    case 'eu':
      return `${day}/${m}/${y}`;
  }
}

/** Parse an ISO 8601 string. Returns null on failure. */
export function parseDate(s: string): Date | null {
  const d = new Date(s);
  return isNaN(d.getTime()) ? null : d;
}

/** Add N days to a date, returning a new Date. */
export function addDays(d: Date, days: number): Date {
  const r = new Date(d);
  r.setUTCDate(r.getUTCDate() + days);
  return r;
}
