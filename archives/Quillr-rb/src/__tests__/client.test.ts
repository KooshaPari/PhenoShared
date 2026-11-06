import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { createClient } from "../client";
import { MockServer } from "../mock";
import { InterceptorChain } from "../interceptor";
import { RetryPolicy, calculateBackoff, isRetryableStatus } from "../retry";
import type { Interceptor, InterceptorContext as ICtx } from "../types";

describe("Quill HTTP Client", () => {
  it("should create a client with base URL", () => {
    const client = createClient({ baseUrl: "https://api.example.com" });
    expect(client).toBeDefined();
    expect(client).toBeInstanceOf(Object);
  });

  it("should support type-safe request methods", () => {
    const client = createClient({ baseUrl: "http://localhost:9999" });
    expect(typeof client.get).toBe("function");
    expect(typeof client.post).toBe("function");
    expect(typeof client.put).toBe("function");
    expect(typeof client.patch).toBe("function");
    expect(typeof client.delete).toBe("function");
  });

  it("should support interceptors via use()", () => {
    const client = createClient({ baseUrl: "http://localhost:9999" });
    const interceptor: Interceptor = {
      onRequest(ctx: ICtx) {
        return { ...ctx, headers: { ...ctx.headers, "X-Test": "true" } };
      },
    };
    expect(() => client.use(interceptor)).not.toThrow();
  });
});

describe("Client Configuration", () => {
  it("should accept base URL configuration", () => {
    const config = {
      baseUrl: "https://api.example.com",
      headers: { Authorization: "Bearer token" },
    };
    const client = createClient(config);
    expect(client).toBeDefined();
  });

  it("should support custom headers", () => {
    const headers = {
      "Content-Type": "application/json",
      Authorization: "Bearer test",
    };
    const client = createClient({ baseUrl: "http://localhost:9999", headers });
    expect(client).toBeDefined();
  });

  it("should support timeout configuration", () => {
    const client = createClient({ baseUrl: "http://localhost:9999", timeout: 5000 });
    expect(client).toBeDefined();
  });
});

describe("MockServer", () => {
  let mock: MockServer;

  beforeEach(() => {
    mock = new MockServer();
  });

  afterEach(() => {
    mock.reset();
  });

  it("should return a handler-registered response", async () => {
    mock.on("GET", "/users/1", { id: 1, name: "Alice" });
    const res = await mock.resolve("GET", "/users/1");
    expect(res.status).toBe(200);
    expect(res.data).toEqual({ id: 1, name: "Alice" });
  });

  it("should return 404 for unregistered routes", async () => {
    const res = await mock.resolve("GET", "/nonexistent");
    expect(res.status).toBe(404);
  });

  it("should track call count", async () => {
    expect(mock.callCount).toBe(0);
    await mock.resolve("POST", "/items", {}, { name: "test" });
    expect(mock.callCount).toBe(1);
    await mock.resolve("POST", "/items", {}, { name: "test2" });
    expect(mock.callCount).toBe(2);
  });

  it("should support custom handler functions", async () => {
    mock.onHandle("POST", "/echo", async (req) => ({
      status: 200,
      body: { echo: req.body, method: req.method },
      headers: { "content-type": "application/json" },
    }));

    const res = await mock.resolve("POST", "/echo", {}, "hello");
    expect(res.status).toBe(200);
    expect(res.data).toEqual({ echo: "hello", method: "POST" });
  });

  it("should return a CLI-usable url", () => {
    const url = mock.url();
    expect(url).toMatch(/^http:\/\/localhost:\d+\/mock$/);
  });

  it("should reset handlers and call history", async () => {
    mock.on("DELETE", "/resource/1", { deleted: true });
    await mock.resolve("DELETE", "/resource/1");
    expect(mock.callCount).toBe(1);

    mock.reset();
    expect(mock.callCount).toBe(0);
    expect(mock.calls).toHaveLength(0);

    const res = await mock.resolve("DELETE", "/resource/1");
    expect(res.status).toBe(404);
  });
});

describe("InterceptorChain", () => {
  let chain: InterceptorChain;

  beforeEach(() => {
    chain = new InterceptorChain();
  });

  it("should pass context through request interceptors", async () => {
    chain.use({
      onRequest(ctx) {
        return { ...ctx, headers: { ...ctx.headers, "X-Test": "value" } };
      },
    });

    const result = await chain.runRequestInterceptors({
      method: "GET",
      url: "/test",
      headers: {},
    });
    expect(result.headers["X-Test"]).toBe("value");
  });

  it("should chain multiple request interceptors in order", async () => {
    const order: number[] = [];
    chain.use(
      { onRequest(ctx) { order.push(1); return ctx; } },
      { onRequest(ctx) { order.push(2); return ctx; } },
    );

    await chain.runRequestInterceptors({ method: "GET", url: "/test", headers: {} });
    expect(order).toEqual([1, 2]);
  });

  it("should run response interceptors", async () => {
    chain.use({
      onResponse(resp) {
        return { ...resp, headers: { ...resp.headers, "X-Processed": "yes" } };
      },
    });

    const result = await chain.runResponseInterceptors({
      data: "ok",
      status: 200,
      statusText: "OK",
      headers: {},
    });
    expect(result.headers["X-Processed"]).toBe("yes");
  });

  it("should skip non-matching interceptors", async () => {
    const onError = vi.fn();
    chain.use({ onError });

    const result = await chain.runRequestInterceptors({
      method: "GET",
      url: "/test",
      headers: {},
    });
    expect(onError).not.toHaveBeenCalled();
    expect(result.url).toBe("/test");
  });
});

describe("Retry Logic", () => {
  it("should respect retry count configuration", () => {
    const policy = new RetryPolicy({ maxRetries: 5 });
    expect(policy.canRetry(0)).toBe(true);
    expect(policy.canRetry(4)).toBe(true);
    expect(policy.canRetry(5)).toBe(false);
  });

  it("should implement exponential backoff", () => {
    const delay = calculateBackoff(0, 200, 10_000);
    expect(delay).toBeGreaterThanOrEqual(0);
    expect(delay).toBeLessThanOrEqual(200);

    const delay2 = calculateBackoff(5, 200, 10_000);
    expect(delay2).toBeLessThanOrEqual(10_000);
  });

  it("should detect retryable status codes", () => {
    expect(isRetryableStatus(429, [429, 503])).toBe(true);
    expect(isRetryableStatus(200, [429, 503])).toBe(false);
    expect(isRetryableStatus(500, [408, 429, 500, 502, 503])).toBe(true);
  });
});
