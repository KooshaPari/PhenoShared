# Audit: `.gitignore` vs ADR 0008 §D4

**Date:** 2026-08-07
**Auditor:** DAG-71 (`docs/plans/2026-08-05-pheno-harness-WBS-PERT-100.md` task 71)
**Scope:** `.gitignore` (root of `pheno-harness`) audited against ADR 0008 §D4
("kernel tree reorganisation; no source-tree patterns in `.gitignore`").
**Method:** line-by-line read + `git check-ignore -v` walk + `git ls-files` cross-check.
**Outcome:** 1 P0 toxic pattern (the `kernels/**/iso/` rule that swallows tracked
mirror headers), 0 P1 ambiguous, several P2 minors. DAG-72 will apply the fixes.

---

## Scope

| # | File / commit | Why included |
|---|---|---|
| 1 | `.gitignore` (root) | The file under audit. 61 lines, all read. |
| 2 | `docs/adrs/0008-repository-ecosystem-unification.md` §D4 | Canonical spec — kernel tree is split into 6 logical groups; only `dist/{build,iso}` is supposed to be gitignored; everything else is a tracked canonical home. |
| 3 | `tests/test_gitignore_no_source_tree_patterns.py` (DAG-73) | Load-bearing drift-guard already landed. Lists the 5 toxic patterns removed in `4bf638c` (`/AGENTS.md`, `/SPEC.md`, `/DESIGN.md`, `/README.md`, `/pyproject.toml`). |
| 4 | Commit `4bf638c` | Prior `fix(gitignore):` commit — removed 5 toxic source-tree patterns (`kernels/qwen3.5-0.8b/`, `kernels/**/kernels/qwen3.5-0.8b/`, `kernels/qwen3.5-0.8b/include/`, `**/scripts/cron/`, `kernels/qwen3-0-0.8b/`). The DAG-72 follow-up will remove the residual toxic pattern. |
| 5 | `bench/results/**`, `kernels/qwen3.5-0.8b/codegen/arch.json`, `kernels/qwen3.5-0.8b/iso/*.rs/h/mojo/nim/zig` | Tracked-vs-ignored cross-check; `iso/` mirror headers are tracked source files (added in `d06ff05`) but currently also matched by the audit's only P0 rule. |

---

## Findings

### Compliant patterns (no action)

These match ADR 0008 §D4 expectations or are explicitly documented build / local
tooling artefacts. Listed for completeness.

| Line | Pattern | Reason compliant |
|---|---|---|
| 2  | `bench/results/**/*.json` | `.json` outputs only; `.sha256` sidecars remain force-addable (verified via `git check-ignore`). CRON_OPS §6.4 protocol. |
| 5  | `.venv/`, `.venv*/`, `venv/` | Python virtualenvs (local tooling). |
| 6  | `.env` | Secrets / local config (risky_action_gate §13.4). |
| 7  | `.benchmarks/` | Local `pytest-benchmark` cache. |
| 8  | `.hypothesis/` | Hypothesis testing database. |
| 9  | `*.egg-info/` | Python packaging metadata. |
| 10 | `.pytest_cache/` | Pytest cache. |
| 11 | `.ruff_cache/` | Ruff linter cache. |
| 12 | `.mypy_cache/` | MyPy cache. |
| 13 | `dist/` | Python build output. |
| 14 | `*.egg` | Built distribution. |
| 17–20 | `.zig-cache/`, `zig-out/`, `zig-cache/`, `kernels/**/.zig-cache/`, `kernels/**/zig-out/` | Zig build artefacts. |
| 22 | `__pycache__/` | Python bytecode. |
| 23 | `*.pyc` | Python bytecode (top-level). |
| 24 | `*.air` | Apple MLX Intermediate Representation. |
| 25 | `.kernels/` | MLX kernels local cache (`git check-ignore` confirms match on `.kernels/foo`). |
| 26 | `*.a` | Rust static libs from `cargo test`. |
| 27 | `.dogfood-live-*/` | Operator-local dogfood scratch (DAG-76). |
| 28 | `nul` | Windows device sentinel. |
| 30 | `kernels/**/build/` | Kernel build output (`dist/` group per §D4). |
| 31 | `build/` | Top-level build output. |
| 33–34 | `eval/traces/*.jsonl`, `eval/traces/*.profile.csv` | PR-1 micro-eval recorder artefacts; canonical dir is kept. |
| 55 | `kernels/**/rust/target/` | `cargo build --release` cache for `build_dylib.sh` (rust-embed crate). |
| 61 | `kernels/**/0[0-5]_*/` | ADR 0008 §D4 symlink dirs (`00_src` … `05_scripts`). Rule is scoped; untracked by design. |

### P0 — Toxic patterns (source-tree risk)

| Line | Pattern | Why toxic |
|---|---|---|
| **52** | `kernels/**/iso/` | **The single residual P0.** The rule is correct in intent (ADR 0008 §D4 places `iso/` in the `dist/` group of generated artefacts), but the directory is currently home to 5 TRACKED mirror headers: `arch.rs`, `qwen3_5.h`, `qwen3_5.mojo`, `qwen3_5.nim`, `qwen3_5.zig` (added in commit `d06ff05`, still tracked today — verified via `git ls-files kernels/qwen3.5-0.8b/iso/`). Any new file dropped into `iso/` would be silently swallowed, and the existing tracked files sit under a rule that contradicts their presence. The accompanying comment ("only the iso/ golden snapshots are local build products") is **factually wrong**: the tracked files *are* the golden snapshots and they are tracked. `git check-ignore -v kernels/qwen3.5-0.8b/iso/foo.swallow` confirms the rule fires (`.gitignore:52:kernels/**/iso/`); only the previously-force-added files escape. |

