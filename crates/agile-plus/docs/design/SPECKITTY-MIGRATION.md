# SpecKitty → AgilePlus Migration

> Single-source-of-truth mapping from the cursor-side `spec-kitty` plugin
> workflow to the owned `agileplus-cli` (`ap`) successor.

| Field            | Value                                                          |
| ---------------- | -------------------------------------------------------------- |
| Status           | ✓ Active — migration in flight (sibling PR)                    |
| Scope            | 13 SpecKitty cursor commands + scoring engine                  |
| Owner            | <REDACTED> / AgilePlus (Rust workspace)                        |
| Successor        | `ap` (agileplus-cli) — see `crates/agileplus-cli/`             |
| Supersedes       | `.cursor/commands/spec-kitty.*.md`                            |
| Cross-references | `crates/agileplus-governance/src/scoring_engine.rs:6`          |
| Created          | 2026-07-05                                                     |
| Provenance       | Tier 1 — hand-authored (this doc), see §8                      |

---

## 1. Why migrate

SpecKitty was a **Cursor-side** enforcement layer: 13 markdown commands
under `.cursor/commands/spec-kitty.*.md` that an operator invokes from
the IDE. Each command was a long prompt that walked the agent through
the spec-first workflow (research → specify → clarify → plan → tasks →
checklist → analyze → constitution → implement → review → dashboard →
status → accept → merge).

The problem is no longer novelty — it is **authority**. SpecKitty's
artifacts (research.md, spec.md, plan.md, tasks.md, prompts/, etc.)
live in `.kittify/` and are interpreted by whichever cursor agent is in
the loop. There is no typed artifact, no machine-readable contract, no
shared PM spine across forks or repos. Cross-repo consistency is a
markdown diff.

**AgilePlus is the owned successor.** It is a Rust workspace whose
governance crate (`crates/agileplus-governance/`) and CLI
(`crates/agileplus-cli/`) **subsume** SpecKitty's 13 commands and
**extend** them with:

- typed artifact schemas (spec.md → `agileplus-domain::SpecState`)
- shared PM/traceability spine (`shared-traceability/` +
  `traceability-core/`)
- governed channels (`crates/agileplus-governance/src/channel.rs`)
  with rate-limit + audit + policy + rate-limiter
- machine-readable FR/NFR catalogs
- a v38-cluster-formatted scoring engine that supersedes
  SpecKitty's PILLARS-CATALOG evaluator

Migration is one-way: every `spec-kitty.*.md` shim becomes a 2-line
redirect to the canonical `ap <cmd>` entrypoint. Cursor stays a UI;
AgilePlus owns the truth.

---

## 2. Concept mapping

Each SpecKitty concept resolves to **one** AgilePlus owner. No
duplication; no ambiguity. When in doubt, run `ap` — do not invoke the
shim.

| SpecKitty concept   | Cursor shim                                | AgilePlus owner (crate / module)                                   | AgilePlus CLI                              |
| ------------------- | ------------------------------------------ | ------------------------------------------------------------------ | ------------------------------------------ |
| Research artifact   | `.cursor/commands/spec-kitty.research.md`  | `agileplus-cli::commands::research` + `agileplus-domain::research` | `ap research <topic>`                      |
| Feature spec        | `.cursor/commands/spec-kitty.specify.md`   | `agileplus-cli::commands::specify` + `specify/{prompt,tests}.rs`   | `ap specify <name>`                        |
| Clarification pass  | `.cursor/commands/spec-kitty.clarify.md`   | `agileplus-cli::commands::specify` clarification phase              | `ap specify --clarify <name>`              |
| Implementation plan | `.cursor/commands/spec-kitty.plan.md`      | `agileplus-cli::commands::plan` + `plan/{artifacts,parsing}.rs`     | `ap plan <name>`                           |
| Work-package tasks  | `.cursor/commands/spec-kitty.tasks.md`     | `agileplus-cli::commands::implement` + `implement/{worker,tests}.rs`| `ap tasks <plan-id>`                       |
| Domain checklist    | `.cursor/commands/spec-kitty.checklist.md` | `agileplus-cli::commands::validate` + `validate/{evidence,report}` | `ap checklist <name>`                      |
| Cross-artifact linter | `.cursor/commands/spec-kitty.analyze.md` | `agileplus-cli::commands::validate` + `agileplus-trace-validator`  | `ap analyze <name>`                        |
| Project constitution| `.cursor/commands/spec-kitty.constitution.md` | `agileplus-cli::commands::governance`                            | `ap constitution <repo>`                   |
| Implementation work | `.cursor/commands/spec-kitty.implement.md` | `agileplus-cli::commands::implement` (worker.rs)                  | `ap implement <wp-id>`                     |
| Code review         | `.cursor/commands/spec-kitty.review.md`    | `agileplus-cli::commands::review_loop`                            | `ap review <wp-id>`                        |
| Web dashboard       | `.cursor/commands/spec-kitty.dashboard.md` | `agileplus-cli::commands::dashboard`                              | `ap dashboard`                             |
| Kanban status       | `.cursor/commands/spec-kitty.status.md`    | `agileplus-cli::commands::scope_status` + `cycle/{list,show}.rs`   | `ap status [project]`                      |
| Feature acceptance  | `.cursor/commands/spec-kitty.accept.md`    | `agileplus-cli::commands::retrospective` + `retrospective/{metrics,report}.rs` | `ap accept <feature>`                  |
| Merge + cleanup     | `.cursor/commands/spec-kitty.merge.md`     | `agileplus-cli::commands::ship` + `agileplus-git`                   | `ap merge <branch>`                        |
| **Scoring engine**  | (SpecKitty has no equivalent — new)        | `agileplus-governance::{rubric,code_scanner,scoring_engine}`        | `ap rubric score --repo <path>`            |

