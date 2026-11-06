/**
 * FR-QLL-001: Client Creation
 * Verifies: createClient returns a QuillClient instance with proper configuration
 * FR-QLL-006: Error Types
 * Verifies: QuillError, NetworkError, TimeoutError are properly thrown
 */
import { describe, it, expect } from "vitest";
import { createClient } from "../client";
import { QuillError, NetworkError, TimeoutError } from "../types";

describe("FR-QLL-001: Client Creation", () => {
  it("should create a client with base URL and headers", () => {
    const client = createClient({
      baseUrl: "https://api.example.com",
      headers: { Authorization: "Bearer test-token" },
    });
    expect(client).toBeDefined();
    expect(typeof client.get).toBe("function");
  });
});

describe("FR-QLL-006: Error Types", () => {
  it("should construct QuillError with status", () => {
    const err = new QuillError("Not Found", {
      status: 404,
      statusText: "Not Found",
      data: { detail: "missing" },
    });
    expect(err).toBeInstanceOf(Error);
    expect(err.name).toBe("QuillError");
    expect(err.status).toBe(404);
    expect(err.statusText).toBe("Not Found");
    expect(err.data).toEqual({ detail: "missing" });
    expect(err.message).toBe("Not Found");
  });

  it("should construct QuillError without options", () => {
    const err = new QuillError("generic");
    expect(err.status).toBeUndefined();
    expect(err.statusText).toBeUndefined();
    expect(err.data).toBeUndefined();
  });

  it("should construct NetworkError", () => {
    const err = new NetworkError("connection refused");
    expect(err).toBeInstanceOf(QuillError);
    expect(err).toBeInstanceOf(Error);
    expect(err.name).toBe("NetworkError");
    expect(err.message).toBe("connection refused");
  });

  it("should construct TimeoutError with default message", () => {
    const err = new TimeoutError();
    expect(err).toBeInstanceOf(QuillError);
    expect(err.name).toBe("TimeoutError");
    expect(err.message).toBe("Request timed out");
  });

  it("should construct TimeoutError with custom message", () => {
    const err = new TimeoutError("Custom timeout message");
    expect(err.name).toBe("TimeoutError");
    expect(err.message).toBe("Custom timeout message");
  });
});
