# PhenoShared — QA Matrix

**Measured:** 2026-11-19 at `f06c3cc7f`. Read-only configuration recon. **No test suite was executed
to produce this document**, so nothing here is a PASS claim about test results. It reports what is
configured, what is enforced, and what cannot be determined without running CI.

---

## 1. CI surface

81 workflows are configured in `.github/workflows/` (verified: `ls .github/workflows/*.yml | wc -l`).

An aggregate workflow fans out to per-language jobs:

```
detect → { rust, python, go, typescript, security }
```

Notable specialised workflows, by what they actually enforce:

| Workflow | Enforces |
|---|---|
| `ci.yml` | aggregate detect/fan-out above |
| `codeql.yml` | static analysis, code scanning |
| `cargo-deny.yml` | licence and advisory policy |
| `cargo-machete.yml` | unused Rust dependencies |
| `cargo-semver-checks.yml` | public API breakage |
| `ansible-lint.yml` | playbook lint |
| `absorption-verify.yml` | absorbed-tree integrity |
| `a11y-phenodocs.yml` | documentation accessibility |
| `benchmark.yml` | performance runs |
| `ai-testing-orchestration.yml` | agent-driven test orchestration |

**UNKNOWN: required status contexts.** Branch protection is server-side and was not fetched. Which
of these 81 workflows actually block a merge is not determinable from the tree.

---

## 2. Test frameworks present

| Language | Framework | Evidence |
|---|---|---|
| Rust | `cargo test`, `#[test]`, `insta`/`proptest` style snapshots | workspace tests, `tests/` dirs |
| Python | `pytest` | `pyproject.toml` config, `fail_under` declarations |
| TypeScript/JS | `node:test` and `vitest` | test files, package scripts |
| Go | `go test` | 47 module roots |

---

## 3. Test census

6,055 tracked paths match a test-shaped pattern, out of 55,898 tracked files: **10.8% of the tree**.

| Top-level dir | Test-shaped paths |
|---|---|
| `apps/` | 1,520 |
| `crates/` | 1,246 |
| `docs/` | 1,128 |
| `absorption/` | 653 |
| `tests/` | 310 |
| `agents/` | 284 |
| `agileplus/` | 132 |
| `libs/` | 95 |

Two readings matter here. First, the 10.8% headline is inflated by absorbed and vendored trees, so
it says nothing about first-party coverage. Second, **`docs/` carries 1,128 test-shaped paths**,
which are example and fixture files rather than suites. A reader should not treat that column as
test strength.

---

## 4. Coverage floors

17 coverage-floor declarations exist across tracked configuration. Distribution by floor:

| Floor | Count | Reading |
|---|---|---|
| 0 | 4 | **no gate at all**; the declaration is decorative |
| 10 | 3 | near-zero gate |
| 37 | 3 | aggregate/root floor |
| 60 | 1 | real gate |
| 71 | 2 | real gate |
| 80 | 4 | real gate |

The finding is the first row. Four configurations declare `fail-under 0`, which means a coverage
step can never fail them. Two-thirds of the floor declarations sit at or below 37.

---

## 5. Gates configured but not necessarily enforced

| Gate | Configured | Enforced in CI |
|---|---|---|
| clippy / rustfmt | yes | yes (`ci.yml` rust job) |
| cargo-deny | yes | yes |
| cargo-semver-checks | yes | yes |
| codeql | yes | yes |
| ruff / mypy | yes | partially — python job present, depth unverified |
| eslint / tsc | yes | `UNKNOWN` — typescript job present, enforcement depth unverified |
| Sonar | referenced | `UNKNOWN` — not confirmed as a required context |

`UNKNOWN` above means the workflow exists and its internal strictness was not established. It does
not mean the gate is absent.

---

## 6. Gaps, ranked

1. **Four zero coverage floors.** A floor of 0 is not a floor. This is the cheapest fix in the
   matrix: either raise it or delete the pretence.
2. **81 workflows with unknown required status.** Nobody can say from the repository which checks
   gate a merge. Branch protection must be dumped and recorded.
3. **Coverage is not attributable.** With 2.86 M absorbed or vendored code lines in the tree, an
   aggregate percentage measures the corpus, not the product. Floors must be scoped per first-party
   workspace.
4. **Nested sub-workspaces may not be tested by the root build.** 26 cargo sub-workspaces fall
   outside `cargo build --workspace`; whether their tests run in CI is `UNKNOWN` and must be
   checked, because untested code that also never builds at root is invisible twice over.
5. **No `go.work`.** 47 Go module roots with no workspace file means no single test command covers
   Go, so CI coverage of Go depends entirely on how the fan-out job was written.
6. **Absorbed trees are linted and tested as if they were ours.** `absorption/` contributes 653
   test-shaped paths and 6,583 files to every run. Verify-before-absorb, then exclude from
   first-party gates.

---

## 7. What would make this matrix real

| Step | Command that would settle it |
|---|---|
| Required contexts | `gh api repos/KooshaPari/PhenoShared/branches/main/protection` |
| Actual suite results | one CI run's job list, captured with pass/fail per job |
| First-party coverage | `cargo llvm-cov --workspace --exclude` absorbed members, plus `pytest --cov` per project |
| Zero-floor owners | `git grep -n 'fail.under *= *0'` and attribute each to its project |

Until at least the first two are done, this document describes intent, not assurance.
