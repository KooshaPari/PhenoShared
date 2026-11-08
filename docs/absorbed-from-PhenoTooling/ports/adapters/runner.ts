import { spawn } from 'node:child_process';
import { createHash, randomUUID } from 'node:crypto';
import type { ChildProcessWithoutNullStreams } from 'node:child_process';
import type { Contract, Verdict } from '../contract_verifier';

// ---------------------------------------------------------------------------
// Shared types & spawn runner (import directly from this module).
// ---------------------------------------------------------------------------

/** Default per-invocation timeout: 30 seconds. */
const DEFAULT_TIMEOUT_MS = 30_000;
/** Hard upper bound on timeout to prevent unbounded waits: 5 minutes. */
const HARD_TIMEOUT_CAP_MS = 5 * 60_000;
/** Default max bytes captured from stdout/stderr combined: 1 MiB. */
const DEFAULT_MAX_OUTPUT_BYTES = 1 << 20;
/** Hard upper bound on output capture: 16 MiB. */
const HARD_OUTPUT_CAP_BYTES = 16 << 20;

/** Options accepted by every adapter constructor. */
export interface AdapterOptions {
  /**
   * Shell argv to invoke. Must be a non-empty array. Each element is passed
   * verbatim to `spawn`; nothing is concatenated into a shell string.
   * If omitted without an injected runner, the adapter will fail closed.
   */
  readonly command?: readonly string[];
  /** Optional working directory for the child process. */
  readonly cwd?: string;
  /** Optional env passthrough (merged on top of `process.env`). */
  readonly env?: NodeJS.ProcessEnv;
  /**
   * Per-invocation timeout in milliseconds. Hard-capped at 5 minutes to
   * prevent unbounded waits. Default: 30s.
   */
  readonly timeoutMs?: number;
  /**
   * Maximum combined bytes captured from stdout + stderr before the child
   * is killed with SIGKILL. Hard-capped at 16 MiB. Default: 1 MiB.
   */
  readonly maxOutputBytes?: number;
  /** Inject a custom runner for tests. When set, `command` is ignored. */
  readonly runner?: SpawnRunner;
}

export interface SpawnResult {
  /** Child exit code; `null` when killed by signal or never spawned. */
  readonly exitCode: number | null;
  /** Signal name that terminated the child; `null` on normal exit. */
  readonly signal: NodeJS.Signals | null;
  /** Captured stdout (bounded by `maxOutputBytes`). */
  readonly stdout: Buffer;
  /** Captured stderr (bounded by `maxOutputBytes`). */
  readonly stderr: Buffer;
  /** True when the timeout fired and the child was killed. */
  readonly timedOut: boolean;
  /** Wall-clock duration of the spawn in milliseconds. */
  readonly durationMs: number;
  /** True when spawn failed (e.g., ENOENT). */
  readonly spawnError?: boolean;
  /** Spawn error message if any. */
  readonly spawnErrorMessage?: string;
  /** True when the captured output exceeded the cap and was truncated. */
  readonly outputTruncated?: boolean;
}

/**
 * Abstraction over the spawn call so unit tests can substitute a
 * deterministic in-memory runner without touching the filesystem.
 */
export interface SpawnRunner {
  run(argv: readonly string[], opts: SpawnRunnerOptions): Promise<SpawnResult>;
}

export interface SpawnRunnerOptions {
  readonly stdin: string;
  readonly timeoutMs: number;
  readonly maxOutputBytes: number;
  readonly cwd?: string;
  readonly env?: NodeJS.ProcessEnv;
}

/** Clamp a numeric option into (0, hardCap], falling back to a default. */
function clamp(value: number | undefined, fallback: number, hardCap: number): number {
  if (value === undefined || !Number.isFinite(value) || value <= 0) return fallback;
  return Math.min(value, hardCap);
}

/**
 * Default {@link SpawnRunner}: spawns a real child process with `shell:false`,
 * enforces a hard timeout via SIGKILL, and caps captured output to prevent
 * memory abuse. The contract payload is delivered on stdin (never argv) so
 * that malicious-looking contract data cannot be shell-interpreted.
 */
