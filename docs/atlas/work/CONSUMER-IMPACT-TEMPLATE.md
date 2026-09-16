# Consumer-impact attachment — use inside an existing work item, PR or ADR

This is not a new ledger or approval workflow. Link the source identities and evidence already owned by the accepted tools. Follow [the policy](../architecture/ECOSYSTEM-FIRST-EVOLUTION.md).

## Small local change

Use a short attestation: **changed semantic boundary; bounded internal/external consumer search; reason no accepted contract/support profile changes; verification performed; review owner**. Unknown consumer visibility is not evidence of no impact.

## Material capability or shared-contract change

**Subject/capability and intent:** State the exact thing changing and why, with source revision and owning work item.

**Current owner and reuse options:** Existing internal implementations investigated; external facilities investigated; use-as-is, modify, adapter/wrapper, patch, fork, retain-separated or handroll decision; rationale and alternatives.

**Consumers:** Current supported consumers with identities/versions/profiles; committed planned consumers with requirement/owner evidence; plausible future consumers with assumptions; unresolved or external reachability. Keep those tiers separate.

**Preserved contract:** Functional/error/state/security/performance/numerical/compatibility properties that must hold. Identify accidental bugs separately from intended behavior.

**Ecosystem effect:** Before/after authored logic, duplication, dependency direction, update/patch effort, runtime/build cost, consumer migration and coordination burden. Mark unmeasured expectations and uncertain estimates; do not invent a net-benefit number.

**Boundary and future seams:** What remains shared, what stays consumer-specific, and how a plausible future use can be supported without a mandatory speculative framework.

**Execution:** Authorized source and consumer worktrees/paths, integration owner, linked dependencies, rollout sequence, bridge removal condition, rollback/state recovery.

**Verification and decision:** Exact candidate, relevant provider and consumer tests, negative cases, performance results, unknowns, reviewer, and required acceptance authority. Local completion and final parent adoption remain separate states.

The optional JSON shape is [ecosystem-impact.schema.json](../schemas/ecosystem-impact.schema.json); [the example](../examples/ecosystem-impact.json) is synthetic. Schema validity does not discover consumers, authenticate reviewers, establish benefits or approve a change.
