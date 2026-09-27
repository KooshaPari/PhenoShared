# SPEC-06 — Reuse and semantic compression

Status: proposed program contract; no engine transition or product verification claimed.

## REQ-06-01 Preservation contract

State outputs, errors, side effects, ordering, cancellation and quality constraints before refactor.

Acceptance: Differential/contract tests identify an intentional behavior change separately from parity.

## REQ-06-02 Existing-solution assessment

Compare standard facilities and maintained dependencies before handrolling large subsystems.

Acceptance: Decision includes actual fit, limitations, measured cost and exit strategy.

## REQ-06-03 Wrapper restraint

Wrap actual policy/stability boundaries, not every dependency method.

Acceptance: A wrapper without useful contract difference is challenged as maintenance cost.

## REQ-06-04 Patch provenance

Track upstream revision, patch reason, tests, owner and removal condition.

Acceptance: Upgrade rehearsal detects obsolete/conflicting patches before release.

## REQ-06-05 Dead-code classification

Distinguish accepted inactive, future, superseded, duplicate, optional and unknown behavior.

Acceptance: No static candidate is deleted without support/consumer/intent review.

## REQ-06-06 Consumer parity

Verify affected consumers and clean dependencies before retiring a duplicate owner.

Acceptance: A filename match or clean patch application alone fails migration acceptance.

## REQ-06-07 Maintenance evidence

Measure custom concepts/glue/updates/cycles/release burden rather than LOC alone.

Acceptance: A smaller implementation with worse resource/error behavior does not qualify.

## REQ-06-08 Safe rollback

Keep tested state/source recovery appropriate to each change.

Acceptance: Git revert is not represented as a database restore.

## Scope discipline

Apply the actual subject support/role contract. Preserve richer existing source formats and authority. Generated spec bundles do not certify native AgilePlus compatibility; inspect the installed engine/schema first. Unknowns and failures remain explicit.

## REQ-06-09 Owned work in the reuse search

Search existing owned capabilities as well as external facilities before duplicating a substantive mechanism.

Acceptance: Decision records a bounded owned/external search and compares extending the existing owner with a new implementation.

## REQ-06-10 Aggregate ecosystem outcome

Assess changes by total ecosystem user value and maintenance burden under hard correctness, security, compatibility and performance constraints.

Acceptance: A smaller local diff with greater unaddressed downstream cost is not labelled an ecosystem improvement.

## REQ-06-11 Evidence-tiered consumers

Distinguish supported current, committed planned, plausible future and unknown/external consumers.

Acceptance: A speculative consumer is not used as evidence of adoption or an implemented support promise; unknown is not zero.

## REQ-06-12 Consumer-led extension seams

Design shared contracts for actual and committed needs while keeping future-facing seams economical and optional.

Acceptance: A proposed abstraction is challenged when it adds mandatory unrelated dependencies or speculative services.

## REQ-06-13 Canonical capability evolution

Improve the authoritative owned capability or a justified adapter instead of accumulating independent copies.

Acceptance: Source/release ownership and any intentional alternate implementation or temporary mirror are explicit.

## REQ-06-14 Cross-consumer preserved contract

State and verify affected consumer behavior, data, security, resource and compatibility constraints before shared changes are accepted.

Acceptance: Passing provider unit tests alone cannot qualify a changed required consumer contract.

## REQ-06-15 Bounded cross-owner coordination

Keep source, consumer, integration and verifier responsibilities explicit across isolated authorized worktrees.

Acceptance: A dependency on another owner becomes a linked owned task, not unauthorized writes or discarded parent work.

## REQ-06-16 Continuous scoped reassessment

Reassess reuse and consumer fit during meaningful development events without perpetual unrelated rewrites.

Acceptance: New consumer or repeated-workaround evidence creates a bounded decision/change; an urgent fix is not blocked by speculative refactoring.

## REQ-06-17 Proportional impact evidence

Attach consumer-impact and reuse decisions to existing task/PR/ADR records; keep local no-impact attestations lightweight.

Acceptance: A shared API change requires consumer detail; a supported internal spelling change does not require a whole-portfolio audit.

## REQ-06-18 Adoption and bridge retirement

Track consumer transition, compatibility bridges, duplicate ownership and rollback through the accepted parent outcome.

Acceptance: Local PR closure cannot imply completed migration; temporary shims have owner, tracking item and removal trigger.

## REQ-06-19 Own-versus-external neutrality

Do not privilege an owned implementation or external popularity over evidence of contract fit and total cost.

Acceptance: A qualified external replacement, owned extension, or deliberate separation can each win without manufactured novelty.

## REQ-06-20 Reuse beyond code

Apply consumer-aware evolution to test fixtures, schemas, prompts, docs, workflows, assets and operations as well as runtime code.

Acceptance: A common policy/check is reused with subject-specific inputs rather than independently weakened clones.
