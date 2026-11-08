/**
 * Domain models for configuration management.
 *
 * Following hexagonal architecture:
 * - Pure domain logic with no external dependencies
 * - Zod schemas for runtime validation
 * - Immutable config objects
 *
 * xDD Principles:
 * - KISS: Simple data classes
 * - DRY: Shared validation schemas
 * - PoLA: Descriptive error messages
 */

import { z } from 'zod';

// =============================================================================
// Schema Definitions
// =============================================================================

/**
 * Base config value types.
 */
export const ConfigValueSchema = z.union([
  z.string(),
  z.number(),
  z.boolean(),
  z.array(z.string()),
  z.record(z.string(), z.string()),
]);

export type ConfigValue = z.infer<typeof ConfigValueSchema>;

/**
 * Config entry with metadata.
 */
export const ConfigEntrySchema = z.object({
  key: z.string(),
  value: ConfigValueSchema,
  source: z.string().optional(),
  timestamp: z.number().optional(),
});

export type ConfigEntry = z.infer<typeof ConfigEntrySchema>;

/**
 * Config snapshot - immutable config state.
 */
export const ConfigSnapshotSchema = z.object({
  entries: z.record(ConfigValueSchema),
  sources: z.array(z.string()),
  version: z.string(),
  timestamp: z.number(),
});

export type ConfigSnapshot = z.infer<typeof ConfigSnapshotSchema>;

/**
 * Validation error with context.
 */
export const ConfigErrorSchema = z.object({
  message: z.string(),
  path: z.array(z.string()),
  value: z.unknown(),
  context: z.record(z.unknown()).optional(),
});

export type ConfigError = z.infer<typeof ConfigErrorSchema>;

// =============================================================================
// Domain Classes
// =============================================================================

/**
 * Configuration validation error.
 *
 * Following PoLA (Principle of Least Astonishment):
 * - Descriptive error messages
 * - Path to the invalid field
 * - Original value for debugging
 */
export class ConfigValidationError extends Error {
  constructor(
    message: string,
    public readonly path: string[],
    public readonly value: unknown,
    public readonly context?: Record<string, unknown>
  ) {
    super(message);
    this.name = 'ConfigValidationError';
  }

  toJSON(): ConfigError {
    return {
      message: this.message,
      path: this.path,
      value: this.value,
      context: this.context,
    };
  }
}

/**
 * Config source not found error.
 */
export class ConfigSourceNotFoundError extends Error {
  constructor(
    message: string,
    public readonly source: string,
    public readonly context?: Record<string, unknown>
  ) {
    super(message);
    this.name = 'ConfigSourceNotFoundError';
  }
}

/**
 * Immutable configuration snapshot.
 */
export class ImmutableConfig {
  public readonly entries: ReadonlyMap<string, ConfigValue>;
  public readonly sources: ReadonlyArray<string>;

  constructor(
    entries: ReadonlyMap<string, ConfigValue>,
    sources: ReadonlyArray<string>,
    public readonly version: string
  ) {
    this.entries = new Map(entries);
    this.sources = [...sources];
  }

  get(key: string): ConfigValue | undefined {
    return this.entries.get(key);
  }

  has(key: string): boolean {
    return this.entries.has(key);
  }

  toSnapshot(): ConfigSnapshot {
    return {
      entries: Object.fromEntries(this.entries),
      sources: [...this.sources],
      version: this.version,
      timestamp: Date.now(),
    };
  }
}
