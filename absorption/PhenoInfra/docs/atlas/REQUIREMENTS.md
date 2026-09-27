# Program requirements

These are proposed program-level contracts, not invented complete product specifications. Product-level populations are extracted/refined from actual scope. Empty evidence links here mean not yet verified, not pass.

## REQ-01-01 — Stable subject identity

Bind each subject to immutable repository/product identity; names and counts are observations.

**Acceptance:** Renaming a fixture retains its subject relationships and source lineage.

**Status:** PROPOSED_PROGRAM_REQUIREMENT; standard; source INT-001; SPEC-01.

## REQ-01-02 — Current scope binding

Resolve current accepted parent outcome, role and actual permissions before execution.

**Acceptance:** A task without scope approval remains unclaimable for mutation.

**Status:** PROPOSED_PROGRAM_REQUIREMENT; standard; source INT-001; SPEC-01.

## REQ-01-03 — Freshness boundary

Record source revision, tool/config identity, timestamp and partial acquisition coverage.

**Acceptance:** A stale observation cannot silently satisfy a current-revision query.

**Status:** PROPOSED_PROGRAM_REQUIREMENT; standard; source INT-001; SPEC-01.

## REQ-01-04 — Local overlay identity

Represent dirty/untracked authorized state separately from its base commit.

**Acceptance:** Tests for the base commit cannot qualify changed overlay bytes.

**Status:** PROPOSED_PROGRAM_REQUIREMENT; standard; source INT-001; SPEC-01.

## REQ-01-05 — Incremental invalidation

Invalidate affected derived claims from changed inputs without erasing old evidence.

**Acceptance:** A changed source invalidates dependent evidence and leaves unrelated valid evidence reusable.

**Status:** PROPOSED_PROGRAM_REQUIREMENT; standard; source INT-001; SPEC-01.

## REQ-01-06 — Alias and lifecycle distinction

Do not infer activity, archive, deletion or permission solely from topics/prefixes/404.

**Acceptance:** Ambiguous access or conflicting role is explicit rather than classified as deleted.

**Status:** PROPOSED_PROGRAM_REQUIREMENT; standard; source INT-001; SPEC-01.

## REQ-01-07 — Complete acquisition accounting

Enumerate discovered, processed, inaccessible, excluded and unresolved sources.

**Acceptance:** A partial source scan cannot be reported as a complete repository scan.

**Status:** PROPOSED_PROGRAM_REQUIREMENT; standard; source INT-001; SPEC-01.

## REQ-01-08 — No duplicate authority

Reuse accepted source/work/evidence owners and generate projections.

**Acceptance:** A generated document edit does not mutate real engine state.

**Status:** PROPOSED_PROGRAM_REQUIREMENT; critical; source INT-001; SPEC-01.

## REQ-02-01 — Exact visible source preservation

Preserve available exact human text separately from synthesis and raw-client claims.

**Acceptance:** Captured text and digest agree; missing original timestamps remain unknown.

**Status:** PROPOSED_PROGRAM_REQUIREMENT; standard; source INT-001; SPEC-02.

## REQ-02-02 — Normalized derivative identity

Track normalization/redaction as derived records with source lineage.

**Acceptance:** A normalized text cannot be labelled original byte capture.

**Status:** PROPOSED_PROGRAM_REQUIREMENT; standard; source INT-001; SPEC-02.

## REQ-02-03 — Scoped supersession

Link decisions to the exact scope and earlier decision they supersede.

**Acceptance:** A one-repo approval cannot authorize a different repo operation.

**Status:** PROPOSED_PROGRAM_REQUIREMENT; standard; source INT-001; SPEC-02.

## REQ-02-04 — Rationale distinction

Separate historical explanation, inference and proposed rationale.

**Acceptance:** Unsupported historical rationale is flagged rather than promoted as fact.

**Status:** PROPOSED_PROGRAM_REQUIREMENT; standard; source INT-001; SPEC-02.

## REQ-02-05 — Conflicts visible

Expose contradictory behavior, identity and ownership requirements for adjudication.

**Acceptance:** Conflicting defaults appear as an unresolved decision, not last-write-wins prose.

**Status:** PROPOSED_PROGRAM_REQUIREMENT; standard; source INT-001; SPEC-02.

