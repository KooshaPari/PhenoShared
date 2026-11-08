import { describe, expect, it } from 'vitest';
import { KaniVerifier } from '../adapters/kani';
import { PrustiVerifier } from '../adapters/prusti';
import { createVerifier, BackendNotFoundError } from '../registry';

describe('PhenoContracts ports', () => {
  it('KaniVerifier.backend', () => {
    expect(new KaniVerifier().backend).toBe('kani');
  });
  it('PrustiVerifier.backend', () => {
    expect(new PrustiVerifier().backend).toBe('prusti');
  });
  it('KaniVerifier.verify ok', async () => {
    const v = await new KaniVerifier().verify({ name: 'n', predicate: 'true', target: 'fn' });
    expect(v.ok).toBe(true);
  });
  it('PrustiVerifier.discharge', async () => {
    const v = await new PrustiVerifier().discharge({ name: 'n', predicate: 'true', target: 'fn' });
    expect(v.ok).toBe(true);
  });
  it('ContractVerifier interface object-safe', () => {
    const _s: import('../contract_verifier').ContractVerifier = new KaniVerifier();
  });
  it('createVerifier throws BackendNotFoundError for unknown backend', () => {
    expect(() => createVerifier('coq' as never)).toThrow(BackendNotFoundError);
  });
  it('BackendNotFoundError has expected name and properties', () => {
    try {
      createVerifier('coq' as never);
    } catch (e) {
      expect(e).toBeInstanceOf(BackendNotFoundError);
      const err = e as BackendNotFoundError;
      expect(err.name).toBe('BackendNotFoundError');
      expect(err.backend).toBe('coq');
      expect(err.available).toEqual(['kani', 'prusti']);
    }
  });
});
