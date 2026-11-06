/**
 * Core types for the Quill HTTP client library.
 *
 * @module types
 */

/** Configuration for the Quill HTTP client. */
export interface QuillConfig {
  /** Base URL prepended to all requests. */
  baseUrl: string;
  /** Default headers sent with every request. */
  headers?: Record<string, string>;
  /** Request timeout in milliseconds (default: 30_000). */
  timeout?: number;
  /** Retry policy overrides. */
  retry?: RetryConfig;
}

/** Configuration for retry behaviour. */
export interface RetryConfig {
  /** Maximum number of retry attempts (default: 3). */
  maxRetries?: number;
  /** Initial backoff delay in milliseconds (default: 200). */
  baseDelay?: number;
  /** Maximum backoff delay in milliseconds (default: 10_000). */
  maxDelay?: number;
  /** HTTP status codes that trigger a retry (default: [408, 429, 500, 502, 503]). */
  retryableStatuses?: number[];
}

/** A successful HTTP response returned by the client. */
export interface QuillResponse<T = unknown> {
  /** Parsed response body. */
  data: T;
  /** HTTP status code. */
  status: number;
  /** HTTP status text. */
  statusText: string;
  /** Response headers. */
  headers: Record<string, string>;
}

// ---------------------------------------------------------------------------
// Interceptor interfaces
// ---------------------------------------------------------------------------

/** Context passed through the interceptor pipeline. */
export interface InterceptorContext {
  /** HTTP method. */
  method: string;
  /** Request URL (may be relative). */
  url: string;
  /** Request headers. */
  headers: Record<string, string>;
  /** Optional request body. */
  body?: unknown;
  /** Signal for aborting the request. */
  signal?: AbortSignal;
}

/** A request interceptor can inspect / modify a request before it is sent. */
export interface RequestInterceptor {
  /** Invoked before the request is dispatched. */
  onRequest(ctx: InterceptorContext): Promise<InterceptorContext> | InterceptorContext;
}

/** A response interceptor can inspect / modify a response after it arrives. */
export interface ResponseInterceptor {
  /** Invoked after a successful response is received. */
  onResponse<T>(response: QuillResponse<T>): Promise<QuillResponse<T>> | QuillResponse<T>;
}

/** An error interceptor can inspect / transform errors. */
export interface ErrorInterceptor {
  /** Invoked when a request fails. */
  onError(error: QuillError): Promise<QuillError> | QuillError;
}

/** Union type for any interceptor. */
export type Interceptor = RequestInterceptor | ResponseInterceptor | ErrorInterceptor;

// ---------------------------------------------------------------------------
// Error types
// ---------------------------------------------------------------------------

/** Base error class for all Quill HTTP errors. */
export class QuillError extends Error {
  /** HTTP status code (undefined for network / timeout errors). */
  public readonly status?: number;
  /** HTTP status text. */
  public readonly statusText?: string;
  /** Parsed error body from the server. */
  public readonly data?: unknown;

  constructor(
    message: string,
    options?: { status?: number; statusText?: string; data?: unknown },
  ) {
    super(message);
    this.name = "QuillError";
    this.status = options?.status;
    this.statusText = options?.statusText;
    this.data = options?.data;
  }
}

/** Error thrown when a request fails due to a network issue. */
export class NetworkError extends QuillError {
  constructor(message = "Network error") {
    super(message);
    this.name = "NetworkError";
  }
}

/** Error thrown when a request times out. */
export class TimeoutError extends QuillError {
  constructor(message = "Request timed out") {
    super(message);
    this.name = "TimeoutError";
  }
}