## REQ-02-06 — Future horizon preserved

Retain accepted future/research work without advertising it as shipped.

**Acceptance:** Narrow CVP witness does not delete the larger accepted requirement set.

**Status:** PROPOSED_PROGRAM_REQUIREMENT; standard; source INT-001; SPEC-02.

## REQ-02-07 — SROC/CDP unresolved

Retain literal unresolved labels and recover their actual schemas before claiming conformance.

**Acceptance:** No guessed expansion or implemented-state assertion appears in the package.

**Status:** PROPOSED_PROGRAM_REQUIREMENT; standard; source INT-001; SPEC-02.

## REQ-02-08 — Private acquisition policy

Acquire authorized prompts/captures with access restrictions and public derivatives separated.

**Acceptance:** A public projection cannot include a private raw prompt or secret.

**Status:** PROPOSED_PROGRAM_REQUIREMENT; standard; source INT-001; SPEC-02.

## REQ-03-01 — All artifact classes

Inventory source, tests, configs, scripts, schemas, assets, docs and external build inputs.

**Acceptance:** Fixture includes a native shell/config asset outside root build and remains accounted for.

**Status:** PROPOSED_PROGRAM_REQUIREMENT; standard; source INT-001; SPEC-03.

## REQ-03-02 — Meaningful semantic units

Map purpose at the function/state/contract/asset-family level with source spans.

**Acceptance:** Generated boilerplate inherits producer rationale; critical spans keep direct obligations.

**Status:** PROPOSED_PROGRAM_REQUIREMENT; standard; source INT-001; SPEC-03.

## REQ-03-03 — Build and runtime reachability

Trace public behavior through actual supported build/runtime/profile paths.

**Acceptance:** Disabled/mock/test-only code cannot establish shipping capability.

**Status:** PROPOSED_PROGRAM_REQUIREMENT; standard; source INT-001; SPEC-03.

## REQ-03-04 — Dynamic uncertainty

Record unobserved reflection/plugin/FFI/external usage explicitly.

**Acceptance:** Static no-reference output alone cannot authorize deletion.

**Status:** PROPOSED_PROGRAM_REQUIREMENT; standard; source INT-001; SPEC-03.

## REQ-03-05 — Source lineage

Carry logical IDs through moves, copies, extraction and version changes with evidence.

**Acceptance:** One capability moved across repositories retains links without falsely proving equivalence.

**Status:** PROPOSED_PROGRAM_REQUIREMENT; standard; source INT-001; SPEC-03.

## REQ-03-06 — Consumers and state owners

Map actual internal/external consumers and authoritative mutable state.

**Acceptance:** A consumer source-resolution gap is visible before donor retirement.

**Status:** PROPOSED_PROGRAM_REQUIREMENT; standard; source INT-001; SPEC-03.

## REQ-03-07 — Purpose and constraints

Every material unit has a sourced purpose or UNKNOWN plus preserved constraints.

**Acceptance:** A unit lacking rationale is searchable and not auto-justified by an LLM.

**Status:** PROPOSED_PROGRAM_REQUIREMENT; standard; source INT-001; SPEC-03.

## REQ-03-08 — Dissatisfaction model

Record evidence, affected job, impact, alternatives, acceptance and proposed action.

**Acceptance:** An analyzer warning is not a mandatory defect until interpreted under accepted policy.

**Status:** PROPOSED_PROGRAM_REQUIREMENT; standard; source INT-001; SPEC-03.

## REQ-03-09 — Bounded exploration

Support bounded graph expansion/search and source-linked explanation.

**Acceptance:** A large fixture cannot force unbounded context or UI expansion.

**Status:** PROPOSED_PROGRAM_REQUIREMENT; standard; source INT-001; SPEC-03.

## REQ-03-10 — Query evaluation

Test explanations against adjudicated questions and false-positive/abstention cases.

**Acceptance:** Report correct/unsupported/unknown answers, not only token savings.

**Status:** PROPOSED_PROGRAM_REQUIREMENT; standard; source INT-001; SPEC-03.

## REQ-04-01 — Native format reuse

Read actual AgilePlus/subject schemas and adapt richer existing records.

**Acceptance:** No generated schema claims official compatibility without a verified contract version.

**Status:** PROPOSED_PROGRAM_REQUIREMENT; standard; source INT-001; SPEC-04.

