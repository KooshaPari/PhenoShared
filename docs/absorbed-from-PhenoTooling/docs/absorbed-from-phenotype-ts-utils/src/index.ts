/**
 * phenotype-ts-utils: shared TypeScript utility library.
 *
 * Public API:
 * - cn: className concatenation (clsx-like)
 * - truncate: string truncation with suffix
 * - slugify: URL-safe slug from any string
 * - formatDate: ISO/US/EU date formatter
 * - parseDate: parse ISO 8601 string safely
 * - addDays: add N days to a date
 * - debounce: debounce a function
 * - throttle: throttle a function
 * - deepMerge: deep merge two objects
 * - deepClone: deep-clone a JSON-serializable value
 * - sleep: promise-based setTimeout
 * - retry: retry a function with exponential backoff
 * - uniqueBy: array dedup by key
 * - groupBy: group an array by a key extractor
 */
export { cn, truncate, slugify } from './string.js';
export { formatDate, parseDate, addDays } from './date.js';
export { debounce, throttle } from './function.js';
export { deepMerge, deepClone } from './object.js';
export { sleep, retry } from './async.js';
export { uniqueBy, groupBy } from './array.js';
