# Epic traceability autograder: frozen contract direction

Status: PROPOSED. Not implemented. "Frozen" here means a revisioned artifact (`REV-n`) that a human approves; it is append-only, superseded rather than mutated, and never re-rendered from a later revision.

## 1. Status

PROPOSED. No code, schema, CLI flag, MCP tool, table, directory or workflow described here exists in AgilePlus or in dagrun. Every identifier, path, revision number and hash shown is illustrative. This document is a freeze candidate for human approval; until approved it is not a contract.

## 2. Intent and closure

Intent: define an assignment-style specification and autograder direction informed by SCTBDD and related methods, where intent, requirements and behavior are refined with a human, approved expectations are frozen as immutable revisions, and downstream agents implement and test against them. Avoid duplicating AgilePlus. The epic owns exactly the freeze record, the assignment packet, the requirement->test->evidence binding, and grading.

Closure for this epic means: one human-approved frozen revision exists, its requirement->scenario->check->evidence chain is fully traversable with no orphans, and an independent grader can run against it end to end with negative controls.

## 3. Ownership boundary

| Owner | Owns | Must NOT own |
|---|---|---|
| AgilePlus | Feature lifecycle, spec artifacts, work packages, governance gate, audit chain, queue, retrospective, elicit (22 MCP tools in `PhenoShared/python/src/agileplus_mcp`) | Freezing, grading policy, rubric, execution scheduling |
| dagrun | DAG scheduling, harness execution, artifact predicates (`plan.Artifact`: min_bytes/must_contain/must_match/min_count/AllowEmpty in `cmd/dagrun/internal/plan/plan.go`), anti-gaming (`cmd/dagrun/internal/verify/antigaming.go`), trace, AgilePlus export/import bridge (`cmd/dagrun/internal/agileplus/agileplus.go`: "contract is NEVER invented", Unmapped) | Feature lifecycle, grading policy, approval semantics, requirement authoring |
| PhenoRegistry | Contract index, catalog of artifacts and cross-repo links | Execution, grading, lifecycle |
| Grader | Test suite content, rubric, scoring, negative controls | Feature lifecycle, execution, contract authoring |
| Human approver | Approval of a freeze, approval of any revision that supersedes it | Implementation, grading |

Already shipped by AgilePlus, must not be rebuilt (agileplus-surface.md §6): feature lifecycle, spec artifacts, work packages, governance gate, audit chain, queue, retrospective, elicit. Already owned by dagrun, must not be rebuilt: DAG scheduling, harness execution, artifact predicates, anti-gaming, trace, export/import bridge. The epic owns only the freeze record + assignment packet + requirement->test->evidence binding + grading.

## 4. Frozen contract schema

Versioned: `contract_version` (integer, starts at 1). All identifiers are natural keys, never integer autoincrement (`assignment-contract-proposal.md` §4). A frozen revision is immutable; its content hash is its identity.

Fields:

- `requirement`: stable id (`FR-n`), statement (text), kind (functional|non-functional|constraint), priority (P0..Pn), source (intent statement ref), status (required|optional|deferred)
- `scenario`: stable id (`SC-n`), bound requirement ids (`[]FR-n`), given (text), when (text), then (text), observable surface (text)
- `check`: stable id (`PT-n` public, `HT-n` private), bound scenario ids (`[]SC-n`), tier (public|private), runner (shell command or test entry), timeout (duration), determinism class (deterministic|probabilistic|environmental), expected signal (exit code, output predicate)
- `scope`: allowed paths (globs), starter paths (globs), forbidden paths (globs)
- `evidence`: per check: exit code (int), stdout digest (sha256), duration (ms), environment digest (toolchain+deps hash)
- `freeze`: revision (int), approved_by (identity), approved_at (RFC3339), supersedes (revision or null), content_hash (sha256 over canonical serialization)

Worked example (illustrative):

```json
{
  "contract_version": 1,
  "packet_id": "AP-assignment-contract-demo",
  "feature_slug": "assignment-contract-demo",
  "revision": 1,
  "supersedes": null,
  "requirements": [
    {"id":"FR-001","statement":"The tool exits 0 on valid input","kind":"functional","priority":"P0","source":"intent#1","status":"required"}
  ],
  "scenarios": [
    {"id":"SC-001","requirement_ids":["FR-001"],"given":"a valid file","when":"run","then":"exit 0","observable_surface":"process exit code"}
  ],
  "checks": [
    {"id":"PT-001","scenario_ids":["SC-001"],"tier":"public","runner":"go test ./... -run TestValid","timeout":"60s","determinism_class":"deterministic","expected_signal":"exit 0"}
  ],
  "scope": {"allowed":["src/**"],"starter":["src/main.go"],"forbidden":["vendor/**"]},
  "evidence": {"per_check":["exit_code","stdout_digest","duration_ms","environment_digest"]},
  "freeze": {"revision":1,"approved_by":"human","approved_at":"2026-11-12T00:00:00Z","supersedes":null,"content_hash":"sha256:0000..."}
}
```