## REQ-04-02 — Capability decomposition

Expand actors, state, inputs, errors, recovery, support and lifecycle systematically.

**Acceptance:** A broad requirement such as resume is decomposed into testable relevant behaviors.

**Status:** PROPOSED_PROGRAM_REQUIREMENT; standard; source INT-001; SPEC-04.

## REQ-04-03 — Typed contracts

Represent data, API, UX, performance, security and delivery obligations distinctly.

**Acceptance:** Artifact count alone cannot satisfy a contract family.

**Status:** PROPOSED_PROGRAM_REQUIREMENT; standard; source INT-001; SPEC-04.

## REQ-04-04 — Stable identifiers

Assign stable IDs and explicit relation types with provenance.

**Acceptance:** Duplicate or dangling IDs fail consistency validation.

**Status:** PROPOSED_PROGRAM_REQUIREMENT; standard; source INT-001; SPEC-04.

## REQ-04-05 — Bidirectional traceability

Link source intent through requirement/decision/work/test/run/artifact and reverse gaps.

**Acceptance:** An orphan implementation and an unimplemented requirement are both detected.

**Status:** PROPOSED_PROGRAM_REQUIREMENT; standard; source INT-001; SPEC-04.

## REQ-04-06 — Critical invariants

Define non-negotiable behavior and ownership separately from optimization targets.

**Acceptance:** A throughput gain cannot compensate for a safety invariant failure.

**Status:** PROPOSED_PROGRAM_REQUIREMENT; critical; source INT-001; SPEC-04.

## REQ-04-07 — Versioned public contracts

Track schema/API/config/save compatibility and actual support profiles.

**Acceptance:** A breaking change requires migration/support decision, not merely passing new tests.

**Status:** PROPOSED_PROGRAM_REQUIREMENT; standard; source INT-001; SPEC-04.

## REQ-04-08 — No record padding

Let counts reflect the real product rather than fixed FR/ADR/entity quotas.

**Acceptance:** Generated templates are not counted as accepted product requirements.

**Status:** PROPOSED_PROGRAM_REQUIREMENT; standard; source INT-001; SPEC-04.

## REQ-05-01 — Unit floor

Meet at least 85 percent independent required unit structural/behavioral coverage; preserve stronger floors.

**Acceptance:** A below-floor unit cell blocks even if integration/E2E are high.

**Status:** PROPOSED_PROGRAM_REQUIREMENT; critical; source INT-001; SPEC-05.

## REQ-05-02 — Integration floor

Measure actual integration boundaries independently against their required inventories.

**Acceptance:** A unit mock run relabelled integration is rejected.

**Status:** PROPOSED_PROGRAM_REQUIREMENT; critical; source INT-001; SPEC-05.

## REQ-05-03 — E2E floor

Measure the real public product/consumer E2E independently.

**Acceptance:** A root library smoke test cannot qualify a native product artifact.

**Status:** PROPOSED_PROGRAM_REQUIREMENT; critical; source INT-001; SPEC-05.

## REQ-05-04 — Metric independence

Keep line, branch/decision, function and behavioral metrics distinct where supported.

**Acceptance:** High line coverage cannot hide required low branch coverage.

**Status:** PROPOSED_PROGRAM_REQUIREMENT; critical; source INT-001; SPEC-05.

## REQ-05-05 — Denominator provenance

Inventory eligible zero-hit units and freeze reviewed denominator before interpreting results.

**Acceptance:** Unknown/duplicate units and covered items outside denominator fail.

**Status:** PROPOSED_PROGRAM_REQUIREMENT; critical; source INT-001; SPEC-05.

## REQ-05-06 — Critical completeness

Cover and satisfy every finite enumerated critical obligation.

**Acceptance:** Any missing critical item blocks regardless of percentage.

**Status:** PROPOSED_PROGRAM_REQUIREMENT; critical; source INT-001; SPEC-05.

## REQ-05-07 — All mandatory checks

Run and pass required checks; missing, failed, skipped, crashed and timeout are nonaccepting.

**Acceptance:** Empty selected checks or a skipped mandatory case cannot pass.

**Status:** PROPOSED_PROGRAM_REQUIREMENT; critical; source INT-001; SPEC-05.

