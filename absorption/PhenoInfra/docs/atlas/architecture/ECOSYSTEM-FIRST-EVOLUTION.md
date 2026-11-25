# Ecosystem-first, consumer-driven evolution

**Revision 1.1. Source: INT-003.** The two user directions are explicit: modify/adapt/wrap instead of unnecessarily handrolling, and apply that preference to our own work while improving the overall polyrepo ecosystem for current and possible future consumers. The mechanics below are proposed acceptance rules, not claimed product implementations or new mutation authority.

## 1. Governing rule

> Prefer reusing, modifying, adapting or narrowly wrapping a suitable existing capability—external or owned—over a parallel bespoke implementation. Evolve that capability with its supported consumers and credible future uses in view. Optimize total ecosystem value and maintenance burden, not the apparent cleanliness or delivery speed of one repository.

The repository assigned to an agent is a custody and write boundary, not the boundary of architectural reasoning. A feature is not an ecosystem improvement merely because its local tests pass. A shared implementation is not correct merely because all consumers depend on it.

Apply this to product code, libraries, protocols, configuration, tests, fixtures, prompts, documentation generators, build/release workflows, assets and operational policies. Reuse our existing useful work as deliberately as external work. Equally, do not privilege our own implementation when an external facility better satisfies the contract at lower total cost.

## 2. Before creating another implementation

Locate the relevant capability in the subject, sibling packages/repositories, declared consumers, previous accepted extractions and suitable external projects. Search by semantics, entrypoints and manifests, not names alone. Record the search scope and unresolved locations; absence from one code-search result does not prove the capability does not exist.

Compare: use as-is; extend the current owner; adapt at a consumer boundary; improve a narrow shared contract; contribute upstream; maintain a focused patch; intentionally keep separate implementations; or implement a new capability. Do not mechanically follow an ordering when compatibility, privacy, performance, licensing, safety or ownership makes another option better.

An owned deficiency is normally a candidate for an owned upstream improvement, not a reason for each consumer to carry a local copy. A consumer-specific behavior belongs in an adapter/configuration/extension only when that is the right contract. Do not push unrelated application policy into a generic shared module merely to eliminate a small amount of code.

Temporary local shims can be necessary for urgent repairs or unavailable owners. Name their owner, upstream tracking item, tested scope, expiry/review trigger and removal condition. Do not silently turn a bridge into permanent parallel authority.

## 3. Classify consumers before generalizing

| Consumer tier | Required evidence and response |
|---|---|
| Current, supported | Identify real entrypoints, versions, platforms, deployment/release paths, data and constraints. Preserve the agreed compatibility envelope and execute relevant consumer tests. |
| Committed/planned | Identify an accepted requirement, sponsor/owner and bounded near-term use. Test a contract example or spike where useful; do not call the future product implemented. |
| Plausible future | State the use case, assumptions and confidence. Prefer an inexpensive extension seam, stable vocabulary, optional dependency or migration route. Do not invent integration tests/results or force the current product to wait. |
| Unknown/external | Record incomplete reachability or external-consumer visibility. Use public compatibility policy and risk-based rollout; do not interpret unknown as zero consumers. |

One consumer can justify a reusable boundary. Several consumers do not automatically justify one universal abstraction. Current/planned evidence determines the shared semantics; hypothetical possibilities should not generate a speculative framework, a new service fleet, or hundreds of unaccepted features.

## 4. Optimize the aggregate system, with hard constraints

For a material decision, compare current and proposed user outcomes, authored code/contract burden, cross-repo glue, duplicate policy, dependency coupling/cycles, upgrade effort, patch drift, build/test cost, runtime resources, operations, and coordination/review cost. Include migration and downstream costs instead of exporting them to another owner.

Use measured quantities where available and labelled estimates/ranges otherwise. Leave unlike units separate unless a reviewed decision model supplies explicit conversions. A weighted score must never conceal a safety, correctness, performance or compatibility violation. Counterfactuals include a small local repair, extending an existing module, and retaining a justified separation.

A local win with a larger downstream burden is not accepted as an ecosystem win. A required security/correctness repair can be necessary even if it adds cost; explain that constraint and choose the least-burdensome valid solution. The objective is not fewer lines or repositories at any cost.

## 5. Preserve semantics at the right level

Before modification, state observable outputs/errors, ordering, retries/idempotency, cancellation, side effects, state ownership/durability, numeric tolerances, latency tails, throughput, memory, isolation, extension points and data/package compatibility that are required by affected consumers. Separate useful behavior from bugs that must change.

Run the relevant positive, negative, differential/property, integration, E2E, compatibility and performance tests against the actual candidate. Preserve the independent QA floors and stronger accepted constraints. Testing only the modified shared library is not sufficient for a changed consumer contract. Testing every product for a one-line internal spelling change is not proportional either.

