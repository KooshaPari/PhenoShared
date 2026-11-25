/**
 * Benchmarks for the {@link ContractVerifier} port.
 *
 * Vitest 2 ships a built-in `bench()` API (powered by tinypool + tinybench)
 * that fills the same role as `criterion` in the Rust ecosystem. The
 * `bench` script in `package.json` is `vitest bench --run`.
 *
 * Run: `bun run bench`
 */
import { bench, describe } from 'vitest';
import { BACKENDS, createVerifier } from '../../index';
import type { Contract } from '../../index';

const sample: Contract = {
  name: 'bench_no_overflow',
  predicate: 'x + 1 > x',
  target: 'fn add_one(x: u64) -> u64',
};

describe('PhenoContracts ports — benchmarks', () => {
  for (const backend of BACKENDS) {
    const v = createVerifier(backend);

    describe(`backend=${backend}`, () => {
      bench(
        'verify',
        async () => {
          await v.verify(sample);
        },
        { time: 250 }
      );

      bench(
        'discharge',
        async () => {
          await v.discharge(sample);
        },
        { time: 250 }
      );
    });
  }

  describe('registry', () => {
    bench(
      'createVerifier x 3',
      () => {
        for (const b of BACKENDS) {
          createVerifier(b);
        }
      },
      { time: 250 }
    );
  });
});