## REQ-05-08 — Independent run selection

Do not combine accumulators or use one run identity as three independent suites.

**Acceptance:** A mixed-family or reused run is rejected by the reference admission checks.

**Status:** PROPOSED_PROGRAM_REQUIREMENT; critical; source INT-001; SPEC-05.

## REQ-05-09 — Unsupported measurements

Expose measurement limitations and require an alternative/authorized exception.

**Acceptance:** Unsupported or zero-denominator output is not 100 percent.

**Status:** PROPOSED_PROGRAM_REQUIREMENT; critical; source INT-001; SPEC-05.

## REQ-05-10 — Negative controls

Prove verifier failure on missing/malformed inputs and actual bad behavior.

**Acceptance:** A seeded broken docs link or known-bad task causes the final gate to reject.

**Status:** PROPOSED_PROGRAM_REQUIREMENT; critical; source INT-001; SPEC-05.

## REQ-05-11 — Trust boundary

Separate payload integrity, producer authenticity and domain truth.

**Acceptance:** A valid hash on a fabricated report never grants lifecycle approval.

**Status:** PROPOSED_PROGRAM_REQUIREMENT; critical; source INT-001; SPEC-05.

## REQ-05-12 — Other required families

Track security, fault, compatibility, performance, docs and delivery obligations independently.

**Acceptance:** A required family absent from the support profile cannot disappear from acceptance silently.

**Status:** PROPOSED_PROGRAM_REQUIREMENT; critical; source INT-001; SPEC-05.

## REQ-06-01 — Preservation contract

State outputs, errors, side effects, ordering, cancellation and quality constraints before refactor.

**Acceptance:** Differential/contract tests identify an intentional behavior change separately from parity.

**Status:** PROPOSED_PROGRAM_REQUIREMENT; standard; source INT-001; SPEC-06.

## REQ-06-02 — Existing-solution assessment

Compare standard facilities and maintained dependencies before handrolling large subsystems.

**Acceptance:** Decision includes actual fit, limitations, measured cost and exit strategy.

**Status:** PROPOSED_PROGRAM_REQUIREMENT; standard; source INT-001; SPEC-06.

## REQ-06-03 — Wrapper restraint

Wrap actual policy/stability boundaries, not every dependency method.

**Acceptance:** A wrapper without useful contract difference is challenged as maintenance cost.

**Status:** PROPOSED_PROGRAM_REQUIREMENT; standard; source INT-001; SPEC-06.

## REQ-06-04 — Patch provenance

Track upstream revision, patch reason, tests, owner and removal condition.

**Acceptance:** Upgrade rehearsal detects obsolete/conflicting patches before release.

**Status:** PROPOSED_PROGRAM_REQUIREMENT; standard; source INT-001; SPEC-06.

## REQ-06-05 — Dead-code classification

Distinguish accepted inactive, future, superseded, duplicate, optional and unknown behavior.

**Acceptance:** No static candidate is deleted without support/consumer/intent review.

**Status:** PROPOSED_PROGRAM_REQUIREMENT; standard; source INT-001; SPEC-06.

## REQ-06-06 — Consumer parity

Verify affected consumers and clean dependencies before retiring a duplicate owner.

**Acceptance:** A filename match or clean patch application alone fails migration acceptance.

**Status:** PROPOSED_PROGRAM_REQUIREMENT; standard; source INT-001; SPEC-06.

## REQ-06-07 — Maintenance evidence

Measure custom concepts/glue/updates/cycles/release burden rather than LOC alone.

**Acceptance:** A smaller implementation with worse resource/error behavior does not qualify.

**Status:** PROPOSED_PROGRAM_REQUIREMENT; standard; source INT-001; SPEC-06.

## REQ-06-08 — Safe rollback

Keep tested state/source recovery appropriate to each change.

**Acceptance:** Git revert is not represented as a database restore.

**Status:** PROPOSED_PROGRAM_REQUIREMENT; standard; source INT-001; SPEC-06.

## REQ-07-01 — Explicit applet manifest

Declare capabilities, state, ports, permissions, lifecycle, resources and children.

**Acceptance:** An unnamed shared mutable state fails boundary review.

**Status:** PROPOSED_PROGRAM_REQUIREMENT; standard; source INT-001; SPEC-07.

## REQ-07-02 — Dependency direction

