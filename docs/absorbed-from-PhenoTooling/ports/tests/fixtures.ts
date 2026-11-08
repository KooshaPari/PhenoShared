import type { SpawnResult } from '../adapters/runner';

/** In-memory runner that always returns exit 0 with a tagged proof. */
export function okRunner(
  backend: string,
  version = 'test-1'
): {
  run: (
    argv: readonly string[],
    opts: { stdin: string; timeoutMs: number; maxOutputBytes: number }
  ) => Promise<SpawnResult>;
} {
  return {
    async run(_argv, opts) {
      const request = JSON.parse(opts.stdin) as { requestId: string; contractHash: string };
      return {
        exitCode: 0,
        signal: null,
        stdout: Buffer.from(
          JSON.stringify({
            ok: true,
            backend,
            version,
            proof: 'proof',
            requestId: request.requestId,
            contractHash: request.contractHash,
          })
        ),
        stderr: Buffer.alloc(0),
        timedOut: false,
        durationMs: 1,
      };
    },
  };
}
