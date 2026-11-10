## Four-dimension roll-up

Evidence cells only; every non-`?` cell cites a source. No percentage is derived from partial evidence.
```
PhenoShared QA posture
├── Implementation ................ PASS   `.github/workflows/` = 92 entries (89 `.yml` + 3 non-YAML files)
│   ├── test + scanner lanes ...... PASS   ci.yml, quality-gate.yml, e2e.yml; gitleaks, trufflehog, secret-guard, cargo-audit, Trivy, CodeQL, SBOM — workflow inventory
│   ├── PII sweep wired ........... FAIL   0 of 89 workflows reference scripts/pii-sweep-repair.py
│   └── cosign / typos wired ...... FAIL   4 signing scripts, 0 workflows call them; typos only in compute-infra-auditors.yml
├── Usability ..................... UNKNOWN  no developer-journey / time-to-green measurement run
│   ├── one-command gate .......... PASS   `make check` = fmt + clippy + test-unit (`Makefile:9`)
│   └── duplicate workflow pairs .. FAIL   audit/security, deny/cargo-deny, scorecard/-ci, fuzz/fuzzing in `.github/workflows/`
├── Validation .................... PASS-with-gaps
│   ├── coverage floor enforced ... PASS   `.coverage-baselines/root-workspace.toml`: aggregate 36.00 + 10 per-group floors, tarpaulin
│   ├── floor is a low bar ........ FAIL   aggregate floor 36.00 vs measured 54.79 and ~19.2k test attributes in `crates/` (16,266 `#[test]` + 2,955 `#[tokio::test]`, measured 10:53Z; drifts with the concurrent checkout)
│   └── required checks / trunk ... UNKNOWN branch protection never queried; trunk exit codes untraced
└── Assurance ..................... UNKNOWN  enforcement is real in-workflow; merge-blocking does not
    ├── repo-grounded evidence ..... PASS   every cell cites a repo path; 0 mutating git commands run
    ├── deny.toml as hard gate ..... FAIL   only `deny.yml` is non-continue-on-error; the PR path is advisory
    └── deny.yml tool pinned ....... FAIL   unpinned `cargo install cargo-deny` + `@stable`, not the repo's 1.99.x
```

## Claimed but unproven

| Claim | Where claimed | Why unproven |
|---|---|---|
| Checks are *required* on `main` | workflow trigger blocks in `.github/workflows/` | Workflows running is not proof that branch protection blocks a merge; branch protection was never queried |
| Codecov 71%/80% are live gates | `.github/codecov.yml` | No workflow uploads a report; config-only |
| `[workspace] members` = 287 | `Cargo.toml` | 287 quoted strings resolve to 283 unique paths (1 comment line, 3 duplicates); the raw 287 is not the member count |
| "0 manifests lack a `license` key" | `Cargo.toml` files | Not zero, but far from the raw-grep figure: of 688 tracked `Cargo.toml`, **317 declare `license` explicitly, 323 inherit via `license.workspace = true`, and 50 declare none at all**. A literal `^license =` grep misreports the 323 inheriting manifests as unlicensed |
| `crates/` README ×844 / CLAUDE ×111 / AGENTS ×136 | `git ls-files` | Measured 313 / 45 / 50 — up to 2.7× overstated |
| Local branches 45 / worktrees 19 | `git branch`; `git worktree list` | Measured 28 local branches / 28 worktree entries (1 main + 27 linked) |

## How to run the full gate locally

1. `cd ~/CodeProjects/Phenotype/repos/PhenoShared`
2. `make check`  # fmt + clippy + test-unit, the canonical gate
3. `cargo nextest run --workspace`  # mirrors ci.yml
4. `cargo install cargo-tarpaulin --locked && cargo tarpaulin --engine llvm --out Json -p <crate-group>`
5. `python3 .github/scripts/coverage_report.py`  # enforces .coverage-baselines/root-workspace.toml floors
6. `cargo deny check && cargo audit`  # deny.toml sections; .cargo/audit.toml has a separate ignore list
7. `trunk check`  # multi-linter; `--fix` to autofix
8. `typos --config .typos.toml`  # NOT in the default CI path
9. `actionlint && gitleaks detect --config .gitleaks.toml`
10. `./governance/happy-path-precommit.sh`  # needs HAPPY_PATH_BASE / HAPPY_PATH_HEAD
11. `python3 scripts/pii-sweep-repair.py`  # NOT in CI, run manually
12. `pre-commit install --hook-type commit-msg && pre-commit run --all-files && npm run docs:build`

## CI lane inventory

| Workflow file | Purpose | Trigger | Disabled? |
|---|---|---|---|
| `ci.yml` | nextest, ruff, gitleaks, cargo-deny (advisory) | push / PR / merge_group | No |
| `quality-gate.yml` | `make check` -> fmt + clippy + test-unit | PR + push to `main` | No |
| `coverage.yml` | Tier-2 coverage floor, tarpaulin matrix | push(main) + PR(main) | No |
| `e2e.yml` | e2e_smoke + daemon health-probe smoke | dedicated | No |
| `deny.yml` | `cargo deny check` at root, the real gate | push(main) on lockfile/manifest + weekly Mon 09:00 | No |
| `cargo-deny.yml` | cargo-deny-action on `iac/Cargo.toml` only | manifest change | No (wrong scope) |
| `security.yml`, `trunk-check.yml` | CodeQL/audit/SBOM; trunk linter | push / PR / weekly Mon 03:00 UTC | No |
| `release-macos.yml`, `pages.yml` | macOS release, Pages publish | n/a | YES, in `workflows-disabled/` |
