/**
 * phenotype-config-ts
 *
 * TypeScript configuration management with Zod validation.
 *
 * xDD Methodologies:
 * - TDD: Test-driven with contract tests
 * - BDD: Behavior-driven with scenario naming
 * - DDD: Domain-driven with bounded context
 * - CDD: Contract-driven with port/adapter verification
 */

export * from './domain/config';
export * from './ports/config-source';
export * from './adapters/env-adapter';
export * from './adapters/file-adapter';
