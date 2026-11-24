/**
 * Adapter fail-closed contract tests.
 *
 * Hardening per the verifier-honesty repair: adapters must never return
 * `ok: true` unless a configured real backend was actually invoked and
 * returned valid evidence. Unsupported / unconfigured backend, missing
 * tool, timeout, nonzero exit, negative result, and malformed output
 * must surface as an explicit `ok: false` Verdict with a `counterexample`
 * describing the failure mode.
 *
 * Tests exercise:
 *   - fail-closed when no command is configured
 *   - fail-closed when the configured command is not on PATH
 *   - fail-closed on nonzero exit / negative result
 *   - fail-closed on timeout
 *   - fail-closed on malformed output
 *   - success only when a real backend is invoked and returns valid evidence
 *   - the spawn path uses shell:false argv (a controlled fake executable proves this)
 */
import { existsSync, mkdtempSync, rmSync, writeFileSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { afterAll, beforeAll, describe, expect, it } from 'vitest';
import { CoqVerifier } from '../coq';
import { KaniVerifier } from '../kani';
import type { SpawnResult } from '../runner';
import { PrustiVerifier } from '../prusti';
import type { Contract } from '../../contract_verifier';

const sample: Contract = { name: 'add_one', predicate: 'x + 1 > x', target: 'fn add_one(x: u64) -> u64' };

function correlatedEvidence(payload: string, evidence: Record<string, unknown>): string {
  const request = JSON.parse(payload) as { requestId: string; contractHash: string };
  return JSON.stringify({ ...evidence, requestId: request.requestId, contractHash: request.contractHash });
}

/** A deterministic in-memory runner for unit tests. */
function makeFakeRunner(
  behavior: (argv: readonly string[], payload: string) => Partial<SpawnResult> & { exitCode: number | null }
) {
  return {
    async run(
      argv: readonly string[],
      opts: { stdin: string; timeoutMs: number; maxOutputBytes: number }
    ): Promise<SpawnResult> {
      const out = behavior(argv, opts.stdin);
      const stdout = Buffer.from(out.stdout ?? '');
      const stderr = Buffer.from(out.stderr ?? '');
      return {
        exitCode: out.exitCode,
        signal: out.signal ?? null,
        stdout,
        stderr,
        timedOut: out.timedOut ?? false,
        durationMs: out.durationMs ?? 1,
        spawnError: out.spawnError,
        spawnErrorMessage: out.spawnErrorMessage,
        outputTruncated: out.outputTruncated,
      };
    },
  };
}

describe('PhenoContracts adapters — fail-closed', () => {
  describe('Kani', () => {
    it('ok=false and no proof when no command is configured', async () => {
      const v = new KaniVerifier();
      const verdict = await v.verify(sample);
      expect(verdict.ok).toBe(false);
      expect(verdict.proof).toBeUndefined();
      expect(verdict.counterexample).toBeDefined();
      expect(verdict.counterexample).toMatch(/not configured|command/i);
    });

    it('ok=false and no proof when configured command is missing (ENOENT)', async () => {
      // Inject a runner that mimics spawn ENOENT: exitCode=null, signal=null, no output.
      const runner = makeFakeRunner(() => ({
        exitCode: null,
        signal: null,
        spawnError: true,
        spawnErrorMessage: 'spawn ENOENT',
      }));
      const v = new KaniVerifier({ command: ['definitely-not-a-real-binary-xyz'], runner });
      const verdict = await v.verify(sample);
      expect(verdict.ok).toBe(false);
      expect(verdict.proof).toBeUndefined();
      expect(verdict.counterexample).toMatch(/ENOENT|not found|missing/i);
    });

    it('ok=false on nonzero exit (negative result)', async () => {
      const runner = makeFakeRunner(() => ({
        exitCode: 1,
        stdout: 'Check failed: arithmetic overflow at x=0\n',
      }));
      const v = new KaniVerifier({ command: ['fake-kani'], runner });
      const verdict = await v.verify(sample);
      expect(verdict.ok).toBe(false);
      expect(verdict.proof).toBeUndefined();
      expect(verdict.counterexample).toContain('arithmetic overflow');
    });

    it('ok=false on timeout (no synthetic proof)', async () => {
      const runner = makeFakeRunner(() => ({ exitCode: null, signal: 'SIGKILL', timedOut: true, stderr: 'killed' }));
      const v = new KaniVerifier({ command: ['slow-kani'], runner, timeoutMs: 100 });
      const verdict = await v.verify(sample);
      expect(verdict.ok).toBe(false);
      expect(verdict.proof).toBeUndefined();
      expect(verdict.counterexample).toMatch(/timeout|timed out/i);
    });

    it('ok=true only when exit=0 and non-empty stdout evidence', async () => {
      const runner = makeFakeRunner((_argv, payload) => ({
        exitCode: 0,
        stdout: correlatedEvidence(payload, { ok: true, backend: 'kani', version: 'test-1', proof: 'verified' }),
      }));
      const v = new KaniVerifier({ command: ['kani'], runner });
      const verdict = await v.verify(sample);
      expect(verdict.ok).toBe(true);
      expect(verdict.proof).toBe('kani@test-1:verified');
      expect(verdict.counterexample).toBeUndefined();
    });

    it('ok=false on empty stdout (malformed evidence)', async () => {
      const runner = makeFakeRunner(() => ({ exitCode: 0, stdout: '   \n  ' }));
      const v = new KaniVerifier({ command: ['kani'], runner });
      const verdict = await v.verify(sample);
      expect(verdict.ok).toBe(false);
      expect(verdict.proof).toBeUndefined();
      expect(verdict.counterexample).toMatch(/malformed|empty|no evidence/i);
    });

    it.each([
      { ok: true, backend: 'prusti', version: 'test-1', proof: 'wrong backend' },
      { ok: true, backend: 'kani', version: '', proof: 'missing version' },
      { ok: true, backend: 'kani', version: 'test-1', proof: '' },
      { ok: false, backend: 'kani', version: 'test-1', counterexample: '' },
    ])('ok=false on invalid protocol evidence %#', async (evidence) => {
      const runner = makeFakeRunner(() => ({ exitCode: 0, stdout: JSON.stringify(evidence) }));
      const verdict = await new KaniVerifier({ command: ['kani'], runner }).verify(sample);
      expect(verdict.ok).toBe(false);
      expect(verdict.counterexample).toMatch(/malformed/i);
    });

    it('fails closed when correlation fields are absent or mismatched', async () => {
      for (const evidence of [
        { ok: true, backend: 'kani', version: 'test-1', proof: 'verified' },
        {
          ok: true,
          backend: 'kani',
          version: 'test-1',
          proof: 'verified',
          requestId: 'stale-request',
          contractHash: 'stale-hash',
        },
      ]) {
        const runner = makeFakeRunner(() => ({ exitCode: 0, stdout: JSON.stringify(evidence) }));
        const verdict = await new KaniVerifier({ command: ['kani'], runner }).verify(sample);
        expect(verdict.ok).toBe(false);
        expect(verdict.counterexample).toMatch(/malformed|correlation mismatch/i);
      }
    });

    it('preserves a backend-declared negative result', async () => {
      const runner = makeFakeRunner((_argv, payload) => ({
        exitCode: 0,
        stdout: correlatedEvidence(payload, {
          ok: false,
          backend: 'kani',
          version: 'test-1',
          counterexample: 'assertion failed',
        }),
      }));
      const verdict = await new KaniVerifier({ command: ['kani'], runner }).verify(sample);
      expect(verdict.ok).toBe(false);
      expect(verdict.counterexample).toContain('verification_false: kani@test-1: assertion failed');
    });

    it('discharge behaves identically to verify on the same contract', async () => {
      const runner = makeFakeRunner((_argv, payload) => ({
        exitCode: 0,
        stdout: correlatedEvidence(payload, { ok: true, backend: 'kani', version: 'test-1', proof: 'verified' }),
      }));
      const v = new KaniVerifier({ command: ['kani'], runner });
      const a = await v.verify(sample);
      const b = await v.discharge(sample);
      expect(b).toEqual(a);
    });

    it('fails closed when the runner reports truncated output', async () => {
      const runner = makeFakeRunner(() => ({ exitCode: null, signal: 'SIGKILL', outputTruncated: true }));
      const v = new KaniVerifier({ command: ['kani'], runner, maxOutputBytes: 64 });
      const verdict = await v.verify(sample);
      expect(verdict.ok).toBe(false);
      expect(verdict.proof).toBeUndefined();
      expect(verdict.counterexample).toMatch(/capture cap/i);
    });
  });

  describe('Prusti', () => {
    it('ok=false and no proof when no command is configured', async () => {
      const v = new PrustiVerifier();
      const verdict = await v.discharge(sample);
      expect(verdict.ok).toBe(false);
      expect(verdict.proof).toBeUndefined();
      expect(verdict.counterexample).toMatch(/not configured|command/i);
    });

    it('ok=false on missing tool (ENOENT)', async () => {
      const runner = makeFakeRunner(() => ({
        exitCode: null,
        spawnError: true,
        spawnErrorMessage: 'spawn ENOENT',
      }));
      const v = new PrustiVerifier({ command: ['nope'], runner });
      const verdict = await v.verify(sample);
      expect(verdict.ok).toBe(false);
      expect(verdict.proof).toBeUndefined();
      expect(verdict.counterexample).toMatch(/ENOENT|missing/i);
    });

    it('ok=false on nonzero exit', async () => {
      const runner = makeFakeRunner(() => ({ exitCode: 2, stdout: 'verification failed: precondition\n' }));
      const v = new PrustiVerifier({ command: ['prusti'], runner });
      const verdict = await v.verify(sample);
      expect(verdict.ok).toBe(false);
      expect(verdict.proof).toBeUndefined();
      expect(verdict.counterexample).toContain('precondition');
    });

    it('ok=false on timeout', async () => {
      const runner = makeFakeRunner(() => ({ exitCode: null, signal: 'SIGKILL', timedOut: true }));
      const v = new PrustiVerifier({ command: ['prusti'], runner, timeoutMs: 50 });
      const verdict = await v.verify(sample);
      expect(verdict.ok).toBe(false);
      expect(verdict.proof).toBeUndefined();
      expect(verdict.counterexample).toMatch(/timeout/i);
    });

    it('ok=true on real exit=0 evidence', async () => {
      const runner = makeFakeRunner((_argv, payload) => ({
        exitCode: 0,
        stdout: correlatedEvidence(payload, { ok: true, backend: 'prusti', version: 'test-1', proof: 'verified' }),
      }));
      const v = new PrustiVerifier({ command: ['prusti'], runner });
      const verdict = await v.verify(sample);
      expect(verdict.ok).toBe(true);
      expect(verdict.proof).toBe('prusti@test-1:verified');
    });
  });

  describe('Coq', () => {
    it('identifies itself as the coq backend', () => {
      expect(new CoqVerifier().backend).toBe('coq');
    });

    it('ok=false and no proof when no command is configured', async () => {
      const v = new CoqVerifier();
      const verdict = await v.verify(sample);
      expect(verdict.ok).toBe(false);
      expect(verdict.proof).toBeUndefined();
      expect(verdict.counterexample).toMatch(/not configured/i);
    });

    it('ok=false on missing tool', async () => {
      const runner = makeFakeRunner(() => ({
        exitCode: null,
        spawnError: true,
        spawnErrorMessage: 'spawn ENOENT',
      }));
      const v = new CoqVerifier({ command: ['coq'], runner });
      const verdict = await v.verify(sample);
      expect(verdict.ok).toBe(false);
      expect(verdict.proof).toBeUndefined();
    });

    it('ok=false on nonzero exit (proof not completed)', async () => {
      const runner = makeFakeRunner(() => ({ exitCode: 1, stdout: 'Unable to unify terms.\n' }));
      const v = new CoqVerifier({ command: ['coqc'], runner });
      const verdict = await v.verify(sample);
      expect(verdict.ok).toBe(false);
      expect(verdict.proof).toBeUndefined();
      expect(verdict.counterexample).toContain('unify');
    });

    it('ok=true only on exit=0 with non-empty evidence', async () => {
      const runner = makeFakeRunner((_argv, payload) => ({
        exitCode: 0,
        stdout: correlatedEvidence(payload, { ok: true, backend: 'coq', version: 'test-1', proof: 'QED' }),
      }));
      const v = new CoqVerifier({ command: ['coqc'], runner });
      const verdict = await v.verify(sample);
      expect(verdict.ok).toBe(true);
      expect(verdict.proof).toBe('coq@test-1:QED');
    });

    it('ok=false on empty/malformed evidence', async () => {
      const runner = makeFakeRunner(() => ({ exitCode: 0, stdout: '' }));
      const v = new CoqVerifier({ command: ['coqc'], runner });
      const verdict = await v.verify(sample);
      expect(verdict.ok).toBe(false);
      expect(verdict.proof).toBeUndefined();
    });
  });

  describe('real spawn — shell:false argv with a controlled fake executable', () => {
    let tmp: string;
    let fakePath: string;

    beforeAll(() => {
      tmp = mkdtempSync(join(tmpdir(), 'phenoc-'));
      fakePath = join(tmp, 'fake-prover.sh');
      // The fake prover prints whatever was passed on argv[1] (the contract JSON marker)
      // so we can prove argv wasn't flattened/shell-parsed. It echoes "argv:N" where N = argc.
      writeFileSync(
        fakePath,
        `#!/bin/sh
if [ "$1" = "ok" ]; then
  req=$(cat)
  rid=$(printf '%s' "$req" | sed -n 's/.*"requestId":"\\([^"]*\\)".*/\\1/p')
  hash=$(printf '%s' "$req" | sed -n 's/.*"contractHash":"\\([^"]*\\)".*/\\1/p')
  printf '{"ok":true,"backend":"kani","version":"fake-1","proof":"argv-ok","requestId":"%s","contractHash":"%s"}\n' "$rid" "$hash"
  exit 0
elif [ "$1" = "fail" ]; then
  echo "verification failed" 1>&2
  exit 1
elif [ "$1" = "hang" ]; then
  sleep 5
  exit 0
fi
exit 2
`,
        { mode: 0o755 }
      );
    });

    afterAll(() => {
      rmSync(tmp, { recursive: true, force: true });
    });

    it('spawns argv via shell:false and produces a real proof on exit 0', async () => {
      const v = new KaniVerifier({ command: [fakePath, 'ok'] });
      const verdict = await v.verify(sample);
      expect(verdict.ok).toBe(true);
      expect(verdict.proof).toBe('kani@fake-1:argv-ok');
    });

    it('returns ok=false on nonzero exit with stderr captured', async () => {
      const v = new PrustiVerifier({ command: [fakePath, 'fail'] });
      const verdict = await v.verify(sample);
      expect(verdict.ok).toBe(false);
      expect(verdict.proof).toBeUndefined();
      expect(verdict.counterexample).toContain('verification failed');
    });

    it('returns ok=false on timeout and cleans up the child', async () => {
      const v = new CoqVerifier({ command: [fakePath, 'hang'], timeoutMs: 200 });
      const verdict = await v.verify(sample);
      expect(verdict.ok).toBe(false);
      expect(verdict.proof).toBeUndefined();
      expect(verdict.counterexample).toMatch(/timeout/i);
    }, 10_000);

    it('returns ok=false when the executable cannot be spawned', async () => {
      const v = new KaniVerifier({ command: [join(tmp, 'missing-prover')] });
      const verdict = await v.verify(sample);
      expect(verdict.ok).toBe(false);
      expect(verdict.counterexample).toMatch(/spawn failed|ENOENT/i);
    });

    it('argv injection from a malicious-looking contract is not shell-interpreted', async () => {
      // If shell:true had been used, this command argument would execute. With shell:false it remains literal.
      const injectionMarker = join(tmp, 'should-not-exist');
      const v = new KaniVerifier({ command: [fakePath, 'ok', `$(touch ${injectionMarker})`] });
      const verdict = await v.verify(sample);
      expect(verdict.ok).toBe(true);
      expect(existsSync(injectionMarker)).toBe(false);
    });
  });

  describe('invariants — never synthetic ok=true', () => {
    it('across all three backends, no command configured => ok=false, no proof', async () => {
      const ks = await new KaniVerifier().verify(sample);
      const ps = await new PrustiVerifier().verify(sample);
      const cs = await new CoqVerifier().verify(sample);
      for (const v of [ks, ps, cs]) {
        expect(v.ok).toBe(false);
        expect(v.proof).toBeUndefined();
        expect(v.counterexample).toBeDefined();
        expect(typeof v.durationMs).toBe('number');
        expect(v.durationMs).toBeGreaterThanOrEqual(0);
      }
    });
  });
});

describe('injected runner contract', () => {
  for (const Adapter of [KaniVerifier, PrustiVerifier, CoqVerifier]) {
    it(`${Adapter.name} contains runner rejection`, async () => {
      const adapter = new Adapter({
        runner: {
          run: async () => {
            throw new Error('runner failure');
          },
        },
      });
      await expect(adapter.verify(sample)).resolves.toMatchObject({
        ok: false,
        counterexample: expect.stringContaining('runner failure'),
      });
    });
    it(`${Adapter.name} invokes runner without dummy command`, async () => {
      const adapter = new Adapter({
        runner: makeFakeRunner((_argv, payload) => ({
          exitCode: 0,
          stdout: Buffer.from(
            correlatedEvidence(payload, { backend: new Adapter().backend, version: '1', ok: true, proof: 'proof' })
          ),
        })),
      });
      await expect(adapter.verify(sample)).resolves.toMatchObject({ ok: true });
    });
  }
});
