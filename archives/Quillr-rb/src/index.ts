/**
 * Quillr — a type-safe HTTP client for the Phenotype ecosystem.
 *
 * @module quillts
 */

export { createClient, QuillClient } from "./client";
export { InterceptorChain } from "./interceptor";
export { MockServer } from "./mock";
export { calculateBackoff, isRetryableStatus, isTransientError, RetryPolicy } from "./retry";
export {
  NetworkError,
  QuillError,
  TimeoutError,
} from "./types";
export type {
  ErrorInterceptor,
  Interceptor,
  InterceptorContext,
  QuillConfig,
  QuillResponse,
  RequestInterceptor,
  ResponseInterceptor,
  RetryConfig,
} from "./types";