### P1 — Ambiguous patterns

None. Every other rule either has a documented comment explaining its scope or
matches an unambiguous build / tooling path.

### P2 — Minor (formatting, redundancies)

| Line | Issue | Suggestion |
|---|---|---|
| 17 | `.zig-cache/` (top-level) duplicates 19 (`kernels/**/.zig-cache/`). | Keep both — kernel trees live outside `kernels/`, and the top-level form is required for the `scripts/cron/*` harness builders. No change. |
| 23 | `__pycache__/` covers bytecode directory; `*.pyc` overlaps. | Standard belt-and-braces; no change. |
| 31 | `build/` is redundant given `kernels/**/build/` for kernel trees. | Different scope (top-level vs kernel); no change. |
| 38–39 | Comment block is multi-line; line wrapping is fine but the 5th line ("only the iso/ golden snapshots are local build products") is the false claim driving P0. | Replace alongside the P0 fix. |
| 50 | Comment "build_dylib.sh invokes `cargo build --release` …" mixes prose and rule; readable but longer than necessary. | Optional: tighten. |

---

## Recommended fixes

> All fixes are DAG-72 work. This audit produces findings only.

### Fix-1 (P0) — Reconcile `kernels/**/iso/` with ADR 0008 §D4

Two acceptable resolutions (pick one in DAG-72):

**Option A (preferred):** Move the 5 tracked mirror headers out of `iso/` into
their canonical homes per ADR 0008 §D1 / D4 — `include/`, `rust/src/`, `zig/`,
`mojo/`, `nim/`. Then `kernels/**/iso/` becomes a pure build-output rule and
the misleading comment can stand.

**Option B (fallback):** Keep the 5 mirrors where they are and remove the
`kernels/**/iso/` rule from `.gitignore`. Update the comment to say "the
canonical iso/ mirrors are tracked; no further ignore needed".

In either case, also delete the false sentence "only the iso/ golden snapshots
are local build products" — it is the audit root cause.

### Fix-2 (P2, optional) — Tighten comment at line 38–39

After Fix-1 lands, replace the multi-line comment with a single-line pointer:
`# iso/ golden mirrors are tracked (see codegen/arch.json + ADR 0008 §D4)`.

### Fix-3 (P2, optional) — Pin `.zig-cache/` and `zig-out/` to kernel trees only

Drop the top-level forms (lines 17, 18, 20) if no scripts outside `kernels/`
produce them. Verify with `grep -r "zig-cache\|zig-out" scripts/ bench/`
before removing.

---

## Pre-DAG-72 state vs current

### What `4bf638c` already removed (5 patterns)

| Removed pattern | Risk it caused |
|---|---|
| `kernels/qwen3.5-0.8b/` | Shadowed the entire kernel source tree. |
| `kernels/**/kernels/qwen3.5-0.8b/` | Duplicate of the above (recursive). |
| `kernels/qwen3.5-0.8b/include/` | Shadowed kernel public headers. |
| `**/scripts/cron/` | Shadowed all 4 launchd cron wrappers. |
| `kernels/qwen3-0-0.8b/` | Typo (extra `0-`); would have shadowed a non-existent tree, but still a footgun. |

### What remains pending (this audit, DAG-71 → DAG-72)

| Pattern | Action |
|---|---|
| `kernels/**/iso/` | Reconcile via Fix-1 above (P0). |

### What the existing drift-guard (DAG-73) does NOT catch

`tests/test_gitignore_no_source_tree_patterns.py` only blocks the re-introduction
of the 5 patterns in `4bf638c` (root-level source files) and any top-level
`**/` pattern. It does **not** flag `kernels/**/iso/` because that pattern is
scoped (`kernels/**/…`) and the test allows scoped kernel ignores. A
follow-up DAG-72 or DAG-73+ test should assert that every `kernels/**/…`
gitignore line corresponds to a path that is *not* in `git ls-files`.

---

## References

- ADR 0008: `docs/adrs/0008-repository-ecosystem-unification.md` §D4 (kernel tree
  reorganisation; `dist/{build,iso}` gitignored, everything else tracked) — copy
  in worktree `worktrees/pheno-harness/agentora-replay-finish/docs/adrs/0008-repository-ecosystem-unification.md`.
- WBS/PERT DAG task 71: `docs/plans/2026-08-05-pheno-harness-WBS-PERT-100.md`
  Phase 5 (`.gitignore` hardening + drift tests).
- Drift-guard test: `tests/test_gitignore_no_source_tree_patterns.py` (DAG-73).
- Sibling audit (structure mirror): `docs/superpowers/audits/bench-harness-hardening.md`.
- Sibling audit (kernel-side mirror): `kernels/qwen3.5-0.8b/docs/superpowers/audits/metal-hardening.md`.
- Prior close-out commit: `4bf638c` — `fix(gitignore): remove 5 toxic source-tree patterns that dropped kernel + cron files`.
- Follow-up to land the fixes: DAG-72 (`remove 5 toxic source-tree patterns (per 4bf638c review)`) — will execute Fix-1.
- Tracked iso/ source files (added in `d06ff05`): `kernels/qwen3.5-0.8b/iso/{arch.rs, qwen3_5.h, qwen3_5.mojo, qwen3_5.nim, qwen3_5.zig}`.
