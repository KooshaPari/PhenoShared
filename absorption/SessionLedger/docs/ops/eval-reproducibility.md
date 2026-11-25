# Eval reproducibility manifest

SessionLedger records eval surface boundaries and reproducibility anchors in
[`eval-manifest.json`](eval-manifest.json). The manifest is not a scorecard; it
binds conformance fixtures, the committed lockfile, MSRV, and the pipeline
performance baseline policy so local and CI eval runs can be compared.

## Verify

From the repository root:

```powershell
./scripts/eval-repro-check.ps1
# or explicit CI smoke (also validates doc/CI wiring):
./scripts/eval-repro-check.ps1 -SelfCheck
```

Rust integration wrapper (runs the same `-SelfCheck` path):

```powershell
$env:CARGO_TARGET_DIR = 'target-w40-eval-repro'
cargo test --test eval_repro
```

The script asserts:

1. `Cargo.lock` SHA-256 matches the manifest (update the manifest when the
   lockfile changes intentionally).
2. Host `rustc` meets `rust_msrv`.
3. OKF conformance fixture count matches `fixture_count`.
4. When present, every entry in `fixture_anchors` exists on disk and matches
   the glob (no extras, no omissions).
5. Bench policy (`perf-baseline.json`) and gate script exist.

It prints the current Git commit SHA for human correlation; the commit is
intentionally **not** pinned in the manifest because eval runs move with every
merge.

## When to update the manifest

| Change                                | Action                                                                                                  |
| ------------------------------------- | ------------------------------------------------------------------------------------------------------- |
| `Cargo.lock` updated                  | Recompute SHA-256 and bump `cargo_lock_sha256`                                                          |
| Fixture added/removed                 | Bump `fixture_count`, update `fixture_anchors`, and bump `fixture_seed` only if corpus identity changes |
| MSRV raised in workspace `Cargo.toml` | Bump `rust_msrv`                                                                                        |
| Bench policy path changes             | Update `bench_policy_path` / `bench_gate_script`                                                        |

## CI

`.github/workflows/ci.yml` runs `eval-repro-check.ps1` on every pull request
alongside the existing bench gate workflow. `tests/eval_repro.rs` mirrors the
`-SelfCheck` path for local `cargo test` proof.

## Related

- [`EVAL_SCOPE.md`](../EVAL_SCOPE.md) — product eval boundaries
- [`perf-regression.md`](perf-regression.md) — Criterion gate policy
- [`perf-baseline.json`](perf-baseline.json) — checked-in pipeline means