The bottom row — `ap rubric score` — has no SpecKitty ancestor. It is
the win: SpecKitty's `PILLARS-CATALOG` scoring was external; AgilePlus
embeds it.

---

## 3. Workflow equivalence — the 13-step canonical flow

The SpecKitty 13-step workflow (research → … → merge) maps one-to-one to
`ap` subcommands. Worked example: SpecKitty vs AgilePlus.

| # | SpecKitty (Cursor)                                    | AgilePlus (`ap` CLI)                                  |
| - | ----------------------------------------------------- | ----------------------------------------------------- |
| 1 | `/spec-kitty.research rate-limiting-strategy`         | `ap research rate-limiting-strategy`                 |
| 2 | `/spec-kitty.specify RateLimiter`                     | `ap specify RateLimiter`                             |
| 3 | `/spec-kitty.clarify RateLimiter`                     | `ap specify --clarify RateLimiter`                   |
| 4 | `/spec-kitty.plan RateLimiter`                        | `ap plan RateLimiter`                                |
| 5 | `/spec-kitty.tasks RateLimiter`                       | `ap tasks RateLimiter`                               |
| 6 | `/spec-kitty.checklist RateLimiter`                   | `ap checklist RateLimiter`                           |
| 7 | `/spec-kitty.analyze RateLimiter`                     | `ap analyze RateLimiter`                             |
| 8 | `/spec-kitty.constitution rate-limiter/`              | `ap constitution agileplus-governance`               |
| 9 | `/spec-kitty.implement RateLimiter/01-core`           | `ap implement WPK-01-core`                            |
| 10| `/spec-kitty.review WPK-01-core`                      | `ap review WPK-01-core`                              |
| 11| `/spec-kitty.dashboard`                               | `ap dashboard`                                       |
| 12| `/spec-kitty.status RateLimiter`                      | `ap status RateLimiter`                              |
| 13| `/spec-kitty.accept RateLimiter`                      | `ap accept RateLimiter`                              |
| ✓ | `/spec-kitty.merge WPK-01-core`                       | `ap merge WPK-01-core`                               |

**Worked example.** Operator needs a new `RateLimiter` feature in
`agileplus-governance`. Old way: type `/spec-kitty.research
rate-limiting-strategy` in Cursor → walk a 40-line markdown prompt →
agent emits `kitty-specs/rate-limiter/research.md`. New way: from the
workspace root, run `ap research rate-limiting-strategy` → typed
artifact lands in `agileplus-domain::research::ResearchArtifact` and a
markdown preview is rendered for the IDE to consume. Same operator
intent, machine-readable substrate.

The same table is mirrored in the cursor shim files themselves (the
`spec-kitty.*.md` files are being shortened to a one-liner redirect
in the sibling migration PR — see §6).

---

## 4. Scoring engine migration — the win