## 5. Freeze protocol

1. Propose: human states intent; requirements are proposed, challenged, revised. Each requirement gets a stable id at first write (`assignment-contract-proposal.md` §5).
2. Bind: every requirement bound to >=1 scenario; every scenario to >=1 observable check. A requirement with no scenario is not freezable.
3. Review: human reviews candidate revision, including change impact set if it supersedes.
4. Approve: human approves; approval recorded with approver, timestamp, content hash of exact bytes approved.
5. Freeze: produce immutable `REV-n` and freeze record pinning content hash of every packet part, private suite hash, approved requirement set, approver identity.
6. Publish packet: packet materialized with `packet.json` recording source revision hash.
7. Implement: submission agent implements against frozen revision.
8. Grade: independent grader runs; grading never mixes revisions (`assignment-contract-proposal.md` §6).
9. Change: any change re-enters at step 1 as revision N+1 with `supersedes: N`. A revision cannot be produced without a stated impact set.

Escalation rule: an agent that finds a contradiction or material ambiguity MUST stop and escalate to the human approver rather than edit the frozen revision. Silent adoption of a changed revision by an in-flight run is forbidden.

## 6. Linkage rules (invariants to test)

- Every check binds >=1 scenario. A check with zero scenarios is a defect.
- Every scenario binds >=1 requirement. A scenario with zero requirements is a defect.
- Every requirement is reachable from at least one check OR is explicitly marked `unverified` with a reason. An orphan requirement is a defect.
- Every check's tier is public or private; a check with no tier is a defect.
- Every scenario's observable surface is non-empty.
- Every check's expected signal is non-empty.
- `FR-n` ids are stable across revisions; a renamed requirement is a new id plus a supersession note, not an edit.
- No two revisions share a content hash.
- A grader result references exactly one revision hash and one private suite hash.

## 7. Grading semantics

Ordered rules, from operator direction (traceability-closure.md §User direction):

1. Requirements-bound checks carry most of the score. (weight: UNKNOWN)
2. Regressions against the overall baseline can make the grade negative.
3. New-feature defects beyond mapped requirements or baseline prevent a perfect score.
4. Strict full runs with coverage.
5. Independent execution; missing evidence is FAIL, not PASS-with-warning (NC-004, `assignment-contract-proposal.md` §8).
6. Negative controls NC-001..NC-006 run with every grade; a control failure prevents PASS.
7. Two grades of the same submission against the same revision produce identical result records under hermetic conditions.

Weights are not specified by the operator and are marked UNKNOWN. No weighting may be invented by an implementing agent.

## 8. Verification and safety

- Independent execution: grader runs in its own environment and workspace; never shares mutable state with submission (`assignment-contract-proposal.md` §7).
- Read-only grader: may read submission workspace, never writes to it.
- Hidden suite: private suite not present in packet directory readable by submission; only hash and location visible.
- No shared session: grading does not reuse the agent session that produced the submission.
- Hermetic conditions: pinned toolchain, pinned dependency set, no network, fixed seed/locale where tooling permits. Nondeterminism that survives is recorded as a property of the test, not averaged away.
- Provenance: grade record captures packet revision hash, private suite hash, toolchain versions, command line, exit code, raw output digest.
- Negative controls: NC-001 empty submission (must FAIL), NC-002 no-op submission (must FAIL), NC-003 inverted-logic sentinel (must FAIL), NC-004 missing evidence (must FAIL, not PASS-with-warning), NC-005 nondeterminism probe (divergence surfaced), NC-006 suite integrity (hash mismatch aborts grading).
- Missing evidence handling: a check with no captured evidence is FAIL; never reported as PASS with a warning.
- Nondeterminism handling: determinism class per check; probabilistic/environmental checks declare repetition count and aggregation. (count and aggregation: UNKNOWN, operator has not ruled, traceability-closure.md and assignment-contract-proposal.md §11.7)
- A hash proves a file is unchanged. It does not prove correctness. A passing test is evidence of a property of the submission, never proof of semantic correctness of the contract (`assignment-contract-proposal.md` §7).

## 9. SCTBDD mapping

SCTBDD is an umbrella spanning specification, contract, test and behaviour DD methodologies (operator direction 2026-11-11). No expansion is invented here. Mapping of epic artifacts onto methodologies verifiable in the research corpus:

