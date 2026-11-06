/**
 * Retry logic with exponential backoff and jitter for the Quill HTTP client.
 *
 * @module retry
 */

import type { RetryConfig } from "./types";

// ---------------------------------------------------------------------------
// Defaults
// ---------------------------------------------------------------------------

const DEFAULT_MAX_RETRIES = 3;
const DEFAULT_BASE_DELAY = 200;
const DEFAULT_MAX_DELAY = 10_000;
const DEFAULT_RETRYABLE_STATUSES = [408, 429, 500, 502, 503];

// ---------------------------------------------------------------------------
// Backoff helpers
// ---------------------------------------------------------------------------

/**
 * Calculate the delay before the `attempt`-th retry (0-based), using
 * exponential backoff with full jitter.
 *
 * delay = min(maxDelay, baseDelay * 2^attempt) * random[0, 1)
 */
export function calculateBackoff(
  attempt: number,
  baseDelay: number,
  maxDelay: number,
): number {
  const cap = Math.min(maxDelay, baseDelay * 2 ** attempt);
  return Math.round(Math.random() * cap);
}

/**
 * Returns `true` when the given HTTP status code should trigger a retry.
 */
export function isRetryableStatus(status: number, retryableStatuses: number[]): boolean {
  return retryableStatuses.includes(status);
}

/**
 * Check if the error is transient (network or timeout).
 */
export function isTransientError(error: Error): boolean {
  const name = error.name ?? "";
  return name === "NetworkError" || name === "TimeoutError" || name === "TypeError";
}

// ---------------------------------------------------------------------------
// Retry policy
// ---------------------------------------------------------------------------

/**
 * Immutable retry policy built from a (partial) user config.
 */
export class RetryPolicy {
  readonly maxRetries: number;
  readonly baseDelay: number;
  readonly maxDelay: number;
  readonly retryableStatuses: readonly number[];

  constructor(config?: RetryConfig) {
    this.maxRetries = config?.maxRetries ?? DEFAULT_MAX_RETRIES;
    this.baseDelay = config?.baseDelay ?? DEFAULT_BASE_DELAY;
    this.maxDelay = config?.maxDelay ?? DEFAULT_MAX_DELAY;
    this.retryableStatuses = config?.retryableStatuses ?? DEFAULT_RETRYABLE_STATUSES;
  }

  /** Whether another retry is allowed (attempt is 0-based). */
  canRetry(attempt: number): boolean {
    return attempt < this.maxRetries;
  }

  /** Whether this HTTP status should trigger a retry. */
  isRetryableStatus(status: number): boolean {
    return isRetryableStatus(status, [...this.retryableStatuses]);
  }

  /** Compute delay before the given attempt. */
  delayForAttempt(attempt: number): number {
    return calculateBackoff(attempt, this.baseDelay, this.maxDelay);
  }
}
