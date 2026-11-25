# Program specification

Normative records live in `records/requirements.json`; this document explains their interpretation. They are proposed program contracts except where explicitly identified as carried human constraints. Actual AgilePlus acceptance and lifecycle transitions remain unperformed.

## Immutable observation, versioned interpretation

An observation binds an authenticated source where available, immutable repository ID, resolved revision, path/blob or artifact digest, acquisition boundary and timestamp. A claim references observations and states whether it is inferred, reported, proposed or measured. A decision names its authority and scope. Derived views never silently convert claims into decisions. New observations supersede stale claims with links rather than erase history.

## Full artifact accountability

Inventory tracked files, declared untracked/generated inputs, configuration, automation, data/schema, assets, native shells, documentation and external build dependencies. Use hashes and source ownership for exact duplicates. Use semantic/AST/API and consumer analysis for possible duplicates. A duplicate file is not proof of complete migration. A path absent from default compilation can still be a supported optional, native, plugin, generated or external-consumer path.

Map meaningful spans, not prose per token. Generated records inherit producer/contract rationale. Critical checks can require several obligations for a few lines. Dynamic behavior and inaccessible sources remain explicitly unresolved. Stable entities use source anchors and lineage relationships across revisions; line numbers are locators, not identity.

## Assurance and evidence

Every required measurement cell is independent: subject × capability/component × language/runtime × platform × feature/build profile × family × metric × revision/artifact. Unit, integration and E2E cannot reuse one accumulator or relabel one run. Existing stronger floors remain. Critical obligations all pass; 85% coverage does not permit 15% failing tests.

A measurement must identify denominator provenance, eligible zero-hit items, covered items, required checks, run identity and tool adapter. Zero denominators are unknown/N/A by reviewed interpretation, not automatic 100%. Native tool limitations require another instrument, an explicitly labelled proxy or an authorized exception. A worker cannot reduce the denominator or critical set simply to pass.

## Architectural change and reuse

Refactors preserve declared observable semantics, including ordering, errors, cancellation, consistency, numeric properties, compatibility, isolation and resource limits. Use existing facilities when suitable. Every substantial handrolled subsystem gets a retain/adopt/patch/wrap assessment. A shared foundation may contain several packages with independent release contracts. An applet defines semantic ports/state/permissions/lifecycle; it need not be a repository, process or microservice.

## Comparative truth

Separate documented capabilities, hypothesized advantages, measured non-inferiority and actual user outcomes. Every serious pilot has a real baseline, workload, version identities, hard invariants, margins, controls, failure classification and retained unsuccessful trials. Evaluate implementation ergonomics and maintenance changes, not LOC alone. Keep controlled replay, matched live and idiomatic whole-stack modes distinct.

## Delivery and governance

Close useful bounded work depth-first, while maintaining full-horizon traceability and owned blockers. A source branch, PR, integrated revision, verification run, release asset and installed binary are different identities and states. Inherited failures may be separate PRs but remain in the parent's delivery responsibility. Do not replace target work with low-risk comments, badges or docs generation when authorized substantive work remains.

The files under `specs/` use a provisional AgilePlus-shaped layout observed in earlier supplied artifacts. They are not certified against a currently deployed engine. Read the local adapter guidance before materialization. No engine receipts, human approvals or accepted migrations are manufactured here.

## Revision 1.1 — ecosystem-wide consumer impact

[Continuous ecosystem-first evolution](architecture/ECOSYSTEM-FIRST-EVOLUTION.md) applies to design, implementation, verification and delivery. External and owned reuse are both considered before handrolling. Current and committed consumers determine compatible behavior; plausible future consumers guide inexpensive seams, not speculative mandatory dependencies. Capability owners, adapters, consumer versions, cross-repo rollout and aggregate maintenance effects belong in each material change record. The repository write boundary does not narrow reasoning or expand authority. The proposed impact shape is `schemas/ecosystem-impact.schema.json`; it is structural evidence, not an approval or proof of parity.