Keep domain rules independent of concrete UI/provider/storage implementations.

**Acceptance:** Architecture tests detect forbidden dependency direction.

**Status:** PROPOSED_PROGRAM_REQUIREMENT; standard; source INT-001; SPEC-07.

## REQ-07-03 — Behavioral substitutability

Qualify adapters against errors, timing, data and cancellation contracts.

**Acceptance:** Type compatibility alone cannot certify an adapter.

**Status:** PROPOSED_PROGRAM_REQUIREMENT; standard; source INT-001; SPEC-07.

## REQ-07-04 — Recursive composition

Allow composites to expose applet contracts without copying child authority.

**Acceptance:** Composed state ownership remains consistent across nesting.

**Status:** PROPOSED_PROGRAM_REQUIREMENT; standard; source INT-001; SPEC-07.

## REQ-07-05 — Optional capability semantics

Differentiate disabled, unsupported, unavailable, forbidden and incompatible.

**Acceptance:** Required missing backend is non-ready rather than mock healthy.

**Status:** PROPOSED_PROGRAM_REQUIREMENT; standard; source INT-001; SPEC-07.

## REQ-07-06 — Locality-aware lowering

Use direct/local paths unless isolation/placement cost justifies boundaries.

**Acceptance:** A proposed RPC/microservice split records overhead and benefit.

**Status:** PROPOSED_PROGRAM_REQUIREMENT; standard; source INT-001; SPEC-07.

## REQ-07-07 — No forced repo split

Applet identity does not itself create a repository or release requirement.

**Acceptance:** New repo requires independent boundary/approval beyond a module name.

**Status:** PROPOSED_PROGRAM_REQUIREMENT; standard; source INT-001; SPEC-07.

## REQ-07-08 — Lifecycle composition

Specify startup, readiness, quiescence, cancellation, unmount and recovery.

**Acceptance:** Parent shutdown does not leave unowned children or duplicate operations.

**Status:** PROPOSED_PROGRAM_REQUIREMENT; standard; source INT-001; SPEC-07.

## REQ-08-01 — Current primary sources

Pin versions and claim-specific sources before relying on external facts.

**Acceptance:** A seed URL or vendor claim cannot be tagged independently measured.

**Status:** PROPOSED_PROGRAM_REQUIREMENT; standard; source INT-001; SPEC-08.

## REQ-08-02 — Relevant research breadth

Build relevant candidate longlists and justified executable shortlists.

**Acceptance:** No duplicate/adjacent padding or unproved maximum claims.

**Status:** PROPOSED_PROGRAM_REQUIREMENT; standard; source INT-001; SPEC-08.

## REQ-08-03 — Fair baseline

Include competent direct/upstream/composed alternatives as appropriate.

**Acceptance:** Owned preprocessing/setup is accounted for equivalently.

**Status:** PROPOSED_PROGRAM_REQUIREMENT; standard; source INT-001; SPEC-08.

## REQ-08-04 — Modes separated

Distinguish controlled replay, matched live and idiomatic whole-stack trials.

**Acceptance:** Language/runtime differences are not attributed solely to framework design.

**Status:** PROPOSED_PROGRAM_REQUIREMENT; standard; source INT-001; SPEC-08.

## REQ-08-05 — Ergonomics study

Measure writing/testing/debugging/change/upgrade burden beyond LOC.

**Acceptance:** At least one post-version-one change request is evaluated.

**Status:** PROPOSED_PROGRAM_REQUIREMENT; standard; source INT-001; SPEC-08.

## REQ-08-06 — Safety and failure trials

Inject representative interruption, malformed output, permission and resource failures.

**Acceptance:** Success-only corpus cannot certify recovery/safety.

**Status:** PROPOSED_PROGRAM_REQUIREMENT; standard; source INT-001; SPEC-08.

## REQ-08-07 — Uncertainty and retention

Retain all outcomes and predeclare thresholds/stopping/analysis.

**Acceptance:** Retries and inconclusive results remain in the final record.

**Status:** PROPOSED_PROGRAM_REQUIREMENT; standard; source INT-001; SPEC-08.

## REQ-08-08 — Bounded claims

Require hard invariants plus declared margins and meaningful advantage/distinct job.

**Acceptance:** No universal winner or safety-compensating aggregate score is published.

