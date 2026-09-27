# PhenoGfx: role-specific atlas and qualification

**Role:** Shared graphics/data/FFI components. **Class:** pooled-foundation. **Repository ID:** 1271708536.

This is a proposed scope record, not permission to revive, move, delete, publish or create a repository. For pooled foundations, count packages and independently maintained contracts rather than treating a shared folder as one product. The contemplated Pheno consolidation is not executed by this package.

## What must be understood

Map data ownership, renderer adapters, native ABI, asset conversion and required game consumers. A byte-compatible API and a semantically correct rendering path are different proofs.

Map source/build inclusion, native tools, configuration, data ownership, consumers, external contracts and publication paths. Preserve old IDs and provenance. Reachability, API usage and intended future behavior need independent evidence. Unknowns remain visible; no file is declared safe to delete solely from a name, stale comment, or lack of static references.

## Maintenance reduction

Reuse engine facilities and common data formats; minimize cross-engine wrappers to the actual shared contract.

Use an adopt/patch/wrap/retain decision per meaningful subsystem. Record required semantics: outputs, errors, ordering, security, recovery, cancellation, performance and supported platforms. Patch sets need source/version pins, ownership, an upstream strategy, reproducible build and exit plan. Avoid a generic wrapper that simply renames a dependency's entire API.

## Qualification

At least the accepted real consumers exercise the canonical package with correct ABI/data/rendering and explicit performance budgets.

The local contract inherits the same independent QA policy as product work for the relevant profiles. N/A is a reviewed role decision, not an escape from a difficult test. Consumer end-to-end behavior is the relevant E2E for a library. Negative controls must demonstrate that actual failures propagate to the final gate. A reference-only repository instead receives custody, licensing, truthful status and preservation checks; it does not need a fake app release.

## Coordination

Use a pooled foundation owner plus independent consumer verification. Do not allocate a full pair of product-development chats to every small dependency. Changes in a shared target need unique worktrees and path leases, especially workspace manifests, locks, generated catalogs and CI. Keep source and destination acceptance linked, and do not duplicate the canonical product/spec/work ledger.

## Evidence before a status change

Record actual source and built artifact identity, supported profiles, test selection and native reports, baseline comparison where a replacement is proposed, consumer validation, licensing and rollback. A clean file move or successful Cargo metadata query is not semantic absorption. Current names/topics do not override accepted scope or the user's no-delete policy for fork networks.

## Cross-ecosystem acceptance — revision 1.1

Apply the [shared consumer-evolution rule](../../architecture/ECOSYSTEM-FIRST-EVOLUTION.md) to this subject's actual capabilities: inspect owned and external reuse, preserve current consumers, distinguish planned/speculative uses, and account for downstream cost. Relevant adaptations and consumer tests remain part of the parent outcome. Do not reopen a completed audit or create a universal abstraction merely to satisfy this rule.