SpecKitty had a PILLARS-CATALOG + scoring engine as bolt-on external
scripts. AgilePlus **owns** it as native Rust. The mapping is at four
levels: parser, scanner, orchestrator, renderer.

### 4.1 Parser — `agileplus-governance::rubric`

[`crates/agileplus-governance/src/rubric.rs:15`](../../crates/agileplus-governance/src/rubric.rs)

`RubricCatalog` (line 15) parses the catalog JSON into typed structs
(`Pillar`, `ScoringSpec`, `SubPillar`). Source of truth:
`crates/agileplus-governance/data/PILLARS-CATALOG.json` (parses
unmodified, byte-shape preserved for diffability).

### 4.2 Scanner — `agileplus-governance::code_scanner`

[`crates/agileplus-governance/src/code_scanner.rs:86`](../../crates/agileplus-governance/src/code_scanner.rs)

`RepoScan` (line 86) holds structural facts extracted from the target
repo. Free function `scan_repo(repo_root)` (line 104) walks the tree
and yields typed `EvidenceItem` records (line 16). Pure function; no
side effects.

### 4.3 Orchestrator — `agileplus-governance::scoring_engine`

[`crates/agileplus-governance/src/scoring_engine.rs:71`](../../crates/agileplus-governance/src/scoring_engine.rs)

Top-level entry point `evaluate<R, C>(repo_root, catalog_path, filter)
-> Result<ScoreReport>` (line 71) wires the rubric parser and the
scanner together via a `SCORING_RULES` registry, then dispatches per
cluster to the rule set. Returns a typed `ScoreReport` (line 61).

### 4.4 Renderer — `render_markdown`

[`crates/agileplus-governance/src/scoring_engine.rs:311`](../../crates/agileplus-governance/src/scoring_engine.rs)

`render_markdown(report) -> String` (line 311) emits markdown in the
exact byte-shape required by `phenotype-org-audits/audit-v38/output/
<repo>/<cluster>.md`. Diffability against the canonical audit catalog
is intentional.

### 4.5 CLI surface — `ap rubric score`

Proposed surface (parent dispatch pending):

```text
ap rubric score --repo <path> \
                [--clusters C03,C10,C11] \
                [--output <file>] \
                [--catalog <path-to-PILLARS-CATALOG.json>]
```

Defaults:

- `--catalog` resolves to
  `crates/agileplus-governance/data/PILLARS-CATALOG.json` if unset
  (the embedded catalog).
- `--clusters` is optional; unset = all clusters in the catalog.
- `--output` defaults to stdout; if set, writes UTF-8 markdown and
  exits 0 only on successful render.

This is the **single canonical entrypoint**. There is no
`speckitty score`, no `audit-toolkit score`, no `v38-eval`. Everything
goes through `ap`.

---

## 5. Why AgilePlus beats SpecKitty

The case for an owned successor is not aesthetic — it is operational.

| Dimension                | SpecKitty                                | AgilePlus                                    |
| ------------------------ | ---------------------------------------- | -------------------------------------------- |
| Runtime                  | Cursor markdown prompt                   | Native Rust binary (`ap`)                    |
| Architecture             | Single-file markdown workflows           | Hexagonal — `crates/agileplus-{cli,domain,governance,api,*}` |
| Governance channel       | Implicit (operator trust)                | Typed: `agileplus-governance::channel` with rate limit, audit, policy |
| Audit + rate limiting    | None — markdown only                     | `agileplus-governance::{audit,rate_limiter,policy}` |
| PM/traceability spine    | None — `.kittify/` markdown              | `shared-traceability/` + `traceability-core/` — typed, cross-repo |
| FR/NFR catalogs          | Markdown tables                          | Machine-readable JSON / typed structs        |
| Scoring engine           | External scripts                         | In-crate (`agileplus-governance::scoring_engine`) |
| Worktree isolation       | Recommended, not enforced                | First-class: `ap implement` creates the worktree |
| Test surface             | Manual                                   | `cargo test -p agileplus-governance scoring_engine` (TDD) |
| Sub-repo reuse           | Copy `.kittify/` per repo                | Cargo workspace dependency on shared crates   |

A 200-line cursor prompt becomes a typed function; a 40-line artifact
becomes a struct. Every gate the operator wanted SpecKitty to enforce
(clarify before implement, plan before tasks, review before merge) is
**also** enforced by `ap` — at the type and CLI level, not at the
politeness of the LLM.