Break an accepted contract only through an explicit, scoped product/compatibility decision and consumer transition plan. Internal-looking functions can still be part of an external extension surface; static reference absence does not settle that question. No semantic preservation is claimed for configurations that were not verified.

## 6. One capability owner, composable consumers

Choose the authoritative implementation and release owner per capability, not per old repository name. Prefer a common mechanism plus explicit optional adapters over consumer-name switches and duplicated implementations. Respect intentional alternate implementations where performance, licensing, trust or independent lifecycle requires them.

Composite applets may consume and expose lower-level applets, but composition must preserve dependency direction, permission boundaries, state ownership and version negotiation. Same-process reuse should not acquire a network hop merely to look federated. Independent products must remain usable without mandatory adoption of the entire Phenotype environment.

A proposed future Pheno workspace is a hosting choice, not permission to create one enormous dependency, one release train, one runtime or one globally shared database. Packages keep bounded APIs, minimal dependency closures and focused tests.

## 7. Coordinate writes without narrowing responsibility

The source owner prepares the capability change; consumer owners supply current contracts and integration changes; one integration owner coordinates shared manifest/lock/schema changes; an independent verifier evaluates affected behavior. Preserve unique worktrees/path leases and exact base revisions.

A worker can identify and prepare a cross-repo improvement without obtaining write access everywhere. Register the smallest linked task and owner for work outside its lease. Carry the accepted parent outcome forward. A child PR or paused worker does not erase remaining consumer migrations, and a consumer handoff does not expand destructive authority.

Schema approvals, hosted credentials, publication, force pushes and retirement remain under their existing permission policies. No current agent should restart a broad audit or move source simply to comply with this document.

## 8. Make this continuous and bounded

Reassess on a new consumer, duplicated mechanism, repeated adapter workaround, upstream release, changed platform/performance constraint, breaking schema/API proposal, or repeated defect across consumers. During ordinary work, leave the touched capability and its nearby boundaries more coherent when the change is safe and material.

Continual improvement does not mean perpetual rewriting. Preserve working code when a proposed refactor has no evidenced benefit. Do not mix large unrelated cleanup into an urgent repair. Capture discoveries outside the current slice as owned opportunities with evidence, rather than ignoring them or taking over the ecosystem.

Measure completed useful outcomes: supported consumers still working; duplicate mechanisms actually retired; repeated policy eliminated; lower upgrade/patch burden; reduced change amplification; simpler install/recovery; useful new capability delivered. A migration is not closed while both copies require independent maintenance unless that duplication is deliberately governed.

## 9. Proportional acceptance record

Use existing work/ADR/PR records. Do not create another registry. For each substantive capability, dependency, public-contract, schema, workflow or architecture change, record:

1. Intent and capability; source owner and affected consumer tiers.
2. Internal and external reuse alternatives and why the chosen delta is needed.
3. Preserved semantics, legitimate differences and future-facing seams.
4. Costs/benefits across the ecosystem, including migration and ongoing ownership.
5. Actual candidate, consumer checks, results, unknowns and rollback/recovery.
6. Cross-owner dependencies, compatibility rollout and bridge removal conditions.
7. Decision and acceptance authority; proposal versus accepted/verified status.

For a truly local change, a short impact attestation naming the boundary, consumer search and no-contract-change rationale is sufficient. A material shared change needs the fuller record. Expected benefits are not measured benefits. A schema can enforce field structure but cannot prove the consumer map is complete or authenticate approval.

## 10. Examples, not new architecture mandates

**Docs checking:** reuse a qualified checker, put shared policy/output normalization at the appropriate tool boundary, and let applications supply their own docs/visibility rules. Do not independently handroll weaker checkers in each product.

**Session metadata:** inspect existing owned formats and adapters before adding another canonical session schema. Share interoperable primitives where contracts align while preserving each tool's actual state and sensitive-data boundaries.

**Game graphics:** consider Civis and WorldSphereMod's real data/rendering requirements before extracting a primitive. Keep their different engines and gameplay policy in adapters/products. Do not introduce a universal lowest-common-denominator renderer or regress frame time for abstract reuse.

These examples describe a method, not a finding that a particular current component should be merged. The current and future consumer evidence decides the boundary.

## Review questions

What does this improve for the ecosystem? What suitable existing work did we extend or reuse? Which consumers bear a cost? Which properties remain proved? Is a supposed shared abstraction actually two different domains? Have future possibilities been accommodated cheaply rather than implemented speculatively? Who owns the resulting capability and its removal/upgrade path?

Use [the compact work/PR attachment template](../work/CONSUMER-IMPACT-TEMPLATE.md) or adapt the [JSON shape](../schemas/ecosystem-impact.schema.json) to existing richer records.