**Status:** PROPOSED_PROGRAM_REQUIREMENT; standard; source INT-001; SPEC-08.

## REQ-08-09 — Case study

Demonstrate actual user setup/task/recovery/output separately from design comparison.

**Acceptance:** A mocked demo cannot be the installed-product case study.

**Status:** PROPOSED_PROGRAM_REQUIREMENT; standard; source INT-001; SPEC-08.

## REQ-08-10 — Negative-result usefulness

Allow dependency adoption, narrowing or retained-fork justification as outcomes.

**Acceptance:** Pilot failure is not concealed to preserve the owned brand.

**Status:** PROPOSED_PROGRAM_REQUIREMENT; standard; source INT-001; SPEC-08.

## REQ-09-01 — Complementary product pair

Separate implementation ownership from active independent assurance/comparison.

**Acceptance:** One agent is not sole author of requirement, oracle, implementation and approval.

**Status:** PROPOSED_PROGRAM_REQUIREMENT; standard; source INT-001; SPEC-09.

## REQ-09-02 — Ten Tracera seats

Assign bounded distinct streams with schema/integration ownership.

**Acceptance:** Ten independent incompatible graph engines do not satisfy the allocation.

**Status:** PROPOSED_PROGRAM_REQUIREMENT; standard; source INT-001; SPEC-09.

## REQ-09-03 — Product independence

Permit repo-local portable records before Tracera completion.

**Acceptance:** Unrelated product CVP is not blocked on every future graph integration.

**Status:** PROPOSED_PROGRAM_REQUIREMENT; standard; source INT-001; SPEC-09.

## REQ-09-04 — Write leases

Bind unique worktrees and target path ownership, including shared manifests.

**Acceptance:** Concurrent overlapping destination writes are blocked/escalated.

**Status:** PROPOSED_PROGRAM_REQUIREMENT; standard; source INT-001; SPEC-09.

## REQ-09-05 — Scoped permissions

Tie writes, publication and lifecycle actions to explicit real authorization.

**Acceptance:** Documentation approval cannot authorize admin merge or deletion.

**Status:** PROPOSED_PROGRAM_REQUIREMENT; critical; source INT-001; SPEC-09.

## REQ-09-06 — Restart reconciliation

Reconcile unknown operation outcome before retrying side effects.

**Acceptance:** Dropped connection is not treated as proof of mutation failure.

**Status:** PROPOSED_PROGRAM_REQUIREMENT; standard; source INT-001; SPEC-09.

## REQ-09-07 — Parent outcome continuation

Continue useful authorized work beyond a narrow PR while preserving scope.

**Acceptance:** Inherited required defects remain assigned; child completion does not close parent.

**Status:** PROPOSED_PROGRAM_REQUIREMENT; standard; source INT-001; SPEC-09.

## REQ-09-08 — Owned external blockers

Record owner, exact action, affected gates and wakeup condition.

**Acceptance:** Out-of-scope prose without ownership is not a terminal completion state.

**Status:** PROPOSED_PROGRAM_REQUIREMENT; standard; source INT-001; SPEC-09.

## REQ-09-09 — Resource admission

Separate chat capacity from CPU/GPU/native/CI/review quotas.

**Acceptance:** Foreground-interference budgets are tested under real concurrent load.

**Status:** PROPOSED_PROGRAM_REQUIREMENT; standard; source INT-001; SPEC-09.

## REQ-09-10 — No fake schedules

Calculate durations only from explicit estimates and capacity assumptions.

**Acceptance:** Missing estimates yield unknown schedule, not fabricated dates.

**Status:** PROPOSED_PROGRAM_REQUIREMENT; standard; source INT-001; SPEC-09.

## REQ-10-01 — Artifact identity

Bind source, build profile, package digest and installed executable.

**Acceptance:** A tag or source archive cannot impersonate the tested binary.

**Status:** PROPOSED_PROGRAM_REQUIREMENT; standard; source INT-001; SPEC-10.

## REQ-10-02 — Clean consumer

Install/build without private warm caches or accidental sibling checkouts.

**Acceptance:** Missing dependency is a real blocker rather than a local workaround hidden from docs.

**Status:** PROPOSED_PROGRAM_REQUIREMENT; standard; source INT-001; SPEC-10.

