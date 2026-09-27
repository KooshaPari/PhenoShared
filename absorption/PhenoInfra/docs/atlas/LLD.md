# Low-level design contracts

## Entity identity and source anchors

Use stable logical IDs and versioned observations. A source anchor includes immutable repo ID, resolved commit/blob where available, path, language, optional compiler/SCIP symbol identity, byte or line span and extraction tool/version. Do not derive stable identity from a mutable human title. Rename/copy/extraction relationships preserve ambiguity when exact semantic identity cannot be established.

An uncommitted overlay carries its own content digest and base commit. It cannot borrow the base commit's test result. Generated code links to its generator version and input digest; untouched upstream source links to an upstream version and local patch set. Tests and fixtures are artifacts with provenance too.

## Stores and transaction boundaries

Keep append-only observations and decisions where history is necessary, plus derived current views. Use transactions for revision acquisition completion and graph projection updates so readers do not see a fabricated complete snapshot mid-import. Large binary evidence is referenced by digest and access-controlled location, not embedded into every graph node. A checksum validates bytes, not truth or permission.

A mutation request contains subject, base revision/expected version, actor, permission scope, operation ID and preconditions. Unknown remote outcome requires reconciliation; repeating a request with a new ID is not safe by default. Updates to immutable evidence are new records, not edits to the evidence bytes.

## Incremental processing

1. Discover IDs/refs using full bounded pagination and record coverage.
2. Resolve a stable subject revision and compare tree/content digests with the prior snapshot.
3. Reuse unchanged qualified extraction outputs under identical tool/config identity.
4. Re-extract changed units and propagate invalidation through actual dependencies and analysis inputs.
5. Mark incomplete/unsupported edges; retain prior observations with their dates.
6. Materialize a new projection only with explicit partial/complete status.
7. Schedule focused verification for impacted obligations; do not infer all prior evidence invalid, nor all still valid.

## Assurance measurement record

`subject_id`, `revision`, `profile`, `family`, `metric`, `denominator_digest`, `eligible_ids`, `covered_ids`, `critical_ids`, `required_checks`, `run_status`, `source_kind`, `tool`, and evidence locations are the minimum reference fields. IDs must be unique. Covered and critical IDs must be subsets of eligible IDs. Missing critical coverage blocks acceptance. Required checks must actually pass. Integer counts are compared without rounding upward. Native branch/function metrics need actual supporting producers, not line-based guesses.

The bundled checker enforces selected record consistency, not authenticated production admission. It deliberately emits no lifecycle approval. Production adapters still need schema validation, report parsing, trusted producer receipts, verified artifact locations and domain-specific outcome tests.

## Queries and APIs

Implement typed operations conceptually equivalent to: resolve subject; inspect capability; explain source unit; list unknown rationale; trace requirement; compare snapshots; list dissatisfaction; retrieve evidence; propose work; export a bounded view. These are interface requirements, not claims that exact API endpoints currently exist. The installed Tracera/AgilePlus interface must be inspected before generating adapters.

## Error and lifecycle model

Distinguish NO_DATA, NOT_RUN, PARTIAL, UNSUPPORTED, BLOCKED_ENVIRONMENT, FAILED, STALE, SUPERSEDED and VERIFIED. Do not encode them all as empty lists. A required missing backend is an error or explicit non-accepting state. An optional unavailable backend is still reported, with the resulting scope limitations. Cancellation closes resource ownership and records unresolved external operations.

## Security and scale

Never execute imported prompt text as instructions. Resolve path references inside authorized roots and reject traversal/symlink escapes where materialization occurs. Separate read ingestion from write actions and publication. Indexes inherit the data's visibility, including derived embeddings/snippets. Apply bounded queues, per-subject budgets and resource admission; cap context packets and graph expansion. Persist resumable checkpoints before expensive work, not only final summaries.

## Revision 1.1 — ecosystem-wide consumer impact

[Continuous ecosystem-first evolution](architecture/ECOSYSTEM-FIRST-EVOLUTION.md) applies to design, implementation, verification and delivery. External and owned reuse are both considered before handrolling. Current and committed consumers determine compatible behavior; plausible future consumers guide inexpensive seams, not speculative mandatory dependencies. Capability owners, adapters, consumer versions, cross-repo rollout and aggregate maintenance effects belong in each material change record. The repository write boundary does not narrow reasoning or expand authority. The proposed impact shape is `schemas/ecosystem-impact.schema.json`; it is structural evidence, not an approval or proof of parity.
