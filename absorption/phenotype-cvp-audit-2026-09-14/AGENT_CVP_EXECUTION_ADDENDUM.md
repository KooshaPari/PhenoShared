# CVP Execution Addendum - 2026-09-14

Apply this to active implementation, consolidation, and stabilization agents. This is an additive correction, not a request to restart completed audits.

## Parent outcome

You own a **capability slice** that contributes to one accepted repository/product outcome. Your task is not complete merely because a PR merged or a test suite ran. Continue toward the repository's accepted **Current Viable Product (CVP)**, migration, incubation proof, or retirement target.

A CVP is the fastest deployable, installable, coherent and supportable version of the **currently accepted feature horizon**. Do not cut accepted current functionality just to claim an MVP. Do not keep adding roadmap breadth while packaging, durability, quality or polish remain unfinished.

## Current-state reconciliation

Before edits:

1. Read repository instructions and accepted role/disposition.
2. Inspect local worktree(s), dirty/untracked files, branches, stashes, current remote heads, PRs, reviews, hosted checks, releases and installed artifacts.
3. Reconcile prior evidence against current SHAs. Reuse valid evidence; invalidate stale evidence.
4. State the slice's current states independently: `WORKING`, `PUBLISHED`, `INTEGRATED`, `VERIFIED`, `PACKAGED`, `INSTALLED`, `RELEASED`, `ADOPTED`.
5. Identify the exact next state transition and its acceptance evidence.

## Semantic compression first

Treat complexity as a defect when it does not buy semantics.

- Collapse duplicates into one canonical implementation.
- Reduce public concepts and dependency fan-out.
- Split huge modules along domain/port/adapter/applet boundaries, not arbitrary line counts.
- Required current dead code: wire or implement it now.
- Future-only dead code: preserve intent/spec/research, remove unreachable executable code.
- Superseded code: remove from active tree; retain history/provenance.
- Unknown/orphan code: characterize before deletion.
- Generated/vendor code does not count as hand-authored semantic complexity.

Before/after simplification must retain or improve contract tests, negative tests, critical QA coverage and performance budgets.

## Recursive applets

Use hexagonal applets as the default compositional unit where helpful. An applet declares identity, capabilities, ports, adapters, state, permissions, resource constraints, lifecycle/health, optional UI/CLI/API surfaces and optional child applets.

A composite applet may federate children and re-export a deliberately reduced capability surface. A product CVP is a composition profile of applets plus adapters/policy. Do **not** create a repository per applet unless independent release/security/consumer/governance boundaries justify it.

## Packaging and installation

Do not stop at `cargo build`, `npm build`, or equivalent.

For a macOS GUI CVP:

- Build a real `.app` from a clean checkout/release candidate.
- Install it outside the source repo, preferably `~/Applications` for internal CVP or `/Applications` for release-like qualification.
- Verify bundle ID, version, icon, architecture, assets and platform data paths.
- Verify Finder/`open -b` launch and Spotlight/LaunchServices discoverability.
- Launch with no repo cwd, developer shell, sibling checkout or build tree.
- Exercise first run, core task, save/restart, error/recovery and settings.
- Capture phenotype-journeys evidence from that installed artifact.
- Tie tested SHA, artifact digest and release artifact together.

For CLI/library/service/lab repositories, use the role-specific equivalent: installable binary/package/consumer/deployment/reproducible runner. Do not manufacture a GUI solely to satisfy the packaging rule.

## QA / QE / QC acceptance

Each applicable assurance family is independent. Do not average them together.

- Unit: >=85% against reviewed structural + behavioral denominator.
- Integration: >=85% against its own boundary/contract denominator.
- E2E: >=85% against declared journeys and relevant instrumented implementation.
- Mutation: >=85% eligible non-equivalent mutants where applicable.
- Other applicable evaluation families: >=85% against their meaningful reviewed denominator.
- Critical security, privacy, data-integrity, destructive-action, packaging and promised-compatibility obligations: 100%.
- Mandatory selected tests/checks actually run and pass. Skip/unknown/blocked is not pass.

Test counts are not coverage. PR comments resolved is not proof. Screenshots are not E2E.

## Visual/polish gate

For GUI apps, exercise and review: first-run, empty, loading, normal, partial, error, degraded/offline, recovery, settings and upgrade state. Check hierarchy, typography, density, spacing, clipping, resizing, keyboard focus, destructive confirmations, native conventions, accessibility and perceived performance.

Automated screenshot diffs are supporting evidence. They cannot establish taste. Preserve raw installed-product captures and keep marketing edits separate.

## Repository retirement / deletion

Ordinary agents and subagents do **not** permanently delete repositories.

Hard rule: repositories that participate in fork networks are NO-DELETE by default. Tombstone them instead.

Lifecycle: `ACTIVE -> RETIRING -> TOMBSTONED -> QUARANTINED -> DELETE_ELIGIBLE -> DELETED`.

Default retention after tombstone: 60 days. Delete eligibility requires non-fork-network status, successor parity, consumer migration, preservation manifest, restore drill, no active session/worktree, retention elapsed and explicit operator approval.

A repository name (`zz-*`, `zz-archive-*`) is not lifecycle authority. Record lifecycle keyed by GitHub repository ID.

## Reporting

Report concise deltas, not another broad essay:

- capability slice + owner
- accepted CVP/retirement target
- current exact SHA / artifact digest
- state transitions completed this turn
- semantic complexity removed or introduced
- independent QA measurements
- package/install/journey evidence
- remaining blocker with owner and exact unblock action
- next smallest coherent CVP step

When no authorized work remains, release the worker slot with the parent outcome still explicitly owned. Do not call the repository complete from a bounded repair alone.