## REQ-10-03 — Actual tooling adoption

Use real scoped AgilePlus/PhenoDocs contracts and receipts.

**Acceptance:** Generated docs do not count as an engine operation or working federation.

**Status:** PROPOSED_PROGRAM_REQUIREMENT; standard; source INT-001; SPEC-10.

## REQ-10-04 — Real product capture

Capture qualified actual product behavior and negative cases.

**Acceptance:** Mock/stub screenshots or fixed live evaluator values cannot qualify a product.

**Status:** PROPOSED_PROGRAM_REQUIREMENT; standard; source INT-001; SPEC-10.

## REQ-10-05 — Authored asset distinction

Separate branding/concept art from product evidence; preserve source/rights.

**Acceptance:** No generated overlay falsifies implemented UI or performance evidence.

**Status:** PROPOSED_PROGRAM_REQUIREMENT; standard; source INT-001; SPEC-10.

## REQ-10-06 — Role-specific delivery

GUI, CLI, library, lab and historical targets have appropriate acceptance.

**Acceptance:** Reference repo is not forced into a fake app release.

**Status:** PROPOSED_PROGRAM_REQUIREMENT; standard; source INT-001; SPEC-10.

## REQ-10-07 — Public route qualification

Verify actual authorized docs/package/app distribution plus rollback.

**Acceptance:** Configured provider names alone cannot claim deployment completed.

**Status:** PROPOSED_PROGRAM_REQUIREMENT; standard; source INT-001; SPEC-10.

## REQ-10-08 — Private/public separation

Protect private content across docs/search/media and exports.

**Acceptance:** A public generated index must not contain private capture content.

**Status:** PROPOSED_PROGRAM_REQUIREMENT; standard; source INT-001; SPEC-10.

## REQ-11-01 — No automatic deletion

Keep destructive lifecycle actions outside this program default authority.

**Acceptance:** Repo count targets cannot trigger deletion.

**Status:** PROPOSED_PROGRAM_REQUIREMENT; critical; source INT-001; SPEC-11.

## REQ-11-02 — Fork-network protection

Honor no-delete policy and scoped exceptional authority.

**Acceptance:** A fork remains protected regardless of a pause/topic rename.

**Status:** PROPOSED_PROGRAM_REQUIREMENT; critical; source INT-001; SPEC-11.

## REQ-11-03 — Full custody

Preserve required source/dirty/refs/releases/data and verify recovery when transitioning.

**Acceptance:** A Git bundle alone cannot be labelled a complete dirty-state backup.

**Status:** PROPOSED_PROGRAM_REQUIREMENT; critical; source INT-001; SPEC-11.

## REQ-11-04 — Untrusted content

Treat repo prompts and historic tool output as data, not controlling instructions.

**Acceptance:** Malicious source text cannot cause an unauthorized shell/tool action.

**Status:** PROPOSED_PROGRAM_REQUIREMENT; critical; source INT-001; SPEC-11.

## REQ-11-05 — Least-privilege tests

Use disposable scoped credentials and controlled isolation.

**Acceptance:** General QA never mounts the operator entire home or unrestricted vault.

**Status:** PROPOSED_PROGRAM_REQUIREMENT; critical; source INT-001; SPEC-11.

## REQ-11-06 — Evidence redaction

Track private raw and sanitized derivatives with separate IDs.

**Acceptance:** Blurring a screenshot does not satisfy log/index redaction.

**Status:** PROPOSED_PROGRAM_REQUIREMENT; critical; source INT-001; SPEC-11.

## REQ-11-07 — Credential segregation

Separate normal edit privileges from admin/delete/publication authority.

**Acceptance:** A worker cannot bypass gates by selecting an elevated credential.

**Status:** PROPOSED_PROGRAM_REQUIREMENT; critical; source INT-001; SPEC-11.

## REQ-11-08 — Update/retention boundaries

Preserve provenance and policy when changing tool/model/asset dependencies.

**Acceptance:** License/source obligations survive absorption and export.

**Status:** PROPOSED_PROGRAM_REQUIREMENT; critical; source INT-001; SPEC-11.

## Revision 1.1 — INT-003 ecosystem-first requirements

### REQ-06-09 — Owned work in the reuse search

