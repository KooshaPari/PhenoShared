/**
 * Mock server utilities for testing Quill HTTP client consumers.
 *
 * Provides a lightweight mock HTTP server that can be used in tests without
 * making real network requests.
 *
 * @module mock
 */

import type { QuillResponse } from "./types";

// ---------------------------------------------------------------------------
// MockHandler
// ---------------------------------------------------------------------------

/** A handler function that receives a request and returns a mock response. */
export type MockHandler = (req: MockRequest) => MockResponse | Promise<MockResponse>;

/** A mock HTTP request received by the mock server. */
export interface MockRequest {
  method: string;
  url: string;
  /** Parsed pathname (e.g. `/users/123`). */
  pathname: string;
  /** Query parameters parsed from the URL. */
  query: Record<string, string>;
  headers: Record<string, string>;
  body?: unknown;
}

/** A mock HTTP response to return from the mock server. */
export interface MockResponse {
  status: number;
  statusText?: string;
  headers?: Record<string, string>;
  body?: unknown;
}

// ---------------------------------------------------------------------------
// MockServer
// ---------------------------------------------------------------------------

/**
 * A lightweight mock server for testing.
 *
 * @example
 * ```ts
 * const mock = new MockServer();
 * mock.on("GET", "/users/123", { id: 1, name: "Alice" });
 *
 * const client = createClient({ baseUrl: mock.url() });
 * const res = await client.get("/users/123");
 * expect(res.data).toEqual({ id: 1, name: "Alice" });
 * ```
 */
export class MockServer {
  private handlers: Map<string, MockHandler> = new Map();
  private _callCount = 0;
  private _calls: { method: string; url: string; body?: unknown }[] = [];

  /**
   * Register a handler that returns a static body.
   *
   * Shortcut for simple cases. The handler matches `METHOD pathname` (e.g.
   * `GET /users/123`).
   */
  on(method: string, pathname: string, body: unknown, status = 200): void {
    const key = `${method.toUpperCase()} ${pathname}`;
    this.handlers.set(key, () =>
      Promise.resolve({ status, body, headers: { "content-type": "application/json" } }),
    );
  }

  /**
   * Register a custom handler function.
   */
  onHandle(method: string, pathname: string, handler: MockHandler): void {
    const key = `${method.toUpperCase()} ${pathname}`;
    this.handlers.set(key, handler);
  }

  /** Return the number of requests received. */
  get callCount(): number {
    return this._callCount;
  }

  /** Return the list of received calls for assertions. */
  get calls(): { method: string; url: string; body?: unknown }[] {
    return [...this._calls];
  }

  /** Get the base URL for this mock server (to pass to `createClient`). */
  url(): string {
    return `http://localhost:${Math.floor(Math.random() * 40000) + 20000}/mock`;
  }

  /** Resolve a mock request and return a QuillResponse. */
  async resolve(
    method: string,
    url: string,
    headers?: Record<string, string>,
    body?: unknown,
  ): Promise<QuillResponse<unknown>> {
    this._callCount++;
    const { pathname, query } = parseUrl(url);
    this._calls.push({ method, url, body });

    const key = `${method.toUpperCase()} ${pathname}`;
    const handler = this.handlers.get(key);

    if (!handler) {
      return {
        data: { error: `No handler for ${key}` },
        status: 404,
        statusText: "Not Found",
        headers: { "content-type": "application/json" },
      };
    }

    const mockReq: MockRequest = { method, url, pathname, query, headers: headers ?? {}, body };
    const mockResp = await handler(mockReq);

    return {
      data: mockResp.body,
      status: mockResp.status,
      statusText: mockResp.statusText ?? "",
      headers: mockResp.headers ?? {},
    };
  }

  /** Reset all handlers and call history. */
  reset(): void {
    this.handlers.clear();
    this._callCount = 0;
    this._calls = [];
  }
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function parseUrl(url: string): { pathname: string; query: Record<string, string> } {
  const idx = url.indexOf("?");
  const pathname = idx === -1 ? url : url.slice(0, idx);
  const queryString = idx === -1 ? "" : url.slice(idx + 1);
  const query: Record<string, string> = {};
  if (queryString) {
    for (const part of queryString.split("&")) {
      const eq = part.indexOf("=");
      if (eq === -1) {
        query[decodeURIComponent(part)] = "";
      } else {
        query[decodeURIComponent(part.slice(0, eq))] = decodeURIComponent(
          part.slice(eq + 1),
        );
      }
    }
  }
  return { pathname, query };
}