export const defaultSpawnRunner: SpawnRunner = {
  async run(argv, opts) {
    if (argv.length === 0) {
      return {
        exitCode: null,
        signal: null,
        stdout: Buffer.alloc(0),
        stderr: Buffer.alloc(0),
        timedOut: false,
        durationMs: 0,
        spawnError: true,
        spawnErrorMessage: 'empty argv',
        outputTruncated: false,
      };
    }
    const timeoutMs = clamp(opts.timeoutMs, DEFAULT_TIMEOUT_MS, HARD_TIMEOUT_CAP_MS);
    const maxBytes = clamp(opts.maxOutputBytes, DEFAULT_MAX_OUTPUT_BYTES, HARD_OUTPUT_CAP_BYTES);

    const start = Date.now();
    return await new Promise<SpawnResult>((resolve) => {
      let child: ChildProcessWithoutNullStreams;
      try {
        const executable = argv[0];
        if (executable === undefined) throw new Error('empty argv');
        child = spawn(executable, argv.slice(1), {
          shell: false, // explicit: argv is NOT shell-parsed
          stdio: ['pipe', 'pipe', 'pipe'],
          cwd: opts.cwd,
          env: opts.env ? { ...process.env, ...opts.env } : process.env,
          windowsHide: true,
          detached: process.platform !== 'win32',
        });
      } catch (err) {
        resolve({
          exitCode: null,
          signal: null,
          stdout: Buffer.alloc(0),
          stderr: Buffer.alloc(0),
          timedOut: false,
          durationMs: Date.now() - start,
          spawnError: true,
          spawnErrorMessage: err instanceof Error ? err.message : String(err),
          outputTruncated: false,
        });
        return;
      }

      let settled = false;
      let timedOut = false;
      let outputTruncated = false;
      const killChild = () => {
        try {
          if (process.platform !== 'win32' && child.pid !== undefined) {
            process.kill(-child.pid, 'SIGKILL');
          } else {
            child.kill('SIGKILL');
          }
        } catch {
          /* already exited */
        }
      };
      const timer = setTimeout(() => {
        timedOut = true;
        killChild();
      }, timeoutMs);

      const stdoutChunks: Buffer[] = [];
      const stderrChunks: Buffer[] = [];
      let stdoutLen = 0;
      let stderrLen = 0;

      const killForOverflow = () => {
        outputTruncated = true;
        killChild();
      };

      const onChunk = (kind: 'stdout' | 'stderr') => (chunk: Buffer) => {
        const buf = kind === 'stdout' ? stdoutChunks : stderrChunks;
        const remaining = maxBytes - stdoutLen - stderrLen;
        if (remaining <= 0) {
          killForOverflow();
          return;
        }
        const slice = chunk.length > remaining ? chunk.subarray(0, remaining) : chunk;
        buf.push(slice);
        if (kind === 'stdout') {
          stdoutLen += slice.length;
        } else {
          stderrLen += slice.length;
        }
        if (chunk.length > remaining) {
          killForOverflow();
        }
      };

      child.stdout?.on('data', onChunk('stdout'));
      child.stderr?.on('data', onChunk('stderr'));
      const onStreamError = (error: Error) => {
        child.emit('error', error);
        killChild();
      };
      child.stdout?.on('error', onStreamError);
      child.stderr?.on('error', onStreamError);

      // Deliver contract payload via stdin, then close so the child can drain.
      // A backend may exit before consuming stdin; retain a listener so its
      // asynchronous EPIPE is not emitted as an uncaught stream error.
      child.stdin?.once('error', () => {});
      try {
        child.stdin?.write(opts.stdin);
        child.stdin?.end();
      } catch {
        /* stdin may already be closed if the child exited early */
      }

      child.on('error', (err) => {
        if (settled) return;
        settled = true;
        clearTimeout(timer);
        resolve({
          exitCode: null,
          signal: null,
          stdout: Buffer.concat(stdoutChunks),
          stderr: Buffer.concat(stderrChunks),
          timedOut: false,
          durationMs: Date.now() - start,
          spawnError: true,
          spawnErrorMessage: err.message,
          outputTruncated,
        });
      });

      child.on('close', (code, signal) => {
        if (settled) return;
        settled = true;
        clearTimeout(timer);
        resolve({
          exitCode: code,
          signal,
          stdout: Buffer.concat(stdoutChunks),
          stderr: Buffer.concat(stderrChunks),
          timedOut,
          durationMs: Date.now() - start,
          spawnError: false,
          outputTruncated,
        });
      });
    });
  },
};

/**
 * Format a {@link SpawnResult} into a short, human-readable failure string
 * suitable for inclusion in a {@link Verdict.counterexample}.
 */
export function formatSpawnFailure(res: SpawnResult): string {
  if (res.spawnError) {
    return `backend spawn failed: ${res.spawnErrorMessage ?? 'unknown error'}`;
  }
  if (res.timedOut) {
    return 'backend timeout';
  }
  if (res.outputTruncated) {
    return 'backend output exceeded the configured capture cap';
  }
  if (res.signal) {
    return `backend terminated by signal ${res.signal}`;
  }
  if (res.exitCode !== 0) {
    const stderr = res.stderr.toString('utf8').trim();
    const stdout = res.stdout.toString('utf8').trim();
    const tail = stderr || stdout || '(no output)';
    return `backend exited with code ${res.exitCode}: ${tail.slice(0, 512)}`;
  }
  return 'backend returned no evidence';
}

