# AI-DD Governance & Strict Quality Gate

**Generated:** 2026-06-08
**Status:** Draft — pending review and agent-validation

---

## AI-DD Mandate

Every line of code is read, written, specified, validated, and verified by an agent or agent-configured program.
All code is brittle, unstable, and drift-prone — or already drifted. Heavy evaluation required.

---

## 1. Quality Gate (per commit, per PR)

### lefthook pre-commit (local, pre-push)

```
$STAGED_FILES is checked by:
  - ruff / ruff-format         (Python — fast, strict)
  - rustfmt + cargo-check      (Rust — workspace-wide)
  - actionlint                 (workflow YAML)
  - trufflehog                (secret scanning, pre-commit)
  - <linter-per-language>
  - <formatter-per-language>
  - <type-checker-per-language>
```

If any hook fails, commit is blocked. No bypass. No `--no-verify`.

### Task quality-gate (CI, per PR)

```yaml
quality-gate:
  desc: Full AI-DD quality gate
  cmds:
    - task: lint
    - task: type-check
    - task: test
    - task: audit-secrets
    - task: drift-check
    - task: anti-pattern-scan
    - task: libification-scan
    - task: traceability-verify  # FR/NFR IDs link to tests → code → JSONs
```

All must pass. Any failure blocks merge.

---

## 2. Commit-to-Commit Drift Checker

Runs as a CI job after every push to a feature branch. Compares current commit to parent (`HEAD^`):

| Check | Tool | Blocks Merge |
|-------|------|-------------|
| Mutated action refs | custom scanner | YES |
| Unpinned runners | custom scanner | YES |
| New `unwrap()` in lib code | custom scanner | YES |
| New `panic!()` in lib code | custom scanner | YES |
| Test count decreased | `cargo test --no-run` | YES |
| Coverage decreased | `cargo tarpaulin` | YES |
| Dependency version bump (Cargo.lock) | `cargo update` | warn |
| Added `unsafe` block | `grep unsafe` | YES |

Report as a CI comment on the PR. Use `gh pr comment`.

---

## 3. Anti-Pattern Detector

Runs as part of the quality-gate.

| Pattern | Severity | Auto-Fix |
|---------|----------|----------|
| `.unwrap()` in lib code | HIGH | suggest `?` or `expect()` with message |
| `panic!()` in lib code | HIGH | suggest `Result` return |
| `unwrap_or_else` with no context | MEDIUM | flag for review |
| `expect()` without message | MEDIUM | require message |
| Dead code (`cargo-dead-links` or `cargo-deplint`) | HIGH | delete |
| `TODO` without issue ref | LOW | add `TODO(issue-n)` |
| `unsafe` without safety comment | HIGH | require safety doc |
| Clone of `Arc::clone` pattern | MEDIUM | suggest `Arc::clone` |
| Stringly-typed enums | MEDIUM | suggest `newtype` |
| Broad `serde Deserialize` without validation | MEDIUM | require schema check |

Implement as: `cargo deny check` + custom grep/RIPgrep pass + `cargo-geiger` for unsafe surface area.

---

## 4. Libification Detector

Finds code that re-implements something available in a well-maintained crate.

| Pattern | Alternative |
|---------|------------|
| Manual `RwLock`/`Mutex` with 3 lines | `parking_lot` |
| Custom LRU cache | `lru` |
| Custom JSON validation | `jsonschema` or `pydantic` |
| Custom HTTP client retries | `reqwest` retry middleware |
| Custom time parsing | `chrono` / `time` |
| Custom UUID generation | `uuid` |
| Custom base64 | `base64` |
| Custom hex encoding | `hex` |
| Custom async sleep loop | `tokio::time::interval` |

Run with: `cargo-deplint` or custom `grep` pass against std / known-crate API surface.

---

## 5. Traceability Verification (FR/NFR → test → code → JSONs)

Per `FR-024-1` through `FR-024-8` (AgilePlus `FUNCTIONAL_REQUIREMENTS.md`):

- `agileplus-trace` binary ingests FR/NFR IDs from `FUNCTIONAL_REQUIREMENTS.md`
- Walks repo for tests annotated with FR IDs
- Maps test → code under test → JSON fixture/contract
- Emits `.trace.json` per FR
- `trace-validator` binary gates CI

CI check: `agileplus-trace --check` must pass on every PR touching `FUNCTIONAL_REQUIREMENTS.md`, `crates/`, `python/`, `*.test.ts`, or `*.spec.ts`.

---

## 6. WSM/Dino/Civis Audit Integration

WSM upstream documented flaws in fork-relative implementations. Key learnings:

- **No silent dependency resolution** — pin everything upstream explicitly
- **AI-generated code must be human-reviewed before commit** — use `git blame` + `gh pr review`
- **Drift between fork and upstream must be detected within 24h** — nightly cron comparing upstream diffs
- **AI-DD means: every generated line has a test that would catch its removal** — enforce 100% diff-coverage on new functions

Findings from WSM/Dino/Civis audits (pending retrieval from remote) will be incorporated into a revision of this document.

---

## 7. Drift Detection: Fork vs Upstream

For every fork that has an upstream (e.g. `agisync-mcp`, `dispatch-mcp`, `McpKit`):

```yaml
upstream-drift:
  schedule: "0 2 * * *"  # nightly at 02:00
  steps:
    - git fetch upstream
    - git log upstream/main..HEAD --oneline
    - git diff upstream/main --stat
    - gh issue create --label "upstream-drift" if diff > threshold
```

---

## 8. Secret Scanning & Credential Hygiene

- **pre-commit**: `trufflehog3` or `gitleaks` on staged files
- **CI**: `trufflehog github --only-verified` on every PR
- **Commit hook**: `git rev-parse --verify` on all commit SHAs to catch forged refs

---

## 9. CVE Policy for Experimental / Beta Dependencies

- Experimental/beta versions: OK to use
- CVE wait period: 7–30 days before patching mandatory
- CVSS score ≥ 9.0: patch immediately regardless of version status
- `cargo audit` runs weekly (restored in HeliosLab `cargo-audit.yml` after duplicate-`on:` fix)

---

## 10. Implementation Checklist

- [ ] `lefthook.yml` in AgilePlus + phenotype-tooling
- [ ] Taskfile `quality-gate` task in AgilePlus and 4 priority repos
- [ ] Anti-pattern detector as `cargo xtask check-anti-patterns`
- [ ] Commit-to-commit drift checker as `agileplus drift --check`
- [ ] Libification detector as `cargo xtask check-libification`
- [ ] `agileplus-trace` binary (FR-024 MVP)
- [ ] Nightly upstream-drift cron for forks
- [ ] Incorporate WSM/Dino/Civis audit findings (pending)
