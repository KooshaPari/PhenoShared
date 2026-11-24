/**
 * phenotype-core-ts - TypeScript SDK for Phenotype Core
 *
 * This package provides TypeScript/JavaScript bindings for the
 * Phenotype Core library.
 */

// Core types
export {
  EntityId,
  Entity,
  ValidationResult,
  validateEntity,
  generateId
} from './entity';

// Config types
export {
  Config,
  ConfigSource,
  Configuration,
  ConfigStore
} from './config';
