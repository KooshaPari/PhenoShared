/**
 * Property-based tests for the {@link ContractVerifier} port.
 *
 * Mirrors the role of `proptest!` in the Rust ecosystem: arbitrary
 * {@link Contract} values are fed into every backend, and we assert
 * structural invariants of the returned {@link Verdict}.
 *
 * This file is the TypeScript analogue of `ports/tests/property/...`
 * referenced by the `test:property` script in `package.json`.
 */
import fc from 'fast-check';
import { describe, expect, it } from 'vitest';
import { BACKENDS, createVerifier } from '../../index';
import type { Contract, Verdict } from '../../index';

/** Generator: any well-formed {@link Contract} (non-empty strings, etc). */
const contractArb: fc.Arbitrary<Contract> = fc.record({
  name: fc.string({ minLength: 1, maxLength: 64 }),
  predicate: fc.string({ minLength: 1, maxLength: 256 }),
  target: fc.string({ minLength: 1, maxLength: 128 }),
});

/** A {@link Verdict} must satisfy the documented structural invariants. */
function assertVerdictInvariants(v: Verdict): void {
  expect(typeof v.ok).toBe('boolean');
  expect(Number.isFinite(v.durationMs)).toBe(true);
  expect(v.durationMs).toBeGreaterThanOrEqual(0);
  if (v.ok) {
    expect(v.proof).toBeDefined();
    expect(typeof v.proof).toBe('string');
    expect(v.counterexample).toBeUndefined();
  } else {
    expect(v.counterexample).toBeDefined();
    expect(typeof v.counterexample).toBe('string');
    expect(v.proof).toBeUndefined();
  }
}

describe('PhenoContracts ports — property-based', () => {
  // 100 iterations is the default for fast-check; bump to 200 for higher
  // confidence without slowing the suite materially.
  const NUM_RUNS = 200;

  for (const backend of BACKENDS) {
    describe(`backend=${backend}`, () => {
      const v = createVerifier(backend);

      it('verify always returns a Verdict honoring the invariants', async () => {
        await fc.assert(
          fc.asyncProperty(contractArb, async (c) => {
            const verdict = await v.verify(c);
            assertVerdictInvariants(verdict);
            // Backend tag is always present in the proof string.
            expect(verdict.proof).toContain(`${backend}:`);
            // Contract name is preserved.
            expect(verdict.proof).toContain(c.name);
          }),
          { numRuns: NUM_RUNS }
        );
      });

      it('discharge always returns a Verdict honoring the invariants', async () => {
        await fc.assert(
          fc.asyncProperty(contractArb, async (c) => {
            const verdict = await v.discharge(c);
            assertVerdictInvariants(verdict);
            expect(verdict.proof).toContain(`${backend}:`);
            expect(verdict.proof).toContain(c.name);
          }),
          { numRuns: NUM_RUNS }
        );
      });

      it('verify and discharge agree on the same Contract (idempotence)', async () => {
        await fc.assert(
          fc.asyncProperty(contractArb, async (c) => {
            const a = await v.verify(c);
            const b = await v.discharge(c);
            expect(b).toEqual(a);
          }),
          { numRuns: NUM_RUNS }
        );
      });

      it('backend field is stable across calls', () => {
        fc.assert(
          fc.property(fc.constant(null), () => {
            expect(v.backend).toBe(backend);
          }),
          { numRuns: NUM_RUNS }
        );
      });
    });
  }

  it('BACKENDS list has no duplicates and is non-empty', () => {
    fc.assert(
      fc.property(fc.constant(null), () => {
        expect(BACKENDS.length).toBeGreaterThan(0);
        expect(new Set(BACKENDS).size).toBe(BACKENDS.length);
      }),
      { numRuns: 10 }
    );
  });
});
