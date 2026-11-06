import { afterEach, describe, expect, it, vi } from "vitest";
import { createClient } from "../client";
import { MockServer } from "../mock";
import { QuillError } from "../types";

const jsonResponse = (body: unknown, status = 200): Response =>
  new Response(JSON.stringify(body), {
    status,
    statusText: status >= 400 ? "Failure" : "OK",
    headers: { "content-type": "application/json", "x-request-id": "req-1" },
  });

afterEach(() => {
  vi.unstubAllGlobals();
  vi.restoreAllMocks();
});

describe("FR-1: Client Creation", () => {
  it("uses base URL, default headers, timeout, and exposes typed methods", async () => {
    const fetchMock = vi.fn().mockResolvedValue(jsonResponse({ id: 1 }));
    vi.stubGlobal("fetch", fetchMock);
    const client = createClient({
      baseUrl: "https://api.example.com/",
      headers: { Authorization: "Bearer x" },
      timeout: 5_000,
    });

    await client.get<{ id: number }>("/users/1");

    expect(fetchMock).toHaveBeenCalledWith(
      "https://api.example.com/users/1",
      expect.objectContaining({
        method: "GET",
        headers: { Authorization: "Bearer x" },
        signal: expect.any(AbortSignal),
      }),
    );
    for (const method of ["get", "post", "put", "delete"]) {
      expect(client[method as "get"]).toBeTypeOf("function");
    }
  });
});

describe("FR-2: Typed HTTP Methods", () => {
  it.each([
    ["GET", "get", undefined],
    ["POST", "post", { name: "Alice" }],
    ["PUT", "put", { name: "Bob" }],
    ["DELETE", "delete", undefined],
  ] as const)("dispatches %s through the typed %s method", async (verb, method, body) => {
    const fetchMock = vi.fn().mockResolvedValue(jsonResponse({ ok: true }));
    vi.stubGlobal("fetch", fetchMock);
    const client = createClient({ baseUrl: "https://api.example.com" });

    if (method === "get" || method === "delete") {
      await client[method]<{ ok: boolean }>("/resource");
    } else {
      await client[method]<{ ok: boolean }>("/resource", body);
    }

    expect(fetchMock).toHaveBeenCalledWith(
      "https://api.example.com/resource",
      expect.objectContaining({ method: verb }),
    );
  });
});

describe("FR-3: Request Interceptors", () => {
  it("modifies headers, body, and URL before dispatch", async () => {
    const fetchMock = vi.fn().mockResolvedValue(jsonResponse({ ok: true }));
    vi.stubGlobal("fetch", fetchMock);
    const client = createClient({ baseUrl: "https://api.example.com" });
    client.use({
      onRequest: (ctx) => ({
        ...ctx,
        url: "/intercepted",
        headers: { ...ctx.headers, Authorization: "Bearer intercepted" },
        body: { transformed: true },
      }),
    });

    await client.post("/original", { transformed: false });

    expect(fetchMock).toHaveBeenCalledWith(
      "https://api.example.com/intercepted",
      expect.objectContaining({
        headers: expect.objectContaining({ Authorization: "Bearer intercepted" }),
        body: JSON.stringify({ transformed: true }),
      }),
    );
  });
});

describe("FR-4: Response Interceptors", () => {
  it("transforms a successful response before returning it", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(jsonResponse({ value: 1 })));
    const client = createClient({ baseUrl: "https://api.example.com" });
    client.use({
      onResponse: async (response) => ({
        ...response,
        data: { value: (response.data as { value: number }).value + 1 },
      }),
    });

    const response = await client.get<{ value: number }>("/value");

    expect(response.data).toEqual({ value: 2 });
  });
});

describe("FR-5: Error Interceptors", () => {
  it("invokes an error interceptor for an HTTP 5xx failure", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(jsonResponse({ error: true }, 500)));
    const client = createClient({
      baseUrl: "https://api.example.com",
      retry: { maxRetries: 0 },
    });
    const onError = vi.fn((error: QuillError) => error);
    client.use({ onError });

    await expect(client.get("/failure")).rejects.toMatchObject({ status: 500 });
    expect(onError).toHaveBeenCalledOnce();
  });
});

describe("FR-6: Retry with Backoff", () => {
  it("honours retry config and returns a later successful response", async () => {
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce(jsonResponse({ error: true }, 503))
      .mockResolvedValueOnce(jsonResponse({ ok: true }));
    vi.stubGlobal("fetch", fetchMock);
    const client = createClient({
      baseUrl: "https://api.example.com",
      retry: { maxRetries: 1, baseDelay: 0, maxDelay: 0 },
    });

    const response = await client.get<{ ok: boolean }>("/eventual-success");

    expect(fetchMock).toHaveBeenCalledTimes(2);
    expect(response.data.ok).toBe(true);
  });
});

describe("FR-7: Mock Utilities", () => {
  it("simulates success and error responses without network access", async () => {
    const mock = new MockServer();
    mock.on("GET", "/ok", { ok: true });
    mock.on("GET", "/failure", { error: "expected" }, 503);

    await expect(mock.resolve("GET", "/ok")).resolves.toMatchObject({
      status: 200,
      data: { ok: true },
    });
    await expect(mock.resolve("GET", "/failure")).resolves.toMatchObject({
      status: 503,
      data: { error: "expected" },
    });
    expect(mock.callCount).toBe(2);
  });
});