// ---------------------------------------------------------------------------
// Shared adapter core. Verdict construction is identical across backends;
// only the argv differs.
// ---------------------------------------------------------------------------

const UNCONFIGURED = 'backend not configured: no command provided';

interface BackendEvidence {
  readonly ok: boolean;
  readonly backend: string;
  readonly version: string;
  readonly proof?: string;
  readonly counterexample?: string;
  readonly requestId: string;
  readonly contractHash: string;
}

function contractHash(contract: Contract): string {
  return createHash('sha256').update(JSON.stringify(contract)).digest('hex');
}

function parseEvidence(stdout: Buffer, backend: string): BackendEvidence | undefined {
  try {
    const value: unknown = JSON.parse(stdout.toString('utf8'));
    if (!value || typeof value !== 'object') return undefined;
    const evidence = value as Partial<BackendEvidence>;
    if (
      typeof evidence.ok !== 'boolean' ||
      evidence.backend !== backend ||
      typeof evidence.version !== 'string' ||
      evidence.version.trim().length === 0
    )
      return undefined;
    if (evidence.ok && (typeof evidence.proof !== 'string' || evidence.proof.trim().length === 0)) return undefined;
    if (!evidence.ok && (typeof evidence.counterexample !== 'string' || evidence.counterexample.trim().length === 0))
      return undefined;
    return evidence as BackendEvidence;
  } catch {
    return undefined;
  }
}

export async function runAdapter(
  backend: string,
  contract: Contract,
  options: AdapterOptions
): Promise<{ result: SpawnResult; ok: boolean; reason: string; proof?: string; durationMs: number }> {
  // Fail-closed: unconfigured adapter has no command to invoke.
  if (!options.runner && (!options.command || options.command.length === 0)) {
    return {
      result: {
        exitCode: null,
        signal: null,
        stdout: Buffer.alloc(0),
        stderr: Buffer.alloc(0),
        timedOut: false,
        durationMs: 0,
        spawnError: true,
        spawnErrorMessage: UNCONFIGURED,
        outputTruncated: false,
      },
      ok: false,
      reason: UNCONFIGURED,
      durationMs: 0,
    };
  }

  const runner = options.runner ?? defaultSpawnRunner;
  const requestId = randomUUID();
  const expectedHash = contractHash(contract);
  const payload = JSON.stringify({ protocolVersion: 1, requestId, contractHash: expectedHash, backend, contract });
  let result: SpawnResult;
  try {
    result = await runner.run(options.command ?? [], {
      stdin: payload,
      timeoutMs: options.timeoutMs ?? DEFAULT_TIMEOUT_MS,
      maxOutputBytes: options.maxOutputBytes ?? DEFAULT_MAX_OUTPUT_BYTES,
      cwd: options.cwd,
      env: options.env,
    });
  } catch (error) {
    return {
      result: {
        exitCode: null,
        signal: null,
        stdout: Buffer.alloc(0),
        stderr: Buffer.alloc(0),
        timedOut: false,
        durationMs: 0,
        spawnError: true,
      },
      ok: false,
      reason: `tool_error: runner rejected: ${String(error)}`,
      durationMs: 0,
    };
  }

  // Hard-fail on any abnormal exit path BEFORE considering ok=true.
  if (result.spawnError || result.timedOut || result.signal || result.outputTruncated) {
    return { result, ok: false, reason: formatSpawnFailure(result), durationMs: result.durationMs };
  }
  if (result.exitCode !== 0) {
    return {
      result,
      ok: false,
      reason: `tool_error: ${formatSpawnFailure(result)}`,
      durationMs: result.durationMs,
    };
  }

  const evidence = parseEvidence(result.stdout, backend);
  if (!evidence)
    return { result, ok: false, reason: 'tool_error: malformed backend output', durationMs: result.durationMs };
  if (evidence.requestId !== requestId || evidence.contractHash !== expectedHash) {
    return {
      result,
      ok: false,
      reason: 'tool_error: backend response correlation mismatch',
      durationMs: result.durationMs,
    };
  }
  if (!evidence.ok) {
    return {
      result,
      ok: false,
      reason: `verification_false: ${backend}@${evidence.version}: ${evidence.counterexample}`,
      durationMs: result.durationMs,
    };
  }

  return {
    result,
    ok: true,
    reason: '',
    proof: `${backend}@${evidence.version}:${evidence.proof}`,
    durationMs: result.durationMs,
  };
}

export function toVerdict(outcome: { ok: boolean; reason: string; proof?: string; durationMs: number }): Verdict {
  if (outcome.ok) {
    return { ok: true, proof: outcome.proof ?? '', durationMs: outcome.durationMs };
  }
  return { ok: false, counterexample: outcome.reason, durationMs: outcome.durationMs };
}
