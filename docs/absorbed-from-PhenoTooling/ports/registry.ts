//! Registry — concrete adapter factory for contract verifier backends.
//!
//! Each backend (Prusti, Kani, …) is registered here as an adapter that
//! implements the ContractVerifier interface.

import type { ContractVerifier, Backend } from './contract_verifier';

/// Error thrown when `createVerifier` is called with an unregistered backend.
export class BackendNotFoundError extends Error {
  readonly backend: string;
  readonly available: readonly string[];

  constructor(backend: string, available: readonly string[]) {
    super(`No ContractVerifier registered for backend "${backend}".\nAvailable: ${available.join(', ')}`);
    this.name = 'BackendNotFoundError';
    this.backend = backend;
    this.available = available;
  }
}

/// Map of registered backends keyed by their canonical name.
const backends = new Map<string, ContractVerifier>();

/// Register a backend by name. Called at module load time by each adapter.
export function registerBackend(name: Backend, verifier: ContractVerifier): void {
  backends.set(name, verifier);
}

/// Create a ContractVerifier for the given backend, defaulting to "prusti".
///
/// @throws {BackendNotFoundError} if the requested backend has not been registered.
export function createVerifier(backend: Backend = 'prusti'): ContractVerifier {
  const v = backends.get(backend);
  if (!v) {
    throw new BackendNotFoundError(backend, [...backends.keys()]);
  }
  return v;
}

/// Check whether a backend has been registered.
export function isBackend(name: string): name is Backend {
  return backends.has(name);
}

/// Return the list of registered backend names (runtime registry introspection).
export function backendNames(): Backend[] {
  return [...backends.keys()] as Backend[];
}

/**
 * Canonical list of all backend names defined by the {@link Backend} union.
 *
 * Derived statically from the type system (not from the runtime registry) so that
 * the list is always populated, even before any adapter has called
 * {@link registerBackend}. This is the list consumed by bench + property tests
 * (see `ports/tests/property/contract_verifier.property.test.ts:96`,
 * `ports/tests/bench/contract_verifier.bench.ts:11`). For runtime registry
 * state, use {@link backendNames} instead.
 */
export const BACKENDS = ['kani', 'prusti', 'coq'] as const satisfies readonly Backend[];

/// Re-export the Backend type from the contract verifier for convenience.
export type { Backend, Verdict, ContractVerifier } from './contract_verifier';
