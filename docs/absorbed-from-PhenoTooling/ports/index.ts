// PhenoContracts ports — barrel re-export for hexagonal interface layer.
//
// This file re-exports all public types and constructors so that tests,
// benchmarks, and adapters import from a stable path (../../index or
// ../index depending on depth).
//
// Adapter side-effect imports: importing `./adapters/*` is what causes each
// backend to register itself with the registry (see `ports/registry.ts`).
// Re-exporting them here ensures the registry is populated as soon as any
// downstream consumer imports the barrel — required for property tests and
// benchmarks that iterate over `BACKENDS` and call `createVerifier(...)`.

import './adapters/coq';
import './adapters/kani';
import './adapters/prusti';

export type { Backend, Contract, Verdict, ContractVerifier } from './contract_verifier';
export { BACKENDS, createVerifier, isBackend, backendNames, registerBackend } from './registry';
export { CoqVerifier } from './adapters/coq';
export { KaniVerifier } from './adapters/kani';
export { PrustiVerifier } from './adapters/prusti';
