import { describe, it, expect } from "vitest";
import {
  emailSchema,
  urlSchema,
  uuidSchema,
  isoTimestampSchema,
  paginationQuerySchema,
} from "./index.js";

describe("emailSchema", () => {
  it("accepts a well-formed address and trims surrounding whitespace", () => {
    const result = emailSchema.parse("  alice@example.com  ");
    expect(result).toBe("alice@example.com");
  });

  it("rejects an obviously malformed address", () => {
    expect(() => emailSchema.parse("not-an-email")).toThrow();
  });
});

describe("urlSchema", () => {
  it("accepts https and http URLs", () => {
    expect(urlSchema.parse("https://example.com/path?x=1")).toBe(
      "https://example.com/path?x=1"
    );
    expect(urlSchema.parse("http://example.com")).toBe("http://example.com");
  });

  it("rejects non-http(s) schemes", () => {
    expect(() => urlSchema.parse("ftp://example.com")).toThrow();
    expect(() => urlSchema.parse("javascript:alert(1)")).toThrow();
  });
});

describe("uuidSchema", () => {
  it("accepts a v4 UUID and lowercases it on the way out", () => {
    const result = uuidSchema.parse("550E8400-E29B-41D4-A716-446655440000");
    expect(result).toBe("550e8400-e29b-41d4-a716-446655440000");
  });

  it("rejects a string that is not a UUID", () => {
    expect(() => uuidSchema.parse("not-a-uuid")).toThrow();
  });
});

describe("isoTimestampSchema", () => {
  it("accepts an ISO 8601 timestamp with a Z timezone", () => {
    expect(isoTimestampSchema.parse("2026-06-08T12:00:00Z")).toBe(
      "2026-06-08T12:00:00Z"
    );
  });

  it("accepts a millisecond-precision timestamp with an offset", () => {
    expect(isoTimestampSchema.parse("2026-06-08T12:00:00.123+02:00")).toBe(
      "2026-06-08T12:00:00.123+02:00"
    );
  });

  it("rejects a date-only string (no time component)", () => {
    expect(() => isoTimestampSchema.parse("2026-06-08")).toThrow();
  });
});

describe("paginationQuerySchema", () => {
  it("defaults page=1 and pageSize=20 when input is empty", () => {
    const result = paginationQuerySchema.parse({});
    expect(result).toEqual({ page: 1, pageSize: 20 });
  });

  it("coerces string query values into bounded integers", () => {
    const result = paginationQuerySchema.parse({ page: "3", pageSize: "50" });
    expect(result).toEqual({ page: 3, pageSize: 50 });
  });

  it("rejects pageSize greater than 100", () => {
    expect(() => paginationQuerySchema.parse({ pageSize: 500 })).toThrow();
  });
});