Search existing owned capabilities as well as external facilities before duplicating a substantive mechanism.

**Acceptance:** Decision records a bounded owned/external search and compares extending the existing owner with a new implementation.

**Source:** INT-003 · **Spec:** SPEC-06 · **State:** proposed mechanics, not product verification.

### REQ-06-10 — Aggregate ecosystem outcome

Assess changes by total ecosystem user value and maintenance burden under hard correctness, security, compatibility and performance constraints.

**Acceptance:** A smaller local diff with greater unaddressed downstream cost is not labelled an ecosystem improvement.

**Source:** INT-003 · **Spec:** SPEC-06 · **State:** proposed mechanics, not product verification.

### REQ-06-11 — Evidence-tiered consumers

Distinguish supported current, committed planned, plausible future and unknown/external consumers.

**Acceptance:** A speculative consumer is not used as evidence of adoption or an implemented support promise; unknown is not zero.

**Source:** INT-003 · **Spec:** SPEC-06 · **State:** proposed mechanics, not product verification.

### REQ-06-12 — Consumer-led extension seams

Design shared contracts for actual and committed needs while keeping future-facing seams economical and optional.

**Acceptance:** A proposed abstraction is challenged when it adds mandatory unrelated dependencies or speculative services.

**Source:** INT-003 · **Spec:** SPEC-06 · **State:** proposed mechanics, not product verification.

### REQ-06-13 — Canonical capability evolution

Improve the authoritative owned capability or a justified adapter instead of accumulating independent copies.

**Acceptance:** Source/release ownership and any intentional alternate implementation or temporary mirror are explicit.

**Source:** INT-003 · **Spec:** SPEC-06 · **State:** proposed mechanics, not product verification.

### REQ-06-14 — Cross-consumer preserved contract

State and verify affected consumer behavior, data, security, resource and compatibility constraints before shared changes are accepted.

**Acceptance:** Passing provider unit tests alone cannot qualify a changed required consumer contract.

**Source:** INT-003 · **Spec:** SPEC-06 · **State:** proposed mechanics, not product verification.

### REQ-06-15 — Bounded cross-owner coordination

Keep source, consumer, integration and verifier responsibilities explicit across isolated authorized worktrees.

**Acceptance:** A dependency on another owner becomes a linked owned task, not unauthorized writes or discarded parent work.

**Source:** INT-003 · **Spec:** SPEC-06 · **State:** proposed mechanics, not product verification.

### REQ-06-16 — Continuous scoped reassessment

Reassess reuse and consumer fit during meaningful development events without perpetual unrelated rewrites.

**Acceptance:** New consumer or repeated-workaround evidence creates a bounded decision/change; an urgent fix is not blocked by speculative refactoring.

**Source:** INT-003 · **Spec:** SPEC-06 · **State:** proposed mechanics, not product verification.

### REQ-06-17 — Proportional impact evidence

Attach consumer-impact and reuse decisions to existing task/PR/ADR records; keep local no-impact attestations lightweight.

**Acceptance:** A shared API change requires consumer detail; a supported internal spelling change does not require a whole-portfolio audit.

**Source:** INT-003 · **Spec:** SPEC-06 · **State:** proposed mechanics, not product verification.

### REQ-06-18 — Adoption and bridge retirement

Track consumer transition, compatibility bridges, duplicate ownership and rollback through the accepted parent outcome.

**Acceptance:** Local PR closure cannot imply completed migration; temporary shims have owner, tracking item and removal trigger.

**Source:** INT-003 · **Spec:** SPEC-06 · **State:** proposed mechanics, not product verification.

### REQ-06-19 — Own-versus-external neutrality

Do not privilege an owned implementation or external popularity over evidence of contract fit and total cost.

**Acceptance:** A qualified external replacement, owned extension, or deliberate separation can each win without manufactured novelty.

**Source:** INT-003 · **Spec:** SPEC-06 · **State:** proposed mechanics, not product verification.

### REQ-06-20 — Reuse beyond code

Apply consumer-aware evolution to test fixtures, schemas, prompts, docs, workflows, assets and operations as well as runtime code.

**Acceptance:** A common policy/check is reused with subject-specific inputs rather than independently weakened clones.

**Source:** INT-003 · **Spec:** SPEC-06 · **State:** proposed mechanics, not product verification.
