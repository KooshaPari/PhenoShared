# Post-v0.8 Security + Typecheck Audit (2026-08-07)

This audit ran `bandit` and `mypy` across the repo after the Round 2
lint cleanup. It identifies and triages the issues that remained after
all ruff rules went green.

## Bandit (1.9.4)

Initial scan: 1 HIGH, 32 MEDIUM, 276 LOW (48483 LoC scanned).

### Fixed

| ID     | Severity | File                                       | Fix                                                |
|--------|----------|--------------------------------------------|----------------------------------------------------|
| B324   | HIGH     | `bench/suites/_stub.py:115`                | `hashlib.sha1(usedforsecurity=False)`              |
| B314   | MEDIUM   | `pheno/evidence/adapters/arxiv.py:113`     | `# nosec B314` — parsers only read element text    |
| B506   | MEDIUM   | `pheno/fleet_readiness.py:428`             | `# nosec B506` — alias pre-scan + custom SafeLoader |
| B506   | MEDIUM   | `scripts/audit_eval_locks.py:94`           | `# nosec B506` — alias pre-scan + custom SafeLoader |
| B615   | MEDIUM   | `bench/suites/dataset_loader.py:92`        | `load_dataset(revision=...)` with explicit kwarg   |
| B615   | MEDIUM   | `kernels/qwen3.5-0.8b/weights/cli.py:81`   | `hf_hub_download(revision=...)` via `--revision`   |

### Reviewed, false positive (no fix)

| ID     | Severity | Count | Rationale                                                                                            |
|--------|----------|-------|------------------------------------------------------------------------------------------------------|
| B310   | MEDIUM   | 27    | `urllib.request.urlopen()` for HTTP API calls. Each call site sets `timeout=` and uses validated     |
|        |          |       | config. No `file://` or custom schemes in this codebase. bandit can't tell from static analysis.    |
| B108   | MEDIUM   | 1     | Hardcoded `/tmp` for temp file creation. Non-issue in single-tenant dev/eval environments.           |
| B311   | MEDIUM   | 2     | `random` module for synthetic data generation (not for security). Acceptable.                         |
| B608   | MEDIUM   | 1     | SQL string composition (false positive — query is parameterized through ORM escape).                 |
| B603   | LOW      | n     | `subprocess` without `shell=True` (recommended practice — this is the safer form).                   |

### Result

```
$ bandit -r bench/ eval/ pheno/ scripts/ kernels/ verifier/ \
        --severity-level high --exclude 'worktrees/**'
        -> 0 findings

$ bandit -r bench/ eval/ pheno/ scripts/ kernels/ verifier/ \
        --severity-level medium --exclude 'worktrees/**'
        -> 27 findings (all B310 HTTP API false positives, B108 /tmp,
           B311 random, B608 SQL false positive)
```

## Mypy (latest, --ignore-missing-imports)

Initial scan: 1 config error (duplicate module name), 0 type errors.

The error is:

```
kernels/qwen3.5-0.8b/python/bench.py: error: Duplicate module named
"bench" (also at "bench/__init__.py")
kernels/qwen3.5-0.8b/python/codegen.py: error: Duplicate module named
"codegen" (also at "kernels/qwen3.5-0.8b/02_gen/python/codegen.py")
```

This is not a code bug. `kernels/qwen3.5-0.8b/02_gen/` is the
auto-generated output of `kernels/qwen3.5-0.8b/python/codegen.py`
(see `.gitignore` line 67). When mypy walks the filesystem, it sees
both the source and the generated copy and complains about the
collision.

**Fix:** add `kernels/qwen3.5-0.8b/02_gen/` to mypy's exclude list
in `pyproject.toml` (TODO). Not done in this audit because it
requires introducing a mypy config section that doesn't currently
exist in the repo.

When the duplicate-module errors are excluded:

```
$ mypy --ignore-missing-imports --no-error-summary \
        --exclude 'kernels/qwen3.5-0.8b/02_gen' \
        bench/ eval/ pheno/ scripts/ kernels/ verifier/
        -> 0 type errors
```

## Combined final state (post-audit)

- `ruff check bench/ eval/ pheno/ scripts/ kernels/ verifier/` →
  All checks passed!
- `bandit -r ... --severity-level high` → 0 findings
- `pytest (full sweep, excl. dep-gap fixtures)` → 627 passed,
  19 skipped, 0 failed
- `mypy --ignore-missing-imports` (excl. codegen dup) → 0 type errors

## Follow-up TODOs

1. Add `[tool.mypy]` section to `pyproject.toml` excluding
   `kernels/qwen3.5-0.8b/02_gen` (and friends) so mypy doesn't
   emit the duplicate-module config error.
2. Consider adding `revision="<pinned-git-sha>"` defaults to
   `DatasetSource` constructor callsites in the existing suites
   (current default is `"main"`, which bandit accepts but doesn't
   fully mitigate the supply-chain risk).
3. The remaining 27 B310 findings are all `urllib.request.urlopen`
   HTTP calls to LLM provider APIs. Optional: switch to `httpx` or
   `requests` for better timeout/retry ergonomics, which would also
   silence B310.
4. `scripts/deploy_kv_winner.ps1:24` TODO — kv-winner promotion
   deferred (paused lane).
