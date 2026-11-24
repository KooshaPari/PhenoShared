/** Concatenate class names, dropping falsy values. */
export function cn(...classes: Array<string | undefined | null | false>): string {
  return classes.filter(Boolean).join(' ');
}

/** Truncate a string to maxLen, appending suffix if cut. */
export function truncate(s: string, maxLen = 80, suffix = '...'): string {
  if (maxLen < suffix.length) {
    throw new Error(`maxLen (${maxLen}) must be >= len(suffix) (${suffix.length})`);
  }
  if (s.length <= maxLen) return s;
  return s.slice(0, maxLen - suffix.length) + suffix;
}

/** Convert a string to a URL-safe slug. */
export function slugify(s: string): string {
  return (
    s
      .toLowerCase()
      .replace(/[^a-z0-9]+/g, '-')
      .replace(/^-|-$/g, '') || 'untitled'
  );
}
