# Assignment contract proposal: SCTBDD-style human freeze and assignment packet

**Status: PROPOSAL ONLY. NOT IMPLEMENTED.**

Nothing in this document is built. No schema, CLI flag, MCP tool, table, directory or workflow
described here exists in AgilePlus or in dagrun. Every identifier, path, revision number and hash
shown is illustrative and illustrative only. This file is a design proposal to be reviewed,
challenged and accepted or rejected by a human before any implementation begins.

It is a candidate answer to the "Epic direction", "Verification and safety" and "Ownership
boundaries" items in `docs/research/traceability-closure.md`.

## 1. Purpose

Give a downstream implementing agent a stable, human-approved contract to work against, and give
an independent grader a stable, human-approved contract to judge the result against. The two
contracts are the same frozen artifact, read through two different lenses.

The method is informed by SCTBDD and related approaches. The intended expansion and precise
meaning of SCTBDD remain to be confirmed with the user. Requirements and observable behavior
are refined with a human, proposed for approval as a revision, and then handed to implementers
and graders. The approval and freeze semantics below are proposals, not established behavior.

## 2. Roles

| Role | Owns | Does not own |
|---|---|---|
| Human approver | Approval of a freeze, approval of any revision that supersedes it | Implementation, grading |
| AgilePlus | Existing feature lifecycle, spec artifacts, work packages, governance rules, audit chain; candidate owner for freeze records | Exclusive ownership of execution: its CLI can also dispatch agents |
| dagrun | DAG plan, node scheduling, harness execution, artifact collection, evidence capture, trace export | Feature lifecycle, grading policy, approval semantics |
| Grader | Test suite content, rubric, scoring | Feature lifecycle, execution |
| Submission agent | Implementing against the frozen contract | The grader suite, the rubric, the freeze |

## 3. Assignment packet contents

A packet is a proposed frozen, self-describing bundle. Its authoritative owner and materialization
path remain unresolved; avoid creating a competing source of truth.

```text
packet/
  packet.json          # identity, revision, freeze record, hashes of every part below
  contract.md          # human-readable statement of intent, requirements, scenarios
  requirements.json    # machine-readable requirement list with stable ids
  scenarios.json       # observable behavior, each bound to one or more requirements
  scope.md             # allowed files, starter files, forbidden areas
  public_tests/       # visible checks, safe for the submission agent to read
  grader_ref.json     # pointer to the private suite, by hash and location only
```

`grader_ref.json` names the private suite but does not contain it. The submission agent may read
the pointer and may not read the suite.

## 4. Stable identifiers

Identifiers are natural keys and are stable across processes, machines and exports. Integer
autoincrement ids are never used: they are not portable and they leak storage layout.

| Entity | Identifier form | Example |
|---|---|---|
| Packet | `AP-<feature_slug>` | `AP-assignment-contract-demo` |
| Feature | `feature_slug` (AgilePlus natural key) | `assignment-contract-demo` |
| Requirement | `FR-<n>` | `FR-001` |
| Scenario | `SC-<n>` | `SC-001` |
| Public test | `PT-<n>` | `PT-001` |
| Private test | `HT-<n>` (grader-owned) | `HT-001` |
| Negative control | `NC-<n>` | `NC-001` |
| Work package | `WP-<n>` | `WP-001` |
| Frozen revision | `REV-<4 digit>` | `REV-0001` |
| Freeze record | `FREEZE-<revision>` | `FREEZE-REV-0001` |

The feature slug is the join key across AgilePlus, the packet and dagrun plan nodes. A requirement
carries a stable id because a requirement must survive refactors of the surrounding document
structure.

## 5. Human approval and the freeze

The conversation before the freeze is deliberately human-led and incremental:

1. **Refine.** The human states intent. Requirements are proposed, challenged and revised. Each
   requirement is given a stable id at the moment it is first written, not later.
2. **Bind.** Every requirement is bound to at least one scenario, and every scenario to at least one
   observable check. A requirement with no scenario is not freezable.
3. **Approve.** The human approves a candidate revision. Approval is recorded with approver,
   timestamp, and the content hash of the exact bytes approved.
4. **Freeze.** The freeze produces an immutable revision `REV-n` and a freeze record that pins: the
   content hash of every packet part, the hash of the private suite, the approved requirement set,
   and the approver identity.

