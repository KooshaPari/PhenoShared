# review.md — Kilo Code Stand

`review.md` is the **automated PR review contract**. Every Phenotype repo runs agent reviewers on each PR; this file is the single authority they must not violate.

**Standard ID:** `kilo-code-stand@1` (fleet-wide; do not fork the ID — customize tiers only)

Bootstrap template: [`templates/genesis/review.md`](../../templates/genesis/review.md)

**AgilePlus trace:** FR-GENESIS-004 (automated PR governance per repo)

## Purpose

Humans cannot review every agent-authored PR at scale. Kilo Code Stand encodes:

- What **blocks** merge vs **warns** vs **informs**
- Which agents run and what they must read
- How findings are formatted for downstream automation
- Org-wide forbidden patterns (non-negotiable Block tier)

## Required sections

### 1. Standard identity

```markdown
## Kilo Code Stand
- standard_id: kilo-code-stand@1
- applies_to: [all PRs, agent-authored commits]
- owner: <team or repo maintainers>
- charter: charter.md
- sota: SOTA.md
```

The `standard_id` must remain `kilo-code-stand@1` across the fleet. Repo-specific rules extend tiers 2–3 only.

### 2. Review tiers

| Tier | Action | Agent behavior |
|------|--------|----------------|
| **Block** | Fail PR / block merge | Must fix or human override with documented exception |
| **Warn** | Comment; merge allowed if other checks pass | Should fix before next related change |
| **Info** | Optional note | No merge impact |

#### Block tier (minimum org set)

- Secrets, credentials, tokens in diff
- Scope outside `charter.md` (drive-by refactors, domain code in genesis trees)
- Missing tests per test policy below
- `delete_repo` or destructive git without absorption proof
- Force-push to protected default branch
- Push to remotes outside `<REDACTED>/*` without explicit user approval
- `git commit --amend` on already-pushed commits without explicit user request

#### Warn tier (recommended)

- Doc drift from documented SOTA choices (new dependency not in `docs/sota/`)
- Naming / style inconsistent with template conventions
- OKF manifest not updated when doc structure changes
- PR description missing intent citation or FR ID

#### Info tier (optional)

- Performance micro-optimizations
- Comment wording suggestions

### 3. Linkage to other artifacts

Review agents **must read** before verdict:

| Artifact | Use |
|----------|-----|
| `charter.md` | Scope boundaries — reject out-of-scope changes |
| `docs/sota/*.md` | New patterns must match researched alternatives or include ADR |
| `intent.md` + `docs/intent/synthesis.md` | Reject changes contradicting confirmed user goals without ADR |
| `okf/manifest.okf.yaml` | Resolve doc paths; verify manifest bump on structural changes |

### 4. Agent roster

| Agent | Trigger | Must read | Output |
|-------|---------|-----------|--------|
| GitHub Actions / CodeQL | push, PR | — | workflow conclusion |
| `phenotype-compliance-scanner` | PR | charter, review | compliance report |
| KodeVibe | PR (if `.kodevibe.yaml`) | review tiers | static findings |
| kwality / Benchora | PR label `llm-review` | review LLM section | LLM validation |
| Custom review agent | PR | **this file** | Kilo Review Summary |

Document repo-specific agents in the template table; keep org blocklist identical.

### 5. Test and evidence requirements

| Change type | Required evidence |
|-------------|-------------------|
| Bugfix | Regression test or documented repro steps in PR |
| Feature | Unit/integration tests; SOTA dimension note if UX/DX/AX affected |
| Refactor | Behavior unchanged proof (tests green; charter scope unchanged) |
| Docs-only | OKF manifest bump if paths/structure changed |
| Boundary move | Migration note; charter amendment; consumer repoint list |

HexaKit genesis repos: **do not require `cargo build`** on doc-only PRs (see `docs/sota/ops.md`).

### 6. LLM review section (optional block)

When PR has label `llm-review`:

1. Confirm PR description cites `intent.md`, synthesis, or FR ID
2. Check SOTA alignment for new dependencies (security + alternatives dimensions)
3. Flag assumptions not recorded in `docs/intent/synthesis.md` or `assumptions.md`

### 7. Forbidden patterns (org blocklist)

Extend per repo in charter **Out of scope** — never remove org blocklist items:

- Placing domain SDK code in HexaKit genesis trees
- Disabling secret scan workflows without charter amendment
- Merging with open Block-tier findings unless `needs-human` escalation documented

### 8. Output format for review agents

All automated reviewers should emit (or append) this structure:

```markdown
## Kilo Review Summary
- verdict: pass | fail | needs-human
- standard_id: kilo-code-stand@1
- charter_alignment: yes | no | unclear
- sota_alignment: yes | no | n/a
- intent_alignment: yes | no | unclear
- findings:
  - severity: block | warn | info
    file: path/to/file
    line: 42
    rule_id: kilo.block.scope.charter
    message: "Adds domain crate outside charter in-scope"
```

`needs-human` is valid when charter or intent is ambiguous — not a silent pass.

## Escalation

| Situation | Action |
|-----------|--------|
| Block + user explicitly requested exception | Human merge with PR comment citing charter amendment plan |
| Intent vs charter conflict | Update synthesis + charter; do not merge until reconciled |
| SOTA violation with strong reason | Add ADR linked from `docs/sota/alternatives.md` |

## Bootstrap

1. Copy `templates/genesis/review.md`
2. Set `owner` and agent roster for your repo
3. Customize Warn/Info tiers only
4. Keep `standard_id: kilo-code-stand@1`
5. Link from `charter.md` governance table

## Related specs

- [STANDARD.md](STANDARD.md)
- [CHARTER_SPEC.md](CHARTER_SPEC.md)
- [SOTA_SPEC.md](SOTA_SPEC.md) — alignment checks