| Methodology | Contributes to this epic | Cannot prove |
|---|---|---|
| Specification by example | Scenarios with given/when/then and observable surface | That the implementation is correct |
| Design by contract | Artifact predicates (min_bytes, must_contain, must_match, min_count, AllowEmpty) in `cmd/dagrun/internal/plan/plan.go`; per-kind contracts in `cmd/dagrun/internal/verify/kinds.go` | Semantic correctness of the contract itself |
| BDD scenarios | Scenario entity with bound requirement ids and observable surface | That hidden checks pass |
| ATDD | Acceptance criteria as executable checks; dagrun `Check` field; executableCheck in `cmd/dagrun/internal/agileplus/agileplus.go` | That prose criteria are testable (they are reported as Unmapped) |
| Consumer-driven contract testing | Export/import bridge round trip with Unmapped reporting; contractDiff in agileplus.go | That AgilePlus and dagrun agree on semantics beyond field names |
| Model-based testing | UNKNOWN: no model-based testing exists in the inspected codebase | n/a |
| Mutation testing | NC-003 inverted-logic sentinel as a minimal mutation | Full mutation score or coverage depth (UNKNOWN) |

## 10. Acceptance criteria for the epic

Each is an executable check with expected value.

1. `test -f cmd/dagrun/docs/research/epic-traceability-autograder.md && wc -l < cmd/dagrun/docs/research/epic-traceability-autograder.md` -> file exists, line count <= 320.
2. `grep -c '^## ' cmd/dagrun/docs/research/epic-traceability-autograder.md` -> 12.
3. `grep -q 'PROPOSED' cmd/dagrun/docs/research/epic-traceability-autograder.md` -> match.
4. `grep -q 'contract_version' cmd/dagrun/docs/research/epic-traceability-autograder.md` -> match.
5. `grep -q 'FR-001' cmd/dagrun/docs/research/epic-traceability-autograder.md` -> match (worked example present).
6. `grep -q 'NC-006' cmd/dagrun/docs/research/epic-traceability-autograder.md` -> match.
7. `grep -q 'UNKNOWN' cmd/dagrun/docs/research/epic-traceability-autograder.md` -> match.
8. No edit to `assignment-contract-proposal.md`, `traceability-closure.md`, `agileplus-surface.md` or anything under `tools/` during this task. (Verified by git diff at completion.)

## 11. Non-goals

- No parallel feature lifecycle, work-package system or governance platform.
- No second backlog.
- No new governance platform.
- No replacing the AgilePlus write surface.
- No autograder for a language it cannot sandbox.
- No claim of semantic correctness from a passing suite.
- No integer identifiers in any exchange format.
- No implicit approval through file existence, elapsed time or agent self-report.
- No change to AgilePlus feature state transitions as part of this work.

## 12. Open questions

| # | Question | Decision authority | Status |
|---|---|---|---|
| 1 | Authoritative approval record: first-class AgilePlus artifact in audit chain, or field on feature? Proposed: AgilePlus artifact, audited | Human approver | UNKNOWN-unresolved |
| 2 | Physical location of private suite: AgilePlus artifact tree or dagrun-private store? Proposed: dagrun private store by hash | Human approver | UNKNOWN-unresolved |
| 3 | Freeze to revision mapping: packet owns history or AgilePlus spec_revisions owns it with packet as materialized view? Proposed: AgilePlus owns it | Human approver | UNKNOWN-unresolved |
| 4 | What a freeze blocks: AgilePlus transitions such as implementing, or only dagrun dispatch? Proposed: only dagrun dispatch | Human approver | UNKNOWN-unresolved |
| 5 | Rubric ownership: who writes it, who arbitrates disputed score? | Human approver | UNKNOWN-unassigned |
| 6 | Cross-repo packets: no single owning repo, no single home | Human approver | UNKNOWN-unresolved |
| 7 | Nondeterminism policy: repetitions, aggregation, who decides variance is test vs submission defect | Human approver | UNKNOWN-unresolved |
| 8 | Retirement: what happens to frozen revisions, private suite, historical grades on ship | Human approver | UNKNOWN-unresolved |
| 9 | Adversarial submission threat model | Human approver | UNKNOWN-unwritten |
| 10 | Retroactive regrading policy | Human approver | UNKNOWN (operator 2026-11-11) |
| 11 | Grading weights | Human approver | UNKNOWN |
| 12 | Model-based testing applicability | Human approver | UNKNOWN |
| 13 | Mutation testing depth/score | Human approver | UNKNOWN |