After the freeze, the frozen revision is append-only. It is never edited, never re-rendered, never
regenerated. A change to any part produces a new revision.

The freeze is not implied by elapsed time, by file existence, by a passing test, or by an agent
reporting that it finished a conversation. It exists only as an explicit, hash-pinned human act.

## 6. Immutable revisions and change impact

A revision is immutable. Its content hash is the identity. When any part of the contract changes,
the change is expressed as a new revision with an explicit delta.

Each new revision carries a **change impact set**, computed and reviewed, not inferred silently:

- requirements added, removed or semantically altered (text diff alone is insufficient, an altered
  requirement is flagged for human confirmation),
- scenarios affected and therefore public tests that must be revised,
- private tests whose expected outcomes changed,
- work packages that must be reopened or newly created,
- whether the previous freeze is superseded or remains in force.

Two rules follow from this. A revision cannot be produced without a stated impact set. And a
revision that invalidates frozen expectations cannot be silently adopted by an in-flight run: a
dagrun node that was dispatched against `REV-0001` continues to be graded against `REV-0001`, and
its result is recorded as belonging to that revision. Grading never mixes revisions.

## 7. Grader isolation

The grader must not be able to be flattered by the submission, and the submission must not be able
to edit the instrument that judges it.

- **Separate execution.** The grader runs in its own environment with its own workspace. It never
  shares mutable state with the submission workspace.
- **Read-only grader.** The grader may read the submission workspace. It never writes to it.
- **Hidden suite.** The private suite is not present in the packet directory the submission agent
  can read. Only its hash and location are visible. The submission agent is told that a private
  suite exists and is not told its content.
- **Read-only submission.** The submission agent cannot read or modify the private suite path.
  Enforcement requires a defined adversary and independently validated isolation boundary. Filesystem
  permissions and container layout alone are not sufficient evidence of isolation.
- **No shared session.** Grading does not reuse the agent session that produced the submission. A
  grader that shares context with the submission cannot be independent.
- **Hermetic conditions.** Pinned toolchain, pinned dependency set, no network access, fixed seed
  and fixed locale where the tooling permits it. Any nondeterminism that survives is recorded as a
  property of the test rather than silently averaged away.
- **Provenance.** The grade record captures the packet revision hash, the private suite hash, the
  toolchain versions, the command line, the exit code and the raw output digest.

A hash proves that a file is unchanged. It does not prove that the file is correct, and it does not
prove that the tests are meaningful. A passing suite is evidence of a property of the submission,
never proof of semantic correctness of the contract itself.

## 8. Negative controls

A suite that passes everything grades nothing. Each frozen revision carries negative controls that
the grader runs alongside the real suite, and the grader reports FAIL when a control misbehaves.

| Control | Expectation |
|---|---|
| `NC-001` empty submission | Starter files only. Must FAIL. |
| `NC-002` no-op submission | Files present, bodies unchanged from starter. Must FAIL. |
| `NC-003` inverted-logic sentinel | A known-correct mutant of one requirement. Must FAIL. |
| `NC-004` missing evidence | Evidence artifact absent from a submission claiming completion. Must FAIL, and must not be reported as PASS with a warning. |
| `NC-005` nondeterminism probe | Suite run twice on the same submission. Divergence must be surfaced, not hidden. |
| `NC-006` suite integrity | Private suite hash equals the hash pinned in the freeze record. Mismatch must abort grading. |

`NC-003` is the one that matters most, because a suite that passes an inverted implementation is
testing nothing about the behavior it claims to cover. Controls are part of the frozen revision,
so changing them requires a new revision.

## 9. Ownership boundary: AgilePlus owns the lifecycle, dagrun executes

**Proposed boundary, not a current capability or settled ownership decision.** AgilePlus owns its
existing feature lifecycle, specifications, work packages, governance and audit. Whether AgilePlus
should also own approval and freeze records remains open. Its CLI can dispatch agents, so execution
capability is not exclusive to dagrun. Avoid creating a second lifecycle or governance platform.

**dagrun executes.** dagrun owns the DAG plan, node scheduling, provider and harness selection,
artifact collection, evidence capture and trace export. A dagrun node references a frozen revision
by hash and a requirement or scenario set by id. dagrun does not decide what is approved, does
not define what counts as correct, and does not reinterpret a requirement.

