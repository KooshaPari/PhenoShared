/**
 * phenotype-auth-ts
 *
 * TypeScript OAuth2/OIDC authentication patterns.
 *
 * xDD Methodologies:
 * - TDD: Test-driven with Vitest
 * - BDD: Scenario-based tests
 * - CDD: Contract tests for adapters
 */

export * from './domain/token';
export * from './domain/claims';
export * from './domain/errors';
export * from './ports';
export { MemoryTokenStore, asToken } from './adapters/memory-token-store';
export { PlaceholderJwtVerifier } from './adapters/jwt-provider';
