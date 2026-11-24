import { z } from "zod";

/**
 * RFC 5322-friendly email string.
 *
 * Zod's built-in `.email()` applies a pragmatic regex that covers the vast
 * majority of real-world addresses without enforcing the full RFC 5322
 * grammar (which is intentionally impractical to implement in a regex).
 */
export const emailSchema = z
  .string({ required_error: "email is required" })
  .trim()
  .min(1, "email must not be empty")
  .max(254, "email must be at most 254 characters")
  .email("email must be a valid address");

/**
 * HTTP or HTTPS URL string.
 *
 * Returns the validated string (not a `URL` object) so it can be stored /
 * serialized as-is. Rejects empty strings and non-HTTP(S) schemes
 * (`ftp://`, `data:`, `javascript:`, ...).
 */
export const urlSchema = z
  .string({ required_error: "url is required" })
  .trim()
  .url("url must be a valid URL")
  .refine(
    (value) => {
      const scheme = value.toLowerCase().match(/^([a-z][a-z0-9+\-.]*):/);
      return scheme !== null && ["http", "https"].includes(scheme[1] ?? "");
    },
    { message: "url must use the http or https scheme" }
  );

/**
 * RFC 4122 UUID string. Accepts versions 1–5 and the nil/all-ones forms.
 *
 * Always lowercased on output to give consumers a canonical representation.
 */
export const uuidSchema = z
  .string({ required_error: "uuid is required" })
  .trim()
  .uuid("uuid must be a valid RFC 4122 identifier")
  .transform((value) => value.toLowerCase());

/**
 * ISO 8601 timestamp string (e.g. `2026-06-08T12:00:00Z`,
 * `2026-06-08T12:00:00.123+02:00`).
 *
 * Validated via `Date.parse` round-trip: the input must parse cleanly and
 * the original string is returned unchanged so the consumer keeps the
 * precision / timezone offset that the producer sent.
 */
export const isoTimestampSchema = z
  .string({ required_error: "isoTimestamp is required" })
  .trim()
  .refine(
    (value) => !Number.isNaN(Date.parse(value)),
    "isoTimestamp must be a valid ISO 8601 date-time"
  )
  .refine(
    (value) => /^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:\d{2})$/.test(
      value
    ),
    "isoTimestamp must include a time component (e.g. 2026-06-08T12:00:00Z)"
  );

/**
 * Common 1-based pagination query schema.
 *
 * - `page` defaults to `1`, must be a positive integer
 * - `pageSize` defaults to `20`, must be in `[1, 100]`
 *
 * Accepts the values as strings (the way they arrive on an HTTP query
 * string) and coerces them to numbers; rejects out-of-range / non-integer
 * input with a clear message.
 */
export const paginationQuerySchema = z.object({
  page: z
    .union([z.string(), z.number()])
    .optional()
    .transform((value) => (value === undefined ? 1 : Number(value)))
    .pipe(
      z
        .number({ required_error: "page is required", invalid_type_error: "page must be a number" })
        .int("page must be an integer")
        .min(1, "page must be >= 1")
    ),
  pageSize: z
    .union([z.string(), z.number()])
    .optional()
    .transform((value) => (value === undefined ? 20 : Number(value)))
    .pipe(
      z
        .number({ required_error: "pageSize is required", invalid_type_error: "pageSize must be a number" })
        .int("pageSize must be an integer")
        .min(1, "pageSize must be >= 1")
        .max(100, "pageSize must be <= 100")
    ),
});

export type PaginationQuery = z.infer<typeof paginationQuerySchema>;
