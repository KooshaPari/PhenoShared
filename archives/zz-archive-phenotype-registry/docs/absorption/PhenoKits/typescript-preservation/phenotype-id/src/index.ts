/**
 * UUID generation utilities for Phenotype services.
 *
 * Provides methods for generating unique identifiers with optional prefixes
 * for different use cases.
 */

import { randomUUID } from "crypto";

/**
 * Generator provides methods for generating unique identifiers.
 */
export class Generator {
  /**
   * Generate a new random UUID v4.
   *
   * @returns String representation of a UUID v4
   */
  static generateUUID(): string {
    return randomUUID();
  }

  /**
   * Generate a new request ID using UUID v4.
   *
   * @returns Request ID with 'req-' prefix
   */
  static generateRequestID(): string {
    return `req-${randomUUID()}`;
  }

  /**
   * Generate a new trace ID using UUID v4.
   *
   * @returns Trace ID with 'trace-' prefix
   */
  static generateTraceID(): string {
    return `trace-${randomUUID()}`;
  }

  /**
   * Generate a new correlation ID using UUID v4.
   *
   * @returns Correlation ID with 'corr-' prefix
   */
  static generateCorrelationID(): string {
    return `corr-${randomUUID()}`;
  }

  /**
   * Check if the given string is a valid UUID.
   *
   * @param idStr - String to validate
   * @returns True if valid UUID, False otherwise
   */
  static isValidUUID(idStr: string): boolean {
    const uuidRegex =
      /^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i;
    return uuidRegex.test(idStr);
  }
}

export default Generator;
