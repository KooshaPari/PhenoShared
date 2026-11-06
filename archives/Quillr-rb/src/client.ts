/**
 * Quill HTTP client — a type-safe HTTP client with interceptors and retry.
 *
 * @module client
 */

import { InterceptorChain } from "./interceptor";
import { NetworkError, QuillError, TimeoutError } from "./types";
import type { Interceptor, QuillConfig, QuillResponse, RetryConfig } from "./types";
import { isTransientError, RetryPolicy } from "./retry";

// ---------------------------------------------------------------------------
// createClient
// ---------------------------------------------------------------------------

/**
 * Create a new Quill HTTP client.
 *
 * @example
 * ```ts
 * const api = createClient({
 *   baseUrl: "https://api.example.com",
 *   headers: { Authorization: "Bearer token" },
 * });
 *
 * const user = await api.get<User>("/users/123");
 * ```
 */
export function createClient(config: QuillConfig): QuillClient {
  return new QuillClient(config);
}

// ---------------------------------------------------------------------------
// QuillClient
// ---------------------------------------------------------------------------

/**
 * Type-safe HTTP client with interceptors, retry, and timeout support.
 */
export class QuillClient {
  private readonly baseUrl: string;
  private readonly defaultHeaders: Record<string, string>;
  private readonly timeout: number;
  private readonly retryPolicy: RetryPolicy;
  private readonly chain: InterceptorChain;

  constructor(config: QuillConfig, retryConfig: RetryConfig | undefined = config.retry) {
    this.baseUrl = config.baseUrl.replace(/\/+$/, "");
    this.defaultHeaders = { ...config.headers };
    this.timeout = config.timeout ?? 30_000;
    this.retryPolicy = new RetryPolicy(retryConfig);
    this.chain = new InterceptorChain();
  }

  // -----------------------------------------------------------------------
  // Interceptor registration
  // -----------------------------------------------------------------------

  /** Register one or more interceptors. */
  use(...interceptors: Interceptor[]): void {
    this.chain.use(...interceptors);
  }

  // -----------------------------------------------------------------------
  // HTTP methods
  // -----------------------------------------------------------------------

  /** Perform a GET request. */
  async get<T = unknown>(
    url: string,
    headers?: Record<string, string>,
  ): Promise<QuillResponse<T>> {
    return this.request<T>("GET", url, undefined, headers);
  }

  /** Perform a POST request. */
  async post<T = unknown>(
    url: string,
    body?: unknown,
    headers?: Record<string, string>,
  ): Promise<QuillResponse<T>> {
    return this.request<T>("POST", url, body, headers);
  }

  /** Perform a PUT request. */
  async put<T = unknown>(
    url: string,
    body?: unknown,
    headers?: Record<string, string>,
  ): Promise<QuillResponse<T>> {
    return this.request<T>("PUT", url, body, headers);
  }

  /** Perform a PATCH request. */
  async patch<T = unknown>(
    url: string,
    body?: unknown,
    headers?: Record<string, string>,
  ): Promise<QuillResponse<T>> {
    return this.request<T>("PATCH", url, body, headers);
  }

  /** Perform a DELETE request. */
  async delete<T = unknown>(
    url: string,
    headers?: Record<string, string>,
  ): Promise<QuillResponse<T>> {
    return this.request<T>("DELETE", url, undefined, headers);
  }

  // -----------------------------------------------------------------------
  // Core request logic
  // -----------------------------------------------------------------------

  /**
   * Execute an HTTP request with interceptor pipeline and retry.
   */
  private async request<T>(
    method: string,
    url: string,
    body?: unknown,
    extraHeaders?: Record<string, string>,
  ): Promise<QuillResponse<T>> {
    // Build initial context
    const ctx = await this.chain.runRequestInterceptors({
      method,
      url,
      headers: { ...this.defaultHeaders, ...extraHeaders },
      body,
    });

    // Resolve the full URL
    const fullUrl = ctx.url.startsWith("http")
      ? ctx.url
      : `${this.baseUrl}${ctx.url.startsWith("/") ? "" : "/"}${ctx.url}`;

    // Serialise body
    let bodyInit: BodyInit | undefined;
    const headers: Record<string, string> = { ...ctx.headers };
    if (ctx.body !== undefined) {
      bodyInit = JSON.stringify(ctx.body);
      if (!headers["Content-Type"]) {
        headers["Content-Type"] = "application/json";
      }
    }

    // Build fetch init
    const init: RequestInit & { signal: AbortSignal } = {
      method: ctx.method,
      headers,
      body: bodyInit,
      signal: ctx.signal ?? new AbortController().signal,
    };

    // Execute with retry loop
    let lastError: Error | null = null;
    for (let attempt = 0; ; attempt++) {
      try {
        const controller = new AbortController();
        const timeoutId = setTimeout(() => controller.abort(), this.timeout);

        let response: Response;
        try {
          response = await fetch(fullUrl, { ...init, signal: controller.signal });
        } finally {
          clearTimeout(timeoutId);
        }

        // Parse response body
        const contentType = response.headers.get("content-type") ?? "";
        let data: unknown;
        if (contentType.includes("application/json")) {
          data = await response.json();
        } else {
          data = await response.text();
        }

        // Collect headers
        const respHeaders: Record<string, string> = {};
        response.headers.forEach((v, k) => {
          respHeaders[k] = v;
        });

        const quillResponse: QuillResponse<T> = {
          data: data as T,
          status: response.status,
          statusText: response.statusText,
          headers: respHeaders,
        };

        // Check for retryable status
        if (!response.ok && this.retryPolicy.isRetryableStatus(response.status)) {
          if (this.retryPolicy.canRetry(attempt)) {
            const delay = this.retryPolicy.delayForAttempt(attempt);
            await sleep(delay);
            continue;
          }
          // Ran out of retries — treat as error
          lastError = new QuillError(
            `HTTP ${response.status}: ${response.statusText}`,
            { status: response.status, statusText: response.statusText, data },
          );
          break;
        }

        // Run response interceptors
        return await this.chain.runResponseInterceptors(quillResponse);
      } catch (err) {
        const error = err instanceof Error ? err : new Error(String(err));

        // AbortError = timeout
        if (error.name === "AbortError") {
          lastError = new TimeoutError();
        } else if (isTransientError(error)) {
          lastError = error.name === "TimeoutError"
            ? error
            : new NetworkError(error.message);
        } else {
          lastError = error instanceof QuillError ? error : new QuillError(error.message);
        }

        if (
          this.retryPolicy.canRetry(attempt) &&
          (isTransientError(error) || error.name === "AbortError")
        ) {
          const delay = this.retryPolicy.delayForAttempt(attempt);
          await sleep(delay);
          continue;
        }
        break;
      }
    }

    // Run error interceptors
    const processed = await this.chain.runErrorInterceptors(
      lastError instanceof QuillError
        ? lastError
        : new QuillError(lastError?.message ?? "Unknown error"),
    );
    throw processed;
  }
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

/** Promise-based sleep helper. */
function sleep(ms: number): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, ms));
}
