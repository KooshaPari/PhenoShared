# Start here — portfolio atlas, assurance and simplification

This package converts the immediately preceding plan into work contracts and per-product pilots. It is a planning and reference-validation artifact, not another live GitHub audit, an executed migration, an accepted product scorecard, or permission to mutate remote systems.

## Read in this order

1. Read [the master assignment](prompts/MASTER-COORDINATOR.md) and the [program specification](SPECIFICATION.md).
2. Resolve the subject in [the planning roster](portfolio/ROSTER.md) by immutable repository ID, current name, accepted role, worktree and owner. Prefixes/topics and a 52-ish count are not authority.
3. Read that subject's `products/<name>/DOSSIER.md`, its pilot and the accepted repo instructions. Preserve richer existing intent capture, specs, tools and ledgers.
4. Produce a delta outcome-gap record. Do not restart a complete historical audit or overwrite better current evidence.
5. Claim one bounded work package under the real permissions. The product pair works toward a shared parent outcome; narrow PRs do not redefine the parent scope.
6. Run and independently verify a real useful path. Keep unknown, failed, blocked, partial and superseded states explicit.

## Revision 1.1 — mandatory direction, proposed execution mechanics

Read [ecosystem-first evolution](architecture/ECOSYSTEM-FIRST-EVOLUTION.md) and give existing chats [the focused addendum](prompts/ECOSYSTEM-FIRST-ADDENDUM.md). Reuse now explicitly includes owned work, and substantive changes carry cross-consumer impact. This is a delta, not a restart. [Revision notes](REVISION-1.1.md) identify changes and preserved evidence.

## Three concurrent tracks

Product comprehension builds an explanatory atlas; qualification/comparison produces meaningful independent proof; simplification/delivery reduces custom burden and installs a current viable product. None waits for a complete Tracera implementation. A known repair need not wait for a perfect atlas. A small repair does not establish atlas completeness.

## Main boundaries

Tracera is the persistent product/system model. AgilePlus is repository-scoped work/spec tooling. PhenoDocs is reusable rendering/federation tooling. Subject repositories and approved authorities retain their source documents and operational state. This package introduces shared interchange records and projections, not a universal database or new product registry.

SROC/CDP remain unresolved labels in [the terminology register](intent/TERMINOLOGY-AND-CONFLICTS.md). Do not invent their expansions. Their ambiguity does not block the unambiguous atlas, QA, comparison or CVP work.

## What is real in this archive

The original contextual archives, their hashes, captured visible user request, proposed subject-specific work plans, schemas, example records, documentation validators and validator tests are real files. All product pilots are planned, not executed. Example measurements are synthetic, not portfolio evidence. No product is certified by the package validator.

## Validation

From this `docs/` directory, run `python scripts/validate_package.py .` and `python -m unittest discover -s tests -v`. The validator requires Python 3.11+ and jsonschema; a requirements file is supplied. Install dependencies only into an appropriate isolated environment. See [VALIDATION_REPORT.md](VALIDATION_REPORT.md) for what was actually run during packaging and what was not.

## Permission defaults

Read and propose only until the coordinator binds an accepted task and exact permissions. Editing documentation is not permission for code movement, admin merges, publication, DNS changes, branch cleanup, archives or deletion. Keep source/destination ownership, privacy and rollback explicit.