---

## 6. Migration checklist

End state: zero behavior gap, zero operator confusion, zero
duplication.

- [x] PILLARS-CATALOG landed in `agileplus-governance` (PR #893)
- [x] `rubric.rs` parser landed (PR #893, 233 lines)
- [x] `code_scanner.rs` extractor landed (PR #893, 232 lines)
- [x] `scoring_engine.rs` orchestrator landed (this PR, 564 lines)
- [ ] `ap rubric score` CLI subcommand (parent dispatch in flight)
- [ ] 14 Cursor shim files rewritten to delegate to `ap`
      (sibling migration in this PR; see task #7)
- [x] `docs/design/SPECKITTY-MIGRATION.md` authored (this doc)
- [ ] `CLAUDE.md` updated to point at `ap` as the canonical
      entrypoint (sibling edit pending)

Completion = all boxes ticked and `cargo build -p agileplus-cli &&
cargo test -p agileplus-governance scoring_engine` is green.

---

## 7. Cross-references

| Resource                                  | Path                                                                                       |
| ----------------------------------------- | ------------------------------------------------------------------------------------------ |
| SpecKitty shim files                      | `.cursor/commands/spec-kitty.{research,specify,clarify,plan,tasks,checklist,analyze,constitution,implement,review,dashboard,status,accept,merge}.md` |
| AgilePlus CLI surface                     | `crates/agileplus-cli/src/commands/`                                                       |
| Governance crate (scoring owner)          | `crates/agileplus-governance/`                                                              |
| Rubric parser                             | `crates/agileplus-governance/src/rubric.rs`                                                 |
| Code scanner                              | `crates/agileplus-governance/src/code_scanner.rs`                                           |
| Scoring orchestrator + renderer           | `crates/agileplus-governance/src/scoring_engine.rs`                                         |
| PILLARS-CATALOG.json                      | `crates/agileplus-governance/data/PILLARS-CATALOG.json`                                    |
| SpecState domain model                    | `crates/agileplus-domain/src/domain/spec_state.rs`                                         |
| Shared traceability spine                 | `crates/shared-traceability/` + `crates/traceability-core/`                                 |
| v38 audit catalog (byte-compat target)    | `phenotype-org-audits/audit-v38/catalog/` (across the org tree)                             |

The rendering contract is fixed: output of
`agileplus-governance::scoring_engine::render_markdown` is
byte-comparable with `phenotype-org-audits/audit-v38/output/<repo>/
<cluster>.md`. Verifying this on a known-good sample repo is the
acceptance test for the scoring migration.

---

## 8. Provenance

Per the project's three-tier visual-identity + provenance directive:

| Tier | Artifact                                  | Author                |
| ---- | ----------------------------------------- | --------------------- |
| 1    | This design doc                           | Hand-authored (Opus)  |
| 1    | `crates/agileplus-governance/src/scoring_engine.rs` | Hand-authored (Opus) |
| 2    | Cursor shim redirects (14 files)          | Co-authored (parent → child) |
| 2    | `CLAUDE.md` update pointing at `ap`       | Hand-authored (Opus)  |
| 3    | Generated v38-cluster markdown outputs    | Generated by `render_markdown` |

Tier-1 artifacts are durable engineering: by hand, reviewed, never
generated. Tier-2 are co-authored — a parent writes the redirect and a
child fills in a 2-line body. Tier-3 is fully reproducible output.

---

## 9. Acceptance criteria

Migration is **complete** when all of the following hold:

1. `cargo build -p agileplus-cli` and
   `cargo test -p agileplus-governance scoring_engine` are green.
2. Every `.cursor/commands/spec-kitty.*.md` file's body is **only**
   `delegated: ap <cmd>` (no embedded workflow prose).
3. `ap rubric score --repo crates/agileplus-application --clusters C03`
   produces markdown diff-compatible with
   `phenotype-org-audits/audit-v38/output/agileplus-application/C03.md`.
4. `CLAUDE.md` lists `ap <cmd>` as the canonical entrypoint for the
   spec-first workflow.
5. Task #7 (Cursor shim rewrite) and the doc-edit pending box (§6) are
   resolved.

Until then, both surfaces coexist — shims forward to `ap` for anyone
who runs them. After cutover, the shims become inert; `.kittify/`
remains as legacy evidence (do not delete — preserved for
traceability).