**The grader owns grading.** The rubric, the test suite and the score belong to the grader. dagrun
runs the grader as a node and records its output. It does not author or alter the rubric.

**Traceability consumers read both.** A consumer joins AgilePlus state and dagrun evidence through
the feature slug and the revision hash. The join is read-only on both sides.

## 10. Traceability chain

The chain that must be walkable end to end, with no gaps and no hand-waving:

```text
intent
  -> requirement (FR-n)
  -> scenario (SC-n)
  -> public test (PT-n) / private test (HT-n)
  -> work package (WP-n)
  -> dagrun node + agent output
  -> evidence artifact
  -> grade result
```

Every edge is an explicit foreign key, not a shared paragraph. A requirement with no scenario, a
scenario with no test, a test with no grade and a grade with no evidence are all detectable and
all are defects, not acceptable states.

## 11. Unresolved ownership

These are open. They are not settled by this proposal, and each one must be answered by a human
before implementation begins.

1. **Authoritative approval record.** Is the freeze a first-class AgilePlus artifact in the audit
   chain, or a field on the feature? Proposed: AgilePlus artifact, audited, so that approval
   cannot be lost by a run-record overwrite.
2. **Physical location of the private suite.** In the AgilePlus artifact tree, where the
   submission agent might be able to reach it, or in a dagrun-private store? Proposed: dagrun
   private store, referenced by hash.
3. **Freeze to revision mapping.** Does the packet own its revision history, or does AgilePlus
   `spec_revisions` own it with the packet as a materialized view? Proposed: AgilePlus owns it.
4. **What a freeze blocks.** Does a freeze block AgilePlus transitions such as `implementing`, or
   only dagrun dispatch? Proposed: only dagrun dispatch is blocked. AgilePlus lifecycle must keep
   moving, otherwise the freeze becomes a governance deadlock.
5. **Rubric ownership.** Who writes the rubric, and who arbitrates a disputed score? Unassigned.
6. **Cross-repo packets.** A packet whose scope spans repositories has no single owning repo, and
   therefore no single `docs/agileplus/<slug>/` home. Unresolved.
7. **Nondeterminism policy.** How many repetitions, what aggregation, and who decides when
   variance is a test defect rather than a submission defect. Unresolved.
8. **Retirement.** When a feature ships and the packet is retired, what happens to the frozen
   revisions, the private suite and the historical grades? Unresolved, and it affects auditability.
9. **Adversarial submission.** A submission agent that knows the grader exists may try to detect
   and satisfy the grader rather than satisfy the contract. The threat model for that case is not
   written.

## 12. Acceptance criteria for a future implementation

Proposed, measurable, and not yet met by anything.

1. A packet can be created from an existing AgilePlus feature by slug, and the packet's `packet.json`
   records the source revision hash.
2. A freeze attempt is refused when any requirement lacks a scenario or any scenario lacks a test.
3. A frozen revision cannot be edited. Attempting to write to its path is rejected by tooling, and
   the rejection is recorded.
4. A revision that changes a requirement produces a change impact set naming affected scenarios,
   tests and work packages, and the supersession decision is human-supplied.
5. The grader cannot write into the submission workspace, and the submission agent cannot read the
   private suite path. Both are proven by a test that attempts it and expects refusal.
6. `NC-001` through `NC-006` run with every grade, and a control failure prevents a PASS verdict.
7. Two grades of the same submission against the same revision produce identical result records
   under hermetic conditions.
8. The full chain from `FR-n` to grade is traversable from the packet alone, and each edge resolves
   to exactly one artifact.
9. No dagrun node can be dispatched against a revision that has no freeze record.

## 13. Non-goals

- No second feature lifecycle, work-package system or governance platform.
- No integer identifiers in any exchange format.
- No claim that a passing suite proves the contract is semantically correct.
- No implicit approval through file existence, elapsed time or agent self-report.
- No change to AgilePlus feature state transitions as part of this work.

## 14. Decision requested

A human decides, per item in section 11, and records the answer. Implementation begins only after
the ownership answers exist, because the ownership boundary is what keeps this an extension of
AgilePlus rather than a competitor to it.

Until that happens this document remains a proposal, and the closure ledger in
`docs/research/traceability-closure.md` remains OPEN.
