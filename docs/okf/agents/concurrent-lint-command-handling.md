---
source_file: ChatGPT-Concurrent Lint Command Handling.md
sha256: 942785ed90e584cb5e229047dcb3ced6c9cc58508af7ca33e1300898e90b350c
topics: [agents, concurrent-lint, harness, flock, debounce, tool-calls]
related_okf:
  - agents/coding-agents-intent-graphs.md
  - agents/feature-graph-system-design.md
evidence_class: L
status: stub — N10 priority, needs full distillation
---

# Concurrent Lint Command Handling

**Source:** `ChatGPT-Concurrent Lint Command Handling.md` (16 KB, 2026-07-04) — class **L**.

OS-level coordination for isolated agent processes (Claude Code, Cursor CLI, Auggie) that each invoke the same lint/binary concurrently without cross-communication. The corpus proposes a shared Bash harness at the OS layer to deduplicate, debounce, and queue executions rather than spawning N interpreters.

## Key insights (stub — full distillation pending N10)

- **Lock-wait-cache wrapper:** `flock` on a per-request lock + shared `stdout/stderr/exitcode` cache so burst callers collapse to one real execution; latecomers read the cached result under lock.
- **Debounce + TTL:** `DEBOUNCE_MS ~150–200ms` groups near-simultaneous arrivals; `TTL_MS ~800–1200ms` reuses fresh results, keyed by `tool + args + cwd + git HEAD` (and optionally `git diff` for state-aware invalidation).
- **Generic PATH shim:** single `agentwrap` binary symlinked to `ruff`, `eslint`, `prettier`, `golangci-lint`, etc., placed first in `PATH` (`~/.agent_shims/bin`); resolves real binary by skipping shim dir, applies per-tool rules from `~/.agent_shims/rules/<tool>.conf` (`MODE=dedupe|passthrough`).
- **Process-filtered gating:** match `PPID`/`comm` or full ancestor chain / cgroup to apply dedupe only for agent parents (`claude|cursor|auggie|codex`); normal user shells passthrough via `exec`.
- **What is not practical:** transparent system-wide `exec` interception that returns shared output without a choke point — observable via eBPF/auditd/ptrace and blockable via seccomp/LSM, but output injection requires a debugger/pty broker; PATH shim is the sane lever.

## Next (N10)

- Extract full `[L]`-tagged claims with `local://sha256/942785ed90e584...` citations.
- Add cross-links to `docs/okf/agents/*` and `config/risky_action_gate.yaml` (harness policy).
- Verify against primary sources (flock, GNU parallel, bash-concurrent) before promoting to **P**.

**Evidence:** `local://sha256/942785ed90e584cb5e229047dcb3ced6c9cc58508af7ca33e1300898e90b350c` (class **L**).
